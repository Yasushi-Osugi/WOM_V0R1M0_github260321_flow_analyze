# Codex Request: Add run_full_plan Explicit Pipeline Feature Flag Helper

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/run_full_plan_explicit_pipeline_feature_flag.md
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

The Phase 1 runner wraps the existing E2E bridge + forward capacity smoke and exposes a pipeline-level result.

This request is **Phase 2a**.

Phase 2a should add a small feature-flag helper:

```text
maybe_run_explicit_bridge_capacity_pipeline(ctx)
```

and focused tests for:

```text
flag off
flag on
missing required input
```

Do not modify `run_full_plan` yet.

---

## 2. Main Objective

Add a feature-flag helper to:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
```

The helper should:

```text
1. Read ctx["enable_explicit_bridge_capacity_pipeline"].
2. If the flag is missing or False, return None and do nothing.
3. If the flag is True, validate required ctx inputs.
4. Call run_explicit_bridge_capacity_pipeline(...).
5. Store result into ctx["explicit_bridge_capacity_pipeline_result"].
6. Return the result.
```

This creates the safe entry gate before actually inserting the pipeline into `run_full_plan`.

---

## 3. Important Constraints

Please follow these constraints:

```text
1. Do not modify run_full_plan.
2. Do not modify GUI.
3. Do not modify loaders.
4. Do not implement costing / KPI.
5. Do not implement Management Issue generation.
6. Do not implement OR optimization.
7. Do not execute ReplanCommand.
8. Do not change existing default behavior.
9. Keep this as an additive helper + focused tests.
```

This request is only for:

```text
Phase 2a: feature flag helper
```

---

## 4. Files to Modify / Add

Modify:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
```

Add:

```text
tests/test_explicit_bridge_capacity_pipeline_feature_flag.py
```

Do not modify:

```text
run_full_plan
pysi/gui/*
loaders
costing / KPI modules
Management Issue modules
```

---

## 5. Feature Flag Name

Use exactly:

```python
ctx["enable_explicit_bridge_capacity_pipeline"]
```

Default behavior:

```python
ctx.get("enable_explicit_bridge_capacity_pipeline", False)
```

If the key is missing, the helper should treat it as:

```python
False
```

---

## 6. Helper Function

Please implement:

```python
def maybe_run_explicit_bridge_capacity_pipeline(ctx: dict):
    ...
```

Suggested behavior:

```python
def maybe_run_explicit_bridge_capacity_pipeline(ctx: dict):
    if not ctx.get("enable_explicit_bridge_capacity_pipeline", False):
        return None

    # validate required keys
    # call run_explicit_bridge_capacity_pipeline(...)
    # attach result to ctx
    # return result
```

---

## 7. Required Context Keys When Flag Is On

When the feature flag is True, the helper must require:

```python
ctx["explicit_pipeline_outbound_root"]
ctx["explicit_pipeline_inbound_root"]
ctx["explicit_pipeline_product"]
ctx["explicit_pipeline_mom_policy"]
ctx["explicit_pipeline_backward_weekly_capability"]
ctx["explicit_pipeline_forward_weekly_capacity"]
```

Map them to:

```python
run_explicit_bridge_capacity_pipeline(
    outbound_root=ctx["explicit_pipeline_outbound_root"],
    inbound_root=ctx["explicit_pipeline_inbound_root"],
    product=ctx["explicit_pipeline_product"],
    mom_policy=ctx["explicit_pipeline_mom_policy"],
    backward_weekly_capability=ctx["explicit_pipeline_backward_weekly_capability"],
    forward_weekly_capacity=ctx["explicit_pipeline_forward_weekly_capacity"],
    ...
)
```

---

## 8. Optional Context Keys

Support these optional keys with defaults:

```python
ctx.get("explicit_pipeline_bridge_a_mode", "replace")
ctx.get("explicit_pipeline_bridge_b_policy", "s_p_only")
ctx.get("explicit_pipeline_bridge_b_mode", "replace")
ctx.get("explicit_pipeline_max_early_build_weeks", 13)
ctx.get("explicit_pipeline_cap_i_mode", "soft")
ctx.get("explicit_pipeline_debug", False)
```

Map them to the same-named parameters in:

```python
run_explicit_bridge_capacity_pipeline(...)
```

---

## 9. Output Context Key

When the helper runs the pipeline successfully, store:

```python
ctx["explicit_bridge_capacity_pipeline_result"] = result
```

Return the same result.

Expected:

```python
result = maybe_run_explicit_bridge_capacity_pipeline(ctx)
assert result is ctx["explicit_bridge_capacity_pipeline_result"]
```

---

## 10. Missing Input Behavior

If the flag is disabled:

```text
missing explicit inputs should not matter
```

The helper should simply return:

```python
None
```

If the flag is enabled but a required input is missing:

```text
raise ValueError
```

The error message should include the missing key name.

Example:

```text
explicit bridge capacity pipeline enabled but missing ctx key: explicit_pipeline_product
```

Do not silently skip when the flag is True.

---

## 11. Debug Logging / Message

If `explicit_pipeline_debug` is True, it is acceptable to print or log a compact summary.

Do not print verbose Lot_ID lists by default.

Suggested compact fields:

```text
missing_lot_ids count
blocked_lot_ids count
overflow_i_lot_ids count
non_list_bucket_errors count
non_string_lot_errors count
```

Logging is optional for this MVP.

---

## 12. Safety Invariants

The helper must preserve:

```text
1. Flag off means no-op.
2. Existing run_full_plan behavior remains unchanged.
3. GUI behavior remains unchanged.
4. Loaders remain unchanged.
5. PSI buckets remain list[str].
6. No numeric quantities are inserted.
7. Lot_ID identity is preserved by the underlying pipeline.
8. No automatic replan is executed.
```

---

## 13. Required Tests

Add:

```text
tests/test_explicit_bridge_capacity_pipeline_feature_flag.py
```

Use the same minimal in-memory fixture style as:

```text
tests/test_explicit_bridge_capacity_pipeline.py
tests/test_e2e_bridge_forward_capacity_smoke.py
```

### 13.1 Flag missing means no-op

Input:

```python
ctx = {}
```

Call:

```python
result = maybe_run_explicit_bridge_capacity_pipeline(ctx)
```

Expected:

```python
result is None
"explicit_bridge_capacity_pipeline_result" not in ctx
```

### 13.2 Flag False means no-op

Input:

```python
ctx = {"enable_explicit_bridge_capacity_pipeline": False}
```

Expected:

```python
result is None
"explicit_bridge_capacity_pipeline_result" not in ctx
```

### 13.3 Flag True happy path

Build minimal outbound / inbound topology:

```text
outbound supply_point

inbound supply_point
    ├── MOM_ASIA
    └── MOM_EURO
```

Use known Lot_IDs:

```text
RT_JP_RICE_2026W10_0001
RT_JP_RICE_2026W10_0002
RT_JP_RICE_2026W10_0003
RT_DE_RICE_2026W10_0001
```

Set required ctx keys:

```python
ctx = {
    "enable_explicit_bridge_capacity_pipeline": True,
    "explicit_pipeline_outbound_root": outbound_root,
    "explicit_pipeline_inbound_root": inbound_root,
    "explicit_pipeline_product": "RICE",
    "explicit_pipeline_mom_policy": mom_policy,
    "explicit_pipeline_backward_weekly_capability": backward_weekly_capability,
    "explicit_pipeline_forward_weekly_capacity": forward_weekly_capacity,
}
```

Expected:

```python
result is not None
ctx["explicit_bridge_capacity_pipeline_result"] is result
result.missing_lot_ids == []
result.non_list_bucket_errors == []
result.non_string_lot_errors == []
```

### 13.4 Flag True missing key raises ValueError

Enable flag but omit one required key, for example:

```python
ctx = {"enable_explicit_bridge_capacity_pipeline": True}
```

Expected:

```python
ValueError is raised
error message includes missing key name
```

---

## 14. Existing Tests to Run

Please run:

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

If optional tests are not run, state so clearly.

---

## 15. Completion Criteria

This request is complete when:

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

## 16. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Whether run_full_plan was untouched
3. Whether GUI was untouched
4. Main implementation approach
5. Feature flag behavior
6. Missing key behavior
7. Test commands executed
8. Test results
9. Limitations / follow-up
```

Please do not proceed into:

```text
run_full_plan insertion
GUI integration
reporting UI
Management Issue generation
costing / KPI
OR optimization
database persistence
```

This request is only for:

```text
Phase 2a: explicit pipeline feature flag helper
```
