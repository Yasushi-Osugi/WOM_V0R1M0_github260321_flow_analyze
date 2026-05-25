# Explicit Pipeline Management Cockpit KPI View Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-24  
**Status:** Completion memo  
**Target path:** `docs/design/explicit_pipeline_management_cockpit_kpi_view_completion.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Explicit Pipeline Management Cockpit KPI View Model MVP**.

The purpose of this milestone was to implement the first Management Cockpit KPI View layer as a **pure read-only view model**, not as a Tk GUI screen.

The completed view-model builder is:

```python
build_explicit_pipeline_management_cockpit_view_model(env) -> dict
```

implemented in:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

This milestone creates the data shape that a future Management Cockpit GUI can render.

It does not yet create a window, button, panel, or visual cockpit screen.

---

## 2. Background

Before this milestone, WOM had completed the explicit pipeline explanation stack and connected it to the planning sequence:

```text
explicit bridge + capacity pipeline
    ↓
reporting flag switchboard helper
    ↓
capacity report
    ↓
capacity report export
    ↓
issue candidates
    ↓
issue candidate export
    ↓
Cost / KPI enrichment
    ↓
Cost / KPI export
```

The next natural step was to prepare a management-facing representation of these artifacts.

However, instead of going directly into GUI rendering, this milestone intentionally implemented only:

```text
env explicit pipeline artifacts
    ↓
build_explicit_pipeline_management_cockpit_view_model(env)
    ↓
Management Cockpit display-ready dict
```

This keeps GUI rendering separated from data extraction and formatting.

---

## 3. Implemented Files

This milestone added:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
tests/test_explicit_pipeline_management_cockpit_kpi_view.py
```

The implementation was committed as:

```text
fb8acd9 Add explicit pipeline management cockpit KPI view model
```

---

## 4. Main Implemented Function

The implemented main function is:

```python
build_explicit_pipeline_management_cockpit_view_model(env) -> dict
```

It reads existing env attributes and returns a deterministic dictionary suitable for future GUI rendering.

Primary env inputs:

```text
env.explicit_bridge_capacity_pipeline_result
env.explicit_bridge_capacity_pipeline_report
env.explicit_bridge_capacity_issue_candidates
env.explicit_bridge_capacity_issue_candidate_kpi_bundle
env.explicit_bridge_capacity_reporting_stack_results
```

Export result inputs:

```text
env.explicit_bridge_capacity_pipeline_report_export_result
env.explicit_bridge_capacity_issue_candidate_export_result
env.explicit_bridge_capacity_issue_candidate_kpi_export_result
```

The function tolerates missing attributes and returns safe defaults.

---

## 5. View Model Schema Implemented

The view model includes the requested top-level schema:

```text
available
product
status
executive_kpi_summary
capacity_summary
issue_summary
top_impact_issues
replan_candidates
health_summary
assumption_summary
export_summary
next_review_actions
messages
```

Conceptually:

```python
{
    "available": bool,
    "product": str,
    "status": {...},
    "executive_kpi_summary": {...},
    "capacity_summary": {...},
    "issue_summary": {...},
    "top_impact_issues": [...],
    "replan_candidates": [...],
    "health_summary": {...},
    "assumption_summary": {...},
    "export_summary": {...},
    "next_review_actions": [...],
    "messages": [...],
}
```

---

## 6. Status Section

The view model includes status flags such as:

```text
explicit_pipeline_result
capacity_report
issue_candidates
cost_kpi_bundle
capacity_report_export
issue_candidate_export
cost_kpi_export
reporting_stack_results
```

These fields allow a future GUI to show which parts of the explicit pipeline explanation stack are available.

---

## 7. Product Resolution

The view model resolves product from available data without raising errors.

Priority is conceptually:

```text
KPI bundle
issue candidate bundle
capacity report
pipeline result
fallback empty string
```

This makes the view robust when only partial objects are available.

---

## 8. Executive KPI Summary

The view model includes an executive KPI summary based on:

```text
env.explicit_bridge_capacity_issue_candidate_kpi_bundle.summary
```

When available, this section can include:

```text
currency
estimated_total_business_impact
estimated_lost_sales_value_total
estimated_margin_impact_total
estimated_inventory_cost_impact_total
estimated_capacity_cost_impact_total
estimated_service_penalty_total
impact_values_are_directional
double_counting_possible
```

When the KPI bundle is missing, safe defaults are returned and an explanatory message is included.

---

## 9. Capacity Summary

The view model summarizes capacity report information from:

```text
env.explicit_bridge_capacity_pipeline_report.summary
```

It includes safe default fields such as:

```text
available
capacity_usage_record_count
capacity_violation_record_count
lot_exception_record_count
replan_candidate_record_count
health_check_record_count
has_error
has_warning
```

This section is intended to support future display of:

```text
Where is the capacity pressure?
```

---

## 10. Issue Summary

The view model summarizes issue candidates from:

```text
env.explicit_bridge_capacity_issue_candidates.summary
```

It includes fields such as:

```text
planning_issue_candidate_count
management_issue_candidate_count
replan_command_candidate_count
health_issue_candidate_count
error_count
warning_count
info_count
has_error
has_warning
```

When issue candidates are missing, safe defaults are returned and a message is included.

---

## 11. Top Impact Issues

The view model builds a `top_impact_issues` list from enriched issue candidates.

Source preference:

```text
kpi_bundle.enriched_management_issue_candidates
kpi_bundle.enriched_planning_issue_candidates
```

The list is sorted deterministically by:

```text
estimated_total_business_impact descending
severity priority
issue_type
node
week
```

Each row includes a rank.

This is the central future Management Cockpit table because it converts operational planning signals into management attention.

---

## 12. Replan Candidates

The view model extracts replan candidates from:

```text
kpi_bundle.enriched_replan_command_candidates
```

or, if KPI bundle is unavailable:

```text
issue_candidates.replan_command_candidates
```

Important safety rule preserved:

```text
Replan candidates remain candidate_only.
```

No executable command behavior was added.

No "Run" or "Execute" behavior was added.

---

## 13. Health Summary

The view model builds a health / data quality summary from available health signals:

```text
kpi_bundle.enriched_health_issue_candidates
issue_candidates.health_issue_candidates
capacity_report.health_check_records
```

It includes safe fields such as:

```text
available
health_issue_count
data_quality_risk_issue_count
missing_lot_count
non_list_bucket_error_count
non_string_lot_error_count
has_error
has_warning
top_health_issues
```

This section supports future display of:

```text
Can we trust this planning evidence?
```

---

## 14. Assumption Summary

The view model builds a compact assumption summary from:

```text
kpi_bundle.assumptions
```

It avoids dumping a huge JSON object into the view model.

Instead, it extracts compact keys such as:

```text
currency
unit_price_products
unit_margin_products
unit_cost_products
inventory_holding_cost_products
capacity_shortage_penalty_types
capacity_overtime_cost_types
service_penalty_products
```

This section supports future display of:

```text
What assumptions were used for the business impact estimate?
```

---

## 15. Export Summary

The view model normalizes export result objects from:

```text
env.explicit_bridge_capacity_pipeline_report_export_result
env.explicit_bridge_capacity_issue_candidate_export_result
env.explicit_bridge_capacity_issue_candidate_kpi_export_result
```

Each export summary can include:

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

Path values are converted to stable string representations.

A Windows Path formatting issue was found during testing and corrected by using POSIX-style path conversion for `Path` objects.

This avoids test failures caused by platform-specific path separators.

---

## 16. Messages

The view model includes user-facing messages for missing or caveated data, such as:

```text
No explicit pipeline reporting data is available. Run planning with explicit pipeline enabled.
Cost / KPI enrichment is not available or the flag is off.
Issue candidates are not available or the flag is off.
Export results are not available. Export flags may be off.
Cost / KPI values are directional scenario estimates, not formal accounting values.
Double counting may be possible depending on assumptions.
```

These messages are intended for future GUI display.

---

## 17. Next Review Actions

The view model generates deterministic review actions based on available data.

Examples:

```text
Review high impact management issues.
Check capacity violations with high capacity risk.
Validate Cost / KPI assumptions before using estimates.
Review data quality health issues.
Consider replan candidates manually; they are not executed automatically.
```

These are review prompts only.

They do not execute any planning or command logic.

---

## 18. Safety Boundaries Preserved

This milestone preserved all requested safety boundaries.

It did not:

```text
modify cockpit_tk.py
add Tk windows
add buttons
add widgets
change GUI layout
run planning
trigger exports
change feature flags
execute ReplanCommand
implement automatic replanning
run OR optimization
persist to database
persist Knowledge Continuity records
modify Cost / KPI enrichment logic
modify exporter logic
```

The module is a pure view assembly layer.

---

## 19. Helper Functions Implemented

The module includes deterministic helper functions for safe extraction and formatting, such as:

```text
safe dict/list coercion
numeric conversion
severity ranking
export-result normalization
Path-to-string conversion
```

These helpers keep the view-model builder robust against partial or missing env data.

---

## 20. Tests Added

The focused test file is:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view.py
```

It covers:

```text
1. no-data behavior
2. report-only behavior
3. issue-only behavior
4. KPI bundle and top-impact sorting
5. candidate_only preservation
6. assumptions extraction
7. export summary path/string behavior
8. partial-data safety
```

---

## 21. Test Issue Found and Fixed

During testing, one platform-specific issue was found.

The failure was caused by Windows path formatting:

```text
expected: /tmp/out
actual:   \tmp\out
```

The fix was to normalize `Path` output using POSIX-style conversion.

This keeps exported path strings stable across platforms.

After the fix, the focused view-model test passed.

---

## 22. Validation

The focused test passed:

```bat
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_view.py
```

Observed result:

```text
8 passed
```

The broader regression set also passed:

```bat
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
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results included:

```text
tests/test_explicit_pipeline_reporting_stack_insertion.py: 7 passed
tests/test_explicit_pipeline_reporting_flags.py: 10 passed
tests/test_explicit_pipeline_issue_candidate_cost_kpi_export.py: 7 passed
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

## 23. Completion Criteria

This milestone satisfies the intended completion criteria.

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
[OK] broader regression tests pass
[OK] no Tk window is added
[OK] no cockpit_tk.py modification
[OK] no planning execution
[OK] no export execution
[OK] no ReplanCommand execution
```

---

## 24. Meaning of This Milestone

Before this milestone:

```text
The explicit pipeline could generate management-relevant artifacts,
but there was no stable GUI-facing view model.
```

After this milestone:

```text
The explicit pipeline artifacts can be transformed into a deterministic Management Cockpit KPI view model.
```

This is a major preparation step for the actual GUI screen.

The system now has:

```text
planning execution
    ↓
reporting stack
    ↓
issue and Cost / KPI enrichment
    ↓
view model for management cockpit
```

---

## 25. Current Pipeline Position

The staged integration now stands here:

```text
isolated utilities
    ↓
explicit pipeline runner                 ✅ completed
    ↓
feature flag helper                      ✅ completed
    ↓
run_full_plan insertion                  ✅ completed
    ↓
capacity reporting MVP                   ✅ completed
    ↓
capacity report attachment               ✅ completed
    ↓
capacity report export                   ✅ completed
    ↓
issue candidates                         ✅ completed
    ↓
issue candidate export                   ✅ completed
    ↓
Cost / KPI enrichment                    ✅ completed
    ↓
Cost / KPI export                        ✅ completed
    ↓
reporting flag switchboard helper        ✅ completed
    ↓
planning-sequence reporting insertion    ✅ completed
    ↓
Management Cockpit KPI view model        ✅ completed
    ↓
Management Cockpit GUI rendering
```

---

## 26. Current Operational Meaning

WOM can now move from execution artifacts to cockpit-ready information:

```text
env explicit pipeline artifacts
    ↓
build_explicit_pipeline_management_cockpit_view_model(env)
    ↓
read-only management cockpit data structure
```

This means a future GUI can display:

```text
pipeline status
executive KPI estimates
capacity risk summary
issue candidate summary
top business impact issues
replan candidates
health / data quality risks
assumptions summary
export summary
next review actions
```

without recalculating or mutating the plan.

---

## 27. Known Limitations

This milestone is intentionally limited.

It does not implement:

```text
Tk rendering
Management Cockpit window
button integration
interactive filtering
file open links
issue review workflow
knowledge capture
automatic replanning
ReplanCommand execution
OR optimization
database persistence
```

It only builds the data model for future display.

---

## 28. Future Milestones

### 28.1 Read-only Tk rendering

A natural next implementation phase is to render this view model in a read-only Tk window.

Possible method:

```python
_open_explicit_pipeline_kpi_view(self)
```

Possible design document:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_view_tk_rendering.md
```

### 28.2 Button / menu integration

After rendering is safe, a button or menu item can be added to open the view.

Important rule:

```text
The button should open the view only.
It should not run planning.
It should not run exports.
It should not execute replan commands.
```

### 28.3 Review workflow

Later, the cockpit may support review workflows such as:

```text
mark issue reviewed
promote to open issue
create decision log candidate
generate next-entry prompt
```

These should be controlled by separate design and feature flags.

### 28.4 Knowledge Continuity integration

The view model can later provide structured inputs to the WOM Knowledge Continuity Layer.

Potential mapping:

```text
top impact issues → open issues
health warnings → facts and findings
replan candidates → next-entry prompts
management decisions → decision log candidates
```

This is not implemented in this milestone.

---

## 29. Summary

The Explicit Pipeline Management Cockpit KPI View Model MVP is complete.

The key achievement is:

```text
WOM now has a deterministic, read-only Management Cockpit view model
built from explicit pipeline report / issue / Cost-KPI artifacts.
```

The implementation remains safely non-invasive:

```text
no GUI rendering
no cockpit_tk.py changes
no planning execution
no export execution
no command execution
```

The cockpit now has its signal model.

The next phase can attach actual meters to the panel.
