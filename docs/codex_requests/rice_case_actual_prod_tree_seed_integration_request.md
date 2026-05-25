# Codex Request: Implement Rice Case Actual Product Tree Seed Integration

## 1. Background

We are working on branch:

```text
feature/rice-case-actual-plannode-seed-v0r1
```

The following design memo has already been added:

```text
docs/design/rice_case_actual_prod_tree_seed_integration.md
```

Please read this design memo first.

The previous Rice Case integration stages are complete:

```text
Rice weekly input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
mock PlanNode.psi4demand

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

This request is the next controlled step:

```text
Rice weekly input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
actual product-specific PlanNode tree
```

The target WOM / PySI V0R8 structures are:

```text
prod_tree_dict_OT[product_name]
prod_tree_dict_IN[product_name]
```

This request should still avoid running Backward Planning or Forward Planning.

---

## 2. Main Objective

Implement a safe adapter that seeds Rice Case weekly input into actual product-specific PlanNode trees.

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
actual product-specific PlanNode.psi4demand / psi4supply
```

This request should prove that the Rice Case can seed real WOM product-specific planning trees using the new Plan Input Granularity Adapter pipeline.

---

## 3. Critical WOM / PySI V0R8 Assumptions

Please preserve these assumptions.

### 3.1 Physical node layer and planning PlanNode layer are different

WOM has two node worlds:

```text
Physical layer:
    product-independent GUI / map / NetworkX node world

Planning layer:
    product-specific PlanNode tree world
```

This request targets the planning layer only.

Do not seed physical GUI nodes.

---

### 3.2 Product-specific PlanNode tree is the target

The actual target is:

```text
prod_tree_dict_OT[product_name]
prod_tree_dict_IN[product_name]
```

These product-specific planning trees hold:

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

### 3.3 PSI buckets must contain Lot_ID lists, not numeric quantities

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

Lot attributes should remain outside PSI buckets, in `LotHeader`, `lot_pool`, or metadata structures.

---

## 4. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan.
3. Do not modify existing S_month / P_month loader.
4. Do not run Backward Planning.
5. Do not run Forward Planning.
6. Do not implement demand-to-supply bridge.
7. Do not implement full Rice supply chain network simulation.
8. Do not implement Management Issue Generation.
9. Do not create physical GUI nodes.
10. Keep this as a safe additive integration layer.
```

This request is only for:

```text
Rice Case weekly input to actual product-specific PlanNode seed integration
```

---

## 5. Existing Modules to Reuse

Please reuse existing modules.

```text
pysi/adapters/weekly_plan_table.py
pysi/adapters/lot_generation.py
pysi/adapters/psi_seed.py
pysi/adapters/plan_input_pipeline.py
pysi/adapters/plan_node_seeding.py

pysi/cases/japanese_rice/rice_case_dataset.py
pysi/cases/japanese_rice/rice_case_adapter.py
pysi/cases/japanese_rice/rice_plan_input_integration.py
pysi/cases/japanese_rice/rice_real_plannode_seed_integration.py
```

Do not duplicate existing logic for:

```text
WeeklyPlanRow
LotHeader
PsiSeedRecord
Lot_ID generation
PlanNode PSI seeding
Rice week indexer
```

---

## 6. Suggested Files

Please add:

```text
pysi/cases/japanese_rice/rice_actual_prod_tree_seed_integration.py
tests/test_japanese_rice_actual_prod_tree_seed_integration.py
```

Please update only if useful:

```text
pysi/cases/japanese_rice/__init__.py
```

Optional smoke runner:

```text
pysi/runners/run_japanese_rice_actual_prod_tree_seed_smoke.py
```

If adding the optional runner is too much for this MVP, focused tests are sufficient.

---

## 7. Root Resolution

Please implement product-specific root resolution.

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

If no root is found:

```text
record missing root
skip seeding
return structured result with warnings/errors
```

Do not create new product trees automatically.

---

## 8. PlanNode Lookup

Please reuse or implement lookup helpers.

Suggested functions:

```python
def build_plan_node_lookup_from_tree(root) -> dict[str, object]:
    ...

def build_plan_node_lookup_from_roots(roots: list[object]) -> dict[str, object]:
    ...
```

Expected behavior:

```text
1. traverse root and descendants
2. read node.name
3. return {node.name: node}
```

Duplicate handling policy:

```text
outbound root first
inbound root second
first root wins
duplicates recorded as warning if easy
```

Do not traverse physical GUI nodes.

---

## 9. Rice Node Mapping

For the MVP, use exact name matching:

```text
Rice node_id == PlanNode.name
```

If a Rice node is not found:

```text
record missing_node_id
skip corresponding seed records
```

Do not create PlanNodes automatically.

Future versions may use:

```text
rice_node_id → wom_plan_node_name
```

from adapter mapping master, but this is out of scope for this request.

---

## 10. Week Indexing

Rice Case v2 uses:

```text
2026-W01 to 2028-W52
```

Expected total weeks:

```text
156 weeks
```

Please reuse:

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

If actual PlanNode PSI arrays have fewer than 156 weeks:

```text
record invalid week or horizon error
skip affected seed records
do not silently extend
```

---

## 11. Seeding Policy

### 11.1 Demand rows

Rice demand rows should seed:

```text
WeeklyPlanRow(plan_type="demand")
    ↓
PsiSeedRecord(layer="demand", bucket="S")
    ↓
PlanNode.psi4demand[w][S]
```

### 11.2 Supply / harvest rows

Rice supply rows should seed:

```text
WeeklyPlanRow(plan_type="supply")
    ↓
PsiSeedRecord(layer="demand", bucket="P")
    ↓
PlanNode.psi4demand[w][P]
```

This keeps harvest / supply requirements in demand planning space until Backward Planning is run.

### 11.3 Future initial inventory

Future versions may seed old-crop carryover as:

```text
PsiSeedRecord(layer="supply", bucket="I")
```

or a dedicated initial inventory structure.

This is out of scope unless already available safely.

---

## 12. Main Function

Please implement:

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

## 13. Result Dataclass

Please implement:

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

## 14. Test Strategy

### 14.1 No full WOM environment required

The first implementation may use a minimal product-specific tree built with a real PlanNode-like class, as long as the function signature and flow match actual `prod_tree_dict_OT / IN` integration.

### 14.2 Minimal actual-like tree

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

### 14.3 Optional real environment smoke

If the repository has a safe helper to build product-specific PlanNode trees without GUI, a smoke test may use it.

But the MVP should not require GUI.

---

## 15. Required Tests

Please add:

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

## 16. Test Commands

Please run:

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

If broader tests fail due to unrelated optional dependencies, report separately.

---

## 17. Completion Criteria

This request is complete when:

```text
[OK] rice_actual_prod_tree_seed_integration.py exists
[OK] actual product tree integration function exists
[OK] explicit root resolution works
[OK] prod_tree_dict_OT / IN root resolution works
[OK] PlanNode lookup can be built from roots
[OK] Rice weekly input can seed actual-like product PlanNode tree
[OK] demand rows seed to psi4demand[w][S]
[OK] supply rows seed to psi4demand[w][P]
[OK] W40 / W41 boundary is preserved
[OK] dry-run works
[OK] missing roots / nodes are reported
[OK] PSI buckets contain Lot_ID lists, not quantities
[OK] no GUI changes
[OK] no run_full_plan changes
[OK] no loader changes
[OK] no planning engine changes
[OK] focused tests pass
```

---

## 18. Expected Response from Codex

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
demand-to-supply bridge
existing monthly loader refactor
GUI integration
database persistence
Management Issue Generation
```

This request is only for:

```text
Rice Case actual product-specific PlanNode seed integration
```