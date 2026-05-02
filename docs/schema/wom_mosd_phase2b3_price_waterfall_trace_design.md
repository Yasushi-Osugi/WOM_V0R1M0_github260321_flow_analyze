# WOM MOSD Phase 2B+3 Price Waterfall and Propagation Trace Export Design

## 1. Purpose

Phase 2B+3 defines the export design for price waterfall and price propagation trace data in WOM money evaluation.

Phase 2B+1 implemented purchase cost propagation:

```text
parent.ship_price_per_lot
→ child.purchase_cost_per_lot

Phase 2B+2 implemented node price formation:

purchase_cost_per_lot
+ cost components
+ target_profit_per_lot
= ship_price_per_lot

Phase 2B+3 exports these results into two CSV files:

data/node_price_waterfall.csv
data/price_propagation_trace.csv

These files will become the foundation for Phase 2B+4 stacked bar chart visualization and later Phase 2C Management KPI integration.

2. Background

After Phase 2B+2, WOM can calculate or preserve ship_price_per_lot at each product × node level.

However, the current runtime output is still mainly node-level money evaluation.

To verify the End-to-End price chain, WOM needs explicit export files that show:

How each node price is formed.
How parent node ship price is propagated to child node purchase cost.
Which node adds what cost component.
Where margin, tax, logistics, fixed cost, or other cost buildup occurs.
Which price was explicit and which price was calculated.

This phase does not draw graphs yet.
It prepares clean data for graph generation.

3. Scope
In scope
Export node_price_waterfall.csv.
Export price_propagation_trace.csv.
Use existing Phase 2B+2 node money rows / unit price records.
Preserve existing node_money_eval.csv behavior.
Add a small exporter helper if needed.
Add focused tests for exported rows and columns.
Add a short implementation note under docs/notes.
Not in scope
GUI graph display.
Matplotlib / Plotly chart generation.
Management Cockpit integration.
Issue Engine integration.
Bidirectional downward target costing.
Full inventory B/S to P/L bridge.
Planner behavior changes.
MOSD adapter rewrite.
Fixture master CSV overwrite.
4. Design Principle

Phase 2B+3 is an export phase.

It must not change the calculation meaning already established in Phase 2B+1 and Phase 2B+2.

The intended sequence is:

money_evaluator.py
  → env.node_money_rows
  → node_money_eval.csv
  → node_price_waterfall.csv
  → price_propagation_trace.csv

If possible, export should reuse existing evaluated results instead of recalculating prices independently.

5. Output File 1: node_price_waterfall.csv
5.1 Purpose

node_price_waterfall.csv explains how each node-level ship_price_per_lot is formed.

It is a per-product, per-node, per-direction cost component table.

This file is intended for:

checking price formation logic
creating stacked bar charts
explaining cost buildup
preparing Management Cockpit narratives
5.2 Output path
data/node_price_waterfall.csv

If the current exporter writes to another runtime output folder, follow the existing repository convention, but keep this filename.

5.3 Grain

One row per:

product × node

If inbound / outbound direction can be determined safely, use:

product × direction × sequence_no × node
5.4 Recommended columns
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
fixed_cost_per_week
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
5.5 Column meanings
Column	Meaning
product	Product ID used by WOM
product_name	Display product name if available
direction	inbound / outbound / unknown
sequence_no	Node order along product tree if available
node_name	WOM node name
node_character	MOM / DAD / CS / supply_point / etc.
price_formation_mode	explicit_ship_price / calculated_from_cost_components / fallback_zero
purchase_cost_per_lot	Cost acquired from parent node or explicit master
value_added_cost_per_lot	Node-specific value added cost
variable_cost_per_lot	Variable operating cost per lot
fixed_cost_per_week	Weekly fixed cost before allocation
fixed_cost_per_lot	Allocated fixed cost per lot
logistics_cost_per_lot	Transport or logistics cost per lot
inventory_handling_cost_per_lot	Shipment / release handling cost per lot
tax_rate	Tax or tariff rate
tax_tariff_cost_per_lot	Tax / tariff amount per lot
target_profit_per_lot	Target profit added at node
ship_price_per_lot	Outbound node price
inventory_unit_value_per_lot	Inventory valuation unit price, not part of price formation
revenue	Revenue amount calculated by evaluator
purchase_amount	Purchase amount / COGS-like amount calculated by evaluator
variable_cost	Total variable cost amount
fixed_cost	Total fixed cost amount
tax_cost	Total tax cost amount if available
profit	Node-level profit
ending_inventory_value	Ending inventory value
inventory_value	Existing inventory value output
remarks	Optional notes / fallback explanation
5.6 Accounting rule

inventory_unit_value_per_lot must be exported for reference, but must not be included as a direct additive component of ship_price_per_lot.

The price formation equation remains:

ship_price_per_lot
=
purchase_cost_per_lot
+ value_added_cost_per_lot
+ variable_cost_per_lot
+ fixed_cost_per_lot
+ logistics_cost_per_lot
+ inventory_handling_cost_per_lot
+ tax_tariff_cost_per_lot
+ target_profit_per_lot

Only when price_formation_mode == calculated_from_cost_components.

If price_formation_mode == explicit_ship_price, the explicit ship price remains authoritative.

6. Output File 2: price_propagation_trace.csv
6.1 Purpose

price_propagation_trace.csv explains how prices move across product tree edges.

It shows:

parent.ship_price_per_lot
→ child.purchase_cost_per_lot

This file is intended for:

checking Phase 2B+1 propagation behavior
validating End-to-End price chain continuity
detecting gaps between parent ship price and child purchase cost
preparing future price propagation graph display
6.2 Output path
data/price_propagation_trace.csv
6.3 Grain

One row per:

product × product_tree_edge

Where an edge is:

parent_node → child_node
6.4 Recommended columns
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
6.5 Column meanings
Column	Meaning
product	Product ID
product_name	Display product name if available
direction	inbound / outbound / unknown
sequence_no	Edge order if available
from_node	Parent node
from_node_character	Parent node character
to_node	Child node
to_node_character	Child node character
parent_ship_price_per_lot	Parent node ship price
child_purchase_cost_per_lot	Child node purchase cost after propagation
child_ship_price_per_lot	Child node outbound price
propagated_purchase_cost_per_lot	Value propagated from parent if used
purchase_cost_source	explicit / propagated_from_parent_ship_price / fallback_zero
delta_parent_ship_to_child_purchase	child_purchase_cost_per_lot - parent_ship_price_per_lot
delta_child_purchase_to_child_ship	child_ship_price_per_lot - child_purchase_cost_per_lot
child_price_formation_mode	explicit_ship_price / calculated_from_cost_components / fallback_zero
edge_leadtime	Edge lead time if available
edge_lot_size	Edge lot size if available
edge_transport_mode	Transport mode if available
remarks	Optional notes
6.6 Interpretation

A normal propagated edge should show:

delta_parent_ship_to_child_purchase == 0

when child purchase cost is derived directly from parent ship price.

If the child has explicit purchase cost, the delta may be non-zero and should be explained by:

purchase_cost_source == explicit

The value:

delta_child_purchase_to_child_ship

shows how much value / cost / profit was added inside the child node.

7. Direction and Sequence Handling
7.1 Direction

If the current product tree source can identify inbound vs outbound:

rows from product_tree_inbound.csv should use direction = inbound
rows from product_tree_outbound.csv should use direction = outbound

If direction cannot be determined safely:

direction = unknown
7.2 Sequence

For chart preparation, sequence order is useful.

Preferred approach:

Use product_tree traversal order if available.
Otherwise use source file row order.
Otherwise use stable sorted order.

The implementation should not fail if sequence cannot be perfectly determined.

Fallback:

sequence_no = 0, 1, 2, ...
8. Data Source

Preferred data source:

env.node_money_rows

or the internal evaluated records used to generate node_money_eval.csv.

For product tree edge trace, the exporter may also inspect:

data/product_tree_inbound.csv
data/product_tree_outbound.csv

or the loaded equivalent in env if available.

The exporter should not recalculate price formation independently.

It should reuse evaluated values:

purchase_cost_per_lot
ship_price_per_lot
price_formation_mode
fixed_cost_per_lot
tax_tariff_cost_per_lot
target_profit_per_lot
9. Suggested Implementation Location

Preferred options:

Option A: Extend existing money output exporter
pysi/evaluate/money_output_exporter.py

Add:

export_node_price_waterfall(...)
export_price_propagation_trace(...)
Option B: Add a small new exporter module
pysi/evaluate/price_trace_exporter.py

This is acceptable if it keeps responsibilities clearer.

Option C: Minimal addition inside money_evaluator.py

Only use this if current exporter structure makes it difficult to add a separate function.

Preferred order:

Option A > Option B > Option C
10. Runtime Integration

The export should be triggered from the same reporting path that currently writes:

node_money_eval.csv
product_money_summary.csv
kpi_summary.csv

The new files should be written at the same time as node money evaluation results, if safe.

The implementation must not require GUI interaction.

11. Tests

Add focused tests.

Suggested test file:

tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py
Test 1: node_price_waterfall columns exist

Given sample evaluated node money rows.

Expected:

node_price_waterfall.csv

contains required columns:

product
node_name
purchase_cost_per_lot
ship_price_per_lot
fixed_cost_per_lot
target_profit_per_lot
price_formation_mode
Test 2: node_price_waterfall preserves inventory separation

Given:

inventory_unit_value_per_lot = 9999
ship_price_per_lot = 850

Expected:

inventory_unit_value_per_lot is exported
ship_price_per_lot does not change
Test 3: price_propagation_trace shows parent-child price movement

Given:

parent.ship_price_per_lot = 700
child.purchase_cost_per_lot = 700
child.ship_price_per_lot = 850

Expected:

delta_parent_ship_to_child_purchase == 0
delta_child_purchase_to_child_ship == 150
Test 4: explicit child purchase cost is visible

Given:

parent.ship_price_per_lot = 700
child.purchase_cost_per_lot = 650

Expected:

purchase_cost_source == explicit
delta_parent_ship_to_child_purchase == -50
Test 5: existing Phase 2B+1 and Phase 2B+2 tests still pass

Existing tests:

tests/evaluate_test_money_evaluator_purchase_cost_propagation.py
tests/evaluate_test_money_evaluator_node_price_formation.py

must continue to pass.

12. Acceptance Criteria

Phase 2B+3 is accepted when:

node_price_waterfall.csv is exported.
price_propagation_trace.csv is exported.
Existing node_money_eval.csv behavior is preserved.
Existing Phase 2B+1 tests pass.
Existing Phase 2B+2 tests pass.
New export tests pass.
No GUI changes are introduced.
No planner changes are introduced.
No fixture master CSV files are overwritten.
Exported CSV columns are stable enough for Phase 2B+4 chart generation.
13. Future Phase 2B+4

Phase 2B+4 will use these CSVs to generate price propagation graphs.

Expected graph types:

13.1 Node price waterfall stacked bar

Source:

data/node_price_waterfall.csv

Chart concept:

x-axis: node sequence
y-axis: amount per lot
stack: purchase cost, value added cost, variable cost, fixed cost, logistics cost, tax, target profit
line or label: ship_price_per_lot
13.2 Price propagation trace graph

Source:

data/price_propagation_trace.csv

Chart concept:

from_node.ship_price_per_lot
→ to_node.purchase_cost_per_lot
→ to_node.ship_price_per_lot
14. Future Phase 2C

Phase 2C will connect money results to:

ManagementFact
Issue Engine
Management Cockpit

Phase 2B+3 should not implement Phase 2C directly.

However, it should prepare clean intermediate data that can later be used by Phase 2C.

15. Future Bidirectional Price Propagation

Later phases may support both directions:

Material_Price upward2market
material / procurement cost
→ production cost
→ logistics cost
→ channel cost
→ market price
Market_Price downward2material
market required price
→ allowable channel cost
→ allowable logistics cost
→ allowable plant cost
→ allowable material cost

Phase 2B+3 should not implement downward propagation.

It only exports current upward / runtime evaluated price formation and propagation data.

16. Summary

Phase 2B+3 is the bridge between calculation and visualization.

It does not change WOM planning or pricing logic.

It exports the already evaluated price formation and price propagation data into stable CSV files:

node_price_waterfall.csv
price_propagation_trace.csv

These files will allow WOM developers and users to inspect:

where the price is formed
where cost is added
where margin is added
how parent price becomes child purchase cost
whether the E2E price chain is natural

This phase prepares WOM for price propagation stacked bar chart visualization in Phase 2B+4.