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
    if not mandate.is_active(checked_at):
        reasons.append("MANDATE_INACTIVE")
    if kill_switch:
        reasons.append("KILL_SWITCH_ACTIVE")
    if stale:
        reasons.append("SNAPSHOT_STALE")
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
    if mandate.require_stop_loss and proposal.action == "OPEN":
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
    result = "PAUSED" if any(code in unique_reasons for code in ("MANDATE_INACTIVE", "KILL_SWITCH_ACTIVE", "SNAPSHOT_STALE")) else ("REJECTED" if unique_reasons else "APPROVED")
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
