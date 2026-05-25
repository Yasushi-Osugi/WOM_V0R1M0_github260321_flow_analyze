# Codex Request: Implement WOM Demand-to-Supply Execution Bridge MVP

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/wom_demand_to_supply_execution_bridge.md
```

Please read this design memo first.

The current demand-layer planning flow has been progressively validated:

```text
Rice weekly input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
PlanNode.psi4demand seed
    ↓
Backward Planning smoke
    ↓
Bridge A: outbound-to-inbound demand bridge
    ↓
MOM allocation
    ↓
TOBE capacity-aware inbound backward planning
```

The next controlled step is **Bridge B**:

```text
finalized psi4demand
    ↓
psi4supply
```

This is the **Demand-to-Supply Execution Bridge**.

This request should implement a small, safe MVP bridge utility.

---

## 2. Main Objective

Implement a canonical MVP function that transfers finalized demand-side PSI lots into supply-side PSI lots.

MVP target:

```text
MOM subtree
    demand/S → supply/S
    demand/P → supply/P
    supply/CO = []
    supply/I  = []
```

Default behavior:

```text
bridge_policy = "s_p_only"
mode = "replace"
bridge_leadtime_weeks = 0
```

This should prepare `psi4supply` for later Forward Planning / PUSH / PULL / With Capacity Forward PUSH.

---

## 3. Critical WOM / PySI V0R8 Assumptions

Please preserve these assumptions.

### 3.1 PSI bucket structure

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

### 3.2 PSI buckets must contain Lot_ID lists, not numeric quantities

Correct:

```python
node.psi4supply[w][PSI_S] = ["LOT_A", "LOT_B"]
```

Incorrect:

```python
node.psi4supply[w][PSI_S] = 2
```

Quantity remains:

```python
quantity = len(node.psi4supply[w][bucket])
```

### 3.3 Lot attributes remain outside PSI buckets

PSI buckets contain only Lot_IDs.

Lot attributes belong in:

```text
LotHeader
lot_pool
metadata table
lot attribute dictionary
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
6. Do not implement With Capacity Forward PUSH.
7. Do not modify MOM allocation.
8. Do not modify capacity-aware backward planning.
9. Keep this as a safe additive bridge utility + focused tests.
```

This request is only for:

```text
finalized psi4demand
    ↓
psi4supply
```

---

## 5. Suggested Files

Please add:

```text
pysi/plan/bridges/demand_to_supply_execution_bridge.py
tests/test_demand_to_supply_execution_bridge.py
```

Please update only if useful:

```text
pysi/plan/bridges/__init__.py
```

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

## 8. Main Function

Please implement:

```python
def bridge_demand_to_supply_execution(
    *,
    root,
    bridge_policy: str = "s_p_only",
    mode: str = "replace",
    bridge_leadtime_weeks: int = 0,
) -> DemandToSupplyBridgeResult:
    ...
```

---

## 9. Bridge Policy

Please support at least:

```text
s_p_only
s_only
full_clone
```

### 9.1 s_p_only policy

MVP default.

For each node and week:

```python
psi4supply[w][S] = copy(psi4demand[w][S])
psi4supply[w][P] = copy(psi4demand[w][P])
psi4supply[w][CO] = []
psi4supply[w][I]  = []
```

This is the recommended conservative default.

### 9.2 s_only policy

For each node and week:

```python
psi4supply[w][S] = copy(psi4demand[w][S])
psi4supply[w][CO] = []
psi4supply[w][I]  = []
psi4supply[w][P]  = []
```

This resembles the current `bridge_inbound_demand_to_supply(root)` behavior.

### 9.3 full_clone policy

For each node and week:

```python
psi4supply[w][S]  = copy(psi4demand[w][S])
psi4supply[w][CO] = copy(psi4demand[w][CO])
psi4supply[w][I]  = copy(psi4demand[w][I])
psi4supply[w][P]  = copy(psi4demand[w][P])
```

This should not be the default, because CO/I may have different meanings between demand and supply layers.

---

## 10. Mode Behavior

Please support:

```text
replace
append
dedupe_append
```

### 10.1 replace

Default.

Clear target supply buckets according to bridge policy, then copy source lots.

This should be idempotent.

### 10.2 append

Append source lots to target supply bucket.

### 10.3 dedupe_append

Append only Lot_IDs not already present in target supply bucket.

---

## 11. Leadtime Handling

### 11.1 MVP default

```text
bridge_leadtime_weeks = 0
```

Meaning:

```text
source_week = target_week
```

### 11.2 Future-compatible behavior

If:

```text
bridge_leadtime_weeks = 1
```

then:

```text
demand week 0 → supply week 1
```

If target week is out of range:

```text
record invalid_weeks
skip that week
```

Do not extend PSI horizon silently.

---

## 12. Scope

The function should operate on a subtree root.

MVP target:

```text
MOM subtree
```

It should traverse:

```text
root and all descendants
```

Do not require full WOM environment.

---

## 13. Safety Rules

### 13.1 Do not modify demand source

The source `psi4demand` buckets must not be modified.

### 13.2 Do not insert numeric quantities

Correct:

```python
target_bucket[:] = list(source_bucket)
```

Incorrect:

```python
target_bucket.append(len(source_bucket))
```

### 13.3 Preserve Lot_ID identity

Lot_IDs should be copied exactly.

Do not generate new Lot_IDs.

### 13.4 Validate bucket structure

If a demand or supply bucket is not a list:

```text
record non_list_bucket_errors
skip safely
```

### 13.5 No planning execution

Do not call:

```text
PUSH_process
PULL_process
calcPS2I4supply
Backward Planning
Forward Planning
```

This bridge only seeds supply layer.

---

## 14. Helper Functions

If useful, implement local helpers:

```python
def iter_nodes(root):
    ...
```

This should traverse root and descendants.

---

## 15. Test Plan

Please add:

```text
tests/test_demand_to_supply_execution_bridge.py
```

Required tests:

### 15.1 s_p_only basic bridge

Given:

```python
node.psi4demand[0][S] = ["S_LOT"]
node.psi4demand[0][P] = ["P_LOT"]
```

After bridge:

```python
node.psi4supply[0][S] == ["S_LOT"]
node.psi4supply[0][P] == ["P_LOT"]
node.psi4supply[0][CO] == []
node.psi4supply[0][I] == []
```

### 15.2 source demand unchanged

Verify `psi4demand` remains unchanged.

### 15.3 replace mode idempotent

Run twice in replace mode.

Expected no duplicates.

### 15.4 append mode

Existing supply lots should remain and source lots should be appended.

### 15.5 dedupe_append mode

Existing identical Lot_IDs should not duplicate.

### 15.6 bridge_leadtime_weeks

With leadtime 1, demand week 0 should copy to supply week 1.

### 15.7 full_clone policy

Verify all S/CO/I/P buckets are copied.

### 15.8 s_only policy

Verify only S is copied.

### 15.9 non-list bucket error

If a target or source bucket is not list, record error.

### 15.10 no numeric quantities inserted

Verify all supply bucket contents are strings.

---

## 16. Existing Tests to Run

Please run:

```bat
python -m pytest tests/test_demand_to_supply_execution_bridge.py
```

Also run:

```bat
python -m pytest tests/test_outbound_to_inbound_bridge_to_mom_allocation.py
python -m pytest tests/test_outbound_to_inbound_demand_bridge.py
python -m pytest tests/test_japanese_rice_backward_planning_after_seed.py
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_plan_input_plan_node_seeding.py
```

Optional:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

---

## 17. Completion Criteria

This request is complete when:

```text
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
[OK] no GUI / run_full_plan / planning engine changes
```

---

## 18. Expected Response from Codex

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
Forward Planning
With Capacity Forward PUSH
MOM allocation
capacity-aware backward planning
GUI integration
run_full_plan integration
```

This request is only for:

```text
Bridge B:
    Demand-to-Supply Execution Bridge
```