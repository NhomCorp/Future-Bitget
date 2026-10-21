import unittest
from decimal import Decimal

from executor.zone_executor import (
    IdempotencyConflict,
    IntentRole,
    IntentState,
    InvalidTransition,
    OrderEventType,
    OrderObservation,
    RiskTrigger,
    ZoneExecutor,
    ZoneOrderSpec,
    ZoneState,
    deterministic_client_oid,
)


class MemoryZoneStore:
    def __init__(self):
        self.intents = []
        self.events = []
        self.zones = []

    def save_intent(self, record):
        self.intents.append(dict(record))

    def append_event(self, event):
        self.events.append(dict(event))

    def save_zone(self, snapshot):
        self.zones.append(dict(snapshot))


class ZoneExecutorTests(unittest.TestCase):
    def make_executor(self, position_quantity="0", position_side="long"):
        store = MemoryZoneStore()
        executor = ZoneExecutor(store)
        executor.create_zone(
            "zone-1",
            [
                ZoneOrderSpec(IntentRole.ENTRY, 0, "1.00", "100", "buy"),
                ZoneOrderSpec(IntentRole.DCA, 1, "2.00", "98", "buy"),
            ],
            position_quantity=position_quantity,
            position_side=position_side,
        )
        return executor, store

    def test_client_oid_is_deterministic_and_bounded(self):
        first = deterministic_client_oid("zone-1", IntentRole.ENTRY, 0)
        second = deterministic_client_oid("zone-1", IntentRole.ENTRY, 0)
        different = deterministic_client_oid("zone-1", IntentRole.ENTRY, 1)
        self.assertEqual(first, second)
        self.assertNotEqual(first, different)
        self.assertLessEqual(len(first), 32)
        self.assertNotIn("/", first)

    def test_creation_is_idempotent_and_payload_changes_are_rejected(self):
        executor, _ = self.make_executor()
        original = executor.intents("zone-1")
        repeated = executor.create_zone(
            "zone-1",
            [
                ZoneOrderSpec("entry", 0, "1.00", "100", "buy"),
                ZoneOrderSpec("dca", 1, "2.00", "98", "buy"),
            ],
        )
        self.assertEqual([item.client_oid for item in original], [item.client_oid for item in repeated])
        with self.assertRaises(IdempotencyConflict):
            executor.create_zone(
                "zone-1",
                [
                    ZoneOrderSpec("entry", 0, "1.01", "100", "buy"),
                    ZoneOrderSpec("dca", 1, "2.00", "98", "buy"),
                ],
            )

    def test_partial_fill_timeout_unknown_and_reconcile(self):
        executor, _ = self.make_executor()
        oid = executor.intents("zone-1")[0].client_oid
        self.assertEqual(executor.mark_submitted(oid).state, IntentState.ACCEPTED)
        self.assertEqual(executor.record_fill(oid, "0.40").state, IntentState.PARTIALLY_FILLED)
        self.assertEqual(executor.record_fill(oid, "0.40").state, IntentState.PARTIALLY_FILLED)
        self.assertEqual(
            executor.apply_observation(OrderObservation(oid, OrderEventType.TIMEOUT)).state,
            IntentState.TIMED_OUT,
        )
        self.assertEqual(
            executor.apply_observation(OrderObservation(oid, OrderEventType.UNKNOWN)).state,
            IntentState.UNKNOWN,
        )
        self.assertEqual(
            executor.apply_observation(OrderObservation(oid, OrderEventType.RECONCILED_OPEN)).state,
            IntentState.PARTIALLY_FILLED,
        )
        self.assertEqual(executor.record_fill(oid, "1.00").state, IntentState.FILLED)
        with self.assertRaises(InvalidTransition):
            executor.record_fill(oid, "0.50")

    def test_loss_budget_cancels_entries_and_records_emergency_close(self):
        executor, store = self.make_executor(position_quantity="0.75", position_side="long")
        action = executor.on_risk_trigger("zone-1", RiskTrigger.LOSS_BUDGET)
        self.assertEqual(action.trigger, RiskTrigger.LOSS_BUDGET)
        self.assertEqual(len(action.cancelled_client_oids), 2)
        self.assertEqual(len(action.cancellation_intent_oids), 2)
        self.assertIsNotNone(action.emergency_close_client_oid)
        snapshot = executor.snapshot("zone-1")
        self.assertEqual(snapshot["state"], ZoneState.RISK_STOPPING.value)
        emergency = executor.get_intent(action.emergency_close_client_oid)
        self.assertEqual(emergency.role, IntentRole.EMERGENCY_CLOSE)
        self.assertEqual(emergency.state, IntentState.DRY_RUN_RECORDED)
        self.assertEqual(emergency.quantity, Decimal("0.75"))
        self.assertEqual(emergency.side, "sell")
        self.assertTrue(emergency.metadata["dry_run_only"])
        self.assertTrue(all(record.get("dry_run") for record in store.events))

    def test_both_trigger_is_idempotent_and_does_not_duplicate_close(self):
        executor, _ = self.make_executor(position_quantity="1", position_side="short")
        first = executor.on_risk_trigger("zone-1", RiskTrigger.PRICE_SL)
        second = executor.on_risk_trigger("zone-1", RiskTrigger.LOSS_BUDGET)
        third = executor.on_risk_trigger("zone-1", RiskTrigger.BOTH)
        self.assertEqual(second.trigger, RiskTrigger.BOTH)
        self.assertEqual(third.trigger, RiskTrigger.BOTH)
        self.assertEqual(first.emergency_close_client_oid, second.emergency_close_client_oid)
        self.assertEqual(second.emergency_close_client_oid, third.emergency_close_client_oid)
        self.assertEqual(
            len([item for item in executor.intents("zone-1") if item.role is IntentRole.EMERGENCY_CLOSE]),
            1,
        )
        emergency = executor.get_intent(first.emergency_close_client_oid)
        self.assertEqual(emergency.side, "buy")

    def test_no_network_or_trade_key_is_needed(self):
        executor, _ = self.make_executor()
        self.assertIsNone(getattr(executor, "client", None))
        self.assertTrue(executor.snapshot("zone-1")["dry_run"])


if __name__ == "__main__":
    unittest.main()
