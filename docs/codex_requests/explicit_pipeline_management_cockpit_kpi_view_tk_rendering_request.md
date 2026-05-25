# Codex Request: Implement Explicit Pipeline Management Cockpit KPI View Tk Rendering Helper MVP

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_view_tk_rendering.md
```

Please read this design memo first.

The Management Cockpit KPI View Model has already been implemented:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
tests/test_explicit_pipeline_management_cockpit_kpi_view.py
```

The existing view-model builder is:

```python
build_explicit_pipeline_management_cockpit_view_model(env) -> dict
```

This request is for the next small step:

```text
render the already-built view model in a read-only Tk window
```

This request is **not** for button integration.

This request is **not** for modifying `cockpit_tk.py`.

This request is only for:

```text
Tk rendering helper only + focused rendering tests
```

---

## 2. Main Objective

Add a read-only Tk rendering helper that takes an existing view model and displays it in a `tk.Toplevel` window.

Target function:

```python
render_explicit_pipeline_management_cockpit_tk(parent, view_model: dict) -> tk.Toplevel
```

Target module to update:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

Target test file to add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py
```

The renderer should consume the dictionary produced by:

```python
build_explicit_pipeline_management_cockpit_view_model(env)
```

It should not build or mutate planning data.

---

## 3. Important Constraints

Please follow these constraints strictly:

```text
1. Do not modify pysi/gui/cockpit_tk.py.
2. Do not add a button.
3. Do not add menu integration.
4. Do not run planning.
5. Do not run explicit pipeline.
6. Do not run reporting stack helper.
7. Do not trigger exports.
8. Do not change feature flags.
9. Do not mutate env.
10. Do not execute ReplanCommand.
11. Do not implement automatic replanning.
12. Do not implement OR optimization.
13. Do not implement database persistence.
14. Do not implement Knowledge Continuity persistence.
15. Do not modify Cost / KPI enrichment logic.
16. Do not modify exporter logic.
```

This request is only for:

```text
read-only Tk rendering helper + tests
```

---

## 4. Files to Modify / Add

Please modify:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

Please add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py
```

Do not modify:

```text
pysi/gui/cockpit_tk.py
pysi/reporting/*
pysi/plan/*
```

unless a tiny import issue is absolutely unavoidable.

---

## 5. Existing Function to Keep

The existing function must remain available and unchanged in behavior:

```python
build_explicit_pipeline_management_cockpit_view_model(env) -> dict
```

Do not change its schema or semantics unless required for a tiny compatibility fix.

The new renderer should consume the existing schema:

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

---

## 6. New Function to Add

Please add:

```python
def render_explicit_pipeline_management_cockpit_tk(parent, view_model: dict):
    ...
```

Return:

```python
tk.Toplevel
```

The function should:

```text
create a Toplevel window
set a clear title
render the view model in read-only form
return the Toplevel object
```

Recommended title:

```text
Explicit Pipeline Management Cockpit KPI View
```

or:

```text
Explicit Pipeline KPI View
```

---

## 7. Recommended Window Layout

Use `tkinter` / `ttk`.

Recommended layout:

```text
Toplevel
    ttk.Frame
        ttk.Notebook
            Summary tab
            Top Issues tab
            Replan Candidates tab
            Health tab
            Assumptions / Exports tab
            Messages tab
```

MVP can use this tab structure.

If a simpler layout is needed, a single scrollable window is acceptable, but Notebook is preferred.

---

## 8. Summary Tab

Source fields:

```python
view_model["status"]
view_model["executive_kpi_summary"]
view_model["capacity_summary"]
view_model["issue_summary"]
view_model["product"]
view_model["available"]
```

Display as read-only labels or a two-column `ttk.Treeview`.

Suggested groups:

```text
Status
Executive KPI
Capacity Summary
Issue Summary
```

Recommended display values:

```text
Product
Available
Explicit Pipeline Result
Capacity Report
Issue Candidates
Cost / KPI Bundle
Total Business Impact
Currency
Capacity Violations
Lot Exceptions
Planning Issues
Management Issues
Warnings
Errors
```

Use safe string formatting.

---

## 9. Top Issues Tab

Source:

```python
view_model["top_impact_issues"]
```

Render as read-only `ttk.Treeview`.

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

If no rows exist, show a simple message:

```text
No top impact issues are available.
```

Do not add double-click behavior.

Do not add execute behavior.

---

## 10. Replan Candidates Tab

Source:

```python
view_model["replan_candidates"]
```

Render as read-only `ttk.Treeview`.

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

Important rule:

```text
candidate_only must remain visible when present.
```

No execute button.

No run button.

No double-click command behavior.

---

## 11. Health Tab

Source:

```python
view_model["health_summary"]["top_health_issues"]
```

Render as read-only `ttk.Treeview`.

Recommended columns:

```text
severity
issue_type
source
message
details
```

Also show summary counts if convenient:

```text
health_issue_count
data_quality_risk_issue_count
missing_lot_count
has_error
has_warning
```

---

## 12. Assumptions / Exports Tab

Source:

```python
view_model["assumption_summary"]
view_model["export_summary"]
```

MVP display may use key-value Treeviews or read-only text areas.

Assumption fields:

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

Export groups:

```text
capacity_report_export
issue_candidate_export
cost_kpi_export
```

For each export group, display:

```text
available
output_dir
file_count
summary_path
assumptions_path
message
```

Display paths as text only.

Do not open files.

Do not verify files on disk.

Do not create files.

---

## 13. Messages Tab

Source:

```python
view_model["messages"]
view_model["next_review_actions"]
```

Render as read-only text or Treeview.

Suggested sections:

```text
Messages
Next Review Actions
```

The messages should include caveats such as:

```text
Cost / KPI values are directional scenario estimates, not formal accounting values.
Double counting may be possible depending on assumptions.
```

---

## 14. Empty State Behavior

If:

```python
view_model["available"] is False
```

the renderer should still open a Toplevel window and show a clear message.

Example:

```text
No explicit pipeline reporting data is available.
Run planning with explicit pipeline enabled.
```

The function must not raise.

---

## 15. Formatting Helpers

It is fine to add small private helpers in the module.

Recommended helpers:

```python
_format_value(value) -> str
_bool_label(value) -> str
_rows_from_dict(data: dict) -> list[tuple[str, str]]
_insert_tree_rows(tree, rows)
_create_key_value_tree(parent, rows)
_create_table(parent, columns, rows)
```

Formatting rules:

```text
None -> ""
bool -> Yes / No
list -> comma-separated string
dict -> compact string
float/int -> string with comma grouping where appropriate
Path/string -> string
```

Keep formatting deterministic.

---

## 16. Scrollbars

For MVP, add vertical scrollbars for Treeviews if simple.

If scrollbars add too much complexity, omit them only if the window remains usable.

Recommended:

```text
Treeview + vertical scrollbar
```

Horizontal scrolling is optional.

---

## 17. Window Size

Set a reasonable default geometry, for example:

```text
1100x700
```

or:

```text
1200x750
```

Do not make it fullscreen.

---

## 18. Safety Boundaries

The rendering function must not:

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
read the provided view_model
render labels
render Treeviews
render read-only messages
return Toplevel
```

---

## 19. Test Strategy

Add focused tests for the rendering helper.

Testing Tk can be environment-sensitive.

Please use safe skip behavior when Tk cannot initialize.

Recommended helper in tests:

```python
def _make_root_or_skip():
    try:
        root = tk.Tk()
        root.withdraw()
        return root
    except tk.TclError as exc:
        pytest.skip(f"Tk unavailable: {exc}")
```

Destroy windows after tests.

Use:

```python
window.destroy()
root.destroy()
```

in finally blocks where appropriate.

---

## 20. Tests to Add

Please add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py
```

### 20.1 Render no-data model

Create a minimal no-data view model, or use:

```python
build_explicit_pipeline_management_cockpit_view_model(SimpleNamespace())
```

Render it.

Verify:

```text
Toplevel is returned
window title contains "Explicit Pipeline"
no exception
```

### 20.2 Render populated model

Create a synthetic populated view model with:

```text
one top impact issue
one replan candidate
one health issue
assumption summary
export summary
messages
next review actions
```

Render it.

Verify:

```text
Toplevel is returned
no exception
```

### 20.3 Candidate-only visibility

If feasible, verify the rendered table contains:

```text
candidate_only
```

This can be done by inspecting Treeview values, or keep it at view-model level if Tk introspection is too brittle.

### 20.4 No side effects

Use a view model copy.

Render it.

Verify:

```text
view model remains structurally unchanged
```

No env object is required for renderer tests.

---

## 21. Existing Tests to Run

Please run:

```bat
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py
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

If Tk rendering tests are skipped because Tk is unavailable, state so clearly.

---

## 22. Completion Criteria

This request is complete when:

```text
[OK] render_explicit_pipeline_management_cockpit_tk(parent, view_model) exists
[OK] renderer returns tk.Toplevel
[OK] renderer consumes view model only
[OK] renderer does not mutate view model
[OK] renderer displays Summary
[OK] renderer displays Top Issues
[OK] renderer displays Replan Candidates
[OK] renderer displays Health
[OK] renderer displays Assumptions / Exports
[OK] renderer displays Messages / Next Actions
[OK] empty model renders without crashing
[OK] populated model renders without crashing
[OK] no cockpit_tk.py modification
[OK] no button added
[OK] no planning execution
[OK] no export execution
[OK] no ReplanCommand execution
[OK] focused tests pass or are clearly skipped only when Tk is unavailable
[OK] existing view-model tests still pass
```

---

## 23. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. Renderer function added
4. Tabs / sections implemented
5. Empty-state behavior
6. Safety boundaries preserved
7. Test commands executed
8. Test results
9. Any skipped tests and why
10. Limitations / follow-up
```

Please do not proceed into:

```text
cockpit_tk.py modification
button integration
menu integration
planning execution
export execution
OR optimization
database persistence
ReplanCommand execution
Knowledge Continuity persistence
```

This request is only for:

```text
Explicit Pipeline Management Cockpit KPI View Tk Rendering Helper MVP
```
