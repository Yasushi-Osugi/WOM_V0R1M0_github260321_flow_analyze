#pysi/gui/business_animation/replay_models.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NodeWeeklyMetrics:
    node_id: str
    revenue: float = 0.0
    cost: float = 0.0
    profit: float = 0.0
    inventory: float = 0.0
    cash_in: float = 0.0
    cash_out: float = 0.0
    service_level: Optional[float] = None
    capacity_utilization: Optional[float] = None
    produced_qty: float = 0.0
    shipped_qty: float = 0.0


@dataclass
class EdgeWeeklyMetrics:
    from_node: str
    to_node: str
    shipped_qty: float = 0.0
    shipment_count: int = 0
    pulse_strength: float = 0.0


@dataclass
class TotalWeeklyMetrics:
    revenue: float = 0.0
    cost: float = 0.0
    profit: float = 0.0
    inventory: float = 0.0
    cash_in: float = 0.0
    cash_out: float = 0.0
    service_level: Optional[float] = None


@dataclass
class AnimationEvent:
    week_no: int
    event_type: str
    node_id: Optional[str] = None
    from_node: Optional[str] = None
    to_node: Optional[str] = None
    lot_id: Optional[str] = None
    magnitude: float = 0.0


@dataclass
class WeeklyReplaySnapshot:
    week_no: int
    node_metrics: dict[str, NodeWeeklyMetrics] = field(default_factory=dict)
    edge_metrics: dict[tuple[str, str], EdgeWeeklyMetrics] = field(default_factory=dict)
    total_metrics: TotalWeeklyMetrics = field(default_factory=TotalWeeklyMetrics)
    active_events: list[AnimationEvent] = field(default_factory=list)


@dataclass
class ReplayState:
    current_index: int = 0
    is_playing: bool = False
    speed_mult: float = 1.0
    selected_node_id: Optional[str] = None
    mode: str = "profit"   # "revenue" | "profit" | "inventory"
    overlay_events: bool = True
