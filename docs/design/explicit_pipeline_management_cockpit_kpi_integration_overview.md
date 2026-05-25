# Explicit Pipeline Management Cockpit KPI Integration Overview

**Version:** v0r1 overview  
**Date:** 2026-05-24  
**Status:** Overview memo  
**Target path:** `docs/design/explicit_pipeline_management_cockpit_kpi_integration_overview.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo provides an overview of the completed **Explicit Pipeline Management Cockpit KPI Integration** work.

The integration connects the explicit bridge + capacity planning pipeline to a read-only management-facing KPI cockpit view.

The completed chain is:

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
```

The central result is:

```text
The main WOM GUI can now open a read-only Explicit KPI View
that displays explicit pipeline reporting / issue / Cost-KPI evidence.
```

This is a viewer path, not an execution path.

---

## 2. Big Picture

The explicit pipeline work has gradually moved from backend planning logic toward management decision support.

The high-level flow is:

```text
Plan
    ↓
Detect capacity / lot / health signals
    ↓
Build reports
    ↓
Generate issue candidates
    ↓
Estimate directional Cost / KPI impact
    ↓
Build cockpit view model
    ↓
Render read-only cockpit window
    ↓
Open from main GUI button
```

This enables WOM to show the manager:

```text
what happened
where the capacity risk is
which issue candidates exist
which issues have business impact
which assumptions were used
which export artifacts exist
what should be reviewed next
```

without automatically executing replanning decisions.

---

## 3. Completed Integration Layers

### 3.1 Explicit pipeline runner

The explicit bridge + capacity pipeline runner produces the base execution result.

Conceptual artifact:

```text
ExplicitBridgeCapacityPipelineResult
```

Its purpose is to connect demand-side execution to explicit capacity-aware planning evidence.

---

### 3.2 Feature-flag helper

The explicit pipeline and its reporting stack are controlled through flags.

This preserves safe default behavior:

```text
default OFF
no accidental reporting
no accidental export
no accidental Cost / KPI processing
```

---

### 3.3 Planning-sequence insertion

The explicit pipeline and later reporting stack were inserted into the planning sequence behind explicit conditions.

Important rule:

```text
reporting stack only runs after explicit_result is not None
```

This prevents report generation from running when the explicit pipeline did not execute.

---

### 3.4 Capacity report

The capacity report layer converts pipeline execution artifacts into report records.

Examples:

```text
capacity usage records
capacity violation records
lot exception records
replan candidate records
health check records
summary
```

This is the first explanation layer.

---

### 3.5 Capacity report export

The capacity report export layer writes deterministic CSV / JSON files when export flags are enabled.

Important rule:

```text
export is explicit
export does not happen by default
```

---

### 3.6 Issue candidate bundle

The issue candidate builder transforms report records into candidate issues.

Candidate groups include:

```text
planning issue candidates
management issue candidates
replan command candidates
health issue candidates
```

Important rule:

```text
replan candidates are candidate_only
```

They are review options, not executable commands.

---

### 3.7 Issue candidate export

The issue candidate export layer writes issue candidate CSV / JSON artifacts when enabled.

This creates audit-friendly evidence for later review.

---

### 3.8 Cost / KPI enrichment

The Cost / KPI enrichment layer adds directional business impact estimates to issue candidates.

Examples:

```text
estimated total business impact
estimated lost sales value
estimated margin impact
estimated inventory cost impact
estimated capacity cost impact
estimated service penalty
risk scores
assumption source
```

Important caveat:

```text
Directional scenario estimate, not formal accounting.
Double counting may be possible depending on assumptions.
```

---

### 3.9 Cost / KPI export

The Cost / KPI export layer writes enriched issue candidate artifacts and assumptions.

It separates:

```text
impact estimates
assumptions
audit trail
```

---

### 3.10 Reporting flag switchboard helper

The reporting flag helper orchestrates existing report / issue / Cost-KPI builders and exporters.

Representative helper:

```python
maybe_run_explicit_pipeline_reporting_stack_from_env(...)
```

It reads flags from `env` and delegates to existing helpers.

Important rule:

```text
switchboard does not run the base planning pipeline
```

It only orchestrates reporting layers from already-existing artifacts.

---

### 3.11 Planning-sequence reporting stack insertion

The reporting switchboard was connected to the planning sequence.

Conceptual flow:

```text
explicit_result = maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
if explicit_result is not None:
    maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
    maybe_run_explicit_pipeline_reporting_stack_from_env(...)
```

This means the planning sequence can now produce the full explanation stack when flags are enabled.

---

### 3.12 Management Cockpit KPI view model

A pure view-model builder was added:

```python
build_explicit_pipeline_management_cockpit_view_model(env) -> dict
```

It transforms env artifacts into a read-only GUI-ready dictionary.

Top-level schema:

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

This separates business extraction / formatting from Tk rendering.

---

### 3.13 Read-only Tk rendering helper

A rendering helper was added:

```python
render_explicit_pipeline_management_cockpit_tk(parent, view_model) -> tk.Toplevel
```

It renders the view model using a `ttk.Notebook` tab layout.

Tabs:

```text
Summary
Top Issues
Replan Candidates
Health
Assumptions / Exports
Messages
```

Important rule:

```text
render existing view model only
do not run anything
```

---

### 3.14 Button integration

The main `WOMCockpit` GUI now has an entry point:

```python
_open_explicit_pipeline_kpi_view(self)
```

and a button:

```text
Explicit KPI View
```

The button flow is:

```text
click Explicit KPI View
    ↓
build view model from self.env
    ↓
render read-only KPI window
```

The button does not run planning, exports, reporting stack, or replan commands.

---

## 4. Main Files Added or Modified

### 4.1 Core GUI view model / rendering helper

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

Contains:

```python
build_explicit_pipeline_management_cockpit_view_model(env)
render_explicit_pipeline_management_cockpit_tk(parent, view_model)
```

---

### 4.2 Main cockpit GUI

```text
pysi/gui/cockpit_tk.py
```

Contains:

```python
WOMCockpit._open_explicit_pipeline_kpi_view(self)
```

and the button:

```text
Explicit KPI View
```

---

### 4.3 Focused tests

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view.py
tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py
tests/test_explicit_pipeline_management_cockpit_kpi_view_button_integration.py
```

These cover:

```text
view model behavior
Tk rendering helper
button entry-point integration
```

---

## 5. Important Design Documents

This integration is supported by a chain of design and completion documents.

### 5.1 View model

```text
docs/design/explicit_pipeline_management_cockpit_kpi_view.md
docs/design/explicit_pipeline_management_cockpit_kpi_view_completion.md
```

### 5.2 Tk rendering

```text
docs/design/explicit_pipeline_management_cockpit_kpi_view_tk_rendering.md
docs/design/explicit_pipeline_management_cockpit_kpi_view_tk_rendering_completion.md
```

### 5.3 Button integration

```text
docs/design/explicit_pipeline_management_cockpit_kpi_view_button_integration.md
docs/design/explicit_pipeline_management_cockpit_kpi_view_button_integration_completion.md
```

### 5.4 Reporting stack overview

```text
docs/design/explicit_pipeline_reporting_issue_cost_kpi_overview.md
docs/design/explicit_pipeline_phase1_to_phase4_overview.md
```

### 5.5 Knowledge continuity direction

```text
docs/design/wom_knowledge_continuity_layer.md
```

This will become important when cockpit issue evidence is promoted into persistent learning / decision memory.

---

## 6. Current User-Facing Behavior

The user can now open the WOM GUI and click:

```text
Explicit KPI View
```

The button opens a read-only Tk window with tabs.

The view may show:

```text
Summary
Top Issues
Replan Candidates
Health
Assumptions / Exports
Messages
```

If no explicit pipeline data exists, it still opens and shows a no-data message.

This is intentional.

The view is safe even before planning runs.

---

## 7. Safety Boundary

The integration preserves a strict safety boundary.

The Explicit KPI View button does not:

```text
run planning
run Run Full Plan
run the explicit pipeline
run reporting stack
run exports
change feature flags
execute ReplanCommand
write files
open files
delete files
persist data
perform OR optimization
persist Knowledge Continuity records
```

The button only:

```text
reads current env
builds a view model
opens a read-only Tk window
```

Core rule:

```text
Open the panel.
Do not start the engine.
```

---

## 8. Relationship to Replan Candidates

Replan candidates are displayed as decision-support information.

Their status remains:

```text
candidate_only
```

No command execution path was added.

This preserves human-in-the-loop decision making.

---

## 9. Relationship to Cost / KPI

The Cost / KPI layer is directional.

The view model and messages should continue to communicate:

```text
Cost / KPI values are directional scenario estimates, not formal accounting values.
Double counting may be possible depending on assumptions.
```

This is important for management trust.

The KPI View is not a formal accounting report.

It is a scenario-based management attention tool.

---

## 10. Relationship to Export

The view displays export summaries only if export result objects already exist.

It does not trigger exports.

This keeps file creation explicit and feature-flag controlled.

---

## 11. Relationship to Existing Management Cockpit

The new Explicit KPI View complements the existing WOM Management Cockpit.

Existing Management Cockpit areas may still handle:

```text
business report
cost waterfall
allocation breakdown
scenario comparison
business animation
PSI / profit animation
```

The Explicit KPI View focuses specifically on:

```text
explicit bridge + capacity planning evidence
issue candidates
directional Cost / KPI impact
data quality / health signals
```

---

## 12. Test Coverage Summary

The completed work has focused tests for each integration layer.

Representative tests include:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view.py
tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py
tests/test_explicit_pipeline_management_cockpit_kpi_view_button_integration.py
tests/test_explicit_pipeline_reporting_stack_insertion.py
tests/test_explicit_pipeline_reporting_flags.py
tests/test_covid_vaccine_with_capacity_push.py
```

Observed final local acceptance around button integration:

```text
button integration: 1 passed
Tk rendering: 2 passed, 1 skipped
view model: 8 passed
reporting stack insertion: 7 passed
reporting flags: 10 passed
covid vaccine optional: 1 passed
```

The `1 skipped` in Tk rendering is acceptable because Tk tests can be environment-sensitive.

---

## 13. Completed Commit Milestones

Key commits from the final cockpit KPI integration stages:

```text
fb8acd9 Add explicit pipeline management cockpit KPI view model
8159352 Add read-only Tk rendering helper for explicit pipeline KPI cockpit view
b31fc54 Add Explicit KPI View button and cockpit entry point
8d0dbfb Add explicit pipeline management cockpit KPI view button integration completion memo
```

These represent:

```text
view model
rendering helper
button integration
completion memo
```

---

## 14. Current Architecture

The current runtime architecture can be summarized as:

```text
WOMCockpit
    ├─ Run Full Plan / planning sequence
    │      └─ explicit pipeline reporting stack attaches artifacts to env
    │
    └─ Explicit KPI View button
           └─ _open_explicit_pipeline_kpi_view()
                  ├─ build_explicit_pipeline_management_cockpit_view_model(self.env)
                  └─ render_explicit_pipeline_management_cockpit_tk(self, view_model)
```

This makes the view path read-only and separate from the execution path.

---

## 15. Why This Matters

This integration is important because it turns low-level planning artifacts into management review information.

Before this integration:

```text
explicit pipeline evidence existed mostly as internal objects / exports
```

After this integration:

```text
explicit pipeline evidence can be viewed from the main GUI
```

This helps bridge:

```text
planning engine
    and
management decision support
```

without prematurely automating decisions.

---

## 16. Known Limitations

The current view is a read-only table / key-value cockpit.

It does not yet include:

```text
graph / chart view
KPI cards
interactive filtering
row detail pane
copy-to-clipboard
open file path buttons
automatic refresh after planning
issue review workflow
Knowledge Continuity capture
ReplanCommand execution
```

It is a safe first management cockpit panel, not the final dashboard.

---

## 17. Recommended Next Enhancements

### 17.1 Graph / chart view

Potential design document:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_graph_view.md
```

Potential charts:

```text
Top impact issue bar chart
Cost / KPI impact waterfall
Capacity violation by week
Issue severity distribution
Health / data quality risk count
```

### 17.2 KPI cards

Potential compact cards:

```text
Total Business Impact
Capacity Violations
Management Issues
Replan Candidates
Health Warnings
```

### 17.3 Detail pane

Clicking a top issue could show:

```text
full issue record
lot IDs
assumptions used
candidate action
related export file path
```

Still read-only in first refinement.

### 17.4 Filtering

Potential filters:

```text
severity
issue type
node
product
week
impact category
```

### 17.5 Knowledge Continuity integration

Future integration with:

```text
docs/design/wom_knowledge_continuity_layer.md
```

could promote selected cockpit evidence into:

```text
open issues
facts and findings
decision log candidates
next-entry prompts
recurring pattern memory
```

This should be separately designed and explicitly controlled.

---

## 18. Suggested Next Design Step

A natural next design step is:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_graph_view.md
```

This should define how to add graphical KPI representations while preserving the same safety boundary:

```text
display only
no execution
no automatic decision
```

Recommended first graph enhancements:

```text
1. Top Business Impact bar chart
2. Issue severity distribution
3. Capacity violations by week
4. Cost / KPI impact waterfall
```

---

## 19. Summary

The Explicit Pipeline Management Cockpit KPI Integration is now complete through button integration.

The main GUI can open a read-only Explicit KPI View.

The integration chain is:

```text
explicit pipeline artifacts
    ↓
view model
    ↓
read-only Tk rendering
    ↓
Explicit KPI View button
```

The safety boundary is intact:

```text
view only
no planning execution
no export execution
no replan execution
no feature flag mutation
```

This gives WOM a visible management cockpit entry point for explicit bridge + capacity planning evidence.

The cockpit now has a working instrument panel.

The next frontier is better visualization.
