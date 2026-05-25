from __future__ import annotations

from pysi.planning.bottleneck_allocation import (
    AllocationRule,
    allocate_lots_at_bottleneck,
    order_lots_for_allocation,
)
from pysi.planning.capacity_master import CapacityMasterRecord, build_capacity_lookup
from pysi.planning.forward_push_with_capacity_psi_adapter import run_forward_push_with_capacity_psi_lists


class DummyNode:
    def __init__(self, name: str):
        self.name = name
        self.psi4demand = {}
        self.psi4supply = {}


def test_fifo_keeps_input_order():
    lots = ["L3", "L1", "L2"]
    assert order_lots_for_allocation(lots, AllocationRule("FIFO")) == lots


def test_lot_priority_sorts_ascending_and_stable():
    lots = [
        {"lot_id": "A", "priority": 10},
        {"lot_id": "B", "priority": 1},
        {"lot_id": "C", "priority": 10},
    ]
    ordered = order_lots_for_allocation(lots, AllocationRule("LOT_PRIORITY"))
    assert [x["lot_id"] for x in ordered] == ["B", "A", "C"]


def test_default_priority_for_string_or_missing_priority():
    lots = [
        {"lot_id": "A", "priority": 2},
        "S1",
        {"lot_id": "MISSING"},
    ]
    ordered = order_lots_for_allocation(lots, AllocationRule("LOT_PRIORITY", default_priority=100))
    assert ordered[0]["lot_id"] == "A"


def test_allocate_capacity_none_unlimited():
    lots = ["L1", "L2"]
    res = allocate_lots_at_bottleneck(
        node_name="N1", product_name="P1", week="2026-W01", capacity_type="P", requested_lots=lots, capacity_qty=None
    )
    assert not res.is_bottleneck
    assert res.accepted_lots == lots
    assert res.blocked_lots == []


def test_capacity_sufficient_keeps_order_no_reorder():
    lots = ["Z", "A", "B"]
    res = allocate_lots_at_bottleneck(
        node_name="N1", product_name="P1", week="2026-W01", capacity_type="P", requested_lots=lots, capacity_qty=5,
        rule=AllocationRule("LOT_PRIORITY"),
    )
    assert not res.is_bottleneck
    assert res.accepted_lots == lots


def test_capacity_shortage_applies_rule_and_splits():
    lots = [
        {"lot_id": "LOW", "priority": 9},
        {"lot_id": "HIGH", "priority": 1},
        {"lot_id": "MID", "priority": 5},
    ]
    res = allocate_lots_at_bottleneck(
        node_name="N1", product_name="P1", week="2026-W01", capacity_type="P", requested_lots=lots, capacity_qty=2,
        rule=AllocationRule("LOT_PRIORITY"),
    )
    assert res.is_bottleneck
    assert [x["lot_id"] for x in res.accepted_lots] == ["HIGH", "MID"]
    assert [x["lot_id"] for x in res.blocked_lots] == ["LOW"]


def test_zero_capacity_blocks_all():
    res = allocate_lots_at_bottleneck(
        node_name="N1", product_name="P1", week="2026-W01", capacity_type="P", requested_lots=["A", "B"], capacity_qty=0
    )
    assert res.is_bottleneck
    assert res.accepted_lots == []
    assert res.blocked_lots == ["A", "B"]


def test_psi_adapter_lot_priority_and_demand_unchanged():
    node = DummyNode("MOM_CHINA")
    week = "2026-W01"
    lots = [
        {"lot_id": "LOW", "priority": 90},
        {"lot_id": "HIGH", "priority": 1},
        {"lot_id": "MID", "priority": 50},
    ]
    node.psi4demand[week] = [[], [], [], lots.copy()]
    node.psi4supply[week] = [[], [], [], []]
    lookup = build_capacity_lookup([
        CapacityMasterRecord("BASE", "INBOUND", "MOM_CHINA", "PROD", week, "P", 2),
    ])

    result = run_forward_push_with_capacity_psi_lists(
        nodes=[node],
        weeks=[week],
        scenario_id="BASE",
        tree_side="INBOUND",
        product_name="PROD",
        capacity_lookup=lookup,
        capacity_types=["P"],
        allocation_rule=AllocationRule("LOT_PRIORITY"),
    )

    assert [x["lot_id"] for x in node.psi4supply[week][3]] == ["HIGH", "MID"]
    key = ("MOM_CHINA", "PROD", week, "P")
    assert [x["lot_id"] for x in result.blocked_lots_by_key[key]] == ["LOW"]
    assert node.psi4demand[week][3] == lots
