from pathlib import Path

from pysi.planning.capacity_io import (
    CapacityUsage,
    CapacityViolation,
    export_capacity_usage_csv,
    export_capacity_violation_csv,
    run_forward_push_with_capacity_from_master,
)
from pysi.planning.capacity_master import (
    build_capacity_lookup,
    get_capacity_record,
    load_capacity_master_csv,
)


def test_load_capacity_master_csv_and_types():
    records = load_capacity_master_csv("pysi/master_data/capacity_master_sample.csv")
    assert len(records) == 4
    assert isinstance(records[0].capacity_qty, int)
    assert isinstance(records[0].priority, int)


def test_exact_lookup_and_wildcard_and_missing():
    lookup = build_capacity_lookup(load_capacity_master_csv("pysi/master_data/capacity_master_sample.csv"))

    exact = get_capacity_record(
        lookup,
        scenario_id="BASE",
        tree_side="INBOUND",
        node_name="MOM_CHINA",
        product_name="IPHONE_NM_2028_BASE",
        week="2026-W01",
        capacity_type="P",
    )
    assert exact is not None
    assert exact.capacity_qty == 100

    wildcard = get_capacity_record(
        lookup,
        scenario_id="BASE",
        tree_side="INBOUND",
        node_name="MOM_CHINA",
        product_name="ANY_PRODUCT",
        week="2026-W02",
        capacity_type="P",
    )
    assert wildcard is not None
    assert wildcard.product_name == "*"

    missing = get_capacity_record(
        lookup,
        scenario_id="BASE",
        tree_side="INBOUND",
        node_name="MOM_CHINA",
        product_name="ANY_PRODUCT",
        week="2026-W99",
        capacity_type="P",
    )
    assert missing is None


def test_missing_capacity_treated_as_unlimited():
    lookup = build_capacity_lookup(load_capacity_master_csv("pysi/master_data/capacity_master_sample.csv"))
    requested = [{"lot_id": f"L{i}"} for i in range(120)]
    result, usage, violation = run_forward_push_with_capacity_from_master(
        scenario_id="BASE",
        tree_side="INBOUND",
        node_name="MOM_CHINA",
        product_name="NO_CAPACITY_PRODUCT",
        week="2026-W01",
        capacity_type="P",
        requested_lots=requested,
        capacity_lookup=lookup,
    )
    assert len(result.pushed_lots) == 120
    assert len(result.blocked_lots) == 0
    assert usage is None
    assert violation is None


def test_export_headers_and_lot_id_handling(tmp_path: Path):
    usage_path = tmp_path / "usage.csv"
    violation_path = tmp_path / "violation.csv"

    usage = CapacityUsage(
        scenario_id="BASE", tree_side="INBOUND", node_name="MOM", product_name="P", week="2026-W01",
        capacity_type="P", capacity_qty=10, used_qty=2, used_lot_ids=["L001", "L002"]
    )
    violation = CapacityViolation(
        scenario_id="BASE", tree_side="INBOUND", node_name="MOM", product_name="P", week="2026-W01",
        capacity_type="P", cap_mode="soft", capacity_qty=10, required_qty=12, overflow_qty=2,
        violation_type="CAPACITY_OVERFLOW", overflow_lot_ids=["L011", "L012"]
    )

    export_capacity_usage_csv([usage], usage_path)
    export_capacity_violation_csv([violation], violation_path)

    usage_lines = usage_path.read_text(encoding="utf-8").splitlines()
    violation_lines = violation_path.read_text(encoding="utf-8").splitlines()
    assert usage_lines[0] == "scenario_id,tree_side,node_name,product_name,week,capacity_type,capacity_qty,used_qty,remaining_qty,utilization,used_lot_ids"
    assert violation_lines[0] == "scenario_id,tree_side,node_name,product_name,week,capacity_type,cap_mode,capacity_qty,required_qty,overflow_qty,violation_type,overflow_lot_ids,action"
    assert "L001|L002" in usage_lines[1]
    assert "L011|L012" in violation_lines[1]


def test_zero_capacity_creates_violation():
    lookup = build_capacity_lookup([
        load_capacity_master_csv("pysi/master_data/capacity_master_sample.csv")[0].__class__(
            scenario_id="BASE", tree_side="INBOUND", node_name="MOM_CHINA", product_name="IPHONE_NM_2028_BASE",
            week="2026-W01", capacity_type="P", capacity_qty=0, cap_mode="hard"
        )
    ])

    requested = ["L1", {"lot_id": "L2"}]
    result, usage, violation = run_forward_push_with_capacity_from_master(
        scenario_id="BASE",
        tree_side="INBOUND",
        node_name="MOM_CHINA",
        product_name="IPHONE_NM_2028_BASE",
        week="2026-W01",
        capacity_type="P",
        requested_lots=requested,
        capacity_lookup=lookup,
    )
    assert len(result.pushed_lots) == 0
    assert len(result.blocked_lots) == 2
    assert usage is not None and usage.used_qty == 0
    assert violation is not None and violation.overflow_qty == 2
    assert violation.overflow_lot_ids == ["L1", "L2"]