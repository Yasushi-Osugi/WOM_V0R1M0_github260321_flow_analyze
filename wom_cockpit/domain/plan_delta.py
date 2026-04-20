from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass(slots=True)
class ValueDelta:
    """
    単一指標の差分。
    """
    before: float = 0.0
    after: float = 0.0

    @property
    def absolute_change(self) -> float:
        return self.after - self.before

    @property
    def percent_change(self) -> float:
        if self.before == 0:
            return 0.0 if self.after == 0 else 999999.0
        return (self.after - self.before) / self.before * 100.0


@dataclass(slots=True)
class NodeDelta:
    """
    単一nodeの差分。
    """
    node_id: str
    node_name: str = ""
    node_type: str = ""

    demand_qty: ValueDelta = field(default_factory=ValueDelta)
    supply_qty: ValueDelta = field(default_factory=ValueDelta)
    inventory_qty: ValueDelta = field(default_factory=ValueDelta)
    backlog_qty: ValueDelta = field(default_factory=ValueDelta)
    lost_sales_qty: ValueDelta = field(default_factory=ValueDelta)

    revenue: ValueDelta = field(default_factory=ValueDelta)
    cost: ValueDelta = field(default_factory=ValueDelta)
    profit: ValueDelta = field(default_factory=ValueDelta)

    production_utilization: ValueDelta = field(default_factory=ValueDelta)
    shipment_utilization: ValueDelta = field(default_factory=ValueDelta)
    inventory_utilization: ValueDelta = field(default_factory=ValueDelta)

    changed_fields: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LaneDelta:
    """
    単一laneの差分。
    """
    lane_id: str
    from_node_id: str
    to_node_id: str

    flow_qty: ValueDelta = field(default_factory=ValueDelta)
    lead_time: ValueDelta = field(default_factory=ValueDelta)
    capacity: ValueDelta = field(default_factory=ValueDelta)
    utilization: ValueDelta = field(default_factory=ValueDelta)

    cost: ValueDelta = field(default_factory=ValueDelta)
    tariff_cost: ValueDelta = field(default_factory=ValueDelta)

    active_before: bool = True
    active_after: bool = True

    changed_fields: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SummaryDelta:
    """
    全体集計の差分。
    """
    total_demand_qty: ValueDelta = field(default_factory=ValueDelta)
    total_supply_qty: ValueDelta = field(default_factory=ValueDelta)
    total_inventory_qty: ValueDelta = field(default_factory=ValueDelta)
    total_backlog_qty: ValueDelta = field(default_factory=ValueDelta)
    total_lost_sales_qty: ValueDelta = field(default_factory=ValueDelta)

    total_revenue: ValueDelta = field(default_factory=ValueDelta)
    total_cost: ValueDelta = field(default_factory=ValueDelta)
    total_profit: ValueDelta = field(default_factory=ValueDelta)
    profit_ratio: ValueDelta = field(default_factory=ValueDelta)

    avg_production_utilization: ValueDelta = field(default_factory=ValueDelta)
    avg_shipment_utilization: ValueDelta = field(default_factory=ValueDelta)
    avg_inventory_utilization: ValueDelta = field(default_factory=ValueDelta)


@dataclass(slots=True)
class PlanDelta:
    """
    baseline snapshot と scenario snapshot の差分全体。
    """
    delta_id: str
    baseline_snapshot_id: str
    scenario_snapshot_id: str

    baseline_scenario_id: str = ""
    scenario_id: str = ""
    time_bucket: str = ""

    node_deltas: Dict[str, NodeDelta] = field(default_factory=dict)
    lane_deltas: Dict[str, LaneDelta] = field(default_factory=dict)
    summary_delta: SummaryDelta = field(default_factory=SummaryDelta)

    added_nodes: List[str] = field(default_factory=list)
    removed_nodes: List[str] = field(default_factory=list)
    added_lanes: List[str] = field(default_factory=list)
    removed_lanes: List[str] = field(default_factory=list)

    structural_changes: List[str] = field(default_factory=list)
    policy_changes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
