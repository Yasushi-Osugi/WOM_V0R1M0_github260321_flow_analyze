# Explicit Pipeline Capacity Usage / Violation Reporting Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-23  
**Status:** Design memo  
**Target path:** `docs/design/explicit_pipeline_capacity_reporting.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/run_full_plan_explicit_bridge_capacity_pipeline.md`
- `docs/design/run_full_plan_explicit_pipeline_feature_flag.md`
- `docs/design/run_full_plan_explicit_pipeline_insertion.md`
- `docs/design/run_full_plan_explicit_pipeline_insertion_completion.md`
- `docs/design/explicit_bridge_capacity_pipeline_runner_completion.md`
- `docs/design/explicit_pipeline_feature_flag_helper_completion.md`
- `docs/design/weekly_forward_push_with_capacity_psi_engine_completion.md`
- `docs/design/e2e_bridge_forward_capacity_smoke_completion.md`

---

## 1. Purpose

This memo defines **Phase 3: Capacity Usage / Violation Reporting** for the explicit bridge + capacity pipeline.

Phase 1 completed:

```text
explicit pipeline runner
```

Phase 2a completed:

```text
feature flag helper
```

Phase 2b completed:

```text
run_full_plan planning-sequence insertion behind feature flag
```

Phase 3 should make the explicit pipeline result reportable.

The purpose is to transform the raw explicit pipeline result into a stable reporting structure that can later be consumed by:

```text
Management Issue generation
Cost / KPI integration
GUI display
CSV / JSON export
```

Phase 3 is not GUI integration yet.

---

## 2. Current Completed Flow

The current completed flow is:

```text
run_full_plan / planning sequence
    ↓
outbound demand-side preparation
    ↓
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
    ↓
run_explicit_bridge_capacity_pipeline(...)
    ↓
explicit bridge + capacity pipeline result
```

The explicit pipeline internally represents:

```text
Bridge A
    ↓
MOM allocation
    ↓
TOBE capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
Weekly Forward PUSH with Capacity
```

The result already contains or can expose:

```text
missing_lot_ids
blocked_lot_ids
overflow_i_lot_ids
capacity_usage
capacity_violations
replan_commands
non_list_bucket_errors
non_string_lot_errors
```

Phase 3 should normalize these into report-friendly records.

---

## 3. Design Goal

The goal of Phase 3 is to add a clear reporting layer:

```text
ExplicitBridgeCapacityPipelineResult
    ↓
CapacityReportingSummary
    ↓
capacity_usage records
capacity_violation records
lot_exception records
replan candidate records
health check records
```

The reporting layer should be:

```text
deterministic
testable
serializable
independent from GUI
independent from costing
independent from Management Issue generation
```

---

## 4. Non-Goals

Phase 3 must not implement:

```text
GUI display
Management Issue generation
cost / KPI calculation
OR optimization
automatic replanning
capacity editing UI
MOM policy editing UI
database persistence
```

Phase 3 should only define and implement reportable structures and optional CSV / JSON style export helpers.

---

## 5. Reporting Inputs

Primary input:

```python
ExplicitBridgeCapacityPipelineResult
```

Likely source:

```python
env.explicit_bridge_capacity_pipeline_result
```

or:

```python
ctx["explicit_bridge_capacity_pipeline_result"]
```

Core fields to consume:

```text
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

---

## 6. Recommended Reporting Module

Suggested file:

```text
pysi/reporting/explicit_pipeline_capacity_report.py
```

Alternative if reporting package is not appropriate yet:

```text
pysi/plan/explicit_pipeline_capacity_report.py
```

Recommended:

```text
pysi/reporting/explicit_pipeline_capacity_report.py
```

because this is now a report transformation layer, not a planning engine.

---

## 7. Recommended Test File

Suggested test:

```text
tests/test_explicit_pipeline_capacity_reporting.py
```

This should build a minimal `ExplicitBridgeCapacityPipelineResult` or run the explicit pipeline fixture, then verify report records.

---

## 8. Report Result Dataclass

Recommended dataclass:

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

The report should be simple and serializable.

---

## 9. Main Function

Recommended function:

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

---

## 10. Capacity Usage Records

Capacity usage records should describe how capacity was used.

Suggested schema:

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

Required fields:

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

If upstream usage records already exist, preserve them as much as possible and add normalized fields where missing.

---

## 11. Capacity Violation Records

Capacity violation records should describe blocked / overflow / over-limit situations.

Suggested schema:

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

Required fields:

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

Capacity type examples:

```text
P
S
I
```

---

## 12. Lot Exception Records

Lot exception records should summarize lot-level exceptional states.

Suggested schema:

```python
{
    "record_type": "lot_exception",
    "exception_type": "blocked",
    "product": "RICE",
    "lot_id": "RT_JP_RICE_2026W10_0003",
    "node": "MOM_ASIA",
    "week": 10,
    "source": "explicit_bridge_capacity_pipeline",
    "message": "Lot blocked by P capacity",
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

Lot exceptions are the bridge toward later Management Issue generation.

---

## 13. Replan Candidate Records

The explicit pipeline may surface replan command candidates.

Suggested schema:

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
    "source": "weekly_forward_push_with_capacity",
}
```

Important boundary:

```text
Phase 3 reports replan candidates.
Phase 3 does not execute replan commands.
```

---

## 14. Health Check Records

Health checks should report structural problems.

Sources:

```text
non_list_bucket_errors
non_string_lot_errors
missing_lot_ids
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

Severity:

```text
info
warning
error
```

---

## 15. Summary Counts

The report should include a compact summary:

```python
{
    "product": "RICE",
    "capacity_usage_record_count": 12,
    "capacity_violation_record_count": 2,
    "lot_exception_record_count": 3,
    "replan_candidate_record_count": 1,
    "health_check_record_count": 0,

    "missing_lot_count": 0,
    "blocked_lot_count": 1,
    "overflow_i_lot_count": 1,
    "backlog_lot_count": 0,
    "shifted_lot_count": 1,

    "has_error": False,
    "has_warning": True,
}
```

This summary becomes the first compact management-facing signal.

---

## 16. Serialization Policy

The report should be serializable to:

```text
dict
JSON
CSV-like rows
```

Phase 3 MVP can implement only in-memory dataclasses and dict rows.

Optional helper functions:

```python
def report_to_dict(report: ExplicitPipelineCapacityReport) -> dict:
    ...

def report_records_as_rows(report: ExplicitPipelineCapacityReport) -> list[dict]:
    ...
```

CSV export can be a later small step.

---

## 17. Output File Naming Policy

If later file export is added, recommended paths:

```text
outputs/explicit_pipeline/capacity_usage.csv
outputs/explicit_pipeline/capacity_violations.csv
outputs/explicit_pipeline/lot_exceptions.csv
outputs/explicit_pipeline/replan_candidates.csv
outputs/explicit_pipeline/health_checks.csv
outputs/explicit_pipeline/summary.json
```

Do not implement broad file export in Phase 3 MVP unless requested.

---

## 18. Relationship to Management Issues

Phase 3 is the reporting foundation for later Management Issue generation.

Mapping concept:

```text
capacity_violation_record
    ↓
PlanningIssue candidate
    ↓
ManagementIssue candidate
```

But Phase 3 stops at:

```text
reportable records
```

It does not create formal Management Issues yet.

---

## 19. Relationship to Cost / KPI

Phase 3 should expose signals that later cost / KPI can consume.

Examples:

```text
blocked_lot_ids
    → lost sales / opportunity loss candidate

overflow_i_lot_ids
    → excess inventory / holding cost candidate

shifted_lot_ids
    → early build / inventory timing impact

capacity_usage
    → utilization KPI

capacity_violations
    → bottleneck / investment candidate
```

But Phase 3 does not calculate cost or KPI values.

---

## 20. Relationship to GUI

GUI should not be changed in Phase 3.

Future GUI display should consume:

```python
env.explicit_bridge_capacity_pipeline_report
```

or:

```python
ctx["explicit_bridge_capacity_pipeline_report"]
```

after this report is generated.

Phase 3 may optionally attach the report to env in a helper, but should not display it.

---

## 21. Optional Env Attachment Helper

Recommended helper for future use:

```python
def maybe_build_explicit_pipeline_capacity_report_from_env(env):
    result = getattr(env, "explicit_bridge_capacity_pipeline_result", None)
    if result is None:
        return None

    report = build_explicit_pipeline_capacity_report(result)
    env.explicit_bridge_capacity_pipeline_report = report
    return report
```

This helper should be no-op if no pipeline result exists.

---

## 22. Testing Strategy

### 22.1 Build report from synthetic result

Create an `ExplicitBridgeCapacityPipelineResult` with:

```text
blocked_lot_ids
overflow_i_lot_ids
missing_lot_ids
capacity_usage
capacity_violations
replan_commands
```

Verify report records and summary counts.

### 22.2 Build report from real explicit pipeline fixture

Use the existing minimal fixture from:

```text
tests/test_explicit_bridge_capacity_pipeline.py
```

or equivalent.

Verify:

```text
report.summary exists
lot exceptions reflect blocked / overflow lots
health checks are empty in happy path
```

### 22.3 Empty result safety

If all lists are empty, report should still be valid.

Expected:

```text
summary counts are zero
has_error == False
```

---

## 23. Existing Tests to Run

Run:

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

---

## 24. Recommended Implementation Phases

### Phase 3a: In-memory report builder

Add:

```text
pysi/reporting/explicit_pipeline_capacity_report.py
tests/test_explicit_pipeline_capacity_reporting.py
```

No file export.

No GUI.

### Phase 3b: Env attachment helper

Add:

```python
maybe_build_explicit_pipeline_capacity_report_from_env(env)
```

No GUI.

### Phase 3c: Optional CSV / JSON export

Only after report shape is stable.

---

## 25. Completion Criteria for This Design

This design is complete when it defines:

```text
[OK] reporting module location
[OK] report dataclass
[OK] main report builder function
[OK] capacity usage record schema
[OK] capacity violation record schema
[OK] lot exception record schema
[OK] replan candidate record schema
[OK] health check record schema
[OK] summary counts
[OK] serialization policy
[OK] test strategy
[OK] future Management Issue / Cost / GUI boundaries
```

---

## 26. Summary

Phase 3 should convert the explicit pipeline result into a stable reporting structure.

The core transformation is:

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

This is the first step from planning execution toward management explanation.

The guiding principle is:

```text
Do not jump to GUI or KPI yet.
First make the planning result explainable, testable, and serializable.
