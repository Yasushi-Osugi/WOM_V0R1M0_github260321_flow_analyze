# WOM MOSD Phase 2B+4 Price Propagation Stacked Bar Chart Design

## 1. Purpose

Phase 2B+4 defines the chart generation design for WOM price propagation visualization.

Phase 2B+1 implemented purchase cost propagation.

Phase 2B+2 implemented node price formation.

Phase 2B+3 exported price formation and propagation trace data into CSV files:

```text
data/node_price_waterfall.csv
data/price_propagation_trace.csv
```

Phase 2B+4 uses these CSV files to generate static chart reports that visualize:

- how price is formed at each node
- how cost components accumulate across the supply chain
- how parent ship price becomes child purchase cost
- where value added, logistics cost, fixed cost, tax, and profit are added
- whether the E2E price chain looks natural

The first implementation should generate PNG files only.

---

## 2. Background

WOM is moving from quantity-only PSI planning to two-phase costing.

The current sequence is:

```text
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
  generate stacked bar chart reports
```

This phase corresponds to the legacy PySI V0R8 style by-node cost structure chart, but adapted to WOM’s current MOSD / money evaluator output.

The primary goal is not visual beauty yet.

The primary goal is to create a reliable inspection chart for developers and heavy users.

---

## 3. Scope

### In scope

- Read `data/node_price_waterfall.csv`.
- Optionally read `data/price_propagation_trace.csv`.
- Generate by-node stacked bar chart PNG files.
- Support at least one selected product.
- Use node sequence order if available.
- Separate inbound / outbound direction if available.
- Use cost components as stacked bars.
- Overlay or annotate `ship_price_per_lot`.
- Save output image files under an output reporting folder.
- Add focused tests for chart generation.
- Add a short implementation note under `docs/notes`.

### Not in scope

- GUI tab integration.
- Interactive chart UI.
- Plotly dashboard.
- Management Cockpit integration.
- Issue Engine integration.
- New price calculation logic.
- Recalculation of money evaluation.
- Bidirectional target costing.
- Market-price downward allowable-cost propagation.
- Inventory B/S to P/L bridge.
- Modification of committed master CSV fixtures.

---

## 4. Design Principle

Phase 2B+4 is a reporting and visualization phase.

It must not change the meaning of money evaluation.

The chart generator should be downstream of Phase 2B+3 exports:

```text
money_evaluator.py
  → money_output_exporter.py
  → node_price_waterfall.csv
  → price propagation chart generator
  → PNG report
```

The chart generator must not recalculate ship_price_per_lot.

It should only visualize values that have already been evaluated and exported.

---

## 5. Input Files

### 5.1 Required input

```text
data/node_price_waterfall.csv
```

This file is required.

It should contain per-product, per-node cost component rows.

### 5.2 Optional input

```text
data/price_propagation_trace.csv
```

This file is optional for Phase 2B+4 initial implementation.

It may be used to annotate edge-level propagation or validate chart order.

The first implementation may generate charts from `node_price_waterfall.csv` only.

---

## 6. Output Files

### 6.1 Recommended output folder

```text
outputs/reporting_mvp/price_propagation/
```

### 6.2 Recommended output file names

For one product:

```text
outputs/reporting_mvp/price_propagation/<product>_price_waterfall_stacked_bar.png
```

If direction is separated:

```text
outputs/reporting_mvp/price_propagation/<product>_inbound_price_waterfall_stacked_bar.png
outputs/reporting_mvp/price_propagation/<product>_outbound_price_waterfall_stacked_bar.png
```

If a combined chart is generated:

```text
outputs/reporting_mvp/price_propagation/<product>_e2e_price_waterfall_stacked_bar.png
```

### 6.3 Optional report index

A simple markdown or text report may be generated later:

```text
outputs/reporting_mvp/price_propagation/price_propagation_report.md
```

This is optional and not required in the first PR.

---

## 7. Chart Type

### 7.1 Primary chart

The primary chart is:

```text
By-node stacked bar chart
```

### 7.2 X-axis

```text
node sequence
```

Display label:

```text
node_name
```

If available, use:

```text
sequence_no
```

If `sequence_no` is missing, use stable row order.

### 7.3 Y-axis

```text
amount per lot
```

Unit:

```text
cost / price per lot
```

### 7.4 Stacked bar components

Recommended stack components:

```text
purchase_cost_per_lot
value_added_cost_per_lot
variable_cost_per_lot
fixed_cost_per_lot
logistics_cost_per_lot
inventory_handling_cost_per_lot
tax_tariff_cost_per_lot
target_profit_per_lot
```

Missing columns should be treated as zero.

### 7.5 Overlay / annotation

Show `ship_price_per_lot` as either:

1. a line over the stacked bars, or
2. a label above each bar, or
3. both if simple and safe.

The first implementation may use labels above bars if line overlay is awkward.

### 7.6 Reference-only values

The chart must not stack:

```text
inventory_unit_value_per_lot
```

This value may be shown only as a reference line or omitted in the first implementation.

It must not be visually interpreted as a price formation component.

---

## 8. Chart Interpretation

The chart should help users inspect the following:

### 8.1 Node price formation

At each node:

```text
purchase cost
+ node cost components
+ target profit
= ship price
```

### 8.2 Edge price propagation

Across nodes:

```text
parent ship price
≈ child purchase cost
```

If `price_propagation_trace.csv` is used, the chart may later annotate where the propagation gap is non-zero.

### 8.3 Added value by node

The difference between:

```text
ship_price_per_lot
-
purchase_cost_per_lot
```

indicates the cost / value / margin added inside that node.

---

## 9. Direction Handling

### 9.1 Inbound chart

If `direction = inbound`, chart should show upstream supply-side cost buildup.

Interpretation:

```text
material / procurement side
→ supply point / mother plant side
```

This corresponds to:

```text
Material_Price upward2market
```

or supply-side feasible price buildup.

### 9.2 Outbound chart

If `direction = outbound`, chart should show downstream distribution and market-side price buildup.

Interpretation:

```text
supply point / mother plant side
→ distribution
→ channel
→ market
```

### 9.3 Unknown direction

If direction is not available:

```text
direction = unknown
```

Generate a single chart using available row order.

---

## 10. Product Selection

The chart generator should support:

1. a specific product
2. all products

### 10.1 Specific product

Recommended function argument:

```python
product: str | None = None
```

If product is provided, generate chart for that product only.

### 10.2 All products

If product is None, generate one chart per product.

The first PR may implement all-products mode if simple.

---

## 11. Suggested Implementation Location

Preferred new module:

```text
pysi/reporting/price_propagation_chart.py
```

Suggested functions:

```python
def generate_price_waterfall_stacked_bar(
    node_price_waterfall_csv: str,
    output_dir: str,
    *,
    product: str | None = None,
    direction: str | None = None,
) -> list[str]:
    """
    Generate price waterfall stacked bar chart PNG files.
    Return list of generated file paths.
    """
```

Optional helper functions:

```python
def load_node_price_waterfall(path: str) -> list[dict]:
    ...

def group_rows_by_product_and_direction(rows: list[dict]) -> dict:
    ...

def sort_waterfall_rows(rows: list[dict]) -> list[dict]:
    ...

def build_chart_title(product: str, direction: str | None) -> str:
    ...
```

A small CLI entry point may be added later, but is not required in the first PR.

---

## 12. Runtime Integration

For Phase 2B+4 initial PR, do not automatically run chart generation from the main WOM planning flow unless it is very safe.

Preferred initial integration:

```text
standalone function + tests
```

Optional simple script:

```text
pysi/reporting/price_propagation_chart.py
```

with manual execution support if convenient.

Future integration can connect this to reporting pipeline after the chart generator is stable.

---

## 13. Chart Library

Use matplotlib for the initial implementation.

Do not introduce large new dependencies.

Recommended behavior:

- Use default matplotlib colors.
- Use a non-interactive backend if needed for test environments.
- Save PNG files.
- Do not require a GUI display.

The implementation should be safe in headless environments.

---

## 14. Input Column Handling

The chart generator should tolerate missing optional columns.

Required minimum columns:

```text
product
node_name
ship_price_per_lot
```

Recommended columns:

```text
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
tax_tariff_cost_per_lot
target_profit_per_lot
ship_price_per_lot
inventory_unit_value_per_lot
```

If a cost component column is missing:

```text
treat as 0
```

If `ship_price_per_lot` is missing:

```text
fallback to sum of available stacked components
```

but this fallback should be noted in remarks or tests.

---

## 15. Recommended Stacking Order

Use this order:

```text
purchase_cost_per_lot
value_added_cost_per_lot
variable_cost_per_lot
fixed_cost_per_lot
logistics_cost_per_lot
inventory_handling_cost_per_lot
tax_tariff_cost_per_lot
target_profit_per_lot
```

This order follows the logic:

```text
acquired cost
→ node operation cost
→ logistics / handling
→ tax
→ profit
```

---

## 16. Data Quality Checks

The chart generator may warn or annotate internally if:

```text
ship_price_per_lot differs significantly from stacked component sum
```

Possible check:

```text
stack_sum
=
sum(component_per_lot)

price_gap
=
ship_price_per_lot - stack_sum
```

For Phase 2B+4 initial implementation:

- this check may be calculated
- it does not need to fail
- it may be added as a label or ignored visually

Later phases may export a chart validation report.

---

## 17. Tests

Add focused tests.

Suggested test file:

```text
tests/reporting_test_price_propagation_chart.py
```

or, if current test naming prefers evaluate tests:

```text
tests/evaluate_test_price_propagation_chart.py
```

### Test 1: chart file is generated

Given a small temporary `node_price_waterfall.csv`.

Expected:

```text
PNG file exists
PNG file size > 0
```

### Test 2: product filtering works

Given two products in CSV.

When `product = PRODUCT_A`.

Expected:

```text
only PRODUCT_A chart is generated
```

### Test 3: missing optional columns are treated as zero

Given CSV with only:

```text
product
node_name
ship_price_per_lot
purchase_cost_per_lot
```

Expected:

```text
chart generation does not fail
```

### Test 4: direction split works if implemented

Given inbound and outbound rows.

Expected:

```text
inbound chart is generated
outbound chart is generated
```

If direction split is not implemented in the first PR, this test can be omitted.

### Test 5: no GUI display required

The test should run in a headless environment.

---

## 18. Acceptance Criteria

Phase 2B+4 is accepted when:

1. A chart generator exists.
2. It reads `node_price_waterfall.csv`.
3. It generates at least one PNG stacked bar chart.
4. It can run without GUI interaction.
5. It does not modify money evaluation logic.
6. It does not modify planner behavior.
7. It does not modify committed master CSV fixtures.
8. It tolerates missing optional cost component columns.
9. It uses `inventory_unit_value_per_lot` only as reference or omits it.
10. It passes focused tests.
11. Existing Phase 2B+1, 2B+2, and 2B+3 tests continue to pass.

---

## 19. Commands for Validation

Recommended test commands:

```text
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py
PYTHONPATH=. pytest -q tests/reporting_test_price_propagation_chart.py
```

Combined:

```text
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py tests/evaluate_test_money_evaluator_node_price_formation.py tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py tests/reporting_test_price_propagation_chart.py
```

---

## 20. Documentation Note

Add a short implementation note:

```text
docs/notes/mosd_phase2b4_price_propagation_stacked_bar_chart_260503.md
```

Suggested contents:

```text
# MOSD Phase 2B+4 Price Propagation Stacked Bar Chart

## Purpose

Generate stacked bar chart PNG reports from node_price_waterfall.csv.

## Background

Phase 2B+3 exports node-level price formation data.

Phase 2B+4 visualizes that data for inspection.

## Implemented behavior

- Read node_price_waterfall.csv.
- Generate by-node stacked bar chart.
- Use cost components as stacked bars.
- Show ship_price_per_lot as chart reference.
- Save PNG under outputs/reporting_mvp/price_propagation.
- Do not change money evaluation logic.

## Not included

- GUI integration
- Interactive dashboard
- Management Cockpit integration
- Bidirectional target costing
- Downward allowable cost propagation

## Testing

List test commands and results.
```

---

## 21. Future Extensions

### 21.1 GUI integration

After the static report is stable, the chart can be linked from:

```text
Management Cockpit
reporting MVP
GUI report menu
```

### 21.2 Price propagation trace annotation

Later charts may use:

```text
price_propagation_trace.csv
```

to annotate:

```text
parent ship price
child purchase cost
price propagation gap
```

### 21.3 Bidirectional chart

Later phases may support two chart modes:

```text
Material_Price upward2market
Market_Price downward2material
```

Phase 2B+4 initial implementation only covers the evaluated upward / runtime price buildup.

### 21.4 Management KPI integration

Later Phase 2C may consume chart outputs or underlying waterfall data to support:

```text
ManagementFact
Issue Engine
Management Cockpit
```

---

## 22. Summary

Phase 2B+4 adds the first visual inspection layer for WOM two-phase costing.

It turns the exported price formation data into a by-node stacked bar chart.

This lets WOM users see:

- where price starts
- where cost is added
- where profit is added
- how each node contributes to the final price
- whether the E2E cost and price structure is natural

The first implementation should remain small:

```text
CSV in
→ PNG out
```

No GUI, no recalculation, no Management Cockpit integration yet.