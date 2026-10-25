"""Compact TA briefing for Demo AI context. Risk filter, not a forecast.

Uses public candles only. Missing adapter method, numpy, or short history
→ status unavailable; callers must not invent levels.
"""
from __future__ import annotations

from typing import Any, Mapping

GRANULARITY = {"15m": "15m", "1h": "1H", "4h": "4H", "1d": "1D"}
TF_KEYS = ("1h", "4h", "1d")
MAX_REASONS = 4
MAX_LEVELS = 6


def _num(value: Any) -> str | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in {float("inf"), float("-inf")}:
        return None
    return format(round(number, 6), "f")


def candles_to_arrays(rows: Any) -> dict[str, list[float]] | None:
    if not isinstance(rows, list) or len(rows) < 30:
        return None
    parsed: list[tuple[int, float, float, float, float, float]] = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 6:
            continue
        try:
            parsed.append(
                (
                    int(row[0]),
                    float(row[1]),
                    float(row[2]),
                    float(row[3]),
                    float(row[4]),
                    float(row[5]),
                )
            )
        except (TypeError, ValueError):
            continue
    if len(parsed) < 30:
        return None
    parsed.sort(key=lambda item: item[0])
    ts, o, h, l, c, v = zip(*parsed)
    return {"ts": list(ts), "o": list(o), "h": list(h), "l": list(l), "c": list(c), "v": list(v)}


def compact_analysis(analysis: Mapping[str, Any], side: str) -> dict[str, Any]:
    hold = "long" if str(side).strip().lower() != "short" else "short"
    risk = analysis.get("risk") if isinstance(analysis.get("risk"), Mapping) else {}
    side_risk = risk.get(hold) if isinstance(risk, Mapping) else None
    flag = "unavailable"
    reasons: list[str] = []
    if isinstance(side_risk, Mapping):
        flag = str(side_risk.get("flag") or "unavailable")
        raw_reasons = side_risk.get("reasons") or []
        if isinstance(raw_reasons, list):
            reasons = [str(item) for item in raw_reasons[:MAX_REASONS]]
    tfs: dict[str, Any] = {}
    source_tf = analysis.get("tf") if isinstance(analysis.get("tf"), Mapping) else {}
    for key in TF_KEYS:
        row = source_tf.get(key)
        if not isinstance(row, Mapping):
            continue
        tfs[key] = {
            "adx": _num(row.get("adx")),
            "bias": str(row.get("bias") or ""),
            "rsi": _num(row.get("rsi")),
            "structure": str(row.get("structure") or ""),
        }
    levels = []
    for item in analysis.get("levels") or []:
        if not isinstance(item, Mapping):
            continue
        price = _num(item.get("price"))
        if not price:
            continue
        levels.append(
            {
                "price": price,
                "strength": _num(item.get("strength")) or "0",
                "type": str(item.get("type") or ""),
            }
        )
        if len(levels) >= MAX_LEVELS:
            break
    changes = analysis.get("changes") if isinstance(analysis.get("changes"), Mapping) else {}
    return {
        "status": "ok",
        "disclaimer": str(analysis.get("disclaimer") or "Risk filter, not a price forecast."),
        "regime": str(analysis.get("regime") or ""),
        "mtf_score": _num(analysis.get("mtf_score")),
        "ch_1h": _num(changes.get("ch_1h")) if isinstance(changes, Mapping) else None,
        "risk_side": flag,
        "risk_reasons": reasons,
        "tf": tfs,
        "near_levels": levels,
    }


def build_ta_brief(
    symbol: str,
    side: str,
    adapter: Any | None,
    *,
    analyze=None,
) -> dict[str, Any]:
    if adapter is None or not hasattr(adapter, "public_candles"):
        return {"status": "unavailable", "reason": "no_public_candles"}
    try:
        from trader.ta import analyze as default_analyze
    except ImportError:
        default_analyze = None
    fn = analyze or default_analyze
    if fn is None:
        return {"status": "unavailable", "reason": "ta_module_missing"}
    candles: dict[str, Any] = {}
    now_ms = None
    try:
        for tf, gran in GRANULARITY.items():
            arrays = candles_to_arrays(adapter.public_candles(symbol, gran, limit=200))
            if arrays is None:
                return {"status": "unavailable", "reason": f"short_{tf}"}
            candles[tf] = arrays
            now_ms = int(arrays["ts"][-1])
        packed = fn(candles, now_ms)
    except Exception:
        return {"status": "error", "reason": "ta_failed"}
    if not isinstance(packed, Mapping):
        return {"status": "error", "reason": "ta_invalid"}
    return compact_analysis(packed, side)
