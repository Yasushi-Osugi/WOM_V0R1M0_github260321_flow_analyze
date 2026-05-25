from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pysi.planning.capacity_master import CapacityMasterRecord, get_capacity_record
from pysi.planning.forward_push_with_capacity_planner import (
    ForwardPushWithCapacityPlanner,
    ForwardPushWithCapacityResult,
)


@dataclass
class CapacityUsage:
    scenario_id: str
    tree_side: str
    node_name: str
    product_name: str
    week: str
    capacity_type: str
    capacity_qty: int
    used_qty: int
    used_lot_ids: list[str] = field(default_factory=list)

    @property
    def remaining_qty(self) -> int:
        return max(self.capacity_qty - self.used_qty, 0)

    @property
    def utilization(self) -> float:
        if self.capacity_qty <= 0:
            return 0.0
        return self.used_qty / self.capacity_qty


@dataclass
class CapacityViolation:
    scenario_id: str
    tree_side: str
    node_name: str
    product_name: str
    week: str
    capacity_type: str
    cap_mode: str
    capacity_qty: int
    required_qty: int
    overflow_qty: int
    violation_type: str
    overflow_lot_ids: list[str] = field(default_factory=list)
    action: str = "CARRY_OVER"


def _lot_id(lot: Any) -> str:
    if isinstance(lot, dict):
        return str(lot.get("lot_id", lot))
    return str(lot)


def export_capacity_usage_csv(usages: list[CapacityUsage], path: str | Path) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(
            [
                "scenario_id","tree_side","node_name","product_name","week","capacity_type",
                "capacity_qty","used_qty","remaining_qty","utilization","used_lot_ids",
            ]
        )
        for u in usages:
            writer.writerow([
                u.scenario_id, u.tree_side, u.node_name, u.product_name, u.week, u.capacity_type,
                u.capacity_qty, u.used_qty, u.remaining_qty, u.utilization, "|".join(u.used_lot_ids),
            ])


def export_capacity_violation_csv(violations: list[CapacityViolation], path: str | Path) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow([
            "scenario_id","tree_side","node_name","product_name","week","capacity_type","cap_mode",
            "capacity_qty","required_qty","overflow_qty","violation_type","overflow_lot_ids","action",
        ])
        for v in violations:
            writer.writerow([
                v.scenario_id, v.tree_side, v.node_name, v.product_name, v.week, v.capacity_type, v.cap_mode,
                v.capacity_qty, v.required_qty, v.overflow_qty, v.violation_type,
                "|".join(v.overflow_lot_ids), v.action,
            ])


def run_forward_push_with_capacity_from_master(
    *,
    scenario_id: str,
    tree_side: str,
    node_name: str,
    product_name: str,
    week: str,
    capacity_type: str,
    requested_lots: list[Any],
    capacity_lookup: dict[tuple[str, str, str, str, str, str], CapacityMasterRecord],
) -> tuple[ForwardPushWithCapacityResult, CapacityUsage | None, CapacityViolation | None]:
    record = get_capacity_record(
        capacity_lookup,
        scenario_id=scenario_id,
        tree_side=tree_side,
        node_name=node_name,
        product_name=product_name,
        week=week,
        capacity_type=capacity_type,
    )

    planner = ForwardPushWithCapacityPlanner()
    capacity_qty = None if record is None else record.capacity_qty
    result = planner.consume_lots_with_capacity(
        node_id=node_name,
        product_id=product_name,
        week=week,
        requested_lots=requested_lots,
        capacity_qty=capacity_qty,
    )

    if record is None:
        return result, None, None

    usage = CapacityUsage(
        scenario_id=scenario_id,
        tree_side=tree_side,
        node_name=node_name,
        product_name=product_name,
        week=week,
        capacity_type=capacity_type,
        capacity_qty=record.capacity_qty,
        used_qty=len(result.pushed_lots),
        used_lot_ids=[_lot_id(lot) for lot in result.pushed_lots],
    )

    violation = None
    if result.blocked_lots:
        violation = CapacityViolation(
            scenario_id=scenario_id,
            tree_side=tree_side,
            node_name=node_name,
            product_name=product_name,
            week=week,
            capacity_type=capacity_type,
            cap_mode=record.cap_mode,
            capacity_qty=record.capacity_qty,
            required_qty=len(requested_lots),
            overflow_qty=len(result.blocked_lots),
            violation_type="CAPACITY_OVERFLOW",
            overflow_lot_ids=[_lot_id(lot) for lot in result.blocked_lots],
            action="BLOCK" if record.cap_mode == "hard" else "CARRY_OVER",
        )

    return result, usage, violation