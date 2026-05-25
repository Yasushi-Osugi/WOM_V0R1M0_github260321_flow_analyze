# Codex Request: Implement With-Capacity PSI Engine v0r2-m3 PSI List Integration

## 1. Background

We are working on:

```text
feature/with-capacity-psi-engine-v0r2

The previous milestones are complete:

v0r2-m1:
    standalone Forward PUSH with Capacity planner MVP

v0r2-m2:
    capacity_master.csv loader
    capacity lookup
    CapacityUsage / CapacityViolation
    usage / violation CSV export

The current request is:

v0r2-m3:
    connect Forward PUSH with Capacity logic to WOM PSI list structures

Please read the design memo first:

docs/design/with_capacity_forward_push_planning_v0r2_m3_psi_list_integration.md

Please also inspect the existing implementations:

pysi/planning/forward_push_with_capacity_planner.py
pysi/planning/capacity_master.py
pysi/planning/capacity_io.py
2. Main Objective

Implement a thin PSI-list integration adapter that:

1. reads requested lots from node.psi4demand
2. looks up capacity using v0r2-m2 capacity lookup
3. applies v0r2-m1 capacity split logic
4. writes accepted lots into node.psi4supply
5. records blocked lots separately
6. returns CapacityUsage / CapacityViolation records

This request should not implement advanced allocation logic.

The default rule remains:

first-in, first-pushed
3. Most Important Constraints

Please follow these constraints:

1. Do not modify the original Forward PUSH planner behavior.
2. Do not rewrite the Node class.
3. Do not implement GUI integration.
4. Do not implement PULL integration.
5. Do not implement costing / profit simulation.
6. Do not implement advanced allocation rules.
7. Keep v0r2-m1 and v0r2-m2 tests passing.
8. Keep implementation small and testable.

This is an integration adapter milestone.

4. Suggested Files

Please add:

pysi/planning/forward_push_with_capacity_psi_adapter.py
pysi/runners/run_forward_push_with_capacity_psi_smoke.py
tests/test_forward_push_with_capacity_psi_adapter.py

Please reuse:

pysi/planning/forward_push_with_capacity_planner.py
pysi/planning/capacity_master.py
pysi/planning/capacity_io.py
pysi/master_data/capacity_master_sample.csv

Avoid broad refactoring.

5. PSI Bucket Handling

The PSI list structure is conceptually:

node.psi4demand[week][S/CO/I/P] = [lot_id, ...]
node.psi4supply[week][S/CO/I/P] = [lot_id, ...]

Please isolate bucket mapping in helper functions.

Suggested mapping:

PSI_BUCKET_INDEX = {
    "S": 0,
    "CO": 1,
    "I": 2,
    "P": 3,
}

If the repository already has PSI bucket constants, use the existing definitions instead.

6. Required Helper Functions

Please implement small helper functions.

6.1 Read PSI lots
def get_psi_lots(node, psi_attr: str, week: str | int, bucket: str) -> list:
    ...

Expected behavior:

reads node.psi4demand or node.psi4supply
returns the requested bucket list
creates empty week / bucket structures only if necessary and safe
6.2 Append PSI lots
def append_psi_lots(node, psi_attr: str, week: str | int, bucket: str, lots: list) -> None:
    ...

Expected behavior:

appends lots into node.psi4supply[week][bucket]
does not overwrite existing lots unless explicitly intended
6.3 Apply capacity to one PSI bucket
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

1. read requested lots from node.psi4demand[week][capacity_type bucket]
2. run capacity-aware planning using v0r2-m2 wrapper
3. append accepted lots to node.psi4supply[week][capacity_type bucket]
4. return accepted lots, blocked lots, usage, violation
6.4 Run multi-node / multi-week PSI integration
def run_forward_push_with_capacity_psi_lists(
    *,
    nodes: list,
    weeks: list[str | int],
    scenario_id: str,
    tree_side: str,
    product_name: str,
    capacity_lookup: dict,
    capacity_types: list[str] | None = None,
) -> ForwardPushWithCapacityPsiResult:
    ...

Default capacity types:

["P", "S"]

Expected behavior:

for each week:
    for each node:
        for each capacity_type in ["P", "S"]:
            apply capacity to the node PSI bucket
            collect usage / violation
            collect accepted / blocked lots
7. Result Dataclass

Please implement:

@dataclass
class ForwardPushWithCapacityPsiResult:
    usage_records: list[CapacityUsage] = field(default_factory=list)
    violation_records: list[CapacityViolation] = field(default_factory=list)
    accepted_lots_by_key: dict = field(default_factory=dict)
    blocked_lots_by_key: dict = field(default_factory=dict)
    carryover_lots_by_key: dict = field(default_factory=dict)

Suggested key format:

(node_name, product_name, week, capacity_type)
8. Mutation Policy

Default policy:

read from:
    node.psi4demand

write to:
    node.psi4supply

do not delete from:
    node.psi4demand

Reason:

The demand-placed PSI state should remain inspectable.

The capacity-constrained executable result should appear in psi4supply.

Blocked lots should be recorded separately.

9. Missing Capacity Policy

Keep v0r2-m2 behavior:

missing capacity means unlimited capacity

Therefore:

missing capacity:
    all requested lots accepted
    no violation emitted by default

capacity exists:
    apply capacity
    emit usage
    emit violation if overflow exists
10. Carryover / Backlog Policy

For v0r2-m3, blocked lots should be recorded as carryover candidates.

Recommended structure:

carryover_lots_by_key[(node_name, product_name, week, capacity_type)] = blocked_lots

Please do not implement complex automatic rescheduling unless it is small, explicit, and test-covered.

The main requirement is:

blocked lots must not disappear
11. Smoke Runner

Please add:

pysi/runners/run_forward_push_with_capacity_psi_smoke.py

The smoke runner should:

1. Load pysi/master_data/capacity_master_sample.csv
2. Build capacity lookup
3. Create a minimal PSI node with:
   - name = MOM_CHINA
   - psi4demand["2026-W01"][P] = 120 lots
   - psi4supply["2026-W01"][P] = []
4. Run PSI list integration for P capacity
5. Confirm accepted lots are written to psi4supply
6. Confirm blocked lots are recorded
7. Export usage / violation CSV using v0r2-m2 exporters
8. Print summary to stdout

Expected output:

=== with capacity PSI smoke ===
node: MOM_CHINA
week: 2026-W01
capacity type: P
requested lots: 120
capacity: 100
accepted lots in psi4supply: 100
blocked lots: 20
usage csv: outputs/capacity/forward_push_with_capacity_psi_usage.csv
violation csv: outputs/capacity/forward_push_with_capacity_psi_violation.csv

Recommended output paths:

outputs/capacity/forward_push_with_capacity_psi_usage.csv
outputs/capacity/forward_push_with_capacity_psi_violation.csv

Please create the output directory if it does not exist.

12. Test Requirements

Please add:

tests/test_forward_push_with_capacity_psi_adapter.py

Required tests:

1. get_psi_lots reads P lots from psi4demand
2. append_psi_lots appends lots to psi4supply
3. capacity-sufficient case writes all lots to psi4supply
4. capacity-shortage case writes only accepted lots to psi4supply
5. blocked lots are recorded separately
6. missing capacity accepts all lots
7. original psi4demand remains unchanged
8. usage record is generated when capacity master exists
9. violation record is generated when capacity is exceeded
10. S capacity bucket is supported

Please also keep these tests passing:

python -m pytest tests/test_forward_push_with_capacity_planner.py
python -m pytest tests/test_capacity_master_io.py
13. Test Commands to Run

Please run at minimum:

python -m pytest tests/test_forward_push_with_capacity_psi_adapter.py
python -m pytest tests/test_capacity_master_io.py
python -m pytest tests/test_forward_push_with_capacity_planner.py
python -m pysi.runners.run_forward_push_with_capacity_psi_smoke

If reasonable, also run:

python -m pytest -q -k "capacity"

If -k "capacity" fails due to unrelated optional dependencies such as pulp, matplotlib, or dash, report that separately and do not treat it as a v0r2-m3 failure.

14. Completion Criteria

This request is complete when:

[OK] PSI adapter module exists
[OK] PSI lot read helper works
[OK] PSI lot append helper works
[OK] P capacity can be applied to psi4demand / psi4supply
[OK] S capacity can be applied to psi4demand / psi4supply
[OK] accepted lots are written to psi4supply
[OK] blocked lots are recorded separately
[OK] missing capacity remains unlimited
[OK] usage / violation records are generated
[OK] smoke runner works
[OK] tests pass
[OK] original Forward PUSH planner remains unchanged
[OK] v0r2-m1 and v0r2-m2 behavior remains compatible
15. Expected Response from Codex

After implementation, please summarize:

1. Files changed
2. Main implementation approach
3. Test commands executed
4. Test results
5. Any limitations or follow-up tasks

Please do not proceed to v0r3 allocation rule enhancement.

This request is only for:

v0r2-m3 PSI list integration