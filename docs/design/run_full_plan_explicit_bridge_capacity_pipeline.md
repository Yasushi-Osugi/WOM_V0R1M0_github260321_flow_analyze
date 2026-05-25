# run_full_plan Explicit Bridge + Capacity Pipeline Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-22  
**Status:** Design memo  
**Target path:** `docs/design/run_full_plan_explicit_bridge_capacity_pipeline.md`  
**Branch:** `feature/with-capacity-psi-engine-v0r2`

**Related design documents:**

- `docs/design/e2e_demand_to_supply_bridge_flow_completion_overview.md`
- `docs/design/e2e_demand_to_supply_bridge_flow_smoke.md`
- `docs/design/e2e_demand_to_supply_bridge_flow_smoke_completion.md`
- `docs/design/e2e_bridge_forward_capacity_smoke.md`
- `docs/design/e2e_bridge_forward_capacity_smoke_completion.md`
- `docs/design/wom_outbound_to_inbound_demand_bridge.md`
- `docs/design/outbound_to_inbound_bridge_to_mom_allocation.md`
- `docs/design/capacity_aware_inbound_backward_planning_tobe.md`
- `docs/design/demand_to_supply_execution_bridge_completion.md`
- `docs/design/weekly_forward_push_with_capacity_psi_engine.md`
- `docs/design/weekly_forward_push_with_capacity_psi_engine_completion.md`

---

## 1. Purpose

This memo defines how the explicit bridge + capacity pipeline should eventually be integrated into `run_full_plan`.

The completed explicit pipeline is:

```text
Bridge A
    ↓
MOM allocation
    ↓
TOBE capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
Weekly Forward PUSH with Capacity
```

The purpose of this design is not to immediately modify GUI behavior.

The purpose is to define a safe integration path from the current isolated smoke wrappers into a controlled full-plan execution flow.

---

## 2. Current Completed State

The following MVP components are already implemented and tested independently.

### 2.1 Bridge A

```text
outbound supply_point.psi4demand[w][P]
    ↓
inbound supply_point.psi4demand[w][S]
```

Implemented by:

```text
pysi/plan/bridges/outbound_to_inbound_demand_bridge.py
```

### 2.2 MOM allocation

```text
inbound supply_point.psi4demand[w][S]
    ↓
MOMxxx.psi4demand[w][S]
```

Implemented by:

```text
pysi/plan/bridges/outbound_to_inbound_mom_allocation.py
```

### 2.3 TOBE capacity-aware inbound backward planning

```text
MOM.psi4demand[w][S]
    ↓
MOM.psi4demand[w][P]
    ↓
effective MOM capacity check
    ↓
early build / backlog
```

Implemented by:

```text
pysi/plan/capacity_aware_inbound_backward.py
```

### 2.4 Bridge B

```text
finalized psi4demand
    ↓
psi4supply
```

Implemented by:

```text
pysi/plan/bridges/demand_to_supply_execution_bridge.py
```

### 2.5 Weekly Forward PUSH with Capacity

```text
psi4supply
    ↓
cap_P / cap_S / cap_I
    ↓
accepted / blocked / overflow lots
```

Implemented by:

```text
pysi/plan/weekly_forward_push_with_capacity.py
```

### 2.6 E2E smoke wrapper

The current controlled smoke wrapper verifies the entire explicit chain:

```text
Bridge A
    ↓
MOM allocation
    ↓
capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
Weekly Forward PUSH with Capacity
```

Implemented by:

```text
pysi/plan/bridges/e2e_bridge_forward_capacity_smoke.py
```

Tested by:

```text
tests/test_e2e_bridge_forward_capacity_smoke.py
```

---

## 3. Integration Principle

The integration principle is:

```text
Do not embed complex bridge/capacity logic directly into GUI or run_full_plan.

First create an explicit pipeline runner.
Then call the runner from run_full_plan behind a feature flag.
Then expose it to GUI.
```

In short:

```text
isolated utilities
    ↓
explicit pipeline runner
    ↓
run_full_plan optional branch
    ↓
GUI execution option
```

This preserves debuggability and prevents `run_full_plan` from becoming an untraceable “all-in-one” function.

---

## 4. Why Not Integrate Directly into GUI First

GUI is not the correct place to create planning correctness.

GUI should call a stable planning pipeline and display its result.

If pipeline logic is introduced directly into GUI:

```text
Lot_ID loss
capacity blocking
backlog
overflow inventory
KPI distortion
```

become harder to debug.

Recommended rule:

```text
GUI should display pipeline results.
GUI should not define pipeline semantics.
```

---

## 5. Proposed Integration Layers

### 5.1 Layer 1: Explicit pipeline runner

Add a new runner that composes existing utilities.

Suggested file:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
```

Suggested main function:

```python
run_explicit_bridge_capacity_pipeline(...)
```

This function should be callable from tests or CLI-like runners without GUI.

### 5.2 Layer 2: run_full_plan optional integration

After the runner is stable, call it from `run_full_plan` only when explicitly enabled.

Suggested feature flag:

```text
enable_explicit_bridge_capacity_pipeline = True
```

or context key:

```python
ctx["enable_explicit_bridge_capacity_pipeline"] = True
```

Default should be:

```text
False
```

until the integration is stable.

### 5.3 Layer 3: GUI option

Only after Layer 1 and Layer 2 are stable, expose a GUI action or option.

Examples:

```text
Run Full Plan
Run Full Plan with Explicit Bridge + Capacity
Run E2E Capacity Pipeline Smoke
```

---

## 6. Proposed Full Pipeline Sequence

The explicit pipeline should run in this conceptual order:

```text
[1] Input preparation / plan seeding
    ↓
[2] Outbound backward planning
    ↓
[3] Bridge A
    ↓
[4] MOM allocation
    ↓
[5] Capacity-aware inbound backward planning
    ↓
[6] Bridge B
    ↓
[7] Weekly Forward PUSH with Capacity
    ↓
[8] Reporting / issue candidate generation
```

This memo focuses on [3] through [7].

---

## 7. Existing vs New Pipeline Mapping

| Stage | Existing / Current Role | New Explicit Pipeline Role | Notes |
|---|---|---|---|
| Input seeding | Rice weekly input / seed utilities | unchanged | Do not refactor now |
| Outbound backward planning | existing backward planning smoke | upstream prerequisite | Should produce outbound supply_point demand/P |
| Bridge A | new utility | explicit | outbound demand/P → inbound demand/S |
| MOM allocation | existing allocation wrapped | explicit | inbound supply_point demand/S → MOM demand/S |
| Inbound backward capacity planning | new TOBE MVP | explicit | MOM demand/S → MOM demand/P with early build/backlog |
| Bridge B | new utility | explicit | finalized demand → supply seed |
| Forward capacity execution | new weekly forward capacity engine | explicit | psi4supply → accepted/blocked/overflow |
| Reporting | currently partial | future | result aggregation first |
| Management issue | not yet | future | candidate generation only first |
| GUI | existing | future | call stable pipeline only |

---

## 8. Proposed Pipeline Result Object

Suggested result object:

```python
@dataclass
class ExplicitBridgeCapacityPipelineResult:
    product_name: str = ""

    bridge_a_result: object | None = None
    mom_allocation_result: object | None = None
    backward_capacity_result: object | None = None
    bridge_b_result: object | None = None
    forward_capacity_result: object | None = None

    source_lot_ids: list[str] = field(default_factory=list)
    missing_lot_ids: list[str] = field(default_factory=list)

    shifted_lot_ids: list[str] = field(default_factory=list)
    backlog_lot_ids: list[str] = field(default_factory=list)
    accepted_lot_ids: list[str] = field(default_factory=list)
    blocked_lot_ids: list[str] = field(default_factory=list)
    overflow_i_lot_ids: list[str] = field(default_factory=list)

    capacity_usage: list[dict] = field(default_factory=list)
    capacity_violations: list[dict] = field(default_factory=list)
    replan_commands: list[dict] = field(default_factory=list)

    non_list_bucket_errors: list[dict] = field(default_factory=list)
    non_string_lot_errors: list[dict] = field(default_factory=list)

    message: str = ""
```

This result should aggregate the output of all explicit stages.

---

## 9. Proposed Pipeline Function

Suggested function:

```python
def run_explicit_bridge_capacity_pipeline(
    *,
    outbound_root,
    inbound_root,
    product: str,
    mom_policy: dict,
    backward_weekly_capability: dict,
    forward_weekly_capacity: dict,
    bridge_a_mode: str = "replace",
    bridge_b_policy: str = "s_p_only",
    bridge_b_mode: str = "replace",
    max_early_build_weeks: int = 13,
    cap_i_mode: str = "soft",
    debug: bool = False,
) -> ExplicitBridgeCapacityPipelineResult:
    ...
```

This can initially delegate to:

```text
run_e2e_bridge_forward_capacity_smoke(...)
```

or call the underlying utilities directly.

MVP recommendation:

```text
First implement pipeline runner by wrapping the existing E2E smoke wrapper.
Then expand only when reporting requirements grow.
```

---

## 10. Result Aggregation Policy

The explicit pipeline should aggregate the following:

```text
Bridge A:
    copied lots
    source / target weeks
    invalid week records

MOM allocation:
    MOM-assigned lots
    allocation counts by MOM

Capacity-aware inbound backward planning:
    shifted lots
    backlog lots
    accepted planned P lots

Bridge B:
    demand-to-supply copied lots
    touched nodes / weeks

Weekly Forward PUSH with Capacity:
    accepted P / blocked P
    accepted S / blocked S
    overflow I
    capacity usage
    capacity violations
    replan command candidates
```

This aggregated result becomes the main interface for later reporting and GUI.

---

## 11. Feature Flag Policy

The integration into `run_full_plan` should be optional.

Suggested context keys:

```python
ctx["enable_explicit_bridge_capacity_pipeline"] = False
ctx["explicit_pipeline_product"] = product_name
ctx["explicit_pipeline_mom_policy"] = mom_policy
ctx["explicit_pipeline_backward_weekly_capability"] = backward_weekly_capability
ctx["explicit_pipeline_forward_weekly_capacity"] = forward_weekly_capacity
```

Default:

```text
enable_explicit_bridge_capacity_pipeline = False
```

Rationale:

```text
Existing run_full_plan behavior must remain unchanged unless the new pipeline is explicitly enabled.
```

---

## 12. Where to Call in run_full_plan

The new pipeline should be called only after:

```text
outbound demand-side plan has produced outbound supply_point.psi4demand[P]
```

and before:

```text
legacy forward execution / reports that depend on psi4supply
```

Conceptual insertion point:

```text
existing planning sequence
    ↓
outbound backward planning complete
    ↓
if enable_explicit_bridge_capacity_pipeline:
    run_explicit_bridge_capacity_pipeline(...)
    attach result to env / ctx
    ↓
continue reporting
```

Exact insertion point must be confirmed by inspecting current `run_full_plan` implementation.

---

## 13. Proposed Env / Context Output

After pipeline execution, attach result to a safe attribute:

```python
env.explicit_bridge_capacity_pipeline_result = result
```

or:

```python
ctx["explicit_bridge_capacity_pipeline_result"] = result
```

Recommendation:

```text
Use ctx for MVP.
Use env only after current env conventions are confirmed.
```

This avoids mutating environment structure prematurely.

---

## 14. Reporting Boundary

At this stage, do not implement full Management Issue generation.

Instead, expose these data:

```text
capacity_usage
capacity_violations
blocked_lot_ids
overflow_i_lot_ids
backlog_lot_ids
shifted_lot_ids
replan_commands
```

This enables a later reporting layer to consume them.

---

## 15. ReplanCommand Boundary

The Weekly Forward PUSH engine already creates replan command candidates.

At this stage:

```text
generate candidates
do not execute candidates
do not automatically rerun planning
```

Reason:

```text
Forward execution should not silently rewrite previous demand-side planning.
```

---

## 16. Cost / KPI Boundary

Cost / KPI integration should not be part of the first run_full_plan integration.

However, the pipeline should expose data that cost/KPI can later use:

```text
accepted lots
blocked lots
overflow inventory lots
shifted lots
backlog lots
capacity usage
capacity violation
```

Future KPI examples:

```text
service level impact
blocked demand quantity
capacity utilization
inventory overflow
opportunity loss
cost of unmet demand
```

---

## 17. GUI Boundary

GUI should be a later step.

First GUI integration should be limited to:

```text
display pipeline result
display capacity usage
display blocked / shifted / backlog counts
```

GUI should not yet provide complex editing of:

```text
mom_policy
weekly_capacity
replan commands
```

Those should remain advanced future functions.

---

## 18. Safety Invariants

The explicit pipeline must preserve:

```text
1. PSI buckets hold Lot_ID lists.
2. Quantity is len(list).
3. Lot attributes remain outside PSI buckets.
4. Demand Anchored Lots do not disappear.
5. Shifted lots remain traceable.
6. Backlog lots preserve Lot_ID identity.
7. Blocked lots preserve Lot_ID identity.
8. Overflow inventory lots preserve Lot_ID identity.
9. No numeric quantities are inserted into PSI buckets.
10. Existing run_full_plan behavior remains unchanged unless feature flag is enabled.
```

---

## 19. Test Strategy

### 19.1 Pipeline runner test

Add:

```text
tests/test_explicit_bridge_capacity_pipeline.py
```

Verify:

```text
run_explicit_bridge_capacity_pipeline(...)
```

can execute the full chain.

### 19.2 run_full_plan feature flag test

Only after runner is stable, add:

```text
tests/test_run_full_plan_explicit_bridge_capacity_pipeline.py
```

Verify:

```text
default flag off:
    existing behavior unchanged

flag on:
    explicit pipeline result is attached to ctx/env
```

### 19.3 Existing tests to protect

Continue running:

```text
tests/test_e2e_bridge_forward_capacity_smoke.py
tests/test_weekly_forward_push_with_capacity.py
tests/test_e2e_demand_to_supply_bridge_flow_smoke.py
tests/test_demand_to_supply_execution_bridge.py
tests/test_capacity_aware_inbound_backward_planning.py
tests/test_japanese_rice_case_smoke.py
tests/test_covid_vaccine_with_capacity_push.py
```

---

## 20. Recommended Implementation Phases

### Phase 1: Explicit pipeline runner

Add:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
tests/test_explicit_bridge_capacity_pipeline.py
```

No `run_full_plan` modification yet.

### Phase 2: Optional run_full_plan hook

Add feature-flagged integration.

No GUI change.

### Phase 3: Reporting data export

Expose:

```text
capacity_usage
capacity_violations
blocked lots
overflow lots
replan candidates
```

### Phase 4: Management issue candidate generation

Generate issue candidates, but do not automate replan.

### Phase 5: GUI display

Expose pipeline result in GUI.

---

## 21. Codex Request Sequence

Recommended Codex Requests should be separated:

```text
1. explicit_bridge_capacity_pipeline_runner_request.md
2. run_full_plan_explicit_pipeline_feature_flag_request.md
3. capacity_usage_violation_reporting_request.md
4. replan_management_issue_candidate_request.md
5. gui_explicit_pipeline_result_display_request.md
```

Do not combine all five into one request.

---

## 22. Completion Criteria for This Design

This design is complete when it clarifies:

```text
[OK] explicit pipeline sequence
[OK] run_full_plan integration principle
[OK] feature flag policy
[OK] result aggregation policy
[OK] reporting boundary
[OK] replan boundary
[OK] cost/KPI boundary
[OK] GUI boundary
[OK] recommended implementation phases
```

---

## 23. Summary

The explicit bridge + capacity pipeline is ready to move toward controlled full-plan integration.

The key sequence is:

```text
Bridge A
    ↓
MOM allocation
    ↓
capacity-aware inbound backward planning
    ↓
Bridge B
    ↓
Weekly Forward PUSH with Capacity
```

The correct next step is not direct GUI integration.

The correct next step is:

```text
explicit pipeline runner
    ↓
feature-flagged run_full_plan integration
    ↓
reporting
    ↓
issue candidates
    ↓
cost/KPI
    ↓
GUI display
```

This staged approach keeps WOM debuggable, testable, and faithful to the Lot_ID-based planning model.
