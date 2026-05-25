# Explicit Pipeline Management Cockpit KPI Graph View Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-24  
**Status:** Design memo  
**Target path:** `docs/design/explicit_pipeline_management_cockpit_kpi_graph_view.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/explicit_pipeline_management_cockpit_kpi_integration_overview.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view_completion.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view_tk_rendering.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view_tk_rendering_completion.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view_button_integration.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view_button_integration_completion.md`
- `docs/design/explicit_pipeline_reporting_issue_cost_kpi_overview.md`
- `docs/design/explicit_pipeline_issue_candidate_cost_kpi_enrichment.md`
- `docs/design/wom_knowledge_continuity_layer.md`

---

## 1. Purpose

This memo defines the design for adding a **Graph / Chart View** to the Explicit Pipeline Management Cockpit KPI View.

The current cockpit view is already integrated into the main WOM GUI through:

```text
Explicit KPI View button
    ↓
Management Cockpit KPI view model
    ↓
read-only Tk rendering helper
    ↓
tabular / key-value cockpit view
```

The next enhancement is to add visual charts so that managers can understand the most important planning issues faster.

This design is for:

```text
view_model
    ↓
chart-ready data extraction
    ↓
read-only graph / chart rendering
```

It is not for:

```text
planning execution
export execution
replanning
optimization
Knowledge Continuity persistence
```

---

## 2. Current Completed State

The completed cockpit chain is:

```text
explicit pipeline runner
    ↓
reporting stack
    ↓
issue candidates
    ↓
Cost / KPI enrichment
    ↓
planning-sequence insertion
    ↓
Management Cockpit KPI view model
    ↓
read-only Tk rendering helper
    ↓
Explicit KPI View button
```

The current UI displays:

```text
Summary
Top Issues
Replan Candidates
Health
Assumptions / Exports
Messages
```

using:

```text
ttk.Notebook tabs
Treeview tables
key-value sections
read-only message lists
```

The current view is a safe table / diagnostic cockpit.

The next step is to add graphical summaries.

---

## 3. Design Goal

The goal is to add a graph view that makes the following visible at a glance:

```text
1. Which issues have the largest business impact?
2. What is the Cost / KPI impact composition?
3. How many issues exist by severity?
4. Where and when capacity violations occur?
5. How many health / data-quality risks exist?
```

The graph view should help answer:

```text
Where should management look first?
```

The graph view should remain read-only.

---

## 4. Non-Goals

This design does not implement:

```text
planning execution
Run Full Plan execution
explicit pipeline execution
reporting stack execution
export execution
Cost / KPI recalculation
issue candidate generation
automatic replanning
ReplanCommand execution
OR optimization
database persistence
Knowledge Continuity persistence
formal accounting dashboard
interactive approval workflow
```

The graph view is display-only.

---

## 5. Core Safety Rule

The graph view must follow the same safety rule as the existing KPI view:

```text
Display what exists.
Do not execute anything.
```

It may:

```text
read the existing view_model
derive chart-ready rows
render charts
```

It must not:

```text
run planning
run exports
change flags
execute commands
mutate env
```

---

## 6. Recommended Implementation Direction

The safest approach is to extend the existing module:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

with graph-view helpers that consume the already-built view model.

Recommended new functions:

```python
build_explicit_pipeline_kpi_graph_view_model(view_model: dict) -> dict
render_explicit_pipeline_kpi_graphs_tk(parent, graph_model: dict) -> tk.Frame
```

or, if simpler:

```python
add_explicit_pipeline_kpi_graph_tab(notebook, view_model: dict) -> None
```

Recommended first implementation:

```text
Add a Graphs tab to the existing Explicit KPI View window.
```

This avoids adding a second button and keeps the user flow simple:

```text
Explicit KPI View button
    ↓
same KPI window
    ↓
new Graphs tab
```

---

## 7. Recommended Graph Tab

Add a new tab to the existing `ttk.Notebook`:

```text
Graphs
```

Potential tab order:

```text
Summary
Graphs
Top Issues
Replan Candidates
Health
Assumptions / Exports
Messages
```

Reason:

```text
Graphs should appear near Summary because they are high-level management views.
```

If implementation risk is high, it is also acceptable to append `Graphs` after existing tabs.

---

## 8. Chart Technology Options

### 8.1 Preferred MVP: Tk Canvas / ttk-based simple charts

Use `tk.Canvas` to draw simple bar charts.

Pros:

```text
no additional dependency
works with standard Tk
easier to test as widget creation
avoids matplotlib backend issues
lightweight
```

Cons:

```text
less polished
manual layout required
```

### 8.2 Alternative: matplotlib FigureCanvasTkAgg

Pros:

```text
polished charts
familiar plotting
supports future waterfall / bar / pie charts
```

Cons:

```text
heavier dependency
backend issues in tests
existing tests already needed matplotlib stubs
more fragile in CI
```

### 8.3 Recommended choice

For MVP, prefer:

```text
Tk Canvas simple charts
```

because this project has already encountered Tk / matplotlib environment sensitivity.

Matplotlib can be introduced later if richer visuals are needed.

---

## 9. Recommended First Chart Set

The first Graph View should implement a small, management-friendly chart set.

Recommended MVP charts:

```text
1. Top Business Impact Bar Chart
2. Issue Severity Distribution
3. Cost / KPI Impact Composition
4. Capacity Violation / Issue Count by Week
```

Do not implement too many charts at once.

A cockpit should illuminate the runway, not recreate Times Square.

---

## 10. Chart 1: Top Business Impact Bar Chart

### 10.1 Purpose

Show the top issue candidates by estimated business impact.

### 10.2 Source

```python
view_model["top_impact_issues"]
```

### 10.3 Metric

```text
estimated_total_business_impact
```

### 10.4 Category label

Recommended label priority:

```text
issue_type + node + week
```

Example:

```text
capacity_bottleneck / MOM_RICE_MILL_A / W12
```

### 10.5 Sort

Use the same order as `top_impact_issues`.

### 10.6 Max bars

Recommended:

```text
Top 5
```

or:

```text
Top 10 if space allows
```

### 10.7 Empty state

If no top issues exist:

```text
No top impact issues are available.
```

---

## 11. Chart 2: Issue Severity Distribution

### 11.1 Purpose

Show management risk level distribution.

### 11.2 Source

Use combined issue rows from:

```text
top_impact_issues
replan_candidates
health_summary.top_health_issues
```

or, if available in issue summary:

```text
issue_summary.error_count
issue_summary.warning_count
issue_summary.info_count
```

### 11.3 Recommended MVP source

Use:

```python
view_model["issue_summary"]
```

Fields:

```text
error_count
warning_count
info_count
```

### 11.4 Chart type

Simple horizontal or vertical bar chart:

```text
Error
Warning
Info
```

### 11.5 Empty state

If all counts are zero:

```text
No issue severity counts are available.
```

---

## 12. Chart 3: Cost / KPI Impact Composition

### 12.1 Purpose

Show the composition of estimated business impact.

### 12.2 Source

```python
view_model["executive_kpi_summary"]
```

Fields:

```text
estimated_lost_sales_value_total
estimated_margin_impact_total
estimated_inventory_cost_impact_total
estimated_capacity_cost_impact_total
estimated_service_penalty_total
```

### 12.3 Chart type

Recommended MVP:

```text
horizontal bar chart
```

or key-value bar set.

Avoid complex stacked waterfall in MVP.

### 12.4 Caveat display

Always show:

```text
Directional scenario estimate, not formal accounting.
Double counting may be possible depending on assumptions.
```

when the KPI summary indicates directional values.

### 12.5 Empty state

If all impact components are zero:

```text
No Cost / KPI impact composition is available.
```

---

## 13. Chart 4: Capacity Violation / Issue Count by Week

### 13.1 Purpose

Show when planning pressure occurs.

### 13.2 Source options

Preferred source:

```python
view_model["top_impact_issues"]
```

using rows with:

```text
week
issue_type
severity
```

Alternative source:

```text
capacity report records
```

but those are not currently exposed directly in the view model.

### 13.3 MVP source

Use `top_impact_issues` week values.

Count rows per week.

### 13.4 Chart type

Simple bar chart:

```text
Week → issue count
```

### 13.5 Empty state

If no week values exist:

```text
No week-level issue data is available.
```

---

## 14. Optional Future Chart: Cost / KPI Waterfall

A future graph phase may implement:

```text
Cost / KPI Impact Waterfall
```

Showing:

```text
lost sales
margin impact
inventory cost impact
capacity cost impact
service penalty
total directional impact
```

This is useful for management storytelling.

However, waterfall chart layout is more complex.

Recommended status:

```text
future phase
```

not MVP.

---

## 15. Optional Future Chart: Capacity Heatmap

A future graph phase may implement:

```text
node x week capacity issue heatmap
```

Useful for:

```text
bottleneck node visibility
weekly pressure pattern
```

However, it requires richer capacity report records in the view model.

Recommended status:

```text
future phase
```

---

## 16. Chart Data Model

Recommended graph model schema:

```python
{
    "available": bool,
    "top_impact_bars": [
        {
            "label": str,
            "value": float,
            "severity": str,
            "issue_type": str,
            "node": str,
            "week": str,
        }
    ],
    "severity_distribution": {
        "error": int,
        "warning": int,
        "info": int,
    },
    "impact_composition": [
        {"label": "Lost Sales", "value": float},
        {"label": "Margin Impact", "value": float},
        {"label": "Inventory Cost", "value": float},
        {"label": "Capacity Cost", "value": float},
        {"label": "Service Penalty", "value": float},
    ],
    "weekly_issue_counts": [
        {"week": str, "count": int}
    ],
    "messages": [str],
}
```

This graph model should be derived from the existing cockpit view model.

---

## 17. New Helper: Graph Model Builder

Recommended function:

```python
def build_explicit_pipeline_kpi_graph_view_model(view_model: dict) -> dict:
    ...
```

This function should be pure and easily testable.

It should:

```text
read the existing view model
extract top impact bars
compute severity distribution
build impact composition rows
count top issues by week
return safe defaults
```

It should not:

```text
read env
run planning
run exports
mutate input view_model
```

---

## 18. New Helper: Canvas Chart Rendering

Recommended small rendering helpers:

```python
_create_simple_bar_chart(parent, title, rows, label_key="label", value_key="value")
_create_count_bar_chart(parent, title, counts)
_create_empty_chart_message(parent, message)
```

Use `tk.Canvas` or `ttk.Frame` + labels.

A simple Canvas bar chart can draw:

```text
title
axis labels
bars
values
```

Keep it robust and readable, not mathematically perfect.

---

## 19. Formatting Rules

### 19.1 Numeric values

Use existing `_format_value` if available.

For chart labels:

```text
1,250,000
```

not:

```text
1250000.0
```

### 19.2 Negative values

If negative values appear, support them safely.

MVP option:

```text
use absolute max scale
draw negative bars in same direction but label with negative value
```

Future option:

```text
center zero axis
```

For MVP, most impact values are expected to be non-negative directional magnitudes.

### 19.3 Very long labels

Truncate labels safely:

```text
max 40 characters
```

with ellipsis:

```text
...
```

The full label may remain in the table view.

---

## 20. Graph Tab Layout

Recommended layout:

```text
Graphs tab
    ├─ Top Business Impact
    ├─ Impact Composition
    ├─ Issue Severity Distribution
    └─ Weekly Issue Count
```

Use a vertical scrollable frame if possible.

If scrollable frame is too much for MVP, arrange charts in a 2x2 grid:

```text
Top Impact                 Impact Composition
Severity Distribution       Weekly Issue Count
```

Recommended MVP:

```text
2x2 grid of simple chart frames
```

Window size is already large enough from current renderer.

---

## 21. Empty State Behavior

The Graphs tab should render even when no graph data exists.

Empty messages:

```text
No top impact issues are available.
No Cost / KPI impact composition is available.
No issue severity counts are available.
No week-level issue data is available.
```

The view should not crash.

---

## 22. Test Strategy

Add focused tests for the graph model builder first.

Recommended tests:

```text
1. no data view model
2. populated top impact issues
3. severity distribution from issue_summary
4. impact composition from executive_kpi_summary
5. weekly issue counts from top_impact_issues
6. input view_model not mutated
```

Rendering tests can be lighter because Tk drawing is environment-sensitive.

If graph rendering is implemented in the same phase, add smoke tests with safe Tk skip behavior.

---

## 23. Recommended Test File

Add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_graph_view.py
```

Potential focused tests:

```python
def test_graph_model_no_data():
    ...

def test_graph_model_top_impact_bars_sorted_and_limited():
    ...

def test_graph_model_severity_distribution():
    ...

def test_graph_model_impact_composition():
    ...

def test_graph_model_weekly_issue_counts():
    ...

def test_graph_model_does_not_mutate_input():
    ...
```

If rendering is added:

```python
def test_render_graph_tab_smoke_or_skip():
    ...
```

---

## 24. Recommended Implementation Phase Split

### Phase A: Graph model only

Implement:

```python
build_explicit_pipeline_kpi_graph_view_model(view_model)
```

and tests.

No Tk rendering changes.

### Phase B: Graph rendering helper

Add Canvas-based rendering helpers and Graphs tab.

### Phase C: Usability refinement

Add layout polish, label truncation, value formatting, and detail text.

### Phase D: Future charts

Add waterfall / heatmap / KPI cards.

---

## 25. Recommended First Codex Request Scope

Recommended first Codex request:

```text
Graph model only
```

Files:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
tests/test_explicit_pipeline_management_cockpit_kpi_graph_view.py
```

Do not modify:

```text
pysi/gui/cockpit_tk.py
```

Do not add rendering yet in the first graph request unless the user explicitly wants graph display immediately.

Reason:

```text
Graph data correctness should be verified before drawing charts.
```

This follows the same successful staged approach:

```text
view model first
rendering second
button integration third
```

---

## 26. Completion Criteria for This Design

This design is complete when it defines:

```text
[OK] purpose of graph view
[OK] safety boundaries
[OK] non-goals
[OK] recommended MVP charts
[OK] source fields from existing view model
[OK] graph model schema
[OK] graph model builder
[OK] chart rendering options
[OK] empty-state behavior
[OK] test strategy
[OK] phased implementation plan
[OK] recommended first Codex request scope
```

---

## 27. Summary

The current Explicit KPI View is a read-only table / key-value cockpit.

The Graph / Chart View should add management-friendly visual summaries.

Recommended MVP graph set:

```text
Top Business Impact Bar Chart
Issue Severity Distribution
Cost / KPI Impact Composition
Weekly Issue Count
```

Recommended implementation sequence:

```text
graph model first
Canvas-based rendering second
integration into Graphs tab third
```

The core rule remains:

```text
Draw the instruments.
Do not start the engine.
```
