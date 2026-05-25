# Codex Request: Implement Japanese Rice Case Smoke Runner / Adapter MVP

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design documents have already been added:

```text
docs/design/case_japanese_rice_supply_chain_as_is_research.md
docs/design/wom_case_modeling_base_dataset.md
docs/design/case_japanese_rice_supply_chain_modeling.md
docs/design/case_japanese_rice_master_dataset.md
docs/design/case_japanese_rice_simulation_plan.md
```

Please read these design documents before coding.

The key modeling principle is:

```text
Real-world Supply Chain Case
    ↓
WOM Case Modeling Base Dataset
    ↓
Adapter
    ↓
WOM Planning Engine / simplified smoke engine
    ↓
PSI / Capacity / Cost / KPI outputs
    ↓
Visualization
    ↓
Management Issue
```

This request is for the first **Japanese Rice Case smoke runner / adapter MVP**.

It is not a request to implement the full Rice Case, full GUI integration, full optimization, or final Management Issue Generation.

---

## 2. Main Objective

Implement a minimal Japanese Rice Case MVP that validates the WOM Modeling Process.

The MVP should demonstrate:

```text
Rice Case Master Dataset
    ↓
Adapter
    ↓
simple weekly PSI simulation
    ↓
basic cost / price evaluation
    ↓
basic KPI summary
    ↓
smoke runner outputs
```

The main pattern to demonstrate is:

```text
Harvest season:
    P rises sharply

After harvest:
    I rises sharply

Through the year:
    S continues weekly
    I gradually decreases
```

The MVP should be small, deterministic, and easy to test.

---

## 3. Important Scope Control

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify existing core WOM planners unless absolutely necessary.
3. Do not implement full optimization.
4. Do not implement full Rice industry model.
5. Do not implement full database persistence.
6. Do not implement full Management Issue Generation.
7. Do not implement LLM summarization.
8. Keep this as a smoke runner + adapter MVP.
```

The goal is to validate the modeling process, not to complete the full Rice simulation.

---

## 4. Design Concepts to Preserve

Please preserve the following concepts from the design documents.

### 4.1 Case dataset first, adapter second

Do not force the Rice Case directly into the current WOM CSV format.

Instead:

```text
Rice Case Master Dataset:
    business-friendly case model

Adapter:
    transforms case data into simple executable structures
```

### 4.2 Lot identity

Rice lots should preserve identity.

For MVP:

```text
1 lot = 1,000 kg
```

A lot can be generated from `rice_supply_plan.csv`.

### 4.3 Weekly bucket

Use weekly buckets:

```text
2026-W01 ... 2026-W52
```

### 4.4 Quantity + money

The MVP should include both:

```text
quantity:
    P / S / I

money:
    revenue / cost / gross profit / inventory value
```

---

## 5. Suggested Files

Please add:

```text
pysi/cases/japanese_rice/__init__.py
pysi/cases/japanese_rice/rice_case_dataset.py
pysi/cases/japanese_rice/rice_case_adapter.py
pysi/runners/run_japanese_rice_case_smoke.py
tests/test_japanese_rice_case_smoke.py
```

Optional if useful:

```text
pysi/cases/japanese_rice/data/rice_scenario_master.csv
pysi/cases/japanese_rice/data/rice_node_master.csv
pysi/cases/japanese_rice/data/rice_lane_master.csv
pysi/cases/japanese_rice/data/rice_product_master.csv
pysi/cases/japanese_rice/data/rice_supply_plan.csv
pysi/cases/japanese_rice/data/rice_demand_plan.csv
pysi/cases/japanese_rice/data/rice_capacity_master.csv
pysi/cases/japanese_rice/data/rice_cost_price_master.csv
pysi/cases/japanese_rice/data/rice_kpi_policy_master.csv
pysi/cases/japanese_rice/data/rice_assumption_log.csv
```

For this first MVP, it is acceptable to define the sample dataset in Python code rather than CSV files, as long as the code mirrors the master dataset schemas.

Please keep the implementation small.

---

## 6. MVP Scenario Definition

Use the following MVP scenario.

```text
scenario_id: RICE_AS_IS
product_name: PACKAGED_RICE_STANDARD
planning horizon: 2026-W01 to 2026-W52
lot_size: 1 lot = 1,000 kg
```

### 6.1 Nodes

Use these simplified nodes:

```text
PRODUCER_NIIGATA
COLLECTION_NIIGATA
BROWN_STORAGE_EAST
MILL_EAST
PACKAGING_EAST
WHOLESALER_EAST
RETAIL_TOKYO
FOOD_SERVICE_TOKYO
DEMAND_HOUSEHOLD_TOKYO
DEMAND_FOOD_SERVICE_TOKYO
```

For the first MVP, the actual simulation may aggregate downstream behavior into a simplified `MARKET_DEMAND` stage if that keeps the smoke runner small.

### 6.2 Supply Pattern

Use harvest supply concentrated in W40-W44.

```text
W40: 20 lots
W41: 30 lots
W42: 30 lots
W43: 15 lots
W44: 5 lots
Total: 100 lots
```

### 6.3 Demand Pattern

Use constant weekly demand.

```text
household demand: 1.0 lot / week
food service demand: 0.6 lot / week
total weekly demand: 1.6 lots / week
annual demand: 83.2 lots
```

For integer lot simulation, choose one of the following simple policies:

```text
Option A:
    represent demand as float quantity in summary outputs

Option B:
    convert to integer lots by using 16 lots per 10 weeks or similar deterministic approximation
```

Preferred MVP approach:

```text
Use float quantities for summary calculation,
but preserve generated harvest lots as integer lot objects.
```

If this complicates implementation, use integer demand:

```text
household: 1 lot / week
food_service: 1 lot / week
total: 2 lots / week
```

and document that this is an MVP simplification.

---

## 7. Capacity Assumptions

Use simple capacity assumptions.

```text
storage capacity:
    100 lots

milling capacity:
    5 lots / week

transport capacity:
    5 lots / week
```

For the first smoke test, these should be enough to demonstrate:

```text
harvest supply spike
inventory buildup
inventory drawdown
capacity usage
```

---

## 8. Cost / Price Assumptions

Use simple values.

```text
purchase_cost_per_lot: 250,000 JPY
storage_cost_per_lot_week: 5,000 JPY
milling_cost_per_lot: 30,000 JPY
transport_cost_per_lot: 20,000 JPY
selling_price_per_lot: 500,000 JPY
```

These are simplified modeling assumptions, not real industry values.

Please record these assumptions in the output or code comments.

---

## 9. Required Adapter Behavior

Implement a small adapter layer that converts Rice Case sample data into executable structures.

### 9.1 Suggested dataclasses

```python
@dataclass
class RiceSupplyPlanRow:
    scenario_id: str
    node_id: str
    product_id: str
    week: str
    supply_qty: float
    supply_type: str
    source_type: str
    comment: str = ""
```

```python
@dataclass
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
```

```python
@dataclass
class RiceCostPrice:
    cost_price_type: str
    unit_value: float
```

```python
@dataclass
class RiceCaseDataset:
    scenario_id: str
    weeks: list[str]
    supply_plan: list[RiceSupplyPlanRow]
    demand_plan: list[RiceDemandPlanRow]
    cost_price: dict[str, float]
    storage_capacity: float
    milling_capacity: float
    transport_capacity: float
```

### 9.2 Adapter output

The adapter should produce a simplified executable dataset:

```python
@dataclass
class RiceExecutablePlanInput:
    scenario_id: str
    weeks: list[str]
    weekly_supply_qty: dict[str, float]
    weekly_demand_qty: dict[str, float]
    storage_capacity: float
    milling_capacity: float
    transport_capacity: float
    cost_price: dict[str, float]
```

This keeps the MVP independent from the full current WOM node tree while validating the modeling process.

---

## 10. Required Smoke Simulation Behavior

Implement a small deterministic simulator inside the case runner or adapter.

### 10.1 Weekly logic

For each week:

```text
P = harvest supply in that week
available_inventory = previous_inventory + P

S_candidate = weekly demand
S_limited_by_milling = min(S_candidate, milling_capacity)
S_limited_by_transport = min(S_limited_by_milling, transport_capacity)
S = min(available_inventory, S_limited_by_transport)

I = available_inventory - S
```

Storage capacity check:

```text
if I > storage_capacity:
    overflow_inventory = I - storage_capacity
else:
    overflow_inventory = 0
```

For MVP:

```text
overflow_inventory is recorded as capacity violation / warning
but not automatically disposed.
```

### 10.2 Outputs to calculate

```text
weekly P
weekly S
weekly I
storage utilization
milling utilization
transport utilization
storage cost
revenue
gross profit
inventory value
```

---

## 11. Required Smoke Output

The runner should print a clear summary.

Example:

```text
=== Japanese Rice Case smoke ===
scenario: RICE_AS_IS
product: PACKAGED_RICE_STANDARD
horizon: 2026-W01..2026-W52

supply:
  total harvest supply: 100.0 lots
  harvest weeks: W40-W44

demand:
  total annual demand: 83.2 lots
  weekly demand: 1.6 lots

PSI:
  peak inventory: XX lots
  ending inventory: XX lots
  total shipped/sold: XX lots

capacity:
  storage capacity: 100 lots
  peak storage utilization: XX%
  milling capacity: 5 lots/week
  transport capacity: 5 lots/week

money:
  total revenue: XXX JPY
  total purchase cost: XXX JPY
  total storage cost: XXX JPY
  total gross profit: XXX JPY

KPI:
  fill rate: XX%
  inventory turnover proxy: XX
```

---

## 12. Output Files

Write outputs under:

```text
outputs/japanese_rice/
```

Required output CSVs:

```text
rice_psi_summary.csv
rice_cost_summary.csv
rice_kpi_summary.csv
```

Optional output CSVs:

```text
rice_capacity_usage.csv
rice_capacity_violation.csv
rice_inventory_by_week.csv
```

### 12.1 rice_psi_summary.csv

Header:

```csv
scenario_id,week,product_id,P,S,I,storage_capacity,storage_utilization,milling_capacity,transport_capacity
```

### 12.2 rice_cost_summary.csv

Header:

```csv
scenario_id,metric,value,currency,comment
```

Rows:

```text
total_revenue
total_purchase_cost
total_storage_cost
total_milling_cost
total_transport_cost
gross_profit
ending_inventory_value
```

### 12.3 rice_kpi_summary.csv

Header:

```csv
scenario_id,kpi_id,value,unit,comment
```

Rows:

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

---

## 13. Test Requirements

Add:

```text
tests/test_japanese_rice_case_smoke.py
```

Required tests:

```text
1. RiceCaseDataset builds 52 weekly buckets.
2. Total harvest supply is 100 lots.
3. Weekly demand is generated for all 52 weeks.
4. PSI simulation produces non-negative inventory.
5. Inventory rises during harvest weeks.
6. Total shipped quantity is positive.
7. Cost summary includes revenue, storage cost, gross profit.
8. KPI summary includes fill_rate and peak_inventory_qty.
9. Output CSVs can be generated.
```

Keep tests deterministic.

---

## 14. Test Commands

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

## 15. Completion Criteria

This request is complete when:

```text
[OK] Rice Case smoke runner exists
[OK] Rice Case adapter / dataset structures exist
[OK] 52-week AS-IS simulation runs
[OK] harvest supply W40-W44 is represented
[OK] PSI summary is generated
[OK] cost summary is generated
[OK] KPI summary is generated
[OK] focused test passes
[OK] no GUI changes are made
[OK] no core WOM planner behavior is changed
```

---

## 16. Expected Response from Codex

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

This request is only for the minimal:

```text
Japanese Rice Case smoke runner / adapter MVP
```