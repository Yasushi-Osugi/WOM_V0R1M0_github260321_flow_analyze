# Outbound-to-Inbound Bridge to MOM Allocation Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-20  
**Status:** Design memo  
**Target path:** `docs/design/outbound_to_inbound_bridge_to_mom_allocation.md`

---

## 1. Purpose

This memo defines the integration between:

```text
Bridge A:
    Outbound-to-Inbound Demand Bridge
```

and:

```text
MOM Production Allocation
```

The previous milestone implemented Bridge A:

```text
outbound supply_point.psi4demand[w][P]
    ↓
inbound supply_point.psi4demand[w][S]
```

The next step is to verify that the bridged inbound demand lots can be passed into existing or future MOM allocation logic:

```text
inbound supply_point.psi4demand[w][S]
    ↓
allocate_markets_to_moms(...)
    ↓
MOMxxx.psi4demand[w][S]
```

This memo defines the design boundary, MVP behavior, current implementation mapping, and test strategy for that connection.

---

## 2. Core Principle

The key principle is:

```text
E2E demand should be bridged into the inbound demand layer first,
then allocated to MOM nodes,
then processed by capacity-aware inbound backward planning.
```

In other words:

```text
Do not jump directly from outbound demand to supply execution.

Do not let the inbound root / supply_point blindly propagate the same demand into all MOM branches.

Bridge first.
Allocate MOM second.
Run inbound backward planning third.
```

---

## 3. Position in the Overall Planning Flow

The intended sequence is:

```text
[1] Outbound Backward Planning
    leaf demand
        ↓
    DAD
        ↓
    outbound supply_point.psi4demand[w][P]

[2] Bridge A: Outbound-to-Inbound Demand Bridge
    outbound supply_point.psi4demand[w][P]
        ↓
    inbound supply_point.psi4demand[w][S]

[3] MOM Production Allocation
    inbound supply_point demand lots
        ↓
    assigned MOM nodes

[4] Capacity-Aware Inbound Backward Planning
    MOM demand
        ↓
    upstream / inbound leaf demand
        ↓
    capacity leveling / advance production if needed

[5] Bridge B: Demand-to-Supply Execution Bridge
    finalized psi4demand
        ↓
    psi4supply

[6] Forward Supply Execution
    psi4supply
        ↓
    PUSH / PULL / With Capacity Forward PUSH
```

This memo focuses on step `[3]`.

---

## 4. Current Implementation Context

### 4.1 Bridge A completed

The current Bridge A utility is:

```text
pysi/plan/bridges/outbound_to_inbound_demand_bridge.py
```

It implements:

```python
bridge_outbound_to_inbound_demand(...)
```

Default behavior:

```text
outbound supply_point.psi4demand[w][P]
    ↓
inbound supply_point.psi4demand[w][S]
```

Important safety behavior:

```text
source bucket is not modified
psi4supply is not touched
Lot_ID lists are copied, not quantities
replace / append / dedupe_append modes are supported
```

### 4.2 Existing MOM allocation function

The existing function candidate is:

```python
allocate_markets_to_moms(...)
```

located in:

```text
pysi/plan/engines.py
```

Current conceptual behavior:

```text
1. collect source lots
2. extract market_key from lot_id
3. select assigned MOM using policy dictionary
4. append lot to selected MOM.psi4demand[w][S]
```

This function is policy-based, not optimization-based.

### 4.3 Existing inbound backward planning

After MOM allocation, the existing flow uses MOM subtree planning.

Relevant function:

```python
inbound_backward_MOM_to_leaf(...)
```

which identifies MOM nodes and runs inbound backward planning per MOM subtree.

This avoids propagating the same demand through all MOM branches from `supply_point`.

---

## 5. Why MOM Allocation Must Be Separate from Bridge A

Bridge A should not decide the MOM.

Bridge A only transfers demand requirements across the E2E boundary.

```text
Bridge A:
    outbound demand context
        ↓
    inbound demand context
```

MOM allocation is a separate decision layer:

```text
MOM Allocation:
    inbound demand lots
        ↓
    selected MOM nodes
```

This separation is important because MOM allocation may depend on:

```text
market priority
MOM capacity
leadtime
transport cost
product capability
service level
strategic priority
optimization objective
```

If Bridge A directly assigns lots to MOMs, it mixes connection logic with allocation decision logic.

---

## 6. MOM Allocation as Policy-Based Today, Optimization Candidate Tomorrow

### 6.1 Current policy-based allocation

Current implementation appears to use policy dict logic.

Example conceptual policy:

```python
policy = {
    "CN": ["MOM_ASIA", "MOM_EURO"],
    "JP": ["MOM_ASIA", "MOM_EURO"],
    "DE": ["MOM_EURO", "MOM_ASIA"],
    "DEFAULT": ["MOM_ASIA"],
}
```

Allocation flow:

```text
lot_id
    ↓
market_key
    ↓
policy candidate MOM list
    ↓
first available MOM
```

### 6.2 Future optimization-based allocation

In future, MOM allocation can become an optimization problem.

Possible objectives:

```text
maximize service level
maximize profit
minimize transport cost
balance MOM utilization
prioritize strategic markets
minimize delay
```

Possible constraints:

```text
MOM capacity
product capability
lane availability
leadtime
market demand priority
inventory availability
```

This future work should not be mixed into the Bridge A MVP.

---

## 7. Source and Target Buckets

### 7.1 Source

After Bridge A, the source for MOM allocation should be:

```python
inbound_supply_point.psi4demand[w][PSI_S]
```

or a semantically equivalent inbound demand buffer.

### 7.2 Target

The MOM allocation target should be:

```python
MOMxxx.psi4demand[w][PSI_S]
```

This means MOM receives the demand requirement as an S-side demand signal.

Inbound backward planning can then convert / propagate it into P and upstream needs.

---

## 8. Lot_ID Requirements

MOM allocation must operate on Lot_ID lists.

Correct:

```python
mom.psi4demand[w][PSI_S].append(lot_id)
```

Incorrect:

```python
mom.psi4demand[w][PSI_S].append(quantity)
mom.psi4demand[w][PSI_S] = len(lot_ids)
```

Lot identity must be preserved.

Allocation should optionally record allocation links:

```text
lot_id
source_node
assigned_mom
week
market_key
allocation_policy
allocation_reason
```

This will later support traceability, event generation, KPI evaluation, and Management Issue analysis.

---

## 9. Market Key Extraction

The current implementation extracts market key from `lot_id`.

Example:

```text
RT_JP_...
RT_DE_...
```

For Rice Case, this may not be sufficient.

Rice Case lot IDs may not contain market tokens in the same format.

Therefore, MVP should allow market key source to be configurable.

Possible sources:

```text
1. parse from lot_id
2. lookup from LotHeader.attributes["target_region"]
3. lookup from external lot metadata
4. fallback DEFAULT
```

### MVP recommendation

For now, keep current lot_id parsing behavior for compatibility.

Add design note:

```text
Rice Case may need LotHeader-based target_region extraction in future.
```

Do not implement broad metadata lookup in this MVP unless it is already available.

---

## 10. Allocation Input Policy

### 10.1 Source layer

The source should be inbound demand layer.

```text
layer = demand
bucket = S
```

### 10.2 Source node

Default source node:

```text
inbound supply_point
```

### 10.3 Target nodes

Target nodes:

```text
MOM_* nodes
```

### 10.4 Scope

MVP scope:

```text
single inbound tree
all MOM_* nodes under inbound tree
```

Future scope:

```text
selected MOM group
product-specific capability filtering
market-specific MOM policy
```

---

## 11. Proposed Wrapper Function

Existing `allocate_markets_to_moms(...)` may already perform most of this behavior.

However, for clarity, a wrapper may be useful.

Suggested function:

```python
def allocate_bridged_demand_to_moms(
    *,
    out_root,
    in_root,
    policy: dict,
    source_node_name: str = "supply_point",
    weeks: int | None = None,
    clear_existing_mom_demand: bool = True,
    debug: bool = False,
) -> MomAllocationBridgeResult:
    ...
```

This wrapper can call:

```python
allocate_markets_to_moms(
    out_root,
    in_root,
    policy=policy,
    source_layer="inbound_root_demand",
    weeks=weeks,
    clear_existing_mom_demand=clear_existing_mom_demand,
    debug=debug,
)
```

if that matches existing behavior.

Alternatively, if current `allocate_markets_to_moms(...)` already covers the use case directly, no wrapper is required.

---

## 12. Suggested Result Object

```python
@dataclass
class MomAllocationBridgeResult:
    source_node_name: str = "supply_point"
    allocated_lot_count: int = 0
    allocated_by_mom: dict[str, int] = field(default_factory=dict)
    unallocated_lot_ids: list[str] = field(default_factory=list)
    missing_mom_nodes: list[str] = field(default_factory=list)
    weeks_touched: list[int] = field(default_factory=list)
    policy_id: str = ""
```

This result is not required for MVP if `allocate_markets_to_moms(...)` does not currently return details, but it is useful for future traceability.

---

## 13. MVP Smoke Strategy

The MVP should prove the following sequence:

```text
1. outbound supply_point.psi4demand[w][P] contains known Lot_IDs
2. Bridge A copies those Lot_IDs to inbound supply_point.psi4demand[w][S]
3. MOM allocation assigns those Lot_IDs to MOMxxx.psi4demand[w][S]
4. source and target buckets remain Lot_ID lists
5. no numeric quantities are inserted
```

### Minimal test tree

```text
outbound:
    supply_point

inbound:
    supply_point
        ├── MOM_ASIA
        └── MOM_EURO
```

### Test lot IDs

Use lot IDs with market tokens if existing allocation uses lot_id parsing.

Example:

```text
RT_JP_RICE_2026W40_0001
RT_DE_RICE_2026W40_0002
```

### Test policy

```python
policy = {
    "JP": ["MOM_ASIA"],
    "DE": ["MOM_EURO"],
    "DEFAULT": ["MOM_ASIA"],
}
```

Expected result:

```text
JP lot → MOM_ASIA.psi4demand[w][S]
DE lot → MOM_EURO.psi4demand[w][S]
```

---

## 14. Safety Rules

### 14.1 Do not write to psi4supply

This integration remains in demand layer.

### 14.2 Do not run inbound backward planning

This step only tests bridge-to-MOM allocation.

### 14.3 Do not run capacity leveling

Capacity leveling comes after MOM allocation.

### 14.4 Do not run Forward Planning

Forward Planning comes later.

### 14.5 Preserve source

Outbound source and inbound supply_point demand bucket should remain understandable.

MVP may allow MOM allocation to clear existing MOM demand buckets if explicitly configured.

---

## 15. Tests

Suggested test file:

```text
tests/test_outbound_to_inbound_bridge_to_mom_allocation.py
```

Required tests:

```text
1. Bridge A copies outbound demand/P to inbound supply_point demand/S.
2. MOM allocation assigns JP lot to MOM_ASIA.
3. MOM allocation assigns DE lot to MOM_EURO.
4. Default policy handles unknown market.
5. PSI buckets contain Lot_ID strings only.
6. No psi4supply buckets are modified.
7. Existing Bridge A tests still pass.
```

Optional tests:

```text
8. clear_existing_mom_demand=True clears previous MOM demand.
9. clear_existing_mom_demand=False appends to existing MOM demand.
10. unallocated lot behavior if policy references missing MOM.
```

---

## 16. Current Implementation Questions

Before or during implementation, confirm:

```text
1. Does allocate_markets_to_moms(..., source_layer="inbound_root_demand") read in_root.psi4demand[w][S]?
2. Does it expect source_layer="outbound_supply" by default?
3. Does it clear MOM demand before allocation?
4. Does it return useful allocation summary?
5. Does it preserve source lot IDs?
```

If existing function behavior is enough, use it.

If not, create a small wrapper that adapts Bridge A output to the existing function.

---

## 17. Future Work

After this bridge-to-MOM allocation is validated:

```text
Bridge A
    ↓
MOM Allocation
```

the next step is:

```text
MOM Allocation
    ↓
Capacity-Aware Inbound Backward Planning
```

That next step should validate:

```text
MOM.psi4demand[w][S]
    ↓
level_mom_demand_with_capacity(...)
    ↓
MOM.psi4demand[w][P] feasibility
```

---

## 18. Summary

Bridge A alone connects outbound demand to inbound demand context.

The next required step is MOM allocation:

```text
outbound supply_point.psi4demand[w][P]
    ↓
Bridge A
    ↓
inbound supply_point.psi4demand[w][S]
    ↓
MOM allocation
    ↓
MOMxxx.psi4demand[w][S]
```

This is still demand-layer planning.

It does not execute supply.

It does not touch psi4supply.

It prepares the inbound demand tree for capacity-aware backward planning.
