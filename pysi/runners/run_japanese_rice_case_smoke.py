from __future__ import annotations

import csv
from pathlib import Path

from pysi.cases.japanese_rice import (
    PRODUCT_ID,
    adapt_rice_case_to_executable,
    build_default_rice_case_dataset,
    run_weekly_psi_simulation,
    summarize_costs,
    summarize_kpis,
)


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_smoke(output_dir: Path | None = None) -> dict[str, object]:
    dataset = build_default_rice_case_dataset()
    plan = adapt_rice_case_to_executable(dataset)
    weekly = run_weekly_psi_simulation(plan)
    costs = summarize_costs(plan, weekly)
    kpis = summarize_kpis(plan, weekly, costs)

    out_dir = output_dir or Path("outputs/japanese_rice")

    psi_rows = [
        {
            "scenario_id": dataset.scenario_id,
            "week": w.week,
            "product_id": PRODUCT_ID,
            "P": w.P,
            "S": w.S,
            "I": w.I,
            "storage_capacity": w.storage_capacity,
            "storage_utilization": w.storage_utilization,
            "milling_capacity": plan.milling_capacity,
            "transport_capacity": plan.transport_capacity,
        }
        for w in weekly
    ]
    _write_csv(
        out_dir / "rice_psi_summary.csv",
        psi_rows,
        [
            "scenario_id",
            "week",
            "product_id",
            "P",
            "S",
            "I",
            "storage_capacity",
            "storage_utilization",
            "milling_capacity",
            "transport_capacity",
        ],
    )

    inventory_rows: list[dict[str, object]] = []
    for week_result in weekly:
        for crop_year in (2025, 2026, 2027):
            p = week_result.P_by_crop_year.get(crop_year, 0.0)
            s = week_result.S_by_crop_year.get(crop_year, 0.0)
            i = week_result.I_by_crop_year.get(crop_year, 0.0)
            inventory_rows.append(
                {
                    "scenario_id": dataset.scenario_id,
                    "week": week_result.week,
                    "product_id": PRODUCT_ID,
                    "crop_year": crop_year,
                    "P": p,
                    "S": s,
                    "I": i,
                    "inventory_value": i * dataset.cost_price["purchase_cost_per_lot"],
                    "comment": "Crop-year inventory tracking (FIFO by crop_year)",
                }
            )
    _write_csv(
        out_dir / "rice_inventory_by_crop_year.csv",
        inventory_rows,
        ["scenario_id", "week", "product_id", "crop_year", "P", "S", "I", "inventory_value", "comment"],
    )

    cost_rows = [
        {
            "scenario_id": dataset.scenario_id,
            "metric": metric,
            "value": value,
            "currency": "JPY",
            "comment": "MVP simplified assumption",
        }
        for metric, value in costs.items()
    ]
    _write_csv(
        out_dir / "rice_cost_summary.csv",
        cost_rows,
        ["scenario_id", "metric", "value", "currency", "comment"],
    )

    kpi_rows = [
        {
            "scenario_id": dataset.scenario_id,
            "kpi_id": kpi,
            "value": value,
            "unit": "year" if kpi == "main_evaluation_year" else "ratio" if "rate" in kpi or "margin" in kpi or "utilization" in kpi else "lot",
            "comment": "MVP KPI",
        }
        for kpi, value in kpis.items()
    ]
    _write_csv(
        out_dir / "rice_kpi_summary.csv",
        kpi_rows,
        ["scenario_id", "kpi_id", "value", "unit", "comment"],
    )

    return {"dataset": dataset, "plan": plan, "weekly": weekly, "costs": costs, "kpis": kpis, "output_dir": out_dir}


def main() -> None:
    result = run_smoke()
    dataset = result["dataset"]
    weekly = result["weekly"]
    costs = result["costs"]
    kpis = result["kpis"]

    print("=== Japanese Rice Case smoke v2 ===")
    print(f"scenario: {dataset.scenario_id}")
    print(f"product: {PRODUCT_ID}")
    print(f"horizon: {dataset.weeks[0]}..{dataset.weeks[-1]}")
    print(f"main evaluation year: {dataset.main_evaluation_year}\n")
    print("crop cycles:")
    print("  2025 crop carryover: 80.0 lots")
    print("  2026 crop harvest: 100.0 lots")
    print("  2027 crop harvest: 100.0 lots\n")
    print("demand:")
    print("  weekly demand: 1.6 lots")
    print(f"  total demand over horizon: {kpis['total_demand_qty']:.1f} lots")
    print(f"  2027 demand: {1.6 * 52:.1f} lots\n")

    ending = weekly[-1].I_by_crop_year
    print("inventory by crop year:")
    print(f"  ending 2025 crop inventory: {ending.get(2025, 0.0):.1f} lots")
    print(f"  ending 2026 crop inventory: {ending.get(2026, 0.0):.1f} lots")
    print(f"  ending 2027 crop inventory: {ending.get(2027, 0.0):.1f} lots\n")

    y2027 = [r for r in weekly if r.week.startswith("2027-")]
    consumed_2026_before_w40 = sum(r.S_by_crop_year.get(2026, 0.0) for r in y2027 if r.week <= "2027-W40")
    consumed_2027_after_w41 = sum(r.S_by_crop_year.get(2027, 0.0) for r in y2027 if r.week >= "2027-W41")
    end_2027 = next(r for r in weekly if r.week == "2027-W52").I

    print("2027 evaluation:")
    print(f"  2026 crop consumed before W40: {consumed_2026_before_w40:.1f} lots")
    print("  2027 crop harvested W40-W44: 100.0 lots")
    print(f"  2027 crop consumed after W41: {consumed_2027_after_w41:.1f} lots")
    print(f"  ending inventory at 2027-W52: {end_2027:.1f} lots\n")

    print("money:")
    print(f"  total revenue: {costs['total_revenue']:.0f} JPY")
    print(f"  total storage cost: {costs['total_storage_cost']:.0f} JPY")
    print(f"  total gross profit: {costs['gross_profit']:.0f} JPY\n")
    print("KPI:")
    print(f"  fill rate: {kpis['fill_rate'] * 100:.1f}%")
    print(f"  peak storage utilization: {kpis['peak_storage_utilization'] * 100:.1f}%")


if __name__ == "__main__":
    main()
