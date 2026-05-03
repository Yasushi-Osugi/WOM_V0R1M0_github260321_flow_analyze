# WOM MOSD Phase 2B+5d One-shot E2E Lane Price Chart from Env Design

## 1. Purpose

Phase 2B+5d defines the design for a one-shot runtime helper that generates E2E Lane Price & Cost Structure charts from a WOM runtime env.

Previous phases prepared the required components:

```text
Phase 2B+5a:
  PlanNode tree → e2e_lane_route.csv

Phase 2B+5b:
  e2e_lane_route.csv → chart X-axis ordering

Phase 2B+5c:
  runtime env → e2e_lane_route.csv

Phase 2B+5d combines these into one callable helper:

generate_e2e_lane_price_chart_from_env(...)

The helper should:

1. Export e2e_lane_route.csv from env
2. Generate full_price E2E lane chart
3. Generate delta_only E2E lane chart
4. Return generated PNG file paths

This phase does not add a GUI button yet.

2. Background

WOM now has the following runtime/reporting components:

node_price_waterfall.csv
price_propagation_trace.csv
e2e_lane_route.csv
price_propagation_chart.py
e2e_lane_route_runtime.py

The current manual flow is:

Run Full Plan
  ↓
node_price_waterfall.csv
price_propagation_trace.csv
  ↓
export_e2e_lane_route_from_env(...)
  ↓
e2e_lane_route.csv
  ↓
generate_price_waterfall_stacked_bar(..., chart_mode="full_price")
  ↓
generate_price_waterfall_stacked_bar(..., chart_mode="delta_only")

Phase 2B+5d makes this flow callable with one helper.

3. Scope
In scope
Add a one-shot reporting helper.
Read WOM runtime env.
Export e2e_lane_route.csv from env.
Generate E2E full_price chart.
Generate E2E delta_only chart.
Return generated file paths.
Keep implementation outside GUI.
Add focused tests using fake env and temporary CSVs.
Add documentation note under docs/notes.
Not in scope
GUI menu/button integration.
Management Cockpit integration.
Automatic pipeline hook.
Money evaluation changes.
Price formation changes.
Purchase cost propagation changes.
PSI planning changes.
Fan-in E2E lane export.
Bidirectional target costing.
Downward allowable-cost propagation.
Master CSV fixture changes.
4. Proposed Module

Preferred new module:

pysi/reporting/e2e_lane_price_chart_runtime.py

This module should depend on the already implemented modules:

from pysi.reporting.e2e_lane_route_runtime import export_e2e_lane_route_from_env
from pysi.reporting.price_propagation_chart import generate_price_waterfall_stacked_bar

It should not duplicate route export or chart generation logic.

5. Primary Function
def generate_e2e_lane_price_chart_from_env(
    env,
    *,
    product_name: str,
    leaf_node: str,
    inbound_leaf_node: str | None = None,
    node_price_waterfall_csv: str = "data/node_price_waterfall.csv",
    price_propagation_trace_csv: str = "data/price_propagation_trace.csv",
    e2e_lane_route_csv: str = "data/e2e_lane_route.csv",
    output_dir: str = "outputs/reporting_mvp/price_propagation",
    supply_point_node: str = "supply_point",
    generate_full_price: bool = True,
    generate_delta_only: bool = True,
    skip_all_zero: bool = True,
) -> dict:
    """
    Generate E2E Lane Price & Cost Structure charts from WOM runtime env.

    Returns:
        {
            "product_name": "...",
            "leaf_node": "...",
            "e2e_lane_route_csv": "...",
            "generated_files": [...],
            "route_rows": [...],
            "errors": [...],
            "warnings": [...],
        }
    """
6. Required Behavior
6.1 Validate inputs safely

If env is None:

return result with errors

If product_name is blank:

return result with errors

If leaf_node is blank:

return result with errors

The helper should not crash in GUI context.

6.2 Export E2E lane route

Call:

route_rows = export_e2e_lane_route_from_env(
    env,
    product_name=product_name,
    leaf_node=leaf_node,
    inbound_leaf_node=inbound_leaf_node,
    output_path=e2e_lane_route_csv,
    supply_point_node=supply_point_node,
)

If no route rows are generated:

return result with warnings
do not call chart generation
6.3 Generate full_price chart

If generate_full_price is True:

generate_price_waterfall_stacked_bar(
    node_price_waterfall_csv,
    output_dir,
    product=product_name,
    leaf_node=leaf_node,
    e2e_lane_route_csv=e2e_lane_route_csv,
    price_propagation_trace_csv=price_propagation_trace_csv,
    chart_mode="full_price",
    chart_scope="e2e_primary",
    inbound_leaf_node=inbound_leaf_node,
    supply_point_node=supply_point_node,
    skip_all_zero=skip_all_zero,
)
6.4 Generate delta_only chart

If generate_delta_only is True:

generate_price_waterfall_stacked_bar(
    node_price_waterfall_csv,
    output_dir,
    product=product_name,
    leaf_node=leaf_node,
    e2e_lane_route_csv=e2e_lane_route_csv,
    price_propagation_trace_csv=price_propagation_trace_csv,
    chart_mode="delta_only",
    chart_scope="e2e_primary",
    inbound_leaf_node=inbound_leaf_node,
    supply_point_node=supply_point_node,
    skip_all_zero=skip_all_zero,
)
6.5 Return result object

The function should return a dict like:

{
    "product_name": product_name,
    "leaf_node": leaf_node,
    "inbound_leaf_node": inbound_leaf_node,
    "e2e_lane_route_csv": e2e_lane_route_csv,
    "generated_files": generated_files,
    "route_rows": route_rows,
    "errors": [],
    "warnings": [],
}
7. Output Files
7.1 Route CSV
data/e2e_lane_route.csv
7.2 Full price chart

Expected output from existing chart generator:

outputs/reporting_mvp/price_propagation/<product>_<leaf_node>_e2e_lane_price_cost_structure.png
7.3 Delta-only chart

Expected output:

outputs/reporting_mvp/price_propagation/<product>_<leaf_node>_e2e_lane_added_cost_structure_delta_only.png

Actual filenames may follow current sanitization rules.

8. Error and Warning Handling
8.1 Missing env
errors.append("env is None")
return result
8.2 Blank product
errors.append("product_name is required")
return result
8.3 Blank leaf_node
errors.append("leaf_node is required")
return result
8.4 Missing node_price_waterfall.csv

If chart generation cannot proceed because node_price_waterfall_csv does not exist:

return result with errors or warnings

Preferred behavior:

do not crash
add a clear error message
return generated_files as empty list
8.5 Missing price_propagation_trace.csv

This should not necessarily fail if e2e_lane_route_csv exists.

However, the helper may warn:

price_propagation_trace_csv not found; chart generation will rely on e2e_lane_route_csv only
8.6 No route rows

If route export returns empty rows:

warnings.append("no e2e lane route rows generated")
return without chart generation
9. Relationship with Existing Modules

Phase 2B+5d should compose existing modules.

9.1 Route export

Use:

pysi/reporting/e2e_lane_route_runtime.py
9.2 Chart generation

Use:

pysi/reporting/price_propagation_chart.py
9.3 No duplication

Do not duplicate:

PlanNode traversal
route stitching
CSV export format
chart rendering logic
component selection logic
10. Tests

Add focused tests.

Suggested file:

tests/reporting_test_e2e_lane_price_chart_runtime.py
Test 1: one-shot helper generates route and charts

Given:

fake env with inbound and outbound PlanNode trees
temporary node_price_waterfall.csv
temporary price_propagation_trace.csv

When calling:

generate_e2e_lane_price_chart_from_env(
    env,
    product_name="PRODUCT_A",
    leaf_node="CS",
    node_price_waterfall_csv=temp_waterfall,
    price_propagation_trace_csv=temp_trace,
    e2e_lane_route_csv=temp_route,
    output_dir=temp_output,
)

Expected:

route CSV generated
full_price PNG generated
delta_only PNG generated
generated_files length == 2
errors == []
Test 2: full_price only

Given:

generate_delta_only=False

Expected:

only full_price chart generated
Test 3: delta_only only

Given:

generate_full_price=False

Expected:

only delta_only chart generated
Test 4: env None

Given:

env = None

Expected:

errors not empty
generated_files == []
no crash
Test 5: blank product

Given:

product_name = ""

Expected:

errors not empty
generated_files == []
Test 6: blank leaf_node

Given:

leaf_node = ""

Expected:

errors not empty
generated_files == []
Test 7: missing node_price_waterfall.csv

Given missing waterfall CSV path.

Expected:

errors or warnings include missing input
generated_files == []
no crash
Test 8: existing tests still pass

Existing test groups must continue to pass.

11. Validation Commands

Run:

PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_price_chart_runtime.py
PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_runtime.py
PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_exporter.py
PYTHONPATH=. pytest -q tests/reporting_test_price_propagation_chart.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py

Combined:

PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py tests/evaluate_test_money_evaluator_node_price_formation.py tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py tests/reporting_test_price_propagation_chart.py tests/reporting_test_e2e_lane_route_exporter.py tests/reporting_test_e2e_lane_route_runtime.py tests/reporting_test_e2e_lane_price_chart_runtime.py
12. Manual Usage

After python -m main and Run Full Plan, when runtime env is available:

from pysi.reporting.e2e_lane_price_chart_runtime import generate_e2e_lane_price_chart_from_env

result = generate_e2e_lane_price_chart_from_env(
    env,
    product_name="IPHONE_NM_2028_BASE",
    leaf_node="CS_US_MAINSTREAM",
)

Expected result:

{
    "product_name": "IPHONE_NM_2028_BASE",
    "leaf_node": "CS_US_MAINSTREAM",
    "e2e_lane_route_csv": "data/e2e_lane_route.csv",
    "generated_files": [
        "...e2e_lane_price_cost_structure.png",
        "...e2e_lane_added_cost_structure_delta_only.png",
    ],
    "errors": [],
    "warnings": [],
}
13. Documentation Note

Add:

docs/notes/mosd_phase2b5d_one_shot_e2e_lane_price_chart_from_env_260503.md

Suggested content:

# MOSD Phase 2B+5d One-shot E2E Lane Price Chart from Env

## Purpose

Generate E2E Lane Price & Cost Structure charts from WOM runtime env with one helper call.

## Background

Phase 2B+5a exports E2E lane route from PlanNode trees.
Phase 2B+5b makes chart generator consume e2e_lane_route.csv.
Phase 2B+5c exports route CSV from runtime env.

Phase 2B+5d combines these into one helper.

## Implemented behavior

- Export e2e_lane_route.csv from env.
- Generate full_price E2E lane chart.
- Generate delta_only E2E lane chart.
- Return generated PNG paths.
- Do not change money evaluation or planner behavior.

## Not included

- GUI button
- Management Cockpit integration
- automatic pipeline hook
- fan-in E2E lane export
- price recalculation

## Testing

List test commands and results.
14. Acceptance Criteria

Phase 2B+5d is accepted when:

pysi/reporting/e2e_lane_price_chart_runtime.py exists.
It exposes generate_e2e_lane_price_chart_from_env(...).
It calls export_e2e_lane_route_from_env(...).
It calls generate_price_waterfall_stacked_bar(...).
It generates full_price chart when requested.
It generates delta_only chart when requested.
It returns generated PNG paths.
It returns route rows.
It handles missing env safely.
It handles blank product safely.
It handles blank leaf node safely.
New one-shot tests pass.
Existing route runtime tests pass.
Existing route exporter tests pass.
Existing chart tests pass.
Existing Phase 2B money evaluator tests pass.
No money evaluation logic is changed.
No planner behavior is changed.
No GUI behavior is changed.
No committed master CSV fixtures are changed.
15. Future Phase 2B+5e

Phase 2B+5e may add a thin GUI adapter in:

pysi/gui/cockpit_tk.py

Possible UI label:

Price & Cost Structure

GUI responsibility should be limited to:

1. get selected product
2. get selected or input leaf_node
3. call generate_e2e_lane_price_chart_from_env(...)
4. show generated file paths or open PNG

Do not place route export or chart generation logic directly in cockpit_tk.py.

16. Summary

Phase 2B+5d turns the current route export and chart generation parts into one callable runtime helper.

The key transition is:

Before:
  export route CSV manually
  then call chart generator manually twice

After:
  generate_e2e_lane_price_chart_from_env(...)
  handles route export + full_price chart + delta_only chart

This prepares WOM for a future GUI button:

Price & Cost Structure

without putting reporting logic inside the GUI.