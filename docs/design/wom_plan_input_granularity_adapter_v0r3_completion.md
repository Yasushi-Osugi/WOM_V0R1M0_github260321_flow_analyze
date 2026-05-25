# WOM Plan Input Granularity Adapter v0r3 Completion Memo
## PSI Seed Records → Product-Specific PlanNode Seeding

**Version:** v0r3 completion  
**Date:** 2026-05-17  
**Status:** Completion memo  
**Branch:** `feature/plan-input-granularity-adapter-v0r1`

---

## 1. Purpose

This memo summarizes the completion status of **WOM Plan Input Granularity Adapter v0r3**.

The purpose of v0r3 was to safely connect the v0r2 in-memory PSI seed layer to WOM / PySI V0R8-compatible PlanNode PSI structures.

v0r1 normalized input granularity:

```text
monthly / weekly / case_weekly input
    ↓
canonical WeeklyPlanRow

v0r2 generated lot-level seed data:

WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
in-memory PSI seed table

v0r3 implemented the next bridge:

PsiSeedRecord
    ↓
product-specific PlanNode.psi4demand / psi4supply
2. Core Planning Image

v0r3 is based on the following WOM / PySI V0R8 planning image:

Generated Lot_IDs are seeded first into psi4demand[w][S].

Backward Planning propagates these demand lots across
psi4demand[w][S, CO, I, P]
and through the product-specific planning tree.

After demand allocation is completed,
the resulting demand-side plan is copied or bridged into psi4supply.

Forward Planning then moves Lot_IDs across
psi4supply[w][S, CO, I, P]
as supply execution / simulation.

This is the key interpretation of the Plan Input Adapter pipeline.

3. Critical WOM / PySI V0R8 Assumptions

v0r3 preserves the following assumptions.

3.1 Physical node and planning PlanNode are different

WOM has two node worlds:

Physical layer:
    product-independent GUI / map / NetworkX node world

Planning layer:
    product-specific PlanNode tree world

v0r3 targets the planning layer only.

It does not seed physical GUI nodes.

3.2 PSI source of truth is product-specific PlanNode

The intended final target is:

prod_tree_dict_OT[product_name] → outbound planning tree
prod_tree_dict_IN[product_name] → inbound planning tree

Each PlanNode holds:

node.psi4demand[w] = [S_ids, CO_ids, I_ids, P_ids]
node.psi4supply[w] = [S_ids, CO_ids, I_ids, P_ids]
3.3 PSI buckets contain Lot_ID lists

The most important invariant is:

PSI buckets contain Lot_ID lists, not numeric quantities.

Correct:

node.psi4demand[w][0] = ["LOT_A", "LOT_B", "LOT_C"]

Incorrect:

node.psi4demand[w][0] = 3

Quantity remains:

quantity = len(node.psi4demand[w][bucket])
quantity = len(node.psi4supply[w][bucket])
3.4 Lot attributes remain outside PSI buckets

PSI buckets contain only Lot_IDs.

Lot attributes are held in:

LotHeader
lot_pool
metadata table
lot attribute dictionary

Examples:

crop_year
harvest_week
expiry_week
quality_status
unit cost
origin node
target region
priority
4. Implemented Files

v0r3 added or updated the following files:

pysi/adapters/__init__.py
pysi/adapters/plan_node_seeding.py
tests/test_plan_input_plan_node_seeding.py
5. Implemented Features
5.1 PSI bucket constants

v0r3 defines the PSI bucket index mapping:

PSI_BUCKET_INDEX = {
    "S": 0,
    "CO": 1,
    "I": 2,
    "P": 3,
}
5.2 PlanNodeSeedingResult

v0r3 introduced PlanNodeSeedingResult.

It records:

scenario_id
product_id
seeded_count
skipped_count
missing_node_ids
invalid_weeks
invalid_buckets
seeded_by_key
dry_run

This makes PlanNode seeding auditable and testable.

5.3 apply_psi_seed_records_to_plan_nodes

v0r3 implemented:

apply_psi_seed_records_to_plan_nodes(...)

This function takes PsiSeedRecord rows and safely appends lot_id strings into the target PlanNode PSI bucket.

Conceptual behavior:

PsiSeedRecord(layer="demand", bucket="S")
    ↓
plan_node.psi4demand[w][0].append(lot_id)
PsiSeedRecord(layer="demand", bucket="P")
    ↓
plan_node.psi4demand[w][3].append(lot_id)
PsiSeedRecord(layer="supply", bucket="I")
    ↓
plan_node.psi4supply[w][2].append(lot_id)
5.4 Safe missing node handling

If a seed record references a missing node:

record missing_node_id
skip seed record

No new node is created automatically.

5.5 Safe invalid week handling

If a seed record references an invalid week:

record invalid week
skip seed record

The PSI horizon is not extended silently.

5.6 Invalid layer / bucket handling

Invalid layer or bucket is handled deterministically.

In the implemented behavior:

invalid layer / bucket → ValueError

This keeps failures explicit.

5.7 Dry-run mode

v0r3 supports dry-run mode.

When:

dry_run=True

the adapter reports what would be seeded, but does not mutate the target PlanNode.

This is important for future safe integration into existing loaders.

5.8 Append-only behavior

v0r3 appends Lot_IDs to existing PSI buckets.

It does not overwrite existing bucket contents.

Correct behavior:

target_bucket.append(seed_record.lot_id)

or grouped equivalent:

target_bucket.extend(lot_ids)

This preserves existing seeded lots.

5.9 Lot_ID only insertion

v0r3 inserts only:

seed_record.lot_id

It does not insert:

seed_record.quantity

This preserves V0R8 PSI semantics.

5.10 Rice W40 / W41 boundary test

v0r3 includes a test confirming that Rice Case weekly boundaries are preserved:

2026-W40 → week index 39
2026-W41 → week index 40

This protects the old-crop / new-crop boundary logic needed by Rice Case.

6. Test Summary

The following tests passed.

python -m pytest tests/test_plan_input_plan_node_seeding.py

Result:

11 passed
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

Compatibility checks also passed:

python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py

Result:

both passed
7. Completion Criteria

v0r3 satisfies the intended completion criteria.

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
[OK] Rice smoke test remains compatible
[OK] COVID vaccine smoke test remains compatible
[OK] no GUI changes
[OK] no existing loader changes
[OK] no planning engine changes
8. Important Boundary

v0r3 intentionally does not execute planning logic.

It does not run:

Backward Planning
Forward Planning
psi4demand → psi4supply bridge
existing monthly loader refactor
GUI integration

v0r3 only seeds Lot_IDs into target PSI buckets.

This keeps the layer safe and testable.

9. Current Branch Status

Implementation was completed on:

feature/plan-input-granularity-adapter-v0r1

Latest implementation commit:

94ac7d9 Add plan input PlanNode PSI seeding adapter

Related commits:

adbd1fd Add plan input granularity adapter MVP
d6d2f01 Add plan input granularity adapter v0r2 design
4a4cfb7 Add plan input granularity adapter v0r2 Codex request
05419a0 Add plan input lot generation and PSI seed adapter
f87631d Add plan input granularity adapter v0r2 completion memo
a7c1788 Add plan input granularity adapter v0r3 PlanNode seeding design
9985304 Add plan input granularity adapter v0r3 PlanNode seeding Codex request
94ac7d9 Add plan input PlanNode PSI seeding adapter
10. Pipeline Completion Status

The Plan Input Granularity Adapter now has three completed stages.

v0r1
monthly / weekly / case_weekly
    ↓
canonical WeeklyPlanRow
v0r2
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
in-memory PSI seed table
v0r3
PsiSeedRecord
    ↓
product-specific PlanNode.psi4demand / psi4supply
11. Future Milestones
v0r4: Existing monthly loader refactor

Future goal:

existing S_month / P_month loader
    ↓
canonical WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
PlanNode seeding

This should be done only after v0r3 is stable.

v0r5: Rice Case direct weekly input integration

Future goal:

Rice Case weekly master dataset
    ↓
case_weekly input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
PlanNode seeding

This will allow Rice Case data to enter the real WOM planning layer more directly.

v0r6: GUI / case selection integration

Future goal:

GUI selects case dataset
    ↓
adapter loads weekly or monthly input
    ↓
PlanNode PSI seed
    ↓
WOM planning sequence

This should come later.

12. Summary

Plan Input Granularity Adapter v0r3 completed the safe bridge from adapter-generated seed records to V0R8-compatible PSI buckets.

The completed pipeline is:

monthly / weekly / case_weekly input
    ↓
canonical WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
PlanNode.psi4demand / psi4supply

The most important achievement is:

WOM can now safely seed Lot_IDs into product-specific PlanNode PSI buckets
without violating V0R8 PSI semantics.

The core invariant remains intact:

PSI buckets hold Lot_ID lists.
Quantity is len(list).
Lot attributes live outside the PSI bucket.

This completes the first safe path from normalized plan input toward real WOM planning structures.