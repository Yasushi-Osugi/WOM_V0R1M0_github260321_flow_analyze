from __future__ import annotations

import csv
import os
from typing import Any, Dict, List


def _safe_float(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def _walk_nodes(root: Any):
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


def _node_name(node: Any) -> str:
    return (getattr(node, "name", "") or getattr(node, "id", "") or "").strip()


def _write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path, "w", newline="", encoding="utf-8") as f:
            f.write("")
        return

    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def export_money_outputs(
    output_dir: str,
    node_money_rows: List[Dict[str, Any]],
    kpi_summary_rows: List[Dict[str, Any]],
    product_money_summary_rows: List[Dict[str, Any]],
    env: Any = None,
) -> Dict[str, str]:
    node_path = os.path.join(output_dir, "node_money_eval.csv")
    kpi_path = os.path.join(output_dir, "kpi_summary.csv")
    product_path = os.path.join(output_dir, "product_money_summary.csv")
    waterfall_path = os.path.join(output_dir, "node_price_waterfall.csv")
    trace_path = os.path.join(output_dir, "price_propagation_trace.csv")

    _write_csv(node_path, node_money_rows)
    _write_csv(kpi_path, kpi_summary_rows)
    _write_csv(product_path, product_money_summary_rows)
    _write_csv(waterfall_path, export_node_price_waterfall(node_money_rows, env=env))
    _write_csv(trace_path, export_price_propagation_trace(node_money_rows, env=env))

    return {
        "node_money_eval_csv": node_path,
        "kpi_summary_csv": kpi_path,
        "product_money_summary_csv": product_path,
        "node_price_waterfall_csv": waterfall_path,
        "price_propagation_trace_csv": trace_path,
    }


def export_node_price_waterfall(node_money_rows: List[Dict[str, Any]], env: Any = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for i, r in enumerate(node_money_rows, start=1):
        rows.append(
            {
                "product": r.get("product", ""),
                "product_name": r.get("product_name", r.get("product", "")),
                "direction": "unknown",
                "sequence_no": i,
                "node_name": r.get("node_name", ""),
                "node_character": r.get("node_character", ""),
                "price_formation_mode": r.get("price_formation_mode", ""),
                "purchase_cost_per_lot": _safe_float(r.get("purchase_cost_per_lot")),
                "value_added_cost_per_lot": _safe_float(r.get("value_added_cost_per_lot")),
                "variable_cost_per_lot": _safe_float(r.get("variable_cost_per_lot")),
                "fixed_cost_per_week": _safe_float(r.get("fixed_cost_per_week")),
                "fixed_cost_per_lot": _safe_float(r.get("fixed_cost_per_lot")),
                "logistics_cost_per_lot": _safe_float(r.get("logistics_cost_per_lot")),
                "inventory_handling_cost_per_lot": _safe_float(r.get("inventory_handling_cost_per_lot")),
                "tax_rate": _safe_float(r.get("tax_rate")),
                "tax_tariff_cost_per_lot": _safe_float(r.get("tax_tariff_cost_per_lot")),
                "target_profit_per_lot": _safe_float(r.get("target_profit_per_lot")),
                "ship_price_per_lot": _safe_float(r.get("ship_price_per_lot")),
                "inventory_unit_value_per_lot": _safe_float(r.get("inventory_unit_value_per_lot")),
                "revenue": _safe_float(r.get("revenue")),
                "purchase_amount": _safe_float(r.get("purchase_amount")),
                "variable_cost": _safe_float(r.get("variable_cost")),
                "fixed_cost": _safe_float(r.get("fixed_cost")),
                "tax_cost": _safe_float(r.get("tax")),
                "profit": _safe_float(r.get("profit")),
                "ending_inventory_value": _safe_float(r.get("ending_inventory_value")),
                "inventory_value": _safe_float(r.get("inventory_value")),
                "remarks": "",
            }
        )
    return rows


def export_price_propagation_trace(node_money_rows: List[Dict[str, Any]], env: Any = None) -> List[Dict[str, Any]]:
    by_key = {(r.get("product"), r.get("node_name")): r for r in node_money_rows}
    out: List[Dict[str, Any]] = []

    for direction, tree_map in (("outbound", getattr(env, "prod_tree_dict_OT", {}) if env else {}), ("inbound", getattr(env, "prod_tree_dict_IN", {}) if env else {})):
        for product, root in (tree_map or {}).items():
            seq = 1
            for parent in _walk_nodes(root):
                for child in getattr(parent, "children", []) or []:
                    p_name = _node_name(parent)
                    c_name = _node_name(child)
                    if not p_name or not c_name:
                        continue
                    p_row = by_key.get((product, p_name), {})
                    c_row = by_key.get((product, c_name), {})
                    parent_ship = _safe_float(p_row.get("ship_price_per_lot"))
                    child_purchase = _safe_float(c_row.get("purchase_cost_per_lot"))
                    child_ship = _safe_float(c_row.get("ship_price_per_lot"))
                    propagated = parent_ship
                    source = "propagated_from_parent_ship_price" if abs(child_purchase - parent_ship) < 1e-9 and parent_ship != 0 else ("explicit" if child_purchase != 0 else "fallback_zero")
                    out.append(
                        {
                            "product": product,
                            "product_name": c_row.get("product_name", product),
                            "direction": direction,
                            "sequence_no": seq,
                            "from_node": p_name,
                            "from_node_character": p_row.get("node_character", ""),
                            "to_node": c_name,
                            "to_node_character": c_row.get("node_character", ""),
                            "parent_ship_price_per_lot": parent_ship,
                            "child_purchase_cost_per_lot": child_purchase,
                            "child_ship_price_per_lot": child_ship,
                            "propagated_purchase_cost_per_lot": propagated,
                            "purchase_cost_source": source,
                            "delta_parent_ship_to_child_purchase": child_purchase - parent_ship,
                            "delta_child_purchase_to_child_ship": child_ship - child_purchase,
                            "child_price_formation_mode": c_row.get("price_formation_mode", ""),
                            "edge_leadtime": "",
                            "edge_lot_size": "",
                            "edge_transport_mode": "",
                            "remarks": "",
                        }
                    )
                    seq += 1
    return out
