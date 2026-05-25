from __future__ import annotations

from dataclasses import dataclass, field

from pysi.adapters.lot_generation import LotHeader
from pysi.adapters.plan_node_seeding import PlanNodeSeedingResult, apply_psi_seed_records_to_plan_nodes
from pysi.adapters.psi_seed import PsiSeedRecord, generate_psi_seed_records
from pysi.adapters.weekly_plan_table import WeeklyPlanRow
from pysi.cases.japanese_rice.rice_case_dataset import RiceCaseDataset


@dataclass
class MockPlanNode:
    name: str
    psi4demand: list
    psi4supply: list


@dataclass
class RicePlanInputSeedResult:
    weekly_rows_count: int
    lot_count: int
    seed_record_count: int
    plan_node_seeded_count: int
    demand_s_count: int
    supply_p_count: int
    weeks_seeded: list[str]
    missing_node_ids: list[str] = field(default_factory=list)
    invalid_weeks: list[dict] = field(default_factory=list)
    lot_headers: list[LotHeader] = field(default_factory=list)
    seed_records: list[PsiSeedRecord] = field(default_factory=list)
    plan_nodes: dict[str, MockPlanNode] = field(default_factory=dict)
    seeding_result: PlanNodeSeedingResult | None = None


def make_mock_plan_node(name: str, weeks: int) -> MockPlanNode:
    return MockPlanNode(
        name=name,
        psi4demand=[[[], [], [], []] for _ in range(weeks)],
        psi4supply=[[[], [], [], []] for _ in range(weeks)],
    )


def build_rice_week_indexer(start_year: int = 2026, end_year: int = 2028) -> dict[str, int]:
    if end_year < start_year:
        raise ValueError("end_year must be >= start_year")

    indexer: dict[str, int] = {}
    index = 0
    for year in range(start_year, end_year + 1):
        for week in range(1, 53):
            indexer[f"{year}-W{week:02d}"] = index
            index += 1
    return indexer


def build_rice_weekly_plan_rows(case_data: RiceCaseDataset) -> list[WeeklyPlanRow]:
    rows: list[WeeklyPlanRow] = []

    for demand in case_data.demand_plan:
        rows.append(
            WeeklyPlanRow(
                scenario_id=demand.scenario_id,
                product_id=demand.product_id,
                node_id=demand.demand_node_id,
                week=demand.week,
                plan_type="demand",
                quantity=demand.demand_qty,
                source_granularity="case_weekly",
                source_id="rice_demand_plan",
                comment=demand.comment,
            )
        )

    for supply in case_data.supply_plan:
        rows.append(
            WeeklyPlanRow(
                scenario_id=supply.scenario_id,
                product_id=supply.product_id,
                node_id=supply.node_id,
                week=supply.week,
                plan_type="supply",
                quantity=supply.supply_qty,
                source_granularity="case_weekly",
                source_id="rice_supply_plan",
                comment=supply.comment,
            )
        )

    return rows


def build_rice_row_attributes(rows: list[WeeklyPlanRow]) -> dict[int, dict]:
    attrs: dict[int, dict] = {}
    for idx, row in enumerate(rows):
        if row.source_id != "rice_supply_plan":
            continue

        year_str, week_str = row.week.split("-W")
        crop_year = int(year_str)
        harvest_week_no = int(week_str)
        available_week_no = min(harvest_week_no + 1, 52)
        attrs[idx] = {
            "crop_year": str(crop_year),
            "harvest_week": row.week,
            "available_week": f"{crop_year}-W{available_week_no:02d}",
            "quality_limit_week": f"{crop_year + 1}-W{harvest_week_no:02d}",
        }
    return attrs


def seed_rice_weekly_rows_to_mock_plan_nodes(
    rows: list[WeeklyPlanRow],
    *,
    week_indexer: dict[str, int],
) -> RicePlanInputSeedResult:
    row_attributes = build_rice_row_attributes(rows)
    lot_headers, seed_records = generate_psi_seed_records(rows, row_attributes=row_attributes)

    node_ids = sorted({row.node_id for row in rows})
    plan_nodes = {node_id: make_mock_plan_node(node_id, weeks=len(week_indexer)) for node_id in node_ids}

    seeding_result = apply_psi_seed_records_to_plan_nodes(
        seed_records,
        plan_node_lookup=plan_nodes,
        week_indexer=week_indexer,
    )

    demand_s_count = sum(1 for r in seed_records if r.layer == "demand" and r.bucket == "S")
    supply_p_count = sum(1 for r in seed_records if r.layer == "demand" and r.bucket == "P")

    return RicePlanInputSeedResult(
        weekly_rows_count=len(rows),
        lot_count=len(lot_headers),
        seed_record_count=len(seed_records),
        plan_node_seeded_count=seeding_result.seeded_count,
        demand_s_count=demand_s_count,
        supply_p_count=supply_p_count,
        weeks_seeded=sorted({r.week for r in seed_records}),
        missing_node_ids=seeding_result.missing_node_ids,
        invalid_weeks=seeding_result.invalid_weeks,
        lot_headers=lot_headers,
        seed_records=seed_records,
        plan_nodes=plan_nodes,
        seeding_result=seeding_result,
    )
