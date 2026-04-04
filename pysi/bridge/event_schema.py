from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Union

EventType = Literal["shipment", "arrival", "pull_request", "bind", "inventory_move"]


@dataclass(frozen=True, kw_only=True)
class BaseBridgeEvent:
    """
    Base bridge event.

    NOTE:
    - event_type is init=False here and concretely defined in each subclass.
      This keeps dataclass inheritance initialization safe while still allowing
      static access via BaseBridgeEvent type (e.event_type).
    """

    event_type: EventType = field(init=False)
    event_id: str
    time_bucket: str
    product_id: str
    quantity_cpu: float
    creation_sequence: int
    stable_object_id: str
    source_ref: str
    diff_basis: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate_common(self) -> None:
        if not self.event_id:
            raise ValueError("event_id is required")
        if len(self.time_bucket) != 6 or not self.time_bucket.isdigit():
            raise ValueError("time_bucket must be YYYYWW")
        if self.quantity_cpu < 0:
            raise ValueError("quantity_cpu must be >= 0")
        if not self.stable_object_id:
            raise ValueError("stable_object_id is required")
        if not self.source_ref:
            raise ValueError("source_ref is required")


@dataclass(frozen=True, kw_only=True)
class ShipmentEvent(BaseBridgeEvent):
    event_type: Literal["shipment"] = field(init=False, default="shipment")
    lot_id: str
    from_node: str
    to_node: str
    demand_id: str | None = None
    reason_code: str | None = None

    def validate(self) -> None:
        self.validate_common()
        if not self.lot_id:
            raise ValueError("shipment.lot_id is required")
        if not self.from_node or not self.to_node:
            raise ValueError("shipment.from_node/to_node are required")


@dataclass(frozen=True, kw_only=True)
class ArrivalEvent(BaseBridgeEvent):
    event_type: Literal["arrival"] = field(init=False, default="arrival")
    lot_id: str
    from_node: str
    to_node: str
    reason_code: str | None = None

    def validate(self) -> None:
        self.validate_common()
        if not self.lot_id:
            raise ValueError("arrival.lot_id is required")
        if not self.from_node or not self.to_node:
            raise ValueError("arrival.from_node/to_node are required")


@dataclass(frozen=True, kw_only=True)
class PullRequestEvent(BaseBridgeEvent):
    event_type: Literal["pull_request"] = field(init=False, default="pull_request")
    to_node: str
    from_node: str | None = None
    demand_id: str | None = None
    reason_code: str | None = None

    def validate(self) -> None:
        self.validate_common()
        if not self.to_node:
            raise ValueError("pull_request.to_node is required")


@dataclass(frozen=True, kw_only=True)
class BindEvent(BaseBridgeEvent):
    event_type: Literal["bind"] = field(init=False, default="bind")
    lot_id: str
    demand_id: str
    to_node: str
    from_node: str | None = None
    binding_id: str | None = None
    reason_code: str | None = None

    def validate(self) -> None:
        self.validate_common()
        if not self.lot_id:
            raise ValueError("bind.lot_id is required")
        if not self.demand_id:
            raise ValueError("bind.demand_id is required")
        if not self.to_node:
            raise ValueError("bind.to_node is required")


@dataclass(frozen=True, kw_only=True)
class InventoryMoveEvent(BaseBridgeEvent):
    event_type: Literal["inventory_move"] = field(init=False, default="inventory_move")
    to_node: str
    from_node: str | None = None
    reason_code: str | None = "residual_adjustment"

    def validate(self) -> None:
        self.validate_common()
        if not self.to_node:
            raise ValueError("inventory_move.to_node is required")
        required_keys = ("observed_inventory_delta", "explained_delta", "residual_qty")
        missing = [k for k in required_keys if k not in self.metadata]
        if missing:
            raise ValueError(f"inventory_move.metadata missing keys: {missing}")


BridgeEvent = Union[
    ShipmentEvent,
    ArrivalEvent,
    PullRequestEvent,
    BindEvent,
    InventoryMoveEvent,
]


def validate_event(evt: BridgeEvent) -> None:
    evt.validate()
