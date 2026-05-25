from __future__ import annotations

from pysi.plan.bridges.outbound_to_inbound_demand_bridge import PSI_BUCKET_INDEX, find_node_by_name
from pysi.plan.engines import allocate_markets_to_moms


def _clone_psi(psi):
    return [[list(slot) for slot in week] for week in psi]


def allocate_bridged_demand_to_moms(
    *,
    out_root,
    inbound_root,
    policy: dict,
    source_node_name: str = "supply_point",
    source_bucket: str = "S",
    clear_existing_mom_demand: bool = True,
    debug: bool = False,
):
    """Allocate already-bridged inbound demand lots to MOM nodes via existing engine policy logic.

    This is a demand-layer adapter for the smoke flow:
    inbound {source_node}.psi4demand[w][source_bucket] -> MOM*.psi4demand[w][S].

    It preserves existing ``allocate_markets_to_moms`` behavior by seeding inbound_root.psi4demand[w][S]
    from the chosen source node/bucket before calling it with source_layer='inbound_root_demand'.
    """
    source_node = find_node_by_name(inbound_root, source_node_name)
    if source_node is None:
        return out_root, inbound_root

    src_idx = PSI_BUCKET_INDEX[source_bucket]

    root_demand_backup = _clone_psi(getattr(inbound_root, "psi4demand", []) or [])

    src_psi = getattr(source_node, "psi4demand", []) or []
    root_psi = getattr(inbound_root, "psi4demand", []) or []
    W = min(len(src_psi), len(root_psi))
    for w in range(W):
        root_psi[w][PSI_BUCKET_INDEX["S"]] = list(src_psi[w][src_idx])

    out_root, inbound_root = allocate_markets_to_moms(
        out_root,
        inbound_root,
        policy=policy,
        source_layer="inbound_root_demand",
        clear_existing_mom_demand=clear_existing_mom_demand,
        debug=debug,
    )

    inbound_root.psi4demand = root_demand_backup
    return out_root, inbound_root
