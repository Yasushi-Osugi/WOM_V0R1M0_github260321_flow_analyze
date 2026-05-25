# Codex Request: Implement Explicit Pipeline Management Cockpit KPI View Model MVP

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_view.md
```

Please read this design memo first.

The explicit pipeline reporting / issue / Cost-KPI stack has already been connected to the planning sequence:

```text
explicit bridge + capacity pipeline
    ↓
reporting flag switchboard helper
    ↓
capacity report
    ↓
issue candidates
    ↓
Cost / KPI enrichment
    ↓
exportable audit files
```

The current completed stack includes:

```text
ExplicitBridgeCapacityPipelineResult
ExplicitPipelineCapacityReport
ExplicitPipelineCapacityReportExportResult
ExplicitPipelineIssueCandidateBundle
ExplicitPipelineIssueCandidateExportResult
ExplicitPipelineIssueCandidateKPIBundle
ExplicitPipelineIssueCandidateKPIExportResult
```

The next step is **not GUI rendering yet**.

This request is only for the first Management Cockpit KPI View phase:

```text
view model only
```

---

## 2. Main Objective

Add a pure view-model builder that converts the explicit pipeline env state into a management-friendly dictionary.

Target function:

```python
build_explicit_pipeline_management_cockpit_view_model(env) -> dict
```

Target module:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

Target test file:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view.py
```

The view model should summarize:

```text
status
executive KPI totals
capacity summary
issue summary
top impact issues
replan candidates
health summary
assumption summary
export summary
next review actions
messages
```

This request must not create a Tk window.

This request must not modify `cockpit_tk.py`.

This request must not add buttons or GUI widgets.

---

## 3. Important Constraints

Please follow these constraints:

```text
1. Do not modify pysi/gui/cockpit_tk.py.
2. Do not add GUI widgets.
3. Do not add buttons.
4. Do not add Tk windows.
5. Do not change layout.
6. Do not run planning.
7. Do not trigger exports.
8. Do not change feature flags.
9. Do not execute ReplanCommand.
10. Do not implement automatic replanning.
11. Do not implement OR optimization.
12. Do not implement database persistence.
13. Do not implement Knowledge Continuity persistence.
14. Do not modify Cost / KPI enrichment logic.
15. Do not modify exporter logic.
```

This request is only for:

```text
read-only view model builder + focused tests
```

---

## 4. Files to Add / Modify

Please add:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
tests/test_explicit_pipeline_management_cockpit_kpi_view.py
```

Optionally update:

```text
pysi/gui/__init__.py
```

only if the project style already exports GUI helpers there.

Do not modify:

```text
pysi/gui/cockpit_tk.py
pysi/reporting/*
pysi/plan/*
```

unless a very small import path fix is absolutely necessary.

---

## 5. Primary Data Sources

The view model should read from env attributes.

Primary data sources:

```text
env.explicit_bridge_capacity_pipeline_result
env.explicit_bridge_capacity_pipeline_report
env.explicit_bridge_capacity_issue_candidates
env.explicit_bridge_capacity_issue_candidate_kpi_bundle
env.explicit_bridge_capacity_reporting_stack_results
```

Export result sources:

```text
env.explicit_bridge_capacity_pipeline_report_export_result
env.explicit_bridge_capacity_issue_candidate_export_result
env.explicit_bridge_capacity_issue_candidate_kpi_export_result
```

The function should tolerate missing attributes.

Missing data should produce safe empty summaries and messages.

---

## 6. Recommended Function Signature

Please implement:

```python
def build_explicit_pipeline_management_cockpit_view_model(env) -> dict:
    ...
```

The function should return a deterministic dictionary.

Recommended top-level schema:

```python
{
    "available": bool,
    "product": str,
    "status": dict,
    "executive_kpi_summary": dict,
    "capacity_summary": dict,
    "issue_summary": dict,
    "top_impact_issues": list[dict],
    "replan_candidates": list[dict],
    "health_summary": dict,
    "assumption_summary": dict,
    "export_summary": dict,
    "next_review_actions": list[str],
    "messages": list[str],
}
```

---

## 7. Availability Behavior

If no explicit pipeline data exists, return:

```python
{
    "available": False,
    ...
}
```

with a message similar to:

```text
No explicit pipeline reporting data is available. Run planning with explicit pipeline enabled.
```

Consider explicit pipeline data available if at least one of these exists:

```text
env.explicit_bridge_capacity_pipeline_result
env.explicit_bridge_capacity_pipeline_report
env.explicit_bridge_capacity_issue_candidates
env.explicit_bridge_capacity_issue_candidate_kpi_bundle
env.explicit_bridge_capacity_reporting_stack_results
```

---

## 8. Status Section

Build:

```python
"status": {
    "explicit_pipeline_result": bool,
    "capacity_report": bool,
    "issue_candidates": bool,
    "cost_kpi_bundle": bool,
    "capacity_report_export": bool,
    "issue_candidate_export": bool,
    "cost_kpi_export": bool,
    "reporting_stack_results": bool,
}
```

Each value should be based on whether the corresponding env attribute exists and is not `None`.

---

## 9. Product Resolution

Resolve product in this order:

```text
1. kpi_bundle.product_name
2. kpi_bundle.summary["product"]
3. issue_candidates.product_name
4. issue_candidates.summary["product"]
5. capacity_report.product_name
6. capacity_report.summary["product"]
7. pipeline_result.product_name
8. ""
```

Do not raise if a field is missing.

---

## 10. Executive KPI Summary

Source:

```text
env.explicit_bridge_capacity_issue_candidate_kpi_bundle.summary
```

If missing, return safe defaults.

Recommended keys:

```python
{
    "currency": "",
    "estimated_total_business_impact": 0.0,
    "estimated_lost_sales_value_total": 0.0,
    "estimated_margin_impact_total": 0.0,
    "estimated_inventory_cost_impact_total": 0.0,
    "estimated_capacity_cost_impact_total": 0.0,
    "estimated_service_penalty_total": 0.0,
    "impact_values_are_directional": True,
    "double_counting_possible": True,
}
```

If no KPI bundle exists, still include the keys with safe defaults and add a message:

```text
Cost / KPI enrichment is not available or the flag is off.
```

---

## 11. Capacity Summary

Source:

```text
env.explicit_bridge_capacity_pipeline_report.summary
```

Recommended keys:

```python
{
    "capacity_usage_record_count": 0,
    "capacity_violation_record_count": 0,
    "lot_exception_record_count": 0,
    "replan_candidate_record_count": 0,
    "health_check_record_count": 0,
    "has_error": False,
    "has_warning": False,
}
```

If report summary contains additional useful count fields, preserve them.

Also include:

```python
"available": bool
```

---

## 12. Issue Summary

Source:

```text
env.explicit_bridge_capacity_issue_candidates.summary
```

Recommended keys:

```python
{
    "planning_issue_candidate_count": 0,
    "management_issue_candidate_count": 0,
    "replan_command_candidate_count": 0,
    "health_issue_candidate_count": 0,
    "error_count": 0,
    "warning_count": 0,
    "info_count": 0,
    "has_error": False,
    "has_warning": False,
}
```

If issue candidate bundle is missing, return safe defaults and add message:

```text
Issue candidates are not available or the flag is off.
```

---

## 13. Top Impact Issues

Source preference:

```text
1. kpi_bundle.enriched_management_issue_candidates
2. kpi_bundle.enriched_planning_issue_candidates
```

Combine both lists.

Sort by:

```text
estimated_total_business_impact descending
severity priority
issue_type
node
week
```

Severity priority:

```python
SEVERITY_PRIORITY = {
    "error": 0,
    "warning": 1,
    "info": 2,
    "none": 3,
    "": 4,
}
```

Return top 10 by default.

Each row should preserve original candidate fields and include at least:

```text
rank
severity
issue_type
impact_category
product
node
week
capacity_type
lot_ids
estimated_total_business_impact
suggested_action
suggested_decision
message
```

If no KPI bundle exists, return empty list.

---

## 14. Replan Candidates

Source preference:

```text
1. kpi_bundle.enriched_replan_command_candidates
2. issue_candidates.replan_command_candidates
```

Return a list of dicts.

Important rule:

```text
status must remain candidate_only when present.
```

Recommended row fields:

```text
status
command_type
issue_type
product
node
week
expected_benefit_category
message
suggested_action
```

Do not add executable command behavior.

Do not add a run action.

---

## 15. Health Summary

Sources:

```text
kpi_bundle.enriched_health_issue_candidates
issue_candidates.health_issue_candidates
capacity_report.health_check_records
```

Recommended keys:

```python
{
    "available": bool,
    "health_issue_count": 0,
    "data_quality_risk_issue_count": 0,
    "missing_lot_count": 0,
    "non_list_bucket_error_count": 0,
    "non_string_lot_error_count": 0,
    "has_error": False,
    "has_warning": False,
    "top_health_issues": list[dict],
}
```

Top health issue rows should include:

```text
severity
issue_type
source
message
details
```

---

## 16. Assumption Summary

Source:

```text
kpi_bundle.assumptions
```

Return compact summary, not a huge JSON dump.

Recommended keys:

```python
{
    "available": bool,
    "currency": "",
    "product_assumption_keys": [],
    "unit_price_products": [],
    "unit_margin_products": [],
    "unit_cost_products": [],
    "inventory_holding_cost_products": [],
    "capacity_shortage_penalty_types": [],
    "capacity_overtime_cost_types": [],
    "service_penalty_products": [],
}
```

Extract keys safely from dictionaries such as:

```text
unit_price_by_product
unit_margin_by_product
unit_cost_by_product
inventory_holding_cost_per_lot_per_week
capacity_shortage_penalty_per_lot
capacity_overtime_cost_per_lot
service_penalty_per_lot
```

---

## 17. Export Summary

Sources:

```text
env.explicit_bridge_capacity_pipeline_report_export_result
env.explicit_bridge_capacity_issue_candidate_export_result
env.explicit_bridge_capacity_issue_candidate_kpi_export_result
```

Return:

```python
{
    "capacity_report_export": {...},
    "issue_candidate_export": {...},
    "cost_kpi_export": {...},
}
```

Each export summary should include:

```text
available
output_dir
file_count
files
record_counts
summary_path
assumptions_path
message
```

Convert Path objects to strings.

If export result is missing, return:

```python
{"available": False}
```

Do not open files.

Do not verify files on disk.

Do not create files.

---

## 18. Next Review Actions

Generate simple, deterministic review actions from the view model.

Examples:

```text
Review high impact management issues.
Check capacity violations with high capacity risk.
Validate Cost / KPI assumptions before using estimates.
Review data quality health issues.
Consider replan candidates manually; they are not executed automatically.
```

Rules:

```text
if top_impact_issues non-empty:
    add high impact review message

if capacity_summary.has_warning or has_error:
    add capacity risk review message

if health_summary.health_issue_count > 0:
    add data quality review message

if assumption_summary.available:
    add assumption validation message

if replan_candidates non-empty:
    add candidate-only review message
```

No command execution.

---

## 19. Messages

The `messages` list should include safe, user-facing messages for missing or caveated data.

Examples:

```text
No explicit pipeline reporting data is available. Run planning with explicit pipeline enabled.
Cost / KPI enrichment is not available or the flag is off.
Issue candidates are not available or the flag is off.
Export results are not available. Export flags may be off.
Cost / KPI values are directional scenario estimates, not formal accounting values.
Double counting may be possible depending on assumptions.
```

If KPI bundle exists, include the directional caveat message.

---

## 20. Helper Functions

It is fine to implement small private helpers inside the module, such as:

```python
_getattr(obj, name, default=None)
_get_summary(obj) -> dict
_as_dict(value) -> dict
_as_list(value) -> list
_to_float(value) -> float
_severity_rank(value) -> int
_export_result_to_summary(value) -> dict
```

Keep them simple and deterministic.

---

## 21. Tests to Add

Please add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view.py
```

### 21.1 No data

Create empty env.

Verify:

```text
available is False
status values are False
messages include no-data message
top_impact_issues is []
```

### 21.2 Report only

Create env with synthetic `ExplicitPipelineCapacityReport`.

Verify:

```text
available is True
capacity_summary.available is True
capacity counts are reflected
issue summary remains safe default
Cost / KPI missing message is present
```

### 21.3 Issue candidates only

Create env with synthetic `ExplicitPipelineIssueCandidateBundle`.

Verify:

```text
issue_summary counts are reflected
replan candidates are shown if present
Cost / KPI missing message is present
```

### 21.4 KPI bundle with top impact issues

Create env with synthetic `ExplicitPipelineIssueCandidateKPIBundle`.

Include at least three enriched issues with different impacts and severities.

Verify:

```text
executive_kpi_summary totals are reflected
top_impact_issues sorted by estimated_total_business_impact descending
rank starts at 1
directional caveat messages are present
```

### 21.5 Replan candidate remains candidate_only

Create KPI bundle or issue bundle with replan candidates.

Verify:

```text
status == candidate_only
```

### 21.6 Assumption summary

Create KPI bundle with assumptions.

Verify:

```text
currency
unit_price_products
capacity_shortage_penalty_types
service_penalty_products
```

### 21.7 Export summary

Create synthetic export result objects using `SimpleNamespace` or existing dataclasses.

Verify:

```text
available is True
output_dir string
file_count
record_counts
summary_path
assumptions_path
```

### 21.8 Missing partial data does not crash

Create env with partial objects missing summaries or fields.

Verify:

```text
function returns dict
safe defaults are present
no exception
```

---

## 22. Existing Tests to Run

Please run:

```bat
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_view.py
python -m pytest tests/test_explicit_pipeline_reporting_stack_insertion.py
python -m pytest tests/test_explicit_pipeline_reporting_flags.py
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

## 23. Completion Criteria

This request is complete when:

```text
[OK] pysi/gui/explicit_pipeline_management_cockpit_view.py exists
[OK] build_explicit_pipeline_management_cockpit_view_model(env) exists
[OK] view model contains status
[OK] view model contains executive_kpi_summary
[OK] view model contains capacity_summary
[OK] view model contains issue_summary
[OK] view model contains top_impact_issues
[OK] view model contains replan_candidates
[OK] view model contains health_summary
[OK] view model contains assumption_summary
[OK] view model contains export_summary
[OK] view model contains next_review_actions
[OK] view model contains messages
[OK] missing data is handled safely
[OK] top impact sorting is deterministic
[OK] Cost / KPI caveat messages are included
[OK] replan candidates remain candidate_only
[OK] focused tests pass
[OK] no Tk window is added
[OK] no cockpit_tk.py modification
[OK] no planning execution
[OK] no export execution
[OK] no ReplanCommand execution
```

---

## 24. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. View model schema implemented
4. Missing data behavior
5. Top impact sorting behavior
6. Assumption summary behavior
7. Export summary behavior
8. Safety boundaries preserved
9. Test commands executed
10. Test results
11. Limitations / follow-up
```

Please do not proceed into:

```text
Tk rendering
Management Cockpit button
cockpit_tk.py modification
planning execution
export execution
OR optimization
database persistence
ReplanCommand execution
Knowledge Continuity persistence
```

This request is only for:

```text
Explicit Pipeline Management Cockpit KPI View Model MVP
```
