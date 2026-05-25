# Codex Request: Implement Explicit Pipeline Capacity Report Export MVP

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/explicit_pipeline_capacity_report_export.md
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
capacity report attachment      ✅ Phase 3b completed
    ↓
capacity report export          ← Phase 3c target
```

Phase 3a added:

```text
pysi/reporting/explicit_pipeline_capacity_report.py
```

with:

```python
ExplicitPipelineCapacityReport
build_explicit_pipeline_capacity_report(...)
maybe_build_explicit_pipeline_capacity_report_from_env(...)
report_to_dict(...)
report_records_as_rows(...)
```

Phase 3b attached the report to env:

```python
env.explicit_bridge_capacity_pipeline_report
```

This request is **Phase 3c**.

Phase 3c should implement a standalone exporter that writes the in-memory report to CSV / JSON files.

Do not automatically call the exporter from `_run_planning_sequence` yet.

---

## 2. Main Objective

Add a standalone report exporter that converts:

```python
ExplicitPipelineCapacityReport
```

into files under:

```text
outputs/explicit_pipeline/
```

Recommended output files:

```text
capacity_usage.csv
capacity_violations.csv
lot_exceptions.csv
replan_candidates.csv
health_checks.csv
summary.json
all_records.csv
```

The exporter should be callable from tests and future pipeline stages, but Phase 3c MVP should not add automatic planning-sequence export.

---

## 3. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan / _run_planning_sequence.
3. Do not automatically export from the planning sequence.
4. Do not implement Management Issue generation.
5. Do not implement cost / KPI calculation.
6. Do not implement OR optimization.
7. Do not execute ReplanCommand.
8. Do not add database persistence.
9. Keep this as standalone exporter + tests.
```

This request is only for:

```text
Phase 3c: explicit pipeline capacity report export MVP
```

---

## 4. Files to Add / Modify

Please add:

```text
pysi/reporting/explicit_pipeline_capacity_report_exporter.py
tests/test_explicit_pipeline_capacity_report_export.py
```

Optionally update:

```text
pysi/reporting/__init__.py
```

to export the new APIs if this is consistent with existing package style.

Do not modify:

```text
pysi/gui/*
run_full_plan
planning sequence
loaders
costing / KPI modules
Management Issue modules
```

---

## 5. Existing Components to Reuse

Reuse:

```python
ExplicitPipelineCapacityReport
report_to_dict(...)
report_records_as_rows(...)
```

from:

```text
pysi/reporting/explicit_pipeline_capacity_report.py
```

The exporter should not rebuild the report.

It should only export an already-built report.

---

## 6. Export Result Dataclass

Please implement:

```python
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExplicitPipelineCapacityReportExportResult:
    output_dir: Path
    files: dict[str, Path] = field(default_factory=dict)
    record_counts: dict[str, int] = field(default_factory=dict)
    summary_path: Path | None = None
    message: str = ""
```

This object should be deterministic and easy to inspect in tests.

---

## 7. Main Export Function

Please implement:

```python
def export_explicit_pipeline_capacity_report(
    report,
    *,
    output_dir: str | Path = "outputs/explicit_pipeline",
    write_empty_files: bool = True,
    write_all_records: bool = True,
    write_report_json: bool = False,
) -> ExplicitPipelineCapacityReportExportResult:
    ...
```

Expected behavior:

```text
1. Ensure output_dir exists.
2. Write one CSV file per record group.
3. Write summary.json.
4. Optionally write all_records.csv.
5. Optionally write report.json.
6. Return ExplicitPipelineCapacityReportExportResult.
```

---

## 8. Env Helper

Please implement:

```python
def maybe_export_explicit_pipeline_capacity_report_from_env(
    env,
    *,
    output_dir: str | Path = "outputs/explicit_pipeline",
    write_empty_files: bool = True,
    write_all_records: bool = True,
    write_report_json: bool = False,
):
    ...
```

Expected behavior:

```text
1. Read env.explicit_bridge_capacity_pipeline_report.
2. If missing, return None.
3. Export report.
4. Attach env.explicit_bridge_capacity_pipeline_report_export_result.
5. Return export result.
```

The helper must not display anything in GUI.

The helper must not create files if no report exists.

---

## 9. Output Directory

Default:

```text
outputs/explicit_pipeline
```

The function should accept a custom `output_dir`, especially for tests using temporary directories.

Use `pathlib.Path`.

Create the directory with:

```python
Path(output_dir).mkdir(parents=True, exist_ok=True)
```

---

## 10. Output Files

### 10.1 Capacity usage

```text
capacity_usage.csv
```

Source:

```python
report.capacity_usage_records
```

### 10.2 Capacity violations

```text
capacity_violations.csv
```

Source:

```python
report.capacity_violation_records
```

### 10.3 Lot exceptions

```text
lot_exceptions.csv
```

Source:

```python
report.lot_exception_records
```

### 10.4 Replan candidates

```text
replan_candidates.csv
```

Source:

```python
report.replan_candidate_records
```

### 10.5 Health checks

```text
health_checks.csv
```

Source:

```python
report.health_check_records
```

### 10.6 Summary

```text
summary.json
```

Source:

```python
report.summary
```

### 10.7 Combined records

```text
all_records.csv
```

Source:

```python
report_records_as_rows(report)
```

Only write this when:

```python
write_all_records=True
```

### 10.8 Full report JSON

```text
report.json
```

Source:

```python
report_to_dict(report)
```

Only write this when:

```python
write_report_json=True
```

---

## 11. CSV Column Policy

The record groups may contain different keys.

Please implement deterministic CSV columns.

Recommended behavior:

```text
1. For non-empty rows:
     union all keys from all rows
     sort columns deterministically
2. For empty rows and write_empty_files=True:
     use predefined default columns per file
3. JSON-encode list/dict values inside CSV cells
4. Write header row
```

Suggested default columns:

### capacity_usage.csv

```text
record_type,product,node,week,capacity_type,capacity,used,remaining,utilization_ratio,source,message,lot_ids
```

### capacity_violations.csv

```text
record_type,product,node,week,capacity_type,severity,capacity,requested,overflow,lot_ids,source,message
```

### lot_exceptions.csv

```text
record_type,exception_type,product,lot_id,node,week,source,message
```

### replan_candidates.csv

```text
record_type,command_type,product,node,week,capacity_type,lot_ids,suggested_action,source,message
```

### health_checks.csv

```text
record_type,check_type,severity,count,details,source,message
```

### all_records.csv

```text
record_type,product,node,week,capacity_type,lot_id,lot_ids,severity,source,message
```

Do not require every row to have every column; use empty string for missing values.

---

## 12. JSON Policy

Write `summary.json` with:

```python
json.dump(report.summary, f, ensure_ascii=False, indent=2)
```

If `write_report_json=True`, write `report.json` with:

```python
json.dump(report_to_dict(report), f, ensure_ascii=False, indent=2)
```

Make sure paths and non-primitive values are serializable.

---

## 13. Empty Report Behavior

If the report exists but all record groups are empty:

```text
summary.json should still be written.
```

When:

```python
write_empty_files=True
```

write CSV files with headers even if no rows exist.

When:

```python
write_empty_files=False
```

skip empty CSV files.

---

## 14. No Report Behavior

If env has no:

```python
env.explicit_bridge_capacity_pipeline_report
```

then:

```python
maybe_export_explicit_pipeline_capacity_report_from_env(env)
```

should return:

```python
None
```

and should not create files.

---

## 15. Record Counts

The export result should include record counts such as:

```python
{
    "capacity_usage": len(report.capacity_usage_records),
    "capacity_violations": len(report.capacity_violation_records),
    "lot_exceptions": len(report.lot_exception_records),
    "replan_candidates": len(report.replan_candidate_records),
    "health_checks": len(report.health_check_records),
    "all_records": len(report_records_as_rows(report)),
}
```

Use stable keys.

---

## 16. Package Export

If updating `pysi/reporting/__init__.py`, export:

```python
ExplicitPipelineCapacityReportExportResult
export_explicit_pipeline_capacity_report
maybe_export_explicit_pipeline_capacity_report_from_env
```

Keep the update minimal.

---

## 17. Tests to Add

Please add:

```text
tests/test_explicit_pipeline_capacity_report_export.py
```

### 17.1 Export synthetic report

Build an `ExplicitPipelineCapacityReport` with:

```text
one capacity usage record
one capacity violation record
one lot exception record
one replan candidate record
one health check record
summary
```

Export to `tmp_path`.

Verify files exist:

```text
capacity_usage.csv
capacity_violations.csv
lot_exceptions.csv
replan_candidates.csv
health_checks.csv
summary.json
all_records.csv
```

Verify export result fields:

```text
output_dir
files
record_counts
summary_path
```

### 17.2 Verify summary.json

Read `summary.json`.

Verify:

```text
product
record counts
has_error
has_warning
```

### 17.3 Verify CSV content

Read at least:

```text
capacity_usage.csv
lot_exceptions.csv
all_records.csv
```

Verify:

```text
header exists
expected row exists
list/dict fields are JSON-encoded if present
```

### 17.4 Empty report export

Export an empty `ExplicitPipelineCapacityReport` with:

```python
write_empty_files=True
```

Verify:

```text
summary.json exists
CSV files exist with headers
record counts are zero
```

### 17.5 write_empty_files=False

Export an empty report with:

```python
write_empty_files=False
```

Verify:

```text
summary.json exists
empty CSV files are skipped
```

### 17.6 Env helper no-op

Create env without report.

Verify:

```python
maybe_export_explicit_pipeline_capacity_report_from_env(env, output_dir=tmp_path) is None
```

Also verify output directory is not created, or no files are created.

### 17.7 Env helper attaches export result

Create env with:

```python
env.explicit_bridge_capacity_pipeline_report = report
```

Call helper.

Verify:

```text
env.explicit_bridge_capacity_pipeline_report_export_result exists
```

---

## 18. Existing Tests to Run

Please run:

```bat
python -m pytest tests/test_explicit_pipeline_capacity_report_export.py
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

If optional tests are not run, state so clearly.

---

## 19. Completion Criteria

This request is complete when:

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
[OK] no GUI changes
[OK] no planning-sequence changes
[OK] no Management Issue generation
[OK] no cost / KPI calculation
[OK] no replan execution
```

---

## 20. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. Exported files
4. CSV column / JSON encoding behavior
5. Empty report behavior
6. Env helper behavior
7. Test commands executed
8. Test results
9. Limitations / follow-up
```

Please do not proceed into:

```text
automatic planning-sequence export
GUI display
Management Issue generation
costing / KPI integration
OR optimization
database persistence
```

This request is only for:

```text
Phase 3c: standalone explicit pipeline capacity report exporter MVP
```
