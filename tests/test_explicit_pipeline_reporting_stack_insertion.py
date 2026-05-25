from types import SimpleNamespace

from pysi.reporting.explicit_pipeline_capacity_report import (
    ExplicitPipelineCapacityReport,
    maybe_build_explicit_pipeline_capacity_report_from_env,
)
from pysi.reporting.explicit_pipeline_reporting_flags import (
    maybe_run_explicit_pipeline_reporting_stack_from_env,
)
from tests.test_explicit_pipeline_issue_candidate_cost_kpi import _context


def _simulate_reporting_stack_insertion(env, explicit_result):
    if explicit_result is not None:
        maybe_build_explicit_pipeline_capacity_report_from_env(env)
        return maybe_run_explicit_pipeline_reporting_stack_from_env(
            env,
            output_root=getattr(env, "explicit_bridge_capacity_reporting_output_root", None),
            cost_kpi_context=getattr(env, "explicit_bridge_capacity_cost_kpi_context", None),
        )
    return None


def _sample_pipeline_result():
    return SimpleNamespace(
        product_name="RICE",
        outbound_plan=[],
        inbound_plan=[],
        psi_dp_records=[],
        capacity_records=[],
        exceptions=[],
    )


def test_no_explicit_result_returns_none_and_does_not_attach_results(monkeypatch):
    env = SimpleNamespace()

    called = {"reporting": False}

    def _never_call(*args, **kwargs):
        called["reporting"] = True
        return {}

    monkeypatch.setattr(
        "pysi.reporting.explicit_pipeline_reporting_flags.maybe_run_explicit_pipeline_reporting_stack_from_env",
        _never_call,
    )

    results = _simulate_reporting_stack_insertion(env, explicit_result=None)

    assert results is None
    assert called["reporting"] is False
    assert not hasattr(env, "explicit_bridge_capacity_reporting_stack_results")


def test_explicit_result_all_flags_off_no_exports(tmp_path):
    env = SimpleNamespace(
        explicit_bridge_capacity_pipeline_result=_sample_pipeline_result(),
        explicit_bridge_capacity_reporting_output_root=tmp_path,
    )

    results = _simulate_reporting_stack_insertion(env, explicit_result=env.explicit_bridge_capacity_pipeline_result)

    assert results is not None
    assert all(value is None for value in results.values())
    assert env.explicit_bridge_capacity_reporting_stack_results == results
    assert list(tmp_path.iterdir()) == []


def test_report_flag_enabled_attaches_report():
    env = SimpleNamespace(
        enable_explicit_bridge_capacity_report=True,
        explicit_bridge_capacity_pipeline_result=_sample_pipeline_result(),
    )

    results = _simulate_reporting_stack_insertion(env, explicit_result=env.explicit_bridge_capacity_pipeline_result)

    assert isinstance(env.explicit_bridge_capacity_pipeline_report, ExplicitPipelineCapacityReport)
    assert results["capacity_report"] is env.explicit_bridge_capacity_pipeline_report


def test_issue_candidates_enabled_attaches_bundle():
    env = SimpleNamespace(
        enable_explicit_bridge_capacity_issue_candidates=True,
        explicit_bridge_capacity_pipeline_result=_sample_pipeline_result(),
    )

    results = _simulate_reporting_stack_insertion(env, explicit_result=env.explicit_bridge_capacity_pipeline_result)

    assert hasattr(env, "explicit_bridge_capacity_issue_candidates")
    assert results["issue_candidates"] is env.explicit_bridge_capacity_issue_candidates


def test_cost_kpi_enabled_uses_env_context():
    env = SimpleNamespace(
        enable_explicit_bridge_capacity_issue_candidates=True,
        enable_explicit_bridge_capacity_issue_candidate_cost_kpi=True,
        explicit_bridge_capacity_pipeline_result=_sample_pipeline_result(),
        explicit_bridge_capacity_cost_kpi_context=_context(),
    )

    results = _simulate_reporting_stack_insertion(env, explicit_result=env.explicit_bridge_capacity_pipeline_result)

    assert hasattr(env, "explicit_bridge_capacity_issue_candidate_kpi_bundle")
    assert results["issue_candidate_cost_kpi"] is env.explicit_bridge_capacity_issue_candidate_kpi_bundle


def test_export_flags_write_under_output_root(tmp_path):
    env = SimpleNamespace(
        enable_explicit_bridge_capacity_report=True,
        enable_explicit_bridge_capacity_report_export=True,
        enable_explicit_bridge_capacity_issue_candidates=True,
        enable_explicit_bridge_capacity_issue_candidate_export=True,
        enable_explicit_bridge_capacity_issue_candidate_cost_kpi=True,
        enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export=True,
        explicit_bridge_capacity_pipeline_result=_sample_pipeline_result(),
        explicit_bridge_capacity_reporting_output_root=tmp_path,
        explicit_bridge_capacity_cost_kpi_context=_context(),
    )

    _simulate_reporting_stack_insertion(env, explicit_result=env.explicit_bridge_capacity_pipeline_result)

    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "issue_candidates" / "summary.json").exists()
    assert (tmp_path / "issue_candidate_kpi" / "summary.json").exists()


def test_call_path_uses_env_output_root_and_env_cost_context():
    env = SimpleNamespace(
        enable_explicit_bridge_capacity_issue_candidates=True,
        enable_explicit_bridge_capacity_issue_candidate_cost_kpi=True,
        explicit_bridge_capacity_pipeline_result=_sample_pipeline_result(),
        explicit_bridge_capacity_reporting_output_root=None,
        explicit_bridge_capacity_cost_kpi_context={"currency": "EUR"},
    )

    _simulate_reporting_stack_insertion(env, explicit_result=env.explicit_bridge_capacity_pipeline_result)

    assert env.explicit_bridge_capacity_issue_candidate_kpi_bundle.summary["currency"] == "EUR"
