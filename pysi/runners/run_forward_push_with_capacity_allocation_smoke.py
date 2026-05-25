from __future__ import annotations

from pysi.planning.bottleneck_allocation import AllocationRule
from pysi.planning.capacity_master import CapacityMasterRecord, build_capacity_lookup
from pysi.planning.forward_push_with_capacity_psi_adapter import run_forward_push_with_capacity_psi_lists


class DummyNode:
    def __init__(self, name: str):
        self.name = name
        self.psi4demand = {}
        self.psi4supply = {}


if __name__ == "__main__":
    week = "2026-W01"
    node = DummyNode("MOM_CHINA")
    lots = []
    for i in range(20):
        lots.append({"lot_id": f"LOW_{i:03d}", "priority": 90})
    for i in range(100):
        lots.append({"lot_id": f"HIGH_{i:03d}", "priority": 1})

    node.psi4demand[week] = [[], [], [], lots]
    node.psi4supply[week] = [[], [], [], []]

    lookup = build_capacity_lookup([
        CapacityMasterRecord("BASE", "INBOUND", "MOM_CHINA", "IPHONE_NM_2028_BASE", week, "P", 100),
    ])

    result = run_forward_push_with_capacity_psi_lists(
        nodes=[node],
        weeks=[week],
        scenario_id="BASE",
        tree_side="INBOUND",
        product_name="IPHONE_NM_2028_BASE",
        capacity_lookup=lookup,
        capacity_types=["P"],
        allocation_rule=AllocationRule("LOT_PRIORITY"),
    )
    key = ("MOM_CHINA", "IPHONE_NM_2028_BASE", week, "P")
    accepted = result.accepted_lots_by_key[key]
    blocked = result.blocked_lots_by_key[key]

    highest_priority_first = all(lot["priority"] == 1 for lot in accepted)
    print("=== with capacity allocation smoke ===")
    print("rule: LOT_PRIORITY")
    print(f"requested lots: {len(lots)}")
    print("capacity: 100")
    print(f"accepted lots: {len(accepted)}")
    print(f"blocked lots: {len(blocked)}")
    print(f"highest priority lots accepted first: {str(highest_priority_first).lower()}")
