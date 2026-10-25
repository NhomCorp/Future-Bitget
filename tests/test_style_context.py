"""Offline tests for user-style load, TA brief, and Demo AI prompt context."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from ai_proposal.adapter import build_prompt
from tests.test_ai_adapter import make_snapshot
from trader.ta_brief import build_ta_brief, candles_to_arrays, compact_analysis
from trading.decision_context import enrich_decision_features

from trading.style_load import (
    DEFAULT_PATH,
    append_style_entry,
    list_style_entries,
    load_user_style,
    merge_active_entries,
    parse_style_yaml,
)
from trader.style_cli import run as run_style_cli


SAMPLE = """
entries:
  - id: "fade-1h-mean-revert"
    version: 1
    kind: "preference"
    source: "user"
    channel: "mcp_chat"
    status: "active"
    effective_from: "2026-10-23T00:00:00+07:00"
    effective_to: null
    scope: ["all"]
    priority: 90
    rule: "Fade the prior 1h move."
    tags: ["entry"]
  - id: "fade-1h-mean-revert"
    version: 2
    kind: "preference"
    source: "user"
    channel: "mcp_chat"
    status: "active"
    effective_from: "2026-10-23T12:00:00+07:00"
    effective_to: null
    scope: ["all"]
    priority: 90
    rule: "Fade 1h, do not chase trend."
    tags: ["entry"]
  - id: "bad-leverage"
    version: 1
    kind: "preference"
    source: "user"
    channel: "manual"
    status: "active"
    effective_from: "2026-10-23T00:00:00+07:00"
    effective_to: null
    scope: ["all"]
    priority: 10
    rule: "Use high leverage always."
    tags: []
"""


class StyleLoadTests(TestCase):
    def test_real_yaml_has_active_preferences(self):
        packed = load_user_style(DEFAULT_PATH, now="2026-10-23T17:00:00Z")
        self.assertEqual(packed["status"], "ok")
        ids = [row["id"] for row in packed["rules"]]
        self.assertIn("fade-1h-mean-revert", ids)
        self.assertIn("prefer-limit-maker", ids)
        self.assertTrue(all(row["kind"] in {"preference", "note", "no_trade"} for row in packed["rules"]))

    def test_merge_keeps_latest_version_and_skips_hard_limits(self):
        entries = parse_style_yaml(SAMPLE)
        rules = merge_active_entries(
            entries,
            now=datetime(2026, 10, 23, 17, tzinfo=timezone.utc),
        )
        by_id = {row["id"]: row["rule"] for row in rules}
        self.assertEqual(by_id["fade-1h-mean-revert"], "Fade 1h, do not chase trend.")
        self.assertNotIn("bad-leverage", by_id)


class StyleWriteTests(TestCase):
    def test_append_new_version_and_reject_hard_limit(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "user_style.yaml"
            first = append_style_entry(
                {
                    "id": "prefer-limit-maker",
                    "kind": "preference",
                    "rule": "Prefer limit maker entries.",
                    "priority": 70,
                    "scope": "all",
                    "tags": "limit",
                },
                path=path,
                now="2026-10-24T00:00:00+07:00",
            )
            self.assertTrue(first["ok"])
            self.assertEqual(first["saved"]["version"], 1)
            second = append_style_entry(
                {
                    "id": "prefer-limit-maker",
                    "kind": "preference",
                    "rule": "Prefer limit; market only to flatten.",
                    "priority": 80,
                    "scope": "all",
                    "tags": "limit,maker",
                },
                path=path,
                now="2026-10-24T01:00:00+07:00",
            )
            self.assertTrue(second["ok"])
            self.assertEqual(second["saved"]["version"], 2)
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("id: \"prefer-limit-maker\""), 2)
            listed = list_style_entries(path, now="2026-10-24T02:00:00+07:00")
            self.assertEqual(listed["entries"][0]["rule"], "Prefer limit; market only to flatten.")
            blocked = append_style_entry(
                {
                    "id": "use-high-leverage",
                    "kind": "preference",
                    "rule": "Use high leverage always.",
                    "priority": 10,
                },
                path=path,
            )
            self.assertFalse(blocked["ok"])
            self.assertIn("hạn mức", blocked["error"])
            self.assertNotIn("Use high leverage always.", path.read_text(encoding="utf-8"))

    def test_retire_appends_and_cli_lists(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "user_style.yaml"
            append_style_entry(
                {
                    "id": "fade-1h",
                    "kind": "preference",
                    "rule": "Fade the prior 1h move.",
                    "priority": 90,
                },
                path=path,
                now="2026-10-24T00:00:00+07:00",
            )
            retired = append_style_entry(
                {"id": "fade-1h"},
                path=path,
                action="retire",
                now="2026-10-24T03:00:00+07:00",
            )
            self.assertTrue(retired["ok"])
            self.assertEqual(retired["saved"]["status"], "retired")
            listed = list_style_entries(path, now="2026-10-24T04:00:00+07:00")
            self.assertEqual(listed["count"], 0)
            self.assertEqual(listed["entries"][0]["status"], "retired")
            with patch("sys.stdout", new=StringIO()):
                self.assertEqual(run_style_cli(["--path", str(path), "retire", "--id", "missing-id"]), 2)


class TaBriefTests(TestCase):
    def test_short_rows_are_unavailable(self):
        self.assertIsNone(candles_to_arrays([[1, 1, 1, 1, 1, 1]]))

    def test_compact_analysis_keeps_side_risk(self):
        packed = compact_analysis(
            {
                "disclaimer": "filter",
                "regime": "range",
                "mtf_score": 0.2,
                "changes": {"ch_1h": -0.18},
                "risk": {"long": {"flag": "AVOID", "reasons": ["shock", "trend"]}},
                "tf": {"1h": {"adx": 18.2, "bias": "giảm", "rsi": 45.1, "structure": "LH/LL (giảm)"}},
                "levels": [{"type": "support", "price": 100.5, "strength": 2}],
            },
            "long",
        )
        self.assertEqual(packed["status"], "ok")
        self.assertEqual(packed["risk_side"], "AVOID")
        self.assertEqual(packed["tf"]["1h"]["bias"], "giảm")

    def test_missing_adapter_is_unavailable(self):
        brief = build_ta_brief("BTCUSDT", "long", adapter=None)
        self.assertEqual(brief["status"], "unavailable")


class DecisionContextTests(TestCase):
    def test_enrich_attaches_style_and_skips_ta_without_candles(self):
        features = enrich_decision_features({}, symbol="BTCUSDT", side="long", now="2026-10-23T17:00:00Z")
        self.assertEqual(features["user_style"]["status"], "ok")
        self.assertEqual(features["ta"]["status"], "unavailable")

    def test_prompt_includes_style_and_ta_instructions(self):
        snap = make_snapshot(
            features={
                "user_style": {
                    "status": "ok",
                    "rules": [{"id": "fade-1h-mean-revert", "kind": "preference", "rule": "Fade 1h"}],
                },
                "ta": {"status": "ok", "risk_side": "OK", "regime": "range"},
            }
        )
        prompt = build_prompt(snap, max_leverage="5")
        self.assertIn("fade-1h-mean-revert", prompt)
        self.assertIn("risk filter", prompt.lower())
        self.assertNotIn("secret", prompt)
        self.assertEqual(snap.features["ta"]["risk_side"], "OK")
        self.assertIsInstance(snap.ref_price, Decimal)
