# Explicit Pipeline Feature Flag Helper Phase 2a Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-22  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Phase 2a: Explicit Pipeline Feature Flag Helper**.

The purpose of this milestone was to add a safe feature-flag gate before inserting the explicit bridge + capacity pipeline into `run_full_plan`.

The completed helper is:

```python
maybe_run_explicit_bridge_capacity_pipeline(ctx)
```

This helper provides the controlled entry point for the explicit pipeline runner:

```python
run_explicit_bridge_capacity_pipeline(...)
```

Phase 2a does **not** modify `run_full_plan`.

Phase 2a does **not** modify GUI behavior.

---

## 2. Background

The previous milestone, Phase 1, added the explicit pipeline runner:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
```

with:

```python
run_explicit_bridge_capacity_pipeline(...)
```

That runner wraps the explicit E2E bridge + capacity flow:

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

Phase 2a adds the feature-flag helper that can later be called from `run_full_plan`.

---

## 3. Implemented Files

This milestone updated or added:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
tests/test_explicit_bridge_capacity_pipeline_feature_flag.py
```

No `run_full_plan` file was changed.

No GUI file under `pysi/gui` was changed.

No loader file was changed.

---

## 4. Implemented Helper

The implemented helper is:

```python
maybe_run_explicit_bridge_capacity_pipeline(ctx)
```

It implements the following behavior:

```text
1. If ctx["enable_explicit_bridge_capacity_pipeline"] is missing:
       return None

2. If ctx["enable_explicit_bridge_capacity_pipeline"] is False:
       return None

3. If ctx["enable_explicit_bridge_capacity_pipeline"] is True:
       validate required ctx keys

4. If required keys are present:
       call run_explicit_bridge_capacity_pipeline(...)

5. Store result into:
       ctx["explicit_bridge_capacity_pipeline_result"]

6. Return the same result object.
```

---

## 5. Feature Flag

The feature flag is:

```python
ctx["enable_explicit_bridge_capacity_pipeline"]
```

Default behavior is:

```python
ctx.get("enable_explicit_bridge_capacity_pipeline", False)
```

Therefore, if the key is missing, the helper performs a safe no-op.

This preserves existing behavior.

---

## 6. Required Context Keys

When the feature flag is `True`, the helper requires:

```python
ctx["explicit_pipeline_outbound_root"]
ctx["explicit_pipeline_inbound_root"]
ctx["explicit_pipeline_product"]
ctx["explicit_pipeline_mom_policy"]
ctx["explicit_pipeline_backward_weekly_capability"]
ctx["explicit_pipeline_forward_weekly_capacity"]
```

These are mapped into:

```python
run_explicit_bridge_capacity_pipeline(...)
```

---

## 7. Optional Context Keys

The helper supports optional parameters with defaults:

```python
ctx.get("explicit_pipeline_bridge_a_mode", "replace")
ctx.get("explicit_pipeline_bridge_b_policy", "s_p_only")
ctx.get("explicit_pipeline_bridge_b_mode", "replace")
ctx.get("explicit_pipeline_max_early_build_weeks", 13)
ctx.get("explicit_pipeline_cap_i_mode", "soft")
ctx.get("explicit_pipeline_debug", False)
```

This keeps the default Phase 2a behavior aligned with the existing explicit pipeline runner and smoke tests.

---

## 8. Missing Key Behavior

If the feature flag is `True` but a required ctx key is missing, the helper raises:

```python
ValueError
```

The error message includes the missing key name.

Conceptual example:

```text
explicit bridge capacity pipeline enabled but missing ctx key: explicit_pipeline_product
```

This is intentional.

When the user explicitly enables the pipeline, silent skip would hide configuration errors.

---

## 9. Output Context Key

When the helper runs successfully, it stores the pipeline result into:

```python
ctx["explicit_bridge_capacity_pipeline_result"]
```

The helper returns the same object:

```python
result = maybe_run_explicit_bridge_capacity_pipeline(ctx)
assert result is ctx["explicit_bridge_capacity_pipeline_result"]
```

This creates the output contract for future `run_full_plan` integration.

---

## 10. Safety Boundaries

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

The helper is additive.

The existing WOM execution path remains unchanged unless a future `run_full_plan` call explicitly invokes this helper.

---

## 11. Tests Added

Focused tests were added in:

```text
tests/test_explicit_bridge_capacity_pipeline_feature_flag.py
```

They validate:

```text
1. Flag missing means no-op.
2. Flag False means no-op.
3. Flag True happy path runs the explicit pipeline and stores result in ctx.
4. Flag True with missing required key raises ValueError.
```

---

## 12. Validation

The following focused test passed:

```bat
python -m pytest tests/test_explicit_bridge_capacity_pipeline_feature_flag.py
```

Observed result:

```text
4 passed
```

Compatibility tests also passed:

```bat
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
77044a6 Add explicit pipeline feature flag helper
```

Work was performed on:

```text
feature/with-capacity-psi-engine-v0r2
```

---

## 14. Completion Criteria

This milestone satisfies the intended completion criteria.

```text
[OK] maybe_run_explicit_bridge_capacity_pipeline(ctx) exists
[OK] flag missing returns None
[OK] flag False returns None
[OK] flag True calls run_explicit_bridge_capacity_pipeline(...)
[OK] result is stored in ctx["explicit_bridge_capacity_pipeline_result"]
[OK] missing required ctx key raises ValueError
[OK] error message names the missing key
[OK] focused tests pass
[OK] no run_full_plan changes
[OK] no GUI changes
[OK] no loader changes
```

---

## 15. Meaning of This Milestone

This milestone completes the entry gate for future `run_full_plan` integration.

Before Phase 2a:

```text
explicit pipeline runner exists,
but there is no standard feature-flag gate.
```

After Phase 2a:

```text
explicit pipeline runner can be invoked through a controlled ctx-based feature flag helper.
```

This makes future `run_full_plan` integration small and reviewable.

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
run_full_plan insertion         ← Phase 2b next
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

## 17. Future Milestone: Phase 2b

The next phase should insert the helper into the actual `run_full_plan` flow.

Target:

```text
run_full_plan
    ↓
if ctx["enable_explicit_bridge_capacity_pipeline"]:
    maybe_run_explicit_bridge_capacity_pipeline(ctx)
```

Important rule:

```text
default flag off
    ↓
existing behavior unchanged
```

The Phase 2b task should be small:

```text
1. inspect current run_full_plan hook point
2. insert helper call behind feature flag
3. verify default behavior unchanged
4. verify flag-on path attaches result to ctx/env
```

---

## 18. Summary

Phase 2a: Explicit Pipeline Feature Flag Helper is complete.

The key achievement is:

```text
The explicit bridge + capacity pipeline now has a safe ctx-based feature flag entry gate,
without touching run_full_plan or GUI.
```

This prepares WOM for the next phase:

```text
feature-flagged run_full_plan insertion
```
