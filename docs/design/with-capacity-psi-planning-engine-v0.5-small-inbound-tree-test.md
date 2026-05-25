# with Capacity PSI Planning Engine v0.5 Design
## Small Inbound Tree Integration Test

## 1. Purpose

This document defines the v0.5 design of the **with Capacity PSI Planning Engine**.

v0.1 introduced the additive `pysi.capacity` package.

v0.2 verified that the capacity planner can operate on a dummy WOM-like node.

v0.3 verified compatibility with a real-WOM-like node structure.

v0.4 verified that the capacity planner can process a small Outbound Tree using `tree_side="OUTBOUND"` and PreOrder traversal.

v0.5 takes the next step:

```text
Verify that with_capacity_forward_planning() can process a small Inbound Tree
using tree_side="INBOUND" and PostOrder traversal.

The goal is not yet Run Full Plan integration.

The goal is to confirm that the capacity planner can process multiple WOM-like nodes in a simple inbound Fan-In supply chain structure.

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

v0.5 is still a test-focused integration step.

3. Core Concept

The core WOM concept remains unchanged:

Weekly WOM with Capacity
= lot_ID list operation under capacity constraints

v0.5 should not convert PSI planning into numeric calculations.

The capacity planner must continue to preserve lot identity.

The test should verify that multiple inbound-side nodes can be processed in a Fan-In structure while keeping lot_ID lists visible in usage and violation records.

4. Scope of v0.5
4.1 In Scope

v0.5 should implement:

A small inbound tree test.
A minimal Fan-In tree structure such as:
RAW_A_TEST
RAW_B_TEST
    ↓
MOM_TEST

or, in tree form:

MOM_TEST
├── RAW_A_TEST
└── RAW_B_TEST
PostOrder traversal verification for tree_side="INBOUND".
Capacity buckets for multiple inbound nodes.
P_cap at RAW_A_TEST or RAW_B_TEST.
S_cap at RAW_A_TEST or RAW_B_TEST.
I_cap at MOM_TEST.
Capacity usage records from multiple nodes.
Capacity violation records from multiple nodes.
CSV export from small inbound tree result.
Verification that existing v0.1, v0.2, v0.3, and v0.4 tests still pass.
4.2 Out of Scope

v0.5 does not implement:

Run Full Plan pipeline integration
GUI integration
real scenario master integration
real inbound tree from existing master files
inbound Fan-In costing
event flow tracing
optimizer integration
alternative sourcing allocation
alternative lane selection
shelf life logic
temperature class logic
database integration

v0.5 is only a small inbound tree integration test.

5. Recommended Test File

Recommended new file:

tests/test_capacity_planning_small_inbound_tree.py

This file should define a lightweight inbound tree node class or reuse the small tree node pattern from v0.4.

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

Index	Symbol	Meaning
0	S	Ship / Sales / Supply
1	CO	Carry Over
2	I	Inventory
3	P	Production / Purchase
6. Small Inbound Tree Structure

The test tree should be:

MOM_TEST
├── RAW_A_TEST
└── RAW_B_TEST

This represents an inbound Fan-In structure where material or component nodes feed the MOM node.

Python construction example:

mom = SmallInboundTreeNode("MOM_TEST")
raw_a = SmallInboundTreeNode("RAW_A_TEST")
raw_b = SmallInboundTreeNode("RAW_B_TEST")

mom.add_child(raw_a)
mom.add_child(raw_b)

The root node is:

root_node = mom

The capacity planner should be called with:

tree_side="INBOUND"

For v0.5, the test should verify that INBOUND traversal uses PostOrder.

Expected PostOrder:

RAW_A_TEST → RAW_B_TEST → MOM_TEST

The exact order of RAW_A_TEST and RAW_B_TEST should follow the order in mom.children.

7. Test Case 1: INBOUND PostOrder Traversal
7.1 Purpose

Verify that iter_nodes_for_capacity_forward(root_node, "INBOUND") processes the small inbound tree in PostOrder.

7.2 Input Tree
MOM_TEST
├── RAW_A_TEST
└── RAW_B_TEST
7.3 Expected Order
["RAW_A_TEST", "RAW_B_TEST", "MOM_TEST"]

This confirms that inbound capacity planning uses material-side-to-MOM-side order.

8. Test Case 2: RAW_A P_cap in Small Inbound Tree
8.1 Purpose

Verify that RAW_A P_cap is applied within a small inbound tree.

8.2 Input
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
8.3 Expected Result
raw_a.psi4supply[week][3] == ["PA1", "PA2", "PA3"]

Expected violation:

node_name = RAW_A_TEST
capacity_type = P
overflow_qty = 2
violation_type = CAPACITY_OVER_SOFT
action = CARRY_OVER
9. Test Case 3: RAW_B S_cap Soft Overflow
9.1 Purpose

Verify that RAW_B S_cap is applied within a small inbound tree.

9.2 Input
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
9.3 Expected Result
raw_b.psi4supply[week][0] == ["SB1", "SB2"]

Expected violation:

node_name = RAW_B_TEST
capacity_type = S
overflow_qty = 2
violation_type = CAPACITY_OVER_SOFT
action = CARRY_OVER
10. Test Case 4: MOM I_cap Soft Overflow
10.1 Purpose

Verify that MOM inventory capacity is checked within a small inbound tree.

10.2 Input
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
10.3 Expected Result

Soft I_cap should not delete inventory lots.

mom.psi4supply[week][2] == ["IM1", "IM2", "IM3", "IM4"]

Expected violation:

node_name = MOM_TEST
capacity_type = I
required_qty = 4
overflow_qty = 1
violation_type = INVENTORY_OVER_SOFT
action = ALERT_ONLY
11. Test Case 5: Multi-Node Usage and Violation Records
11.1 Purpose

Verify that one call to with_capacity_forward_planning() over the small inbound tree produces records for multiple nodes.

11.2 Input

Use the same tree:

MOM_TEST
├── RAW_A_TEST
└── RAW_B_TEST

Use one week:

week = "2026-W01"

Place PSI lots:

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
11.3 Expected Result

Usage records should include at least:

RAW_A_TEST / P
RAW_B_TEST / S
MOM_TEST / I

Violation records should include:

RAW_A_TEST / CAPACITY_OVER_SOFT
RAW_B_TEST / CAPACITY_OVER_SOFT
MOM_TEST / INVENTORY_OVER_SOFT

The test should verify that records are generated for multiple inbound nodes.

12. Test Case 6: CSV Export from Small Inbound Tree Result
12.1 Purpose

Verify that usage and violation records generated from a small inbound tree can be exported.

12.2 Expected Output

Use tmp_path in pytest.

Expected files:

capacity_usage_small_inbound_tree.csv
capacity_violation_small_inbound_tree.csv

The test should confirm:

files are created
headers are correct
lot IDs are pipe-separated
multiple node names appear in the output
at least one usage record exists
at least one violation record exists
13. Recommended Test Names
def test_capacity_forward_inbound_postorder_traversal():
    ...

def test_with_capacity_forward_planning_small_inbound_tree_raw_a_p_cap():
    ...

def test_with_capacity_forward_planning_small_inbound_tree_raw_b_s_cap():
    ...

def test_with_capacity_forward_planning_small_inbound_tree_mom_i_cap_soft():
    ...

def test_with_capacity_forward_planning_small_inbound_tree_multi_node_records():
    ...

def test_capacity_export_from_small_inbound_tree_result(tmp_path):
    ...
14. Required Imports

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

15. Compatibility Requirements

The implementation should preserve all existing v0.1, v0.2, v0.3, and v0.4 tests.

Expected command:

PYTHONPATH=. pytest -q \
  tests/test_capacity_planning_basic.py \
  tests/test_capacity_planning_dummy_node.py \
  tests/test_capacity_planning_real_node.py \
  tests/test_capacity_planning_small_outbound_tree.py \
  tests/test_capacity_planning_small_inbound_tree.py

On Windows command prompt:

set PYTHONPATH=.
pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py tests/test_capacity_planning_real_node.py tests/test_capacity_planning_small_outbound_tree.py tests/test_capacity_planning_small_inbound_tree.py

Alternative:

set PYTHONPATH=.
python -m pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py tests/test_capacity_planning_real_node.py tests/test_capacity_planning_small_outbound_tree.py tests/test_capacity_planning_small_inbound_tree.py
16. Minimal Fix Policy

If small inbound tree testing reveals small issues in traversal or node compatibility, minimal fixes are allowed.

Allowed fixes:

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
17. Completion Criteria

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
18. Design Summary

v0.5 verifies that the capacity planner can process multiple nodes in a small inbound Fan-In supply chain tree.

It still does not connect to Run Full Plan.

It proves this:

The capacity planner can process a small INBOUND tree in PostOrder,
while preserving lot_ID list operations and recording capacity usage / violations.

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

The first goal is still not optimization.

The first goal is to make capacity collision visible at the Lot level across multiple inbound nodes.