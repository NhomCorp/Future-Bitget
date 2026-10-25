"""Local CLI for profile/user_style.yaml.

Examples:
  python -m trader.style_cli list
  python -m trader.style_cli add --file draft.json
  python -m trader.style_cli retire --id fade-1h-mean-revert

Append-only. Never edits or deletes an old entry. Preferences are not hard
limits. Frontend local spawns this module; Node does not rewrite the YAML.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from trading.style_load import DEFAULT_PATH, append_style_entry, list_style_entries


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local user-style YAML CLI")
    parser.add_argument("--path", default=str(DEFAULT_PATH), help="YAML path")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="list latest version per id")
    add = sub.add_parser("add", help="append a new entry or a new version")
    add.add_argument("--file", required=True, help="JSON draft")
    retire = sub.add_parser("retire", help="append a retired version")
    retire.add_argument("--id", required=True, help="existing style id")
    return parser


def _print(payload: Mapping[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def run(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    target = Path(args.path)
    if args.command == "list":
        packed = list_style_entries(target)
        _print(packed)
        return 0 if packed.get("ok") else 2
    if args.command == "add":
        try:
            draft = json.loads(Path(args.file).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            _print({"ok": False, "error": "draft json không đọc được"})
            return 2
        if not isinstance(draft, Mapping):
            _print({"ok": False, "error": "draft json không hợp lệ"})
            return 2
        packed = append_style_entry(draft, path=target, action="add")
        _print(packed)
        return 0 if packed.get("ok") else 2
    if args.command == "retire":
        packed = append_style_entry({"id": args.id}, path=target, action="retire")
        _print(packed)
        return 0 if packed.get("ok") else 2
    return 2


if __name__ == "__main__":
    raise SystemExit(run())
