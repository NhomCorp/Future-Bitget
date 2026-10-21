"""Durable, append-oriented storage for zone preview and risk observations.

This module deliberately owns no exchange side effects.  It stores immutable zone
configuration, current lifecycle state, observations, and an audit event stream.
The sync layer can use the returned risk trigger as a stop intent, but this store
never submits or cancels an exchange order.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import os
import sqlite3
import threading
import uuid
from typing import Any, Iterator, Mapping


SCHEMA_VERSION = 1
STATES = frozenset({"PREVIEW", "ACTIVE", "STOPPING", "UNKNOWN", "CLOSED"})
_TRANSITIONS = {
    "PREVIEW": frozenset({"PREVIEW", "ACTIVE", "UNKNOWN", "CLOSED"}),
    "ACTIVE": frozenset({"ACTIVE", "STOPPING", "UNKNOWN", "CLOSED"}),
    "STOPPING": frozenset({"STOPPING", "UNKNOWN", "CLOSED"}),
    "UNKNOWN": frozenset({"UNKNOWN", "STOPPING", "CLOSED"}),
    "CLOSED": frozenset({"CLOSED"}),
}


class ZoneStoreError(RuntimeError):
    """Base error for invalid or unavailable local zone state."""


class ZoneValidationError(ZoneStoreError, ValueError):
    """Raised when a zone or observation fails a local invariant."""


class ZoneNotFound(ZoneStoreError, KeyError):
    """Raised when a requested zone does not exist."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _decimal(value: Any, field: str, *, required: bool = False, positive: bool = False) -> Decimal | None:
    if value is None or value == "":
        if required:
            raise ZoneValidationError(f"{field} is required")
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ZoneValidationError(f"{field} must be a decimal") from exc
    if not result.is_finite():
        raise ZoneValidationError(f"{field} must be finite")
    if positive and result <= 0:
        raise ZoneValidationError(f"{field} must be greater than zero")
    return result


def _decimal_text(value: Any, field: str, *, required: bool = False, positive: bool = False) -> str | None:
    result = _decimal(value, field, required=required, positive=positive)
    return None if result is None else format(result, "f")


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, float):
        if not (float("-inf") < value < float("inf")):
            raise ZoneValidationError("JSON values must be finite")
        return value
    raise ZoneValidationError(f"unsupported JSON value: {type(value).__name__}")


def _json_text(value: Any) -> str:
    try:
        return json.dumps(_json_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ZoneValidationError("value cannot be encoded as JSON") from exc


def _normalise_config(config: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(config, Mapping):
        raise ZoneValidationError("zone config must be an object")
    symbol = str(config.get("symbol", "")).strip().upper()
    if not symbol or len(symbol) > 32:
        raise ZoneValidationError("symbol is required")
    side = str(config.get("side", "")).strip().lower()
    if side not in {"long", "short"}:
        raise ZoneValidationError("side must be long or short")
    ref_price = _decimal_text(config.get("ref_price"), "ref_price", required=True, positive=True)
    loss_limit = _decimal_text(config.get("zone_loss_limit_usdt"), "zone_loss_limit_usdt", positive=True)
    sl_pct = _decimal_text(config.get("sl_pct"), "sl_pct", positive=True)
    if loss_limit is None and sl_pct is None:
        raise ZoneValidationError("at least one risk limit is required")

    normalised = dict(_json_value(config))
    normalised.update(
        {
            "symbol": symbol,
            "side": side,
            "ref_price": ref_price,
            "zone_loss_limit_usdt": loss_limit,
            "sl_pct": sl_pct,
            "policy_version": str(config.get("policy_version", "zone-risk-policy.p1")),
        }
    )
    return normalised


@dataclass(frozen=True)
class ZoneRecord:
    zone_id: str
    symbol: str
    side: str
    state: str
    created_at: str
    updated_at: str
    config: dict[str, Any]
    ref_price: str
    last_mark_price: str | None
    last_net_pnl: str | None
    stop_reason: str | None
    version: int

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ZoneRecord":
        return cls(
            zone_id=row["zone_id"],
            symbol=row["symbol"],
            side=row["side"],
            state=row["state"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            config=json.loads(row["config_json"]),
            ref_price=row["ref_price"],
            last_mark_price=row["last_mark_price"],
            last_net_pnl=row["last_net_pnl"],
            stop_reason=row["stop_reason"],
            version=row["version"],
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "symbol": self.symbol,
            "side": self.side,
            "state": self.state,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "config": self.config,
            "ref_price": self.ref_price,
            "last_mark_price": self.last_mark_price,
            "last_net_pnl": self.last_net_pnl,
            "stop_reason": self.stop_reason,
            "version": self.version,
        }


class ZoneStore:
    """SQLite-backed zone store with atomic state transitions and audit events."""

    def __init__(self, path: str | os.PathLike[str] | None = None):
        self.path = os.fspath(path or os.environ.get("ZONE_STORE_PATH", "trader/data/zones.sqlite3"))
        if self.path != ":memory:":
            parent = os.path.dirname(os.path.abspath(self.path))
            os.makedirs(parent, mode=0o700, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, timeout=5, isolation_level=None, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        if self.path == ":memory:":
            self._conn.execute("PRAGMA journal_mode = MEMORY")
        else:
            self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = FULL")
        self._initialise()
        if self.path != ":memory:":
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass

    def _initialise(self) -> None:
        with self._transaction():
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS store_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS zones (
                    zone_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL CHECK (side IN ('long', 'short')),
                    state TEXT NOT NULL CHECK (state IN ('PREVIEW', 'ACTIVE', 'STOPPING', 'UNKNOWN', 'CLOSED')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    ref_price TEXT NOT NULL,
                    last_mark_price TEXT,
                    last_net_pnl TEXT,
                    stop_reason TEXT,
                    version INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS zone_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    zone_id TEXT NOT NULL REFERENCES zones(zone_id),
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS zone_observations (
                    observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    zone_id TEXT NOT NULL REFERENCES zones(zone_id),
                    observed_at TEXT NOT NULL,
                    mark_price TEXT,
                    realized_pnl TEXT NOT NULL,
                    unrealized_pnl TEXT NOT NULL,
                    fees TEXT NOT NULL,
                    funding_paid TEXT NOT NULL,
                    funding_received TEXT NOT NULL,
                    net_pnl TEXT NOT NULL,
                    source TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS zone_events_zone_idx ON zone_events(zone_id, event_id);
                CREATE INDEX IF NOT EXISTS zone_observations_zone_idx ON zone_observations(zone_id, observation_id);
                """
            )
            self._conn.execute(
                "INSERT OR REPLACE INTO store_meta(key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield
            except Exception:
                self._conn.rollback()
                raise
            else:
                self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> "ZoneStore":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _row(self, zone_id: str) -> sqlite3.Row:
        row = self._conn.execute("SELECT * FROM zones WHERE zone_id = ?", (zone_id,)).fetchone()
        if row is None:
            raise ZoneNotFound(zone_id)
        return row

    def get_zone(self, zone_id: str) -> ZoneRecord:
        with self._lock:
            return ZoneRecord.from_row(self._row(zone_id))

    def list_zones(self, *, include_closed: bool = True) -> list[ZoneRecord]:
        with self._lock:
            query = "SELECT * FROM zones"
            params: tuple[Any, ...] = ()
            if not include_closed:
                query += " WHERE state <> ?"
                params = ("CLOSED",)
            query += " ORDER BY created_at, zone_id"
            return [ZoneRecord.from_row(row) for row in self._conn.execute(query, params).fetchall()]

    def create_zone(
        self,
        config: Mapping[str, Any],
        *,
        zone_id: str | None = None,
        state: str = "PREVIEW",
        now: str | None = None,
    ) -> ZoneRecord:
        normalised = _normalise_config(config)
        state = str(state).upper()
        if state not in STATES:
            raise ZoneValidationError(f"unsupported state: {state}")
        if state not in {"PREVIEW", "ACTIVE"}:
            raise ZoneValidationError("new zones may only start in PREVIEW or ACTIVE")
        zone_id = zone_id or f"zone-{uuid.uuid4().hex[:12]}"
        if not zone_id or len(zone_id) > 80:
            raise ZoneValidationError("invalid zone_id")
        created = now or utc_now()
        config_json = _json_text(normalised)
        with self._transaction():
            try:
                self._conn.execute(
                    """
                    INSERT INTO zones(zone_id, symbol, side, state, created_at, updated_at,
                                      config_json, ref_price, version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        zone_id,
                        normalised["symbol"],
                        normalised["side"],
                        state,
                        created,
                        created,
                        config_json,
                        normalised["ref_price"],
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ZoneValidationError(f"zone_id already exists: {zone_id}") from exc
            self._insert_event(zone_id, "ZONE_CREATED", {"state": state, "config": normalised}, created)
        return self.get_zone(zone_id)

    def _insert_event(self, zone_id: str, event_type: str, payload: Mapping[str, Any], occurred_at: str) -> None:
        self._conn.execute(
            "INSERT INTO zone_events(zone_id, event_type, occurred_at, payload_json) VALUES (?, ?, ?, ?)",
            (zone_id, event_type, occurred_at, _json_text(payload)),
        )

    def transition_zone(
        self,
        zone_id: str,
        state: str,
        *,
        reason: str | None = None,
        payload: Mapping[str, Any] | None = None,
        now: str | None = None,
    ) -> ZoneRecord:
        target = str(state).upper()
        if target not in STATES:
            raise ZoneValidationError(f"unsupported state: {target}")
        occurred = now or utc_now()
        with self._transaction():
            row = self._row(zone_id)
            current = row["state"]
            if target not in _TRANSITIONS[current]:
                raise ZoneValidationError(f"invalid transition {current} -> {target}")
            event_payload = dict(payload or {})
            if reason is not None:
                event_payload["reason"] = str(reason)
            self._conn.execute(
                "UPDATE zones SET state = ?, updated_at = ?, stop_reason = ?, version = version + 1 WHERE zone_id = ?",
                (target, occurred, reason if target == "STOPPING" else row["stop_reason"], zone_id),
            )
            self._insert_event(zone_id, "STATE_CHANGED", {"from": current, "to": target, **event_payload}, occurred)
        return self.get_zone(zone_id)

    def activate_zone(self, zone_id: str, *, now: str | None = None) -> ZoneRecord:
        return self.transition_zone(zone_id, "ACTIVE", now=now)

    @staticmethod
    def _risk_result(zone: ZoneRecord, observation: Mapping[str, str | None]) -> tuple[str | None, dict[str, Any]]:
        config = zone.config
        net = Decimal(observation["net_pnl"] or "0")
        reasons: list[str] = []
        loss_limit = _decimal(config.get("zone_loss_limit_usdt"), "zone_loss_limit_usdt", positive=True)
        if loss_limit is not None and net <= -loss_limit:
            reasons.append("LOSS_BUDGET")
        mark = _decimal(observation.get("mark_price"), "mark_price")
        sl_pct = _decimal(config.get("sl_pct"), "sl_pct", positive=True)
        price_triggered = False
        stop_price: str | None = None
        if mark is not None and sl_pct is not None:
            ref = Decimal(zone.ref_price)
            multiplier = Decimal(1) - sl_pct / Decimal(100) if zone.side == "long" else Decimal(1) + sl_pct / Decimal(100)
            stop = ref * multiplier
            stop_price = format(stop, "f")
            price_triggered = mark <= stop if zone.side == "long" else mark >= stop
            if price_triggered:
                reasons.append("PRICE_SL")
        reason = None
        if reasons:
            reason = "BOTH" if len(reasons) == 2 else reasons[0]
        return reason, {"net_pnl": format(net, "f"), "stop_price": stop_price, "reasons": reasons}

    def record_observation(
        self,
        zone_id: str,
        observation: Mapping[str, Any],
        *,
        source: str = "unknown",
        now: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(observation, Mapping):
            raise ZoneValidationError("observation must be an object")
        observed = now or str(observation.get("observed_at") or utc_now())
        mark = _decimal_text(observation.get("mark_price"), "mark_price")
        realized = _decimal_text(observation.get("realized_pnl", "0"), "realized_pnl", required=True)
        unrealized = _decimal_text(observation.get("unrealized_pnl", "0"), "unrealized_pnl", required=True)
        fees = _decimal_text(observation.get("fees", "0"), "fees", required=True)
        funding_paid = _decimal_text(observation.get("funding_paid", "0"), "funding_paid", required=True)
        funding_received = _decimal_text(observation.get("funding_received", "0"), "funding_received", required=True)
        net = Decimal(realized or "0") + Decimal(unrealized or "0") - Decimal(fees or "0") - Decimal(funding_paid or "0") + Decimal(funding_received or "0")
        source = str(source)[:80] or "unknown"
        raw_payload = dict(_json_value(observation))
        raw_payload["observed_at"] = observed
        raw_payload["source"] = source
        with self._transaction():
            row = self._row(zone_id)
            zone = ZoneRecord.from_row(row)
            normalized = {
                "mark_price": mark,
                "realized_pnl": realized,
                "unrealized_pnl": unrealized,
                "fees": fees,
                "funding_paid": funding_paid,
                "funding_received": funding_received,
                "net_pnl": format(net, "f"),
            }
            reason, risk = self._risk_result(zone, normalized)
            self._conn.execute(
                """
                INSERT INTO zone_observations(
                    zone_id, observed_at, mark_price, realized_pnl, unrealized_pnl, fees,
                    funding_paid, funding_received, net_pnl, source, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    zone_id,
                    observed,
                    mark,
                    realized,
                    unrealized,
                    fees,
                    funding_paid,
                    funding_received,
                    format(net, "f"),
                    source,
                    _json_text(raw_payload),
                ),
            )
            state = zone.state
            stop_recorded = False
            if reason and state == "ACTIVE":
                self._conn.execute(
                    "UPDATE zones SET state = 'STOPPING', updated_at = ?, last_mark_price = ?, last_net_pnl = ?, stop_reason = ?, version = version + 1 WHERE zone_id = ?",
                    (observed, mark, format(net, "f"), reason, zone_id),
                )
                self._insert_event(zone_id, "RISK_TRIGGERED", {**risk, "reason": reason, "source": source}, observed)
                state = "STOPPING"
                stop_recorded = True
            else:
                self._conn.execute(
                    "UPDATE zones SET updated_at = ?, last_mark_price = ?, last_net_pnl = ? WHERE zone_id = ?",
                    (observed, mark, format(net, "f"), zone_id),
                )
                self._insert_event(zone_id, "OBSERVATION_RECORDED", {**normalized, "source": source, "risk": risk}, observed)
        return {
            "zone_id": zone_id,
            "state": state,
            "triggered": bool(stop_recorded),
            "reason": reason,
            "risk": risk,
            "observation": normalized,
            "source": source,
        }

    def latest_observation(self, zone_id: str) -> dict[str, Any] | None:
        with self._lock:
            self._row(zone_id)
            row = self._conn.execute(
                "SELECT * FROM zone_observations WHERE zone_id = ? ORDER BY observation_id DESC LIMIT 1",
                (zone_id,),
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["payload"] = json.loads(result.pop("payload_json"))
            return result

    def events(self, zone_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        if limit < 1 or limit > 10000:
            raise ZoneValidationError("limit must be between 1 and 10000")
        with self._lock:
            self._row(zone_id)
            rows = self._conn.execute(
                "SELECT * FROM zone_events WHERE zone_id = ? ORDER BY event_id DESC LIMIT ?",
                (zone_id, limit),
            ).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item["payload"] = json.loads(item.pop("payload_json"))
                result.append(item)
            return result
