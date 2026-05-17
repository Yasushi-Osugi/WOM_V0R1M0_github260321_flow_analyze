# WOM Plan Input Granularity Adapter v0r3 Design Memo
## PSI Seed Table → Product-Specific PlanNode Seeding

**Version:** v0r3 draft  
**Date:** 2026-05-17  
**Status:** Design memo  
**Target path:** `docs/design/wom_plan_input_granularity_adapter_v0r3_plan_node_seeding.md`

**Related documents:**

- `docs/design/wom_plan_input_granularity_adapter.md`
- `docs/design/wom_plan_input_granularity_adapter_v0r2.md`
- `docs/design/wom_plan_input_granularity_adapter_v0r2_completion.md`
- `docs/design/wom_case_modeling_base_dataset.md`
- `docs/design/case_japanese_rice_crop_year_modeling_addendum.md`
- `docs/design/wom_planning_operations_commands.md`

---

## 1. Purpose

This memo defines **Plan Input Granularity Adapter v0r3**.

v0r1 normalized different input granularities into a canonical weekly plan table.

```text
monthly / weekly / case_weekly input
    ↓
canonical weekly plan table
```

v0r2 generated lot headers and PSI seed records.

```text
canonical weekly plan table
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
in-memory PSI seed table
```

v0r3 connects the in-memory PSI seed table to WOM / PySI V0R8 product-specific `PlanNode` PSI structures.

```text
in-memory PSI seed table
    ↓
product-specific PlanNode.psi4demand / psi4supply
```

The goal of v0r3 is to safely seed generated Lot_IDs into the correct PSI bucket of the correct product-specific planning tree, without confusing planning-layer PlanNodes with physical GUI nodes.

---

## 2. Core Planning Image

The expected WOM planning image is:

```text
Generated Lot_IDs are seeded first into psi4demand[w][S].

Backward Planning propagates these demand lots across
psi4demand[w][S, CO, I, P]
and through the product-specific planning tree.

After demand allocation is completed,
the resulting demand-side plan is copied or bridged into psi4supply.

Forward Planning then moves Lot_IDs across
psi4supply[w][S, CO, I, P]
as supply execution / simulation.
```

This is the core mental model for v0r3.

---

## 3. WOM / PySI V0R8 Data Structure Assumptions

### 3.1 Physical node and PlanNode are different

WOM has at least two node worlds.

```text
Physical layer:
    product-independent GUI / map / NetworkX node world

Planning layer:
    product-specific PlanNode tree world
```

The physical layer is used for map rendering, GUI selection, and network display.

The planning layer is used for PSI planning.

v0r3 must target the planning layer, not the physical GUI layer.

### 3.2 Product-specific PlanNode trees are the PSI target

Conceptually, the planning roots are:

```text
prod_tree_dict_OT[product_name] → outbound planning tree
prod_tree_dict_IN[product_name] → inbound planning tree
```

These product-specific planning trees hold `psi4demand` and `psi4supply`.

v0r3 should not search physical GUI nodes to seed PSI. It should seed product-specific `PlanNode` objects.

### 3.3 PSI bucket structure

The canonical V0R8 PSI structure is:

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

Equivalently:

```python
node.psi4demand[w][0] = S lot_ID list
node.psi4demand[w][1] = CO lot_ID list
node.psi4demand[w][2] = I lot_ID list
node.psi4demand[w][3] = P lot_ID list

node.psi4supply[w][0] = S lot_ID list
node.psi4supply[w][1] = CO lot_ID list
node.psi4supply[w][2] = I lot_ID list
node.psi4supply[w][3] = P lot_ID list
```

### 3.4 PSI buckets hold Lot_ID lists, not quantities

This is the most important invariant.

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

Therefore, v0r3 seeding must extend PSI buckets with `lot_id` values. It must not insert numeric quantities into PSI buckets.

### 3.5 Lot attributes remain outside PSI buckets

PSI buckets contain only Lot_IDs.

Lot attributes remain in:

```text
LotHeader
lot_pool
metadata table
lot attribute dictionary
```

Examples:

```text
crop_year
harvest_week
expiry_week
quality_status
unit cost
origin node
target region
priority
```

---

## 4. v0r3 Scope

### 4.1 In Scope

v0r3 should define and later implement:

```text
1. PlanNode lookup by node_id / node_name
2. conversion from week key to PlanNode week index
3. mapping from PsiSeedRecord layer / bucket to psi4demand / psi4supply bucket
4. safe extension of Lot_ID lists into target PSI bucket
5. validation that target bucket is a list
6. optional dry-run mode
7. result summary for seeded counts
8. focused tests with mock PlanNode objects
```

### 4.2 Out of Scope

v0r3 should not yet:

```text
1. refactor existing S_month / P_month loader
2. modify GUI
3. modify run_full_plan
4. modify existing planning engines
5. run Backward Planning automatically
6. copy psi4demand to psi4supply
7. implement full Rice Case adapter
8. implement database persistence
```

v0r3 should only perform safe PlanNode PSI seeding.

---

## 5. Input and Output

### 5.1 Input

v0r3 consumes:

```text
list[PsiSeedRecord]
list[LotHeader]
product-specific PlanNode tree or node lookup
week index mapping
```

The primary input is:

```python
PsiSeedRecord(
    scenario_id="RICE_AS_IS",
    product_id="BROWN_RICE_STANDARD",
    node_id="DEMAND_HOUSEHOLD_TOKYO",
    week="2026-W40",
    layer="demand",
    bucket="S",
    lot_id="RICE_AS_IS-BROWN_RICE_STANDARD-DEMAND_HOUSEHOLD_TOKYO-2026W40-demand-000001",
    quantity=1.0,
)
```

### 5.2 Output

v0r3 should return a structured seeding result.

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

## 6. Default Seeding Policy

### 6.1 Demand plan seed

The primary default seed is:

```text
plan_type = demand
    ↓
PsiSeedRecord(layer="demand", bucket="S")
    ↓
PlanNode.psi4demand[w][PSI_S].extend(lot_ids)
```

This corresponds to:

```text
Generated Lot_IDs are seeded first into psi4demand[w][S].
```

### 6.2 Supply plan seed

For supply-oriented input, default mapping may be:

```text
plan_type = supply
    ↓
PsiSeedRecord(layer="demand", bucket="P")
    ↓
PlanNode.psi4demand[w][PSI_P].extend(lot_ids)
```

This keeps supply requirements in the demand planning layer before Forward Planning.

### 6.3 Initial inventory seed

For future use:

```text
plan_type = initial_inventory
    ↓
PsiSeedRecord(layer="supply", bucket="I")
    ↓
PlanNode.psi4supply[w][PSI_I].extend(lot_ids)
```

Initial inventory is more sensitive and may be deferred.

---

## 7. Week Key Mapping

### 7.1 Need for week indexer

`PsiSeedRecord.week` may be a string such as:

```text
2026-W40
```

but `PlanNode.psi4demand` is likely a list indexed by integer week position.

Therefore v0r3 needs a week indexer.

Suggested interface:

```python
def week_to_index(week: str | int) -> int:
    ...
```

### 7.2 Simple MVP mapping

For tests, support direct integer weeks and simple map dictionaries.

```python
week_indexer = {
    "2026-W01": 0,
    "2026-W02": 1,
    ...
}
```

### 7.3 No implicit calendar assumptions

v0r3 should not infer the full planning horizon unless a week indexer is provided.

This avoids hidden calendar bugs.

---

## 8. PlanNode Lookup

### 8.1 Purpose

Find target PlanNode from `PsiSeedRecord.node_id`.

Suggested input:

```python
plan_node_lookup: dict[str, Any]
```

where:

```python
plan_node_lookup[node_id] = plan_node
```

### 8.2 Future tree traversal helper

Future v0r3 implementation may provide:

```python
def build_plan_node_lookup(root) -> dict[str, Any]:
    ...
```

This should traverse product-specific PlanNode tree.

It should not traverse physical GUI nodes.

---

## 9. PSI Bucket Mapping

### 9.1 Bucket constants

Define or reuse:

```python
PSI_BUCKET_INDEX = {
    "S": 0,
    "CO": 1,
    "I": 2,
    "P": 3,
}
```

### 9.2 Layer mapping

```text
layer = demand:
    target attribute = psi4demand

layer = supply:
    target attribute = psi4supply
```

Invalid layer should raise `ValueError` or be recorded as an invalid seed, depending on implementation policy.

Invalid bucket should raise `ValueError` or be recorded as an invalid seed, depending on implementation policy.

For MVP tests, either approach is acceptable if deterministic and documented.

---

## 10. Safe PSI Seeding Function

Suggested function:

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
1. for each seed record:
2. find PlanNode by node_id
3. convert week key to week index
4. resolve target layer psi4demand / psi4supply
5. resolve target bucket index
6. validate target bucket is list
7. if dry_run:
       record what would be seeded
   else:
       append lot_id to target bucket list
8. return PlanNodeSeedingResult
```

---

## 11. Safety Rules

### 11.1 Do not overwrite existing bucket contents

The function should append Lot_IDs.

Correct:

```python
target_bucket.extend(new_lot_ids)
```

Incorrect:

```python
target_bucket = new_lot_ids
```

### 11.2 Do not insert quantities

Correct:

```python
target_bucket.append(seed_record.lot_id)
```

Incorrect:

```python
target_bucket.append(seed_record.quantity)
```

### 11.3 Do not create unknown nodes silently

If `node_id` does not exist:

```text
record missing_node_id
skip seed record
```

Do not create a physical or planning node automatically.

### 11.4 Validate week range

If week index is out of range:

```text
record invalid week
skip seed record
```

Do not extend the PSI horizon silently unless explicitly configured.

### 11.5 Dry-run mode

Dry-run should report seeding counts without mutating PlanNode.

This is useful before attaching the adapter to existing loaders.

---

## 12. Mock PlanNode for Tests

v0r3 tests should use a minimal mock PlanNode.

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

This avoids needing the full WOM tree for v0r3 tests.

---

## 13. Example: Demand Seed

Input seed record:

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
plan_node.psi4demand[0][PSI_S] == ["LOT_DEMAND_001"]
```

---

## 14. Example: Supply Requirement Seed

Input seed record:

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
plan_node.psi4demand[week_indexer["2026-W40"]][PSI_P] == ["LOT_SUPPLY_001"]
```

---

## 15. Relationship to Backward and Forward Planning

v0r3 only seeds initial lots.

The subsequent planning flow is:

```text
1. Seed demand lots into psi4demand[w][S]
2. Backward Planning propagates through psi4demand buckets and product-specific planning tree
3. Demand allocation result is copied / bridged into psi4supply
4. Forward Planning moves lots across psi4supply buckets
```

v0r3 should not run Backward or Forward Planning.

---

## 16. Suggested Files

Please add or update:

```text
pysi/adapters/plan_node_seeding.py
tests/test_plan_input_plan_node_seeding.py
```

Optionally update:

```text
pysi/adapters/__init__.py
```

Do not modify:

```text
existing monthly loader
GUI
planning engines
```

---

## 17. Test Policy

### 17.1 Required tests

```text
1. demand/S seed goes to psi4demand[w][0]
2. demand/P seed goes to psi4demand[w][3]
3. supply/I seed goes to psi4supply[w][2]
4. multiple seed records preserve lot order
5. dry_run does not mutate PlanNode
6. missing node is recorded and skipped
7. invalid bucket raises or records error
8. seed table values are Lot_IDs, not quantities
9. no existing bucket contents are overwritten
```

### 17.2 Rice boundary test

Use:

```text
2026-W40
2026-W41
```

with a week indexer.

Confirm that the correct week indices are used and lot IDs are seeded into the expected weeks.

---

## 18. Completion Criteria

v0r3 is complete when:

```text
[OK] plan_node_seeding.py exists
[OK] apply_psi_seed_records_to_plan_nodes works
[OK] demand/S seeds psi4demand[w][S]
[OK] demand/P seeds psi4demand[w][P]
[OK] supply/I seeds psi4supply[w][I]
[OK] dry_run mode works
[OK] missing node handling works
[OK] lot order is preserved
[OK] no numeric quantities are inserted into PSI buckets
[OK] focused tests pass
[OK] no GUI / loader / planning engine modifications
```

---

## 19. Future Milestones

### v0r4: existing loader refactor

Refactor existing monthly loader so that it uses:

```text
monthly input
    ↓
canonical weekly plan table
    ↓
Lot_ID generation
    ↓
PSI seeding
```

### v0r5: Rice Case direct weekly input integration

Connect Rice Case weekly master dataset to PlanNode PSI seeding.

### v0r6: GUI selection / case loading

Allow GUI to select a case dataset and load it through the adapter.

---

## 20. Summary

v0r3 is the first point where the Plan Input Granularity Adapter touches WOM planning structures.

The essential rule is:

```text
Generated Lot_IDs are seeded first into psi4demand[w][S].

Backward Planning propagates these demand lots across psi4demand[w][S, CO, I, P]
and through the product-specific planning tree.

After demand allocation is completed,
the resulting demand-side plan is copied or bridged into psi4supply.

Forward Planning then moves Lot_IDs across psi4supply[w][S, CO, I, P]
as supply execution / simulation.
```

v0r3 must remain safe:

```text
target product-specific PlanNode tree
append Lot_IDs
do not insert quantities
do not overwrite buckets
do not touch physical GUI nodes
do not run planning engines
```

This completes the bridge from adapter seed table to V0R8-compatible PSI list initialization.
