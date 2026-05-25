# MOM Allocation to Capacity-Aware Backward Planning Design Memo

**Version:** v0r2 revised with Current / TOBE separation  
**Date:** 2026-05-21  
**Status:** Design memo  
**Target path:** `docs/design/mom_allocation_to_capacity_aware_backward_planning.md`

**Related design documents:**

- `docs/design/wom_demand_layer_bridge_and_supply_execution_bridge.md`
- `docs/design/wom_outbound_to_inbound_demand_bridge.md`
- `docs/design/outbound_to_inbound_bridge_to_mom_allocation.md`
- `docs/design/outbound_to_inbound_bridge_to_mom_allocation_completion.md`
- `docs/design/current_wom_backward_planning_and_capacity_flow_mapping.md`
- `docs/design/wom_capacity_input_granularity_adapter.md`
- `docs/design/capacity_provider_monthly_csv_adapter_v0r2.md`
- `docs/design/capacity_provider_monthly_csv_adapter_v0r2_completion.md`
- `docs/design/rice_case_backward_planning_after_seed.md`
- `docs/design/rice_case_backward_planning_after_seed_completion.md`

---

## 1. Purpose

This memo defines the design boundary from **MOM Production Allocation** to **Capacity-Aware Inbound Backward Planning**.

The previous milestones completed the following demand-layer path:

```text
outbound supply_point.psi4demand[w][P]
    ↓
Bridge A: Outbound-to-Inbound Demand Bridge
    ↓
inbound supply_point.psi4demand[w][S]
    ↓
MOM Production Allocation
    ↓
MOMxxx.psi4demand[w][S]
```

The next controlled planning step is:

```text
MOMxxx.psi4demand[w][S]
    ↓
Capacity-Aware Inbound Backward Planning
    ↓
MOMxxx.psi4demand[w][P]
    ↓
capacity feasibility / advance production / overflow handling
```

This revision explicitly separates:

```text
Current implementation:
    level_mom_demand_with_capacity(...) as a feasibility / rebalancing prototype

TOBE design:
    true capacity-aware backward planning with S→P propagation and early build
```

This separation is necessary because the current implementation is useful, but it is not yet the final canonical capacity-aware backward planning engine.

---

## 2. Core Principle

The key principle is:

```text
MOM allocation decides which MOM should serve which market demand.

Capacity-aware backward planning decides when that MOM can feasibly satisfy the assigned demand.
```

These are different responsibilities.

```text
MOM Allocation:
    assignment problem

MOM Demand Capacity Feasibility:
    capacity feasibility / secondary MOM / backlog prototype

Capacity-Aware Backward Planning:
    timing and feasibility problem using S→P and effective MOM capacity
```

This separation keeps WOM planning logic modular.

---

## 3. Position in the Overall Planning Flow

The recommended planning sequence is:

```text
[1] Plan Input Seed
    demand / supply / case_weekly input
        ↓
    PlanNode.psi4demand seed

[2] Outbound Backward Planning
    leaf demand
        ↓
    DAD
        ↓
    outbound supply_point

[3] Outbound-to-Inbound Demand Bridge
    outbound supply_point.psi4demand[w][P]
        ↓
    inbound supply_point.psi4demand[w][S]

[4] MOM Production Allocation
    inbound demand lots
        ↓
    MOMxxx.psi4demand[w][S]

[5A] Current MOM Demand Capacity Feasibility
    MOMxxx.psi4demand[w][S]
        ↓
    level_mom_demand_with_capacity(...)
        ↓
    adjusted MOMxxx.psi4demand[w][S]
        - primary MOM within capacity
        - optional secondary MOM reassignment
        - backlog recorded in result

[5B] TOBE Capacity-Aware Inbound Backward Planning
    adjusted MOMxxx.psi4demand[w][S]
        ↓
    S→P / subtree backward planning
        ↓
    MOMxxx.psi4demand[w][P]
        ↓
    effective MOM capacity check
        ↓
    early build / week shifting / backlog state

[6] Demand-to-Supply Execution Bridge
    finalized psi4demand
        ↓
    psi4supply

[7] Forward Supply Execution
    psi4supply
        ↓
    PUSH / PULL / With Capacity Forward PUSH
```

This memo focuses on `[5A]` and `[5B]`.

---

## 4. Current Implementation: `level_mom_demand_with_capacity(...)`

### 4.1 Current active definition

The current active implementation of:

```python
level_mom_demand_with_capacity(...)
```

should be classified as a **MOM assigned demand feasibility / secondary MOM rebalancing prototype**, not as the final capacity-aware backward planning engine.

### 4.2 Current input bucket

The current implementation reads:

```python
MOM.psi4demand[w][0]
```

where bucket index `0` is:

```text
S bucket
```

Thus, the current function works on:

```text
MOM.psi4demand[w][S]
```

not on:

```text
MOM.psi4demand[w][P]
```

### 4.3 Current behavior

The current implementation:

```text
1. reads MOM-assigned demand lots from MOM.psi4demand[w][S]
2. compares assigned lot count with MOM weekly capacity
3. keeps lots within primary MOM capacity
4. optionally moves overflow lots to secondary MOM
5. records remaining overflow as backlog in result
6. writes adjusted assignments back to MOM.psi4demand[w][S]
```

### 4.4 Current explicit limitations

The current implementation explicitly does not perform:

```text
S→P backward planning
P bucket capacity check
early build / advance production
writing backlog lots into a persistent WOM state bucket
Forward Planning
```

In particular:

```text
early build / 前倒し is not implemented
backlog is recorded in result, not written to node state
```

### 4.5 Correct current classification

Therefore, the correct classification is:

```text
Current level_mom_demand_with_capacity(...)
    =
MOM assigned demand feasibility / secondary MOM rebalancing prototype
```

It should not be treated as the final canonical capacity-aware backward planning engine.

---

## 5. Why Secondary MOM Reallocation Is Not Normal Weekly Operation

### 5.1 Business reality

Automatically switching supply source from one mother plant to another every week is often unrealistic.

Example:

```text
MOM_NA originally serves North America.
MOM_ASIA serves Asia.
```

Dynamically moving lots from `MOM_NA` to `MOM_ASIA` may create problems:

```text
quality control differences
production specification differences
regulatory / certification constraints
transport leadtime differences
cost differences
contractual commitments
traceability complexity
customer / market allocation assumptions
```

### 5.2 Design implication

Secondary MOM reassignment should not be treated as a normal hidden operation.

It should be treated as one of:

```text
exceptional scenario
alternative MOM selection
management decision
replanning command
optimization scenario
```

### 5.3 Recommended policy

For canonical planning:

```text
normal weekly planning:
    keep demand lots assigned to the planned MOM
    use capacity-aware backward planning / early build

exceptional planning:
    allow secondary MOM only when explicitly enabled
    record reason and traceability
```

---

## 6. Backlog Must Preserve Demand Anchored Lot Identity

### 6.1 Current concern

The current implementation records backlog in the result object.

This is acceptable for a prototype, but it is not sufficient for the canonical WOM design.

### 6.2 WOM principle

WOM's core principle is:

```text
Lot remains the subject.
Demand Anchored Lots must not disappear.
```

Therefore, capacity-overflow lots should remain traceable.

### 6.3 TOBE backlog handling

Future backlog handling should preserve Lot_ID identity using one or more of:

```text
PlanningIssue
ReplanCommand
backlog state
unallocated lot record
delayed lot status
event trace
LotHeader.status
```

### 6.4 Design rule

Backlog should not be merely an external summary.

It should be represented as:

```text
lot_id + status + reason + suggested action
```

Example:

```python
{
    "lot_id": "LOT_001",
    "status": "backlog",
    "reason": "capacity_overflow_no_room",
    "assigned_mom": "MOM_ASIA",
    "week": "2026-W40",
    "suggested_action": "advance_production_or_review_capacity",
}
```

---

## 7. TOBE: True Capacity-Aware Backward Planning

### 7.1 Desired canonical flow

The TOBE capacity-aware backward planning should follow:

```text
MOM.psi4demand[w][S]
    ↓
S→P backward planning
    ↓
MOM.psi4demand[w][P]
    ↓
effective MOM capacity check
    ↓
if within capacity:
        keep planned P week
    ↓
if over capacity:
        move overflow lots to earlier feasible production week
    ↓
if no feasible earlier week:
        keep Lot_ID and mark backlog / delayed / issue
```

### 7.2 Difference from current implementation

Current implementation:

```text
checks MOM.psi4demand[w][S]
reassigns overflow to secondary MOM
records backlog in result
does not early build
```

TOBE implementation:

```text
checks MOM.psi4demand[w][P]
moves overflow to earlier feasible week
preserves Lot_ID state
records issue if no feasible placement
```

### 7.3 Why TOBE is preferable

This is more consistent with WOM because:

```text
Demand Anchored Lots remain in the planning state.
Capacity constraint changes the time position, not the existence of the lot.
Advance production is naturally represented by backward planning.
Secondary MOM is treated as exceptional, not default.
```

---

## 8. Effective MOM Capacity Model

### 8.1 Motivation

The inbound tree can contain many possible bottleneck sources:

```text
supplier shortage
material shortage
component factory trouble
process capacity shortage
transport route closure
port / strait disruption
customs delay
yield loss
labor availability
```

Modeling all of these explicitly at every node and edge is possible, but it is not required for the first practical WOM MVP.

### 8.2 MVP assumption

For the MVP, inbound-side bottlenecks are represented as **effective MOM capacity**.

```text
inbound internal bottleneck
    ↓
effective MOM capacity
    ↓
MOM capacity-aware backward planning
```

This means:

```text
MOM nominal capacity
    - upstream bottleneck impact
    - material shortage impact
    - logistics disruption impact
    - process availability impact
    = effective MOM capacity
```

WOM consumes this as:

```python
env.weekly_capability[product][MOM_node][week]
```

or an equivalent `WeeklyCapacityRow`-derived runtime structure.

---

## 9. Bottleneck Modeling Levels

WOM should support multiple levels of bottleneck modeling.

### 9.1 Level 1: Effective MOM Capacity Model

This is the recommended MVP.

```text
inbound internal bottleneck
    ↓
effective MOM capacity
```

Runtime input:

```python
weekly_capability[product][MOM_ASIA][week] = 60
```

### 9.2 Level 2: Explicit Bottleneck Node / Lane Model

Future explicit modeling may represent bottleneck nodes and lanes directly.

Examples:

```text
supplier node capacity
material process capacity
subassembly factory capacity
transport lane capacity
port capacity
customs capacity
```

### 9.3 Level 3: OR Optimization Model

Future optimization may model allocation and capacity usage as an OR problem.

Possible objectives:

```text
maximize service level
maximize profit
minimize total cost
balance MOM utilization
prioritize strategic markets
minimize delay
```

Possible constraints:

```text
MOM capacity
supplier capacity
lane capacity
leadtime
material availability
market demand
inventory availability
```

---

## 10. Current Implementation Candidates

### 10.1 MOM allocation

Current function candidate:

```python
allocate_markets_to_moms(...)
```

Current role:

```text
policy-based MOM assignment
```

Current behavior:

```text
inbound supply_point demand lots
    ↓
market key extraction
    ↓
policy dict
    ↓
MOMxxx.psi4demand[w][S]
```

### 10.2 Current feasibility / rebalancing prototype

Current function:

```python
level_mom_demand_with_capacity(...)
```

Current role:

```text
MOM assigned demand feasibility / secondary MOM rebalancing prototype
```

### 10.3 Legacy P-bucket leveling function

Legacy/simple function:

```python
inbound_MOM_leveling_vs_capacity(...)
```

This checks:

```text
MOM.psi4demand[w][P]
```

and shifts overflow lots earlier.

This is conceptually closer to TOBE capacity-aware backward planning, but it is a simpler legacy implementation.

### 10.4 Inbound backward planning

Relevant current function:

```python
inbound_backward_MOM_to_leaf(...)
```

This performs MOM subtree planning and calls:

```python
calc_all_psiS2P2childS_preorder(...)
```

---

## 11. Recommended Repositioning

### 11.1 Current stage names

Rename conceptually:

```text
MOM Production Allocation
    ↓
MOM Assigned Demand Feasibility
    ↓
Inbound Backward Planning
    ↓
Future P-Bucket Capacity-Aware Leveling
```

### 11.2 Do not call current function the final engine

Avoid calling current `level_mom_demand_with_capacity(...)`:

```text
canonical capacity-aware backward planning
```

Instead call it:

```text
MOM assigned demand feasibility / secondary MOM rebalancing prototype
```

### 11.3 Keep TOBE separate

Define the future canonical function separately.

Possible future name:

```python
capacity_aware_inbound_backward_planning(...)
```

or:

```python
level_mom_p_demand_with_effective_capacity(...)
```

---

## 12. Revised Planning Flow

The revised planning flow should be:

```text
[1] Bridge A
    outbound supply_point.psi4demand[w][P]
        ↓
    inbound supply_point.psi4demand[w][S]

[2] MOM Allocation
    inbound supply_point.psi4demand[w][S]
        ↓
    MOM.psi4demand[w][S]

[3] Current Feasibility Layer
    MOM.psi4demand[w][S]
        ↓
    level_mom_demand_with_capacity(...)
        ↓
    adjusted MOM.psi4demand[w][S]

[4] Inbound Backward Planning
    adjusted MOM.psi4demand[w][S]
        ↓
    inbound subtree S→P propagation
        ↓
    MOM / upstream psi4demand[w][P]

[5] TOBE P-Bucket Capacity-Aware Leveling
    MOM.psi4demand[w][P]
        ↓
    effective MOM capacity check
        ↓
    early build / week shifting / backlog state

[6] Demand-to-Supply Execution Bridge
    finalized psi4demand
        ↓
    psi4supply

[7] Forward Supply Execution
    psi4supply
        ↓
    Forward PUSH / PULL / With Capacity Forward PUSH
```

---

## 13. Capacity Input Source

Effective MOM capacity may come from:

```text
monthly capacity CSV
weekly capacity CSV
scenario override
external bottleneck model
manual input
simulation result
```

Preferred path:

```text
P_capacity_month / P_capacity_week
    ↓
WeeklyCapacityRow
    ↓
env.weekly_capability
    ↓
capacity-aware planning
```

Current runtime path:

```text
capacity_provider_monthly_csv
    ↓
env.weekly_capability
```

The provider has been refactored to use the capacity input granularity adapter while preserving default `four_week_month` behavior.

---

## 14. Relationship to Forward PUSH with Capacity

Capacity-aware backward planning and Forward PUSH with Capacity are different.

### 14.1 Backward capacity

Backward capacity answers:

```text
Can the assigned demand be planned within MOM capacity?
```

It controls:

```text
production week
advance production
capacity feasibility
```

### 14.2 Forward capacity

Forward capacity answers:

```text
Can the planned supply actually move through the supply network?
```

It controls:

```text
shipment
transport
storage
delivery
execution feasibility
blocked lots
```

### 14.3 Correct placement

```text
MOM allocation
    ↓
capacity-aware backward planning
    ↓
demand-to-supply bridge
    ↓
Forward PUSH with Capacity
```

Forward PUSH with Capacity should not replace backward capacity planning.

---

## 15. Suggested Future Result Object

```python
@dataclass
class MomCapacityBackwardPlanningResult:
    product_name: str
    assigned_lot_count: int = 0
    feasibility_checked_lot_count: int = 0
    shifted_lot_count: int = 0
    overflow_lot_count: int = 0
    capacity_usage_by_mom_week: dict = field(default_factory=dict)
    shifted_lots: list[dict] = field(default_factory=list)
    backlog_lots: list[dict] = field(default_factory=list)
    replan_commands: list[dict] = field(default_factory=list)
    non_list_bucket_errors: list[dict] = field(default_factory=list)
    message: str = ""
```

---

## 16. Safety Invariants

The following invariants must be preserved.

```text
1. All psi4demand buckets remain lists.
2. All bucket items remain Lot_ID strings.
3. No numeric quantity values are inserted into PSI buckets.
4. Existing source demand lots are not silently lost.
5. Shifted lots remain traceable.
6. Backlog lots preserve Lot_ID identity.
7. Secondary MOM reassignment is not hidden as normal default behavior.
8. Capacity check does not write to psi4supply.
9. Forward Planning is not executed in this stage.
```

---

## 17. MVP Test Strategy

### 17.1 Current implementation tests

Tests for current implementation should verify:

```text
1. MOM allocation produces MOM.psi4demand[w][S].
2. level_mom_demand_with_capacity runs as feasibility / rebalancing prototype.
3. overflow may be moved to secondary MOM if explicitly enabled.
4. backlog is recorded in result if no capacity remains.
5. PSI buckets remain Lot_ID lists.
6. No psi4supply mutation occurs.
```

### 17.2 TOBE tests

Future tests for canonical capacity-aware backward planning should verify:

```text
1. adjusted MOM.psi4demand[w][S] propagates to MOM.psi4demand[w][P].
2. MOM.psi4demand[w][P] is checked against effective MOM capacity.
3. overflow lots are moved to earlier feasible weeks.
4. backlog lots preserve Lot_ID identity.
5. no Lot_ID disappears.
```

---

## 18. Current Open Questions

Before implementation, confirm:

```text
1. Should current level_mom_demand_with_capacity be renamed or wrapped?
2. Should secondary MOM reassignment default to disabled?
3. How should backlog lots be represented in WOM state?
4. Where should PlanningIssue / ReplanCommand be introduced?
5. Should inbound_MOM_leveling_vs_capacity be retired, wrapped, or reused?
6. What should be the first TOBE P-bucket capacity-aware backward planning function?
```

---

## 19. Recommended Next Step

Do not immediately force the current function to become the TOBE planning engine.

Recommended next step:

```text
1. Update design documentation to distinguish current and TOBE.
2. Write tests that document current level_mom_demand_with_capacity behavior.
3. Introduce a future TOBE function for true P-bucket capacity-aware backward planning.
4. Keep secondary MOM reassignment as optional / exceptional.
```

---

## 20. Summary

The current implementation is useful, but it should be classified correctly.

Current:

```text
level_mom_demand_with_capacity(...)
    =
MOM assigned demand feasibility / secondary MOM rebalancing prototype
```

TOBE:

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

The design decision is:

```text
Do not bend WOM's canonical design to match the current prototype.

Instead, preserve the current prototype as a feasibility layer,
and define the canonical capacity-aware backward planning as the next stage.
```
