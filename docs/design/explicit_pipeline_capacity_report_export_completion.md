# Explicit Pipeline Capacity Report Export Phase 3c Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-23  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Phase 3c: Explicit Pipeline Capacity Report Export MVP**.

The purpose of this milestone was to add a standalone exporter that converts the in-memory explicit pipeline capacity report into externally inspectable CSV / JSON files.

The completed transformation is:

```text
ExplicitBridgeCapacityPipelineResult
    ↓
ExplicitPipelineCapacityReport
    ↓
export_explicit_pipeline_capacity_report(...)
    ↓
outputs/explicit_pipeline/*.csv
outputs/explicit_pipeline/summary.json
```

This phase creates the first file-based audit trail for the explicit bridge + capacity planning flow.

---

## 2. Background

Before Phase 3c, the staged integration had reached this state:

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
capacity report export          ← Phase 3c target
```

Phase 3a added the in-memory report object:

```text
ExplicitPipelineCapacityReport
```

Phase 3b attached that report to env:

```python
env.explicit_bridge_capacity_pipeline_report
```

Phase 3c adds standalone file export.

---

## 3. Implemented Files

This milestone added or updated:

```text
pysi/reporting/__init__.py
pysi/reporting/explicit_pipeline_capacity_report_exporter.py
tests/test_explicit_pipeline_capacity_report_export.py
```

The implementation was committed as:

```text
0431f2e Add explicit pipeline capacity report exporter MVP
```

---

## 4. Implemented Exporter Module

The new exporter module is:

```text
pysi/reporting/explicit_pipeline_capacity_report_exporter.py
```

It provides a pure reporting/export layer.

It does not:

```text
modify GUI
modify run_full_plan
modify _run_planning_sequence
execute planning logic
generate Management Issues
calculate cost / KPI
execute ReplanCommand
persist to database
```

---

## 5. Implemented Export Result Dataclass

The implemented dataclass is:

```python
ExplicitPipelineCapacityReportExportResult
```

It contains:

```text
output_dir
files
record_counts
summary_path
message
```

This makes the export result deterministic and inspectable from tests or later pipeline stages.

---

## 6. Implemented Main Export Function

The implemented main export function is:

```python
export_explicit_pipeline_capacity_report(...)
```

Supported parameters include:

```text
report
output_dir
write_empty_files
write_all_records
write_report_json
```

The exporter:

```text
1. ensures output_dir exists
2. writes per-group CSV files
3. writes summary.json
4. optionally writes all_records.csv
5. optionally writes report.json
6. returns ExplicitPipelineCapacityReportExportResult
```

The default output directory is:

```text
outputs/explicit_pipeline
```

---

## 7. Implemented Env Helper

The implemented env helper is:

```python
maybe_export_explicit_pipeline_capacity_report_from_env(...)
```

Behavior:

```text
1. Read env.explicit_bridge_capacity_pipeline_report.
2. If missing, return None.
3. Export the report.
4. Attach env.explicit_bridge_capacity_pipeline_report_export_result.
5. Return the export result.
```

If no report exists, the helper is a no-op and does not create output files.

---

## 8. Exported Files

The exporter supports the following files.

### 8.1 Group CSV files

```text
capacity_usage.csv
capacity_violations.csv
lot_exceptions.csv
replan_candidates.csv
health_checks.csv
```

### 8.2 Summary JSON

```text
summary.json
```

### 8.3 Optional combined CSV

```text
all_records.csv
```

Written when:

```python
write_all_records=True
```

### 8.4 Optional full report JSON

```text
report.json
```

Written when:

```python
write_report_json=True
```

---

## 9. CSV Behavior

The exporter implements deterministic CSV behavior:

```text
predefined default columns per record group
sorted union of keys for non-empty row groups
JSON encoding for list / dict values
empty string for missing or None values
header row always written when a CSV is written
```

This makes the files useful both for human inspection and for downstream automation.

---

## 10. JSON Behavior

The exporter writes:

```text
summary.json
```

from:

```python
report.summary
```

with readable JSON formatting.

When enabled, it also writes:

```text
report.json
```

from:

```python
report_to_dict(report)
```

This gives both compact and full-report JSON options.

---

## 11. Empty Report Behavior

The exporter supports two empty-report modes.

### 11.1 write_empty_files=True

When:

```python
write_empty_files=True
```

the exporter writes CSV files with headers even if there are no records.

This is useful for automation because expected file names are stable.

### 11.2 write_empty_files=False

When:

```python
write_empty_files=False
```

empty CSV files are skipped.

In both cases:

```text
summary.json is still written
```

---

## 12. Package Export

The reporting package export was updated in:

```text
pysi/reporting/__init__.py
```

The following APIs were exported:

```text
ExplicitPipelineCapacityReportExportResult
export_explicit_pipeline_capacity_report
maybe_export_explicit_pipeline_capacity_report_from_env
```

---

## 13. Tests Added

The new focused test file is:

```text
tests/test_explicit_pipeline_capacity_report_export.py
```

It validates:

```text
1. synthetic report export
2. summary.json content
3. CSV content and JSON encoding
4. empty report export with write_empty_files=True
5. empty report export with write_empty_files=False
6. env helper no-op behavior
7. env helper export-result attachment
8. optional report.json output
```

---

## 14. Validation

The focused Phase 3c test passed:

```bat
python -m pytest tests/test_explicit_pipeline_capacity_report_export.py
```

Observed result:

```text
8 passed
```

The broader regression set also passed:

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
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results:

```text
tests/test_explicit_pipeline_capacity_report_attachment.py: 3 passed
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

## 15. Completion Criteria

This milestone satisfies the intended completion criteria.

```text
[OK] pysi/reporting/explicit_pipeline_capacity_report_exporter.py exists
[OK] ExplicitPipelineCapacityReportExportResult exists
[OK] export_explicit_pipeline_capacity_report(...) exists
[OK] maybe_export_explicit_pipeline_capacity_report_from_env(...) exists
[OK] CSV files are written
[OK] summary.json is written
[OK] all_records.csv is written when enabled
[OK] report.json is written when enabled
[OK] empty report behavior is tested
[OK] env helper no-op is tested
[OK] env helper attaches export result
[OK] focused tests pass
[OK] broader regression tests pass
[OK] no GUI changes
[OK] no planning-sequence changes
[OK] no Management Issue generation
[OK] no cost / KPI calculation
[OK] no replan execution
```

---

## 16. Meaning of This Milestone

Before Phase 3c:

```text
WOM could build and attach an in-memory ExplicitPipelineCapacityReport.
```

After Phase 3c:

```text
WOM can export that report as CSV / JSON audit files.
```

This means the explicit bridge + capacity pipeline result is now externally inspectable.

The reporting chain is now:

```text
execution result
    ↓
in-memory report
    ↓
exported audit trail
```

This is an important step before Management Issue candidate generation.

---

## 17. Current Pipeline Position

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
capacity report export          ✅ Phase 3c completed
    ↓
issue candidates
    ↓
cost/KPI
    ↓
GUI display
```

---

## 18. Known Limitations

Phase 3c is intentionally limited.

It does not implement:

```text
automatic export from planning sequence
GUI display
Management Issue generation
cost / KPI calculation
OR optimization
database persistence
ReplanCommand execution
```

The exporter is standalone and callable from tests or future integration points.

Automatic planning-sequence export should be controlled by a separate feature flag because file output is side-effectful.

---

## 19. Future Milestones

### 19.1 Optional export integration

A later phase may add a feature-controlled export call.

Potential flag:

```python
env.enable_explicit_pipeline_capacity_report_export
```

Default should be:

```text
False
```

### 19.2 Management Issue candidate generation

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

### 19.3 Cost / KPI integration

Future work should connect exported records and report summaries to:

```text
service level
capacity utilization
inventory overflow
cost impact
profit impact
opportunity loss
```

### 19.4 GUI display

GUI should display the report only after report structure, export, and issue-candidate mapping are stable.

---

## 20. Summary

Phase 3c is complete.

The key achievement is:

```text
ExplicitPipelineCapacityReport can now be exported as stable CSV / JSON audit files.
```

The completed chain is:

```text
ExplicitBridgeCapacityPipelineResult
    ↓
ExplicitPipelineCapacityReport
    ↓
ExplicitPipelineCapacityReportExportResult
    ↓
CSV / JSON files
```

This moves WOM one step further from planning execution toward explainable management decision support.
