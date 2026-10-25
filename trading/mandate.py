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


AI_AUTONOMY_MODES = frozenset({"PROPOSAL_ONLY", "MANAGED_ZONE", "AUTONOMOUS_WITHIN_MANDATE"})
MANDATE_ACTIONS = frozenset({"OPEN", "CLOSE", "REDUCE", "HOLD", "NO_TRADE", "ADJUST_SL", "CANCEL"})
DAILY_LOSS_ACTIONS = frozenset({"FREEZE_ENTRY", "EMERGENCY_FLATTEN"})
MANDATE_STATES = frozenset({"ENABLED", "PAUSED", "COOLDOWN", "REVOKED", "EXPIRED"})
POSITION_REVIEW_INTERVAL_UNIT = "minutes"
POSITION_REVIEW_INTERVAL_MIN = 1
POSITION_REVIEW_INTERVAL_MAX = 240
POSITION_REVIEW_INTERVAL_SUGGESTIONS = (5, 15, 30, 60)


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
    daily_loss_limit: Decimal | None = None
    daily_loss_limit_pct: Decimal | None = None
    daily_loss_reference: str | None = None
    drawdown_limit: Decimal | None = None
    max_leverage: Decimal | None = None
    daily_loss_scope: str | None = None
    daily_loss_reset_time_utc: str = "00:00"
    drawdown_scope: str | None = None
    drawdown_reference: str | None = None
    drawdown_unit: str = "usdt"
    margin_mode: str = "isolated"
    entry_order_type: str = "limit"
    dca_order_type: str = "limit"
    take_profit_order_type: str = "limit"
    strategic_stop_mode: str = "required"
    emergency_order_type: str = "market_reduce_only"
    kill_switch_order_type: str = "market_reduce_only"
    state: str = "ENABLED"
    require_stop_loss: bool = True
    ai_autonomy: str | None = None
    granted_capital: Decimal | None = None
    capital_currency: str = "USDT"
    daily_loss_action: str | None = None
    max_consecutive_losses: int | None = None
    loss_streak_scope: str | None = None
    loss_streak_cooldown: str | None = None
    allow_average_down: bool = False
    position_review_interval: int | None = None

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
        if not set(actions) <= MANDATE_ACTIONS:
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
        for name in ("daily_loss_limit", "daily_loss_limit_pct", "drawdown_limit", "max_leverage"):
            value = getattr(self, name)
            if value is not None:
                value = _decimal(value, name, positive=True)
                object.__setattr__(self, name, value)
        for name in ("daily_loss_scope", "drawdown_scope", "drawdown_reference", "daily_loss_reference"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise MandateError(f"{name} must be non-empty when configured")
        if self.daily_loss_reset_time_utc != "00:00":
            raise MandateError("daily_loss_reset_time_utc must be 00:00 UTC")
        if self.daily_loss_reference != "day_start_equity":
            raise MandateError("daily_loss_reference must be day_start_equity")
        if self.drawdown_unit not in {"usdt", "pct"}:
            raise MandateError("drawdown_unit must be usdt or pct")
        if self.margin_mode.lower() != "isolated":
            raise MandateError("margin_mode must be isolated")
        object.__setattr__(self, "margin_mode", "isolated")
        for name in ("entry_order_type", "dca_order_type", "take_profit_order_type"):
            if getattr(self, name).lower() != "limit":
                raise MandateError(f"{name} must be limit")
            object.__setattr__(self, name, "limit")
        if self.strategic_stop_mode.lower() not in {"required", "optional", "disabled"}:
            raise MandateError("unsupported strategic_stop_mode")
        object.__setattr__(self, "strategic_stop_mode", self.strategic_stop_mode.lower())
        for name in ("emergency_order_type", "kill_switch_order_type"):
            if getattr(self, name).lower() != "market_reduce_only":
                raise MandateError(f"{name} must be market_reduce_only")
            object.__setattr__(self, name, "market_reduce_only")
        object.__setattr__(self, "valid_from", _timestamp(self.valid_from, "valid_from"))
        object.__setattr__(self, "valid_until", _timestamp(self.valid_until, "valid_until"))
        if self.valid_until <= self.valid_from:
            raise MandateError("valid_until must follow valid_from")
        state = self.state.upper()
        if state not in MANDATE_STATES:
            raise MandateError("unsupported mandate state")
        object.__setattr__(self, "state", state)
        if not isinstance(self.require_stop_loss, bool):
            raise MandateError("require_stop_loss must be boolean")
        if not isinstance(self.allow_average_down, bool):
            raise MandateError("allow_average_down must be boolean")
        if self.ai_autonomy is not None:
            autonomy = self.ai_autonomy.strip().upper()
            if autonomy not in AI_AUTONOMY_MODES:
                raise MandateError("unsupported ai_autonomy")
            object.__setattr__(self, "ai_autonomy", autonomy)
        if self.granted_capital is not None:
            object.__setattr__(self, "granted_capital", _decimal(self.granted_capital, "granted_capital", positive=True))
        currency = self.capital_currency.strip().upper()
        if not currency:
            raise MandateError("capital_currency must be a non-empty trimmed string")
        object.__setattr__(self, "capital_currency", currency)
        if self.daily_loss_action is not None:
            action = self.daily_loss_action.strip().upper()
            if action not in DAILY_LOSS_ACTIONS:
                raise MandateError("unsupported daily_loss_action")
            object.__setattr__(self, "daily_loss_action", action)
        if self.max_consecutive_losses is not None:
            if isinstance(self.max_consecutive_losses, bool) or not isinstance(self.max_consecutive_losses, int) or self.max_consecutive_losses < 1:
                raise MandateError("max_consecutive_losses must be a positive integer")
        for name in ("loss_streak_scope", "loss_streak_cooldown"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise MandateError(f"{name} must be non-empty when configured")
        if self.position_review_interval is not None:
            interval = self.position_review_interval
            if isinstance(interval, bool) or not isinstance(interval, int):
                raise MandateError("position_review_interval must be an integer number of minutes")
            if interval < POSITION_REVIEW_INTERVAL_MIN or interval > POSITION_REVIEW_INTERVAL_MAX:
                raise MandateError(
                    "position_review_interval must be between "
                    f"{POSITION_REVIEW_INTERVAL_MIN} and {POSITION_REVIEW_INTERVAL_MAX} minutes"
                )

    def is_active(self, now: str) -> bool:
        current = _timestamp(now, "now")
        return self.state in {"ENABLED", "COOLDOWN"} and self.valid_from <= current < self.valid_until

    def policy_complete(self) -> bool:
        return not bool(self.missing_policy_fields())

    def missing_policy_fields(self) -> tuple[str, ...]:
        missing: list[str] = []
        if self.ai_autonomy is None:
            missing.append("ai_autonomy")
        if self.granted_capital is None:
            missing.append("granted_capital")
        if not self.capital_currency:
            missing.append("capital_currency")
        if self.daily_loss_action is None:
            missing.append("daily_loss_action")
        if self.max_consecutive_losses is None:
            missing.append("max_consecutive_losses")
        if not self.loss_streak_scope:
            missing.append("loss_streak_scope")
        if not self.loss_streak_cooldown:
            missing.append("loss_streak_cooldown")
        if self.daily_loss_limit is None and self.daily_loss_limit_pct is None:
            missing.append("daily_loss_limit")
        if self.daily_loss_limit is not None and self.daily_loss_limit_pct is not None:
            missing.append("daily_loss_limit_conflict")
        if self.drawdown_limit is None:
            missing.append("drawdown_limit")
        if self.max_leverage is None:
            missing.append("max_leverage")
        if not self.daily_loss_scope:
            missing.append("daily_loss_scope")
        if self.daily_loss_reference != "day_start_equity":
            missing.append("daily_loss_reference")
        if self.daily_loss_reset_time_utc != "00:00":
            missing.append("daily_loss_reset_time_utc")
        if not self.drawdown_scope:
            missing.append("drawdown_scope")
        if not self.drawdown_reference:
            missing.append("drawdown_reference")
        if self.position_review_interval is None:
            missing.append("position_review_interval")
        return tuple(missing)

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
            "daily_loss_limit": None if self.daily_loss_limit is None else format(self.daily_loss_limit, "f"),
            "daily_loss_limit_pct": None if self.daily_loss_limit_pct is None else format(self.daily_loss_limit_pct, "f"),
            "daily_loss_reference": self.daily_loss_reference,
            "daily_loss_reset_time_utc": self.daily_loss_reset_time_utc,
            "drawdown_limit": None if self.drawdown_limit is None else format(self.drawdown_limit, "f"),
            "daily_loss_scope": self.daily_loss_scope,
            "drawdown_scope": self.drawdown_scope,
            "drawdown_reference": self.drawdown_reference,
            "drawdown_unit": self.drawdown_unit,
            "max_leverage": None if self.max_leverage is None else format(self.max_leverage, "f"),
            "margin_mode": self.margin_mode,
            "entry_order_type": self.entry_order_type,
            "dca_order_type": self.dca_order_type,
            "take_profit_order_type": self.take_profit_order_type,
            "strategic_stop_mode": self.strategic_stop_mode,
            "emergency_order_type": self.emergency_order_type,
            "kill_switch_order_type": self.kill_switch_order_type,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "state": self.state,
            "require_stop_loss": self.require_stop_loss,
            "ai_autonomy": self.ai_autonomy,
            "granted_capital": None if self.granted_capital is None else format(self.granted_capital, "f"),
            "capital_currency": self.capital_currency,
            "daily_loss_action": self.daily_loss_action,
            "max_consecutive_losses": self.max_consecutive_losses,
            "loss_streak_scope": self.loss_streak_scope,
            "loss_streak_cooldown": self.loss_streak_cooldown,
            "allow_average_down": self.allow_average_down,
            "position_review_interval": self.position_review_interval,
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
            daily_loss_limit=None if value.get("daily_loss_limit") is None else _decimal(value["daily_loss_limit"], "daily_loss_limit"),
            daily_loss_limit_pct=None if value.get("daily_loss_limit_pct") is None else _decimal(value["daily_loss_limit_pct"], "daily_loss_limit_pct"),
            daily_loss_reference=value.get("daily_loss_reference"),
            drawdown_limit=None if value.get("drawdown_limit") is None else _decimal(value["drawdown_limit"], "drawdown_limit"),
            max_leverage=None if value.get("max_leverage") is None else _decimal(value["max_leverage"], "max_leverage"),
            daily_loss_scope=value.get("daily_loss_scope"),
            daily_loss_reset_time_utc=value.get("daily_loss_reset_time_utc", "00:00"),
            drawdown_scope=value.get("drawdown_scope"),
            drawdown_reference=value.get("drawdown_reference"),
            drawdown_unit=value.get("drawdown_unit", "usdt"),
            margin_mode=value.get("margin_mode", "isolated"),
            entry_order_type=value.get("entry_order_type", "limit"),
            dca_order_type=value.get("dca_order_type", "limit"),
            take_profit_order_type=value.get("take_profit_order_type", "limit"),
            strategic_stop_mode=value.get("strategic_stop_mode", "required"),
            emergency_order_type=value.get("emergency_order_type", "market_reduce_only"),
            kill_switch_order_type=value.get("kill_switch_order_type", "market_reduce_only"),
            state=value.get("state", "ENABLED"),
            require_stop_loss=value.get("require_stop_loss", True),
            ai_autonomy=value.get("ai_autonomy"),
            granted_capital=None if value.get("granted_capital") is None else _decimal(value["granted_capital"], "granted_capital"),
            capital_currency=value.get("capital_currency", "USDT"),
            daily_loss_action=value.get("daily_loss_action"),
            max_consecutive_losses=value.get("max_consecutive_losses"),
            loss_streak_scope=value.get("loss_streak_scope"),
            loss_streak_cooldown=value.get("loss_streak_cooldown"),
            allow_average_down=value.get("allow_average_down", False),
            position_review_interval=value.get("position_review_interval"),
        )
