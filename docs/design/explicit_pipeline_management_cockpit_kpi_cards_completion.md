# Explicit Pipeline Management Cockpit KPI Cards Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-25  
**Status:** Completion memo  
**Target path:** `docs/design/explicit_pipeline_management_cockpit_kpi_cards_completion.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Explicit Pipeline Management Cockpit KPI Cards MVP**.

The purpose of this milestone was to add read-only KPI Cards to the top area of the existing `Summary` tab in the Explicit Pipeline Management Cockpit KPI View.

The completed cockpit path is now:

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

This milestone adds large, compact management warning lamps to the existing table / graph cockpit.

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
    ↓
Canvas graph rendering / Graphs tab
```

The cockpit already had:

```text
Summary
Graphs
Top Issues
Replan Candidates
Health
Assumptions / Exports
Messages
```

The `Graphs` tab already provided visual charts.

This milestone improves the first screen of the cockpit by adding KPI Cards to the `Summary` tab.

---

## 3. Implemented Files

This milestone modified or added:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
tests/test_explicit_pipeline_management_cockpit_kpi_cards.py
```

The implementation was committed as:

```text
92a71ac Add explicit KPI cards to management cockpit summary
```

---

## 4. Main Implementation

A read-only KPI card layer was added to:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

The implementation added private helpers to:

```text
build KPI card data
render KPI card frames
render individual KPI cards
```

The cards are placed at the top of the existing `Summary` tab.

Existing Summary key-value tables remain visible.

Existing tabs, including `Graphs`, remain visible.

No public function signature was changed.

---

## 5. KPI Card Helpers Added

The implementation added private helpers such as:

```text
_build_explicit_pipeline_kpi_cards
_create_kpi_cards_frame
_create_kpi_card
```

Additional small utility helpers were added as needed.

These helpers are private, deterministic, and read-only.

They consume the existing `view_model`.

They do not read `env`.

They do not run planning.

They do not run exports.

They do not execute replan commands.

---

## 6. KPI Cards Implemented

The MVP implements five KPI Cards:

```text
1. Total Business Impact
2. Capacity Violations
3. Management Issues
4. Health Warnings
5. Replan Candidates
```

These are the cockpit's first-row management signals.

They are intended to answer:

```text
How large is the impact?
Where is capacity pressure?
How many management issues exist?
Can we trust the data?
Are there candidate-only replan options?
```

---

## 7. Card 1: Total Business Impact

### Source

```text
executive_kpi_summary.estimated_total_business_impact
```

### Unit

```text
executive_kpi_summary.currency
```

### Subtitle

```text
Directional estimate
```

### Status behavior

```text
value > 0  → warning
value == 0 → normal
no data    → unknown
```

This card is directional and should not be interpreted as a formal accounting value.

---

## 8. Card 2: Capacity Violations

### Source

```text
capacity_summary.capacity_violation_record_count
```

### Unit

```text
records
```

### Subtitle

```text
Capacity pressure
```

### Status behavior

```text
count > 0  → warning
count == 0 → normal
no data    → unknown
```

This card indicates capacity pressure requiring review.

---

## 9. Card 3: Management Issues

### Source

```text
issue_summary.management_issue_candidate_count
```

### Unit

```text
issues
```

### Subtitle

```text
Management attention
```

### Status behavior

```text
count > 0  → warning
count == 0 → normal
no data    → unknown
```

This card shows how many management-level issue candidates exist.

---

## 10. Card 4: Health Warnings

### Preferred source

```text
health_summary.health_issue_count
```

### Fallback source

```text
issue_summary.health_issue_candidate_count
```

### Unit

```text
warnings
```

### Subtitle

```text
Data quality / health
```

### Status behavior

```text
count > 0  → warning
count == 0 → normal
no data    → unknown
```

This card answers the management question:

```text
Can we trust the evidence?
```

---

## 11. Card 5: Replan Candidates

### Preferred source

```text
len(replan_candidates)
```

### Fallback source

```text
issue_summary.replan_command_candidate_count
```

### Unit

```text
candidates
```

### Subtitle

```text
Candidate-only actions
```

### Status behavior

```text
count > 0  → warning
count == 0 → normal
no data    → unknown
```

Important rule:

```text
This card does not execute replan candidates.
```

It only displays the number of candidate-only actions.

---

## 12. No-Data Behavior

If the view model is unavailable or missing:

```text
view_model.available is False
```

the implementation returns five stable cards with:

```text
value = N/A
status = unknown
```

The five card titles remain visible:

```text
Total Business Impact
Capacity Violations
Management Issues
Health Warnings
Replan Candidates
```

This keeps the UI stable even before planning data exists.

---

## 13. Summary Tab Integration

The `Summary` tab now conceptually renders:

```text
Summary tab
    ├─ KPI Cards frame
    └─ existing key-value summary sections
```

The cards are rendered before the existing key-value tree.

The existing Summary content remains available.

This preserves backward compatibility while improving first-glance readability.

---

## 14. Rendering Approach

The implementation uses standard Tk / ttk widgets:

```text
ttk.LabelFrame
ttk.Label
```

No external dependency was added.

No matplotlib was introduced.

The cards are read-only visual elements.

They display:

```text
title
value + unit
subtitle
status
```

Status is visible as text, so the cards do not rely on color alone.

---

## 15. Input Mutation Safety

The implementation preserves the non-mutation rule.

Tests verify that:

```text
_build_explicit_pipeline_kpi_cards(view_model)
render_explicit_pipeline_management_cockpit_tk(root, view_model)
```

do not mutate the input `view_model`.

This was verified using:

```python
copy.deepcopy(view_model)
```

before and after card building / rendering.

---

## 16. Safety Boundaries Preserved

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
interactive card clicks
drilldown behavior
```

The implementation is view-only.

The rule remains:

```text
Show the warning lamps.
Do not start the engine.
```

---

## 17. Tests Added

The focused test file is:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_cards.py
```

It covers:

```text
1. populated KPI card model
2. no-data KPI card model
3. Summary tab rendering with cards
4. core tab preservation
5. input view_model non-mutation
```

The tests use safe Tk initialization / skip behavior for environment-sensitive rendering.

---

## 18. Validation

The focused KPI Cards test passed:

```bat
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_cards.py
```

Observed result:

```text
3 passed
```

Related tests also passed:

```bat
python -m pytest tests/test_explicit_pipeline_management_cockpit_kpi_graph_canvas_rendering.py
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
Graph Canvas Rendering: 4 passed, 1 skipped
Graph View Model: 8 passed
Button Integration: 1 passed
Tk Rendering: 3 passed
KPI View Model: 8 passed
Reporting Stack Insertion: 7 passed
Reporting Flags: 10 passed
Covid Vaccine optional: 1 passed
```

The `1 skipped` in Graph Canvas Rendering is acceptable because Tk rendering tests can be environment-sensitive.

No failures or errors remained at commit time.

---

## 19. Completion Criteria

This milestone satisfies the intended completion criteria.

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
[OK] focused KPI card tests pass
[OK] existing graph / view / button tests pass
```

---

## 20. Meaning of This Milestone

Before this milestone:

```text
Explicit KPI View had Summary, tables, and Graphs, but no first-glance KPI card row.
```

After this milestone:

```text
Explicit KPI View Summary tab has a KPI Cards row at the top.
```

This means the manager can immediately see:

```text
business impact
capacity pressure
management issue count
health warning count
replan candidate count
```

before reading details.

The cockpit now has a stronger first-screen management signal.

---

## 21. Current Pipeline Position

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
KPI Cards                                        ✅ completed
    ↓
future drilldown / waterfall / heatmap
```

---

## 22. Current Operational Meaning

The user can now:

```text
Run planning
    ↓
open Explicit KPI View
    ↓
see KPI Cards immediately on Summary
    ↓
inspect Graphs
    ↓
inspect Top Issues / Replan Candidates / Health / Assumptions / Messages
```

The cockpit now supports both:

```text
first-glance management review
and
detailed evidence review
```

---

## 23. Known Limitations

This milestone intentionally keeps KPI Cards simple.

It does not yet implement:

```text
card color styling
critical threshold rules
click card to filter table rows
click card to open detail pane
card-level tooltips
copy card values
responsive wrapping
KPI cards in Graphs tab
Knowledge Continuity handoff
```

The cards are MVP warning lamps, not a full interactive dashboard.

---

## 24. Future Milestones

### 24.1 Card styling

Improve visual distinction among:

```text
normal
warning
unknown
critical
```

while keeping status text visible.

### 24.2 Critical thresholds

Add threshold rules such as:

```text
capacity violations above threshold → critical
business impact above threshold → critical
health warnings above threshold → critical
```

These should be configurable later.

### 24.3 Card drilldown

Allow clicking a card to:

```text
focus related tab
filter related rows
show detail summary
```

The first drilldown phase should remain read-only.

### 24.4 Waterfall chart

Add a Cost / KPI waterfall chart for more executive-friendly impact storytelling.

### 24.5 Knowledge Continuity handoff

Later, selected card / chart / issue insights may feed:

```text
open issues
facts and findings
decision log candidates
next-entry prompts
```

through the WOM Knowledge Continuity Layer.

This should remain separately designed and explicitly controlled.

---

## 25. Summary

The Explicit Pipeline Management Cockpit KPI Cards MVP is complete.

The key achievement is:

```text
Explicit KPI View Summary tab now includes five read-only KPI Cards.
```

The cards are:

```text
Total Business Impact
Capacity Violations
Management Issues
Health Warnings
Replan Candidates
```

The milestone remains safely non-invasive:

```text
no cockpit_tk.py change
no new button
no planning execution
no export execution
no replan execution
```

The cockpit now has:

```text
KPI cards
Graphs tab
Detailed evidence tabs
```

The large warning lamps are installed and tested.
