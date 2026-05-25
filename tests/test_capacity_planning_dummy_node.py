from pathlib import Path

from pysi.capacity.capacity_exporter import (
    export_capacity_usage_csv,
    export_capacity_violation_csv,
)
from pysi.capacity.capacity_model import CapacityBucket
from pysi.capacity.capacity_planning import with_capacity_forward_planning


class DummyNode:
    def __init__(self, name: str):
        self.name = name
        self.children = []
        self.psi4demand = {}
        self.psi4supply = {}

    def init_week(self, week):
        self.psi4demand[week] = [[], [], [], []]
        self.psi4supply[week] = [[], [], [], []]


def _run(node, week, product_name, bucket):
    return with_capacity_forward_planning(
        root_node=node,
        weeks=[week],
        scenario_id="BASE",
        product_name=product_name,
        capacity_buckets=[bucket],
        tree_side="OUTBOUND",
        node_order=[node],
    )


def test_with_capacity_forward_planning_p_cap_dummy_node():
    week = "2026-W01"
    node = DummyNode("DUMMY_MOM")
    node.init_week(week)
    node.psi4demand[week][3] = ["L1", "L2", "L3", "L4", "L5"]

    bucket = CapacityBucket(
        scenario_id="BASE",
        node_name="DUMMY_MOM",
        product_name="TEST_PRODUCT",
        week=week,
        capacity_type="P",
        capacity_qty=3,
        cap_mode="soft",
    )

    usage_records, violation_records = _run(node, week, "TEST_PRODUCT", bucket)

    assert node.psi4supply[week][3] == ["L1", "L2", "L3"]

    p_usage = next(r for r in usage_records if r.capacity_type == "P")
    assert p_usage.capacity_qty == 3
    assert p_usage.used_qty == 3
    assert p_usage.utilization == 1.0

    p_violation = next(r for r in violation_records if r.capacity_type == "P")
    assert p_violation.cap_mode == "soft"
    assert p_violation.overflow_qty == 2
    assert p_violation.violation_type == "CAPACITY_OVER_SOFT"
    assert p_violation.action == "CARRY_OVER"


def test_with_capacity_forward_planning_s_cap_dummy_node():
    week = "2026-W01"
    node = DummyNode("DUMMY_DAD")
    node.init_week(week)
    node.psi4demand[week][0] = ["S1", "S2", "S3", "S4"]

    bucket = CapacityBucket(
        scenario_id="BASE",
        node_name="DUMMY_DAD",
        product_name="TEST_PRODUCT",
        week=week,
        capacity_type="S",
        capacity_qty=2,
        cap_mode="soft",
    )

    _, violation_records = _run(node, week, "TEST_PRODUCT", bucket)

    assert node.psi4supply[week][0] == ["S1", "S2"]

    s_violation = next(r for r in violation_records if r.capacity_type == "S")
    assert s_violation.cap_mode == "soft"
    assert s_violation.overflow_qty == 2
    assert s_violation.violation_type == "CAPACITY_OVER_SOFT"
    assert s_violation.action == "CARRY_OVER"


def test_with_capacity_forward_planning_i_cap_soft_dummy_node():
    week = "2026-W01"
    node = DummyNode("DUMMY_DAD")
    node.init_week(week)
    node.psi4supply[week][2] = ["I1", "I2", "I3", "I4"]

    bucket = CapacityBucket(
        scenario_id="BASE",
        node_name="DUMMY_DAD",
        product_name="TEST_PRODUCT",
        week=week,
        capacity_type="I",
        capacity_qty=3,
        cap_mode="soft",
    )

    _, violation_records = _run(node, week, "TEST_PRODUCT", bucket)

    assert node.psi4supply[week][2] == ["I1", "I2", "I3", "I4"]

    i_violation = next(r for r in violation_records if r.capacity_type == "I")
    assert i_violation.cap_mode == "soft"
    assert i_violation.required_qty == 4
    assert i_violation.overflow_qty == 1
    assert i_violation.violation_type == "INVENTORY_OVER_SOFT"
    assert i_violation.action == "ALERT_ONLY"


def test_with_capacity_forward_planning_i_cap_hard_dummy_node():
    week = "2026-W01"
    node = DummyNode("DUMMY_COLD_DC")
    node.init_week(week)
    node.psi4supply[week][2] = ["I1", "I2", "I3", "I4"]

    bucket = CapacityBucket(
        scenario_id="BASE",
        node_name="DUMMY_COLD_DC",
        product_name="VACCINE_X",
        week=week,
        capacity_type="I",
        capacity_qty=3,
        cap_mode="hard",
    )

    _, violation_records = _run(node, week, "VACCINE_X", bucket)

    i_violation = next(r for r in violation_records if r.capacity_type == "I")
    assert i_violation.cap_mode == "hard"
    assert i_violation.required_qty == 4
    assert i_violation.overflow_qty == 1
    assert i_violation.violation_type == "INVENTORY_OVER_HARD"
    assert i_violation.action == "WASTE"


def test_capacity_export_from_dummy_node_result(tmp_path):
    week = "2026-W01"
    node = DummyNode("DUMMY_MOM")
    node.init_week(week)
    node.psi4demand[week][3] = ["L1", "L2", "L3", "L4", "L5"]

    bucket = CapacityBucket(
        scenario_id="BASE",
        node_name="DUMMY_MOM",
        product_name="TEST_PRODUCT",
        week=week,
        capacity_type="P",
        capacity_qty=3,
        cap_mode="soft",
    )

    usage_records, violation_records = _run(node, week, "TEST_PRODUCT", bucket)

    usage_path = tmp_path / "capacity_usage.csv"
    violation_path = tmp_path / "capacity_violation.csv"
    export_capacity_usage_csv(usage_path, usage_records)
    export_capacity_violation_csv(violation_path, violation_records)

    assert usage_path.exists()
    assert violation_path.exists()

    usage_text = usage_path.read_text(encoding="utf-8")
    violation_text = violation_path.read_text(encoding="utf-8")

    assert "scenario_id,tree_side,node_name,product_name,week,capacity_type" in usage_text
    assert "scenario_id,tree_side,node_name,product_name,week,capacity_type,cap_mode" in violation_text
    assert "L1|L2|L3" in usage_text
    assert "L4|L5" in violation_text
