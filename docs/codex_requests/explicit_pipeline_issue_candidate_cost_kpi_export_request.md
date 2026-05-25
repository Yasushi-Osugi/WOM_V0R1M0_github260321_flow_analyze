# Codex Request: Implement Explicit Pipeline Issue Candidate Cost / KPI Export MVP

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/explicit_pipeline_issue_candidate_cost_kpi_export.md
```

Please read this design memo first.

The current staged integration status is:

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
Cost / KPI export                        ← current request target
    ↓
GUI display
```

The current explicit pipeline explanation chain is:

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

This request should implement the next standalone export layer:

```text
ExplicitPipelineIssueCandidateKPIBundle
    ↓
export_explicit_pipeline_issue_candidate_kpi_bundle(...)
    ↓
CSV / JSON audit files
```

This request is only for the **Cost / KPI enriched issue candidate export MVP**.

---

## 2. Main Objective

Add a standalone exporter that converts:

```python
ExplicitPipelineIssueCandidateKPIBundle
```

into stable CSV / JSON files under:

```text
outputs/explicit_pipeline/issue_candidate_kpi/
```

The intended transformation is:

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

The exporter must not calculate Cost / KPI.

The exporter must not execute replan commands.

The exporter must not modify GUI or planning sequence.

---

## 3. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan / _run_planning_sequence.
3. Do not execute ReplanCommand.
4. Do not implement automatic replanning.
5. Do not implement Cost / KPI calculation in this exporter.
6. Do not modify Cost / KPI enrichment logic.
7. Do not implement OR optimization.
8. Do not implement database persistence.
9. Do not implement knowledge continuity persistence.
10. Keep this as standalone exporter + focused tests.
```

This request is only for:

```text
Explicit Pipeline Issue Candidate Cost / KPI Export MVP
```

---

## 4. Files to Add / Modify

Please add:

```text
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi_exporter.py
tests/test_explicit_pipeline_issue_candidate_cost_kpi_export.py
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
issue candidate builder logic
issue candidate exporter
Cost / KPI enrichment logic
capacity report exporter
optimization modules
database modules
```

---

## 5. Existing Components to Reuse

Reuse these from:

```text
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi.py
```

```python
ExplicitPipelineIssueCandidateKPIBundle
issue_candidate_kpi_bundle_to_dict(...)
issue_candidate_kpi_bundle_as_rows(...)
```

The exporter should not enrich or recalculate records.

It should only export an already-built KPI bundle.

---

## 6. Export Result Dataclass

Please implement:

```python
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExplicitPipelineIssueCandidateKPIExportResult:
    output_dir: Path
    files: dict[str, Path] = field(default_factory=dict)
    record_counts: dict[str, int] = field(default_factory=dict)
    summary_path: Path | None = None
    assumptions_path: Path | None = None
    message: str = ""
```

This mirrors the already-established exporter design pattern.

The result should be deterministic and easy to inspect in tests.

---

## 7. Main Export Function

Please implement:

```python
def export_explicit_pipeline_issue_candidate_kpi_bundle(
    bundle,
    *,
    output_dir: str | Path = "outputs/explicit_pipeline/issue_candidate_kpi",
    write_empty_files: bool = True,
    write_all_candidates: bool = True,
    write_bundle_json: bool = False,
) -> ExplicitPipelineIssueCandidateKPIExportResult:
    ...
```

Expected behavior:

```text
1. Ensure output_dir exists.
2. Write one CSV file per enriched candidate group.
3. Write summary.json.
4. Write assumptions.json.
5. Optionally write all_enriched_issue_candidates.csv.
6. Optionally write issue_candidate_kpi_bundle.json.
7. Return ExplicitPipelineIssueCandidateKPIExportResult.
```

---

## 8. Env Helper

Please implement:

```python
def maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env(
    env,
    *,
    output_dir: str | Path = "outputs/explicit_pipeline/issue_candidate_kpi",
    write_empty_files: bool = True,
    write_all_candidates: bool = True,
    write_bundle_json: bool = False,
):
    ...
```

Expected behavior:

```text
1. Read env.explicit_bridge_capacity_issue_candidate_kpi_bundle.
2. If missing, return None.
3. Export the KPI bundle.
4. Attach env.explicit_bridge_capacity_issue_candidate_kpi_export_result.
5. Return the export result.
```

The helper must not display anything in GUI.

The helper must not create files if no KPI bundle exists.

---

## 9. Output Directory

Default:

```text
outputs/explicit_pipeline/issue_candidate_kpi
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

### 10.1 Enriched planning issues

```text
enriched_planning_issues.csv
```

Source:

```python
bundle.enriched_planning_issue_candidates
```

### 10.2 Enriched management issues

```text
enriched_management_issues.csv
```

Source:

```python
bundle.enriched_management_issue_candidates
```

### 10.3 Enriched replan command candidates

```text
enriched_replan_command_candidates.csv
```

Source:

```python
bundle.enriched_replan_command_candidates
```

### 10.4 Enriched health issues

```text
enriched_health_issues.csv
```

Source:

```python
bundle.enriched_health_issue_candidates
```

### 10.5 Summary

```text
summary.json
```

Source:

```python
bundle.summary
```

### 10.6 Assumptions

```text
assumptions.json
```

Source:

```python
bundle.assumptions
```

### 10.7 Combined enriched candidates

```text
all_enriched_issue_candidates.csv
```

Source:

```python
issue_candidate_kpi_bundle_as_rows(bundle)
```

Only write this when:

```python
write_all_candidates=True
```

### 10.8 Full KPI bundle JSON

```text
issue_candidate_kpi_bundle.json
```

Source:

```python
issue_candidate_kpi_bundle_to_dict(bundle)
```

Only write this when:

```python
write_bundle_json=True
```

---

## 11. CSV Column Policy

Enriched candidate groups may contain different keys.

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

This should mirror the behavior already used in:

```text
pysi/reporting/explicit_pipeline_issue_candidate_exporter.py
pysi/reporting/explicit_pipeline_capacity_report_exporter.py
```

Do not require every row to contain every column.

---

## 12. Suggested Default Columns

### 12.1 enriched_planning_issues.csv

```text
candidate_type,issue_type,severity,product,node,week,capacity_type,lot_ids,impact_status,impact_category,impact_quantity,impact_quantity_basis,currency,estimated_lost_sales_value,estimated_margin_impact,estimated_inventory_cost_impact,estimated_capacity_cost_impact,estimated_service_penalty,estimated_total_business_impact,kpi_service_risk_score,kpi_inventory_risk_score,kpi_capacity_risk_score,kpi_data_quality_risk_score,cost_kpi_assumption_source,evidence_record_type,source,message,suggested_action
```

### 12.2 enriched_management_issues.csv

```text
candidate_type,issue_type,severity,product,node,week,capacity_type,lot_ids,business_theme,impact_status,impact_category,impact_quantity,impact_quantity_basis,currency,estimated_lost_sales_value,estimated_margin_impact,estimated_inventory_cost_impact,estimated_capacity_cost_impact,estimated_service_penalty,estimated_total_business_impact,kpi_service_risk_score,kpi_inventory_risk_score,kpi_capacity_risk_score,kpi_data_quality_risk_score,cost_kpi_assumption_source,evidence_record_type,source,message,suggested_decision
```

### 12.3 enriched_replan_command_candidates.csv

```text
candidate_type,command_type,status,product,node,week,capacity_type,lot_ids,impact_status,impact_category,impact_quantity,impact_quantity_basis,currency,estimated_total_business_impact,expected_benefit_category,source,message,suggested_action
```

### 12.4 enriched_health_issues.csv

```text
candidate_type,issue_type,severity,product,details,impact_status,impact_category,currency,kpi_data_quality_risk_score,estimated_total_business_impact,evidence_record_type,source,message
```

### 12.5 all_enriched_issue_candidates.csv

```text
candidate_type,issue_type,severity,product,node,week,capacity_type,lot_ids,impact_status,impact_category,currency,estimated_total_business_impact,source,message
```

The implementation may include additional columns if rows contain additional keys.

---

## 13. JSON Policy

Write `summary.json` with:

```python
json.dump(bundle.summary, f, ensure_ascii=False, indent=2, default=str)
```

Write `assumptions.json` with:

```python
json.dump(bundle.assumptions, f, ensure_ascii=False, indent=2, default=str)
```

If `write_bundle_json=True`, write `issue_candidate_kpi_bundle.json` with:

```python
json.dump(issue_candidate_kpi_bundle_to_dict(bundle), f, ensure_ascii=False, indent=2, default=str)
```

---

## 14. Empty KPI Bundle Behavior

If the KPI bundle exists but all enriched candidate lists are empty:

```text
summary.json should still be written
assumptions.json should still be written
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

## 15. No Bundle Behavior

If env has no:

```python
env.explicit_bridge_capacity_issue_candidate_kpi_bundle
```

then:

```python
maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env(env)
```

should return:

```python
None
```

and should not create files.

---

## 16. Record Counts

The export result should include stable record counts such as:

```python
{
    "enriched_planning_issues": len(bundle.enriched_planning_issue_candidates),
    "enriched_management_issues": len(bundle.enriched_management_issue_candidates),
    "enriched_replan_command_candidates": len(bundle.enriched_replan_command_candidates),
    "enriched_health_issues": len(bundle.enriched_health_issue_candidates),
    "all_enriched_issue_candidates": len(issue_candidate_kpi_bundle_as_rows(bundle)),
}
```

Use these stable keys.

---

## 17. Package Export

If updating `pysi/reporting/__init__.py`, export:

```python
ExplicitPipelineIssueCandidateKPIExportResult
export_explicit_pipeline_issue_candidate_kpi_bundle
maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env
```

Keep the update minimal.

---

## 18. Tests to Add

Please add:

```text
tests/test_explicit_pipeline_issue_candidate_cost_kpi_export.py
```

### 18.1 Export synthetic KPI bundle

Build an `ExplicitPipelineIssueCandidateKPIBundle` with:

```text
one enriched planning issue
one enriched management issue
one enriched replan command candidate
one enriched health issue
summary
assumptions
```

Export to `tmp_path`.

Verify files exist:

```text
enriched_planning_issues.csv
enriched_management_issues.csv
enriched_replan_command_candidates.csv
enriched_health_issues.csv
summary.json
assumptions.json
all_enriched_issue_candidates.csv
```

Verify export result fields:

```text
output_dir
files
record_counts
summary_path
assumptions_path
```

### 18.2 Verify summary.json

Read `summary.json`.

Verify:

```text
product
currency
estimated_total_business_impact
impact_values_are_directional
double_counting_possible
```

### 18.3 Verify assumptions.json

Read `assumptions.json`.

Verify:

```text
currency
unit_price_by_product
capacity_shortage_penalty_per_lot
```

### 18.4 Verify CSV content

Read at least:

```text
enriched_planning_issues.csv
enriched_management_issues.csv
enriched_replan_command_candidates.csv
all_enriched_issue_candidates.csv
```

Verify:

```text
header exists
expected row exists
lot_ids are JSON-encoded
estimated_total_business_impact exists
status=candidate_only is preserved for replan command candidates
```

### 18.5 Empty KPI bundle export

Export an empty `ExplicitPipelineIssueCandidateKPIBundle` with:

```python
write_empty_files=True
```

Verify:

```text
summary.json exists
assumptions.json exists
CSV files exist with headers
record counts are zero
```

### 18.6 write_empty_files=False

Export an empty KPI bundle with:

```python
write_empty_files=False
```

Verify:

```text
summary.json exists
assumptions.json exists
empty CSV files are skipped
```

### 18.7 Env helper no-op

Create env without KPI bundle.

Verify:

```python
maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env(env, output_dir=tmp_path) is None
```

Also verify output directory is not created, or no files are created.

### 18.8 Env helper attaches export result

Create env with:

```python
env.explicit_bridge_capacity_issue_candidate_kpi_bundle = bundle
```

Call helper.

Verify:

```text
env.explicit_bridge_capacity_issue_candidate_kpi_export_result exists
```

### 18.9 Optional bundle JSON

Export with:

```python
write_bundle_json=True
```

Verify:

```text
issue_candidate_kpi_bundle.json exists
```

---

## 19. Existing Tests to Run

Please run:

```bat
python -m pytest tests/test_explicit_pipeline_issue_candidate_cost_kpi_export.py
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
```

Optional:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

If optional tests are not run, state so clearly.

---

## 20. Completion Criteria

This request is complete when:

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
[OK] no GUI changes
[OK] no planning-sequence changes
[OK] no Cost / KPI calculation in exporter
[OK] no command execution
```

---

## 21. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. Exported files
4. CSV column / JSON encoding behavior
5. Empty KPI bundle behavior
6. Env helper behavior
7. Test commands executed
8. Test results
9. Limitations / follow-up
```

Please do not proceed into:

```text
automatic planning-sequence integration
GUI display
Cost / KPI recalculation
OR optimization
database persistence
ReplanCommand execution
Knowledge Continuity persistence
```

This request is only for:

```text
Explicit Pipeline Issue Candidate Cost / KPI Export MVP
```
