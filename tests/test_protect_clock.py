"""Offline tests for the local protection clock. No exchange POST."""
from __future__ import annotations

import inspect
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from decimal import Decimal

from ai_proposal.schema import DecisionOpportunitySnapshot, HardLimits, ProposalDraft
from executor.p1_adapter import P1IntegrationStore
from executor.zone_executor import IntentRole, ZoneExecutor
from trader.protect_clock_cli import run as protect_cli_run
from trader.zone_store import ZoneStore
from trading.mandate import TradingMandate
from trading.paper_agent import PaperAgent
from trading.paper_scan import REASON_INACTIVE, REASON_NOT_DUE, REASON_UNKNOWN, tick as scan_tick
from trading.protect_clock import (
    EMERGENCY_FLATTEN_EVENT,
    PROTECT_TRIGGERED_EVENT,
    REASON_RAN,
    REASON_STALE,
    REASON_TRIGGERED,
    REASON_UNKNOWN as PROTECT_UNKNOWN,
    ProtectObservation,
    run_loop,
    tick,
)
from trading.reconcile import ReconcileObservation


NOW = "2026-10-21T10:00:00Z"
LATER = "2026-10-21T10:14:00Z"
EXPIRED = "2026-10-21T12:00:00Z"


def make_snapshot() -> DecisionOpportunitySnapshot:
    return DecisionOpportunitySnapshot(
        opportunity_id="opp-protect-1",
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
        features={
            "trend": "up",
            "daily_loss": "0",
            "day_start_equity": "1000",
            "daily_loss_at": NOW,
            "drawdown": "0",
            "drawdown_unit": "usdt",
            "consecutive_losses": "0",
        },
    )


def make_proposal(snapshot: DecisionOpportunitySnapshot, **overrides) -> ProposalDraft:
    fields = dict(
        proposal_id="decision-protect-1",
        opportunity_id=snapshot.opportunity_id,
        decision_timestamp=NOW,
        feature_as_of=snapshot.feature_as_of,
        model_version="fake-1",
        policy_version="policy-1",
        action="OPEN",
        rationale="protect clock test candidate",
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
    def __init__(self, proposal=None):
        self.proposal = proposal
        self.calls = 0

    def propose(self, snapshot):
        self.calls += 1
        return self.proposal


class ProtectClockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "zones.sqlite3")
        self.zones = ZoneStore(self.path)
        self.zones.create_zone(
            {"symbol": "BTCUSDT", "side": "long", "ref_price": "100", "zone_loss_limit_usdt": "20", "sl_pct": "5"},
            zone_id="zone-protect",
            state="ACTIVE",
        )
        self.store = P1IntegrationStore(self.zones)
        self.snapshot = make_snapshot()
        self.mandate = self._mandate()
        self.store.save_mandate(self.mandate.to_dict())

    def _mandate(self, **overrides) -> TradingMandate:
        values = dict(
            mandate_id="mandate-protect",
            version=1,
            zone_id="zone-protect",
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

    def test_mark_hit_creates_one_emergency_and_second_tick_reuses_oid(self):
        observation = ProtectObservation(
            mark_price=Decimal("95"),
            position_quantity=Decimal("1"),
            position_side="long",
        )
        first = tick(self.store, "zone-protect", observation, now=NOW)
        self.assertEqual(first.reason_code, REASON_TRIGGERED)
        self.assertTrue(first.triggered)
        self.assertFalse(first.to_dict()["exchange_post"])
        self.assertIsNotNone(first.emergency_close_client_oid)
        emergencies = [
            item
            for item in ZoneExecutor.restore(self.store, "zone-protect").intents("zone-protect")
            if item.role is IntentRole.EMERGENCY_CLOSE
        ]
        self.assertEqual(len(emergencies), 1)

        second = tick(self.store, "zone-protect", observation, now=LATER)
        self.assertEqual(second.emergency_close_client_oid, first.emergency_close_client_oid)
        restored = ZoneExecutor.restore(self.store, "zone-protect")
        self.assertEqual(
            len([item for item in restored.intents("zone-protect") if item.role is IntentRole.EMERGENCY_CLOSE]),
            1,
        )
        triggered = [event for event in self.store.agent_events("zone-protect") if event.get("event") == PROTECT_TRIGGERED_EVENT]
        self.assertEqual(len(triggered), 2)

    def test_fill_reconciles_without_inventing_qty(self):
        provider = FakeProvider(make_proposal(self.snapshot))
        opened = PaperAgent(provider, self.store).run(self.snapshot, self.mandate, now=NOW)
        self.assertIsNotNone(opened.intent)
        observation = ProtectObservation(
            mark_price=Decimal("100"),
            fills=(
                ReconcileObservation(
                    client_oid=opened.intent.client_oid,
                    found=True,
                    filled_quantity=Decimal("0.4"),
                ),
            ),
        )
        result = tick(self.store, "zone-protect", observation, now=NOW)
        self.assertEqual(result.reason_code, REASON_RAN)
        self.assertEqual(len(result.reconcile_results), 1)
        self.assertEqual(result.reconcile_results[0].result, "partial")
        stored = self.store.get_paper_intent(opened.intent.client_oid)
        self.assertEqual(stored["state"], "paper_partial")
        self.assertEqual(Decimal(stored["filled_quantity"]), Decimal("0.4"))
        self.assertEqual(Decimal(stored["remaining_quantity"]), Decimal("0.6"))

    def test_timeout_unknown_blocks_later_scan(self):
        provider = FakeProvider(make_proposal(self.snapshot))
        agent = PaperAgent(provider, self.store)
        opened = agent.run(self.snapshot, self.mandate, now=NOW)
        protect = tick(
            self.store,
            "zone-protect",
            ProtectObservation(
                mark_price=Decimal("100"),
                fills=(ReconcileObservation(client_oid=opened.intent.client_oid, timeout=True),),
            ),
            now=NOW,
        )
        self.assertEqual(protect.reason_code, PROTECT_UNKNOWN)
        self.assertTrue(protect.unknown)
        self.assertFalse(protect.triggered)
        skipped = scan_tick(agent, self.snapshot, self.mandate, now=LATER)
        self.assertEqual(skipped.reason_code, REASON_UNKNOWN)
        self.assertEqual(provider.calls, 1)

    def test_scan_not_due_still_runs_protect(self):
        provider = FakeProvider(make_proposal(self.snapshot))
        agent = PaperAgent(provider, self.store)
        first = scan_tick(agent, self.snapshot, self.mandate, now=NOW)
        self.assertTrue(first.ran)
        skipped = scan_tick(agent, self.snapshot, self.mandate, now=LATER)
        self.assertEqual(skipped.reason_code, REASON_NOT_DUE)
        protect = tick(
            self.store,
            "zone-protect",
            ProtectObservation(mark_price=Decimal("94"), position_quantity=Decimal("1"), position_side="long"),
            now=LATER,
        )
        self.assertEqual(protect.reason_code, REASON_TRIGGERED)
        self.assertEqual(provider.calls, 1)

    def test_expired_scan_does_not_flatten_protect_still_kills(self):
        provider = FakeProvider(make_proposal(self.snapshot))
        agent = PaperAgent(provider, self.store)
        expired = scan_tick(agent, self.snapshot, self.mandate, now=EXPIRED)
        self.assertEqual(expired.reason_code, REASON_INACTIVE)
        self.assertFalse(any(event.get("event") == EMERGENCY_FLATTEN_EVENT for event in self.store.agent_events("zone-protect")))
        protect = tick(
            self.store,
            "zone-protect",
            ProtectObservation(
                mark_price=Decimal("100"),
                kill_switch=True,
                position_quantity=Decimal("1"),
                position_side="long",
            ),
            now=EXPIRED,
        )
        self.assertEqual(protect.reason_code, REASON_TRIGGERED)
        self.assertTrue(protect.kill_switch)
        flatten = [event for event in self.store.agent_events("zone-protect") if event.get("event") == EMERGENCY_FLATTEN_EVENT]
        self.assertEqual(len(flatten), 1)
        again = tick(
            self.store,
            "zone-protect",
            ProtectObservation(
                mark_price=Decimal("100"),
                kill_switch=True,
                position_quantity=Decimal("1"),
                position_side="long",
            ),
            now=EXPIRED,
        )
        self.assertEqual(again.emergency_close_client_oid, protect.emergency_close_client_oid)
        self.assertEqual(
            len([event for event in self.store.agent_events("zone-protect") if event.get("event") == EMERGENCY_FLATTEN_EVENT]),
            1,
        )

    def test_stale_does_not_fire_sl_on_invented_mark(self):
        result = tick(
            self.store,
            "zone-protect",
            ProtectObservation(mark_price=Decimal("90"), stale=True, position_quantity=Decimal("1")),
            now=NOW,
        )
        self.assertEqual(result.reason_code, REASON_STALE)
        self.assertFalse(result.triggered)
        self.assertIsNone(result.emergency_close_client_oid)

    def test_loop_reuses_emergency_oid(self):
        sleeps: list[float] = []
        results = run_loop(
            self.store,
            "zone-protect",
            ProtectObservation(mark_price=Decimal("95"), position_quantity=Decimal("1"), position_side="long"),
            now_fn=lambda: NOW,
            sleep=sleeps.append,
            poll_seconds=2,
            max_ticks=2,
        )
        self.assertEqual([item.reason_code for item in results], [REASON_TRIGGERED, REASON_TRIGGERED])
        self.assertEqual(results[0].emergency_close_client_oid, results[1].emergency_close_client_oid)
        self.assertEqual(sleeps, [2])

    def test_protect_does_not_call_demo_dispatch(self):
        import trader.protect_clock_cli as protect_cli
        import trader.paper_scan_cli as scan_cli
        import trading.protect_clock as protect_clock

        for source in (inspect.getsource(protect_clock), inspect.getsource(protect_cli)):
            self.assertNotIn("demo_dispatch", source)
            self.assertNotIn("dispatch_intent", source)
        self.assertNotIn("from .paper_agent", inspect.getsource(protect_clock))
        self.assertNotIn("from trading.paper_agent", inspect.getsource(protect_clock))
        self.assertIn("make_demo_poster", inspect.getsource(scan_cli))

    def test_cli_tick_json_and_live_guard(self):
        obs_path = os.path.join(self.tmp.name, "obs.json")
        with open(obs_path, "w", encoding="utf-8") as handle:
            json.dump({"mark_price": "100", "position_quantity": "1", "position_side": "long"}, handle)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = protect_cli_run(
                ["tick", "--zone-id", "zone-protect", "--observation", obs_path, "--now", NOW, "--json"],
                store=self.store,
            )
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertTrue(payload["ran"])
        self.assertFalse(payload["exchange_post"])
        self.assertEqual(payload["reason_code"], REASON_RAN)

        live = io.StringIO()
        with redirect_stdout(live):
            live_code = protect_cli_run(
                ["tick", "--zone-id", "zone-protect", "--observation", obs_path, "--json"],
                environ={"GROK_TRADER_ALLOW_LIVE": "1"},
            )
        self.assertEqual(live_code, 2)
        self.assertIn("LiveModeDisabled", live.getvalue())


if __name__ == "__main__":
    unittest.main()
