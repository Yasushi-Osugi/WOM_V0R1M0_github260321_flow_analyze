from dataclasses import dataclass, field
from typing import Any

from pysi.cases.japanese_rice import (
    build_default_rice_case_dataset,
    build_rice_week_indexer,
)
from pysi.cases.japanese_rice.rice_actual_prod_tree_seed_integration import (
    build_plan_node_lookup_from_roots,
    build_plan_node_lookup_from_tree,
    resolve_product_plan_roots,
    seed_rice_weekly_input_to_actual_product_plan_nodes,
)


@dataclass
class _Node:
    name: str
    children: list[Any] = field(default_factory=list)
    psi4demand: list = field(default_factory=list)
    psi4supply: list = field(default_factory=list)


def _make_node(name: str, weeks: int = 156) -> _Node:
    return _Node(
        name=name,
        children=[],
        psi4demand=[[[], [], [], []] for _ in range(weeks)],
        psi4supply=[[[], [], [], []] for _ in range(weeks)],
    )


def _build_actual_like_roots(weeks: int = 156) -> tuple[_Node, _Node, _Node, _Node]:
    root = _make_node("ROOT_RICE", weeks)
    producer = _make_node("PRODUCER_NIIGATA", weeks)
    household = _make_node("DEMAND_HOUSEHOLD_TOKYO", weeks)
    food_service = _make_node("DEMAND_FOOD_SERVICE_TOKYO", weeks)
    root.children.extend([producer, household, food_service])
    inbound_root = _make_node("INBOUND_ROOT_RICE", weeks)
    inbound_root.children.append(_make_node("INBOUND_WAREHOUSE_TOKYO", weeks))
    return root, inbound_root, producer, household


def test_resolve_product_plan_roots_with_explicit_roots():
    out_root = object()
    in_root = object()
    resolved_out, resolved_in = resolve_product_plan_roots(
        product_name="PACKAGED_RICE_STANDARD",
        outbound_root=out_root,
        inbound_root=in_root,
    )
    assert resolved_out is out_root
    assert resolved_in is in_root


def test_resolve_product_plan_roots_with_product_dicts():
    out_root = object()
    in_root = object()
    resolved_out, resolved_in = resolve_product_plan_roots(
        product_name="PACKAGED_RICE_STANDARD",
        prod_tree_dict_OT={"PACKAGED_RICE_STANDARD": out_root},
        prod_tree_dict_IN={"PACKAGED_RICE_STANDARD": in_root},
    )
    assert resolved_out is out_root
    assert resolved_in is in_root


def test_build_plan_node_lookup_from_actual_like_roots():
    out_root, in_root, producer, household = _build_actual_like_roots()
    tree_lookup = build_plan_node_lookup_from_tree(out_root)
    assert tree_lookup["PRODUCER_NIIGATA"] is producer
    assert tree_lookup["DEMAND_HOUSEHOLD_TOKYO"] is household

    lookup, duplicates = build_plan_node_lookup_from_roots([out_root, in_root])
    assert "ROOT_RICE" in lookup
    assert "INBOUND_ROOT_RICE" in lookup
    assert duplicates == []


def test_rice_weekly_input_seeds_actual_product_specific_plan_nodes_and_preserves_w40_w41():
    dataset = build_default_rice_case_dataset()
    out_root, in_root, producer, household = _build_actual_like_roots()

    result = seed_rice_weekly_input_to_actual_product_plan_nodes(
        case_data=dataset,
        product_name="PACKAGED_RICE_STANDARD",
        outbound_root=out_root,
        inbound_root=in_root,
        dry_run=False,
    )

    week_indexer = build_rice_week_indexer(2026, 2028)
    assert week_indexer["2026-W40"] == 39
    assert week_indexer["2026-W41"] == 40
    assert result.plan_node_seeded_count > 0
    assert result.missing_roots == []
    assert result.missing_node_ids == []

    assert household.psi4demand[0][0]
    assert producer.psi4demand[39][3]
    assert producer.psi4demand[40][3]


def test_dry_run_does_not_mutate_actual_product_specific_roots():
    dataset = build_default_rice_case_dataset()
    out_root, in_root, producer, household = _build_actual_like_roots()

    before_household = list(household.psi4demand[0][0])
    before_producer = list(producer.psi4demand[39][3])

    result = seed_rice_weekly_input_to_actual_product_plan_nodes(
        case_data=dataset,
        product_name="PACKAGED_RICE_STANDARD",
        outbound_root=out_root,
        inbound_root=in_root,
        dry_run=True,
    )

    assert result.plan_node_seeded_count > 0
    assert household.psi4demand[0][0] == before_household
    assert producer.psi4demand[39][3] == before_producer


def test_missing_root_is_reported_and_seeding_is_skipped():
    dataset = build_default_rice_case_dataset()
    out_root, _, _, _ = _build_actual_like_roots()

    result = seed_rice_weekly_input_to_actual_product_plan_nodes(
        case_data=dataset,
        product_name="PACKAGED_RICE_STANDARD",
        outbound_root=out_root,
        inbound_root=None,
        dry_run=False,
    )

    assert "inbound_root" in result.missing_roots
    assert result.plan_node_seeded_count == 0


def test_missing_node_is_reported():
    dataset = build_default_rice_case_dataset()
    out_root, in_root, _, household = _build_actual_like_roots()
    out_root.children = [household]

    result = seed_rice_weekly_input_to_actual_product_plan_nodes(
        case_data=dataset,
        product_name="PACKAGED_RICE_STANDARD",
        outbound_root=out_root,
        inbound_root=in_root,
        dry_run=False,
    )

    assert "PRODUCER_NIIGATA" in result.missing_node_ids


def test_psi_buckets_contain_lot_id_lists_not_quantities():
    dataset = build_default_rice_case_dataset()
    out_root, in_root, producer, household = _build_actual_like_roots()

    seed_rice_weekly_input_to_actual_product_plan_nodes(
        case_data=dataset,
        product_name="PACKAGED_RICE_STANDARD",
        outbound_root=out_root,
        inbound_root=in_root,
        dry_run=False,
    )

    demand_bucket = household.psi4demand[0][0]
    supply_as_demand_bucket = producer.psi4demand[39][3]

    assert isinstance(demand_bucket, list)
    assert isinstance(supply_as_demand_bucket, list)
    assert all(isinstance(item, str) for item in demand_bucket)
    assert all(isinstance(item, str) for item in supply_as_demand_bucket)
