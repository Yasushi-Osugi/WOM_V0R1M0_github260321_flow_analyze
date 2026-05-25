# Rice Case Backward Planning After Seed Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-18  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Rice Case Backward Planning After Seed**.

The purpose of this milestone was to verify that Rice Case weekly input, after being seeded into WOM / PySI V0R8-compatible PlanNode `psi4demand`, can be passed safely into existing Backward Planning logic.

The target flow was:

```text
Rice weekly input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
PlanNode.psi4demand seed
    ↓
Backward Planning smoke
```

This milestone confirms that the new input adapter pipeline can feed existing WOM demand-layer planning behavior without violating V0R8 PSI semantics.

---

## 2. Background

Before this milestone, the following pipeline had already been completed.

### Input normalization

```text
monthly / weekly / case_weekly input
    ↓
canonical WeeklyPlanRow
```

### Lot and seed generation

```text
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
in-memory PSI seed table
```

### PlanNode seeding

```text
PsiSeedRecord
    ↓
PlanNode.psi4demand / psi4supply
```

### Rice Case PlanNode seed integration

```text
Rice weekly input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
actual-like product-specific PlanNode tree
```

This milestone adds the next controlled step:

```text
seeded PlanNode.psi4demand
    ↓
existing Backward Planning smoke
```

---

## 3. Critical WOM / PySI V0R8 Assumptions

### 3.1 Backward Planning operates on `psi4demand`

Backward Planning is a demand-layer process.

Initial seed:

```text
PlanNode.psi4demand[w][S]
```

Backward Planning propagates demand lots through:

```text
psi4demand[w][S, CO, I, P]
```

and through the product-specific planning tree.

---

### 3.2 PSI buckets are Lot_ID lists

The V0R8 canonical PSI structure remains:

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

The most important rule remains:

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

Quantity is still:

```python
quantity = len(node.psi4demand[w][bucket])
```

---

## 4. Implemented Files

This milestone added:

```text
pysi/cases/japanese_rice/rice_backward_planning_after_seed.py
tests/test_japanese_rice_backward_planning_after_seed.py
```

It also updated:

```text
docs/codex_requests/rice_case_backward_planning_after_seed_request.md
```

with branch and file verification instructions.

---

## 5. Implemented Features

### 5.1 RiceBackwardPlanningAfterSeedResult

A structured result object was added.

It records:

```text
product_name
seed_count
backward_planning_ran
lot_ids_before
lot_ids_after
missing_lot_ids_after
non_list_bucket_errors
non_string_lot_errors
touched_nodes
message
```

This makes the smoke result auditable.

---

### 5.2 collect_lot_ids_from_demand_tree

A helper was added to collect Lot_IDs from the demand-layer tree.

Purpose:

```text
capture lot IDs before and after Backward Planning
verify seeded lots are not lost
```

---

### 5.3 validate_psi_buckets_are_lot_id_lists

A helper was added to validate the V0R8 PSI bucket invariant.

It checks:

```text
psi object exists
week row is list
bucket is list
bucket items are strings
```

This ensures that Backward Planning does not introduce numeric quantities into PSI buckets.

---

### 5.4 run_rice_backward_planning_after_seed_smoke

The main smoke helper was added.

Conceptual flow:

```text
1. build Rice WeeklyPlanRows
2. generate LotHeaders and PsiSeedRecords
3. seed into product-specific PlanNode tree
4. collect Lot_IDs before Backward Planning
5. run selected Backward Planning function
6. inspect psi4demand after Backward Planning
7. return RiceBackwardPlanningAfterSeedResult
```

---

## 6. Selected Backward Planning Function

The smoke uses the existing V0R8 engine function:

```python
outbound_backward_leaf_to_MOM(out_root, in_root, layer="demand")
```

Reason:

```text
1. It is already part of the existing full planning sequence.
2. It operates on the demand layer.
3. It does not require GUI.
4. It is a suitable first smoke target for Backward Planning after seed.
```

This milestone does not claim to validate the full Backward Planning universe.  
It validates that the seeded demand tree can be accepted by an existing Backward Planning function without breaking PSI structure.

---

## 7. Test Summary

New focused test:

```bat
python -m pytest tests/test_japanese_rice_backward_planning_after_seed.py
```

Result:

```text
2 passed
```

Compatibility tests also passed:

```bat
python -m pytest tests/test_japanese_rice_actual_prod_tree_seed_integration.py
python -m pytest tests/test_japanese_rice_real_plannode_seed_integration.py
python -m pytest tests/test_japanese_rice_plan_input_integration.py
python -m pytest tests/test_plan_input_plan_node_seeding.py
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results:

```text
tests/test_japanese_rice_actual_prod_tree_seed_integration.py: 8 passed
tests/test_japanese_rice_real_plannode_seed_integration.py: 6 passed
tests/test_japanese_rice_plan_input_integration.py: 4 passed
tests/test_plan_input_plan_node_seeding.py: 11 passed
tests/test_japanese_rice_case_smoke.py: 1 passed
tests/test_covid_vaccine_with_capacity_push.py: 1 passed
```

---

## 8. Completion Criteria

This milestone satisfies the intended completion criteria.

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
[OK] no psi4demand to psi4supply bridge
[OK] no GUI changes
[OK] no run_full_plan changes
[OK] no existing loader refactor
```

---

## 9. Latest Commit

Implementation was completed with:

```text
cab180c Add Rice case backward planning after seed smoke
```

Work was performed on:

```text
feature/with-capacity-psi-engine-v0r2
```

---

## 10. Important Boundary

This milestone still does not execute:

```text
Forward Planning
psi4demand → psi4supply bridge
existing monthly loader refactor
GUI integration
cost / KPI evaluation
Management Issue Generation
```

It only verifies:

```text
PlanNode.psi4demand seed
    ↓
Backward Planning smoke
```

---

## 11. Meaning of This Milestone

This milestone is important because it confirms that the new input pipeline can feed existing WOM Backward Planning safely.

Before:

```text
Rice weekly input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
PlanNode.psi4demand seed
```

Now:

```text
Rice weekly input
    ↓
PlanNode.psi4demand seed
    ↓
Backward Planning smoke
```

This confirms that the input adapter pipeline is no longer isolated from the planning engine world.

---

## 12. Future Milestones

### 12.1 Demand-to-supply bridge

Next natural milestone:

```text
psi4demand
    ↓
psi4supply
```

This will prepare the demand-side planning result for Forward Planning.

---

### 12.2 Forward Planning after bridge

Future flow:

```text
psi4supply
    ↓
Forward Planning
```

This will validate execution-side PSI movement after demand allocation.

---

### 12.3 E2E Rice Case smoke

Longer-term flow:

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

### 12.4 Existing monthly loader refactor

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

This should be done after the full seed → backward → bridge → forward flow is stable.

---

## 13. Summary

Rice Case Backward Planning After Seed completed the first controlled connection between the new input pipeline and existing WOM Backward Planning logic.

The completed path is:

```text
Rice weekly input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
PlanNode.psi4demand seed
    ↓
Backward Planning smoke
```

The key invariant remains intact:

```text
PSI buckets hold Lot_ID lists.
Quantity is len(list).
Lot attributes live outside PSI buckets.
```

This milestone proves that Rice Case data can enter the WOM demand-side planning flow through the new normalized inpu