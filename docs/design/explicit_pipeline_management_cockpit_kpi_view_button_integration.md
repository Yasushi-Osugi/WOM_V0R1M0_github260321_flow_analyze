# Explicit Pipeline Management Cockpit KPI View Button Integration Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-24  
**Status:** Design memo  
**Target path:** `docs/design/explicit_pipeline_management_cockpit_kpi_view_button_integration.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/explicit_pipeline_management_cockpit_kpi_view.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view_completion.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view_tk_rendering.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view_tk_rendering_completion.md`
- `docs/codex_requests/explicit_pipeline_management_cockpit_kpi_view_tk_rendering_request.md`
- `docs/design/explicit_pipeline_planning_sequence_reporting_stack_insertion.md`
- `docs/design/explicit_pipeline_planning_sequence_reporting_stack_insertion_completion.md`
- `docs/design/explicit_pipeline_reporting_issue_cost_kpi_overview.md`
- `docs/design/wom_knowledge_continuity_layer.md`

---

## 1. Purpose

This memo defines the design for integrating the already-completed Explicit Pipeline Management Cockpit KPI View into the main WOM cockpit GUI.

The completed components are:

```python
build_explicit_pipeline_management_cockpit_view_model(env) -> dict
render_explicit_pipeline_management_cockpit_tk(parent, view_model) -> tk.Toplevel
```

implemented in:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

The next step is to add a small entry point in:

```text
pysi/gui/cockpit_tk.py
```

so that the user can open the read-only Explicit Pipeline KPI View from the main GUI.

This design is for:

```text
cockpit_tk.py entry point / button integration
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
cockpit_tk.py entry point / button integration   ← current design target
```

The KPI view can already be rendered as a standalone read-only Tk window if supplied with a view model.

The missing step is a GUI entry point.

---

## 3. Design Goal

The goal is to add a user-accessible way to open the read-only Explicit Pipeline KPI View from the main WOM cockpit GUI.

The intended behavior is:

```text
User clicks "Explicit KPI View" button
    ↓
WOM builds a view model from current self.env
    ↓
WOM renders the read-only Tk KPI view window
```

Conceptual method:

```python
def _open_explicit_pipeline_kpi_view(self):
    view_model = build_explicit_pipeline_management_cockpit_view_model(self.env)
    render_explicit_pipeline_management_cockpit_tk(self, view_model)
```

This is a display operation only.

---

## 4. Non-Goals

This phase must not implement:

```text
Run Full Plan execution
explicit pipeline execution
reporting stack execution
file export execution
Cost / KPI recalculation
issue candidate generation
automatic replanning
ReplanCommand execution
OR optimization
database persistence
Knowledge Continuity persistence
approval workflow
formal issue review workflow
graph/chart rendering
```

This phase is only:

```text
open existing read-only view
```

---

## 5. Core Safety Rule

The button must be:

```text
a viewer button
```

not:

```text
an engine start button
```

It must only:

```text
build the view model from current env
render the read-only KPI view
```

It must not:

```text
run planning
run exports
change flags
execute commands
modify env
```

The cockpit should behave like a dashboard instrument panel, not a hidden control launcher.

---

## 6. Recommended Implementation Scope

Recommended files to modify:

```text
pysi/gui/cockpit_tk.py
```

Recommended tests to add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view_button_integration.py
```

Existing helper module to import:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

Functions to import:

```python
build_explicit_pipeline_management_cockpit_view_model
render_explicit_pipeline_management_cockpit_tk
```

Do not modify:

```text
pysi/reporting/*
pysi/plan/*
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

unless a small import compatibility fix is necessary.

---

## 7. Proposed Entry Point Method

Add a method to `WOMCockpit`:

```python
def _open_explicit_pipeline_kpi_view(self):
    from pysi.gui.explicit_pipeline_management_cockpit_view import (
        build_explicit_pipeline_management_cockpit_view_model,
        render_explicit_pipeline_management_cockpit_tk,
    )

    view_model = build_explicit_pipeline_management_cockpit_view_model(self.env)
    return render_explicit_pipeline_management_cockpit_tk(self, view_model)
```

Recommended points:

```text
Use local import to minimize startup impact.
Return the Toplevel window for testability.
Do not pre-validate whether explicit pipeline data exists.
Let the view model and renderer handle no-data state.
```

---

## 8. Import Placement

To minimize startup impact and avoid GUI import side effects, prefer a local import inside the entry-point method.

Recommended:

```python
def _open_explicit_pipeline_kpi_view(self):
    from pysi.gui.explicit_pipeline_management_cockpit_view import (
        build_explicit_pipeline_management_cockpit_view_model,
        render_explicit_pipeline_management_cockpit_tk,
    )
    ...
```

This keeps `cockpit_tk.py` top-level imports stable.

---

## 9. Button Label

Recommended button label:

```text
Explicit KPI View
```

Alternative label:

```text
Pipeline KPI View
```

Recommended first choice:

```text
Explicit KPI View
```

Reason:

```text
It makes clear that the view relates to the explicit pipeline stack, not the whole WOM business cockpit.
```

---

## 10. Button Placement

Recommended placement:

```text
near existing Management Cockpit / reporting / Run Full Plan controls
```

Since exact layout in `cockpit_tk.py` may already be dense, Codex should inspect the current GUI layout and choose the smallest consistent placement.

Preferred approach:

```text
Add one button near the existing Management Cockpit / report-related button area.
```

Do not reorganize layout.

Do not move existing buttons.

Do not rename existing buttons.

Do not change existing command bindings.

---

## 11. Button Command

The button command should be:

```python
command=self._open_explicit_pipeline_kpi_view
```

No lambda with planning calls.

No export call.

No flag changes.

---

## 12. Empty Data Behavior

If the user clicks the button before running explicit pipeline planning:

```text
The view should still open.
```

The existing view model and renderer already support no-data behavior:

```text
No explicit pipeline reporting data is available.
Run planning with explicit pipeline enabled.
```

Therefore the button does not need to block or pre-validate data.

It should simply open the view.

This is important for usability.

---

## 13. Expected User Flow

### 13.1 With no explicit pipeline data

```text
User opens WOM GUI
User clicks Explicit KPI View
Window opens
Message explains no explicit pipeline data is available
```

### 13.2 After planning with explicit pipeline and reporting flags

```text
User runs planning
Explicit pipeline produces reporting / issue / KPI artifacts depending on flags
User clicks Explicit KPI View
Window opens with Summary / Top Issues / Replan / Health / Assumptions / Messages tabs
```

### 13.3 With partial data

```text
User has capacity report but no Cost / KPI bundle
Window opens
Available sections are shown
Missing sections show safe messages
```

---

## 14. Safety Boundaries

The entry point and button must not:

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
read self.env
build view model
render read-only Tk window
return Toplevel
```

---

## 15. Relationship to Feature Flags

This button should not change any feature flags.

The data shown in the view depends on what has already been generated by previous planning runs and flags:

```text
enable_explicit_bridge_capacity_report
enable_explicit_bridge_capacity_report_export
enable_explicit_bridge_capacity_issue_candidates
enable_explicit_bridge_capacity_issue_candidate_export
enable_explicit_bridge_capacity_issue_candidate_cost_kpi
enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export
```

The button only displays current state.

It should not enable flags automatically.

---

## 16. Relationship to Exports

The button should not run export helpers.

If export results exist, the view can display them.

If export results do not exist, the view can display:

```text
Export results are not available. Export flags may be off.
```

This preserves the separation:

```text
export execution
    ≠
view display
```

---

## 17. Relationship to Replan Candidates

The view may display replan candidates.

But the button must not execute them.

The status:

```text
candidate_only
```

must remain conceptually unchanged.

This is a decision-support view, not a command console.

---

## 18. Relationship to Existing Management Cockpit

This new button should be positioned as:

```text
Explicit Pipeline KPI View
```

not as a replacement for existing Management Cockpit functions.

Existing Management Cockpit / reporting capabilities may still handle:

```text
business reports
cost waterfall
allocation breakdown
scenario comparison
```

This view focuses on:

```text
explicit bridge + capacity planning evidence
capacity risk
issue candidates
directional Cost / KPI impact
```

---

## 19. Test Strategy

Testing `cockpit_tk.py` GUI layout directly may be brittle.

Recommended tests:

```text
1. Test the entry-point method by monkeypatching the builder and renderer.
2. Verify that it passes self.env to the builder.
3. Verify that it passes self and the returned view_model to the renderer.
4. Verify that it returns the renderer return value.
5. Verify that no planning/export helper is called.
```

Avoid full Tk visual assertions if possible.

---

## 20. Recommended Test File

Add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view_button_integration.py
```

Potential strategy:

```text
Use a lightweight object or allocated WOMCockpit instance substitute.
Call WOMCockpit._open_explicit_pipeline_kpi_view(fake_self).
Monkeypatch imported helper functions.
```

Because the method uses local imports, the test can monkeypatch the functions in:

```text
pysi.gui.explicit_pipeline_management_cockpit_view
```

---

## 21. Test Case: Entry Point Calls Builder and Renderer

Pseudo-test:

```python
def test_open_explicit_pipeline_kpi_view_calls_builder_and_renderer(monkeypatch):
    calls = {}

    fake_env = object()
    fake_self = SimpleNamespace(env=fake_env)

    def fake_builder(env):
        calls["env"] = env
        return {"available": True}

    def fake_renderer(parent, view_model):
        calls["parent"] = parent
        calls["view_model"] = view_model
        return "window"

    monkeypatch.setattr(
        "pysi.gui.explicit_pipeline_management_cockpit_view.build_explicit_pipeline_management_cockpit_view_model",
        fake_builder,
    )
    monkeypatch.setattr(
        "pysi.gui.explicit_pipeline_management_cockpit_view.render_explicit_pipeline_management_cockpit_tk",
        fake_renderer,
    )

    result = WOMCockpit._open_explicit_pipeline_kpi_view(fake_self)

    assert result == "window"
    assert calls["env"] is fake_env
    assert calls["parent"] is fake_self
    assert calls["view_model"] == {"available": True}
```

This test validates the important contract without opening a real Tk window.

---

## 22. Test Case: Button Exists

A lightweight test may verify that a button text appears in the cockpit setup code, but this can be brittle.

Alternative:

```text
Do not test exact layout.
Rely on code review for button placement.
Test entry-point method behavior.
```

If the project has existing GUI button tests, follow that style.

---

## 23. Tests to Run

After implementation, run:

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

## 24. Recommended Codex Implementation Scope

Future Codex request should modify:

```text
pysi/gui/cockpit_tk.py
tests/test_explicit_pipeline_management_cockpit_kpi_view_button_integration.py
```

Do not modify:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
pysi/reporting/*
pysi/plan/*
```

unless a tiny import compatibility issue is found.

---

## 25. Completion Criteria for Implementation

The future implementation is complete when:

```text
[OK] WOMCockpit has _open_explicit_pipeline_kpi_view method
[OK] method builds view model from self.env
[OK] method renders read-only Tk view
[OK] method returns renderer return value
[OK] GUI has one user-accessible button/menu entry
[OK] button label is clear, e.g. Explicit KPI View
[OK] button only opens the view
[OK] no planning execution is added
[OK] no export execution is added
[OK] no ReplanCommand execution is added
[OK] no feature flags are changed
[OK] no env mutation beyond read-only view construction
[OK] entry-point tests pass
[OK] existing view-model and rendering tests pass
[OK] key regression tests pass
```

---

## 26. Future Enhancements

After button integration, future enhancements can include:

```text
better column sizing
copy selected row
detail pane for selected issue
filter by severity
filter by node
filter by issue type
open exported file path
graph / chart view
KPI cards
Knowledge Continuity issue promotion
```

Each should be separately designed and feature-controlled.

---

## 27. Summary

This design defines the next safe integration step.

The completed components are:

```text
view model
    ↓
read-only Tk rendering helper
```

The next step is:

```text
main cockpit button
    ↓
build view model from self.env
    ↓
open read-only KPI view
```

The core rule remains:

```text
Open the panel.
Do not start the engine.
```

This brings the explicit pipeline management cockpit into the main GUI while preserving WOM's staged, human-in-the-loop safety model.
