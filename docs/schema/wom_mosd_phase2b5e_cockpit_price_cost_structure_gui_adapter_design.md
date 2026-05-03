# WOM MOSD Phase 2B+5e Cockpit Price & Cost Structure GUI Adapter Design

## 1. Purpose

Phase 2B+5e defines the design for adding a thin GUI adapter to `cockpit_tk.py` so that WOM users can generate E2E Lane Price & Cost Structure charts from the GUI.

Previous phases prepared the reporting logic outside the GUI:

```text
Phase 2B+5a:
  PlanNode tree → e2e_lane_route.csv

Phase 2B+5b:
  e2e_lane_route.csv → chart X-axis ordering

Phase 2B+5c:
  runtime env → e2e_lane_route.csv

Phase 2B+5d:
  runtime env → route export → full_price chart + delta_only chart

Phase 2B+5e adds a GUI entry point:

Price & Cost Structure

The GUI should call:

generate_e2e_lane_price_chart_from_env(...)

and display or log the generated PNG file paths.

This phase must keep GUI changes thin.

2. Background

The one-shot reporting helper now exists:

pysi/reporting/e2e_lane_price_chart_runtime.py

Expected function:

generate_e2e_lane_price_chart_from_env(
    env,
    product_name="IPHONE_NM_2028_BASE",
    leaf_node="CS_US_MAINSTREAM",
)

This helper performs:

1. export e2e_lane_route.csv from env
2. generate full_price E2E lane chart
3. generate delta_only E2E lane chart
4. return generated PNG paths and route rows

Therefore, cockpit_tk.py does not need to know the details of:

PlanNode tree traversal
route stitching
e2e_lane_route.csv format
chart component selection
matplotlib rendering

It only needs to collect user inputs and call the helper.

3. Scope
In scope
Add a thin GUI adapter in pysi/gui/cockpit_tk.py.
Add a GUI button or menu entry labeled:
Price & Cost Structure
Get selected product from the existing product selector.
Get leaf node from a simple input mechanism.
Call generate_e2e_lane_price_chart_from_env(...).
Print generated file paths to console or GUI log.
Optionally open the generated PNG folder or first PNG file.
Add minimal tests if existing GUI test structure allows.
Add implementation note under docs/notes.
Not in scope
Rewriting GUI layout.
Embedding the PNG chart inside Tkinter canvas.
Adding interactive chart viewer.
Adding Management Cockpit integration.
Changing money evaluation logic.
Changing price formation logic.
Changing purchase cost propagation logic.
Changing PSI planning logic.
Modifying committed master CSV fixtures.
Implementing fan-in E2E lane chart.
Implementing target costing / downward propagation.
4. Design Principle

cockpit_tk.py should remain a caller, not an owner of reporting logic.

The GUI adapter should do only this:

1. read current product
2. read or ask for leaf node
3. call reporting helper
4. show result paths

The reporting body remains here:

pysi/reporting/e2e_lane_price_chart_runtime.py
pysi/reporting/e2e_lane_route_runtime.py
pysi/reporting/e2e_lane_route_exporter.py
pysi/reporting/price_propagation_chart.py

This keeps GUI thin and future-proof.

5. Proposed GUI Behavior
5.1 User action

User clicks:

Price & Cost Structure

from the WOM cockpit.

5.2 GUI asks for leaf node

Initial implementation can use a simple input dialog:

Enter market leaf node:

Example:

CS_US_MAINSTREAM

Default value may be blank or a known sample value.

5.3 Product selection

Use the currently selected product from the existing product selector.

Conceptual code:

product_name = (self.var_product.get() or "").strip()
5.4 Helper call

Call:

from pysi.reporting.e2e_lane_price_chart_runtime import (
    generate_e2e_lane_price_chart_from_env,
)

result = generate_e2e_lane_price_chart_from_env(
    self.env,
    product_name=product_name,
    leaf_node=leaf_node,
)
5.5 Output handling

If success:

Generated:
- full_price PNG
- delta_only PNG

Show file paths using one or more of:

print(...)
status label
messagebox
existing log panel if available

If errors:

show error message
do not crash GUI
6. Proposed Function in cockpit_tk.py

Add a method inside the cockpit class:

def on_generate_price_cost_structure_chart(self):
    """
    Generate E2E Lane Price & Cost Structure charts for the current product.

    Thin GUI adapter only:
    - get product_name
    - get leaf_node
    - call reporting helper
    - show generated paths / errors
    """

Pseudo-code:

def on_generate_price_cost_structure_chart(self):
    product_name = (self.var_product.get() or "").strip()
    if not product_name:
        messagebox.showwarning("Price & Cost Structure", "Please select a product.")
        return

    leaf_node = simpledialog.askstring(
        "Price & Cost Structure",
        "Enter market leaf node:",
        parent=self,
    )
    leaf_node = (leaf_node or "").strip()
    if not leaf_node:
        return

    try:
        from pysi.reporting.e2e_lane_price_chart_runtime import (
            generate_e2e_lane_price_chart_from_env,
        )

        result = generate_e2e_lane_price_chart_from_env(
            self.env,
            product_name=product_name,
            leaf_node=leaf_node,
        )

        errors = result.get("errors") or []
        warnings = result.get("warnings") or []
        files = result.get("generated_files") or []

        if errors:
            messagebox.showerror(
                "Price & Cost Structure",
                "\n".join(str(e) for e in errors),
            )
            return

        msg_lines = []
        if files:
            msg_lines.append("Generated chart files:")
            msg_lines.extend(str(p) for p in files)
        else:
            msg_lines.append("No chart files were generated.")

        if warnings:
            msg_lines.append("")
            msg_lines.append("Warnings:")
            msg_lines.extend(str(w) for w in warnings)

        print("[price-cost-structure]", result)
        messagebox.showinfo(
            "Price & Cost Structure",
            "\n".join(msg_lines),
        )

    except Exception as e:
        print(f"[price-cost-structure] failed: {e}")
        messagebox.showerror("Price & Cost Structure", str(e))
7. Menu / Button Placement
Option A: Add button near reporting / cockpit actions

If there is an existing reporting button area, add:

Price & Cost Structure

next to Management Cockpit / Reporting MVP buttons.

Option B: Add menu item

If a menu bar exists, add under:

Reports
  → Price & Cost Structure
Option C: Add minimal temporary button

For first implementation, a button is enough:

ttk.Button(
    parent,
    text="Price & Cost Structure",
    command=self.on_generate_price_cost_structure_chart,
)

Preferred first implementation:

Option C or A

Keep the UI patch small.

8. Leaf Node Input
8.1 Initial implementation

Use simpledialog.askstring.

Reason:

minimal code
no need to add complex selector
avoids scanning all leaf nodes in GUI phase
8.2 Future improvement

Later, provide a dropdown selector populated from:

price_propagation_trace.csv
e2e_lane_route.csv
product tree leaves

This is not required in Phase 2B+5e.

9. Generated Files

The helper should generate or return paths like:

outputs/reporting_mvp/price_propagation/<product>_<leaf_node>_e2e_lane_price_cost_structure.png
outputs/reporting_mvp/price_propagation/<product>_<leaf_node>_e2e_lane_added_cost_structure_delta_only.png

It should also generate:

data/e2e_lane_route.csv

via runtime env route export.

10. Preconditions

For chart generation to work, the current run should already have generated:

data/node_price_waterfall.csv
data/price_propagation_trace.csv

Therefore, the GUI may show a warning if these are missing:

Please run Full Plan before generating Price & Cost Structure charts.

The one-shot helper already handles missing CSVs safely.
The GUI adapter can rely on helper errors, or add a pre-check if simple.

11. Error Handling
11.1 No product selected

Show warning:

Please select a product.
11.2 No leaf node entered

Do nothing or show light warning.

11.3 Missing runtime env

Show error from helper:

env is None
11.4 Missing data/node_price_waterfall.csv

Show error:

node_price_waterfall.csv not found. Please run Full Plan first.
11.5 No generated files

Show warning:

No chart files were generated.
11.6 Unexpected exception

Catch and show messagebox error.

12. Tests

GUI tests may be difficult if the repository does not already have a Tkinter GUI test structure.

Preferred test scope:

12.1 Unit test helper logic indirectly

The core logic is already covered by:

tests/reporting_test_e2e_lane_price_chart_runtime.py
12.2 GUI adapter smoke test if feasible

If cockpit class can be instantiated safely in test environment, add a minimal test that:

monkeypatches simpledialog.askstring
monkeypatches generate_e2e_lane_price_chart_from_env
verifies the helper is called with selected product and leaf node

Suggested test file only if feasible:

tests/gui_test_cockpit_price_cost_structure_adapter.py

If GUI instantiation is heavy, skip GUI test and keep implementation note.

For Phase 2B+5e, lack of GUI automated test is acceptable if the patch is small and manual verification is documented.

13. Manual Verification

After implementation:

Start WOM:
python -m main
Run Full Plan.
Select product:
IPHONE_NM_2028_BASE
Click:
Price & Cost Structure
Enter leaf node:
CS_US_MAINSTREAM
Confirm generated paths are shown.
Confirm output files exist:
dir outputs\reporting_mvp\price_propagation
dir data\e2e_lane_route.csv

Expected PNG files:

...e2e_lane_price_cost_structure.png
...e2e_lane_added_cost_structure_delta_only.png
14. Validation Commands

Existing tests should continue to pass:

PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_node_price_formation.py
PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py
PYTHONPATH=. pytest -q tests/reporting_test_price_propagation_chart.py
PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_exporter.py
PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_route_runtime.py
PYTHONPATH=. pytest -q tests/reporting_test_e2e_lane_price_chart_runtime.py

Combined:

PYTHONPATH=. pytest -q tests/evaluate_test_money_evaluator_purchase_cost_propagation.py tests/evaluate_test_money_evaluator_node_price_formation.py tests/evaluate_test_money_evaluator_price_waterfall_trace_export.py tests/reporting_test_price_propagation_chart.py tests/reporting_test_e2e_lane_route_exporter.py tests/reporting_test_e2e_lane_route_runtime.py tests/reporting_test_e2e_lane_price_chart_runtime.py
15. Acceptance Criteria

Phase 2B+5e is accepted when:

cockpit_tk.py has a small Price & Cost Structure GUI entry.
GUI entry gets currently selected product.
GUI entry asks for leaf node.
GUI entry calls generate_e2e_lane_price_chart_from_env(...).
Generated file paths are shown or logged.
Errors are shown safely.
No reporting logic is implemented directly inside cockpit_tk.py.
Existing reporting tests pass.
Existing Phase 2B evaluator tests pass.
No money evaluation logic is changed.
No planner behavior is changed.
No committed master CSV fixtures are changed.
16. Future Phase 2B+5f

Possible next improvements:

leaf node dropdown selector
open PNG automatically
open output folder automatically
show generated chart inside GUI
add Management Cockpit link
add “Generate Full + Delta” toggle
add inbound source selector
add fan-in E2E lane support
17. Summary

Phase 2B+5e adds the first GUI entry point for E2E Lane Price & Cost Structure visualization.

The key design principle is:

GUI calls reporting helper.
GUI does not own reporting logic.

This turns the reporting chain:

env
→ e2e_lane_route.csv
→ full_price chart
→ delta_only chart

into a user-facing cockpit action:

Price & Cost Structure