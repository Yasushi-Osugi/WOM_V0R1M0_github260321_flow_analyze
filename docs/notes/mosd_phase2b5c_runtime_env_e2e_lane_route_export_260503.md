# MOSD Phase 2B+5c Runtime Env E2E Lane Route Export

## Purpose

Provide a runtime helper to export `e2e_lane_route.csv` from WOM env.

## Background

- Phase 2B+5a added a PlanNode-tree-based E2E lane route exporter.
- Phase 2B+5b made the chart generator consume `e2e_lane_route.csv`.
- Phase 2B+5c connects the exporter to WOM runtime env.

## Implemented behavior

- Read `env.prod_tree_dict_IN`.
- Read `env.prod_tree_dict_OT`.
- Export `e2e_lane_route.csv` for selected product and leaf node.
- Reuse existing `e2e_lane_route_exporter`.
- Return `[]` safely for missing env or blank product.
- Do not change money evaluation or planner behavior.

## Not included

- GUI button.
- Automatic pipeline hook.
- Management Cockpit integration.
- Chart auto-generation.
- Fan-in E2E lane export.

## Testing

- `PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_runtime.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py`
- `PYTHONPATH=. pytest -q tests/reporting_test_price_propagation_chart.py`
- `PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_exporter.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py tests/evaluate_test_money_evaluator_node_price_formation.py tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py tests/reporting_test_price_propagation_chart.py tests/reporting_test_e2e_lane_route_exporter.py tests/reporting_test_e2e_lane_route_runtime.py`
