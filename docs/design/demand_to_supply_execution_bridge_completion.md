# Demand-to-Supply Execution Bridge MVP Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-21  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Demand-to-Supply Execution Bridge MVP**.

The purpose of this milestone was to implement Bridge B:

```text
finalized psi4demand
    ↓
psi4supply

This bridge transfers finalized demand-side planning lots into the supply-side execution simulation layer.

It is intentionally separate from Bridge A.

Bridge A:
    outbound demand context
        ↓
    inbound demand context

Bridge B:
    finalized demand plan
        ↓
    supply execution seed
2. Background

Before this milestone, the demand-layer flow had reached:

outbound supply_point.psi4demand[w][P]
    ↓
Bridge A
    ↓
inbound supply_point.psi4demand[w][S]
    ↓
MOM allocation
    ↓
MOM.psi4demand[w][S]
    ↓
TOBE capacity-aware inbound backward planning
    ↓
MOM.psi4demand[w][P]

The next required step was to bridge the finalized demand-side state into psi4supply for forward execution.

3. Critical WOM / PySI V0R8 Assumptions
3.1 PSI bucket structure

The canonical PSI structure remains:

node.psi4demand[w] = [S_ids, CO_ids, I_ids, P_ids]
node.psi4supply[w] = [S_ids, CO_ids, I_ids, P_ids]

Bucket index convention:

PSI_S  = 0
PSI_CO = 1
PSI_I  = 2
PSI_P  = 3
3.2 PSI buckets contain Lot_ID lists

The most important invariant remains:

PSI buckets contain Lot_ID lists, not numeric quantities.

Correct:

node.psi4supply[w][PSI_S] = ["LOT_A", "LOT_B"]

Incorrect:

node.psi4supply[w][PSI_S] = 2

Quantity remains:

quantity = len(node.psi4supply[w][bucket])
4. Implemented Files

This milestone added or updated:

pysi/plan/bridges/__init__.py
pysi/plan/bridges/demand_to_supply_execution_bridge.py
tests/test_demand_to_supply_execution_bridge.py
5. Implemented Features
5.1 DemandToSupplyBridgeResult

A structured result object was added.

It records:

root_node_name
bridge_policy
mode
bridge_leadtime_weeks
copied_lot_count
weeks_touched
nodes_touched
invalid_weeks
non_list_bucket_errors
duplicate_lot_ids

This makes the bridge auditable and testable.

5.2 bridge_demand_to_supply_execution

Implemented:

bridge_demand_to_supply_execution(...)

This function copies Lot_ID lists from psi4demand to psi4supply according to bridge policy and mode.

It does not run planning engines.

It does not call:

PUSH_process
PULL_process
calcPS2I4supply
Backward Planning
Forward Planning
6. Supported Bridge Policies
6.1 s_p_only

This is the MVP default policy.

Behavior:

demand/S → supply/S
demand/P → supply/P
supply/CO = []
supply/I  = []

This prepares the supply layer for future Forward Planning while avoiding unsafe copying of demand-layer CO / I semantics.

6.2 s_only

Behavior:

demand/S → supply/S
supply/CO = []
supply/I  = []
supply/P  = []

This resembles the narrow behavior of existing bridge_inbound_demand_to_supply(...).

6.3 full_clone

Behavior:

demand/S  → supply/S
demand/CO → supply/CO
demand/I  → supply/I
demand/P  → supply/P

This is intentionally not the default because CO / I may have different meanings between demand and supply layers.

7. Supported Modes
7.1 replace

Default.

Clears target buckets according to bridge policy, then copies source lots.

This mode is idempotent.

Running the bridge twice produces the same target supply state.

7.2 append

Appends source lots to existing supply buckets.

7.3 dedupe_append

Appends only Lot_IDs not already present in the target supply bucket.

This prevents duplicate Lot_IDs.

8. Leadtime Handling

The bridge supports:

bridge_leadtime_weeks

Default:

0

Meaning:

source_week = target_week

If:

bridge_leadtime_weeks = 1

then:

demand week 0 → supply week 1

Out-of-range target weeks are recorded in invalid_weeks and skipped.

The bridge does not silently extend PSI horizon.

9. Safety Invariants

This implementation preserves the following invariants.

[OK] Source psi4demand is not modified.
[OK] Target psi4supply contains Lot_ID lists.
[OK] No numeric quantities are inserted into PSI buckets.
[OK] Lot_ID identity is preserved.
[OK] Replace mode is idempotent.
[OK] Invalid / non-list bucket structures are recorded.
[OK] No planning engine is executed.
10. Tests

Focused tests were added in:

tests/test_demand_to_supply_execution_bridge.py

They cover:

1. s_p_only behavior
2. demand immutability
3. replace idempotency
4. append mode
5. dedupe_append mode
6. leadtime shift
7. full_clone policy
8. s_only policy
9. non-list bucket safety
10. no numeric quantities inserted
11. Test Summary

The following tests passed.

python -m pytest tests/test_demand_to_supply_execution_bridge.py

Result:

10 passed

Compatibility tests also passed:

python -m pytest tests/test_outbound_to_inbound_bridge_to_mom_allocation.py
python -m pytest tests/test_outbound_to_inbound_demand_bridge.py
python -m pytest tests/test_japanese_rice_backward_planning_after_seed.py
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_plan_input_plan_node_seeding.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py

Observed results:

tests/test_outbound_to_inbound_bridge_to_mom_allocation.py: 1 passed
tests/test_outbound_to_inbound_demand_bridge.py: 10 passed
tests/test_japanese_rice_backward_planning_after_seed.py: 2 passed
tests/test_japanese_rice_case_smoke.py: 1 passed
tests/test_plan_input_plan_node_seeding.py: 11 passed
tests/test_covid_vaccine_with_capacity_push.py: 1 passed
12. Completion Criteria

This milestone satisfies the intended completion criteria.

[OK] demand_to_supply_execution_bridge.py exists
[OK] bridge_demand_to_supply_execution works
[OK] s_p_only policy works
[OK] s_only policy works
[OK] full_clone policy works
[OK] replace mode is idempotent
[OK] append mode works
[OK] dedupe_append mode works
[OK] bridge_leadtime_weeks works
[OK] source psi4demand is not modified
[OK] target psi4supply contains Lot_ID lists only
[OK] no numeric quantity insertion
[OK] focused tests pass
[OK] no GUI changes
[OK] no run_full_plan changes
[OK] no planning engine changes
13. Latest Commit

Implementation was completed with:

00e46dd Add demand-to-supply execution bridge MVP

Work was performed on:

feature/with-capacity-psi-engine-v0r2
14. Meaning of This Milestone

This milestone completes the first explicit Bridge B implementation.

Before this milestone:

finalized psi4demand
    ↓
supply execution bridge was only implicit / scattered

After this milestone:

finalized psi4demand
    ↓
explicit demand-to-supply execution bridge
    ↓
psi4supply

This prepares the supply layer for future Forward Planning and With Capacity Forward PUSH.

15. Important Boundary

This milestone does not implement:

Forward Planning
With Capacity Forward PUSH
MOM allocation
Capacity-aware backward planning
GUI integration
run_full_plan integration

It only implements the bridge from finalized demand-side plan to supply-side seed state.

16. Future Milestones
16.1 Forward Supply Execution after Bridge B

Next flow:

finalized psi4demand
    ↓
Bridge B
    ↓
psi4supply
    ↓
Forward Supply Execution
16.2 With Capacity Forward PUSH

After the supply layer is seeded:

psi4supply
    ↓
Forward PUSH with Capacity
16.3 Run Full Plan Integration

Eventually:

Bridge A
    ↓
MOM allocation
    ↓
capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
Forward Planning

can be integrated into the controlled Run Full Plan sequence.

17. Summary

Demand-to-Supply Execution Bridge MVP is complete.

The completed operation is:

finalized psi4demand
    ↓
psi4supply

The recommended MVP policy is:

s_p_only:
    demand/S → supply/S
    demand/P → supply/P
    supply/CO = []
    supply/I  = []

The key invariant remains:

PSI buckets hold Lot_ID lists.
Quantity is len(list).
Lot attributes live outside PSI buckets.

This milestone prepares WOM for the next stage:

Forward Supply Execution / With Capacity Forward PUSH