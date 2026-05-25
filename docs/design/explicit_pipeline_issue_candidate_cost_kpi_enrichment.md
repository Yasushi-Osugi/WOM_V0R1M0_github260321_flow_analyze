# Explicit Pipeline Issue Candidate Cost / KPI Enrichment Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-23  
**Status:** Design memo  
**Target path:** `docs/design/explicit_pipeline_issue_candidate_cost_kpi_enrichment.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/explicit_pipeline_phase1_to_phase4_overview.md`
- `docs/design/explicit_pipeline_issue_candidate_export.md`
- `docs/design/explicit_pipeline_issue_candidate_export_completion.md`
- `docs/design/explicit_pipeline_management_issue_candidates.md`
- `docs/design/explicit_pipeline_management_issue_candidates_completion.md`
- `docs/design/explicit_pipeline_capacity_report_export.md`
- `docs/design/explicit_pipeline_capacity_report_export_completion.md`
- `docs/design/wom_knowledge_continuity_layer.md`

---

## 1. Purpose

This memo defines the design for **Explicit Pipeline Issue Candidate Cost / KPI Enrichment**.

The current explicit pipeline can already produce:

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

The next step is to enrich issue candidates with business impact values.

The goal is to move from:

```text
This issue exists.
```

to:

```text
This issue exists, and this is its estimated business impact.
```

This phase attaches Cost / KPI implications to issue candidates without changing the underlying planning result and without executing replanning.

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
cost/KPI enrichment                      ← next target
    ↓
GUI display
```

The current input object is:

```python
ExplicitPipelineIssueCandidateBundle
```

The current exported audit files include:

```text
planning_issues.csv
management_issues.csv
replan_command_candidates.csv
health_issues.csv
all_issue_candidates.csv
summary.json
```

---

## 3. Design Goal

The design goal is deliberately focused:

```text
Attach estimated Cost / KPI impact fields to existing issue candidate records.
```

Recommended enriched output object:

```text
ExplicitPipelineIssueCandidateKPIBundle
```

Recommended transformation:

```text
ExplicitPipelineIssueCandidateBundle
    ↓
Cost / KPI enrichment
    ↓
ExplicitPipelineIssueCandidateKPIBundle
    ↓
enriched_planning_issue_candidates
enriched_management_issue_candidates
enriched_replan_command_candidates
enriched_health_issue_candidates
summary
```

This is an enrichment layer.

It should not replace the original issue candidate builder.

---

## 4. Non-Goals

This phase must not implement:

```text
automatic replanning
ReplanCommand execution
GUI display
OR optimization
database persistence
final management decision logic
financial accounting precision
full product costing engine
```

This phase is not a replacement for a formal costing system.

It should provide practical, explainable, scenario-level business impact estimates.

---

## 5. WOM Cost / KPI Philosophy

WOM is not intended to become a full precision product costing system.

WOM’s Cost / KPI role is:

```text
scenario-level business impact simulation
```

The cost / KPI enrichment should therefore focus on:

```text
directional decision support
relative comparison between alternatives
issue prioritization
management explanation
```

rather than:

```text
statutory accounting
ERP-grade product costing
actual cost settlement
```

The design should remain aligned with the existing WOM philosophy:

```text
Lot is the subject.
```

Cost / KPI values should, as much as possible, remain traceable to:

```text
Lot_ID
product
node
week
capacity_type
issue_type
```

---

## 6. Primary Inputs

### 6.1 Issue candidate bundle

Primary input:

```python
ExplicitPipelineIssueCandidateBundle
```

from:

```text
pysi/reporting/explicit_pipeline_issue_candidates.py
```

Important fields:

```text
planning_issue_candidates
management_issue_candidates
replan_command_candidates
health_issue_candidates
summary
```

### 6.2 Optional business context

Optional input:

```text
cost_kpi_context
```

This may include:

```text
unit_price_by_product
unit_margin_by_product
unit_cost_by_product
inventory_holding_cost_rate
capacity_overtime_cost_rate
capacity_shortage_penalty_rate
service_penalty_rate
lost_sales_rate
currency
period_granularity
```

### 6.3 Optional master data

Later phases may load values from:

```text
CSV
SQL
existing WOM costing masters
scenario parameter files
```

For MVP, dictionary-based inputs are sufficient.

---

## 7. Recommended Module

Suggested module:

```text
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi.py
```

Reason:

```text
The enrichment consumes issue candidates and produces reporting / management-support records.
It does not belong in the core planning engine.
```

Future architecture may move it to:

```text
pysi/management/
pysi/kpi/
pysi/costing/
```

but MVP should stay near the explicit pipeline reporting chain.

---

## 8. Recommended Test File

Suggested test file:

```text
tests/test_explicit_pipeline_issue_candidate_cost_kpi.py
```

Tests should use synthetic `ExplicitPipelineIssueCandidateBundle` objects.

---

## 9. Enrichment Result Dataclass

Recommended dataclass:

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

The records remain dictionary-based in the MVP.

Typed records can be introduced later after the KPI taxonomy stabilizes.

---

## 10. Main Enrichment Function

Recommended function:

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
2. Copy each issue candidate record.
3. Attach estimated Cost / KPI fields based on deterministic rules.
4. Preserve Lot_ID, node, week, product, severity, issue_type.
5. Build enriched summary.
6. Return ExplicitPipelineIssueCandidateKPIBundle.
```

The function should tolerate missing cost assumptions.

When assumptions are missing, it should still produce enriched records with:

```text
impact_status = "not_estimated"
```

rather than failing.

---

## 11. Env Helper

Recommended helper:

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
3. Enrich bundle with cost / KPI values.
4. Attach env.explicit_bridge_capacity_issue_candidate_kpi_bundle.
5. Return enriched bundle.
```

No GUI display.

No command execution.

---

## 12. Cost / KPI Context Schema

Recommended MVP context schema:

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

This schema is intentionally simple.

Future versions can connect to WOM costing masters.

---

## 13. Lot Quantity Assumption

Issue candidates currently preserve `lot_ids`, but they may not always contain quantity.

MVP rule:

```text
one Lot_ID = one planning lot unit
```

Therefore:

```python
lot_count = len(lot_ids)
```

If `lot_ids` is empty:

```python
lot_count = 0
```

If a future record has:

```text
quantity
lot_qty
qty
```

then enrichment may use that instead.

MVP should record the method:

```text
impact_quantity_basis = "lot_count"
```

---

## 14. Enriched Common Fields

Each enriched candidate should preserve original fields and add:

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

Not every field must have a non-zero value.

If not applicable, use:

```text
0
```

or:

```text
not_applicable
```

depending on field type.

---

## 15. Impact Categories

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
shifted_lot              → no_direct_cost_estimate / inventory_risk depending on context
```

---

## 16. Planning Issue Enrichment Rules

### 16.1 capacity_violation

For `issue_type = capacity_violation`:

```text
impact_category = capacity_risk
estimated_capacity_cost_impact =
    lot_count × capacity_shortage_penalty_per_lot[capacity_type]
```

If no penalty rate is available:

```text
impact_status = not_estimated
```

If available:

```text
impact_status = estimated
```

### 16.2 blocked_lot

For `issue_type = blocked_lot`:

```text
impact_category = service_risk
estimated_lost_sales_value =
    lot_count × unit_price_by_product[product]

estimated_margin_impact =
    lot_count × unit_margin_by_product[product]

estimated_service_penalty =
    lot_count × service_penalty_per_lot[product]
```

### 16.3 backlog_lot

For `issue_type = backlog_lot`:

```text
impact_category = service_risk
estimated_service_penalty =
    lot_count × service_penalty_per_lot[product]
```

Lost sales may not be assumed by default because backlog can still be fulfilled later.

### 16.4 overflow_inventory

For `issue_type = overflow_inventory`:

```text
impact_category = inventory_risk
estimated_inventory_cost_impact =
    lot_count × inventory_holding_cost_per_lot_per_week[product]
```

### 16.5 shifted_lot

For `issue_type = shifted_lot`:

```text
impact_category = no_direct_cost_estimate
```

Optional future logic:

```text
early build inventory cost = shifted weeks × holding cost × lot count
```

But MVP should avoid guessing shifted duration if not present.

### 16.6 missing_lot

For `issue_type = missing_lot`:

```text
impact_category = data_quality_risk
kpi_data_quality_risk_score = high
```

Do not estimate monetary impact unless assumptions are available.

---

## 17. Management Issue Enrichment Rules

Management issue candidates should receive a management-level rollup.

Examples:

### 17.1 capacity_bottleneck

```text
impact_category = capacity_risk
kpi_capacity_risk_score = high
```

If lot count and penalty are available:

```text
estimated_capacity_cost_impact =
    lot_count × capacity_shortage_penalty_per_lot[capacity_type]
```

### 17.2 service_risk

```text
impact_category = service_risk
kpi_service_risk_score = high
```

If product price or margin exists:

```text
estimated_lost_sales_value
estimated_margin_impact
```

### 17.3 inventory_overflow_risk

```text
impact_category = inventory_risk
kpi_inventory_risk_score = high
```

### 17.4 planning_data_quality_risk

```text
impact_category = data_quality_risk
kpi_data_quality_risk_score = high
```

---

## 18. Replan Command Candidate Enrichment Rules

Replan command candidates remain:

```text
status = candidate_only
```

Enrichment should add:

```text
impact_category = replan_option
estimated_total_business_impact = 0
```

The candidate may include:

```text
expected_benefit_category
```

such as:

```text
reduce_capacity_risk
reduce_service_risk
reduce_inventory_risk
```

But no replan command should be executed.

---

## 19. Health Issue Enrichment Rules

Health issues usually represent structural risks.

For health issues:

```text
impact_category = data_quality_risk
kpi_data_quality_risk_score = high
impact_status = qualitative_only
```

Do not estimate monetary impact by default.

---

## 20. Total Business Impact

Recommended MVP calculation:

```text
estimated_total_business_impact =
    estimated_lost_sales_value
  + estimated_margin_impact
  + estimated_inventory_cost_impact
  + estimated_capacity_cost_impact
  + estimated_service_penalty
```

Note:

```text
This is not formal accounting.
It is a scenario-level impact signal.
```

Potential double-counting exists between lost sales and margin impact.

Therefore, the enriched summary should include a warning:

```text
impact_values_are_directional = True
double_counting_possible = True
```

---

## 21. Enriched Summary

The enriched bundle summary should include:

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

This summary should be deterministic and testable.

---

## 22. Serialization Helpers

Recommended helpers:

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

---

## 23. Export Design Boundary

This design is for enrichment only.

Export of enriched issue candidates should be a later phase.

Possible future files:

```text
outputs/explicit_pipeline/issue_candidate_kpi/enriched_planning_issues.csv
outputs/explicit_pipeline/issue_candidate_kpi/enriched_management_issues.csv
outputs/explicit_pipeline/issue_candidate_kpi/enriched_replan_command_candidates.csv
outputs/explicit_pipeline/issue_candidate_kpi/enriched_health_issues.csv
outputs/explicit_pipeline/issue_candidate_kpi/summary.json
```

Do not implement export in this MVP unless explicitly requested.

---

## 24. Package Export

If implemented, package export may include:

```python
ExplicitPipelineIssueCandidateKPIBundle
enrich_explicit_pipeline_issue_candidates_with_cost_kpi
maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env
issue_candidate_kpi_bundle_to_dict
issue_candidate_kpi_bundle_as_rows
```

---

## 25. Testing Strategy

### 25.1 Synthetic bundle with assumptions

Create a synthetic issue candidate bundle with:

```text
blocked_lot
overflow_inventory
capacity_violation
planning_data_quality_risk
replan_command_candidate
```

Use context:

```text
unit_price_by_product
unit_margin_by_product
inventory_holding_cost_per_lot_per_week
capacity_shortage_penalty_per_lot
service_penalty_per_lot
```

Verify enriched fields.

### 25.2 Missing assumptions

Run enrichment with empty context.

Verify:

```text
records still produced
impact_status is not_estimated or qualitative_only
monetary fields default to zero
no exception is raised
```

### 25.3 Lot_ID preservation

Verify original `lot_ids` are preserved.

### 25.4 Replan candidate remains candidate-only

Verify:

```text
status = candidate_only
```

is preserved.

### 25.5 Summary totals

Verify summary totals equal the sum of enriched records.

### 25.6 Env helper no-op

If env has no issue candidate bundle:

```text
return None
```

### 25.7 Env helper attach

If env has issue candidate bundle:

```text
env.explicit_bridge_capacity_issue_candidate_kpi_bundle is attached
```

---

## 26. Existing Tests to Run

Run:

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

---

## 27. Recommended Implementation Scope

Recommended MVP implementation:

```text
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi.py
tests/test_explicit_pipeline_issue_candidate_cost_kpi.py
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
capacity report exporter
```

---

## 28. Completion Criteria

This design is complete when it defines:

```text
[OK] enrichment module location
[OK] KPI bundle dataclass
[OK] main enrichment function
[OK] env helper
[OK] cost / KPI context schema
[OK] lot quantity assumption
[OK] common enriched fields
[OK] impact category mapping
[OK] planning issue enrichment rules
[OK] management issue enrichment rules
[OK] replan candidate enrichment rules
[OK] health issue enrichment rules
[OK] total business impact rule
[OK] enriched summary fields
[OK] serialization helpers
[OK] test strategy
[OK] boundaries from GUI / command execution / formal accounting
```

---

## 29. Relationship to GUI

GUI should not be modified in this phase.

Future GUI display may show:

```text
issue type
severity
node
week
lot_ids
estimated business impact
risk category
suggested action
```

But GUI should wait until:

```text
issue candidate schema
cost / KPI enrichment schema
export behavior
```

are stable.

---

## 30. Relationship to WOM Knowledge Continuity Layer

The enriched issue candidates can later become inputs to WOM Knowledge Continuity Layer.

Possible mapping:

```text
high-impact management issues
    → open issues / decision log candidates

validated impact patterns
    → facts & findings

recurring blocked_lot / capacity_bottleneck patterns
    → business rules / scenario patterns

replan candidates with strong impact
    → next-entry prompts
```

This phase should not automate that flow.

It only prepares the enriched facts that a future Knowledge Continuity process may consume.

---

## 31. Summary

This design defines Cost / KPI enrichment for explicit pipeline issue candidates.

The target flow is:

```text
ExplicitPipelineIssueCandidateBundle
    ↓
enrich_explicit_pipeline_issue_candidates_with_cost_kpi(...)
    ↓
ExplicitPipelineIssueCandidateKPIBundle
```

The guiding principle is:

```text
Attach directional business impact values.
Preserve Lot_ID traceability.
Do not execute commands.
Do not perform formal accounting.
Do not display GUI yet.
```

This gives WOM the next layer of management decision support.
