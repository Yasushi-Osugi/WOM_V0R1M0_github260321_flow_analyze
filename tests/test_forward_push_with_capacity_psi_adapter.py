from __future__ import annotations

from pysi.planning.capacity_master import CapacityMasterRecord, build_capacity_lookup
from pysi.planning.forward_push_with_capacity_psi_adapter import (
    PSI_BUCKET_INDEX,
    append_psi_lots,
    get_psi_lots,
    run_forward_push_with_capacity_psi_lists,
)


class DummyNode:
    def __init__(self, name: str):
        self.name = name
        self.psi4demand = {}
        self.psi4supply = {}


def _mk_lookup(records: list[CapacityMasterRecord]):
    return build_capacity_lookup(records)


def test_get_psi_lots_reads_p_from_demand():
    node = DummyNode("N1")
    week = "2026-W01"
    node.psi4demand[week] = [[], [], [], ["P1", "P2"]]

    lots = get_psi_lots(node, "psi4demand", week, "P")

    assert lots == ["P1", "P2"]


def test_append_psi_lots_appends_to_supply():
    node = DummyNode("N1")
    week = "2026-W01"
    node.psi4supply[week] = [[], [], [], ["EXISTING"]]

    append_psi_lots(node, "psi4supply", week, "P", ["N1", "N2"])

    assert node.psi4supply[week][PSI_BUCKET_INDEX["P"]] == ["EXISTING", "N1", "N2"]


def test_capacity_sufficient_writes_all_to_supply_and_generates_usage():
    node = DummyNode("MOM_CHINA")
    week = "2026-W01"
    node.psi4demand[week] = [[], [], [], ["P1", "P2", "P3"]]
    node.psi4supply[week] = [[], [], [], []]
    lookup = _mk_lookup([
        CapacityMasterRecord("BASE", "INBOUND", "MOM_CHINA", "PROD", week, "P", 10),
    ])

    result = run_forward_push_with_capacity_psi_lists(
        nodes=[node], weeks=[week], scenario_id="BASE", tree_side="INBOUND", product_name="PROD", capacity_lookup=lookup, capacity_types=["P"]
    )

    key = ("MOM_CHINA", "PROD", week, "P")
    assert node.psi4supply[week][3] == ["P1", "P2", "P3"]
    assert result.blocked_lots_by_key[key] == []
    assert len(result.usage_records) == 1


def test_capacity_shortage_writes_only_accepted_and_records_blocked_and_violation():
    node = DummyNode("MOM_CHINA")
    week = "2026-W01"
    lots = [f"P{i}" for i in range(1, 6)]
    node.psi4demand[week] = [[], [], [], lots.copy()]
    node.psi4supply[week] = [[], [], [], []]
    lookup = _mk_lookup([
        CapacityMasterRecord("BASE", "INBOUND", "MOM_CHINA", "PROD", week, "P", 3),
    ])

    result = run_forward_push_with_capacity_psi_lists(
        nodes=[node], weeks=[week], scenario_id="BASE", tree_side="INBOUND", product_name="PROD", capacity_lookup=lookup, capacity_types=["P"]
    )

    key = ("MOM_CHINA", "PROD", week, "P")
    assert node.psi4supply[week][3] == ["P1", "P2", "P3"]
    assert result.blocked_lots_by_key[key] == ["P4", "P5"]
    assert result.carryover_lots_by_key[key] == ["P4", "P5"]
    assert len(result.violation_records) == 1


def test_missing_capacity_accepts_all_and_no_usage_violation():
    node = DummyNode("N1")
    week = "2026-W01"
    node.psi4demand[week] = [[], [], [], ["P1", "P2"]]
    node.psi4supply[week] = [[], [], [], []]

    result = run_forward_push_with_capacity_psi_lists(
        nodes=[node], weeks=[week], scenario_id="BASE", tree_side="INBOUND", product_name="PROD", capacity_lookup={}, capacity_types=["P"]
    )

    key = ("N1", "PROD", week, "P")
    assert node.psi4supply[week][3] == ["P1", "P2"]
    assert result.blocked_lots_by_key[key] == []
    assert result.usage_records == []
    assert result.violation_records == []


def test_original_psi4demand_remains_unchanged():
    node = DummyNode("N1")
    week = "2026-W01"
    original = ["P1", "P2", "P3"]
    node.psi4demand[week] = [[], [], [], original.copy()]
    node.psi4supply[week] = [[], [], [], []]

    run_forward_push_with_capacity_psi_lists(
        nodes=[node], weeks=[week], scenario_id="BASE", tree_side="INBOUND", product_name="PROD", capacity_lookup={}, capacity_types=["P"]
    )

    assert node.psi4demand[week][3] == original


def test_s_capacity_bucket_supported():
    node = DummyNode("DAD_US")
    week = "2026-W01"
    node.psi4demand[week] = [["S1", "S2", "S3"], [], [], []]
    node.psi4supply[week] = [[], [], [], []]
    lookup = _mk_lookup([
        CapacityMasterRecord("BASE", "OUTBOUND", "DAD_US", "PROD", week, "S", 2),
    ])

    result = run_forward_push_with_capacity_psi_lists(
        nodes=[node], weeks=[week], scenario_id="BASE", tree_side="OUTBOUND", product_name="PROD", capacity_lookup=lookup, capacity_types=["S"]
    )

    key = ("DAD_US", "PROD", week, "S")
    assert node.psi4supply[week][0] == ["S1", "S2"]
    assert result.blocked_lots_by_key[key] == ["S3"]
