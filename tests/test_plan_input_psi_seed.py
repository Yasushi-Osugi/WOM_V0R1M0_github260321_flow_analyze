from pysi.adapters.psi_seed import build_psi_seed_table, generate_psi_seed_records
from pysi.adapters.weekly_plan_table import WeeklyPlanRow


def _row(plan_type: str, week: str = "2026-W40", quantity: float = 1.0) -> WeeklyPlanRow:
    return WeeklyPlanRow("BASE", "PRODUCT_X", "NODE_A", week, plan_type, quantity, "weekly")


def test_plan_type_mapping_demand_and_s_to_demand_s():
    _, seeds = generate_psi_seed_records([_row("demand"), _row("S")])
    assert [s.layer for s in seeds] == ["demand", "demand"]
    assert [s.bucket for s in seeds] == ["S", "S"]


def test_plan_type_mapping_supply_and_p_to_demand_p():
    _, seeds = generate_psi_seed_records([_row("supply"), _row("P")])
    assert [s.layer for s in seeds] == ["demand", "demand"]
    assert [s.bucket for s in seeds] == ["P", "P"]


def test_seed_table_groups_lot_ids_and_preserves_order():
    rows = [_row("demand", quantity=2.0), _row("demand", quantity=1.0)]
    _, seeds = generate_psi_seed_records(rows)
    table = build_psi_seed_table(seeds)
    key = ("BASE", "PRODUCT_X", "NODE_A", "2026-W40", "demand", "S")
    assert key in table
    assert table[key] == [record.lot_id for record in seeds]


def test_seed_table_values_are_lot_id_lists_not_numeric_quantity():
    _, seeds = generate_psi_seed_records([_row("supply", quantity=2.0)])
    table = build_psi_seed_table(seeds)
    value = next(iter(table.values()))
    assert isinstance(value, list)
    assert all(isinstance(item, str) for item in value)
