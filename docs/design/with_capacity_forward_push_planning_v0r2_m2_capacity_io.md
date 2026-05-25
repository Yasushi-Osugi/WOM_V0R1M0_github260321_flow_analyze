# With-Capacity PSI Engine v0r2-m2 Design Memo
## Capacity Master Loader and Usage / Violation CSV Output

## 1. Purpose

This document defines the design scope and implementation approach for:

```text
with-capacity PSI engine v0r2-m2

The purpose of v0r2-m2 is to add the data I/O layer for Forward PUSH with Capacity Planning.

v0r2-m1 already implemented the standalone MVP planner logic:

requested lots
capacity
accepted lots
blocked lots
capacity issue

v0r2-m2 extends this foundation by adding:

capacity_master.csv loader
CapacityUsage records
CapacityViolation records
usage / violation CSV export

v0r2-m2 does not yet connect the planner deeply into the real WOM Node.psi4demand / psi4supply structure.
That will be handled in v0r2-m3.

2. Background

The overall with-capacity PSI engine roadmap is:

v0r1:
    capacity report / hook / runner foundation

v0r2-m1:
    standalone Forward PUSH with Capacity planner MVP

v0r2-m2:
    capacity master loader and usage / violation output

v0r2-m3:
    connection to WOM Node.psi4demand / psi4supply

v0r3:
    bottleneck allocation rule enhancement

v0r2-m2 is the bridge between the standalone planner and real WOM scenario data.

The key question for v0r2-m2 is:

How should weekly capacity definitions be loaded,
and how should capacity usage and bottleneck violations be recorded?
3. Design Principle

The key design principles are:

1. Keep the original Forward PUSH planner unchanged.
2. Keep the v0r2-m1 standalone planner behavior unchanged unless necessary.
3. Add capacity I/O as small, isolated, testable components.
4. Use an integrated capacity_master.csv first.
5. Export capacity usage and violation records in simple CSV format.
6. Do not implement advanced allocation rules in v0r2-m2.
7. Do not implement GUI integration in v0r2-m2.

v0r2-m2 is not an optimization milestone.

It is a data foundation milestone.

4. Scope
4.1 In Scope

v0r2-m2 should implement:

capacity_master.csv schema
capacity master loader
CapacityBucket / CapacityMasterRecord data structure
CapacityUsage data structure
CapacityViolation data structure
capacity lookup by scenario / node / product / week / capacity_type
product_name='*' fallback
capacity_usage.csv export
capacity_violation.csv export
smoke runner update or new smoke runner for CSV I/O
basic tests
4.2 Out of Scope

v0r2-m2 should not implement:

WOM Node.psi4demand / psi4supply integration
automatic carryover into future PSI weeks
advanced allocation rules
profit-based priority
market priority
multi-bottleneck optimization
PULL integration
GUI integration
management cockpit integration
costing integration
SQL persistence

These are later milestones.

5. capacity_master.csv Schema

For v0r2-m2, use a single integrated CSV file.

Recommended path:

pysi/master_data/capacity_master_sample.csv

or, if existing repository convention suggests a better location, follow the existing convention.

5.1 Header
scenario_id,tree_side,node_name,product_name,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
5.2 Example
scenario_id,tree_side,node_name,product_name,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
BASE,INBOUND,MOM_CHINA,IPHONE_NM_2028_BASE,2026-W01,P,120,soft,LOT,100,STD_CAL,weekly production capacity
BASE,OUTBOUND,DAD_US,IPHONE_NM_2028_BASE,2026-W01,S,150,soft,LOT,100,STD_CAL,weekly shipping capacity
BASE,OUTBOUND,DAD_US,IPHONE_NM_2028_BASE,2026-W01,I,500,soft,LOT,100,STD_CAL,inventory absorption capacity
BASE,OUTBOUND,DAD_COLD_DC,VACCINE_X,2026-W01,I,300,hard,LOT,100,COLD_CAL,cold storage capacity
BASE,OUTBOUND,MKT_HOSP,VACCINE_X,2026-W01,S,80,hard,LOT,100,COLD_CAL,vaccination capacity
BASE,INBOUND,MOM_CHINA,*,2026-W02,P,200,soft,LOT,100,STD_CAL,wildcard product capacity
6. Column Definition
Column	Required	Description
scenario_id	Yes	Scenario name such as BASE / ASIS / TOBE / PORT_STOP
tree_side	Yes	INBOUND / OUTBOUND / E2E
node_name	Yes	Node that owns the capacity
product_name	Yes	Product-specific capacity. * means product wildcard
week	Yes	Planning week such as 2026-W01 or WOM internal week key
capacity_type	Yes	P, S, or I
capacity_qty	Yes	Capacity quantity in LOT unit
cap_mode	Yes	soft or hard
unit	Optional	Default should be LOT
priority	Optional	Priority when duplicate records exist
calendar_id	Optional	Calendar ID. Not used in v0r2-m2 logic
comment	Optional	Free description
7. Capacity Type Semantics
7.1 P capacity
capacity_type = P

P capacity is a flow capacity.

It represents the number of lots that a node can produce, purchase, receive, or process in a week.

7.2 S capacity
capacity_type = S

S capacity is a flow capacity.

It represents the number of lots that a node can ship, sell, consume, or dispatch in a week.

7.3 I capacity
capacity_type = I

I capacity is a stock capacity.

It represents the number of lots that can be held at the end of the week.

7.4 Important distinction
P / S capacity:
    weekly flow upper bound

I capacity:
    end-of-week stock upper bound

v0r2-m2 should define this distinction in data structures and comments, but the first implementation may focus on P / S flow capacity export.

Full I capacity enforcement can be expanded later.

8. cap_mode Semantics
8.1 soft
cap_mode = soft

Soft capacity means the plan may exceed capacity, but the excess should be recorded as a violation or management alert.

Recommended default action:

CARRY_OVER
8.2 hard
cap_mode = hard

Hard capacity means the plan must not exceed capacity.

Recommended default actions:

P / S hard cap:
    BLOCK

I hard cap:
    REJECT or WASTE

v0r2-m2 only records the action in CapacityViolation.
It does not need to execute sophisticated recovery logic.

9. Missing Capacity Policy

v0r2-m1 used the policy:

missing capacity means unlimited capacity

v0r2-m2 should keep this as the default policy for compatibility.

Reason:

Existing WOM scenarios may not yet define full capacity data.

Therefore:

capacity master record found:
    apply capacity check

capacity master record not found:
    treat as unlimited capacity
    do not block lots by default

Optional diagnostic behavior may be added later, but default behavior should not break existing scenarios.

10. Product Wildcard Fallback

The loader should support product wildcard records.

Lookup order:

1. exact key:
   scenario_id, tree_side, node_name, product_name, week, capacity_type

2. wildcard product key:
   scenario_id, tree_side, node_name, "*", week, capacity_type

3. missing:
   unlimited capacity by default

This makes it possible to define capacity at node level without listing every product.

11. Duplicate Record Policy

If duplicate capacity records exist for the same key, use the following rule for v0r2-m2:

higher priority wins

If priority is missing or equal:

last record wins

The loader should keep the implementation simple and deterministic.

12. Data Structures
12.1 CapacityMasterRecord
@dataclass
class CapacityMasterRecord:
    scenario_id: str
    tree_side: str
    node_name: str
    product_name: str
    week: str
    capacity_type: str
    capacity_qty: int
    cap_mode: str = "soft"
    unit: str = "LOT"
    priority: int = 100
    calendar_id: str = ""
    comment: str = ""
12.2 CapacityUsage
@dataclass
class CapacityUsage:
    scenario_id: str
    tree_side: str
    node_name: str
    product_name: str
    week: str
    capacity_type: str
    capacity_qty: int
    used_qty: int
    used_lot_ids: list[str] = field(default_factory=list)

    @property
    def remaining_qty(self) -> int:
        return max(self.capacity_qty - self.used_qty, 0)

    @property
    def utilization(self) -> float:
        if self.capacity_qty <= 0:
            return 0.0
        return self.used_qty / self.capacity_qty
12.3 CapacityViolation
@dataclass
class CapacityViolation:
    scenario_id: str
    tree_side: str
    node_name: str
    product_name: str
    week: str
    capacity_type: str
    cap_mode: str
    capacity_qty: int
    required_qty: int
    overflow_qty: int
    violation_type: str
    overflow_lot_ids: list[str] = field(default_factory=list)
    action: str = "CARRY_OVER"
13. capacity_usage.csv Output

Recommended output path:

outputs/capacity/forward_push_with_capacity_usage.csv
13.1 Header
scenario_id,tree_side,node_name,product_name,week,capacity_type,capacity_qty,used_qty,remaining_qty,utilization,used_lot_ids
13.2 Example
scenario_id,tree_side,node_name,product_name,week,capacity_type,capacity_qty,used_qty,remaining_qty,utilization,used_lot_ids
BASE,INBOUND,MOM_CHINA,IPHONE_NM_2028_BASE,2026-W01,P,120,120,0,1.0000,LOT001|LOT002|LOT003
BASE,OUTBOUND,DAD_US,IPHONE_NM_2028_BASE,2026-W01,S,150,142,8,0.9467,LOT101|LOT102
14. capacity_violation.csv Output

Recommended output path:

outputs/capacity/forward_push_with_capacity_violation.csv
14.1 Header
scenario_id,tree_side,node_name,product_name,week,capacity_type,cap_mode,capacity_qty,required_qty,overflow_qty,violation_type,overflow_lot_ids,action
14.2 Example
scenario_id,tree_side,node_name,product_name,week,capacity_type,cap_mode,capacity_qty,required_qty,overflow_qty,violation_type,overflow_lot_ids,action
BASE,INBOUND,MOM_CHINA,IPHONE_NM_2028_BASE,2026-W01,P,soft,120,150,30,CAPACITY_OVER,LOT131|LOT132|LOT133,CARRY_OVER
BASE,OUTBOUND,DAD_COLD_DC,VACCINE_X,2026-W01,I,hard,300,340,40,INVENTORY_OVER,LOT901|LOT902,WASTE
15. Violation Types

Minimum violation types:

violation_type	Meaning
CAPACITY_OVER	P / S flow capacity exceeded
INVENTORY_OVER	I stock capacity exceeded
ZERO_CAPACITY	capacity_qty is zero and requested lots exist
NO_CAPACITY_MASTER	optional diagnostic only; not emitted by default
CARRIED_OVER	soft cap overflow carried to future week
WASTE	hard cap overflow cannot be accepted or stored

For v0r2-m2, required types are:

CAPACITY_OVER
ZERO_CAPACITY

INVENTORY_OVER should be defined but may be lightly implemented if I-cap enforcement is not yet connected.

16. CSV Export Rule

Lot IDs should be exported as pipe-separated strings.

Example:

LOT001|LOT002|LOT003

The exporter should handle both lot dictionaries and lot ID strings.

Recommended helper:

def _lot_id(lot: Any) -> str:
    if isinstance(lot, dict):
        return str(lot.get("lot_id", lot))
    return str(lot)

This keeps compatibility with current and future lot representations.

17. Suggested Module Structure

Suggested files:

pysi/planning/capacity_master.py
pysi/planning/capacity_io.py
pysi/runners/run_forward_push_with_capacity_io_smoke.py
tests/test_capacity_master_io.py
tests/test_forward_push_with_capacity_io.py

If the repository already has a more appropriate location, follow the existing convention.

18. Runner Policy

v0r2-m2 should be verified by CLI / smoke runner, not GUI.

Recommended runner:

pysi/runners/run_forward_push_with_capacity_io_smoke.py

The runner should:

1. Create or load a sample capacity_master.csv
2. Create requested lots
3. Apply ForwardPushWithCapacityPlanner using loaded capacity
4. Export capacity_usage.csv
5. Export capacity_violation.csv
6. Print summary to stdout

Expected stdout example:

=== with capacity IO smoke ===
capacity master records: 3
requested lots: 120
capacity: 100
accepted lots: 100
blocked lots: 20
usage csv: outputs/capacity/forward_push_with_capacity_usage.csv
violation csv: outputs/capacity/forward_push_with_capacity_violation.csv
19. Test Policy

Required tests:

19.1 Load capacity_master.csv

Expected:

records are loaded
capacity_qty is parsed as int
priority is parsed as int
cap_mode default is soft if omitted
unit default is LOT if omitted
19.2 Exact lookup

Expected:

exact product capacity record is found
19.3 Product wildcard lookup

Expected:

product_name='*' fallback is used when exact product is missing
19.4 Missing capacity

Expected:

missing capacity is treated as unlimited capacity
no blocked lots by default
19.5 Usage CSV export

Expected:

capacity_usage.csv is written
header is correct
used_lot_ids are pipe-separated
19.6 Violation CSV export

Expected:

capacity_violation.csv is written
header is correct
overflow_lot_ids are pipe-separated
19.7 Zero capacity

Expected:

requested lots > 0 and capacity_qty = 0
all lots are blocked
ZERO_CAPACITY or CAPACITY_OVER violation is generated
20. v0r2-m2 Completion Criteria

v0r2-m2 is complete when:

[OK] capacity_master.csv sample exists
[OK] capacity master loader exists
[OK] capacity lookup works
[OK] product wildcard fallback works
[OK] missing capacity means unlimited capacity
[OK] CapacityUsage records are generated
[OK] CapacityViolation records are generated
[OK] usage CSV is exported
[OK] violation CSV is exported
[OK] smoke runner runs successfully
[OK] tests pass
[OK] v0r2-m1 planner behavior remains compatible
21. Boundary with v0r2-m3

v0r2-m2 does not yet need to update real WOM PSI lists.

v0r2-m3 will handle:

Node.psi4demand read
Node.psi4supply update
blocked lots to backlog / carryover structure
real planning runner integration

Therefore, v0r2-m2 should focus only on:

capacity input
capacity lookup
usage / violation output
22. Summary

v0r2-m2 turns the standalone Forward PUSH with Capacity planner into a data-ready component.

The essence of v0r2-m2 is:

capacity masterを読み、
capacity使用状況とcapacity超過をCSVで見える化する

This prepares v0r2-m3, where the planner will be connected to actual WOM PSI list structures.