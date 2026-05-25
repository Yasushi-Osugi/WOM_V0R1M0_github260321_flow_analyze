from dataclasses import dataclass, field

from pysi.plan.bridges.demand_to_supply_execution_bridge import bridge_demand_to_supply_execution
from pysi.plan.weekly_forward_push_with_capacity import weekly_forward_push_with_capacity


PSI_S = 0
PSI_I = 2
PSI_P = 3


@dataclass
class MockSupplyNode:
    name: str
    children: list = field(default_factory=list)
    psi4supply: list = field(default_factory=list)
    psi4demand: list = field(default_factory=list)


def make_node(name: str, weeks: int):
    return MockSupplyNode(
        name=name,
        children=[],
        psi4supply=[[[], [], [], []] for _ in range(weeks)],
        psi4demand=[[[], [], [], []] for _ in range(weeks)],
    )


def test_p_cap_blocks_production_lots():
    node = make_node("N1", 12)
    node.psi4supply[10][PSI_P] = ["P1", "P2", "P3"]

    result = weekly_forward_push_with_capacity(
        root=node,
        product="rice",
        weekly_capacity={"rice": {"N1": {"P": [None] * 10 + [2]}}},
    )

    assert node.psi4supply[10][PSI_P] == ["P1", "P2"]
    assert result.blocked_p_lot_ids == ["P3"]


def test_s_cap_blocks_shipment_lots():
    node = make_node("N1", 12)
    node.psi4supply[10][PSI_I] = ["A", "B", "C"]
    node.psi4supply[10][PSI_S] = ["A", "B", "C"]

    result = weekly_forward_push_with_capacity(
        root=node,
        product="rice",
        weekly_capacity={"rice": {"N1": {"S": [None] * 10 + [2]}}},
    )

    assert node.psi4supply[10][PSI_S] == ["A", "B"]
    assert result.blocked_s_lot_ids == ["C"]


def test_i_cap_soft_overflow_keeps_inventory():
    node = make_node("N1", 12)
    node.psi4supply[10][PSI_I] = ["I1", "I2", "I3"]

    result = weekly_forward_push_with_capacity(
        root=node,
        product="rice",
        weekly_capacity={"rice": {"N1": {"I": [None] * 10 + [2]}}},
        cap_i_mode="soft",
    )

    assert node.psi4supply[10][PSI_I] == ["I1", "I2", "I3"]
    assert result.overflow_i_lot_ids == ["I3"]


def test_no_numeric_quantities_inserted():
    node = make_node("N1", 4)
    node.psi4supply[0][PSI_I] = ["A", "B"]
    node.psi4supply[0][PSI_P] = ["P1"]
    node.psi4supply[0][PSI_S] = ["A"]

    weekly_forward_push_with_capacity(root=node, product="rice", weekly_capacity={"rice": {"N1": {"P": [1], "S": [1], "I": [10]}}})

    assert all(isinstance(bucket, list) for week in node.psi4supply for bucket in week)
    assert all(isinstance(lot_id, str) for week in node.psi4supply for bucket in week for lot_id in bucket)


def test_missing_capacity_means_unlimited():
    node = make_node("N1", 2)
    node.psi4supply[0][PSI_P] = ["P1", "P2"]
    node.psi4supply[0][PSI_S] = ["P1", "P2"]

    result = weekly_forward_push_with_capacity(root=node, product="rice", weekly_capacity=None)

    assert result.blocked_p_lot_ids == []
    assert result.blocked_s_lot_ids == []
    assert node.psi4supply[0][PSI_P] == ["P1", "P2"]
    assert node.psi4supply[0][PSI_S] == ["P1", "P2"]


def test_bridge_b_compatibility_seed_then_run():
    node = make_node("N1", 4)
    node.psi4demand[0][PSI_S] = ["S1", "S2"]
    node.psi4demand[0][PSI_P] = ["P1", "P2"]

    bridge_demand_to_supply_execution(root=node)
    result = weekly_forward_push_with_capacity(root=node, product="rice", weekly_capacity=None)

    assert result.non_list_bucket_errors == []
    assert isinstance(node.psi4supply[0], list)
    assert len(node.psi4supply[0]) >= 4
