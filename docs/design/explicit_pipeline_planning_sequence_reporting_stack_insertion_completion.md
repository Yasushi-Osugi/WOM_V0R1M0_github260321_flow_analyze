# Explicit Pipeline Planning Sequence Reporting Stack Insertion Completion Memo

**Version:** v0r1 completion  
**Date:** 2026-05-24  
**Status:** Completion memo  
**Target path:** `docs/design/explicit_pipeline_planning_sequence_reporting_stack_insertion_completion.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

---

## 1. Purpose

This memo summarizes the completion status of **Explicit Pipeline Planning Sequence Reporting Stack Insertion MVP**.

The purpose of this milestone was to connect the already-tested explicit pipeline reporting stack helper into the planning sequence.

The inserted helper is:

```python
maybe_run_explicit_pipeline_reporting_stack_from_env(...)
```

from:

```text
pysi/reporting/explicit_pipeline_reporting_flags.py
```

The completed wiring is:

```text
explicit bridge + capacity pipeline
    ↓
capacity report attachment
    ↓
reporting stack helper
    ↓
MOM allocation / downstream planning sequence
```

This milestone connects the switchboard to the planning sequence while keeping all reporting / export / Cost-KPI switches default OFF.

---

## 2. Background

Before this milestone, WOM had already completed the following standalone explanation stack:

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

The reporting stack helper was already implemented and tested as an isolated module.

However, it was not yet connected to the actual planning sequence.

This milestone completes that wiring.

---

## 3. Implemented Files

This milestone added or updated:

```text
pysi/gui/cockpit_tk.py
tests/test_explicit_pipeline_reporting_stack_insertion.py
```

The implementation was committed as:

```text
daa96ad Insert explicit pipeline reporting stack into planning sequence
```

---

## 4. Exact Insertion Point

The insertion was made in:

```text
pysi/gui/cockpit_tk.py
```

inside:

```python
WOMCockpit._run_planning_sequence(...)
```

The helper was inserted inside the existing:

```python
if explicit_result is not None:
```

block, directly after:

```python
maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
```

The implemented conceptual block is:

```python
if explicit_result is not None:
    maybe_build_explicit_pipeline_capacity_report_from_env(self.env)
    maybe_run_explicit_pipeline_reporting_stack_from_env(
        self.env,
        output_root=getattr(self.env, "explicit_bridge_capacity_reporting_output_root", None),
        cost_kpi_context=getattr(self.env, "explicit_bridge_capacity_cost_kpi_context", None),
    )
```

This means the reporting stack helper is called only after the explicit bridge + capacity pipeline has produced a non-None result.

---

## 5. Import Added

The following import was added inside the planning sequence method:

```python
from pysi.reporting.explicit_pipeline_reporting_flags import (
    maybe_run_explicit_pipeline_reporting_stack_from_env,
)
```

This was the only new dependency added to `cockpit_tk.py`.

---

## 6. GUI Display Status

No GUI display behavior was changed.

The implementation did not add:

```text
new widgets
new buttons
new labels
new popups
new layout changes
new event handlers
new Management Cockpit panels
new file dialogs
```

The change is strictly planning-sequence wiring.

The cockpit screen remains visually unchanged.

---

## 7. Feature Flag Behavior

The inserted helper reads the reporting / issue / Cost-KPI flags already defined in the previous helper phase:

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

Therefore, with default settings:

```text
no exports are written
no issue candidates are generated
no Cost / KPI bundle is generated
no Cost / KPI export is written
```

The inserted helper may attach:

```text
env.explicit_bridge_capacity_reporting_stack_results
```

with all entries set to `None`, but this is a safe diagnostic attachment.

---

## 8. Output Root Behavior

The helper call passes:

```python
output_root=getattr(self.env, "explicit_bridge_capacity_reporting_output_root", None)
```

This allows scenario code or tests to control where export files are written.

If this env attribute is absent or `None`, the reporting stack helper uses its default output root:

```text
outputs/explicit_pipeline
```

Derived directories remain:

```text
capacity report export:
    output_root

issue candidate export:
    output_root / "issue_candidates"

Cost / KPI export:
    output_root / "issue_candidate_kpi"
```

No export files are written unless the corresponding export flags are explicitly enabled.

---

## 9. Cost / KPI Context Behavior

The helper call passes:

```python
cost_kpi_context=getattr(self.env, "explicit_bridge_capacity_cost_kpi_context", None)
```

This allows Cost / KPI assumptions to be supplied by scenario setup code without adding GUI controls.

The reporting stack helper still applies its normal context precedence:

```text
1. explicit cost_kpi_context argument
2. env.explicit_bridge_capacity_cost_kpi_context
3. {}
```

Because the planning sequence passes the env context explicitly, scenario-level assumptions can be wired through safely.

---

## 10. Env Attachment Behavior

Depending on enabled flags, the planning sequence can now attach the following env objects after explicit pipeline execution:

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

With all reporting flags false, the most important new attachment is:

```text
env.explicit_bridge_capacity_reporting_stack_results
```

and its values should remain `None`.

This is expected and safe.

---

## 11. Test File Added

The focused insertion test file is:

```text
tests/test_explicit_pipeline_reporting_stack_insertion.py
```

The tests use an adapter-level insertion pattern rather than a full GUI instantiation.

This avoids brittle Tk / GUI dependencies while validating the insertion semantics.

The adapter mirrors the planning-sequence logic:

```text
if explicit_result is not None:
    build capacity report
    run reporting stack helper
else:
    return None
```

---

## 12. Test Coverage

The focused insertion tests validate:

```text
1. no explicit result returns None and does not attach reporting stack results
2. explicit result with all reporting flags off creates no exports
3. report flag attaches capacity report
4. issue candidate flag attaches issue candidate bundle
5. Cost / KPI flag uses env cost context
6. export flags write files under output_root
7. output_root and cost context call-path semantics
```

This confirms that the planning-sequence wiring behavior is correct without adding GUI display tests.

---

## 13. Validation

The focused insertion test passed:

```bat
python -m pytest tests/test_explicit_pipeline_reporting_stack_insertion.py
```

Observed result:

```text
7 passed
```

The broader regression set also passed:

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
python -m pytest tests/test_covid_vaccine_with_capacity_push.py
```

Observed results:

```text
tests/test_explicit_pipeline_reporting_flags.py: 10 passed
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

## 14. Completion Criteria

This milestone satisfies the intended completion criteria.

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

## 15. Meaning of This Milestone

Before this milestone:

```text
The reporting stack switchboard existed, but it was not connected to the planning sequence.
```

After this milestone:

```text
The reporting stack switchboard is connected to the planning sequence after explicit pipeline execution.
```

This means the planning sequence can now produce, depending on enabled flags:

```text
capacity report
capacity report export
issue candidates
issue candidate export
Cost / KPI enrichment
Cost / KPI export
```

without adding GUI display or automatic command execution.

---

## 16. Current Pipeline Position

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
planning-sequence reporting insertion    ✅ completed
    ↓
GUI / Management Cockpit display
```

---

## 17. Current Operational Meaning

The explicit pipeline now has a connected explanation path:

```text
explicit bridge + capacity pipeline
    ↓
reporting switchboard
    ↓
report / issue / Cost-KPI layers
```

However, because all reporting flags default to false, the default planning run remains quiet.

To activate specific layers, scenario setup or future GUI controls can explicitly enable flags such as:

```text
enable_explicit_bridge_capacity_report
enable_explicit_bridge_capacity_issue_candidates
enable_explicit_bridge_capacity_issue_candidate_cost_kpi
```

Export flags remain separate and explicit:

```text
enable_explicit_bridge_capacity_report_export
enable_explicit_bridge_capacity_issue_candidate_export
enable_explicit_bridge_capacity_issue_candidate_cost_kpi_export
```

This separation prevents accidental file output.

---

## 18. Known Limitations

This milestone is intentionally limited.

It does not implement:

```text
Management Cockpit GUI
GUI display panels
new buttons
new widgets
strict dependency validation
automatic export activation
database persistence
Knowledge Continuity persistence
automatic replanning
ReplanCommand execution
OR optimization
```

The helper is now connected, but it remains controlled by feature flags.

---

## 19. Future Milestones

### 19.1 Management Cockpit KPI View

A natural next design phase is:

```text
docs/design/explicit_pipeline_management_cockpit_kpi_view.md
```

This should define how the GUI will display:

```text
capacity report summary
issue candidates
Cost / KPI enriched issue candidates
top impact issues
assumptions
export status
```

### 19.2 GUI display implementation

A later Codex request can implement a read-only view that consumes:

```text
env.explicit_bridge_capacity_reporting_stack_results
env.explicit_bridge_capacity_pipeline_report
env.explicit_bridge_capacity_issue_candidates
env.explicit_bridge_capacity_issue_candidate_kpi_bundle
```

The GUI should display what the planning sequence generated.

It should not secretly trigger exports or replan commands.

### 19.3 Strict flag validation

Future batch / CI modes may add:

```text
child flag true + missing parent object → ValueError
```

but this was intentionally not added in this interactive MVP.

### 19.4 Knowledge Continuity integration

Future Knowledge Continuity capture may consume:

```text
high-impact management issues
facts and findings
decision log candidates
next-entry prompts
```

from the reporting stack.

This should remain explicitly controlled by a future knowledge-capture flag.

---

## 20. Summary

The Explicit Pipeline Planning Sequence Reporting Stack Insertion MVP is complete.

The key achievement is:

```text
The already-tested reporting switchboard is now connected to the planning sequence after explicit pipeline execution.
```

The wiring is minimal and safe:

```text
no GUI display changes
no new buttons
no new widgets
no Cost / KPI logic changes
no exporter logic changes
no command execution
```

The system remains safely human-in-the-loop:

```text
all reporting layers are flag-controlled
all export layers are separately flag-controlled
all flags default OFF
ReplanCommand remains candidate_only
management decisions are not automated
```

In short:

```text
The switchboard is now connected to the cockpit power line.
The switches are still OFF by default.
The cockpit has not yet grown new lights or meters.
```
