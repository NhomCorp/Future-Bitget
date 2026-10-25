"""Append-only mandate versions and local recovery after process restart.

This module reads and writes the existing P1 SQLite bridge. It never calls an
exchange and never resets a consumed loss budget.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .mandate import TradingMandate


class MandateStoreError(ValueError):
    """Raised when a local mandate or budget record cannot be recovered safely."""


UNKNOWN_PAPER_STATES = frozenset({"paper_unknown", "unknown"})
OPEN_PAPER_STATES = frozenset({
    "paper_pending",
    "paper_open",
    "paper_partial",
    "paper_unknown",
    "unknown",
})


def _decimal(value: Any, name: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise MandateStoreError(f"{name} must be a decimal") from exc
    if not result.is_finite():
        raise MandateStoreError(f"{name} must be finite")
    return result


@dataclass(frozen=True)
class RecoverySnapshot:
    """Materialized local state loaded before a new AI or intent cycle."""

    zone_id: str
    mandate: TradingMandate | None
    paper_intents: tuple[dict[str, Any], ...]
    pending_or_unknown: tuple[dict[str, Any], ...]
    remaining_loss_budget: Decimal | None
    consumed_loss_budget: Decimal

    def paper_intent(self, client_oid: str) -> dict[str, Any] | None:
        for item in self.paper_intents:
            if item.get("client_oid") == client_oid:
                return item
        return None

    def unknown_for(self, client_oid: str) -> dict[str, Any] | None:
        item = self.paper_intent(client_oid)
        if item is None or item.get("state") not in UNKNOWN_PAPER_STATES:
            return None
        return item

    def has_unknown(self) -> bool:
        return any(item.get("state") in UNKNOWN_PAPER_STATES for item in self.pending_or_unknown)


class MandateStore:
    """Facade over P1IntegrationStore for immutable mandate versions."""

    def __init__(self, store: Any):
        self.store = store

    def save(self, mandate: TradingMandate) -> None:
        self.store.save_mandate(mandate.to_dict())

    def get(self, mandate_id: str, version: int) -> TradingMandate | None:
        raw = self.store.get_mandate(mandate_id, version)
        return None if raw is None else TradingMandate.from_dict(raw)

    def latest(self, mandate_id: str) -> TradingMandate | None:
        getter = getattr(self.store, "latest_mandate", None)
        raw = getter(mandate_id) if getter is not None else None
        if raw is None:
            versions = getattr(self.store, "mandate_versions", lambda _id: [])(mandate_id)
            if not versions:
                return None
            raw = self.store.get_mandate(mandate_id, versions[-1])
        return None if raw is None else TradingMandate.from_dict(raw)

    def versions(self, mandate_id: str) -> tuple[int, ...]:
        listing = getattr(self.store, "mandate_versions", None)
        if listing is None:
            return ()
        return tuple(listing(mandate_id))


def recover_session(
    store: Any,
    zone_id: str,
    mandate_id: str | None = None,
    *,
    original_loss_budget: Decimal | None = None,
) -> RecoverySnapshot:
    """Load mandate, paper intents and remaining budget after a local restart."""
    mandate = MandateStore(store).latest(mandate_id) if mandate_id else None
    intents = tuple(store.paper_intents(zone_id))
    pending = tuple(item for item in intents if item.get("state") in OPEN_PAPER_STATES)
    last = getattr(store, "latest_budget", lambda _zone: None)(zone_id)
    if last is not None:
        remaining = _decimal(last.get("remaining"), "remaining")
        consumed = _decimal(last.get("consumed", "0"), "consumed")
    elif mandate is not None:
        remaining = mandate.loss_budget
        consumed = Decimal("0")
    elif original_loss_budget is not None:
        remaining = _decimal(original_loss_budget, "original_loss_budget")
        consumed = Decimal("0")
    else:
        remaining = None
        consumed = Decimal("0")
    return RecoverySnapshot(
        zone_id=zone_id,
        mandate=mandate,
        paper_intents=intents,
        pending_or_unknown=pending,
        remaining_loss_budget=remaining,
        consumed_loss_budget=consumed,
    )


def consume_loss_budget(
    store: Any,
    *,
    zone_id: str,
    mandate_id: str,
    amount: Decimal | int | str,
    reason: str,
    original_loss_budget: Decimal | None = None,
) -> Decimal:
    """Append a consume-only budget event. Restart must not restore spent budget."""
    delta = _decimal(amount, "amount")
    if delta <= 0:
        raise MandateStoreError("budget consume amount must be positive")
    recovered = recover_session(store, zone_id, mandate_id, original_loss_budget=original_loss_budget)
    if recovered.remaining_loss_budget is None:
        raise MandateStoreError("cannot consume budget without a starting remaining value")
    remaining = recovered.remaining_loss_budget - delta
    if remaining < 0:
        remaining = Decimal("0")
    consumed = recovered.consumed_loss_budget + (recovered.remaining_loss_budget - remaining)
    store.append_budget_event(
        {
            "zone_id": zone_id,
            "mandate_id": mandate_id,
            "delta": format(delta, "f"),
            "consumed": format(consumed, "f"),
            "remaining": format(remaining, "f"),
            "reason": reason,
            "dry_run": True,
        }
    )
    return remaining
