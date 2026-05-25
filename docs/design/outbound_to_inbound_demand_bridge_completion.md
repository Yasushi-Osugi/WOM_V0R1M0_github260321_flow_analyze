# Outbound-to-Inbound Demand Bridge Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-20  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Bridge A: Outbound-to-Inbound Demand Bridge**.

The purpose of this milestone was to implement a small, safe, explicit bridge that connects the E2E supply chain **in the demand layer**, not in the supply execution layer.

The completed target flow is:

```text
outbound supply_point.psi4demand[w][P]
    ↓
inbound supply_point.psi4demand[w][S]

This is the first E2E bridge before:

MOM Production Allocation
    ↓
Capacity-Aware Backward Demand Planning
    ↓
Demand-to-Supply Execution Bridge
    ↓
Forward Supply Execution
2. Background

The bridge concept was split into two stages.

Bridge A: Outbound-to-Inbound Demand Bridge
outbound demand context
    ↓
inbound demand context

This is a demand-layer planning bridge.

Bridge B: Demand-to-Supply Execution Bridge
finalized psi4demand
    ↓
psi4supply

This is an execution bridge that should occur only after MOM allocation and capacity-aware backward planning.

This milestone implemented Bridge A only.

3. Critical WOM / PySI V0R8 Assumptions
3.1 Outbound and inbound PlanNodes are separate

Both outbound and inbound product trees may contain a node named:

supply_point

However, they are separate PlanNode objects belonging to separate trees.

The bridge explicitly copies Lot_IDs from one tree to the other.

3.2 PSI bucket structure

The canonical V0R8 PSI structure is:

node.psi4demand[w] = [S_ids, CO_ids, I_ids, P_ids]
node.psi4supply[w] = [S_ids, CO_ids, I_ids, P_ids]

Bucket index convention:

PSI_S  = 0
PSI_CO = 1
PSI_I  = 2
PSI_P  = 3
3.3 PSI buckets contain Lot_ID lists, not numeric quantities

Correct:

node.psi4demand[w][PSI_S] = ["LOT_A", "LOT_B"]

Incorrect:

node.psi4demand[w][PSI_S] = 2

Quantity remains:

quantity = len(node.psi4demand[w][bucket])
4. Implemented Files

This milestone added:

pysi/plan/bridges/__init__.py
pysi/plan/bridges/outbound_to_inbound_demand_bridge.py
tests/test_outbound_to_inbound_demand_bridge.py
5. Implemented Features
5.1 PSI bucket constants

Implemented canonical PSI bucket mapping:

PSI_BUCKET_INDEX = {
    "S": 0,
    "CO": 1,
    "I": 2,
    "P": 3,
}
5.2 OutboundInboundDemandBridgeResult

A structured result object was added.

It records:

source_node_name
target_node_name
bridge_leadtime_weeks
copied_lot_count
weeks_touched
missing_source_node
missing_target_node
invalid_weeks
duplicate_lot_ids
mode
5.3 bridge_outbound_to_inbound_demand

Implemented:

bridge_outbound_to_inbound_demand(...)

Default MVP behavior:

source:
    outbound supply_point.psi4demand[w][P]

target:
    inbound supply_point.psi4demand[w][S]

This bridge copies Lot_IDs only.

It does not write to psi4supply.

5.4 Supported modes

The bridge supports:

replace
append
dedupe_append
replace

Clears target bucket first, then copies source lots.

This is the default mode and is idempotent.

append

Appends source lots to the target bucket.

dedupe_append

Appends only Lot_IDs not already present in the target bucket.

5.5 Leadtime support

The bridge supports:

bridge_leadtime_weeks

Default:

0

Meaning:

source_week = target_week

If bridge_leadtime_weeks = 1, source week 0 maps to target week 1.

5.6 Missing node handling

If the source node is missing:

missing_source_node = True

If the target node is missing:

missing_target_node = True

The bridge returns safely.

It does not create missing nodes.

5.7 Safety behavior

The bridge:

does not modify source buckets
does not write to psi4supply
does not insert numeric quantities
preserves Lot_ID identity
records invalid weeks
6. Test Summary

New focused tests:

python -m pytest tests/test_outbound_to_inbound_demand_bridge.py

Result:

10 passed

Compatibility tests also passed:

python -m pytest tests/test_japanese_rice_backward_planning_after_seed.py
python -m pytest tests/test_japanese_rice_actual_prod_tree_seed_integration.py
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_plan_input_plan_node_seeding.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py

Observed results:

tests/test_japanese_rice_backward_planning_after_seed.py: 2 passed
tests/test_japanese_rice_actual_prod_tree_seed_integration.py: 8 passed
tests/test_japanese_rice_case_smoke.py: 1 passed
tests/test_plan_input_plan_node_seeding.py: 11 passed
tests/test_covid_vaccine_with_capacity_push.py: 1 passed
7. Completion Criteria

This milestone satisfies the intended completion criteria.

[OK] outbound_to_inbound_demand_bridge.py exists
[OK] bridge_outbound_to_inbound_demand works
[OK] outbound demand/P copies to inbound demand/S
[OK] source bucket is not modified
[OK] replace mode is idempotent
[OK] append mode works
[OK] dedupe_append mode works
[OK] bridge_leadtime_weeks works
[OK] missing source / target are handled safely
[OK] PSI buckets contain Lot_ID lists, not quantities
[OK] no psi4supply writes occur
[OK] focused tests pass
[OK] no GUI changes
[OK] no run_full_plan changes
[OK] no loader changes
[OK] no planning engine changes
8. Latest Commit

Implementation was completed with:

3026d07 Add outbound-to-inbound demand bridge utility

Work was performed on:

feature/with-capacity-psi-engine-v0r2
9. Meaning of This Milestone

This milestone implements the first explicit E2E demand-layer bridge.

Before this milestone, the conceptual bridge existed in design and through older engine behavior.

After this milestone, WOM has a small explicit utility for:

outbound supply_point.psi4demand[w][P]
    ↓
inbound supply_point.psi4demand[w][S]

This makes the E2E demand-layer connection testable and independent from supply execution.

10. Important Boundary

This bridge does not perform:

MOM allocation
capacity-aware backward planning
demand-to-supply execution bridge
Forward Planning
with Capacity Forward PUSH
GUI integration
run_full_plan integration

It is only Bridge A.

11. Future Milestones
11.1 Bridge A to MOM allocation smoke

Next natural milestone:

Outbound-to-Inbound Demand Bridge
    ↓
allocate_markets_to_moms(...)

This will verify that bridged inbound demand lots can be assigned to MOM nodes.

11.2 Capacity-aware inbound backward planning

After MOM allocation:

MOM.psi4demand[w][S]
    ↓
level_mom_demand_with_capacity(...)
    ↓
inbound backward planning
11.3 Demand-to-Supply Execution Bridge

After demand-side planning is finalized:

finalized psi4demand
    ↓
psi4supply

This is Bridge B.

11.4 With Capacity Forward PUSH

After Bridge B:

psi4supply
    ↓
Forward PUSH with Capacity
12. Summary

Bridge A has been completed as a safe, explicit demand-layer bridge.

The key rule is:

Do not jump directly from outbound demand to inbound supply execution.

The completed operation is:

outbound demand/P
    ↓
inbound demand/S

The next step is to connect this bridge to MOM allocation while preserving the separation between:

demand-layer E2E planning

and:

supply-layer execution simulation