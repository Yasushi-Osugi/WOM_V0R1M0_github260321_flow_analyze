from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pysi.capacity.capacity_model import CapacityBucket, CapacityUsage, CapacityViolation

PSI_S = 0
PSI_I = 2
PSI_P = 3


def build_capacity_lookup(
    capacity_buckets: list[CapacityBucket],
) -> dict[tuple[str, str, str, int | str, str], CapacityBucket]:
    return {
        (b.scenario_id, b.node_name, b.product_name, b.week, b.capacity_type): b
        for b in capacity_buckets
    }


def get_capacity_bucket(
    lookup: dict,
    *,
    scenario_id: str,
    node_name: str,
    product_name: str,
    week: int | str,
    capacity_type: Literal["P", "S", "I"],
    default_cap_mode: Literal["soft", "hard"] = "soft",
    missing_capacity_qty: int = 10**12,
) -> CapacityBucket:
    exact = lookup.get((scenario_id, node_name, product_name, week, capacity_type))
    if exact is not None:
        return exact
    wildcard = lookup.get((scenario_id, node_name, "*", week, capacity_type))
    if wildcard is not None:
        return wildcard
    return CapacityBucket(scenario_id, node_name, product_name, week, capacity_type, missing_capacity_qty, default_cap_mode)


def split_lots_by_capacity(lot_ids: list[str], capacity_qty: int) -> tuple[list[str], list[str]]:
    if capacity_qty <= 0:
        return [], list(lot_ids)
    return list(lot_ids[:capacity_qty]), list(lot_ids[capacity_qty:])


def get_next_week(weeks: list[int | str], current_week: int | str) -> int | str | None:
    try:
        idx = weeks.index(current_week)
    except ValueError:
        return None
    return weeks[idx + 1] if idx + 1 < len(weeks) else None


def get_node_name(node) -> str:
    return getattr(
        node,
        "name",
        getattr(node, "node_name", getattr(node, "name4node", "UNKNOWN_NODE")),
    )


def _get_psi_lots(node, layer: str, week: int | str, idx: int) -> list[str]:
    table = getattr(node, layer, None)
    if table is None:
        return []
    try:
        row = table[week] if isinstance(table, dict) else table[int(week)]
        lots = row[idx]
        return list(lots) if lots is not None else []
    except Exception:
        return []


def _set_psi_lots(node, layer: str, week: int | str, idx: int, lot_ids: list[str]) -> None:
    table = getattr(node, layer, None)
    if table is None:
        return
    try:
        row = table[week] if isinstance(table, dict) else table[int(week)]
        row[idx] = list(lot_ids)
    except Exception:
        return


def get_target_lots_for_P(node, week) -> list[str]:
    return _get_psi_lots(node, "psi4demand", week, PSI_P)


def get_target_lots_for_S(node, week) -> list[str]:
    return _get_psi_lots(node, "psi4demand", week, PSI_S)


def apply_P_execution(node, week, lot_ids: list[str]) -> None:
    _set_psi_lots(node, "psi4supply", week, PSI_P, lot_ids)


def apply_S_execution(node, week, lot_ids: list[str]) -> None:
    _set_psi_lots(node, "psi4supply", week, PSI_S, lot_ids)


def get_ending_inventory_lots(node, week) -> list[str]:
    return _get_psi_lots(node, "psi4supply", week, PSI_I)


def _children(node) -> list:
    for attr in ("children", "child_nodes", "children_nodes"):
        x = getattr(node, attr, None)
        if isinstance(x, Iterable):
            return list(x)
    return []


def iter_nodes_for_capacity_forward(root_node, tree_side: str):
    side = (tree_side or "OUTBOUND").upper()
    if side == "INBOUND":
        def post(n):
            for c in _children(n):
                yield from post(c)
            yield n
        yield from post(root_node)
    else:
        def pre(n):
            yield n
            for c in _children(n):
                yield from pre(c)
        yield from pre(root_node)


def with_capacity_forward_planning(*, root_node, weeks: list[int | str], scenario_id: str, product_name: str,
                                   capacity_buckets: list[CapacityBucket], tree_side: Literal["OUTBOUND", "INBOUND"],
                                   node_order: list | None = None,
                                   default_cap_mode: Literal["soft", "hard"] = "soft") -> tuple[list[CapacityUsage], list[CapacityViolation]]:
    lookup = build_capacity_lookup(capacity_buckets)
    usages: list[CapacityUsage] = []
    violations: list[CapacityViolation] = []
    nodes = node_order if node_order is not None else list(iter_nodes_for_capacity_forward(root_node, tree_side))

    for week in weeks:
        for node in nodes:
            node_name = get_node_name(node)
            for cap_type, getter, applier in [
                ("P", get_target_lots_for_P, apply_P_execution),
                ("S", get_target_lots_for_S, apply_S_execution),
            ]:
                target = getter(node, week)
                bucket = get_capacity_bucket(lookup, scenario_id=scenario_id, node_name=node_name, product_name=product_name,
                                             week=week, capacity_type=cap_type, default_cap_mode=default_cap_mode)
                executable, overflow = split_lots_by_capacity(target, bucket.capacity_qty)
                applier(node, week, executable)
                usages.append(CapacityUsage(scenario_id, tree_side, node_name, product_name, week, cap_type,
                                            bucket.capacity_qty, len(executable), executable))
                if overflow:
                    next_week = get_next_week(weeks, week)
                    if bucket.cap_mode == "soft":
                        if next_week is not None:
                            next_target = getter(node, next_week)
                            applier_fn = apply_P_execution if cap_type == "P" else apply_S_execution
                            applier_fn(node, next_week, next_target + overflow)
                        action = "CARRY_OVER"
                        violation_type = "CAPACITY_OVER_SOFT"
                    else:
                        action = "BLOCKED"
                        violation_type = "CAPACITY_OVER_HARD"
                    violations.append(CapacityViolation(scenario_id, tree_side, node_name, product_name, week, cap_type,
                                                        bucket.cap_mode, bucket.capacity_qty, len(target), len(overflow),
                                                        violation_type, overflow, action))

            i_lots = get_ending_inventory_lots(node, week)
            i_bucket = get_capacity_bucket(lookup, scenario_id=scenario_id, node_name=node_name, product_name=product_name,
                                           week=week, capacity_type="I", default_cap_mode=default_cap_mode)
            i_exec, i_over = split_lots_by_capacity(i_lots, i_bucket.capacity_qty)
            usages.append(CapacityUsage(scenario_id, tree_side, node_name, product_name, week, "I",
                                        i_bucket.capacity_qty, len(i_exec), i_exec))
            if i_over:
                violations.append(CapacityViolation(
                    scenario_id, tree_side, node_name, product_name, week, "I", i_bucket.cap_mode,
                    i_bucket.capacity_qty, len(i_lots), len(i_over),
                    "INVENTORY_OVER_SOFT" if i_bucket.cap_mode == "soft" else "INVENTORY_OVER_HARD",
                    i_over,
                    "ALERT_ONLY" if i_bucket.cap_mode == "soft" else "WASTE"
                ))
    return usages, violations
