"""Offline tests for the supervised Demo cycle. No live POST."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from pathlib import Path

from executor.p1_adapter import P1IntegrationStore
from trader.bitget_readonly import BitgetAdapterError
from trader.demo_scan_cli import _ensure_autonomous_zone, run as demo_scan_run
from trader.zone_store import ZoneStore
from trading.demo_cycle import (
    ProtectDispatchOptions,
    observation_from_snapshot,
    run_allowlist_cycle,
    run_cycle,
    run_loop,
)
from trading.equity_store import EquityStore
from trading.frontend_mandate import FRONTEND_MANDATE_ID, ScanLimits, build_scan_snapshot, policy_to_mandate
from trading.paper_agent import PaperAgent
from trading.paper_scan import REASON_NOT_DUE, REASON_RAN, REASON_STALE, LocalNoTradeProvider
from trading.protect_clock import REASON_STALE as PROTECT_STALE
from trading.protect_clock import REASON_TRIGGERED
from tests.test_frontend_mandate import make_limits, make_policy


NOW = "2026-10-23T02:00:00Z"


class FakeAdapter:
    def __init__(self, payload):
        self.payload = payload
        self.snapshot_calls = 0

    def snapshot(self, *, symbol=None):
        self.snapshot_calls += 1
        return self.payload

    def public_ticker(self, symbol):
        self.ticker_calls = getattr(self, "ticker_calls", 0) + 1
        return self.payload.get("ticker")

    def account(self):
        return self.payload.get("account")

    def positions(self):
        return self.payload.get("positions") or []

    def pending_orders(self):
        return self.payload.get("pending_orders") or []


class BoomAdapter(FakeAdapter):
    def snapshot(self, *, symbol=None):
        self.snapshot_calls += 1
        raise BitgetAdapterError("snapshot failed")


def make_raw(**overrides):
    payload = {
        "account": [{"marginCoin": "USDT", "accountEquity": "1000"}],
        "positions": [
            {
                "symbol": "BTCUSDT",
                "holdSide": "long",
                "total": "0.001",
                "markPrice": "100",
                "unrealizedPL": "0",
            }
        ],
        "pending_orders": [],
        "fills": [],
        "ticker": {"lastPr": "100", "markPrice": "100"},
    }
    payload.update(overrides)
    return payload


class DemoCycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.zones = ZoneStore(str(Path(self.tmp.name) / "zones.sqlite3"))
        self.store = P1IntegrationStore(self.zones)
        self.equity = EquityStore(":memory:")
        self.limits = ScanLimits.from_mapping(make_limits())
        self.mandate = policy_to_mandate(make_policy(), self.limits, now=NOW)
        self.store.save_mandate(self.mandate.to_dict())
        self.zones.create_zone(
            {
                "symbol": "BTCUSDT",
                "side": "long",
                "ref_price": "100",
                "zone_loss_limit_usdt": "20",
                "sl_pct": "2",
                "opened_by": "ai",
            },
            zone_id=self.mandate.zone_id,
            state="ACTIVE",
        )
        self.agent = PaperAgent(LocalNoTradeProvider(), self.store)

    def tearDown(self):
        self.store.close()
        self.zones.close()
        self.equity.close()
        self.tmp.cleanup()

    def _cycle(self, adapter, **kwargs):
        return run_cycle(
            adapter=adapter,
            store=self.store,
            equity_store=self.equity,
            agent=self.agent,
            mandate=self.mandate,
            limits=self.limits,
            now=NOW,
            **kwargs,
        )

    def test_first_utc_day_bootstraps_day_start(self):
        result = self._cycle(FakeAdapter(make_raw()))
        self.assertTrue(result.equity.complete)
        self.assertEqual(result.equity.day_start_equity, Decimal("1000"))
        self.assertIn("DAY_START_BOOTSTRAP", result.equity.reason_codes)
        self.assertFalse(result.snapshot_stale)

    def test_fresh_get_each_loop_and_protect_when_scan_not_due(self):
        adapter = FakeAdapter(make_raw())
        results = run_loop(
            now_fn=lambda: NOW,
            sleep=lambda _: None,
            poll_seconds=8,
            max_ticks=2,
            adapter=adapter,
            store=self.store,
            equity_store=self.equity,
            agent=self.agent,
            mandate=self.mandate,
            limits=self.limits,
        )
        self.assertEqual(adapter.snapshot_calls, 2)
        self.assertEqual(results[0].scan.reason_code, REASON_RAN)
        self.assertEqual(results[1].scan.reason_code, REASON_NOT_DUE)
        self.assertTrue(results[1].protect.ran)

    def test_protect_trigger_dry_run_does_not_post(self):
        calls = []
        adapter = FakeAdapter(make_raw(ticker={"lastPr": "94", "markPrice": "94"}))
        result = self._cycle(
            adapter,
            protect_dispatch=ProtectDispatchOptions(
                confirm_demo=True,
                dry_run=True,
                poster=lambda intent: calls.append(intent) or {"dispatch": "FOUND"},
                adapter=adapter,
            ),
        )
        self.assertEqual(result.protect.reason_code, REASON_TRIGGERED)
        self.assertTrue(result.protect.triggered)
        self.assertFalse(result.protect.to_dict()["exchange_post"])
        self.assertFalse(result.protect_kill.posted)
        self.assertEqual(calls, [])
        self.assertFalse(result.to_dict()["exchange_post"])

    def test_protect_trigger_posts_once_when_leftover_clear(self):
        calls = []
        payload = make_raw(ticker={"lastPr": "94", "markPrice": "94"})
        adapter = FakeAdapter(payload)

        def poster(intent):
            calls.append(intent)
            payload["positions"] = []
            payload["pending_orders"] = []
            return {"dispatch": "FOUND"}

        opts = ProtectDispatchOptions(
            confirm_demo=True,
            dry_run=False,
            poster=poster,
            adapter=adapter,
        )
        first = self._cycle(adapter, protect_dispatch=opts)
        self.assertTrue(first.protect.triggered)
        self.assertTrue(first.protect_kill.posted)
        self.assertTrue(first.to_dict()["exchange_post"])
        posted = len(calls)
        self.assertGreaterEqual(posted, 1)
        second = self._cycle(adapter, protect_dispatch=opts)
        self.assertEqual(len(calls), posted)

    def test_stale_get_does_not_fire_invented_sl(self):
        calls = []
        adapter = BoomAdapter(make_raw(ticker={"lastPr": "94", "markPrice": "94"}))
        result = self._cycle(
            adapter,
            protect_dispatch=ProtectDispatchOptions(
                confirm_demo=True,
                dry_run=False,
                poster=lambda intent: calls.append(intent) or {"dispatch": "FOUND"},
                adapter=adapter,
            ),
        )
        self.assertTrue(result.snapshot_stale)
        self.assertEqual(result.protect.reason_code, PROTECT_STALE)
        self.assertFalse(result.protect.triggered)
        self.assertEqual(result.scan.reason_code, REASON_STALE)
        self.assertEqual(calls, [])

    def test_allowlist_scans_each_approved_pair_once_equity(self):
        adapter = FakeAdapter(
            make_raw(
                positions=[
                    {
                        "symbol": "BTCUSDT",
                        "holdSide": "long",
                        "total": "0.001",
                        "markPrice": "100",
                        "unrealizedPL": "0",
                    }
                ]
            )
        )
        policy = make_policy(symbol_allowlist=["BTCUSDT", "ETHUSDT"])

        def build_job(job):
            built = policy_to_mandate(
                policy,
                job,
                now=NOW,
                mandate_id=f"{FRONTEND_MANDATE_ID}-{job.symbol}-{job.side}",
            )
            _ensure_autonomous_zone(self.store, built, build_scan_snapshot(built, job, now=NOW))
            return built

        payload = run_allowlist_cycle(
            adapter=adapter,
            store=self.store,
            equity_store=self.equity,
            agent=self.agent,
            policy=policy,
            limits={
                "scope": "allowlist",
                "sl_pct": "2",
                "loss_budget": "20",
                "max_order_risk": "5",
                "max_size": "0.01",
            },
            mandate_builder=build_job,
            now=NOW,
        )
        self.assertEqual(payload["scanned"], 3)
        symbols = {row["symbol"] for row in payload["pairs"]}
        self.assertEqual(symbols, {"BTCUSDT", "ETHUSDT"})
        self.assertEqual({row["side"] for row in payload["pairs"] if row["symbol"] == "BTCUSDT"}, {"long"})
        self.assertEqual({row["side"] for row in payload["pairs"] if row["symbol"] == "ETHUSDT"}, {"long", "short"})
        self.assertFalse(payload["exchange_post"])

    def test_observation_ignores_unknown_fill_oids(self):
        raw = make_raw(
            fills=[{"symbol": "BTCUSDT", "clientOid": "unknown-oid", "baseVolume": "0.001"}]
        )
        observation = observation_from_snapshot(
            raw,
            symbol="BTCUSDT",
            side="long",
            store=self.store,
        )
        self.assertEqual(observation.fills, ())
        self.assertEqual(observation.position_quantity, Decimal("0.001"))


class DemoCycleCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.policy = self.root / "policy.json"
        self.limits = self.root / "limits.json"
        self.policy.write_text(json.dumps(make_policy()), encoding="utf-8")
        self.limits.write_text(json.dumps(make_limits()), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, extra, **kwargs):
        argv = [
            "cycle",
            "--policy",
            str(self.policy),
            "--limits",
            str(self.limits),
            "--store",
            str(self.root / "zones.sqlite3"),
            "--equity-store",
            str(self.root / "equity.sqlite3"),
            "--now",
            NOW,
            "--json",
            *extra,
        ]
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = demo_scan_run(
                argv,
                environ=kwargs.get("environ") or {"BITGET_ENV": "demo"},
                adapter=kwargs.get("adapter") or FakeAdapter(make_raw()),
                poster=kwargs.get("poster"),
            )
        return code, json.loads(buf.getvalue() or "{}")

    def test_cycle_json_bootstraps_equity_and_does_not_post_by_default(self):
        calls = []
        code, payload = self._run([], poster=lambda intent: calls.append(intent) or {"dispatch": "FOUND"})
        self.assertEqual(code, 0)
        self.assertEqual(calls, [])
        self.assertFalse(payload["exchange_post"])
        self.assertTrue(payload["equity"]["complete"])
        self.assertIn("DAY_START_BOOTSTRAP", payload["equity"]["reason_codes"])
        self.assertIn("protect", payload)

    def test_cycle_live_flag_is_refused(self):
        code, payload = self._run(
            ["--place-orders", "--i-confirm-demo"],
            environ={"BITGET_ENV": "demo", "GROK_TRADER_ALLOW_LIVE": "1"},
        )
        self.assertEqual(code, 2)
        self.assertEqual(payload["error"], "LiveModeDisabled")

    def test_allowlist_scope_walks_approved_pairs(self):
        self.policy.write_text(
            json.dumps(make_policy(symbol_allowlist=["BTCUSDT", "ETHUSDT"])),
            encoding="utf-8",
        )
        self.limits.write_text(
            json.dumps(
                {
                    "scope": "allowlist",
                    "sl_pct": "2",
                    "loss_budget": "20",
                    "max_order_risk": "5",
                    "max_size": "0.01",
                }
            ),
            encoding="utf-8",
        )
        code, payload = self._run([])
        self.assertEqual(code, 0)
        self.assertEqual(payload["scanned"], 3)
        self.assertEqual({row["symbol"] for row in payload["pairs"]}, {"BTCUSDT", "ETHUSDT"})
        self.assertFalse(payload["exchange_post"])

    def test_scan_dispatch_still_dry_run_without_both_flags(self):
        calls = []
        code, payload = self._run(
            ["--i-confirm-demo"],
            poster=lambda intent: calls.append(intent) or {"dispatch": "FOUND"},
        )
        self.assertEqual(code, 0)
        self.assertEqual(calls, [])
        self.assertFalse(payload["exchange_post"])


if __name__ == "__main__":
    unittest.main()
