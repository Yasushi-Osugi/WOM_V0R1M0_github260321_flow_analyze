from __future__ import annotations

from pathlib import Path

from pysi.planning.capacity_io import (
    export_capacity_usage_csv,
    export_capacity_violation_csv,
)
from pysi.planning.capacity_master import build_capacity_lookup, get_capacity_record, load_capacity_master_csv
from pysi.planning.forward_push_with_capacity_psi_adapter import (
    PSI_BUCKET_INDEX,
    run_forward_push_with_capacity_psi_lists,
)


class SmokeNode:
    def __init__(self, name: str):
        self.name = name
        self.psi4demand: dict[str, list[list[str]]] = {}
        self.psi4supply: dict[str, list[list[str]]] = {}


def main() -> None:
    records = load_capacity_master_csv("pysi/master_data/capacity_master_sample.csv")
    lookup = build_capacity_lookup(records)

    node = SmokeNode("MOM_CHINA")
    week = "2026-W01"
    node.psi4demand[week] = [[], [], [], [f"PLOT-{i:03d}" for i in range(1, 121)]]
    node.psi4supply[week] = [[], [], [], []]

    result = run_forward_push_with_capacity_psi_lists(
        nodes=[node],
        weeks=[week],
        scenario_id="BASE",
        tree_side="INBOUND",
        product_name="IPHONE_NM_2028_BASE",
        capacity_lookup=lookup,
        capacity_types=["P"],
    )

    usage_csv = Path("outputs/capacity/forward_push_with_capacity_psi_usage.csv")
    violation_csv = Path("outputs/capacity/forward_push_with_capacity_psi_violation.csv")
    export_capacity_usage_csv(result.usage_records, usage_csv)
    export_capacity_violation_csv(result.violation_records, violation_csv)

    key = (node.name, "IPHONE_NM_2028_BASE", week, "P")
    requested = len(node.psi4demand[week][PSI_BUCKET_INDEX["P"]])
    accepted = len(node.psi4supply[week][PSI_BUCKET_INDEX["P"]])
    blocked = len(result.blocked_lots_by_key[key])
    cap_record = get_capacity_record(
        lookup,
        scenario_id="BASE",
        tree_side="INBOUND",
        node_name=node.name,
        product_name="IPHONE_NM_2028_BASE",
        week=week,
        capacity_type="P",
    )

    print("=== with capacity PSI smoke ===")
    print(f"node: {node.name}")
    print(f"week: {week}")
    print("capacity type: P")
    print(f"requested lots: {requested}")
    print(f"capacity: {cap_record.capacity_qty if cap_record is not None else 'None'}")
    print(f"accepted lots in psi4supply: {accepted}")
    print(f"blocked lots: {blocked}")
    print(f"usage csv: {usage_csv}")
    print(f"violation csv: {violation_csv}")


if __name__ == "__main__":
    main()
