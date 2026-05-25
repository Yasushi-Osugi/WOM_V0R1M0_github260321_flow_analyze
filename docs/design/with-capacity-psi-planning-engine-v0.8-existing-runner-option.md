# with Capacity PSI Planning Engine v0.8 Design
## Connect Optional Capacity Report Hook to Existing WOM Runner Option

## 1. Purpose

This document defines the v0.8 design of the **with Capacity PSI Planning Engine**.

v0.1 introduced the additive `pysi.capacity` package.

v0.2 verified dummy-node PSI list integration.

v0.3 verified real-WOM-compatible node compatibility.

v0.4 verified small Outbound Tree processing using PreOrder traversal.

v0.5 verified small Inbound Tree processing using PostOrder traversal.

v0.6 introduced an optional capacity report hook:

```python
run_capacity_report_hook()

v0.7 added a manually executable smoke runner:

tools/smoke_capacity_report_hook.py

v0.8 takes the next step:

Connect the optional capacity report hook to an existing WOM sample runner
or pipeline-level option, with the default setting disabled.

The goal is not to replace the existing Forward Planning engine.

The goal is to make capacity reporting available from an existing WOM execution path while preserving current WOM behavior by default.

2. Development Stage

The staged development flow is:

v0.1:
    Build the capacity gate.

v0.2:
    Pass dummy lots through the gate.

v0.3:
    Pass real-WOM-compatible lots through the gate.

v0.4:
    Pass lots through a small Outbound Tree.

v0.5:
    Pass lots through a small Inbound Tree.

v0.6:
    Add optional capacity report hook.

v0.7:
    Add manual smoke runner for the capacity report hook.

v0.8:
    Connect the capacity report hook to an existing runner option.

v0.9:
    Consider GUI / cockpit visibility or pipeline hook refinement.

v0.8 is the first step toward existing WOM runner integration.

3. Core Concept

The core WOM concept remains unchanged:

Weekly WOM with Capacity
= lot_ID list operation under capacity constraints

v0.8 must not convert WOM PSI into numeric PSI calculations.

Capacity reporting should continue to operate on existing psi4demand and psi4supply lot_ID lists.

4. Design Principle

v0.8 follows this principle:

Default behavior must remain unchanged.

Capacity reporting must be disabled by default.

The new option should behave as follows:

enable_capacity_report = False

Only when explicitly enabled:

if enable_capacity_report:
    run_capacity_report_hook(...)

The existing WOM runner should continue to work exactly as before when this option is not enabled.

5. Scope of v0.8
5.1 In Scope

v0.8 should implement:

Identify one existing sample runner or pipeline runner suitable for optional hook connection.
Add a disabled-by-default option such as:
enable_capacity_report=False
CLI argument --enable-capacity-report
function argument enable_capacity_report=False
When enabled, call run_capacity_report_hook() after existing planning has produced PSI results.
Export:
capacity_usage.csv
capacity_violation.csv
Preserve all existing v0.1 through v0.7 tests.
Add a small test or smoke test confirming:
default disabled behavior does not change runner behavior
enabled behavior calls the hook and creates output files
missing capacity master in non-strict mode does not crash
5.2 Out of Scope

v0.8 does not implement:

replacing existing Forward Planning
capacity-constrained execution mode
GUI integration
management cockpit integration
optimizer integration
alternative MOM allocation
alternative lane selection
costing integration
event flow tracing integration
database integration
real business scenario capacity tuning

v0.8 is only an optional runner-level capacity report connection.

6. Candidate Integration Locations

Codex should inspect the repository and identify a safe runner location.

Candidate areas may include:

tools/
pysi/
pysi/runner/
pysi/pipeline/
pysi/reporting/
sample runner scripts

A suitable runner is one that already has access to some or all of:

scenario_id
product_name
weeks
outbound_root
inbound_root
output directory

If no existing runner can safely provide all required inputs, Codex should not force integration into a fragile location.

In that case, v0.8 may create a lightweight wrapper script around the v0.7 smoke runner, but it should document why real runner integration was deferred.

7. Recommended Integration Pattern

Preferred pattern:

def run_existing_sample(
    ...,
    enable_capacity_report: bool = False,
    capacity_master_path=None,
    capacity_output_dir="outputs/capacity/runner",
):
    # existing planning logic
    ...

    if enable_capacity_report:
        run_capacity_report_hook(
            enabled=True,
            scenario_id=scenario_id,
            product_name=product_name,
            weeks=weeks,
            outbound_root=outbound_root,
            inbound_root=inbound_root,
            capacity_master_path=capacity_master_path,
            output_dir=capacity_output_dir,
            strict_capacity_master=False,
        )

The default must be:

enable_capacity_report = False
8. Capacity Master Path

v0.8 should use an explicit capacity master path.

Recommended parameter:

capacity_master_path: str | Path | None = None

If not provided, the runner should not fail.

Recommended default behavior:

If enable_capacity_report == True
and capacity_master_path is missing:
    run hook in non-strict mode
    return no-op if file is missing

This preserves compatibility with existing scenarios that do not yet have capacity masters.

9. Output Directory

Recommended default output directory:

outputs/capacity/runner

Expected files when enabled and records exist:

outputs/capacity/runner/capacity_usage.csv
outputs/capacity/runner/capacity_violation.csv

The output path may be adjusted to fit existing repository conventions.

10. Required Behavior
10.1 Default Disabled Behavior

When enable_capacity_report=False, the runner must behave exactly as before.

Expected:

no capacity report hook call
no capacity output required
existing output unchanged
10.2 Enabled Behavior

When enable_capacity_report=True, the runner should call:

run_capacity_report_hook(...)

Expected:

capacity_usage.csv generated if usage records exist
capacity_violation.csv generated if violation records exist
no modification to existing PSI planning result
10.3 Missing Capacity Master

If capacity master file is missing and strict mode is not enabled:

do not crash
return empty capacity records
continue existing runner behavior
11. Suggested Test Strategy

Recommended new test file:

tests/test_capacity_report_hook_runner_option.py

The test should not require full GUI execution.

The test may use a small fake runner function or an existing runner function if it is lightweight and safe.

12. Test Case 1: Default Option Disabled

Purpose:

Verify that capacity report is disabled by default.

Expected:

runner executes successfully
capacity hook is not required
no capacity output is required
13. Test Case 2: Enabled Option Produces Report

Purpose:

Verify that enabling the option triggers capacity report generation.

Use small test trees or a lightweight runner fixture.

Expected output:

capacity_usage.csv
capacity_violation.csv

Expected records:

at least one usage record
at least one violation record
14. Test Case 3: Missing Capacity Master Non-Strict

Purpose:

Verify that enabling capacity report with a missing capacity master path does not crash in non-strict mode.

Expected:

runner completes
no exception
capacity report returns empty records or no output
15. Test Case 4: Existing Tests Still Pass

The following command should pass:

PYTHONPATH=. pytest -q \
  tests/test_capacity_planning_basic.py \
  tests/test_capacity_planning_dummy_node.py \
  tests/test_capacity_planning_real_node.py \
  tests/test_capacity_planning_small_outbound_tree.py \
  tests/test_capacity_planning_small_inbound_tree.py \
  tests/test_capacity_report_hook.py \
  tests/test_capacity_report_hook_smoke_runner.py

If v0.8 adds a new test file, include it:

PYTHONPATH=. pytest -q \
  tests/test_capacity_planning_basic.py \
  tests/test_capacity_planning_dummy_node.py \
  tests/test_capacity_planning_real_node.py \
  tests/test_capacity_planning_small_outbound_tree.py \
  tests/test_capacity_planning_small_inbound_tree.py \
  tests/test_capacity_report_hook.py \
  tests/test_capacity_report_hook_smoke_runner.py \
  tests/test_capacity_report_hook_runner_option.py

On Windows command prompt:

set PYTHONPATH=.
pytest -q tests/test_capacity_planning_basic.py tests/test_capacity_planning_dummy_node.py tests/test_capacity_planning_real_node.py tests/test_capacity_planning_small_outbound_tree.py tests/test_capacity_planning_small_inbound_tree.py tests/test_capacity_report_hook.py tests/test_capacity_report_hook_smoke_runner.py tests/test_capacity_report_hook_runner_option.py
16. Minimal Fix Policy

Allowed fixes:

- add a disabled-by-default capacity report option
- add a lightweight runner wrapper if existing runner is not suitable
- add a small test for runner option behavior
- create output directories when enabled
- preserve existing v0.1 through v0.7 tests

Not allowed:

- replacing existing Forward Planning
- changing existing default runner behavior
- modifying GUI
- modifying costing modules
- modifying event extraction modules
- adding optimization
- redesigning scenario master
17. Completion Criteria

v0.8 is complete when:

A safe runner-level capacity report option is added.
The option is disabled by default.
Existing runner behavior is unchanged when disabled.
When enabled, run_capacity_report_hook() is called.
Capacity report CSV files can be generated.
Missing capacity master in non-strict mode does not crash.
A test or smoke verification confirms the option behavior.
Existing v0.1 through v0.7 tests still pass.
No existing WOM planning behavior is changed by default.
18. Future Steps

After v0.8, possible next steps are:

v0.9:
    Add GUI or management cockpit visibility for capacity report files.

v1.0:
    Consider capacity-constrained execution mode.

Future:
    Connect capacity violations to event trace and management issue analyzer.

v0.8 should remain small and safe.

19. Design Summary

v0.8 connects the optional capacity report hook to an existing WOM runner or pipeline-level option.

It still does not replace existing Forward Planning.

It proves this:

The capacity report hook can be invoked from an existing WOM execution path
without changing default behavior.

In WOM terms:

v0.1:
    The capacity gate was built.

v0.2:
    Dummy lots passed through the gate.

v0.3:
    Real-WOM-compatible lots passed through the gate.

v0.4:
    Lots passed through a small outbound road.

v0.5:
    Lots passed through a small inbound Fan-In road.

v0.6:
    A capacity checkpoint was placed after the existing planning road.

v0.7:
    A manual test button was added for the checkpoint.

v0.8:
    The checkpoint is connected to an existing WOM runner, but remains off by default.

The first goal is still not optimization.

The first goal is to make capacity collision visible at the Lot level through an optional, safe runner connection.