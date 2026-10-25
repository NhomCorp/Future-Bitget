"""Offline tests for Demo kill CLI. Fake poster; no exchange POST."""
from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from trader.demo_kill_cli import run as kill_run


class DemoKillCliTests(unittest.TestCase):
    def _run(self, extra, *, environ=None, poster=None, pending=None, positions=None):
        argv = ["run", "--symbol", "BTCUSDT", "--allowlist", "BTCUSDT", "--json", *extra]
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = kill_run(
                argv,
                environ=environ or {"BITGET_ENV": "demo"},
                poster=poster,
                pending=pending if pending is not None else [],
                positions=positions if positions is not None else [],
            )
        return code, json.loads(buf.getvalue() or "{}")

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

    def test_default_is_dry_run(self):
        calls = []
        code, payload = self._run(
            ["--i-confirm-demo"],
            poster=lambda intent: calls.append(intent.order_role) or {"dispatch": "FOUND"},
            pending=[{"symbol": "BTCUSDT", "clientOid": "oid-1"}],
        )
        self.assertEqual(code, 0)
        self.assertTrue(payload["dry_run"])
        self.assertFalse(payload["exchange_post"])
        self.assertEqual(payload["cancelled"], 1)
        self.assertEqual(calls, [])

    def test_outside_allowlist_does_not_post(self):
        calls = []
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = kill_run(
                ["run", "--symbol", "ETHUSDT", "--allowlist", "BTCUSDT", "--place-orders", "--i-confirm-demo", "--json"],
                environ={"BITGET_ENV": "demo"},
                poster=lambda intent: calls.append(intent.symbol) or {"dispatch": "FOUND"},
                pending=[],
                positions=[],
            )
        payload = json.loads(buf.getvalue() or "{}")
        self.assertEqual(code, 0)
        self.assertEqual(payload["reason_code"], "SYMBOL_NOT_IN_WHITELIST")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
