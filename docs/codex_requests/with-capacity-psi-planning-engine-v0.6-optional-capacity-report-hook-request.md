# Codex Request: with Capacity PSI Planning Engine v0.6
## Optional Capacity Report Hook after Existing Planning Pipeline

## 1. Request Summary

Please implement v0.6 of the **with Capacity PSI Planning Engine**.

This request is based on the design document:

```text
docs/design/with-capacity-psi-planning-engine-v0.6-optional-capacity-report-hook.md

v0.1 added the additive pysi.capacity package.

v0.2 added dummy-node PSI list integration tests.

v0.3 added real-WOM-compatible node tests.

v0.4 added small Outbound Tree integration tests using tree_side="OUTBOUND" and PreOrder traversal.

v0.5 added small Inbound Tree integration tests using tree_side="INBOUND" and PostOrder traversal.

v0.6 should add an optional capacity report hook that can run after an existing planning process and export capacity usage / violation reports.

The key goal is:

Add a safe diagnostic capacity report hook
without replacing or modifying the existing Forward Planning engine.

This is still not a capacity-constrained execution mode.

Do not modify the existing Run Full Plan behavior by default.

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

v0.5:
    Small Inbound Tree tests
    INBOUND PostOrder traversal
    MOM_TEST <- RAW_A_TEST / RAW_B_TEST

v0.6 should build on this existing implementation.

3. Important Concept

Please preserve the core WOM concept:

Monthly PSI on Capacity:
    numeric PSI calculation

Weekly WOM PSI with Capacity:
    lot_ID list operation under capacity constraints

The capacity planner must preserve lot identity.

Do not convert the weekly WOM PSI structure into pure numeric PSI calculations.

4. Required New Module

Please add:

pysi/capacity/capacity_report_hook.py

This module should provide a public function:

def run_capacity_report_hook(
    *,
    enabled: bool,
    scenario_id: str,
    product_name: str,
    weeks: list[int | str],
    outbound_root=None,
    inbound_root=None,
    capacity_master_path: str | Path | None = None,
    output_dir: str | Path = "outputs/capacity",
    strict_capacity_master: bool = False,
) -> tuple[list[CapacityUsage], list[CapacityViolation]]:
    ...

The function should return:

usage_records, violation_records

where:

usage_records: list[CapacityUsage]
violation_records: list[CapacityViolation]
5. Required Behavior
5.1 Disabled Hook

If enabled == False, the hook should immediately return empty lists.

Expected:

usage_records == []
violation_records == []

No output files are required.

5.2 Missing Capacity Master: Non-Strict Mode

If capacity_master_path is missing or does not exist and:

strict_capacity_master == False

the hook should not crash.

Expected:

usage_records == []
violation_records == []

This is important because existing WOM scenarios may not yet have capacity master files.

5.3 Missing Capacity Master: Strict Mode

If capacity_master_path is missing or does not exist and:

strict_capacity_master == True

the hook should raise a clear FileNotFoundError.

5.4 Outbound Report

If outbound_root is provided, the hook should run:

with_capacity_forward_planning(
    root_node=outbound_root,
    weeks=weeks,
    scenario_id=scenario_id,
    product_name=product_name,
    capacity_buckets=capacity_buckets,
    tree_side="OUTBOUND",
)

The returned usage and violation records should be included in the final result.

5.5 Inbound Report

If inbound_root is provided, the hook should run:

with_capacity_forward_planning(
    root_node=inbound_root,
    weeks=weeks,
    scenario_id=scenario_id,
    product_name=product_name,
    capacity_buckets=capacity_buckets,
    tree_side="INBOUND",
)

The returned usage and violation records should be included in the final result.

5.6 Combined Outbound and Inbound Report

If both outbound_root and inbound_root are provided, the hook should run both reports and combine the records.

Expected:

tree_side == OUTBOUND records exist
tree_side == INBOUND records exist

The output CSV files should contain both tree sides.

5.7 Output CSV

If the hook runs and records exist, export:

capacity_usage.csv
capacity_violation.csv

under:

output_dir

Default output location:

outputs/capacity/

Expected default files:

outputs/capacity/capacity_usage.csv
outputs/capacity/capacity_violation.csv

Use the existing exporters:

export_capacity_usage_csv()
export_capacity_violation_csv()
6. Required Imports

The new module should import:

from __future__ import annotations

from pathlib import Path

from pysi.capacity.capacity_exporter import (
    export_capacity_usage_csv,
    export_capacity_violation_csv,
)
from pysi.capacity.capacity_master_loader import load_capacity_master_csv
from pysi.capacity.capacity_model import CapacityUsage, CapacityViolation
from pysi.capacity.capacity_planning import with_capacity_forward_planning

Add any other minimal imports as needed.

7. Package Export

Please expose run_capacity_report_hook from:

pysi/capacity/__init__.py

So that this works:

from pysi.capacity import run_capacity_report_hook

Do not break existing package-level exports.

8. Required New Test File

Please add:

tests/test_capacity_report_hook.py

This test file should not depend on the full WOM Run Full Plan pipeline.

Use small test tree objects similar to v0.4 and v0.5.

The purpose is to test the hook wrapper safely before connecting it to the real planning pipeline.

9. Recommended Test Node Class

Inside tests/test_capacity_report_hook.py, define a lightweight test node class.

Example:

class HookTreeNode:
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
10. Required Tests
10.1 Disabled Hook No-Op Test

Test name:

def test_capacity_report_hook_disabled_noop():
    ...

Expected:

usage_records == []
violation_records == []
10.2 Missing Capacity Master Non-Strict Test

Test name:

def test_capacity_report_hook_missing_master_non_strict(tmp_path):
    ...

Call run_capacity_report_hook() with:

enabled=True
capacity_master_path=tmp_path / "missing_capacity_master.csv"
strict_capacity_master=False

Expected:

usage_records == []
violation_records == []

No exception should be raised.

10.3 Missing Capacity Master Strict Test

Test name:

def test_capacity_report_hook_missing_master_strict(tmp_path):
    ...

Call run_capacity_report_hook() with:

enabled=True
capacity_master_path=tmp_path / "missing_capacity_master.csv"
strict_capacity_master=True

Expected:

with pytest.raises(FileNotFoundError):
    ...
10.4 Outbound Capacity Report Hook Test

Test name:

def test_capacity_report_hook_outbound_tree_exports(tmp_path):
    ...

Create a small outbound tree:

MOM_TEST
    ↓
DAD_TEST
    ↓
MKT_TEST

Place PSI lots:

week = "2026-W01"

mom.psi4demand[week][3] = ["P1", "P2", "P3", "P4", "P5"]
dad.psi4supply[week][2] = ["I1", "I2", "I3", "I4"]
mkt.psi4demand[week][0] = ["S1", "S2", "S3", "S4"]

Create a temporary capacity master CSV under tmp_path:

scenario_id,node_name,product_name,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
BASE,MOM_TEST,TEST_PRODUCT,2026-W01,P,3,soft,LOT,100,STD_CAL,test MOM P cap
BASE,DAD_TEST,TEST_PRODUCT,2026-W01,I,3,soft,LOT,100,STD_CAL,test DAD I cap
BASE,MKT_TEST,TEST_PRODUCT,2026-W01,S,2,soft,LOT,100,STD_CAL,test MKT S cap

Run:

usage_records, violation_records = run_capacity_report_hook(
    enabled=True,
    scenario_id="BASE",
    product_name="TEST_PRODUCT",
    weeks=[week],
    outbound_root=mom,
    capacity_master_path=capacity_master_path,
    output_dir=tmp_path / "capacity_out",
)

Expected:

capacity_usage.csv exists
capacity_violation.csv exists
usage contains MOM_TEST / P
usage contains DAD_TEST / I
usage contains MKT_TEST / S
violation records are not empty
10.5 Inbound Capacity Report Hook Test

Test name:

def test_capacity_report_hook_inbound_tree_exports(tmp_path):
    ...

Create a small inbound tree:

MOM_TEST
├── RAW_A_TEST
└── RAW_B_TEST

Place PSI lots:

week = "2026-W01"

raw_a.psi4demand[week][3] = ["PA1", "PA2", "PA3", "PA4", "PA5"]
raw_b.psi4demand[week][0] = ["SB1", "SB2", "SB3", "SB4"]
mom.psi4supply[week][2] = ["IM1", "IM2", "IM3", "IM4"]

Create a temporary capacity master CSV under tmp_path:

scenario_id,node_name,product_name,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
BASE,RAW_A_TEST,TEST_PRODUCT,2026-W01,P,3,soft,LOT,100,STD_CAL,test RAW_A P cap
BASE,RAW_B_TEST,TEST_PRODUCT,2026-W01,S,2,soft,LOT,100,STD_CAL,test RAW_B S cap
BASE,MOM_TEST,TEST_PRODUCT,2026-W01,I,3,soft,LOT,100,STD_CAL,test MOM I cap

Run:

usage_records, violation_records = run_capacity_report_hook(
    enabled=True,
    scenario_id="BASE",
    product_name="TEST_PRODUCT",
    weeks=[week],
    inbound_root=mom,
    capacity_master_path=capacity_master_path,
    output_dir=tmp_path / "capacity_in",
)

Expected:

capacity_usage.csv exists
capacity_violation.csv exists
usage contains RAW_A_TEST / P
usage contains RAW_B_TEST / S
usage contains MOM_TEST / I
violation records are not empty
10.6 Combined Outbound and Inbound Report Hook Test

Test name:

def test_capacity_report_hook_combined_outbound_inbound(tmp_path):
    ...

Create both:

Outbound:
MOM_TEST -> DAD_TEST -> MKT_TEST

Inbound:
MOM_TEST <- RAW_A_TEST / RAW_B_TEST

Use one capacity master CSV that contains both outbound and inbound node capacity definitions.

Run:

usage_records, violation_records = run_capacity_report_hook(
    enabled=True,
    scenario_id="BASE",
    product_name="TEST_PRODUCT",
    weeks=[week],
    outbound_root=outbound_mom,
    inbound_root=inbound_mom,
    capacity_master_path=capacity_master_path,
    output_dir=tmp_path / "capacity_combined",
)

Expected:

usage records include tree_side == OUTBOUND
usage records include tree_side == INBOUND
violation records include tree_side == OUTBOUND
violation records include tree_side == INBOUND
capacity_usage.csv exists
capacity_violation.csv exists
11. Required Test Command

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

Alternative:

set PYTHONPATH=.
python -m pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py tests/test_capacity_planning_real_node.py tests/test_capacity_planning_small_outbound_tree.py tests/test_capacity_planning_small_inbound_tree.py tests/test_capacity_report_hook.py

Expected:

All tests pass.
12. Minimal Fix Policy

If v0.6 testing reveals small issues, minimal fixes are allowed.

Allowed fixes:

- add capacity_report_hook.py
- expose run_capacity_report_hook from pysi.capacity.__init__.py
- create parent output directories if needed
- make hook no-op behavior safe
- preserve existing v0.1 through v0.5 tests

Not allowed:

- replacing existing Forward Planning
- modifying Run Full Plan behavior by default
- modifying GUI
- modifying costing modules
- modifying event extraction modules
- adding optimization
- adding scenario master redesign
13. Do Not Modify Existing WOM Pipeline

Please do not modify:

existing GUI files
existing costing modules
existing event extraction modules
existing non-capacity planning engine
existing Run Full Plan pipeline
existing sample scenario behavior

v0.6 is still a post-planning diagnostic hook module.

The hook may later be connected to the existing WOM pipeline, but not in this implementation step.

14. Future Pipeline Integration

v0.6 only creates the hook function and tests it with small trees.

A later version may integrate it into the real WOM pipeline as:

if enable_capacity_report:
    run_capacity_report_hook(...)

The default should remain:

enable_capacity_report = False

until the hook is validated in actual WOM execution.

15. Expected Completion Criteria

v0.6 is complete when:

pysi/capacity/capacity_report_hook.py is added.
run_capacity_report_hook() is implemented.
run_capacity_report_hook is exposed from pysi.capacity.
The disabled no-op test passes.
The missing capacity master non-strict no-op test passes.
The missing capacity master strict error test passes.
The outbound hook export test passes.
The inbound hook export test passes.
The combined outbound / inbound hook test passes.
capacity_usage.csv and capacity_violation.csv are exported.
Existing v0.1 through v0.5 tests still pass.
No existing WOM execution path is changed.
16. Notes for Codex

This is not Run Full Plan integration.

This is not GUI integration.

This is not optimization.

This is not costing integration.

This is a small, defensive, test-focused capacity report hook step.

The key goal is:

Confirm that the capacity planner can be called as a safe optional report hook.

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
    A capacity checkpoint is placed after the existing planning road.

Please keep the implementation small, readable, additive, and safe.