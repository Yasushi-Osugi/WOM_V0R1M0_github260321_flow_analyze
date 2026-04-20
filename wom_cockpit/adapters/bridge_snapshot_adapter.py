from __future__ import annotations

from collections import defaultdict
from typing import Any

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
    env: Any = None,
) -> StateSnapshot:
    """
    pysi.bridge.state_snapshot.PlanningStateSnapshot
    -> wom_cockpit.domain.state_snapshot.StateSnapshot
    の最小変換。

    NOTE:
    - 現時点では bridge snapshot に financial fields が直接無いので、
      env / source snapshot から参照できるものがあれば attributes 側に入れる余地を残す。
    - backlog を暫定的に lost_sales としても扱う。
    """

    nodes = {}
    lanes = {}

    demand_by_node = defaultdict(float)
    inventory_by_node = defaultdict(float)
    backlog_by_node = defaultdict(float)
    lost_sales_by_node = defaultdict(float)

    revenue_by_node = defaultdict(float)
    cost_by_node = defaultdict(float)
    profit_by_node = defaultdict(float)

    total_inventory = 0.0
    total_backlog = 0.0
    total_lost_sales = 0.0
    total_revenue = 0.0
    total_cost = 0.0
    total_profit = 0.0

    # inventory / backlog
    for (node_id, product_id), qty in getattr(planning_snapshot, "inventory", {}).items():
        q = float(qty)
        inventory_by_node[node_id] += q
        total_inventory += q

    for (node_id, product_id), qty in getattr(planning_snapshot, "backlog", {}).items():
        q = float(qty)
        backlog_by_node[node_id] += q
        total_backlog += q

        # 最小版では backlog を lost_sales の proxy として扱う
        lost_sales_by_node[node_id] += q
        total_lost_sales += q

    # demand bindings -> demand
    for (_lot_id, _demand_id), binding in getattr(planning_snapshot, "lot_demand_bindings", {}).items():
        node_id = str(getattr(binding, "node_id", "unknown"))
        qty = float(getattr(binding, "quantity_cpu", 1.0))
        demand_by_node[node_id] += qty

    # financial summary は env 側の集計済み KPI を優先利用
    if env is not None:
        total_revenue = float(getattr(env, "total_revenue", 0.0) or 0.0)
        total_cost = float(getattr(env, "total_cost", 0.0) or 0.0)
        total_profit = float(getattr(env, "total_profit", 0.0) or 0.0)
    else:
        summary_like = getattr(planning_snapshot, "summary", None)
        if summary_like is not None:
            total_revenue = float(getattr(summary_like, "total_revenue", 0.0) or 0.0)
            total_cost = float(getattr(summary_like, "total_cost", 0.0) or 0.0)
            total_profit = float(getattr(summary_like, "total_profit", 0.0) or 0.0)

    # nodes
    all_node_ids = (
        set(demand_by_node.keys())
        | set(inventory_by_node.keys())
        | set(backlog_by_node.keys())
        | set(lost_sales_by_node.keys())
        | set(revenue_by_node.keys())
        | set(cost_by_node.keys())
        | set(profit_by_node.keys())
    )

    for node_id in sorted(all_node_ids):
        demand_qty = demand_by_node.get(node_id, 0.0)
        inventory_qty = inventory_by_node.get(node_id, 0.0)
        backlog_qty = backlog_by_node.get(node_id, 0.0)
        lost_sales_qty = lost_sales_by_node.get(node_id, 0.0)

        revenue = revenue_by_node.get(node_id, 0.0)
        cost = cost_by_node.get(node_id, 0.0)
        profit = profit_by_node.get(node_id, 0.0)

        nodes[node_id] = NodeSnapshot(
            node_id=node_id,
            node_name=node_id,
            node_type="node",
            demand_qty=demand_qty,
            supply_qty=0.0,
            inventory_qty=inventory_qty,
            backlog_qty=backlog_qty,
            lost_sales_qty=lost_sales_qty,
            revenue=revenue,
            cost=cost,
            profit=profit,
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

    profit_ratio = 0.0
    if abs(total_revenue) > 1e-9:
        profit_ratio = (total_profit / total_revenue) * 100.0

    summary = NetworkSummary(
        total_demand_qty=float(sum(demand_by_node.values())),
        total_supply_qty=0.0,
        total_inventory_qty=float(total_inventory),
        total_backlog_qty=float(total_backlog),
        total_lost_sales_qty=float(total_lost_sales),
        total_revenue=float(total_revenue),
        total_cost=float(total_cost),
        total_profit=float(total_profit),
        profit_ratio=float(profit_ratio),
    )

    return StateSnapshot(
        snapshot_id=snapshot_id,
        scenario_id=scenario_id,
        scenario_name=scenario_name or scenario_id,
        time_bucket=str(getattr(planning_snapshot, "time_bucket", "")),
        as_of="",
        version="bridge-adapted-v2",
        nodes=nodes,
        lanes=lanes,
        summary=summary,
        tags=["bridge_adapted"],
        assumptions={},
        metadata={},
    )