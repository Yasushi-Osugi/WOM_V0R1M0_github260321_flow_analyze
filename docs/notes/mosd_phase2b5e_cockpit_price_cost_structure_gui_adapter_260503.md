# MOSD Phase 2B+5e Cockpit Price & Cost Structure GUI Adapter

## Purpose

Add a thin cockpit GUI entry to generate E2E Lane Price & Cost Structure charts.

## Background

Phase 2B+5d added a one-shot runtime helper:

- `generate_e2e_lane_price_chart_from_env(...)`

Phase 2B+5e connects this helper to the cockpit UI.

## Implemented behavior

- Added `Price & Cost Structure` button in cockpit action row.
- Uses current selected product from cockpit product selector.
- Asks user for market leaf node via `simpledialog.askstring(...)`.
- Calls `generate_e2e_lane_price_chart_from_env(...)` from `pysi.reporting.e2e_lane_price_chart_runtime`.
- Shows generated PNG paths, warnings, or errors via message boxes.
- Prints helper result for debug as `[price-cost-structure] {...}`.
- Keeps reporting logic outside `cockpit_tk.py` (GUI adapter only).

## Not included

- Embedded chart display in Tkinter
- Interactive chart viewer
- Management Cockpit integration
- Leaf node dropdown selector
- Price recalculation

## Testing

### Automated

Run:

```bash
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py tests/evaluate_test_money_evaluator_node_price_formation.py tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py tests/reporting_test_price_propagation_chart.py tests/reporting_test_e2e_lane_route_exporter.py tests/reporting_test_e2e_lane_route_runtime.py tests/reporting_test_e2e_lane_price_chart_runtime.py
```

### Manual verification

1. Start WOM GUI:

   ```bash
   python -m main
   ```

2. Run **Full Plan**.
3. Select product `IPHONE_NM_2028_BASE`.
4. Click **Price & Cost Structure**.
5. Enter leaf node `CS_US_MAINSTREAM`.
6. Confirm message shows generated PNG paths.
7. Confirm outputs exist:

   - `outputs/reporting_mvp/price_propagation`
   - `data/e2e_lane_route.csv`
