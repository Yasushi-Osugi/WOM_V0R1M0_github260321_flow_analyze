"""Build reporting input from static payload or environment object."""

from __future__ import annotations

from typing import Any


def _iter_nodes(root: Any):
    stack = [root]
    while stack:
        n = stack.pop()
        if n is None:
            continue
        yield n
        for c in getattr(n, "children", []) or []:
            stack.append(c)


def _ensure_env_node_dict(env: Any, product: str | None = None) -> dict[str, Any]:
    node_dict = getattr(env, "node_dict", None)
    if isinstance(node_dict, dict) and node_dict:
        return node_dict

    roots = []
    if product:
        roots.append((getattr(env, "prod_tree_dict_OT", {}) or {}).get(product))
        roots.append((getattr(env, "prod_tree_dict_IN", {}) or {}).get(product))
    else:
        roots.extend((getattr(env, "prod_tree_dict_OT", {}) or {}).values())
        roots.extend((getattr(env, "prod_tree_dict_IN", {}) or {}).values())

    built: dict[str, Any] = {}
    for root in roots:
        if root is None:
            continue
        for n in _iter_nodes(root):
            name = getattr(n, "name", None)
            if name and name not in built:
                built[name] = n

    setattr(env, "node_dict", built)
    return built


def _extract_qty_from_node(node: Any, week_index: int) -> float:
    psi = getattr(node, "psi4demand", None)
    if not isinstance(psi, list):
        return 0.0
    if week_index >= len(psi):
        return 0.0
    week_bucket = psi[week_index]
    if not isinstance(week_bucket, list) or len(week_bucket) < 1:
        return 0.0
    sales_bucket = week_bucket[0] or []
    return float(len(sales_bucket))


def _detect_market_id(node_name: str, node: Any) -> str:
    for attr in ("market_id", "market", "sales_market"):
        value = getattr(node, attr, None)
        if value:
            return str(value)

    name = str(node_name or "")
    if name.startswith("CS_US"):
        return "US"
    if name.startswith("CS_DE"):
        return "DE"
    if name.startswith("CS_UK"):
        return "UK"
    if name.startswith("CS_JP"):
        return "JP"
    if name.startswith("CS_CN"):
        return "CN"
    if name.startswith("CS_IN"):
        return "IN"
    return ""


def build_report_input(
    planning_result: dict[str, Any] | None = None,
    env: Any = None,
) -> dict[str, Any]:
    """Build normalized report input.

    Returns {'records': [...]} where each record is product×node×week grain.
    """
    if planning_result and isinstance(planning_result.get("records"), list):
        return {"records": list(planning_result["records"])}

    records: list[dict[str, Any]] = []

    if env is not None:
        product = getattr(env, "product_selected", None) or "UNKNOWN_PRODUCT"
        node_dict = _ensure_env_node_dict(env, product=product)

        for node_name, node in node_dict.items():
            psi = getattr(node, "psi4demand", None)
            if not isinstance(psi, list) or not psi:
                continue

            market_id = _detect_market_id(node_name, node)

            for week_index in range(len(psi)):
                qty = _extract_qty_from_node(node, week_index)
                if qty <= 0:
                    continue

                #@STOP
                #records.append(
                #    {
                #        "product": product,
                #        "product_id": product,
                #        "node": node_name,
                #        "node_id": node_name,
                #        "week": f"2026-W{week_index + 1:02d}",
                #        "week_index": week_index,
                #        "qty": qty,
                #        "market": market_id,
                #        "market_id": market_id,
                #        "sales_units": qty,
                #    }
                #)

                records.append(
                    {
                        "product": product,
                        "product_id": "IPHONE_STD",   # ← 仮固定
                        "node": node_name,
                        "node_id": node_name,
                        "week": week_index,           # ← ★ここ重要
                        "week_index": week_index,
                        "qty": qty,
                        "market": market_id,
                        "market_id": market_id or "DEFAULT",  # ← ★ここ重要
                        "sales_units": qty,
                    }
                )



    return {"records": records}