# WOM MOSD Phase 2B+4a Lane Chart Verification Design

## 1. Purpose

This document defines the verification procedure for Phase 2B+4a lane-based price propagation chart.

The goal is to confirm that WOM can visualize:

```text
Product × Leaf Node
→ Supply Chain Lane
→ Price & Cost Structure per lot by node

using the generated runtime CSV files:

data/node_price_waterfall.csv
data/price_propagation_trace.csv

This verification focuses on a real existing product and an existing leaf node, for example:

product   = IPHONE_NM_2028_BASE
leaf_node = CS_US_MAINSTREAM

The chart should help users understand:

upstream parent ship_price_per_lot
→ downstream child purchase_cost_per_lot
→ child node-added cost
→ child ship_price_per_lot
2. Background

Phase 2B+1 implemented:

parent.ship_price_per_lot
→ child.purchase_cost_per_lot

Phase 2B+2 implemented:

purchase_cost_per_lot
+ node cost components
+ target_profit_per_lot
= ship_price_per_lot

Phase 2B+3 exported:

data/node_price_waterfall.csv
data/price_propagation_trace.csv

Phase 2B+4 generated static stacked bar charts.

Phase 2B+4a improved:

trace-based ordering
leaf_node route filtering
delta_only chart mode
all-zero chart skipping

This document verifies that these capabilities work on actual WOM runtime outputs.

3. Verification Concept

The main view is:

Product × Leaf Node → a Lane of Supply Chain

For example:

IPHONE_NM_2028_BASE × CS_US_MAINSTREAM

should generate a chart for the lane ending at:

CS_US_MAINSTREAM

A successful lane chart should avoid unnecessary nodes and show only the relevant route.

Example conceptual route:

supply_point
→ DAD_FAS_AMER
→ WS_NA
→ RT_US_CARRIER or RT_US_ONLINE
→ CS_US_MAINSTREAM

The actual route should be inferred from:

data/price_propagation_trace.csv
4. Required Input Files

Before running chart verification, confirm that the following files exist:

data/node_price_waterfall.csv
data/price_propagation_trace.csv

Command:

dir data\node_price_waterfall.csv
dir data\price_propagation_trace.csv

If these files do not exist, run WOM planning first:

python -m main

Then run full planning / recompute from the WOM GUI so that money outputs and price trace outputs are regenerated.

5. Confirm Available Products

Use the following command to list available products in node_price_waterfall.csv:

python -c "import csv; print(sorted({r['product'] for r in csv.DictReader(open('data/node_price_waterfall.csv', encoding='utf-8'))}))"

Expected example:

['IPHONE_NM_2028_BASE']

or:

['IPHONE_NM_2028_BASE', 'IPHONE_NM_2028_PRO']

For this verification, use:

IPHONE_NM_2028_BASE

because it currently has non-zero price and cost values.

6. Confirm Available Leaf Nodes

Use the following command to list candidate to_node values from price_propagation_trace.csv:

python -c "import csv; print(sorted({r['to_node'] for r in csv.DictReader(open('data/price_propagation_trace.csv', encoding='utf-8'))}))"

Example observed values:

CS_CN_PREMIUM
CS_DE_PREMIUM
CS_IN_ASPIRER
CS_JP_REPLACEMENT
CS_UK_MAINSTREAM
CS_US_MAINSTREAM
CS_US_PREMIUM
DAD_FAS_AMER
DAD_FAS_APAC
DAD_FAS_EURO
MOM_final_assy_ASIA
MOM_final_assy_EURO
PAD_final_assy_ASIA
PAD_final_assy_EURO
RT_CN_ONLINE
RT_DE_ONLINE
RT_IN_ECOM
RT_JP_APPLE
RT_UK_CARRIER
RT_US_CARRIER
RT_US_ONLINE
WS_APAC
WS_EU
WS_NA

For US mainstream lane verification, use:

leaf_node = CS_US_MAINSTREAM

Do not use non-existing node names such as:

CS_US_ECOM

unless they actually appear in the trace file.

7. Full Price Lane Chart Command

Generate a lane-based full price chart:

set PYTHONPATH=.

python -c "from pysi.reporting.price_propagation_chart import generate_price_waterfall_stacked_bar as g; print(g('data/node_price_waterfall.csv','outputs/reporting_mvp/price_propagation', product='IPHONE_NM_2028_BASE', direction='outbound', leaf_node='CS_US_MAINSTREAM', price_propagation_trace_csv='data/price_propagation_trace.csv', chart_mode='full_price'))"

Expected output:

['outputs/reporting_mvp/price_propagation\\IPHONE_NM_2028_BASE_outbound_CS_US_MAINSTREAM_price_waterfall_route_stacked_bar.png']

Actual filename may differ depending on current filename sanitization and implementation.

8. Delta-Only Lane Chart Command

Generate a lane-based delta-only chart:

set PYTHONPATH=.

python -c "from pysi.reporting.price_propagation_chart import generate_price_waterfall_stacked_bar as g; print(g('data/node_price_waterfall.csv','outputs/reporting_mvp/price_propagation', product='IPHONE_NM_2028_BASE', direction='outbound', leaf_node='CS_US_MAINSTREAM', price_propagation_trace_csv='data/price_propagation_trace.csv', chart_mode='delta_only'))"

Expected output:

['outputs/reporting_mvp/price_propagation\\IPHONE_NM_2028_BASE_outbound_CS_US_MAINSTREAM_price_waterfall_delta_only.png']

Actual filename may differ depending on implementation.

9. Output Folder

Generated PNG files should be saved under:

outputs/reporting_mvp/price_propagation/

Command:

dir outputs\reporting_mvp\price_propagation
10. What to Check in the Full Price Lane Chart

The full price lane chart should show:

purchase_cost_per_lot
+ value_added_cost_per_lot
+ variable_cost_per_lot
+ fixed_cost_per_lot
+ logistics_cost_per_lot
+ inventory_handling_cost_per_lot
+ tax_tariff_cost_per_lot
+ target_profit_per_lot

as stacked components.

It should show the full per-lot price structure at each node.

Check the following:

Only nodes on the selected lane are shown.
X-axis follows upstream-to-downstream route order.
purchase_cost_per_lot is visible as the base of each node.
ship_price_per_lot labels are shown.
The relationship between parent ship price and child purchase cost is easier to follow.
No unrelated branch nodes are included.
11. What to Check in the Delta-Only Lane Chart

The delta-only chart should exclude:

purchase_cost_per_lot
inventory_unit_value_per_lot

and show only node-added components:

value_added_cost_per_lot
variable_cost_per_lot
fixed_cost_per_lot
logistics_cost_per_lot
inventory_handling_cost_per_lot
tax_tariff_cost_per_lot
target_profit_per_lot

Check the following:

purchase_cost_per_lot is not stacked.
smaller cost components are easier to see.
node-added cost / profit can be visually compared across the lane.
ship_price_per_lot reference remains understandable.
the chart helps explain where price increases inside the lane.
12. Recommended Axis and Title Interpretation

The current chart may use:

Amount per lot

as Y-axis label.

For WOM interpretation, the intended meaning is:

Price / Cost per lot

or:

Price & Cost Structure per lot

This is not:

Ship_Price × Lot_QTY

The graph is not a total amount graph.

It visualizes per-lot price and cost structure after price propagation.

Preferred future title:

Price & Cost Structure per Lot by Product - IPHONE_NM_2028_BASE

Preferred future Y-axis:

Price / Cost per lot

This wording improvement can be handled in a future Phase 2B+4b request.

13. Data Quality Interpretation

If the chart still looks unnatural, check whether the issue is caused by:

13.1 Master data values

Examples:

purchase_cost_per_lot too large
target_profit_per_lot too large
logistics cost too small
tax cost missing
ship price not aligned with realistic market price

In this case, the chart is working, but the Price & Cost master values need refinement.

13.2 Chart ordering

If unrelated nodes appear in the chart, verify:

leaf_node
direction
product
price_propagation_trace_csv
13.3 All-zero product

If no chart is generated, the selected product may have all-zero price components.

Try:

IPHONE_NM_2028_BASE

rather than a product with no price data.

14. Acceptance Criteria

This verification is accepted when:

node_price_waterfall.csv exists.
price_propagation_trace.csv exists.
available leaf nodes can be listed.
CS_US_MAINSTREAM or another real leaf node can be selected.
full_price lane chart is generated.
delta_only lane chart is generated.
chart contains only the selected supply chain lane nodes.
X-axis node order follows upstream-to-downstream order.
delta_only chart makes node-added components easier to see.
the chart is interpretable as Price / Cost per lot, not total amount.
15. Suggested Follow-up

After verifying lane charts, define Phase 2B+4b for chart wording and usability improvements:

title wording
Y-axis wording
route chart default behavior
parent ship / child purchase visual annotations
lane chart report command simplification
optional helper script or CLI entry point

Possible Phase 2B+4b title:

Phase 2B+4b: Lane Price & Cost Structure Chart Usability Improvement
16. Summary

This verification confirms that WOM can show price propagation results as a lane-level chart.

The intended concept is:

Product × Leaf Node
→ Supply Chain Lane
→ Node-level Price & Cost Structure per lot

This view is important because it removes unrelated nodes and makes the E2E price propagation story easier to understand.

The most important relationship to inspect is:

parent node ship_price_per_lot
→ child node purchase_cost_per_lot
→ child node-added cost
→ child node ship_price_per_lot