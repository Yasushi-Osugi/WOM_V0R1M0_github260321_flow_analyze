# WOM Plan Input Granularity Adapter v0r2 Completion Memo
## Canonical Weekly Plan Table → Lot_ID Generation → PSI Seed Table

**Version:** v0r2 completion  
**Date:** 2026-05-17  
**Status:** Completion memo  
**Branch:** `feature/plan-input-granularity-adapter-v0r1`

---

## 1. Purpose

This memo summarizes the completion status of **WOM Plan Input Granularity Adapter v0r2**.

The purpose of v0r2 was to extend the v0r1 input normalization layer:

```text
monthly / weekly / case_weekly input
    ↓
canonical weekly plan table

into the next stage:

canonical weekly plan table
    ↓
Lot_ID generation
    ↓
PsiSeedRecord generation
    ↓
in-memory PSI seed table

This creates the foundation for future safe loading into WOM / PySI V0R8 PlanNode.psi4demand and PlanNode.psi4supply.

2. Background

v0r1 introduced the input granularity normalization layer.

v0r1 supports:

monthly_sp:
    S_month / P_month
        ↓
    4-4-5 calendar conversion
        ↓
    canonical WeeklyPlanRow

weekly_sp:
    S_week / P_week
        ↓
    canonical WeeklyPlanRow

case_weekly:
    case-level weekly supply / demand
        ↓
    canonical WeeklyPlanRow

v0r2 builds on this by generating deterministic Lot_IDs and PSI seed records from WeeklyPlanRow.

3. Key Design Assumptions

v0r2 follows the WOM / PySI V0R8 canonical data structure.

3.1 Physical node and planning PlanNode are different

WOM has two node worlds:

Physical layer:
    product-independent GUI / map / NetworkX node world

Planning layer:
    product-specific PlanNode tree world

v0r2 does not target the physical GUI node world.

The future target is:

product-specific planning PlanNode tree
3.2 PSI source of truth is PlanNode

The product-specific planning tree holds the PSI state.

Conceptually:

prod_tree_dict_OT[product_name] → outbound planning tree
prod_tree_dict_IN[product_name] → inbound planning tree
3.3 PSI bucket structure

The canonical PSI structure is:

node.psi4demand[w] = [S_ids, CO_ids, I_ids, P_ids]
node.psi4supply[w] = [S_ids, CO_ids, I_ids, P_ids]

Bucket index convention:

PSI_S  = 0
PSI_CO = 1
PSI_I  = 2
PSI_P  = 3
3.4 PSI buckets hold Lot_ID lists

The most important rule is:

PSI buckets must contain Lot_ID lists, not numeric quantities.

Correct:

node.psi4demand[w][0] = ["LOT_A", "LOT_B", "LOT_C"]

Incorrect:

node.psi4demand[w][0] = 3

Quantity is calculated as:

quantity = len(node.psi4demand[w][bucket])
quantity = len(node.psi4supply[w][bucket])
3.5 Lot attributes stay outside PSI buckets

PSI buckets hold only Lot_IDs.

Lot attributes are held outside the PSI bucket, for example in:

LotHeader
lot_pool
metadata table
lot attribute dictionary
4. Implemented Files

v0r2 added or updated the following files.

pysi/adapters/__init__.py
pysi/adapters/lot_generation.py
pysi/adapters/psi_seed.py
pysi/adapters/plan_input_pipeline.py
pysi/adapters/weekly_plan_table.py

tests/test_plan_input_lot_generation.py
tests/test_plan_input_psi_seed.py
tests/test_plan_input_pipeline.py
5. Implemented Features
5.1 LotHeader

LotHeader was added as the intermediate representation of generated lots.

It preserves:

lot_id
scenario_id
product_id
node_id
week
plan_type
quantity
lot_size
source_granularity
source_id
sequence_no
quality_status
priority
attributes

attributes can hold case-specific metadata such as:

crop_year
harvest_week
available_week
quality_limit_week
expiry_week
temperature_class
target_region
5.2 LotGenerationConfig

LotGenerationConfig was added to control lot generation behavior.

It supports:

lot_size
quantity_mode
lot_id_prefix
allow_fractional_last_lot
sequence_digits
5.3 Deterministic Lot_ID generation

Lot IDs are generated deterministically from stable row fields and sequence number.

Example:

RICE_AS_IS-BROWN_RICE_STANDARD-PRODUCER_NIIGATA-2026W40-supply-000001

Unsafe characters are sanitized.

5.4 Fractional last lot support

v0r2 supports fractional final lots.

Example:

quantity = 1.6
lot_size = 1.0

generates:

lot 1 quantity = 1.0
lot 2 quantity = 0.6

Important:

Fractional quantity may exist in LotHeader.quantity,
but PSI seed table still stores Lot_ID lists.
5.5 PsiSeedRecord

PsiSeedRecord was added as an intermediate representation between LotHeader and future PSI seeding.

It holds:

scenario_id
product_id
node_id
week
layer
bucket
lot_id
quantity
source_id
5.6 Default plan_type to PSI bucket mapping

v0r2 defines default mapping:

demand → demand/S
S      → demand/S
supply → demand/P
P      → demand/P
initial_inventory → supply/I

This mapping is configurable.

5.7 PSI seed table

v0r2 added an in-memory seed table.

Conceptual structure:

{
    (scenario_id, product_id, node_id, week, layer, bucket): [lot_id, ...]
}

Important:

Seed table values are list[str] of Lot_IDs, not numeric quantities.
5.8 Pipeline helper

v0r2 added a helper pipeline:

WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
in-memory PSI seed table
6. Test Summary

The following tests passed.

python -m pytest tests/test_plan_input_lot_generation.py

Result:

6 passed
python -m pytest tests/test_plan_input_psi_seed.py

Result:

4 passed
python -m pytest tests/test_plan_input_pipeline.py

Result:

3 passed
python -m pytest tests/test_plan_input_granularity_adapter.py

Result:

11 passed

Compatibility checks also passed.

python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py

Result:

both passed
7. Completion Criteria

v0r2 satisfies the intended completion criteria.

[OK] LotHeader exists
[OK] LotGenerationConfig exists
[OK] generate_lots_from_weekly_plan works
[OK] PsiSeedRecord exists
[OK] generate_psi_seed_records works
[OK] build_psi_seed_table works
[OK] monthly and weekly inputs share downstream generation logic
[OK] Rice crop_year metadata can be preserved
[OK] seed table stores Lot_ID lists, not numeric quantities
[OK] focused tests pass
[OK] existing v0r1 adapter tests pass
[OK] no existing loader changes
[OK] no GUI changes
[OK] no planning engine changes
[OK] no live PlanNode mutation
8. Important Boundary

v0r2 intentionally stops before mutating live PlanNode objects.

v0r2 produces:

LotHeader
PsiSeedRecord
in-memory PSI seed table

It does not yet execute:

plan_node.psi4demand[w][bucket_index].extend(lot_id_list)
plan_node.psi4supply[w][bucket_index].extend(lot_id_list)

That belongs to a future v0r3 stage.

9. Relationship to Rice Case

Rice Case can now preserve weekly semantics through the input pipeline.

This is important for:

2026-W40:
    old crop final consumption week
    new crop harvest start week

2026-W41:
    new crop consumption start week

v0r2 can preserve Rice metadata such as:

crop_year
harvest_week
available_week
quality_limit_week

inside LotHeader.attributes.

10. Relationship to Vaccine Case

Vaccine Case can also use this pipeline.

Vaccine-specific metadata can be preserved in LotHeader.attributes.

Examples:

expiry_week
quality_status
temperature_class
target_region
target_node
11. Current Branch Status

Implementation was completed on:

feature/plan-input-granularity-adapter-v0r1

Latest implementation commit:

05419a0 Add plan input lot generation and PSI seed adapter

Design and request commits include:

d6d2f01 Add plan input granularity adapter v0r2 design
4a4cfb7 Add plan input granularity adapter v0r2 Codex request
12. Future Milestones
v0r3: PSI seed table to real PlanNode seeding

Next milestone:

in-memory PSI seed table
    ↓
product-specific PlanNode.psi4demand / psi4supply

This should be done carefully because it touches live WOM planning structures.

v0r4: Existing monthly loader refactor

Future milestone:

existing S_month / P_month loader
    ↓
canonical weekly plan table
    ↓
shared Lot_ID generation
    ↓
shared PSI seeding

This should only happen after v0r3 is stable.

13. Summary

Plan Input Granularity Adapter v0r2 completed the second stage of input-layer normalization.

The pipeline is now:

v0r1:
    monthly / weekly / case_weekly input
        ↓
    canonical weekly plan table

v0r2:
    canonical weekly plan table
        ↓
    LotHeader
        ↓
    PsiSeedRecord
        ↓
    in-memory PSI seed table

This gives WOM a clean and safe path from both monthly and weekly planning inputs toward the V0R8 canonical PSI structure.

The most important achievement is:

The adapter now prepares Lot_ID list seed data without violating V0R8 PSI semantics.

In other words:

PSI buckets remain Lot_ID lists.
Quantity remains len(list).
Lot attributes remain outside the bucket.

This is an important foundation for future safe loading into product-specific PlanNode trees.