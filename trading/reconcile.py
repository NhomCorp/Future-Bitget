"""Local paper reconcile boundary. No exchange requests.

Classify a caller-supplied observation into confirmed_open, confirmed_absent,
partial, or unknown. Timeout and indeterminate results stay UNKNOWN until a
later observation arrives. This is not a Demo dispatcher.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from executor.zone_executor import ZoneExecutor

from .mandate_store import UNKNOWN_PAPER_STATES


class ReconcileError(ValueError):
    """Raised when a local observation cannot be applied safely."""


RECONCILE_RESULTS = frozenset({"confirmed_open", "confirmed_absent", "partial", "unknown"})
_STATE_BY_RESULT = {
    "unknown": "paper_unknown",
    "confirmed_absent": "paper_absent",
    "partial": "paper_partial",
}


def _decimal(value: Any, name: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ReconcileError(f"{name} must be a decimal") from exc
    if not result.is_finite() or result < 0:
        raise ReconcileError(f"{name} must be a non-negative finite decimal")
    return result


@dataclass(frozen=True)
class ReconcileObservation:
    client_oid: str
    found: bool | None = None
    filled_quantity: Decimal | int | str | None = None
    timeout: bool = False

    def normalized_filled(self) -> Decimal | None:
        if self.filled_quantity is None:
            return None
        return _decimal(self.filled_quantity, "filled_quantity")


@dataclass(frozen=True)
class ReconcileResult:
    client_oid: str
    result: str
    state: str
    filled_quantity: Decimal
    remaining_quantity: Decimal
    requires_reconcile: bool

    def to_record(self) -> dict[str, Any]:
        return {
            "client_oid": self.client_oid,
            "result": self.result,
            "state": self.state,
            "filled_quantity": format(self.filled_quantity, "f"),
            "remaining_quantity": format(self.remaining_quantity, "f"),
            "requires_reconcile": self.requires_reconcile,
            "dry_run": True,
        }


def classify(
    observation: ReconcileObservation,
    *,
    quantity: Decimal,
    filled_so_far: Decimal,
) -> str:
    """Return one of the four local reconcile results. Never contacts an exchange."""
    if observation.timeout or observation.found is None:
        return "unknown"
    filled = observation.normalized_filled()
    if filled is None:
        filled = Decimal("0") if observation.found is False else filled_so_far
    if filled > quantity:
        raise ReconcileError("filled_quantity cannot exceed intent quantity")
    if filled < filled_so_far:
        raise ReconcileError("filled quantity cannot move backwards")
    if observation.found is False:
        return "confirmed_absent"
    if Decimal("0") < filled < quantity:
        return "partial"
    return "confirmed_open"


def _state_for(result: str, filled: Decimal, quantity: Decimal) -> str:
    if result != "confirmed_open":
        return _STATE_BY_RESULT[result]
    return "paper_filled" if filled >= quantity else "paper_open"


class PaperReconcile:
    """Apply paper observations to persisted intents and append audit events."""

    def __init__(self, store: Any):
        self.store = store

    def apply(self, observation: ReconcileObservation) -> ReconcileResult:
        client_oid = observation.client_oid.strip()
        if not client_oid:
            raise ReconcileError("client_oid is required")
        intent = self.store.get_paper_intent(client_oid)
        if intent is None:
            raise ReconcileError(f"paper intent not found: {client_oid}")
        quantity = _decimal(intent["quantity"], "quantity")
        filled_so_far = _decimal(intent.get("filled_quantity", "0"), "filled_quantity")
        result = classify(observation, quantity=quantity, filled_so_far=filled_so_far)
        filled = observation.normalized_filled()
        if filled is None:
            filled = filled_so_far if result != "confirmed_absent" else filled_so_far
        if result == "confirmed_open" and observation.found is True and observation.normalized_filled() is None:
            filled = filled_so_far
        remaining = max(Decimal("0"), quantity - filled)
        state = _state_for(result, filled, quantity)
        updated = self.store.update_paper_intent_runtime(
            client_oid,
            {
                "state": state,
                "filled_quantity": filled,
                "remaining_quantity": remaining,
                "last_event": result,
                "last_reconcile": result,
            },
        )
        record = ReconcileResult(
            client_oid=client_oid,
            result=result,
            state=updated["state"],
            filled_quantity=_decimal(updated["filled_quantity"], "filled_quantity"),
            remaining_quantity=_decimal(updated["remaining_quantity"], "remaining_quantity"),
            requires_reconcile=result == "unknown",
        )
        self.store.append_agent_event(
            str(intent["zone_id"]),
            "RECONCILE_RESULT",
            record.to_record(),
        )
        if result == "unknown":
            self.store.append_agent_event(
                str(intent["zone_id"]),
                "RECONCILE_REQUIRED",
                {"client_oid": client_oid, "decision_id": intent.get("decision_id"), "dry_run": True},
            )
        return record

    def record_timeout(self, client_oid: str) -> ReconcileResult:
        return self.apply(ReconcileObservation(client_oid=client_oid, timeout=True))


def restore_executor(store: Any, zone_id: str) -> ZoneExecutor:
    """Rebuild a dry-run executor from SQLite after process restart."""
    return ZoneExecutor.restore(store, zone_id)


def blocks_new_intent(intent: Mapping[str, Any] | None) -> bool:
    return bool(intent) and str(intent.get("state", "")) in UNKNOWN_PAPER_STATES
