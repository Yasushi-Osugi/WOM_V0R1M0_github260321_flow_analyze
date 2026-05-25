# Codex Request: Implement Explicit Pipeline Management Cockpit KPI Cards MVP

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_cards.md
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
    ↓
Graphs tab with Tk Canvas charts
```

The current Explicit KPI View already has these tabs:

```text
Summary
Graphs
Top Issues
Replan Candidates
Health
Assumptions / Exports
Messages
```

This request is for the next small read-only cockpit enhancement:

```text
KPI Cards in the Summary tab
```

This request is **not** for planning execution.

This request is **not** for export execution.

This request is **not** for ReplanCommand execution.

---

## 2. Main Objective

Add KPI Cards to the top area of the existing `Summary` tab inside the Explicit KPI View.

Target module to update:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

Target test file to add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_cards.py
```

The MVP cards are:

```text
1. Total Business Impact
2. Capacity Violations
3. Management Issues
4. Health Warnings
5. Replan Candidates
```

The cards should be read-only.

They should summarize the current `view_model`.

They should not run or trigger anything.

---

## 3. Important Constraints

Please follow these constraints strictly:

```text
1. Do not modify pysi/gui/cockpit_tk.py.
2. Do not add GUI buttons.
3. Do not add menu entries.
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
20. Do not remove existing Summary tab tables.
21. Do not remove the existing Graphs tab.
```

This request is only for:

```text
KPI card model + Summary tab card rendering
```

The safety rule remains:

```text
Show the warning lamps.
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
tests/test_explicit_pipeline_management_cockpit_kpi_cards.py
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

The existing public functions must remain available and unchanged in behavior:

```python
build_explicit_pipeline_management_cockpit_view_model(env) -> dict
build_explicit_pipeline_kpi_graph_view_model(view_model: dict) -> dict
render_explicit_pipeline_management_cockpit_tk(parent, view_model) -> tk.Toplevel
```

Do not change their public signatures.

The KPI cards should be rendered inside the existing:

```python
render_explicit_pipeline_management_cockpit_tk(parent, view_model)
```

using the existing `view_model`.

---

## 6. Recommended New Helper Functions

Add private helpers in:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

Recommended helpers:

```python
def _build_explicit_pipeline_kpi_cards(view_model: dict[str, Any]) -> list[dict[str, Any]]:
    ...

def _create_kpi_cards_frame(parent: tk.Widget, cards: list[dict[str, Any]]) -> ttk.Frame:
    ...

def _create_kpi_card(parent: tk.Widget, card: dict[str, Any]) -> ttk.Frame:
    ...
```

Helper signatures can differ if simpler, but keep them private, deterministic, and small.

---

## 7. KPI Card Model Schema

Recommended card schema:

```python
{
    "title": "Total Business Impact",
    "value": "1,250,000",
    "unit": "JPY",
    "subtitle": "Directional estimate",
    "status": "warning",
    "source": "executive_kpi_summary.estimated_total_business_impact",
}
```

For count cards:

```python
{
    "title": "Capacity Violations",
    "value": "2",
    "unit": "records",
    "subtitle": "Capacity pressure",
    "status": "warning",
    "source": "capacity_summary.capacity_violation_record_count",
}
```

Recommended statuses:

```text
normal
warning
unknown
```

Do not implement complex thresholding in this MVP.

---

## 8. Card 1: Total Business Impact

### Source

```python
view_model["executive_kpi_summary"]["estimated_total_business_impact"]
```

### Unit / currency

Use:

```python
view_model["executive_kpi_summary"]["currency"]
```

when available.

### Value formatting

Use existing formatting helper if available.

Example:

```text
1,250,000
```

### Subtitle

```text
Directional estimate
```

### Status

Recommended:

```text
value > 0           -> warning
value == 0          -> normal
missing unavailable -> unknown
```

If `view_model["available"] is False`, show:

```text
N/A
```

with status:

```text
unknown
```

---

## 9. Card 2: Capacity Violations

### Source

```python
view_model["capacity_summary"]["capacity_violation_record_count"]
```

### Unit

```text
records
```

### Subtitle

```text
Capacity pressure
```

### Status

```text
count > 0           -> warning
count == 0          -> normal
missing unavailable -> unknown
```

If no data:

```text
N/A
```

---

## 10. Card 3: Management Issues

### Source

```python
view_model["issue_summary"]["management_issue_candidate_count"]
```

### Unit

```text
issues
```

### Subtitle

```text
Management attention
```

### Status

```text
count > 0           -> warning
count == 0          -> normal
missing unavailable -> unknown
```

If no data:

```text
N/A
```

---

## 11. Card 4: Health Warnings

### Preferred source

```python
view_model["health_summary"]["health_issue_count"]
```

### Fallback source

```python
view_model["issue_summary"]["health_issue_candidate_count"]
```

### Unit

```text
warnings
```

### Subtitle

```text
Data quality / health
```

### Status

```text
count > 0           -> warning
count == 0          -> normal
missing unavailable -> unknown
```

If no data:

```text
N/A
```

---

## 12. Card 5: Replan Candidates

### Preferred source

```python
len(view_model["replan_candidates"])
```

### Fallback source

```python
view_model["issue_summary"]["replan_command_candidate_count"]
```

### Unit

```text
candidates
```

### Subtitle

```text
Candidate-only actions
```

### Status

```text
count > 0           -> warning
count == 0          -> normal
missing unavailable -> unknown
```

If no data:

```text
N/A
```

Important:

```text
This card must not execute replan candidates.
```

It only displays the count.

---

## 13. No-Data Behavior

If:

```python
view_model.get("available") is False
```

or the input view model is missing / invalid, return five cards with:

```text
value = N/A
status = unknown
```

The five titles should still be present:

```text
Total Business Impact
Capacity Violations
Management Issues
Health Warnings
Replan Candidates
```

This keeps the UI stable even before planning data exists.

---

## 14. Summary Tab Integration

Add KPI Cards to the top of the existing Summary tab.

Current Summary tab should become conceptually:

```text
Summary tab
    ├─ KPI Cards frame
    └─ existing key-value summary sections
```

Do not remove existing Summary tables.

Do not remove existing fields.

Do not change the Graphs tab.

Do not change other tabs except as required by layout.

---

## 15. Rendering Approach

Use standard Tk / ttk widgets.

Recommended:

```text
ttk.Frame
ttk.Label
```

The cards may be rendered as bordered frames.

Recommended layout:

```text
horizontal row of five cards
```

If width is constrained, allow wrap:

```text
3 cards first row
2 cards second row
```

MVP can use a simple grid:

```text
5 columns in one row
```

or:

```text
3 columns x 2 rows
```

Choose the simpler option that fits the existing Summary tab.

---

## 16. Card Visual Content

Each card should show:

```text
title
large value + unit
subtitle
status
```

Example:

```text
Total Business Impact
1,250,000 JPY
Directional estimate
Status: warning
```

Avoid relying on color alone.

It is acceptable to display status as text.

---

## 17. Input Mutation Rule

The implementation must not mutate the input `view_model`.

Tests should use:

```python
copy.deepcopy(view_model)
```

and compare after:

```text
_build_explicit_pipeline_kpi_cards(view_model)
render_explicit_pipeline_management_cockpit_tk(root, view_model)
```

---

## 18. Test Strategy

Add focused tests for:

```text
1. card model builder with populated view model
2. card model builder with no-data view model
3. Summary tab renders with cards
4. existing tabs still present
5. input view_model not mutated
```

Avoid brittle pixel-level GUI tests.

Use safe Tk skip behavior for rendering tests.

---

## 19. Recommended Test File

Add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_cards.py
```

### 19.1 Test card model populated

Input view model with:

```text
executive_kpi_summary
capacity_summary
issue_summary
health_summary
replan_candidates
```

Verify:

```text
five cards returned
titles match expected
values are formatted strings
statuses are deterministic
units are expected
```

### 19.2 Test card model no data

Input:

```python
{"available": False}
```

Verify:

```text
five cards returned
values are N/A
statuses are unknown
```

### 19.3 Test Summary tab renders

Use:

```python
render_explicit_pipeline_management_cockpit_tk(root, view_model)
```

Find `ttk.Notebook`.

Verify:

```text
Summary tab exists
```

If feasible, recursively check card title labels exist.

If that is brittle, verifying render no exception plus Summary tab existence is acceptable for MVP.

### 19.4 Test existing tabs still present

Verify tabs include:

```text
Summary
Graphs
Top Issues
Replan Candidates
Health
Assumptions / Exports
Messages
```

### 19.5 Test no side effects

Deep copy the view model before calling builder and renderer.

Verify input remains unchanged.

---

## 20. Recommended Test Helpers

Use safe Tk skip behavior:

```python
def _make_root_or_skip():
    try:
        root = tk.Tk()
        root.withdraw()
        return root
    except tk.TclError as exc:
        pytest.skip(f"Tk unavailable: {exc}")
```

Use recursive widget search if needed:

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

To find label text, optionally use:

```python
def _collect_label_texts(root):
    texts = []
    if isinstance(root, ttk.Label):
        texts.append(str(root.cget("text")))
    for child in root.winfo_children():
        texts.extend(_collect_label_texts(child))
    return texts
```

---

## 21. Existing Tests to Run

Please run:

```bat
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_cards.py
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

## 22. Completion Criteria

This request is complete when:

```text
[OK] KPI card model helper exists
[OK] five MVP cards are produced
[OK] no-data view model produces safe N/A cards
[OK] populated view model produces deterministic card values
[OK] Summary tab renders KPI cards
[OK] existing Summary details remain visible
[OK] existing Graphs tab remains visible
[OK] existing core tabs remain visible
[OK] input view_model is not mutated
[OK] no cockpit_tk.py modification
[OK] no planning execution is added
[OK] no export execution is added
[OK] no ReplanCommand execution is added
[OK] focused KPI card tests pass or safely skip when Tk unavailable
[OK] existing graph / view / button tests pass
```

---

## 23. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. KPI card helper added
4. Card titles / sources / statuses implemented
5. Summary tab placement
6. No-data behavior
7. Input mutation safety
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
interactive card clicks
drilldown
Knowledge Continuity handoff
waterfall chart
capacity heatmap
planning execution
export execution
reporting stack execution
OR optimization
database persistence
ReplanCommand execution
```

This request is only for:

```text
Explicit Pipeline Management Cockpit KPI Cards MVP
```
