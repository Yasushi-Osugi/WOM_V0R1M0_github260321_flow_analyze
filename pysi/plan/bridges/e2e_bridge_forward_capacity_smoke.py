from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pysi.plan.bridges.demand_to_supply_execution_bridge import bridge_demand_to_supply_execution
from pysi.plan.bridges.outbound_to_inbound_demand_bridge import PSI_BUCKET_INDEX, bridge_outbound_to_inbound_demand, iter_nodes
from pysi.plan.bridges.outbound_to_inbound_mom_allocation import allocate_bridged_demand_to_moms
from pysi.plan.capacity_aware_inbound_backward import capacity_aware_inbound_backward_planning
from pysi.plan.weekly_forward_push_with_capacity import weekly_forward_push_with_capacity


@dataclass
class E2EBridgeForwardCapacitySmokeResult:
    bridge_a_lot_count: int = 0
    mom_allocated_lot_count: int = 0
    capacity_planned_lot_count: int = 0
    bridge_b_lot_count: int = 0

    forward_accepted_p_count: int = 0
    forward_blocked_p_count: int = 0
    forward_accepted_s_count: int = 0
    forward_blocked_s_count: int = 0
    forward_overflow_i_count: int = 0

    missing_lot_ids: list[str] = field(default_factory=list)
    blocked_lot_ids: list[str] = field(default_factory=list)
    overflow_i_lot_ids: list[str] = field(default_factory=list)

    non_list_bucket_errors: list[dict] = field(default_factory=list)
    non_string_lot_errors: list[dict] = field(default_factory=list)
    message: str = ""


def _collect_lots_by_layer(root: Any, layer: str) -> set[str]:
    lots: set[str] = set()
    for node in iter_nodes(root):
        psi = getattr(node, layer, None)
        if not isinstance(psi, list):
            continue
        for week in psi:
            if not isinstance(week, list):
                continue
            for bucket in week:
                if not isinstance(bucket, list):
                    continue
                for lot in bucket:
                    if isinstance(lot, str):
                        lots.add(lot)
    return lots


def _validate_psi_invariants(root: Any, layer: str) -> tuple[list[dict], list[dict]]:
    non_list_bucket_errors: list[dict] = []
    non_string_lot_errors: list[dict] = []
    for node in iter_nodes(root):
        psi = getattr(node, layer, None)
        if not isinstance(psi, list):
            non_list_bucket_errors.append({"node": getattr(node, "name", ""), "layer": layer, "reason": "psi_not_list"})
            continue
        for w, week in enumerate(psi):
            if not isinstance(week, list) or len(week) < 4:
                non_list_bucket_errors.append({"node": getattr(node, "name", ""), "layer": layer, "week": w, "reason": "week_not_list_or_short"})
                continue
            for b_idx, bucket in enumerate(week[:4]):
                if not isinstance(bucket, list):
                    non_list_bucket_errors.append({"node": getattr(node, "name", ""), "layer": layer, "week": w, "bucket": b_idx, "reason": "bucket_not_list"})
                    continue
                for lot in bucket:
                    if not isinstance(lot, str):
                        non_string_lot_errors.append({"node": getattr(node, "name", ""), "layer": layer, "week": w, "bucket": b_idx, "lot": lot})
    return non_list_bucket_errors, non_string_lot_errors


def run_e2e_bridge_forward_capacity_smoke(
    *,
    outbound_root,
    inbound_root,
    product: str,
    mom_policy: dict,
    backward_weekly_capability: dict,
    forward_weekly_capacity: dict,
    bridge_a_mode: str = "replace",
    bridge_b_policy: str = "s_p_only",
    bridge_b_mode: str = "replace",
    max_early_build_weeks: int = 13,
    cap_i_mode: str = "soft",
    debug: bool = False,
) -> E2EBridgeForwardCapacitySmokeResult:
    result = E2EBridgeForwardCapacitySmokeResult()

    source_node = next((n for n in iter_nodes(outbound_root) if getattr(n, "name", None) == "supply_point"), None)
    source_lots = set()
    if source_node is not None and isinstance(getattr(source_node, "psi4demand", None), list):
        for week in source_node.psi4demand:
            if isinstance(week, list) and len(week) > PSI_BUCKET_INDEX["P"] and isinstance(week[PSI_BUCKET_INDEX["P"]], list):
                source_lots.update(lot for lot in week[PSI_BUCKET_INDEX["P"]] if isinstance(lot, str))

    bridge_a_result = bridge_outbound_to_inbound_demand(
        outbound_root=outbound_root,
        inbound_root=inbound_root,
        source_node_name="supply_point",
        target_node_name="supply_point",
        source_bucket="P",
        target_bucket="S",
        layer="demand",
        mode=bridge_a_mode,
    )
    result.bridge_a_lot_count = bridge_a_result.copied_lot_count

    _, inbound_root = allocate_bridged_demand_to_moms(
        out_root=outbound_root,
        inbound_root=inbound_root,
        policy=mom_policy,
        source_node_name="supply_point",
        source_bucket="S",
        clear_existing_mom_demand=True,
        debug=debug,
    )

    result.mom_allocated_lot_count = sum(
        len(week[PSI_BUCKET_INDEX["S"]])
        for node in iter_nodes(inbound_root)
        if str(getattr(node, "name", "")).startswith("MOM")
        for week in (getattr(node, "psi4demand", []) or [])
        if isinstance(week, list) and len(week) > PSI_BUCKET_INDEX["S"] and isinstance(week[PSI_BUCKET_INDEX["S"]], list)
    )

    backward_result = capacity_aware_inbound_backward_planning(
        in_root=inbound_root,
        product=product,
        weekly_capability=backward_weekly_capability,
        max_early_build_weeks=max_early_build_weeks,
        debug=debug,
    )
    result.capacity_planned_lot_count = backward_result.accepted_lot_count

    bridge_b_result = bridge_demand_to_supply_execution(
        root=inbound_root,
        bridge_policy=bridge_b_policy,
        mode=bridge_b_mode,
    )
    result.bridge_b_lot_count = bridge_b_result.copied_lot_count

    forward_result = weekly_forward_push_with_capacity(
        root=inbound_root,
        product=product,
        weekly_capacity=forward_weekly_capacity,
        cap_i_mode=cap_i_mode,
        debug=debug,
    )

    result.forward_accepted_p_count = forward_result.accepted_p_lot_count
    result.forward_blocked_p_count = forward_result.blocked_p_lot_count
    result.forward_accepted_s_count = forward_result.accepted_s_lot_count
    result.forward_blocked_s_count = forward_result.blocked_s_lot_count
    result.forward_overflow_i_count = forward_result.overflow_i_lot_count

    result.blocked_lot_ids = sorted(
        set(forward_result.blocked_p_lot_ids) | set(forward_result.blocked_s_lot_ids)
    )
    result.overflow_i_lot_ids = sorted(set(forward_result.overflow_i_lot_ids))

    demand_lots = _collect_lots_by_layer(inbound_root, "psi4demand")
    supply_lots = _collect_lots_by_layer(inbound_root, "psi4supply")
    backlog_lots = {entry.get("lot_id") for entry in backward_result.backlog_lots if isinstance(entry.get("lot_id"), str)}
    final_lots = demand_lots | supply_lots | set(result.blocked_lot_ids) | set(result.overflow_i_lot_ids) | backlog_lots
    result.missing_lot_ids = sorted(source_lots - final_lots)

    d_non_list, d_non_string = _validate_psi_invariants(inbound_root, "psi4demand")
    s_non_list, s_non_string = _validate_psi_invariants(inbound_root, "psi4supply")
    result.non_list_bucket_errors = (
        d_non_list
        + s_non_list
        + backward_result.non_list_bucket_errors
        + bridge_b_result.non_list_bucket_errors
        + forward_result.non_list_bucket_errors
    )
    result.non_string_lot_errors = d_non_string + s_non_string + backward_result.non_string_lot_errors + forward_result.non_string_lot_errors

    result.message = "Completed Bridge A -> MOM allocation -> capacity-aware inbound backward planning -> Bridge B -> weekly forward push with capacity smoke flow."
    return result
