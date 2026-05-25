# Codex Request: Insert Explicit Bridge + Capacity Pipeline into run_full_plan behind Feature Flag

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/run_full_plan_explicit_pipeline_insertion.md
```

Please read this design memo first.

Phase 1 is complete:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
tests/test_explicit_bridge_capacity_pipeline.py
```

Phase 1 added:

```text
ExplicitBridgeCapacityPipelineResult
run_explicit_bridge_capacity_pipeline(...)
```

Phase 2a is complete:

```text
maybe_run_explicit_bridge_capacity_pipeline(ctx)
tests/test_explicit_bridge_capacity_pipeline_feature_flag.py
```

Phase 2a added a safe feature-flag helper that:

```text
flag missing / False:
    no-op

flag True:
    validate required ctx keys
    call run_explicit_bridge_capacity_pipeline(...)
    attach result to ctx["explicit_bridge_capacity_pipeline_result"]
```

This request is **Phase 2b**.

Phase 2b should insert the helper into the actual `run_full_plan` / planning sequence in the smallest safe way.

---

## 2. Main Objective

Identify the smallest safe insertion point in the existing `run_full_plan` / planning sequence and call:

```python
maybe_run_explicit_bridge_capacity_pipeline(ctx)
```

behind the existing feature flag:

```python
ctx["enable_explicit_bridge_capacity_pipeline"]
```

The default behavior must remain unchanged:

```text
feature flag off
    ↓
existing behavior unchanged
```

When the flag is on and required inputs are available:

```text
run_full_plan / planning sequence
    ↓
maybe_run_explicit_bridge_capacity_pipeline(ctx)
    ↓
ctx["explicit_bridge_capacity_pipeline_result"]
```

---

## 3. Important Constraints

Please follow these constraints:

```text
1. Keep the insertion minimal.
2. Do not modify GUI unless absolutely unavoidable.
3. Do not implement reporting UI.
4. Do not implement Management Issue generation.
5. Do not implement costing / KPI integration.
6. Do not implement OR optimization.
7. Do not execute ReplanCommand.
8. Do not silently skip when flag is True and required inputs are missing.
9. Preserve default run_full_plan behavior when the flag is off.
```

This request is only for:

```text
Phase 2b: feature-flagged run_full_plan insertion
```

---

## 4. Existing Helper to Reuse

Use the existing helper:

```python
from pysi.plan.explicit_bridge_capacity_pipeline import (
    maybe_run_explicit_bridge_capacity_pipeline,
)
```

Do not duplicate the internal pipeline logic.

Do not paste Bridge A / MOM allocation / backward planning / Bridge B / forward capacity logic into `run_full_plan`.

The correct integration shape is:

```python
maybe_run_explicit_bridge_capacity_pipeline(ctx)
```

---

## 5. Required Investigation Before Editing

Before making code changes, inspect the current structure and identify the real insertion point.

Please inspect likely locations such as:

```text
run_full_plan
_run_planning_sequence
pipeline runner
sample env runner
GUI Run Full Plan callback
```

Search suggestions:

```bat
git grep -n "def run_full_plan"
git grep -n "_run_planning_sequence"
git grep -n "Run Full Plan"
git grep -n "after_supply_planning"
git grep -n "psi4demand"
git grep -n "psi4supply"
```

The correct insertion point should be:

```text
after outbound demand-side planning has produced outbound supply_point.psi4demand[w][P]
before downstream reporting / exports that use psi4supply
```

If the exact insertion point is ambiguous, prefer adding a small testable adapter/helper and document the next insertion point clearly rather than making broad changes.

---

## 6. Feature Flag

Use exactly:

```python
ctx["enable_explicit_bridge_capacity_pipeline"]
```

Default must be:

```python
False
```

Flag-off behavior:

```text
No pipeline run.
No explicit_bridge_capacity_pipeline_result attached.
Existing run_full_plan behavior unchanged.
```

Flag-on behavior:

```text
maybe_run_explicit_bridge_capacity_pipeline(ctx) is called.
ctx["explicit_bridge_capacity_pipeline_result"] is attached if successful.
```

---

## 7. Required ctx Inputs When Flag Is On

The helper requires these ctx keys when the flag is True:

```python
ctx["explicit_pipeline_outbound_root"]
ctx["explicit_pipeline_inbound_root"]
ctx["explicit_pipeline_product"]
ctx["explicit_pipeline_mom_policy"]
ctx["explicit_pipeline_backward_weekly_capability"]
ctx["explicit_pipeline_forward_weekly_capacity"]
```

The insertion work must either:

```text
A. ensure these keys are already available in ctx before calling the helper
```

or:

```text
B. add the smallest safe adapter that populates these keys from the current env / planning context
```

Do not invent broad loader behavior.

If required inputs are not currently available from `run_full_plan`, do not add a large mapping layer in this task. Instead, provide a small, explicit adapter and tests, or document the missing integration point.

---

## 8. Optional ctx Inputs

The helper already supports:

```python
ctx.get("explicit_pipeline_bridge_a_mode", "replace")
ctx.get("explicit_pipeline_bridge_b_policy", "s_p_only")
ctx.get("explicit_pipeline_bridge_b_mode", "replace")
ctx.get("explicit_pipeline_max_early_build_weeks", 13)
ctx.get("explicit_pipeline_cap_i_mode", "soft")
ctx.get("explicit_pipeline_debug", False)
```

No additional aliases are needed.

---

## 9. Output Contract

When the helper runs successfully, the result must be available as:

```python
ctx["explicit_bridge_capacity_pipeline_result"]
```

If the surrounding planning sequence uses an env result convention, it is acceptable to attach:

```python
env.explicit_bridge_capacity_pipeline_result = result
```

but this is optional.

Recommended MVP:

```text
ctx attachment is required.
env attachment is optional.
```

---

## 10. Minimal Code Shape

Preferred insertion shape:

```python
from pysi.plan.explicit_bridge_capacity_pipeline import (
    maybe_run_explicit_bridge_capacity_pipeline,
)

# after outbound demand/P is ready, before downstream reporting
explicit_result = maybe_run_explicit_bridge_capacity_pipeline(ctx)

# optional, only if env convention supports this
if explicit_result is not None and env is not None:
    setattr(env, "explicit_bridge_capacity_pipeline_result", explicit_result)
```

If `ctx` does not currently exist in the target function, do not create a large new global context system.

Prefer a small local dict only if it can be populated safely and tested.

---

## 11. Missing Input Behavior

Do not suppress errors from the helper.

If the flag is True and a required ctx key is missing, the helper raises:

```python
ValueError
```

This is desired.

Reason:

```text
If the explicit pipeline is enabled, missing inputs are configuration defects.
Silent skip hides planning errors.
```

---

## 12. Tests to Add

Please add focused tests.

Suggested file:

```text
tests/test_run_full_plan_explicit_pipeline_insertion.py
```

If direct `run_full_plan` tests are too heavy or unstable, add tests around the smallest planning-sequence helper / insertion wrapper.

### 12.1 Flag-off default unchanged

Verify that when:

```python
ctx.get("enable_explicit_bridge_capacity_pipeline", False) is False
```

then:

```text
maybe_run_explicit_bridge_capacity_pipeline is not executed
explicit_bridge_capacity_pipeline_result is not attached
existing smoke still passes
```

If testing direct `run_full_plan` is heavy, use monkeypatch or a lightweight wrapper to confirm no call occurs.

### 12.2 Flag-on result attached

Provide a minimal valid ctx/env using the existing test fixture pattern.

Verify:

```python
ctx["explicit_bridge_capacity_pipeline_result"] exists
```

and:

```python
result.missing_lot_ids == []
result.non_list_bucket_errors == []
result.non_string_lot_errors == []
```

### 12.3 Flag-on missing key raises

Enable the flag but omit a required key.

Verify:

```text
ValueError is raised
error message includes missing key name
```

### 12.4 Existing compatibility guard

Ensure existing tests continue to pass.

---

## 13. Existing Tests to Run

Please run:

```bat
python -m pytest tests/test_run_full_plan_explicit_pipeline_insertion.py
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

If optional tests are not run, state so clearly.

---

## 14. Completion Criteria

This request is complete when:

```text
[OK] smallest safe insertion point is identified
[OK] maybe_run_explicit_bridge_capacity_pipeline(ctx) is called behind feature flag
[OK] flag-off behavior remains unchanged
[OK] flag-on path attaches ctx["explicit_bridge_capacity_pipeline_result"]
[OK] missing required ctx key still raises ValueError
[OK] focused tests pass
[OK] no GUI semantic changes
[OK] no reporting / KPI / issue generation added
[OK] no OR optimization added
```

If actual `run_full_plan` insertion cannot be done safely because required ctx/env mappings are unavailable, do not force it.

In that case:

```text
[OK] add the smallest safe adapter/helper
[OK] add tests
[OK] document the missing mapping and exact next step
```

---

## 15. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Where the insertion point was found
3. Whether run_full_plan was modified
4. Whether GUI was modified
5. Feature flag behavior
6. How ctx inputs are populated or expected
7. How result is attached
8. Test commands executed
9. Test results
10. Limitations / follow-up
```

Please do not proceed into:

```text
GUI integration
reporting UI
Management Issue generation
costing / KPI integration
OR optimization
database persistence
```

This request is only for:

```text
Phase 2b: feature-flagged run_full_plan insertion
```
