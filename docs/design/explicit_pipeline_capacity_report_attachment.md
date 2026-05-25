# Explicit Pipeline Capacity Report Attachment Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-23  
**Status:** Design memo  
**Target path:** `docs/design/explicit_pipeline_capacity_report_attachment.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/explicit_pipeline_capacity_reporting.md`
- `docs/design/explicit_pipeline_capacity_reporting_completion.md`
- `docs/design/run_full_plan_explicit_pipeline_insertion.md`
- `docs/design/run_full_plan_explicit_pipeline_insertion_completion.md`
- `docs/design/explicit_pipeline_feature_flag_helper_completion.md`
- `docs/design/explicit_bridge_capacity_pipeline_runner_completion.md`

---

## 1. Purpose

This memo defines **Phase 3b: Explicit Pipeline Capacity Report Attachment in Planning Sequence**.

Phase 3a completed the in-memory reporting layer:

```text
ExplicitBridgeCapacityPipelineResult
    ↓
ExplicitPipelineCapacityReport
```

Implemented by:

```text
pysi/reporting/explicit_pipeline_capacity_report.py
```

with:

```python
build_explicit_pipeline_capacity_report(...)
maybe_build_explicit_pipeline_capacity_report_from_env(env)
```

Phase 3b should attach the report to the planning environment after the explicit bridge + capacity pipeline has run.

The target attachment is:

```python
env.explicit_bridge_capacity_pipeline_report
```

This phase still does not implement GUI display.

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
run_full_plan insertion         ✅ Phase 2b completed
    ↓
capacity reporting MVP          ✅ Phase 3a completed
    ↓
report attachment               ← Phase 3b target
    ↓
issue candidates
    ↓
cost/KPI
    ↓
GUI display
```

The current Phase 2b flow is:

```text
_run_planning_sequence(...)
    ↓
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
    ↓
env.explicit_bridge_capacity_pipeline_result
```

Phase 3b should extend this to:

```text
env.explicit_bridge_capacity_pipeline_result
    ↓
maybe_build_explicit_pipeline_capacity_report_from_env(env)
    ↓
env.explicit_bridge_capacity_pipeline_report
```

---

## 3. Design Goal

The Phase 3b goal is deliberately small:

```text
If an explicit bridge + capacity pipeline result exists on env,
build an ExplicitPipelineCapacityReport and attach it to env.
```

Conceptual flow:

```text
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
    ↓
env.explicit_bridge_capacity_pipeline_result
    ↓
maybe_build_explicit_pipeline_capacity_report_from_env(env)
    ↓
env.explicit_bridge_capacity_pipeline_report
```

The report should be generated only when the explicit pipeline result exists.

If the explicit pipeline did not run, the report attachment should be a no-op.

---

## 4. Non-Goals

Phase 3b must not implement:

```text
GUI display
report panel
CSV / JSON file output
Management Issue generation
Cost / KPI calculation
OR optimization
automatic replanning
capacity editing UI
MOM policy editing UI
database persistence
```

Phase 3b is only:

```text
report attachment in planning sequence
```

---

## 5. Existing Helper to Reuse

Use the existing helper from:

```text
pysi/reporting/explicit_pipeline_capacity_report.py
```

Function:

```python
maybe_build_explicit_pipeline_capacity_report_from_env(env)
```

Behavior already defined:

```text
1. Read env.explicit_bridge_capacity_pipeline_result.
2. If missing, return None.
3. Build ExplicitPipelineCapacityReport.
4. Attach env.explicit_bridge_capacity_pipeline_report.
5. Return the report.
```

Do not duplicate report-building logic in `cockpit_tk.py` or planning sequence.

---

## 6. Recommended Insertion Point

The report attachment should run immediately after the explicit pipeline insertion.

Current Phase 2b insertion:

```python
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
```

Recommended Phase 3b insertion:

```python
explicit_result = maybe_run_explicit_bridge_capacity_pipeline_from_env(...)

if explicit_result is not None:
    maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
```

or simply:

```python
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
```

Because the report helper is no-op when no pipeline result exists, the second form is acceptable.

Preferred pattern:

```python
explicit_result = maybe_run_explicit_bridge_capacity_pipeline_from_env(...)

if explicit_result is not None:
    maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
```

Reason:

```text
It makes the conditional relationship explicit and avoids unnecessary helper calls.
```

---

## 7. Feature Flag Behavior

The feature flag remains:

```python
env.enable_explicit_bridge_capacity_pipeline
```

Default:

```text
False
```

Expected behavior:

```text
flag missing / False:
    explicit pipeline does not run
    env.explicit_bridge_capacity_pipeline_result is not attached
    env.explicit_bridge_capacity_pipeline_report is not attached

flag True:
    explicit pipeline runs
    env.explicit_bridge_capacity_pipeline_result is attached
    env.explicit_bridge_capacity_pipeline_report is attached
```

This preserves:

```text
feature flag off
    ↓
existing behavior unchanged
```

---

## 8. Output Contract

After Phase 3b, when the explicit pipeline is enabled and succeeds, the environment should contain:

```python
env.explicit_bridge_capacity_pipeline_result
env.explicit_bridge_capacity_pipeline_report
```

The report should be an instance of:

```python
ExplicitPipelineCapacityReport
```

The report should include:

```text
capacity_usage_records
capacity_violation_records
lot_exception_records
replan_candidate_records
health_check_records
summary
```

---

## 9. Error Handling

If the explicit pipeline is enabled but required pipeline inputs are missing, Phase 2b behavior remains:

```python
ValueError
```

Phase 3b should not suppress this.

If the explicit pipeline does not run, the report helper should not raise.

If the pipeline result exists but is malformed, the report builder should rely on Phase 3a tolerant behavior and safe defaults.

---

## 10. GUI Boundary

Phase 3b may modify `pysi/gui/cockpit_tk.py` only if that is where `_run_planning_sequence(...)` currently lives.

Allowed change:

```text
Add import and call to maybe_build_explicit_pipeline_capacity_report_from_env(env)
near the existing explicit pipeline insertion.
```

Not allowed:

```text
Add GUI widgets
Add report display
Add buttons
Add layout changes
Add popups
Add user-facing report rendering
```

The GUI file currently owns the planning sequence, but Phase 3b must keep GUI display semantics unchanged.

---

## 11. Recommended Code Shape

In `pysi/gui/cockpit_tk.py` or the current planning-sequence module:

```python
from pysi.reporting.explicit_pipeline_capacity_report import (
    maybe_build_explicit_pipeline_capacity_report_from_env,
)
```

Near the Phase 2b explicit pipeline call:

```python
explicit_result = maybe_run_explicit_bridge_capacity_pipeline_from_env(
    env=self.env,
    outbound_root=out_root,
    inbound_root=in_root,
    product=prod,
    mom_policy=MOM_POLICY_IPHONE,
    backward_weekly_capability=getattr(self.env, "explicit_pipeline_backward_weekly_capability", None),
    forward_weekly_capacity=getattr(self.env, "explicit_pipeline_forward_weekly_capacity", None),
)

if explicit_result is not None:
    maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
```

Alternative no-op-safe pattern:

```python
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
```

The explicit-result conditional pattern is preferred.

---

## 12. Test Strategy

### 12.1 Report helper no-op test

Already covered in Phase 3a:

```text
maybe_build_explicit_pipeline_capacity_report_from_env(env) returns None when no pipeline result exists.
```

Phase 3b should add planning-sequence-level tests.

### 12.2 Flag-off no report attachment

When:

```python
env.enable_explicit_bridge_capacity_pipeline = False
```

Expected:

```text
env.explicit_bridge_capacity_pipeline_result does not exist
env.explicit_bridge_capacity_pipeline_report does not exist
```

### 12.3 Flag-on report attachment

When:

```python
env.enable_explicit_bridge_capacity_pipeline = True
```

and required inputs exist:

Expected:

```text
env.explicit_bridge_capacity_pipeline_result exists
env.explicit_bridge_capacity_pipeline_report exists
```

Also verify:

```python
env.explicit_bridge_capacity_pipeline_report.summary is not None
```

### 12.4 Missing input behavior

When flag is True and required inputs are missing:

```text
ValueError is still raised
```

No report should be attached.

### 12.5 Regression tests

Continue running the Phase 2b and Phase 3a tests.

---

## 13. Suggested Test File

Suggested file:

```text
tests/test_explicit_pipeline_capacity_report_attachment.py
```

or extend:

```text
tests/test_run_full_plan_explicit_pipeline_insertion.py
```

Recommended:

```text
tests/test_explicit_pipeline_capacity_report_attachment.py
```

Reason:

```text
It keeps Phase 3b report attachment tests separate from Phase 2b insertion tests.
```

---

## 14. Existing Tests to Run

Run:

```bat
python -m pytest tests/test_explicit_pipeline_capacity_report_attachment.py
python -m pytest tests/test_explicit_pipeline_capacity_reporting.py
python -m pytest tests/test_run_full_plan_explicit_pipeline_insertion.py
python -m pytest tests/test_explicit_bridge_capacity_pipeline_feature_flag.py
python -m pytest tests/test_explicit_bridge_capacity_pipeline.py
python -m pytest tests/test_e2e_bridge_forward_capacity_smoke.py
python -m pytest tests/test_weekly_forward_push_with_capacity.py
python -m pytest tests/test_demand_to_supply_execution_bridge.py
python -m pytest tests/test_capacity_aware_inbound_backward_planning.py
python -m pytest tests/test_japanese_rice_case_smoke.py
```

Optional:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

---

## 15. Recommended Implementation Scope

Phase 3b implementation should likely modify:

```text
pysi/gui/cockpit_tk.py
tests/test_explicit_pipeline_capacity_report_attachment.py
```

Possibly no change is needed in:

```text
pysi/reporting/explicit_pipeline_capacity_report.py
```

because the env helper already exists.

If a small wrapper is useful, add it only if it improves testability.

---

## 16. Completion Criteria

Phase 3b is complete when:

```text
[OK] explicit pipeline report is built after explicit pipeline result exists
[OK] env.explicit_bridge_capacity_pipeline_report is attached when flag is on
[OK] flag-off behavior remains unchanged
[OK] no report is attached when pipeline did not run
[OK] missing input behavior still raises ValueError
[OK] tests pass
[OK] no GUI display changes
[OK] no Management Issue generation
[OK] no cost / KPI calculation
[OK] no CSV / JSON file export
```

---

## 17. Why This Step Matters

Phase 2b made the explicit pipeline reachable from planning sequence.

Phase 3a made the result explainable as a report object.

Phase 3b connects those two:

```text
planning sequence
    ↓
explicit pipeline result
    ↓
capacity report attached to env
```

After Phase 3b, the result will be ready for later:

```text
file export
Management Issue generation
Cost / KPI integration
GUI display
```

---

## 18. Summary

Phase 3b should attach the explicit pipeline capacity report to the planning environment.

The target flow is:

```text
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
    ↓
env.explicit_bridge_capacity_pipeline_result
    ↓
maybe_build_explicit_pipeline_capacity_report_from_env(env)
    ↓
env.explicit_bridge_capacity_pipeline_report
```

The guiding principle remains:

```text
feature flag off:
    existing behavior unchanged

feature flag on:
    explicit pipeline runs
    explicit capacity report is attached
```

This is a small but important bridge from execution result to management explanation.
