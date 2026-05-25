# Codex Request: Implement Japanese Rice Case Smoke Runner v2 with Crop-Year Horizon

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following Rice Case design documents have already been added:

```text
docs/design/case_japanese_rice_supply_chain_as_is_research.md
docs/design/wom_case_modeling_base_dataset.md
docs/design/case_japanese_rice_supply_chain_modeling.md
docs/design/case_japanese_rice_master_dataset.md
docs/design/case_japanese_rice_simulation_plan.md
docs/design/case_japanese_rice_crop_year_modeling_addendum.md
```

The latest important addendum is:

```text
docs/design/case_japanese_rice_crop_year_modeling_addendum.md
```

Please read this addendum first.

The current Japanese Rice Case MVP already exists and includes:

```text
pysi/cases/japanese_rice/__init__.py
pysi/cases/japanese_rice/rice_case_dataset.py
pysi/cases/japanese_rice/rice_case_adapter.py
pysi/runners/run_japanese_rice_case_smoke.py
tests/test_japanese_rice_case_smoke.py
```

The current MVP uses a simplified 52-week horizon.

This request is to upgrade it to v2 using:

```text
3-year crop-cycle horizon
crop-year inventory tracking
2027 main evaluation summary
```

---

## 2. Main Objective

Implement **Japanese Rice Case smoke runner v2**.

The objective is to revise the current Rice Case MVP so that it models rice as a crop-year inventory cycle instead of a single calendar-year simulation.

The v2 smoke runner should show:

```text
2025 crop carryover inventory
    consumed during 2026-W01 to 2026-W40

2026 crop
    harvested during 2026-W40 to 2026-W44
    consumed mainly during 2026-W41 to 2027-W40

2027 crop
    harvested during 2027-W40 to 2027-W44
    consumed mainly during 2027-W41 to 2028-W40
```

The main evaluation year should be:

```text
2027
```

---

## 3. Key Modeling Principle

Rice should not be modeled only by calendar year.

Rice should be modeled by:

```text
crop_year
harvest_cohort
old_crop_inventory
new_crop_harvest
old_crop / new_crop transition
crop-year inventory drawdown
```

The correct boundary convention is:

```text
W40:
    old crop consumption final week
    new crop harvest start week

W41:
    new crop consumption start week
```

This means:

```text
2026-W40:
    2025 crop is still consumed
    2026 crop harvest starts

2026-W41:
    2026 crop becomes available for normal consumption
```

---

## 4. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify existing core WOM planners unless absolutely necessary.
3. Do not implement full Rice supply chain optimization.
4. Do not replace the existing Rice MVP with a large complex model.
5. Keep this as a deterministic smoke runner / adapter v2.
6. Preserve the current v1 smoke runner behavior where practical.
7. Add focused tests.
8. Do not implement Management Issue Generation yet.
9. Do not implement LLM summarization.
```

This request is only for:

```text
Rice Case smoke runner v2 with crop-year inventory tracking
```

---

## 5. Files to Update

Please update existing files:

```text
pysi/cases/japanese_rice/rice_case_dataset.py
pysi/cases/japanese_rice/rice_case_adapter.py
pysi/runners/run_japanese_rice_case_smoke.py
tests/test_japanese_rice_case_smoke.py
```

Optional, only if useful:

```text
pysi/runners/run_japanese_rice_case_smoke_v2.py
tests/test_japanese_rice_case_smoke_v2.py
```

Preferred approach:

```text
Keep the existing runner name if changes remain backward-compatible.
```

If the v2 behavior substantially changes expected output, adding a new v2 runner is acceptable.

---

## 6. Horizon Definition

The v2 simulation should use:

```text
planning horizon:
    2026-W01 to 2028-W52

main evaluation year:
    2027
```

Generate week keys deterministically:

```text
2026-W01
2026-W02
...
2026-W52
2027-W01
...
2027-W52
2028-W01
...
2028-W52
```

Expected total number of weeks:

```text
156 weeks
```

---

## 7. Crop Cohort Definition

Please define three crop cohorts.

### 7.1 2025 crop carryover

```text
crop_year: 2025
initial inventory at 2026-W01: 80 lots
consumption period: 2026-W01 to 2026-W40
```

### 7.2 2026 crop

```text
crop_year: 2026
harvest weeks:
    2026-W40: 20 lots
    2026-W41: 30 lots
    2026-W42: 30 lots
    2026-W43: 15 lots
    2026-W44: 5 lots

total harvest: 100 lots

normal consumption starts:
    2026-W41

main consumption period:
    2026-W41 to 2027-W40
```

### 7.3 2027 crop

```text
crop_year: 2027
harvest weeks:
    2027-W40: 20 lots
    2027-W41: 30 lots
    2027-W42: 30 lots
    2027-W43: 15 lots
    2027-W44: 5 lots

total harvest: 100 lots

normal consumption starts:
    2027-W41

main consumption period:
    2027-W41 to 2028-W40
```

---

## 8. Demand Definition

Use the same MVP demand assumptions as v1 unless otherwise needed.

```text
household demand:
    1.0 lot / week

food-service demand:
    0.6 lot / week

total weekly demand:
    1.6 lots / week
```

Demand should exist for all 156 weeks.

For MVP simplicity, demand may remain float quantity.

Please preserve deterministic calculation.

---

## 9. Capacity Definition

Use the same simplified capacity assumptions as the current MVP.

```text
storage capacity:
    100 lots

milling capacity:
    5 lots / week

transport capacity:
    5 lots / week
```

The MVP may continue to treat milling / transport capacity in a simplified way.

The key new requirement is crop-year inventory tracking.

---

## 10. Cost / Price Assumptions

Use the same simplified assumptions as v1 unless already defined differently in code.

Example:

```text
purchase_cost_per_lot: 250,000 JPY
storage_cost_per_lot_week: 5,000 JPY
milling_cost_per_lot: 30,000 JPY
transport_cost_per_lot: 20,000 JPY
selling_price_per_lot: 500,000 JPY
```

These are modeling assumptions, not real industry values.

Please keep assumptions documented in code comments or output comments.

---

## 11. Required Adapter / Simulator Behavior

The v2 simulator should track inventory by crop year.

At minimum, each week should calculate:

```text
P_total
S_total
I_total

P_by_crop_year
S_by_crop_year
I_by_crop_year
```

### 11.1 Inventory consumption policy

Use FIFO by crop year for MVP:

```text
oldest crop inventory is consumed first
```

Expected order:

```text
2025 crop
then 2026 crop
then 2027 crop
```

This means:

```text
2025 crop carryover should be consumed before 2026 crop
2026 crop should be consumed before 2027 crop
```

This is not yet full FEFO, but it is appropriate for crop-year modeling.

### 11.2 Harvest availability convention

Use:

```text
harvest week:
    W40

new crop consumption start:
    W41
```

Practical interpretation:

```text
2026-W40 harvest increases 2026 crop inventory,
but normal 2026 crop consumption starts from 2026-W41.
```

If implementation makes same-week consumption easier, please still preserve the conceptual rule in comments and tests.

Preferred MVP:

```text
Do not consume newly harvested crop in the same W40 week if old crop remains.
```

---

## 12. Required Outputs

The runner should write outputs under:

```text
outputs/japanese_rice/
```

Required CSV outputs:

```text
rice_psi_summary.csv
rice_inventory_by_crop_year.csv
rice_cost_summary.csv
rice_kpi_summary.csv
```

Optional:

```text
rice_2027_evaluation_summary.csv
```

### 12.1 rice_psi_summary.csv

Header:

```csv
scenario_id,week,product_id,P,S,I,storage_capacity,storage_utilization,milling_capacity,transport_capacity
```

### 12.2 rice_inventory_by_crop_year.csv

Header:

```csv
scenario_id,week,product_id,crop_year,P,S,I,inventory_value,comment
```

Expected crop years:

```text
2025
2026
2027
```

### 12.3 rice_cost_summary.csv

Header:

```csv
scenario_id,metric,value,currency,comment
```

Expected metrics:

```text
total_revenue
total_purchase_cost
total_storage_cost
total_milling_cost
total_transport_cost
gross_profit
ending_inventory_value
```

### 12.4 rice_kpi_summary.csv

Header:

```csv
scenario_id,kpi_id,value,unit,comment
```

Expected KPIs:

```text
total_supply_qty
total_demand_qty
total_shipped_qty
ending_inventory_qty
peak_inventory_qty
fill_rate
peak_storage_utilization
gross_profit
profit_margin
```

For v2, also add:

```text
ending_inventory_2025_crop
ending_inventory_2026_crop
ending_inventory_2027_crop
main_evaluation_year
```

---

## 13. Required Smoke Summary Output

The runner should print a clear summary.

Expected structure:

```text
=== Japanese Rice Case smoke v2 ===
scenario: RICE_AS_IS
product: PACKAGED_RICE_STANDARD
horizon: 2026-W01..2028-W52
main evaluation year: 2027

crop cycles:
  2025 crop carryover: 80.0 lots
  2026 crop harvest: 100.0 lots
  2027 crop harvest: 100.0 lots

demand:
  weekly demand: 1.6 lots
  total demand over horizon: XXX lots
  2027 demand: XX lots

inventory by crop year:
  ending 2025 crop inventory: XX lots
  ending 2026 crop inventory: XX lots
  ending 2027 crop inventory: XX lots

2027 evaluation:
  2026 crop consumed before W40: XX lots
  2027 crop harvested W40-W44: 100.0 lots
  2027 crop consumed after W41: XX lots
  ending inventory at 2027-W52: XX lots

money:
  total revenue: XXX JPY
  total storage cost: XXX JPY
  total gross profit: XXX JPY

KPI:
  fill rate: XX%
  peak storage utilization: XX%
```

Exact numeric values may be determined by implementation, but tests should assert key structural expectations.

---

## 14. Test Requirements

Please update or add tests.

### 14.1 Required tests

```text
1. Generates 156 weekly buckets.
2. Main evaluation year is 2027.
3. 2025 crop carryover inventory exists at 2026-W01.
4. 2026 crop harvest total is 100 lots.
5. 2027 crop harvest total is 100 lots.
6. 2025 crop inventory declines during 2026-W01 to 2026-W40.
7. 2026 crop inventory exists during 2027-W01 to 2027-W40.
8. 2027 crop harvest starts at 2027-W40.
9. 2027 crop consumption starts no earlier than 2027-W41 under the MVP convention.
10. rice_inventory_by_crop_year.csv is generated.
11. rice_psi_summary.csv is generated.
12. rice_cost_summary.csv is generated.
13. rice_kpi_summary.csv is generated.
14. Inventory never becomes negative.
```

### 14.2 Compatibility tests

Please keep the existing Rice smoke test passing if it is updated in place.

Also run:

```bat
python -m pytest tests/test_japanese_rice_case_smoke.py
```

---

## 15. Test Commands

Please run:

```bat
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pysi.runners.run_japanese_rice_case_smoke
```

Optional compatibility checks:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
python -m pytest tests/test_forward_push_with_capacity_planner.py
python -m pytest tests/test_capacity_master_io.py
```

If broader tests fail due to unrelated optional dependencies, report separately.

---

## 16. Completion Criteria

This request is complete when:

```text
[OK] Rice smoke runner uses 3-year horizon
[OK] 156 weeks are generated
[OK] crop-year inventory is tracked
[OK] 2025 crop carryover is represented
[OK] 2026 crop harvest and consumption cycle is represented
[OK] 2027 crop harvest and consumption cycle is represented
[OK] 2027 main evaluation summary is printed
[OK] inventory_by_crop_year CSV is generated
[OK] cost and KPI summaries are still generated
[OK] focused tests pass
[OK] no GUI changes are made
[OK] no core WOM planner behavior is changed
```

---

## 17. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. Test commands executed
4. Test results
5. Output files generated
6. Any limitations or follow-up tasks
```

Please do not proceed into:

```text
full Rice model
full current WOM CSV adapter
full E2E Evaluation
Management Issue Generation
GUI integration
optimization
```

This request is only for:

```text
Japanese Rice Case smoke runner v2:
    3-year crop-cycle horizon
    crop-year inventory tracking
    2027 main evaluation summary
```