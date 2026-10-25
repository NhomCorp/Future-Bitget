"""Offline tests for the local paper scan clock. Fake provider only; no exchange."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from decimal import Decimal

from ai_proposal.schema import DecisionOpportunitySnapshot, HardLimits, ProposalDraft
from executor.p1_adapter import P1IntegrationStore
from trader.paper_scan_cli import run as scan_cli_run
from trader.zone_store import ZoneStore
from trading.mandate import TradingMandate
from trading.paper_agent import PaperAgent
from trading.paper_scan import (
    DISPATCH_EVENT,
    REASON_INACTIVE,
    REASON_INTERVAL,
    REASON_NOT_DUE,
    REASON_RAN,
    REASON_STALE,
    REASON_UNKNOWN,
    REASON_ZONE,
    SCAN_RAN_EVENT,
    ScanDispatchOptions,
    tick,
    run_loop,
)
from trading.reconcile import PaperReconcile


NOW = "2026-10-21T10:00:00Z"
LATER = "2026-10-21T10:14:00Z"
DUE = "2026-10-21T10:15:00Z"
EXPIRED = "2026-10-21T12:00:00Z"


def make_snapshot() -> DecisionOpportunitySnapshot:
    return DecisionOpportunitySnapshot(
        opportunity_id="opp-scan-1",
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
        proposal_id="decision-scan-1",
        opportunity_id=snapshot.opportunity_id,
        decision_timestamp=NOW,
        feature_as_of=snapshot.feature_as_of,
        model_version="fake-1",
        policy_version="policy-1",
        action="OPEN",
        rationale="paper scan test candidate",
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


class PaperScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "zones.sqlite3")
        self.zones = ZoneStore(self.path)
        self.zones.create_zone(
            {"symbol": "BTCUSDT", "side": "long", "ref_price": "100", "zone_loss_limit_usdt": "20", "sl_pct": "5"},
            zone_id="zone-scan",
            state="ACTIVE",
        )
        self.store = P1IntegrationStore(self.zones)
        self.snapshot = make_snapshot()
        self.mandate = self._mandate()
        self.store.save_mandate(self.mandate.to_dict())

    def _mandate(self, **overrides) -> TradingMandate:
        values = dict(
            mandate_id="mandate-scan",
            version=1,
            zone_id="zone-scan",
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

    def test_calls_ai_only_when_interval_is_due(self):
        provider = FakeProvider(make_proposal(self.snapshot))
        agent = PaperAgent(provider, self.store)
        first = tick(agent, self.snapshot, self.mandate, now=NOW)
        self.assertTrue(first.due)
        self.assertTrue(first.ran)
        self.assertEqual(first.reason_code, REASON_RAN)
        self.assertEqual(provider.calls, 1)
        self.assertIsNotNone(first.intent)
        self.assertEqual(first.intent.order_role, "entry")

        skipped = tick(agent, self.snapshot, self.mandate, now=LATER)
        self.assertFalse(skipped.due)
        self.assertFalse(skipped.ran)
        self.assertEqual(skipped.reason_code, REASON_NOT_DUE)
        self.assertEqual(provider.calls, 1)
        self.assertIsNone(skipped.intent)
        self.assertEqual(skipped.proposal.proposal.action, "NO_TRADE")
        self.assertEqual(len(self.store.paper_intents("zone-scan")), 1)

        again = tick(agent, self.snapshot, self.mandate, now=DUE)
        self.assertTrue(again.due)
        self.assertTrue(again.ran)
        self.assertEqual(provider.calls, 2)
        ran = [event for event in self.store.agent_events("zone-scan") if event.get("event") == SCAN_RAN_EVENT]
        self.assertEqual(len(ran), 2)

    def test_stale_unknown_and_stopping_are_no_trade_without_ai(self):
        provider = FakeProvider(make_proposal(self.snapshot))
        agent = PaperAgent(provider, self.store)
        stale = tick(agent, self.snapshot, self.mandate, now=NOW, stale=True)
        self.assertEqual(stale.reason_code, REASON_STALE)
        self.assertFalse(stale.ran)
        self.assertEqual(provider.calls, 0)
        self.assertIsNone(stale.intent)
        self.assertEqual(stale.proposal.proposal.action, "NO_TRADE")

        first = tick(agent, self.snapshot, self.mandate, now=NOW)
        self.assertEqual(provider.calls, 1)
        PaperReconcile(self.store).record_timeout(first.intent.client_oid)
        unknown = tick(agent, self.snapshot, self.mandate, now=DUE)
        self.assertEqual(unknown.reason_code, REASON_UNKNOWN)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(unknown.proposal.proposal.action, "NO_TRADE")
        self.assertEqual(len(self.store.paper_intents("zone-scan")), 1)

        self.zones.transition_zone("zone-scan", "STOPPING", reason="scan-test")
        stopping = tick(agent, self.snapshot, self.mandate, now=DUE)
        self.assertEqual(stopping.reason_code, REASON_ZONE)
        self.assertEqual(provider.calls, 1)
        self.assertIsNone(stopping.intent)

    def test_expired_mandate_does_not_flatten(self):
        provider = FakeProvider(make_proposal(self.snapshot, action="CLOSE", metadata={"leverage": "2", "order_type": "limit", "order_role": "reduce", "reduce_only": True}))
        agent = PaperAgent(provider, self.store)
        result = tick(agent, self.snapshot, self.mandate, now=EXPIRED)
        self.assertEqual(result.reason_code, REASON_INACTIVE)
        self.assertEqual(provider.calls, 0)
        self.assertIsNone(result.intent)
        self.assertEqual(self.store.paper_intents("zone-scan"), [])
        self.assertFalse(any(event.get("event") == "EMERGENCY_FLATTEN_RECORDED" for event in self.store.agent_events("zone-scan")))

    def test_missing_interval_skips_ai(self):
        mandate = self._mandate(position_review_interval=None)
        provider = FakeProvider(make_proposal(self.snapshot))
        result = tick(PaperAgent(provider, self.store), self.snapshot, mandate, now=NOW)
        self.assertEqual(result.reason_code, REASON_INTERVAL)
        self.assertEqual(provider.calls, 0)
        self.assertEqual(result.proposal.proposal.action, "NO_TRADE")

    def test_loop_calls_ai_once_while_clock_is_frozen(self):
        provider = FakeProvider(make_proposal(self.snapshot))
        agent = PaperAgent(provider, self.store)
        sleeps: list[float] = []
        results = run_loop(
            agent,
            self.snapshot,
            self.mandate,
            now_fn=lambda: NOW,
            sleep=sleeps.append,
            poll_seconds=5,
            max_ticks=2,
        )
        self.assertEqual([item.reason_code for item in results], [REASON_RAN, REASON_NOT_DUE])
        self.assertEqual(provider.calls, 1)
        self.assertEqual(sleeps, [5])

    def test_cli_tick_json_and_live_guard(self):
        snap_path = os.path.join(self.tmp.name, "snapshot.json")
        with open(snap_path, "w", encoding="utf-8") as handle:
            json.dump(self.snapshot.to_dict(), handle)
        provider = FakeProvider(make_proposal(self.snapshot))
        agent = PaperAgent(provider, self.store)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = scan_cli_run(
                ["tick", "--zone-id", "zone-scan", "--mandate-id", "mandate-scan", "--snapshot", snap_path, "--now", NOW, "--json"],
                agent=agent,
                store=self.store,
                snapshot=self.snapshot,
                mandate=self.mandate,
            )
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertTrue(payload["due"])
        self.assertTrue(payload["ran"])
        self.assertFalse(payload["exchange_post"])
        self.assertEqual(payload["dispatch_results"], [])
        self.assertEqual(payload["action"], "OPEN")
        self.assertEqual(provider.calls, 1)

        live = io.StringIO()
        with redirect_stdout(live):
            live_code = scan_cli_run(
                ["tick", "--zone-id", "zone-scan", "--mandate-id", "mandate-scan", "--snapshot", snap_path, "--json"],
                environ={"GROK_TRADER_ALLOW_LIVE": "1"},
            )
        self.assertEqual(live_code, 2)
        self.assertIn("LiveModeDisabled", live.getvalue())
        self.assertEqual(provider.calls, 1)

    def test_whitelist_dispatch_posts_only_when_confirmed(self):
        provider = FakeProvider(make_proposal(self.snapshot))
        agent = PaperAgent(provider, self.store)
        calls = []

        def poster(intent):
            calls.append(intent.symbol)
            return {"dispatch": "FOUND"}

        skipped = tick(
            agent,
            self.snapshot,
            self.mandate,
            now=NOW,
            dispatch=ScanDispatchOptions(confirm_demo=True, dry_run=True, poster=poster, environ={"BITGET_ENV": "demo"}),
        )
        self.assertTrue(skipped.ran)
        self.assertFalse(skipped.to_dict()["exchange_post"])
        self.assertEqual(skipped.dispatch_results[0].reason_code, "DRY_RUN")
        self.assertEqual(calls, [])

        posted = tick(
            agent,
            self.snapshot,
            self.mandate,
            now=DUE,
            dispatch=ScanDispatchOptions(
                confirm_demo=True,
                dry_run=False,
                poster=poster,
                environ={"BITGET_ENV": "demo"},
            ),
        )
        self.assertTrue(posted.to_dict()["exchange_post"])
        self.assertEqual(posted.dispatch_results[0].dispatch, "FOUND")
        self.assertEqual(calls, ["BTCUSDT"])
        events = [event for event in self.store.agent_events("zone-scan") if event.get("event") == DISPATCH_EVENT]
        self.assertEqual(len(events), 2)
        self.assertTrue(events[1].get("exchange_post"))

        again = tick(
            agent,
            self.snapshot,
            self.mandate,
            now="2026-10-21T10:30:00Z",
            dispatch=ScanDispatchOptions(
                confirm_demo=True,
                dry_run=False,
                poster=poster,
                environ={"BITGET_ENV": "demo"},
            ),
        )
        self.assertEqual(calls, ["BTCUSDT"])
        self.assertEqual(again.dispatch_results, ())

    def test_found_dispatch_queries_exchange_for_reconcile(self):
        provider = FakeProvider(make_proposal(self.snapshot))
        agent = PaperAgent(provider, self.store)
        queried = []

        result = tick(
            agent,
            self.snapshot,
            self.mandate,
            now=NOW,
            dispatch=ScanDispatchOptions(
                confirm_demo=True,
                dry_run=False,
                poster=lambda _intent: {"dispatch": "FOUND"},
                query=lambda intent: queried.append(intent.client_oid) or {
                    "dispatch": "FOUND",
                    "timeout": False,
                    "data": {"status": "live", "accBaseVolume": "0"},
                },
                environ={"BITGET_ENV": "demo"},
            ),
        )
        self.assertEqual(queried, [result.intent.client_oid])
        self.assertEqual(result.dispatch_results[0].reconcile, "confirmed_open")
        self.assertEqual(self.store.get_paper_intent(result.intent.client_oid)["state"], "paper_open")

    def test_unknown_dispatch_blocks_next_scan(self):
        provider = FakeProvider(make_proposal(self.snapshot))
        agent = PaperAgent(provider, self.store)

        def poster(_intent):
            return {"dispatch": "UNKNOWN"}

        first = tick(
            agent,
            self.snapshot,
            self.mandate,
            now=NOW,
            dispatch=ScanDispatchOptions(
                confirm_demo=True,
                dry_run=False,
                poster=poster,
                environ={"BITGET_ENV": "demo"},
            ),
        )
        self.assertEqual(first.dispatch_results[0].dispatch, "UNKNOWN")
        self.assertEqual(self.store.get_paper_intent(first.intent.client_oid)["state"], "paper_unknown")

        skipped = tick(
            agent,
            self.snapshot,
            self.mandate,
            now=DUE,
            dispatch=ScanDispatchOptions(
                confirm_demo=True,
                dry_run=False,
                poster=poster,
                environ={"BITGET_ENV": "demo"},
            ),
        )
        self.assertEqual(skipped.reason_code, REASON_UNKNOWN)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(skipped.dispatch_results, ())

    def test_cli_place_orders_requires_confirm_and_can_post_whitelist(self):
        snap_path = os.path.join(self.tmp.name, "snapshot.json")
        with open(snap_path, "w", encoding="utf-8") as handle:
            json.dump(self.snapshot.to_dict(), handle)
        blocked = io.StringIO()
        with redirect_stdout(blocked):
            code = scan_cli_run(
                [
                    "tick",
                    "--zone-id",
                    "zone-scan",
                    "--mandate-id",
                    "mandate-scan",
                    "--snapshot",
                    snap_path,
                    "--place-orders",
                    "--json",
                ],
            )
        self.assertEqual(code, 2)
        self.assertIn("PostDisabled", blocked.getvalue())

        provider = FakeProvider(make_proposal(self.snapshot))
        agent = PaperAgent(provider, self.store)
        calls = []

        def poster(intent):
            calls.append(intent.client_oid)
            return {"dispatch": "FOUND"}

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            posted_code = scan_cli_run(
                [
                    "tick",
                    "--zone-id",
                    "zone-scan",
                    "--mandate-id",
                    "mandate-scan",
                    "--snapshot",
                    snap_path,
                    "--now",
                    NOW,
                    "--place-orders",
                    "--i-confirm-demo",
                    "--json",
                ],
                agent=agent,
                store=self.store,
                snapshot=self.snapshot,
                mandate=self.mandate,
                poster=poster,
                environ={"BITGET_ENV": "demo"},
            )
        self.assertEqual(posted_code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertTrue(payload["exchange_post"])
        self.assertEqual(payload["dispatch_results"][0]["dispatch"], "FOUND")
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
