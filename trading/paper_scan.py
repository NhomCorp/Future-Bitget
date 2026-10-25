"""Local paper scan clock.

One tick reads ``position_review_interval`` and either skips or calls
``PaperAgent.run()``. Default is no exchange POST. With explicit Demo
confirm, approved intents in the mandate whitelist may go through
``demo_dispatch``. This module does not run the protection clock
(SL / fill / mark). Expired mandate time does not flatten. A due tick may
yield 0-N paper intents from ``plan_actions``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

from ai_proposal.interface import no_trade_proposal
from ai_proposal.schema import DecisionOpportunitySnapshot, ProposalDraft, ProposalRecord
from .demo_dispatch import (
    DemoDispatchResult,
    Poster,
    QueryFn,
    TpslPoster,
    dispatch_intents,
    observation_from_query,
)
from .mandate import TradingMandate
from .mandate_store import recover_session
from .order_intent import PaperOrderIntent
from .paper_agent import PaperAgent, PaperAgentResult
from .reconcile import PaperReconcile
from .risk_engine import RiskCheckRecord


SCAN_RAN_EVENT = "PAPER_SCAN_RAN"
SCAN_SKIPPED_EVENT = "PAPER_SCAN_SKIPPED"
DISPATCH_EVENT = "ORDER_DISPATCH_RESULT"

REASON_NOT_DUE = "NOT_DUE"
REASON_STALE = "SNAPSHOT_STALE"
REASON_UNKNOWN = "RECONCILE_REQUIRED"
REASON_ZONE = "ZONE_NOT_ACTIVE"
REASON_INACTIVE = "MANDATE_INACTIVE"
REASON_INTERVAL = "REVIEW_INTERVAL_MISSING"
REASON_RAN = "REVIEW_RAN"

_SKIP_RATIONALE = {
    REASON_NOT_DUE: "paper scan not due; no AI call",
    REASON_STALE: "stale snapshot; paper scan NO_TRADE",
    REASON_UNKNOWN: "UNKNOWN or unreconciled paper intent; paper scan NO_TRADE",
    REASON_ZONE: "zone not ACTIVE; paper scan NO_TRADE",
    REASON_INACTIVE: "mandate inactive or expired; paper scan NO_TRADE without flatten",
    REASON_INTERVAL: "position_review_interval missing; paper scan NO_TRADE",
}


class LocalNoTradeProvider:
    """Deterministic paper provider used when CLI has no candidate. Never hits a network."""

    def propose(self, snapshot: DecisionOpportunitySnapshot) -> ProposalDraft:
        return ProposalDraft.from_snapshot(
            snapshot,
            proposal_id=f"scan-no-trade-{snapshot.opportunity_id}",
            model_version="paper-scan-local",
            policy_version="paper-scan",
            action="NO_TRADE",
            rationale="paper scan default no-trade; no exchange POST",
            decision_timestamp=snapshot.snapshot_at,
        )


@dataclass(frozen=True)
class ScanDispatchOptions:
    """Opt-in Demo dispatch after a due scan creates paper intents."""

    confirm_demo: bool = False
    dry_run: bool = True
    poster: Poster | None = None
    tpsl_poster: TpslPoster | None = None
    query: QueryFn | None = None
    environ: Mapping[str, str] | None = None
    pos_mode: str = "hedge_mode"


@dataclass(frozen=True)
class PaperScanResult:
    due: bool
    ran: bool
    reason_code: str
    reviewed_at: str | None
    next_due_at: str | None
    proposal: ProposalRecord | None
    risk_check: RiskCheckRecord | None
    intent: PaperOrderIntent | None
    intents: tuple[PaperOrderIntent, ...] = ()
    dispatch_results: tuple[DemoDispatchResult, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        action = "NO_TRADE"
        if self.proposal is not None and self.proposal.proposal is not None:
            action = self.proposal.proposal.action
        intent_count = len(self.intents) if self.intents else (0 if self.intent is None else 1)
        posted = any(item.posted for item in self.dispatch_results)
        return {
            "action": action,
            "dispatch_results": [item.to_dict() for item in self.dispatch_results],
            "due": self.due,
            "dry_run": not posted,
            "exchange_post": posted,
            "intent_client_oid": None if self.intent is None else self.intent.client_oid,
            "intent_count": intent_count,
            "next_due_at": self.next_due_at,
            "ran": self.ran,
            "reason_code": self.reason_code,
            "reviewed_at": self.reviewed_at,
        }


def _parse_dt(value: str, name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def last_reviewed_at(store: Any, zone_id: str) -> str | None:
    getter = getattr(store, "agent_events", None)
    if getter is None:
        return None
    last: str | None = None
    for event in getter(zone_id):
        if event.get("event") != SCAN_RAN_EVENT:
            continue
        stamp = event.get("reviewed_at")
        if isinstance(stamp, str) and stamp.strip():
            last = stamp
    return last


def next_due_at(mandate: TradingMandate, last: str | None, now: str) -> str | None:
    interval = mandate.position_review_interval
    if interval is None:
        return None
    if last is None:
        return now
    return _iso(_parse_dt(last, "last_reviewed_at") + timedelta(minutes=interval))


def is_due(mandate: TradingMandate, now: str, last: str | None) -> bool:
    if mandate.position_review_interval is None:
        return False
    due_at = next_due_at(mandate, last, now)
    if due_at is None:
        return False
    return _parse_dt(now, "now") >= _parse_dt(due_at, "next_due_at")


def _zone_state(store: Any, zone_id: str) -> str | None:
    zone_store = getattr(store, "zone_store", None)
    if zone_store is None:
        return None
    try:
        return zone_store.get_zone(zone_id).state
    except Exception:
        return None


def _no_trade(snapshot: DecisionOpportunitySnapshot, reason_code: str, now: str) -> ProposalRecord:
    return no_trade_proposal(
        snapshot,
        proposal_id=f"scan-{reason_code.lower()}-{snapshot.opportunity_id}",
        model_version="paper-scan-local",
        policy_version="paper-scan",
        rationale=_SKIP_RATIONALE.get(reason_code, "paper scan NO_TRADE"),
        decision_timestamp=now,
    )


def _skip(
    store: Any,
    snapshot: DecisionOpportunitySnapshot,
    mandate: TradingMandate,
    *,
    reason_code: str,
    now: str,
    last: str | None,
    persist_proposal: bool,
) -> PaperScanResult:
    due = reason_code != REASON_NOT_DUE and is_due(mandate, now, last)
    proposal = _no_trade(snapshot, reason_code, now)
    payload = {
        "opportunity_id": snapshot.opportunity_id,
        "reason_code": reason_code,
        "next_due_at": next_due_at(mandate, last, now),
    }
    store.append_agent_event(mandate.zone_id, SCAN_SKIPPED_EVENT, payload)
    if persist_proposal:
        store.append_agent_event(
            mandate.zone_id,
            "AI_DECISION_BLOCKED",
            {"opportunity_id": snapshot.opportunity_id, "reason_code": reason_code},
        )
        store.record_proposal(proposal.to_dict(), zone_id=mandate.zone_id)
    return PaperScanResult(
        due=due,
        ran=False,
        reason_code=reason_code,
        reviewed_at=last,
        next_due_at=next_due_at(mandate, last, now),
        proposal=proposal,
        risk_check=None,
        intent=None,
        intents=(),
    )


def _already_sent(store: Any, zone_id: str, client_oid: str) -> bool:
    getter = getattr(store, "agent_events", None)
    if getter is None:
        return False
    for event in getter(zone_id):
        if event.get("event") != DISPATCH_EVENT:
            continue
        if event.get("client_oid") != client_oid:
            continue
        if event.get("exchange_post"):
            return True
        if event.get("result") in {"POSTED", "REJECTED", "UNKNOWN"}:
            return True
        if event.get("dispatch") in {"FOUND", "REJECTED", "UNKNOWN"}:
            return True
    return False


def _dispatch_created(
    store: Any,
    mandate: TradingMandate,
    intents: tuple[PaperOrderIntent, ...],
    dispatch: ScanDispatchOptions | None,
) -> tuple[DemoDispatchResult, ...]:
    if dispatch is None or not intents:
        return ()
    pending = tuple(intent for intent in intents if not _already_sent(store, mandate.zone_id, intent.client_oid))
    if not pending:
        return ()
    results = dispatch_intents(
        pending,
        allowed_symbols=mandate.allowed_symbols,
        confirm_demo=dispatch.confirm_demo,
        dry_run=dispatch.dry_run,
        environ=dispatch.environ,
        poster=dispatch.poster,
        tpsl_poster=dispatch.tpsl_poster,
        pos_mode=dispatch.pos_mode,
    )
    by_oid = {intent.client_oid: intent for intent in pending}
    updated: list[DemoDispatchResult] = []
    for item in results:
        payload = item.to_dict()
        intent = by_oid.get(item.client_oid)
        if item.posted and dispatch.query is not None and intent is not None:
            try:
                queried = dispatch.query(intent)
                reconciled = PaperReconcile(store).apply(observation_from_query(intent, queried))
                item = DemoDispatchResult(**{**item.__dict__, "reconcile": reconciled.result})
                payload = item.to_dict()
            except Exception:
                PaperReconcile(store).record_timeout(item.client_oid)
                item = DemoDispatchResult(**{**item.__dict__, "reconcile": "unknown"})
                payload = item.to_dict()
        elif item.dispatch == "UNKNOWN" or item.result == "UNKNOWN":
            PaperReconcile(store).record_timeout(item.client_oid)
        store.append_agent_event(mandate.zone_id, DISPATCH_EVENT, payload)
        updated.append(item)
    return tuple(updated)


def tick(
    agent: PaperAgent,
    snapshot: DecisionOpportunitySnapshot,
    mandate: TradingMandate,
    *,
    now: str,
    stale: bool = False,
    kill_switch: bool = False,
    dispatch: ScanDispatchOptions | None = None,
) -> PaperScanResult:
    """One paper scan tick. Calls AI only when the review interval is due."""
    store = agent.store
    last = last_reviewed_at(store, mandate.zone_id)

    if mandate.position_review_interval is None:
        return _skip(store, snapshot, mandate, reason_code=REASON_INTERVAL, now=now, last=last, persist_proposal=True)
    if not mandate.is_active(now):
        return _skip(store, snapshot, mandate, reason_code=REASON_INACTIVE, now=now, last=last, persist_proposal=True)

    zone_state = _zone_state(store, mandate.zone_id)
    autonomous_open = mandate.ai_autonomy == "AUTONOMOUS_WITHIN_MANDATE" and zone_state is None
    if zone_state != "ACTIVE" and not autonomous_open:
        return _skip(store, snapshot, mandate, reason_code=REASON_ZONE, now=now, last=last, persist_proposal=True)

    recovery = recover_session(store, mandate.zone_id, mandate.mandate_id)
    if recovery.has_unknown():
        return _skip(store, snapshot, mandate, reason_code=REASON_UNKNOWN, now=now, last=last, persist_proposal=True)
    if stale:
        return _skip(store, snapshot, mandate, reason_code=REASON_STALE, now=now, last=last, persist_proposal=True)
    if not is_due(mandate, now, last):
        return _skip(store, snapshot, mandate, reason_code=REASON_NOT_DUE, now=now, last=last, persist_proposal=False)

    result: PaperAgentResult = agent.run(snapshot, mandate, kill_switch=kill_switch, stale=False, now=now)
    dispatch_results = _dispatch_created(store, mandate, result.intents, dispatch)
    store.append_agent_event(
        mandate.zone_id,
        SCAN_RAN_EVENT,
        {
            "opportunity_id": snapshot.opportunity_id,
            "reason_code": REASON_RAN,
            "reviewed_at": now,
            "next_due_at": next_due_at(mandate, now, now),
        },
    )
    return PaperScanResult(
        due=True,
        ran=True,
        reason_code=REASON_RAN,
        reviewed_at=now,
        next_due_at=next_due_at(mandate, now, now),
        proposal=result.proposal,
        risk_check=result.risk_check,
        intent=result.intent,
        intents=result.intents,
        dispatch_results=dispatch_results,
    )


def run_loop(
    agent: PaperAgent,
    snapshot: DecisionOpportunitySnapshot,
    mandate: TradingMandate,
    *,
    now_fn: Callable[[], str],
    sleep: Callable[[float], None],
    poll_seconds: float,
    max_ticks: int,
    stale: bool = False,
    kill_switch: bool = False,
    dispatch: ScanDispatchOptions | None = None,
) -> list[PaperScanResult]:
    """Repeat ``tick`` locally. Sleep is injected; this is not a protection-clock poll."""
    if max_ticks < 1:
        raise ValueError("max_ticks must be >= 1")
    if poll_seconds <= 0:
        raise ValueError("poll_seconds must be positive")
    results: list[PaperScanResult] = []
    for index in range(max_ticks):
        results.append(
            tick(
                agent,
                snapshot,
                mandate,
                now=now_fn(),
                stale=stale,
                kill_switch=kill_switch,
                dispatch=dispatch,
            )
        )
        if index + 1 < max_ticks:
            sleep(poll_seconds)
    return results
