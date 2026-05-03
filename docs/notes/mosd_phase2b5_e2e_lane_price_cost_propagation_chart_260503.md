# MOSD Phase 2B+5 E2E Lane Price & Cost Propagation Chart

## Purpose

Generate E2E lane-level Price & Cost Structure charts from `node_price_waterfall.csv` and `price_propagation_trace.csv`.

## Background

Phase 2B+4a supports outbound lane chart generation using Product × Leaf Node.

Phase 2B+5 extends this to include inbound routes stitched through `supply_point`.

## Implemented behavior

- Build outbound route to selected market leaf.
- Build inbound route to `supply_point`.
- Stitch inbound and outbound routes into an E2E lane.
- Generate `full_price` E2E lane chart.
- Generate `delta_only` E2E lane chart.
- Label Y-axis as `Price / Cost per lot`.
- Preserve existing outbound-only behavior.

## Not included

- GUI integration
- Management Cockpit integration
- Price recalculation
- Bidirectional target costing
- Downward allowable cost propagation
- Inventory B/S to P/L bridge
- fan-in E2E lane chart

## Testing

- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py`
- `PYTHONPATH=. pytest -q tests/reporting_test_price_propagation_chart.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py tests/evaluate_test_money_evaluator_node_price_formation.py tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py tests/reporting_test_price_propagation_chart.py`
