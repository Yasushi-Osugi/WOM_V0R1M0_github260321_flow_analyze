"""Build reporting input from static payload or environment object."""

from __future__ import annotations

import csv
from pathlib import Path
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


def _default_cost_master_dir() -> Path:
    # pysi/reporting/report_input_builder.py -> repo_root/data/cost_masters
    return Path(__file__).resolve().parents[2] / "data" / "cost_masters"


def _load_cs_node_to_market_map(base_dir: Path | None = None) -> dict[tuple[str, str], str]:
    """
    Returns:
        {(cs_node, product_name): market_id}
    """
    base = base_dir or _default_cost_master_dir()
    path = base / "cs_node_to_market_map.csv"
    mapping: dict[tuple[str, str], str] = {}

    if not path.exists():
        return mapping

    with path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            cs_node = (row.get("cs_node") or "").strip()
            product_name = (row.get("product_name") or "").strip()
            market_id = (row.get("market_id") or "").strip()
            if not cs_node or not product_name or not market_id:
                continue
            mapping[(cs_node, product_name)] = market_id

    return mapping


def _fallback_market_id(node_name: str, node: Any) -> str:
    """
    Backward-compatible fallback only when map CSV does not provide a match.
    """
    for attr in ("market_id", "market", "sales_market"):
        value = getattr(node, attr, None)
        if value:
            return str(value)

    name = str(node_name or "")
    if name.startswith("CS_US"):
        return "MKT_US_UNKNOWN"
    if name.startswith("CS_DE"):
        return "MKT_DE_UNKNOWN"
    if name.startswith("CS_UK"):
        return "MKT_UK_UNKNOWN"
    if name.startswith("CS_JP"):
        return "MKT_JP_UNKNOWN"
    if name.startswith("CS_CN"):
        return "MKT_CN_UNKNOWN"
    if name.startswith("CS_IN"):
        return "MKT_IN_UNKNOWN"
    return ""


def _resolve_market_id(
    *,
    node_name: str,
    product_name: str,
    node: Any,
    cs_to_market_map: dict[tuple[str, str], str],
) -> str:
    # 1) exact mapping: (cs_node, product_name)
    key = (node_name, product_name)
    if key in cs_to_market_map:
        return cs_to_market_map[key]

    # 2) fallback heuristic
    return _fallback_market_id(node_name, node)


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
        cs_to_market_map = _load_cs_node_to_market_map()

        for node_name, node in node_dict.items():
            psi = getattr(node, "psi4demand", None)
            if not isinstance(psi, list) or not psi:
                continue

            market_id = _resolve_market_id(
                node_name=node_name,
                product_name=product,
                node=node,
                cs_to_market_map=cs_to_market_map,
            )

            for week_index in range(len(psi)):
                qty = _extract_qty_from_node(node, week_index)
                if qty <= 0:
                    continue

                records.append(
                    {
                        "product": product,
                        "product_id": product,
                        "node": node_name,
                        "node_id": node_name,
                        "week": week_index,
                        "week_index": week_index,
                        "qty": qty,
                        "market": market_id,
                        "market_id": market_id,
                        "sales_units": qty,
                    }
                )

    return {"records": records}