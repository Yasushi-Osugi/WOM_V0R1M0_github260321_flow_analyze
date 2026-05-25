# E2E Demand-to-Supply Bridge Flow Smoke Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-21  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of the **E2E Demand-to-Supply Bridge Flow Smoke**.

The purpose of this milestone was to verify that the recently implemented bridge and demand-layer planning utilities can be connected end-to-end in a small, controlled smoke flow.

The completed target chain is:

```text
Bridge A
    ↓
MOM allocation
    ↓
TOBE capacity-aware inbound backward planning
    ↓
Bridge B

This smoke confirms that WOM can move from outbound demand-side PSI to inbound MOM demand, apply capacity-aware backward placement, and then seed the supply-side PSI layer.

This milestone does not execute Forward Planning.

2. Background

Before this milestone, the following components had already been implemented and tested independently.

Bridge A: Outbound-to-Inbound Demand Bridge
outbound supply_point.psi4demand[w][P]
    ↓
inbound supply_point.psi4demand[w][S]
MOM Allocation
inbound supply_point.psi4demand[w][S]
    ↓
MOMxxx.psi4demand[w][S]
TOBE Capacity-Aware Inbound Backward Planning
MOM.psi4demand[w][S]
    ↓
MOM.psi4demand[w][P]
    ↓
effective MOM capacity check
    ↓
early build / week shifting / backlog record
Bridge B: Demand-to-Supply Execution Bridge
finalized psi4demand
    ↓
psi4supply

This milestone connects those pieces in one smoke flow.

3. Implemented Files

This milestone added or updated:

pysi/plan/bridges/__init__.py
pysi/plan/bridges/e2e_demand_to_supply_bridge_flow_smoke.py
tests/test_e2e_demand_to_supply_bridge_flow_smoke.py
4. Implemented Wrapper

The implemented wrapper is:

run_e2e_demand_to_supply_bridge_flow_smoke(...)

It orchestrates the following sequence:

1. Bridge A:
       outbound demand/P → inbound demand/S

2. MOM allocation:
       inbound demand/S → MOM demand/S

3. TOBE capacity-aware inbound backward planning:
       MOM demand/S → MOM demand/P
       capacity check
       early build / backlog

4. Bridge B:
       finalized demand/S and demand/P → supply/S and supply/P

The wrapper does not call Forward Planning.

5. Implemented Result Object

The result dataclass is:

E2EDemandToSupplyBridgeFlowSmokeResult

It records:

bridge_a_lot_count
mom_allocated_lot_count
capacity_planned_lot_count
shifted_lot_count
backlog_lot_count
bridge_b_lot_count
missing_lot_ids
non_list_bucket_errors
non_string_lot_errors
message

This makes the smoke result auditable.

6. Smoke Scenario

The smoke scenario uses a minimal inbound / outbound structure.

6.1 Outbound source
outbound supply_point.psi4demand[10][P]

contains known market-labeled Lot_IDs.

Example:

RT_JP_RICE_2026W10_0001
RT_JP_RICE_2026W10_0002
RT_JP_RICE_2026W10_0003
RT_DE_RICE_2026W10_0001
6.2 Bridge A

The lots are bridged to:

inbound supply_point.psi4demand[10][S]
6.3 MOM allocation

Policy:

policy = {
    "JP": ["MOM_ASIA"],
    "DE": ["MOM_EURO"],
    "DEFAULT": ["MOM_ASIA"],
}

Expected allocation:

JP lots → MOM_ASIA
DE lot  → MOM_EURO
6.4 Capacity-aware inbound backward planning

Capacity scenario:

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

Expected supply-side seed:

demand/S → supply/S
demand/P → supply/P
supply/CO = []
supply/I  = []
7. Implemented Tests

Focused tests were added in:

tests/test_e2e_demand_to_supply_bridge_flow_smoke.py

They verify:

1. Bridge A runs.
2. MOM allocation runs.
3. TOBE capacity-aware inbound backward planning runs.
4. Bridge B runs.
5. JP lots go to MOM_ASIA.
6. DE lots go to MOM_EURO.
7. MOM_ASIA overflow shifts from week 10 to week 9.
8. Bridge B mirrors finalized demand/S and demand/P into supply/S and supply/P.
9. Lot_ID identity is preserved.
10. Optional backlog scenario preserves Lot_ID identity.
11. All PSI buckets remain list[str].
12. No numeric quantities are inserted.
13. Forward Planning is not executed.
8. Test Summary

The new E2E smoke test passed:

python -m pytest tests/test_e2e_demand_to_supply_bridge_flow_smoke.py

Result:

2 passed

Compatibility tests also passed:

python -m pytest tests/test_demand_to_supply_execution_bridge.py
python -m pytest tests/test_outbound_to_inbound_bridge_to_mom_allocation.py
python -m pytest tests/test_outbound_to_inbound_demand_bridge.py
python -m pytest tests/test_capacity_aware_inbound_backward_planning.py
python -m pytest tests/test_japanese_rice_case_smoke.py

Observed results:

tests/test_demand_to_supply_execution_bridge.py: 10 passed
tests/test_outbound_to_inbound_bridge_to_mom_allocation.py: 1 passed
tests/test_outbound_to_inbound_demand_bridge.py: 10 passed
tests/test_capacity_aware_inbound_backward_planning.py: 3 passed
tests/test_japanese_rice_case_smoke.py: 1 passed
9. Completion Criteria

This milestone satisfies the intended completion criteria.

[OK] E2E smoke test exists
[OK] Bridge A runs
[OK] MOM allocation runs
[OK] capacity-aware inbound backward planning runs
[OK] Bridge B runs
[OK] Lot_ID identity is preserved
[OK] shifted lots are visible
[OK] backlog record preserves Lot_ID
[OK] psi4demand buckets remain list[str]
[OK] psi4supply buckets remain list[str]
[OK] no numeric quantities are inserted
[OK] no Forward Planning is executed
[OK] focused tests pass
10. Latest Commit

Implementation was completed with:

89cfeeb Add E2E demand-to-supply bridge flow smoke

Work was performed on:

feature/with-capacity-psi-engine-v0r2
11. Important Boundary

This milestone does not implement:

Forward Planning
With Capacity Forward PUSH
run_full_plan integration
GUI integration
costing / KPI
Management Issue Generation
OR optimization

It only verifies the demand-side bridge flow through supply-side seed state.

12. Meaning of This Milestone

This milestone confirms that the following bridge chain is now connected:

Bridge A
    ↓
MOM allocation
    ↓
capacity-aware inbound backward planning
    ↓
Bridge B

This is the first compact E2E demand-to-supply bridge flow in WOM.

Before this milestone, these pieces were individually verified.

After this milestone, they are verified as one continuous flow.

13. Current Completed Chain

The completed chain is:

outbound supply_point.psi4demand[P]
    ↓
inbound supply_point.psi4demand[S]
    ↓
MOM.psi4demand[S]
    ↓
MOM.psi4demand[P] with early build / backlog
    ↓
MOM.psi4supply[S/P]

This is the first verified bridge from demand-side E2E planning into supply-side PSI seed state.

14. Core Invariants Preserved

The following invariants remain preserved:

1. PSI buckets hold Lot_ID lists.
2. Quantity is len(list).
3. Lot attributes remain outside PSI buckets.
4. Demand Anchored Lots do not disappear.
5. Shifted lots remain traceable.
6. Backlog lots preserve Lot_ID identity.
7. psi4supply is written only by Bridge B.
8. Forward Planning is not executed inside the bridge smoke.
15. Future Milestones
15.1 Forward Supply Execution after Bridge B

Next target:

finalized psi4demand
    ↓
Bridge B
    ↓
psi4supply
    ↓
Forward Supply Execution
15.2 With Capacity Forward PUSH

After supply-side PSI is seeded:

psi4supply
    ↓
Forward PUSH with Capacity
15.3 Run Full Plan Integration

Once the explicit smoke flow is stable, this sequence can be integrated into the controlled Run Full Plan pipeline.

Future target:

Bridge A
    ↓
MOM allocation
    ↓
capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
Forward Planning
16. Summary

The E2E Demand-to-Supply Bridge Flow Smoke is complete.

The completed MVP flow is:

Bridge A
    ↓
MOM allocation
    ↓
TOBE capacity-aware inbound backward planning
    ↓
Bridge B

This prepares WOM for the next major phase:

Forward Supply Execution / With Capacity Forward PUSH