"""Local protection clock CLI. One tick or a local loop; never POSTs to Bitget.

Examples:
  python -m trader.protect_clock_cli tick --store trader/data/zones.sqlite3 --zone-id ZONE --observation obs.json --json
  python -m trader.protect_clock_cli loop --store trader/data/zones.sqlite3 --zone-id ZONE --observation obs.json --max-ticks 1

The command does not run the paper scan clock and does not POST. Frontend does
not call this module.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from executor.p1_adapter import P1IntegrationStore
from trader.zone_store import ZoneStore, ZoneStoreError
from trading.protect_clock import ProtectClockError, ProtectObservation, run_loop, tick


DEFAULT_STORE = "trader/data/zones.sqlite3"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local protection clock tick/loop; no exchange POST")
    parser.add_argument("--store", default=DEFAULT_STORE, help="SQLite path (default: %(default)s)")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--zone-id", required=True)
        command_parser.add_argument("--observation", required=True, help="JSON ProtectObservation")
        command_parser.add_argument("--now", help="ISO-8601 evaluation time; default is current UTC")
        command_parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON")

    tick_cmd = sub.add_parser("tick", help="one protection tick")
    common(tick_cmd)

    loop_cmd = sub.add_parser("loop", help="repeat tick locally; not a paper-scan poll")
    common(loop_cmd)
    loop_cmd.add_argument("--poll-seconds", type=float, default=2.0)
    loop_cmd.add_argument("--max-ticks", type=int, default=1, help="stop after N ticks (default: 1)")
    return parser


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _live_blocked(environ: Any | None = None) -> bool:
    env = os.environ if environ is None else environ
    return str(env.get("GROK_TRADER_ALLOW_LIVE", "")).strip() == "1"


def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _output(value: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str))
        return
    if isinstance(value, list):
        for item in value:
            _output(item, False)
        return
    print(
        f"ran={value.get('ran')} triggered={value.get('triggered')} "
        f"reason={value.get('reason_code')} post={value.get('exchange_post')}"
    )


def run(
    argv: list[str] | None = None,
    *,
    store: P1IntegrationStore | None = None,
    observation: ProtectObservation | None = None,
    environ: Any | None = None,
    sleep: Any | None = None,
    now_fn: Any | None = None,
) -> int:
    args = _parser().parse_args(argv)
    if _live_blocked(environ):
        payload = {"error": "LiveModeDisabled", "message": "protect clock refuses GROK_TRADER_ALLOW_LIVE"}
        if args.as_json:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            print(f"ERROR {payload['error']}: {payload['message']}", file=sys.stderr)
        return 2

    owned = store is None
    zones: ZoneStore | None = None
    try:
        if observation is None:
            observation = ProtectObservation.from_dict(_load_json(args.observation))
        if store is None:
            zones = ZoneStore(args.store)
            store = P1IntegrationStore(zones)

        clock = now_fn or _now_utc
        now = args.now or clock()
        if args.command == "tick":
            result = tick(store, args.zone_id, observation, now=now)
            _output(result.to_dict(), args.as_json)
            return 0
        if args.command == "loop":
            results = run_loop(
                store,
                args.zone_id,
                observation,
                now_fn=(lambda: args.now) if args.now else clock,
                sleep=sleep or time.sleep,
                poll_seconds=args.poll_seconds,
                max_ticks=args.max_ticks,
            )
            _output([item.to_dict() for item in results], args.as_json)
            return 0
    except (ZoneStoreError, ProtectClockError, ValueError, OSError, json.JSONDecodeError) as exc:
        payload = {"error": type(exc).__name__, "message": str(exc)[:80]}
        if args.as_json:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            print(f"ERROR {payload['error']}: {payload['message']}", file=sys.stderr)
        return 2
    finally:
        if owned:
            if store is not None:
                store.close()
            if zones is not None:
                zones.close()
    return 2


if __name__ == "__main__":
    raise SystemExit(run())
