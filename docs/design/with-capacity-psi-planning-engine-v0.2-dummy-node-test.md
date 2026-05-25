# with Capacity PSI Planning Engine v0.2 Design
## Dummy Node PSI List Integration Test

## 1. Purpose

This document defines the v0.2 design of the **with Capacity PSI Planning Engine**.

v0.1 introduced an additive `pysi.capacity` package with the following functions:

- capacity dataclasses
- capacity master CSV loader
- capacity lookup
- lot list splitting by capacity
- capacity usage records
- capacity violation records
- CSV exporters
- basic pytest smoke tests

v0.2 verifies that these components can operate on a WOM-like Node object that has actual PSI list structures:

```python
node.psi4demand[week][0]  # S
node.psi4demand[week][1]  # CO
node.psi4demand[week][2]  # I
node.psi4demand[week][3]  # P

node.psi4supply[week][0]  # S
node.psi4supply[week][1]  # CO
node.psi4supply[week][2]  # I
node.psi4supply[week][3]  # P

The key purpose of v0.2 is to confirm that Weekly WOM PSI with Capacity is a lot_ID list operation, not a numeric PSI calculation.

2. Background

The prior Monthly PSI on Capacity examples used numeric PSI calculations.

For example:

production_actual = min(production_plan, P_cap)
sales_actual = min(demand, inventory, S_cap)
over_cap = max(inventory - I_cap, 0)

However, WOM Weekly PSI uses PSI lists whose elements are lot_id.

For example:

node.psi4demand["2026-W01"][3] = ["L1", "L2", "L3", "L4", "L5"]

Therefore, capacity planning must operate by splitting lot_ID lists.

Example:

P_cap = 3

input lots:
["L1", "L2", "L3", "L4", "L5"]

executable lots:
["L1", "L2", "L3"]

overflow lots:
["L4", "L5"]

This is the central validation target of v0.2.

3. Scope of v0.2
3.1 In Scope

v0.2 implements the following:

Add a dummy WOM-like Node for testing.
Initialize psi4demand and psi4supply as PSI list structures.
Run with_capacity_forward_planning() against the dummy node.
Confirm P_cap lot splitting.
Confirm S_cap lot splitting.
Confirm I_cap soft overflow behavior.
Confirm I_cap hard overflow behavior.
Confirm CapacityUsage records.
Confirm CapacityViolation records.
Confirm exporter output with dummy node results.
3.2 Out of Scope

v0.2 does not implement:

real WOM Node integration
real Outbound Tree traversal
real Inbound Tree traversal
Run Full Plan pipeline integration
GUI integration
optimization
alternative MOM allocation
alternative lane selection
shelf life logic
temperature class logic
costing logic
event flow tracing

v0.2 is only a dummy node integration test.

4. Design Principle

The v0.2 design follows this principle:

v0.1:
    Build the capacity parts.

v0.2:
    Pass dummy WOM lots through the capacity parts.

v0.3:
    Connect to actual WOM Node.

The existing non-capacity PSI planning engine must remain unchanged.

The new tests must be additive.

5. Dummy Node Definition

v0.2 should define a minimal dummy node class inside the test file.

Recommended file:

tests/test_capacity_planning_dummy_node.py

Recommended dummy node:

class DummyNode:
    def __init__(self, name: str):
        self.name = name
        self.children = []
        self.psi4demand = {}
        self.psi4supply = {}

    def init_week(self, week):
        self.psi4demand[week] = [[], [], [], []]
        self.psi4supply[week] = [[], [], [], []]

Where PSI index meaning is:

Index	Symbol	Meaning
0	S	Ship / Sales / Supply
1	CO	Carry Over
2	I	Inventory
3	P	Production / Purchase
6. Test Case 1: P_cap Soft Overflow
6.1 Input
week = "2026-W01"

node.psi4demand[week][3] = ["L1", "L2", "L3", "L4", "L5"]
node.psi4supply[week][3] = []

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
6.2 Expected Result
node.psi4supply[week][3] == ["L1", "L2", "L3"]

Overflow lots:

["L4", "L5"]

Expected usage:

capacity_type = P
capacity_qty = 3
used_qty = 3
utilization = 1.0

Expected violation:

capacity_type = P
cap_mode = soft
overflow_qty = 2
violation_type = CAPACITY_OVER_SOFT
action = CARRY_OVER
7. Test Case 2: S_cap Soft Overflow
7.1 Input
week = "2026-W01"

node.psi4demand[week][0] = ["S1", "S2", "S3", "S4"]
node.psi4supply[week][0] = []

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
7.2 Expected Result
node.psi4supply[week][0] == ["S1", "S2"]

Overflow lots:

["S3", "S4"]

Expected violation:

capacity_type = S
cap_mode = soft
overflow_qty = 2
violation_type = CAPACITY_OVER_SOFT
action = CARRY_OVER
8. Test Case 3: I_cap Soft Overflow
8.1 Input
week = "2026-W01"

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
8.2 Expected Result

Inventory lots should not be deleted in soft mode.

node.psi4supply[week][2] == ["I1", "I2", "I3", "I4"]

Expected violation:

capacity_type = I
cap_mode = soft
required_qty = 4
overflow_qty = 1
violation_type = INVENTORY_OVER_SOFT
action = ALERT_ONLY

This means that soft I_cap is a management alert, not forced disposal.

9. Test Case 4: I_cap Hard Overflow
9.1 Input
week = "2026-W01"

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
9.2 Expected Result

In hard mode, overflow is recorded as waste.

Expected violation:

capacity_type = I
cap_mode = hard
required_qty = 4
overflow_qty = 1
violation_type = INVENTORY_OVER_HARD
action = WASTE

v0.2 does not need to physically remove overflow inventory from the dummy node unless the current v0.1 implementation already supports it.

The minimum requirement is to record the hard-cap violation correctly.

10. Test Case 5: CSV Export from Dummy Node Result

v0.2 should confirm that dummy node planning results can be exported.

Recommended output directory:

outputs/capacity/smoke/

Expected files:

outputs/capacity/smoke/capacity_usage_dummy_node.csv
outputs/capacity/smoke/capacity_violation_dummy_node.csv

These files should be generated by the test or a smoke script.

If generated by pytest, the test should use a temporary directory such as tmp_path to avoid polluting the repository.

11. Recommended Test File

Recommended file:

tests/test_capacity_planning_dummy_node.py

Recommended tests:

def test_with_capacity_forward_planning_p_cap_dummy_node():
    ...

def test_with_capacity_forward_planning_s_cap_dummy_node():
    ...

def test_with_capacity_forward_planning_i_cap_soft_dummy_node():
    ...

def test_with_capacity_forward_planning_i_cap_hard_dummy_node():
    ...

def test_capacity_export_from_dummy_node_result(tmp_path):
    ...
12. Optional Smoke Script

A simple smoke script may also be added.

Recommended file:

tools/smoke_capacity_dummy_node.py

Purpose:

Create dummy node
Place demand lots
Create capacity buckets
Run with_capacity_forward_planning()
Export usage and violation CSV files
Print summary

Example output:

Capacity dummy node smoke test completed.
Usage records: 3
Violation records: 2
Output:
  outputs/capacity/smoke/capacity_usage_dummy_node.csv
  outputs/capacity/smoke/capacity_violation_dummy_node.csv

This script is optional for v0.2.
The pytest file is the primary requirement.

13. Current v0.1 Compatibility Assumption

v0.2 should reuse the existing v0.1 implementation:

pysi/capacity/capacity_model.py
pysi/capacity/capacity_master_loader.py
pysi/capacity/capacity_planning.py
pysi/capacity/capacity_exporter.py

v0.2 should avoid rewriting these modules unless a small bug fix is required.

If a bug is found in v0.1 during dummy node testing, the fix should be minimal and covered by a test.

14. Expected Completion Criteria

v0.2 is complete when:

Dummy node test file is added.
with_capacity_forward_planning() is executed against a dummy node.
P_cap split behavior is verified.
S_cap split behavior is verified.
I_cap soft overflow behavior is verified.
I_cap hard overflow behavior is verified.
Capacity usage records are verified.
Capacity violation records are verified.
CSV export from dummy node results is verified.
Existing v0.1 tests still pass.

Expected test command:

set PYTHONPATH=.
pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py

For PowerShell:

$env:PYTHONPATH="."
pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py
15. Design Summary

with Capacity PSI Planning Engine v0.2 is a bridge between the capacity utility package and the real WOM PSI list structure.

It does not yet connect to the full WOM planning pipeline.

It proves the following core idea:

Weekly WOM with Capacity is not numeric PSI calculation.
It is lot_ID list operation under capacity constraints.

In other words:

v0.1:
    The capacity gate was built.

v0.2:
    Dummy lots pass through the gate.

v0.3:
    Real WOM lots pass through the gate.