# MOSD Phase 2B+5b E2E Lane Route CSV Chart Input

## Purpose

Use `e2e_lane_route.csv` as the route-order input for E2E Price & Cost Structure charts.

## Background

Phase 2B+5a exports E2E lane route ordering from product-specific PlanNode trees.

Phase 2B+5b connects that route file to the chart generator.

## Implemented behavior

- Added optional `e2e_lane_route_csv` argument to the chart generator.
- Added loading and filtering for `e2e_lane_route.csv` by product, leaf node, chart scope, and optional inbound leaf.
- Added sequence-based route ordering from `sequence_no` and applied it to chart node ordering.
- Filtered `node_price_waterfall.csv` chart rows to route nodes when route rows are found.
- Preserved fallback behavior when `e2e_lane_route_csv` is absent or has no matching rows.
- Avoided over-filtering on waterfall `direction` so `unknown` values still render with route-based ordering.

## Not included

- Runtime env generation of `e2e_lane_route.csv`
- GUI integration
- Management Cockpit integration
- Price recalculation
- Money evaluation changes

## Testing

- `PYTHONPATH=. pytest -q tests/reporting_test_price_propagation_chart.py`
- `PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_exporter.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py tests/evaluate_test_money_evaluator_node_price_formation.py tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py tests/reporting_test_price_propagation_chart.py tests/reporting_test_e2e_lane_route_exporter.py`
