from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .explicit_pipeline_issue_candidates import (
    ExplicitPipelineIssueCandidateBundle,
    issue_candidates_as_rows,
    issue_candidates_to_dict,
)


@dataclass
class ExplicitPipelineIssueCandidateExportResult:
    output_dir: Path
    files: dict[str, Path] = field(default_factory=dict)
    record_counts: dict[str, int] = field(default_factory=dict)
    summary_path: Path | None = None
    message: str = ""


_DEFAULT_COLUMNS: dict[str, list[str]] = {
    "planning_issues": [
        "candidate_type",
        "issue_type",
        "severity",
        "product",
        "node",
        "week",
        "capacity_type",
        "lot_ids",
        "evidence_record_type",
        "source",
        "message",
        "suggested_action",
    ],
    "management_issues": [
        "candidate_type",
        "issue_type",
        "severity",
        "product",
        "node",
        "week",
        "capacity_type",
        "lot_ids",
        "business_theme",
        "evidence_record_type",
        "source",
        "message",
        "suggested_decision",
    ],
    "replan_command_candidates": [
        "candidate_type",
        "command_type",
        "status",
        "product",
        "node",
        "week",
        "capacity_type",
        "lot_ids",
        "source",
        "message",
        "suggested_action",
    ],
    "health_issues": [
        "candidate_type",
        "issue_type",
        "severity",
        "product",
        "details",
        "evidence_record_type",
        "source",
        "message",
    ],
    "all_issue_candidates": [
        "candidate_type",
        "issue_type",
        "severity",
        "product",
        "node",
        "week",
        "capacity_type",
        "lot_ids",
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


def export_explicit_pipeline_issue_candidates(
    bundle: ExplicitPipelineIssueCandidateBundle,
    *,
    output_dir: str | Path = "outputs/explicit_pipeline/issue_candidates",
    write_empty_files: bool = True,
    write_all_candidates: bool = True,
    write_bundle_json: bool = False,
) -> ExplicitPipelineIssueCandidateExportResult:
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    all_candidates = issue_candidates_as_rows(bundle)
    record_counts = {
        "planning_issues": len(bundle.planning_issue_candidates),
        "management_issues": len(bundle.management_issue_candidates),
        "replan_command_candidates": len(bundle.replan_command_candidates),
        "health_issues": len(bundle.health_issue_candidates),
        "all_issue_candidates": len(all_candidates),
    }

    result = ExplicitPipelineIssueCandidateExportResult(
        output_dir=output_dir_path,
        record_counts=record_counts,
    )

    groups = [
        ("planning_issues", "planning_issues.csv", bundle.planning_issue_candidates),
        ("management_issues", "management_issues.csv", bundle.management_issue_candidates),
        (
            "replan_command_candidates",
            "replan_command_candidates.csv",
            bundle.replan_command_candidates,
        ),
        ("health_issues", "health_issues.csv", bundle.health_issue_candidates),
    ]

    for group_key, filename, rows in groups:
        if rows or write_empty_files:
            path = output_dir_path / filename
            _write_csv(path, rows, _DEFAULT_COLUMNS[group_key])
            result.files[group_key] = path

    summary_path = output_dir_path / "summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(bundle.summary, f, ensure_ascii=False, indent=2, default=str)
    result.summary_path = summary_path
    result.files["summary"] = summary_path

    if write_all_candidates and (all_candidates or write_empty_files):
        all_candidates_path = output_dir_path / "all_issue_candidates.csv"
        _write_csv(all_candidates_path, all_candidates, _DEFAULT_COLUMNS["all_issue_candidates"])
        result.files["all_issue_candidates"] = all_candidates_path

    if write_bundle_json:
        bundle_json_path = output_dir_path / "issue_candidate_bundle.json"
        with bundle_json_path.open("w", encoding="utf-8") as f:
            json.dump(issue_candidates_to_dict(bundle), f, ensure_ascii=False, indent=2, default=str)
        result.files["bundle_json"] = bundle_json_path

    result.message = f"Exported explicit pipeline issue candidates to {output_dir_path}"
    return result


def maybe_export_explicit_pipeline_issue_candidates_from_env(
    env,
    *,
    output_dir: str | Path = "outputs/explicit_pipeline/issue_candidates",
    write_empty_files: bool = True,
    write_all_candidates: bool = True,
    write_bundle_json: bool = False,
):
    bundle = getattr(env, "explicit_bridge_capacity_issue_candidates", None)
    if bundle is None:
        return None

    result = export_explicit_pipeline_issue_candidates(
        bundle,
        output_dir=output_dir,
        write_empty_files=write_empty_files,
        write_all_candidates=write_all_candidates,
        write_bundle_json=write_bundle_json,
    )
    setattr(env, "explicit_bridge_capacity_issue_candidate_export_result", result)
    return result
