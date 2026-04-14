"""Export reporting artifacts as JSON/CSV/Markdown."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


CSV_TABLES = [
    "product_report",
    "node_report",
    "market_report",
    "cost_waterfall",
    "pain_points",
    "allocation_breakdown",
]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_summary_md(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# WOM Business Report Summary",
        "",
        f"- Records: {report.get('meta', {}).get('record_count', 0)}",
        f"- Cost lines: {report.get('meta', {}).get('cost_line_count', 0)}",
        f"- Product rows: {len(report.get('product_report', []))}",
        f"- Node rows: {len(report.get('node_report', []))}",
        f"- Market rows: {len(report.get('market_report', []))}",
        f"- Allocation rows: {len(report.get('allocation_breakdown', []))}",
        "",
        "## Top Pain Points",
    ]
    for row in report.get("pain_points", [])[:5]:
        lines.append(f"- {row.get('pain_point')}: {row.get('value')}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_report_bundle(report: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    json_path = out / "business_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_paths: dict[str, str] = {}
    for table_name in CSV_TABLES:
        path = out / f"{table_name}.csv"
        _write_csv(path=path, rows=list(report.get(table_name, [])))
        csv_paths[table_name] = str(path)

    md_path = out / "summary.md"
    _write_summary_md(md_path, report)

    return {
        "json": str(json_path),
        "markdown": str(md_path),
        **csv_paths,
    }
