"""Map frontend local policy + scan limits to a paper mandate.

Risk numbers come from saved Mandate fields or an explicit limits mapping.
Does not invent risk numbers. Empty allowlist is not tradable. This module
never calls an exchange.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from ai_proposal.schema import DecisionOpportunitySnapshot, HardLimits, ProposalDraft
from .mandate import MandateError, TradingMandate


FRONTEND_MANDATE_ID = "local-frontend"
SESSION_HOURS = 24
ALLOWED_ACTIONS = ("OPEN", "CLOSE", "REDUCE", "HOLD", "NO_TRADE", "ADJUST_SL", "CANCEL")
ALLOWED_SIDES = ("long", "short")


class FrontendMandateError(MandateError):
    """Raised when frontend policy cannot become a tradable mandate."""


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FrontendMandateError(f"{name} is required")
    return value.strip()


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise FrontendMandateError(f"{name} must be a decimal")
    try:
        number = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError) as exc:
        raise FrontendMandateError(f"{name} must be a decimal") from exc
    if not number.is_finite() or number <= 0:
        raise FrontendMandateError(f"{name} must be finite and positive")
    return number


def _int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        try:
            number = int(str(value).strip())
        except (TypeError, ValueError) as exc:
            raise FrontendMandateError(f"{name} must be an integer") from exc
    else:
        number = value
    if number < 1:
        raise FrontendMandateError(f"{name} must be a positive integer")
    return number


def _now(value: str | None) -> str:
    if value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise FrontendMandateError("now must include a timezone")
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def zone_id_for(symbol: str, side: str) -> str:
    return f"local-{str(symbol).strip().upper()}-{str(side).strip().lower()}"


def normalize_allowlist(policy: Mapping[str, Any]) -> tuple[str, ...]:
    raw = policy.get("symbol_allowlist")
    if not isinstance(raw, list):
        raise FrontendMandateError("symbol_allowlist must be a list")
    seen: list[str] = []
    for item in raw:
        symbol = str(item or "").strip().upper()
        if not symbol:
            raise FrontendMandateError("symbol_allowlist contains an empty symbol")
        if symbol in seen:
            raise FrontendMandateError("symbol_allowlist must be unique")
        seen.append(symbol)
    return tuple(seen)


def _optional_decimal(value: Any, name: str) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return _decimal(value, name)


@dataclass(frozen=True)
class ScanLimits:
    symbol: str
    side: str
    ref_price: Decimal
    sl_pct: Decimal
    loss_budget: Decimal
    max_order_risk: Decimal
    max_size: Decimal
    size: Decimal = Decimal("0")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ScanLimits":
        side = str(value.get("side") or "").strip().lower()
        if side not in ALLOWED_SIDES:
            raise FrontendMandateError("side must be long or short")
        return cls(
            symbol=str(value.get("symbol") or "").strip().upper(),
            side=side,
            ref_price=_decimal(value.get("ref_price"), "ref_price"),
            sl_pct=_decimal(value.get("sl_pct"), "sl_pct"),
            loss_budget=_decimal(value.get("loss_budget"), "loss_budget"),
            max_order_risk=_decimal(value.get("max_order_risk"), "max_order_risk"),
            max_size=_decimal(value.get("max_size"), "max_size"),
            size=_optional_decimal(value.get("size"), "size"),
        )


def _first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def scan_limits_from_policy(
    policy: Mapping[str, Any],
    limits: Mapping[str, Any],
) -> ScanLimits:
    """Fill scan limits from saved policy when the tick omits risk numbers."""
    if not isinstance(policy, Mapping):
        raise FrontendMandateError("policy must be a mapping")
    if not isinstance(limits, Mapping):
        raise FrontendMandateError("limits must be a mapping")
    return ScanLimits.from_mapping(
        {
            "symbol": limits.get("symbol"),
            "side": limits.get("side"),
            "ref_price": limits.get("ref_price"),
            "size": limits.get("size"),
            "sl_pct": _first_present(limits.get("sl_pct"), policy.get("sl_pct")),
            "loss_budget": _first_present(
                limits.get("loss_budget"),
                policy.get("loss_budget"),
                policy.get("zone_loss_limit_usdt"),
            ),
            "max_order_risk": _first_present(
                limits.get("max_order_risk"),
                policy.get("max_order_risk"),
                policy.get("max_order_risk_usdt"),
            ),
            "max_size": _first_present(limits.get("max_size"), policy.get("max_size")),
        }
    )


def scan_risk_from_policy(policy: Mapping[str, Any], limits: Mapping[str, Any]) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Return sl_pct, loss_budget, max_order_risk, max_size. Does not invent a symbol."""
    if not isinstance(policy, Mapping):
        raise FrontendMandateError("policy must be a mapping")
    if not isinstance(limits, Mapping):
        raise FrontendMandateError("limits must be a mapping")
    return (
        _decimal(_first_present(limits.get("sl_pct"), policy.get("sl_pct")), "sl_pct"),
        _decimal(
            _first_present(limits.get("loss_budget"), policy.get("loss_budget"), policy.get("zone_loss_limit_usdt")),
            "loss_budget",
        ),
        _decimal(
            _first_present(
                limits.get("max_order_risk"),
                policy.get("max_order_risk"),
                policy.get("max_order_risk_usdt"),
            ),
            "max_order_risk",
        ),
        _decimal(_first_present(limits.get("max_size"), policy.get("max_size")), "max_size"),
    )


def use_allowlist_scope(limits: Mapping[str, Any]) -> bool:
    """True when the tick should walk every approved pair instead of one symbol."""
    if not isinstance(limits, Mapping):
        return False
    if str(limits.get("scope") or "").strip().lower() == "allowlist":
        return True
    return not str(limits.get("symbol") or "").strip()


def sides_for_symbol(symbol: str, positions: Any) -> tuple[str, ...]:
    """Open sides if the pair is already held; otherwise both so AI may open one."""
    wanted = str(symbol or "").strip().upper()
    found: list[str] = []
    raw = positions
    if isinstance(positions, Mapping):
        raw = positions.get("positions") or positions.get("list") or positions.get("data") or []
    if not isinstance(raw, list):
        raw = []
    for row in raw:
        if not isinstance(row, Mapping):
            continue
        if str(row.get("symbol") or "").strip().upper() != wanted:
            continue
        side = str(row.get("holdSide") or row.get("posSide") or row.get("side") or "").strip().lower()
        if side not in ALLOWED_SIDES or side in found:
            continue
        qty = row.get("total") or row.get("available") or row.get("size")
        try:
            size = Decimal(str(qty).strip()) if qty not in (None, "") else Decimal("0")
        except (InvalidOperation, ValueError, AttributeError):
            continue
        if size > 0:
            found.append(side)
    return tuple(found) or ALLOWED_SIDES


def allowlist_scan_jobs(
    policy: Mapping[str, Any],
    limits: Mapping[str, Any],
    *,
    positions: Any,
    prices: Mapping[str, Decimal],
) -> tuple[ScanLimits, ...]:
    """One ScanLimits per approved pair and side that has a real price."""
    allowlist = normalize_allowlist(policy)
    sl_pct, loss_budget, max_order_risk, max_size = scan_risk_from_policy(policy, limits)
    jobs: list[ScanLimits] = []
    for symbol in allowlist:
        price = prices.get(symbol)
        if price is None or price <= 0:
            continue
        for side in sides_for_symbol(symbol, positions):
            jobs.append(
                ScanLimits(
                    symbol=symbol,
                    side=side,
                    ref_price=price,
                    sl_pct=sl_pct,
                    loss_budget=loss_budget,
                    max_order_risk=max_order_risk,
                    max_size=max_size,
                )
            )
    return tuple(jobs)


def policy_to_mandate(
    policy: Mapping[str, Any],
    limits: ScanLimits,
    *,
    now: str | None = None,
    session_hours: int = SESSION_HOURS,
    mandate_id: str | None = None,
) -> TradingMandate:
    """Build an immutable mandate from a saved frontend policy and user limits."""
    allowlist = normalize_allowlist(policy)
    if not allowlist:
        raise FrontendMandateError("WHITELIST_EMPTY")
    if not limits.symbol:
        raise FrontendMandateError("symbol is required")
    if limits.symbol not in allowlist:
        raise FrontendMandateError("SYMBOL_NOT_IN_WHITELIST")
    if policy.get("ai_autonomy") != "AUTONOMOUS_WITHIN_MANDATE":
        raise FrontendMandateError("Demo POST requires AUTONOMOUS_WITHIN_MANDATE")
    if policy.get("allow_average_down") is not False:
        raise FrontendMandateError("allow_average_down must be false")
    stamp = _now(now)
    start = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    granted = _decimal(policy.get("granted_capital"), "granted_capital")
    return TradingMandate(
        mandate_id=str(mandate_id or FRONTEND_MANDATE_ID),
        version=_int(policy.get("version"), "version"),
        zone_id=zone_id_for(limits.symbol, limits.side),
        allowed_symbols=allowlist,
        allowed_sides=ALLOWED_SIDES,
        allowed_actions=ALLOWED_ACTIONS,
        max_size=limits.max_size,
        max_exposure=granted,
        loss_budget=limits.loss_budget,
        max_order_risk=limits.max_order_risk,
        valid_from=stamp,
        valid_until=(start + timedelta(hours=session_hours)).isoformat().replace("+00:00", "Z"),
        daily_loss_limit_pct=_decimal(policy.get("daily_loss_limit_pct"), "daily_loss_limit_pct"),
        daily_loss_reference="day_start_equity",
        daily_loss_reset_time_utc="00:00",
        drawdown_limit=_decimal(policy.get("drawdown_limit"), "drawdown_limit"),
        drawdown_unit=_text(policy.get("drawdown_unit"), "drawdown_unit"),
        drawdown_reference=_text(policy.get("drawdown_reference"), "drawdown_reference"),
        drawdown_scope=_text(policy.get("drawdown_scope") or "subaccount", "drawdown_scope"),
        daily_loss_scope=_text(policy.get("daily_loss_scope") or "subaccount", "daily_loss_scope"),
        max_leverage=_decimal(policy.get("max_leverage"), "max_leverage"),
        ai_autonomy="AUTONOMOUS_WITHIN_MANDATE",
        granted_capital=granted,
        capital_currency=_text(policy.get("capital_currency") or "USDT", "capital_currency"),
        daily_loss_action=_text(policy.get("daily_loss_action"), "daily_loss_action"),
        max_consecutive_losses=_int(policy.get("max_consecutive_losses"), "max_consecutive_losses"),
        loss_streak_scope=_text(policy.get("loss_streak_scope") or "subaccount", "loss_streak_scope"),
        loss_streak_cooldown=_text(policy.get("loss_streak_cooldown"), "loss_streak_cooldown"),
        allow_average_down=False,
        position_review_interval=_int(policy.get("position_review_interval"), "position_review_interval"),
    )


def build_scan_snapshot(
    mandate: TradingMandate,
    limits: ScanLimits,
    *,
    now: str | None = None,
    opportunity_id: str | None = None,
    features: Mapping[str, Any] | None = None,
) -> DecisionOpportunitySnapshot:
    stamp = _now(now)
    return DecisionOpportunitySnapshot(
        opportunity_id=opportunity_id or f"demo-scan-{limits.symbol.lower()}",
        snapshot_at=stamp,
        feature_as_of=stamp,
        symbol=limits.symbol,
        side=limits.side,
        state="READY",
        ref_price=limits.ref_price,
        sl_pct=limits.sl_pct,
        loss_budget=limits.loss_budget,
        size=limits.size,
        exposure=limits.ref_price * limits.size,
        hard_limits=HardLimits(
            allowed_symbols=mandate.allowed_symbols,
            allowed_sides=mandate.allowed_sides,
            allowed_states=("READY",),
            max_size=mandate.max_size,
            max_exposure=mandate.max_exposure,
        ),
        features=dict(features or {}),
    )


def proposal_from_intent(
    snapshot: DecisionOpportunitySnapshot,
    intent: Mapping[str, Any],
    *,
    policy_version: str,
    now: str | None = None,
) -> ProposalDraft:
    """Build an OPEN draft from a user-filled intent ticket. Does not send."""
    size = _decimal(intent.get("size"), "intent_size")
    price = _decimal(intent.get("price") or snapshot.ref_price, "intent_price")
    side = str(intent.get("side") or snapshot.side).strip().lower()
    if side not in ALLOWED_SIDES:
        raise FrontendMandateError("intent side must be long or short")
    stop = intent.get("stop_loss")
    if stop in (None, ""):
        delta = snapshot.ref_price * snapshot.sl_pct / Decimal("100")
        stop = snapshot.ref_price - delta if side == "long" else snapshot.ref_price + delta
    stamp = _now(now)
    return ProposalDraft.from_snapshot(
        snapshot,
        proposal_id=f"intent-{snapshot.opportunity_id}",
        model_version="frontend-intent",
        policy_version=policy_version,
        action="OPEN",
        rationale="User-confirmed Demo intent ticket within whitelist",
        decision_timestamp=stamp,
        side=side,
        size=size,
        exposure=price * size,
        ref_price=price,
        metadata={
            "stop_loss": format(_decimal(stop, "stop_loss"), "f"),
            "leverage": str(intent.get("leverage") or "1"),
        },
    )
