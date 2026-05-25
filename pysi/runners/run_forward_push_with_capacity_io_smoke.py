from __future__ import annotations

from pathlib import Path

from pysi.planning.capacity_io import (
    export_capacity_usage_csv,
    export_capacity_violation_csv,
    run_forward_push_with_capacity_from_master,
)
from pysi.planning.capacity_master import build_capacity_lookup, load_capacity_master_csv


def main() -> None:
    master_path = Path("pysi/master_data/capacity_master_sample.csv")
    records = load_capacity_master_csv(master_path)
    lookup = build_capacity_lookup(records)

    requested_lots = [{"lot_id": f"LOT{i:03d}"} for i in range(1, 121)]

    result, usage, violation = run_forward_push_with_capacity_from_master(
        scenario_id="BASE",
        tree_side="INBOUND",
        node_name="MOM_CHINA",
        product_name="IPHONE_NM_2028_BASE",
        week="2026-W01",
        capacity_type="P",
        requested_lots=requested_lots,
        capacity_lookup=lookup,
    )

    usage_path = Path("outputs/capacity/forward_push_with_capacity_usage.csv")
    violation_path = Path("outputs/capacity/forward_push_with_capacity_violation.csv")
    export_capacity_usage_csv([usage] if usage else [], usage_path)
    export_capacity_violation_csv([violation] if violation else [], violation_path)

    print("=== with capacity IO smoke ===")
    print(f"capacity master records: {len(records)}")
    print(f"requested lots: {len(requested_lots)}")
    print(f"capacity: {usage.capacity_qty if usage else 'unlimited'}")
    print(f"accepted lots: {len(result.pushed_lots)}")
    print(f"blocked lots: {len(result.blocked_lots)}")
    print(f"usage csv: {usage_path}")
    print(f"violation csv: {violation_path}")


if __name__ == "__main__":
    main()