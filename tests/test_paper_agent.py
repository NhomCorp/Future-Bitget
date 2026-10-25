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
        features={"trend": "up", "daily_loss": "0", "day_start_equity": "1000", "daily_loss_at": NOW, "drawdown": "0", "drawdown_unit": "usdt", "consecutive_losses": "0"},
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
        metadata={"stop_loss": "95", "leverage": "2"},
    )
    fields.update(overrides)
    return ProposalDraft(**fields)


class FakeProvider:
    def __init__(self, proposal=None, error=None):
        self.proposal = proposal
        self.error = error
        self.calls = 0

    def propose(self, snapshot):
        self.calls += 1
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
        self.mandate = self._mandate()

    def _mandate(self, **overrides) -> TradingMandate:
        values = dict(
            mandate_id="mandate-1",
            version=1,
            zone_id="zone-paper",
            allowed_symbols=("BTCUSDT",),
            allowed_sides=("long",),
            allowed_actions=("OPEN", "CLOSE", "REDUCE", "NO_TRADE"),
            max_size=Decimal("1"),
            max_exposure=Decimal("100"),
            loss_budget=Decimal("20"),
            max_order_risk=Decimal("5"),
            valid_from="2026-10-21T09:00:00Z",
            valid_until="2026-10-21T11:00:00Z",
            daily_loss_limit_pct=Decimal("1"),
            daily_loss_reference="day_start_equity",
            daily_loss_reset_time_utc="00:00",
            drawdown_limit=Decimal("20"),
            drawdown_unit="usdt",
            max_leverage=Decimal("3"),
            daily_loss_scope="subaccount",
            drawdown_scope="subaccount",
            drawdown_reference="equity_peak",
            ai_autonomy="MANAGED_ZONE",
            granted_capital=Decimal("1000"),
            capital_currency="USDT",
            daily_loss_action="FREEZE_ENTRY",
            max_consecutive_losses=3,
            loss_streak_scope="subaccount",
            loss_streak_cooldown="24h",
            allow_average_down=False,
            position_review_interval=15,
        )
        values.update(overrides)
        return TradingMandate(**values)

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
        narrow = self._mandate(mandate_id="mandate-small", allowed_symbols=("ETHUSDT",), allowed_actions=("OPEN",))
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

    def test_proposal_only_records_without_intent(self):
        mandate = self._mandate(ai_autonomy="PROPOSAL_ONLY")
        result = PaperAgent(FakeProvider(make_proposal(self.snapshot)), self.store).run(self.snapshot, mandate, now=NOW)
        self.assertEqual(result.risk_check.result, "APPROVED")
        self.assertIsNone(result.intent)
        self.assertEqual(self.store.paper_intents("zone-paper"), [])
        self.assertTrue(any(event["event"] == "RISK_CHECKED" for event in self.store.agent_events("zone-paper")))

    def test_autonomous_mode_creates_paper_intent(self):
        mandate = self._mandate(ai_autonomy="AUTONOMOUS_WITHIN_MANDATE")
        result = PaperAgent(FakeProvider(make_proposal(self.snapshot)), self.store).run(self.snapshot, mandate, now=NOW)
        self.assertEqual(result.risk_check.result, "APPROVED")
        self.assertIsNotNone(result.intent)
        self.assertEqual(len(self.store.paper_intents("zone-paper")), 1)

    def test_plan_actions_creates_approved_steps_only(self):
        mandate = self._mandate(allowed_actions=("OPEN", "CLOSE", "REDUCE", "ADJUST_SL", "NO_TRADE"))
        snapshot = make_snapshot()
        snapshot = DecisionOpportunitySnapshot(
            opportunity_id=snapshot.opportunity_id,
            snapshot_at=snapshot.snapshot_at,
            feature_as_of=snapshot.feature_as_of,
            symbol=snapshot.symbol,
            side=snapshot.side,
            state=snapshot.state,
            ref_price=snapshot.ref_price,
            sl_pct=snapshot.sl_pct,
            loss_budget=snapshot.loss_budget,
            size=snapshot.size,
            exposure=snapshot.exposure,
            hard_limits=snapshot.hard_limits,
            features={**dict(snapshot.features), "current_stop_loss": "95"},
        )
        proposal = make_proposal(
            snapshot,
            action="REDUCE",
            metadata={
                "leverage": "2",
                "order_type": "limit",
                "order_role": "reduce",
                "reduce_only": True,
                "stop_loss": "96",
                "plan_actions": [
                    {"action": "REDUCE", "size": "0.4", "order_type": "limit", "order_role": "reduce", "reduce_only": True, "leverage": "2"},
                    {"action": "ADJUST_SL", "stop_loss": "96", "leverage": "2"},
                    {"action": "OPEN", "order_role": "dca", "stop_loss": "95", "leverage": "2"},
                ],
            },
        )
        result = PaperAgent(FakeProvider(proposal), self.store).run(snapshot, mandate, now=NOW)
        self.assertEqual(len(result.risk_checks), 3)
        self.assertEqual(result.risk_checks[0].result, "APPROVED")
        self.assertEqual(result.risk_checks[1].result, "APPROVED")
        self.assertEqual(result.risk_checks[2].result, "REJECTED")
        self.assertIn("AVERAGE_DOWN_DISABLED", result.risk_checks[2].reason_codes)
        self.assertEqual(len(result.intents), 2)
        self.assertEqual(result.intents[0].order_role, "reduce")
        self.assertEqual(result.intents[1].order_role, "adjust_sl")

    def test_autonomous_open_without_zone_creates_local_zone(self):
        mandate = self._mandate(zone_id="zone-ai-new", ai_autonomy="AUTONOMOUS_WITHIN_MANDATE")
        result = PaperAgent(FakeProvider(make_proposal(self.snapshot)), self.store).run(self.snapshot, mandate, now=NOW)
        self.assertEqual(result.risk_check.result, "APPROVED")
        self.assertIsNotNone(result.intent)
        zone = self.zones.get_zone("zone-ai-new")
        self.assertEqual(zone.state, "ACTIVE")
        self.assertEqual(str(zone.config.get("opened_by")), "ai")

    def test_close_creates_reduce_only_paper_intent(self):
        proposal = make_proposal(
            self.snapshot,
            action="CLOSE",
            metadata={"leverage": "2", "order_type": "limit", "order_role": "reduce", "reduce_only": True},
        )
        result = PaperAgent(FakeProvider(proposal), self.store).run(self.snapshot, self.mandate, now=NOW)
        self.assertEqual(result.risk_check.result, "APPROVED")
        self.assertTrue(result.intent.reduce_only)
        self.assertEqual(result.intent.order_role, "reduce")
        self.assertEqual(self.store.paper_intents("zone-paper")[0]["role"], "reduce")
        self.assertTrue(self.store.paper_intents("zone-paper")[0]["reduce_only"])

    def test_emergency_flatten_is_recorded_once(self):
        snapshot = make_snapshot()
        snapshot = DecisionOpportunitySnapshot(
            opportunity_id=snapshot.opportunity_id,
            snapshot_at=snapshot.snapshot_at,
            feature_as_of=snapshot.feature_as_of,
            symbol=snapshot.symbol,
            side=snapshot.side,
            state=snapshot.state,
            ref_price=snapshot.ref_price,
            sl_pct=snapshot.sl_pct,
            loss_budget=snapshot.loss_budget,
            size=snapshot.size,
            exposure=snapshot.exposure,
            hard_limits=snapshot.hard_limits,
            features={**dict(snapshot.features), "daily_loss": "10"},
        )
        mandate = self._mandate(daily_loss_action="EMERGENCY_FLATTEN")
        agent = PaperAgent(FakeProvider(make_proposal(snapshot)), self.store)
        first = agent.run(snapshot, mandate, now=NOW)
        second = agent.run(snapshot, mandate, now=NOW)
        self.assertIsNone(first.intent)
        self.assertIn("DAILY_LOSS_LIMIT", first.risk_check.reason_codes)
        flatten = [event for event in self.store.agent_events("zone-paper") if event["event"] == "EMERGENCY_FLATTEN_RECORDED"]
        self.assertEqual(len(flatten), 1)
        self.assertIsNone(second.intent)


if __name__ == "__main__":
    unittest.main()
