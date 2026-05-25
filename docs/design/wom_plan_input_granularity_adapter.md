# WOM Plan Input Granularity Adapter Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-16  
**Status:** Design memo  
**Target path:** `docs/design/wom_plan_input_granularity_adapter.md`

**Related design documents:**

- `docs/design/wom_case_modeling_base_dataset.md`
- `docs/design/case_japanese_rice_master_dataset.md`
- `docs/design/case_japanese_rice_simulation_plan.md`
- `docs/design/case_japanese_rice_crop_year_modeling_addendum.md`
- `docs/design/wom_planning_operations_commands.md`

---

## 1. Purpose

This memo defines the **WOM Plan Input Granularity Adapter**.

The purpose is to separate the following responsibilities:

```text
raw plan input
    ↓
calendar / granularity normalization
    ↓
canonical weekly plan table
    ↓
Lot_ID generation
    ↓
PSI seeding
```

Historically, the WOM loading process has handled monthly `S_month` / `P_month` input, weekly decomposition, Lot_ID generation, and PSI list initialization as a connected flow.

However, WOM Case Modeling now needs to support cases where weekly data already exists.

Examples:

- Japanese Rice Case
- COVID Vaccine Case
- weekly demand / supply scenario cases
- weekly capacity planning cases

For these cases, weekly data should be loaded directly when available.

The adapter should support both:

```text
monthly input mode:
    S_month / P_month

weekly input mode:
    S_week / P_week or case-level weekly supply / demand
```

---

## 2. Background

Current WOM inputs historically include monthly planning data such as:

```text
S_month
P_month
```

The existing loading logic decomposes monthly quantities into weekly quantities and also generates Lot_IDs.

This is useful for existing monthly planning data.

However, for WOM Case Modeling Base Dataset, especially Rice Case and Vaccine Case, weekly data may already be meaningful.

For example, in the Rice Case:

```text
2026-W40:
    old crop final consumption week
    new crop harvest start week

2026-W41:
    new crop consumption start week
```

This weekly boundary is important.

If this weekly structure is first aggregated to month and then decomposed again, the model may lose important semantics.

Therefore, the input layer should explicitly support both monthly and weekly input modes.

---

## 3. Core Design Principle

The core principle is:

```text
If weekly data exists, keep it weekly.

If only monthly data exists, convert it to weekly using an explicit calendar adapter.
```

This means:

```text
weekly input:
    use directly

monthly input:
    convert to weekly

Lot_ID generation:
    common downstream process

PSI seeding:
    common downstream process
```

---

## 4. Current Problem

The current loader conceptually combines:

```text
1. read S_month / P_month
2. decompose monthly data to weekly data
3. generate Lot_IDs
4. seed PSI lists
```

This creates several issues.

### 4.1 Monthly input becomes implicit default

Cases with native weekly data must still fit a monthly input shape.

### 4.2 Weekly semantics can be lost

Important weekly boundary conditions may be blurred.

Example:

```text
Rice Case:
    W40 = old crop final consumption week / new crop harvest start week
    W41 = new crop consumption start week
```

### 4.3 Lot generation cannot be reused easily

If Lot_ID generation is tightly coupled with monthly decomposition, it is harder to reuse for weekly input.

### 4.4 Adapter behavior is unclear

Different case models may need different raw input granularities.

---

## 5. Desired Loading Pipeline

The desired pipeline is:

```text
Raw Plan Input
    ↓
Calendar / Granularity Normalization
    ↓
Canonical Weekly Plan Table
    ↓
Lot_ID Generation
    ↓
PSI Seeding
```

Each stage should be separable.

---

## 6. Raw Plan Input Layer

The raw input layer may receive data in multiple forms.

### 6.1 Monthly input mode

Examples:

```text
S_month
P_month
```

This mode is needed for compatibility with existing WOM data.

### 6.2 Weekly input mode

Examples:

```text
S_week
P_week
weekly demand plan
weekly supply plan
```

This mode is preferred when the case model already defines weekly data.

### 6.3 Case dataset input mode

Examples:

```text
rice_supply_plan.csv
rice_demand_plan.csv
covid_vaccine_supply_plan.csv
covid_vaccine_region_demand.csv
```

These may be business-friendly case datasets that are adapted into weekly plan tables.

---

## 7. Input Mode Definition

Recommended input mode values:

```text
monthly_sp:
    input = S_month / P_month

weekly_sp:
    input = S_week / P_week

case_weekly:
    input = case-specific weekly supply / demand dataset

case_monthly:
    input = case-specific monthly supply / demand dataset
```

Suggested configuration:

```python
plan_input_config = {
    "input_mode": "case_weekly",
    "calendar_mode": "weekly",
    "lot_size": 1,
    "week_key_format": "YYYY-Www",
}
```

---

## 8. Calendar / Granularity Normalization

### 8.1 Purpose

Convert raw plan input to a canonical weekly plan table.

Canonical output:

```text
scenario_id
product_id
node_id
week
plan_type
quantity
source_granularity
```

where:

```text
plan_type:
    S
    P
    demand
    supply
```

### 8.2 Monthly to weekly conversion

If input is monthly, convert to weekly.

Example:

```text
monthly S / P
    ↓
4-4-5 calendar adapter
    ↓
weekly S / P
```

### 8.3 Weekly input pass-through

If input is already weekly, pass through.

```text
weekly supply / demand
    ↓
canonical weekly plan table
```

No month conversion should be applied.

---

## 9. 4-4-5 Calendar Adapter

### 9.1 Purpose

The 4-4-5 calendar adapter should be used when monthly data must be expanded to weekly data.

It should not be forced on cases where weekly data already exists.

### 9.2 4-4-5 mapping

One year has 52 weeks.

```text
Q1:
    M01 = W01-W04
    M02 = W05-W08
    M03 = W09-W13

Q2:
    M04 = W14-W17
    M05 = W18-W21
    M06 = W22-W26

Q3:
    M07 = W27-W30
    M08 = W31-W34
    M09 = W35-W39

Q4:
    M10 = W40-W43
    M11 = W44-W47
    M12 = W48-W52
```

### 9.3 Monthly flow to weekly flow

For flow quantities such as S or P:

```text
weekly_qty = monthly_qty / number_of_weeks_in_month
```

or another explicit distribution rule.

Possible distribution rules:

```text
even:
    distribute evenly across weeks

front_loaded:
    put more quantity in early weeks

back_loaded:
    put more quantity in later weeks

custom_profile:
    use specified weights
```

MVP default:

```text
even
```

### 9.4 Weekly to monthly aggregation

When aggregating weekly results back to monthly reporting:

```text
flow data:
    monthly_qty = sum(weekly_qty)

stock data:
    month_end_qty = inventory at last week of month
    monthly_avg_qty = average weekly inventory
```

### 9.5 Important note

WOM 4-4-5 month is a planning month.

It is not necessarily identical to a calendar month.

---

## 10. Canonical Weekly Plan Table

All input modes should eventually produce the same canonical weekly plan table.

### 10.1 Schema

```csv
scenario_id,product_id,node_id,week,plan_type,quantity,source_granularity,source_id,comment
```

### 10.2 Example: weekly input

```csv
scenario_id,product_id,node_id,week,plan_type,quantity,source_granularity,source_id,comment
RICE_AS_IS,BROWN_RICE_STANDARD,PRODUCER_NIIGATA,2026-W40,supply,20,weekly,rice_supply_plan,2026 harvest
RICE_AS_IS,PACKAGED_RICE_STANDARD,DEMAND_HOUSEHOLD_TOKYO,2027-W01,demand,1.0,weekly,rice_demand_plan,household demand
```

### 10.3 Example: monthly input after conversion

```csv
scenario_id,product_id,node_id,week,plan_type,quantity,source_granularity,source_id,comment
BASE,PRODUCT_X,DAD_US,2026-W01,S,25,monthly_445,S_month,M01 even split
```

---

## 11. Lot_ID Generation

### 11.1 Purpose

Convert canonical weekly quantities into Lot_ID lists.

This stage should be independent from monthly / weekly input origin.

Input:

```text
canonical weekly plan table
lot_size
lot_id rule
product_id
node_id
week
```

Output:

```text
lot_id list
lot header records
```

### 11.2 Lot generation rule

If quantity is expressed as lot count:

```text
lot_count = quantity
```

If quantity is physical quantity:

```text
lot_count = ceil(quantity / lot_size)
```

The conversion rule should be explicit.

### 11.3 Suggested Lot_ID format

```text
{scenario_id}-{product_id}-{node_id}-{week}-{seq}
```

Example:

```text
RICE_AS_IS-BROWN_RICE_STANDARD-PRODUCER_NIIGATA-2026W40-000001
```

### 11.4 Lot header fields

Recommended fields:

```text
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
crop_year
quality_status
priority
```

For Rice Case, include:

```text
crop_year
harvest_week
available_week
quality_limit_week
```

---

## 12. PSI Seeding

### 12.1 Purpose

Seed generated lots into WOM PSI structures.

Examples:

```text
psi4demand[week][bucket]
psi4supply[week][bucket]
```

### 12.2 Bucket mapping

Suggested mapping:

```text
demand plan:
    S bucket in psi4demand

supply plan:
    P bucket in psi4demand or seed supply depending on planning mode

external supply:
    P / inventory seed depending on node role

initial inventory:
    I bucket or initial inventory structure
```

This mapping may differ by case and should be adapter-configurable.

### 12.3 Common PSI seeding function

Recommended function concept:

```python
seed_weekly_plan_to_psi(
    weekly_plan,
    lot_headers,
    target_layer="demand",
    bucket_mapping=...
)
```

This function should not care whether the original input was monthly or weekly.

---

## 13. Rice Case Application

### 13.1 Recommended input mode

Rice Case should use:

```text
input_mode = case_weekly
```

Reason:

Rice Case has important weekly semantics:

```text
W40:
    old crop final consumption week
    new crop harvest start week

W41:
    new crop consumption start week
```

These should not be flattened into monthly input.

### 13.2 Rice weekly inputs

Rice Case should define:

```text
rice_supply_plan.csv:
    weekly supply / harvest / carryover

rice_demand_plan.csv:
    weekly demand

rice_capacity_master.csv:
    weekly or repeatable weekly capacity

rice_cost_price_master.csv:
    weekly or scenario-level cost / price
```

### 13.3 Rice-specific lot fields

Lot generation should preserve:

```text
crop_year
harvest_week
available_week
expected_consumption_start_week
expected_consumption_end_week
quality_limit_week
```

### 13.4 Rice output expectation

Rice input adapter should support:

```text
crop-year inventory tracking
inventory by crop year
3-year horizon
2027 main evaluation year
```

---

## 14. Vaccine Case Application

### 14.1 Recommended input mode

COVID Vaccine Case should also use:

```text
input_mode = case_weekly
```

Reason:

Vaccine supply and demand are naturally weekly in the current case.

### 14.2 Vaccine weekly inputs

Vaccine Case should define:

```text
weekly vaccine supply
regional weekly demand
weekly transport capacity
weekly vaccination capacity
```

### 14.3 Vaccine lot fields

Lot generation should preserve:

```text
expiry_week
quality_status
temperature_class
target_region
```

---

## 15. Current WOM Compatibility

### 15.1 Existing monthly input support

The adapter must preserve the existing monthly path.

```text
S_month / P_month
    ↓
monthly_to_weekly
    ↓
Lot_ID generation
    ↓
PSI seeding
```

### 15.2 New weekly input support

Add weekly path:

```text
S_week / P_week or case_weekly data
    ↓
weekly normalization
    ↓
Lot_ID generation
    ↓
PSI seeding
```

### 15.3 No immediate breaking change

The first implementation should avoid breaking current WOM loaders.

A safe implementation approach is:

```text
1. create new adapter modules
2. add smoke tests
3. keep existing monthly loader intact
4. later refactor common Lot_ID generation and PSI seeding
```

---

## 16. Suggested Modules

Potential future modules:

```text
pysi/adapters/plan_input_granularity.py
pysi/adapters/calendar_445.py
pysi/adapters/weekly_plan_table.py
pysi/adapters/lot_generation.py
pysi/adapters/psi_seeding.py
```

or case-local versions:

```text
pysi/cases/japanese_rice/adapters/...
```

---

## 17. Test Policy

### 17.1 Monthly mode tests

```text
1. monthly S/P input is converted to 52 weekly rows
2. 4-4-5 mapping creates correct week groups
3. flow quantities are summed correctly
4. stock quantities use month-end or average rule
```

### 17.2 Weekly mode tests

```text
1. weekly input passes through without calendar conversion
2. week keys are preserved
3. W40 / W41 boundary remains intact
4. Lot_ID generation works for weekly data
5. PSI seeding works for weekly data
```

### 17.3 Rice case tests

```text
1. 2026-W40 and 2026-W41 are preserved
2. crop_year fields are preserved in lot headers
3. 3-year horizon creates 156 weeks
4. inventory by crop year can be calculated
```

---

## 18. Implementation Roadmap

### Phase 1: Design

Create this memo and keep current loader unchanged.

### Phase 2: Weekly Plan Table MVP

Implement canonical weekly plan table for case datasets.

### Phase 3: 4-4-5 Calendar Adapter

Implement monthly-to-weekly conversion.

### Phase 4: Common Lot_ID Generation

Extract Lot_ID generation from current monthly loader.

### Phase 5: Common PSI Seeding

Extract PSI seeding from current loader.

### Phase 6: Rice Case Integration

Use weekly input mode for Rice Case.

### Phase 7: Current WOM Loader Refactor

Optionally refactor current monthly loader to use the new shared pipeline.

---

## 19. Summary

The key design principle is:

```text
Weekly data should remain weekly.
Monthly data should be explicitly converted to weekly.
Lot_ID generation and PSI seeding should be common downstream processes.
```

Recommended final structure:

```text
monthly input mode:
    S_month / P_month
        ↓
    4-4-5 or calendar adapter
        ↓
    canonical weekly plan table
        ↓
    Lot_ID generation
        ↓
    PSI seeding

weekly input mode:
    S_week / P_week or case_weekly data
        ↓
    canonical weekly plan table
        ↓
    Lot_ID generation
        ↓
    PSI seeding
```

This design allows WOM to support both:

```text
existing monthly CSV assets
```

and:

```text
new weekly case modeling datasets
```

without forcing one into the other.
