from __future__ import annotations

import csv
from pathlib import Path

from pysi.capacity.capacity_model import CapacityUsage, CapacityViolation


def export_capacity_usage_csv(path: str | Path, records: list[CapacityUsage]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "scenario_id", "tree_side", "node_name", "product_name", "week", "capacity_type",
            "capacity_qty", "used_qty", "remaining_qty", "utilization", "used_lot_ids"
        ])
        for r in records:
            w.writerow([
                r.scenario_id, r.tree_side, r.node_name, r.product_name, r.week, r.capacity_type,
                r.capacity_qty, r.used_qty, r.remaining_qty, r.utilization, "|".join(r.used_lot_ids)
            ])


def export_capacity_violation_csv(path: str | Path, records: list[CapacityViolation]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "scenario_id", "tree_side", "node_name", "product_name", "week", "capacity_type", "cap_mode",
            "capacity_qty", "required_qty", "overflow_qty", "violation_type", "overflow_lot_ids", "action"
        ])
        for r in records:
            w.writerow([
                r.scenario_id, r.tree_side, r.node_name, r.product_name, r.week, r.capacity_type, r.cap_mode,
                r.capacity_qty, r.required_qty, r.overflow_qty, r.violation_type, "|".join(r.overflow_lot_ids), r.action
            ])
