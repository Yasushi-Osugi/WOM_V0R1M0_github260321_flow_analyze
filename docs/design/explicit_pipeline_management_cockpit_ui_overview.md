# Explicit Pipeline Management Cockpit UI Overview

**Version:** v0r1 overview  
**Date:** 2026-05-25  
**Status:** Overview memo  
**Target path:** `docs/design/explicit_pipeline_management_cockpit_ui_overview.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo provides an overview of the completed **Explicit Pipeline Management Cockpit UI**.

The purpose of this overview is to summarize the current user-facing cockpit structure after the following UI enhancements were completed:

```text
Management Cockpit KPI view model
    ↓
read-only Tk rendering helper
    ↓
Explicit KPI View button
    ↓
Graph view model
    ↓
Graphs tab with Tk Canvas charts
    ↓
Summary KPI Cards
```

The cockpit now provides both:

```text
first-glance management signals
and
detailed planning evidence
```

The UI remains read-only and does not execute planning, exports, replanning, optimization, or persistence.

---

## 2. Current UI Structure

The current `Explicit KPI View` window contains:

```text
Explicit KPI View
    ├─ Summary
    │   └─ KPI Cards
    ├─ Graphs
    │   └─ Canvas Charts
    ├─ Top Issues
    ├─ Replan Candidates
    ├─ Health
    ├─ Assumptions / Exports
    └─ Messages
```

This structure gives the user a layered cockpit experience:

```text
1. first-glance cards
2. visual charts
3. issue detail tables
4. replan candidate review
5. health / data-quality signals
6. assumptions and exports
7. messages and next review actions
```

---

## 3. Background

Before the Explicit Pipeline Management Cockpit UI work, explicit pipeline artifacts existed mainly as backend objects, reporting outputs, and testable data bundles.

The staged work converted those artifacts into a user-facing management cockpit:

```text
explicit pipeline artifacts
    ↓
capacity report
    ↓
issue candidates
    ↓
Cost / KPI enrichment
    ↓
view model
    ↓
read-only Tk rendering
    ↓
button integration
    ↓
graphs
    ↓
KPI cards
```

The key transformation is:

```text
from backend evidence
to management review cockpit
```

---

## 4. Completed UI Milestones

The UI integration was implemented in stages.

### 4.1 Management Cockpit KPI View Model

A pure view-model builder was implemented:

```python
build_explicit_pipeline_management_cockpit_view_model(env) -> dict
```

It extracts cockpit-ready information from the current `env`.

It produces sections such as:

```text
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

### 4.2 Read-only Tk Rendering Helper

A read-only renderer was implemented:

```python
render_explicit_pipeline_management_cockpit_tk(parent, view_model) -> tk.Toplevel
```

It renders the already-built view model into a `ttk.Notebook`-based window.

No planning logic is executed by the renderer.

---

### 4.3 Explicit KPI View Button

The main WOM cockpit gained a button:

```text
Explicit KPI View
```

The button calls:

```python
WOMCockpit._open_explicit_pipeline_kpi_view(self)
```

The method:

```text
builds the current view model from self.env
renders the read-only Tk KPI window
returns the rendered Toplevel
```

It does not run planning or exports.

---

### 4.4 Graph View Model

A graph-ready model builder was implemented:

```python
build_explicit_pipeline_kpi_graph_view_model(view_model: dict) -> dict
```

It derives chart-ready data from the already-built cockpit view model.

Graph model sections include:

```text
top_impact_bars
severity_distribution
impact_composition
weekly_issue_counts
messages
```

---

### 4.5 Graphs Tab with Tk Canvas Charts

A `Graphs` tab was added to the Explicit KPI View.

It renders four simple Canvas charts:

```text
Top Business Impact
Cost / KPI Impact Composition
Issue Severity Distribution
Weekly Issue Count
```

The implementation uses only standard Tk Canvas primitives:

```text
create_text
create_rectangle
create_line
```

No matplotlib dependency was added.

---

### 4.6 Summary KPI Cards

The `Summary` tab gained five first-glance KPI Cards:

```text
Total Business Impact
Capacity Violations
Management Issues
Health Warnings
Replan Candidates
```

These cards show large, compact management signals before the user reads tables or charts.

---

## 5. Summary Tab

The `Summary` tab is the cockpit's first screen.

It now consists of:

```text
Summary tab
    ├─ KPI Cards row
    └─ existing summary key-value sections
```

The cards are intended to answer, within a few seconds:

```text
How large is the impact?
Where is capacity pressure?
How many management issues exist?
Can we trust the data?
Are there candidate-only replan options?
```

---

## 6. KPI Cards

The MVP card set is:

```text
1. Total Business Impact
2. Capacity Violations
3. Management Issues
4. Health Warnings
5. Replan Candidates
```

### 6.1 Total Business Impact

Source:

```text
executive_kpi_summary.estimated_total_business_impact
```

Meaning:

```text
directional estimated business impact
```

Caveat:

```text
not a formal accounting value
```

---

### 6.2 Capacity Violations

Source:

```text
capacity_summary.capacity_violation_record_count
```

Meaning:

```text
capacity pressure requiring review
```

---

### 6.3 Management Issues

Source:

```text
issue_summary.management_issue_candidate_count
```

Meaning:

```text
issue candidates requiring management attention
```

---

### 6.4 Health Warnings

Preferred source:

```text
health_summary.health_issue_count
```

Fallback source:

```text
issue_summary.health_issue_candidate_count
```

Meaning:

```text
data quality / health risk signal
```

---

### 6.5 Replan Candidates

Preferred source:

```text
len(replan_candidates)
```

Fallback source:

```text
issue_summary.replan_command_candidate_count
```

Meaning:

```text
candidate-only actions available for review
```

Important rule:

```text
The card does not execute replan candidates.
```

---

## 7. Graphs Tab

The `Graphs` tab gives visual management summaries.

Implemented charts:

```text
Top Business Impact
Cost / KPI Impact Composition
Issue Severity Distribution
Weekly Issue Count
```

The charts are intentionally simple.

They support fast review, not formal accounting or interactive analysis.

---

## 8. Top Business Impact Chart

Source:

```text
graph_model.top_impact_bars
```

Purpose:

```text
show the issue candidates with the largest estimated directional business impact
```

Chart type:

```text
horizontal bar chart
```

This chart helps answer:

```text
Which issue deserves attention first?
```

---

## 9. Cost / KPI Impact Composition Chart

Source:

```text
graph_model.impact_composition
```

Components:

```text
Lost Sales
Margin Impact
Inventory Cost
Capacity Cost
Service Penalty
```

Purpose:

```text
show directional impact composition
```

Caveat:

```text
values are directional scenario estimates and may involve double counting
```

---

## 10. Issue Severity Distribution Chart

Source:

```text
graph_model.severity_distribution
```

Categories:

```text
error
warning
info
```

Purpose:

```text
show issue severity profile
```

This helps the user quickly see whether the situation is mostly informational, warning-level, or error-level.

---

## 11. Weekly Issue Count Chart

Source:

```text
graph_model.weekly_issue_counts
```

Purpose:

```text
show timing concentration of issue signals
```

This helps identify stressed weeks in the planning horizon.

---

## 12. Top Issues Tab

The `Top Issues` tab displays ranked issue candidates.

It supports detailed review after the user sees the Summary cards and Graphs tab.

Typical fields may include:

```text
rank
issue_type
severity
node
product
week
estimated impact
impact category
```

This tab is the bridge between visual alert and detailed evidence.

---

## 13. Replan Candidates Tab

The `Replan Candidates` tab displays candidate-only replan options.

Important rule:

```text
candidate_only means display-only review candidate
```

The UI does not execute replan commands.

The tab is for human review.

Future phases may add read-only drilldown, but command execution should remain explicitly controlled and separately designed.

---

## 14. Health Tab

The `Health` tab displays data-quality and integrity signals.

It helps answer:

```text
Can we trust the planning evidence?
```

Examples of health signals may include:

```text
missing data
inconsistent records
data-quality risk
health issue candidates
```

This tab is important because management action should not be based on untrusted evidence.

---

## 15. Assumptions / Exports Tab

The `Assumptions / Exports` tab displays:

```text
Cost / KPI assumptions
export result summaries
file paths or export metadata when available
```

This tab supports traceability.

Important rule:

```text
The tab displays export information only if export results already exist.
```

It does not trigger exports.

---

## 16. Messages Tab

The `Messages` tab displays:

```text
view-model messages
warnings
caveats
next review actions
```

This tab is where the cockpit can explain missing data, caveats, or recommended next review steps.

---

## 17. Read-only Safety Boundary

The entire cockpit UI preserves a strict safety boundary.

The UI does not:

```text
run planning
run Run Full Plan
run the explicit pipeline
run the reporting stack helper
trigger exports
change feature flags
mutate env
execute ReplanCommand
perform automatic replanning
perform OR optimization
write files
delete files
persist database records
persist Knowledge Continuity records
```

The UI only:

```text
reads current env-derived view model
renders read-only cards
renders read-only charts
renders read-only tables
renders messages
```

Core rule:

```text
Show the instruments.
Do not start the engine.
```

---

## 18. Current Runtime Architecture

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
                         ├─ Summary tab
                         │      ├─ KPI Cards
                         │      └─ key-value summary
                         ├─ Graphs tab
                         │      ├─ build_explicit_pipeline_kpi_graph_view_model(view_model)
                         │      ├─ Top Business Impact chart
                         │      ├─ Cost / KPI Impact Composition chart
                         │      ├─ Issue Severity Distribution chart
                         │      └─ Weekly Issue Count chart
                         ├─ Top Issues tab
                         ├─ Replan Candidates tab
                         ├─ Health tab
                         ├─ Assumptions / Exports tab
                         └─ Messages tab
```

This keeps execution and viewing paths separated.

---

## 19. Test Coverage Summary

The UI work is supported by focused tests.

Representative test files:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_view.py
tests/test_explicit_pipeline_management_cockpit_kpi_view_tk_rendering.py
tests/test_explicit_pipeline_management_cockpit_kpi_view_button_integration.py
tests/test_explicit_pipeline_management_cockpit_kpi_graph_view.py
tests/test_explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.py
tests/test_explicit_pipeline_management_cockpit_kpi_cards.py
```

These cover:

```text
view model behavior
Tk rendering behavior
button integration
graph model behavior
Canvas graph rendering
KPI cards
input non-mutation
no-data behavior
core tab preservation
```

---

## 20. Important Design Documents

The cockpit UI is supported by the following design and completion documents:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_view.md
docs/design/explicit_pipeline_management_cockpit_kpi_view_completion.md
docs/design/explicit_pipeline_management_cockpit_kpi_view_tk_rendering.md
docs/design/explicit_pipeline_management_cockpit_kpi_view_tk_rendering_completion.md
docs/design/explicit_pipeline_management_cockpit_kpi_view_button_integration.md
docs/design/explicit_pipeline_management_cockpit_kpi_view_button_integration_completion.md
docs/design/explicit_pipeline_management_cockpit_kpi_integration_overview.md
docs/design/explicit_pipeline_management_cockpit_kpi_graph_view.md
docs/design/explicit_pipeline_management_cockpit_kpi_graph_view_completion.md
docs/design/explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.md
docs/design/explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering_completion.md
docs/design/explicit_pipeline_management_cockpit_kpi_graph_integration_overview.md
docs/design/explicit_pipeline_management_cockpit_kpi_cards.md
docs/design/explicit_pipeline_management_cockpit_kpi_cards_completion.md
```

This overview memo summarizes the UI layer across those documents.

---

## 21. Current User Experience

A typical user path is now:

```text
Run planning
    ↓
Click Explicit KPI View
    ↓
See KPI Cards on Summary
    ↓
Inspect Graphs
    ↓
Review Top Issues
    ↓
Review Replan Candidates
    ↓
Check Health
    ↓
Confirm Assumptions / Exports
    ↓
Read Messages / Next Review Actions
```

The UI now supports:

```text
first-glance review
visual review
detailed evidence review
traceability review
```

---

## 22. What This Means for WOM

This cockpit UI is a major step toward a management-facing WOM experience.

Before:

```text
WOM produced planning artifacts and reports.
```

After:

```text
WOM presents explicit pipeline evidence as a management cockpit.
```

The cockpit does not make decisions automatically.

It supports the manager's review and judgment.

This is aligned with WOM's role as a planning and scenario review environment.

---

## 23. Known Limitations

The current cockpit UI remains an MVP.

It does not yet include:

```text
card color styling
critical threshold rules
click card to filter detail rows
click chart bar to show related issue
detail pane
copy-to-clipboard
waterfall chart
capacity heatmap
severity trend chart
export graph image
Knowledge Continuity handoff
issue review workflow
decision log capture
```

The current UI is useful, but still intentionally simple.

---

## 24. Recommended Next Enhancements

### 24.1 KPI Card Styling

Improve visual distinction for:

```text
normal
warning
unknown
critical
```

while preserving status text.

Potential design document:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_card_styling.md
```

---

### 24.2 Critical Threshold Rules

Define configurable thresholds for:

```text
business impact
capacity violations
management issue count
health warning count
replan candidate count
```

Potential design document:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_thresholds.md
```

---

### 24.3 Drilldown / Detail Pane

Allow read-only interactions such as:

```text
click KPI card
focus related tab
filter related rows
show related issue details
```

Potential design document:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_drilldown.md
```

---

### 24.4 Cost / KPI Waterfall

Add a waterfall chart for executive impact storytelling.

Potential design document:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_waterfall.md
```

---

### 24.5 Capacity Heatmap

Add a node x week pressure map after richer capacity details are exposed.

Potential design document:

```text
docs/design/explicit_pipeline_management_cockpit_capacity_heatmap.md
```

---

### 24.6 Knowledge Continuity Handoff

Connect selected cockpit evidence to the WOM Knowledge Continuity Layer.

Potential design document:

```text
docs/design/explicit_pipeline_management_cockpit_knowledge_continuity_handoff.md
```

Potential mapping:

```text
top impact issues → open issues
health warnings → facts and findings
replan candidates → next-entry prompts
management comments → decision log candidates
```

This must remain explicitly controlled.

---

## 25. Completion Criteria for Current UI Overview

The current UI can be considered complete for this MVP stage because:

```text
[OK] Explicit KPI View opens from main GUI
[OK] Summary tab exists
[OK] Summary tab has KPI Cards
[OK] Graphs tab exists
[OK] Graphs tab has Canvas charts
[OK] Top Issues tab exists
[OK] Replan Candidates tab exists
[OK] Health tab exists
[OK] Assumptions / Exports tab exists
[OK] Messages tab exists
[OK] view remains read-only
[OK] no planning/export/replan execution is introduced
[OK] focused tests cover key UI layers
```

---

## 26. Summary

The Explicit Pipeline Management Cockpit UI is now complete through the MVP cockpit stage.

The cockpit includes:

```text
KPI Cards
Canvas Charts
Issue Tables
Replan Candidate Tables
Health Review
Assumption / Export Review
Messages
```

The UI remains safely read-only:

```text
no planning execution
no export execution
no replan execution
no feature flag mutation
```

WOM now has a visible management cockpit for explicit pipeline KPI evidence.

The next frontier is refinement:

```text
styling
thresholds
drilldown
waterfall
heatmap
Knowledge Continuity handoff
```
