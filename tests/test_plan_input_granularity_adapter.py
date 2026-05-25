from pysi.adapters.calendar_445 import build_445_month_to_weeks_map
from pysi.adapters.plan_input_granularity import (
    case_weekly_plan_to_weekly_rows,
    monthly_plan_to_weekly_rows,
    normalize_plan_input_to_weekly_rows,
    weekly_plan_to_weekly_rows,
)
from pysi.adapters.weekly_plan_table import MonthlyPlanInputRow, WeeklyPlanInputRow


def test_445_m01_weeks():
    mapping = build_445_month_to_weeks_map(2026)
    assert mapping["2026-M01"] == ["2026-W01", "2026-W02", "2026-W03", "2026-W04"]


def test_445_m03_weeks():
    mapping = build_445_month_to_weeks_map(2026)
    assert mapping["2026-M03"] == ["2026-W09", "2026-W10", "2026-W11", "2026-W12", "2026-W13"]


def test_445_has_12_months_and_52_weeks():
    mapping = build_445_month_to_weeks_map(2026)
    assert len(mapping) == 12
    total_weeks = sum(len(weeks) for weeks in mapping.values())
    assert total_weeks == 52


def test_monthly_s_converts_evenly():
    rows = [
        MonthlyPlanInputRow(
            scenario_id="BASE",
            product_id="PRODUCT_X",
            node_id="DAD_US",
            month="2026-M01",
            plan_type="S",
            quantity=100.0,
        )
    ]
    weekly = monthly_plan_to_weekly_rows(rows)
    assert len(weekly) == 4
    assert [r.week for r in weekly] == ["2026-W01", "2026-W02", "2026-W03", "2026-W04"]
    assert all(r.quantity == 25.0 for r in weekly)
    assert all(r.source_granularity == "monthly" for r in weekly)


def test_monthly_p_converts_evenly():
    rows = [
        MonthlyPlanInputRow(
            scenario_id="BASE",
            product_id="PRODUCT_X",
            node_id="DAD_US",
            month="2026-M03",
            plan_type="P",
            quantity=500.0,
        )
    ]
    weekly = monthly_plan_to_weekly_rows(rows)
    assert len(weekly) == 5
    assert [r.week for r in weekly] == ["2026-W09", "2026-W10", "2026-W11", "2026-W12", "2026-W13"]
    assert all(r.quantity == 100.0 for r in weekly)


def test_weekly_pass_through_preserves_week_keys():
    rows = [
        WeeklyPlanInputRow("BASE", "PRODUCT_X", "DAD_US", "2026-W20", "demand", 10.0),
        WeeklyPlanInputRow("BASE", "PRODUCT_X", "DAD_US", "2026-W21", "demand", 15.0),
    ]
    weekly = weekly_plan_to_weekly_rows(rows)
    assert [r.week for r in weekly] == ["2026-W20", "2026-W21"]
    assert [r.quantity for r in weekly] == [10.0, 15.0]


def test_case_weekly_preserves_rice_boundary_weeks_w40_w41():
    rows = [
        WeeklyPlanInputRow("RICE_AS_IS", "BROWN_RICE_STANDARD", "PRODUCER_NIIGATA", "2026-W40", "supply", 20.0),
        WeeklyPlanInputRow("RICE_AS_IS", "BROWN_RICE_STANDARD", "PRODUCER_NIIGATA", "2026-W41", "supply", 22.0),
    ]
    weekly = case_weekly_plan_to_weekly_rows(rows, source_id="rice_supply_plan.csv")
    assert [r.week for r in weekly] == ["2026-W40", "2026-W41"]
    assert [r.quantity for r in weekly] == [20.0, 22.0]
    assert all(r.source_granularity == "case_weekly" for r in weekly)


def test_dispatcher_routes_monthly_sp():
    monthly = [MonthlyPlanInputRow("BASE", "PRODUCT_X", "DAD_US", "2026-M01", "S", 80.0)]
    weekly = normalize_plan_input_to_weekly_rows(input_mode="monthly_sp", monthly_rows=monthly)
    assert len(weekly) == 4
    assert all(row.source_granularity == "monthly" for row in weekly)


def test_dispatcher_routes_weekly_sp():
    raw = [WeeklyPlanInputRow("BASE", "PRODUCT_X", "DAD_US", "2026-W03", "P", 12.0)]
    weekly = normalize_plan_input_to_weekly_rows(input_mode="weekly_sp", weekly_rows=raw)
    assert len(weekly) == 1
    assert weekly[0].week == "2026-W03"
    assert weekly[0].source_granularity == "weekly"


def test_dispatcher_routes_case_weekly():
    raw = [WeeklyPlanInputRow("RICE_AS_IS", "BROWN_RICE_STANDARD", "PRODUCER_NIIGATA", "2026-W40", "supply", 20.0)]
    weekly = normalize_plan_input_to_weekly_rows(
        input_mode="case_weekly",
        weekly_rows=raw,
        source_id="rice_supply_plan.csv",
    )
    assert len(weekly) == 1
    assert weekly[0].source_granularity == "case_weekly"
    assert weekly[0].source_id == "rice_supply_plan.csv"


def test_dispatcher_invalid_mode_raises():
    try:
        normalize_plan_input_to_weekly_rows(input_mode="invalid")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Unsupported input_mode" in str(exc)
