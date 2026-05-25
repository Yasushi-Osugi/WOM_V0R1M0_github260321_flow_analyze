from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator


PSI_BUCKET_INDEX = {
    "S": 0,
    "CO": 1,
    "I": 2,
    "P": 3,
}

_ALLOWED_POLICIES = {"s_p_only", "s_only", "full_clone"}
_ALLOWED_MODES = {"replace", "append", "dedupe_append"}


@dataclass
class DemandToSupplyBridgeResult:
    root_node_name: str
    bridge_policy: str
    mode: str
    bridge_leadtime_weeks: int
    copied_lot_count: int = 0
    weeks_touched: list[int] = field(default_factory=list)
    nodes_touched: list[str] = field(default_factory=list)
    invalid_weeks: list[dict] = field(default_factory=list)
    non_list_bucket_errors: list[dict] = field(default_factory=list)
    duplicate_lot_ids: list[str] = field(default_factory=list)


def iter_nodes(root: Any) -> Iterator[Any]:
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        children = getattr(node, "children", []) or []
        stack.extend(reversed(children))


def _policy_bucket_pairs(bridge_policy: str) -> list[tuple[str, str]]:
    if bridge_policy == "s_p_only":
        return [("S", "S"), ("P", "P")]
    if bridge_policy == "s_only":
        return [("S", "S")]
    if bridge_policy == "full_clone":
        return [("S", "S"), ("CO", "CO"), ("I", "I"), ("P", "P")]
    raise ValueError(f"Unsupported bridge_policy: {bridge_policy}")


def _validate_week_structure(week_data: Any) -> bool:
    return isinstance(week_data, list) and len(week_data) >= 4


def bridge_demand_to_supply_execution(
    *,
    root,
    bridge_policy: str = "s_p_only",
    mode: str = "replace",
    bridge_leadtime_weeks: int = 0,
) -> DemandToSupplyBridgeResult:
    if bridge_policy not in _ALLOWED_POLICIES:
        raise ValueError(f"Unsupported bridge_policy: {bridge_policy}")
    if mode not in _ALLOWED_MODES:
        raise ValueError(f"Unsupported mode: {mode}")

    result = DemandToSupplyBridgeResult(
        root_node_name=getattr(root, "name", ""),
        bridge_policy=bridge_policy,
        mode=mode,
        bridge_leadtime_weeks=bridge_leadtime_weeks,
    )

    pairs = _policy_bucket_pairs(bridge_policy)
    all_bucket_names = ["S", "CO", "I", "P"]

    for node in iter_nodes(root):
        node_name = getattr(node, "name", "")
        demand_psi = getattr(node, "psi4demand", None)
        supply_psi = getattr(node, "psi4supply", None)

        if not isinstance(demand_psi, list) or not isinstance(supply_psi, list):
            result.invalid_weeks.append({"node": node_name, "reason": "psi_not_list"})
            continue

        node_touched = False
        for source_week, demand_week_data in enumerate(demand_psi):
            target_week = source_week + bridge_leadtime_weeks
            if target_week < 0 or target_week >= len(supply_psi):
                result.invalid_weeks.append(
                    {
                        "node": node_name,
                        "source_week": source_week,
                        "target_week": target_week,
                        "reason": "target_week_out_of_range",
                    }
                )
                continue

            supply_week_data = supply_psi[target_week]
            if not _validate_week_structure(demand_week_data) or not _validate_week_structure(supply_week_data):
                result.invalid_weeks.append(
                    {
                        "node": node_name,
                        "source_week": source_week,
                        "target_week": target_week,
                        "reason": "week_data_not_list_or_short",
                    }
                )
                continue

            clear_buckets = all_bucket_names if bridge_policy in {"s_p_only", "s_only"} else []
            if mode == "replace":
                non_list_on_clear = False
                for bucket_name in clear_buckets:
                    idx = PSI_BUCKET_INDEX[bucket_name]
                    bucket = supply_week_data[idx]
                    if not isinstance(bucket, list):
                        result.non_list_bucket_errors.append({
                            "node": node_name,
                            "source_week": source_week,
                            "target_week": target_week,
                            "layer": "supply",
                            "bucket": bucket_name,
                        })
                        non_list_on_clear = True
                    else:
                        bucket.clear()
                if non_list_on_clear:
                    continue

            bucket_error = False
            for source_bucket_name, target_bucket_name in pairs:
                source_idx = PSI_BUCKET_INDEX[source_bucket_name]
                target_idx = PSI_BUCKET_INDEX[target_bucket_name]
                source_bucket = demand_week_data[source_idx]
                target_bucket = supply_week_data[target_idx]

                if not isinstance(source_bucket, list):
                    result.non_list_bucket_errors.append({
                        "node": node_name,
                        "source_week": source_week,
                        "target_week": target_week,
                        "layer": "demand",
                        "bucket": source_bucket_name,
                    })
                    bucket_error = True
                    break
                if not isinstance(target_bucket, list):
                    result.non_list_bucket_errors.append({
                        "node": node_name,
                        "source_week": source_week,
                        "target_week": target_week,
                        "layer": "supply",
                        "bucket": target_bucket_name,
                    })
                    bucket_error = True
                    break

                if mode in {"replace", "append"}:
                    target_bucket.extend(list(source_bucket))
                    result.copied_lot_count += len(source_bucket)
                else:
                    for lot_id in source_bucket:
                        if lot_id in target_bucket:
                            result.duplicate_lot_ids.append(lot_id)
                            continue
                        target_bucket.append(lot_id)
                        result.copied_lot_count += 1

            if bucket_error:
                continue

            if source_week not in result.weeks_touched:
                result.weeks_touched.append(source_week)
            node_touched = True

        if node_touched and node_name not in result.nodes_touched:
            result.nodes_touched.append(node_name)

    return result
