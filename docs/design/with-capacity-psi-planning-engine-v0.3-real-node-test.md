# with Capacity PSI Planning Engine v0.3 Design
## Real WOM Node Single-Node Integration Test

## 1. Purpose

This document defines the v0.3 design of the **with Capacity PSI Planning Engine**.

v0.1 introduced the additive `pysi.capacity` package.

v0.2 verified that `with_capacity_forward_planning()` can operate on a dummy WOM-like node with `psi4demand` and `psi4supply` list structures.

v0.3 takes the next step:

```text
Use a real WOM Node class or a real-WOM-compatible node instance,
and verify that the capacity planner can read and write actual PSI list structures.

The goal is not yet full pipeline integration.

The goal is to confirm that the v0.1/v0.2 capacity planner can work with the actual WOM Node data model, at least for a single node.

2. Background

The core concept has already been validated in v0.2:

Weekly WOM with Capacity
= lot_ID list operation under capacity constraints

v0.2 used an in-test DummyNode.

However, real WOM nodes may differ from DummyNode in details such as:

node name attribute
children attribute
PSI list initialization
week indexing
PSI bucket structure
existing helper methods
node traversal behavior
actual psi4demand and psi4supply initialization timing

Therefore, before connecting the capacity planner to Run Full Plan, v0.3 should verify compatibility with a real or near-real WOM Node.

3. Positioning

The staged development flow is:

v0.1:
    Build the capacity gate.

v0.2:
    Pass dummy lots through the gate.

v0.3:
    Pass real-WOM-compatible lots through the gate.

v0.4:
    Connect to a small Outbound Tree.

v0.5:
    Connect to a small Inbound Tree.

v0.6:
    Add optional capacity report hook after existing planning pipeline.

v0.3 is still a test-focused integration step.

4. Scope of v0.3
4.1 In Scope

v0.3 should implement:

A single-node integration test using a real WOM Node class if practical.
If direct real Node creation is too difficult, a minimal real-WOM-compatible adapter node may be used.
Verification that the node has actual psi4demand and psi4supply structures.
Verification that with_capacity_forward_planning() can read P/S/I PSI buckets.
Verification that with_capacity_forward_planning() can write executable P/S lots into psi4supply.
Verification that capacity usage records are generated.
Verification that capacity violation records are generated.
Verification that existing v0.1 and v0.2 tests still pass.
4.2 Out of Scope

v0.3 does not implement:

Run Full Plan pipeline integration
GUI integration
Outbound Tree full traversal
Inbound Tree full traversal
optimizer integration
alternative MOM allocation
alternative lane selection
shelf life logic
temperature class logic
costing logic
event flow tracing
database integration

v0.3 is only a single-node real-WOM-compatibility test.

5. Real Node Strategy

v0.3 should first try to use the actual WOM Node class.

Potential locations to inspect include, but are not limited to:

pysi/network_tree*.py
pysi/tree*.py
pysi/node*.py
pysi/core*.py

If a suitable Node class can be imported and initialized with minimal parameters, use it.

If the actual Node class requires too many scenario-specific dependencies, v0.3 may define a small test adapter that mimics the actual Node structure more closely than the v0.2 DummyNode.

The test adapter should be named clearly, for example:

class RealLikeNode:
    ...

or

class MinimalWOMNodeAdapter:
    ...

This adapter is not production code.
It is only a compatibility test object.

6. Required Test File

Recommended new file:

tests/test_capacity_planning_real_node.py

This file should contain either:

Option A:
    tests using the actual WOM Node class

Option B:
    tests using a real-WOM-compatible adapter node

Option A is preferred.

Option B is acceptable if the actual Node class is difficult to instantiate safely in a unit test.

7. Test Case 1: Real Node P_cap Soft Overflow
7.1 Purpose

Verify that a real or real-like WOM node can process P lots under P_cap.

7.2 Input
week = "2026-W01"
product_name = "TEST_PRODUCT"
node_name = "REAL_LIKE_MOM"

PSI demand:

node.psi4demand[week][3] = ["L1", "L2", "L3", "L4", "L5"]

Capacity:

CapacityBucket(
    scenario_id="BASE",
    node_name=node_name,
    product_name="TEST_PRODUCT",
    week="2026-W01",
    capacity_type="P",
    capacity_qty=3,
    cap_mode="soft",
)
7.3 Expected Result
node.psi4supply[week][3] == ["L1", "L2", "L3"]

Expected violation:

capacity_type = P
cap_mode = soft
overflow_qty = 2
violation_type = CAPACITY_OVER_SOFT
action = CARRY_OVER
8. Test Case 2: Real Node S_cap Soft Overflow
8.1 Purpose

Verify that a real or real-like WOM node can process S lots under S_cap.

8.2 Input
week = "2026-W01"
product_name = "TEST_PRODUCT"
node_name = "REAL_LIKE_DAD"

PSI demand:

node.psi4demand[week][0] = ["S1", "S2", "S3", "S4"]

Capacity:

CapacityBucket(
    scenario_id="BASE",
    node_name=node_name,
    product_name="TEST_PRODUCT",
    week="2026-W01",
    capacity_type="S",
    capacity_qty=2,
    cap_mode="soft",
)
8.3 Expected Result
node.psi4supply[week][0] == ["S1", "S2"]

Expected violation:

capacity_type = S
cap_mode = soft
overflow_qty = 2
violation_type = CAPACITY_OVER_SOFT
action = CARRY_OVER
9. Test Case 3: Real Node I_cap Soft Overflow
9.1 Purpose

Verify that real or real-like inventory bucket can be checked under soft I_cap.

9.2 Input
week = "2026-W01"
product_name = "TEST_PRODUCT"
node_name = "REAL_LIKE_DAD"

PSI supply inventory:

node.psi4supply[week][2] = ["I1", "I2", "I3", "I4"]

Capacity:

CapacityBucket(
    scenario_id="BASE",
    node_name=node_name,
    product_name="TEST_PRODUCT",
    week="2026-W01",
    capacity_type="I",
    capacity_qty=3,
    cap_mode="soft",
)
9.3 Expected Result

Soft I_cap should not delete inventory lots.

node.psi4supply[week][2] == ["I1", "I2", "I3", "I4"]

Expected violation:

capacity_type = I
cap_mode = soft
required_qty = 4
overflow_qty = 1
violation_type = INVENTORY_OVER_SOFT
action = ALERT_ONLY
10. Test Case 4: Real Node I_cap Hard Overflow
10.1 Purpose

Verify that hard I_cap overflow is recorded correctly with a real or real-like WOM node.

10.2 Input
week = "2026-W01"
product_name = "VACCINE_X"
node_name = "REAL_LIKE_COLD_DC"

PSI supply inventory:

node.psi4supply[week][2] = ["I1", "I2", "I3", "I4"]

Capacity:

CapacityBucket(
    scenario_id="BASE",
    node_name=node_name,
    product_name="VACCINE_X",
    week="2026-W01",
    capacity_type="I",
    capacity_qty=3,
    cap_mode="hard",
)
10.3 Expected Result

Expected violation:

capacity_type = I
cap_mode = hard
required_qty = 4
overflow_qty = 1
violation_type = INVENTORY_OVER_HARD
action = WASTE

v0.3 does not require physical removal of inventory lots unless the existing implementation already supports it.

The minimum requirement is correct hard-cap violation recording.

11. Test Case 5: Real Node Capacity CSV Export
11.1 Purpose

Verify that capacity usage and violation records generated from a real or real-like WOM node can be exported.

11.2 Expected Output

Use tmp_path in pytest.

Expected files:

capacity_usage_real_node.csv
capacity_violation_real_node.csv

The test should confirm:

files are created
headers are correct
lot IDs are pipe-separated
at least one usage record exists
at least one violation record exists
12. Recommended Test Names
def test_with_capacity_forward_planning_real_node_p_cap():
    ...

def test_with_capacity_forward_planning_real_node_s_cap():
    ...

def test_with_capacity_forward_planning_real_node_i_cap_soft():
    ...

def test_with_capacity_forward_planning_real_node_i_cap_hard():
    ...

def test_capacity_export_from_real_node_result(tmp_path):
    ...

If using a real-like adapter instead of the actual Node class, the test names may use real_like_node.

13. Node Attribute Compatibility

The capacity planner currently expects the following minimum node interface:

node.name
node.children
node.psi4demand
node.psi4supply

v0.3 should verify whether the actual WOM Node uses these names.

If actual Node uses different names, the capacity planner adapter helpers should be minimally improved.

Allowed minimal improvements:

get_node_name(node)
    support node.name
    support node.node_name
    support node.name4node

_get_children(node)
    support node.children
    support node.child_nodes
    support node.children_nodes

PSI access helpers
    remain defensive for missing weeks and missing buckets

Do not over-generalize.

Do not redesign the capacity planner.

14. Expected Command

The following command should pass after v0.3 implementation:

PYTHONPATH=. pytest -q \
  tests/test_capacity_planning_basic.py \
  tests/test_capacity_planning_dummy_node.py \
  tests/test_capacity_planning_real_node.py

On Windows command prompt:

set PYTHONPATH=.
pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py tests/test_capacity_planning_real_node.py

Alternative:

set PYTHONPATH=.
python -m pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py tests/test_capacity_planning_real_node.py

Expected result:

All tests pass.
15. Bug Fix Policy

If actual Node compatibility reveals small issues in the v0.1/v0.2 capacity planner, minimal fixes are allowed.

Allowed fixes:

support alternate node name attributes
support alternate children attributes
make PSI bucket access more defensive
avoid crashing on missing PSI week
avoid crashing on missing PSI bucket
preserve existing behavior for DummyNode tests

Not allowed:

rewriting the capacity planner
modifying the existing non-capacity planning engine
modifying GUI
modifying costing
modifying event extraction
connecting to Run Full Plan
16. Completion Criteria

v0.3 is complete when:

A new real-node or real-like-node test file is added.
The test uses actual WOM Node if practical.
If actual Node is not practical, the test explains why and uses a real-like adapter.
P_cap behavior is verified.
S_cap behavior is verified.
I_cap soft behavior is verified.
I_cap hard behavior is verified.
CSV export from real-node-style records is verified.
Existing v0.1 and v0.2 tests still pass.
No existing WOM execution path is changed.
17. Design Summary

v0.3 is the bridge from dummy PSI list testing to actual WOM Node compatibility.

It still does not connect to Run Full Plan.

It proves this:

The capacity planner can operate on a WOM-realistic Node PSI structure.

In WOM terms:

v0.1:
    The capacity gate was built.

v0.2:
    Dummy lots passed through the gate.

v0.3:
    Real-WOM-compatible lots pass through the gate.

The first goal is still not optimization.

The first goal is to make capacity collision visible at the Lot level without breaking the existing WOM planning flow.