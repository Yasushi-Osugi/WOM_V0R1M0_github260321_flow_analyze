# run_full_plan Explicit Pipeline Feature Flag Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-22  
**Status:** Design memo  
**Target path:** `docs/design/run_full_plan_explicit_pipeline_feature_flag.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/run_full_plan_explicit_bridge_capacity_pipeline.md`
- `docs/design/explicit_bridge_capacity_pipeline_runner_completion.md`
- `docs/design/e2e_bridge_forward_capacity_smoke_completion.md`
- `docs/design/weekly_forward_push_with_capacity_psi_engine_completion.md`
- `docs/design/e2e_demand_to_supply_bridge_flow_completion_overview.md`

---

## 1. Purpose

This memo defines **Phase 2: feature-flagged run_full_plan integration** for the explicit bridge + capacity pipeline.

Phase 1 completed the standalone pipeline runner:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
```

with:

```text
run_explicit_bridge_capacity_pipeline(...)
```

The purpose of Phase 2 is to connect this runner to the existing `run_full_plan` flow safely, behind a feature flag.

The goal is:

```text
existing run_full_plan behavior remains unchanged by default
    ↓
when explicitly enabled
    ↓
run_explicit_bridge_capacity_pipeline(...) is called
    ↓
result is attached to ctx/env for reporting and later GUI display
```

---

## 2. Current Completed State

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

This has already been wrapped by:

```text
run_explicit_bridge_capacity_pipeline(...)
```

The current pipeline runner is additive and does not modify:

```text
run_full_plan
GUI
loaders
cost/KPI
Management Issue modules
```

---

## 3. Phase 2 Design Goal

Phase 2 should add a controlled hook point into `run_full_plan`.

The default behavior must remain:

```text
enable_explicit_bridge_capacity_pipeline = False
```

Only when explicitly enabled should `run_full_plan` call:

```python
run_explicit_bridge_capacity_pipeline(...)
```

and store the returned result.

---

## 4. Non-Goals

Phase 2 must not implement:

```text
GUI display
Management Issue generation
Cost / KPI integration
OR optimization
automatic replanning
database persistence
large loader refactoring
```

Phase 2 is only:

```text
feature-flagged run_full_plan integration
```

---

## 5. Feature Flag Policy

### 5.1 Recommended flag name

Use:

```python
ctx["enable_explicit_bridge_capacity_pipeline"]
```

Default:

```python
False
```

### 5.2 Avoid ambiguous aliases

Preferred:

```text
enable_explicit_bridge_capacity_pipeline
```

Do not introduce similar names such as:

```text
use_explicit_pipeline
enable_bridge_pipeline
run_capacity_pipeline
```

unless backward compatibility requires them.

### 5.3 Default behavior

If the key is missing:

```python
ctx.get("enable_explicit_bridge_capacity_pipeline", False)
```

must evaluate to:

```python
False
```

Therefore existing runs remain unchanged.

---

## 6. Required Context Inputs

When the feature flag is enabled, `run_full_plan` or its pipeline context must provide the inputs required by:

```python
run_explicit_bridge_capacity_pipeline(...)
```

Required inputs:

```text
outbound_root
inbound_root
product
mom_policy
backward_weekly_capability
forward_weekly_capacity
```

Suggested ctx keys:

```python
ctx["explicit_pipeline_outbound_root"]
ctx["explicit_pipeline_inbound_root"]
ctx["explicit_pipeline_product"]
ctx["explicit_pipeline_mom_policy"]
ctx["explicit_pipeline_backward_weekly_capability"]
ctx["explicit_pipeline_forward_weekly_capacity"]
```

Optional ctx keys:

```python
ctx["explicit_pipeline_bridge_a_mode"]
ctx["explicit_pipeline_bridge_b_policy"]
ctx["explicit_pipeline_bridge_b_mode"]
ctx["explicit_pipeline_max_early_build_weeks"]
ctx["explicit_pipeline_cap_i_mode"]
ctx["explicit_pipeline_debug"]
```

Recommended defaults:

```python
bridge_a_mode = "replace"
bridge_b_policy = "s_p_only"
bridge_b_mode = "replace"
max_early_build_weeks = 13
cap_i_mode = "soft"
debug = False
```

---

## 7. Output Attachment Policy

The returned result should be attached to `ctx`.

Recommended key:

```python
ctx["explicit_bridge_capacity_pipeline_result"] = result
```

Optional later env attribute:

```python
env.explicit_bridge_capacity_pipeline_result = result
```

MVP recommendation:

```text
Use ctx first.
Only attach to env if current run_full_plan conventions already use env for similar outputs.
```

This keeps the integration minimal and avoids changing environment shape unnecessarily.

---

## 8. Hook Placement

The explicit bridge + capacity pipeline should run only after the upstream outbound demand-side plan has produced:

```text
outbound supply_point.psi4demand[w][P]
```

and before downstream reporting / forward execution logic that depends on:

```text
psi4supply
```

Conceptual placement:

```text
run_full_plan
    ↓
input/load/seed
    ↓
outbound backward planning
    ↓
if enable_explicit_bridge_capacity_pipeline:
        run_explicit_bridge_capacity_pipeline(...)
        ctx["explicit_bridge_capacity_pipeline_result"] = result
    ↓
continue existing reporting / output steps
```

Exact placement should be confirmed by inspecting the current `run_full_plan` implementation.

---

## 9. Recommended Integration Helper

To keep `run_full_plan` small, add a small helper function.

Suggested location:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
```

Suggested helper:

```python
def maybe_run_explicit_bridge_capacity_pipeline(ctx: dict) -> object | None:
    if not ctx.get("enable_explicit_bridge_capacity_pipeline", False):
        return None

    result = run_explicit_bridge_capacity_pipeline(
        outbound_root=ctx["explicit_pipeline_outbound_root"],
        inbound_root=ctx["explicit_pipeline_inbound_root"],
        product=ctx["explicit_pipeline_product"],
        mom_policy=ctx["explicit_pipeline_mom_policy"],
        backward_weekly_capability=ctx["explicit_pipeline_backward_weekly_capability"],
        forward_weekly_capacity=ctx["explicit_pipeline_forward_weekly_capacity"],
        bridge_a_mode=ctx.get("explicit_pipeline_bridge_a_mode", "replace"),
        bridge_b_policy=ctx.get("explicit_pipeline_bridge_b_policy", "s_p_only"),
        bridge_b_mode=ctx.get("explicit_pipeline_bridge_b_mode", "replace"),
        max_early_build_weeks=ctx.get("explicit_pipeline_max_early_build_weeks", 13),
        cap_i_mode=ctx.get("explicit_pipeline_cap_i_mode", "soft"),
        debug=ctx.get("explicit_pipeline_debug", False),
    )
    ctx["explicit_bridge_capacity_pipeline_result"] = result
    return result
```

This helper keeps `run_full_plan` integration to a small, reviewable call.

---

## 10. Missing Input Behavior

If the flag is disabled:

```text
missing explicit pipeline inputs must not matter
```

If the flag is enabled but required inputs are missing, fail clearly.

Recommended behavior:

```python
raise ValueError("explicit bridge capacity pipeline enabled but ctx[...] is missing")
```

The error should identify the missing key.

Do not silently skip when the flag is enabled.

Reason:

```text
If the user explicitly enables the pipeline, silent skip hides configuration errors.
```

---

## 11. Result Summary Logging

When debug is enabled, log a compact summary:

```text
explicit bridge capacity pipeline:
    missing_lot_ids = N
    blocked_lot_ids = N
    overflow_i_lot_ids = N
    capacity_violations = N
    non_list_bucket_errors = N
    non_string_lot_errors = N
```

Avoid verbose full Lot_ID dumps by default.

---

## 12. Safety Invariants

The Phase 2 hook must preserve:

```text
1. Existing run_full_plan behavior remains unchanged when flag is off.
2. GUI behavior remains unchanged.
3. Existing loaders remain unchanged.
4. PSI buckets remain list[str].
5. No numeric quantities are inserted.
6. Lot_ID identity is preserved.
7. Pipeline result is stored, not immediately converted to KPI/issue output.
8. No automatic replan is executed.
```

---

## 13. Testing Strategy

### 13.1 Flag-off test

Add a test verifying:

```text
enable_explicit_bridge_capacity_pipeline = False
```

or missing flag:

```text
pipeline runner is not called
ctx does not receive explicit_bridge_capacity_pipeline_result
existing behavior is unchanged
```

If direct `run_full_plan` testing is heavy, test `maybe_run_explicit_bridge_capacity_pipeline(ctx)` in isolation.

### 13.2 Flag-on happy path test

Add a test with the minimal known topology:

```text
outbound supply_point
inbound supply_point
    ├── MOM_ASIA
    └── MOM_EURO
```

Set:

```python
ctx["enable_explicit_bridge_capacity_pipeline"] = True
```

Provide required ctx inputs.

Verify:

```text
ctx["explicit_bridge_capacity_pipeline_result"] exists
result.missing_lot_ids == []
result.non_list_bucket_errors == []
result.non_string_lot_errors == []
```

### 13.3 Missing input test

Enable flag but omit a required key.

Verify:

```text
ValueError is raised
error message includes missing key name
```

### 13.4 Existing tests to protect

Run:

```bat
python -m pytest tests/test_explicit_bridge_capacity_pipeline.py
python -m pytest tests/test_e2e_bridge_forward_capacity_smoke.py
python -m pytest tests/test_weekly_forward_push_with_capacity.py
python -m pytest tests/test_e2e_demand_to_supply_bridge_flow_smoke.py
python -m pytest tests/test_demand_to_supply_execution_bridge.py
python -m pytest tests/test_capacity_aware_inbound_backward_planning.py
python -m pytest tests/test_japanese_rice_case_smoke.py
```

Optional:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

---

## 14. Recommended Files for Phase 2 Implementation

Preferred minimal implementation:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
tests/test_explicit_bridge_capacity_pipeline_feature_flag.py
```

If actual `run_full_plan` hook is added in Phase 2:

```text
<current run_full_plan module>
tests/test_run_full_plan_explicit_bridge_capacity_pipeline.py
```

However, first MVP of Phase 2 may stop at:

```text
maybe_run_explicit_bridge_capacity_pipeline(ctx)
```

without changing `run_full_plan`.

Then a subsequent micro-task can place the helper call inside the actual `run_full_plan`.

---

## 15. Why Helper First Is Safer

A helper-first approach allows testing the feature flag behavior without touching the heavy full-plan execution path.

Sequence:

```text
Phase 2a:
    add maybe_run_explicit_bridge_capacity_pipeline(ctx)
    test flag-off / flag-on / missing input

Phase 2b:
    insert helper into run_full_plan at confirmed hook point
    test default unchanged
```

This reduces risk and makes the integration reviewable.

---

## 16. Completion Criteria for This Design

This design is complete when it defines:

```text
[OK] feature flag name
[OK] default flag-off behavior
[OK] required ctx inputs
[OK] result ctx output key
[OK] missing input behavior
[OK] helper function concept
[OK] hook placement concept
[OK] safety invariants
[OK] test strategy
[OK] recommended Phase 2a / Phase 2b split
```

---

## 17. Summary

Phase 2 should integrate the explicit bridge + capacity pipeline into the full-plan world carefully.

The correct first move is not a broad `run_full_plan` rewrite.

The correct first move is:

```text
feature flag helper
    ↓
tested in isolation
    ↓
small run_full_plan hook
```

The intended flow is:

```text
if ctx["enable_explicit_bridge_capacity_pipeline"]:
    result = run_explicit_bridge_capacity_pipeline(...)
    ctx["explicit_bridge_capacity_pipeline_result"] = result
```

The default must remain:

```text
feature flag off
existing behavior unchanged
```

This protects the existing WOM execution path while opening the door to the new explicit bridge + capacity pipeline.
