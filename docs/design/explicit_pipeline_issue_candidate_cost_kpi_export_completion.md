# Explicit Pipeline Issue Candidate Cost / KPI Export Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-24  
**Status:** Completion memo  
**Target path:** `docs/design/explicit_pipeline_issue_candidate_cost_kpi_export_completion.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Explicit Pipeline Issue Candidate Cost / KPI Export MVP**.

The purpose of this milestone was to add a standalone exporter that converts an in-memory Cost / KPI enriched issue candidate bundle into externally inspectable CSV / JSON files.

The completed transformation is:

```text
ExplicitPipelineIssueCandidateKPIBundle
    ↓
export_explicit_pipeline_issue_candidate_kpi_bundle(...)
    ↓
enriched_planning_issues.csv
enriched_management_issues.csv
enriched_replan_command_candidates.csv
enriched_health_issues.csv
all_enriched_issue_candidates.csv
summary.json
assumptions.json
```

This milestone creates the business-impact audit trail that sits after Cost / KPI enrichment and before GUI / Management Cockpit integration.

---

## 2. Background

Before this milestone, WOM had completed the following explanatory pipeline:

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
    ↓
Cost / KPI enrichment
```

The missing layer was:

```text
Cost / KPI enriched issue candidate bundle
    ↓
Cost / KPI export
```

This milestone completes that export step.

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
    ↓
Cost / KPI enrichment
    ↓
Cost / KPI export
```

---

## 3. Implemented Files

This milestone added or updated:

```text
pysi/reporting/__init__.py
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi_exporter.py
tests/test_explicit_pipeline_issue_candidate_cost_kpi_export.py
```

The implementation was committed as:

```text
5b13af1 Add explicit pipeline issue candidate cost KPI exporter MVP
```

---

## 4. Implemented Exporter Module

The new exporter module is:

```text
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi_exporter.py
```

This module provides a pure reporting/export layer for:

```python
ExplicitPipelineIssueCandidateKPIBundle
```

It does not:

```text
modify GUI
modify run_full_plan
modify _run_planning_sequence
recalculate Cost / KPI values
modify Cost / KPI enrichment logic
execute ReplanCommand
perform automatic replanning
run OR optimization
persist to database
write knowledge continuity records
```

---

## 5. Implemented Export Result Dataclass

The implemented dataclass is:

```python
ExplicitPipelineIssueCandidateKPIExportResult
```

It contains:

```text
output_dir
files
record_counts
summary_path
assumptions_path
message
```

This follows the existing export result pattern used by:

```text
ExplicitPipelineCapacityReportExportResult
ExplicitPipelineIssueCandidateExportResult
```

---

## 6. Implemented Main Export Function

The implemented main export function is:

```python
export_explicit_pipeline_issue_candidate_kpi_bundle(...)
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
outputs/explicit_pipeline/issue_candidate_kpi
```

The exporter:

```text
1. ensures output_dir exists
2. writes per-enriched-candidate-group CSV files
3. writes summary.json
4. writes assumptions.json
5. optionally writes all_enriched_issue_candidates.csv
6. optionally writes issue_candidate_kpi_bundle.json
7. returns ExplicitPipelineIssueCandidateKPIExportResult
```

---

## 7. Implemented Env Helper

The implemented env helper is:

```python
maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env(...)
```

Behavior:

```text
1. Read env.explicit_bridge_capacity_issue_candidate_kpi_bundle.
2. If missing, return None.
3. Export the KPI bundle.
4. Attach env.explicit_bridge_capacity_issue_candidate_kpi_export_result.
5. Return the export result.
```

If no KPI bundle exists, the helper is a no-op and does not create output files.

---

## 8. Exported Files

The exporter supports the following files.

### 8.1 Enriched planning issues

```text
enriched_planning_issues.csv
```

Source:

```python
bundle.enriched_planning_issue_candidates
```

### 8.2 Enriched management issues

```text
enriched_management_issues.csv
```

Source:

```python
bundle.enriched_management_issue_candidates
```

### 8.3 Enriched replan command candidates

```text
enriched_replan_command_candidates.csv
```

Source:

```python
bundle.enriched_replan_command_candidates
```

### 8.4 Enriched health issues

```text
enriched_health_issues.csv
```

Source:

```python
bundle.enriched_health_issue_candidates
```

### 8.5 Summary JSON

```text
summary.json
```

Source:

```python
bundle.summary
```

### 8.6 Assumptions JSON

```text
assumptions.json
```

Source:

```python
bundle.assumptions
```

### 8.7 Optional combined enriched candidates

```text
all_enriched_issue_candidates.csv
```

Source:

```python
issue_candidate_kpi_bundle_as_rows(bundle)
```

Written when:

```python
write_all_candidates=True
```

### 8.8 Optional full KPI bundle JSON

```text
issue_candidate_kpi_bundle.json
```

Source:

```python
issue_candidate_kpi_bundle_to_dict(bundle)
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
Path values converted to string
None or missing values emitted as empty string
```

This keeps the output files:

```text
human-inspectable
testable
stable for downstream automation
```

---

## 10. JSON Behavior

The exporter writes:

```text
summary.json
assumptions.json
```

When enabled, it also writes:

```text
issue_candidate_kpi_bundle.json
```

The JSON output uses readable formatting and `default=str` for safer serialization.

---

## 11. Empty KPI Bundle Behavior

The exporter supports two empty-bundle modes.

### 11.1 write_empty_files=True

When:

```python
write_empty_files=True
```

the exporter writes CSV files with headers even if there are no enriched candidate rows.

This gives stable filenames for automation and future GUI integration.

### 11.2 write_empty_files=False

When:

```python
write_empty_files=False
```

empty CSV files are skipped.

In both cases:

```text
summary.json is written
assumptions.json is written
```

when export is invoked.

---

## 12. Record Counts

The export result includes stable record counts:

```text
enriched_planning_issues
enriched_management_issues
enriched_replan_command_candidates
enriched_health_issues
all_enriched_issue_candidates
```

These counts make export results easy to validate in tests and useful for later logging / cockpit integration.

---

## 13. Package Export

The reporting package export was updated in:

```text
pysi/reporting/__init__.py
```

The following APIs were exported:

```text
ExplicitPipelineIssueCandidateKPIExportResult
export_explicit_pipeline_issue_candidate_kpi_bundle
maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env
```

---

## 14. Tests Added

The focused test file is:

```text
tests/test_explicit_pipeline_issue_candidate_cost_kpi_export.py
```

It validates:

```text
1. synthetic KPI bundle export
2. summary.json content
3. assumptions.json content
4. CSV content and JSON-encoded lot_ids
5. preservation of status=candidate_only for replan command candidates
6. empty KPI bundle export with write_empty_files=True
7. empty KPI bundle export with write_empty_files=False
8. env helper no-op behavior
9. env helper export-result attachment
10. optional issue_candidate_kpi_bundle.json output
```

---

## 15. Validation

The focused Cost / KPI export test passed:

```bat
python -m pytest tests/test_explicit_pipeline_issue_candidate_cost_kpi_export.py
```

Observed result:

```text
7 passed
```

The broader regression set also passed:

```bat
python -m pytest tests/test_explicit_pipeline_issue_candidate_cost_kpi.py
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
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results:

```text
tests/test_explicit_pipeline_issue_candidate_cost_kpi.py: 4 passed
tests/test_explicit_pipeline_issue_candidate_export.py: 8 passed
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

## 16. Completion Criteria

This milestone satisfies the intended completion criteria.

```text
[OK] pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi_exporter.py exists
[OK] ExplicitPipelineIssueCandidateKPIExportResult exists
[OK] export_explicit_pipeline_issue_candidate_kpi_bundle(...) exists
[OK] maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env(...) exists
[OK] enriched_planning_issues.csv is written
[OK] enriched_management_issues.csv is written
[OK] enriched_replan_command_candidates.csv is written
[OK] enriched_health_issues.csv is written
[OK] summary.json is written
[OK] assumptions.json is written
[OK] all_enriched_issue_candidates.csv is written when enabled
[OK] issue_candidate_kpi_bundle.json is written when enabled
[OK] empty KPI bundle behavior is tested
[OK] env helper no-op is tested
[OK] env helper attaches export result
[OK] focused tests pass
[OK] broader regression tests pass
[OK] no GUI changes
[OK] no planning-sequence changes
[OK] no Cost / KPI calculation in exporter
[OK] no command execution
```

---

## 17. Meaning of This Milestone

Before this milestone:

```text
WOM could enrich issue candidates with directional Cost / KPI values in memory.
```

After this milestone:

```text
WOM can export Cost / KPI enriched issue candidates as CSV / JSON audit files.
```

This completes the current explicit pipeline explanation chain:

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
    ↓
Cost / KPI enrichment
    ↓
Cost / KPI export
```

WOM can now externally show:

```text
what happened
which capacity / lot issue was detected
which management issue candidate was generated
which Cost / KPI assumptions were used
what the directional business impact was
```

---

## 18. Current Pipeline Position

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
Cost / KPI enrichment                    ✅ completed
    ↓
Cost / KPI export                        ✅ completed
    ↓
GUI display
```

---

## 19. Known Limitations

This milestone is intentionally limited.

It does not implement:

```text
automatic planning-sequence integration
GUI display
Cost / KPI recalculation
formal accounting
OR optimization
database persistence
ReplanCommand execution
Knowledge Continuity persistence
```

The exporter simply writes the already-enriched bundle.

Any Cost / KPI caveats remain inherited from the enrichment layer:

```text
impact_values_are_directional = True
double_counting_possible = True
```

---

## 20. Future Milestones

### 20.1 Planning-sequence attachment

A later phase may attach Cost / KPI enrichment and export to the planning sequence behind explicit feature flags.

Potential feature flags:

```text
enable_explicit_bridge_capacity_issue_candidate_cost_kpi
enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export
```

### 20.2 GUI display / Management Cockpit integration

Future GUI display may use:

```text
env.explicit_bridge_capacity_issue_candidate_kpi_bundle
outputs/explicit_pipeline/issue_candidate_kpi/*.csv
```

Potential cockpit columns:

```text
severity
issue_type
impact_category
node
week
product
lot_ids
estimated_total_business_impact
suggested_action
suggested_decision
```

### 20.3 Knowledge Continuity integration

The exported enriched issue candidates can later feed WOM Knowledge Continuity Layer categories:

```text
open issues
facts and findings
decision log candidates
next-entry prompts
business rules / scenario patterns
```

This should remain controlled by explicit lifecycle rules.

### 20.4 Cost / KPI model refinement

Future refinements may include:

```text
avoiding double counting between sales and margin impact
using product-level lot quantity / unit conversion
supporting multiple currencies
connecting to Cost Master / scenario master
distinguishing lost sales from delayed backlog
estimating shifted-lot early-build carrying cost
```

---

## 21. Summary

The Explicit Pipeline Issue Candidate Cost / KPI Export MVP is complete.

The key achievement is:

```text
ExplicitPipelineIssueCandidateKPIBundle can now be exported as stable CSV / JSON audit files.
```

The completed transformation is:

```text
ExplicitPipelineIssueCandidateKPIBundle
    ↓
ExplicitPipelineIssueCandidateKPIExportResult
    ↓
enriched_planning_issues.csv
enriched_management_issues.csv
enriched_replan_command_candidates.csv
enriched_health_issues.csv
all_enriched_issue_candidates.csv
summary.json
assumptions.json
```

This creates the final audit layer before GUI / Management Cockpit integration.

The system remains safely human-in-the-loop:

```text
enriched issue candidates are exported
replan command candidates remain candidate_only
commands are not executed
management decisions are not automated
formal accounting is not implied
```
