# E2E Bridge + Forward Capacity Smoke Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-22  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **E2E Bridge + Forward Capacity Smoke**.

The purpose of this milestone was to verify that the completed E2E demand-to-supply bridge flow can be connected to the Weekly Forward PUSH with Capacity PSI Engine.

The completed target chain is:

```text
Bridge A
    ↓
MOM allocation
    ↓
TOBE capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
Weekly Forward PUSH with Capacity

This milestone confirms that WOM can move from demand-side E2E planning into supply-side capacity-aware execution smoke while preserving Lot_ID identity and V0R8 PSI semantics.

2. Background

Before this milestone, the following components had already been completed and tested individually.

Bridge A
outbound supply_point.psi4demand[w][P]
    ↓
inbound supply_point.psi4demand[w][S]
MOM allocation
inbound supply_point.psi4demand[w][S]
    ↓
MOMxxx.psi4demand[w][S]
TOBE capacity-aware inbound backward planning
MOM.psi4demand[w][S]
    ↓
MOM.psi4demand[w][P]
    ↓
effective MOM capacity check
    ↓
early build / backlog
Bridge B
finalized psi4demand
    ↓
psi4supply
Weekly Forward PUSH with Capacity
psi4supply
    ↓
cap_P / cap_S / cap_I
    ↓
accepted / blocked / overflow lots

This milestone connects all of these components in one controlled smoke flow.

3. Implemented Files

This milestone added or updated:

pysi/plan/bridges/__init__.py
pysi/plan/bridges/e2e_bridge_forward_capacity_smoke.py
tests/test_e2e_bridge_forward_capacity_smoke.py
4. Implemented Wrapper

The implemented wrapper is:

run_e2e_bridge_forward_capacity_smoke(...)

It orchestrates the following sequence:

1. Bridge A:
       outbound demand/P → inbound demand/S

2. MOM allocation:
       inbound demand/S → MOM demand/S

3. TOBE capacity-aware inbound backward planning:
       MOM demand/S → MOM demand/P
       effective capacity check
       early build / backlog

4. Bridge B:
       finalized demand/S and demand/P → supply/S and supply/P

5. Weekly Forward PUSH with Capacity:
       supply/P and supply/S are accepted or blocked under capacity
       ending inventory is checked against cap_I

The wrapper does not call run_full_plan.

The wrapper does not modify GUI.

5. Implemented Result Object

The result dataclass is:

E2EBridgeForwardCapacitySmokeResult

It records:

bridge_a_lot_count
mom_allocated_lot_count
capacity_planned_lot_count
bridge_b_lot_count

forward_accepted_p_count
forward_blocked_p_count
forward_accepted_s_count
forward_blocked_s_count
forward_overflow_i_count

missing_lot_ids
blocked_lot_ids
overflow_i_lot_ids

non_list_bucket_errors
non_string_lot_errors
message

This gives the smoke flow a compact audit record.

6. Smoke Scenario

The smoke uses a minimal outbound / inbound topology.

6.1 Outbound seed

Known Lot_IDs are seeded into:

outbound supply_point.psi4demand[10][P]

Example lots:

RT_JP_RICE_2026W10_0001
RT_JP_RICE_2026W10_0002
RT_JP_RICE_2026W10_0003
RT_DE_RICE_2026W10_0001
6.2 Bridge A

The lots are bridged to:

inbound supply_point.psi4demand[10][S]
6.3 MOM allocation

Policy:

mom_policy = {
    "JP": ["MOM_ASIA"],
    "DE": ["MOM_EURO"],
    "DEFAULT": ["MOM_ASIA"],
}

Expected allocation:

JP lots → MOM_ASIA
DE lot  → MOM_EURO
6.4 Capacity-aware inbound backward planning

Backward capacity scenario:

MOM_ASIA:
    week 10 capacity = 2
    week 9 capacity  = 2

MOM_EURO:
    week 10 capacity = 2

Expected result:

MOM_ASIA:
    2 lots remain in week 10 P
    1 lot shifts to week 9 P

MOM_EURO:
    1 lot remains in week 10 P
6.5 Bridge B

Bridge B uses:

bridge_policy = s_p_only
mode = replace

Expected:

demand/S → supply/S
demand/P → supply/P
supply/CO = []
supply/I  = []
6.6 Weekly Forward PUSH with Capacity

Forward capacity is then applied to psi4supply.

The test verifies:

P capacity blocking
S capacity blocking
I soft overflow
Lot_ID preservation
7. Test Summary

Focused tests were added in:

tests/test_e2e_bridge_forward_capacity_smoke.py

The new smoke test verifies:

Bridge A runs
MOM allocation runs
capacity-aware inbound backward planning runs
Bridge B runs
Weekly Forward PUSH with Capacity runs
forward P capacity blocking is visible
forward S capacity blocking is visible
I soft overflow is visible
Lot_ID identity is preserved
PSI buckets remain list[str]
No numeric quantities are inserted
8. Validation

The following tests passed:

python -m pytest tests/test_e2e_bridge_forward_capacity_smoke.py

Observed result:

1 passed

Compatibility tests also passed:

python -m pytest tests/test_weekly_forward_push_with_capacity.py
python -m pytest tests/test_e2e_demand_to_supply_bridge_flow_smoke.py
python -m pytest tests/test_demand_to_supply_execution_bridge.py
python -m pytest tests/test_capacity_aware_inbound_backward_planning.py
python -m pytest tests/test_japanese_rice_case_smoke.py

Observed results:

tests/test_weekly_forward_push_with_capacity.py: 6 passed
tests/test_e2e_demand_to_supply_bridge_flow_smoke.py: 2 passed
tests/test_demand_to_supply_execution_bridge.py: 10 passed
tests/test_capacity_aware_inbound_backward_planning.py: 3 passed
tests/test_japanese_rice_case_smoke.py: 1 passed

Optional COVID vaccine test also passed in the local run:

python -m pytest tests/test_covid_vaccine_with_capacity_push.py

Observed result:

1 passed
9. Completion Criteria

This milestone satisfies the intended completion criteria.

[OK] Bridge A runs.
[OK] MOM allocation runs.
[OK] capacity-aware inbound backward planning runs.
[OK] Bridge B runs.
[OK] Weekly Forward PUSH with Capacity runs.
[OK] forward P capacity blocking is verified.
[OK] forward S capacity blocking is verified.
[OK] I soft overflow is verified.
[OK] Lot_ID identity is preserved.
[OK] psi4demand buckets remain list[str].
[OK] psi4supply buckets remain list[str].
[OK] no numeric quantities are inserted.
[OK] no GUI / run_full_plan / loader changes.
[OK] focused tests pass.
10. Latest Commit

Implementation was completed with:

a811b82 Add E2E bridge forward capacity smoke

Work was performed on:

feature/with-capacity-psi-engine-v0r2
11. Important Boundary

This milestone does not implement:

run_full_plan integration
GUI integration
costing / KPI
Management Issue Generation
OR optimization
database persistence

It is a controlled smoke wrapper only.

12. Meaning of This Milestone

This milestone is important because it verifies the first full MVP path from demand-side E2E planning to supply-side capacity-aware execution.

Before this milestone, WOM had separate utilities:

Bridge A
MOM allocation
capacity-aware inbound backward planning
Bridge B
Weekly Forward PUSH with Capacity

After this milestone, WOM has a verified smoke that composes them:

Bridge A
    ↓
MOM allocation
    ↓
capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
Weekly Forward PUSH with Capacity

This is the first compact execution smoke after the bridge flow completion overview.

13. Current Completed Chain

The completed chain is:

outbound demand/P
    ↓
inbound demand/S
    ↓
MOM demand/S
    ↓
MOM demand/P with early build / backlog
    ↓
supply/S and supply/P seed
    ↓
P/S/I capacity-aware forward push

This represents a major step toward a canonical WOM E2E planning engine.

14. Core Invariants Preserved

The following invariants remain preserved:

1. PSI buckets hold Lot_ID lists.
2. Quantity is len(list).
3. Lot attributes remain outside PSI buckets.
4. Demand Anchored Lots do not disappear.
5. Shifted lots remain traceable.
6. Backlog lots preserve Lot_ID identity.
7. Blocked lots preserve Lot_ID identity.
8. Overflow inventory lots preserve Lot_ID identity.
9. Forward PUSH changes lot status, not lot identity.
15. Future Milestones
15.1 Controlled run_full_plan integration design

Future design should define how this explicit pipeline enters the controlled run_full_plan sequence.

Possible design document:

docs/design/run_full_plan_explicit_bridge_capacity_pipeline.md
15.2 E2E Capacity Usage / Violation Reporting

Forward capacity results should connect to:

capacity_usage
capacity_violations
blocked_lots
overflow_inventory
replan command candidates
15.3 ReplanCommand / Management Issue Generation

Future work should connect:

capacity violations
    ↓
ReplanCommand
    ↓
Management Issue
15.4 Cost / KPI Integration

Future work should connect blocked / shifted / overflow lots to:

service level
inventory cost
revenue impact
profit impact
capacity utilization
ROI / investment evaluation
16. Summary

E2E Bridge + Forward Capacity Smoke is complete.

The verified flow is:

Bridge A
    ↓
MOM allocation
    ↓
TOBE capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
Weekly Forward PUSH with Capacity

The key achievement is:

WOM can now move from demand-side E2E planning into supply-side capacity-aware execution smoke while preserving Lot_ID identity and V0R8 PSI semantics.

This prepares WOM for the next major phase:

controlled run_full_plan integration