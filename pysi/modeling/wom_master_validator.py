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

    infos.append("Generated master validation completed")
    return {"errors": errors, "warnings": warnings, "infos": infos}
