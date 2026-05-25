# Rice Case Weekly Input to PlanNode Seed Integration Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-17  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of the **Rice Case Weekly Input to PlanNode Seed Integration**.

The purpose of this integration was to confirm that Japanese Rice Case weekly supply / demand data can flow through the new WOM Plan Input Granularity Adapter pipeline and safely seed product-specific PlanNode PSI buckets.

The target flow was:

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

This integration verifies that Rice Case data can enter the WOM planning layer through the normalized input pipeline while preserving V0R8 PSI semantics.

2. Background

Before this integration, the Plan Input Granularity Adapter had completed the following stages.

v0r1: Input granularity normalization
monthly / weekly / case_weekly input
    ↓
canonical WeeklyPlanRow
v0r2: Lot and PSI seed generation
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
in-memory PSI seed table
v0r3: PlanNode PSI seeding adapter
PsiSeedRecord
    ↓
product-specific PlanNode.psi4demand / psi4supply

This Rice Case integration used those adapter layers to validate a concrete case flow.

3. Core Assumption

The integration follows the WOM / PySI V0R8 canonical PSI structure.

node.psi4demand[w] = [S_ids, CO_ids, I_ids, P_ids]
node.psi4supply[w] = [S_ids, CO_ids, I_ids, P_ids]

Bucket index convention:

PSI_S  = 0
PSI_CO = 1
PSI_I  = 2
PSI_P  = 3

The most important rule is:

PSI buckets contain Lot_ID lists, not numeric quantities.

Correct:

node.psi4demand[w][PSI_S] = ["LOT_A", "LOT_B", "LOT_C"]

Incorrect:

node.psi4demand[w][PSI_S] = 3

Quantity remains:

quantity = len(node.psi4demand[w][bucket])
4. Implemented Files

This integration added or updated the following files.

pysi/cases/japanese_rice/__init__.py
pysi/cases/japanese_rice/rice_plan_input_integration.py
tests/test_japanese_rice_plan_input_integration.py
5. Implemented Features
5.1 Rice week indexer

Implemented a deterministic week indexer for the 3-year Rice Case horizon.

2026-W01 to 2028-W52

Expected mappings:

week_indexer["2026-W01"] == 0
week_indexer["2026-W40"] == 39
week_indexer["2026-W41"] == 40
week_indexer["2027-W01"] == 52
week_indexer["2028-W52"] == 155

This protects the important Rice Case W40 / W41 boundary.

5.2 Rice weekly plan rows

Implemented conversion from Rice Case weekly data into WeeklyPlanRow.

The integration supports:

Rice demand rows
    → WeeklyPlanRow(plan_type="demand")

Rice supply / harvest rows
    → WeeklyPlanRow(plan_type="supply")

Default mapping:

demand row
    ↓
WeeklyPlanRow(plan_type="demand")
    ↓
PsiSeedRecord(layer="demand", bucket="S")
    ↓
PlanNode.psi4demand[w][S]
supply / harvest row
    ↓
WeeklyPlanRow(plan_type="supply")
    ↓
PsiSeedRecord(layer="demand", bucket="P")
    ↓
PlanNode.psi4demand[w][P]
5.3 Crop-year metadata preservation

The integration preserves Rice Case crop-year metadata in LotHeader.attributes.

Required metadata includes:

crop_year
harvest_week
available_week
quality_limit_week

This is important for the Rice Case crop-year model:

2025 crop carryover
2026 crop harvest / consumption cycle
2027 crop harvest / consumption cycle
5.4 Mock PlanNode seeding

The integration verifies that Rice-generated seed records can be seeded into mock PlanNode PSI buckets.

Confirmed behavior:

demand rows → psi4demand[w][S]
supply rows → psi4demand[w][P]

The test confirms that PSI buckets contain Lot_ID strings, not numeric quantities.

5.5 W40 / W41 boundary preservation

The integration confirms:

2026-W40 → week index 39
2026-W41 → week index 40

This preserves the Rice Case boundary rule:

W40:
    old crop final consumption week
    new crop harvest start week

W41:
    new crop consumption start week
6. Test Summary

The following new integration test passed.

python -m pytest tests/test_japanese_rice_plan_input_integration.py

Result:

4 passed

Compatibility tests also passed:

python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_plan_input_granularity_adapter.py
python -m pytest tests/test_plan_input_lot_generation.py
python -m pytest tests/test_plan_input_psi_seed.py
python -m pytest tests/test_plan_input_pipeline.py
python -m pytest tests/test_plan_input_plan_node_seeding.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py

All focused adapter and case smoke tests passed.

7. Completion Criteria

This integration satisfies the intended completion criteria.

[OK] Rice weekly data can produce WeeklyPlanRow records
[OK] Rice WeeklyPlanRows can produce LotHeader records
[OK] crop_year metadata is preserved in LotHeader.attributes
[OK] Rice WeeklyPlanRows can produce PsiSeedRecord records
[OK] Rice PsiSeedRecords can seed mock PlanNode PSI buckets
[OK] demand rows seed to psi4demand[w][S]
[OK] supply rows seed to psi4demand[w][P]
[OK] W40 / W41 boundary is preserved
[OK] PSI buckets contain Lot_ID lists, not quantities
[OK] existing Rice smoke test remains compatible
[OK] no GUI changes
[OK] no run_full_plan changes
[OK] no existing monthly loader refactor
[OK] no Backward / Forward Planning execution
8. Latest Commit

Implementation was completed with:

9577d5d Add Rice case weekly input to PlanNode seed integration
9. Meaning of This Milestone

This milestone proves that Rice Case data can enter the WOM planning layer through the new normalized input pipeline.

The completed flow is:

Rice weekly supply / demand data
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
mock PlanNode.psi4demand

This is a major step from case-specific smoke simulation toward real WOM planning integration.

10. Important Boundary

This integration intentionally stops before full WOM planning execution.

It does not yet perform:

Backward Planning
Forward Planning
demand-to-supply bridge
real product-specific PlanNode tree integration
existing monthly loader refactor
GUI case loading
Management Issue Generation

The current integration uses mock PlanNodes to validate the PSI seeding contract.

11. Future Milestones
Next: Real product-specific PlanNode tree integration

Future target:

Rice weekly input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
prod_tree_dict_OT / prod_tree_dict_IN PlanNode seeding

This will connect the adapter to real WOM product-specific planning trees.

Later: Existing monthly loader refactor

Future target:

S_month / P_month
    ↓
4-4-5 or calendar adapter
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
PlanNode PSI seed

This should be done only after the adapter pipeline is stable.

Later: GUI case loading

Future target:

GUI selects Rice Case
    ↓
case dataset load
    ↓
PlanNode seed
    ↓
WOM planning sequence
12. Summary

This integration confirms that the Rice Case can use the new WOM input normalization pipeline.

The key achievement is:

Rice weekly data can now be transformed into V0R8-compatible PlanNode PSI seed data.

The most important invariant remains intact:

PSI buckets hold Lot_ID lists.
Quantity is len(list).
Lot attributes live outside the PSI bucket.

This milestone connects the Rice Case Modeling Process to the WOM planning layer in a safe, testable, and V0R8-compatible way.