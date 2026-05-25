# Codex Request: Integrate Explicit Pipeline Management Cockpit KPI View Button into cockpit_tk.py

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_view_button_integration.md
```

Please read this design memo first.

The Explicit Pipeline Management Cockpit KPI View has already been implemented in two staged parts.

### 1.1 View model

Implemented in:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

Main function:

```python
build_explicit_pipeline_management_cockpit_view_model(env) -> dict
```

This builds a read-only management cockpit view model from existing explicit pipeline artifacts on `env`.

### 1.2 Tk rendering helper

Implemented in the same module:

```python
render_explicit_pipeline_management_cockpit_tk(parent, view_model) -> tk.Toplevel
```

This renders the already-built view model as a read-only Tk window.

The rendering helper has already been tested independently.

This request is for the final small integration step:

```text
Add a cockpit_tk.py entry point and user-accessible button/menu entry
to open the read-only Explicit Pipeline KPI View.
```

This request is **not** for new planning logic.

This request is **not** for running exports.

This request is **not** for command execution.

---

## 2. Main Objective

Modify:

```text
pysi/gui/cockpit_tk.py
```

to add a small entry point method on `WOMCockpit`:

```python
def _open_explicit_pipeline_kpi_view(self):
    ...
```

The method should:

```text
1. Build the current explicit pipeline KPI view model from self.env.
2. Render it using the existing read-only Tk rendering helper.
3. Return the Toplevel object returned by the renderer.
```

Conceptual implementation:

```python
def _open_explicit_pipeline_kpi_view(self):
    from pysi.gui.explicit_pipeline_management_cockpit_view import (
        build_explicit_pipeline_management_cockpit_view_model,
        render_explicit_pipeline_management_cockpit_tk,
    )

    view_model = build_explicit_pipeline_management_cockpit_view_model(self.env)
    return render_explicit_pipeline_management_cockpit_tk(self, view_model)
```

Also add one user-accessible button or menu entry labeled:

```text
Explicit KPI View
```

The button should only call:

```python
self._open_explicit_pipeline_kpi_view
```

---

## 3. Important Constraints

Please follow these constraints strictly:

```text
1. Do not run planning.
2. Do not run Run Full Plan.
3. Do not run the explicit pipeline.
4. Do not run the reporting stack helper.
5. Do not run any export helper.
6. Do not change feature flags.
7. Do not mutate env beyond normal read-only view construction.
8. Do not execute ReplanCommand.
9. Do not implement automatic replanning.
10. Do not implement OR optimization.
11. Do not implement database persistence.
12. Do not implement Knowledge Continuity persistence.
13. Do not modify Cost / KPI enrichment logic.
14. Do not modify exporter logic.
15. Do not modify the existing rendering helper unless a tiny compatibility fix is necessary.
```

This request is only for:

```text
main cockpit entry point / button integration
```

The button is a viewer button, not an engine-start button.

---

## 4. Files to Modify / Add

Please modify:

```text
pysi/gui/cockpit_tk.py
```

Please add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view_button_integration.py
```

Avoid modifying:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
pysi/reporting/*
pysi/plan/*
```

unless a tiny compatibility issue is genuinely necessary.

---

## 5. Existing Helpers to Reuse

Reuse these existing helpers:

```python
build_explicit_pipeline_management_cockpit_view_model
render_explicit_pipeline_management_cockpit_tk
```

from:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

Do not duplicate view-model or rendering logic in `cockpit_tk.py`.

---

## 6. Recommended Entry Point Method

Add this method to `WOMCockpit`:

```python
def _open_explicit_pipeline_kpi_view(self):
    from pysi.gui.explicit_pipeline_management_cockpit_view import (
        build_explicit_pipeline_management_cockpit_view_model,
        render_explicit_pipeline_management_cockpit_tk,
    )

    view_model = build_explicit_pipeline_management_cockpit_view_model(self.env)
    return render_explicit_pipeline_management_cockpit_tk(self, view_model)
```

Implementation notes:

```text
Use local import to keep cockpit_tk.py top-level imports stable.
Return the Toplevel object to make testing easy.
Do not pre-check whether data exists.
Let the view model and renderer handle no-data behavior.
```

If the local project style strongly prefers top-level imports, use project style, but local import is recommended.

---

## 7. Button Label and Placement

Add one user-accessible button labeled:

```text
Explicit KPI View
```

Preferred placement:

```text
near existing Management Cockpit / reporting / Run Full Plan related controls
```

Codex should inspect the current `cockpit_tk.py` layout and choose the smallest consistent placement.

Important layout constraints:

```text
Do not reorganize the GUI.
Do not move existing buttons.
Do not rename existing buttons.
Do not change existing command bindings.
Do not change existing layout semantics.
```

A small additional button is enough.

---

## 8. Button Command

The new button command must be:

```python
command=self._open_explicit_pipeline_kpi_view
```

or equivalent.

Do not use a command that also runs:

```text
planning
reporting stack
exports
replan
optimization
```

The button should only open the view.

---

## 9. Empty Data Behavior

If the user clicks the button before running planning or before enabling explicit pipeline reporting:

```text
The read-only view should still open.
```

The existing view model and renderer already support this no-data case.

Do not block the button.

Do not show a separate warning popup.

Let the KPI view window display the no-data message.

Expected behavior:

```text
User clicks Explicit KPI View
    ↓
Window opens
    ↓
Message says no explicit pipeline reporting data is available
```

---

## 10. Expected User Flow

### 10.1 No explicit pipeline data

```text
Open WOM GUI
Click Explicit KPI View
Read-only window opens
No-data message is shown
```

### 10.2 After planning with explicit pipeline reporting flags

```text
Run planning
Explicit pipeline artifacts are attached to env
Click Explicit KPI View
Read-only window opens
Summary / Top Issues / Replan Candidates / Health / Assumptions / Messages tabs are shown
```

### 10.3 Partial data

```text
Only some artifacts are available
Click Explicit KPI View
Available sections show data
Missing sections show safe default messages
```

---

## 11. Safety Boundaries

The entry point and button must not:

```text
mutate env
run planning
run explicit pipeline
run reporting stack
run exports
execute ReplanCommand
change feature flags
write files
open files
delete files
persist data
```

They may:

```text
read self.env
build a view model
render a read-only Tk Toplevel
return the Toplevel
```

---

## 12. Relationship to Feature Flags

The button should not change feature flags.

The view displays whatever has already been generated by previous planning runs and flags, such as:

```text
enable_explicit_bridge_capacity_report
enable_explicit_bridge_capacity_report_export
enable_explicit_bridge_capacity_issue_candidates
enable_explicit_bridge_capacity_issue_candidate_export
enable_explicit_bridge_capacity_issue_candidate_cost_kpi
enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export
```

The button only displays current state.

It should not enable or disable anything.

---

## 13. Relationship to Exports

The button should not run export helpers.

If export result objects already exist on env, the view may display them.

If they do not exist, the view may display a message such as:

```text
Export results are not available. Export flags may be off.
```

Do not create export files from the button.

---

## 14. Relationship to Replan Candidates

The view may display replan candidates.

But the button must not execute them.

The status:

```text
candidate_only
```

must remain a display-only concept.

No run button.

No double-click execution.

No command execution.

---

## 15. Test Strategy

Add focused tests for the entry point method.

Avoid brittle full GUI visual tests.

Recommended test style:

```text
Monkeypatch the builder and renderer.
Call WOMCockpit._open_explicit_pipeline_kpi_view(fake_self).
Verify the builder receives fake_self.env.
Verify the renderer receives fake_self and the returned view model.
Verify the method returns the renderer's return value.
```

This validates the important integration contract without opening a real Tk window.

---

## 16. Recommended Test File

Add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view_button_integration.py
```

The test can use:

```python
from types import SimpleNamespace

from pysi.gui.cockpit_tk import WOMCockpit
```

Then call the method as an unbound method:

```python
result = WOMCockpit._open_explicit_pipeline_kpi_view(fake_self)
```

where:

```python
fake_self = SimpleNamespace(env=fake_env)
```

This avoids constructing the full GUI.

---

## 17. Recommended Test Case

Suggested test:

```python
def test_open_explicit_pipeline_kpi_view_calls_builder_and_renderer(monkeypatch):
    calls = {}

    fake_env = object()
    fake_self = SimpleNamespace(env=fake_env)
    fake_view_model = {"available": True}
    fake_window = object()

    def fake_builder(env):
        calls["env"] = env
        return fake_view_model

    def fake_renderer(parent, view_model):
        calls["parent"] = parent
        calls["view_model"] = view_model
        return fake_window

    monkeypatch.setattr(
        "pysi.gui.explicit_pipeline_management_cockpit_view.build_explicit_pipeline_management_cockpit_view_model",
        fake_builder,
    )
    monkeypatch.setattr(
        "pysi.gui.explicit_pipeline_management_cockpit_view.render_explicit_pipeline_management_cockpit_tk",
        fake_renderer,
    )

    result = WOMCockpit._open_explicit_pipeline_kpi_view(fake_self)

    assert result is fake_window
    assert calls["env"] is fake_env
    assert calls["parent"] is fake_self
    assert calls["view_model"] is fake_view_model
```

This test proves:

```text
self.env is used
renderer receives self as parent
view model is passed through
return value is preserved
```

---

## 18. Button Presence Test

Testing exact Tk layout may be brittle.

A simple code-level assertion may be enough if project style allows it.

Possible options:

```text
1. Rely on code review for button placement.
2. Add a light text-source assertion that "Explicit KPI View" appears in cockpit_tk.py.
3. Follow any existing GUI button test style if available.
```

Recommended MVP:

```text
entry-point method test + code review of one-button diff
```

Avoid constructing the full cockpit unless existing tests already do so safely.

---

## 19. Tests to Run

Please run:

```bat
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

## 20. Completion Criteria

This request is complete when:

```text
[OK] WOMCockpit has _open_explicit_pipeline_kpi_view method
[OK] method builds view model from self.env
[OK] method renders read-only Tk view
[OK] method returns renderer return value
[OK] GUI has one user-accessible button or menu entry
[OK] button label is clear, e.g. Explicit KPI View
[OK] button only opens the view
[OK] no planning execution is added
[OK] no explicit pipeline execution is added
[OK] no reporting stack execution is added
[OK] no export execution is added
[OK] no ReplanCommand execution is added
[OK] no feature flags are changed
[OK] no env mutation beyond read-only view construction
[OK] entry-point tests pass
[OK] existing view-model and rendering tests pass
[OK] key regression tests pass
```

---

## 21. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Exact entry point method added
3. Exact button/menu placement
4. Button label
5. Safety boundaries preserved
6. Tests added
7. Test commands executed
8. Test results
9. Any skipped tests and why
10. Limitations / follow-up
```

Please do not proceed into:

```text
graph / chart view
KPI cards
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
Explicit Pipeline Management Cockpit KPI View Button Integration MVP
```
