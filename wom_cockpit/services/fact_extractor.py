# ********
# STARTER
# ********
#from wom_cockpit.services.delta_detector import compare_snapshots
#from wom_cockpit.services.fact_extractor import extract_management_facts
#
#plan_delta = compare_snapshots(baseline_snapshot, scenario_snapshot)
#facts = extract_management_facts(plan_delta)
#
#for fact in facts:
#    print(f"[{fact.category}] {fact.title} / severity={fact.severity}")



from __future__ import annotations

from typing import List, Iterable

from wom_cockpit.domain.plan_delta import (
    PlanDelta,
    NodeDelta,
    LaneDelta,
    ValueDelta,
)
from wom_cockpit.domain.management_fact import (
    ManagementFact,
    EvidenceRef,
)


# ------------------------------------------------------------
# thresholds (minimal defaults)
# ------------------------------------------------------------

DEFAULT_LOST_SALES_ALERT_THRESHOLD = 1.0
DEFAULT_BACKLOG_ALERT_THRESHOLD = 1.0
DEFAULT_INVENTORY_ALERT_THRESHOLD = 1.0
DEFAULT_PROFIT_ALERT_THRESHOLD = 1.0
DEFAULT_REVENUE_ALERT_THRESHOLD = 1.0
DEFAULT_UTILIZATION_HIGH_THRESHOLD = 90.0


# ------------------------------------------------------------
# helpers
# ------------------------------------------------------------

def _delta_abs(v: ValueDelta) -> float:
    return v.after - v.before


def _is_increase(v: ValueDelta, threshold: float = 0.0) -> bool:
    return (v.after - v.before) > threshold


def _is_decrease(v: ValueDelta, threshold: float = 0.0) -> bool:
    return (v.before - v.after) > threshold


def _severity_by_magnitude(value: float) -> str:
    """
    最小版のseverity判定。
    絶対値ベースの雑な実装だが、最初のMVPには十分。
    """
    x = abs(value)
    if x >= 1000:
        return "critical"
    if x >= 100:
        return "high"
    if x >= 10:
        return "medium"
    return "low"


def _make_evidence_from_node_delta(
    node_delta: NodeDelta,
    metric_name: str,
    unit: str = "",
    note: str = "",
) -> EvidenceRef:
    metric_delta = getattr(node_delta, metric_name)
    return EvidenceRef(
        ref_type="node",
        ref_id=node_delta.node_id,
        metric_name=metric_name,
        before=metric_delta.before,
        after=metric_delta.after,
        unit=unit,
        note=note,
    )


def _make_evidence_from_summary(
    plan_delta: PlanDelta,
    metric_name: str,
    unit: str = "",
    note: str = "",
) -> EvidenceRef:
    metric_delta = getattr(plan_delta.summary_delta, metric_name)
    return EvidenceRef(
        ref_type="summary",
        ref_id=plan_delta.delta_id,
        metric_name=metric_name,
        before=metric_delta.before,
        after=metric_delta.after,
        unit=unit,
        note=note,
    )


def _fact_id(plan_delta: PlanDelta, suffix: str) -> str:
    return f"{plan_delta.delta_id}::{suffix}"


# ------------------------------------------------------------
# summary-level facts
# ------------------------------------------------------------

def _extract_summary_facts(plan_delta: PlanDelta) -> List[ManagementFact]:
    facts: List[ManagementFact] = []
    s = plan_delta.summary_delta

    # total profit down
    if _is_decrease(s.total_profit, DEFAULT_PROFIT_ALERT_THRESHOLD):
        change = _delta_abs(s.total_profit)
        facts.append(
            ManagementFact(
                fact_id=_fact_id(plan_delta, "summary_profit_down"),
                fact_type="risk",
                category="profitability",
                title="全体利益が低下",
                description="シナリオ比較の結果、全体利益が悪化している。",
                severity=_severity_by_magnitude(change),
                direction="negative",
                metric_name="total_profit",
                metric_value=s.total_profit.after,
                metric_unit="amount",
                evidence=[
                    _make_evidence_from_summary(
                        plan_delta,
                        "total_profit",
                        unit="amount",
                        note="全体利益の低下"
                    )
                ],
                tags=["summary", "profit"],
            )
        )

    # total revenue down
    if _is_decrease(s.total_revenue, DEFAULT_REVENUE_ALERT_THRESHOLD):
        change = _delta_abs(s.total_revenue)
        facts.append(
            ManagementFact(
                fact_id=_fact_id(plan_delta, "summary_revenue_down"),
                fact_type="risk",
                category="profitability",
                title="全体売上が低下",
                description="シナリオ比較の結果、全体売上が低下している。",
                severity=_severity_by_magnitude(change),
                direction="negative",
                metric_name="total_revenue",
                metric_value=s.total_revenue.after,
                metric_unit="amount",
                evidence=[
                    _make_evidence_from_summary(
                        plan_delta,
                        "total_revenue",
                        unit="amount",
                        note="全体売上の低下"
                    )
                ],
                tags=["summary", "revenue"],
            )
        )

    # inventory up
    if _is_increase(s.total_inventory_qty, DEFAULT_INVENTORY_ALERT_THRESHOLD):
        change = _delta_abs(s.total_inventory_qty)
        facts.append(
            ManagementFact(
                fact_id=_fact_id(plan_delta, "summary_inventory_up"),
                fact_type="alert",
                category="cash",
                title="全体在庫が増加",
                description="シナリオ比較の結果、全体在庫が増加している。",
                severity=_severity_by_magnitude(change),
                direction="negative",
                metric_name="total_inventory_qty",
                metric_value=s.total_inventory_qty.after,
                metric_unit="qty",
                evidence=[
                    _make_evidence_from_summary(
                        plan_delta,
                        "total_inventory_qty",
                        unit="qty",
                        note="全体在庫の増加"
                    )
                ],
                tags=["summary", "inventory", "working_capital"],
            )
        )

    # lost sales up
    if _is_increase(s.total_lost_sales_qty, DEFAULT_LOST_SALES_ALERT_THRESHOLD):
        change = _delta_abs(s.total_lost_sales_qty)
        facts.append(
            ManagementFact(
                fact_id=_fact_id(plan_delta, "summary_lost_sales_up"),
                fact_type="risk",
                category="service",
                title="全体欠品が増加",
                description="シナリオ比較の結果、全体の欠品量が増加している。",
                severity=_severity_by_magnitude(change),
                direction="negative",
                metric_name="total_lost_sales_qty",
                metric_value=s.total_lost_sales_qty.after,
                metric_unit="qty",
                evidence=[
                    _make_evidence_from_summary(
                        plan_delta,
                        "total_lost_sales_qty",
                        unit="qty",
                        note="全体欠品量の増加"
                    )
                ],
                tags=["summary", "lost_sales", "service"],
            )
        )

    # backlog up
    if _is_increase(s.total_backlog_qty, DEFAULT_BACKLOG_ALERT_THRESHOLD):
        change = _delta_abs(s.total_backlog_qty)
        facts.append(
            ManagementFact(
                fact_id=_fact_id(plan_delta, "summary_backlog_up"),
                fact_type="risk",
                category="service",
                title="全体バックログが増加",
                description="シナリオ比較の結果、未充足需要が増加している。",
                severity=_severity_by_magnitude(change),
                direction="negative",
                metric_name="total_backlog_qty",
                metric_value=s.total_backlog_qty.after,
                metric_unit="qty",
                evidence=[
                    _make_evidence_from_summary(
                        plan_delta,
                        "total_backlog_qty",
                        unit="qty",
                        note="全体バックログの増加"
                    )
                ],
                tags=["summary", "backlog", "service"],
            )
        )

    return facts


# ------------------------------------------------------------
# node-level facts
# ------------------------------------------------------------

def _extract_node_service_facts(
    plan_delta: PlanDelta,
    node_delta: NodeDelta,
) -> List[ManagementFact]:
    facts: List[ManagementFact] = []

    # lost sales increase
    if _is_increase(node_delta.lost_sales_qty, DEFAULT_LOST_SALES_ALERT_THRESHOLD):
        change = _delta_abs(node_delta.lost_sales_qty)
        facts.append(
            ManagementFact(
                fact_id=_fact_id(plan_delta, f"node_{node_delta.node_id}_lost_sales_up"),
                fact_type="risk",
                category="service",
                title=f"{node_delta.node_name or node_delta.node_id} の欠品増加",
                description="nodeレベルで欠品量が増加している。",
                severity=_severity_by_magnitude(change),
                direction="negative",
                metric_name="lost_sales_qty",
                metric_value=node_delta.lost_sales_qty.after,
                metric_unit="qty",
                affected_nodes=[node_delta.node_id],
                evidence=[
                    _make_evidence_from_node_delta(
                        node_delta,
                        "lost_sales_qty",
                        unit="qty",
                        note="node欠品量の増加"
                    )
                ],
                tags=["node", "service", "lost_sales"],
            )
        )

    # backlog increase
    if _is_increase(node_delta.backlog_qty, DEFAULT_BACKLOG_ALERT_THRESHOLD):
        change = _delta_abs(node_delta.backlog_qty)
        facts.append(
            ManagementFact(
                fact_id=_fact_id(plan_delta, f"node_{node_delta.node_id}_backlog_up"),
                fact_type="risk",
                category="service",
                title=f"{node_delta.node_name or node_delta.node_id} のバックログ増加",
                description="nodeレベルで未充足需要が増加している。",
                severity=_severity_by_magnitude(change),
                direction="negative",
                metric_name="backlog_qty",
                metric_value=node_delta.backlog_qty.after,
                metric_unit="qty",
                affected_nodes=[node_delta.node_id],
                evidence=[
                    _make_evidence_from_node_delta(
                        node_delta,
                        "backlog_qty",
                        unit="qty",
                        note="nodeバックログの増加"
                    )
                ],
                tags=["node", "service", "backlog"],
            )
        )

    return facts


def _extract_node_profitability_facts(
    plan_delta: PlanDelta,
    node_delta: NodeDelta,
) -> List[ManagementFact]:
    facts: List[ManagementFact] = []

    # profit decrease
    if _is_decrease(node_delta.profit, DEFAULT_PROFIT_ALERT_THRESHOLD):
        change = _delta_abs(node_delta.profit)
        facts.append(
            ManagementFact(
                fact_id=_fact_id(plan_delta, f"node_{node_delta.node_id}_profit_down"),
                fact_type="risk",
                category="profitability",
                title=f"{node_delta.node_name or node_delta.node_id} の利益低下",
                description="nodeレベルで利益が低下している。",
                severity=_severity_by_magnitude(change),
                direction="negative",
                metric_name="profit",
                metric_value=node_delta.profit.after,
                metric_unit="amount",
                affected_nodes=[node_delta.node_id],
                evidence=[
                    _make_evidence_from_node_delta(
                        node_delta,
                        "profit",
                        unit="amount",
                        note="node利益の低下"
                    )
                ],
                tags=["node", "profitability", "profit"],
            )
        )

    # revenue decrease
    if _is_decrease(node_delta.revenue, DEFAULT_REVENUE_ALERT_THRESHOLD):
        change = _delta_abs(node_delta.revenue)
        facts.append(
            ManagementFact(
                fact_id=_fact_id(plan_delta, f"node_{node_delta.node_id}_revenue_down"),
                fact_type="risk",
                category="profitability",
                title=f"{node_delta.node_name or node_delta.node_id} の売上低下",
                description="nodeレベルで売上が低下している。",
                severity=_severity_by_magnitude(change),
                direction="negative",
                metric_name="revenue",
                metric_value=node_delta.revenue.after,
                metric_unit="amount",
                affected_nodes=[node_delta.node_id],
                evidence=[
                    _make_evidence_from_node_delta(
                        node_delta,
                        "revenue",
                        unit="amount",
                        note="node売上の低下"
                    )
                ],
                tags=["node", "profitability", "revenue"],
            )
        )

    return facts


def _extract_node_cash_facts(
    plan_delta: PlanDelta,
    node_delta: NodeDelta,
) -> List[ManagementFact]:
    facts: List[ManagementFact] = []

    # inventory increase
    if _is_increase(node_delta.inventory_qty, DEFAULT_INVENTORY_ALERT_THRESHOLD):
        change = _delta_abs(node_delta.inventory_qty)
        facts.append(
            ManagementFact(
                fact_id=_fact_id(plan_delta, f"node_{node_delta.node_id}_inventory_up"),
                fact_type="alert",
                category="cash",
                title=f"{node_delta.node_name or node_delta.node_id} の在庫増加",
                description="nodeレベルで在庫が増加している。",
                severity=_severity_by_magnitude(change),
                direction="negative",
                metric_name="inventory_qty",
                metric_value=node_delta.inventory_qty.after,
                metric_unit="qty",
                affected_nodes=[node_delta.node_id],
                evidence=[
                    _make_evidence_from_node_delta(
                        node_delta,
                        "inventory_qty",
                        unit="qty",
                        note="node在庫の増加"
                    )
                ],
                tags=["node", "cash", "inventory"],
            )
        )

    return facts


def _extract_node_resilience_facts(
    plan_delta: PlanDelta,
    node_delta: NodeDelta,
) -> List[ManagementFact]:
    facts: List[ManagementFact] = []

    # utilization too high after scenario
    after_util = node_delta.production_utilization.after
    if after_util >= DEFAULT_UTILIZATION_HIGH_THRESHOLD:
        facts.append(
            ManagementFact(
                fact_id=_fact_id(plan_delta, f"node_{node_delta.node_id}_prod_util_high"),
                fact_type="alert",
                category="resilience",
                title=f"{node_delta.node_name or node_delta.node_id} の生産能力逼迫",
                description="生産能力使用率が高水準に達している。",
                severity="high" if after_util >= 95.0 else "medium",
                direction="negative",
                metric_name="production_utilization",
                metric_value=after_util,
                metric_unit="percent",
                affected_nodes=[node_delta.node_id],
                evidence=[
                    _make_evidence_from_node_delta(
                        node_delta,
                        "production_utilization",
                        unit="percent",
                        note="高い生産能力使用率"
                    )
                ],
                tags=["node", "resilience", "capacity"],
            )
        )

    return facts


def _extract_node_facts(
    plan_delta: PlanDelta,
    node_delta: NodeDelta,
) -> List[ManagementFact]:
    facts: List[ManagementFact] = []
    facts.extend(_extract_node_service_facts(plan_delta, node_delta))
    facts.extend(_extract_node_profitability_facts(plan_delta, node_delta))
    facts.extend(_extract_node_cash_facts(plan_delta, node_delta))
    facts.extend(_extract_node_resilience_facts(plan_delta, node_delta))
    return facts


# ------------------------------------------------------------
# structural facts
# ------------------------------------------------------------

def _extract_structural_facts(plan_delta: PlanDelta) -> List[ManagementFact]:
    facts: List[ManagementFact] = []

    if plan_delta.added_nodes:
        facts.append(
            ManagementFact(
                fact_id=_fact_id(plan_delta, "added_nodes"),
                fact_type="change",
                category="structure",
                title="node構造が追加された",
                description="baselineに対して新たなnodeが追加されている。",
                severity="medium",
                direction="neutral",
                metric_name="added_nodes_count",
                metric_value=float(len(plan_delta.added_nodes)),
                metric_unit="count",
                affected_nodes=list(plan_delta.added_nodes),
                tags=["structure", "added_nodes"],
            )
        )

    if plan_delta.removed_nodes:
        facts.append(
            ManagementFact(
                fact_id=_fact_id(plan_delta, "removed_nodes"),
                fact_type="change",
                category="structure",
                title="node構造が削除された",
                description="baselineに対してnodeが削除されている。",
                severity="medium",
                direction="neutral",
                metric_name="removed_nodes_count",
                metric_value=float(len(plan_delta.removed_nodes)),
                metric_unit="count",
                affected_nodes=list(plan_delta.removed_nodes),
                tags=["structure", "removed_nodes"],
            )
        )

    if plan_delta.added_lanes:
        facts.append(
            ManagementFact(
                fact_id=_fact_id(plan_delta, "added_lanes"),
                fact_type="change",
                category="structure",
                title="lane構造が追加された",
                description="baselineに対して新たなlaneが追加されている。",
                severity="medium",
                direction="neutral",
                metric_name="added_lanes_count",
                metric_value=float(len(plan_delta.added_lanes)),
                metric_unit="count",
                affected_lanes=list(plan_delta.added_lanes),
                tags=["structure", "added_lanes"],
            )
        )

    if plan_delta.removed_lanes:
        facts.append(
            ManagementFact(
                fact_id=_fact_id(plan_delta, "removed_lanes"),
                fact_type="change",
                category="structure",
                title="lane構造が削除された",
                description="baselineに対してlaneが削除されている。",
                severity="medium",
                direction="neutral",
                metric_name="removed_lanes_count",
                metric_value=float(len(plan_delta.removed_lanes)),
                metric_unit="count",
                affected_lanes=list(plan_delta.removed_lanes),
                tags=["structure", "removed_lanes"],
            )
        )

    return facts


# ------------------------------------------------------------
# public API
# ------------------------------------------------------------

def extract_management_facts(plan_delta: PlanDelta) -> List[ManagementFact]:
    """
    PlanDelta から ManagementFact の一覧を抽出する最小実装。

    現時点では以下を対象とする:
      - summary差分
      - node差分
      - 構造変化

    今後ここに以下を追加できる:
      - lane由来の輸送/関税/LT変化
      - 地域集中/依存度リスク
      - tradeoff fact
      - policy change fact
    """
    facts: List[ManagementFact] = []

    # 1. summary facts
    facts.extend(_extract_summary_facts(plan_delta))

    # 2. node facts
    for node_delta in plan_delta.node_deltas.values():
        facts.extend(_extract_node_facts(plan_delta, node_delta))

    # 3. structural facts
    facts.extend(_extract_structural_facts(plan_delta))

    return facts