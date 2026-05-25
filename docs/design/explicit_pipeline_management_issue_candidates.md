# Explicit Pipeline Management Issue / Planning Issue Candidates Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-23  
**Status:** Design memo  
**Target path:** `docs/design/explicit_pipeline_management_issue_candidates.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/explicit_pipeline_capacity_reporting.md`
- `docs/design/explicit_pipeline_capacity_reporting_completion.md`
- `docs/design/explicit_pipeline_capacity_report_attachment.md`
- `docs/design/explicit_pipeline_capacity_report_attachment_completion.md`
- `docs/design/explicit_pipeline_capacity_report_export.md`
- `docs/design/explicit_pipeline_capacity_report_export_completion.md`
- `docs/design/run_full_plan_explicit_pipeline_insertion_completion.md`

---

## 1. Purpose

This memo defines **Phase 4: Management Issue / Planning Issue Candidates** for the explicit bridge + capacity pipeline.

Phase 3 completed the reporting foundation:

```text
ExplicitBridgeCapacityPipelineResult
    ↓
ExplicitPipelineCapacityReport
    ↓
exported CSV / JSON audit trail
```

Phase 4 should transform report records into issue candidates.

The purpose is to convert explicit pipeline signals such as:

```text
capacity_violation_records
lot_exception_records
health_check_records
replan_candidate_records
```

into structured candidates:

```text
PlanningIssueCandidate
ManagementIssueCandidate
ReplanCommandCandidate
```

Phase 4 does **not** execute replanning automatically.

Phase 4 does **not** make final management decisions.

It only creates explainable candidate issues for review.

---

## 2. Current Completed State

The current staged integration is:

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

Phase 4 uses the report object:

```python
env.explicit_bridge_capacity_pipeline_report
```

or its exported audit files as evidence.

Recommended primary input:

```python
ExplicitPipelineCapacityReport
```

---

## 3. Design Goal

The Phase 4 goal is to add a deterministic issue-candidate builder:

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

The candidates should be:

```text
Lot_ID traceable
node / week / capacity-type aware
deterministic
serializable
non-executing
GUI-independent
cost/KPI-independent for now
```

---

## 4. Non-Goals

Phase 4 must not implement:

```text
automatic replanning
ReplanCommand execution
GUI display
cost / KPI calculation
OR optimization
database persistence
capacity editing UI
MOM policy editing UI
final management decision logic
```

Phase 4 only creates candidates.

---

## 5. Input Records

Primary input records from `ExplicitPipelineCapacityReport`:

```text
capacity_violation_records
lot_exception_records
health_check_records
replan_candidate_records
summary
```

Optional context:

```text
product_name
message
capacity_usage_records
```

Phase 4 should not depend on exported files, but exported files can be used for audit / debugging.

---

## 6. Recommended Module

Suggested module:

```text
pysi/reporting/explicit_pipeline_issue_candidates.py
```

Reason:

```text
The issue candidate builder consumes reporting records.
It does not belong in planning engines yet.
```

Alternative future location:

```text
pysi/management/issues/...
```

But Phase 4 MVP should stay near reporting to avoid premature architecture expansion.

---

## 7. Recommended Test File

Suggested test:

```text
tests/test_explicit_pipeline_issue_candidates.py
```

Tests should use synthetic `ExplicitPipelineCapacityReport` objects and, optionally, a report built from existing fixtures.

---

## 8. Candidate Bundle Dataclass

Recommended dataclass:

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

Keep candidates as dict rows for Phase 4 MVP.

Typed dataclasses can be introduced later when issue taxonomy stabilizes.

---

## 9. Main Builder Function

Recommended function:

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
1. Read ExplicitPipelineCapacityReport.
2. Convert capacity violations into planning + management issue candidates.
3. Convert lot exceptions into planning issue candidates.
4. Convert health checks into health issue candidates.
5. Convert replan candidate records into replan command candidates.
6. Build summary counts and severity flags.
7. Return ExplicitPipelineIssueCandidateBundle.
```

The function should tolerate missing / empty record groups.

---

## 10. Issue Candidate Principles

### 10.1 Lot is the subject

Whenever a record contains:

```text
lot_id
lot_ids
```

the issue candidate must preserve those IDs.

The candidate should not collapse Lot_IDs into only numeric quantities.

### 10.2 No automatic execution

Replan candidates are proposals only.

```text
candidate != command execution
```

### 10.3 Evidence-preserving

Every candidate should include a pointer back to its source record type.

Suggested field:

```text
evidence_record_type
```

Example:

```text
capacity_violation
lot_exception
health_check
replan_candidate
```

### 10.4 Deterministic severity

Severity should be rule-based and deterministic.

No LLM judgment inside the builder.

---

## 11. Candidate Schema: Planning Issue

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

Planning issue types:

```text
capacity_violation
blocked_lot
overflow_inventory
backlog_lot
shifted_lot
missing_lot
```

---

## 12. Candidate Schema: Management Issue

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

Management issue types:

```text
capacity_bottleneck
inventory_overflow_risk
service_risk
planning_data_quality_risk
```

Management issue candidates should be generated conservatively.

Not every planning issue needs a management issue.

---

## 13. Candidate Schema: Replan Command Candidate

Replan command candidates represent possible actions, but they must not be executed.

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

Important field:

```text
status = candidate_only
```

---

## 14. Candidate Schema: Health Issue

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

Health issue types:

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

## 15. Mapping Rules

### 15.1 capacity_violation_records

For each capacity violation:

```text
create planning_issue_candidate
```

If severity is `warning` or `error`, also create management issue candidate:

```text
capacity_bottleneck
```

Suggested mapping:

```text
capacity_type P → capacity_bottleneck
capacity_type S → shipment_capacity_constraint
capacity_type I → inventory_overflow_risk
```

### 15.2 lot_exception_records

Mapping by exception type:

```text
blocked      → planning_issue: blocked_lot
overflow_i   → planning_issue: overflow_inventory
backlog      → planning_issue: backlog_lot
shifted      → planning_issue: shifted_lot
missing      → planning_issue: missing_lot + health_issue
```

Management issue elevation:

```text
blocked      → service_risk candidate
overflow_i   → inventory_overflow_risk candidate
backlog      → service_risk candidate
missing      → planning_data_quality_risk candidate
shifted      → no management issue by default
```

Reason:

```text
shifted lots can be normal early-build behavior.
```

### 15.3 health_check_records

For each health check:

```text
create health_issue_candidate
```

If severity is error:

```text
also create management_issue_candidate: planning_data_quality_risk
```

### 15.4 replan_candidate_records

For each replan candidate record:

```text
create replan_command_candidate
```

Do not execute.

---

## 16. Severity Rules

Recommended severity mapping:

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
default to warning for capacity and lot exceptions
default to error for health checks
```

---

## 17. Summary Counts

Bundle summary should include:

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

Counts should be derived from all candidate groups.

---

## 18. Serialization Helpers

Recommended helpers:

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

---

## 19. Env Helper

Recommended helper:

```python
def maybe_build_explicit_pipeline_issue_candidates_from_env(env):
    ...
```

Expected behavior:

```text
1. Read env.explicit_bridge_capacity_pipeline_report.
2. If missing, return None.
3. Build issue candidate bundle.
4. Attach env.explicit_bridge_capacity_issue_candidates.
5. Return bundle.
```

No GUI display.

No command execution.

---

## 20. Optional Export Later

Issue candidate export should be a later phase.

Possible future files:

```text
outputs/explicit_pipeline/issue_candidates/planning_issues.csv
outputs/explicit_pipeline/issue_candidates/management_issues.csv
outputs/explicit_pipeline/issue_candidates/replan_commands.csv
outputs/explicit_pipeline/issue_candidates/health_issues.csv
outputs/explicit_pipeline/issue_candidates/summary.json
```

Do not implement export in Phase 4 MVP unless explicitly requested.

---

## 21. Relationship to Cost / KPI

Phase 4 should not calculate cost / KPI.

But it should preserve enough fields to support future integration:

```text
product
node
week
capacity_type
lot_ids
issue_type
severity
suggested_action
suggested_decision
```

Future cost / KPI logic can attach:

```text
lost_sales_value
inventory_cost_impact
capacity_investment_candidate
profit_impact
ROI impact
```

---

## 22. Relationship to GUI

Phase 4 does not display issues in GUI.

Future GUI may show:

```text
issue candidate list
severity filter
node/week drilldown
Lot_ID trace
suggested action
```

But Phase 4 only builds the candidate bundle.

---

## 23. Testing Strategy

### 23.1 Synthetic report with all record types

Create a synthetic `ExplicitPipelineCapacityReport` with:

```text
capacity_violation_records
lot_exception_records
health_check_records
replan_candidate_records
```

Verify candidate counts and mappings.

### 23.2 Empty report

Verify:

```text
all candidate lists empty
summary counts zero
has_error False
has_warning False
```

### 23.3 Lot_ID preservation

Verify Lot_IDs from source records are preserved in candidates.

### 23.4 No execution

Verify replan candidate has:

```text
status = candidate_only
```

### 23.5 Env helper no-op

If env has no report:

```text
maybe_build_explicit_pipeline_issue_candidates_from_env(env) returns None
```

### 23.6 Env helper attach

If env has report:

```text
env.explicit_bridge_capacity_issue_candidates is attached
```

---

## 24. Existing Tests to Run

Run:

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

---

## 25. Recommended Implementation Scope

Recommended Phase 4 MVP implementation:

```text
pysi/reporting/explicit_pipeline_issue_candidates.py
tests/test_explicit_pipeline_issue_candidates.py
```

Optional package export:

```text
pysi/reporting/__init__.py
```

Do not modify:

```text
pysi/gui/*
planning sequence
run_full_plan
exporter modules
cost / KPI modules
```

---

## 26. Completion Criteria

Phase 4 design is complete when it defines:

```text
[OK] issue candidate module location
[OK] bundle dataclass
[OK] main builder function
[OK] planning issue candidate schema
[OK] management issue candidate schema
[OK] replan command candidate schema
[OK] health issue candidate schema
[OK] mapping rules
[OK] severity rules
[OK] summary counts
[OK] serialization helpers
[OK] env helper
[OK] test strategy
[OK] boundaries from execution / cost / KPI / GUI
```

---

## 27. Summary

Phase 4 should transform explicit pipeline capacity report records into issue candidates.

The target flow is:

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

The guiding principle is:

```text
Generate explainable candidates.
Do not execute commands.
Do not make final decisions.
Preserve Lot_ID identity.
```

This moves WOM from audit reporting toward management decision support.
