"""Offline checks for the Phong cách page and local style API."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
SERVER = (ROOT / "frontend" / "server.js").read_text(encoding="utf-8")


class FrontendStyleTests(unittest.TestCase):
    def test_style_page_is_not_a_stub(self):
        self.assertIn('id="style-form"', INDEX)
        self.assertIn('id="style-list"', INDEX)
        self.assertIn('id="style-refresh"', INDEX)
        self.assertNotIn("Form YAML theo spec phong cách người dùng", INDEX)
        platform = INDEX.split("Nền tảng")[1].split("Hạn mức")[0]
        self.assertIn('data-view="phong-cach"', platform)

    def test_style_api_is_local_yaml_only(self):
        self.assertIn('"/api/user-style"', SERVER)
        self.assertIn("trader.style_cli", SERVER)
        self.assertIn("handleUserStyle", SERVER)
        handler = SERVER.split("async function handleUserStyle")[1].split("function publicDemoScan")[0]
        self.assertNotIn("GROK_TRADER_ALLOW_LIVE", handler)
        self.assertIn("loadUserStyle", APP)
        self.assertIn("postUserStyle", APP)
        self.assertNotIn("localStorage", APP.split("function postUserStyle")[1].split("function render()")[0])

    def test_style_form_rejects_hard_limits(self):
        self.assertIn("STYLE_FORBIDDEN", APP)
        self.assertIn("leverage", APP.split("const STYLE_FORBIDDEN")[1].split(";")[0])
        self.assertIn("margin", APP.split("const STYLE_FORBIDDEN")[1].split(";")[0])
        self.assertIn("no_trade", INDEX)
        self.assertIn("profile/user_style.yaml", INDEX)


if __name__ == "__main__":
    unittest.main()
