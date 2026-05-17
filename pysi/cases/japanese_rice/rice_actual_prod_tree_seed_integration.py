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
class RiceActualPlanNodeSeedResult:
    scenario_id: str
    product_name: str
    weekly_rows_count: int = 0
    lot_count: int = 0
    seed_record_count: int = 0
    plan_node_seeded_count: int = 0
    missing_roots: list[str] = field(default_factory=list)
    missing_node_ids: list[str] = field(default_factory=list)
    duplicate_node_ids: list[str] = field(default_factory=list)
    invalid_weeks: list[dict] = field(default_factory=list)
    dry_run: bool = True
    seeding_result: PlanNodeSeedingResult | None = None


def resolve_product_plan_roots(
    *,
    product_name: str,
    prod_tree_dict_OT: dict | None = None,
    prod_tree_dict_IN: dict | None = None,
    outbound_root=None,
    inbound_root=None,
) -> tuple[object | None, object | None]:
    resolved_outbound = outbound_root
    resolved_inbound = inbound_root

    if resolved_outbound is None and prod_tree_dict_OT is not None:
        resolved_outbound = prod_tree_dict_OT.get(product_name)
    if resolved_inbound is None and prod_tree_dict_IN is not None:
        resolved_inbound = prod_tree_dict_IN.get(product_name)

    return resolved_outbound, resolved_inbound


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


def build_plan_node_lookup_from_roots(roots: list[Any]) -> tuple[dict[str, Any], list[str]]:
    lookup: dict[str, Any] = {}
    duplicates: list[str] = []

    for root in roots:
        if root is None:
            continue

        tree_lookup = build_plan_node_lookup_from_tree(root)
        for node_id, node in tree_lookup.items():
            if node_id in lookup:
                if node_id not in duplicates:
                    duplicates.append(node_id)
                continue
            lookup[node_id] = node

    return lookup, duplicates


def seed_rice_weekly_input_to_actual_product_plan_nodes(
    *,
    case_data: RiceCaseDataset,
    product_name: str,
    prod_tree_dict_OT: dict | None = None,
    prod_tree_dict_IN: dict | None = None,
    outbound_root=None,
    inbound_root=None,
    dry_run: bool = True,
) -> RiceActualPlanNodeSeedResult:
    rows = build_rice_weekly_plan_rows(case_data)
    row_attributes = build_rice_row_attributes(rows)
    lot_headers, seed_records, _ = weekly_rows_to_lots_and_seed_table(rows, row_attributes=row_attributes)

    resolved_outbound, resolved_inbound = resolve_product_plan_roots(
        product_name=product_name,
        prod_tree_dict_OT=prod_tree_dict_OT,
        prod_tree_dict_IN=prod_tree_dict_IN,
        outbound_root=outbound_root,
        inbound_root=inbound_root,
    )

    missing_roots: list[str] = []
    if resolved_outbound is None:
        missing_roots.append("outbound_root")
    if resolved_inbound is None:
        missing_roots.append("inbound_root")

    scenario_id = seed_records[0].scenario_id if seed_records else ""
    if missing_roots:
        return RiceActualPlanNodeSeedResult(
            scenario_id=scenario_id,
            product_name=product_name,
            weekly_rows_count=len(rows),
            lot_count=len(lot_headers),
            seed_record_count=len(seed_records),
            missing_roots=missing_roots,
            dry_run=dry_run,
        )

    plan_node_lookup, duplicates = build_plan_node_lookup_from_roots([resolved_outbound, resolved_inbound])
    week_indexer = build_rice_week_indexer(2026, 2028)
    seeding_result = apply_psi_seed_records_to_plan_nodes(
        seed_records,
        plan_node_lookup=plan_node_lookup,
        week_indexer=week_indexer,
        dry_run=dry_run,
    )

    return RiceActualPlanNodeSeedResult(
        scenario_id=scenario_id,
        product_name=product_name,
        weekly_rows_count=len(rows),
        lot_count=len(lot_headers),
        seed_record_count=len(seed_records),
        plan_node_seeded_count=seeding_result.seeded_count,
        missing_roots=missing_roots,
        missing_node_ids=seeding_result.missing_node_ids,
        duplicate_node_ids=duplicates,
        invalid_weeks=seeding_result.invalid_weeks,
        dry_run=dry_run,
        seeding_result=seeding_result,
    )
