# WOM MOSD Phase 2B+5b E2E Lane Route CSV Chart Input Design

## 1. Purpose

Phase 2B+5b defines the design for using `e2e_lane_route.csv` as the route-order input for E2E Price & Cost Structure charts.

Phase 2B+5a introduced a PlanNode tree based route exporter that can generate:

```text
data/e2e_lane_route.csv

from WOM product-specific planning trees:

prod_tree_dict_IN[product]
prod_tree_dict_OT[product]

Phase 2B+5b connects this exported route file to the chart generator:

pysi/reporting/price_propagation_chart.py

so that the chart X-axis follows the correct E2E lane order:

inbound upstream
→ supply_point
→ outbound downstream
→ selected market leaf

The goal is to make the E2E Lane Price & Cost Structure Chart reflect WOM's actual product-specific PlanNode tree ordering.

2. Background

Current implemented phases:

Phase 2B+1:
  parent.ship_price_per_lot
  → child.purchase_cost_per_lot

Phase 2B+2:
  purchase_cost_per_lot
  + node cost components
  + target_profit_per_lot
  → ship_price_per_lot

Phase 2B+3:
  export node_price_waterfall.csv
  export price_propagation_trace.csv

Phase 2B+4:
  generate price propagation stacked bar chart

Phase 2B+4a:
  improve route ordering, delta_only mode, and all-zero handling

Phase 2B+5:
  add E2E lane chart scope

Phase 2B+5a:
  export E2E lane route from product-specific PlanNode trees

Phase 2B+5b completes the next step:

e2e_lane_route.csv
→ chart X-axis ordering
3. Problem Statement

Phase 2B+5 can generate E2E-named chart files, but if it relies only on:

price_propagation_trace.csv

the route ordering may still be incomplete or reversed.

The correct route order should come from:

e2e_lane_route.csv

because this file is generated from WOM's product-specific planning trees.

Without using e2e_lane_route.csv, the chart may still show nodes in an order such as:

CS_US_MAINSTREAM
→ DAD_FAS_AMER
→ RT_US_CARRIER
→ WS_NA
→ supply_point

whereas the intended order is:

inbound upstream
→ supply_point
→ DAD_FAS_AMER
→ WS_NA
→ RT_US_CARRIER
→ CS_US_MAINSTREAM
4. Scope
In scope
Add optional e2e_lane_route_csv argument to chart generator.
Load data/e2e_lane_route.csv.
Filter route rows by:
product
leaf_node
chart_scope
optional inbound_leaf_node
Use sequence_no from e2e_lane_route.csv for X-axis ordering.
Use node_name route order to filter and sort node_price_waterfall.csv rows.
Preserve existing chart behavior when e2e_lane_route_csv is not provided.
Preserve existing price_propagation_trace_csv ordering fallback.
Support both:
full_price
delta_only
Add focused tests.
Add implementation note under docs/notes.
Not in scope
Generating e2e_lane_route.csv from runtime env.
GUI integration.
Management Cockpit integration.
Money evaluation changes.
Price formation changes.
Purchase cost propagation changes.
Planner behavior changes.
Fan-in E2E lane chart.
Bidirectional target costing.
Downward allowable-cost propagation.
Inventory B/S to P/L bridge.
5. Input Files
5.1 node_price_waterfall.csv

Required chart value input:

data/node_price_waterfall.csv

This file contains product × node price and cost component values.

Main fields used:

product
node_name
purchase_cost_per_lot
value_added_cost_per_lot
variable_cost_per_lot
fixed_cost_per_lot
logistics_cost_per_lot
inventory_handling_cost_per_lot
tax_tariff_cost_per_lot
target_profit_per_lot
ship_price_per_lot
inventory_unit_value_per_lot
price_formation_mode
5.2 e2e_lane_route.csv

New preferred route-order input:

data/e2e_lane_route.csv

Expected fields:

product
lane_id
leaf_node
inbound_leaf_node
chart_scope

sequence_no
segment
direction
node_name
node_character

parent_node
child_node
depth
is_supply_point
route_role
source_tree
remarks
5.3 price_propagation_trace.csv

Existing fallback input:

data/price_propagation_trace.csv

This remains useful for parent ship price → child purchase cost inspection and fallback ordering.

6. Updated Chart Function Interface

Current function:

def generate_price_waterfall_stacked_bar(
    node_price_waterfall_csv: str,
    output_dir: str,
    *,
    product: str | None = None,
    direction: str | None = None,
    leaf_node: str | None = None,
    price_propagation_trace_csv: str | None = None,
    chart_mode: str = "full_price",
    chart_scope: str = "outbound_only",
    inbound_leaf_node: str | None = None,
    supply_point_node: str = "supply_point",
    skip_all_zero: bool = True,
) -> list[str]:
    ...

Phase 2B+5b should extend it to:

def generate_price_waterfall_stacked_bar(
    node_price_waterfall_csv: str,
    output_dir: str,
    *,
    product: str | None = None,
    direction: str | None = None,
    leaf_node: str | None = None,
    price_propagation_trace_csv: str | None = None,
    e2e_lane_route_csv: str | None = None,
    chart_mode: str = "full_price",
    chart_scope: str = "outbound_only",
    inbound_leaf_node: str | None = None,
    supply_point_node: str = "supply_point",
    skip_all_zero: bool = True,
) -> list[str]:
    ...
Backward compatibility

Existing calls without e2e_lane_route_csv must continue to work.

7. Route Ordering Priority

When generating chart rows, use the following priority:

1. e2e_lane_route_csv
2. price_propagation_trace_csv
3. node_price_waterfall.csv sequence_no
4. node_price_waterfall.csv row order
7.1 e2e_lane_route_csv priority

If e2e_lane_route_csv is provided and contains matching route rows, use it as the primary order source.

Matching criteria:

product == selected product
leaf_node == selected leaf_node if provided
chart_scope == selected chart_scope if provided

If inbound_leaf_node is provided, also match it when possible.

7.2 Fallback

If no matching route rows are found:

fall back to price_propagation_trace_csv behavior
do not crash
optionally print a warning
8. Route Row Filtering
8.1 Product

If product is provided:

route_row.product == product
8.2 Leaf node

If leaf_node is provided:

route_row.leaf_node == leaf_node

If route rows have blank leaf_node, do not use them for leaf-specific chart ordering.

8.3 Chart scope

If chart_scope = e2e_primary, prefer rows with:

chart_scope == e2e_primary

If chart_scope is blank in route CSV, fallback may still be allowed if product and leaf_node match.

8.4 Inbound leaf node

If inbound_leaf_node is provided:

route_row.inbound_leaf_node == inbound_leaf_node

If not provided, accept rows with blank inbound_leaf_node.

9. Sorting Rule

Sort route rows by:

sequence_no

Then use the ordered node_name list as the chart X-axis order.

Example route:

1 MOM_final_assy_ASIA
2 supply_point
3 DAD_FAS_AMER
4 WS_NA
5 RT_US_CARRIER
6 CS_US_MAINSTREAM

The chart rows should be sorted in exactly that order.

If node_price_waterfall.csv has multiple rows for the same node, preserve the first matching row for the selected product.

10. Waterfall Row Filtering by Route

After route order is found:

route_nodes = [row.node_name for row in e2e_lane_route.csv]

Filter node_price_waterfall.csv rows:

product == selected product
node_name in route_nodes

Then sort according to route_nodes.

Rows not in the route should be excluded.

This is important because the chart must show a lane, not the full network.

11. Direction Handling

node_price_waterfall.csv may have:

direction = unknown

even when price_propagation_trace.csv or e2e_lane_route.csv has direction.

Therefore, when e2e_lane_route_csv is provided, do not require waterfall rows to match direction.

Direction should be used primarily for route rows, not for filtering out waterfall rows too aggressively.

This avoids the previous issue:

waterfall direction = unknown
trace direction = outbound
→ chart rows become empty
12. Chart Title and Y-axis

Phase 2B+5b should preserve the improved labels.

12.1 E2E full price title
E2E Lane Price & Cost Structure per Lot - <product> → <leaf_node>
12.2 E2E delta-only title
E2E Lane Added Cost Structure per Lot - <product> → <leaf_node> [delta only]
12.3 Y-axis label

Use:

Price / Cost per lot

Do not use:

Amount per lot

because this chart is not:

Ship_Price × Lot_QTY

It is per-lot price and cost structure.

13. Chart Modes
13.1 full_price

Stack components:

purchase_cost_per_lot
value_added_cost_per_lot
variable_cost_per_lot
fixed_cost_per_lot
logistics_cost_per_lot
inventory_handling_cost_per_lot
tax_tariff_cost_per_lot
target_profit_per_lot
13.2 delta_only

Stack components:

value_added_cost_per_lot
variable_cost_per_lot
fixed_cost_per_lot
logistics_cost_per_lot
inventory_handling_cost_per_lot
tax_tariff_cost_per_lot
target_profit_per_lot
13.3 Always excluded

Never stack:

inventory_unit_value_per_lot
14. Suggested Implementation Location

Modify existing module:

pysi/reporting/price_propagation_chart.py

Suggested new helpers:

def load_e2e_lane_route(path: str) -> list[dict]:
    ...

def select_e2e_lane_route_rows(
    route_rows: list[dict],
    *,
    product: str,
    leaf_node: str | None = None,
    chart_scope: str | None = None,
    inbound_leaf_node: str | None = None,
) -> list[dict]:
    ...

def build_route_order_from_e2e_lane_rows(route_rows: list[dict]) -> list[str]:
    ...

def sort_waterfall_rows_by_route(
    waterfall_rows: list[dict],
    route_nodes: list[str],
) -> list[dict]:
    ...

Keep changes local to the reporting chart module if possible.

Do not modify e2e_lane_route_exporter.py unless required by tests.

15. Output File Names

Preserve Phase 2B+5 output naming.

For E2E full price:

<product>_<leaf_node>_e2e_lane_price_cost_structure.png

For E2E delta-only:

<product>_<leaf_node>_e2e_lane_added_cost_structure_delta_only.png

If inbound_leaf_node is provided, optional future naming:

<product>_<inbound_leaf_node>_to_<leaf_node>_e2e_lane_price_cost_structure.png

This is optional for Phase 2B+5b.

16. Tests

Add focused tests to:

tests/reporting_test_price_propagation_chart.py

or add:

tests/reporting_test_e2e_lane_route_chart_input.py
Test 1: load e2e lane route CSV

Given route CSV rows:

sequence_no,node_name
1,MOM
2,supply_point
3,DAD
4,CS

Expected ordered route nodes:

MOM
supply_point
DAD
CS
Test 2: chart uses e2e route order

Given node_price_waterfall.csv rows in random order:

CS
DAD
MOM
supply_point

and e2e_lane_route.csv order:

MOM
supply_point
DAD
CS

Expected internal sorted chart rows:

MOM
supply_point
DAD
CS

If image inspection is hard, expose and test helper output.

Test 3: chart excludes nodes not in route

Given waterfall rows:

MOM
supply_point
DAD
CS
OTHER_NODE

and route rows:

MOM
supply_point
DAD
CS

Expected chart rows do not include:

OTHER_NODE
Test 4: waterfall direction unknown still works

Given:

node_price_waterfall.csv direction = unknown
e2e_lane_route.csv direction = IN / OUT

Expected chart generation still works.

Test 5: E2E full price chart generated from e2e_lane_route_csv

Given temporary CSVs.

When:

chart_scope = e2e_primary
chart_mode = full_price
e2e_lane_route_csv is provided

Expected:

PNG generated
file size > 0
Test 6: E2E delta-only chart generated from e2e_lane_route_csv

Same input.

When:

chart_mode = delta_only

Expected:

PNG generated
purchase_cost_per_lot is not stacked
Test 7: fallback still works without e2e_lane_route_csv

Existing Phase 2B+5 chart tests must continue to pass.

17. Validation Commands

Recommended commands:

PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py
PYTHONPATH=. pytest -q tests/reporting_test_price_propagation_chart.py
PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_exporter.py

If a new chart input test file is added:

PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_chart_input.py

Combined command:

PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py tests/evaluate_test_money_evaluator_node_price_formation.py tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py tests/reporting_test_price_propagation_chart.py tests/reporting_test_e2e_lane_route_exporter.py
18. Example Manual Command

After e2e_lane_route.csv exists:

set PYTHONPATH=.

python -c "from pysi.reporting.price_propagation_chart import generate_price_waterfall_stacked_bar as g; print(g('data/node_price_waterfall.csv','outputs/reporting_mvp/price_propagation', product='IPHONE_NM_2028_BASE', leaf_node='CS_US_MAINSTREAM', e2e_lane_route_csv='data/e2e_lane_route.csv', price_propagation_trace_csv='data/price_propagation_trace.csv', chart_mode='full_price', chart_scope='e2e_primary'))"

Delta-only:

python -c "from pysi.reporting.price_propagation_chart import generate_price_waterfall_stacked_bar as g; print(g('data/node_price_waterfall.csv','outputs/reporting_mvp/price_propagation', product='IPHONE_NM_2028_BASE', leaf_node='CS_US_MAINSTREAM', e2e_lane_route_csv='data/e2e_lane_route.csv', price_propagation_trace_csv='data/price_propagation_trace.csv', chart_mode='delta_only', chart_scope='e2e_primary'))"
19. Acceptance Criteria

Phase 2B+5b is accepted when:

generate_price_waterfall_stacked_bar accepts e2e_lane_route_csv.
Chart ordering uses e2e_lane_route.csv when provided.
X-axis follows sequence_no from e2e_lane_route.csv.
Nodes not in selected route are excluded.
Waterfall rows with direction = unknown do not break E2E chart generation.
Existing fallback behavior without e2e_lane_route_csv still works.
E2E full_price chart can be generated.
E2E delta_only chart can be generated.
Y-axis remains Price / Cost per lot.
Existing Phase 2B+1 tests pass.
Existing Phase 2B+2 tests pass.
Existing Phase 2B+3 tests pass.
Existing Phase 2B+4 / 2B+4a / 2B+5 tests pass.
Existing Phase 2B+5a route exporter tests pass.
No money evaluation logic is changed.
No planner behavior is changed.
No GUI behavior is changed.
No committed master CSV fixtures are changed.
20. Documentation Note

Add implementation note:

docs/notes/mosd_phase2b5b_e2e_lane_route_chart_input_260503.md

Suggested contents:

# MOSD Phase 2B+5b E2E Lane Route CSV Chart Input

## Purpose

Use e2e_lane_route.csv as the route-order input for E2E Price & Cost Structure charts.

## Background

Phase 2B+5a exports E2E lane route ordering from product-specific PlanNode trees.

Phase 2B+5b connects that route file to the chart generator.

## Implemented behavior

- Add e2e_lane_route_csv chart argument.
- Load and filter e2e_lane_route.csv by product and leaf node.
- Use sequence_no for X-axis ordering.
- Filter node_price_waterfall rows to route nodes.
- Preserve fallback behavior when e2e_lane_route_csv is absent.
- Avoid over-filtering when node_price_waterfall direction is unknown.

## Not included

- Runtime env generation of e2e_lane_route.csv
- GUI integration
- Management Cockpit integration
- Price recalculation
- Money evaluation changes

## Testing

List test commands and results.
21. Future Phase 2B+5c

After Phase 2B+5b, define:

Phase 2B+5c: Runtime Env E2E Lane Route Export Command

Purpose:

provide a practical command or hook to generate data/e2e_lane_route.csv
use actual env.prod_tree_dict_IN/OT
avoid manual Python object handling by the user

Possible outputs:

data/e2e_lane_route.csv

Future manual usage could become:

Run Full Plan
→ export_e2e_lane_route_from_current_env(...)
→ generate E2E chart using e2e_lane_route.csv
22. Summary

Phase 2B+5b connects the E2E lane route export to the chart generator.

The key change is:

Before:
  chart order guessed from price_propagation_trace.csv

After:
  chart order follows e2e_lane_route.csv generated from product-specific PlanNode trees

This moves the E2E Price & Cost Structure chart closer to WOM's true internal model:

prod_tree_dict_IN[product]
→ supply_point
→ prod_tree_dict_OT[product]
→ selected market leaf