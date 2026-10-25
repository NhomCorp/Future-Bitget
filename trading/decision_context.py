"""Attach user-style + TA briefing onto a Demo decision snapshot's features."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from trader.ta_brief import build_ta_brief
from trading.style_load import load_user_style


def enrich_decision_features(
    features: Mapping[str, Any] | None,
    *,
    symbol: str,
    side: str,
    now: datetime | str | None = None,
    adapter: Any | None = None,
    style_path: str | None = None,
    analyze=None,
) -> dict[str, Any]:
    out = dict(features or {})
    out["user_style"] = load_user_style(style_path, now=now)
    out["ta"] = build_ta_brief(symbol, side, adapter, analyze=analyze)
    return out
