# Explicit Pipeline Management Cockpit KPI Cards Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-25  
**Status:** Design memo  
**Target path:** `docs/design/explicit_pipeline_management_cockpit_kpi_cards.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/explicit_pipeline_management_cockpit_kpi_integration_overview.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_graph_integration_overview.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view_completion.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view_tk_rendering.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view_tk_rendering_completion.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view_button_integration.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_view_button_integration_completion.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_graph_view.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_graph_view_completion.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.md`
- `docs/design/explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering_completion.md`
- `docs/design/explicit_pipeline_reporting_issue_cost_kpi_overview.md`
- `docs/design/wom_knowledge_continuity_layer.md`

---

## 1. Purpose

This memo defines the design for adding **KPI Cards** to the Explicit Pipeline Management Cockpit KPI View.

The current cockpit already has:

```text
Explicit KPI View
    ├─ Summary
    ├─ Graphs
    ├─ Top Issues
    ├─ Replan Candidates
    ├─ Health
    ├─ Assumptions / Exports
    └─ Messages
```

The current `Graphs` tab already displays simple Tk Canvas charts:

```text
Top Business Impact
Cost / KPI Impact Composition
Issue Severity Distribution
Weekly Issue Count
```

The next enhancement is to add compact, management-facing KPI Cards that show the most important cockpit signals at a glance.

The goal is:

```text
make the first 5 seconds of management review more effective
```

This design is for read-only display.

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
Canvas graph rendering / Graphs tab              ✅ completed
    ↓
KPI Cards                                        ← current design target
```

The cockpit is now functional as both:

```text
table / key-value cockpit
graph / chart cockpit
```

The next layer is:

```text
large, compact, management summary cards
```

---

## 3. Design Goal

The KPI Cards should answer the manager's first questions:

```text
1. How large is the total business impact?
2. How many capacity violations exist?
3. How many management issues need attention?
4. Are there health / data quality warnings?
5. Are there replan candidates to review?
```

The KPI Cards are not intended to replace detailed tabs.

They are the cockpit's front-row warning lamps.

Detailed review remains in:

```text
Graphs
Top Issues
Replan Candidates
Health
Assumptions / Exports
Messages
```

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
new main GUI button
matplotlib rendering
advanced dashboard framework
```

This phase is only:

```text
read-only KPI card rendering
```

---

## 5. Core Safety Rule

The existing cockpit safety rule remains:

```text
Show the instruments.
Do not start the engine.
```

The KPI Cards may:

```text
read the existing view_model
derive card values
render read-only cards
show messages / caveats
```

They must not:

```text
run planning
run exports
change flags
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
tests/test_explicit_pipeline_management_cockpit_kpi_cards.py
```

Do not modify:

```text
pysi/gui/cockpit_tk.py
pysi/reporting/*
pysi/plan/*
```

unless a tiny compatibility issue is absolutely necessary.

The existing `Explicit KPI View` button should automatically benefit because it opens the same renderer.

---

## 7. Recommended Placement

There are two reasonable placement options.

### Option A: Summary tab top area

Add KPI Cards at the top of the existing `Summary` tab.

Recommended for MVP.

Reason:

```text
Summary is the first tab.
Cards belong at the top of Summary.
No new tab is needed.
```

### Option B: Graphs tab top area

Add KPI Cards above the 2x2 chart grid in the existing `Graphs` tab.

Reason:

```text
Cards and charts are both visual management summaries.
```

### Recommended choice

Use:

```text
Option A: Summary tab top area
```

because the user should see the cards immediately when the Explicit KPI View opens.

If implementation risk is lower in Graphs tab, Option B is acceptable, but Option A is preferred.

---

## 8. Recommended KPI Cards

Recommended MVP card set:

```text
1. Total Business Impact
2. Capacity Violations
3. Management Issues
4. Health Warnings
5. Replan Candidates
```

Optional sixth card:

```text
Planning Issues
```

MVP should start with five cards.

---

## 9. Card 1: Total Business Impact

### 9.1 Purpose

Show the estimated total directional business impact.

### 9.2 Source

```python
view_model["executive_kpi_summary"]["estimated_total_business_impact"]
```

### 9.3 Secondary text

Use currency if available:

```python
view_model["executive_kpi_summary"]["currency"]
```

Example:

```text
1,250,000 JPY
```

### 9.4 Caveat

This value is directional.

The card should not imply formal accounting precision.

Suggested tooltip or subtitle:

```text
Directional estimate
```

If no value exists:

```text
0
```

or:

```text
N/A
```

Recommended MVP:

```text
0
```

with caveat message visible elsewhere.

---

## 10. Card 2: Capacity Violations

### 10.1 Purpose

Show how many capacity violation records exist.

### 10.2 Source

```python
view_model["capacity_summary"]["capacity_violation_record_count"]
```

### 10.3 Interpretation

This card indicates capacity pressure.

If count is positive, manager should inspect:

```text
Graphs
Top Issues
Health
```

---

## 11. Card 3: Management Issues

### 11.1 Purpose

Show the number of management issue candidates.

### 11.2 Source

```python
view_model["issue_summary"]["management_issue_candidate_count"]
```

### 11.3 Interpretation

This card represents issue candidates that may deserve management attention.

---

## 12. Card 4: Health Warnings

### 12.1 Purpose

Show data quality / health risk signals.

### 12.2 Source options

Preferred:

```python
view_model["health_summary"]["health_issue_count"]
```

Alternative:

```python
view_model["issue_summary"]["health_issue_candidate_count"]
```

Recommended MVP:

```text
use health_summary.health_issue_count first
fallback to issue_summary.health_issue_candidate_count
```

### 12.3 Interpretation

This card answers:

```text
Can we trust the evidence?
```

---

## 13. Card 5: Replan Candidates

### 13.1 Purpose

Show how many replan candidate records exist.

### 13.2 Source

Preferred:

```python
len(view_model["replan_candidates"])
```

Fallback:

```python
view_model["issue_summary"]["replan_command_candidate_count"]
```

### 13.3 Interpretation

This card means:

```text
There are candidate-only actions to review.
```

It does not mean they should be automatically executed.

---

## 14. Optional Card 6: Planning Issues

Optional future card:

```text
Planning Issues
```

Source:

```python
view_model["issue_summary"]["planning_issue_candidate_count"]
```

This may be useful if five-card layout feels incomplete.

For MVP, keep it optional.

---

## 15. Recommended Card Data Model

To keep rendering simple, add a private helper that builds card dictionaries.

Recommended helper:

```python
def _build_explicit_pipeline_kpi_cards(view_model: dict[str, Any]) -> list[dict[str, Any]]:
    ...
```

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

Status should be simple and deterministic.

Recommended statuses:

```text
normal
warning
critical
unknown
```

---

## 16. Card Status Rules

Recommended status logic:

### 16.1 Total Business Impact

```text
value > 0          → warning
value == 0         → normal
missing / invalid  → unknown
```

### 16.2 Capacity Violations

```text
count > 0          → warning
count == 0         → normal
missing / invalid  → unknown
```

### 16.3 Management Issues

```text
count > 0          → warning
count == 0         → normal
missing / invalid  → unknown
```

### 16.4 Health Warnings

```text
count > 0          → warning
count == 0         → normal
missing / invalid  → unknown
```

### 16.5 Replan Candidates

```text
count > 0          → warning
count == 0         → normal
missing / invalid  → unknown
```

Future enhancements may add `critical` rules based on severity or thresholds.

MVP should avoid complex threshold logic.

---

## 17. Rendering Approach

Recommended helper:

```python
def _create_kpi_cards_frame(parent: tk.Widget, cards: list[dict[str, Any]]) -> ttk.Frame:
    ...
```

This helper should:

```text
create a frame
render cards in a horizontal row or wrapping grid
return the frame
```

Recommended MVP layout:

```text
5 cards in one horizontal row
```

If window width is limited, use:

```text
3 cards in first row
2 cards in second row
```

Recommended card size:

```text
width: 180 to 220 px
height: 80 to 100 px
```

---

## 18. Tk Widget Choice

Use standard Tk / ttk widgets.

Recommended:

```text
ttk.Frame
ttk.Label
```

Optional:

```text
tk.Frame with border relief
```

Do not use external dependencies.

Do not use matplotlib.

Do not use Canvas unless simpler for visual styling.

MVP can use plain labels inside bordered frames.

---

## 19. Visual Style

The cards should be clear but simple.

Recommended elements:

```text
Title
Large value
Unit / subtitle
Status marker text
```

Example:

```text
+-----------------------------+
| Total Business Impact        |
| 1,250,000 JPY                |
| Directional estimate         |
+-----------------------------+
```

For warning status, it is acceptable to show:

```text
Status: warning
```

as text rather than relying on color.

This keeps visual meaning accessible and testable.

---

## 20. Empty-State Behavior

If the view model is unavailable:

```python
view_model["available"] is False
```

KPI Cards should still render with safe defaults.

Suggested cards:

```text
Total Business Impact: N/A
Capacity Violations: N/A
Management Issues: N/A
Health Warnings: N/A
Replan Candidates: N/A
```

or zero values with unknown status.

Recommended MVP:

```text
N/A with status unknown
```

This is clearer than showing zeros when no data exists.

---

## 21. Integration Point

Recommended integration:

```text
Summary tab top area
```

Current Summary tab already renders key-value sections.

Modify the Summary tab construction so it becomes:

```text
Summary tab
    ├─ KPI Cards frame
    └─ existing key-value summary sections
```

Existing Summary data should remain visible.

Do not remove existing key-value tables.

---

## 22. Graphs Tab Relationship

Graphs tab should remain unchanged.

It may benefit indirectly because KPI Cards and Graphs share the same source view model.

Future phase may optionally add cards above Graphs.

MVP should avoid duplicate cards in both Summary and Graphs.

---

## 23. Test Strategy

Add focused tests for:

```text
1. card model builder
2. Summary tab renders with cards
3. no-data view model renders cards safely
4. populated view model renders cards safely
5. input view_model not mutated
```

Avoid brittle pixel-level GUI assertions.

Test text / structure where possible.

---

## 24. Recommended Test File

Add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_cards.py
```

Recommended tests:

### 24.1 Card model populated

Input sample view model with:

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
```

### 24.2 Card model no data

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

### 24.3 Summary tab renders

Use safe Tk skip helper.

Render:

```python
render_explicit_pipeline_management_cockpit_tk(root, view_model)
```

Verify no exception and Summary tab still exists.

### 24.4 Input not mutated

Deep copy input view model.

Build cards / render.

Verify input remains unchanged.

---

## 25. Recommended Test Helpers

Tk rendering tests should use safe skip behavior:

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

---

## 26. Existing Tests to Run

After implementation, run:

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

## 27. Recommended First Codex Request Scope

Recommended first implementation:

```text
KPI card model + Summary tab card rendering
```

Files:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
tests/test_explicit_pipeline_management_cockpit_kpi_cards.py
```

Do not modify:

```text
pysi/gui/cockpit_tk.py
```

Do not implement:

```text
interactive card clicks
card thresholds beyond basic warning/normal
card drilldown
Knowledge Continuity handoff
```

---

## 28. Completion Criteria

This implementation will be complete when:

```text
[OK] KPI card model helper exists
[OK] five MVP cards are produced
[OK] no-data view model produces safe N/A cards
[OK] populated view model produces deterministic card values
[OK] Summary tab renders KPI cards
[OK] existing Summary details remain visible
[OK] input view_model is not mutated
[OK] no cockpit_tk.py modification
[OK] no planning execution is added
[OK] no export execution is added
[OK] no ReplanCommand execution is added
[OK] focused KPI card tests pass
[OK] existing graph / view / button tests pass
```

---

## 29. Future Enhancements

Future improvements may include:

```text
card color styling
critical threshold rules
click card to filter related table rows
click card to open detail pane
copy card values
card layout responsive wrapping
KPI cards in Graphs tab
Knowledge Continuity handoff
```

Each should be separately designed.

---

## 30. Summary

The current cockpit already has tables and graphs.

The KPI Cards layer should add immediate management visibility:

```text
Total Business Impact
Capacity Violations
Management Issues
Health Warnings
Replan Candidates
```

Recommended implementation:

```text
KPI card model
    ↓
Summary tab card frame
    ↓
read-only management warning lamps
```

The rule remains:

```text
Show the warning lamps.
Do not start the engine.
```
