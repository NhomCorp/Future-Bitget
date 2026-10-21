"""Append-only local ledger and fail-closed zone state transitions.

This module is for local Demo/dry-run simulation only. It never calls the
exchange or sends/cancels orders.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Callable, Optional

try:
    from .zone_risk import RiskDecision, ZoneRiskConfig, ZoneRiskSnapshot, evaluate
except ImportError:
    from zone_risk import RiskDecision, ZoneRiskConfig, ZoneRiskSnapshot, evaluate


ACTIVE = "ACTIVE"
STOPPING = "STOPPING"
UNKNOWN = "UNKNOWN"
CLOSED = "CLOSED"


def _json_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return {key: _json_value(val) for key, val in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _json_value(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(val) for val in value]
    return value


class AppendOnlyLedger:
    """JSONL event sink; creates a new file or appends, never truncates."""

    def __init__(self, path: str):
        self.path = os.path.abspath(path)

    def append(self, event: dict) -> None:
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        record = {"ts_ms": int(time.time() * 1000), **_json_value(event)}
        with open(self.path, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())


@dataclass
class ZoneState:
    """Minimal in-memory state; durable lifecycle recovery is not implemented."""

    config: ZoneRiskConfig
    status: str = ACTIVE
    last_trigger_reason: Optional[str] = None
    last_net_pnl: Decimal = Decimal("0")
    last_mark_price: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.status not in {ACTIVE, STOPPING, UNKNOWN, CLOSED}:
            raise ValueError("invalid zone status")
        if self.status != ACTIVE and not self.last_trigger_reason:
            raise ValueError("non-active zone requires a trigger reason")


def process_snapshot(
    zone: ZoneState,
    snapshot: ZoneRiskSnapshot,
    ledger: AppendOnlyLedger,
    request_stop: Callable[[str], None],
) -> RiskDecision:
    """Record a reconcile snapshot and request a simulated stop once.

    The callback represents a local dry-run intent only. It must not be wired
    to a live exchange adapter. Callback errors move the zone to UNKNOWN.
    """
    decision = evaluate(zone.config, snapshot)
    zone.last_net_pnl = decision.net_pnl
    zone.last_mark_price = snapshot.mark_price
    ledger.append({
        "event": "RISK_EVALUATED",
        "zone_id": zone.config.zone_id,
        "symbol": zone.config.symbol,
        "side": zone.config.side,
        "status": zone.status,
        "net_pnl": decision.net_pnl,
        "mark_price": snapshot.mark_price,
        "price_stop": decision.price_stop,
        "loss_budget_hit": decision.loss_budget_hit,
        "price_sl_hit": decision.price_sl_hit,
        "reason": decision.reason,
    })
    if zone.status != ACTIVE or not decision.triggered:
        return decision

    zone.status = STOPPING
    zone.last_trigger_reason = decision.reason
    ledger.append({
        "event": "ZONE_STOP_REQUESTED_DRY_RUN",
        "zone_id": zone.config.zone_id,
        "reason": decision.reason,
        "net_pnl": decision.net_pnl,
        "mark_price": snapshot.mark_price,
    })
    try:
        request_stop(decision.reason)
    except Exception as exc:
        zone.status = UNKNOWN
        ledger.append({
            "event": "ZONE_STATE_UNKNOWN",
            "zone_id": zone.config.zone_id,
            "reason": decision.reason,
            "error_type": type(exc).__name__,
        })
    return decision


def mark_closed(zone: ZoneState, remaining_size: Decimal, ledger: AppendOnlyLedger) -> None:
    """Close local zone after a caller has reconciled a zero remaining size."""
    size = Decimal(str(remaining_size))
    if zone.status != STOPPING:
        raise ValueError("only a stopping zone can be closed")
    if size != 0:
        raise ValueError("zone cannot close while position size remains")
    zone.status = CLOSED
    ledger.append({
        "event": "ZONE_CLOSED_DRY_RUN",
        "zone_id": zone.config.zone_id,
        "reason": zone.last_trigger_reason,
    })


def record_unknown(zone: ZoneState, ledger: AppendOnlyLedger, reason: str) -> None:
    """Fail closed when reconcile cannot establish the exchange state."""
    if zone.status == CLOSED:
        raise ValueError("closed zone cannot become unknown")
    zone.status = UNKNOWN
    zone.last_trigger_reason = zone.last_trigger_reason or reason
    ledger.append({
        "event": "ZONE_STATE_UNKNOWN",
        "zone_id": zone.config.zone_id,
        "reason": zone.last_trigger_reason,
    })
