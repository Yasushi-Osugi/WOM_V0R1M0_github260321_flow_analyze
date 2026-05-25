# Capacity Provider Monthly CSV Adapter v0r2 Design Memo
## Refactor capacity_provider_monthly_csv to Use Capacity Input Granularity Adapter

**Version:** v0r2 draft  
**Date:** 2026-05-19  
**Status:** Design memo  
**Target path:** `docs/design/capacity_provider_monthly_csv_adapter_v0r2.md`

**Related design documents:**

- `docs/design/current_wom_backward_planning_and_capacity_flow_mapping.md`
- `docs/design/wom_capacity_input_granularity_adapter.md`
- `docs/design/capacity_input_granularity_adapter_v0r1_completion.md`
- `docs/design/wom_plan_input_granularity_adapter.md`
- `docs/design/legacy_pysi_v0r8_input_loader_mapping.md`

---

## 1. Purpose

This memo defines **Capacity Provider Monthly CSV Adapter v0r2**.

The purpose is to refactor the current plugin:

```text
pysi/plugins/capacity_provider_monthly_csv/plugin.py
```

so that it uses the new capacity input normalization layer:

```text
pysi/adapters/capacity_input_granularity.py
```

Current behavior:

```text
sku_P_month_data.csv
    ↓
capacity_provider_monthly_csv plugin
    ↓
1 month = 4 weeks conversion
    ↓
env.weekly_capability[product][MOMxxx]
```

Target v0r2 behavior:

```text
sku_P_month_data.csv
    ↓
MonthlyCapacityInputRow
    ↓
capacity_input_granularity adapter
    ↓
WeeklyCapacityRow
    ↓
env.weekly_capability[product][MOMxxx]
```

This refactor should preserve current behavior by default while enabling cleaner future support for:

```text
4-4-5 capacity calendar
weekly capacity input
case-specific capacity input
```

---

## 2. Background

The current `capacity_provider_monthly_csv` plugin already provides an important runtime capability path:

```text
monthly capacity CSV
    ↓
env.weekly_capability
    ↓
level_mom_demand_with_capacity(...)
```

This path is used by MOM capacity-constrained planning / leveling.

However, the current plugin directly implements:

```text
CSV read
month-to-week conversion
DAD→MOM name normalization
weekly_capability dict creation
```

inside one plugin.

The new `capacity_input_granularity` adapter has already implemented:

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

Therefore, v0r2 should make the existing plugin delegate conversion and dictionary creation to the adapter.

---

## 3. Key Design Principle

The key principle is:

```text
Plugin = I/O boundary and env wiring
Adapter = capacity normalization logic
```

The plugin should be responsible for:

```text
1. locating CSV file
2. reading raw CSV rows
3. creating MonthlyCapacityInputRow records
4. calling capacity_input_granularity adapter
5. attaching result to env.weekly_capability
6. writing debug dataframe if useful
```

The adapter should be responsible for:

```text
1. monthly-to-weekly conversion
2. weekly capacity row normalization
3. DAD→MOM owner normalization
4. env.weekly_capability-like dict construction
```

---

## 4. Existing Plugin Behavior to Preserve

The current plugin behavior should remain compatible by default.

### 4.1 Default file name

Current default:

```text
sku_P_month_data.csv
```

This should remain the default in v0r2.

### 4.2 Input columns

Current required columns:

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

This should remain supported.

### 4.3 Owner normalization

Current plugin normalizes:

```text
DADxxx → MOMxxx
```

This behavior should remain supported through:

```python
normalize_capacity_owner_name(...)
```

### 4.4 Output attributes

The plugin should continue to set:

```python
env.weekly_capability
env.weekly_capability_df
```

### 4.5 Missing CSV behavior

If the CSV is missing, current plugin skips with warning.

v0r2 should preserve this behavior.

---

## 5. Important Compatibility Policy

### 5.1 Default calendar mode

To avoid changing existing behavior unexpectedly, v0r2 should default to:

```text
calendar_mode = "four_week_month"
```

when called from `capacity_provider_monthly_csv`.

Reason:

The existing plugin uses:

```text
1 month = 4 weeks
```

Changing the default to `445` would change runtime capacity distribution.

### 5.2 Optional 4-4-5 mode

v0r2 should allow explicit override through plugin context.

Example:

```text
ctx["capacity_calendar_mode"] = "445"
```

or:

```text
ctx["calendar_mode"] = "445"
```

This enables future migration to 4-4-5 without breaking current behavior.

### 5.3 Distribution rule

Default:

```text
distribution_rule = "even"
```

This matches current behavior.

---

## 6. Input Mapping from Current CSV to MonthlyCapacityInputRow

Current CSV row:

```csv
product_name,node_name,year,m1,m2,...,m12
```

should become multiple `MonthlyCapacityInputRow` records.

For each non-zero monthly value:

```python
MonthlyCapacityInputRow(
    scenario_id=scenario_id,
    product_id=product_name,
    capacity_owner_type="node",
    capacity_owner_id=node_name,
    month=f"{year}-M{month:02d}",
    capacity_type="P",
    capacity_qty=value,
    cap_mode="hard",
    unit="LOT",
    source_id="sku_P_month_data.csv",
    comment="monthly MOM production capacity",
)
```

### 6.1 scenario_id

If `scenario_id` is not available in CSV, use:

```text
ctx["scenario_id"]
```

or fallback:

```text
"BASE"
```

### 6.2 capacity_type

For this plugin:

```text
capacity_type = "P"
```

because it provides MOM production capacity.

### 6.3 capacity_owner_type

For this plugin:

```text
capacity_owner_type = "node"
```

---

## 7. Adapter Call Flow

The refactored plugin should conceptually do:

```python
monthly_rows = build_monthly_capacity_rows_from_csv(df, ...)
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

This preserves the final runtime output while separating logic.

---

## 8. weekly_capability_df

The existing plugin creates a debug dataframe:

```text
product
node
week
cap_lot
```

v0r2 should preserve this attribute.

Recommended v0r2 debug dataframe columns:

```text
product
node
week
cap_lot
source_granularity
capacity_type
source_id
```

To preserve compatibility, at minimum keep:

```text
product
node
week
cap_lot
```

---

## 9. Error and Validation Policy

### 9.1 Missing required columns

If required columns are missing, raise `ValueError`.

This preserves existing behavior.

### 9.2 Invalid numeric values

Invalid monthly capacity values should be treated as zero or raise.

Recommended compatibility behavior:

```text
coerce invalid to 0
```

because current plugin uses `pd.to_numeric(...).fillna(0)`.

### 9.3 Empty result

If no positive capacity rows exist:

```python
env.weekly_capability = {}
env.weekly_capability_df = empty dataframe
```

and log an info message.

---

## 10. Tests

### 10.1 Existing adapter tests remain

The existing capacity adapter tests should continue to pass:

```bat
python -m pytest tests/test_capacity_input_granularity_adapter.py
```

### 10.2 New plugin tests

Add focused tests for the plugin if possible:

```text
tests/test_capacity_provider_monthly_csv_plugin.py
```

Required test cases:

```text
1. Missing CSV path skips without crash.
2. CSV with product_name/node_name/year/m1..m12 sets env.weekly_capability.
3. Default plugin calendar mode preserves four_week_month behavior.
4. Explicit ctx calendar mode "445" uses 4-4-5 behavior.
5. DADxxx owner is normalized to MOMxxx.
6. env.weekly_capability_df is created.
7. Existing output structure env.weekly_capability[product][mom] is preserved.
```

### 10.3 No broad pipeline tests required

Do not require full Run Full Plan test in this MVP.

---

## 11. Suggested Files

Update:

```text
pysi/plugins/capacity_provider_monthly_csv/plugin.py
```

Reuse:

```text
pysi/adapters/capacity_input_granularity.py
```

Add if needed:

```text
tests/test_capacity_provider_monthly_csv_plugin.py
```

Do not modify:

```text
GUI
run_full_plan
planning engines
existing monthly S/P loaders
```

---

## 12. Completion Criteria

v0r2 is complete when:

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
[OK] no GUI / run_full_plan / planning engine changes
```

---

## 13. Out of Scope

This v0r2 should not implement:

```text
weekly capacity CSV plugin
lane / flow runtime capacity structure
E2E Evaluation integration
Management Issue Generation
Run Full Plan refactor
capacity investment ROI logic
```

These are future milestones.

---

## 14. Future Milestones

### v0r3: Weekly capacity CSV support

Add support for:

```text
P_capacity_week.csv
```

or generic weekly capacity input.

### v0r4: Lane / flow capacity support

Support:

```text
transport capacity
storage capacity
lane capacity
flow capacity
```

beyond MOM P capacity.

### v0r5: E2E Evaluation connection

Connect capacity input to:

```text
capacity usage
bottleneck detection
KPI
Management Issue
```

---

## 15. Summary

This v0r2 refactor should preserve existing runtime behavior while moving capacity normalization into a reusable adapter.

Before:

```text
capacity_provider_monthly_csv plugin
    does CSV read + month conversion + weekly_capability build
```

After:

```text
capacity_provider_monthly_csv plugin
    reads CSV
    creates MonthlyCapacityInputRow
    calls capacity_input_granularity adapter
    attaches env.weekly_capability
```

This aligns capacity input handling with the broader WOM input normalization architecture while avoiding breaking changes.