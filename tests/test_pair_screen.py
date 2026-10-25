from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from trader.bitget_readonly import (
    LiveModeDisabled,
    ReadOnlyBitgetAdapter,
    ReadOnlyCredentials,
)
from trader.pair_screen_cli import run as pair_screen_cli_run
from trading.pair_screen import rank_pair_candidates


TICKERS_PATH = "/api/v2/mix/market/tickers?productType=USDT-FUTURES"


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


class PairScreenTests(unittest.TestCase):
    def test_ranks_by_quote_volume_and_skips_invalid(self):
        rows = [
            {"symbol": "ethusdt", "lastPr": "2500", "usdtVolume": "100", "change24h": "1.5"},
            {"symbol": "BTCUSDT", "lastPr": "60000", "quoteVolume": "500", "markPrice": "60001"},
            {"symbol": "BAD SPACE", "usdtVolume": "9999"},
            {"symbol": "ZEROUSDT", "usdtVolume": "0"},
            {"symbol": "MISSUSDT"},
            {"symbol": "SOLUSDT", "usdtVolume": "not-a-number"},
            {"secretDump": "should-not-leak", "symbol": "XRPUSDT", "usdtVolume": "50"},
        ]
        ranked = rank_pair_candidates(rows, limit=10)
        self.assertEqual([item["symbol"] for item in ranked], ["BTCUSDT", "ETHUSDT", "XRPUSDT"])
        self.assertEqual(ranked[0]["volume24h"], "500")
        self.assertEqual(ranked[0]["last"], "60000")
        self.assertEqual(ranked[0]["reason"], "Top khối lượng 24h USDT-M")
        self.assertNotIn("secretDump", ranked[2])
        encoded = json.dumps({"candidates": ranked}, ensure_ascii=True)
        self.assertIn("BTCUSDT", encoded)
        self.assertEqual(json.loads(encoded)["candidates"][0]["reason"], ranked[0]["reason"])

    def test_exclude_and_limit(self):
        rows = [
            {"symbol": "BTCUSDT", "usdtVolume": "30"},
            {"symbol": "ETHUSDT", "usdtVolume": "20"},
            {"symbol": "SOLUSDT", "usdtVolume": "10"},
        ]
        ranked = rank_pair_candidates(rows, limit=1, exclude=("btcusdt",))
        self.assertEqual([item["symbol"] for item in ranked], ["ETHUSDT"])

    def test_cli_public_get_redacts_and_blocks_live(self):
        adapter, transport = make_adapter(
            {
                TICKERS_PATH: ok(
                    [
                        {
                            "symbol": "BTCUSDT",
                            "lastPr": "60000",
                            "usdtVolume": "1000",
                            "secretDump": "should-not-leak",
                        }
                    ]
                )
            }
        )
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = pair_screen_cli_run(["screen", "--limit", "5"], adapter=adapter)
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["candidates"][0]["symbol"], "BTCUSDT")
        self.assertNotIn("secretDump", json.dumps(payload))
        self.assertEqual(transport.calls[0][0], "GET")
        self.assertEqual(transport.calls[0][1], TICKERS_PATH)
        self.assertNotIn("ACCESS-KEY", transport.calls[0][2])

        blocked = io.StringIO()
        with redirect_stdout(blocked):
            live_code = pair_screen_cli_run(
                ["screen"],
                environ={"GROK_TRADER_ALLOW_LIVE": "1", "BITGET_ENV": "demo"},
            )
        self.assertEqual(live_code, 2)
        live_payload = json.loads(blocked.getvalue())
        self.assertFalse(live_payload["ok"])
        self.assertEqual(live_payload["error"], "LiveModeDisabled")
        self.assertNotIn("public-key", blocked.getvalue())

    def test_adapter_rejects_live_env(self):
        with self.assertRaises(LiveModeDisabled):
            ReadOnlyBitgetAdapter(environ={"BITGET_ENV": "live"})

    def test_cli_empty_tickers(self):
        adapter, _transport = make_adapter({TICKERS_PATH: ok([])})
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = pair_screen_cli_run(["screen"], adapter=adapter)
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["candidates"], [])


if __name__ == "__main__":
    unittest.main()
