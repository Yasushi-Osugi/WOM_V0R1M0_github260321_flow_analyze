# Explicit Pipeline Issue Candidate Export Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-23  
**Status:** Design memo  
**Target path:** `docs/design/explicit_pipeline_issue_candidate_export.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/explicit_pipeline_phase1_to_phase4_overview.md`
- `docs/design/explicit_pipeline_management_issue_candidates.md`
- `docs/design/explicit_pipeline_management_issue_candidates_completion.md`
- `docs/design/explicit_pipeline_capacity_report_export.md`
- `docs/design/explicit_pipeline_capacity_report_export_completion.md`
- `docs/design/wom_knowledge_continuity_layer.md`

---

## 1. Purpose

This memo defines the design for **Explicit Pipeline Issue Candidate Export**.

Phase 4 completed the in-memory issue candidate bundle:

```text
ExplicitPipelineCapacityReport
    ↓
ExplicitPipelineIssueCandidateBundle
    ↓
planning_issue_candidates
management_issue_candidates
replan_command_candidates
health_issue_candidates
summary
```

This design defines the next step:

```text
ExplicitPipelineIssueCandidateBundle
    ↓
issue candidate exporter
    ↓
CSV / JSON audit files
```

The purpose is to make Planning / Management / Replan / Health issue candidates externally inspectable before moving into:

```text
Cost / KPI enrichment
GUI display
knowledge continuity integration
```

This phase is the issue-level audit trail.

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
capacity report attachment      ✅ Phase 3b completed
    ↓
capacity report export          ✅ Phase 3c completed
    ↓
issue candidates                ✅ Phase 4 completed
    ↓
issue candidate export          ← next target
    ↓
cost/KPI
    ↓
GUI display
```

The current in-memory object is:

```python
ExplicitPipelineIssueCandidateBundle
```

The bundle includes:

```text
planning_issue_candidates
management_issue_candidates
replan_command_candidates
health_issue_candidates
summary
```

---

## 3. Design Goal

The goal is deliberately small:

```text
Export ExplicitPipelineIssueCandidateBundle into stable CSV / JSON files.
```

Recommended output files:

```text
outputs/explicit_pipeline/issue_candidates/planning_issues.csv
outputs/explicit_pipeline/issue_candidates/management_issues.csv
outputs/explicit_pipeline/issue_candidates/replan_command_candidates.csv
outputs/explicit_pipeline/issue_candidates/health_issues.csv
outputs/explicit_pipeline/issue_candidates/all_issue_candidates.csv
outputs/explicit_pipeline/issue_candidates/summary.json
```

Optional output:

```text
outputs/explicit_pipeline/issue_candidates/issue_candidate_bundle.json
```

This phase should not calculate Cost / KPI values.

It should not display anything in GUI.

It should not execute replan commands.

---

## 4. Non-Goals

This phase must not implement:

```text
automatic replanning
ReplanCommand execution
GUI display
cost / KPI calculation
OR optimization
database persistence
final management decision logic
issue approval workflow
knowledge DB persistence
```

This phase is only:

```text
export issue candidate bundle to files
```

---

## 5. Primary Input

Primary input:

```python
ExplicitPipelineIssueCandidateBundle
```

Likely source:

```python
env.explicit_bridge_capacity_issue_candidates
```

The bundle is produced by:

```python
build_explicit_pipeline_issue_candidates(...)
maybe_build_explicit_pipeline_issue_candidates_from_env(env)
```

from:

```text
pysi/reporting/explicit_pipeline_issue_candidates.py
```

---

## 6. Recommended Module

Suggested file:

```text
pysi/reporting/explicit_pipeline_issue_candidate_exporter.py
```

Reason:

```text
Issue candidates are reporting-derived decision-support records.
Exporting belongs to reporting, not planning engines.
```

This mirrors the existing capacity report exporter:

```text
pysi/reporting/explicit_pipeline_capacity_report_exporter.py
```

---

## 7. Recommended Test File

Suggested test:

```text
tests/test_explicit_pipeline_issue_candidate_export.py
```

The test should use synthetic `ExplicitPipelineIssueCandidateBundle` objects.

It may also build a bundle from a synthetic `ExplicitPipelineCapacityReport` using the Phase 4 builder.

---

## 8. Export Result Dataclass

Recommended dataclass:

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

This mirrors the capacity report export result design.

---

## 9. Main Export Function

Recommended function:

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
2. Write one CSV per candidate group.
3. Write summary.json.
4. Optionally write all_issue_candidates.csv.
5. Optionally write issue_candidate_bundle.json.
6. Return ExplicitPipelineIssueCandidateExportResult.
```

---

## 10. Env Helper

Recommended helper:

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

This helper should not display anything in GUI.

This helper should not create files if no issue candidate bundle exists.

---

## 11. Output Directory Policy

Default output directory:

```text
outputs/explicit_pipeline/issue_candidates
```

Rationale:

```text
Capacity report exports and issue candidate exports should be separated.
```

Current capacity report export default:

```text
outputs/explicit_pipeline
```

Issue candidate export should be nested under:

```text
outputs/explicit_pipeline/issue_candidates
```

to keep the audit trail organized.

---

## 12. Output File Policy

### 12.1 Planning issues

```text
planning_issues.csv
```

Source:

```python
bundle.planning_issue_candidates
```

### 12.2 Management issues

```text
management_issues.csv
```

Source:

```python
bundle.management_issue_candidates
```

### 12.3 Replan command candidates

```text
replan_command_candidates.csv
```

Source:

```python
bundle.replan_command_candidates
```

### 12.4 Health issues

```text
health_issues.csv
```

Source:

```python
bundle.health_issue_candidates
```

### 12.5 Summary

```text
summary.json
```

Source:

```python
bundle.summary
```

### 12.6 Combined candidates

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

### 12.7 Full bundle JSON

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

## 13. CSV Column Policy

Candidate groups may contain different keys.

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

Suggested default columns are below.

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

All list/dict values should be JSON-encoded.

---

## 14. JSON Policy

Write:

```text
summary.json
```

with:

```python
json.dump(bundle.summary, f, ensure_ascii=False, indent=2)
```

If `write_bundle_json=True`, write:

```text
issue_candidate_bundle.json
```

with:

```python
json.dump(issue_candidates_to_dict(bundle), f, ensure_ascii=False, indent=2)
```

Use `default=str` if needed to ensure serializability.

---

## 15. Empty Bundle Behavior

If the bundle exists but all candidate lists are empty:

```text
summary.json should still be written.
```

When:

```python
write_empty_files=True
```

CSV files should be written with headers even if there are no rows.

When:

```python
write_empty_files=False
```

empty CSV files should be skipped.

---

## 16. No Bundle Behavior

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

This preserves feature-flag-off and non-integrated behavior.

---

## 17. Record Counts

The export result should include stable record counts:

```python
{
    "planning_issues": len(bundle.planning_issue_candidates),
    "management_issues": len(bundle.management_issue_candidates),
    "replan_command_candidates": len(bundle.replan_command_candidates),
    "health_issues": len(bundle.health_issue_candidates),
    "all_issue_candidates": len(issue_candidates_as_rows(bundle)),
}
```

---

## 18. Package Export

If updating `pysi/reporting/__init__.py`, export:

```python
ExplicitPipelineIssueCandidateExportResult
export_explicit_pipeline_issue_candidates
maybe_export_explicit_pipeline_issue_candidates_from_env
```

Keep the update minimal.

---

## 19. Tests to Add

Please add:

```text
tests/test_explicit_pipeline_issue_candidate_export.py
```

### 19.1 Export synthetic candidate bundle

Create an `ExplicitPipelineIssueCandidateBundle` with:

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

### 19.2 Verify summary.json

Read `summary.json`.

Verify:

```text
product
candidate counts
has_error
has_warning
```

### 19.3 Verify CSV content

Read at least:

```text
planning_issues.csv
management_issues.csv
all_issue_candidates.csv
```

Verify:

```text
header exists
expected row exists
lot_ids are JSON-encoded
status=candidate_only is preserved for replan command candidates
```

### 19.4 Empty bundle export

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

### 19.5 write_empty_files=False

Export an empty bundle with:

```python
write_empty_files=False
```

Verify:

```text
summary.json exists
empty CSV files are skipped
```

### 19.6 Env helper no-op

Create env without issue candidate bundle.

Verify:

```python
maybe_export_explicit_pipeline_issue_candidates_from_env(env, output_dir=tmp_path) is None
```

Also verify output directory is not created, or no files are created.

### 19.7 Env helper attaches export result

Create env with:

```python
env.explicit_bridge_capacity_issue_candidates = bundle
```

Call helper.

Verify:

```text
env.explicit_bridge_capacity_issue_candidate_export_result exists
```

### 19.8 Optional bundle JSON

Export with:

```python
write_bundle_json=True
```

Verify:

```text
issue_candidate_bundle.json exists
```

---

## 20. Existing Tests to Run

Run:

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

---

## 21. Recommended Implementation Scope

Recommended MVP implementation:

```text
pysi/reporting/explicit_pipeline_issue_candidate_exporter.py
tests/test_explicit_pipeline_issue_candidate_export.py
```

Optional package export:

```text
pysi/reporting/__init__.py
```

Do not modify:

```text
pysi/gui/*
planning sequence
run_full_plan
capacity report exporter
issue candidate builder
cost / KPI modules
```

---

## 22. Completion Criteria

This design is complete when it defines:

```text
[OK] exporter module location
[OK] export result dataclass
[OK] main export function
[OK] env export helper
[OK] output directory policy
[OK] output file names
[OK] CSV column policy
[OK] JSON policy
[OK] empty bundle behavior
[OK] no-bundle behavior
[OK] record counts
[OK] package export concept
[OK] test strategy
[OK] boundaries from cost / KPI / GUI / command execution
```

---

## 23. Relationship to Cost / KPI Enrichment

Issue candidate export should happen before cost / KPI enrichment.

Reason:

```text
Cost / KPI enrichment needs stable issue candidate records.
```

The future cost / KPI flow can be:

```text
issue candidate bundle
    ↓
issue candidate export
    ↓
cost / KPI enrichment
    ↓
management cockpit / GUI
```

Cost / KPI enrichment may later add fields such as:

```text
lost_sales_value
inventory_cost_impact
capacity_cost_impact
profit_impact
service_level_impact
ROI implication
```

---

## 24. Relationship to Knowledge Continuity Layer

The exported issue candidates can later feed WOM Knowledge Continuity Layer categories.

Possible mapping:

```text
health issues
    → facts / findings / open issues

management issues
    → decision log candidates / open issues

replan command candidates
    → next-entry prompts / action candidates
```

This should not be automated in this phase.

But issue candidate export creates the evidence needed for future knowledge preservation.

---

## 25. Summary

This design defines the file-export layer for Phase 4 issue candidates.

The target flow is:

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

The guiding principle remains:

```text
Export candidates.
Do not execute commands.
Do not calculate Cost / KPI yet.
Do not display GUI yet.
```

This creates the audit trail needed before Cost / KPI enrichment.
