# Explicit Pipeline Management Issue Candidates Phase 4 Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-23  
**Status:** Completion memo  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Phase 4: Explicit Pipeline Management Issue / Planning Issue Candidates MVP**.

The purpose of this milestone was to transform the explicit pipeline capacity report into deterministic, explainable issue candidates.

The completed transformation is:

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

This phase does not implement GUI display, issue export, cost / KPI calculation, OR optimization, database persistence, or ReplanCommand execution.

The core principle is:

```text
Generate explainable candidates.
Do not execute commands.
Do not make final decisions.
Preserve Lot_ID identity.
```

---

## 2. Background

Before Phase 4, the staged integration had reached this state:

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
```

The prior phases created:

```text
execution result
    ↓
in-memory capacity report
    ↓
exported audit trail
```

Phase 4 adds the next interpretive layer:

```text
capacity report
    ↓
issue candidate bundle
```

---

## 3. Implemented Files

This milestone added or updated:

```text
pysi/reporting/__init__.py
pysi/reporting/explicit_pipeline_issue_candidates.py
tests/test_explicit_pipeline_issue_candidates.py
```

The implementation was committed as:

```text
b986e4d Add explicit pipeline issue candidate bundle builder
```

---

## 4. Implemented Issue Candidate Module

The new module is:

```text
pysi/reporting/explicit_pipeline_issue_candidates.py
```

It provides a pure in-memory transformation layer.

It does not:

```text
modify GUI
modify run_full_plan
modify _run_planning_sequence
execute ReplanCommand
calculate cost / KPI
run optimization
write issue export files
persist to database
```

---

## 5. Implemented Candidate Bundle Dataclass

The implemented dataclass is:

```python
ExplicitPipelineIssueCandidateBundle
```

It contains:

```text
product_name
planning_issue_candidates
management_issue_candidates
replan_command_candidates
health_issue_candidates
summary
message
```

Candidate records are dictionary-based in this MVP.

This keeps the implementation flexible while the issue taxonomy is still stabilizing.

---

## 6. Implemented Main Builder

The implemented main builder is:

```python
build_explicit_pipeline_issue_candidates(...)
```

It consumes an `ExplicitPipelineCapacityReport`-like object and generates:

```text
planning_issue_candidates
management_issue_candidates
replan_command_candidates
health_issue_candidates
summary
```

The builder is deterministic and rule-based.

It does not use LLM judgment at runtime.

---

## 7. Implemented Candidate Groups

### 7.1 Planning issue candidates

Planning issue candidates are generated from:

```text
capacity_violation_records
lot_exception_records
```

Supported planning issue types include:

```text
capacity_violation
blocked_lot
overflow_inventory
backlog_lot
shifted_lot
missing_lot
```

These candidates represent operational planning problems.

### 7.2 Management issue candidates

Management issue candidates are generated conservatively from:

```text
capacity_violation_records
selected lot_exception_records
error health_check_records
```

Supported management issue types include:

```text
capacity_bottleneck
shipment_capacity_constraint
inventory_overflow_risk
service_risk
planning_data_quality_risk
```

These candidates represent elevated business / decision-level signals.

### 7.3 Replan command candidates

Replan command candidates are generated from:

```text
replan_candidate_records
```

Every generated replan command candidate uses:

```text
status = candidate_only
```

This is a critical boundary.

The system proposes possible actions but does not execute them.

### 7.4 Health issue candidates

Health issue candidates are generated from:

```text
health_check_records
missing lot exceptions
```

Supported health issue types include:

```text
missing_lot
non_list_bucket_error
non_string_lot_error
```

These candidates represent structural PSI / data quality risks.

---

## 8. Implemented Mapping Rules

### 8.1 Capacity violation mapping

Each capacity violation generates:

```text
one planning_issue_candidate
```

If severity is:

```text
warning
error
```

then it also generates:

```text
one management_issue_candidate
```

Capacity type mapping:

```text
P → capacity_bottleneck
S → shipment_capacity_constraint
I → inventory_overflow_risk
other → capacity_bottleneck
```

### 8.2 Lot exception mapping

Lot exception mapping:

```text
blocked    → planning_issue: blocked_lot
overflow_i → planning_issue: overflow_inventory
backlog    → planning_issue: backlog_lot
shifted    → planning_issue: shifted_lot
missing    → planning_issue: missing_lot + health_issue
```

Management elevation:

```text
blocked    → service_risk
overflow_i → inventory_overflow_risk
backlog    → service_risk
missing    → planning_data_quality_risk
shifted    → no management issue by default
```

The reason shifted lots are not elevated by default is:

```text
shifted lots can represent normal early-build behavior.
```

### 8.3 Health check mapping

Each health check generates:

```text
one health_issue_candidate
```

If severity is:

```text
error
```

then it also generates:

```text
one management_issue_candidate: planning_data_quality_risk
```

### 8.4 Replan candidate mapping

Each replan candidate record generates:

```text
one replan_command_candidate
```

with:

```text
status = candidate_only
```

No execution logic is included.

---

## 9. Implemented Severity Rules

The implemented severity logic is deterministic.

Default / mapping rules include:

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

The bundle summary counts severities across all candidate groups.

---

## 10. Lot_ID Preservation

Lot identity is preserved through:

```text
lot_id
lot_ids
```

The implementation extracts Lot_IDs from source records and carries them into generated candidates.

This preserves the WOM principle:

```text
Lot is the subject.
```

The focused tests verify examples such as:

```text
LOT_BLOCKED
LOT_OVERFLOW
LOT_REPLAN
```

are retained in the generated candidates.

---

## 11. Implemented Summary

The bundle summary includes:

```text
product
planning_issue_candidate_count
management_issue_candidate_count
replan_command_candidate_count
health_issue_candidate_count
error_count
warning_count
info_count
has_error
has_warning
```

The summary flags are derived as:

```text
has_error = error_count > 0
has_warning = warning_count > 0
```

---

## 12. Implemented Serialization Helpers

The following helpers were implemented:

```python
issue_candidates_to_dict(...)
issue_candidates_as_rows(...)
```

### 12.1 issue_candidates_to_dict(...)

Returns a serializable dictionary representation of the candidate bundle.

### 12.2 issue_candidates_as_rows(...)

Returns a row list in stable order:

```text
planning_issue_candidates
management_issue_candidates
replan_command_candidates
health_issue_candidates
```

---

## 13. Implemented Env Helper

The implemented env helper is:

```python
maybe_build_explicit_pipeline_issue_candidates_from_env(env)
```

Behavior:

```text
1. Read env.explicit_bridge_capacity_pipeline_report.
2. If missing, return None.
3. Build ExplicitPipelineIssueCandidateBundle.
4. Attach env.explicit_bridge_capacity_issue_candidates.
5. Return the bundle.
```

This helper does not display anything in GUI and does not execute commands.

---

## 14. Package Export

The reporting package export was updated in:

```text
pysi/reporting/__init__.py
```

The following APIs were exported:

```text
ExplicitPipelineIssueCandidateBundle
build_explicit_pipeline_issue_candidates
maybe_build_explicit_pipeline_issue_candidates_from_env
issue_candidates_to_dict
issue_candidates_as_rows
```

---

## 15. Tests Added

The focused test file is:

```text
tests/test_explicit_pipeline_issue_candidates.py
```

It validates:

```text
1. synthetic report with all record types
2. empty report safety
3. Lot_ID preservation
4. candidate-only replan status
5. env helper no-op behavior
6. env helper bundle attachment
7. serialization helper outputs
```

---

## 16. Validation

The focused Phase 4 test passed:

```bat
python -m pytest tests/test_explicit_pipeline_issue_candidates.py
```

Observed result:

```text
7 passed
```

The broader regression set also passed:

```bat
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
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results:

```text
tests/test_explicit_pipeline_capacity_report_export.py: 8 passed
tests/test_explicit_pipeline_capacity_report_attachment.py: 3 passed
tests/test_explicit_pipeline_capacity_reporting.py: 5 passed
tests/test_run_full_plan_explicit_pipeline_insertion.py: 3 passed
tests/test_explicit_bridge_capacity_pipeline_feature_flag.py: 4 passed
tests/test_explicit_bridge_capacity_pipeline.py: 3 passed
tests/test_e2e_bridge_forward_capacity_smoke.py: 1 passed
tests/test_weekly_forward_push_with_capacity.py: 6 passed
tests/test_demand_to_supply_execution_bridge.py: 10 passed
tests/test_capacity_aware_inbound_backward_planning.py: 3 passed
tests/test_japanese_rice_case_smoke.py: 1 passed
tests/test_covid_vaccine_with_capacity_push.py: 1 passed
```

---

## 17. Completion Criteria

This milestone satisfies the intended completion criteria.

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
[OK] broader regression tests pass
[OK] no GUI changes
[OK] no planning-sequence changes
[OK] no cost / KPI calculation
[OK] no command execution
```

---

## 18. Meaning of This Milestone

Before Phase 4:

```text
WOM could produce and export capacity reports.
```

After Phase 4:

```text
WOM can interpret capacity report records as issue candidates.
```

This moves WOM from:

```text
explaining what happened
```

toward:

```text
suggesting what should be reviewed
```

without crossing into automatic decision-making.

The completed chain is:

```text
execution result
    ↓
in-memory report
    ↓
exported audit trail
    ↓
issue candidate bundle
```

---

## 19. Relationship to WOM Knowledge Continuity Layer

During this same development stage, the following design document was also added:

```text
docs/design/wom_knowledge_continuity_layer.md
```

That document defines a long-term knowledge continuity architecture for WOM.

Phase 4 issue candidate generation and the Knowledge Continuity Layer are complementary.

```text
Phase 4:
    turns planning/report signals into issue candidates

Knowledge Continuity Layer:
    preserves decisions, facts, rules, hypotheses, open issues, and next-entry prompts
```

Together, they point toward a future WOM capability:

```text
operational issue detection
    ↓
management explanation
    ↓
knowledge preservation
    ↓
next planning / design action
```

This is a foundation for WOM Custom GAI / WOM Navigator style support.

---

## 20. Current Pipeline Position

The staged integration now stands here:

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
issue candidates                ✅ Phase 4 completed
    ↓
cost/KPI
    ↓
GUI display
```

---

## 21. Known Limitations

Phase 4 is intentionally limited.

It does not implement:

```text
issue export
automatic planning-sequence integration
GUI display
cost / KPI calculation
OR optimization
database persistence
ReplanCommand execution
```

Candidate records remain dictionary-based.

Typed issue dataclasses and a formal issue taxonomy can be introduced later after the schema stabilizes.

---

## 22. Future Milestones

### 22.1 Issue candidate export

A later phase may export issue candidates to:

```text
outputs/explicit_pipeline/issue_candidates/planning_issues.csv
outputs/explicit_pipeline/issue_candidates/management_issues.csv
outputs/explicit_pipeline/issue_candidates/replan_commands.csv
outputs/explicit_pipeline/issue_candidates/health_issues.csv
outputs/explicit_pipeline/issue_candidates/summary.json
```

### 22.2 Planning sequence attachment

A later phase may attach issue candidates after report generation:

```text
env.explicit_bridge_capacity_pipeline_report
    ↓
env.explicit_bridge_capacity_issue_candidates
```

This should remain feature-controlled.

### 22.3 Cost / KPI integration

Future work should connect issue candidates to:

```text
service level
lost sales
inventory holding cost
capacity utilization
profit impact
ROI impact
```

### 22.4 GUI display

Future GUI work can display:

```text
severity
issue type
node
week
Lot_ID trace
suggested action
suggested decision
```

but only after the issue candidate schema is stable.

---

## 23. Summary

Phase 4 is complete.

The key achievement is:

```text
ExplicitPipelineCapacityReport can now be transformed into explainable Planning / Management / Replan / Health issue candidates.
```

The completed transformation is:

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

WOM now has a foundation for moving from capacity reporting into management decision support.

The system still remains safely human-in-the-loop:

```text
Issue candidates are generated.
Commands are not executed.
Final decisions are not automated.
