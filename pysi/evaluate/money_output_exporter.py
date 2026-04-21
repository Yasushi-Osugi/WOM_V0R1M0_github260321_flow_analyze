from __future__ import annotations

import csv
import os
from typing import Any, Dict, List


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
) -> Dict[str, str]:
    node_path = os.path.join(output_dir, "node_money_eval.csv")
    kpi_path = os.path.join(output_dir, "kpi_summary.csv")
    product_path = os.path.join(output_dir, "product_money_summary.csv")

    _write_csv(node_path, node_money_rows)
    _write_csv(kpi_path, kpi_summary_rows)
    _write_csv(product_path, product_money_summary_rows)

    return {
        "node_money_eval_csv": node_path,
        "kpi_summary_csv": kpi_path,
        "product_money_summary_csv": product_path,
    }
