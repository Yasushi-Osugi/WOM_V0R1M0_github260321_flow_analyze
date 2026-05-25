from dataclasses import dataclass, field

import pytest

from pysi.plan.capacity_aware_inbound_backward import PSI_I, PSI_P
from pysi.plan.explicit_bridge_capacity_pipeline import (
    maybe_run_explicit_bridge_capacity_pipeline,
)


@dataclass
class MockPlanNode:
    name: str
    children: list = field(default_factory=list)
    psi4demand: list = field(default_factory=list)
    psi4supply: list = field(default_factory=list)


def _node(name: str, weeks: int = 16) -> MockPlanNode:
    return MockPlanNode(
        name=name,
        children=[],
        psi4demand=[[[], [], [], []] for _ in range(weeks)],
        psi4supply=[[[], [], [], []] for _ in range(weeks)],
    )


def _roots(weeks: int = 12):
    out_root = _node("out_root", weeks)
    out_supply = _node("supply_point", weeks)
    out_root.children = [out_supply]

    in_root = _node("in_root", weeks)
    in_supply = _node("supply_point", weeks)
    mom_asia = _node("MOM_ASIA", weeks)
    mom_euro = _node("MOM_EURO", weeks)
    in_supply.children = [mom_asia, mom_euro]
    in_root.children = [in_supply]

    return out_root, out_supply, in_root, mom_asia


def _happy_ctx():
    out_root, out_supply, in_root, mom_asia = _roots(weeks=12)
    out_supply.psi4demand[10][PSI_P] = [
        "RT_JP_RICE_2026W10_0001",
        "RT_JP_RICE_2026W10_0002",
        "RT_JP_RICE_2026W10_0003",
        "RT_DE_RICE_2026W10_0001",
    ]
    mom_asia.psi4supply[10][PSI_I] = ["RT_JP_RICE_2026W09_INV01"]

    forward_weekly_capacity = {
        "RICE": {
            "MOM_ASIA": {"P": [999] * 12, "S": [999] * 12, "I": [999] * 12},
            "MOM_EURO": {"P": [999] * 12, "S": [999] * 12, "I": [999] * 12},
        }
    }
    forward_weekly_capacity["RICE"]["MOM_ASIA"]["P"][10] = 1
    forward_weekly_capacity["RICE"]["MOM_ASIA"]["S"][10] = 0
    forward_weekly_capacity["RICE"]["MOM_ASIA"]["I"][10] = 0

    return {
        "enable_explicit_bridge_capacity_pipeline": True,
        "explicit_pipeline_outbound_root": out_root,
        "explicit_pipeline_inbound_root": in_root,
        "explicit_pipeline_product": "RICE",
        "explicit_pipeline_mom_policy": {
            "JP": ["MOM_ASIA"],
            "DE": ["MOM_EURO"],
            "DEFAULT": ["MOM_ASIA"],
        },
        "explicit_pipeline_backward_weekly_capability": {
            "RICE": {
                "MOM_ASIA": [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 0],
                "MOM_EURO": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0],
            }
        },
        "explicit_pipeline_forward_weekly_capacity": forward_weekly_capacity,
    }


def test_maybe_run_flag_missing_is_noop():
    ctx = {}
    result = maybe_run_explicit_bridge_capacity_pipeline(ctx)
    assert result is None
    assert "explicit_bridge_capacity_pipeline_result" not in ctx


def test_maybe_run_flag_false_is_noop():
    ctx = {"enable_explicit_bridge_capacity_pipeline": False}
    result = maybe_run_explicit_bridge_capacity_pipeline(ctx)
    assert result is None
    assert "explicit_bridge_capacity_pipeline_result" not in ctx


def test_maybe_run_flag_true_happy_path_sets_ctx_result():
    ctx = _happy_ctx()

    result = maybe_run_explicit_bridge_capacity_pipeline(ctx)

    assert result is not None
    assert ctx["explicit_bridge_capacity_pipeline_result"] is result
    assert result.missing_lot_ids == []
    assert result.non_list_bucket_errors == []
    assert result.non_string_lot_errors == []


def test_maybe_run_flag_true_missing_required_key_raises_value_error():
    ctx = {"enable_explicit_bridge_capacity_pipeline": True}

    with pytest.raises(ValueError, match="explicit_pipeline_outbound_root"):
        maybe_run_explicit_bridge_capacity_pipeline(ctx)
