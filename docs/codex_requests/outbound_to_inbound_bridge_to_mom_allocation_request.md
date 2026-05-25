# Codex Request: Verify Outbound-to-Inbound Bridge to MOM Allocation

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/outbound_to_inbound_bridge_to_mom_allocation.md
```

Please read this design memo first.

The previous milestone implemented Bridge A:

```text
outbound supply_point.psi4demand[w][P]
    ↓
inbound supply_point.psi4demand[w][S]
```

using:

```text
pysi/plan/bridges/outbound_to_inbound_demand_bridge.py
```

This request is to verify and minimally support the next demand-layer step:

```text
Bridge A
    ↓
MOM Production Allocation
```

The target flow is:

```text
outbound supply_point.psi4demand[w][P]
    ↓
bridge_outbound_to_inbound_demand(...)
    ↓
inbound supply_point.psi4demand[w][S]
    ↓
allocate_markets_to_moms(...)
    ↓
MOMxxx.psi4demand[w][S]
```

This is still demand-layer planning.

Do not implement supply execution in this request.

---

## 2. Main Objective

Implement a small, safe smoke integration for:

```text
Outbound-to-Inbound Demand Bridge
    ↓
MOM Production Allocation
```

The goal is to prove that lots bridged from outbound demand/P into inbound demand/S can be allocated to MOM nodes by market policy.

The MVP should show:

```text
JP lot → MOM_ASIA.psi4demand[w][S]
DE lot → MOM_EURO.psi4demand[w][S]
unknown market lot → DEFAULT MOM
```

---

## 3. Important Conceptual Boundary

This request is still in the **demand layer**.

It should not touch:

```text
psi4supply
Forward Planning
Demand-to-Supply Execution Bridge
Capacity-Aware Backward Planning
Run Full Plan
GUI
```

This request only verifies:

```text
inbound supply_point.psi4demand[w][S]
    ↓
MOMxxx.psi4demand[w][S]
```

---

## 4. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan.
3. Do not run Backward Planning.
4. Do not run Forward Planning.
5. Do not implement Demand-to-Supply Execution Bridge.
6. Do not write to psi4supply.
7. Do not run capacity leveling.
8. Do not create physical GUI nodes.
9. Do not create missing MOM nodes automatically.
10. Keep this as a safe additive utility / wrapper / test.
```

This request is only for:

```text
Bridge A output
    ↓
MOM allocation smoke verification
```

---

## 5. Files to Inspect

Please inspect:

```text
docs/design/outbound_to_inbound_bridge_to_mom_allocation.md
pysi/plan/bridges/outbound_to_inbound_demand_bridge.py
pysi/plan/engines.py
```

Please find the existing function:

```python
allocate_markets_to_moms(...)
```

and confirm its current signature and behavior before coding.

---

## 6. Suggested Files

Add if needed:

```text
pysi/plan/bridges/outbound_to_inbound_mom_allocation.py
tests/test_outbound_to_inbound_bridge_to_mom_allocation.py
```

You may skip the new wrapper module if the existing `allocate_markets_to_moms(...)` can be used directly in tests.

If a wrapper is useful, keep it additive and focused.

Possible wrapper:

```python
def allocate_bridged_demand_to_moms(
    *,
    inbound_root,
    policy: dict,
    source_node_name: str = "supply_point",
    source_bucket: str = "S",
    target_bucket: str = "S",
    clear_existing_mom_demand: bool = True,
    debug: bool = False,
):
    ...
```

Do not modify existing engine behavior unless required for testability and backward compatibility.

---

## 7. Existing Bridge A Utility

Bridge A has already been implemented.

Use:

```python
from pysi.plan.bridges.outbound_to_inbound_demand_bridge import (
    bridge_outbound_to_inbound_demand,
)
```

Default Bridge A behavior:

```text
outbound supply_point.psi4demand[w][P]
    ↓
inbound supply_point.psi4demand[w][S]
```

The bridge must remain:

```text
Lot_ID list based
psi4supply untouched
source bucket unchanged
```

---

## 8. MOM Allocation Requirements

### 8.1 Source

MOM allocation should read bridged lots from:

```python
inbound_supply_point.psi4demand[w][PSI_S]
```

or an equivalent source defined by existing `allocate_markets_to_moms(...)`.

### 8.2 Target

MOM allocation should write to:

```python
MOMxxx.psi4demand[w][PSI_S]
```

### 8.3 Lot_ID preservation

The same Lot_ID should be preserved.

Correct:

```python
MOM_ASIA.psi4demand[w][S] = ["RT_JP_RICE_2026W40_0001"]
```

Incorrect:

```python
MOM_ASIA.psi4demand[w][S] = [1]
MOM_ASIA.psi4demand[w][S] = 1
```

---

## 9. Market Key Extraction

Use existing market-key extraction behavior if `allocate_markets_to_moms(...)` already provides it.

For the smoke test, use lot IDs that are compatible with market parsing.

Example lot IDs:

```text
RT_JP_RICE_2026W40_0001
RT_DE_RICE_2026W40_0002
RT_UNKNOWN_RICE_2026W40_0003
```

Policy example:

```python
policy = {
    "JP": ["MOM_ASIA"],
    "DE": ["MOM_EURO"],
    "DEFAULT": ["MOM_ASIA"],
}
```

Expected allocation:

```text
RT_JP...      → MOM_ASIA
RT_DE...      → MOM_EURO
RT_UNKNOWN... → MOM_ASIA
```

If existing market extraction uses a different convention, adapt the test lot IDs to the current implementation and document it in the test.

---

## 10. Minimal Test Tree

Use a minimal in-memory tree.

Conceptual structure:

```text
outbound:
    supply_point

inbound:
    supply_point
        ├── MOM_ASIA
        └── MOM_EURO
```

Each node should have:

```python
psi4demand[w] = [S_ids, CO_ids, I_ids, P_ids]
psi4supply[w] = [S_ids, CO_ids, I_ids, P_ids]
children
name
```

Use the same lightweight test node pattern used in existing tests if available.

---

## 11. Required Smoke Flow

The test should execute:

```python
bridge_outbound_to_inbound_demand(
    outbound_root=outbound_root,
    inbound_root=inbound_root,
    source_node_name="supply_point",
    target_node_name="supply_point",
    source_bucket="P",
    target_bucket="S",
    mode="replace",
)
```

Then execute existing or wrapper MOM allocation.

Expected sequence:

```text
outbound supply_point.psi4demand[0][P]
    contains JP / DE / UNKNOWN lots

Bridge A

inbound supply_point.psi4demand[0][S]
    contains the same lots

MOM allocation

MOM_ASIA.psi4demand[0][S]
    contains JP lot and UNKNOWN lot

MOM_EURO.psi4demand[0][S]
    contains DE lot
```

---

## 12. Required Tests

Please add:

```text
tests/test_outbound_to_inbound_bridge_to_mom_allocation.py
```

Required tests:

### 12.1 Bridge A to inbound supply_point

Verify:

```text
outbound demand/P
    ↓
inbound supply_point demand/S
```

### 12.2 JP lot allocation

Verify:

```text
JP lot → MOM_ASIA.psi4demand[w][S]
```

### 12.3 DE lot allocation

Verify:

```text
DE lot → MOM_EURO.psi4demand[w][S]
```

### 12.4 DEFAULT policy allocation

Verify unknown market lot goes to DEFAULT MOM.

### 12.5 Lot_ID list invariant

Verify all involved PSI buckets contain strings only.

### 12.6 No psi4supply mutation

Verify `psi4supply` remains unchanged for:

```text
outbound supply_point
inbound supply_point
MOM_ASIA
MOM_EURO
```

### 12.7 Existing Bridge A tests still pass

Run the existing Bridge A test.

---

## 13. Optional Tests

If easy and consistent with current implementation, add:

```text
1. clear_existing_mom_demand=True clears previous MOM demand before allocation.
2. clear_existing_mom_demand=False appends to existing MOM demand.
3. policy references missing MOM node and the lot is reported as unallocated.
```

Do not over-expand scope if these require changing existing engine behavior.

---

## 14. Existing Tests to Run

Please run:

```bat
python -m pytest tests/test_outbound_to_inbound_bridge_to_mom_allocation.py
python -m pytest tests/test_outbound_to_inbound_demand_bridge.py
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

## 15. Completion Criteria

This request is complete when:

```text
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
[OK] no GUI / run_full_plan / planning engine broad refactor
```

---

## 16. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Whether existing allocate_markets_to_moms was used directly or wrapped
3. Main implementation approach
4. Test commands executed
5. Test results
6. Any limitations or follow-up tasks
```

Please do not proceed into:

```text
capacity-aware backward planning
demand-to-supply execution bridge
forward planning
with Capacity Forward PUSH
GUI integration
run_full_plan integration
OR optimization
```

This request is only for:

```text
Bridge A
    ↓
MOM Production Allocation smoke verification
```