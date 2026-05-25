# Codex Request: Implement Explicit Pipeline Management Cockpit KPI Graph View Model MVP

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_graph_view.md
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
```

The current GUI view is a read-only `ttk.Notebook` table / key-value cockpit view.

The next step is **not drawing charts yet**.

This request is only for the first Graph / Chart View phase:

```text
graph model only
```

---

## 2. Main Objective

Add a pure graph-view-model builder that converts the existing Management Cockpit KPI view model into chart-ready data.

Target function:

```python
build_explicit_pipeline_kpi_graph_view_model(view_model: dict) -> dict
```

Target module to update:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

Target test file to add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_graph_view.py
```

The graph model should support future charts such as:

```text
Top Business Impact Bar Chart
Issue Severity Distribution
Cost / KPI Impact Composition
Weekly Issue Count
```

This request must not render charts.

This request must not modify `cockpit_tk.py`.

This request must not add Canvas drawing.

This request must not add a Graphs tab yet.

---

## 3. Important Constraints

Please follow these constraints strictly:

```text
1. Do not modify pysi/gui/cockpit_tk.py.
2. Do not add GUI buttons.
3. Do not add menu integration.
4. Do not add Canvas rendering.
5. Do not add matplotlib rendering.
6. Do not add a Graphs tab yet.
7. Do not run planning.
8. Do not run explicit pipeline.
9. Do not run reporting stack helper.
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
```

This request is only for:

```text
chart-ready graph model builder + focused tests
```

---

## 4. Files to Modify / Add

Please modify:

```text
pysi/gui/explicit_pipeline_management_cockpit_view.py
```

Please add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_graph_view.py
```

Do not modify:

```text
pysi/gui/cockpit_tk.py
pysi/reporting/*
pysi/plan/*
```

unless a tiny import compatibility issue is absolutely unavoidable.

---

## 5. Existing Functions to Keep

The existing functions must remain available and unchanged in behavior:

```python
build_explicit_pipeline_management_cockpit_view_model(env) -> dict
render_explicit_pipeline_management_cockpit_tk(parent, view_model) -> tk.Toplevel
```

Do not change their schemas or semantics.

The new graph model builder should consume the existing view model schema:

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
def build_explicit_pipeline_kpi_graph_view_model(view_model: dict) -> dict:
    ...
```

The function should be:

```text
pure
deterministic
read-only
safe for missing keys
safe for None values
```

It should not mutate the input `view_model`.

---

## 7. Recommended Graph Model Schema

Return a dictionary with this top-level schema:

```python
{
    "available": bool,
    "top_impact_bars": list[dict],
    "severity_distribution": dict,
    "impact_composition": list[dict],
    "weekly_issue_counts": list[dict],
    "messages": list[str],
}
```

Recommended detailed schema:

```python
{
    "available": True,
    "top_impact_bars": [
        {
            "label": "capacity_bottleneck / MOM_RICE_MILL_A / W12",
            "value": 1250000.0,
            "severity": "warning",
            "issue_type": "capacity_bottleneck",
            "node": "MOM_RICE_MILL_A",
            "week": "12",
        }
    ],
    "severity_distribution": {
        "error": 0,
        "warning": 3,
        "info": 2,
    },
    "impact_composition": [
        {"label": "Lost Sales", "value": 800000.0},
        {"label": "Margin Impact", "value": 300000.0},
        {"label": "Inventory Cost", "value": 100000.0},
        {"label": "Capacity Cost", "value": 50000.0},
        {"label": "Service Penalty", "value": 0.0},
    ],
    "weekly_issue_counts": [
        {"week": "12", "count": 2},
        {"week": "13", "count": 1},
    ],
    "messages": [
        "Graph model is derived from the current read-only KPI view model.",
        "Cost / KPI values are directional scenario estimates, not formal accounting values.",
    ],
}
```

---

## 8. Availability Behavior

The graph model should be considered available when the input view model is available:

```python
bool(view_model.get("available"))
```

If the input view model is missing or not available, return:

```python
{
    "available": False,
    "top_impact_bars": [],
    "severity_distribution": {"error": 0, "warning": 0, "info": 0},
    "impact_composition": [],
    "weekly_issue_counts": [],
    "messages": [
        "No explicit pipeline KPI view data is available for graph rendering."
    ],
}
```

Do not raise.

---

## 9. Top Impact Bars

### 9.1 Source

```python
view_model["top_impact_issues"]
```

### 9.2 Metric

Use:

```text
estimated_total_business_impact
```

### 9.3 Label

Build label from:

```text
issue_type
node
week
```

Recommended format:

```text
{issue_type} / {node} / W{week}
```

If week is already prefixed or non-numeric, use safe string form.

If fields are missing, fall back safely:

```text
issue_type or "issue"
node or ""
week or ""
```

### 9.4 Sort and limit

Sort by:

```text
value descending
severity priority
issue_type
node
week
```

Use severity priority:

```python
SEVERITY_PRIORITY = {
    "error": 0,
    "warning": 1,
    "info": 2,
    "none": 3,
    "": 4,
}
```

Return only top 10 rows.

### 9.5 Safe numeric conversion

Missing / None / invalid values should become:

```python
0.0
```

---

## 10. Severity Distribution

### 10.1 Source

Prefer:

```python
view_model["issue_summary"]
```

Fields:

```text
error_count
warning_count
info_count
```

### 10.2 Output

Return:

```python
{
    "error": int,
    "warning": int,
    "info": int,
}
```

Missing fields should default to 0.

### 10.3 Fallback

If issue summary is empty but issue rows exist, optionally count severities from:

```text
top_impact_issues
replan_candidates
health_summary.top_health_issues
```

This fallback is optional for MVP.

The preferred MVP behavior is summary-based.

---

## 11. Impact Composition

### 11.1 Source

```python
view_model["executive_kpi_summary"]
```

Fields:

```text
estimated_lost_sales_value_total
estimated_margin_impact_total
estimated_inventory_cost_impact_total
estimated_capacity_cost_impact_total
estimated_service_penalty_total
```

### 11.2 Output rows

Return:

```python
[
    {"label": "Lost Sales", "value": ...},
    {"label": "Margin Impact", "value": ...},
    {"label": "Inventory Cost", "value": ...},
    {"label": "Capacity Cost", "value": ...},
    {"label": "Service Penalty", "value": ...},
]
```

### 11.3 Empty / zero behavior

If all values are 0.0, it is acceptable to return the five rows with 0.0 values.

Alternatively, return an empty list and add a message:

```text
No Cost / KPI impact composition is available.
```

Recommended MVP:

```text
return the five rows with 0.0 values
```

because it gives future rendering a stable structure.

---

## 12. Weekly Issue Counts

### 12.1 Source

```python
view_model["top_impact_issues"]
```

### 12.2 Logic

Count rows by the `week` field.

Output:

```python
[
    {"week": "12", "count": 2},
    {"week": "13", "count": 1},
]
```

### 12.3 Sort

Sort week values deterministically.

Recommended:

```text
numeric sort when possible
string sort fallback
```

Examples:

```text
"2" before "10"
"W2" before "W10" if numeric part can be extracted
otherwise normal string sort
```

MVP can implement simple safe sorting:

```python
def _week_sort_key(value):
    ...
```

### 12.4 Missing week

Rows without week should be ignored for weekly count.

---

## 13. Messages

The graph model should include useful messages.

Always include:

```text
Graph model is derived from the current read-only KPI view model.
```

If KPI summary caveats are present, preserve or add messages such as:

```text
Cost / KPI values are directional scenario estimates, not formal accounting values.
Double counting may be possible depending on assumptions.
```

If there are no top impact bars:

```text
No top impact issues are available for graph rendering.
```

If no weekly issue data exists:

```text
No week-level issue data is available for graph rendering.
```

Keep messages deterministic.

---

## 14. Helper Functions

It is fine to add small private helpers in the module.

Recommended helpers:

```python
_to_float(value) -> float
_to_int(value) -> int
_as_dict(value) -> dict
_as_list(value) -> list
_severity_rank(value) -> int
_make_top_impact_label(row: dict) -> str
_week_sort_key(value) -> tuple
```

If similar helpers already exist in the module, reuse them instead of duplicating.

Keep helpers deterministic and small.

---

## 15. Input Mutation Rule

The function must not mutate the input `view_model`.

Tests should confirm this using:

```python
copy.deepcopy(view_model)
```

and then comparing after calling the graph model builder.

---

## 16. Tests to Add

Please add:

```text
tests/test_explicit_pipeline_management_cockpit_kpi_graph_view.py
```

### 16.1 No data

Input:

```python
{}
```

or:

```python
{"available": False}
```

Verify:

```text
available is False
top_impact_bars == []
severity_distribution == {"error": 0, "warning": 0, "info": 0}
impact_composition exists
weekly_issue_counts == []
no exception
```

### 16.2 Populated top impact bars

Input view model with at least three top impact issues.

Verify:

```text
top_impact_bars sorted by value descending
top_impact_bars has labels
top_impact_bars preserves severity / issue_type / node / week
```

### 16.3 Top 10 limit

Input 12 or more top impact issues.

Verify:

```text
len(top_impact_bars) == 10
```

### 16.4 Severity distribution

Input:

```python
"issue_summary": {
    "error_count": 1,
    "warning_count": 2,
    "info_count": 3,
}
```

Verify:

```python
{"error": 1, "warning": 2, "info": 3}
```

### 16.5 Impact composition

Input executive KPI summary with five components.

Verify:

```text
five rows returned
labels are Lost Sales / Margin Impact / Inventory Cost / Capacity Cost / Service Penalty
values match input
```

### 16.6 Weekly issue counts

Input top impact issues with weeks:

```text
12, 12, 13
```

Verify:

```text
weekly_issue_counts == [{"week": "12", "count": 2}, {"week": "13", "count": 1}]
```

### 16.7 Input not mutated

Deep copy the input before calling.

Verify input is unchanged after the call.

### 16.8 Missing / invalid values safe

Input with missing impact, None week, invalid numeric string.

Verify no exception and safe defaults.

---

## 17. Existing Tests to Run

Please run:

```bat
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

## 18. Completion Criteria

This request is complete when:

```text
[OK] build_explicit_pipeline_kpi_graph_view_model(view_model) exists
[OK] function returns graph-ready dict
[OK] graph model contains available
[OK] graph model contains top_impact_bars
[OK] graph model contains severity_distribution
[OK] graph model contains impact_composition
[OK] graph model contains weekly_issue_counts
[OK] graph model contains messages
[OK] missing data is handled safely
[OK] top impact bars are sorted and limited to top 10
[OK] severity distribution is derived from issue_summary
[OK] impact composition is derived from executive_kpi_summary
[OK] weekly issue counts are derived from top_impact_issues
[OK] input view_model is not mutated
[OK] focused tests pass
[OK] existing view-model/rendering/button tests pass
[OK] no cockpit_tk.py modification
[OK] no Canvas rendering
[OK] no Graphs tab added
[OK] no planning/export/replan execution
```

---

## 19. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. Graph model schema implemented
4. Top impact bar behavior
5. Severity distribution behavior
6. Impact composition behavior
7. Weekly issue count behavior
8. Input mutation safety
9. Safety boundaries preserved
10. Test commands executed
11. Test results
12. Any skipped tests and why
13. Limitations / follow-up
```

Please do not proceed into:

```text
Canvas rendering
matplotlib rendering
Graphs tab integration
cockpit_tk.py modification
graph buttons
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
Explicit Pipeline Management Cockpit KPI Graph View Model MVP
```
