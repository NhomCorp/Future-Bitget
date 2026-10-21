"""Offline tests for mandate-backed paper agent decisions."""
from __future__ import annotations

import os
import tempfile
import unittest
from decimal import Decimal

from ai_proposal.schema import DecisionOpportunitySnapshot, HardLimits, ProposalDraft
from executor.p1_adapter import P1IntegrationStore
from trader.zone_store import ZoneStore
from trading.mandate import TradingMandate
from trading.paper_agent import PaperAgent


NOW = "2026-10-21T10:00:00Z"


def make_snapshot() -> DecisionOpportunitySnapshot:
    return DecisionOpportunitySnapshot(
        opportunity_id="opp-paper-1",
        snapshot_at=NOW,
        feature_as_of=NOW,
        symbol="BTCUSDT",
        side="long",
        state="READY",
        ref_price=Decimal("100"),
        sl_pct=Decimal("5"),
        loss_budget=Decimal("20"),
        size=Decimal("1"),
        exposure=Decimal("100"),
        hard_limits=HardLimits(
            allowed_symbols=("BTCUSDT",),
            allowed_sides=("long", "short"),
            allowed_states=("READY",),
            max_size=Decimal("2"),
            max_exposure=Decimal("200"),
        ),
        features={"trend": "up"},
    )


def make_proposal(snapshot: DecisionOpportunitySnapshot, **overrides) -> ProposalDraft:
    fields = dict(
        proposal_id="decision-1",
        opportunity_id=snapshot.opportunity_id,
        decision_timestamp=NOW,
        feature_as_of=snapshot.feature_as_of,
        model_version="fake-1",
        policy_version="policy-1",
        action="OPEN",
        rationale="paper test candidate",
        symbol=snapshot.symbol,
        side=snapshot.side,
        state=snapshot.state,
        ref_price=snapshot.ref_price,
        sl_pct=snapshot.sl_pct,
        loss_budget=snapshot.loss_budget,
        size=snapshot.size,
        exposure=snapshot.exposure,
        metadata={"stop_loss": "95"},
    )
    fields.update(overrides)
    return ProposalDraft(**fields)


class FakeProvider:
    def __init__(self, proposal=None, error=None):
        self.proposal = proposal
        self.error = error

    def propose(self, snapshot):
        if self.error:
            raise self.error
        return self.proposal


class PaperAgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "zones.sqlite3")
        self.zones = ZoneStore(self.path)
        self.zones.create_zone(
            {"symbol": "BTCUSDT", "side": "long", "ref_price": "100", "zone_loss_limit_usdt": "20", "sl_pct": "5"},
            zone_id="zone-paper",
            state="ACTIVE",
        )
        self.store = P1IntegrationStore(self.zones)
        self.snapshot = make_snapshot()
        self.mandate = TradingMandate(
            mandate_id="mandate-1",
            version=1,
            zone_id="zone-paper",
            allowed_symbols=("BTCUSDT",),
            allowed_sides=("long",),
            allowed_actions=("OPEN", "NO_TRADE"),
            max_size=Decimal("1"),
            max_exposure=Decimal("100"),
            loss_budget=Decimal("20"),
            max_order_risk=Decimal("5"),
            valid_from="2026-10-21T09:00:00Z",
            valid_until="2026-10-21T11:00:00Z",
        )

    def tearDown(self):
        self.store.close()
        self.zones.close()
        self.tmp.cleanup()

    def test_approved_decision_creates_idempotent_paper_intent(self):
        agent = PaperAgent(FakeProvider(make_proposal(self.snapshot)), self.store)
        first = agent.run(self.snapshot, self.mandate, now=NOW)
        second = agent.run(self.snapshot, self.mandate, now=NOW)
        self.assertEqual(first.risk_check.result, "APPROVED")
        self.assertEqual(first.intent.client_oid, second.intent.client_oid)
        self.assertEqual(len(self.store.paper_intents("zone-paper")), 1)
        intent = self.store.paper_intents("zone-paper")[0]
        self.assertTrue(intent["paper"])
        self.assertTrue(intent["dry_run"])
        self.assertEqual(intent["risk_check_id"], first.risk_check.risk_check_id)

    def test_provider_failure_creates_no_intent(self):
        agent = PaperAgent(FakeProvider(error=RuntimeError("provider failed")), self.store)
        result = agent.run(self.snapshot, self.mandate, now=NOW)
        self.assertIsNone(result.intent)
        self.assertEqual(self.store.paper_intents("zone-paper"), [])
        self.assertEqual(self.store.agent_events("zone-paper")[0]["event"], "AI_PROVIDER_FAILED")

    def test_mandate_rejection_creates_no_intent(self):
        narrow = TradingMandate(
            mandate_id="mandate-small",
            version=1,
            zone_id="zone-paper",
            allowed_symbols=("ETHUSDT",),
            allowed_sides=("long",),
            allowed_actions=("OPEN",),
            max_size=Decimal("1"),
            max_exposure=Decimal("100"),
            loss_budget=Decimal("20"),
            max_order_risk=Decimal("5"),
            valid_from="2026-10-21T09:00:00Z",
            valid_until="2026-10-21T11:00:00Z",
        )
        result = PaperAgent(FakeProvider(make_proposal(self.snapshot)), self.store).run(self.snapshot, narrow, now=NOW)
        self.assertEqual(result.risk_check.result, "REJECTED")
        self.assertIn("SYMBOL_NOT_ALLOWED", result.risk_check.reason_codes)
        self.assertIsNone(result.intent)

    def test_kill_switch_and_stale_snapshot_pause_decision(self):
        agent = PaperAgent(FakeProvider(make_proposal(self.snapshot)), self.store)
        result = agent.run(self.snapshot, self.mandate, now=NOW, kill_switch=True)
        self.assertEqual(result.risk_check.result, "PAUSED")
        self.assertIsNone(result.intent)
        result = agent.run(self.snapshot, self.mandate, now=NOW, stale=True)
        self.assertEqual(result.risk_check.result, "PAUSED")
        self.assertIsNone(result.intent)

    def test_missing_required_stop_rejected(self):
        proposal = make_proposal(self.snapshot, metadata={})
        result = PaperAgent(FakeProvider(proposal), self.store).run(self.snapshot, self.mandate, now=NOW)
        self.assertEqual(result.risk_check.result, "REJECTED")
        self.assertIn("PROTECTIVE_STOP_REQUIRED", result.risk_check.reason_codes)
        self.assertIsNone(result.intent)


if __name__ == "__main__":
    unittest.main()
