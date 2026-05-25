# Codex Request: Refactor capacity_provider_monthly_csv Plugin to Use Capacity Input Granularity Adapter v0r2

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/capacity_provider_monthly_csv_adapter_v0r2.md
```

Please read this design memo first.

The current plugin:

```text
pysi/plugins/capacity_provider_monthly_csv/plugin.py
```

currently reads:

```text
sku_P_month_data.csv
```

and creates:

```text
env.weekly_capability[product][MOMxxx] = [cap_lot per week]
env.weekly_capability_df
```

The new adapter already exists:

```text
pysi/adapters/capacity_input_granularity.py
```

with:

```text
MonthlyCapacityInputRow
WeeklyCapacityRow
monthly_capacity_to_weekly_rows
weekly_capacity_rows_to_weekly_capability
normalize_capacity_owner_name
```

This request is to refactor the existing plugin so that it delegates capacity normalization to the new adapter.

---

## 2. Main Objective

Refactor:

```text
pysi/plugins/capacity_provider_monthly_csv/plugin.py
```

from:

```text
CSV read
    ↓
direct 1 month = 4 weeks conversion
    ↓
direct weekly_capability dict creation
```

to:

```text
CSV read
    ↓
MonthlyCapacityInputRow
    ↓
capacity_input_granularity adapter
    ↓
WeeklyCapacityRow
    ↓
env.weekly_capability
```

The plugin should remain the I/O and env-wiring layer.

The adapter should perform the normalization logic.

---

## 3. Important Compatibility Requirement

Preserve current runtime behavior by default.

The existing plugin uses:

```text
1 month = 4 weeks
```

Therefore, the refactored plugin should default to:

```text
calendar_mode = "four_week_month"
```

Do **not** default to `445` in this plugin yet.

Support optional override:

```python
ctx["capacity_calendar_mode"] = "445"
```

or:

```python
ctx["calendar_mode"] = "445"
```

If neither is provided, use:

```text
four_week_month
```

---

## 4. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan.
3. Do not modify planning engines.
4. Do not modify S_month / P_month loaders.
5. Do not implement database persistence.
6. Keep env.weekly_capability output shape compatible.
7. Keep env.weekly_capability_df available.
8. Preserve missing CSV behavior.
9. Preserve DADxxx → MOMxxx normalization.
10. Keep this as a small plugin refactor.
```

---

## 5. Files to Modify

Modify:

```text
pysi/plugins/capacity_provider_monthly_csv/plugin.py
```

Reuse:

```text
pysi/adapters/capacity_input_granularity.py
```

Add tests:

```text
tests/test_capacity_provider_monthly_csv_plugin.py
```

Do not modify:

```text
GUI
run_full_plan
planning engines
```

---

## 6. Existing CSV Format to Preserve

The existing CSV format should remain supported:

```csv
product_name,node_name,year,m1,m2,m3,m4,m5,m6,m7,m8,m9,m10,m11,m12
```

Required columns:

```text
product_name
node_name
year
m1
m2
m3
m4
m5
m6
m7
m8
m9
m10
m11
m12
```

---

## 7. Mapping to MonthlyCapacityInputRow

For each CSV row and each positive monthly capacity value, create:

```python
MonthlyCapacityInputRow(
    scenario_id=scenario_id,
    product_id=product_name,
    capacity_owner_type="node",
    capacity_owner_id=node_name,
    month=f"{year}-M{month_no:02d}",
    capacity_type="P",
    capacity_qty=value,
    cap_mode="hard",
    unit="LOT",
    source_id="sku_P_month_data.csv",
    comment="monthly MOM production capacity",
)
```

### 7.1 scenario_id

Use:

```python
ctx.get("scenario_id", "BASE")
```

### 7.2 capacity_type

Use:

```text
P
```

### 7.3 capacity_owner_type

Use:

```text
node
```

---

## 8. Adapter Call Flow

The refactored plugin should conceptually do:

```python
monthly_rows = build_monthly_capacity_rows_from_csv(...)
weekly_rows = monthly_capacity_to_weekly_rows(
    monthly_rows,
    calendar_mode=calendar_mode,
    distribution_rule="even",
)
weekly_capability = weekly_capacity_rows_to_weekly_capability(
    weekly_rows,
    weeks_count=weeks_count,
    normalize_owner_name=True,
    capacity_type_filter="P",
)
env.weekly_capability = weekly_capability
env.weekly_capability_df = weekly_rows_to_debug_df(weekly_rows)
```

Use the existing adapter functions wherever possible.

---

## 9. Context Handling

The plugin should continue to locate `data_dir` as it does today.

Support calendar mode from context:

```python
calendar_mode = (
    ctx.get("capacity_calendar_mode")
    or ctx.get("calendar_mode")
    or "four_week_month"
)
```

Support weeks count from context where reasonable:

```python
weeks_count = ctx.get("weeks_count") or ctx.get("plan_weeks") or 53
```

If the current plugin already has a weeks count convention, preserve it.

---

## 10. weekly_capability_df

Preserve:

```python
env.weekly_capability_df
```

At minimum include the existing-compatible columns:

```text
product
node
week
cap_lot
```

Additional columns are acceptable:

```text
source_granularity
capacity_type
source_id
```

but do not remove the compatible columns.

---

## 11. Missing CSV Behavior

If `sku_P_month_data.csv` is missing, preserve current behavior:

```text
skip without crash
log warning or info
do not break pipeline
```

---

## 12. Invalid Numeric Values

Preserve current compatibility behavior:

```text
invalid monthly capacity values are coerced to 0
```

Use `pandas.to_numeric(..., errors="coerce").fillna(0)` or equivalent.

---

## 13. Tests

Please add:

```text
tests/test_capacity_provider_monthly_csv_plugin.py
```

Required tests:

### 13.1 Missing CSV

```text
If CSV is missing, plugin does not crash.
```

### 13.2 Default four_week_month behavior

Given CSV:

```text
product_name=PRODUCT_X
node_name=DAD_CHINA
year=2026
m1=400
```

With default context, expect:

```text
env.weekly_capability["PRODUCT_X"]["MOM_CHINA"][0] == 100
env.weekly_capability["PRODUCT_X"]["MOM_CHINA"][1] == 100
env.weekly_capability["PRODUCT_X"]["MOM_CHINA"][2] == 100
env.weekly_capability["PRODUCT_X"]["MOM_CHINA"][3] == 100
```

### 13.3 DAD to MOM normalization

Verify:

```text
DAD_CHINA → MOM_CHINA
```

### 13.4 Optional 445 behavior

Given:

```text
m3=500
ctx["capacity_calendar_mode"] = "445"
```

Expect capacity distributed over:

```text
W09-W13
```

that is, 5 weeks with 100 each.

### 13.5 weekly_capability_df exists

Verify:

```text
env.weekly_capability_df exists
```

and contains at least:

```text
product
node
week
cap_lot
```

### 13.6 Existing adapter tests still pass

Run:

```bat
python -m pytest tests/test_capacity_input_granularity_adapter.py
```

---

## 14. Test Commands

Please run:

```bat
python -m pytest tests/test_capacity_provider_monthly_csv_plugin.py
python -m pytest tests/test_capacity_input_granularity_adapter.py
python -m pytest tests/test_plan_input_granularity_adapter.py
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

---

## 15. Completion Criteria

This request is complete when:

```text
[OK] capacity_provider_monthly_csv delegates conversion to capacity_input_granularity adapter
[OK] default plugin behavior remains four_week_month compatible
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

## 16. Out of Scope

Do not implement:

```text
weekly capacity CSV plugin
lane / flow capacity runtime structure
E2E Evaluation integration
Management Issue Generation
Run Full Plan refactor
capacity investment ROI logic
```

---

## 17. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. How default four_week_month compatibility is preserved
4. How optional 445 mode is enabled
5. Test commands executed
6. Test results
7. Any limitations or follow-up tasks
```

This request is only for:

```text
Capacity Provider Monthly CSV Adapter v0r2
```