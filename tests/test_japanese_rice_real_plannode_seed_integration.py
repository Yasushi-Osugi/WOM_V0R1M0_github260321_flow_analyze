from pysi.cases.japanese_rice import (
    build_default_rice_case_dataset,
    build_rice_week_indexer,
    build_rice_weekly_plan_rows,
    build_plan_node_lookup_from_tree,
    make_real_like_plan_node,
    seed_rice_weekly_input_to_real_like_plan_tree,
)


def _build_real_like_tree(weeks: int = 156):
    root = make_real_like_plan_node("ROOT_RICE", weeks)
    producer = make_real_like_plan_node("PRODUCER_NIIGATA", weeks)
    household = make_real_like_plan_node("DEMAND_HOUSEHOLD_TOKYO", weeks)
    food_service = make_real_like_plan_node("DEMAND_FOOD_SERVICE_TOKYO", weeks)
    root.children.extend([producer, household, food_service])
    return root, producer, household, food_service


def test_build_plan_node_lookup_from_tree_finds_children():
    root, producer, household, food_service = _build_real_like_tree()
    lookup = build_plan_node_lookup_from_tree(root)

    assert lookup["ROOT_RICE"] is root
    assert lookup["PRODUCER_NIIGATA"] is producer
    assert lookup["DEMAND_HOUSEHOLD_TOKYO"] is household
    assert lookup["DEMAND_FOOD_SERVICE_TOKYO"] is food_service


def test_rice_weekly_rows_seed_into_real_like_tree_and_preserve_w40_w41_boundary():
    dataset = build_default_rice_case_dataset()
    root, producer, household, _ = _build_real_like_tree()
    result = seed_rice_weekly_input_to_real_like_plan_tree(
        case_data=dataset,
        product_name="PACKAGED_RICE_STANDARD",
        roots=[root],
        dry_run=False,
    )

    week_indexer = build_rice_week_indexer(2026, 2028)
    assert week_indexer["2026-W40"] == 39
    assert week_indexer["2026-W41"] == 40

    assert result.plan_node_seeded_count > 0
    assert result.missing_node_ids == []
    assert result.invalid_weeks == []

    assert household.psi4demand[0][0]
    assert producer.psi4demand[39][3]
    assert producer.psi4demand[40][3]


def test_dry_run_does_not_mutate_real_like_plan_tree():
    dataset = build_default_rice_case_dataset()
    root, producer, household, _ = _build_real_like_tree()

    before_household = list(household.psi4demand[0][0])
    before_producer = list(producer.psi4demand[39][3])

    result = seed_rice_weekly_input_to_real_like_plan_tree(
        case_data=dataset,
        product_name="PACKAGED_RICE_STANDARD",
        roots=[root],
        dry_run=True,
    )

    assert result.plan_node_seeded_count > 0
    assert result.dry_run is True
    assert household.psi4demand[0][0] == before_household
    assert producer.psi4demand[39][3] == before_producer


def test_missing_node_is_recorded_and_skipped():
    dataset = build_default_rice_case_dataset()
    root, _, household, _ = _build_real_like_tree()
    # Remove producer to force missing node behavior for supply rows.
    root.children = [household]

    result = seed_rice_weekly_input_to_real_like_plan_tree(
        case_data=dataset,
        product_name="PACKAGED_RICE_STANDARD",
        roots=[root],
        dry_run=False,
    )

    assert "PRODUCER_NIIGATA" in result.missing_node_ids
    assert result.plan_node_seeded_count > 0


def test_psi_buckets_contain_lot_id_lists_not_numeric_quantities():
    dataset = build_default_rice_case_dataset()
    root, producer, household, _ = _build_real_like_tree()

    seed_rice_weekly_input_to_real_like_plan_tree(
        case_data=dataset,
        product_name="PACKAGED_RICE_STANDARD",
        roots=[root],
        dry_run=False,
    )

    demand_bucket = household.psi4demand[0][0]
    supply_as_demand_bucket = producer.psi4demand[39][3]

    assert isinstance(demand_bucket, list)
    assert isinstance(supply_as_demand_bucket, list)
    assert all(isinstance(item, str) for item in demand_bucket)
    assert all(isinstance(item, str) for item in supply_as_demand_bucket)
    assert not any(isinstance(item, (int, float)) for item in demand_bucket)
    assert not any(isinstance(item, (int, float)) for item in supply_as_demand_bucket)


def test_rice_weekly_rows_present_for_expected_seed_mapping_types():
    dataset = build_default_rice_case_dataset()
    rows = build_rice_weekly_plan_rows(dataset)
    assert any(row.plan_type == "demand" for row in rows)
    assert any(row.plan_type == "supply" for row in rows)
