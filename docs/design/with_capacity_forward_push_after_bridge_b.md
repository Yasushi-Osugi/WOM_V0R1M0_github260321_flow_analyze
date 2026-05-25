# With Capacity Forward PUSH after Bridge B Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-21  
**Status:** Design memo  
**Target path:** `docs/design/with_capacity_forward_push_after_bridge_b.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/e2e_demand_to_supply_bridge_flow_completion_overview.md`
- `docs/design/e2e_demand_to_supply_bridge_flow_smoke.md`
- `docs/design/e2e_demand_to_supply_bridge_flow_smoke_completion.md`
- `docs/design/wom_demand_to_supply_execution_bridge.md`
- `docs/design/demand_to_supply_execution_bridge_completion.md`
- `docs/design/capacity_aware_inbound_backward_planning_tobe.md`
- `docs/design/capacity_aware_inbound_backward_planning_tobe_completion.md`
- `docs/design/wom_capacity_input_granularity_adapter.md`
- `docs/design/capacity_provider_monthly_csv_adapter_v0r2.md`

---

## 1. Purpose

This memo defines the next planning stage after **Bridge B: Demand-to-Supply Execution Bridge**.

The completed bridge flow is:

```text
Bridge A
    ↓
MOM allocation
    ↓
TOBE capacity-aware inbound backward planning
    ↓
Bridge B
```

Bridge B creates a supply-side PSI seed:

```text
finalized psi4demand
    ↓
psi4supply
```

The next stage is:

```text
psi4supply
    ↓
Forward Supply Execution
    ↓
With Capacity Forward PUSH
```

This memo defines how WOM should position and design **With Capacity Forward PUSH after Bridge B**.

---

## 2. Current Completed Input State

After Bridge B, the supply-side PSI layer is explicitly seeded.

Default MVP policy:

```text
s_p_only:
    demand/S → supply/S
    demand/P → supply/P
    supply/CO = []
    supply/I  = []
```

Therefore, after Bridge B:

```text
node.psi4supply[w][S]
node.psi4supply[w][P]
```

contain Lot_ID lists derived from finalized demand-side PSI.

This supply-side seed is not yet forward-executed.

---

## 3. Position in the Overall Flow

The intended full flow is:

```text
[1] Demand input / seeding
    ↓
[2] Outbound backward planning
    ↓
[3] Bridge A: outbound demand → inbound demand
    ↓
[4] MOM allocation
    ↓
[5] TOBE capacity-aware inbound backward planning
    ↓
[6] Bridge B: finalized demand → supply seed
    ↓
[7] With Capacity Forward PUSH
    ↓
[8] Supply-side execution result
```

This memo focuses on step `[7]`.

---

## 4. Conceptual Meaning

### 4.1 Backward capacity vs forward capacity

Capacity-aware inbound backward planning answers:

```text
Can this demand be planned into feasible production weeks?
```

With Capacity Forward PUSH answers:

```text
Can the planned supply actually move through the supply network as an execution flow?
```

These are different questions.

```text
Backward capacity:
    plan feasibility

Forward capacity:
    execution feasibility
```

### 4.2 Why Bridge B is required first

Forward PUSH should operate on:

```text
psi4supply
```

not directly on:

```text
psi4demand
```

Bridge B therefore creates the explicit supply-side starting state.

---

## 5. Core Design Principle

The core principle is:

```text
Demand-side planning produces a feasible planned intent.
Bridge B converts that intent into supply-side PSI seed.
Forward PUSH simulates execution of that supply-side seed under capacity.
```

In short:

```text
Plan first.
Bridge second.
Execute third.
```

---

## 6. Supply-Side PSI Semantics after Bridge B

After Bridge B, the supply-side PSI buckets retain V0R8 semantics:

```python
node.psi4supply[w] = [S_ids, CO_ids, I_ids, P_ids]
```

where:

```text
S  = shipment / sales / supply outflow bucket
CO = confirmed order / carry-over style bucket
I  = inventory bucket
P  = production / purchase / supply inflow bucket
```

Bridge B does not calculate inventory or execution movement.

It only seeds:

```text
supply/S
supply/P
```

Forward PUSH should then interpret these supply-side lots and apply movement, consumption, and inventory logic.

---

## 7. Scope of With Capacity Forward PUSH MVP

### 7.1 In scope

The MVP should verify:

```text
1. psi4supply seed exists after Bridge B
2. Forward PUSH can consume supply/P and/or supply/S Lot_ID lists
3. Capacity constraints can block or accept lots
4. blocked lots preserve Lot_ID identity
5. accepted lots remain traceable
6. supply-side buckets remain list[str]
7. no numeric quantities are inserted
```

### 7.2 Out of scope

The MVP should not yet include:

```text
GUI integration
run_full_plan integration
costing / KPI integration
Management Issue generation
OR optimization
multi-echelon full execution
external event generation
```

---

## 8. Capacity Modeling after Bridge B

### 8.1 Capacity source

Forward capacity may come from:

```text
edge capacity
node capacity
lane capacity
transport capacity
warehouse capacity
MOM shipping capacity
```

For MVP, use a simple capacity source such as:

```text
weekly_capability[product][node_or_edge][week]
```

or existing forward-push-with-capacity test fixtures.

### 8.2 Difference from effective MOM capacity

Effective MOM capacity used in backward planning represents:

```text
production feasibility before execution
```

Forward capacity represents:

```text
execution throughput after the supply seed is created
```

They may have the same numeric value in a simple MVP, but conceptually they are different.

---

## 9. Existing Candidate Functions

Existing implementation candidates should be inspected before coding.

Likely candidates include:

```text
pysi/plan/engines.py
tests/test_covid_vaccine_with_capacity_push.py
tests/test_forward_push_with_capacity_planner.py
```

Possible function names to inspect:

```text
forward_push_with_capacity
with_capacity_forward_push
run_forward_push_with_capacity
PUSH_process
calcPS2I4supply
```

The exact current implementation should determine the first Codex Request.

---

## 10. Recommended MVP Strategy

Do not immediately wire into `run_full_plan`.

First implement a focused smoke:

```text
Bridge B output
    ↓
With Capacity Forward PUSH smoke
```

Suggested test:

```text
tests/test_with_capacity_forward_push_after_bridge_b.py
```

Suggested design target:

```text
pysi/plan/bridges/with_capacity_forward_push_after_bridge_b.py
```

or, if there is already a canonical forward planner module:

```text
pysi/plan/forward_push_with_capacity.py
```

---

## 11. Minimal Test Topology

Use a small supply-side tree.

Example:

```text
MOM_ASIA
    ↓
supply_point
```

or:

```text
source_node
    ↓
destination_node
```

For MVP, a single-node or two-node fixture is acceptable if it can demonstrate capacity blocking.

---

## 12. Minimal Supply Seed

After Bridge B, seed:

```python
node.psi4supply[10][P] = ["LOT_A", "LOT_B", "LOT_C"]
```

Capacity:

```text
week 10 capacity = 2
```

Expected:

```text
accepted lots = 2
blocked lots = 1
```

If the current forward planner supports carry-over or delayed execution:

```text
blocked lot may stay in source bucket
or move to blocked_lot_ids / result
```

But Lot_ID identity must be preserved.

---

## 13. Expected Result Object

A future wrapper may return:

```python
@dataclass
class WithCapacityForwardPushAfterBridgeBResult:
    product_name: str
    accepted_lot_count: int = 0
    blocked_lot_count: int = 0
    accepted_lot_ids: list[str] = field(default_factory=list)
    blocked_lot_ids: list[str] = field(default_factory=list)
    capacity_usage_by_node_week: dict = field(default_factory=dict)
    non_list_bucket_errors: list[dict] = field(default_factory=list)
    non_string_lot_errors: list[dict] = field(default_factory=list)
    message: str = ""
```

---

## 14. Safety Invariants

The MVP must preserve:

```text
1. psi4supply buckets remain lists.
2. bucket items remain Lot_ID strings.
3. no numeric quantity values are inserted.
4. accepted lots preserve Lot_ID identity.
5. blocked lots preserve Lot_ID identity.
6. Bridge B source demand is not modified by Forward PUSH.
7. no GUI / run_full_plan changes.
```

---

## 15. Relationship to E2E Bridge Smoke

The completed E2E bridge smoke verifies:

```text
Bridge A
    ↓
MOM allocation
    ↓
capacity-aware inbound backward planning
    ↓
Bridge B
```

The next smoke should append:

```text
Bridge B
    ↓
With Capacity Forward PUSH
```

Eventually:

```text
Bridge A
    ↓
MOM allocation
    ↓
capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
With Capacity Forward PUSH
```

can become a controlled E2E execution smoke.

---

## 16. Test Strategy

### 16.1 Focused test

Add a focused test that starts from an already seeded `psi4supply`.

Required assertions:

```text
1. supply seed exists
2. forward capacity process runs
3. accepted_lot_ids are correct
4. blocked_lot_ids are correct
5. Lot_ID identity is preserved
6. no numeric quantities are inserted
```

### 16.2 Integration test with Bridge B

Optional second test:

```text
demand/S/P
    ↓
Bridge B
    ↓
psi4supply/S/P
    ↓
With Capacity Forward PUSH
```

This confirms Bridge B output is compatible with the forward capacity process.

---

## 17. Open Questions Before Codex Request

Before implementation, inspect current forward capacity code and answer:

```text
1. Which function is the current canonical With Capacity Forward PUSH?
2. Does it consume psi4supply[P], psi4supply[S], or both?
3. Does it return accepted / blocked lots?
4. Where are blocked lots stored?
5. Does it mutate psi4supply buckets directly?
6. Does it preserve Lot_ID strings?
7. Does it use edge capacity, node capacity, or weekly_capability?
8. Can it be called without full GUI / run_full_plan context?
```

The Codex Request should be written after these are confirmed.

---

## 18. Recommended Next Step

The immediate next step is not broad implementation.

Recommended sequence:

```text
1. Add this design memo.
2. Inspect current forward-push-with-capacity code and tests.
3. Write a focused Codex Request for Bridge B → With Capacity Forward PUSH smoke.
4. Keep run_full_plan integration separate.
```

---

## 19. Summary

This memo defines the next phase after Bridge B.

The completed bridge flow produces:

```text
psi4supply
```

The next target is:

```text
psi4supply
    ↓
With Capacity Forward PUSH
```

The design principle is:

```text
Demand planning creates intent.
Bridge B seeds supply execution state.
Forward PUSH with Capacity tests execution feasibility.
```

This is the correct next layer after the completed E2E demand-to-supply bridge flow.
