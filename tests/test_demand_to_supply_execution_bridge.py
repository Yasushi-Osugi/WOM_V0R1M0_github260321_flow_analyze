from dataclasses import dataclass, field

from pysi.plan.bridges.demand_to_supply_execution_bridge import bridge_demand_to_supply_execution


@dataclass
class MockPlanNode:
    name: str
    children: list = field(default_factory=list)
    psi4demand: list = field(default_factory=list)
    psi4supply: list = field(default_factory=list)


def _node(name: str, weeks: int = 4) -> MockPlanNode:
    return MockPlanNode(
        name=name,
        psi4demand=[[[], [], [], []] for _ in range(weeks)],
        psi4supply=[[[], [], [], []] for _ in range(weeks)],
    )


def test_s_p_only_basic_bridge():
    node = _node("mom")
    node.psi4demand[0][0] = ["S_LOT"]
    node.psi4demand[0][3] = ["P_LOT"]

    bridge_demand_to_supply_execution(root=node)

    assert node.psi4supply[0][0] == ["S_LOT"]
    assert node.psi4supply[0][3] == ["P_LOT"]
    assert node.psi4supply[0][1] == []
    assert node.psi4supply[0][2] == []


def test_source_demand_unchanged():
    node = _node("mom")
    node.psi4demand[0][0] = ["S_LOT"]
    node.psi4demand[0][3] = ["P_LOT"]

    bridge_demand_to_supply_execution(root=node)

    assert node.psi4demand[0][0] == ["S_LOT"]
    assert node.psi4demand[0][3] == ["P_LOT"]


def test_replace_mode_idempotent():
    node = _node("mom")
    node.psi4demand[0][0] = ["S_LOT"]
    node.psi4demand[0][3] = ["P_LOT"]

    bridge_demand_to_supply_execution(root=node, mode="replace")
    bridge_demand_to_supply_execution(root=node, mode="replace")

    assert node.psi4supply[0][0] == ["S_LOT"]
    assert node.psi4supply[0][3] == ["P_LOT"]


def test_append_mode():
    node = _node("mom")
    node.psi4supply[0][0] = ["OLD_S"]
    node.psi4supply[0][3] = ["OLD_P"]
    node.psi4demand[0][0] = ["S_LOT"]
    node.psi4demand[0][3] = ["P_LOT"]

    bridge_demand_to_supply_execution(root=node, mode="append")

    assert node.psi4supply[0][0] == ["OLD_S", "S_LOT"]
    assert node.psi4supply[0][3] == ["OLD_P", "P_LOT"]


def test_dedupe_append_mode():
    node = _node("mom")
    node.psi4supply[0][0] = ["S_LOT"]
    node.psi4demand[0][0] = ["S_LOT", "S_LOT2"]

    result = bridge_demand_to_supply_execution(root=node, mode="dedupe_append", bridge_policy="s_only")

    assert node.psi4supply[0][0] == ["S_LOT", "S_LOT2"]
    assert result.duplicate_lot_ids == ["S_LOT"]


def test_bridge_leadtime_weeks():
    node = _node("mom", weeks=3)
    node.psi4demand[0][0] = ["S_LOT"]

    bridge_demand_to_supply_execution(root=node, bridge_policy="s_only", bridge_leadtime_weeks=1)

    assert node.psi4supply[1][0] == ["S_LOT"]


def test_full_clone_policy():
    node = _node("mom")
    node.psi4demand[0] = [["S"], ["CO"], ["I"], ["P"]]

    bridge_demand_to_supply_execution(root=node, bridge_policy="full_clone")

    assert node.psi4supply[0] == [["S"], ["CO"], ["I"], ["P"]]


def test_s_only_policy():
    node = _node("mom")
    node.psi4demand[0] = [["S"], ["CO"], ["I"], ["P"]]

    bridge_demand_to_supply_execution(root=node, bridge_policy="s_only")

    assert node.psi4supply[0] == [["S"], [], [], []]


def test_non_list_bucket_error():
    node = _node("mom")
    node.psi4demand[0][0] = "NOT_LIST"

    result = bridge_demand_to_supply_execution(root=node, bridge_policy="s_only")

    assert len(result.non_list_bucket_errors) == 1


def test_no_numeric_quantities_inserted():
    node = _node("mom")
    node.psi4demand[0][0] = ["S_LOT"]
    node.psi4demand[0][3] = ["P_LOT"]

    bridge_demand_to_supply_execution(root=node)

    assert all(
        isinstance(lot_id, str)
        for week in node.psi4supply
        for bucket in week
        for lot_id in bucket
    )
