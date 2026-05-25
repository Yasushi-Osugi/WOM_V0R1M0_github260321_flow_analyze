# Outbound-to-Inbound Bridge to MOM Allocation Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-21  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Outbound-to-Inbound Bridge to MOM Allocation**.

The purpose of this milestone was to verify that demand lots bridged from the outbound tree to the inbound demand context can be allocated to MOM nodes using the existing MOM allocation logic.

The completed target flow is:

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

This remains a demand-layer planning process.

This milestone does not execute:

inbound backward planning
capacity leveling
demand-to-supply execution bridge
forward planning
2. Background

The previous milestone implemented Bridge A:

outbound supply_point.psi4demand[w][P]
    ↓
inbound supply_point.psi4demand[w][S]

Bridge A was implemented as a safe demand-layer bridge.

It preserves:

Lot_ID identity
source bucket immutability
V0R8 PSI bucket semantics

The next logical step was to verify that the bridged lots can be consumed by MOM allocation logic.

3. Core Design Principle

The key principle is:

Bridge first.
Allocate MOM second.
Run inbound backward planning third.

The E2E demand should first be bridged into the inbound demand layer.

Then MOM allocation assigns bridged demand lots to appropriate MOM nodes.

Only after this should capacity-aware inbound backward planning run.

4. Critical WOM / PySI V0R8 Assumptions
4.1 PSI bucket structure

The canonical PSI structure remains:

node.psi4demand[w] = [S_ids, CO_ids, I_ids, P_ids]
node.psi4supply[w] = [S_ids, CO_ids, I_ids, P_ids]

Bucket index convention:

PSI_S  = 0
PSI_CO = 1
PSI_I  = 2
PSI_P  = 3
4.2 PSI buckets contain Lot_ID lists

The most important invariant remains:

PSI buckets contain Lot_ID lists, not numeric quantities.

Correct:

MOM_ASIA.psi4demand[w][PSI_S] = ["RT_JP_RICE_2026W40_0001"]

Incorrect:

MOM_ASIA.psi4demand[w][PSI_S] = 1

Quantity remains:

quantity = len(node.psi4demand[w][bucket])
4.3 This milestone stays in the demand layer

This milestone only touches:

psi4demand

It does not write to:

psi4supply
5. Implemented Files

This milestone added the following files:

pysi/plan/bridges/outbound_to_inbound_mom_allocation.py
tests/test_outbound_to_inbound_bridge_to_mom_allocation.py
6. Implemented Behavior
6.1 New bridge-to-MOM allocation helper

A small additive helper was added:

allocate_bridged_demand_to_moms(...)

Its purpose is to adapt Bridge A output to the existing MOM allocation function.

Conceptual flow:

inbound supply_point.psi4demand[w][S]
    ↓
allocate_bridged_demand_to_moms(...)
    ↓
allocate_markets_to_moms(...)
    ↓
MOMxxx.psi4demand[w][S]
6.2 Existing allocation logic reused

The implementation reuses the existing engine function:

allocate_markets_to_moms(...)

The existing function was not modified.

This is important because it preserves existing WOM engine behavior.

6.3 Source alignment

The helper reads bridged lots from:

inbound supply_point.psi4demand[w][S]

and adapts them so that existing allocate_markets_to_moms(...) can process them.

This keeps the responsibility boundary clear:

Bridge A:
    outbound demand/P → inbound supply_point demand/S

MOM Allocation:
    inbound supply_point demand/S → MOM demand/S
6.4 MOM allocation by market policy

The smoke test uses Lot_IDs containing market tokens.

Example:

RT_JP_RICE_2026W40_0001
RT_DE_RICE_2026W40_0002
RT_UNKNOWN_RICE_2026W40_0003

Example policy:

policy = {
    "JP": ["MOM_ASIA"],
    "DE": ["MOM_EURO"],
    "DEFAULT": ["MOM_ASIA"],
}

Expected allocation:

JP lot      → MOM_ASIA
DE lot      → MOM_EURO
UNKNOWN lot → MOM_ASIA
6.5 Demand-layer only

The implementation does not write to psi4supply.

This was explicitly verified in tests.

6.6 Existing MOM demand clearing behavior

The smoke verifies that:

clear_existing_mom_demand=True

clears previous MOM demand before allocation.

This is useful for deterministic full recomputation.

7. Test Summary

The focused test added was:

python -m pytest tests/test_outbound_to_inbound_bridge_to_mom_allocation.py

Result:

1 passed

Compatibility tests also passed:

python -m pytest tests/test_outbound_to_inbound_demand_bridge.py
python -m pytest tests/test_japanese_rice_backward_planning_after_seed.py
python -m pytest tests/test_japanese_rice_actual_prod_tree_seed_integration.py
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_plan_input_plan_node_seeding.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py

Observed results:

tests/test_outbound_to_inbound_demand_bridge.py: 10 passed
tests/test_japanese_rice_backward_planning_after_seed.py: 2 passed
tests/test_japanese_rice_actual_prod_tree_seed_integration.py: 8 passed
tests/test_japanese_rice_case_smoke.py: 1 passed
tests/test_plan_input_plan_node_seeding.py: 11 passed
tests/test_covid_vaccine_with_capacity_push.py: 1 passed
8. Completion Criteria

This milestone satisfies the intended completion criteria.

[OK] Bridge A output can be consumed by MOM allocation
[OK] inbound supply_point.psi4demand[w][S] is populated
[OK] JP lot is allocated to MOM_ASIA
[OK] DE lot is allocated to MOM_EURO
[OK] DEFAULT policy is verified
[OK] MOM target buckets remain Lot_ID lists
[OK] no numeric quantities are inserted
[OK] no psi4supply writes occur
[OK] focused tests pass
[OK] existing Bridge A tests pass
[OK] no GUI changes
[OK] no run_full_plan changes
[OK] no planning engine broad refactor
9. Latest Commit

Implementation was completed with:

2e82b93 Add outbound-to-inbound bridge to MOM allocation smoke

Work was performed on:

feature/with-capacity-psi-engine-v0r2
10. Meaning of This Milestone

This milestone confirms that bridged E2E demand can proceed to MOM allocation.

Before this milestone:

outbound demand/P
    ↓
Bridge A
    ↓
inbound supply_point demand/S

After this milestone:

outbound demand/P
    ↓
Bridge A
    ↓
inbound supply_point demand/S
    ↓
MOM allocation
    ↓
MOM demand/S

This is an important step toward full E2E demand-layer planning.

11. Important Boundary

This milestone still does not run:

inbound backward planning
capacity-aware backward planning
MOM capacity leveling
demand-to-supply execution bridge
forward planning
with Capacity Forward PUSH
GUI integration
run_full_plan integration
OR optimization

It only verifies:

Bridge A
    ↓
MOM Production Allocation
12. Future Milestones
12.1 MOM Allocation to Capacity-Aware Inbound Backward Planning

Next natural milestone:

MOM.psi4demand[w][S]
    ↓
capacity-aware inbound backward planning
    ↓
MOM.psi4demand[w][P]

This should verify that MOM-assigned demand lots can proceed into inbound backward planning.

12.2 Capacity Leveling

After inbound backward planning:

MOM.psi4demand[w][P]
    ↓
level_mom_demand_with_capacity(...)
    ↓
capacity feasibility / advance production

This is where weekly capability and MOM capacity constraints become important.

12.3 Demand-to-Supply Execution Bridge

After demand-side planning is finalized:

finalized psi4demand
    ↓
psi4supply

This is Bridge B.

12.4 With Capacity Forward PUSH

After Bridge B:

psi4supply
    ↓
Forward PUSH with Capacity
13. Summary

This milestone completed the demand-layer connection from Bridge A to MOM allocation.

The completed flow is:

outbound supply_point.psi4demand[w][P]
    ↓
inbound supply_point.psi4demand[w][S]
    ↓
MOM allocation
    ↓
MOMxxx.psi4demand[w][S]

The most important rule remains:

This is still demand-layer planning.
It does not execute supply.
It does not write to psi4supply.

This confirms that E2E demand can now pass from the outbound tree into the inbound MOM allocation stage while preserving V0R8 Lot_ID list semantics.