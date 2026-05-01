from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from .mosd_loader import load_mosd
from .mosd_schema import validate_mosd_schema

TREE_COLUMNS = ["Product_name", "Parent_node", "Child_node", "child_node_name", "lot_size", "leadtime", "process_capa", "long_vacation_weeks", "LT_boat", "LT_air", "LT_qourier", "weeks_year", "SS_days", "TAX_currency_condition", "HS_code", "customs_tariff_rate", "price_elasticity", "cost_standard_flag", "AR_lead_time", "AP_lead_time", "PSI_graph_flag", "buffering_stock_flag"]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _build_tree_rows(mosd: dict[str, Any], bound: str) -> tuple[list[dict[str, Any]], list[str]]:
    products = {p.get("product_name"): p for p in mosd.get("products", []) if isinstance(p, dict)}
    weeks_year = mosd.get("planning_horizon", {}).get("weeks_per_year", 52)
    rows, defaults = [], []
    for edge in mosd.get("product_plan_edges", []):
        if not isinstance(edge, dict) or str(edge.get("bound", "")).upper() != bound:
            continue
        product = products.get(edge.get("product_name"), {})
        lot = edge.get("lot_size", product.get("lot_size", ""))
        if lot == "":
            lot, defaults = 1, defaults + [f"{bound} edge {edge.get('parent_node')}->{edge.get('child_node')}: lot_size defaulted to 1"]
        rows.append({"Product_name": edge.get("product_name", ""), "Parent_node": edge.get("parent_node", ""), "Child_node": edge.get("child_node", ""), "child_node_name": edge.get("child_node_name") or edge.get("child_node", ""), "lot_size": lot, "leadtime": edge.get("leadtime_days", 0), "process_capa": edge.get("process_capa", 0), "long_vacation_weeks": edge.get("long_vacation_weeks", ""), "LT_boat": edge.get("LT_boat", ""), "LT_air": edge.get("LT_air", ""), "LT_qourier": edge.get("LT_qourier", ""), "weeks_year": weeks_year, "SS_days": edge.get("ss_days", 0), "TAX_currency_condition": "", "HS_code": "", "customs_tariff_rate": 0, "price_elasticity": "", "cost_standard_flag": "", "AR_lead_time": "", "AP_lead_time": "", "PSI_graph_flag": edge.get("psi_graph_flag", True), "buffering_stock_flag": edge.get("buffering_stock_flag", False)})
    return rows, defaults


def _build_sku_month_rows(mosd: dict[str, Any], bucket: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int], dict[int, float]] = defaultdict(dict)
    for q in mosd.get("quantity_profiles", []):
        if not isinstance(q, dict) or q.get("bucket") != bucket:
            continue
        grouped[(q.get("product_name", ""), q.get("node_name", ""), int(q.get("year", 2028)))][int(q.get("month", 1))] = float(q.get("quantity", 0))
    rows = []
    for (product_name, node_name, year), month_map in sorted(grouped.items()):
        row: dict[str, Any] = {"product_name": product_name, "node_name": node_name, "year": year}
        for m in range(1, 13):
            row[f"m{m}"] = month_map.get(m, 0)
        rows.append(row)
    return rows


def _build_money_rows(mosd: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], list[str], list[dict[str, Any]]]:
    currencies = {mosd.get("reporting_currency", "USD")}
    currencies |= {r.get("from_currency") for r in mosd.get("currencies", {}).get("fx_rates", []) if isinstance(r, dict)}
    currencies |= {r.get("to_currency") for r in mosd.get("currencies", {}).get("fx_rates", []) if isinstance(r, dict)}
    currency = next((c for c in currencies if c), "USD")
    products = {p.get("product_name"): p for p in mosd.get("products", []) if isinstance(p, dict)}
    nodes = {n.get("node_name"): n for n in mosd.get("physical_nodes", []) if isinstance(n, dict)}
    node_product = mosd.get("money_overlay", {}).get("node_product_values", []) or []
    product_cost_map = {r.get("product_name"): r for r in mosd.get("cost_assumptions", {}).get("product_costs", []) if isinstance(r, dict)}
    sales_prices = mosd.get("cost_assumptions", {}).get("sales_prices", []) or []
    mapping = mosd.get("node_market_mapping", []) or []

    if not node_product:
        for nn, nd in nodes.items():
            if nd.get("node_character") in {"SUPPLY_CHAIN_OFFICE", "MOM", "DAD", "CS"}:
                for pn, prod in products.items():
                    pc = product_cost_map.get(pn, {})
                    sp = next((s for s in sales_prices if s.get("product_name") == pn and any(m.get("node_name")==nn and m.get("market_id")==s.get("market_id") for m in mapping if isinstance(m, dict))), {})
                    inv = prod.get("inventory_unit_value", 0)
                    var = rev = 0
                    if nd.get("node_character") == "MOM":
                        inv = float(pc.get("standard_material_cost", 0)) + float(pc.get("standard_production_cost", 0))
                        var = inv
                    elif nd.get("node_character") == "DAD":
                        inv = prod.get("inventory_unit_value") or float(pc.get("base_sales_price", 0)) * 0.6
                    elif nd.get("node_character") == "CS":
                        rev = float(sp.get("sales_price", 0))
                        inv = 0
                    node_product.append({"node_name": nn, "product_name": pn, "inventory_unit_value": inv, "revenue_unit_value": rev, "variable_cost_unit_value": var, "fixed_cost_weekly": 0, "currency": currency, "remarks": "derived placeholder"})

    nchar_rows = [
        {"node_character": "SUPPLY_CHAIN_OFFICE", "revenue_items": "", "variable_cost_items": "", "fixed_cost_items": "fixed_cost_weekly", "inventory_value_items": "inventory_unit_value", "tax_compare_items": ""},
        {"node_character": "MOM", "revenue_items": "", "variable_cost_items": "variable_cost_unit_value", "fixed_cost_items": "fixed_cost_weekly", "inventory_value_items": "inventory_unit_value", "tax_compare_items": ""},
        {"node_character": "DAD", "revenue_items": "", "variable_cost_items": "variable_cost_unit_value", "fixed_cost_items": "fixed_cost_weekly", "inventory_value_items": "inventory_unit_value", "tax_compare_items": ""},
        {"node_character": "CS", "revenue_items": "revenue_unit_value", "variable_cost_items": "", "fixed_cost_items": "", "inventory_value_items": "", "tax_compare_items": ""},
        {"node_character": "WS", "revenue_items": "", "variable_cost_items": "", "fixed_cost_items": "", "inventory_value_items": "", "tax_compare_items": ""},
        {"node_character": "RT", "revenue_items": "", "variable_cost_items": "", "fixed_cost_items": "", "inventory_value_items": "", "tax_compare_items": ""},
        {"node_character": "SUPPLIER", "revenue_items": "", "variable_cost_items": "", "fixed_cost_items": "", "inventory_value_items": "", "tax_compare_items": ""},
        {"node_character": "MARKET", "revenue_items": "", "variable_cost_items": "", "fixed_cost_items": "", "inventory_value_items": "", "tax_compare_items": ""},
        {"node_character": "CONSUMER", "revenue_items": "", "variable_cost_items": "", "fixed_cost_items": "", "inventory_value_items": "", "tax_compare_items": ""},
    ]
    np_rows = [{"node_name": r.get("node_name", ""), "product_name": r.get("product_name", ""), "inventory_unit_value": r.get("inventory_unit_value", 0), "revenue_unit_value": r.get("revenue_unit_value", 0), "variable_cost_unit_value": r.get("variable_cost_unit_value", 0), "fixed_cost_weekly": r.get("fixed_cost_weekly", 0), "currency": r.get("currency", currency), "remarks": r.get("remarks", "")} for r in node_product if isinstance(r, dict)]

    rows = {
        "market_master": mosd.get("markets", []), "cs_node_to_market_map": mosd.get("node_market_mapping", []),
        "product_cost_master": mosd.get("cost_assumptions", {}).get("product_costs", []), "node_cost_master": mosd.get("cost_assumptions", {}).get("node_costs", []),
        "lane_cost_master": mosd.get("cost_assumptions", {}).get("lane_costs", []), "sales_price_master": mosd.get("cost_assumptions", {}).get("sales_prices", []),
        "fx_rate_master": mosd.get("currencies", {}).get("fx_rates", []), "node_product_money_master": np_rows, "node_character_money_master": nchar_rows,
    }
    assumption_rows = []
    for section, items in (("money_overlay.node_product_values", node_product), ("markets", rows["market_master"]), ("node_market_mapping", rows["cs_node_to_market_map"]), ("cost_assumptions.product_costs", rows["product_cost_master"]), ("cost_assumptions.node_costs", rows["node_cost_master"]), ("cost_assumptions.lane_costs", rows["lane_cost_master"]), ("cost_assumptions.sales_prices", rows["sales_price_master"]), ("currencies.fx_rates", rows["fx_rate_master"])):
        for item in items or []:
            if not isinstance(item, dict):
                continue
            key = item.get("node_name") or item.get("market_id") or item.get("product_name") or item.get("from_currency") or "row"
            st, conf = item.get("source_type", ""), item.get("confidence", "")
            hr = str(st == "navigator_assumption" or conf == "low").lower()
            assumption_rows.append({"section": section, "object_key": key, "field_name": "remarks", "value": item.get("remarks", ""), "source_type": st, "source_ref": item.get("source_ref", ""), "confidence": conf, "human_review_required": hr, "assumption_note": item.get("remarks", "")})
    return rows, ["money placeholders may require review"], assumption_rows


def generate_wom_masters(mosd_path: str, output_dir: str, *, overwrite: bool = False, include_money: bool = False) -> dict[str, Any]:
    mosd = load_mosd(mosd_path)
    messages = validate_mosd_schema(mosd)
    errors = [m for m in messages if m["level"] == "ERROR"]
    warnings = [m for m in messages if m["level"] == "WARNING"]
    summary = {"model_id": mosd.get("model_id", ""), "output_dir": str(Path(output_dir)), "generated_files": [], "errors": errors, "warnings": warnings, "human_review_required": bool(mosd.get("human_review_required", False) or warnings)}
    out = Path(output_dir)
    if out.exists() and not overwrite:
        raise FileExistsError(f"Output directory already exists: {out}")
    if out.exists() and overwrite:
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "validation_report.md").write_text("\n".join(["# Validation Report", "", "## ERROR", *([f"- [{m['code']}] {m['message']}" for m in errors] or ["- (none)"]), "", "## WARNING", *([f"- [{m['code']}] {m['message']}" for m in warnings] or ["- (none)"])]), encoding="utf-8")
    if errors:
        summary["generated_files"] = [str(out / "validation_report.md")]
        return summary

    _write_csv(out / "data/node_geo.csv", ["node_name", "lat", "lon"], [{"node_name": n.get("node_name", ""), "lat": n.get("lat", ""), "lon": n.get("lon", "")} for n in mosd.get("physical_nodes", []) if isinstance(n, dict)])
    _write_csv(out / "pysi/master_data/node_master.csv", ["node_name", "node_character", "display_name", "country", "company", "remarks"], [{"node_name": n.get("node_name", ""), "node_character": n.get("node_character") or n.get("role") or "UNKNOWN", "display_name": n.get("display_name") or n.get("node_name", ""), "country": n.get("country", ""), "company": n.get("company", ""), "remarks": n.get("remarks", "")} for n in mosd.get("physical_nodes", []) if isinstance(n, dict)])
    inbound_rows, defaults_in = _build_tree_rows(mosd, "IN")
    outbound_rows, defaults_out = _build_tree_rows(mosd, "OUT")
    _write_csv(out / "data/product_tree_inbound.csv", TREE_COLUMNS, inbound_rows)
    _write_csv(out / "data/product_tree_outbound.csv", TREE_COLUMNS, outbound_rows)
    sku_cols = ["product_name", "node_name", "year"] + [f"m{i}" for i in range(1, 13)]
    _write_csv(out / "data/sku_P_month_data.csv", sku_cols, _build_sku_month_rows(mosd, "P"))
    _write_csv(out / "data/sku_S_month_data.csv", sku_cols, _build_sku_month_rows(mosd, "S"))

    generated = ["data/node_geo.csv", "pysi/master_data/node_master.csv", "data/product_tree_inbound.csv", "data/product_tree_outbound.csv", "data/sku_P_month_data.csv", "data/sku_S_month_data.csv", "validation_report.md"]
    defaults = defaults_in + defaults_out
    if include_money:
        money_rows, money_defaults, assumption_rows = _build_money_rows(mosd)
        _write_csv(out / "pysi/master_data/node_character_money_master.csv", ["node_character", "revenue_items", "variable_cost_items", "fixed_cost_items", "inventory_value_items", "tax_compare_items"], money_rows["node_character_money_master"])
        _write_csv(out / "pysi/master_data/node_product_money_master.csv", ["node_name", "product_name", "inventory_unit_value", "revenue_unit_value", "variable_cost_unit_value", "fixed_cost_weekly", "currency", "remarks"], money_rows["node_product_money_master"])
        cost_dir = out / "data/cost_masters"
        _write_csv(cost_dir / "market_master.csv", ["market_id", "market_name", "country", "region", "channel", "segment", "priority_class", "service_policy", "price_policy", "currency", "active_flag", "remarks"], money_rows["market_master"])
        _write_csv(cost_dir / "cs_node_to_market_map.csv", ["node_name", "market_id", "product_name", "allocation_ratio", "priority_class", "service_policy", "price_policy", "valid_from_week", "valid_to_week", "scenario_name", "active_flag", "remarks"], money_rows["cs_node_to_market_map"])
        _write_csv(cost_dir / "product_cost_master.csv", ["product_name", "product_family", "base_sales_price", "standard_material_cost", "standard_production_cost", "purchase_cost", "inventory_unit_value", "currency", "scenario_name", "remarks"], money_rows["product_cost_master"])
        _write_csv(cost_dir / "node_cost_master.csv", ["node_name", "node_character", "direct_labor_cost_rate", "machine_cost_rate", "utility_cost_rate", "inventory_holding_cost_rate", "local_sga_fixed_cost", "local_sga_variable_cost_rate", "depreciation_cost_per_period", "capacity_cost_basis", "currency", "scenario_name", "remarks"], money_rows["node_cost_master"])
        _write_csv(cost_dir / "lane_cost_master.csv", ["from_node", "to_node", "transport_mode", "freight_cost_per_unit", "insurance_cost_per_unit", "tariff_rate", "customs_cost_per_unit", "lead_time_days", "special_risk_cost_rate", "currency", "scenario_name", "valid_from_week", "valid_to_week", "remarks"], money_rows["lane_cost_master"])
        _write_csv(cost_dir / "sales_price_master.csv", ["product_name", "market_id", "customer_segment", "sales_price", "rebate_rate", "promotion_cost_rate", "gross_to_net_adjustment", "expected_return_rate", "currency", "scenario_name", "valid_from_week", "valid_to_week", "remarks"], money_rows["sales_price_master"])
        _write_csv(cost_dir / "fx_rate_master.csv", ["scenario_name", "from_currency", "to_currency", "fx_rate", "rate_type", "valid_from_week", "valid_to_week", "source_type", "confidence", "remarks"], money_rows["fx_rate_master"])
        _write_csv(out / "source_assumption_register.csv", ["section", "object_key", "field_name", "value", "source_type", "source_ref", "confidence", "human_review_required", "assumption_note"], assumption_rows)
        defaults += money_defaults
        generated += ["pysi/master_data/node_character_money_master.csv", "pysi/master_data/node_product_money_master.csv", "data/cost_masters/market_master.csv", "data/cost_masters/cs_node_to_market_map.csv", "data/cost_masters/product_cost_master.csv", "data/cost_masters/node_cost_master.csv", "data/cost_masters/lane_cost_master.csv", "data/cost_masters/sales_price_master.csv", "data/cost_masters/fx_rate_master.csv", "source_assumption_register.csv"]

    generated += ["adapter_report.md"]
    summary["generated_files"] = [str(out / rel) for rel in generated]
    (out / "adapter_report.md").write_text("\n".join(["# MOSD Adapter Report", "", f"- model_id: {mosd.get('model_id','')}", f"- input_mosd: {mosd_path}", f"- output_dir: {output_dir}", f"- include_money: {include_money}", "", "## Generated files", *[f"- {g}" for g in generated], "", "## Money Master Generation", *( [f"- {g}" for g in generated if "cost_masters" in g or "money_master" in g or "source_assumption" in g] if include_money else ["- (not enabled)"] ), "", "## Human Review Required Money Assumptions", *( [f"- {d}" for d in defaults if 'money' in d or 'placeholder' in d] if include_money else ["- (none)"] )]), encoding="utf-8")
    return summary


def _main() -> int:
    p = argparse.ArgumentParser(description="Generate WOM master files from MOSD")
    p.add_argument("--mosd", required=True); p.add_argument("--output", required=True); p.add_argument("--overwrite", action="store_true"); p.add_argument("--include-money", action="store_true")
    a = p.parse_args(); summary = generate_wom_masters(a.mosd, a.output, overwrite=a.overwrite, include_money=a.include_money)
    print(json.dumps(summary, indent=2, ensure_ascii=False)); return 1 if summary.get("errors") else 0


if __name__ == "__main__":
    sys.exit(_main())
