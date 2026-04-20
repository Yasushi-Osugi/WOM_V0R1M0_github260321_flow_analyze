from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass(slots=True)
class NodeSnapshot:
    """
    単一nodeの時点状態。
    node単位のPSI/KPI/能力情報を保持する最小単位。
    """
    node_id: str
    node_name: str = ""
    node_type: str = ""   # market / factory / warehouse / supplier / etc.
    region: str = ""
    product: str = ""

    demand_qty: float = 0.0
    supply_qty: float = 0.0
    inventory_qty: float = 0.0
    backlog_qty: float = 0.0
    lost_sales_qty: float = 0.0

    production_capacity: float = 0.0
    shipment_capacity: float = 0.0
    inventory_capacity: float = 0.0

    production_utilization: float = 0.0
    shipment_utilization: float = 0.0
    inventory_utilization: float = 0.0

    revenue: float = 0.0
    cost: float = 0.0
    profit: float = 0.0

    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LaneSnapshot:
    """
    node間laneの状態。
    物流レーン、輸送条件、依存度などを保持。
    """
    lane_id: str
    from_node_id: str
    to_node_id: str

    transport_mode: str = ""   # ship / air / truck / rail / etc.
    lead_time: float = 0.0
    capacity: float = 0.0
    utilization: float = 0.0

    flow_qty: float = 0.0
    cost: float = 0.0
    tariff_cost: float = 0.0

    active: bool = True
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NetworkSummary:
    """
    全体集計の最小サマリ。
    """
    total_demand_qty: float = 0.0
    total_supply_qty: float = 0.0
    total_inventory_qty: float = 0.0
    total_backlog_qty: float = 0.0
    total_lost_sales_qty: float = 0.0

    total_revenue: float = 0.0
    total_cost: float = 0.0
    total_profit: float = 0.0
    profit_ratio: float = 0.0

    total_production_capacity: float = 0.0
    total_shipment_capacity: float = 0.0
    total_inventory_capacity: float = 0.0

    avg_production_utilization: float = 0.0
    avg_shipment_utilization: float = 0.0
    avg_inventory_utilization: float = 0.0

    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StateSnapshot:
    """
    WOMのある時点/あるシナリオにおける計画状態全体。
    baseline と scenario を比較する元データになる。
    """
    snapshot_id: str
    scenario_id: str
    scenario_name: str = ""

    time_bucket: str = ""          # 2026W01 / 202601 / etc.
    as_of: str = ""                # ISO文字列でもよい
    version: str = "v0"

    nodes: Dict[str, NodeSnapshot] = field(default_factory=dict)
    lanes: Dict[str, LaneSnapshot] = field(default_factory=dict)
    summary: NetworkSummary = field(default_factory=NetworkSummary)

    tags: List[str] = field(default_factory=list)
    assumptions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_node(self, node_id: str) -> Optional[NodeSnapshot]:
        return self.nodes.get(node_id)

    def get_lane(self, lane_id: str) -> Optional[LaneSnapshot]:
        return self.lanes.get(lane_id)
