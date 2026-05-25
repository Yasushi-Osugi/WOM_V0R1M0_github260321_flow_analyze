# Explicit Pipeline Issue Candidate Export Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-23  
**Status:** Completion memo  
**Target path:** `docs/design/explicit_pipeline_issue_candidate_export_completion.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Explicit Pipeline Issue Candidate Export MVP**.

The purpose of this milestone was to add a standalone exporter that converts an in-memory issue candidate bundle into externally inspectable CSV / JSON files.

The completed transformation is:

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

This milestone creates the issue-level audit trail that sits after Phase 4 issue candidate generation and before Cost / KPI enrichment.

---

## 2. Background

Before this milestone, WOM had completed the following chain:

```text
execution result
    ↓
in-memory capacity report
    ↓
capacity report export
    ↓
issue candidate bundle
```

The missing piece was:

```text
issue candidate bundle
    ↓
issue candidate export
```

This milestone completes that missing export step.

The updated chain is now:

```text
execution result
    ↓
in-memory capacity report
    ↓
capacity report export
    ↓
issue candidate bundle
    ↓
issue candidate export
```

---

## 3. Implemented Files

This milestone added or updated:

```text
pysi/reporting/__init__.py
pysi/reporting/explicit_pipeline_issue_candidate_exporter.py
tests/test_explicit_pipeline_issue_candidate_export.py
```

The implementation was committed as:

```text
55040e2 Add explicit pipeline issue candidate exporter MVP
```

---

## 4. Implemented Exporter Module

The new exporter module is:

```text
pysi/reporting/explicit_pipeline_issue_candidate_exporter.py
```

This module provides a pure reporting/export layer for `ExplicitPipelineIssueCandidateBundle`.

It does not:

```text
modify GUI
modify run_full_plan
modify _run_planning_sequence
execute ReplanCommand
calculate cost / KPI
run optimization
persist to database
write knowledge continuity records
```

---

## 5. Implemented Export Result Dataclass

The implemented dataclass is:

```python
ExplicitPipelineIssueCandidateExportResult
```

It contains:

```text
output_dir
files
record_counts
summary_path
message
```

This mirrors the design pattern already used by the capacity report exporter.

---

## 6. Implemented Main Export Function

The implemented main export function is:

```python
export_explicit_pipeline_issue_candidates(...)
```

Supported parameters include:

```text
bundle
output_dir
write_empty_files
write_all_candidates
write_bundle_json
```

Default output directory:

```text
outputs/explicit_pipeline/issue_candidates
```

The exporter:

```text
1. ensures output_dir exists
2. writes per-candidate-group CSV files
3. writes summary.json
4. optionally writes all_issue_candidates.csv
5. optionally writes issue_candidate_bundle.json
6. returns ExplicitPipelineIssueCandidateExportResult
```

---

## 7. Implemented Env Helper

The implemented env helper is:

```python
maybe_export_explicit_pipeline_issue_candidates_from_env(...)
```

Behavior:

```text
1. Read env.explicit_bridge_capacity_issue_candidates.
2. If missing, return None.
3. Export the bundle.
4. Attach env.explicit_bridge_capacity_issue_candidate_export_result.
5. Return the export result.
```

If no issue candidate bundle exists, the helper is a no-op and does not create the output directory or files.

---

## 8. Exported Files

The exporter supports the following files.

### 8.1 Planning issues

```text
planning_issues.csv
```

Source:

```python
bundle.planning_issue_candidates
```

### 8.2 Management issues

```text
management_issues.csv
```

Source:

```python
bundle.management_issue_candidates
```

### 8.3 Replan command candidates

```text
replan_command_candidates.csv
```

Source:

```python
bundle.replan_command_candidates
```

### 8.4 Health issues

```text
health_issues.csv
```

Source:

```python
bundle.health_issue_candidates
```

### 8.5 Summary JSON

```text
summary.json
```

Source:

```python
bundle.summary
```

### 8.6 Optional combined issue candidates

```text
all_issue_candidates.csv
```

Source:

```python
issue_candidates_as_rows(bundle)
```

Written when:

```python
write_all_candidates=True
```

### 8.7 Optional full bundle JSON

```text
issue_candidate_bundle.json
```

Source:

```python
issue_candidates_to_dict(bundle)
```

Written when:

```python
write_bundle_json=True
```

---

## 9. CSV Behavior

The exporter implements deterministic CSV behavior:

```text
union + sorted columns when rows exist
default columns when rows are empty
header row written whenever a CSV file is written
list / dict values JSON-encoded
None or missing values emitted as empty string
```

This makes the output files usable both for human inspection and future downstream automation.

---

## 10. JSON Behavior

The exporter writes:

```text
summary.json
```

from:

```python
bundle.summary
```

When enabled, it also writes:

```text
issue_candidate_bundle.json
```

from:

```python
issue_candidates_to_dict(bundle)
```

The JSON output uses readable formatting and `default=str` for safer serialization.

---

## 11. Empty Bundle Behavior

The exporter supports two empty-bundle modes.

### 11.1 write_empty_files=True

When:

```python
write_empty_files=True
```

the exporter writes CSV files with headers even if there are no candidate rows.

This gives stable filenames for automation and later GUI integration.

### 11.2 write_empty_files=False

When:

```python
write_empty_files=False
```

empty CSV files are skipped.

In both cases:

```text
summary.json is still written when export is invoked
```

---

## 12. Package Export

The reporting package export was updated in:

```text
pysi/reporting/__init__.py
```

The following APIs were exported:

```text
ExplicitPipelineIssueCandidateExportResult
export_explicit_pipeline_issue_candidates
maybe_export_explicit_pipeline_issue_candidates_from_env
```

---

## 13. Tests Added

The focused test file is:

```text
tests/test_explicit_pipeline_issue_candidate_export.py
```

It validates:

```text
1. synthetic candidate bundle export
2. summary.json content
3. CSV content and JSON-encoded lot_ids
4. preservation of status=candidate_only for replan command candidates
5. empty bundle export with write_empty_files=True
6. empty bundle export with write_empty_files=False
7. env helper no-op behavior
8. env helper export-result attachment
9. optional issue_candidate_bundle.json output
```

---

## 14. Validation

The focused issue candidate export test passed:

```bat
python -m pytest tests/test_explicit_pipeline_issue_candidate_export.py
```

Observed result:

```text
8 passed
```

The broader regression set also passed:

```bat
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
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results:

```text
tests/test_explicit_pipeline_issue_candidates.py: 7 passed
tests/test_explicit_pipeline_capacity_report_export.py: 8 passed
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
[OK] broader regression tests pass
[OK] no GUI changes
[OK] no planning-sequence changes
[OK] no cost / KPI calculation
[OK] no command execution
```

---

## 16. Meaning of This Milestone

Before this milestone:

```text
WOM could generate issue candidates in memory.
```

After this milestone:

```text
WOM can export issue candidates as CSV / JSON audit files.
```

This moves WOM one step closer to cost / KPI enrichment because the candidate records can now be externally inspected and validated before business values are attached.

The completed chain is:

```text
execution result
    ↓
in-memory capacity report
    ↓
capacity report export
    ↓
issue candidate bundle
    ↓
issue candidate export
```

---

## 17. Current Pipeline Position

The staged integration now stands here:

```text
isolated utilities
    ↓
explicit pipeline runner                 ✅ Phase 1 completed
    ↓
feature flag helper                      ✅ Phase 2a completed
    ↓
run_full_plan insertion                  ✅ Phase 2b completed
    ↓
capacity reporting MVP                   ✅ Phase 3a completed
    ↓
capacity report attachment               ✅ Phase 3b completed
    ↓
capacity report export                   ✅ Phase 3c completed
    ↓
issue candidates                         ✅ Phase 4 completed
    ↓
issue candidate export                   ✅ completed
    ↓
cost/KPI
    ↓
GUI display
```

---

## 18. Known Limitations

This milestone is intentionally limited.

It does not implement:

```text
automatic planning-sequence export
GUI display
cost / KPI enrichment
OR optimization
database persistence
ReplanCommand execution
Knowledge Continuity persistence
```

The exporter is standalone and callable from tests or future integration points.

Automatic export from the planning sequence should remain feature-controlled because file output is side-effectful.

---

## 19. Future Milestones

### 19.1 Cost / KPI enrichment

The next major design theme is:

```text
Cost / KPI enrichment of issue candidates
```

Potential design memo:

```text
docs/design/explicit_pipeline_issue_candidate_cost_kpi_enrichment.md
```

Goal:

```text
Attach business impact values to issue candidates.
```

Possible fields:

```text
lost_sales_value
inventory_cost_impact
capacity_cost_impact
profit_impact
service_level_impact
ROI implication
```

### 19.2 Planning-sequence attachment / export control

A later phase may attach issue candidate generation and export to the planning sequence with feature flags.

Potential flags:

```python
env.enable_explicit_bridge_capacity_issue_candidates
env.enable_explicit_bridge_capacity_issue_candidate_export
```

### 19.3 GUI display

GUI display should wait until the issue candidate schema and Cost / KPI enrichment approach are stable.

### 19.4 Knowledge Continuity integration

Exported issue candidates can later become inputs to WOM Knowledge Continuity Layer categories:

```text
open issues
facts and findings
decision log candidates
next-entry prompts
```

This should not be automated until the knowledge lifecycle rules are stable.

---

## 20. Summary

The Explicit Pipeline Issue Candidate Export MVP is complete.

The key achievement is:

```text
ExplicitPipelineIssueCandidateBundle can now be exported as stable CSV / JSON audit files.
```

The completed transformation is:

```text
ExplicitPipelineIssueCandidateBundle
    ↓
ExplicitPipelineIssueCandidateExportResult
    ↓
planning_issues.csv
management_issues.csv
replan_command_candidates.csv
health_issues.csv
all_issue_candidates.csv
summary.json
```

This creates the final audit layer before Cost / KPI enrichment.

The system remains safely human-in-the-loop:

```text
issue candidates are exported
replan command candidates remain candidate_only
commands are not executed
management decisions are not automated
```
