"""Minimal Demo/dry-run CLI for the standalone zone foundation.

Examples:
  python -m trader.zone_cli --store :memory: preview --symbol BTCUSDT --side long --ref-price 100 --zone-loss-limit-usdt 10
  python -m trader.zone_cli --store trader/data/zones.sqlite3 status
  python -m trader.zone_cli --store trader/data/zones.sqlite3 sync --zone-id zone-... --mark-price 95

The CLI only mutates the local store. It does not call Bitget and has no POST
path. Exchange reads belong to ``bitget_readonly.ReadOnlyBitgetAdapter`` and
must be wired by a future reconcile layer after Demo verification.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

try:
    from .zone_store import ZoneStore, ZoneStoreError
except ImportError:
    from zone_store import ZoneStore, ZoneStoreError


DEFAULT_STORE = "trader/data/zones.sqlite3"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Zone foundation Demo/dry-run CLI")
    parser.add_argument("--store", default=DEFAULT_STORE, help="SQLite path (default: %(default)s)")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON")

    preview = sub.add_parser("preview", help="persist an immutable local zone preview")
    common(preview)
    preview.add_argument("--zone-id")
    preview.add_argument("--symbol", required=True)
    preview.add_argument("--side", required=True, choices=("long", "short"))
    preview.add_argument("--ref-price", required=True)
    preview.add_argument("--zone-loss-limit-usdt")
    preview.add_argument("--sl-pct")
    preview.add_argument("--policy-version", default="zone-risk-policy.p1")
    preview.add_argument("--activate", action="store_true", help="start local Demo zone as ACTIVE")

    status = sub.add_parser("status", help="show durable local zone state")
    common(status)
    status.add_argument("--zone-id")
    status.add_argument("--include-closed", action="store_true", default=False)

    sync = sub.add_parser("sync", help="record one mock/dry-run observation")
    common(sync)
    sync.add_argument("--zone-id", required=True)
    sync.add_argument("--mark-price")
    sync.add_argument("--realized-pnl", default="0")
    sync.add_argument("--unrealized-pnl", default="0")
    sync.add_argument("--fees", default="0")
    sync.add_argument("--funding-paid", default="0")
    sync.add_argument("--funding-received", default="0")
    sync.add_argument("--source", default="mock", choices=("mock", "dry-run"))
    sync.add_argument("--activate", action="store_true", help="activate a PREVIEW zone before recording")
    return parser


def _output(value: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str))
        return
    if isinstance(value, list):
        if not value:
            print("Không có zone.")
            return
        for item in value:
            print(
                f"{item['zone_id']} {item['symbol']} {item['side']} "
                f"state={item['state']} ref={item['ref_price']} "
                f"net={item.get('last_net_pnl') or '—'}"
            )
        return
    if "observation" in value:
        print(
            f"{value['zone_id']} state={value['state']} "
            f"net={value['observation']['net_pnl']} "
            f"triggered={'yes' if value['triggered'] else 'no'}"
        )
        if value.get("reason"):
            print(f"reason={value['reason']} (dry-run intent only)")
        return
    print(
        f"{value['zone_id']} {value['symbol']} {value['side']} "
        f"state={value['state']} ref={value['ref_price']}"
    )


def run(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        with ZoneStore(args.store) as store:
            if args.command == "preview":
                config = {
                    "symbol": args.symbol,
                    "side": args.side,
                    "ref_price": args.ref_price,
                    "zone_loss_limit_usdt": args.zone_loss_limit_usdt,
                    "sl_pct": args.sl_pct,
                    "policy_version": args.policy_version,
                }
                zone = store.create_zone(config, zone_id=args.zone_id, state="ACTIVE" if args.activate else "PREVIEW")
                _output(zone.as_dict(), args.as_json)
                return 0

            if args.command == "status":
                if args.zone_id:
                    _output(store.get_zone(args.zone_id).as_dict(), args.as_json)
                else:
                    _output([zone.as_dict() for zone in store.list_zones(include_closed=args.include_closed)], args.as_json)
                return 0

            if args.command == "sync":
                zone = store.get_zone(args.zone_id)
                if args.activate and zone.state == "PREVIEW":
                    zone = store.activate_zone(args.zone_id)
                result = store.record_observation(
                    args.zone_id,
                    {
                        "mark_price": args.mark_price,
                        "realized_pnl": args.realized_pnl,
                        "unrealized_pnl": args.unrealized_pnl,
                        "fees": args.fees,
                        "funding_paid": args.funding_paid,
                        "funding_received": args.funding_received,
                    },
                    source=args.source,
                )
                _output(result, args.as_json)
                return 0
    except (ZoneStoreError, ValueError) as exc:
        if args.as_json:
            print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False))
        else:
            print(f"ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(run())
