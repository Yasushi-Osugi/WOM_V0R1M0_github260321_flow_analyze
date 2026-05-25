from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .explicit_pipeline_capacity_report import (
    ExplicitPipelineCapacityReport,
    report_records_as_rows,
    report_to_dict,
)


@dataclass
class ExplicitPipelineCapacityReportExportResult:
    output_dir: Path
    files: dict[str, Path] = field(default_factory=dict)
    record_counts: dict[str, int] = field(default_factory=dict)
    summary_path: Path | None = None
    message: str = ""


_DEFAULT_COLUMNS: dict[str, list[str]] = {
    "capacity_usage": [
        "record_type",
        "product",
        "node",
        "week",
        "capacity_type",
        "capacity",
        "used",
        "remaining",
        "utilization_ratio",
        "source",
        "message",
        "lot_ids",
    ],
    "capacity_violations": [
        "record_type",
        "product",
        "node",
        "week",
        "capacity_type",
        "severity",
        "capacity",
        "requested",
        "overflow",
        "lot_ids",
        "source",
        "message",
    ],
    "lot_exceptions": [
        "record_type",
        "exception_type",
        "product",
        "lot_id",
        "node",
        "week",
        "source",
        "message",
    ],
    "replan_candidates": [
        "record_type",
        "command_type",
        "product",
        "node",
        "week",
        "capacity_type",
        "lot_ids",
        "suggested_action",
        "source",
        "message",
    ],
    "health_checks": [
        "record_type",
        "check_type",
        "severity",
        "count",
        "details",
        "source",
        "message",
    ],
    "all_records": [
        "record_type",
        "product",
        "node",
        "week",
        "capacity_type",
        "lot_id",
        "lot_ids",
        "severity",
        "source",
        "message",
    ],
}


def _jsonable_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _columns_for_rows(rows: list[dict[str, Any]], default_columns: list[str]) -> list[str]:
    if not rows:
        return list(default_columns)

    keys = set(default_columns)
    for row in rows:
        keys.update(row.keys())
    return sorted(keys)


def _write_csv(path: Path, rows: list[dict[str, Any]], default_columns: list[str]) -> None:
    columns = _columns_for_rows(rows, default_columns)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            normalized = {column: _jsonable_value(row.get(column)) for column in columns}
            writer.writerow(normalized)


def export_explicit_pipeline_capacity_report(
    report: ExplicitPipelineCapacityReport,
    *,
    output_dir: str | Path = "outputs/explicit_pipeline",
    write_empty_files: bool = True,
    write_all_records: bool = True,
    write_report_json: bool = False,
) -> ExplicitPipelineCapacityReportExportResult:
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    all_records = report_records_as_rows(report)
    record_counts = {
        "capacity_usage": len(report.capacity_usage_records),
        "capacity_violations": len(report.capacity_violation_records),
        "lot_exceptions": len(report.lot_exception_records),
        "replan_candidates": len(report.replan_candidate_records),
        "health_checks": len(report.health_check_records),
        "all_records": len(all_records),
    }

    result = ExplicitPipelineCapacityReportExportResult(
        output_dir=output_dir_path,
        record_counts=record_counts,
    )

    groups = [
        ("capacity_usage", "capacity_usage.csv", report.capacity_usage_records),
        ("capacity_violations", "capacity_violations.csv", report.capacity_violation_records),
        ("lot_exceptions", "lot_exceptions.csv", report.lot_exception_records),
        ("replan_candidates", "replan_candidates.csv", report.replan_candidate_records),
        ("health_checks", "health_checks.csv", report.health_check_records),
    ]

    for group_key, filename, rows in groups:
        if rows or write_empty_files:
            path = output_dir_path / filename
            _write_csv(path, rows, _DEFAULT_COLUMNS[group_key])
            result.files[group_key] = path

    summary_path = output_dir_path / "summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(report.summary, f, ensure_ascii=False, indent=2)
    result.summary_path = summary_path
    result.files["summary"] = summary_path

    if write_all_records and (all_records or write_empty_files):
        all_records_path = output_dir_path / "all_records.csv"
        _write_csv(all_records_path, all_records, _DEFAULT_COLUMNS["all_records"])
        result.files["all_records"] = all_records_path

    if write_report_json:
        report_json_path = output_dir_path / "report.json"
        with report_json_path.open("w", encoding="utf-8") as f:
            json.dump(report_to_dict(report), f, ensure_ascii=False, indent=2, default=str)
        result.files["report_json"] = report_json_path

    result.message = f"Exported explicit pipeline capacity report to {output_dir_path}"
    return result


def maybe_export_explicit_pipeline_capacity_report_from_env(
    env,
    *,
    output_dir: str | Path = "outputs/explicit_pipeline",
    write_empty_files: bool = True,
    write_all_records: bool = True,
    write_report_json: bool = False,
):
    report = getattr(env, "explicit_bridge_capacity_pipeline_report", None)
    if report is None:
        return None

    result = export_explicit_pipeline_capacity_report(
        report,
        output_dir=output_dir,
        write_empty_files=write_empty_files,
        write_all_records=write_all_records,
        write_report_json=write_report_json,
    )
    setattr(env, "explicit_bridge_capacity_pipeline_report_export_result", result)
    return result
