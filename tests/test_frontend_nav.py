"""Offline checks for frontend sidenav grouping and default hash."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")


class FrontendNavTests(unittest.TestCase):
    def test_nav_groups_follow_unlock_order(self):
        labels = re.findall(r'class="nav-group-label">([^<]+)', INDEX)
        self.assertEqual(labels, ["Vận hành", "Nền tảng", "Hạn mức", "Chưa làm"])
        views = re.findall(r'data-view="([^"]+)"', INDEX)
        self.assertEqual(
            views,
            [
                "tong-quan",
                "ban-zone",
                "ket-noi",
                "cau-hinh-ai",
                "phong-cach",
                "mandate",
                "de-xuat-cap",
                "quyen-ai",
                "nhat-ky",
            ],
        )

    def test_stubs_sit_in_later_group(self):
        later = re.search(
            r'nav-group nav-group-later">(.*?)</div>',
            INDEX,
            flags=re.S,
        )
        self.assertIsNotNone(later)
        stub_views = re.findall(r'data-view="([^"]+)"', later.group(1))
        self.assertEqual(stub_views, ["nhat-ky"])
        self.assertIn('class="nav-link is-stub"', INDEX)
        self.assertNotIn('data-view="phong-cach"', later.group(1))

    def test_checklist_is_local_only(self):
        metas = re.findall(r'data-nav-meta="([^"]+)"', INDEX)
        self.assertEqual(
            metas,
            ["ban-zone", "cau-hinh-ai", "phong-cach", "mandate", "de-xuat-cap", "quyen-ai"],
        )
        self.assertIn("function navChecklist()", APP)
        self.assertNotIn("loadConnectStatus()", APP.split("function navChecklist()")[1].split("function renderNav")[0])
        self.assertIn("const NAV_AUTONOMY", APP)

    def test_default_view_is_overview(self):
        self.assertIn("const DEFAULT_VIEW = 'tong-quan';", APP)
        self.assertRegex(APP, r"if \(!window\.location\.hash\) window\.location\.hash = `#/\$\{DEFAULT_VIEW\}`;")

    def test_overview_highlights_account_metrics(self):
        self.assertIn('id="overview-metrics"', INDEX)
        self.assertIn('id="overview-equity"', INDEX)
        self.assertIn('id="overview-available"', INDEX)
        self.assertIn('id="overview-upnl"', INDEX)
        self.assertIn('id="overview-positions-count"', INDEX)
        self.assertIn('id="overview-orders-count"', INDEX)
        self.assertIn('id="overview-fills-count"', INDEX)
        self.assertLess(INDEX.find('id="overview-metrics"'), INDEX.find('id="book-heading"'))
        self.assertLess(INDEX.find('id="book-heading"'), INDEX.find('class="overview-ops"'))
        self.assertIn("Lịch sử", INDEX)
        self.assertIn("renderAccountMetrics", APP)
        self.assertIn("snapshotUnrealized", APP)
        self.assertNotIn("day_start_equity", APP.split("function renderAccountMetrics")[1].split("function ")[0])

    def test_overview_has_demo_kill(self):
        self.assertIn('id="demo-kill-form"', INDEX)
        self.assertIn("/api/demo-kill", (ROOT / "frontend" / "server.js").read_text(encoding="utf-8"))
        self.assertIn("runDemoKill", APP)

    def test_overview_tick_can_call_ai(self):
        self.assertNotIn('id="demo-scan-use-ai"', INDEX)
        self.assertIn("--agent-config", (ROOT / "frontend" / "server.js").read_text(encoding="utf-8"))
        self.assertIn("hasDemoAgent", APP)
        self.assertIn("policyTradeLimits", APP)

    def test_overview_cycle_has_run_stop_without_fake_equity(self):
        self.assertIn('id="demo-cycle-run"', INDEX)
        self.assertIn('id="demo-cycle-stop"', INDEX)
        self.assertIn("Dự phòng 2", INDEX)
        self.assertNotIn('id="demo-scan-side"', INDEX)
        self.assertNotIn('id="demo-scan-confirm"', INDEX)
        self.assertIn("scope: 'allowlist'", APP)
        self.assertNotIn("demo-scan-submit", INDEX)
        self.assertNotIn("Chạy 1 chu kỳ", INDEX)
        self.assertNotIn("demo-scan-use-equity", INDEX)
        self.assertNotIn("demoScanUseEquity", APP)
        self.assertNotIn('id="intent-form"', INDEX)
        self.assertNotIn('id="demo-scan-place"', INDEX)
        self.assertNotIn('id="demo-kill-place"', INDEX)
        self.assertIn('name="sl_pct"', INDEX)
        self.assertIn('name="zone_loss_limit_usdt"', INDEX)
        self.assertIn('name="max_order_risk_usdt"', INDEX)
        self.assertIn('name="max_size"', INDEX)
        server = (ROOT / "frontend" / "server.js").read_text(encoding="utf-8")
        self.assertIn("/api/demo-cycle", server)
        self.assertIn('"cycle"', server)
        self.assertIn("DEMO_CYCLE_MS", APP)
        self.assertIn("stopDemoCycle", APP)

    def test_overview_polls_snapshot_get_only(self):
        self.assertIn("const SNAPSHOT_POLL_MS = 12000;", APP)
        self.assertIn("startSnapshotPoll", APP)
        self.assertIn("stopSnapshotPoll", APP)
        self.assertIn("document.hidden", APP)
        loader = APP.split("function loadBitgetSnapshot")[1].split("function renderOverview")[0]
        self.assertIn("method: 'GET'", loader)
        self.assertNotIn("POST", loader)
        self.assertNotIn("/api/demo-cycle", loader)
        self.assertNotIn("/api/demo-scan", loader)
        self.assertNotIn("/api/demo-kill", loader)


if __name__ == "__main__":
    unittest.main()
