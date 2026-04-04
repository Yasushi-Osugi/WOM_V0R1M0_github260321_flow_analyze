#pysi/gui/business_animation/context_models.py

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class BusinessAnimationContext:
    """
    Context object passed from cockpit_tk.py to BusinessAnimationPanel.

    v0.1 minimal scope:
    - current product / scenario / direction
    - current selected node
    - current planning root / node dictionary / edge list
    - trace events / bridge payload
    - cashflow_df used to build weekly KPI snapshots
    - metadata for optional layout / diagnostics
    """
    product_name: Optional[str] = None
    scenario_name: Optional[str] = None
    direction: Optional[str] = None
    selected_node: Optional[str] = None

    root_node: Any = None
    node_dict: Dict[str, Any] = field(default_factory=dict)
    edges: List[Any] = field(default_factory=list)

    trace_events: List[Dict[str, Any]] = field(default_factory=list)
    bridge_payload: Any = None
    cashflow_df: Any = None

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SnapshotEdgeMetrics:
    """
    Edge-level animation metrics for one frame/week.
    Aligned to NetworkAnimView expectations.
    """
    shipment_count: int = 0
    pulse_strength: float = 0.0


@dataclass
class SnapshotNodeMetrics:
    """
    KPI values for one node in one week/frame.
    Aligned to BusinessAnimationPanel expectations.
    """
    revenue: float = 0.0
    cost: float = 0.0
    profit: float = 0.0
    inventory: float = 0.0
    cash_in: float = 0.0
    cash_out: float = 0.0


@dataclass
class SnapshotTotalMetrics:
    """
    Totals for one animation frame/week.
    """
    revenue: float = 0.0
    cost: float = 0.0
    profit: float = 0.0
    inventory: float = 0.0


@dataclass
class BusinessAnimationSnapshot:
    """
    Controller-facing frame schema.

    Aligned to the current BusinessAnimationPanel and NetworkAnimView:
      - snapshot.week_no
      - snapshot.total_metrics
      - snapshot.node_metrics
      - snapshot.edge_metrics
    """
    week_no: int
    total_metrics: SnapshotTotalMetrics = field(default_factory=SnapshotTotalMetrics)
    node_metrics: Dict[str, SnapshotNodeMetrics] = field(default_factory=dict)
    edge_metrics: Dict[Tuple[str, str], SnapshotEdgeMetrics] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)


def to_jsonable(obj: Any) -> Any:
    """
    Convert dataclass / nested structures into JSON-serializable objects.
    Useful for debug dump, snapshot inspection, and future API export.
    """
    if is_dataclass(obj):
        return {k: to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, tuple):
        return [to_jsonable(v) for v in obj]
    return obj
