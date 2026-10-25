"""Local protection clock, separate from the paper scan review interval.

One tick reads an injected observation (mark, fills, SL, UNKNOWN, kill) and
may reconcile or record a dry-run emergency close. This module never POSTs to
an exchange, never calls the paper scan agent, and never waits for
``position_review_interval``.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Mapping

from executor.zone_executor import IntentError, IntentRole, RiskTrigger, ZoneExecutor, ZoneOrderSpec
from trader.zone_risk import ZoneRiskConfig, ZoneRiskSnapshot, evaluate
from .reconcile import PaperReconcile, ReconcileError, ReconcileObservation, ReconcileResult

PROTECT_RAN_EVENT = "PROTECT_RAN"
PROTECT_TRIGGERED_EVENT = "PROTECT_TRIGGERED"
PROTECT_UNKNOWN_EVENT = "PROTECT_UNKNOWN"
PROTECT_STALE_EVENT = "PROTECT_STALE"
PROTECT_SKIPPED_EVENT = "PROTECT_SKIPPED"
EMERGENCY_FLATTEN_EVENT = "EMERGENCY_FLATTEN_RECORDED"

REASON_RAN = "PROTECT_RAN"
REASON_TRIGGERED = "PROTECT_TRIGGERED"
REASON_UNKNOWN = "PROTECT_UNKNOWN"
REASON_STALE = "PROTECT_STALE"
REASON_SKIPPED = "PROTECT_SKIPPED"

_TRIGGER_BY_REASON = {
    "PRICE_SL": RiskTrigger.PRICE_SL,
    "LOSS_BUDGET": RiskTrigger.LOSS_BUDGET,
    "BOTH": RiskTrigger.BOTH,
}


class ProtectClockError(ValueError):
    """Raised when a local protection observation cannot be applied safely."""


def _decimal(value: Any, name: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ProtectClockError(f"{name} must be a decimal") from exc
    if not result.is_finite():
        raise ProtectClockError(f"{name} must be finite")
    return result


def _optional_decimal(value: Any, name: str) -> Decimal | None:
    if value is None or value == "":
        return None
    return _decimal(value, name)


@dataclass(frozen=True)
class ProtectObservation:
    mark_price: Decimal | None = None
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")
    funding_paid: Decimal = Decimal("0")
    funding_received: Decimal = Decimal("0")
    fills: tuple[ReconcileObservation, ...] = ()
    unknown: bool = False
    kill_switch: bool = False
    stale: bool = False
    position_quantity: Decimal | None = None
    position_side: str | None = None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProtectObservation":
        if not isinstance(value, Mapping):
            raise ProtectClockError("observation must be an object")
        fills: list[ReconcileObservation] = []
        raw_fills = value.get("fills") or ()
        if not isinstance(raw_fills, (list, tuple)):
            raise ProtectClockError("fills must be a list")
        for item in raw_fills:
            if not isinstance(item, Mapping):
                raise ProtectClockError("fill observation must be an object")
            fills.append(
                ReconcileObservation(
                    client_oid=str(item.get("client_oid") or ""),
                    found=item.get("found"),
                    filled_quantity=item.get("filled_quantity"),
                    timeout=bool(item.get("timeout", False)),
                )
            )
        side = value.get("position_side")
        return cls(
            mark_price=_optional_decimal(value.get("mark_price"), "mark_price"),
            realized_pnl=_decimal(value.get("realized_pnl", "0"), "realized_pnl"),
            unrealized_pnl=_decimal(value.get("unrealized_pnl", "0"), "unrealized_pnl"),
            fees=_decimal(value.get("fees", "0"), "fees"),
            funding_paid=_decimal(value.get("funding_paid", "0"), "funding_paid"),
            funding_received=_decimal(value.get("funding_received", "0"), "funding_received"),
            fills=tuple(fills),
            unknown=bool(value.get("unknown", False)),
            kill_switch=bool(value.get("kill_switch", False)),
            stale=bool(value.get("stale", False)),
            position_quantity=_optional_decimal(value.get("position_quantity"), "position_quantity"),
            position_side=None if side in (None, "") else str(side),
        )


@dataclass(frozen=True)
class ProtectClockResult:
    ran: bool
    reason_code: str
    triggered: bool
    emergency_close_client_oid: str | None = None
    unknown: bool = False
    kill_switch: bool = False
    reconcile_results: tuple[ReconcileResult, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "dry_run": True,
            "emergency_close_client_oid": self.emergency_close_client_oid,
            "exchange_post": False,
            "kill_switch": self.kill_switch,
            "ran": self.ran,
            "reason_code": self.reason_code,
            "reconcile_count": len(self.reconcile_results),
            "triggered": self.triggered,
            "unknown": self.unknown,
        }


def _append(store: Any, zone_id: str, event: str, payload: Mapping[str, Any]) -> None:
    store.append_agent_event(zone_id, event, dict(payload))


def _already_flattened(store: Any, zone_id: str) -> bool:
    getter = getattr(store, "agent_events", None)
    if getter is None:
        return False
    return any(event.get("event") == EMERGENCY_FLATTEN_EVENT for event in getter(zone_id))


def _risk_config(zone: Any) -> ZoneRiskConfig:
    config = zone.config if isinstance(getattr(zone, "config", None), Mapping) else {}
    return ZoneRiskConfig(
        zone_id=zone.zone_id,
        symbol=zone.symbol,
        side=zone.side,
        ref_price=zone.ref_price,
        zone_loss_limit_usdt=config.get("zone_loss_limit_usdt"),
        sl_pct=config.get("sl_pct"),
    )


def _ensure_executor(store: Any, zone: Any, observation: ProtectObservation, executor: ZoneExecutor | None) -> ZoneExecutor:
    if executor is None:
        try:
            executor = ZoneExecutor.restore(store, zone.zone_id)
        except IntentError:
            executor = ZoneExecutor(store)
    try:
        executor.snapshot(zone.zone_id)
    except IntentError:
        quantity = observation.position_quantity or Decimal("1")
        side = observation.position_side or zone.side
        order_side = "buy" if side == "long" else "sell"
        executor.create_zone(
            zone.zone_id,
            [
                ZoneOrderSpec(
                    IntentRole.ENTRY,
                    0,
                    quantity,
                    zone.ref_price,
                    order_side,
                    position_side=side,
                )
            ],
            position_quantity=quantity,
            position_side=side,
        )
    if observation.position_quantity is not None:
        executor.set_position(zone.zone_id, observation.position_quantity, observation.position_side or zone.side)
    return executor


def _flatten(
    store: Any,
    executor: ZoneExecutor,
    zone_id: str,
    trigger: RiskTrigger,
    *,
    record_flatten_event: bool,
) -> str | None:
    action = executor.on_risk_trigger(zone_id, trigger)
    if record_flatten_event and not _already_flattened(store, zone_id):
        _append(
            store,
            zone_id,
            EMERGENCY_FLATTEN_EVENT,
            {
                "dry_run": True,
                "emergency_close_client_oid": action.emergency_close_client_oid,
                "cancelled_client_oids": list(action.cancelled_client_oids),
            },
        )
    return action.emergency_close_client_oid


def _apply_fills(store: Any, observation: ProtectObservation) -> tuple[tuple[ReconcileResult, ...], bool]:
    if not observation.fills:
        return (), False
    reconcilers = PaperReconcile(store)
    results: list[ReconcileResult] = []
    unknown = False
    for fill in observation.fills:
        try:
            record = reconcilers.apply(fill)
        except ReconcileError:
            unknown = True
            continue
        results.append(record)
        if record.requires_reconcile:
            unknown = True
    return tuple(results), unknown


def tick(
    store: Any,
    zone_id: str,
    observation: ProtectObservation,
    *,
    now: str,
    executor: ZoneExecutor | None = None,
) -> ProtectClockResult:
    """One local protection tick. Never calls AI and never POSTs."""
    try:
        zone = store.zone_store.get_zone(zone_id)
    except Exception:
        zone = None
    if zone is None:
        _append(
            store,
            zone_id,
            PROTECT_SKIPPED_EVENT,
            {"reason_code": REASON_SKIPPED, "dry_run": True, "observed_at": now},
        )
        return ProtectClockResult(ran=False, reason_code=REASON_SKIPPED, triggered=False)

    reconcile_results, fill_unknown = _apply_fills(store, observation)
    unknown = bool(observation.unknown or fill_unknown)
    skip_sl = bool(observation.stale or unknown or observation.mark_price is None)
    triggered = False
    emergency_oid: str | None = None
    local_executor: ZoneExecutor | None = None

    def flatten(trigger: RiskTrigger, *, record_flatten_event: bool) -> None:
        nonlocal local_executor, emergency_oid, triggered
        local_executor = _ensure_executor(store, zone, observation, local_executor or executor)
        emergency_oid = _flatten(
            store,
            local_executor,
            zone_id,
            trigger,
            record_flatten_event=record_flatten_event,
        )
        triggered = True

    if observation.kill_switch:
        flatten(RiskTrigger.LOSS_BUDGET, record_flatten_event=True)

    if not skip_sl:
        decision = evaluate(
            _risk_config(zone),
            ZoneRiskSnapshot(
                realized_pnl=observation.realized_pnl,
                unrealized_pnl=observation.unrealized_pnl,
                fees=observation.fees,
                funding_paid=observation.funding_paid,
                funding_received=observation.funding_received,
                mark_price=observation.mark_price,
            ),
        )
        if decision.triggered:
            flatten(_TRIGGER_BY_REASON[decision.reason], record_flatten_event=False)

    if observation.stale:
        reason = REASON_STALE if not triggered else REASON_TRIGGERED
        event = PROTECT_TRIGGERED_EVENT if triggered else PROTECT_STALE_EVENT
        _append(
            store,
            zone_id,
            event,
            {
                "reason_code": reason,
                "dry_run": True,
                "emergency_close_client_oid": emergency_oid,
                "kill_switch": observation.kill_switch,
                "stale": True,
            },
        )
        if not triggered:
            return ProtectClockResult(
                ran=True,
                reason_code=REASON_STALE,
                triggered=False,
                unknown=unknown,
                kill_switch=observation.kill_switch,
                reconcile_results=reconcile_results,
            )
        return ProtectClockResult(
            ran=True,
            reason_code=REASON_TRIGGERED,
            triggered=True,
            emergency_close_client_oid=emergency_oid,
            unknown=unknown,
            kill_switch=observation.kill_switch,
            reconcile_results=reconcile_results,
        )

    if triggered:
        _append(
            store,
            zone_id,
            PROTECT_TRIGGERED_EVENT,
            {
                "reason_code": REASON_TRIGGERED,
                "dry_run": True,
                "emergency_close_client_oid": emergency_oid,
                "kill_switch": observation.kill_switch,
                "unknown": unknown,
            },
        )
        return ProtectClockResult(
            ran=True,
            reason_code=REASON_TRIGGERED,
            triggered=True,
            emergency_close_client_oid=emergency_oid,
            unknown=unknown,
            kill_switch=observation.kill_switch,
            reconcile_results=reconcile_results,
        )

    if unknown or (observation.mark_price is None and not reconcile_results):
        _append(
            store,
            zone_id,
            PROTECT_UNKNOWN_EVENT,
            {"reason_code": REASON_UNKNOWN, "dry_run": True, "unknown": True, "observed_at": now},
        )
        return ProtectClockResult(
            ran=True,
            reason_code=REASON_UNKNOWN,
            triggered=False,
            unknown=True,
            reconcile_results=reconcile_results,
        )

    _append(store, zone_id, PROTECT_RAN_EVENT, {"reason_code": REASON_RAN, "dry_run": True})
    return ProtectClockResult(
        ran=True,
        reason_code=REASON_RAN,
        triggered=False,
        reconcile_results=reconcile_results,
    )


def run_loop(
    store: Any,
    zone_id: str,
    observation: ProtectObservation,
    *,
    now_fn: Callable[[], str],
    sleep: Callable[[float], None],
    poll_seconds: float,
    max_ticks: int,
    executor: ZoneExecutor | None = None,
) -> list[ProtectClockResult]:
    """Repeat ``tick`` locally. Sleep is injected; this is not a scan clock."""
    if max_ticks < 1:
        raise ProtectClockError("max_ticks must be >= 1")
    if poll_seconds <= 0:
        raise ProtectClockError("poll_seconds must be positive")
    results: list[ProtectClockResult] = []
    for index in range(max_ticks):
        results.append(tick(store, zone_id, observation, now=now_fn(), executor=executor))
        if index + 1 < max_ticks:
            sleep(poll_seconds)
    return results
