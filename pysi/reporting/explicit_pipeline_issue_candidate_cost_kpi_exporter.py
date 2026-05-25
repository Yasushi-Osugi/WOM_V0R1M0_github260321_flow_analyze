from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .explicit_pipeline_issue_candidate_cost_kpi import (
    ExplicitPipelineIssueCandidateKPIBundle,
    issue_candidate_kpi_bundle_as_rows,
    issue_candidate_kpi_bundle_to_dict,
)


@dataclass
class ExplicitPipelineIssueCandidateKPIExportResult:
    output_dir: Path
    files: dict[str, Path] = field(default_factory=dict)
    record_counts: dict[str, int] = field(default_factory=dict)
    summary_path: Path | None = None
    assumptions_path: Path | None = None
    message: str = ""


_DEFAULT_COLUMNS: dict[str, list[str]] = {
    "enriched_planning_issues": [
        "candidate_type", "issue_type", "severity", "product", "node", "week", "capacity_type", "lot_ids",
        "impact_status", "impact_category", "impact_quantity", "impact_quantity_basis", "currency",
        "estimated_lost_sales_value", "estimated_margin_impact", "estimated_inventory_cost_impact",
        "estimated_capacity_cost_impact", "estimated_service_penalty", "estimated_total_business_impact",
        "kpi_service_risk_score", "kpi_inventory_risk_score", "kpi_capacity_risk_score",
        "kpi_data_quality_risk_score", "cost_kpi_assumption_source", "evidence_record_type", "source",
        "message", "suggested_action",
    ],
    "enriched_management_issues": [
        "candidate_type", "issue_type", "severity", "product", "node", "week", "capacity_type", "lot_ids",
        "business_theme", "impact_status", "impact_category", "impact_quantity", "impact_quantity_basis",
        "currency", "estimated_lost_sales_value", "estimated_margin_impact", "estimated_inventory_cost_impact",
        "estimated_capacity_cost_impact", "estimated_service_penalty", "estimated_total_business_impact",
        "kpi_service_risk_score", "kpi_inventory_risk_score", "kpi_capacity_risk_score",
        "kpi_data_quality_risk_score", "cost_kpi_assumption_source", "evidence_record_type", "source",
        "message", "suggested_decision",
    ],
    "enriched_replan_command_candidates": [
        "candidate_type", "command_type", "status", "product", "node", "week", "capacity_type", "lot_ids",
        "impact_status", "impact_category", "impact_quantity", "impact_quantity_basis", "currency",
        "estimated_total_business_impact", "expected_benefit_category", "source", "message", "suggested_action",
    ],
    "enriched_health_issues": [
        "candidate_type", "issue_type", "severity", "product", "details", "impact_status", "impact_category",
        "currency", "kpi_data_quality_risk_score", "estimated_total_business_impact", "evidence_record_type",
        "source", "message",
    ],
    "all_enriched_issue_candidates": [
        "candidate_type", "issue_type", "severity", "product", "node", "week", "capacity_type", "lot_ids",
        "impact_status", "impact_category", "currency", "estimated_total_business_impact", "source", "message",
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
            writer.writerow({column: _jsonable_value(row.get(column)) for column in columns})


def export_explicit_pipeline_issue_candidate_kpi_bundle(
    bundle: ExplicitPipelineIssueCandidateKPIBundle,
    *,
    output_dir: str | Path = "outputs/explicit_pipeline/issue_candidate_kpi",
    write_empty_files: bool = True,
    write_all_candidates: bool = True,
    write_bundle_json: bool = False,
) -> ExplicitPipelineIssueCandidateKPIExportResult:
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    all_rows = issue_candidate_kpi_bundle_as_rows(bundle)
    record_counts = {
        "enriched_planning_issues": len(bundle.enriched_planning_issue_candidates),
        "enriched_management_issues": len(bundle.enriched_management_issue_candidates),
        "enriched_replan_command_candidates": len(bundle.enriched_replan_command_candidates),
        "enriched_health_issues": len(bundle.enriched_health_issue_candidates),
        "all_enriched_issue_candidates": len(all_rows),
    }

    result = ExplicitPipelineIssueCandidateKPIExportResult(output_dir=output_dir_path, record_counts=record_counts)

    groups = [
        ("enriched_planning_issues", "enriched_planning_issues.csv", bundle.enriched_planning_issue_candidates),
        ("enriched_management_issues", "enriched_management_issues.csv", bundle.enriched_management_issue_candidates),
        (
            "enriched_replan_command_candidates",
            "enriched_replan_command_candidates.csv",
            bundle.enriched_replan_command_candidates,
        ),
        ("enriched_health_issues", "enriched_health_issues.csv", bundle.enriched_health_issue_candidates),
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

    assumptions_path = output_dir_path / "assumptions.json"
    with assumptions_path.open("w", encoding="utf-8") as f:
        json.dump(bundle.assumptions, f, ensure_ascii=False, indent=2, default=str)
    result.assumptions_path = assumptions_path
    result.files["assumptions"] = assumptions_path

    if write_all_candidates and (all_rows or write_empty_files):
        all_path = output_dir_path / "all_enriched_issue_candidates.csv"
        _write_csv(all_path, all_rows, _DEFAULT_COLUMNS["all_enriched_issue_candidates"])
        result.files["all_enriched_issue_candidates"] = all_path

    if write_bundle_json:
        bundle_json_path = output_dir_path / "issue_candidate_kpi_bundle.json"
        with bundle_json_path.open("w", encoding="utf-8") as f:
            json.dump(issue_candidate_kpi_bundle_to_dict(bundle), f, ensure_ascii=False, indent=2, default=str)
        result.files["bundle_json"] = bundle_json_path

    result.message = f"Exported explicit pipeline issue candidate KPI bundle to {output_dir_path}"
    return result


def maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env(
    env,
    *,
    output_dir: str | Path = "outputs/explicit_pipeline/issue_candidate_kpi",
    write_empty_files: bool = True,
    write_all_candidates: bool = True,
    write_bundle_json: bool = False,
):
    bundle = getattr(env, "explicit_bridge_capacity_issue_candidate_kpi_bundle", None)
    if bundle is None:
        return None

    result = export_explicit_pipeline_issue_candidate_kpi_bundle(
        bundle,
        output_dir=output_dir,
        write_empty_files=write_empty_files,
        write_all_candidates=write_all_candidates,
        write_bundle_json=write_bundle_json,
    )
    setattr(env, "explicit_bridge_capacity_issue_candidate_kpi_export_result", result)
    return result
