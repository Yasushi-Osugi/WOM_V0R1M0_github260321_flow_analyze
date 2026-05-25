# Codex Request: Implement Explicit Bridge + Capacity Pipeline Runner MVP

## 1. Background

We are working on branch:

```text
feature/with-capacity-psi-engine-v0r2
```

The following design memo has already been added:

```text
docs/design/run_full_plan_explicit_bridge_capacity_pipeline.md
```

Please read this design memo first.

The current explicit E2E bridge + capacity flow has already been implemented and tested as a smoke wrapper:

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

Existing smoke wrapper:

```text
pysi/plan/bridges/e2e_bridge_forward_capacity_smoke.py
```

Existing test:

```text
tests/test_e2e_bridge_forward_capacity_smoke.py
```

This request is to create a more canonical explicit pipeline runner, still independent from `run_full_plan` and GUI.

---

## 2. Main Objective

Implement an additive explicit pipeline runner module:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
```

with a focused test:

```text
tests/test_explicit_bridge_capacity_pipeline.py
```

The runner should provide a stable, production-oriented interface over the already validated smoke flow.

This is Phase 1 of the staged integration plan:

```text
isolated utilities
    ↓
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

This task is only for:

```text
explicit pipeline runner
```

Do not modify `run_full_plan` yet.

---

## 3. Existing Components to Reuse

Please reuse existing modules and do not duplicate their logic.

```text
pysi/plan/bridges/outbound_to_inbound_demand_bridge.py
pysi/plan/bridges/outbound_to_inbound_mom_allocation.py
pysi/plan/capacity_aware_inbound_backward.py
pysi/plan/bridges/demand_to_supply_execution_bridge.py
pysi/plan/weekly_forward_push_with_capacity.py
pysi/plan/bridges/e2e_bridge_forward_capacity_smoke.py
```

Relevant existing functions:

```text
bridge_outbound_to_inbound_demand(...)
allocate_bridged_demand_to_moms(...)
capacity_aware_inbound_backward_planning(...)
bridge_demand_to_supply_execution(...)
weekly_forward_push_with_capacity(...)
run_e2e_bridge_forward_capacity_smoke(...)
```

MVP recommendation:

```text
Implement run_explicit_bridge_capacity_pipeline(...) by wrapping run_e2e_bridge_forward_capacity_smoke(...),
then normalize / aggregate the result into a pipeline-specific result object.
```

This keeps the first runner small and safe.

---

## 4. Important Constraints

Please follow these constraints:

```text
1. Do not modify GUI.
2. Do not modify run_full_plan.
3. Do not modify existing loaders.
4. Do not implement costing / KPI.
5. Do not implement Management Issue Generation.
6. Do not implement OR optimization.
7. Do not execute ReplanCommand.
8. Do not rewrite existing bridge utilities.
9. Keep this as an additive runner + focused tests.
```

This request is only for:

```text
Explicit Bridge + Capacity Pipeline Runner MVP
```

---

## 5. Suggested Files

Please add:

```text
pysi/plan/explicit_bridge_capacity_pipeline.py
tests/test_explicit_bridge_capacity_pipeline.py
```

Please update only if useful:

```text
pysi/plan/__init__.py
```

Do not modify:

```text
pysi/gui/*
run_full_plan
existing loaders
costing / KPI modules
Management Issue modules
```

---

## 6. Result Dataclass

Please implement:

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExplicitBridgeCapacityPipelineResult:
    product_name: str = ""

    bridge_a_result: Any | None = None
    mom_allocation_result: Any | None = None
    backward_capacity_result: Any | None = None
    bridge_b_result: Any | None = None
    forward_capacity_result: Any | None = None
    smoke_result: Any | None = None

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

Notes:

```text
smoke_result may hold the raw E2E smoke wrapper result.
forward_capacity_result may be set if accessible from smoke result or future direct composition.
For MVP, it is acceptable if some stage-specific result fields remain None,
as long as the aggregated lot/capacity fields are populated.
```

---

## 7. Main Function

Please implement:

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

Expected sequence:

```text
1. Call run_e2e_bridge_forward_capacity_smoke(...)
2. Convert / aggregate smoke output into ExplicitBridgeCapacityPipelineResult
3. Preserve Lot_ID traceability
4. Preserve PSI list[str] invariant checks
5. Return pipeline-level result
```

---

## 8. Aggregation Requirements

The runner should aggregate the following, where available:

```text
source_lot_ids
missing_lot_ids
blocked_lot_ids
overflow_i_lot_ids
non_list_bucket_errors
non_string_lot_errors
```

It should also expose forward capacity outputs where available:

```text
accepted lots
blocked lots
overflow I lots
capacity_usage
capacity_violations
replan_commands
```

For MVP, if the existing smoke wrapper does not expose all internal stage result objects, do not rewrite all underlying utilities.

Instead:

```text
1. expose what is currently available
2. leave unavailable stage-specific fields as None or empty
3. document this limitation in code comments and tests
```

---

## 9. Lot_ID Preservation

The runner must preserve the core WOM invariant:

```text
Demand Anchored Lots do not disappear.
```

The result should expose:

```text
missing_lot_ids
```

The test must assert:

```python
result.missing_lot_ids == []
```

for the happy path.

---

## 10. PSI Bucket Invariants

The runner should preserve and surface invariant errors:

```text
non_list_bucket_errors
non_string_lot_errors
```

The test must assert:

```python
result.non_list_bucket_errors == []
result.non_string_lot_errors == []
```

---

## 11. Safety Rules

Please enforce these invariants:

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
10. Existing run_full_plan behavior remains unchanged.
11. GUI behavior remains unchanged.
```

---

## 12. Test Fixture

Use the same minimal in-memory fixture style as:

```text
tests/test_e2e_bridge_forward_capacity_smoke.py
```

Reuse the topology pattern:

```text
outbound supply_point

inbound supply_point
    ├── MOM_ASIA
    └── MOM_EURO
```

Use market-key-compatible Lot_IDs:

```text
RT_JP_RICE_2026W10_0001
RT_JP_RICE_2026W10_0002
RT_JP_RICE_2026W10_0003
RT_DE_RICE_2026W10_0001
```

---

## 13. Required Tests

Please add:

```text
tests/test_explicit_bridge_capacity_pipeline.py
```

### 13.1 Pipeline runner happy path

Verify:

```text
run_explicit_bridge_capacity_pipeline(...) returns ExplicitBridgeCapacityPipelineResult
```

and that the result shows:

```text
missing_lot_ids == []
non_list_bucket_errors == []
non_string_lot_errors == []
```

### 13.2 Forward blocked lots are surfaced

Use a forward capacity scenario that blocks at least one P or S lot.

Verify:

```text
blocked_lot_ids is not empty
```

or, if the current smoke result has separate P/S counters:

```text
forward_blocked_p_count > 0 or forward_blocked_s_count > 0
```

### 13.3 Overflow I is surfaced

Use a forward capacity scenario that creates soft I overflow.

Verify:

```text
overflow_i_lot_ids is not empty
```

if already exposed by the smoke wrapper.

If not currently exposed, document limitation and verify the wrapper does not lose invariant data.

### 13.4 No run_full_plan / GUI change

This is a structural requirement.

The test should not import or call GUI.

The test should not call run_full_plan.

---

## 14. Existing Tests to Run

Please run:

```bat
python -m pytest tests/test_explicit_bridge_capacity_pipeline.py
python -m pytest tests/test_e2e_bridge_forward_capacity_smoke.py
python -m pytest tests/test_weekly_forward_push_with_capacity.py
python -m pytest tests/test_e2e_demand_to_supply_bridge_flow_smoke.py
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

## 15. Completion Criteria

This request is complete when:

```text
[OK] pysi/plan/explicit_bridge_capacity_pipeline.py exists
[OK] ExplicitBridgeCapacityPipelineResult exists
[OK] run_explicit_bridge_capacity_pipeline(...) exists
[OK] runner composes existing E2E bridge + forward capacity smoke
[OK] missing_lot_ids are surfaced
[OK] blocked_lot_ids are surfaced where available
[OK] overflow_i_lot_ids are surfaced where available
[OK] non_list_bucket_errors are surfaced
[OK] non_string_lot_errors are surfaced
[OK] focused tests pass
[OK] no run_full_plan changes
[OK] no GUI changes
[OK] no loader changes
```

---

## 16. Expected Response from Codex

After implementation, please summarize:

```text
1. Files changed
2. Whether run_full_plan was untouched
3. Whether GUI was untouched
4. Main implementation approach
5. How the existing smoke wrapper was reused
6. How Lot_ID preservation is surfaced
7. How blocked / overflow lots are surfaced
8. Test commands executed
9. Test results
10. Limitations / follow-up
```

Please do not proceed into:

```text
run_full_plan integration
GUI integration
capacity usage reporting UI
Management Issue Generation
costing / KPI integration
OR optimization
database persistence
```

This request is only for:

```text
Explicit Bridge + Capacity Pipeline Runner MVP
```
