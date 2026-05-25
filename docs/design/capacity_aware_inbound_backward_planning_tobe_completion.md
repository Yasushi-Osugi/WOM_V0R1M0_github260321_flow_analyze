# TOBE Capacity-Aware Inbound Backward Planning MVP Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-21  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **TOBE Capacity-Aware Inbound Backward Planning MVP**.

The purpose of this milestone was to implement a canonical TOBE-side capacity-aware inbound backward planning function that differs from the existing prototype:

```text
level_mom_demand_with_capacity(...)

The current prototype is positioned as:

MOM assigned demand feasibility / secondary MOM rebalancing prototype

The TOBE function implemented in this milestone is positioned as:

MOM.psi4demand[w][S]
    ↓
S→P backward planning
    ↓
MOM.psi4demand[w][P]
    ↓
effective MOM capacity check
    ↓
early build / week shifting / backlog state

The most important principle is:

Demand Anchored Lots must remain traceable.
Capacity constraints should change the time position or status of a lot.
Capacity constraints must not erase lots.
2. Background

Before this milestone, the completed demand-layer flow was:

Bridge A
    ↓
MOM allocation
    ↓
MOM.psi4demand[w][S]

The existing level_mom_demand_with_capacity(...) function operated on MOM.psi4demand[w][S] and could rebalance lots to secondary MOMs or record backlog in a result.

However, it did not implement:

S→P backward planning
P bucket capacity checking
early build / advance production
backlog state with canonical Lot_ID preservation

This milestone adds the first MVP of the TOBE behavior.

3. Implemented Files

This milestone added:

pysi/plan/capacity_aware_inbound_backward.py
tests/test_capacity_aware_inbound_backward_planning.py
4. Implemented Function

The main function added is:

capacity_aware_inbound_backward_planning(...)

Conceptual behavior:

1. Discover MOM nodes by prefix.
2. Read demand lots from MOM.psi4demand[w][S].
3. Place those lots into MOM.psi4demand[w][P].
4. Check P bucket lot count against effective MOM capacity.
5. If capacity is exceeded:
       move overflow lots to earlier feasible weeks.
6. If no earlier feasible week exists:
       preserve Lot_ID identity in backlog records.
7. Never mutate psi4supply.
5. Capacity Resolution

Effective MOM capacity is resolved in the following order:

1. weekly_capability[product][mom.name]
2. weekly_capability[mom.name]
3. mom.nx_capacity
4. fallback 0

This matches the design requirement.

The implementation also normalizes capacity inputs across possible structures:

dict
list / tuple
scalar
6. Early Build / Week Shifting

The MVP implements early build behavior.

If demand lots assigned to MOM.psi4demand[w][P] exceed capacity:

1. Keep lots up to capacity in the current week.
2. Move overflow lots to earlier weeks.
3. Search earlier weeks from w-1 backward.
4. Place the lot in the first earlier week with available capacity.
5. If no earlier week is available, record backlog.

Example:

week 10 capacity = 2
week 9 capacity = 2
week 10 demand = 3 lots

Result:
  2 lots remain in week 10 P bucket
  1 lot shifts to week 9 P bucket
7. Backlog Handling

If no feasible earlier week exists, the lot is not dropped.

Instead, it is recorded as backlog while preserving Lot_ID identity.

Backlog record contains:

lot_id
assigned_mom
demand_week
attempted_week
reason

This preserves the WOM principle:

Demand Anchored Lots must not disappear.
8. Safety Invariants

The implementation enforces the following invariants:

[OK] All psi4demand buckets remain lists.
[OK] Bucket items remain Lot_ID strings.
[OK] No numeric quantity values are inserted into PSI buckets.
[OK] Demand Anchored Lots are not silently erased.
[OK] Shifted lots remain traceable.
[OK] Backlog lots preserve Lot_ID identity.
[OK] psi4supply is not mutated.
[OK] Forward Planning is not executed.
[OK] Secondary MOM reassignment is not default behavior.
9. Tests

Focused tests were added in:

tests/test_capacity_aware_inbound_backward_planning.py

They cover:

1. Basic S→P placement and within-capacity behavior.
2. Overflow shifting to an earlier feasible week.
3. Backlog recording when no earlier capacity exists.
4. psi4supply unchanged.
5. PSI bucket list/string invariants.
6. MOM prefix discovery through tree traversal.
7. No default secondary MOM reassignment.
10. Test Summary

The following tests passed:

python -m pytest tests/test_capacity_aware_inbound_backward_planning.py

Result:

3 passed

Compatibility tests also passed:

python -m pytest tests/test_outbound_to_inbound_bridge_to_mom_allocation.py
python -m pytest tests/test_outbound_to_inbound_demand_bridge.py
python -m pytest tests/test_japanese_rice_backward_planning_after_seed.py
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py

Observed results:

tests/test_outbound_to_inbound_bridge_to_mom_allocation.py: 1 passed
tests/test_outbound_to_inbound_demand_bridge.py: 10 passed
tests/test_japanese_rice_backward_planning_after_seed.py: 2 passed
tests/test_japanese_rice_case_smoke.py: 1 passed
tests/test_covid_vaccine_with_capacity_push.py: 1 passed
11. Completion Criteria

This milestone satisfies the intended completion criteria.

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
[OK] no GUI changes
[OK] no run_full_plan changes
[OK] no loader changes
[OK] no Forward Planning changes
12. Latest Commit

Implementation was completed with:

248fde4 Add TOBE capacity-aware inbound backward planning MVP

Work was performed on:

feature/with-capacity-psi-engine-v0r2
13. Relationship to Current Prototype

The existing current prototype remains:

level_mom_demand_with_capacity(...)

Its position is:

MOM assigned demand feasibility / secondary MOM rebalancing prototype

The new TOBE function is:

capacity_aware_inbound_backward_planning(...)

Its position is:

MOM.psi4demand[w][S]
    ↓
S→P
    ↓
MOM.psi4demand[w][P]
    ↓
effective capacity check
    ↓
early build / backlog

These are not the same responsibility and should remain conceptually separate.

14. Important Boundary

This milestone does not implement:

secondary MOM optimization
OR optimization
demand-to-supply execution bridge
Forward Planning
With Capacity Forward PUSH
GUI integration
run_full_plan integration
Management Issue Generation

It only implements the TOBE MVP for:

MOM S lots
    ↓
MOM P bucket
    ↓
effective capacity
    ↓
early build / backlog
15. Meaning of This Milestone

This milestone is important because it restores the canonical WOM idea that:

Capacity constraints should not erase Demand Anchored Lots.

Instead, capacity constraints should create one of the following:

accepted placement
shifted placement
backlog state
planning issue
replan command

This MVP now supports the first three:

accepted placement
shifted placement
backlog record

while preserving Lot_ID identity.

16. Future Milestones
16.1 Integration with MOM Allocation

Future flow:

Bridge A
    ↓
MOM allocation
    ↓
capacity_aware_inbound_backward_planning(...)
16.2 Backlog to PlanningIssue / ReplanCommand

Future work should convert backlog records into:

PlanningIssue
ReplanCommand
ManagementIssue candidate
16.3 Demand-to-Supply Execution Bridge

After demand-side planning is finalized:

psi4demand
    ↓
psi4supply
16.4 Forward PUSH with Capacity

After Bridge B:

psi4supply
    ↓
Forward PUSH with Capacity
17. Summary

TOBE Capacity-Aware Inbound Backward Planning MVP is complete.

The completed canonical behavior is:

MOM.psi4demand[w][S]
    ↓
MOM.psi4demand[w][P]
    ↓
effective MOM capacity check
    ↓
early build / week shifting
    ↓
backlog record if no feasible capacity

The key invariant remains:

PSI buckets hold Lot_ID lists.
Quantity is len(list).
Lot attributes live outside PSI buckets.
Demand Anchored Lots do not disappear.

This is a major step toward the canonical WOM demand-side planning engine.