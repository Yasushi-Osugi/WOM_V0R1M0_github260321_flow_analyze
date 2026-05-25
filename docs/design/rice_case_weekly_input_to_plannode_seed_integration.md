# Rice Case Weekly Input to PlanNode Seed Integration Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-17  
**Status:** Design memo  
**Target path:** `docs/design/rice_case_weekly_input_to_plannode_seed_integration.md`

**Related design documents:**

- `docs/design/case_japanese_rice_supply_chain_as_is_research.md`
- `docs/design/case_japanese_rice_supply_chain_modeling.md`
- `docs/design/case_japanese_rice_master_dataset.md`
- `docs/design/case_japanese_rice_simulation_plan.md`
- `docs/design/case_japanese_rice_crop_year_modeling_addendum.md`
- `docs/design/wom_case_modeling_base_dataset.md`
- `docs/design/wom_plan_input_granularity_adapter.md`
- `docs/design/wom_plan_input_granularity_adapter_v0r2.md`
- `docs/design/wom_plan_input_granularity_adapter_v0r2_completion.md`
- `docs/design/wom_plan_input_granularity_adapter_v0r3_plan_node_seeding.md`
- `docs/design/wom_plan_input_granularity_adapter_v0r3_completion.md`

---

## 1. Purpose

This memo defines the next integration step after completion of the WOM Plan Input Granularity Adapter v0r1-v0r3.

The purpose is to connect the **Japanese Rice Case weekly dataset** to the new adapter pipeline and verify that Rice Case weekly plan data can be safely seeded into product-specific WOM / PySI V0R8 `PlanNode` PSI buckets.

The target flow is:

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

This is a controlled integration step.

It should not yet refactor the existing monthly `S_month / P_month` loader.

It should not yet connect to GUI.

It should not yet run the full Backward / Forward Planning sequence.

---

## 2. Background

The Plan Input Granularity Adapter has completed three foundational stages.

### v0r1: input granularity normalization

```text
monthly / weekly / case_weekly input
    ↓
canonical WeeklyPlanRow
```

### v0r2: lot and seed record generation

```text
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
in-memory PSI seed table
```

### v0r3: safe PlanNode seeding

```text
PsiSeedRecord
    ↓
product-specific PlanNode.psi4demand / psi4supply
```

The next step is to demonstrate that the Rice Case can use this pipeline.

---

## 3. Core Integration Objective

The integration objective is:

```text
Rice Case weekly plan data should be converted into WeeklyPlanRow records,
expanded into LotHeader and PsiSeedRecord records,
and safely seeded into mock or small product-specific PlanNode PSI buckets
without violating V0R8 PSI semantics.
```

The most important invariant is:

```text
PSI buckets hold Lot_ID lists, not numeric quantities.
```

Correct:

```python
plan_node.psi4demand[w][0] = ["LOT_A", "LOT_B", "LOT_C"]
```

Incorrect:

```python
plan_node.psi4demand[w][0] = 3
```

---

## 4. WOM / PySI V0R8 Assumptions

### 4.1 Physical layer and planning layer are different

WOM has two node worlds.

```text
Physical layer:
    product-independent GUI / map / NetworkX node world

Planning layer:
    product-specific PlanNode tree world
```

This integration targets the planning layer.

It does not seed physical GUI nodes.

### 4.2 PlanNode PSI structure

The target planning structure is:

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

### 4.3 Rice integration starts from demand-side seeding

The default Rice demand plan should seed:

```text
Generated demand Lot_IDs
    ↓
psi4demand[w][S]
```

Backward Planning will later propagate these lots through:

```text
psi4demand[w][S, CO, I, P]
```

and through the product-specific planning tree.

After demand allocation, a later bridge can copy or transform demand-side results into `psi4supply`.

Forward Planning then moves Lot_IDs through:

```text
psi4supply[w][S, CO, I, P]
```

This integration memo does not implement Backward Planning, Forward Planning, or demand-to-supply bridge.

---

## 5. Current Rice Case Assets

Current Rice Case code exists under:

```text
pysi/cases/japanese_rice/
```

Expected current modules:

```text
pysi/cases/japanese_rice/__init__.py
pysi/cases/japanese_rice/rice_case_dataset.py
pysi/cases/japanese_rice/rice_case_adapter.py
```

Current smoke runner:

```text
pysi/runners/run_japanese_rice_case_smoke.py
```

Current test:

```text
tests/test_japanese_rice_case_smoke.py
```

The Rice Case v2 currently models:

```text
3-year crop-cycle horizon:
    2026-W01 to 2028-W52

main evaluation year:
    2027

crop cycles:
    2025 crop carryover
    2026 crop harvest / consumption cycle
    2027 crop harvest / consumption cycle
```

Important weekly boundary:

```text
2026-W40:
    old crop final consumption week
    new crop harvest start week

2026-W41:
    new crop consumption start week
```

The integration must preserve this W40 / W41 boundary.

---

## 6. Integration Scope

### 6.1 In Scope

This integration should implement or verify:

```text
1. Rice weekly demand / supply rows can be converted to WeeklyPlanRow
2. crop_year metadata can be attached to LotHeader.attributes
3. WeeklyPlanRow can generate LotHeader records
4. LotHeader / WeeklyPlanRow can generate PsiSeedRecord records
5. PsiSeedRecord can seed mock PlanNode psi4demand / psi4supply buckets
6. W40 / W41 boundary is preserved
7. PSI buckets contain Lot_ID lists
8. Existing Rice smoke test remains compatible
```

### 6.2 Out of Scope

This integration should not:

```text
1. refactor existing S_month / P_month loader
2. modify GUI
3. modify run_full_plan
4. modify existing planning engines
5. run Backward Planning
6. run Forward Planning
7. implement demand-to-supply bridge
8. implement full Rice supply chain network
9. implement full Rice cost model
10. implement database persistence
```

---

## 7. Recommended Implementation Strategy

The implementation should be additive.

Do not replace current Rice smoke runner logic immediately.

Add a small Rice Case integration module and tests.

Suggested new file:

```text
pysi/cases/japanese_rice/rice_plan_input_integration.py
```

Suggested test file:

```text
tests/test_japanese_rice_plan_input_integration.py
```

Optional smoke runner:

```text
pysi/runners/run_japanese_rice_plan_input_seed_smoke.py
```

---

## 8. Rice Weekly Data to WeeklyPlanRow Mapping

### 8.1 Weekly demand row mapping

Rice weekly demand should map to demand-side S seed.

Conceptual mapping:

```text
Rice demand row
    scenario_id
    product_id
    demand node_id
    week
    demand quantity
        ↓
WeeklyPlanRow(
    scenario_id=scenario_id,
    product_id=product_id,
    node_id=demand_node_id,
    week=week,
    plan_type="demand",
    quantity=demand_quantity,
    source_granularity="case_weekly",
    source_id="rice_demand_plan",
)
```

Default downstream mapping:

```text
WeeklyPlanRow(plan_type="demand")
    ↓
PsiSeedRecord(layer="demand", bucket="S")
    ↓
PlanNode.psi4demand[w][S]
```

### 8.2 Weekly supply / harvest row mapping

Rice weekly harvest / supply should map to supply-side planning requirement.

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
    quantity=supply_quantity,
    source_granularity="case_weekly",
    source_id="rice_supply_plan",
)
```

Default downstream mapping from v0r2/v0r3:

```text
WeeklyPlanRow(plan_type="supply")
    ↓
PsiSeedRecord(layer="demand", bucket="P")
    ↓
PlanNode.psi4demand[w][P]
```

This is acceptable for MVP because the supply requirement is still being positioned in the demand planning layer before the eventual forward simulation.

Future variants may map external supply or initial inventory into:

```text
PsiSeedRecord(layer="supply", bucket="I")
```

but that should be handled in a later design if needed.

---

## 9. Rice Lot Metadata

Rice Case should preserve crop-year metadata in `LotHeader.attributes`.

Recommended metadata fields:

```text
crop_year
harvest_week
available_week
quality_limit_week
expected_consumption_start_week
expected_consumption_end_week
rice_grade
origin_region
```

MVP minimum:

```text
crop_year
harvest_week
available_week
quality_limit_week
```

Example:

```python
{
    "crop_year": "2026",
    "harvest_week": "2026-W40",
    "available_week": "2026-W41",
    "quality_limit_week": "2027-W40",
}
```

---

## 10. Week Indexing

Rice Case v2 uses a 3-year horizon:

```text
2026-W01 to 2028-W52
```

Therefore the integration needs a deterministic week indexer.

Recommended MVP helper:

```python
def build_rice_week_indexer(start_year: int = 2026, end_year: int = 2028) -> dict[str, int]:
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

The integration should not silently infer weeks outside the declared horizon.

---

## 11. Mock PlanNode for Integration Test

Use a minimal mock PlanNode for the first integration test.

```python
@dataclass
class MockPlanNode:
    name: str
    psi4demand: list
    psi4supply: list
```

Helper:

```python
def make_mock_plan_node(name: str, weeks: int) -> MockPlanNode:
    return MockPlanNode(
        name=name,
        psi4demand=[[[], [], [], []] for _ in range(weeks)],
        psi4supply=[[[], [], [], []] for _ in range(weeks)],
    )
```

The first test should not require real WOM PlanNode construction.

---

## 12. Proposed Integration Functions

### 12.1 Build Rice WeeklyPlanRows

Suggested function:

```python
def build_rice_weekly_plan_rows(case_data) -> list[WeeklyPlanRow]:
    ...
```

This should produce both:

```text
demand WeeklyPlanRows
supply / harvest WeeklyPlanRows
```

If current Rice Case dataset structure is not yet aligned, implement a minimal adapter around current dataset structures.

### 12.2 Build Rice Row Attributes

Suggested function:

```python
def build_rice_row_attributes(rows: list[WeeklyPlanRow]) -> dict[int, dict]:
    ...
```

This returns row-indexed metadata for use by:

```python
generate_psi_seed_records(..., row_attributes=row_attributes)
```

### 12.3 Build Rice Week Indexer

Suggested function:

```python
def build_rice_week_indexer(start_year: int = 2026, end_year: int = 2028) -> dict[str, int]:
    ...
```

### 12.4 Seed Rice Rows into Mock PlanNodes

Suggested helper:

```python
def seed_rice_weekly_rows_to_mock_plan_nodes(
    rows: list[WeeklyPlanRow],
    *,
    week_indexer: dict[str, int],
) -> RicePlanInputSeedResult:
    ...
```

This may be implemented only in tests or as a small smoke helper.

---

## 13. Suggested Result Object

Optional result dataclass:

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
```

This is useful for a smoke runner summary.

---

## 14. Expected Smoke Summary

If a smoke runner is added, it should print something like:

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

## 15. Required Tests

### 15.1 WeeklyPlanRow generation test

Verify that Rice weekly data is converted to `WeeklyPlanRow`.

Expected:

```text
rows are not empty
rows contain plan_type="demand"
rows contain plan_type="supply"
source_granularity="case_weekly"
```

### 15.2 Crop-year metadata test

Verify that Rice crop-year metadata is preserved in `LotHeader.attributes`.

Expected:

```text
crop_year exists
harvest_week exists for harvest rows
available_week exists where applicable
quality_limit_week exists where applicable
```

### 15.3 W40 / W41 boundary test

Verify:

```python
week_indexer["2026-W40"] == 39
week_indexer["2026-W41"] == 40
```

and seed records go to correct PSI week index.

### 15.4 PlanNode seed test

Verify:

```text
demand rows seed to psi4demand[w][S]
supply rows seed to psi4demand[w][P]
PSI buckets contain Lot_ID strings
PSI buckets do not contain numeric quantities
```

### 15.5 Compatibility test

Existing tests must still pass:

```text
tests/test_japanese_rice_case_smoke.py
tests/test_plan_input_granularity_adapter.py
tests/test_plan_input_lot_generation.py
tests/test_plan_input_psi_seed.py
tests/test_plan_input_pipeline.py
tests/test_plan_input_plan_node_seeding.py
```

---

## 16. Completion Criteria

This integration is complete when:

```text
[OK] Rice weekly data can produce WeeklyPlanRow records
[OK] Rice WeeklyPlanRows produce LotHeader records
[OK] crop_year metadata is preserved in LotHeader.attributes
[OK] Rice WeeklyPlanRows produce PsiSeedRecord records
[OK] Rice PsiSeedRecords can seed mock PlanNode PSI buckets
[OK] demand rows seed to psi4demand[w][S]
[OK] supply rows seed to psi4demand[w][P]
[OK] W40 / W41 boundary is preserved
[OK] PSI buckets contain Lot_ID lists, not quantities
[OK] existing Rice smoke test remains compatible
[OK] no GUI / run_full_plan / existing loader refactor is performed
```

---

## 17. Future Work

### 17.1 Real product-specific PlanNode integration

After mock PlanNode integration is stable, connect this to actual product-specific planning trees:

```text
prod_tree_dict_OT[product_name]
prod_tree_dict_IN[product_name]
```

### 17.2 Existing monthly loader refactor

Later, existing monthly `S_month / P_month` loader can be refactored to use:

```text
monthly input
    ↓
canonical WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
PlanNode seeding
```

### 17.3 GUI case load

Future GUI function:

```text
select Rice Case
    ↓
load weekly case data
    ↓
seed PlanNode PSI
    ↓
run planning sequence
```

### 17.4 Backward / Forward Planning integration

Future integration should run planning after seeding:

```text
PlanNode PSI seed
    ↓
Backward Planning
    ↓
demand-to-supply bridge
    ↓
Forward Planning
```

This is out of scope for the current integration.

---

## 18. Summary

This integration connects the Rice Case Modeling Process to the newly completed Plan Input Granularity Adapter pipeline.

The target integration flow is:

```text
Rice weekly supply / demand data
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
product-specific PlanNode.psi4demand / psi4supply
```

The most important rule remains:

```text
PSI buckets hold Lot_ID lists.
Quantity is len(list).
Lot attributes live outside PSI buckets.
```

This step proves that the Rice Case can enter the WOM planning layer through the new normalized input pipeline, while preserving weekly crop-year semantics such as the W40 / W41 boundary.
