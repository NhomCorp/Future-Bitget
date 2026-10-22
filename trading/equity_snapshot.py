"""Build risk-engine equity features from a GET-only Bitget account snapshot.

Missing, stale, or unparsable equity does not invent numbers. The caller must
pass the resulting features into the risk engine; this module never dispatches
orders and never talks to the frontend.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from ai_proposal.schema import DecisionOpportunitySnapshot
from trader.bitget_readonly import BitgetAdapterError, LiveModeDisabled, MissingReadOnlyCredentials

from .equity_store import EquityStore, SOURCE_READONLY_DEMO, normalize_timestamp, utc_day_start


DRAWDOWN_REFERENCES = frozenset({"equity_peak", "day_start", "policy_start"})
DRAWDOWN_UNITS = frozenset({"usdt", "pct"})
EQUITY_FEATURE_KEYS = (
    "daily_loss",
    "day_start_equity",
    "daily_loss_at",
    "drawdown",
    "drawdown_unit",
    "current_equity",
    "equity_as_of",
)


def parse_account_equity(payload: Any) -> Decimal | None:
    """Return USDT accountEquity when the payload matches the local GET contract."""
    if isinstance(payload, Mapping):
        rows: list[Any] = [payload]
    elif isinstance(payload, list):
        rows = payload
    else:
        return None
    chosen: Mapping[str, Any] | None = None
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        coin = str(row.get("marginCoin") or row.get("margin_coin") or "").strip().upper()
        if coin == "USDT":
            chosen = row
            break
    if chosen is None:
        first = rows[0] if rows else None
        chosen = first if isinstance(first, Mapping) else None
    if chosen is None:
        return None
    raw = chosen.get("accountEquity")
    if raw is None or raw == "":
        return None
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return None
    if not value.is_finite() or value <= 0:
        return None
    return value


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(normalize_timestamp(value, "now").replace("Z", "+00:00"))


@dataclass(frozen=True)
class EquitySnapshotRecord:
    current_equity: Decimal | None
    day_start_equity: Decimal | None
    daily_loss: Decimal | None
    daily_loss_at: str | None
    drawdown: Decimal | None
    drawdown_unit: str | None
    drawdown_reference: str | None
    equity_as_of: str | None
    stale: bool
    complete: bool
    reason_codes: tuple[str, ...]
    source: str = SOURCE_READONLY_DEMO

    def features_dict(self) -> dict[str, str]:
        features: dict[str, str] = {}
        if self.current_equity is not None:
            features["current_equity"] = format(self.current_equity, "f")
        if self.day_start_equity is not None:
            features["day_start_equity"] = format(self.day_start_equity, "f")
        if self.daily_loss is not None:
            features["daily_loss"] = format(self.daily_loss, "f")
        if self.daily_loss_at is not None:
            features["daily_loss_at"] = self.daily_loss_at
        if self.drawdown is not None:
            features["drawdown"] = format(self.drawdown, "f")
        if self.drawdown_unit is not None:
            features["drawdown_unit"] = self.drawdown_unit
        if self.equity_as_of is not None:
            features["equity_as_of"] = self.equity_as_of
        return features

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_equity": None if self.current_equity is None else format(self.current_equity, "f"),
            "day_start_equity": None if self.day_start_equity is None else format(self.day_start_equity, "f"),
            "daily_loss": None if self.daily_loss is None else format(self.daily_loss, "f"),
            "daily_loss_at": self.daily_loss_at,
            "drawdown": None if self.drawdown is None else format(self.drawdown, "f"),
            "drawdown_unit": self.drawdown_unit,
            "drawdown_reference": self.drawdown_reference,
            "equity_as_of": self.equity_as_of,
            "stale": self.stale,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
            "source": self.source,
        }


def _incomplete(
    reasons: list[str],
    *,
    drawdown_unit: str | None = None,
    drawdown_reference: str | None = None,
    stale: bool = False,
    equity_as_of: str | None = None,
) -> EquitySnapshotRecord:
    unique = tuple(dict.fromkeys(reasons))
    return EquitySnapshotRecord(
        current_equity=None,
        day_start_equity=None,
        daily_loss=None,
        daily_loss_at=None,
        drawdown=None,
        drawdown_unit=drawdown_unit,
        drawdown_reference=drawdown_reference,
        equity_as_of=equity_as_of,
        stale=stale or "EQUITY_STALE" in unique,
        complete=False,
        reason_codes=unique,
    )


def _drawdown(
    current: Decimal,
    reference_equity: Decimal | None,
    unit: str,
) -> Decimal | None:
    if reference_equity is None or reference_equity <= 0:
        return None
    drop = reference_equity - current
    if drop < 0:
        drop = Decimal("0")
    if unit == "usdt":
        return drop
    return (drop / reference_equity) * Decimal("100")


def capture_equity_snapshot(
    adapter: Any,
    store: EquityStore,
    *,
    max_age_seconds: int,
    now: str,
    drawdown_unit: str,
    drawdown_reference: str,
    captured_at: str | None = None,
    tags: tuple[str, ...] = (),
) -> EquitySnapshotRecord:
    """GET account equity, append a local row, and compute fail-closed features."""
    unit = str(drawdown_unit or "").strip().lower()
    reference = str(drawdown_reference or "").strip().lower()
    unit_ok = unit if unit in DRAWDOWN_UNITS else None
    reference_ok = reference if reference in DRAWDOWN_REFERENCES else None
    if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, int) or max_age_seconds < 0:
        return _incomplete(["EQUITY_STALE"], drawdown_unit=unit_ok, drawdown_reference=reference_ok, stale=True)
    try:
        now_stamp = normalize_timestamp(now, "now")
        as_of = normalize_timestamp(captured_at, "captured_at") if captured_at else now_stamp
    except Exception:
        return _incomplete(["EQUITY_STALE"], drawdown_unit=unit_ok, drawdown_reference=reference_ok, stale=True)

    reasons: list[str] = []
    if unit_ok is None:
        reasons.append("DRAWDOWN_UNIT_INVALID")
    if reference_ok is None:
        reasons.append("DRAWDOWN_REFERENCE_MISSING")

    try:
        payload = adapter.account()
    except LiveModeDisabled:
        return _incomplete(["EQUITY_LIVE_DISABLED", *reasons], drawdown_unit=unit_ok, drawdown_reference=reference_ok)
    except MissingReadOnlyCredentials:
        return _incomplete(
            ["EQUITY_CREDENTIALS_MISSING", *reasons],
            drawdown_unit=unit_ok,
            drawdown_reference=reference_ok,
        )
    except BitgetAdapterError:
        return _incomplete(["EQUITY_FETCH_FAILED", *reasons], drawdown_unit=unit_ok, drawdown_reference=reference_ok)
    except Exception:
        return _incomplete(["EQUITY_FETCH_FAILED", *reasons], drawdown_unit=unit_ok, drawdown_reference=reference_ok)

    current = parse_account_equity(payload)
    if current is None:
        return _incomplete(
            ["EQUITY_PARSE_FAILED", *reasons],
            drawdown_unit=unit_ok,
            drawdown_reference=reference_ok,
            equity_as_of=as_of,
        )

    store.append(as_of, current, source=SOURCE_READONLY_DEMO, tags=tags)

    age = (_parse_datetime(now_stamp) - _parse_datetime(as_of)).total_seconds()
    stale = age > max_age_seconds or age < 0
    if stale:
        reasons.append("EQUITY_STALE")

    day_start_row = store.last_before(utc_day_start(now_stamp))
    day_start = None if day_start_row is None else day_start_row.equity
    if day_start is None:
        reasons.append("DAY_START_MISSING")
        daily_loss = None
        daily_loss_at = None
    else:
        daily_loss = day_start - current
        if daily_loss < 0:
            daily_loss = Decimal("0")
        daily_loss_at = now_stamp

    drawdown = None
    if unit_ok is not None and reference_ok is not None:
        if reference_ok == "equity_peak":
            ref_equity = store.max_equity()
        elif reference_ok == "day_start":
            ref_equity = day_start
        else:
            tagged = store.last_tagged("policy_start")
            ref_equity = None if tagged is None else tagged.equity
        if ref_equity is None:
            if reference_ok == "day_start":
                if "DAY_START_MISSING" not in reasons:
                    reasons.append("DAY_START_MISSING")
            else:
                reasons.append("DRAWDOWN_REFERENCE_MISSING")
        else:
            drawdown = _drawdown(current, ref_equity, unit_ok)

    complete = (
        current is not None
        and day_start is not None
        and daily_loss is not None
        and daily_loss_at is not None
        and drawdown is not None
        and unit_ok is not None
        and reference_ok is not None
        and not stale
    )
    unique = tuple(dict.fromkeys(reasons))
    return EquitySnapshotRecord(
        current_equity=current,
        day_start_equity=day_start,
        daily_loss=daily_loss,
        daily_loss_at=daily_loss_at,
        drawdown=drawdown,
        drawdown_unit=unit_ok,
        drawdown_reference=reference_ok,
        equity_as_of=as_of,
        stale=stale,
        complete=complete,
        reason_codes=unique,
    )


def merge_into_snapshot(
    snapshot: DecisionOpportunitySnapshot,
    record: EquitySnapshotRecord,
) -> DecisionOpportunitySnapshot:
    """Overwrite equity feature keys without dropping consecutive_losses or other fields."""
    features = dict(snapshot.features)
    for key in EQUITY_FEATURE_KEYS:
        features.pop(key, None)
    features.update(record.features_dict())
    return replace(snapshot, features=features)
