# Codex Request: Attach Explicit Pipeline Capacity Report in Planning Sequence

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/explicit_pipeline_capacity_report_attachment.md
```

Please read this design memo first.

The current staged integration status is:

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
capacity report attachment      ← Phase 3b target
```

Phase 3a added the in-memory report builder:

```text
pysi/reporting/explicit_pipeline_capacity_report.py
```

with:

```python
ExplicitPipelineCapacityReport
build_explicit_pipeline_capacity_report(...)
maybe_build_explicit_pipeline_capacity_report_from_env(env)
report_to_dict(...)
report_records_as_rows(...)
```

This request is **Phase 3b**.

Phase 3b should attach the explicit pipeline capacity report to the planning environment after the explicit pipeline result exists.

---

## 2. Main Objective

Insert the report attachment step immediately after the existing explicit pipeline insertion in the planning sequence.

Current Phase 2b flow:

```text
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
    ↓
env.explicit_bridge_capacity_pipeline_result
```

Target Phase 3b flow:

```text
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
    ↓
env.explicit_bridge_capacity_pipeline_result
    ↓
maybe_build_explicit_pipeline_capacity_report_from_env(env)
    ↓
env.explicit_bridge_capacity_pipeline_report
```

The report should be attached only when the explicit pipeline result exists.

Default feature-flag-off behavior must remain unchanged.

---

## 3. Important Constraints

Please follow these constraints:

```text
1. Keep the insertion minimal.
2. Do not add GUI widgets.
3. Do not add GUI report display.
4. Do not change button behavior.
5. Do not implement CSV / JSON file output.
6. Do not implement Management Issue generation.
7. Do not implement costing / KPI calculation.
8. Do not implement OR optimization.
9. Do not execute ReplanCommand.
10. Preserve default behavior when explicit pipeline flag is off.
```

This request is only for:

```text
Phase 3b: attach report object to env after explicit pipeline result exists
```

---

## 4. Existing Helper to Reuse

Use the existing helper:

```python
from pysi.reporting.explicit_pipeline_capacity_report import (
    maybe_build_explicit_pipeline_capacity_report_from_env,
)
```

Do not duplicate the report-building logic in `cockpit_tk.py`.

Do not manually construct `ExplicitPipelineCapacityReport` in the planning sequence.

---

## 5. Likely Files to Modify / Add

Likely modify:

```text
pysi/gui/cockpit_tk.py
```

because the current `_run_planning_sequence(...)` lives there.

Add focused test:

```text
tests/test_explicit_pipeline_capacity_report_attachment.py
```

Do not modify:

```text
pysi/gui widgets / layout / display behavior
run_full_plan public API
loaders
costing / KPI modules
Management Issue modules
```

If the current code structure suggests a smaller non-GUI planning-sequence module, prefer that. But based on Phase 2b, the likely insertion remains in `pysi/gui/cockpit_tk.py`.

---

## 6. Recommended Insertion Pattern

Current Phase 2b code likely contains:

```python
maybe_run_explicit_bridge_capacity_pipeline_from_env(
    env=self.env,
    outbound_root=out_root,
    inbound_root=in_root,
    product=prod,
    mom_policy=MOM_POLICY_IPHONE,
    backward_weekly_capability=getattr(self.env, "explicit_pipeline_backward_weekly_capability", None),
    forward_weekly_capacity=getattr(self.env, "explicit_pipeline_forward_weekly_capacity", None),
)
```

Please change it to the preferred explicit-result pattern:

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

This makes the dependency clear:

```text
only build report after explicit pipeline actually ran
```

---

## 7. Feature Flag Behavior

The existing feature flag remains:

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

Preserve:

```text
feature flag off
    ↓
existing behavior unchanged
```

---

## 8. Output Contract

When the feature flag is on and required inputs exist, the planning environment should contain:

```python
env.explicit_bridge_capacity_pipeline_result
env.explicit_bridge_capacity_pipeline_report
```

The report should be an instance of:

```python
ExplicitPipelineCapacityReport
```

At minimum, the report should expose:

```text
summary
capacity_usage_records
capacity_violation_records
lot_exception_records
replan_candidate_records
health_check_records
```

---

## 9. Error Handling

If the feature flag is on and required explicit pipeline inputs are missing, existing Phase 2b behavior should remain:

```python
ValueError
```

Do not suppress this error.

If the explicit pipeline does not run, the report helper must not raise.

If the explicit pipeline result exists, `maybe_build_explicit_pipeline_capacity_report_from_env(env)` should attach a report using the existing Phase 3a tolerant report builder.

---

## 10. GUI Boundary

`pysi/gui/cockpit_tk.py` may be touched only because it owns `_run_planning_sequence(...)`.

Allowed:

```text
import maybe_build_explicit_pipeline_capacity_report_from_env
call it near the existing explicit pipeline insertion
```

Not allowed:

```text
new buttons
new widgets
new display panel
new popup
new text rendering
new GUI layout
new report table
```

Phase 3b should not make the report visible in GUI yet.

---

## 11. Tests to Add

Please add:

```text
tests/test_explicit_pipeline_capacity_report_attachment.py
```

Use the existing fixture style from:

```text
tests/test_run_full_plan_explicit_pipeline_insertion.py
tests/test_explicit_bridge_capacity_pipeline_feature_flag.py
tests/test_explicit_pipeline_capacity_reporting.py
```

### 11.1 Flag-off no report attachment

Create env with:

```python
enable_explicit_bridge_capacity_pipeline = False
```

Call the adapter / insertion-equivalent flow.

Expected:

```text
no env.explicit_bridge_capacity_pipeline_result
no env.explicit_bridge_capacity_pipeline_report
```

### 11.2 Flag-on report attachment

Create env with:

```python
enable_explicit_bridge_capacity_pipeline = True
```

Provide valid required inputs.

Expected:

```text
env.explicit_bridge_capacity_pipeline_result exists
env.explicit_bridge_capacity_pipeline_report exists
env.explicit_bridge_capacity_pipeline_report.summary exists
```

Also verify the report type if convenient:

```python
isinstance(env.explicit_bridge_capacity_pipeline_report, ExplicitPipelineCapacityReport)
```

### 11.3 Missing required input still raises

Enable the flag but omit a required pipeline input.

Expected:

```text
ValueError is raised
no env.explicit_bridge_capacity_pipeline_report is attached
```

### 11.4 Report helper no-op remains valid

If useful, verify:

```python
maybe_build_explicit_pipeline_capacity_report_from_env(env_without_result) is None
```

This is already covered in Phase 3a, so avoid redundant tests unless useful for attachment scenario.

---

## 12. Suggested Testing Approach

The goal is not to instantiate the full GUI.

Prefer testing the smallest helper / adapter behavior.

If the insertion in `cockpit_tk.py` is difficult to test directly without GUI, add a small testable helper near the planning integration, or test the two helper calls together:

```python
explicit_result = maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
if explicit_result is not None:
    maybe_build_explicit_pipeline_capacity_report_from_env(env)
```

This can be tested without GUI.

---

## 13. Existing Tests to Run

Please run:

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

If the optional test is not run, state so clearly.

---

## 14. Completion Criteria

This request is complete when:

```text
[OK] capacity report attachment is added after explicit pipeline result is created
[OK] env.explicit_bridge_capacity_pipeline_report is attached when flag is on
[OK] no report is attached when flag is off
[OK] missing required input behavior still raises ValueError
[OK] tests pass
[OK] no GUI display changes
[OK] no CSV / JSON file export
[OK] no Management Issue generation
[OK] no cost / KPI calculation
[OK] no replan execution
```

---

## 15. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Exact insertion point
3. Whether GUI display was changed
4. Feature flag behavior
5. Report attachment behavior
6. Missing input behavior
7. Test commands executed
8. Test results
9. Limitations / follow-up
```

Please do not proceed into:

```text
GUI display
report panel
CSV / JSON file output
Management Issue generation
costing / KPI integration
OR optimization
database persistence
```

This request is only for:

```text
Phase 3b: explicit pipeline capacity report attachment
```
