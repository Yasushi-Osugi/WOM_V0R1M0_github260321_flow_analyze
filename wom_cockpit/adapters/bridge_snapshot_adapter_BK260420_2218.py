from __future__ import annotations

from collections import defaultdict

from wom_cockpit.domain.state_snapshot import (
    StateSnapshot,
    NodeSnapshot,
    LaneSnapshot,
    NetworkSummary,
)


def adapt_planning_snapshot_to_state_snapshot(
    planning_snapshot,
    *,
    snapshot_id: str,
    scenario_id: str,
    scenario_name: str = "",
) -> StateSnapshot:
    """
    pysi.bridge.state_snapshot.PlanningStateSnapshot
    -> wom_cockpit.domain.state_snapshot.StateSnapshot
    の最小変換。
    """

    nodes = {}
    lanes = {}

    demand_by_node = defaultdict(float)
    inventory_by_node = defaultdict(float)
    backlog_by_node = defaultdict(float)

    total_inventory = 0.0
    total_backlog = 0.0

    # inventory / backlog
    for (node_id, product_id), qty in getattr(planning_snapshot, "inventory", {}).items():
        inventory_by_node[node_id] += float(qty)
        total_inventory += float(qty)

    for (node_id, product_id), qty in getattr(planning_snapshot, "backlog", {}).items():
        backlog_by_node[node_id] += float(qty)
        total_backlog += float(qty)

    # lot_demand_bindings を demand とみなす
    for (_lot_id, _demand_id), binding in getattr(planning_snapshot, "lot_demand_bindings", {}).items():
        node_id = str(getattr(binding, "node_id", "unknown"))
        qty = float(getattr(binding, "quantity_cpu", 1.0))
        demand_by_node[node_id] += qty

    # nodes
    all_node_ids = set(demand_by_node.keys()) | set(inventory_by_node.keys()) | set(backlog_by_node.keys())

    for node_id in sorted(all_node_ids):
        demand_qty = demand_by_node.get(node_id, 0.0)
        inventory_qty = inventory_by_node.get(node_id, 0.0)
        backlog_qty = backlog_by_node.get(node_id, 0.0)

        nodes[node_id] = NodeSnapshot(
            node_id=node_id,
            node_name=node_id,
            node_type="node",
            demand_qty=demand_qty,
            supply_qty=0.0,
            inventory_qty=inventory_qty,
            backlog_qty=backlog_qty,
            lost_sales_qty=0.0,
            revenue=0.0,
            cost=0.0,
            profit=0.0,
            attributes={},
        )

    # edge_flows -> lanes
    for (from_node, to_node, product_id), qty in getattr(planning_snapshot, "edge_flows", {}).items():
        lane_id = f"{from_node}__{to_node}"
        lanes[lane_id] = LaneSnapshot(
            lane_id=lane_id,
            from_node_id=str(from_node),
            to_node_id=str(to_node),
            flow_qty=float(qty),
            active=True,
            attributes={"product_id": str(product_id)},
        )

    summary = NetworkSummary(
        total_demand_qty=float(sum(demand_by_node.values())),
        total_supply_qty=0.0,
        total_inventory_qty=float(total_inventory),
        total_backlog_qty=float(total_backlog),
        total_lost_sales_qty=0.0,
        total_revenue=0.0,
        total_cost=0.0,
        total_profit=0.0,
        profit_ratio=0.0,
    )

    return StateSnapshot(
        snapshot_id=snapshot_id,
        scenario_id=scenario_id,
        scenario_name=scenario_name or scenario_id,
        time_bucket=str(getattr(planning_snapshot, "time_bucket", "")),
        as_of="",
        version="bridge-adapted-v1",
        nodes=nodes,
        lanes=lanes,
        summary=summary,
        tags=["bridge_adapted"],
        assumptions={},
        metadata={},
    )