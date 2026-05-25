# Codex Request: Implement Explicit Pipeline Management Issue / Planning Issue Candidates MVP

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/explicit_pipeline_management_issue_candidates.md
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
capacity reporting MVP          ✅ Phase 3a completed
    ↓
capacity report attachment      ✅ Phase 3b completed
    ↓
capacity report export          ✅ Phase 3c completed
    ↓
issue candidates                ← Phase 4 target
    ↓
cost/KPI
    ↓
GUI display
```

Phase 3a added the in-memory report object:

```python
ExplicitPipelineCapacityReport
```

Phase 3b attached it to env:

```python
env.explicit_bridge_capacity_pipeline_report
```

Phase 3c added the standalone exporter:

```python
export_explicit_pipeline_capacity_report(...)
```

This request is **Phase 4**.

Phase 4 should transform explicit pipeline capacity report records into structured candidate issues.

---

## 2. Main Objective

Add a deterministic issue-candidate builder that converts:

```python
ExplicitPipelineCapacityReport
```

into:

```python
ExplicitPipelineIssueCandidateBundle
```

The intended transformation is:

```text
ExplicitPipelineCapacityReport
    ↓
ExplicitPipelineIssueCandidateBundle
    ↓
planning_issue_candidates
management_issue_candidates
replan_command_candidates
health_issue_candidates
summary
```

The builder must preserve Lot_ID identity and must not execute any command.

---

## 3. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan / _run_planning_sequence.
3. Do not implement automatic replanning.
4. Do not execute ReplanCommand.
5. Do not implement cost / KPI calculation.
6. Do not implement OR optimization.
7. Do not implement database persistence.
8. Do not implement issue export yet.
9. Keep this as an additive in-memory candidate builder + focused tests.
```

This request is only for:

```text
Phase 4: Management Issue / Planning Issue candidate MVP
```

---

## 4. Files to Add / Modify

Please add:

```text
pysi/reporting/explicit_pipeline_issue_candidates.py
tests/test_explicit_pipeline_issue_candidates.py
```

Optionally update:

```text
pysi/reporting/__init__.py
```

to export the new APIs if this is consistent with existing package style.

Do not modify:

```text
pysi/gui/*
run_full_plan
planning sequence
capacity report exporter
costing / KPI modules
optimization modules
```

---

## 5. Existing Components to Reuse

Reuse:

```python
ExplicitPipelineCapacityReport
```

from:

```text
pysi/reporting/explicit_pipeline_capacity_report.py
```

The issue candidate builder should consume the report object directly.

It should not read CSV / JSON files.

It should not rebuild capacity reports.

---

## 6. Candidate Bundle Dataclass

Please implement:

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExplicitPipelineIssueCandidateBundle:
    product_name: str = ""

    planning_issue_candidates: list[dict] = field(default_factory=list)
    management_issue_candidates: list[dict] = field(default_factory=list)
    replan_command_candidates: list[dict] = field(default_factory=list)
    health_issue_candidates: list[dict] = field(default_factory=list)

    summary: dict[str, Any] = field(default_factory=dict)
    message: str = ""
```

Keep candidates as dictionary records for Phase 4 MVP.

Typed dataclasses can be introduced later after the issue taxonomy stabilizes.

---

## 7. Main Builder Function

Please implement:

```python
def build_explicit_pipeline_issue_candidates(
    report,
    *,
    product_name: str | None = None,
) -> ExplicitPipelineIssueCandidateBundle:
    ...
```

Expected behavior:

```text
1. Read ExplicitPipelineCapacityReport-like object.
2. Convert capacity_violation_records into planning issue candidates.
3. Conservatively elevate selected capacity violations to management issue candidates.
4. Convert lot_exception_records into planning issue candidates.
5. Conservatively elevate selected lot exceptions to management issue candidates.
6. Convert health_check_records into health issue candidates.
7. Conservatively elevate error health checks to management issue candidates.
8. Convert replan_candidate_records into replan command candidates.
9. Build summary counts and severity flags.
10. Return ExplicitPipelineIssueCandidateBundle.
```

The function should tolerate missing / empty record groups.

---

## 8. Candidate Principles

### 8.1 Lot is the subject

Whenever source records contain:

```text
lot_id
lot_ids
```

the candidate must preserve those IDs.

Do not collapse Lot_IDs into numeric quantities only.

### 8.2 Candidate only

A generated candidate is not an executed command.

For replan command candidates, always include:

```text
status = candidate_only
```

### 8.3 Evidence-preserving

Every candidate should include:

```text
evidence_record_type
source
message
```

The source should be:

```text
explicit_pipeline_capacity_report
```

unless a more specific source is already available and useful.

### 8.4 Deterministic rules

Severity and mapping should be rule-based.

Do not use LLM judgment inside the builder.

---

## 9. Planning Issue Candidate Schema

Planning issues represent operational planning problems.

Suggested schema:

```python
{
    "candidate_type": "planning_issue",
    "issue_type": "capacity_violation",
    "severity": "warning",
    "product": "RICE",
    "node": "MOM_ASIA",
    "week": 10,
    "capacity_type": "P",
    "lot_ids": ["LOT_001"],
    "evidence_record_type": "capacity_violation",
    "source": "explicit_pipeline_capacity_report",
    "message": "P capacity violation at MOM_ASIA week 10",
    "suggested_action": "review_capacity_or_rerun_backward_planning",
}
```

Supported planning issue types:

```text
capacity_violation
blocked_lot
overflow_inventory
backlog_lot
shifted_lot
missing_lot
```

---

## 10. Management Issue Candidate Schema

Management issues represent elevated business / decision-level signals.

Suggested schema:

```python
{
    "candidate_type": "management_issue",
    "issue_type": "capacity_bottleneck",
    "severity": "warning",
    "product": "RICE",
    "node": "MOM_ASIA",
    "week": 10,
    "capacity_type": "P",
    "lot_ids": ["LOT_001"],
    "business_theme": "supply_capacity_constraint",
    "evidence_record_type": "capacity_violation",
    "source": "explicit_pipeline_capacity_report",
    "message": "Capacity bottleneck candidate detected at MOM_ASIA week 10",
    "suggested_decision": "review capacity, allocation policy, or early-build scenario",
}
```

Supported management issue types:

```text
capacity_bottleneck
inventory_overflow_risk
service_risk
planning_data_quality_risk
shipment_capacity_constraint
```

Management issue candidates should be generated conservatively.

Not every planning issue needs a management issue.

---

## 11. Replan Command Candidate Schema

Replan command candidates represent possible actions but must not be executed.

Suggested schema:

```python
{
    "candidate_type": "replan_command_candidate",
    "command_type": "capacity_replan",
    "status": "candidate_only",
    "product": "RICE",
    "node": "MOM_ASIA",
    "week": 10,
    "capacity_type": "P",
    "lot_ids": ["LOT_001"],
    "source": "explicit_pipeline_capacity_report",
    "message": "Candidate replan command generated from capacity report",
    "suggested_action": "review_capacity_or_rerun_backward_planning",
}
```

Important:

```text
Never execute this command in Phase 4.
```

---

## 12. Health Issue Candidate Schema

Health issues represent structural data / PSI invariant problems.

Suggested schema:

```python
{
    "candidate_type": "health_issue",
    "issue_type": "non_string_lot_error",
    "severity": "error",
    "product": "RICE",
    "details": [...],
    "evidence_record_type": "health_check",
    "source": "explicit_pipeline_capacity_report",
    "message": "Structural PSI health issue detected",
}
```

Supported health issue types:

```text
missing_lot
non_list_bucket_error
non_string_lot_error
```

These should usually be severity:

```text
error
```

---

## 13. Mapping Rules

### 13.1 capacity_violation_records

For each capacity violation record:

```text
create one planning_issue_candidate
```

Planning issue:

```text
issue_type = capacity_violation
```

If severity is `warning` or `error`, also create one management issue candidate.

Management mapping:

```text
capacity_type P → capacity_bottleneck
capacity_type S → shipment_capacity_constraint
capacity_type I → inventory_overflow_risk
otherwise       → capacity_bottleneck
```

Suggested action:

```text
review_capacity_or_rerun_backward_planning
```

Suggested decision:

```text
review capacity, allocation policy, or early-build scenario
```

### 13.2 lot_exception_records

Mapping by `exception_type`:

```text
blocked     → planning_issue: blocked_lot
overflow_i  → planning_issue: overflow_inventory
backlog     → planning_issue: backlog_lot
shifted     → planning_issue: shifted_lot
missing     → planning_issue: missing_lot + health_issue
```

Management issue elevation:

```text
blocked     → service_risk
overflow_i  → inventory_overflow_risk
backlog     → service_risk
missing     → planning_data_quality_risk
shifted     → no management issue by default
```

Reason:

```text
shifted lots may be normal early-build behavior.
```

### 13.3 health_check_records

For each health check record:

```text
create one health_issue_candidate
```

If severity is `error`, also create one management issue candidate:

```text
issue_type = planning_data_quality_risk
```

### 13.4 replan_candidate_records

For each replan candidate record:

```text
create one replan_command_candidate
status = candidate_only
```

Do not execute.

---

## 14. Severity Rules

Use deterministic severity rules:

```text
health_check severity error → error
missing_lot → error
capacity_violation severity error → error
capacity_violation severity warning → warning
blocked_lot → warning
overflow_i → warning
backlog → warning
shifted → info
```

If severity is missing:

```text
capacity_violation → warning
lot_exception → warning
health_check → error
```

---

## 15. Summary Counts

Build bundle summary with at least:

```python
{
    "product": "RICE",

    "planning_issue_candidate_count": 0,
    "management_issue_candidate_count": 0,
    "replan_command_candidate_count": 0,
    "health_issue_candidate_count": 0,

    "error_count": 0,
    "warning_count": 0,
    "info_count": 0,

    "has_error": False,
    "has_warning": False,
}
```

Rules:

```text
Count severities across all candidate groups.
has_error = error_count > 0
has_warning = warning_count > 0
```

---

## 16. Serialization Helpers

Please implement:

```python
def issue_candidates_to_dict(bundle: ExplicitPipelineIssueCandidateBundle) -> dict:
    ...

def issue_candidates_as_rows(bundle: ExplicitPipelineIssueCandidateBundle) -> list[dict]:
    ...
```

Row order:

```text
planning_issue_candidates
management_issue_candidates
replan_command_candidates
health_issue_candidates
```

The helpers should return serializable Python objects.

---

## 17. Env Helper

Please implement:

```python
def maybe_build_explicit_pipeline_issue_candidates_from_env(env):
    ...
```

Expected behavior:

```text
1. Read env.explicit_bridge_capacity_pipeline_report.
2. If missing, return None.
3. Build ExplicitPipelineIssueCandidateBundle.
4. Attach env.explicit_bridge_capacity_issue_candidates.
5. Return the bundle.
```

No GUI display.

No command execution.

---

## 18. Tests to Add

Please add:

```text
tests/test_explicit_pipeline_issue_candidates.py
```

### 18.1 Synthetic report with all record types

Create an `ExplicitPipelineCapacityReport` with:

```text
capacity_violation_records
lot_exception_records
health_check_records
replan_candidate_records
```

Include at least:

```text
P capacity violation
blocked lot
overflow_i lot
backlog lot
shifted lot
missing lot
health check error
replan candidate
```

Verify:

```text
planning issue candidates are generated
management issue candidates are generated conservatively
health issue candidates are generated
replan command candidates are generated
summary counts are correct
```

### 18.2 Empty report

Create an empty `ExplicitPipelineCapacityReport`.

Verify:

```text
all candidate lists are empty
summary counts are zero
has_error is False
has_warning is False
```

### 18.3 Lot_ID preservation

Verify source Lot_IDs are preserved in generated candidates.

For example:

```text
LOT_BLOCKED appears in blocked_lot planning issue
LOT_OVERFLOW appears in overflow_inventory planning issue
LOT_REPLAN appears in replan command candidate
```

### 18.4 Candidate-only status

Verify every replan command candidate has:

```text
status == "candidate_only"
```

### 18.5 Env helper no-op

Create env without report.

Verify:

```python
maybe_build_explicit_pipeline_issue_candidates_from_env(env) is None
```

### 18.6 Env helper attaches bundle

Create env with report.

Verify:

```text
env.explicit_bridge_capacity_issue_candidates exists
```

### 18.7 Serialization helpers

Verify:

```text
issue_candidates_to_dict(bundle) returns dict
issue_candidates_as_rows(bundle) returns list[dict]
```

---

## 19. Existing Tests to Run

Please run:

```bat
python -m pytest tests/test_explicit_pipeline_issue_candidates.py
python -m pytest tests/test_explicit_pipeline_capacity_report_export.py
python -m pytest tests/test_explicit_pipeline_capacity_report_attachment.py
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

## 20. Package Export

If updating `pysi/reporting/__init__.py`, export:

```python
ExplicitPipelineIssueCandidateBundle
build_explicit_pipeline_issue_candidates
maybe_build_explicit_pipeline_issue_candidates_from_env
issue_candidates_to_dict
issue_candidates_as_rows
```

Keep the update minimal.

---

## 21. Completion Criteria

This request is complete when:

```text
[OK] pysi/reporting/explicit_pipeline_issue_candidates.py exists
[OK] ExplicitPipelineIssueCandidateBundle exists
[OK] build_explicit_pipeline_issue_candidates(...) exists
[OK] planning_issue_candidates are generated
[OK] management_issue_candidates are generated conservatively
[OK] replan_command_candidates are generated with status=candidate_only
[OK] health_issue_candidates are generated
[OK] Lot_ID identity is preserved
[OK] summary counts are generated
[OK] serialization helpers exist
[OK] env helper exists
[OK] focused tests pass
[OK] no GUI changes
[OK] no planning-sequence changes
[OK] no cost / KPI calculation
[OK] no command execution
```

---

## 22. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. Candidate schemas implemented
4. Mapping rules implemented
5. Severity rules implemented
6. Summary fields implemented
7. Env helper behavior
8. Test commands executed
9. Test results
10. Limitations / follow-up
```

Please do not proceed into:

```text
issue export
automatic planning-sequence integration
GUI display
costing / KPI integration
OR optimization
database persistence
ReplanCommand execution
```

This request is only for:

```text
Phase 4: explicit pipeline issue candidate MVP
```
