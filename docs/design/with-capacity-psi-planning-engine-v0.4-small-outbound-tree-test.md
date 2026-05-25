# with Capacity PSI Planning Engine v0.4 Design
## Small Outbound Tree Integration Test

## 1. Purpose

This document defines the v0.4 design of the **with Capacity PSI Planning Engine**.

v0.1 introduced the additive `pysi.capacity` package.

v0.2 verified that the capacity planner can operate on a dummy WOM-like node.

v0.3 verified that the capacity planner can operate on a real-WOM-compatible node structure.

v0.4 takes the next step:

```text
Verify that with_capacity_forward_planning() can process a small Outbound Tree
using OUTBOUND PreOrder traversal.

The goal is not yet Run Full Plan integration.

The goal is to confirm that the capacity planner can process multiple WOM-like nodes in a simple outbound supply chain structure.

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

v0.4 is still a test-focused integration step.

3. Core Concept

The core WOM concept remains unchanged:

Weekly WOM with Capacity
= lot_ID list operation under capacity constraints

v0.4 should not convert PSI planning into numeric calculations.

The capacity planner must continue to preserve lot identity.

The test should verify that multiple nodes can be processed in a simple outbound tree while keeping lot_ID lists visible in usage and violation records.

4. Scope of v0.4
4.1 In Scope

v0.4 should implement:

A small outbound tree test.
A minimal tree structure such as:
MOM_TEST
    ↓
DAD_TEST
    ↓
MKT_TEST
PreOrder traversal verification for tree_side="OUTBOUND".
Capacity buckets for multiple nodes.
P_cap at MOM.
S_cap at DAD or MKT.
I_cap at DAD.
Capacity usage records from multiple nodes.
Capacity violation records from multiple nodes.
CSV export from small outbound tree result.
Verification that existing v0.1, v0.2, and v0.3 tests still pass.
4.2 Out of Scope

v0.4 does not implement:

Run Full Plan pipeline integration
GUI integration
real scenario master integration
real outbound tree from existing master files
inbound tree traversal
optimizer integration
alternative MOM allocation
alternative lane selection
costing logic
event flow tracing
database integration

v0.4 is only a small outbound tree integration test.

5. Recommended Test File

Recommended new file:

tests/test_capacity_planning_small_outbound_tree.py

This file should define a lightweight outbound tree node class or reuse the v0.3 real-like node if appropriate.

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

Index	Symbol	Meaning
0	S	Ship / Sales / Supply
1	CO	Carry Over
2	I	Inventory
3	P	Production / Purchase
6. Small Outbound Tree Structure

The test tree should be:

MOM_TEST
    ↓
DAD_TEST
    ↓
MKT_TEST

Python construction example:

mom = SmallTreeNode("MOM_TEST")
dad = SmallTreeNode("DAD_TEST")
mkt = SmallTreeNode("MKT_TEST")

mom.add_child(dad)
dad.add_child(mkt)

The root node is:

root_node = mom

The capacity planner should be called with:

tree_side="OUTBOUND"

For v0.4, the test may either:

Use automatic traversal from root_node, or
Pass explicit node_order=[mom, dad, mkt].

However, at least one test should verify that OUTBOUND traversal returns nodes in PreOrder:

MOM_TEST → DAD_TEST → MKT_TEST
7. Test Case 1: Outbound PreOrder Traversal
7.1 Purpose

Verify that iter_nodes_for_capacity_forward(root_node, "OUTBOUND") processes the small outbound tree in PreOrder.

7.2 Input Tree
MOM_TEST
    ↓
DAD_TEST
    ↓
MKT_TEST
7.3 Expected Order
["MOM_TEST", "DAD_TEST", "MKT_TEST"]

This confirms that outbound capacity planning uses supply-side-to-market-side order.

8. Test Case 2: MOM P_cap in Small Outbound Tree
8.1 Purpose

Verify that MOM P_cap is applied within a small outbound tree.

8.2 Input
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
8.3 Expected Result
mom.psi4supply[week][3] == ["P1", "P2", "P3"]

Expected violation:

node_name = MOM_TEST
capacity_type = P
overflow_qty = 2
violation_type = CAPACITY_OVER_SOFT
action = CARRY_OVER
9. Test Case 3: DAD I_cap Soft Overflow
9.1 Purpose

Verify that DAD inventory capacity is checked within a small outbound tree.

9.2 Input
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
9.3 Expected Result

Soft I_cap should not delete inventory lots.

dad.psi4supply[week][2] == ["I1", "I2", "I3", "I4"]

Expected violation:

node_name = DAD_TEST
capacity_type = I
required_qty = 4
overflow_qty = 1
violation_type = INVENTORY_OVER_SOFT
action = ALERT_ONLY
10. Test Case 4: MKT S_cap Soft Overflow
10.1 Purpose

Verify that MKT S_cap is applied within a small outbound tree.

10.2 Input
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
10.3 Expected Result
mkt.psi4supply[week][0] == ["S1", "S2"]

Expected violation:

node_name = MKT_TEST
capacity_type = S
overflow_qty = 2
violation_type = CAPACITY_OVER_SOFT
action = CARRY_OVER
11. Test Case 5: Multi-Node Usage and Violation Records
11.1 Purpose

Verify that one call to with_capacity_forward_planning() over the small outbound tree produces records for multiple nodes.

11.2 Input

Use the same tree:

MOM_TEST → DAD_TEST → MKT_TEST

Use one week:

week = "2026-W01"

Place PSI lots:

mom.psi4demand[week][3] = ["P1", "P2", "P3", "P4", "P5"]
dad.psi4supply[week][2] = ["I1", "I2", "I3", "I4"]
mkt.psi4demand[week][0] = ["S1", "S2", "S3", "S4"]

Capacity buckets:

[
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
11.3 Expected Result

Usage records should include at least:

MOM_TEST / P
DAD_TEST / I
MKT_TEST / S

Violation records should include:

MOM_TEST / CAPACITY_OVER_SOFT
DAD_TEST / INVENTORY_OVER_SOFT
MKT_TEST / CAPACITY_OVER_SOFT

The test should verify that records are generated for multiple nodes.

12. Test Case 6: CSV Export from Small Outbound Tree Result
12.1 Purpose

Verify that usage and violation records generated from a small outbound tree can be exported.

12.2 Expected Output

Use tmp_path in pytest.

Expected files:

capacity_usage_small_outbound_tree.csv
capacity_violation_small_outbound_tree.csv

The test should confirm:

files are created
headers are correct
lot IDs are pipe-separated
multiple node names appear in the output
at least one usage record exists
at least one violation record exists
13. Recommended Test Names
def test_capacity_forward_outbound_preorder_traversal():
    ...

def test_with_capacity_forward_planning_small_outbound_tree_mom_p_cap():
    ...

def test_with_capacity_forward_planning_small_outbound_tree_dad_i_cap_soft():
    ...

def test_with_capacity_forward_planning_small_outbound_tree_mkt_s_cap():
    ...

def test_with_capacity_forward_planning_small_outbound_tree_multi_node_records():
    ...

def test_capacity_export_from_small_outbound_tree_result(tmp_path):
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

The implementation should preserve all existing v0.1, v0.2, and v0.3 tests.

Expected command:

PYTHONPATH=. pytest -q \
  tests/test_capacity_planning_basic.py \
  tests/test_capacity_planning_dummy_node.py \
  tests/test_capacity_planning_real_node.py \
  tests/test_capacity_planning_small_outbound_tree.py

On Windows command prompt:

set PYTHONPATH=.
pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py tests/test_capacity_planning_real_node.py tests/test_capacity_planning_small_outbound_tree.py

Alternative:

set PYTHONPATH=.
python -m pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py tests/test_capacity_planning_real_node.py tests/test_capacity_planning_small_outbound_tree.py
16. Minimal Fix Policy

If small outbound tree testing reveals small issues in traversal or node compatibility, minimal fixes are allowed.

Allowed fixes:

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
17. Completion Criteria

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
18. Design Summary

v0.4 verifies that the capacity planner can process multiple nodes in a small outbound supply chain tree.

It still does not connect to Run Full Plan.

It proves this:

The capacity planner can process a small OUTBOUND tree in PreOrder,
while preserving lot_ID list operations and recording capacity usage / violations.

In WOM terms:

v0.1:
    The capacity gate was built.

v0.2:
    Dummy lots passed through the gate.

v0.3:
    Real-WOM-compatible lots passed through the gate.

v0.4:
    Lots pass through a small outbound road with multiple gates.

The first goal is still not optimization.

The first goal is to make capacity collision visible at the Lot level across multiple outbound nodes.