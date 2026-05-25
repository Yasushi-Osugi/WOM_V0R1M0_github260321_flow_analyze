# Codex Request: Implement Rice Case Backward Planning After Seed Smoke

Please implement this request on the current branch:
feature/with-capacity-psi-engine-v0r2

Before coding, please verify that the following files exist:
- docs/design/rice_case_backward_planning_after_seed.md
- pysi/cases/japanese_rice/rice_actual_prod_tree_seed_integration.py
- pysi/cases/japanese_rice/rice_real_plannode_seed_integration.py
- pysi/cases/japanese_rice/rice_plan_input_integration.py
- pysi/adapters/plan_node_seeding.py
- tests/test_japanese_rice_actual_prod_tree_seed_integration.py

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/rice_case_backward_planning_after_seed.md
```

Please read this design memo first.

The current Rice Case input pipeline has already been implemented up to actual product-tree compatible PSI seeding:

```text
Rice weekly input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
actual-like / product-specific PlanNode.psi4demand
```

The next controlled step is:

```text
PlanNode.psi4demand seed
    ↓
Backward Planning
    ↓
demand allocation result in psi4demand
```

This request is to implement a **small smoke integration** that verifies existing WOM / PySI V0R8 Backward Planning can operate on Rice Case seeded `psi4demand` data.

---

## 2. Main Objective

Implement a minimal Rice Case Backward Planning After Seed smoke layer.

The goal is to verify:

```text
1. Rice Case seed records can be applied to a product-specific PlanNode tree.
2. Existing Backward Planning logic can run on the seeded tree.
3. PSI buckets remain Lot_ID lists after Backward Planning.
4. Seeded Lot_IDs are not lost.
5. W40 / W41 Rice crop-year boundary remains valid.
```

This request should not attempt to produce final business results.

It is a structural safety test between:

```text
PlanNode seeding
    ↓
Backward Planning
```

---

## 3. Critical WOM / PySI V0R8 Assumptions

Please preserve the following assumptions.

### 3.1 Physical node layer and planning PlanNode layer are different

WOM has two node worlds:

```text
Physical layer:
    product-independent GUI / map / NetworkX node world

Planning layer:
    product-specific PlanNode tree world
```

This request targets the planning layer only.

Do not use physical GUI nodes as the planning target.

---

### 3.2 Backward Planning operates on `psi4demand`

Backward Planning is a demand-layer process.

Initial seed:

```text
PlanNode.psi4demand[w][S]
```

Expected propagation:

```text
psi4demand[w][S, CO, I, P]
```

and / or parent-child tree propagation, depending on existing V0R8 functions.

---

### 3.3 PSI buckets must contain Lot_ID lists

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

Correct:

```python
node.psi4demand[w][PSI_S] = ["LOT_A", "LOT_B", "LOT_C"]
```

Incorrect:

```python
node.psi4demand[w][PSI_S] = 3
```

Quantity is:

```python
quantity = len(node.psi4demand[w][bucket])
```

Please ensure no numeric quantities are inserted into PSI buckets.

---

## 4. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan.
3. Do not modify existing S_month / P_month loader.
4. Do not run Forward Planning.
5. Do not copy psi4demand to psi4supply.
6. Do not implement demand-to-supply bridge.
7. Do not implement full Rice supply chain network simulation.
8. Do not implement cost / KPI / Management Issue Generation.
9. Keep this as a small Backward Planning smoke integration.
```

This request is only for:

```text
Rice Case seeded PlanNode
    ↓
Backward Planning smoke
```

---

## 5. Existing Modules to Reuse

Please inspect and reuse existing modules where possible.

Relevant existing modules include:

```text
pysi/plan/engines.py
pysi/cases/japanese_rice/rice_case_dataset.py
pysi/cases/japanese_rice/rice_case_adapter.py
pysi/cases/japanese_rice/rice_plan_input_integration.py
pysi/cases/japanese_rice/rice_real_plannode_seed_integration.py
pysi/cases/japanese_rice/rice_actual_prod_tree_seed_integration.py
pysi/adapters/plan_node_seeding.py
```

Candidate existing Backward Planning functions:

```text
outbound_backward_leaf_to_MOM(...)
inbound_backward_MOM_to_leaf(...)
allocate_markets_to_moms(...)
inbound_MOM_leveling_vs_capacity(...)
```

The first smoke should prefer the smallest safe existing function.

Recommended first target:

```python
outbound_backward_leaf_to_MOM(out_root, in_root, layer="demand")
```

If this function is too broad for the first smoke, use the smaller available PlanNode methods such as:

```text
aggregate_children_P_into_parent_S
calcS2P
```

when they exist on the test node objects.

---

## 6. Suggested Files

Please add:

```text
pysi/cases/japanese_rice/rice_backward_planning_after_seed.py
tests/test_japanese_rice_backward_planning_after_seed.py
```

Please update only if useful:

```text
pysi/cases/japanese_rice/__init__.py
```

Optional smoke runner:

```text
pysi/runners/run_japanese_rice_backward_planning_after_seed_smoke.py
```

If adding the optional runner is too much, focused tests are sufficient.

---

## 7. Minimal Smoke Strategy

### 7.1 Build or use a small product-specific PlanNode tree

Use a small actual-like PlanNode tree with the minimum methods required by the selected Backward Planning function.

Example:

```text
ROOT_RICE
    └── DAD_RICE
          ├── DEMAND_HOUSEHOLD_TOKYO
          └── DEMAND_FOOD_SERVICE_TOKYO
```

Each node should have:

```text
name
children
parent
psi4demand
psi4supply
```

If testing `outbound_backward_leaf_to_MOM`, the node objects may also need:

```text
aggregate_children_P_into_parent_S
calcS2P
```

Use the smallest test object that safely exercises existing logic.

---

### 7.2 Seed initial Rice demand

Seed demand lots into leaf nodes using the existing Rice input adapter pipeline.

Expected seed location:

```text
DEMAND_HOUSEHOLD_TOKYO.psi4demand[w][S]
DEMAND_FOOD_SERVICE_TOKYO.psi4demand[w][S]
```

Then run selected Backward Planning logic.

---

### 7.3 Expected behavior

Because existing Backward Planning internals may vary, avoid over-specifying exact bucket movement in the first smoke.

The first smoke should verify safe invariants:

```text
1. Backward Planning runs without error.
2. PSI buckets remain lists.
3. PSI bucket items remain Lot_ID strings.
4. Seeded Lot_IDs are not lost.
5. Some parent / upstream demand bucket receives Lot_IDs if supported by existing behavior.
6. W40 / W41 seed weeks remain valid.
```

---

## 8. Safety Invariants

After Backward Planning:

```text
Every psi4demand[w][bucket] must be a list.
Every item in psi4demand[w][bucket] should be a Lot_ID string.
No bucket should contain numeric quantity values.
Seeded Lot_IDs should remain somewhere in the demand-layer tree unless explicitly consumed by known logic.
```

For the first smoke, it is acceptable to check that seeded Lot_IDs are present somewhere in the demand tree after planning.

---

## 9. Suggested Result Dataclass

Please implement:

```python
@dataclass
class RiceBackwardPlanningAfterSeedResult:
    product_name: str
    seed_count: int = 0
    backward_planning_ran: bool = False
    lot_ids_before: set[str] = field(default_factory=set)
    lot_ids_after: set[str] = field(default_factory=set)
    missing_lot_ids_after: set[str] = field(default_factory=set)
    non_list_bucket_errors: list[dict] = field(default_factory=list)
    non_string_lot_errors: list[dict] = field(default_factory=list)
    touched_nodes: list[str] = field(default_factory=list)
    message: str = ""
```

---

## 10. Suggested Main Function

Please implement:

```python
def run_rice_backward_planning_after_seed_smoke(
    *,
    out_root,
    in_root,
    product_name: str,
    case_data,
    dry_run_seed: bool = False,
) -> RiceBackwardPlanningAfterSeedResult:
    ...
```

Expected flow:

```text
1. build Rice WeeklyPlanRows
2. generate LotHeaders and PsiSeedRecords
3. seed into product-specific PlanNode tree
4. collect seeded Lot_IDs before planning
5. run selected Backward Planning function
6. inspect psi4demand buckets after planning
7. return structured result
```

---

## 11. PSI Inspection Helpers

Please add small inspection helpers.

### 11.1 Collect Lot_IDs

```python
def collect_lot_ids_from_demand_tree(root) -> set[str]:
    ...
```

### 11.2 Validate PSI bucket structure

```python
def validate_psi_buckets_are_lot_id_lists(root, *, layer="demand") -> list[dict]:
    ...
```

Expected checks:

```text
psi object exists
week row is list
bucket is list
items are str
```

---

## 12. Tests

Please add:

```text
tests/test_japanese_rice_backward_planning_after_seed.py
```

Required tests:

```text
1. Rice seed can be applied before Backward Planning.
2. Backward Planning function runs on seeded tree.
3. PSI buckets remain lists after Backward Planning.
4. No numeric quantities are inserted into PSI buckets.
5. Seeded Lot_IDs are still present somewhere in demand tree after planning.
6. W40 / W41 boundary indices remain correct.
```

Optional tests:

```text
7. Parent node receives aggregated demand lots if existing behavior supports it.
8. Missing method is handled with clear skip or fallback.
```

---

## 13. Test Commands

Please run:

```bat
python -m pytest tests/test_japanese_rice_backward_planning_after_seed.py
python -m pytest tests/test_japanese_rice_actual_prod_tree_seed_integration.py
python -m pytest tests/test_japanese_rice_real_plannode_seed_integration.py
python -m pytest tests/test_japanese_rice_plan_input_integration.py
python -m pytest tests/test_plan_input_plan_node_seeding.py
python -m pytest tests/test_japanese_rice_case_smoke.py
```

Optional:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

If broader tests fail due to unrelated optional dependencies, report separately.

---

## 14. Completion Criteria

This request is complete when:

```text
[OK] rice_backward_planning_after_seed.py exists
[OK] seeded Rice PlanNode tree can be passed to Backward Planning smoke
[OK] selected Backward Planning function runs without error
[OK] PSI buckets remain Lot_ID lists
[OK] no numeric quantities are inserted
[OK] seeded Lot_IDs are not lost
[OK] W40 / W41 boundary remains valid
[OK] focused tests pass
[OK] no Forward Planning execution
[OK] no GUI / run_full_plan / loader changes
```

---

## 15. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. Selected Backward Planning function used
4. Test commands executed
5. Test results
6. Any limitations or follow-up tasks
```

Please do not proceed into:

```text
Forward Planning execution
demand-to-supply bridge
existing monthly loader refactor
GUI integration
run_full_plan integration
cost / KPI evaluation
Management Issue Generation
```

This request is only for:

```text
Rice Case Backward Planning After Seed smoke
```