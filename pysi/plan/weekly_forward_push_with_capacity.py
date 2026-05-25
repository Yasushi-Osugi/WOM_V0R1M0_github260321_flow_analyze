from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

PSI_S = 0
PSI_CO = 1
PSI_I = 2
PSI_P = 3


@dataclass
class WeeklyForwardPushWithCapacityResult:
    product_name: str
    processed_node_count: int = 0
    processed_week_count: int = 0

    accepted_p_lot_count: int = 0
    blocked_p_lot_count: int = 0
    accepted_s_lot_count: int = 0
    blocked_s_lot_count: int = 0
    overflow_i_lot_count: int = 0

    accepted_p_lot_ids: list[str] = field(default_factory=list)
    blocked_p_lot_ids: list[str] = field(default_factory=list)
    accepted_s_lot_ids: list[str] = field(default_factory=list)
    blocked_s_lot_ids: list[str] = field(default_factory=list)
    overflow_i_lot_ids: list[str] = field(default_factory=list)

    capacity_usage: list[dict] = field(default_factory=list)
    capacity_violations: list[dict] = field(default_factory=list)
    replan_commands: list[dict] = field(default_factory=list)

    non_list_bucket_errors: list[dict] = field(default_factory=list)
    non_string_lot_errors: list[dict] = field(default_factory=list)
    message: str = ""


def _iter_nodes(root: Any) -> Iterator[Any]:
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        children = getattr(node, "children", []) or []
        stack.extend(reversed(children))


def _cap_for_week(cap_values: list | None, week: int) -> int | None:
    if cap_values is None:
        # MVP fallback: missing capacity means unlimited.
        return None
    if week < 0 or week >= len(cap_values):
        return None
    return cap_values[week]


def _record_bucket_errors(result: WeeklyForwardPushWithCapacityResult, node_name: str, week: int, bucket_name: str, bucket: Any) -> bool:
    if not isinstance(bucket, list):
        result.non_list_bucket_errors.append({"node": node_name, "week": week, "bucket": bucket_name})
        return True
    bad_lot_ids = [lot_id for lot_id in bucket if not isinstance(lot_id, str)]
    if bad_lot_ids:
        result.non_string_lot_errors.append(
            {"node": node_name, "week": week, "bucket": bucket_name, "lot_ids": bad_lot_ids}
        )
        return True
    return False


def weekly_forward_push_with_capacity(
    *,
    root,
    product: str,
    weekly_capacity: dict | None = None,
    weeks: int | None = None,
    cap_i_mode: str = "soft",
    debug: bool = False,
) -> WeeklyForwardPushWithCapacityResult:
    if cap_i_mode not in {"soft", "hard"}:
        raise ValueError("cap_i_mode must be 'soft' or 'hard'")

    result = WeeklyForwardPushWithCapacityResult(product_name=product)
    capacity_by_product = (weekly_capacity or {}).get(product, {})

    for node in _iter_nodes(root):
        node_name = getattr(node, "name", "")
        psi4supply = getattr(node, "psi4supply", None)
        if not isinstance(psi4supply, list):
            result.non_list_bucket_errors.append({"node": node_name, "week": None, "bucket": "psi4supply"})
            continue

        node_weeks = len(psi4supply) if weeks is None else min(weeks, len(psi4supply))
        if node_weeks <= 0:
            continue

        result.processed_node_count += 1
        node_caps = capacity_by_product.get(node_name, {})
        prev_ending_inventory: list[str] | None = None

        for w in range(node_weeks):
            week_data = psi4supply[w]
            if not isinstance(week_data, list) or len(week_data) < 4:
                result.non_list_bucket_errors.append({"node": node_name, "week": w, "bucket": "week_data"})
                continue

            s_bucket = week_data[PSI_S]
            i_bucket = week_data[PSI_I]
            p_bucket = week_data[PSI_P]

            has_err = False
            has_err |= _record_bucket_errors(result, node_name, w, "S", s_bucket)
            has_err |= _record_bucket_errors(result, node_name, w, "I", i_bucket)
            has_err |= _record_bucket_errors(result, node_name, w, "P", p_bucket)
            if has_err:
                continue

            requested_p_lots = list(p_bucket)
            requested_s_lots = list(s_bucket)

            cap_p = _cap_for_week(node_caps.get("P"), w)
            cap_s = _cap_for_week(node_caps.get("S"), w)
            cap_i = _cap_for_week(node_caps.get("I"), w)

            p_accept_limit = len(requested_p_lots) if cap_p is None else max(0, min(cap_p, len(requested_p_lots)))
            accepted_p_lots = requested_p_lots[:p_accept_limit]
            blocked_p_lots = requested_p_lots[p_accept_limit:]

            if cap_p is not None:
                result.capacity_usage.append(
                    {"node": node_name, "product": product, "week": w, "capacity_type": "P", "capacity": cap_p, "used": len(accepted_p_lots), "remaining": max(0, cap_p - len(accepted_p_lots))}
                )

            if blocked_p_lots:
                result.capacity_violations.append(
                    {"node": node_name, "product": product, "week": w, "capacity_type": "P", "capacity": cap_p, "requested": len(requested_p_lots), "overflow": len(blocked_p_lots), "lot_ids": list(blocked_p_lots), "severity": "blocked"}
                )
                result.replan_commands.append(
                    {"type": "capacity_replan", "node": node_name, "product": product, "week": w, "capacity_type": "P", "lot_ids": list(blocked_p_lots), "suggested_action": "review_capacity_or_rerun_backward_planning"}
                )

            if w == 0 or prev_ending_inventory is None or (len(prev_ending_inventory) == 0 and len(i_bucket) > 0):
                beginning_inventory_lots = list(i_bucket)
            else:
                beginning_inventory_lots = list(prev_ending_inventory)
            available_lots = list(beginning_inventory_lots) + list(accepted_p_lots)

            cap_s_limit = len(requested_s_lots) if cap_s is None else max(0, cap_s)
            ship_limit = min(len(available_lots), cap_s_limit, len(requested_s_lots))
            accepted_s_lots = requested_s_lots[:ship_limit]
            blocked_s_lots = requested_s_lots[ship_limit:]

            if cap_s is not None:
                result.capacity_usage.append(
                    {"node": node_name, "product": product, "week": w, "capacity_type": "S", "capacity": cap_s, "used": len(accepted_s_lots), "remaining": max(0, cap_s - len(accepted_s_lots))}
                )

            if blocked_s_lots:
                result.capacity_violations.append(
                    {"node": node_name, "product": product, "week": w, "capacity_type": "S", "capacity": cap_s, "requested": len(requested_s_lots), "overflow": len(blocked_s_lots), "lot_ids": list(blocked_s_lots), "severity": "blocked"}
                )
                result.replan_commands.append(
                    {"type": "capacity_replan", "node": node_name, "product": product, "week": w, "capacity_type": "S", "lot_ids": list(blocked_s_lots), "suggested_action": "review_capacity_or_rerun_backward_planning"}
                )

            ending_inventory_lots = list(available_lots[len(accepted_s_lots):])
            overflow_i_lots: list[str] = []

            if cap_i is not None and len(ending_inventory_lots) > cap_i:
                overflow_i_lots = ending_inventory_lots[cap_i:]
                result.capacity_violations.append(
                    {"node": node_name, "product": product, "week": w, "capacity_type": "I", "capacity": cap_i, "requested": len(ending_inventory_lots), "overflow": len(overflow_i_lots), "lot_ids": list(overflow_i_lots), "severity": "warning" if cap_i_mode == "soft" else "blocked"}
                )
                if cap_i_mode == "hard":
                    ending_inventory_lots = ending_inventory_lots[:cap_i]

            if cap_i is not None:
                result.capacity_usage.append(
                    {"node": node_name, "product": product, "week": w, "capacity_type": "I", "capacity": cap_i, "used": len(ending_inventory_lots), "remaining": max(0, cap_i - len(ending_inventory_lots))}
                )

            week_data[PSI_P] = list(accepted_p_lots)
            week_data[PSI_S] = list(accepted_s_lots)
            week_data[PSI_I] = list(ending_inventory_lots)
            prev_ending_inventory = list(ending_inventory_lots)

            result.accepted_p_lot_ids.extend(accepted_p_lots)
            result.blocked_p_lot_ids.extend(blocked_p_lots)
            result.accepted_s_lot_ids.extend(accepted_s_lots)
            result.blocked_s_lot_ids.extend(blocked_s_lots)
            result.overflow_i_lot_ids.extend(overflow_i_lots)
            result.processed_week_count += 1

            if debug:
                print(f"[weekly_push] node={node_name} week={w} P={len(accepted_p_lots)}/{len(requested_p_lots)} S={len(accepted_s_lots)}/{len(requested_s_lots)} I={len(ending_inventory_lots)}")

    result.accepted_p_lot_count = len(result.accepted_p_lot_ids)
    result.blocked_p_lot_count = len(result.blocked_p_lot_ids)
    result.accepted_s_lot_count = len(result.accepted_s_lot_ids)
    result.blocked_s_lot_count = len(result.blocked_s_lot_ids)
    result.overflow_i_lot_count = len(result.overflow_i_lot_ids)
    result.message = "completed"
    return result
