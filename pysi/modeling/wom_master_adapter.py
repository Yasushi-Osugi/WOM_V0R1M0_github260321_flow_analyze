"""MOSD to WOM master CSV adapter (Phase 1)."""

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

TREE_COLUMNS = [
    "Product_name", "Parent_node", "Child_node", "child_node_name", "lot_size", "leadtime", "process_capa",
    "long_vacation_weeks", "LT_boat", "LT_air", "LT_qourier", "weeks_year", "SS_days", "TAX_currency_condition",
    "HS_code", "customs_tariff_rate", "price_elasticity", "cost_standard_flag", "AR_lead_time", "AP_lead_time",
    "PSI_graph_flag", "buffering_stock_flag",
]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_tree_rows(mosd: dict[str, Any], bound: str) -> tuple[list[dict[str, Any]], list[str]]:
    products = {p.get("product_name"): p for p in mosd.get("products", []) if isinstance(p, dict)}
    weeks_year = mosd.get("planning_horizon", {}).get("weeks_per_year", 52)
    rows = []
    defaults: list[str] = []
    for edge in mosd.get("product_plan_edges", []):
        if not isinstance(edge, dict) or str(edge.get("bound", "")).upper() != bound:
            continue
        product = products.get(edge.get("product_name"), {})
        lot = edge.get("lot_size", product.get("lot_size", ""))
        if lot == "":
            lot = 1
            defaults.append(f"{bound} edge {edge.get('parent_node')}->{edge.get('child_node')}: lot_size defaulted to 1")
        rows.append({
            "Product_name": edge.get("product_name", ""),
            "Parent_node": edge.get("parent_node", ""),
            "Child_node": edge.get("child_node", ""),
            "child_node_name": edge.get("child_node_name") or edge.get("child_node", ""),
            "lot_size": lot,
            "leadtime": edge.get("leadtime_days", 0),
            "process_capa": edge.get("process_capa", 0),
            "long_vacation_weeks": edge.get("long_vacation_weeks", ""),
            "LT_boat": edge.get("LT_boat", ""),
            "LT_air": edge.get("LT_air", ""),
            "LT_qourier": edge.get("LT_qourier", ""),
            "weeks_year": weeks_year,
            "SS_days": edge.get("ss_days", 0),
            "TAX_currency_condition": "",
            "HS_code": "",
            "customs_tariff_rate": 0,
            "price_elasticity": "",
            "cost_standard_flag": "",
            "AR_lead_time": "",
            "AP_lead_time": "",
            "PSI_graph_flag": edge.get("psi_graph_flag", True),
            "buffering_stock_flag": edge.get("buffering_stock_flag", False),
        })
    return rows, defaults


def _build_sku_month_rows(mosd: dict[str, Any], bucket: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int], dict[int, float]] = defaultdict(dict)
    for q in mosd.get("quantity_profiles", []):
        if not isinstance(q, dict) or q.get("bucket") != bucket:
            continue
        key = (q.get("product_name", ""), q.get("node_name", ""), int(q.get("year", 2028)))
        grouped[key][int(q.get("month", 1))] = float(q.get("quantity", 0))

    rows = []
    for (product_name, node_name, year), month_map in sorted(grouped.items()):
        row: dict[str, Any] = {"product_name": product_name, "node_name": node_name, "year": year}
        for m in range(1, 13):
            row[f"m{m}"] = month_map.get(m, 0)
        rows.append(row)
    return rows


def generate_wom_masters(mosd_path: str, output_dir: str, *, overwrite: bool = False) -> dict[str, Any]:
    mosd = load_mosd(mosd_path)
    messages = validate_mosd_schema(mosd)
    errors = [m for m in messages if m["level"] == "ERROR"]
    warnings = [m for m in messages if m["level"] == "WARNING"]

    summary = {
        "model_id": mosd.get("model_id", ""),
        "output_dir": str(Path(output_dir)),
        "generated_files": [],
        "errors": errors,
        "warnings": warnings,
        "human_review_required": bool(mosd.get("human_review_required", False) or warnings),
    }

    out = Path(output_dir)
    if out.exists() and not overwrite:
        raise FileExistsError(f"Output directory already exists: {out}")
    if out.exists() and overwrite:
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    val_lines = {"ERROR": [], "WARNING": [], "INFO": []}
    for m in messages:
        val_lines[m["level"]].append(f"- [{m['code']}] {m['message']}")
    validation_text = "\n".join([
        "# Validation Report", "", "## ERROR", *(val_lines["ERROR"] or ["- (none)"]), "",
        "## WARNING", *(val_lines["WARNING"] or ["- (none)"]), "",
        "## INFO", *(val_lines["INFO"] or ["- (none)"]), "",
    ])
    (out / "validation_report.md").write_text(validation_text, encoding="utf-8")
    summary["generated_files"].append(str(out / "validation_report.md"))

    if errors:
        return summary

    nodes = mosd.get("physical_nodes", [])
    node_geo_rows = [{"node_name": n.get("node_name", ""), "lat": n.get("lat", ""), "lon": n.get("lon", "")} for n in nodes if isinstance(n, dict)]
    _write_csv(out / "data/node_geo.csv", ["node_name", "lat", "lon"], node_geo_rows)

    node_master_rows = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        remarks = n.get("remarks", "")
        if not remarks and (n.get("source_type") or n.get("confidence")):
            remarks = f"source_type={n.get('source_type','')}; confidence={n.get('confidence','')}"
        node_master_rows.append({
            "node_name": n.get("node_name", ""),
            "node_character": n.get("node_character") or n.get("role") or "UNKNOWN",
            "display_name": n.get("display_name") or n.get("node_name", ""),
            "country": n.get("country", ""),
            "company": n.get("company", ""),
            "remarks": remarks,
        })
    _write_csv(out / "pysi/master_data/node_master.csv", ["node_name", "node_character", "display_name", "country", "company", "remarks"], node_master_rows)

    inbound_rows, defaults_in = _build_tree_rows(mosd, "IN")
    outbound_rows, defaults_out = _build_tree_rows(mosd, "OUT")
    _write_csv(out / "data/product_tree_inbound.csv", TREE_COLUMNS, inbound_rows)
    _write_csv(out / "data/product_tree_outbound.csv", TREE_COLUMNS, outbound_rows)

    p_rows = _build_sku_month_rows(mosd, "P")
    s_rows = _build_sku_month_rows(mosd, "S")
    sku_cols = ["product_name", "node_name", "year"] + [f"m{i}" for i in range(1, 13)]
    _write_csv(out / "data/sku_P_month_data.csv", sku_cols, p_rows)
    _write_csv(out / "data/sku_S_month_data.csv", sku_cols, s_rows)

    generated = [
        "data/node_geo.csv", "pysi/master_data/node_master.csv", "data/product_tree_inbound.csv", "data/product_tree_outbound.csv",
        "data/sku_P_month_data.csv", "data/sku_S_month_data.csv", "adapter_report.md", "validation_report.md",
    ]
    summary["generated_files"] = [str(out / rel) for rel in generated]

    defaults = defaults_in + defaults_out
    adapter_report = "\n".join([
        "# MOSD Adapter Report", "", f"- model_id: {mosd.get('model_id','')}", f"- model_name: {mosd.get('model_name','')}",
        f"- input_mosd: {mosd_path}", f"- output_dir: {output_dir}", f"- human_review_required: {summary['human_review_required']}",
        "", "## Generated files", *[f"- {g}" for g in generated], "",
        f"## Validation summary\n- errors: {len(errors)}\n- warnings: {len(warnings)}", "",
        "## Defaults applied", *( [f"- {d}" for d in defaults] if defaults else ["- (none)"] ), "",
    ])
    (out / "adapter_report.md").write_text(adapter_report, encoding="utf-8")
    return summary


def _main() -> int:
    parser = argparse.ArgumentParser(description="Generate phase-1 WOM master files from MOSD")
    parser.add_argument("--mosd", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    summary = generate_wom_masters(args.mosd, args.output, overwrite=args.overwrite)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if summary.get("errors") else 0


if __name__ == "__main__":
    sys.exit(_main())
