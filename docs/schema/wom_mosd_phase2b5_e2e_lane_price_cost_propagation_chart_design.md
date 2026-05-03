# WOM MOSD Phase 2B+5 E2E Lane Price & Cost Propagation Chart Design

## 1. Purpose

Phase 2B+5 defines the design for E2E lane-level Price & Cost Propagation Chart.

Phase 2B+4a introduced lane chart readability improvements for a selected:

```text
Product × Leaf Node

However, the current lane chart mainly focuses on the outbound side:

supply_point
→ DAD / WS / RT
→ CS / market leaf

Phase 2B+5 extends the lane concept to the End-to-End supply chain by connecting outbound and inbound lanes through:

supply_point

The goal is to visualize:

Product × Market Leaf Node
→ E2E Supply Chain Lane
→ Price & Cost Structure per lot by node

including both:

Inbound side:
  upstream supply / production / assembly path
  → supply_point

Outbound side:
  supply_point
  → distribution / channel / market leaf

This enables WOM to show how a product's cost and price structure is formed across the E2E supply chain.

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
  generate price waterfall stacked bar PNG

Phase 2B+4a:
  improve chart ordering
  add leaf_node route chart
  add delta_only chart
  add all-zero skip handling

Phase 2B+5 extends this from an outbound lane chart to an E2E lane chart.

3. Core Concept

The central concept is:

Product × Leaf Node
→ a Lane on E2E Supply Chain
→ Price & Cost Propagation

For example:

Product   = IPHONE_NM_2028_BASE
Leaf Node = CS_US_MAINSTREAM

The E2E lane should show:

Inbound upstream node(s)
→ MOM / PAD / final assembly node
→ supply_point
→ DAD / WS / RT
→ CS_US_MAINSTREAM

The chart should allow users to inspect:

parent node ship_price_per_lot
→ child node purchase_cost_per_lot
→ child node-added cost
→ child node ship_price_per_lot

across both inbound and outbound parts of the supply chain.

4. Why This Matters

The outbound-only chart explains how price is formed from supply_point to market.

The E2E lane chart explains how the market-facing cost structure is connected back to upstream supply and production.

This view enables users to answer questions such as:

Where does the market price structure originate?
Which upstream node contributes most to cost?
Which node adds fixed cost, logistics cost, tax, or target profit?
How does upstream ship price become downstream purchase cost?
Which supply chain lane is expensive?
Which market leaf is exposed to which upstream cost structure?
How does one product's E2E lane compare with another?

This is a key step toward WOM modeling with both:

PSI quantity flow
+
Price & Cost money flow

on the same E2E supply chain lane.

5. Scope
In scope
Extend lane chart concept from outbound-only to E2E lane.
Use price_propagation_trace.csv to identify inbound and outbound edges.
Use node_price_waterfall.csv to retrieve node-level price and cost components.
Connect inbound and outbound through supply_point.
Support selected:
product
market leaf node
Generate E2E lane full_price chart.
Generate E2E lane delta_only chart.
Preserve existing Phase 2B+4a outbound lane chart behavior.
Add tests for E2E route construction and chart generation.
Add implementation note under docs/notes.
Not in scope
Money evaluation logic changes.
Price formation logic changes.
Purchase cost propagation logic changes.
GUI integration.
Management Cockpit integration.
Interactive dashboard.
Bidirectional target costing.
Market-price downward allowable-cost propagation.
Inventory B/S to P/L bridge.
Master CSV fixture modifications.
Recalculation of ship_price_per_lot.
Automatic lane optimization.
Multi-scenario comparison.
6. Required Input Files

Phase 2B+5 uses the existing Phase 2B+3 output files:

data/node_price_waterfall.csv
data/price_propagation_trace.csv
6.1 node_price_waterfall.csv

This file provides node-level price and cost structure.

Expected columns include:

product
product_name
direction
sequence_no
node_name
node_character
price_formation_mode

purchase_cost_per_lot
value_added_cost_per_lot
variable_cost_per_lot
fixed_cost_per_lot
logistics_cost_per_lot
inventory_handling_cost_per_lot
tax_rate
tax_tariff_cost_per_lot
target_profit_per_lot
ship_price_per_lot
inventory_unit_value_per_lot

revenue
purchase_amount
variable_cost
fixed_cost
tax_cost
profit
ending_inventory_value
inventory_value
remarks

Some optional columns may be missing or blank.

The chart generator must treat missing optional component columns as zero.

6.2 price_propagation_trace.csv

This file provides edge-level propagation relationships.

Expected columns include:

product
product_name
direction
sequence_no

from_node
from_node_character
to_node
to_node_character

parent_ship_price_per_lot
child_purchase_cost_per_lot
child_ship_price_per_lot

propagated_purchase_cost_per_lot
purchase_cost_source

delta_parent_ship_to_child_purchase
delta_child_purchase_to_child_ship

child_price_formation_mode

edge_leadtime
edge_lot_size
edge_transport_mode

remarks

The direction column is important:

inbound
outbound
unknown
7. E2E Lane Definition

An E2E lane is a connected node sequence consisting of:

Inbound route
+
supply_point
+
Outbound route to selected market leaf
7.1 Outbound route

For selected:

product
leaf_node

find an outbound path ending at the selected leaf node.

Example:

supply_point
→ DAD_FAS_AMER
→ WS_NA
→ RT_US_CARRIER
→ CS_US_MAINSTREAM
7.2 Inbound route

Find inbound path(s) that lead to:

supply_point

Example:

PAD_final_assy_ASIA
→ MOM_final_assy_ASIA
→ supply_point

or:

MOM_final_assy_EURO
→ supply_point

depending on available trace data.

7.3 E2E stitched lane

The simplest E2E lane is:

selected inbound path
→ supply_point
→ selected outbound path

Example:

PAD_final_assy_ASIA
→ MOM_final_assy_ASIA
→ supply_point
→ DAD_FAS_AMER
→ WS_NA
→ RT_US_CARRIER
→ CS_US_MAINSTREAM
8. E2E Lane Modes

Phase 2B+5 should support at least one of the following modes.

8.1 e2e_primary mode

Select one inbound path and stitch it with the selected outbound path.

This is the recommended first implementation.

Behavior:

chart_scope = e2e_primary
find outbound route to selected leaf_node
find one inbound route to supply_point
join the two through supply_point
generate one E2E lane chart

Inbound path selection priority:

If user provides inbound_leaf_node, use route from that inbound node to supply_point.
If not provided, choose the first stable inbound route ending at supply_point.
If multiple inbound routes exist, use sequence order or stable sorted order.
Do not fail only because multiple inbound routes exist.
8.2 e2e_fanin mode

Include all inbound branches that feed into supply_point, plus the selected outbound route.

Behavior:

chart_scope = e2e_fanin

Example:

PAD_final_assy_ASIA ─┐
MOM_final_assy_ASIA ─┼→ supply_point → DAD_FAS_AMER → WS_NA → RT_US_CARRIER → CS_US_MAINSTREAM
MOM_final_assy_EURO ─┘

This is more complete but visually more complex.

This mode may be left for a later phase if it is not simple.

8.3 outbound_only mode

Preserve current Phase 2B+4a behavior.

Behavior:

chart_scope = outbound_only

This is the current route chart:

supply_point
→ DAD / WS / RT
→ market leaf
9. Recommended Function Interface

Extend the existing chart generator if safe.

Current base function:

def generate_price_waterfall_stacked_bar(
    node_price_waterfall_csv: str,
    output_dir: str,
    *,
    product: str | None = None,
    direction: str | None = None,
    leaf_node: str | None = None,
    price_propagation_trace_csv: str | None = None,
    chart_mode: str = "full_price",
    skip_all_zero: bool = True,
) -> list[str]:
    ...

Recommended Phase 2B+5 extension:

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
9.1 chart_mode

Supported values:

full_price
delta_only
9.2 chart_scope

Supported values:

outbound_only
e2e_primary

Optional future value:

e2e_fanin

If unsupported scope is provided, raise:

ValueError

with a clear message.

9.3 inbound_leaf_node

Optional node name used to select a specific inbound route.

Example:

PAD_final_assy_ASIA
MOM_final_assy_ASIA
MOM_final_assy_EURO

If omitted, choose a stable primary inbound route.

9.4 supply_point_node

Default:

supply_point

This is the stitch point between inbound and outbound routes.

10. Route Construction Logic
10.1 Build outbound route

Input:

product
leaf_node
direction = outbound

Find route ending at leaf_node.

Example output:

supply_point
DAD_FAS_AMER
WS_NA
RT_US_CARRIER
CS_US_MAINSTREAM
10.2 Build inbound route

Input:

product
supply_point_node
direction = inbound

Find route ending at supply_point.

Example output:

PAD_final_assy_ASIA
MOM_final_assy_ASIA
supply_point

If inbound_leaf_node is provided, use route:

inbound_leaf_node
→ ...
→ supply_point
10.3 Stitch route

If inbound route ends with supply_point and outbound route starts with supply_point, avoid duplicate supply_point.

Example:

inbound_route:
PAD_final_assy_ASIA
MOM_final_assy_ASIA
supply_point

outbound_route:
supply_point
DAD_FAS_AMER
WS_NA
RT_US_CARRIER
CS_US_MAINSTREAM

stitched_route:
PAD_final_assy_ASIA
MOM_final_assy_ASIA
supply_point
DAD_FAS_AMER
WS_NA
RT_US_CARRIER
CS_US_MAINSTREAM
10.4 Fallback behavior

If inbound route cannot be found:

fall back to outbound_only route
optionally print a warning
do not crash unless no outbound route exists

If outbound route cannot be found:

fall back to existing product-filtered chart
optionally print a warning
do not crash unless no rows exist
11. Display Order

For E2E lane chart, node order must be:

upstream inbound
→ supply_point
→ downstream outbound
→ market leaf

This order is important because it supports the WOM narrative:

upstream cost structure
→ supply point transfer price
→ downstream channel cost structure
→ market-facing price

The route must not be displayed leaf-to-root unless explicitly requested.

12. Chart Title and Y-axis Label

Phase 2B+5 should improve labels.

12.1 Full price E2E chart title

Recommended title:

E2E Lane Price & Cost Structure per Lot - <product> → <leaf_node>

Example:

E2E Lane Price & Cost Structure per Lot - IPHONE_NM_2028_BASE → CS_US_MAINSTREAM
12.2 Delta-only E2E chart title

Recommended title:

E2E Lane Added Cost Structure per Lot - <product> → <leaf_node> [delta only]
12.3 Y-axis label

Replace:

Amount per lot

with:

Price / Cost per lot

This chart is not:

Ship_Price × Lot_QTY

It visualizes per-lot price and cost structure.

13. Chart Components
13.1 full_price mode

Stack components:

purchase_cost_per_lot
value_added_cost_per_lot
variable_cost_per_lot
fixed_cost_per_lot
logistics_cost_per_lot
inventory_handling_cost_per_lot
tax_tariff_cost_per_lot
target_profit_per_lot
13.2 delta_only mode

Stack components:

value_added_cost_per_lot
variable_cost_per_lot
fixed_cost_per_lot
logistics_cost_per_lot
inventory_handling_cost_per_lot
tax_tariff_cost_per_lot
target_profit_per_lot
13.3 Always excluded

Do not stack:

inventory_unit_value_per_lot

It is a B/S inventory valuation reference, not a price formation component.

14. E2E Price Propagation Interpretation

The E2E lane chart should support the following interpretation.

For each adjacent pair:

node A
→ node B

Inspect:

node A ship_price_per_lot
≈ node B purchase_cost_per_lot

For each node:

purchase_cost_per_lot
+ node-added costs
+ target_profit_per_lot
= ship_price_per_lot

For the full E2E lane:

upstream cost buildup
→ supply_point price
→ downstream channel and market cost buildup
→ market-facing ship_price_per_lot

This is the visual form of WOM two-phase costing.

15. Output File Naming
15.1 outbound_only existing chart

Preserve existing naming as much as possible:

<product>_price_waterfall_route_stacked_bar.png
<product>_price_waterfall_route_delta_only.png
15.2 e2e_primary full price chart

Recommended:

<product>_<leaf_node>_e2e_lane_price_cost_structure.png
15.3 e2e_primary delta-only chart

Recommended:

<product>_<leaf_node>_e2e_lane_added_cost_structure_delta_only.png
15.4 If inbound_leaf_node is specified

Recommended:

<product>_<inbound_leaf_node>_to_<leaf_node>_e2e_lane_price_cost_structure.png

Sanitize all file names.

16. Output Folder

Use existing folder:

outputs/reporting_mvp/price_propagation/

Do not change existing Phase 2B+4 / 2B+4a output folder behavior.

17. Suggested Implementation Location

Modify existing module:

pysi/reporting/price_propagation_chart.py

Add helpers such as:

def find_route_between_nodes(
    trace_rows: list[dict],
    product: str,
    start_node: str,
    end_node: str,
    direction: str | None = None,
) -> list[str]:
    ...

def find_primary_inbound_route_to_supply_point(
    trace_rows: list[dict],
    product: str,
    supply_point_node: str = "supply_point",
    inbound_leaf_node: str | None = None,
) -> list[str]:
    ...

def build_e2e_lane_route(
    trace_rows: list[dict],
    product: str,
    leaf_node: str,
    supply_point_node: str = "supply_point",
    inbound_leaf_node: str | None = None,
) -> list[str]:
    ...

def stitch_routes(
    inbound_route: list[str],
    outbound_route: list[str],
    supply_point_node: str = "supply_point",
) -> list[str]:
    ...

Keep implementation small.

Do not touch money evaluator unless absolutely necessary.

18. Tests

Add focused tests in:

tests/reporting_test_price_propagation_chart.py

or new file:

tests/reporting_test_e2e_lane_price_propagation_chart.py
Test 1: stitch inbound and outbound routes

Given:

inbound_route  = ["MOM", "supply_point"]
outbound_route = ["supply_point", "DAD", "CS"]

Expected:

["MOM", "supply_point", "DAD", "CS"]

without duplicate supply_point.

Test 2: build E2E lane route

Given trace:

MOM → supply_point        direction=inbound
supply_point → DAD        direction=outbound
DAD → CS                  direction=outbound

When:

product = PRODUCT_A
leaf_node = CS

Expected:

MOM
supply_point
DAD
CS
Test 3: E2E chart generation

Given temporary node_price_waterfall.csv and price_propagation_trace.csv.

When:

chart_scope = e2e_primary
chart_mode = full_price
leaf_node = CS

Expected:

PNG generated
file size > 0
Test 4: E2E delta-only chart generation

Same input.

When:

chart_scope = e2e_primary
chart_mode = delta_only

Expected:

PNG generated
purchase_cost_per_lot not included in stacked components
Test 5: fallback to outbound_only if inbound route missing

Given only outbound trace.

When:

chart_scope = e2e_primary

Expected:

chart still generated using outbound route
Test 6: existing chart tests still pass

Existing Phase 2B+4 / 2B+4a tests must continue to pass.

19. Validation Commands

Recommended test commands:

PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py
PYTHONPATH=. pytest -q tests/reporting_test_price_propagation_chart.py

If new test file is added:

PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_price_propagation_chart.py

Combined:

PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py tests/evaluate_test_money_evaluator_node_price_formation.py tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py tests/reporting_test_price_propagation_chart.py
20. Example Manual Commands
20.1 E2E full price chart
set PYTHONPATH=.

python -c "from pysi.reporting.price_propagation_chart import generate_price_waterfall_stacked_bar as g; print(g('data/node_price_waterfall.csv','outputs/reporting_mvp/price_propagation', product='IPHONE_NM_2028_BASE', leaf_node='CS_US_MAINSTREAM', price_propagation_trace_csv='data/price_propagation_trace.csv', chart_mode='full_price', chart_scope='e2e_primary'))"
20.2 E2E delta-only chart
python -c "from pysi.reporting.price_propagation_chart import generate_price_waterfall_stacked_bar as g; print(g('data/node_price_waterfall.csv','outputs/reporting_mvp/price_propagation', product='IPHONE_NM_2028_BASE', leaf_node='CS_US_MAINSTREAM', price_propagation_trace_csv='data/price_propagation_trace.csv', chart_mode='delta_only', chart_scope='e2e_primary'))"
20.3 E2E with specific inbound start node
python -c "from pysi.reporting.price_propagation_chart import generate_price_waterfall_stacked_bar as g; print(g('data/node_price_waterfall.csv','outputs/reporting_mvp/price_propagation', product='IPHONE_NM_2028_BASE', leaf_node='CS_US_MAINSTREAM', inbound_leaf_node='MOM_final_assy_ASIA', price_propagation_trace_csv='data/price_propagation_trace.csv', chart_mode='full_price', chart_scope='e2e_primary'))"
21. Acceptance Criteria

Phase 2B+5 is accepted when:

Existing outbound_only chart behavior still works.
E2E primary lane route can be constructed.
E2E route is ordered upstream → supply_point → downstream market leaf.
E2E full_price chart can be generated.
E2E delta_only chart can be generated.
supply_point is not duplicated when stitching inbound and outbound routes.
If inbound route is unavailable, chart generation falls back safely.
Y-axis is labeled Price / Cost per lot.
Chart title clearly says E2E lane price / cost structure.
Existing Phase 2B+1 tests pass.
Existing Phase 2B+2 tests pass.
Existing Phase 2B+3 tests pass.
Existing Phase 2B+4 / 2B+4a tests pass.
No money evaluation logic is changed.
No GUI behavior is changed.
No planner behavior is changed.
No committed master CSV fixtures are changed.
22. Documentation Note

Add implementation note:

docs/notes/mosd_phase2b5_e2e_lane_price_cost_propagation_chart_260503.md

Suggested contents:

# MOSD Phase 2B+5 E2E Lane Price & Cost Propagation Chart

## Purpose

Generate E2E lane-level Price & Cost Structure charts from node_price_waterfall.csv and price_propagation_trace.csv.

## Background

Phase 2B+4a supports outbound lane chart generation using Product × Leaf Node.

Phase 2B+5 extends this to include inbound routes stitched through supply_point.

## Implemented behavior

- Build outbound route to selected market leaf.
- Build inbound route to supply_point.
- Stitch inbound and outbound routes into an E2E lane.
- Generate full_price E2E lane chart.
- Generate delta_only E2E lane chart.
- Label Y-axis as Price / Cost per lot.
- Preserve existing outbound-only behavior.

## Not included

- GUI integration
- Management Cockpit integration
- Price recalculation
- Bidirectional target costing
- Downward allowable cost propagation
- Inventory B/S to P/L bridge

## Testing

List test commands and results.
23. Future Phase 2B+5a / 2B+6

Possible future improvements:

23.1 Fan-in E2E lane chart

Support:

chart_scope = e2e_fanin

to show all inbound branches feeding supply_point.

23.2 Connector annotations

Show:

parent ship price
→ child purchase cost

as visual annotations between adjacent nodes.

23.3 Lane selector

Add simple report command or GUI selector:

Product
Leaf Node
Inbound Source
Chart Mode
23.4 Management Cockpit integration

Expose E2E lane chart from Management Cockpit.

24. Summary

Phase 2B+5 extends WOM price propagation visualization from outbound lane to E2E lane.

The intended view is:

Product × Market Leaf Node
→ Inbound route
→ supply_point
→ Outbound route
→ Market leaf
→ Price & Cost Structure per lot

This lets WOM users inspect the almost full cost structure of a product serving a specific market lane.

The chart is still based on evaluated runtime outputs.

It does not recalculate price.

It visualizes the existing price and cost propagation results in a more complete E2E supply chain context.