# E2E Demand-to-Supply Bridge Flow Completion Overview

**Version:** v0r1 completion overview  
**Date:** 2026-05-21  
**Status:** Completion overview  
**Target path:** `docs/design/e2e_demand_to_supply_bridge_flow_completion_overview.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of the recent E2E bridge / backward planning / capacity flow work.

The purpose is to provide a one-page-style overview of the completed milestones that now connect:

```text
outbound demand planning
    ↓
inbound demand context
    ↓
MOM allocation
    ↓
capacity-aware inbound backward planning
    ↓
demand-to-supply execution bridge
```

This overview is intended as a checkpoint before moving into:

```text
Forward Supply Execution
With Capacity Forward PUSH
run_full_plan integration
```

---

## 2. Completed E2E Flow

The current completed MVP flow is:

```text
[1] Outbound demand-side planning
    outbound supply_point.psi4demand[w][P]

[2] Bridge A: Outbound-to-Inbound Demand Bridge
    outbound supply_point.psi4demand[w][P]
        ↓
    inbound supply_point.psi4demand[w][S]

[3] Bridge A → MOM Allocation
    inbound supply_point.psi4demand[w][S]
        ↓
    MOMxxx.psi4demand[w][S]

[4] TOBE Capacity-Aware Inbound Backward Planning MVP
    MOMxxx.psi4demand[w][S]
        ↓
    MOMxxx.psi4demand[w][P]
        ↓
    effective MOM capacity check
        ↓
    early build / week shifting / backlog record

[5] Bridge B: Demand-to-Supply Execution Bridge
    finalized psi4demand
        ↓
    psi4supply
```

This flow means WOM now has explicit MVP utilities for the demand-to-supply transition path.

---

## 3. Milestone 1: Bridge A

### 3.1 Design

Design memo:

```text
docs/design/wom_outbound_to_inbound_demand_bridge.md
```

Completion memo:

```text
docs/design/outbound_to_inbound_demand_bridge_completion.md
```

Codex request:

```text
docs/codex_requests/outbound_to_inbound_demand_bridge_request.md
```

### 3.2 Implementation

Implemented file:

```text
pysi/plan/bridges/outbound_to_inbound_demand_bridge.py
```

Test file:

```text
tests/test_outbound_to_inbound_demand_bridge.py
```

### 3.3 Completed behavior

```text
outbound supply_point.psi4demand[w][P]
    ↓
inbound supply_point.psi4demand[w][S]
```

Key rules:

```text
source bucket is not modified
psi4supply is not touched
Lot_ID lists are copied, not numeric quantities
replace / append / dedupe_append modes are supported
bridge_leadtime_weeks is supported
```

### 3.4 Commit

```text
3026d07 Add outbound-to-inbound demand bridge utility
```

---

## 4. Milestone 2: Bridge A to MOM Allocation

### 4.1 Design

Design memo:

```text
docs/design/outbound_to_inbound_bridge_to_mom_allocation.md
```

Completion memo:

```text
docs/design/outbound_to_inbound_bridge_to_mom_allocation_completion.md
```

Codex request:

```text
docs/codex_requests/outbound_to_inbound_bridge_to_mom_allocation_request.md
```

### 4.2 Implementation

Implemented file:

```text
pysi/plan/bridges/outbound_to_inbound_mom_allocation.py
```

Test file:

```text
tests/test_outbound_to_inbound_bridge_to_mom_allocation.py
```

### 4.3 Completed behavior

```text
inbound supply_point.psi4demand[w][S]
    ↓
MOMxxx.psi4demand[w][S]
```

This step verifies that Bridge A output can be consumed by MOM allocation.

Key rules:

```text
still demand-layer planning
psi4supply is not touched
MOM demand buckets remain Lot_ID lists
existing allocate_markets_to_moms(...) behavior is reused through a safe wrapper
```

### 4.4 Commit

```text
2e82b93 Add outbound-to-inbound bridge to MOM allocation smoke
```

---

## 5. Milestone 3: Current / TOBE Capacity Design Separation

### 5.1 Design

Design memo:

```text
docs/design/mom_allocation_to_capacity_aware_backward_planning.md
```

TOBE design memo:

```text
docs/design/capacity_aware_inbound_backward_planning_tobe.md
```

### 5.2 Key design decision

The current function:

```text
level_mom_demand_with_capacity(...)
```

is not treated as the final canonical capacity-aware backward planning engine.

It is classified as:

```text
MOM assigned demand feasibility / secondary MOM rebalancing prototype
```

The TOBE canonical flow is defined as:

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

### 5.3 Important policy decision

Secondary MOM reassignment is not normal weekly operation.

It should be treated as:

```text
exceptional scenario
alternative MOM selection
management decision
future OR optimization
```

Backlog should preserve Lot_ID identity and should eventually connect to:

```text
PlanningIssue
ReplanCommand
backlog state
event trace
LotHeader.status
```

### 5.4 Commits

```text
4a9595b Revise MOM allocation and capacity-aware backward planning design
487e350 Add TOBE capacity-aware inbound backward planning design
```

---

## 6. Milestone 4: TOBE Capacity-Aware Inbound Backward Planning MVP

### 6.1 Design

Design memo:

```text
docs/design/capacity_aware_inbound_backward_planning_tobe.md
```

Completion memo:

```text
docs/design/capacity_aware_inbound_backward_planning_tobe_completion.md
```

Codex request:

```text
docs/codex_requests/capacity_aware_inbound_backward_planning_tobe_request.md
```

### 6.2 Implementation

Implemented file:

```text
pysi/plan/capacity_aware_inbound_backward.py
```

Test file:

```text
tests/test_capacity_aware_inbound_backward_planning.py
```

### 6.3 Completed behavior

```text
MOM.psi4demand[w][S]
    ↓
MOM.psi4demand[w][P]
    ↓
effective MOM capacity check
    ↓
early build / week shifting
    ↓
backlog record if no feasible capacity
```

Key rules:

```text
Demand Anchored Lots do not disappear
P bucket respects effective MOM capacity
overflow lots move to earlier feasible weeks
backlog records preserve Lot_ID identity
psi4supply is not touched
secondary MOM reassignment is not default behavior
```

### 6.4 Commit

```text
248fde4 Add TOBE capacity-aware inbound backward planning MVP
```

Completion memo commit:

```text
6fccb0a Add TOBE capacity-aware inbound backward planning completion memo
```

---

## 7. Milestone 5: Bridge B

### 7.1 Design

Design memo:

```text
docs/design/wom_demand_to_supply_execution_bridge.md
```

Completion memo:

```text
docs/design/demand_to_supply_execution_bridge_completion.md
```

Codex request:

```text
docs/codex_requests/demand_to_supply_execution_bridge_request.md
```

### 7.2 Implementation

Implemented file:

```text
pysi/plan/bridges/demand_to_supply_execution_bridge.py
```

Updated file:

```text
pysi/plan/bridges/__init__.py
```

Test file:

```text
tests/test_demand_to_supply_execution_bridge.py
```

### 7.3 Completed behavior

```text
finalized psi4demand
    ↓
psi4supply
```

Default MVP policy:

```text
s_p_only:
    demand/S → supply/S
    demand/P → supply/P
    supply/CO = []
    supply/I  = []
```

Supported policies:

```text
s_p_only
s_only
full_clone
```

Supported modes:

```text
replace
append
dedupe_append
```

Key rules:

```text
source psi4demand is not modified
target psi4supply contains Lot_ID lists only
replace mode is idempotent
bridge_leadtime_weeks is supported
no planning engine is executed
```

### 7.4 Commit

```text
00e46dd Add demand-to-supply execution bridge MVP
```

Completion memo commit:

```text
c5630f0 Add demand-to-supply execution bridge completion memo
```

---

## 8. Current Completed Architecture

The completed MVP architecture is:

```text
Outbound demand layer
    ↓
Bridge A
    ↓
Inbound demand layer
    ↓
MOM allocation
    ↓
MOM demand layer
    ↓
TOBE capacity-aware inbound backward planning
    ↓
finalized demand-side PSI
    ↓
Bridge B
    ↓
supply-side PSI seed
```

In compact form:

```text
outbound supply_point.psi4demand[P]
    ↓
inbound supply_point.psi4demand[S]
    ↓
MOM.psi4demand[S]
    ↓
MOM.psi4demand[P] with early build / backlog
    ↓
psi4supply[S/P]
```

---

## 9. Core Invariants Preserved

Across the completed milestones, the following invariants are preserved:

```text
1. PSI buckets hold Lot_ID lists.
2. Quantity is len(list).
3. Lot attributes remain outside PSI buckets.
4. Demand Anchored Lots do not disappear.
5. Capacity constraints change time position or status.
6. Backlog preserves Lot_ID identity.
7. secondary MOM reassignment is not default normal operation.
8. psi4supply is only written by Bridge B.
9. Forward Planning is not executed inside bridge utilities.
10. GUI and run_full_plan have not been modified in these MVP steps.
```

---

## 10. Effective MOM Capacity Assumption

The MVP uses the following modeling assumption:

```text
inbound-side bottlenecks are represented as effective MOM capacity
```

This means:

```text
supplier / material / process / lane bottleneck
    ↓
effective MOM weekly capacity
    ↓
capacity-aware inbound backward planning
```

WOM consumes effective capacity through:

```text
env.weekly_capability[product][MOM][week]
```

or the equivalent canonical capacity structure.

This keeps the MVP simple while preserving a path toward explicit node / lane bottleneck modeling later.

---

## 11. What Is Not Yet Done

The following are intentionally not integrated yet:

```text
run_full_plan integration
GUI integration
Forward Supply Execution
With Capacity Forward PUSH after Bridge B
Management Issue Generation
PlanningIssue / ReplanCommand integration
explicit node / lane bottleneck modeling
OR optimization for MOM allocation or lane selection
```

These are future milestones.

---

## 12. Recommended Next Milestones

### 12.1 Forward Supply Execution after Bridge B

Next conceptual stage:

```text
finalized psi4demand
    ↓
Bridge B
    ↓
psi4supply
    ↓
Forward Supply Execution
```

Design candidate:

```text
docs/design/with_capacity_forward_push_after_bridge_b.md
```

### 12.2 Controlled E2E Smoke

A small E2E smoke test can later connect:

```text
Bridge A
    ↓
MOM allocation
    ↓
capacity-aware inbound backward planning
    ↓
Bridge B
```

without yet modifying `run_full_plan`.

Possible test candidate:

```text
tests/test_e2e_demand_to_supply_bridge_flow_smoke.py
```

### 12.3 run_full_plan Integration

Only after the above smoke is stable should this flow be wired into `run_full_plan`.

---

## 13. Summary

This workstream completed the first explicit demand-to-supply bridge flow in WOM.

The completed chain is:

```text
Bridge A
    ↓
MOM allocation
    ↓
capacity-aware inbound backward planning
    ↓
Bridge B
```

The most important architectural achievement is that WOM now has explicit MVP utilities for:

```text
1. connecting outbound demand to inbound demand
2. assigning inbound demand to MOM nodes
3. placing MOM demand into feasible P weeks under capacity
4. preserving backlog Lot_ID identity
5. seeding psi4supply from finalized psi4demand
```

This prepares WOM for the next phase:

```text
Forward Supply Execution / With Capacity Forward PUSH
```
