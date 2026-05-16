# Codex Request: Implement WOM Plan Input Granularity Adapter v0r1

## 1. Background

We are working on branch:

```text
feature/plan-input-granularity-adapter-v0r1
```

The design memo has already been added:

```text
docs/design/wom_plan_input_granularity_adapter.md
```

Please read this design memo first.

This request is to implement the first MVP of the **WOM Plan Input Granularity Adapter**.

The goal is to normalize different input granularities into a common weekly planning table.

Current WOM loading has historically handled monthly planning inputs such as:

```text
S_month
P_month
```

and then decomposed them into weekly data, generated Lot IDs, and seeded PSI lists.

However, new WOM Case Modeling examples such as the Japanese Rice Case and COVID Vaccine Case may already have meaningful weekly supply / demand data.

Therefore, WOM should support both:

```text
monthly input mode:
    S_month / P_month
    ↓
    4-4-5 calendar adapter
    ↓
    canonical weekly plan table

weekly input mode:
    S_week / P_week or case_weekly data
    ↓
    canonical weekly plan table
```

This request should **not** modify the existing WOM loader yet.

---

## 2. Main Objective

Implement a small, isolated adapter layer that converts monthly or weekly plan input into a canonical weekly plan table.

The MVP should support:

```text
1. 4-4-5 calendar mapping
2. monthly input → weekly plan table
3. weekly input → weekly plan table pass-through
4. case_weekly input → weekly plan table pass-through
5. focused tests
```

This request is only for input normalization.

Do not implement Lot_ID generation or PSI seeding yet.

---

## 3. Most Important Constraints

Please follow these constraints:

```text
1. Do not modify existing monthly WOM loaders.
2. Do not modify GUI.
3. Do not modify existing planning engines.
4. Do not implement Lot_ID generation in this request.
5. Do not implement PSI seeding in this request.
6. Do not refactor S_month / P_month loading yet.
7. Add new adapter modules only.
8. Keep implementation small and testable.
```

This is a safe additive MVP.

---

## 4. Suggested Files

Please add:

```text
pysi/adapters/__init__.py
pysi/adapters/calendar_445.py
pysi/adapters/weekly_plan_table.py
pysi/adapters/plan_input_granularity.py
tests/test_plan_input_granularity_adapter.py
```

If the repository has a better convention for adapter modules, please follow it, but avoid broad refactoring.

---

## 5. Core Concepts

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

This request implements only the first two steps:

```text
Raw Plan Input
    ↓
Calendar / Granularity Normalization
    ↓
Canonical Weekly Plan Table
```

Lot_ID Generation and PSI Seeding will be later milestones.

---

## 6. Input Modes

Please support these input modes:

```text
monthly_sp:
    input = S_month / P_month style monthly data

weekly_sp:
    input = S_week / P_week style weekly data

case_weekly:
    input = case-specific weekly supply / demand dataset

case_monthly:
    input = case-specific monthly supply / demand dataset
```

For v0r1, it is enough to support:

```text
monthly_sp
weekly_sp
case_weekly
```

`case_monthly` may be defined but can be left as a future extension if needed.

---

## 7. 4-4-5 Calendar Adapter

Please implement a 4-4-5 calendar adapter.

One year has 52 weeks.

Mapping:

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

Suggested functions:

```python
def build_445_week_to_month_map(year: str | int) -> dict[str, str]:
    ...

def build_445_month_to_weeks_map(year: str | int) -> dict[str, list[str]]:
    ...
```

Example:

```python
build_445_month_to_weeks_map(2026)["2026-M01"]
# ["2026-W01", "2026-W02", "2026-W03", "2026-W04"]
```

Important note:

```text
WOM 4-4-5 month is a planning month.
It is not necessarily identical to a calendar month.
```

---

## 8. Canonical Weekly Plan Table

Please define a small dataclass for canonical weekly plan rows.

Suggested dataclass:

```python
from dataclasses import dataclass


@dataclass
class WeeklyPlanRow:
    scenario_id: str
    product_id: str
    node_id: str
    week: str
    plan_type: str
    quantity: float
    source_granularity: str
    source_id: str = ""
    comment: str = ""
```

Allowed `plan_type` values for MVP:

```text
S
P
demand
supply
```

Allowed `source_granularity` values:

```text
monthly
weekly
case_weekly
```

---

## 9. Monthly Input Row

Please define a small dataclass for monthly input rows.

Suggested dataclass:

```python
@dataclass
class MonthlyPlanInputRow:
    scenario_id: str
    product_id: str
    node_id: str
    month: str
    plan_type: str
    quantity: float
    source_id: str = ""
    comment: str = ""
```

Example:

```python
MonthlyPlanInputRow(
    scenario_id="BASE",
    product_id="PRODUCT_X",
    node_id="DAD_US",
    month="2026-M01",
    plan_type="S",
    quantity=100.0,
)
```

With 4-4-5 even distribution:

```text
2026-M01 = W01-W04
weekly quantity = 25.0
```

---

## 10. Weekly Input Row

Please define a small dataclass for weekly input rows.

Suggested dataclass:

```python
@dataclass
class WeeklyPlanInputRow:
    scenario_id: str
    product_id: str
    node_id: str
    week: str
    plan_type: str
    quantity: float
    source_id: str = ""
    comment: str = ""
```

Weekly input should pass through to `WeeklyPlanRow` without changing week keys.

This is important for Rice Case.

Example:

```text
2026-W40:
    old crop final consumption week
    new crop harvest start week

2026-W41:
    new crop consumption start week
```

These week keys must remain unchanged.

---

## 11. Monthly to Weekly Conversion

Please implement:

```python
def monthly_plan_to_weekly_rows(
    monthly_rows: list[MonthlyPlanInputRow],
    *,
    calendar_mode: str = "445",
    distribution_rule: str = "even",
) -> list[WeeklyPlanRow]:
    ...
```

MVP distribution rule:

```text
even
```

Example:

```text
monthly quantity = 100
month = 2026-M01
weeks = 2026-W01..2026-W04
weekly quantity = 25 each
```

For flow data such as S / P / demand / supply:

```text
weekly_qty = monthly_qty / number_of_weeks_in_month
```

---

## 12. Weekly Pass-Through

Please implement:

```python
def weekly_plan_to_weekly_rows(
    weekly_rows: list[WeeklyPlanInputRow],
    *,
    source_granularity: str = "weekly",
) -> list[WeeklyPlanRow]:
    ...
```

Behavior:

```text
week key is preserved
quantity is preserved
plan_type is preserved
```

No 4-4-5 conversion is applied.

---

## 13. Case Weekly Input

Please implement a generic helper for case weekly data.

Suggested function:

```python
def case_weekly_plan_to_weekly_rows(
    rows: list[WeeklyPlanInputRow],
    *,
    source_id: str,
) -> list[WeeklyPlanRow]:
    ...
```

This may delegate to `weekly_plan_to_weekly_rows`.

The purpose is to make the mode explicit for case modeling datasets such as:

```text
rice_supply_plan.csv
rice_demand_plan.csv
covid_vaccine_supply_plan.csv
covid_vaccine_region_demand.csv
```

---

## 14. Adapter Dispatcher

Please implement a dispatcher function:

```python
def normalize_plan_input_to_weekly_rows(
    *,
    input_mode: str,
    monthly_rows: list[MonthlyPlanInputRow] | None = None,
    weekly_rows: list[WeeklyPlanInputRow] | None = None,
    calendar_mode: str = "445",
    distribution_rule: str = "even",
    source_id: str = "",
) -> list[WeeklyPlanRow]:
    ...
```

Expected behavior:

```text
input_mode = monthly_sp:
    use monthly_plan_to_weekly_rows

input_mode = weekly_sp:
    use weekly_plan_to_weekly_rows

input_mode = case_weekly:
    use case_weekly_plan_to_weekly_rows
```

Invalid mode should raise `ValueError`.

---

## 15. Rice Case Boundary Test

Please include a test that confirms weekly mode preserves important Rice Case week boundaries.

Input:

```python
WeeklyPlanInputRow(
    scenario_id="RICE_AS_IS",
    product_id="BROWN_RICE_STANDARD",
    node_id="PRODUCER_NIIGATA",
    week="2026-W40",
    plan_type="supply",
    quantity=20.0,
)
```

Expected:

```text
output week = 2026-W40
quantity = 20.0
source_granularity = case_weekly
```

Also test:

```text
2026-W41 remains 2026-W41
```

This confirms that Rice Case's W40 / W41 semantics are not blurred by monthly conversion.

---

## 16. Tests

Please add:

```text
tests/test_plan_input_granularity_adapter.py
```

Required tests:

```text
1. 4-4-5 month-to-weeks map for M01 returns W01-W04.
2. 4-4-5 month-to-weeks map for M03 returns W09-W13.
3. 4-4-5 month-to-weeks map has 12 months and 52 total weeks.
4. Monthly S input converts to expected weekly quantities.
5. Monthly P input converts to expected weekly quantities.
6. Weekly input pass-through preserves week keys.
7. case_weekly input preserves Rice Case W40 / W41 boundary.
8. Dispatcher routes monthly_sp correctly.
9. Dispatcher routes weekly_sp correctly.
10. Dispatcher routes case_weekly correctly.
11. Invalid input mode raises ValueError.
```

Please keep tests deterministic.

---

## 17. Test Commands

Please run:

```bat
python -m pytest tests/test_plan_input_granularity_adapter.py
```

Optional compatibility checks:

```bat
python -m pytest tests/test_japanese_rice_case_smoke.py
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

If broader tests fail due to unrelated optional dependencies, report separately.

---

## 18. Completion Criteria

This request is complete when:

```text
[OK] calendar_445.py exists
[OK] weekly_plan_table.py exists
[OK] plan_input_granularity.py exists
[OK] monthly_sp input converts to weekly rows
[OK] weekly_sp input passes through to weekly rows
[OK] case_weekly input passes through to weekly rows
[OK] 4-4-5 mapping is tested
[OK] Rice W40 / W41 boundary preservation is tested
[OK] existing loaders are not modified
[OK] no GUI changes are made
[OK] focused tests pass
```

---

## 19. Expected Response from Codex

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
Lot_ID generation
PSI seeding
existing monthly loader refactor
GUI integration
Rice Case adapter refactor
database persistence
```

This request is only for:

```text
Plan Input Granularity Adapter v0r1:
    monthly / weekly / case_weekly input
    to canonical weekly plan table
```