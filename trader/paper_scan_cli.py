"""Local paper scan CLI. One tick or a local loop; Demo POST is opt-in.

Examples:
  python -m trader.paper_scan_cli tick --store trader/data/zones.sqlite3 --zone-id ZONE --mandate-id MID --snapshot snap.json --json
  python -m trader.paper_scan_cli loop --store trader/data/zones.sqlite3 --zone-id ZONE --mandate-id MID --snapshot snap.json --max-ticks 1
  python -m trader.paper_scan_cli tick --zone-id ZONE --mandate-id MID --snapshot snap.json --place-orders --i-confirm-demo --json

Default is local paper intents only. Demo POST requires both ``--place-orders``
and ``--i-confirm-demo``, and only for symbols in the mandate whitelist.
The command does not run the protection clock (SL / fill / mark) and does not
flatten when a mandate expires. Frontend does not call this module. Live is refused.
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

from ai_proposal.provider import StaticPaperProvider
from ai_proposal.schema import DecisionOpportunitySnapshot, ProposalDraft
from executor.p1_adapter import P1IntegrationStore
from trader.bitget_readonly import LiveModeDisabled, MissingReadOnlyCredentials
from trader.zone_store import ZoneStore, ZoneStoreError
from trading.demo_dispatch import (
    DemoDispatchError,
    make_demo_poster,
    make_order_query,
    make_tpsl_poster,
)
from trading.mandate import MandateError, TradingMandate
from trading.mandate_store import MandateStore
from trading.paper_agent import PaperAgent
from trading.paper_scan import LocalNoTradeProvider, ScanDispatchOptions, run_loop, tick


DEFAULT_STORE = "trader/data/zones.sqlite3"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local paper scan tick/loop; Demo POST only with --place-orders --i-confirm-demo"
    )
    parser.add_argument("--store", default=DEFAULT_STORE, help="SQLite path (default: %(default)s)")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--zone-id", required=True)
        command_parser.add_argument("--mandate-id", required=True)
        command_parser.add_argument("--snapshot", required=True, help="JSON DecisionOpportunitySnapshot")
        command_parser.add_argument("--proposal", help="optional JSON ProposalDraft; default is local NO_TRADE")
        command_parser.add_argument("--now", help="ISO-8601 evaluation time; default is current UTC")
        command_parser.add_argument("--stale", action="store_true", help="treat snapshot as stale; skip AI")
        command_parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON")
        command_parser.add_argument(
            "--place-orders",
            action="store_true",
            help="allow Demo POST for whitelist intents (requires --i-confirm-demo)",
        )
        command_parser.add_argument(
            "--i-confirm-demo",
            action="store_true",
            help="confirm Demo dispatch; without --place-orders stays dry-run",
        )

    tick_cmd = sub.add_parser("tick", help="one paper scan tick")
    common(tick_cmd)

    loop_cmd = sub.add_parser("loop", help="repeat tick locally; not a protection-clock poll")
    common(loop_cmd)
    loop_cmd.add_argument("--poll-seconds", type=float, default=10.0)
    loop_cmd.add_argument("--max-ticks", type=int, default=1, help="stop after N ticks (default: 1)")
    return parser


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _live_blocked(environ: Any | None = None) -> bool:
    env = os.environ if environ is None else environ
    mode = str(env.get("BITGET_ENV", "demo")).strip().lower()
    return str(env.get("GROK_TRADER_ALLOW_LIVE", "")).strip() == "1" or mode in {"live", "production", "prod"}


def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _provider(args: argparse.Namespace) -> Any:
    if not args.proposal:
        return LocalNoTradeProvider()
    draft = ProposalDraft.from_dict(_load_json(args.proposal))
    return StaticPaperProvider(draft)


def _output(value: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str))
        return
    if isinstance(value, list):
        for item in value:
            _output(item, False)
        return
    posted = " post=yes" if value.get("exchange_post") else ""
    print(
        f"due={value.get('due')} ran={value.get('ran')} "
        f"action={value.get('action')} reason={value.get('reason_code')} "
        f"next={value.get('next_due_at') or '—'}{posted}"
    )


def _dispatch_options(
    args: argparse.Namespace,
    *,
    environ: Any | None,
    poster: Any | None,
) -> ScanDispatchOptions | None:
    if not args.i_confirm_demo and not args.place_orders:
        return None
    place = bool(args.place_orders and args.i_confirm_demo)
    built = poster
    tpsl = None
    query = None
    if place and built is None:
        built = make_demo_poster(environ=environ)
        tpsl = make_tpsl_poster(environ=environ)
        query = make_order_query(environ=environ)
    return ScanDispatchOptions(
        confirm_demo=bool(args.i_confirm_demo),
        dry_run=not place,
        poster=built,
        tpsl_poster=tpsl,
        query=query,
        environ=environ,
    )


def run(
    argv: list[str] | None = None,
    *,
    agent: PaperAgent | None = None,
    store: P1IntegrationStore | None = None,
    snapshot: DecisionOpportunitySnapshot | None = None,
    mandate: TradingMandate | None = None,
    environ: Any | None = None,
    sleep: Any | None = None,
    now_fn: Any | None = None,
    poster: Any | None = None,
    dispatch: ScanDispatchOptions | None = None,
) -> int:
    args = _parser().parse_args(argv)
    if _live_blocked(environ):
        payload = {"error": "LiveModeDisabled", "message": "paper scan refuses GROK_TRADER_ALLOW_LIVE"}
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

    owned = store is None
    zones: ZoneStore | None = None
    try:
        if snapshot is None:
            snapshot = DecisionOpportunitySnapshot.from_dict(_load_json(args.snapshot))
        if store is None:
            zones = ZoneStore(args.store)
            store = P1IntegrationStore(zones)
        if mandate is None:
            mandate = MandateStore(store).latest(args.mandate_id)
        if mandate is None:
            raise MandateError(f"mandate not found: {args.mandate_id}")
        if mandate.zone_id != args.zone_id:
            raise MandateError("mandate zone_id does not match --zone-id")
        if agent is None:
            agent = PaperAgent(_provider(args), store)
        if dispatch is None:
            dispatch = _dispatch_options(args, environ=environ, poster=poster)

        clock = now_fn or _now_utc
        now = args.now or clock()
        if args.command == "tick":
            result = tick(agent, snapshot, mandate, now=now, stale=args.stale, dispatch=dispatch)
            _output(result.to_dict(), args.as_json)
            return 0
        if args.command == "loop":
            results = run_loop(
                agent,
                snapshot,
                mandate,
                now_fn=(lambda: args.now) if args.now else clock,
                sleep=sleep or time.sleep,
                poll_seconds=args.poll_seconds,
                max_ticks=args.max_ticks,
                stale=args.stale,
                dispatch=dispatch,
            )
            _output([item.to_dict() for item in results], args.as_json)
            return 0
    except (
        ZoneStoreError,
        MandateError,
        ValueError,
        OSError,
        json.JSONDecodeError,
        LiveModeDisabled,
        MissingReadOnlyCredentials,
        DemoDispatchError,
    ) as exc:
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
