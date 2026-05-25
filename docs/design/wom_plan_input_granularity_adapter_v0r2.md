# WOM Plan Input Granularity Adapter v0r2 Design Memo
## Canonical Weekly Plan Table → Lot_ID Generation → PSI Seed Records

**Version:** v0r2 revised draft  
**Date:** 2026-05-16  
**Status:** Design memo  
**Target path:** `docs/design/wom_plan_input_granularity_adapter_v0r2.md`

**Related design documents:**

- `docs/design/wom_plan_input_granularity_adapter.md`
- `docs/design/wom_case_modeling_base_dataset.md`
- `docs/design/case_japanese_rice_crop_year_modeling_addendum.md`
- `docs/design/case_japanese_rice_master_dataset.md`
- `docs/design/case_japanese_rice_simulation_plan.md`
- `docs/design/wom_planning_operations_commands.md`

---

## 1. Purpose

This memo defines **Plan Input Granularity Adapter v0r2**.

v0r1 created a safe additive input normalization layer:

```text
monthly_sp / weekly_sp / case_weekly input
    ↓
canonical weekly plan table
```

v0r2 extends this pipeline:

```text
canonical weekly plan table
    ↓
Lot_ID generation
    ↓
PSI seed records
    ↓
in-memory PSI seed table
```

The purpose is to decouple the following responsibilities:

```text
1. plan input granularity normalization
2. Lot_ID generation
3. PSI seed record generation
4. eventual PSI seeding into WOM PlanNode trees
```

The key principle is:

> Monthly and weekly inputs should share the same downstream Lot_ID generation and PSI seed generation logic after they have been normalized into the canonical weekly plan table.

---

## 2. WOM Internal Data Structure Assumptions

This design depends on the WOM / PySI V0R8 internal data structure.

### 2.1 Physical layer and planning layer are different

WOM has at least two node worlds:

```text
Physical layer:
    product-independent physical / GUI / map / NetworkX node world

Planning layer:
    product-specific PlanNode tree world
```

The physical layer is used for location, network display, and GUI interaction.

The planning layer is where product-specific PSI planning state is held.

Therefore, the Plan Input Granularity Adapter ultimately targets:

```text
product-specific planning layer PlanNode tree
```

not the physical GUI node world.

### 2.2 PSI source of truth is held by product-specific PlanNode trees

For each product, WOM maintains product-specific planning trees.

Conceptually:

```text
prod_tree_dict_OT[product_name] → outbound planning tree
prod_tree_dict_IN[product_name] → inbound planning tree
```

These product-specific PlanNode trees are the intended target for future PSI seeding.

### 2.3 PSI buckets are Lot_ID lists

The canonical V0R8 PSI structure is:

```python
node.psi4demand[w] = [S_ids, CO_ids, I_ids, P_ids]
node.psi4supply[w] = [S_ids, CO_ids, I_ids, P_ids]
```

The bucket index convention is:

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

### 2.4 Quantity is `len(list)` in V0R8 PSI buckets

In the V0R8 canonical PSI bucket structure, quantity is calculated from the number of Lot_IDs in the bucket.

```python
quantity = len(node.psi4demand[w][bucket])
quantity = len(node.psi4supply[w][bucket])
```

Therefore:

> **PSI buckets must contain Lot_ID lists, not numeric quantities.**

This is a non-negotiable design rule for this adapter.

### 2.5 Lot attributes are held outside PSI buckets

PSI buckets hold only Lot_IDs.

Lot attributes should be held outside the PSI bucket, for example in:

```text
LotHeader
lot_pool
metadata table
lot attribute dictionary
```

Examples of lot attributes:

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

### 2.6 v0r2 should not mutate live PlanNode PSI directly

The v0r2 adapter should stop at an intermediate representation:

```text
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
in-memory PSI seed table
```

Actual mutation of:

```python
PlanNode.psi4demand
PlanNode.psi4supply
```

should be implemented in a later v0r3 stage after the seed table contract is stable.

---

## 3. Goal of v0r2

The goal of v0r2 is not to replace the existing WOM loader.

The goal is to create a safe, testable intermediate layer that converts normalized weekly plan rows into data structures that are compatible with the V0R8 PSI model.

### 3.1 v0r2 Goal Statement

```text
Plan Input Granularity Adapter v0r2 should convert canonical weekly plan rows into deterministic LotHeader records and PsiSeedRecord rows, preserving Lot_ID identity and preparing Lot_ID lists for future seeding into product-specific PlanNode psi4demand / psi4supply buckets.
```

### 3.2 v0r2 should guarantee

```text
1. WeeklyPlanRow quantity is converted into LotHeader records.
2. Lot_IDs are deterministic.
3. Lot attributes are preserved outside PSI buckets.
4. PsiSeedRecord maps each lot to layer / bucket / week / node.
5. In-memory PSI seed table groups Lot_ID lists by target PSI key.
6. PSI seed table contains Lot_ID lists, not numeric quantities.
7. Real PlanNode mutation is deferred to v0r3.
```

---

## 4. Current v0r1 Scope

The v0r1 adapter introduced:

```text
pysi/adapters/calendar_445.py
pysi/adapters/weekly_plan_table.py
pysi/adapters/plan_input_granularity.py
tests/test_plan_input_granularity_adapter.py
```

v0r1 supports:

```text
monthly_sp:
    MonthlyPlanInputRow → 4-4-5 calendar → WeeklyPlanRow

weekly_sp:
    WeeklyPlanInputRow → WeeklyPlanRow

case_weekly:
    case-specific weekly data → WeeklyPlanRow
```

v0r1 intentionally does not implement:

```text
Lot_ID generation
PSI seed records
PlanNode mutation
existing loader refactor
GUI integration
```

---

## 5. v0r2 Scope

### 5.1 In Scope

v0r2 should define and later implement:

```text
1. LotHeader dataclass
2. LotGenerationConfig dataclass
3. generate_lots_from_weekly_plan(...)
4. PsiSeedRecord dataclass
5. bucket mapping from plan_type to PSI layer / bucket
6. generate_psi_seed_records(...)
7. build_psi_seed_table(...)
8. focused tests
```

### 5.2 Out of Scope

v0r2 should not yet:

```text
1. refactor existing S_month / P_month loader
2. mutate live production PlanNode objects by default
3. modify GUI
4. modify existing planning engines
5. change existing run_full_plan behavior
6. implement full Rice Case adapter
7. implement database persistence
```

This should remain additive and safe.

---

## 6. Desired Pipeline

The complete target pipeline is:

```text
Raw Plan Input
    ↓
Calendar / Granularity Normalization
    ↓
Canonical Weekly Plan Table
    ↓
Lot_ID Generation
    ↓
PSI Seed Records
    ↓
PSI Seeding into WOM PlanNode trees
```

v0r2 implements:

```text
Canonical Weekly Plan Table
    ↓
Lot_ID Generation
    ↓
PSI Seed Records
    ↓
In-memory PSI Seed Table
```

---

## 7. Canonical Weekly Plan Row

v0r2 consumes the v0r1 canonical row.

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

Allowed `plan_type` values in v0r2:

```text
S
P
demand
supply
initial_inventory
```

v0r2 may initially support only:

```text
S
P
demand
supply
```

and leave `initial_inventory` as a near-term extension.

---

## 8. Lot_ID Generation

### 8.1 Purpose

Generate Lot_IDs and lot headers from weekly plan rows.

Input:

```text
WeeklyPlanRow
LotGenerationConfig
optional case-specific metadata
```

Output:

```text
list[LotHeader]
```

### 8.2 LotHeader dataclass

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

### 8.3 LotGenerationConfig dataclass

```python
@dataclass
class LotGenerationConfig:
    lot_size: float = 1.0
    quantity_mode: str = "lot_count"
    lot_id_prefix: str = ""
    allow_fractional_last_lot: bool = True
    sequence_digits: int = 6
```

### 8.4 quantity_mode

Supported modes:

```text
lot_count:
    WeeklyPlanRow.quantity means number of lots.

physical_quantity:
    WeeklyPlanRow.quantity means physical quantity.
    lot_count = ceil(quantity / lot_size)

single_lot:
    generate one lot whose quantity equals WeeklyPlanRow.quantity.
```

MVP recommendation:

```text
lot_count
```

because current Rice and Vaccine smoke runners already use lot quantities.

### 8.5 Fractional quantity handling

Some case datasets may use float quantities.

Example:

```text
Rice weekly demand:
    1.6 lots/week
```

Recommended MVP policy:

```text
allow_fractional_last_lot = True
```

Example:

```text
quantity = 1.6
lot_size = 1.0
    ↓
LOT 1: quantity = 1.0
LOT 2: quantity = 0.6
```

Important:

```text
Fractional quantity may exist in LotHeader.quantity,
but future PlanNode PSI buckets still receive Lot_ID lists.
```

If strict V0R8 `len(list)` quantity semantics are required, the future PlanNode seeding stage should decide whether to round, carry fractional remainders, or use only integer lots.

### 8.6 Lot_ID format

Suggested default Lot_ID format:

```text
{scenario_id}-{product_id}-{node_id}-{week}-{plan_type}-{seq}
```

Example:

```text
RICE_AS_IS-BROWN_RICE_STANDARD-PRODUCER_NIIGATA-2026W40-supply-000001
```

The implementation may sanitize IDs by removing or replacing characters such as `/`, spaces, and `:`.

### 8.7 Case-specific metadata

Lot generation should preserve case-specific metadata through `attributes`.

Rice example:

```python
attributes = {
    "crop_year": "2026",
    "harvest_week": "2026-W40",
    "available_week": "2026-W41",
    "quality_limit_week": "2027-W40",
}
```

Vaccine example:

```python
attributes = {
    "expiry_week": "2026-W48",
    "temperature_class": "cold",
    "target_region": "TOKYO",
}
```

---

## 9. Lot Generation Function

Suggested function:

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
3. generate stable Lot_IDs
4. preserve source information
5. return LotHeader list
```

For a zero quantity row:

```text
quantity = 0
    ↓
return []
```

For a negative quantity row:

```text
raise ValueError
```

---

## 10. PSI Seed Records

### 10.1 Purpose

A PSI seed record is an intermediate representation between lot generation and actual mutation of WOM PSI structures.

This is safer than immediately writing into live PlanNode objects.

```text
LotHeader
    ↓
PsiSeedRecord
    ↓
in-memory seed table
    ↓
future optional seeding into psi4demand / psi4supply
```

### 10.2 PsiSeedRecord dataclass

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

## 11. Bucket Mapping

### 11.1 Purpose

Map canonical plan types to PSI target layer / bucket.

### 11.2 Default mapping

Recommended MVP mapping:

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

### 11.3 Why supply maps to demand/P by default

In WOM Backward Planning, external supply or production requirement may be represented as demand-layer P placement before Forward Planning simulation.

However, this mapping should remain configurable.

Different cases may use:

```text
external supply:
    layer = supply
    bucket = I

production input:
    layer = demand
    bucket = P
```

Therefore, v0r2 should implement default mapping but allow override.

---

## 12. PSI Seed Generation Function

Suggested function:

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
5. return lot headers and seed records
```

`row_attributes` is optional and may be used by Rice / Vaccine cases to attach metadata.

---

## 13. In-memory PSI Seed Table

### 13.1 Purpose

For MVP tests, provide a safe in-memory table.

This avoids requiring real WOM PlanNode objects.

Suggested structure:

```python
{
    (scenario_id, product_id, node_id, week, layer, bucket): [lot_id, ...]
}
```

### 13.2 Suggested function

```python
def build_psi_seed_table(seed_records: list[PsiSeedRecord]) -> dict[tuple, list[str]]:
    ...
```

Expected behavior:

```text
group seed records by scenario / product / node / week / layer / bucket
preserve lot order
```

### 13.3 Important rule

The seed table must store:

```text
Lot_ID lists
```

not numeric quantities.

Correct:

```python
seed_table[key] = ["LOT_A", "LOT_B", "LOT_C"]
```

Incorrect:

```python
seed_table[key] = 3
```

This preserves compatibility with V0R8 PSI bucket semantics.

---

## 14. Future PSI Seeding into Real WOM PlanNodes

v0r2 should not mutate real WOM PlanNode objects by default.

Future function concept:

```python
def apply_psi_seed_records_to_plan_nodes(
    seed_records: list[PsiSeedRecord],
    plan_node_lookup: dict[str, Any],
    week_indexer: Any,
) -> None:
    ...
```

This should be implemented only after the seed table behavior is stable.

The future target is:

```python
plan_node.psi4demand[w][bucket_index].extend(lot_id_list)
plan_node.psi4supply[w][bucket_index].extend(lot_id_list)
```

The future implementation must target product-specific PlanNode trees, not physical GUI node trees.

---

## 15. Rice Case Application

Rice Case uses `case_weekly` input.

### 15.1 Weekly rows

Example:

```python
WeeklyPlanRow(
    scenario_id="RICE_AS_IS",
    product_id="BROWN_RICE_STANDARD",
    node_id="PRODUCER_NIIGATA",
    week="2026-W40",
    plan_type="supply",
    quantity=20.0,
    source_granularity="case_weekly",
    source_id="rice_supply_plan",
)
```

### 15.2 Lot metadata

Rice-specific `attributes` should include:

```text
crop_year
harvest_week
available_week
expected_consumption_start_week
expected_consumption_end_week
quality_limit_week
```

### 15.3 Boundary requirement

Rice v0r2 tests should confirm:

```text
2026-W40 remains 2026-W40
2026-W41 remains 2026-W41
crop_year metadata is preserved
```

---

## 16. Vaccine Case Application

Vaccine Case also uses `case_weekly` input.

Vaccine-specific lot metadata should include:

```text
expiry_week
quality_status
temperature_class
target_region
target_node
```

---

## 17. Suggested Files

Please add or update:

```text
pysi/adapters/lot_generation.py
pysi/adapters/psi_seed.py
pysi/adapters/plan_input_pipeline.py
tests/test_plan_input_lot_generation.py
tests/test_plan_input_psi_seed.py
```

Optional:

```text
tests/test_plan_input_pipeline.py
```

Do not modify:

```text
existing monthly loader
GUI
planning engines
```

---

## 18. Test Policy

### 18.1 Lot generation tests

Required tests:

```text
1. quantity 0 generates no lots
2. quantity 3.0 with lot_count mode generates 3 lots
3. quantity 1.6 with fractional last lot generates quantities [1.0, 0.6]
4. negative quantity raises ValueError
5. Lot_IDs are deterministic
6. Rice crop_year metadata is preserved in LotHeader.attributes
```

### 18.2 PSI seed tests

Required tests:

```text
1. demand plan_type maps to demand/S
2. S plan_type maps to demand/S
3. supply plan_type maps to demand/P
4. P plan_type maps to demand/P
5. seed table groups lot IDs by key
6. lot order is preserved
7. seed table contains Lot_ID list, not numeric quantity
```

### 18.3 Pipeline tests

Required tests:

```text
1. weekly row → lots → seed records
2. monthly row → 4-4-5 weekly rows → lots → seed records
3. Rice W40 / W41 boundary is preserved through full pipeline
```

---

## 19. Completion Criteria

v0r2 is complete when:

```text
[OK] LotHeader exists
[OK] LotGenerationConfig exists
[OK] generate_lots_from_weekly_plan works
[OK] PsiSeedRecord exists
[OK] generate_psi_seed_records works
[OK] build_psi_seed_table works
[OK] monthly and weekly inputs share the same downstream generation
[OK] Rice crop_year metadata can be preserved
[OK] seed table stores Lot_ID lists, not numeric quantities
[OK] focused tests pass
[OK] existing v0r1 adapter tests pass
[OK] no existing loader / GUI / planning engine changes
```

---

## 20. Implementation Roadmap

### v0r2

```text
canonical weekly plan table
    ↓
Lot_ID generation
    ↓
PSI seed records
    ↓
in-memory seed table
```

### v0r3

```text
PSI seed records
    ↓
real WOM PlanNode psi4demand / psi4supply seeding
```

### v0r4

```text
existing monthly loader refactor
```

---

## 21. Summary

The key idea of v0r2 is:

```text
Once data is normalized into canonical weekly plan rows,
all inputs should share the same Lot_ID generation and PSI seed generation logic.
```

This allows WOM to support:

```text
monthly input
weekly input
case_weekly input
```

without duplicating downstream loading logic.

The design must remain faithful to V0R8 PSI semantics:

```text
PlanNode.psi4demand / psi4supply buckets hold Lot_ID lists.
Quantity is len(list).
Lot attributes live outside the PSI bucket.
```

Therefore, v0r2 produces:

```text
LotHeader
PsiSeedRecord
in-memory PSI seed table
```

and defers actual PlanNode PSI mutation to v0r3.
