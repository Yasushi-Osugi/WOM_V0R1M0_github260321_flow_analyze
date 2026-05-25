from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pysi.adapters.plan_input_pipeline import weekly_rows_to_lots_and_seed_table
from pysi.adapters.plan_node_seeding import PlanNodeSeedingResult, apply_psi_seed_records_to_plan_nodes
from pysi.cases.japanese_rice.rice_case_dataset import RiceCaseDataset
from pysi.cases.japanese_rice.rice_plan_input_integration import (
    build_rice_row_attributes,
    build_rice_week_indexer,
    build_rice_weekly_plan_rows,
)


@dataclass
class RealLikePlanNode:
    name: str
    children: list[Any] = field(default_factory=list)
    psi4demand: list = field(default_factory=list)
    psi4supply: list = field(default_factory=list)


@dataclass
class RiceRealPlanNodeSeedResult:
    scenario_id: str
    product_name: str
    weekly_rows_count: int = 0
    lot_count: int = 0
    seed_record_count: int = 0
    plan_node_seeded_count: int = 0
    missing_node_ids: list[str] = field(default_factory=list)
    invalid_weeks: list[dict] = field(default_factory=list)
    dry_run: bool = True
    seeding_result: PlanNodeSeedingResult | None = None


def make_real_like_plan_node(name: str, weeks: int) -> RealLikePlanNode:
    return RealLikePlanNode(
        name=name,
        children=[],
        psi4demand=[[[], [], [], []] for _ in range(weeks)],
        psi4supply=[[[], [], [], []] for _ in range(weeks)],
    )


def build_plan_node_lookup_from_tree(root: Any) -> dict[str, Any]:
    lookup: dict[str, Any] = {}

    def _walk(node: Any) -> None:
        node_name = getattr(node, "name", None)
        if node_name is not None and node_name not in lookup:
            lookup[node_name] = node
        for child in getattr(node, "children", []) or []:
            _walk(child)

    _walk(root)
    return lookup


def build_plan_node_lookup_from_roots(roots: list[Any]) -> dict[str, Any]:
    lookup: dict[str, Any] = {}
    for root in roots:
        tree_lookup = build_plan_node_lookup_from_tree(root)
        for name, node in tree_lookup.items():
            if name not in lookup:
                lookup[name] = node
    return lookup


def seed_rice_weekly_input_to_real_like_plan_tree(
    *,
    case_data: RiceCaseDataset,
    product_name: str,
    roots: list[Any],
    dry_run: bool = True,
) -> RiceRealPlanNodeSeedResult:
    rows = build_rice_weekly_plan_rows(case_data)
    row_attributes = build_rice_row_attributes(rows)
    lot_headers, seed_records, _ = weekly_rows_to_lots_and_seed_table(rows, row_attributes=row_attributes)
    week_indexer = build_rice_week_indexer(2026, 2028)
    plan_node_lookup = build_plan_node_lookup_from_roots(roots)

    seeding_result = apply_psi_seed_records_to_plan_nodes(
        seed_records,
        plan_node_lookup=plan_node_lookup,
        week_indexer=week_indexer,
        dry_run=dry_run,
    )

    scenario_id = seed_records[0].scenario_id if seed_records else ""
    return RiceRealPlanNodeSeedResult(
        scenario_id=scenario_id,
        product_name=product_name,
        weekly_rows_count=len(rows),
        lot_count=len(lot_headers),
        seed_record_count=len(seed_records),
        plan_node_seeded_count=seeding_result.seeded_count,
        missing_node_ids=seeding_result.missing_node_ids,
        invalid_weeks=seeding_result.invalid_weeks,
        dry_run=dry_run,
        seeding_result=seeding_result,
    )
