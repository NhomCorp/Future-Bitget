"""Deterministic paper order intents derived from approved proposals."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import hashlib
from typing import Any

from ai_proposal.schema import ProposalDraft


class PaperIntentError(ValueError):
    """Raised when a proposal cannot become a paper intent."""


def paper_client_oid(mandate_id: str, decision_id: str, action: str) -> str:
    """Return a stable client id for one logical paper order."""
    canonical = "\x1f".join((mandate_id, decision_id, action.upper()))
    return "ai-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True)
class PaperOrderIntent:
    """A persistence-safe paper intent; it never dispatches to an exchange."""

    client_oid: str
    zone_id: str
    decision_id: str
    risk_check_id: str
    mandate_id: str
    mandate_version: int
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    stop_loss: str | None
    take_profit: str | None
    state: str = "paper_pending"

    def to_record(self) -> dict[str, Any]:
        return {
            "client_oid": self.client_oid,
            "intent_id": self.client_oid,
            "zone_id": self.zone_id,
            "decision_id": self.decision_id,
            "risk_check_id": self.risk_check_id,
            "mandate_id": self.mandate_id,
            "mandate_version": self.mandate_version,
            "symbol": self.symbol,
            "role": "entry",
            "side": "buy" if self.side == "long" else "sell",
            "position_side": self.side,
            "quantity": format(self.quantity, "f"),
            "price": format(self.price, "f"),
            "state": self.state,
            "filled_quantity": "0",
            "remaining_quantity": format(self.quantity, "f"),
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "source": "ai_agent",
            "paper": True,
            "dry_run": True,
        }


def intent_from_proposal(
    proposal: ProposalDraft,
    *,
    zone_id: str,
    mandate_id: str,
    mandate_version: int,
    risk_check_id: str,
) -> PaperOrderIntent | None:
    """Map only an approved OPEN proposal to an entry intent."""
    if proposal.action in {"NO_TRADE", "HOLD"}:
        return None
    if proposal.action != "OPEN":
        raise PaperIntentError(f"paper P1 does not dispatch action {proposal.action}")
    metadata = dict(proposal.metadata)
    return PaperOrderIntent(
        client_oid=paper_client_oid(mandate_id, proposal.proposal_id, proposal.action),
        zone_id=zone_id,
        decision_id=proposal.proposal_id,
        risk_check_id=risk_check_id,
        mandate_id=mandate_id,
        mandate_version=mandate_version,
        symbol=proposal.symbol,
        side=proposal.side,
        quantity=proposal.size,
        price=proposal.ref_price,
        stop_loss=None if metadata.get("stop_loss") is None else str(metadata["stop_loss"]),
        take_profit=None if metadata.get("take_profit") is None else str(metadata["take_profit"]),
    )
