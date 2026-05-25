# Codex Request: Implement With-Capacity PSI Engine v0r2-m2 Capacity I/O

## 1. Background

We are working on:

```text
feature/with-capacity-psi-engine-v0r2

The previous v0r2-m1 implementation added the standalone Forward PUSH with Capacity planner MVP.

The current request is for:

v0r2-m2:
    capacity_master.csv loader
    CapacityUsage / CapacityViolation records
    usage / violation CSV output

Please read the design memo first:

docs/design/with_capacity_forward_push_planning_v0r2_m2_capacity_io.md

Also keep compatibility with the existing v0r2-m1 planner implementation.

2. Main Objective

Implement the capacity I/O layer for Forward PUSH with Capacity Planning.

The goal is to make the planner data-ready by adding:

capacity master CSV input
capacity lookup
capacity usage records
capacity violation records
CSV output for usage and violations

This request does not require deep integration with WOM Node.psi4demand / psi4supply yet.

That will be v0r2-m3.

3. Most Important Constraints

Please follow these constraints:

1. Do not modify the original Forward PUSH planner behavior.
2. Do not introduce GUI integration.
3. Do not implement advanced allocation rules.
4. Do not implement PULL integration.
5. Do not implement cost/profit simulation.
6. Keep v0r2-m1 planner tests passing.
7. Keep the implementation small and testable.

This is a data I/O milestone, not an optimization milestone.

4. Files to Add or Update

Suggested files:

pysi/planning/capacity_master.py
pysi/planning/capacity_io.py
pysi/runners/run_forward_push_with_capacity_io_smoke.py
tests/test_capacity_master_io.py
tests/test_forward_push_with_capacity_io.py
pysi/master_data/capacity_master_sample.csv

If the repository has a better existing convention, please follow it.

Avoid broad refactoring.

5. capacity_master.csv

Please add a sample CSV.

Suggested path:

pysi/master_data/capacity_master_sample.csv

Header:

scenario_id,tree_side,node_name,product_name,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment

Example rows:

scenario_id,tree_side,node_name,product_name,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
BASE,INBOUND,MOM_CHINA,IPHONE_NM_2028_BASE,2026-W01,P,100,soft,LOT,100,STD_CAL,weekly production capacity
BASE,OUTBOUND,DAD_US,IPHONE_NM_2028_BASE,2026-W01,S,80,soft,LOT,100,STD_CAL,weekly shipping capacity
BASE,OUTBOUND,DAD_US,IPHONE_NM_2028_BASE,2026-W01,I,500,soft,LOT,100,STD_CAL,inventory absorption capacity
BASE,INBOUND,MOM_CHINA,*,2026-W02,P,200,soft,LOT,100,STD_CAL,wildcard product capacity
6. Data Structures

Please implement small dataclasses.

6.1 CapacityMasterRecord
@dataclass
class CapacityMasterRecord:
    scenario_id: str
    tree_side: str
    node_name: str
    product_name: str
    week: str
    capacity_type: str
    capacity_qty: int
    cap_mode: str = "soft"
    unit: str = "LOT"
    priority: int = 100
    calendar_id: str = ""
    comment: str = ""
6.2 CapacityUsage
@dataclass
class CapacityUsage:
    scenario_id: str
    tree_side: str
    node_name: str
    product_name: str
    week: str
    capacity_type: str
    capacity_qty: int
    used_qty: int
    used_lot_ids: list[str] = field(default_factory=list)

    @property
    def remaining_qty(self) -> int:
        return max(self.capacity_qty - self.used_qty, 0)

    @property
    def utilization(self) -> float:
        if self.capacity_qty <= 0:
            return 0.0
        return self.used_qty / self.capacity_qty
6.3 CapacityViolation
@dataclass
class CapacityViolation:
    scenario_id: str
    tree_side: str
    node_name: str
    product_name: str
    week: str
    capacity_type: str
    cap_mode: str
    capacity_qty: int
    required_qty: int
    overflow_qty: int
    violation_type: str
    overflow_lot_ids: list[str] = field(default_factory=list)
    action: str = "CARRY_OVER"

Please adapt imports and typing to existing project style.

7. Loader Requirements

Please implement a CSV loader such as:

def load_capacity_master_csv(path: str | Path) -> list[CapacityMasterRecord]:
    ...

Requirements:

1. Read UTF-8 CSV.
2. Parse capacity_qty as int.
3. Parse priority as int.
4. Default cap_mode to "soft" if missing.
5. Default unit to "LOT" if missing.
6. Default priority to 100 if missing.
7. Strip whitespace from string fields.
8. Validate capacity_type is one of P / S / I.
9. Validate cap_mode is one of soft / hard.

Please keep error handling simple but clear.

8. Lookup Requirements

Please implement lookup helpers.

Suggested functions:

def build_capacity_lookup(records: list[CapacityMasterRecord]) -> dict:
    ...

def get_capacity_record(
    lookup: dict,
    *,
    scenario_id: str,
    tree_side: str,
    node_name: str,
    product_name: str,
    week: str,
    capacity_type: str,
) -> CapacityMasterRecord | None:
    ...

Lookup order:

1. exact product match
2. product_name="*" wildcard
3. None

Missing capacity means unlimited capacity by default.

Do not block lots if no capacity record exists.

9. Export Requirements
9.1 capacity_usage.csv

Please implement:

def export_capacity_usage_csv(
    usages: list[CapacityUsage],
    path: str | Path,
) -> None:
    ...

Header:

scenario_id,tree_side,node_name,product_name,week,capacity_type,capacity_qty,used_qty,remaining_qty,utilization,used_lot_ids

used_lot_ids should be pipe-separated.

Example:

LOT001|LOT002|LOT003
9.2 capacity_violation.csv

Please implement:

def export_capacity_violation_csv(
    violations: list[CapacityViolation],
    path: str | Path,
) -> None:
    ...

Header:

scenario_id,tree_side,node_name,product_name,week,capacity_type,cap_mode,capacity_qty,required_qty,overflow_qty,violation_type,overflow_lot_ids,action

overflow_lot_ids should be pipe-separated.

10. Lot ID Helper

Please implement or reuse a safe lot ID helper.

Required behavior:

def _lot_id(lot: Any) -> str:
    if isinstance(lot, dict):
        return str(lot.get("lot_id", lot))
    return str(lot)

This is important because lots may be represented either as dictionaries or as string lot IDs.

11. Integration with v0r2-m1 Planner

Please add a small helper or wrapper that can use loaded capacity records with the existing v0r2-m1 planner.

Conceptual function:

def run_forward_push_with_capacity_from_master(
    *,
    scenario_id: str,
    tree_side: str,
    node_name: str,
    product_name: str,
    week: str,
    capacity_type: str,
    requested_lots: list,
    capacity_lookup: dict,
) -> tuple[result, CapacityUsage | None, CapacityViolation | None]:
    ...

Expected behavior:

capacity record found:
    use capacity_qty and cap_mode

capacity record not found:
    treat as unlimited capacity
    all lots accepted
    no violation by default

Please keep this wrapper small.

Do not integrate into real WOM Node.psi4demand / psi4supply yet.

12. Smoke Runner

Please add a smoke runner:

pysi/runners/run_forward_push_with_capacity_io_smoke.py

The runner should:

1. Load pysi/master_data/capacity_master_sample.csv
2. Create 120 requested lots for MOM_CHINA / IPHONE_NM_2028_BASE / 2026-W01 / P
3. Use capacity 100 from the CSV
4. Run the v0r2-m1 planner or wrapper
5. Export usage CSV
6. Export violation CSV
7. Print summary

Expected output:

=== with capacity IO smoke ===
capacity master records: 4
requested lots: 120
capacity: 100
accepted lots: 100
blocked lots: 20
usage csv: outputs/capacity/forward_push_with_capacity_usage.csv
violation csv: outputs/capacity/forward_push_with_capacity_violation.csv

Recommended output paths:

outputs/capacity/forward_push_with_capacity_usage.csv
outputs/capacity/forward_push_with_capacity_violation.csv

Please create the output directory if it does not exist.

13. Test Requirements

Please add tests.

Suggested test file:

tests/test_capacity_master_io.py

Required tests:

1. load_capacity_master_csv loads records correctly
2. capacity_qty and priority are parsed as int
3. exact capacity lookup works
4. product wildcard fallback works
5. missing capacity returns None
6. missing capacity is treated as unlimited by wrapper
7. capacity_usage.csv export writes expected header
8. capacity_violation.csv export writes expected header
9. lot ID export handles both dict lots and string lot IDs
10. zero capacity creates blocked lots and violation

Please also ensure the previous v0r2-m1 tests still pass:

python -m pytest tests/test_forward_push_with_capacity_planner.py
14. Test Commands to Run

Please run at minimum:

python -m pytest tests/test_capacity_master_io.py
python -m pytest tests/test_forward_push_with_capacity_planner.py
python -m pysi.runners.run_forward_push_with_capacity_io_smoke

If reasonable, also run:

python -m pytest -q -k "capacity"

Please report the test results.

15. Completion Criteria

This request is complete when:

[OK] capacity_master_sample.csv exists
[OK] capacity master loader exists
[OK] capacity lookup supports exact match
[OK] capacity lookup supports product wildcard
[OK] missing capacity means unlimited capacity by default
[OK] CapacityUsage dataclass exists
[OK] CapacityViolation dataclass exists
[OK] usage CSV export works
[OK] violation CSV export works
[OK] smoke runner works
[OK] tests pass
[OK] v0r2-m1 planner behavior remains compatible
16. Expected Response from Codex

After implementation, please summarize:

1. Files changed
2. Main implementation approach
3. Test commands executed
4. Test results
5. Any limitations or follow-up tasks

Please do not proceed to v0r2-m3 or v0r3 in this request.

This request is only for:

v0r2-m2 capacity I/O layer