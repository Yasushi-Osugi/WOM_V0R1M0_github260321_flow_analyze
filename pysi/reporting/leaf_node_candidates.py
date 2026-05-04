from __future__ import annotations

import csv
from typing import Any


def get_plan_node_name(node: Any) -> str:
    for attr in ("name", "node_name", "node_id"):
        val = getattr(node, attr, None)
        if val is not None:
            s = str(val).strip()
            if s:
                return s
    return ""


def get_plan_children(node: Any) -> list[Any]:
    for attr in ("children", "child_nodes"):
        children = getattr(node, attr, None)
        if children is None:
            continue
        if isinstance(children, dict):
            return list(children.values())
        if isinstance(children, (list, tuple)):
            return list(children)
    return []


def _sorted_unique(values: list[str]) -> list[str]:
    return sorted({v.strip() for v in values if isinstance(v, str) and v.strip()})


def collect_leaf_nodes_from_product_outbound_tree(env: Any, product_name: str) -> list[str]:
    prod_tree_dict_ot = getattr(env, "prod_tree_dict_OT", {}) or {}
    root = prod_tree_dict_ot.get(product_name)
    if root is None:
        return []

    leaves: list[str] = []
    stack = [root]
    visited = set()

    while stack:
        node = stack.pop()
        node_id = id(node)
        if node_id in visited:
            continue
        visited.add(node_id)

        children = get_plan_children(node)
        if not children:
            name = get_plan_node_name(node)
            if name:
                leaves.append(name)
            continue

        stack.extend(children)

    return _sorted_unique(leaves)


def collect_leaf_nodes_from_env_leaf_nodes_out(env: Any) -> list[str]:
    leaf_nodes_out = getattr(env, "leaf_nodes_out", []) or []
    names: list[str] = []

    for item in leaf_nodes_out:
        if isinstance(item, str):
            name = item.strip()
        else:
            name = (
                getattr(item, "name", None)
                or getattr(item, "node_name", None)
                or getattr(item, "node_id", None)
                or str(item)
            )
            name = str(name).strip()
        if name:
            names.append(name)

    return _sorted_unique(names)


def collect_leaf_nodes_from_price_trace_csv(path: str, product_name: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    except Exception:
        return []

    product_rows = [
        r for r in rows
        if not product_name or str(r.get("product", "")).strip() == product_name
    ]
    if not product_rows:
        return []

    outbound_rows = [
        r for r in product_rows
        if str(r.get("direction", "")).strip().lower() == "outbound"
    ]
    target_rows = outbound_rows or product_rows

    from_nodes = {
        str(r.get("from_node", "")).strip()
        for r in target_rows
        if str(r.get("from_node", "")).strip()
    }
    to_nodes = {
        str(r.get("to_node", "")).strip()
        for r in target_rows
        if str(r.get("to_node", "")).strip()
    }

    leaves = [n for n in to_nodes if n not in from_nodes]
    return _sorted_unique(leaves)


def get_leaf_node_candidates_for_product(
    env: Any,
    *,
    product_name: str,
    price_propagation_trace_csv: str = "data/price_propagation_trace.csv",
) -> list[str]:
    leaves = collect_leaf_nodes_from_product_outbound_tree(env, product_name)
    if leaves:
        return leaves

    leaves = collect_leaf_nodes_from_env_leaf_nodes_out(env)
    if leaves:
        return leaves

    return collect_leaf_nodes_from_price_trace_csv(price_propagation_trace_csv, product_name)
