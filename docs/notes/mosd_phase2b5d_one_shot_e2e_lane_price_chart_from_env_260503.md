# MOSD Phase 2B+5d One-shot E2E Lane Price Chart from Env

## Purpose

Generate E2E Lane Price & Cost Structure charts from WOM runtime env with one helper call.

## Background

- Phase 2B+5a exports E2E lane route from PlanNode trees.
- Phase 2B+5b makes chart generator consume `e2e_lane_route.csv`.
- Phase 2B+5c exports route CSV from runtime env.
- Phase 2B+5d combines these into one helper.

## Implemented behavior

- Export `e2e_lane_route.csv` from env.
- Generate `full_price` E2E lane chart.
- Generate `delta_only` E2E lane chart.
- Return generated PNG paths.
- Return route rows.
- Do not change money evaluation or planner behavior.

## Not included

- GUI button.
- Management Cockpit integration.
- Automatic pipeline hook.
- Fan-in E2E lane export.
- Price recalculation.

## Testing

- `PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_price_chart_runtime.py`
- `PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_runtime.py`
- `PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_exporter.py`
- `PYTHONPATH=. pytest -q tests/reporting_test_price_propagation_chart.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py tests/evaluate_test_money_evaluator_node_price_formation.py tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py tests/reporting_test_price_propagation_chart.py tests/reporting_test_e2e_lane_route_exporter.py tests/reporting_test_e2e_lane_route_runtime.py tests/reporting_test_e2e_lane_price_chart_runtime.py`
