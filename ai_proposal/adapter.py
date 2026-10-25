"""HTTP adapter for one structured Demo-scan decision.

Provider errors, timeout, bad JSON, or schema mismatch raise ``ProviderError``.
Callers must treat that as ``NO_TRADE`` and must not invent a replacement order.
This module never talks to Bitget and never logs secrets.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Mapping
from urllib.parse import quote, urljoin, urlparse
import ipaddress
import json
import urllib.error
import urllib.request

from .schema import DecisionOpportunitySnapshot, ProposalDraft, utc_now_iso

Transport = Callable[[str, str, Mapping[str, str], str | None, float], Mapping[str, Any]]

GEMINI_HOST = "generativelanguage.googleapis.com"
PRIVATE_HOSTS = frozenset(
    {"localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"}
)
ALLOWED_ACTIONS = frozenset(
    {"NO_TRADE", "OPEN", "CLOSE", "REDUCE", "HOLD", "ADJUST_SL", "CANCEL"}
)
ACTION_ALIASES = {
    "OPEN_LONG": ("OPEN", "long"),
    "OPEN_SHORT": ("OPEN", "short"),
}
MAX_OUTPUT_CHARS = 4000
MAX_RATIONALE = 500


class ProviderError(ValueError):
    """Raised when the model call or decision cannot be used. Never includes secrets."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    model: str
    api_key: str
    base_url: str = ""
    request_timeout: float = 30.0
    label: str = ""

    def __repr__(self) -> str:
        return (
            f"ProviderConfig(provider={self.provider!r}, model={self.model!r}, "
            f"label={self.label!r}, request_timeout={self.request_timeout})"
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ProviderConfig":
        if not isinstance(value, Mapping):
            raise ProviderError("AGENT_CONFIG_INVALID")
        provider = str(value.get("provider") or "").strip()
        model = str(value.get("model") or "").strip()
        api_key = str(value.get("api_key") or "").strip()
        if provider not in {"gemini", "openai_compatible"} or not model or not api_key:
            raise ProviderError("AGENT_CONFIG_INVALID")
        timeout_raw = value.get("request_timeout", 30)
        try:
            timeout = float(timeout_raw)
        except (TypeError, ValueError) as exc:
            raise ProviderError("AGENT_TIMEOUT_INVALID") from exc
        if timeout < 1 or timeout > 60:
            raise ProviderError("AGENT_TIMEOUT_INVALID")
        base_url = str(value.get("base_url") or "").strip()
        if provider == "openai_compatible" and not is_allowed_openai_url(base_url):
            raise ProviderError("BASE_URL_NOT_ALLOWED")
        if provider == "gemini":
            base_url = ""
        label = str(value.get("label") or "").strip()[:64]
        return cls(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            request_timeout=timeout,
            label=label,
        )


def _is_blocked_openai_host(host: str) -> bool:
    cleaned = (host or "").strip().lower().strip("[]")
    if not cleaned or cleaned in PRIVATE_HOSTS:
        return True
    if cleaned.endswith((".localhost", ".local", ".internal")):
        return True
    try:
        ip = ipaddress.ip_address(cleaned)
    except ValueError:
        return False
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
    )


def is_allowed_openai_url(value: str) -> bool:
    try:
        parsed = urlparse(str(value or "").strip())
    except ValueError:
        return False
    if parsed.scheme != "https" or parsed.username or parsed.password:
        return False
    if parsed.port not in {None, 443}:
        return False
    return not _is_blocked_openai_host(parsed.hostname or "")


def _decimal(value: Any, code: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise ProviderError(code)
    try:
        number = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError) as exc:
        raise ProviderError(code) from exc
    if not number.is_finite() or number <= 0:
        raise ProviderError(code)
    return number


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = str(text or "").strip()
    if not stripped:
        raise ProviderError("MODEL_OUTPUT_EMPTY")
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    if len(stripped) > MAX_OUTPUT_CHARS:
        raise ProviderError("MODEL_OUTPUT_TOO_LONG")
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise ProviderError("MODEL_OUTPUT_NOT_JSON")
        try:
            value = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ProviderError("MODEL_OUTPUT_NOT_JSON") from exc
    if not isinstance(value, dict):
        raise ProviderError("MODEL_OUTPUT_NOT_OBJECT")
    return value


def build_prompt(snapshot: DecisionOpportunitySnapshot, *, max_leverage: str) -> str:
    features = {
        key: snapshot.features[key]
        for key in (
            "daily_loss",
            "day_start_equity",
            "drawdown",
            "consecutive_losses",
            "drawdown_unit",
            "user_style",
            "ta",
        )
        if key in snapshot.features
    }
    payload = {
        "symbol": snapshot.symbol,
        "side": snapshot.side,
        "ref_price": format(snapshot.ref_price, "f"),
        "sl_pct": format(snapshot.sl_pct, "f"),
        "loss_budget": format(snapshot.loss_budget, "f"),
        "current_size": format(snapshot.size, "f"),
        "max_size": format(snapshot.hard_limits.max_size, "f"),
        "max_exposure": format(snapshot.hard_limits.max_exposure, "f"),
        "max_leverage": max_leverage,
        "features": features,
        "allowed_actions": sorted(ALLOWED_ACTIONS),
    }
    return (
        "You are a futures trading decision adapter. Reply with one JSON object only. "
        "Do not add markdown. Use Decimal strings, never floats. "
        "Fields: action, quantity, stop_loss, take_profit, order_type, rationale, valid_until. "
        "action must be one of NO_TRADE, OPEN, CLOSE, REDUCE, HOLD, ADJUST_SL, CANCEL. "
        "OPEN must use order_type LIMIT. If unsure, use action NO_TRADE. "
        "Follow features.user_style rules as strategy preferences; they never override hard limits. "
        "features.ta is a risk filter, not a forecast. If ta.risk_side is AVOID, prefer NO_TRADE. "
        "Prefer fade/mean-revert and limit/maker when those preferences are present. "
        "Do not invent prices when ta.status is not ok; then prefer NO_TRADE unless already in a position. "
        f"Context: {json.dumps(payload, ensure_ascii=False, sort_keys=True)}"
    )


def snapshot_with_size(
    snapshot: DecisionOpportunitySnapshot, size: Decimal
) -> DecisionOpportunitySnapshot:
    data = snapshot.to_dict()
    data["size"] = format(size, "f")
    data["exposure"] = format(size * snapshot.ref_price, "f")
    try:
        return DecisionOpportunitySnapshot.from_dict(data)
    except (TypeError, ValueError) as exc:
        raise ProviderError("OPEN_SIZE_OUT_OF_LIMITS") from exc


def parse_decision(
    snapshot: DecisionOpportunitySnapshot,
    payload: Mapping[str, Any],
    *,
    model_version: str,
    policy_version: str,
    now: str,
    leverage: str,
) -> tuple[DecisionOpportunitySnapshot, ProposalDraft]:
    if not isinstance(payload, Mapping):
        raise ProviderError("MODEL_OUTPUT_NOT_OBJECT")
    raw_action = str(payload.get("action") or "").strip().upper().replace("-", "_")
    side = snapshot.side
    if raw_action in ACTION_ALIASES:
        raw_action, alias_side = ACTION_ALIASES[raw_action]
        if alias_side != snapshot.side:
            raise ProviderError("SIDE_MISMATCH")
    if raw_action not in ALLOWED_ACTIONS:
        raise ProviderError("ACTION_INVALID")
    if raw_action == "ADD":
        raise ProviderError("ACTION_INVALID")
    valid_until = payload.get("valid_until")
    if valid_until not in (None, ""):
        try:
            until = _parse_dt(str(valid_until).strip())
        except ValueError as exc:
            raise ProviderError("VALID_UNTIL_INVALID") from exc
        if until < _parse_dt(now):
            raise ProviderError("DECISION_EXPIRED")
    rationale = str(payload.get("rationale") or "model decision").strip()
    if not rationale or len(rationale) > MAX_RATIONALE:
        raise ProviderError("RATIONALE_INVALID")
    order_type = str(payload.get("order_type") or "LIMIT").strip().lower()
    if raw_action == "OPEN" and order_type != "limit":
        raise ProviderError("OPEN_REQUIRES_LIMIT")
    if order_type not in {"limit", "market", "none"}:
        raise ProviderError("ORDER_TYPE_INVALID")
    bound = snapshot
    overrides: dict[str, Any] = {}
    if raw_action == "OPEN":
        size = _decimal(payload.get("quantity"), "QUANTITY_INVALID")
        if snapshot.size == 0:
            bound = snapshot_with_size(snapshot, size)
        elif size != snapshot.size:
            raise ProviderError("OPEN_SIZE_LOCKED")
    elif raw_action == "REDUCE":
        size = _decimal(payload.get("quantity"), "QUANTITY_INVALID")
        if size > snapshot.size:
            raise ProviderError("REDUCE_SIZE_INVALID")
        overrides["size"] = size
        overrides["exposure"] = snapshot.exposure
    elif raw_action in {"CLOSE", "ADJUST_SL", "CANCEL"} and snapshot.size <= 0:
        raise ProviderError("POSITION_SIZE_REQUIRED")
    metadata: dict[str, Any] = {
        "order_type": "none" if order_type == "none" else order_type,
        "leverage": leverage,
        "source": "ai_adapter",
    }
    stop = payload.get("stop_loss")
    if stop in (None, ""):
        if raw_action == "OPEN":
            delta = bound.ref_price * bound.sl_pct / Decimal("100")
            computed = bound.ref_price - delta if bound.side == "long" else bound.ref_price + delta
            metadata["stop_loss"] = format(computed, "f")
    else:
        metadata["stop_loss"] = format(_decimal(stop, "STOP_LOSS_INVALID"), "f")
    take = payload.get("take_profit")
    if take not in (None, ""):
        metadata["take_profit"] = format(_decimal(take, "TAKE_PROFIT_INVALID"), "f")
    if raw_action in {"CLOSE", "REDUCE"}:
        metadata["reduce_only"] = True
        metadata["order_role"] = "reduce"
    draft = ProposalDraft.from_snapshot(
        bound,
        proposal_id=f"ai-{snapshot.opportunity_id}",
        model_version=model_version,
        policy_version=policy_version,
        action=raw_action,
        rationale=rationale,
        decision_timestamp=now,
        metadata=metadata,
        **overrides,
    )
    return bound, draft


def _http_transport(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: str | None,
    timeout: float,
) -> Mapping[str, Any]:
    request = urllib.request.Request(
        url,
        data=body.encode() if body else None,
        method=method,
        headers=dict(headers),
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_OUTPUT_CHARS + 1)
    except TimeoutError as exc:
        raise ProviderError("PROVIDER_TIMEOUT") from exc
    except urllib.error.HTTPError as exc:
        raise ProviderError("PROVIDER_HTTP_ERROR") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise ProviderError("PROVIDER_UNAVAILABLE") from exc
    if len(raw) > MAX_OUTPUT_CHARS:
        raise ProviderError("MODEL_OUTPUT_TOO_LONG")
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderError("PROVIDER_RESPONSE_NOT_JSON") from exc
    if not isinstance(parsed, Mapping):
        raise ProviderError("PROVIDER_RESPONSE_NOT_OBJECT")
    return parsed


def _gemini_text(payload: Mapping[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ProviderError("PROVIDER_EMPTY")
    content = candidates[0]
    if not isinstance(content, Mapping):
        raise ProviderError("PROVIDER_EMPTY")
    inner = content.get("content")
    parts = inner.get("parts") if isinstance(inner, Mapping) else None
    if not isinstance(parts, list):
        raise ProviderError("PROVIDER_EMPTY")
    chunks = []
    for part in parts:
        if isinstance(part, Mapping) and isinstance(part.get("text"), str):
            chunks.append(part["text"])
    text = "".join(chunks).strip()
    if not text:
        raise ProviderError("PROVIDER_EMPTY")
    return text


def _openai_text(payload: Mapping[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderError("PROVIDER_EMPTY")
    message = choices[0]
    if not isinstance(message, Mapping):
        raise ProviderError("PROVIDER_EMPTY")
    inner = message.get("message")
    text = inner.get("content") if isinstance(inner, Mapping) else None
    if not isinstance(text, str) or not text.strip():
        raise ProviderError("PROVIDER_EMPTY")
    return text


class NetworkProposalProvider:
    """One network call per ``decide``. Bitget is out of scope."""

    def __init__(
        self,
        config: ProviderConfig,
        *,
        policy_version: str,
        leverage: str,
        transport: Transport | None = None,
        now: str | None = None,
    ):
        self._config = config
        self._policy_version = policy_version
        self._leverage = leverage
        self._transport = transport or _http_transport
        self._now = now

    def decide(
        self, snapshot: DecisionOpportunitySnapshot
    ) -> tuple[DecisionOpportunitySnapshot, ProposalDraft]:
        now = self._now or utc_now_iso()
        prompt = build_prompt(snapshot, max_leverage=self._leverage)
        text = self._complete(prompt)
        payload = extract_json_object(text)
        return parse_decision(
            snapshot,
            payload,
            model_version=self._config.model.replace(" ", "-")[:64] or "ai-model",
            policy_version=self._policy_version,
            now=now,
            leverage=self._leverage,
        )

    def propose(self, snapshot: DecisionOpportunitySnapshot) -> ProposalDraft:
        _, draft = self.decide(snapshot)
        return draft

    def _complete(self, prompt: str) -> str:
        if self._config.provider == "gemini":
            return self._complete_gemini(prompt)
        return self._complete_openai(prompt)

    def _complete_gemini(self, prompt: str) -> str:
        url = (
            f"https://{GEMINI_HOST}/v1beta/models/"
            f"{quote(self._config.model, safe='.-_')}:generateContent"
        )
        body = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0,
                    "maxOutputTokens": 512,
                    "responseMimeType": "application/json",
                },
            },
            separators=(",", ":"),
            ensure_ascii=False,
        )
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._config.api_key,
        }
        payload = self._send("POST", url, headers, body)
        return _gemini_text(payload)

    def _complete_openai(self, prompt: str) -> str:
        base = self._config.base_url.rstrip("/") + "/"
        url = urljoin(base, "chat/completions")
        body = json.dumps(
            {
                "model": self._config.model,
                "temperature": 0,
                "max_tokens": 512,
                "messages": [
                    {
                        "role": "system",
                        "content": "Reply with one JSON object only. No markdown.",
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            separators=(",", ":"),
            ensure_ascii=False,
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.api_key}",
        }
        payload = self._send("POST", url, headers, body)
        return _openai_text(payload)

    def _send(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: str,
    ) -> Mapping[str, Any]:
        try:
            payload = self._transport(method, url, headers, body, self._config.request_timeout)
        except ProviderError:
            raise
        except TimeoutError as exc:
            raise ProviderError("PROVIDER_TIMEOUT") from exc
        except Exception as exc:
            raise ProviderError("PROVIDER_UNAVAILABLE") from exc
        if not isinstance(payload, Mapping):
            raise ProviderError("PROVIDER_RESPONSE_NOT_OBJECT")
        return payload
