"""Deterministic paper order intents derived from approved proposals."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import hashlib
from typing import Any, Mapping

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
    order_type: str = "limit"
    order_role: str = "entry"
    reduce_only: bool = False
    filled_quantity: Decimal = Decimal("0")
    remaining_quantity: Decimal | None = None

    def to_record(self) -> dict[str, Any]:
        remaining = self.quantity - self.filled_quantity if self.remaining_quantity is None else self.remaining_quantity
        return {
            "client_oid": self.client_oid,
            "intent_id": self.client_oid,
            "zone_id": self.zone_id,
            "decision_id": self.decision_id,
            "risk_check_id": self.risk_check_id,
            "mandate_id": self.mandate_id,
            "mandate_version": self.mandate_version,
            "symbol": self.symbol,
            "role": self.order_role,
            "side": ("sell" if self.side == "long" else "buy") if self.reduce_only else ("buy" if self.side == "long" else "sell"),
            "position_side": self.side,
            "quantity": format(self.quantity, "f"),
            "price": format(self.price, "f"),
            "state": self.state,
            "order_type": self.order_type,
            "order_role": self.order_role,
            "reduce_only": self.reduce_only,
            "filled_quantity": format(self.filled_quantity, "f"),
            "remaining_quantity": format(remaining, "f"),
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "source": "ai_agent",
            "paper": True,
            "dry_run": True,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "PaperOrderIntent":
        return cls(
            client_oid=str(record["client_oid"]),
            zone_id=str(record["zone_id"]),
            decision_id=str(record["decision_id"]),
            risk_check_id=str(record["risk_check_id"]),
            mandate_id=str(record["mandate_id"]),
            mandate_version=int(record["mandate_version"]),
            symbol=str(record["symbol"]),
            side=str(record.get("position_side") or record["side"]),
            quantity=Decimal(str(record["quantity"])),
            price=Decimal(str(record["price"])),
            stop_loss=None if record.get("stop_loss") is None else str(record["stop_loss"]),
            take_profit=None if record.get("take_profit") is None else str(record["take_profit"]),
            state=str(record.get("state", "paper_pending")),
            order_type=str(record.get("order_type", "limit")),
            order_role=str(record.get("order_role") or record.get("role") or "entry"),
            reduce_only=bool(record.get("reduce_only", False)),
            filled_quantity=Decimal(str(record.get("filled_quantity", "0"))),
            remaining_quantity=Decimal(str(record["remaining_quantity"])) if record.get("remaining_quantity") is not None else None,
        )


def intent_from_proposal(
    proposal: ProposalDraft,
    *,
    zone_id: str,
    mandate_id: str,
    mandate_version: int,
    risk_check_id: str,
) -> PaperOrderIntent | None:
    """Map an approved proposal to a paper intent; never dispatch to an exchange."""
    if proposal.action in {"NO_TRADE", "HOLD"}:
        return None
    if proposal.action not in {"OPEN", "CLOSE", "REDUCE", "ADJUST_SL", "CANCEL"}:
        raise PaperIntentError(f"paper does not map action {proposal.action}")
    metadata = dict(proposal.metadata)
    order_type = str(metadata.get("order_type", "limit")).strip().lower()
    default_role = {
        "OPEN": "entry",
        "CLOSE": "reduce",
        "REDUCE": "reduce",
        "ADJUST_SL": "adjust_sl",
        "CANCEL": "cancel",
    }[proposal.action]
    order_role = str(metadata.get("order_role", default_role)).strip().lower()
    reduce_only = True if proposal.action in {"CLOSE", "REDUCE"} else bool(metadata.get("reduce_only", False))
    if proposal.action in {"CLOSE", "REDUCE"} and not reduce_only:
        raise PaperIntentError("paper CLOSE/REDUCE must be reduce-only")
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
        order_type=order_type,
        order_role=order_role,
        reduce_only=reduce_only,
    )
