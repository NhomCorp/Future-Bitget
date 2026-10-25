"""Local GET-only CLI for USDT-M pair screening.

Examples:
  python -m trader.pair_screen_cli screen
  python -m trader.pair_screen_cli screen --limit 12

Public tickers only. Never dumps raw Bitget payloads, credentials or signed
headers, never approves a whitelist, and never creates paper or exchange
intents. Frontend local spawns this module; Node does not sign Bitget requests.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any, Mapping

from trader.bitget_readonly import (
    BitgetAdapterError,
    LiveModeDisabled,
    ReadOnlyBitgetAdapter,
)
from trader.envfile import load_os_env_file
from trading.pair_screen import (
    CANDIDATE_LIMIT_DEFAULT,
    CANDIDATE_LIMIT_MAX,
    clamp_candidate_limit,
    rank_pair_candidates,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only USDT-M pair screen CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    screen = sub.add_parser("screen", help="GET public USDT-M tickers and rank by 24h volume")
    screen.add_argument(
        "--limit",
        type=int,
        default=CANDIDATE_LIMIT_DEFAULT,
        help=f"max candidates, 1-{CANDIDATE_LIMIT_MAX} (default {CANDIDATE_LIMIT_DEFAULT})",
    )
    return parser


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _live_guard_on(environ: Mapping[str, str] | None) -> bool:
    env = os.environ if environ is None else environ
    return str(env.get("GROK_TRADER_ALLOW_LIVE", "")).strip() == "1"


def build_pair_screen(tickers: Any, *, limit: int = CANDIDATE_LIMIT_DEFAULT) -> dict[str, Any]:
    return {
        "ok": True,
        "as_of": _now_utc(),
        "product_type": "USDT-FUTURES",
        "candidates": rank_pair_candidates(tickers, limit=limit),
    }


def _print_error(kind: str, message: str) -> None:
    print(json.dumps({"ok": False, "error": kind, "message": str(message)[:80]}, ensure_ascii=True, sort_keys=True))


def run(
    argv: list[str] | None = None,
    *,
    adapter: Any | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    args = _parser().parse_args(argv)
    if args.command != "screen":
        return 2
    limit = clamp_candidate_limit(args.limit)
    try:
        if adapter is None:
            if environ is None:
                load_os_env_file()
            env = os.environ if environ is None else environ
            if _live_guard_on(env):
                raise LiveModeDisabled("GROK_TRADER_ALLOW_LIVE is on; pair screen GET is Demo-only")
            client: Any = ReadOnlyBitgetAdapter(demo=True, environ=env if environ is not None else None)
        else:
            client = adapter
        raw = client.public_tickers()
        print(json.dumps(build_pair_screen(raw, limit=limit), ensure_ascii=True, sort_keys=True))
        return 0
    except (LiveModeDisabled, BitgetAdapterError, ValueError, OSError) as exc:
        _print_error(type(exc).__name__, str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
