from pysi.capacity.capacity_exporter import export_capacity_usage_csv, export_capacity_violation_csv
from pysi.capacity.capacity_master_loader import load_capacity_master_csv
from pysi.capacity.capacity_model import CapacityUsage, CapacityViolation
from pysi.capacity.capacity_planning import split_lots_by_capacity


def test_split_lots_by_capacity():
    lots = ["L1", "L2", "L3", "L4", "L5"]
    executable, overflow = split_lots_by_capacity(lots, 3)
    assert executable == ["L1", "L2", "L3"]
    assert overflow == ["L4", "L5"]


def test_usage_properties_and_csv_export(tmp_path):
    usage = CapacityUsage("BASE", "OUTBOUND", "N1", "P1", "2026-W01", "P", 3, 2, ["L1", "L2"])
    assert usage.remaining_qty == 1
    assert usage.utilization == 2 / 3

    violation = CapacityViolation("BASE", "OUTBOUND", "N1", "P1", "2026-W01", "P", "soft", 3, 5, 2, "OVERFLOW", ["L4", "L5"], "CARRY_OVER")

    usage_path = tmp_path / "out" / "capacity_usage.csv"
    vio_path = tmp_path / "out" / "capacity_violation.csv"
    export_capacity_usage_csv(usage_path, [usage])
    export_capacity_violation_csv(vio_path, [violation])
    assert usage_path.exists()
    assert vio_path.exists()


def test_load_capacity_master_sample():
    rows = load_capacity_master_csv("pysi/master_data/capacity_master_sample.csv")
    assert len(rows) >= 5
    assert rows[0].capacity_type in {"P", "S", "I"}
