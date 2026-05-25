# Japanese Rice Crop-Year Modeling Addendum

**Version:** v0r1 draft  
**Date:** 2026-05-16  
**Status:** Design addendum  
**Target path:** `docs/design/case_japanese_rice_crop_year_modeling_addendum.md`

**Related design documents:**

- `docs/design/case_japanese_rice_supply_chain_as_is_research.md`
- `docs/design/case_japanese_rice_supply_chain_modeling.md`
- `docs/design/case_japanese_rice_master_dataset.md`
- `docs/design/case_japanese_rice_simulation_plan.md`
- `docs/design/wom_case_modeling_base_dataset.md`

---

## 1. Purpose

This addendum defines the **crop-year / harvest-cohort treatment** for the Japanese Rice Supply Chain WOM case.

The purpose is to correct the limitation of the initial Rice Case MVP, which used a 52-week calendar-year horizon.

For rice, a single calendar year is not enough.

Rice harvested in a given year is typically consumed over the period from that harvest season to the next harvest season. Therefore, the Rice Case should explicitly model:

- old-crop carryover inventory
- new-crop harvest
- old-crop / new-crop transition
- crop-year inventory drawdown
- crop-year inventory value
- main evaluation year

This addendum should be used before revising the four Rice Case design documents.

---

## 2. Core Issue

The earlier Rice Case MVP used:

```text
planning horizon:
    2026-W01 to 2026-W52
```

This was useful for smoke-testing the adapter and PSI / cost / KPI output flow.

However, it is not sufficient for representing rice supply-demand behavior.

Reason:

```text
2026-W40 harvested rice is not fully consumed by 2026-W52.
It is consumed mainly until the next harvest season around 2027-W40.
```

Therefore, evaluating the 2026 crop only through 2026-W52 makes the ending inventory look artificially high and the fill rate artificially low.

The issue is not necessarily operational failure. It may simply be that the crop-year consumption period is not complete yet.

---

## 3. Recommended Planning Horizon

The recommended Rice Case planning horizon is:

```text
2026-W01 to 2028-W52
```

This creates a three-year horizon.

The three-year horizon allows WOM to represent:

```text
2026:
    consumption of 2025 crop carryover
    harvest of 2026 crop

2027:
    main evaluation year
    consumption of 2026 crop in the first half
    harvest and transition to 2027 crop in the second half

2028:
    tail observation of 2027 crop consumption
```

---

## 4. Main Evaluation Year

The recommended main evaluation year is:

```text
2027
```

Reason:

```text
2027-W01 to 2027-W40:
    consumption of 2026 crop inventory

2027-W40:
    boundary week between 2026 crop and 2027 crop

2027-W41 to 2027-W52:
    initial consumption of 2027 crop
```

This makes 2027 the best year for evaluating a full rice supply-demand cycle.

---

## 5. Crop Cohort Cycles

The initial crop cohort cycles should be defined as follows.

```text
2025 crop inventory:
    consumed during 2026-W01 to 2026-W40

2026 crop:
    harvested during 2026-W40 to 2026-W44
    consumed mainly during 2026-W41 to 2027-W40

2027 crop:
    harvested during 2027-W40 to 2027-W44
    consumed mainly during 2027-W41 to 2028-W40
```

---

## 6. W40 / W41 Boundary Rule

The boundary rule is:

```text
W40:
    old crop consumption final week
    new crop harvest start week

W41:
    new crop consumption start week
```

This means W40 has two meanings:

```text
W40 is:
    the final consumption week of the previous crop
    the first harvest week of the new crop
```

W41 is the first week in which the new crop is assumed to be available for normal consumption.

---

## 7. Why New Crop Consumption Starts in W41

Even if harvest starts in W40, newly harvested rice is not generally available for all market consumption in the same week.

There are intermediate steps:

```text
harvest
drying / adjustment
collection
inspection
storage
milling
packaging
shipment
retail availability
```

Therefore, the initial WOM Rice Case should use:

```text
harvest week:
    W40

new crop consumption start:
    W41
```

This provides a clean and practical weekly modeling convention.

---

## 8. Required Lot Header Extensions

Rice lot headers should include crop-year fields.

### 8.1 New-crop lot example

```python
lot = {
    "lot_id": "RICE-JP-2026W40-000001",
    "product_id": "BROWN_RICE_STANDARD",
    "crop_year": "2026",
    "origin_region": "NIIGATA",
    "harvest_week": "2026-W40",
    "available_week": "2026-W41",
    "expected_consumption_start_week": "2026-W41",
    "expected_consumption_end_week": "2027-W40",
    "quality_limit_week": "2027-W40",
    "current_node": "COLLECTION_NIIGATA",
    "quality_grade": "standard",
    "brand_class": "domestic_standard",
    "quantity_kg": 1000,
}
```

### 8.2 Old-crop carryover lot example

```python
lot = {
    "lot_id": "RICE-JP-2025-CARRYOVER-000001",
    "product_id": "BROWN_RICE_STANDARD",
    "crop_year": "2025",
    "harvest_week": "2025-W40",
    "available_week": "2026-W01",
    "expected_consumption_start_week": "2026-W01",
    "expected_consumption_end_week": "2026-W40",
    "quality_limit_week": "2026-W40",
    "current_node": "BROWN_STORAGE_EAST",
    "quality_grade": "standard",
    "brand_class": "domestic_standard",
    "quantity_kg": 1000,
}
```

---

## 9. Required Master Dataset Extensions

The following Rice Case master files should be extended.

### 9.1 `rice_scenario_master.csv`

Add:

```text
main_evaluation_year
```

Example:

```csv
scenario_id,scenario_name,baseline_scenario_id,description,start_week,end_week,main_evaluation_year,scenario_type,is_baseline,comment
RICE_AS_IS,Rice AS-IS,,Current simplified Japanese rice supply chain,2026-W01,2028-W52,2027,AS_IS,true,baseline scenario
```

### 9.2 `rice_lot_master.csv`

Add or ensure:

```text
crop_year
harvest_week
available_week
expected_consumption_start_week
expected_consumption_end_week
quality_limit_week
```

### 9.3 `rice_supply_plan.csv`

Add:

```text
crop_year
```

Example:

```csv
scenario_id,node_id,product_id,crop_year,week,supply_qty,supply_type,source_type,comment
RICE_AS_IS,BROWN_STORAGE_EAST,BROWN_RICE_STANDARD,2025,2026-W01,80,old_crop_carryover,initial_inventory,2025 crop carryover inventory
RICE_AS_IS,PRODUCER_NIIGATA,BROWN_RICE_STANDARD,2026,2026-W40,20,harvest,internal,2026 harvest peak week 1
RICE_AS_IS,PRODUCER_NIIGATA,BROWN_RICE_STANDARD,2027,2027-W40,20,harvest,internal,2027 harvest peak week 1
```

### 9.4 `rice_demand_plan.csv`

Demand should cover the full three-year horizon:

```text
2026-W01 to 2028-W52
```

At minimum, the adapter may generate repeated weekly demand rows.

### 9.5 `rice_assumption_log.csv`

Add assumptions:

```csv
scenario_id,assumption_id,category,description,value,source,confidence,comment
RICE_AS_IS,ASSUMP_HORIZON,TIME,Planning horizon is 2026-W01 to 2028-W52,3 years,model assumption,high,needed to observe crop-year cycles
RICE_AS_IS,ASSUMP_EVAL_YEAR,TIME,Main evaluation year is 2027,2027,model assumption,high,2027 shows old-crop consumption and new-crop transition
RICE_AS_IS,ASSUMP_2025_CARRYOVER,TIME,2025 crop carryover is consumed during 2026-W01 to 2026-W40,W01-W40,model assumption,medium,boundary convention
RICE_AS_IS,ASSUMP_NEW_CROP_START,TIME,New crop is harvested from W40 and consumed from W41,W40 harvest W41 consumption,model assumption,medium,one-week availability lag
```

---

## 10. Required Output Extensions

The Rice smoke runner and future implementation should produce inventory by crop year.

Recommended output:

```text
rice_inventory_by_crop_year.csv
```

Suggested schema:

```csv
scenario_id,week,product_id,crop_year,inventory_qty,inventory_value,comment
```

Example:

```csv
scenario_id,week,product_id,crop_year,inventory_qty,inventory_value,comment
RICE_AS_IS,2027-W01,PACKAGED_RICE_STANDARD,2026,75,37500000,2026 crop inventory
RICE_AS_IS,2027-W40,PACKAGED_RICE_STANDARD,2026,10,5000000,2026 crop remaining before 2027 crop
RICE_AS_IS,2027-W41,PACKAGED_RICE_STANDARD,2027,20,10000000,2027 crop begins consumption
```

---

## 11. Required Visualization Extensions

The most important revised visualization is:

```text
Inventory by Crop Year
```

This chart should be a stacked weekly inventory chart:

```text
2025 crop inventory
2026 crop inventory
2027 crop inventory
```

Expected visual interpretation:

```text
2026-W01 to 2026-W40:
    2025 crop inventory declines

2026-W40 to 2026-W44:
    2026 crop inventory rises

2027-W01 to 2027-W40:
    2026 crop inventory declines

2027-W40 to 2027-W44:
    2027 crop inventory rises

2027-W41 onward:
    2027 crop inventory starts to be consumed
```

This is the key chart that makes Rice Case understandable.

---

## 12. Required Smoke Runner v2 Changes

The next Rice smoke runner should be revised from a 52-week smoke test to a 3-year crop-cycle smoke test.

### 12.1 Input

```text
planning horizon:
    2026-W01 to 2028-W52

main evaluation year:
    2027

initial old crop:
    2025 crop carryover = 80 lots

2026 harvest:
    W40: 20 lots
    W41: 30 lots
    W42: 30 lots
    W43: 15 lots
    W44: 5 lots

2027 harvest:
    W40: 20 lots
    W41: 30 lots
    W42: 30 lots
    W43: 15 lots
    W44: 5 lots

weekly demand:
    household: 1.0 lot/week
    food service: 0.6 lot/week

storage capacity:
    100 lots

milling capacity:
    5 lots/week

transport capacity:
    5 lots/week
```

### 12.2 Expected output

```text
old crop consumption:
    2025 crop inventory declines during 2026-W01 to 2026-W40

2026 crop:
    harvested during 2026-W40 to 2026-W44
    inventory consumed through 2027-W40

2027 evaluation year:
    first half consumes 2026 crop
    W40 begins 2027 harvest
    W41 begins 2027 crop consumption

inventory by crop year:
    visible for 2025 / 2026 / 2027
```

---

## 13. Impact on Existing Design Documents

The following documents should be updated by adding references to this addendum rather than replacing the full detailed content.

```text
case_japanese_rice_supply_chain_as_is_research.md
case_japanese_rice_supply_chain_modeling.md
case_japanese_rice_master_dataset.md
case_japanese_rice_simulation_plan.md
```

Recommended approach:

1. Add a short note near the beginning of each document.
2. Add a reference to this addendum.
3. Update only the specific horizon / crop-year sections as needed.
4. Preserve existing detailed schemas and sample rows.

Suggested note:

```text
Note:
For crop-year and 3-year horizon treatment, see
docs/design/case_japanese_rice_crop_year_modeling_addendum.md.
```

---

## 14. Summary

The Rice Case should be modeled using:

```text
planning horizon:
    2026-W01 to 2028-W52

main evaluation year:
    2027

crop cohort cycles:
    2025 crop carryover:
        consumed during 2026-W01 to 2026-W40

    2026 crop:
        harvested during 2026-W40 to 2026-W44
        consumed mainly during 2026-W41 to 2027-W40

    2027 crop:
        harvested during 2027-W40 to 2027-W44
        consumed mainly during 2027-W41 to 2028-W40
```

The key modeling principle is:

```text
Rice is not only a calendar-year product.

It is a crop-year inventory cycle.

WOM should model old-crop carryover,
new-crop harvest,
new-crop consumption,
and crop-year inventory transition
over a multi-year horizon.
```

The next implementation step is:

```text
Rice Case smoke runner v2:
    3-year crop-cycle horizon
    crop-year inventory tracking
    2027 main evaluation summary
```
