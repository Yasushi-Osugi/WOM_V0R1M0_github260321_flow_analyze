from pysi.capacity.capacity_exporter import (
    export_capacity_usage_csv,
    export_capacity_violation_csv,
)
from pysi.capacity.capacity_model import CapacityBucket
from pysi.capacity.capacity_planning import (
    iter_nodes_for_capacity_forward,
    with_capacity_forward_planning,
)


class SmallInboundTreeNode:
    def __init__(self, name: str):
        self.name = name
        self.children = []
        self.psi4demand = {}
        self.psi4supply = {}

    def add_child(self, child):
        self.children.append(child)

    def init_week(self, week):
        self.psi4demand[week] = [[], [], [], []]
        self.psi4supply[week] = [[], [], [], []]


def _build_small_inbound_tree(week: str):
    mom = SmallInboundTreeNode("MOM_TEST")
    raw_a = SmallInboundTreeNode("RAW_A_TEST")
    raw_b = SmallInboundTreeNode("RAW_B_TEST")

    mom.add_child(raw_a)
    mom.add_child(raw_b)

    for node in (mom, raw_a, raw_b):
        node.init_week(week)

    return mom, raw_a, raw_b


def test_capacity_forward_inbound_postorder_traversal():
    week = "2026-W01"
    mom, _, _ = _build_small_inbound_tree(week)

    order = [node.name for node in iter_nodes_for_capacity_forward(mom, "INBOUND")]

    assert order == ["RAW_A_TEST", "RAW_B_TEST", "MOM_TEST"]


def test_with_capacity_forward_planning_small_inbound_tree_raw_a_p_cap():
    week = "2026-W01"
    mom, raw_a, _ = _build_small_inbound_tree(week)
    raw_a.psi4demand[week][3] = ["PA1", "PA2", "PA3", "PA4", "PA5"]

    bucket = CapacityBucket(
        scenario_id="BASE",
        node_name="RAW_A_TEST",
        product_name="TEST_PRODUCT",
        week=week,
        capacity_type="P",
        capacity_qty=3,
        cap_mode="soft",
    )

    _, violation_records = with_capacity_forward_planning(
        root_node=mom,
        weeks=[week],
        scenario_id="BASE",
        product_name="TEST_PRODUCT",
        capacity_buckets=[bucket],
        tree_side="INBOUND",
    )

    assert raw_a.psi4supply[week][3] == ["PA1", "PA2", "PA3"]

    p_violation = next(r for r in violation_records if r.node_name == "RAW_A_TEST" and r.capacity_type == "P")
    assert p_violation.overflow_qty == 2
    assert p_violation.violation_type == "CAPACITY_OVER_SOFT"
    assert p_violation.action == "CARRY_OVER"


def test_with_capacity_forward_planning_small_inbound_tree_raw_b_s_cap():
    week = "2026-W01"
    mom, _, raw_b = _build_small_inbound_tree(week)
    raw_b.psi4demand[week][0] = ["SB1", "SB2", "SB3", "SB4"]

    bucket = CapacityBucket(
        scenario_id="BASE",
        node_name="RAW_B_TEST",
        product_name="TEST_PRODUCT",
        week=week,
        capacity_type="S",
        capacity_qty=2,
        cap_mode="soft",
    )

    _, violation_records = with_capacity_forward_planning(
        root_node=mom,
        weeks=[week],
        scenario_id="BASE",
        product_name="TEST_PRODUCT",
        capacity_buckets=[bucket],
        tree_side="INBOUND",
    )

    assert raw_b.psi4supply[week][0] == ["SB1", "SB2"]

    s_violation = next(r for r in violation_records if r.node_name == "RAW_B_TEST" and r.capacity_type == "S")
    assert s_violation.overflow_qty == 2
    assert s_violation.violation_type == "CAPACITY_OVER_SOFT"
    assert s_violation.action == "CARRY_OVER"


def test_with_capacity_forward_planning_small_inbound_tree_mom_i_cap_soft():
    week = "2026-W01"
    mom, _, _ = _build_small_inbound_tree(week)
    mom.psi4supply[week][2] = ["IM1", "IM2", "IM3", "IM4"]

    bucket = CapacityBucket(
        scenario_id="BASE",
        node_name="MOM_TEST",
        product_name="TEST_PRODUCT",
        week=week,
        capacity_type="I",
        capacity_qty=3,
        cap_mode="soft",
    )

    _, violation_records = with_capacity_forward_planning(
        root_node=mom,
        weeks=[week],
        scenario_id="BASE",
        product_name="TEST_PRODUCT",
        capacity_buckets=[bucket],
        tree_side="INBOUND",
    )

    assert mom.psi4supply[week][2] == ["IM1", "IM2", "IM3", "IM4"]

    i_violation = next(r for r in violation_records if r.node_name == "MOM_TEST" and r.capacity_type == "I")
    assert i_violation.required_qty == 4
    assert i_violation.overflow_qty == 1
    assert i_violation.violation_type == "INVENTORY_OVER_SOFT"
    assert i_violation.action == "ALERT_ONLY"


def test_with_capacity_forward_planning_small_inbound_tree_multi_node_records():
    week = "2026-W01"
    mom, raw_a, raw_b = _build_small_inbound_tree(week)

    raw_a.psi4demand[week][3] = ["PA1", "PA2", "PA3", "PA4", "PA5"]
    raw_b.psi4demand[week][0] = ["SB1", "SB2", "SB3", "SB4"]
    mom.psi4supply[week][2] = ["IM1", "IM2", "IM3", "IM4"]

    capacity_buckets = [
        CapacityBucket("BASE", "RAW_A_TEST", "TEST_PRODUCT", week, "P", 3, "soft"),
        CapacityBucket("BASE", "RAW_B_TEST", "TEST_PRODUCT", week, "S", 2, "soft"),
        CapacityBucket("BASE", "MOM_TEST", "TEST_PRODUCT", week, "I", 3, "soft"),
    ]

    usage_records, violation_records = with_capacity_forward_planning(
        root_node=mom,
        weeks=[week],
        scenario_id="BASE",
        product_name="TEST_PRODUCT",
        capacity_buckets=capacity_buckets,
        tree_side="INBOUND",
    )

    usage_pairs = {(r.node_name, r.capacity_type) for r in usage_records}
    assert ("RAW_A_TEST", "P") in usage_pairs
    assert ("RAW_B_TEST", "S") in usage_pairs
    assert ("MOM_TEST", "I") in usage_pairs

    violation_pairs = {(r.node_name, r.violation_type) for r in violation_records}
    assert ("RAW_A_TEST", "CAPACITY_OVER_SOFT") in violation_pairs
    assert ("RAW_B_TEST", "CAPACITY_OVER_SOFT") in violation_pairs
    assert ("MOM_TEST", "INVENTORY_OVER_SOFT") in violation_pairs


def test_capacity_export_from_small_inbound_tree_result(tmp_path):
    week = "2026-W01"
    mom, raw_a, raw_b = _build_small_inbound_tree(week)

    raw_a.psi4demand[week][3] = ["PA1", "PA2", "PA3", "PA4", "PA5"]
    raw_b.psi4demand[week][0] = ["SB1", "SB2", "SB3", "SB4"]
    mom.psi4supply[week][2] = ["IM1", "IM2", "IM3", "IM4"]

    capacity_buckets = [
        CapacityBucket("BASE", "RAW_A_TEST", "TEST_PRODUCT", week, "P", 3, "soft"),
        CapacityBucket("BASE", "RAW_B_TEST", "TEST_PRODUCT", week, "S", 2, "soft"),
        CapacityBucket("BASE", "MOM_TEST", "TEST_PRODUCT", week, "I", 3, "soft"),
    ]

    usage_records, violation_records = with_capacity_forward_planning(
        root_node=mom,
        weeks=[week],
        scenario_id="BASE",
        product_name="TEST_PRODUCT",
        capacity_buckets=capacity_buckets,
        tree_side="INBOUND",
    )

    usage_path = tmp_path / "capacity_usage_small_inbound_tree.csv"
    violation_path = tmp_path / "capacity_violation_small_inbound_tree.csv"
    export_capacity_usage_csv(usage_path, usage_records)
    export_capacity_violation_csv(violation_path, violation_records)

    assert usage_path.exists()
    assert violation_path.exists()

    usage_text = usage_path.read_text(encoding="utf-8")
    violation_text = violation_path.read_text(encoding="utf-8")

    assert "scenario_id,tree_side,node_name,product_name,week,capacity_type" in usage_text
    assert "scenario_id,tree_side,node_name,product_name,week,capacity_type,cap_mode" in violation_text
    assert "PA1|PA2|PA3" in usage_text
    assert "PA4|PA5" in violation_text
    assert "RAW_A_TEST" in usage_text
    assert "RAW_B_TEST" in usage_text
    assert "MOM_TEST" in usage_text
    assert "RAW_A_TEST" in violation_text
    assert "RAW_B_TEST" in violation_text
    assert "MOM_TEST" in violation_text
    assert len(usage_records) > 0
    assert len(violation_records) > 0
