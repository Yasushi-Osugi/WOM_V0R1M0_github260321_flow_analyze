# Explicit Pipeline Management Cockpit KPI View Tk Rendering Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-24  
**Status:** Completion memo  
**Target path:** `docs/design/explicit_pipeline_management_cockpit_kpi_view_tk_rendering_completion.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Explicit Pipeline Management Cockpit KPI View Tk Rendering Helper MVP**.

The purpose of this milestone was to implement a read-only Tk rendering helper for the already-completed Management Cockpit KPI View Model.

The existing view-model builder is:

```python
build_explicit_pipeline_management_cockpit_view_model(env) -> dict
```

The newly completed Tk rendering helper is:

```python
render_explicit_pipeline_management_cockpit_tk(parent, view_model) -> tk.Toplevel
```

implemented in:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

This milestone creates the display panel for the cockpit data model.

It does not connect the panel to the main cockpit button yet.

---

## 2. Background

Before this milestone, WOM had already completed the following chain:

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
```

The missing layer was a safe read-only Tk rendering helper that can display the view model without triggering planning or command execution.

This milestone completes that helper.

---

## 3. Implemented Files

This milestone updated or added:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py
```

The implementation was committed as:

```text
8159352 Add read-only Tk rendering helper for explicit pipeline KPI cockpit view
```

---

## 4. Main Implemented Function

The new rendering function is:

```python
render_explicit_pipeline_management_cockpit_tk(parent, view_model) -> tk.Toplevel
```

The function:

```text
creates a Tk Toplevel window
sets title and geometry
renders the provided view_model only
uses read-only labels / Treeviews / text-like sections
returns the Toplevel object
```

It consumes the view model produced by:

```python
build_explicit_pipeline_management_cockpit_view_model(env)
```

It does not read env directly.

It does not mutate env.

---

## 5. Rendering Layout Implemented

The renderer uses a `ttk.Notebook` tab layout.

Here, `Notebook` means:

```text
Tkinter standard ttk.Notebook tab widget
```

not Jupyter Notebook.

Implemented tabs:

```text
Summary
Top Issues
Replan Candidates
Health
Assumptions / Exports
Messages
```

This makes the cockpit view compact and organized without changing the main WOM GUI.

---

## 6. Summary Tab

The Summary tab renders compact key-value sections from the view model.

Primary sections:

```text
Status
Executive KPI
Capacity Summary
Issue Summary
```

The tab displays values such as:

```text
product
available
explicit pipeline result availability
capacity report availability
issue candidate availability
Cost / KPI bundle availability
currency
estimated total business impact
capacity violation count
lot exception count
planning issue count
management issue count
warning / error counts
```

The display is read-only.

---

## 7. Top Issues Tab

The Top Issues tab renders:

```text
view_model["top_impact_issues"]
```

as a read-only `ttk.Treeview`.

Representative columns include:

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

If no top issues exist, the renderer displays an empty-state message.

This tab is intended to become the central management attention table.

---

## 8. Replan Candidates Tab

The Replan Candidates tab renders:

```text
view_model["replan_candidates"]
```

as a read-only table.

The status field remains visible.

Important rule preserved:

```text
candidate_only remains candidate_only
```

No execute button was added.

No run button was added.

No double-click command behavior was added.

---

## 9. Health Tab

The Health tab renders health / data quality information from:

```text
view_model["health_summary"]
```

It can show:

```text
health issue count
data quality risk issue count
missing lot count
has_error
has_warning
top health issues
```

Top health issues are displayed as read-only rows.

This supports future review of planning evidence quality.

---

## 10. Assumptions / Exports Tab

The Assumptions / Exports tab renders:

```text
view_model["assumption_summary"]
view_model["export_summary"]
```

Assumption summary is shown in compact key-value form.

Export result summaries are displayed as text / key-value sections.

The renderer displays file paths as text only.

It does not:

```text
open files
verify files on disk
create files
run exports
```

---

## 11. Messages Tab

The Messages tab renders:

```text
view_model["messages"]
view_model["next_review_actions"]
```

This includes caveats and recommended review actions such as:

```text
Cost / KPI values are directional scenario estimates, not formal accounting values.
Double counting may be possible depending on assumptions.
Review high impact management issues.
Consider replan candidates manually; they are not executed automatically.
```

These are read-only review prompts.

---

## 12. Formatting Helpers Implemented

The rendering helper added deterministic UI formatting utilities such as:

```text
_format_value
_bool_label
_rows_from_dict
_insert_tree_rows
_create_key_value_tree
_create_table
```

These helpers support consistent formatting of:

```text
booleans
numbers
lists
dicts
generic row dictionaries
Treeview rows
key-value sections
```

The formatting layer is intentionally simple and deterministic.

---

## 13. Empty-State Behavior

If the view model is unavailable:

```python
view_model["available"] is False
```

the Toplevel window still opens.

The renderer displays a clear no-data message rather than raising an exception.

This is important because users may open the cockpit view before running the explicit pipeline.

---

## 14. Safety Boundaries Preserved

This milestone preserved the intended safety boundaries.

It did not modify:

```text
pysi/gui/cockpit_tk.py
```

It did not add:

```text
button integration
menu integration
main GUI layout changes
planning execution
explicit pipeline execution
reporting stack execution
export execution
feature flag mutation
ReplanCommand execution
automatic replanning
OR optimization
database persistence
Knowledge Continuity persistence
```

The renderer only consumes a provided view model and displays it.

---

## 15. Tests Added

The focused rendering test file is:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py
```

It covers:

```text
1. no-data rendering
2. populated view-model rendering
3. candidate_only visibility / no side effects
```

The tests use a safe Tk initialization helper.

If Tk is unavailable, the tests can skip safely.

In the local Windows GUI environment, the focused tests passed.

---

## 16. Test Issue Found and Fixed

During local testing, one test issue was found.

Failure:

```text
StopIteration in test_candidate_only_visibility_and_no_side_effects
```

Cause:

```text
The test assumed a direct tk.Frame child under the Toplevel window.
The implementation used ttk widgets / ttk.Notebook.
```

Fix:

```text
Change the test to search recursively for ttk.Notebook instead of assuming tk.Frame as a direct child.
```

This was a test-harness issue, not a rendering logic issue.

After the test fix, the rendering test passed:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py: 3 passed
```

---

## 17. Validation

The focused rendering test passed:

```bat
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py
```

Observed result:

```text
3 passed
```

The following key regression tests were also run after the final rendering test fix:

```bat
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_view.py
python -m pytest tests/test_explicit_pipeline_reporting_stack_insertion.py
python -m pytest tests/test_explicit_pipeline_reporting_flags.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view.py: 8 passed
tests/test_explicit_pipeline_reporting_stack_insertion.py: 7 passed
tests/test_explicit_pipeline_reporting_flags.py: 10 passed
tests/test_covid_vaccine_with_capacity_push.py: 1 passed
```

Earlier in the Codex execution summary, the broader non-optional regression batch also passed before the final local test-harness fix, with Tk rendering tests skipped where Tk was unavailable.

The final local acceptance confirmed the corrected rendering test on a Windows GUI-capable environment.

---

## 18. Completion Criteria

This milestone satisfies the intended completion criteria.

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
[OK] candidate_only remains visible
[OK] no cockpit_tk.py modification
[OK] no button added
[OK] no planning execution
[OK] no export execution
[OK] no ReplanCommand execution
[OK] focused rendering tests pass locally
[OK] key regression tests pass
```

---

## 19. Meaning of This Milestone

Before this milestone:

```text
WOM had a Management Cockpit KPI view model, but no Tk display panel.
```

After this milestone:

```text
WOM has a read-only Tk rendering helper for the Management Cockpit KPI view model.
```

This means WOM now has a displayable cockpit panel component, though it is not yet connected to the main cockpit button.

The integration remains intentionally staged:

```text
view model
    ↓
read-only Tk rendering helper
    ↓
future cockpit_tk.py entry point / button integration
```

---

## 20. Current Pipeline Position

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
cockpit_tk.py entry point / button integration
```

---

## 21. Current Operational Meaning

WOM can now do the following:

```text
explicit pipeline artifacts
    ↓
Management Cockpit KPI view model
    ↓
read-only Tk rendering helper
```

The renderer can display:

```text
summary
top impact issues
replan candidates
health / data quality
assumptions
export summary
messages
next review actions
```

without running planning, exports, or commands.

This is the display panel component for the future cockpit.

---

## 22. Known Limitations

This milestone is intentionally limited.

It does not yet implement:

```text
cockpit_tk.py integration
button / menu entry
automatic window opening after planning
interactive filtering
row detail popup
copy-to-clipboard
file open links
issue review workflow
Knowledge Continuity capture
ReplanCommand execution
```

The helper is available, but the user still needs a future entry point to open it from the main GUI.

---

## 23. Future Milestones

### 23.1 Cockpit entry method

A natural next design phase is:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_view_button_integration.md
```

This should define a small method in `WOMCockpit`, for example:

```python
_open_explicit_pipeline_kpi_view(self)
```

which should:

```text
build the view model from self.env
call the rendering helper
not run planning
not run exports
not execute commands
```

### 23.2 Button / menu integration

A later implementation can add a button:

```text
Explicit KPI View
```

or equivalent menu item.

The button should only open the read-only view.

### 23.3 Usability improvements

Future improvements can include:

```text
column sizing
scrollbars
copy selected row
detail pane
filter by severity
filter by node
filter by issue type
file path open buttons
```

These should remain separate from the MVP rendering helper.

### 23.4 Knowledge Continuity integration

Future review workflow can use cockpit artifacts to generate:

```text
open issues
decision log candidates
next-entry prompts
facts and findings
```

This should remain explicitly controlled by a future design and feature flag.

---

## 24. Summary

The Explicit Pipeline Management Cockpit KPI View Tk Rendering Helper MVP is complete.

The key achievement is:

```text
WOM now has a read-only Tk display helper for the explicit pipeline Management Cockpit KPI view model.
```

The implementation remains safely non-invasive:

```text
no cockpit_tk.py changes
no button integration
no planning execution
no export execution
no command execution
```

The cockpit display panel has passed its local factory test.

The next phase can attach it to the main cockpit, still with the engine-start switch safely covered.
