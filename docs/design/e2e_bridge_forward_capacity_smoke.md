# E2E Bridge + Forward Capacity Smoke Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-22  
**Status:** Design memo  
**Target path:** `docs/design/e2e_bridge_forward_capacity_smoke.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/e2e_demand_to_supply_bridge_flow_completion_overview.md`
- `docs/design/e2e_demand_to_supply_bridge_flow_smoke.md`
- `docs/design/e2e_demand_to_supply_bridge_flow_smoke_completion.md`
- `docs/design/wom_demand_to_supply_execution_bridge.md`
- `docs/design/demand_to_supply_execution_bridge_completion.md`
- `docs/design/weekly_forward_push_with_capacity_psi_engine.md`
- `docs/design/weekly_forward_push_with_capacity_psi_engine_completion.md`

---

## 1. Purpose

This memo defines the first controlled **E2E Bridge + Forward Capacity Smoke**.

The purpose is to verify that the explicit E2E demand-to-supply bridge flow can be connected to the new Weekly Forward PUSH with Capacity PSI Engine.

The target chain is:

```text
Bridge A
    ↓
MOM allocation
    ↓
TOBE capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
Weekly Forward PUSH with Capacity
```

This smoke should prove that a demand-side E2E plan can be transformed into a supply-side PSI seed and then executed under P / S / I capacity constraints.

This is still not `run_full_plan` integration.

---

## 2. Completed Components to Reuse

### 2.1 Bridge A

Implemented module:

```text
pysi/plan/bridges/outbound_to_inbound_demand_bridge.py
```

Main function:

```python
bridge_outbound_to_inbound_demand(...)
```

Purpose:

```text
outbound supply_point.psi4demand[w][P]
    ↓
inbound supply_point.psi4demand[w][S]
```

---

### 2.2 Bridge A to MOM allocation

Implemented module:

```text
pysi/plan/bridges/outbound_to_inbound_mom_allocation.py
```

Main helper:

```python
allocate_bridged_demand_to_moms(...)
```

Purpose:

```text
inbound supply_point.psi4demand[w][S]
    ↓
MOMxxx.psi4demand[w][S]
```

---

### 2.3 TOBE capacity-aware inbound backward planning

Implemented module:

```text
pysi/plan/capacity_aware_inbound_backward.py
```

Main function:

```python
capacity_aware_inbound_backward_planning(...)
```

Purpose:

```text
MOM.psi4demand[w][S]
    ↓
MOM.psi4demand[w][P]
    ↓
effective MOM capacity check
    ↓
early build / backlog
```

---

### 2.4 Bridge B

Implemented module:

```text
pysi/plan/bridges/demand_to_supply_execution_bridge.py
```

Main function:

```python
bridge_demand_to_supply_execution(...)
```

Purpose:

```text
finalized psi4demand
    ↓
psi4supply
```

Default policy:

```text
s_p_only:
    demand/S → supply/S
    demand/P → supply/P
    supply/CO = []
    supply/I  = []
```

---

### 2.5 Weekly Forward PUSH with Capacity

Implemented module:

```text
pysi/plan/weekly_forward_push_with_capacity.py
```

Main function:

```python
weekly_forward_push_with_capacity(...)
```

Purpose:

```text
psi4supply
    ↓
P / S / I capacity check
    ↓
accepted / blocked / overflow lots
```

---

## 3. Scope

### 3.1 In Scope

This smoke should verify:

```text
1. Bridge A runs.
2. MOM allocation runs.
3. capacity-aware inbound backward planning runs.
4. Bridge B runs.
5. Weekly Forward PUSH with Capacity runs.
6. P capacity blocks / accepts P lots.
7. S capacity blocks / accepts S lots.
8. I capacity detects overflow.
9. Lot_ID identity is preserved.
10. PSI buckets remain list[str].
11. No numeric quantities are inserted.
```

### 3.2 Out of Scope

This smoke should not:

```text
1. modify GUI
2. modify run_full_plan
3. refactor existing loaders
4. run costing / KPI
5. generate Management Issues
6. run OR optimization
7. perform full multi-echelon lane propagation
8. persist outputs to database
```

---

## 4. Recommended MVP Topology

Use a minimal inbound / outbound tree pair.

### 4.1 Outbound tree

```text
outbound supply_point
```

Seed source lots into:

```python
outbound_supply_point.psi4demand[10][P]
```

### 4.2 Inbound tree

```text
inbound supply_point
    ├── MOM_ASIA
    └── MOM_EURO
```

Each node must have:

```text
name
children
psi4demand
psi4supply
```

Use at least 12 weeks, or more if needed for shifting.

---

## 5. Minimal Lot Inputs

Use market-key-compatible Lot_IDs.

Example:

```text
RT_JP_RICE_2026W10_0001
RT_JP_RICE_2026W10_0002
RT_JP_RICE_2026W10_0003
RT_DE_RICE_2026W10_0001
```

Seed them into:

```python
outbound_supply_point.psi4demand[10][P]
```

---

## 6. MOM Allocation Policy

Use a simple policy:

```python
mom_policy = {
    "JP": ["MOM_ASIA"],
    "DE": ["MOM_EURO"],
    "DEFAULT": ["MOM_ASIA"],
}
```

Expected after MOM allocation:

```text
JP lots → MOM_ASIA.psi4demand[10][S]
DE lot  → MOM_EURO.psi4demand[10][S]
```

---

## 7. Effective MOM Capacity Scenario

Use a scenario that demonstrates early build.

Example:

```python
backward_weekly_capability = {
    "RICE": {
        "MOM_ASIA": [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 0],
        "MOM_EURO": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0],
    }
}
```

Expected after TOBE capacity-aware inbound backward planning:

```text
MOM_ASIA:
    week 10 P bucket has 2 lots
    week 9 P bucket has 1 shifted lot

MOM_EURO:
    week 10 P bucket has 1 lot
```

---

## 8. Bridge B Expected Output

After capacity-aware inbound backward planning, run Bridge B on the inbound tree.

```python
bridge_demand_to_supply_execution(
    root=inbound_root,
    bridge_policy="s_p_only",
    mode="replace",
)
```

Expected:

```text
demand/S → supply/S
demand/P → supply/P
supply/CO = []
supply/I  = []
```

---

## 9. Forward Capacity Scenario

After Bridge B, run Weekly Forward PUSH with Capacity.

Use a supply-side capacity scenario that demonstrates P / S / I capacity.

### 9.1 P capacity

For a capacity-blocking test, set:

```text
MOM_ASIA P capacity at week 10 = 1
```

if MOM_ASIA has 2 P lots in week 10.

Expected:

```text
accepted_P = 1
blocked_P = 1
```

### 9.2 S capacity

If supply/S has multiple lots, set:

```text
cap_S < requested S
```

to verify S blocking.

### 9.3 I capacity

Set:

```text
cap_I < ending inventory
```

to verify soft overflow.

---

## 10. Expected Result Object

Suggested wrapper result:

```python
@dataclass
class E2EBridgeForwardCapacitySmokeResult:
    bridge_a_lot_count: int = 0
    mom_allocated_lot_count: int = 0
    capacity_planned_lot_count: int = 0
    bridge_b_lot_count: int = 0

    forward_accepted_p_count: int = 0
    forward_blocked_p_count: int = 0
    forward_accepted_s_count: int = 0
    forward_blocked_s_count: int = 0
    forward_overflow_i_count: int = 0

    missing_lot_ids: list[str] = field(default_factory=list)
    blocked_lot_ids: list[str] = field(default_factory=list)
    overflow_i_lot_ids: list[str] = field(default_factory=list)

    non_list_bucket_errors: list[dict] = field(default_factory=list)
    non_string_lot_errors: list[dict] = field(default_factory=list)
    message: str = ""
```

---

## 11. Suggested Wrapper Function

Suggested function:

```python
def run_e2e_bridge_forward_capacity_smoke(
    *,
    outbound_root,
    inbound_root,
    product: str,
    mom_policy: dict,
    backward_weekly_capability: dict,
    forward_weekly_capacity: dict,
    bridge_a_mode: str = "replace",
    bridge_b_policy: str = "s_p_only",
    bridge_b_mode: str = "replace",
    max_early_build_weeks: int = 13,
    cap_i_mode: str = "soft",
    debug: bool = False,
) -> E2EBridgeForwardCapacitySmokeResult:
    ...
```

Flow:

```text
1. Bridge A
2. MOM allocation
3. TOBE capacity-aware inbound backward planning
4. Bridge B
5. Weekly Forward PUSH with Capacity
6. Validate Lot_ID identity and PSI invariants
```

---

## 12. Suggested File Location

Add:

```text
pysi/plan/bridges/e2e_bridge_forward_capacity_smoke.py
```

This is an integration smoke over bridge utilities.

---

## 13. Suggested Test File

Add:

```text
tests/test_e2e_bridge_forward_capacity_smoke.py
```

---

## 14. Required Tests

### 14.1 Happy path with no forward blocking

Verify:

```text
Bridge A runs.
MOM allocation runs.
Capacity-aware inbound backward planning runs.
Bridge B runs.
Forward capacity runs.
No Lot_ID disappears.
No numeric quantities are inserted.
```

### 14.2 Forward P capacity blocking

Set cap_P below requested P.

Verify:

```text
blocked_p_lot_ids contains expected Lot_ID
accepted_p_lot_ids contains expected Lot_IDs
```

### 14.3 Forward S capacity blocking

Set cap_S below requested S.

Verify:

```text
blocked_s_lot_ids contains expected Lot_ID
accepted_s_lot_ids contains expected Lot_IDs
```

### 14.4 I soft overflow

Set cap_I below ending inventory.

Verify:

```text
overflow_i_lot_ids contains expected Lot_ID
ending inventory remains unchanged in soft mode
```

### 14.5 Bridge B compatibility

Verify that Bridge B output is a valid input for Weekly Forward PUSH with Capacity.

### 14.6 No Forward Planning side effects beyond psi4supply

Verify the smoke does not run unrelated planning engines.

---

## 15. Existing Tests to Run

Run:

```bat
python -m pytest tests/test_e2e_bridge_forward_capacity_smoke.py
python -m pytest tests/test_weekly_forward_push_with_capacity.py
python -m pytest tests/test_e2e_demand_to_supply_bridge_flow_smoke.py
python -m pytest tests/test_demand_to_supply_execution_bridge.py
python -m pytest tests/test_capacity_aware_inbound_backward_planning.py
python -m pytest tests/test_japanese_rice_case_smoke.py
```

Optional:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

---

## 16. Completion Criteria

This smoke is complete when:

```text
[OK] Bridge A runs.
[OK] MOM allocation runs.
[OK] capacity-aware inbound backward planning runs.
[OK] Bridge B runs.
[OK] Weekly Forward PUSH with Capacity runs.
[OK] forward P capacity blocking is verified.
[OK] forward S capacity blocking is verified.
[OK] I soft overflow is verified.
[OK] Lot_ID identity is preserved.
[OK] psi4supply buckets remain list[str].
[OK] no numeric quantities are inserted.
[OK] no GUI / run_full_plan / loader changes.
```

---

## 17. Next Milestones

After this smoke, next milestones are:

```text
1. run_full_plan integration design
2. E2E capacity usage / violation reporting
3. ReplanCommand / Management Issue generation
4. GUI case load and execution
5. Cost / KPI integration
```

---

## 18. Summary

This smoke should prove the first full MVP path from demand-side E2E planning to supply-side capacity execution:

```text
Bridge A
    ↓
MOM allocation
    ↓
capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
Weekly Forward PUSH with Capacity
```

It is the first compact execution smoke after the bridge completion overview.

The core invariant remains:

```text
PSI buckets hold Lot_ID lists.
Quantity is len(list).
Capacity changes lot status, not lot identity.
```
