# Codex Request: with Capacity PSI Planning Engine v0.4
## Small Outbound Tree Integration Test

## 1. Request Summary

Please implement v0.4 of the **with Capacity PSI Planning Engine**.

This request is based on the design document:

```text
docs/design/with-capacity-psi-planning-engine-v0.4-small-outbound-tree-test.md

v0.1 added the additive pysi.capacity package.

v0.2 added dummy-node PSI list integration tests.

v0.3 added real-WOM-compatible node tests.

v0.4 should verify that the capacity planner can process a small outbound tree using tree_side="OUTBOUND" and PreOrder traversal.

The target structure is:

MOM_TEST
    ↓
DAD_TEST
    ↓
MKT_TEST

The main goal is:

Confirm that with_capacity_forward_planning() can process multiple WOM-like nodes
in a small outbound tree while preserving lot_ID list operations.

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

v0.3:
    RealLikeNode compatibility tests
    name / node_name / name4node compatibility

v0.4 should build on this existing implementation.

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

tests/test_capacity_planning_small_outbound_tree.py

This test file should construct a small outbound tree:

MOM_TEST -> DAD_TEST -> MKT_TEST

The test should verify:

OUTBOUND PreOrder traversal
MOM P_cap behavior
DAD I_cap soft overflow behavior
MKT S_cap behavior
Multi-node usage records
Multi-node violation records
CSV export from small outbound tree result
5. Recommended Test Node Class

Please define a lightweight test node class inside the test file.

Recommended class:

class SmallTreeNode:
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
6. Small Outbound Tree Construction

Please use the following test structure:

mom = SmallTreeNode("MOM_TEST")
dad = SmallTreeNode("DAD_TEST")
mkt = SmallTreeNode("MKT_TEST")

mom.add_child(dad)
dad.add_child(mkt)

The root node is:

root_node = mom

The planner should be called with:

tree_side="OUTBOUND"
7. Required Tests
7.1 OUTBOUND PreOrder Traversal Test

Test name:

def test_capacity_forward_outbound_preorder_traversal():
    ...

Purpose:

Verify that:

iter_nodes_for_capacity_forward(mom, "OUTBOUND")

returns nodes in this order:

["MOM_TEST", "DAD_TEST", "MKT_TEST"]

This confirms supply-side-to-market-side traversal.

7.2 MOM P_cap Test

Test name:

def test_with_capacity_forward_planning_small_outbound_tree_mom_p_cap():
    ...

Input:

week = "2026-W01"

mom.psi4demand[week][3] = ["P1", "P2", "P3", "P4", "P5"]

Capacity:

CapacityBucket(
    scenario_id="BASE",
    node_name="MOM_TEST",
    product_name="TEST_PRODUCT",
    week="2026-W01",
    capacity_type="P",
    capacity_qty=3,
    cap_mode="soft",
)

Run:

usage_records, violation_records = with_capacity_forward_planning(
    root_node=mom,
    weeks=[week],
    scenario_id="BASE",
    product_name="TEST_PRODUCT",
    capacity_buckets=[bucket],
    tree_side="OUTBOUND",
)

Expected:

mom.psi4supply[week][3] == ["P1", "P2", "P3"]

Expected violation:

node_name == "MOM_TEST"
capacity_type == "P"
overflow_qty == 2
violation_type == "CAPACITY_OVER_SOFT"
action == "CARRY_OVER"
7.3 DAD I_cap Soft Overflow Test

Test name:

def test_with_capacity_forward_planning_small_outbound_tree_dad_i_cap_soft():
    ...

Input:

week = "2026-W01"

dad.psi4supply[week][2] = ["I1", "I2", "I3", "I4"]

Capacity:

CapacityBucket(
    scenario_id="BASE",
    node_name="DAD_TEST",
    product_name="TEST_PRODUCT",
    week="2026-W01",
    capacity_type="I",
    capacity_qty=3,
    cap_mode="soft",
)

Expected:

dad.psi4supply[week][2] == ["I1", "I2", "I3", "I4"]

Soft I_cap should not delete inventory lots.

Expected violation:

node_name == "DAD_TEST"
capacity_type == "I"
required_qty == 4
overflow_qty == 1
violation_type == "INVENTORY_OVER_SOFT"
action == "ALERT_ONLY"
7.4 MKT S_cap Test

Test name:

def test_with_capacity_forward_planning_small_outbound_tree_mkt_s_cap():
    ...

Input:

week = "2026-W01"

mkt.psi4demand[week][0] = ["S1", "S2", "S3", "S4"]

Capacity:

CapacityBucket(
    scenario_id="BASE",
    node_name="MKT_TEST",
    product_name="TEST_PRODUCT",
    week="2026-W01",
    capacity_type="S",
    capacity_qty=2,
    cap_mode="soft",
)

Expected:

mkt.psi4supply[week][0] == ["S1", "S2"]

Expected violation:

node_name == "MKT_TEST"
capacity_type == "S"
overflow_qty == 2
violation_type == "CAPACITY_OVER_SOFT"
action == "CARRY_OVER"
7.5 Multi-Node Usage and Violation Records Test

Test name:

def test_with_capacity_forward_planning_small_outbound_tree_multi_node_records():
    ...

Use the tree:

MOM_TEST -> DAD_TEST -> MKT_TEST

Input PSI lots:

week = "2026-W01"

mom.psi4demand[week][3] = ["P1", "P2", "P3", "P4", "P5"]
dad.psi4supply[week][2] = ["I1", "I2", "I3", "I4"]
mkt.psi4demand[week][0] = ["S1", "S2", "S3", "S4"]

Capacity buckets:

capacity_buckets = [
    CapacityBucket(
        scenario_id="BASE",
        node_name="MOM_TEST",
        product_name="TEST_PRODUCT",
        week=week,
        capacity_type="P",
        capacity_qty=3,
        cap_mode="soft",
    ),
    CapacityBucket(
        scenario_id="BASE",
        node_name="DAD_TEST",
        product_name="TEST_PRODUCT",
        week=week,
        capacity_type="I",
        capacity_qty=3,
        cap_mode="soft",
    ),
    CapacityBucket(
        scenario_id="BASE",
        node_name="MKT_TEST",
        product_name="TEST_PRODUCT",
        week=week,
        capacity_type="S",
        capacity_qty=2,
        cap_mode="soft",
    ),
]

Run:

usage_records, violation_records = with_capacity_forward_planning(
    root_node=mom,
    weeks=[week],
    scenario_id="BASE",
    product_name="TEST_PRODUCT",
    capacity_buckets=capacity_buckets,
    tree_side="OUTBOUND",
)

Expected usage records should include at least:

MOM_TEST / P
DAD_TEST / I
MKT_TEST / S

Expected violation records should include:

MOM_TEST / CAPACITY_OVER_SOFT
DAD_TEST / INVENTORY_OVER_SOFT
MKT_TEST / CAPACITY_OVER_SOFT

The test should verify that records are generated for multiple nodes.

7.6 CSV Export from Small Outbound Tree Result

Test name:

def test_capacity_export_from_small_outbound_tree_result(tmp_path):
    ...

This test should:

Create the small outbound tree.
Place PSI lot_ID lists.
Run with_capacity_forward_planning().
Export usage records with export_capacity_usage_csv().
Export violation records with export_capacity_violation_csv().
Confirm both files exist.
Confirm headers are correct.
Confirm lot IDs are pipe-separated.
Confirm multiple node names appear in output.
Confirm at least one usage record exists.
Confirm at least one violation record exists.

Use tmp_path to avoid polluting the repository.

8. Required Imports

The test file should import:

from pysi.capacity.capacity_model import CapacityBucket
from pysi.capacity.capacity_planning import (
    iter_nodes_for_capacity_forward,
    with_capacity_forward_planning,
)
from pysi.capacity.capacity_exporter import (
    export_capacity_usage_csv,
    export_capacity_violation_csv,
)

Package-level imports from pysi.capacity are also acceptable if already exposed.

9. Minimal Fix Policy

If small outbound tree testing reveals small issues in traversal or node compatibility, minimal fixes are allowed.

Allowed minimal fixes:

- improve children traversal fallback
- support children / child_nodes / children_nodes consistently
- preserve PreOrder behavior for OUTBOUND
- avoid crashing on missing PSI week
- avoid crashing on missing PSI bucket
- preserve existing v0.1 / v0.2 / v0.3 tests

Not allowed:

- rewriting the capacity planner
- changing non-capacity Forward Planning
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

v0.4 is still a small outbound tree compatibility test.

11. Required Test Command

The following command must pass:

PYTHONPATH=. pytest -q \
  tests/test_capacity_planning_basic.py \
  tests/test_capacity_planning_dummy_node.py \
  tests/test_capacity_planning_real_node.py \
  tests/test_capacity_planning_small_outbound_tree.py

On Windows command prompt:

set PYTHONPATH=.
pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py tests/test_capacity_planning_real_node.py tests/test_capacity_planning_small_outbound_tree.py

Also acceptable:

set PYTHONPATH=.
python -m pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py tests/test_capacity_planning_real_node.py tests/test_capacity_planning_small_outbound_tree.py

Expected result:

All tests pass.
12. Expected Completion Criteria

v0.4 is complete when:

tests/test_capacity_planning_small_outbound_tree.py is added.
A small outbound tree is constructed in the test.
OUTBOUND PreOrder traversal is verified.
MOM P_cap behavior is verified.
DAD I_cap soft behavior is verified.
MKT S_cap behavior is verified.
Multi-node usage records are verified.
Multi-node violation records are verified.
CSV export from small outbound tree results is verified.
Existing v0.1 / v0.2 / v0.3 tests still pass.
No existing WOM execution path is changed.
13. Notes for Codex

This is not Run Full Plan integration.

This is not GUI integration.

This is not optimization.

This is not costing integration.

This is a small, defensive, test-focused outbound tree compatibility step.

The key goal is:

Confirm that the capacity planner can process a small OUTBOUND tree in PreOrder.

In WOM terms:

v0.1:
    The capacity gate was built.

v0.2:
    Dummy lots passed through the gate.

v0.3:
    Real-WOM-compatible lots passed through the gate.

v0.4:
    Lots pass through a small outbound road with multiple gates.

Please keep the implementation small, readable, and additive.