# WOM Demand-to-Supply Execution Bridge Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-20  
**Status:** Design memo  
**Target path:** `docs/design/wom_demand_to_supply_execution_bridge.md`

**Related design documents:**

- `docs/design/wom_demand_layer_bridge_and_supply_execution_bridge.md`
- `docs/design/wom_outbound_to_inbound_demand_bridge.md`
- `docs/design/current_wom_backward_planning_and_capacity_flow_mapping.md`
- `docs/design/rice_case_backward_planning_after_seed.md`
- `docs/design/rice_case_backward_planning_after_seed_completion.md`
- `docs/design/rice_case_actual_prod_tree_seed_integration.md`
- `docs/design/wom_plan_input_granularity_adapter_v0r3_plan_node_seeding.md`
- `docs/design/wom_capacity_input_granularity_adapter.md`
- `docs/design/capacity_provider_monthly_csv_adapter_v0r2.md`

---

## 1. Purpose

This memo defines the **Demand-to-Supply Execution Bridge** in WOM.

The purpose is to define how a finalized demand-side plan is transferred into supply-side execution simulation.

This is **Bridge B** in the two-bridge structure.

```text
Bridge A:
    Outbound-to-Inbound Demand Bridge
    outbound demand context → inbound demand context

Bridge B:
    Demand-to-Supply Execution Bridge
    finalized psi4demand → psi4supply
```

This memo focuses only on Bridge B.

Bridge B should run only after:

```text
Outbound-to-Inbound Demand Bridge
MOM Production Allocation
Capacity-Aware Backward Demand Planning
```

are complete.

---

## 2. Core Principle

The core principle is:

> Do not execute supply before demand allocation is finalized.

In WOM, `psi4demand` and `psi4supply` have different meanings.

```text
psi4demand:
    demand-side planning result
    where and when lots are required

psi4supply:
    supply-side execution simulation state
    how lots actually move through P / I / S under constraints
```

Therefore, Bridge B should be a controlled operation that moves a finalized demand-side plan into the supply-side simulation layer.

---

## 3. Position in Overall Planning Flow

The correct sequence is:

```text
[1] Plan Input Seed
    WeeklyPlanRow → LotHeader → PsiSeedRecord → PlanNode.psi4demand

[2] Outbound Backward Planning
    market leaf demand → DAD → outbound supply_point

[3] Outbound-to-Inbound Demand Bridge
    outbound supply_point.psi4demand[w][P]
        ↓
    inbound demand context

[4] MOM Production Allocation
    demand lots are assigned to MOM nodes

[5] Capacity-Aware Inbound Backward Planning
    MOM demand is propagated upstream with capacity constraints

[6] Demand-to-Supply Execution Bridge
    finalized psi4demand
        ↓
    psi4supply

[7] Forward Supply Execution
    psi4supply
        ↓
    PUSH / PULL / With Capacity Forward PUSH
```

Bridge B is step `[6]`.

---

## 4. Current Existing Bridge Candidates

The current WOM codebase already has several bridge-like functions.

### 4.1 `bridge_inbound_demand_to_supply(root)`

Conceptual behavior:

```text
node.psi4demand[w][S]
    ↓
node.psi4supply[w][S]
```

The implementation concept is a clean seed:

```python
node.psi4supply[w] = [demand_s, [], [], []]
```

This is a narrow bridge from demand S to supply S.

### 4.2 `copy_demand_to_supply_rec(node)`

This appears inside `inbound_backward_MOM_to_leaf(...)`.

Conceptual behavior:

```text
node.psi4demand
    ↓
node.psi4supply
```

This is broader than `bridge_inbound_demand_to_supply`.

It may clone all buckets.

### 4.3 `copy_S_demand2supply(node)`

Conceptual behavior:

```text
node.psi4demand[w][S]
    ↓
node.psi4supply[w][S]
```

### 4.4 `copy_P_demand2supply(node)`

Conceptual behavior:

```text
node.psi4demand[w][P]
    ↓
node.psi4supply[w][P]
```

### 4.5 PUSH / PULL functions

Existing functions such as:

```text
PUSH_process(...)
PULL_process(...)
push_pull_all_psi2i_decouple4supply5(...)
```

operate on supply-side PSI and may internally rely on demand-to-supply copying.

---

## 5. Need for Canonical Bridge Policy

Because multiple candidate functions exist, WOM should define a canonical Bridge B policy.

The canonical policy should answer:

```text
1. Which demand buckets are copied?
2. Which supply buckets are initialized?
3. Should bridge overwrite or append?
4. Should bridge operate on full tree or MOM subtrees?
5. Should bridge preserve CO / I / P?
6. Should bridge clean existing supply state?
7. Should bridge support leadtime?
8. Should bridge be idempotent?
```

---

## 6. Recommended MVP Policy

For the first canonical Bridge B, use a conservative policy.

### 6.1 Scope

Operate on:

```text
MOM subtree
```

rather than the entire inbound root.

Reason:

The existing implementation already warns that operating from inbound root / supply_point can cause the same demand to propagate into all MOM branches.

MOM subtree scope is safer.

### 6.2 Source layer

Source:

```text
PlanNode.psi4demand
```

### 6.3 Target layer

Target:

```text
PlanNode.psi4supply
```

### 6.4 Bucket policy

Recommended MVP bucket mapping:

```text
demand/S → supply/S
demand/P → supply/P
```

Leave CO and I empty initially unless explicitly required.

MVP bridge:

```python
psi4supply[w][S] = copy(psi4demand[w][S])
psi4supply[w][P] = copy(psi4demand[w][P])
psi4supply[w][CO] = []
psi4supply[w][I] = []
```

This gives Forward Planning enough seed information for:

```text
P / I / S execution simulation
```

without accidentally carrying demand-layer inventory or carry-over semantics into supply-layer state.

---

## 7. Alternative Policy: Full Demand Clone

A broader policy is:

```text
psi4supply = clone(psi4demand)
```

This may be useful when demand-side CO / I / P are already finalized and should be mirrored.

However, this is risky as a default.

Reason:

```text
CO and I may have different meanings in demand and supply layers.
```

Therefore, full clone should be a named policy:

```text
bridge_policy = "full_clone"
```

not the implicit default.

---

## 8. Overwrite vs Append

### 8.1 Recommended default

Bridge B should use:

```text
replace
```

when it creates a fresh supply-side simulation seed.

Reason:

```text
Forward Planning should start from a clean supply seed.
```

### 8.2 Alternative modes

Future bridge may support:

```text
append:
    add lots to existing supply bucket

dedupe_append:
    add only new lot IDs

replace:
    clear target bucket first, then copy source
```

### 8.3 MVP default

```text
mode = "replace"
```

---

## 9. Idempotency

A bridge operation should be idempotent when using replace mode.

If the same bridge runs twice:

```text
same input psi4demand
same target psi4supply
```

should be produced.

This helps avoid duplicate Lot_IDs.

---

## 10. Lot Operation

Bridge B must operate on Lot_ID lists.

Correct:

```python
target_bucket[:] = list(source_bucket)
```

or:

```python
target_bucket.extend(source_lots)
```

depending on bridge mode.

Incorrect:

```python
target_bucket = len(source_bucket)
target_bucket.append(quantity)
```

Lot_ID identity must be preserved.

---

## 11. Lead Time

### 11.1 MVP

Bridge B should use:

```text
bridge_leadtime_weeks = 0
```

This means:

```text
source_week = target_week
```

### 11.2 Future

Future bridge may support:

```text
target_week = source_week + bridge_leadtime_weeks
```

This should be explicit.

No hidden leadtime should be embedded in copying logic.

---

## 12. Proposed Function

Suggested function:

```python
def bridge_demand_to_supply_execution(
    *,
    root,
    scope: str = "subtree",
    bridge_policy: str = "s_p_only",
    mode: str = "replace",
    bridge_leadtime_weeks: int = 0,
) -> DemandToSupplyBridgeResult:
    ...
```

### 12.1 Parameters

```text
root:
    PlanNode subtree root

scope:
    subtree / full_tree

bridge_policy:
    s_p_only / s_only / full_clone

mode:
    replace / append / dedupe_append

bridge_leadtime_weeks:
    target week offset
```

---

## 13. Result Object

Suggested dataclass:

```python
@dataclass
class DemandToSupplyBridgeResult:
    root_node_name: str
    bridge_policy: str
    mode: str
    bridge_leadtime_weeks: int
    copied_lot_count: int = 0
    weeks_touched: list[int] = field(default_factory=list)
    nodes_touched: list[str] = field(default_factory=list)
    invalid_weeks: list[dict] = field(default_factory=list)
    non_list_bucket_errors: list[dict] = field(default_factory=list)
    duplicate_lot_ids: list[str] = field(default_factory=list)
```

---

## 14. Suggested MVP Implementation

For MVP:

```text
root:
    MOM subtree root

bridge_policy:
    s_p_only

mode:
    replace

bridge_leadtime_weeks:
    0
```

Behavior:

```python
for node in subtree:
    for w in weeks:
        supply[w][S] = list(demand[w][S])
        supply[w][CO] = []
        supply[w][I] = []
        supply[w][P] = list(demand[w][P])
```

This is conservative and explicit.

---

## 15. Relationship to Existing Functions

### 15.1 `bridge_inbound_demand_to_supply`

This current function resembles:

```text
bridge_policy = "s_only"
mode = "replace"
scope = "full_tree or subtree"
```

It copies demand S into supply S.

### 15.2 `copy_demand_to_supply_rec`

This resembles:

```text
bridge_policy = "full_clone"
mode = "replace"
scope = "subtree"
```

### 15.3 `copy_S_demand2supply` and `copy_P_demand2supply`

These resemble:

```text
bucket-specific copy helpers
```

### 15.4 Recommended treatment

Do not delete existing functions.

Instead:

```text
1. document them as bridge policy variants
2. implement canonical wrapper or new function
3. gradually route future calls through canonical function
```

---

## 16. Test Strategy

### 16.1 Test file

Suggested test:

```text
tests/test_demand_to_supply_execution_bridge.py
```

### 16.2 Required tests

```text
1. demand/S copies to supply/S.
2. demand/P copies to supply/P.
3. supply/CO and supply/I are cleared in s_p_only policy.
4. replace mode is idempotent.
5. source demand buckets are not modified.
6. PSI buckets remain Lot_ID lists.
7. no numeric quantities are inserted.
8. bridge_leadtime_weeks = 1 shifts target week.
9. full_clone policy copies all buckets.
10. dedupe_append avoids duplicate lot IDs.
```

---

## 17. Placement in Run Full Plan

Bridge B should be placed after:

```text
MOM Production Allocation
Capacity-Aware Backward Demand Planning
Inbound Backward Planning
```

and before:

```text
Forward Supply Execution
With Capacity Forward PUSH
```

Conceptual placement:

```text
inbound_backward_MOM_to_leaf
level_mom_demand_with_capacity
    ↓
bridge_demand_to_supply_execution
    ↓
inbound_forward_leaf_to_MOM / push_pull / with Capacity Forward PUSH
```

Exact Run Full Plan integration should be done only after the canonical bridge is tested.

---

## 18. Out of Scope

This memo does not implement:

```text
Outbound-to-Inbound Demand Bridge
MOM Allocation
Capacity-Aware Backward Planning
Forward PUSH with Capacity
GUI integration
run_full_plan refactor
cost / KPI evaluation
Management Issue Generation
```

---

## 19. Completion Criteria

The bridge design is complete when:

```text
[OK] Bridge B is clearly separated from Bridge A.
[OK] source and target layers are defined.
[OK] bucket mapping is defined.
[OK] replace / append / full_clone policies are defined.
[OK] existing bridge candidates are mapped.
[OK] MVP implementation policy is clear.
[OK] test plan is clear.
```

---

## 20. Summary

Demand-to-Supply Execution Bridge is the point where finalized demand-side planning becomes supply-side execution simulation.

It should happen only after:

```text
Outbound-to-Inbound Demand Bridge
MOM Production Allocation
Capacity-Aware Backward Demand Planning
```

are complete.

The recommended MVP is:

```text
MOM subtree
    demand/S → supply/S
    demand/P → supply/P
    supply/CO = []
    supply/I  = []
```

with:

```text
mode = replace
bridge_leadtime_weeks = 0
```

This preserves V0R8 PSI semantics while preparing the supply layer for Forward Planning and future With Capacity Forward PUSH.
