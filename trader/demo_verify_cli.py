"""CLI for Demo verification checklist D0-D15.

Examples:
  python -m trader.demo_verify_cli run --symbol BTCUSDT --json
  python -m trader.demo_verify_cli run --symbol BTCUSDT --place-orders --i-confirm-demo

Default is GET-only baseline (Bước A / D0-D4). POST for D5-D6 requires both
``--place-orders`` and ``--i-confirm-demo``. This CLI is not a dispatcher and
never sets GROK_TRADER_ALLOW_LIVE.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from trader.bitget_readonly import BitgetAdapterError, LiveModeDisabled, MissingReadOnlyCredentials
from trader.demo_verify import DemoVerifyClient, DemoVerifyError, write_evidence, run_demo_verify


DEFAULT_EVIDENCE = "logs/demo_verify.jsonl"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bitget Demo verification harness (not a dispatcher)")
    sub = parser.add_subparsers(dest="command", required=True)
    run_cmd = sub.add_parser("run", help="Run Demo checklist cases and write redacted evidence")
    run_cmd.add_argument("--symbol", required=True)
    run_cmd.add_argument("--zone-id", default="demo-verify")
    run_cmd.add_argument("--json", action="store_true", dest="as_json")
    run_cmd.add_argument("--evidence", default=DEFAULT_EVIDENCE, help="append-only JSONL path")
    run_cmd.add_argument("--now", help="ISO-8601 capture time; default is current UTC")
    run_cmd.add_argument(
        "--place-orders",
        action="store_true",
        help="allow Demo POST for far-from-market limit + cancel (D5-D6)",
    )
    run_cmd.add_argument(
        "--i-confirm-demo",
        action="store_true",
        help="required together with --place-orders; confirms Demo, not live",
    )
    return parser


def _print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        sys.stdout.buffer.write((text + "\n").encode(encoding, errors="replace"))


def _output(report: dict[str, Any], as_json: bool) -> None:
    if as_json:
        _print(json.dumps(report, ensure_ascii=True, sort_keys=True))
        return
    _print(f"{report['symbol']} {report['captured_at']} paptrading={report['paptrading']}")
    for case in report["cases"]:
        dispatch = f" dispatch={case['dispatch']}" if case.get("dispatch") else ""
        _print(f"{case['case_id']} {case['verdict']}{dispatch} {case['notes']}")


def run(argv: list[str] | None = None, *, client: DemoVerifyClient | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "run":
        return 2
    if args.place_orders and not args.i_confirm_demo:
        payload = {
            "error": "PostDisabled",
            "message": "--place-orders requires --i-confirm-demo",
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True) if args.as_json else f"ERROR {payload['error']}: {payload['message']}")
        return 2
    try:
        harness = client
        if harness is None:
            harness = DemoVerifyClient(demo=True, allow_post=bool(args.place_orders and args.i_confirm_demo))
        elif args.place_orders and args.i_confirm_demo:
            harness.allow_post = True
        report = run_demo_verify(
            harness,
            symbol=args.symbol,
            zone_id=args.zone_id,
            now=args.now,
            place_orders=bool(args.place_orders and args.i_confirm_demo),
        )
        payload = report.to_dict()
        write_evidence(args.evidence, report)
        _output(payload, args.as_json)
        return 0
    except (LiveModeDisabled, MissingReadOnlyCredentials, BitgetAdapterError, DemoVerifyError, ValueError) as exc:
        payload = {"error": type(exc).__name__, "message": str(exc)[:80]}
        if args.as_json:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            print(f"ERROR {payload['error']}: {payload['message']}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
