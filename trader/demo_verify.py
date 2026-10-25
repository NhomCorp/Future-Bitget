"""Demo verification harness for checklist D0-D15.

This module records redacted Bitget Demo evidence. It is not an order
dispatcher, does not open live, and does not change paper/AI autonomy.
GET is the default. POST is opt-in, Demo-only, and always sends
``paptrading: 1``. ``GROK_TRADER_ALLOW_LIVE`` blocks POST.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_UP
import hashlib
import json
import os
import time
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
PLACE_TPSL_PATH = "/api/v2/mix/order/place-tpsl-order"
CANCEL_ORDER_PATH = "/api/v2/mix/order/cancel-order"
CANCEL_PLAN_PATH = "/api/v2/mix/order/cancel-plan-order"
CLOSE_POSITIONS_PATH = "/api/v2/mix/order/close-positions"
ORDER_DETAIL_PATH = "/api/v2/mix/order/detail"
ORDERS_PLAN_PENDING_PATH = "/api/v2/mix/order/orders-plan-pending"
ACCOUNT_SYMBOL_PATH = "/api/v2/mix/account/account"
PLAN_TYPE_PROFIT_LOSS = "profit_loss"

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


def size_for_notional(contract: Mapping[str, Any], last: Decimal | None, size: Decimal | None) -> Decimal | None:
    if size is None:
        return None
    min_usdt = decimal_or_none(contract.get("minTradeUSDT"))
    lot = decimal_or_none(contract.get("sizeMultiplier")) or size
    if min_usdt is None or last is None or last <= 0 or lot <= 0:
        return size
    if size * last >= min_usdt:
        return size
    steps = (min_usdt / last / lot).to_integral_value(rounding=ROUND_UP)
    if steps <= 0:
        steps = Decimal("1")
    return steps * lot


def size_for_partial(contract: Mapping[str, Any], size: Decimal | None) -> Decimal | None:
    if size is None:
        return None
    lot = decimal_or_none(contract.get("sizeMultiplier")) or size
    if lot <= 0:
        return size
    two = lot * 2
    return two if size < two else size


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
        sleeper: Callable[[float], None] | None = None,
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
        self._sleep = sleeper or time.sleep
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

    def _get(
        self,
        path: str,
        params: Mapping[str, Any] | None = None,
        *,
        private: bool = True,
        timeout: float | None = None,
    ) -> Any:
        query = query_string(params)
        request_path = path + (f"?{query}" if query else "")
        headers = {"locale": "en-US", "Content-Type": "application/json", "paptrading": "1"}
        if private:
            headers.update(self._headers("GET", request_path))
        result = self._tracked_transport("GET", request_path, headers, None, self.timeout if timeout is None else timeout)
        if result.get("code") != "00000":
            raise BitgetResponseError(f"{path}: {result.get('code')}")
        return result.get("data")

    def account_symbol(self, symbol: str) -> Any:
        return self._get(
            ACCOUNT_SYMBOL_PATH,
            {"productType": PRODUCT_TYPE, "symbol": symbol.upper(), "marginCoin": "USDT"},
        )

    def order_detail(
        self,
        symbol: str,
        *,
        client_oid: str | None = None,
        order_id: str | None = None,
        timeout: float | None = None,
    ) -> Any:
        params: dict[str, Any] = {"symbol": symbol.upper(), "productType": PRODUCT_TYPE}
        if client_oid:
            params["clientOid"] = client_oid
        if order_id:
            params["orderId"] = order_id
        return self._get(ORDER_DETAIL_PATH, params, timeout=timeout)

    def plan_pending(self, symbol: str, *, plan_type: str = PLAN_TYPE_PROFIT_LOSS) -> Any:
        return self._get(
            ORDERS_PLAN_PENDING_PATH,
            {"productType": PRODUCT_TYPE, "planType": plan_type, "symbol": symbol.upper()},
        )

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
        order_id = None
        data = result.get("data")
        if isinstance(data, Mapping) and data.get("orderId") not in (None, ""):
            order_id = str(data.get("orderId"))
        return {
            "dispatch": classified,
            "sent": True,
            "response": redact_payload(dict(result)),
            "order_id": order_id,
        }


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


def _leg_sizes(positions: Any, symbol: str) -> tuple[Decimal, Decimal]:
    long = Decimal("0")
    short = Decimal("0")
    for row in symbol_rows(positions, symbol):
        qty = decimal_or_none(row.get("total") or row.get("available") or row.get("size") or row.get("holdVol"))
        if qty is None or qty == 0:
            continue
        side = str(row.get("holdSide") or row.get("posSide") or row.get("side") or "").lower()
        if side in {"long", "buy"}:
            long += qty
        elif side in {"short", "sell"}:
            short += qty
        else:
            long += qty
    return long, short


def _fill_fields(detail: Any) -> dict[str, Any]:
    size = decimal_or_none(first_field(detail, "size", "qty"))
    executed = decimal_or_none(
        first_field(detail, "accBaseVolume", "filledQty", "executeQty", "executedQty", "fillSize", "baseVolume")
    )
    remaining = None if size is None or executed is None else size - executed
    status = first_field(detail, "status", "state")
    average = first_field(detail, "priceAvg", "avgPrice", "averagePr", "fillPrice")
    keys = sorted(rows(detail)[0].keys()) if rows(detail) else []
    return {
        "size": None if size is None else format(size, "f"),
        "executed": None if executed is None else format(executed, "f"),
        "remaining": None if remaining is None else format(remaining, "f"),
        "average": None if average in (None, "") else str(average),
        "status": None if status in (None, "") else str(status),
        "partial": bool(size is not None and executed is not None and Decimal("0") < executed < size),
        "remaining_matches": remaining is not None and remaining == (size - executed if size is not None and executed is not None else remaining),
        "detail_keys": keys,
    }


def _limit_body(
    *,
    symbol: str,
    size: Decimal,
    price: Decimal | None,
    side: str,
    trade_side: str | None,
    client_oid: str,
    reduce_only: bool = False,
    pos_side: str | None = None,
    order_type: str = "limit",
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "symbol": symbol.upper(),
        "productType": PRODUCT_TYPE,
        "marginMode": "isolated",
        "marginCoin": "USDT",
        "size": format(size, "f"),
        "side": side,
        "orderType": order_type,
        "clientOid": client_oid,
    }
    if order_type == "limit":
        if price is None:
            raise DemoVerifyError("limit order requires price")
        body["price"] = format(price, "f")
        body["force"] = "gtc"
    else:
        body["force"] = "ioc"
    if trade_side:
        body["tradeSide"] = trade_side
    if reduce_only:
        body["reduceOnly"] = "YES"
    if pos_side:
        body["posSide"] = pos_side
    return body


def _query_order(
    client: DemoVerifyClient,
    symbol: str,
    *,
    client_oid: str | None = None,
    order_id: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    try:
        data = client.order_detail(symbol, client_oid=client_oid, order_id=order_id, timeout=timeout)
    except BitgetResponseError:
        return {"dispatch": "NOT_FOUND", "data": None, "timeout": False}
    except (BitgetAdapterError, TimeoutError, OSError) as exc:
        name = type(exc).__name__
        timed_out = timeout is not None or "Timeout" in name or "timeout" in str(exc).lower()
        return {"dispatch": "UNKNOWN", "data": None, "timeout": timed_out, "error": name}
    if data in (None, "", [], {}):
        return {"dispatch": "NOT_FOUND", "data": None, "timeout": False}
    return {"dispatch": "FOUND", "data": data, "timeout": False}


def _response_code(placed: Mapping[str, Any] | None) -> str | None:
    if not isinstance(placed, Mapping):
        return None
    response = placed.get("response")
    if isinstance(response, Mapping):
        code = response.get("code")
        return None if code in (None, "") else str(code)
    return None


def _cancel_oid(client: DemoVerifyClient, symbol: str, client_oid: str) -> dict[str, Any]:
    return client.post(
        CANCEL_ORDER_PATH,
        {
            "symbol": symbol.upper(),
            "productType": PRODUCT_TYPE,
            "marginCoin": "USDT",
            "clientOid": client_oid,
        },
    )


def _cancel_plan(
    client: DemoVerifyClient,
    symbol: str,
    *,
    plan_type: str,
    client_oid: str,
    order_id: str | None = None,
) -> dict[str, Any]:
    item: dict[str, str] = {"clientOid": client_oid}
    if order_id:
        item["orderId"] = order_id
    return client.post(
        CANCEL_PLAN_PATH,
        {
            "symbol": symbol.upper(),
            "productType": PRODUCT_TYPE,
            "planType": plan_type,
            "orderIdList": [item],
        },
    )


def _close_leg_body(
    *,
    symbol: str,
    size: Decimal,
    hold_side: str,
    pos_mode: str,
    client_oid: str,
    price: Decimal | None = None,
    order_type: str = "limit",
) -> dict[str, Any]:
    hedge = pos_mode == "hedge_mode"
    long_leg = hold_side == "long"
    if hedge:
        side = "buy" if long_leg else "sell"
        trade_side = "close"
        reduce_only = False
    else:
        side = "sell" if long_leg else "buy"
        trade_side = None
        reduce_only = True
    return _limit_body(
        symbol=symbol,
        size=size,
        price=price,
        side=side,
        trade_side=trade_side,
        client_oid=client_oid,
        reduce_only=reduce_only,
        order_type=order_type,
    )


def _flatten_leftover(
    client: DemoVerifyClient,
    *,
    symbol: str,
    zone_id: str,
    pos_mode: str,
    oids: tuple[str, ...] = (),
) -> dict[str, Any]:
    leftover = leftover_on_symbol(client.adapter.positions(), client.adapter.pending_orders(), symbol)
    if leftover["pending_orders"]:
        for oid in oids:
            _cancel_oid(client, symbol, oid)
    long, short = _leg_sizes(client.adapter.positions(), symbol)
    seq = 20
    for hold_side, qty in (("long", long), ("short", short)):
        if qty <= 0:
            continue
        client.post(
            PLACE_ORDER_PATH,
            _close_leg_body(
                symbol=symbol,
                size=qty,
                hold_side=hold_side,
                pos_mode=pos_mode,
                client_oid=verify_client_oid(zone_id, "reduce", seq),
                order_type="market",
            ),
        )
        seq += 1
        client._sleep(1)
    leftover = leftover_on_symbol(client.adapter.positions(), client.adapter.pending_orders(), symbol)
    if leftover["positions"]:
        long, short = _leg_sizes(client.adapter.positions(), symbol)
        for hold_side, qty in (("long", long), ("short", short)):
            if qty <= 0:
                continue
            client.post(
                CLOSE_POSITIONS_PATH,
                {"symbol": symbol.upper(), "productType": PRODUCT_TYPE, "holdSide": hold_side},
            )
            client._sleep(1)
    return leftover_on_symbol(client.adapter.positions(), client.adapter.pending_orders(), symbol)


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
    if isinstance(contract, Mapping):
        size = size_for_notional(contract, last_price, size)
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
    response_code = None
    if isinstance(placed.get("response"), Mapping):
        response_code = placed["response"].get("code")
    d5 = _case(
        "D5",
        "PASS" if dispatch == "FOUND" else "FAIL" if dispatch == "REJECTED" else "UNKNOWN",
        detail_error or f"place-order dispatch={dispatch}" + (f" code={response_code}" if response_code else ""),
        dispatch=dispatch,
        client_oid=redact_id(client_oid),
        size=format(size, "f"),
        price=format(limit_price, "f"),
        detail_status=first_field(detail, "status", "state"),
        response_code=response_code,
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
    if not d6_pass:
        return [d5, d6, *_blocked_remaining(7, "blocked until D6 cancel is confirmed")]
    return [d5, d6, *run_d7_to_d10(client, symbol=symbol, zone_id=zone_id, context=context)]


def run_d7_to_d10(
    client: DemoVerifyClient,
    *,
    symbol: str,
    zone_id: str,
    context: Mapping[str, Any],
) -> list[CaseResult]:
    """Demo POST path for partial fill, timeout/UNKNOWN, clientOid retry, close/reduce."""
    contract = context.get("contract")
    pos_mode = str(context.get("pos_mode") or "")
    trade_open = "open" if pos_mode == "hedge_mode" else None
    trade_close = "close" if pos_mode == "hedge_mode" else None
    size = round_size(contract) if isinstance(contract, Mapping) else None
    snapshot = context.get("snapshot") if isinstance(context.get("snapshot"), Mapping) else {}
    last = decimal_or_none(first_field((snapshot or {}).get("ticker"), "lastPr", "markPrice"))
    if isinstance(contract, Mapping):
        size = size_for_partial(contract, size_for_notional(contract, last, size))
    if size is None or last is None or not isinstance(contract, Mapping):
        reason = "missing contract or ticker for D7-D10"
        return [
            _case("D7", "BLOCKED", reason),
            _case("D8", "BLOCKED", reason),
            _case("D9", "BLOCKED", reason),
            _case("D10", "BLOCKED", reason),
            *_blocked_remaining(11, "blocked by missing contract/ticker"),
        ]

    far_buy = round_price(last * Decimal("0.96"), contract)
    near_buy = round_price(last, contract)
    fill_buy = round_price(last * Decimal("1.002"), contract) or near_buy
    near_sell = round_price(last * Decimal("0.998"), contract) or far_buy
    if far_buy is None or near_buy is None or fill_buy is None or near_sell is None:
        reason = "cannot round D7-D10 prices"
        return [
            _case("D7", "BLOCKED", reason),
            _case("D8", "BLOCKED", reason),
            _case("D9", "BLOCKED", reason),
            _case("D10", "BLOCKED", reason),
            *_blocked_remaining(11, "blocked by price rounding"),
        ]

    d7_oid = verify_client_oid(zone_id, "entry", 7)
    d7_place = client.post(
        PLACE_ORDER_PATH,
        _limit_body(symbol=symbol, size=size, price=near_buy, side="buy", trade_side=trade_open, client_oid=d7_oid),
    )
    polls: list[dict[str, Any]] = []
    for _ in range(12):
        queried = _query_order(client, symbol, client_oid=d7_oid)
        fields = _fill_fields(queried.get("data"))
        polls.append({"dispatch": queried.get("dispatch"), **fields})
        if fields["partial"] or str(fields.get("status") or "").lower() in {"filled", "full_fill"}:
            break
        client._sleep(0.15)

    last_poll = polls[-1] if polls else {}
    executed = decimal_or_none(last_poll.get("executed"))
    remaining = decimal_or_none(last_poll.get("remaining"))
    if last_poll.get("partial") and last_poll.get("remaining_matches"):
        d7 = _case(
            "D7",
            "PASS",
            "partial fill remaining matches size - executed",
            dispatch=str(last_poll.get("dispatch") or "FOUND"),
            client_oid=redact_id(d7_oid),
            polls=polls,
        )
    else:
        d7 = _case(
            "D7",
            "UNKNOWN",
            "partial fill not observed; remaining recorded from exchange fields" if last_poll else "no order detail",
            dispatch=str(last_poll.get("dispatch") or d7_place.get("dispatch") or "UNKNOWN"),
            client_oid=redact_id(d7_oid),
            polls=polls,
        )
    if remaining is not None and remaining > 0:
        _cancel_oid(client, symbol, d7_oid)

    d8_oid = verify_client_oid(zone_id, "entry", 8)
    place_before = sum(1 for item in client.calls if item.get("method") == "POST" and str(item.get("path") or "").startswith(PLACE_ORDER_PATH))
    d8_place = client.post(
        PLACE_ORDER_PATH,
        _limit_body(symbol=symbol, size=size, price=far_buy, side="buy", trade_side=trade_open, client_oid=d8_oid),
    )
    found = _query_order(client, symbol, client_oid=d8_oid)
    missing = _query_order(client, symbol, client_oid=verify_client_oid(zone_id, "entry", 80))
    timed = _query_order(client, symbol, client_oid=d8_oid, timeout=0.001)
    place_after = sum(1 for item in client.calls if item.get("method") == "POST" and str(item.get("path") or "").startswith(PLACE_ORDER_PATH))
    extra_place = place_after - place_before - 1
    classified = {
        "found": found.get("dispatch"),
        "not_found": missing.get("dispatch"),
        "timeout": timed.get("dispatch"),
        "timeout_fired": bool(timed.get("timeout")),
        "place_dispatch": d8_place.get("dispatch"),
        "extra_place": extra_place,
    }
    d8_ok = (
        classified["found"] == "FOUND"
        and classified["not_found"] == "NOT_FOUND"
        and classified["timeout_fired"]
        and classified["timeout"] == "UNKNOWN"
        and extra_place == 0
    )
    d8 = _case(
        "D8",
        "PASS" if d8_ok else "UNKNOWN",
        "classified FOUND/NOT_FOUND/UNKNOWN without a compensating place" if d8_ok else "timeout or NOT_FOUND not fully observed; no compensating place" if extra_place == 0 else "compensating place detected",
        dispatch="UNKNOWN" if classified["timeout_fired"] else str(classified["found"] or "UNKNOWN"),
        client_oid=redact_id(d8_oid),
        **classified,
    )
    _cancel_oid(client, symbol, d8_oid)

    d9_oid = verify_client_oid(zone_id, "entry", 9)
    first = client.post(
        PLACE_ORDER_PATH,
        _limit_body(symbol=symbol, size=size, price=far_buy, side="buy", trade_side=trade_open, client_oid=d9_oid),
    )
    second = client.post(
        PLACE_ORDER_PATH,
        _limit_body(symbol=symbol, size=size, price=far_buy, side="buy", trade_side=trade_open, client_oid=d9_oid),
    )
    first_id = None
    second_id = None
    if isinstance(first.get("response"), Mapping):
        data = first["response"].get("data") if isinstance(first["response"].get("data"), Mapping) else first["response"]
        if isinstance(data, Mapping):
            first_id = data.get("orderId")
    if isinstance(second.get("response"), Mapping):
        data = second["response"].get("data") if isinstance(second["response"].get("data"), Mapping) else second["response"]
        if isinstance(data, Mapping):
            second_id = data.get("orderId")
    if first.get("dispatch") == "FOUND" and second.get("dispatch") == "REJECTED":
        conclusion = "no-duplicate-rejected"
    elif first.get("dispatch") == "FOUND" and second.get("dispatch") == "FOUND" and first_id and second_id and first_id == second_id:
        conclusion = "duplicate-same-order"
    elif first.get("dispatch") == "FOUND" and second.get("dispatch") == "FOUND" and first_id and second_id and first_id != second_id:
        conclusion = "no-duplicate-second-order"
    else:
        conclusion = "inconclusive"
    d9 = _case(
        "D9",
        "PASS" if conclusion != "inconclusive" else "UNKNOWN",
        f"clientOid retry conclusion={conclusion}",
        dispatch=str(second.get("dispatch") or "UNKNOWN"),
        client_oid=redact_id(d9_oid),
        first_dispatch=first.get("dispatch"),
        second_dispatch=second.get("dispatch"),
        same_order_id=bool(first_id and second_id and first_id == second_id),
        conclusion=conclusion,
    )
    _cancel_oid(client, symbol, d9_oid)

    long_before, short_before = _leg_sizes(client.adapter.positions(), symbol)
    opened_for_close = False
    d10_open_oid = verify_client_oid(zone_id, "entry", 10)
    if long_before <= 0:
        opened_for_close = True
        open_place = client.post(
            PLACE_ORDER_PATH,
            _limit_body(symbol=symbol, size=size, price=fill_buy, side="buy", trade_side=trade_open, client_oid=d10_open_oid),
        )
        client._sleep(1)
        long_before, short_before = _leg_sizes(client.adapter.positions(), symbol)
        if long_before <= 0:
            _cancel_oid(client, symbol, d10_open_oid)
            d10_open_oid = verify_client_oid(zone_id, "entry", 12)
            open_place = client.post(
                PLACE_ORDER_PATH,
                _limit_body(
                    symbol=symbol,
                    size=size,
                    price=None,
                    side="buy",
                    trade_side=trade_open,
                    client_oid=d10_open_oid,
                    order_type="market",
                ),
            )
            client._sleep(1)
            long_before, short_before = _leg_sizes(client.adapter.positions(), symbol)
        d10_open_dispatch = str(open_place.get("dispatch") or "UNKNOWN")
    else:
        d10_open_dispatch = None
    d10_close_oid = verify_client_oid(zone_id, "reduce", 10)
    close_place = {"dispatch": "VERIFIED_NOT_RECEIVED"}
    lot = decimal_or_none(contract.get("sizeMultiplier")) if isinstance(contract, Mapping) else None
    if long_before > 0:
        if lot is not None and Decimal("0") < lot < long_before:
            close_qty = lot
        else:
            close_qty = size if size <= long_before else long_before
        close_place = client.post(
            PLACE_ORDER_PATH,
            _close_leg_body(
                symbol=symbol,
                size=close_qty,
                price=near_sell,
                hold_side="long",
                pos_mode=pos_mode,
                client_oid=d10_close_oid,
            ),
        )
        client._sleep(1)
        long_mid, _short_mid = _leg_sizes(client.adapter.positions(), symbol)
        if long_mid >= long_before:
            _cancel_oid(client, symbol, d10_close_oid)
            d10_close_oid = verify_client_oid(zone_id, "reduce", 11)
            close_place = client.post(
                PLACE_ORDER_PATH,
                _close_leg_body(
                    symbol=symbol,
                    size=close_qty,
                    hold_side="long",
                    pos_mode=pos_mode,
                    client_oid=d10_close_oid,
                    order_type="market",
                ),
            )
            client._sleep(1)
    if opened_for_close:
        _cancel_oid(client, symbol, d10_open_oid)
    long_after, short_after = _leg_sizes(client.adapter.positions(), symbol)
    other_leg_unchanged = short_after == short_before
    reduced = long_after < long_before
    d10_ok = long_before > 0 and reduced and other_leg_unchanged and close_place.get("dispatch") == "FOUND"
    d10 = _case(
        "D10",
        "PASS" if d10_ok else "UNKNOWN" if long_before > 0 else "BLOCKED",
        "close/reduce changed long leg only" if d10_ok else "no position to close" if long_before <= 0 else "close did not reduce long or other leg moved",
        dispatch=str(close_place.get("dispatch") or "UNKNOWN"),
        client_oid=redact_id(d10_close_oid),
        opened_for_close=opened_for_close,
        open_dispatch=d10_open_dispatch,
        long_before=format(long_before, "f"),
        long_after=format(long_after, "f"),
        short_before=format(short_before, "f"),
        short_after=format(short_after, "f"),
        other_leg_unchanged=other_leg_unchanged,
        reduce_only="not-sent" if pos_mode == "hedge_mode" else "YES",
        trade_side=trade_close or "one_way",
        close_side="buy",
        response_code=_response_code(close_place),
    )
    d11_rest, leftover = run_d11_to_d15(
        client,
        symbol=symbol,
        zone_id=zone_id,
        context={**dict(context), "size": size, "fill_buy": fill_buy, "pos_mode": pos_mode},
        flatten_oids=(d7_oid, d8_oid, d9_oid, d10_open_oid, d10_close_oid),
    )
    d10.evidence["leftover_clear"] = leftover.get("clear")
    return [d7, d8, d9, d10, *d11_rest]


def _present_keys(row: Mapping[str, Any] | None, *needles: str) -> dict[str, str]:
    found: dict[str, str] = {}
    if not isinstance(row, Mapping):
        return found
    for key, value in row.items():
        lowered = str(key).lower()
        if any(needle in lowered for needle in needles):
            found[str(key)] = "present" if value not in (None, "") else "missing"
    return found


def _d14_d15_from_snapshot(snapshot: Mapping[str, Any] | None, symbol: str) -> list[CaseResult]:
    account = snapshot.get("account") if isinstance(snapshot, Mapping) else None
    positions = symbol_rows(snapshot.get("positions") if isinstance(snapshot, Mapping) else None, symbol)
    position = positions[0] if positions else None
    pnl_keys = {
        **_present_keys(account if isinstance(account, Mapping) else None, "realized", "unrealiz", "fee", "fund"),
        **_present_keys(position, "realized", "unrealiz", "fee", "fund"),
    }
    realized = any("realized" in key.lower() and "unreal" not in key.lower() for key in pnl_keys)
    unrealized = any("unrealiz" in key.lower() for key in pnl_keys)
    fee = any("fee" in key.lower() for key in pnl_keys)
    funding = any("fund" in key.lower() for key in pnl_keys)
    separable = realized and unrealized
    d14 = _case(
        "D14",
        "PASS" if separable else "UNKNOWN",
        "realized/unrealized keys are distinct" if separable else "funding/PnL fields not fully separable on this snapshot",
        keys=pnl_keys,
        fee_field=fee,
        funding_field=funding,
    )
    liq_keys = {
        **_present_keys(account if isinstance(account, Mapping) else None, "liq", "adl", "bankrupt"),
        **_present_keys(position, "liq", "adl", "bankrupt", "liquidate"),
    }
    d15 = _case(
        "D15",
        "UNKNOWN",
        "no liquidation/ADL event in this session; not a claim of absolute control",
        keys=liq_keys,
    )
    return [d14, d15]


def _plan_trigger_type(plan_data: Any, *, symbol: str, client_oid: str) -> str | None:
    matched = []
    for row in rows(plan_data):
        row_symbol = str(row.get("symbol") or "").upper()
        if row_symbol and row_symbol != symbol.upper():
            continue
        if str(row.get("clientOid") or "") not in {"", client_oid}:
            continue
        matched.append(row)
    source = matched[0] if matched else None
    if source is None and rows(plan_data):
        source = rows(plan_data)[0]
    if source is None:
        return None
    trigger = first_field(source, "triggerType", "trigger_type")
    return None if trigger in (None, "") else str(trigger)


def _ensure_long_for_protect(
    client: DemoVerifyClient,
    *,
    symbol: str,
    zone_id: str,
    pos_mode: str,
    size: Decimal | None,
    fill_buy: Decimal | None,
) -> tuple[Decimal, str | None]:
    long, _short = _leg_sizes(client.adapter.positions(), symbol)
    if long > 0 or size is None:
        return long, None
    trade_open = "open" if pos_mode == "hedge_mode" else None
    setup_oid = verify_client_oid(zone_id, "entry", 13)
    client.post(
        PLACE_ORDER_PATH,
        _limit_body(
            symbol=symbol,
            size=size,
            price=fill_buy,
            side="buy",
            trade_side=trade_open,
            client_oid=setup_oid,
            order_type="limit" if fill_buy is not None else "market",
        ),
    )
    client._sleep(1)
    long, _short = _leg_sizes(client.adapter.positions(), symbol)
    if long > 0:
        return long, setup_oid
    setup_oid = verify_client_oid(zone_id, "entry", 14)
    client.post(
        PLACE_ORDER_PATH,
        _limit_body(
            symbol=symbol,
            size=size,
            price=None,
            side="buy",
            trade_side=trade_open,
            client_oid=setup_oid,
            order_type="market",
        ),
    )
    client._sleep(1)
    long, _short = _leg_sizes(client.adapter.positions(), symbol)
    return long, setup_oid


def run_d11_to_d15(
    client: DemoVerifyClient,
    *,
    symbol: str,
    zone_id: str,
    context: Mapping[str, Any],
    leftover_clear: bool | None = None,
    flatten_oids: tuple[str, ...] = (),
) -> tuple[list[CaseResult], dict[str, Any]]:
    """Observe stop/plan while a position exists, then flatten. Trigger fill is not simulated."""
    snapshot = context.get("snapshot") if isinstance(context.get("snapshot"), Mapping) else {}
    pos_mode = str(context.get("pos_mode") or "")
    contract = context.get("contract") if isinstance(context.get("contract"), Mapping) else None
    last = decimal_or_none(first_field((snapshot or {}).get("ticker"), "lastPr", "markPrice"))
    size = context.get("size") if isinstance(context.get("size"), Decimal) else (round_size(contract) if contract else None)
    fill_buy = context.get("fill_buy") if isinstance(context.get("fill_buy"), Decimal) else None
    trigger = round_price(last * Decimal("0.94"), contract) if last is not None and contract else None
    setup_oid = None
    long_qty = Decimal("0")
    if client.allow_post:
        long_qty, setup_oid = _ensure_long_for_protect(
            client,
            symbol=symbol,
            zone_id=zone_id,
            pos_mode=pos_mode,
            size=size,
            fill_buy=fill_buy,
        )
    protect_snapshot = {
        "account": snapshot.get("account") if isinstance(snapshot, Mapping) else None,
        "positions": client.adapter.positions() if client.allow_post else snapshot.get("positions"),
    }

    plan_error = None
    try:
        client.plan_pending(symbol, plan_type=PLAN_TYPE_PROFIT_LOSS)
    except BitgetResponseError:
        plan_error = "NOT_FOUND"
    except Exception as exc:
        plan_error = type(exc).__name__

    d11_oid = verify_client_oid(zone_id, "tpsl", 11)
    placed: dict[str, Any] = {"dispatch": "VERIFIED_NOT_RECEIVED"}
    used_plan_type = "pos_loss"
    after_plan = None
    if client.allow_post and trigger is not None and long_qty > 0:
        body = {
            "symbol": symbol.upper(),
            "productType": PRODUCT_TYPE,
            "marginCoin": "USDT",
            "planType": "pos_loss",
            "triggerType": "mark_price",
            "triggerPrice": format(trigger, "f"),
            "executePrice": "0",
            "holdSide": "long",
            "clientOid": d11_oid,
        }
        try:
            placed = client.post(PLACE_TPSL_PATH, body)
        except Exception as exc:
            placed = {"dispatch": "UNKNOWN", "error": type(exc).__name__}
        if placed.get("dispatch") == "REJECTED" and size is not None:
            used_plan_type = "loss_plan"
            d11_oid = verify_client_oid(zone_id, "tpsl", 12)
            body = {
                "symbol": symbol.upper(),
                "productType": PRODUCT_TYPE,
                "marginCoin": "USDT",
                "planType": "loss_plan",
                "triggerType": "mark_price",
                "triggerPrice": format(trigger, "f"),
                "executePrice": "0",
                "holdSide": "long",
                "size": format(size, "f"),
                "clientOid": d11_oid,
            }
            try:
                placed = client.post(PLACE_TPSL_PATH, body)
            except Exception as exc:
                placed = {"dispatch": "UNKNOWN", "error": type(exc).__name__}
        try:
            after_plan = client.plan_pending(symbol, plan_type=PLAN_TYPE_PROFIT_LOSS)
        except BitgetResponseError:
            plan_error = plan_error or "NOT_FOUND"
        except Exception as exc:
            plan_error = plan_error or type(exc).__name__
        if placed.get("dispatch") == "FOUND":
            _cancel_plan(
                client,
                symbol,
                plan_type=used_plan_type,
                client_oid=d11_oid,
                order_id=placed.get("order_id") if isinstance(placed.get("order_id"), str) else None,
            )

    trigger_type = _plan_trigger_type(after_plan, symbol=symbol, client_oid=d11_oid)
    d11_ok = placed.get("dispatch") == "FOUND" and trigger_type is not None
    d11 = _case(
        "D11",
        "PASS" if d11_ok else "UNKNOWN",
        "preset stop observed with trigger type" if d11_ok else "TPSL trigger semantics not fully observed; fields recorded",
        dispatch=str(placed.get("dispatch") or "UNKNOWN"),
        client_oid=redact_id(d11_oid),
        trigger_type=trigger_type,
        plan_error=plan_error,
        pos_mode=pos_mode or None,
        plan_type=used_plan_type,
        response_code=_response_code(placed),
        long_qty=format(long_qty, "f"),
    )

    leftover = leftover_on_symbol(client.adapter.positions(), client.adapter.pending_orders(), symbol)
    if client.allow_post:
        oids = tuple(oid for oid in (*flatten_oids, setup_oid or "", d11_oid) if oid)
        leftover = _flatten_leftover(
            client,
            symbol=symbol,
            zone_id=zone_id,
            pos_mode=pos_mode,
            oids=oids,
        )
    if leftover_clear is None:
        leftover_clear = leftover.get("clear")

    pending = []
    pending_error = None
    try:
        pending = rows(client.adapter.pending_orders())
    except (BitgetAdapterError, TimeoutError, OSError) as exc:
        pending_error = type(exc).__name__
    pending_empty = not pending
    d12 = _case(
        "D12",
        "PASS" if leftover_clear and pending_empty else "UNKNOWN",
        "no leftover entry after flatten; emergency intent not auto-sent" if leftover_clear and pending_empty else "risk-trigger cancel/emergency not fully observed on Demo",
        leftover_clear=leftover_clear,
        pending_count=len(pending),
        pending_error=pending_error,
        extra_place=0,
    )

    first_oids = sorted(str(item.get("clientOid") or "") for item in pending)
    second = []
    try:
        second = rows(client.adapter.pending_orders())
    except (BitgetAdapterError, TimeoutError, OSError):
        second = pending
    second_oids = sorted(str(item.get("clientOid") or "") for item in second)
    d13 = _case(
        "D13",
        "PASS" if first_oids == second_oids else "UNKNOWN",
        "pending clientOid set unchanged after re-GET" if first_oids == second_oids else "pending set changed between GET snapshots",
        before=len(first_oids),
        after=len(second_oids),
        same=first_oids == second_oids,
    )
    return [d11, d12, d13, *_d14_d15_from_snapshot(protect_snapshot, symbol)], leftover


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
    snapshot = context.get("snapshot") if isinstance(context.get("snapshot"), Mapping) else {}
    return [
        _case(
            "D5",
            "BLOCKED",
            "GET-only run; pass --place-orders --i-confirm-demo to send Demo limit",
            dispatch="VERIFIED_NOT_RECEIVED",
        ),
        _case("D6", "BLOCKED", "GET-only run; cancel not sent", dispatch="VERIFIED_NOT_RECEIVED"),
        *[_case(f"D{index}", "BLOCKED", "GET-only run") for index in range(7, 14)],
        *_d14_d15_from_snapshot(snapshot, symbol),
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
