# Codex Request: Implement Forward PUSH with Capacity Planning v0r2

## 1. Background

We are working on the branch:

```text
feature/with-capacity-psi-engine-v0r2

The design memo has already been added and pushed:

docs/design/with_capacity_forward_push_planning_v0r2.md

Please read this design memo first and implement the MVP described there.

The previous v0r1 work focused on capacity report hooks, smoke runners, and disabled-by-default capacity reporting.

The goal of v0r2 is to move from capacity observation to capacity-constrained execution.

In short:

v0r1:
    capacity measurement meter and diagnosis window

v0r2:
    Forward PUSH with Capacity Planning MVP
2. Main Objective

Implement a new planning capability:

Forward PUSH with Capacity Planning

This new module should apply weekly capacity constraints during Forward PUSH planning.

The existing original Forward PUSH planning behavior must remain unchanged.

The new capacity-aware planner should be implemented as a separate module, not by adding complex ON/OFF branching inside the existing planner.

Conceptually:

Original Forward PUSH Planning
    = ideal plan without capacity constraints

Forward PUSH with Capacity Planning
    = executable plan with weekly capacity constraints
3. Most Important Design Principle

Please do not modify the existing Forward PUSH planner in a way that changes its current behavior.

The original planner must remain available as the capacity-unconstrained baseline.

Please add the new capability separately, so that future GUI integration can call:

Run Original Forward PUSH Plan
Run Forward PUSH with Capacity Plan
Compare Plans

This separation is intentional.

4. Scope of This Request

Please implement the MVP only.

In Scope

Please implement:

A new Forward PUSH with Capacity planning module.
A small capacity bucket component.
A simple capacity issue/result structure.
Logic to split requested lots into:
accepted / executable lots
blocked / backlog lots
Basic capacity usage summary.
Basic capacity shortage issue generation.
A smoke runner to exercise the new logic.
Basic tests.
Out of Scope

Please do not implement the following in this request:

Advanced allocation optimization.
Profit-based priority allocation.
Multi-bottleneck global optimization.
PULL planning integration.
GUI button integration.
Management cockpit integration.
Costing / profit simulation integration.
Lane selection optimization.
TOC-style throughput optimization.

These will be handled in later milestones.

5. Expected Behavior

For each planning bucket:

node_id
product_id
week

compare:

requested_lots
available_capacity

The MVP behavior should be:

requested_lots <= available_capacity
    -> all requested lots are accepted and pushed

requested_lots > available_capacity
    -> lots within capacity are accepted and pushed
    -> excess lots are blocked and recorded

The default allocation rule for v0r2 should be simple:

first-in, first-pushed

No advanced priority rule is required in v0r2.

6. Bottleneck Rule

Allocation is required only at bottleneck nodes.

A bottleneck exists when:

requested_lots > available_capacity

for a given:

node_id
product_id
week

If a node is not capacity-constrained, no special allocation is required.

non-bottleneck node:
    normal pass-through

bottleneck node:
    apply simple capacity allocation
7. Missing Capacity Policy

For the MVP, please use the following default policy:

missing capacity means unlimited capacity

Reason:

Existing scenarios may not yet define full capacity data.
This default avoids breaking existing plans and keeps the new capacity-aware behavior opt-in through available capacity data.

Please make this policy explicit in code comments and tests.

8. Suggested Module Structure

Please inspect the current repository structure and adapt file locations accordingly.

The design memo suggests the following structure:

pysi/planning/forward_push_with_capacity_planner.py
pysi/planning/capacity_bucket.py
pysi/planning/capacity_issue.py
pysi/runners/run_forward_push_with_capacity_smoke.py
tests/test_forward_push_with_capacity_planner.py

If the repository already has a more appropriate location for planning engine modules, please follow the existing convention.

Please avoid large refactoring unless required.

9. Suggested Data Structures

Please add small, testable data structures.

For example:

from dataclasses import dataclass, field
from typing import Any

@dataclass
class CapacityBucket:
    node_id: str
    product_id: str
    week: Any
    capacity_qty: int
    used_qty: int = 0

    @property
    def remaining_qty(self) -> int:
        return max(self.capacity_qty - self.used_qty, 0)

Suggested result structure:

@dataclass
class ForwardPushWithCapacityResult:
    pushed_lots: list = field(default_factory=list)
    blocked_lots: list = field(default_factory=list)
    backlog_lots: list = field(default_factory=list)
    capacity_usage: list = field(default_factory=list)
    capacity_issues: list = field(default_factory=list)

Suggested capacity issue fields:

issue_type
node_id
product_id
week
requested_qty
capacity_qty
accepted_qty
blocked_qty
blocked_lot_ids
severity
message

Issue type:

CAPACITY_SHORTAGE

Please adapt field names to match the existing code style.

10. MVP Functionality

Please implement a function or class method that can consume requested lots against capacity.

Conceptual behavior:

accepted_lots, blocked_lots = consume_lots_with_capacity(
    requested_lots=requested_lots,
    capacity_qty=capacity_qty,
)

Expected result:

requested lots: 120
capacity: 100

accepted lots: 100
blocked lots: 20

If capacity is missing:

accepted lots: all
blocked lots: none

If capacity is zero:

accepted lots: none
blocked lots: all
capacity shortage issue: generated
11. Smoke Runner

Please add a smoke runner that can be executed from the command line.

Suggested file:

pysi/runners/run_forward_push_with_capacity_smoke.py

The runner should create a minimal scenario such as:

node_id: MOM_A
product_id: PRODUCT_X
week: 2026-W01
requested lots: 120
capacity: 100

Expected output:

accepted lots: 100
blocked lots: 20
capacity usage: 100 / 100
capacity issue: CAPACITY_SHORTAGE

Also include a non-bottleneck case:

requested lots: 80
capacity: 100

Expected:

accepted lots: 80
blocked lots: 0
capacity issue: none

The smoke runner may print results to stdout.

Optional CSV output is welcome but not required for the first MVP.

If CSV output is added, suggested files are:

outputs/capacity/forward_push_with_capacity_usage.csv
outputs/capacity/forward_push_with_capacity_issues.csv
outputs/capacity/forward_push_with_capacity_blocked_lots.csv
12. Tests

Please add tests for the MVP logic.

Required test cases:

12.1 Capacity is sufficient
requested <= capacity

Expected:

all lots are accepted
no blocked lots
no capacity issue
12.2 Capacity is insufficient
requested > capacity

Expected:

accepted lots equal capacity
excess lots are blocked
capacity shortage issue is generated
12.3 Zero capacity
capacity = 0

Expected:

no lots are accepted
all lots are blocked
capacity shortage issue is generated
12.4 Missing capacity
capacity is None or missing

Expected:

all lots are accepted
no blocked lots
no capacity issue

Please keep tests small and deterministic.

13. Compatibility Requirements

Please verify that existing tests still pass.

At minimum, please run:

python -m pytest -q

If the full test suite is too large or has unrelated failures, please run the new test file and any relevant capacity tests:

python -m pytest -q tests/test_forward_push_with_capacity_planner.py
python -m pytest -q -k "capacity"

Please report what was run and the result.

14. Implementation Constraints

Please follow these constraints:

Keep the original Forward PUSH planner behavior unchanged.
Avoid broad refactoring.
Prefer small, isolated, testable components.
Add comments where the missing capacity policy is implemented.
Keep the MVP simple.
Do not implement GUI integration in this request.
Do not implement advanced allocation rules in this request.
Do not introduce new external dependencies unless absolutely necessary.
15. Completion Criteria

This request is complete when:

[OK] new Forward PUSH with Capacity planner module exists
[OK] capacity bucket logic exists
[OK] requested lots can be split into accepted and blocked lots
[OK] capacity shortage issue can be generated
[OK] missing capacity is treated as unlimited capacity
[OK] zero capacity blocks all requested lots
[OK] smoke runner runs successfully
[OK] tests are added
[OK] original Forward PUSH planning behavior is not changed
16. Expected Response from Codex

After implementation, please summarize:

Files changed.
Main implementation approach.
Test commands executed.
Test results.
Any limitations or follow-up tasks.

Please do not proceed into v0r3 advanced allocation logic.
This request is only for v0r2 MVP.