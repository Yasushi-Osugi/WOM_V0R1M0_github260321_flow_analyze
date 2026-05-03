# MOSD Phase 2B+3 Price Waterfall and Propagation Trace Export

## Purpose

Export evaluated node price formation and price propagation results into CSV files.

## Background

Phase 2B+1 connected parent ship price to child purchase cost.

Phase 2B+2 added node price formation from cost components.

Phase 2B+3 exposes those evaluated results for inspection and future visualization.

## Implemented behavior

- Export `node_price_waterfall.csv`.
- Export `price_propagation_trace.csv`.
- Preserve existing `node_money_eval.csv` behavior.
- Reuse evaluated node money rows.
- Do not recalculate price formation independently.
- Keep `inventory_unit_value_per_lot` separate from `ship_price_per_lot`.

## Not included

- Graph generation
- GUI tab integration
- Management Cockpit integration
- Bidirectional price propagation
- Target costing / allowable cost downward propagation
- Inventory B/S to P/L bridge

## Testing

- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py tests/evaluate_test_money_evaluator_node_price_formation.py tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py`
