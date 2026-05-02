# MOSD Phase 2B+2 Node Price Formation

## Purpose

Calculate `ship_price_per_lot` from node-level cost components when explicit `ship_price_per_lot` is not provided.

## Background

Phase 2B+1 connected parent `ship_price_per_lot` to child `purchase_cost_per_lot`.

Phase 2B+2 adds node-internal price formation before downstream price propagation.

## Implemented behavior

- Explicit non-zero `ship_price_per_lot` remains authoritative.
- Missing or zero `ship_price_per_lot` is calculated from cost components.
- `purchase_cost_per_lot` is used as the base cost.
- `fixed_cost_per_week` is converted to `fixed_cost_per_lot` using safe fallback logic.
- `inventory_unit_value_per_lot` is not included in `ship_price_per_lot`.
- Revenue remains based on `ship_price_per_lot`.
- Purchase amount remains based on `purchase_cost_per_lot`.

## Not included

- Management Cockpit KPI integration
- GUI graph display
- Bidirectional price propagation
- Target costing / allowable cost downward propagation
- Inventory B/S to P/L bridge
- `node_price_waterfall.csv`
- `price_propagation_trace.csv`

## Testing

- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py tests/evaluate_test_money_evaluator_node_price_formation.py`
