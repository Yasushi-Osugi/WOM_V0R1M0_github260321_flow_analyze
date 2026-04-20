from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass(slots=True)
class EvidenceRef:
    """
    FactやIssueの根拠参照。
    node/lane/metric を指し示す軽量オブジェクト。
    """
    ref_type: str                 # node / lane / summary / policy / scenario
    ref_id: str                   # node_id / lane_id / etc.
    metric_name: str = ""
    before: float = 0.0
    after: float = 0.0
    unit: str = ""
    note: str = ""


@dataclass(slots=True)
class ManagementFact:
    """
    差分を経営視点で意味づけした中間表現。
    例:
      - 'ASEAN service level deterioration'
      - 'North America profit improvement'
      - 'China sourcing concentration increase'
    """
    fact_id: str
    fact_type: str                # risk / opportunity / tradeoff / alert / change
    category: str                 # profitability / service / resilience / cash / strategy / etc.
    title: str
    description: str = ""

    severity: str = "medium"      # low / medium / high / critical
    direction: str = "neutral"    # positive / negative / tradeoff / neutral

    metric_name: str = ""
    metric_value: float = 0.0
    metric_unit: str = ""

    affected_nodes: List[str] = field(default_factory=list)
    affected_lanes: List[str] = field(default_factory=list)
    affected_regions: List[str] = field(default_factory=list)
    affected_products: List[str] = field(default_factory=list)
    affected_markets: List[str] = field(default_factory=list)

    evidence: List[EvidenceRef] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
