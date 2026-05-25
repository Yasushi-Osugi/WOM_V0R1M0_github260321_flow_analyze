# with Capacity PSI Planning Engine v0.7 Design
## Smoke Capacity Report Runner

## 1. Purpose

This document defines the v0.7 design of the **with Capacity PSI Planning Engine**.

v0.1 introduced the additive `pysi.capacity` package.

v0.2 verified dummy-node PSI list integration.

v0.3 verified real-WOM-compatible node compatibility.

v0.4 verified small Outbound Tree processing using PreOrder traversal.

v0.5 verified small Inbound Tree processing using PostOrder traversal.

v0.6 introduced an optional capacity report hook:

```python
run_capacity_report_hook()

v0.7 takes the next step:

Add a manually executable smoke runner for the optional capacity report hook.

The purpose is to confirm that the capacity report hook can be executed from a simple script and can generate:

outputs/capacity/smoke/capacity_usage.csv
outputs/capacity/smoke/capacity_violation.csv

This is still not full Run Full Plan integration.

2. Development Stage

The staged development flow is:

v0.1:
    Build the capacity gate.

v0.2:
    Pass dummy lots through the gate.

v0.3:
    Pass real-WOM-compatible lots through the gate.

v0.4:
    Pass lots through a small Outbound Tree.

v0.5:
    Pass lots through a small Inbound Tree.

v0.6:
    Add optional capacity report hook after existing planning pipeline.

v0.7:
    Add manually executable smoke runner for the capacity report hook.

v0.8:
    Connect capacity report hook to an existing WOM sample runner or pipeline option.

v0.7 is still a smoke-runner step.

3. Core Concept

The core WOM concept remains unchanged:

Weekly WOM with Capacity
= lot_ID list operation under capacity constraints

v0.7 must not convert WOM PSI into pure numeric PSI calculation.

The smoke runner should create small PSI lot_ID list structures and pass them to run_capacity_report_hook().

4. Design Principle

v0.7 follows this principle:

Do not modify existing Run Full Plan.

Do not modify existing GUI.

Do not replace existing Forward Planning.

Add a standalone smoke runner that can be manually executed.

The smoke runner is a safe trial button for the capacity report hook.

5. Scope of v0.7
5.1 In Scope

v0.7 should implement:

A standalone smoke runner script.
Creation of a small Outbound Tree.
Creation of a small Inbound Tree.
Creation of a temporary or local capacity master CSV.
Execution of run_capacity_report_hook().
Export of:
capacity_usage.csv
capacity_violation.csv
Console summary output.
A lightweight pytest smoke test for the runner if practical.
Existing v0.1 through v0.6 tests must still pass.
5.2 Out of Scope

v0.7 does not implement:

Run Full Plan integration
GUI integration
management cockpit integration
optimizer integration
alternative MOM allocation
alternative lane selection
costing integration
event flow tracing integration
database integration
real scenario master integration

v0.7 is only a manual smoke runner.

6. Recommended New File

Recommended file:

tools/smoke_capacity_report_hook.py

Alternative acceptable location:

pysi/capacity/smoke_capacity_report_hook.py

Preferred location is:

tools/smoke_capacity_report_hook.py

because this is an executable development utility rather than a production module.

7. Smoke Runner Overview

The smoke runner should:

Build a small outbound tree:
MOM_TEST
    ↓
DAD_TEST
    ↓
MKT_TEST
Build a small inbound tree:
MOM_IN_TEST
├── RAW_A_TEST
└── RAW_B_TEST
Place lot_ID lists in psi4demand and psi4supply.
Create a capacity master CSV.
Call:
run_capacity_report_hook(
    enabled=True,
    scenario_id="BASE",
    product_name="TEST_PRODUCT",
    weeks=["2026-W01"],
    outbound_root=outbound_root,
    inbound_root=inbound_root,
    capacity_master_path=capacity_master_path,
    output_dir="outputs/capacity/smoke",
)
Print a summary to console.
Exit with code 0 when successful.
8. Recommended Smoke Node Class

The smoke runner may define a small local node class.

class SmokeTreeNode:
    def __init__(self, name: str):
        self.name = name
        self.children = []
        self.psi4demand = {}
        self.psi4supply = {}

    def add_child(self, child):
        self.children.append(child)

    def init_week(self, week):
        self.psi4demand[week] = [[], [], [], []]
        self.psi4supply[week] = [[], [], [], []]

PSI index meaning:

Index	Symbol	Meaning
0	S	Ship / Sales / Supply
1	CO	Carry Over
2	I	Inventory
3	P	Production / Purchase
9. Outbound Smoke Tree
9.1 Structure
MOM_TEST
    ↓
DAD_TEST
    ↓
MKT_TEST
9.2 Construction
mom = SmokeTreeNode("MOM_TEST")
dad = SmokeTreeNode("DAD_TEST")
mkt = SmokeTreeNode("MKT_TEST")

mom.add_child(dad)
dad.add_child(mkt)
9.3 PSI Lot Placement
week = "2026-W01"

mom.psi4demand[week][3] = ["P1", "P2", "P3", "P4", "P5"]
dad.psi4supply[week][2] = ["I1", "I2", "I3", "I4"]
mkt.psi4demand[week][0] = ["S1", "S2", "S3", "S4"]

Expected capacity collisions:

MOM_TEST / P_cap overflow
DAD_TEST / I_cap soft overflow
MKT_TEST / S_cap overflow
10. Inbound Smoke Tree
10.1 Structure
MOM_IN_TEST
├── RAW_A_TEST
└── RAW_B_TEST
10.2 Construction
mom_in = SmokeTreeNode("MOM_IN_TEST")
raw_a = SmokeTreeNode("RAW_A_TEST")
raw_b = SmokeTreeNode("RAW_B_TEST")

mom_in.add_child(raw_a)
mom_in.add_child(raw_b)
10.3 PSI Lot Placement
week = "2026-W01"

raw_a.psi4demand[week][3] = ["PA1", "PA2", "PA3", "PA4", "PA5"]
raw_b.psi4demand[week][0] = ["SB1", "SB2", "SB3", "SB4"]
mom_in.psi4supply[week][2] = ["IM1", "IM2", "IM3", "IM4"]

Expected capacity collisions:

RAW_A_TEST / P_cap overflow
RAW_B_TEST / S_cap overflow
MOM_IN_TEST / I_cap soft overflow
11. Capacity Master CSV

The smoke runner should create a capacity master CSV under a smoke output or temporary directory.

Recommended path:

outputs/capacity/smoke/capacity_master_smoke.csv

Recommended content:

scenario_id,node_name,product_name,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
BASE,MOM_TEST,TEST_PRODUCT,2026-W01,P,3,soft,LOT,100,STD_CAL,smoke outbound MOM P cap
BASE,DAD_TEST,TEST_PRODUCT,2026-W01,I,3,soft,LOT,100,STD_CAL,smoke outbound DAD I cap
BASE,MKT_TEST,TEST_PRODUCT,2026-W01,S,2,soft,LOT,100,STD_CAL,smoke outbound MKT S cap
BASE,RAW_A_TEST,TEST_PRODUCT,2026-W01,P,3,soft,LOT,100,STD_CAL,smoke inbound RAW_A P cap
BASE,RAW_B_TEST,TEST_PRODUCT,2026-W01,S,2,soft,LOT,100,STD_CAL,smoke inbound RAW_B S cap
BASE,MOM_IN_TEST,TEST_PRODUCT,2026-W01,I,3,soft,LOT,100,STD_CAL,smoke inbound MOM I cap
12. Output Files

The smoke runner should generate:

outputs/capacity/smoke/capacity_usage.csv
outputs/capacity/smoke/capacity_violation.csv

These files should include both:

tree_side = OUTBOUND
tree_side = INBOUND
13. Console Output

The smoke runner should print a short summary.

Recommended output:

Capacity report hook smoke runner completed.
Scenario: BASE
Product: TEST_PRODUCT
Weeks: 2026-W01

Usage records: <count>
Violation records: <count>

Output files:
  outputs/capacity/smoke/capacity_usage.csv
  outputs/capacity/smoke/capacity_violation.csv

It should also print a warning or clear message if no records were generated.

14. Recommended Command

The runner should be executable from repository root as:

set PYTHONPATH=.
python tools/smoke_capacity_report_hook.py

For PowerShell:

$env:PYTHONPATH="."
python tools/smoke_capacity_report_hook.py

For Unix-like shells:

PYTHONPATH=. python tools/smoke_capacity_report_hook.py
15. Optional Test File

A lightweight test may be added if practical.

Recommended file:

tests/test_capacity_report_hook_smoke_runner.py

This test should verify that:

The smoke runner can be imported.
The runner main function can execute with a temporary output directory if supported.
Usage and violation files are created.
The runner does not modify existing WOM planning paths.

However, v0.7 may be considered complete with only the manual smoke runner if adding a test would make the runner unnecessarily complex.

16. Recommended Function Structure

The smoke runner should avoid putting all logic directly under if __name__ == "__main__".

Recommended structure:

def main(output_dir: str | Path = "outputs/capacity/smoke") -> tuple[int, int]:
    ...
    return len(usage_records), len(violation_records)


if __name__ == "__main__":
    main()

This makes the runner testable without executing it as a subprocess.

17. Compatibility Requirements

The implementation should preserve all existing v0.1 through v0.6 tests.

Expected command:

PYTHONPATH=. pytest -q \
  tests/test_capacity_planning_basic.py \
  tests/test_capacity_planning_dummy_node.py \
  tests/test_capacity_planning_real_node.py \
  tests/test_capacity_planning_small_outbound_tree.py \
  tests/test_capacity_planning_small_inbound_tree.py \
  tests/test_capacity_report_hook.py

On Windows command prompt:

set PYTHONPATH=.
pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py tests/test_capacity_planning_real_node.py tests/test_capacity_planning_small_outbound_tree.py tests/test_capacity_planning_small_inbound_tree.py tests/test_capacity_report_hook.py

The smoke runner should also run manually:

set PYTHONPATH=.
python tools/smoke_capacity_report_hook.py
18. Minimal Fix Policy

If v0.7 testing reveals small issues, minimal fixes are allowed.

Allowed fixes:

- add tools/smoke_capacity_report_hook.py
- add a small helper function inside the smoke runner
- create output directories if needed
- write capacity master smoke CSV
- preserve existing v0.1 through v0.6 tests

Not allowed:

- replacing existing Forward Planning
- modifying Run Full Plan behavior
- modifying GUI
- modifying costing modules
- modifying event extraction modules
- adding optimization
- redesigning scenario master
19. Completion Criteria

v0.7 is complete when:

tools/smoke_capacity_report_hook.py is added.
The smoke runner creates small outbound and inbound trees.
The smoke runner creates or writes a smoke capacity master CSV.
The smoke runner calls run_capacity_report_hook().
The smoke runner exports capacity_usage.csv.
The smoke runner exports capacity_violation.csv.
The smoke runner prints a useful console summary.
Manual execution succeeds.
Existing v0.1 through v0.6 tests still pass.
No existing WOM execution path is changed.
20. Future Pipeline Integration

v0.7 only adds a manual smoke runner.

A later version may integrate the capacity report hook into an existing WOM sample runner or planning pipeline using a disabled-by-default option:

enable_capacity_report = False

Then:

if enable_capacity_report:
    run_capacity_report_hook(...)

That is not part of v0.7.

21. Design Summary

v0.7 introduces a manually executable smoke runner for the optional capacity report hook.

It still does not connect to Run Full Plan.

It proves this:

The capacity report hook can be executed outside pytest
and can generate capacity usage / violation CSV reports.

In WOM terms:

v0.1:
    The capacity gate was built.

v0.2:
    Dummy lots passed through the gate.

v0.3:
    Real-WOM-compatible lots passed through the gate.

v0.4:
    Lots passed through a small outbound road with multiple gates.

v0.5:
    Lots passed through a small inbound Fan-In road with multiple gates.

v0.6:
    A capacity checkpoint was placed after the existing planning road.

v0.7:
    A manual test button is added for the capacity checkpoint.

The first goal is still not optimization.

The first goal is to make capacity collision visible at the Lot level through a manually executable smoke runner.