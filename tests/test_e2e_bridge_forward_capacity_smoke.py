from dataclasses import dataclass, field

from pysi.plan.bridges.e2e_bridge_forward_capacity_smoke import run_e2e_bridge_forward_capacity_smoke
from pysi.plan.capacity_aware_inbound_backward import PSI_CO, PSI_I, PSI_P, PSI_S


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


def _all_buckets_string_lists(node):
    for layer in (node.psi4demand, node.psi4supply):
        for week in layer:
            for bucket in week:
                assert isinstance(bucket, list)
                assert all(isinstance(lot, str) for lot in bucket)


def test_e2e_bridge_forward_capacity_smoke_end_to_end():
    out_root, out_supply, in_root, in_supply, mom_asia, mom_euro = _roots(weeks=12)
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

    result = run_e2e_bridge_forward_capacity_smoke(
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

    assert sorted(in_supply.psi4demand[10][PSI_S]) == sorted(source_lots)
    assert sorted(mom_asia.psi4demand[10][PSI_S]) == sorted(source_lots[:3])
    assert mom_euro.psi4demand[10][PSI_S] == [source_lots[3]]

    assert len(mom_asia.psi4demand[10][PSI_P]) == 2
    assert len(mom_asia.psi4demand[9][PSI_P]) == 1
    assert len(mom_euro.psi4demand[10][PSI_P]) == 1

    # Bridge B copies demand/S,P into supply/S,P before forward execution.
    # After forward, supply/P and supply/S may be reduced by blocking rules, so check subset relation.
    for mom in (mom_asia, mom_euro):
        for w in range(12):
            assert set(mom.psi4supply[w][PSI_S]).issubset(set(mom.psi4demand[w][PSI_S]))
            assert set(mom.psi4supply[w][PSI_P]).issubset(set(mom.psi4demand[w][PSI_P]))
            assert mom.psi4supply[w][PSI_CO] == []

    assert result.forward_blocked_p_count == 1
    assert result.forward_accepted_p_count >= 3
    assert result.forward_blocked_s_count >= 1
    assert result.forward_accepted_s_count >= 1
    assert result.forward_overflow_i_count >= 1

    assert set(result.blocked_lot_ids).issuperset({"RT_JP_RICE_2026W10_0002"})
    assert "RT_JP_RICE_2026W10_0001" in set(result.overflow_i_lot_ids)
    assert result.missing_lot_ids == []
    assert result.non_list_bucket_errors == []
    assert result.non_string_lot_errors == []

    _all_buckets_string_lists(in_supply)
    _all_buckets_string_lists(mom_asia)
    _all_buckets_string_lists(mom_euro)
