from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from unittest.mock import patch

from ai_proposal.schema import DecisionOpportunitySnapshot, HardLimits, ProposalDraft
from executor.p1_adapter import P1IntegrationStore
from trader.bitget_readonly import (
    LiveModeDisabled,
    MissingReadOnlyCredentials,
    ReadOnlyBitgetAdapter,
    ReadOnlyCredentials,
)
from trader.equity_cli import run as equity_cli_run
from trader.zone_store import ZoneStore
from trading.equity_snapshot import capture_equity_snapshot, merge_into_snapshot, parse_account_equity
from trading.equity_store import EquityStore
from trading.mandate import TradingMandate
from trading.paper_agent import PaperAgent
from trading.risk_engine import evaluate_decision


NOW = "2026-10-21T10:00:00Z"
YESTERDAY = "2026-10-20T23:00:00Z"
ACCOUNT_PATH = "/api/v2/mix/account/accounts?productType=USDT-FUTURES"


class FakeTransport:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, method, path, headers, body, timeout):
        self.calls.append((method, path, dict(headers), body))
        return self.responses[path]


class FakeProvider:
    def __init__(self, proposal):
        self.proposal = proposal

    def propose(self, snapshot):
        return self.proposal


def account_ok(equity="1000", margin_coin="USDT"):
    return {
        ACCOUNT_PATH: {"code": "00000", "data": [{"marginCoin": margin_coin, "accountEquity": equity}]},
    }


def make_adapter(responses):
    transport = FakeTransport(responses)
    adapter = ReadOnlyBitgetAdapter(
        credentials=ReadOnlyCredentials("public-key", "secret", "passphrase"),
        transport=transport,
        clock=lambda: 1700000000,
    )
    return adapter, transport


def make_snapshot(**features):
    return DecisionOpportunitySnapshot(
        opportunity_id="opp-equity-1",
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
            allowed_symbols=("BTCUSDT", "ETHUSDT"),
            allowed_sides=("long", "short"),
            allowed_states=("READY",),
            max_size=Decimal("2"),
            max_exposure=Decimal("200"),
        ),
        features={"trend": "up", "consecutive_losses": "0", **features},
    )


def make_proposal(snapshot, action="OPEN", **metadata):
    return ProposalDraft(
        proposal_id="decision-equity-1",
        opportunity_id=snapshot.opportunity_id,
        decision_timestamp=NOW,
        feature_as_of=snapshot.feature_as_of,
        model_version="fake-1",
        policy_version="policy-1",
        action=action,
        rationale="equity test",
        symbol=snapshot.symbol,
        side=snapshot.side,
        state=snapshot.state,
        ref_price=snapshot.ref_price,
        sl_pct=snapshot.sl_pct,
        loss_budget=snapshot.loss_budget,
        size=snapshot.size,
        exposure=snapshot.exposure,
        metadata={"stop_loss": "95", "leverage": "2", **metadata},
    )


def make_mandate(**overrides):
    values = dict(
        mandate_id="mandate-equity-1",
        version=1,
        zone_id="zone-equity",
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


class ParseTests(unittest.TestCase):
    def test_prefers_usdt_account_equity(self):
        payload = [
            {"marginCoin": "BTC", "accountEquity": "1"},
            {"marginCoin": "USDT", "accountEquity": "500.25"},
        ]
        self.assertEqual(parse_account_equity(payload), Decimal("500.25"))

    def test_missing_or_invalid_equity_is_none(self):
        self.assertIsNone(parse_account_equity([]))
        self.assertIsNone(parse_account_equity([{"marginCoin": "USDT"}]))
        self.assertIsNone(parse_account_equity([{"accountEquity": "0"}]))
        self.assertIsNone(parse_account_equity([{"accountEquity": "-1"}]))
        self.assertIsNone(parse_account_equity("not-a-payload"))


class CaptureTests(unittest.TestCase):
    def test_live_disabled_and_missing_credentials_are_incomplete(self):
        with EquityStore(":memory:") as store:
            class LiveAdapter:
                def account(self):
                    raise LiveModeDisabled("read-only adapter is Demo-only; live mode is disabled")

            live = capture_equity_snapshot(
                LiveAdapter(),
                store,
                max_age_seconds=60,
                now=NOW,
                drawdown_unit="usdt",
                drawdown_reference="equity_peak",
            )
            self.assertFalse(live.complete)
            self.assertIn("EQUITY_LIVE_DISABLED", live.reason_codes)

            missing = ReadOnlyBitgetAdapter(credentials=None, environ={})
            with self.assertRaises(MissingReadOnlyCredentials):
                missing.account()
            record = capture_equity_snapshot(
                missing,
                store,
                max_age_seconds=60,
                now=NOW,
                drawdown_unit="usdt",
                drawdown_reference="equity_peak",
            )
            self.assertFalse(record.complete)
            self.assertIn("EQUITY_CREDENTIALS_MISSING", record.reason_codes)

    def test_parse_failure_does_not_append(self):
        adapter, _transport = make_adapter({ACCOUNT_PATH: {"code": "00000", "data": [{"marginCoin": "USDT"}]}})
        with EquityStore(":memory:") as store:
            record = capture_equity_snapshot(
                adapter,
                store,
                max_age_seconds=60,
                now=NOW,
                drawdown_unit="usdt",
                drawdown_reference="equity_peak",
            )
            self.assertFalse(record.complete)
            self.assertIn("EQUITY_PARSE_FAILED", record.reason_codes)
            self.assertIsNone(store.max_equity())

    def test_today_only_has_no_day_start(self):
        adapter, transport = make_adapter(account_ok("1000"))
        with EquityStore(":memory:") as store:
            record = capture_equity_snapshot(
                adapter,
                store,
                max_age_seconds=60,
                now=NOW,
                drawdown_unit="usdt",
                drawdown_reference="equity_peak",
            )
            self.assertEqual(record.current_equity, Decimal("1000"))
            self.assertIsNone(record.day_start_equity)
            self.assertIsNone(record.daily_loss)
            self.assertIn("DAY_START_MISSING", record.reason_codes)
            self.assertFalse(record.complete)
            self.assertNotIn("day_start_equity", record.features_dict())
            self.assertEqual(transport.calls[0][0], "GET")
            self.assertEqual(transport.calls[0][2]["paptrading"], "1")

    def test_bootstrap_uses_first_row_of_utc_day(self):
        adapter, _transport = make_adapter(account_ok("1000"))
        with EquityStore(":memory:") as store:
            record = capture_equity_snapshot(
                adapter,
                store,
                max_age_seconds=60,
                now=NOW,
                drawdown_unit="usdt",
                drawdown_reference="equity_peak",
                allow_day_start_bootstrap=True,
            )
            self.assertTrue(record.complete)
            self.assertEqual(record.day_start_equity, Decimal("1000"))
            self.assertEqual(record.daily_loss, Decimal("0"))
            self.assertIn("DAY_START_BOOTSTRAP", record.reason_codes)
            self.assertNotIn("DAY_START_MISSING", record.reason_codes)

    def test_yesterday_snapshot_becomes_day_start(self):
        adapter, _transport = make_adapter(account_ok("990"))
        with EquityStore(":memory:") as store:
            store.append(YESTERDAY, Decimal("1000"))
            record = capture_equity_snapshot(
                adapter,
                store,
                max_age_seconds=60,
                now=NOW,
                drawdown_unit="usdt",
                drawdown_reference="equity_peak",
            )
            self.assertTrue(record.complete)
            self.assertEqual(record.day_start_equity, Decimal("1000"))
            self.assertEqual(record.daily_loss, Decimal("10"))
            self.assertEqual(record.drawdown, Decimal("10"))
            self.assertEqual(record.daily_loss_at, "2026-10-21T10:00:00.000Z")

    def test_drawdown_references_and_percent(self):
        adapter, _transport = make_adapter(account_ok("80"))
        with EquityStore(":memory:") as store:
            store.append(YESTERDAY, Decimal("100"), tags=("policy_start",))
            peak = capture_equity_snapshot(
                adapter,
                store,
                max_age_seconds=60,
                now=NOW,
                drawdown_unit="pct",
                drawdown_reference="equity_peak",
            )
            self.assertEqual(peak.drawdown, Decimal("20"))
            day = capture_equity_snapshot(
                adapter,
                store,
                max_age_seconds=60,
                now=NOW,
                drawdown_unit="usdt",
                drawdown_reference="day_start",
            )
            self.assertEqual(day.drawdown, Decimal("20"))
            policy = capture_equity_snapshot(
                adapter,
                store,
                max_age_seconds=60,
                now=NOW,
                drawdown_unit="usdt",
                drawdown_reference="policy_start",
            )
            self.assertEqual(policy.drawdown, Decimal("20"))

    def test_policy_start_missing_is_incomplete(self):
        adapter, _transport = make_adapter(account_ok("100"))
        with EquityStore(":memory:") as store:
            store.append(YESTERDAY, Decimal("100"))
            record = capture_equity_snapshot(
                adapter,
                store,
                max_age_seconds=60,
                now=NOW,
                drawdown_unit="usdt",
                drawdown_reference="policy_start",
            )
            self.assertFalse(record.complete)
            self.assertIn("DRAWDOWN_REFERENCE_MISSING", record.reason_codes)
            self.assertNotIn("drawdown", record.features_dict())

    def test_stale_when_older_than_max_age(self):
        adapter, _transport = make_adapter(account_ok("1000"))
        with EquityStore(":memory:") as store:
            store.append(YESTERDAY, Decimal("1000"))
            record = capture_equity_snapshot(
                adapter,
                store,
                max_age_seconds=60,
                now=NOW,
                drawdown_unit="usdt",
                drawdown_reference="equity_peak",
                captured_at="2026-10-21T09:58:00Z",
            )
            self.assertTrue(record.stale)
            self.assertFalse(record.complete)
            self.assertIn("EQUITY_STALE", record.reason_codes)

    def test_merge_keeps_consecutive_losses(self):
        adapter, _transport = make_adapter(account_ok("1000"))
        with EquityStore(":memory:") as store:
            store.append(YESTERDAY, Decimal("1000"))
            record = capture_equity_snapshot(
                adapter,
                store,
                max_age_seconds=60,
                now=NOW,
                drawdown_unit="usdt",
                drawdown_reference="equity_peak",
            )
            snapshot = merge_into_snapshot(make_snapshot(consecutive_losses="4", daily_loss="99"), record)
            self.assertEqual(snapshot.features["consecutive_losses"], "4")
            self.assertEqual(snapshot.features["daily_loss"], "0")
            self.assertEqual(snapshot.features["trend"], "up")


class RiskWireTests(unittest.TestCase):
    def test_missing_day_start_pauses_open_but_allows_close(self):
        adapter, _transport = make_adapter(account_ok("1000"))
        with EquityStore(":memory:") as store:
            record = capture_equity_snapshot(
                adapter,
                store,
                max_age_seconds=60,
                now=NOW,
                drawdown_unit="usdt",
                drawdown_reference="equity_peak",
            )
            snapshot = merge_into_snapshot(make_snapshot(), record)
            opened = evaluate_decision(snapshot, make_proposal(snapshot), make_mandate(), now=NOW, stale=record.stale)
            self.assertEqual(opened.risk_check.result, "PAUSED")
            self.assertIn("RISK_CONTEXT_INCOMPLETE", opened.risk_check.reason_codes)
            closed = evaluate_decision(
                snapshot,
                make_proposal(snapshot, action="CLOSE", order_type="limit", order_role="reduce", reduce_only=True),
                make_mandate(),
                now=NOW,
                stale=record.stale,
            )
            self.assertEqual(closed.risk_check.result, "APPROVED")
            self.assertNotIn("RISK_CONTEXT_INCOMPLETE", closed.risk_check.reason_codes)

    def test_stale_equity_pauses_open(self):
        adapter, _transport = make_adapter(account_ok("1000"))
        with EquityStore(":memory:") as store:
            store.append(YESTERDAY, Decimal("1000"))
            record = capture_equity_snapshot(
                adapter,
                store,
                max_age_seconds=30,
                now=NOW,
                drawdown_unit="usdt",
                drawdown_reference="equity_peak",
                captured_at="2026-10-21T09:58:00Z",
            )
            snapshot = merge_into_snapshot(make_snapshot(), record)
            result = evaluate_decision(snapshot, make_proposal(snapshot), make_mandate(), now=NOW, stale=record.stale)
            self.assertEqual(result.risk_check.result, "PAUSED")
            self.assertIn("SNAPSHOT_STALE", result.risk_check.reason_codes)

    def test_daily_loss_limit_from_bitget_features(self):
        adapter, _transport = make_adapter(account_ok("990"))
        with EquityStore(":memory:") as store:
            store.append(YESTERDAY, Decimal("1000"))
            record = capture_equity_snapshot(
                adapter,
                store,
                max_age_seconds=60,
                now=NOW,
                drawdown_unit="usdt",
                drawdown_reference="equity_peak",
            )
            snapshot = merge_into_snapshot(make_snapshot(), record)
            result = evaluate_decision(snapshot, make_proposal(snapshot), make_mandate(), now=NOW, stale=record.stale)
            self.assertIn("DAILY_LOSS_LIMIT", result.risk_check.reason_codes)

    def test_paper_agent_uses_merged_features_without_http(self):
        adapter, transport = make_adapter(account_ok("1000"))
        with tempfile.TemporaryDirectory() as tmp:
            zone_path = os.path.join(tmp, "zones.sqlite3")
            zones = ZoneStore(zone_path)
            zones.create_zone(
                {"symbol": "BTCUSDT", "side": "long", "ref_price": "100", "zone_loss_limit_usdt": "20", "sl_pct": "5"},
                zone_id="zone-equity",
                state="ACTIVE",
            )
            store = P1IntegrationStore(zones)
            with EquityStore(":memory:") as equity:
                record = capture_equity_snapshot(
                    adapter,
                    equity,
                    max_age_seconds=60,
                    now=NOW,
                    drawdown_unit="usdt",
                    drawdown_reference="equity_peak",
                )
                snapshot = merge_into_snapshot(make_snapshot(), record)
                result = PaperAgent(FakeProvider(make_proposal(snapshot)), store).run(
                    snapshot,
                    make_mandate(),
                    now=NOW,
                    stale=record.stale,
                )
            self.assertIsNone(result.intent)
            self.assertIn("RISK_CONTEXT_INCOMPLETE", result.risk_check.reason_codes)
            self.assertEqual([call[0] for call in transport.calls], ["GET"])
            store.close()
            zones.close()


class CliTests(unittest.TestCase):
    def test_cli_json_is_redacted_and_get_only(self):
        adapter, transport = make_adapter(account_ok("1000"))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "equity.sqlite3")
            with EquityStore(path) as store, redirect_stdout(io.StringIO()) as stdout:
                code = equity_cli_run(
                    ["snapshot", "--max-age-seconds", "60", "--json", "--now", NOW],
                    adapter=adapter,
                    store=store,
                )
            payload = stdout.getvalue()
            self.assertEqual(code, 0)
            self.assertIn('"complete": false', payload)
            self.assertNotIn("secret", payload)
            self.assertNotIn("public-key", payload)
            self.assertNotIn("passphrase", payload)
            self.assertNotIn("accountEquity", payload)
            self.assertEqual(transport.calls[0][0], "GET")
            self.assertEqual(transport.calls[0][2]["paptrading"], "1")
            self.assertIsNone(transport.calls[0][3])

    def test_cli_live_env_fails_closed(self):
        with patch.dict(os.environ, {"BITGET_ENV": "live"}, clear=False):
            with self.assertRaises(LiveModeDisabled):
                ReadOnlyBitgetAdapter(environ={"BITGET_ENV": "live"})
            with redirect_stdout(io.StringIO()) as stdout:
                code = equity_cli_run(
                    ["snapshot", "--max-age-seconds", "60", "--json", "--store", ":memory:"],
                    adapter=None,
                )
            self.assertEqual(code, 2)
            self.assertIn("LiveModeDisabled", stdout.getvalue())
            self.assertNotIn("secret", stdout.getvalue())

    def test_cli_requires_max_age(self):
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            with patch("sys.stderr", new=io.StringIO()):
                equity_cli_run(["snapshot", "--json"])


if __name__ == "__main__":
    unittest.main()
