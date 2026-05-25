# Codex Request: with Capacity PSI Planning Engine v0.2
## Dummy Node PSI List Integration Test

## 1. Request Summary

Please implement v0.2 of the **with Capacity PSI Planning Engine**.

This request is based on the design document:

```text
docs/design/with-capacity-psi-planning-engine-v0.2-dummy-node-test.md

v0.1 already added the additive pysi.capacity package:

pysi/capacity/__init__.py
pysi/capacity/capacity_model.py
pysi/capacity/capacity_master_loader.py
pysi/capacity/capacity_planning.py
pysi/capacity/capacity_exporter.py
pysi/master_data/capacity_master_sample.csv
tests/test_capacity_planning_basic.py

v0.2 should verify that the v0.1 capacity planning components can operate on an actual WOM-like PSI list structure using a dummy node.

The key concept is:

Monthly PSI on Capacity:
    numeric PSI calculation

Weekly WOM PSI with Capacity:
    lot_ID list operation

Therefore, the implementation must confirm that with_capacity_forward_planning() works with psi4demand and psi4supply list structures whose elements are lot_id.

2. Important Implementation Principle

This implementation must remain additive and test-focused.

Do not integrate with the real WOM Run Full Plan pipeline yet.

Do not modify the GUI.

Do not modify costing modules.

Do not modify event extraction modules.

Do not replace the existing non-capacity planning logic.

The purpose of v0.2 is only to validate the capacity planner using a dummy WOM-like node.

3. Target Branch

The target branch is:

feature/with-capacity-psi-engine-v0r1
4. Required New Test File

Please add the following test file:

tests/test_capacity_planning_dummy_node.py

This test file should define a simple DummyNode class inside the test file.

Recommended class:

class DummyNode:
    def __init__(self, name: str):
        self.name = name
        self.children = []
        self.psi4demand = {}
        self.psi4supply = {}

    def init_week(self, week):
        self.psi4demand[week] = [[], [], [], []]
        self.psi4supply[week] = [[], [], [], []]

PSI index meaning:

0 = S
1 = CO
2 = I
3 = P
5. Required Tests

Please implement the following pytest tests.

5.1 P_cap Soft Overflow Test

Test name:

def test_with_capacity_forward_planning_p_cap_dummy_node():
    ...

Input:

week = "2026-W01"

node = DummyNode("DUMMY_MOM")
node.init_week(week)
node.psi4demand[week][3] = ["L1", "L2", "L3", "L4", "L5"]

Capacity:

CapacityBucket(
    scenario_id="BASE",
    node_name="DUMMY_MOM",
    product_name="TEST_PRODUCT",
    week="2026-W01",
    capacity_type="P",
    capacity_qty=3,
    cap_mode="soft",
)

Expected:

node.psi4supply[week][3] == ["L1", "L2", "L3"]

Also verify:

CapacityUsage:
    capacity_type == "P"
    capacity_qty == 3
    used_qty == 3
    utilization == 1.0

CapacityViolation:
    capacity_type == "P"
    cap_mode == "soft"
    overflow_qty == 2
    violation_type == "CAPACITY_OVER_SOFT"
    action == "CARRY_OVER"
5.2 S_cap Soft Overflow Test

Test name:

def test_with_capacity_forward_planning_s_cap_dummy_node():
    ...

Input:

week = "2026-W01"

node = DummyNode("DUMMY_DAD")
node.init_week(week)
node.psi4demand[week][0] = ["S1", "S2", "S3", "S4"]

Capacity:

CapacityBucket(
    scenario_id="BASE",
    node_name="DUMMY_DAD",
    product_name="TEST_PRODUCT",
    week="2026-W01",
    capacity_type="S",
    capacity_qty=2,
    cap_mode="soft",
)

Expected:

node.psi4supply[week][0] == ["S1", "S2"]

Also verify:

CapacityViolation:
    capacity_type == "S"
    cap_mode == "soft"
    overflow_qty == 2
    violation_type == "CAPACITY_OVER_SOFT"
    action == "CARRY_OVER"
5.3 I_cap Soft Overflow Test

Test name:

def test_with_capacity_forward_planning_i_cap_soft_dummy_node():
    ...

Input:

week = "2026-W01"

node = DummyNode("DUMMY_DAD")
node.init_week(week)
node.psi4supply[week][2] = ["I1", "I2", "I3", "I4"]

Capacity:

CapacityBucket(
    scenario_id="BASE",
    node_name="DUMMY_DAD",
    product_name="TEST_PRODUCT",
    week="2026-W01",
    capacity_type="I",
    capacity_qty=3,
    cap_mode="soft",
)

Expected:

node.psi4supply[week][2] == ["I1", "I2", "I3", "I4"]

Soft I_cap must not delete inventory lots.

Also verify:

CapacityViolation:
    capacity_type == "I"
    cap_mode == "soft"
    required_qty == 4
    overflow_qty == 1
    violation_type == "INVENTORY_OVER_SOFT"
    action == "ALERT_ONLY"
5.4 I_cap Hard Overflow Test

Test name:

def test_with_capacity_forward_planning_i_cap_hard_dummy_node():
    ...

Input:

week = "2026-W01"

node = DummyNode("DUMMY_COLD_DC")
node.init_week(week)
node.psi4supply[week][2] = ["I1", "I2", "I3", "I4"]

Capacity:

CapacityBucket(
    scenario_id="BASE",
    node_name="DUMMY_COLD_DC",
    product_name="VACCINE_X",
    week="2026-W01",
    capacity_type="I",
    capacity_qty=3,
    cap_mode="hard",
)

Expected violation:

capacity_type == "I"
cap_mode == "hard"
required_qty == 4
overflow_qty == 1
violation_type == "INVENTORY_OVER_HARD"
action == "WASTE"

v0.2 does not need to physically remove overflow inventory lots unless the existing v0.1 implementation already supports it.

The minimum requirement is to record the hard-cap violation correctly.

5.5 CSV Export from Dummy Node Result

Test name:

def test_capacity_export_from_dummy_node_result(tmp_path):
    ...

This test should:

Create a dummy node.
Run with_capacity_forward_planning().
Export usage records using export_capacity_usage_csv().
Export violation records using export_capacity_violation_csv().
Confirm that both CSV files exist.
Confirm that expected headers exist.
Confirm that lot IDs are pipe-separated.

Use tmp_path so that test output does not pollute the repository.

6. Required Imports

The new test file should import from the existing v0.1 package:

from pysi.capacity.capacity_model import CapacityBucket
from pysi.capacity.capacity_planning import with_capacity_forward_planning
from pysi.capacity.capacity_exporter import (
    export_capacity_usage_csv,
    export_capacity_violation_csv,
)

If package-level exports in pysi.capacity.__init__ are already sufficient, using those is also acceptable.

7. Expected Usage of with_capacity_forward_planning

Each test should call:

usage_records, violation_records = with_capacity_forward_planning(
    root_node=node,
    weeks=[week],
    scenario_id="BASE",
    product_name="TEST_PRODUCT",
    capacity_buckets=[...],
    tree_side="OUTBOUND",
    node_order=[node],
)

For the hard I_cap vaccine test, use:

product_name="VACCINE_X"

Passing node_order=[node] is recommended so that traversal behavior is not the focus of v0.2.

8. Bug Fix Policy

If the current v0.1 implementation has small issues that prevent the dummy node tests from passing, please apply minimal fixes only.

Allowed minimal fixes include:

correcting PSI adapter behavior
correcting violation type names
correcting action names
making helper functions more defensive
ensuring CapacityUsage and CapacityViolation fields are populated consistently
ensuring exporters handle records generated by dummy node tests

Do not perform broad refactoring.

Do not redesign the v0.1 package.

9. Required Test Command

The following command must pass:

PYTHONPATH=. pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py

On Windows command prompt:

set PYTHONPATH=.
pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py

Also acceptable:

set PYTHONPATH=.
python -m pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py
10. Do Not Modify Unless Necessary

Please do not modify the following unless absolutely necessary:

existing GUI files
existing costing modules
existing event extraction modules
existing non-capacity planning engine
existing sample scenario behavior

v0.2 must remain isolated and test-focused.

11. Expected Completion Criteria

v0.2 is complete when:

tests/test_capacity_planning_dummy_node.py is added.
DummyNode is defined in the test file.
P_cap dummy node test passes.
S_cap dummy node test passes.
I_cap soft dummy node test passes.
I_cap hard dummy node test passes.
CSV export dummy node test passes.
Existing v0.1 basic tests still pass.
No existing WOM execution path is changed.
The implementation remains additive.
12. Notes for Codex

This is not yet real WOM pipeline integration.

The main objective is to prove this concept:

Weekly WOM with Capacity is lot_ID list operation under capacity constraints.

In WOM terms:

v0.1:
    The capacity gate was built.

v0.2:
    Dummy lots pass through the gate.

v0.3:
    Real WOM lots pass through the gate.

Please keep the implementation small, readable, and defensive.