# Explicit Pipeline Phase 1–4 Overview Memo

**Version:** v0r1 overview  
**Date:** 2026-05-23  
**Status:** Overview memo  
**Target path:** `docs/design/explicit_pipeline_phase1_to_phase4_overview.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo provides an overview of the work completed across **Phase 1 through Phase 4** of the explicit bridge + capacity pipeline integration.

The completed development path is:

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
```

The purpose of this sequence was to move WOM from:

```text
planning execution
```

toward:

```text
explainable management decision support
```

without jumping too quickly into GUI, cost/KPI, or automatic replanning.

---

## 2. Executive Summary

The completed chain is now:

```text
explicit bridge + capacity execution
    ↓
explicit pipeline result
    ↓
in-memory capacity report
    ↓
exported audit trail
    ↓
issue candidate bundle
```

In more concrete terms:

```text
ExplicitBridgeCapacityPipelineResult
    ↓
ExplicitPipelineCapacityReport
    ↓
ExplicitPipelineCapacityReportExportResult
    ↓
ExplicitPipelineIssueCandidateBundle
```

This means WOM now has the foundation to:

```text
1. run the explicit bridge + capacity pipeline,
2. capture the result,
3. explain capacity usage / violations,
4. export audit evidence,
5. generate Planning / Management / Replan / Health issue candidates.
```

Importantly, the implementation remains:

```text
feature-flagged
testable
human-in-the-loop
non-GUI for now
non-KPI for now
non-automatic-replan for now
```

---

## 3. Background

Before this work, the bridge / capacity / planning pieces existed mostly as isolated utilities and focused tests.

The key challenge was to connect them without destabilizing existing WOM behavior.

The integration strategy was therefore incremental:

```text
Phase 1:
    create an explicit pipeline runner

Phase 2:
    connect it safely to planning sequence behind a feature flag

Phase 3:
    make the result explainable and exportable

Phase 4:
    convert explainable report records into issue candidates
```

This avoided the risky pattern of trying to connect everything at once:

```text
run_full_plan
    ↓
capacity engine
    ↓
reporting
    ↓
issue generation
    ↓
cost/KPI
    ↓
GUI
```

Instead, each step was completed with a narrow boundary and focused tests.

---

## 4. Phase 1: Explicit Bridge + Capacity Pipeline Runner

### 4.1 Purpose

Phase 1 introduced the explicit pipeline runner.

Its purpose was to wrap the already-implemented bridge and capacity utilities into a single additive runner.

The runner creates a pipeline-level result object without modifying `run_full_plan` or GUI behavior.

### 4.2 Main artifact

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
```

### 4.3 Main function

```python
run_explicit_bridge_capacity_pipeline(...)
```

### 4.4 Main result type

```python
ExplicitBridgeCapacityPipelineResult
```

### 4.5 Conceptual flow

```text
Bridge A
    ↓
MOM allocation
    ↓
capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
weekly forward PUSH with Capacity
    ↓
ExplicitBridgeCapacityPipelineResult
```

### 4.6 Key outputs

The Phase 1 result surfaces signals such as:

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

### 4.7 Meaning

Phase 1 created the first integrated execution wrapper.

Before Phase 1:

```text
Utilities existed, but the E2E explicit pipeline was not represented as one callable unit.
```

After Phase 1:

```text
The explicit bridge + capacity flow could be run and inspected as a single pipeline result.
```

---

## 5. Phase 2a: Feature Flag Helper

### 5.1 Purpose

Phase 2a added a feature-flag helper around the explicit pipeline runner.

This made the explicit pipeline safe to call from a larger planning context.

### 5.2 Main artifact

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
```

### 5.3 Main helper

```python
maybe_run_explicit_bridge_capacity_pipeline(ctx)
```

### 5.4 Behavior

```text
flag missing / False:
    return None
    no-op

flag True:
    validate required ctx keys
    run explicit pipeline
    attach ctx["explicit_bridge_capacity_pipeline_result"]
    return result
```

### 5.5 Safety policy

If the feature flag is enabled but required inputs are missing:

```python
ValueError
```

is raised.

This prevents silent failure when the explicit pipeline is intentionally enabled.

### 5.6 Meaning

Phase 2a introduced the controlled gate.

Before Phase 2a:

```text
The explicit pipeline could run directly, but did not have a standardized feature-flag gate.
```

After Phase 2a:

```text
The explicit pipeline could be activated safely and explicitly from a context object.
```

---

## 6. Phase 2b: run_full_plan Planning-Sequence Insertion

### 6.1 Purpose

Phase 2b inserted the explicit pipeline into the current planning sequence behind the feature flag.

This made the pipeline reachable from the `run_full_plan`-style flow while preserving default behavior.

### 6.2 Main artifacts

```text
pysi/gui/cockpit_tk.py
pysi/plan/explicit_bridge_capacity_pipeline.py
tests/test_run_full_plan_explicit_pipeline_insertion.py
```

### 6.3 Insertion point

The insertion was made inside:

```python
_run_planning_sequence(...)
```

The call was placed after outbound demand-side preparation and before downstream MOM allocation / inbound / capacity / push-pull stages.

### 6.4 Main adapter

```python
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
```

### 6.5 Behavior

```text
feature flag off:
    existing behavior unchanged

feature flag on:
    explicit pipeline runs
    env.explicit_bridge_capacity_pipeline_result is attached
```

### 6.6 GUI boundary

Although `pysi/gui/cockpit_tk.py` was touched, this was because the planning sequence currently lives there.

Phase 2b did not add:

```text
new GUI widgets
new buttons
new report panels
new visual display behavior
```

### 6.7 Meaning

Phase 2b connected the explicit pipeline to the operational planning flow.

Before Phase 2b:

```text
The explicit pipeline was callable, but not reachable from the planning sequence.
```

After Phase 2b:

```text
The explicit pipeline became reachable from the main planning sequence, but only when explicitly enabled.
```

---

## 7. Phase 3a: Capacity Reporting MVP

### 7.1 Purpose

Phase 3a transformed the explicit pipeline result into an in-memory report object.

This made the pipeline result explainable without going directly to GUI or KPI.

### 7.2 Main artifacts

```text
pysi/reporting/explicit_pipeline_capacity_report.py
tests/test_explicit_pipeline_capacity_reporting.py
```

### 7.3 Main report type

```python
ExplicitPipelineCapacityReport
```

### 7.4 Main builder

```python
build_explicit_pipeline_capacity_report(...)
```

### 7.5 Conceptual transformation

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

### 7.6 Report record groups

The report includes:

```text
capacity_usage_records
capacity_violation_records
lot_exception_records
replan_candidate_records
health_check_records
summary
```

### 7.7 Meaning

Phase 3a converted raw execution signals into a stable reportable structure.

Before Phase 3a:

```text
The pipeline result had signals, but no report object.
```

After Phase 3a:

```text
The pipeline result could be explained through a normalized report.
```

---

## 8. Phase 3b: Capacity Report Attachment

### 8.1 Purpose

Phase 3b attached the capacity report to the planning environment after the explicit pipeline result is created.

### 8.2 Main artifacts

```text
pysi/gui/cockpit_tk.py
tests/test_explicit_pipeline_capacity_report_attachment.py
```

### 8.3 Main helper reused

```python
maybe_build_explicit_pipeline_capacity_report_from_env(env)
```

### 8.4 Completed flow

```text
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
    ↓
env.explicit_bridge_capacity_pipeline_result
    ↓
maybe_build_explicit_pipeline_capacity_report_from_env(env)
    ↓
env.explicit_bridge_capacity_pipeline_report
```

### 8.5 Code shape

```python
explicit_result = maybe_run_explicit_bridge_capacity_pipeline_from_env(...)

if explicit_result is not None:
    maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
```

### 8.6 Meaning

Phase 3b made the report available in the environment.

Before Phase 3b:

```text
The report builder existed, but planning sequence did not automatically attach a report.
```

After Phase 3b:

```text
When the explicit pipeline runs, the environment carries both result and report.
```

---

## 9. Phase 3c: Capacity Report Export

### 9.1 Purpose

Phase 3c added a standalone exporter that writes the in-memory report to CSV / JSON files.

This created the audit trail layer.

### 9.2 Main artifacts

```text
pysi/reporting/explicit_pipeline_capacity_report_exporter.py
tests/test_explicit_pipeline_capacity_report_export.py
```

### 9.3 Main export result type

```python
ExplicitPipelineCapacityReportExportResult
```

### 9.4 Main exporter

```python
export_explicit_pipeline_capacity_report(...)
```

### 9.5 Env helper

```python
maybe_export_explicit_pipeline_capacity_report_from_env(...)
```

### 9.6 Supported output files

```text
capacity_usage.csv
capacity_violations.csv
lot_exceptions.csv
replan_candidates.csv
health_checks.csv
summary.json
all_records.csv
report.json
```

### 9.7 Default output directory

```text
outputs/explicit_pipeline
```

### 9.8 Important boundary

Phase 3c is standalone.

It does not automatically export from planning sequence yet.

File output is side-effectful and should later be controlled by a separate feature flag.

### 9.9 Meaning

Phase 3c made the report externally inspectable.

Before Phase 3c:

```text
The report existed only in memory.
```

After Phase 3c:

```text
The report can be exported as stable audit evidence.
```

---

## 10. Phase 4: Management / Planning Issue Candidates

### 10.1 Purpose

Phase 4 transformed the capacity report into explainable issue candidates.

This moved WOM from audit reporting toward management decision support.

### 10.2 Main artifacts

```text
pysi/reporting/explicit_pipeline_issue_candidates.py
tests/test_explicit_pipeline_issue_candidates.py
```

### 10.3 Main bundle type

```python
ExplicitPipelineIssueCandidateBundle
```

### 10.4 Main builder

```python
build_explicit_pipeline_issue_candidates(...)
```

### 10.5 Conceptual transformation

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

### 10.6 Candidate groups

The bundle includes:

```text
planning_issue_candidates
management_issue_candidates
replan_command_candidates
health_issue_candidates
summary
```

### 10.7 Main mapping principles

```text
capacity_violation_records → planning issues + conservative management elevation
lot_exception_records → planning issues + selected management elevation
health_check_records → health issues + management elevation on error
replan_candidate_records → replan command candidates
```

### 10.8 Critical boundary

Every replan command candidate remains:

```text
status = candidate_only
```

No command execution is performed.

### 10.9 Meaning

Phase 4 created the interpretive layer.

Before Phase 4:

```text
WOM could explain capacity outcomes as report records.
```

After Phase 4:

```text
WOM can propose Planning / Management / Replan / Health issue candidates for human review.
```

---

## 11. Cross-Cutting Theme: WOM Knowledge Continuity Layer

During this same development stage, the following design document was added:

```text
docs/design/wom_knowledge_continuity_layer.md
```

This document defines a long-term knowledge continuity architecture for WOM.

It introduces the idea that WOM needs not only:

```text
code
tests
planning logic
```

but also:

```text
canonical definitions
decision logs
facts and findings
business rules
hypothesis registers
open issues
test anchors
next-entry prompts
```

This is complementary to Phase 1–4.

```text
Explicit Pipeline phases:
    detect and explain planning / capacity issues

Knowledge Continuity Layer:
    preserve decisions, facts, rules, issues, and next action prompts
```

Together, they form a larger loop:

```text
planning execution
    ↓
reporting
    ↓
issue candidates
    ↓
knowledge preservation
    ↓
next design / implementation action
```

This is the foundation for WOM Custom GAI / WOM Navigator style support.

---

## 12. Current Architecture After Phase 1–4

The current architecture can be viewed as four layers.

### 12.1 Execution layer

```text
explicit bridge + capacity pipeline
```

Produces:

```text
ExplicitBridgeCapacityPipelineResult
```

### 12.2 Reporting layer

```text
capacity report builder
```

Produces:

```text
ExplicitPipelineCapacityReport
```

### 12.3 Audit export layer

```text
capacity report exporter
```

Produces:

```text
ExplicitPipelineCapacityReportExportResult
CSV / JSON files
```

### 12.4 Issue candidate layer

```text
issue candidate builder
```

Produces:

```text
ExplicitPipelineIssueCandidateBundle
```

The complete chain is:

```text
ExplicitBridgeCapacityPipelineResult
    ↓
ExplicitPipelineCapacityReport
    ↓
ExplicitPipelineCapacityReportExportResult
    ↓
ExplicitPipelineIssueCandidateBundle
```

---

## 13. Safety Principles Preserved

Across Phase 1–4, the following safety principles were preserved:

```text
feature flag off means existing behavior unchanged
no automatic replanning
no command execution
no GUI display until the data structures are stable
no cost / KPI calculation before issue records stabilize
no OR optimization during report / issue candidate phases
Lot_ID identity is preserved
reports and issues are deterministic and testable
```

These principles prevented the implementation from becoming too broad or too risky.

---

## 14. Test Coverage Overview

The following focused and regression test groups were used through the phases:

```text
tests/test_explicit_bridge_capacity_pipeline.py
tests/test_explicit_bridge_capacity_pipeline_feature_flag.py
tests/test_run_full_plan_explicit_pipeline_insertion.py
tests/test_explicit_pipeline_capacity_reporting.py
tests/test_explicit_pipeline_capacity_report_attachment.py
tests/test_explicit_pipeline_capacity_report_export.py
tests/test_explicit_pipeline_issue_candidates.py
tests/test_e2e_bridge_forward_capacity_smoke.py
tests/test_weekly_forward_push_with_capacity.py
tests/test_demand_to_supply_execution_bridge.py
tests/test_capacity_aware_inbound_backward_planning.py
tests/test_japanese_rice_case_smoke.py
tests/test_covid_vaccine_with_capacity_push.py
```

The repeated passing of these tests shows that the new explicit pipeline layers were added without breaking the existing bridge / capacity / smoke behavior.

---

## 15. Current Repository State Concept

At the end of Phase 4, the conceptual repo state is:

```text
docs/design/
    run_full_plan_explicit_pipeline_insertion_completion.md
    explicit_pipeline_capacity_reporting_completion.md
    explicit_pipeline_capacity_report_attachment_completion.md
    explicit_pipeline_capacity_report_export_completion.md
    explicit_pipeline_management_issue_candidates_completion.md
    wom_knowledge_continuity_layer.md

pysi/plan/
    explicit_bridge_capacity_pipeline.py

pysi/reporting/
    explicit_pipeline_capacity_report.py
    explicit_pipeline_capacity_report_exporter.py
    explicit_pipeline_issue_candidates.py

tests/
    test_explicit_bridge_capacity_pipeline.py
    test_explicit_bridge_capacity_pipeline_feature_flag.py
    test_run_full_plan_explicit_pipeline_insertion.py
    test_explicit_pipeline_capacity_reporting.py
    test_explicit_pipeline_capacity_report_attachment.py
    test_explicit_pipeline_capacity_report_export.py
    test_explicit_pipeline_issue_candidates.py
```

---

## 16. Management Meaning

The work completed here is not just technical plumbing.

It changes WOM’s role.

Before:

```text
WOM generated planning results.
```

Now:

```text
WOM can begin to explain planning results as operational and management issue candidates.
```

This is important because management does not only need numbers.

Management needs:

```text
what happened
where it happened
which lots were affected
which node / week / capacity type was involved
what should be reviewed
what should not be automatically executed
```

The completed Phase 1–4 chain begins to provide that structure.

---

## 17. Why Cost / KPI Should Come Next

The next major phase is naturally:

```text
cost/KPI integration
```

But it is good that cost/KPI was not implemented before Phase 4.

Reason:

```text
Cost/KPI needs a stable issue/event/report structure to attach business meaning to.
```

Now that issue candidates exist, future cost/KPI logic can attach values such as:

```text
lost sales candidate
inventory holding cost candidate
capacity utilization
opportunity loss
profit impact
ROI impact
service risk
```

to specific issue candidates.

The future flow can become:

```text
issue candidate
    ↓
cost/KPI enrichment
    ↓
management cockpit / GUI
```

---

## 18. Future Milestone Candidates

### 18.1 Phase 5: Cost / KPI Enrichment

Potential design memo:

```text
docs/design/explicit_pipeline_issue_candidate_cost_kpi_enrichment.md
```

Purpose:

```text
Attach cost / KPI implications to issue candidates.
```

### 18.2 Issue Candidate Export

Potential design memo:

```text
docs/design/explicit_pipeline_issue_candidate_export.md
```

Purpose:

```text
Export Planning / Management / Replan / Health issue candidates to CSV / JSON.
```

### 18.3 Planning Sequence Issue Attachment

Potential design memo:

```text
docs/design/explicit_pipeline_issue_candidate_attachment.md
```

Purpose:

```text
Attach env.explicit_bridge_capacity_issue_candidates after capacity report attachment.
```

### 18.4 GUI Display

Potential design memo:

```text
docs/design/explicit_pipeline_issue_candidate_gui_view.md
```

Purpose:

```text
Display issue candidates in GUI only after issue schema and cost/KPI enrichment stabilize.
```

### 18.5 Knowledge Continuity MVP

Potential design memo:

```text
docs/design/wom_knowledge_continuity_mvp.md
```

Purpose:

```text
Create the first canonical definitions / decision logs / facts / open issues files.
```

---

## 19. Recommended Next Step

The most natural next implementation path is:

```text
Phase 5:
    Cost / KPI enrichment of issue candidates
```

However, a short intermediate step may be useful:

```text
Issue Candidate Export
```

because it would make the newly generated issue candidates externally inspectable, just as Phase 3c did for capacity reports.

Recommended sequence:

```text
1. Issue Candidate Export
2. Cost / KPI Enrichment
3. GUI Display
```

This keeps the same safe pattern:

```text
in-memory object
    ↓
export / audit trail
    ↓
business enrichment
    ↓
GUI
```

---

## 20. Summary

Phase 1–4 completed a major architectural bridge.

The new explicit pipeline capability is no longer only an execution path.

It is now an explainable decision-support path:

```text
execution
    ↓
reporting
    ↓
audit export
    ↓
issue candidates
```

The key achievement is:

```text
WOM can now preserve Lot_ID traceability from planning execution
through capacity reporting and into management issue candidates.
```

The system remains safely human-in-the-loop:

```text
issues are candidates
replan commands are candidate_only
decisions are not automated
GUI display is deferred
cost/KPI is deferred until issue structure is stable
```

This is a strong foundation for the next WOM evolution stage:

```text
from planning simulation
to explainable management decision support
```
