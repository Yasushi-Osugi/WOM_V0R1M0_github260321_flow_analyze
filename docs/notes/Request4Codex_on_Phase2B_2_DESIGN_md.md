# Codex Request: Implement Phase 2B+2 Node Price Formation for WOM Money Evaluator

You are working on the WOM repository:

Yasushi-Osugi/wom-event-flow-analyzer

Target branch:

feature/costing-two-phase-integration

Latest relevant commit:

2685ff5 Add wom_mosd_phase2b2_node_price_formation_design.md

Please implement a small, safe PR for:

Phase 2B+2: Node Price Formation

This PR should implement node-level ship_price_per_lot formation from cost components in the existing WOM money evaluator.

Do not implement Phase 2C Management KPI aggregation in this PR.
Do not implement GUI graph display in this PR.
Do not implement bidirectional price propagation in this PR.
Do not implement target costing / allowable cost downward propagation in this PR.
Do not rewrite the planner.
Do not overwrite committed fixture master CSV files.

Keep this PR small, additive, safe, and testable.

---

## 1. Design document to read first

Please read the following design document before editing code:

docs/schema/wom_mosd_phase2b2_node_price_formation_design.md

This design document is the authoritative scope for this PR.

Also inspect the previous Phase 2B+1 implementation and tests:

pysi/evaluate/money_evaluator.py
tests/evaluate_test_money_evaluator_purchase_cost_propagation.py
docs/notes/mosd_phase2b_purchase_cost_propagation_260502.md

---

## 2. Background

Phase 2B+1 has already implemented purchase cost propagation:

parent node ship_price_per_lot
→ child node purchase_cost_per_lot

That means purchase_cost_per_lot and purchase_amount can now become non-zero when parent ship_price_per_lot exists.

However, ship_price_per_lot itself is still mainly based on explicit master values.

Phase 2B+2 should add node-level price formation:

purchase_cost_per_lot
+ value_added_cost_per_lot
+ variable_cost_per_lot
+ fixed_cost_per_lot
+ logistics_cost_per_lot
+ inventory_handling_cost_per_lot
+ tax_tariff_cost_per_lot
+ target_profit_per_lot
= ship_price_per_lot

Only calculate ship_price_per_lot from components when explicit ship_price_per_lot is blank or zero.

Explicit non-zero ship_price_per_lot must remain authoritative.

---

## 3. Important accounting rule

Do not add inventory_unit_value_per_lot directly to ship_price_per_lot.

inventory_unit_value_per_lot is for B/S-style inventory valuation:

ending_inventory_value
=
ending_inventory_lots × inventory_unit_value_per_lot

It is not a direct price formation component.

For this PR:

- inventory_unit_value_per_lot should remain separate
- purchase_cost_per_lot should be used for purchase_amount / COGS-like cost
- ship_price_per_lot should be used for revenue calculation
- inventory B/S to P/L bridge is out of scope

---

## 4. Scope of this PR

Implement Phase 2B+2 only:

1. Add node price formation helper logic in pysi/evaluate/money_evaluator.py.
2. Preserve explicit non-zero ship_price_per_lot.
3. If ship_price_per_lot is blank or zero, calculate it from available cost components.
4. Use purchase_cost_per_lot after Phase 2B+1 propagation.
5. Allocate fixed_cost_per_week into fixed_cost_per_lot.
6. Treat missing cost component columns as zero.
7. Preserve existing revenue, purchase_amount, variable_cost, fixed_cost, inventory valuation behavior as much as possible.
8. Add explanatory output columns to node_money_eval.csv if safe.
9. Add focused tests.
10. Add a short implementation note under docs/notes.

---

## 5. Preferred implementation location

Prefer to implement this in:

pysi/evaluate/money_evaluator.py

Expected helper candidates:

def _calculate_fixed_cost_per_lot(...):
    ...

def _form_ship_price_per_lot(...):
    ...

or similar names that fit the current code structure.

Please avoid large refactoring.

---

## 6. Price formation rule

For each product × node:

### Step 1: determine purchase_cost_per_lot

Use existing Phase 2B+1 behavior.

Priority:

1. Explicit non-zero purchase_cost_per_lot from master
2. Parent ship_price_per_lot propagated through product_tree edge
3. 0

Do not break existing Phase 2B+1 tests.

### Step 2: determine fixed_cost_per_lot

Preferred rule:

fixed_cost_per_lot
=
fixed_cost_per_week / standard_volume_lots_per_week

If standard_volume_lots_per_week does not exist yet, use safe fallback:

1. current evaluator lot basis if available
2. 1.0 to avoid division by zero

Please add clear comments for fallback behavior.

### Step 3: determine tax_tariff_cost_per_lot

Minimum rule for this PR:

tax_tariff_cost_per_lot
=
tax_rate × tax_base_per_lot

tax_base_per_lot fallback:

1. purchase_cost_per_lot
2. explicit ship_price_per_lot if available
3. 0

If the current evaluator does not support enough tax fields, keep this minimal and safe.

### Step 4: determine target_profit_per_lot

Use explicit target_profit_per_lot if available.

If not available, use 0.

Do not implement target_margin_rate unless it is already easy and safe.

### Step 5: determine ship_price_per_lot

If explicit non-zero ship_price_per_lot exists:

ship_price_per_lot = explicit ship_price_per_lot
price_formation_mode = "explicit_ship_price"

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

price_formation_mode = "calculated_from_cost_components"

If all values are zero:

ship_price_per_lot = 0
price_formation_mode = "fallback_zero"

---

## 7. Cost component columns

The current master files may not yet have all future columns.

For this PR, treat missing columns as zero.

Supported component names should include, where available:

- purchase_cost_per_lot
- value_added_cost_per_lot
- variable_cost_per_lot
- fixed_cost_per_week
- fixed_cost_per_lot
- logistics_cost_per_lot
- inventory_handling_cost_per_lot
- tax_rate
- tax_tariff_cost_per_lot
- target_profit_per_lot
- ship_price_per_lot
- inventory_unit_value_per_lot

Do not require all of these columns to exist.

---

## 8. Output columns

Please preserve all existing node_money_eval.csv columns.

If safe, add the following explanatory columns:

fixed_cost_per_lot
value_added_cost_per_lot
logistics_cost_per_lot
inventory_handling_cost_per_lot
tax_tariff_cost_per_lot
target_profit_per_lot
price_formation_mode

Do not remove existing columns.

Existing important columns should continue to exist:

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
tax_rate

---

## 9. Tests

Please add focused tests.

Suggested test file:

tests/evaluate_test_money_evaluator_node_price_formation.py

Test cases:

### Test 1: explicit ship price is preserved

Setup:

purchase_cost_per_lot = 600
variable_cost_per_lot = 50
fixed_cost_per_lot = 20
target_profit_per_lot = 100
ship_price_per_lot = 900

Expected:

ship_price_per_lot == 900
price_formation_mode == "explicit_ship_price"

### Test 2: ship price is calculated when explicit value is zero

Setup:

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
price_formation_mode == "calculated_from_cost_components"

### Test 3: inventory unit value is not added to ship price

Setup:

purchase_cost_per_lot = 600
inventory_unit_value_per_lot = 9999
variable_cost_per_lot = 50
target_profit_per_lot = 100
ship_price_per_lot = 0

Expected:

ship_price_per_lot does not include 9999

### Test 4: fixed cost per lot allocation

Setup:

fixed_cost_per_week = 1000
standard_volume_lots_per_week = 100

Expected:

fixed_cost_per_lot == 10

If standard_volume_lots_per_week is not supported yet, test the fallback behavior clearly.

### Test 5: Phase 2B+1 tests still pass

Existing test must continue to pass:

tests/evaluate_test_money_evaluator_purchase_cost_propagation.py

---

## 10. Acceptance criteria

This PR is accepted when:

1. Existing Phase 2B+1 tests pass.
2. New Phase 2B+2 node price formation tests pass.
3. Explicit non-zero ship_price_per_lot remains authoritative.
4. Blank or zero ship_price_per_lot is calculated from cost components.
5. inventory_unit_value_per_lot is not added directly to ship_price_per_lot.
6. node_money_eval.csv keeps existing columns.
7. New explanatory columns are added only if safe.
8. No GUI behavior changes.
9. No planner behavior changes.
10. No committed fixture master CSV files are overwritten.
11. Implementation remains small and easy to review.

---

## 11. Commands to run

Please run:

PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py

If there is a broader relevant test command available, run it as well.

---

## 12. Documentation note

Please add a short note:

docs/notes/mosd_phase2b2_node_price_formation_260503.md

Suggested contents:

# MOSD Phase 2B+2 Node Price Formation

## Purpose

Calculate ship_price_per_lot from node-level cost components when explicit ship_price_per_lot is not provided.

## Background

Phase 2B+1 connected parent ship_price_per_lot to child purchase_cost_per_lot.

Phase 2B+2 adds node-internal price formation before downstream price propagation.

## Implemented behavior

- Explicit non-zero ship_price_per_lot remains authoritative.
- Missing or zero ship_price_per_lot is calculated from cost components.
- purchase_cost_per_lot is used as the base cost.
- fixed_cost_per_week is converted to fixed_cost_per_lot using safe fallback logic.
- inventory_unit_value_per_lot is not included in ship_price_per_lot.
- Revenue remains based on ship_price_per_lot.
- Purchase amount remains based on purchase_cost_per_lot.

## Not included

- Management Cockpit KPI integration
- GUI graph display
- Bidirectional price propagation
- Target costing / allowable cost downward propagation
- Inventory B/S to P/L bridge
- node_price_waterfall.csv
- price_propagation_trace.csv

## Testing

List test commands and results.

---

## 13. Future phases, not this PR

The following are future PRs:

Phase 2B+3:
- Export node_price_waterfall.csv
- Export price_propagation_trace.csv

Phase 2B+4:
- Generate price propagation stacked bar chart report

Phase 2C:
- Connect money_result / node_money_rows to ManagementFact, Issue Engine, and Management Cockpit

Later:
- Support bidirectional price propagation:
  - Material_Price upward2market
  - Market_Price downward2material

Please create a focused PR implementing only Phase 2B+2 Node Price Formation.