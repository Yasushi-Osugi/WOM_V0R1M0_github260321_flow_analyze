from __future__ import annotations

from pathlib import Path

from pysi.capacity import run_capacity_report_hook


class SmokeTreeNode:
    def __init__(self, name: str):
        self.name = name
        self.children = []
        self.psi4demand = {}
        self.psi4supply = {}

    def add_child(self, child) -> None:
        self.children.append(child)

    def init_week(self, week: str) -> None:
        self.psi4demand[week] = [[], [], [], []]
        self.psi4supply[week] = [[], [], [], []]


def _build_outbound_tree(week: str) -> SmokeTreeNode:
    mom = SmokeTreeNode("MOM_TEST")
    dad = SmokeTreeNode("DAD_TEST")
    mkt = SmokeTreeNode("MKT_TEST")
    mom.add_child(dad)
    dad.add_child(mkt)

    for node in (mom, dad, mkt):
        node.init_week(week)

    mom.psi4demand[week][3] = ["P1", "P2", "P3", "P4", "P5"]
    dad.psi4supply[week][2] = ["I1", "I2", "I3", "I4"]
    mkt.psi4demand[week][0] = ["S1", "S2", "S3", "S4"]
    return mom


def _build_inbound_tree(week: str) -> SmokeTreeNode:
    mom_in = SmokeTreeNode("MOM_IN_TEST")
    raw_a = SmokeTreeNode("RAW_A_TEST")
    raw_b = SmokeTreeNode("RAW_B_TEST")
    mom_in.add_child(raw_a)
    mom_in.add_child(raw_b)

    for node in (mom_in, raw_a, raw_b):
        node.init_week(week)

    raw_a.psi4demand[week][3] = ["PA1", "PA2", "PA3", "PA4", "PA5"]
    raw_b.psi4demand[week][0] = ["SB1", "SB2", "SB3", "SB4"]
    mom_in.psi4supply[week][2] = ["IM1", "IM2", "IM3", "IM4"]
    return mom_in


def _write_capacity_master_smoke_csv(path: Path) -> None:
    rows = [
        "BASE,MOM_TEST,TEST_PRODUCT,2026-W01,P,3,soft,LOT,100,STD_CAL,smoke outbound MOM P cap",
        "BASE,DAD_TEST,TEST_PRODUCT,2026-W01,I,3,soft,LOT,100,STD_CAL,smoke outbound DAD I cap",
        "BASE,MKT_TEST,TEST_PRODUCT,2026-W01,S,2,soft,LOT,100,STD_CAL,smoke outbound MKT S cap",
        "BASE,RAW_A_TEST,TEST_PRODUCT,2026-W01,P,3,soft,LOT,100,STD_CAL,smoke inbound RAW_A P cap",
        "BASE,RAW_B_TEST,TEST_PRODUCT,2026-W01,S,2,soft,LOT,100,STD_CAL,smoke inbound RAW_B S cap",
        "BASE,MOM_IN_TEST,TEST_PRODUCT,2026-W01,I,3,soft,LOT,100,STD_CAL,smoke inbound MOM I cap",
    ]
    header = (
        "scenario_id,node_name,product_name,week,capacity_type,capacity_qty,"
        "cap_mode,unit,priority,calendar_id,comment\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")


def run_smoke_runner_with_optional_capacity_report(
    output_dir: str | Path = "outputs/capacity/runner",
    *,
    enable_capacity_report: bool = False,
    capacity_master_path: str | Path | None = None,
) -> tuple[int, int]:
    """Run a small WOM-like sample path with an optional capacity report hook.

    This wrapper is intentionally lightweight and disabled by default so that
    existing runner behavior is unchanged unless explicitly opted in.
    """
    scenario_id = "BASE"
    product_name = "TEST_PRODUCT"
    week = "2026-W01"
    weeks = [week]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    outbound_root = _build_outbound_tree(week)
    inbound_root = _build_inbound_tree(week)

    usage_records = []
    violation_records = []

    if enable_capacity_report:
        usage_records, violation_records = run_capacity_report_hook(
            enabled=True,
            scenario_id=scenario_id,
            product_name=product_name,
            weeks=weeks,
            outbound_root=outbound_root,
            inbound_root=inbound_root,
            capacity_master_path=capacity_master_path,
            output_dir=output_dir,
            strict_capacity_master=False,
        )

    return len(usage_records), len(violation_records)


def main(output_dir: str | Path = "outputs/capacity/smoke") -> tuple[int, int]:
    scenario_id = "BASE"
    product_name = "TEST_PRODUCT"
    week = "2026-W01"
    weeks = [week]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    outbound_root = _build_outbound_tree(week)
    inbound_root = _build_inbound_tree(week)

    capacity_master_path = output_dir / "capacity_master_smoke.csv"
    _write_capacity_master_smoke_csv(capacity_master_path)

    usage_count, violation_count = run_smoke_runner_with_optional_capacity_report(
        output_dir=output_dir,
        enable_capacity_report=True,
        capacity_master_path=capacity_master_path,
    )

    print("Capacity report hook smoke runner completed.")
    print(f"Scenario: {scenario_id}")
    print(f"Product: {product_name}")
    print(f"Weeks: {', '.join(weeks)}")
    print()
    print(f"Usage records: {usage_count}")
    print(f"Violation records: {violation_count}")

    if usage_count == 0 and violation_count == 0:
        print("WARNING: No capacity usage or violation records were generated.")

    print()
    print("Output files:")
    print(f"  {output_dir / 'capacity_usage.csv'}")
    print(f"  {output_dir / 'capacity_violation.csv'}")

    return usage_count, violation_count


if __name__ == "__main__":
    main()
