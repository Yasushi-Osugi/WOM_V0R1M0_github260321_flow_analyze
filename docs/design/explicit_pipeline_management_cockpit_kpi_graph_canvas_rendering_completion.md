# Explicit Pipeline Management Cockpit KPI Graph Canvas Rendering Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-24  
**Status:** Completion memo  
**Target path:** `docs/design/explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering_completion.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Explicit Pipeline Management Cockpit KPI Graph Canvas Rendering MVP**.

The purpose of this milestone was to add a read-only **Graphs** tab to the existing Explicit Pipeline KPI View and draw simple KPI charts using standard Tk Canvas primitives.

The completed visual path is now:

```text
Management Cockpit KPI view model
    ↓
Graph view model
    ↓
Tk Canvas chart rendering
    ↓
Graphs tab in Explicit KPI View
```

This milestone adds visual cockpit instruments to the previously completed table / key-value cockpit.

It does not add planning execution, export execution, replanning, or new command behavior.

---

## 2. Background

Before this milestone, WOM had already completed:

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
    ↓
Graph view model
```

The Graph View Model MVP had already prepared chart-ready data through:

```python
build_explicit_pipeline_kpi_graph_view_model(view_model: dict) -> dict
```

This milestone uses that graph model to render actual visual charts inside the existing Explicit KPI View window.

---

## 3. Implemented Files

This milestone modified or added:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
tests/test_explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.py
```

The implementation was committed as:

```text
d5b86f9 Add explicit KPI Graphs tab with Tk canvas charts
```

---

## 4. Main Implementation

A new private Canvas rendering layer was added to:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

The renderer now adds a new tab:

```text
Graphs
```

to the existing `ttk.Notebook` inside:

```python
render_explicit_pipeline_management_cockpit_tk(parent, view_model)
```

The Graphs tab is built by reusing:

```python
build_explicit_pipeline_kpi_graph_view_model(view_model)
```

No new public API was required.

No existing public function signatures were changed.

---

## 5. Graphs Tab Placement

The `Graphs` tab is added immediately after:

```text
Summary
```

Recommended tab order is now:

```text
Summary
Graphs
Top Issues
Replan Candidates
Health
Assumptions / Exports
Messages
```

This is appropriate because graphs are management summary visuals and should appear close to the high-level summary.

---

## 6. Chart Layout Implemented

The Graphs tab uses a 2x2 chart layout.

Implemented chart panels:

```text
Top Business Impact
Cost / KPI Impact Composition
Issue Severity Distribution
Weekly Issue Count
```

Each chart is rendered in a labeled frame using `tk.Canvas`.

The layout is intended to be compact, readable, and safe for MVP usage.

---

## 7. Charts Implemented

### 7.1 Top Business Impact

Source:

```python
graph_model["top_impact_bars"]
```

Displays a horizontal bar chart of issue candidates by estimated total business impact.

Empty message:

```text
No top impact issues are available.
```

### 7.2 Cost / KPI Impact Composition

Source:

```python
graph_model["impact_composition"]
```

Displays component bars for:

```text
Lost Sales
Margin Impact
Inventory Cost
Capacity Cost
Service Penalty
```

Empty message:

```text
No Cost / KPI impact composition is available.
```

### 7.3 Issue Severity Distribution

Source:

```python
graph_model["severity_distribution"]
```

Displays bars for:

```text
error
warning
info
```

Empty message:

```text
No issue severity counts are available.
```

### 7.4 Weekly Issue Count

Source:

```python
graph_model["weekly_issue_counts"]
```

Displays issue count bars by week.

Empty message:

```text
No week-level issue data is available.
```

---

## 8. Canvas Rendering Helpers Added

The implementation added private helper functions such as:

```text
_truncate_label
_draw_chart_message
_draw_horizontal_bar_chart
_draw_distribution_bar_chart
_create_canvas_chart_frame
_create_graphs_tab
```

These helpers use only standard Tk Canvas primitives:

```text
create_text
create_rectangle
create_line
```

No matplotlib was introduced.

No new dependency was introduced.

---

## 9. Graph Notes / Caveats

The Graphs tab includes a notes / caveats area.

It displays the first graph-model messages, including caveats such as:

```text
Cost / KPI values are directional scenario estimates, not formal accounting values.
Double counting may be possible depending on assumptions.
```

This is important because the visual chart should not imply formal accounting precision.

The graph remains a management attention tool, not a statutory accounting report.

---

## 10. Empty-State Behavior

The Graphs tab renders safely even when:

```python
graph_model["available"] is False
```

or the source view model has no explicit pipeline artifacts.

Each chart panel shows an empty-state message when its data is absent.

The renderer does not crash.

This preserves the usability rule:

```text
The user can open Explicit KPI View before planning data exists.
```

---

## 11. Safety Boundaries Preserved

This milestone preserved the intended safety boundaries.

It did not modify:

```text
pysi/gui/cockpit_tk.py
```

It did not add:

```text
new GUI buttons
menu entries
planning execution
explicit pipeline execution
reporting stack execution
export execution
feature flag changes
env mutation
ReplanCommand execution
automatic replanning
OR optimization
database persistence
Knowledge Continuity persistence
matplotlib dependency
```

The implementation is view-only.

The rule remains:

```text
Draw the instruments.
Do not start the engine.
```

---

## 12. Tests Added

The focused test file is:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.py
```

It covers:

```text
1. Graphs tab appears
2. empty model renders safely
3. populated model renders safely
4. core tabs are preserved
5. input view_model is not mutated by rendering
```

The tests use safe Tk initialization / skip behavior for environment-sensitive rendering.

---

## 13. Validation

The focused Graph Canvas Rendering test passed:

```bat
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.py
```

Observed result:

```text
5 passed
```

Related tests also passed:

```bat
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_graph_view.py
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_view_button_integration.py
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_view.py
python -m pytest tests/test_explicit_pipeline_reporting_stack_insertion.py
python -m pytest tests/test_explicit_pipeline_reporting_flags.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results:

```text
Graph View Model: 8 passed
Button Integration: 1 passed
Tk Rendering: 2 passed, 1 skipped
KPI View Model: 8 passed
Reporting Stack Insertion: 7 passed
Reporting Flags: 10 passed
Covid Vaccine optional: 1 passed
```

The `1 skipped` in Tk rendering is acceptable because Tk rendering tests can be environment-sensitive.

No failures or errors remained at commit time.

---

## 14. Completion Criteria

This milestone satisfies the intended completion criteria.

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
[OK] focused graph rendering tests pass
[OK] existing graph model / view model / rendering / button tests pass
```

---

## 15. Meaning of This Milestone

Before this milestone:

```text
WOM had chart-ready graph model data, but the Explicit KPI View did not draw charts.
```

After this milestone:

```text
WOM has a Graphs tab inside Explicit KPI View with Canvas-based charts.
```

This means management users can now see visual summaries rather than only tables.

The data path is now:

```text
explicit pipeline artifacts
    ↓
Management Cockpit KPI view model
    ↓
Graph view model
    ↓
Tk Canvas charts
    ↓
Graphs tab
```

---

## 16. Current Pipeline Position

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
Canvas graph rendering / Graphs tab              ✅ completed
    ↓
future KPI cards / usability refinements
```

---

## 17. Current Operational Meaning

The user can now:

```text
Run planning
    ↓
open Explicit KPI View
    ↓
inspect Summary / Graphs / Top Issues / Replan Candidates / Health / Assumptions / Messages
```

The Graphs tab can show:

```text
Top Business Impact
Cost / KPI Impact Composition
Issue Severity Distribution
Weekly Issue Count
```

without executing planning, exports, or replan commands.

---

## 18. Known Limitations

This milestone intentionally keeps graph rendering simple.

It does not yet implement:

```text
interactive filtering
hover tooltips
click-to-select related table rows
KPI cards
waterfall chart
capacity heatmap
severity trend chart
graph image export
copy graph to clipboard
dark mode styling
advanced chart scaling
```

The charts are basic Tk Canvas charts, intended as a safe MVP.

---

## 19. Future Milestones

### 19.1 KPI cards

Add compact cards for:

```text
Total Business Impact
Capacity Violations
Management Issues
Health Warnings
Replan Candidates
```

### 19.2 Detail interaction

Future read-only interaction can include:

```text
click a bar
show related issue details
highlight related table row
copy issue summary
```

No command execution should be added in the first interaction phase.

### 19.3 Waterfall chart

Add a Cost / KPI impact waterfall:

```text
Lost Sales
Margin Impact
Inventory Cost
Capacity Cost
Service Penalty
Total
```

### 19.4 Capacity heatmap

Add a node x week capacity pressure heatmap after richer capacity detail is exposed to the view model.

### 19.5 Knowledge Continuity handoff

Later, selected chart / issue insights may feed:

```text
open issues
facts and findings
decision log candidates
next-entry prompts
```

through the WOM Knowledge Continuity Layer.

This should remain separately designed and explicitly controlled.

---

## 20. Summary

The Explicit Pipeline Management Cockpit KPI Graph Canvas Rendering MVP is complete.

The key achievement is:

```text
Explicit KPI View now includes a Graphs tab with Tk Canvas charts.
```

The milestone remains safely non-invasive:

```text
no cockpit_tk.py change
no new button
no matplotlib dependency
no planning execution
no export execution
no replan execution
```

The cockpit now has both:

```text
table / key-value evidence
and
visual management charts
```

The instruments are now drawn.
