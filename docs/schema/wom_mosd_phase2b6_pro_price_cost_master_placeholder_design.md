# WOM MOSD Phase 2B+6 PRO Price & Cost Master Placeholder Design

## 1. Purpose

Phase 2B+6 defines the design for adding placeholder Price & Cost master values for:

```text
IPHONE_NM_2028_PRO

The immediate purpose is to resolve the confirmed issue that IPHONE_NM_2028_PRO has PSI / route rows but all Price & Cost values are zero in:

data/node_price_waterfall.csv

As a result, the E2E Lane Price & Cost Structure chart is skipped by the chart generator.

This phase gives IPHONE_NM_2028_PRO a provisional but reasonable Price & Cost structure so that WOM can visualize both:

IPHONE_NM_2028_BASE
IPHONE_NM_2028_PRO

as product-specific Price & Cost models.

2. Background

Phase 2B+5f added a product-aware Leaf node dropdown selector in the cockpit.

When selecting:

Product: IPHONE_NM_2028_PRO
Leaf:    CS_US_PREMIUM

the GUI displayed:

No chart files were generated.

A data check confirmed that IPHONE_NM_2028_PRO has rows in node_price_waterfall.csv:

IPHONE_NM_2028_PRO: 25 rows

but all relevant per-lot values are zero:

purchase_cost_per_lot = 0
value_added_cost_per_lot = 0
variable_cost_per_lot = 0
fixed_cost_per_lot = 0
logistics_cost_per_lot = 0
inventory_handling_cost_per_lot = 0
tax_tariff_cost_per_lot = 0
target_profit_per_lot = 0
ship_price_per_lot = 0

Therefore the issue is not a dropdown issue and not a route issue.

It is a Price & Cost master modeling issue.

3. Confirmed Issue

Current state:

IPHONE_NM_2028_BASE:
  PSI quantity model exists
  Price & Cost values exist
  E2E Lane chart can be generated

IPHONE_NM_2028_PRO:
  PSI quantity model exists
  Route / leaf nodes exist
  Price & Cost values are all zero
  E2E Lane chart is skipped

This means WOM currently has:

Quantity model for PRO
but no meaningful money model for PRO

Phase 2B+6 fixes this by adding placeholder money values for PRO.

4. Scope
In scope
Add or update Price & Cost master rows for IPHONE_NM_2028_PRO.
Use IPHONE_NM_2028_BASE as the reference product.
Generate PRO placeholder values by applying reasonable premium-product multipliers.
Ensure node_price_waterfall.csv for PRO becomes non-zero.
Ensure Price & Cost Structure chart can be generated for:
IPHONE_NM_2028_PRO
CS_US_PREMIUM
Add focused tests or smoke checks if feasible.
Add implementation note under docs/notes.
Not in scope
Changing money evaluation logic.
Changing price formation logic.
Changing purchase cost propagation logic.
Changing PSI planning logic.
Changing cockpit GUI behavior.
Adding new chart types.
Adding real-world smartphone cost benchmarks.
Full market pricing research.
Management Cockpit integration.
Fan-in E2E lane chart.
Downward target costing.
5. Target Product

Target product:

IPHONE_NM_2028_PRO

Reference product:

IPHONE_NM_2028_BASE

Target leaf node for verification:

CS_US_PREMIUM

Additional candidate leaf nodes may include:

CS_CN_PREMIUM
CS_DE_PREMIUM
CS_US_PREMIUM
6. Design Principle

Phase 2B+6 is a modeling data enhancement phase.

It should not change evaluation logic.

The goal is to provide reasonable placeholder values so that WOM can demonstrate:

Product-specific quantity model
+
Product-specific Price & Cost model
+
Product-specific E2E Lane visualization

For initial placeholder modeling:

PRO = BASE premium variant

Therefore PRO values should be derived from BASE values using simple multipliers.

7. Placeholder Value Rule
7.1 Recommended multiplier approach

Use BASE as the reference and apply product-premium multipliers.

Recommended initial multipliers:

Field	PRO multiplier vs BASE	Rationale
purchase_cost_per_lot	1.15	higher component / acquisition cost
value_added_cost_per_lot	1.20	higher assembly / feature value add
variable_cost_per_lot	1.15	higher variable operating cost
fixed_cost_per_week	1.10	slightly higher allocated fixed burden
fixed_cost_per_lot	calculated	should follow existing evaluator
logistics_cost_per_lot	1.00	similar logistics unless weight/handling differs
inventory_handling_cost_per_lot	1.00	similar handling
tax_tariff_cost_per_lot	1.15	proportional to higher taxable value
target_profit_per_lot	1.30	premium product margin
inventory_unit_value_per_lot	1.15	higher inventory valuation
ship_price_per_lot	1.25	higher market / transfer price
7.2 If BASE value is zero

If a BASE value is zero, do not blindly multiply zero.

Use a safe placeholder fallback where needed.

Example fallback values may be:

Field	Fallback
purchase_cost_per_lot	500
value_added_cost_per_lot	50
variable_cost_per_lot	30
logistics_cost_per_lot	20
inventory_handling_cost_per_lot	5
tax_tariff_cost_per_lot	30
target_profit_per_lot	150
inventory_unit_value_per_lot	500
ship_price_per_lot	900

These are placeholder values only.

They are not intended to represent actual Apple cost data.

8. Files to Inspect

Codex should inspect these files before editing:

pysi/master_data/node_product_money_master.csv
pysi/master_data/node_character_money_master.csv

data/cost_masters/product_cost_master.csv
data/cost_masters/sales_price_master.csv
data/cost_masters/node_cost_master.csv
data/cost_masters/lane_cost_master.csv

pysi/evaluate/money_evaluator.py
pysi/evaluate/money_output_exporter.py

Also inspect current generated outputs if available:

data/node_price_waterfall.csv
data/price_propagation_trace.csv

However, generated runtime output files should not be committed.

9. Preferred File to Modify

Preferred first target:

pysi/master_data/node_product_money_master.csv

Rationale:

Runtime money evaluator reads node-product money values.
IPHONE_NM_2028_PRO currently has zero per-lot values in output.
Node-product level values are the most direct way to make PRO visible in node-level money evaluation.

If IPHONE_NM_2028_PRO rows already exist:

update zero values to placeholder values

If PRO rows do not exist:

copy corresponding IPHONE_NM_2028_BASE rows
change product_name/product to IPHONE_NM_2028_PRO
apply premium multipliers

Do not remove existing BASE rows.

10. Expected Node Coverage

PRO placeholder values should cover at least the nodes that appear in the E2E lane to:

CS_US_PREMIUM

Expected lane may include nodes such as:

supply_point
DAD_FAS_AMER
WS_NA
RT_US_CARRIER
RT_US_ONLINE
CS_US_PREMIUM

Depending on current PlanNode tree, actual route may differ.

Recommended approach:

Add/update PRO money rows for all nodes where BASE has money rows.

This keeps PRO coverage broad and avoids leaf-specific holes.

11. Expected Behavior After Implementation

After running WOM full plan, node_price_waterfall.csv should show non-zero values for IPHONE_NM_2028_PRO.

Expected check:

sum(ship_price_per_lot) > 0
sum(purchase_cost_per_lot or cost components) > 0

The following GUI action should generate chart files:

Product: IPHONE_NM_2028_PRO
Leaf:    CS_US_PREMIUM
Button:  Price & Cost Structure

Expected generated files:

outputs/reporting_mvp/price_propagation/...
  IPHONE_NM_2028_PRO_CS_US_PREMIUM_e2e_lane_price_cost_structure.png
  IPHONE_NM_2028_PRO_CS_US_PREMIUM_e2e_lane_added_cost_structure_delta_only.png
12. Testing and Verification
12.1 Unit / regression tests

Existing tests should continue to pass:

tests/evaluate_test_money_evaluator_purchase_cost_propagation.py
tests/evaluate_test_money_evaluator_node_price_formation.py
tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py
tests/reporting_test_price_propagation_chart.py
tests/reporting_test_e2e_lane_route_exporter.py
tests/reporting_test_e2e_lane_route_runtime.py
tests/reporting_test_e2e_lane_price_chart_runtime.py
tests/reporting_test_leaf_node_candidates.py
12.2 Suggested focused test

If feasible, add a small test or smoke check that confirms:

IPHONE_NM_2028_PRO rows in node_product_money_master.csv have non-zero price/cost values

However, avoid over-coupling tests to exact CSV values if fixture patterns are not stable.

12.3 Manual verification command

After Run Full Plan, verify PRO values:

python -c "import csv; cols=['purchase_cost_per_lot','value_added_cost_per_lot','variable_cost_per_lot','fixed_cost_per_lot','logistics_cost_per_lot','inventory_handling_cost_per_lot','tax_tariff_cost_per_lot','target_profit_per_lot','ship_price_per_lot']; rows=[r for r in csv.DictReader(open('data/node_price_waterfall.csv', encoding='utf-8')) if r.get('product')=='IPHONE_NM_2028_PRO' or r.get('product_name')=='IPHONE_NM_2028_PRO']; print('rows=',len(rows)); print({c:sum(float((r.get(c) or 0) or 0) for r in rows) for c in cols})"

Expected:

rows > 0
at least some values > 0
13. GUI Manual Verification
Start WOM:
python -m main
Run Full Plan.
Select product:
IPHONE_NM_2028_PRO
Select leaf:
CS_US_PREMIUM
Click:
Price & Cost Structure
Confirm that generated chart files are shown.
Confirm output PNG files exist:
dir outputs\reporting_mvp\price_propagation
14. GUI Message Improvement

This phase may optionally improve the “No chart files were generated” message.

Current message:

No chart files were generated.

Recommended improved message:

No chart files were generated.

Possible reasons:
- selected product has all-zero price/cost values
- no matching E2E route rows
- no matching node_price_waterfall rows
- Run Full Plan has not been executed
Optional scope

This can be included in Phase 2B+6 if the change is very small.

Otherwise, define as a follow-up:

Phase 2B+6a: No Chart Generated UX Message Improvement
15. Acceptance Criteria

Phase 2B+6 is accepted when:

IPHONE_NM_2028_PRO has non-zero Price & Cost values.
Existing IPHONE_NM_2028_BASE values are preserved.
node_price_waterfall.csv after Run Full Plan shows non-zero PRO values.
GUI can generate Price & Cost Structure chart for:
IPHONE_NM_2028_PRO
CS_US_PREMIUM
No money evaluation logic is changed.
No planning logic is changed.
No chart generation logic is changed unless optional UX message improvement is included.
Existing tests pass.
Runtime generated CSV/PNG files are not committed.
16. Implementation Note

Add implementation note:

docs/notes/mosd_phase2b6_pro_price_cost_master_placeholder_260504.md

Suggested content:

# MOSD Phase 2B+6 PRO Price & Cost Master Placeholder

## Purpose

Add placeholder Price & Cost master values for IPHONE_NM_2028_PRO.

## Background

IPHONE_NM_2028_PRO exists in PSI and route outputs, but its price/cost values were all zero in node_price_waterfall.csv. This caused Price & Cost Structure chart generation to return no files.

## Implemented behavior

- Add/update PRO node-product money rows.
- Use BASE as reference where possible.
- Apply premium multipliers for PRO.
- Preserve BASE values.
- Enable E2E Lane Price & Cost Structure chart generation for PRO.

## Not included

- Real-world smartphone cost benchmark
- money evaluator logic changes
- GUI structural changes
- Management Cockpit integration

## Verification

List test commands and manual verification results.
17. Future Phase 2B+6a

Recommended follow-up:

Phase 2B+6a: No Chart Generated UX Message Improvement

Purpose:

show why chart was not generated
distinguish all-zero money values from missing route rows
reduce user confusion

Possible improved GUI message:

No chart files were generated.

Possible reasons:
- selected product has all-zero price/cost values
- no matching route rows
- no matching node_price_waterfall rows
- Run Full Plan has not been executed
18. Summary

Phase 2B+6 is the first explicit product-level Price & Cost modeling refinement after chart integration.

The confirmed issue is:

IPHONE_NM_2028_PRO has quantity and route data,
but all Price & Cost values are zero.

The fix is not a chart logic fix.

The fix is:

Add placeholder Price & Cost master values for PRO.

This turns PRO from:

quantity-only product

into:

quantity + money model product

which is exactly the WOM modeling direction.