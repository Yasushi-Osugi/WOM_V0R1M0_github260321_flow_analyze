from __future__ import annotations

from pathlib import Path

from pysi.cases.japanese_rice import adapt_rice_case_to_executable, build_default_rice_case_dataset, run_weekly_psi_simulation
from pysi.runners.run_japanese_rice_case_smoke import run_smoke


def test_rice_case_smoke_v2(tmp_path: Path) -> None:
    dataset = build_default_rice_case_dataset()
    assert len(dataset.weeks) == 156
    assert dataset.weeks[0] == "2026-W01"
    assert dataset.weeks[-1] == "2028-W52"
    assert dataset.main_evaluation_year == 2027

    plan = adapt_rice_case_to_executable(dataset)
    assert len(plan.weekly_demand_qty) == 156
    assert all(v == 1.6 for v in plan.weekly_demand_qty.values())
    assert plan.initial_inventory_by_crop_year[2025] == 80.0

    assert sum(q.get(2026, 0.0) for q in plan.weekly_supply_by_crop_year.values()) == 100.0
    assert sum(q.get(2027, 0.0) for q in plan.weekly_supply_by_crop_year.values()) == 100.0

    weekly = run_weekly_psi_simulation(plan)
    assert all(x.I >= 0 for x in weekly)
    assert all(v >= 0 for w in weekly for v in w.I_by_crop_year.values())

    w1 = next(x for x in weekly if x.week == "2026-W01")
    w40_2026 = next(x for x in weekly if x.week == "2026-W40")
    assert w1.I_by_crop_year.get(2025, 0.0) > w40_2026.I_by_crop_year.get(2025, 0.0)

    inv_2026_during_2027 = [x.I_by_crop_year.get(2026, 0.0) for x in weekly if "2027-W01" <= x.week <= "2027-W40"]
    assert any(v > 0 for v in inv_2026_during_2027)

    w40_2027 = next(x for x in weekly if x.week == "2027-W40")
    assert w40_2027.P_by_crop_year.get(2027, 0.0) == 20.0

    pre_w41_2027_consumption = sum(x.S_by_crop_year.get(2027, 0.0) for x in weekly if x.week <= "2027-W40")
    assert pre_w41_2027_consumption == 0.0

    result = run_smoke(output_dir=tmp_path / "japanese_rice")
    out_dir = result["output_dir"]
    assert (out_dir / "rice_inventory_by_crop_year.csv").exists()
    assert (out_dir / "rice_psi_summary.csv").exists()
    assert (out_dir / "rice_cost_summary.csv").exists()
    assert (out_dir / "rice_kpi_summary.csv").exists()
