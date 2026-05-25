# Codex Request: Implement E2E Demand-to-Supply Bridge Flow Smoke

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/e2e_demand_to_supply_bridge_flow_smoke.md
```

Please read this design memo first.

The recent bridge / planning MVP work has completed the following independent utilities:

```text
Bridge A:
    pysi/plan/bridges/outbound_to_inbound_demand_bridge.py

Bridge A → MOM allocation:
    pysi/plan/bridges/outbound_to_inbound_mom_allocation.py

TOBE capacity-aware inbound backward planning:
    pysi/plan/capacity_aware_inbound_backward.py

Bridge B:
    pysi/plan/bridges/demand_to_supply_execution_bridge.py
```

This request is to implement a small focused smoke test and optional additive smoke wrapper that connects these utilities end-to-end:

```text
Bridge A
    ↓
MOM allocation
    ↓
TOBE capacity-aware inbound backward planning
    ↓
Bridge B
```

This is still not `run_full_plan` integration.

---

## 2. Main Objective

Implement a controlled E2E smoke that proves:

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
```

The smoke must preserve WOM / PySI V0R8 semantics:

```text
PSI buckets hold Lot_ID lists.
Quantity is len(list).
Lot attributes remain outside PSI buckets.
Demand Anchored Lots do not disappear.
```

---

## 3. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan.
3. Do not modify existing loaders.
4. Do not run Forward Planning.
5. Do not run With Capacity Forward PUSH.
6. Do not generate Management Issues.
7. Do not run costing / KPI evaluation.
8. Do not implement OR optimization.
9. Keep this as an additive smoke wrapper and focused tests.
```

This request is only for:

```text
Bridge A → MOM allocation → capacity-aware inbound backward planning → Bridge B
```

---

## 4. Files to Inspect

Please inspect these existing files before coding:

```text
docs/design/e2e_demand_to_supply_bridge_flow_smoke.md
docs/design/e2e_demand_to_supply_bridge_flow_completion_overview.md

pysi/plan/bridges/outbound_to_inbound_demand_bridge.py
pysi/plan/bridges/outbound_to_inbound_mom_allocation.py
pysi/plan/capacity_aware_inbound_backward.py
pysi/plan/bridges/demand_to_supply_execution_bridge.py
```

Also inspect existing focused tests:

```text
tests/test_outbound_to_inbound_demand_bridge.py
tests/test_outbound_to_inbound_bridge_to_mom_allocation.py
tests/test_capacity_aware_inbound_backward_planning.py
tests/test_demand_to_supply_execution_bridge.py
```

Reuse the lightweight test-node patterns already used there.

---

## 5. Suggested Files

Please add:

```text
pysi/plan/bridges/e2e_demand_to_supply_bridge_flow_smoke.py
tests/test_e2e_demand_to_supply_bridge_flow_smoke.py
```

If a wrapper is unnecessary, the test may directly compose existing utilities.  
However, a small additive wrapper is preferred if it improves readability.

Please update `pysi/plan/bridges/__init__.py` only if you add a public wrapper API.

---

## 6. Proposed Result Dataclass

If adding a wrapper, please implement:

```python
from dataclasses import dataclass, field


@dataclass
class E2EDemandToSupplyBridgeFlowSmokeResult:
    bridge_a_lot_count: int = 0
    mom_allocated_lot_count: int = 0
    capacity_planned_lot_count: int = 0
    shifted_lot_count: int = 0
    backlog_lot_count: int = 0
    bridge_b_lot_count: int = 0
    missing_lot_ids: list[str] = field(default_factory=list)
    non_list_bucket_errors: list[dict] = field(default_factory=list)
    non_string_lot_errors: list[dict] = field(default_factory=list)
    message: str = ""
```

---

## 7. Proposed Wrapper Function

If adding a wrapper, please implement:

```python
def run_e2e_demand_to_supply_bridge_flow_smoke(
    *,
    outbound_root,
    inbound_root,
    product: str,
    mom_policy: dict,
    weekly_capability: dict,
    source_node_name: str = "supply_point",
    target_node_name: str = "supply_point",
    bridge_a_mode: str = "replace",
    bridge_b_policy: str = "s_p_only",
    bridge_b_mode: str = "replace",
    max_early_build_weeks: int = 13,
    debug: bool = False,
) -> E2EDemandToSupplyBridgeFlowSmokeResult:
    ...
```

Conceptual implementation:

```text
1. Run Bridge A:
       outbound demand/P → inbound demand/S

2. Run MOM allocation:
       inbound supply_point demand/S → MOM demand/S

3. Run TOBE capacity-aware inbound backward planning:
       MOM demand/S → MOM demand/P with early build / backlog

4. Run Bridge B:
       finalized demand/S/P → supply/S/P

5. Validate Lot_ID preservation and bucket invariants.
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

Use enough weeks to test shifting, for example 12 or 16 weeks.

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

Expected Bridge A output:

```python
inbound_supply_point.psi4demand[10][S]
```

contains all four Lot_IDs.

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
DE lots → MOM_EURO.psi4demand[10][S]
```

---

## 11. Effective MOM Capacity Scenario

Use a scenario that demonstrates early build.

Example:

```python
weekly_capability = {
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

If three JP lots are assigned to `MOM_ASIA` in week 10:

```text
2 lots stay in week 10 P
1 lot shifts to week 9 P
```

The DE lot assigned to `MOM_EURO` should stay in week 10 P.

---

## 12. Expected Bridge B Output

After capacity-aware inbound backward planning, run Bridge B on the inbound tree:

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

Specifically:

```text
MOM_ASIA.psi4demand[10][P] → MOM_ASIA.psi4supply[10][P]
MOM_ASIA.psi4demand[9][P]  → MOM_ASIA.psi4supply[9][P]
MOM_EURO.psi4demand[10][P] → MOM_EURO.psi4supply[10][P]
```

---

## 13. Required Tests

Please add:

```text
tests/test_e2e_demand_to_supply_bridge_flow_smoke.py
```

Required tests:

### 13.1 Happy path

Verify the whole chain:

```text
Bridge A
    ↓
MOM allocation
    ↓
capacity-aware inbound backward planning
    ↓
Bridge B
```

### 13.2 Bridge A result

Verify:

```text
outbound supply_point demand/P
    ↓
inbound supply_point demand/S
```

### 13.3 MOM allocation result

Verify:

```text
JP lots → MOM_ASIA demand/S
DE lots → MOM_EURO demand/S
```

### 13.4 Capacity-aware early build result

Verify:

```text
MOM_ASIA week 10 P has 2 lots
MOM_ASIA week 9 P has 1 shifted lot
MOM_EURO week 10 P has 1 lot
```

### 13.5 Bridge B result

Verify supply buckets mirror finalized demand buckets according to `s_p_only`:

```text
supply/S == demand/S
supply/P == demand/P
supply/CO == []
supply/I == []
```

### 13.6 Lot_ID preservation

Verify all original Lot_IDs exist in the final demand/supply state or backlog records.

### 13.7 No numeric quantities

Verify all PSI bucket contents are strings.

### 13.8 No Forward Planning

The test should not call any forward execution function.

---

## 14. Optional Backlog Test

Add a second test if straightforward.

Capacity scenario:

```text
MOM_ASIA week 10 capacity = 1
MOM_ASIA week 9 capacity = 0
MOM_ASIA week 8 capacity = 0
JP demand at week 10 = 2 lots
```

Expected:

```text
1 lot stays in week 10 P
1 lot becomes backlog record
backlog record preserves Lot_ID
```

---

## 15. Safety Invariants

The smoke must verify:

```text
1. all psi4demand buckets remain list[str]
2. all psi4supply buckets remain list[str]
3. no numeric quantities are inserted
4. outbound source lots are not modified by Bridge A
5. Lot_ID identity is preserved through all stages
6. shifted lots remain traceable
7. backlog lots preserve Lot_ID identity if any
8. Forward Planning is not executed
```

---

## 16. Existing Tests to Run

Please run:

```bat
python -m pytest tests/test_e2e_demand_to_supply_bridge_flow_smoke.py
python -m pytest tests/test_demand_to_supply_execution_bridge.py
python -m pytest tests/test_outbound_to_inbound_bridge_to_mom_allocation.py
python -m pytest tests/test_outbound_to_inbound_demand_bridge.py
python -m pytest tests/test_capacity_aware_inbound_backward_planning.py
python -m pytest tests/test_japanese_rice_case_smoke.py
```

Optional:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

If broader tests fail due to unrelated optional dependencies, report separately.

---

## 17. Completion Criteria

This request is complete when:

```text
[OK] E2E smoke test exists
[OK] Bridge A runs
[OK] MOM allocation runs
[OK] capacity-aware inbound backward planning runs
[OK] Bridge B runs
[OK] Lot_ID identity is preserved
[OK] shifted lots are visible
[OK] optional backlog record preserves Lot_ID
[OK] psi4demand buckets remain list[str]
[OK] psi4supply buckets remain list[str]
[OK] no numeric quantities are inserted
[OK] no Forward Planning is executed
[OK] focused tests pass
[OK] no GUI / run_full_plan / loader changes
```

---

## 18. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Whether a wrapper function was added or test directly composed utilities
3. Main implementation approach
4. How Lot_ID preservation was verified
5. How early build / backlog was verified
6. Test commands executed
7. Test results
8. Limitations / follow-up
```

Do not proceed into:

```text
Forward Planning
With Capacity Forward PUSH
run_full_plan integration
GUI integration
costing / KPI
Management Issue Generation
OR optimization
```

This request is only for:

```text
E2E Demand-to-Supply Bridge Flow Smoke
```
