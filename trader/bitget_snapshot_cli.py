"""Local GET-only CLI for Demo dashboard snapshots.

Examples:
  python -m trader.bitget_snapshot_cli snapshot
  python -m trader.bitget_snapshot_cli snapshot --symbol BTCUSDT

The command never dumps raw Bitget account payloads, never prints credentials
or signed headers, and never creates paper or exchange intents. Frontend local
spawns this module; Node does not sign Bitget requests. Recent fills come from
GET /api/v2/mix/order/fills (Demo); fill-history is not used.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from trader.bitget_readonly import (
    FILL_LIMIT,
    BitgetAdapterError,
    LiveModeDisabled,
    MissingReadOnlyCredentials,
    ReadOnlyBitgetAdapter,
)
from trader.envfile import load_os_env_file


POSITION_FIELDS = (
    ("symbol", "symbol"),
    ("holdSide", "side"),
    ("posSide", "side"),
    ("total", "size"),
    ("available", "available"),
    ("leverage", "leverage"),
    ("marginMode", "margin_mode"),
    ("openPriceAvg", "entry_price"),
    ("markPrice", "mark_price"),
    ("liquidationPrice", "liquidation_price"),
    ("unrealizedPL", "unrealized_pnl"),
)
ORDER_FIELDS = (
    ("symbol", "symbol"),
    ("side", "side"),
    ("posSide", "pos_side"),
    ("tradeSide", "trade_side"),
    ("price", "price"),
    ("size", "size"),
    ("orderType", "order_type"),
    ("status", "status"),
)
FILL_FIELDS = (
    ("symbol", "symbol"),
    ("side", "side"),
    ("posSide", "pos_side"),
    ("holdSide", "pos_side"),
    ("tradeSide", "trade_side"),
    ("price", "price"),
    ("fillPrice", "price"),
    ("baseVolume", "size"),
    ("size", "size"),
    ("tradeScope", "trade_scope"),
    ("clientOid", "client_oid"),
    ("tradeId", "trade_id"),
    ("orderId", "order_id"),
)
ASSET_EQUITY_KEYS = ("accountEquity", "usdtEquity", "equity")
ASSET_AVAILABLE_KEYS = ("available", "availableEquity", "crossedMaxAvailable")
ASSET_PNL_KEYS = ("unrealizedPL", "crossedUnrealizedPL", "isolatedUnrealizedPL")
TICKER_LAST_KEYS = ("lastPr", "last")
TICKER_MARK_KEYS = ("markPrice", "markPr", "indexPrice")
TICKER_FUNDING_KEYS = ("fundingRate", "funding")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Demo dashboard snapshot CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    snapshot = sub.add_parser("snapshot", help="GET Demo account, positions, pending orders and recent fills")
    snapshot.add_argument("--symbol", help="optional public ticker symbol")
    return parser


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _finite_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite():
        return None
    return text


def _text(row: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _rows(payload: Any) -> list[Mapping[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]
    if isinstance(payload, Mapping):
        for key in ("list", "entrustedList", "fillList"):
            inner = payload.get(key)
            if isinstance(inner, list):
                return [item for item in inner if isinstance(item, Mapping)]
        if "entrustedList" in payload or "fillList" in payload or "endId" in payload:
            return []
        return [payload]
    return []


def _first_row(payload: Any) -> Mapping[str, Any] | None:
    items = _rows(payload)
    return items[0] if items else None


def _live_guard_on(environ: Mapping[str, str] | None) -> bool:
    env = os.environ if environ is None else environ
    return str(env.get("GROK_TRADER_ALLOW_LIVE", "")).strip() == "1"


def _pick_mapped(row: Mapping[str, Any], mapping: tuple[tuple[str, str], ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for source, dest in mapping:
        if dest in out:
            continue
        value = row.get(source)
        if dest in {
            "size",
            "available",
            "leverage",
            "entry_price",
            "mark_price",
            "liquidation_price",
            "unrealized_pnl",
            "price",
            "fee",
            "profit",
        }:
            text = _finite_text(value)
        else:
            text = str(value).strip() if value not in (None, "") else None
        if text:
            out[dest] = text
    return out


def _filter_position(row: Mapping[str, Any]) -> dict[str, str] | None:
    size = _finite_text(row.get("total") or row.get("available") or row.get("size") or row.get("holdVol"))
    if size is None:
        return None
    try:
        if Decimal(size) == 0:
            return None
    except (InvalidOperation, ValueError):
        return None
    item = _pick_mapped(row, POSITION_FIELDS)
    if size and "size" not in item:
        item["size"] = size
    if not item.get("symbol"):
        return None
    return item


def _filter_order(row: Mapping[str, Any]) -> dict[str, str] | None:
    item = _pick_mapped(row, ORDER_FIELDS)
    if not item.get("symbol"):
        return None
    return item


def _fill_fee(row: Mapping[str, Any]) -> str | None:
    fee = _finite_text(row.get("fee") or row.get("totalFee"))
    if fee is not None:
        return fee
    details = row.get("feeDetail")
    if not isinstance(details, list):
        return None
    total = Decimal("0")
    found = False
    for item in details:
        if not isinstance(item, Mapping):
            continue
        part = _finite_text(item.get("totalFee") or item.get("fee"))
        if part is None:
            continue
        total += Decimal(part)
        found = True
    if not found:
        return None
    return format(total, "f")


def _time_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    if "T" in text:
        return text[:40]
    try:
        raw = int(text)
    except ValueError:
        return text[:40]
    if raw <= 0:
        return None
    seconds = raw / 1000 if raw >= 10_000_000_000 else raw
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError):
        return text[:40]


def _fill_sort_key(row: Mapping[str, Any]) -> int:
    value = row.get("cTime")
    if value in (None, ""):
        value = row.get("c_time")
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _filter_fill(row: Mapping[str, Any]) -> dict[str, str] | None:
    item = _pick_mapped(row, FILL_FIELDS)
    if not item.get("symbol"):
        return None
    fee = _fill_fee(row)
    if fee is not None:
        item["fee"] = fee
    profit = _finite_text(row.get("profit"))
    if profit is not None:
        item["profit"] = profit
    filled_at = _time_text(row.get("cTime") or row.get("c_time") or row.get("filled_at"))
    if filled_at:
        item["filled_at"] = filled_at
    return item


def _filter_asset(row: Mapping[str, Any]) -> dict[str, str] | None:
    coin = _text(row, "marginCoin", "margin_coin")
    equity = None
    for key in ASSET_EQUITY_KEYS:
        equity = _finite_text(row.get(key))
        if equity is not None:
            break
    available = None
    for key in ASSET_AVAILABLE_KEYS:
        available = _finite_text(row.get(key))
        if available is not None:
            break
    pnl = None
    for key in ASSET_PNL_KEYS:
        pnl = _finite_text(row.get(key))
        if pnl is not None:
            break
    if not coin and equity is None and available is None:
        return None
    item: dict[str, str] = {}
    if coin:
        item["margin_coin"] = coin.upper()
    if equity is not None:
        item["equity"] = equity
    if available is not None:
        item["available"] = available
    if pnl is not None:
        item["unrealized_pnl"] = pnl
    return item or None


def _filter_ticker(payload: Any, symbol: str | None) -> dict[str, str] | None:
    row = _first_row(payload)
    if row is None:
        return None
    last = None
    mark = None
    funding = None
    for key in TICKER_LAST_KEYS:
        last = _finite_text(row.get(key))
        if last is not None:
            break
    for key in TICKER_MARK_KEYS:
        mark = _finite_text(row.get(key))
        if mark is not None:
            break
    for key in TICKER_FUNDING_KEYS:
        funding = _finite_text(row.get(key))
        if funding is not None:
            break
    ticker_symbol = _text(row, "symbol") or (symbol.upper() if symbol else None)
    if not ticker_symbol and last is None and mark is None and funding is None:
        return None
    item: dict[str, str] = {}
    if ticker_symbol:
        item["symbol"] = ticker_symbol.upper()
    if last is not None:
        item["last"] = last
    if mark is not None:
        item["mark"] = mark
    if funding is not None:
        item["funding"] = funding
    return item or None


def _usdt_equity(assets: list[dict[str, str]]) -> str | None:
    for row in assets:
        if row.get("margin_coin") == "USDT" and row.get("equity"):
            return row["equity"]
    if assets and assets[0].get("equity"):
        return assets[0]["equity"]
    return None


def build_dashboard_snapshot(raw: Mapping[str, Any], *, symbol: str | None = None) -> dict[str, Any]:
    positions = [item for item in (_filter_position(row) for row in _rows(raw.get("positions"))) if item]
    pending_orders = [item for item in (_filter_order(row) for row in _rows(raw.get("pending_orders"))) if item]
    assets = [item for item in (_filter_asset(row) for row in _rows(raw.get("account"))) if item]
    fill_rows = sorted(_rows(raw.get("fills")), key=_fill_sort_key, reverse=True)
    fills = [item for item in (_filter_fill(row) for row in fill_rows) if item][:FILL_LIMIT]
    payload: dict[str, Any] = {
        "ok": True,
        "as_of": _now_utc(),
        "product_type": str(raw.get("product_type") or "USDT-FUTURES"),
        "equity": _usdt_equity(assets),
        "assets": assets,
        "positions": positions,
        "pending_orders": pending_orders,
        "fills": fills,
    }
    ticker = _filter_ticker(raw.get("ticker"), symbol)
    if ticker:
        payload["ticker"] = ticker
    return payload


def _print_error(kind: str, message: str) -> None:
    print(json.dumps({"ok": False, "error": kind, "message": str(message)[:80]}, ensure_ascii=False, sort_keys=True))


def run(
    argv: list[str] | None = None,
    *,
    adapter: Any | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    args = _parser().parse_args(argv)
    if args.command != "snapshot":
        return 2
    symbol = str(args.symbol or "").strip().upper() or None
    if symbol and len(symbol) > 32:
        _print_error("ValueError", "symbol quá dài")
        return 2
    try:
        if adapter is None:
            if environ is None:
                load_os_env_file()
            env = os.environ if environ is None else environ
            if _live_guard_on(env):
                raise LiveModeDisabled("GROK_TRADER_ALLOW_LIVE is on; dashboard GET is Demo-only")
            client: Any = ReadOnlyBitgetAdapter(demo=True, environ=env if environ is not None else None)
        else:
            client = adapter
        raw = client.snapshot(symbol=symbol)
        if not isinstance(raw, Mapping):
            raise BitgetAdapterError("snapshot is not an object")
        print(json.dumps(build_dashboard_snapshot(raw, symbol=symbol), ensure_ascii=False, sort_keys=True))
        return 0
    except (LiveModeDisabled, MissingReadOnlyCredentials, BitgetAdapterError, ValueError) as exc:
        _print_error(type(exc).__name__, str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
