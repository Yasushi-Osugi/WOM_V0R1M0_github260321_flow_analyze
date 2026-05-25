# Codex Request: Implement Weekly Forward PUSH with Capacity PSI Engine MVP

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/weekly_forward_push_with_capacity_psi_engine.md
```

Please read this design memo first.

The current E2E demand-to-supply bridge flow is already implemented and tested up to Bridge B:

```text
Bridge A
    ↓
MOM allocation
    ↓
TOBE capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
psi4supply seed
```

Bridge B creates supply-side PSI seed data:

```text
finalized psi4demand
    ↓
psi4supply
```

This request is to implement the next MVP layer:

```text
psi4supply
    ↓
Weekly Forward PUSH with Capacity
```

The implementation should translate the monthly PSI with capacity concept into WOM's weekly, multi-node, Lot_ID-list-based PSI model.

---

## 2. Main Objective

Implement a small, safe **Weekly Forward PUSH with Capacity PSI Engine MVP**.

The MVP should operate on `psi4supply` and apply:

```text
cap_P
cap_S
cap_I
```

to weekly PSI buckets.

The core flow is:

```text
psi4supply[w][P]
    ↓
cap_P accept / block

available supply
    ↓
psi4supply[w][S]
    ↓
cap_S accept / block

ending inventory
    ↓
cap_I overflow check
```

The MVP should preserve WOM / PySI V0R8 PSI semantics:

```text
PSI buckets hold Lot_ID lists.
Quantity is len(list).
Lot attributes live outside PSI buckets.
Capacity changes lot status, not lot identity.
```

---

## 3. Critical WOM / PySI V0R8 Assumptions

Please preserve these assumptions.

### 3.1 PSI bucket structure

The canonical V0R8 PSI structure is:

```python
node.psi4supply[w] = [S_ids, CO_ids, I_ids, P_ids]
```

Bucket index convention:

```python
PSI_S  = 0
PSI_CO = 1
PSI_I  = 2
PSI_P  = 3
```

### 3.2 PSI buckets contain Lot_ID lists, not numeric quantities

Correct:

```python
node.psi4supply[w][PSI_P] = ["LOT_A", "LOT_B"]
```

Incorrect:

```python
node.psi4supply[w][PSI_P] = 2
```

Quantity remains:

```python
quantity = len(node.psi4supply[w][bucket])
```

### 3.3 Lot identity must be preserved

Accepted, blocked, carryover, and overflow lots must retain their original Lot_IDs.

Do not generate new Lot_IDs in this MVP.

---

## 4. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan.
3. Do not modify existing monthly loaders.
4. Do not run Backward Planning.
5. Do not run Demand-to-Supply Bridge.
6. Do not implement Management Issue Generation.
7. Do not implement costing / KPI.
8. Do not implement OR optimization.
9. Keep this as an additive engine module + focused tests.
```

This request is only for:

```text
Weekly Forward PUSH with Capacity PSI Engine MVP
```

---

## 5. Suggested Files

Please add:

```text
pysi/plan/weekly_forward_push_with_capacity.py
tests/test_weekly_forward_push_with_capacity.py
```

Please update only if useful:

```text
pysi/plan/__init__.py
```

Do not modify:

```text
pysi/gui/*
run_full_plan
existing loaders
Bridge A / Bridge B utilities
```

---

## 6. Capacity Inputs

The MVP should accept weekly capacity as a plain dictionary.

Suggested input shape:

```python
weekly_capacity = {
    product_name: {
        node_name: {
            "P": [cap_p_w0, cap_p_w1, ...],
            "S": [cap_s_w0, cap_s_w1, ...],
            "I": [cap_i_w0, cap_i_w1, ...],
        }
    }
}
```

If a capacity type is missing, use a safe fallback:

```text
missing cap_P:
    unlimited or len(requested_P) for MVP

missing cap_S:
    unlimited or len(requested_S) for MVP

missing cap_I:
    unlimited or no overflow
```

Please document the chosen fallback in code comments.

Recommended MVP fallback:

```text
missing capacity = unlimited
```

---

## 7. Result Dataclass

Please implement:

```python
from dataclasses import dataclass, field


@dataclass
class WeeklyForwardPushWithCapacityResult:
    product_name: str
    processed_node_count: int = 0
    processed_week_count: int = 0

    accepted_p_lot_count: int = 0
    blocked_p_lot_count: int = 0
    accepted_s_lot_count: int = 0
    blocked_s_lot_count: int = 0
    overflow_i_lot_count: int = 0

    accepted_p_lot_ids: list[str] = field(default_factory=list)
    blocked_p_lot_ids: list[str] = field(default_factory=list)
    accepted_s_lot_ids: list[str] = field(default_factory=list)
    blocked_s_lot_ids: list[str] = field(default_factory=list)
    overflow_i_lot_ids: list[str] = field(default_factory=list)

    capacity_usage: list[dict] = field(default_factory=list)
    capacity_violations: list[dict] = field(default_factory=list)
    replan_commands: list[dict] = field(default_factory=list)

    non_list_bucket_errors: list[dict] = field(default_factory=list)
    non_string_lot_errors: list[dict] = field(default_factory=list)
    message: str = ""
```

---

## 8. Main Function

Please implement:

```python
def weekly_forward_push_with_capacity(
    *,
    root,
    product: str,
    weekly_capacity: dict | None = None,
    weeks: int | None = None,
    cap_i_mode: str = "soft",
    debug: bool = False,
) -> WeeklyForwardPushWithCapacityResult:
    ...
```

The function should traverse `root` and its descendants.

It should operate only on `psi4supply`.

---

## 9. Processing Logic

For each node and week:

### 9.1 P capacity

Read requested P lots:

```python
requested_P_lots = node.psi4supply[w][PSI_P]
```

Apply cap_P:

```text
accepted_P_lots = first cap_P lots
blocked_P_lots  = remaining requested_P_lots
```

The accepted P lots become available supply for that week.

### 9.2 Available supply

For MVP:

```text
available_lots = beginning_inventory_lots + accepted_P_lots
```

Beginning inventory may come from previous week inventory.

For week 0:

```text
beginning_inventory_lots = existing node.psi4supply[0][I]
```

For week w > 0:

```text
beginning_inventory_lots = previous ending inventory
```

### 9.3 S capacity

Read requested S lots:

```python
requested_S_lots = node.psi4supply[w][PSI_S]
```

Apply available supply and cap_S:

```text
ship_limit = min(len(available_lots), cap_S, len(requested_S_lots))

accepted_S_lots = first ship_limit lots from requested_S_lots
blocked_S_lots  = remaining requested_S_lots
```

### 9.4 Ending inventory

Update ending inventory:

```text
ending_inventory_lots = available_lots - accepted_S_lots
```

For MVP, if exact matching between requested S lots and available lots is not guaranteed, use deterministic FIFO removal from available_lots.

### 9.5 I capacity

Apply cap_I to ending inventory.

If `cap_i_mode = "soft"`:

```text
overflow_I_lots = ending_inventory_lots beyond cap_I
ending_inventory_lots remains unchanged
```

If `cap_i_mode = "hard"`:

```text
overflow_I_lots = ending_inventory_lots beyond cap_I
ending_inventory_lots = first cap_I lots
```

MVP must support at least:

```text
soft
```

Hard mode may be implemented if simple.

---

## 10. Capacity Usage Records

Please append usage records.

Suggested shape:

```python
{
    "node": node.name,
    "product": product,
    "week": w,
    "capacity_type": "P",
    "capacity": cap,
    "used": used,
    "remaining": max(0, cap - used),
}
```

Do this for P, S, and I when capacity is provided.

---

## 11. Capacity Violation Records

Please append violation records when requested or resulting quantity exceeds capacity.

Suggested shape:

```python
{
    "node": node.name,
    "product": product,
    "week": w,
    "capacity_type": "P",
    "capacity": cap,
    "requested": requested,
    "overflow": overflow,
    "lot_ids": overflow_lot_ids,
    "severity": "blocked",
}
```

For I soft cap:

```python
severity = "warning"
```

---

## 12. Replan Command Candidates

Forward Planning should not silently rewrite previous demand-side planning.

If capacity violations occur, append replan command candidates.

Suggested shape:

```python
{
    "type": "capacity_replan",
    "node": node.name,
    "product": product,
    "week": w,
    "capacity_type": "P",
    "lot_ids": blocked_lot_ids,
    "suggested_action": "review_capacity_or_rerun_backward_planning",
}
```

This is only a candidate record.

Do not implement a full ReplanCommand system here.

---

## 13. Safety Rules

Please enforce these invariants:

```text
1. psi4supply buckets remain lists.
2. bucket items remain Lot_ID strings.
3. no numeric quantity values are inserted.
4. accepted lots preserve Lot_ID identity.
5. blocked lots preserve Lot_ID identity.
6. overflow inventory lots preserve Lot_ID identity.
7. source psi4demand is not modified.
8. no Backward Planning is run.
9. no Demand-to-Supply Bridge is run.
10. no GUI / run_full_plan changes.
```

---

## 14. Test Fixtures

Use a minimal node class in tests.

```python
@dataclass
class MockSupplyNode:
    name: str
    children: list
    psi4supply: list
```

Helper:

```python
def make_node(name: str, weeks: int):
    return MockSupplyNode(
        name=name,
        children=[],
        psi4supply=[[[], [], [], []] for _ in range(weeks)],
    )
```

---

## 15. Required Tests

Please add:

```text
tests/test_weekly_forward_push_with_capacity.py
```

### 15.1 P cap blocks production lots

Input:

```python
node.psi4supply[10][P] = ["P1", "P2", "P3"]
cap_P[10] = 2
```

Expected:

```text
accepted_P = ["P1", "P2"]
blocked_P = ["P3"]
```

### 15.2 S cap blocks shipment lots

Input:

```python
node.psi4supply[10][I] = ["A", "B", "C"]
node.psi4supply[10][S] = ["A", "B", "C"]
cap_S[10] = 2
```

Expected:

```text
accepted_S = ["A", "B"]
blocked_S = ["C"]
```

### 15.3 I cap soft overflow

Input:

```python
ending_inventory = ["I1", "I2", "I3"]
cap_I[10] = 2
cap_i_mode = "soft"
```

Expected:

```text
overflow_I = ["I3"]
ending inventory remains ["I1", "I2", "I3"]
```

### 15.4 No numeric quantities inserted

Verify all `psi4supply` buckets contain strings only.

### 15.5 Missing capacity means unlimited

If no capacity is provided, requested lots should not be blocked by capacity.

### 15.6 Bridge B compatibility

Use `bridge_demand_to_supply_execution(...)` to seed `psi4supply`, then run `weekly_forward_push_with_capacity(...)`.

Expected:

```text
Bridge B output is accepted as input
no PSI structure error
```

---

## 16. Existing Tests to Run

Please run:

```bat
python -m pytest tests/test_weekly_forward_push_with_capacity.py
python -m pytest tests/test_demand_to_supply_execution_bridge.py
python -m pytest tests/test_e2e_demand_to_supply_bridge_flow_smoke.py
python -m pytest tests/test_capacity_aware_inbound_backward_planning.py
python -m pytest tests/test_japanese_rice_case_smoke.py
```

Optional:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

---

## 17. Completion Criteria

This request is complete when:

```text
[OK] weekly_forward_push_with_capacity.py exists
[OK] weekly_forward_push_with_capacity(...) works
[OK] P cap accepts / blocks lots
[OK] S cap accepts / blocks lots
[OK] I cap soft overflow is recorded
[OK] blocked lots preserve Lot_ID identity
[OK] overflow I lots preserve Lot_ID identity
[OK] capacity_usage records are produced
[OK] capacity_violations records are produced
[OK] replan command candidates are produced when blocked lots exist
[OK] no numeric quantities are inserted into PSI buckets
[OK] Bridge B output is compatible
[OK] focused tests pass
[OK] no GUI / run_full_plan / loader changes
```

---

## 18. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. How P/S/I capacity is applied
4. How blocked / overflow lots preserve Lot_ID identity
5. Test commands executed
6. Test results
7. Any limitations or follow-up tasks
```

Please do not proceed into:

```text
run_full_plan integration
GUI integration
full multi-echelon lane propagation
costing / KPI integration
Management Issue Generation
OR optimization
```

This request is only for:

```text
Weekly Forward PUSH with Capacity PSI Engine MVP
```