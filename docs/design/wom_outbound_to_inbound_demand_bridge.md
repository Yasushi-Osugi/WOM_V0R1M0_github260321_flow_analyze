# WOM Outbound-to-Inbound Demand Bridge Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-20  
**Status:** Design memo  
**Target path:** `docs/design/wom_outbound_to_inbound_demand_bridge.md`

**Related design documents:**

- `docs/design/wom_demand_layer_bridge_and_supply_execution_bridge.md`
- `docs/design/current_wom_backward_planning_and_capacity_flow_mapping.md`
- `docs/design/rice_case_backward_planning_after_seed.md`
- `docs/design/rice_case_backward_planning_after_seed_completion.md`
- `docs/design/wom_plan_input_granularity_adapter_v0r3_plan_node_seeding.md`
- `docs/design/wom_capacity_input_granularity_adapter.md`
- `docs/design/capacity_provider_monthly_csv_adapter_v0r2.md`

---

## 1. Purpose

This memo defines the **Outbound-to-Inbound Demand Bridge** in WOM.

The purpose is to clarify how demand lots accumulated on the outbound side are handed over to the inbound side **as demand-layer planning lots**, not as immediate supply execution lots.

The key principle is:

```text
E2E supply chain connection should first happen in the demand layer.
Supply execution should start only after MOM allocation and capacity-aware backward planning are completed.
```

This memo focuses on Bridge A in the bridge structure:

```text
Bridge A:
    Outbound-to-Inbound Demand Bridge

Bridge B:
    Demand-to-Supply Execution Bridge
```

---

## 2. Core Idea

The Outbound-to-Inbound Demand Bridge connects:

```text
outbound supply_point.psi4demand[w][P]
    ↓
inbound demand context
```

The bridge should **not** directly connect outbound demand to inbound `psi4supply`.

Correct conceptual flow:

```text
outbound supply_point.psi4demand[w][P]
    ↓
inbound supply_point.psi4demand[w][S]
    or MOM allocation input
```

Incorrect conceptual flow for this stage:

```text
outbound supply_point.psi4demand[w][P]
    ↓
inbound supply_point.psi4supply[w][S]
```

The latter skips MOM allocation and capacity-aware backward planning, so it should not be used as the first E2E connection.

---

## 3. Position in the Overall Planning Flow

The bridge sits between outbound backward planning and inbound MOM allocation.

```text
[1] Plan input seed
    Demand lots are seeded into psi4demand.

[2] Outbound Backward Planning
    leaf demand
        ↓
    DAD nodes
        ↓
    outbound supply_point

[3] Outbound-to-Inbound Demand Bridge
    outbound supply_point demand P
        ↓
    inbound demand context

[4] MOM Production Allocation
    demand lots are assigned to MOM nodes

[5] Capacity-Aware Inbound Backward Planning
    MOM demand is propagated upstream with capacity constraints

[6] Demand-to-Supply Execution Bridge
    finalized psi4demand is copied / bridged to psi4supply

[7] Forward Supply Execution
    supply-side PSI simulation runs on psi4supply
```

---

## 4. Why This Bridge Is Demand-Layer First

Outbound backward planning answers:

```text
What finished-product requirement is needed at the E2E supply point?
```

Inbound backward planning answers:

```text
Which MOM / upstream / material / process nodes must satisfy that requirement?
```

Therefore, the outbound-to-inbound connection must first transfer the requirement into the inbound **demand planning context**.

If the lots are moved directly into `psi4supply`, WOM would treat them as already executable supply lots. That would bypass:

- MOM production allocation
- MOM capacity feasibility check
- advance production / week shifting
- inbound material demand allocation

This would make the plan appear executable too early.

---

## 5. Current WOM Implementation Candidates

The current codebase contains several relevant functions.

### 5.1 `outbound_backward_leaf_to_MOM(...)`

This function performs outbound-side backward planning.

Conceptual behavior:

```text
leaf demand
    ↓
DAD demand
    ↓
outbound supply_point demand
```

The function walks the outbound tree in postorder and applies child-to-parent aggregation and S-to-P calculation.

### 5.2 `connect_outbound2inbound(...)`

This is the current candidate for Bridge A.

It is called inside:

```python
inbound_backward_MOM_to_leaf(...)
```

Conceptual role:

```text
outbound demand context
    ↓
inbound demand context
```

The exact bucket-level behavior should be treated as an implementation detail to verify in tests.

### 5.3 `allocate_markets_to_moms(...)`

This is the current MOM allocation step.

Conceptual behavior:

```text
source lots
    ↓
market key extraction
    ↓
policy-based MOM assignment
    ↓
MOM.psi4demand[w][S]
```

### 5.4 `inbound_backward_MOM_to_leaf(...)`

This function performs inbound backward planning by MOM subtree after outbound-to-inbound connection and optional MOM allocation.

Important design detail:

```text
MOM subtree planning avoids propagating identical demand into all MOM branches.
```

---

## 6. Source and Target Buckets

### 6.1 Source

The default source should be:

```python
outbound_supply_point.psi4demand[w][PSI_P]
```

This represents outbound-side requirement after backward planning.

### 6.2 Target

The recommended MVP target is demand-side:

```python
inbound_supply_point.psi4demand[w][PSI_S]
```

or an equivalent MOM allocation input.

### 6.3 Do not target supply layer

The bridge should not write directly to:

```python
inbound_supply_point.psi4supply[w][PSI_S]
```

at this stage.

That belongs to the later Demand-to-Supply Execution Bridge.

---

## 7. Week Alignment

### 7.1 MVP rule

For the MVP, bridge with zero lead time.

```text
bridge_leadtime_weeks = 0
```

So:

```text
target_week = source_week
```

Example:

```text
outbound supply_point.psi4demand[W][P]
    ↓
inbound supply_point.psi4demand[W][S]
```

### 7.2 Future extension

Later, the bridge may support lead time:

```text
target_week = source_week + bridge_leadtime_weeks
```

Examples:

```text
LT = 0:
    W → W

LT = 1:
    W → W+1
```

Bridge lead time should be explicit, not hidden inside copy logic.

---

## 8. Lot Operation

### 8.1 Correct operation

The bridge operates on Lot_ID lists.

```python
target_bucket.extend(source_lot_ids)
```

### 8.2 Incorrect operations

Do not insert numeric quantities.

```python
target_bucket.append(len(source_lot_ids))  # wrong
target_bucket = len(source_lot_ids)        # wrong
```

### 8.3 Lot identity

The bridge should preserve Lot_ID identity.

Do not generate new Lot_IDs in Bridge A.

If future transformations require new lot identity, they should be handled by a separate transformation layer and recorded as lot lineage.

---

## 9. Copy vs Move Semantics

Bridge A should be defined as a **planning copy / handoff**, not physical movement.

### 9.1 Recommended MVP behavior

Use copy semantics:

```text
source outbound demand lots remain in outbound tree
target inbound demand receives copied lot IDs
```

Reason:

The outbound tree remains the record of market-side demand planning.

The inbound tree receives the same demand requirement for production / procurement planning.

### 9.2 Future lineage

Future versions may record bridge lineage:

```text
source_lot_id
target_lot_id or same_lot_id
source_node
target_node
source_week
target_week
bridge_type
```

MVP can preserve the same Lot_ID.

---

## 10. Overwrite vs Append

### 10.1 Recommended behavior

Append is safer for incremental bridge operations.

```python
target_bucket.extend(source_lot_ids)
```

### 10.2 Duplicate risk

If bridge is run multiple times, duplicate lot IDs may appear.

Therefore, the bridge should support one of the following policies:

```text
append:
    simply append lot IDs

replace:
    clear target bucket then copy

dedupe_append:
    append only if lot_id not already present
```

### 10.3 MVP recommendation

For deterministic smoke tests, use:

```text
replace
```

or:

```text
dedupe_append
```

The exact policy should be configurable.

Suggested default:

```text
replace
```

when bridging a full recomputed plan.

Suggested future mode:

```text
dedupe_append
```

for incremental planning.

---

## 11. Scope: supply_point vs MOM Allocation Input

There are two possible targets.

### 11.1 Target A: inbound supply_point demand S

```text
outbound supply_point.psi4demand[w][P]
    ↓
inbound supply_point.psi4demand[w][S]
```

Then MOM allocation reads from inbound supply_point.

### 11.2 Target B: MOM allocation input directly

```text
outbound supply_point.psi4demand[w][P]
    ↓
allocate_markets_to_moms(...)
    ↓
MOM.psi4demand[w][S]
```

### 11.3 Recommended MVP

Use the existing current implementation path first.

If `connect_outbound2inbound(...)` already feeds `allocate_markets_to_moms(...)`, preserve that structure.

The design principle is:

```text
Bridge A should feed the inbound demand planning context.
MOM allocation should remain a separate step.
```

---

## 12. Relationship to MOM Allocation

After Bridge A, MOM allocation determines which MOM should satisfy each demand lot.

Current function candidate:

```python
allocate_markets_to_moms(...)
```

Current behavior is policy-based.

Future direction:

```text
OR optimization may replace or extend policy-based allocation.
```

MOM allocation should remain separate from Bridge A.

Bridge A should not decide the optimal MOM.

---

## 13. Relationship to Capacity-Aware Backward Planning

After MOM allocation, inbound backward planning and capacity leveling run.

Relevant functions:

```text
inbound_backward_MOM_to_leaf(...)
level_mom_demand_with_capacity(...)
inbound_MOM_leveling_vs_capacity(...)
```

Capacity-aware backward planning may perform:

```text
advance production
week shifting
capacity feasibility
overflow / backlog handling
```

Bridge A should not perform capacity leveling itself.

---

## 14. Relationship to Demand-to-Supply Execution Bridge

Demand-to-Supply Execution Bridge is Bridge B.

It happens after demand-side planning is finalized.

```text
finalized psi4demand
    ↓
psi4supply
```

Existing candidate functions:

```text
bridge_inbound_demand_to_supply(...)
copy_demand_to_supply_rec(...)
copy_S_demand2supply(...)
copy_P_demand2supply(...)
```

Bridge A should not perform Bridge B's responsibility.

---

## 15. Proposed Bridge A Function

Suggested future function:

```python
def bridge_outbound_to_inbound_demand(
    *,
    outbound_root,
    inbound_root,
    source_node_name: str = "supply_point",
    target_node_name: str = "supply_point",
    source_bucket: str = "P",
    target_bucket: str = "S",
    layer: str = "demand",
    bridge_leadtime_weeks: int = 0,
    mode: str = "replace",
) -> OutboundInboundDemandBridgeResult:
    ...
```

### 15.1 Function behavior

Expected behavior:

```text
1. find source node in outbound planning tree
2. find target node in inbound planning tree
3. for each week:
       read source psi4demand[w][P]
       compute target week
       write to target psi4demand[target_w][S]
4. preserve Lot_ID list
5. return structured result
```

### 15.2 Result object

Suggested dataclass:

```python
@dataclass
class OutboundInboundDemandBridgeResult:
    source_node_name: str
    target_node_name: str
    bridge_leadtime_weeks: int
    copied_lot_count: int = 0
    weeks_touched: list[str] = field(default_factory=list)
    missing_source_node: bool = False
    missing_target_node: bool = False
    invalid_weeks: list[dict] = field(default_factory=list)
    duplicate_lot_ids: list[str] = field(default_factory=list)
    mode: str = "replace"
```

---

## 16. Safety Invariants

Bridge A must preserve:

```text
1. source bucket remains list[str]
2. target bucket remains list[str]
3. no numeric quantities are inserted
4. Lot_IDs are preserved
5. target week is within range
6. no physical GUI nodes are touched
7. no supply layer mutation occurs
```

---

## 17. Tests

Suggested test file:

```text
tests/test_outbound_to_inbound_demand_bridge.py
```

Required tests:

```text
1. outbound supply_point demand/P copies to inbound supply_point demand/S.
2. Lot_ID identity is preserved.
3. Target bucket is list[str].
4. Source bucket is not destroyed.
5. bridge_leadtime_weeks = 0 keeps same week.
6. bridge_leadtime_weeks = 1 shifts target week by one.
7. replace mode clears target before copy.
8. dedupe_append mode avoids duplicate Lot_IDs.
9. missing source node is reported.
10. missing target node is reported.
```

---

## 18. Current Implementation Mapping

Current candidates:

```text
connect_outbound2inbound(...)
allocate_markets_to_moms(...)
inbound_backward_MOM_to_leaf(...)
```

The first implementation should decide whether to:

```text
A. wrap existing connect_outbound2inbound(...)
B. create a new explicit bridge_outbound_to_inbound_demand(...)
C. document connect_outbound2inbound as the canonical Bridge A
```

Recommended approach:

```text
Start with tests around current connect_outbound2inbound behavior.
If behavior is unclear or too broad, implement a new explicit bridge function.
```

---

## 19. Out of Scope

This Bridge A design does not implement:

```text
MOM allocation optimization
capacity leveling
demand-to-supply execution bridge
Forward PUSH
with Capacity Forward PUSH
ROI evaluation
GUI integration
```

---

## 20. Summary

The Outbound-to-Inbound Demand Bridge is the first E2E bridge in WOM planning.

It connects:

```text
outbound supply_point.psi4demand[w][P]
```

to:

```text
inbound demand context
```

not directly to supply execution.

The key principle is:

```text
Bridge demand first.
Allocate MOM and apply capacity-aware backward planning next.
Only then bridge demand to supply execution.
```

This separation keeps WOM's E2E planning structure clear and prevents outbound-inbound connection, MOM allocation, capacity leveling, and forward execution from becoming tangled.
