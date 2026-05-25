# With-Capacity PSI Engine v0r2 Design Memo
## Forward PUSH with Capacity Planning MVP

## 1. Purpose

This document defines the design scope and implementation approach for
`with-capacity PSI engine v0r2`.

The goal of v0r2 is to implement the first MVP version of:

```text
Forward PUSH with Capacity Planning

This planning module applies weekly capacity constraints to the Forward PUSH PSI planning process.

The existing Forward PUSH planning module must remain unchanged as the original, capacity-unconstrained planning logic.

The new module should be implemented separately so that users and developers can clearly compare:

Original Forward PUSH Planning
    = ideal plan without capacity constraints

Forward PUSH with Capacity Planning
    = executable plan with weekly capacity constraints
2. Background

In v0r1, the with-capacity PSI engine work focused on foundation-level functionality:

capacity report hook
smoke capacity report runner
disabled-by-default capacity report option
basic runner integration
basic tests for capacity report behavior

v0r1 is therefore understood as:

capacity measurement meter and diagnosis window

v0r2 moves from capacity observation to planning execution.

The key question for v0r2 is:

When requested lots exceed available weekly capacity,
which lots can be pushed forward,
and which lots must be blocked, delayed, or carried over?
3. Design Principle

The core design principle is:

Do not modify the existing Forward PUSH planning module directly.
Add a new Forward PUSH with Capacity planning module.

This keeps the original planning behavior stable and allows clear comparison between:

capacity-unconstrained ideal plan
capacity-constrained executable plan

This also avoids introducing complex ON/OFF switches inside the original planning logic.

4. Scope of v0r2

v0r2 targets the MVP implementation of Forward PUSH with Capacity Planning.

4.1 In Scope

v0r2 should implement:

new planning module for Forward PUSH with Capacity
weekly capacity check by node / product / week
capacity bucket logic
separation of executable lots and blocked lots
backlog / carryover data structure
capacity usage summary
capacity issue summary
smoke runner for with-capacity planning
basic tests for capacity-constrained behavior
4.2 Out of Scope

v0r2 should not attempt to implement the following advanced features:

complex allocation optimization
profit-based priority allocation
multi-bottleneck global optimization
PULL planning integration
GUI button integration
management cockpit integration
costing / profit simulation integration
lane selection optimization
TOC-style throughput optimization

These should be handled in later versions.

5. Target Behavior

The basic behavior of v0r2 is simple.

For each node / product / week:

requested lots <= available capacity
    -> all requested lots are pushed forward

requested lots > available capacity
    -> only lots within available capacity are pushed forward
    -> excess lots are blocked and recorded as backlog / carryover

The allocation rule in v0r2 is intentionally simple.

Default MVP rule:

first-in, first-pushed

Advanced priority rules will be handled in v0r3 or later.

6. Planning Concept
6.1 Original Forward PUSH Planning

The existing Forward PUSH planning assumes that lots can be pushed through the supply chain according to the planning logic, without explicitly limiting the flow by weekly capacity.

It represents an ideal or unconstrained plan.

Demand / supply lots
    ↓
Forward PUSH logic
    ↓
PSI list update
6.2 Forward PUSH with Capacity Planning

The new v0r2 module inserts a capacity check into the Forward PUSH flow.

Demand / supply lots
    ↓
Forward PUSH with Capacity logic
    ↓
Capacity bucket check
    ↓
Executable lots are pushed
Blocked lots are recorded
    ↓
PSI list update
    ↓
Capacity issue report
7. Bottleneck and Allocation Rule

Allocation is required only when a node becomes a bottleneck.

A bottleneck is defined as:

requested_lots > available_capacity

at a given:

node_id
product_id
week

If a node is not capacity-constrained, no allocation rule is required.

non-bottleneck node:
    normal pass-through

bottleneck node:
    capacity allocation rule is applied

In v0r2, the allocation rule should remain simple:

accept lots until capacity is consumed
block the remaining lots

This is sufficient for the MVP.

8. Proposed Module Structure

The recommended structure is:

pysi/planning/forward_push_with_capacity_planner.py
pysi/planning/capacity_bucket.py
pysi/planning/capacity_issue.py
pysi/runners/run_forward_push_with_capacity_smoke.py
tests/test_forward_push_with_capacity_planner.py

The exact folder names may be adjusted to match the current repository structure.

9. Key Components
9.1 CapacityBucket

CapacityBucket manages available weekly capacity.

Responsibilities:

hold total capacity
hold used capacity
calculate remaining capacity
accept executable lots
reject excess lots
return blocked lots

Conceptual behavior:

bucket = CapacityBucket(capacity=100)

accepted, blocked = bucket.consume(lots)

# accepted: lots within capacity
# blocked: lots exceeding capacity
9.2 CapacityUsage

CapacityUsage records capacity consumption by:

node_id
product_id
week
capacity
used
remaining
overload
9.3 CapacityIssue

CapacityIssue records bottleneck events.

Suggested fields:

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

Example issue type:

CAPACITY_SHORTAGE
9.4 ForwardPushWithCapacityPlanner

The new planner should:

receive planning context
read requested lots by node / product / week
check capacity bucket
push accepted lots forward
keep blocked lots in backlog / carryover
generate capacity usage and capacity issue records
return a structured result object
10. Suggested Result Object

The planner should return a result object such as:

@dataclass
class ForwardPushWithCapacityResult:
    pushed_lots: list
    blocked_lots: list
    backlog_lots: list
    capacity_usage: list
    capacity_issues: list

This keeps the planner result inspectable and testable.

11. Capacity Data Source

v0r2 should reuse the existing capacity-related master data as much as possible.

Candidate capacity sources include:

sku_P_month_data.csv
capacity report input data
existing node / product / week capacity structures

The first implementation should avoid creating a large new master format unless necessary.

If the current capacity source is monthly, v0r2 should convert it into weekly capacity buckets using the existing WOM convention.

Example:

monthly capacity -> weekly capacity by planning calendar

For MVP purposes, simple equal weekly distribution is acceptable if no more precise rule exists.

12. Backlog / Carryover Handling

When lots exceed capacity, they should not disappear.

They should be recorded as:

blocked_lots
backlog_lots
carryover_lots

For v0r2 MVP, the simplest behavior is:

blocked lots are recorded but not automatically rescheduled

Automatic rescheduling into future weeks can be added later.

This avoids mixing two problems:

capacity-constrained execution
backlog recovery planning

v0r2 should focus on the first.

13. Smoke Scenario

A minimal smoke scenario should include:

node_id: MOM_A
product_id: PRODUCT_X
week: 2026-W01
requested lots: 120
capacity: 100

Expected result:

accepted lots: 100
blocked lots: 20
capacity usage: 100 / 100
capacity issue: CAPACITY_SHORTAGE

A second non-bottleneck case should also be tested:

requested lots: 80
capacity: 100

Expected result:

accepted lots: 80
blocked lots: 0
capacity issue: none
14. Test Policy

v0r2 should include tests for the following cases.

14.1 Capacity is sufficient
requested <= capacity

Expected:

all lots are pushed
no blocked lots
no capacity issue
14.2 Capacity is insufficient
requested > capacity

Expected:

accepted lots equal capacity
excess lots are blocked
capacity issue is generated
14.3 Zero capacity
capacity = 0

Expected:

no lots are pushed
all requested lots are blocked
capacity issue is generated
14.4 Missing capacity

For MVP, missing capacity should be handled explicitly.

Recommended default:

missing capacity means unlimited capacity

or

missing capacity means zero capacity

The choice must be defined clearly in implementation.

Recommended v0r2 default:

missing capacity means unlimited capacity

Reason:

This avoids breaking existing scenarios that do not yet define full capacity data.

15. Compatibility Requirement

The original Forward PUSH planning behavior must not change.

The following must remain true:

Running the original planner produces the same result as before.

The new planner should be invoked explicitly.

Recommended invocation style:

Run Original Forward PUSH Plan
Run Forward PUSH with Capacity Plan

This separation will later make GUI integration easier.

16. CLI / Runner Policy

v0r2 should first be verified by a smoke runner, not by GUI.

Recommended runner:

pysi/runners/run_forward_push_with_capacity_smoke.py

The runner should print or export:

accepted lots
blocked lots
capacity usage
capacity issues

Optional output files:

outputs/capacity/forward_push_with_capacity_usage.csv
outputs/capacity/forward_push_with_capacity_issues.csv
outputs/capacity/forward_push_with_capacity_blocked_lots.csv
17. v0r2 Completion Criteria

v0r2 can be considered complete when:

[OK] original Forward PUSH planning remains unchanged
[OK] new Forward PUSH with Capacity module exists
[OK] capacity bucket logic works
[OK] requested lots are split into accepted and blocked lots
[OK] capacity shortage issue is generated
[OK] smoke runner runs successfully
[OK] tests pass
[OK] result can be inspected without GUI
18. Future Milestones
v0r3: Allocation Rule Enhancement

Add more advanced allocation rules at bottleneck nodes.

Examples:

market priority
product priority
customer priority
profit priority
due-date priority
strategic priority
v0r4: GUI Comparison

Add GUI-level comparison between:

Original Forward PUSH Plan
Forward PUSH with Capacity Plan

Expected GUI functions:

run original plan
run capacity plan
compare PSI
show bottleneck
show blocked lots
show backlog
v0r5: PULL Integration

Integrate PULL planning with capacity-constrained PUSH planning.

Concept:

PULL creates required supply requests.
PUSH with Capacity creates executable supply flow.
19. Summary

v0r2 is the first step from capacity observation to capacity-constrained execution.

The essence of v0r2 is:

capacityを超えたら流せない

The original Forward PUSH planner remains the ideal planning module.

The new Forward PUSH with Capacity planner becomes the executable planning module.

This separation allows WOM to compare:

what we want to do

and

what we can actually do under capacity constraints

This is the foundation for future bottleneck analysis, allocation planning, management issue detection, and scenario comparison.