"""Deterministic validation of AI proposals against a mandate."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from typing import Any

from ai_proposal.schema import DecisionOpportunitySnapshot, ProposalDraft, ProposalRecord
from ai_proposal.validator import evaluate_proposal
from .mandate import TradingMandate


@dataclass(frozen=True)
class RiskCheckRecord:
    risk_check_id: str
    decision_id: str
    mandate_id: str
    mandate_version: int
    result: str
    reason_codes: tuple[str, ...]
    checked_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_check_id": self.risk_check_id,
            "decision_id": self.decision_id,
            "mandate_id": self.mandate_id,
            "mandate_version": self.mandate_version,
            "result": self.result,
            "reason_codes": list(self.reason_codes),
            "checked_at": self.checked_at,
        }


@dataclass(frozen=True)
class RiskEvaluation:
    proposal_record: ProposalRecord
    risk_check: RiskCheckRecord


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _context_decimal(snapshot: DecisionOpportunitySnapshot, name: str) -> Decimal | None:
    value = snapshot.features.get(name)
    if value is None:
        return None
    try:
        result = Decimal(str(value))
    except Exception:
        return None
    return result if result.is_finite() else None


def _context_timestamp(snapshot: DecisionOpportunitySnapshot, name: str) -> datetime | None:
    value = snapshot.features.get(name)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def increases_risk(proposal: ProposalDraft) -> bool:
    return proposal.action not in {"CLOSE", "REDUCE", "HOLD", "NO_TRADE"}


def _order_role(proposal: ProposalDraft) -> str:
    return str(proposal.metadata.get("order_role", "entry")).strip().lower()


def evaluate_decision(
    snapshot: DecisionOpportunitySnapshot,
    proposal: ProposalDraft,
    mandate: TradingMandate,
    *,
    now: str | None = None,
    kill_switch: bool = False,
    stale: bool = False,
) -> RiskEvaluation:
    """Validate proposal and return a durable-ready result; never dispatch orders."""
    checked_at = now or _utc_now()
    reasons: list[str] = []
    new_risk = increases_risk(proposal)
    if not mandate.is_active(checked_at):
        reasons.append("MANDATE_INACTIVE")
    if kill_switch:
        reasons.append("KILL_SWITCH_ACTIVE")
    if stale:
        reasons.append("SNAPSHOT_STALE")
    if not mandate.policy_complete():
        reasons.append("POLICY_INCOMPLETE")
    else:
        if mandate.ai_autonomy == "AUTONOMOUS_WITHIN_MANDATE" and new_risk:
            reasons.append("AUTONOMY_NOT_ENABLED")
        if mandate.state == "COOLDOWN" and new_risk:
            reasons.append("LOSS_STREAK_COOLDOWN")
        leverage_value = proposal.metadata.get("leverage")
        try:
            leverage = Decimal(str(leverage_value))
        except Exception:
            leverage = None
        if leverage is None or not leverage.is_finite() or leverage <= 0:
            reasons.append("LEVERAGE_MISSING_OR_INVALID")
        elif leverage > mandate.max_leverage:
            reasons.append("LEVERAGE_LIMIT")
        daily_loss = _context_decimal(snapshot, "daily_loss")
        day_start_equity = _context_decimal(snapshot, "day_start_equity")
        daily_loss_at = _context_timestamp(snapshot, "daily_loss_at")
        drawdown = _context_decimal(snapshot, "drawdown")
        consecutive_losses = _context_decimal(snapshot, "consecutive_losses")
        drawdown_unit = str(snapshot.features.get("drawdown_unit", "usdt")).lower()
        context_missing = (
            daily_loss is None
            or day_start_equity is None
            or day_start_equity <= 0
            or daily_loss_at is None
            or drawdown is None
            or consecutive_losses is None
        )
        if context_missing and new_risk:
            reasons.append("RISK_CONTEXT_INCOMPLETE")
        elif not context_missing:
            checked_dt = datetime.fromisoformat(checked_at.replace("Z", "+00:00")).astimezone(timezone.utc)
            if daily_loss_at.date() != checked_dt.date() and new_risk:
                reasons.append("DAILY_LOSS_CONTEXT_STALE")
            daily_loss_limit = (
                day_start_equity * mandate.daily_loss_limit_pct / Decimal("100")
                if mandate.daily_loss_limit_pct is not None
                else mandate.daily_loss_limit
            )
            if daily_loss_limit is None:
                reasons.append("POLICY_INCOMPLETE")
            elif new_risk and daily_loss >= daily_loss_limit:
                reasons.append("DAILY_LOSS_LIMIT")
            if mandate.drawdown_limit is None or drawdown_unit != mandate.drawdown_unit:
                if new_risk:
                    reasons.append("DRAWDOWN_CONTEXT_INVALID")
            elif new_risk and drawdown >= mandate.drawdown_limit:
                reasons.append("DRAWDOWN_LIMIT")
            if new_risk and consecutive_losses >= Decimal(mandate.max_consecutive_losses):
                reasons.append("LOSS_STREAK_LIMIT")
    if mandate.margin_mode != "isolated":
        reasons.append("MARGIN_MODE_NOT_ALLOWED")
    order_type = str(proposal.metadata.get("order_type", "limit")).strip().lower()
    order_role = str(proposal.metadata.get("order_role", "entry")).strip().lower()
    reduce_only = proposal.metadata.get("reduce_only", False)
    if not isinstance(reduce_only, bool):
        reasons.append("REDUCE_ONLY_INVALID")
    if not mandate.allow_average_down and _order_role(proposal) in {"dca", "add"}:
        reasons.append("AVERAGE_DOWN_DISABLED")
    if proposal.action == "OPEN" and order_type != mandate.entry_order_type:
        reasons.append("ENTRY_ORDER_TYPE_NOT_ALLOWED")
    if proposal.action in {"CLOSE", "REDUCE"} and order_type == "limit" and order_role not in {"take_profit", "reduce"}:
        reasons.append("EXIT_ORDER_ROLE_NOT_ALLOWED")
    if order_type == "market" and (
        not reduce_only
        or order_role not in {"strategic_stop", "emergency_close", "kill_switch"}
    ):
        reasons.append("MARKET_REDUCE_ONLY_REQUIRED")
    if order_type not in {"limit", "market"}:
        reasons.append("ORDER_TYPE_NOT_ALLOWED")
    if snapshot.symbol not in mandate.allowed_symbols or proposal.symbol not in mandate.allowed_symbols:
        reasons.append("SYMBOL_NOT_ALLOWED")
    if snapshot.side not in mandate.allowed_sides or proposal.side not in mandate.allowed_sides:
        reasons.append("SIDE_NOT_ALLOWED")
    if proposal.action not in mandate.allowed_actions:
        reasons.append("ACTION_NOT_ALLOWED")
    if proposal.size > mandate.max_size:
        reasons.append("SIZE_LIMIT")
    if proposal.exposure > mandate.max_exposure:
        reasons.append("EXPOSURE_LIMIT")
    if proposal.loss_budget != mandate.loss_budget:
        reasons.append("LOSS_BUDGET_MISMATCH")
    stop_loss_value: Decimal | None = None
    requires_strategic_stop = mandate.require_stop_loss and mandate.strategic_stop_mode == "required"
    if requires_strategic_stop and proposal.action == "OPEN":
        stop_loss = proposal.metadata.get("stop_loss")
        try:
            stop_loss_value = None if stop_loss is None else Decimal(str(stop_loss))
            if stop_loss_value is None or not stop_loss_value.is_finite() or stop_loss_value <= 0:
                reasons.append("PROTECTIVE_STOP_REQUIRED" if stop_loss is None else "PROTECTIVE_STOP_INVALID")
            elif proposal.side == "long" and stop_loss_value >= proposal.ref_price:
                reasons.append("PROTECTIVE_STOP_WRONG_SIDE")
            elif proposal.side == "short" and stop_loss_value <= proposal.ref_price:
                reasons.append("PROTECTIVE_STOP_WRONG_SIDE")
            else:
                order_risk = abs(proposal.ref_price - stop_loss_value) * proposal.size
                if order_risk > mandate.max_order_risk:
                    reasons.append("ORDER_RISK_LIMIT")
        except Exception:
            reasons.append("PROTECTIVE_STOP_INVALID")

    proposal_record = evaluate_proposal(snapshot, proposal)
    if proposal_record.result != "ACCEPTED":
        reasons.extend(error.code for error in proposal_record.validation_errors)
    unique_reasons = tuple(dict.fromkeys(reasons))
    paused = (
        "MANDATE_INACTIVE",
        "KILL_SWITCH_ACTIVE",
        "SNAPSHOT_STALE",
        "POLICY_INCOMPLETE",
        "RISK_CONTEXT_INCOMPLETE",
        "DAILY_LOSS_CONTEXT_STALE",
        "LOSS_STREAK_LIMIT",
        "LOSS_STREAK_COOLDOWN",
    )
    result = "PAUSED" if any(code in unique_reasons for code in paused) else ("REJECTED" if unique_reasons else "APPROVED")
    # Risk checks are immutable records. UUID is audit identity, not an idempotency key.
    check = RiskCheckRecord(
        risk_check_id="risk-" + hashlib.sha256(
            "\\x1f".join((mandate.mandate_id, str(mandate.version), proposal.proposal_id, checked_at, ",".join(unique_reasons))).encode("utf-8")
        ).hexdigest()[:24],
        decision_id=proposal.proposal_id,
        mandate_id=mandate.mandate_id,
        mandate_version=mandate.version,
        result=result,
        reason_codes=unique_reasons,
        checked_at=checked_at,
    )
    return RiskEvaluation(proposal_record=proposal_record, risk_check=check)
