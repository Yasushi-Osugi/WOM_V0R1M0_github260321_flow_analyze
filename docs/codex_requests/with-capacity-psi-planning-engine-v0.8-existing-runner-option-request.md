# Codex Request: with Capacity PSI Planning Engine v0.8
## Connect Optional Capacity Report Hook to Existing WOM Runner Option

## 1. Request Summary

Please implement v0.8 of the **with Capacity PSI Planning Engine**.

This request is based on the design document:

```text
docs/design/with-capacity-psi-planning-engine-v0.8-existing-runner-option.md

v0.1 added the additive pysi.capacity package.

v0.2 added dummy-node PSI list integration tests.

v0.3 added real-WOM-compatible node tests.

v0.4 added small Outbound Tree integration tests.

v0.5 added small Inbound Tree integration tests.

v0.6 added the optional capacity report hook:

run_capacity_report_hook()

v0.7 added a manually executable smoke runner:

tools/smoke_capacity_report_hook.py

v0.8 should connect the optional capacity report hook to an existing WOM sample runner or a safe runner-level option.

The key goal is:

Make capacity reporting available from an existing WOM execution path,
while keeping the default behavior unchanged.

This is not capacity-constrained execution mode.

Do not replace existing Forward Planning.

Do not change existing WOM runner behavior by default.

2. Current Branch

The target branch is:

feature/with-capacity-psi-engine-v0r1

Current completed stages:

v0.1:
    Capacity package skeleton
    Capacity dataclasses
    Capacity master loader
    Capacity planner utilities
    CSV exporters
    Basic tests

v0.2:
    DummyNode PSI list integration tests

v0.3:
    RealLikeNode compatibility tests

v0.4:
    Small Outbound Tree tests

v0.5:
    Small Inbound Tree tests

v0.6:
    Optional capacity report hook

v0.7:
    Smoke capacity report hook runner

v0.8 should build on the existing v0.6 / v0.7 implementation.

3. Important Concept

Please preserve the core WOM concept:

Monthly PSI on Capacity:
    numeric PSI calculation

Weekly WOM PSI with Capacity:
    lot_ID list operation under capacity constraints

The capacity report hook must continue to operate on psi4demand and psi4supply lot_ID list structures.

Do not convert the weekly WOM PSI structure into pure numeric PSI calculations.

4. Required Task

Please inspect the repository and identify a safe existing runner or sample execution path where the optional capacity report hook can be connected.

Candidate locations may include:

tools/
pysi/
pysi/runner/
pysi/pipeline/
pysi/reporting/
sample runner scripts

A suitable runner should already have access to some or all of:

scenario_id
product_name
weeks
outbound_root
inbound_root
output directory

If no existing runner can safely provide these inputs, do not force integration into a fragile location.

In that case, create a lightweight runner-option wrapper around the v0.7 smoke runner pattern, and document the reason in comments.

5. Required Design Principle

The new option must be disabled by default.

Required default:

enable_capacity_report = False

The integration pattern should be:

if enable_capacity_report:
    run_capacity_report_hook(...)

When enable_capacity_report=False, existing behavior must remain unchanged.

6. Preferred Integration Pattern

If an existing runner function is suitable, update it with optional arguments such as:

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

The default must remain:

enable_capacity_report = False
7. Capacity Master Behavior

Use an explicit capacity master path.

Recommended parameter:

capacity_master_path: str | Path | None = None

If enable_capacity_report=True and the capacity master path is missing, the integration should call the hook in non-strict mode.

Expected behavior:

missing capacity master
↓
no crash
↓
capacity report returns empty records or no output
↓
existing runner continues

This preserves compatibility with existing WOM scenarios that do not yet have capacity masters.

8. Output Directory

Recommended default output directory:

outputs/capacity/runner

Expected files when enabled and records exist:

outputs/capacity/runner/capacity_usage.csv
outputs/capacity/runner/capacity_violation.csv

The output path may be adjusted if the repository has an existing convention for runner outputs.

9. Required Behavior
9.1 Default Disabled Behavior

When enable_capacity_report=False:

existing runner behavior unchanged
capacity report hook not required
capacity output not required
no new failure path introduced
9.2 Enabled Behavior

When enable_capacity_report=True:

run_capacity_report_hook() is called
capacity_usage.csv is generated if usage records exist
capacity_violation.csv is generated if violation records exist
existing PSI planning result is not modified
9.3 Missing Capacity Master

When capacity master file is missing and strict mode is not enabled:

do not crash
continue existing runner behavior
capacity report returns empty records or no output
10. Recommended New Test File

Please add a small test file if practical:

tests/test_capacity_report_hook_runner_option.py

The test should avoid full GUI execution.

The test may use:

Option A:
    a lightweight existing runner if available

Option B:
    a small fake runner function that mimics the selected integration pattern

Option A is preferred only if it is safe and lightweight.

Do not make the test depend on full GUI startup or real business scenario loading.

11. Required Tests
11.1 Default Option Disabled Test

Test name:

def test_capacity_report_runner_option_disabled_by_default():
    ...

Purpose:

Verify that capacity reporting is disabled by default.

Expected:

runner executes successfully
capacity hook is not required
no capacity output is required
11.2 Enabled Option Produces Report Test

Test name:

def test_capacity_report_runner_option_enabled_outputs_files(tmp_path):
    ...

Purpose:

Verify that enabling the option triggers capacity report generation.

Expected output:

capacity_usage.csv
capacity_violation.csv

Expected records:

at least one usage record
at least one violation record
11.3 Missing Capacity Master Non-Strict Test

Test name:

def test_capacity_report_runner_option_missing_master_non_strict(tmp_path):
    ...

Purpose:

Verify that enabling capacity report with a missing capacity master path does not crash.

Expected:

runner completes
no exception
capacity report returns empty records or no output
12. Required Existing Test Compatibility

The following tests must still pass:

PYTHONPATH=. pytest -q \
  tests/test_capacity_planning_basic.py \
  tests/test_capacity_planning_dummy_node.py \
  tests/test_capacity_planning_real_node.py \
  tests/test_capacity_planning_small_outbound_tree.py \
  tests/test_capacity_planning_small_inbound_tree.py \
  tests/test_capacity_report_hook.py \
  tests/test_capacity_report_hook_smoke_runner.py

If v0.8 adds the new test file, also include it:

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
13. Manual Smoke Verification

The existing v0.7 smoke runner should still work:

set PYTHONPATH=.
python tools/smoke_capacity_report_hook.py

Expected:

capacity_usage.csv created
capacity_violation.csv created
console summary printed
14. Minimal Fix Policy

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
15. Do Not Modify Existing WOM Pipeline Behavior by Default

Please do not change the default behavior of:

existing GUI files
existing costing modules
existing event extraction modules
existing non-capacity planning engine
existing Run Full Plan pipeline
existing sample scenario behavior

If integration into an existing runner is done, it must be controlled by an explicit disabled-by-default option.

16. Expected Completion Criteria

v0.8 is complete when:

A safe runner-level capacity report option is added.
The option is disabled by default.
Existing runner behavior is unchanged when disabled.
When enabled, run_capacity_report_hook() is called.
Capacity report CSV files can be generated.
Missing capacity master in non-strict mode does not crash.
A test or smoke verification confirms option behavior.
Existing v0.1 through v0.7 tests still pass.
No existing WOM planning behavior is changed by default.
17. Notes for Codex

This is not capacity-constrained execution mode.

This is not GUI integration.

This is not optimization.

This is not costing integration.

This is a small, defensive, disabled-by-default runner option.

The key goal is:

Confirm that the capacity report hook can be invoked from an existing WOM execution path
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

Please keep the implementation small, readable, additive, and safe.