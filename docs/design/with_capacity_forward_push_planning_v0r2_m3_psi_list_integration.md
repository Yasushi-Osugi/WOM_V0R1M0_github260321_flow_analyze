# With-Capacity PSI Engine v0r2-m3 Design Memo
## PSI List Integration for Forward PUSH with Capacity Planning

## 1. Purpose

This document defines the design scope and implementation approach for:

```text
with-capacity PSI engine v0r2-m3

The purpose of v0r2-m3 is to connect the existing v0r2-m1 / v0r2-m2 components to WOM's actual PSI list structure.

v0r2-m1 implemented the standalone capacity-aware split logic:

requested lots
capacity
accepted lots
blocked lots
capacity issue

v0r2-m2 implemented the capacity I/O layer:

capacity_master.csv loader
capacity lookup
CapacityUsage
CapacityViolation
usage / violation CSV export

v0r2-m3 now connects these to:

Node.psi4demand
Node.psi4supply

The goal is to apply capacity constraints to demand-placed lot lists and reflect accepted lots into supply-side PSI lists while preserving blocked / overflow lots.

2. Background

The overall roadmap is:

v0r1:
    capacity report / hook / runner foundation

v0r2-m1:
    standalone Forward PUSH with Capacity planner MVP

v0r2-m2:
    capacity master loader and usage / violation CSV output

v0r2-m3:
    WOM PSI list integration

v0r3:
    bottleneck allocation rule enhancement

v0r2-m3 is still part of v0r2.

It should not introduce advanced allocation optimization.

The essence of v0r2 remains:

capacityを超えたら流せない

v0r2-m3 applies that rule to real or real-like WOM PSI list structures.

3. Core Concept

WOM nodes already hold lot lists in PSI structures.

Typical conceptual structure:

node.psi4demand[week][S/CO/I/P] = [lot_id, lot_id, ...]
node.psi4supply[week][S/CO/I/P] = [lot_id, lot_id, ...]

The with-capacity Forward PUSH logic should:

1. read requested lots from node.psi4demand
2. look up capacity from capacity master
3. split requested lots into accepted and blocked lots
4. write accepted lots into node.psi4supply
5. keep blocked lots in backlog / carryover records
6. generate CapacityUsage / CapacityViolation

The processing unit remains lot lists, not aggregated quantities.

4. Design Principle

Key principles:

1. Do not modify the original Forward PUSH planner behavior.
2. Do not rewrite the existing Node class.
3. Add a thin PSI-list adapter around v0r2-m1 / v0r2-m2 components.
4. Keep m1 and m2 tests passing.
5. Avoid broad refactoring.
6. Keep the first PSI integration narrow and testable.
7. Do not implement advanced allocation rules in v0r2-m3.
8. Do not implement GUI integration in v0r2-m3.

v0r2-m3 is an integration milestone, not an optimization milestone.

5. Scope
5.1 In Scope

v0r2-m3 should implement:

PSI list read helper
PSI list write helper
P/S capacity application to Node.psi4demand and Node.psi4supply
blocked lot / carryover record structure
minimal runner using real-like PSI node objects
usage / violation CSV export reuse
basic tests for PSI list integration
5.2 Out of Scope

v0r2-m3 should not implement:

advanced allocation priority
market priority
profit priority
multi-bottleneck optimization
full PULL integration
GUI integration
management cockpit integration
costing integration
lane alternative selection
TOC optimization
full E2E scenario execution

These remain later milestones.

6. PSI Bucket Policy

The existing WOM code may represent PSI buckets by numeric index or symbolic name.

Known conceptual bucket order:

S
CO
I
P

A common internal representation may be:

0: "S"
1: "CO"
2: "I"
3: "P"

v0r2-m3 should avoid hard-coding assumptions too deeply.

Recommended approach:

PSI_BUCKET_INDEX = {
    "S": 0,
    "CO": 1,
    "I": 2,
    "P": 3,
}

Helper functions should isolate this mapping.

If the repository already defines bucket constants, use the existing definitions.

7. Target Capacity Types for v0r2-m3

v0r2-m3 should focus on P and S capacity first.

7.1 P capacity
capacity_type = P

Reads requested lots from the demand-side P bucket and writes accepted lots to the supply-side P bucket.

Conceptual behavior:

requested_lots = node.psi4demand[week][P]
accepted_lots, blocked_lots = capacity planner
node.psi4supply[week][P].extend(accepted_lots)
7.2 S capacity
capacity_type = S

Reads requested lots from the demand-side S bucket and writes accepted lots to the supply-side S bucket.

Conceptual behavior:

requested_lots = node.psi4demand[week][S]
accepted_lots, blocked_lots = capacity planner
node.psi4supply[week][S].extend(accepted_lots)
7.3 I capacity
capacity_type = I

I capacity is stock capacity.

v0r2-m3 may define structure for I-cap checks, but full I-cap enforcement may remain a later extension.

For this milestone, P/S flow capacity is the priority.

8. Carryover / Backlog Policy

When capacity is insufficient, blocked lots must not disappear.

For v0r2-m3, use a simple carryover structure:

carryover[(node_name, product_name, next_week, capacity_type)] = [lot_id, ...]

Recommended behavior:

accepted lots:
    written to node.psi4supply[week][bucket]

blocked lots:
    recorded in carryover / backlog result
    optionally added to next week's requested list only inside the adapter result, not by destructive mutation unless explicitly implemented

To keep the first integration safe, the default behavior should be:

record blocked lots as carryover candidates
do not aggressively rewrite future psi4demand unless test-covered

If future-week carryover insertion is implemented, it must be simple and explicit.

9. Minimal Result Object

Add a result object for PSI integration.

Suggested dataclass:

@dataclass
class ForwardPushWithCapacityPsiResult:
    usage_records: list[CapacityUsage] = field(default_factory=list)
    violation_records: list[CapacityViolation] = field(default_factory=list)
    accepted_lots_by_key: dict = field(default_factory=dict)
    blocked_lots_by_key: dict = field(default_factory=dict)
    carryover_lots_by_key: dict = field(default_factory=dict)

Suggested key:

(node_name, product_name, week, capacity_type)
10. Proposed Module Structure

Suggested files:

pysi/planning/forward_push_with_capacity_psi_adapter.py
pysi/runners/run_forward_push_with_capacity_psi_smoke.py
tests/test_forward_push_with_capacity_psi_adapter.py

Reuse existing files from v0r2-m1 and v0r2-m2:

pysi/planning/forward_push_with_capacity_planner.py
pysi/planning/capacity_master.py
pysi/planning/capacity_io.py
pysi/master_data/capacity_master_sample.csv

Avoid broad refactoring.

11. Suggested Functions
11.1 PSI list helpers
def get_psi_lots(node, psi_attr: str, week: str | int, bucket: str) -> list:
    ...

Example:

get_psi_lots(node, "psi4demand", "2026-W01", "P")
11.2 PSI list writer
def append_psi_lots(node, psi_attr: str, week: str | int, bucket: str, lots: list) -> None:
    ...

Example:

append_psi_lots(node, "psi4supply", "2026-W01", "P", accepted_lots)
11.3 Capacity application for one node / week / type
def apply_capacity_to_node_psi_bucket(
    *,
    node,
    scenario_id: str,
    tree_side: str,
    product_name: str,
    week: str | int,
    capacity_type: str,
    capacity_lookup: dict,
) -> tuple[list, list, CapacityUsage | None, CapacityViolation | None]:
    ...

Expected behavior:

read requested lots from node.psi4demand
run capacity-aware split using v0r2-m2 wrapper
write accepted lots to node.psi4supply
return accepted / blocked / usage / violation
11.4 Multi-week adapter
def run_forward_push_with_capacity_psi_lists(
    *,
    nodes: list,
    weeks: list[str | int],
    scenario_id: str,
    tree_side: str,
    product_name: str,
    capacity_lookup: dict,
    capacity_types: list[str] = ["P", "S"],
) -> ForwardPushWithCapacityPsiResult:
    ...

Expected behavior:

for each week
  for each node
    for capacity_type in ["P", "S"]
      read node.psi4demand
      apply capacity
      write accepted lots to node.psi4supply
      record blocked lots
      record usage / violation
12. Tree Order Policy

v0r2-m3 may accept nodes as an explicit ordered list.

Recommended first implementation:

caller provides nodes in planning order

This avoids prematurely implementing traversal.

Optional later helper:

iter_nodes_for_capacity_forward(root_node, tree_side)

Conceptual traversal:

OUTBOUND:
    preorder

INBOUND:
    postorder

But this traversal abstraction may be left as a later extension if current Node tree APIs are unclear.

13. Missing Capacity Policy

Keep v0r2-m2 policy:

missing capacity means unlimited capacity

Therefore:

capacity record missing:
    all requested lots are accepted
    no violation emitted by default

capacity record found:
    apply capacity check
    generate usage
    generate violation if overflow exists
14. Mutation Policy

v0r2-m3 should mutate only the supply-side PSI list by default.

Recommended default:

read:
    node.psi4demand

write:
    node.psi4supply

do not delete lots from psi4demand

Reason:

This preserves the original demand-placed state and keeps comparison/debugging easier.

The accepted lots in psi4supply represent executable supply under capacity constraints.

Blocked lots are recorded separately in result structures.

15. Smoke Scenario

The smoke runner should create minimal real-like nodes.

Example node:

@dataclass
class MiniPsiNode:
    name: str
    psi4demand: dict
    psi4supply: dict

Initial demand:

node.psi4demand["2026-W01"][P] = 120 lots
node.psi4supply["2026-W01"][P] = []

Capacity:

BASE,INBOUND,MOM_CHINA,IPHONE_NM_2028_BASE,2026-W01,P,100,soft,LOT,100,STD_CAL,weekly production capacity

Expected after run:

psi4supply["2026-W01"][P] has 100 accepted lots
blocked lots = 20
usage record = 100 / 100
violation = CAPACITY_OVER or CAPACITY_SHORTAGE

The runner should export:

outputs/capacity/forward_push_with_capacity_psi_usage.csv
outputs/capacity/forward_push_with_capacity_psi_violation.csv
16. Test Policy

Required tests:

1. get_psi_lots reads P bucket from psi4demand
2. append_psi_lots writes accepted lots to psi4supply
3. capacity-sufficient case writes all lots to psi4supply
4. capacity-shortage case writes only accepted lots to psi4supply
5. blocked lots are recorded and not lost
6. missing capacity accepts all lots
7. usage records are generated when capacity exists
8. violation records are generated when capacity is exceeded
9. original psi4demand is preserved
10. v0r2-m1 and v0r2-m2 tests still pass
17. Completion Criteria

v0r2-m3 is complete when:

[OK] PSI adapter module exists
[OK] node.psi4demand can be read through helper
[OK] node.psi4supply can be updated through helper
[OK] P capacity can be applied to PSI list
[OK] S capacity can be applied to PSI list
[OK] accepted lots are written to psi4supply
[OK] blocked lots are recorded separately
[OK] missing capacity remains unlimited
[OK] usage / violation records are reused from v0r2-m2
[OK] smoke runner works
[OK] tests pass
[OK] original Forward PUSH planner remains unchanged
18. Boundary with v0r3

v0r2-m3 does not choose which lots should be prioritized beyond the current default order.

The default rule remains:

first-in, first-pushed

v0r3 will handle:

market priority
product priority
customer priority
profit priority
due-date priority
strategic allocation
19. Summary

v0r2-m3 connects the with-capacity planner to WOM PSI list structures.

The essence is:

demand側に置かれたLot listを読み、
capacity内のLotだけをsupply側PSI listへ移し、
capacity超過Lotをblocked / carryover候補として記録する

This milestone turns the v0r2-m1 / v0r2-m2 components into a PSI-connected planning adapter.

It prepares the ground for v0r3 allocation rule enhancement.