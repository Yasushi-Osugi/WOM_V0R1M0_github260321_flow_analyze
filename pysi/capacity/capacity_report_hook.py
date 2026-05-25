from __future__ import annotations

from pathlib import Path

from pysi.capacity.capacity_exporter import (
    export_capacity_usage_csv,
    export_capacity_violation_csv,
)
from pysi.capacity.capacity_master_loader import load_capacity_master_csv
from pysi.capacity.capacity_model import CapacityUsage, CapacityViolation
from pysi.capacity.capacity_planning import with_capacity_forward_planning


def run_capacity_report_hook(
    *,
    enabled: bool,
    scenario_id: str,
    product_name: str,
    weeks: list[int | str],
    outbound_root=None,
    inbound_root=None,
    capacity_master_path: str | Path | None = None,
    output_dir: str | Path = "outputs/capacity",
    strict_capacity_master: bool = False,
) -> tuple[list[CapacityUsage], list[CapacityViolation]]:
    if not enabled:
        return [], []

    if capacity_master_path is None:
        if strict_capacity_master:
            raise FileNotFoundError("capacity_master_path is required when strict_capacity_master=True")
        return [], []

    master_path = Path(capacity_master_path)
    if not master_path.exists():
        if strict_capacity_master:
            raise FileNotFoundError(f"capacity master csv not found: {master_path}")
        return [], []

    capacity_buckets = load_capacity_master_csv(master_path)

    usage_records: list[CapacityUsage] = []
    violation_records: list[CapacityViolation] = []

    if outbound_root is not None:
        out_usage, out_violation = with_capacity_forward_planning(
            root_node=outbound_root,
            weeks=weeks,
            scenario_id=scenario_id,
            product_name=product_name,
            capacity_buckets=capacity_buckets,
            tree_side="OUTBOUND",
        )
        usage_records.extend(out_usage)
        violation_records.extend(out_violation)

    if inbound_root is not None:
        in_usage, in_violation = with_capacity_forward_planning(
            root_node=inbound_root,
            weeks=weeks,
            scenario_id=scenario_id,
            product_name=product_name,
            capacity_buckets=capacity_buckets,
            tree_side="INBOUND",
        )
        usage_records.extend(in_usage)
        violation_records.extend(in_violation)

    if usage_records or violation_records:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        export_capacity_usage_csv(out_dir / "capacity_usage.csv", usage_records)
        export_capacity_violation_csv(out_dir / "capacity_violation.csv", violation_records)

    return usage_records, violation_records
