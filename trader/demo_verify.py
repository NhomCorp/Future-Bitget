"""Demo verification harness for checklist D0-D15.

This module records redacted Bitget Demo evidence. It is not an order
dispatcher, does not open live, and does not change paper/AI autonomy.
GET is the default. POST is opt-in, Demo-only, and always sends
``paptrading: 1``. ``GROK_TRADER_ALLOW_LIVE`` blocks POST.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN
import hashlib
import json
import os
from typing import Any, Callable, Mapping

from trader.bitget_readonly import (
    API_BASE,
    PRODUCT_TYPE,
    BitgetAdapterError,
    BitgetResponseError,
    LiveModeDisabled,
    MissingReadOnlyCredentials,
    ReadOnlyBitgetAdapter,
    ReadOnlyCredentials,
    query_string,
    sign,
)
from trader.envfile import load_os_env_file


Transport = Callable[[str, str, Mapping[str, str], str | None, float], Mapping[str, Any]]

PLACE_ORDER_PATH = "/api/v2/mix/order/place-order"
CANCEL_ORDER_PATH = "/api/v2/mix/order/cancel-order"
ORDER_DETAIL_PATH = "/api/v2/mix/order/detail"
ACCOUNT_SYMBOL_PATH = "/api/v2/mix/account/account"

CASE_IDS = tuple(f"D{index}" for index in range(16))

VERDICTS = frozenset({"PASS", "FAIL", "BLOCKED", "UNKNOWN"})
DISPATCH_RESULTS = frozenset(
    {"FOUND", "REJECTED", "VERIFIED_NOT_RECEIVED", "UNKNOWN", "NOT_FOUND"}
)

SECRET_HEADER_KEYS = frozenset(
    {"access-key", "access-sign", "access-passphrase", "authorization"}
)
NUMERIC_REDACT_KEYS = frozenset(
    {
        "accountequity",
        "available",
        "availableequity",
        "crossedmargin",
        "crossedmaxavailable",
        "equity",
        "isolatedmargin",
        "isolatedmaxavailable",
        "locked",
        "maxopenposavailable",
        "unrealizedpl",
        "unrealizedpnl",
        "usdtequity",
        "assetamount",
    }
)
SECRET_VALUE_KEYS = frozenset(
    {"apikey", "api_key", "secret", "passphrase", "token", "password"}
)


class DemoVerifyError(RuntimeError):
    """Raised when the Demo verification harness cannot run safely."""


class PostDisabled(DemoVerifyError):
    """Raised when a POST is requested without Demo confirmations."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def verify_client_oid(zone_id: str, role: str, sequence: int) -> str:
    canonical = "\x1f".join((zone_id, role, str(sequence)))
    return "dvf-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def redact_id(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if len(text) <= 6:
        return text[0] + "…" + text[-1]
    return text[:4] + "…" + text[-4:]


def _is_secret_header(name: str) -> bool:
    lowered = name.lower()
    return lowered in SECRET_HEADER_KEYS or "key" in lowered or "sign" in lowered


def redact_headers(headers: Mapping[str, Any] | None) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in dict(headers or {}).items():
        redacted[key] = "[redacted]" if _is_secret_header(str(key)) else value
    return redacted


def redact_payload(value: Any, key: str | None = None) -> Any:
    lowered = (key or "").lower()
    if lowered in SECRET_VALUE_KEYS or lowered in SECRET_HEADER_KEYS:
        return "[redacted]"
    if lowered in {"orderid", "clientoid"}:
        return redact_id(value)
    if lowered in NUMERIC_REDACT_KEYS:
        return "present" if value not in (None, "") else "missing"
    if isinstance(value, Mapping):
        return {str(item_key): redact_payload(item, str(item_key)) for item_key, item in value.items()}
    if isinstance(value, list):
        return [redact_payload(item, key) for item in value]
    return value


def rows(payload: Any) -> list[Mapping[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]
    if isinstance(payload, Mapping):
        inner = payload.get("list")
        if inner is None:
            inner = payload.get("entrustedList")
        if isinstance(inner, list):
            return [item for item in inner if isinstance(item, Mapping)]
        if "entrustedList" in payload or "endId" in payload:
            return []
        return [payload]
    return []


def symbol_rows(payload: Any, symbol: str) -> list[Mapping[str, Any]]:
    wanted = symbol.upper()
    return [row for row in rows(payload) if str(row.get("symbol") or "").upper() == wanted]


def decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def nonzero(value: Any) -> bool:
    parsed = decimal_or_none(value)
    if parsed is None:
        return str(value or "").strip() not in {"", "0"}
    return parsed != 0


def first_field(payload: Any, *names: str) -> Any:
    for row in rows(payload):
        for name in names:
            if name in row and row[name] not in (None, ""):
                return row[name]
    return None


def pick_contract(payload: Any, symbol: str) -> Mapping[str, Any] | None:
    matches = symbol_rows(payload, symbol)
    if matches:
        return matches[0]
    items = rows(payload)
    return items[0] if len(items) == 1 else None


def tick_size(contract: Mapping[str, Any]) -> Decimal | None:
    place = decimal_or_none(contract.get("pricePlace"))
    step = decimal_or_none(contract.get("priceEndStep"))
    if place is None or step is None:
        return None
    return step * (Decimal(10) ** int(-place))


def round_price(price: Decimal, contract: Mapping[str, Any]) -> Decimal | None:
    tick = tick_size(contract)
    if tick is None or tick <= 0:
        return None
    return (price / tick).to_integral_value(rounding=ROUND_DOWN) * tick


def round_size(contract: Mapping[str, Any]) -> Decimal | None:
    lot = decimal_or_none(contract.get("sizeMultiplier"))
    minimum = decimal_or_none(contract.get("minTradeNum"))
    if lot is None or lot <= 0:
        return minimum
    if minimum is None:
        return lot
    steps = (minimum / lot).to_integral_value(rounding=ROUND_DOWN)
    sized = steps * lot
    return minimum if sized < minimum else sized


def classify_dispatch(
    *,
    sent: bool,
    timeout: bool = False,
    unparseable: bool = False,
    response: Mapping[str, Any] | None = None,
    found_on_exchange: bool | None = None,
) -> str:
    if not sent:
        return "VERIFIED_NOT_RECEIVED"
    if timeout or unparseable:
        return "UNKNOWN"
    code = None if response is None else response.get("code")
    if code not in (None, "00000"):
        return "REJECTED"
    if found_on_exchange is False:
        return "NOT_FOUND"
    if found_on_exchange is True:
        return "FOUND"
    if isinstance(response, Mapping) and code == "00000":
        data = response.get("data") if isinstance(response.get("data"), Mapping) else response
        if isinstance(data, Mapping) and (data.get("orderId") or data.get("clientOid")):
            return "FOUND"
    return "UNKNOWN"


@dataclass
class CaseResult:
    case_id: str
    verdict: str
    notes: str
    dispatch: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "case_id": self.case_id,
            "verdict": self.verdict,
            "notes": self.notes,
            "dispatch": self.dispatch,
            "evidence": redact_payload(self.evidence),
        }
        return payload


@dataclass
class VerifyReport:
    captured_at: str
    symbol: str
    zone_id: str
    cases: list[CaseResult]
    product_type: str = PRODUCT_TYPE
    paptrading: str = "1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "captured_at": self.captured_at,
            "symbol": self.symbol,
            "zone_id": self.zone_id,
            "product_type": self.product_type,
            "paptrading": self.paptrading,
            "cases": [case.to_dict() for case in self.cases],
            "summary": {
                case.case_id: case.verdict for case in self.cases
            },
        }


def write_evidence(path: str, report: VerifyReport) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


class DemoVerifyClient:
    """Demo-only GET/POST client for checklist evidence. Not a dispatcher."""

    def __init__(
        self,
        *,
        credentials: ReadOnlyCredentials | None = None,
        environ: Mapping[str, str] | None = None,
        base_url: str = API_BASE,
        timeout: float = 15.0,
        transport: Transport | None = None,
        clock: Callable[[], float] | None = None,
        demo: bool = True,
        allow_post: bool = False,
    ):
        if not demo:
            raise LiveModeDisabled("demo verify is Demo-only; live mode is disabled")
        if environ is None:
            load_os_env_file()
        env = os.environ if environ is None else environ
        env_mode = str(env.get("BITGET_ENV", "demo")).strip().lower()
        if env_mode in {"live", "production", "prod"}:
            raise LiveModeDisabled("BITGET_ENV live/production is disabled for demo verify")
        self._environ = env
        self._credentials = credentials
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self._transport = transport
        self._clock = clock
        self.allow_post = bool(allow_post)
        self.calls: list[dict[str, Any]] = []
        self.adapter = ReadOnlyBitgetAdapter(
            credentials=credentials,
            environ=environ,
            base_url=self.base_url,
            timeout=self.timeout,
            transport=self._tracked_transport,
            clock=clock,
            demo=True,
        )

    @property
    def credentials(self) -> ReadOnlyCredentials:
        if self._credentials is None:
            self._credentials = ReadOnlyCredentials.from_env(self._environ)
        return self._credentials

    def _tracked_transport(
        self,
        method: str,
        request_path: str,
        headers: Mapping[str, str],
        body: str | None,
        timeout: float,
    ) -> Mapping[str, Any]:
        self.calls.append(
            {
                "method": method,
                "path": request_path,
                "headers": redact_headers(headers),
                "has_body": bool(body),
                "paptrading": str(headers.get("paptrading", "")),
            }
        )
        transport = self._transport or self._http_transport
        return transport(method, request_path, headers, body, timeout)

    def _http_transport(
        self,
        method: str,
        request_path: str,
        headers: Mapping[str, str],
        body: str | None,
        timeout: float,
    ) -> Mapping[str, Any]:
        import urllib.error
        import urllib.request

        request = urllib.request.Request(
            self.base_url + request_path,
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

    def _headers(self, method: str, request_path: str, body: str = "") -> dict[str, str]:
        credentials = self.credentials
        timestamp = str(int((self._clock or __import__("time").time)() * 1000))
        return {
            "locale": "en-US",
            "Content-Type": "application/json",
            "paptrading": "1",
            "ACCESS-KEY": credentials.api_key,
            "ACCESS-SIGN": sign(credentials.api_secret, timestamp, method, request_path, body),
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": credentials.passphrase,
        }

    def _get(self, path: str, params: Mapping[str, Any] | None = None, *, private: bool = True) -> Any:
        query = query_string(params)
        request_path = path + (f"?{query}" if query else "")
        headers = {"locale": "en-US", "Content-Type": "application/json", "paptrading": "1"}
        if private:
            headers.update(self._headers("GET", request_path))
        result = self._tracked_transport("GET", request_path, headers, None, self.timeout)
        if result.get("code") != "00000":
            raise BitgetResponseError(f"{path}: {result.get('code')}")
        return result.get("data")

    def account_symbol(self, symbol: str) -> Any:
        return self._get(
            ACCOUNT_SYMBOL_PATH,
            {"productType": PRODUCT_TYPE, "symbol": symbol.upper(), "marginCoin": "USDT"},
        )

    def order_detail(self, symbol: str, *, client_oid: str | None = None, order_id: str | None = None) -> Any:
        params: dict[str, Any] = {"symbol": symbol.upper(), "productType": PRODUCT_TYPE}
        if client_oid:
            params["clientOid"] = client_oid
        if order_id:
            params["orderId"] = order_id
        return self._get(ORDER_DETAIL_PATH, params)

    def post(self, path: str, body: Mapping[str, Any]) -> dict[str, Any]:
        if not self.allow_post:
            raise PostDisabled("POST requires --place-orders --i-confirm-demo")
        if str(self._environ.get("GROK_TRADER_ALLOW_LIVE", "")) == "1":
            raise LiveModeDisabled("demo verify refuses GROK_TRADER_ALLOW_LIVE")
        payload = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
        headers = self._headers("POST", path, payload)
        try:
            result = self._tracked_transport("POST", path, headers, payload, self.timeout)
        except (BitgetAdapterError, TimeoutError, OSError) as exc:
            name = type(exc).__name__
            if "Timeout" in name or "timeout" in str(exc).lower():
                return {"dispatch": "UNKNOWN", "timeout": True, "sent": True}
            return {"dispatch": "UNKNOWN", "unparseable": True, "sent": True, "error": name}
        if not isinstance(result, Mapping):
            return {"dispatch": "UNKNOWN", "unparseable": True, "sent": True, "response": {"code": "invalid"}}
        classified = classify_dispatch(sent=True, response=result)
        return {"dispatch": classified, "sent": True, "response": redact_payload(dict(result))}


def _values_contain_secret(payload: Any, secrets: tuple[str, ...]) -> bool:
    needles = tuple(item for item in secrets if item)
    if not needles:
        return False
    if isinstance(payload, Mapping):
        return any(_values_contain_secret(value, needles) for value in payload.values())
    if isinstance(payload, list):
        return any(_values_contain_secret(item, needles) for item in payload)
    text = str(payload)
    return any(secret in text for secret in needles)


def leftover_on_symbol(positions: Any, pending: Any, symbol: str) -> dict[str, Any]:
    open_positions = [row for row in symbol_rows(positions, symbol) if nonzero(row.get("total") or row.get("available") or row.get("size") or row.get("holdVol"))]
    open_orders = symbol_rows(pending, symbol)
    return {
        "positions": len(open_positions),
        "pending_orders": len(open_orders),
        "clear": not open_positions and not open_orders,
    }


def _case(case_id: str, verdict: str, notes: str, **kwargs: Any) -> CaseResult:
    if verdict not in VERDICTS:
        raise DemoVerifyError(f"invalid verdict {verdict}")
    dispatch = kwargs.pop("dispatch", None)
    if dispatch is not None and dispatch not in DISPATCH_RESULTS:
        raise DemoVerifyError(f"invalid dispatch {dispatch}")
    return CaseResult(case_id=case_id, verdict=verdict, notes=notes, dispatch=dispatch, evidence=kwargs)


def _blocked_remaining(start: int = 5, reason: str = "not run in this session") -> list[CaseResult]:
    return [_case(f"D{index}", "BLOCKED", reason) for index in range(start, 16)]


def run_baseline(client: DemoVerifyClient, *, symbol: str) -> tuple[list[CaseResult], dict[str, Any]]:
    symbol = symbol.upper()
    before = len(client.calls)
    snapshot = client.adapter.snapshot(symbol=symbol)
    account_symbol = None
    account_error = None
    try:
        account_symbol = client.account_symbol(symbol)
    except BitgetAdapterError as exc:
        account_error = type(exc).__name__
    calls = client.calls[before:]
    headers_ok = bool(calls) and all(item.get("paptrading") == "1" for item in calls)
    methods_ok = all(item.get("method") == "GET" for item in calls)
    redacted_calls = redact_payload(calls)
    secrets = (
        client.credentials.api_key,
        client.credentials.api_secret,
        client.credentials.passphrase,
    )
    secret_leak = _values_contain_secret(redacted_calls, secrets)
    d0 = _case(
        "D0",
        "PASS" if headers_ok and methods_ok and not secret_leak else "FAIL",
        "all GET calls use paptrading=1 and redacted evidence" if headers_ok and not secret_leak else "header or redaction check failed",
        request_count=len(calls),
        methods=sorted({str(item.get("method")) for item in calls}),
    )

    margin_mode = first_field(account_symbol, "marginMode") or first_field(snapshot.get("account"), "marginMode")
    pos_mode = first_field(account_symbol, "posMode") or first_field(snapshot.get("account"), "posMode")
    equity_present = first_field(snapshot.get("account"), "accountEquity") not in (None, "")
    d1 = _case(
        "D1",
        "PASS" if (margin_mode or pos_mode) and equity_present else "UNKNOWN" if account_error else "FAIL",
        account_error or f"marginMode={margin_mode or 'missing'} posMode={pos_mode or 'missing'}",
        margin_mode=margin_mode,
        pos_mode=pos_mode,
        equity="present" if equity_present else "missing",
        product_type=PRODUCT_TYPE,
    )

    position_margin = first_field(symbol_rows(snapshot.get("positions"), symbol), "marginMode")
    isolated = str(position_margin or margin_mode or "").lower() == "isolated"
    d2 = _case(
        "D2",
        "PASS" if isolated else "FAIL" if (position_margin or margin_mode) else "UNKNOWN",
        "symbol/account isolated" if isolated else "isolated not confirmed; mode not changed by this harness",
        margin_mode=position_margin or margin_mode,
    )
    d3 = _case(
        "D3",
        "PASS" if pos_mode in {"one_way_mode", "hedge_mode"} else "UNKNOWN",
        "recorded current position mode; harness does not set mode",
        pos_mode=pos_mode,
    )

    contract = pick_contract(snapshot.get("contract"), symbol)
    required = ("minTradeNum", "sizeMultiplier", "pricePlace", "priceEndStep")
    missing = [name for name in required if not contract or contract.get(name) in (None, "")]
    size = round_size(contract) if contract else None
    price_tick = tick_size(contract) if contract else None
    d4 = _case(
        "D4",
        "PASS" if contract and not missing and size and price_tick else "FAIL",
        "contract rules available for size/price rounding" if not missing else "missing " + ",".join(missing),
        min_trade_num=None if contract is None else contract.get("minTradeNum"),
        size_multiplier=None if contract is None else contract.get("sizeMultiplier"),
        price_place=None if contract is None else contract.get("pricePlace"),
        price_end_step=None if contract is None else contract.get("priceEndStep"),
        rounded_min_size=None if size is None else format(size, "f"),
        tick=None if price_tick is None else format(price_tick, "f"),
    )

    leftover = leftover_on_symbol(snapshot.get("positions"), snapshot.get("pending_orders"), symbol)
    context = {
        "snapshot": snapshot,
        "account_symbol": account_symbol,
        "contract": contract,
        "margin_mode": margin_mode,
        "pos_mode": pos_mode,
        "leftover": leftover,
        "clear": leftover["clear"],
        "baseline_ok": d0.verdict == "PASS" and d1.verdict in {"PASS", "UNKNOWN"} and d4.verdict == "PASS" and leftover["clear"],
    }
    return [d0, d1, d2, d3, d4], context


def run_place_cancel(
    client: DemoVerifyClient,
    *,
    symbol: str,
    zone_id: str,
    context: Mapping[str, Any],
) -> list[CaseResult]:
    if not context.get("clear"):
        return [
            _case("D5", "BLOCKED", "symbol still has position or pending order"),
            _case("D6", "BLOCKED", "cancel skipped because entry was not placed"),
            *_blocked_remaining(7, "blocked by leftover position/order"),
        ]
    if str(context.get("margin_mode") or "").lower() != "isolated":
        return [
            _case("D5", "BLOCKED", "isolated margin not confirmed; harness does not set mode"),
            _case("D6", "BLOCKED", "cancel skipped because entry was not placed"),
            *_blocked_remaining(7, "blocked until isolated margin is confirmed"),
        ]
    contract = context.get("contract")
    ticker_last = first_field(context.get("snapshot", {}).get("ticker"), "lastPr", "markPrice")
    last_price = decimal_or_none(ticker_last)
    size = round_size(contract) if isinstance(contract, Mapping) else None
    limit_price = round_price(last_price * Decimal("0.96"), contract) if last_price and isinstance(contract, Mapping) else None
    if size is None or limit_price is None:
        return [
            _case("D5", "BLOCKED", "cannot round min size or far-from-market price"),
            _case("D6", "BLOCKED", "cancel skipped because entry was not placed"),
            *_blocked_remaining(7, "blocked by missing contract/ticker"),
        ]

    client_oid = verify_client_oid(zone_id, "entry", 1)
    pos_mode = str(context.get("pos_mode") or "")
    body: dict[str, Any] = {
        "symbol": symbol.upper(),
        "productType": PRODUCT_TYPE,
        "marginMode": "isolated",
        "marginCoin": "USDT",
        "size": format(size, "f"),
        "price": format(limit_price, "f"),
        "side": "buy",
        "orderType": "limit",
        "force": "gtc",
        "clientOid": client_oid,
    }
    if pos_mode == "hedge_mode":
        body["tradeSide"] = "open"

    if not client.allow_post:
        return [
            _case(
                "D5",
                "BLOCKED",
                "POST not enabled; body recorded as VERIFIED_NOT_RECEIVED",
                dispatch="VERIFIED_NOT_RECEIVED",
                client_oid=redact_id(client_oid),
                body=redact_payload({**body, "clientOid": redact_id(client_oid)}),
            ),
            _case("D6", "BLOCKED", "cancel not sent because place-order was not sent", dispatch="VERIFIED_NOT_RECEIVED"),
            *_blocked_remaining(7, "needs --place-orders --i-confirm-demo"),
        ]

    try:
        placed = client.post(PLACE_ORDER_PATH, body)
    except LiveModeDisabled as exc:
        return [
            _case("D5", "BLOCKED", str(exc)[:80], dispatch="VERIFIED_NOT_RECEIVED"),
            _case("D6", "BLOCKED", "cancel skipped because place-order was not sent", dispatch="VERIFIED_NOT_RECEIVED"),
            *_blocked_remaining(7, "blocked by live guard"),
        ]
    dispatch = str(placed.get("dispatch") or "UNKNOWN")
    detail = None
    detail_error = None
    if dispatch == "FOUND":
        try:
            detail = client.order_detail(symbol, client_oid=client_oid)
        except BitgetAdapterError as exc:
            detail_error = type(exc).__name__
            dispatch = classify_dispatch(sent=True, unparseable=True)
    d5 = _case(
        "D5",
        "PASS" if dispatch == "FOUND" else "FAIL" if dispatch == "REJECTED" else "UNKNOWN",
        detail_error or f"place-order dispatch={dispatch}",
        dispatch=dispatch,
        client_oid=redact_id(client_oid),
        size=format(size, "f"),
        price=format(limit_price, "f"),
        detail_status=first_field(detail, "status", "state"),
    )
    if dispatch != "FOUND":
        return [d5, _case("D6", "BLOCKED", "cancel skipped because entry was not FOUND"), *_blocked_remaining(7)]

    cancel_body = {
        "symbol": symbol.upper(),
        "productType": PRODUCT_TYPE,
        "marginCoin": "USDT",
        "clientOid": client_oid,
    }
    cancelled = client.post(CANCEL_ORDER_PATH, cancel_body)
    cancel_dispatch = str(cancelled.get("dispatch") or "UNKNOWN")
    after = None
    pending_after = None
    positions_after = None
    try:
        after = client.order_detail(symbol, client_oid=client_oid)
        pending_after = leftover_on_symbol(None, client.adapter.pending_orders(), symbol)
        positions_after = leftover_on_symbol(client.adapter.positions(), None, symbol)
    except BitgetAdapterError as exc:
        cancel_dispatch = classify_dispatch(sent=True, unparseable=True)
        after_error = type(exc).__name__
    else:
        after_error = None
    status = str(first_field(after, "status", "state") or "").lower()
    still_pending = bool(pending_after and not pending_after["clear"])
    position_grew = bool(positions_after and not positions_after["clear"])
    d6_pass = cancel_dispatch in {"FOUND", "REJECTED"} and status in {"canceled", "cancelled"} and not still_pending and not position_grew
    # REJECTED on cancel can still be PASS if the follow-up query shows canceled.
    if status in {"canceled", "cancelled"} and not still_pending and not position_grew:
        d6_pass = True
        cancel_dispatch = "FOUND"
    d6 = _case(
        "D6",
        "PASS" if d6_pass else "FAIL" if cancel_dispatch == "REJECTED" else "UNKNOWN",
        after_error or f"cancel dispatch={cancel_dispatch} status={status or 'missing'}",
        dispatch=cancel_dispatch,
        status=status or None,
        pending_clear=None if pending_after is None else pending_after["clear"],
        position_clear=None if positions_after is None else positions_after["clear"],
    )
    return [d5, d6, *_blocked_remaining(7, "fill/timeout/protection/restart not auto-run")]


def _deferred_or_place(
    client: DemoVerifyClient,
    *,
    symbol: str,
    zone_id: str,
    context: Mapping[str, Any],
    place_orders: bool,
) -> list[CaseResult]:
    if place_orders:
        return run_place_cancel(client, symbol=symbol, zone_id=zone_id, context=context)
    leftover = context.get("leftover") or {}
    if not context.get("clear"):
        if leftover.get("positions") or leftover.get("pending_orders"):
            reason = "baseline failed: leftover position or pending order on symbol"
        else:
            reason = "baseline did not confirm a clear symbol"
        return [
            _case("D5", "BLOCKED", reason, positions=leftover.get("positions"), pending_orders=leftover.get("pending_orders")),
            *_blocked_remaining(6, "blocked until baseline is clear"),
        ]
    return [
        _case(
            "D5",
            "BLOCKED",
            "GET-only run; pass --place-orders --i-confirm-demo to send Demo limit",
            dispatch="VERIFIED_NOT_RECEIVED",
        ),
        _case("D6", "BLOCKED", "GET-only run; cancel not sent", dispatch="VERIFIED_NOT_RECEIVED"),
        *_blocked_remaining(7, "GET-only run"),
    ]


def run_demo_verify(
    client: DemoVerifyClient,
    *,
    symbol: str,
    zone_id: str = "demo-verify",
    now: str | None = None,
    place_orders: bool = False,
) -> VerifyReport:
    try:
        baseline, context = run_baseline(client, symbol=symbol)
    except MissingReadOnlyCredentials:
        raise
    except (BitgetAdapterError, TimeoutError, OSError) as exc:
        notes = type(exc).__name__
        baseline = [
            _case("D0", "UNKNOWN", notes),
            _case("D1", "UNKNOWN", notes),
            _case("D2", "UNKNOWN", notes),
            _case("D3", "UNKNOWN", notes),
            _case("D4", "UNKNOWN", notes),
        ]
        context = {"clear": False, "margin_mode": None, "contract": None, "leftover": {}}
    rest = _deferred_or_place(
        client,
        symbol=symbol,
        zone_id=zone_id,
        context=context,
        place_orders=place_orders,
    )
    by_id = {case.case_id: case for case in [*baseline, *rest]}
    ordered = [by_id[case_id] for case_id in CASE_IDS if case_id in by_id]
    return VerifyReport(captured_at=now or utc_now(), symbol=symbol.upper(), zone_id=zone_id, cases=ordered)
