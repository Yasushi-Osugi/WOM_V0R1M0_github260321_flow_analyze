from __future__ import annotations

from pathlib import Path

import pytest

from pysi.capacity import run_capacity_report_hook


class HookTreeNode:
    def __init__(self, name: str):
        self.name = name
        self.children = []
        self.psi4demand = {}
        self.psi4supply = {}

    def add_child(self, child):
        self.children.append(child)

    def init_week(self, week):
        self.psi4demand[week] = [[], [], [], []]
        self.psi4supply[week] = [[], [], [], []]


def _write_capacity_master(path: Path, rows: list[str]) -> None:
    header = (
        "scenario_id,node_name,product_name,week,capacity_type,capacity_qty,"
        "cap_mode,unit,priority,calendar_id,comment\n"
    )
    path.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")


def test_capacity_report_hook_disabled_noop():
    usage_records, violation_records = run_capacity_report_hook(
        enabled=False,
        scenario_id="BASE",
        product_name="TEST_PRODUCT",
        weeks=["2026-W01"],
    )
    assert usage_records == []
    assert violation_records == []


def test_capacity_report_hook_missing_master_non_strict(tmp_path):
    usage_records, violation_records = run_capacity_report_hook(
        enabled=True,
        scenario_id="BASE",
        product_name="TEST_PRODUCT",
        weeks=["2026-W01"],
        capacity_master_path=tmp_path / "missing_capacity_master.csv",
        strict_capacity_master=False,
    )
    assert usage_records == []
    assert violation_records == []


def test_capacity_report_hook_missing_master_strict(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_capacity_report_hook(
            enabled=True,
            scenario_id="BASE",
            product_name="TEST_PRODUCT",
            weeks=["2026-W01"],
            capacity_master_path=tmp_path / "missing_capacity_master.csv",
            strict_capacity_master=True,
        )


def test_capacity_report_hook_outbound_tree_exports(tmp_path):
    week = "2026-W01"
    mom = HookTreeNode("MOM_TEST")
    dad = HookTreeNode("DAD_TEST")
    mkt = HookTreeNode("MKT_TEST")
    mom.add_child(dad)
    dad.add_child(mkt)
    for node in (mom, dad, mkt):
        node.init_week(week)

    mom.psi4demand[week][3] = ["P1", "P2", "P3", "P4", "P5"]
    dad.psi4supply[week][2] = ["I1", "I2", "I3", "I4"]
    mkt.psi4demand[week][0] = ["S1", "S2", "S3", "S4"]

    capacity_master_path = tmp_path / "capacity_master.csv"
    _write_capacity_master(
        capacity_master_path,
        [
            "BASE,MOM_TEST,TEST_PRODUCT,2026-W01,P,3,soft,LOT,100,STD_CAL,test MOM P cap",
            "BASE,DAD_TEST,TEST_PRODUCT,2026-W01,I,3,soft,LOT,100,STD_CAL,test DAD I cap",
            "BASE,MKT_TEST,TEST_PRODUCT,2026-W01,S,2,soft,LOT,100,STD_CAL,test MKT S cap",
        ],
    )

    out_dir = tmp_path / "capacity_out"
    usage_records, violation_records = run_capacity_report_hook(
        enabled=True,
        scenario_id="BASE",
        product_name="TEST_PRODUCT",
        weeks=[week],
        outbound_root=mom,
        capacity_master_path=capacity_master_path,
        output_dir=out_dir,
    )

    assert (out_dir / "capacity_usage.csv").exists()
    assert (out_dir / "capacity_violation.csv").exists()
    assert any(r.node_name == "MOM_TEST" and r.capacity_type == "P" for r in usage_records)
    assert any(r.node_name == "DAD_TEST" and r.capacity_type == "I" for r in usage_records)
    assert any(r.node_name == "MKT_TEST" and r.capacity_type == "S" for r in usage_records)
    assert violation_records


def test_capacity_report_hook_inbound_tree_exports(tmp_path):
    week = "2026-W01"
    mom = HookTreeNode("MOM_TEST")
    raw_a = HookTreeNode("RAW_A_TEST")
    raw_b = HookTreeNode("RAW_B_TEST")
    mom.add_child(raw_a)
    mom.add_child(raw_b)
    for node in (mom, raw_a, raw_b):
        node.init_week(week)

    raw_a.psi4demand[week][3] = ["PA1", "PA2", "PA3", "PA4", "PA5"]
    raw_b.psi4demand[week][0] = ["SB1", "SB2", "SB3", "SB4"]
    mom.psi4supply[week][2] = ["IM1", "IM2", "IM3", "IM4"]

    capacity_master_path = tmp_path / "capacity_master.csv"
    _write_capacity_master(
        capacity_master_path,
        [
            "BASE,RAW_A_TEST,TEST_PRODUCT,2026-W01,P,3,soft,LOT,100,STD_CAL,test RAW_A P cap",
            "BASE,RAW_B_TEST,TEST_PRODUCT,2026-W01,S,2,soft,LOT,100,STD_CAL,test RAW_B S cap",
            "BASE,MOM_TEST,TEST_PRODUCT,2026-W01,I,3,soft,LOT,100,STD_CAL,test MOM I cap",
        ],
    )

    out_dir = tmp_path / "capacity_in"
    usage_records, violation_records = run_capacity_report_hook(
        enabled=True,
        scenario_id="BASE",
        product_name="TEST_PRODUCT",
        weeks=[week],
        inbound_root=mom,
        capacity_master_path=capacity_master_path,
        output_dir=out_dir,
    )

    assert (out_dir / "capacity_usage.csv").exists()
    assert (out_dir / "capacity_violation.csv").exists()
    assert any(r.node_name == "RAW_A_TEST" and r.capacity_type == "P" for r in usage_records)
    assert any(r.node_name == "RAW_B_TEST" and r.capacity_type == "S" for r in usage_records)
    assert any(r.node_name == "MOM_TEST" and r.capacity_type == "I" for r in usage_records)
    assert violation_records


def test_capacity_report_hook_combined_outbound_inbound(tmp_path):
    week = "2026-W01"

    outbound_mom = HookTreeNode("MOM_TEST")
    dad = HookTreeNode("DAD_TEST")
    mkt = HookTreeNode("MKT_TEST")
    outbound_mom.add_child(dad)
    dad.add_child(mkt)

    inbound_mom = HookTreeNode("MOM_TEST")
    raw_a = HookTreeNode("RAW_A_TEST")
    raw_b = HookTreeNode("RAW_B_TEST")
    inbound_mom.add_child(raw_a)
    inbound_mom.add_child(raw_b)

    for node in (outbound_mom, dad, mkt, inbound_mom, raw_a, raw_b):
        node.init_week(week)

    outbound_mom.psi4demand[week][3] = ["P1", "P2", "P3", "P4", "P5"]
    dad.psi4supply[week][2] = ["I1", "I2", "I3", "I4"]
    mkt.psi4demand[week][0] = ["S1", "S2", "S3", "S4"]

    raw_a.psi4demand[week][3] = ["PA1", "PA2", "PA3", "PA4", "PA5"]
    raw_b.psi4demand[week][0] = ["SB1", "SB2", "SB3", "SB4"]
    inbound_mom.psi4supply[week][2] = ["IM1", "IM2", "IM3", "IM4"]

    capacity_master_path = tmp_path / "capacity_master.csv"
    _write_capacity_master(
        capacity_master_path,
        [
            "BASE,MOM_TEST,TEST_PRODUCT,2026-W01,P,3,soft,LOT,100,STD_CAL,test MOM P cap",
            "BASE,DAD_TEST,TEST_PRODUCT,2026-W01,I,3,soft,LOT,100,STD_CAL,test DAD I cap",
            "BASE,MKT_TEST,TEST_PRODUCT,2026-W01,S,2,soft,LOT,100,STD_CAL,test MKT S cap",
            "BASE,RAW_A_TEST,TEST_PRODUCT,2026-W01,P,3,soft,LOT,100,STD_CAL,test RAW_A P cap",
            "BASE,RAW_B_TEST,TEST_PRODUCT,2026-W01,S,2,soft,LOT,100,STD_CAL,test RAW_B S cap",
            "BASE,MOM_TEST,TEST_PRODUCT,2026-W01,I,3,soft,LOT,100,STD_CAL,test MOM I cap",
        ],
    )

    out_dir = tmp_path / "capacity_combined"
    usage_records, violation_records = run_capacity_report_hook(
        enabled=True,
        scenario_id="BASE",
        product_name="TEST_PRODUCT",
        weeks=[week],
        outbound_root=outbound_mom,
        inbound_root=inbound_mom,
        capacity_master_path=capacity_master_path,
        output_dir=out_dir,
    )

    assert {r.tree_side for r in usage_records} == {"OUTBOUND", "INBOUND"}
    assert {r.tree_side for r in violation_records} == {"OUTBOUND", "INBOUND"}
    assert (out_dir / "capacity_usage.csv").exists()
    assert (out_dir / "capacity_violation.csv").exists()
