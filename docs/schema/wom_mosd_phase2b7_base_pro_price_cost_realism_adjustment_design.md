# WOM MOSD Phase 2B+7 BASE / PRO Price & Cost Master Realism Adjustment Design

## 1. Purpose

Phase 2B+7 defines the design for adjusting the placeholder Price & Cost master values for:

```text
IPHONE_NM_2028_BASE
IPHONE_NM_2028_PRO

The purpose is to move from:

non-zero placeholder values

to:

more natural smartphone-like Price & Cost structures

so that WOM E2E Lane Price & Cost Structure charts become easier to interpret as business / management simulation outputs.

Phase 2B+6 solved the immediate issue:

IPHONE_NM_2028_PRO had all-zero money values
→ chart generation skipped

Phase 2B+7 improves the realism and explanatory quality of the money model.

2. Background

WOM can now generate E2E Lane Price & Cost Structure charts from cockpit UI:

Product
→ Leaf Node
→ E2E Lane
→ Price & Cost Structure per lot

Current implemented phases:

Phase 2B+1:
  parent.ship_price_per_lot
  → child.purchase_cost_per_lot

Phase 2B+2:
  node-level price formation

Phase 2B+3:
  export node_price_waterfall.csv
  export price_propagation_trace.csv

Phase 2B+4:
  generate price propagation stacked bar chart

Phase 2B+4a:
  route ordering / delta-only readability improvement

Phase 2B+5:
  E2E lane chart

Phase 2B+5a:
  PlanNode tree based E2E lane route export

Phase 2B+5b:
  e2e_lane_route.csv as chart X-axis ordering input

Phase 2B+5c:
  runtime env to e2e_lane_route.csv

Phase 2B+5d:
  one-shot env helper for E2E lane price chart

Phase 2B+5e:
  cockpit Price & Cost Structure GUI adapter

Phase 2B+5f:
  product-aware leaf node dropdown selector

Phase 2B+6:
  PRO placeholder money values

After Phase 2B+6, both BASE and PRO can generate charts.

However, placeholder values may still look artificial.

Phase 2B+7 refines the Price & Cost master values so that BASE and PRO show a more natural cost / price / margin relationship.

3. Current Issue

Current Phase 2B+6 values are sufficient to generate charts, but they are still placeholder values.

Possible issues:

- BASE / PRO price gap may be too mechanical.
- PRO values may be simple multipliers of BASE.
- Node-level added cost may not reflect realistic supply chain behavior.
- Fixed cost or revenue values may dominate the chart.
- Logistics / distribution / retail costs may be too small or too large.
- Delta-only chart may not tell a natural cost story.

The next goal is not numerical accuracy against a real company.

The goal is:

business-plausible demonstration data

that makes WOM modeling understandable.

4. Scope
In scope
Adjust Price & Cost master values for:
IPHONE_NM_2028_BASE
IPHONE_NM_2028_PRO
Preserve node coverage for both products.
Make BASE / PRO price and cost structures more natural.
Keep PRO as a premium product relative to BASE.
Ensure E2E Lane charts remain generatable for:
IPHONE_NM_2028_BASE
IPHONE_NM_2028_PRO
Prefer modifications in:
pysi/master_data/node_product_money_master.csv
Add implementation note under docs/notes.
Add or update tests if feasible.
Not in scope
Real-world Apple cost modeling.
Market research.
External benchmark collection.
Money evaluator logic changes.
Price formation logic changes.
Purchase cost propagation logic changes.
PSI planning logic changes.
Cockpit GUI changes.
Chart rendering logic changes.
Management Cockpit integration.
Runtime output CSV/PNG commits.
5. Target File

Primary target:

pysi/master_data/node_product_money_master.csv

This file currently holds product × node money values used by WOM runtime money evaluation.

Phase 2B+7 should modify this file carefully.

Do not commit runtime-generated files such as:

data/node_price_waterfall.csv
data/price_propagation_trace.csv
data/e2e_lane_route.csv
outputs/reporting_mvp/price_propagation/
6. Modeling Principle

The goal is not to make every value realistic in an accounting sense.

The goal is to make the E2E Lane chart tell a plausible smartphone supply chain story.

A natural smartphone lane should show:

upstream / assembly:
  component cost and manufacturing value are formed

supply_point:
  global transfer / allocation price is established

DAD / warehouse:
  regional logistics and handling cost are added

retail / channel:
  selling cost and channel margin are added

consumer / market leaf:
  market-facing price is higher than upstream transfer price

For PRO:

PRO should be more expensive than BASE
because of higher component cost,
higher value-added cost,
higher target margin,
and higher final market price.

But not every component should increase equally.

7. BASE / PRO Relationship
7.1 BASE positioning

IPHONE_NM_2028_BASE represents the standard model.

Expected structure:

moderate component cost
moderate value-added cost
moderate target profit
moderate final market price
7.2 PRO positioning

IPHONE_NM_2028_PRO represents the premium model.

Expected structure:

higher component / purchase cost
higher value-added cost
slightly higher fixed burden
similar or slightly higher logistics / handling
higher target profit
higher ship / market price
7.3 Recommended ratios

Recommended PRO vs BASE ratios:

Field	Recommended PRO / BASE relationship
purchase / acquisition cost	1.20 - 1.30
inventory valuation	1.20 - 1.30
variable cost	1.10 - 1.25
fixed cost weekly	1.05 - 1.15
logistics / handling	1.00 - 1.10
target profit / margin	1.40 - 1.70
ship / revenue price	1.30 - 1.50
8. Node Role Based Cost Structure

The values should differ by node role.

8.1 Upstream / assembly nodes

Examples:

PAD_final_assy_ASIA
PAD_final_assy_EURO
MOM_final_assy_ASIA
MOM_final_assy_EURO
supply_point

Expected behavior:

- Component / purchase cost is important.
- Value-added cost should be visible.
- Fixed cost may exist.
- Target profit may be moderate.
- Ship price should become a meaningful transfer price.
8.2 Regional distribution nodes

Examples:

DAD_FAS_AMER
DAD_FAS_APAC
DAD_FAS_EURO
WS_NA
WS_EU
WS_APAC

Expected behavior:

- Purchase cost comes from upstream.
- Logistics / handling cost should be visible.
- Fixed cost can be moderate.
- Target profit should be smaller than market-facing nodes.
8.3 Retail / channel nodes

Examples:

RT_US_CARRIER
RT_US_ONLINE
RT_JP_APPLE
RT_DE_ONLINE
RT_CN_ONLINE
RT_UK_CARRIER
RT_IN_ECOM

Expected behavior:

- Purchase cost should reflect upstream ship price.
- Selling / channel cost should be visible if represented.
- Target profit / margin should be higher than warehouse nodes.
- Ship / revenue price should approach market price.
8.4 Market / customer leaf nodes

Examples:

CS_US_MAINSTREAM
CS_US_PREMIUM
CS_CN_PREMIUM
CS_DE_PREMIUM
CS_UK_MAINSTREAM
CS_JP_REPLACEMENT
CS_IN_ASPIRER

Expected behavior:

- Revenue / ship price should represent market-facing price.
- Purchase cost should come from parent RT / channel node.
- Target margin can be visible.
- PRO premium leaves should show higher final price than BASE.
9. Suggested Demo Price Levels

These are not real market prices.

They are demonstration price levels for WOM charts.

9.1 BASE

Possible final market-facing price range:

BASE final market / CS price:
  800 - 950 per lot
9.2 PRO

Possible final market-facing price range:

PRO final market / CS price:
  1100 - 1300 per lot
9.3 Interpretation

These are intended to make charts readable.

They should show:

PRO has higher price and higher margin potential.
BASE has lower price and lower cost.
10. Suggested Adjustment Pattern

If current CSV has simplified columns such as:

inventory_unit_value
revenue_unit_value
variable_cost_unit_value
fixed_cost_weekly

then use these as follows:

Column	Meaning in current simplified master
inventory_unit_value	inventory valuation / acquisition-like value
revenue_unit_value	revenue / ship price like value
variable_cost_unit_value	variable operating cost
fixed_cost_weekly	fixed cost burden
10.1 BASE example

For BASE:

supply_point:
  inventory_unit_value     around 450 - 550
  revenue_unit_value       around 600 - 700
  variable_cost_unit_value around 20 - 50
  fixed_cost_weekly        moderate

DAD / WS:
  revenue_unit_value       gradually higher
  variable_cost_unit_value logistics / handling-like cost

RT / CS:
  revenue_unit_value       highest
  variable_cost_unit_value selling/channel-like cost
10.2 PRO example

For PRO:

supply_point:
  inventory_unit_value     around 600 - 700
  revenue_unit_value       around 800 - 900

DAD / WS:
  revenue_unit_value       gradually higher

RT / CS:
  revenue_unit_value       around 1100 - 1300
10.3 Avoid unrealistic patterns

Avoid:

- every node has exactly the same revenue price
- PRO is just BASE × same multiplier everywhere
- logistics nodes add more margin than market nodes
- market leaf has lower price than upstream node
- all added costs are zero
11. Verification Chart Expectations

After Phase 2B+7, the following charts should be visually more natural.

11.1 BASE × CS_US_MAINSTREAM

Expected:

moderate E2E price build-up
lower than PRO
visible warehouse / channel / market added cost
11.2 PRO × CS_US_PREMIUM

Expected:

higher E2E price build-up
higher target profit or revenue value than BASE
premium product visible in final market price
11.3 Delta-only charts

Delta-only charts should make node-added costs visible.

Expected:

manufacturing / assembly value visible upstream
logistics / handling visible in DAD / WS
channel / market margin visible near RT / CS
12. Recommended Verification Commands

After updating master and running Full Plan, check sums.

python -c "import csv; cols=['inventory_unit_value','revenue_unit_value','variable_cost_unit_value','fixed_cost_weekly','purchase_cost_per_lot','value_added_cost_per_lot','variable_cost_per_lot','fixed_cost_per_lot','logistics_cost_per_lot','inventory_handling_cost_per_lot','tax_tariff_cost_per_lot','target_profit_per_lot','ship_price_per_lot']; rows=list(csv.DictReader(open('data/node_price_waterfall.csv', encoding='utf-8'))); 
for product in ['IPHONE_NM_2028_BASE','IPHONE_NM_2028_PRO']:
    pr=[r for r in rows if r.get('product')==product or r.get('product_name')==product]
    print(product, 'rows=', len(pr))
    print({c:sum(float((r.get(c) or 0) or 0) for r in pr if c in r) for c in cols})"

Manual GUI checks:

Product: IPHONE_NM_2028_BASE
Leaf:    CS_US_MAINSTREAM

Product: IPHONE_NM_2028_PRO
Leaf:    CS_US_PREMIUM

Both should generate:

full_price chart
delta_only chart
13. Tests

Existing tests should continue to pass:

tests/evaluate_test_money_evaluator_purchase_cost_propagation.py
tests/evaluate_test_money_evaluator_node_price_formation.py
tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py
tests/reporting_test_price_propagation_chart.py
tests/reporting_test_e2e_lane_route_exporter.py
tests/reporting_test_e2e_lane_route_runtime.py
tests/reporting_test_e2e_lane_price_chart_runtime.py
tests/reporting_test_leaf_node_candidates.py
tests/master_data_test_node_product_money_master_pro_placeholder.py

Possible new test:

tests/master_data_test_base_pro_money_master_realism.py

Suggested assertions:

- BASE rows exist.
- PRO rows exist.
- PRO covers at least the same nodes as BASE.
- PRO total revenue_unit_value > BASE total revenue_unit_value.
- PRO total inventory_unit_value > BASE total inventory_unit_value.
- PRO total variable_cost_unit_value >= BASE total variable_cost_unit_value.

Avoid overly strict exact-value tests.

14. Documentation Note

Add:

docs/notes/mosd_phase2b7_base_pro_price_cost_realism_adjustment_260504.md

Suggested content:

# MOSD Phase 2B+7 BASE / PRO Price & Cost Realism Adjustment

## Purpose

Adjust BASE and PRO Price & Cost master values to make E2E Lane charts more natural and business-plausible.

## Background

Phase 2B+6 added non-zero placeholder values for PRO. Phase 2B+7 refines BASE / PRO values so that the Price & Cost Structure chart better represents a smartphone-like cost buildup.

## Implemented behavior

- Preserve BASE and PRO node coverage.
- Adjust money values to create more natural price / cost relationships.
- Keep PRO as premium product relative to BASE.
- Do not change money evaluator or chart logic.

## Not included

- Real-world Apple cost estimation
- external benchmark research
- evaluator logic changes
- GUI changes
- Management Cockpit integration

## Verification

List test commands and manual chart checks.
15. Acceptance Criteria

Phase 2B+7 is accepted when:

BASE rows remain present.
PRO rows remain present.
PRO node coverage is at least BASE node coverage.
PRO revenue / final price is higher than BASE.
PRO inventory / acquisition-like value is higher than BASE.
Both BASE and PRO charts generate successfully.
BASE / PRO visual difference is interpretable in E2E lane charts.
Existing evaluator logic is unchanged.
Existing chart logic is unchanged.
Existing tests pass.
Runtime output CSV / PNG files are not committed.
16. Future Phase 2B+8

Possible future modeling refinements:

- market-specific price variation
- region-specific logistics cost
- country-specific tariff / trade policy cost
- channel-specific margin
- inbound material cost fan-in
- scenario-based cost shock
- target costing downward propagation

These are out of scope for Phase 2B+7.

17. Summary

Phase 2B+7 moves WOM Price & Cost modeling from:

non-zero placeholder values

to:

business-plausible demonstration values

for both:

IPHONE_NM_2028_BASE
IPHONE_NM_2028_PRO

This makes the E2E Lane Price & Cost Structure charts more useful for management explanation and WOM modeling demonstrations.