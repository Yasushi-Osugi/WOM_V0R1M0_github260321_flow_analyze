# Explicit Pipeline Issue Candidate Cost / KPI Enrichment Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-24  
**Status:** Completion memo  
**Target path:** `docs/design/explicit_pipeline_issue_candidate_cost_kpi_enrichment_completion.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Explicit Pipeline Issue Candidate Cost / KPI Enrichment MVP**.

The purpose of this milestone was to add an in-memory enrichment layer that attaches directional Cost / KPI impact fields to existing explicit pipeline issue candidates.

The completed transformation is:

```text
ExplicitPipelineIssueCandidateBundle
    ↓
enrich_explicit_pipeline_issue_candidates_with_cost_kpi(...)
    ↓
ExplicitPipelineIssueCandidateKPIBundle
```

This milestone moves WOM from:

```text
This issue exists.
```

toward:

```text
This issue exists, and this is its estimated business impact.
```

The implementation is intentionally directional and scenario-level.

It is not intended to be formal accounting, ERP-grade costing, or statutory financial calculation.

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
```

The missing layer was:

```text
issue candidate bundle
    ↓
Cost / KPI enrichment
```

This milestone completes that in-memory enrichment step.

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
```

---

## 3. Implemented Files

This milestone added or updated:

```text
pysi/reporting/__init__.py
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi.py
tests/test_explicit_pipeline_issue_candidate_cost_kpi.py
```

The implementation was committed as:

```text
26b4a5e Add explicit pipeline issue candidate cost KPI enrichment MVP
```

---

## 4. Implemented Enrichment Module

The new module is:

```text
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi.py
```

This module provides a pure in-memory Cost / KPI enrichment layer.

It does not:

```text
modify GUI
modify run_full_plan
modify _run_planning_sequence
execute ReplanCommand
perform automatic replanning
run OR optimization
persist to database
export enriched KPI files
perform formal accounting
```

---

## 5. Implemented KPI Bundle Dataclass

The implemented dataclass is:

```python
ExplicitPipelineIssueCandidateKPIBundle
```

It contains:

```text
product_name
enriched_planning_issue_candidates
enriched_management_issue_candidates
enriched_replan_command_candidates
enriched_health_issue_candidates
summary
assumptions
message
```

The enriched records remain dictionary-based in this MVP.

This keeps the structure flexible while the Cost / KPI taxonomy is still stabilizing.

---

## 6. Implemented Main Enrichment Function

The implemented main function is:

```python
enrich_explicit_pipeline_issue_candidates_with_cost_kpi(...)
```

It consumes an `ExplicitPipelineIssueCandidateBundle`-like object and returns:

```python
ExplicitPipelineIssueCandidateKPIBundle
```

The function:

```text
1. reads existing issue candidates
2. copies each candidate record
3. preserves original fields such as product, node, week, capacity_type, issue_type, severity, lot_ids
4. adds deterministic Cost / KPI fields
5. preserves status=candidate_only on replan command candidates
6. handles missing assumptions without error
7. builds summary totals
```

---

## 7. Implemented Env Helper

The implemented env helper is:

```python
maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env(...)
```

Behavior:

```text
1. Read env.explicit_bridge_capacity_issue_candidates.
2. If missing, return None.
3. Enrich the issue candidate bundle.
4. Attach env.explicit_bridge_capacity_issue_candidate_kpi_bundle.
5. Return the enriched KPI bundle.
```

No GUI display, file export, or command execution is performed.

---

## 8. Implemented Cost / KPI Context Behavior

The enrichment function accepts an optional dictionary:

```python
cost_kpi_context
```

Example supported fields include:

```text
currency
unit_price_by_product
unit_margin_by_product
unit_cost_by_product
inventory_holding_cost_per_lot_per_week
capacity_overtime_cost_per_lot
capacity_shortage_penalty_per_lot
service_penalty_per_lot
```

The implementation treats missing maps safely as empty maps.

If assumptions are missing:

```text
monetary fields default to 0.0
impact_status becomes not_estimated or qualitative_only
no exception is raised
```

The context is attached to the returned KPI bundle as:

```text
assumptions
```

for traceability.

---

## 9. Lot Quantity Rule

The MVP uses the following lot quantity rule:

```text
one Lot_ID = one planning lot unit
```

Therefore:

```text
impact_quantity = len(lot_ids)
impact_quantity_basis = lot_count
```

If a record has an explicit numeric quantity field such as:

```text
quantity
lot_qty
qty
```

the implementation can use that quantity as the basis.

Lot_ID identity is preserved in enriched records.

---

## 10. Implemented Common Enriched Fields

Each enriched candidate preserves original fields and adds Cost / KPI fields such as:

```text
impact_status
impact_category
impact_quantity
impact_quantity_basis
currency
estimated_lost_sales_value
estimated_margin_impact
estimated_inventory_cost_impact
estimated_capacity_cost_impact
estimated_service_penalty
estimated_total_business_impact
kpi_service_risk_score
kpi_inventory_risk_score
kpi_capacity_risk_score
kpi_data_quality_risk_score
cost_kpi_assumption_source
```

The per-record total is calculated as:

```text
estimated_total_business_impact =
    estimated_lost_sales_value
  + estimated_margin_impact
  + estimated_inventory_cost_impact
  + estimated_capacity_cost_impact
  + estimated_service_penalty
```

---

## 11. Implemented Impact Categories

The MVP supports impact categories such as:

```text
service_risk
inventory_risk
capacity_risk
data_quality_risk
replan_option
no_direct_cost_estimate
```

Representative mappings:

```text
blocked_lot              → service_risk
backlog_lot              → service_risk
overflow_inventory       → inventory_risk
capacity_violation       → capacity_risk
missing_lot              → data_quality_risk
non_string_lot_error     → data_quality_risk
replan_command_candidate → replan_option
shifted_lot              → no_direct_cost_estimate
```

---

## 12. Planning Issue Enrichment

Planning issue candidates are enriched according to deterministic rules.

### 12.1 capacity_violation

```text
impact_category = capacity_risk
kpi_capacity_risk_score = high
estimated_capacity_cost_impact =
    lot_count × capacity_shortage_penalty_per_lot[capacity_type]
```

### 12.2 blocked_lot

```text
impact_category = service_risk
kpi_service_risk_score = high
estimated_lost_sales_value =
    lot_count × unit_price_by_product[product]
estimated_margin_impact =
    lot_count × unit_margin_by_product[product]
estimated_service_penalty =
    lot_count × service_penalty_per_lot[product]
```

### 12.3 backlog_lot

```text
impact_category = service_risk
kpi_service_risk_score = high
estimated_service_penalty =
    lot_count × service_penalty_per_lot[product]
```

Lost sales is not assumed by default for backlog, because backlog may still be fulfilled later.

### 12.4 overflow_inventory

```text
impact_category = inventory_risk
kpi_inventory_risk_score = high
estimated_inventory_cost_impact =
    lot_count × inventory_holding_cost_per_lot_per_week[product]
```

### 12.5 missing_lot

```text
impact_category = data_quality_risk
impact_status = qualitative_only
kpi_data_quality_risk_score = high
```

### 12.6 shifted_lot

```text
impact_category = no_direct_cost_estimate
impact_status = not_estimated
```

The MVP does not guess shifted duration.

---

## 13. Management Issue Enrichment

Management issue candidates are enriched with management-level impact categories and risk scores.

Implemented examples include:

```text
capacity_bottleneck             → capacity_risk
shipment_capacity_constraint    → capacity_risk
service_risk                    → service_risk
inventory_overflow_risk         → inventory_risk
planning_data_quality_risk      → data_quality_risk
```

Where assumptions are available, the implementation attaches directional monetary impact.

Where assumptions are missing, it preserves the candidate and marks it as non-estimated or qualitative.

---

## 14. Replan Command Candidate Enrichment

Replan command candidates remain:

```text
status = candidate_only
```

They are enriched as:

```text
impact_category = replan_option
impact_status = qualitative_only
estimated_total_business_impact = 0.0
```

The MVP may add an `expected_benefit_category`, such as:

```text
reduce_capacity_risk
reduce_service_risk
reduce_inventory_risk
review_required
```

No command is executed.

---

## 15. Health Issue Enrichment

Health issues represent structural data / PSI risks.

They are enriched as:

```text
impact_category = data_quality_risk
impact_status = qualitative_only
kpi_data_quality_risk_score = high
estimated_total_business_impact = 0.0
```

The MVP does not estimate monetary impact for health issues by default.

---

## 16. Implemented Summary

The enriched KPI bundle summary includes:

```text
product
currency
planning_issue_candidate_count
management_issue_candidate_count
replan_command_candidate_count
health_issue_candidate_count
estimated_lost_sales_value_total
estimated_margin_impact_total
estimated_inventory_cost_impact_total
estimated_capacity_cost_impact_total
estimated_service_penalty_total
estimated_total_business_impact
service_risk_issue_count
inventory_risk_issue_count
capacity_risk_issue_count
data_quality_risk_issue_count
impact_values_are_directional
double_counting_possible
```

The summary totals are deterministic sums over enriched rows.

Important flags:

```text
impact_values_are_directional = True
double_counting_possible = True
```

These flags are important because the MVP can include conceptual overlap between lost sales and margin impact.

---

## 17. Implemented Serialization Helpers

The following helpers were implemented:

```python
issue_candidate_kpi_bundle_to_dict(...)
issue_candidate_kpi_bundle_as_rows(...)
```

Row order is:

```text
enriched_planning_issue_candidates
enriched_management_issue_candidates
enriched_replan_command_candidates
enriched_health_issue_candidates
```

---

## 18. Package Export

The reporting package export was updated in:

```text
pysi/reporting/__init__.py
```

The following APIs were exported:

```text
ExplicitPipelineIssueCandidateKPIBundle
enrich_explicit_pipeline_issue_candidates_with_cost_kpi
maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env
issue_candidate_kpi_bundle_to_dict
issue_candidate_kpi_bundle_as_rows
```

---

## 19. Tests Added

The focused test file is:

```text
tests/test_explicit_pipeline_issue_candidate_cost_kpi.py
```

It validates:

```text
1. enrichment with assumptions
2. summary totals
3. missing assumption behavior
4. Lot_ID preservation
5. replan candidate remains candidate_only
6. env helper no-op behavior
7. env helper attachment behavior
8. serialization helper outputs
```

---

## 20. Validation

The focused Cost / KPI enrichment test passed:

```bat
python -m pytest tests/test_explicit_pipeline_issue_candidate_cost_kpi.py
```

Observed result:

```text
4 passed
```

The broader regression set also passed:

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
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results:

```text
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

## 21. Completion Criteria

This milestone satisfies the intended completion criteria.

```text
[OK] pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi.py exists
[OK] ExplicitPipelineIssueCandidateKPIBundle exists
[OK] enrich_explicit_pipeline_issue_candidates_with_cost_kpi(...) exists
[OK] maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env(...) exists
[OK] planning issue candidates are enriched
[OK] management issue candidates are enriched
[OK] replan command candidates are enriched without execution
[OK] health issue candidates are enriched
[OK] Lot_ID identity is preserved
[OK] impact status is handled when assumptions are missing
[OK] summary totals are generated
[OK] serialization helpers exist
[OK] env helper exists
[OK] focused tests pass
[OK] broader regression tests pass
[OK] no GUI changes
[OK] no planning-sequence changes
[OK] no formal accounting implementation
[OK] no command execution
```

---

## 22. Meaning of This Milestone

Before this milestone:

```text
WOM could generate and export issue candidates.
```

After this milestone:

```text
WOM can attach directional Cost / KPI impact values to issue candidates.
```

This is a major step toward management decision support.

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
    ↓
Cost / KPI enrichment
```

WOM can now begin to answer:

```text
What happened?
Where did it happen?
Which lots were involved?
What issue candidate was generated?
What is the directional business impact?
```

---

## 23. Current Pipeline Position

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
GUI display
```

---

## 24. Known Limitations

This milestone is intentionally limited.

It does not implement:

```text
enriched issue export
automatic planning-sequence integration
GUI display
formal accounting
OR optimization
database persistence
ReplanCommand execution
Knowledge Continuity persistence
```

The estimation is directional and may involve conceptual overlap or double counting.

The summary flags this explicitly:

```text
impact_values_are_directional = True
double_counting_possible = True
```

---

## 25. Future Milestones

### 25.1 Enriched issue export

A natural next step is exporting enriched issue candidates.

Potential design memo:

```text
docs/design/explicit_pipeline_issue_candidate_cost_kpi_export.md
```

Potential files:

```text
outputs/explicit_pipeline/issue_candidate_kpi/enriched_planning_issues.csv
outputs/explicit_pipeline/issue_candidate_kpi/enriched_management_issues.csv
outputs/explicit_pipeline/issue_candidate_kpi/enriched_replan_command_candidates.csv
outputs/explicit_pipeline/issue_candidate_kpi/enriched_health_issues.csv
outputs/explicit_pipeline/issue_candidate_kpi/summary.json
```

### 25.2 Planning-sequence attachment

A later phase may attach Cost / KPI enrichment after issue candidate generation.

Potential env attribute:

```text
env.explicit_bridge_capacity_issue_candidate_kpi_bundle
```

Potential feature flag:

```text
enable_explicit_bridge_capacity_issue_candidate_cost_kpi
```

### 25.3 GUI display

GUI display should wait until:

```text
issue candidate schema
Cost / KPI enrichment schema
export behavior
```

are stable.

### 25.4 WOM Knowledge Continuity integration

High-impact issue candidates may later be mapped into:

```text
open issues
facts and findings
decision log candidates
next-entry prompts
```

But this should remain controlled by explicit lifecycle rules.

---

## 26. Summary

The Explicit Pipeline Issue Candidate Cost / KPI Enrichment MVP is complete.

The key achievement is:

```text
ExplicitPipelineIssueCandidateBundle can now be enriched into ExplicitPipelineIssueCandidateKPIBundle.
```

The completed transformation is:

```text
ExplicitPipelineIssueCandidateBundle
    ↓
ExplicitPipelineIssueCandidateKPIBundle
    ↓
directional Cost / KPI fields
```

This gives WOM the first layer of business impact explanation for explicit pipeline issue candidates.

The system remains safely human-in-the-loop:

```text
impact values are directional
replan commands remain candidate_only
commands are not executed
management decisions are not automated
formal accounting is not implied
```
