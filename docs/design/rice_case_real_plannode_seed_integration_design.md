# Rice Case Real PlanNode Seed Integration Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-17  
**Status:** Design memo  
**Target path:** `docs/design/rice_case_real_plannode_seed_integration_design.md`

**Related design documents:**

- `docs/design/rice_case_weekly_input_to_plannode_seed_integration.md`
- `docs/design/rice_case_weekly_input_to_plannode_seed_integration_completion.md`
- `docs/design/wom_plan_input_granularity_adapter.md`
- `docs/design/wom_plan_input_granularity_adapter_v0r2.md`
- `docs/design/wom_plan_input_granularity_adapter_v0r3_plan_node_seeding.md`
- `docs/design/wom_plan_input_granularity_adapter_v0r3_completion.md`
- `docs/design/case_japanese_rice_crop_year_modeling_addendum.md`

---

## 1. Purpose

This memo defines the next integration step for the Japanese Rice Case.

The previous integration verified that Rice weekly input can flow through:

```text
Rice Case weekly supply / demand data
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
mock PlanNode.psi4demand
```

This memo defines the next target:

```text
Rice Case weekly supply / demand data
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
real product-specific PlanNode.psi4demand / psi4supply
```

The goal is to move from mock PlanNode verification to a controlled real-like PlanNode tree integration.

This is still not full WOM planning execution.

---

## 2. Background

The Plan Input Granularity Adapter pipeline has been completed through v0r3.

```text
v0r1:
    monthly / weekly / case_weekly
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

The Rice Case integration has also confirmed:

```text
Rice weekly data
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
mock PlanNode.psi4demand
```

The next step is to seed a small real product-specific PlanNode tree or real-like PlanNode tree with Rice Case inputs.

---

## 3. Critical WOM / PySI V0R8 Assumptions

### 3.1 Physical node layer and planning PlanNode layer are different

WOM has two node worlds:

```text
Physical layer:
    product-independent GUI / map / NetworkX node world

Planning layer:
    product-specific PlanNode tree world
```

This integration must target the planning layer only.

It must not seed physical GUI nodes.

---

### 3.2 Product-specific PlanNode tree is the target

The intended real target is:

```text
prod_tree_dict_OT[product_name]
prod_tree_dict_IN[product_name]
```

These contain product-specific planning PlanNodes.

The first controlled test may use a small real-like PlanNode tree instead of the full production tree, but the design should follow the same access pattern.

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

### 3.4 PSI buckets contain Lot_ID lists, not quantities

This remains the most important rule.

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
1. PlanNode lookup from a real or real-like product-specific PlanNode tree
2. Rice weekly input → WeeklyPlanRow
3. WeeklyPlanRow → LotHeader
4. LotHeader / WeeklyPlanRow → PsiSeedRecord
5. PsiSeedRecord → real-like PlanNode.psi4demand / psi4supply
6. W40 / W41 boundary preservation
7. dry-run mode
8. focused tests
```

### 4.2 Out of Scope

This integration should not:

```text
1. modify GUI
2. modify run_full_plan
3. refactor existing monthly loader
4. run Backward Planning
5. run Forward Planning
6. perform psi4demand → psi4supply bridge
7. implement full Rice supply chain network
8. implement Management Issue Generation
9. implement database persistence
```

---

## 5. Design Strategy

### 5.1 Use current adapter pipeline

The integration should reuse:

```text
pysi/cases/japanese_rice/rice_plan_input_integration.py
pysi/adapters/weekly_plan_table.py
pysi/adapters/lot_generation.py
pysi/adapters/psi_seed.py
pysi/adapters/plan_node_seeding.py
```

Do not duplicate the existing pipeline.

---

### 5.2 Start with real-like PlanNode tree

The first implementation may use a small real-like PlanNode tree that follows the real PlanNode shape.

This is safer than immediately wiring into the full production `prod_tree_dict_OT / IN`.

The real-like node should have:

```text
name
children
psi4demand
psi4supply
```

This gives better coverage than the previous flat mock PlanNode while still keeping the test small.

---

### 5.3 Real product-specific tree integration is the next boundary

After the real-like tree integration is stable, the next step will be connecting to:

```text
prod_tree_dict_OT[product_name]
prod_tree_dict_IN[product_name]
```

This memo prepares for that but does not require full environment integration yet.

---

## 6. PlanNode Lookup

### 6.1 Purpose

Build a lookup dictionary from a PlanNode tree.

Suggested function:

```python
def build_plan_node_lookup_from_tree(root) -> dict[str, Any]:
    ...
```

Expected behavior:

```text
1. traverse root and all children
2. read node.name
3. return {node.name: node}
```

### 6.2 Multiple roots

If both outbound and inbound roots are provided:

```python
def build_plan_node_lookup_from_roots(roots: list[Any]) -> dict[str, Any]:
    ...
```

MVP duplicate handling:

```text
first root wins
duplicates may be recorded later
```

### 6.3 Do not use physical GUI nodes

The lookup must be built from planning-layer PlanNode trees.

Do not use:

```text
GUI map nodes
NetworkX physical nodes
world map nodes
```

---

## 7. Rice Node Mapping

### 7.1 MVP exact match policy

For the MVP, use exact name matching:

```text
Rice node_id == PlanNode.name
```

If a Rice node is not found in the PlanNode lookup:

```text
record missing_node_id
skip seed record
```

Do not create PlanNodes automatically.

### 7.2 Future mapping table

Future versions may add:

```text
rice_node_id → wom_plan_node_name
```

as a mapping table.

This is out of scope for the MVP.

---

## 8. Week Indexing

Rice Case uses a 3-year horizon:

```text
2026-W01 to 2028-W52
```

Expected index examples:

```python
week_indexer["2026-W01"] == 0
week_indexer["2026-W40"] == 39
week_indexer["2026-W41"] == 40
week_indexer["2027-W01"] == 52
week_indexer["2028-W52"] == 155
```

Do not silently extend PlanNode PSI horizon.

If the target PlanNode has fewer weeks than required:

```text
record invalid_week
skip seed record
```

---

## 9. Target Seeding Rules

### 9.1 Demand rows

Rice demand rows should seed:

```text
WeeklyPlanRow(plan_type="demand")
    ↓
PsiSeedRecord(layer="demand", bucket="S")
    ↓
PlanNode.psi4demand[w][S]
```

### 9.2 Supply / harvest rows

Rice supply rows should seed:

```text
WeeklyPlanRow(plan_type="supply")
    ↓
PsiSeedRecord(layer="demand", bucket="P")
    ↓
PlanNode.psi4demand[w][P]
```

This keeps supply-side planning requirements in the demand planning layer until Backward Planning is run.

### 9.3 Future initial inventory

Future versions may support:

```text
initial_inventory
    ↓
PsiSeedRecord(layer="supply", bucket="I")
```

This is out of scope unless already implemented safely.

---

## 10. Proposed Integration Function

Suggested function:

```python
def seed_rice_weekly_input_to_real_like_plan_tree(
    *,
    case_data,
    product_name: str,
    roots: list[Any],
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
5. apply PsiSeedRecords to PlanNode lookup
6. return structured result
```

---

## 11. Suggested Result Object

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

## 12. Real-like PlanNode for Tests

Use a minimal tree node class in tests.

```python
@dataclass
class RealLikePlanNode:
    name: str
    children: list = field(default_factory=list)
    psi4demand: list = field(default_factory=list)
    psi4supply: list = field(default_factory=list)
```

Helper:

```python
def make_real_like_plan_node(name: str, weeks: int) -> RealLikePlanNode:
    return RealLikePlanNode(
        name=name,
        children=[],
        psi4demand=[[[], [], [], []] for _ in range(weeks)],
        psi4supply=[[[], [], [], []] for _ in range(weeks)],
    )
```

Example tree:

```text
root
    ├── PRODUCER_NIIGATA
    ├── DEMAND_HOUSEHOLD_TOKYO
    └── DEMAND_FOOD_SERVICE_TOKYO
```

---

## 13. Smoke Runner Option

Optional smoke runner:

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

This runner is optional for MVP if tests cover the behavior.

---

## 14. Required Tests

Add:

```text
tests/test_japanese_rice_real_plannode_seed_integration.py
```

Required tests:

```text
1. build_plan_node_lookup_from_tree finds child nodes.
2. Rice weekly rows seed into real-like PlanNode tree.
3. demand rows seed to psi4demand[w][S].
4. supply rows seed to psi4demand[w][P].
5. W40 / W41 boundary is preserved.
6. dry_run does not mutate PlanNodes.
7. missing node is recorded and skipped.
8. no numeric quantities are inserted into PSI buckets.
9. existing Rice plan input integration tests still pass.
```

---

## 15. Existing Tests to Run

Run:

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

---

## 16. Completion Criteria

This integration is complete when:

```text
[OK] real-like PlanNode lookup can be built
[OK] Rice weekly input can seed PlanNode.psi4demand
[OK] demand rows seed to S bucket
[OK] supply rows seed to P bucket
[OK] W40 / W41 boundary is preserved
[OK] dry-run works
[OK] missing node handling works
[OK] PSI buckets contain Lot_ID lists, not numeric quantities
[OK] no GUI / run_full_plan / loader / planning engine changes
[OK] focused tests pass
```

---

## 17. Future Work

After this integration, future milestones are:

```text
1. Connect to actual prod_tree_dict_OT / prod_tree_dict_IN.
2. Run Backward Planning after seed.
3. Bridge demand-side result into psi4supply.
4. Run Forward Planning.
5. Refactor existing monthly loader to use this input pipeline.
6. Add GUI case loading.
```

---

## 18. Summary

This design moves Rice Case one step closer to real WOM Planning Engine integration.

The target flow is:

```text
Rice Case weekly input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
real-like product-specific PlanNode.psi4demand / psi4supply
```

The key safety rule is unchanged:

```text
PSI buckets contain Lot_ID lists.
Quantity is len(list).
Lot attributes live outside PSI buckets.
```

This integration should prove that Rice Case data can enter real WOM planning structures without breaking V0R8 PSI semantics.