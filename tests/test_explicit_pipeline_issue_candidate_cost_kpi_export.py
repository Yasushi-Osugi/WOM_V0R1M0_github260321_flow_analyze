import csv
import json
from types import SimpleNamespace

from pysi.reporting.explicit_pipeline_issue_candidate_cost_kpi import ExplicitPipelineIssueCandidateKPIBundle
from pysi.reporting.explicit_pipeline_issue_candidate_cost_kpi_exporter import (
    export_explicit_pipeline_issue_candidate_kpi_bundle,
    maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env,
)


def _bundle() -> ExplicitPipelineIssueCandidateKPIBundle:
    return ExplicitPipelineIssueCandidateKPIBundle(
        product_name="A",
        enriched_planning_issue_candidates=[{
            "candidate_type": "planning_issue",
            "issue_type": "capacity_violation",
            "severity": "high",
            "product": "A",
            "node": "N1",
            "week": 1,
            "capacity_type": "P",
            "lot_ids": ["L1", "L2"],
            "impact_status": "estimated",
            "impact_category": "capacity_risk",
            "estimated_total_business_impact": 100.0,
            "source": "explicit_pipeline",
            "message": "planning",
            "suggested_action": "review",
        }],
        enriched_management_issue_candidates=[{
            "candidate_type": "management_issue",
            "issue_type": "capacity_bottleneck",
            "severity": "high",
            "product": "A",
            "node": "N1",
            "week": 1,
            "capacity_type": "P",
            "lot_ids": ["M1"],
            "business_theme": "throughput",
            "impact_status": "estimated",
            "impact_category": "capacity_risk",
            "estimated_total_business_impact": 200.0,
            "source": "explicit_pipeline",
            "message": "management",
            "suggested_decision": "approve",
        }],
        enriched_replan_command_candidates=[{
            "candidate_type": "replan_command_candidate",
            "command_type": "rebalance",
            "status": "candidate_only",
            "product": "A",
            "node": "N1",
            "week": 1,
            "capacity_type": "P",
            "lot_ids": ["R1"],
            "impact_status": "qualitative_only",
            "impact_category": "replan_option",
            "estimated_total_business_impact": 0.0,
            "expected_benefit_category": "reduce_capacity_risk",
            "source": "explicit_pipeline",
            "message": "replan",
            "suggested_action": "consider",
        }],
        enriched_health_issue_candidates=[{
            "candidate_type": "health_issue",
            "issue_type": "missing_data",
            "severity": "medium",
            "product": "A",
            "details": "missing field",
            "impact_status": "qualitative_only",
            "impact_category": "data_quality_risk",
            "currency": "USD",
            "kpi_data_quality_risk_score": "high",
            "estimated_total_business_impact": 0.0,
            "source": "explicit_pipeline",
            "message": "health",
        }],
        summary={
            "product": "A",
            "currency": "USD",
            "estimated_total_business_impact": 300.0,
            "impact_values_are_directional": True,
            "double_counting_possible": True,
        },
        assumptions={
            "currency": "USD",
            "unit_price_by_product": {"A": 10},
            "capacity_shortage_penalty_per_lot": {"P": 30},
        },
    )


def test_export_synthetic_kpi_bundle(tmp_path):
    result = export_explicit_pipeline_issue_candidate_kpi_bundle(_bundle(), output_dir=tmp_path)
    for name in [
        "enriched_planning_issues.csv",
        "enriched_management_issues.csv",
        "enriched_replan_command_candidates.csv",
        "enriched_health_issues.csv",
        "summary.json",
        "assumptions.json",
        "all_enriched_issue_candidates.csv",
    ]:
        assert (tmp_path / name).exists()

    assert result.output_dir == tmp_path
    assert result.files
    assert result.record_counts["all_enriched_issue_candidates"] == 4
    assert result.summary_path == tmp_path / "summary.json"
    assert result.assumptions_path == tmp_path / "assumptions.json"

    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["product"] == "A"
    assert summary["currency"] == "USD"
    assert "estimated_total_business_impact" in summary
    assert summary["impact_values_are_directional"] is True
    assert summary["double_counting_possible"] is True

    assumptions = json.loads((tmp_path / "assumptions.json").read_text(encoding="utf-8"))
    assert assumptions["currency"] == "USD"
    assert "unit_price_by_product" in assumptions
    assert "capacity_shortage_penalty_per_lot" in assumptions


def test_csv_content(tmp_path):
    export_explicit_pipeline_issue_candidate_kpi_bundle(_bundle(), output_dir=tmp_path)

    with (tmp_path / "enriched_planning_issues.csv").open(encoding="utf-8") as f:
        planning_rows = list(csv.DictReader(f))
    assert planning_rows
    assert planning_rows[0]["lot_ids"] == '["L1", "L2"]'
    assert planning_rows[0]["estimated_total_business_impact"] == "100.0"

    with (tmp_path / "enriched_management_issues.csv").open(encoding="utf-8") as f:
        management_rows = list(csv.DictReader(f))
    assert management_rows

    with (tmp_path / "enriched_replan_command_candidates.csv").open(encoding="utf-8") as f:
        replan_rows = list(csv.DictReader(f))
    assert replan_rows[0]["status"] == "candidate_only"

    with (tmp_path / "all_enriched_issue_candidates.csv").open(encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))
    assert len(all_rows) == 4


def test_empty_bundle_write_empty_files_true(tmp_path):
    empty_bundle = ExplicitPipelineIssueCandidateKPIBundle(summary={}, assumptions={})
    result = export_explicit_pipeline_issue_candidate_kpi_bundle(
        empty_bundle,
        output_dir=tmp_path,
        write_empty_files=True,
    )
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "assumptions.json").exists()
    assert (tmp_path / "enriched_planning_issues.csv").exists()
    assert result.record_counts["all_enriched_issue_candidates"] == 0


def test_empty_bundle_write_empty_files_false(tmp_path):
    empty_bundle = ExplicitPipelineIssueCandidateKPIBundle(summary={}, assumptions={})
    export_explicit_pipeline_issue_candidate_kpi_bundle(
        empty_bundle,
        output_dir=tmp_path,
        write_empty_files=False,
    )
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "assumptions.json").exists()
    assert not (tmp_path / "enriched_planning_issues.csv").exists()


def test_env_helper_noop(tmp_path):
    env = SimpleNamespace()
    result = maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env(env, output_dir=tmp_path)
    assert result is None
    assert not tmp_path.exists() or not any(tmp_path.iterdir())


def test_env_helper_attaches_result(tmp_path):
    env = SimpleNamespace(explicit_bridge_capacity_issue_candidate_kpi_bundle=_bundle())
    result = maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env(env, output_dir=tmp_path)
    assert result is not None
    assert hasattr(env, "explicit_bridge_capacity_issue_candidate_kpi_export_result")


def test_optional_bundle_json(tmp_path):
    export_explicit_pipeline_issue_candidate_kpi_bundle(
        _bundle(),
        output_dir=tmp_path,
        write_bundle_json=True,
    )
    assert (tmp_path / "issue_candidate_kpi_bundle.json").exists()
