"""Model/provider-agnostic proposal boundary.

Adapters receive one immutable snapshot and may return only a candidate.  The
validator is always applied before a record is accepted.  This module performs
no model calls, network I/O, credential access, or exchange actions.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Mapping, Protocol

from .schema import DecisionOpportunitySnapshot, ProposalDraft, ProposalRecord, ValidationError
from .validator import evaluate_proposal, reject_candidate


class ProposalAdapter(Protocol):
    """Pure adapter contract. Implementations must not perform side effects."""

    def propose(self, snapshot: DecisionOpportunitySnapshot) -> ProposalDraft | Mapping[str, Any]:
        """Produce one candidate from exactly one snapshot."""


Adapter = Callable[[DecisionOpportunitySnapshot], ProposalDraft | Mapping[str, Any]]


def _candidate_to_draft(
    snapshot: DecisionOpportunitySnapshot,
    candidate: ProposalDraft | Mapping[str, Any],
) -> ProposalDraft:
    if isinstance(candidate, ProposalDraft):
        return candidate
    if not isinstance(candidate, Mapping):
        raise TypeError("adapter must return ProposalDraft or a mapping")
    return ProposalDraft.from_dict(candidate)


def propose(
    snapshot: DecisionOpportunitySnapshot,
    adapter: ProposalAdapter | Adapter,
) -> ProposalRecord:
    """Invoke an adapter once and deterministically evaluate its candidate.

    Adapter exceptions are represented as a rejected proposal record, rather than
    escaping into an execution path.  The exception text is intentionally not
    copied into the record to avoid leaking credentials or provider internals.
    """
    candidate: ProposalDraft | Mapping[str, Any] | None = None
    proposal_id = f"rejected-{snapshot.opportunity_id}"
    try:
        candidate = adapter.propose(snapshot) if hasattr(adapter, "propose") else adapter(snapshot)
        if isinstance(candidate, ProposalDraft):
            proposal_id = candidate.proposal_id
        elif isinstance(candidate, Mapping) and isinstance(candidate.get("proposal_id"), str):
            proposal_id = candidate["proposal_id"]
        draft = _candidate_to_draft(snapshot, candidate)
    except Exception:
        return reject_candidate(
            snapshot,
            proposal_id=proposal_id,
            candidate=candidate if isinstance(candidate, Mapping) else None,
            errors=(ValidationError("ADAPTER_OUTPUT_INVALID", "candidate", "adapter output is invalid"),),
        )
    return evaluate_proposal(snapshot, draft)


def no_trade_proposal(
    snapshot: DecisionOpportunitySnapshot,
    *,
    proposal_id: str,
    model_version: str,
    policy_version: str,
    rationale: str,
    decision_timestamp: str | None = None,
) -> ProposalRecord:
    """Create and validate an explicit no-trade proposal."""
    draft = ProposalDraft.from_snapshot(
        snapshot,
        proposal_id=proposal_id,
        model_version=model_version,
        policy_version=policy_version,
        action="NO_TRADE",
        rationale=rationale,
        decision_timestamp=decision_timestamp,
    )
    return evaluate_proposal(snapshot, draft)
