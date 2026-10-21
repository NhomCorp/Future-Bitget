"""Immutable mandate contract for paper trading.

This module owns no exchange side effects and never exposes API credentials.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


class MandateError(ValueError):
    """Raised when a mandate violates a local safety invariant."""


def _decimal(value: Decimal | int | str, name: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, (bool, float)):
        raise MandateError(f"{name} must be Decimal, integer, or decimal string")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise MandateError(f"{name} must be a decimal") from exc
    if not result.is_finite() or (positive and result <= 0):
        raise MandateError(f"{name} must be finite" + (" and positive" if positive else ""))
    return result


def _timestamp(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MandateError(f"{name} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MandateError(f"{name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise MandateError(f"{name} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _strings(values: tuple[str, ...], name: str, *, lower: bool = False) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise MandateError(f"{name} must be a collection")
    normalized = tuple((value.strip().lower() if lower else value.strip().upper()) for value in values)
    if not normalized or any(not value for value in normalized) or len(set(normalized)) != len(normalized):
        raise MandateError(f"{name} must be non-empty and unique")
    return normalized


@dataclass(frozen=True)
class TradingMandate:
    """Versioned limits that a proposal cannot modify."""

    mandate_id: str
    version: int
    zone_id: str
    allowed_symbols: tuple[str, ...]
    allowed_sides: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    max_size: Decimal
    max_exposure: Decimal
    loss_budget: Decimal
    max_order_risk: Decimal
    valid_from: str
    valid_until: str
    state: str = "ENABLED"
    require_stop_loss: bool = True

    def __post_init__(self) -> None:
        for name in ("mandate_id", "zone_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or value.strip() != value:
                raise MandateError(f"{name} must be a non-empty trimmed string")
        if isinstance(self.version, bool) or self.version < 1:
            raise MandateError("version must be a positive integer")
        symbols = _strings(self.allowed_symbols, "allowed_symbols")
        sides = _strings(self.allowed_sides, "allowed_sides", lower=True)
        actions = _strings(self.allowed_actions, "allowed_actions")
        if not set(sides) <= {"long", "short"}:
            raise MandateError("allowed_sides may contain only long or short")
        if not set(actions) <= {"OPEN", "CLOSE", "REDUCE", "HOLD", "NO_TRADE"}:
            raise MandateError("allowed_actions contains an unsupported action")
        object.__setattr__(self, "allowed_symbols", symbols)
        object.__setattr__(self, "allowed_sides", sides)
        object.__setattr__(self, "allowed_actions", actions)
        for name in ("max_size", "max_exposure", "loss_budget", "max_order_risk"):
            value = _decimal(getattr(self, name), name)
            if value < 0:
                raise MandateError(f"{name} must be non-negative")
            object.__setattr__(self, name, value)
        if self.max_size == 0 or self.max_exposure == 0 or self.loss_budget == 0 or self.max_order_risk == 0:
            raise MandateError("limits must be greater than zero")
        object.__setattr__(self, "valid_from", _timestamp(self.valid_from, "valid_from"))
        object.__setattr__(self, "valid_until", _timestamp(self.valid_until, "valid_until"))
        if self.valid_until <= self.valid_from:
            raise MandateError("valid_until must follow valid_from")
        state = self.state.upper()
        if state not in {"ENABLED", "PAUSED", "REVOKED", "EXPIRED"}:
            raise MandateError("unsupported mandate state")
        object.__setattr__(self, "state", state)
        if not isinstance(self.require_stop_loss, bool):
            raise MandateError("require_stop_loss must be boolean")

    def is_active(self, now: str) -> bool:
        current = _timestamp(now, "now")
        return self.state == "ENABLED" and self.valid_from <= current < self.valid_until

    def to_dict(self) -> dict[str, Any]:
        return {
            "mandate_id": self.mandate_id,
            "version": self.version,
            "zone_id": self.zone_id,
            "allowed_symbols": list(self.allowed_symbols),
            "allowed_sides": list(self.allowed_sides),
            "allowed_actions": list(self.allowed_actions),
            "max_size": format(self.max_size, "f"),
            "max_exposure": format(self.max_exposure, "f"),
            "loss_budget": format(self.loss_budget, "f"),
            "max_order_risk": format(self.max_order_risk, "f"),
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "state": self.state,
            "require_stop_loss": self.require_stop_loss,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TradingMandate":
        return cls(
            mandate_id=value["mandate_id"],
            version=value["version"],
            zone_id=value["zone_id"],
            allowed_symbols=tuple(value["allowed_symbols"]),
            allowed_sides=tuple(value["allowed_sides"]),
            allowed_actions=tuple(value["allowed_actions"]),
            max_size=_decimal(value["max_size"], "max_size"),
            max_exposure=_decimal(value["max_exposure"], "max_exposure"),
            loss_budget=_decimal(value["loss_budget"], "loss_budget"),
            max_order_risk=_decimal(value["max_order_risk"], "max_order_risk"),
            valid_from=value["valid_from"],
            valid_until=value["valid_until"],
            state=value.get("state", "ENABLED"),
            require_stop_loss=value.get("require_stop_loss", True),
        )
