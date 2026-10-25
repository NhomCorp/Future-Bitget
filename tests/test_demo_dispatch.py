"""Offline tests for Demo-only paper dispatch. Fake poster; no live POST."""
from __future__ import annotations

import unittest
from decimal import Decimal

from trader.bitget_readonly import LiveModeDisabled, ReadOnlyCredentials
from trading.demo_dispatch import (
    DemoDispatchError,
    dispatch_intent,
    dispatch_intents,
    intent_to_cancel_body,
    intent_to_place_body,
    intent_to_tpsl_body,
    kill_symbol,
    make_demo_poster,
    normalize_whitelist,
    observation_from_query,
    tpsl_client_oid,
)
from trading.order_intent import PaperOrderIntent


WHITELIST = ("BTCUSDT",)


def make_intent(**overrides) -> PaperOrderIntent:
    values = dict(
        client_oid="ai-test-oid-0001",
        zone_id="zone-dispatch",
        decision_id="decision-1",
        risk_check_id="risk-1",
        mandate_id="mandate-1",
        mandate_version=1,
        symbol="BTCUSDT",
        side="long",
        quantity=Decimal("0.001"),
        price=Decimal("100"),
        stop_loss="95",
        take_profit=None,
    )
    values.update(overrides)
    return PaperOrderIntent(**values)


class DemoDispatchTests(unittest.TestCase):
    def test_requires_demo_confirm(self):
        result = dispatch_intent(
            make_intent(),
            allowed_symbols=WHITELIST,
            environ={"BITGET_ENV": "demo"},
        )
        self.assertEqual(result.result, "BLOCKED")
        self.assertFalse(result.posted)
        self.assertEqual(result.reason_code, "DEMO_CONFIRM_REQUIRED")

    def test_confirm_stays_dry_run_by_default(self):
        result = dispatch_intent(
            make_intent(),
            confirm_demo=True,
            allowed_symbols=WHITELIST,
            environ={"BITGET_ENV": "demo"},
        )
        self.assertEqual(result.result, "DRY_RUN")
        self.assertTrue(result.dry_run)
        self.assertFalse(result.posted)

    def test_live_flag_is_refused(self):
        with self.assertRaises(LiveModeDisabled):
            dispatch_intent(
                make_intent(),
                confirm_demo=True,
                allowed_symbols=WHITELIST,
                environ={"BITGET_ENV": "demo", "GROK_TRADER_ALLOW_LIVE": "1"},
            )

    def test_empty_whitelist_blocks_even_with_confirm(self):
        calls = []

        def poster(intent):
            calls.append(intent.client_oid)
            return {"dispatch": "FOUND"}

        result = dispatch_intent(
            make_intent(),
            confirm_demo=True,
            dry_run=False,
            poster=poster,
            allowed_symbols=(),
            environ={"BITGET_ENV": "demo"},
        )
        self.assertEqual(result.reason_code, "WHITELIST_EMPTY")
        self.assertFalse(result.posted)
        self.assertEqual(calls, [])

    def test_symbol_outside_whitelist_is_not_posted(self):
        calls = []

        def poster(intent):
            calls.append(intent.symbol)
            return {"dispatch": "FOUND"}

        result = dispatch_intent(
            make_intent(symbol="ETHUSDT"),
            confirm_demo=True,
            dry_run=False,
            poster=poster,
            allowed_symbols=WHITELIST,
            environ={"BITGET_ENV": "demo"},
        )
        self.assertEqual(result.reason_code, "SYMBOL_NOT_IN_WHITELIST")
        self.assertFalse(result.posted)
        self.assertEqual(calls, [])

    def test_poster_runs_only_when_not_dry_run(self):
        calls = []

        def poster(intent):
            calls.append(intent.client_oid)
            return {"dispatch": "FOUND"}

        result = dispatch_intent(
            make_intent(),
            confirm_demo=True,
            dry_run=False,
            poster=poster,
            allowed_symbols=WHITELIST,
            environ={"BITGET_ENV": "demo"},
        )
        self.assertEqual(calls, ["ai-test-oid-0001"])
        self.assertTrue(result.posted)
        self.assertEqual(result.dispatch, "FOUND")

    def test_dispatch_intents_keeps_whitelist_and_skips_outsiders(self):
        calls = []

        def poster(intent):
            calls.append(intent.symbol)
            return {"dispatch": "FOUND"}

        results = dispatch_intents(
            (make_intent(), make_intent(client_oid="ai-eth", symbol="ETHUSDT")),
            allowed_symbols=WHITELIST,
            confirm_demo=True,
            dry_run=False,
            poster=poster,
            environ={"BITGET_ENV": "demo"},
        )
        self.assertEqual([item.reason_code for item in results], [None, "SYMBOL_NOT_IN_WHITELIST"])
        self.assertEqual(calls, ["BTCUSDT"])
        self.assertTrue(results[0].posted)
        self.assertFalse(results[1].posted)

    def test_missing_poster_fails_closed(self):
        with self.assertRaises(DemoDispatchError):
            dispatch_intent(
                make_intent(),
                confirm_demo=True,
                dry_run=False,
                allowed_symbols=WHITELIST,
                environ={"BITGET_ENV": "demo"},
            )

    def test_place_body_uses_isolated_and_client_oid(self):
        body = intent_to_place_body(make_intent())
        self.assertEqual(body["marginMode"], "isolated")
        self.assertEqual(body["clientOid"], "ai-test-oid-0001")
        self.assertEqual(body["tradeSide"], "open")
        self.assertNotIn("reduceOnly", body)

    def test_hedge_close_long_is_buy_trade_side_close(self):
        body = intent_to_place_body(
            make_intent(reduce_only=True, order_role="reduce", order_type="market"),
            pos_mode="hedge_mode",
        )
        self.assertEqual(body["side"], "buy")
        self.assertEqual(body["tradeSide"], "close")
        self.assertNotIn("reduceOnly", body)
        self.assertEqual(body["force"], "ioc")

    def test_cancel_and_tpsl_bodies(self):
        intent = make_intent(stop_loss="95")
        cancel = intent_to_cancel_body(make_intent(order_role="cancel"))
        self.assertEqual(cancel["clientOid"], "ai-test-oid-0001")
        tpsl = intent_to_tpsl_body(intent)
        self.assertEqual(tpsl["planType"], "pos_loss")
        self.assertEqual(tpsl["triggerType"], "mark_price")
        self.assertEqual(tpsl["holdSide"], "long")
        self.assertEqual(tpsl["clientOid"], tpsl_client_oid(intent.client_oid))

    def test_cancel_posts_when_opted_in(self):
        calls = []

        def poster(intent):
            calls.append(intent.order_role)
            return {"dispatch": "FOUND"}

        result = dispatch_intent(
            make_intent(order_role="cancel"),
            confirm_demo=True,
            dry_run=False,
            poster=poster,
            allowed_symbols=WHITELIST,
            environ={"BITGET_ENV": "demo"},
        )
        self.assertEqual(calls, ["cancel"])
        self.assertTrue(result.posted)
        self.assertEqual(result.dispatch, "FOUND")

    def test_adjust_sl_stays_dry_run(self):
        calls = []
        result = dispatch_intent(
            make_intent(order_role="adjust_sl"),
            confirm_demo=True,
            dry_run=False,
            poster=lambda intent: calls.append(intent.order_role) or {"dispatch": "FOUND"},
            allowed_symbols=WHITELIST,
            environ={"BITGET_ENV": "demo"},
        )
        self.assertEqual(result.reason_code, "DRY_RUN")
        self.assertEqual(calls, [])

    def test_tpsl_follows_open_found(self):
        tpsl_calls = []

        result = dispatch_intent(
            make_intent(stop_loss="95"),
            confirm_demo=True,
            dry_run=False,
            poster=lambda _intent: {"dispatch": "FOUND"},
            tpsl_poster=lambda intent: tpsl_calls.append(intent.client_oid) or {"dispatch": "FOUND", "tpsl_client_oid": "ai-sl"},
            allowed_symbols=WHITELIST,
            environ={"BITGET_ENV": "demo"},
        )
        self.assertEqual(tpsl_calls, ["ai-test-oid-0001"])
        self.assertEqual(result.tpsl_dispatch, "FOUND")
        self.assertEqual(result.tpsl_client_oid, "ai-sl")

    def test_observation_from_query_canceled_is_absent(self):
        intent = make_intent()
        canceled = observation_from_query(
            intent,
            {"dispatch": "FOUND", "timeout": False, "data": {"status": "canceled", "accBaseVolume": "0"}},
        )
        self.assertFalse(canceled.found)
        timeout = observation_from_query(intent, {"dispatch": "UNKNOWN", "timeout": True})
        self.assertTrue(timeout.timeout)

    def test_kill_dry_run_does_not_post(self):
        calls = []
        result = kill_symbol(
            "BTCUSDT",
            allowed_symbols=WHITELIST,
            confirm_demo=True,
            dry_run=True,
            poster=lambda intent: calls.append(intent.order_role) or {"dispatch": "FOUND"},
            pending=[{"symbol": "BTCUSDT", "clientOid": "oid-1"}],
            positions=[{"symbol": "BTCUSDT", "holdSide": "long", "total": "0.001"}],
            environ={"BITGET_ENV": "demo"},
        )
        self.assertTrue(result.dry_run)
        self.assertEqual(result.cancelled, 1)
        self.assertEqual(result.closed, 1)
        self.assertEqual(calls, [])

    def test_kill_posts_cancel_then_close(self):
        calls = []

        class Adapter:
            def pending_orders(self):
                return []

            def positions(self):
                return []

        result = kill_symbol(
            "BTCUSDT",
            allowed_symbols=WHITELIST,
            confirm_demo=True,
            dry_run=False,
            poster=lambda intent: calls.append(intent.order_role) or {"dispatch": "FOUND"},
            adapter=Adapter(),
            pending=[{"symbol": "BTCUSDT", "clientOid": "oid-1"}],
            positions=[{"symbol": "BTCUSDT", "holdSide": "long", "total": "0.001"}],
            environ={"BITGET_ENV": "demo"},
        )
        self.assertEqual(calls, ["cancel", "reduce"])
        self.assertTrue(result.posted)
        self.assertTrue(result.leftover_clear)

    def test_kill_empty_whitelist_blocks(self):
        result = kill_symbol(
            "BTCUSDT",
            allowed_symbols=(),
            confirm_demo=True,
            dry_run=False,
            poster=lambda _intent: {"dispatch": "FOUND"},
            environ={"BITGET_ENV": "demo"},
        )
        self.assertEqual(result.reason_code, "WHITELIST_EMPTY")
        self.assertFalse(result.posted)

    def test_make_demo_poster_signs_paptrading_and_classifies(self):
        captured = {}

        def transport(method, path, headers, body, timeout):
            captured["method"] = method
            captured["path"] = path
            captured["headers"] = dict(headers)
            captured["body"] = body
            return {"code": "00000", "data": {"orderId": "1", "clientOid": "ai-test-oid-0001"}}

        poster = make_demo_poster(
            environ={"BITGET_ENV": "demo"},
            credentials=ReadOnlyCredentials("keykeykeykey", "secret", "pass"),
            transport=transport,
            clock=lambda: 0,
        )
        payload = poster(make_intent())
        self.assertEqual(payload["dispatch"], "FOUND")
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["path"], "/api/v2/mix/order/place-order")
        self.assertEqual(captured["headers"]["paptrading"], "1")
        self.assertIn("ACCESS-SIGN", captured["headers"])
        self.assertNotIn("secret", json_blob(captured))

    def test_normalize_whitelist_dedupes(self):
        self.assertEqual(normalize_whitelist(("btcusdt", "BTCUSDT", " ETHUSDT ")), ("BTCUSDT", "ETHUSDT"))
        self.assertEqual(normalize_whitelist(None), ())


def json_blob(value) -> str:
    import json

    return json.dumps(value)


if __name__ == "__main__":
    unittest.main()
