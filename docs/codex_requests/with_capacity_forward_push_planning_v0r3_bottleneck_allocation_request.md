# Codex Request: Implement With-Capacity PSI Engine v0r3 Bottleneck Allocation

## 1. Background

We are working on:

```text
feature/with-capacity-psi-engine-v0r2
```

The v0r2 foundation has already been completed:

```text
v0r2-m1:
    standalone Forward PUSH with Capacity planner MVP

v0r2-m2:
    capacity_master.csv loader
    capacity lookup
    CapacityUsage / CapacityViolation
    usage / violation CSV export

v0r2-m3:
    PSI list adapter
    node.psi4demand -> capacity gate -> node.psi4supply
```

The v0r2 completion memo has also been added.

The current request is for:

```text
v0r3:
    bottleneck allocation rule enhancement
```

Please read the design memo first:

```text
docs/design/with_capacity_forward_push_planning_v0r3_bottleneck_allocation.md
```

Please also inspect the existing v0r2 implementations:

```text
pysi/planning/forward_push_with_capacity_planner.py
pysi/planning/capacity_master.py
pysi/planning/capacity_io.py
pysi/planning/forward_push_with_capacity_psi_adapter.py
```

---

## 2. Main Objective

Implement a small bottleneck allocation layer for Forward PUSH with Capacity Planning.

v0r2 answered this question:

```text
capacityを超えたら、Lotを止められるか？
```

v0r3 should answer the next question:

```text
capacityを超えた時、どのLotを優先して通すか？
```

The key principle is:

```text
Allocation rule is applied only at bottleneck nodes.
```

A bottleneck exists when:

```text
requested lots > available capacity
```

for a given:

```text
node
product
week
capacity_type
```

If capacity is sufficient, the existing v0r2 behavior should remain unchanged.

---

## 3. Most Important Constraints

Please follow these constraints:

```text
1. Do not modify the original Forward PUSH planner behavior.
2. Preserve all v0r2-m1 / m2 / m3 behavior by default.
3. Keep FIFO / first-in-first-pushed as the default rule.
4. Apply allocation logic only when a bottleneck is detected.
5. Do not implement GUI integration.
6. Do not implement PULL integration.
7. Do not implement costing / profit simulation.
8. Do not implement multi-bottleneck global optimization.
9. Keep the implementation small and testable.
```

This request is for local bottleneck allocation, not global optimization.

---

## 4. Design Concept

The current v0r2 planner effectively accepts lots in input order.

That means the current default allocation rule is:

```text
FIFO / first-in-first-pushed
```

v0r3 should make this allocation rule explicit and extensible.

Conceptual flow:

```text
requested lots
    ↓
capacity lookup
    ↓
bottleneck check
    ↓
if not bottleneck:
    keep original order
if bottleneck:
    apply allocation rule
    reorder requested lots
    pass reordered lots to existing capacity split logic
    accepted lots = lots within capacity
    blocked lots = remaining lots
```

The actual capacity split logic should continue to rely on existing v0r2 planner behavior.

v0r3 should mainly decide the order of requested lots before the capacity gate.

---

## 5. Suggested Files

Please add:

```text
pysi/planning/bottleneck_allocation.py
pysi/runners/run_forward_push_with_capacity_allocation_smoke.py
tests/test_bottleneck_allocation.py
```

Please update only if necessary:

```text
pysi/planning/forward_push_with_capacity_psi_adapter.py
```

Please avoid broad refactoring.

---

## 6. Allocation Rules

Please implement the following minimum rules.

### 6.1 FIFO

Rule name:

```text
FIFO
```

Behavior:

```text
keep the input lot order
```

This must remain the default behavior.

### 6.2 LOT_PRIORITY

Rule name:

```text
LOT_PRIORITY
```

Behavior:

```text
sort lots by priority value
lower priority number means higher priority
```

Supported lot representations:

```python
{"lot_id": "LOT001", "priority": 10}
{"lot_id": "LOT002", "allocation_priority": 20}
"LOT003"
```

For dict lots, use priority fields if available.

Priority field lookup order:

```text
allocation_priority
priority
```

For string lot IDs without priority, use default priority:

```text
100
```

Sorting should be stable.

Expected behavior:

```text
priority 1 lots are accepted before priority 10 lots
lots with same priority keep original relative order
```

### 6.3 Optional: DUE_WEEK_PRIORITY

If simple to implement, add:

```text
DUE_WEEK_PRIORITY
```

Behavior:

```text
sort by due_week if present
earlier due_week first
missing due_week last
stable within same due_week
```

If this becomes too large, leave it as a follow-up.

---

## 7. Data Structures

Please implement small dataclasses.

### 7.1 AllocationRule

```python
@dataclass
class AllocationRule:
    rule_name: str = "FIFO"
    default_priority: int = 100
    descending: bool = False
```

For v0r3, `rule_name` can support:

```text
FIFO
LOT_PRIORITY
DUE_WEEK_PRIORITY
```

### 7.2 BottleneckAllocationResult

```python
@dataclass
class BottleneckAllocationResult:
    node_name: str
    product_name: str
    week: str | int
    capacity_type: str
    rule_name: str
    requested_qty: int
    capacity_qty: int | None
    is_bottleneck: bool
    ordered_lots: list = field(default_factory=list)
    accepted_lots: list = field(default_factory=list)
    blocked_lots: list = field(default_factory=list)
```

---

## 8. Suggested Functions

### 8.1 Lot ID helper

Reuse or implement safely:

```python
def _lot_id(lot: Any) -> str:
    if isinstance(lot, dict):
        return str(lot.get("lot_id", lot))
    return str(lot)
```

### 8.2 Lot priority helper

```python
def get_lot_priority(lot: Any, default_priority: int = 100) -> int:
    ...
```

Expected behavior:

```text
dict with allocation_priority:
    use allocation_priority

dict with priority:
    use priority

string lot:
    use default_priority
```

If parsing fails, use default priority.

### 8.3 Allocation function

```python
def order_lots_for_allocation(
    lots: list,
    rule: AllocationRule | None = None,
) -> list:
    ...
```

Expected behavior:

```text
rule is None:
    FIFO

rule_name == "FIFO":
    keep input order

rule_name == "LOT_PRIORITY":
    stable sort by priority ascending

rule_name == "DUE_WEEK_PRIORITY":
    stable sort by due_week ascending, missing last
```

### 8.4 Bottleneck allocation function

```python
def allocate_lots_at_bottleneck(
    *,
    node_name: str,
    product_name: str,
    week: str | int,
    capacity_type: str,
    requested_lots: list,
    capacity_qty: int | None,
    rule: AllocationRule | None = None,
) -> BottleneckAllocationResult:
    ...
```

Expected behavior:

```text
capacity_qty is None:
    not bottleneck
    all lots accepted
    no blocked lots

requested_qty <= capacity_qty:
    not bottleneck
    all lots accepted
    no blocked lots

requested_qty > capacity_qty:
    bottleneck
    apply allocation rule
    accepted lots = ordered_lots[:capacity_qty]
    blocked lots = ordered_lots[capacity_qty:]
```

Zero capacity behavior:

```text
capacity_qty = 0
requested_qty > 0
    bottleneck
    accepted lots = []
    blocked lots = all requested lots
```

---

## 9. Integration with v0r2-m3 PSI Adapter

Please integrate allocation into the PSI adapter in a backward-compatible way.

Recommended approach:

```python
def apply_capacity_to_node_psi_bucket(
    *,
    node,
    scenario_id: str,
    tree_side: str,
    product_name: str,
    week: str | int,
    capacity_type: str,
    capacity_lookup: dict,
    allocation_rule: AllocationRule | None = None,
):
    ...
```

Default:

```text
allocation_rule = None
```

should behave exactly like v0r2 FIFO behavior.

When a capacity record exists and requested lots exceed capacity:

```text
1. apply allocation rule to requested lots
2. pass ordered lots to existing capacity wrapper/planner
3. accepted lots are appended to node.psi4supply
4. blocked lots are recorded
```

Do not delete lots from node.psi4demand.

---

## 10. Missing Capacity Policy

Keep the existing v0r2 policy:

```text
missing capacity means unlimited capacity
```

Therefore:

```text
capacity record missing:
    no bottleneck allocation required
    all requested lots accepted
    no violation emitted by default
```

---

## 11. Non-Bottleneck Policy

If capacity exists but is sufficient:

```text
requested_qty <= capacity_qty
```

then:

```text
do not reorder lots
accept all lots in original order
no violation
```

This avoids unnecessary changes when there is no bottleneck.

---

## 12. Bottleneck Policy

If capacity exists and is insufficient:

```text
requested_qty > capacity_qty
```

then:

```text
apply allocation rule
write accepted lots to psi4supply
record blocked lots
record carryover candidates
emit existing CapacityViolation
```

v0r3 should not introduce automatic future-week rescheduling.

Blocked lots should remain recorded as carryover candidates.

---

## 13. Smoke Runner

Please add:

```text
pysi/runners/run_forward_push_with_capacity_allocation_smoke.py
```

Smoke scenario:

```text
node: MOM_CHINA
product: IPHONE_NM_2028_BASE
week: 2026-W01
capacity_type: P
requested lots: 120
capacity: 100
rule: LOT_PRIORITY
```

Create lots with mixed priorities, for example:

```python
lots = [
    {"lot_id": "LOW_001", "priority": 90},
    {"lot_id": "HIGH_001", "priority": 1},
    {"lot_id": "MID_001", "priority": 50},
    ...
]
```

Expected output should show:

```text
=== with capacity allocation smoke ===
rule: LOT_PRIORITY
requested lots: 120
capacity: 100
accepted lots: 100
blocked lots: 20
highest priority lots accepted first: true
```

The smoke runner should not require GUI.

Optional output:

```text
outputs/capacity/forward_push_with_capacity_allocation_usage.csv
outputs/capacity/forward_push_with_capacity_allocation_violation.csv
```

If output CSVs are generated, please reuse v0r2-m2 exporters.

---

## 14. Tests

Please add:

```text
tests/test_bottleneck_allocation.py
```

Required tests:

```text
1. FIFO keeps input order
2. LOT_PRIORITY sorts lower priority number first
3. LOT_PRIORITY keeps stable order for equal priorities
4. string lot IDs use default priority
5. missing priority uses default priority
6. capacity None means unlimited capacity
7. capacity sufficient means not bottleneck and no reordering
8. capacity shortage applies allocation and splits accepted / blocked
9. zero capacity blocks all requested lots
10. PSI adapter with LOT_PRIORITY writes high-priority lots to psi4supply first
11. original psi4demand remains unchanged
12. v0r2-m1 / m2 / m3 tests still pass
```

Please also keep these tests passing:

```bat
python -m pytest tests/test_forward_push_with_capacity_psi_adapter.py
python -m pytest tests/test_capacity_master_io.py
python -m pytest tests/test_forward_push_with_capacity_planner.py
```

---

## 15. Test Commands to Run

Please run at minimum:

```bat
python -m pytest tests/test_bottleneck_allocation.py
python -m pytest tests/test_forward_push_with_capacity_psi_adapter.py
python -m pytest tests/test_capacity_master_io.py
python -m pytest tests/test_forward_push_with_capacity_planner.py
python -m pysi.runners.run_forward_push_with_capacity_allocation_smoke
```

If reasonable, also run:

```bat
python -m pytest -q -k "capacity"
```

If `-k "capacity"` fails due to unrelated optional dependencies such as pulp, matplotlib, dash, or unrelated existing test-side errors, report it separately and do not treat it as a v0r3 failure.

---

## 16. Completion Criteria

This request is complete when:

```text
[OK] bottleneck allocation module exists
[OK] FIFO allocation rule exists
[OK] LOT_PRIORITY allocation rule exists
[OK] stable sorting is preserved
[OK] allocation applies only at bottleneck
[OK] non-bottleneck lots remain in original order
[OK] missing capacity remains unlimited
[OK] zero capacity blocks all lots
[OK] PSI adapter can use allocation rule
[OK] high-priority lots are accepted before low-priority lots under capacity shortage
[OK] blocked lots are recorded separately
[OK] smoke runner works
[OK] tests pass
[OK] v0r2 behavior remains compatible by default
```

---

## 17. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. Test commands executed
4. Test results
5. Any limitations or follow-up tasks
```

Please do not proceed into GUI integration, PULL integration, costing integration, or global optimization.

This request is only for:

```text
v0r3 bottleneck allocation rule enhancement
```