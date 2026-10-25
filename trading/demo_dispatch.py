"""Demo-only dispatcher for approved paper intents.

Default is dry-run. Live env and ``GROK_TRADER_ALLOW_LIVE`` are refused.
Paper scan may call this for symbols in the mandate whitelist when the CLI
passes ``--place-orders --i-confirm-demo``. Protect clock does not call it.
Demo cycle may call ``kill_symbol`` when protect triggers, with the same flags.
Cancel, close/reduce, TPSL-on-open and GET reconcile are in scope.
WebSocket is out of scope.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
from typing import Any, Callable, Iterable, Mapping, Sequence

from trader.bitget_readonly import (
    API_BASE,
    BitgetAdapterError,
    BitgetResponseError,
    LiveModeDisabled,
    PRODUCT_TYPE,
    ReadOnlyBitgetAdapter,
    ReadOnlyCredentials,
    sign,
)
from trader.demo_verify import (
    CANCEL_ORDER_PATH,
    CANCEL_PLAN_PATH,
    CLOSE_POSITIONS_PATH,
    PLACE_ORDER_PATH,
    PLACE_TPSL_PATH,
    classify_dispatch,
    decimal_or_none,
    first_field,
    leftover_on_symbol,
    rows,
)
from .order_intent import PaperOrderIntent
from .reconcile import ReconcileObservation

Poster = Callable[[PaperOrderIntent], Mapping[str, Any]]
TpslPoster = Callable[[PaperOrderIntent], Mapping[str, Any]]
QueryFn = Callable[[PaperOrderIntent], Mapping[str, Any]]
Transport = Callable[[str, str, Mapping[str, str], str | None, float], Mapping[str, Any]]
PathPoster = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]

REASON_WHITELIST_EMPTY = "WHITELIST_EMPTY"
REASON_SYMBOL_NOT_IN_WHITELIST = "SYMBOL_NOT_IN_WHITELIST"
REASON_DEMO_CONFIRM = "DEMO_CONFIRM_REQUIRED"
REASON_DRY_RUN = "DRY_RUN"
REASON_POST_ERROR = "POST_ERROR"
REASON_NOTHING_TO_KILL = "NOTHING_TO_KILL"

DEFAULT_POS_MODE = "hedge_mode"


class DemoDispatchError(RuntimeError):
    """Raised when Demo dispatch cannot run safely."""


@dataclass(frozen=True)
class DemoDispatchResult:
    result: str
    dry_run: bool
    posted: bool
    client_oid: str
    reason_code: str | None = None
    dispatch: str | None = None
    tpsl_dispatch: str | None = None
    tpsl_client_oid: str | None = None
    reconcile: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "client_oid": self.client_oid,
            "dispatch": self.dispatch,
            "dry_run": self.dry_run,
            "exchange_post": self.posted,
            "reason_code": self.reason_code,
            "reconcile": self.reconcile,
            "result": self.result,
            "tpsl_client_oid": self.tpsl_client_oid,
            "tpsl_dispatch": self.tpsl_dispatch,
        }


@dataclass(frozen=True)
class DemoKillResult:
    symbol: str
    dry_run: bool
    posted: bool
    cancelled: int
    closed: int
    leftover_clear: bool
    reason_code: str | None = None
    results: tuple[DemoDispatchResult, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "cancelled": self.cancelled,
            "closed": self.closed,
            "dry_run": self.dry_run,
            "exchange_post": self.posted,
            "leftover_clear": self.leftover_clear,
            "reason_code": self.reason_code,
            "results": [item.to_dict() for item in self.results[:12]],
            "symbol": self.symbol,
        }


def _env_mode(environ: Mapping[str, str] | None) -> str:
    import os

    env = os.environ if environ is None else environ
    return str(env.get("BITGET_ENV", "demo")).strip().lower()


def _refuse_live(environ: Mapping[str, str] | None) -> None:
    import os

    env = os.environ if environ is None else environ
    if str(env.get("GROK_TRADER_ALLOW_LIVE", "")).strip() == "1":
        raise LiveModeDisabled("demo dispatch refuses GROK_TRADER_ALLOW_LIVE")
    if _env_mode(environ) in {"live", "production", "prod"}:
        raise LiveModeDisabled("demo dispatch is Demo-only; live mode is disabled")


def normalize_whitelist(allowed_symbols: Sequence[str] | None) -> tuple[str, ...]:
    """Return unique uppercase symbols. Empty means no pair is tradable."""
    seen: list[str] = []
    for raw in allowed_symbols or ():
        symbol = str(raw).strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.append(symbol)
    return tuple(seen)


def tpsl_client_oid(entry_oid: str) -> str:
    digest = hashlib.sha256(f"{entry_oid}\x1ftpsl".encode("utf-8")).hexdigest()[:24]
    return f"ai-{digest}"


def _blocked(intent: PaperOrderIntent, reason_code: str) -> DemoDispatchResult:
    return DemoDispatchResult(
        result="BLOCKED",
        dry_run=True,
        posted=False,
        client_oid=intent.client_oid,
        reason_code=reason_code,
    )


def intent_to_place_body(
    intent: PaperOrderIntent,
    *,
    pos_mode: str = DEFAULT_POS_MODE,
) -> dict[str, Any]:
    """Map a paper intent to a Demo place-order body. Does not send."""
    hedge = pos_mode == "hedge_mode"
    if intent.reduce_only:
        if hedge:
            side = "buy" if intent.side == "long" else "sell"
            trade_side = "close"
            reduce_only = False
        else:
            side = "sell" if intent.side == "long" else "buy"
            trade_side = None
            reduce_only = True
    else:
        side = "buy" if intent.side == "long" else "sell"
        trade_side = "open" if hedge else None
        reduce_only = False
    body: dict[str, Any] = {
        "symbol": intent.symbol.upper(),
        "productType": PRODUCT_TYPE,
        "marginMode": "isolated",
        "marginCoin": "USDT",
        "size": format(intent.quantity, "f"),
        "side": side,
        "orderType": intent.order_type,
        "clientOid": intent.client_oid,
        "force": "gtc" if intent.order_type == "limit" else "ioc",
    }
    if intent.order_type == "limit":
        body["price"] = format(intent.price, "f")
    if trade_side:
        body["tradeSide"] = trade_side
    if reduce_only:
        body["reduceOnly"] = "YES"
    return body


def intent_to_cancel_body(intent: PaperOrderIntent) -> dict[str, Any]:
    """Cancel the exchange order identified by ``intent.client_oid``."""
    return {
        "symbol": intent.symbol.upper(),
        "productType": PRODUCT_TYPE,
        "marginCoin": "USDT",
        "clientOid": intent.client_oid,
    }


def intent_to_tpsl_body(
    intent: PaperOrderIntent,
    *,
    plan_type: str = "pos_loss",
) -> dict[str, Any] | None:
    """Map entry stop_loss to a Demo TPSL body. Does not send."""
    stop = str(intent.stop_loss or "").strip()
    if not stop or intent.reduce_only or intent.order_role in {"cancel", "adjust_sl"}:
        return None
    body: dict[str, Any] = {
        "symbol": intent.symbol.upper(),
        "productType": PRODUCT_TYPE,
        "marginCoin": "USDT",
        "planType": plan_type,
        "triggerType": "mark_price",
        "triggerPrice": stop,
        "executePrice": "0",
        "holdSide": intent.side,
        "clientOid": tpsl_client_oid(intent.client_oid),
    }
    if plan_type == "loss_plan":
        body["size"] = format(intent.quantity, "f")
    return body


def _http_transport(
    method: str,
    request_path: str,
    headers: Mapping[str, str],
    body: str | None,
    timeout: float,
    *,
    base_url: str,
) -> Mapping[str, Any]:
    import urllib.error
    import urllib.request

    request = urllib.request.Request(
        base_url.rstrip("/") + request_path,
        data=body.encode() if body else None,
        method=method,
        headers=dict(headers),
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            result = json.loads(exc.read().decode()[:1000])
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise BitgetAdapterError(f"Bitget HTTP error {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise BitgetAdapterError(f"Bitget request failed: {type(exc).__name__}") from exc
    if not isinstance(result, Mapping):
        raise BitgetAdapterError("Bitget response is not an object")
    return result


def make_path_poster(
    *,
    environ: Mapping[str, str] | None = None,
    credentials: ReadOnlyCredentials | None = None,
    transport: Transport | None = None,
    timeout: float = 15.0,
    clock: Callable[[], float] | None = None,
    base_url: str = API_BASE,
) -> PathPoster:
    """POST an arbitrary Demo path. Credentials load on first call, never live."""
    _refuse_live(environ)

    def poster(path: str, body: Mapping[str, Any]) -> Mapping[str, Any]:
        _refuse_live(environ)
        creds = credentials if credentials is not None else ReadOnlyCredentials.from_env(environ)
        payload = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
        timestamp = str(int((clock or __import__("time").time)() * 1000))
        headers = {
            "locale": "en-US",
            "Content-Type": "application/json",
            "paptrading": "1",
            "ACCESS-KEY": creds.api_key,
            "ACCESS-SIGN": sign(creds.api_secret, timestamp, "POST", path, payload),
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": creds.passphrase,
        }
        try:
            sender = transport or (
                lambda method, request_path, hdrs, raw, wait: _http_transport(
                    method, request_path, hdrs, raw, wait, base_url=base_url
                )
            )
            result = sender("POST", path, headers, payload, timeout)
        except (BitgetAdapterError, TimeoutError, OSError) as exc:
            name = type(exc).__name__
            if "Timeout" in name or "timeout" in str(exc).lower():
                return {"dispatch": "UNKNOWN", "timeout": True, "sent": True}
            return {"dispatch": "UNKNOWN", "unparseable": True, "sent": True, "error": name}
        if not isinstance(result, Mapping):
            return {"dispatch": "UNKNOWN", "unparseable": True, "sent": True}
        return {
            "dispatch": classify_dispatch(sent=True, response=result),
            "sent": True,
            "response_code": result.get("code"),
            "response": result,
        }

    return poster


def make_demo_poster(
    *,
    environ: Mapping[str, str] | None = None,
    credentials: ReadOnlyCredentials | None = None,
    transport: Transport | None = None,
    timeout: float = 15.0,
    clock: Callable[[], float] | None = None,
    base_url: str = API_BASE,
    pos_mode: str = DEFAULT_POS_MODE,
) -> Poster:
    """Build a Demo poster. Cancel uses cancel-order; others use place-order."""
    sender = make_path_poster(
        environ=environ,
        credentials=credentials,
        transport=transport,
        timeout=timeout,
        clock=clock,
        base_url=base_url,
    )

    def poster(intent: PaperOrderIntent) -> Mapping[str, Any]:
        if intent.order_role == "cancel":
            return sender(CANCEL_ORDER_PATH, intent_to_cancel_body(intent))
        return sender(PLACE_ORDER_PATH, intent_to_place_body(intent, pos_mode=pos_mode))

    return poster


def make_tpsl_poster(
    *,
    environ: Mapping[str, str] | None = None,
    credentials: ReadOnlyCredentials | None = None,
    transport: Transport | None = None,
    timeout: float = 15.0,
    clock: Callable[[], float] | None = None,
    base_url: str = API_BASE,
) -> TpslPoster:
    """POST pos_loss, then loss_plan if rejected. Never live."""
    sender = make_path_poster(
        environ=environ,
        credentials=credentials,
        transport=transport,
        timeout=timeout,
        clock=clock,
        base_url=base_url,
    )

    def poster(intent: PaperOrderIntent) -> Mapping[str, Any]:
        body = intent_to_tpsl_body(intent, plan_type="pos_loss")
        if body is None:
            return {"dispatch": "VERIFIED_NOT_RECEIVED", "sent": False}
        placed = sender(PLACE_TPSL_PATH, body)
        if placed.get("dispatch") == "REJECTED":
            fallback = intent_to_tpsl_body(intent, plan_type="loss_plan")
            if fallback is not None:
                placed = sender(PLACE_TPSL_PATH, fallback)
                placed = {**placed, "plan_type": "loss_plan"}
            else:
                placed = {**placed, "plan_type": "pos_loss"}
        else:
            placed = {**placed, "plan_type": "pos_loss"}
        placed["tpsl_client_oid"] = tpsl_client_oid(intent.client_oid)
        return placed

    return poster


def make_order_query(
    *,
    environ: Mapping[str, str] | None = None,
    credentials: ReadOnlyCredentials | None = None,
    adapter: ReadOnlyBitgetAdapter | None = None,
) -> QueryFn:
    """GET order detail by clientOid. Timeout/error → UNKNOWN, never compensates."""
    _refuse_live(environ)

    def query(intent: PaperOrderIntent) -> Mapping[str, Any]:
        _refuse_live(environ)
        client = adapter or ReadOnlyBitgetAdapter(credentials=credentials, environ=environ)
        try:
            data = client.order_detail(intent.symbol, client_oid=intent.client_oid)
        except BitgetResponseError:
            return {"dispatch": "NOT_FOUND", "timeout": False, "data": None}
        except (BitgetAdapterError, TimeoutError, OSError) as exc:
            name = type(exc).__name__
            timed = "Timeout" in name or "timeout" in str(exc).lower()
            return {"dispatch": "UNKNOWN", "timeout": timed, "data": None, "error": name}
        if data in (None, "", [], {}):
            return {"dispatch": "NOT_FOUND", "timeout": False, "data": None}
        return {"dispatch": "FOUND", "timeout": False, "data": data}

    return query


def observation_from_query(intent: PaperOrderIntent, payload: Mapping[str, Any]) -> ReconcileObservation:
    """Turn a GET order-detail payload into a local paper observation."""
    if payload.get("timeout") or payload.get("dispatch") == "UNKNOWN":
        return ReconcileObservation(client_oid=intent.client_oid, timeout=True)
    if payload.get("dispatch") == "NOT_FOUND":
        return ReconcileObservation(client_oid=intent.client_oid, found=False, filled_quantity=Decimal("0"))
    data = payload.get("data")
    status = str(first_field(data, "status", "state") or "").lower()
    filled = decimal_or_none(first_field(data, "accBaseVolume", "baseVolume", "filledQty", "executeQty"))
    if filled is None:
        filled = Decimal("0")
    if status in {"canceled", "cancelled"}:
        return ReconcileObservation(client_oid=intent.client_oid, found=False, filled_quantity=filled)
    return ReconcileObservation(client_oid=intent.client_oid, found=True, filled_quantity=filled)


def _post_intent(
    intent: PaperOrderIntent,
    *,
    poster: Poster,
) -> DemoDispatchResult:
    try:
        payload = poster(intent)
    except LiveModeDisabled:
        raise
    except Exception:
        return DemoDispatchResult(
            result="UNKNOWN",
            dry_run=False,
            posted=True,
            client_oid=intent.client_oid,
            reason_code=REASON_POST_ERROR,
            dispatch="UNKNOWN",
        )
    dispatch = str(payload.get("dispatch") or "UNKNOWN")
    return DemoDispatchResult(
        result="POSTED" if dispatch == "FOUND" else dispatch,
        dry_run=False,
        posted=True,
        client_oid=intent.client_oid,
        dispatch=dispatch,
    )


def _attach_tpsl(
    result: DemoDispatchResult,
    intent: PaperOrderIntent,
    tpsl_poster: TpslPoster | None,
) -> DemoDispatchResult:
    if tpsl_poster is None or intent_to_tpsl_body(intent) is None:
        return result
    if result.dispatch != "FOUND":
        return result
    try:
        payload = tpsl_poster(intent)
    except LiveModeDisabled:
        raise
    except Exception:
        return DemoDispatchResult(
            **{**result.__dict__, "tpsl_dispatch": "UNKNOWN", "tpsl_client_oid": tpsl_client_oid(intent.client_oid)}
        )
    return DemoDispatchResult(
        **{
            **result.__dict__,
            "tpsl_dispatch": str(payload.get("dispatch") or "UNKNOWN"),
            "tpsl_client_oid": str(payload.get("tpsl_client_oid") or tpsl_client_oid(intent.client_oid)),
        }
    )


def dispatch_intent(
    intent: PaperOrderIntent,
    *,
    confirm_demo: bool = False,
    dry_run: bool = True,
    environ: Mapping[str, str] | None = None,
    poster: Poster | None = None,
    tpsl_poster: TpslPoster | None = None,
    allowed_symbols: Sequence[str] | None = None,
    pos_mode: str = DEFAULT_POS_MODE,
) -> DemoDispatchResult:
    """Dispatch one paper intent to Demo or return dry-run. Never live.

    Symbols outside the whitelist, and an empty whitelist, never POST.
    ``adjust_sl`` stays dry-run. Cancel and close/reduce POST when opted in.
    """
    _refuse_live(environ)
    whitelist = normalize_whitelist(allowed_symbols)
    if not whitelist:
        return _blocked(intent, REASON_WHITELIST_EMPTY)
    if intent.symbol.upper() not in whitelist:
        return _blocked(intent, REASON_SYMBOL_NOT_IN_WHITELIST)
    if not confirm_demo:
        return _blocked(intent, REASON_DEMO_CONFIRM)
    if dry_run or intent.order_role == "adjust_sl":
        return DemoDispatchResult(
            result="DRY_RUN",
            dry_run=True,
            posted=False,
            client_oid=intent.client_oid,
            reason_code=REASON_DRY_RUN,
            dispatch="VERIFIED_NOT_RECEIVED",
        )
    if poster is None:
        raise DemoDispatchError("poster is required when dry_run is false")
    del pos_mode
    result = _post_intent(intent, poster=poster)
    return _attach_tpsl(result, intent, tpsl_poster)


def dispatch_intents(
    intents: Iterable[PaperOrderIntent],
    *,
    allowed_symbols: Sequence[str] | None,
    confirm_demo: bool = False,
    dry_run: bool = True,
    environ: Mapping[str, str] | None = None,
    poster: Poster | None = None,
    tpsl_poster: TpslPoster | None = None,
    pos_mode: str = DEFAULT_POS_MODE,
) -> tuple[DemoDispatchResult, ...]:
    """Dispatch each intent independently. One failure does not invent a retry."""
    return tuple(
        dispatch_intent(
            intent,
            confirm_demo=confirm_demo,
            dry_run=dry_run,
            environ=environ,
            poster=poster,
            tpsl_poster=tpsl_poster,
            allowed_symbols=allowed_symbols,
            pos_mode=pos_mode,
        )
        for intent in intents
    )


def _pending_oids(pending: Any, symbol: str) -> tuple[str, ...]:
    wanted = symbol.upper()
    found: list[str] = []
    for row in rows(pending):
        if str(row.get("symbol") or "").upper() != wanted:
            continue
        oid = str(row.get("clientOid") or "").strip()
        if oid and oid not in found:
            found.append(oid)
    return tuple(found)


def _position_legs(positions: Any, symbol: str) -> tuple[tuple[str, Decimal], ...]:
    wanted = symbol.upper()
    legs: list[tuple[str, Decimal]] = []
    for row in rows(positions):
        if str(row.get("symbol") or "").upper() != wanted:
            continue
        size = decimal_or_none(row.get("total") or row.get("available") or row.get("size"))
        if size is None or size <= 0:
            continue
        side = str(row.get("holdSide") or row.get("posSide") or row.get("side") or "").strip().lower()
        if side not in {"long", "short"}:
            continue
        legs.append((side, size))
    return tuple(legs)


def _cancel_intent(symbol: str, client_oid: str) -> PaperOrderIntent:
    return PaperOrderIntent(
        client_oid=client_oid,
        zone_id="demo-kill",
        decision_id=f"kill-cancel-{client_oid}",
        risk_check_id="kill",
        mandate_id="demo-kill",
        mandate_version=1,
        symbol=symbol,
        side="long",
        quantity=Decimal("0.0001"),
        price=Decimal("1"),
        stop_loss=None,
        take_profit=None,
        order_role="cancel",
        reduce_only=False,
    )


def _close_intent(symbol: str, side: str, quantity: Decimal, decision_id: str) -> PaperOrderIntent:
    return PaperOrderIntent(
        client_oid=tpsl_client_oid(decision_id),
        zone_id="demo-kill",
        decision_id=decision_id,
        risk_check_id="kill",
        mandate_id="demo-kill",
        mandate_version=1,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=Decimal("1"),
        stop_loss=None,
        take_profit=None,
        order_type="market",
        order_role="reduce",
        reduce_only=True,
    )


def kill_symbol(
    symbol: str,
    *,
    allowed_symbols: Sequence[str] | None,
    confirm_demo: bool = False,
    dry_run: bool = True,
    environ: Mapping[str, str] | None = None,
    poster: Poster | None = None,
    path_poster: PathPoster | None = None,
    adapter: ReadOnlyBitgetAdapter | None = None,
    pending: Any = None,
    positions: Any = None,
    pos_mode: str = DEFAULT_POS_MODE,
) -> DemoKillResult:
    """Cancel pending orders and flatten Demo positions on one whitelist symbol.

    Independent of AI. Live is refused. Empty leftover is success; leftover after
    POST is recorded, not invented away.
    """
    _refuse_live(environ)
    wanted = str(symbol or "").strip().upper()
    whitelist = normalize_whitelist(allowed_symbols)
    dummy = _cancel_intent(wanted or "BTCUSDT", "kill-blocked")
    if not whitelist:
        blocked = _blocked(dummy, REASON_WHITELIST_EMPTY)
        return DemoKillResult(wanted, True, False, 0, 0, False, REASON_WHITELIST_EMPTY, (blocked,))
    if not wanted or wanted not in whitelist:
        blocked = _blocked(dummy, REASON_SYMBOL_NOT_IN_WHITELIST)
        return DemoKillResult(wanted, True, False, 0, 0, False, REASON_SYMBOL_NOT_IN_WHITELIST, (blocked,))
    if not confirm_demo:
        blocked = _blocked(dummy, REASON_DEMO_CONFIRM)
        return DemoKillResult(wanted, True, False, 0, 0, False, REASON_DEMO_CONFIRM, (blocked,))

    client = adapter
    if pending is None or positions is None:
        if client is None:
            client = ReadOnlyBitgetAdapter(environ=environ)
        if pending is None:
            pending = client.pending_orders()
        if positions is None:
            positions = client.positions()

    oids = _pending_oids(pending, wanted)
    legs = _position_legs(positions, wanted)
    if dry_run:
        planned = len(oids) + len(legs)
        leftover = leftover_on_symbol(positions, pending, wanted)
        return DemoKillResult(
            symbol=wanted,
            dry_run=True,
            posted=False,
            cancelled=len(oids),
            closed=len(legs),
            leftover_clear=bool(leftover.get("clear")),
            reason_code=REASON_DRY_RUN if planned else REASON_NOTHING_TO_KILL,
            results=(),
        )
    if poster is None:
        raise DemoDispatchError("poster is required when dry_run is false")

    results: list[DemoDispatchResult] = []
    for oid in oids:
        results.append(
            dispatch_intent(
                _cancel_intent(wanted, oid),
                confirm_demo=True,
                dry_run=False,
                environ=environ,
                poster=poster,
                allowed_symbols=whitelist,
                pos_mode=pos_mode,
            )
        )
    for index, (side, qty) in enumerate(legs, start=1):
        results.append(
            dispatch_intent(
                _close_intent(wanted, side, qty, f"kill-close-{wanted}-{side}-{index}"),
                confirm_demo=True,
                dry_run=False,
                environ=environ,
                poster=poster,
                allowed_symbols=whitelist,
                pos_mode=pos_mode,
            )
        )

    if client is None:
        client = ReadOnlyBitgetAdapter(environ=environ)
    leftover = leftover_on_symbol(client.positions(), client.pending_orders(), wanted)
    if leftover.get("positions") and path_poster is not None:
        for side, _qty in _position_legs(client.positions(), wanted):
            path_poster(
                CLOSE_POSITIONS_PATH,
                {"symbol": wanted, "productType": PRODUCT_TYPE, "holdSide": side},
            )
        leftover = leftover_on_symbol(client.positions(), client.pending_orders(), wanted)
    if leftover.get("pending_orders") and path_poster is not None and hasattr(client, "plan_pending"):
        try:
            plans = client.plan_pending(wanted)
        except (BitgetAdapterError, BitgetResponseError, TimeoutError, OSError):
            plans = []
        for row in rows(plans):
            oid = str(row.get("clientOid") or "").strip()
            if not oid:
                continue
            path_poster(
                CANCEL_PLAN_PATH,
                {
                    "symbol": wanted,
                    "productType": PRODUCT_TYPE,
                    "planType": str(row.get("planType") or "profit_loss"),
                    "orderIdList": [{"clientOid": oid}],
                },
            )
        leftover = leftover_on_symbol(client.positions(), client.pending_orders(), wanted)

    posted = any(item.posted for item in results)
    return DemoKillResult(
        symbol=wanted,
        dry_run=False,
        posted=posted,
        cancelled=len(oids),
        closed=len(legs),
        leftover_clear=bool(leftover.get("clear")),
        reason_code=None if leftover.get("clear") else "LEFTOVER",
        results=tuple(results),
    )
