from pathlib import Path
from types import SimpleNamespace

from pysi.gui.explicit_pipeline_management_cockpit_view import (
    build_explicit_pipeline_management_cockpit_view_model,
)


def test_no_data():
    vm = build_explicit_pipeline_management_cockpit_view_model(SimpleNamespace())
    assert vm["available"] is False
    assert all(v is False for v in vm["status"].values())
    assert vm["top_impact_issues"] == []
    assert any("No explicit pipeline reporting data is available" in x for x in vm["messages"])


def test_report_only():
    report = SimpleNamespace(summary={"capacity_usage_record_count": 3, "capacity_violation_record_count": 2, "has_warning": True})
    env = SimpleNamespace(explicit_bridge_capacity_pipeline_report=report)
    vm = build_explicit_pipeline_management_cockpit_view_model(env)
    assert vm["available"] is True
    assert vm["capacity_summary"]["available"] is True
    assert vm["capacity_summary"]["capacity_usage_record_count"] == 3
    assert vm["issue_summary"]["planning_issue_candidate_count"] == 0
    assert any("Cost / KPI enrichment is not available" in x for x in vm["messages"])


def test_issue_candidates_only():
    issue = SimpleNamespace(
        summary={"planning_issue_candidate_count": 1, "replan_command_candidate_count": 1},
        replan_command_candidates=[{"status": "candidate_only", "product": "A"}],
    )
    env = SimpleNamespace(explicit_bridge_capacity_issue_candidates=issue)
    vm = build_explicit_pipeline_management_cockpit_view_model(env)
    assert vm["issue_summary"]["planning_issue_candidate_count"] == 1
    assert len(vm["replan_candidates"]) == 1
    assert any("Cost / KPI enrichment is not available" in x for x in vm["messages"])


def test_kpi_bundle_top_impact_sorting_and_messages():
    kpi = SimpleNamespace(
        summary={"estimated_total_business_impact": 111, "estimated_margin_impact_total": 10},
        enriched_management_issue_candidates=[
            {"severity": "warning", "issue_type": "z", "node": "N2", "week": 2, "estimated_total_business_impact": 10},
            {"severity": "error", "issue_type": "a", "node": "N1", "week": 1, "estimated_total_business_impact": 30},
        ],
        enriched_planning_issue_candidates=[
            {"severity": "info", "issue_type": "b", "node": "N3", "week": 3, "estimated_total_business_impact": 20}
        ],
    )
    vm = build_explicit_pipeline_management_cockpit_view_model(SimpleNamespace(explicit_bridge_capacity_issue_candidate_kpi_bundle=kpi))
    assert vm["executive_kpi_summary"]["estimated_total_business_impact"] == 111.0
    impacts = [x["estimated_total_business_impact"] for x in vm["top_impact_issues"]]
    assert impacts == [30.0, 20.0, 10.0]
    assert vm["top_impact_issues"][0]["rank"] == 1
    assert any("directional scenario estimates" in x for x in vm["messages"])


def test_replan_candidate_remains_candidate_only():
    kpi = SimpleNamespace(enriched_replan_command_candidates=[{"status": "candidate_only", "command_type": "capacity_replan"}])
    vm = build_explicit_pipeline_management_cockpit_view_model(SimpleNamespace(explicit_bridge_capacity_issue_candidate_kpi_bundle=kpi))
    assert vm["replan_candidates"][0]["status"] == "candidate_only"


def test_assumption_summary():
    kpi = SimpleNamespace(
        assumptions={
            "currency": "USD",
            "unit_price_by_product": {"A": 1},
            "capacity_shortage_penalty_per_lot": {"P": 2},
            "service_penalty_per_lot": {"A": 3},
        }
    )
    vm = build_explicit_pipeline_management_cockpit_view_model(SimpleNamespace(explicit_bridge_capacity_issue_candidate_kpi_bundle=kpi))
    assert vm["assumption_summary"]["currency"] == "USD"
    assert vm["assumption_summary"]["unit_price_products"] == ["A"]
    assert vm["assumption_summary"]["capacity_shortage_penalty_types"] == ["P"]
    assert vm["assumption_summary"]["service_penalty_products"] == ["A"]


def test_export_summary():
    export = SimpleNamespace(
        output_dir=Path("/tmp/out"),
        files={"summary": Path("/tmp/out/summary.json")},
        record_counts={"a": 1},
        summary_path=Path("/tmp/out/summary.json"),
        assumptions_path=Path("/tmp/out/assumptions.json"),
        message="ok",
    )
    env = SimpleNamespace(
        explicit_bridge_capacity_pipeline_report_export_result=export,
        explicit_bridge_capacity_issue_candidate_export_result=export,
        explicit_bridge_capacity_issue_candidate_kpi_export_result=export,
    )
    vm = build_explicit_pipeline_management_cockpit_view_model(env)
    ex = vm["export_summary"]["cost_kpi_export"]
    assert ex["available"] is True
    assert ex["output_dir"] == "/tmp/out"
    assert ex["file_count"] == 1
    assert ex["record_counts"]["a"] == 1
    assert ex["summary_path"].endswith("summary.json")
    assert ex["assumptions_path"].endswith("assumptions.json")


def test_partial_data_safe_defaults():
    env = SimpleNamespace(explicit_bridge_capacity_pipeline_report=SimpleNamespace(summary=None), explicit_bridge_capacity_issue_candidates=SimpleNamespace())
    vm = build_explicit_pipeline_management_cockpit_view_model(env)
    assert isinstance(vm, dict)
    assert vm["capacity_summary"]["capacity_usage_record_count"] == 0
    assert vm["issue_summary"]["planning_issue_candidate_count"] == 0
