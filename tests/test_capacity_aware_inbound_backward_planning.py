from dataclasses import dataclass, field

from pysi.plan.capacity_aware_inbound_backward import (
    PSI_P,
    PSI_S,
    capacity_aware_inbound_backward_planning,
)


@dataclass
class MockPlanNode:
    name: str
    children: list = field(default_factory=list)
    psi4demand: list = field(default_factory=list)
    psi4supply: list = field(default_factory=list)
    nx_capacity: int | None = None


def _node(name: str, weeks: int = 16, nx_capacity: int | None = None) -> MockPlanNode:
    return MockPlanNode(
        name=name,
        children=[],
        psi4demand=[[[], [], [], []] for _ in range(weeks)],
        psi4supply=[[[], [], [], []] for _ in range(weeks)],
        nx_capacity=nx_capacity,
    )


def test_basic_s_to_p_capacity_within_limit_and_invariants():
    root = _node("supply_point", weeks=16)
    mom = _node("MOM_ASIA", weeks=16)
    root.children = [mom]

    mom.psi4demand[10][PSI_S] = ["LOT_A", "LOT_B"]
    supply_before = [[bucket[:] for bucket in week] for week in mom.psi4supply]

    result = capacity_aware_inbound_backward_planning(
        in_root=root,
        product="RICE",
        weekly_capability={"RICE": {"MOM_ASIA": {10: 2}}},
    )

    assert mom.psi4demand[10][PSI_P] == ["LOT_A", "LOT_B"]
    assert result.shifted_lot_count == 0
    assert result.backlog_lot_count == 0
    assert mom.psi4supply == supply_before
    for week in mom.psi4demand:
        for bucket in week:
            assert isinstance(bucket, list)
            assert all(isinstance(lot, str) for lot in bucket)


def test_overflow_shifts_earlier_and_no_secondary_mom_reassignment():
    root = _node("supply_point", weeks=16)
    mom_asia = _node("MOM_ASIA", weeks=16)
    mom_euro = _node("MOM_EURO", weeks=16)
    root.children = [mom_asia, mom_euro]

    mom_asia.psi4demand[10][PSI_S] = ["LOT_1", "LOT_2", "LOT_3"]

    result = capacity_aware_inbound_backward_planning(
        in_root=root,
        product="RICE",
        weekly_capability={"RICE": {"MOM_ASIA": {10: 2, 9: 2}, "MOM_EURO": {10: 100, 9: 100}}},
    )

    assert len(mom_asia.psi4demand[10][PSI_P]) == 2
    assert len(mom_asia.psi4demand[9][PSI_P]) == 1
    assert mom_euro.psi4demand[10][PSI_P] == []
    assert mom_euro.psi4demand[9][PSI_P] == []
    assert result.shifted_lot_count == 1
    assert result.backlog_lot_count == 0


def test_backlog_when_no_earlier_capacity_and_mom_prefix_discovery():
    top = _node("in_root", weeks=16)
    supply = _node("supply_point", weeks=16)
    mom = _node("MOM_ASIA", weeks=16)
    supply.children = [mom]
    top.children = [supply]

    mom.psi4demand[10][PSI_S] = ["LOT_X", "LOT_Y"]

    result = capacity_aware_inbound_backward_planning(
        in_root=top,
        product="RICE",
        weekly_capability={"RICE": {"MOM_ASIA": {10: 1, 9: 0, 8: 0}}},
        max_early_build_weeks=2,
    )

    assert len(mom.psi4demand[10][PSI_P]) == 1
    assert result.backlog_lot_count == 1
    assert result.backlog_lots[0]["lot_id"] in {"LOT_X", "LOT_Y"}
    assert result.backlog_lots[0]["assigned_mom"] == "MOM_ASIA"
