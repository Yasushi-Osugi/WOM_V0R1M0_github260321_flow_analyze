from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pysi.cases.japanese_rice.rice_actual_prod_tree_seed_integration import (
    seed_rice_weekly_input_to_actual_product_plan_nodes,
)
from pysi.plan.engines import outbound_backward_leaf_to_MOM


@dataclass
class RiceBackwardPlanningAfterSeedResult:
    product_name: str
    seed_count: int = 0
    backward_planning_ran: bool = False
    lot_ids_before: set[str] = field(default_factory=set)
    lot_ids_after: set[str] = field(default_factory=set)
    missing_lot_ids_after: set[str] = field(default_factory=set)
    non_list_bucket_errors: list[dict] = field(default_factory=list)
    non_string_lot_errors: list[dict] = field(default_factory=list)
    touched_nodes: list[str] = field(default_factory=list)
    message: str = ""


def _walk_tree(root: Any):
    stack = [root]
    seen = set()
    while stack:
        node = stack.pop()
        if node is None:
            continue
        node_id = id(node)
        if node_id in seen:
            continue
        seen.add(node_id)
        yield node
        children = getattr(node, "children", []) or []
        stack.extend(reversed(children))


def collect_lot_ids_from_demand_tree(root) -> set[str]:
    lot_ids: set[str] = set()
    for node in _walk_tree(root):
        psi = getattr(node, "psi4demand", None)
        if not isinstance(psi, list):
            continue
        for week_row in psi:
            if not isinstance(week_row, list):
                continue
            for bucket in week_row:
                if isinstance(bucket, list):
                    for item in bucket:
                        if isinstance(item, str):
                            lot_ids.add(item)
    return lot_ids


def validate_psi_buckets_are_lot_id_lists(root, *, layer="demand") -> tuple[list[dict], list[dict]]:
    attr = "psi4demand" if layer == "demand" else "psi4supply"
    non_list_bucket_errors: list[dict] = []
    non_string_lot_errors: list[dict] = []

    for node in _walk_tree(root):
        psi = getattr(node, attr, None)
        if not isinstance(psi, list):
            non_list_bucket_errors.append({"node": getattr(node, "name", ""), "error": f"{attr} is not list"})
            continue

        for week_index, week_row in enumerate(psi):
            if not isinstance(week_row, list):
                non_list_bucket_errors.append(
                    {"node": getattr(node, "name", ""), "week_index": week_index, "error": "week row is not list"}
                )
                continue
            for bucket_index, bucket in enumerate(week_row):
                if not isinstance(bucket, list):
                    non_list_bucket_errors.append(
                        {
                            "node": getattr(node, "name", ""),
                            "week_index": week_index,
                            "bucket_index": bucket_index,
                            "error": "bucket is not list",
                        }
                    )
                    continue
                for lot in bucket:
                    if not isinstance(lot, str):
                        non_string_lot_errors.append(
                            {
                                "node": getattr(node, "name", ""),
                                "week_index": week_index,
                                "bucket_index": bucket_index,
                                "value": lot,
                            }
                        )

    return non_list_bucket_errors, non_string_lot_errors


def run_rice_backward_planning_after_seed_smoke(
    *,
    out_root,
    in_root,
    product_name: str,
    case_data,
    dry_run_seed: bool = False,
) -> RiceBackwardPlanningAfterSeedResult:
    seed_result = seed_rice_weekly_input_to_actual_product_plan_nodes(
        case_data=case_data,
        product_name=product_name,
        outbound_root=out_root,
        inbound_root=in_root,
        dry_run=dry_run_seed,
    )

    result = RiceBackwardPlanningAfterSeedResult(
        product_name=product_name,
        seed_count=seed_result.plan_node_seeded_count,
        touched_nodes=sorted({k[0] for k in seed_result.seeding_result.seeded_by_key}) if seed_result.seeding_result else [],
    )

    result.lot_ids_before = collect_lot_ids_from_demand_tree(out_root) | collect_lot_ids_from_demand_tree(in_root)

    outbound_backward_leaf_to_MOM(out_root, in_root, layer="demand")
    result.backward_planning_ran = True

    result.lot_ids_after = collect_lot_ids_from_demand_tree(out_root) | collect_lot_ids_from_demand_tree(in_root)
    result.missing_lot_ids_after = result.lot_ids_before - result.lot_ids_after

    out_non_list, out_non_string = validate_psi_buckets_are_lot_id_lists(out_root, layer="demand")
    in_non_list, in_non_string = validate_psi_buckets_are_lot_id_lists(in_root, layer="demand")
    result.non_list_bucket_errors = out_non_list + in_non_list
    result.non_string_lot_errors = out_non_string + in_non_string

    result.message = "ok" if not result.missing_lot_ids_after and not result.non_list_bucket_errors and not result.non_string_lot_errors else "issues_found"
    return result
