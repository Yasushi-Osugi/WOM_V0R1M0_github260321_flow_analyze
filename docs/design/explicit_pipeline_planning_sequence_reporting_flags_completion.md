# Explicit Pipeline Planning Sequence Reporting Flags Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-24  
**Status:** Completion memo  
**Target path:** `docs/design/explicit_pipeline_planning_sequence_reporting_flags_completion.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Explicit Pipeline Planning Sequence Reporting Flags MVP**.

The purpose of this milestone was to add an isolated reporting-stack orchestration helper that controls the explicit pipeline reporting / issue / Cost-KPI chain through explicit feature flags.

The completed helper is:

```python
maybe_run_explicit_pipeline_reporting_stack_from_env(...)
```

The helper is implemented as a standalone switchboard.

It does not yet modify the planning sequence.

This was intentional.

The goal of this phase was:

```text
Build and test the switchboard before wiring it into the cockpit.
```

---

## 2. Background

Before this milestone, WOM had already completed the explicit pipeline explanation stack:

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

However, these layers were available as standalone helpers and exporters.

The missing layer was a safe orchestration helper that could decide, based on feature flags, which reporting / issue / Cost-KPI layers should run.

This milestone completes that isolated orchestration layer.

---

## 3. Implemented Files

This milestone added or updated:

```text
pysi/reporting/__init__.py
pysi/reporting/explicit_pipeline_reporting_flags.py
tests/test_explicit_pipeline_reporting_flags.py
```

The implementation was committed as:

```text
b5aa824 Add explicit pipeline reporting flags helper MVP
```

---

## 4. Implemented Helper Module

The new module is:

```text
pysi/reporting/explicit_pipeline_reporting_flags.py
```

This module provides an isolated switchboard for the reporting stack.

It orchestrates existing helper functions.

It does not implement new report, issue, or KPI logic.

It does not:

```text
modify GUI
modify run_full_plan
modify _run_planning_sequence
run the explicit bridge + capacity pipeline
execute ReplanCommand
perform automatic replanning
run OR optimization
persist to database
write Knowledge Continuity records
```

---

## 5. Implemented Main Helper

The implemented helper is:

```python
maybe_run_explicit_pipeline_reporting_stack_from_env(...)
```

Recommended conceptual signature:

```python
def maybe_run_explicit_pipeline_reporting_stack_from_env(
    env,
    *,
    output_root=None,
    cost_kpi_context=None,
) -> dict:
    ...
```

The helper returns and attaches a stable result dictionary:

```text
env.explicit_bridge_capacity_reporting_stack_results
```

The result dictionary contains:

```text
capacity_report
capacity_report_export
issue_candidates
issue_candidate_export
issue_candidate_cost_kpi
issue_candidate_cost_kpi_export
```

Each entry is either the generated object / export result, or `None`.

---

## 6. Supported Feature Flags

The helper supports the following flags.

```text
enable_explicit_bridge_capacity_report
enable_explicit_bridge_capacity_report_export
enable_explicit_bridge_capacity_issue_candidates
enable_explicit_bridge_capacity_issue_candidate_export
enable_explicit_bridge_capacity_issue_candidate_cost_kpi
enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export
```

All flags default to:

```python
False
```

The helper does not manage:

```text
enable_explicit_bridge_capacity_pipeline
```

That base pipeline flag remains handled elsewhere.

This helper assumes that the explicit pipeline result may already exist on `env`.

---

## 7. Execution Order

When enabled by flags, the helper runs the reporting stack in this order:

```text
1. capacity report attachment
2. capacity report export
3. issue candidate generation
4. issue candidate export
5. Cost / KPI enrichment
6. Cost / KPI export
```

Conceptual chain:

```text
maybe_build_explicit_pipeline_capacity_report_from_env(...)
    ↓
maybe_export_explicit_pipeline_capacity_report_from_env(...)
    ↓
maybe_build_explicit_pipeline_issue_candidates_from_env(...)
    ↓
maybe_export_explicit_pipeline_issue_candidates_from_env(...)
    ↓
maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env(...)
    ↓
maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env(...)
```

---

## 8. Reused Existing Helpers

The implementation reuses existing helper functions.

### 8.1 Capacity report

```python
maybe_build_explicit_pipeline_capacity_report_from_env(...)
```

Expected attachment:

```text
env.explicit_bridge_capacity_pipeline_report
```

### 8.2 Capacity report export

```python
maybe_export_explicit_pipeline_capacity_report_from_env(...)
```

Expected attachment:

```text
env.explicit_bridge_capacity_pipeline_report_export_result
```

### 8.3 Issue candidates

```python
maybe_build_explicit_pipeline_issue_candidates_from_env(...)
```

Expected attachment:

```text
env.explicit_bridge_capacity_issue_candidates
```

### 8.4 Issue candidate export

```python
maybe_export_explicit_pipeline_issue_candidates_from_env(...)
```

Expected attachment:

```text
env.explicit_bridge_capacity_issue_candidate_export_result
```

### 8.5 Cost / KPI enrichment

```python
maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env(...)
```

Expected attachment:

```text
env.explicit_bridge_capacity_issue_candidate_kpi_bundle
```

### 8.6 Cost / KPI export

```python
maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env(...)
```

Expected attachment:

```text
env.explicit_bridge_capacity_issue_candidate_kpi_export_result
```

The new helper does not duplicate these behaviors.

It coordinates them.

---

## 9. Dependency / No-Op Behavior

The MVP uses safe no-op dependency behavior.

If a child flag is true but the required parent object is missing:

```text
the child layer returns None
no exception is raised
no files are written
the result dictionary records None
```

Example:

```text
enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export=True
```

but:

```text
env.explicit_bridge_capacity_issue_candidate_kpi_bundle
```

is missing.

Result:

```text
results["issue_candidate_cost_kpi_export"] is None
```

and no export files are created.

This behavior is appropriate for an interactive planning environment where some layers may be selectively enabled.

Strict dependency validation can be added later as a separate option.

---

## 10. Output Directory Behavior

The helper supports `output_root`.

Default output root:

```text
outputs/explicit_pipeline
```

Derived paths are:

```text
capacity report export:
    output_root

issue candidate export:
    output_root / "issue_candidates"

Cost / KPI export:
    output_root / "issue_candidate_kpi"
```

The helper itself does not create output directories unnecessarily.

Directories are created only by the export helpers when an export actually runs.

This keeps flag-off and child-no-op behavior clean.

---

## 11. Cost / KPI Context Behavior

The helper implements Cost / KPI context precedence:

```text
1. explicit cost_kpi_context argument
2. env.explicit_bridge_capacity_cost_kpi_context
3. {}
```

This makes the helper usable from:

```text
tests
CLI
GUI
scenario runners
future notebook-style experiments
```

The precedence behavior was verified by tests.

The explicit argument wins over env context.

---

## 12. Env Attachment Behavior

The helper delegates the primary attachments to the existing helper functions.

It additionally attaches:

```text
env.explicit_bridge_capacity_reporting_stack_results
```

This provides a compact execution summary for:

```text
tests
debugging
future GUI display
future logging
```

The attached dictionary includes:

```text
capacity_report
capacity_report_export
issue_candidates
issue_candidate_export
issue_candidate_cost_kpi
issue_candidate_cost_kpi_export
```

---

## 13. Package Export

The reporting package export was updated in:

```text
pysi/reporting/__init__.py
```

The new helper is available through the package namespace:

```python
maybe_run_explicit_pipeline_reporting_stack_from_env
```

---

## 14. Tests Added

The focused test file is:

```text
tests/test_explicit_pipeline_reporting_flags.py
```

It validates:

```text
1. flag-off no-op
2. report-only execution
3. capacity report export
4. issue candidate generation
5. issue candidate export
6. Cost / KPI enrichment
7. Cost / KPI export
8. dependency no-op for child flag without parent data
9. output_root override routing
10. Cost / KPI context precedence
```

The tests use synthetic / minimal objects for orchestration-focused validation.

This keeps the tests focused on switchboard behavior rather than planning-engine correctness.

---

## 15. Validation

The focused reporting flags test passed:

```bat
python -m pytest tests/test_explicit_pipeline_reporting_flags.py
```

Observed result:

```text
10 passed
```

The broader regression set also passed:

```bat
python -m pytest tests/test_explicit_pipeline_issue_candidate_cost_kpi_export.py
python -m pytest tests/test_explicit_pipeline_issue_candidate_cost_kpi.py
python -m pytest tests/test_explicit_pipeline_issue_candidate_export.py
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
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results:

```text
tests/test_explicit_pipeline_issue_candidate_cost_kpi_export.py: 7 passed
tests/test_explicit_pipeline_issue_candidate_cost_kpi.py: 4 passed
tests/test_explicit_pipeline_issue_candidate_export.py: 8 passed
tests/test_explicit_pipeline_issue_candidates.py: 7 passed
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

## 16. Completion Criteria

This milestone satisfies the intended completion criteria.

```text
[OK] pysi/reporting/explicit_pipeline_reporting_flags.py exists
[OK] maybe_run_explicit_pipeline_reporting_stack_from_env(...) exists
[OK] helper reads all reporting flags with default False
[OK] helper returns stable result dict
[OK] helper attaches env.explicit_bridge_capacity_reporting_stack_results
[OK] capacity report flag is supported
[OK] capacity report export flag is supported
[OK] issue candidate flag is supported
[OK] issue candidate export flag is supported
[OK] Cost / KPI enrichment flag is supported
[OK] Cost / KPI export flag is supported
[OK] output_root routing works
[OK] cost_kpi_context precedence works
[OK] child flag without parent data is safe no-op
[OK] focused tests pass
[OK] broader regression tests pass
[OK] no GUI changes
[OK] no planning-sequence changes
[OK] no ReplanCommand execution
[OK] no Cost / KPI recalculation beyond existing enrichment helper
```

---

## 17. Meaning of This Milestone

Before this milestone:

```text
The reporting / issue / Cost-KPI layers existed, but orchestration was manual.
```

After this milestone:

```text
WOM has an isolated switchboard helper for the reporting / issue / Cost-KPI stack.
```

The helper makes the explanation stack controllable through explicit flags.

This is a key preparation step before wiring the stack into the planning sequence or GUI.

---

## 18. Current Pipeline Position

The staged integration now stands here:

```text
isolated utilities
    ↓
explicit pipeline runner                 ✅ Phase 1 completed
    ↓
feature flag helper                      ✅ Phase 2a completed
    ↓
run_full_plan insertion                  ✅ Phase 2b completed
    ↓
capacity reporting MVP                   ✅ Phase 3a completed
    ↓
capacity report attachment               ✅ Phase 3b completed
    ↓
capacity report export                   ✅ Phase 3c completed
    ↓
issue candidates                         ✅ Phase 4 completed
    ↓
issue candidate export                   ✅ completed
    ↓
Cost / KPI enrichment                    ✅ completed
    ↓
Cost / KPI export                        ✅ completed
    ↓
reporting flag switchboard helper        ✅ completed
    ↓
planning-sequence reporting insertion
    ↓
GUI / Management Cockpit display
```

---

## 19. Known Limitations

This milestone is intentionally limited.

It does not implement:

```text
planning-sequence insertion
GUI display
Management Cockpit implementation
strict dependency validation
database persistence
Knowledge Continuity persistence
automatic replanning
ReplanCommand execution
OR optimization
```

The helper is isolated and tested.

Planning-sequence insertion should be a separate phase and Codex request.

---

## 20. Future Milestones

### 20.1 Planning-sequence reporting insertion

A natural next step is to insert this helper into the planning sequence after the explicit pipeline result is generated.

Potential design memo:

```text
docs/design/explicit_pipeline_planning_sequence_reporting_stack_insertion.md
```

Conceptual insertion:

```python
explicit_result = maybe_run_explicit_bridge_capacity_pipeline_from_env(...)

if explicit_result is not None:
    maybe_run_explicit_pipeline_reporting_stack_from_env(self.env)
```

This should be done carefully, with feature flags defaulting to false.

### 20.2 Management Cockpit KPI View

A later design can define:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_view.md
```

Potential cockpit sections:

```text
capacity summary
issue candidates
Cost / KPI enriched issue candidates
top impact issues
assumptions
export links
```

### 20.3 Strict validation mode

A future helper option may add strict dependency checks:

```text
child flag true + parent object missing → ValueError
```

This may be useful for CI or batch runners.

### 20.4 Knowledge Continuity integration

Future layers may capture high-impact issues into:

```text
open issues
decision log candidates
facts and findings
next-entry prompts
```

This should remain explicitly controlled.

---

## 21. Summary

The Explicit Pipeline Planning Sequence Reporting Flags MVP is complete.

The key achievement is:

```text
WOM now has an isolated, tested switchboard helper for the reporting / issue / Cost-KPI stack.
```

The completed helper controls:

```text
capacity report
capacity report export
issue candidates
issue candidate export
Cost / KPI enrichment
Cost / KPI export
```

through explicit feature flags.

The system remains safely human-in-the-loop:

```text
no automatic replanning
no command execution
no GUI side effects
no hidden file export unless export flags are enabled
```

This prepares WOM for the next step:

```text
safe planning-sequence reporting-stack insertion
```

without turning the cockpit into a haunted control panel.
