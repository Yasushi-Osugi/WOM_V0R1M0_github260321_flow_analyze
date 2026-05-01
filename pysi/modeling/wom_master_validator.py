"""Validation for generated WOM phase-1 masters."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def validate_generated_masters(output_dir: str) -> dict[str, list[str]]:
    """Validate generated Phase 1 CSV files."""
    out = Path(output_dir)
    errors: list[str] = []
    warnings: list[str] = []
    infos: list[str] = []

    required = {
        "data/node_geo.csv": ["node_name", "lat", "lon"],
        "data/product_tree_inbound.csv": ["Product_name", "Parent_node", "Child_node", "lot_size", "leadtime"],
        "data/product_tree_outbound.csv": ["Product_name", "Parent_node", "Child_node", "lot_size", "leadtime"],
        "data/sku_P_month_data.csv": ["product_name", "node_name", "year", "m1", "m12"],
        "data/sku_S_month_data.csv": ["product_name", "node_name", "year", "m1", "m12"],
        "pysi/master_data/node_master.csv": ["node_name", "node_character", "display_name", "country", "company", "remarks"],
    }

    for rel, cols in required.items():
        p = out / rel
        if not p.exists():
            errors.append(f"Missing required file: {rel}")
            continue
        rows = _read_csv(p)
        hdr = rows[0].keys() if rows else []
        for col in cols:
            if col not in hdr:
                errors.append(f"Missing column {col} in {rel}")

    if errors:
        return {"errors": errors, "warnings": warnings, "infos": infos}

    node_rows = _read_csv(out / "pysi/master_data/node_master.csv")
    node_names = [r["node_name"] for r in node_rows]
    if len(set(node_names)) != len(node_names):
        errors.append("node_master node_name must be unique")
    if node_names.count("supply_point") != 1:
        errors.append("supply_point must exist exactly once in node_master")

    node_set = set(node_names)
    in_rows = _read_csv(out / "data/product_tree_inbound.csv")
    out_rows = _read_csv(out / "data/product_tree_outbound.csv")
    all_tree = in_rows + out_rows
    product_set = {r["Product_name"] for r in all_tree}
    for r in all_tree:
        for key in ("Parent_node", "Child_node"):
            val = r[key]
            if val != "root" and val not in node_set:
                errors.append(f"Tree node {val} not found in node_master")
        for key in ("lot_size", "leadtime"):
            val = r.get(key, "")
            if val != "":
                num = float(val)
                if key == "lot_size" and num <= 0:
                    errors.append("lot_size must be > 0 in product tree")
                if key == "leadtime" and num < 0:
                    errors.append("leadtime must be >= 0 in product tree")

    for rel in ("data/sku_P_month_data.csv", "data/sku_S_month_data.csv"):
        rows = _read_csv(out / rel)
        for r in rows:
            if r["node_name"] not in node_set:
                errors.append(f"{rel} node not found in node_master: {r['node_name']}")
            if r["product_name"] not in product_set:
                warnings.append(f"{rel} product not found in product trees: {r['product_name']}")



    # optional phase2 validation
    npm = out / "pysi/master_data/node_product_money_master.csv"
    ncm = out / "pysi/master_data/node_character_money_master.csv"
    if npm.exists():
        rows=_read_csv(npm)
        req={"node_name","product_name","inventory_unit_value","revenue_unit_value","variable_cost_unit_value","fixed_cost_weekly","currency","remarks"}
        if rows and not req.issubset(set(rows[0].keys())): errors.append("node_product_money_master required columns missing")
        for r in rows:
            if r["node_name"] not in node_set: errors.append(f"node_product_money_master node missing: {r['node_name']}")
            if r["product_name"] not in product_set: errors.append(f"node_product_money_master product missing: {r['product_name']}")
            for k in ("inventory_unit_value","revenue_unit_value","variable_cost_unit_value","fixed_cost_weekly"):
                if float(r.get(k,0))<0: errors.append(f"node_product_money_master {k} must be >=0")
    if ncm.exists():
        rows=_read_csv(ncm); chars={r.get("node_character","") for r in rows}
        for r in node_rows:
            c=r.get("node_character","")
            if c and c!="UNKNOWN" and c not in chars: errors.append(f"node_character missing in node_character_money_master: {c}")

    mm=out/"data/cost_masters/market_master.csv"
    if mm.exists():
        mk=_read_csv(mm); mids=[r.get("market_id","") for r in mk]; mset=set(mids)
        if len(mids)!=len(mset): errors.append("market_master market_id must be unique")
        csm=out/"data/cost_masters/cs_node_to_market_map.csv"
        if csm.exists():
            for r in _read_csv(csm):
                if r.get("market_id") not in mset: errors.append("cs_node_to_market_map market_id missing")
                if r.get("node_name") not in node_set: errors.append("cs_node_to_market_map node missing")
        sp=out/"data/cost_masters/sales_price_master.csv"
        if sp.exists():
            for r in _read_csv(sp):
                if r.get("market_id") not in mset: errors.append("sales_price_master market_id missing")
    for rel,key in (("data/cost_masters/product_cost_master.csv","product_name"),("data/cost_masters/node_cost_master.csv","node_name")):
        p=out/rel
        if p.exists():
            for r in _read_csv(p):
                if key=="product_name" and r.get(key) not in product_set: errors.append("product_cost_master product missing")
                if key=="node_name" and r.get(key) not in node_set: errors.append("node_cost_master node missing")
    lc=out/"data/cost_masters/lane_cost_master.csv"
    if lc.exists():
        for r in _read_csv(lc):
            if r.get("from_node") not in node_set or r.get("to_node") not in node_set: errors.append("lane_cost_master node missing")
    fx=out/"data/cost_masters/fx_rate_master.csv"
    if fx.exists():
        for r in _read_csv(fx):
            if float(r.get("fx_rate",0))<=0: errors.append("fx_rate_master fx_rate must be >0")

    infos.append("Generated master validation completed")
    return {"errors": errors, "warnings": warnings, "infos": infos}
