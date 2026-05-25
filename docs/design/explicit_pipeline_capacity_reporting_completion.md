# Explicit Pipeline Capacity Reporting Phase 3a Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-23  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Phase 3a: Explicit Pipeline Capacity Reporting MVP**.

The purpose of this milestone was to convert the explicit bridge + capacity pipeline result into a stable, in-memory, reportable structure.

The core transformation completed in this milestone is:

```text
ExplicitBridgeCapacityPipelineResult
    ↓
ExplicitPipelineCapacityReport
    ↓
capacity_usage_records
capacity_violation_records
lot_exception_records
replan_candidate_records
health_check_records
summary
```

This phase does not implement GUI display, Management Issue generation, cost / KPI calculation, OR optimization, file export, or replan execution.

---

## 2. Background

Before Phase 3a, the staged integration had reached this state:

```text
isolated utilities
    ↓
explicit pipeline runner        ✅ Phase 1 completed
    ↓
feature flag helper             ✅ Phase 2a completed
    ↓
run_full_plan insertion         ✅ Phase 2b completed
    ↓
capacity reporting              ← Phase 3a target
```

The explicit bridge + capacity pipeline had already been made reachable from the planning sequence behind a feature flag.

Phase 3a adds the first reporting layer on top of that result.

---

## 3. Implemented Files

This milestone added or updated:

```text
pysi/reporting/__init__.py
pysi/reporting/explicit_pipeline_capacity_report.py
tests/test_explicit_pipeline_capacity_reporting.py
```

The implementation was committed as:

```text
b7b6a69 Add explicit pipeline capacity reporting MVP
```

---

## 4. Implemented Reporting Module

The new reporting module is:

```text
pysi/reporting/explicit_pipeline_capacity_report.py
```

It provides a pure in-memory transformation layer.

It does not write files.

It does not modify GUI.

It does not call planning engines.

It does not execute replan commands.

---

## 5. Implemented Report Dataclass

The implemented dataclass is:

```python
ExplicitPipelineCapacityReport
```

It contains:

```text
product_name

capacity_usage_records
capacity_violation_records
lot_exception_records
replan_candidate_records
health_check_records

summary
message
```

The report object is designed to be:

```text
simple
deterministic
serializable
testable
GUI-independent
KPI-independent
Management-Issue-independent
```

---

## 6. Implemented Main Builder

The implemented main builder function is:

```python
build_explicit_pipeline_capacity_report(...)
```

Its role is to convert an `ExplicitBridgeCapacityPipelineResult`-like object into an `ExplicitPipelineCapacityReport`.

The builder is attribute-based and tolerant of missing fields.

This means it can accept:

```text
ExplicitBridgeCapacityPipelineResult
```

or a simple object with compatible attributes.

---

## 7. Implemented Record Groups

### 7.1 Capacity usage records

The builder normalizes upstream `capacity_usage` entries into:

```text
capacity_usage_records
```

Normalized records include fields such as:

```text
record_type
product
node
week
capacity_type
capacity
used
remaining
source
```

When upstream fields are missing, safe defaults are used.

### 7.2 Capacity violation records

The builder normalizes upstream `capacity_violations` entries into:

```text
capacity_violation_records
```

Normalized records include fields such as:

```text
record_type
product
node
week
capacity_type
severity
lot_ids
source
```

If severity is missing, the default is:

```text
warning
```

### 7.3 Lot exception records

The builder creates one lot exception record per lot for:

```text
missing_lot_ids
blocked_lot_ids
overflow_i_lot_ids
backlog_lot_ids
shifted_lot_ids
```

Supported exception types are:

```text
missing
blocked
overflow_i
backlog
shifted
```

These records are the future bridge toward Planning Issue / Management Issue generation.

### 7.4 Replan candidate records

The builder normalizes upstream `replan_commands` into:

```text
replan_candidate_records
```

Important boundary:

```text
Phase 3a reports replan candidates.
Phase 3a does not execute replan commands.
```

### 7.5 Health check records

The builder creates health check records from:

```text
missing_lot_ids
non_list_bucket_errors
non_string_lot_errors
```

Supported check types are:

```text
missing_lot
non_list_bucket_error
non_string_lot_error
```

These are marked as structural errors.

---

## 8. Implemented Summary

The report includes summary counts such as:

```text
capacity_usage_record_count
capacity_violation_record_count
lot_exception_record_count
replan_candidate_record_count
health_check_record_count

missing_lot_count
blocked_lot_count
overflow_i_lot_count
backlog_lot_count
shifted_lot_count

has_error
has_warning
```

The implemented logic follows the design rule:

```text
has_error:
    True when missing lots or structural health-check errors exist

has_warning:
    True when capacity violations or lot exceptions exist
```

Blocked lots and overflow inventory lots are business / capacity events, not structural errors.

---

## 9. Implemented Serialization Helpers

The following helpers were implemented:

```python
report_to_dict(report)
report_records_as_rows(report)
```

### 9.1 report_to_dict(...)

Returns a serializable dictionary representation of the report.

### 9.2 report_records_as_rows(...)

Returns a single list of dictionary rows by concatenating:

```text
capacity_usage_records
capacity_violation_records
lot_exception_records
replan_candidate_records
health_check_records
```

The row order is stable.

---

## 10. Implemented Env Helper

The following helper was implemented:

```python
maybe_build_explicit_pipeline_capacity_report_from_env(env)
```

Behavior:

```text
1. Read env.explicit_bridge_capacity_pipeline_result.
2. If missing, return None.
3. Build ExplicitPipelineCapacityReport.
4. Attach it to env.explicit_bridge_capacity_pipeline_report.
5. Return the report.
```

This prepares future reporting / GUI integration without displaying anything yet.

---

## 11. Reporting Package Export

The reporting package export was updated in:

```text
pysi/reporting/__init__.py
```

The following APIs were exported:

```text
ExplicitPipelineCapacityReport
build_explicit_pipeline_capacity_report
maybe_build_explicit_pipeline_capacity_report_from_env
report_records_as_rows
report_to_dict
```

---

## 12. Tests Added

The new focused test file is:

```text
tests/test_explicit_pipeline_capacity_reporting.py
```

It validates:

```text
1. synthetic result normalization
2. empty result safety
3. env helper no-op behavior
4. env helper report attachment
5. serialization helper behavior
```

---

## 13. Validation

The focused Phase 3a test passed:

```bat
python -m pytest tests/test_explicit_pipeline_capacity_reporting.py
```

Observed result:

```text
5 passed
```

The broader regression set also passed:

```bat
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

## 14. Completion Criteria

This milestone satisfies the intended completion criteria.

```text
[OK] pysi/reporting/explicit_pipeline_capacity_report.py exists
[OK] ExplicitPipelineCapacityReport exists
[OK] build_explicit_pipeline_capacity_report(...) exists
[OK] capacity_usage_records are normalized
[OK] capacity_violation_records are normalized
[OK] lot_exception_records are generated
[OK] replan_candidate_records are generated
[OK] health_check_records are generated
[OK] summary counts are generated
[OK] report_to_dict(...) exists
[OK] report_records_as_rows(...) exists
[OK] maybe_build_explicit_pipeline_capacity_report_from_env(...) exists
[OK] focused tests pass
[OK] no GUI changes
[OK] no run_full_plan changes
[OK] no Management Issue generation
[OK] no cost / KPI calculation
[OK] no replan execution
```

---

## 15. Meaning of This Milestone

Before Phase 3a:

```text
The explicit bridge + capacity pipeline could run,
but its result was not yet normalized into a reporting structure.
```

After Phase 3a:

```text
The explicit bridge + capacity pipeline result can be transformed into a stable report object.
```

This means WOM can now start explaining the operational result of the explicit pipeline.

The report answers questions such as:

```text
Which lots were blocked?
Which lots overflowed inventory?
Which lots were shifted?
Were any lots missing?
Were there structural PSI bucket errors?
What capacity usage and violation records were reported?
```

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
capacity reporting MVP          ✅ Phase 3a completed
    ↓
report attachment / export      ← future
    ↓
issue candidates
    ↓
cost/KPI
    ↓
GUI display
```

---

## 17. Known Limitations

Phase 3a is intentionally limited.

It does not implement:

```text
GUI display
Management Issue generation
cost / KPI calculation
OR optimization
CSV / JSON file output
database persistence
replan execution
```

The normalization currently accepts dict-like upstream entries and uses safe defaults for missing fields.

If upstream later introduces richer typed records, a typed adapter layer may be added.

---

## 18. Future Milestones

### 18.1 Phase 3b: Report attachment in planning sequence

Potential next step:

```text
After explicit pipeline result is attached to env,
build explicit pipeline capacity report
and attach env.explicit_bridge_capacity_pipeline_report.
```

### 18.2 Phase 3c: Optional file export

Future output candidates:

```text
outputs/explicit_pipeline/capacity_usage.csv
outputs/explicit_pipeline/capacity_violations.csv
outputs/explicit_pipeline/lot_exceptions.csv
outputs/explicit_pipeline/replan_candidates.csv
outputs/explicit_pipeline/health_checks.csv
outputs/explicit_pipeline/summary.json
```

### 18.3 Phase 4: Management Issue candidates

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

### 18.4 Phase 5: Cost / KPI integration

Future work should connect report records to:

```text
service level
capacity utilization
inventory overflow
cost impact
profit impact
opportunity loss
```

### 18.5 Phase 6: GUI display

GUI should display the report only after report attachment / export is stable.

---

## 19. Summary

Phase 3a is complete.

The key achievement is:

```text
The explicit bridge + capacity pipeline result is now explainable through a stable in-memory reporting object.
```

The completed transformation is:

```text
ExplicitBridgeCapacityPipelineResult
    ↓
ExplicitPipelineCapacityReport
    ↓
capacity_usage_records
capacity_violation_records
lot_exception_records
replan_candidate_records
health_check_records
summary
```

This is the first step from planning execution toward management explanation.
