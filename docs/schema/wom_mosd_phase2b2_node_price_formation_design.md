# WOM MOSD Phase 2B+2 Node Price Formation Design

## 1. Purpose

Phase 2B+2 defines the minimum runtime design for node-level price formation in WOM money evaluation.

Phase 2B+1 implemented purchase cost propagation:

parent node ship_price_per_lot
→ child node purchase_cost_per_lot

Phase 2B+2 extends this by calculating ship_price_per_lot at each node from node-level cost components when ship_price_per_lot is not explicitly provided.

The goal is to make WOM money evaluation explain not only "what price is used", but also "why that price is formed".

---

## 2. Background

In Phase 2B runtime integration, WOM confirmed that node_product_money_master.csv values can be read by the runtime money evaluator.

In Phase 2B+1, purchase_cost_per_lot and purchase_amount were connected through product_tree parent-child relationships.

However, the current money evaluator still mainly depends on explicit ship_price_per_lot values from master files.

For WOM 2 Phase Costing, this is not enough.

WOM needs to support:

1. Node internal price formation
2. Edge-based price propagation
3. Future price waterfall visualization
4. Future Management KPI aggregation

This phase implements item 1.

---

## 3. Scope

This phase implements a small, safe extension to node-level money evaluation.

### In scope

- Add node price formation logic in money_evaluator.py.
- Use existing purchase_cost_per_lot, including Phase 2B+1 propagated purchase cost.
- Calculate ship_price_per_lot from cost components when ship_price_per_lot is blank or zero.
- Preserve explicit non-zero ship_price_per_lot as authoritative.
- Calculate fixed_cost_per_lot from fixed_cost_per_week.
- Add output columns required to explain price formation.
- Add focused tests.
- Add a short note under docs/notes.

### Not in scope

- Management Cockpit KPI integration.
- GUI tab implementation.
- Full bidirectional price propagation.
- Target costing / allowable cost downward propagation.
- Inventory B/S to P/L bridge.
- Major rewrite of money evaluator.
- Rewrite of MOSD adapter.
- Rewrite of planner behavior.

---

## 4. Accounting Design Principles

### 4.1 Price formation and price propagation are different

Node price formation happens inside a node.

Edge price propagation happens between nodes.

```text
Node price formation:
  purchase_cost_per_lot
  + cost components
  + target profit
  = ship_price_per_lot

Edge price propagation:
  parent.ship_price_per_lot
  → child.purchase_cost_per_lot

Phase 2B+1 implemented the second part.

Phase 2B+2 implements the first part.

4.2 Inventory valuation and P/L cost must be separated

inventory_unit_value_per_lot is not a direct component of ship_price_per_lot.

It is used for inventory valuation:

ending_inventory_value
=
ending_inventory_lots × inventory_unit_value_per_lot

P/L cost should be handled separately through purchase_amount, COGS, inventory release cost, or future inventory B/S to P/L bridge.

Therefore, Phase 2B+2 must not calculate ship_price_per_lot as:

purchase_cost_per_lot
+ inventory_unit_value_per_lot
+ ...

This is explicitly prohibited.

5. Node Price Formation Rule

For each product × node:

Step 1: Determine purchase_cost_per_lot

Use existing Phase 2B+1 behavior:

Explicit non-zero purchase_cost_per_lot from master file
Parent node ship_price_per_lot propagated through product_tree edge
Fallback 0
Step 2: Determine fixed_cost_per_lot

Preferred rule:

fixed_cost_per_lot
=
fixed_cost_per_week / standard_volume_lots_per_week

If standard_volume_lots_per_week is not available, use a safe fallback volume already available in the evaluator.

Fallback priority:

standard_volume_lots_per_week
current node lot basis used by evaluator
1.0 to avoid division by zero

The fallback must be commented clearly.

Step 3: Determine tax_tariff_cost_per_lot

Minimum Phase 2B+2 rule:

tax_tariff_cost_per_lot
=
tax_rate × tax_base_per_lot

tax_base_per_lot fallback:

purchase_cost_per_lot
ship_price_per_lot if explicitly provided
0

For this phase, tax implementation may be minimal if existing evaluator has only tax_rate.

Step 4: Determine target_profit_per_lot

Use explicit target_profit_per_lot if present.

If only target_margin_rate is present in future, it may be supported later.

For this phase:

target_profit_per_lot = explicit value or 0
Step 5: Determine ship_price_per_lot

If explicit non-zero ship_price_per_lot exists:

ship_price_per_lot = explicit ship_price_per_lot

Otherwise:

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

If some columns do not exist yet, treat them as 0.

6. Cost Component Definitions

Recommended internal component names:

Component	Meaning
purchase_cost_per_lot	Acquired cost from parent node or explicit master
value_added_cost_per_lot	Node-specific value-added cost
variable_cost_per_lot	Variable operating cost per lot
fixed_cost_per_week	Weekly fixed cost before allocation
fixed_cost_per_lot	Allocated fixed cost per lot
logistics_cost_per_lot	Transport / logistics cost per lot
inventory_handling_cost_per_lot	Warehouse handling cost linked to shipment / release activity
tax_tariff_cost_per_lot	Tax / tariff per lot
target_profit_per_lot	Target profit added at node
ship_price_per_lot	Node outbound price to next node or market
7. Explicit Master Value Precedence

Explicit non-zero master values remain authoritative.

purchase_cost_per_lot
explicit non-zero purchase_cost_per_lot
> propagated parent ship_price_per_lot
> 0
ship_price_per_lot
explicit non-zero ship_price_per_lot
> calculated ship_price_per_lot from cost components
> 0

This keeps Phase 2B+2 safe and backward compatible.

8. Revenue, Purchase Amount, and Profit
Revenue

Revenue continues to use ship_price_per_lot:

revenue
=
ship_price_per_lot × revenue_lots

The current evaluator's lot basis should be preserved.

Purchase amount / COGS proxy

Purchase amount continues to use purchase_cost_per_lot:

purchase_amount
=
purchase_cost_per_lot × purchase_lots

For this phase, purchase_amount may continue to use the existing lot basis used by the evaluator.

Profit

Minimum rule:

profit
=
revenue
- purchase_amount
- variable_cost
- fixed_cost
- tax_cost

If existing evaluator already calculates profit, Phase 2B+2 should preserve the existing structure and only improve unit price formation inputs.

9. Output Columns

node_money_eval.csv should preserve existing columns and may add the following columns if safe:

product
product_name
node_name
node_character
revenue
purchase_amount
variable_cost
fixed_cost
ending_inventory_value
inventory_value
profit
purchase_cost_per_lot
ship_price_per_lot
inventory_unit_value_per_lot
variable_cost_per_lot
fixed_cost_per_week
fixed_cost_per_lot
value_added_cost_per_lot
logistics_cost_per_lot
inventory_handling_cost_per_lot
tax_rate
tax_tariff_cost_per_lot
target_profit_per_lot
price_formation_mode

price_formation_mode values:

explicit_ship_price
calculated_from_cost_components
fallback_zero
10. Future Output Files

The following files are not required in Phase 2B+2 but should be prepared conceptually for Phase 2B+3.

data/node_price_waterfall.csv
data/price_propagation_trace.csv

These will support price propagation visualization.

11. Tests

Add focused tests.

Suggested test file:

tests/evaluate_test_money_evaluator_node_price_formation.py
Test 1: Explicit ship price is preserved

Given:

purchase_cost_per_lot = 600
variable_cost_per_lot = 50
fixed_cost_per_lot = 20
target_profit_per_lot = 100
explicit ship_price_per_lot = 900

Expected:

ship_price_per_lot == 900
price_formation_mode == explicit_ship_price
Test 2: Ship price is calculated when explicit value is zero

Given:

purchase_cost_per_lot = 600
value_added_cost_per_lot = 40
variable_cost_per_lot = 50
fixed_cost_per_lot = 20
logistics_cost_per_lot = 30
tax_tariff_cost_per_lot = 10
target_profit_per_lot = 100
ship_price_per_lot = 0

Expected:

ship_price_per_lot == 850
price_formation_mode == calculated_from_cost_components
Test 3: Inventory unit value is not added to ship price

Given:

purchase_cost_per_lot = 600
inventory_unit_value_per_lot = 9999
variable_cost_per_lot = 50
target_profit_per_lot = 100
ship_price_per_lot = 0

Expected:

ship_price_per_lot does not include 9999
Test 4: Fixed cost per lot allocation

Given:

fixed_cost_per_week = 1000
standard_volume_lots_per_week = 100

Expected:

fixed_cost_per_lot == 10
Test 5: Existing purchase cost propagation remains valid

Phase 2B+1 tests must continue to pass.

12. Acceptance Criteria

Phase 2B+2 is accepted when:

Existing Phase 2B+1 tests pass.
New node price formation tests pass.
Explicit ship_price_per_lot remains authoritative.
Missing or zero ship_price_per_lot is calculated from cost components.
inventory_unit_value_per_lot is not added directly to ship_price_per_lot.
node_money_eval.csv keeps existing columns.
No GUI behavior changes.
No planner behavior changes.
No committed fixture master CSV files are overwritten.
The implementation remains small and testable.

13. Future Phases
Phase 2B+3

Export:

node_price_waterfall.csv
price_propagation_trace.csv

Phase 2B+4

Generate price propagation stacked bar chart.

Phase 2C

Connect money_result / node_money_rows to ManagementFact, Issue Engine, and Management Cockpit.

Later

Support bidirectional price propagation:

Material_Price upward2market
Market_Price downward2material

This later phase will support both cost buildup and market-back target costing.