# Explicit Bridge + Capacity Pipeline Runner MVP Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-22  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Phase 1: Explicit Bridge + Capacity Pipeline Runner MVP**.

The purpose of this milestone was to create a stable, production-oriented pipeline runner interface over the already validated E2E bridge + forward capacity smoke flow.

The completed explicit pipeline is:

```text
Bridge A
    ↓
MOM allocation
    ↓
TOBE capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
Weekly Forward PUSH with Capacity
```

This Phase 1 runner does **not** integrate with `run_full_plan` yet.

It also does **not** modify GUI behavior.

---

## 2. Background

Before this milestone, the following isolated utilities and smoke wrapper had already been implemented and tested.

### 2.1 Bridge A

```text
outbound supply_point.psi4demand[w][P]
    ↓
inbound supply_point.psi4demand[w][S]
```

### 2.2 MOM allocation

```text
inbound supply_point.psi4demand[w][S]
    ↓
MOMxxx.psi4demand[w][S]
```

### 2.3 TOBE capacity-aware inbound backward planning

```text
MOM.psi4demand[w][S]
    ↓
MOM.psi4demand[w][P]
    ↓
effective MOM capacity check
    ↓
early build / backlog
```

### 2.4 Bridge B

```text
finalized psi4demand
    ↓
psi4supply
```

### 2.5 Weekly Forward PUSH with Capacity

```text
psi4supply
    ↓
cap_P / cap_S / cap_I
    ↓
accepted / blocked / overflow lots
```

### 2.6 E2E bridge + forward capacity smoke

```text
Bridge A
    ↓
MOM allocation
    ↓
capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
Weekly Forward PUSH with Capacity
```

Phase 1 wraps this smoke into a canonical explicit pipeline runner.

---

## 3. Implemented Files

This milestone added:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
tests/test_explicit_bridge_capacity_pipeline.py
```

No `run_full_plan` file was changed.

No GUI file under `pysi/gui` was changed.

---

## 4. Implemented Runner

The implemented runner is:

```python
run_explicit_bridge_capacity_pipeline(...)
```

Its role is to provide a stable pipeline-level entry point for the explicit bridge + capacity flow.

Conceptual behavior:

```text
1. Call existing E2E bridge + forward capacity smoke.
2. Normalize smoke output into ExplicitBridgeCapacityPipelineResult.
3. Surface Lot_ID preservation information.
4. Surface blocked / overflow lot information.
5. Surface PSI invariant errors.
6. Return a pipeline-level result object.
```

This runner currently reuses:

```text
run_e2e_bridge_forward_capacity_smoke(...)
```

as the execution engine.

---

## 5. Implemented Result Object

The result dataclass is:

```python
ExplicitBridgeCapacityPipelineResult
```

It includes the requested fields:

```text
product_name

bridge_a_result
mom_allocation_result
backward_capacity_result
bridge_b_result
forward_capacity_result
smoke_result

source_lot_ids
missing_lot_ids

shifted_lot_ids
backlog_lot_ids
accepted_lot_ids
blocked_lot_ids
overflow_i_lot_ids

capacity_usage
capacity_violations
replan_commands

non_list_bucket_errors
non_string_lot_errors

message
```

For the Phase 1 MVP, the raw stage-specific result objects may remain `None`.

This is intentional.

The current MVP goal is to establish a stable explicit pipeline interface while reusing the already validated smoke wrapper.

---

## 6. Main Implementation Approach

The implementation follows the **Phase 1 MVP wrapper pattern**:

```text
existing isolated utilities
    ↓
existing E2E bridge + forward capacity smoke
    ↓
explicit pipeline runner
```

The runner does not duplicate bridge or capacity planning logic.

Instead, it calls the smoke wrapper and maps available outputs into a pipeline-level result.

This keeps Phase 1 small, safe, and testable.

---

## 7. Surfaced Outputs

The runner surfaces the following key outputs.

### 7.1 Lot_ID preservation

```text
missing_lot_ids
```

The happy path expects:

```text
missing_lot_ids == []
```

### 7.2 Blocked lots

```text
blocked_lot_ids
```

These are surfaced from the underlying smoke / forward capacity result where available.

### 7.3 Inventory overflow lots

```text
overflow_i_lot_ids
```

These are surfaced from the underlying smoke / forward capacity result where available.

### 7.4 PSI invariant errors

```text
non_list_bucket_errors
non_string_lot_errors
```

The expected healthy condition is:

```text
non_list_bucket_errors == []
non_string_lot_errors == []
```

---

## 8. Safety Boundaries

This milestone intentionally did not modify:

```text
run_full_plan
GUI
loaders
costing / KPI modules
Management Issue modules
OR optimization logic
database persistence
```

The runner is additive.

The existing `run_full_plan` behavior remains unchanged.

---

## 9. Tests Added

Focused tests were added in:

```text
tests/test_explicit_bridge_capacity_pipeline.py
```

They validate:

```text
1. run_explicit_bridge_capacity_pipeline(...) returns ExplicitBridgeCapacityPipelineResult.
2. missing_lot_ids is empty in the happy path.
3. PSI invariant error lists are empty.
4. blocked_lot_ids are surfaced.
5. overflow_i_lot_ids are surfaced.
```

---

## 10. Validation

The following tests passed.

```bat
python -m pytest tests/test_explicit_bridge_capacity_pipeline.py
```

Observed result:

```text
3 passed
```

Compatibility tests also passed:

```bat
python -m pytest tests/test_e2e_bridge_forward_capacity_smoke.py
python -m pytest tests/test_weekly_forward_push_with_capacity.py
python -m pytest tests/test_e2e_demand_to_supply_bridge_flow_smoke.py
python -m pytest tests/test_demand_to_supply_execution_bridge.py
python -m pytest tests/test_capacity_aware_inbound_backward_planning.py
python -m pytest tests/test_japanese_rice_case_smoke.py
```

Observed results:

```text
tests/test_e2e_bridge_forward_capacity_smoke.py: 1 passed
tests/test_weekly_forward_push_with_capacity.py: 6 passed
tests/test_e2e_demand_to_supply_bridge_flow_smoke.py: 2 passed
tests/test_demand_to_supply_execution_bridge.py: 10 passed
tests/test_capacity_aware_inbound_backward_planning.py: 3 passed
tests/test_japanese_rice_case_smoke.py: 1 passed
```

Optional test:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

was not run in this Phase 1 validation.

---

## 11. Latest Commit

Implementation was completed with:

```text
b99c93b Add explicit bridge capacity pipeline runner MVP
```

Work was performed on:

```text
feature/with-capacity-psi-engine-v0r2
```

---

## 12. Completion Criteria

This milestone satisfies the intended completion criteria.

```text
[OK] pysi/plan/explicit_bridge_capacity_pipeline.py exists
[OK] ExplicitBridgeCapacityPipelineResult exists
[OK] run_explicit_bridge_capacity_pipeline(...) exists
[OK] existing E2E bridge + forward capacity smoke is reused
[OK] missing_lot_ids are surfaced
[OK] blocked_lot_ids are surfaced
[OK] overflow_i_lot_ids are surfaced
[OK] non_list_bucket_errors are surfaced
[OK] non_string_lot_errors are surfaced
[OK] focused tests pass
[OK] no run_full_plan changes
[OK] no GUI changes
[OK] no loader changes
```

---

## 13. Meaning of This Milestone

This milestone creates the first canonical pipeline-level interface for the explicit bridge + capacity flow.

Before this milestone:

```text
E2E bridge + forward capacity existed as a smoke wrapper.
```

After this milestone:

```text
E2E bridge + forward capacity is accessible through a pipeline runner interface.
```

This is the required bridge between isolated smoke testing and future `run_full_plan` integration.

---

## 14. Current Pipeline Position

The completed staged integration now stands here:

```text
isolated utilities
    ↓
explicit pipeline runner   ← Phase 1 completed
    ↓
feature-flagged run_full_plan integration
    ↓
reporting
    ↓
issue candidates
    ↓
cost/KPI
    ↓
GUI display
```

---

## 15. Known MVP Limitations

The Phase 1 runner intentionally keeps some fields as future extension points.

Examples:

```text
bridge_a_result
mom_allocation_result
backward_capacity_result
bridge_b_result
forward_capacity_result
```

These may remain `None` because the runner currently wraps the existing smoke wrapper rather than directly composing every internal stage.

This is acceptable for Phase 1.

Future direct composition can populate these fields more fully.

---

## 16. Future Milestones

### 16.1 Phase 2: Feature-flagged run_full_plan integration

Next target:

```text
run_full_plan
    ↓
if enable_explicit_bridge_capacity_pipeline:
    run_explicit_bridge_capacity_pipeline(...)
```

The default should remain:

```text
enable_explicit_bridge_capacity_pipeline = False
```

### 16.2 Phase 3: Reporting data export

Future reporting should expose:

```text
capacity_usage
capacity_violations
blocked_lot_ids
overflow_i_lot_ids
backlog_lot_ids
shifted_lot_ids
replan_commands
```

### 16.3 Phase 4: Management issue candidates

Future work should transform:

```text
capacity violations
blocked lots
overflow inventory
backlog lots
```

into planning issue / management issue candidates.

### 16.4 Phase 5: GUI display

GUI should display stable pipeline results after the pipeline is integrated and tested.

---

## 17. Summary

Phase 1: Explicit Bridge + Capacity Pipeline Runner MVP is complete.

The verified flow is:

```text
Bridge A
    ↓
MOM allocation
    ↓
TOBE capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
Weekly Forward PUSH with Capacity
```

The key achievement is:

```text
The explicit E2E bridge + forward capacity flow now has a canonical runner interface,
without touching run_full_plan or GUI.
```

This prepares WOM for the next phase:

```text
feature-flagged run_full_plan integration
```
