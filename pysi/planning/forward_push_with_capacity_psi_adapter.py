from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pysi.planning.bottleneck_allocation import AllocationRule, allocate_lots_at_bottleneck
from pysi.planning.capacity_master import get_capacity_record
from pysi.planning.capacity_io import (
    CapacityUsage,
    CapacityViolation,
    run_forward_push_with_capacity_from_master,
)

PSI_BUCKET_INDEX = {
    "S": 0,
    "CO": 1,
    "I": 2,
    "P": 3,
}


@dataclass
class ForwardPushWithCapacityPsiResult:
    usage_records: list[CapacityUsage] = field(default_factory=list)
    violation_records: list[CapacityViolation] = field(default_factory=list)
    accepted_lots_by_key: dict = field(default_factory=dict)
    blocked_lots_by_key: dict = field(default_factory=dict)
    carryover_lots_by_key: dict = field(default_factory=dict)


def _ensure_week_slots(node: Any, psi_attr: str, week: str | int) -> list[list[Any]]:
    matrix = getattr(node, psi_attr)
    if week not in matrix:
        matrix[week] = [[], [], [], []]
    slots = matrix[week]
    while len(slots) < 4:
        slots.append([])
    return slots


def get_psi_lots(node: Any, psi_attr: str, week: str | int, bucket: str) -> list:
    if bucket not in PSI_BUCKET_INDEX:
        raise ValueError(f"unknown PSI bucket: {bucket}")
    slots = _ensure_week_slots(node, psi_attr, week)
    return slots[PSI_BUCKET_INDEX[bucket]]


def append_psi_lots(node: Any, psi_attr: str, week: str | int, bucket: str, lots: list) -> None:
    target = get_psi_lots(node, psi_attr, week, bucket)
    target.extend(lots)


def apply_capacity_to_node_psi_bucket(
    *,
    node,
    scenario_id: str,
    tree_side: str,
    product_name: str,
    week: str | int,
    capacity_type: str,
    capacity_lookup: dict,
    allocation_rule: AllocationRule | None = None,
) -> tuple[list, list, CapacityUsage | None, CapacityViolation | None]:
    requested_lots = list(get_psi_lots(node, "psi4demand", week, capacity_type))

    record = get_capacity_record(
        capacity_lookup,
        scenario_id=scenario_id,
        tree_side=tree_side,
        node_name=node.name,
        product_name=product_name,
        week=str(week),
        capacity_type=capacity_type,
    )
    allocation_result = allocate_lots_at_bottleneck(
        node_name=node.name,
        product_name=product_name,
        week=week,
        capacity_type=capacity_type,
        requested_lots=requested_lots,
        capacity_qty=None if record is None else record.capacity_qty,
        rule=allocation_rule,
    )

    plan_result, usage, violation = run_forward_push_with_capacity_from_master(
        scenario_id=scenario_id,
        tree_side=tree_side,
        node_name=node.name,
        product_name=product_name,
        week=str(week),
        capacity_type=capacity_type,
        requested_lots=allocation_result.ordered_lots,
        capacity_lookup=capacity_lookup,
    )
    append_psi_lots(node, "psi4supply", week, capacity_type, plan_result.pushed_lots)
    return plan_result.pushed_lots, plan_result.blocked_lots, usage, violation


def run_forward_push_with_capacity_psi_lists(
    *,
    nodes: list,
    weeks: list[str | int],
    scenario_id: str,
    tree_side: str,
    product_name: str,
    capacity_lookup: dict,
    capacity_types: list[str] | None = None,
    allocation_rule: AllocationRule | None = None,
) -> ForwardPushWithCapacityPsiResult:
    cap_types = capacity_types or ["P", "S"]
    result = ForwardPushWithCapacityPsiResult()

    for week in weeks:
        for node in nodes:
            for capacity_type in cap_types:
                accepted_lots, blocked_lots, usage, violation = apply_capacity_to_node_psi_bucket(
                    node=node,
                    scenario_id=scenario_id,
                    tree_side=tree_side,
                    product_name=product_name,
                    week=week,
                    capacity_type=capacity_type,
                    capacity_lookup=capacity_lookup,
                    allocation_rule=allocation_rule,
                )
                key = (node.name, product_name, week, capacity_type)
                result.accepted_lots_by_key[key] = list(accepted_lots)
                result.blocked_lots_by_key[key] = list(blocked_lots)
                result.carryover_lots_by_key[key] = list(blocked_lots)
                if usage is not None:
                    result.usage_records.append(usage)
                if violation is not None:
                    result.violation_records.append(violation)

    return result
