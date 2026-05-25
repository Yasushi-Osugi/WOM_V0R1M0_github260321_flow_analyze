# with Capacity PSI Planning Engine v0.6 Design
## Optional Capacity Report Hook after Existing Planning Pipeline

## 1. Purpose

This document defines the v0.6 design of the **with Capacity PSI Planning Engine**.

v0.1 introduced the additive `pysi.capacity` package.

v0.2 verified dummy-node PSI list integration.

v0.3 verified real-WOM-compatible node compatibility.

v0.4 verified small Outbound Tree processing using PreOrder traversal.

v0.5 verified small Inbound Tree processing using PostOrder traversal.

v0.6 takes the next step:

```text
Connect the capacity planner to the existing WOM planning pipeline
as an optional capacity report hook after the existing planning flow.

The goal is not yet to replace the existing Forward Planning engine.

The goal is to run capacity diagnosis after the existing planning process and export capacity usage / violation reports.

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

v0.7:
    Connect report output to GUI or management cockpit.

v0.8:
    Consider capacity-constrained execution mode.

v0.6 is still a diagnostic mode, not a replacement planning mode.

3. Core Concept

The core WOM concept remains unchanged:

Weekly WOM with Capacity
= lot_ID list operation under capacity constraints

v0.6 must not convert WOM PSI into pure numeric PSI calculation.

Capacity diagnosis should operate on the existing psi4demand / psi4supply lot_ID list structures.

4. Design Principle

v0.6 follows this principle:

Do not break existing WOM planning.

Do not replace existing Forward Planning.

Add an optional capacity report step after planning.

This means the initial integration should be safe.

The existing planning pipeline should continue to run exactly as before when the capacity report hook is disabled.

5. Scope of v0.6
5.1 In Scope

v0.6 should implement:

Optional capacity report hook function.
A small wrapper that runs with_capacity_forward_planning() after existing planning.
Loading capacity master CSV from a configured path.
Exporting:
capacity_usage.csv
capacity_violation.csv
Support for Outbound tree capacity reporting.
Support for Inbound tree capacity reporting if root nodes are available.
Safe no-op behavior when capacity reporting is disabled.
Safe no-op behavior when capacity master file is missing, if configured as non-strict.
Minimal smoke test for the hook using small test trees.
Existing v0.1 through v0.5 tests must still pass.
5.2 Out of Scope

v0.6 does not implement:

replacing existing Forward Planning
modifying existing PSI planning logic
GUI integration
management cockpit integration
optimization
alternative MOM allocation
alternative lane selection
shelf life logic
temperature class logic
costing integration
event flow tracing integration
database integration

v0.6 is only an optional post-planning capacity report hook.

6. Target Position in Pipeline

The expected position is:

Existing Run Full Plan
    ↓
Existing Backward Planning
    ↓
Existing Forward Planning
    ↓
Existing Costing / Reporting / Event hooks as currently implemented
    ↓
Optional Capacity Report Hook
    ↓
capacity_usage.csv
capacity_violation.csv

The exact hook location may depend on the current repository structure.

Preferred location:

after existing PSI planning results are available
before or alongside reporting export

The hook must not alter the existing plan in v0.6.

7. Recommended New Module

Recommended file:

pysi/capacity/capacity_report_hook.py

Recommended public function:

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

This function should:

Return empty lists immediately if enabled == False.
Load capacity buckets if capacity_master_path exists.
If capacity master path is missing:
return empty result if strict_capacity_master == False
raise FileNotFoundError if strict_capacity_master == True
Run capacity planning for outbound tree if outbound_root is provided.
Run capacity planning for inbound tree if inbound_root is provided.
Export usage and violation CSV files.
Return all usage and violation records.
8. Output Files

Recommended output directory:

outputs/capacity/

Recommended output files:

outputs/capacity/capacity_usage.csv
outputs/capacity/capacity_violation.csv

If both outbound and inbound are processed, records should be combined into the same output files.

Each record already contains:

tree_side
node_name
week
capacity_type

Therefore, separate files for inbound/outbound are not required in v0.6.

Future versions may add:

capacity_usage_outbound.csv
capacity_usage_inbound.csv
capacity_violation_outbound.csv
capacity_violation_inbound.csv

but v0.6 should keep output simple.

9. Recommended Configuration Parameters

v0.6 may use direct function arguments first.

A later version may introduce config file or GUI parameters.

Recommended minimum parameters:

Parameter	Meaning
enabled	Whether capacity report hook runs
scenario_id	Scenario ID such as BASE
product_name	Product name
weeks	Planning weeks
outbound_root	Root node of outbound tree
inbound_root	Root node of inbound tree
capacity_master_path	Path to capacity master CSV
output_dir	Output directory
strict_capacity_master	Whether missing master is error
10. No-Op Behavior
10.1 Disabled Hook

If enabled == False, the hook should do nothing.

Expected behavior:

usage_records, violation_records = run_capacity_report_hook(
    enabled=False,
    ...
)

assert usage_records == []
assert violation_records == []
10.2 Missing Capacity Master in Non-Strict Mode

If capacity_master_path is missing and strict_capacity_master == False, the hook should not crash.

Expected behavior:

capacity report hook skipped
return [], []

This is important because existing WOM scenarios may not yet have capacity master files.

10.3 Missing Capacity Master in Strict Mode

If capacity_master_path is missing and strict_capacity_master == True, the hook should raise a clear FileNotFoundError.

11. Test Strategy

Recommended new test file:

tests/test_capacity_report_hook.py

This file should not depend on the full Run Full Plan pipeline.

It should use small test tree objects similar to v0.4 and v0.5.

The purpose is to test the hook wrapper itself before connecting it to the real pipeline.

12. Test Case 1: Disabled Hook No-Op
12.1 Purpose

Verify that the hook does nothing when disabled.

12.2 Expected Result
usage_records == []
violation_records == []

No output files should be required.

13. Test Case 2: Missing Capacity Master Non-Strict
13.1 Purpose

Verify safe no-op behavior when capacity master file does not exist and strict mode is disabled.

13.2 Expected Result
usage_records == []
violation_records == []

No exception should be raised.

14. Test Case 3: Missing Capacity Master Strict
14.1 Purpose

Verify that strict mode raises a clear error when the capacity master file is missing.

14.2 Expected Result
with pytest.raises(FileNotFoundError):
    run_capacity_report_hook(
        strict_capacity_master=True,
        ...
    )
15. Test Case 4: Outbound Capacity Report Hook
15.1 Purpose

Verify that the hook can run against a small outbound tree and export usage / violation files.

15.2 Tree
MOM_TEST
    ↓
DAD_TEST
    ↓
MKT_TEST
15.3 Capacity Master

Use a temporary CSV file under tmp_path.

Example:

scenario_id,node_name,product_name,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
BASE,MOM_TEST,TEST_PRODUCT,2026-W01,P,3,soft,LOT,100,STD_CAL,test MOM P cap
BASE,DAD_TEST,TEST_PRODUCT,2026-W01,I,3,soft,LOT,100,STD_CAL,test DAD I cap
BASE,MKT_TEST,TEST_PRODUCT,2026-W01,S,2,soft,LOT,100,STD_CAL,test MKT S cap
15.4 Expected Result

The hook should create:

capacity_usage.csv
capacity_violation.csv

The records should include:

MOM_TEST / P
DAD_TEST / I
MKT_TEST / S
16. Test Case 5: Inbound Capacity Report Hook
16.1 Purpose

Verify that the hook can run against a small inbound Fan-In tree and export usage / violation files.

16.2 Tree
MOM_TEST
├── RAW_A_TEST
└── RAW_B_TEST
16.3 Capacity Master

Use a temporary CSV file under tmp_path.

Example:

scenario_id,node_name,product_name,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
BASE,RAW_A_TEST,TEST_PRODUCT,2026-W01,P,3,soft,LOT,100,STD_CAL,test RAW_A P cap
BASE,RAW_B_TEST,TEST_PRODUCT,2026-W01,S,2,soft,LOT,100,STD_CAL,test RAW_B S cap
BASE,MOM_TEST,TEST_PRODUCT,2026-W01,I,3,soft,LOT,100,STD_CAL,test MOM I cap
16.4 Expected Result

The hook should create:

capacity_usage.csv
capacity_violation.csv

The records should include:

RAW_A_TEST / P
RAW_B_TEST / S
MOM_TEST / I
17. Test Case 6: Combined Outbound and Inbound Report Hook
17.1 Purpose

Verify that outbound and inbound reports can be combined in one hook call.

17.2 Expected Result

When both outbound_root and inbound_root are provided:

tree_side = OUTBOUND records exist
tree_side = INBOUND records exist

The output CSV files should contain records for both tree sides.

18. Recommended Test Names
def test_capacity_report_hook_disabled_noop():
    ...

def test_capacity_report_hook_missing_master_non_strict(tmp_path):
    ...

def test_capacity_report_hook_missing_master_strict(tmp_path):
    ...

def test_capacity_report_hook_outbound_tree_exports(tmp_path):
    ...

def test_capacity_report_hook_inbound_tree_exports(tmp_path):
    ...

def test_capacity_report_hook_combined_outbound_inbound(tmp_path):
    ...
19. Expected Imports

The hook module should import:

from pathlib import Path

from pysi.capacity.capacity_exporter import (
    export_capacity_usage_csv,
    export_capacity_violation_csv,
)
from pysi.capacity.capacity_master_loader import load_capacity_master_csv
from pysi.capacity.capacity_model import CapacityUsage, CapacityViolation
from pysi.capacity.capacity_planning import with_capacity_forward_planning

The tests should import:

from pysi.capacity.capacity_report_hook import run_capacity_report_hook
20. Expected Test Command

After v0.6 implementation, the following command should pass:

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
21. Minimal Fix Policy

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
22. Future Pipeline Integration

v0.6 only creates the hook function and tests it with small trees.

A later version may integrate it into the real WOM pipeline as:

if enable_capacity_report:
    run_capacity_report_hook(...)

The default should remain:

enable_capacity_report = False

until the hook is validated in actual WOM execution.

23. Completion Criteria

v0.6 is complete when:

pysi/capacity/capacity_report_hook.py is added.
run_capacity_report_hook() is implemented.
The hook supports disabled no-op behavior.
The hook supports missing capacity master non-strict no-op behavior.
The hook supports missing capacity master strict error behavior.
The hook can run outbound small tree report.
The hook can run inbound small tree report.
The hook can run combined outbound / inbound report.
Usage and violation CSV files are exported.
Existing v0.1 through v0.5 tests still pass.
No existing WOM execution path is changed.
24. Design Summary

v0.6 introduces an optional post-planning capacity report hook.

It still does not replace existing Forward Planning.

It proves this:

The capacity planner can be called as a safe diagnostic report step
after an existing planning process.

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

The first goal is still not optimization.

The first goal is to make capacity collision visible at the Lot level without changing existing WOM planning behavior.