from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator


PSI_BUCKET_INDEX = {
    "S": 0,
    "CO": 1,
    "I": 2,
    "P": 3,
}

_ALLOWED_MODES = {"replace", "append", "dedupe_append"}


@dataclass
class OutboundInboundDemandBridgeResult:
    source_node_name: str
    target_node_name: str
    bridge_leadtime_weeks: int
    copied_lot_count: int = 0
    weeks_touched: list[str] = field(default_factory=list)
    missing_source_node: bool = False
    missing_target_node: bool = False
    invalid_weeks: list[dict] = field(default_factory=list)
    duplicate_lot_ids: list[str] = field(default_factory=list)
    mode: str = "replace"


def iter_nodes(root: Any) -> Iterator[Any]:
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        children = getattr(node, "children", []) or []
        stack.extend(reversed(children))


def find_node_by_name(root: Any, name: str):
    for node in iter_nodes(root):
        if getattr(node, "name", None) == name:
            return node
    return None


def _validate_bucket_name(bucket: str) -> int:
    if bucket not in PSI_BUCKET_INDEX:
        raise ValueError(f"Unsupported PSI bucket: {bucket}")
    return PSI_BUCKET_INDEX[bucket]


def bridge_outbound_to_inbound_demand(
    *,
    outbound_root,
    inbound_root,
    source_node_name: str = "supply_point",
    target_node_name: str = "supply_point",
    source_bucket: str = "P",
    target_bucket: str = "S",
    layer: str = "demand",
    bridge_leadtime_weeks: int = 0,
    mode: str = "replace",
) -> OutboundInboundDemandBridgeResult:
    if layer != "demand":
        raise ValueError(f"Unsupported layer for Bridge A: {layer}")
    if mode not in _ALLOWED_MODES:
        raise ValueError(f"Unsupported mode: {mode}")

    source_bucket_idx = _validate_bucket_name(source_bucket)
    target_bucket_idx = _validate_bucket_name(target_bucket)

    result = OutboundInboundDemandBridgeResult(
        source_node_name=source_node_name,
        target_node_name=target_node_name,
        bridge_leadtime_weeks=bridge_leadtime_weeks,
        mode=mode,
    )

    source_node = find_node_by_name(outbound_root, source_node_name)
    if source_node is None:
        result.missing_source_node = True
        return result

    target_node = find_node_by_name(inbound_root, target_node_name)
    if target_node is None:
        result.missing_target_node = True
        return result

    source_psi = getattr(source_node, "psi4demand", None)
    target_psi = getattr(target_node, "psi4demand", None)
    if not isinstance(source_psi, list) or not isinstance(target_psi, list):
        raise ValueError("source/target psi4demand must be list-based PSI weeks")

    for source_week in range(len(source_psi)):
        target_week = source_week + bridge_leadtime_weeks
        if target_week < 0 or target_week >= len(target_psi):
            result.invalid_weeks.append(
                {"source_week": source_week, "target_week": target_week, "reason": "target_week_out_of_range"}
            )
            continue

        source_week_data = source_psi[source_week]
        target_week_data = target_psi[target_week]

        if not isinstance(source_week_data, list) or not isinstance(target_week_data, list):
            result.invalid_weeks.append(
                {"source_week": source_week, "target_week": target_week, "reason": "week_data_not_list"}
            )
            continue

        if max(source_bucket_idx, target_bucket_idx) >= len(source_week_data) or max(source_bucket_idx, target_bucket_idx) >= len(target_week_data):
            result.invalid_weeks.append(
                {"source_week": source_week, "target_week": target_week, "reason": "bucket_index_out_of_range"}
            )
            continue

        source_lot_ids = source_week_data[source_bucket_idx]
        target_lot_ids = target_week_data[target_bucket_idx]

        if not isinstance(source_lot_ids, list) or not isinstance(target_lot_ids, list):
            result.invalid_weeks.append(
                {"source_week": source_week, "target_week": target_week, "reason": "bucket_not_list"}
            )
            continue

        if mode == "replace":
            target_week_data[target_bucket_idx] = list(source_lot_ids)
            result.copied_lot_count += len(source_lot_ids)
        elif mode == "append":
            target_lot_ids.extend(source_lot_ids)
            result.copied_lot_count += len(source_lot_ids)
        else:  # dedupe_append
            for lot_id in source_lot_ids:
                if lot_id in target_lot_ids:
                    result.duplicate_lot_ids.append(lot_id)
                    continue
                target_lot_ids.append(lot_id)
                result.copied_lot_count += 1

        result.weeks_touched.append(f"{source_week}->{target_week}")

    return result
