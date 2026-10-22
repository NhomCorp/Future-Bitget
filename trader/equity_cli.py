"""Local GET-only CLI for Demo account equity snapshots.

Examples:
  python -m trader.equity_cli snapshot --max-age-seconds 60 --json

The command never dumps raw Bitget payloads, never prints credentials, and
never creates paper or exchange intents. Frontend does not call this module.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any

from trader.bitget_readonly import BitgetAdapterError, LiveModeDisabled, ReadOnlyBitgetAdapter
from trading.equity_snapshot import capture_equity_snapshot
from trading.equity_store import DEFAULT_PATH, EquityStore, EquityStoreError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Demo equity snapshot CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    snapshot = sub.add_parser("snapshot", help="GET Demo account equity and print a redacted snapshot")
    snapshot.add_argument("--max-age-seconds", type=int, required=True, help="freshness limit; no trading default")
    snapshot.add_argument("--json", action="store_true", dest="as_json", help="emit JSON")
    snapshot.add_argument("--store", default=DEFAULT_PATH, help="SQLite path (default: %(default)s)")
    snapshot.add_argument("--drawdown-unit", default="usdt", choices=("usdt", "pct"))
    snapshot.add_argument(
        "--drawdown-reference",
        default="equity_peak",
        choices=("equity_peak", "day_start", "policy_start"),
    )
    snapshot.add_argument("--now", help="ISO-8601 evaluation time; default is current UTC")
    return parser


def _output(value: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, sort_keys=True))
        return
    status = "complete" if value.get("complete") else "incomplete"
    stale = " stale" if value.get("stale") else ""
    print(
        f"equity={value.get('current_equity') or '—'} "
        f"day_start={value.get('day_start_equity') or '—'} "
        f"daily_loss={value.get('daily_loss') or '—'} "
        f"drawdown={value.get('drawdown') or '—'} "
        f"{status}{stale}"
    )
    reasons = value.get("reason_codes") or []
    if reasons:
        print("reason=" + ",".join(str(item) for item in reasons))


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def run(
    argv: list[str] | None = None,
    *,
    adapter: Any | None = None,
    store: EquityStore | None = None,
) -> int:
    args = _parser().parse_args(argv)
    if args.command != "snapshot":
        return 2
    owned_store = store is None
    ledger = store
    try:
        client = adapter if adapter is not None else ReadOnlyBitgetAdapter(demo=True)
        if ledger is None:
            ledger = EquityStore(args.store)
        record = capture_equity_snapshot(
            client,
            ledger,
            max_age_seconds=args.max_age_seconds,
            now=args.now or _now_utc(),
            drawdown_unit=args.drawdown_unit,
            drawdown_reference=args.drawdown_reference,
        )
        _output(record.to_dict(), args.as_json)
        return 0
    except (LiveModeDisabled, BitgetAdapterError, EquityStoreError, ValueError) as exc:
        payload = {"error": type(exc).__name__, "message": str(exc)[:80]}
        if args.as_json:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            print(f"ERROR {payload['error']}: {payload['message']}", file=sys.stderr)
        return 2
    finally:
        if owned_store and ledger is not None:
            ledger.close()


if __name__ == "__main__":
    raise SystemExit(run())
