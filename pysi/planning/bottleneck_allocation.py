from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AllocationRule:
    rule_name: str = "FIFO"
    default_priority: int = 100
    descending: bool = False


@dataclass
class BottleneckAllocationResult:
    node_name: str
    product_name: str
    week: str | int
    capacity_type: str
    rule_name: str
    requested_qty: int
    capacity_qty: int | None
    is_bottleneck: bool
    ordered_lots: list[Any] = field(default_factory=list)
    accepted_lots: list[Any] = field(default_factory=list)
    blocked_lots: list[Any] = field(default_factory=list)


def _lot_id(lot: Any) -> str:
    if isinstance(lot, dict):
        return str(lot.get("lot_id", lot))
    return str(lot)


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_lot_priority(lot: Any, default_priority: int = 100) -> int:
    if not isinstance(lot, dict):
        return default_priority
    if "allocation_priority" in lot:
        return _safe_int(lot.get("allocation_priority"), default_priority)
    if "priority" in lot:
        return _safe_int(lot.get("priority"), default_priority)
    return default_priority


def _due_week_key(lot: Any) -> tuple[int, Any]:
    if isinstance(lot, dict) and lot.get("due_week") is not None:
        return (0, lot.get("due_week"))
    return (1, "")


def order_lots_for_allocation(
    lots: list[Any],
    rule: AllocationRule | None = None,
) -> list[Any]:
    active_rule = rule or AllocationRule()
    if active_rule.rule_name == "LOT_PRIORITY":
        return sorted(
            lots,
            key=lambda lot: get_lot_priority(lot, active_rule.default_priority),
            reverse=active_rule.descending,
        )
    if active_rule.rule_name == "DUE_WEEK_PRIORITY":
        return sorted(lots, key=_due_week_key, reverse=active_rule.descending)
    return list(lots)


def allocate_lots_at_bottleneck(
    *,
    node_name: str,
    product_name: str,
    week: str | int,
    capacity_type: str,
    requested_lots: list[Any],
    capacity_qty: int | None,
    rule: AllocationRule | None = None,
) -> BottleneckAllocationResult:
    active_rule = rule or AllocationRule()
    requested_qty = len(requested_lots)

    if capacity_qty is None:
        return BottleneckAllocationResult(
            node_name=node_name,
            product_name=product_name,
            week=week,
            capacity_type=capacity_type,
            rule_name=active_rule.rule_name,
            requested_qty=requested_qty,
            capacity_qty=None,
            is_bottleneck=False,
            ordered_lots=list(requested_lots),
            accepted_lots=list(requested_lots),
            blocked_lots=[],
        )

    bounded_capacity = max(int(capacity_qty), 0)
    is_bottleneck = requested_qty > bounded_capacity
    if not is_bottleneck:
        ordered = list(requested_lots)
    else:
        ordered = order_lots_for_allocation(list(requested_lots), active_rule)

    accepted_lots = ordered[:bounded_capacity]
    blocked_lots = ordered[bounded_capacity:]

    return BottleneckAllocationResult(
        node_name=node_name,
        product_name=product_name,
        week=week,
        capacity_type=capacity_type,
        rule_name=active_rule.rule_name,
        requested_qty=requested_qty,
        capacity_qty=bounded_capacity,
        is_bottleneck=is_bottleneck,
        ordered_lots=ordered,
        accepted_lots=accepted_lots,
        blocked_lots=blocked_lots,
    )
