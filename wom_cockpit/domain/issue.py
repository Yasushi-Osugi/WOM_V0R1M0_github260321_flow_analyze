from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any

from .management_fact import EvidenceRef


@dataclass(slots=True)
class RecommendedAction:
    """
    Issueに対する推奨アクション。
    WOM上で再シミュレーションできる操作単位を意識する。
    """
    action_id: str
    action_type: str              # reroute / rebalance / add_capacity / change_priority / etc.
    title: str
    description: str = ""

    expected_effect: str = ""
    feasibility: str = "medium"   # low / medium / high
    urgency: str = "medium"       # low / medium / high

    target_nodes: List[str] = field(default_factory=list)
    target_lanes: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Issue:
    """
    cockpitに表示する経営課題。
    ManagementFact群から生成される。
    """
    issue_id: str
    issue_type: str               # risk / opportunity / tradeoff / strategic_issue
    category: str                 # profitability / service / resilience / investment / strategy
    title: str
    summary: str

    severity: str = "medium"      # low / medium / high / critical
    priority: int = 50            # 小さいほど優先など、運用ルール次第

    why_it_matters: str = ""
    management_question: str = ""
    recommendation_summary: str = ""

    related_fact_ids: List[str] = field(default_factory=list)
    evidence: List[EvidenceRef] = field(default_factory=list)
    recommended_actions: List[RecommendedAction] = field(default_factory=list)

    affected_nodes: List[str] = field(default_factory=list)
    affected_lanes: List[str] = field(default_factory=list)
    affected_regions: List[str] = field(default_factory=list)
    affected_products: List[str] = field(default_factory=list)
    affected_markets: List[str] = field(default_factory=list)

    owner_hint: str = ""          # SCM / Sales / Procurement / CXO / etc.
    tags: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
