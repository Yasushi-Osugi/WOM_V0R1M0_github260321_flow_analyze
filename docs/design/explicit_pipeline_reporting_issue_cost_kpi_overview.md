# Explicit Pipeline Reporting / Issue / Cost-KPI Overview Memo

**Version:** v0r1 overview  
**Date:** 2026-05-24  
**Status:** Overview memo  
**Target path:** `docs/design/explicit_pipeline_reporting_issue_cost_kpi_overview.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completed explicit pipeline explanation stack from reporting through issue candidates and Cost / KPI export.

The current completed chain is:

```text
execution result
    ↓
in-memory capacity report
    ↓
capacity report export
    ↓
issue candidate bundle
    ↓
issue candidate export
    ↓
Cost / KPI enrichment
    ↓
Cost / KPI export
```

The purpose of this memo is to provide a consolidated architectural view before moving into:

```text
GUI display
Management Cockpit integration
planning-sequence attachment
WOM Knowledge Continuity integration
```

This memo complements the earlier Phase 1–4 overview and extends it through the Cost / KPI enrichment and export layers.

---

## 2. Executive Summary

The explicit pipeline has evolved from a planning execution experiment into an explainable management-support data pipeline.

The current stack can now answer:

```text
1. What happened?
2. Which Lot_IDs were involved?
3. Which capacity / planning / health issue was detected?
4. Which management issue candidate was generated?
5. What Cost / KPI impact was estimated?
6. Which assumptions were used?
7. Which CSV / JSON evidence files were exported?
```

This is a major step toward WOM as a management decision-support environment.

The current output is not yet GUI-based.

Instead, WOM now has a stable data foundation:

```text
in-memory objects
    ↓
CSV / JSON audit files
    ↓
future Management Cockpit / GUI display
```

This is the right sequencing.

Before putting data into GUI, the records, summaries, assumptions, and audit outputs are now explicit and testable.

---

## 3. Current Completed Architecture

The current explicit pipeline explanation architecture can be viewed as seven layers.

```text
Layer 1: Execution Result
Layer 2: Capacity Report
Layer 3: Capacity Report Export
Layer 4: Issue Candidate Bundle
Layer 5: Issue Candidate Export
Layer 6: Cost / KPI Enrichment
Layer 7: Cost / KPI Export
```

Expanded:

```text
ExplicitBridgeCapacityPipelineResult
    ↓
ExplicitPipelineCapacityReport
    ↓
ExplicitPipelineCapacityReportExportResult
    ↓
ExplicitPipelineIssueCandidateBundle
    ↓
ExplicitPipelineIssueCandidateExportResult
    ↓
ExplicitPipelineIssueCandidateKPIBundle
    ↓
ExplicitPipelineIssueCandidateKPIExportResult
```

This forms the current explicit pipeline explanation spine.

---

## 4. Layer 1: Execution Result

### 4.1 Main object

```text
ExplicitBridgeCapacityPipelineResult
```

### 4.2 Main module

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
```

### 4.3 Role

The execution result captures the output of the explicit bridge + capacity pipeline.

It surfaces operational signals such as:

```text
missing_lot_ids
blocked_lot_ids
overflow_i_lot_ids
capacity usage signals
capacity violation signals
PSI invariant errors
```

### 4.4 Management meaning

This layer answers:

```text
What did the explicit pipeline execution produce?
```

It is close to the engine.

It is not yet a management view.

---

## 5. Layer 2: Capacity Report

### 5.1 Main object

```text
ExplicitPipelineCapacityReport
```

### 5.2 Main module

```text
pysi/reporting/explicit_pipeline_capacity_report.py
```

### 5.3 Role

The capacity report normalizes execution result signals into reportable groups:

```text
capacity_usage_records
capacity_violation_records
lot_exception_records
replan_candidate_records
health_check_records
summary
```

### 5.4 Management meaning

This layer answers:

```text
What capacity / lot / health conditions should be reported?
```

This converts raw execution signals into explainable report records.

---

## 6. Layer 3: Capacity Report Export

### 6.1 Main object

```text
ExplicitPipelineCapacityReportExportResult
```

### 6.2 Main module

```text
pysi/reporting/explicit_pipeline_capacity_report_exporter.py
```

### 6.3 Role

The capacity report exporter writes the capacity report to audit files.

Typical output files:

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

### 6.4 Management meaning

This layer answers:

```text
Where is the audit evidence for the capacity report?
```

It turns the in-memory capacity report into inspectable CSV / JSON files.

---

## 7. Layer 4: Issue Candidate Bundle

### 7.1 Main object

```text
ExplicitPipelineIssueCandidateBundle
```

### 7.2 Main module

```text
pysi/reporting/explicit_pipeline_issue_candidates.py
```

### 7.3 Role

The issue candidate builder transforms report records into issue candidates:

```text
planning_issue_candidates
management_issue_candidates
replan_command_candidates
health_issue_candidates
summary
```

### 7.4 Candidate categories

```text
Planning issues:
    operational planning problems

Management issues:
    elevated decision-support signals

Replan command candidates:
    possible actions, but candidate_only

Health issues:
    PSI / data quality / structural risks
```

### 7.5 Management meaning

This layer answers:

```text
What should a planner or manager review?
```

This is the first layer where WOM begins to speak in the language of management issues rather than only execution records.

---

## 8. Layer 5: Issue Candidate Export

### 8.1 Main object

```text
ExplicitPipelineIssueCandidateExportResult
```

### 8.2 Main module

```text
pysi/reporting/explicit_pipeline_issue_candidate_exporter.py
```

### 8.3 Role

The issue candidate exporter writes issue candidates to audit files.

Typical output files:

```text
planning_issues.csv
management_issues.csv
replan_command_candidates.csv
health_issues.csv
all_issue_candidates.csv
summary.json
issue_candidate_bundle.json
```

### 8.4 Management meaning

This layer answers:

```text
Where is the audit evidence for the generated issue candidates?
```

This allows issue candidates to be reviewed outside the GUI and before Cost / KPI enrichment.

---

## 9. Layer 6: Cost / KPI Enrichment

### 9.1 Main object

```text
ExplicitPipelineIssueCandidateKPIBundle
```

### 9.2 Main module

```text
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi.py
```

### 9.3 Role

The Cost / KPI enrichment layer attaches directional business impact fields to issue candidates.

It enriches:

```text
planning issue candidates
management issue candidates
replan command candidates
health issue candidates
```

with fields such as:

```text
impact_status
impact_category
impact_quantity
impact_quantity_basis
currency
estimated_lost_sales_value
estimated_margin_impact
estimated_inventory_cost_impact
estimated_capacity_cost_impact
estimated_service_penalty
estimated_total_business_impact
kpi_service_risk_score
kpi_inventory_risk_score
kpi_capacity_risk_score
kpi_data_quality_risk_score
cost_kpi_assumption_source
```

### 9.4 Important caveat

This is:

```text
scenario-level directional impact estimation
```

It is not:

```text
formal accounting
ERP-grade product costing
statutory financial reporting
```

### 9.5 Management meaning

This layer answers:

```text
How large might the business impact be?
```

This is the point where issue candidates receive a practical “value tag.”

---

## 10. Layer 7: Cost / KPI Export

### 10.1 Main object

```text
ExplicitPipelineIssueCandidateKPIExportResult
```

### 10.2 Main module

```text
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi_exporter.py
```

### 10.3 Role

The Cost / KPI exporter writes enriched issue candidates to audit files.

Typical output files:

```text
enriched_planning_issues.csv
enriched_management_issues.csv
enriched_replan_command_candidates.csv
enriched_health_issues.csv
all_enriched_issue_candidates.csv
summary.json
assumptions.json
issue_candidate_kpi_bundle.json
```

### 10.4 Management meaning

This layer answers:

```text
Where is the audit evidence for the business impact estimate?
```

It exports not only the enriched issue records but also the assumptions used.

This is essential for later management review.

---

## 11. Current Main File Map

### 11.1 Planning layer

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
```

### 11.2 Reporting layer

```text
pysi/reporting/explicit_pipeline_capacity_report.py
pysi/reporting/explicit_pipeline_capacity_report_exporter.py
pysi/reporting/explicit_pipeline_issue_candidates.py
pysi/reporting/explicit_pipeline_issue_candidate_exporter.py
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi.py
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi_exporter.py
```

### 11.3 Test layer

```text
tests/test_explicit_bridge_capacity_pipeline.py
tests/test_explicit_bridge_capacity_pipeline_feature_flag.py
tests/test_run_full_plan_explicit_pipeline_insertion.py
tests/test_explicit_pipeline_capacity_reporting.py
tests/test_explicit_pipeline_capacity_report_attachment.py
tests/test_explicit_pipeline_capacity_report_export.py
tests/test_explicit_pipeline_issue_candidates.py
tests/test_explicit_pipeline_issue_candidate_export.py
tests/test_explicit_pipeline_issue_candidate_cost_kpi.py
tests/test_explicit_pipeline_issue_candidate_cost_kpi_export.py
```

---

## 12. Output Directory Map

The current export output structure is conceptually:

```text
outputs/
└── explicit_pipeline/
    ├── capacity_usage.csv
    ├── capacity_violations.csv
    ├── lot_exceptions.csv
    ├── replan_candidates.csv
    ├── health_checks.csv
    ├── summary.json
    ├── all_records.csv
    ├── report.json
    │
    ├── issue_candidates/
    │   ├── planning_issues.csv
    │   ├── management_issues.csv
    │   ├── replan_command_candidates.csv
    │   ├── health_issues.csv
    │   ├── all_issue_candidates.csv
    │   ├── summary.json
    │   └── issue_candidate_bundle.json
    │
    └── issue_candidate_kpi/
        ├── enriched_planning_issues.csv
        ├── enriched_management_issues.csv
        ├── enriched_replan_command_candidates.csv
        ├── enriched_health_issues.csv
        ├── all_enriched_issue_candidates.csv
        ├── summary.json
        ├── assumptions.json
        └── issue_candidate_kpi_bundle.json
```

This structure separates:

```text
capacity evidence
issue evidence
business impact evidence
```

---

## 13. Safety Boundaries Preserved

Across the completed stack, the following boundaries were preserved:

```text
no automatic replanning
no ReplanCommand execution
no GUI display during data-model stabilization
no OR optimization
no database persistence
no Knowledge Continuity persistence yet
no formal accounting claim
```

The system remains:

```text
human-in-the-loop
feature-flag friendly
audit-friendly
testable
incrementally extendable
```

---

## 14. Candidate-Only Principle

A key design rule is:

```text
replan command candidates are not commands.
```

They remain:

```text
status = candidate_only
```

This is important because the explicit pipeline can suggest possible review actions but does not automatically alter the plan.

The current architecture supports:

```text
detect
explain
estimate
export
```

but not:

```text
decide
approve
execute
```

This distinction is essential for management trust.

---

## 15. Lot_ID Traceability

The stack preserves Lot_ID traceability across layers.

Conceptual trace:

```text
Lot_ID
    ↓
execution result
    ↓
capacity report
    ↓
issue candidate
    ↓
Cost / KPI enriched issue candidate
    ↓
CSV / JSON audit evidence
```

This supports the WOM design principle:

```text
Lot is the subject.
```

The practical meaning is:

```text
A manager can see which lots are affected by a capacity issue and how those lots contribute to the estimated impact.
```

---

## 16. Cost / KPI Philosophy

The Cost / KPI enrichment layer intentionally provides:

```text
directional business impact
```

not:

```text
formal accounting
```

The current design supports:

```text
relative prioritization
scenario comparison
issue triage
management explanation
```

It does not attempt:

```text
actual cost settlement
statutory accounting
ERP-grade costing
audit-grade financial reporting
```

Important summary flags:

```text
impact_values_are_directional = True
double_counting_possible = True
```

This is honest and useful.

---

## 17. Why Export Before GUI Was Correct

The current sequence deliberately built export layers before GUI display.

That is important.

```text
In-memory object
    ↓
CSV / JSON export
    ↓
test validation
    ↓
future GUI display
```

This sequence ensures that GUI will consume stable records rather than unstable intermediate objects.

The GUI can later be treated as a viewer over already-validated data.

This avoids the common failure mode:

```text
GUI first
data model later
```

WOM took the safer route:

```text
data model first
audit files second
GUI later
```

A boring route, but a good kind of boring. The kind accountants like and bugs dislike.

---

## 18. Relationship to Management Cockpit

The current stack is now ready to support a Management Cockpit view.

Potential cockpit sections:

```text
1. Capacity / lot exception summary
2. Planning issue candidates
3. Management issue candidates
4. Replan command candidates
5. Health issue candidates
6. Cost / KPI impact summary
7. Top business impact issues
8. Assumptions used
```

Potential cockpit columns:

```text
severity
issue_type
impact_category
product
node
week
capacity_type
lot_ids
estimated_total_business_impact
suggested_action
suggested_decision
```

The GUI should show:

```text
candidate
review
evidence
assumption
impact
```

not:

```text
automatic decision
```

---

## 19. Relationship to WOM Knowledge Continuity Layer

The completed explanation stack can later feed the WOM Knowledge Continuity Layer.

Potential mapping:

```text
high-impact management issues
    → open issues

recurring capacity bottlenecks
    → business rules / scenario patterns

data quality risks
    → facts and findings / open issues

replan candidates
    → next-entry prompts

validated issue impact patterns
    → decision log candidates
```

The current phase does not automate that flow.

It only creates structured evidence that future knowledge-continuity functions can consume.

This keeps the knowledge lifecycle controlled.

---

## 20. Completed Commit Trail

The relevant completed commits include:

```text
Phase 1–4 overview and completion:
fdcb6c0 Add explicit pipeline phase 1 to 4 overview memo
183bab9 Add explicit pipeline management issue candidates completion memo

Issue candidate export:
c7c047a Add explicit pipeline issue candidate export design
932757f Add explicit pipeline issue candidate export Codex request
55040e2 Add explicit pipeline issue candidate exporter MVP
42fa023 Add explicit pipeline issue candidate export completion memo

Cost / KPI enrichment:
d93612e Add explicit pipeline issue candidate cost KPI enrichment design
61cc03f Add explicit pipeline issue candidate cost KPI enrichment Codex request
26b4a5e Add explicit pipeline issue candidate cost KPI enrichment MVP
9f3ff27 Add explicit pipeline issue candidate cost KPI enrichment completion memo

Cost / KPI export:
17271d0 Add explicit pipeline issue candidate cost KPI export design
c7b8a24 Add explicit pipeline issue candidate cost KPI export Codex request
5b13af1 Add explicit pipeline issue candidate cost KPI exporter MVP
3957490 Add explicit pipeline issue candidate cost KPI export completion memo
```

---

## 21. Testing Confidence

The recent test runs repeatedly validated:

```text
explicit pipeline issue candidate export
explicit pipeline issue candidate Cost / KPI enrichment
explicit pipeline issue candidate Cost / KPI export
capacity report export
capacity report attachment
capacity reporting
run_full_plan explicit pipeline insertion
feature flag helper
explicit bridge capacity pipeline
weekly forward push with capacity
demand-to-supply execution bridge
capacity-aware inbound backward planning
Japanese rice case smoke
COVID vaccine with capacity push
```

This gives confidence that the reporting / issue / Cost-KPI layers were added without breaking the already-tested capacity and bridge behavior.

---

## 22. Current Management Meaning

At the current milestone, WOM can provide the following management-facing chain:

```text
Detected condition:
    capacity violation / blocked lot / overflow inventory / data quality issue

Translated issue:
    planning issue / management issue / replan candidate / health issue

Business impact:
    directional Cost / KPI estimate

Evidence:
    CSV / JSON audit files

Assumptions:
    explicit assumptions.json
```

This is already a practical management-support skeleton.

It is not yet polished for end-user display, but the data foundation is strong.

---

## 23. What Has Not Yet Been Done

The current stack does not yet include:

```text
GUI display
Management Cockpit screen integration
planning-sequence automatic export
feature flag policy for automatic export
database persistence
Knowledge Continuity persistence
approval workflow
formal Cost Master integration
multi-currency logic
OR optimization
automatic replan execution
```

These are future layers.

The important point is that the current foundation makes those future layers much safer to build.

---

## 24. Recommended Next Step

The next natural design target is:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_view.md
```

This should define how the GUI / Management Cockpit will display:

```text
capacity summary
issue candidates
Cost / KPI enriched issue candidates
top impact issues
assumptions
export file links
```

A safer intermediate design may also be useful:

```text
docs/design/explicit_pipeline_planning_sequence_reporting_flags.md
```

to define feature flags for:

```text
capacity report export
issue candidate generation
issue candidate export
Cost / KPI enrichment
Cost / KPI export
```

Recommended order:

```text
1. planning-sequence reporting feature flags
2. Management Cockpit KPI view design
3. GUI implementation
```

This prevents the GUI from becoming a hidden trigger for file exports or expensive processing.

---

## 25. Suggested Future Feature Flags

Potential flags:

```text
enable_explicit_bridge_capacity_pipeline
enable_explicit_bridge_capacity_report
enable_explicit_bridge_capacity_report_export
enable_explicit_bridge_capacity_issue_candidates
enable_explicit_bridge_capacity_issue_candidate_export
enable_explicit_bridge_capacity_issue_candidate_cost_kpi
enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export
```

The current implementation already has the foundation for some of these.

Future planning-sequence integration should make side effects explicit.

---

## 26. One-Page Architecture Summary

```text
Execution
  ExplicitBridgeCapacityPipelineResult
        |
        v
Reporting
  ExplicitPipelineCapacityReport
        |
        v
Reporting Export
  capacity CSV / JSON
        |
        v
Issue Translation
  ExplicitPipelineIssueCandidateBundle
        |
        v
Issue Export
  issue candidate CSV / JSON
        |
        v
Business Impact
  ExplicitPipelineIssueCandidateKPIBundle
        |
        v
Business Impact Export
  enriched issue CSV / JSON + assumptions
        |
        v
Future
  Management Cockpit / Knowledge Continuity
```

---

## 27. Summary

The reporting / issue / Cost-KPI explanation stack is now complete enough to serve as the data foundation for Management Cockpit design.

The completed chain is:

```text
execution result
    ↓
in-memory capacity report
    ↓
capacity report export
    ↓
issue candidate bundle
    ↓
issue candidate export
    ↓
Cost / KPI enrichment
    ↓
Cost / KPI export
```

The key achievement is:

```text
WOM can now convert explicit pipeline execution outcomes into externally inspectable management issue candidates with directional business impact and explicit assumptions.
```

This is a meaningful transition from:

```text
planning simulator
```

toward:

```text
explainable management decision-support system
```

The next question is no longer:

```text
Can WOM detect the issue?
```

The next question is:

```text
How should WOM present the issue to a manager?
```

That is the role of the next Management Cockpit / GUI design phase.
