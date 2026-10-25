"""One supervised Demo cycle: fresh GET, equity ledger, protect, then scan if due.

Protect clock still never POSTs. This module may call ``kill_symbol`` when
protect triggers, only with opt-in Demo flags. Scan still uses
``ScanDispatchOptions``. Live is refused by the dispatcher and adapter.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any, Callable, Mapping

from trader.bitget_readonly import BitgetAdapterError, LiveModeDisabled, MissingReadOnlyCredentials
from trader.demo_verify import decimal_or_none, first_field, rows
from trading.demo_dispatch import DemoKillResult, PathPoster, Poster, kill_symbol
from trading.equity_snapshot import EquitySnapshotRecord, capture_equity_snapshot, merge_into_snapshot
from trading.equity_store import EquityStore
from trading.decision_context import enrich_decision_features
from trading.frontend_mandate import ScanLimits, allowlist_scan_jobs, build_scan_snapshot, normalize_allowlist
from trading.paper_agent import PaperAgent
from trading.paper_scan import PaperScanResult, ScanDispatchOptions, tick as scan_tick
from trading.protect_clock import ProtectClockResult, ProtectObservation, tick as protect_tick
from trading.reconcile import ReconcileObservation

PROTECT_DISPATCH_EVENT = "PROTECT_DISPATCH"
DEFAULT_MAX_AGE_SECONDS = 120


class DemoCycleError(ValueError):
    """Raised when a Demo cycle cannot run safely."""


@dataclass(frozen=True)
class ProtectDispatchOptions:
    """Opt-in Demo flatten after a protect trigger. Default is dry-run."""

    confirm_demo: bool = False
    dry_run: bool = True
    poster: Poster | None = None
    path_poster: PathPoster | None = None
    environ: Mapping[str, str] | None = None
    adapter: Any = None


@dataclass(frozen=True)
class DemoCycleResult:
    snapshot_stale: bool
    equity: EquitySnapshotRecord | None
    protect: ProtectClockResult | None
    protect_kill: DemoKillResult | None
    scan: PaperScanResult | None

    def to_dict(self) -> dict[str, Any]:
        scan = {} if self.scan is None else self.scan.to_dict()
        kill = None if self.protect_kill is None else self.protect_kill.to_dict()
        posted = bool(scan.get("exchange_post")) or bool(kill and kill.get("exchange_post"))
        return {
            "action": scan.get("action") or "NO_TRADE",
            "dispatch_results": scan.get("dispatch_results") or [],
            "due": bool(scan.get("due")),
            "dry_run": not posted,
            "equity": None if self.equity is None else self.equity.to_dict(),
            "exchange_post": posted,
            "intent_client_oid": scan.get("intent_client_oid"),
            "intent_count": scan.get("intent_count") or 0,
            "next_due_at": scan.get("next_due_at"),
            "protect": None if self.protect is None else self.protect.to_dict(),
            "protect_kill": kill,
            "ran": bool(scan.get("ran")),
            "reason_code": scan.get("reason_code") or "CYCLE_RAN",
            "reviewed_at": scan.get("reviewed_at"),
            "snapshot_stale": self.snapshot_stale,
        }


def _append(store: Any, zone_id: str, event: str, payload: Mapping[str, Any]) -> None:
    store.append_agent_event(zone_id, event, dict(payload))


def _protect_flatten_settled(store: Any, zone_id: str) -> bool:
    getter = getattr(store, "agent_events", None)
    if getter is None:
        return False
    for event in reversed(list(getter(zone_id))):
        if event.get("event") != PROTECT_DISPATCH_EVENT:
            continue
        return bool(event.get("exchange_post") and event.get("leftover_clear"))
    return False


def observation_from_snapshot(
    raw: Mapping[str, Any],
    *,
    symbol: str,
    side: str,
    store: Any,
    stale: bool = False,
    kill_switch: bool = False,
) -> ProtectObservation:
    wanted = str(symbol or "").strip().upper()
    hold = str(side or "").strip().lower()
    ticker = raw.get("ticker") if isinstance(raw, Mapping) else None
    mark = decimal_or_none(first_field(ticker, "markPrice", "markPr", "indexPrice"))
    quantity = None
    realized = Decimal("0")
    unrealized = Decimal("0")
    fees = Decimal("0")
    for row in rows(raw.get("positions") if isinstance(raw, Mapping) else None):
        if str(row.get("symbol") or "").upper() != wanted:
            continue
        row_side = str(row.get("holdSide") or row.get("posSide") or row.get("side") or "").strip().lower()
        if row_side != hold:
            continue
        quantity = decimal_or_none(row.get("total") or row.get("available") or row.get("size"))
        realized = decimal_or_none(row.get("achievedProfits") or row.get("realizedPNL") or row.get("realizedPnl")) or Decimal("0")
        unrealized = decimal_or_none(row.get("unrealizedPL") or row.get("unrealizedPnl")) or Decimal("0")
        fees = decimal_or_none(row.get("totalFee") or row.get("fee")) or Decimal("0")
        if mark is None:
            mark = decimal_or_none(row.get("markPrice") or row.get("markPr"))
        break
    fills: list[ReconcileObservation] = []
    getter = getattr(store, "get_paper_intent", None)
    for row in rows(raw.get("fills") if isinstance(raw, Mapping) else None):
        oid = str(row.get("clientOid") or "").strip()
        if not oid or getter is None or getter(oid) is None:
            continue
        fills.append(
            ReconcileObservation(
                client_oid=oid,
                found=True,
                filled_quantity=decimal_or_none(row.get("baseVolume") or row.get("size") or row.get("fillQuantity")),
            )
        )
    unknown = bool(not stale and quantity is not None and quantity > 0 and mark is None)
    return ProtectObservation(
        mark_price=mark,
        realized_pnl=realized,
        unrealized_pnl=unrealized,
        fees=fees,
        fills=tuple(fills),
        unknown=unknown,
        kill_switch=kill_switch,
        stale=stale,
        position_quantity=quantity,
        position_side=None if quantity is None else hold,
    )


def _limits_from_snapshot(limits: ScanLimits, raw: Mapping[str, Any]) -> ScanLimits:
    ticker = raw.get("ticker") if isinstance(raw, Mapping) else None
    last = decimal_or_none(first_field(ticker, "lastPr", "markPrice", "markPr"))
    updated = limits
    if last is not None and last > 0:
        updated = replace(updated, ref_price=last)
    for row in rows(raw.get("positions") if isinstance(raw, Mapping) else None):
        if str(row.get("symbol") or "").upper() != limits.symbol:
            continue
        row_side = str(row.get("holdSide") or row.get("posSide") or row.get("side") or "").strip().lower()
        if row_side != limits.side:
            continue
        qty = decimal_or_none(row.get("total") or row.get("available") or row.get("size"))
        if qty is not None and qty > 0:
            updated = replace(updated, size=qty)
        break
    return updated


def _scan_features(equity: EquitySnapshotRecord, mandate: Any) -> dict[str, str]:
    features = equity.features_dict()
    features.setdefault("consecutive_losses", "0")
    if mandate.drawdown_unit:
        features.setdefault("drawdown_unit", str(mandate.drawdown_unit))
    return features


def maybe_flatten_on_protect(
    store: Any,
    *,
    zone_id: str,
    symbol: str,
    allowed_symbols: tuple[str, ...],
    protect: ProtectClockResult,
    options: ProtectDispatchOptions | None,
    now: str,
    pending: Any,
    positions: Any,
) -> DemoKillResult | None:
    if options is None or not protect.triggered:
        return None
    if _protect_flatten_settled(store, zone_id):
        return None
    result = kill_symbol(
        symbol,
        allowed_symbols=allowed_symbols,
        confirm_demo=options.confirm_demo,
        dry_run=options.dry_run,
        environ=options.environ,
        poster=options.poster,
        path_poster=options.path_poster,
        adapter=options.adapter,
        pending=pending,
        positions=positions,
    )
    _append(
        store,
        zone_id,
        PROTECT_DISPATCH_EVENT,
        {
            "cancelled": result.cancelled,
            "closed": result.closed,
            "dry_run": result.dry_run,
            "exchange_post": result.posted,
            "leftover_clear": result.leftover_clear,
            "observed_at": now,
            "reason_code": result.reason_code,
        },
    )
    return result


def _ticker_payload(adapter: Any, symbol: str) -> Any:
    getter = getattr(adapter, "public_ticker", None)
    if getter is None:
        fetched = adapter.snapshot(symbol=symbol)
        return fetched.get("ticker") if isinstance(fetched, Mapping) else None
    return getter(symbol)


def prices_from_adapter(adapter: Any, symbols: tuple[str, ...]) -> dict[str, Decimal]:
    """Collect last/mark per symbol. Missing or failed ticker is skipped, not invented."""
    prices: dict[str, Decimal] = {}
    for symbol in symbols:
        try:
            ticker = _ticker_payload(adapter, symbol)
        except LiveModeDisabled:
            raise
        except MissingReadOnlyCredentials:
            raise
        except (BitgetAdapterError, TimeoutError, OSError, TypeError, AttributeError):
            continue
        last = decimal_or_none(first_field(ticker, "lastPr", "markPrice", "markPr"))
        if last is not None and last > 0:
            prices[symbol] = last
    return prices


def run_cycle(
    *,
    adapter: Any,
    store: Any,
    equity_store: EquityStore,
    agent: PaperAgent,
    mandate: Any,
    limits: ScanLimits,
    now: str,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    kill_switch: bool = False,
    scan_dispatch: ScanDispatchOptions | None = None,
    protect_dispatch: ProtectDispatchOptions | None = None,
    prefetched: Mapping[str, Any] | None = None,
    equity: EquitySnapshotRecord | None = None,
) -> DemoCycleResult:
    """GET a fresh snapshot, append equity, protect, then scan if due."""
    stale = False
    raw: dict[str, Any] = {}
    if prefetched is not None:
        raw = dict(prefetched)
        stale = bool(prefetched.get("_stale"))
    else:
        try:
            fetched = adapter.snapshot(symbol=limits.symbol)
            if isinstance(fetched, Mapping):
                raw = dict(fetched)
        except LiveModeDisabled:
            raise
        except MissingReadOnlyCredentials:
            raise
        except (BitgetAdapterError, TimeoutError, OSError):
            stale = True
            raw = {}

    if equity is None:
        equity = capture_equity_snapshot(
            adapter,
            equity_store,
            max_age_seconds=max_age_seconds,
            now=now,
            drawdown_unit=str(mandate.drawdown_unit),
            drawdown_reference=str(mandate.drawdown_reference),
            account_payload=raw.get("account"),
            allow_day_start_bootstrap=True,
        )
    if equity.stale:
        stale = True

    fresh_limits = limits if stale else _limits_from_snapshot(limits, raw)
    snapshot = build_scan_snapshot(
        mandate,
        fresh_limits,
        now=now,
        features=_scan_features(equity, mandate),
    )
    snapshot = merge_into_snapshot(snapshot, equity)
    features = dict(snapshot.features)
    features.setdefault("consecutive_losses", "0")
    features = enrich_decision_features(
        features,
        symbol=limits.symbol,
        side=limits.side,
        now=now,
        adapter=adapter,
    )
    snapshot = replace(snapshot, features=features)

    observation = observation_from_snapshot(
        raw,
        symbol=limits.symbol,
        side=limits.side,
        store=store,
        stale=stale,
        kill_switch=kill_switch,
    )
    protect = protect_tick(store, mandate.zone_id, observation, now=now)
    protect_kill = maybe_flatten_on_protect(
        store,
        zone_id=mandate.zone_id,
        symbol=limits.symbol,
        allowed_symbols=tuple(mandate.allowed_symbols),
        protect=protect,
        options=protect_dispatch,
        now=now,
        pending=raw.get("pending_orders"),
        positions=raw.get("positions"),
    )
    scan = scan_tick(
        agent,
        snapshot,
        mandate,
        now=now,
        stale=stale,
        kill_switch=False,
        dispatch=scan_dispatch,
    )
    return DemoCycleResult(
        snapshot_stale=stale,
        equity=equity,
        protect=protect,
        protect_kill=protect_kill,
        scan=scan,
    )


def _merge_allowlist_payload(
    results: tuple[DemoCycleResult, ...],
    skipped: tuple[str, ...],
    jobs: tuple[ScanLimits, ...],
    zone_ids: tuple[str, ...],
) -> dict[str, Any]:
    pairs: list[dict[str, Any]] = []
    posted = False
    stale = False
    action = "NO_TRADE"
    reason = "NO_SCAN_PRICE" if skipped or not results else "CYCLE_RAN"
    equity = None
    for index, item in enumerate(results):
        payload = item.to_dict()
        job = jobs[index] if index < len(jobs) else None
        pairs.append(
            {
                "action": payload.get("action") or "NO_TRADE",
                "exchange_post": bool(payload.get("exchange_post")),
                "reason_code": payload.get("reason_code") or "",
                "side": "" if job is None else job.side,
                "symbol": "" if job is None else job.symbol,
                "zone_id": zone_ids[index] if index < len(zone_ids) else "",
            }
        )
        posted = posted or bool(payload.get("exchange_post"))
        stale = stale or bool(payload.get("snapshot_stale"))
        if equity is None:
            equity = payload.get("equity")
        step_action = str(payload.get("action") or "NO_TRADE")
        if step_action not in {"", "NO_TRADE", "HOLD"} and action in {"NO_TRADE", "HOLD"}:
            action = step_action
        if payload.get("reason_code"):
            reason = str(payload.get("reason_code"))
    if results and action == "NO_TRADE":
        action = str(results[-1].to_dict().get("action") or "NO_TRADE")
    if not results:
        reason = "NO_SCAN_PRICE" if skipped else "ALLOWLIST_EMPTY"
    return {
        "action": action,
        "dispatch_results": [
            row
            for item in results
            for row in (item.to_dict().get("dispatch_results") or [])
        ],
        "due": any(item.scan is not None and item.scan.due for item in results),
        "dry_run": not posted,
        "equity": equity,
        "exchange_post": posted,
        "intent_count": sum((item.to_dict().get("intent_count") or 0) for item in results),
        "pairs": pairs,
        "protect": None if not results or results[-1].protect is None else results[-1].protect.to_dict(),
        "protect_kill": None
        if not results or results[-1].protect_kill is None
        else results[-1].protect_kill.to_dict(),
        "ran": any(item.scan is not None and item.scan.ran for item in results),
        "reason_code": reason,
        "scanned": len(results),
        "skipped": list(skipped),
        "snapshot_stale": stale,
    }


def run_allowlist_cycle(
    *,
    adapter: Any,
    store: Any,
    equity_store: EquityStore,
    agent: PaperAgent,
    policy: Mapping[str, Any],
    limits: Mapping[str, Any],
    mandate_builder: Callable[[ScanLimits], Any],
    now: str,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    kill_switch: bool = False,
    scan_dispatch: ScanDispatchOptions | None = None,
    protect_dispatch: ProtectDispatchOptions | None = None,
) -> dict[str, Any]:
    """One Demo GET, one equity row, then protect/scan every approved pair."""
    stale = False
    raw: dict[str, Any] = {}
    try:
        fetched = adapter.snapshot()
        if isinstance(fetched, Mapping):
            raw = dict(fetched)
    except LiveModeDisabled:
        raise
    except MissingReadOnlyCredentials:
        raise
    except (BitgetAdapterError, TimeoutError, OSError):
        stale = True
        raw = {}

    allowlist = normalize_allowlist(policy)
    prices = {} if stale else prices_from_adapter(adapter, allowlist)
    jobs = allowlist_scan_jobs(policy, limits, positions=raw.get("positions"), prices=prices)
    skipped = tuple(symbol for symbol in allowlist if symbol not in prices)
    if not jobs:
        empty_equity = capture_equity_snapshot(
            adapter,
            equity_store,
            max_age_seconds=max_age_seconds,
            now=now,
            drawdown_unit=str(policy.get("drawdown_unit") or "pct"),
            drawdown_reference=str(policy.get("drawdown_reference") or "equity_peak"),
            account_payload=raw.get("account"),
            allow_day_start_bootstrap=True,
        )
        payload = _merge_allowlist_payload((), skipped, (), ())
        payload["allowed_symbols"] = list(allowlist)
        payload["equity"] = empty_equity.to_dict()
        payload["snapshot_stale"] = stale or empty_equity.stale
        payload["reason_code"] = "NO_SCAN_PRICE" if skipped or stale else "ALLOWLIST_EMPTY"
        return payload

    first_mandate = mandate_builder(jobs[0])
    equity = capture_equity_snapshot(
        adapter,
        equity_store,
        max_age_seconds=max_age_seconds,
        now=now,
        drawdown_unit=str(first_mandate.drawdown_unit),
        drawdown_reference=str(first_mandate.drawdown_reference),
        account_payload=raw.get("account"),
        allow_day_start_bootstrap=True,
    )
    results: list[DemoCycleResult] = []
    zone_ids: list[str] = []
    for job in jobs:
        mandate = mandate_builder(job)
        zone_ids.append(mandate.zone_id)
        ticker = None
        try:
            ticker = _ticker_payload(adapter, job.symbol)
        except (BitgetAdapterError, TimeoutError, OSError, TypeError, AttributeError, LiveModeDisabled, MissingReadOnlyCredentials):
            ticker = raw.get("ticker")
        merged = dict(raw)
        if ticker is not None:
            merged["ticker"] = ticker
        if stale:
            merged["_stale"] = True
        results.append(
            run_cycle(
                adapter=adapter,
                store=store,
                equity_store=equity_store,
                agent=agent,
                mandate=mandate,
                limits=job,
                now=now,
                max_age_seconds=max_age_seconds,
                kill_switch=kill_switch,
                scan_dispatch=scan_dispatch,
                protect_dispatch=protect_dispatch,
                prefetched=merged,
                equity=equity,
            )
        )
    payload = _merge_allowlist_payload(tuple(results), skipped, jobs, tuple(zone_ids))
    payload["allowed_symbols"] = list(allowlist)
    return payload


def run_loop(
    *,
    now_fn: Callable[[], str],
    sleep: Callable[[float], None],
    poll_seconds: float,
    max_ticks: int,
    **cycle_kwargs: Any,
) -> list[DemoCycleResult]:
    """Repeat ``run_cycle``. Sleep is injected; this is not a background daemon."""
    if max_ticks < 1:
        raise DemoCycleError("max_ticks must be >= 1")
    if poll_seconds <= 0:
        raise DemoCycleError("poll_seconds must be positive")
    results: list[DemoCycleResult] = []
    for index in range(max_ticks):
        results.append(run_cycle(now=now_fn(), **cycle_kwargs))
        if index + 1 < max_ticks:
            sleep(poll_seconds)
    return results
