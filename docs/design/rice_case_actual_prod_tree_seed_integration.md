# Rice Case Actual Product-Specific PlanNode Tree Seed Integration Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-17  
**Status:** Design memo  
**Target path:** `docs/design/rice_case_actual_prod_tree_seed_integration.md`

**Related design documents:**

- `docs/design/rice_case_real_plannode_seed_integration_design.md`
- `docs/design/rice_case_weekly_input_to_plannode_seed_integration.md`
- `docs/design/rice_case_weekly_input_to_plannode_seed_integration_completion.md`
- `docs/design/wom_plan_input_granularity_adapter.md`
- `docs/design/wom_plan_input_granularity_adapter_v0r2.md`
- `docs/design/wom_plan_input_granularity_adapter_v0r3_plan_node_seeding.md`
- `docs/design/wom_plan_input_granularity_adapter_v0r3_completion.md`
- `docs/design/case_japanese_rice_crop_year_modeling_addendum.md`

---

## 1. Purpose

This memo defines the next integration stage for the Japanese Rice Case and the WOM Plan Input Granularity Adapter.

The previous stage verified that Rice weekly input can be seeded into a **real-like PlanNode tree**.

This memo defines how to connect that same pipeline to the **actual product-specific WOM / PySI V0R8 PlanNode trees**.

The target flow is:

```text
Rice Case weekly supply / demand data
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
actual product-specific PlanNode tree
    ↓
PlanNode.psi4demand / psi4supply
```

This is still a controlled input-layer integration.

It should **not** run the full Backward Planning or Forward Planning sequence automatically.

---

## 2. Background

The Plan Input Granularity Adapter has been implemented through v0r3.

```text
v0r1:
    monthly / weekly / case_weekly input
        ↓
    canonical WeeklyPlanRow

v0r2:
    WeeklyPlanRow
        ↓
    LotHeader
        ↓
    PsiSeedRecord
        ↓
    in-memory PSI seed table

v0r3:
    PsiSeedRecord
        ↓
    PlanNode.psi4demand / psi4supply
```

The Rice Case has also been integrated up to a real-like tree.

```text
Rice weekly input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
real-like PlanNode tree
```

The next step is actual WOM product-specific tree integration:

```text
prod_tree_dict_OT[product_name]
prod_tree_dict_IN[product_name]
```

---

## 3. Critical WOM / PySI V0R8 Assumptions

### 3.1 Physical node layer and planning layer are different

WOM has at least two node worlds.

```text
Physical layer:
    product-independent GUI / map / NetworkX node world

Planning layer:
    product-specific PlanNode tree world
```

This integration must target the **planning layer**.

It must not seed physical GUI nodes.

### 3.2 Product-specific PlanNode trees are the target

The target trees are:

```text
prod_tree_dict_OT[product_name] → outbound planning tree
prod_tree_dict_IN[product_name] → inbound planning tree
```

These PlanNode trees hold `psi4demand` and `psi4supply`.

### 3.3 PSI bucket structure

The V0R8 canonical PSI structure is:

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

### 3.4 PSI buckets contain Lot_ID lists, not quantities

This remains the most important invariant.

Correct:

```python
node.psi4demand[w][PSI_S] = ["LOT_A", "LOT_B", "LOT_C"]
```

Incorrect:

```python
node.psi4demand[w][PSI_S] = 3
```

Quantity remains:

```python
quantity = len(node.psi4demand[w][bucket])
```

Lot attributes remain outside PSI buckets.

---

## 4. Integration Scope

### 4.1 In Scope

This integration should define and later implement:

```text
1. Resolve actual product-specific outbound / inbound planning roots.
2. Build PlanNode lookup from prod_tree_dict_OT / prod_tree_dict_IN.
3. Map Rice node IDs to actual PlanNode names.
4. Convert Rice weekly data to WeeklyPlanRows.
5. Generate LotHeaders and PsiSeedRecords.
6. Apply PsiSeedRecords to actual product-specific PlanNode.psi4demand / psi4supply.
7. Preserve Rice W40 / W41 crop-year boundary.
8. Provide dry-run mode.
9. Provide safe commit mode.
10. Report missing nodes, invalid weeks, invalid buckets.
11. Provide focused smoke test.
```

### 4.2 Out of Scope

This integration should not:

```text
1. Modify GUI.
2. Modify run_full_plan.
3. Refactor existing S_month / P_month loader.
4. Run Backward Planning automatically.
5. Run Forward Planning automatically.
6. Copy psi4demand to psi4supply.
7. Implement full Rice supply chain network.
8. Implement Management Issue Generation.
9. Implement database persistence.
```

This stage only seeds actual product-specific PlanNode PSI buckets.

---

## 5. Design Strategy

### 5.1 Reuse existing adapter modules

Do not duplicate the existing adapter pipeline.

Reuse:

```text
pysi/cases/japanese_rice/rice_plan_input_integration.py
pysi/cases/japanese_rice/rice_real_plannode_seed_integration.py
pysi/adapters/weekly_plan_table.py
pysi/adapters/lot_generation.py
pysi/adapters/psi_seed.py
pysi/adapters/plan_input_pipeline.py
pysi/adapters/plan_node_seeding.py
```

### 5.2 Use explicit root resolution

The integration should receive either:

```text
prod_tree_dict_OT
prod_tree_dict_IN
product_name
```

or explicit roots:

```text
outbound_root
inbound_root
```

No implicit global lookup should be used in MVP.

### 5.3 Dry-run first

The integration must support:

```text
dry_run=True
```

Dry-run should report what would be seeded without mutating the actual PlanNode trees.

Actual mutation requires:

```text
dry_run=False
```

---

## 6. Root Resolution

### 6.1 Product dictionary based resolution

Suggested function:

```python
def resolve_product_plan_roots(
    *,
    product_name: str,
    prod_tree_dict_OT: dict | None = None,
    prod_tree_dict_IN: dict | None = None,
    outbound_root=None,
    inbound_root=None,
) -> tuple[object | None, object | None]:
    ...
```

Resolution order:

```text
1. explicit outbound_root / inbound_root if provided
2. prod_tree_dict_OT[product_name] / prod_tree_dict_IN[product_name]
3. None if not found
```

### 6.2 Missing root handling

If no root is found:

```text
record missing root
skip seeding
return result with warnings/errors
```

Do not create new product trees automatically.

---

## 7. PlanNode Lookup

### 7.1 Build lookup from actual tree

Reuse or adapt:

```python
build_plan_node_lookup_from_tree(root)
build_plan_node_lookup_from_roots(roots)
```

Expected behavior:

```text
1. traverse root and descendants
2. read node.name
3. return {node.name: node}
```

### 7.2 Duplicate node names

If duplicate names exist across outbound / inbound roots, use a deterministic policy.

Recommended MVP:

```text
outbound root first
inbound root second
first root wins
duplicates recorded as warning
```

The duplicate policy should be visible in the result object.

---

## 8. Rice Node Mapping

### 8.1 Exact match policy for MVP

Use exact match first:

```text
Rice node_id == PlanNode.name
```

### 8.2 Missing node handling

If a Rice node is not found:

```text
record missing_node_id
skip the corresponding seed records
```

Do not create PlanNodes automatically.

### 8.3 Future mapping table

Future versions may use:

```text
rice_node_id → wom_plan_node_name
```

from a case adapter mapping master.

This is out of scope for MVP.

---

## 9. Week Indexing

### 9.1 Rice horizon

Rice Case v2 uses:

```text
2026-W01 to 2028-W52
```

Expected:

```text
156 weeks
```

### 9.2 Week indexer

Reuse:

```python
build_rice_week_indexer(2026, 2028)
```

Expected mappings:

```python
week_indexer["2026-W01"] == 0
week_indexer["2026-W40"] == 39
week_indexer["2026-W41"] == 40
week_indexer["2027-W01"] == 52
week_indexer["2028-W52"] == 155
```

### 9.3 Horizon validation

If actual PlanNode PSI arrays have fewer than 156 weeks:

```text
record invalid week or horizon error
skip affected seed records
do not silently extend
```

---

## 10. Seeding Policy

### 10.1 Demand rows

Rice demand rows should seed:

```text
WeeklyPlanRow(plan_type="demand")
    ↓
PsiSeedRecord(layer="demand", bucket="S")
    ↓
PlanNode.psi4demand[w][S]
```

### 10.2 Supply / harvest rows

Rice supply rows should seed:

```text
WeeklyPlanRow(plan_type="supply")
    ↓
PsiSeedRecord(layer="demand", bucket="P")
    ↓
PlanNode.psi4demand[w][P]
```

This keeps harvest / supply requirement in demand planning space until Backward Planning is run.

### 10.3 Future initial inventory

Future versions may seed old-crop carryover as:

```text
PsiSeedRecord(layer="supply", bucket="I")
```

or a dedicated initial inventory structure.

This is out of scope unless already available safely.

---

## 11. Proposed Main Function

Suggested function:

```python
def seed_rice_weekly_input_to_actual_product_plan_nodes(
    *,
    case_data,
    product_name: str,
    prod_tree_dict_OT: dict | None = None,
    prod_tree_dict_IN: dict | None = None,
    outbound_root=None,
    inbound_root=None,
    dry_run: bool = True,
) -> RiceActualPlanNodeSeedResult:
    ...
```

Expected behavior:

```text
1. resolve outbound / inbound product-specific roots
2. build PlanNode lookup from roots
3. build Rice WeeklyPlanRows
4. build Rice row attributes
5. generate LotHeaders and PsiSeedRecords
6. apply PsiSeedRecords to PlanNode lookup
7. return structured result
```

---

## 12. Result Object

Suggested dataclass:

```python
@dataclass
class RiceActualPlanNodeSeedResult:
    scenario_id: str
    product_name: str
    weekly_rows_count: int = 0
    lot_count: int = 0
    seed_record_count: int = 0
    plan_node_seeded_count: int = 0
    missing_roots: list[str] = field(default_factory=list)
    missing_node_ids: list[str] = field(default_factory=list)
    duplicate_node_ids: list[str] = field(default_factory=list)
    invalid_weeks: list[dict] = field(default_factory=list)
    dry_run: bool = True
```

---

## 13. Smoke Test Strategy

### 13.1 No full WOM environment required

The first implementation may use a minimal product-specific tree built with a real PlanNode-like class, as long as the function signature and flow match actual `prod_tree_dict_OT / IN` integration.

### 13.2 Minimal tree

Use a small tree with real target node names:

```text
ROOT_RICE
    ├── PRODUCER_NIIGATA
    ├── DEMAND_HOUSEHOLD_TOKYO
    └── DEMAND_FOOD_SERVICE_TOKYO
```

Each node must have:

```text
name
children
psi4demand
psi4supply
```

with 156 weeks.

### 13.3 Optional real environment smoke

If the repository has a safe helper to build product-specific PlanNode trees without GUI, a smoke test may use it.

But the MVP should not require GUI.

---

## 14. Tests

Add:

```text
tests/test_japanese_rice_actual_prod_tree_seed_integration.py
```

Required tests:

```text
1. resolve_product_plan_roots works with explicit roots.
2. resolve_product_plan_roots works with prod_tree_dict_OT / IN.
3. PlanNode lookup can be built from actual-like roots.
4. Rice weekly input seeds actual-like PlanNodes.
5. demand rows seed to psi4demand[w][S].
6. supply rows seed to psi4demand[w][P].
7. W40 / W41 boundary is preserved.
8. dry-run does not mutate roots.
9. missing root is reported.
10. missing node is reported.
11. PSI buckets contain Lot_ID lists, not quantities.
```

---

## 15. Existing Tests to Run

Run:

```bat
python -m pytest tests/test_japanese_rice_actual_prod_tree_seed_integration.py
python -m pytest tests/test_japanese_rice_real_plannode_seed_integration.py
python -m pytest tests/test_japanese_rice_plan_input_integration.py
python -m pytest tests/test_plan_input_plan_node_seeding.py
python -m pytest tests/test_plan_input_pipeline.py
python -m pytest tests/test_japanese_rice_case_smoke.py
```

Optional:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

---

## 16. Completion Criteria

This integration is complete when:

```text
[OK] actual product tree integration function exists
[OK] explicit root resolution works
[OK] prod_tree_dict_OT / IN root resolution works
[OK] Rice weekly input can seed actual-like product PlanNode tree
[OK] demand rows seed to psi4demand[w][S]
[OK] supply rows seed to psi4demand[w][P]
[OK] W40 / W41 boundary is preserved
[OK] dry-run works
[OK] missing roots / nodes are reported
[OK] PSI buckets contain Lot_ID lists, not quantities
[OK] no GUI / run_full_plan / loader / planning engine changes
[OK] focused tests pass
```

---

## 17. Future Work

### 17.1 Run Backward Planning after seeding

Future flow:

```text
actual PlanNode PSI seed
    ↓
Backward Planning
```

### 17.2 Demand-to-supply bridge

Future flow:

```text
psi4demand
    ↓
psi4supply
```

### 17.3 Forward Planning

Future flow:

```text
psi4supply
    ↓
Forward simulation
```

### 17.4 Existing loader refactor

Future flow:

```text
S_month / P_month
    ↓
canonical WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
PlanNode seeding
```

---

## 18. Summary

This design moves Rice Case from real-like PlanNode integration toward actual product-specific WOM planning tree integration.

Target flow:

```text
Rice Case weekly input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
actual product-specific PlanNode.psi4demand / psi4supply
```

The key safety rules remain:

```text
seed product-specific PlanNode trees
do not seed physical GUI nodes
append Lot_IDs only
do not insert quantities
do not overwrite buckets
do not run planning engines
```

This is the final safety bridge before running actual Backward / Forward Planning on Rice Case seeded data.
````