# Codex Request: Implement Rice Case Weekly Input to PlanNode Seed Integration

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/rice_case_weekly_input_to_plannode_seed_integration.md
```

Please read this design memo first.

The following Plan Input Granularity Adapter pipeline is already implemented and merged into this branch:

```text
v0r1:
  monthly / weekly / case_weekly input
      ↓
  canonical WeeklyPlanRow

v0r2:
  WeeklyPlanRow
      ↓
  LotHeader
      ↓
  PsiSeedRecord
      ↓
  in-memory PSI seed table

v0r3:
  PsiSeedRecord
      ↓
  product-specific PlanNode.psi4demand / psi4supply
```

Existing adapter modules include:

```text
pysi/adapters/calendar_445.py
pysi/adapters/weekly_plan_table.py
pysi/adapters/plan_input_granularity.py
pysi/adapters/lot_generation.py
pysi/adapters/psi_seed.py
pysi/adapters/plan_input_pipeline.py
pysi/adapters/plan_node_seeding.py
```

The Rice Case currently has:

```text
pysi/cases/japanese_rice/__init__.py
pysi/cases/japanese_rice/rice_case_dataset.py
pysi/cases/japanese_rice/rice_case_adapter.py
pysi/runners/run_japanese_rice_case_smoke.py
tests/test_japanese_rice_case_smoke.py
```

The current Rice Case smoke runner v2 uses:

```text
3-year crop-cycle horizon
2026-W01 to 2028-W52
main evaluation year = 2027
crop-year inventory tracking
```

This request is to connect Rice Case weekly supply / demand data to the Plan Input Adapter pipeline and verify that Rice weekly input can be safely seeded into PlanNode PSI buckets.

---

## 2. Main Objective

Implement a minimal integration layer:

```text
Rice Case weekly supply / demand data
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
product-specific PlanNode.psi4demand / psi4supply
```

This should prove that the Rice Case can enter the WOM planning layer through the new normalized input pipeline.

This request should use mock or minimal PlanNode objects for tests.

Do not run full Backward Planning or Forward Planning.

---

## 3. Critical WOM / PySI V0R8 Assumptions

Please preserve these assumptions.

### 3.1 Physical node layer and planning PlanNode layer are different

WOM has two node worlds:

```text
Physical layer:
    product-independent GUI / map / NetworkX node world

Planning layer:
    product-specific PlanNode tree world
```

This request targets the planning layer only.

Do not seed physical GUI nodes.

### 3.2 PSI bucket structure

The canonical V0R8 PSI structure is:

```python
node.psi4demand[w] = [S_ids, CO_ids, I_ids, P_ids]
node.psi4supply[w] = [S_ids, CO_ids, I_ids, P_ids]
```

Bucket index convention:

```python
PSI_S  = 0
PSI_CO = 1
PSI_I  = 2
PSI_P  = 3
```

### 3.3 PSI buckets must contain Lot_ID lists, not numeric quantities

Correct:

```python
node.psi4demand[w][PSI_S] = ["LOT_A", "LOT_B", "LOT_C"]
```

Incorrect:

```python
node.psi4demand[w][PSI_S] = 3
```

Quantity remains:

```python
quantity = len(node.psi4demand[w][bucket])
```

Lot attributes should remain in `LotHeader.attributes`, not inside PSI buckets.

---

## 4. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan.
3. Do not modify existing monthly S_month / P_month loader.
4. Do not run Backward Planning.
5. Do not run Forward Planning.
6. Do not implement demand-to-supply bridge.
7. Do not implement full Rice Case network simulation.
8. Do not implement Management Issue Generation.
9. Keep this as a safe additive integration layer.
10. Use mock or minimal PlanNode objects for tests.
```

---

## 5. Suggested Files

Please add:

```text
pysi/cases/japanese_rice/rice_plan_input_integration.py
tests/test_japanese_rice_plan_input_integration.py
```

Optional, if useful:

```text
pysi/runners/run_japanese_rice_plan_input_seed_smoke.py
```

Please update only if needed:

```text
pysi/cases/japanese_rice/__init__.py
```

Do not modify:

```text
existing monthly loaders
GUI
planning engines
run_full_plan
```

---

## 6. Rice Weekly Data to WeeklyPlanRow Mapping

### 6.1 Demand rows

Rice weekly demand should map to demand-side `S` seed.

Conceptual mapping:

```text
Rice demand row
    scenario_id
    product_id
    demand_node_id
    week
    demand quantity
        ↓
WeeklyPlanRow(
    scenario_id=scenario_id,
    product_id=product_id,
    node_id=demand_node_id,
    week=week,
    plan_type="demand",
    quantity=demand_qty,
    source_granularity="case_weekly",
    source_id="rice_demand_plan",
)
```

Downstream default mapping:

```text
WeeklyPlanRow(plan_type="demand")
    ↓
PsiSeedRecord(layer="demand", bucket="S")
    ↓
PlanNode.psi4demand[w][S]
```

### 6.2 Supply / harvest rows

Rice weekly supply / harvest should map to planning-side `P` seed.

Conceptual mapping:

```text
Rice supply / harvest row
    scenario_id
    product_id
    producer node_id
    week
    supply quantity
    crop_year
        ↓
WeeklyPlanRow(
    scenario_id=scenario_id,
    product_id=product_id,
    node_id=producer_node_id,
    week=week,
    plan_type="supply",
    quantity=supply_qty,
    source_granularity="case_weekly",
    source_id="rice_supply_plan",
)
```

Downstream default mapping:

```text
WeeklyPlanRow(plan_type="supply")
    ↓
PsiSeedRecord(layer="demand", bucket="P")
    ↓
PlanNode.psi4demand[w][P]
```

This is acceptable for MVP because the supply requirement is still being positioned in the demand planning layer before eventual Forward Planning.

---

## 7. Rice Crop-Year Metadata

Rice Case must preserve crop-year metadata in `LotHeader.attributes`.

Recommended metadata fields:

```text
crop_year
harvest_week
available_week
quality_limit_week
expected_consumption_start_week
expected_consumption_end_week
origin_region
rice_grade
```

MVP minimum:

```text
crop_year
harvest_week
available_week
quality_limit_week
```

Example attributes:

```python
{
    "crop_year": "2026",
    "harvest_week": "2026-W40",
    "available_week": "2026-W41",
    "quality_limit_week": "2027-W40",
}
```

---

## 8. Week Indexing

Rice Case v2 uses:

```text
planning horizon:
    2026-W01 to 2028-W52
```

Please implement or reuse a deterministic week indexer.

Suggested function:

```python
def build_rice_week_indexer(
    start_year: int = 2026,
    end_year: int = 2028,
) -> dict[str, int]:
    ...
```

Expected examples:

```python
week_indexer["2026-W01"] == 0
week_indexer["2026-W40"] == 39
week_indexer["2026-W41"] == 40
week_indexer["2027-W01"] == 52
week_indexer["2028-W52"] == 155
```

Do not silently infer weeks outside the declared horizon.

---

## 9. Mock PlanNode

Use a minimal mock PlanNode for integration tests.

```python
from dataclasses import dataclass


@dataclass
class MockPlanNode:
    name: str
    psi4demand: list
    psi4supply: list
```

Suggested helper:

```python
def make_mock_plan_node(name: str, weeks: int) -> MockPlanNode:
    return MockPlanNode(
        name=name,
        psi4demand=[[[], [], [], []] for _ in range(weeks)],
        psi4supply=[[[], [], [], []] for _ in range(weeks)],
    )
```

This should not depend on the full WOM tree.

---

## 10. Proposed Integration Functions

Please implement small functions in:

```text
pysi/cases/japanese_rice/rice_plan_input_integration.py
```

### 10.1 build_rice_week_indexer

```python
def build_rice_week_indexer(
    start_year: int = 2026,
    end_year: int = 2028,
) -> dict[str, int]:
    ...
```

### 10.2 build_rice_weekly_plan_rows

```python
def build_rice_weekly_plan_rows(case_data) -> list[WeeklyPlanRow]:
    ...
```

This should produce both:

```text
demand WeeklyPlanRows
supply / harvest WeeklyPlanRows
```

If the current Rice Case dataset structure is not yet fully aligned, implement a minimal adapter around existing `rice_case_dataset.py` structures.

### 10.3 build_rice_row_attributes

```python
def build_rice_row_attributes(
    rows: list[WeeklyPlanRow],
) -> dict[int, dict]:
    ...
```

This should return row-indexed metadata for use by:

```python
generate_psi_seed_records(..., row_attributes=row_attributes)
```

### 10.4 seed_rice_weekly_rows_to_mock_plan_nodes

```python
def seed_rice_weekly_rows_to_mock_plan_nodes(
    rows: list[WeeklyPlanRow],
    *,
    week_indexer: dict[str, int],
) -> RicePlanInputSeedResult:
    ...
```

This function may:

```text
1. generate LotHeader records
2. generate PsiSeedRecord records
3. build mock PlanNodes
4. seed records into mock PlanNodes
5. return summary result
```

---

## 11. Suggested Result Dataclass

Optional but useful:

```python
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
```

This makes the smoke result easier to inspect.

---

## 12. Expected Smoke Summary

If a smoke runner is added, it should print:

```text
=== Japanese Rice Plan Input Seed smoke ===
scenario: RICE_AS_IS
product: PACKAGED_RICE_STANDARD
horizon: 2026-W01..2028-W52

input:
  weekly rows: N
  generated lots: N
  seed records: N

PlanNode seed:
  demand/S seeded lots: N
  demand/P seeded lots: N
  supply/I seeded lots: N
  missing nodes: 0
  invalid weeks: 0

boundary:
  2026-W40 index: 39
  2026-W41 index: 40
```

---

## 13. Required Tests

Please add:

```text
tests/test_japanese_rice_plan_input_integration.py
```

### 13.1 WeeklyPlanRow generation test

Verify that Rice weekly data is converted to `WeeklyPlanRow`.

Expected:

```text
rows are not empty
rows contain plan_type="demand"
rows contain plan_type="supply"
source_granularity="case_weekly"
```

### 13.2 Crop-year metadata test

Verify that Rice crop-year metadata is preserved in `LotHeader.attributes`.

Expected:

```text
crop_year exists
harvest_week exists for harvest rows
available_week exists where applicable
quality_limit_week exists where applicable
```

### 13.3 W40 / W41 boundary test

Verify:

```python
week_indexer["2026-W40"] == 39
week_indexer["2026-W41"] == 40
```

Also verify that seed records land in the correct PSI week index.

### 13.4 PlanNode seed test

Verify:

```text
demand rows seed to psi4demand[w][S]
supply rows seed to psi4demand[w][P]
PSI buckets contain Lot_ID strings
PSI buckets do not contain numeric quantities
```

### 13.5 Compatibility tests

Existing tests should still pass:

```text
tests/test_japanese_rice_case_smoke.py
tests/test_plan_input_granularity_adapter.py
tests/test_plan_input_lot_generation.py
tests/test_plan_input_psi_seed.py
tests/test_plan_input_pipeline.py
tests/test_plan_input_plan_node_seeding.py
```

---

## 14. Test Commands

Please run:

```bat
python -m pytest tests/test_japanese_rice_plan_input_integration.py
```

Also run:

```bat
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_plan_input_granularity_adapter.py
python -m pytest tests/test_plan_input_lot_generation.py
python -m pytest tests/test_plan_input_psi_seed.py
python -m pytest tests/test_plan_input_pipeline.py
python -m pytest tests/test_plan_input_plan_node_seeding.py
```

Optional compatibility check:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

---

## 15. Completion Criteria

This request is complete when:

```text
[OK] rice_plan_input_integration.py exists
[OK] Rice weekly data can produce WeeklyPlanRow records
[OK] Rice WeeklyPlanRows can produce LotHeader records
[OK] crop_year metadata is preserved in LotHeader.attributes
[OK] Rice WeeklyPlanRows can produce PsiSeedRecord records
[OK] Rice PsiSeedRecords can seed mock PlanNode PSI buckets
[OK] demand rows seed to psi4demand[w][S]
[OK] supply rows seed to psi4demand[w][P]
[OK] W40 / W41 boundary is preserved
[OK] PSI buckets contain Lot_ID lists, not quantities
[OK] existing Rice smoke test remains compatible
[OK] no GUI / run_full_plan / existing loader refactor is performed
```

---

## 16. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. Test commands executed
4. Test results
5. Any limitations or follow-up tasks
```

Please do not proceed into:

```text
real product-specific PlanNode tree integration
existing monthly loader refactor
run_full_plan integration
GUI integration
Backward Planning execution
Forward Planning execution
Management Issue Generation
```

This request is only for:

```text
Rice Case weekly input to mock PlanNode seed integration
```