import os
import tempfile
import unittest

from executor import IntentRole, ZoneExecutor, ZoneOrderSpec
from executor.p1_adapter import P1IntegrationStore
from trader.zone_store import ZoneStore


class P1AdapterTests(unittest.TestCase):
    def config(self):
        return {
            "symbol": "BTCUSDT",
            "side": "long",
            "ref_price": "100",
            "zone_loss_limit_usdt": "10",
            "sl_pct": "5",
        }

    def test_executor_records_are_persisted_in_p1_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "zones.sqlite3")
            with ZoneStore(path) as zones:
                zones.create_zone(self.config(), zone_id="zone-bridge", state="ACTIVE")
                with P1IntegrationStore(zones) as bridge:
                    executor = ZoneExecutor(bridge)
                    executor.create_zone(
                        "zone-bridge",
                        [ZoneOrderSpec(IntentRole.ENTRY, 0, "1", "100", "buy")],
                        position_quantity="1",
                        position_side="long",
                    )
                    action = executor.on_risk_trigger("zone-bridge", "PRICE_SL")
                    self.assertIsNotNone(action.emergency_close_client_oid)
                    self.assertGreaterEqual(len(bridge.intents("zone-bridge")), 2)
                    self.assertTrue(all(event.get("dry_run") for event in bridge.events("zone-bridge")))
                with ZoneStore(path) as reopened:
                    self.assertEqual(reopened.get_zone("zone-bridge").state, "ACTIVE")

    def test_unknown_zone_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with ZoneStore(os.path.join(tmp, "zones.sqlite3")) as zones:
                with P1IntegrationStore(zones) as bridge:
                    with self.assertRaises(Exception):
                        bridge.append_event({"zone_id": "missing", "kind": "x"})

    def test_proposal_is_audit_event_not_intent(self):
        with tempfile.TemporaryDirectory() as tmp:
            with ZoneStore(os.path.join(tmp, "zones.sqlite3")) as zones:
                zones.create_zone(self.config(), zone_id="opp-1", state="ACTIVE")
                with P1IntegrationStore(zones) as bridge:
                    bridge.record_proposal({
                        "proposal_id": "p-1",
                        "result": "ACCEPTED",
                        "snapshot": {"opportunity_id": "opp-1"},
                    })
                    self.assertEqual(bridge.intents("opp-1"), [])
                    self.assertEqual(bridge.events("opp-1")[0]["event"], "AI_PROPOSAL_RECORDED")


if __name__ == "__main__":
    unittest.main()
