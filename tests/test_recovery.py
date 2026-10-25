"""Local restart recovery for paper intents, budget and dry-run executor."""
from __future__ import annotations

import os
import tempfile
import unittest
from decimal import Decimal

from ai_proposal.schema import DecisionOpportunitySnapshot, HardLimits, ProposalDraft
from executor.p1_adapter import P1IntegrationStore
from executor.zone_executor import IntentRole, IntentState, OrderEventType, OrderObservation, RiskTrigger, ZoneExecutor, ZoneOrderSpec
from trader.zone_store import ZoneStore
from trading.mandate import TradingMandate
from trading.mandate_store import MandateStore, consume_loss_budget, recover_session
from trading.paper_agent import PaperAgent
from trading.reconcile import PaperReconcile, ReconcileObservation


NOW = "2026-10-21T10:00:00Z"


def make_snapshot() -> DecisionOpportunitySnapshot:
    return DecisionOpportunitySnapshot(
        opportunity_id="opp-recover-1",
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
        proposal_id="decision-recover-1",
        opportunity_id=snapshot.opportunity_id,
        decision_timestamp=NOW,
        feature_as_of=snapshot.feature_as_of,
        model_version="fake-1",
        policy_version="policy-1",
        action="OPEN",
        rationale="recovery test",
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
    def __init__(self, proposal):
        self.proposal = proposal
        self.calls = 0

    def propose(self, snapshot):
        self.calls += 1
        return self.proposal


class PaperRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "zones.sqlite3")
        self.zones = ZoneStore(self.path)
        self.zones.create_zone(
            {"symbol": "BTCUSDT", "side": "long", "ref_price": "100", "zone_loss_limit_usdt": "20", "sl_pct": "5"},
            zone_id="zone-recover",
            state="ACTIVE",
        )
        self.store = P1IntegrationStore(self.zones)
        self.snapshot = make_snapshot()
        self.mandate = self._mandate()

    def _mandate(self, **overrides) -> TradingMandate:
        values = dict(
            mandate_id="mandate-recover",
            version=1,
            zone_id="zone-recover",
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

    def _reopen(self):
        self.store.close()
        self.zones.close()
        self.zones = ZoneStore(self.path)
        self.store = P1IntegrationStore(self.zones)

    def tearDown(self):
        self.store.close()
        self.zones.close()
        self.tmp.cleanup()

    def test_restart_reloads_mandate_and_pending_intent(self):
        first = PaperAgent(FakeProvider(make_proposal(self.snapshot)), self.store).run(self.snapshot, self.mandate, now=NOW)
        self.assertEqual(first.intent.state, "paper_pending")
        client_oid = first.intent.client_oid
        self._reopen()
        recovered = recover_session(self.store, "zone-recover", "mandate-recover")
        self.assertEqual(recovered.mandate.version, 1)
        self.assertEqual(recovered.mandate.loss_budget, Decimal("20"))
        self.assertEqual(len(recovered.paper_intents), 1)
        self.assertEqual(recovered.paper_intents[0]["client_oid"], client_oid)
        self.assertEqual(recovered.paper_intents[0]["state"], "paper_pending")
        self.assertEqual(MandateStore(self.store).versions("mandate-recover"), (1,))

    def test_timeout_unknown_blocks_new_proposal_after_restart(self):
        first = PaperAgent(FakeProvider(make_proposal(self.snapshot)), self.store).run(self.snapshot, self.mandate, now=NOW)
        timed_out = PaperReconcile(self.store).record_timeout(first.intent.client_oid)
        self.assertEqual(timed_out.result, "unknown")
        self.assertTrue(timed_out.requires_reconcile)
        self._reopen()
        provider = FakeProvider(make_proposal(self.snapshot, proposal_id="decision-recover-2"))
        second = PaperAgent(provider, self.store).run(self.snapshot, self.mandate, now=NOW)
        self.assertIsNone(second.intent)
        self.assertEqual(provider.calls, 0)
        self.assertEqual(len(self.store.paper_intents("zone-recover")), 1)
        self.assertEqual(self.store.paper_intents("zone-recover")[0]["client_oid"], first.intent.client_oid)
        self.assertTrue(
            any(event.get("reason_code") == "RECONCILE_REQUIRED" for event in self.store.agent_events("zone-recover"))
        )

    def test_partial_fill_updates_remaining_and_survives_restart(self):
        first = PaperAgent(FakeProvider(make_proposal(self.snapshot)), self.store).run(self.snapshot, self.mandate, now=NOW)
        partial = PaperReconcile(self.store).apply(
            ReconcileObservation(client_oid=first.intent.client_oid, found=True, filled_quantity="0.40")
        )
        self.assertEqual(partial.result, "partial")
        self.assertEqual(partial.remaining_quantity, Decimal("0.60"))
        self._reopen()
        recovered = recover_session(self.store, "zone-recover", "mandate-recover")
        self.assertEqual(recovered.paper_intents[0]["remaining_quantity"], "0.60")
        confirmed = PaperReconcile(self.store).apply(
            ReconcileObservation(client_oid=first.intent.client_oid, found=True, filled_quantity="1")
        )
        self.assertEqual(confirmed.result, "confirmed_open")
        self.assertEqual(confirmed.remaining_quantity, Decimal("0"))
        self.assertEqual(confirmed.state, "paper_filled")

    def test_confirmed_absent_does_not_create_second_intent(self):
        first = PaperAgent(FakeProvider(make_proposal(self.snapshot)), self.store).run(self.snapshot, self.mandate, now=NOW)
        absent = PaperReconcile(self.store).apply(ReconcileObservation(client_oid=first.intent.client_oid, found=False))
        self.assertEqual(absent.result, "confirmed_absent")
        second = PaperAgent(FakeProvider(make_proposal(self.snapshot)), self.store).run(self.snapshot, self.mandate, now=NOW)
        self.assertEqual(second.intent.client_oid, first.intent.client_oid)
        self.assertEqual(len(self.store.paper_intents("zone-recover")), 1)

    def test_loss_budget_is_not_regranted_after_restart(self):
        self.store.save_mandate(self.mandate.to_dict())
        remaining = consume_loss_budget(
            self.store,
            zone_id="zone-recover",
            mandate_id="mandate-recover",
            amount=Decimal("8"),
            reason="partial_close",
            original_loss_budget=self.mandate.loss_budget,
        )
        self.assertEqual(remaining, Decimal("12"))
        self._reopen()
        recovered = recover_session(self.store, "zone-recover", "mandate-recover")
        self.assertEqual(recovered.remaining_loss_budget, Decimal("12"))
        self.assertEqual(recovered.consumed_loss_budget, Decimal("8"))
        self.assertEqual(recovered.mandate.loss_budget, Decimal("20"))
        consume_loss_budget(
            self.store,
            zone_id="zone-recover",
            mandate_id="mandate-recover",
            amount=Decimal("12"),
            reason="episode_loss",
        )
        provider = FakeProvider(make_proposal(self.snapshot, proposal_id="decision-recover-exhausted"))
        exhausted = PaperAgent(provider, self.store).run(self.snapshot, self.mandate, now=NOW)
        self.assertIsNone(exhausted.intent)
        self.assertEqual(provider.calls, 0)
        self.assertTrue(
            any(event.get("reason_code") == "LOSS_BUDGET_EXHAUSTED" for event in self.store.agent_events("zone-recover"))
        )

    def test_open_intent_consumes_loss_budget(self):
        PaperAgent(FakeProvider(make_proposal(self.snapshot)), self.store).run(self.snapshot, self.mandate, now=NOW)
        recovered = recover_session(self.store, "zone-recover", "mandate-recover")
        self.assertEqual(recovered.consumed_loss_budget, Decimal("5"))
        self.assertEqual(recovered.remaining_loss_budget, Decimal("15"))

    def test_latest_mandate_is_used_for_risk(self):
        self.store.save_mandate(self.mandate.to_dict())
        newer = self._mandate(version=2, allowed_symbols=("ETHUSDT",))
        self.store.save_mandate(newer.to_dict())
        provider = FakeProvider(make_proposal(self.snapshot))
        result = PaperAgent(provider, self.store).run(self.snapshot, self.mandate, now=NOW)
        self.assertEqual(provider.calls, 1)
        self.assertIsNone(result.intent)
        self.assertEqual(result.risk_check.result, "REJECTED")
        self.assertIn("SYMBOL_NOT_ALLOWED", result.risk_check.reason_codes)
        self.assertEqual(result.risk_check.mandate_version, 2)


class ExecutorRecoveryTests(unittest.TestCase):
    def test_unknown_intent_and_emergency_close_survive_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "zones.sqlite3")
            with ZoneStore(path) as zones:
                zones.create_zone(
                    {"symbol": "BTCUSDT", "side": "long", "ref_price": "100", "zone_loss_limit_usdt": "10", "sl_pct": "5"},
                    zone_id="zone-exec",
                    state="ACTIVE",
                )
                with P1IntegrationStore(zones) as store:
                    executor = ZoneExecutor(store)
                    executor.create_zone(
                        "zone-exec",
                        [ZoneOrderSpec(IntentRole.ENTRY, 0, "1", "100", "buy")],
                        position_quantity="1",
                        position_side="long",
                    )
                    oid = executor.intents("zone-exec")[0].client_oid
                    executor.mark_submitted(oid)
                    executor.apply_observation(OrderObservation(oid, OrderEventType.TIMEOUT))
                    executor.apply_observation(OrderObservation(oid, OrderEventType.UNKNOWN))
                    self.assertEqual(executor.get_intent(oid).state, IntentState.UNKNOWN)
            with ZoneStore(path) as zones:
                with P1IntegrationStore(zones) as store:
                    restored = ZoneExecutor.restore(store, "zone-exec")
                    oid = restored.intents("zone-exec")[0].client_oid
                    self.assertEqual(restored.get_intent(oid).state, IntentState.UNKNOWN)
                    first = restored.on_risk_trigger("zone-exec", RiskTrigger.LOSS_BUDGET)
                    second = restored.on_risk_trigger("zone-exec", RiskTrigger.LOSS_BUDGET)
                    self.assertEqual(first.emergency_close_client_oid, second.emergency_close_client_oid)
                    self.assertEqual(
                        len([item for item in restored.intents("zone-exec") if item.role is IntentRole.EMERGENCY_CLOSE]),
                        1,
                    )


if __name__ == "__main__":
    unittest.main()
