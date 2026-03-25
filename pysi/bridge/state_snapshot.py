# \pysi\bridge\state_snapshot.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Tuple


@dataclass(frozen=True)
class LotPosition:
    lot_id: str
    product_id: str
    quantity_cpu: float
    time_bucket: str
    status: str  # "at_node" | "in_transit" | "consumed" | "unknown"
    current_node: Optional[str] = None
    from_node: Optional[str] = None
    to_node: Optional[str] = None
    current_edge: Optional[Tuple[str, str]] = None


@dataclass(frozen=True)
class LotDemandBinding:
    lot_id: str
    demand_id: str
    product_id: str
    node_id: str
    quantity_cpu: float
    time_bucket: str


InventoryMap = Dict[Tuple[str, str], float]  # (node_id, product_id) -> qty
BacklogMap = Dict[Tuple[str, str], float]  # (node_id, product_id) -> qty
EdgeFlowMap = Dict[Tuple[str, str, str], float]  # (from_node, to_node, product_id) -> qty


@dataclass(frozen=True)
class PlanningStateSnapshot:
    """
    Canonical state snapshot for bridge state-diff synthesis.

    NOTE:
    - This dataclass is frozen, but internal mapping objects are mutable containers.
    - Operational rule in bridge v0.1:
      "Do not mutate internal maps after snapshot creation."
    - Future improvement:
      switch to immutable containers (e.g., mapping proxies / persistent maps).
    """

    time_bucket: str
    lots: Dict[str, LotPosition] = field(default_factory=dict)
    inventory: InventoryMap = field(default_factory=dict)
    backlog: BacklogMap = field(default_factory=dict)
    edge_flows: EdgeFlowMap = field(default_factory=dict)
    lot_demand_bindings: Dict[Tuple[str, str], LotDemandBinding] = field(default_factory=dict)
    allocation_pairs: Dict[Tuple[str, str], float] = field(default_factory=dict)


@dataclass(frozen=True)
class SnapshotBuildContext:
    product_id: Optional[str] = None
    epsilon: float = 1e-9


def build_snapshot_from_v0r8(
    env_or_root,
    *,
    time_bucket: str,
    ctx: SnapshotBuildContext,
) -> PlanningStateSnapshot:
    """
    Minimal V0R8 snapshot extraction for bridge v0.1.
    Extracts:
      - lots
      - inventory
      - backlog
      - lot_demand_bindings

    Notes:
    - This implementation is intentionally conservative and schema-first.
    - Quantity semantics are lot-count based where per-lot quantity is unknown.
    """
    def _iter_tree(root):
        stack = [root]
        while stack:
            n = stack.pop()
            if n is None:
                continue
            yield n
            for c in getattr(n, "children", []) or []:
                stack.append(c)

    def _roots_from_env_or_root(obj) -> Iterable:
        if hasattr(obj, "prod_tree_dict_OT"):
            product = getattr(obj, "product_selected", None)
            trees = getattr(obj, "prod_tree_dict_OT", {}) or {}
            if product and product in trees:
                return [trees[product]]
            return list(trees.values())
        return [obj]

    def _week_index_from_tb(node, tb: str) -> Optional[int]:
        if len(tb) != 6 or not tb.isdigit():
            return None
        year = int(tb[:4])
        week = int(tb[4:6])
        if week <= 0:
            return None
        plan_year = getattr(node, "plan_year_st", None)
        if plan_year is None:
            return week - 1
        return max((year - int(plan_year)) * 53 + (week - 1), 0)

    lots: Dict[str, LotPosition] = {}
    inventory: InventoryMap = {}
    backlog: BacklogMap = {}
    bindings: Dict[Tuple[str, str], LotDemandBinding] = {}
    allocation_pairs: Dict[Tuple[str, str], float] = {}

    roots = _roots_from_env_or_root(env_or_root)
    for root in roots:
        for node in _iter_tree(root):
            node_name = str(getattr(node, "name", "unknown"))
            wk = _week_index_from_tb(node, time_bucket)

            psi_d = getattr(node, "psi4demand", None)
            psi_s = getattr(node, "psi4supply", None)

            week_d = psi_d[wk] if isinstance(psi_d, list) and wk is not None and wk < len(psi_d) else None
            week_s = psi_s[wk] if isinstance(psi_s, list) and wk is not None and wk < len(psi_s) else None
            if not isinstance(week_d, list):
                week_d = [[], [], [], []]
            if not isinstance(week_s, list):
                week_s = [[], [], [], []]

            product_id = str(getattr(node, "sku_name", None) or ctx.product_id or "UNKNOWN_PRODUCT")

            inv_lots = week_s[2] if len(week_s) > 2 and isinstance(week_s[2], list) else []
            backlog_lots = week_d[1] if len(week_d) > 1 and isinstance(week_d[1], list) else []
            prod_or_ship_lots = week_d[3] if len(week_d) > 3 and isinstance(week_d[3], list) else []

            inventory[(node_name, product_id)] = float(len(inv_lots))
            backlog[(node_name, product_id)] = float(len(backlog_lots))

            for lot_id in inv_lots:
                lots[str(lot_id)] = LotPosition(
                    lot_id=str(lot_id),
                    product_id=product_id,
                    quantity_cpu=1.0,
                    time_bucket=time_bucket,
                    status="at_node",
                    current_node=node_name,
                )

            # fallback lot presence for planned/progression lots
            for lot_id in prod_or_ship_lots:
                k = str(lot_id)
                if k in lots:
                    continue
                parent = getattr(node, "parent", None)
                from_node = getattr(parent, "name", None) if parent is not None else None
                lots[k] = LotPosition(
                    lot_id=k,
                    product_id=product_id,
                    quantity_cpu=1.0,
                    time_bucket=time_bucket,
                    status="in_transit",
                    from_node=str(from_node) if from_node else None,
                    to_node=node_name,
                    current_edge=(str(from_node), node_name) if from_node else None,
                )

    # Optional binding sources from env object
    src_bindings = getattr(env_or_root, "lot_demand_bindings", None)
    if isinstance(src_bindings, dict):
        for key, value in src_bindings.items():
            lot_id, demand_id = key if isinstance(key, tuple) and len(key) == 2 else (None, None)
            if not lot_id or not demand_id:
                continue
            if isinstance(value, LotDemandBinding):
                bindings[(str(lot_id), str(demand_id))] = value
            elif isinstance(value, dict):
                bindings[(str(lot_id), str(demand_id))] = LotDemandBinding(
                    lot_id=str(lot_id),
                    demand_id=str(demand_id),
                    product_id=str(value.get("product_id", ctx.product_id or "UNKNOWN_PRODUCT")),
                    node_id=str(value.get("node_id", "unknown")),
                    quantity_cpu=float(value.get("quantity_cpu", 1.0)),
                    time_bucket=str(value.get("time_bucket", time_bucket)),
                )

    src_alloc = getattr(env_or_root, "allocation_pairs", None)
    if isinstance(src_alloc, dict):
        for key, qty in src_alloc.items():
            if not (isinstance(key, tuple) and len(key) == 2):
                continue
            allocation_pairs[(str(key[0]), str(key[1]))] = float(qty)

    return PlanningStateSnapshot(
        time_bucket=time_bucket,
        lots=lots,
        inventory=inventory,
        backlog=backlog,
        edge_flows={},
        lot_demand_bindings=bindings,
        allocation_pairs=allocation_pairs,
    )
