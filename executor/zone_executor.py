"""Standalone dry-run intent executor for zone trading.

This module deliberately contains no exchange client and no network code.  It
only creates deterministic order intents and advances their local state from
caller-supplied observations.  A later P1 integration can persist the records
through :class:`executor.zone_store.ZoneStore` and dispatch them elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
import hashlib
import json
from typing import Any, Iterable, Mapping

from .zone_store import ZoneStore


class IntentRole(str, Enum):
    ENTRY = "entry"
    DCA = "dca"
    CANCEL = "cancel"
    EMERGENCY_CLOSE = "emergency_close"


class IntentState(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    PARTIAL = "partially_filled"  # readable compatibility alias
    FILLED = "filled"
    TIMED_OUT = "timed_out"
    UNKNOWN = "unknown"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    DRY_RUN_RECORDED = "dry_run_recorded"


class OrderEventType(str, Enum):
    ACCEPTED = "accepted"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    RECONCILED_OPEN = "reconciled_open"
    RECONCILED_ABSENT = "reconciled_absent"
    DRY_RUN_RECORDED = "dry_run_recorded"


class RiskTrigger(str, Enum):
    LOSS_BUDGET = "LOSS_BUDGET"
    PRICE_SL = "PRICE_SL"
    BOTH = "BOTH"


class ZoneState(str, Enum):
    PLANNED = "planned"
    WORKING = "working"
    ACTIVE = "active"
    RISK_STOPPING = "risk_stopping"
    CLOSED = "closed"


class IntentError(ValueError):
    """Base error for invalid local intent operations."""


class IdempotencyConflict(IntentError):
    """The same deterministic key was requested with different parameters."""


class InvalidTransition(IntentError):
    """An observed order event cannot follow the local state."""


class UnknownIntent(KeyError):
    """An event references an intent not known by this local executor."""


def _decimal(value: Decimal | int | str | float, *, field_name: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise IntentError(f"{field_name} must be a decimal") from exc
    if not result.is_finite():
        raise IntentError(f"{field_name} must be finite")
    return result


def _oid_value(value: Any) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def deterministic_client_oid(
    zone_id: str,
    role: IntentRole | str,
    level: int | None = None,
    revision: int = 0,
    target_client_oid: str | None = None,
    prefix: str = "zdr",
) -> str:
    """Return a stable, bounded client id for one logical order intent.

    The canonical key is hashed instead of incorporating wall-clock time or a
    random value.  Consequently retrying the same logical operation cannot
    manufacture a second order id.  The 28-character result also stays below
    the common exchange client-id limit; the exchange itself is not contacted.
    """
    if not zone_id:
        raise IntentError("zone_id must not be empty")
    if revision < 0:
        raise IntentError("revision must be non-negative")
    role_value = _oid_value(role)
    canonical = "\x1f".join(
        (
            prefix,
            zone_id,
            role_value,
            "" if level is None else str(level),
            str(revision),
            target_client_oid or "",
        )
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


@dataclass(frozen=True)
class ZoneOrderSpec:
    """Input for one entry or DCA intent."""

    role: IntentRole | str
    level: int
    quantity: Decimal | int | str | float
    price: Decimal | int | str | float
    side: str
    position_side: str = ""
    revision: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def normalized(self) -> "ZoneOrderSpec":
        try:
            role = self.role if isinstance(self.role, IntentRole) else IntentRole(str(self.role))
        except ValueError as exc:
            raise IntentError(f"unsupported order role: {self.role}") from exc
        quantity = _decimal(self.quantity, field_name="quantity")
        price = _decimal(self.price, field_name="price")
        if role not in (IntentRole.ENTRY, IntentRole.DCA):
            raise IntentError("zone order specs can only create entry or DCA intents")
        if self.level < 0:
            raise IntentError("level must be non-negative")
        if quantity <= 0:
            raise IntentError("quantity must be greater than zero")
        if price <= 0:
            raise IntentError("price must be greater than zero")
        if not self.side:
            raise IntentError("side must not be empty")
        if self.revision < 0:
            raise IntentError("revision must be non-negative")
        return ZoneOrderSpec(
            role=role,
            level=self.level,
            quantity=quantity,
            price=price,
            side=self.side,
            position_side=self.position_side,
            revision=self.revision,
            metadata=dict(self.metadata),
        )


@dataclass
class OrderIntent:
    """A local order or cancellation record.  It is never dispatched here."""

    intent_id: str
    client_oid: str
    zone_id: str
    role: IntentRole
    level: int | None
    revision: int
    quantity: Decimal
    price: Decimal | None
    side: str
    position_side: str
    state: IntentState = IntentState.PENDING
    filled_quantity: Decimal = Decimal("0")
    target_client_oid: str | None = None
    dry_run: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    last_event: str | None = None

    @property
    def remaining_quantity(self) -> Decimal:
        return max(Decimal("0"), self.quantity - self.filled_quantity)

    @property
    def is_entry_like(self) -> bool:
        return self.role in (IntentRole.ENTRY, IntentRole.DCA)

    @property
    def terminal(self) -> bool:
        return self.state in {
            IntentState.FILLED,
            IntentState.CANCELLED,
            IntentState.REJECTED,
            IntentState.DRY_RUN_RECORDED,
        }

    def as_record(self) -> dict[str, Any]:
        """Return a persistence-safe record with Decimal values as strings."""
        return {
            "intent_id": self.intent_id,
            "client_oid": self.client_oid,
            "zone_id": self.zone_id,
            "role": self.role.value,
            "level": self.level,
            "revision": self.revision,
            "quantity": str(self.quantity),
            "price": None if self.price is None else str(self.price),
            "side": self.side,
            "position_side": self.position_side,
            "state": self.state.value,
            "filled_quantity": str(self.filled_quantity),
            "remaining_quantity": str(self.remaining_quantity),
            "target_client_oid": self.target_client_oid,
            "dry_run": self.dry_run,
            "metadata": dict(self.metadata),
            "last_event": self.last_event,
        }


@dataclass(frozen=True)
class OrderObservation:
    client_oid: str
    event: OrderEventType | str
    filled_quantity: Decimal | int | str | float | None = None
    message: str = ""

    def normalized(self) -> "OrderObservation":
        try:
            event = self.event if isinstance(self.event, OrderEventType) else OrderEventType(str(self.event))
        except ValueError as exc:
            raise IntentError(f"unsupported order event: {self.event}") from exc
        quantity = None
        if self.filled_quantity is not None:
            quantity = _decimal(self.filled_quantity, field_name="filled_quantity")
        return OrderObservation(self.client_oid, event, quantity, self.message)


@dataclass(frozen=True)
class RiskAction:
    zone_id: str
    trigger: RiskTrigger
    cancelled_client_oids: tuple[str, ...]
    cancellation_intent_oids: tuple[str, ...]
    emergency_close_client_oid: str | None
    dry_run: bool = True


@dataclass
class _Zone:
    zone_id: str
    intents: dict[str, OrderIntent]
    position_quantity: Decimal
    position_side: str
    state: ZoneState = ZoneState.PLANNED
    triggers: set[RiskTrigger] = field(default_factory=set)
    events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def effective_trigger(self) -> RiskTrigger | None:
        if RiskTrigger.LOSS_BUDGET in self.triggers and RiskTrigger.PRICE_SL in self.triggers:
            return RiskTrigger.BOTH
        if RiskTrigger.LOSS_BUDGET in self.triggers:
            return RiskTrigger.LOSS_BUDGET
        if RiskTrigger.PRICE_SL in self.triggers:
            return RiskTrigger.PRICE_SL
        if RiskTrigger.BOTH in self.triggers:
            return RiskTrigger.BOTH
        return None


class ZoneExecutor:
    """Local-only deterministic executor for a single or multiple zones.

    ``ZoneExecutor`` is intentionally a dry-run recorder, not an API client.
    No method sends HTTP, reads credentials, creates a socket, or interprets
    ``GROK_TRADER_ALLOW_LIVE``.  A production P1 adapter can consume the
    records and events through the ``ZoneStore`` protocol.
    """

    def __init__(self, store: ZoneStore | None = None):
        self.store = store
        self._zones: dict[str, _Zone] = {}
        self._intent_index: dict[str, OrderIntent] = {}

    def create_zone(
        self,
        zone_id: str,
        orders: Iterable[ZoneOrderSpec],
        *,
        position_quantity: Decimal | int | str | float = Decimal("0"),
        position_side: str = "",
    ) -> tuple[OrderIntent, ...]:
        """Create deterministic entry/DCA intents, idempotently.

        Repeating the exact request returns the existing records.  Reusing a
        zone id with a changed order payload raises ``IdempotencyConflict``.
        """
        if not zone_id:
            raise IntentError("zone_id must not be empty")
        position = _decimal(position_quantity, field_name="position_quantity")
        if position < 0:
            raise IntentError("position_quantity cannot be negative")
        normalized = tuple(order.normalized() for order in orders)
        if not normalized:
            raise IntentError("at least one entry or DCA order is required")
        keys = [
            deterministic_client_oid(zone_id, order.role, order.level, order.revision)
            for order in normalized
        ]
        if len(set(keys)) != len(keys):
            raise IdempotencyConflict("duplicate deterministic order key in zone")

        existing = self._zones.get(zone_id)
        if existing is not None:
            existing_specs = tuple(
                (
                    intent.role,
                    intent.level,
                    intent.revision,
                    intent.quantity,
                    intent.price,
                    intent.side,
                    intent.position_side,
                    json.dumps(intent.metadata, sort_keys=True, default=str),
                )
                for intent in sorted(
                    (item for item in existing.intents.values() if item.is_entry_like),
                    key=lambda item: (item.level, item.role.value, item.revision, item.client_oid),
                )
            )
            requested_specs = tuple(
                (
                    order.role,
                    order.level,
                    order.revision,
                    order.quantity,
                    order.price,
                    order.side,
                    order.position_side or existing.position_side,
                    json.dumps(dict(order.metadata), sort_keys=True, default=str),
                )
                for order in sorted(normalized, key=lambda item: (item.level, item.role.value, item.revision))
            )
            if existing_specs != requested_specs:
                raise IdempotencyConflict(f"zone {zone_id!r} already exists with another payload")
            return self.intents(zone_id)

        zone = _Zone(zone_id, {}, position, position_side)
        self._zones[zone_id] = zone
        for order, client_oid in zip(normalized, keys):
            intent = OrderIntent(
                intent_id=client_oid,
                client_oid=client_oid,
                zone_id=zone_id,
                role=order.role if isinstance(order.role, IntentRole) else IntentRole(str(order.role)),
                level=order.level,
                revision=order.revision,
                quantity=order.quantity if isinstance(order.quantity, Decimal) else _decimal(order.quantity, field_name="quantity"),
                price=order.price if isinstance(order.price, Decimal) else _decimal(order.price, field_name="price"),
                side=order.side,
                position_side=order.position_side or position_side,
                metadata=dict(order.metadata),
            )
            zone.intents[client_oid] = intent
            self._intent_index[client_oid] = intent
            self._persist_intent(intent)
        self._record_zone_event(zone, "zone_created")
        self._persist_zone(zone)
        return self.intents(zone_id)

    def intents(self, zone_id: str) -> tuple[OrderIntent, ...]:
        zone = self._get_zone(zone_id)
        return tuple(
            sorted(
                zone.intents.values(),
                key=lambda item: (
                    item.level is None,
                    -1 if item.level is None else item.level,
                    item.role.value,
                    item.revision,
                    item.client_oid,
                ),
            )
        )

    def get_intent(self, client_oid: str) -> OrderIntent:
        try:
            return self._intent_index[client_oid]
        except KeyError as exc:
            raise UnknownIntent(client_oid) from exc

    def mark_submitted(self, client_oid: str) -> OrderIntent:
        """Record a local dry-run submission acknowledgement."""
        return self.apply_observation(OrderObservation(client_oid, OrderEventType.ACCEPTED))

    def apply_observation(self, observation: OrderObservation) -> OrderIntent:
        """Apply one caller-supplied exchange observation locally.

        Fill quantity is cumulative for ``PARTIAL_FILL``.  Replaying an equal
        observation is idempotent; a lower cumulative quantity is rejected.
        Timeout and unknown are explicit states and require later reconcile
        observations instead of silently retrying with a new client id.
        """
        event = observation.normalized()
        intent = self.get_intent(event.client_oid)
        zone = self._get_zone(intent.zone_id)
        before = intent.state
        quantity = event.filled_quantity

        if event.event is OrderEventType.PARTIAL_FILL:
            if quantity is None:
                raise IntentError("partial_fill requires cumulative filled_quantity")
            if quantity < intent.filled_quantity:
                raise InvalidTransition("filled quantity cannot move backwards")
            if quantity == intent.quantity:
                event = OrderObservation(event.client_oid, OrderEventType.FILLED, quantity, event.message)
            elif quantity <= 0:
                raise IntentError("partial fill must be greater than zero")
            else:
                self._ensure_active(intent, event.event, allow_partial=True)
                intent.filled_quantity = quantity
                intent.state = IntentState.PARTIALLY_FILLED
                intent.last_event = event.event.value
                self._record_order_event(zone, intent, event)
                self._persist_intent(intent)
                self._refresh_zone_state(zone)
                return intent

        if event.event is OrderEventType.FILLED:
            fill = intent.quantity if quantity in (None, Decimal("0")) else quantity
            if fill != intent.quantity:
                raise IntentError("filled event must equal the intent quantity")
            if intent.filled_quantity > fill:
                raise InvalidTransition("filled quantity cannot move backwards")
            self._ensure_active(intent, event.event, allow_partial=True)
            intent.filled_quantity = fill
            intent.state = IntentState.FILLED
        elif event.event is OrderEventType.ACCEPTED:
            self._ensure_state(intent, {IntentState.PENDING, IntentState.TIMED_OUT, IntentState.UNKNOWN, IntentState.CANCEL_REQUESTED}, event.event)
            intent.state = IntentState.PARTIALLY_FILLED if intent.filled_quantity else IntentState.ACCEPTED
        elif event.event is OrderEventType.TIMEOUT:
            self._ensure_state(intent, {IntentState.PENDING, IntentState.ACCEPTED, IntentState.PARTIALLY_FILLED}, event.event)
            intent.state = IntentState.TIMED_OUT
        elif event.event is OrderEventType.UNKNOWN:
            self._ensure_state(intent, {IntentState.PENDING, IntentState.ACCEPTED, IntentState.PARTIALLY_FILLED, IntentState.TIMED_OUT, IntentState.CANCEL_REQUESTED}, event.event)
            intent.state = IntentState.UNKNOWN
        elif event.event is OrderEventType.CANCEL_REQUESTED:
            self._ensure_state(intent, {IntentState.PENDING, IntentState.ACCEPTED, IntentState.PARTIALLY_FILLED, IntentState.TIMED_OUT, IntentState.UNKNOWN, IntentState.CANCEL_REQUESTED}, event.event)
            intent.state = IntentState.CANCEL_REQUESTED
        elif event.event is OrderEventType.CANCELLED:
            self._ensure_state(intent, {IntentState.PENDING, IntentState.ACCEPTED, IntentState.PARTIALLY_FILLED, IntentState.TIMED_OUT, IntentState.UNKNOWN, IntentState.CANCEL_REQUESTED}, event.event)
            intent.state = IntentState.CANCELLED
        elif event.event is OrderEventType.REJECTED:
            self._ensure_state(intent, {IntentState.PENDING, IntentState.ACCEPTED, IntentState.TIMED_OUT, IntentState.UNKNOWN, IntentState.CANCEL_REQUESTED}, event.event)
            intent.state = IntentState.REJECTED
        elif event.event is OrderEventType.RECONCILED_OPEN:
            self._ensure_state(intent, {IntentState.TIMED_OUT, IntentState.UNKNOWN, IntentState.CANCEL_REQUESTED}, event.event)
            intent.state = IntentState.PARTIALLY_FILLED if intent.filled_quantity else IntentState.ACCEPTED
        elif event.event is OrderEventType.RECONCILED_ABSENT:
            self._ensure_state(intent, {IntentState.TIMED_OUT, IntentState.UNKNOWN, IntentState.CANCEL_REQUESTED}, event.event)
            intent.state = IntentState.CANCELLED
        elif event.event is OrderEventType.DRY_RUN_RECORDED:
            self._ensure_state(intent, {IntentState.PENDING, IntentState.DRY_RUN_RECORDED}, event.event)
            intent.state = IntentState.DRY_RUN_RECORDED
        else:  # pragma: no cover, enum normalization makes this unreachable
            raise IntentError(f"unsupported event: {event.event}")

        intent.last_event = event.event.value
        if quantity is not None and event.event not in (OrderEventType.TIMEOUT, OrderEventType.UNKNOWN):
            if quantity < intent.filled_quantity or quantity > intent.quantity:
                raise IntentError("filled_quantity is outside the intent quantity")
            intent.filled_quantity = quantity
        self._record_order_event(zone, intent, event, before=before)
        self._persist_intent(intent)
        self._refresh_zone_state(zone)
        return intent

    def record_fill(self, client_oid: str, cumulative_filled_quantity: Decimal | int | str | float) -> OrderIntent:
        return self.apply_observation(
            OrderObservation(client_oid, OrderEventType.PARTIAL_FILL, cumulative_filled_quantity)
        )

    def request_cancel(self, client_oid: str) -> OrderIntent | None:
        """Create one local cancellation intent for an entry or DCA order."""
        original = self.get_intent(client_oid)
        if not original.is_entry_like or original.terminal:
            return None
        zone = self._get_zone(original.zone_id)
        self.apply_observation(OrderObservation(client_oid, OrderEventType.CANCEL_REQUESTED))
        cancel_oid = deterministic_client_oid(
            zone.zone_id,
            IntentRole.CANCEL,
            original.level,
            original.revision,
            target_client_oid=original.client_oid,
        )
        existing = self._intent_index.get(cancel_oid)
        if existing is not None:
            return existing
        cancel = OrderIntent(
            intent_id=cancel_oid,
            client_oid=cancel_oid,
            zone_id=zone.zone_id,
            role=IntentRole.CANCEL,
            level=original.level,
            revision=original.revision,
            quantity=original.remaining_quantity,
            price=None,
            side="cancel",
            position_side=original.position_side,
            state=IntentState.DRY_RUN_RECORDED,
            target_client_oid=original.client_oid,
            metadata={"target_client_oid": original.client_oid},
        )
        zone.intents[cancel_oid] = cancel
        self._intent_index[cancel_oid] = cancel
        self._record_order_event(zone, cancel, OrderObservation(cancel_oid, OrderEventType.DRY_RUN_RECORDED))
        self._persist_intent(cancel)
        self._persist_zone(zone)
        return cancel

    def on_risk_trigger(self, zone_id: str, trigger: RiskTrigger | str) -> RiskAction:
        """Cancel open entry/DCA intents and record a dry-run emergency close."""
        try:
            trigger_value = trigger if isinstance(trigger, RiskTrigger) else RiskTrigger(str(trigger))
        except ValueError as exc:
            raise IntentError(f"unsupported risk trigger: {trigger}") from exc
        if trigger_value is RiskTrigger.BOTH:
            risk_parts = (RiskTrigger.LOSS_BUDGET, RiskTrigger.PRICE_SL)
        else:
            risk_parts = (trigger_value,)
        zone = self._get_zone(zone_id)
        zone.triggers.update(risk_parts)
        zone.state = ZoneState.RISK_STOPPING

        cancelled: list[str] = []
        cancellation_oids: list[str] = []
        for intent in self.intents(zone_id):
            if not intent.is_entry_like or intent.terminal:
                continue
            cancelled.append(intent.client_oid)
            cancellation = self.request_cancel(intent.client_oid)
            if cancellation is not None:
                cancellation_oids.append(cancellation.client_oid)

        emergency_oid: str | None = None
        if zone.position_quantity > 0:
            emergency_oid = deterministic_client_oid(zone_id, IntentRole.EMERGENCY_CLOSE)
            emergency = self._intent_index.get(emergency_oid)
            if emergency is None:
                close_side = _close_side(zone.position_side)
                emergency = OrderIntent(
                    intent_id=emergency_oid,
                    client_oid=emergency_oid,
                    zone_id=zone_id,
                    role=IntentRole.EMERGENCY_CLOSE,
                    level=None,
                    revision=0,
                    quantity=zone.position_quantity,
                    price=None,
                    side=close_side,
                    position_side=zone.position_side,
                    state=IntentState.DRY_RUN_RECORDED,
                    metadata={
                        "dry_run_only": True,
                        "risk_trigger": zone.effective_trigger.value if zone.effective_trigger else trigger_value.value,
                    },
                )
                zone.intents[emergency_oid] = emergency
                self._intent_index[emergency_oid] = emergency
                self._persist_intent(emergency)
            else:
                emergency.metadata["risk_trigger"] = zone.effective_trigger.value if zone.effective_trigger else trigger_value.value
                self._persist_intent(emergency)

        self._record_zone_event(zone, "risk_trigger", {"trigger": zone.effective_trigger.value if zone.effective_trigger else trigger_value.value})
        self._persist_zone(zone)
        return RiskAction(
            zone_id=zone_id,
            trigger=zone.effective_trigger or trigger_value,
            cancelled_client_oids=tuple(cancelled),
            cancellation_intent_oids=tuple(cancellation_oids),
            emergency_close_client_oid=emergency_oid,
        )

    # Short aliases make the integration point explicit without requiring a
    # P1 zone_store or CLI to exist in this branch.
    trigger_risk = on_risk_trigger

    def set_position(self, zone_id: str, quantity: Decimal | int | str | float, position_side: str | None = None) -> None:
        zone = self._get_zone(zone_id)
        position = _decimal(quantity, field_name="position_quantity")
        if position < 0:
            raise IntentError("position_quantity cannot be negative")
        zone.position_quantity = position
        if position_side is not None:
            zone.position_side = position_side
        self._persist_zone(zone)

    def snapshot(self, zone_id: str) -> dict[str, Any]:
        zone = self._get_zone(zone_id)
        return {
            "zone_id": zone.zone_id,
            "state": zone.state.value,
            "position_quantity": str(zone.position_quantity),
            "position_side": zone.position_side,
            "risk_trigger": zone.effective_trigger.value if zone.effective_trigger else None,
            "risk_triggers": sorted(trigger.value for trigger in zone.triggers),
            "intents": [intent.as_record() for intent in self.intents(zone_id)],
            "events": list(zone.events),
            "dry_run": True,
        }

    def _get_zone(self, zone_id: str) -> _Zone:
        try:
            return self._zones[zone_id]
        except KeyError as exc:
            raise IntentError(f"unknown zone: {zone_id}") from exc

    @staticmethod
    def _ensure_state(intent: OrderIntent, allowed: set[IntentState], event: OrderEventType) -> None:
        if intent.state in allowed:
            return
        # Event replay is safe for an already-applied terminal event.
        if event is OrderEventType.CANCELLED and intent.state is IntentState.CANCELLED:
            return
        if event is OrderEventType.FILLED and intent.state is IntentState.FILLED:
            return
        raise InvalidTransition(f"{event.value} cannot follow {intent.state.value}")

    @classmethod
    def _ensure_active(cls, intent: OrderIntent, event: OrderEventType, allow_partial: bool = False) -> None:
        allowed = {IntentState.PENDING, IntentState.ACCEPTED, IntentState.TIMED_OUT, IntentState.UNKNOWN, IntentState.CANCEL_REQUESTED}
        if allow_partial:
            allowed.add(IntentState.PARTIALLY_FILLED)
        cls._ensure_state(intent, allowed, event)

    def _refresh_zone_state(self, zone: _Zone) -> None:
        entry_like = [item for item in zone.intents.values() if item.is_entry_like]
        if zone.state is ZoneState.RISK_STOPPING:
            return
        if entry_like and all(item.state in {IntentState.CANCELLED, IntentState.REJECTED, IntentState.FILLED} for item in entry_like):
            zone.state = ZoneState.ACTIVE if zone.position_quantity > 0 else ZoneState.CLOSED
        elif any(item.state in {IntentState.ACCEPTED, IntentState.PARTIALLY_FILLED, IntentState.FILLED} for item in entry_like):
            zone.state = ZoneState.ACTIVE
        else:
            zone.state = ZoneState.WORKING
        self._persist_zone(zone)

    def _record_order_event(
        self,
        zone: _Zone,
        intent: OrderIntent,
        observation: OrderObservation,
        *,
        before: IntentState | None = None,
    ) -> None:
        zone.events.append(
            {
                "kind": "order_event",
                "zone_id": zone.zone_id,
                "client_oid": intent.client_oid,
                "event": _oid_value(observation.event),
                "before": None if before is None else before.value,
                "after": intent.state.value,
                "filled_quantity": str(intent.filled_quantity),
                "message": observation.message,
                "dry_run": True,
            }
        )
        self._persist_event(zone.events[-1])

    def _record_zone_event(self, zone: _Zone, kind: str, data: Mapping[str, Any] | None = None) -> None:
        event = {"kind": kind, "zone_id": zone.zone_id, "dry_run": True}
        if data:
            event.update(dict(data))
        zone.events.append(event)
        self._persist_event(event)

    def _persist_intent(self, intent: OrderIntent) -> None:
        if self.store is not None:
            self.store.save_intent(intent.as_record())

    def _persist_event(self, event: Mapping[str, Any]) -> None:
        if self.store is not None:
            self.store.append_event(dict(event))

    def _persist_zone(self, zone: _Zone) -> None:
        if self.store is not None:
            self.store.save_zone(self.snapshot(zone.zone_id))


# Explicit name for callers that want the safety property in the type name.
DryRunExecutor = ZoneExecutor
DryRunZoneExecutor = ZoneExecutor


def _close_side(position_side: str) -> str:
    value = position_side.lower()
    if value in {"long", "buy"}:
        return "sell"
    if value in {"short", "sell"}:
        return "buy"
    return "close"


__all__ = [
    "DryRunExecutor",
    "DryRunZoneExecutor",
    "IdempotencyConflict",
    "IntentError",
    "IntentRole",
    "IntentState",
    "InvalidTransition",
    "OrderEventType",
    "OrderIntent",
    "OrderObservation",
    "RiskAction",
    "RiskTrigger",
    "UnknownIntent",
    "ZoneExecutor",
    "ZoneOrderSpec",
    "ZoneState",
    "deterministic_client_oid",
]
