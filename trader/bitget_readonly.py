"""Read-only Bitget v2 adapter for zone previews and status snapshots.

Only GET requests are exposed. Credentials are read from the existing
BITGET_API_KEY/BITGET_API_SECRET/BITGET_PASSPHRASE environment variables and
never returned in snapshots or error text. The adapter can be given a transport
callable in tests, so no credential or network is needed for unit tests.
"""
from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Callable, Mapping
import urllib.error
import urllib.request


API_BASE = "https://api.bitget.com"
PRODUCT_TYPE = "USDT-FUTURES"


class BitgetAdapterError(RuntimeError):
    """Base exception for read-only adapter failures."""


class MissingReadOnlyCredentials(BitgetAdapterError):
    """Raised when a private read-only endpoint lacks its env credentials."""


class BitgetResponseError(BitgetAdapterError):
    """Raised when Bitget returns a non-success response code."""


class LiveModeDisabled(BitgetAdapterError):
    """Raised when a caller attempts to use this Demo-only adapter live."""


@dataclass(frozen=True)
class ReadOnlyCredentials:
    api_key: str
    api_secret: str
    passphrase: str

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "ReadOnlyCredentials":
        env = os.environ if environ is None else environ
        names = ("BITGET_API_KEY", "BITGET_API_SECRET", "BITGET_PASSPHRASE")
        values = tuple(str(env.get(name, "")) for name in names)
        if not all(values):
            raise MissingReadOnlyCredentials(
                "missing read-only Bitget credentials: BITGET_API_KEY/BITGET_API_SECRET/BITGET_PASSPHRASE"
            )
        return cls(*values)


def sign(secret: str, timestamp: str, method: str, request_path: str, body: str = "") -> str:
    payload = f"{timestamp}{method.upper()}{request_path}{body}".encode()
    return base64.b64encode(hmac.new(secret.encode(), payload, hashlib.sha256).digest()).decode()


def query_string(params: Mapping[str, Any] | None) -> str:
    if not params:
        return ""
    # Keep the existing helper's insertion order while escaping values correctly.
    from urllib.parse import urlencode

    return urlencode([(str(key), value) for key, value in params.items() if value is not None and value != ""])


def _safe_error_text(value: Any) -> str:
    # Avoid relaying response body text: providers can echo request fragments or
    # diagnostics that should not be treated as safe secrets-free output.
    if isinstance(value, Mapping):
        return str(value.get("code") or "Bitget request failed")[:80]
    return str(value)[:80]


Transport = Callable[[str, str, Mapping[str, str], str | None, float], Mapping[str, Any]]


class ReadOnlyBitgetAdapter:
    """Small GET-only adapter with public and signed private snapshots."""

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
    ):
        if not demo:
            raise LiveModeDisabled("read-only adapter is Demo-only; live mode is disabled")
        env_mode = (environ or os.environ).get("BITGET_ENV", "demo").strip().lower()
        if env_mode in {"live", "production", "prod"}:
            raise LiveModeDisabled("BITGET_ENV live/production is disabled for this adapter")
        self._credentials = credentials
        self._environ = environ
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self._transport = transport
        self._clock = clock or time.time

    @property
    def credentials(self) -> ReadOnlyCredentials:
        if self._credentials is None:
            self._credentials = ReadOnlyCredentials.from_env(self._environ)
        return self._credentials

    def _http_transport(
        self,
        method: str,
        request_path: str,
        headers: Mapping[str, str],
        body: str | None,
        timeout: float,
    ) -> Mapping[str, Any]:
        url = self.base_url + request_path
        request = urllib.request.Request(
            url,
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
            raise BitgetAdapterError(f"Bitget GET failed: {type(exc).__name__}") from exc
        if not isinstance(result, Mapping):
            raise BitgetAdapterError("Bitget response is not an object")
        return result

    def _request(self, path: str, params: Mapping[str, Any] | None = None, *, private: bool = False) -> Any:
        query = query_string(params)
        request_path = path + (f"?{query}" if query else "")
        headers: dict[str, str] = {
            "locale": "en-US",
            "Content-Type": "application/json",
            "paptrading": "1",
        }
        if private:
            credentials = self.credentials
            timestamp = str(int(self._clock() * 1000))
            headers.update(
                {
                    "ACCESS-KEY": credentials.api_key,
                    "ACCESS-SIGN": sign(credentials.api_secret, timestamp, "GET", request_path),
                    "ACCESS-TIMESTAMP": timestamp,
                    "ACCESS-PASSPHRASE": credentials.passphrase,
                }
            )
        transport = self._transport or self._http_transport
        result = transport("GET", request_path, headers, None, self.timeout)
        code = result.get("code")
        if code != "00000":
            raise BitgetResponseError(f"{path}: {_safe_error_text(result)}")
        return result.get("data")

    def public_ticker(self, symbol: str) -> Any:
        return self._request(
            "/api/v2/mix/market/ticker",
            {"productType": PRODUCT_TYPE, "symbol": symbol.upper()},
        )

    def public_contract(self, symbol: str) -> Any:
        return self._request(
            "/api/v2/mix/market/contracts",
            {"productType": PRODUCT_TYPE, "symbol": symbol.upper()},
        )

    def account(self) -> Any:
        return self._request(
            "/api/v2/mix/account/accounts",
            {"productType": PRODUCT_TYPE},
            private=True,
        )

    def positions(self) -> Any:
        return self._request(
            "/api/v2/mix/position/all-position",
            {"productType": PRODUCT_TYPE, "marginCoin": "USDT"},
            private=True,
        )

    def pending_orders(self) -> Any:
        return self._request(
            "/api/v2/mix/order/orders-pending",
            {"productType": PRODUCT_TYPE},
            private=True,
        )

    def snapshot(self, *, symbol: str | None = None) -> dict[str, Any]:
        """Return only GET-derived fields for CLI preview/status/sync."""
        snapshot: dict[str, Any] = {
            "product_type": PRODUCT_TYPE,
            "account": self.account(),
            "positions": self.positions() or [],
            "pending_orders": self.pending_orders() or [],
        }
        if symbol:
            snapshot["ticker"] = self.public_ticker(symbol)
            snapshot["contract"] = self.public_contract(symbol)
        return snapshot
