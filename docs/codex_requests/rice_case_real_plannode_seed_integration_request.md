# Codex Request: Implement Rice Case Real-Like PlanNode Seed Integration

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/rice_case_real_plannode_seed_integration_design.md
```

Please read this design memo first.

The current adapter pipeline is already implemented and tested:

```text
Plan Input Granularity Adapter v0r1:
  monthly / weekly / case_weekly input
      ↓
  canonical WeeklyPlanRow

Plan Input Granularity Adapter v0r2:
  WeeklyPlanRow
      ↓
  LotHeader
      ↓
  PsiSeedRecord
      ↓
  in-memory PSI seed table

Plan Input Granularity Adapter v0r3:
  PsiSeedRecord
      ↓
  PlanNode.psi4demand / psi4supply
```

The Rice Case weekly input integration has also been implemented and tested:

```text
Rice weekly supply / demand data
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
mock PlanNode.psi4demand
```

Current related files include:

```text
pysi/adapters/weekly_plan_table.py
pysi/adapters/lot_generation.py
pysi/adapters/psi_seed.py
pysi/adapters/plan_input_pipeline.py
pysi/adapters/plan_node_seeding.py

pysi/cases/japanese_rice/rice_case_dataset.py
pysi/cases/japanese_rice/rice_case_adapter.py
pysi/cases/japanese_rice/rice_plan_input_integration.py

tests/test_plan_input_granularity_adapter.py
tests/test_plan_input_lot_generation.py
tests/test_plan_input_psi_seed.py
tests/test_plan_input_pipeline.py
tests/test_plan_input_plan_node_seeding.py
tests/test_japanese_rice_plan_input_integration.py
tests/test_japanese_rice_case_smoke.py
```

This request is to move one step further:

```text
Rice weekly input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
real-like product-specific PlanNode tree
```

This is still a controlled integration test.  
It should not run the full WOM Planning Engine.

---

## 2. Main Objective

Implement a minimal, safe integration layer that seeds Rice Case weekly input into a **real-like product-specific PlanNode tree**.

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
real-like PlanNode.psi4demand / psi4supply
```

The purpose is to verify that the Plan Input Adapter pipeline can seed Lot_IDs into a tree-shaped planning structure, not just isolated mock nodes.

This request should still avoid full `prod_tree_dict_OT / prod_tree_dict_IN` integration.

---

## 3. Critical WOM / PySI V0R8 Assumptions

Please preserve the following assumptions.

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

### 3.2 Product-specific PlanNode tree is the final target

The future production target is:

```text
prod_tree_dict_OT[product_name]
prod_tree_dict_IN[product_name]
```

This request does not need to connect to those production dictionaries yet.

For MVP, create and use a **real-like PlanNode tree** with:

```text
name
children
psi4demand
psi4supply
```

---

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

---

### 3.4 PSI buckets must contain Lot_ID lists, not numeric quantities

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

Lot attributes should remain in `LotHeader.attributes` or other metadata structures, not inside PSI buckets.

---

## 4. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan.
3. Do not modify existing monthly S_month / P_month loader.
4. Do not run Backward Planning.
5. Do not run Forward Planning.
6. Do not implement demand-to-supply bridge.
7. Do not implement full Rice supply chain network simulation.
8. Do not implement Management Issue Generation.
9. Do not connect to real prod_tree_dict_OT / prod_tree_dict_IN yet.
10. Keep this as a safe additive integration layer.
```

This request is only for:

```text
Rice Case weekly input to real-like PlanNode seed integration
```

---

## 5. Suggested Files

Please add:

```text
pysi/cases/japanese_rice/rice_real_plannode_seed_integration.py
tests/test_japanese_rice_real_plannode_seed_integration.py
```

Please update only if useful:

```text
pysi/cases/japanese_rice/__init__.py
```

Optional smoke runner:

```text
pysi/runners/run_japanese_rice_real_plannode_seed_smoke.py
```

If adding the optional runner is too much, tests are sufficient for this MVP.

---

## 6. Real-Like PlanNode

Please define a minimal real-like PlanNode for tests.

Suggested dataclass:

```python
from dataclasses import dataclass, field


@dataclass
class RealLikePlanNode:
    name: str
    children: list = field(default_factory=list)
    psi4demand: list = field(default_factory=list)
    psi4supply: list = field(default_factory=list)
```

Suggested helper:

```python
def make_real_like_plan_node(name: str, weeks: int) -> RealLikePlanNode:
    return RealLikePlanNode(
        name=name,
        children=[],
        psi4demand=[[[], [], [], []] for _ in range(weeks)],
        psi4supply=[[[], [], [], []] for _ in range(weeks)],
    )
```

Suggested tree for tests:

```text
ROOT_RICE
    ├── PRODUCER_NIIGATA
    ├── DEMAND_HOUSEHOLD_TOKYO
    └── DEMAND_FOOD_SERVICE_TOKYO
```

This should be tree-shaped, not only a flat dictionary.

---

## 7. PlanNode Lookup

Please implement:

```python
def build_plan_node_lookup_from_tree(root) -> dict[str, object]:
    ...
```

Expected behavior:

```text
1. traverse root
2. traverse children recursively
3. collect node.name
4. return {node.name: node}
```

Please also implement if useful:

```python
def build_plan_node_lookup_from_roots(roots: list[object]) -> dict[str, object]:
    ...
```

MVP duplicate handling:

```text
first root wins
```

Do not traverse physical GUI nodes.

This helper is for planning-layer PlanNode-like trees.

---

## 8. Rice Node Matching

For the MVP, use exact name matching:

```text
Rice node_id == PlanNode.name
```

If no matching PlanNode exists:

```text
record missing_node_id
skip seed record
```

Do not create PlanNodes automatically.

Future versions may use a mapping table:

```text
rice_node_id → wom_plan_node_name
```

but that is out of scope for this request.

---

## 9. Rice Week Indexer

Please reuse or implement:

```python
def build_rice_week_indexer(
    start_year: int = 2026,
    end_year: int = 2028,
) -> dict[str, int]:
    ...
```

Expected mappings:

```python
week_indexer["2026-W01"] == 0
week_indexer["2026-W40"] == 39
week_indexer["2026-W41"] == 40
week_indexer["2027-W01"] == 52
week_indexer["2028-W52"] == 155
```

The PlanNode should have 156 weekly rows.

Do not silently extend the PSI horizon.

---

## 10. Rice Weekly Data Pipeline

Please reuse existing helper functions from:

```text
pysi/cases/japanese_rice/rice_plan_input_integration.py
pysi/adapters/plan_input_pipeline.py
pysi/adapters/plan_node_seeding.py
```

The integration should orchestrate existing pieces.

Expected pipeline:

```text
Rice case data
    ↓
build_rice_weekly_plan_rows(...)
    ↓
build_rice_row_attributes(...)
    ↓
generate LotHeader / PsiSeedRecord
    ↓
build real-like PlanNode lookup
    ↓
apply_psi_seed_records_to_plan_nodes(...)
```

Do not duplicate the lot generation or PSI seed logic.

---

## 11. Proposed Integration Function

Please implement:

```python
def seed_rice_weekly_input_to_real_like_plan_tree(
    *,
    case_data,
    product_name: str,
    roots: list[object],
    dry_run: bool = True,
) -> RiceRealPlanNodeSeedResult:
    ...
```

Expected behavior:

```text
1. build Rice WeeklyPlanRows
2. build Rice row attributes
3. generate LotHeader and PsiSeedRecord
4. build PlanNode lookup from root(s)
5. apply PsiSeedRecords to PlanNodes
6. return structured result
```

---

## 12. Suggested Result Dataclass

Please implement:

```python
@dataclass
class RiceRealPlanNodeSeedResult:
    scenario_id: str
    product_name: str
    weekly_rows_count: int = 0
    lot_count: int = 0
    seed_record_count: int = 0
    plan_node_seeded_count: int = 0
    missing_node_ids: list[str] = field(default_factory=list)
    invalid_weeks: list[dict] = field(default_factory=list)
    dry_run: bool = True
```

---

## 13. Target Seeding Rules

### 13.1 Demand rows

Rice demand rows should seed:

```text
WeeklyPlanRow(plan_type="demand")
    ↓
PsiSeedRecord(layer="demand", bucket="S")
    ↓
PlanNode.psi4demand[w][S]
```

### 13.2 Supply / harvest rows

Rice supply / harvest rows should seed:

```text
WeeklyPlanRow(plan_type="supply")
    ↓
PsiSeedRecord(layer="demand", bucket="P")
    ↓
PlanNode.psi4demand[w][P]
```

This keeps supply-side planning requirements in demand planning space before Backward Planning is run.

---

## 14. Dry Run

Please support `dry_run=True`.

Expected behavior:

```text
dry_run=True:
    do not mutate PlanNodes
    still return expected seeded counts / keys

dry_run=False:
    append Lot_IDs into PlanNode PSI buckets
```

---

## 15. Optional Smoke Runner

If simple, add:

```text
pysi/runners/run_japanese_rice_real_plannode_seed_smoke.py
```

Expected output:

```text
=== Japanese Rice real-like PlanNode seed smoke ===
scenario: RICE_AS_IS
product: PACKAGED_RICE_STANDARD
horizon: 2026-W01..2028-W52

weekly rows: N
generated lots: N
seed records: N
seeded lots: N
missing nodes: 0
invalid weeks: 0

demand/S seeded: N
demand/P seeded: N

boundary:
  2026-W40 index: 39
  2026-W41 index: 40
```

This runner is optional. Focused tests are required.

---

## 16. Required Tests

Please add:

```text
tests/test_japanese_rice_real_plannode_seed_integration.py
```

Required tests:

```text
1. build_plan_node_lookup_from_tree finds child nodes.
2. Rice weekly rows seed into a real-like PlanNode tree.
3. demand rows seed to psi4demand[w][S].
4. supply rows seed to psi4demand[w][P].
5. W40 / W41 boundary is preserved.
6. dry_run does not mutate PlanNodes.
7. missing node is recorded and skipped.
8. PSI buckets contain Lot_ID lists, not numeric quantities.
9. existing Rice plan input integration tests still pass.
```

---

## 17. Test Commands

Please run:

```bat
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

## 18. Completion Criteria

This request is complete when:

```text
[OK] rice_real_plannode_seed_integration.py exists
[OK] real-like PlanNode lookup can be built
[OK] Rice weekly input can seed PlanNode.psi4demand
[OK] demand rows seed to S bucket
[OK] supply rows seed to P bucket
[OK] W40 / W41 boundary is preserved
[OK] dry-run works
[OK] missing node handling works
[OK] PSI buckets contain Lot_ID lists, not numeric quantities
[OK] no GUI changes
[OK] no run_full_plan changes
[OK] no loader changes
[OK] no planning engine changes
[OK] focused tests pass
```

---

## 19. Expected Response from Codex

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
actual prod_tree_dict_OT / prod_tree_dict_IN integration
Backward Planning execution
Forward Planning execution
demand-to-supply bridge
existing monthly loader refactor
GUI integration
database persistence
```

This request is only for:

```text
Rice Case weekly input to real-like PlanNode seed integration