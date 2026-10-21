"""SQLite bridge from the dry-run executor/proposal layers to P1 ZoneStore.

The bridge stores executor records in dedicated tables in the same SQLite file
as ``trader.zone_store.ZoneStore``. It never changes exchange state and never
turns a dry-run intent into an order dispatch.
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from trader.zone_store import ZoneNotFound, ZoneStore


class P1IntegrationError(RuntimeError):
    """Raised when an integration record cannot be persisted safely."""


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise P1IntegrationError(f"unsupported integration value: {type(value).__name__}")


def _json_text(value: Any) -> str:
    return json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class P1IntegrationStore:
    """Implement the P2 store protocol and record P3 proposals in P1 SQLite."""

    def __init__(self, zone_store: ZoneStore):
        self.zone_store = zone_store
        if zone_store.path == ":memory:":
            self._connection = zone_store._conn
            self._owns_connection = False
        else:
            self._connection = sqlite3.connect(zone_store.path, timeout=5, isolation_level=None)
            self._owns_connection = True
        self._connection.execute("PRAGMA busy_timeout = 5000")
        self._initialise()

    def close(self) -> None:
        if self._owns_connection:
            self._connection.close()

    def __enter__(self) -> "P1IntegrationStore":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _initialise(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS executor_intents (
                client_oid TEXT PRIMARY KEY,
                zone_id TEXT NOT NULL,
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                state TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS executor_snapshots (
                zone_id TEXT PRIMARY KEY,
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                state TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS executor_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                zone_id TEXT NOT NULL,
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                event_kind TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS executor_events_zone_idx
                ON executor_events(zone_id, event_id);
            CREATE TABLE IF NOT EXISTS trading_mandates (
                mandate_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                payload_json TEXT NOT NULL,
                PRIMARY KEY(mandate_id, version)
            );
            CREATE TABLE IF NOT EXISTS ai_risk_checks (
                risk_check_id TEXT PRIMARY KEY,
                decision_id TEXT NOT NULL,
                mandate_id TEXT NOT NULL,
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                result TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS paper_intents (
                client_oid TEXT PRIMARY KEY,
                zone_id TEXT NOT NULL,
                decision_id TEXT NOT NULL,
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ai_agent_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                zone_id TEXT NOT NULL,
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                event_kind TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ai_agent_events_zone_idx
                ON ai_agent_events(zone_id, event_id);
            """
        )

    def _require_zone(self, zone_id: str) -> None:
        try:
            self.zone_store.get_zone(zone_id)
        except ZoneNotFound as exc:
            raise P1IntegrationError(f"P1 zone does not exist: {zone_id}") from exc

    def save_intent(self, record: Mapping[str, Any]) -> None:
        zone_id = str(record.get("zone_id", ""))
        client_oid = str(record.get("client_oid", ""))
        if not zone_id or not client_oid:
            raise P1IntegrationError("intent requires zone_id and client_oid")
        self._require_zone(zone_id)
        self._connection.execute(
            """
            INSERT INTO executor_intents(client_oid, zone_id, state, payload_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(client_oid) DO UPDATE SET
                state = excluded.state,
                payload_json = excluded.payload_json,
                recorded_at = CURRENT_TIMESTAMP
            """,
            (client_oid, zone_id, str(record.get("state", "")), _json_text(record)),
        )

    def append_event(self, event: Mapping[str, Any]) -> None:
        zone_id = str(event.get("zone_id", ""))
        if not zone_id:
            raise P1IntegrationError("executor event requires zone_id")
        self._require_zone(zone_id)
        kind = str(event.get("kind", "event"))
        self._connection.execute(
            "INSERT INTO executor_events(zone_id, event_kind, payload_json) VALUES (?, ?, ?)",
            (zone_id, kind, _json_text(event)),
        )

    def save_zone(self, snapshot: Mapping[str, Any]) -> None:
        zone_id = str(snapshot.get("zone_id", ""))
        if not zone_id:
            raise P1IntegrationError("zone snapshot requires zone_id")
        self._require_zone(zone_id)
        self._connection.execute(
            """
            INSERT INTO executor_snapshots(zone_id, state, payload_json)
            VALUES (?, ?, ?)
            ON CONFLICT(zone_id) DO UPDATE SET
                state = excluded.state,
                payload_json = excluded.payload_json,
                recorded_at = CURRENT_TIMESTAMP
            """,
            (zone_id, str(snapshot.get("state", "")), _json_text(snapshot)),
        )

    def record_proposal(self, record: Mapping[str, Any], *, zone_id: str | None = None) -> None:
        """Append a P3 proposal as an audit event, never as an order intent."""
        snapshot = record.get("snapshot")
        snapshot = snapshot if isinstance(snapshot, Mapping) else {}
        zone_id = zone_id or str(snapshot.get("zone_id") or snapshot.get("opportunity_id") or "")
        if not zone_id:
            raise P1IntegrationError("proposal requires an explicit zone_id or snapshot zone_id/opportunity_id")
        self._require_zone(zone_id)
        self._connection.execute(
            "INSERT INTO executor_events(zone_id, event_kind, payload_json) VALUES (?, ?, ?)",
            (zone_id, "AI_PROPOSAL_RECORDED", _json_text({"event": "AI_PROPOSAL_RECORDED", "record": record, "dry_run": True})),
        )

    def save_mandate(self, mandate: Mapping[str, Any]) -> None:
        mandate_id = str(mandate.get("mandate_id", ""))
        version = int(mandate.get("version", 0))
        if not mandate_id or version < 1:
            raise P1IntegrationError("mandate requires mandate_id and positive version")
        existing = self._connection.execute(
            "SELECT payload_json FROM trading_mandates WHERE mandate_id = ? AND version = ?",
            (mandate_id, version),
        ).fetchone()
        payload_json = _json_text(mandate)
        if existing is not None:
            if existing[0] != payload_json:
                raise P1IntegrationError("mandate version is immutable")
            return
        self._connection.execute(
            "INSERT INTO trading_mandates(mandate_id, version, payload_json) VALUES (?, ?, ?)",
            (mandate_id, version, payload_json),
        )

    def get_mandate(self, mandate_id: str, version: int) -> dict[str, Any] | None:
        row = self._connection.execute(
            "SELECT payload_json FROM trading_mandates WHERE mandate_id = ? AND version = ?",
            (mandate_id, version),
        ).fetchone()
        return None if row is None else json.loads(row[0])

    def save_risk_check(self, check: Mapping[str, Any]) -> None:
        risk_check_id = str(check.get("risk_check_id", ""))
        decision_id = str(check.get("decision_id", ""))
        if not risk_check_id or not decision_id:
            raise P1IntegrationError("risk check requires risk_check_id and decision_id")
        payload_json = _json_text(check)
        existing = self._connection.execute(
            "SELECT payload_json FROM ai_risk_checks WHERE risk_check_id = ?",
            (risk_check_id,),
        ).fetchone()
        if existing is not None:
            if existing[0] != payload_json:
                raise P1IntegrationError("risk_check_id already exists with a different payload")
            return
        self._connection.execute(
            "INSERT INTO ai_risk_checks(risk_check_id, decision_id, mandate_id, result, payload_json) VALUES (?, ?, ?, ?, ?)",
            (risk_check_id, decision_id, str(check.get("mandate_id", "")), str(check.get("result", "")), payload_json),
        )

    def save_paper_intent(self, intent: Mapping[str, Any]) -> None:
        client_oid = str(intent.get("client_oid", ""))
        zone_id = str(intent.get("zone_id", ""))
        decision_id = str(intent.get("decision_id", ""))
        if not client_oid or not zone_id or not decision_id:
            raise P1IntegrationError("paper intent requires client_oid, zone_id, and decision_id")
        self._require_zone(zone_id)
        payload_json = _json_text(intent)
        existing = self._connection.execute(
            "SELECT payload_json FROM paper_intents WHERE client_oid = ?",
            (client_oid,),
        ).fetchone()
        if existing is not None:
            if existing[0] != payload_json:
                raise P1IntegrationError("paper client_oid already exists with a different payload")
            return
        self._connection.execute(
            "INSERT INTO paper_intents(client_oid, zone_id, decision_id, payload_json) VALUES (?, ?, ?, ?)",
            (client_oid, zone_id, decision_id, payload_json),
        )

    def agent_events(self, zone_id: str) -> list[dict[str, Any]]:
        self._require_zone(zone_id)
        rows = self._connection.execute(
            "SELECT payload_json FROM ai_agent_events WHERE zone_id = ? ORDER BY event_id",
            (zone_id,),
        ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def append_agent_event(self, zone_id: str, event_kind: str, payload: Mapping[str, Any]) -> None:
        self._require_zone(zone_id)
        event = {"zone_id": zone_id, "event": event_kind, **dict(payload), "dry_run": True}
        self._connection.execute(
            "INSERT INTO ai_agent_events(zone_id, event_kind, payload_json) VALUES (?, ?, ?)",
            (zone_id, event_kind, _json_text(event)),
        )

    def paper_intents(self, zone_id: str) -> list[dict[str, Any]]:
        self._require_zone(zone_id)
        rows = self._connection.execute(
            "SELECT payload_json FROM paper_intents WHERE zone_id = ? ORDER BY recorded_at, client_oid",
            (zone_id,),
        ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def intents(self, zone_id: str) -> list[dict[str, Any]]:
        self._require_zone(zone_id)
        rows = self._connection.execute(
            "SELECT * FROM executor_intents WHERE zone_id = ? ORDER BY client_oid",
            (zone_id,),
        ).fetchall()
        return [self._decode_row(row, "payload_json") for row in rows]

    def events(self, zone_id: str) -> list[dict[str, Any]]:
        self._require_zone(zone_id)
        rows = self._connection.execute(
            "SELECT * FROM executor_events WHERE zone_id = ? ORDER BY event_id",
            (zone_id,),
        ).fetchall()
        return [self._decode_row(row, "payload_json") for row in rows]

    def snapshot(self, zone_id: str) -> dict[str, Any] | None:
        self._require_zone(zone_id)
        row = self._connection.execute(
            "SELECT * FROM executor_snapshots WHERE zone_id = ?",
            (zone_id,),
        ).fetchone()
        return None if row is None else self._decode_row(row, "payload_json")

    @staticmethod
    def _decode_row(row: sqlite3.Row | tuple[Any, ...], payload_column: str) -> dict[str, Any]:
        # Payload is the final selected column in all read methods.
        payload = row[-1]
        return json.loads(payload)
