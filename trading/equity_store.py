"""Append-only local ledger for Demo equity snapshots.

This store never calls Bitget, never keeps credentials, and never stores raw
exchange payloads. It only records parsed equity numbers and timestamps.
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
from typing import Any, Iterator, Sequence


SCHEMA_VERSION = 1
DEFAULT_PATH = "trader/data/equity.sqlite3"
SOURCE_READONLY_DEMO = "bitget_readonly_demo"


class EquityStoreError(RuntimeError):
    """Raised when the local equity ledger cannot be used."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def normalize_timestamp(value: str, name: str = "captured_at") -> str:
    if not isinstance(value, str) or not value.strip():
        raise EquityStoreError(f"{name} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EquityStoreError(f"{name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise EquityStoreError(f"{name} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def utc_day_start(value: str) -> str:
    stamp = normalize_timestamp(value, "now")
    parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    start = parsed.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return start.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _decimal(value: Decimal | int | str, name: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise EquityStoreError(f"{name} must be Decimal, integer, or decimal string")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise EquityStoreError(f"{name} must be a decimal") from exc
    if not result.is_finite() or result <= 0:
        raise EquityStoreError(f"{name} must be finite and positive")
    return result


@dataclass(frozen=True)
class EquityRow:
    captured_at: str
    utc_date: str
    equity: Decimal
    source: str
    tags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "captured_at": self.captured_at,
            "utc_date": self.utc_date,
            "equity": format(self.equity, "f"),
            "source": self.source,
            "tags": list(self.tags),
        }


class EquityStore:
    """SQLite ledger of parsed equity observations."""

    def __init__(self, path: str | os.PathLike[str] | None = None):
        self.path = os.fspath(path or os.environ.get("EQUITY_STORE_PATH", DEFAULT_PATH))
        if self.path != ":memory:":
            parent = os.path.dirname(os.path.abspath(self.path))
            os.makedirs(parent, mode=0o700, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, timeout=5, isolation_level=None, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
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
                CREATE TABLE IF NOT EXISTS equity_snapshots (
                    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    captured_at TEXT NOT NULL,
                    utc_date TEXT NOT NULL,
                    equity TEXT NOT NULL,
                    source TEXT NOT NULL,
                    tags_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS equity_snapshots_captured_idx
                    ON equity_snapshots(captured_at);
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

    def __enter__(self) -> "EquityStore":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def append(
        self,
        captured_at: str,
        equity: Decimal | int | str,
        *,
        source: str = SOURCE_READONLY_DEMO,
        tags: Sequence[str] = (),
    ) -> EquityRow:
        stamp = normalize_timestamp(captured_at)
        amount = _decimal(equity, "equity")
        if not isinstance(source, str) or not source.strip() or source.strip() != source:
            raise EquityStoreError("source must be a non-empty trimmed string")
        normalized_tags = tuple(tag.strip() for tag in tags)
        if any(not tag for tag in normalized_tags):
            raise EquityStoreError("tags must be non-empty strings")
        utc_date = stamp[:10]
        with self._transaction():
            self._conn.execute(
                """
                INSERT INTO equity_snapshots(captured_at, utc_date, equity, source, tags_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (stamp, utc_date, format(amount, "f"), source, json.dumps(list(normalized_tags))),
            )
        return EquityRow(stamp, utc_date, amount, source, normalized_tags)

    def last_before(self, instant: str) -> EquityRow | None:
        stamp = normalize_timestamp(instant, "instant")
        with self._lock:
            row = self._conn.execute(
                """
                SELECT captured_at, utc_date, equity, source, tags_json
                FROM equity_snapshots
                WHERE captured_at < ?
                ORDER BY captured_at DESC, snapshot_id DESC
                LIMIT 1
                """,
                (stamp,),
            ).fetchone()
        return None if row is None else self._from_row(row)

    def max_equity(self) -> Decimal | None:
        with self._lock:
            rows = self._conn.execute("SELECT equity FROM equity_snapshots").fetchall()
        values = tuple(_decimal(row["equity"], "equity") for row in rows)
        return max(values) if values else None

    def last_tagged(self, tag: str) -> EquityRow | None:
        if not isinstance(tag, str) or not tag.strip():
            raise EquityStoreError("tag must be a non-empty string")
        needle = tag.strip()
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT captured_at, utc_date, equity, source, tags_json
                FROM equity_snapshots
                ORDER BY captured_at DESC, snapshot_id DESC
                """
            ).fetchall()
        for row in rows:
            record = self._from_row(row)
            if needle in record.tags:
                return record
        return None

    def _from_row(self, row: sqlite3.Row) -> EquityRow:
        tags = json.loads(row["tags_json"])
        if not isinstance(tags, list):
            tags = []
        return EquityRow(
            captured_at=row["captured_at"],
            utc_date=row["utc_date"],
            equity=_decimal(row["equity"], "equity"),
            source=row["source"],
            tags=tuple(str(tag) for tag in tags),
        )
