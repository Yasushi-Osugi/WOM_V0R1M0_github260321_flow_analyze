# Explicit Pipeline Capacity Report Attachment Phase 3b Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-23  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Phase 3b: Explicit Pipeline Capacity Report Attachment in Planning Sequence**.

The purpose of this milestone was to attach an explicit pipeline capacity report to the planning environment after the explicit bridge + capacity pipeline result is created.

The completed attachment flow is:

```text
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
    ↓
env.explicit_bridge_capacity_pipeline_result
    ↓
maybe_build_explicit_pipeline_capacity_report_from_env(env)
    ↓
env.explicit_bridge_capacity_pipeline_report
```

This phase does not implement GUI display, CSV / JSON export, Management Issue generation, Cost / KPI calculation, OR optimization, or ReplanCommand execution.

---

## 2. Background

Before Phase 3b, the staged integration had reached this state:

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

Phase 3a added the report builder:

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

Phase 3b connects this reporting layer to the planning sequence.

---

## 3. Implemented Files

This milestone updated or added:

```text
pysi/gui/cockpit_tk.py
tests/test_explicit_pipeline_capacity_report_attachment.py
```

The implementation was committed as:

```text
988f22d Attach explicit pipeline capacity report in planning sequence
```

---

## 4. Insertion Point

The Phase 3b insertion was made in:

```text
pysi/gui/cockpit_tk.py
```

inside the current planning-sequence function:

```python
_run_planning_sequence(...)
```

The report attachment was inserted immediately after the explicit pipeline execution step.

Conceptually:

```text
explicit bridge + capacity pipeline execution
    ↓
if explicit_result is not None
    ↓
build and attach explicit capacity report to env
    ↓
continue existing planning sequence
```

This keeps report generation close to the explicit pipeline result creation.

---

## 5. Implemented Code Shape

The Phase 2b call was changed from a direct call:

```python
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
```

to an explicit-result pattern:

```python
explicit_result = maybe_run_explicit_bridge_capacity_pipeline_from_env(...)

if explicit_result is not None:
    maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
```

This makes the dependency clear:

```text
Only build the capacity report when the explicit pipeline actually ran.
```

---

## 6. Report Attachment Behavior

When the feature flag is enabled and the explicit pipeline succeeds, the environment now contains:

```python
env.explicit_bridge_capacity_pipeline_result
env.explicit_bridge_capacity_pipeline_report
```

The report is expected to be an instance of:

```python
ExplicitPipelineCapacityReport
```

The report includes:

```text
capacity_usage_records
capacity_violation_records
lot_exception_records
replan_candidate_records
health_check_records
summary
```

---

## 7. Feature Flag Behavior

The existing feature flag remains:

```python
env.enable_explicit_bridge_capacity_pipeline
```

Default behavior remains:

```text
False
```

Expected behavior after Phase 3b:

```text
flag missing / False:
    explicit pipeline does not run
    no explicit pipeline result is attached
    no explicit capacity report is attached

flag True:
    explicit pipeline runs
    explicit pipeline result is attached
    explicit capacity report is attached
```

This preserves the core safety rule:

```text
feature flag off
    ↓
existing behavior unchanged
```

---

## 8. Missing Input Behavior

The existing Phase 2b missing-input behavior remains unchanged.

When the feature flag is enabled but required explicit pipeline inputs are missing:

```python
ValueError
```

is still raised.

The report is not attached in this case.

This is intentional because missing required pipeline inputs are configuration defects when the explicit pipeline is enabled.

---

## 9. GUI Boundary

This milestone touched:

```text
pysi/gui/cockpit_tk.py
```

only because `_run_planning_sequence(...)` currently lives there.

This milestone did not add or change:

```text
GUI widgets
buttons
screen layout
report panels
popups
user-facing report rendering
CSV / JSON export actions
```

The change is limited to planning-sequence integration logic.

---

## 10. Non-Goals Preserved

This milestone did not implement:

```text
GUI display
report panel
CSV / JSON file output
Management Issue generation
Cost / KPI calculation
OR optimization
database persistence
ReplanCommand execution
capacity editing UI
MOM policy editing UI
```

Phase 3b remains a minimal report attachment step.

---

## 11. Tests Added

The new focused test file is:

```text
tests/test_explicit_pipeline_capacity_report_attachment.py
```

It validates:

```text
1. flag-off does not attach result or report
2. flag-on attaches result and report
3. attached report is ExplicitPipelineCapacityReport
4. attached report has summary
5. flag-on missing required input raises ValueError
6. missing-input case does not attach report
```

---

## 12. Validation

The focused Phase 3b test passed:

```bat
python -m pytest tests/test_explicit_pipeline_capacity_report_attachment.py
```

Observed result:

```text
3 passed
```

The broader regression set also passed:

```bat
python -m pytest tests/test_explicit_pipeline_capacity_reporting.py
python -m pytest tests/test_run_full_plan_explicit_pipeline_insertion.py
python -m pytest tests/test_explicit_bridge_capacity_pipeline_feature_flag.py
python -m pytest tests/test_explicit_bridge_capacity_pipeline.py
python -m pytest tests/test_e2e_bridge_forward_capacity_smoke.py
python -m pytest tests/test_weekly_forward_push_with_capacity.py
python -m pytest tests/test_demand_to_supply_execution_bridge.py
python -m pytest tests/test_capacity_aware_inbound_backward_planning.py
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results:

```text
tests/test_explicit_pipeline_capacity_reporting.py: 5 passed
tests/test_run_full_plan_explicit_pipeline_insertion.py: 3 passed
tests/test_explicit_bridge_capacity_pipeline_feature_flag.py: 4 passed
tests/test_explicit_bridge_capacity_pipeline.py: 3 passed
tests/test_e2e_bridge_forward_capacity_smoke.py: 1 passed
tests/test_weekly_forward_push_with_capacity.py: 6 passed
tests/test_demand_to_supply_execution_bridge.py: 10 passed
tests/test_capacity_aware_inbound_backward_planning.py: 3 passed
tests/test_japanese_rice_case_smoke.py: 1 passed
tests/test_covid_vaccine_with_capacity_push.py: 1 passed
```

---

## 13. Completion Criteria

This milestone satisfies the intended completion criteria.

```text
[OK] capacity report attachment is added after explicit pipeline result is created
[OK] env.explicit_bridge_capacity_pipeline_report is attached when flag is on
[OK] no report is attached when flag is off
[OK] missing required input behavior still raises ValueError
[OK] focused tests pass
[OK] broader regression tests pass
[OK] no GUI display changes
[OK] no CSV / JSON file export
[OK] no Management Issue generation
[OK] no cost / KPI calculation
[OK] no replan execution
```

---

## 14. Meaning of This Milestone

Before Phase 3b:

```text
The explicit bridge + capacity pipeline could produce a result.
The capacity reporting builder could transform a result into a report.
But the planning sequence did not yet connect those two automatically.
```

After Phase 3b:

```text
When the explicit pipeline runs inside the planning sequence,
the capacity report is also attached to env automatically.
```

This means the planning environment now carries both:

```text
execution result
explanation report
```

This is the foundation for later management-facing issue generation and GUI display.

---

## 15. Current Pipeline Position

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
capacity reporting MVP          ✅ Phase 3a completed
    ↓
capacity report attachment      ✅ Phase 3b completed
    ↓
report export / issue candidates
    ↓
cost/KPI
    ↓
GUI display
```

---

## 16. Future Milestones

### 16.1 Optional report export

The next reporting-oriented step may be to export the in-memory report to files such as:

```text
outputs/explicit_pipeline/capacity_usage.csv
outputs/explicit_pipeline/capacity_violations.csv
outputs/explicit_pipeline/lot_exceptions.csv
outputs/explicit_pipeline/replan_candidates.csv
outputs/explicit_pipeline/health_checks.csv
outputs/explicit_pipeline/summary.json
```

### 16.2 Management Issue candidate generation

Future work should transform:

```text
capacity_violation_records
lot_exception_records
health_check_records
```

into:

```text
PlanningIssue
ManagementIssue
ReplanCommand candidate
```

without executing replanning automatically.

### 16.3 Cost / KPI integration

Future work should connect report records to:

```text
service level
capacity utilization
inventory overflow
cost impact
profit impact
opportunity loss
```

### 16.4 GUI display

GUI should display the report only after the report structure and optional export path are stable.

---

## 17. Summary

Phase 3b is complete.

The key achievement is:

```text
The planning sequence now attaches an ExplicitPipelineCapacityReport to env
when the explicit bridge + capacity pipeline runs successfully.
```

The completed chain is:

```text
explicit pipeline execution
    ↓
env.explicit_bridge_capacity_pipeline_result
    ↓
env.explicit_bridge_capacity_pipeline_report
```

This moves WOM one step further from planning execution toward management explanation.
