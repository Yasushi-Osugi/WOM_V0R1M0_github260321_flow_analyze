# Codex Request: with Capacity PSI Planning Engine v0.5
## Small Inbound Tree Integration Test

## 1. Request Summary

Please implement v0.5 of the **with Capacity PSI Planning Engine**.

This request is based on the design document:

```text
docs/design/with-capacity-psi-planning-engine-v0.5-small-inbound-tree-test.md

v0.1 added the additive pysi.capacity package.

v0.2 added dummy-node PSI list integration tests.

v0.3 added real-WOM-compatible node tests.

v0.4 added small Outbound Tree integration tests using tree_side="OUTBOUND" and PreOrder traversal.

v0.5 should verify that the capacity planner can process a small inbound Fan-In tree using tree_side="INBOUND" and PostOrder traversal.

The target inbound structure is:

MOM_TEST
├── RAW_A_TEST
└── RAW_B_TEST

Expected INBOUND processing order:

RAW_A_TEST -> RAW_B_TEST -> MOM_TEST

The main goal is:

Confirm that with_capacity_forward_planning() can process multiple WOM-like nodes
in a small inbound Fan-In tree while preserving lot_ID list operations.

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

v0.4:
    Small Outbound Tree tests
    OUTBOUND PreOrder traversal
    MOM_TEST -> DAD_TEST -> MKT_TEST

v0.5 should build on this existing implementation.

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

tests/test_capacity_planning_small_inbound_tree.py

This test file should construct a small inbound Fan-In tree:

MOM_TEST
├── RAW_A_TEST
└── RAW_B_TEST

The test should verify:

INBOUND PostOrder traversal
RAW_A_TEST P_cap behavior
RAW_B_TEST S_cap behavior
MOM_TEST I_cap soft overflow behavior
Multi-node usage records
Multi-node violation records
CSV export from small inbound tree result
5. Recommended Test Node Class

Please define a lightweight test node class inside the test file.

Recommended class:

class SmallInboundTreeNode:
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
6. Small Inbound Tree Construction

Please use the following test structure:

mom = SmallInboundTreeNode("MOM_TEST")
raw_a = SmallInboundTreeNode("RAW_A_TEST")
raw_b = SmallInboundTreeNode("RAW_B_TEST")

mom.add_child(raw_a)
mom.add_child(raw_b)

The root node is:

root_node = mom

The planner should be called with:

tree_side="INBOUND"

Expected INBOUND PostOrder traversal:

["RAW_A_TEST", "RAW_B_TEST", "MOM_TEST"]

The order of RAW_A_TEST and RAW_B_TEST should follow mom.children.

7. Required Tests
7.1 INBOUND PostOrder Traversal Test

Test name:

def test_capacity_forward_inbound_postorder_traversal():
    ...

Purpose:

Verify that:

iter_nodes_for_capacity_forward(mom, "INBOUND")

returns nodes in this order:

["RAW_A_TEST", "RAW_B_TEST", "MOM_TEST"]

This confirms material-side-to-MOM-side traversal.

7.2 RAW_A P_cap Test

Test name:

def test_with_capacity_forward_planning_small_inbound_tree_raw_a_p_cap():
    ...

Input:

week = "2026-W01"

raw_a.psi4demand[week][3] = ["PA1", "PA2", "PA3", "PA4", "PA5"]

Capacity:

CapacityBucket(
    scenario_id="BASE",
    node_name="RAW_A_TEST",
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
    tree_side="INBOUND",
)

Expected:

raw_a.psi4supply[week][3] == ["PA1", "PA2", "PA3"]

Expected violation:

node_name == "RAW_A_TEST"
capacity_type == "P"
overflow_qty == 2
violation_type == "CAPACITY_OVER_SOFT"
action == "CARRY_OVER"
7.3 RAW_B S_cap Test

Test name:

def test_with_capacity_forward_planning_small_inbound_tree_raw_b_s_cap():
    ...

Input:

week = "2026-W01"

raw_b.psi4demand[week][0] = ["SB1", "SB2", "SB3", "SB4"]

Capacity:

CapacityBucket(
    scenario_id="BASE",
    node_name="RAW_B_TEST",
    product_name="TEST_PRODUCT",
    week="2026-W01",
    capacity_type="S",
    capacity_qty=2,
    cap_mode="soft",
)

Expected:

raw_b.psi4supply[week][0] == ["SB1", "SB2"]

Expected violation:

node_name == "RAW_B_TEST"
capacity_type == "S"
overflow_qty == 2
violation_type == "CAPACITY_OVER_SOFT"
action == "CARRY_OVER"
7.4 MOM I_cap Soft Overflow Test

Test name:

def test_with_capacity_forward_planning_small_inbound_tree_mom_i_cap_soft():
    ...

Input:

week = "2026-W01"

mom.psi4supply[week][2] = ["IM1", "IM2", "IM3", "IM4"]

Capacity:

CapacityBucket(
    scenario_id="BASE",
    node_name="MOM_TEST",
    product_name="TEST_PRODUCT",
    week="2026-W01",
    capacity_type="I",
    capacity_qty=3,
    cap_mode="soft",
)

Expected:

mom.psi4supply[week][2] == ["IM1", "IM2", "IM3", "IM4"]

Soft I_cap should not delete inventory lots.

Expected violation:

node_name == "MOM_TEST"
capacity_type == "I"
required_qty == 4
overflow_qty == 1
violation_type == "INVENTORY_OVER_SOFT"
action == "ALERT_ONLY"
7.5 Multi-Node Usage and Violation Records Test

Test name:

def test_with_capacity_forward_planning_small_inbound_tree_multi_node_records():
    ...

Use the tree:

MOM_TEST
├── RAW_A_TEST
└── RAW_B_TEST

Input PSI lots:

week = "2026-W01"

raw_a.psi4demand[week][3] = ["PA1", "PA2", "PA3", "PA4", "PA5"]
raw_b.psi4demand[week][0] = ["SB1", "SB2", "SB3", "SB4"]
mom.psi4supply[week][2] = ["IM1", "IM2", "IM3", "IM4"]

Capacity buckets:

capacity_buckets = [
    CapacityBucket(
        scenario_id="BASE",
        node_name="RAW_A_TEST",
        product_name="TEST_PRODUCT",
        week=week,
        capacity_type="P",
        capacity_qty=3,
        cap_mode="soft",
    ),
    CapacityBucket(
        scenario_id="BASE",
        node_name="RAW_B_TEST",
        product_name="TEST_PRODUCT",
        week=week,
        capacity_type="S",
        capacity_qty=2,
        cap_mode="soft",
    ),
    CapacityBucket(
        scenario_id="BASE",
        node_name="MOM_TEST",
        product_name="TEST_PRODUCT",
        week=week,
        capacity_type="I",
        capacity_qty=3,
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
    tree_side="INBOUND",
)

Expected usage records should include at least:

RAW_A_TEST / P
RAW_B_TEST / S
MOM_TEST / I

Expected violation records should include:

RAW_A_TEST / CAPACITY_OVER_SOFT
RAW_B_TEST / CAPACITY_OVER_SOFT
MOM_TEST / INVENTORY_OVER_SOFT

The test should verify that records are generated for multiple inbound nodes.

7.6 CSV Export from Small Inbound Tree Result

Test name:

def test_capacity_export_from_small_inbound_tree_result(tmp_path):
    ...

This test should:

Create the small inbound tree.
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

If small inbound tree testing reveals small issues in traversal or node compatibility, minimal fixes are allowed.

Allowed minimal fixes:

- improve children traversal fallback
- support children / child_nodes / children_nodes consistently
- preserve PostOrder behavior for INBOUND
- avoid crashing on missing PSI week
- avoid crashing on missing PSI bucket
- preserve existing v0.1 / v0.2 / v0.3 / v0.4 tests

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

v0.5 is still a small inbound tree compatibility test.

11. Required Test Command

The following command must pass:

PYTHONPATH=. pytest -q \
  tests/test_capacity_planning_basic.py \
  tests/test_capacity_planning_dummy_node.py \
  tests/test_capacity_planning_real_node.py \
  tests/test_capacity_planning_small_outbound_tree.py \
  tests/test_capacity_planning_small_inbound_tree.py

On Windows command prompt:

set PYTHONPATH=.
pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py tests/test_capacity_planning_real_node.py tests/test_capacity_planning_small_outbound_tree.py tests/test_capacity_planning_small_inbound_tree.py

Also acceptable:

set PYTHONPATH=.
python -m pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py tests/test_capacity_planning_real_node.py tests/test_capacity_planning_small_outbound_tree.py tests/test_capacity_planning_small_inbound_tree.py

Expected result:

All tests pass.
12. Expected Completion Criteria

v0.5 is complete when:

tests/test_capacity_planning_small_inbound_tree.py is added.
A small inbound Fan-In tree is constructed in the test.
INBOUND PostOrder traversal is verified.
RAW_A P_cap behavior is verified.
RAW_B S_cap behavior is verified.
MOM I_cap soft behavior is verified.
Multi-node usage records are verified.
Multi-node violation records are verified.
CSV export from small inbound tree results is verified.
Existing v0.1 / v0.2 / v0.3 / v0.4 tests still pass.
No existing WOM execution path is changed.
13. Notes for Codex

This is not Run Full Plan integration.

This is not GUI integration.

This is not optimization.

This is not costing integration.

This is a small, defensive, test-focused inbound Fan-In tree compatibility step.

The key goal is:

Confirm that the capacity planner can process a small INBOUND tree in PostOrder.

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
    Lots pass through a small inbound Fan-In road with multiple gates.

Please keep the implementation small, readable, and additive.