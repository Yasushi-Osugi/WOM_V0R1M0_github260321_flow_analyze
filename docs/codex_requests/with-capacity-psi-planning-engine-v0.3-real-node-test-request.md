# Codex Request: with Capacity PSI Planning Engine v0.3
## Real WOM Node Single-Node Integration Test

## 1. Request Summary

Please implement v0.3 of the **with Capacity PSI Planning Engine**.

This request is based on the design document:

```text
docs/design/with-capacity-psi-planning-engine-v0.3-real-node-test.md

v0.1 added the additive pysi.capacity package.

v0.2 added dummy-node PSI list integration tests.

v0.3 should verify that the capacity planner can operate on a real WOM Node class, or on a real-WOM-compatible node adapter if the actual Node class is too heavy to instantiate in a unit test.

The main goal is:

Confirm that with_capacity_forward_planning() can read and write WOM-realistic psi4demand / psi4supply lot_ID lists.

This is still a test-focused integration step.

Do not connect this functionality to Run Full Plan yet.

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
    P_cap / S_cap / I_cap behavior tests
    8 pytest tests passing

v0.3 should build on this existing implementation.

3. Important Concept

Please preserve the core WOM concept:

Monthly PSI on Capacity:
    numeric PSI calculation

Weekly WOM PSI with Capacity:
    lot_ID list operation under capacity constraints

The capacity planner must preserve lot identity.

Do not convert the weekly WOM PSI structure into pure numeric PSI calculations.

4. Required New Test File

Please add:

tests/test_capacity_planning_real_node.py

This test file should verify capacity planning with either:

Option A:
    Actual WOM Node class

Option B:
    Real-WOM-compatible adapter node

Option A is preferred if it can be done safely and simply.

Option B is acceptable if the actual WOM Node class requires many scenario-specific dependencies.

5. Try to Use Actual WOM Node First

Please inspect the current repository for the actual WOM Node class.

Likely locations may include:

pysi/network_tree*.py
pysi/tree*.py
pysi/node*.py
pysi/core*.py

If the actual Node class can be imported and initialized without heavy scenario setup, please use it in the test.

If the real Node requires complex master data, GUI state, scenario files, tree construction, or other heavy dependencies, do not force it into this unit test.

In that case, define a real-WOM-compatible adapter in the test file.

Recommended adapter names:

class RealLikeNode:
    ...

or

class MinimalWOMNodeAdapter:
    ...

The adapter should mimic the minimum real WOM Node interface needed by the capacity planner.

6. Minimum Node Interface

The capacity planner currently expects the following node interface:

node.name
node.children
node.psi4demand
node.psi4supply

However, the actual WOM Node may use slightly different attribute names.

Please minimally improve adapter helpers if necessary.

Allowed compatibility improvements:

get_node_name(node):
    support node.name
    support node.node_name
    support node.name4node

children access:
    support node.children
    support node.child_nodes
    support node.children_nodes

PSI access:
    handle missing week defensively
    handle missing bucket defensively

Do not over-generalize.

Do not redesign the capacity planner.

7. Required Tests

Please implement the following tests.

7.1 P_cap Real Node Test

Test name:

def test_with_capacity_forward_planning_real_node_p_cap():
    ...

Purpose:

Verify that a real or real-like WOM node can process P lots under P_cap.

Input:

week = "2026-W01"
product_name = "TEST_PRODUCT"
node_name = "REAL_LIKE_MOM"

node.psi4demand[week][3] = ["L1", "L2", "L3", "L4", "L5"]
node.psi4supply[week][3] = []

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

Run:

usage_records, violation_records = with_capacity_forward_planning(
    root_node=node,
    weeks=[week],
    scenario_id="BASE",
    product_name="TEST_PRODUCT",
    capacity_buckets=[bucket],
    tree_side="OUTBOUND",
    node_order=[node],
)

Expected:

node.psi4supply[week][3] == ["L1", "L2", "L3"]

Expected violation:

capacity_type == "P"
cap_mode == "soft"
overflow_qty == 2
violation_type == "CAPACITY_OVER_SOFT"
action == "CARRY_OVER"
7.2 S_cap Real Node Test

Test name:

def test_with_capacity_forward_planning_real_node_s_cap():
    ...

Input:

week = "2026-W01"
product_name = "TEST_PRODUCT"
node_name = "REAL_LIKE_DAD"

node.psi4demand[week][0] = ["S1", "S2", "S3", "S4"]
node.psi4supply[week][0] = []

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

Expected:

node.psi4supply[week][0] == ["S1", "S2"]

Expected violation:

capacity_type == "S"
cap_mode == "soft"
overflow_qty == 2
violation_type == "CAPACITY_OVER_SOFT"
action == "CARRY_OVER"
7.3 I_cap Soft Real Node Test

Test name:

def test_with_capacity_forward_planning_real_node_i_cap_soft():
    ...

Input:

week = "2026-W01"
product_name = "TEST_PRODUCT"
node_name = "REAL_LIKE_DAD"

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

Expected:

node.psi4supply[week][2] == ["I1", "I2", "I3", "I4"]

Soft I_cap should not delete inventory lots.

Expected violation:

capacity_type == "I"
cap_mode == "soft"
required_qty == 4
overflow_qty == 1
violation_type == "INVENTORY_OVER_SOFT"
action == "ALERT_ONLY"
7.4 I_cap Hard Real Node Test

Test name:

def test_with_capacity_forward_planning_real_node_i_cap_hard():
    ...

Input:

week = "2026-W01"
product_name = "VACCINE_X"
node_name = "REAL_LIKE_COLD_DC"

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

Expected violation:

capacity_type == "I"
cap_mode == "hard"
required_qty == 4
overflow_qty == 1
violation_type == "INVENTORY_OVER_HARD"
action == "WASTE"

v0.3 does not require physical removal of inventory lots unless the current implementation already supports it.

The minimum requirement is correct hard-cap violation recording.

7.5 CSV Export from Real Node Result

Test name:

def test_capacity_export_from_real_node_result(tmp_path):
    ...

This test should:

Create a real or real-like WOM node.
Place PSI lot_ID lists.
Run with_capacity_forward_planning().
Export usage records with export_capacity_usage_csv().
Export violation records with export_capacity_violation_csv().
Confirm files exist.
Confirm headers are correct.
Confirm lot IDs are pipe-separated.
Confirm at least one usage record exists.
Confirm at least one violation record exists.

Use tmp_path to avoid polluting the repository.

8. Required Imports

The test file should import from the existing capacity package:

from pysi.capacity.capacity_model import CapacityBucket
from pysi.capacity.capacity_planning import with_capacity_forward_planning
from pysi.capacity.capacity_exporter import (
    export_capacity_usage_csv,
    export_capacity_violation_csv,
)

Package-level imports from pysi.capacity are also acceptable if already exposed.

9. Minimal Fix Policy

If actual or real-like Node testing reveals small issues in the v0.1/v0.2 implementation, minimal fixes are allowed.

Allowed minimal fixes:

- support node.node_name in get_node_name()
- support node.name4node in get_node_name()
- support children / child_nodes / children_nodes traversal
- avoid crashing on missing PSI week
- avoid crashing on missing PSI bucket
- preserve existing DummyNode behavior
- preserve existing v0.1 and v0.2 tests

Not allowed:

- rewriting the capacity planner
- changing the non-capacity Forward Planning engine
- connecting to Run Full Plan
- modifying GUI
- modifying costing modules
- modifying event extraction modules
- adding optimization
10. Do Not Modify Existing WOM Pipeline

Please do not modify:

existing GUI files
existing costing modules
existing event extraction modules
existing non-capacity planning engine
existing Run Full Plan pipeline
existing sample scenario behavior

v0.3 is still a compatibility test step.

11. Expected Test Command

The following command must pass:

PYTHONPATH=. pytest -q \
  tests/test_capacity_planning_basic.py \
  tests/test_capacity_planning_dummy_node.py \
  tests/test_capacity_planning_real_node.py

On Windows command prompt:

set PYTHONPATH=.
pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py tests/test_capacity_planning_real_node.py

Also acceptable:

set PYTHONPATH=.
python -m pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py tests/test_capacity_planning_real_node.py

Expected result:

All tests pass.
12. Expected Completion Criteria

v0.3 is complete when:

tests/test_capacity_planning_real_node.py is added.
The test uses actual WOM Node if practical.
If actual WOM Node is not practical, the test uses a real-WOM-compatible adapter.
P_cap behavior is verified.
S_cap behavior is verified.
I_cap soft behavior is verified.
I_cap hard behavior is verified.
CSV export from real-node-style records is verified.
Existing v0.1 and v0.2 tests still pass.
No existing WOM execution path is changed.
13. Notes for Codex

This is not Run Full Plan integration.

This is not GUI integration.

This is not optimization.

This is a small, defensive, test-focused compatibility step.

The key goal is:

Confirm that the capacity planner can operate on a WOM-realistic Node PSI structure.

In WOM terms:

v0.1:
    The capacity gate was built.

v0.2:
    Dummy lots passed through the gate.

v0.3:
    Real-WOM-compatible lots pass through the gate.

Please keep the implementation small and readable.