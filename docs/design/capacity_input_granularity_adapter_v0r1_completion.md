# Capacity Input Granularity Adapter v0r1 Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-19  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **WOM Capacity Input Granularity Adapter v0r1**.

The purpose of this milestone was to add a safe, isolated adapter layer that normalizes capacity input into canonical weekly capacity rows.

The target flow was:

```text
monthly capacity input
or
weekly capacity input
    ↓
Canonical WeeklyCapacityRow
    ↓
env.weekly_capability-like dictionary
```

This milestone is intentionally additive.

It does not modify:

```text
GUI
run_full_plan
existing planning engines
existing monthly loaders
capacity_provider_monthly_csv plugin
```

---

## 2. Background

Before this milestone, WOM already had a capacity provider plugin:

```text
pysi/plugins/capacity_provider_monthly_csv/plugin.py
```

That plugin reads:

```text
sku_P_month_data.csv
```

and builds:

```text
env.weekly_capability[product][MOMxxx] = [cap_lot per week]
env.weekly_capability_df
```

However, the current plugin uses a simplified conversion rule:

```text
1 month = 4 weeks
```

The new Plan Input Granularity Adapter uses a 4-4-5 calendar.

Therefore, capacity input needed its own normalization layer so that monthly / weekly capacity input can be treated explicitly and consistently.

---

## 3. Design Principle

The key design principle is:

```text
Capacity input should be normalized independently from demand / supply plan input.
```

Demand / supply plan input answers:

```text
What is required or planned?
```

Capacity input answers:

```text
What is possible?
```

Therefore, WOM should distinguish:

```text
P_month plan:
    production requirement / planned production quantity

P_capacity_month:
    production capacity limit for MOM / production node

S_month supply:
    supply / shipment / sales quantity depending on context
```

This distinction is important because `sku_P_month_data.csv` has historically been overloaded.

---

## 4. Implemented Files

This milestone added or updated:

```text
pysi/adapters/__init__.py
pysi/adapters/capacity_input_granularity.py
tests/test_capacity_input_granularity_adapter.py
```

---

## 5. Implemented Dataclasses

### 5.1 WeeklyCapacityRow

`WeeklyCapacityRow` was added as the canonical weekly capacity representation.

It contains:

```text
scenario_id
product_id
capacity_owner_type
capacity_owner_id
week
capacity_type
capacity_qty
cap_mode
unit
source_granularity
source_id
comment
```

Conceptually:

```text
Any capacity input
    ↓
WeeklyCapacityRow
```

---

### 5.2 MonthlyCapacityInputRow

`MonthlyCapacityInputRow` was added to represent monthly capacity input.

Example use:

```text
MOM_CHINA can produce 400 lots in 2026-M01.
```

This can be converted to weekly rows using an explicit calendar mode.

---

### 5.3 WeeklyCapacityInputRow

`WeeklyCapacityInputRow` was added to represent capacity already provided at weekly granularity.

This is important for case models such as:

```text
Rice Case
COVID Vaccine Case
weekly capacity scenarios
```

---

## 6. Implemented Functions

### 6.1 monthly_capacity_to_weekly_rows

Implemented:

```python
monthly_capacity_to_weekly_rows(...)
```

Purpose:

```text
MonthlyCapacityInputRow
    ↓
WeeklyCapacityRow
```

Supported calendar modes:

```text
445
four_week_month
```

Supported distribution rule:

```text
even
```

---

### 6.2 weekly_capacity_to_weekly_rows

Implemented:

```python
weekly_capacity_to_weekly_rows(...)
```

Purpose:

```text
WeeklyCapacityInputRow
    ↓
WeeklyCapacityRow
```

This preserves:

```text
week key
capacity_qty
capacity_type
capacity owner
```

---

### 6.3 normalize_capacity_input_to_weekly_rows

Implemented dispatcher:

```python
normalize_capacity_input_to_weekly_rows(...)
```

Supported input modes:

```text
monthly_capacity
weekly_capacity
case_weekly_capacity
```

Invalid input mode raises `ValueError`.

---

### 6.4 normalize_capacity_owner_name

Implemented owner normalization.

MVP behavior:

```text
DADxxx → MOMxxx
otherwise unchanged
```

This preserves the behavior of the existing capacity provider plugin.

---

### 6.5 weekly_capacity_rows_to_weekly_capability

Implemented conversion from canonical weekly capacity rows to an `env.weekly_capability`-like dictionary.

Conceptual output:

```python
weekly_capability[product_id][MOM_node] = [cap_lot_per_week]
```

Important behavior:

```text
duplicate rows add capacity rather than overwrite
capacity_type_filter is supported
DAD→MOM owner normalization is supported
```

---

## 7. Calendar Modes

### 7.1 4-4-5 mode

The adapter supports the 4-4-5 planning calendar.

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

This aligns capacity normalization with the newer Plan Input Granularity Adapter.

---

### 7.2 Legacy four-week-month mode

The adapter also supports legacy behavior.

```text
M01 = W01-W04
M02 = W05-W08
M03 = W09-W12
...
M12 = W45-W48
```

This exists for backward compatibility with `capacity_provider_monthly_csv`.

Important note:

```text
four_week_month mode does not claim to cover all 52 weeks.
```

---

## 8. Tests

The following tests passed.

```bat
python -m pytest tests/test_capacity_input_granularity_adapter.py
```

Result:

```text
11 passed
```

Compatibility tests also passed.

```bat
python -m pytest tests/test_plan_input_granularity_adapter.py
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results:

```text
tests/test_plan_input_granularity_adapter.py: 11 passed
tests/test_japanese_rice_case_smoke.py: 1 passed
tests/test_covid_vaccine_with_capacity_push.py: 1 passed
```

---

## 9. Completion Criteria

This milestone satisfies the intended completion criteria.

```text
[OK] capacity_input_granularity.py exists
[OK] MonthlyCapacityInputRow exists
[OK] WeeklyCapacityInputRow exists
[OK] WeeklyCapacityRow exists
[OK] monthly capacity converts to weekly rows
[OK] weekly capacity passes through
[OK] 4-4-5 calendar mode is supported
[OK] legacy four_week_month mode is supported
[OK] weekly rows map to env.weekly_capability-like structure
[OK] DAD→MOM owner normalization is supported
[OK] duplicate rows add capacity rather than overwrite
[OK] capacity_type_filter is supported
[OK] focused tests pass
[OK] existing capacity provider plugin remains untouched
[OK] no GUI changes
[OK] no planning engine changes
[OK] no loader refactor changes
```

---

## 10. Latest Commit

Implementation was completed with:

```text
c8938ac Add capacity input granularity adapter MVP
```

Work was performed on:

```text
feature/with-capacity-psi-engine-v0r2
```

---

## 11. Important Boundary

This milestone does **not** modify the existing plugin:

```text
pysi/plugins/capacity_provider_monthly_csv/plugin.py
```

It only adds a new isolated adapter layer.

Current behavior remains:

```text
capacity_provider_monthly_csv
    sku_P_month_data.csv
        ↓
    1 month = 4 weeks
        ↓
    env.weekly_capability
```

New adapter behavior exists separately:

```text
monthly_capacity / weekly_capacity / case_weekly_capacity
    ↓
WeeklyCapacityRow
    ↓
weekly_capability-like dict
```

---

## 12. Meaning of This Milestone

This milestone gives WOM a clean capacity input normalization layer.

Before:

```text
capacity_provider_monthly_csv plugin
    directly builds env.weekly_capability
```

Now:

```text
Raw Capacity Input
    ↓
WeeklyCapacityRow
    ↓
env.weekly_capability-like dictionary
```

This matches the same architectural direction as the Plan Input Granularity Adapter.

---

## 13. Relationship to Plan Input Granularity Adapter

The capacity adapter mirrors the plan input adapter.

### Plan input

```text
monthly / weekly / case_weekly input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
PlanNode PSI seed
```

### Capacity input

```text
monthly_capacity / weekly_capacity / case_weekly_capacity
    ↓
WeeklyCapacityRow
    ↓
env.weekly_capability-like dict
```

This makes WOM's input layer more consistent.

---

## 14. Future Milestones

### v0r2: Refactor capacity_provider_monthly_csv plugin

Future target:

```text
capacity_provider_monthly_csv plugin
    ↓
capacity_input_granularity adapter
    ↓
env.weekly_capability
```

The plugin should call the new adapter internally.

---

### v0r3: Weekly capacity CSV support

Future target:

```text
P_capacity_week.csv
    ↓
WeeklyCapacityInputRow
    ↓
WeeklyCapacityRow
    ↓
env.weekly_capability
```

This is important for Rice Case and Vaccine Case.

---

### v0r4: Lane / flow capacity structures

Future target:

```text
transport capacity
storage capacity
lane capacity
flow capacity
```

These may need runtime structures beyond `env.weekly_capability`.

---

### v0r5: E2E Evaluation / Management Issue connection

Future target:

```text
capacity input
    ↓
capacity usage
    ↓
capacity bottleneck
    ↓
KPI
    ↓
Management Issue
```

---

## 15. Summary

Capacity Input Granularity Adapter v0r1 completed the first safe step toward canonical capacity input handling.

The completed flow is:

```text
monthly_capacity / weekly_capacity / case_weekly_capacity
    ↓
WeeklyCapacityRow
    ↓
weekly_capability-like dict
```

The most important design achievement is:

```text
Capacity input is now separated from production plan input.
```

In other words:

```text
P_month plan ≠ P_capacity_month
```

This is essential for future MOM capacity-constrained planning, Forward PUSH with Capacity, and capacity investment / ROI analysis.