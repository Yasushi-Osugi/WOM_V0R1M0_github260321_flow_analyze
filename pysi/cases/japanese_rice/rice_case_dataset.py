from __future__ import annotations

from dataclasses import dataclass


SCENARIO_ID = "RICE_AS_IS"
PRODUCT_ID = "PACKAGED_RICE_STANDARD"
MAIN_EVALUATION_YEAR = 2027
CROP_YEARS = (2025, 2026, 2027)


@dataclass(frozen=True)
class RiceSupplyPlanRow:
    scenario_id: str
    node_id: str
    product_id: str
    week: str
    supply_qty: float
    supply_type: str
    source_type: str
    crop_year: int
    comment: str = ""


@dataclass(frozen=True)
class RiceDemandPlanRow:
    scenario_id: str
    demand_node_id: str
    region: str
    product_id: str
    week: str
    demand_qty: float
    demand_type: str
    priority: int = 100
    comment: str = ""




@dataclass(frozen=True)
class RiceCostPrice:
    cost_price_type: str
    unit_value: float


@dataclass(frozen=True)
class RiceCaseDataset:
    scenario_id: str
    weeks: list[str]
    supply_plan: list[RiceSupplyPlanRow]
    demand_plan: list[RiceDemandPlanRow]
    cost_price: dict[str, float]
    storage_capacity: float
    milling_capacity: float
    transport_capacity: float
    main_evaluation_year: int
    initial_inventory_by_crop_year: dict[int, float]


def build_weeks(start_year: int = 2026, end_year: int = 2028) -> list[str]:
    return [f"{year}-W{week:02d}" for year in range(start_year, end_year + 1) for week in range(1, 53)]


def build_default_rice_case_dataset() -> RiceCaseDataset:
    weeks = build_weeks(2026, 2028)

    harvest_supply_by_crop_year = {
        2026: {
            "2026-W40": 20.0,
            "2026-W41": 30.0,
            "2026-W42": 30.0,
            "2026-W43": 15.0,
            "2026-W44": 5.0,
        },
        2027: {
            "2027-W40": 20.0,
            "2027-W41": 30.0,
            "2027-W42": 30.0,
            "2027-W43": 15.0,
            "2027-W44": 5.0,
        },
    }

    supply_plan: list[RiceSupplyPlanRow] = []
    for crop_year, harvest_weeks in harvest_supply_by_crop_year.items():
        for week, qty in harvest_weeks.items():
            supply_plan.append(
                RiceSupplyPlanRow(
                    scenario_id=SCENARIO_ID,
                    node_id="PRODUCER_NIIGATA",
                    product_id=PRODUCT_ID,
                    week=week,
                    supply_qty=qty,
                    supply_type="HARVEST",
                    source_type="DOMESTIC",
                    crop_year=crop_year,
                    comment="MVP fixed harvest supply pattern",
                )
            )

    demand_plan: list[RiceDemandPlanRow] = []
    for week in weeks:
        demand_plan.append(
            RiceDemandPlanRow(
                scenario_id=SCENARIO_ID,
                demand_node_id="DEMAND_HOUSEHOLD_TOKYO",
                region="TOKYO",
                product_id=PRODUCT_ID,
                week=week,
                demand_qty=1.0,
                demand_type="HOUSEHOLD",
                comment="MVP household demand",
            )
        )
        demand_plan.append(
            RiceDemandPlanRow(
                scenario_id=SCENARIO_ID,
                demand_node_id="DEMAND_FOOD_SERVICE_TOKYO",
                region="TOKYO",
                product_id=PRODUCT_ID,
                week=week,
                demand_qty=0.6,
                demand_type="FOOD_SERVICE",
                comment="MVP food service demand",
            )
        )

    # Modeling assumptions for MVP smoke only (not real market values)
    cost_price = {
        "purchase_cost_per_lot": 250_000.0,
        "storage_cost_per_lot_week": 5_000.0,
        "milling_cost_per_lot": 30_000.0,
        "transport_cost_per_lot": 20_000.0,
        "selling_price_per_lot": 500_000.0,
    }

    return RiceCaseDataset(
        scenario_id=SCENARIO_ID,
        weeks=weeks,
        supply_plan=supply_plan,
        demand_plan=demand_plan,
        cost_price=cost_price,
        storage_capacity=100.0,
        milling_capacity=5.0,
        transport_capacity=5.0,
        main_evaluation_year=MAIN_EVALUATION_YEAR,
        initial_inventory_by_crop_year={2025: 80.0, 2026: 0.0, 2027: 0.0},
    )
