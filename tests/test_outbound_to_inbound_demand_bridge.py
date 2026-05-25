from dataclasses import dataclass, field

import pytest

from pysi.plan.bridges.outbound_to_inbound_demand_bridge import bridge_outbound_to_inbound_demand


@dataclass
class MockPlanNode:
    name: str
    children: list = field(default_factory=list)
    psi4demand: list = field(default_factory=list)
    psi4supply: list = field(default_factory=list)


def _node(name: str, weeks: int = 4) -> MockPlanNode:
    return MockPlanNode(
        name=name,
        psi4demand=[[[], [], [], []] for _ in range(weeks)],
        psi4supply=[[[], [], [], []] for _ in range(weeks)],
    )


def _roots(weeks: int = 4):
    out_root = _node("out_root", weeks)
    out_supply = _node("supply_point", weeks)
    out_root.children = [out_supply]

    in_root = _node("in_root", weeks)
    in_supply = _node("supply_point", weeks)
    in_root.children = [in_supply]
    return out_root, out_supply, in_root, in_supply


def test_basic_bridge_copies_p_to_s_lot_ids():
    out_root, out_supply, in_root, in_supply = _roots()
    out_supply.psi4demand[0][3] = ["LOT_A", "LOT_B"]

    bridge_outbound_to_inbound_demand(outbound_root=out_root, inbound_root=in_root)

    assert in_supply.psi4demand[0][0] == ["LOT_A", "LOT_B"]


def test_source_bucket_not_modified():
    out_root, out_supply, in_root, _ = _roots()
    out_supply.psi4demand[0][3] = ["LOT_A", "LOT_B"]

    bridge_outbound_to_inbound_demand(outbound_root=out_root, inbound_root=in_root)

    assert out_supply.psi4demand[0][3] == ["LOT_A", "LOT_B"]


def test_replace_mode_is_idempotent():
    out_root, out_supply, in_root, in_supply = _roots()
    out_supply.psi4demand[0][3] = ["LOT_A", "LOT_B"]

    bridge_outbound_to_inbound_demand(outbound_root=out_root, inbound_root=in_root, mode="replace")
    bridge_outbound_to_inbound_demand(outbound_root=out_root, inbound_root=in_root, mode="replace")

    assert in_supply.psi4demand[0][0] == ["LOT_A", "LOT_B"]


def test_append_mode_appends_without_clearing_target():
    out_root, out_supply, in_root, in_supply = _roots()
    in_supply.psi4demand[0][0] = ["OLD_LOT"]
    out_supply.psi4demand[0][3] = ["LOT_A"]

    bridge_outbound_to_inbound_demand(outbound_root=out_root, inbound_root=in_root, mode="append")

    assert in_supply.psi4demand[0][0] == ["OLD_LOT", "LOT_A"]


def test_dedupe_append_mode_avoids_duplicates():
    out_root, out_supply, in_root, in_supply = _roots()
    in_supply.psi4demand[0][0] = ["LOT_A"]
    out_supply.psi4demand[0][3] = ["LOT_A", "LOT_B"]

    result = bridge_outbound_to_inbound_demand(outbound_root=out_root, inbound_root=in_root, mode="dedupe_append")

    assert in_supply.psi4demand[0][0] == ["LOT_A", "LOT_B"]
    assert result.duplicate_lot_ids == ["LOT_A"]


def test_bridge_leadtime_weeks_shifts_target_week():
    out_root, out_supply, in_root, in_supply = _roots(weeks=3)
    out_supply.psi4demand[0][3] = ["LOT_A"]

    bridge_outbound_to_inbound_demand(outbound_root=out_root, inbound_root=in_root, bridge_leadtime_weeks=1)

    assert in_supply.psi4demand[1][0] == ["LOT_A"]


def test_missing_source_node_returns_safe_result():
    _, _, in_root, _ = _roots()
    out_root = _node("out_root")

    result = bridge_outbound_to_inbound_demand(outbound_root=out_root, inbound_root=in_root)

    assert result.missing_source_node is True


def test_missing_target_node_returns_safe_result():
    out_root, _, _, _ = _roots()
    in_root = _node("in_root")

    result = bridge_outbound_to_inbound_demand(outbound_root=out_root, inbound_root=in_root)

    assert result.missing_target_node is True


def test_target_bucket_contains_only_string_lot_ids():
    out_root, out_supply, in_root, in_supply = _roots()
    out_supply.psi4demand[0][3] = ["LOT_A", "LOT_B"]

    bridge_outbound_to_inbound_demand(outbound_root=out_root, inbound_root=in_root)

    assert all(isinstance(item, str) for item in in_supply.psi4demand[0][0])


def test_invalid_bucket_name_raises_value_error_deterministically():
    out_root, _, in_root, _ = _roots()
    with pytest.raises(ValueError):
        bridge_outbound_to_inbound_demand(
            outbound_root=out_root,
            inbound_root=in_root,
            source_bucket="X",
        )
