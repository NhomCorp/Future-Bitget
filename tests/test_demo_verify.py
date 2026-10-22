from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from unittest.mock import patch

from trader.bitget_readonly import LiveModeDisabled, ReadOnlyCredentials
from trader.demo_verify import (
    DemoVerifyClient,
    classify_dispatch,
    redact_headers,
    redact_payload,
    round_price,
    round_size,
    rows,
    run_demo_verify,
    verify_client_oid,
)
from trader.demo_verify_cli import run as demo_verify_cli_run


NOW = "2026-10-22T06:00:00Z"
SYMBOL = "BTCUSDT"
ACCOUNTS = "/api/v2/mix/account/accounts?productType=USDT-FUTURES"
POSITIONS = "/api/v2/mix/position/all-position?productType=USDT-FUTURES&marginCoin=USDT"
PENDING = "/api/v2/mix/order/orders-pending?productType=USDT-FUTURES"
TICKER = "/api/v2/mix/market/ticker?productType=USDT-FUTURES&symbol=BTCUSDT"
CONTRACTS = "/api/v2/mix/market/contracts?productType=USDT-FUTURES&symbol=BTCUSDT"
ACCOUNT_SYMBOL = "/api/v2/mix/account/account?productType=USDT-FUTURES&symbol=BTCUSDT&marginCoin=USDT"
PLACE = "/api/v2/mix/order/place-order"
CANCEL = "/api/v2/mix/order/cancel-order"


class FakeTransport:
    def __init__(self, responses, post_handler=None):
        self.responses = responses
        self.post_handler = post_handler
        self.calls = []

    def __call__(self, method, path, headers, body, timeout):
        self.calls.append((method, path, dict(headers), body))
        if method == "POST" and self.post_handler is not None:
            return self.post_handler(method, path, headers, body)
        key = f"{method} {path}"
        if key in self.responses:
            value = self.responses[key]
        else:
            value = self.responses[path]
        if isinstance(value, Exception):
            raise value
        return value


def ok(data):
    return {"code": "00000", "data": data}


def contract():
    return {
        "symbol": "BTCUSDT",
        "minTradeNum": "0.001",
        "sizeMultiplier": "0.001",
        "pricePlace": "1",
        "priceEndStep": "1",
        "minTradeUSDT": "5",
    }


def baseline_ok(**overrides):
    payload = {
        ACCOUNTS: ok([{"marginCoin": "USDT", "accountEquity": "1000", "marginMode": "isolated"}]),
        POSITIONS: ok([]),
        PENDING: ok([]),
        TICKER: ok([{"lastPr": "100.0", "markPrice": "100.0"}]),
        CONTRACTS: ok([contract()]),
        ACCOUNT_SYMBOL: ok({"marginMode": "isolated", "posMode": "hedge_mode", "accountEquity": "1000"}),
    }
    payload.update(overrides)
    return payload


def make_client(responses, allow_post=False, post_handler=None, environ=None):
    transport = FakeTransport(responses, post_handler=post_handler)
    client = DemoVerifyClient(
        credentials=ReadOnlyCredentials("public-key", "secret-value", "pass-value"),
        transport=transport,
        clock=lambda: 1700000000,
        allow_post=allow_post,
        environ=environ or {"BITGET_ENV": "demo"},
    )
    return client, transport


def cases_by_id(report):
    return {case.case_id: case for case in report.cases}


class ClassifyTests(unittest.TestCase):
    def test_dispatch_matrix(self):
        self.assertEqual(classify_dispatch(sent=False), "VERIFIED_NOT_RECEIVED")
        self.assertEqual(classify_dispatch(sent=True, timeout=True), "UNKNOWN")
        self.assertEqual(classify_dispatch(sent=True, unparseable=True), "UNKNOWN")
        self.assertEqual(classify_dispatch(sent=True, response={"code": "43001"}), "REJECTED")
        self.assertEqual(
            classify_dispatch(sent=True, response={"code": "00000", "data": {"orderId": "1", "clientOid": "a"}}),
            "FOUND",
        )
        self.assertEqual(classify_dispatch(sent=True, found_on_exchange=False), "NOT_FOUND")


class RedactionTests(unittest.TestCase):
    def test_headers_and_equity_are_redacted(self):
        headers = redact_headers(
            {"ACCESS-KEY": "public-key", "ACCESS-SIGN": "sig", "ACCESS-PASSPHRASE": "pass-value", "paptrading": "1"}
        )
        self.assertEqual(headers["paptrading"], "1")
        self.assertEqual(headers["ACCESS-KEY"], "[redacted]")
        self.assertNotIn("public-key", json.dumps(headers))
        payload = redact_payload({"accountEquity": "1000", "marginMode": "isolated", "orderId": "123456789"})
        self.assertEqual(payload["accountEquity"], "present")
        self.assertEqual(payload["marginMode"], "isolated")
        self.assertNotEqual(payload["orderId"], "123456789")


class RowsTests(unittest.TestCase):
    def test_empty_pending_wrapper_is_zero_orders(self):
        self.assertEqual(rows({"entrustedList": None, "endId": "0"}), [])
        self.assertEqual(rows({"entrustedList": [], "endId": "0"}), [])
        self.assertEqual(len(rows({"entrustedList": [{"symbol": "ETHUSDT", "status": "live"}]})), 1)


class RoundingTests(unittest.TestCase):
    def test_size_and_price_follow_contract(self):
        spec = contract()
        self.assertEqual(round_size(spec), Decimal("0.001"))
        self.assertEqual(round_price(Decimal("96.19"), spec), Decimal("96.1"))


class BaselineTests(unittest.TestCase):
    def test_get_baseline_pass_and_defers_post(self):
        client, transport = make_client(baseline_ok())
        report = run_demo_verify(client, symbol=SYMBOL, now=NOW, place_orders=False)
        by_id = cases_by_id(report)
        self.assertEqual(by_id["D0"].verdict, "PASS")
        self.assertEqual(by_id["D1"].verdict, "PASS")
        self.assertEqual(by_id["D2"].verdict, "PASS")
        self.assertEqual(by_id["D3"].verdict, "PASS")
        self.assertEqual(by_id["D4"].verdict, "PASS")
        self.assertEqual(by_id["D5"].verdict, "BLOCKED")
        self.assertEqual(by_id["D5"].dispatch, "VERIFIED_NOT_RECEIVED")
        self.assertEqual(by_id["D7"].verdict, "BLOCKED")
        self.assertTrue(all(call[0] == "GET" for call in transport.calls))
        self.assertTrue(all(call[2]["paptrading"] == "1" for call in transport.calls))
        dump = json.dumps(report.to_dict())
        self.assertNotIn("secret-value", dump)
        self.assertNotIn("public-key", dump)
        self.assertNotIn("pass-value", dump)
        self.assertNotIn("1000", dump)

    def test_crossed_margin_fails_d2_and_blocks_place(self):
        client, _transport = make_client(
            baseline_ok(
                **{
                    ACCOUNT_SYMBOL: ok({"marginMode": "crossed", "posMode": "hedge_mode", "accountEquity": "1000"}),
                    ACCOUNTS: ok([{"marginCoin": "USDT", "accountEquity": "1000", "marginMode": "crossed"}]),
                }
            )
        )
        report = run_demo_verify(client, symbol=SYMBOL, now=NOW, place_orders=True)
        by_id = cases_by_id(report)
        self.assertEqual(by_id["D2"].verdict, "FAIL")
        self.assertEqual(by_id["D5"].verdict, "BLOCKED")
        self.assertTrue(all(item["method"] == "GET" for item in client.calls))

    def test_leftover_position_blocks_entry(self):
        client, _transport = make_client(
            baseline_ok(**{POSITIONS: ok([{"symbol": "BTCUSDT", "total": "1", "marginMode": "isolated"}])})
        )
        report = run_demo_verify(client, symbol=SYMBOL, now=NOW, place_orders=True)
        self.assertEqual(cases_by_id(report)["D5"].verdict, "BLOCKED")


class PlaceCancelTests(unittest.TestCase):
    def test_found_place_and_cancel(self):
        oid = verify_client_oid("demo-verify", "entry", 1)
        state = {"cancelled": False}

        def post_handler(method, path, headers, body):
            self.assertEqual(headers["paptrading"], "1")
            payload = json.loads(body)
            if path == PLACE:
                self.assertEqual(payload["marginMode"], "isolated")
                self.assertEqual(payload["orderType"], "limit")
                self.assertEqual(payload["tradeSide"], "open")
                return ok({"orderId": "11111111", "clientOid": payload["clientOid"]})
            self.assertEqual(path, CANCEL)
            state["cancelled"] = True
            return ok({"orderId": "11111111", "clientOid": payload["clientOid"]})

        inner = FakeTransport(baseline_ok(), post_handler=post_handler)

        def sequenced(method, path, headers, body, timeout):
            if method == "GET" and path.startswith("/api/v2/mix/order/detail"):
                inner.calls.append((method, path, dict(headers), body))
                status = "canceled" if state["cancelled"] else "live"
                return ok({"status": status, "clientOid": oid, "orderId": "11111111", "size": "0.001"})
            return inner(method, path, headers, body, timeout)

        client = DemoVerifyClient(
            credentials=ReadOnlyCredentials("public-key", "secret-value", "pass-value"),
            transport=sequenced,
            clock=lambda: 1700000000,
            allow_post=True,
            environ={"BITGET_ENV": "demo"},
        )
        report = run_demo_verify(client, symbol=SYMBOL, zone_id="demo-verify", now=NOW, place_orders=True)
        by_id = cases_by_id(report)
        self.assertEqual(by_id["D5"].verdict, "PASS")
        self.assertEqual(by_id["D5"].dispatch, "FOUND")
        self.assertEqual(by_id["D6"].verdict, "PASS")
        self.assertEqual(by_id["D6"].dispatch, "FOUND")
        self.assertTrue(any(call["method"] == "POST" for call in client.calls))

    def test_rejected_place(self):
        def post_handler(method, path, headers, body):
            return {"code": "43012", "msg": "rejected"}

        client, _transport = make_client(baseline_ok(), allow_post=True, post_handler=post_handler)
        report = run_demo_verify(client, symbol=SYMBOL, now=NOW, place_orders=True)
        by_id = cases_by_id(report)
        self.assertEqual(by_id["D5"].verdict, "FAIL")
        self.assertEqual(by_id["D5"].dispatch, "REJECTED")
        self.assertEqual(by_id["D6"].verdict, "BLOCKED")

    def test_timeout_is_unknown_and_does_not_retry(self):
        posts = {"count": 0}

        def post_handler(method, path, headers, body):
            posts["count"] += 1
            raise TimeoutError("timed out")

        client, _transport = make_client(baseline_ok(), allow_post=True, post_handler=post_handler)
        report = run_demo_verify(client, symbol=SYMBOL, now=NOW, place_orders=True)
        by_id = cases_by_id(report)
        self.assertEqual(by_id["D5"].dispatch, "UNKNOWN")
        self.assertEqual(by_id["D5"].verdict, "UNKNOWN")
        self.assertEqual(posts["count"], 1)

    def test_live_flag_blocks_post(self):
        client, _transport = make_client(
            baseline_ok(),
            allow_post=True,
            environ={"BITGET_ENV": "demo", "GROK_TRADER_ALLOW_LIVE": "1"},
        )
        report = run_demo_verify(client, symbol=SYMBOL, now=NOW, place_orders=True)
        by_id = cases_by_id(report)
        self.assertEqual(by_id["D5"].verdict, "BLOCKED")
        self.assertEqual(by_id["D5"].dispatch, "VERIFIED_NOT_RECEIVED")
        self.assertTrue(all(item["method"] != "POST" for item in client.calls))


class CliTests(unittest.TestCase):
    def test_cli_get_only_json(self):
        client, transport = make_client(baseline_ok())
        with tempfile.TemporaryDirectory() as tmp:
            evidence = os.path.join(tmp, "demo.jsonl")
            with redirect_stdout(io.StringIO()) as stdout:
                code = demo_verify_cli_run(
                    ["run", "--symbol", "BTCUSDT", "--json", "--now", NOW, "--evidence", evidence],
                    client=client,
                )
            payload = stdout.getvalue()
            self.assertEqual(code, 0)
            self.assertIn('"D0"', payload)
            self.assertNotIn("secret-value", payload)
            self.assertTrue(all(call[0] == "GET" for call in transport.calls))
            with open(evidence, encoding="utf-8") as handle:
                stored = handle.read()
            self.assertNotIn("secret-value", stored)
            self.assertNotIn("public-key", stored)

    def test_place_orders_requires_confirm(self):
        with redirect_stdout(io.StringIO()) as stdout:
            code = demo_verify_cli_run(["run", "--symbol", "BTCUSDT", "--place-orders", "--json"])
        self.assertEqual(code, 2)
        self.assertIn("PostDisabled", stdout.getvalue())

    def test_live_env_fails_closed(self):
        with self.assertRaises(LiveModeDisabled):
            DemoVerifyClient(environ={"BITGET_ENV": "live"})
        with patch.dict(os.environ, {"BITGET_ENV": "live"}, clear=False):
            with redirect_stdout(io.StringIO()) as stdout:
                code = demo_verify_cli_run(["run", "--symbol", "BTCUSDT", "--json"])
        self.assertEqual(code, 2)
        self.assertIn("LiveModeDisabled", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
