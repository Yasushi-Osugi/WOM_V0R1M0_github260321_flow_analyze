from __future__ import annotations

from pysi.bridge.event_extractor import ExtractContext, extract_events
from pysi.bridge.state_snapshot import (
    LotDemandBinding,
    LotPosition,
    PlanningStateSnapshot,
)


def make_snapshot(
    *,
    tb: str,
    lots=None,
    inventory=None,
    backlog=None,
    edge_flows=None,
    bindings=None,
    allocations=None,
) -> PlanningStateSnapshot:
    # NOTE:
    # PlanningStateSnapshot is frozen, but its internal dict containers are mutable.
    # Bridge v0.1 operational policy: construct maps up front and treat as immutable.
    return PlanningStateSnapshot(
        time_bucket=tb,
        lots=dict(lots or {}),
        inventory=dict(inventory or {}),
        backlog=dict(backlog or {}),
        edge_flows=dict(edge_flows or {}),
        lot_demand_bindings=dict(bindings or {}),
        allocation_pairs=dict(allocations or {}),
    )


def test_shipment_simplified_rule_at_node_to_in_transit():
    prev = make_snapshot(
        tb="202601",
        lots={
            "lot-1": LotPosition(
                lot_id="lot-1",
                product_id="P1",
                quantity_cpu=10.0,
                time_bucket="202601",
                status="at_node",
                current_node="A",
            )
        },
        inventory={("A", "P1"): 10.0},
    )
    cur = make_snapshot(
        tb="202601",
        lots={
            "lot-1": LotPosition(
                lot_id="lot-1",
                product_id="P1",
                quantity_cpu=10.0,
                time_bucket="202601",
                status="in_transit",
                from_node="A",
                to_node="B",
                current_edge=("A", "B"),
            )
        },
        inventory={("A", "P1"): 0.0},
    )

    events = extract_events(prev, cur, ExtractContext(time_bucket="202601", seq_start=1))
    ships = [e for e in events if e.event_type == "shipment"]
    assert len(ships) == 1
    assert ships[0].lot_id == "lot-1"


def test_arrival_simplified_rule_in_transit_to_at_node():
    prev = make_snapshot(
        tb="202602",
        lots={
            "lot-1": LotPosition(
                lot_id="lot-1",
                product_id="P1",
                quantity_cpu=10.0,
                time_bucket="202602",
                status="in_transit",
                from_node="A",
                to_node="B",
                current_edge=("A", "B"),
            )
        },
        inventory={("B", "P1"): 0.0},
    )
    cur = make_snapshot(
        tb="202602",
        lots={
            "lot-1": LotPosition(
                lot_id="lot-1",
                product_id="P1",
                quantity_cpu=10.0,
                time_bucket="202602",
                status="at_node",
                current_node="B",
                from_node="A",
                to_node="B",
            )
        },
        inventory={("B", "P1"): 10.0},
    )

    events = extract_events(prev, cur, ExtractContext(time_bucket="202602", seq_start=1))
    arrs = [e for e in events if e.event_type == "arrival"]
    assert len(arrs) == 1
    assert arrs[0].lot_id == "lot-1"


def test_bind_priority_prefers_binding_snapshot_diff():
    prev = make_snapshot(tb="202601")
    cur = make_snapshot(
        tb="202601",
        lots={
            "lot-9": LotPosition(
                lot_id="lot-9",
                product_id="P1",
                quantity_cpu=5.0,
                time_bucket="202601",
                status="at_node",
                current_node="MKT",
            )
        },
        bindings={
            ("lot-9", "d-1"): LotDemandBinding(
                lot_id="lot-9",
                demand_id="d-1",
                product_id="P1",
                node_id="MKT",
                quantity_cpu=5.0,
                time_bucket="202601",
            )
        },
        allocations={("lot-9", "d-1"): 5.0},
    )

    events = extract_events(prev, cur, ExtractContext(time_bucket="202601", seq_start=1))
    binds = [e for e in events if e.event_type == "bind"]
    assert len(binds) == 1
    assert binds[0].source_ref == "binding_snapshot_diff"


def test_bind_fallback_uses_allocation_pseudo_bind_when_no_binding_snapshot():
    prev = make_snapshot(tb="202601")
    cur = make_snapshot(
        tb="202601",
        lots={
            "lot-8": LotPosition(
                lot_id="lot-8",
                product_id="P1",
                quantity_cpu=7.0,
                time_bucket="202601",
                status="at_node",
                current_node="MKT",
            )
        },
        bindings={},
        allocations={("lot-8", "d-2"): 7.0},
    )

    events = extract_events(prev, cur, ExtractContext(time_bucket="202601", seq_start=1))
    binds = [e for e in events if e.event_type == "bind"]
    assert len(binds) == 1
    assert binds[0].source_ref == "allocation_pseudo_bind"
    assert binds[0].lot_id == "lot-8"
    assert binds[0].demand_id == "d-2"


def test_inventory_move_residual_quantity_and_sign_policy():
    prev = make_snapshot(tb="202601", inventory={("N1", "P1"): 10.0})
    cur = make_snapshot(tb="202601", inventory={("N1", "P1"): 13.0})

    events = extract_events(prev, cur, ExtractContext(time_bucket="202601", seq_start=1))
    imv = [e for e in events if e.event_type == "inventory_move"]
    assert len(imv) == 1
    e = imv[0]
    assert e.quantity_cpu == abs(e.metadata["residual_qty"])
    assert e.metadata["observed_inventory_delta"] == 3.0
    assert e.metadata["explained_delta"] == 0.0
    assert e.metadata["residual_qty"] == 3.0


def test_deterministic_order_stable_object_id():
    prev = make_snapshot(tb="202601", backlog={("N2", "P1"): 1.0, ("N1", "P1"): 1.0})
    cur = make_snapshot(tb="202601", backlog={("N2", "P1"): 3.0, ("N1", "P1"): 2.0})

    e1 = extract_events(prev, cur, ExtractContext(time_bucket="202601", seq_start=1))
    e2 = extract_events(prev, cur, ExtractContext(time_bucket="202601", seq_start=1))

    assert [(x.event_type, x.stable_object_id, x.creation_sequence) for x in e1] == [
        (x.event_type, x.stable_object_id, x.creation_sequence) for x in e2
    ]
