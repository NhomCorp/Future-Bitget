"""Flatten one Demo whitelist symbol: cancel pending, close positions.

Examples:
  python -m trader.demo_kill_cli run --symbol BTCUSDT --allowlist BTCUSDT --json
  python -m trader.demo_kill_cli run --symbol BTCUSDT --allowlist BTCUSDT --place-orders --i-confirm-demo --json

Default is dry-run. Live is refused. This CLI does not call PaperAgent.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from trader.bitget_readonly import LiveModeDisabled, MissingReadOnlyCredentials, ReadOnlyBitgetAdapter
from trading.demo_dispatch import (
    DemoDispatchError,
    kill_symbol,
    make_demo_poster,
    make_path_poster,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Demo kill/flatten; POST only with --place-orders --i-confirm-demo")
    parser.add_argument("command", choices=("run",))
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--allowlist", required=True, help="comma-separated whitelist symbols")
    parser.add_argument("--pos-mode", default="hedge_mode")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--place-orders", action="store_true")
    parser.add_argument("--i-confirm-demo", action="store_true")
    return parser


def _live_blocked(environ: Any | None = None) -> bool:
    env = os.environ if environ is None else environ
    mode = str(env.get("BITGET_ENV", "demo")).strip().lower()
    return str(env.get("GROK_TRADER_ALLOW_LIVE", "")).strip() == "1" or mode in {"live", "production", "prod"}


def _allowlist(raw: str) -> tuple[str, ...]:
    return tuple(part.strip().upper() for part in raw.split(",") if part.strip())


def _output(value: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str))
        return
    posted = " post=yes" if value.get("exchange_post") else ""
    print(
        f"symbol={value.get('symbol')} cancelled={value.get('cancelled')} "
        f"closed={value.get('closed')} leftover_clear={value.get('leftover_clear')} "
        f"reason={value.get('reason_code') or '—'}{posted}"
    )


def run(
    argv: list[str] | None = None,
    *,
    environ: Any | None = None,
    poster: Any | None = None,
    path_poster: Any | None = None,
    adapter: Any | None = None,
    pending: Any = None,
    positions: Any = None,
) -> int:
    args = _parser().parse_args(argv)
    if _live_blocked(environ):
        payload = {"error": "LiveModeDisabled", "message": "demo kill refuses GROK_TRADER_ALLOW_LIVE"}
        if args.as_json:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            print(f"ERROR {payload['error']}: {payload['message']}", file=sys.stderr)
        return 2
    if args.place_orders and not args.i_confirm_demo:
        payload = {"error": "PostDisabled", "message": "--place-orders requires --i-confirm-demo"}
        if args.as_json:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            print(f"ERROR {payload['error']}: {payload['message']}", file=sys.stderr)
        return 2
    place = bool(args.place_orders and args.i_confirm_demo)
    try:
        built = poster
        paths = path_poster
        client = adapter
        if place and built is None:
            built = make_demo_poster(environ=environ, pos_mode=args.pos_mode)
            paths = paths or make_path_poster(environ=environ)
            client = client or ReadOnlyBitgetAdapter(environ=environ)
        result = kill_symbol(
            args.symbol,
            allowed_symbols=_allowlist(args.allowlist),
            confirm_demo=bool(args.i_confirm_demo),
            dry_run=not place,
            environ=environ,
            poster=built,
            path_poster=paths,
            adapter=client,
            pending=pending,
            positions=positions,
            pos_mode=args.pos_mode,
        )
        _output(result.to_dict(), args.as_json)
        return 0
    except (
        LiveModeDisabled,
        MissingReadOnlyCredentials,
        DemoDispatchError,
        ValueError,
        OSError,
    ) as exc:
        payload = {"error": type(exc).__name__, "message": str(exc)[:80]}
        if args.as_json:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            print(f"ERROR {payload['error']}: {payload['message']}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
