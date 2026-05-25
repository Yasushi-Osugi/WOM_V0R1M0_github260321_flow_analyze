from types import SimpleNamespace

import pytest

from pysi.plan.explicit_bridge_capacity_pipeline import (
    maybe_run_explicit_bridge_capacity_pipeline_from_env,
)
from pysi.reporting.explicit_pipeline_capacity_report import (
    ExplicitPipelineCapacityReport,
    maybe_build_explicit_pipeline_capacity_report_from_env,
)
from tests.test_explicit_bridge_capacity_pipeline_feature_flag import _happy_ctx


def _run_pipeline_then_attach_report(env, ctx):
    explicit_result = maybe_run_explicit_bridge_capacity_pipeline_from_env(
        env=env,
        outbound_root=ctx.get("explicit_pipeline_outbound_root"),
        inbound_root=ctx.get("explicit_pipeline_inbound_root"),
        product=ctx.get("explicit_pipeline_product"),
        mom_policy=ctx.get("explicit_pipeline_mom_policy"),
        backward_weekly_capability=ctx.get("explicit_pipeline_backward_weekly_capability"),
        forward_weekly_capacity=ctx.get("explicit_pipeline_forward_weekly_capacity"),
    )
    if explicit_result is not None:
        maybe_build_explicit_pipeline_capacity_report_from_env(env)
    return explicit_result


def test_flag_off_does_not_attach_result_or_report():
    ctx = _happy_ctx()
    env = SimpleNamespace(enable_explicit_bridge_capacity_pipeline=False)

    explicit_result = _run_pipeline_then_attach_report(env, ctx)

    assert explicit_result is None
    assert not hasattr(env, "explicit_bridge_capacity_pipeline_result")
    assert not hasattr(env, "explicit_bridge_capacity_pipeline_report")


def test_flag_on_attaches_result_and_report():
    ctx = _happy_ctx()
    env = SimpleNamespace(enable_explicit_bridge_capacity_pipeline=True)

    explicit_result = _run_pipeline_then_attach_report(env, ctx)

    assert explicit_result is env.explicit_bridge_capacity_pipeline_result
    assert hasattr(env, "explicit_bridge_capacity_pipeline_report")
    report = env.explicit_bridge_capacity_pipeline_report
    assert isinstance(report, ExplicitPipelineCapacityReport)
    assert isinstance(report.summary, dict)


def test_flag_on_missing_required_input_raises_and_does_not_attach_report():
    ctx = _happy_ctx()
    env = SimpleNamespace(enable_explicit_bridge_capacity_pipeline=True)

    with pytest.raises(ValueError, match="explicit_pipeline_outbound_root"):
        _run_pipeline_then_attach_report(
            env,
            {
                **ctx,
                "explicit_pipeline_outbound_root": None,
            },
        )

    assert not hasattr(env, "explicit_bridge_capacity_pipeline_report")
