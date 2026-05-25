# With-Capacity PSI Engine v0r2 Completion Memo
## Forward PUSH with Capacity Planning MVP Completion

## 1. Purpose

This memo summarizes the completion status of:

```text
with-capacity PSI engine v0r2
```

The purpose of v0r2 was to move from capacity observation to capacity-constrained Forward PUSH planning.

v0r1 provided the foundation:

```text
capacity report / hook / runner foundation
```

v0r2 implemented the first executable planning foundation:

```text
Forward PUSH with Capacity Planning MVP
```

The core concept of v0r2 is:

```text
capacityを超えたら流せない
```

In other words, WOM now has the first foundation for distinguishing:

```text
Original Forward PUSH Planning
    = ideal plan without capacity constraints

Forward PUSH with Capacity Planning
    = executable plan under capacity constraints
```

---

## 2. Branch

The work was implemented on:

```text
feature/with-capacity-psi-engine-v0r2
```

Latest relevant commits:

```text
d0e8551 Add v0r2-m3 PSI list adapter for forward push with capacity
dec67c7 Add v0r2-m3 PSI list integration design and Codex request
adb02cf Add v0r2-m2 capacity master I/O and exports
a7e4e9e Split v0r2-m2 capacity IO design and Codex request
465d5d8 Add v0r2-m2 capacity IO design and Codex request
c0c953c Add forward push with capacity planner MVP
```

---

## 3. v0r2 Milestone Structure

v0r2 was completed in three sub-milestones:

```text
v0r2-m1:
    standalone Forward PUSH with Capacity planner MVP

v0r2-m2:
    capacity master loader and usage / violation CSV output

v0r2-m3:
    PSI list integration adapter
```

This staged approach was used to avoid jumping directly from capacity observation to full allocation optimization.

---

## 4. v0r2-m1 Completion Summary

### 4.1 Objective

v0r2-m1 implemented the standalone core planner logic.

The planner splits requested lots into:

```text
accepted lots
blocked lots
```

based on available capacity.

### 4.2 Implemented Features

```text
[OK] Forward PUSH with Capacity planner MVP
[OK] capacity sufficient case
[OK] capacity shortage case
[OK] zero capacity case
[OK] missing capacity = unlimited capacity
[OK] blocked_lot_ids safe handling for dict lots and string lot IDs
[OK] smoke runner
[OK] focused tests
```

### 4.3 Key Behavior

Example:

```text
requested lots: 120
capacity: 100
accepted lots: 100
blocked lots: 20
capacity issue: CAPACITY_SHORTAGE
```

### 4.4 Meaning

v0r2-m1 established the core rule:

```text
capacity内のLotだけを通す
capacity超過Lotはblockedとして記録する
```

This is the first minimal “capacity gate” logic.

---

## 5. v0r2-m2 Completion Summary

### 5.1 Objective

v0r2-m2 implemented the capacity data I/O layer.

The goal was to make the standalone planner data-ready by adding:

```text
capacity_master.csv loader
capacity lookup
CapacityUsage
CapacityViolation
usage / violation CSV export
```

### 5.2 Implemented Files

```text
pysi/master_data/capacity_master_sample.csv
pysi/planning/capacity_master.py
pysi/planning/capacity_io.py
pysi/runners/run_forward_push_with_capacity_io_smoke.py
tests/test_capacity_master_io.py
```

### 5.3 Implemented Features

```text
[OK] CapacityMasterRecord
[OK] capacity_master.csv loader
[OK] validation for capacity_type = P / S / I
[OK] validation for cap_mode = soft / hard
[OK] exact capacity lookup
[OK] product wildcard lookup using product_name="*"
[OK] missing capacity = unlimited capacity
[OK] CapacityUsage
[OK] CapacityViolation
[OK] usage CSV export
[OK] violation CSV export
[OK] pipe-separated lot ID output
[OK] smoke runner
[OK] focused tests
```

### 5.4 Key Policy

The missing capacity policy is:

```text
capacity master record found:
    apply capacity check

capacity master record not found:
    treat as unlimited capacity
    do not block lots by default
```

This preserves compatibility with existing WOM scenarios that do not yet define full capacity data.

### 5.5 Meaning

v0r2-m2 connected the capacity gate to master data and report output.

In WOM terms:

```text
capacity制約の入力マスター
capacity使用状況の記録
capacity超過の記録
```

became available as a reusable data layer.

---

## 6. v0r2-m3 Completion Summary

### 6.1 Objective

v0r2-m3 connected the m1 planner and m2 capacity I/O layer to WOM-like PSI list structures.

The target structure is:

```python
node.psi4demand[week][S/CO/I/P] = [lot_id, ...]
node.psi4supply[week][S/CO/I/P] = [lot_id, ...]
```

### 6.2 Implemented Files

```text
pysi/planning/forward_push_with_capacity_psi_adapter.py
pysi/runners/run_forward_push_with_capacity_psi_smoke.py
tests/test_forward_push_with_capacity_psi_adapter.py
```

### 6.3 Implemented Features

```text
[OK] PSI_BUCKET_INDEX mapping
[OK] get_psi_lots helper
[OK] append_psi_lots helper
[OK] apply_capacity_to_node_psi_bucket
[OK] run_forward_push_with_capacity_psi_lists
[OK] ForwardPushWithCapacityPsiResult
[OK] accepted_lots_by_key
[OK] blocked_lots_by_key
[OK] carryover_lots_by_key
[OK] usage_records
[OK] violation_records
[OK] P bucket support
[OK] S bucket support
[OK] smoke runner
[OK] focused tests
```

### 6.4 Key Behavior

The adapter reads requested lots from:

```text
node.psi4demand
```

and writes capacity-accepted lots into:

```text
node.psi4supply
```

The adapter does not delete lots from `psi4demand`.

This preserves the original demand-placed state for inspection and comparison.

### 6.5 Smoke Result

Example:

```text
node: MOM_CHINA
week: 2026-W01
capacity type: P
requested lots: 120
capacity: 100
accepted lots in psi4supply: 100
blocked lots: 20
```

### 6.6 Meaning

v0r2-m3 connected the capacity gate to WOM PSI list flow.

In WOM terms:

```text
psi4demandに置かれたLot listを読み、
capacity内のLotだけをpsi4supplyへ流し、
capacity超過Lotをblocked / carryover候補として記録する
```

This is the first PSI-connected with-capacity Forward PUSH planning adapter.

---

## 7. Test Summary

The following focused tests and smoke runners were used during v0r2 completion.

### v0r2-m1

```bat
python -m pytest tests/test_forward_push_with_capacity_planner.py
python -m pysi.runners.run_forward_push_with_capacity_smoke
```

### v0r2-m2

```bat
python -m pytest tests/test_capacity_master_io.py
python -m pytest tests/test_forward_push_with_capacity_planner.py
python -m pysi.runners.run_forward_push_with_capacity_io_smoke
```

### v0r2-m3

```bat
python -m pytest tests/test_forward_push_with_capacity_psi_adapter.py
python -m pytest tests/test_capacity_master_io.py
python -m pytest tests/test_forward_push_with_capacity_planner.py
python -m pysi.runners.run_forward_push_with_capacity_psi_smoke
```

Known note:

```text
python -m pytest -q -k "capacity"
```

may fail in the current environment due to unrelated optional dependencies or unrelated existing tests.

Examples include:

```text
pulp
matplotlib
dash
unrelated cost master test-side errors
```

These are not considered v0r2 blocker issues.

---

## 8. What v0r2 Completed

v0r2 completed the following foundation:

```text
[OK] standalone capacity-aware lot split logic
[OK] capacity master input
[OK] capacity lookup
[OK] usage / violation output
[OK] PSI list adapter
[OK] accepted lots written to psi4supply
[OK] blocked lots recorded separately
[OK] missing capacity remains unlimited
[OK] original Forward PUSH planner remains unchanged
```

Therefore, v0r2 can be considered complete as:

```text
Forward PUSH with Capacity Planning MVP foundation
```

---

## 9. What v0r2 Did Not Implement

v0r2 intentionally did not implement:

```text
advanced allocation rule
market priority
product priority
customer priority
profit priority
due-date priority
strategic priority
multi-bottleneck optimization
automatic carryover rescheduling
PULL integration
GUI integration
management cockpit integration
costing / profit simulation integration
lane alternative selection
TOC-style throughput optimization
```

These remain future milestones.

---

## 10. Boundary Between v0r2 and v0r3

v0r2 answers the question:

```text
capacityを超えたら、Lotを止められるか？
```

v0r3 should answer the next question:

```text
capacityを超えた時、どのLotを優先して通すか？
```

Therefore, v0r3 should focus on:

```text
bottleneck allocation rule enhancement
```

v0r3 should not revisit the basic capacity gate unless required.

---

## 11. Recommended v0r3 Direction

The recommended v0r3 scope is:

```text
Allocation rule enhancement at bottleneck nodes
```

Candidate rules:

```text
first-in, first-pushed
market priority
product priority
customer priority
due-date priority
profit priority
strategic priority
manual override priority
```

The key principle remains:

```text
Allocation rule is needed only at bottleneck nodes.
```

A bottleneck node is detected when:

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

Non-bottleneck nodes should continue normal pass-through behavior.

---

## 12. Conceptual Completion Statement

With v0r2 completed, WOM now has the first executable foundation for:

```text
理想計画:
    Original Forward PUSH Planning

実行可能計画:
    Forward PUSH with Capacity Planning
```

This is an important step because WOM can now begin to compare:

```text
what we want to do
```

with:

```text
what we can actually do under capacity constraints
```

In supply chain planning terms, v0r2 installed the first operational capacity gate into WOM’s PSI flow.

In WOM implementation terms:

```text
m1:
    capacity gate logic

m2:
    capacity master and report I/O

m3:
    PSI list connection
```

This completes the v0r2 foundation and prepares the project for v0r3 bottleneck allocation planning.