# Explicit Pipeline Management Cockpit KPI Graph Canvas Rendering Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-24  
**Status:** Design memo  
**Target path:** `docs/design/explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/explicit_pipeline_management_cockpit_kpi_integration_overview.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_graph_view.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_graph_view_completion.md`
- `docs/codex_requests/explicit_pipeline_management_cockpit_kpi_graph_view_request.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view_tk_rendering.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view_button_integration.md`
- `docs/design/explicit_pipeline_reporting_issue_cost_kpi_overview.md`
- `docs/design/wom_knowledge_continuity_layer.md`

---

## 1. Purpose

This memo defines the design for adding **Canvas-based graph rendering** and a **Graphs tab** to the Explicit Pipeline Management Cockpit KPI View.

The previous milestone completed the graph-view-model builder:

```python
build_explicit_pipeline_kpi_graph_view_model(view_model: dict) -> dict
```

implemented in:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

This design covers the next step:

```text
Management Cockpit KPI view model
    ↓
Graph view model
    ↓
Tk Canvas graph rendering
    ↓
Graphs tab in Explicit KPI View
```

The goal is to make management-relevant risk and impact signals visible as simple charts.

This design is for **read-only visual rendering**.

It is not for planning execution, export execution, replanning, optimization, or persistence.

---

## 2. Current Completed State

The staged integration currently stands here:

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
Canvas graph rendering / Graphs tab              ← current design target
```

The current Explicit KPI View already opens from the main GUI and displays read-only tabular data.

The next step is to add a **Graphs** tab to the same window.

---

## 3. Design Goal

The goal is to provide simple, read-only, management-friendly charts for the current Explicit KPI View.

The first graph set should answer:

```text
1. Which issues have the largest estimated business impact?
2. What is the directional Cost / KPI impact composition?
3. What is the distribution of issue severity?
4. Which weeks contain the most issue signals?
```

The graph view should help a manager quickly identify:

```text
where to look first
which risks deserve attention
which impact components dominate
which timing buckets are stressed
```

The graph view should not turn the cockpit into an execution console.

---

## 4. Non-Goals

This phase must not implement:

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
formal approval workflow
issue status write-back
matplotlib rendering
advanced interactive dashboard
```

The graph tab is a **viewer only**.

---

## 5. Core Safety Rule

The same cockpit safety rule applies:

```text
Draw the instruments.
Do not start the engine.
```

The graph rendering may:

```text
read the existing view_model
build the graph_model
draw charts on Tk Canvas
show messages
```

It must not:

```text
run planning
run exports
change feature flags
execute commands
mutate env
write files
open files
persist data
```

---

## 6. Recommended Implementation Scope

Recommended file to modify:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

Recommended test file to add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.py
```

Do not modify:

```text
pysi/gui/cockpit_tk.py
pysi/reporting/*
pysi/plan/*
```

unless a tiny compatibility issue is absolutely necessary.

The main GUI button already opens the KPI view.  
This phase should extend the rendered view by adding a new tab.

---

## 7. Existing Functions to Reuse

Reuse the existing view-model and graph-model builders:

```python
build_explicit_pipeline_management_cockpit_view_model(env) -> dict
build_explicit_pipeline_kpi_graph_view_model(view_model: dict) -> dict
```

Reuse the current renderer:

```python
render_explicit_pipeline_management_cockpit_tk(parent, view_model) -> tk.Toplevel
```

The graph rendering should be integrated inside the existing renderer.

Conceptually:

```python
def render_explicit_pipeline_management_cockpit_tk(parent, view_model):
    ...
    graph_model = build_explicit_pipeline_kpi_graph_view_model(view_model)
    _add_graphs_tab(notebook, graph_model)
    ...
```

---

## 8. Recommended New Helper Functions

Add private helper functions in:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

Recommended helpers:

```python
def _create_graphs_tab(notebook: ttk.Notebook, graph_model: dict[str, Any]) -> None:
    ...

def _create_canvas_chart_frame(parent: tk.Widget, title: str) -> tuple[ttk.Frame, tk.Canvas]:
    ...

def _draw_horizontal_bar_chart(
    canvas: tk.Canvas,
    rows: list[dict[str, Any]],
    *,
    label_key: str,
    value_key: str,
    empty_message: str,
) -> None:
    ...

def _draw_count_bar_chart(
    canvas: tk.Canvas,
    counts: dict[str, int] | list[dict[str, Any]],
    *,
    empty_message: str,
) -> None:
    ...

def _draw_chart_message(canvas: tk.Canvas, message: str) -> None:
    ...
```

Keep helpers small and deterministic.

---

## 9. Graphs Tab Placement

Add a new tab:

```text
Graphs
```

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

Reason:

```text
Graphs are management summary visuals, so they should appear near Summary.
```

If it is simpler to append the tab after existing tabs in MVP, that is acceptable, but the preferred order is near Summary.

---

## 10. Graphs Tab Layout

Recommended MVP layout:

```text
Graphs tab
    2x2 grid:
        Top Business Impact        Cost / KPI Impact Composition
        Issue Severity Distribution Weekly Issue Count
```

Each chart should be placed in a labeled frame.

Suggested chart frame titles:

```text
Top Business Impact
Cost / KPI Impact Composition
Issue Severity Distribution
Weekly Issue Count
```

Use a fixed reasonable size for each Canvas, for example:

```text
520 x 240
```

or:

```text
500 x 220
```

The existing window can scroll or display the 2x2 grid depending on layout.

For MVP, a 2x2 grid is acceptable.

---

## 11. Chart Technology Choice

Use:

```text
tk.Canvas
```

not:

```text
matplotlib
```

Reason:

```text
Tk Canvas has no additional dependency.
Tk Canvas avoids backend issues.
Tk Canvas is enough for simple cockpit bars.
```

This is a deliberate MVP choice.

Matplotlib can be considered later for advanced charts such as waterfall or heatmap.

---

## 12. Chart 1: Top Business Impact

### 12.1 Source

```python
graph_model["top_impact_bars"]
```

### 12.2 Chart type

Horizontal bar chart.

### 12.3 Fields

```text
label
value
severity
issue_type
node
week
```

### 12.4 Display

Draw up to top 10 bars, though top 5 may be easier to read if the Canvas height is limited.

Recommended MVP:

```text
draw all rows already present in top_impact_bars
```

The graph model already limits to top 10.

### 12.5 Empty state

If no bars exist:

```text
No top impact issues are available.
```

---

## 13. Chart 2: Cost / KPI Impact Composition

### 13.1 Source

```python
graph_model["impact_composition"]
```

### 13.2 Chart type

Horizontal bar chart.

### 13.3 Rows

```text
Lost Sales
Margin Impact
Inventory Cost
Capacity Cost
Service Penalty
```

### 13.4 Display

Draw component bars using each row's `value`.

### 13.5 Caveat

A text note should be shown near the chart or at the bottom of the Graphs tab:

```text
Cost / KPI values are directional scenario estimates, not formal accounting values.
Double counting may be possible depending on assumptions.
```

If these messages are present in `graph_model["messages"]`, reuse them.

---

## 14. Chart 3: Issue Severity Distribution

### 14.1 Source

```python
graph_model["severity_distribution"]
```

### 14.2 Chart type

Simple bar chart.

Labels:

```text
error
warning
info
```

### 14.3 Empty state

If all counts are zero:

```text
No issue severity counts are available.
```

---

## 15. Chart 4: Weekly Issue Count

### 15.1 Source

```python
graph_model["weekly_issue_counts"]
```

### 15.2 Chart type

Simple bar chart.

X/category:

```text
week
```

Y/value:

```text
count
```

### 15.3 Empty state

If no weekly data exists:

```text
No week-level issue data is available.
```

---

## 16. Canvas Drawing Rules

### 16.1 General

Charts should be simple and robust.

Use Canvas primitives:

```text
create_text
create_rectangle
create_line
```

### 16.2 No explicit color dependency

MVP can rely on simple default colors or minimal standard colors.

If using colors, keep them conservative and readable.

Recommended:

```text
bars: standard blue or neutral gray
text: black
background: default / white
```

If existing project style avoids explicit colors, use Tk defaults as much as practical.

### 16.3 Scaling

Compute max value safely:

```python
max_value = max(abs(value), ...)
```

If all values are zero, show an empty-state message rather than drawing zero-length bars.

### 16.4 Long labels

Truncate long labels to around:

```text
40 characters
```

Use ellipsis:

```text
...
```

Full details remain available in the table tabs.

### 16.5 Value labels

Display formatted values at the end of bars:

```text
1,250,000
```

or:

```text
3
```

Use existing formatting helper if available.

---

## 17. Messages / Caveats in Graphs Tab

At the bottom of the Graphs tab, show key messages from:

```python
graph_model["messages"]
```

Recommended MVP:

```text
show first 3 graph messages
```

or show all if few.

Important caveats:

```text
Cost / KPI values are directional scenario estimates, not formal accounting values.
Double counting may be possible depending on assumptions.
```

The graph should not imply formal accounting precision.

---

## 18. Empty Graph Model Behavior

If:

```python
graph_model["available"] is False
```

the Graphs tab should still render.

It should show:

```text
No explicit pipeline KPI view data is available for graph rendering.
```

and empty chart panels.

The renderer must not crash.

---

## 19. Test Strategy

Tk rendering can be environment-sensitive.

Testing should focus on:

```text
1. helper functions that build / draw widgets without crashing
2. Graphs tab appears in the Notebook
3. empty graph model renders without crashing
4. populated graph model renders without crashing
5. existing renderer still works
```

Use safe Tk skip behavior:

```python
try:
    root = tk.Tk()
    root.withdraw()
except tk.TclError as exc:
    pytest.skip(...)
```

---

## 20. Recommended Test File

Add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.py
```

Suggested tests:

### 20.1 Graphs tab appears

Build a populated sample view model.

Render with:

```python
render_explicit_pipeline_management_cockpit_tk(root, view_model)
```

Find `ttk.Notebook`.

Verify one tab text is:

```text
Graphs
```

### 20.2 Empty graph model renders

Use a no-data view model.

Render.

Verify no exception.

### 20.3 Populated graph model renders

Use a populated view model with:

```text
top_impact_issues
issue_summary
executive_kpi_summary
weekly issue fields
messages
```

Render.

Verify no exception.

### 20.4 Existing rendering tests still pass

Existing test:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py
```

must still pass or skip appropriately.

---

## 21. Recommended Test Helpers

If needed, add small test helper:

```python
def _find_widget(root, widget_type):
    if isinstance(root, widget_type):
        return root
    for child in root.winfo_children():
        found = _find_widget(child, widget_type)
        if found is not None:
            return found
    return None
```

This pattern has already been useful for `ttk.Notebook` testing.

---

## 22. Existing Tests to Run

After implementation, run:

```bat
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.py
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_graph_view.py
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_view_button_integration.py
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_view.py
python -m pytest tests/test_explicit_pipeline_reporting_stack_insertion.py
python -m pytest tests/test_explicit_pipeline_reporting_flags.py
```

Then run key regression tests:

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

If Tk tests are skipped because Tk is unavailable, state so clearly.

---

## 23. Implementation Phase Recommendation

Recommended first implementation scope:

```text
Canvas graph rendering helper + Graphs tab
```

Files:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
tests/test_explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.py
```

Do not modify:

```text
pysi/gui/cockpit_tk.py
```

The existing `Explicit KPI View` button should automatically benefit because it opens the same renderer.

---

## 24. Completion Criteria

This implementation will be complete when:

```text
[OK] Graphs tab is added to Explicit KPI View renderer
[OK] graph model builder is reused
[OK] Top Business Impact chart is rendered or empty message shown
[OK] Cost / KPI Impact Composition chart is rendered or empty message shown
[OK] Issue Severity Distribution chart is rendered or empty message shown
[OK] Weekly Issue Count chart is rendered or empty message shown
[OK] no planning execution is added
[OK] no export execution is added
[OK] no ReplanCommand execution is added
[OK] no cockpit_tk.py modification
[OK] focused graph rendering tests pass or safely skip when Tk unavailable
[OK] existing graph model / view model / rendering / button tests pass
```

---

## 25. Future Enhancements

After MVP Canvas rendering, future improvements may include:

```text
better chart scaling
hover / tooltip detail
click chart bar to select related table row
KPI cards
waterfall chart
capacity heatmap
severity trend
export graph image
copy graph to clipboard
```

Each should be separately designed and feature-controlled.

---

## 26. Summary

The graph model is complete.

This design defines the next safe step:

```text
Graph model
    ↓
Tk Canvas simple charts
    ↓
Graphs tab in Explicit KPI View
```

The target is a readable management visual layer.

The rule remains:

```text
Draw the instruments.
Do not start the engine.
```
