# Explicit Pipeline Management Cockpit KPI Graph View Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-24  
**Status:** Completion memo  
**Target path:** `docs/design/explicit_pipeline_management_cockpit_kpi_graph_view_completion.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Explicit Pipeline Management Cockpit KPI Graph View Model MVP**.

The purpose of this milestone was to implement the first graph / chart view layer as a **pure graph-view-model builder**, not as a chart renderer.

The completed function is:

```python
build_explicit_pipeline_kpi_graph_view_model(view_model: dict) -> dict
```

implemented in:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

This milestone creates chart-ready data from the already-completed Management Cockpit KPI view model.

It does not yet draw charts.

It does not yet add a Graphs tab.

---

## 2. Background

Before this milestone, WOM had already completed the following cockpit integration chain:

```text
explicit pipeline runner
    ↓
reporting stack
    ↓
issue candidates
    ↓
Cost / KPI enrichment
    ↓
Cost / KPI export
    ↓
planning-sequence insertion
    ↓
Management Cockpit KPI view model
    ↓
read-only Tk rendering helper
    ↓
Explicit KPI View button
```

The current `Explicit KPI View` can show:

```text
Summary
Top Issues
Replan Candidates
Health
Assumptions / Exports
Messages
```

as a read-only table / key-value cockpit view.

This milestone prepares the next visual layer by deriving a graph-ready model from that existing view model.

---

## 3. Implemented Files

This milestone modified or added:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
tests/test_explicit_pipeline_management_cockpit_kpi_graph_view.py
```

The implementation was committed as:

```text
443652f Add explicit pipeline KPI graph view model builder MVP
```

---

## 4. Main Implemented Function

The new graph-view-model builder is:

```python
build_explicit_pipeline_kpi_graph_view_model(view_model: dict) -> dict
```

The function:

```text
reads the existing Management Cockpit KPI view model
extracts chart-ready data
returns a deterministic graph model dictionary
handles missing / invalid values safely
does not mutate the input view_model
```

It is a pure transformation layer.

It does not read `env`.

It does not draw charts.

It does not modify GUI layout.

---

## 5. Graph Model Schema Implemented

The graph model includes:

```text
available
top_impact_bars
severity_distribution
impact_composition
weekly_issue_counts
messages
```

Conceptually:

```python
{
    "available": bool,
    "top_impact_bars": [...],
    "severity_distribution": {
        "error": int,
        "warning": int,
        "info": int,
    },
    "impact_composition": [...],
    "weekly_issue_counts": [...],
    "messages": [...],
}
```

This schema is designed for future chart rendering.

---

## 6. Availability Behavior

If the input view model is unavailable:

```python
view_model.get("available") is False
```

or if an empty dictionary is passed, the graph model returns safe defaults:

```text
available = False
top_impact_bars = []
severity_distribution = {"error": 0, "warning": 0, "info": 0}
impact_composition = []
weekly_issue_counts = []
messages include no-data explanation
```

No exception is raised.

This keeps future rendering safe even when the user opens the view before running planning.

---

## 7. Top Impact Bars

The graph model builds:

```text
top_impact_bars
```

from:

```python
view_model["top_impact_issues"]
```

Each bar record includes fields such as:

```text
label
value
severity
issue_type
node
week
```

The value is derived from:

```text
estimated_total_business_impact
```

with safe float conversion.

Labels are generated from:

```text
issue_type
node
week
```

Example:

```text
capacity_bottleneck / MOM_RICE_MILL_A / W12
```

Sorting is deterministic:

```text
estimated impact descending
severity priority
issue_type
node
week
```

The result is limited to:

```text
top 10 rows
```

---

## 8. Severity Distribution

The graph model builds:

```text
severity_distribution
```

from:

```python
view_model["issue_summary"]
```

Fields used:

```text
error_count
warning_count
info_count
```

Output format:

```python
{
    "error": int,
    "warning": int,
    "info": int,
}
```

Invalid or missing values default to zero.

---

## 9. Impact Composition

The graph model builds:

```text
impact_composition
```

from:

```python
view_model["executive_kpi_summary"]
```

Implemented stable rows:

```text
Lost Sales
Margin Impact
Inventory Cost
Capacity Cost
Service Penalty
```

These map to:

```text
estimated_lost_sales_value_total
estimated_margin_impact_total
estimated_inventory_cost_impact_total
estimated_capacity_cost_impact_total
estimated_service_penalty_total
```

The function always returns the stable five-row structure when the view model is available, using `0.0` as safe default.

This makes future chart rendering simpler.

---

## 10. Weekly Issue Counts

The graph model builds:

```text
weekly_issue_counts
```

from:

```python
view_model["top_impact_issues"]
```

It counts issue rows by week.

Example:

```python
[
    {"week": "12", "count": 2},
    {"week": "13", "count": 1},
]
```

Blank week values are ignored.

Sorting is deterministic and handles numeric-like weeks safely.

---

## 11. Messages

The graph model includes deterministic messages.

It always includes a baseline message such as:

```text
Graph model is derived from the current read-only KPI view model.
```

It also preserves Cost / KPI caveat messages when present in the source view model.

Examples:

```text
Cost / KPI values are directional scenario estimates, not formal accounting values.
Double counting may be possible depending on assumptions.
```

If no top impact bars or no week-level data exist, it adds safe explanatory messages.

---

## 12. Helper Functions Added

The implementation added focused helper functions such as:

```text
_to_int
_make_top_impact_label
_week_sort_key
```

These complement existing helper behavior and support:

```text
safe integer conversion
deterministic chart labels
deterministic week sorting
```

Existing safe float / list / dict helpers are reused where appropriate.

---

## 13. Input Mutation Safety

A key requirement was:

```text
Do not mutate the input view_model.
```

The test suite verifies this using:

```python
copy.deepcopy(view_model)
```

before calling the builder, then comparing the input afterward.

The graph model builder is therefore safe as a read-only transformation.

---

## 14. Safety Boundaries Preserved

This milestone preserved all intended safety boundaries.

It did not modify:

```text
pysi/gui/cockpit_tk.py
```

It did not add:

```text
Canvas rendering
matplotlib rendering
Graphs tab
GUI button
menu entry
planning execution
explicit pipeline execution
reporting stack execution
export execution
feature flag mutation
env mutation
ReplanCommand execution
automatic replanning
OR optimization
database persistence
Knowledge Continuity persistence
```

The milestone is graph-data preparation only.

---

## 15. Tests Added

The focused test file is:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_graph_view.py
```

It covers:

```text
1. no-data unavailable behavior
2. top-impact sorting / labels / field preservation
3. top-10 limit
4. severity distribution from issue_summary
5. impact composition rows
6. weekly issue counts
7. input view_model not mutated
8. missing / invalid value safety
```

---

## 16. Validation

The focused graph-view-model test passed:

```bat
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_graph_view.py
```

Observed result:

```text
8 passed
```

The following related tests also passed:

```bat
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_view_button_integration.py
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_view.py
python -m pytest tests/test_explicit_pipeline_reporting_stack_insertion.py
python -m pytest tests/test_explicit_pipeline_reporting_flags.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results:

```text
button integration: 1 passed
Tk rendering: 2 passed, 1 skipped
KPI view model: 8 passed
Reporting stack insertion: 7 passed
Reporting flags: 10 passed
Covid vaccine optional: 1 passed
```

The `1 skipped` in Tk rendering is acceptable because Tk rendering tests can be environment-sensitive.

No failures or errors remained at commit time.

---

## 17. Completion Criteria

This milestone satisfies the intended completion criteria.

```text
[OK] build_explicit_pipeline_kpi_graph_view_model(view_model) exists
[OK] function returns graph-ready dict
[OK] graph model contains available
[OK] graph model contains top_impact_bars
[OK] graph model contains severity_distribution
[OK] graph model contains impact_composition
[OK] graph model contains weekly_issue_counts
[OK] graph model contains messages
[OK] missing data is handled safely
[OK] top impact bars are sorted and limited to top 10
[OK] severity distribution is derived from issue_summary
[OK] impact composition is derived from executive_kpi_summary
[OK] weekly issue counts are derived from top_impact_issues
[OK] input view_model is not mutated
[OK] focused tests pass
[OK] existing view-model / rendering / button tests pass
[OK] no cockpit_tk.py modification
[OK] no Canvas rendering
[OK] no Graphs tab added
[OK] no planning / export / replan execution
```

---

## 18. Meaning of This Milestone

Before this milestone:

```text
WOM had a read-only Explicit KPI View, but no chart-ready graph model.
```

After this milestone:

```text
WOM has a deterministic graph model derived from the read-only KPI view model.
```

This means the next rendering layer can draw charts without reinterpreting raw planning objects.

The data path is now:

```text
explicit pipeline artifacts
    ↓
Management Cockpit KPI view model
    ↓
Graph view model
    ↓
future chart rendering
```

---

## 19. Current Pipeline Position

The staged integration now stands here:

```text
isolated utilities
    ↓
explicit pipeline runner                         ✅ completed
    ↓
feature flag helper                              ✅ completed
    ↓
run_full_plan insertion                          ✅ completed
    ↓
capacity reporting MVP                           ✅ completed
    ↓
capacity report attachment                       ✅ completed
    ↓
capacity report export                           ✅ completed
    ↓
issue candidates                                 ✅ completed
    ↓
issue candidate export                           ✅ completed
    ↓
Cost / KPI enrichment                            ✅ completed
    ↓
Cost / KPI export                                ✅ completed
    ↓
reporting flag switchboard helper                ✅ completed
    ↓
planning-sequence reporting insertion            ✅ completed
    ↓
Management Cockpit KPI view model                ✅ completed
    ↓
read-only Tk rendering helper                    ✅ completed
    ↓
cockpit_tk.py entry point / button integration   ✅ completed
    ↓
Graph view model                                 ✅ completed
    ↓
Canvas graph rendering / Graphs tab
```

---

## 20. Current Operational Meaning

WOM can now derive graph-ready information such as:

```text
top impact bars
severity distribution
Cost / KPI impact composition
weekly issue counts
```

from the existing read-only KPI view model.

This makes the future chart renderer simple and safe.

The graph model is still read-only and does not affect planning behavior.

---

## 21. Known Limitations

This milestone intentionally does not implement:

```text
actual chart rendering
Canvas drawing
matplotlib drawing
Graphs tab integration
KPI cards
waterfall chart
capacity heatmap
interactive filtering
row-detail links
copy-to-clipboard
Knowledge Continuity capture
```

It only prepares chart-ready data.

---

## 22. Future Milestones

### 22.1 Canvas graph rendering

A natural next design / implementation phase is:

```text
Canvas-based rendering helper
```

Potential future design document:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.md
```

This would draw simple bar charts from the graph model.

### 22.2 Graphs tab integration

After Canvas rendering is stable, add:

```text
Graphs
```

tab to the existing Explicit KPI View window.

Recommended tab order:

```text
Summary
Graphs
Top Issues
Replan Candidates
Health
Assumptions / Exports
Messages
```

### 22.3 KPI cards

Add compact visual KPI cards:

```text
Total Business Impact
Capacity Violations
Management Issues
Health Warnings
Replan Candidates
```

### 22.4 Waterfall / heatmap

Future advanced charts:

```text
Cost / KPI impact waterfall
capacity violation by week / node heatmap
issue severity trend
```

These should remain separate phases.

---

## 23. Summary

The Explicit Pipeline Management Cockpit KPI Graph View Model MVP is complete.

The key achievement is:

```text
WOM now has a pure, deterministic graph-view-model builder
derived from the read-only Explicit KPI view model.
```

The milestone remains safely non-invasive:

```text
no GUI layout change
no cockpit_tk.py change
no chart drawing
no planning execution
no export execution
no replan execution
```

The chart signal model is ready.

The next phase can draw the instruments.
