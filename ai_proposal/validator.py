"""Deterministic hard-limit validation for model-agnostic proposals."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .schema import (
    DecisionOpportunitySnapshot,
    ProposalDraft,
    ProposalRecord,
    ValidationError,
    RESULT_ACCEPTED,
    RESULT_REJECTED,
)


def _error(code: str, field: str, message: str, expected: Any = None, actual: Any = None) -> ValidationError:
    return ValidationError(code=code, field=field, message=message, expected=expected, actual=actual)


def validate_proposal(snapshot: DecisionOpportunitySnapshot, proposal: ProposalDraft) -> tuple[ValidationError, ...]:
    """Validate candidate against immutable snapshot and hard limits.

    This function compares every execution-sensitive field, including fields that
    an adapter must never be allowed to alter.  It has no side effects.
    """
    errors: list[ValidationError] = []
    limits = snapshot.hard_limits
    if proposal.opportunity_id != snapshot.opportunity_id:
        errors.append(_error("OPPORTUNITY_MISMATCH", "opportunity_id", "proposal must target the input opportunity", snapshot.opportunity_id, proposal.opportunity_id))
    if proposal.symbol != snapshot.symbol:
        errors.append(_error("SYMBOL_IMMUTABLE", "symbol", "proposal cannot change symbol", snapshot.symbol, proposal.symbol))
    if proposal.side != snapshot.side:
        errors.append(_error("SIDE_IMMUTABLE", "side", "proposal cannot change side", snapshot.side, proposal.side))
    if proposal.state != snapshot.state:
        errors.append(_error("STATE_IMMUTABLE", "state", "proposal cannot change state", snapshot.state, proposal.state))
    for field_name in ("loss_budget", "sl_pct", "ref_price"):
        expected = getattr(snapshot, field_name)
        actual = getattr(proposal, field_name)
        if actual != expected:
            errors.append(_error(f"{field_name.upper()}_IMMUTABLE", field_name, f"proposal cannot change {field_name}", str(expected), str(actual)))
    if proposal.size != snapshot.size:
        errors.append(_error("SIZE_IMMUTABLE", "size", "proposal cannot change size", str(snapshot.size), str(proposal.size)))
    if proposal.exposure != snapshot.exposure:
        errors.append(_error("EXPOSURE_IMMUTABLE", "exposure", "proposal cannot change exposure", str(snapshot.exposure), str(proposal.exposure)))
    if proposal.symbol not in limits.allowed_symbols:
        errors.append(_error("SYMBOL_NOT_ALLOWED", "symbol", "symbol is outside the hard allowlist", list(limits.allowed_symbols), proposal.symbol))
    if proposal.side not in limits.allowed_sides:
        errors.append(_error("SIDE_NOT_ALLOWED", "side", "side is outside the hard allowlist", list(limits.allowed_sides), proposal.side))
    if proposal.state not in limits.allowed_states:
        errors.append(_error("STATE_NOT_ALLOWED", "state", "state is outside the hard allowlist", list(limits.allowed_states), proposal.state))
    if proposal.size < 0 or proposal.size > limits.max_size:
        errors.append(_error("SIZE_HARD_LIMIT", "size", "size exceeds the hard limit", str(limits.max_size), str(proposal.size)))
    if proposal.exposure < 0 or proposal.exposure > limits.max_exposure:
        errors.append(_error("EXPOSURE_HARD_LIMIT", "exposure", "exposure exceeds the hard limit", str(limits.max_exposure), str(proposal.exposure)))
    return tuple(errors)


def evaluate_proposal(
    snapshot: DecisionOpportunitySnapshot,
    proposal: ProposalDraft,
) -> ProposalRecord:
    """Return ACCEPTED or REJECTED without executing or dispatching anything."""
    errors = validate_proposal(snapshot, proposal)
    if errors:
        return ProposalRecord.rejected(
            snapshot,
            proposal_id=proposal.proposal_id,
            errors=errors,
            proposal=proposal,
            raw_candidate=proposal.to_dict(),
        )
    return ProposalRecord.accepted(snapshot, proposal)


def reject_candidate(
    snapshot: DecisionOpportunitySnapshot,
    *,
    proposal_id: str,
    candidate: Mapping[str, Any] | None,
    errors: tuple[ValidationError, ...],
) -> ProposalRecord:
    """Build a REJECTED record for an unparseable or incomplete adapter output."""
    return ProposalRecord.rejected(
        snapshot,
        proposal_id=proposal_id,
        errors=errors,
        raw_candidate=candidate,
    )
