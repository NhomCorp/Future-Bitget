"""Pure per-zone risk checks for Demo/dry-run operation.

This module does not call Bitget and cannot place orders. Values used for
risk decisions are Decimal to keep the boundary and trigger calculations
reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional


ZERO = Decimal("0")


def dec(value: object, field: str) -> Decimal:
    """Convert a config or exchange value without accepting floats silently."""
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a decimal value")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be a decimal value") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def optional_positive(value: object, field: str) -> Optional[Decimal]:
    if value is None:
        return None
    result = dec(value, field)
    if result <= ZERO:
        raise ValueError(f"{field} must be greater than zero when enabled")
    return result


@dataclass(frozen=True)
class ZoneRiskConfig:
    """Immutable risk thresholds captured when a zone is opened."""

    zone_id: str
    symbol: str
    side: str
    ref_price: Decimal
    zone_loss_limit_usdt: Optional[Decimal] = None
    sl_pct: Optional[Decimal] = None

    def __post_init__(self) -> None:
        if not self.zone_id:
            raise ValueError("zone_id is required")
        if not self.symbol:
            raise ValueError("symbol is required")
        if self.side not in {"long", "short"}:
            raise ValueError("side must be long or short")
        ref_price = dec(self.ref_price, "ref_price")
        if ref_price <= ZERO:
            raise ValueError("ref_price must be greater than zero")
        loss_limit = optional_positive(self.zone_loss_limit_usdt, "zone_loss_limit_usdt")
        sl_pct = optional_positive(self.sl_pct, "sl_pct")
        if loss_limit is None and sl_pct is None:
            raise ValueError("at least one zone risk option must be enabled")
        object.__setattr__(self, "ref_price", ref_price)
        object.__setattr__(self, "zone_loss_limit_usdt", loss_limit)
        object.__setattr__(self, "sl_pct", sl_pct)

    @property
    def price_stop(self) -> Optional[Decimal]:
        if self.sl_pct is None:
            return None
        direction = Decimal("-1") if self.side == "long" else Decimal("1")
        return self.ref_price * (Decimal("1") + direction * self.sl_pct / Decimal("100"))


@dataclass(frozen=True)
class ZoneRiskSnapshot:
    """One reconcile input; all PnL components are episode totals."""

    realized_pnl: Decimal = ZERO
    unrealized_pnl: Decimal = ZERO
    fees: Decimal = ZERO
    funding_paid: Decimal = ZERO
    funding_received: Decimal = ZERO
    mark_price: Decimal = ZERO

    def __post_init__(self) -> None:
        for field in (
            "realized_pnl",
            "unrealized_pnl",
            "fees",
            "funding_paid",
            "funding_received",
            "mark_price",
        ):
            value = dec(getattr(self, field), field)
            if field in {"fees", "funding_paid", "funding_received"} and value < ZERO:
                raise ValueError(f"{field} cannot be negative")
            object.__setattr__(self, field, value)

    @property
    def net_pnl(self) -> Decimal:
        return (
            self.realized_pnl
            + self.unrealized_pnl
            - self.fees
            - self.funding_paid
            + self.funding_received
        )


@dataclass(frozen=True)
class RiskDecision:
    """Pure result of evaluating one snapshot against one zone config."""

    net_pnl: Decimal
    loss_budget_hit: bool
    price_sl_hit: bool
    reason: Optional[str]
    price_stop: Optional[Decimal]

    @property
    def triggered(self) -> bool:
        return self.reason is not None


def evaluate(config: ZoneRiskConfig, snapshot: ZoneRiskSnapshot) -> RiskDecision:
    """Evaluate both enabled options using OR semantics."""
    loss_hit = (
        config.zone_loss_limit_usdt is not None
        and snapshot.net_pnl <= -config.zone_loss_limit_usdt
    )
    stop = config.price_stop
    if stop is None:
        price_hit = False
    elif config.side == "long":
        price_hit = snapshot.mark_price <= stop
    else:
        price_hit = snapshot.mark_price >= stop

    if loss_hit and price_hit:
        reason = "BOTH"
    elif loss_hit:
        reason = "LOSS_BUDGET"
    elif price_hit:
        reason = "PRICE_SL"
    else:
        reason = None
    return RiskDecision(
        net_pnl=snapshot.net_pnl,
        loss_budget_hit=loss_hit,
        price_sl_hit=price_hit,
        reason=reason,
        price_stop=stop,
    )
