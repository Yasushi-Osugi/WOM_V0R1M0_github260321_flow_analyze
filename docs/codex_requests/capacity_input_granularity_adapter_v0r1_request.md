# Codex Request: Implement WOM Capacity Input Granularity Adapter v0r1

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/wom_capacity_input_granularity_adapter.md
```

Please read this design memo first.

Current WOM already has a capacity provider plugin:

```text
pysi/plugins/capacity_provider_monthly_csv/plugin.py
```

This plugin reads:

```text
sku_P_month_data.csv
```

and creates:

```text
env.weekly_capability[product][MOMxxx] = [cap_lot per week]
env.weekly_capability_df
```

However, the current plugin uses a simplified conversion:

```text
1 month = 4 weeks
```

The newer Plan Input Granularity Adapter uses a 4-4-5 planning calendar.

This request is to implement an isolated, additive **Capacity Input Granularity Adapter v0r1** that normalizes monthly or weekly capacity input into a canonical weekly capacity representation.

Do not refactor the existing capacity provider plugin in this request.

---

## 2. Main Objective

Implement a new additive capacity input adapter layer.

Target flow:

```text
monthly capacity input
or
weekly capacity input
    ↓
Canonical WeeklyCapacityRow
    ↓
env.weekly_capability-like dictionary
```

The primary use case is MOM production capacity:

```text
P_capacity_month / P_capacity_week
    ↓
WeeklyCapacityRow
    ↓
env.weekly_capability[product][MOM_node][week]
    ↓
level_mom_demand_with_capacity(...)
```

---

## 3. Important Conceptual Distinction

Please preserve this distinction:

```text
P_month plan:
    production requirement / planned production quantity

P_capacity_month:
    production capacity limit for MOM / production node

S_month supply:
    supply / shipment / sales quantity depending on context
```

The current file name `sku_P_month_data.csv` is overloaded.

This v0r1 implementation should introduce clearer dataclasses and adapter functions without changing the existing plugin yet.

---

## 4. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan.
3. Do not modify existing planning engines.
4. Do not modify existing capacity_provider_monthly_csv plugin in v0r1.
5. Do not modify existing S_month / P_month loaders.
6. Do not implement database persistence.
7. Add only isolated adapter module(s) and focused tests.
8. Preserve current behavior elsewhere.
```

This request is only for:

```text
Capacity Input Granularity Adapter v0r1
```

---

## 5. Suggested Files

Please add:

```text
pysi/adapters/capacity_input_granularity.py
tests/test_capacity_input_granularity_adapter.py
```

Please update only if useful:

```text
pysi/adapters/__init__.py
```

Do not modify:

```text
pysi/plugins/capacity_provider_monthly_csv/plugin.py
```

in this v0r1 request.

---

## 6. Dataclasses to Implement

### 6.1 WeeklyCapacityRow

Please implement:

```python
from dataclasses import dataclass


@dataclass
class WeeklyCapacityRow:
    scenario_id: str
    product_id: str
    capacity_owner_type: str
    capacity_owner_id: str
    week: str
    capacity_type: str
    capacity_qty: float
    cap_mode: str = "hard"
    unit: str = "LOT"
    source_granularity: str = "weekly"
    source_id: str = ""
    comment: str = ""
```

`capacity_owner_type` values for MVP:

```text
node
lane
flow
```

`capacity_type` values for MVP:

```text
P
S
I
transport
storage
process
```

---

### 6.2 MonthlyCapacityInputRow

Please implement:

```python
@dataclass
class MonthlyCapacityInputRow:
    scenario_id: str
    product_id: str
    capacity_owner_type: str
    capacity_owner_id: str
    month: str
    capacity_type: str
    capacity_qty: float
    cap_mode: str = "hard"
    unit: str = "LOT"
    source_id: str = ""
    comment: str = ""
```

Example:

```python
MonthlyCapacityInputRow(
    scenario_id="BASE",
    product_id="PRODUCT_X",
    capacity_owner_type="node",
    capacity_owner_id="MOM_CHINA",
    month="2026-M01",
    capacity_type="P",
    capacity_qty=400.0,
)
```

---

### 6.3 WeeklyCapacityInputRow

Please implement:

```python
@dataclass
class WeeklyCapacityInputRow:
    scenario_id: str
    product_id: str
    capacity_owner_type: str
    capacity_owner_id: str
    week: str
    capacity_type: str
    capacity_qty: float
    cap_mode: str = "hard"
    unit: str = "LOT"
    source_id: str = ""
    comment: str = ""
```

Example:

```python
WeeklyCapacityInputRow(
    scenario_id="RICE_AS_IS",
    product_id="PACKAGED_RICE_STANDARD",
    capacity_owner_type="node",
    capacity_owner_id="MILL_EAST",
    week="2027-W40",
    capacity_type="P",
    capacity_qty=5.0,
)
```

---

## 7. Monthly Capacity Conversion

Please implement:

```python
def monthly_capacity_to_weekly_rows(
    monthly_rows: list[MonthlyCapacityInputRow],
    *,
    calendar_mode: str = "445",
    distribution_rule: str = "even",
) -> list[WeeklyCapacityRow]:
    ...
```

Supported `calendar_mode` values:

```text
445
four_week_month
```

`calendar_month` can be left for future extension.

Supported `distribution_rule` values for MVP:

```text
even
```

### 7.1 4-4-5 mode

Use the same 4-4-5 mapping as `pysi/adapters/calendar_445.py`.

Expected mapping:

```text
M01 = W01-W04
M02 = W05-W08
M03 = W09-W13
M04 = W14-W17
M05 = W18-W21
M06 = W22-W26
M07 = W27-W30
M08 = W31-W34
M09 = W35-W39
M10 = W40-W43
M11 = W44-W47
M12 = W48-W52
```

Example:

```text
2026-M03 capacity_qty = 500
M03 has 5 weeks
weekly capacity = 100
```

### 7.2 legacy four_week_month mode

Implement the legacy behavior used by `capacity_provider_monthly_csv`.

Expected mapping:

```text
M01 = W01-W04
M02 = W05-W08
M03 = W09-W12
...
M12 = W45-W48
```

Important:

```text
four_week_month mode is backward compatibility only.
It does not cover all 52 weeks.
```

---

## 8. Weekly Capacity Pass-through

Please implement:

```python
def weekly_capacity_to_weekly_rows(
    weekly_rows: list[WeeklyCapacityInputRow],
    *,
    source_granularity: str = "weekly",
) -> list[WeeklyCapacityRow]:
    ...
```

Behavior:

```text
week key is preserved
capacity_qty is preserved
capacity_type is preserved
capacity_owner_id is preserved
```

This is important for Rice Case / Vaccine Case weekly inputs.

---

## 9. Dispatcher

Please implement:

```python
def normalize_capacity_input_to_weekly_rows(
    *,
    input_mode: str,
    monthly_rows: list[MonthlyCapacityInputRow] | None = None,
    weekly_rows: list[WeeklyCapacityInputRow] | None = None,
    calendar_mode: str = "445",
    distribution_rule: str = "even",
) -> list[WeeklyCapacityRow]:
    ...
```

Supported `input_mode` values:

```text
monthly_capacity
weekly_capacity
case_weekly_capacity
```

Expected behavior:

```text
monthly_capacity:
    use monthly_capacity_to_weekly_rows

weekly_capacity:
    use weekly_capacity_to_weekly_rows

case_weekly_capacity:
    use weekly_capacity_to_weekly_rows with source_granularity="case_weekly"
```

Invalid input mode should raise `ValueError`.

---

## 10. Mapping to env.weekly_capability

Please implement:

```python
def weekly_capacity_rows_to_weekly_capability(
    rows: list[WeeklyCapacityRow],
    *,
    weeks_count: int,
    normalize_owner_name: bool = True,
    capacity_type_filter: str = "P",
) -> dict[str, dict[str, list[int]]]:
    ...
```

Expected output:

```python
weekly_capability[product_id][owner_id] = [cap_lot_per_week]
```

Example:

```python
weekly_capability["PRODUCT_X"]["MOM_CHINA"][0] == 100
```

### 10.1 Owner normalization

Please implement:

```python
def normalize_capacity_owner_name(owner_id: str) -> str:
    ...
```

MVP behavior:

```text
if owner_id starts with "DAD":
    return "MOM" + owner_id[3:]

otherwise:
    return owner_id
```

This preserves the current capacity provider behavior.

### 10.2 Duplicate weekly rows

If multiple rows target the same product / owner / week:

```text
add capacity values
do not overwrite
```

---

## 11. Tests

Please add:

```text
tests/test_capacity_input_granularity_adapter.py
```

Required tests:

### 11.1 4-4-5 calendar tests

```text
1. M01 expands to W01-W04.
2. M03 expands to W09-W13.
3. 12 months cover 52 weeks in 4-4-5 mode.
4. M03 capacity 500 becomes 100 per week across 5 weeks.
```

### 11.2 legacy four-week-month tests

```text
1. M01 expands to W01-W04.
2. M12 starts at W45.
3. four_week_month mode does not claim to cover all 52 weeks.
```

### 11.3 weekly pass-through tests

```text
1. weekly input preserves week key.
2. weekly input preserves capacity_qty.
3. case_weekly_capacity input preserves Rice W40 / W41 boundary.
```

### 11.4 weekly_capability mapping tests

```text
1. WeeklyCapacityRow maps to weekly_capability-like dict.
2. product key is preserved.
3. owner normalization DADxxx → MOMxxx works.
4. capacity values are stored in correct week index.
5. duplicate rows add capacity rather than overwrite.
6. capacity_type_filter="P" filters out non-P rows.
```

### 11.5 invalid mode test

```text
invalid input_mode raises ValueError
```

---

## 12. Test Commands

Please run:

```bat
python -m pytest tests/test_capacity_input_granularity_adapter.py
```

Also run relevant existing tests:

```bat
python -m pytest tests/test_plan_input_granularity_adapter.py
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

If broader tests fail due to unrelated optional dependencies, report separately.

---

## 13. Completion Criteria

This request is complete when:

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
[OK] tests pass
[OK] existing capacity provider plugin remains untouched
[OK] no GUI / planning engine / loader refactor changes
```

---

## 14. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. Test commands executed
4. Test results
5. Any limitations or follow-up tasks
```

Please do not proceed into:

```text
capacity_provider_monthly_csv plugin refactor
GUI integration
planning engine changes
database persistence
lane / flow capacity runtime integration
E2E Evaluation
```

This request is only for:

```text
WOM Capacity Input Granularity Adapter v0r1
```