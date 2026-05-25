from __future__ import annotations

from pathlib import Path
from typing import Any

from .explicit_pipeline_capacity_report import maybe_build_explicit_pipeline_capacity_report_from_env
from .explicit_pipeline_capacity_report_exporter import maybe_export_explicit_pipeline_capacity_report_from_env
from .explicit_pipeline_issue_candidate_cost_kpi import (
    maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env,
)
from .explicit_pipeline_issue_candidate_cost_kpi_exporter import (
    maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env,
)
from .explicit_pipeline_issue_candidate_exporter import maybe_export_explicit_pipeline_issue_candidates_from_env
from .explicit_pipeline_issue_candidates import maybe_build_explicit_pipeline_issue_candidates_from_env


_DEFAULT_OUTPUT_ROOT = Path("outputs/explicit_pipeline")


def maybe_run_explicit_pipeline_reporting_stack_from_env(
    env,
    *,
    output_root: str | Path | None = None,
    cost_kpi_context: dict | None = None,
) -> dict[str, Any]:
    root = Path(output_root) if output_root is not None else _DEFAULT_OUTPUT_ROOT
    selected_cost_kpi_context = (
        cost_kpi_context
        if cost_kpi_context is not None
        else getattr(env, "explicit_bridge_capacity_cost_kpi_context", None)
    )
    if selected_cost_kpi_context is None:
        selected_cost_kpi_context = {}

    results: dict[str, Any] = {
        "capacity_report": None,
        "capacity_report_export": None,
        "issue_candidates": None,
        "issue_candidate_export": None,
        "issue_candidate_cost_kpi": None,
        "issue_candidate_cost_kpi_export": None,
    }

    if getattr(env, "enable_explicit_bridge_capacity_report", False):
        results["capacity_report"] = maybe_build_explicit_pipeline_capacity_report_from_env(env)

    if getattr(env, "enable_explicit_bridge_capacity_report_export", False):
        results["capacity_report_export"] = maybe_export_explicit_pipeline_capacity_report_from_env(
            env,
            output_dir=root,
        )

    if getattr(env, "enable_explicit_bridge_capacity_issue_candidates", False):
        results["issue_candidates"] = maybe_build_explicit_pipeline_issue_candidates_from_env(env)

    if getattr(env, "enable_explicit_bridge_capacity_issue_candidate_export", False):
        results["issue_candidate_export"] = maybe_export_explicit_pipeline_issue_candidates_from_env(
            env,
            output_dir=root / "issue_candidates",
        )

    if getattr(env, "enable_explicit_bridge_capacity_issue_candidate_cost_kpi", False):
        results["issue_candidate_cost_kpi"] = maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env(
            env,
            cost_kpi_context=selected_cost_kpi_context,
        )

    if getattr(env, "enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export", False):
        results["issue_candidate_cost_kpi_export"] = maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env(
            env,
            output_dir=root / "issue_candidate_kpi",
        )

    setattr(env, "explicit_bridge_capacity_reporting_stack_results", results)
    return results
