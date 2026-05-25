from __future__ import annotations

from dataclasses import dataclass

from pysi.cases.japanese_rice.rice_case_dataset import PRODUCT_ID, RiceCaseDataset


@dataclass(frozen=True)
class RiceExecutablePlanInput:
    scenario_id: str
    weeks: list[str]
    weekly_supply_qty: dict[str, float]
    weekly_supply_by_crop_year: dict[str, dict[int, float]]
    weekly_demand_qty: dict[str, float]
    storage_capacity: float
    milling_capacity: float
    transport_capacity: float
    cost_price: dict[str, float]
    main_evaluation_year: int
    initial_inventory_by_crop_year: dict[int, float]


@dataclass(frozen=True)
class RiceWeekResult:
    week: str
    P: float
    S: float
    I: float
    P_by_crop_year: dict[int, float]
    S_by_crop_year: dict[int, float]
    I_by_crop_year: dict[int, float]
    storage_capacity: float
    storage_utilization: float
    milling_utilization: float
    transport_utilization: float
    overflow_inventory: float


def adapt_rice_case_to_executable(dataset: RiceCaseDataset) -> RiceExecutablePlanInput:
    weekly_supply_qty = {week: 0.0 for week in dataset.weeks}
    weekly_supply_by_crop_year = {week: {} for week in dataset.weeks}
    weekly_demand_qty = {week: 0.0 for week in dataset.weeks}

    for row in dataset.supply_plan:
        weekly_supply_qty[row.week] = weekly_supply_qty.get(row.week, 0.0) + row.supply_qty
        weekly_supply_by_crop_year.setdefault(row.week, {})[row.crop_year] = (
            weekly_supply_by_crop_year.setdefault(row.week, {}).get(row.crop_year, 0.0) + row.supply_qty
        )

    for row in dataset.demand_plan:
        weekly_demand_qty[row.week] = weekly_demand_qty.get(row.week, 0.0) + row.demand_qty

    return RiceExecutablePlanInput(
        scenario_id=dataset.scenario_id,
        weeks=dataset.weeks,
        weekly_supply_qty=weekly_supply_qty,
        weekly_supply_by_crop_year=weekly_supply_by_crop_year,
        weekly_demand_qty=weekly_demand_qty,
        storage_capacity=dataset.storage_capacity,
        milling_capacity=dataset.milling_capacity,
        transport_capacity=dataset.transport_capacity,
        cost_price=dataset.cost_price,
        main_evaluation_year=dataset.main_evaluation_year,
        initial_inventory_by_crop_year=dataset.initial_inventory_by_crop_year,
    )


def run_weekly_psi_simulation(plan: RiceExecutablePlanInput) -> list[RiceWeekResult]:
    inventory_by_crop_year: dict[int, float] = dict(plan.initial_inventory_by_crop_year)
    results: list[RiceWeekResult] = []

    for week in plan.weeks:
        p_by_crop_year = dict(plan.weekly_supply_by_crop_year.get(week, {}))
        for crop_year, p_qty in p_by_crop_year.items():
            inventory_by_crop_year[crop_year] = inventory_by_crop_year.get(crop_year, 0.0) + p_qty

        available_inventory = sum(inventory_by_crop_year.values())
        s_candidate = plan.weekly_demand_qty.get(week, 0.0)
        s_limited_milling = min(s_candidate, plan.milling_capacity)
        s_limited_transport = min(s_limited_milling, plan.transport_capacity)
        s_qty = min(available_inventory, s_limited_transport)

        remaining_to_ship = s_qty
        s_by_crop_year: dict[int, float] = {}
        for crop_year in sorted(inventory_by_crop_year.keys()):
            if remaining_to_ship <= 0:
                break
            draw = min(inventory_by_crop_year[crop_year], remaining_to_ship)
            if draw > 0:
                inventory_by_crop_year[crop_year] -= draw
                s_by_crop_year[crop_year] = draw
                remaining_to_ship -= draw

        i_total = sum(inventory_by_crop_year.values())
        overflow = max(0.0, i_total - plan.storage_capacity)

        results.append(
            RiceWeekResult(
                week=week,
                P=sum(p_by_crop_year.values()),
                S=s_qty,
                I=i_total,
                P_by_crop_year=p_by_crop_year,
                S_by_crop_year=s_by_crop_year,
                I_by_crop_year=dict(inventory_by_crop_year),
                storage_capacity=plan.storage_capacity,
                storage_utilization=(i_total / plan.storage_capacity) if plan.storage_capacity > 0 else 0.0,
                milling_utilization=(s_qty / plan.milling_capacity) if plan.milling_capacity > 0 else 0.0,
                transport_utilization=(s_qty / plan.transport_capacity) if plan.transport_capacity > 0 else 0.0,
                overflow_inventory=overflow,
            )
        )

    return results


def summarize_costs(plan: RiceExecutablePlanInput, weekly: list[RiceWeekResult]) -> dict[str, float]:
    shipped_qty = sum(row.S for row in weekly)
    total_supply = sum(row.P for row in weekly)
    total_storage_cost = sum(row.I * plan.cost_price["storage_cost_per_lot_week"] for row in weekly)

    revenue = shipped_qty * plan.cost_price["selling_price_per_lot"]
    purchase_cost = total_supply * plan.cost_price["purchase_cost_per_lot"]
    milling_cost = shipped_qty * plan.cost_price["milling_cost_per_lot"]
    transport_cost = shipped_qty * plan.cost_price["transport_cost_per_lot"]
    ending_inventory_value = weekly[-1].I * plan.cost_price["purchase_cost_per_lot"] if weekly else 0.0
    gross_profit = revenue - purchase_cost - total_storage_cost - milling_cost - transport_cost

    return {
        "total_revenue": revenue,
        "total_purchase_cost": purchase_cost,
        "total_storage_cost": total_storage_cost,
        "total_milling_cost": milling_cost,
        "total_transport_cost": transport_cost,
        "gross_profit": gross_profit,
        "ending_inventory_value": ending_inventory_value,
    }


def summarize_kpis(plan: RiceExecutablePlanInput, weekly: list[RiceWeekResult], costs: dict[str, float]) -> dict[str, float]:
    total_supply = sum(row.P for row in weekly)
    total_demand = sum(plan.weekly_demand_qty.get(w, 0.0) for w in plan.weeks)
    total_shipped = sum(row.S for row in weekly)
    ending_inventory = weekly[-1].I if weekly else 0.0
    peak_inventory = max((row.I for row in weekly), default=0.0)
    peak_storage_util = max((row.storage_utilization for row in weekly), default=0.0)
    fill_rate = (total_shipped / total_demand) if total_demand > 0 else 0.0
    margin = (costs["gross_profit"] / costs["total_revenue"]) if costs["total_revenue"] > 0 else 0.0
    ending_by_crop = weekly[-1].I_by_crop_year if weekly else {}

    return {
        "total_supply_qty": total_supply,
        "total_demand_qty": total_demand,
        "total_shipped_qty": total_shipped,
        "ending_inventory_qty": ending_inventory,
        "peak_inventory_qty": peak_inventory,
        "fill_rate": fill_rate,
        "peak_storage_utilization": peak_storage_util,
        "gross_profit": costs["gross_profit"],
        "profit_margin": margin,
        "ending_inventory_2025_crop": ending_by_crop.get(2025, 0.0),
        "ending_inventory_2026_crop": ending_by_crop.get(2026, 0.0),
        "ending_inventory_2027_crop": ending_by_crop.get(2027, 0.0),
        "main_evaluation_year": float(plan.main_evaluation_year),
    }


__all__ = [
    "PRODUCT_ID",
    "RiceExecutablePlanInput",
    "RiceWeekResult",
    "adapt_rice_case_to_executable",
    "run_weekly_psi_simulation",
    "summarize_costs",
    "summarize_kpis",
]
