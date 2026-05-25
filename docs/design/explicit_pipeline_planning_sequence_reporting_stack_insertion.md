# Explicit Pipeline Planning Sequence Reporting Stack Insertion Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-24  
**Status:** Design memo  
**Target path:** `docs/design/explicit_pipeline_planning_sequence_reporting_stack_insertion.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/run_full_plan_explicit_pipeline_feature_flag.md`
- `docs/design/run_full_plan_explicit_pipeline_insertion.md`
- `docs/design/run_full_plan_explicit_pipeline_insertion_completion.md`
- `docs/design/explicit_pipeline_reporting_issue_cost_kpi_overview.md`
- `docs/design/explicit_pipeline_planning_sequence_reporting_flags.md`
- `docs/design/explicit_pipeline_planning_sequence_reporting_flags_completion.md`
- `docs/design/explicit_pipeline_capacity_report_attachment.md`
- `docs/design/explicit_pipeline_issue_candidate_cost_kpi_export.md`
- `docs/design/wom_knowledge_continuity_layer.md`

---

## 1. Purpose

This memo defines the design for inserting the already-tested explicit pipeline reporting stack helper into the planning sequence.

The helper already exists as an isolated switchboard:

```python
maybe_run_explicit_pipeline_reporting_stack_from_env(...)
```

from:

```text
pysi/reporting/explicit_pipeline_reporting_flags.py
```

The next step is to call this helper from the planning sequence after the explicit bridge + capacity pipeline has successfully run.

This design defines:

```text
where to insert it
when to call it
which flags control it
what must remain unchanged
how to test it
```

---

## 2. Current Completed State

The current explicit pipeline explanation stack is complete as standalone layers:

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

The helper MVP is complete and tested:

```text
pysi/reporting/explicit_pipeline_reporting_flags.py
tests/test_explicit_pipeline_reporting_flags.py
```

Current helper:

```python
maybe_run_explicit_pipeline_reporting_stack_from_env(...)
```

It supports these flags:

```text
enable_explicit_bridge_capacity_report
enable_explicit_bridge_capacity_report_export
enable_explicit_bridge_capacity_issue_candidates
enable_explicit_bridge_capacity_issue_candidate_export
enable_explicit_bridge_capacity_issue_candidate_cost_kpi
enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export
```

It attaches:

```text
env.explicit_bridge_capacity_reporting_stack_results
```

It does **not** run the explicit pipeline itself.

It assumes that the explicit pipeline result may already exist on `env`.

---

## 3. Design Goal

The design goal is deliberately narrow:

```text
Insert the reporting stack helper into the planning sequence after explicit pipeline execution.
```

The target planning sequence shape is:

```text
outbound demand-side preparation
    ↓
explicit bridge + capacity pipeline
    ↓
capacity report attachment
    ↓
reporting stack helper
    ↓
remaining MOM allocation / downstream planning sequence
```

The insertion should be:

```text
feature-flag safe
side-effect controlled
minimal
testable
non-invasive
```

---

## 4. Non-Goals

This phase must not implement:

```text
new GUI widgets
new buttons
new panels
Management Cockpit display
new Cost / KPI logic
new issue candidate logic
new exporter logic
new optimization logic
ReplanCommand execution
automatic replanning
database persistence
Knowledge Continuity persistence
```

This phase is only:

```text
planning-sequence insertion of an existing helper
```

The cockpit screen should not change yet.

---

## 5. Existing Insertion Point Context

Phase 2b inserted the explicit pipeline call in:

```text
pysi/gui/cockpit_tk.py
```

inside:

```python
WOMCockpit._run_planning_sequence(...)
```

The insertion point was after outbound backward planning and before MOM allocation.

Current conceptual flow:

```text
_run_planning_sequence(...)
    ↓
outbound_backward_leaf_to_MOM(...)
    ↓
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
    ↓
if explicit_result is not None:
    maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
    ↓
MOM allocation
    ↓
downstream planning sequence
```

The new insertion should occur after `explicit_result` is returned and after existing capacity report attachment behavior.

---

## 6. Recommended Exact Insertion Point

Recommended location:

```text
pysi/gui/cockpit_tk.py
```

inside:

```python
WOMCockpit._run_planning_sequence(...)
```

immediately after the existing explicit pipeline execution block:

```python
explicit_result = maybe_run_explicit_bridge_capacity_pipeline_from_env(...)

if explicit_result is not None:
    maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
```

Recommended new structure:

```python
explicit_result = maybe_run_explicit_bridge_capacity_pipeline_from_env(...)

if explicit_result is not None:
    maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
    maybe_run_explicit_pipeline_reporting_stack_from_env(self.env)
```

However, to avoid duplicate capacity report building, the final implementation should consider the current state carefully.

There are two possible approaches.

---

## 7. Approach A: Minimal Direct Insertion

### 7.1 Concept

Keep the existing capacity report attachment call unchanged, then call the reporting stack helper.

```python
if explicit_result is not None:
    maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
    maybe_run_explicit_pipeline_reporting_stack_from_env(self.env)
```

### 7.2 Benefit

This is the smallest code change.

### 7.3 Risk

If:

```text
enable_explicit_bridge_capacity_report=True
```

the reporting stack helper may build the report again.

This is usually harmless, but unnecessary.

### 7.4 Use When

Use this approach if the current capacity report attachment should remain unconditional after explicit pipeline execution.

---

## 8. Approach B: Reporting Stack Owns Report Attachment

### 8.1 Concept

Let the reporting stack helper own report attachment when the report flag is enabled.

Change the explicit pipeline block to:

```python
explicit_result = maybe_run_explicit_bridge_capacity_pipeline_from_env(...)

if explicit_result is not None:
    maybe_run_explicit_pipeline_reporting_stack_from_env(self.env)
```

Then report attachment happens only when:

```text
enable_explicit_bridge_capacity_report=True
```

### 8.2 Benefit

Cleaner flag semantics.

No duplicate report generation.

The switchboard truly controls all reporting layers.

### 8.3 Risk

This changes previous Phase 3b behavior where a report could be attached whenever explicit pipeline result existed.

If existing tests assume unconditional report attachment, they need to be reviewed.

### 8.4 Use When

Use this approach if strict flag-controlled behavior is preferred.

---

## 9. Recommended MVP Choice

Recommended MVP:

```text
Approach A with duplicate-build tolerance.
```

More specifically:

```python
if explicit_result is not None:
    maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
    maybe_run_explicit_pipeline_reporting_stack_from_env(self.env)
```

If duplicate rebuilding is a concern, a later refinement can add:

```text
skip if env.explicit_bridge_capacity_pipeline_report already exists
```

to the reporting helper.

The immediate objective is safe insertion, not refactoring earlier behavior.

---

## 10. Feature Flag Semantics

The insertion itself should be gated by:

```text
explicit_result is not None
```

The helper internally reads these flags:

```text
enable_explicit_bridge_capacity_report
enable_explicit_bridge_capacity_report_export
enable_explicit_bridge_capacity_issue_candidates
enable_explicit_bridge_capacity_issue_candidate_export
enable_explicit_bridge_capacity_issue_candidate_cost_kpi
enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export
```

All flags default to false.

Therefore, when no reporting flags are set:

```text
the helper returns a result dict with all None values
no files are written
no issue candidates are generated
no Cost / KPI bundle is generated
```

The planning sequence behavior remains effectively unchanged.

---

## 11. Side Effect Control

Only export flags cause file output.

```text
enable_explicit_bridge_capacity_report_export
enable_explicit_bridge_capacity_issue_candidate_export
enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export
```

All should default to:

```python
False
```

Therefore, simply inserting the helper should not cause file creation unless export flags are explicitly enabled.

This is critical for GUI safety.

No one wants a planning run to become a confetti cannon of CSV files.

---

## 12. Output Directory Policy

The inserted helper may be called without explicit `output_root`.

Default:

```text
outputs/explicit_pipeline
```

Later, GUI or scenario runner may provide:

```text
env.explicit_bridge_capacity_reporting_output_root
```

Recommended MVP insertion:

```python
maybe_run_explicit_pipeline_reporting_stack_from_env(
    self.env,
    output_root=getattr(self.env, "explicit_bridge_capacity_reporting_output_root", None),
    cost_kpi_context=getattr(self.env, "explicit_bridge_capacity_cost_kpi_context", None),
)
```

This keeps future configuration possible without adding GUI controls now.

---

## 13. Cost / KPI Context Policy

The helper already supports context precedence:

```text
1. explicit cost_kpi_context argument
2. env.explicit_bridge_capacity_cost_kpi_context
3. {}
```

When inserted into planning sequence, pass:

```python
cost_kpi_context=getattr(self.env, "explicit_bridge_capacity_cost_kpi_context", None)
```

This allows scenario setup code to attach assumptions to env before planning.

No GUI change is required.

---

## 14. Recommended Code Shape

In:

```text
pysi/gui/cockpit_tk.py
```

inside `_run_planning_sequence(...)`, add import:

```python
from pysi.reporting.explicit_pipeline_reporting_flags import (
    maybe_run_explicit_pipeline_reporting_stack_from_env,
)
```

Recommended block:

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

If current code already calls:

```python
maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
```

then only add the reporting stack helper call and import.

---

## 15. What Must Not Change in `cockpit_tk.py`

The diff in `pysi/gui/cockpit_tk.py` should be minimal.

Allowed:

```text
import maybe_run_explicit_pipeline_reporting_stack_from_env
call helper after explicit_result is not None
pass output_root and cost_kpi_context from env attributes
```

Not allowed:

```text
new GUI widgets
new buttons
new labels
new popups
new layout changes
new event handlers
new report display panels
new file dialogs
new management cockpit screen behavior
```

This is still not the GUI display phase.

It is only planning-sequence wiring.

---

## 16. Expected Env Attachments After Insertion

Depending on flags, the following may be attached:

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

With all reporting flags false:

```text
env.explicit_bridge_capacity_reporting_stack_results
```

may still be attached with all `None` values if explicit pipeline runs.

This is acceptable.

---

## 17. Error Handling

The existing base pipeline behavior remains unchanged.

If:

```text
enable_explicit_bridge_capacity_pipeline=True
```

but required explicit pipeline inputs are missing:

```text
maybe_run_explicit_bridge_capacity_pipeline_from_env(...)
```

may raise `ValueError`.

This should not be changed.

The reporting stack helper uses safe no-op behavior for missing parent objects.

Therefore:

```text
reporting child flags should not raise merely because parent object is missing
```

This keeps GUI planning runs safe.

---

## 18. Test Strategy

Add a focused test file:

```text
tests/test_explicit_pipeline_reporting_stack_insertion.py
```

The tests should validate the planning-sequence insertion behavior without relying on full GUI display.

There are two possible strategies.

---

## 19. Test Strategy A: Adapter-Level Test

If direct `_run_planning_sequence` tests are difficult, create an adapter-style test that mirrors the insertion pattern.

Example helper in test:

```python
def _simulate_insertion(env, explicit_result):
    if explicit_result is not None:
        maybe_build_explicit_pipeline_capacity_report_from_env(env)
        return maybe_run_explicit_pipeline_reporting_stack_from_env(env)
    return None
```

This is less ideal but safe and focused.

---

## 20. Test Strategy B: Direct Planning Sequence Test

If existing tests can instantiate the cockpit app or use current planning sequence fixtures, test:

```text
flag off: explicit pipeline runs, no reporting side effects except safe stack result
flag on: reporting stack helper runs and attaches expected outputs
```

This may be heavier due to Tk / GUI dependencies.

For MVP, prefer an isolated / adapter-style insertion test if GUI instantiation is brittle.

---

## 21. Recommended Test Cases

### 21.1 Flag-off behavior

Set:

```text
enable_explicit_bridge_capacity_pipeline=True
```

but all reporting flags false.

Verify:

```text
planning sequence does not fail
no export files are written
reporting_stack_results is either absent or all None depending on insertion design
```

If explicit result is not available in the test, use adapter style.

### 21.2 Report flag enabled

Set:

```text
enable_explicit_bridge_capacity_report=True
```

and provide minimal explicit pipeline result / report-compatible fixture.

Verify:

```text
env.explicit_bridge_capacity_pipeline_report exists
results["capacity_report"] is not None or already attached report is present
```

### 21.3 Issue candidate flag enabled

Set:

```text
enable_explicit_bridge_capacity_issue_candidates=True
```

with report available.

Verify:

```text
env.explicit_bridge_capacity_issue_candidates exists
```

### 21.4 Cost / KPI flag enabled

Set:

```text
enable_explicit_bridge_capacity_issue_candidate_cost_kpi=True
```

with issue candidates available and cost context.

Verify:

```text
env.explicit_bridge_capacity_issue_candidate_kpi_bundle exists
```

### 21.5 Export flags enabled with tmp output root

Set export flags and:

```text
env.explicit_bridge_capacity_reporting_output_root = tmp_path
```

Verify:

```text
tmp_path / "summary.json"
tmp_path / "issue_candidates" / "summary.json"
tmp_path / "issue_candidate_kpi" / "summary.json"
```

exist only for enabled exports with parent data.

### 21.6 No explicit result behavior

If explicit result is `None`, helper should not be called from insertion block.

Verify:

```text
no reporting_stack_results attached
```

or whatever behavior the implementation chooses.

---

## 22. Existing Tests to Run

After implementation, run:

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

---

## 23. Recommended Codex Implementation Scope

Future Codex request should modify:

```text
pysi/gui/cockpit_tk.py
tests/test_explicit_pipeline_reporting_stack_insertion.py
```

Possibly no other files.

Do not modify:

```text
pysi/reporting/explicit_pipeline_reporting_flags.py
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi_exporter.py
pysi/reporting/explicit_pipeline_issue_candidate_cost_kpi.py
pysi/reporting/explicit_pipeline_issue_candidate_exporter.py
pysi/reporting/explicit_pipeline_issue_candidates.py
pysi/reporting/explicit_pipeline_capacity_report_exporter.py
```

unless a small import path fix is genuinely necessary.

---

## 24. Completion Criteria for Implementation

The future implementation is complete when:

```text
[OK] planning sequence imports maybe_run_explicit_pipeline_reporting_stack_from_env
[OK] helper is called after explicit_result is not None
[OK] output_root can be read from env.explicit_bridge_capacity_reporting_output_root
[OK] cost context can be read from env.explicit_bridge_capacity_cost_kpi_context
[OK] reporting flags remain default false
[OK] no GUI widgets/layout/buttons are changed
[OK] no run_full_plan semantics are changed except reporting side-effect hook
[OK] no ReplanCommand execution is added
[OK] no Cost / KPI logic is changed
[OK] focused insertion tests pass
[OK] broader regression tests pass
```

---

## 25. Relationship to Management Cockpit

This phase is still not Management Cockpit display.

However, it prepares the cockpit data sources.

After insertion, a future cockpit view can read:

```text
env.explicit_bridge_capacity_reporting_stack_results
env.explicit_bridge_capacity_pipeline_report
env.explicit_bridge_capacity_issue_candidates
env.explicit_bridge_capacity_issue_candidate_kpi_bundle
```

The cockpit should display the results, not secretly generate them.

That is why this feature flag insertion phase is important.

---

## 26. Relationship to Knowledge Continuity

This phase does not persist knowledge.

However, once the reporting stack runs inside the planning sequence, the resulting objects can later serve as inputs to:

```text
open issues
facts and findings
decision log candidates
next-entry prompts
```

through a future explicit Knowledge Continuity capture flag.

This should not be added in this phase.

---

## 27. Summary

This memo defines the next safe wiring step.

The current state:

```text
reporting stack helper exists and is tested
```

The next implementation:

```text
call reporting stack helper after explicit pipeline result is produced
```

The key safety rule:

```text
all reporting / export / Cost-KPI layers remain controlled by explicit flags
```

This turns the isolated switchboard into a planning-sequence-connected switchboard, while keeping every switch default OFF.

In short:

```text
The switchboard is ready.
Now connect it to the cockpit power line.
Do not turn all switches on by default.
```
