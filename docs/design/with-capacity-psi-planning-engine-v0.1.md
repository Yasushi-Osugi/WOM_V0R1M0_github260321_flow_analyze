# with Capacity PSI Planning Engine v0.1 Design

## 1. Purpose

This document defines the v0.1 design of the **with Capacity PSI Planning Engine** for WOM.

The purpose of this module is to extend the existing PSI Forward Planning process so that it can consider weekly capacity constraints at each Node.

The engine assumes that **Backward Planning has already completed demand placing**.  
In other words, demand lots have already been placed on each node's `psi4demand` time series.

The with Capacity PSI Planning Engine takes this demand-placed state as input, and performs Forward Planning while checking weekly capacity constraints.

The key output is not only the PSI result itself, but also:

- which lots could be executed within capacity
- which lots exceeded capacity
- which node and week became a bottleneck
- how much capacity was used
- which lots were delayed, carried over, blocked, or wasted

This module is a core step toward making WOM a planning engine that can represent real-world executable constraints.

---

## 2. Background

The current non-capacity Forward Planning can move lots through the PSI structure without considering the upper limits of node capability.

However, in real supply chains, each node has constraints such as:

- production capacity
- purchase capacity
- shipment capacity
- sales capacity
- storage capacity
- cold storage capacity
- vaccination capacity
- handling capacity

Therefore, WOM needs a planning mode where lots are forwarded only within the available capacity of each node and week.

This design is based on the prior Monthly PSI on Capacity concept, where three capacity constraints were defined:

| Constraint | Meaning |
|---|---|
| `P_cap` | Production / Purchase / Processing capacity |
| `S_cap` | Shipment / Sales / Consumption capacity |
| `I_cap` | Inventory / Storage capacity |

In the Weekly WOM engine, these constraints are applied to Lot-based PSI lists.

---

## 3. Scope of v0.1

### 3.1 In Scope

v0.1 implements the following minimum functions:

1. Read `capacity_master.csv`
2. Define `CapacityBucket`
3. Define `CapacityUsage`
4. Define `CapacityViolation`
5. Apply weekly `P_cap`, `S_cap`, and `I_cap`
6. Split lot lists into executable lots and overflow lots
7. Record capacity usage
8. Record capacity violation
9. Support `soft` and `hard` capacity modes
10. Export:
   - `capacity_usage.csv`
   - `capacity_violation.csv`

### 3.2 Out of Scope

The following functions are intentionally excluded from v0.1:

- optimization
- automatic alternative MOM allocation
- automatic alternative lane selection
- multi-resource capacity
- shelf life control
- temperature class control
- cost evaluation
- event flow tracing
- inbound Fan-In costing
- GUI enhancement
- database implementation

These functions may be added in later versions.

---

## 4. Planning Assumption

The with Capacity PSI Planning Engine is executed after Backward Planning.

### 4.1 Input State

The input state is:

```text
Backward Planning completed
↓
Demand placing completed
↓
Each node has demand lots in psi4demand
↓
with Capacity Forward Planning starts

The engine does not generate demand.
The engine does not perform demand placing.

It only processes demand-placed lots under capacity constraints.

5. PSI List Structure

WOM nodes maintain PSI lists by week.

The assumed structure is:

node.psi4demand[week][0]  # S
node.psi4demand[week][1]  # CO
node.psi4demand[week][2]  # I
node.psi4demand[week][3]  # P

node.psi4supply[week][0]  # S
node.psi4supply[week][1]  # CO
node.psi4supply[week][2]  # I
node.psi4supply[week][3]  # P

Where:

Index	Symbol	Meaning
0	S	Ship / Sales / Supply
1	CO	Carry Over
2	I	Inventory
3	P	Production / Purchase

v0.1 assumes that each element is a list of lot_id.

node.psi4demand[week][0] = ["LOT001", "LOT002", ...]

v0.1 assumes:

1 lot_id = 1 capacity unit

Future versions may support lot quantity conversion.

6. Capacity Types
6.1 P Capacity

P_cap represents how many lots can be produced, purchased, received, or processed by the node in a week.

Examples:

production capacity at MOM
purchase capacity at procurement node
inbound processing capacity
bottleneck process capacity
P_cap = weekly generation / processing capacity
6.2 S Capacity

S_cap represents how many lots can be shipped, sold, consumed, or dispatched by the node in a week.

Examples:

shipping capacity at DAD
sales capacity at market node
vaccination capacity at hospital node
dispatch capacity at warehouse node
S_cap = weekly flow-out / consumption capacity
6.3 I Capacity

I_cap represents how many lots can be held at the node at the end of a week.

Examples:

warehouse storage capacity
cold storage capacity
buffer stock capacity
market inventory absorption capacity
I_cap = ending inventory capacity
7. Capacity Mode

Capacity has two modes.

Mode	Meaning	Typical Use
soft	Capacity can be exceeded, but violation is recorded	phone, rice, general inventory
hard	Capacity cannot be exceeded; overflow is blocked or wasted	pharma cold chain, expiry-sensitive product
7.1 Soft Cap

In soft mode:

overflow lots are not deleted
overflow lots are carried over or marked as over-cap
violation records are created
PSI can still show the overloaded state

Example:

Inventory exceeds warehouse guideline
↓
Do not waste product
↓
Record over-cap alert
7.2 Hard Cap

In hard mode:

overflow lots cannot be accepted or retained
overflow lots are blocked or wasted
violation records are created

Example:

Cold storage capacity exceeded
↓
Overflow lots cannot be stored
↓
Record waste / blocked lots
8. capacity_master.csv
8.1 File Location

Recommended sample file location:

pysi/master_data/capacity_master_sample.csv

Future scenario-specific files may be placed under scenario directories.

8.2 CSV Format
scenario_id,node_name,product_name,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
BASE,MOM_CHINA,IPHONE_NM_2028_BASE,2026-W01,P,120,soft,LOT,100,STD_CAL,weekly production capacity
BASE,DAD_US,IPHONE_NM_2028_BASE,2026-W01,I,500,soft,LOT,100,STD_CAL,inventory absorption capacity
BASE,DAD_US,IPHONE_NM_2028_BASE,2026-W01,S,150,soft,LOT,100,STD_CAL,shipping capacity
BASE,DAD_COLD_DC,VACCINE_X,2026-W01,I,300,hard,LOT,100,COLD_CAL,cold storage capacity
BASE,MKT_HOSP,VACCINE_X,2026-W01,S,80,hard,LOT,100,COLD_CAL,vaccination capacity
8.3 Column Definition
Column	Required	Description
scenario_id	Yes	Scenario ID such as BASE, ASIS, TOBE
node_name	Yes	Target node name
product_name	Yes	Target product name. * can be used as wildcard
week	Yes	Planning week. Example: 2026-W01
capacity_type	Yes	P, S, or I
capacity_qty	Yes	Capacity quantity in lot units
cap_mode	Yes	soft or hard
unit	Optional	Usually LOT in v0.1
priority	Optional	Priority when multiple rules exist
calendar_id	Optional	Calendar ID for future extension
comment	Optional	Free text
9. Core Data Classes
9.1 CapacityBucket
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
9.2 CapacityUsage
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
9.3 CapacityViolation
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
10. Processing Logic
10.1 Basic Lot Split

The core operation is to split lot lists by capacity.

def split_lots_by_capacity(
    lot_ids: list[str],
    capacity_qty: int,
) -> tuple[list[str], list[str]]:
    executable_lots = lot_ids[:capacity_qty]
    overflow_lots = lot_ids[capacity_qty:]
    return executable_lots, overflow_lots
10.2 Basic Flow

For each week and node:

1. Read demand-placed P lots
2. Apply P_cap
3. Move executable P lots to supply PSI
4. Record P capacity usage
5. Record P capacity violation if overflow exists

6. Read demand-placed S lots
7. Apply S_cap
8. Move executable S lots to supply PSI
9. Record S capacity usage
10. Record S capacity violation if overflow exists

11. Read ending inventory lots
12. Apply I_cap
13. Record I capacity usage
14. Record I capacity violation if inventory exceeds cap
11. Function Skeleton

The main function should be added as a new function.
It must not replace the existing non-capacity Forward Planning.

Recommended name:

with_capacity_forward_planning()

Recommended module:

pysi/engine/capacity_planning.py

Skeleton:

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
    """
    Execute Forward Planning with weekly P/S/I capacity constraints.

    Preconditions:
        - Backward Planning has already completed demand placing.
        - node.psi4demand contains demand-placed lot lists.
        - node.psi4supply is available for writing execution result.

    Returns:
        - capacity usage records
        - capacity violation records
    """
12. Tree Traversal

The engine should support both Outbound and Inbound trees.

12.1 Outbound Tree

Outbound tree is processed in PreOrder.

Supply side
↓
DAD
↓
Market leaf
12.2 Inbound Tree

Inbound tree is processed in PostOrder.

Material / component leaf
↓
MOM

Recommended helper:

def iter_nodes_for_capacity_forward(root_node, tree_side: str):
    if tree_side == "OUTBOUND":
        yield from preorder(root_node)
    elif tree_side == "INBOUND":
        yield from postorder(root_node)
    else:
        raise ValueError(f"unknown tree_side: {tree_side}")
13. Output Files
13.1 capacity_usage.csv

Recommended output location:

outputs/capacity/capacity_usage.csv

Format:

scenario_id,tree_side,node_name,product_name,week,capacity_type,capacity_qty,used_qty,remaining_qty,utilization,used_lot_ids
BASE,OUTBOUND,DAD_US,IPHONE_NM_2028_BASE,2026-W01,S,150,142,8,0.9467,LOT001|LOT002|LOT003
BASE,INBOUND,MOM_CHINA,IPHONE_NM_2028_BASE,2026-W01,P,120,120,0,1.0000,LOT101|LOT102
13.2 capacity_violation.csv

Recommended output location:

outputs/capacity/capacity_violation.csv

Format:

scenario_id,tree_side,node_name,product_name,week,capacity_type,cap_mode,capacity_qty,required_qty,overflow_qty,violation_type,overflow_lot_ids,action
BASE,INBOUND,MOM_CHINA,IPHONE_NM_2028_BASE,2026-W01,P,soft,120,150,30,CAPACITY_OVER_SOFT,LOT131|LOT132|LOT133,CARRY_OVER
BASE,OUTBOUND,DAD_COLD_DC,VACCINE_X,2026-W01,I,hard,300,340,40,INVENTORY_OVER_HARD,LOT901|LOT902,WASTE
14. Violation Types

Minimum violation types for v0.1:

Type	Meaning
CAPACITY_OVER_SOFT	P/S capacity exceeded in soft mode
CAPACITY_OVER_HARD	P/S capacity exceeded in hard mode
INVENTORY_OVER_SOFT	I capacity exceeded in soft mode
INVENTORY_OVER_HARD	I capacity exceeded in hard mode
NO_CAPACITY_MASTER	Capacity master not found
ZERO_CAPACITY	Capacity is zero
15. Action Types

Minimum action types for v0.1:

Action	Meaning
EXECUTE	Lot was processed within capacity
CARRY_OVER	Lot was delayed to next week
ALERT_ONLY	Soft cap exceeded but lot remains
BLOCKED	Hard cap prevented execution
WASTE	Hard inventory cap caused waste
NO_ACTION	Violation was recorded only
16. Default Behavior
16.1 Missing Capacity

In v0.1, missing capacity should not break existing planning.

Recommended default:

If capacity is missing:
    use practically infinite capacity
    record optional warning

This avoids breaking existing scenarios.

Future versions may support strict mode:

strict_capacity=True

where missing capacity becomes an error.

16.2 Capacity Quantity Zero

If capacity_qty = 0, no lots can be executed.

This should generate a ZERO_CAPACITY or capacity over violation.

17. Adapter Functions

Existing PSI list access should be isolated in adapter functions.

Recommended helper functions:

def get_target_lots_for_P(node, week) -> list[str]:
    return list(node.psi4demand[week][3])

def get_target_lots_for_S(node, week) -> list[str]:
    return list(node.psi4demand[week][0])

def apply_P_execution(node, week, lot_ids: list[str]) -> None:
    node.psi4supply[week][3].extend(lot_ids)

def apply_S_execution(node, week, lot_ids: list[str]) -> None:
    node.psi4supply[week][0].extend(lot_ids)

def get_ending_inventory_lots(node, week) -> list[str]:
    return list(node.psi4supply[week][2])

These functions may need adjustment based on the actual current Node implementation.

18. Implementation Policy

v0.1 must be implemented as an additive module.

18.1 Must Not Break

The implementation must not break:

existing non-capacity Forward Planning
existing GUI execution
existing sample scenarios
existing costing modules
existing event extraction modules
18.2 Recommended New Files

Recommended new files:

pysi/engine/capacity_planning.py
pysi/engine/capacity_master_loader.py
pysi/engine/capacity_exporter.py
pysi/master_data/capacity_master_sample.csv

Alternative package location is also acceptable:

pysi/capacity/

For example:

pysi/capacity/__init__.py
pysi/capacity/capacity_model.py
pysi/capacity/capacity_master_loader.py
pysi/capacity/capacity_planning.py
pysi/capacity/capacity_exporter.py

The implementation should choose the location that best fits the current repository structure.

19. Test Policy

v0.1 should include at least one minimal test or sample runner.

19.1 Minimum Test Case

Create a simple node with 5 demand lots and capacity 3.

Input:

lot_ids = ["L1", "L2", "L3", "L4", "L5"]
capacity_qty = 3

Expected result:

executable = ["L1", "L2", "L3"]
overflow = ["L4", "L5"]
19.2 Expected Validation

The test should confirm:

lot split works
usage record is created
violation record is created
utilization is calculated correctly
output CSV can be written
20. Future Extension

Future versions may add:

alternative MOM allocation
alternative lane selection
optimizer integration
shelf life constraint
temperature class constraint
resource calendar
shift calendar
cost impact of capacity shortage
event flow tracing integration
GUI visualization of capacity utilization
SQL-based capacity master
21. Design Summary

The with Capacity PSI Planning Engine v0.1 is defined as follows:

Input:
    Demand-placed PSI state after Backward Planning

Process:
    Forward Planning with weekly P/S/I capacity constraints

Core:
    Split lot lists into executable lots and overflow lots

Output:
    Updated supply PSI
    capacity_usage.csv
    capacity_violation.csv

Principle:
    Existing non-capacity planning must remain unchanged

This design keeps the first implementation simple.

The first goal is not optimization.
The first goal is to make bottlenecks visible.

First, let WOM show where lots hit capacity.
Then, let optimization decide how to avoid it.