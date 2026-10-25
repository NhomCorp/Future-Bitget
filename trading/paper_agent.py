"""Paper-only AI proposal pipeline with mandatory deterministic risk checks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ai_proposal.interface import propose
from ai_proposal.schema import DecisionOpportunitySnapshot, ProposalDraft, ProposalRecord, iter_plan_proposals
from executor.zone_executor import IntentRole, RiskTrigger, ZoneExecutor, ZoneOrderSpec
from .mandate import TradingMandate
from .mandate_store import consume_loss_budget, recover_session
from .order_intent import PaperOrderIntent, intent_from_proposal
from .reconcile import blocks_new_intent
from .risk_engine import RiskCheckRecord, evaluate_decision


def _load_paper_intent(store: Any, client_oid: str, zone_id: str) -> dict[str, Any] | None:
    getter = getattr(store, "get_paper_intent", None)
    if getter is not None:
        return getter(client_oid)
    for item in store.paper_intents(zone_id):
        if item.get("client_oid") == client_oid:
            return item
    return None


@dataclass(frozen=True)
class PaperAgentResult:
    proposal: ProposalRecord
    risk_check: RiskCheckRecord | None
    intent: PaperOrderIntent | None
    intents: tuple[PaperOrderIntent, ...] = ()
    risk_checks: tuple[RiskCheckRecord, ...] = ()


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
        if zone is None and mandate.ai_autonomy == "AUTONOMOUS_WITHIN_MANDATE":
            zone = self._ensure_autonomous_zone(snapshot, mandate)

        recovery = recover_session(self.store, mandate.zone_id, mandate.mandate_id)
        active_mandate = recovery.mandate or mandate

        if active_mandate.ai_autonomy == "MANAGED_ZONE" and (
            zone is None
            or zone.state != "ACTIVE"
            or zone.symbol != snapshot.symbol
            or zone.side != snapshot.side
            or zone.zone_id != active_mandate.zone_id
            or str(zone.config.get("opened_by", "user")).strip().lower() != "user"
        ):
            return self._blocked(snapshot, active_mandate, "ZONE_NOT_ACTIVE")

        if zone is None:
            if active_mandate.ai_autonomy != "AUTONOMOUS_WITHIN_MANDATE":
                return self._blocked(snapshot, active_mandate, "ZONE_NOT_ACTIVE")
        elif zone.state not in {"ACTIVE", "PREVIEW"}:
            return self._blocked(snapshot, active_mandate, "ZONE_NOT_ACTIVE")
        elif active_mandate.ai_autonomy == "AUTONOMOUS_WITHIN_MANDATE" and (
            zone.symbol != snapshot.symbol or zone.side != snapshot.side
        ):
            return self._blocked(snapshot, active_mandate, "ZONE_NOT_ACTIVE")

        if recovery.has_unknown():
            return self._blocked(snapshot, active_mandate, "RECONCILE_REQUIRED")

        if recovery.remaining_loss_budget is not None and recovery.remaining_loss_budget <= 0:
            return self._blocked(snapshot, active_mandate, "LOSS_BUDGET_EXHAUSTED")

        candidate: ProposalDraft | Mapping[str, Any] | None = None
        try:
            candidate = self.provider.propose(snapshot)
        except Exception:
            self.store.append_agent_event(
                active_mandate.zone_id,
                "AI_PROVIDER_FAILED",
                {"opportunity_id": snapshot.opportunity_id, "reason_code": "PROVIDER_ERROR"},
            )
            rejected = propose(snapshot, lambda _snapshot: None)
            self.store.record_proposal(rejected.to_dict(), zone_id=active_mandate.zone_id)
            self.store.append_agent_event(
                active_mandate.zone_id,
                "AI_DECISION_REJECTED",
                {"proposal_id": rejected.proposal_id, "reason_codes": [error.code for error in rejected.validation_errors]},
            )
            return PaperAgentResult(
                proposal=rejected,
                risk_check=None,
                intent=None,
                intents=(),
                risk_checks=(),
            )

        proposal_record = propose(snapshot, lambda _snapshot: candidate)
        self.store.record_proposal(proposal_record.to_dict(), zone_id=active_mandate.zone_id)
        if proposal_record.proposal is None:
            self.store.append_agent_event(
                active_mandate.zone_id,
                "AI_DECISION_REJECTED",
                {"proposal_id": proposal_record.proposal_id, "reason_codes": [error.code for error in proposal_record.validation_errors]},
            )
            return PaperAgentResult(proposal=proposal_record, risk_check=None, intent=None)

        steps, plan_error = iter_plan_proposals(proposal_record.proposal)
        if plan_error:
            evaluation = evaluate_decision(
                snapshot,
                proposal_record.proposal,
                active_mandate,
                now=now,
                kill_switch=kill_switch,
                stale=stale,
            )
            self._save_risk(active_mandate.zone_id, evaluation.risk_check)
            return PaperAgentResult(
                proposal=proposal_record,
                risk_check=evaluation.risk_check,
                intent=None,
                risk_checks=(evaluation.risk_check,),
            )

        created: list[PaperOrderIntent] = []
        checks: list[RiskCheckRecord] = []
        for step in steps:
            evaluation = evaluate_decision(
                snapshot,
                step,
                active_mandate,
                now=now,
                kill_switch=kill_switch,
                stale=stale,
            )
            checks.append(evaluation.risk_check)
            self._save_risk(active_mandate.zone_id, evaluation.risk_check)
            if "DAILY_LOSS_LIMIT" in evaluation.risk_check.reason_codes and active_mandate.daily_loss_action == "EMERGENCY_FLATTEN":
                self._record_emergency_flatten(snapshot, active_mandate, evaluation.risk_check)
            if active_mandate.ai_autonomy == "PROPOSAL_ONLY" or evaluation.risk_check.result != "APPROVED":
                continue
            if zone is None and step.action != "OPEN":
                self.store.append_agent_event(
                    active_mandate.zone_id,
                    "AI_DECISION_BLOCKED",
                    {"opportunity_id": snapshot.opportunity_id, "reason_code": "ZONE_NOT_ACTIVE", "action": step.action},
                )
                continue
            if zone is None and step.action == "OPEN" and active_mandate.ai_autonomy == "AUTONOMOUS_WITHIN_MANDATE":
                zone = self._ensure_autonomous_zone(snapshot, active_mandate)
            intent = self._persist_step_intent(step, evaluation.risk_check, active_mandate, recovery)
            if intent is not None:
                created.append(intent)
                recovery = recover_session(self.store, active_mandate.zone_id, active_mandate.mandate_id)

        primary = checks[0] if checks else None
        return PaperAgentResult(
            proposal=proposal_record,
            risk_check=primary,
            intent=created[0] if created else None,
            intents=tuple(created),
            risk_checks=tuple(checks),
        )

    def _save_risk(self, zone_id: str, risk_check: RiskCheckRecord) -> None:
        self.store.save_risk_check(risk_check.to_dict())
        self.store.append_agent_event(
            zone_id,
            "RISK_CHECKED",
            {
                "decision_id": risk_check.decision_id,
                "risk_check_id": risk_check.risk_check_id,
                "result": risk_check.result,
                "reason_codes": list(risk_check.reason_codes),
            },
        )

    def _ensure_autonomous_zone(self, snapshot: DecisionOpportunitySnapshot, mandate: TradingMandate) -> Any:
        try:
            return self.store.zone_store.get_zone(mandate.zone_id)
        except Exception:
            pass
        return self.store.zone_store.create_zone(
            {
                "symbol": snapshot.symbol,
                "side": snapshot.side,
                "ref_price": format(snapshot.ref_price, "f"),
                "zone_loss_limit_usdt": format(mandate.loss_budget, "f"),
                "sl_pct": format(snapshot.sl_pct, "f"),
                "opened_by": "ai",
            },
            zone_id=mandate.zone_id,
            state="ACTIVE",
        )

    def _persist_step_intent(
        self,
        proposal: ProposalDraft,
        risk_check: RiskCheckRecord,
        mandate: TradingMandate,
        recovery: Any,
    ) -> PaperOrderIntent | None:
        intent = intent_from_proposal(
            proposal,
            zone_id=mandate.zone_id,
            mandate_id=mandate.mandate_id,
            mandate_version=mandate.version,
            risk_check_id=risk_check.risk_check_id,
        )
        if intent is None:
            return None
        existing = _load_paper_intent(self.store, intent.client_oid, mandate.zone_id)
        if existing is not None:
            recovered = PaperOrderIntent.from_record(existing)
            if blocks_new_intent(existing):
                self.store.append_agent_event(
                    mandate.zone_id,
                    "RECONCILE_REQUIRED",
                    {"client_oid": intent.client_oid, "decision_id": intent.decision_id, "dry_run": True},
                )
            return recovered
        if proposal.action == "OPEN" and not intent.reduce_only:
            remaining = recovery.remaining_loss_budget
            needed = mandate.max_order_risk
            if remaining is not None and remaining < needed:
                self.store.append_agent_event(
                    mandate.zone_id,
                    "AI_DECISION_BLOCKED",
                    {"opportunity_id": proposal.opportunity_id, "reason_code": "LOSS_BUDGET_EXHAUSTED"},
                )
                return None
            consume_loss_budget(
                self.store,
                zone_id=mandate.zone_id,
                mandate_id=mandate.mandate_id,
                amount=needed,
                reason="paper_open_reserve",
                original_loss_budget=mandate.loss_budget,
            )
        self.store.save_paper_intent(intent.to_record())
        self.store.append_agent_event(
            mandate.zone_id,
            "PAPER_ORDER_INTENT_CREATED",
            {"decision_id": intent.decision_id, "risk_check_id": intent.risk_check_id, "client_oid": intent.client_oid},
        )
        return intent

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
