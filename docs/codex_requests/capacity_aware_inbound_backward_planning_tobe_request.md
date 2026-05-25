# Codex Request: Implement TOBE Capacity-Aware Inbound Backward Planning MVP

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/capacity_aware_inbound_backward_planning_tobe.md
```

Please read this design memo first.

The current implementation has:

```text
level_mom_demand_with_capacity(...)
```

but this function should be treated as:

```text
MOM assigned demand feasibility / secondary MOM rebalancing prototype
```

It is **not** the final canonical capacity-aware backward planning engine.

The TOBE design is:

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

This request is to implement the first small MVP of that TOBE flow.

---

## 2. Main Objective

Implement a minimal, safe TOBE capacity-aware inbound backward planning function.

The function should:

```text
1. Read demand lots from MOM.psi4demand[w][S].
2. Convert / place those lots into MOM.psi4demand[w][P].
3. Check MOM.psi4demand[w][P] against effective MOM weekly capacity.
4. If capacity is exceeded, shift overflow lots to earlier feasible weeks.
5. If no earlier feasible week exists, preserve Lot_ID identity in backlog records.
6. Never insert numeric quantities into PSI buckets.
7. Never mutate psi4supply.
```

This should be a new additive implementation.

Do not replace `level_mom_demand_with_capacity(...)`.

---

## 3. Critical WOM / PySI V0R8 Assumptions

Please preserve these assumptions.

### 3.1 PSI bucket structure

The canonical V0R8 PSI structure is:

```python
node.psi4demand[w] = [S_ids, CO_ids, I_ids, P_ids]
node.psi4supply[w] = [S_ids, CO_ids, I_ids, P_ids]
```

Bucket index convention:

```python
PSI_S  = 0
PSI_CO = 1
PSI_I  = 2
PSI_P  = 3
```

### 3.2 PSI buckets contain Lot_ID lists, not numeric quantities

Correct:

```python
mom.psi4demand[w][PSI_P] = ["LOT_A", "LOT_B"]
```

Incorrect:

```python
mom.psi4demand[w][PSI_P] = 2
```

Quantity remains:

```python
quantity = len(mom.psi4demand[w][bucket])
```

### 3.3 Demand Anchored Lots must not disappear

If a lot cannot be placed within capacity, it must remain traceable.

It should be recorded as:

```text
backlog
delayed
unallocated
PlanningIssue candidate
ReplanCommand candidate
```

Do not simply drop it.

---

## 4. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan.
3. Do not modify existing monthly loaders.
4. Do not run Forward Planning.
5. Do not implement demand-to-supply bridge.
6. Do not implement Management Issue Generation.
7. Do not remove or replace level_mom_demand_with_capacity(...).
8. Do not make secondary MOM reassignment the default.
9. Keep this as an additive TOBE MVP function and focused tests.
```

This request is only for:

```text
MOM.psi4demand[S]
    ↓
MOM.psi4demand[P]
    ↓
effective capacity check
    ↓
early build / backlog
```

---

## 5. Suggested Files

Please add:

```text
pysi/plan/capacity_aware_inbound_backward.py
tests/test_capacity_aware_inbound_backward_planning.py
```

Please add `__init__.py` only if needed.

Do not modify:

```text
pysi/gui/*
run_full_plan
existing loaders
Forward Planning functions
```

---

## 6. Proposed Constants

Use canonical PSI bucket constants.

```python
PSI_S  = 0
PSI_CO = 1
PSI_I  = 2
PSI_P  = 3
```

or:

```python
PSI_BUCKET_INDEX = {
    "S": 0,
    "CO": 1,
    "I": 2,
    "P": 3,
}
```

---

## 7. Result Dataclass

Please implement:

```python
from dataclasses import dataclass, field


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
    non_list_bucket_errors: list[dict] = field(default_factory=list)
    non_string_lot_errors: list[dict] = field(default_factory=list)
    message: str = ""
```

---

## 8. Main Function

Please implement:

```python
def capacity_aware_inbound_backward_planning(
    *,
    in_root,
    product: str,
    weekly_capability: dict | None = None,
    weeks: int | None = None,
    max_early_build_weeks: int = 13,
    priority_rule: str = "FIFO",
    backlog_policy: str = "record_backlog_state",
    debug: bool = False,
) -> CapacityAwareInboundBackwardPlanningResult:
    ...
```

---

## 9. Expected Behavior

### 9.1 Read MOM demand S

For each MOM node:

```python
demand_lots = mom.psi4demand[w][PSI_S]
```

These lots represent assigned demand for that MOM.

### 9.2 Convert S to P

For the MVP, it is acceptable to treat:

```text
demand week = production week
```

unless leadtime is available.

MVP behavior:

```python
mom.psi4demand[w][PSI_P].extend(demand_lots)
```

or equivalent controlled placement.

Future behavior may use:

```text
production_week = demand_week - leadtime_weeks
```

### 9.3 Capacity check on P bucket

For each MOM and week:

```python
len(mom.psi4demand[w][PSI_P]) <= effective_capacity[w]
```

Capacity should come from:

```text
weekly_capability[product][mom_name][w]
```

or fallback to:

```text
mom.nx_capacity
```

if provided.

### 9.4 Early build / week shifting

If P bucket exceeds capacity:

```text
keep lots within capacity in current week
move overflow lots to earlier feasible weeks
```

Search earlier weeks:

```text
w-1
w-2
...
w-max_early_build_weeks
```

A lot should be placed in the first earlier week with available capacity.

### 9.5 Backlog if no feasible week exists

If no earlier feasible week has capacity:

```text
do not drop the lot
record backlog_lot with Lot_ID and reason
```

Backlog record should include:

```text
lot_id
assigned_mom
demand_week
attempted_week
reason
```

---

## 10. Secondary MOM Reassignment Policy

Do not implement secondary MOM reassignment as default behavior.

This request should not move lots to another MOM.

Reason:

Secondary MOM reassignment is a heavy business operation involving:

```text
quality differences
leadtime differences
transport differences
cost differences
customer allocation assumptions
```

It should be treated as:

```text
exceptional scenario
alternative MOM selection
management decision
future OR optimization
```

---

## 11. Safety Rules

Please enforce these invariants:

```text
1. All psi4demand buckets remain lists.
2. All bucket items remain Lot_ID strings.
3. No numeric quantity values are inserted into PSI buckets.
4. No Demand Anchored Lot disappears.
5. Shifted lots remain traceable.
6. Backlog lots preserve Lot_ID identity.
7. psi4supply is not mutated.
8. Forward Planning is not executed.
```

---

## 12. MOM Node Discovery

MVP can identify MOM nodes by prefix:

```text
MOM_
```

or:

```python
node.name.startswith("MOM")
```

If no MOM nodes exist, return empty result safely.

---

## 13. Capacity Resolution

Please implement a small helper:

```python
def resolve_mom_weekly_capacity(
    mom,
    *,
    product: str,
    weekly_capability: dict | None,
    weeks: int,
) -> list[int]:
    ...
```

Resolution order:

```text
1. weekly_capability[product][mom.name]
2. weekly_capability[mom.name]
3. mom.nx_capacity
4. 0
```

This should be deterministic.

---

## 14. Test Strategy

Please add:

```text
tests/test_capacity_aware_inbound_backward_planning.py
```

Use a minimal MOM tree:

```text
supply_point
    └── MOM_ASIA
```

Each node should have:

```text
name
children
psi4demand
psi4supply
```

with enough weeks for testing.

---

## 15. Required Tests

### 15.1 Basic S to P placement

Given:

```python
MOM_ASIA.psi4demand[10][S] = ["LOT_A", "LOT_B"]
```

After planning:

```python
MOM_ASIA.psi4demand[10][P] contains ["LOT_A", "LOT_B"]
```

### 15.2 Capacity within limit

Given capacity 2 and 2 lots:

```text
no shift
no backlog
```

### 15.3 Overflow shifts earlier

Given:

```text
week 10 capacity = 2
week 9 capacity = 2
week 10 demand = 3 lots
```

Expected:

```text
2 lots stay in week 10 P
1 lot shifts to week 9 P
```

### 15.4 Backlog when no earlier capacity

Given:

```text
week 10 capacity = 1
week 9 capacity = 0
week 8 capacity = 0
week 10 demand = 2 lots
```

Expected:

```text
1 lot stays
1 lot becomes backlog_lot
Lot_ID is preserved in backlog record
```

### 15.5 No psi4supply mutation

Verify:

```text
psi4supply remains empty / unchanged
```

### 15.6 PSI bucket invariant

Verify all `psi4demand` buckets remain `list[str]`.

### 15.7 MOM prefix discovery

Verify function finds MOM nodes by prefix.

### 15.8 No secondary MOM reassignment

If there are two MOM nodes, overflow should not move to second MOM by default.

---

## 16. Existing Tests to Run

Please run:

```bat
python -m pytest tests/test_capacity_aware_inbound_backward_planning.py
python -m pytest tests/test_outbound_to_inbound_bridge_to_mom_allocation.py
python -m pytest tests/test_outbound_to_inbound_demand_bridge.py
python -m pytest tests/test_japanese_rice_backward_planning_after_seed.py
python -m pytest tests/test_japanese_rice_case_smoke.py
```

Optional:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

If broader tests fail due to unrelated optional dependencies, report separately.

---

## 17. Completion Criteria

This request is complete when:

```text
[OK] capacity_aware_inbound_backward.py exists
[OK] capacity_aware_inbound_backward_planning(...) works
[OK] MOM S lots are placed into P bucket
[OK] P bucket respects capacity
[OK] overflow lots shift earlier when capacity exists
[OK] backlog records preserve Lot_ID identity
[OK] psi4supply is not mutated
[OK] no numeric quantities are inserted
[OK] secondary MOM reassignment is not default behavior
[OK] focused tests pass
[OK] no GUI / run_full_plan / loader / Forward Planning changes
```

---

## 18. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. How effective MOM capacity is resolved
4. How early build / week shifting is handled
5. How backlog Lot_ID identity is preserved
6. Test commands executed
7. Test results
8. Limitations / follow-up
```

Do not proceed into:

```text
secondary MOM optimization
OR optimization
demand-to-supply execution bridge
Forward Planning
With Capacity Forward PUSH
GUI integration
run_full_plan integration
Management Issue Generation
```

This request is only for:

```text
TOBE Capacity-Aware Inbound Backward Planning MVP
```