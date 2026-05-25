# Codex Request: Implement Explicit Pipeline Management Cockpit KPI Graph Canvas Rendering MVP

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.md
```

Please read this design memo first.

The Explicit Pipeline Management Cockpit KPI integration has already reached this state:

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
    ↓
Graph view model
```

The graph-view-model builder has already been implemented:

```python
build_explicit_pipeline_kpi_graph_view_model(view_model: dict) -> dict
```

in:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

This request is for the next small step:

```text
use the graph model to add a read-only Graphs tab
with Tk Canvas-based simple charts
inside the existing Explicit KPI View window.
```

This request is **not** for changing `cockpit_tk.py`.

This request is **not** for planning / export / replan execution.

---

## 2. Main Objective

Modify the existing Explicit KPI View renderer so that the rendered `ttk.Notebook` includes a new tab:

```text
Graphs
```

The new tab should display simple read-only charts based on:

```python
build_explicit_pipeline_kpi_graph_view_model(view_model)
```

Target module to update:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

Target test file to add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.py
```

Recommended MVP charts:

```text
1. Top Business Impact
2. Cost / KPI Impact Composition
3. Issue Severity Distribution
4. Weekly Issue Count
```

Use Tk Canvas, not matplotlib.

---

## 3. Important Constraints

Please follow these constraints strictly:

```text
1. Do not modify pysi/gui/cockpit_tk.py.
2. Do not add GUI buttons.
3. Do not add menu integration.
4. Do not use matplotlib.
5. Do not add new dependencies.
6. Do not run planning.
7. Do not run Run Full Plan.
8. Do not run the explicit pipeline.
9. Do not run the reporting stack helper.
10. Do not trigger exports.
11. Do not change feature flags.
12. Do not mutate env.
13. Do not execute ReplanCommand.
14. Do not implement automatic replanning.
15. Do not implement OR optimization.
16. Do not implement database persistence.
17. Do not implement Knowledge Continuity persistence.
18. Do not modify Cost / KPI enrichment logic.
19. Do not modify exporter logic.
```

This request is only for:

```text
Canvas graph rendering helper + Graphs tab in the existing read-only KPI window
```

The safety rule remains:

```text
Draw the instruments.
Do not start the engine.
```

---

## 4. Files to Modify / Add

Please modify:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

Please add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.py
```

Do not modify:

```text
pysi/gui/cockpit_tk.py
pysi/reporting/*
pysi/plan/*
```

unless a tiny compatibility issue is absolutely unavoidable.

---

## 5. Existing Functions to Keep

The existing functions must remain available and unchanged in behavior:

```python
build_explicit_pipeline_management_cockpit_view_model(env) -> dict
build_explicit_pipeline_kpi_graph_view_model(view_model: dict) -> dict
render_explicit_pipeline_management_cockpit_tk(parent, view_model) -> tk.Toplevel
```

Do not change their public signatures.

The new Graphs tab should be added inside:

```python
render_explicit_pipeline_management_cockpit_tk(parent, view_model)
```

using the existing `view_model`.

---

## 6. Recommended Integration Point

Inside `render_explicit_pipeline_management_cockpit_tk(parent, view_model)`, after creating the `ttk.Notebook`, add a Graphs tab.

Conceptual flow:

```python
graph_model = build_explicit_pipeline_kpi_graph_view_model(view_model)
_create_graphs_tab(notebook, graph_model)
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

If inserting after Summary is awkward, appending Graphs after existing tabs is acceptable for MVP, but preferred order is near Summary.

---

## 7. Recommended New Helper Functions

Add private helpers in:

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
    label_key: str = "label",
    value_key: str = "value",
    empty_message: str,
) -> None:
    ...

def _draw_distribution_bar_chart(
    canvas: tk.Canvas,
    rows: list[dict[str, Any]],
    *,
    label_key: str = "label",
    value_key: str = "value",
    empty_message: str,
) -> None:
    ...

def _draw_chart_message(canvas: tk.Canvas, message: str) -> None:
    ...
```

Helper signatures can differ if simpler, but keep them private, small, and deterministic.

---

## 8. Graphs Tab Layout

Use a 2x2 grid inside the Graphs tab.

Recommended layout:

```text
Graphs tab
    ├─ Top Business Impact            ├─ Cost / KPI Impact Composition
    └─ Issue Severity Distribution    └─ Weekly Issue Count
```

Each chart should be placed inside a labeled frame.

Suggested Canvas size:

```text
520 x 240
```

or similar.

The existing KPI window geometry should not need major changes.

---

## 9. Chart 1: Top Business Impact

### Source

```python
graph_model["top_impact_bars"]
```

### Chart type

```text
horizontal bar chart
```

### Row fields

```text
label
value
severity
issue_type
node
week
```

### Behavior

Draw one horizontal bar per row.

Use:

```text
label on the left
bar in the middle
formatted value at the end
```

If rows are empty, show:

```text
No top impact issues are available.
```

---

## 10. Chart 2: Cost / KPI Impact Composition

### Source

```python
graph_model["impact_composition"]
```

### Chart type

```text
horizontal bar chart
```

### Rows

```text
Lost Sales
Margin Impact
Inventory Cost
Capacity Cost
Service Penalty
```

### Behavior

Draw one horizontal bar per component.

If all values are zero or rows are empty, show:

```text
No Cost / KPI impact composition is available.
```

---

## 11. Chart 3: Issue Severity Distribution

### Source

```python
graph_model["severity_distribution"]
```

### Chart type

```text
simple bar chart
```

### Labels

```text
error
warning
info
```

Convert the distribution dict into chart rows such as:

```python
[
    {"label": "error", "value": 1},
    {"label": "warning", "value": 2},
    {"label": "info", "value": 3},
]
```

If all counts are zero, show:

```text
No issue severity counts are available.
```

---

## 12. Chart 4: Weekly Issue Count

### Source

```python
graph_model["weekly_issue_counts"]
```

### Chart type

```text
simple bar chart
```

### Row fields

```text
week
count
```

Convert rows to chart row format or draw directly.

If rows are empty, show:

```text
No week-level issue data is available.
```

---

## 13. Canvas Drawing Rules

### 13.1 Basic primitives

Use only standard Canvas primitives:

```text
create_text
create_rectangle
create_line
```

### 13.2 Scaling

Compute maximum value safely.

If max value is zero or no rows exist, show the empty-state message.

### 13.3 Long labels

Truncate long labels to around:

```text
40 characters
```

Use ellipsis:

```text
...
```

### 13.4 Value labels

Show formatted values such as:

```text
1,250,000
3
```

Use existing `_format_value` if available.

### 13.5 Colors

Keep colors simple and conservative.

It is acceptable to use minimal standard colors such as:

```text
white background
gray / blue bars
black text
```

Do not introduce complex styling.

---

## 14. Graph Messages / Caveats

At the bottom of the Graphs tab, display key messages from:

```python
graph_model["messages"]
```

Recommended MVP:

```text
show first 3 messages
```

Important caveats to preserve when present:

```text
Cost / KPI values are directional scenario estimates, not formal accounting values.
Double counting may be possible depending on assumptions.
```

The graphs must not imply formal accounting precision.

---

## 15. Empty / No-Data Behavior

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

The renderer must not raise.

---

## 16. Test Strategy

Tk rendering can be environment-sensitive.

Add tests that safely skip when Tk cannot initialize.

Recommended helper:

```python
def _make_root_or_skip():
    try:
        root = tk.Tk()
        root.withdraw()
        return root
    except tk.TclError as exc:
        pytest.skip(f"Tk unavailable: {exc}")
```

Destroy windows and root after tests.

Recommended recursive helper:

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

---

## 17. Tests to Add

Please add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.py
```

### 17.1 Graphs tab appears

Create a populated view model.

Call:

```python
window = render_explicit_pipeline_management_cockpit_tk(root, view_model)
```

Find `ttk.Notebook`.

Verify one tab text is:

```text
Graphs
```

### 17.2 Empty model renders

Use:

```python
{"available": False}
```

Render.

Verify:

```text
Toplevel returned
Notebook exists
Graphs tab exists
no exception
```

### 17.3 Populated model renders

Use a populated view model containing:

```text
top_impact_issues
issue_summary
executive_kpi_summary
messages
```

Render.

Verify:

```text
Toplevel returned
Graphs tab exists
no exception
```

### 17.4 Existing renderer still supports core tabs

Verify tabs still include:

```text
Summary
Top Issues
Replan Candidates
Health
Assumptions / Exports
Messages
```

along with:

```text
Graphs
```

### 17.5 No side effects

Deep copy the view model before render.

Verify input view model remains unchanged after render.

---

## 18. Existing Tests to Run

Please run:

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

## 19. Completion Criteria

This request is complete when:

```text
[OK] Graphs tab is added to Explicit KPI View renderer
[OK] graph model builder is reused
[OK] Top Business Impact chart is rendered or empty message shown
[OK] Cost / KPI Impact Composition chart is rendered or empty message shown
[OK] Issue Severity Distribution chart is rendered or empty message shown
[OK] Weekly Issue Count chart is rendered or empty message shown
[OK] graph messages / caveats are shown
[OK] empty model renders without crashing
[OK] populated model renders without crashing
[OK] input view_model is not mutated
[OK] no cockpit_tk.py modification
[OK] no matplotlib dependency is added
[OK] no planning execution is added
[OK] no export execution is added
[OK] no ReplanCommand execution is added
[OK] focused graph rendering tests pass or safely skip when Tk unavailable
[OK] existing graph model / view model / rendering / button tests pass
```

---

## 20. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. Graphs tab placement
4. Chart helpers added
5. Charts implemented
6. Empty-state behavior
7. Messages / caveats behavior
8. Safety boundaries preserved
9. Test commands executed
10. Test results
11. Any skipped tests and why
12. Limitations / follow-up
```

Please do not proceed into:

```text
cockpit_tk.py modification
new GUI buttons
matplotlib rendering
waterfall chart
capacity heatmap
interactive filtering
planning execution
export execution
reporting stack execution
OR optimization
database persistence
ReplanCommand execution
Knowledge Continuity persistence
```

This request is only for:

```text
Explicit Pipeline Management Cockpit KPI Graph Canvas Rendering MVP
```
