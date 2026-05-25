# Codex Request: Implement WOM Plan Input Granularity Adapter v0r2

## 1. Background

We are working on branch:

```text
feature/plan-input-granularity-adapter-v0r1
```

The following design documents already exist:

```text
docs/design/wom_plan_input_granularity_adapter.md
docs/design/wom_plan_input_granularity_adapter_v0r2.md
```

The current v0r1 implementation already added:

```text
pysi/adapters/__init__.py
pysi/adapters/calendar_445.py
pysi/adapters/weekly_plan_table.py
pysi/adapters/plan_input_granularity.py
tests/test_plan_input_granularity_adapter.py
```

v0r1 supports:

```text
monthly_sp input
    → 4-4-5 calendar conversion
    → canonical WeeklyPlanRow

weekly_sp input
    → pass-through
    → canonical WeeklyPlanRow

case_weekly input
    → pass-through
    → canonical WeeklyPlanRow
```

This request is for v0r2:

```text
canonical weekly plan table
    ↓
Lot_ID generation
    ↓
PsiSeedRecord generation
    ↓
in-memory PSI seed table
```

Please read this design memo first:

```text
docs/design/wom_plan_input_granularity_adapter_v0r2.md
```

---

## 2. Main Objective

Implement the next additive layer of the Plan Input Granularity Adapter.

The goal is to convert normalized `WeeklyPlanRow` records into:

```text
LotHeader records
PsiSeedRecord records
in-memory PSI seed table
```

This prepares future loading into WOM / PySI V0R8 PlanNode structures.

This request should not mutate real PlanNode objects yet.

---

## 3. Critical WOM / PySI V0R8 Data Structure Assumptions

Please preserve the following assumptions.

### 3.1 Physical node layer and planning PlanNode layer are different

WOM has at least two node worlds:

```text
Physical layer:
    product-independent GUI / map / NetworkX node world

Planning layer:
    product-specific PlanNode tree world
```

The final PSI target is the product-specific planning layer, not the physical GUI node world.

Conceptually:

```text
prod_tree_dict_OT[product_name] → outbound planning tree
prod_tree_dict_IN[product_name] → inbound planning tree
```

### 3.2 PSI source of truth is the product-specific PlanNode tree

Each product-specific PlanNode holds:

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

### 3.3 PSI buckets must contain Lot_ID lists, not numeric quantities

This is the most important rule.

Correct:

```python
node.psi4demand[w][0] = ["LOT_A", "LOT_B", "LOT_C"]
```

Incorrect:

```python
node.psi4demand[w][0] = 3
```

Quantity is calculated as:

```python
quantity = len(node.psi4demand[w][bucket])
quantity = len(node.psi4supply[w][bucket])
```

### 3.4 Lot attributes must be outside PSI buckets

PSI buckets store only Lot_IDs.

Lot attributes should be stored in:

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

## 4. Important Constraints

Please follow these constraints:

```text
1. Do not modify existing monthly WOM loaders.
2. Do not modify GUI.
3. Do not modify existing planning engines.
4. Do not mutate real PlanNode.psi4demand / psi4supply yet.
5. Do not refactor run_full_plan.
6. Do not implement database persistence.
7. Do not implement full Rice Case adapter.
8. Add only safe additive adapter modules and tests.
```

This request should remain additive and isolated.

---

## 5. Files to Add or Update

Please add:

```text
pysi/adapters/lot_generation.py
pysi/adapters/psi_seed.py
pysi/adapters/plan_input_pipeline.py
tests/test_plan_input_lot_generation.py
tests/test_plan_input_psi_seed.py
```

Please update if useful:

```text
pysi/adapters/__init__.py
```

Optional:

```text
tests/test_plan_input_pipeline.py
```

Do not modify:

```text
existing monthly loaders
GUI
planning engines
```

---

## 6. Existing v0r1 Types to Reuse

Please reuse the v0r1 `WeeklyPlanRow` from:

```text
pysi/adapters/weekly_plan_table.py
```

Conceptual structure:

```python
@dataclass
class WeeklyPlanRow:
    scenario_id: str
    product_id: str
    node_id: str
    week: str
    plan_type: str
    quantity: float
    source_granularity: str
    source_id: str = ""
    comment: str = ""
```

Allowed `plan_type` values for v0r2:

```text
S
P
demand
supply
initial_inventory
```

For MVP, support at least:

```text
S
P
demand
supply
```

`initial_inventory` may be defined but can remain a future extension if needed.

---

## 7. LotHeader

Please implement `LotHeader`.

Suggested file:

```text
pysi/adapters/lot_generation.py
```

Suggested dataclass:

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LotHeader:
    lot_id: str
    scenario_id: str
    product_id: str
    node_id: str
    week: str
    plan_type: str
    quantity: float
    lot_size: float
    source_granularity: str
    source_id: str = ""
    sequence_no: int = 0
    quality_status: str = "usable"
    priority: int = 100
    attributes: dict[str, Any] = field(default_factory=dict)
```

---

## 8. LotGenerationConfig

Please implement `LotGenerationConfig`.

```python
@dataclass
class LotGenerationConfig:
    lot_size: float = 1.0
    quantity_mode: str = "lot_count"
    lot_id_prefix: str = ""
    allow_fractional_last_lot: bool = True
    sequence_digits: int = 6
```

Supported `quantity_mode` values:

```text
lot_count:
    WeeklyPlanRow.quantity means number of lots.

physical_quantity:
    WeeklyPlanRow.quantity means physical quantity.
    lot_count = ceil(quantity / lot_size)

single_lot:
    generate one lot whose quantity equals WeeklyPlanRow.quantity.
```

MVP default:

```text
lot_count
```

---

## 9. Fractional Quantity Policy

Some case datasets may use float lot quantities.

Example:

```text
Rice weekly demand = 1.6 lots/week
```

For v0r2, support fractional last lot when configured.

Example:

```text
quantity = 1.6
lot_size = 1.0
allow_fractional_last_lot = True

Generated lots:
    lot 1 quantity = 1.0
    lot 2 quantity = 0.6
```

Important:

```text
Fractional quantity may exist in LotHeader.quantity,
but PSI seed table must still store Lot_ID lists, not numeric quantities.
```

Future PlanNode seeding can decide whether to round, carry fractional remainders, or use only integer lots.

---

## 10. Lot_ID Format

Default Lot_ID format:

```text
{scenario_id}-{product_id}-{node_id}-{week}-{plan_type}-{seq}
```

Example:

```text
RICE_AS_IS-BROWN_RICE_STANDARD-PRODUCER_NIIGATA-2026W40-supply-000001
```

Please sanitize Lot_IDs by replacing or removing unsafe characters such as:

```text
space
/
:
```

Determinism is important.

Same input row and same sequence should produce same Lot_ID.

---

## 11. generate_lots_from_weekly_plan

Please implement:

```python
def generate_lots_from_weekly_plan(
    row: WeeklyPlanRow,
    *,
    config: LotGenerationConfig | None = None,
    attributes: dict | None = None,
) -> list[LotHeader]:
    ...
```

Expected behavior:

```text
1. validate quantity >= 0
2. determine lot count / lot quantities
3. generate stable deterministic Lot_IDs
4. preserve source information
5. preserve attributes
6. return list[LotHeader]
```

Special cases:

```text
quantity = 0:
    return []

quantity < 0:
    raise ValueError
```

---

## 12. PsiSeedRecord

Please implement `PsiSeedRecord`.

Suggested file:

```text
pysi/adapters/psi_seed.py
```

Suggested dataclass:

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

Allowed `layer` values:

```text
demand
supply
```

Allowed `bucket` values:

```text
S
CO
I
P
```

---

## 13. Default Bucket Mapping

Please implement default mapping from `plan_type` to `(layer, bucket)`.

Recommended mapping:

```text
plan_type = demand:
    layer = demand
    bucket = S

plan_type = S:
    layer = demand
    bucket = S

plan_type = supply:
    layer = demand
    bucket = P

plan_type = P:
    layer = demand
    bucket = P

plan_type = initial_inventory:
    layer = supply
    bucket = I
```

This mapping should be configurable through an optional `bucket_mapping` argument.

---

## 14. generate_psi_seed_records

Please implement:

```python
def generate_psi_seed_records(
    rows: list[WeeklyPlanRow],
    *,
    lot_config: LotGenerationConfig | None = None,
    bucket_mapping: dict[str, tuple[str, str]] | None = None,
    row_attributes: dict[int, dict] | None = None,
) -> tuple[list[LotHeader], list[PsiSeedRecord]]:
    ...
```

Expected behavior:

```text
1. generate lots for each WeeklyPlanRow
2. map each row's plan_type to layer / bucket
3. create PsiSeedRecord for each lot
4. preserve lot_id and quantity
5. return both lot headers and seed records
```

`row_attributes` may be used by Rice / Vaccine cases to attach metadata.

---

## 15. build_psi_seed_table

Please implement:

```python
def build_psi_seed_table(
    seed_records: list[PsiSeedRecord],
) -> dict[tuple, list[str]]:
    ...
```

Suggested key:

```python
(
    scenario_id,
    product_id,
    node_id,
    week,
    layer,
    bucket,
)
```

Expected value:

```python
["LOT_A", "LOT_B", "LOT_C"]
```

Important:

```text
The seed table must store Lot_ID lists, not numeric quantities.
```

Correct:

```python
seed_table[key] = ["LOT_A", "LOT_B", "LOT_C"]
```

Incorrect:

```python
seed_table[key] = 3
```

---

## 16. Optional Plan Input Pipeline Helper

Please add a small pipeline helper if useful.

Suggested file:

```text
pysi/adapters/plan_input_pipeline.py
```

Suggested function:

```python
def weekly_rows_to_lots_and_seed_table(
    rows: list[WeeklyPlanRow],
    *,
    lot_config: LotGenerationConfig | None = None,
    bucket_mapping: dict[str, tuple[str, str]] | None = None,
    row_attributes: dict[int, dict] | None = None,
) -> tuple[list[LotHeader], list[PsiSeedRecord], dict[tuple, list[str]]]:
    ...
```

Expected behavior:

```text
WeeklyPlanRow list
    ↓
LotHeader list
    ↓
PsiSeedRecord list
    ↓
in-memory PSI seed table
```

---

## 17. Rice Case Requirements

Please include tests that confirm Rice-specific metadata can be preserved.

Example attributes:

```python
{
    "crop_year": "2026",
    "harvest_week": "2026-W40",
    "available_week": "2026-W41",
    "quality_limit_week": "2027-W40",
}
```

Test should confirm:

```text
crop_year exists in LotHeader.attributes
2026-W40 remains 2026-W40
2026-W41 remains 2026-W41
```

---

## 18. Vaccine Case Compatibility

No vaccine-specific implementation is required.

However, the design should support attributes such as:

```text
expiry_week
quality_status
temperature_class
target_region
target_node
```

This can be covered indirectly by generic attribute preservation.

---

## 19. Tests

Please add:

```text
tests/test_plan_input_lot_generation.py
tests/test_plan_input_psi_seed.py
```

Optional:

```text
tests/test_plan_input_pipeline.py
```

Required tests for lot generation:

```text
1. quantity 0 generates no lots
2. quantity 3.0 with lot_count mode generates 3 lots
3. quantity 1.6 with fractional last lot generates quantities [1.0, 0.6]
4. negative quantity raises ValueError
5. Lot_IDs are deterministic
6. Rice crop_year metadata is preserved in LotHeader.attributes
```

Required tests for PSI seed:

```text
1. demand plan_type maps to demand/S
2. S plan_type maps to demand/S
3. supply plan_type maps to demand/P
4. P plan_type maps to demand/P
5. seed table groups lot IDs by key
6. lot order is preserved
7. seed table contains Lot_ID list, not numeric quantity
```

Required pipeline tests:

```text
1. weekly row → lots → seed records
2. monthly row → 4-4-5 weekly rows → lots → seed records
3. Rice W40 / W41 boundary is preserved through full pipeline
```

---

## 20. Test Commands

Please run:

```bat
python -m pytest tests/test_plan_input_lot_generation.py
python -m pytest tests/test_plan_input_psi_seed.py
```

If pipeline test is added:

```bat
python -m pytest tests/test_plan_input_pipeline.py
```

Also run existing v0r1 adapter tests:

```bat
python -m pytest tests/test_plan_input_granularity_adapter.py
```

Optional compatibility tests:

```bat
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

If broader tests fail due to unrelated optional dependencies, report separately.

---

## 21. Completion Criteria

This request is complete when:

```text
[OK] LotHeader exists
[OK] LotGenerationConfig exists
[OK] generate_lots_from_weekly_plan works
[OK] PsiSeedRecord exists
[OK] generate_psi_seed_records works
[OK] build_psi_seed_table works
[OK] weekly and monthly inputs share downstream lot/seed logic
[OK] seed table stores Lot_ID lists, not numeric quantities
[OK] Rice crop_year metadata is preserved
[OK] W40 / W41 boundary is preserved
[OK] focused tests pass
[OK] existing v0r1 adapter tests pass
[OK] no existing loader / GUI / planning engine changes
```

---

## 22. Expected Response from Codex

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
real PlanNode.psi4demand / psi4supply mutation
existing monthly loader refactor
GUI integration
Rice Case adapter refactor
database persistence
```

This request is only for:

```text
Plan Input Granularity Adapter v0r2:
    WeeklyPlanRow
        ↓
    LotHeader
        ↓
    PsiSeedRecord
        ↓
    in-memory PSI seed table
```