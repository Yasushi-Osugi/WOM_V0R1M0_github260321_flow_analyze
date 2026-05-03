# MOSD Phase 2B+4 Price Propagation Stacked Bar Chart

## Purpose

Generate stacked bar chart PNG reports from `node_price_waterfall.csv`.

## Background

Phase 2B+3 exports node-level price formation data.
Phase 2B+4 visualizes that data for inspection.

## Implemented behavior

- Read `data/node_price_waterfall.csv` (or equivalent input path).
- Generate by-node stacked bar chart PNG files using matplotlib in headless mode.
- Use cost components as stacked bars:
  - purchase_cost_per_lot
  - value_added_cost_per_lot
  - variable_cost_per_lot
  - fixed_cost_per_lot
  - logistics_cost_per_lot
  - inventory_handling_cost_per_lot
  - tax_tariff_cost_per_lot
  - target_profit_per_lot
- Show `ship_price_per_lot` as labels above stacked bars.
- Save PNG files under `outputs/reporting_mvp/price_propagation` (or caller-provided output directory).
- Support product filter and direction filter.
- Treat missing optional component columns as zero.
- Do not stack `inventory_unit_value_per_lot`.
- Do not change money evaluation logic.

If `direction` is omitted, one chart per product is generated with all available directions combined for that product.
If `direction` is specified, charts are generated only for matching rows.

## Not included

- GUI integration
- Interactive dashboard
- Management Cockpit integration
- Bidirectional target costing
- Downward allowable cost propagation
- Inventory B/S to P/L bridge

## Testing

- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py`
- `PYTHONPATH=. pytest -q tests/reporting_test_price_propagation_chart.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py tests/evaluate_test_money_evaluator_node_price_formation.py tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py tests/reporting_test_price_propagation_chart.py`
