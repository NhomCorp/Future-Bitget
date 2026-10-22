from __future__ import annotations

import os
import tempfile
import unittest

from trader.envfile import load_env_file, parse_env_file


class EnvFileTests(unittest.TestCase):
    def test_parse_skips_comments_and_quotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, ".env")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("# comment\nBITGET_ENV=demo\nBITGET_API_KEY='abc'\nEMPTY=\n")
            parsed = parse_env_file(path)
            self.assertEqual(parsed["BITGET_ENV"], "demo")
            self.assertEqual(parsed["BITGET_API_KEY"], "abc")
            self.assertEqual(parsed["EMPTY"], "")

    def test_load_does_not_override_existing_and_does_not_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, ".env")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("BITGET_API_KEY=file-secret\nBITGET_ENV=demo\n")
            env = {"BITGET_API_KEY": "already-set"}
            loaded = load_env_file(path, environ=env)
            self.assertEqual(loaded, path)
            self.assertEqual(env["BITGET_API_KEY"], "already-set")
            self.assertEqual(env["BITGET_ENV"], "demo")
            self.assertNotIn("file-secret", repr(loaded))


if __name__ == "__main__":
    unittest.main()
