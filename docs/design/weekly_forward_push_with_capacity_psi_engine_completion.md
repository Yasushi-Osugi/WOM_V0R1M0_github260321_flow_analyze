# Weekly Forward PUSH with Capacity PSI Engine MVP Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-22  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Weekly Forward PUSH with Capacity PSI Engine MVP**.

The purpose of this milestone was to implement the first supply-side execution simulation layer after Bridge B.

The completed target flow is:

```text
finalized psi4demand
    ↓
Bridge B: Demand-to-Supply Execution Bridge
    ↓
psi4supply
    ↓
Weekly Forward PUSH with Capacity
```

This milestone translates the monthly PSI with capacity concept into WOM's weekly, multi-node, Lot_ID-list-based PSI model.

---

## 2. Background

Before this milestone, the E2E demand-to-supply bridge flow had been completed up to Bridge B.

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

Bridge B creates a supply-side seed state.

The next required step was to validate whether `psi4supply` can be processed under weekly capacity constraints.

---

## 3. Implemented Files

This milestone added:

```text
pysi/plan/weekly_forward_push_with_capacity.py
tests/test_weekly_forward_push_with_capacity.py
```

---

## 4. Implemented Function

The main function added is:

```python
weekly_forward_push_with_capacity(...)
```

Conceptual behavior:

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

The function traverses the target root and descendants, and operates only on `psi4supply`.

---

## 5. Capacity Handling

### 5.1 P capacity

`cap_P` limits weekly production / purchase / supply inflow.

```text
requested P lots
    ↓
accepted P lots
blocked P lots
```

Example:

```text
psi4supply[10][P] = ["P1", "P2", "P3"]
cap_P[10] = 2

accepted_P = ["P1", "P2"]
blocked_P  = ["P3"]
```

---

### 5.2 S capacity

`cap_S` limits weekly shipment / sales / supply outflow.

```text
requested S lots
    ↓
accepted S lots
blocked S lots
```

Example:

```text
available inventory = ["A", "B", "C"]
psi4supply[10][S] = ["A", "B", "C"]
cap_S[10] = 2

accepted_S = ["A", "B"]
blocked_S  = ["C"]
```

---

### 5.3 I capacity

`cap_I` limits ending inventory.

MVP supports soft inventory overflow.

```text
ending inventory = ["I1", "I2", "I3"]
cap_I[10] = 2

overflow_I = ["I3"]
ending inventory remains ["I1", "I2", "I3"]
```

This means `cap_I` can be used as a warning / violation detector without deleting inventory.

---

## 6. Missing Capacity Policy

The MVP uses:

```text
missing capacity = unlimited
```

This means:

```text
missing cap_P:
    P lots are not blocked by capacity

missing cap_S:
    S lots are not blocked by capacity

missing cap_I:
    inventory overflow is not recorded
```

This keeps the MVP safe and backward compatible.

---

## 7. Result Object

The result dataclass is:

```python
WeeklyForwardPushWithCapacityResult
```

It records:

```text
processed_node_count
processed_week_count

accepted_p_lot_count
blocked_p_lot_count
accepted_s_lot_count
blocked_s_lot_count
overflow_i_lot_count

accepted_p_lot_ids
blocked_p_lot_ids
accepted_s_lot_ids
blocked_s_lot_ids
overflow_i_lot_ids

capacity_usage
capacity_violations
replan_commands

non_list_bucket_errors
non_string_lot_errors
message
```

---

## 8. Capacity Usage and Violation Records

The MVP produces capacity usage records.

Example:

```python
{
    "node": "MOM_ASIA",
    "product": "RICE",
    "week": 10,
    "capacity_type": "P",
    "capacity": 2,
    "used": 2,
    "remaining": 0,
}
```

It also produces capacity violation records.

Example:

```python
{
    "node": "MOM_ASIA",
    "product": "RICE",
    "week": 10,
    "capacity_type": "P",
    "capacity": 2,
    "requested": 3,
    "overflow": 1,
    "lot_ids": ["P3"],
    "severity": "blocked",
}
```

For soft inventory overflow:

```text
severity = warning
```

---

## 9. Replan Command Candidates

The MVP creates candidate records when capacity blocks lots.

Conceptual example:

```python
{
    "type": "capacity_replan",
    "node": "MOM_ASIA",
    "product": "RICE",
    "week": 10,
    "capacity_type": "P",
    "lot_ids": ["P3"],
    "suggested_action": "review_capacity_or_rerun_backward_planning",
}
```

This is only a candidate record.

The MVP does not implement full ReplanCommand orchestration.

---

## 10. Safety Invariants

The following invariants were preserved.

```text
[OK] psi4supply buckets remain lists.
[OK] bucket items remain Lot_ID strings.
[OK] no numeric quantities are inserted.
[OK] accepted lots preserve Lot_ID identity.
[OK] blocked lots preserve Lot_ID identity.
[OK] overflow inventory lots preserve Lot_ID identity.
[OK] source psi4demand is not modified.
[OK] no Backward Planning is run.
[OK] no Demand-to-Supply Bridge is run.
[OK] no GUI / run_full_plan changes.
```

---

## 11. Test Summary

Focused tests were added in:

```text
tests/test_weekly_forward_push_with_capacity.py
```

They cover:

```text
1. P cap accepts / blocks production lots.
2. S cap accepts / blocks shipment lots.
3. I cap soft overflow is recorded.
4. No numeric quantities are inserted.
5. Missing capacity means unlimited.
6. Bridge B output is compatible with weekly forward push.
```

---

## 12. Validation

The following test passed:

```bat
python -m pytest tests/test_weekly_forward_push_with_capacity.py
```

Result:

```text
6 passed
```

Compatibility tests also passed:

```bat
python -m pytest tests/test_demand_to_supply_execution_bridge.py
python -m pytest tests/test_e2e_demand_to_supply_bridge_flow_smoke.py
python -m pytest tests/test_capacity_aware_inbound_backward_planning.py
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results:

```text
tests/test_demand_to_supply_execution_bridge.py: 10 passed
tests/test_e2e_demand_to_supply_bridge_flow_smoke.py: 2 passed
tests/test_capacity_aware_inbound_backward_planning.py: 3 passed
tests/test_japanese_rice_case_smoke.py: 1 passed
tests/test_covid_vaccine_with_capacity_push.py: 1 passed
```

---

## 13. Latest Commit

Implementation was completed with:

```text
750e127 Add weekly forward push with capacity MVP engine
```

Work was performed on:

```text
feature/with-capacity-psi-engine-v0r2
```

---

## 14. Meaning of This Milestone

This milestone completes the first MVP layer after Bridge B.

Before this milestone:

```text
finalized psi4demand
    ↓
Bridge B
    ↓
psi4supply seed
```

After this milestone:

```text
finalized psi4demand
    ↓
Bridge B
    ↓
psi4supply seed
    ↓
Weekly Forward PUSH with Capacity
```

This means WOM can now begin to simulate supply-side execution feasibility under P / S / I capacity constraints.

---

## 15. Important Boundary

This milestone does not implement:

```text
run_full_plan integration
GUI integration
full multi-echelon lane propagation
costing / KPI integration
Management Issue Generation
OR optimization
automatic backward replan
```

It only implements the focused weekly forward capacity process on `psi4supply`.

---

## 16. Relationship to Monthly PSI with Capacity

The monthly PSI with capacity model uses scalar formulas.

```text
capped_P = min(Purchase, cap_P)
Ship = min(available, demand/backlog, cap_S)
overflow_I = max(0, Inventory - cap_I)
```

The WOM weekly version uses Lot_ID list operations.

```text
cap_P:
    accept / block supply P lots

cap_S:
    accept / block supply S lots

cap_I:
    detect ending inventory overflow
```

The key conversion is:

```text
scalar quantity
    ↓
len(Lot_ID list)
```

---

## 17. Current Completed Flow

The current completed flow is now:

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

In compact form:

```text
outbound demand/P
    ↓
inbound demand/S
    ↓
MOM demand/S
    ↓
MOM demand/P with early build / backlog
    ↓
supply/S and supply/P seed
    ↓
P/S/I capacity-aware forward push
```

---

## 18. Future Milestones

### 18.1 E2E bridge + forward capacity smoke

Future target:

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

as one controlled smoke test.

---

### 18.2 Run Full Plan Integration

After the above E2E smoke is stable:

```text
run_full_plan
    ↓
explicit bridge / backward / forward pipeline
```

---

### 18.3 Cost / KPI / Management Issue Integration

Forward capacity results should later connect to:

```text
capacity usage
capacity violations
blocked lots
replan commands
service impact
inventory impact
cost / profit impact
management issues
```

---

## 19. Summary

Weekly Forward PUSH with Capacity PSI Engine MVP is complete.

The completed operation is:

```text
psi4supply
    ↓
cap_P / cap_S / cap_I
    ↓
accepted / blocked / overflow lots
```

The key invariant remains:

```text
PSI buckets hold Lot_ID lists.
Quantity is len(list).
Capacity changes lot status, not lot identity.
```

This milestone prepares WOM for controlled E2E execution smoke and future `run_full_plan` integration.