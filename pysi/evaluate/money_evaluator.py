from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List


def _safe_float(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def _walk_nodes(root: Any) -> Iterable[Any]:
    stack = [root]
    seen = set()
    while stack:
        node = stack.pop()
        if node is None:
            continue
        oid = id(node)
        if oid in seen:
            continue
        seen.add(oid)
        yield node
        for c in getattr(node, "children", []) or []:
            stack.append(c)


def _legacy_node_character(node_name: str) -> str:
    # backward-compatible fallback; future logic should use master lookup first
    n = (node_name or "").strip().lower()
    if n == "supply_point":
        return "supply_point"
    if n.startswith("market"):
        return "market"
    if n.startswith("dc"):
        return "distribution_center"
    if n.startswith("plant"):
        return "factory"
    return "unknown"


def _last_inventory_lots(node: Any) -> int:
    """
    Return last-week inventory lot count from psi4supply[w][2].
    Safe fallback = 0.
    """
    psi4supply = getattr(node, "psi4supply", None) or []
    if not psi4supply:
        return 0

    try:
        last_week = psi4supply[-1]
        lots = last_week[2] if len(last_week) > 2 else []
        return len(lots or [])
    except Exception:
        return 0


def _inventory_unit_value_from_master(bundle: Any, node_name: str, product: str) -> float:
    """
    Read inventory_unit_value from node_product_money_master.
    Safe fallback = 0.0.
    """
    if bundle is None:
        return 0.0

    try:
        rec = bundle.get_node_product_money(node_name, product)
    except Exception:
        rec = None

    if rec is None:
        return 0.0

    return _safe_float(getattr(rec, "inventory_unit_value", 0.0))


def _total_shipped_lots(node: Any) -> int:
    """
    Return cumulative shipped/sales lot count from psi4supply[w][0].
    Safe fallback = 0.
    """
    psi4supply = getattr(node, "psi4supply", None) or []
    if not psi4supply:
        return 0

    total = 0
    for week in psi4supply:
        try:
            lots = week[0] if len(week) > 0 else []
            total += len(lots or [])
        except Exception:
            continue
    return total


def _revenue_unit_value_from_master(bundle: Any, node_name: str, product: str) -> float:
    """
    Read revenue_unit_value from node_product_money_master.
    Safe fallback = 0.0.
    """
    if bundle is None:
        return 0.0

    try:
        rec = bundle.get_node_product_money(node_name, product)
    except Exception:
        rec = None

    if rec is None:
        return 0.0

    return _safe_float(getattr(rec, "revenue_unit_value", 0.0))


def _variable_cost_unit_value_from_master(bundle: Any, node_name: str, product: str) -> float:
    """
    Read variable_cost_unit_value from node_product_money_master.
    Safe fallback = 0.0.
    """
    if bundle is None:
        return 0.0

    try:
        rec = bundle.get_node_product_money(node_name, product)
    except Exception:
        rec = None

    if rec is None:
        return 0.0

    return _safe_float(getattr(rec, "variable_cost_unit_value", 0.0))


def _fixed_cost_weekly_from_master(bundle: Any, node_name: str, product: str) -> float:
    """
    Read fixed_cost_weekly from node_product_money_master.
    Safe fallback = 0.0.
    """
    if bundle is None:
        return 0.0

    try:
        rec = bundle.get_node_product_money(node_name, product)
    except Exception:
        rec = None

    if rec is None:
        return 0.0

    return _safe_float(getattr(rec, "fixed_cost_weekly", 0.0))


def evaluate_money_by_node(env: Any) -> List[Dict[str, Any]]:
    """
    Build minimal node-level money rows after planning.
    If accounting sources are missing, return safe zero placeholders.
    """
    ot = getattr(env, "prod_tree_dict_OT", {}) or {}
    inn = getattr(env, "prod_tree_dict_IN", {}) or {}
    products = sorted(set(ot.keys()) | set(inn.keys()))
    bundle = getattr(env, "money_master_bundle", None)

    rows: List[Dict[str, Any]] = []
    uniq = set()
    for product in products:
        for root in (ot.get(product), inn.get(product)):
            if root is None:
                continue
            for node in _walk_nodes(root):
                node_name = (getattr(node, "name", "") or getattr(node, "id", "") or "").strip()
                if not node_name:
                    continue
                key = (product, node_name)
                if key in uniq:
                    continue
                uniq.add(key)

                node_character = None
                if bundle is not None:
                    try:
                        node_character = bundle.get_node_character(node_name)
                    except Exception:
                        node_character = None
                if not node_character:
                    node_character = _legacy_node_character(node_name)

                money_master_found = 0
                if bundle is not None:
                    try:
                        money_master_found = 1 if bundle.get_money_master_by_node_character(node_character) else 0
                    except Exception:
                        money_master_found = 0

                #@STOP
                #revenue = 0.0
                #variable_cost = 0.0
                #fixed_cost = 0.0
                #inventory_value = 0.0
                #tax_base = revenue - variable_cost - fixed_cost
                #profit = tax_base

                print("product node_name", product, node_name)

                revenue = 0.0
                if node_character in ("CS", "RT"):
                    shipped_lots = _total_shipped_lots(node)
                    revenue_unit_value = _revenue_unit_value_from_master(
                        bundle,
                        node_name,
                        product,
                    )
                    revenue = shipped_lots * revenue_unit_value
                    print("shipped_lots = ", shipped_lots)
                    print("revenue_unit_value = ", revenue_unit_value)
                    print("revenue = ", revenue)


                variable_cost = 0.0
                if node_character in ("MOM", "DAD", "WS"):
                    flow_lots = _total_shipped_lots(node)
                    variable_cost_unit_value = _variable_cost_unit_value_from_master(
                        bundle,
                        node_name,
                        product,
                    )
                    variable_cost = flow_lots * variable_cost_unit_value


                fixed_cost = 0.0
                if node_character in ("MOM", "DAD", "WS"):
                    fixed_cost = _fixed_cost_weekly_from_master(
                        bundle,
                        node_name,
                        product,
                    )

                # ********
                # Inventory Evaluation
                # ********
                inventory_lots = _last_inventory_lots(node)
                inventory_unit_value = _inventory_unit_value_from_master(
                    bundle,
                    node_name,
                    product,
                )

                inventory_value = inventory_lots * inventory_unit_value
                print("inventory_lots = ", inventory_lots)
                print("inventory_unit_value = ", inventory_unit_value)
                print("inventory_value = ", inventory_value)

                tax_base = revenue - variable_cost - fixed_cost
                profit = tax_base


                rows.append(
                    {
                        "product": product,
                        "node_name": node_name,
                        "node_character": node_character,
                        "money_master_found": money_master_found,
                        "revenue": _safe_float(revenue),
                        "variable_cost": _safe_float(variable_cost),
                        "fixed_cost": _safe_float(fixed_cost),
                        "inventory_value": _safe_float(inventory_value),
                        "tax_base": _safe_float(tax_base),
                        "profit": _safe_float(profit),
                    }
                )

    # ------------------------------------------------------------
    # Backward-compatible bridge for existing GUI / reporting code
    # ------------------------------------------------------------
    try:
        env.node_money_rows = rows
        env.money_node_rows = rows

        money_result = getattr(env, "money_result", None)
        if not isinstance(money_result, dict):
            money_result = {}

        money_result["node_money_rows"] = rows
        money_result["kpi_summary_rows"] = build_kpi_summary(rows)
        money_result["product_money_summary_rows"] = build_product_money_summary(rows)

        env.money_result = money_result
    except Exception as e:
        print(f"[WARN] failed to attach money rows to env: {e}")

    return rows


def build_kpi_summary(node_money_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    total_revenue = sum(_safe_float(r.get("revenue")) for r in node_money_rows)
    total_variable_cost = sum(_safe_float(r.get("variable_cost")) for r in node_money_rows)
    total_fixed_cost = sum(_safe_float(r.get("fixed_cost")) for r in node_money_rows)
    total_inventory_value = sum(_safe_float(r.get("inventory_value")) for r in node_money_rows)
    total_tax_base = sum(_safe_float(r.get("tax_base")) for r in node_money_rows)
    total_profit = sum(_safe_float(r.get("profit")) for r in node_money_rows)
    node_count = len({r.get("node_name") for r in node_money_rows})
    product_count = len({r.get("product") for r in node_money_rows})

    return [
        {
            "node_count": node_count,
            "product_count": product_count,
            "total_revenue": total_revenue,
            "total_variable_cost": total_variable_cost,
            "total_fixed_cost": total_fixed_cost,
            "total_inventory_value": total_inventory_value,
            "total_tax_base": total_tax_base,
            "total_profit": total_profit,
            "profit_ratio": (total_profit / total_revenue) if total_revenue else 0.0,
        }
    ]


def build_product_money_summary(node_money_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    agg = defaultdict(
        lambda: {
            "product": "",
            "node_count": 0,
            "total_revenue": 0.0,
            "total_variable_cost": 0.0,
            "total_fixed_cost": 0.0,
            "total_inventory_value": 0.0,
            "total_tax_base": 0.0,
            "total_profit": 0.0,
        }
    )
    nodes = defaultdict(set)
    for r in node_money_rows:
        p = (r.get("product") or "").strip()
        d = agg[p]
        d["product"] = p
        d["total_revenue"] += _safe_float(r.get("revenue"))
        d["total_variable_cost"] += _safe_float(r.get("variable_cost"))
        d["total_fixed_cost"] += _safe_float(r.get("fixed_cost"))
        d["total_inventory_value"] += _safe_float(r.get("inventory_value"))
        d["total_tax_base"] += _safe_float(r.get("tax_base"))
        d["total_profit"] += _safe_float(r.get("profit"))
        nodes[p].add(r.get("node_name"))

    out = []
    for p, d in agg.items():
        d["node_count"] = len(nodes[p])
        d["profit_ratio"] = (d["total_profit"] / d["total_revenue"]) if d["total_revenue"] else 0.0
        out.append(d)
    return sorted(out, key=lambda x: x["product"])