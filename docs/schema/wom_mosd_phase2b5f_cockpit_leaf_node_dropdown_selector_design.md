# WOM MOSD Phase 2B+5f Cockpit Leaf Node Dropdown Selector Design

## 1. Purpose

Phase 2B+5f defines the design for adding a product-aware leaf node dropdown selector to the WOM cockpit.

Phase 2B+5e added a cockpit GUI adapter:

```text
Price & Cost Structure

that asks the user to manually enter a market leaf node.

Phase 2B+5f improves this by replacing manual leaf node input with a dropdown selector.

The key purpose is:

current selected product
→ product-specific outbound PlanNode tree
→ valid leaf nodes for that product
→ dropdown selector
→ Price & Cost Structure chart generation

This reduces user input errors and prevents users from selecting leaf nodes that do not belong to the selected product.

2. Background

WOM has two node worlds.

2.1 Physical / GUI node world

This layer is used for:

NetworkX display
World map display
E2E physical network display
GUI node selection

Typical attributes include:

env.root_node_outbound
env.nodes_outbound
env.leaf_nodes_out

env.leaf_nodes_out is useful, but it may represent the physical outbound tree and can include leaf nodes not valid for the currently selected product.

2.2 Product-specific planning node world

This layer is product-specific and should be the primary source for leaf node candidates.

Typical attributes:

env.prod_tree_dict_OT[product_name]
env.prod_tree_dict_IN[product_name]

For the Price & Cost Structure chart, the selected lane is defined by:

Product × Leaf Node

Therefore the leaf node dropdown should be based on the current product's outbound PlanNode tree.

3. Problem Statement

Current Phase 2B+5e behavior:

User clicks Price & Cost Structure
→ GUI asks user to type leaf_node manually

This works but has drawbacks:

Users can mistype node names.
Users may enter a node that does not exist.
Users may enter a physical leaf node that is not valid for the selected product.
It is difficult to know which leaf nodes are valid for the selected product.

Using env.leaf_nodes_out directly is not ideal because it may be product-independent.

The dropdown should show product-specific leaf nodes where possible.

4. Scope
In scope
Add a leaf node dropdown selector to cockpit_tk.py.
Populate the dropdown based on the currently selected product.
Prefer product-specific outbound PlanNode tree leaves.
Fallback to env.leaf_nodes_out if product-specific leaves are unavailable.
Fallback to price_propagation_trace.csv if both are unavailable.
Use selected dropdown value when generating Price & Cost Structure charts.
Preserve the existing Price & Cost Structure button.
Keep GUI adapter thin.
Add documentation note under docs/notes.
Add small helper tests if feasible.
Not in scope
Rewriting cockpit layout.
Embedded chart display.
Interactive chart viewer.
Management Cockpit integration.
Changing price / cost calculation.
Changing PlanNode tree construction.
Changing money evaluation logic.
Changing planner behavior.
Changing master CSV fixtures.
Fan-in E2E lane chart.
Leaf node multi-select.
5. Design Principle

The dropdown candidate source should follow this priority:

1. Product-specific outbound PlanNode tree leaves
2. env.leaf_nodes_out
3. price_propagation_trace.csv to_node values

Reason:

Product-specific PlanNode tree is the most accurate source for the selected product.
env.leaf_nodes_out is useful fallback but may be product-independent.
price_propagation_trace.csv is useful runtime output fallback.

The GUI should not contain heavy tree traversal logic.

If practical, place candidate extraction helper in a reporting or GUI-support module.

However, a small local adapter in cockpit_tk.py is acceptable if it remains thin.

6. Proposed UI Behavior
6.1 Add leaf node dropdown

Add a dropdown near existing product / node / step / direction controls.

Suggested label:

Leaf:

Suggested Tk variable:

self.var_leaf_node = tk.StringVar()

Suggested widget:

self.cmb_leaf_node = ttk.Combobox(
    ...,
    textvariable=self.var_leaf_node,
    values=[],
    width=24,
    state="readonly",
)
6.2 Product change updates leaf dropdown

When selected product changes:

current product changes
→ recompute leaf node candidates
→ update leaf dropdown values
→ select first candidate if available

If no candidates exist:

dropdown values = []
var_leaf_node = ""
6.3 Price & Cost Structure uses dropdown value

When user clicks:

Price & Cost Structure

use:

leaf_node = (self.var_leaf_node.get() or "").strip()

If blank, fallback to simple dialog is acceptable, but preferred first behavior is to show a warning:

Please select a leaf node.
7. Leaf Node Candidate Extraction
7.1 Preferred source: product-specific outbound PlanNode tree

Use:

env.prod_tree_dict_OT[product_name]

Then walk the tree and collect nodes that have no children.

A leaf node is:

PlanNode with no children

Node name priority:

name
node_name
node_id

Children priority:

children
child_nodes

Support list/tuple and dict child containers.

Pseudo-code:

def collect_leaf_nodes_from_product_outbound_tree(env, product_name):
    prod_tree_dict_OT = getattr(env, "prod_tree_dict_OT", {}) or {}
    root = prod_tree_dict_OT.get(product_name)
    if root is None:
        return []

    leaves = []
    for node in walk_plan_tree(root):
        children = get_plan_children(node)
        if not children:
            name = get_plan_node_name(node)
            if name:
                leaves.append(name)

    return sorted_unique(leaves)
7.2 Fallback source: env.leaf_nodes_out

If product-specific leaves are empty, use:

env.leaf_nodes_out

This may contain strings or node objects.

Name extraction priority:

name
node_name
node_id
str(node)

Pseudo-code:

def collect_leaf_nodes_from_env_leaf_nodes_out(env):
    raw = getattr(env, "leaf_nodes_out", []) or []
    return sorted_unique(extract_name(x) for x in raw)
7.3 Fallback source: price_propagation_trace.csv

If both previous sources are empty, use:

data/price_propagation_trace.csv

Filter by selected product if possible.

Candidate logic:

to_node values that do not appear as from_node

This approximates downstream leaf nodes.

Optional filter:

direction == outbound

But do not over-filter if direction is missing.

8. Suggested Helper Location

Preferred lightweight helper module:

pysi/reporting/leaf_node_candidates.py

Suggested primary function:

def get_leaf_node_candidates_for_product(
    env,
    *,
    product_name: str,
    price_propagation_trace_csv: str = "data/price_propagation_trace.csv",
) -> list[str]:
    """
    Return leaf node candidates for the selected product.

    Priority:
      1. product-specific outbound PlanNode tree leaves
      2. env.leaf_nodes_out
      3. price_propagation_trace.csv leaf candidates
    """

Suggested helpers:

def collect_leaf_nodes_from_product_outbound_tree(env, product_name: str) -> list[str]:
    ...

def collect_leaf_nodes_from_env_leaf_nodes_out(env) -> list[str]:
    ...

def collect_leaf_nodes_from_price_trace_csv(path: str, product_name: str) -> list[str]:
    ...

def get_plan_node_name(node) -> str:
    ...

def get_plan_children(node) -> list:
    ...

This keeps cockpit_tk.py thin.

9. cockpit_tk.py Changes
9.1 Add Tk variable

In cockpit initialization:

self.var_leaf_node = tk.StringVar()
9.2 Add combobox

Add near product selector:

ttk.Label(top_frame, text="Leaf:").pack(...)
self.cmb_leaf_node = ttk.Combobox(
    top_frame,
    textvariable=self.var_leaf_node,
    values=[],
    width=24,
    state="readonly",
)
self.cmb_leaf_node.pack(...)

Actual layout should follow existing cockpit style.

9.3 Update leaf dropdown method

Add method:

def refresh_leaf_node_dropdown(self):
    product_name = (self.var_product.get() or "").strip()
    if not product_name:
        self.cmb_leaf_node["values"] = []
        self.var_leaf_node.set("")
        return

    try:
        from pysi.reporting.leaf_node_candidates import (
            get_leaf_node_candidates_for_product,
        )

        candidates = get_leaf_node_candidates_for_product(
            self.env,
            product_name=product_name,
        )
    except Exception as e:
        print(f"[price-cost-structure] leaf dropdown refresh skipped: {e}")
        candidates = []

    self.cmb_leaf_node["values"] = candidates
    if candidates:
        if self.var_leaf_node.get() not in candidates:
            self.var_leaf_node.set(candidates[0])
    else:
        self.var_leaf_node.set("")
9.4 Bind product selector change

When product combobox selection changes, call:

self.refresh_leaf_node_dropdown()

If product selector already has a callback, add this call inside the existing callback.

If not, bind:

self.cmb_product.bind("<<ComboboxSelected>>", lambda e: self.refresh_leaf_node_dropdown())

Actual widget name may differ. Codex should inspect current cockpit_tk.py.

9.5 Use selected leaf in Price & Cost Structure

Update:

leaf_node = simpledialog.askstring(...)

to:

leaf_node = (self.var_leaf_node.get() or "").strip()
if not leaf_node:
    messagebox.showwarning(
        "Price & Cost Structure",
        "Please select a leaf node.",
    )
    return

Optional fallback:

If dropdown is empty, askstring may still be used.

Preferred first behavior:

use dropdown only
10. Error Handling
10.1 No product

Show:

Please select a product.
10.2 No leaf node candidates

Show:

No leaf node candidates found for selected product.
10.3 Leaf node blank

Show:

Please select a leaf node.
10.4 Candidate extraction failure

Print debug log and leave dropdown empty.

Do not crash GUI.

11. Manual Verification
Start WOM:
python -m main
Select product:
IPHONE_NM_2028_BASE
Confirm leaf dropdown is populated.

Expected examples:

CS_CN_PREMIUM
CS_DE_PREMIUM
CS_IN_ASPIRER
CS_JP_REPLACEMENT
CS_UK_MAINSTREAM
CS_US_MAINSTREAM
CS_US_PREMIUM
Select:
CS_US_MAINSTREAM
Run Full Plan if needed.
Click:
Price & Cost Structure
Confirm charts are generated and paths shown.
12. Tests
12.1 Candidate helper tests

Add test file:

tests/reporting_test_leaf_node_candidates.py

Recommended tests:

Test 1: product-specific PlanNode leaves

Given fake PlanNode tree:

supply_point
→ DAD
→ CS_A
→ CS_B

Expected:

CS_A
CS_B
Test 2: fallback to env.leaf_nodes_out

Given no product tree, but:

env.leaf_nodes_out = ["CS_A", "CS_B"]

Expected:

CS_A
CS_B
Test 3: fallback to price_propagation_trace.csv

Given trace:

supply_point → DAD
DAD → CS_A
DAD → CS_B

Expected candidates:

CS_A
CS_B
Test 4: product filter in trace fallback

Given multiple products in trace, return only leaf nodes for selected product.

Test 5: sorted unique output

Ensure duplicate nodes are removed and output order is stable.

12.2 GUI tests

Only add GUI test if existing repo has lightweight cockpit GUI testing.

If heavy, skip GUI automated tests and rely on manual verification.

13. Existing Tests Must Continue to Pass

Recommended commands:

PYTHONPATH=. pytest -q tests/reporting_test_leaf_node_candidates.py
PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_price_chart_runtime.py
PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_runtime.py
PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_exporter.py
PYTHONPATH=. pytest -q tests/reporting_test_price_propagation_chart.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py

Combined:

PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py tests/evaluate_test_money_evaluator_node_price_formation.py tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py tests/reporting_test_price_propagation_chart.py tests/reporting_test_e2e_lane_route_exporter.py tests/reporting_test_e2e_lane_route_runtime.py tests/reporting_test_e2e_lane_price_chart_runtime.py tests/reporting_test_leaf_node_candidates.py
14. Documentation Note

Add:

docs/notes/mosd_phase2b5f_cockpit_leaf_node_dropdown_selector_260504.md

Suggested content:

# MOSD Phase 2B+5f Cockpit Leaf Node Dropdown Selector

## Purpose

Replace manual leaf node input with a product-aware dropdown selector in the cockpit.

## Background

Phase 2B+5e added a Price & Cost Structure button that asks the user to type a leaf node.

Phase 2B+5f populates valid leaf nodes for the currently selected product.

## Implemented behavior

- Add leaf node dropdown.
- Resolve leaf candidates from product-specific outbound PlanNode tree first.
- Fallback to env.leaf_nodes_out.
- Fallback to price_propagation_trace.csv.
- Use selected leaf node when generating Price & Cost Structure charts.
- Keep reporting logic outside cockpit_tk.py.

## Not included

- Embedded chart viewer
- Management Cockpit integration
- fan-in E2E lane selector
- inbound source selector
- chart display inside GUI

## Testing

List test commands and manual verification.
15. Acceptance Criteria

Phase 2B+5f is accepted when:

Cockpit has a leaf node dropdown selector.
Leaf dropdown updates according to selected product.
Candidate source priority is:
product outbound PlanNode tree
env.leaf_nodes_out
price_propagation_trace.csv
Price & Cost Structure button uses selected dropdown leaf node.
Manual leaf node typing is no longer required for normal use.
Existing one-shot reporting helper is still used.
Reporting logic remains outside cockpit_tk.py.
Candidate helper tests pass.
Existing Phase 2B reporting tests pass.
Existing Phase 2B evaluator tests pass.
No money evaluation logic is changed.
No planner behavior is changed.
No committed master CSV fixtures are changed.
16. Future Phase 2B+5g

Possible next improvements:

auto-open generated PNG file
auto-open output folder
show first chart inside a lightweight image viewer
add inbound source selector
add fan-in mode selector
add chart mode toggles
add Management Cockpit link
17. Summary

Phase 2B+5f improves cockpit usability by replacing manual leaf node input with a product-aware dropdown.

The key rule is:

Use product-specific outbound PlanNode tree leaves first.
Use env.leaf_nodes_out only as fallback.

This prevents product-irrelevant physical leaf nodes from confusing the user and makes the Price & Cost Structure cockpit action practical for normal use.