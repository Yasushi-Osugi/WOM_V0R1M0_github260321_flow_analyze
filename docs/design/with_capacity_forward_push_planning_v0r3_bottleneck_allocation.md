# With-Capacity PSI Engine v0r3 Design Memo
## Bottleneck Allocation Rule Enhancement

## 1. Purpose

This document defines the design scope and implementation approach for:

```text
with-capacity PSI engine v0r3
```

v0r2 completed the foundation of Forward PUSH with Capacity Planning.

```text
v0r2-m1:
    standalone capacity-aware lot split logic

v0r2-m2:
    capacity master loader and usage / violation CSV output

v0r2-m3:
    PSI list integration adapter
```

v0r2 answered the question:

```text
capacityを超えたら、Lotを止められるか？
```

v0r3 now answers the next question:

```text
capacityを超えた時、どのLotを優先して通すか？
```

The purpose of v0r3 is to enhance allocation behavior at bottleneck nodes.

---

## 2. Core Concept

Allocation is required only when capacity is insufficient.

A bottleneck exists when:

```text
requested_lots > available_capacity
```

for a given:

```text
node
product
week
capacity_type
```

If the node is not a bottleneck, no allocation rule is required.

```text
non-bottleneck node:
    normal pass-through

bottleneck node:
    allocation rule is applied
```

This is the key design principle.

v0r3 should not apply complex allocation logic to all nodes.

The allocation rule should be triggered only at bottleneck points.

---

## 3. Relationship with v0r2

v0r2 currently uses a simple default rule:

```text
first-in, first-pushed
```

v0r3 extends this by allowing selected priority rules.

The v0r2 behavior must remain the default.

Therefore:

```text
no allocation rule specified:
    use first-in, first-pushed

allocation rule specified:
    sort / select lots according to the rule
```

This preserves compatibility and keeps existing tests stable.

---

## 4. Design Principle

The key principles are:

```text
1. Do not modify the original Forward PUSH planner behavior.
2. Do not rewrite the Node class.
3. Do not break v0r2-m1 / m2 / m3 tests.
4. Keep first-in, first-pushed as the default allocation rule.
5. Apply allocation only at bottleneck nodes.
6. Keep allocation rule logic small, explicit, and testable.
7. Do not implement full optimization in v0r3.
8. Do not implement GUI integration in v0r3.
```

v0r3 is a rule-based allocation milestone, not a mathematical optimization milestone.

---

## 5. In Scope

v0r3 should implement:

```text
allocation rule dataclass
allocation priority key function
lot sorting / selection function
bottleneck-only allocation behavior
rule-based accepted / blocked lot selection
basic allocation rule master CSV
allocation decision records
smoke runner
focused tests
```

The implementation should be additive.

---

## 6. Out of Scope

v0r3 should not implement:

```text
linear programming optimization
multi-bottleneck global optimization
profit maximization solver
lane selection optimization
PULL integration
GUI integration
management cockpit integration
costing engine integration
automatic future-week rescheduling
complex inventory balancing
```

These are later milestones.

---

## 7. Allocation Rule Types

v0r3 should support a small set of practical rule types.

### 7.1 FIFO

```text
FIFO
```

Default rule.

Meaning:

```text
input order is preserved
```

Equivalent to v0r2 behavior.

---

### 7.2 Due Date Priority

```text
DUE_DATE
```

Earlier due date gets priority.

Required lot attribute:

```text
due_week
```

or similar.

If missing, lot should be treated as low priority.

---

### 7.3 Market Priority

```text
MARKET_PRIORITY
```

Lots for higher-priority market nodes get priority.

Required lot attribute:

```text
market_priority
```

or:

```text
market_name
```

mapped through a rule table.

---

### 7.4 Product Priority

```text
PRODUCT_PRIORITY
```

Lots for higher-priority products get priority.

Required lot attribute:

```text
product_priority
```

or product-level priority from rule master.

---

### 7.5 Customer Priority

```text
CUSTOMER_PRIORITY
```

Lots for strategic customers get priority.

Required lot attribute:

```text
customer_priority
```

This can be lightly supported as an optional lot field.

---

### 7.6 Strategic Priority

```text
STRATEGIC_PRIORITY
```

A generic priority score.

Required lot attribute:

```text
priority
```

or:

```text
strategic_priority
```

This is useful as a flexible MVP rule.

---

## 8. Recommended v0r3 MVP Rule Set

For v0r3 MVP, implement only these rules first:

```text
FIFO
DUE_DATE
PRIORITY_SCORE
```

Where:

```text
FIFO:
    preserve input order

DUE_DATE:
    earlier due_week first

PRIORITY_SCORE:
    larger priority score first
```

Other rule names may be defined in the design but can be left for later.

This keeps the first implementation compact.

---

## 9. Lot Representation

Lots may be represented as:

```python
"LOT001"
```

or:

```python
{"lot_id": "LOT001", "due_week": "2026-W02", "priority": 90}
```

v0r3 should continue to support both forms.

For string lot IDs:

```text
no metadata is available
```

Therefore, non-FIFO rules should treat string lots as lowest priority unless external metadata is provided.

Recommended helper:

```python
def _lot_id(lot: Any) -> str:
    if isinstance(lot, dict):
        return str(lot.get("lot_id", lot))
    return str(lot)
```

---

## 10. Allocation Rule Dataclass

Suggested structure:

```python
@dataclass
class AllocationRule:
    rule_id: str
    rule_type: str = "FIFO"
    scenario_id: str = "BASE"
    node_name: str = "*"
    product_name: str = "*"
    capacity_type: str = "*"
    priority_field: str = "priority"
    due_week_field: str = "due_week"
    ascending: bool = True
    enabled: bool = True
    comment: str = ""
```

Meaning:

| Field | Meaning |
|---|---|
| rule_id | Rule identifier |
| rule_type | FIFO / DUE_DATE / PRIORITY_SCORE |
| scenario_id | Scenario name |
| node_name | Target node or `*` |
| product_name | Target product or `*` |
| capacity_type | P / S / I or `*` |
| priority_field | Lot dict field used for priority |
| due_week_field | Lot dict field used for due date |
| ascending | Sort direction |
| enabled | Whether this rule is active |
| comment | Description |

---

## 11. Allocation Rule Master CSV

Recommended sample file:

```text
pysi/master_data/allocation_rule_master_sample.csv
```

Header:

```csv
scenario_id,node_name,product_name,capacity_type,rule_id,rule_type,priority_field,due_week_field,ascending,enabled,comment
```

Example:

```csv
scenario_id,node_name,product_name,capacity_type,rule_id,rule_type,priority_field,due_week_field,ascending,enabled,comment
BASE,MOM_CHINA,IPHONE_NM_2028_BASE,P,RULE_FIFO,FIFO,priority,due_week,true,true,default FIFO rule
BASE,MOM_CHINA,IPHONE_NM_2028_BASE,P,RULE_DUE,DUE_DATE,priority,due_week,true,true,earliest due week first
BASE,MOM_CHINA,IPHONE_NM_2028_BASE,P,RULE_PRIORITY,PRIORITY_SCORE,priority,due_week,false,true,higher priority score first
BASE,*,*,P,RULE_DEFAULT,FIFO,priority,due_week,true,true,wildcard fallback FIFO
```

---

## 12. Rule Lookup Policy

Rule lookup should follow a simple fallback order:

```text
1. exact:
   scenario_id, node_name, product_name, capacity_type

2. node + product wildcard:
   scenario_id, node_name, "*", capacity_type

3. node wildcard:
   scenario_id, "*", product_name, capacity_type

4. global wildcard:
   scenario_id, "*", "*", capacity_type

5. default:
   FIFO
```

If multiple rules match, use the first enabled rule by deterministic order.

For v0r3 MVP, it is acceptable to keep lookup simple.

---

## 13. Allocation Function

Suggested function:

```python
def allocate_lots(
    *,
    requested_lots: list,
    capacity_qty: int | None,
    allocation_rule: AllocationRule | None = None,
) -> tuple[list, list]:
    ...
```

Expected behavior:

```text
capacity_qty is None:
    accepted = all requested lots
    blocked = []

capacity_qty >= len(requested_lots):
    accepted = all requested lots
    blocked = []

capacity_qty < len(requested_lots):
    sort requested lots according to allocation rule
    accepted = first capacity_qty lots
    blocked = remaining lots
```

If no rule is specified:

```text
use FIFO
```

---

## 14. Priority Sorting Rules

### 14.1 FIFO

```python
key = original_position
```

No sorting required.

---

### 14.2 DUE_DATE

```text
earlier due_week first
```

Example lot:

```python
{"lot_id": "LOT001", "due_week": "2026-W01"}
```

Missing due_week should be treated as late.

---

### 14.3 PRIORITY_SCORE

```text
higher priority score first
```

Example lot:

```python
{"lot_id": "LOT001", "priority": 90}
```

Missing priority should be treated as lowest priority.

---

## 15. Allocation Decision Record

v0r3 should produce allocation decision records for traceability.

Suggested dataclass:

```python
@dataclass
class AllocationDecision:
    scenario_id: str
    node_name: str
    product_name: str
    week: str
    capacity_type: str
    rule_id: str
    rule_type: str
    requested_qty: int
    capacity_qty: int | None
    accepted_qty: int
    blocked_qty: int
    accepted_lot_ids: list[str] = field(default_factory=list)
    blocked_lot_ids: list[str] = field(default_factory=list)
```

This record is useful for later event tracing and management reporting.

---

## 16. Allocation Decision CSV Output

Recommended output path:

```text
outputs/capacity/forward_push_with_capacity_allocation_decisions.csv
```

Header:

```csv
scenario_id,node_name,product_name,week,capacity_type,rule_id,rule_type,requested_qty,capacity_qty,accepted_qty,blocked_qty,accepted_lot_ids,blocked_lot_ids
```

Lot IDs should be pipe-separated.

Example:

```csv
BASE,MOM_CHINA,IPHONE_NM_2028_BASE,2026-W01,P,RULE_PRIORITY,PRIORITY_SCORE,120,100,100,20,LOT001|LOT002,LOT119|LOT120
```

---

## 17. Integration with v0r2 PSI Adapter

v0r3 should integrate allocation rule selection into the v0r2-m3 adapter.

Current v0r2-m3 behavior:

```text
read requested lots from psi4demand
apply capacity split using FIFO
write accepted lots to psi4supply
record blocked lots
```

v0r3 behavior:

```text
read requested lots from psi4demand
detect bottleneck
if bottleneck:
    lookup allocation rule
    allocate lots according to rule
else:
    pass through
write accepted lots to psi4supply
record blocked lots
record allocation decision
```

The adapter should remain backward compatible.

If no allocation rule master is provided, the result should be the same as v0r2.

---

## 18. Mutation Policy

Keep the v0r2-m3 mutation policy:

```text
read from:
    node.psi4demand

write to:
    node.psi4supply

do not delete from:
    node.psi4demand
```

Blocked lots should be recorded separately.

Do not automatically reschedule blocked lots into future weeks in v0r3 MVP.

---

## 19. Recommended Module Structure

Suggested files:

```text
pysi/planning/allocation_rule.py
pysi/planning/allocation_io.py
pysi/runners/run_forward_push_with_capacity_allocation_smoke.py
tests/test_allocation_rule.py
tests/test_forward_push_with_capacity_allocation_adapter.py
pysi/master_data/allocation_rule_master_sample.csv
```

Existing files may be lightly extended if appropriate:

```text
pysi/planning/forward_push_with_capacity_psi_adapter.py
pysi/planning/capacity_io.py
```

Avoid broad refactoring.

---

## 20. Smoke Scenario

Create a bottleneck scenario:

```text
node: MOM_CHINA
product: IPHONE_NM_2028_BASE
week: 2026-W01
capacity type: P
requested lots: 5
capacity: 3
allocation rule: PRIORITY_SCORE
```

Requested lots:

```python
[
    {"lot_id": "LOT_A", "priority": 10},
    {"lot_id": "LOT_B", "priority": 90},
    {"lot_id": "LOT_C", "priority": 30},
    {"lot_id": "LOT_D", "priority": 80},
    {"lot_id": "LOT_E", "priority": 20},
]
```

Expected accepted lots:

```text
LOT_B
LOT_D
LOT_C
```

Expected blocked lots:

```text
LOT_E
LOT_A
```

This confirms that allocation is no longer simple FIFO when a priority rule is active.

---

## 21. Test Policy

Required tests:

```text
1. FIFO preserves original order
2. DUE_DATE accepts earlier due_week lots first
3. PRIORITY_SCORE accepts higher priority lots first
4. missing allocation rule defaults to FIFO
5. capacity sufficient case does not need special allocation
6. bottleneck case applies allocation rule
7. string lot IDs remain supported
8. dict lots with lot_id remain supported
9. accepted / blocked lot IDs are recorded
10. allocation decision CSV export works
11. v0r2-m1 tests still pass
12. v0r2-m2 tests still pass
13. v0r2-m3 tests still pass
```

---

## 22. Completion Criteria

v0r3 is complete when:

```text
[OK] AllocationRule dataclass exists
[OK] allocation rule master sample exists
[OK] allocation rule loader exists
[OK] FIFO allocation works
[OK] DUE_DATE allocation works
[OK] PRIORITY_SCORE allocation works
[OK] missing rule defaults to FIFO
[OK] allocation is applied only at bottleneck nodes
[OK] accepted lots are written to psi4supply
[OK] blocked lots are recorded separately
[OK] allocation decision record exists
[OK] allocation decision CSV export works
[OK] v0r2 tests remain compatible
[OK] smoke runner works
```

---

## 23. Future Milestones After v0r3

After v0r3, possible next steps include:

```text
v0r4:
    GUI comparison of original vs capacity vs allocation plans

v0r5:
    PULL integration and E2E scenario planning

v0r6:
    management issue generation and cockpit integration

v0r7:
    profit / cost aware allocation

v0r8:
    multi-bottleneck optimization
```

These are outside v0r3.

---

## 24. Summary

v0r3 adds rule-based bottleneck allocation to the with-capacity Forward PUSH planning foundation.

The essential transition is:

```text
v0r2:
    capacityを超えたらLotを止める

v0r3:
    capacityを超えた時、どのLotを優先して通すかを決める
```

This is the first step from simple capacity gating toward management-aware allocation planning.

In WOM terms:

```text
v0r2:
    capacity gate

v0r3:
    bottleneck traffic controller
```

The first implementation should remain rule-based, explicit, and testable.