# Codex Request: Implement E2E Bridge + Forward Capacity Smoke

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/e2e_bridge_forward_capacity_smoke.md
```

Please read this design memo first.

The current E2E demand-to-supply bridge flow has already been implemented and tested through:

```text
Bridge A
    ↓
MOM allocation
    ↓
TOBE capacity-aware inbound backward planning
    ↓
Bridge B
```

The next controlled smoke is:

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

This request should compose existing utilities and verify the first compact demand-to-supply-to-forward-capacity execution path.

---

## 2. Existing Components to Reuse

Please reuse existing modules. Do not duplicate logic.

```text
pysi/plan/bridges/outbound_to_inbound_demand_bridge.py
pysi/plan/bridges/outbound_to_inbound_mom_allocation.py
pysi/plan/capacity_aware_inbound_backward.py
pysi/plan/bridges/demand_to_supply_execution_bridge.py
pysi/plan/weekly_forward_push_with_capacity.py
```

Relevant existing functions:

```text
bridge_outbound_to_inbound_demand(...)
allocate_bridged_demand_to_moms(...)
capacity_aware_inbound_backward_planning(...)
bridge_demand_to_supply_execution(...)
weekly_forward_push_with_capacity(...)
```

---

## 3. Main Objective

Implement an additive E2E smoke wrapper and focused tests.

Target chain:

```text
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
capacity-aware inbound backward planning
    ↓
MOM.psi4demand[w][P]
    ↓
Bridge B
    ↓
MOM.psi4supply[w][S/P]
    ↓
Weekly Forward PUSH with Capacity
```

The smoke should prove that Lot_IDs can flow through the completed bridge chain and into the weekly capacity-aware forward execution layer.

---

## 4. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan.
3. Do not modify existing loaders.
4. Do not implement costing / KPI.
5. Do not implement Management Issue Generation.
6. Do not implement OR optimization.
7. Do not run any broad planner beyond the listed utilities.
8. Keep this as an additive smoke wrapper + focused tests.
```

This request is only for:

```text
E2E Bridge + Forward Capacity Smoke
```

---

## 5. Suggested Files

Please add:

```text
pysi/plan/bridges/e2e_bridge_forward_capacity_smoke.py
tests/test_e2e_bridge_forward_capacity_smoke.py
```

Please update only if useful:

```text
pysi/plan/bridges/__init__.py
```

Do not modify:

```text
pysi/gui/*
run_full_plan
existing loaders
costing / KPI modules
```

---

## 6. Result Dataclass

Please implement:

```python
from dataclasses import dataclass, field


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

## 7. Main Wrapper Function

Please implement:

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

Expected sequence:

```text
1. Run Bridge A.
2. Run MOM allocation.
3. Run TOBE capacity-aware inbound backward planning.
4. Run Bridge B.
5. Run Weekly Forward PUSH with Capacity.
6. Validate Lot_ID identity and PSI bucket invariants.
```

---

## 8. Minimal Test Topology

Use a minimal in-memory tree.

### 8.1 Outbound tree

```text
outbound supply_point
```

Seed source lots into:

```python
outbound_supply_point.psi4demand[10][P]
```

### 8.2 Inbound tree

```text
inbound supply_point
    ├── MOM_ASIA
    └── MOM_EURO
```

Each node should have:

```text
name
children
psi4demand
psi4supply
```

Use enough weeks to test early build, for example 12 or 16 weeks.

---

## 9. Minimal Lot Inputs

Use market-key-compatible Lot_IDs:

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

## 10. MOM Allocation Policy

Use:

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

## 11. Backward Capacity Scenario

Use a scenario that demonstrates early build.

```python
backward_weekly_capability = {
    "RICE": {
        "MOM_ASIA": [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 0],
        "MOM_EURO": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0],
    }
}
```

Interpretation:

```text
MOM_ASIA:
    week 10 capacity = 2
    week 9  capacity = 2

MOM_EURO:
    week 10 capacity = 2
```

Expected after capacity-aware inbound backward planning:

```text
MOM_ASIA:
    week 10 P bucket has 2 lots
    week 9 P bucket has 1 shifted lot

MOM_EURO:
    week 10 P bucket has 1 lot
```

---

## 12. Bridge B Expected Behavior

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

## 13. Forward Capacity Scenario

After Bridge B, run Weekly Forward PUSH with Capacity.

Use a forward supply capacity scenario that can demonstrate blocking and overflow.

Example:

```python
forward_weekly_capacity = {
    "RICE": {
        "MOM_ASIA": {
            "P": [999] * 12,
            "S": [999] * 12,
            "I": [999] * 12,
        },
        "MOM_EURO": {
            "P": [999] * 12,
            "S": [999] * 12,
            "I": [999] * 12,
        },
    }
}
```

For a forward P blocking test, set:

```text
MOM_ASIA P capacity at week 10 = 1
```

if `MOM_ASIA` has 2 P lots in week 10.

Expected:

```text
accepted_P = 1
blocked_P = 1
```

For S blocking:

```text
cap_S < requested S
```

For I overflow:

```text
cap_I < ending inventory
cap_i_mode = "soft"
```

---

## 14. Required Tests

Please add:

```text
tests/test_e2e_bridge_forward_capacity_smoke.py
```

### 14.1 Happy path with forward capacity

Verify the whole chain:

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

### 14.2 Bridge A result

Verify:

```text
outbound supply_point demand/P
    ↓
inbound supply_point demand/S
```

### 14.3 MOM allocation result

Verify:

```text
JP lots → MOM_ASIA demand/S
DE lot  → MOM_EURO demand/S
```

### 14.4 Capacity-aware early build result

Verify:

```text
MOM_ASIA week 10 P has 2 lots
MOM_ASIA week 9 P has 1 shifted lot
MOM_EURO week 10 P has 1 lot
```

### 14.5 Bridge B result

Verify:

```text
Bridge B maps finalized demand/S and demand/P into supply/S and supply/P.
```

### 14.6 Forward P capacity blocking

Set forward cap_P below requested P and verify:

```text
blocked_p_lot_ids contains expected Lot_ID
accepted_p_lot_ids contains expected Lot_IDs
```

### 14.7 Forward S capacity blocking

Set forward cap_S below requested S and verify:

```text
blocked_s_lot_ids contains expected Lot_ID
accepted_s_lot_ids contains expected Lot_IDs
```

### 14.8 I soft overflow

Set forward cap_I below ending inventory and verify:

```text
overflow_i_lot_ids contains expected Lot_ID
ending inventory remains unchanged in soft mode
```

### 14.9 Lot_ID preservation

Verify all original Lot_IDs are present in one of:

```text
final demand state
final supply state
blocked lots
overflow lots
backlog lots
```

### 14.10 PSI invariant

Verify:

```text
all psi4demand buckets are list[str]
all psi4supply buckets are list[str]
no numeric quantities are inserted
```

---

## 15. Existing Tests to Run

Please run:

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

If broader tests fail due to unrelated optional dependencies, report separately.

---

## 16. Safety Rules

Please enforce these invariants:

```text
1. PSI buckets hold Lot_ID lists.
2. Quantity is len(list).
3. Lot attributes remain outside PSI buckets.
4. Demand Anchored Lots do not disappear.
5. Shifted lots remain traceable.
6. Blocked lots preserve Lot_ID identity.
7. Overflow I lots preserve Lot_ID identity.
8. No numeric quantities are inserted.
9. No GUI / run_full_plan / loader changes.
```

---

## 17. Completion Criteria

This request is complete when:

```text
[OK] e2e_bridge_forward_capacity_smoke.py exists
[OK] E2E wrapper runs Bridge A → MOM allocation → capacity-aware backward → Bridge B → forward capacity
[OK] forward P capacity blocking is verified
[OK] forward S capacity blocking is verified
[OK] I soft overflow is verified
[OK] Lot_ID identity is preserved
[OK] psi4demand buckets remain list[str]
[OK] psi4supply buckets remain list[str]
[OK] no numeric quantities are inserted
[OK] no Forward Planning beyond weekly_forward_push_with_capacity is executed
[OK] focused tests pass
```

---

## 18. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Whether a wrapper function was added
3. Main implementation approach
4. How Bridge A / MOM allocation / capacity-aware backward / Bridge B / forward capacity were composed
5. How Lot_ID preservation was verified
6. How forward P/S blocking and I overflow were verified
7. Test commands executed
8. Test results
9. Limitations / follow-up
```

Do not proceed into:

```text
run_full_plan integration
GUI integration
costing / KPI
Management Issue Generation
OR optimization
database persistence
```

This request is only for:

```text
E2E Bridge + Forward Capacity Smoke
```