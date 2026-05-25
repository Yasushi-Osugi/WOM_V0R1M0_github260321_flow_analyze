# Rice Case Backward Planning After Seed Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-18  
**Status:** Design memo  
**Target path:** `docs/design/rice_case_backward_planning_after_seed.md`

**Related design documents:**

- `docs/design/rice_case_actual_prod_tree_seed_integration.md`
- `docs/design/rice_case_actual_prod_tree_seed_integration_completion.md`
- `docs/design/rice_case_real_plannode_seed_integration_design.md`
- `docs/design/rice_case_weekly_input_to_plannode_seed_integration.md`
- `docs/design/rice_case_weekly_input_to_plannode_seed_integration_completion.md`
- `docs/design/wom_plan_input_granularity_adapter.md`
- `docs/design/wom_plan_input_granularity_adapter_v0r2.md`
- `docs/design/wom_plan_input_granularity_adapter_v0r3_plan_node_seeding.md`
- `docs/design/wom_plan_input_granularity_adapter_v0r3_completion.md`
- `docs/design/case_japanese_rice_crop_year_modeling_addendum.md`
- `docs/design/wom_planning_operations_commands.md`

---

## 1. Purpose

This memo defines the next controlled integration stage for the Japanese Rice Case.

The previous milestones verified that Rice Case weekly input can be seeded into PlanNode-compatible PSI structures.

Completed flow so far:

```text
Rice Case weekly supply / demand data
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
mock PlanNode
    ↓
real-like PlanNode tree
    ↓
actual product-specific PlanNode tree integration API
```

This memo defines the next step:

```text
PlanNode.psi4demand seed
    ↓
Backward Planning
    ↓
demand allocation result in psi4demand
```

The purpose is to verify that existing WOM / PySI V0R8 Backward Planning logic can operate on Rice Case-seeded `psi4demand` data.

This is still a controlled smoke integration.

It should not yet run Forward Planning, GUI, full `run_full_plan`, or Management Issue Generation.

---

## 2. Background

The Plan Input Granularity Adapter pipeline now supports:

```text
monthly / weekly / case_weekly input
    ↓
canonical WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
PlanNode.psi4demand / psi4supply
```

The Rice Case integration has already verified:

```text
Rice weekly input
    ↓
actual-like product-specific PlanNode.psi4demand seed
```

The next question is:

```text
After Rice lots are seeded into psi4demand,
can the existing Backward Planning logic propagate those lots through the demand layer?
```

---

## 3. Critical WOM / PySI V0R8 Assumptions

### 3.1 Physical node and PlanNode are different

WOM has at least two node worlds:

```text
Physical layer:
    product-independent GUI / map / NetworkX node world

Planning layer:
    product-specific PlanNode tree world
```

This integration targets the planning layer.

It must not use physical GUI nodes as the planning target.

---

### 3.2 Backward Planning operates on `psi4demand`

Backward Planning is a demand-layer process.

Initial input:

```text
PlanNode.psi4demand[w][S]
```

Expected propagation:

```text
psi4demand[w][S]
    ↓
psi4demand[w][CO]
    ↓
psi4demand[w][I]
    ↓
psi4demand[w][P]
```

and / or tree propagation through parent-child relationships, depending on existing V0R8 functions.

---

### 3.3 PSI buckets contain Lot_ID lists

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

PSI buckets must contain Lot_ID lists, not numeric quantities.

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

---

## 4. Current Integration State

### 4.1 Completed input pipeline

The current Rice input pipeline has already verified:

```text
Rice weekly supply / demand
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
actual-like PlanNode.psi4demand seed
```

### 4.2 Completed seeding behavior

Completed seed behavior includes:

```text
demand rows:
    seed to psi4demand[w][S]

supply rows:
    seed to psi4demand[w][P]
```

The next smoke should check whether existing Backward Planning functions can consume this seeded state.

---

## 5. Integration Scope

### 5.1 In Scope

This stage should define and later implement:

```text
1. Build or use a small product-specific Rice PlanNode tree.
2. Seed Rice weekly input into psi4demand using existing adapter pipeline.
3. Run selected existing Backward Planning function(s) on that PlanNode tree.
4. Verify that Lot_IDs remain lists.
5. Verify that demand-side PSI buckets are updated as expected.
6. Verify that Rice W40 / W41 boundary remains preserved.
7. Verify no numeric quantities are inserted into PSI buckets.
8. Provide a focused smoke test.
```

### 5.2 Out of Scope

This stage should not:

```text
1. Run Forward Planning.
2. Copy psi4demand to psi4supply.
3. Modify GUI.
4. Modify run_full_plan.
5. Refactor existing S_month / P_month loader.
6. Implement full Rice network.
7. Implement cost / KPI / Management Issue Generation.
8. Implement optimization.
```

---

## 6. Candidate Existing Backward Planning Functions

The following existing engine functions are likely relevant.

```text
outbound_backward_leaf_to_MOM(...)
inbound_backward_MOM_to_leaf(...)
allocate_markets_to_moms(...)
inbound_MOM_leveling_vs_capacity(...)
```

The first smoke should use the smallest safe existing function.

Candidate first function:

```python
outbound_backward_leaf_to_MOM(out_root, in_root, layer="demand")
```

Reason:

- It is already part of `_run_planning_sequence`.
- It operates on the demand layer.
- It aggregates child P to parent S and calls `calcS2P`.
- It is an existing V0R8 function and should not require GUI.

If this function is too broad for the first test, use smaller PlanNode methods such as:

```text
aggregate_children_P_into_parent_S
calcS2P
```

when available on the test nodes.

---

## 7. Minimal Smoke Strategy

### 7.1 Start with actual-like PlanNode tree

Use a small real-like tree with nodes that implement the minimum required methods.

Example:

```text
ROOT_RICE
    └── DAD_RICE
          ├── DEMAND_HOUSEHOLD_TOKYO
          └── DEMAND_FOOD_SERVICE_TOKYO
```

or, if using existing PlanNode class safely:

```text
use actual PlanNode objects with:
    name
    children
    parent
    psi4demand
    psi4supply
    calcS2P
    aggregate_children_P_into_parent_S
```

---

### 7.2 Seed initial demand lots

Seed demand rows into leaf nodes:

```text
DEMAND_HOUSEHOLD_TOKYO.psi4demand[w][S]
DEMAND_FOOD_SERVICE_TOKYO.psi4demand[w][S]
```

Then run Backward Planning.

---

### 7.3 Expected behavior

The exact bucket transition depends on existing V0R8 methods.

The first test should verify only safe invariants:

```text
1. Backward Planning runs without error.
2. No PSI bucket becomes numeric.
3. Lot_ID lists remain lists.
4. Some parent / upstream demand bucket receives Lot_IDs.
5. Seeded Lot_IDs are not lost.
6. W40 / W41 seeded weeks remain at expected indices.
```

Avoid over-specifying internal bucket movement until existing function behavior is fully mapped.

---

## 8. Required Safety Invariants

After Backward Planning:

```text
Every psi4demand[w][bucket] must be a list.
Every item in psi4demand[w][bucket] should be a Lot_ID string.
No bucket should contain numeric quantity values.
No seeded Lot_ID should disappear unless explicitly consumed by a known algorithm.
```

For the first smoke, it is acceptable to check that seeded lot IDs are present somewhere in the demand-layer tree after planning.

---

## 9. Proposed Integration Function

Suggested function:

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
4. run selected Backward Planning function
5. inspect psi4demand buckets
6. return structured result
```

---

## 10. Result Object

Suggested dataclass:

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

## 11. PSI Inspection Helpers

Add small inspection helpers.

### 11.1 Collect lot IDs

```python
def collect_lot_ids_from_demand_tree(root) -> set[str]:
    ...
```

### 11.2 Validate bucket structure

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

Add:

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

## 13. Existing Tests to Run

Run:

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

---

## 14. Completion Criteria

This stage is complete when:

```text
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

## 15. Future Work

### 15.1 Demand-to-supply bridge

After Backward Planning is verified:

```text
psi4demand
    ↓
psi4supply
```

### 15.2 Forward Planning after bridge

After demand-to-supply bridge:

```text
psi4supply
    ↓
Forward Planning
```

### 15.3 E2E Rice Case smoke

Eventually:

```text
Rice weekly input
    ↓
PlanNode seed
    ↓
Backward Planning
    ↓
demand-to-supply bridge
    ↓
Forward Planning
    ↓
PSI / Cost / KPI outputs
```

---

## 16. Summary

This memo defines the first controlled step from **PlanNode seeding** to **Backward Planning execution**.

The essential idea is:

```text
Seed Rice demand lots into psi4demand[w][S].
Run existing Backward Planning.
Verify that V0R8 PSI semantics remain intact.
```

This stage is not about full planning output yet.

It is about proving that the new input pipeline can feed existing WOM Backward Planning safely.