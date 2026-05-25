# Codex Request: Add PSI State Bucket Order Round-Trip Test

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The current WOM repository already has structured PSI state persistence modules:

```text
pysi/io/psi_state_io.py
pysi/io/psi_state_loader.py
```

A design memo has also been added:

```text
docs/design/current_wom_psi_state_persistence_mapping.md
```

Please read this design memo first.

The current persistence path is:

```text
export_psi_state(...)
    ↓
psi_state/
    physical_tree_outbound.json
    physical_tree_inbound.json
    product_tree_outbound.json
    product_tree_inbound.json
    psi_events.parquet
    parameters.json
    metadata.json
    state_hash.txt

load_psi_state(...)
    ↓
physical roots
product-specific PlanNode trees
parameters
metadata
state hash
psi_events attached to product trees
PsiStatePlanEnv
```

This request is to add a focused round-trip test for PSI bucket order.

---

## 2. Problem

The canonical WOM / PySI V0R8 PSI bucket order is:

```python
PSI_S  = 0
PSI_CO = 1
PSI_I  = 2
PSI_P  = 3
```

Conceptually:

```python
node.psi4demand[w] = [S_ids, CO_ids, I_ids, P_ids]
node.psi4supply[w] = [S_ids, CO_ids, I_ids, P_ids]
```

However, `pysi/io/psi_state_io.py` currently has:

```python
BUCKET_CODES = ["P", "CO", "S", "I"]
```

while `pysi/io/psi_state_loader.py` uses:

```python
BUCKET_IDX = {"S": 0, "CO": 1, "I": 2, "P": 3}
```

This may cause bucket order mismatch during export/load round trip.

Example risk:

```text
original psi4demand[w][S]
    exported as bucket = P
    loaded into psi4demand[w][P]
```

That would corrupt PSI state.

This request is to add tests that clearly verify whether round-trip preserves bucket identity.

---

## 3. Main Objective

Add a focused test that verifies:

```text
PlanNode.psi4demand[w][S/CO/I/P]
    ↓
export_psi_state(...)
    ↓
load_psi_state(...)
    ↓
restored PlanNode.psi4demand[w][S/CO/I/P]
```

returns the same Lot_IDs in the same buckets.

If the test fails under current implementation, fix the minimum required bucket mapping issue.

Most likely fix:

```python
BUCKET_CODES = ["S", "CO", "I", "P"]
```

unless the current export logic has another intentional mapping.

---

## 4. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify planning engines.
3. Do not modify run_full_plan.
4. Do not refactor persistence architecture broadly.
5. Do not introduce database persistence changes.
6. Keep this as a small focused round-trip test and minimal fix if needed.
7. Preserve V0R8 PSI semantics:
   - PSI buckets contain Lot_ID lists.
   - Quantity is len(list).
   - Lot attributes live outside PSI buckets.
```

This request is only for PSI state bucket order round-trip correctness.

---

## 5. Files to Inspect

Please inspect:

```text
pysi/io/psi_state_io.py
pysi/io/psi_state_loader.py
```

Key functions:

```text
export_psi_state(...)
collect_psi_events(...)
export_psi_events_parquet(...)
load_psi_state(...)
attach_psi_events_from_parquet(...)
```

Important constants:

```text
BUCKET_CODES
BUCKET_IDX
```

---

## 6. Suggested Test File

Please add:

```text
tests/test_psi_state_bucket_order_roundtrip.py
```

---

## 7. Test Scenario

Create a minimal product-specific PlanNode tree with one product and one node.

The node should have a known `psi4demand` structure.

Example:

```python
node.psi4demand[0][0] = ["LOT_S_001"]
node.psi4demand[0][1] = ["LOT_CO_001"]
node.psi4demand[0][2] = ["LOT_I_001"]
node.psi4demand[0][3] = ["LOT_P_001"]
```

Then call:

```python
export_psi_state(...)
```

to a temporary directory.

Then call:

```python
load_psi_state(...)
```

and verify that the loaded product tree contains:

```python
restored_node.psi4demand[0][0] == ["LOT_S_001"]
restored_node.psi4demand[0][1] == ["LOT_CO_001"]
restored_node.psi4demand[0][2] == ["LOT_I_001"]
restored_node.psi4demand[0][3] == ["LOT_P_001"]
```

---

## 8. Required Test Cases

Please implement at least these tests.

### 8.1 Demand bucket round-trip

```text
S bucket remains S
CO bucket remains CO
I bucket remains I
P bucket remains P
```

### 8.2 Lot_ID list invariant

Verify restored buckets contain `list[str]`, not numeric values.

### 8.3 State hash exists

Verify `state_hash.txt` is created.

### 8.4 psi_events.parquet exists

Verify `psi_events.parquet` is created.

### 8.5 Optional: bucket codes in exported parquet

If easy, read the exported parquet and confirm that bucket labels are:

```text
S
CO
I
P
```

corresponding to the correct original bucket indices.

---

## 9. Minimal Fix Policy

If the round-trip test fails because of bucket ordering, apply the smallest fix.

Expected likely fix in `pysi/io/psi_state_io.py`:

```python
BUCKET_CODES = ["S", "CO", "I", "P"]
```

Do not perform broad refactoring.

After the fix, all round-trip tests should pass.

---

## 10. Test Commands

Please run:

```bat
python -m pytest tests/test_psi_state_bucket_order_roundtrip.py
```

Also run related smoke / adapter tests:

```bat
python -m pytest tests/test_plan_input_plan_node_seeding.py
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

If optional dependencies such as `pyarrow` or `fastparquet` are required for parquet support and not available, please report that clearly.

If parquet dependencies are already available in the environment, use normal parquet round-trip.

---

## 11. Completion Criteria

This request is complete when:

```text
[OK] test_psi_state_bucket_order_roundtrip.py exists
[OK] export_psi_state creates psi_events.parquet
[OK] export_psi_state creates state_hash.txt
[OK] load_psi_state restores product tree
[OK] S bucket round-trips to S
[OK] CO bucket round-trips to CO
[OK] I bucket round-trips to I
[OK] P bucket round-trips to P
[OK] restored buckets contain Lot_ID lists
[OK] no numeric quantity is inserted into PSI buckets
[OK] focused tests pass
```

---

## 12. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Whether the initial round-trip test failed before fix
3. The bucket mapping issue found, if any
4. Minimal fix applied
5. Test commands executed
6. Test results
7. Any limitations or follow-up tasks
```

Please do not proceed into:

```text
PlanningInput persistence
PlanningOutput redesign
inbound/supply full persistence
GUI integration
database persistence
event store redesign
```

This request is only for:

```text
PSI state bucket order round-trip correctness
```