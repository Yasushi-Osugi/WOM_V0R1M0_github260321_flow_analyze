# Capacity Provider Monthly CSV Adapter v0r2 Completion Memo

**Version:** v0r2 completion  
**Date:** 2026-05-19  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Capacity Provider Monthly CSV Adapter v0r2**.

The purpose of this milestone was to refactor the existing plugin:

```text
pysi/plugins/capacity_provider_monthly_csv/plugin.py
```

so that it delegates monthly-to-weekly capacity normalization to the new adapter:

```text
pysi/adapters/capacity_input_granularity.py
```

The intended flow was:

```text
sku_P_month_data.csv
    ↓
capacity_provider_monthly_csv plugin
    ↓
MonthlyCapacityInputRow
    ↓
capacity_input_granularity adapter
    ↓
WeeklyCapacityRow
    ↓
env.weekly_capability
```

This refactor preserves existing runtime behavior while separating I/O wiring from capacity normalization logic.

---

## 2. Background

Before this milestone, `capacity_provider_monthly_csv` directly handled:

```text
CSV read
    ↓
1 month = 4 weeks conversion
    ↓
DAD→MOM owner normalization
    ↓
weekly_capability dict creation
    ↓
env.weekly_capability
```

This worked, but it mixed several responsibilities inside one plugin.

The newly added `capacity_input_granularity` adapter already provided:

```text
MonthlyCapacityInputRow
WeeklyCapacityInputRow
WeeklyCapacityRow
monthly_capacity_to_weekly_rows
weekly_capacity_to_weekly_rows
normalize_capacity_input_to_weekly_rows
weekly_capacity_rows_to_weekly_capability
normalize_capacity_owner_name
```

Therefore, v0r2 refactored the plugin to become primarily:

```text
I/O boundary + env wiring
```

while the adapter owns:

```text
capacity normalization logic
```

---

## 3. Implemented Files

This milestone modified or added:

```text
pysi/plugins/capacity_provider_monthly_csv/plugin.py
tests/test_capacity_provider_monthly_csv_plugin.py
```

---

## 4. Implemented Changes

### 4.1 Plugin delegates normalization to adapter

The plugin now converts CSV rows into `MonthlyCapacityInputRow` records and delegates monthly-to-weekly normalization to:

```python
monthly_capacity_to_weekly_rows(...)
```

Then it converts normalized weekly rows into runtime capability structure using:

```python
weekly_capacity_rows_to_weekly_capability(...)
```

---

### 4.2 Existing output shape is preserved

The plugin still publishes:

```python
env.weekly_capability
env.weekly_capability_df
```

The runtime structure remains compatible:

```python
env.weekly_capability[product][MOM_node] = [cap_lot_per_week]
```

This keeps downstream consumers such as MOM capacity planning / leveling compatible.

---

### 4.3 Default behavior remains legacy-compatible

The plugin preserves the existing default behavior:

```text
1 month = 4 weeks
```

by defaulting to:

```text
calendar_mode = "four_week_month"
```

This avoids unexpected changes in existing runtime capacity distribution.

---

### 4.4 Optional 4-4-5 mode is supported

The plugin now supports explicit override:

```python
ctx["capacity_calendar_mode"] = "445"
```

or:

```python
ctx["calendar_mode"] = "445"
```

When this override is provided, the plugin uses the 4-4-5 calendar behavior from the capacity input adapter.

Example tested behavior:

```text
M03 = 5 weeks under 4-4-5
m3 = 500
    ↓
W09-W13 each receive 100
```

---

### 4.5 Missing CSV behavior is preserved

If the configured CSV is missing, the plugin continues to skip safely without crashing the pipeline.

This preserves existing non-breaking behavior.

---

### 4.6 Invalid numeric values are coerced to zero

The plugin preserves compatibility behavior using numeric coercion.

Invalid monthly capacity values are treated as zero.

Conceptually:

```python
pd.to_numeric(..., errors="coerce").fillna(0)
```

---

### 4.7 DAD→MOM owner normalization is preserved

The plugin keeps existing behavior:

```text
DADxxx → MOMxxx
```

through the adapter function:

```python
normalize_capacity_owner_name(...)
```

This preserves compatibility with existing data where capacity rows may use DAD-style names but runtime planning expects MOM-style names.

---

### 4.8 weekly_capability_df remains available

The plugin continues to set:

```python
env.weekly_capability_df
```

At minimum, the debug dataframe preserves compatible columns:

```text
product
node
week
cap_lot
```

Additional debug columns may exist.

---

## 5. Tests

New focused test file:

```text
tests/test_capacity_provider_monthly_csv_plugin.py
```

Tested cases include:

```text
1. Missing CSV path skips without crash.
2. CSV with product_name / node_name / year / m1..m12 sets env.weekly_capability.
3. Default plugin calendar mode preserves four_week_month behavior.
4. Explicit ctx calendar mode "445" uses 4-4-5 behavior.
5. DADxxx owner is normalized to MOMxxx.
6. env.weekly_capability_df is created.
7. env.weekly_capability output shape is preserved.
```

---

## 6. Test Summary

The following tests passed.

```bat
python -m pytest tests/test_capacity_provider_monthly_csv_plugin.py
```

Result:

```text
4 passed
```

Compatibility tests also passed.

```bat
python -m pytest tests/test_capacity_input_granularity_adapter.py
python -m pytest tests/test_plan_input_granularity_adapter.py
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results:

```text
tests/test_capacity_input_granularity_adapter.py: 11 passed
tests/test_plan_input_granularity_adapter.py: 11 passed
tests/test_japanese_rice_case_smoke.py: 1 passed
tests/test_covid_vaccine_with_capacity_push.py: 1 passed
```

---

## 7. Completion Criteria

This milestone satisfies the intended completion criteria.

```text
[OK] capacity_provider_monthly_csv delegates conversion to capacity_input_granularity adapter
[OK] existing default behavior remains four_week_month compatible
[OK] optional calendar_mode="445" is supported
[OK] env.weekly_capability output shape is preserved
[OK] env.weekly_capability_df is preserved
[OK] DAD→MOM normalization is preserved
[OK] missing CSV behavior is preserved
[OK] focused plugin tests pass
[OK] capacity_input_granularity adapter tests still pass
[OK] no GUI changes
[OK] no run_full_plan changes
[OK] no planning engine changes
```

---

## 8. Latest Commit

Implementation was completed with:

```text
500aa49 Refactor monthly capacity provider to use granularity adapter
```

Work was performed on:

```text
feature/with-capacity-psi-engine-v0r2
```

---

## 9. Important Boundary

This milestone does **not** implement:

```text
weekly capacity CSV plugin
lane / flow runtime capacity structure
E2E Evaluation integration
Management Issue Generation
Run Full Plan refactor
capacity investment ROI logic
```

It only refactors the monthly capacity provider to delegate normalization to the new capacity input adapter.

---

## 10. Known Follow-up

Current known follow-up:

```text
env.weekly_capability_df["node"]
```

may reflect source owner IDs such as `DAD_*`, while:

```text
env.weekly_capability
```

is normalized to `MOM_*`.

Runtime capability behavior is correct if `env.weekly_capability` is normalized.

However, for future debug / GUI clarity, `weekly_capability_df["node"]` may also be normalized in a small follow-up.

---

## 11. Meaning of This Milestone

Before this milestone:

```text
capacity_provider_monthly_csv plugin
    handled CSV read
    handled month-to-week conversion
    handled DAD→MOM normalization
    built env.weekly_capability directly
```

After this milestone:

```text
capacity_provider_monthly_csv plugin
    reads CSV
    creates MonthlyCapacityInputRow
    calls capacity_input_granularity adapter
    attaches env.weekly_capability
```

This makes the capacity input path more modular, testable, and aligned with the broader WOM input normalization architecture.

---

## 12. Relationship to Plan Input Granularity Adapter

The capacity adapter now follows the same architectural direction as the plan input adapter.

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
env.weekly_capability
```

This separation clarifies the difference between:

```text
what is required or planned
```

and:

```text
what is possible
```

---

## 13. Future Milestones

### v0r3: Weekly capacity CSV support

Add support for:

```text
P_capacity_week.csv
```

or a generic weekly capacity CSV.

Target flow:

```text
weekly capacity CSV
    ↓
WeeklyCapacityInputRow
    ↓
WeeklyCapacityRow
    ↓
env.weekly_capability
```

---

### v0r4: Lane / flow capacity support

Extend runtime capacity structures to support:

```text
transport capacity
storage capacity
lane capacity
flow capacity
```

beyond MOM P capacity.

---

### v0r5: Capacity Evaluation / Management Issue connection

Connect capacity input to:

```text
capacity usage
bottleneck detection
KPI
Management Issue
```

---

## 14. Summary

Capacity Provider Monthly CSV Adapter v0r2 completed a safe refactor of the existing monthly capacity provider plugin.

The most important achievement is:

```text
The existing monthly capacity plugin now delegates normalization to the shared capacity input adapter while preserving runtime compatibility.
```

The key compatibility rule is:

```text
default calendar_mode = four_week_month
```

The key future migration path is:

```text
explicit calendar_mode = 445
```

This lets WOM preserve existing behavior today while moving toward a cleaner, unified capacity input architecture.