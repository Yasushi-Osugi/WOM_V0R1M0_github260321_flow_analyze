# WOM MOSD Phase 2B+4a Price Chart Ordering and Readability Improvement Design

## 1. Purpose

Phase 2B+4a improves the readability of the Phase 2B+4 price propagation stacked bar chart.

Phase 2B+4 successfully introduced static PNG chart generation from:

```text
data/node_price_waterfall.csv

However, the initial chart has two readability issues:

Node order is not yet aligned with product tree / route ordering.
Large purchase_cost_per_lot values can visually hide smaller cost components.

Phase 2B+4a addresses these issues without changing money evaluation logic.

The goal is to make the chart communicate the key WOM price propagation concept:

parent node ship_price_per_lot
≈ child node purchase_cost_per_lot

and to make node-level added cost / margin easier to see.

2. Background

Current Phase 2B sequence:

Phase 2B+1:
  parent.ship_price_per_lot
  → child.purchase_cost_per_lot

Phase 2B+2:
  purchase_cost_per_lot
  + cost components
  + target_profit_per_lot
  → ship_price_per_lot

Phase 2B+3:
  export node_price_waterfall.csv
  export price_propagation_trace.csv

Phase 2B+4:
  generate price waterfall stacked bar PNG

The first Phase 2B+4 chart can generate PNG files, but the first actual visual output showed the following improvement points:

X-axis node order is not yet easy to interpret as parent → child flow.
The chart includes many nodes at once, making E2E route reading difficult.
purchase_cost_per_lot dominates the stacked bar height.
Smaller components such as logistics, fixed cost, tax, or target profit are visually hidden.
Products with all-zero price components generate nearly empty charts.

Phase 2B+4a focuses on chart readability and interpretation.

3. Scope
In scope
Improve chart ordering using product tree / propagation trace information.
Support route-based chart generation for a selected leaf node.
Add a delta-only chart mode that excludes purchase_cost_per_lot from stacked bars.
Add all-zero product handling.
Preserve existing full stacked bar chart behavior.
Use existing CSV files only.
Add tests for ordering, route selection, delta chart, and all-zero handling.
Add a short implementation note under docs/notes.
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
Committed master CSV fixture changes.
4. Design Principle

Phase 2B+4a is a chart readability improvement phase.

It must remain downstream of evaluated and exported data.

money_evaluator.py
  → money_output_exporter.py
  → node_price_waterfall.csv
  → price_propagation_trace.csv
  → price_propagation_chart.py
  → improved PNG reports

The chart generator must not recalculate:

purchase_cost_per_lot
ship_price_per_lot
target_profit_per_lot
tax_tariff_cost_per_lot
price_formation_mode

It only changes:

row ordering
row filtering
chart mode
rendering behavior
5. Current Issue 1: X-axis Ordering
5.1 Problem

The initial Phase 2B+4 chart orders nodes mainly by available row order or sequence_no.

This creates a chart where many nodes are displayed, but the price chain is not easy to follow.

For price propagation, users need to see:

parent node
  ship_price_per_lot
    ↓
child node
  purchase_cost_per_lot

If parent and child are far apart on the X-axis, this relationship is difficult to read.

5.2 Target behavior

Use tree / edge ordering so that nodes appear in a meaningful route sequence.

For outbound examples:

supply_point
→ DAD
→ WS
→ RT
→ CS

For inbound examples:

material / supplier
→ intermediate node
→ mother plant / supply_point
6. Current Issue 2: Purchase Cost Dominates the Bar
6.1 Problem

In full price stacked bar charts, purchase_cost_per_lot can be much larger than the incremental components added inside the node.

As a result, smaller components become visually invisible:

value_added_cost_per_lot
variable_cost_per_lot
fixed_cost_per_lot
logistics_cost_per_lot
inventory_handling_cost_per_lot
tax_tariff_cost_per_lot
target_profit_per_lot
6.2 Target behavior

Keep the existing full chart, but add a second mode:

delta_only

Delta-only chart excludes purchase_cost_per_lot and visualizes only the node-added components.

This helps users see:

ship_price_per_lot - purchase_cost_per_lot

which is the cost / value / margin added inside the node.

7. New Chart Modes
7.1 full_price mode

This is the existing Phase 2B+4 behavior.

Stacked components:

purchase_cost_per_lot
value_added_cost_per_lot
variable_cost_per_lot
fixed_cost_per_lot
logistics_cost_per_lot
inventory_handling_cost_per_lot
tax_tariff_cost_per_lot
target_profit_per_lot

Purpose:

Show full price structure.
Show total ship_price_per_lot level.
Confirm purchase cost base and price formation.
7.2 delta_only mode

New mode.

Stacked components:

value_added_cost_per_lot
variable_cost_per_lot
fixed_cost_per_lot
logistics_cost_per_lot
inventory_handling_cost_per_lot
tax_tariff_cost_per_lot
target_profit_per_lot

Excluded:

purchase_cost_per_lot
inventory_unit_value_per_lot

Purpose:

Show node-added cost and profit.
Avoid purchase_cost dominating the chart.
Make small cost components visible.
7.3 route_full_price mode

Optional naming.

This is full_price mode applied to a specific leaf route.

7.4 route_delta_only mode

Optional naming.

This is delta_only mode applied to a specific leaf route.

8. Tree / Route Ordering
8.1 Input source

Use:

data/price_propagation_trace.csv

to infer parent-child relationships.

Primary edge columns:

product
direction
from_node
to_node
sequence_no
parent_ship_price_per_lot
child_purchase_cost_per_lot
child_ship_price_per_lot

Use:

data/node_price_waterfall.csv

for node-level cost component values.

8.2 Ordering priority

For product and direction:

Use price_propagation_trace.csv parent → child edges.
If route selection is provided, use only nodes on the selected path.
If no route selection is provided, use topological ordering if possible.
If topological ordering is ambiguous, use sequence_no.
If sequence_no is unavailable, use stable input order.
Never fail only because perfect ordering is unavailable.
8.3 Handling branching trees

If a product tree branches into many markets, a single combined chart can become too crowded.

Therefore, the chart generator should support:

leaf_node

as an optional argument.

If leaf_node is provided, generate the route path from upstream origin to that leaf.

Example:

supply_point
→ DAD_US_CENTRAL_DC
→ WS_US_NA
→ RT_US_ONLINE
→ CS_US_MAINSTREAM

This is the preferred chart for explaining price propagation.

9. Leaf Route Chart
9.1 Purpose

A leaf route chart shows only the E2E path leading to one selected market / customer / channel node.

This chart should make the following visually clear:

upstream node ship price
=
downstream node purchase cost

or, if not equal:

price propagation gap exists
9.2 Function argument

Extend existing function if safe:

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
9.3 Behavior

If leaf_node is not provided:

preserve current behavior, but improve ordering if trace CSV is provided.

If leaf_node is provided:

load price_propagation_trace.csv.
find path ending at leaf_node for the selected product and direction.
filter node_price_waterfall rows to nodes on that path.
order rows according to the path.
generate chart for that route.
9.4 Fallback

If path cannot be found:

fall back to product / direction filtered rows.
add a warning to console or remarks if current logging style permits.
do not fail unless input CSV itself is missing or unreadable.
10. Price Propagation Visual Cue
10.1 Purpose

The chart should help users see:

parent.ship_price_per_lot
→ child.purchase_cost_per_lot
10.2 Initial implementation

The first improvement may simply rely on route ordering.

Once parent and child are adjacent, the relationship becomes easier to read.

10.3 Optional annotation

If simple, annotate each node label with both:

purchase: xxx
ship: yyy

or show:

P: xxx / S: yyy

above or below bars.

Do not overcomplicate the chart in Phase 2B+4a.

11. All-Zero Product Handling
11.1 Problem

Some products may have no price values yet.

Example:

all components = 0
ship_price_per_lot = 0

This produces an empty chart.

11.2 Target behavior

Default:

skip_all_zero = True

If all selected rows for a chart have zero values for:

ship_price_per_lot
purchase_cost_per_lot
value_added_cost_per_lot
variable_cost_per_lot
fixed_cost_per_lot
logistics_cost_per_lot
inventory_handling_cost_per_lot
tax_tariff_cost_per_lot
target_profit_per_lot

then:

do not generate PNG by default
return no path for that product
optionally print or log a message
11.3 Optional behavior

If:

skip_all_zero = False

then generate the empty chart, but annotate:

All price components are zero
12. Output File Naming
12.1 Full product chart
<product>_price_waterfall_stacked_bar.png
12.2 Direction-specific chart
<product>_<direction>_price_waterfall_stacked_bar.png
12.3 Leaf route chart
<product>_<direction>_<leaf_node>_price_waterfall_route_stacked_bar.png
12.4 Delta-only chart
<product>_<direction>_<leaf_node>_price_waterfall_delta_only.png

If direction or leaf_node is absent, omit that part.

All filenames should be sanitized.

13. Output Folder

Use the existing Phase 2B+4 folder:

outputs/reporting_mvp/price_propagation/

Do not change existing output folder behavior.

14. Chart Component Sets
14.1 full_price components
purchase_cost_per_lot
value_added_cost_per_lot
variable_cost_per_lot
fixed_cost_per_lot
logistics_cost_per_lot
inventory_handling_cost_per_lot
tax_tariff_cost_per_lot
target_profit_per_lot
14.2 delta_only components
value_added_cost_per_lot
variable_cost_per_lot
fixed_cost_per_lot
logistics_cost_per_lot
inventory_handling_cost_per_lot
tax_tariff_cost_per_lot
target_profit_per_lot
14.3 excluded from stack

Always exclude:

inventory_unit_value_per_lot

It may be used in future reference lines, but not in Phase 2B+4a stack.

15. Suggested Implementation Location

Modify existing module:

pysi/reporting/price_propagation_chart.py

Add helpers such as:

def load_price_propagation_trace(path: str) -> list[dict]:
    ...

def build_edge_order_from_trace(trace_rows: list[dict], product: str, direction: str | None) -> list[str]:
    ...

def find_route_to_leaf(trace_rows: list[dict], product: str, leaf_node: str, direction: str | None) -> list[str]:
    ...

def is_all_zero_chart(rows: list[dict], components: list[str]) -> bool:
    ...

def get_chart_components(chart_mode: str) -> list[str]:
    ...

Keep the module standalone.

Do not touch money_evaluator.py unless absolutely necessary.

16. Tests

Add focused tests in the existing chart test file:

tests/reporting_test_price_propagation_chart.py

or add a new file:

tests/reporting_test_price_propagation_chart_readability.py
Test 1: route ordering from price_propagation_trace

Given trace:

supply_point → DAD
DAD → CS

and node waterfall rows in random order:

CS
supply_point
DAD

Expected chart uses order:

supply_point
DAD
CS

If direct chart image inspection is difficult, expose and test a helper such as:

find_route_to_leaf(...)
sort_rows_by_route(...)
Test 2: leaf route filtering

Given two branches:

supply_point → DAD_US → CS_US
supply_point → DAD_EU → CS_EU

When:

leaf_node = CS_US

Expected selected route:

supply_point
DAD_US
CS_US
Test 3: delta_only excludes purchase cost

Given row:

purchase_cost_per_lot = 1000
value_added_cost_per_lot = 10
target_profit_per_lot = 20

When:

chart_mode = delta_only

Expected component list excludes:

purchase_cost_per_lot
Test 4: all-zero product skipped

Given all component values zero.

When:

skip_all_zero = True

Expected:

no PNG generated
Test 5: all-zero product can still generate if requested

Given all component values zero.

When:

skip_all_zero = False

Expected:

PNG generated
Test 6: existing Phase 2B+4 behavior still works

Existing chart generation tests should continue to pass.

17. Acceptance Criteria

Phase 2B+4a is accepted when:

Existing Phase 2B+4 chart generation still works.
Chart generator can use price_propagation_trace.csv for ordering.
Route chart can be generated for a selected leaf_node.
Delta-only chart mode exists.
purchase_cost_per_lot is excluded from delta-only chart.
inventory_unit_value_per_lot is never stacked.
All-zero products are skipped by default or clearly annotated.
Existing Phase 2B+1 / 2B+2 / 2B+3 tests continue to pass.
Existing Phase 2B+4 tests continue to pass.
No money evaluation logic is changed.
No GUI behavior is changed.
No planner behavior is changed.
No committed master CSV fixtures are changed.
18. Validation Commands

Recommended commands:

PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py
PYTHONPATH=. pytest -q tests/reporting_test_price_propagation_chart.py

If a new readability test file is added:

PYTHONPATH=. pytest -q tests/reporting_test_price_propagation_chart_readability.py

Combined:

PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py tests/evaluate_test_money_evaluator_node_price_formation.py tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py tests/reporting_test_price_propagation_chart.py
19. Documentation Note

Add a short implementation note:

docs/notes/mosd_phase2b4a_price_chart_ordering_readability_260503.md

Suggested contents:

# MOSD Phase 2B+4a Price Chart Ordering and Readability Improvement

## Purpose

Improve price propagation stacked bar chart readability.

## Background

Phase 2B+4 generated static price waterfall charts, but the first output showed that node order and large purchase cost values made propagation interpretation difficult.

## Implemented behavior

- Use price_propagation_trace.csv for route ordering when provided.
- Support leaf_node route chart generation.
- Add delta_only chart mode to show node-added components.
- Skip all-zero charts by default.
- Preserve existing full_price chart behavior.
- Do not change money evaluation logic.

## Not included

- GUI integration
- Management Cockpit integration
- Price recalculation
- Bidirectional target costing
- Downward allowable cost propagation

## Testing

List test commands and results.
20. Future Phase 2B+4b

Possible later improvements:

Add parent ship price → child purchase cost connector annotations.
Generate combined full_price + delta_only report.
Generate side-by-side inbound / outbound charts.
Add market leaf selector.
Add GUI report menu entry.
Add Management Cockpit link.
21. Summary

Phase 2B+4a improves the first price propagation chart so that it tells the correct story.

The first chart showed that the rendering pipeline works.

Phase 2B+4a makes the chart easier to interpret by adding:

tree / route ordering
leaf route filtering
delta-only view
all-zero product handling

This keeps the implementation safe while moving the chart closer to the intended WOM visual narrative:

upstream ship price
→ downstream purchase cost
→ downstream added cost
→ downstream ship price