# WOM Demand Layer Bridge and Supply Execution Bridge Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-20  
**Status:** Design memo  
**Target path:** `docs/design/wom_demand_layer_bridge_and_supply_execution_bridge.md`

**Related design documents:**

- `docs/design/current_wom_backward_planning_and_capacity_flow_mapping.md`
- `docs/design/rice_case_backward_planning_after_seed.md`
- `docs/design/rice_case_backward_planning_after_seed_completion.md`
- `docs/design/wom_capacity_input_granularity_adapter.md`
- `docs/design/capacity_provider_monthly_csv_adapter_v0r2.md`

---

## 1. Purpose

This memo defines the conceptual boundary between two different bridge concepts in WOM:

1. **Outbound-to-Inbound Demand Bridge**
2. **Demand-to-Supply Execution Bridge**

These are often confused because both are "connections" between planning structures.  
However, they occur at different phases and have different meanings.

The most important design principle is:

> Connect the E2E supply chain first in the **demand layer**.  
> Execute supply only after demand allocation and capacity-aware backward planning are complete.

---

## 2. Core Idea

The correct sequence is:

```text
Outbound demand planning
    ↓
Outbound-to-Inbound Demand Bridge
    ↓
MOM Production Allocation
    ↓
Capacity-Aware Backward Demand Planning
    ↓
Demand-to-Supply Execution Bridge
    ↓
Forward Supply Execution
```

In particular:

```text
outbound supply_point.psi4demand[w][P]
    ↓
inbound demand context
```

should happen **before**:

```text
psi4demand
    ↓
psi4supply
```

This distinction is central to the design.

---

## 3. Current WOM Tree Structure

### 3.1 Outbound tree

The outbound tree represents the demand / market-facing side.

```text
supply_point
    ↓
DADxxx nodes
    ↓
market / customer / demand leaf nodes
```

Backward Planning on this tree propagates market demand upward:

```text
leaf demand
    ↓
DAD nodes
    ↓
outbound supply_point
```

### 3.2 Inbound tree

The inbound tree represents the production / procurement / upstream supply side.

```text
supply_point
    ↓
MOMxxx nodes
    ↓
upstream / process / material leaf nodes
```

Backward Planning on this tree propagates assigned production demand from MOM nodes toward upstream / material / process leaf nodes.

### 3.3 supply_point

Both outbound and inbound trees contain a node named `supply_point`.

However, in product-specific PlanNode trees, outbound `supply_point` and inbound `supply_point` should be treated as separate PlanNode objects synchronized by explicit bridge operations.

Do not assume they are the same Python object.

---

## 4. Bridge A: Outbound-to-Inbound Demand Bridge

### 4.1 Purpose

Bridge A moves accumulated outbound demand requirements into the inbound demand planning context.

Conceptually:

```text
outbound leaf demand
    ↓
outbound backward planning
    ↓
DAD demand P
    ↓
outbound supply_point demand P
    ↓
inbound demand bridge
    ↓
inbound demand context
```

### 4.2 Source bucket

The primary source is:

```python
outbound_supply_point.psi4demand[w][PSI_P]
```

This bucket represents the requirement accumulated by outbound backward planning.

### 4.3 Target bucket

The target should be demand-side, not supply-side.

Recommended MVP target:

```python
inbound_supply_point.psi4demand[w][PSI_S]
```

or an equivalent input to MOM allocation.

### 4.4 Not immediate supply execution

Do **not** bridge directly to:

```python
inbound_supply_point.psi4supply[w][PSI_S]
```

at this stage.

Reason:

MOM allocation and capacity-aware backward planning have not yet been completed.

---

## 5. Bridge A Week Alignment

### 5.1 MVP assumption

For MVP, use zero bridge lead time:

```text
bridge_leadtime_weeks = 0
```

Therefore:

```text
source_week = target_week
```

Example:

```text
outbound supply_point.psi4demand[W][P]
    ↓
inbound supply_point.psi4demand[W][S]
```

### 5.2 Future extension

Future bridge may support lead time:

```text
target_week = source_week + bridge_leadtime_weeks
```

Example:

```text
LT = 1:
    W → W+1
```

---

## 6. Bridge A Lot Operation

The bridge should operate on Lot_ID lists.

Correct operation:

```python
target_lots.extend(source_lot_ids)
```

Incorrect operations:

```python
target_bucket = len(source_lot_ids)
target_bucket.append(quantity)
```

Lot_ID identity must be preserved.  
The bridge should not generate new Lot_IDs unless a future transformation rule explicitly requires it.

---

## 7. MOM Production Allocation

After Bridge A, inbound demand lots must be allocated to MOM nodes.

### 7.1 Current implementation candidate

Existing function:

```python
allocate_markets_to_moms(...)
```

### 7.2 Current conceptual behavior

```text
1. collect source lots
2. extract market_key from lot_id
3. select assigned MOM using policy dictionary
4. append lot to selected MOM.psi4demand[w][S]
```

### 7.3 Current role

This is currently a policy-based MOM allocation.

```text
market_key
    ↓
allocation policy
    ↓
MOM node
```

### 7.4 Future optimization role

Future versions may replace or extend this with OR optimization.

Possible objective functions:

```text
service level
market priority
profit contribution
capacity balance
transport cost
leadtime
strategic priority
```

Possible constraints:

```text
MOM capacity
product capability
lane availability
leadtime
market demand
inventory availability
```

### 7.5 Placement

MOM allocation occurs after Bridge A and before inbound backward planning.

```text
Outbound-to-Inbound Demand Bridge
    ↓
MOM Production Allocation
    ↓
Inbound Backward Planning
```

---

## 8. Capacity-Aware Backward Demand Planning

After MOM allocation, demand lots are propagated through the inbound tree.

### 8.1 Current implementation candidates

Relevant functions include:

```text
inbound_backward_MOM_to_leaf(...)
level_mom_demand_with_capacity(...)
inbound_MOM_leveling_vs_capacity(...)
```

### 8.2 Capacity handling

MOM capacity should constrain:

```python
MOM.psi4demand[w][PSI_P]
```

If P lots exceed capacity, overflow lots may be shifted earlier.

Conceptually:

```text
MOM.psi4demand[w][P] > capacity[w]
    ↓
keep within capacity at w
    ↓
move overflow to w-1, w-2, ...
```

This corresponds to advance production / backward time shifting.

### 8.3 Current capacity source

Current functions may consume:

```text
env.weekly_capability[product][mom_name][w]
env.weekly_capability[mom_name][w]
mom.nx_capacity
```

---

## 9. Bridge B: Demand-to-Supply Execution Bridge

### 9.1 Purpose

Bridge B transfers finalized demand-side planning results into supply-side execution simulation structures.

```text
finalized psi4demand
    ↓
psi4supply
```

This is the execution bridge.

### 9.2 When it should run

Bridge B should run after:

```text
Outbound-to-Inbound Demand Bridge
MOM Production Allocation
Capacity-Aware Backward Demand Planning
```

### 9.3 Current implementation candidates

Existing functions include:

```text
bridge_inbound_demand_to_supply(root)
copy_demand_to_supply_rec(node)
copy_S_demand2supply(node)
copy_P_demand2supply(node)
```

### 9.4 Current bridge behavior candidate

`bridge_inbound_demand_to_supply(root)` conceptually does:

```text
node.psi4demand[w][S]
    ↓
node.psi4supply[w][S]
```

with a clean seed:

```python
node.psi4supply[w] = [demand_s, [], [], []]
```

### 9.5 Alternative clone behavior

`copy_demand_to_supply_rec(node)` conceptually clones:

```text
node.psi4demand
    ↓
node.psi4supply
```

This is broader and may copy more buckets than needed.

### 9.6 Need for canonical policy

Before adding new logic, WOM should decide which bridge is canonical.

A canonical bridge should define:

```text
source layer
target layer
bucket mapping
copy vs clone
overwrite vs append
scope: full tree or MOM subtree
leadtime handling
```

---

## 10. Forward Supply Execution

After Bridge B, Forward Planning runs on `psi4supply`.

### 10.1 Current implementation candidates

Existing functions include:

```text
PUSH_process(...)
PULL_process(...)
push_pull_all_psi2i_decouple4supply5(...)
inbound_forward_leaf_to_MOM(...)
```

### 10.2 With Capacity Forward PUSH placement

With Capacity Forward PUSH should be placed here:

```text
psi4supply seed
    ↓
Forward PUSH with Capacity
```

It should not replace:

```text
Outbound-to-Inbound Demand Bridge
MOM Allocation
Capacity-Aware Backward Planning
```

It should validate and simulate supply execution under capacity constraints.

---

## 11. End-to-End Planning Structure

The recommended structure is:

```text
[1] Plan input seed
    Rice weekly input / S_month / P_month / case data
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
    inbound demand context

[4] MOM Production Allocation
    demand lots
        ↓
    assigned MOM nodes

[5] Capacity-Aware Inbound Backward Planning
    MOM demand
        ↓
    upstream / inbound leaf demand
        ↓
    capacity leveling / advance production

[6] Demand-to-Supply Execution Bridge
    finalized psi4demand
        ↓
    psi4supply

[7] Forward Supply Execution
    psi4supply
        ↓
    PUSH / PULL / With Capacity Forward PUSH
```

---

## 12. Design Principles

### 12.1 Do not mix demand bridge and supply execution

Outbound-to-inbound connection is first a demand-layer bridge.

Supply execution starts later.

### 12.2 Do not treat supply_point objects as identical

Outbound `supply_point` and inbound `supply_point` may share the same name but belong to different product trees.

They should be synchronized by explicit bridge operations.

### 12.3 Bridge only required lots / buckets

Do not blindly copy entire tree state unless explicitly intended.

Prefer targeted bridge operations.

### 12.4 Preserve Lot_ID identity

All bridges must preserve Lot_ID lists.

### 12.5 Do not insert numeric quantities into PSI buckets

All PSI buckets remain Lot_ID lists.

### 12.6 Keep MOM allocation separate

MOM allocation is a decision / allocation layer and may later become an optimization problem.

### 12.7 Keep capacity leveling separate

Capacity-aware backward planning belongs after MOM allocation and before supply execution.

---

## 13. Current Implementation Mapping

### 13.1 Confirmed or likely mappings

```text
Outbound Backward Planning:
    outbound_backward_leaf_to_MOM(...)

Outbound-to-Inbound Demand Bridge:
    connect_outbound2inbound(...)

MOM Production Allocation:
    allocate_markets_to_moms(...)

Capacity-Aware Backward Planning:
    level_mom_demand_with_capacity(...)
    inbound_MOM_leveling_vs_capacity(...)

Demand-to-Supply Execution Bridge:
    bridge_inbound_demand_to_supply(...)
    copy_demand_to_supply_rec(...)
    copy_S_demand2supply(...)
    copy_P_demand2supply(...)

Forward Supply Execution:
    PUSH_process(...)
    PULL_process(...)
    push_pull_all_psi2i_decouple4supply5(...)
```

### 13.2 Open questions

```text
1. Which demand-to-supply bridge should be canonical?
2. Should Bridge B clone all demand buckets or only selected buckets?
3. Should Bridge A target inbound supply_point or directly MOM allocation input?
4. Does connect_outbound2inbound preserve Lot_IDs exactly?
5. Should Bridge A have bridge_leadtime_weeks?
6. Should Bridge B overwrite or append?
7. Should Bridge B operate full inbound tree or MOM subtrees?
```

---

## 14. Recommended Canonical Bridge Direction

### 14.1 Bridge A canonical direction

Recommended:

```text
outbound supply_point.psi4demand[w][P]
    ↓
inbound demand context
```

MVP target:

```text
inbound supply_point.psi4demand[w][S]
```

or input to:

```text
allocate_markets_to_moms(...)
```

### 14.2 Bridge B canonical direction

Recommended:

```text
finalized inbound psi4demand
    ↓
inbound psi4supply
```

MVP target:

```text
MOM subtree demand plan
    ↓
MOM subtree supply seed
```

This avoids accidentally copying entire inbound root state across all MOM branches.

---

## 15. Next Implementation Roadmap

### Step 1: Inspect current bridge functions

Inspect:

```text
connect_outbound2inbound(...)
bridge_inbound_demand_to_supply(...)
copy_demand_to_supply_rec(...)
copy_S_demand2supply(...)
copy_P_demand2supply(...)
```

### Step 2: Define canonical Bridge A

Create:

```text
docs/design/wom_outbound_to_inbound_demand_bridge.md
```

### Step 3: Define canonical Bridge B

Create:

```text
docs/design/wom_demand_to_supply_execution_bridge.md
```

### Step 4: Implement small bridge smoke tests

Use minimal PlanNode trees and known Lot_IDs.

### Step 5: Add With Capacity Forward PUSH placement

After canonical Bridge B is verified, connect forward supply execution.

---

## 16. Summary

The central lesson is:

```text
Do not jump directly from outbound demand to inbound supply execution.
```

The correct structure is:

```text
Outbound demand planning
    ↓
Outbound-to-Inbound Demand Bridge
    ↓
MOM Production Allocation
    ↓
Capacity-Aware Backward Demand Planning
    ↓
Demand-to-Supply Execution Bridge
    ↓
Forward Supply Execution
```

In short:

```text
Connect the E2E supply chain first in the demand layer.
Execute supply only after demand allocation and capacity-aware backward planning are complete.
```

This separation prevents bridge logic, MOM allocation, capacity leveling, and Forward PUSH from becoming tangled.
