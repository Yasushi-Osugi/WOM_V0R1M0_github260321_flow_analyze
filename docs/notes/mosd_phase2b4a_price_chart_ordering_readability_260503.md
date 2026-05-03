# MOSD Phase 2B+4a Price Chart Ordering and Readability Improvement

## Purpose

Improve price propagation stacked bar chart readability.

## Background

Phase 2B+4 generated static price waterfall charts, but the first output showed that node order and large purchase cost values made propagation interpretation difficult.

## Implemented behavior

- Use `price_propagation_trace.csv` for route ordering when provided.
- Support `leaf_node` route chart generation.
- Add `delta_only` chart mode to show node-added components.
- Skip all-zero charts by default.
- Preserve existing `full_price` chart behavior.
- Do not change money evaluation logic.

## Not included

- GUI integration.
- Management Cockpit integration.
- Price recalculation.
- Bidirectional target costing.
- Downward allowable cost propagation.

## Testing

- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py`
- `PYTHONPATH=. pytest -q tests/reporting_test_price_propagation_chart.py`
