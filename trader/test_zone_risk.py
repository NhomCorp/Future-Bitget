import json
import os
import tempfile
import unittest
from decimal import Decimal

try:
    from .zone_risk import ZoneRiskConfig, ZoneRiskSnapshot, evaluate
    from .zone_state import (
        ACTIVE,
        CLOSED,
        STOPPING,
        UNKNOWN,
        AppendOnlyLedger,
        ZoneState,
        mark_closed,
        process_snapshot,
        record_unknown,
    )
except ImportError:
    from zone_risk import ZoneRiskConfig, ZoneRiskSnapshot, evaluate
    from zone_state import (
        ACTIVE,
        CLOSED,
        STOPPING,
        UNKNOWN,
        AppendOnlyLedger,
        ZoneState,
        mark_closed,
        process_snapshot,
        record_unknown,
    )


class ZoneRiskTests(unittest.TestCase):
    def config(self, **overrides):
        values = {
            "zone_id": "z-1",
            "symbol": "BTCUSDT",
            "side": "long",
            "ref_price": Decimal("100"),
            "zone_loss_limit_usdt": Decimal("10"),
            "sl_pct": Decimal("5"),
        }
        values.update(overrides)
        return ZoneRiskConfig(**values)

    def test_net_pnl_includes_fees_and_funding(self):
        cfg = self.config(sl_pct=None)
        snap = ZoneRiskSnapshot(
            realized_pnl=Decimal("-4"),
            unrealized_pnl=Decimal("-4"),
            fees=Decimal("1"),
            funding_paid=Decimal("2"),
            funding_received=Decimal("0.5"),
            mark_price=Decimal("100"),
        )
        result = evaluate(cfg, snap)
        self.assertEqual(result.net_pnl, Decimal("-10.5"))
        self.assertEqual(result.reason, "LOSS_BUDGET")

    def test_price_stop_long_and_short(self):
        long_cfg = self.config(zone_loss_limit_usdt=None)
        self.assertEqual(long_cfg.price_stop, Decimal("95.00"))
        self.assertEqual(evaluate(long_cfg, ZoneRiskSnapshot(mark_price="95")).reason, "PRICE_SL")

        short_cfg = self.config(side="short", zone_loss_limit_usdt=None)
        self.assertEqual(short_cfg.price_stop, Decimal("105.00"))
        self.assertEqual(evaluate(short_cfg, ZoneRiskSnapshot(mark_price="105")).reason, "PRICE_SL")

    def test_both_options_use_or_and_report_both(self):
        cfg = self.config()
        loss_only = evaluate(cfg, ZoneRiskSnapshot(realized_pnl="-10", mark_price="99"))
        self.assertEqual(loss_only.reason, "LOSS_BUDGET")
        price_only = evaluate(cfg, ZoneRiskSnapshot(mark_price="95"))
        self.assertEqual(price_only.reason, "PRICE_SL")
        both = evaluate(cfg, ZoneRiskSnapshot(realized_pnl="-10", mark_price="95"))
        self.assertEqual(both.reason, "BOTH")

    def test_at_least_one_option_required(self):
        with self.assertRaises(ValueError):
            self.config(zone_loss_limit_usdt=None, sl_pct=None)
        with self.assertRaises(ValueError):
            self.config(sl_pct=0)

    def test_ref_price_does_not_change_with_dca_or_mark(self):
        cfg = self.config()
        evaluate(cfg, ZoneRiskSnapshot(mark_price="80"))
        self.assertEqual(cfg.ref_price, Decimal("100"))
        self.assertEqual(cfg.price_stop, Decimal("95.00"))

    def test_stop_is_requested_once_and_ledger_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "events.jsonl")
            ledger = AppendOnlyLedger(path)
            zone = ZoneState(self.config())
            requests = []
            stop = lambda reason: requests.append(reason)
            process_snapshot(zone, ZoneRiskSnapshot(mark_price="95"), ledger, stop)
            process_snapshot(zone, ZoneRiskSnapshot(mark_price="90"), ledger, stop)
            self.assertEqual(zone.status, STOPPING)
            self.assertEqual(requests, ["PRICE_SL"])
            with open(path, encoding="utf-8") as stream:
                events = [json.loads(line)["event"] for line in stream]
            self.assertEqual(events.count("ZONE_STOP_REQUESTED_DRY_RUN"), 1)
            self.assertEqual(events.count("RISK_EVALUATED"), 2)

    def test_stop_callback_error_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = ZoneState(self.config())
            process_snapshot(
                zone,
                ZoneRiskSnapshot(mark_price="95"),
                AppendOnlyLedger(os.path.join(tmp, "events.jsonl")),
                lambda _: (_ for _ in ()).throw(TimeoutError()),
            )
            self.assertEqual(zone.status, UNKNOWN)

    def test_only_reconciled_zero_size_can_close_zone(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = ZoneState(self.config(), status=STOPPING, last_trigger_reason="PRICE_SL")
            ledger = AppendOnlyLedger(os.path.join(tmp, "events.jsonl"))
            with self.assertRaises(ValueError):
                mark_closed(zone, Decimal("0.1"), ledger)
            mark_closed(zone, Decimal("0"), ledger)
            self.assertEqual(zone.status, CLOSED)

    def test_unknown_blocks_return_to_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = ZoneState(self.config())
            record_unknown(zone, AppendOnlyLedger(os.path.join(tmp, "events.jsonl")), "reconcile_timeout")
            self.assertEqual(zone.status, UNKNOWN)
            result = process_snapshot(
                zone,
                ZoneRiskSnapshot(mark_price="95"),
                AppendOnlyLedger(os.path.join(tmp, "events.jsonl")),
                lambda _: self.fail("unknown zone must not request a new stop"),
            )
            self.assertTrue(result.triggered)
            self.assertEqual(zone.status, UNKNOWN)


if __name__ == "__main__":
    unittest.main()
