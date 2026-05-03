# WOM MOSD Phase 2B+5a PlanNode Tree Based E2E Lane Route Export Design

## 1. Purpose

Phase 2B+5a defines the design for exporting E2E lane route ordering from WOM product-specific PlanNode trees.

Phase 2B+5 introduced an E2E lane price & cost propagation chart using:

```text
data/node_price_waterfall.csv
data/price_propagation_trace.csv

However, the actual WOM model has a stronger source of truth for E2E supply chain route ordering:

prod_tree_dict_IN[product_name]
prod_tree_dict_OT[product_name]

These are product-specific planning layer trees.

The purpose of Phase 2B+5a is to export an explicit E2E lane route file from these PlanNode trees so that price & cost charts can use the correct upstream-to-downstream node ordering.

The main output is:

data/e2e_lane_route.csv

This file will be used by the Phase 2B+5 chart generator to order the X-axis nodes correctly:

inbound upstream
→ supply_point
→ outbound downstream
→ selected market leaf
2. Background

WOM has at least two node worlds.

2.1 Physical / GUI node world

This is used for GUI, NetworkX, map display, and E2E network visualization.

Examples:

self.nodes_outbound
self.nodes_inbound
self.root_node_outbound
self.root_node_inbound
self.G
self.Gdm_structure
self.Gsp
self.pos_E2E

This layer is product-independent and represents physical or visual nodes.

2.2 Product planning node world

This is used for product-specific planning.

Examples:

self.prod_tree_dict_OT[product_name]
self.prod_tree_dict_IN[product_name]

Each product has its own outbound / inbound PlanNode tree.

Planning nodes contain or connect to product-level planning state such as:

psi4demand
psi4supply
leadtime
lot
cost
planning status
2.3 Bridge between two worlds

The physical GUI node and the product-specific PlanNode are connected by node name.

Conceptually:

gui_node.sku_dict[product_name] = plan_node

Therefore, for E2E lane route construction, the route source should be the product-specific PlanNode tree, not the physical GUI node list.

3. Problem Statement

Phase 2B+5 attempted to build E2E lane charts using:

price_propagation_trace.csv

This can work for simple cases, but it is not the most authoritative route source.

Observed issue:

chart_scope = e2e_primary

generated E2E-named chart files, but the visible route still looked like outbound-only:

CS_US_MAINSTREAM
DAD_FAS_AMER
RT_US_CARRIER
WS_NA
supply_point

instead of:

inbound upstream
→ supply_point
→ DAD_FAS_AMER
→ WS_NA
→ RT_US_CARRIER
→ CS_US_MAINSTREAM

This indicates that the chart generator did not receive a reliable E2E route order.

Phase 2B+5a fixes this by exporting E2E route ordering from product-specific PlanNode trees.

4. Design Principle

Phase 2B+5a is a route export phase.

It must not change:

money evaluation logic
price formation logic
purchase cost propagation logic
PSI planning logic
GUI behavior
committed master CSV fixtures

It should only export route ordering information from the already-built product planning trees.

The intended flow is:

WOM runtime
  → prod_tree_dict_IN[product]
  → prod_tree_dict_OT[product]
  → e2e_lane_route.csv
  → price_propagation_chart.py
  → E2E lane chart

The chart generator should consume route order data rather than guessing E2E route order only from price trace rows.

5. Scope
In scope
Export data/e2e_lane_route.csv.
Build route order from prod_tree_dict_IN[product_name].
Build route order from prod_tree_dict_OT[product_name].
Stitch inbound and outbound routes at supply_point.
Support selected product.
Support selected market leaf node.
Support optional inbound source node.
Provide stable upstream-to-downstream sequence numbers.
Add focused tests.
Add implementation note under docs/notes.
Not in scope
Changing price / cost values.
Recalculating ship_price_per_lot.
Recalculating purchase_cost_per_lot.
Changing node_money_eval.csv logic.
GUI integration.
Management Cockpit integration.
Fan-in E2E chart for all inbound branches.
Bidirectional target costing.
Downward allowable cost propagation.
Inventory B/S to P/L bridge.
6. Output File
6.1 Main output
data/e2e_lane_route.csv
6.2 Grain

One row per:

product × lane_id × sequence_no × node

Each row represents one node in an E2E supply chain lane.

6.3 Recommended columns
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
6.4 Column meanings
Column	Meaning
product	Product ID / product_name
lane_id	Stable lane identifier
leaf_node	Market / downstream leaf node
inbound_leaf_node	Optional upstream inbound start node
chart_scope	e2e_primary / outbound_only / future e2e_fanin
sequence_no	E2E display order
segment	inbound / stitch / outbound
direction	IN / OUT
node_name	Node name
node_character	Node character if available
parent_node	Parent node in route order
child_node	Child node in route order
depth	Depth within segment tree
is_supply_point	True if node_name == supply_point
route_role	upstream_source / production / supply_point / distribution / channel / market_leaf / unknown
source_tree	prod_tree_dict_IN / prod_tree_dict_OT
remarks	fallback or diagnostic note
7. E2E Lane Definition

An E2E lane is:

selected inbound path
→ supply_point
→ selected outbound path
7.1 Inbound path

From product-specific inbound planning tree:

prod_tree_dict_IN[product_name]

Example:

PAD_final_assy_ASIA
→ MOM_final_assy_ASIA
→ supply_point
7.2 Outbound path

From product-specific outbound planning tree:

prod_tree_dict_OT[product_name]

Example:

supply_point
→ DAD_FAS_AMER
→ WS_NA
→ RT_US_CARRIER
→ CS_US_MAINSTREAM
7.3 Stitched E2E lane

The final route:

PAD_final_assy_ASIA
→ MOM_final_assy_ASIA
→ supply_point
→ DAD_FAS_AMER
→ WS_NA
→ RT_US_CARRIER
→ CS_US_MAINSTREAM

supply_point should not be duplicated.

8. Route Construction Rules
8.1 Inputs

Required:

product_name
prod_tree_dict_IN
prod_tree_dict_OT

Optional:

leaf_node
inbound_leaf_node
supply_point_node = "supply_point"
8.2 Outbound route to market leaf

If leaf_node is provided:

Traverse prod_tree_dict_OT[product_name].
Find path from outbound root to leaf_node.
Use that path as outbound route.
Ensure route starts at or includes supply_point.

If leaf_node is not provided:

Use stable outbound root-to-leaf path.
Prefer first stable leaf path.
Add remarks that leaf_node was not specified.
8.3 Inbound route to supply point

If inbound_leaf_node is provided:

Traverse prod_tree_dict_IN[product_name].
Find path from inbound_leaf_node to supply_point.

If inbound_leaf_node is not provided:

Traverse prod_tree_dict_IN[product_name].
Find a stable path ending at supply_point.
Prefer sequence order if available.
Otherwise use stable DFS order.
8.4 Stitch route

If inbound route ends with supply_point and outbound route starts with supply_point:

inbound_route[:-1] + outbound_route

Otherwise:

inbound_route + outbound_route

but add a remark if supply_point could not be used as a clean stitch point.

8.5 Fallback

If inbound route cannot be found:

export outbound route only
set segment = outbound
add remarks:
inbound route not found; exported outbound route only

If outbound route cannot be found:

export inbound route only if available
add remarks:
outbound route not found

If neither route exists:

do not export rows for that lane
return empty result
9. PlanNode Traversal
9.1 PlanNode identification

A PlanNode should be identified by one of:

node.name
node.node_name
node.node_id

Priority:

name
node_name
node_id
fallback empty string
9.2 Children detection

The traversal helper should support common child attributes:

children
child_nodes

Both list and dict forms should be supported.

9.3 Path finding

Implement a simple DFS path search:

def find_path_in_plan_tree(root, target_node_name: str) -> list[Any]:
    ...

For route export, convert PlanNode objects to node names after path is found.

9.4 Stable ordering

When multiple children exist:

preserve list order if children is a list
preserve dict value order if stable
optionally sort by node name only if no stable order exists

Do not introduce random ordering.

10. Suggested Implementation Location

Preferred new module:

pysi/reporting/e2e_lane_route_exporter.py

Suggested functions:

def export_e2e_lane_route(
    *,
    product_name: str,
    prod_tree_dict_IN: dict,
    prod_tree_dict_OT: dict,
    output_path: str,
    leaf_node: str | None = None,
    inbound_leaf_node: str | None = None,
    supply_point_node: str = "supply_point",
) -> list[dict]:
    """
    Build and export E2E lane route rows from product-specific PlanNode trees.
    Return exported rows.
    """

Helper functions:

def build_e2e_lane_route_from_plan_trees(
    *,
    product_name: str,
    prod_tree_dict_IN: dict,
    prod_tree_dict_OT: dict,
    leaf_node: str | None = None,
    inbound_leaf_node: str | None = None,
    supply_point_node: str = "supply_point",
) -> list[str]:
    ...

def find_path_to_node(root, target_node_name: str) -> list:
    ...

def find_path_ending_at_supply_point(root, supply_point_node: str = "supply_point") -> list:
    ...

def stitch_inbound_outbound_routes(
    inbound_route: list[str],
    outbound_route: list[str],
    supply_point_node: str = "supply_point",
) -> list[str]:
    ...

def route_nodes_to_rows(...):
    ...
11. Integration Options
Option A: Standalone exporter only

This is the preferred first implementation.

Manual usage:

from pysi.reporting.e2e_lane_route_exporter import export_e2e_lane_route

rows = export_e2e_lane_route(
    product_name="IPHONE_NM_2028_BASE",
    prod_tree_dict_IN=env.prod_tree_dict_IN,
    prod_tree_dict_OT=env.prod_tree_dict_OT,
    output_path="data/e2e_lane_route.csv",
    leaf_node="CS_US_MAINSTREAM",
)
Option B: Pipeline integration later

Future integration can call this exporter after product trees are built and before chart generation.

Do not automatically wire into python -m main in the first PR unless very safe.

Option C: Chart generator consumes route CSV

Future chart command:

generate_price_waterfall_stacked_bar(
    "data/node_price_waterfall.csv",
    "outputs/reporting_mvp/price_propagation",
    product="IPHONE_NM_2028_BASE",
    leaf_node="CS_US_MAINSTREAM",
    e2e_lane_route_csv="data/e2e_lane_route.csv",
    chart_mode="full_price",
    chart_scope="e2e_primary",
)

Phase 2B+5a may prepare this interface, but it is acceptable to leave chart consumption to a follow-up PR if necessary.

12. Relationship with price_propagation_trace.csv

price_propagation_trace.csv remains useful for price continuity:

parent.ship_price_per_lot
→ child.purchase_cost_per_lot

But route ordering should prefer:

e2e_lane_route.csv

once available.

Recommended priority for chart ordering:

e2e_lane_route.csv
product PlanNode tree route if env is available
price_propagation_trace.csv
node_price_waterfall.csv row order
13. Tests

Add focused tests.

Suggested test file:

tests/reporting_test_e2e_lane_route_exporter.py
Test 1: find path to leaf in outbound tree

Given a simple tree:

supply_point
→ DAD
→ CS

Expected:

["supply_point", "DAD", "CS"]
Test 2: find inbound path to supply_point

Given:

MOM
→ supply_point

Expected:

["MOM", "supply_point"]
Test 3: stitch inbound and outbound routes

Given:

inbound  = ["MOM", "supply_point"]
outbound = ["supply_point", "DAD", "CS"]

Expected:

["MOM", "supply_point", "DAD", "CS"]
Test 4: export e2e_lane_route.csv rows

Given sample PlanNode trees.

Expected output rows:

MOM
supply_point
DAD
CS

with sequence_no:

1, 2, 3, 4
Test 5: no duplicate supply_point

Ensure supply_point appears once in stitched route.

Test 6: fallback outbound-only if inbound missing

Given no inbound tree.

Expected:

supply_point
DAD
CS

and remarks include fallback.

Test 7: stable row columns

Ensure output includes required columns:

product
lane_id
leaf_node
sequence_no
segment
direction
node_name
parent_node
child_node
is_supply_point
source_tree
remarks
14. Acceptance Criteria

Phase 2B+5a is accepted when:

pysi/reporting/e2e_lane_route_exporter.py exists.
It can build an E2E lane route from product-specific PlanNode trees.
It can export data/e2e_lane_route.csv.
The route is ordered upstream inbound → supply_point → outbound downstream.
supply_point is not duplicated.
It supports selected product.
It supports selected market leaf node.
It supports optional inbound leaf node.
It falls back safely if inbound route is missing.
Tests pass.
No money evaluation logic is changed.
No price formation logic is changed.
No planner behavior is changed.
No GUI behavior is changed.
No committed master CSV fixtures are changed.
15. Manual Verification Scenario

After implementation, a manual call should be possible once WOM runtime env is available.

Conceptual example:

from pysi.reporting.e2e_lane_route_exporter import export_e2e_lane_route

export_e2e_lane_route(
    product_name="IPHONE_NM_2028_BASE",
    prod_tree_dict_IN=env.prod_tree_dict_IN,
    prod_tree_dict_OT=env.prod_tree_dict_OT,
    output_path="data/e2e_lane_route.csv",
    leaf_node="CS_US_MAINSTREAM",
)

Expected route:

inbound upstream node
→ supply_point
→ DAD_FAS_AMER
→ WS_NA
→ RT_US_CARRIER
→ CS_US_MAINSTREAM

Actual inbound node depends on product-specific PlanNode tree.

16. Future Phase 2B+5b

Possible next phase:

Phase 2B+5b: E2E Lane Route CSV Consumption in Price Chart

This would modify:

pysi/reporting/price_propagation_chart.py

to consume:

data/e2e_lane_route.csv

for chart X-axis ordering.

Suggested new argument:

e2e_lane_route_csv: str | None = None

Then chart ordering priority becomes:

e2e_lane_route_csv
→ price_propagation_trace_csv
→ node_price_waterfall row order
17. Future Phase 2B+6

Possible later extensions:

fan-in E2E route export
all inbound branches feeding supply_point
lane selector
GUI menu integration
Management Cockpit integration
connector annotations between parent ship and child purchase
comparison of multiple market leaf nodes
comparison of multiple products
18. Summary

Phase 2B+5a corrects the route source for E2E lane visualization.

The key design point is:

Do not infer E2E route only from price_propagation_trace.csv.
Use WOM product-specific PlanNode trees.

The exported route file:

data/e2e_lane_route.csv

will become the route-order source for future E2E Price & Cost Structure charts.

This aligns the chart with WOM's actual internal model:

prod_tree_dict_IN[product]
→ supply_point
→ prod_tree_dict_OT[product]
→ selected market leaf