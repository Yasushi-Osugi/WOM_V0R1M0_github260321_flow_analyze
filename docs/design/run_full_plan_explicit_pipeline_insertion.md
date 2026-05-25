# run_full_plan Explicit Pipeline Insertion Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-22  
**Status:** Design memo  
**Target path:** `docs/design/run_full_plan_explicit_pipeline_insertion.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/run_full_plan_explicit_bridge_capacity_pipeline.md`
- `docs/design/run_full_plan_explicit_pipeline_feature_flag.md`
- `docs/design/explicit_bridge_capacity_pipeline_runner_completion.md`
- `docs/design/explicit_pipeline_feature_flag_helper_completion.md`
- `docs/design/e2e_bridge_forward_capacity_smoke_completion.md`
- `docs/design/weekly_forward_push_with_capacity_psi_engine_completion.md`

---

## 1. Purpose

This memo defines **Phase 2b: run_full_plan insertion** for the explicit bridge + capacity pipeline.

Phase 2a completed the feature-flag helper:

```python
maybe_run_explicit_bridge_capacity_pipeline(ctx)
```

The purpose of Phase 2b is to insert this helper into the existing `run_full_plan` / planning sequence in a safe and minimal way.

The intended behavior is:

```text
default:
    existing run_full_plan behavior unchanged

feature flag ON:
    run_full_plan prepares ctx
    ↓
    maybe_run_explicit_bridge_capacity_pipeline(ctx)
    ↓
    ctx["explicit_bridge_capacity_pipeline_result"] is attached
    ↓
    existing downstream reporting continues
```

This phase should still avoid GUI changes and avoid full reporting / KPI / Management Issue integration.

---

## 2. Current Completed State

The staged integration currently stands here:

```text
isolated utilities
    ↓
explicit pipeline runner        ✅ Phase 1 completed
    ↓
feature flag helper             ✅ Phase 2a completed
    ↓
run_full_plan insertion         ← Phase 2b target
    ↓
reporting
    ↓
issue candidates
    ↓
cost/KPI
    ↓
GUI display
```

Completed helper:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
```

with:

```python
maybe_run_explicit_bridge_capacity_pipeline(ctx)
```

The helper already handles:

```text
flag missing / False:
    no-op, return None

flag True:
    validate required ctx keys
    call run_explicit_bridge_capacity_pipeline(...)
    store result in ctx["explicit_bridge_capacity_pipeline_result"]
```

---

## 3. Phase 2b Design Goal

The Phase 2b goal is deliberately small:

```text
Add a minimal call to maybe_run_explicit_bridge_capacity_pipeline(ctx)
inside the existing planning sequence,
behind the existing feature flag,
without changing default behavior.
```

The feature flag is:

```python
ctx["enable_explicit_bridge_capacity_pipeline"]
```

Default:

```python
False
```

Therefore, if this flag is not set, `run_full_plan` should behave exactly as before.

---

## 4. Non-Goals

Phase 2b must not implement:

```text
GUI display
Management Issue generation
Cost / KPI integration
OR optimization
automatic replanning
database persistence
large loader refactoring
capacity UI editing
full reporting dashboard
```

Phase 2b is only:

```text
small feature-flagged insertion into run_full_plan
```

---

## 5. Integration Principle

The integration principle is:

```text
run_full_plan should orchestrate.
The explicit pipeline runner should execute pipeline semantics.
GUI should not define planning semantics.
```

Therefore, the insertion should be:

```python
maybe_run_explicit_bridge_capacity_pipeline(ctx)
```

not a direct copy of pipeline internals.

Do not paste the bridge / capacity logic directly into `run_full_plan`.

---

## 6. Required Precondition

The helper should only be called after the upstream demand-side plan has produced:

```text
outbound supply_point.psi4demand[w][P]
```

This is the source state required by Bridge A.

Conceptual upstream prerequisite:

```text
outbound backward planning complete
    ↓
outbound supply_point demand/P exists
```

If this state does not exist, the explicit pipeline cannot run correctly.

---

## 7. Conceptual Hook Placement

The desired insertion point is:

```text
run_full_plan
    ↓
input / seed / scenario preparation
    ↓
outbound demand-side planning / backward planning
    ↓
[INSERT HERE]
    maybe_run_explicit_bridge_capacity_pipeline(ctx)
    ↓
downstream reporting / output export / later GUI refresh
```

In compact form:

```text
after outbound demand plan
before downstream reporting that uses psi4supply
```

The exact function / line must be confirmed by inspecting the current code.

Possible locations to inspect:

```text
run_full_plan
_run_planning_sequence
pipeline runner
sample env runner
GUI Run Full Plan callback
```

The first Codex task should identify the smallest safe hook point.

---

## 8. Required ctx Inputs

Before calling:

```python
maybe_run_explicit_bridge_capacity_pipeline(ctx)
```

`ctx` must contain the required keys when the flag is True:

```python
ctx["explicit_pipeline_outbound_root"]
ctx["explicit_pipeline_inbound_root"]
ctx["explicit_pipeline_product"]
ctx["explicit_pipeline_mom_policy"]
ctx["explicit_pipeline_backward_weekly_capability"]
ctx["explicit_pipeline_forward_weekly_capacity"]
```

Phase 2b must define how these are derived from the current `run_full_plan` environment.

---

## 9. Mapping from Existing Environment to ctx

The exact mapping depends on current code, but the intended mapping is:

| ctx key | Intended source | Notes |
|---|---|---|
| `explicit_pipeline_outbound_root` | current outbound tree root / supply chain root | Must contain outbound supply_point demand/P |
| `explicit_pipeline_inbound_root` | current inbound tree root / product tree root | Must contain inbound supply_point and MOM nodes |
| `explicit_pipeline_product` | selected product / product name | Existing selected product should be reused |
| `explicit_pipeline_mom_policy` | scenario config / default MOM allocation policy | MVP may use provided default if not yet in loader |
| `explicit_pipeline_backward_weekly_capability` | weekly capability / MOM effective capacity | Can come from current capacity provider output |
| `explicit_pipeline_forward_weekly_capacity` | weekly P/S/I forward capacity | Can initially reuse test/default scenario data if explicitly enabled |

The first implementation may require a small adapter function to build these keys from env.

---

## 10. Recommended ctx Preparation Helper

To avoid cluttering `run_full_plan`, use a small preparation helper.

Suggested helper:

```python
def build_explicit_pipeline_ctx_from_env(env, ctx: dict) -> dict:
    ...
```

or:

```python
def populate_explicit_pipeline_ctx_from_env(ctx: dict, env) -> dict:
    ...
```

However, if current code already has a central ctx creation point, prefer adding the keys there.

Phase 2b MVP may use:

```text
only pre-existing ctx keys
```

and avoid adding a new env adapter if the test can supply ctx directly.

---

## 11. Minimal Insertion Pattern

The intended code shape is:

```python
from pysi.plan.explicit_bridge_capacity_pipeline import (
    maybe_run_explicit_bridge_capacity_pipeline,
)

# after outbound planning is complete and ctx has required keys
maybe_run_explicit_bridge_capacity_pipeline(ctx)
```

Because the helper is no-op when the flag is missing or False, this insertion should not affect default runs.

---

## 12. Output Attachment

The helper stores:

```python
ctx["explicit_bridge_capacity_pipeline_result"] = result
```

Phase 2b may optionally attach to env:

```python
env.explicit_bridge_capacity_pipeline_result = result
```

Recommended Phase 2b MVP:

```text
Attach to ctx only unless env conventions strongly support result attributes.
```

If existing downstream reporting expects env attributes, consider:

```python
if result is not None:
    setattr(env, "explicit_bridge_capacity_pipeline_result", result)
```

but only if safe.

---

## 13. Default Behavior Requirement

This is the most important Phase 2b invariant:

```text
If enable_explicit_bridge_capacity_pipeline is absent or False,
existing run_full_plan behavior must not change.
```

Tests should verify this as directly as possible.

If full `run_full_plan` testing is too heavy, Phase 2b can test a smaller planning sequence function or insertion helper.

---

## 14. Flag-On Behavior Requirement

When:

```python
ctx["enable_explicit_bridge_capacity_pipeline"] = True
```

and all required inputs exist, the insertion should produce:

```python
ctx["explicit_bridge_capacity_pipeline_result"]
```

Expected result health checks:

```python
result.missing_lot_ids == []
result.non_list_bucket_errors == []
result.non_string_lot_errors == []
```

---

## 15. Missing Input Behavior

When the flag is True and a required ctx key is missing, the helper already raises:

```python
ValueError
```

Phase 2b should not suppress this error.

Reason:

```text
If the user explicitly enables the pipeline, missing required inputs are configuration errors.
Silent skip would hide planning defects.
```

---

## 16. Suggested Test Strategy

### 16.1 Default unchanged test

Test that with flag missing or False:

```text
maybe helper path is no-op
no explicit result is attached
existing planning sequence still completes
```

If possible, use an existing smoke case such as:

```text
tests/test_japanese_rice_case_smoke.py
```

as a compatibility guard.

### 16.2 Flag-on insertion test

Create a minimal ctx/env with:

```text
outbound supply_point
inbound supply_point
MOM_ASIA
MOM_EURO
```

Enable:

```python
ctx["enable_explicit_bridge_capacity_pipeline"] = True
```

Verify:

```text
ctx["explicit_bridge_capacity_pipeline_result"] exists
```

### 16.3 Missing input test

Enable the flag but omit one required key.

Verify:

```text
ValueError is raised
message names missing key
```

### 16.4 Existing regression tests

Run:

```bat
python -m pytest tests/test_explicit_bridge_capacity_pipeline_feature_flag.py
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

## 17. Recommended Phase 2b Implementation Files

Because the current codebase structure must be inspected, exact files are not fixed in this design memo.

Likely candidates:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
<module containing run_full_plan>
<module containing _run_planning_sequence>
tests/test_run_full_plan_explicit_pipeline_insertion.py
```

If a lightweight testable wrapper exists, prefer modifying that over a GUI callback.

Do not modify:

```text
pysi/gui/*
```

unless Phase 2b explicitly discovers that GUI is the only location of `run_full_plan` orchestration. Even then, prefer moving logic out of GUI rather than adding planning semantics to GUI.

---

## 18. Recommended Codex Request Shape

The Phase 2b Codex Request should ask Codex to:

```text
1. Inspect current run_full_plan / _run_planning_sequence structure.
2. Identify the smallest safe insertion point.
3. Insert maybe_run_explicit_bridge_capacity_pipeline(ctx) behind the feature flag.
4. Ensure flag-off behavior remains unchanged.
5. Add focused tests.
6. Do not modify GUI unless absolutely necessary.
7. Do not implement reporting / KPI / issue generation.
```

The request should explicitly say:

```text
If exact insertion point is ambiguous,
prefer adding a small helper / adapter and tests,
and summarize where run_full_plan insertion should happen next.
```

---

## 19. Risk Analysis

### 19.1 Risk: wrong hook timing

If called too early:

```text
outbound demand/P may not exist
Bridge A has no valid source lots
```

If called too late:

```text
downstream reporting may already have used old psi4supply
```

Mitigation:

```text
Call after outbound backward planning, before downstream reporting / execution.
```

### 19.2 Risk: hidden default behavior change

Mitigation:

```text
feature flag default False
flag-off regression test
```

### 19.3 Risk: ctx key mismatch

Mitigation:

```text
centralize ctx key names
required key validation already exists
```

### 19.4 Risk: GUI coupling

Mitigation:

```text
do not modify GUI in Phase 2b
```

---

## 20. Completion Criteria for Phase 2b

Phase 2b is complete when:

```text
[OK] smallest safe run_full_plan / planning-sequence insertion point is identified
[OK] maybe_run_explicit_bridge_capacity_pipeline(ctx) is called behind feature flag
[OK] default flag-off behavior remains unchanged
[OK] flag-on path attaches explicit_bridge_capacity_pipeline_result
[OK] missing required ctx keys fail clearly
[OK] tests pass
[OK] no GUI semantic changes
[OK] no reporting / KPI / issue generation added
```

---

## 21. What Phase 2b Does Not Yet Solve

Phase 2b does not solve:

```text
how to display result in GUI
how to convert result to Management Issues
how to compute cost / KPI impact
how to edit MOM policy in UI
how to edit capacity in UI
how to persist pipeline result
```

Those belong to later phases.

---

## 22. Summary

Phase 2b should be a small, safe insertion:

```text
run_full_plan / planning sequence
    ↓
after outbound demand/P is ready
    ↓
maybe_run_explicit_bridge_capacity_pipeline(ctx)
    ↓
ctx["explicit_bridge_capacity_pipeline_result"]
```

The default path remains:

```text
feature flag off
    ↓
existing behavior unchanged
```

This step moves WOM from a standalone explicit pipeline runner to a controlled full-plan integration point without compromising the existing GUI or planning behavior.
