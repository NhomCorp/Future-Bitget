"""Focused tests for the standalone P1 zone foundation."""
from __future__ import annotations

import os
import tempfile
import unittest

from trader.bitget_readonly import (
    BitgetResponseError,
    LiveModeDisabled,
    MissingReadOnlyCredentials,
    ReadOnlyBitgetAdapter,
    ReadOnlyCredentials,
    sign,
)
from trader.zone_cli import run
from trader.zone_store import ZoneStore, ZoneValidationError


class FakeTransport:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, method, path, headers, body, timeout):
        self.calls.append((method, path, dict(headers), body))
        return self.responses[path]


class ZoneStoreTests(unittest.TestCase):
    def config(self, **overrides):
        config = {
            "symbol": "BTCUSDT",
            "side": "long",
            "ref_price": "100",
            "zone_loss_limit_usdt": "10",
            "sl_pct": "5",
            "policy_version": "test-policy",
        }
        config.update(overrides)
        return config

    def test_persists_config_events_and_recovers_after_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "zones.sqlite3")
            with ZoneStore(path) as store:
                zone = store.create_zone(self.config(), zone_id="zone-a", now="2026-01-01T00:00:00Z")
                store.activate_zone(zone.zone_id, now="2026-01-01T00:00:01Z")
                result = store.record_observation(
                    zone.zone_id,
                    {"mark_price": "96", "realized_pnl": "-3", "unrealized_pnl": "-2", "fees": "1", "funding_paid": "0.5"},
                    source="mock",
                    now="2026-01-01T00:00:02Z",
                )
                self.assertEqual(result["state"], "ACTIVE")
            with ZoneStore(path) as reopened:
                recovered = reopened.get_zone("zone-a")
                self.assertEqual(recovered.state, "ACTIVE")
                self.assertEqual(recovered.ref_price, "100")
                self.assertEqual(reopened.latest_observation("zone-a")["net_pnl"], "-6.5")
                self.assertGreaterEqual(len(reopened.events("zone-a")), 3)

    def test_risk_trigger_is_idempotent_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "zones.sqlite3")
            with ZoneStore(path) as store:
                store.create_zone(self.config(), zone_id="zone-b", state="ACTIVE")
                first = store.record_observation("zone-b", {"mark_price": "95"}, source="dry-run")
                second = store.record_observation("zone-b", {"mark_price": "90"}, source="dry-run")
                self.assertEqual(first["reason"], "PRICE_SL")
                self.assertEqual(second["state"], "STOPPING")
                self.assertEqual(second["triggered"], False)
            with ZoneStore(path) as reopened:
                self.assertEqual(reopened.get_zone("zone-b").state, "STOPPING")
                event_types = [event["event_type"] for event in reopened.events("zone-b")]
                self.assertEqual(event_types.count("RISK_TRIGGERED"), 1)

    def test_both_risk_limits_report_both_and_unknown_state_is_fail_closed(self):
        with ZoneStore(":memory:") as store:
            store.create_zone(self.config(), zone_id="zone-c", state="ACTIVE")
            result = store.record_observation("zone-c", {"mark_price": "95", "realized_pnl": "-10"})
            self.assertEqual(result["reason"], "BOTH")
            with self.assertRaises(ZoneValidationError):
                store.transition_zone("zone-c", "ACTIVE")


class AdapterTests(unittest.TestCase):
    def test_missing_credentials_is_explicit(self):
        with self.assertRaises(MissingReadOnlyCredentials):
            ReadOnlyBitgetAdapter(environ={}).account()

    def test_live_mode_is_hard_disabled(self):
        with self.assertRaises(LiveModeDisabled):
            ReadOnlyBitgetAdapter(demo=False)
        with self.assertRaises(LiveModeDisabled):
            ReadOnlyBitgetAdapter(environ={"BITGET_ENV": "live"})

    def test_public_and_private_get_only(self):
        responses = {
            "/api/v2/mix/market/ticker?productType=USDT-FUTURES&symbol=BTCUSDT": {"code": "00000", "data": [{"lastPr": "100"}]},
            "/api/v2/mix/account/accounts?productType=USDT-FUTURES": {"code": "00000", "data": [{"accountEquity": "100"}]},
        }
        transport = FakeTransport(responses)
        adapter = ReadOnlyBitgetAdapter(
            credentials=ReadOnlyCredentials("public-key", "secret", "passphrase"),
            transport=transport,
            clock=lambda: 1700000000,
        )
        self.assertEqual(adapter.public_ticker("btcusdt")[0]["lastPr"], "100")
        self.assertEqual(adapter.account()[0]["accountEquity"], "100")
        self.assertEqual([call[0] for call in transport.calls], ["GET", "GET"])
        self.assertEqual(transport.calls[0][2]["paptrading"], "1")
        self.assertEqual(transport.calls[1][2]["ACCESS-SIGN"], sign("secret", "1700000000000", "GET", transport.calls[1][1]))

    def test_non_success_does_not_leak_response_or_credentials(self):
        transport = FakeTransport({"/api/v2/mix/account/accounts?productType=USDT-FUTURES": {"code": "43001", "msg": "bad key secret-value"}})
        adapter = ReadOnlyBitgetAdapter(
            credentials=ReadOnlyCredentials("key", "secret", "pass"), transport=transport
        )
        with self.assertRaises(BitgetResponseError) as error:
            adapter.account()
        self.assertNotIn("secret-value", str(error.exception))
        self.assertNotIn("secret", str(error.exception))


class CliTests(unittest.TestCase):
    def test_cli_preview_status_sync_mock(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "zones.sqlite3")
            self.assertEqual(run(["--store", path, "preview", "--zone-id", "zone-cli", "--symbol", "ETHUSDT", "--side", "short", "--ref-price", "2000", "--sl-pct", "2", "--json"]), 0)
            self.assertEqual(run(["--store", path, "sync", "--zone-id", "zone-cli", "--activate", "--mark-price", "2040", "--json"]), 0)
            self.assertEqual(run(["--store", path, "status", "--zone-id", "zone-cli", "--json"]), 0)
            with open(path, "rb") as stream:
                self.assertTrue(stream.read(16))


if __name__ == "__main__":
    unittest.main()
