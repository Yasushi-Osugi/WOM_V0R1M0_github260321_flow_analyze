# WOM MOSD Phase 2B+5c Runtime Env E2E Lane Route Export Design

## 1. Purpose

Phase 2B+5c defines the design for generating `e2e_lane_route.csv` from the actual WOM runtime environment.

Phase 2B+5a implemented a standalone exporter:

```text
pysi/reporting/e2e_lane_route_exporter.py

which can build an E2E lane route from:

prod_tree_dict_IN[product]
prod_tree_dict_OT[product]

Phase 2B+5b updated the chart generator so that it can use:

data/e2e_lane_route.csv

as the X-axis ordering input for E2E Lane Price & Cost Structure charts.

Phase 2B+5c connects the exporter to WOM runtime env so that the user does not need to manually handle env.prod_tree_dict_IN and env.prod_tree_dict_OT.

The goal is to make this flow practical:

python -m main
Run Full Plan
  ↓
WOM runtime env has product-specific PlanNode trees
  ↓
Export data/e2e_lane_route.csv
  ↓
Generate E2E Lane Price & Cost Structure chart
2. Background

Current implemented phases:

Phase 2B+1:
  parent.ship_price_per_lot
  → child.purchase_cost_per_lot

Phase 2B+2:
  node-level price formation

Phase 2B+3:
  export node_price_waterfall.csv
  export price_propagation_trace.csv

Phase 2B+4:
  generate price propagation stacked bar chart

Phase 2B+4a:
  improve route readability and delta-only chart

Phase 2B+5:
  add E2E lane chart scope

Phase 2B+5a:
  export E2E lane route from PlanNode trees

Phase 2B+5b:
  consume e2e_lane_route.csv in chart generator

Phase 2B+5c provides the runtime entry point.

3. Problem Statement

The current exporter works if called directly with:

export_e2e_lane_route(
    product_name="IPHONE_NM_2028_BASE",
    prod_tree_dict_IN=env.prod_tree_dict_IN,
    prod_tree_dict_OT=env.prod_tree_dict_OT,
    output_path="data/e2e_lane_route.csv",
    leaf_node="CS_US_MAINSTREAM",
)

However, this requires the caller to have direct access to env.

For practical use, WOM needs a small runtime helper that:

receives the current WOM runtime env
gets prod_tree_dict_IN
gets prod_tree_dict_OT
gets selected product
gets selected leaf node
exports data/e2e_lane_route.csv
optionally calls chart generation

Phase 2B+5c focuses on step 1 through step 6.

4. Scope
In scope
Add a runtime helper function that exports e2e_lane_route.csv from a WOM env object.
Read prod_tree_dict_IN and prod_tree_dict_OT from env.
Support selected product.
Support selected leaf_node.
Support optional inbound_leaf_node.
Use existing export_e2e_lane_route(...).
Write output to data/e2e_lane_route.csv by default.
Add focused tests using a fake env object.
Add documentation note under docs/notes.
Not in scope
GUI button integration.
Management Cockpit integration.
Automatic chart generation from python -m main.
Money evaluation changes.
Price formation changes.
Purchase cost propagation changes.
PSI planning changes.
Fan-in E2E route export.
Bidirectional target costing.
Downward allowable cost propagation.
Master CSV fixture changes.
5. Proposed Runtime Helper
5.1 Preferred implementation location

Add a small helper module:

pysi/reporting/e2e_lane_route_runtime.py
5.2 Primary function
def export_e2e_lane_route_from_env(
    env,
    *,
    product_name: str,
    leaf_node: str | None = None,
    inbound_leaf_node: str | None = None,
    output_path: str = "data/e2e_lane_route.csv",
    supply_point_node: str = "supply_point",
) -> list[dict]:
    """
    Export E2E lane route CSV from WOM runtime env.

    This function reads:
      - env.prod_tree_dict_IN
      - env.prod_tree_dict_OT

    and delegates route construction/export to:
      - pysi.reporting.e2e_lane_route_exporter.export_e2e_lane_route
    """
5.3 Behavior

The helper should:

1. validate env is not None
2. read env.prod_tree_dict_IN
3. read env.prod_tree_dict_OT
4. validate product_name is non-empty
5. call export_e2e_lane_route(...)
6. return exported rows
5.4 Safe fallback

If prod_tree_dict_IN is missing:

use {}

If prod_tree_dict_OT is missing:

use {}

If both are missing:

return []

Do not crash in GUI / runtime context unless input itself is invalid.

6. Optional Convenience Function

Add a convenience wrapper for generating both route and chart later.

This is optional in Phase 2B+5c.

def export_e2e_lane_route_for_chart_from_env(
    env,
    *,
    product_name: str,
    leaf_node: str,
    output_path: str = "data/e2e_lane_route.csv",
) -> str:
    """
    Export route and return output path if rows were generated.
    """

This can be left for a later phase if it adds complexity.

7. Manual Usage

After python -m main and Run Full Plan, once env is available inside runtime code:

from pysi.reporting.e2e_lane_route_runtime import export_e2e_lane_route_from_env

rows = export_e2e_lane_route_from_env(
    env,
    product_name="IPHONE_NM_2028_BASE",
    leaf_node="CS_US_MAINSTREAM",
    output_path="data/e2e_lane_route.csv",
)

Expected output:

data/e2e_lane_route.csv

Then chart generation can use:

from pysi.reporting.price_propagation_chart import generate_price_waterfall_stacked_bar

generate_price_waterfall_stacked_bar(
    "data/node_price_waterfall.csv",
    "outputs/reporting_mvp/price_propagation",
    product="IPHONE_NM_2028_BASE",
    leaf_node="CS_US_MAINSTREAM",
    e2e_lane_route_csv="data/e2e_lane_route.csv",
    price_propagation_trace_csv="data/price_propagation_trace.csv",
    chart_mode="full_price",
    chart_scope="e2e_primary",
)
8. Relationship with Existing Exporter

Phase 2B+5c must not duplicate route construction logic.

Use existing exporter:

pysi/reporting/e2e_lane_route_exporter.py

Expected call:

    chart_scope="e2e_primary",
)
8. Relationship

from pysi.reporting.e2e_lane_route_exporter import export_e2e_lane_route

return export_e2e_lane_route(
product_name=product_name,
prod_tree_dict_IN=prod_tree_dict_IN,
prod_tree_dict_OT=prod_tree_dict_OT,
output_path=output_path,
leaf_node=leaf_node,
inbound_leaf_node=inbound_leaf_node,
supply_point_node=supply_point_node,
)


---

## 9. Runtime Integration Options

### Option A: Standalone runtime helper only

This is the preferred first implementation.

Add:

```text
pysi/reporting/e2e_lane_route_runtime.py

and tests.

No GUI changes.

Option B: Pipeline integration

Future phase may call route export automatically after money outputs are written.

Possible location:

pysi/core/wom_pipeline.py

This is not required in Phase 2B+5c.

Option C: GUI button

Future phase may add a GUI button:

Export E2E Lane Route

or:

Generate E2E Price Chart

This is not required in Phase 2B+5c.

10. Tests

Add focused tests.

Suggested file:

tests/reporting_test_e2e_lane_route_runtime.py
Test 1: export route from fake env

Given a fake env with:

env.prod_tree_dict_IN = {"PRODUCT_A": inbound_root}
env.prod_tree_dict_OT = {"PRODUCT_A": outbound_root}

When calling:

export_e2e_lane_route_from_env(
    env,
    product_name="PRODUCT_A",
    leaf_node="CS",
    output_path=temp_csv,
)

Expected:

CSV generated
rows returned
route contains MOM, supply_point, DAD, CS
Test 2: missing inbound tree falls back safely

Given:

env.prod_tree_dict_IN = {}
env.prod_tree_dict_OT = {"PRODUCT_A": outbound_root}

Expected:

route exported using outbound route only
no crash
remarks include inbound fallback
Test 3: missing outbound tree returns empty rows

Given:

env.prod_tree_dict_IN = {"PRODUCT_A": inbound_root}
env.prod_tree_dict_OT = {}

Expected:

no crash
rows may be inbound-only or empty depending on exporter behavior
Test 4: missing env attrs return empty rows safely

Given fake env with no prod_tree_dict_IN / prod_tree_dict_OT.

Expected:

returns []
does not crash
Test 5: product_name required

Given empty product_name.

Expected:

returns []
or raises ValueError with clear message

Choose one behavior and document it.

Recommended:

return []

for GUI safety.

11. Existing Tests Must Continue to Pass

Run:

PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py
PYTHONPATH=. pytest -q tests/reporting_test_price_propagation_chart.py
PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_exporter.py

New test:

PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_runtime.py

Combined:

PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py tests/evaluate_test_money_evaluator_node_price_formation.py tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py tests/reporting_test_price_propagation_chart.py tests/reporting_test_e2e_lane_route_exporter.py tests/reporting_test_e2e_lane_route_runtime.py
12. Example Future Manual Command

This phase may not provide a direct CLI, but the conceptual use is:

from pysi.reporting.e2e_lane_route_runtime import export_e2e_lane_route_from_env

export_e2e_lane_route_from_env(
    env,
    product_name="IPHONE_NM_2028_BASE",
    leaf_node="CS_US_MAINSTREAM",
    output_path="data/e2e_lane_route.csv",
)

Then:

from pysi.reporting.price_propagation_chart import generate_price_waterfall_stacked_bar

generate_price_waterfall_stacked_bar(
    "data/node_price_waterfall.csv",
    "outputs/reporting_mvp/price_propagation",
    product="IPHONE_NM_2028_BASE",
    leaf_node="CS_US_MAINSTREAM",
    e2e_lane_route_csv="data/e2e_lane_route.csv",
    price_propagation_trace_csv="data/price_propagation_trace.csv",
    chart_mode="full_price",
    chart_scope="e2e_primary",
)
13. Documentation Note

Add:

docs/notes/mosd_phase2b5c_runtime_env_e2e_lane_route_export_260503.md

Suggested content:

# MOSD Phase 2B+5c Runtime Env E2E Lane Route Export

## Purpose

Provide a runtime helper to export e2e_lane_route.csv from WOM env.

## Background

Phase 2B+5a added a PlanNode-tree-based E2E lane route exporter.

Phase 2B+5b made the chart generator consume e2e_lane_route.csv.

Phase 2B+5c connects the exporter to WOM runtime env.

## Implemented behavior

- Read env.prod_tree_dict_IN.
- Read env.prod_tree_dict_OT.
- Export e2e_lane_route.csv for selected product and leaf node.
- Reuse existing e2e_lane_route_exporter.
- Do not change money evaluation or planner behavior.

## Not included

- GUI button
- automatic pipeline hook
- Management Cockpit integration
- chart auto-generation
- fan-in E2E lane export

## Testing

List test commands and results.
14. Acceptance Criteria

Phase 2B+5c is accepted when:

pysi/reporting/e2e_lane_route_runtime.py exists.
It exposes export_e2e_lane_route_from_env(...).
It reads env.prod_tree_dict_IN.
It reads env.prod_tree_dict_OT.
It calls existing export_e2e_lane_route(...).
It can export data/e2e_lane_route.csv.
It supports selected product_name.
It supports selected leaf_node.
It supports optional inbound_leaf_node.
It handles missing env attrs safely.
New runtime tests pass.
Existing Phase 2B tests pass.
Existing chart tests pass.
No money evaluation logic is changed.
No planner behavior is changed.
No GUI behavior is changed.
No committed master CSV fixtures are changed.
15. Future Phase 2B+5d

Possible next phase:

Phase 2B+5d: One-shot E2E Lane Price Chart Command

This would provide a single function:

generate_e2e_lane_price_chart_from_env(
    env,
    product_name="IPHONE_NM_2028_BASE",
    leaf_node="CS_US_MAINSTREAM",
)

that performs:

1. export e2e_lane_route.csv
2. generate full_price chart
3. generate delta_only chart
4. return generated PNG paths

This is not part of Phase 2B+5c.

16. Summary

Phase 2B+5c makes E2E lane route export practical in WOM runtime.

The key transition is:

Before:
  e2e_lane_route_exporter requires caller to manually pass prod_tree_dict_IN/OT

After:
  export_e2e_lane_route_from_env(env, product_name, leaf_node)
  can export e2e_lane_route.csv directly from WOM runtime env

This prepares the next step toward a one-shot E2E Lane Price & Cost Structure chart generation flow.