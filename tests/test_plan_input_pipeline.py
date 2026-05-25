from pysi.adapters.plan_input_granularity import monthly_plan_to_weekly_rows
from pysi.adapters.plan_input_pipeline import weekly_rows_to_lots_and_seed_table
from pysi.adapters.weekly_plan_table import MonthlyPlanInputRow, WeeklyPlanRow


def test_weekly_rows_to_lots_and_seed_records_pipeline():
    rows = [WeeklyPlanRow("BASE", "PRODUCT_X", "NODE_A", "2026-W20", "demand", 2.0, "weekly")]
    lots, seed_records, table = weekly_rows_to_lots_and_seed_table(rows)
    assert len(lots) == 2
    assert len(seed_records) == 2
    key = ("BASE", "PRODUCT_X", "NODE_A", "2026-W20", "demand", "S")
    assert key in table
    assert len(table[key]) == 2


def test_monthly_to_445_weekly_to_lots_pipeline():
    monthly = [MonthlyPlanInputRow("BASE", "PRODUCT_X", "NODE_A", "2026-M01", "S", 4.0)]
    weekly = monthly_plan_to_weekly_rows(monthly)
    lots, seed_records, table = weekly_rows_to_lots_and_seed_table(weekly)
    assert len(weekly) == 4
    assert len(lots) == 4
    assert len(seed_records) == 4
    assert sum(len(v) for v in table.values()) == 4


def test_rice_w40_w41_boundary_preserved_through_pipeline():
    rows = [
        WeeklyPlanRow("RICE_AS_IS", "BROWN_RICE_STANDARD", "PRODUCER_NIIGATA", "2026-W40", "supply", 1.0, "case_weekly"),
        WeeklyPlanRow("RICE_AS_IS", "BROWN_RICE_STANDARD", "PRODUCER_NIIGATA", "2026-W41", "supply", 1.0, "case_weekly"),
    ]
    lots, seed_records, table = weekly_rows_to_lots_and_seed_table(rows)
    assert [lot.week for lot in lots] == ["2026-W40", "2026-W41"]
    assert [record.week for record in seed_records] == ["2026-W40", "2026-W41"]
    keys = set(table.keys())
    assert ("RICE_AS_IS", "BROWN_RICE_STANDARD", "PRODUCER_NIIGATA", "2026-W40", "demand", "P") in keys
    assert ("RICE_AS_IS", "BROWN_RICE_STANDARD", "PRODUCER_NIIGATA", "2026-W41", "demand", "P") in keys
