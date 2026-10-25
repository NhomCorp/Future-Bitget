"""P3 decision opportunity and proposal records.

This module is deliberately pure and model-agnostic.  It contains no exchange,
network, credential, or order-execution integration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any, Mapping

SNAPSHOT_SCHEMA_VERSION = "p3.decision-opportunity.v1"
PROPOSAL_SCHEMA_VERSION = "p3.proposal.v1"
RESULT_ACCEPTED = "ACCEPTED"
RESULT_REJECTED = "REJECTED"
ACTIONS = frozenset({"OPEN", "CLOSE", "REDUCE", "HOLD", "NO_TRADE", "ADJUST_SL", "CANCEL"})
PLAN_ACTIONS_MAX = 4
_PLAN_STEP_KEYS = frozenset(
    {"action", "size", "stop_loss", "take_profit", "order_type", "order_role", "reduce_only", "leverage"}
)


def _decimal(value: Decimal | int | str, field_name: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError(f"{field_name} must be Decimal, integer, or decimal string")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a decimal") from exc
    if not result.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return result


def decimal_text(value: Decimal | int | str, field_name: str = "value") -> str:
    """Return a non-exponential, exact JSON string representation of a decimal."""
    return format(_decimal(value, field_name), "f")


def _timestamp(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty ISO-8601 timestamp")
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value.strip() != value:
        raise ValueError(f"{field_name} must be a non-empty trimmed string")
    return value


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return decimal_text(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"metadata contains unsupported value: {type(value).__name__}")


def _json_copy(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping):
        raise TypeError("metadata must be a mapping")
    # Metadata is intentionally copied so callers cannot mutate a frozen snapshot.
    return MappingProxyType(_json_safe(dict(value)))


def _symbol(value: str, field_name: str = "symbol") -> str:
    value = _identifier(value, field_name).upper()
    return value


def _side(value: str, field_name: str = "side") -> str:
    value = _identifier(value, field_name).lower()
    if value not in {"long", "short"}:
        raise ValueError(f"{field_name} must be long or short")
    return value


def _state(value: str, field_name: str = "state") -> str:
    return _identifier(value, field_name).upper()


def _action(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("action must be a string")
    action = value.strip().upper().replace("-", "_")
    if action not in ACTIONS:
        raise ValueError(f"action must be one of {sorted(ACTIONS)}")
    return action


def _tuple_strings(values: tuple[str, ...] | list[str] | set[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{field_name} must be a collection of strings")
    result = tuple(_identifier(str(value), field_name) for value in values)
    if not result:
        raise ValueError(f"{field_name} must not be empty")
    if len(set(result)) != len(result):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


@dataclass(frozen=True)
class HardLimits:
    """Immutable policy boundary carried by a decision snapshot."""

    allowed_symbols: tuple[str, ...]
    allowed_sides: tuple[str, ...]
    allowed_states: tuple[str, ...]
    max_size: Decimal
    max_exposure: Decimal

    def __post_init__(self) -> None:
        symbols = tuple(_symbol(value, "allowed_symbols") for value in self.allowed_symbols)
        sides = tuple(_side(value, "allowed_sides") for value in self.allowed_sides)
        states = tuple(_state(value, "allowed_states") for value in self.allowed_states)
        if not symbols or len(set(symbols)) != len(symbols):
            raise ValueError("allowed_symbols must be non-empty and unique")
        if not sides or len(set(sides)) != len(sides):
            raise ValueError("allowed_sides must be non-empty and unique")
        if not states or len(set(states)) != len(states):
            raise ValueError("allowed_states must be non-empty and unique")
        max_size = _decimal(self.max_size, "max_size")
        max_exposure = _decimal(self.max_exposure, "max_exposure")
        if max_size < 0 or max_exposure < 0:
            raise ValueError("max_size and max_exposure must be non-negative")
        object.__setattr__(self, "allowed_symbols", symbols)
        object.__setattr__(self, "allowed_sides", sides)
        object.__setattr__(self, "allowed_states", states)
        object.__setattr__(self, "max_size", max_size)
        object.__setattr__(self, "max_exposure", max_exposure)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_symbols": list(self.allowed_symbols),
            "allowed_sides": list(self.allowed_sides),
            "allowed_states": list(self.allowed_states),
            "max_size": decimal_text(self.max_size, "max_size"),
            "max_exposure": decimal_text(self.max_exposure, "max_exposure"),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "HardLimits":
        return cls(
            allowed_symbols=tuple(data["allowed_symbols"]),
            allowed_sides=tuple(data["allowed_sides"]),
            allowed_states=tuple(data["allowed_states"]),
            max_size=_decimal(data["max_size"], "max_size"),
            max_exposure=_decimal(data["max_exposure"], "max_exposure"),
        )


@dataclass(frozen=True)
class DecisionOpportunitySnapshot:
    """Read-only input snapshot for a proposal adapter."""

    opportunity_id: str
    snapshot_at: str
    feature_as_of: str
    symbol: str
    side: str
    state: str
    ref_price: Decimal
    sl_pct: Decimal
    loss_budget: Decimal
    size: Decimal
    exposure: Decimal
    hard_limits: HardLimits
    features: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = SNAPSHOT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SNAPSHOT_SCHEMA_VERSION:
            raise ValueError(f"unsupported snapshot schema: {self.schema_version}")
        object.__setattr__(self, "opportunity_id", _identifier(self.opportunity_id, "opportunity_id"))
        object.__setattr__(self, "snapshot_at", _timestamp(self.snapshot_at, "snapshot_at"))
        object.__setattr__(self, "feature_as_of", _timestamp(self.feature_as_of, "feature_as_of"))
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        object.__setattr__(self, "side", _side(self.side))
        object.__setattr__(self, "state", _state(self.state))
        ref_price = _decimal(self.ref_price, "ref_price")
        sl_pct = _decimal(self.sl_pct, "sl_pct")
        loss_budget = _decimal(self.loss_budget, "loss_budget")
        size = _decimal(self.size, "size")
        exposure = _decimal(self.exposure, "exposure")
        if ref_price <= 0:
            raise ValueError("ref_price must be positive")
        if min(sl_pct, loss_budget, size, exposure) < 0:
            raise ValueError("sl_pct, loss_budget, size, and exposure must be non-negative")
        if self.symbol not in self.hard_limits.allowed_symbols:
            raise ValueError("snapshot symbol is outside hard allowlist")
        if self.side not in self.hard_limits.allowed_sides:
            raise ValueError("snapshot side is outside hard allowlist")
        if self.state not in self.hard_limits.allowed_states:
            raise ValueError("snapshot state is outside hard allowlist")
        if size > self.hard_limits.max_size or exposure > self.hard_limits.max_exposure:
            raise ValueError("snapshot exceeds hard size or exposure limit")
        for name, value in (("ref_price", ref_price), ("sl_pct", sl_pct), ("loss_budget", loss_budget), ("size", size), ("exposure", exposure)):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "features", _json_copy(self.features))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "opportunity_id": self.opportunity_id,
            "snapshot_at": self.snapshot_at,
            "feature_as_of": self.feature_as_of,
            "symbol": self.symbol,
            "side": self.side,
            "state": self.state,
            "ref_price": decimal_text(self.ref_price, "ref_price"),
            "sl_pct": decimal_text(self.sl_pct, "sl_pct"),
            "loss_budget": decimal_text(self.loss_budget, "loss_budget"),
            "size": decimal_text(self.size, "size"),
            "exposure": decimal_text(self.exposure, "exposure"),
            "hard_limits": self.hard_limits.to_dict(),
            "features": dict(self.features),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DecisionOpportunitySnapshot":
        return cls(
            schema_version=data.get("schema_version", SNAPSHOT_SCHEMA_VERSION),
            opportunity_id=data["opportunity_id"],
            snapshot_at=data["snapshot_at"],
            feature_as_of=data["feature_as_of"],
            symbol=data["symbol"],
            side=data["side"],
            state=data["state"],
            ref_price=_decimal(data["ref_price"], "ref_price"),
            sl_pct=_decimal(data["sl_pct"], "sl_pct"),
            loss_budget=_decimal(data["loss_budget"], "loss_budget"),
            size=_decimal(data["size"], "size"),
            exposure=_decimal(data["exposure"], "exposure"),
            hard_limits=HardLimits.from_dict(data["hard_limits"]),
            features=data.get("features", {}),
        )


@dataclass(frozen=True)
class ProposalDraft:
    """Candidate returned by an adapter before deterministic validation."""

    proposal_id: str
    opportunity_id: str
    decision_timestamp: str
    feature_as_of: str
    model_version: str
    policy_version: str
    action: str
    rationale: str
    symbol: str
    side: str
    state: str
    ref_price: Decimal
    sl_pct: Decimal
    loss_budget: Decimal
    size: Decimal
    exposure: Decimal
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = PROPOSAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PROPOSAL_SCHEMA_VERSION:
            raise ValueError(f"unsupported proposal schema: {self.schema_version}")
        for name in ("proposal_id", "opportunity_id", "model_version", "policy_version"):
            object.__setattr__(self, name, _identifier(getattr(self, name), name))
        object.__setattr__(self, "decision_timestamp", _timestamp(self.decision_timestamp, "decision_timestamp"))
        object.__setattr__(self, "feature_as_of", _timestamp(self.feature_as_of, "feature_as_of"))
        object.__setattr__(self, "action", _action(self.action))
        if not isinstance(self.rationale, str) or not self.rationale.strip() or len(self.rationale.strip()) > 500:
            raise ValueError("rationale must be 1 to 500 characters")
        object.__setattr__(self, "rationale", self.rationale.strip())
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        object.__setattr__(self, "side", _side(self.side))
        object.__setattr__(self, "state", _state(self.state))
        for name in ("ref_price", "sl_pct", "loss_budget", "size", "exposure"):
            object.__setattr__(self, name, _decimal(getattr(self, name), name))
        if self.ref_price <= 0:
            raise ValueError("ref_price must be positive")
        if min(self.sl_pct, self.loss_budget, self.size, self.exposure) < 0:
            raise ValueError("proposal numeric fields must be non-negative")
        object.__setattr__(self, "metadata", _json_copy(self.metadata))

    @classmethod
    def from_snapshot(
        cls,
        snapshot: DecisionOpportunitySnapshot,
        *,
        proposal_id: str,
        model_version: str,
        policy_version: str,
        action: str,
        rationale: str,
        decision_timestamp: str | None = None,
        feature_as_of: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        **overrides: Any,
    ) -> "ProposalDraft":
        values: dict[str, Any] = {
            "proposal_id": proposal_id,
            "opportunity_id": snapshot.opportunity_id,
            "decision_timestamp": decision_timestamp or utc_now_iso(),
            "feature_as_of": feature_as_of or snapshot.feature_as_of,
            "model_version": model_version,
            "policy_version": policy_version,
            "action": action,
            "rationale": rationale,
            "symbol": snapshot.symbol,
            "side": snapshot.side,
            "state": snapshot.state,
            "ref_price": snapshot.ref_price,
            "sl_pct": snapshot.sl_pct,
            "loss_budget": snapshot.loss_budget,
            "size": snapshot.size,
            "exposure": snapshot.exposure,
            "metadata": metadata or {},
        }
        values.update(overrides)
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "proposal_id": self.proposal_id,
            "opportunity_id": self.opportunity_id,
            "decision_timestamp": self.decision_timestamp,
            "feature_as_of": self.feature_as_of,
            "model_version": self.model_version,
            "policy_version": self.policy_version,
            "action": self.action,
            "rationale": self.rationale,
            "symbol": self.symbol,
            "side": self.side,
            "state": self.state,
            "ref_price": decimal_text(self.ref_price, "ref_price"),
            "sl_pct": decimal_text(self.sl_pct, "sl_pct"),
            "loss_budget": decimal_text(self.loss_budget, "loss_budget"),
            "size": decimal_text(self.size, "size"),
            "exposure": decimal_text(self.exposure, "exposure"),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProposalDraft":
        return cls(
            schema_version=data.get("schema_version", PROPOSAL_SCHEMA_VERSION),
            proposal_id=data["proposal_id"],
            opportunity_id=data["opportunity_id"],
            decision_timestamp=data["decision_timestamp"],
            feature_as_of=data["feature_as_of"],
            model_version=data["model_version"],
            policy_version=data["policy_version"],
            action=data["action"],
            rationale=data["rationale"],
            symbol=data["symbol"],
            side=data["side"],
            state=data["state"],
            ref_price=_decimal(data["ref_price"], "ref_price"),
            sl_pct=_decimal(data["sl_pct"], "sl_pct"),
            loss_budget=_decimal(data["loss_budget"], "loss_budget"),
            size=_decimal(data["size"], "size"),
            exposure=_decimal(data["exposure"], "exposure"),
            metadata=data.get("metadata", {}),
        )


def parse_plan_actions(raw: Any) -> tuple[tuple[dict[str, Any], ...], str | None]:
    """Parse optional ``metadata.plan_actions``; one decision may list 1-4 steps."""
    if raw is None:
        return (), None
    if not isinstance(raw, list):
        return (), "PLAN_INVALID"
    if not raw:
        return (), "PLAN_EMPTY"
    if len(raw) > PLAN_ACTIONS_MAX:
        return (), "PLAN_TOO_LONG"
    steps: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            return (), "PLAN_INVALID"
        action = str(item.get("action", "")).strip().upper().replace("-", "_")
        if action not in ACTIONS:
            return (), "PLAN_ACTION_INVALID"
        extra = set(item) - _PLAN_STEP_KEYS
        if extra:
            return (), "PLAN_INVALID"
        step = dict(item)
        step["action"] = action
        steps.append(step)
    return tuple(steps), None


def proposal_with_step(proposal: ProposalDraft, index: int, step: Mapping[str, Any]) -> ProposalDraft:
    """Clone a proposal into one plan step; does not dispatch."""
    data = dict(proposal.to_dict())
    data["proposal_id"] = f"{proposal.proposal_id}:s{index}"
    data["action"] = step["action"]
    metadata = dict(proposal.metadata)
    metadata.pop("plan_actions", None)
    role_by_action = {
        "OPEN": "entry",
        "CLOSE": "reduce",
        "REDUCE": "reduce",
        "ADJUST_SL": "adjust_sl",
        "CANCEL": "cancel",
    }
    metadata["order_role"] = role_by_action.get(step["action"], "entry")
    if step["action"] in {"CLOSE", "REDUCE"}:
        metadata["reduce_only"] = True
    else:
        metadata.pop("reduce_only", None)
    for key in ("stop_loss", "take_profit", "order_type", "order_role", "reduce_only", "leverage"):
        if key in step:
            metadata[key] = step[key]
    if "size" in step:
        size = step["size"]
        data["size"] = format(size, "f") if isinstance(size, Decimal) else str(size)
    data["metadata"] = metadata
    return ProposalDraft.from_dict(data)


def iter_plan_proposals(proposal: ProposalDraft) -> tuple[tuple[ProposalDraft, ...], str | None]:
    """Expand one proposal into executable steps. Missing list = single action."""
    raw = proposal.metadata.get("plan_actions")
    if raw is None:
        return (proposal,), None
    steps, error = parse_plan_actions(raw)
    if error:
        return (proposal,), error
    return tuple(proposal_with_step(proposal, index, step) for index, step in enumerate(steps)), None


@dataclass(frozen=True)
class ValidationError:
    code: str
    field: str
    message: str
    expected: Any = None
    actual: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "field": self.field,
            "message": self.message,
            "expected": self.expected,
            "actual": self.actual,
        }


@dataclass(frozen=True)
class ProposalRecord:
    """Immutable audit record.  Records are written once and never modified."""

    proposal_id: str
    opportunity_id: str
    recorded_at: str
    result: str
    snapshot: DecisionOpportunitySnapshot
    proposal: ProposalDraft | None
    validation_errors: tuple[ValidationError, ...] = ()
    raw_candidate: Mapping[str, Any] | None = None
    schema_version: str = PROPOSAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PROPOSAL_SCHEMA_VERSION:
            raise ValueError(f"unsupported proposal record schema: {self.schema_version}")
        if self.result not in {RESULT_ACCEPTED, RESULT_REJECTED}:
            raise ValueError("result must be ACCEPTED or REJECTED")
        object.__setattr__(self, "proposal_id", _identifier(self.proposal_id, "proposal_id"))
        object.__setattr__(self, "opportunity_id", _identifier(self.opportunity_id, "opportunity_id"))
        object.__setattr__(self, "recorded_at", _timestamp(self.recorded_at, "recorded_at"))
        if self.proposal is not None and self.proposal.proposal_id != self.proposal_id:
            raise ValueError("record proposal_id does not match proposal")
        if self.proposal is not None and self.proposal.opportunity_id != self.opportunity_id:
            raise ValueError("record opportunity_id does not match proposal")
        if self.result == RESULT_ACCEPTED and (self.proposal is None or self.validation_errors):
            raise ValueError("accepted record requires a proposal and no validation errors")
        if self.result == RESULT_REJECTED and not self.validation_errors:
            raise ValueError("rejected record requires validation errors")
        object.__setattr__(self, "validation_errors", tuple(self.validation_errors))
        if self.raw_candidate is not None:
            object.__setattr__(self, "raw_candidate", _json_copy(self.raw_candidate))

    @classmethod
    def accepted(cls, snapshot: DecisionOpportunitySnapshot, proposal: ProposalDraft, recorded_at: str | None = None) -> "ProposalRecord":
        return cls(
            proposal_id=proposal.proposal_id,
            opportunity_id=snapshot.opportunity_id,
            recorded_at=recorded_at or utc_now_iso(),
            result=RESULT_ACCEPTED,
            snapshot=snapshot,
            proposal=proposal,
        )

    @classmethod
    def rejected(
        cls,
        snapshot: DecisionOpportunitySnapshot,
        proposal_id: str,
        errors: tuple[ValidationError, ...],
        proposal: ProposalDraft | None = None,
        raw_candidate: Mapping[str, Any] | None = None,
        recorded_at: str | None = None,
    ) -> "ProposalRecord":
        return cls(
            proposal_id=proposal_id,
            opportunity_id=snapshot.opportunity_id,
            recorded_at=recorded_at or utc_now_iso(),
            result=RESULT_REJECTED,
            snapshot=snapshot,
            proposal=proposal,
            validation_errors=errors,
            raw_candidate=raw_candidate,
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "record_type": "proposal",
            "proposal_id": self.proposal_id,
            "opportunity_id": self.opportunity_id,
            "recorded_at": self.recorded_at,
            "result": self.result,
            "snapshot": self.snapshot.to_dict(),
            "proposal": self.proposal.to_dict() if self.proposal is not None else None,
            "validation_errors": [error.to_dict() for error in self.validation_errors],
        }
        if self.raw_candidate is not None:
            result["raw_candidate"] = dict(self.raw_candidate)
        return result

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProposalRecord":
        errors = tuple(
            ValidationError(
                code=item["code"],
                field=item["field"],
                message=item["message"],
                expected=item.get("expected"),
                actual=item.get("actual"),
            )
            for item in data.get("validation_errors", [])
        )
        proposal_data = data.get("proposal")
        return cls(
            schema_version=data.get("schema_version", PROPOSAL_SCHEMA_VERSION),
            proposal_id=data["proposal_id"],
            opportunity_id=data["opportunity_id"],
            recorded_at=data["recorded_at"],
            result=data["result"],
            snapshot=DecisionOpportunitySnapshot.from_dict(data["snapshot"]),
            proposal=ProposalDraft.from_dict(proposal_data) if proposal_data is not None else None,
            validation_errors=errors,
            raw_candidate=data.get("raw_candidate"),
        )
