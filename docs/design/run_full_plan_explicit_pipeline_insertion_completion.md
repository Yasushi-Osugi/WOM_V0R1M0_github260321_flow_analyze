# run_full_plan Explicit Pipeline Insertion Phase 2b Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-23  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Phase 2b: run_full_plan explicit pipeline insertion behind feature flag**.

The purpose of this milestone was to insert the explicit bridge + capacity pipeline into the existing planning sequence in a minimal, feature-flagged way.

The completed integration path is:

```text
run_full_plan / planning sequence
    ↓
outbound demand-side preparation
    ↓
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
    ↓
maybe_run_explicit_bridge_capacity_pipeline(ctx)
    ↓
run_explicit_bridge_capacity_pipeline(...)
    ↓
ctx / env explicit pipeline result
```

The default behavior remains unchanged because the feature flag is off by default.

---

## 2. Background

Before Phase 2b, the staged integration had reached this state:

```text
isolated utilities
    ↓
explicit pipeline runner        ✅ Phase 1 completed
    ↓
feature flag helper             ✅ Phase 2a completed
    ↓
run_full_plan insertion         ← Phase 2b target
```

Phase 1 added:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
run_explicit_bridge_capacity_pipeline(...)
```

Phase 2a added:

```text
maybe_run_explicit_bridge_capacity_pipeline(ctx)
```

Phase 2b inserts the env-level adapter into the current planning sequence.

---

## 3. Implemented Files

This milestone updated or added:

```text
pysi/gui/cockpit_tk.py
pysi/plan/explicit_bridge_capacity_pipeline.py
tests/test_run_full_plan_explicit_pipeline_insertion.py
tests/__init__.py
```

Notes:

```text
tests/__init__.py
```

was added to allow test-to-test helper import in the local pytest environment.

---

## 4. Insertion Point

The smallest safe insertion point was identified in:

```text
pysi/gui/cockpit_tk.py
```

inside:

```python
CockpitApp / WOMCockpit._run_planning_sequence(...)
```

The insertion was placed immediately after:

```python
eng.outbound_backward_leaf_to_MOM(...)
```

and before downstream inbound / capacity / push-pull stages.

Conceptually:

```text
outbound backward demand-side preparation
    ↓
explicit bridge + capacity pipeline feature-flag hook
    ↓
existing downstream planning sequence
```

This satisfies the design requirement:

```text
after outbound demand/P is ready
before downstream reporting / supply-side result usage
```

---

## 5. Implemented Adapter

The adapter added in:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
```

is:

```python
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
```

Its role is to build a minimal ctx from env / planning sequence inputs and delegate to:

```python
maybe_run_explicit_bridge_capacity_pipeline(ctx)
```

Conceptual behavior:

```text
1. Read env.enable_explicit_bridge_capacity_pipeline.
2. Default to False when absent.
3. Build ctx inputs from env and current planning sequence values.
4. Call maybe_run_explicit_bridge_capacity_pipeline(ctx).
5. If result is not None, attach it to env:
       env.explicit_bridge_capacity_pipeline_result = result
6. Return result.
```

---

## 6. Feature Flag Behavior

The feature flag remains:

```python
enable_explicit_bridge_capacity_pipeline
```

Default behavior:

```text
False
```

Therefore:

```text
flag missing / False:
    no-op
    no explicit pipeline result attached
    existing behavior unchanged

flag True:
    explicit pipeline is executed
    result is attached
```

This preserves the key safety invariant:

```text
feature flag off
    ↓
existing behavior unchanged
```

---

## 7. Result Attachment

When the feature flag is on and required inputs are available, the explicit pipeline result is attached to:

```python
env.explicit_bridge_capacity_pipeline_result
```

The lower-level helper still attaches the result to:

```python
ctx["explicit_bridge_capacity_pipeline_result"]
```

The env-level result attachment prepares future reporting / GUI display without implementing them yet.

---

## 8. Missing Input Behavior

If the feature flag is on and a required input is missing, the helper preserves the Phase 2a behavior:

```python
ValueError
```

with a message naming the missing key.

This is intentional.

Reason:

```text
When the explicit pipeline is enabled, missing inputs are configuration errors.
Silent skip would hide planning defects.
```

---

## 9. GUI Boundary

This milestone did touch:

```text
pysi/gui/cockpit_tk.py
```

However, the change was limited to the planning-sequence insertion point.

This milestone did not add or change:

```text
buttons
widgets
screen layout
GUI display logic
report panels
user event behavior
```

The GUI file currently owns the planning sequence, so the minimal insertion was placed there.

The semantic planning work remains delegated to:

```python
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
```

and ultimately:

```python
run_explicit_bridge_capacity_pipeline(...)
```

---

## 10. Non-Goals Preserved

This milestone did not implement:

```text
reporting UI
Management Issue generation
Cost / KPI integration
OR optimization
ReplanCommand execution
database persistence
capacity editing UI
MOM policy editing UI
```

---

## 11. Tests Added

The new test file is:

```text
tests/test_run_full_plan_explicit_pipeline_insertion.py
```

It validates:

```text
1. flag-off default no-op
2. flag-on result attached to env
3. flag-on missing required input raises ValueError
```

---

## 12. Validation

After adding `tests/__init__.py`, the focused Phase 2b test passed:

```bat
python -m pytest tests/test_run_full_plan_explicit_pipeline_insertion.py
```

Observed result:

```text
3 passed
```

The broader compatibility test set also passed:

```bat
python -m pytest tests/test_explicit_bridge_capacity_pipeline_feature_flag.py
python -m pytest tests/test_explicit_bridge_capacity_pipeline.py
python -m pytest tests/test_e2e_bridge_forward_capacity_smoke.py
python -m pytest tests/test_weekly_forward_push_with_capacity.py
python -m pytest tests/test_e2e_demand_to_supply_bridge_flow_smoke.py
python -m pytest tests/test_demand_to_supply_execution_bridge.py
python -m pytest tests/test_capacity_aware_inbound_backward_planning.py
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results:

```text
tests/test_explicit_bridge_capacity_pipeline_feature_flag.py: 4 passed
tests/test_explicit_bridge_capacity_pipeline.py: 3 passed
tests/test_e2e_bridge_forward_capacity_smoke.py: 1 passed
tests/test_weekly_forward_push_with_capacity.py: 6 passed
tests/test_e2e_demand_to_supply_bridge_flow_smoke.py: 2 passed
tests/test_demand_to_supply_execution_bridge.py: 10 passed
tests/test_capacity_aware_inbound_backward_planning.py: 3 passed
tests/test_japanese_rice_case_smoke.py: 1 passed
tests/test_covid_vaccine_with_capacity_push.py: 1 passed
```

---

## 13. Latest Commit

Implementation was completed with:

```text
0de7fd4 Add run_full_plan explicit pipeline insertion behind feature flag
```

Work was performed on:

```text
feature/with-capacity-psi-engine-v0r2
```

---

## 14. Completion Criteria

This milestone satisfies the intended completion criteria.

```text
[OK] smallest safe planning-sequence insertion point identified
[OK] maybe_run_explicit_bridge_capacity_pipeline_from_env(...) added
[OK] maybe_run_explicit_bridge_capacity_pipeline(ctx) reused
[OK] feature flag default remains False
[OK] flag-off behavior is no-op
[OK] flag-on behavior attaches result
[OK] missing input raises ValueError
[OK] tests pass
[OK] no reporting / KPI / issue generation added
[OK] no OR optimization added
[OK] no GUI display semantics added
```

---

## 15. Meaning of This Milestone

Before Phase 2b:

```text
The explicit bridge + capacity pipeline existed,
but was outside the main planning sequence.
```

After Phase 2b:

```text
The explicit bridge + capacity pipeline is reachable from the main planning sequence,
but only when explicitly enabled by feature flag.
```

This is the first controlled bridge between the new explicit pipeline and the operational WOM planning flow.

---

## 16. Current Pipeline Position

The staged integration now stands here:

```text
isolated utilities
    ↓
explicit pipeline runner        ✅ Phase 1 completed
    ↓
feature flag helper             ✅ Phase 2a completed
    ↓
run_full_plan insertion         ✅ Phase 2b completed
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

## 17. Future Milestones

### 17.1 Reporting data export

Next target:

```text
capacity_usage
capacity_violations
blocked_lot_ids
overflow_i_lot_ids
backlog_lot_ids
shifted_lot_ids
replan_commands
```

should be exported in a stable report-friendly structure.

### 17.2 Management Issue candidates

Future work should transform planning signals into:

```text
PlanningIssue
ManagementIssue
ReplanCommand candidate
```

without executing replanning automatically.

### 17.3 Cost / KPI integration

Later work should connect explicit pipeline outputs to:

```text
service level
capacity utilization
inventory overflow
cost impact
profit impact
opportunity loss
```

### 17.4 GUI display

GUI should display the explicit pipeline result only after reporting structures are stable.

---

## 18. Summary

Phase 2b is complete.

The key achievement is:

```text
The explicit bridge + capacity pipeline is now inserted into the planning sequence behind a feature flag,
while preserving default behavior.
```

The operational principle remains:

```text
feature flag off:
    existing behavior unchanged

feature flag on:
    explicit bridge + capacity pipeline runs
    result is attached for future reporting / GUI use
```

This prepares WOM for the next phase:

```text
capacity usage / violation reporting
```
