# Explicit Pipeline Management Cockpit KPI View Tk Rendering Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-24  
**Status:** Design memo  
**Target path:** `docs/design/explicit_pipeline_management_cockpit_kpi_view_tk_rendering.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/explicit_pipeline_management_cockpit_kpi_view.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view_completion.md`
- `docs/codex_requests/explicit_pipeline_management_cockpit_kpi_view_request.md`
- `docs/design/explicit_pipeline_reporting_issue_cost_kpi_overview.md`
- `docs/design/explicit_pipeline_planning_sequence_reporting_stack_insertion.md`
- `docs/design/explicit_pipeline_planning_sequence_reporting_stack_insertion_completion.md`
- `docs/design/explicit_pipeline_planning_sequence_reporting_flags.md`
- `docs/design/explicit_pipeline_planning_sequence_reporting_flags_completion.md`
- `docs/design/explicit_pipeline_issue_candidate_cost_kpi_enrichment.md`
- `docs/design/explicit_pipeline_issue_candidate_cost_kpi_export.md`
- `docs/design/wom_knowledge_continuity_layer.md`

---

## 1. Purpose

This memo defines the design for rendering the already-completed **Explicit Pipeline Management Cockpit KPI View Model** in a read-only Tk window.

The completed view-model builder is:

```python
build_explicit_pipeline_management_cockpit_view_model(env) -> dict
```

implemented in:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

The next step is to display that dictionary in a simple, safe, read-only GUI.

This design is for:

```text
view model
    ↓
read-only Tk rendering
```

It is not for:

```text
planning execution
export execution
replanning
optimization
knowledge persistence
```

---

## 2. Current Completed State

The current pipeline has reached this point:

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
Management Cockpit KPI view model ✅
    ↓
Tk read-only rendering ← current design target
```

The view model already provides:

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

The Tk rendering phase should consume this already-built model and display it.

---

## 3. Design Goal

The goal is to provide a read-only Management Cockpit KPI View that helps the user understand:

```text
1. Whether explicit pipeline evidence is available
2. What the executive Cost / KPI impact summary says
3. Which capacity / issue / data-quality risks exist
4. Which top impact issues deserve attention
5. Which replan candidates exist as candidate_only
6. Which assumptions were used
7. Which export artifacts exist
8. What next review actions are suggested
```

The view should support management review, not management automation.

---

## 4. Non-Goals

This phase must not implement:

```text
planning execution
Run Full Plan trigger
explicit pipeline rerun
file export execution
Cost / KPI recalculation
issue candidate generation
automatic replanning
ReplanCommand execution
OR optimization
database persistence
Knowledge Continuity persistence
formal approval workflow
write-back to env
```

The GUI is a viewer only.

No hidden side effects.

---

## 5. Core Rule

The Tk view must be:

```text
read-only display over the view model
```

not:

```text
an execution cockpit
```

It should call:

```python
build_explicit_pipeline_management_cockpit_view_model(self.env)
```

and render the returned dictionary.

It should not modify the view model, the env, or any planning data.

---

## 6. Recommended Implementation Scope

Recommended first implementation scope:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
pysi/gui/cockpit_tk.py
tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py
```

However, the preferred design is to keep most rendering logic in the helper module:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

and use `cockpit_tk.py` only for a small entry-point method or button/menu integration.

---

## 7. Proposed Functions

The following functions are recommended.

### 7.1 View-model function already exists

```python
build_explicit_pipeline_management_cockpit_view_model(env) -> dict
```

This should remain the single source of display data.

### 7.2 New rendering function

Add:

```python
render_explicit_pipeline_management_cockpit_tk(parent, view_model: dict) -> tk.Toplevel
```

or:

```python
open_explicit_pipeline_management_cockpit_window(parent, env) -> tk.Toplevel
```

Recommended separation:

```python
def render_explicit_pipeline_management_cockpit_tk(parent, view_model: dict) -> tk.Toplevel:
    ...
```

Then, in `cockpit_tk.py`:

```python
view_model = build_explicit_pipeline_management_cockpit_view_model(self.env)
render_explicit_pipeline_management_cockpit_tk(self, view_model)
```

This keeps rendering testable at the view-model boundary.

---

## 8. Recommended GUI Entry Point

Possible method in `WOMCockpit`:

```python
def _open_explicit_pipeline_kpi_view(self):
    view_model = build_explicit_pipeline_management_cockpit_view_model(self.env)
    render_explicit_pipeline_management_cockpit_tk(self, view_model)
```

The method should:

```text
read env
build view model
render Toplevel
```

It should not:

```text
run planning
run reporting stack
run exports
modify flags
execute commands
```

---

## 9. Button / Menu Integration

This design allows adding a button, but it should be minimal and clearly read-only.

Possible button label:

```text
Explicit KPI View
```

or:

```text
Pipeline KPI View
```

Recommended placement:

```text
near existing Management Cockpit / reporting controls
```

The button should only call:

```python
self._open_explicit_pipeline_kpi_view()
```

No planning execution should be triggered.

No export should be triggered.

This is a viewer button, not an engine switch.

---

## 10. Window Type

Recommended Tk structure:

```text
tk.Toplevel
    Frame
        Header/status section
        Summary cards / labels
        Notebook or vertical sections
        Treeview tables
        Message / next action area
```

A first MVP may use a single scrollable window rather than a complex notebook.

Recommended MVP choice:

```text
Toplevel + ttk.Notebook
```

Tabs:

```text
Summary
Top Issues
Replan Candidates
Health
Assumptions / Exports
Messages
```

This keeps information organized without overwhelming the main screen.

---

## 11. Recommended Window Layout

### 11.1 Tab 1: Summary

Display:

```text
Header / availability
Product
Executive KPI summary
Capacity summary
Issue summary
Cost / KPI caveats
```

### 11.2 Tab 2: Top Issues

Display:

```text
top_impact_issues
```

as a read-only `ttk.Treeview`.

### 11.3 Tab 3: Replan Candidates

Display:

```text
replan_candidates
```

as a read-only table.

Important:

```text
status=candidate_only
```

must be visible.

No execute button.

### 11.4 Tab 4: Health

Display:

```text
health_summary
top_health_issues
```

### 11.5 Tab 5: Assumptions / Exports

Display:

```text
assumption_summary
export_summary
```

### 11.6 Tab 6: Messages / Next Actions

Display:

```text
messages
next_review_actions
```

---

## 12. Summary Tab Design

The Summary tab should include compact labels.

Suggested label groups:

```text
Status:
    Explicit Pipeline: Available / Not available
    Capacity Report: Available / Not available
    Issue Candidates: Available / Not available
    Cost / KPI Bundle: Available / Not available
    Exports: Available / Not available

Executive KPI:
    Currency
    Total Business Impact
    Lost Sales
    Margin Impact
    Inventory Cost Impact
    Capacity Cost Impact
    Service Penalty
```

If values are missing, show safe defaults such as:

```text
0.0
N/A
Not available
```

---

## 13. Capacity / Issue Summary

The Summary tab may also show:

```text
Capacity usage records
Capacity violations
Lot exceptions
Health checks
Planning issue candidates
Management issue candidates
Replan candidates
Health issue candidates
Warnings
Errors
```

This can be displayed as labels or a two-column Treeview:

```text
Metric | Value
```

---

## 14. Top Issues Table

Source:

```python
view_model["top_impact_issues"]
```

Recommended columns:

```text
rank
severity
issue_type
impact_category
product
node
week
capacity_type
estimated_total_business_impact
lot_ids
message
```

Optional columns if available:

```text
suggested_action
suggested_decision
```

MVP should avoid too many columns if the table becomes unreadable.

Columns can be shortened:

```text
Rank
Severity
Issue
Impact
Product
Node
Week
Cap
Value
Lots
Message
```

---

## 15. Replan Candidates Table

Source:

```python
view_model["replan_candidates"]
```

Recommended columns:

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

Important display rule:

```text
candidate_only must be shown clearly
```

No command execution.

No button per row.

No double-click execution.

---

## 16. Health Table

Source:

```python
view_model["health_summary"]["top_health_issues"]
```

Recommended columns:

```text
severity
issue_type
source
message
details
```

This tab should help identify whether planning evidence can be trusted.

---

## 17. Assumptions View

Source:

```python
view_model["assumption_summary"]
```

MVP display can be a simple read-only text area or key-value table.

Recommended fields:

```text
available
currency
unit_price_products
unit_margin_products
unit_cost_products
inventory_holding_cost_products
capacity_shortage_penalty_types
capacity_overtime_cost_types
service_penalty_products
```

Do not dump huge JSON.

Show compact keys.

---

## 18. Export Summary View

Source:

```python
view_model["export_summary"]
```

Display export groups:

```text
capacity_report_export
issue_candidate_export
cost_kpi_export
```

For each group:

```text
available
output_dir
file_count
summary_path
assumptions_path
message
```

MVP should display file paths as text only.

No file-open button in the first rendering phase.

---

## 19. Messages / Next Actions View

Source:

```python
view_model["messages"]
view_model["next_review_actions"]
```

Display as bullet-style read-only list.

Example messages:

```text
Cost / KPI values are directional scenario estimates, not formal accounting values.
Double counting may be possible depending on assumptions.
Export results are not available. Export flags may be off.
```

Example next actions:

```text
Review high impact management issues.
Validate Cost / KPI assumptions before using estimates.
Consider replan candidates manually; they are not executed automatically.
```

---

## 20. Empty State Behavior

If:

```python
view_model["available"] is False
```

the window should still open and show:

```text
No explicit pipeline reporting data is available.
Run planning with explicit pipeline enabled.
```

The view must not crash.

This is important because a user may open the view before running planning.

---

## 21. Formatting Rules

### 21.1 Numeric formatting

Suggested display:

```text
0.0
1,234.0
1,234,567.0
```

No currency conversion.

### 21.2 List formatting

For `lot_ids` or list fields:

```text
join with comma
```

Example:

```text
LOT001, LOT002, LOT003
```

### 21.3 Dict formatting

For small dict fields:

```text
JSON string or compact str()
```

For MVP, use safe string conversion.

### 21.4 Boolean formatting

Display as:

```text
Yes / No
```

or:

```text
Available / Not available
```

---

## 22. Read-Only Treeview Behavior

All Treeviews should be read-only.

Allowed:

```text
select row
scroll
copy maybe later
```

Not allowed:

```text
edit cell
execute command
modify data
```

MVP does not need row detail popups.

---

## 23. Safety Boundaries

The Tk rendering code must not:

```text
mutate env
run planning
run reporting stack
run exports
execute ReplanCommand
change feature flags
write files
open files
delete files
persist data
```

It may:

```text
build view model from env
render labels
render tree rows
render read-only text
```

---

## 24. Relationship to Existing Management Cockpit

This explicit pipeline KPI view should complement, not replace, existing Management Cockpit / business report functionality.

Positioning:

```text
Explicit Pipeline KPI View
    = diagnostic and management issue view for explicit bridge + capacity planning
```

Existing business reporting may still handle:

```text
financial summary
cost waterfall
allocation breakdown
business report
```

The explicit KPI view focuses on:

```text
capacity-risk-driven issue candidates and directional impact
```

---

## 25. Test Strategy

Testing should avoid brittle visual GUI assertions where possible.

Recommended test levels:

```text
1. View-model tests already exist.
2. Rendering helper smoke test can instantiate Tk root in a safe way if supported.
3. If Tk is unavailable in CI, keep rendering tests lightweight or skip with clear condition.
```

MVP test options:

```python
pytest.importorskip("tkinter")
```

or skip if no display is available.

Because the existing environment appears to run Tk-related tests indirectly, a simple Toplevel creation test may be acceptable.

---

## 26. Recommended Tests

Add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py
```

Suggested tests:

### 26.1 Render empty view model

Build empty/no-data view model and render it.

Verify:

```text
Toplevel is created
window title contains "Explicit Pipeline"
no exception
```

### 26.2 Render synthetic populated view model

Use a small synthetic view model with:

```text
one top issue
one replan candidate
one health issue
one message
one next action
```

Verify:

```text
Toplevel is created
no exception
```

### 26.3 No side effects

Use an env object with sentinel flags.

Call view opener.

Verify:

```text
flags unchanged
no new reporting/export objects created
```

### 26.4 View model function remains independent

Existing tests for:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view.py
```

must still pass.

---

## 27. Suggested Implementation Phases

### 27.1 Phase A: Rendering helper only

Add render helper to:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

Do not modify `cockpit_tk.py`.

This allows testing the rendering helper separately.

### 27.2 Phase B: Cockpit entry method

Add a small method in `cockpit_tk.py`:

```python
_open_explicit_pipeline_kpi_view(self)
```

No button yet, or attach to an existing debug/manual path.

### 27.3 Phase C: Button integration

Add a button:

```text
Explicit KPI View
```

to open the read-only view.

### 27.4 Phase D: Usability refinement

Add:

```text
column sizing
scrollbars
detail view
copy to clipboard
filtering
```

later.

---

## 28. Recommended First Codex Request Scope

Recommended first Codex Request for implementation:

```text
Tk rendering helper only
```

Files:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py
```

Do not modify:

```text
pysi/gui/cockpit_tk.py
```

in the first request.

This keeps rendering isolated and testable.

A later request can connect it to `cockpit_tk.py`.

---

## 29. Future Cockpit Integration Request

After rendering helper is stable, a separate request can add:

```text
_open_explicit_pipeline_kpi_view(self)
```

to:

```text
pysi/gui/cockpit_tk.py
```

and a button/menu entry.

That second request should be constrained to:

```text
open view only
no planning execution
no export execution
no command execution
```

---

## 30. Completion Criteria for This Design

This design is complete when it defines:

```text
[OK] purpose of Tk rendering phase
[OK] read-only safety rule
[OK] non-goals
[OK] recommended functions
[OK] recommended tabs / layout
[OK] table columns
[OK] empty-state behavior
[OK] formatting rules
[OK] safety boundaries
[OK] test strategy
[OK] implementation phase split
[OK] first Codex request scope
```

---

## 31. Summary

The Management Cockpit KPI View Model is complete.

This design defines how to render it safely in Tk.

The key rule is:

```text
Render what exists.
Do not execute anything.
```

The recommended next implementation is:

```text
Tk rendering helper only
```

not:

```text
button integration
planning execution
export execution
replanning
```

In cockpit terms:

```text
The signal model is ready.
Now build the display panel.
Do not wire the display panel to the engine starter.
```
