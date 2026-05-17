# Codex Request: Implement WOM Plan Input Granularity Adapter v0r3 PlanNode Seeding

## 1. Background

We are working on branch:

```text
feature/plan-input-granularity-adapter-v0r1
```

The following design documents already exist:

```text
docs/design/wom_plan_input_granularity_adapter.md
docs/design/wom_plan_input_granularity_adapter_v0r2.md
docs/design/wom_plan_input_granularity_adapter_v0r2_completion.md
docs/design/wom_plan_input_granularity_adapter_v0r3_plan_node_seeding.md
```

Please read the v0r3 design memo first:

```text
docs/design/wom_plan_input_granularity_adapter_v0r3_plan_node_seeding.md
```

The current v0r1 / v0r2 implementation already provides:

```text
pysi/adapters/calendar_445.py
pysi/adapters/weekly_plan_table.py
pysi/adapters/plan_input_granularity.py
pysi/adapters/lot_generation.py
pysi/adapters/psi_seed.py
pysi/adapters/plan_input_pipeline.py
```

v0r1 implemented:

```text
monthly / weekly / case_weekly input
    ↓
canonical WeeklyPlanRow
```

v0r2 implemented:

```text
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
in-memory PSI seed table
```

This request is for v0r3:

```text
PsiSeedRecord / seed table
    ↓
product-specific PlanNode.psi4demand / psi4supply
```

---

## 2. Main Objective

Implement a safe PlanNode seeding adapter.

The adapter should take `PsiSeedRecord` records and append their `lot_id` values into the correct PSI bucket of product-specific PlanNode objects.

The core concept is:

```text
Generated Lot_IDs are seeded first into psi4demand[w][S].

Backward Planning propagates these demand lots across psi4demand[w][S, CO, I, P]
and through the product-specific planning tree.

After demand allocation is completed,
the resulting demand-side plan is copied or bridged into psi4supply.

Forward Planning then moves Lot_IDs across psi4supply[w][S, CO, I, P]
as supply execution / simulation.
```

This request should only implement safe seeding.

It should not run Backward Planning or Forward Planning.

---

## 3. Critical WOM / PySI V0R8 Assumptions

Please preserve the following assumptions.

### 3.1 Physical node layer and planning PlanNode layer are different

WOM has at least two node worlds:

```text
Physical layer:
    product-independent GUI / map / NetworkX node world

Planning layer:
    product-specific PlanNode tree world
```

This request targets the planning layer only.

Do not use physical GUI nodes as the PSI seeding target.

---

### 3.2 PSI source of truth is the product-specific PlanNode tree

The product-specific PlanNode tree holds the PSI state.

Conceptually:

```text
prod_tree_dict_OT[product_name] → outbound planning tree
prod_tree_dict_IN[product_name] → inbound planning tree
```

The final target for this adapter is the product-specific PlanNode, not the physical map node.

---

### 3.3 PSI bucket structure

The canonical V0R8 PSI bucket structure is:

```python
node.psi4demand[w] = [S_ids, CO_ids, I_ids, P_ids]
node.psi4supply[w] = [S_ids, CO_ids, I_ids, P_ids]
```

Bucket index convention:

```python
PSI_S  = 0
PSI_CO = 1
PSI_I  = 2
PSI_P  = 3
```

---

### 3.4 PSI buckets must contain Lot_ID lists, not numeric quantities

This is the most important rule.

Correct:

```python
node.psi4demand[w][PSI_S] = ["LOT_A", "LOT_B", "LOT_C"]
```

Incorrect:

```python
node.psi4demand[w][PSI_S] = 3
```

Quantity is calculated as:

```python
quantity = len(node.psi4demand[w][bucket])
quantity = len(node.psi4supply[w][bucket])
```

Please ensure no numeric quantity is inserted into PSI buckets.

---

### 3.5 Lot attributes stay outside PSI buckets

PSI buckets hold only Lot_IDs.

Lot attributes remain in:

```text
LotHeader
lot_pool
metadata table
lot attribute dictionary
```

---

## 4. Important Constraints

Please follow these constraints:

```text
1. Do not modify existing monthly WOM loaders.
2. Do not modify GUI.
3. Do not modify existing planning engines.
4. Do not modify run_full_plan.
5. Do not run Backward Planning.
6. Do not run Forward Planning.
7. Do not copy psi4demand to psi4supply in this request.
8. Do not create or mutate physical GUI nodes.
9. Only append Lot_ID strings to target PSI bucket lists.
10. Keep the implementation additive and testable.
```

This request should remain a safe adapter layer.

---

## 5. Files to Add or Update

Please add:

```text
pysi/adapters/plan_node_seeding.py
tests/test_plan_input_plan_node_seeding.py
```

Please update if useful:

```text
pysi/adapters/__init__.py
```

Do not modify:

```text
existing monthly loaders
GUI
planning engines
```

---

## 6. Existing Types to Reuse

Please reuse `PsiSeedRecord` from:

```text
pysi/adapters/psi_seed.py
```

Conceptual structure:

```python
@dataclass
class PsiSeedRecord:
    scenario_id: str
    product_id: str
    node_id: str
    week: str
    layer: str
    bucket: str
    lot_id: str
    quantity: float
    source_id: str = ""
```

---

## 7. PlanNodeSeedingResult

Please implement a result dataclass.

Suggested:

```python
from dataclasses import dataclass, field


@dataclass
class PlanNodeSeedingResult:
    scenario_id: str
    product_id: str
    seeded_count: int = 0
    skipped_count: int = 0
    missing_node_ids: list[str] = field(default_factory=list)
    invalid_weeks: list[dict] = field(default_factory=list)
    invalid_buckets: list[dict] = field(default_factory=list)
    seeded_by_key: dict[tuple, int] = field(default_factory=dict)
    dry_run: bool = False
```

Suggested `seeded_by_key` key:

```python
(node_id, week, layer, bucket)
```

---

## 8. PSI Bucket Constants

Please define or reuse bucket constants.

```python
PSI_BUCKET_INDEX = {
    "S": 0,
    "CO": 1,
    "I": 2,
    "P": 3,
}
```

Layer mapping:

```text
layer = demand:
    target attribute = psi4demand

layer = supply:
    target attribute = psi4supply
```

Invalid layer should be handled deterministically.

Invalid bucket should be handled deterministically.

For MVP, either raising `ValueError` or recording invalid bucket in result is acceptable, but tests should match the chosen behavior.

Recommended MVP behavior:

```text
invalid layer:
    raise ValueError

invalid bucket:
    raise ValueError
```

Missing node / invalid week should be recorded and skipped.

---

## 9. Week Indexing

`PsiSeedRecord.week` may be a string such as:

```text
2026-W40
```

But PlanNode PSI lists are indexed by integer position.

Please support a `week_indexer`.

Accepted forms:

```python
week_indexer: dict[str, int]
```

or callable:

```python
week_indexer(week) -> int
```

For tests, use dict mapping.

Example:

```python
week_indexer = {
    "2026-W01": 0,
    "2026-W02": 1,
    "2026-W40": 39,
    "2026-W41": 40,
}
```

Do not infer full planning horizon implicitly.

Do not silently extend PSI lists if week index is out of range.

---

## 10. PlanNode Lookup

Input should be:

```python
plan_node_lookup: dict[str, Any]
```

where:

```python
plan_node_lookup[node_id] = plan_node
```

Please add optional helper if useful:

```python
def build_plan_node_lookup(root) -> dict[str, Any]:
    ...
```

If implemented, this helper should traverse product-specific PlanNode tree.

It should not traverse physical GUI node tree.

---

## 11. Main Function

Please implement:

```python
def apply_psi_seed_records_to_plan_nodes(
    seed_records: list[PsiSeedRecord],
    *,
    plan_node_lookup: dict[str, Any],
    week_indexer: dict[str, int] | callable,
    dry_run: bool = False,
) -> PlanNodeSeedingResult:
    ...
```

Expected behavior:

```text
1. For each seed record:
2. Find PlanNode by node_id.
3. Convert week key to week index.
4. Resolve target layer:
       demand → psi4demand
       supply → psi4supply
5. Resolve bucket:
       S / CO / I / P
6. Validate target bucket is list.
7. If dry_run:
       record what would be seeded, but do not mutate.
8. If not dry_run:
       append seed_record.lot_id to target bucket list.
9. Return PlanNodeSeedingResult.
```

---

## 12. Safety Rules

### 12.1 Do not overwrite existing bucket contents

Correct:

```python
target_bucket.append(seed_record.lot_id)
```

or grouped:

```python
target_bucket.extend(lot_ids)
```

Incorrect:

```python
target_bucket = lot_ids
```

---

### 12.2 Do not insert quantities

Correct:

```python
target_bucket.append(seed_record.lot_id)
```

Incorrect:

```python
target_bucket.append(seed_record.quantity)
```

---

### 12.3 Missing node handling

If `node_id` does not exist:

```text
record missing_node_id
skip seed record
```

Do not create a node.

---

### 12.4 Invalid week handling

If week is not in week_indexer or index is out of range:

```text
record invalid_weeks
skip seed record
```

Do not extend PSI horizon automatically.

---

### 12.5 Dry-run mode

If `dry_run=True`:

```text
do not mutate PlanNode
return counts and keys that would be seeded
```

---

## 13. Mock PlanNode for Tests

Use a minimal mock PlanNode in tests.

```python
@dataclass
class MockPlanNode:
    name: str
    psi4demand: list
    psi4supply: list
```

Helper:

```python
def make_mock_plan_node(name: str, weeks: int) -> MockPlanNode:
    return MockPlanNode(
        name=name,
        psi4demand=[[[], [], [], []] for _ in range(weeks)],
        psi4supply=[[[], [], [], []] for _ in range(weeks)],
    )
```

---

## 14. Required Tests

Please add:

```text
tests/test_plan_input_plan_node_seeding.py
```

Required tests:

```text
1. demand/S seed goes to psi4demand[w][0].
2. demand/P seed goes to psi4demand[w][3].
3. supply/I seed goes to psi4supply[w][2].
4. multiple seed records preserve lot order.
5. dry_run does not mutate PlanNode.
6. missing node is recorded and skipped.
7. invalid week is recorded and skipped.
8. invalid bucket raises ValueError or is recorded deterministically.
9. existing bucket contents are not overwritten.
10. PSI buckets contain Lot_IDs, not numeric quantities.
```

---

## 15. Rice Boundary Test

Please include a Rice boundary test.

Use week indexer:

```python
week_indexer = {
    "2026-W40": 39,
    "2026-W41": 40,
}
```

Seed records:

```text
2026-W40 demand/S
2026-W41 demand/S
```

Expected:

```text
2026-W40 seed goes to index 39
2026-W41 seed goes to index 40
```

This confirms that the W40 / W41 boundary is preserved.

---

## 16. Example: Demand Seed

Input:

```python
PsiSeedRecord(
    scenario_id="RICE_AS_IS",
    product_id="PACKAGED_RICE_STANDARD",
    node_id="DEMAND_HOUSEHOLD_TOKYO",
    week="2026-W01",
    layer="demand",
    bucket="S",
    lot_id="LOT_DEMAND_001",
    quantity=1.0,
)
```

After seeding:

```python
plan_node.psi4demand[0][0] == ["LOT_DEMAND_001"]
```

---

## 17. Example: Supply Requirement Seed

Input:

```python
PsiSeedRecord(
    scenario_id="RICE_AS_IS",
    product_id="BROWN_RICE_STANDARD",
    node_id="PRODUCER_NIIGATA",
    week="2026-W40",
    layer="demand",
    bucket="P",
    lot_id="LOT_SUPPLY_001",
    quantity=1.0,
)
```

After seeding:

```python
plan_node.psi4demand[39][3] == ["LOT_SUPPLY_001"]
```

---

## 18. Test Commands

Please run:

```bat
python -m pytest tests/test_plan_input_plan_node_seeding.py
```

Also run existing adapter tests:

```bat
python -m pytest tests/test_plan_input_lot_generation.py
python -m pytest tests/test_plan_input_psi_seed.py
python -m pytest tests/test_plan_input_pipeline.py
python -m pytest tests/test_plan_input_granularity_adapter.py
```

Optional compatibility checks:

```bat
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

If broader tests fail due to unrelated optional dependencies, report separately.

---

## 19. Completion Criteria

This request is complete when:

```text
[OK] plan_node_seeding.py exists
[OK] apply_psi_seed_records_to_plan_nodes works
[OK] demand/S seeds psi4demand[w][S]
[OK] demand/P seeds psi4demand[w][P]
[OK] supply/I seeds psi4supply[w][I]
[OK] dry_run mode works
[OK] missing node handling works
[OK] invalid week handling works
[OK] lot order is preserved
[OK] no numeric quantities are inserted into PSI buckets
[OK] focused tests pass
[OK] existing v0r1/v0r2 adapter tests pass
[OK] no GUI / loader / planning engine modifications
```

---

## 20. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. Test commands executed
4. Test results
5. Any limitations or follow-up tasks
```

Please do not proceed into:

```text
Backward Planning execution
Forward Planning execution
psi4demand to psi4supply copy
existing monthly loader refactor
GUI integration
Rice Case adapter refactor
database persistence
```

This request is only for:

```text
Plan Input Granularity Adapter v0r3:
    PsiSeedRecord
        ↓
    product-specific PlanNode.psi4demand / psi4supply seeding
```