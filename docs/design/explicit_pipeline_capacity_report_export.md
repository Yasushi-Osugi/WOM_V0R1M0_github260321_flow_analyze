# Explicit Pipeline Capacity Report Export Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-23  
**Status:** Design memo  
**Target path:** `docs/design/explicit_pipeline_capacity_report_export.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/explicit_pipeline_capacity_reporting.md`
- `docs/design/explicit_pipeline_capacity_reporting_completion.md`
- `docs/design/explicit_pipeline_capacity_report_attachment.md`
- `docs/design/explicit_pipeline_capacity_report_attachment_completion.md`
- `docs/design/run_full_plan_explicit_pipeline_insertion_completion.md`

---

## 1. Purpose

This memo defines **Phase 3c: Explicit Pipeline Capacity Report Export**.

Phase 3a completed the in-memory report object:

```text
ExplicitPipelineCapacityReport
```

Phase 3b attached that report to the planning environment:

```text
env.explicit_bridge_capacity_pipeline_report
```

Phase 3c should export that report to stable, human-readable and machine-readable files.

The purpose is to make the explicit bridge + capacity pipeline result externally inspectable before proceeding to:

```text
Management Issue candidate generation
Cost / KPI integration
GUI display
```

This phase is the audit trail / evidence layer.

---

## 2. Current Completed State

The current staged integration is:

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
    ↓
issue candidates
    ↓
cost/KPI
    ↓
GUI display
```

The current runtime state when the explicit pipeline feature flag is enabled is:

```text
env.explicit_bridge_capacity_pipeline_result
env.explicit_bridge_capacity_pipeline_report
```

Phase 3c exports:

```text
env.explicit_bridge_capacity_pipeline_report
```

to files.

---

## 3. Design Goal

The Phase 3c goal is deliberately small:

```text
Convert ExplicitPipelineCapacityReport into CSV / JSON files under outputs/explicit_pipeline/.
```

Recommended output files:

```text
outputs/explicit_pipeline/capacity_usage.csv
outputs/explicit_pipeline/capacity_violations.csv
outputs/explicit_pipeline/lot_exceptions.csv
outputs/explicit_pipeline/replan_candidates.csv
outputs/explicit_pipeline/health_checks.csv
outputs/explicit_pipeline/summary.json
```

Optional combined output:

```text
outputs/explicit_pipeline/all_records.csv
outputs/explicit_pipeline/report.json
```

Phase 3c should be file export only.

It should not create formal Management Issues yet.

---

## 4. Non-Goals

Phase 3c must not implement:

```text
GUI display
Management Issue generation
Cost / KPI calculation
OR optimization
automatic replanning
capacity editing UI
MOM policy editing UI
database persistence
```

Phase 3c is only:

```text
export attached report to stable files
```

---

## 5. Primary Input

Primary input:

```python
ExplicitPipelineCapacityReport
```

Likely source:

```python
env.explicit_bridge_capacity_pipeline_report
```

The report contains:

```text
capacity_usage_records
capacity_violation_records
lot_exception_records
replan_candidate_records
health_check_records
summary
message
```

---

## 6. Recommended Module

Suggested file:

```text
pysi/reporting/explicit_pipeline_capacity_report_exporter.py
```

Reason:

```text
The report builder is already in pysi/reporting.
Exporting belongs to reporting, not planning.
```

Alternative:

```text
pysi/reporting/explicit_pipeline_capacity_report.py
```

but a separate exporter module is preferred to keep responsibilities clean:

```text
report builder:
    creates in-memory report

report exporter:
    writes files
```

---

## 7. Recommended Test File

Suggested test:

```text
tests/test_explicit_pipeline_capacity_report_export.py
```

This should verify:

```text
1. CSV files are written.
2. summary.json is written.
3. Empty record groups still produce valid empty CSV files or are handled consistently.
4. Export helper is no-op when env has no report.
5. Export helper attaches/export paths to env if useful.
```

---

## 8. Export Result Dataclass

Recommended dataclass:

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

The result should be deterministic and easy to inspect.

---

## 9. Main Export Function

Recommended function:

```python
def export_explicit_pipeline_capacity_report(
    report,
    *,
    output_dir: str | Path = "outputs/explicit_pipeline",
    write_empty_files: bool = True,
) -> ExplicitPipelineCapacityReportExportResult:
    ...
```

Expected behavior:

```text
1. Ensure output_dir exists.
2. Write one CSV per record group.
3. Write summary.json.
4. Optionally write all_records.csv.
5. Return export result with file paths and record counts.
```

---

## 10. Env Helper

Recommended helper:

```python
def maybe_export_explicit_pipeline_capacity_report_from_env(
    env,
    *,
    output_dir: str | Path = "outputs/explicit_pipeline",
    write_empty_files: bool = True,
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

This helper should not display anything in GUI.

---

## 11. Output Directory Policy

Default output directory:

```text
outputs/explicit_pipeline
```

Rationale:

```text
The explicit pipeline is still optional / feature-flagged.
Its outputs should be grouped separately from existing reporting outputs.
```

Later, this can be integrated into the standard reporting bundle if desired.

---

## 12. Output File Policy

### 12.1 Capacity usage

```text
capacity_usage.csv
```

Source:

```python
report.capacity_usage_records
```

### 12.2 Capacity violations

```text
capacity_violations.csv
```

Source:

```python
report.capacity_violation_records
```

### 12.3 Lot exceptions

```text
lot_exceptions.csv
```

Source:

```python
report.lot_exception_records
```

### 12.4 Replan candidates

```text
replan_candidates.csv
```

Source:

```python
report.replan_candidate_records
```

### 12.5 Health checks

```text
health_checks.csv
```

Source:

```python
report.health_check_records
```

### 12.6 Summary

```text
summary.json
```

Source:

```python
report.summary
```

### 12.7 Optional combined records

```text
all_records.csv
```

Source:

```python
report_records_as_rows(report)
```

This is useful for quick inspection and later issue candidate generation.

---

## 13. CSV Column Policy

The record groups may contain different keys.

Recommended approach:

```text
For each CSV, union all keys from all rows.
Sort columns deterministically.
Write header even if there are no rows when write_empty_files=True.
```

Suggested default columns for empty files:

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

All list/dict values should be JSON-encoded in CSV cells.

---

## 14. JSON Policy

Write:

```text
summary.json
```

with pretty formatting:

```python
json.dump(summary, f, ensure_ascii=False, indent=2)
```

Optional:

```text
report.json
```

can include:

```text
product_name
message
summary
capacity_usage_records
capacity_violation_records
lot_exception_records
replan_candidate_records
health_check_records
```

If implemented, it should use `report_to_dict(report)`.

Phase 3c MVP may include only `summary.json` and CSV files.

---

## 15. Empty Report Behavior

If the report exists but all record groups are empty:

```text
summary.json should still be written.
CSV behavior depends on write_empty_files.
```

Recommended default:

```python
write_empty_files=True
```

This gives predictable outputs for automation and GUI integration.

---

## 16. No Report Behavior

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

This preserves feature-flag-off behavior.

---

## 17. Integration with Planning Sequence

Phase 3c design can be implemented in two substeps.

### Phase 3c-1: standalone exporter

Add exporter module and tests.

No planning sequence modification.

### Phase 3c-2: optional env export call

Later, add a feature-controlled call after report attachment.

Potential env flag:

```python
env.enable_explicit_pipeline_capacity_report_export
```

Default:

```text
False
```

Reason:

```text
Exporting files is side-effectful.
It should be explicitly enabled.
```

Recommended Phase 3c MVP:

```text
Implement exporter and env helper,
but do not automatically call it from _run_planning_sequence yet.
```

This is safer.

---

## 18. Export Feature Flag

Because file writing is a side effect, use a separate export flag if planning-sequence integration is added.

Recommended flag:

```python
env.enable_explicit_pipeline_capacity_report_export
```

Default:

```text
False
```

If the flag is not added in Phase 3c MVP, the exporter remains callable manually or by tests.

---

## 19. Relationship to Issue Candidates

The exported files are the audit trail for issue candidate generation.

Future flow:

```text
capacity_report
    ↓
exported records
    ↓
issue candidate builder
```

Issue candidate generation should consume either:

```text
in-memory report records
```

or:

```text
exported CSV / JSON files
```

But Phase 3c should not generate issues.

---

## 20. Relationship to Cost / KPI

Future cost / KPI integration may use:

```text
capacity_violations.csv
lot_exceptions.csv
summary.json
```

Examples:

```text
blocked lots → opportunity loss candidate
overflow_i lots → inventory holding cost candidate
shifted lots → early-build inventory timing impact
capacity usage → utilization KPI
```

Phase 3c should not calculate those values.

---

## 21. Relationship to GUI

Future GUI display can use:

```text
env.explicit_bridge_capacity_pipeline_report
```

or the exported files.

Phase 3c does not add GUI display.

If automatic export is added later, GUI can provide a link/button to open output folder, but not in this phase.

---

## 22. Testing Strategy

### 22.1 Export synthetic report

Build an `ExplicitPipelineCapacityReport` with:

```text
one capacity usage record
one capacity violation record
one lot exception record
one replan candidate record
one health check record
summary
```

Export to a temporary directory.

Verify files exist.

### 22.2 Verify summary.json

Read `summary.json`.

Verify:

```text
product
record counts
has_error
has_warning
```

### 22.3 Verify CSV content

Read at least:

```text
capacity_usage.csv
lot_exceptions.csv
all_records.csv if implemented
```

Verify rows and headers.

### 22.4 Empty report export

Export an empty report.

Verify:

```text
summary.json exists
CSV files exist if write_empty_files=True
record counts are zero
```

### 22.5 Env helper no-op

Create env without report.

Verify:

```text
maybe_export_explicit_pipeline_capacity_report_from_env(env) is None
```

### 22.6 Env helper attaches export result

Create env with report.

Verify:

```text
env.explicit_bridge_capacity_pipeline_report_export_result exists
```

---

## 23. Existing Tests to Run

Run:

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

---

## 24. Recommended Implementation Scope

Recommended Phase 3c MVP implementation:

```text
pysi/reporting/explicit_pipeline_capacity_report_exporter.py
tests/test_explicit_pipeline_capacity_report_export.py
```

Optional minimal export from package:

```text
pysi/reporting/__init__.py
```

Do not modify:

```text
pysi/gui/cockpit_tk.py
```

in Phase 3c MVP unless explicitly enabling export from the planning sequence.

---

## 25. Completion Criteria

Phase 3c design is complete when it defines:

```text
[OK] exporter module location
[OK] export result dataclass
[OK] main export function
[OK] env export helper
[OK] output directory policy
[OK] output file names
[OK] CSV column policy
[OK] JSON policy
[OK] empty report behavior
[OK] no-report behavior
[OK] export feature flag concept
[OK] test strategy
[OK] boundaries from issue candidates / cost / KPI / GUI
```

---

## 26. Summary

Phase 3c should make the explicit pipeline capacity report externally inspectable.

The target export flow is:

```text
env.explicit_bridge_capacity_pipeline_report
    ↓
export_explicit_pipeline_capacity_report(...)
    ↓
outputs/explicit_pipeline/*.csv
outputs/explicit_pipeline/summary.json
```

The recommended MVP is:

```text
standalone exporter + tests
no automatic planning-sequence export yet
```

This creates the audit trail needed before moving into issue candidates.
