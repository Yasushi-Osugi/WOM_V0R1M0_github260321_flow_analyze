# MOSD Phase 2B+5a PlanNode Tree Based E2E Lane Route Export

## Purpose

Export E2E lane route ordering from product-specific PlanNode trees.

## Background

Phase 2B+5 generated E2E lane chart files, but route ordering based only on `price_propagation_trace.csv` is not enough.

WOM has product-specific planning trees:

- `prod_tree_dict_IN[product]`
- `prod_tree_dict_OT[product]`

These should be the route-order source.

## Implemented behavior

- Build outbound route from `prod_tree_dict_OT[product]`.
- Build inbound route from `prod_tree_dict_IN[product]`.
- Stitch inbound and outbound routes through `supply_point`.
- Export `e2e_lane_route.csv`.
- Avoid duplicate `supply_point`.
- Provide stable `sequence_no`.
- Fall back safely if inbound route is missing.

## Not included

- Chart consumption of `e2e_lane_route.csv`
- GUI integration
- Management Cockpit integration
- Price recalculation
- Money evaluation changes
- Fan-in E2E lane export

## Testing

- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py`
- `PYTHONPATH=. pytest -q tests/reporting_test_price_propagation_chart.py`
- `PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_exporter.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py tests/evaluate_test_money_evaluator_node_price_formation.py tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py tests/reporting_test_price_propagation_chart.py tests/reporting_test_e2e_lane_route_exporter.py`
