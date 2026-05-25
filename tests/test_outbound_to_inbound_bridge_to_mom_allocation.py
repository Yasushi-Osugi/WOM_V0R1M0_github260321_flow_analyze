from dataclasses import dataclass, field

from pysi.plan.bridges.outbound_to_inbound_demand_bridge import bridge_outbound_to_inbound_demand
from pysi.plan.bridges.outbound_to_inbound_mom_allocation import allocate_bridged_demand_to_moms


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


def _roots_with_moms(weeks: int = 4):
    out_root = _node("out_root", weeks)
    out_supply = _node("supply_point", weeks)
    out_root.children = [out_supply]

    in_root = _node("in_root", weeks)
    in_supply = _node("supply_point", weeks)
    mom_asia = _node("MOM_ASIA", weeks)
    mom_euro = _node("MOM_EURO", weeks)
    in_supply.children = [mom_asia, mom_euro]
    in_root.children = [in_supply]

    return out_root, out_supply, in_root, in_supply, mom_asia, mom_euro


def test_bridge_a_to_mom_allocation_smoke_demand_layer_only():
    out_root, out_supply, in_root, in_supply, mom_asia, mom_euro = _roots_with_moms(weeks=2)

    jp_lot = "RT_JP_RICE_2026W40_0001"
    de_lot = "RT_DE_RICE_2026W40_0002"
    unknown_lot = "RT_UNKNOWN_RICE_2026W40_0003"  # regex extracts no 2-letter market => DEFAULT
    out_supply.psi4demand[0][3] = [jp_lot, de_lot, unknown_lot]

    # keep sentinels to verify clear_existing_mom_demand=True behavior
    mom_asia.psi4demand[0][0] = ["OLD_ASIA_LOT"]
    mom_euro.psi4demand[0][0] = ["OLD_EURO_LOT"]

    initial_supply_snapshots = {
        "out_supply": [[slot[:] for slot in week] for week in out_supply.psi4supply],
        "in_supply": [[slot[:] for slot in week] for week in in_supply.psi4supply],
        "mom_asia": [[slot[:] for slot in week] for week in mom_asia.psi4supply],
        "mom_euro": [[slot[:] for slot in week] for week in mom_euro.psi4supply],
    }

    bridge_outbound_to_inbound_demand(
        outbound_root=out_root,
        inbound_root=in_root,
        source_node_name="supply_point",
        target_node_name="supply_point",
        source_bucket="P",
        target_bucket="S",
        mode="replace",
    )

    # 12.1 Bridge A to inbound supply_point
    assert in_supply.psi4demand[0][0] == [jp_lot, de_lot, unknown_lot]

    policy = {
        "JP": ["MOM_ASIA"],
        "DE": ["MOM_EURO"],
        "DEFAULT": ["MOM_ASIA"],
    }
    allocate_bridged_demand_to_moms(
        out_root=out_root,
        inbound_root=in_root,
        policy=policy,
        source_node_name="supply_point",
        source_bucket="S",
        clear_existing_mom_demand=True,
        debug=False,
    )

    # 12.2 JP lot allocation
    assert jp_lot in mom_asia.psi4demand[0][0]
    # 12.3 DE lot allocation
    assert de_lot in mom_euro.psi4demand[0][0]
    # 12.4 DEFAULT policy allocation
    assert unknown_lot in mom_asia.psi4demand[0][0]

    # optional: clear_existing_mom_demand=True clears previous MOM demand
    assert "OLD_ASIA_LOT" not in mom_asia.psi4demand[0][0]
    assert "OLD_EURO_LOT" not in mom_euro.psi4demand[0][0]

    # 12.5 Lot_ID list invariant: string lots only
    involved_buckets = [
        in_supply.psi4demand[0][0],
        mom_asia.psi4demand[0][0],
        mom_euro.psi4demand[0][0],
    ]
    for bucket in involved_buckets:
        assert isinstance(bucket, list)
        assert all(isinstance(lot, str) for lot in bucket)

    # 12.6 No psi4supply mutation across outbound/inbound/MOM nodes
    assert out_supply.psi4supply == initial_supply_snapshots["out_supply"]
    assert in_supply.psi4supply == initial_supply_snapshots["in_supply"]
    assert mom_asia.psi4supply == initial_supply_snapshots["mom_asia"]
    assert mom_euro.psi4supply == initial_supply_snapshots["mom_euro"]
