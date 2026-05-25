# Weekly Forward PUSH with Capacity PSI Engine Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-22  
**Status:** Design memo  
**Target path:** `docs/design/weekly_forward_push_with_capacity_psi_engine.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/with_capacity_forward_push_after_bridge_b.md`
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

## 1. File Name Note

The intended file name is:

```text
docs/design/weekly_forward_push_with_capacity_psi_engine.md
```

Use lowercase `psi` in the file name.

The earlier spelling:

```text
weekly_forward_push_with_capacity_psI_engine.md
```

with capital `I` was not intentional. It was only a visual typo caused by writing PSI as a concept while also using a file name.

Recommended convention:

```text
file name:
    weekly_forward_push_with_capacity_psi_engine.md

title:
    Weekly Forward PUSH with Capacity PSI Engine Design Memo

concept:
    PSI = Production / Shipment / Inventory
```

---

## 2. Purpose

This memo defines the design of **Weekly Forward PUSH with Capacity PSI Engine**.

The purpose is to convert the monthly PSI with capacity concept into WOM's weekly, multi-node, Lot_ID-list-based PSI engine.

The key transformation is:

```text
Monthly scalar PSI with capacity
    ↓
Weekly multi-node Lot_ID-list PSI with capacity
```

The engine should process `psi4supply` after Bridge B.

Bridge B produces:

```text
finalized psi4demand
    ↓
psi4supply
```

Weekly Forward PUSH with Capacity consumes that `psi4supply` seed and simulates supply-side execution under:

```text
cap_P
cap_S
cap_I
```

---

## 3. Position in the WOM Flow

The completed upstream flow is:

```text
Bridge A
    ↓
MOM allocation
    ↓
TOBE capacity-aware inbound backward planning
    ↓
Bridge B
```

After Bridge B:

```text
finalized psi4demand
    ↓
psi4supply
```

The next stage is:

```text
psi4supply
    ↓
Weekly Forward PUSH with Capacity
    ↓
executed supply-side PSI
```

Full conceptual flow:

```text
[1] Demand-side planning
    ↓
[2] Bridge A
    ↓
[3] MOM allocation
    ↓
[4] Capacity-aware inbound backward planning
    ↓
[5] Bridge B
    ↓
[6] Weekly Forward PUSH with Capacity
    ↓
[7] execution feasibility / blocked lots / capacity usage
```

---

## 4. Monthly PSI with Capacity Concept

The monthly PSI with capacity model uses scalar quantities.

Representative monthly logic:

```text
capped_P = min(Purchase, cap_P)

available_supply = previous_inventory + capped_P

Ship = min(available_supply, demand + backlog, cap_S)

Inventory = available_supply - Ship

overflow_I = max(0, Inventory - cap_I)
```

This model uses three capacity concepts:

```text
cap_P:
    production / purchase / supply inflow capacity

cap_S:
    shipment / sales / supply outflow capacity

cap_I:
    inventory / storage capacity
```

---

## 5. Translation to WOM Weekly Lot-Based PSI

WOM does not use scalar PSI quantities as the primary state.

WOM uses Lot_ID lists.

Canonical V0R8 structure:

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

The quantity is:

```python
quantity = len(node.psi4supply[w][bucket])
```

Therefore, monthly scalar formulas must be translated into Lot_ID-list operations.

---

## 6. Core Design Principle

The core design principle is:

```text
Capacity does not replace PSI buckets with numeric quantities.

Capacity selects, blocks, shifts, or marks Lot_IDs while preserving Lot_ID identity.
```

Correct:

```python
node.psi4supply[w][PSI_P] = ["LOT_A", "LOT_B"]
```

Incorrect:

```python
node.psi4supply[w][PSI_P] = 2
```

---

## 7. Capacity Types

### 7.1 cap_P

`cap_P` is a weekly flow capacity for production / purchase / supply inflow.

It limits how many lots can be accepted into the P bucket execution for a week.

Conceptual logic:

```python
requested_P_lots = node.psi4supply[w][PSI_P]
cap_P = capacity[node][product][w]["P"]

accepted_P_lots = requested_P_lots[:cap_P]
blocked_P_lots  = requested_P_lots[cap_P:]
```

### 7.2 cap_S

`cap_S` is a weekly flow capacity for shipment / sales / supply outflow.

It limits how many lots can be shipped, consumed, or supplied out in a week.

Conceptual logic:

```python
requested_S_lots = node.psi4supply[w][PSI_S]
cap_S = capacity[node][product][w]["S"]

accepted_S_lots = requested_S_lots[:cap_S]
blocked_S_lots  = requested_S_lots[cap_S:]
```

### 7.3 cap_I

`cap_I` is a weekly stock capacity for inventory / storage.

It checks the ending inventory level.

Conceptual logic:

```python
inventory_lots = node.psi4supply[w][PSI_I]
cap_I = capacity[node][product][w]["I"]

overflow_I_lots = inventory_lots[cap_I:]
```

---

## 8. P / S / I Capacity Semantics

### 8.1 P and S are flow capacities

`cap_P` and `cap_S` are flow constraints.

They determine how many lots can move through a weekly activity.

```text
P:
    how many lots can be produced / purchased / received this week

S:
    how many lots can be shipped / sold / consumed this week
```

### 8.2 I is stock capacity

`cap_I` is a stock constraint.

It determines how many lots can remain as ending inventory.

```text
I:
    how many lots can be stored at week end
```

### 8.3 Hard cap vs soft cap

`cap_P` and `cap_S` are usually hard caps.

`cap_I` may be hard or soft.

```text
hard cap:
    overflow lot must be blocked / moved / rejected / externalized

soft cap:
    inventory remains, but overflow is recorded as a capacity violation
```

Recommended MVP:

```text
cap_P:
    hard

cap_S:
    hard

cap_I:
    soft by default
```

---

## 9. Weekly Forward PUSH with Capacity Processing Order

Recommended MVP processing order for each node / product / week:

```text
1. Read beginning inventory / carryover pool.
2. Read requested P lots from psi4supply[w][P].
3. Apply cap_P.
4. Add accepted P lots to available supply pool.
5. Read requested S lots from psi4supply[w][S].
6. Apply available supply and cap_S.
7. Update ending inventory lots.
8. Apply cap_I.
9. Record capacity usage and capacity violations.
10. Preserve blocked Lot_IDs.
```

In compact form:

```text
P cap
    ↓
available supply
    ↓
S cap
    ↓
ending inventory
    ↓
I cap
```

---

## 10. Weekly Lot-Based Formula

### 10.1 Input

For each node / product / week:

```text
begin_inventory_lots
requested_P_lots
requested_S_lots
carryover_blocked_lots
cap_P
cap_S
cap_I
```

### 10.2 P capacity

```text
accepted_P_lots = first cap_P lots from requested_P_lots
blocked_P_lots  = remaining requested_P_lots
```

### 10.3 Available supply

```text
available_lots =
    begin_inventory_lots
    + accepted_P_lots
```

### 10.4 S capacity and supply availability

```text
ship_limit = min(len(available_lots), cap_S)

accepted_S_lots = first ship_limit lots from requested_S_lots
blocked_S_lots  = remaining requested_S_lots
```

If requested_S_lots contains lots not present in available_lots, the MVP may use a simple count-based rule first. A later version can enforce exact Lot_ID matching between requested S and available supply.

### 10.5 Ending inventory

```text
ending_inventory_lots =
    available_lots - accepted_S_lots
```

For an MVP, if exact Lot_ID matching is not yet guaranteed, ending inventory may be computed by removing accepted S lots from available lots when present, and otherwise using deterministic FIFO removal.

### 10.6 I capacity

Soft cap:

```text
overflow_I_lots = ending_inventory_lots beyond cap_I
ending_inventory_lots remains unchanged
```

Hard cap:

```text
overflow_I_lots = ending_inventory_lots beyond cap_I
ending_inventory_lots = first cap_I lots
overflow_I_lots are moved to blocked / overflow state
```

---

## 11. Capacity Source

Capacity can be provided by:

```text
weekly_capability
capacity_master
node attribute
edge / lane capacity
scenario override
external event model
```

MVP recommended shape:

```python
weekly_capacity = {
    product: {
        node_name: {
            "P": [cap_p_w0, cap_p_w1, ...],
            "S": [cap_s_w0, cap_s_w1, ...],
            "I": [cap_i_w0, cap_i_w1, ...],
        }
    }
}
```

A more normalized source may later use:

```text
node_name
product_name
week
capacity_type
capacity_qty
cap_mode
```

where:

```text
capacity_type ∈ {P, S, I}
cap_mode ∈ {hard, soft}
```

---

## 12. Result Object

Suggested result object:

```python
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

## 13. Capacity Usage Record

Suggested usage record:

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

---

## 14. Capacity Violation Record

Suggested violation record:

```python
{
    "node": "MOM_ASIA",
    "product": "RICE",
    "week": 10,
    "capacity_type": "P",
    "capacity": 2,
    "requested": 3,
    "overflow": 1,
    "lot_ids": ["LOT_003"],
    "severity": "warning",
}
```

For hard cap violations:

```text
severity = "blocked"
```

For soft inventory overflow:

```text
severity = "warning"
```

---

## 15. Replan Command Candidate

Forward Planning should not silently rewrite the past or re-run backward planning.

If capacity violations occur, it should emit replan command candidates.

Suggested record:

```python
{
    "type": "capacity_replan",
    "node": "MOM_ASIA",
    "product": "RICE",
    "week": 10,
    "capacity_type": "P",
    "lot_ids": ["LOT_003"],
    "suggested_action": "rerun_capacity_aware_backward_planning_or_adjust_capacity",
}
```

---

## 16. Safety Invariants

The engine must preserve:

```text
1. psi4supply buckets remain lists.
2. bucket items remain Lot_ID strings.
3. no numeric quantity values are inserted.
4. accepted lots preserve Lot_ID identity.
5. blocked lots preserve Lot_ID identity.
6. overflow inventory lots preserve Lot_ID identity.
7. Bridge B source demand is not modified.
8. Forward PUSH does not silently perform backward replanning.
9. GUI and run_full_plan are not modified in MVP.
```

---

## 17. MVP Scope

### 17.1 In scope

```text
single-node or small subtree weekly forward supply PSI
P cap hard limit
S cap hard limit
I cap soft limit
accepted / blocked / overflow lot reporting
capacity usage reporting
capacity violation reporting
```

### 17.2 Out of scope

```text
multi-echelon lane propagation
edge capacity
transport leadtime
run_full_plan integration
GUI integration
costing / KPI
Management Issue generation
OR optimization
automatic backward replan
```

---

## 18. Suggested Function

Suggested MVP function:

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

---

## 19. Suggested Implementation File

Suggested file:

```text
pysi/plan/weekly_forward_push_with_capacity.py
```

or, if keeping bridge-related smoke modules together:

```text
pysi/plan/bridges/weekly_forward_push_with_capacity_after_bridge_b.py
```

Recommended:

```text
pysi/plan/weekly_forward_push_with_capacity.py
```

because this is a planning engine component, not merely a bridge.

---

## 20. Suggested Test File

Suggested file:

```text
tests/test_weekly_forward_push_with_capacity.py
```

---

## 21. MVP Test Scenarios

### 21.1 P cap blocks production lots

Input:

```text
psi4supply[10][P] = ["P1", "P2", "P3"]
cap_P[10] = 2
```

Expected:

```text
accepted_P = ["P1", "P2"]
blocked_P = ["P3"]
```

### 21.2 S cap blocks shipment lots

Input:

```text
begin_inventory = ["A", "B", "C"]
psi4supply[10][S] = ["A", "B", "C"]
cap_S[10] = 2
```

Expected:

```text
accepted_S = ["A", "B"]
blocked_S = ["C"]
```

### 21.3 I cap records overflow

Input:

```text
ending_inventory = ["I1", "I2", "I3"]
cap_I[10] = 2
cap_i_mode = "soft"
```

Expected:

```text
overflow_I = ["I3"]
ending_inventory remains ["I1", "I2", "I3"]
```

### 21.4 No numeric quantities inserted

All supply buckets remain `list[str]`.

### 21.5 Bridge B compatibility

Use `bridge_demand_to_supply_execution(...)` to seed `psi4supply`, then run `weekly_forward_push_with_capacity(...)`.

Verify the output accepts / blocks lots as expected.

---

## 22. Relationship to Existing E2E Smoke

The completed E2E bridge smoke ends at:

```text
Bridge B
    ↓
psi4supply
```

This engine begins at:

```text
psi4supply
    ↓
Weekly Forward PUSH with Capacity
```

The next integration smoke can be:

```text
Bridge A
    ↓
MOM allocation
    ↓
capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
weekly_forward_push_with_capacity
```

---

## 23. Open Questions

Before implementation, confirm:

```text
1. Should S requested lots be required to exist in available inventory?
2. Should P accepted lots immediately become available for S in the same week?
3. Should cap_I be soft by default for Rice / Phone cases?
4. Should cap_I hard mode create blocked_I_lots or overflow_I_lots?
5. Should blocked_P and blocked_S be carried to next week automatically?
6. Should carryover be implemented now or as v0r2?
```

Recommended MVP answers:

```text
1. use deterministic FIFO count-based matching first
2. yes, accepted P is available in same week for MVP
3. yes, cap_I soft by default
4. hard mode can be deferred
5. no automatic carryover in v0r1
6. carryover is v0r2
```

---

## 24. Recommended Next Step

Next step:

```text
1. Add this design memo.
2. Create Codex Request:
   docs/codex_requests/weekly_forward_push_with_capacity_psi_engine_request.md
3. Implement focused MVP:
   pysi/plan/weekly_forward_push_with_capacity.py
   tests/test_weekly_forward_push_with_capacity.py
```

---

## 25. Summary

Weekly Forward PUSH with Capacity translates monthly PSI-on-CAP scalar logic into WOM's weekly, multi-node, Lot_ID-list PSI world.

The core processing is:

```text
cap_P:
    accept / block supply P lots

cap_S:
    accept / block supply S lots

cap_I:
    check ending inventory overflow
```

The core invariant is:

```text
PSI buckets contain Lot_ID lists only.
Quantity is len(list).
Capacity changes lot status, not lot identity.
```

This design provides the next planning engine layer after Bridge B.
