from __future__ import annotations

from dataclasses import dataclass
from typing import List

from pysi.bridge.event_schema import (
    ArrivalEvent,
    BindEvent,
    BridgeEvent,
    InventoryMoveEvent,
    PullRequestEvent,
    ShipmentEvent,
)
from pysi.core.kernel.minimal_kernel import FlowEvent


@dataclass
class MappedKernelEvents:
    flow_events: List[FlowEvent]
    sidecar_events: List[BridgeEvent]


def _base_metadata(e: BridgeEvent) -> dict:
    return {
        **e.metadata,
        "bridge_event_type": e.event_type,
        "source_ref": e.source_ref,
        "stable_object_id": e.stable_object_id,
        "diff_basis": e.diff_basis,
    }


def map_bridge_events_to_kernel_v1(events: List[BridgeEvent]) -> MappedKernelEvents:
    """
    Bridge-internal 5 event types are kept explicit through extraction.
    Kernel v1.0 compatibility is applied here at mapper output.
    """

    flow_events: List[FlowEvent] = []
    sidecar_events: List[BridgeEvent] = []

    ordered = sorted(
        events,
        key=lambda e: (e.time_bucket, e.creation_sequence, e.stable_object_id, e.event_id),
    )

    for e in ordered:
        if isinstance(e, ShipmentEvent):
            flow_events.append(
                FlowEvent(
                    flow_id=f"flow-{e.event_id}",
                    lot_id=e.lot_id,
                    event_type="shipment",
                    product_id=e.product_id,
                    from_node=e.from_node,
                    to_node=e.to_node,
                    time_bucket=e.time_bucket,
                    quantity_cpu=e.quantity_cpu,
                    creation_sequence=e.creation_sequence,
                    metadata=_base_metadata(e),
                )
            )

        elif isinstance(e, ArrivalEvent):
            flow_events.append(
                FlowEvent(
                    flow_id=f"flow-{e.event_id}",
                    lot_id=e.lot_id,
                    event_type="arrival",
                    product_id=e.product_id,
                    from_node=e.from_node,
                    to_node=e.to_node,
                    time_bucket=e.time_bucket,
                    quantity_cpu=e.quantity_cpu,
                    creation_sequence=e.creation_sequence,
                    metadata=_base_metadata(e),
                )
            )

        elif isinstance(e, InventoryMoveEvent):
            flow_events.append(
                FlowEvent(
                    flow_id=f"flow-{e.event_id}",
                    lot_id=f"imv-{e.stable_object_id}",
                    event_type="inventory_adjustment",
                    product_id=e.product_id,
                    from_node=e.from_node,
                    to_node=e.to_node,
                    time_bucket=e.time_bucket,
                    quantity_cpu=e.quantity_cpu,
                    creation_sequence=e.creation_sequence,
                    metadata=_base_metadata(e),
                )
            )

        elif isinstance(e, (PullRequestEvent, BindEvent)):
            # Non-native in kernel v1.0, preserved as sidecar for traceability.
            sidecar_events.append(e)
        else:
            sidecar_events.append(e)

    return MappedKernelEvents(flow_events=flow_events, sidecar_events=sidecar_events)
