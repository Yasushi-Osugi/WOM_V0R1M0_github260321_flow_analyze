# Codex Request: Implement COVID Vaccine With-Capacity PUSH Smoke Runner

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The design memo has been added:

```text
docs/design/case_covid_vaccine_with_capacity_push_forward_planning.md
```

This request is to implement the first smoke runner for the COVID vaccine case.

The purpose is to validate WOM's existing v0r2/v0r3 with-capacity PUSH components using a concrete vaccine distribution scenario.

This is **not** a request to implement a full COVID vaccine model.

This is only for a minimal smoke runner.

---

## 2. Main Objective

Implement a minimal COVID vaccine with-capacity PUSH Forward Planning smoke runner.

The smoke runner should demonstrate:

```text
available vaccine lots at CENTRAL_DC
    ↓
transport capacity gate
    ↓
regional / clinic allocation
    ↓
vaccination capacity gate
    ↓
administered lots
    ↓
blocked lots / capacity usage / violations
```

The smoke runner should use existing v0r2/v0r3 components as much as possible.

---

## 3. Existing Components to Reuse

Before coding, please inspect and reuse these existing modules:

```text
pysi/planning/forward_push_with_capacity_planner.py
pysi/planning/capacity_master.py
pysi/planning/capacity_io.py
pysi/planning/bottleneck_allocation.py
```

Expected reusable functions/classes include:

```text
ForwardPushWithCapacityPlanner
load_capacity_master_csv
build_capacity_lookup
get_capacity_record
CapacityUsage
CapacityViolation
run_forward_push_with_capacity_from_master
AllocationRule
```

Please avoid duplicating existing capacity gate logic.

---

## 4. Important Constraints

Please follow these constraints:

```text
1. Do not modify existing core planners unless absolutely necessary.
2. Do not modify GUI.
3. Do not implement a full vaccine supply chain model.
4. Do not implement manufacturer inbound supply yet.
5. Do not implement full FEFO policy yet.
6. Do not introduce database persistence.
7. Do not introduce external dependencies.
8. Keep this as a small smoke runner and focused test.
```

This request is for a minimal validation case.

---

## 5. Suggested Files

Please add:

```text
pysi/runners/run_covid_vaccine_with_capacity_push_smoke.py
tests/test_covid_vaccine_with_capacity_push.py
```

Optional, only if useful:

```text
pysi/cases/covid_vaccine/__init__.py
pysi/cases/covid_vaccine/lot_factory.py
pysi/cases/covid_vaccine/capacity_master_sample.csv
```

If adding a sample CSV is too much for this first version, it is acceptable to build the capacity records in memory inside the smoke runner and test.

Keep the first implementation simple.

---

## 6. Scenario Definition

Use this scenario:

```text
scenario_id: COVID_BASE
product_name: COVID_VACCINE_PFIZER
week: 2026-W40
```

Initial supply:

```text
CENTRAL_DC has 300 usable vaccine lots
```

Regions:

```text
TOKYO
OSAKA
AICHI
```

Regional demand:

```text
TOKYO: 150 lots
OSAKA: 120 lots
AICHI: 80 lots
```

Transport capacity:

```text
CENTRAL_DC → TOKYO: 100 lots/week
CENTRAL_DC → OSAKA: 80 lots/week
CENTRAL_DC → AICHI: 50 lots/week
```

Vaccination capacity:

```text
CLINIC_TOKYO_01: 90 lots/week
CLINIC_OSAKA_01: 70 lots/week
CLINIC_AICHI_01: 50 lots/week
```

---

## 7. Minimal Lot Definition

Create 300 vaccine lots.

Suggested lot format:

```python
{
    "lot_id": "VAC-PFZ-2026W40-000001",
    "product_id": "COVID_VACCINE_PFIZER",
    "dose_qty": 100,
    "current_node": "CENTRAL_DC",
    "target_region": None,
    "target_node": None,
    "week_available": "2026-W40",
    "expiry_week": "2026-W48",
    "quality_status": "usable",
}
```

For MVP:

```text
Only lots with quality_status == "usable" should be eligible.
If expiry_week < current week, exclude from allocation and record as expired.
```

For this smoke case, all lots may be usable and not expired.

---

## 8. Capacity Representation

Please use existing capacity master semantics.

The existing capacity type values are:

```text
P
S
I
```

For this smoke runner:

```text
transport capacity:
    model as S capacity on pseudo lane nodes

vaccination capacity:
    model as S capacity on clinic nodes
```

Suggested pseudo lane names:

```text
LANE_CENTRAL_TO_TOKYO
LANE_CENTRAL_TO_OSAKA
LANE_CENTRAL_TO_AICHI
```

Suggested capacity records:

```csv
scenario_id,tree_side,node_name,product_name,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
COVID_BASE,OUTBOUND,LANE_CENTRAL_TO_TOKYO,COVID_VACCINE_PFIZER,2026-W40,S,100,hard,LOT,100,COLD_CAL,transport capacity central to Tokyo
COVID_BASE,OUTBOUND,LANE_CENTRAL_TO_OSAKA,COVID_VACCINE_PFIZER,2026-W40,S,80,hard,LOT,100,COLD_CAL,transport capacity central to Osaka
COVID_BASE,OUTBOUND,LANE_CENTRAL_TO_AICHI,COVID_VACCINE_PFIZER,2026-W40,S,50,hard,LOT,100,COLD_CAL,transport capacity central to Aichi
COVID_BASE,OUTBOUND,CLINIC_TOKYO_01,COVID_VACCINE_PFIZER,2026-W40,S,90,hard,LOT,100,COLD_CAL,vaccination capacity Tokyo
COVID_BASE,OUTBOUND,CLINIC_OSAKA_01,COVID_VACCINE_PFIZER,2026-W40,S,70,hard,LOT,100,COLD_CAL,vaccination capacity Osaka
COVID_BASE,OUTBOUND,CLINIC_AICHI_01,COVID_VACCINE_PFIZER,2026-W40,S,50,hard,LOT,100,COLD_CAL,vaccination capacity Aichi
```

These can be created in memory or written as a temporary/sample CSV.

---

## 9. Required Smoke Logic

The smoke runner should perform two stages.

### 9.1 Stage 1: Transport Capacity Gate

For each region:

```text
requested_lots = regional demand lots
capacity = lane transport capacity
accepted_lots = lots transported to region
blocked_lots = lots blocked by lane capacity
```

Use existing:

```python
run_forward_push_with_capacity_from_master(...)
```

Expected transport results:

```text
TOKYO:
    requested 150
    capacity 100
    accepted 100
    blocked 50

OSAKA:
    requested 120
    capacity 80
    accepted 80
    blocked 40

AICHI:
    requested 80
    capacity 50
    accepted 50
    blocked 30
```

### 9.2 Stage 2: Vaccination Capacity Gate

For each clinic:

```text
requested_lots = transported lots available at clinic / region
capacity = clinic vaccination capacity
administered_lots = accepted lots through vaccination capacity
not_administered_lots = blocked by vaccination capacity
```

Expected vaccination results:

```text
TOKYO:
    clinic inventory 100
    vaccination capacity 90
    administered 90
    remaining 10

OSAKA:
    clinic inventory 80
    vaccination capacity 70
    administered 70
    remaining 10

AICHI:
    clinic inventory 50
    vaccination capacity 50
    administered 50
    remaining 0
```

---

## 10. Expected Summary Output

The smoke runner should print:

```text
=== COVID vaccine with-capacity PUSH smoke ===
scenario: COVID_BASE
week: 2026-W40
product: COVID_VACCINE_PFIZER

initial supply at CENTRAL_DC: 300 lots

transport:
  TOKYO requested 150 / capacity 100 / accepted 100 / blocked 50
  OSAKA requested 120 / capacity 80 / accepted 80 / blocked 40
  AICHI requested 80 / capacity 50 / accepted 50 / blocked 30

vaccination:
  TOKYO clinic inventory 100 / vaccination capacity 90 / administered 90 / remaining 10
  OSAKA clinic inventory 80 / vaccination capacity 70 / administered 70 / remaining 10
  AICHI clinic inventory 50 / vaccination capacity 50 / administered 50 / remaining 0

summary:
  total supply: 300
  transported lots: 230
  transport blocked lots: 120
  administered lots: 210
  clinic remaining usable inventory: 20
```

Important note:

The regional demand total is 350 while central supply is 300.

For this first smoke test, it is acceptable to treat each regional requested demand independently for capacity gate validation.

A later version can add strict central inventory depletion and regional priority allocation.

Please add a comment explaining this MVP simplification.

---

## 11. CSV Output

If simple, export:

```text
outputs/covid_vaccine/capacity_usage.csv
outputs/covid_vaccine/capacity_violation.csv
```

using existing exporters:

```python
export_capacity_usage_csv
export_capacity_violation_csv
```

If CSV output is implemented, ensure the output directory is created.

---

## 12. Test Requirements

Please add:

```text
tests/test_covid_vaccine_with_capacity_push.py
```

Required tests:

```text
1. creates 300 usable vaccine lots
2. transport capacity gate returns expected accepted / blocked counts
3. vaccination capacity gate returns expected administered / remaining counts
4. capacity usage records are generated
5. capacity violation records are generated for blocked transport lots
6. all lots preserve lot_id identity
```

Expected counts:

```text
transport accepted:
    TOKYO 100
    OSAKA 80
    AICHI 50
    total 230

transport blocked:
    TOKYO 50
    OSAKA 40
    AICHI 30
    total 120

administered:
    TOKYO 90
    OSAKA 70
    AICHI 50
    total 210

clinic remaining:
    TOKYO 10
    OSAKA 10
    AICHI 0
    total 20
```

---

## 13. Test Commands

Please run:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
python -m pysi.runners.run_covid_vaccine_with_capacity_push_smoke
```

Also run these existing compatibility tests:

```bat
python -m pytest tests/test_forward_push_with_capacity_planner.py
python -m pytest tests/test_capacity_master_io.py
python -m pytest tests/test_bottleneck_allocation.py
```

If full capacity test collection fails due to unrelated optional dependencies such as `pulp`, `matplotlib`, or `dash`, report it separately and do not treat it as this request failure.

---

## 14. Completion Criteria

This request is complete when:

```text
[OK] COVID vaccine smoke runner exists
[OK] 300 usable vaccine lots are created
[OK] transport capacity gates produce expected accepted / blocked counts
[OK] vaccination capacity gates produce expected administered / remaining counts
[OK] usage / violation records are generated
[OK] focused test passes
[OK] existing v0r2/v0r3 capacity tests still pass
[OK] no GUI changes are made
[OK] no core planner behavior is changed
```

---

## 15. Expected Response from Codex

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
full COVID vaccine model
manufacturer inbound modeling
FEFO implementation
GUI integration
database persistence
E2E Evaluation / Management Issue Generation
```

This request is only for the minimal:

```text
COVID vaccine with-capacity PUSH Forward Planning smoke runner
```