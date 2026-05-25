# Codex Request: Implement WOM Outbound-to-Inbound Demand Bridge

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/wom_outbound_to_inbound_demand_bridge.md
```

Please read this design memo first.

The key concept is:

```text
Outbound-to-Inbound Demand Bridge
    =
    Bridge A
```

This bridge connects the E2E supply chain **in the demand layer**.

It should not directly create supply execution lots.

The conceptual target is:

```text
outbound supply_point.psi4demand[w][P]
    ↓
inbound demand context / inbound supply_point.psi4demand[w][S]
```

This is different from the later Demand-to-Supply Execution Bridge:

```text
finalized psi4demand
    ↓
psi4supply
```

---

## 2. Main Objective

Implement a small, safe, explicit **Outbound-to-Inbound Demand Bridge**.

The MVP should bridge Lot_IDs from:

```python
outbound_supply_point.psi4demand[w][P]
```

to:

```python
inbound_supply_point.psi4demand[w][S]
```

using V0R8 PSI semantics.

The bridge should operate on **Lot_ID lists**, not numeric quantities.

---

## 3. Critical WOM / PySI V0R8 Assumptions

Please preserve these assumptions.

### 3.1 Outbound and inbound PlanNodes are separate

Both outbound and inbound product trees may contain a node named:

```text
supply_point
```

However, they should be treated as separate PlanNode objects belonging to separate trees.

Do not assume they are the same Python object.

### 3.2 PSI bucket structure

The canonical V0R8 PSI structure is:

```python
node.psi4demand[w] = [S_ids, CO_ids, I_ids, P_ids]
node.psi4supply[w] = [S_ids, CO_ids, I_ids, P_ids]
```

Bucket index convention:

```python
PSI_S  = 0
PSI_CO = 1
PSI_I  = 2
PSI_P  = 3
```

### 3.3 PSI buckets must contain Lot_ID lists, not numeric quantities

Correct:

```python
node.psi4demand[w][PSI_S] = ["LOT_A", "LOT_B"]
```

Incorrect:

```python
node.psi4demand[w][PSI_S] = 2
```

Quantity remains:

```python
quantity = len(node.psi4demand[w][bucket])
```

---

## 4. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan.
3. Do not modify existing monthly loaders.
4. Do not run Backward Planning.
5. Do not run Forward Planning.
6. Do not implement Demand-to-Supply Execution Bridge.
7. Do not write to psi4supply in this request.
8. Do not create physical GUI nodes.
9. Do not create missing PlanNodes automatically.
10. Keep this as a safe additive bridge utility + tests.
```

This request is only for:

```text
outbound demand P
    ↓
inbound demand S
```

---

## 5. Suggested Files

Please add:

```text
pysi/plan/bridges/outbound_to_inbound_demand_bridge.py
tests/test_outbound_to_inbound_demand_bridge.py
```

Please add `__init__.py` only if needed:

```text
pysi/plan/bridges/__init__.py
```

Alternative location is acceptable if the repository has an existing bridge convention, but please keep the change additive and focused.

Do not modify:

```text
pysi/gui/*
run_full_plan
planning engines
existing loaders
```

---

## 6. Proposed Constants

Please define or reuse:

```python
PSI_BUCKET_INDEX = {
    "S": 0,
    "CO": 1,
    "I": 2,
    "P": 3,
}
```

---

## 7. Proposed Result Dataclass

Please implement:

```python
from dataclasses import dataclass, field


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

## 8. Proposed Main Function

Please implement:

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

---

## 9. Expected Behavior

### 9.1 Find source and target nodes

Find:

```text
source node:
    source_node_name in outbound_root tree

target node:
    target_node_name in inbound_root tree
```

MVP default:

```text
source_node_name = supply_point
target_node_name = supply_point
```

If source node is missing:

```text
result.missing_source_node = True
return safely
```

If target node is missing:

```text
result.missing_target_node = True
return safely
```

Do not create missing nodes.

---

### 9.2 Copy from outbound demand/P to inbound demand/S

Default MVP operation:

```text
source:
    outbound_supply_point.psi4demand[w][P]

target:
    inbound_supply_point.psi4demand[w][S]
```

The bridge should copy Lot_IDs, not quantities.

---

### 9.3 Week alignment

MVP default:

```text
bridge_leadtime_weeks = 0
```

So:

```text
target_week = source_week
```

Future-compatible behavior:

```text
target_week = source_week + bridge_leadtime_weeks
```

If target week is out of range:

```text
record invalid_weeks
skip that week
```

Do not extend PSI horizon silently.

---

### 9.4 Mode behavior

Please support at least:

```text
replace
append
dedupe_append
```

#### replace

```text
clear target bucket first
then copy source lots
```

#### append

```text
append source lots to target bucket
```

#### dedupe_append

```text
append only Lot_IDs not already present in target bucket
```

Default:

```text
replace
```

Reason:

A full recomputed bridge should be idempotent.

---

## 10. Safety Rules

### 10.1 Do not modify source

The outbound source bucket should remain unchanged.

### 10.2 Do not write to supply layer

This bridge must not write to:

```python
psi4supply
```

It should write only to:

```python
inbound_target.psi4demand[w][target_bucket]
```

### 10.3 Do not insert numeric quantities

Correct:

```python
target_bucket.extend(source_lot_ids)
```

Incorrect:

```python
target_bucket.append(len(source_lot_ids))
```

### 10.4 Preserve Lot_ID identity

The bridge should preserve original Lot_IDs.

Do not generate new Lot_IDs.

### 10.5 Validate buckets

If source or target bucket is not a list:

```text
record invalid week / bucket error
skip safely
```

---

## 11. Helper Functions

If useful, implement:

```python
def find_node_by_name(root, name: str):
    ...
```

or reuse an existing helper if available.

Also useful:

```python
def iter_nodes(root):
    ...
```

Keep implementation local and simple if no shared helper exists.

---

## 12. Test Plan

Please add:

```text
tests/test_outbound_to_inbound_demand_bridge.py
```

Required tests:

### 12.1 Basic bridge

Given:

```python
outbound_supply_point.psi4demand[0][P] = ["LOT_A", "LOT_B"]
```

After bridge:

```python
inbound_supply_point.psi4demand[0][S] == ["LOT_A", "LOT_B"]
```

### 12.2 Source not modified

Verify:

```python
outbound_supply_point.psi4demand[0][P] == ["LOT_A", "LOT_B"]
```

after bridge.

### 12.3 replace mode idempotent

Run bridge twice in `replace` mode.

Expected:

```python
inbound_supply_point.psi4demand[0][S] == ["LOT_A", "LOT_B"]
```

not duplicated.

### 12.4 append mode

If target already contains:

```python
["OLD_LOT"]
```

and source is:

```python
["LOT_A"]
```

then append mode should produce:

```python
["OLD_LOT", "LOT_A"]
```

### 12.5 dedupe_append mode

If target already contains `LOT_A`, source also has `LOT_A`, do not duplicate.

### 12.6 bridge_leadtime_weeks

Given:

```text
bridge_leadtime_weeks = 1
```

source week 0 should copy to target week 1.

### 12.7 missing source node

Should return result with:

```python
missing_source_node = True
```

### 12.8 missing target node

Should return result with:

```python
missing_target_node = True
```

### 12.9 no numeric quantity insertion

Verify all target bucket items are strings.

### 12.10 invalid bucket

Invalid bucket should raise `ValueError` or be handled deterministically.

Please document the chosen behavior in test.

---

## 13. Existing Tests to Run

Please run:

```bat
python -m pytest tests/test_outbound_to_inbound_demand_bridge.py
```

Also run:

```bat
python -m pytest tests/test_japanese_rice_backward_planning_after_seed.py
python -m pytest tests/test_japanese_rice_actual_prod_tree_seed_integration.py
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_plan_input_plan_node_seeding.py
```

Optional:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

If broader tests fail due to unrelated optional dependencies, report separately.

---

## 14. Completion Criteria

This request is complete when:

```text
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
[OK] no GUI / run_full_plan / loader / planning engine changes
```

---

## 15. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. Test commands executed
4. Test results
5. Any limitations or follow-up tasks
```

Please do not proceed into:

```text
MOM allocation
capacity-aware backward planning
demand-to-supply execution bridge
Forward Planning
with Capacity Forward PUSH
GUI integration
run_full_plan integration
```

This request is only for:

```text
Bridge A:
    Outbound-to-Inbound Demand Bridge
```