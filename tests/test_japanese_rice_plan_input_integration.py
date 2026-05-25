from pysi.cases.japanese_rice import (
    build_default_rice_case_dataset,
    build_rice_row_attributes,
    build_rice_week_indexer,
    build_rice_weekly_plan_rows,
    seed_rice_weekly_rows_to_mock_plan_nodes,
)


def test_rice_weekly_rows_generation_contains_demand_and_supply_rows():
    dataset = build_default_rice_case_dataset()
    rows = build_rice_weekly_plan_rows(dataset)

    assert rows
    assert any(row.plan_type == "demand" for row in rows)
    assert any(row.plan_type == "supply" for row in rows)
    assert all(row.source_granularity == "case_weekly" for row in rows)


def test_crop_year_metadata_is_preserved_in_lot_header_attributes():
    dataset = build_default_rice_case_dataset()
    rows = build_rice_weekly_plan_rows(dataset)
    row_attributes = build_rice_row_attributes(rows)

    supply_attribute_rows = [row_attributes[idx] for idx, row in enumerate(rows) if row.plan_type == "supply"]
    assert supply_attribute_rows
    assert all("crop_year" in attrs for attrs in supply_attribute_rows)
    assert all("harvest_week" in attrs for attrs in supply_attribute_rows)
    assert all("available_week" in attrs for attrs in supply_attribute_rows)
    assert all("quality_limit_week" in attrs for attrs in supply_attribute_rows)


def test_week_indexer_w40_w41_boundary_is_preserved_and_seeded_to_correct_buckets():
    dataset = build_default_rice_case_dataset()
    rows = build_rice_weekly_plan_rows(dataset)
    week_indexer = build_rice_week_indexer(2026, 2028)

    assert week_indexer["2026-W40"] == 39
    assert week_indexer["2026-W41"] == 40

    result = seed_rice_weekly_rows_to_mock_plan_nodes(rows, week_indexer=week_indexer)

    producer = result.plan_nodes["PRODUCER_NIIGATA"]
    assert producer.psi4demand[39][3]
    assert producer.psi4demand[40][3]


def test_plan_node_seed_uses_lot_id_lists_not_quantities_and_maps_demand_supply_buckets():
    dataset = build_default_rice_case_dataset()
    rows = build_rice_weekly_plan_rows(dataset)
    week_indexer = build_rice_week_indexer()

    result = seed_rice_weekly_rows_to_mock_plan_nodes(rows, week_indexer=week_indexer)

    demand_node = result.plan_nodes["DEMAND_HOUSEHOLD_TOKYO"]
    producer_node = result.plan_nodes["PRODUCER_NIIGATA"]

    household_w1_s_bucket = demand_node.psi4demand[0][0]
    producer_w40_p_bucket = producer_node.psi4demand[39][3]

    assert household_w1_s_bucket
    assert producer_w40_p_bucket

    assert isinstance(household_w1_s_bucket, list)
    assert isinstance(producer_w40_p_bucket, list)
    assert all(isinstance(item, str) for item in household_w1_s_bucket)
    assert all(isinstance(item, str) for item in producer_w40_p_bucket)
    assert not any(isinstance(item, (int, float)) for item in household_w1_s_bucket)
    assert not any(isinstance(item, (int, float)) for item in producer_w40_p_bucket)

    assert result.demand_s_count > 0
    assert result.supply_p_count > 0
    assert result.missing_node_ids == []
    assert result.invalid_weeks == []
