from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from wom_cockpit.domain.plan_delta import PlanDelta, ValueDelta
from wom_cockpit.domain.issue import Issue


# ------------------------------------------------------------
# view model primitives
# ------------------------------------------------------------

@dataclass(slots=True)
class KPIViewModel:
    """
    KPIカード表示用の最小ViewModel。
    """
    key: str
    label: str
    value: float
    unit: str = ""
    before: float = 0.0
    after: float = 0.0
    delta: float = 0.0
    direction: str = "neutral"   # positive / negative / neutral
    severity: str = "low"        # low / medium / high / critical


@dataclass(slots=True)
class RiskViewModel:
    """
    リスク一覧表示用の最小ViewModel。
    """
    risk_id: str
    title: str
    category: str
    severity: str
    priority: int
    summary: str = ""
    affected_nodes: List[str] = field(default_factory=list)
    affected_regions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass(slots=True)
class ScenarioSummaryViewModel:
    """
    画面上部または左ペインに置くシナリオ要約。
    """
    delta_id: str
    baseline_scenario_id: str
    scenario_id: str
    time_bucket: str = ""

    summary_text: str = ""
    structural_changes: List[str] = field(default_factory=list)
    policy_changes: List[str] = field(default_factory=list)

    added_nodes: List[str] = field(default_factory=list)
    removed_nodes: List[str] = field(default_factory=list)
    added_lanes: List[str] = field(default_factory=list)
    removed_lanes: List[str] = field(default_factory=list)


@dataclass(slots=True)
class CockpitViewModel:
    """
    Cockpit画面に渡す最上位ViewModel。
    """
    scenario_summary: ScenarioSummaryViewModel
    top_kpis: List[KPIViewModel] = field(default_factory=list)
    top_risks: List[RiskViewModel] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)


# ------------------------------------------------------------
# helpers
# ------------------------------------------------------------

_SEVERITY_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def _delta_value(v: ValueDelta) -> float:
    return v.after - v.before


def _severity_by_abs_delta(x: float) -> str:
    ax = abs(x)
    if ax >= 1000:
        return "critical"
    if ax >= 100:
        return "high"
    if ax >= 10:
        return "medium"
    return "low"


def _direction_for_metric(metric_key: str, delta: float) -> str:
    """
    KPIごとに、増加が良いか悪いかをざっくり定義する。
    最小版なので必要最小限。
    """
    positive_if_up = {"total_revenue", "total_profit", "profit_ratio", "total_supply_qty"}
    negative_if_up = {"total_inventory_qty", "total_backlog_qty", "total_lost_sales_qty", "total_cost"}

    if metric_key in positive_if_up:
        if delta > 0:
            return "positive"
        if delta < 0:
            return "negative"
        return "neutral"

    if metric_key in negative_if_up:
        if delta > 0:
            return "negative"
        if delta < 0:
            return "positive"
        return "neutral"

    return "neutral"


def _make_kpi(
    key: str,
    label: str,
    value_delta: ValueDelta,
    unit: str = "",
) -> KPIViewModel:
    delta = _delta_value(value_delta)
    return KPIViewModel(
        key=key,
        label=label,
        value=value_delta.after,
        unit=unit,
        before=value_delta.before,
        after=value_delta.after,
        delta=delta,
        direction=_direction_for_metric(key, delta),
        severity=_severity_by_abs_delta(delta),
    )


def _build_top_kpis(plan_delta: PlanDelta) -> List[KPIViewModel]:
    s = plan_delta.summary_delta

    kpis = [
        _make_kpi("total_revenue", "売上", s.total_revenue, "amount"),
        _make_kpi("total_profit", "利益", s.total_profit, "amount"),
        _make_kpi("profit_ratio", "利益率", s.profit_ratio, "percent"),
        _make_kpi("total_inventory_qty", "在庫", s.total_inventory_qty, "qty"),
        _make_kpi("total_lost_sales_qty", "欠品", s.total_lost_sales_qty, "qty"),
        _make_kpi("total_backlog_qty", "バックログ", s.total_backlog_qty, "qty"),
    ]

    return kpis


def _build_top_risks(issues: List[Issue], max_items: int = 5) -> List[RiskViewModel]:
    risk_like = [
        x for x in issues
        if x.issue_type in {"risk", "tradeoff", "strategic_issue"}
    ]

    risk_like.sort(
        key=lambda x: (x.priority, -_SEVERITY_RANK.get(x.severity, 1), x.title)
    )

    result: List[RiskViewModel] = []
    for issue in risk_like[:max_items]:
        result.append(
            RiskViewModel(
                risk_id=issue.issue_id,
                title=issue.title,
                category=issue.category,
                severity=issue.severity,
                priority=issue.priority,
                summary=issue.summary,
                affected_nodes=list(issue.affected_nodes),
                affected_regions=list(issue.affected_regions),
                tags=list(issue.tags),
            )
        )
    return result


def _build_summary_text(plan_delta: PlanDelta, issues: List[Issue]) -> str:
    """
    画面用の短い要約文。
    最小版なので summary delta と高優先課題だけを見る。
    """
    s = plan_delta.summary_delta

    profit_delta = _delta_value(s.total_profit)
    revenue_delta = _delta_value(s.total_revenue)
    inventory_delta = _delta_value(s.total_inventory_qty)
    lost_sales_delta = _delta_value(s.total_lost_sales_qty)

    fragments: List[str] = []

    if revenue_delta != 0:
        fragments.append(f"売上差分 {revenue_delta:+.1f}")
    if profit_delta != 0:
        fragments.append(f"利益差分 {profit_delta:+.1f}")
    if inventory_delta != 0:
        fragments.append(f"在庫差分 {inventory_delta:+.1f}")
    if lost_sales_delta != 0:
        fragments.append(f"欠品差分 {lost_sales_delta:+.1f}")

    if issues:
        top_issue = sorted(issues, key=lambda x: (x.priority, x.title))[0]
        fragments.append(f"最優先課題: {top_issue.title}")

    return " / ".join(fragments) if fragments else "顕著な差分は検出されていません。"


def _build_scenario_summary(
    plan_delta: PlanDelta,
    issues: List[Issue],
) -> ScenarioSummaryViewModel:
    return ScenarioSummaryViewModel(
        delta_id=plan_delta.delta_id,
        baseline_scenario_id=plan_delta.baseline_scenario_id,
        scenario_id=plan_delta.scenario_id,
        time_bucket=plan_delta.time_bucket,
        summary_text=_build_summary_text(plan_delta, issues),
        structural_changes=list(plan_delta.structural_changes),
        policy_changes=list(plan_delta.policy_changes),
        added_nodes=list(plan_delta.added_nodes),
        removed_nodes=list(plan_delta.removed_nodes),
        added_lanes=list(plan_delta.added_lanes),
        removed_lanes=list(plan_delta.removed_lanes),
    )


# ------------------------------------------------------------
# public API
# ------------------------------------------------------------

def build_cockpit_view_model(
    plan_delta: PlanDelta,
    issues: List[Issue],
    *,
    top_risk_limit: int = 5,
) -> CockpitViewModel:
    """
    PlanDelta と Issue 一覧から、画面表示用の CockpitViewModel を生成する。

    Parameters
    ----------
    plan_delta : PlanDelta
        baseline vs scenario の差分
    issues : list[Issue]
        issue_engine の出力
    top_risk_limit : int
        画面に表示する top risk 件数

    Returns
    -------
    CockpitViewModel
    """
    scenario_summary = _build_scenario_summary(plan_delta, issues)
    top_kpis = _build_top_kpis(plan_delta)
    top_risks = _build_top_risks(issues, max_items=top_risk_limit)

    return CockpitViewModel(
        scenario_summary=scenario_summary,
        top_kpis=top_kpis,
        top_risks=top_risks,
        issues=sorted(issues, key=lambda x: (x.priority, x.title)),
        metadata={
            "issue_count": len(issues),
            "top_risk_limit": top_risk_limit,
        },
    )
