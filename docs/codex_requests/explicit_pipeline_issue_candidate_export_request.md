# Codex Request: Implement Explicit Pipeline Issue Candidate Export MVP

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/explicit_pipeline_issue_candidate_export.md
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
capacity report export          ✅ Phase 3c completed
    ↓
issue candidates                ✅ Phase 4 completed
    ↓
issue candidate export          ← current request target
    ↓
cost/KPI
    ↓
GUI display
```

Phase 4 added the in-memory issue candidate bundle:

```python
ExplicitPipelineIssueCandidateBundle
```

and helpers:

```python
build_explicit_pipeline_issue_candidates(...)
maybe_build_explicit_pipeline_issue_candidates_from_env(...)
issue_candidates_to_dict(...)
issue_candidates_as_rows(...)
```

This request should implement a standalone exporter for that issue candidate bundle.

---

## 2. Main Objective

Add a standalone exporter that converts:

```python
ExplicitPipelineIssueCandidateBundle
```

into stable CSV / JSON files under:

```text
outputs/explicit_pipeline/issue_candidates/
```

The intended transformation is:

```text
ExplicitPipelineIssueCandidateBundle
    ↓
export_explicit_pipeline_issue_candidates(...)
    ↓
planning_issues.csv
management_issues.csv
replan_command_candidates.csv
health_issues.csv
all_issue_candidates.csv
summary.json
```

The exporter must not execute replan commands.

The exporter must not calculate Cost / KPI.

The exporter must not modify GUI or planning sequence.

---

## 3. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan / _run_planning_sequence.
3. Do not execute ReplanCommand.
4. Do not implement automatic replanning.
5. Do not implement cost / KPI calculation.
6. Do not implement OR optimization.
7. Do not implement database persistence.
8. Do not implement knowledge continuity persistence.
9. Keep this as standalone exporter + focused tests.
```

This request is only for:

```text
Explicit Pipeline Issue Candidate Export MVP
```

---

## 4. Files to Add / Modify

Please add:

```text
pysi/reporting/explicit_pipeline_issue_candidate_exporter.py
tests/test_explicit_pipeline_issue_candidate_export.py
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
capacity report exporter
issue candidate builder logic
cost / KPI modules
optimization modules
```

---

## 5. Existing Components to Reuse

Reuse these from:

```text
pysi/reporting/explicit_pipeline_issue_candidates.py
```

```python
ExplicitPipelineIssueCandidateBundle
issue_candidates_to_dict(...)
issue_candidates_as_rows(...)
```

The exporter should not rebuild issue candidates.

It should only export an already-built issue candidate bundle.

---

## 6. Export Result Dataclass

Please implement:

```python
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExplicitPipelineIssueCandidateExportResult:
    output_dir: Path
    files: dict[str, Path] = field(default_factory=dict)
    record_counts: dict[str, int] = field(default_factory=dict)
    summary_path: Path | None = None
    message: str = ""
```

This mirrors the capacity report exporter design.

The result should be deterministic and easy to inspect in tests.

---

## 7. Main Export Function

Please implement:

```python
def export_explicit_pipeline_issue_candidates(
    bundle,
    *,
    output_dir: str | Path = "outputs/explicit_pipeline/issue_candidates",
    write_empty_files: bool = True,
    write_all_candidates: bool = True,
    write_bundle_json: bool = False,
) -> ExplicitPipelineIssueCandidateExportResult:
    ...
```

Expected behavior:

```text
1. Ensure output_dir exists.
2. Write one CSV file per candidate group.
3. Write summary.json.
4. Optionally write all_issue_candidates.csv.
5. Optionally write issue_candidate_bundle.json.
6. Return ExplicitPipelineIssueCandidateExportResult.
```

---

## 8. Env Helper

Please implement:

```python
def maybe_export_explicit_pipeline_issue_candidates_from_env(
    env,
    *,
    output_dir: str | Path = "outputs/explicit_pipeline/issue_candidates",
    write_empty_files: bool = True,
    write_all_candidates: bool = True,
    write_bundle_json: bool = False,
):
    ...
```

Expected behavior:

```text
1. Read env.explicit_bridge_capacity_issue_candidates.
2. If missing, return None.
3. Export the bundle.
4. Attach env.explicit_bridge_capacity_issue_candidate_export_result.
5. Return the export result.
```

The helper must not display anything in GUI.

The helper must not create files if no issue candidate bundle exists.

---

## 9. Output Directory

Default:

```text
outputs/explicit_pipeline/issue_candidates
```

The function should accept custom `output_dir`, especially for tests using `tmp_path`.

Use `pathlib.Path`.

Create the directory with:

```python
Path(output_dir).mkdir(parents=True, exist_ok=True)
```

only when an export actually runs.

---

## 10. Output Files

### 10.1 Planning issues

```text
planning_issues.csv
```

Source:

```python
bundle.planning_issue_candidates
```

### 10.2 Management issues

```text
management_issues.csv
```

Source:

```python
bundle.management_issue_candidates
```

### 10.3 Replan command candidates

```text
replan_command_candidates.csv
```

Source:

```python
bundle.replan_command_candidates
```

### 10.4 Health issues

```text
health_issues.csv
```

Source:

```python
bundle.health_issue_candidates
```

### 10.5 Summary

```text
summary.json
```

Source:

```python
bundle.summary
```

### 10.6 Combined candidates

```text
all_issue_candidates.csv
```

Source:

```python
issue_candidates_as_rows(bundle)
```

Only write this when:

```python
write_all_candidates=True
```

### 10.7 Full bundle JSON

```text
issue_candidate_bundle.json
```

Source:

```python
issue_candidates_to_dict(bundle)
```

Only write this when:

```python
write_bundle_json=True
```

---

## 11. CSV Column Policy

Candidate groups may contain different keys.

Please implement deterministic CSV columns.

Recommended behavior:

```text
1. For non-empty rows:
     union all keys from all rows
     sort columns deterministically
2. For empty rows and write_empty_files=True:
     use predefined default columns per file
3. JSON-encode list/dict values inside CSV cells
4. Write header row whenever a CSV is written
5. Use empty string for missing or None values
```

Suggested default columns:

### planning_issues.csv

```text
candidate_type,issue_type,severity,product,node,week,capacity_type,lot_ids,evidence_record_type,source,message,suggested_action
```

### management_issues.csv

```text
candidate_type,issue_type,severity,product,node,week,capacity_type,lot_ids,business_theme,evidence_record_type,source,message,suggested_decision
```

### replan_command_candidates.csv

```text
candidate_type,command_type,status,product,node,week,capacity_type,lot_ids,source,message,suggested_action
```

### health_issues.csv

```text
candidate_type,issue_type,severity,product,details,evidence_record_type,source,message
```

### all_issue_candidates.csv

```text
candidate_type,issue_type,severity,product,node,week,capacity_type,lot_ids,source,message
```

Do not require every row to have every column.

Use empty string for missing values.

---

## 12. JSON Policy

Write `summary.json` with:

```python
json.dump(bundle.summary, f, ensure_ascii=False, indent=2)
```

If `write_bundle_json=True`, write `issue_candidate_bundle.json` with:

```python
json.dump(issue_candidates_to_dict(bundle), f, ensure_ascii=False, indent=2)
```

Use `default=str` if needed to ensure serializability.

---

## 13. Empty Bundle Behavior

If the bundle exists but all candidate lists are empty:

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

## 14. No Bundle Behavior

If env has no:

```python
env.explicit_bridge_capacity_issue_candidates
```

then:

```python
maybe_export_explicit_pipeline_issue_candidates_from_env(env)
```

should return:

```python
None
```

and should not create files.

---

## 15. Record Counts

The export result should include stable record counts such as:

```python
{
    "planning_issues": len(bundle.planning_issue_candidates),
    "management_issues": len(bundle.management_issue_candidates),
    "replan_command_candidates": len(bundle.replan_command_candidates),
    "health_issues": len(bundle.health_issue_candidates),
    "all_issue_candidates": len(issue_candidates_as_rows(bundle)),
}
```

Use these stable keys.

---

## 16. Package Export

If updating `pysi/reporting/__init__.py`, export:

```python
ExplicitPipelineIssueCandidateExportResult
export_explicit_pipeline_issue_candidates
maybe_export_explicit_pipeline_issue_candidates_from_env
```

Keep the update minimal.

---

## 17. Tests to Add

Please add:

```text
tests/test_explicit_pipeline_issue_candidate_export.py
```

### 17.1 Export synthetic candidate bundle

Build an `ExplicitPipelineIssueCandidateBundle` with:

```text
one planning issue
one management issue
one replan command candidate
one health issue
summary
```

Export to `tmp_path`.

Verify files exist:

```text
planning_issues.csv
management_issues.csv
replan_command_candidates.csv
health_issues.csv
summary.json
all_issue_candidates.csv
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
candidate counts
has_error
has_warning
```

### 17.3 Verify CSV content

Read at least:

```text
planning_issues.csv
management_issues.csv
replan_command_candidates.csv
all_issue_candidates.csv
```

Verify:

```text
header exists
expected row exists
lot_ids are JSON-encoded
status=candidate_only is preserved for replan command candidates
```

### 17.4 Empty bundle export

Export an empty `ExplicitPipelineIssueCandidateBundle` with:

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

Export an empty bundle with:

```python
write_empty_files=False
```

Verify:

```text
summary.json exists
empty CSV files are skipped
```

### 17.6 Env helper no-op

Create env without issue candidate bundle.

Verify:

```python
maybe_export_explicit_pipeline_issue_candidates_from_env(env, output_dir=tmp_path) is None
```

Also verify output directory is not created, or no files are created.

### 17.7 Env helper attaches export result

Create env with:

```python
env.explicit_bridge_capacity_issue_candidates = bundle
```

Call helper.

Verify:

```text
env.explicit_bridge_capacity_issue_candidate_export_result exists
```

### 17.8 Optional bundle JSON

Export with:

```python
write_bundle_json=True
```

Verify:

```text
issue_candidate_bundle.json exists
```

---

## 18. Existing Tests to Run

Please run:

```bat
python -m pytest tests/test_explicit_pipeline_issue_candidate_export.py
python -m pytest tests/test_explicit_pipeline_issue_candidates.py
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
[OK] pysi/reporting/explicit_pipeline_issue_candidate_exporter.py exists
[OK] ExplicitPipelineIssueCandidateExportResult exists
[OK] export_explicit_pipeline_issue_candidates(...) exists
[OK] maybe_export_explicit_pipeline_issue_candidates_from_env(...) exists
[OK] planning_issues.csv is written
[OK] management_issues.csv is written
[OK] replan_command_candidates.csv is written
[OK] health_issues.csv is written
[OK] summary.json is written
[OK] all_issue_candidates.csv is written when enabled
[OK] issue_candidate_bundle.json is written when enabled
[OK] empty bundle behavior is tested
[OK] env helper no-op is tested
[OK] env helper attaches export result
[OK] focused tests pass
[OK] no GUI changes
[OK] no planning-sequence changes
[OK] no cost / KPI calculation
[OK] no command execution
```

---

## 20. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. Exported files
4. CSV column / JSON encoding behavior
5. Empty bundle behavior
6. Env helper behavior
7. Test commands executed
8. Test results
9. Limitations / follow-up
```

Please do not proceed into:

```text
automatic planning-sequence export
GUI display
costing / KPI integration
OR optimization
database persistence
ReplanCommand execution
Knowledge Continuity persistence
```

This request is only for:

```text
Explicit Pipeline Issue Candidate Export MVP
```
