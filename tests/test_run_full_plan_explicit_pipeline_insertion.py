from types import SimpleNamespace

import pytest

from pysi.plan.explicit_bridge_capacity_pipeline import (
    maybe_run_explicit_bridge_capacity_pipeline_from_env,
)
from tests.test_explicit_bridge_capacity_pipeline_feature_flag import _happy_ctx


def test_flag_off_default_is_noop_and_no_env_result():
    ctx = _happy_ctx()
    env = SimpleNamespace(enable_explicit_bridge_capacity_pipeline=False)
    result = maybe_run_explicit_bridge_capacity_pipeline_from_env(
        env=env,
        outbound_root=ctx["explicit_pipeline_outbound_root"],
        inbound_root=ctx["explicit_pipeline_inbound_root"],
        product=ctx["explicit_pipeline_product"],
        mom_policy=ctx["explicit_pipeline_mom_policy"],
        backward_weekly_capability=ctx["explicit_pipeline_backward_weekly_capability"],
        forward_weekly_capacity=ctx["explicit_pipeline_forward_weekly_capacity"],
    )
    assert result is None
    assert not hasattr(env, "explicit_bridge_capacity_pipeline_result")


def test_flag_on_result_attached_to_env():
    ctx = _happy_ctx()
    env = SimpleNamespace(enable_explicit_bridge_capacity_pipeline=True)
    result = maybe_run_explicit_bridge_capacity_pipeline_from_env(
        env=env,
        outbound_root=ctx["explicit_pipeline_outbound_root"],
        inbound_root=ctx["explicit_pipeline_inbound_root"],
        product=ctx["explicit_pipeline_product"],
        mom_policy=ctx["explicit_pipeline_mom_policy"],
        backward_weekly_capability=ctx["explicit_pipeline_backward_weekly_capability"],
        forward_weekly_capacity=ctx["explicit_pipeline_forward_weekly_capacity"],
    )
    assert result is env.explicit_bridge_capacity_pipeline_result
    assert result.missing_lot_ids == []
    assert result.non_list_bucket_errors == []
    assert result.non_string_lot_errors == []


def test_flag_on_missing_required_key_raises_value_error():
    ctx = _happy_ctx()
    env = SimpleNamespace(enable_explicit_bridge_capacity_pipeline=True)
    with pytest.raises(ValueError, match="explicit_pipeline_outbound_root"):
        maybe_run_explicit_bridge_capacity_pipeline_from_env(
            env=env,
            outbound_root=None,
            inbound_root=ctx["explicit_pipeline_inbound_root"],
            product=ctx["explicit_pipeline_product"],
            mom_policy=ctx["explicit_pipeline_mom_policy"],
            backward_weekly_capability=ctx["explicit_pipeline_backward_weekly_capability"],
            forward_weekly_capacity=ctx["explicit_pipeline_forward_weekly_capacity"],
        )
