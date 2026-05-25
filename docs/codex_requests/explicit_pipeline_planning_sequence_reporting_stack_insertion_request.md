# Codex Request: Insert Explicit Pipeline Reporting Stack into Planning Sequence

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/explicit_pipeline_planning_sequence_reporting_stack_insertion.md
```

Please read this design memo first.

The explicit pipeline explanation stack has already been completed as isolated / standalone layers:

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
    ↓
reporting flag switchboard helper
```

The reporting flag switchboard helper has already been implemented and tested:

```text
pysi/reporting/explicit_pipeline_reporting_flags.py
tests/test_explicit_pipeline_reporting_flags.py
```

The helper is:

```python
maybe_run_explicit_pipeline_reporting_stack_from_env(...)
```

This request is to insert that helper into the existing planning sequence, immediately after the explicit bridge + capacity pipeline has successfully run.

This request is **not** for GUI display.

This request is **not** for Management Cockpit UI.

This request is only for:

```text
planning-sequence reporting-stack insertion
```

---

## 2. Main Objective

Modify the existing planning sequence so that, after:

```python
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
```

returns a non-None `explicit_result`, WOM calls:

```python
maybe_run_explicit_pipeline_reporting_stack_from_env(...)
```

The intended conceptual flow is:

```text
_run_planning_sequence(...)
    ↓
outbound demand-side preparation
    ↓
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
    ↓
if explicit_result is not None:
        existing capacity report attachment
        maybe_run_explicit_pipeline_reporting_stack_from_env(...)
    ↓
MOM allocation / downstream planning sequence
```

The inserted helper should remain fully controlled by explicit feature flags.

All reporting / export / Cost-KPI flags default to false.

---

## 3. Important Constraints

Please follow these constraints:

```text
1. Do not add GUI widgets.
2. Do not add buttons.
3. Do not change layout.
4. Do not add popups.
5. Do not add new GUI event handlers.
6. Do not implement Management Cockpit display.
7. Do not change Cost / KPI enrichment logic.
8. Do not change exporter logic.
9. Do not change issue candidate builder logic.
10. Do not execute ReplanCommand.
11. Do not implement automatic replanning.
12. Do not implement OR optimization.
13. Do not implement database persistence.
14. Do not implement Knowledge Continuity persistence.
```

This request should make only the minimal planning-sequence wiring change plus focused tests.

---

## 4. Files to Modify / Add

Please modify:

```text
pysi/gui/cockpit_tk.py
```

Please add:

```text
tests/test_explicit_pipeline_reporting_stack_insertion.py
```

Avoid modifying other files unless a tiny import-path fix is genuinely necessary.

Do not modify:

```text
pysi/reporting/explicit_pipeline_reporting_flags.py
pysi/reporting/explicit_pipeline_capacity_report.py
pysi/reporting/explicit_pipeline_capacity_report_exporter.py
pysi/reporting/explicit_pipeline_issue_candidates.py
pysi/reporting/explicit_pipeline_issue_candidate_exporter.py
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi.py
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi_exporter.py
pysi/plan/explicit_bridge_capacity_pipeline.py
```

---

## 5. Existing Components to Reuse

### 5.1 Existing explicit pipeline helper

Already used in planning sequence:

```python
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
```

from:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
```

### 5.2 Existing capacity report helper

Already used in the current explicit-result block:

```python
maybe_build_explicit_pipeline_capacity_report_from_env(...)
```

from:

```text
pysi/reporting/explicit_pipeline_capacity_report.py
```

### 5.3 Existing reporting stack helper

Newly added and tested in prior phase:

```python
maybe_run_explicit_pipeline_reporting_stack_from_env(...)
```

from:

```text
pysi/reporting/explicit_pipeline_reporting_flags.py
```

This helper reads flags and controls:

```text
capacity report
capacity report export
issue candidates
issue candidate export
Cost / KPI enrichment
Cost / KPI export
```

---

## 6. Recommended Code Change

In:

```text
pysi/gui/cockpit_tk.py
```

inside:

```python
WOMCockpit._run_planning_sequence(...)
```

add import:

```python
from pysi.reporting.explicit_pipeline_reporting_flags import (
    maybe_run_explicit_pipeline_reporting_stack_from_env,
)
```

Then, in the existing explicit pipeline block, after:

```python
explicit_result = maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
```

and inside:

```python
if explicit_result is not None:
```

call:

```python
maybe_run_explicit_pipeline_reporting_stack_from_env(
    self.env,
    output_root=getattr(self.env, "explicit_bridge_capacity_reporting_output_root", None),
    cost_kpi_context=getattr(self.env, "explicit_bridge_capacity_cost_kpi_context", None),
)
```

Recommended shape:

```python
explicit_result = maybe_run_explicit_bridge_capacity_pipeline_from_env(
    env=self.env,
    outbound_root=out_root,
    inbound_root=in_root,
    product=prod,
    mom_policy=MOM_POLICY_IPHONE,
    backward_weekly_capability=getattr(self.env, "explicit_pipeline_backward_weekly_capability", None),
    forward_weekly_capacity=getattr(self.env, "explicit_pipeline_forward_weekly_capacity", None),
)

if explicit_result is not None:
    maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
    maybe_run_explicit_pipeline_reporting_stack_from_env(
        self.env,
        output_root=getattr(self.env, "explicit_bridge_capacity_reporting_output_root", None),
        cost_kpi_context=getattr(self.env, "explicit_bridge_capacity_cost_kpi_context", None),
    )
```

If the existing code already contains:

```python
maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
```

then keep it unchanged and add only the reporting stack helper call.

---

## 7. Recommended MVP Approach

Use the minimal direct insertion approach.

That means:

```text
keep existing capacity report attachment behavior
add reporting stack helper call after it
```

Do not refactor earlier behavior in this request.

Do not try to make the reporting stack helper own all report attachment semantics yet.

If duplicate capacity report building becomes an issue later, handle it in a future refinement.

This request should prioritize:

```text
small diff
safe wiring
default-off behavior
focused tests
```

---

## 8. Feature Flag Semantics

The insertion should be gated by:

```text
explicit_result is not None
```

The reporting stack helper internally reads:

```text
enable_explicit_bridge_capacity_report
enable_explicit_bridge_capacity_report_export
enable_explicit_bridge_capacity_issue_candidates
enable_explicit_bridge_capacity_issue_candidate_export
enable_explicit_bridge_capacity_issue_candidate_cost_kpi
enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export
```

All these flags default to false.

Therefore, if no reporting flags are enabled:

```text
no exports are written
no issue candidates are generated
no Cost / KPI bundle is generated
no Cost / KPI export is written
```

The planning sequence should remain effectively unchanged, except that:

```text
env.explicit_bridge_capacity_reporting_stack_results
```

may be attached with all values None after explicit pipeline execution.

That is acceptable.

---

## 9. Output Root Policy

The call should pass:

```python
output_root=getattr(self.env, "explicit_bridge_capacity_reporting_output_root", None)
```

If this env attribute is absent or None, the helper uses its default:

```text
outputs/explicit_pipeline
```

Derived output directories remain:

```text
capacity report export:
    output_root

issue candidate export:
    output_root / "issue_candidates"

Cost / KPI export:
    output_root / "issue_candidate_kpi"
```

No export files should be written unless corresponding export flags are enabled.

---

## 10. Cost / KPI Context Policy

The call should pass:

```python
cost_kpi_context=getattr(self.env, "explicit_bridge_capacity_cost_kpi_context", None)
```

This allows scenario code or tests to set Cost / KPI assumptions on `env` before running the planning sequence.

No GUI controls should be added for this in this request.

---

## 11. Expected Env Attachments

Depending on enabled flags, the following env attributes may be attached:

```text
env.explicit_bridge_capacity_pipeline_result
env.explicit_bridge_capacity_pipeline_report
env.explicit_bridge_capacity_pipeline_report_export_result
env.explicit_bridge_capacity_issue_candidates
env.explicit_bridge_capacity_issue_candidate_export_result
env.explicit_bridge_capacity_issue_candidate_kpi_bundle
env.explicit_bridge_capacity_issue_candidate_kpi_export_result
env.explicit_bridge_capacity_reporting_stack_results
```

With all reporting flags false, the important expected behavior is:

```text
env.explicit_bridge_capacity_reporting_stack_results exists only if explicit_result is not None
all entries are None
no files are written
```

---

## 12. Error Handling

Do not change existing base-pipeline error behavior.

If:

```text
enable_explicit_bridge_capacity_pipeline=True
```

but required explicit pipeline inputs are missing, existing behavior may raise:

```text
ValueError
```

This should remain unchanged.

The reporting stack helper already has safe no-op behavior for child flags when parent objects are missing.

Do not add strict dependency validation in this request.

---

## 13. What Must Not Change in `cockpit_tk.py`

The diff in `pysi/gui/cockpit_tk.py` should be minimal.

Allowed changes:

```text
import maybe_run_explicit_pipeline_reporting_stack_from_env
call helper after explicit_result is not None
pass output_root from env
pass cost_kpi_context from env
```

Disallowed changes:

```text
new GUI widgets
new GUI buttons
new frame layout changes
new labels
new popups
new message boxes
new file dialogs
new Management Cockpit display logic
new user-facing report panels
new planning semantics unrelated to reporting stack insertion
```

This is only a wiring phase.

---

## 14. Test Strategy

Please add:

```text
tests/test_explicit_pipeline_reporting_stack_insertion.py
```

Preferred approach:

```text
adapter-level insertion test
```

This avoids brittle Tk / GUI instantiation.

The test can mirror the exact insertion pattern:

```python
def _simulate_reporting_stack_insertion(env, explicit_result):
    if explicit_result is not None:
        maybe_build_explicit_pipeline_capacity_report_from_env(env)
        return maybe_run_explicit_pipeline_reporting_stack_from_env(
            env,
            output_root=getattr(env, "explicit_bridge_capacity_reporting_output_root", None),
            cost_kpi_context=getattr(env, "explicit_bridge_capacity_cost_kpi_context", None),
        )
    return None
```

The purpose is to verify insertion semantics, not GUI behavior.

---

## 15. Tests to Add

### 15.1 No explicit result

If `explicit_result is None`, verify:

```text
helper is not called
return is None
env.explicit_bridge_capacity_reporting_stack_results is not attached
```

### 15.2 Explicit result with all reporting flags off

Provide minimal env with explicit pipeline result and no reporting flags.

Verify:

```text
reporting stack results exist
all result entries are None
no files are written
```

### 15.3 Report flag enabled

Enable:

```text
enable_explicit_bridge_capacity_report=True
```

Verify:

```text
env.explicit_bridge_capacity_pipeline_report exists
results["capacity_report"] is not None
```

### 15.4 Issue candidates enabled

Enable:

```text
enable_explicit_bridge_capacity_issue_candidates=True
```

and provide / create report through the adapter.

Verify:

```text
env.explicit_bridge_capacity_issue_candidates exists
results["issue_candidates"] is not None
```

### 15.5 Cost / KPI enabled

Enable:

```text
enable_explicit_bridge_capacity_issue_candidate_cost_kpi=True
```

and provide Cost / KPI context through:

```text
env.explicit_bridge_capacity_cost_kpi_context
```

Verify:

```text
env.explicit_bridge_capacity_issue_candidate_kpi_bundle exists
results["issue_candidate_cost_kpi"] is not None
```

### 15.6 Export flags and output root

Set:

```text
env.explicit_bridge_capacity_reporting_output_root = tmp_path
```

Enable export flags with required parent data.

Verify expected files are written under:

```text
tmp_path
tmp_path / "issue_candidates"
tmp_path / "issue_candidate_kpi"
```

### 15.7 Reporting helper call path

The tests should prove the same env attributes used by the planning-sequence insertion are passed correctly:

```text
explicit_bridge_capacity_reporting_output_root
explicit_bridge_capacity_cost_kpi_context
```

---

## 16. Existing Tests to Run

Please run:

```bat
python -m pytest tests/test_explicit_pipeline_reporting_stack_insertion.py
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
[OK] pysi/gui/cockpit_tk.py imports maybe_run_explicit_pipeline_reporting_stack_from_env
[OK] planning sequence calls the helper after explicit_result is not None
[OK] helper call passes output_root from env.explicit_bridge_capacity_reporting_output_root
[OK] helper call passes cost_kpi_context from env.explicit_bridge_capacity_cost_kpi_context
[OK] all reporting flags remain default false
[OK] no GUI widgets/buttons/layout are changed
[OK] no Management Cockpit display is added
[OK] no Cost / KPI logic is changed
[OK] no exporter logic is changed
[OK] no ReplanCommand execution is added
[OK] focused insertion tests pass
[OK] broader regression tests pass
```

---

## 18. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Exact insertion point
3. Whether GUI display was changed
4. Feature flag behavior
5. Output root behavior
6. Cost / KPI context behavior
7. Env attachment behavior
8. Test commands executed
9. Test results
10. Limitations / follow-up
```

Please do not proceed into:

```text
Management Cockpit GUI
GUI display panels
new buttons
new widgets
OR optimization
database persistence
ReplanCommand execution
Knowledge Continuity persistence
```

This request is only for:

```text
Explicit Pipeline Planning Sequence Reporting Stack Insertion MVP
```
