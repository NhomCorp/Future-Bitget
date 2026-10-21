"""Minimal persistence protocol for the standalone zone executor.

P1 can provide a SQLite/file implementation later.  This protocol deliberately
has no storage side effects by itself and keeps the executor integration clear.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol


class ZoneStore(Protocol):
    """Persistence methods consumed by :class:`ZoneExecutor`."""

    def save_intent(self, record: Mapping[str, Any]) -> None:
        """Upsert one deterministic intent record."""

    def append_event(self, event: Mapping[str, Any]) -> None:
        """Append one local state transition event."""

    def save_zone(self, snapshot: Mapping[str, Any]) -> None:
        """Upsert the current zone snapshot."""


__all__ = ["ZoneStore"]
