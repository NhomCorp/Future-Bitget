from __future__ import annotations

import unittest
from decimal import Decimal

from ai_proposal.schema import DecisionOpportunitySnapshot, HardLimits, ProposalDraft
from trading.mandate import (
    MandateError,
    POSITION_REVIEW_INTERVAL_MAX,
    POSITION_REVIEW_INTERVAL_MIN,
    POSITION_REVIEW_INTERVAL_SUGGESTIONS,
    TradingMandate,
)
from trading.risk_engine import evaluate_decision


NOW = "2026-10-21T10:00:00Z"


def make_snapshot(**features):
    return DecisionOpportunitySnapshot(
        opportunity_id="opp-policy-1",
        snapshot_at=NOW,
        feature_as_of=NOW,
        symbol="BTCUSDT",
        side="long",
        state="READY",
        ref_price=Decimal("100"),
        sl_pct=Decimal("5"),
        loss_budget=Decimal("20"),
        size=Decimal("1"),
        exposure=Decimal("100"),
        hard_limits=HardLimits(
            allowed_symbols=("BTCUSDT", "ETHUSDT"),
            allowed_sides=("long", "short"),
            allowed_states=("READY",),
            max_size=Decimal("2"),
            max_exposure=Decimal("200"),
        ),
        features={"daily_loss": "0", "day_start_equity": "1000", "daily_loss_at": NOW, "drawdown": "0", "drawdown_unit": "usdt", "consecutive_losses": "0", **features},
    )


def make_proposal(snapshot, action="OPEN", **metadata):
    return ProposalDraft(
        proposal_id="decision-policy-1",
        opportunity_id=snapshot.opportunity_id,
        decision_timestamp=NOW,
        feature_as_of=snapshot.feature_as_of,
        model_version="fake-1",
        policy_version="policy-1",
        action=action,
        rationale="policy test",
        symbol=snapshot.symbol,
        side=snapshot.side,
        state=snapshot.state,
        ref_price=snapshot.ref_price,
        sl_pct=snapshot.sl_pct,
        loss_budget=snapshot.loss_budget,
        size=snapshot.size,
        exposure=snapshot.exposure,
        metadata={"stop_loss": "95", "leverage": "2", **metadata},
    )


def make_mandate(**overrides):
    values = dict(
        mandate_id="mandate-policy-1",
        version=1,
        zone_id="zone-policy",
        allowed_symbols=("BTCUSDT",),
        allowed_sides=("long",),
        allowed_actions=("OPEN", "CLOSE", "REDUCE", "NO_TRADE"),
        max_size=Decimal("1"),
        max_exposure=Decimal("100"),
        loss_budget=Decimal("20"),
        max_order_risk=Decimal("5"),
        valid_from="2026-10-21T09:00:00Z",
        valid_until="2026-10-21T11:00:00Z",
        daily_loss_limit_pct=Decimal("1"),
        daily_loss_reference="day_start_equity",
        daily_loss_reset_time_utc="00:00",
        drawdown_limit=Decimal("20"),
        drawdown_unit="usdt",
        max_leverage=Decimal("3"),
        daily_loss_scope="subaccount",
        drawdown_scope="subaccount",
        drawdown_reference="equity_peak",
        ai_autonomy="MANAGED_ZONE",
        granted_capital=Decimal("1000"),
        capital_currency="USDT",
        daily_loss_action="FREEZE_ENTRY",
        max_consecutive_losses=3,
        loss_streak_scope="subaccount",
        loss_streak_cooldown="24h",
        allow_average_down=False,
        position_review_interval=15,
    )
    values.update(overrides)
    return TradingMandate(**values)


class PolicyRiskTests(unittest.TestCase):
    def test_incomplete_policy_is_paused(self):
        snapshot = make_snapshot()
        mandate = make_mandate(daily_loss_limit_pct=None, daily_loss_limit=None)
        result = evaluate_decision(snapshot, make_proposal(snapshot), mandate, now=NOW)
        self.assertEqual(result.risk_check.result, "PAUSED")
        self.assertIn("POLICY_INCOMPLETE", result.risk_check.reason_codes)

    def test_daily_loss_and_drawdown_are_hard_limits(self):
        snapshot = make_snapshot(daily_loss="10", drawdown="20")
        result = evaluate_decision(snapshot, make_proposal(snapshot), make_mandate(), now=NOW)
        self.assertEqual(result.risk_check.result, "REJECTED")
        self.assertIn("DAILY_LOSS_LIMIT", result.risk_check.reason_codes)
        self.assertIn("DRAWDOWN_LIMIT", result.risk_check.reason_codes)

    def test_daily_loss_uses_percent_of_day_start_equity(self):
        snapshot = make_snapshot(daily_loss="9.99", day_start_equity="1000")
        result = evaluate_decision(snapshot, make_proposal(snapshot), make_mandate(), now=NOW)
        self.assertEqual(result.risk_check.result, "APPROVED")
        snapshot = make_snapshot(daily_loss="10", day_start_equity="1000")
        result = evaluate_decision(snapshot, make_proposal(snapshot), make_mandate(), now=NOW)
        self.assertIn("DAILY_LOSS_LIMIT", result.risk_check.reason_codes)

    def test_stale_daily_loss_context_pauses(self):
        snapshot = make_snapshot(daily_loss_at="2026-10-20T23:59:00Z")
        result = evaluate_decision(snapshot, make_proposal(snapshot), make_mandate(), now=NOW)
        self.assertEqual(result.risk_check.result, "PAUSED")
        self.assertIn("DAILY_LOSS_CONTEXT_STALE", result.risk_check.reason_codes)

    def test_drawdown_percent_uses_day_start_equity(self):
        snapshot = make_snapshot(drawdown="9.99", drawdown_unit="pct")
        mandate = make_mandate(drawdown_limit=Decimal("10"), drawdown_unit="pct")
        result = evaluate_decision(snapshot, make_proposal(snapshot), mandate, now=NOW)
        self.assertEqual(result.risk_check.result, "APPROVED")
        snapshot = make_snapshot(drawdown="10", drawdown_unit="pct")
        result = evaluate_decision(snapshot, make_proposal(snapshot), mandate, now=NOW)
        self.assertIn("DRAWDOWN_LIMIT", result.risk_check.reason_codes)

    def test_policy_serialization_round_trip(self):
        mandate = make_mandate()
        restored = TradingMandate.from_dict(mandate.to_dict())
        self.assertEqual(restored, mandate)

    def test_market_entry_is_rejected(self):
        snapshot = make_snapshot()
        proposal = make_proposal(snapshot, order_type="market", reduce_only=True)
        result = evaluate_decision(snapshot, proposal, make_mandate(), now=NOW)
        self.assertIn("ENTRY_ORDER_TYPE_NOT_ALLOWED", result.risk_check.reason_codes)

    def test_market_must_be_reduce_only_exit_role(self):
        snapshot = make_snapshot()
        proposal = make_proposal(snapshot, order_type="market", order_role="entry", reduce_only=False)
        result = evaluate_decision(snapshot, proposal, make_mandate(), now=NOW)
        self.assertIn("MARKET_REDUCE_ONLY_REQUIRED", result.risk_check.reason_codes)

    def test_missing_granted_capital_is_paused(self):
        snapshot = make_snapshot()
        mandate = make_mandate(granted_capital=None)
        result = evaluate_decision(snapshot, make_proposal(snapshot), mandate, now=NOW)
        self.assertEqual(result.risk_check.result, "PAUSED")
        self.assertIn("POLICY_INCOMPLETE", result.risk_check.reason_codes)

    def test_autonomous_open_is_approved_when_limits_pass(self):
        snapshot = make_snapshot()
        mandate = make_mandate(ai_autonomy="AUTONOMOUS_WITHIN_MANDATE")
        result = evaluate_decision(snapshot, make_proposal(snapshot), mandate, now=NOW)
        self.assertEqual(result.risk_check.result, "APPROVED")
        self.assertNotIn("AUTONOMY_NOT_ENABLED", result.risk_check.reason_codes)

    def test_adjust_sl_tighten_is_approved(self):
        snapshot = make_snapshot(current_stop_loss="95")
        mandate = make_mandate(allowed_actions=("OPEN", "CLOSE", "REDUCE", "ADJUST_SL", "NO_TRADE"))
        proposal = make_proposal(snapshot, action="ADJUST_SL", stop_loss="96", leverage="2")
        result = evaluate_decision(snapshot, proposal, mandate, now=NOW)
        self.assertEqual(result.risk_check.result, "APPROVED")

    def test_adjust_sl_widen_within_budget_is_approved(self):
        snapshot = make_snapshot(current_stop_loss="96")
        mandate = make_mandate(allowed_actions=("OPEN", "CLOSE", "REDUCE", "ADJUST_SL", "NO_TRADE"))
        proposal = make_proposal(snapshot, action="ADJUST_SL", stop_loss="95", leverage="2")
        result = evaluate_decision(snapshot, proposal, mandate, now=NOW)
        self.assertEqual(result.risk_check.result, "APPROVED")

    def test_adjust_sl_widen_over_order_risk_is_rejected(self):
        snapshot = make_snapshot(current_stop_loss="95")
        mandate = make_mandate(allowed_actions=("OPEN", "CLOSE", "REDUCE", "ADJUST_SL", "NO_TRADE"))
        proposal = make_proposal(snapshot, action="ADJUST_SL", stop_loss="90", leverage="2")
        result = evaluate_decision(snapshot, proposal, mandate, now=NOW)
        self.assertEqual(result.risk_check.result, "REJECTED")
        self.assertIn("ORDER_RISK_LIMIT", result.risk_check.reason_codes)

    def test_average_down_is_disabled_by_default(self):
        snapshot = make_snapshot()
        proposal = make_proposal(snapshot, order_role="dca")
        result = evaluate_decision(snapshot, proposal, make_mandate(), now=NOW)
        self.assertIn("AVERAGE_DOWN_DISABLED", result.risk_check.reason_codes)

    def test_close_is_allowed_when_daily_loss_is_hit(self):
        snapshot = make_snapshot(daily_loss="10")
        proposal = make_proposal(snapshot, action="CLOSE", order_role="reduce", reduce_only=True)
        result = evaluate_decision(snapshot, proposal, make_mandate(), now=NOW)
        self.assertEqual(result.risk_check.result, "APPROVED")
        self.assertNotIn("DAILY_LOSS_LIMIT", result.risk_check.reason_codes)

    def test_loss_streak_pauses_open(self):
        snapshot = make_snapshot(consecutive_losses="3")
        result = evaluate_decision(snapshot, make_proposal(snapshot), make_mandate(), now=NOW)
        self.assertEqual(result.risk_check.result, "PAUSED")
        self.assertIn("LOSS_STREAK_LIMIT", result.risk_check.reason_codes)

    def test_missing_review_interval_is_paused(self):
        snapshot = make_snapshot()
        mandate = make_mandate(position_review_interval=None)
        result = evaluate_decision(snapshot, make_proposal(snapshot), mandate, now=NOW)
        self.assertEqual(result.risk_check.result, "PAUSED")
        self.assertIn("POLICY_INCOMPLETE", result.risk_check.reason_codes)
        self.assertIn("position_review_interval", mandate.missing_policy_fields())

    def test_review_interval_must_be_integer_minutes(self):
        with self.assertRaises(MandateError):
            make_mandate(position_review_interval=15.5)
        with self.assertRaises(MandateError):
            make_mandate(position_review_interval=True)
        with self.assertRaises(MandateError):
            make_mandate(position_review_interval=POSITION_REVIEW_INTERVAL_MIN - 1)
        with self.assertRaises(MandateError):
            make_mandate(position_review_interval=POSITION_REVIEW_INTERVAL_MAX + 1)

    def test_review_interval_suggestions_are_valid_and_not_defaults(self):
        self.assertEqual(POSITION_REVIEW_INTERVAL_SUGGESTIONS, (5, 15, 30, 60))
        for minutes in POSITION_REVIEW_INTERVAL_SUGGESTIONS:
            mandate = make_mandate(position_review_interval=minutes)
            self.assertEqual(mandate.position_review_interval, minutes)
            self.assertTrue(mandate.policy_complete())
        restored = TradingMandate.from_dict(make_mandate().to_dict())
        self.assertEqual(restored.position_review_interval, 15)
        legacy = TradingMandate.from_dict(
            {key: value for key, value in make_mandate().to_dict().items() if key != "position_review_interval"}
        )
        self.assertIsNone(legacy.position_review_interval)
        self.assertFalse(legacy.policy_complete())


if __name__ == "__main__":
    unittest.main()
