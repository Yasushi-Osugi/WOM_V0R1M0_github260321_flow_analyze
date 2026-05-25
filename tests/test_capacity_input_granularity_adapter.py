from pysi.adapters.capacity_input_granularity import (
    MonthlyCapacityInputRow,
    WeeklyCapacityInputRow,
    WeeklyCapacityRow,
    monthly_capacity_to_weekly_rows,
    normalize_capacity_input_to_weekly_rows,
    weekly_capacity_rows_to_weekly_capability,
    weekly_capacity_to_weekly_rows,
)


def test_445_m01_weeks():
    rows = [
        MonthlyCapacityInputRow("BASE", "PRODUCT_X", "node", "MOM_CHINA", "2026-M01", "P", 400.0)
    ]
    weekly = monthly_capacity_to_weekly_rows(rows, calendar_mode="445")
    assert [r.week for r in weekly] == ["2026-W01", "2026-W02", "2026-W03", "2026-W04"]


def test_445_m03_weeks():
    rows = [
        MonthlyCapacityInputRow("BASE", "PRODUCT_X", "node", "MOM_CHINA", "2026-M03", "P", 500.0)
    ]
    weekly = monthly_capacity_to_weekly_rows(rows, calendar_mode="445")
    assert [r.week for r in weekly] == ["2026-W09", "2026-W10", "2026-W11", "2026-W12", "2026-W13"]


def test_445_has_52_weeks():
    rows = [
        MonthlyCapacityInputRow("BASE", "PRODUCT_X", "node", "MOM_CHINA", f"2026-M{i:02d}", "P", 100.0)
        for i in range(1, 13)
    ]
    weekly = monthly_capacity_to_weekly_rows(rows, calendar_mode="445")
    assert len(weekly) == 52


def test_445_m03_500_becomes_100_per_week():
    rows = [
        MonthlyCapacityInputRow("BASE", "PRODUCT_X", "node", "MOM_CHINA", "2026-M03", "P", 500.0)
    ]
    weekly = monthly_capacity_to_weekly_rows(rows, calendar_mode="445")
    assert len(weekly) == 5
    assert all(r.capacity_qty == 100.0 for r in weekly)


def test_four_week_month_m01_weeks():
    rows = [MonthlyCapacityInputRow("BASE", "PRODUCT_X", "node", "MOM_CHINA", "2026-M01", "P", 400.0)]
    weekly = monthly_capacity_to_weekly_rows(rows, calendar_mode="four_week_month")
    assert [r.week for r in weekly] == ["2026-W01", "2026-W02", "2026-W03", "2026-W04"]


def test_four_week_month_m12_starts_at_w45():
    rows = [MonthlyCapacityInputRow("BASE", "PRODUCT_X", "node", "MOM_CHINA", "2026-M12", "P", 400.0)]
    weekly = monthly_capacity_to_weekly_rows(rows, calendar_mode="four_week_month")
    assert weekly[0].week == "2026-W45"


def test_four_week_month_does_not_cover_52_weeks():
    rows = [
        MonthlyCapacityInputRow("BASE", "PRODUCT_X", "node", "MOM_CHINA", f"2026-M{i:02d}", "P", 100.0)
        for i in range(1, 13)
    ]
    weekly = monthly_capacity_to_weekly_rows(rows, calendar_mode="four_week_month")
    assert len(weekly) == 48


def test_weekly_pass_through_preserves_week_and_qty():
    rows = [
        WeeklyCapacityInputRow("BASE", "PRODUCT_X", "node", "MILL_EAST", "2027-W40", "P", 5.0),
        WeeklyCapacityInputRow("BASE", "PRODUCT_X", "node", "MILL_EAST", "2027-W41", "P", 7.0),
    ]
    weekly = weekly_capacity_to_weekly_rows(rows)
    assert [r.week for r in weekly] == ["2027-W40", "2027-W41"]
    assert [r.capacity_qty for r in weekly] == [5.0, 7.0]


def test_case_weekly_capacity_preserves_w40_w41_boundary():
    rows = [
        WeeklyCapacityInputRow("RICE_AS_IS", "PACKAGED_RICE_STANDARD", "node", "MILL_EAST", "2027-W40", "P", 5.0),
        WeeklyCapacityInputRow("RICE_AS_IS", "PACKAGED_RICE_STANDARD", "node", "MILL_EAST", "2027-W41", "P", 6.0),
    ]
    weekly = normalize_capacity_input_to_weekly_rows(input_mode="case_weekly_capacity", weekly_rows=rows)
    assert [r.week for r in weekly] == ["2027-W40", "2027-W41"]
    assert all(r.source_granularity == "case_weekly" for r in weekly)


def test_weekly_capacity_rows_mapping_with_owner_normalization_and_duplicates_and_filter():
    rows = [
        WeeklyCapacityRow("BASE", "PRODUCT_X", "node", "DAD_CHINA", "2026-W01", "P", 100.0),
        WeeklyCapacityRow("BASE", "PRODUCT_X", "node", "DAD_CHINA", "2026-W01", "P", 20.0),
        WeeklyCapacityRow("BASE", "PRODUCT_X", "node", "DAD_CHINA", "2026-W02", "S", 99.0),
    ]
    capability = weekly_capacity_rows_to_weekly_capability(rows, weeks_count=52, capacity_type_filter="P")
    assert "PRODUCT_X" in capability
    assert "MOM_CHINA" in capability["PRODUCT_X"]
    assert capability["PRODUCT_X"]["MOM_CHINA"][0] == 120
    assert capability["PRODUCT_X"]["MOM_CHINA"][1] == 0


def test_dispatcher_invalid_mode_raises():
    try:
        normalize_capacity_input_to_weekly_rows(input_mode="invalid")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Unsupported input_mode" in str(exc)
