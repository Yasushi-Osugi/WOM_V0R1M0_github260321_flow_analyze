from dataclasses import dataclass, field

from pysi.plan.capacity_aware_inbound_backward import PSI_I, PSI_P
from pysi.plan.explicit_bridge_capacity_pipeline import (
    ExplicitBridgeCapacityPipelineResult,
    run_explicit_bridge_capacity_pipeline,
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

    return out_root, out_supply, in_root, in_supply, mom_asia, mom_euro


def _run_pipeline():
    out_root, out_supply, in_root, _, mom_asia, _ = _roots(weeks=12)
    source_lots = [
        "RT_JP_RICE_2026W10_0001",
        "RT_JP_RICE_2026W10_0002",
        "RT_JP_RICE_2026W10_0003",
        "RT_DE_RICE_2026W10_0001",
    ]
    out_supply.psi4demand[10][PSI_P] = list(source_lots)
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

    result = run_explicit_bridge_capacity_pipeline(
        outbound_root=out_root,
        inbound_root=in_root,
        product="RICE",
        mom_policy={"JP": ["MOM_ASIA"], "DE": ["MOM_EURO"], "DEFAULT": ["MOM_ASIA"]},
        backward_weekly_capability={
            "RICE": {
                "MOM_ASIA": [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 0],
                "MOM_EURO": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0],
            }
        },
        forward_weekly_capacity=forward_weekly_capacity,
        cap_i_mode="soft",
    )
    return result


def test_explicit_pipeline_happy_path_and_invariants():
    result = _run_pipeline()

    assert isinstance(result, ExplicitBridgeCapacityPipelineResult)
    assert result.product_name == "RICE"
    assert result.missing_lot_ids == []
    assert result.non_list_bucket_errors == []
    assert result.non_string_lot_errors == []


def test_explicit_pipeline_surfaces_blocked_lots():
    result = _run_pipeline()

    assert result.blocked_lot_ids


def test_explicit_pipeline_surfaces_overflow_i_lots():
    result = _run_pipeline()

    # MVP expectation: overflow lots are available through wrapped smoke result output.
    assert result.overflow_i_lot_ids
