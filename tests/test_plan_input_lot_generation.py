from pysi.adapters.lot_generation import LotGenerationConfig, generate_lots_from_weekly_plan
from pysi.adapters.weekly_plan_table import WeeklyPlanRow


def _row(quantity: float = 1.0) -> WeeklyPlanRow:
    return WeeklyPlanRow(
        scenario_id="RICE_AS_IS",
        product_id="BROWN_RICE_STANDARD",
        node_id="PRODUCER_NIIGATA",
        week="2026-W40",
        plan_type="supply",
        quantity=quantity,
        source_granularity="case_weekly",
        source_id="rice_supply_plan.csv",
    )


def test_zero_quantity_generates_no_lots():
    assert generate_lots_from_weekly_plan(_row(0.0)) == []


def test_lot_count_mode_generates_three_lots():
    lots = generate_lots_from_weekly_plan(_row(3.0), config=LotGenerationConfig(quantity_mode="lot_count"))
    assert len(lots) == 3
    assert [lot.quantity for lot in lots] == [1.0, 1.0, 1.0]


def test_fractional_last_lot_is_supported():
    lots = generate_lots_from_weekly_plan(
        _row(1.6), config=LotGenerationConfig(quantity_mode="lot_count", allow_fractional_last_lot=True)
    )
    assert [lot.quantity for lot in lots] == [1.0, 0.6]


def test_negative_quantity_raises_value_error():
    try:
        generate_lots_from_weekly_plan(_row(-1.0))
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "quantity" in str(exc)


def test_lot_ids_are_deterministic():
    first = generate_lots_from_weekly_plan(_row(2.0))
    second = generate_lots_from_weekly_plan(_row(2.0))
    assert [lot.lot_id for lot in first] == [lot.lot_id for lot in second]


def test_rice_crop_year_metadata_is_preserved():
    attrs = {
        "crop_year": "2026",
        "harvest_week": "2026-W40",
        "available_week": "2026-W41",
        "quality_limit_week": "2027-W40",
    }
    lots = generate_lots_from_weekly_plan(_row(1.0), attributes=attrs)
    assert lots[0].attributes["crop_year"] == "2026"
    assert lots[0].attributes["harvest_week"] == "2026-W40"
    assert lots[0].attributes["available_week"] == "2026-W41"
