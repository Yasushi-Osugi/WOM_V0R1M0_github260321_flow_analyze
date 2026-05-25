# Codex Request: Implement with Capacity PSI Planning Engine v0.1

## 1. Request Summary

Please implement the first version of the **with Capacity PSI Planning Engine v0.1** for WOM.

This request is based on the design document:

```text
docs/design/with-capacity-psi-planning-engine-v0.1.md

The implementation must follow the design document as the primary reference.

The goal of this implementation is to add a new capacity-aware forward planning module without breaking the existing non-capacity PSI planning logic.

2. Important Implementation Principle

This implementation must be additive.

Do not replace or rewrite the existing non-capacity Forward Planning engine.

The existing WOM execution flow, GUI, sample scenarios, costing modules, and event extraction modules must continue to work as before.

The new with-capacity functionality should be implemented as a separate module that can be imported and tested independently.

3. Target Branch

The target branch is:

feature/with-capacity-psi-engine-v0r1
4. Required New Modules

Please create the following new package if it does not already exist:

pysi/capacity/

Recommended files:

pysi/capacity/__init__.py
pysi/capacity/capacity_model.py
pysi/capacity/capacity_master_loader.py
pysi/capacity/capacity_planning.py
pysi/capacity/capacity_exporter.py

If the current repository structure strongly suggests another location, such as pysi/engine/, it is acceptable to use that location.
However, the implementation should remain modular and isolated.

5. Required Data Classes

Please implement the following dataclasses in:

pysi/capacity/capacity_model.py
5.1 CapacityBucket
@dataclass
class CapacityBucket:
    scenario_id: str
    node_name: str
    product_name: str
    week: int | str
    capacity_type: Literal["P", "S", "I"]
    capacity_qty: int
    cap_mode: Literal["soft", "hard"] = "soft"
    unit: str = "LOT"
    priority: int = 100
    calendar_id: str = ""
    comment: str = ""
5.2 CapacityUsage
@dataclass
class CapacityUsage:
    scenario_id: str
    tree_side: str
    node_name: str
    product_name: str
    week: int | str
    capacity_type: Literal["P", "S", "I"]
    capacity_qty: int
    used_qty: int
    used_lot_ids: list[str]

    @property
    def remaining_qty(self) -> int:
        return max(self.capacity_qty - self.used_qty, 0)

    @property
    def utilization(self) -> float:
        if self.capacity_qty <= 0:
            return 0.0
        return self.used_qty / self.capacity_qty
5.3 CapacityViolation
@dataclass
class CapacityViolation:
    scenario_id: str
    tree_side: str
    node_name: str
    product_name: str
    week: int | str
    capacity_type: Literal["P", "S", "I"]
    cap_mode: Literal["soft", "hard"]
    capacity_qty: int
    required_qty: int
    overflow_qty: int
    violation_type: str
    overflow_lot_ids: list[str]
    action: str

Please use from __future__ import annotations to keep typing compatible.

6. capacity_master.csv Loader

Please implement a CSV loader in:

pysi/capacity/capacity_master_loader.py

Required function:

def load_capacity_master_csv(path: str | Path) -> list[CapacityBucket]:
    ...

The loader should read the following CSV format:

scenario_id,node_name,product_name,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
BASE,MOM_CHINA,IPHONE_NM_2028_BASE,2026-W01,P,120,soft,LOT,100,STD_CAL,weekly production capacity
BASE,DAD_US,IPHONE_NM_2028_BASE,2026-W01,I,500,soft,LOT,100,STD_CAL,inventory absorption capacity
BASE,DAD_US,IPHONE_NM_2028_BASE,2026-W01,S,150,soft,LOT,100,STD_CAL,shipping capacity

Loader requirements:

Accept str or Path
Validate required columns
Normalize:
capacity_type to uppercase
cap_mode to lowercase
Validate:
capacity_type must be one of P, S, I
cap_mode must be one of soft, hard
capacity_qty must be integer-compatible
Fill optional columns if missing:
unit = "LOT"
priority = 100
calendar_id = ""
comment = ""
Raise a clear ValueError for invalid input
7. capacity_master_sample.csv

Please add a sample CSV file:

pysi/master_data/capacity_master_sample.csv

Sample content:

scenario_id,node_name,product_name,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
BASE,MOM_CHINA,IPHONE_NM_2028_BASE,2026-W01,P,3,soft,LOT,100,STD_CAL,sample production capacity
BASE,MOM_CHINA,IPHONE_NM_2028_BASE,2026-W01,S,999999,soft,LOT,100,STD_CAL,no shipment limit sample
BASE,MOM_CHINA,IPHONE_NM_2028_BASE,2026-W01,I,999999,soft,LOT,100,STD_CAL,no inventory limit sample
BASE,DAD_COLD_DC,VACCINE_X,2026-W01,I,3,hard,LOT,100,COLD_CAL,sample cold storage hard capacity
BASE,MKT_HOSP,VACCINE_X,2026-W01,S,2,hard,LOT,100,COLD_CAL,sample vaccination capacity
8. Capacity Planning Core

Please implement the core functions in:

pysi/capacity/capacity_planning.py
8.1 build_capacity_lookup
def build_capacity_lookup(
    capacity_buckets: list[CapacityBucket],
) -> dict[tuple[str, str, str, int | str, str], CapacityBucket]:
    ...

Key:

(scenario_id, node_name, product_name, week, capacity_type)
8.2 get_capacity_bucket
def get_capacity_bucket(
    lookup: dict,
    *,
    scenario_id: str,
    node_name: str,
    product_name: str,
    week: int | str,
    capacity_type: Literal["P", "S", "I"],
    default_cap_mode: Literal["soft", "hard"] = "soft",
    missing_capacity_qty: int = 10**12,
) -> CapacityBucket:
    ...

Behavior:

First try exact match.
Then try wildcard product match where product_name == "*".
If not found, return a practically infinite capacity bucket.
Missing capacity should not break existing planning in v0.1.
8.3 split_lots_by_capacity
def split_lots_by_capacity(
    lot_ids: list[str],
    capacity_qty: int,
) -> tuple[list[str], list[str]]:
    ...

Example:

lot_ids = ["L1", "L2", "L3", "L4", "L5"]
capacity_qty = 3

executable = ["L1", "L2", "L3"]
overflow = ["L4", "L5"]
8.4 get_next_week
def get_next_week(
    weeks: list[int | str],
    current_week: int | str,
) -> int | str | None:
    ...

Return the next element in the supplied weeks list.
Return None if current_week is the last week.

9. with_capacity_forward_planning Skeleton

Please implement a first working skeleton:

def with_capacity_forward_planning(
    *,
    root_node,
    weeks: list[int | str],
    scenario_id: str,
    product_name: str,
    capacity_buckets: list[CapacityBucket],
    tree_side: Literal["OUTBOUND", "INBOUND"],
    node_order: list | None = None,
    default_cap_mode: Literal["soft", "hard"] = "soft",
) -> tuple[list[CapacityUsage], list[CapacityViolation]]:
    ...
Preconditions
Backward Planning has already completed demand placing.
node.psi4demand contains demand-placed lot lists.
node.psi4supply is available for writing execution results.
v0.1 Behavior

For each week and each node:

Apply P_cap to target P lots.
Apply S_cap to target S lots.
Apply I_cap to ending inventory lots.
Create CapacityUsage records.
Create CapacityViolation records when overflow exists.
In soft mode:
P/S overflow lots should be carried over to next week if possible.
I overflow should be recorded as ALERT_ONLY.
In hard mode:
P/S overflow should be recorded as BLOCKED.
I overflow should be recorded as WASTE.
Important

Because the actual Node implementation may differ, please isolate PSI access in small adapter functions.

Implement these helper functions in the same module:

def get_node_name(node) -> str:
    ...

def get_target_lots_for_P(node, week) -> list[str]:
    ...

def get_target_lots_for_S(node, week) -> list[str]:
    ...

def apply_P_execution(node, week, lot_ids: list[str]) -> None:
    ...

def apply_S_execution(node, week, lot_ids: list[str]) -> None:
    ...

def get_ending_inventory_lots(node, week) -> list[str]:
    ...

Default assumptions:

node.psi4demand[week][3]  # P
node.psi4demand[week][0]  # S
node.psi4supply[week][3]  # P
node.psi4supply[week][0]  # S
node.psi4supply[week][2]  # I

If the repository already has constants for PSI indexes, use those constants instead.

Please make these helper functions defensive enough to avoid crashing on missing PSI buckets where practical.

10. Tree Traversal

Please implement a helper:

def iter_nodes_for_capacity_forward(root_node, tree_side: str):
    ...

Behavior:

OUTBOUND: use preorder traversal
INBOUND: use postorder traversal

Because the current Node class may already have traversal helpers, please reuse existing traversal methods if available.

If no existing traversal helper is found, implement local fallback traversal using common attributes such as:

node.children
node.child_nodes
node.children_nodes

Keep this fallback simple and safe.

11. Export Functions

Please implement CSV exporters in:

pysi/capacity/capacity_exporter.py

Required functions:

def export_capacity_usage_csv(
    path: str | Path,
    records: list[CapacityUsage],
) -> None:
    ...
def export_capacity_violation_csv(
    path: str | Path,
    records: list[CapacityViolation],
) -> None:
    ...
capacity_usage.csv columns
scenario_id,tree_side,node_name,product_name,week,capacity_type,capacity_qty,used_qty,remaining_qty,utilization,used_lot_ids

used_lot_ids should be pipe-separated:

LOT001|LOT002|LOT003
capacity_violation.csv columns
scenario_id,tree_side,node_name,product_name,week,capacity_type,cap_mode,capacity_qty,required_qty,overflow_qty,violation_type,overflow_lot_ids,action

overflow_lot_ids should be pipe-separated.

The exporter should create parent directories if they do not exist.

12. Minimal Test / Smoke Test

Please add a minimal smoke test or sample runner.

Preferred file:

tests/test_capacity_planning_basic.py

If the repository does not currently use pytest, create a simple script instead:

tools/smoke_capacity_planning.py

Minimum test:

lot_ids = ["L1", "L2", "L3", "L4", "L5"]
capacity_qty = 3

Expected:

executable == ["L1", "L2", "L3"]
overflow == ["L4", "L5"]

Also test:

CapacityUsage.remaining_qty
CapacityUsage.utilization
CSV export functions
CSV loader on capacity_master_sample.csv
13. Do Not Modify Unless Necessary

Please do not modify the following unless absolutely necessary:

existing GUI files
existing costing modules
existing event extraction modules
existing non-capacity planning engine
existing sample scenario behavior

This implementation should be safe and isolated.

14. Expected Completion Criteria

The implementation is complete when:

The new capacity package or modules are added.
capacity_master_sample.csv is added.
load_capacity_master_csv() can read the sample file.
split_lots_by_capacity() works as expected.
CapacityUsage and CapacityViolation can be created.
CSV exporters generate valid output files.
with_capacity_forward_planning() exists and can be imported.
Existing WOM execution is not broken.
At least one basic smoke test or sample script runs successfully.
15. Notes for Codex

Please prefer small, readable, defensive code.

This is v0.1.
Do not over-engineer.

Do not implement optimization.
Do not implement GUI.
Do not implement costing.
Do not implement shelf-life logic.

The first goal is:

Read capacity.
Split lots.
Record usage.
Record violations.
Do not break existing WOM.

In WOM terms:

First, let WOM show where lots hit capacity.
Then, later, optimization can decide how to avoid it.