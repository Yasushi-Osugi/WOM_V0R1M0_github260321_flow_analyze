from dataclasses import dataclass, field

from pysi.plan.bridges.e2e_demand_to_supply_bridge_flow_smoke import run_e2e_demand_to_supply_bridge_flow_smoke
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


def test_e2e_happy_path_bridge_to_mom_capacity_to_supply():
    out_root, out_supply, in_root, in_supply, mom_asia, mom_euro = _roots(weeks=12)
    source_lots = [
        "RT_JP_RICE_2026W10_0001",
        "RT_JP_RICE_2026W10_0002",
        "RT_JP_RICE_2026W10_0003",
        "RT_DE_RICE_2026W10_0001",
    ]
    out_supply.psi4demand[10][PSI_P] = list(source_lots)
    outbound_snapshot = [bucket[:] for bucket in out_supply.psi4demand[10]]

    res = run_e2e_demand_to_supply_bridge_flow_smoke(
        outbound_root=out_root,
        inbound_root=in_root,
        product="RICE",
        mom_policy={"JP": ["MOM_ASIA"], "DE": ["MOM_EURO"], "DEFAULT": ["MOM_ASIA"]},
        weekly_capability={
            "RICE": {
                "MOM_ASIA": [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 0],
                "MOM_EURO": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0],
            }
        },
    )

    # Bridge A
    assert sorted(in_supply.psi4demand[10][PSI_S]) == sorted(source_lots)
    assert out_supply.psi4demand[10] == outbound_snapshot

    # MOM allocation
    assert sorted(mom_asia.psi4demand[10][PSI_S]) == sorted(source_lots[:3])
    assert mom_euro.psi4demand[10][PSI_S] == [source_lots[3]]

    # Capacity-aware planning (early build)
    assert len(mom_asia.psi4demand[10][PSI_P]) == 2
    assert len(mom_asia.psi4demand[9][PSI_P]) == 1
    assert len(mom_euro.psi4demand[10][PSI_P]) == 1
    assert res.shifted_lot_count == 1

    # Bridge B
    for mom in (mom_asia, mom_euro):
        for w in range(12):
            assert mom.psi4supply[w][PSI_S] == mom.psi4demand[w][PSI_S]
            assert mom.psi4supply[w][PSI_P] == mom.psi4demand[w][PSI_P]
            assert mom.psi4supply[w][PSI_CO] == []
            assert mom.psi4supply[w][PSI_I] == []

    # Lot_ID preservation + invariants
    assert res.missing_lot_ids == []
    assert res.non_list_bucket_errors == []
    assert res.non_string_lot_errors == []
    _all_buckets_string_lists(in_supply)
    _all_buckets_string_lists(mom_asia)
    _all_buckets_string_lists(mom_euro)


def test_e2e_backlog_lot_preserves_lot_id_when_capacity_insufficient():
    out_root, out_supply, in_root, _, mom_asia, _ = _roots(weeks=12)
    source_lots = ["RT_JP_RICE_2026W10_0001", "RT_JP_RICE_2026W10_0002"]
    out_supply.psi4demand[10][PSI_P] = list(source_lots)

    res = run_e2e_demand_to_supply_bridge_flow_smoke(
        outbound_root=out_root,
        inbound_root=in_root,
        product="RICE",
        mom_policy={"JP": ["MOM_ASIA"], "DEFAULT": ["MOM_ASIA"]},
        weekly_capability={"RICE": {"MOM_ASIA": {10: 1, 9: 0, 8: 0}}},
        max_early_build_weeks=2,
    )

    assert len(mom_asia.psi4demand[10][PSI_P]) == 1
    assert res.backlog_lot_count == 1
    assert len(res.missing_lot_ids) == 0
    assert len(mom_asia.psi4supply[10][PSI_P]) == 1
