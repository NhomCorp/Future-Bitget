"""Provider contract for paper-only proposal generation.

Concrete network clients are intentionally out of scope for P1.
"""
from __future__ import annotations

from typing import Protocol

from ai_proposal.schema import DecisionOpportunitySnapshot, ProposalDraft


class AIProvider(Protocol):
    """Return one proposal from a snapshot without exchange side effects."""

    def propose(self, snapshot: DecisionOpportunitySnapshot) -> ProposalDraft: ...


class StaticPaperProvider:
    """Deterministic provider used for offline paper tests and demonstrations."""

    def __init__(self, proposal: ProposalDraft):
        self._proposal = proposal

    def propose(self, snapshot: DecisionOpportunitySnapshot) -> ProposalDraft:
        if self._proposal.opportunity_id != snapshot.opportunity_id:
            raise ValueError("proposal opportunity does not match snapshot")
        return self._proposal
