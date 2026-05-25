# TOBE Capacity-Aware Inbound Backward Planning Design Memo
## MOM.psi4demand[S] → S→P → P Capacity Check → Early Build / Backlog State

**Version:** v0r1 draft  
**Date:** 2026-05-21  
**Status:** Design memo  
**Target path:** `docs/design/capacity_aware_inbound_backward_planning_tobe.md`

**Related design documents:**

- `docs/design/mom_allocation_to_capacity_aware_backward_planning.md`
- `docs/design/outbound_to_inbound_bridge_to_mom_allocation.md`
- `docs/design/outbound_to_inbound_bridge_to_mom_allocation_completion.md`
- `docs/design/wom_outbound_to_inbound_demand_bridge.md`
- `docs/design/wom_demand_to_supply_execution_bridge.md`
- `docs/design/current_wom_backward_planning_and_capacity_flow_mapping.md`
- `docs/design/wom_capacity_input_granularity_adapter.md`
- `docs/design/capacity_provider_monthly_csv_adapter_v0r2.md`

---

## 1. Purpose

This memo defines the TOBE design for **Capacity-Aware Inbound Backward Planning**.

The current implementation `level_mom_demand_with_capacity(...)` is useful, but it should be treated as a current prototype:

```text
MOM assigned demand feasibility / secondary MOM rebalancing prototype
```

The TOBE design should be defined separately.

The TOBE goal is:

```text
MOM.psi4demand[w][S]
    ↓
S→P backward planning
    ↓
MOM.psi4demand[w][P]
    ↓
effective MOM capacity check
    ↓
early build / week shifting / backlog state
```

The key point is that **Demand Anchored Lots must remain inside WOM state**.

Capacity shortage should not make lots disappear into an external result object only.

---

## 2. Current vs TOBE

### 2.1 Current `level_mom_demand_with_capacity(...)`

Current behavior:

```text
MOM.psi4demand[w][S]
    ↓
compare S-lot count with MOM capacity
    ↓
if overflow:
    move overflow to secondary MOM if allowed
    otherwise record backlog in result
```

Current limitations:

```text
does not perform S→P backward planning
does not check MOM.psi4demand[w][P]
does not perform early build / advance production
does not write backlog into a persistent WOM state
may treat secondary MOM reassignment as normal operation
```

### 2.2 TOBE capacity-aware backward planning

TOBE behavior:

```text
MOM.psi4demand[w][S]
    ↓
S→P backward planning
    ↓
MOM.psi4demand[w][P]
    ↓
compare P-lot count with effective MOM capacity
    ↓
if overflow:
    move overflow lots to earlier feasible production weeks
    ↓
if no feasible week:
    keep Lot_ID identity and mark backlog / delayed / issue
```

---

## 3. Core Design Principle

The core design principle is:

```text
Capacity constraint changes the time position or status of a Demand Anchored Lot.
It must not erase the lot.
```

Therefore:

```text
accepted lots:
    remain in feasible production weeks

shifted lots:
    move to earlier P buckets

unallocated lots:
    remain traceable as backlog / delayed / planning issue
```

---

## 4. Position in the Planning Flow

The TOBE stage sits after MOM allocation and before demand-to-supply execution bridge.

```text
[1] Outbound Backward Planning
    leaf demand → DAD → outbound supply_point

[2] Outbound-to-Inbound Demand Bridge
    outbound supply_point.psi4demand[w][P]
        ↓
    inbound supply_point.psi4demand[w][S]

[3] MOM Production Allocation
    inbound supply_point.psi4demand[w][S]
        ↓
    MOM.psi4demand[w][S]

[4] TOBE Capacity-Aware Inbound Backward Planning
    MOM.psi4demand[w][S]
        ↓
    S→P backward planning
        ↓
    MOM.psi4demand[w][P]
        ↓
    capacity check and early build

[5] Demand-to-Supply Execution Bridge
    finalized psi4demand
        ↓
    psi4supply

[6] Forward Supply Execution
    psi4supply
        ↓
    PUSH / PULL / With Capacity Forward PUSH
```

---

## 5. Effective MOM Capacity Model

### 5.1 MVP assumption

For the MVP, inbound-side bottlenecks are represented as **effective MOM capacity**.

```text
supplier / material / process / lane bottleneck
    ↓
effective MOM weekly capacity
```

This avoids modeling every inbound node and lane explicitly in the first version.

### 5.2 Runtime representation

Effective MOM capacity is consumed as:

```python
env.weekly_capability[product][MOM_node][week]
```

or as a canonical capacity table derived from:

```text
WeeklyCapacityRow
```

### 5.3 Meaning

```text
MOM nominal capacity:
    installed or normal operating capacity

effective MOM capacity:
    available capacity after upstream bottleneck impact
```

Example:

```text
MOM_ASIA nominal capacity = 100 lots/week
component bottleneck impact = -40 lots/week
effective MOM capacity = 60 lots/week
```

---

## 6. Input and Output

### 6.1 Input

The TOBE function receives:

```text
MOM-assigned demand lots:
    MOM.psi4demand[w][S]

effective MOM capacity:
    weekly_capability[product][MOM][w]

planning parameters:
    max_early_build_weeks
    backlog policy
    priority rule
```

### 6.2 Output

The TOBE function updates or returns:

```text
MOM.psi4demand[w][P] after capacity-aware placement
shifted lots
backlog / delayed lots
capacity usage
planning issues
replan commands
```

---

## 7. Proposed Function

Suggested future function:

```python
def capacity_aware_inbound_backward_planning(
    *,
    out_root,
    in_root,
    product: str,
    weeks: int | None = None,
    weekly_capability: dict | None = None,
    max_early_build_weeks: int = 13,
    priority_rule: str = "FIFO",
    backlog_policy: str = "record_backlog_state",
    debug: bool = False,
) -> CapacityAwareInboundBackwardPlanningResult:
    ...
```

This should be a new TOBE function rather than a hidden behavior inside `level_mom_demand_with_capacity(...)`.

---

## 8. Proposed Result Object

```python
@dataclass
class CapacityAwareInboundBackwardPlanningResult:
    product_name: str
    planned_lot_count: int = 0
    capacity_checked_lot_count: int = 0
    accepted_lot_count: int = 0
    shifted_lot_count: int = 0
    backlog_lot_count: int = 0
    capacity_usage_by_mom_week: dict = field(default_factory=dict)
    shifted_lots: list[dict] = field(default_factory=list)
    backlog_lots: list[dict] = field(default_factory=list)
    planning_issues: list[dict] = field(default_factory=list)
    replan_commands: list[dict] = field(default_factory=list)
    non_list_bucket_errors: list[dict] = field(default_factory=list)
    message: str = ""
```

---

## 9. Processing Logic

### 9.1 Step 1: Read MOM demand S

For each MOM node:

```python
lots = MOM.psi4demand[w][PSI_S]
```

These lots represent demand assigned to the MOM.

### 9.2 Step 2: Convert S to planned P

Use existing or new backward planning logic to determine required production week.

MVP may use:

```text
planned_p_week = demand_week - leadtime_weeks
```

or call an existing `calcS2P` / subtree propagation function if safe.

### 9.3 Step 3: Check capacity on P bucket

For each planned production week:

```text
len(MOM.psi4demand[p_week][P]) <= effective_capacity[p_week]
```

### 9.4 Step 4: If capacity is insufficient

Move overflow lots earlier.

```text
try p_week - 1
try p_week - 2
...
until max_early_build_weeks
```

### 9.5 Step 5: If no feasible earlier week exists

Do not erase the lot.

Record as:

```text
backlog
delayed
unallocated
planning issue
replan command
```

The exact state representation can be decided in implementation, but Lot_ID identity must be preserved.

---

## 10. Backlog State Policy

Backlog must not be just a summary count.

Backlog should preserve:

```text
lot_id
product
assigned_mom
original_demand_week
attempted_p_week
reason
suggested_action
```

Suggested backlog record:

```python
{
    "lot_id": "LOT_001",
    "product_id": "PRODUCT_X",
    "assigned_mom": "MOM_ASIA",
    "demand_week": "2026-W40",
    "attempted_p_week": "2026-W38",
    "reason": "no_feasible_capacity",
    "suggested_action": "review_capacity_or_demand_allocation",
}
```

Future state representation may use:

```text
PlanningIssue
ReplanCommand
LotHeader.status
dedicated backlog bucket / report
event trace
```

---

## 11. Secondary MOM Policy

Secondary MOM reassignment should not be the default normal operation.

It should be treated as:

```text
exceptional scenario
alternative MOM selection
management decision
optimization scenario
```

Therefore:

```text
default:
    no secondary MOM reassignment

optional:
    allow_alternative_mom=True
```

If enabled, reassignment should be explicit and traceable.

---

## 12. Relationship to Existing Current Function

The current function:

```python
level_mom_demand_with_capacity(...)
```

should be repositioned as:

```text
MOM assigned demand feasibility / secondary MOM rebalancing prototype
```

It should not be treated as the canonical TOBE planning engine.

Potential future options:

```text
1. keep it as a compatibility helper
2. wrap it under a clearer name
3. deprecate secondary MOM behavior as default
4. replace it with capacity_aware_inbound_backward_planning(...)
```

---

## 13. Safety Invariants

The TOBE implementation must preserve:

```text
1. All psi4demand buckets remain lists.
2. All bucket items remain Lot_ID strings.
3. No numeric quantity values are inserted into PSI buckets.
4. No Demand Anchored Lot disappears.
5. Shifted lots remain traceable.
6. Backlog lots preserve Lot_ID identity.
7. Secondary MOM reassignment is explicit, not hidden.
8. No psi4supply mutation happens in this stage.
9. Forward Planning is not executed in this stage.
```

---

## 14. Test Strategy

### 14.1 MVP test tree

Use a small tree:

```text
supply_point
    └── MOM_ASIA
```

or:

```text
supply_point
    ├── MOM_ASIA
    └── MOM_EURO
```

### 14.2 Capacity scenario

Example:

```text
MOM_ASIA capacity:
    week 10: 2 lots
    week 9:  2 lots

Demand assigned to MOM_ASIA:
    week 10: 3 lots
```

Expected:

```text
2 lots stay in week 10 P bucket
1 lot shifts to week 9 P bucket
```

### 14.3 Required tests

```text
1. MOM-assigned S lots are converted to P lots.
2. P bucket does not exceed capacity.
3. Overflow lot shifts earlier when earlier capacity exists.
4. Backlog lot is recorded when no earlier capacity exists.
5. Lot_ID identity is preserved.
6. No numeric quantities are inserted.
7. psi4supply is not mutated.
8. secondary MOM reassignment is disabled by default.
```

---

## 15. Relationship to Demand-to-Supply Execution Bridge

Only after this TOBE planning is complete should WOM run:

```text
finalized psi4demand
    ↓
psi4supply
```

This bridge is separate and should not be triggered inside capacity-aware backward planning.

---

## 16. Relationship to Forward PUSH with Capacity

Forward PUSH with Capacity should run after:

```text
Demand-to-Supply Execution Bridge
```

It checks execution feasibility on `psi4supply`.

It should not replace capacity-aware backward planning.

---

## 17. Implementation Roadmap

### v0r1

```text
write design
```

### v0r2

```text
implement minimal capacity_aware_inbound_backward_planning(...)
using P bucket capacity check and early build
```

### v0r3

```text
add backlog state / PlanningIssue / ReplanCommand output
```

### v0r4

```text
integrate with Rice Case E2E smoke
```

### v0r5

```text
connect to Management Cockpit / KPI evaluation
```

---

## 18. Summary

The canonical TOBE behavior is:

```text
MOM.psi4demand[w][S]
    ↓
S→P backward planning
    ↓
MOM.psi4demand[w][P]
    ↓
effective MOM capacity check
    ↓
early build / week shifting / backlog state
```

This preserves the core WOM principle:

```text
Demand Anchored Lots remain in WOM state.
Capacity constraints change time position or status.
Capacity constraints do not erase lots.
```

This design separates the current prototype from the future canonical capacity-aware backward planning engine.
