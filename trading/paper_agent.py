"""Paper-only AI proposal pipeline with mandatory deterministic risk checks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ai_proposal.interface import propose
from ai_proposal.schema import DecisionOpportunitySnapshot, ProposalDraft, ProposalRecord
from executor.zone_executor import IntentRole, RiskTrigger, ZoneExecutor, ZoneOrderSpec
from .mandate import TradingMandate
from .order_intent import PaperOrderIntent, intent_from_proposal
from .risk_engine import RiskCheckRecord, evaluate_decision


@dataclass(frozen=True)
class PaperAgentResult:
    proposal: ProposalRecord
    risk_check: RiskCheckRecord | None
    intent: PaperOrderIntent | None


class PaperAgent:
    """Generate, validate, and persist dry-run decisions; never calls exchange APIs."""

    def __init__(self, provider: Any, store: Any, executor: Any | None = None):
        self.provider = provider
        self.store = store
        self.executor = executor

    def run(
        self,
        snapshot: DecisionOpportunitySnapshot,
        mandate: TradingMandate,
        *,
        kill_switch: bool = False,
        stale: bool = False,
        now: str | None = None,
    ) -> PaperAgentResult:
        self.store.save_mandate(mandate.to_dict())
        try:
            zone = self.store.zone_store.get_zone(mandate.zone_id)
        except Exception:
            zone = None

        if mandate.ai_autonomy == "AUTONOMOUS_WITHIN_MANDATE":
            return self._blocked(snapshot, mandate, "AUTONOMY_NOT_ENABLED")

        if mandate.ai_autonomy != "PROPOSAL_ONLY" and (
            zone is None
            or zone.state != "ACTIVE"
            or zone.symbol != snapshot.symbol
            or zone.side != snapshot.side
            or zone.zone_id != mandate.zone_id
            or str(zone.config.get("opened_by", "user")).strip().lower() != "user"
        ):
            return self._blocked(snapshot, mandate, "ZONE_NOT_ACTIVE")

        if zone is None:
            return self._blocked(snapshot, mandate, "ZONE_NOT_ACTIVE")

        candidate: ProposalDraft | Mapping[str, Any] | None = None
        try:
            candidate = self.provider.propose(snapshot)
        except Exception:
            self.store.append_agent_event(
                mandate.zone_id,
                "AI_PROVIDER_FAILED",
                {"opportunity_id": snapshot.opportunity_id, "reason_code": "PROVIDER_ERROR"},
            )
            rejected = propose(snapshot, lambda _snapshot: None)
            self.store.record_proposal(rejected.to_dict(), zone_id=mandate.zone_id)
            self.store.append_agent_event(
                mandate.zone_id,
                "AI_DECISION_REJECTED",
                {"proposal_id": rejected.proposal_id, "reason_codes": [error.code for error in rejected.validation_errors]},
            )
            return PaperAgentResult(
                proposal=rejected,
                risk_check=None,
                intent=None,
            )

        proposal_record = propose(snapshot, lambda _snapshot: candidate)
        self.store.record_proposal(proposal_record.to_dict(), zone_id=mandate.zone_id)
        if proposal_record.proposal is None:
            self.store.append_agent_event(
                mandate.zone_id,
                "AI_DECISION_REJECTED",
                {"proposal_id": proposal_record.proposal_id, "reason_codes": [error.code for error in proposal_record.validation_errors]},
            )
            return PaperAgentResult(proposal=proposal_record, risk_check=None, intent=None)

        evaluation = evaluate_decision(
            snapshot,
            proposal_record.proposal,
            mandate,
            now=now,
            kill_switch=kill_switch,
            stale=stale,
        )
        self.store.save_risk_check(evaluation.risk_check.to_dict())
        self.store.append_agent_event(
            mandate.zone_id,
            "RISK_CHECKED",
            {
                "decision_id": evaluation.risk_check.decision_id,
                "risk_check_id": evaluation.risk_check.risk_check_id,
                "result": evaluation.risk_check.result,
                "reason_codes": list(evaluation.risk_check.reason_codes),
            },
        )
        if "DAILY_LOSS_LIMIT" in evaluation.risk_check.reason_codes and mandate.daily_loss_action == "EMERGENCY_FLATTEN":
            self._record_emergency_flatten(snapshot, mandate, evaluation.risk_check)
        if mandate.ai_autonomy == "PROPOSAL_ONLY" or evaluation.risk_check.result != "APPROVED":
            return PaperAgentResult(proposal=proposal_record, risk_check=evaluation.risk_check, intent=None)

        intent = intent_from_proposal(
            proposal_record.proposal,
            zone_id=mandate.zone_id,
            mandate_id=mandate.mandate_id,
            mandate_version=mandate.version,
            risk_check_id=evaluation.risk_check.risk_check_id,
        )
        if intent is not None:
            self.store.save_paper_intent(intent.to_record())
            self.store.append_agent_event(
                mandate.zone_id,
                "PAPER_ORDER_INTENT_CREATED",
                {"decision_id": intent.decision_id, "risk_check_id": intent.risk_check_id, "client_oid": intent.client_oid},
            )
        return PaperAgentResult(proposal=proposal_record, risk_check=evaluation.risk_check, intent=intent)

    def _blocked(self, snapshot: DecisionOpportunitySnapshot, mandate: TradingMandate, reason_code: str) -> PaperAgentResult:
        self.store.append_agent_event(
            mandate.zone_id,
            "AI_DECISION_BLOCKED",
            {"opportunity_id": snapshot.opportunity_id, "reason_code": reason_code},
        )
        rejected = propose(snapshot, lambda _snapshot: None)
        self.store.record_proposal(rejected.to_dict(), zone_id=mandate.zone_id)
        return PaperAgentResult(proposal=rejected, risk_check=None, intent=None)

    def _record_emergency_flatten(
        self,
        snapshot: DecisionOpportunitySnapshot,
        mandate: TradingMandate,
        risk_check: RiskCheckRecord,
    ) -> None:
        existing = self.store.agent_events(mandate.zone_id)
        if any(event.get("event") == "EMERGENCY_FLATTEN_RECORDED" for event in existing):
            return
        payload: dict[str, Any] = {
            "decision_id": risk_check.decision_id,
            "risk_check_id": risk_check.risk_check_id,
            "dry_run": True,
        }
        try:
            executor = self.executor or ZoneExecutor(self.store)
            self.executor = executor
            side = "buy" if snapshot.side == "long" else "sell"
            try:
                executor.create_zone(
                    mandate.zone_id,
                    [ZoneOrderSpec(IntentRole.ENTRY, 0, snapshot.size, snapshot.ref_price, side, position_side=snapshot.side)],
                    position_quantity=snapshot.size,
                    position_side=snapshot.side,
                )
            except Exception:
                pass
            action = executor.on_risk_trigger(mandate.zone_id, RiskTrigger.LOSS_BUDGET)
            payload["emergency_close_client_oid"] = action.emergency_close_client_oid
            payload["cancelled_client_oids"] = list(action.cancelled_client_oids)
        except Exception:
            payload["reason_code"] = "EXECUTOR_DRY_RUN_ERROR"
        self.store.append_agent_event(mandate.zone_id, "EMERGENCY_FLATTEN_RECORDED", payload)
