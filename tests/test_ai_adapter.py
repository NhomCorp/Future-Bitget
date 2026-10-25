"""Offline tests for the Demo-scan AI adapter. No live provider calls."""
from __future__ import annotations

from decimal import Decimal
from unittest import TestCase

from ai_proposal.adapter import (
    ProviderConfig,
    ProviderError,
    extract_json_object,
    is_allowed_openai_url,
    parse_decision,
    snapshot_with_size,
)
from ai_proposal.schema import DecisionOpportunitySnapshot, HardLimits
from ai_proposal.validator import evaluate_proposal


NOW = "2026-10-23T15:00:00Z"


def make_snapshot(**overrides):
    values = dict(
        opportunity_id="opp-ai-1",
        snapshot_at=NOW,
        feature_as_of=NOW,
        symbol="BTCUSDT",
        side="long",
        state="READY",
        ref_price=Decimal("100"),
        sl_pct=Decimal("2"),
        loss_budget=Decimal("20"),
        size=Decimal("0"),
        exposure=Decimal("0"),
        hard_limits=HardLimits(
            allowed_symbols=("BTCUSDT",),
            allowed_sides=("long", "short"),
            allowed_states=("READY",),
            max_size=Decimal("0.01"),
            max_exposure=Decimal("1000"),
        ),
    )
    values.update(overrides)
    return DecisionOpportunitySnapshot(**values)


class ProviderConfigTests(TestCase):
    def test_rejects_private_openai_url(self):
        self.assertFalse(is_allowed_openai_url("http://127.0.0.1/v1"))
        self.assertFalse(is_allowed_openai_url("https://127.0.0.1/v1"))
        self.assertFalse(is_allowed_openai_url("https://192.168.1.10/v1"))
        self.assertFalse(is_allowed_openai_url("https://example.internal/v1"))
        self.assertFalse(is_allowed_openai_url("https://api.openai.com:8443/v1"))
        self.assertTrue(is_allowed_openai_url("https://api.openai.com/v1"))
        self.assertTrue(is_allowed_openai_url("https://api.xpiki.com/v1"))
        self.assertTrue(is_allowed_openai_url("https://example.com/v1"))
        with self.assertRaises(ProviderError) as caught:
            ProviderConfig.from_mapping(
                {
                    "provider": "openai_compatible",
                    "model": "gpt-4o-mini",
                    "api_key": "sk-test",
                    "base_url": "http://127.0.0.1/v1",
                }
            )
        self.assertEqual(caught.exception.code, "BASE_URL_NOT_ALLOWED")

    def test_repr_hides_key(self):
        config = ProviderConfig.from_mapping(
            {
                "provider": "gemini",
                "model": "gemini-2.0-flash",
                "api_key": "secret-key-value",
                "label": "main",
            }
        )
        self.assertNotIn("secret-key-value", repr(config))


class ParseDecisionTests(TestCase):
    def test_open_binds_size_then_passes_validator(self):
        snap = make_snapshot()
        bound, draft = parse_decision(
            snap,
            {
                "action": "OPEN",
                "quantity": "0.001",
                "order_type": "LIMIT",
                "rationale": "enter small long",
            },
            model_version="gemini-2.0-flash",
            policy_version="policy-3",
            now=NOW,
            leverage="5",
        )
        self.assertEqual(bound.size, Decimal("0.001"))
        self.assertEqual(draft.action, "OPEN")
        self.assertEqual(draft.size, Decimal("0.001"))
        self.assertEqual(draft.metadata["stop_loss"], "98")
        record = evaluate_proposal(bound, draft)
        self.assertEqual(record.result, "ACCEPTED")

    def test_open_short_alias_rejected_on_long_snapshot(self):
        with self.assertRaises(ProviderError) as caught:
            parse_decision(
                make_snapshot(),
                {"action": "OPEN_SHORT", "quantity": "0.001", "rationale": "short"},
                model_version="m",
                policy_version="p",
                now=NOW,
                leverage="5",
            )
        self.assertEqual(caught.exception.code, "SIDE_MISMATCH")

    def test_expired_valid_until_is_no_trade_error(self):
        with self.assertRaises(ProviderError) as caught:
            parse_decision(
                make_snapshot(),
                {
                    "action": "NO_TRADE",
                    "rationale": "stale",
                    "valid_until": "2026-10-23T14:00:00Z",
                },
                model_version="m",
                policy_version="p",
                now=NOW,
                leverage="5",
            )
        self.assertEqual(caught.exception.code, "DECISION_EXPIRED")

    def test_json_fence_is_stripped(self):
        payload = extract_json_object("```json\n{\"action\": \"NO_TRADE\"}\n```")
        self.assertEqual(payload["action"], "NO_TRADE")

    def test_open_market_is_rejected(self):
        with self.assertRaises(ProviderError) as caught:
            parse_decision(
                make_snapshot(),
                {
                    "action": "OPEN",
                    "quantity": "0.001",
                    "order_type": "MARKET",
                    "rationale": "chase",
                },
                model_version="m",
                policy_version="p",
                now=NOW,
                leverage="5",
            )
        self.assertEqual(caught.exception.code, "OPEN_REQUIRES_LIMIT")

    def test_close_without_size_is_rejected(self):
        with self.assertRaises(ProviderError) as caught:
            parse_decision(
                make_snapshot(),
                {"action": "CLOSE", "rationale": "exit"},
                model_version="m",
                policy_version="p",
                now=NOW,
                leverage="5",
            )
        self.assertEqual(caught.exception.code, "POSITION_SIZE_REQUIRED")

    def test_snapshot_with_size_keeps_symbol(self):
        bound = snapshot_with_size(make_snapshot(), Decimal("0.002"))
        self.assertEqual(bound.symbol, "BTCUSDT")
        self.assertEqual(bound.exposure, Decimal("0.2"))
