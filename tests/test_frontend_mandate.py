"""Offline tests for frontend policy → mandate → Demo scan tick."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from pathlib import Path

from trader.demo_scan_cli import run as demo_scan_run
from trading.frontend_mandate import (
    FRONTEND_MANDATE_ID,
    FrontendMandateError,
    ScanLimits,
    allowlist_scan_jobs,
    build_scan_snapshot,
    policy_to_mandate,
    proposal_from_intent,
    scan_limits_from_policy,
    sides_for_symbol,
    use_allowlist_scope,
)


NOW = "2026-10-23T02:00:00Z"


def make_policy(**overrides):
    values = {
        "version": 3,
        "granted_capital": "1000",
        "capital_currency": "USDT",
        "ai_autonomy": "AUTONOMOUS_WITHIN_MANDATE",
        "daily_loss_limit_pct": "20",
        "daily_loss_action": "FREEZE_ENTRY",
        "max_consecutive_losses": 3,
        "loss_streak_cooldown": "24h",
        "loss_streak_scope": "subaccount",
        "allow_average_down": False,
        "drawdown_limit": "15",
        "drawdown_unit": "pct",
        "drawdown_reference": "equity_peak",
        "drawdown_scope": "subaccount",
        "daily_loss_scope": "subaccount",
        "max_leverage": "5",
        "symbol_allowlist": ["BTCUSDT"],
        "position_review_interval": 15,
    }
    values.update(overrides)
    return values


def make_limits(**overrides):
    values = {
        "symbol": "BTCUSDT",
        "side": "long",
        "ref_price": "100",
        "sl_pct": "2",
        "loss_budget": "20",
        "max_order_risk": "5",
        "max_size": "0.01",
    }
    values.update(overrides)
    return values


class FrontendMandateTests(unittest.TestCase):
    def test_empty_allowlist_is_not_tradable(self):
        with self.assertRaises(FrontendMandateError) as caught:
            policy_to_mandate(
                make_policy(symbol_allowlist=[]),
                ScanLimits.from_mapping(make_limits()),
                now=NOW,
            )
        self.assertIn("WHITELIST_EMPTY", str(caught.exception))

    def test_symbol_outside_allowlist_is_rejected(self):
        with self.assertRaises(FrontendMandateError) as caught:
            policy_to_mandate(
                make_policy(symbol_allowlist=["ETHUSDT"]),
                ScanLimits.from_mapping(make_limits()),
                now=NOW,
            )
        self.assertIn("SYMBOL_NOT_IN_WHITELIST", str(caught.exception))

    def test_managed_zone_cannot_open_demo_post_path(self):
        with self.assertRaises(FrontendMandateError) as caught:
            policy_to_mandate(
                make_policy(ai_autonomy="MANAGED_ZONE"),
                ScanLimits.from_mapping(make_limits()),
                now=NOW,
            )
        self.assertIn("AUTONOMOUS_WITHIN_MANDATE", str(caught.exception))

    def test_policy_risk_fields_fill_omitted_limits(self):
        limits = scan_limits_from_policy(
            make_policy(
                sl_pct="2",
                zone_loss_limit_usdt="20",
                max_order_risk_usdt="5",
                max_size="0.01",
            ),
            {"symbol": "BTCUSDT", "side": "long", "ref_price": "100"},
        )
        self.assertEqual(limits.sl_pct, Decimal("2"))
        self.assertEqual(limits.loss_budget, Decimal("20"))
        self.assertEqual(limits.max_order_risk, Decimal("5"))
        self.assertEqual(limits.max_size, Decimal("0.01"))

    def test_missing_policy_and_limits_risk_is_rejected(self):
        with self.assertRaises(FrontendMandateError):
            scan_limits_from_policy(
                make_policy(),
                {"symbol": "BTCUSDT", "side": "long", "ref_price": "100"},
            )

    def test_maps_user_limits_without_inventing_risk(self):
        mandate = policy_to_mandate(
            make_policy(),
            ScanLimits.from_mapping(make_limits()),
            now=NOW,
        )
        self.assertEqual(mandate.mandate_id, FRONTEND_MANDATE_ID)
        self.assertEqual(mandate.allowed_symbols, ("BTCUSDT",))
        self.assertEqual(mandate.max_exposure, Decimal("1000"))
        self.assertEqual(mandate.loss_budget, Decimal("20"))
        self.assertEqual(mandate.max_order_risk, Decimal("5"))
        self.assertEqual(mandate.max_size, Decimal("0.01"))
        self.assertEqual(mandate.zone_id, "local-BTCUSDT-long")
        self.assertTrue(mandate.valid_until > mandate.valid_from)

    def test_allowlist_jobs_use_open_side_or_both(self):
        self.assertTrue(use_allowlist_scope({"scope": "allowlist"}))
        self.assertTrue(use_allowlist_scope({"sl_pct": "2"}))
        self.assertFalse(use_allowlist_scope({"symbol": "BTCUSDT", "side": "long"}))
        self.assertEqual(sides_for_symbol("BTCUSDT", [{"symbol": "BTCUSDT", "holdSide": "long", "total": "1"}]), ("long",))
        jobs = allowlist_scan_jobs(
            make_policy(
                symbol_allowlist=["BTCUSDT", "ETHUSDT"],
                sl_pct="2",
                zone_loss_limit_usdt="20",
                max_order_risk_usdt="5",
                max_size="0.01",
            ),
            {"scope": "allowlist"},
            positions=[{"symbol": "BTCUSDT", "holdSide": "long", "total": "0.001"}],
            prices={"BTCUSDT": Decimal("100"), "ETHUSDT": Decimal("10")},
        )
        self.assertEqual([(job.symbol, job.side) for job in jobs], [("BTCUSDT", "long"), ("ETHUSDT", "long"), ("ETHUSDT", "short")])

    def test_intent_proposal_stays_inside_snapshot_symbol(self):
        mandate = policy_to_mandate(make_policy(), ScanLimits.from_mapping(make_limits()), now=NOW)
        snapshot = build_scan_snapshot(
            mandate,
            ScanLimits.from_mapping(make_limits(size="0.001")),
            now=NOW,
        )
        draft = proposal_from_intent(
            snapshot,
            {"size": "0.001", "price": "100", "side": "long", "leverage": "2"},
            policy_version="policy-3",
            now=NOW,
        )
        self.assertEqual(draft.action, "OPEN")
        self.assertEqual(draft.symbol, "BTCUSDT")
        self.assertEqual(draft.size, Decimal("0.001"))
        self.assertEqual(draft.metadata["stop_loss"], "98")


class DemoScanCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = str(self.root / "zones.sqlite3")
        self.policy = self.root / "policy.json"
        self.limits = self.root / "limits.json"
        self.proposal = self.root / "proposal.json"
        self.features = self.root / "features.json"
        self.agent = self.root / "agent.json"
        self.policy.write_text(json.dumps(make_policy()), encoding="utf-8")
        self.limits.write_text(json.dumps(make_limits()), encoding="utf-8")
        self.proposal.write_text(
            json.dumps({"size": "0.001", "price": "100", "side": "long", "leverage": "2"}),
            encoding="utf-8",
        )
        self.features.write_text(
            json.dumps(
                {
                    "daily_loss": "0",
                    "day_start_equity": "1000",
                    "daily_loss_at": NOW,
                    "drawdown": "0",
                    "drawdown_unit": "pct",
                    "consecutive_losses": "0",
                }
            ),
            encoding="utf-8",
        )
        self.agent.write_text(
            json.dumps(
                {
                    "provider": "gemini",
                    "model": "gemini-2.0-flash",
                    "api_key": "secret-ai-key",
                    "label": "main",
                    "request_timeout": 15,
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, extra, *, poster=None, environ=None, agent_transport=None):
        argv = [
            "tick",
            "--policy",
            str(self.policy),
            "--limits",
            str(self.limits),
            "--store",
            self.store,
            "--now",
            NOW,
            "--json",
            *extra,
        ]
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = demo_scan_run(
                argv,
                environ=environ or {"BITGET_ENV": "demo"},
                poster=poster,
                agent_transport=agent_transport,
            )
        return code, json.loads(buf.getvalue() or "{}")

    def test_empty_whitelist_cli_does_not_post(self):
        self.policy.write_text(json.dumps(make_policy(symbol_allowlist=[])), encoding="utf-8")
        calls = []
        code, payload = self._run(
            ["--proposal", str(self.proposal), "--place-orders", "--i-confirm-demo"],
            poster=lambda intent: calls.append(intent) or {"dispatch": "FOUND"},
        )
        self.assertEqual(code, 2)
        self.assertEqual(payload["error"], "FrontendMandateError")
        self.assertIn("WHITELIST_EMPTY", payload["message"])
        self.assertEqual(calls, [])

    def test_place_orders_requires_confirm(self):
        code, payload = self._run(["--place-orders"])
        self.assertEqual(code, 2)
        self.assertEqual(payload["error"], "PostDisabled")

    def test_live_flag_is_refused(self):
        code, payload = self._run(
            ["--place-orders", "--i-confirm-demo"],
            environ={"BITGET_ENV": "demo", "GROK_TRADER_ALLOW_LIVE": "1"},
        )
        self.assertEqual(code, 2)
        self.assertEqual(payload["error"], "LiveModeDisabled")

    def test_default_tick_is_no_trade_and_dry_run(self):
        code, payload = self._run([])
        self.assertEqual(code, 0)
        self.assertEqual(payload["action"], "NO_TRADE")
        self.assertFalse(payload["exchange_post"])
        self.assertEqual(payload["allowed_symbols"], ["BTCUSDT"])

    def test_confirmed_intent_posts_only_whitelist_symbol(self):
        calls = []

        def poster(intent):
            calls.append(intent.symbol)
            return {"dispatch": "FOUND"}

        code, payload = self._run(
            [
                "--proposal",
                str(self.proposal),
                "--features",
                str(self.features),
                "--place-orders",
                "--i-confirm-demo",
            ],
            poster=poster,
        )
        self.assertEqual(code, 0)
        self.assertTrue(payload["exchange_post"])
        self.assertEqual(calls, ["BTCUSDT"])
        self.assertEqual(payload["dispatch_results"][0]["dispatch"], "FOUND")

    def test_agent_open_posts_without_intent(self):
        calls = []

        def poster(intent):
            calls.append(intent.symbol)
            return {"dispatch": "FOUND"}

        def transport(method, url, headers, body, timeout):
            self.assertIn("x-goog-api-key", headers)
            self.assertEqual(headers["x-goog-api-key"], "secret-ai-key")
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "action": "OPEN",
                                            "quantity": "0.001",
                                            "order_type": "LIMIT",
                                            "rationale": "ai open small",
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ]
            }

        code, payload = self._run(
            [
                "--agent-config",
                str(self.agent),
                "--features",
                str(self.features),
                "--place-orders",
                "--i-confirm-demo",
            ],
            poster=poster,
            agent_transport=transport,
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["action"], "OPEN")
        self.assertTrue(payload["exchange_post"])
        self.assertEqual(calls, ["BTCUSDT"])
        self.assertTrue(payload["agent"]["called"])
        self.assertTrue(payload["agent"]["ok"])
        self.assertNotIn("secret-ai-key", json.dumps(payload))

    def test_agent_timeout_is_no_trade_without_post(self):
        calls = []

        def transport(method, url, headers, body, timeout):
            raise TimeoutError("slow")

        code, payload = self._run(
            [
                "--agent-config",
                str(self.agent),
                "--features",
                str(self.features),
                "--place-orders",
                "--i-confirm-demo",
            ],
            poster=lambda intent: calls.append(intent) or {"dispatch": "FOUND"},
            agent_transport=transport,
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["action"], "NO_TRADE")
        self.assertFalse(payload["exchange_post"])
        self.assertEqual(calls, [])
        self.assertTrue(payload["agent"]["called"])
        self.assertFalse(payload["agent"]["ok"])
        self.assertEqual(payload["agent"]["error"], "PROVIDER_TIMEOUT")

    def test_intent_wins_over_agent_config(self):
        def transport(method, url, headers, body, timeout):
            raise AssertionError("AI must not be called when intent is present")

        code, payload = self._run(
            [
                "--proposal",
                str(self.proposal),
                "--agent-config",
                str(self.agent),
                "--features",
                str(self.features),
            ],
            agent_transport=transport,
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["action"], "OPEN")
        self.assertFalse(payload["agent"]["called"])

    def test_outside_whitelist_never_reaches_poster(self):
        self.limits.write_text(json.dumps(make_limits(symbol="SOLUSDT")), encoding="utf-8")
        calls = []
        code, payload = self._run(
            ["--proposal", str(self.proposal), "--place-orders", "--i-confirm-demo"],
            poster=lambda intent: calls.append(intent) or {"dispatch": "FOUND"},
        )
        self.assertEqual(code, 2)
        self.assertIn("SYMBOL_NOT_IN_WHITELIST", payload["message"])
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
