from types import SimpleNamespace

from pysi.reporting.explicit_pipeline_capacity_report import ExplicitPipelineCapacityReport
from pysi.reporting.explicit_pipeline_issue_candidate_cost_kpi import ExplicitPipelineIssueCandidateKPIBundle
from pysi.reporting.explicit_pipeline_issue_candidates import ExplicitPipelineIssueCandidateBundle
from pysi.reporting.explicit_pipeline_reporting_flags import (
    maybe_run_explicit_pipeline_reporting_stack_from_env,
)
from tests.test_explicit_pipeline_issue_candidate_cost_kpi import _context


def _sample_report() -> ExplicitPipelineCapacityReport:
    return ExplicitPipelineCapacityReport(
        product_name="RICE",
        capacity_violation_records=[
            {
                "record_type": "capacity_violation",
                "product": "RICE",
                "node": "MOM_ASIA",
                "week": 10,
                "capacity_type": "P",
                "severity": "warning",
                "lot_ids": ["LOT_CAP_P"],
            }
        ],
        lot_exception_records=[
            {"record_type": "lot_exception", "exception_type": "blocked", "product": "RICE", "lot_id": "LOT_BLOCKED"}
        ],
        health_check_records=[],
        replan_candidate_records=[],
    )


def _sample_issue_bundle() -> ExplicitPipelineIssueCandidateBundle:
    return ExplicitPipelineIssueCandidateBundle(
        product_name="RICE",
        planning_issue_candidates=[{"issue_type": "blocked_lot", "product": "RICE", "node": "N1", "week": 1, "lot_ids": ["L1"]}],
        management_issue_candidates=[],
        replan_command_candidates=[],
        health_issue_candidates=[],
    )


def _sample_kpi_bundle() -> ExplicitPipelineIssueCandidateKPIBundle:
    return ExplicitPipelineIssueCandidateKPIBundle(
        product_name="RICE",
        enriched_planning_issue_candidates=[{"impact_status": "estimated", "estimated_total_business_impact": 1.0}],
        enriched_management_issue_candidates=[],
        enriched_replan_command_candidates=[],
        enriched_health_issue_candidates=[],
        summary={"currency": "JPY"},
        assumptions={"currency": "JPY"},
    )


def test_flag_off_noop(tmp_path):
    env = SimpleNamespace()
    results = maybe_run_explicit_pipeline_reporting_stack_from_env(env, output_root=tmp_path)

    assert all(value is None for value in results.values())
    assert env.explicit_bridge_capacity_reporting_stack_results == results
    assert list(tmp_path.iterdir()) == []
    assert not hasattr(env, "explicit_bridge_capacity_pipeline_report")
    assert not hasattr(env, "explicit_bridge_capacity_issue_candidates")
    assert not hasattr(env, "explicit_bridge_capacity_issue_candidate_kpi_bundle")


def test_report_only_from_pipeline_result():
    env = SimpleNamespace(
        enable_explicit_bridge_capacity_report=True,
        explicit_bridge_capacity_pipeline_result=SimpleNamespace(product_name="RICE", outbound_plan=[], inbound_plan=[], psi_dp_records=[], capacity_records=[], exceptions=[]),
    )
    results = maybe_run_explicit_pipeline_reporting_stack_from_env(env)

    assert results["capacity_report"] is not None
    assert env.explicit_bridge_capacity_pipeline_report is results["capacity_report"]
    assert results["capacity_report_export"] is None
    assert results["issue_candidates"] is None
    assert results["issue_candidate_cost_kpi"] is None


def test_report_export(tmp_path):
    env = SimpleNamespace(
        enable_explicit_bridge_capacity_report_export=True,
        explicit_bridge_capacity_pipeline_report=_sample_report(),
    )
    results = maybe_run_explicit_pipeline_reporting_stack_from_env(env, output_root=tmp_path)
    assert results["capacity_report_export"] is not None
    assert (tmp_path / "summary.json").exists()


def test_issue_candidates_only():
    env = SimpleNamespace(
        enable_explicit_bridge_capacity_issue_candidates=True,
        explicit_bridge_capacity_pipeline_report=_sample_report(),
    )
    results = maybe_run_explicit_pipeline_reporting_stack_from_env(env)
    assert results["issue_candidates"] is not None
    assert env.explicit_bridge_capacity_issue_candidates is results["issue_candidates"]
    assert results["issue_candidate_export"] is None


def test_issue_candidate_export(tmp_path):
    env = SimpleNamespace(
        enable_explicit_bridge_capacity_issue_candidate_export=True,
        explicit_bridge_capacity_issue_candidates=_sample_issue_bundle(),
    )
    results = maybe_run_explicit_pipeline_reporting_stack_from_env(env, output_root=tmp_path)
    assert results["issue_candidate_export"] is not None
    assert (tmp_path / "issue_candidates" / "summary.json").exists()


def test_cost_kpi_enrichment():
    env = SimpleNamespace(
        enable_explicit_bridge_capacity_issue_candidate_cost_kpi=True,
        explicit_bridge_capacity_issue_candidates=_sample_issue_bundle(),
    )
    results = maybe_run_explicit_pipeline_reporting_stack_from_env(env, cost_kpi_context=_context())
    assert results["issue_candidate_cost_kpi"] is not None
    assert env.explicit_bridge_capacity_issue_candidate_kpi_bundle is results["issue_candidate_cost_kpi"]
    assert "currency" in results["issue_candidate_cost_kpi"].summary


def test_cost_kpi_export(tmp_path):
    env = SimpleNamespace(
        enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export=True,
        explicit_bridge_capacity_issue_candidate_kpi_bundle=_sample_kpi_bundle(),
    )
    results = maybe_run_explicit_pipeline_reporting_stack_from_env(env, output_root=tmp_path)
    assert results["issue_candidate_cost_kpi_export"] is not None
    assert (tmp_path / "issue_candidate_kpi" / "summary.json").exists()
    assert (tmp_path / "issue_candidate_kpi" / "assumptions.json").exists()


def test_dependency_noop_child_flag_without_parent(tmp_path):
    env = SimpleNamespace(enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export=True)
    results = maybe_run_explicit_pipeline_reporting_stack_from_env(env, output_root=tmp_path)

    assert results["issue_candidate_cost_kpi_export"] is None
    assert list(tmp_path.iterdir()) == []


def test_output_root_override_routing(tmp_path):
    env = SimpleNamespace(
        enable_explicit_bridge_capacity_report_export=True,
        enable_explicit_bridge_capacity_issue_candidate_export=True,
        enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export=True,
        explicit_bridge_capacity_pipeline_report=_sample_report(),
        explicit_bridge_capacity_issue_candidates=_sample_issue_bundle(),
        explicit_bridge_capacity_issue_candidate_kpi_bundle=_sample_kpi_bundle(),
    )
    maybe_run_explicit_pipeline_reporting_stack_from_env(env, output_root=tmp_path)

    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "issue_candidates" / "summary.json").exists()
    assert (tmp_path / "issue_candidate_kpi" / "summary.json").exists()


def test_cost_context_precedence_argument_wins_over_env_context():
    env = SimpleNamespace(
        enable_explicit_bridge_capacity_issue_candidate_cost_kpi=True,
        explicit_bridge_capacity_issue_candidates=_sample_issue_bundle(),
        explicit_bridge_capacity_cost_kpi_context={"currency": "USD"},
    )
    maybe_run_explicit_pipeline_reporting_stack_from_env(env, cost_kpi_context={"currency": "EUR"})

    assert env.explicit_bridge_capacity_issue_candidate_kpi_bundle.summary["currency"] == "EUR"
