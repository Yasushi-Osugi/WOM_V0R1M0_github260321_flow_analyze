# MOSD Phase 2B+5f Cockpit Leaf Node Dropdown Selector

## Purpose

Replace manual leaf node input with a product-aware dropdown selector in the cockpit.

## Background

Phase 2B+5e added a **Price & Cost Structure** button that asks the user to type a leaf node.

Phase 2B+5f populates valid leaf nodes for the currently selected product.

## Implemented behavior

- Added a leaf node dropdown to cockpit selection controls.
- Added leaf candidate resolver in `pysi.reporting.leaf_node_candidates`.
- Candidate priority:
  1. Product-specific outbound PlanNode tree leaves
  2. `env.leaf_nodes_out`
  3. `data/price_propagation_trace.csv`
- Updated Price & Cost Structure action to use dropdown selection.
- Reporting orchestration remains outside `cockpit_tk.py`.

## Not included

- Embedded chart viewer
- Management Cockpit integration
- fan-in E2E lane selector
- inbound source selector
- chart display inside GUI

## Testing

- `PYTHONPATH=. pytest -q tests/reporting_test_leaf_node_candidates.py`
- `PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_price_chart_runtime.py`
- `PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_runtime.py`
- `PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_exporter.py`
- `PYTHONPATH=. pytest -q tests/reporting_test_price_propagation_chart.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py`
- `PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py`
- Combined command run covering the above suites.

## Manual verification

1. Start WOM with `python -m main`.
2. Select product `IPHONE_NM_2028_BASE`.
3. Confirm leaf dropdown is populated.
4. Select `CS_US_MAINSTREAM`.
5. Run Full Plan if needed.
6. Click **Price & Cost Structure** and confirm chart file paths are shown.
