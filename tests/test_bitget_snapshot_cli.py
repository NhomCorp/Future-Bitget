from __future__ import annotations

import io
import json
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from trader.bitget_readonly import (
    LiveModeDisabled,
    ReadOnlyBitgetAdapter,
    ReadOnlyCredentials,
)
from trader.bitget_snapshot_cli import build_dashboard_snapshot, run as snapshot_cli_run


ACCOUNT_PATH = "/api/v2/mix/account/accounts?productType=USDT-FUTURES"
POSITIONS_PATH = "/api/v2/mix/position/all-position?productType=USDT-FUTURES&marginCoin=USDT"
ORDERS_PATH = "/api/v2/mix/order/orders-pending?productType=USDT-FUTURES"
FILLS_PATH = "/api/v2/mix/order/fills?productType=USDT-FUTURES&limit=20&symbol=BTCUSDT"
FILLS_PATH_ALL = "/api/v2/mix/order/fills?productType=USDT-FUTURES&limit=20"
TICKER_PATH = "/api/v2/mix/market/ticker?productType=USDT-FUTURES&symbol=BTCUSDT"
CONTRACT_PATH = "/api/v2/mix/market/contracts?productType=USDT-FUTURES&symbol=BTCUSDT"


class FakeTransport:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, method, path, headers, body, timeout):
        self.calls.append((method, path, dict(headers), body))
        return self.responses[path]


def ok(data):
    return {"code": "00000", "data": data}


def make_adapter(responses):
    transport = FakeTransport(responses)
    adapter = ReadOnlyBitgetAdapter(
        credentials=ReadOnlyCredentials("public-key", "secret", "passphrase"),
        transport=transport,
        clock=lambda: 1700000000,
    )
    return adapter, transport


def demo_responses():
    return {
        ACCOUNT_PATH: ok(
            [
                {
                    "marginCoin": "USDT",
                    "accountEquity": "1000.25",
                    "available": "800.5",
                    "unrealizedPL": "12.5",
                    "secretDump": "should-not-leak",
                }
            ]
        ),
        POSITIONS_PATH: ok(
            [
                {
                    "symbol": "BTCUSDT",
                    "holdSide": "long",
                    "total": "0.01",
                    "leverage": "5",
                    "marginMode": "isolated",
                    "openPriceAvg": "60000",
                    "markPrice": "60100",
                    "liquidationPrice": "50000",
                    "unrealizedPL": "10",
                },
                {"symbol": "ETHUSDT", "holdSide": "short", "total": "0"},
            ]
        ),
        ORDERS_PATH: ok(
            {
                "entrustedList": [
                    {
                        "symbol": "BTCUSDT",
                        "side": "buy",
                        "posSide": "long",
                        "tradeSide": "open",
                        "price": "59000",
                        "size": "0.01",
                        "orderType": "limit",
                        "status": "live",
                    }
                ],
                "endId": "abc",
            }
        ),
        FILLS_PATH: ok(
            {
                "fillList": [
                    {
                        "tradeId": "fill-new",
                        "orderId": "ord-1",
                        "clientOid": "oid-local-1",
                        "symbol": "BTCUSDT",
                        "side": "buy",
                        "posSide": "long",
                        "tradeSide": "open",
                        "price": "60100",
                        "baseVolume": "0.01",
                        "profit": "1.5",
                        "tradeScope": "taker",
                        "cTime": "1700000002000",
                        "feeDetail": [{"totalFee": "-0.02"}],
                        "secretDump": "should-not-leak",
                    },
                    {
                        "tradeId": "fill-old",
                        "symbol": "BTCUSDT",
                        "side": "sell",
                        "tradeSide": "close",
                        "price": "60000",
                        "baseVolume": "0.002",
                        "cTime": "1700000001000",
                    },
                ],
                "endId": "fill-end",
            }
        ),
        FILLS_PATH_ALL: ok({"fillList": [], "endId": "none"}),
        TICKER_PATH: ok([{"symbol": "BTCUSDT", "lastPr": "60110", "markPrice": "60105", "fundingRate": "0.0001"}]),
        CONTRACT_PATH: ok([{"symbol": "BTCUSDT", "minTradeNum": "0.0001"}]),
    }


class SnapshotCliTests(unittest.TestCase):
    def test_cli_json_is_filtered_get_only_and_redacted(self):
        adapter, transport = make_adapter(demo_responses())
        with redirect_stdout(io.StringIO()) as stdout:
            code = snapshot_cli_run(["snapshot", "--symbol", "BTCUSDT"], adapter=adapter)
        payload = stdout.getvalue()
        self.assertEqual(code, 0)
        data = json.loads(payload)
        self.assertTrue(data["ok"])
        self.assertEqual(data["equity"], "1000.25")
        self.assertEqual(data["assets"][0]["margin_coin"], "USDT")
        self.assertEqual(data["assets"][0]["available"], "800.5")
        self.assertEqual(len(data["positions"]), 1)
        self.assertEqual(data["positions"][0]["symbol"], "BTCUSDT")
        self.assertEqual(data["positions"][0]["size"], "0.01")
        self.assertEqual(data["pending_orders"][0]["price"], "59000")
        self.assertEqual(len(data["fills"]), 2)
        self.assertEqual(data["fills"][0]["trade_id"], "fill-new")
        self.assertEqual(data["fills"][0]["fee"], "-0.02")
        self.assertEqual(data["fills"][0]["profit"], "1.5")
        self.assertEqual(data["fills"][0]["filled_at"], "2023-11-14T22:13:22Z")
        self.assertEqual(data["fills"][0]["client_oid"], "oid-local-1")
        self.assertEqual(data["fills"][1]["trade_id"], "fill-old")
        self.assertEqual(data["ticker"]["last"], "60110")
        self.assertEqual(data["ticker"]["mark"], "60105")
        self.assertEqual(data["ticker"]["funding"], "0.0001")
        self.assertNotIn("accountEquity", payload)
        self.assertNotIn("secretDump", payload)
        self.assertNotIn("secret", payload)
        self.assertNotIn("public-key", payload)
        self.assertNotIn("passphrase", payload)
        self.assertNotIn("ACCESS-KEY", payload)
        self.assertNotIn("minTradeNum", payload)
        self.assertNotIn("feeDetail", payload)
        self.assertNotIn("fill-history", payload)
        self.assertTrue(any(call[1] == FILLS_PATH for call in transport.calls))
        self.assertFalse(any("fill-history" in call[1] for call in transport.calls))
        self.assertEqual({call[0] for call in transport.calls}, {"GET"})
        self.assertTrue(all(call[2]["paptrading"] == "1" for call in transport.calls))
        self.assertTrue(all(call[3] is None for call in transport.calls))

    def test_cli_live_env_fails_closed(self):
        with patch.dict(os.environ, {"BITGET_ENV": "live", "GROK_TRADER_ALLOW_LIVE": ""}, clear=False):
            with self.assertRaises(LiveModeDisabled):
                ReadOnlyBitgetAdapter(environ={"BITGET_ENV": "live"})
            with redirect_stdout(io.StringIO()) as stdout:
                code = snapshot_cli_run(["snapshot"], adapter=None, environ={"BITGET_ENV": "live"})
            self.assertEqual(code, 2)
            payload = stdout.getvalue()
            self.assertIn("LiveModeDisabled", payload)
            self.assertNotIn("secret", payload)

    def test_cli_live_guard_fails_closed(self):
        with redirect_stdout(io.StringIO()) as stdout:
            code = snapshot_cli_run(
                ["snapshot"],
                adapter=None,
                environ={"GROK_TRADER_ALLOW_LIVE": "1", "BITGET_ENV": "demo"},
            )
        self.assertEqual(code, 2)
        payload = stdout.getvalue()
        self.assertIn("LiveModeDisabled", payload)
        self.assertIn('"ok": false', payload)

    def test_cli_snapshot_without_symbol_still_gets_fills(self):
        adapter, transport = make_adapter(demo_responses())
        with redirect_stdout(io.StringIO()) as stdout:
            code = snapshot_cli_run(["snapshot"], adapter=adapter)
        self.assertEqual(code, 0)
        data = json.loads(stdout.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["fills"], [])
        self.assertTrue(any(call[1] == FILLS_PATH_ALL for call in transport.calls))
        self.assertFalse(any("fill-history" in call[1] for call in transport.calls))

    def test_build_dashboard_snapshot_filters_and_caps_fills(self):
        fills = [
            {
                "tradeId": f"t{index}",
                "symbol": "BTCUSDT",
                "side": "buy",
                "price": "1",
                "baseVolume": "0.001",
                "cTime": str(1_700_000_000_000 + index),
                "secretDump": "nope",
            }
            for index in range(25)
        ]
        payload = build_dashboard_snapshot(
            {
                "product_type": "USDT-FUTURES",
                "account": [],
                "positions": [],
                "pending_orders": [],
                "fills": {"fillList": fills, "endId": "x"},
            }
        )
        self.assertEqual(len(payload["fills"]), 20)
        self.assertEqual(payload["fills"][0]["trade_id"], "t24")
        self.assertEqual(payload["fills"][-1]["trade_id"], "t5")
        self.assertNotIn("secretDump", json.dumps(payload))
        empty = build_dashboard_snapshot({"account": [], "positions": [], "pending_orders": []})
        self.assertEqual(empty["fills"], [])

    def test_cli_missing_credentials(self):
        with redirect_stdout(io.StringIO()) as stdout:
            code = snapshot_cli_run(["snapshot"], adapter=None, environ={"BITGET_ENV": "demo"})
        self.assertEqual(code, 2)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "MissingReadOnlyCredentials")


if __name__ == "__main__":
    unittest.main()
