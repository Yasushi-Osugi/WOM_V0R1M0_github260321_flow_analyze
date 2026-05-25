# Codex Request: Implement Explicit Pipeline Issue Candidate Cost / KPI Enrichment MVP

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/explicit_pipeline_issue_candidate_cost_kpi_enrichment.md
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
cost/KPI enrichment                      ← current request target
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
```

This request should implement the next in-memory layer:

```text
ExplicitPipelineIssueCandidateBundle
    ↓
Cost / KPI enrichment
    ↓
ExplicitPipelineIssueCandidateKPIBundle
```

This request is only for the **Cost / KPI enrichment MVP**.

---

## 2. Main Objective

Add a deterministic enrichment module that attaches directional Cost / KPI impact fields to an existing:

```python
ExplicitPipelineIssueCandidateBundle
```

The intended transformation is:

```text
ExplicitPipelineIssueCandidateBundle
    ↓
enrich_explicit_pipeline_issue_candidates_with_cost_kpi(...)
    ↓
ExplicitPipelineIssueCandidateKPIBundle
    ↓
enriched_planning_issue_candidates
enriched_management_issue_candidates
enriched_replan_command_candidates
enriched_health_issue_candidates
summary
```

The enrichment should support scenario-level management decision support.

It should not attempt formal accounting precision.

It should not execute replan commands.

---

## 3. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan / _run_planning_sequence.
3. Do not execute ReplanCommand.
4. Do not implement automatic replanning.
5. Do not implement OR optimization.
6. Do not implement database persistence.
7. Do not implement enriched issue export yet.
8. Do not implement formal product costing.
9. Keep this as additive in-memory enrichment + focused tests.
```

This request is only for:

```text
Explicit Pipeline Issue Candidate Cost / KPI Enrichment MVP
```

---

## 4. Files to Add / Modify

Please add:

```text
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi.py
tests/test_explicit_pipeline_issue_candidate_cost_kpi.py
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
capacity report exporter
optimization modules
database modules
```

---

## 5. Existing Components to Reuse

Reuse these from:

```text
pysi/reporting/explicit_pipeline_issue_candidates.py
```

```python
ExplicitPipelineIssueCandidateBundle
issue_candidates_as_rows(...)
issue_candidates_to_dict(...)
```

The enrichment module should not rebuild issue candidates.

It should consume an already-built issue candidate bundle.

It should preserve original candidate fields and add cost / KPI fields.

---

## 6. Enrichment Bundle Dataclass

Please implement:

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExplicitPipelineIssueCandidateKPIBundle:
    product_name: str = ""

    enriched_planning_issue_candidates: list[dict] = field(default_factory=list)
    enriched_management_issue_candidates: list[dict] = field(default_factory=list)
    enriched_replan_command_candidates: list[dict] = field(default_factory=list)
    enriched_health_issue_candidates: list[dict] = field(default_factory=list)

    summary: dict[str, Any] = field(default_factory=dict)
    assumptions: dict[str, Any] = field(default_factory=dict)
    message: str = ""
```

Keep enriched records as dictionaries for this MVP.

Typed dataclasses can be introduced later after the Cost / KPI taxonomy stabilizes.

---

## 7. Main Enrichment Function

Please implement:

```python
def enrich_explicit_pipeline_issue_candidates_with_cost_kpi(
    bundle,
    *,
    cost_kpi_context: dict | None = None,
) -> ExplicitPipelineIssueCandidateKPIBundle:
    ...
```

Expected behavior:

```text
1. Read ExplicitPipelineIssueCandidateBundle-like object.
2. Copy each original candidate record.
3. Add deterministic Cost / KPI fields.
4. Preserve product, node, week, capacity_type, issue_type, severity, lot_ids.
5. Preserve replan command status=candidate_only.
6. Build enriched summary totals.
7. Return ExplicitPipelineIssueCandidateKPIBundle.
```

The function should tolerate missing / empty cost assumptions.

When assumptions are missing, it should still produce enriched records with:

```text
impact_status = not_estimated
```

or:

```text
impact_status = qualitative_only
```

instead of raising an exception.

---

## 8. Env Helper

Please implement:

```python
def maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env(
    env,
    *,
    cost_kpi_context: dict | None = None,
):
    ...
```

Expected behavior:

```text
1. Read env.explicit_bridge_capacity_issue_candidates.
2. If missing, return None.
3. Enrich the issue candidate bundle.
4. Attach env.explicit_bridge_capacity_issue_candidate_kpi_bundle.
5. Return the enriched KPI bundle.
```

No GUI display.

No command execution.

No file export.

---

## 9. Cost / KPI Context Schema

Use a simple dictionary-based context for MVP.

Recommended example:

```python
cost_kpi_context = {
    "currency": "JPY",

    "unit_price_by_product": {
        "RICE": 1000.0,
    },
    "unit_margin_by_product": {
        "RICE": 250.0,
    },
    "unit_cost_by_product": {
        "RICE": 750.0,
    },

    "inventory_holding_cost_per_lot_per_week": {
        "RICE": 10.0,
    },
    "capacity_overtime_cost_per_lot": {
        "P": 50.0,
        "S": 30.0,
    },
    "capacity_shortage_penalty_per_lot": {
        "P": 100.0,
        "S": 80.0,
    },
    "service_penalty_per_lot": {
        "RICE": 200.0,
    },
}
```

The MVP should not require every field.

Missing assumptions should lead to zero monetary values plus a non-estimated status.

---

## 10. Lot Quantity Rule

Issue candidates currently preserve:

```text
lot_ids
```

but may not always preserve quantity.

MVP quantity rule:

```text
one Lot_ID = one planning lot unit
```

Therefore:

```python
lot_count = len(lot_ids)
```

If `lot_ids` is missing or empty:

```python
lot_count = 0
```

If a candidate already has:

```text
quantity
lot_qty
qty
```

then it is acceptable to use that value, but this is optional for MVP.

Each enriched record should include:

```text
impact_quantity
impact_quantity_basis
```

Recommended:

```text
impact_quantity = lot_count
impact_quantity_basis = lot_count
```

---

## 11. Common Enriched Fields

Each enriched candidate should preserve the original fields and add at least:

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

Recommended default numeric values:

```text
0.0
```

Recommended default risk scores:

```text
none
low
medium
high
```

Recommended default assumption source:

```text
cost_kpi_context
```

If no relevant assumption exists, use:

```text
impact_status = not_estimated
```

For qualitative data-quality issues, use:

```text
impact_status = qualitative_only
```

---

## 12. Impact Categories

Recommended impact categories:

```text
service_risk
inventory_risk
capacity_risk
data_quality_risk
replan_option
no_direct_cost_estimate
```

Mapping examples:

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

## 13. Enrichment Rules: Planning Issues

### 13.1 capacity_violation

For:

```text
issue_type = capacity_violation
```

Recommended:

```text
impact_category = capacity_risk
estimated_capacity_cost_impact =
    lot_count × capacity_shortage_penalty_per_lot[capacity_type]
```

If penalty rate is available:

```text
impact_status = estimated
kpi_capacity_risk_score = high
```

If not available:

```text
impact_status = not_estimated
kpi_capacity_risk_score = high
```

### 13.2 blocked_lot

For:

```text
issue_type = blocked_lot
```

Recommended:

```text
impact_category = service_risk
estimated_lost_sales_value =
    lot_count × unit_price_by_product[product]

estimated_margin_impact =
    lot_count × unit_margin_by_product[product]

estimated_service_penalty =
    lot_count × service_penalty_per_lot[product]
```

If at least one assumption is available:

```text
impact_status = estimated
```

Otherwise:

```text
impact_status = not_estimated
```

### 13.3 backlog_lot

For:

```text
issue_type = backlog_lot
```

Recommended:

```text
impact_category = service_risk
estimated_service_penalty =
    lot_count × service_penalty_per_lot[product]
```

Do not assume lost sales by default because backlog may still be fulfilled later.

### 13.4 overflow_inventory

For:

```text
issue_type = overflow_inventory
```

Recommended:

```text
impact_category = inventory_risk
estimated_inventory_cost_impact =
    lot_count × inventory_holding_cost_per_lot_per_week[product]
```

### 13.5 shifted_lot

For:

```text
issue_type = shifted_lot
```

Recommended:

```text
impact_category = no_direct_cost_estimate
impact_status = not_estimated
```

Do not guess shifted duration in MVP.

### 13.6 missing_lot

For:

```text
issue_type = missing_lot
```

Recommended:

```text
impact_category = data_quality_risk
impact_status = qualitative_only
kpi_data_quality_risk_score = high
```

No monetary estimate by default.

---

## 14. Enrichment Rules: Management Issues

Management issue enrichment should preserve the management-level issue and add impact category / KPI fields.

Examples:

### 14.1 capacity_bottleneck

```text
impact_category = capacity_risk
kpi_capacity_risk_score = high
estimated_capacity_cost_impact =
    lot_count × capacity_shortage_penalty_per_lot[capacity_type]
```

### 14.2 shipment_capacity_constraint

```text
impact_category = capacity_risk
kpi_capacity_risk_score = high
```

Use `capacity_shortage_penalty_per_lot["S"]` if available.

### 14.3 service_risk

```text
impact_category = service_risk
kpi_service_risk_score = high
```

If product price / margin exists:

```text
estimated_lost_sales_value
estimated_margin_impact
```

### 14.4 inventory_overflow_risk

```text
impact_category = inventory_risk
kpi_inventory_risk_score = high
```

### 14.5 planning_data_quality_risk

```text
impact_category = data_quality_risk
impact_status = qualitative_only
kpi_data_quality_risk_score = high
```

---

## 15. Enrichment Rules: Replan Command Candidates

Replan command candidates must remain:

```text
status = candidate_only
```

Recommended enrichment:

```text
impact_category = replan_option
impact_status = qualitative_only
estimated_total_business_impact = 0.0
```

Optional field:

```text
expected_benefit_category
```

Suggested mappings from `suggested_action` or `issue_type` if obvious:

```text
reduce_capacity_risk
reduce_service_risk
reduce_inventory_risk
review_required
```

Do not execute any command.

---

## 16. Enrichment Rules: Health Issues

Health issues represent structural risks.

Recommended:

```text
impact_category = data_quality_risk
impact_status = qualitative_only
kpi_data_quality_risk_score = high
estimated_total_business_impact = 0.0
```

Do not estimate monetary impact by default.

---

## 17. Total Business Impact

For each enriched record, calculate:

```text
estimated_total_business_impact =
    estimated_lost_sales_value
  + estimated_margin_impact
  + estimated_inventory_cost_impact
  + estimated_capacity_cost_impact
  + estimated_service_penalty
```

Important note:

```text
This is a directional scenario-level impact signal, not formal accounting.
```

The enriched summary should include:

```text
impact_values_are_directional = True
double_counting_possible = True
```

because lost sales and margin impact may overlap conceptually.

---

## 18. Enriched Summary

The enriched KPI bundle summary should include at least:

```python
{
    "product": "RICE",
    "currency": "JPY",

    "planning_issue_candidate_count": 0,
    "management_issue_candidate_count": 0,
    "replan_command_candidate_count": 0,
    "health_issue_candidate_count": 0,

    "estimated_lost_sales_value_total": 0.0,
    "estimated_margin_impact_total": 0.0,
    "estimated_inventory_cost_impact_total": 0.0,
    "estimated_capacity_cost_impact_total": 0.0,
    "estimated_service_penalty_total": 0.0,
    "estimated_total_business_impact": 0.0,

    "service_risk_issue_count": 0,
    "inventory_risk_issue_count": 0,
    "capacity_risk_issue_count": 0,
    "data_quality_risk_issue_count": 0,

    "impact_values_are_directional": True,
    "double_counting_possible": True,
}
```

The summary totals should be deterministic and tested.

---

## 19. Serialization Helpers

Please implement:

```python
def issue_candidate_kpi_bundle_to_dict(bundle: ExplicitPipelineIssueCandidateKPIBundle) -> dict:
    ...

def issue_candidate_kpi_bundle_as_rows(bundle: ExplicitPipelineIssueCandidateKPIBundle) -> list[dict]:
    ...
```

Row order:

```text
enriched_planning_issue_candidates
enriched_management_issue_candidates
enriched_replan_command_candidates
enriched_health_issue_candidates
```

Use dataclasses.asdict if appropriate.

---

## 20. Package Export

If updating `pysi/reporting/__init__.py`, export:

```python
ExplicitPipelineIssueCandidateKPIBundle
enrich_explicit_pipeline_issue_candidates_with_cost_kpi
maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env
issue_candidate_kpi_bundle_to_dict
issue_candidate_kpi_bundle_as_rows
```

Keep the update minimal.

---

## 21. Tests to Add

Please add:

```text
tests/test_explicit_pipeline_issue_candidate_cost_kpi.py
```

### 21.1 Synthetic bundle with assumptions

Create an `ExplicitPipelineIssueCandidateBundle` with at least:

```text
planning issue: blocked_lot with lot_ids
planning issue: overflow_inventory with lot_ids
planning issue: capacity_violation with capacity_type P
planning issue: missing_lot
management issue: service_risk
management issue: capacity_bottleneck
replan command candidate with status=candidate_only
health issue: non_string_lot_error
```

Use a cost context containing:

```text
unit_price_by_product
unit_margin_by_product
inventory_holding_cost_per_lot_per_week
capacity_shortage_penalty_per_lot
service_penalty_per_lot
currency
```

Verify expected numeric enrichments.

### 21.2 Missing assumptions

Call enrichment with:

```python
cost_kpi_context={}
```

Verify:

```text
records are still produced
impact_status is not_estimated or qualitative_only
monetary fields default to zero
no exception is raised
```

### 21.3 Lot_ID preservation

Verify original `lot_ids` are preserved in enriched records.

### 21.4 Replan candidate remains candidate-only

Verify:

```text
status == candidate_only
```

is preserved in enriched replan records.

### 21.5 Summary totals

Verify:

```text
summary estimated totals equal sums across enriched rows
risk issue counts are correct
currency is preserved
```

### 21.6 Env helper no-op

Create env without issue candidate bundle.

Verify:

```python
maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env(env) is None
```

### 21.7 Env helper attaches KPI bundle

Create env with:

```python
env.explicit_bridge_capacity_issue_candidates = bundle
```

Call helper.

Verify:

```text
env.explicit_bridge_capacity_issue_candidate_kpi_bundle exists
```

### 21.8 Serialization helpers

Verify:

```text
issue_candidate_kpi_bundle_to_dict(...) returns dict
issue_candidate_kpi_bundle_as_rows(...) returns list[dict]
```

---

## 22. Existing Tests to Run

Please run:

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
```

Optional:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

If optional tests are not run, state so clearly.

---

## 23. Completion Criteria

This request is complete when:

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
[OK] no GUI changes
[OK] no planning-sequence changes
[OK] no formal accounting implementation
[OK] no command execution
```

---

## 24. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. Enriched fields implemented
4. Cost / KPI context behavior
5. Mapping / enrichment rules implemented
6. Missing assumption behavior
7. Summary fields implemented
8. Env helper behavior
9. Test commands executed
10. Test results
11. Limitations / follow-up
```

Please do not proceed into:

```text
enriched issue export
automatic planning-sequence integration
GUI display
OR optimization
database persistence
ReplanCommand execution
Knowledge Continuity persistence
```

This request is only for:

```text
Explicit Pipeline Issue Candidate Cost / KPI Enrichment MVP
```
