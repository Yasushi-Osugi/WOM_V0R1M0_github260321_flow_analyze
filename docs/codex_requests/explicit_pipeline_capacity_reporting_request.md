# Codex Request: Implement Explicit Pipeline Capacity Usage / Violation Reporting MVP

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/explicit_pipeline_capacity_reporting.md
```

Please read this design memo first.

The current staged integration status is:

```text
isolated utilities
    ↓
explicit pipeline runner        ✅ Phase 1 completed
    ↓
feature flag helper             ✅ Phase 2a completed
    ↓
run_full_plan insertion         ✅ Phase 2b completed
    ↓
capacity reporting              ← Phase 3a target
```

Phase 3a should implement an in-memory reporting layer for the explicit bridge + capacity pipeline result.

This request is only for:

```text
Phase 3a: in-memory capacity usage / violation reporting MVP
```

Do not implement GUI display yet.

---

## 2. Main Objective

Add a report builder module that converts:

```python
ExplicitBridgeCapacityPipelineResult
```

into a stable, serializable report object:

```python
ExplicitPipelineCapacityReport
```

The intended transformation is:

```text
ExplicitBridgeCapacityPipelineResult
    ↓
ExplicitPipelineCapacityReport
    ↓
capacity_usage_records
capacity_violation_records
lot_exception_records
replan_candidate_records
health_check_records
summary
```

This reporting layer should become the foundation for future:

```text
Management Issue generation
Cost / KPI integration
GUI display
CSV / JSON export
```

---

## 3. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan.
3. Do not modify loaders.
4. Do not implement Management Issue generation.
5. Do not implement costing / KPI calculation.
6. Do not implement OR optimization.
7. Do not execute ReplanCommand.
8. Do not add broad file export unless explicitly required.
9. Keep this as an additive in-memory report builder + focused tests.
```

This request is only for:

```text
capacity usage / violation reporting MVP
```

---

## 4. Files to Add / Modify

Please add:

```text
pysi/reporting/explicit_pipeline_capacity_report.py
tests/test_explicit_pipeline_capacity_reporting.py
```

If `pysi/reporting/__init__.py` exists and exports are customary, update it minimally.

Do not modify:

```text
pysi/gui/*
run_full_plan
loaders
costing / KPI modules
Management Issue modules
```

---

## 5. Existing Components to Reuse

Reuse the existing pipeline result type from:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
```

Relevant type:

```python
ExplicitBridgeCapacityPipelineResult
```

Relevant fields may include:

```text
product_name

source_lot_ids
missing_lot_ids
shifted_lot_ids
backlog_lot_ids
accepted_lot_ids
blocked_lot_ids
overflow_i_lot_ids

capacity_usage
capacity_violations
replan_commands

non_list_bucket_errors
non_string_lot_errors

message
```

The report builder should tolerate missing / empty fields.

---

## 6. Report Dataclass

Please implement:

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExplicitPipelineCapacityReport:
    product_name: str = ""

    capacity_usage_records: list[dict] = field(default_factory=list)
    capacity_violation_records: list[dict] = field(default_factory=list)
    lot_exception_records: list[dict] = field(default_factory=list)
    replan_candidate_records: list[dict] = field(default_factory=list)
    health_check_records: list[dict] = field(default_factory=list)

    summary: dict[str, Any] = field(default_factory=dict)
    message: str = ""
```

The report object should be simple, deterministic, and serializable.

---

## 7. Main Report Builder Function

Please implement:

```python
def build_explicit_pipeline_capacity_report(
    pipeline_result,
    *,
    product_name: str | None = None,
) -> ExplicitPipelineCapacityReport:
    ...
```

Expected behavior:

```text
1. Read pipeline_result.
2. Normalize capacity_usage into capacity_usage_records.
3. Normalize capacity_violations into capacity_violation_records.
4. Normalize missing / blocked / overflow / backlog / shifted lots into lot_exception_records.
5. Normalize replan_commands into replan_candidate_records.
6. Normalize invariant errors into health_check_records.
7. Build summary counts.
8. Return ExplicitPipelineCapacityReport.
```

The function should accept the existing result dataclass, but should also be tolerant of a simple object with the same attributes.

---

## 8. Capacity Usage Records

Normalize `pipeline_result.capacity_usage` into:

```python
{
    "record_type": "capacity_usage",
    "product": "RICE",
    "node": "MOM_ASIA",
    "week": 10,
    "capacity_type": "P",
    "capacity": 2,
    "used": 2,
    "remaining": 0,
    "utilization_ratio": 1.0,
    "source": "explicit_bridge_capacity_pipeline",
}
```

Required normalized fields:

```text
record_type
product
node
week
capacity_type
capacity
used
remaining
source
```

Optional fields:

```text
utilization_ratio
lot_ids
message
```

If upstream records already contain similar keys, preserve them where possible.

If some fields are absent, use safe defaults:

```text
node = ""
week = None
capacity_type = ""
capacity = None
used = None
remaining = None
```

---

## 9. Capacity Violation Records

Normalize `pipeline_result.capacity_violations` into:

```python
{
    "record_type": "capacity_violation",
    "product": "RICE",
    "node": "MOM_ASIA",
    "week": 10,
    "capacity_type": "P",
    "severity": "blocked",
    "capacity": 1,
    "requested": 2,
    "overflow": 1,
    "lot_ids": ["RT_JP_RICE_2026W10_0003"],
    "source": "weekly_forward_push_with_capacity",
}
```

Required normalized fields:

```text
record_type
product
node
week
capacity_type
severity
lot_ids
source
```

Severity examples:

```text
blocked
warning
overflow
error
```

If severity is missing, infer conservatively as:

```text
warning
```

---

## 10. Lot Exception Records

Create lot exception records from:

```text
missing_lot_ids
blocked_lot_ids
overflow_i_lot_ids
backlog_lot_ids
shifted_lot_ids
```

Suggested schema:

```python
{
    "record_type": "lot_exception",
    "exception_type": "blocked",
    "product": "RICE",
    "lot_id": "RT_JP_RICE_2026W10_0003",
    "node": "",
    "week": None,
    "source": "explicit_bridge_capacity_pipeline",
    "message": "Lot blocked by capacity",
}
```

Exception types:

```text
missing
blocked
overflow_i
backlog
shifted
```

Suggested messages:

```text
missing: "Lot missing from final demand/supply/backlog/blocked/overflow universe"
blocked: "Lot blocked by capacity"
overflow_i: "Lot contributes to inventory overflow"
backlog: "Lot remains in backlog"
shifted: "Lot shifted by capacity-aware planning"
```

Lot exception records are the bridge toward future Management Issue generation.

---

## 11. Replan Candidate Records

Normalize `pipeline_result.replan_commands` into records like:

```python
{
    "record_type": "replan_candidate",
    "command_type": "capacity_replan",
    "product": "RICE",
    "node": "MOM_ASIA",
    "week": 10,
    "capacity_type": "P",
    "lot_ids": ["RT_JP_RICE_2026W10_0003"],
    "suggested_action": "review_capacity_or_rerun_backward_planning",
    "source": "explicit_bridge_capacity_pipeline",
}
```

If upstream commands are dicts, preserve known fields and add missing normalized fields.

Important boundary:

```text
Phase 3a reports replan candidates.
Phase 3a does not execute replan commands.
```

---

## 12. Health Check Records

Create health check records from:

```text
missing_lot_ids
non_list_bucket_errors
non_string_lot_errors
```

Suggested schema:

```python
{
    "record_type": "health_check",
    "check_type": "non_string_lot_error",
    "severity": "error",
    "count": 1,
    "details": [...],
    "source": "explicit_bridge_capacity_pipeline",
}
```

Health check types:

```text
missing_lot
non_list_bucket_error
non_string_lot_error
```

Severity guidance:

```text
missing_lot: error
non_list_bucket_error: error
non_string_lot_error: error
```

If no issues exist, health_check_records may be empty.

---

## 13. Summary Counts

Build `report.summary` with at least:

```python
{
    "product": "RICE",

    "capacity_usage_record_count": 0,
    "capacity_violation_record_count": 0,
    "lot_exception_record_count": 0,
    "replan_candidate_record_count": 0,
    "health_check_record_count": 0,

    "missing_lot_count": 0,
    "blocked_lot_count": 0,
    "overflow_i_lot_count": 0,
    "backlog_lot_count": 0,
    "shifted_lot_count": 0,

    "has_error": False,
    "has_warning": False,
}
```

Rules:

```text
has_error = True if missing_lot_count > 0 or health_check_records contains severity error
has_warning = True if capacity_violation_records or lot_exception_records exist
```

Do not treat shifted lots as error.

Do not treat blocked lots as structural error; treat as business warning / capacity event.

---

## 14. Serialization Helpers

Please implement lightweight helpers:

```python
def report_to_dict(report: ExplicitPipelineCapacityReport) -> dict:
    ...

def report_records_as_rows(report: ExplicitPipelineCapacityReport) -> list[dict]:
    ...
```

Expected behavior:

```text
report_to_dict:
    returns a serializable dict with all report fields

report_records_as_rows:
    returns concatenated rows from:
        capacity_usage_records
        capacity_violation_records
        lot_exception_records
        replan_candidate_records
        health_check_records
```

Do not implement file writing in Phase 3a.

---

## 15. Optional Env Attachment Helper

Please implement:

```python
def maybe_build_explicit_pipeline_capacity_report_from_env(env):
    ...
```

Behavior:

```text
1. Read env.explicit_bridge_capacity_pipeline_result.
2. If missing, return None.
3. Build report.
4. Attach env.explicit_bridge_capacity_pipeline_report = report.
5. Return report.
```

This helper should not display anything in GUI.

This helper should be no-op if no explicit pipeline result exists.

---

## 16. Tests to Add

Please add:

```text
tests/test_explicit_pipeline_capacity_reporting.py
```

### 16.1 Synthetic result test

Create an `ExplicitBridgeCapacityPipelineResult` with:

```text
product_name = "RICE"
blocked_lot_ids = ["LOT_BLOCKED"]
overflow_i_lot_ids = ["LOT_OVERFLOW"]
missing_lot_ids = ["LOT_MISSING"]
backlog_lot_ids = ["LOT_BACKLOG"]
shifted_lot_ids = ["LOT_SHIFTED"]
capacity_usage = [...]
capacity_violations = [...]
replan_commands = [...]
```

Build report.

Verify:

```text
summary counts are correct
lot_exception_records contain blocked / overflow_i / missing / backlog / shifted
capacity_usage_records are normalized
capacity_violation_records are normalized
replan_candidate_records are normalized
health_check_records include missing_lot
has_error == True
has_warning == True
```

### 16.2 Empty result safety

Create an empty `ExplicitBridgeCapacityPipelineResult`.

Verify:

```text
all record lists are empty
summary counts are zero
has_error == False
has_warning == False
```

### 16.3 Env helper no-op

Create env without `explicit_bridge_capacity_pipeline_result`.

Verify:

```text
maybe_build_explicit_pipeline_capacity_report_from_env(env) is None
```

### 16.4 Env helper attaches report

Create env with `explicit_bridge_capacity_pipeline_result`.

Verify:

```text
result = maybe_build_explicit_pipeline_capacity_report_from_env(env)
result is env.explicit_bridge_capacity_pipeline_report
```

### 16.5 Serialization helpers

Verify:

```text
report_to_dict(report) returns dict
report_records_as_rows(report) returns list[dict]
```

---

## 17. Existing Tests to Run

Please run:

```bat
python -m pytest tests/test_explicit_pipeline_capacity_reporting.py
python -m pytest tests/test_run_full_plan_explicit_pipeline_insertion.py
python -m pytest tests/test_explicit_bridge_capacity_pipeline_feature_flag.py
python -m pytest tests/test_explicit_bridge_capacity_pipeline.py
python -m pytest tests/test_e2e_bridge_forward_capacity_smoke.py
python -m pytest tests/test_weekly_forward_push_with_capacity.py
python -m pytest tests/test_demand_to_supply_execution_bridge.py
python -m pytest tests/test_capacity_aware_inbound_backward_planning.py
python -m pytest tests/test_japanese_rice_case_smoke.py
```

Optional:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

If optional tests are not run, state so clearly.

---

## 18. Completion Criteria

This request is complete when:

```text
[OK] pysi/reporting/explicit_pipeline_capacity_report.py exists
[OK] ExplicitPipelineCapacityReport exists
[OK] build_explicit_pipeline_capacity_report(...) exists
[OK] capacity_usage_records are normalized
[OK] capacity_violation_records are normalized
[OK] lot_exception_records are generated
[OK] replan_candidate_records are generated
[OK] health_check_records are generated
[OK] summary counts are generated
[OK] report_to_dict(...) exists
[OK] report_records_as_rows(...) exists
[OK] maybe_build_explicit_pipeline_capacity_report_from_env(...) exists
[OK] focused tests pass
[OK] no GUI changes
[OK] no run_full_plan changes
[OK] no Management Issue generation
[OK] no cost / KPI calculation
```

---

## 19. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. Record schemas implemented
4. Summary fields implemented
5. Serialization helpers implemented
6. Env helper behavior
7. Test commands executed
8. Test results
9. Limitations / follow-up
```

Please do not proceed into:

```text
GUI display
Management Issue generation
costing / KPI integration
OR optimization
CSV / JSON file export
database persistence
```

This request is only for:

```text
Phase 3a: explicit pipeline capacity reporting MVP
```
