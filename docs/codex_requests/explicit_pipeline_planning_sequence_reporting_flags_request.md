# Codex Request: Implement Explicit Pipeline Planning Sequence Reporting Flags MVP

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/explicit_pipeline_planning_sequence_reporting_flags.md
```

Please read this design memo first.

The current explicit pipeline explanation stack is already implemented as standalone pieces:

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

The current completed objects and exporters include:

```text
ExplicitBridgeCapacityPipelineResult
ExplicitPipelineCapacityReport
ExplicitPipelineCapacityReportExportResult
ExplicitPipelineIssueCandidateBundle
ExplicitPipelineIssueCandidateExportResult
ExplicitPipelineIssueCandidateKPIBundle
ExplicitPipelineIssueCandidateKPIExportResult
```

The next step is to implement an **isolated reporting flag helper** that orchestrates the reporting / issue / Cost-KPI stack based on explicit env flags.

This request is only for the isolated helper and tests.

Do not insert it into planning sequence yet.

---

## 2. Main Objective

Add a standalone orchestration helper that reads feature flags from `env` and conditionally runs the existing reporting / issue / Cost-KPI helper functions.

Target helper:

```python
maybe_run_explicit_pipeline_reporting_stack_from_env(...)
```

Target module:

```text
pysi/reporting/explicit_pipeline_reporting_flags.py
```

Target test file:

```text
tests/test_explicit_pipeline_reporting_flags.py
```

The helper should work as a safe switchboard for the following already-implemented layers:

```text
capacity report attachment
capacity report export
issue candidate generation
issue candidate export
Cost / KPI enrichment
Cost / KPI export
```

---

## 3. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan.
3. Do not modify _run_planning_sequence.
4. Do not run the explicit bridge + capacity pipeline inside this helper.
5. Do not execute ReplanCommand.
6. Do not implement automatic replanning.
7. Do not implement OR optimization.
8. Do not implement database persistence.
9. Do not implement Knowledge Continuity persistence.
10. Do not change the existing report / issue / KPI builder logic.
11. Do not change existing exporter behavior.
```

This request is only for:

```text
isolated reporting stack orchestration helper + focused tests
```

Planning-sequence insertion should be a later separate phase.

---

## 4. Files to Add / Modify

Please add:

```text
pysi/reporting/explicit_pipeline_reporting_flags.py
tests/test_explicit_pipeline_reporting_flags.py
```

Optionally update:

```text
pysi/reporting/__init__.py
```

to export the new helper if consistent with package style.

Do not modify:

```text
pysi/gui/*
run_full_plan
planning sequence
pysi/plan/explicit_bridge_capacity_pipeline.py
existing exporter modules
existing issue candidate builder
existing Cost / KPI enrichment module
```

---

## 5. Existing Helpers to Reuse

Please reuse existing helpers.

### 5.1 Capacity report

```python
maybe_build_explicit_pipeline_capacity_report_from_env(...)
```

from:

```text
pysi/reporting/explicit_pipeline_capacity_report.py
```

Expected attachment:

```text
env.explicit_bridge_capacity_pipeline_report
```

### 5.2 Capacity report export

```python
maybe_export_explicit_pipeline_capacity_report_from_env(...)
```

from:

```text
pysi/reporting/explicit_pipeline_capacity_report_exporter.py
```

Expected attachment:

```text
env.explicit_bridge_capacity_pipeline_report_export_result
```

### 5.3 Issue candidates

```python
maybe_build_explicit_pipeline_issue_candidates_from_env(...)
```

from:

```text
pysi/reporting/explicit_pipeline_issue_candidates.py
```

Expected attachment:

```text
env.explicit_bridge_capacity_issue_candidates
```

### 5.4 Issue candidate export

```python
maybe_export_explicit_pipeline_issue_candidates_from_env(...)
```

from:

```text
pysi/reporting/explicit_pipeline_issue_candidate_exporter.py
```

Expected attachment:

```text
env.explicit_bridge_capacity_issue_candidate_export_result
```

### 5.5 Cost / KPI enrichment

```python
maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env(...)
```

from:

```text
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi.py
```

Expected attachment:

```text
env.explicit_bridge_capacity_issue_candidate_kpi_bundle
```

### 5.6 Cost / KPI export

```python
maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env(...)
```

from:

```text
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi_exporter.py
```

Expected attachment:

```text
env.explicit_bridge_capacity_issue_candidate_kpi_export_result
```

---

## 6. Feature Flags to Support

The helper should read these env flags:

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

Important note:

```text
enable_explicit_bridge_capacity_pipeline
```

is intentionally not handled by this helper.

The explicit pipeline itself is already handled elsewhere.

This helper assumes the pipeline result may already exist on env.

---

## 7. Recommended Helper Signature

Please implement:

```python
def maybe_run_explicit_pipeline_reporting_stack_from_env(
    env,
    *,
    output_root: str | Path | None = None,
    cost_kpi_context: dict | None = None,
) -> dict:
    ...
```

Expected return:

```python
{
    "capacity_report": report_or_none,
    "capacity_report_export": export_result_or_none,
    "issue_candidates": bundle_or_none,
    "issue_candidate_export": export_result_or_none,
    "issue_candidate_cost_kpi": kpi_bundle_or_none,
    "issue_candidate_cost_kpi_export": kpi_export_result_or_none,
}
```

The helper should also attach this dictionary to:

```text
env.explicit_bridge_capacity_reporting_stack_results
```

---

## 8. Output Directory Policy

Default output root:

```text
outputs/explicit_pipeline
```

If `output_root` is provided, use it.

Derived directories:

```text
capacity report export:
    output_root

issue candidate export:
    output_root / "issue_candidates"

Cost / KPI export:
    output_root / "issue_candidate_kpi"
```

Use `pathlib.Path`.

Do not create output directories unless the corresponding export helper actually runs.

---

## 9. Cost / KPI Context Policy

For Cost / KPI enrichment, choose context in this order:

```text
1. cost_kpi_context argument
2. env.explicit_bridge_capacity_cost_kpi_context
3. {}
```

The helper should pass this selected context to:

```python
maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env(...)
```

---

## 10. Recommended Execution Order

When flags are enabled, run in this order:

```text
1. capacity report attachment
2. capacity report export
3. issue candidate generation
4. issue candidate export
5. Cost / KPI enrichment
6. Cost / KPI export
```

Pseudo-flow:

```python
results = {
    "capacity_report": None,
    "capacity_report_export": None,
    "issue_candidates": None,
    "issue_candidate_export": None,
    "issue_candidate_cost_kpi": None,
    "issue_candidate_cost_kpi_export": None,
}

if env.enable_explicit_bridge_capacity_report:
    results["capacity_report"] = maybe_build_explicit_pipeline_capacity_report_from_env(env)

if env.enable_explicit_bridge_capacity_report_export:
    results["capacity_report_export"] = maybe_export_explicit_pipeline_capacity_report_from_env(
        env,
        output_dir=output_root,
    )

if env.enable_explicit_bridge_capacity_issue_candidates:
    results["issue_candidates"] = maybe_build_explicit_pipeline_issue_candidates_from_env(env)

if env.enable_explicit_bridge_capacity_issue_candidate_export:
    results["issue_candidate_export"] = maybe_export_explicit_pipeline_issue_candidates_from_env(
        env,
        output_dir=output_root / "issue_candidates",
    )

if env.enable_explicit_bridge_capacity_issue_candidate_cost_kpi:
    results["issue_candidate_cost_kpi"] = maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env(
        env,
        cost_kpi_context=selected_context,
    )

if env.enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export:
    results["issue_candidate_cost_kpi_export"] = maybe_export_explicit_pipeline_issue_candidate_kpi_bundle_from_env(
        env,
        output_dir=output_root / "issue_candidate_kpi",
    )

env.explicit_bridge_capacity_reporting_stack_results = results
return results
```

---

## 11. Dependency Behavior

Use safe no-op behavior for child flags.

If a child flag is true but its parent object is missing:

```text
return None for that layer
do not raise
do not create output files
store None in results
```

Examples:

```text
issue candidate export flag true
but env.explicit_bridge_capacity_issue_candidates missing
    → issue_candidate_export result is None

Cost / KPI export flag true
but env.explicit_bridge_capacity_issue_candidate_kpi_bundle missing
    → issue_candidate_cost_kpi_export result is None
```

Do not add strict validation in this MVP.

Strict validation can be a future option.

---

## 12. Side Effect Policy

In-memory operations:

```text
capacity report attachment
issue candidate generation
Cost / KPI enrichment
```

File-writing operations:

```text
capacity report export
issue candidate export
Cost / KPI export
```

File-writing should happen only when the corresponding export flag is true and the required parent object exists.

---

## 13. Result Attachment Policy

The helper should rely on existing helpers for primary attachments:

```text
env.explicit_bridge_capacity_pipeline_report
env.explicit_bridge_capacity_pipeline_report_export_result
env.explicit_bridge_capacity_issue_candidates
env.explicit_bridge_capacity_issue_candidate_export_result
env.explicit_bridge_capacity_issue_candidate_kpi_bundle
env.explicit_bridge_capacity_issue_candidate_kpi_export_result
```

In addition, the new helper should attach:

```text
env.explicit_bridge_capacity_reporting_stack_results
```

This dictionary is useful for tests and later GUI debug display.

---

## 14. Tests to Add

Please add:

```text
tests/test_explicit_pipeline_reporting_flags.py
```

Use synthetic / minimal env objects and existing builder inputs.

The tests do not need to call the explicit bridge + capacity pipeline unless already convenient.

They can use synthetic objects already accepted by the downstream helpers.

### 14.1 Flag-off no-op

Create env with no flags.

Verify:

```text
helper returns result dict with all values None
env.explicit_bridge_capacity_reporting_stack_results exists
no output files are created
no unexpected report / issue / KPI attrs are attached
```

### 14.2 Report only

Create env with:

```text
env.explicit_bridge_capacity_pipeline_result
enable_explicit_bridge_capacity_report=True
```

Use a minimal / synthetic pipeline result accepted by existing report helper.

Verify:

```text
capacity_report result is not None
env.explicit_bridge_capacity_pipeline_report exists
no export files are written
issue candidates are None
KPI bundle is None
```

If building a synthetic report through existing helper is too cumbersome, use the smallest existing fixture pattern from current tests.

### 14.3 Report export

Create env with existing report and:

```text
enable_explicit_bridge_capacity_report_export=True
```

Verify:

```text
capacity_report_export result is not None
expected export files are written under tmp_path
```

### 14.4 Issue candidates

Create env with existing report and:

```text
enable_explicit_bridge_capacity_issue_candidates=True
```

Verify:

```text
issue_candidates result is not None
env.explicit_bridge_capacity_issue_candidates exists
no issue export files unless export flag is true
```

### 14.5 Issue candidate export

Create env with existing issue candidates and:

```text
enable_explicit_bridge_capacity_issue_candidate_export=True
```

Verify:

```text
issue_candidate_export result is not None
files are written under tmp_path / "issue_candidates"
```

### 14.6 Cost / KPI enrichment

Create env with existing issue candidates and:

```text
enable_explicit_bridge_capacity_issue_candidate_cost_kpi=True
```

Use a minimal cost context.

Verify:

```text
issue_candidate_cost_kpi result is not None
env.explicit_bridge_capacity_issue_candidate_kpi_bundle exists
summary contains Cost / KPI fields
```

### 14.7 Cost / KPI export

Create env with existing KPI bundle and:

```text
enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export=True
```

Verify:

```text
issue_candidate_cost_kpi_export result is not None
files are written under tmp_path / "issue_candidate_kpi"
summary.json exists
assumptions.json exists
```

### 14.8 Dependency no-op

Enable a child export flag without parent data.

Example:

```text
enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export=True
```

but no KPI bundle.

Verify:

```text
no exception
result entry is None
no files are written
```

### 14.9 Output root override

Run helper with:

```python
output_root=tmp_path
```

Verify derived directories:

```text
tmp_path
tmp_path / "issue_candidates"
tmp_path / "issue_candidate_kpi"
```

are used appropriately.

### 14.10 Cost context precedence

Set:

```text
env.explicit_bridge_capacity_cost_kpi_context
```

and also pass an explicit `cost_kpi_context`.

Verify the explicit argument wins.

This can be tested by checking currency or assumption values in the attached KPI bundle.

---

## 15. Suggested Synthetic Test Data

For tests involving issue candidates or KPI bundles, reuse existing dataclasses:

```python
ExplicitPipelineIssueCandidateBundle
ExplicitPipelineIssueCandidateKPIBundle
```

For tests involving capacity report, reuse:

```python
ExplicitPipelineCapacityReport
```

This avoids over-coupling the reporting flags tests to the explicit pipeline engine.

The purpose of this helper test is orchestration, not planning-engine correctness.

---

## 16. Existing Tests to Run

Please run:

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

If optional tests are not run, state so clearly.

---

## 17. Completion Criteria

This request is complete when:

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
[OK] no GUI changes
[OK] no planning-sequence changes
[OK] no ReplanCommand execution
[OK] no Cost / KPI recalculation beyond existing enrichment helper
```

---

## 18. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Main implementation approach
3. Supported flags
4. Dependency / no-op behavior
5. Output directory behavior
6. Cost / KPI context behavior
7. Env attachment behavior
8. Test commands executed
9. Test results
10. Limitations / follow-up
```

Please do not proceed into:

```text
planning-sequence insertion
GUI display
Management Cockpit implementation
OR optimization
database persistence
ReplanCommand execution
Knowledge Continuity persistence
```

This request is only for:

```text
Explicit Pipeline Planning Sequence Reporting Flags MVP
isolated helper + tests
```
