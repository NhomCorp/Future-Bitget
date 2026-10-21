"""Paper-only AI proposal pipeline with mandatory deterministic risk checks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ai_proposal.interface import propose
from ai_proposal.schema import DecisionOpportunitySnapshot, ProposalDraft, ProposalRecord
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

    def __init__(self, provider: Any, store: Any):
        self.provider = provider
        self.store = store

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
        if (
            zone is None
            or zone.state != "ACTIVE"
            or zone.symbol != snapshot.symbol
            or zone.side != snapshot.side
            or zone.zone_id != mandate.zone_id
        ):
            self.store.append_agent_event(
                mandate.zone_id,
                "AI_DECISION_BLOCKED",
                {"opportunity_id": snapshot.opportunity_id, "reason_code": "ZONE_NOT_ACTIVE"},
            )
            rejected = propose(snapshot, lambda _snapshot: None)
            self.store.record_proposal(rejected.to_dict(), zone_id=mandate.zone_id)
            return PaperAgentResult(proposal=rejected, risk_check=None, intent=None)

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
        if evaluation.risk_check.result != "APPROVED":
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
