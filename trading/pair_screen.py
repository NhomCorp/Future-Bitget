"""Deterministic public pair screen for local Demo whitelist proposals.

Ranks USDT-M tickers by 24h quote volume. Does not approve symbols, create
mandate versions, or send orders. Suggested pairs stay outside the allowlist
until the user confirms them.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

SYMBOL_RE = re.compile(r"^[A-Z0-9_-]{1,32}$")
CANDIDATE_LIMIT_DEFAULT = 12
CANDIDATE_LIMIT_MAX = 20
VOLUME_KEYS = ("usdtVolume", "quoteVolume", "quoteVol", "usdtVol")
LAST_KEYS = ("lastPr", "last")
MARK_KEYS = ("markPrice", "markPr", "indexPrice")
CHANGE_KEYS = ("change24h", "changeUtc24h", "chgUtc")


def clamp_candidate_limit(value: Any, default: int = CANDIDATE_LIMIT_DEFAULT) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return default
    if limit < 1:
        return 1
    return min(limit, CANDIDATE_LIMIT_MAX)


def _rows(payload: Any) -> list[Mapping[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]
    if isinstance(payload, Mapping):
        data = payload.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, Mapping)]
        if isinstance(data, Mapping):
            nested = data.get("tickers") or data.get("list")
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, Mapping)]
        return [payload]
    return []


def _text(row: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite():
        return None
    return number


def _symbol(row: Mapping[str, Any]) -> str | None:
    raw = _text(row, "symbol")
    if not raw:
        return None
    symbol = raw.upper()
    if not SYMBOL_RE.fullmatch(symbol):
        return None
    return symbol


def rank_pair_candidates(
    tickers: Any,
    *,
    limit: int = CANDIDATE_LIMIT_DEFAULT,
    exclude: Any = (),
) -> list[dict[str, str]]:
    """Return top public USDT-M symbols by 24h quote volume.

    Rows without a usable symbol or positive volume are skipped. ``exclude``
    drops symbols already approved or rejected; the function never adds them
    back. Output is public fields only.
    """
    capped = clamp_candidate_limit(limit)
    blocked = {
        str(item).strip().upper()
        for item in (exclude or ())
        if str(item).strip()
    }
    ranked: list[tuple[Decimal, str, dict[str, str]]] = []
    seen: set[str] = set()
    for row in _rows(tickers):
        symbol = _symbol(row)
        if not symbol or symbol in seen or symbol in blocked:
            continue
        volume_text = _text(row, *VOLUME_KEYS)
        volume = _decimal(volume_text)
        if volume is None or volume <= 0:
            continue
        seen.add(symbol)
        item = {
            "symbol": symbol,
            "volume24h": format(volume, "f"),
            "reason": "Top khối lượng 24h USDT-M",
        }
        last = _decimal(_text(row, *LAST_KEYS))
        mark = _decimal(_text(row, *MARK_KEYS))
        change = _decimal(_text(row, *CHANGE_KEYS))
        if last is not None:
            item["last"] = format(last, "f")
        if mark is not None:
            item["mark"] = format(mark, "f")
        if change is not None:
            item["change24h"] = format(change, "f")
        ranked.append((volume, symbol, item))
    ranked.sort(key=lambda entry: (-entry[0], entry[1]))
    return [item for _, _, item in ranked[:capped]]
