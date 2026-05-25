# Explicit Pipeline Issue Candidate Cost / KPI Export Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-24  
**Status:** Design memo  
**Target path:** `docs/design/explicit_pipeline_issue_candidate_cost_kpi_export.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/explicit_pipeline_phase1_to_phase4_overview.md`
- `docs/design/explicit_pipeline_issue_candidate_cost_kpi_enrichment.md`
- `docs/design/explicit_pipeline_issue_candidate_cost_kpi_enrichment_completion.md`
- `docs/design/explicit_pipeline_issue_candidate_export.md`
- `docs/design/explicit_pipeline_issue_candidate_export_completion.md`
- `docs/design/explicit_pipeline_management_issue_candidates.md`
- `docs/design/explicit_pipeline_management_issue_candidates_completion.md`
- `docs/design/wom_knowledge_continuity_layer.md`

---

## 1. Purpose

This memo defines the design for **Explicit Pipeline Issue Candidate Cost / KPI Export**.

The current explicit pipeline can already produce an in-memory Cost / KPI enriched issue candidate bundle:

```text
ExplicitPipelineIssueCandidateBundle
    ↓
enrich_explicit_pipeline_issue_candidates_with_cost_kpi(...)
    ↓
ExplicitPipelineIssueCandidateKPIBundle
```

This design defines the next step:

```text
ExplicitPipelineIssueCandidateKPIBundle
    ↓
Cost / KPI export
    ↓
CSV / JSON audit files
```

The purpose is to make the Cost / KPI enriched issue candidates externally inspectable before moving into:

```text
planning-sequence attachment
GUI display
management cockpit integration
knowledge continuity integration
```

This phase is the **business-impact audit trail**.

---

## 2. Current Completed State

The staged integration currently stands here:

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
Cost / KPI export                        ← next target
    ↓
GUI display
```

The current in-memory object is:

```python
ExplicitPipelineIssueCandidateKPIBundle
```

It contains:

```text
enriched_planning_issue_candidates
enriched_management_issue_candidates
enriched_replan_command_candidates
enriched_health_issue_candidates
summary
assumptions
message
```

---

## 3. Design Goal

The goal is deliberately small:

```text
Export ExplicitPipelineIssueCandidateKPIBundle into stable CSV / JSON files.
```

Recommended output files:

```text
outputs/explicit_pipeline/issue_candidate_kpi/enriched_planning_issues.csv
outputs/explicit_pipeline/issue_candidate_kpi/enriched_management_issues.csv
outputs/explicit_pipeline/issue_candidate_kpi/enriched_replan_command_candidates.csv
outputs/explicit_pipeline/issue_candidate_kpi/enriched_health_issues.csv
outputs/explicit_pipeline/issue_candidate_kpi/all_enriched_issue_candidates.csv
outputs/explicit_pipeline/issue_candidate_kpi/summary.json
outputs/explicit_pipeline/issue_candidate_kpi/assumptions.json
```

Optional output:

```text
outputs/explicit_pipeline/issue_candidate_kpi/issue_candidate_kpi_bundle.json
```

This phase should not perform Cost / KPI calculation.

It exports the already-enriched records.

---

## 4. Non-Goals

This phase must not implement:

```text
Cost / KPI calculation
automatic replanning
ReplanCommand execution
GUI display
OR optimization
database persistence
formal accounting export
ERP integration
approval workflow
knowledge continuity persistence
```

This phase is only:

```text
export enriched issue candidate bundle to files
```

---

## 5. Primary Input

Primary input:

```python
ExplicitPipelineIssueCandidateKPIBundle
```

Likely source:

```python
env.explicit_bridge_capacity_issue_candidate_kpi_bundle
```

The bundle is produced by:

```python
enrich_explicit_pipeline_issue_candidates_with_cost_kpi(...)
maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env(...)
```

from:

```text
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi.py
```

---

## 6. Recommended Module

Suggested file:

```text
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi_exporter.py
```

Reason:

```text
The object being exported is a reporting / management-support artifact.
Exporting belongs to reporting, not planning engines.
```

This mirrors the already completed exporter modules:

```text
pysi/reporting/explicit_pipeline_capacity_report_exporter.py
pysi/reporting/explicit_pipeline_issue_candidate_exporter.py
```

---

## 7. Recommended Test File

Suggested test:

```text
tests/test_explicit_pipeline_issue_candidate_cost_kpi_export.py
```

The test should use synthetic `ExplicitPipelineIssueCandidateKPIBundle` objects.

It may also use the existing enrichment function to create a realistic KPI bundle from a synthetic issue candidate bundle.

---

## 8. Export Result Dataclass

Recommended dataclass:

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

This follows the existing export result pattern.

---

## 9. Main Export Function

Recommended function:

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
2. Write one CSV per enriched candidate group.
3. Write summary.json.
4. Write assumptions.json.
5. Optionally write all_enriched_issue_candidates.csv.
6. Optionally write issue_candidate_kpi_bundle.json.
7. Return ExplicitPipelineIssueCandidateKPIExportResult.
```

---

## 10. Env Helper

Recommended helper:

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

This helper should not display anything in GUI.

This helper should not create files if no KPI bundle exists.

---

## 11. Output Directory Policy

Default output directory:

```text
outputs/explicit_pipeline/issue_candidate_kpi
```

Rationale:

```text
Cost / KPI enriched issue candidates should be separated from raw issue candidate exports.
```

Current related output directories:

```text
outputs/explicit_pipeline
outputs/explicit_pipeline/issue_candidates
outputs/explicit_pipeline/issue_candidate_kpi
```

This keeps the audit trail layered and readable.

---

## 12. Output File Policy

### 12.1 Enriched planning issues

```text
enriched_planning_issues.csv
```

Source:

```python
bundle.enriched_planning_issue_candidates
```

### 12.2 Enriched management issues

```text
enriched_management_issues.csv
```

Source:

```python
bundle.enriched_management_issue_candidates
```

### 12.3 Enriched replan command candidates

```text
enriched_replan_command_candidates.csv
```

Source:

```python
bundle.enriched_replan_command_candidates
```

### 12.4 Enriched health issues

```text
enriched_health_issues.csv
```

Source:

```python
bundle.enriched_health_issue_candidates
```

### 12.5 Summary

```text
summary.json
```

Source:

```python
bundle.summary
```

### 12.6 Assumptions

```text
assumptions.json
```

Source:

```python
bundle.assumptions
```

### 12.7 Combined enriched candidates

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

### 12.8 Full KPI bundle JSON

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

## 13. CSV Column Policy

Enriched candidate groups may contain different keys.

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

The column policy should mirror:

```text
explicit_pipeline_issue_candidate_exporter.py
```

---

## 14. Suggested Default Columns

### 14.1 enriched_planning_issues.csv

```text
candidate_type,issue_type,severity,product,node,week,capacity_type,lot_ids,impact_status,impact_category,impact_quantity,impact_quantity_basis,currency,estimated_lost_sales_value,estimated_margin_impact,estimated_inventory_cost_impact,estimated_capacity_cost_impact,estimated_service_penalty,estimated_total_business_impact,kpi_service_risk_score,kpi_inventory_risk_score,kpi_capacity_risk_score,kpi_data_quality_risk_score,cost_kpi_assumption_source,evidence_record_type,source,message,suggested_action
```

### 14.2 enriched_management_issues.csv

```text
candidate_type,issue_type,severity,product,node,week,capacity_type,lot_ids,business_theme,impact_status,impact_category,impact_quantity,impact_quantity_basis,currency,estimated_lost_sales_value,estimated_margin_impact,estimated_inventory_cost_impact,estimated_capacity_cost_impact,estimated_service_penalty,estimated_total_business_impact,kpi_service_risk_score,kpi_inventory_risk_score,kpi_capacity_risk_score,kpi_data_quality_risk_score,cost_kpi_assumption_source,evidence_record_type,source,message,suggested_decision
```

### 14.3 enriched_replan_command_candidates.csv

```text
candidate_type,command_type,status,product,node,week,capacity_type,lot_ids,impact_status,impact_category,impact_quantity,impact_quantity_basis,currency,estimated_total_business_impact,expected_benefit_category,source,message,suggested_action
```

### 14.4 enriched_health_issues.csv

```text
candidate_type,issue_type,severity,product,details,impact_status,impact_category,currency,kpi_data_quality_risk_score,estimated_total_business_impact,evidence_record_type,source,message
```

### 14.5 all_enriched_issue_candidates.csv

```text
candidate_type,issue_type,severity,product,node,week,capacity_type,lot_ids,impact_status,impact_category,currency,estimated_total_business_impact,source,message
```

The implementation may include additional columns if rows contain additional keys.

---

## 15. JSON Policy

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

## 16. Empty Bundle Behavior

If the KPI bundle exists but all enriched candidate lists are empty:

```text
summary.json should still be written
assumptions.json should still be written
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

## 17. No Bundle Behavior

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

This preserves feature-flag-off and non-integrated behavior.

---

## 18. Record Counts

The export result should include stable record counts:

```python
{
    "enriched_planning_issues": len(bundle.enriched_planning_issue_candidates),
    "enriched_management_issues": len(bundle.enriched_management_issue_candidates),
    "enriched_replan_command_candidates": len(bundle.enriched_replan_command_candidates),
    "enriched_health_issues": len(bundle.enriched_health_issue_candidates),
    "all_enriched_issue_candidates": len(issue_candidate_kpi_bundle_as_rows(bundle)),
}
```

---

## 19. Package Export

If updating `pysi/reporting/__init__.py`, export:

```python
ExplicitPipelineIssueCandidateKPIExportResult
export_explicit_pipeline_issue_candidate_kpi_bundle
maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env
```

Keep the update minimal.

---

## 20. Tests to Add

Please add:

```text
tests/test_explicit_pipeline_issue_candidate_cost_kpi_export.py
```

### 20.1 Export synthetic KPI bundle

Create an `ExplicitPipelineIssueCandidateKPIBundle` with:

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

### 20.2 Verify summary.json

Read `summary.json`.

Verify:

```text
product
currency
estimated_total_business_impact
impact_values_are_directional
double_counting_possible
```

### 20.3 Verify assumptions.json

Read `assumptions.json`.

Verify:

```text
currency
unit_price_by_product
capacity_shortage_penalty_per_lot
```

### 20.4 Verify CSV content

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

### 20.5 Empty KPI bundle export

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

### 20.6 write_empty_files=False

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

### 20.7 Env helper no-op

Create env without KPI bundle.

Verify:

```python
maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env(env, output_dir=tmp_path) is None
```

Also verify output directory is not created, or no files are created.

### 20.8 Env helper attaches export result

Create env with:

```python
env.explicit_bridge_capacity_issue_candidate_kpi_bundle = bundle
```

Call helper.

Verify:

```text
env.explicit_bridge_capacity_issue_candidate_kpi_export_result exists
```

### 20.9 Optional bundle JSON

Export with:

```python
write_bundle_json=True
```

Verify:

```text
issue_candidate_kpi_bundle.json exists
```

---

## 21. Existing Tests to Run

Run:

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

---

## 22. Recommended Implementation Scope

Recommended MVP implementation:

```text
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi_exporter.py
tests/test_explicit_pipeline_issue_candidate_cost_kpi_export.py
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
issue candidate builder
issue candidate exporter
Cost / KPI enrichment logic
capacity report exporter
```

---

## 23. Completion Criteria

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
[OK] empty KPI bundle behavior
[OK] no-bundle behavior
[OK] record counts
[OK] package export concept
[OK] test strategy
[OK] boundaries from Cost / KPI calculation / GUI / command execution
```

---

## 24. Relationship to GUI

GUI should not be modified in this phase.

Future GUI display may consume either:

```text
env.explicit_bridge_capacity_issue_candidate_kpi_bundle
```

or exported files:

```text
outputs/explicit_pipeline/issue_candidate_kpi/*.csv
```

GUI display should wait until:

```text
KPI enrichment schema
KPI export behavior
filtering / sorting requirements
```

are stable.

---

## 25. Relationship to Management Cockpit

The enriched issue export can support a future Management Cockpit view.

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

This phase only prepares the export layer.

It does not implement the cockpit UI.

---

## 26. Relationship to WOM Knowledge Continuity Layer

The enriched issue export can later feed WOM Knowledge Continuity Layer categories.

Possible mapping:

```text
high impact management issues
    → open issues / decision log candidates

recurring capacity bottlenecks
    → business rules / scenario patterns

data quality risk
    → facts and findings / open issues

high value replan candidates
    → next-entry prompts
```

This phase should not automate that flow.

It only creates the structured evidence needed for future knowledge preservation.

---

## 27. Summary

This design defines the file-export layer for Cost / KPI enriched issue candidates.

The target flow is:

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

The guiding principle remains:

```text
Export enriched candidates.
Do not recalculate Cost / KPI here.
Do not execute commands.
Do not display GUI yet.
```

This creates the audit trail needed before Management Cockpit / GUI integration.
