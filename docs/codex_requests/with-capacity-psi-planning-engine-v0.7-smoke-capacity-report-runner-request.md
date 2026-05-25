# Codex Request: with Capacity PSI Planning Engine v0.7
## Smoke Capacity Report Runner

## 1. Request Summary

Please implement v0.7 of the **with Capacity PSI Planning Engine**.

This request is based on the design document:

```text
docs/design/with-capacity-psi-planning-engine-v0.7-smoke-capacity-report-runner.md

v0.1 added the additive pysi.capacity package.

v0.2 added dummy-node PSI list integration tests.

v0.3 added real-WOM-compatible node tests.

v0.4 added small Outbound Tree integration tests.

v0.5 added small Inbound Tree integration tests.

v0.6 added the optional capacity report hook:

run_capacity_report_hook()

v0.7 should add a manually executable smoke runner that uses run_capacity_report_hook() and generates capacity report CSV files.

The key goal is:

Confirm that the optional capacity report hook can be executed manually
outside pytest and can generate capacity_usage.csv and capacity_violation.csv.

This is still not Run Full Plan integration.

Do not modify existing WOM planning behavior.

2. Current Branch

The target branch is:

feature/with-capacity-psi-engine-v0r1

Current completed stages:

v0.1:
    Capacity package skeleton
    Capacity dataclasses
    Capacity master loader
    Capacity planner utilities
    CSV exporters
    Basic tests

v0.2:
    DummyNode PSI list integration tests

v0.3:
    RealLikeNode compatibility tests

v0.4:
    Small Outbound Tree tests

v0.5:
    Small Inbound Tree tests

v0.6:
    Optional capacity report hook

v0.7 should build on the existing v0.6 implementation.

3. Important Concept

Please preserve the core WOM concept:

Monthly PSI on Capacity:
    numeric PSI calculation

Weekly WOM PSI with Capacity:
    lot_ID list operation under capacity constraints

The smoke runner must create and process PSI lot_ID lists.

Do not convert the weekly WOM PSI structure into pure numeric PSI calculations.

4. Required New File

Please add:

tools/smoke_capacity_report_hook.py

This script should be executable from the repository root.

Recommended command:

set PYTHONPATH=.
python tools/smoke_capacity_report_hook.py

For Unix-like shells:

PYTHONPATH=. python tools/smoke_capacity_report_hook.py
5. Required Behavior

The smoke runner should:

Create a small outbound tree.
Create a small inbound tree.
Place PSI lot_ID lists into psi4demand and psi4supply.
Create a smoke capacity master CSV.
Call run_capacity_report_hook().
Export:
outputs/capacity/smoke/capacity_usage.csv
outputs/capacity/smoke/capacity_violation.csv
Print a useful console summary.
Return counts of usage and violation records from a main() function.
6. Recommended Smoke Node Class

Please define a lightweight local node class inside the smoke runner.

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

0 = S
1 = CO
2 = I
3 = P
7. Outbound Smoke Tree

Create the following outbound tree:

MOM_TEST
    ↓
DAD_TEST
    ↓
MKT_TEST

Recommended construction:

mom = SmokeTreeNode("MOM_TEST")
dad = SmokeTreeNode("DAD_TEST")
mkt = SmokeTreeNode("MKT_TEST")

mom.add_child(dad)
dad.add_child(mkt)

Recommended PSI lot placement:

week = "2026-W01"

mom.psi4demand[week][3] = ["P1", "P2", "P3", "P4", "P5"]
dad.psi4supply[week][2] = ["I1", "I2", "I3", "I4"]
mkt.psi4demand[week][0] = ["S1", "S2", "S3", "S4"]

Expected capacity collisions:

MOM_TEST / P_cap overflow
DAD_TEST / I_cap soft overflow
MKT_TEST / S_cap overflow
8. Inbound Smoke Tree

Create the following inbound tree:

MOM_IN_TEST
├── RAW_A_TEST
└── RAW_B_TEST

Recommended construction:

mom_in = SmokeTreeNode("MOM_IN_TEST")
raw_a = SmokeTreeNode("RAW_A_TEST")
raw_b = SmokeTreeNode("RAW_B_TEST")

mom_in.add_child(raw_a)
mom_in.add_child(raw_b)

Recommended PSI lot placement:

week = "2026-W01"

raw_a.psi4demand[week][3] = ["PA1", "PA2", "PA3", "PA4", "PA5"]
raw_b.psi4demand[week][0] = ["SB1", "SB2", "SB3", "SB4"]
mom_in.psi4supply[week][2] = ["IM1", "IM2", "IM3", "IM4"]

Expected capacity collisions:

RAW_A_TEST / P_cap overflow
RAW_B_TEST / S_cap overflow
MOM_IN_TEST / I_cap soft overflow
9. Smoke Capacity Master CSV

The smoke runner should create the following file:

outputs/capacity/smoke/capacity_master_smoke.csv

Recommended content:

scenario_id,node_name,product_name,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
BASE,MOM_TEST,TEST_PRODUCT,2026-W01,P,3,soft,LOT,100,STD_CAL,smoke outbound MOM P cap
BASE,DAD_TEST,TEST_PRODUCT,2026-W01,I,3,soft,LOT,100,STD_CAL,smoke outbound DAD I cap
BASE,MKT_TEST,TEST_PRODUCT,2026-W01,S,2,soft,LOT,100,STD_CAL,smoke outbound MKT S cap
BASE,RAW_A_TEST,TEST_PRODUCT,2026-W01,P,3,soft,LOT,100,STD_CAL,smoke inbound RAW_A P cap
BASE,RAW_B_TEST,TEST_PRODUCT,2026-W01,S,2,soft,LOT,100,STD_CAL,smoke inbound RAW_B S cap
BASE,MOM_IN_TEST,TEST_PRODUCT,2026-W01,I,3,soft,LOT,100,STD_CAL,smoke inbound MOM I cap

The script should create parent directories if needed.

10. Hook Execution

The smoke runner should call:

usage_records, violation_records = run_capacity_report_hook(
    enabled=True,
    scenario_id="BASE",
    product_name="TEST_PRODUCT",
    weeks=["2026-W01"],
    outbound_root=outbound_root,
    inbound_root=inbound_root,
    capacity_master_path=capacity_master_path,
    output_dir=output_dir,
)

Expected output directory:

outputs/capacity/smoke

Expected output files:

outputs/capacity/smoke/capacity_usage.csv
outputs/capacity/smoke/capacity_violation.csv

The output files should include both:

tree_side = OUTBOUND
tree_side = INBOUND
11. Console Summary

The smoke runner should print a concise summary.

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

If no records are generated, print a clear warning message.

12. Recommended Function Structure

Please avoid putting all logic directly under if __name__ == "__main__".

Recommended structure:

from __future__ import annotations

from pathlib import Path

from pysi.capacity import run_capacity_report_hook


def main(output_dir: str | Path = "outputs/capacity/smoke") -> tuple[int, int]:
    ...
    return len(usage_records), len(violation_records)


if __name__ == "__main__":
    main()

This makes the smoke runner easier to test later.

13. Optional Test File

If practical, please add a lightweight test file:

tests/test_capacity_report_hook_smoke_runner.py

The test may verify:

The smoke runner can be imported.
main(tmp_path / "smoke") can execute.
capacity_usage.csv is created.
capacity_violation.csv is created.
Usage and violation counts are greater than zero.

This test is optional.

If adding this test would make the implementation too complex, do not add it in v0.7.

However, existing v0.1 through v0.6 tests must continue to pass.

14. Required Test Command

The following command must pass:

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

If tests/test_capacity_report_hook_smoke_runner.py is added, also include it in the test command.

15. Required Manual Smoke Command

The following command should run successfully from repository root:

set PYTHONPATH=.
python tools/smoke_capacity_report_hook.py

Expected result:

capacity_usage.csv created
capacity_violation.csv created
console summary printed
16. Minimal Fix Policy

If v0.7 testing reveals small issues, minimal fixes are allowed.

Allowed fixes:

- add tools/smoke_capacity_report_hook.py
- add tests/test_capacity_report_hook_smoke_runner.py if practical
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
17. Do Not Modify Existing WOM Pipeline

Please do not modify:

existing GUI files
existing costing modules
existing event extraction modules
existing non-capacity planning engine
existing Run Full Plan pipeline
existing sample scenario behavior

v0.7 is only a manual smoke runner.

18. Expected Completion Criteria

v0.7 is complete when:

tools/smoke_capacity_report_hook.py is added.
The smoke runner creates small outbound and inbound trees.
The smoke runner creates capacity_master_smoke.csv.
The smoke runner calls run_capacity_report_hook().
The smoke runner exports capacity_usage.csv.
The smoke runner exports capacity_violation.csv.
The smoke runner prints a useful console summary.
Manual execution succeeds.
Existing v0.1 through v0.6 tests still pass.
No existing WOM execution path is changed.

Optional completion:

tests/test_capacity_report_hook_smoke_runner.py is added and passes.
19. Notes for Codex

This is not Run Full Plan integration.

This is not GUI integration.

This is not optimization.

This is not costing integration.

This is a small, defensive, manually executable smoke runner.

The key goal is:

Confirm that the capacity report hook can be executed outside pytest
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

Please keep the implementation small, readable, additive, and safe.