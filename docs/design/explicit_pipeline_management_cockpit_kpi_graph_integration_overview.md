# Explicit Pipeline Management Cockpit KPI Graph Integration Overview

**Version:** v0r1 overview  
**Date:** 2026-05-25  
**Status:** Overview memo  
**Target path:** `docs/design/explicit_pipeline_management_cockpit_kpi_graph_integration_overview.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo provides an overview of the completed **Explicit Pipeline Management Cockpit KPI Graph Integration** work.

The graph integration extends the previously completed Explicit Pipeline KPI View from:

```text
table / key-value cockpit
```

to:

```text
table / key-value cockpit
    +
graph / chart cockpit
```

The completed graph chain is:

```text
Management Cockpit KPI view model
    ↓
Graph view model
    ↓
Tk Canvas chart rendering
    ↓
Graphs tab in Explicit KPI View
```

The key result is:

```text
Explicit KPI View now includes a Graphs tab with simple Tk Canvas charts.
```

This is a read-only management visualization layer.

It does not execute planning, exports, or replanning.

---

## 2. Background

Before the graph integration, WOM had already completed the following management cockpit chain:

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

At that point, users could open the Explicit KPI View from the main GUI and inspect:

```text
Summary
Top Issues
Replan Candidates
Health
Assumptions / Exports
Messages
```

Those tabs were useful, but primarily table-based.

The graph integration adds visual management summaries to the same window.

---

## 3. Graph Integration Scope

The graph integration was intentionally staged.

Completed stages:

```text
1. Graph View design
2. Graph View Model MVP
3. Graph View Model completion memo
4. Canvas Rendering / Graphs tab design
5. Canvas Rendering / Graphs tab Codex request
6. Canvas Rendering / Graphs tab implementation
7. Canvas Rendering / Graphs tab completion memo
```

This overview memo closes that graph integration cycle.

---

## 4. Completed Design Documents

The graph integration is supported by the following design documents:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_graph_view.md
docs/design/explicit_pipeline_management_cockpit_kpi_graph_view_completion.md
docs/design/explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.md
docs/design/explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering_completion.md
```

Related integration overview:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_integration_overview.md
```

---

## 5. Completed Codex Requests

The graph integration used the following Codex requests:

```text
docs/codex_requests/explicit_pipeline_management_cockpit_kpi_graph_view_request.md
docs/codex_requests/explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering_request.md
```

The first request implemented chart-ready graph data.

The second request rendered that data as Canvas charts.

---

## 6. Graph View Model MVP

The graph-view-model builder was implemented in:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

Main function:

```python
build_explicit_pipeline_kpi_graph_view_model(view_model: dict) -> dict
```

The function converts the existing Management Cockpit KPI view model into chart-ready data.

It is:

```text
pure
deterministic
read-only
safe for missing values
safe for invalid values
non-mutating
```

It does not:

```text
read env
draw charts
modify GUI layout
run planning
run exports
execute commands
```

---

## 7. Graph Model Schema

The graph model contains:

```text
available
top_impact_bars
severity_distribution
impact_composition
weekly_issue_counts
messages
```

Conceptual schema:

```python
{
    "available": bool,
    "top_impact_bars": list[dict],
    "severity_distribution": {
        "error": int,
        "warning": int,
        "info": int,
    },
    "impact_composition": list[dict],
    "weekly_issue_counts": list[dict],
    "messages": list[str],
}
```

This schema separates graph data preparation from visual rendering.

---

## 8. Graph Data Produced

### 8.1 Top Impact Bars

Source:

```python
view_model["top_impact_issues"]
```

Metric:

```text
estimated_total_business_impact
```

Purpose:

```text
show which issue candidates have the largest directional business impact
```

The result is sorted and limited to top 10 rows.

---

### 8.2 Severity Distribution

Source:

```python
view_model["issue_summary"]
```

Fields:

```text
error_count
warning_count
info_count
```

Purpose:

```text
show risk severity distribution
```

---

### 8.3 Impact Composition

Source:

```python
view_model["executive_kpi_summary"]
```

Rows:

```text
Lost Sales
Margin Impact
Inventory Cost
Capacity Cost
Service Penalty
```

Purpose:

```text
show directional Cost / KPI impact composition
```

---

### 8.4 Weekly Issue Counts

Source:

```python
view_model["top_impact_issues"]
```

Grouping field:

```text
week
```

Purpose:

```text
show when issue pressure appears in the planning horizon
```

---

## 9. Graph View Model Tests

Focused test file:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_graph_view.py
```

Covered cases:

```text
no-data unavailable behavior
top impact sorting / labels / fields
top-10 limit
severity distribution
impact composition rows
weekly issue counts
input view_model not mutated
missing / invalid values safe defaults
```

Observed final local result:

```text
8 passed
```

---

## 10. Canvas Rendering / Graphs Tab MVP

The Canvas rendering layer was implemented in:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

It added a new tab:

```text
Graphs
```

inside the existing Explicit KPI View renderer:

```python
render_explicit_pipeline_management_cockpit_tk(parent, view_model)
```

The Graphs tab is built by reusing:

```python
build_explicit_pipeline_kpi_graph_view_model(view_model)
```

No new public API was required.

No public function signature was changed.

---

## 11. Graphs Tab Placement

The Graphs tab is placed immediately after:

```text
Summary
```

The resulting tab order is:

```text
Summary
Graphs
Top Issues
Replan Candidates
Health
Assumptions / Exports
Messages
```

This placement is intentional.

Graphs are management summary visuals, so they should appear close to Summary.

---

## 12. Graphs Tab Layout

The Graphs tab uses a 2x2 layout.

Implemented chart panels:

```text
Top Business Impact
Cost / KPI Impact Composition
Issue Severity Distribution
Weekly Issue Count
```

Each chart is rendered using:

```text
tk.Canvas
```

The layout is simple, compact, and safe for MVP use.

---

## 13. Charts Implemented

### 13.1 Top Business Impact

Chart type:

```text
horizontal bar chart
```

Data source:

```python
graph_model["top_impact_bars"]
```

Meaning:

```text
largest issue candidates by estimated directional impact
```

---

### 13.2 Cost / KPI Impact Composition

Chart type:

```text
horizontal bar chart
```

Data source:

```python
graph_model["impact_composition"]
```

Meaning:

```text
composition of estimated business impact
```

---

### 13.3 Issue Severity Distribution

Chart type:

```text
simple bar chart
```

Data source:

```python
graph_model["severity_distribution"]
```

Meaning:

```text
error / warning / info distribution
```

---

### 13.4 Weekly Issue Count

Chart type:

```text
simple bar chart
```

Data source:

```python
graph_model["weekly_issue_counts"]
```

Meaning:

```text
issue count by week
```

---

## 14. Canvas Rendering Helpers

The implementation added private helper functions such as:

```text
_truncate_label
_draw_chart_message
_draw_horizontal_bar_chart
_draw_distribution_bar_chart
_create_canvas_chart_frame
_create_graphs_tab
```

The helpers use only standard Tk Canvas primitives:

```text
create_text
create_rectangle
create_line
```

No matplotlib was introduced.

No new dependency was added.

---

## 15. Empty-State Handling

The Graphs tab renders safely when graph data is missing.

Examples:

```text
No top impact issues are available.
No Cost / KPI impact composition is available.
No issue severity counts are available.
No week-level issue data is available.
```

If the underlying view model is unavailable, the tab still opens.

This preserves the user experience rule:

```text
The Explicit KPI View can be opened before planning data exists.
```

---

## 16. Graph Notes / Caveats

The Graphs tab displays graph-model messages as notes.

Important caveats include:

```text
Cost / KPI values are directional scenario estimates, not formal accounting values.
Double counting may be possible depending on assumptions.
```

This prevents visual charts from being mistaken for formal accounting reports.

The Graphs tab is a management attention view, not a statutory financial statement.

---

## 17. Canvas Rendering Tests

Focused test file:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.py
```

Covered cases:

```text
Graphs tab appears
empty model renders safely
populated model renders safely
core tabs are preserved
input view_model is not mutated by rendering
```

Observed final local result:

```text
5 passed
```

Related local validation:

```text
Graph View Model: 8 passed
Button Integration: 1 passed
Tk Rendering: 2 passed, 1 skipped
KPI View Model: 8 passed
Reporting Stack Insertion: 7 passed
Reporting Flags: 10 passed
Covid Vaccine optional: 1 passed
```

The Tk rendering skip is acceptable because Tk rendering tests can be environment-sensitive.

---

## 18. Safety Boundary

The graph integration preserved the same safety boundary as the rest of the Explicit KPI View.

It did not add:

```text
planning execution
Run Full Plan execution
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
new GUI button
new menu entry
matplotlib dependency
```

The Graphs tab only:

```text
reads view_model
builds graph_model
draws Canvas charts
```

Core rule:

```text
Draw the instruments.
Do not start the engine.
```

---

## 19. Current Runtime Architecture

The current runtime path is now:

```text
WOMCockpit
    ├─ Run Full Plan / planning sequence
    │      └─ explicit pipeline reporting stack attaches artifacts to env
    │
    └─ Explicit KPI View button
           └─ _open_explicit_pipeline_kpi_view()
                  ├─ build_explicit_pipeline_management_cockpit_view_model(self.env)
                  └─ render_explicit_pipeline_management_cockpit_tk(self, view_model)
                         ├─ Summary tab
                         ├─ Graphs tab
                         │      ├─ build_explicit_pipeline_kpi_graph_view_model(view_model)
                         │      ├─ Top Business Impact chart
                         │      ├─ Cost / KPI Impact Composition chart
                         │      ├─ Issue Severity Distribution chart
                         │      └─ Weekly Issue Count chart
                         ├─ Top Issues tab
                         ├─ Replan Candidates tab
                         ├─ Health tab
                         ├─ Assumptions / Exports tab
                         └─ Messages tab
```

The execution path and view path remain separated.

---

## 20. Current User Experience

A user can now:

```text
Run planning
    ↓
Click Explicit KPI View
    ↓
Inspect Summary tab
    ↓
Inspect Graphs tab
    ↓
Inspect Top Issues / Replan / Health / Assumptions / Messages tabs
```

The Graphs tab gives fast visual answers to:

```text
What is the largest impact?
What is the impact composition?
How severe are the issues?
Which weeks are stressed?
```

This is a significant improvement over table-only review.

---

## 21. Why This Matters

The graph integration moves WOM closer to a management cockpit.

Before:

```text
The cockpit showed evidence as tables and key-value records.
```

After:

```text
The cockpit also shows visual management signals.
```

This helps managers review complex planning outputs faster.

It also creates a foundation for future KPI cards, waterfall charts, heatmaps, and Knowledge Continuity handoff.

---

## 22. Known Limitations

The graph integration is intentionally simple.

It does not yet include:

```text
KPI cards
waterfall chart
capacity heatmap
severity trend chart
interactive filtering
hover tooltips
click bar to select issue
copy chart to clipboard
export graph image
dark mode styling
advanced scaling
custom colors
formal accounting reconciliation
```

The current charts are MVP instruments, not the final cockpit dashboard.

---

## 23. Recommended Next Enhancements

### 23.1 KPI Cards

Potential design document:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_cards.md
```

Potential cards:

```text
Total Business Impact
Capacity Violations
Management Issues
Health Warnings
Replan Candidates
```

Cards should appear near Summary or at the top of Graphs.

---

### 23.2 Cost / KPI Waterfall

Potential design document:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_waterfall.md
```

Potential structure:

```text
Lost Sales
Margin Impact
Inventory Cost
Capacity Cost
Service Penalty
Total
```

This would improve management storytelling.

---

### 23.3 Capacity Heatmap

Potential design document:

```text
docs/design/explicit_pipeline_management_cockpit_capacity_heatmap.md
```

Potential axes:

```text
node x week
```

This requires richer capacity-detail exposure in the view model.

---

### 23.4 Drilldown / Detail Pane

Potential design document:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_drilldown.md
```

Possible behavior:

```text
click chart bar
show related issue detail
highlight related table row
copy issue summary
```

First phase should remain read-only.

---

### 23.5 Knowledge Continuity Handoff

Potential design document:

```text
docs/design/explicit_pipeline_management_cockpit_knowledge_continuity_handoff.md
```

Possible mapping:

```text
top impact issues → open issues
health warnings → facts and findings
replan candidates → next-entry prompts
user comments → decision log candidates
```

This should remain explicitly controlled and feature-gated.

---

## 24. Completed Commit Milestones

Key final graph integration commits:

```text
443652f Add explicit pipeline KPI graph view model builder MVP
1eae8ce Add explicit pipeline management cockpit KPI graph view completion memo
d5b86f9 Add explicit KPI Graphs tab with Tk canvas charts
17f04f4 Add explicit pipeline management cockpit KPI graph canvas rendering completion memo
```

The related design / request commits include:

```text
83a00eb Add explicit pipeline management cockpit KPI graph view design
463a661 Add explicit pipeline management cockpit KPI graph view Codex request
c2ff994 Add explicit pipeline management cockpit KPI graph canvas rendering design
4781d92 Add explicit pipeline management cockpit KPI graph canvas rendering Codex request
```

---

## 25. Summary

The Explicit Pipeline Management Cockpit KPI Graph Integration is complete through Canvas rendering MVP.

The current state is:

```text
Explicit KPI View
    ├─ Summary
    ├─ Graphs
    ├─ Top Issues
    ├─ Replan Candidates
    ├─ Health
    ├─ Assumptions / Exports
    └─ Messages
```

The Graphs tab includes:

```text
Top Business Impact
Cost / KPI Impact Composition
Issue Severity Distribution
Weekly Issue Count
```

The integration remains safely read-only:

```text
no planning execution
no export execution
no replan execution
no feature flag mutation
```

WOM now has a visible management instrument panel for explicit pipeline KPI evidence.

The next frontier is refinement: KPI cards, waterfall, heatmap, and drilldown.
