# Rice Case Actual Product Tree Seed Integration Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-17  
**Status:** Completion memo  
**Branch:** `feature/rice-case-actual-plannode-seed-v0r1`

---

## 1. Purpose

This memo summarizes the completion status of **Rice Case Actual Product Tree Seed Integration**.

The purpose of this milestone was to connect Japanese Rice Case weekly input data to the new WOM Plan Input Granularity Adapter pipeline and verify that it can seed product-specific PlanNode trees through an actual product-tree style interface.

The completed target flow is:

```text
Rice Case weekly supply / demand data
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
actual-like product-specific PlanNode tree
    ↓
PlanNode.psi4demand / psi4supply
```

This milestone remains an input-layer integration. It does not execute Backward Planning or Forward Planning.

---

## 2. Background

The WOM Plan Input Granularity Adapter pipeline had already completed the following stages.

### v0r1: Input granularity normalization

```text
monthly / weekly / case_weekly input
    ↓
canonical WeeklyPlanRow
```

### v0r2: Lot and PSI seed generation

```text
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
in-memory PSI seed table
```

### v0r3: PlanNode PSI seeding

```text
PsiSeedRecord
    ↓
PlanNode.psi4demand / psi4supply
```

The Rice Case had also already been validated up to:

```text
Rice weekly input
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
```

This milestone adds the next bridge toward actual WOM product-specific tree usage.

---

## 3. Critical WOM / PySI V0R8 Assumptions

### 3.1 Physical node and PlanNode are different

WOM has two node worlds.

```text
Physical layer:
    product-independent GUI / map / NetworkX node world

Planning layer:
    product-specific PlanNode tree world
```

This integration targets the planning layer only.

It does not seed physical GUI nodes.

---

### 3.2 Product-specific PlanNode tree is the target

The target interface is compatible with:

```text
prod_tree_dict_OT[product_name]
prod_tree_dict_IN[product_name]
```

or with explicit outbound / inbound roots.

The completed integration supports root resolution through:

```text
explicit outbound_root / inbound_root
prod_tree_dict_OT / prod_tree_dict_IN fallback
```

---

### 3.3 PSI bucket structure

The canonical V0R8 PSI structure remains:

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

---

### 3.4 PSI buckets contain Lot_ID lists, not quantities

The most important invariant remains:

```text
PSI buckets contain Lot_ID lists, not numeric quantities.
```

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

Lot attributes remain outside PSI buckets.

---

## 4. Implemented Files

This milestone added or updated the following files.

```text
pysi/cases/japanese_rice/__init__.py
pysi/cases/japanese_rice/rice_actual_prod_tree_seed_integration.py
tests/test_japanese_rice_actual_prod_tree_seed_integration.py
```

---

## 5. Implemented Features

### 5.1 RiceActualPlanNodeSeedResult

A structured result object was added to summarize actual product tree seeding.

It records:

```text
scenario_id
product_name
weekly_rows_count
lot_count
seed_record_count
plan_node_seeded_count
missing_roots
missing_node_ids
duplicate_node_ids
invalid_weeks
dry_run
```

This makes seeding auditable and safe.

---

### 5.2 Product root resolution

The integration resolves product-specific roots using the following priority.

```text
1. explicit outbound_root / inbound_root
2. prod_tree_dict_OT[product_name] / prod_tree_dict_IN[product_name]
3. None if not found
```

Missing roots are recorded.

No new product trees are created automatically.

---

### 5.3 PlanNode lookup from outbound / inbound roots

The integration builds PlanNode lookup dictionaries from provided roots.

It supports:

```text
outbound root
inbound root
multiple roots
duplicate tracking
```

The default duplicate policy is deterministic:

```text
first root wins
```

---

### 5.4 Rice weekly input pipeline reuse

The implementation reuses the existing pipeline instead of duplicating logic.

```text
build_rice_weekly_plan_rows
build_rice_row_attributes
weekly_rows_to_lots_and_seed_table
apply_psi_seed_records_to_plan_nodes
```

This keeps the Rice Case integration aligned with the general Plan Input Granularity Adapter.

---

### 5.5 Actual-like product tree seeding

The integration verifies that Rice weekly input can seed actual-like product-specific PlanNode trees.

Completed flow:

```text
Rice weekly input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
actual-like PlanNode tree
```

---

### 5.6 Demand / supply seeding policy

Demand rows seed to:

```text
WeeklyPlanRow(plan_type="demand")
    ↓
PsiSeedRecord(layer="demand", bucket="S")
    ↓
PlanNode.psi4demand[w][S]
```

Supply / harvest rows seed to:

```text
WeeklyPlanRow(plan_type="supply")
    ↓
PsiSeedRecord(layer="demand", bucket="P")
    ↓
PlanNode.psi4demand[w][P]
```

This keeps harvest / supply requirements in demand planning space until Backward Planning is executed in a later stage.

---

### 5.7 W40 / W41 boundary preservation

The Rice Case crop-year boundary remains preserved.

```text
2026-W40 → index 39
2026-W41 → index 40
```

This is important because:

```text
W40:
    old crop final consumption week
    new crop harvest start week

W41:
    new crop consumption start week
```

---

### 5.8 Dry-run mode

The integration supports dry-run behavior.

```text
dry_run=True:
    report what would be seeded
    do not mutate PlanNode PSI buckets

dry_run=False:
    append Lot_IDs to target PSI buckets
```

This is important before connecting to full WOM runtime flows.

---

### 5.9 Missing root / missing node handling

Missing roots and missing nodes are recorded and skipped.

The integration does not create product trees or PlanNodes automatically.

---

## 6. Test Summary

The following tests passed.

```bat
python -m pytest tests/test_japanese_rice_actual_prod_tree_seed_integration.py
```

Result:

```text
8 passed
```

Compatibility tests also passed.

```bat
python -m pytest tests/test_japanese_rice_real_plannode_seed_integration.py
python -m pytest tests/test_japanese_rice_plan_input_integration.py
python -m pytest tests/test_plan_input_plan_node_seeding.py
python -m pytest tests/test_plan_input_pipeline.py
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results:

```text
tests/test_japanese_rice_real_plannode_seed_integration.py: 6 passed
tests/test_japanese_rice_plan_input_integration.py: 4 passed
tests/test_plan_input_plan_node_seeding.py: 11 passed
tests/test_plan_input_pipeline.py: 3 passed
tests/test_japanese_rice_case_smoke.py: 1 passed
tests/test_covid_vaccine_with_capacity_push.py: 1 passed
```

---

## 7. Completion Criteria

This milestone satisfies the intended completion criteria.

```text
[OK] rice_actual_prod_tree_seed_integration.py exists
[OK] actual product tree integration function exists
[OK] explicit root resolution works
[OK] prod_tree_dict_OT / IN root resolution works
[OK] PlanNode lookup can be built from roots
[OK] Rice weekly input can seed actual-like product PlanNode tree
[OK] demand rows seed to psi4demand[w][S]
[OK] supply rows seed to psi4demand[w][P]
[OK] W40 / W41 boundary is preserved
[OK] dry-run works
[OK] missing roots / nodes are reported
[OK] PSI buckets contain Lot_ID lists, not quantities
[OK] no GUI changes
[OK] no run_full_plan changes
[OK] no loader changes
[OK] no planning engine changes
[OK] focused tests pass
```

---

## 8. Latest Commit

Implementation was completed with:

```text
c79c3e3 Add Rice case actual product tree seed integration
```

The work was performed on:

```text
feature/rice-case-actual-plannode-seed-v0r1
```

---

## 9. Important Boundary

This milestone still does not execute WOM planning logic.

It does not perform:

```text
Backward Planning
Forward Planning
demand-to-supply bridge
existing monthly loader refactor
GUI integration
database persistence
Management Issue Generation
```

It only validates safe input seeding into product-specific PlanNode tree style structures.

---

## 10. Meaning of This Milestone

This milestone is important because it moves Rice Case from test-only mock seeding toward actual WOM product-tree-compatible seeding.

Before:

```text
Rice weekly input
    ↓
mock PlanNode
```

Then:

```text
Rice weekly input
    ↓
real-like PlanNode tree
```

Now:

```text
Rice weekly input
    ↓
actual product-specific PlanNode tree integration API
```

This is the final safety bridge before running actual WOM planning logic.

---

## 11. Future Milestones

### 11.1 Run Backward Planning after seeding

Future flow:

```text
actual product-specific PlanNode PSI seed
    ↓
Backward Planning
```

This will propagate demand lots across:

```text
psi4demand[w][S, CO, I, P]
```

and through the product-specific planning tree.

---

### 11.2 Demand-to-supply bridge

Future flow:

```text
psi4demand
    ↓
psi4supply
```

This will prepare the forward execution simulation.

---

### 11.3 Forward Planning

Future flow:

```text
psi4supply
    ↓
Forward simulation
```

This will move Lot_IDs across supply-side PSI buckets.

---

### 11.4 Existing monthly loader refactor

Future flow:

```text
S_month / P_month
    ↓
canonical WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
PlanNode seeding
```

---

### 11.5 GUI case loading

Future flow:

```text
GUI selects Rice Case
    ↓
case dataset load
    ↓
PlanNode seed
    ↓
planning execution
```

---

## 12. Summary

Rice Case actual product tree seed integration has completed the next safety bridge in the WOM input pipeline.

The completed flow is:

```text
Rice Case weekly supply / demand data
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
actual-like product-specific PlanNode tree
    ↓
PlanNode.psi4demand / psi4supply
```

The key invariant remains intact:

```text
PSI buckets hold Lot_ID lists.
Quantity is len(list).
Lot attributes live outside PSI buckets.
```

This confirms that Rice Case can now enter the WOM planning structure through a safe, V0R8-compatible, product-tree-oriented seed integration path.