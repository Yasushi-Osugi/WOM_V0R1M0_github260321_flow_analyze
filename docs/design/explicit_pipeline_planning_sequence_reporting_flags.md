# Explicit Pipeline Planning Sequence Reporting Flags Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-24  
**Status:** Design memo  
**Target path:** `docs/design/explicit_pipeline_planning_sequence_reporting_flags.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/explicit_pipeline_phase1_to_phase4_overview.md`
- `docs/design/explicit_pipeline_reporting_issue_cost_kpi_overview.md`
- `docs/design/run_full_plan_explicit_pipeline_feature_flag.md`
- `docs/design/run_full_plan_explicit_pipeline_insertion.md`
- `docs/design/explicit_pipeline_capacity_report_attachment.md`
- `docs/design/explicit_pipeline_capacity_report_export.md`
- `docs/design/explicit_pipeline_issue_candidate_export.md`
- `docs/design/explicit_pipeline_issue_candidate_cost_kpi_enrichment.md`
- `docs/design/explicit_pipeline_issue_candidate_cost_kpi_export.md`
- `docs/design/wom_knowledge_continuity_layer.md`

---

## 1. Purpose

This memo defines a feature-flag design for controlling the explicit pipeline reporting / issue / Cost-KPI chain inside the planning sequence.

The current completed explanation stack is:

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

The next step is not yet GUI display.

Before GUI display, WOM should define a safe and explicit switchboard for deciding which layers run automatically during planning.

The goal of this memo is to define that switchboard.

---

## 2. Background

The explicit pipeline already has a planning-sequence insertion point for:

```text
explicit bridge + capacity pipeline
```

The result can be attached to env as:

```text
env.explicit_bridge_capacity_pipeline_result
```

The capacity report can also be attached as:

```text
env.explicit_bridge_capacity_pipeline_report
```

Later standalone modules can build / export:

```text
capacity report export
issue candidate bundle
issue candidate export
Cost / KPI enrichment
Cost / KPI export
```

However, file export and Cost / KPI enrichment are side-effectful or business-semantics-heavy operations.

Therefore, they should not silently run inside the planning sequence unless explicitly enabled.

This memo defines those flags and their dependency rules.

---

## 3. Design Goal

The design goal is:

```text
Create explicit feature flags that control each reporting / issue / Cost-KPI layer in planning sequence.
```

The flags should allow safe combinations such as:

```text
pipeline only
pipeline + report
pipeline + report + report export
pipeline + report + issue candidates
pipeline + report + issue candidates + Cost/KPI enrichment
pipeline + report + issue candidates + Cost/KPI enrichment + exports
```

The flags should also prevent unsafe or confusing combinations.

For example:

```text
Cost/KPI export should not run if Cost/KPI enrichment did not run.
Issue candidate export should not run if issue candidates do not exist.
Capacity report export should not run if capacity report does not exist.
```

---

## 4. Non-Goals

This design does not implement:

```text
GUI display
Management Cockpit panels
new Cost / KPI calculation rules
new issue candidate rules
automatic replanning
ReplanCommand execution
OR optimization
database persistence
Knowledge Continuity persistence
```

This memo only defines:

```text
planning-sequence feature flags
dependency rules
attachment rules
side-effect boundaries
testing strategy
```

---

## 5. Current Pipeline Objects

The current explicit pipeline explanation stack uses these objects:

```text
ExplicitBridgeCapacityPipelineResult
ExplicitPipelineCapacityReport
ExplicitPipelineCapacityReportExportResult
ExplicitPipelineIssueCandidateBundle
ExplicitPipelineIssueCandidateExportResult
ExplicitPipelineIssueCandidateKPIBundle
ExplicitPipelineIssueCandidateKPIExportResult
```

The intended env attributes are:

```text
env.explicit_bridge_capacity_pipeline_result
env.explicit_bridge_capacity_pipeline_report
env.explicit_bridge_capacity_pipeline_report_export_result
env.explicit_bridge_capacity_issue_candidates
env.explicit_bridge_capacity_issue_candidate_export_result
env.explicit_bridge_capacity_issue_candidate_kpi_bundle
env.explicit_bridge_capacity_issue_candidate_kpi_export_result
```

---

## 6. Proposed Feature Flags

The recommended feature flags are:

```text
enable_explicit_bridge_capacity_pipeline
enable_explicit_bridge_capacity_report
enable_explicit_bridge_capacity_report_export
enable_explicit_bridge_capacity_issue_candidates
enable_explicit_bridge_capacity_issue_candidate_export
enable_explicit_bridge_capacity_issue_candidate_cost_kpi
enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export
```

All flags should default to:

```python
False
```

The only exception is that a future interactive demo mode may intentionally turn on a preset bundle of flags, but that should be done explicitly by scenario setup.

---

## 7. Flag Definitions

### 7.1 enable_explicit_bridge_capacity_pipeline

Controls whether the explicit bridge + capacity pipeline runs.

When false:

```text
no explicit pipeline result
no report
no issue candidates
no Cost/KPI enrichment
no exports
```

When true:

```text
run explicit bridge + capacity pipeline
attach env.explicit_bridge_capacity_pipeline_result
```

### 7.2 enable_explicit_bridge_capacity_report

Controls whether the capacity report is built and attached.

Requires:

```text
enable_explicit_bridge_capacity_pipeline = True
```

When true:

```text
build ExplicitPipelineCapacityReport
attach env.explicit_bridge_capacity_pipeline_report
```

### 7.3 enable_explicit_bridge_capacity_report_export

Controls whether the capacity report is exported.

Requires:

```text
enable_explicit_bridge_capacity_report = True
```

When true:

```text
export capacity report CSV / JSON
attach env.explicit_bridge_capacity_pipeline_report_export_result
```

### 7.4 enable_explicit_bridge_capacity_issue_candidates

Controls whether issue candidates are built.

Requires:

```text
enable_explicit_bridge_capacity_report = True
```

When true:

```text
build ExplicitPipelineIssueCandidateBundle
attach env.explicit_bridge_capacity_issue_candidates
```

### 7.5 enable_explicit_bridge_capacity_issue_candidate_export

Controls whether issue candidates are exported.

Requires:

```text
enable_explicit_bridge_capacity_issue_candidates = True
```

When true:

```text
export issue candidate CSV / JSON
attach env.explicit_bridge_capacity_issue_candidate_export_result
```

### 7.6 enable_explicit_bridge_capacity_issue_candidate_cost_kpi

Controls whether issue candidates are enriched with Cost / KPI values.

Requires:

```text
enable_explicit_bridge_capacity_issue_candidates = True
```

When true:

```text
build ExplicitPipelineIssueCandidateKPIBundle
attach env.explicit_bridge_capacity_issue_candidate_kpi_bundle
```

### 7.7 enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export

Controls whether Cost / KPI enriched issue candidates are exported.

Requires:

```text
enable_explicit_bridge_capacity_issue_candidate_cost_kpi = True
```

When true:

```text
export enriched Cost / KPI issue candidate CSV / JSON
attach env.explicit_bridge_capacity_issue_candidate_kpi_export_result
```

---

## 8. Dependency Rules

The flags form a dependency tree.

```text
enable_explicit_bridge_capacity_pipeline
    └── enable_explicit_bridge_capacity_report
          ├── enable_explicit_bridge_capacity_report_export
          └── enable_explicit_bridge_capacity_issue_candidates
                ├── enable_explicit_bridge_capacity_issue_candidate_export
                └── enable_explicit_bridge_capacity_issue_candidate_cost_kpi
                      └── enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export
```

### 8.1 Strict dependency mode

Recommended MVP behavior:

```text
If a child flag is True but its parent output is missing, return None and do not execute that child layer.
```

Do not raise by default for reporting child flags.

Reason:

```text
Planning-sequence reporting flags should be safe in partially configured environments.
```

However, if the base pipeline flag itself is true and required pipeline inputs are missing, existing behavior should continue to raise a clear `ValueError`.

### 8.2 Optional strict validation

A future option may be:

```text
enable_explicit_reporting_flag_strict_validation
```

When true:

```text
child flag true + missing parent output → ValueError
```

This is useful for tests and CI but may be too harsh for interactive GUI use.

---

## 9. Recommended Planning Sequence Order

When enabled, the planning sequence should run these operations in order:

```text
1. explicit bridge + capacity pipeline
2. capacity report attachment
3. capacity report export
4. issue candidate generation
5. issue candidate export
6. Cost / KPI enrichment
7. Cost / KPI export
```

Expanded:

```text
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
    ↓
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

## 10. Recommended Integration Shape

The current planning-sequence code should avoid becoming a long chain of direct calls.

Instead, introduce a small orchestration helper.

Suggested module:

```text
pysi/reporting/explicit_pipeline_reporting_flags.py
```

Suggested helper:

```python
def maybe_run_explicit_pipeline_reporting_stack_from_env(env, *, output_root=None, cost_kpi_context=None):
    ...
```

This helper should read env flags, call the existing helpers, and attach results.

This keeps the planning sequence clean.

### 10.1 Why a helper is better than direct insertion

Direct insertion into `_run_planning_sequence` would make that function grow every time a reporting layer is added.

A helper keeps the GUI / planning sequence as:

```python
maybe_run_explicit_pipeline_reporting_stack_from_env(self.env)
```

rather than:

```python
maybe_build_report(...)
maybe_export_report(...)
maybe_build_issues(...)
maybe_export_issues(...)
maybe_enrich_kpi(...)
maybe_export_kpi(...)
```

This is a small but important architectural hygiene step.

The cockpit is a cockpit, not a spaghetti colander.

---

## 11. Suggested Helper Behavior

The helper should follow this pseudo-flow:

```python
def maybe_run_explicit_pipeline_reporting_stack_from_env(
    env,
    *,
    output_root=None,
    cost_kpi_context=None,
):
    results = {}

    if getattr(env, "enable_explicit_bridge_capacity_report", False):
        report = maybe_build_explicit_pipeline_capacity_report_from_env(env)
        results["capacity_report"] = report

    if getattr(env, "enable_explicit_bridge_capacity_report_export", False):
        export_result = maybe_export_explicit_pipeline_capacity_report_from_env(
            env,
            output_dir=...
        )
        results["capacity_report_export"] = export_result

    if getattr(env, "enable_explicit_bridge_capacity_issue_candidates", False):
        issues = maybe_build_explicit_pipeline_issue_candidates_from_env(env)
        results["issue_candidates"] = issues

    if getattr(env, "enable_explicit_bridge_capacity_issue_candidate_export", False):
        issue_export = maybe_export_explicit_pipeline_issue_candidates_from_env(
            env,
            output_dir=...
        )
        results["issue_candidate_export"] = issue_export

    if getattr(env, "enable_explicit_bridge_capacity_issue_candidate_cost_kpi", False):
        kpi_bundle = maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env(
            env,
            cost_kpi_context=cost_kpi_context,
        )
        results["issue_candidate_cost_kpi"] = kpi_bundle

    if getattr(env, "enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export", False):
        kpi_export = maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env(
            env,
            output_dir=...
        )
        results["issue_candidate_cost_kpi_export"] = kpi_export

    env.explicit_bridge_capacity_reporting_stack_results = results
    return results
```

---

## 12. Output Directory Policy

The helper should use a common output root.

Recommended default:

```text
outputs/explicit_pipeline
```

Derived directories:

```text
capacity report export:
    outputs/explicit_pipeline

issue candidate export:
    outputs/explicit_pipeline/issue_candidates

Cost / KPI export:
    outputs/explicit_pipeline/issue_candidate_kpi
```

If `output_root` is supplied:

```text
capacity report export:
    {output_root}

issue candidate export:
    {output_root}/issue_candidates

Cost / KPI export:
    {output_root}/issue_candidate_kpi
```

This keeps test outputs easy to isolate with `tmp_path`.

---

## 13. Cost / KPI Context Policy

Cost / KPI enrichment may require assumptions.

Potential env attribute:

```text
env.explicit_bridge_capacity_cost_kpi_context
```

The helper should choose context in this order:

```text
1. explicit cost_kpi_context argument
2. env.explicit_bridge_capacity_cost_kpi_context
3. empty dict
```

This keeps the helper usable from:

```text
tests
CLI
GUI
future scenario runners
```

---

## 14. Attachment Rules

The helper should not invent new result objects if child helpers already attach them.

It should rely on existing helper behavior:

```text
maybe_build_explicit_pipeline_capacity_report_from_env
    attaches env.explicit_bridge_capacity_pipeline_report

maybe_export_explicit_pipeline_capacity_report_from_env
    attaches env.explicit_bridge_capacity_pipeline_report_export_result

maybe_build_explicit_pipeline_issue_candidates_from_env
    attaches env.explicit_bridge_capacity_issue_candidates

maybe_export_explicit_pipeline_issue_candidates_from_env
    attaches env.explicit_bridge_capacity_issue_candidate_export_result

maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env
    attaches env.explicit_bridge_capacity_issue_candidate_kpi_bundle

maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env
    attaches env.explicit_bridge_capacity_issue_candidate_kpi_export_result
```

The orchestration helper may additionally attach:

```text
env.explicit_bridge_capacity_reporting_stack_results
```

as a compact execution summary.

---

## 15. Side Effect Policy

The following operations are in-memory only:

```text
capacity report attachment
issue candidate generation
Cost / KPI enrichment
```

The following operations write files:

```text
capacity report export
issue candidate export
Cost / KPI export
```

Therefore, all export flags should default to:

```python
False
```

File output should never happen merely because the pipeline ran.

This avoids surprising the user with files appearing after every planning run.

---

## 16. Error Handling Policy

### 16.1 Base pipeline missing inputs

If:

```text
enable_explicit_bridge_capacity_pipeline = True
```

but required pipeline inputs are missing, retain current strict behavior:

```text
raise ValueError with explicit missing key
```

### 16.2 Reporting child missing parent

If child reporting flag is true but parent object is missing, recommended MVP behavior:

```text
return None for that child
record None in reporting_stack_results
do not raise
```

Example:

```text
issue_candidate_export flag true
but env.explicit_bridge_capacity_issue_candidates missing
    → no export
    → result None
```

### 16.3 Future strict mode

Later, strict mode may raise:

```text
ValueError("issue candidate export enabled but issue candidates are missing")
```

but this is not required for MVP.

---

## 17. Suggested Result Summary

The orchestration helper may attach a dictionary:

```python
env.explicit_bridge_capacity_reporting_stack_results = {
    "capacity_report": report_or_none,
    "capacity_report_export": export_result_or_none,
    "issue_candidates": bundle_or_none,
    "issue_candidate_export": export_result_or_none,
    "issue_candidate_cost_kpi": kpi_bundle_or_none,
    "issue_candidate_cost_kpi_export": kpi_export_result_or_none,
}
```

This is useful for tests and future GUI debug display.

---

## 18. Recommended Minimal Implementation Scope

A future Codex request should implement only:

```text
pysi/reporting/explicit_pipeline_reporting_flags.py
tests/test_explicit_pipeline_reporting_flags.py
```

Optional package export:

```text
pysi/reporting/__init__.py
```

Optional planning-sequence insertion:

```text
defer until after helper is tested
```

This design recommends implementing the helper first as an isolated module.

Only after helper tests pass should planning-sequence insertion be considered.

---

## 19. Future Planning-Sequence Insertion

After the helper exists, the planning sequence can call it after the explicit pipeline has run.

Conceptual insertion:

```python
explicit_result = maybe_run_explicit_bridge_capacity_pipeline_from_env(...)

if explicit_result is not None:
    maybe_run_explicit_pipeline_reporting_stack_from_env(self.env)
```

However, this insertion should be a separate phase and separate Codex request.

Reason:

```text
The helper should first be tested independently.
```

---

## 20. Test Strategy

### 20.1 Flag-off no-op

Create env with no flags.

Verify:

```text
helper returns empty or all-None result
no output directory is created
no unexpected env attributes are attached
```

### 20.2 Report only

Create env with:

```text
explicit_bridge_capacity_pipeline_result
enable_explicit_bridge_capacity_report=True
```

Verify:

```text
capacity report is attached
no files are written
no issue candidates are generated
```

### 20.3 Report export

Create env with report available and:

```text
enable_explicit_bridge_capacity_report_export=True
```

Verify:

```text
capacity report export result is attached
expected files are written
```

### 20.4 Issue candidates

Create env with report available and:

```text
enable_explicit_bridge_capacity_issue_candidates=True
```

Verify:

```text
issue candidate bundle is attached
no file export unless export flag is true
```

### 20.5 Issue candidate export

Create env with issue candidates available and:

```text
enable_explicit_bridge_capacity_issue_candidate_export=True
```

Verify:

```text
issue candidate export result is attached
expected files are written
```

### 20.6 Cost / KPI enrichment

Create env with issue candidates and cost context:

```text
enable_explicit_bridge_capacity_issue_candidate_cost_kpi=True
```

Verify:

```text
KPI bundle is attached
summary includes directional impact fields
```

### 20.7 Cost / KPI export

Create env with KPI bundle and:

```text
enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export=True
```

Verify:

```text
KPI export result is attached
summary.json and assumptions.json are written
```

### 20.8 Dependency no-op

Enable a child flag without parent data.

Example:

```text
enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export=True
```

but no KPI bundle.

Verify:

```text
no exception
no files
result entry is None
```

### 20.9 Output root override

Run with `tmp_path` as output root.

Verify derived directories are correct.

---

## 21. Existing Tests to Run After Implementation

A future implementation should run:

```bat
python -m pytest tests/test_explicit_pipeline_reporting_flags.py
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
```

Optional:

```bat
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

---

## 22. Completion Criteria for This Design

This design is complete when it defines:

```text
[OK] proposed feature flags
[OK] dependency tree
[OK] default false policy
[OK] planning sequence order
[OK] orchestration helper concept
[OK] output directory policy
[OK] Cost / KPI context policy
[OK] attachment rules
[OK] side effect policy
[OK] error handling policy
[OK] testing strategy
[OK] future planning-sequence insertion boundary
```

---

## 23. Relationship to Management Cockpit

The Management Cockpit should not be responsible for triggering all reporting side effects implicitly.

Instead, the cockpit should read from:

```text
env explicit objects
or exported files
```

produced by explicitly enabled flags.

This makes the cockpit a viewer / reviewer rather than a hidden execution engine.

Recommended future cockpit data sources:

```text
env.explicit_bridge_capacity_pipeline_report
env.explicit_bridge_capacity_issue_candidates
env.explicit_bridge_capacity_issue_candidate_kpi_bundle
env.explicit_bridge_capacity_reporting_stack_results
```

---

## 24. Relationship to WOM Knowledge Continuity Layer

The reporting flag stack can later support Knowledge Continuity by making the lifecycle explicit.

Future knowledge continuity flags may include:

```text
enable_explicit_bridge_capacity_knowledge_capture
enable_explicit_bridge_capacity_next_entry_prompt_generation
```

But these should come only after the reporting / issue / Cost-KPI stack is stable.

The current design prepares the controlled evidence pipeline.

It does not persist knowledge records.

---

## 25. Summary

This memo defines the switchboard needed before GUI / Management Cockpit integration.

The current stack is powerful:

```text
execution
    ↓
report
    ↓
report export
    ↓
issue candidates
    ↓
issue export
    ↓
Cost / KPI enrichment
    ↓
Cost / KPI export
```

But power needs switches.

The proposed flags make each layer explicit, controlled, and testable.

Recommended next implementation path:

```text
1. Implement isolated reporting flag helper
2. Test all flag combinations
3. Insert helper into planning sequence in a separate phase
4. Design Management Cockpit KPI view
5. Implement GUI display
```

This keeps WOM moving toward management decision support without turning the cockpit into a haunted control panel.
