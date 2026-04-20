from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any

from wom_cockpit.ui.cockpit_view_model import (
    CockpitViewModel,
    KPIViewModel,
    RiskViewModel,
)
from wom_cockpit.domain.issue import Issue


# ------------------------------------------------------------
# presenter row models
# ------------------------------------------------------------

@dataclass(slots=True)
class KPIComparisonCard:
    """
    KPIカード1枚分の表示モデル。
    """
    key: str
    title: str
    headline_value: str
    sub_value: str = ""
    direction: str = "neutral"   # positive / negative / neutral
    severity: str = "low"
    badge: str = ""


@dataclass(slots=True)
class ScenarioCompareRow:
    """
    baseline vs scenario 比較表の1行。
    """
    metric_key: str
    label: str
    baseline_value: str
    scenario_value: str
    delta_value: str
    direction: str = "neutral"
    severity: str = "low"
    note: str = ""


@dataclass(slots=True)
class IssueListItem:
    """
    画面のIssue一覧や右ペイン要約用の軽量表示モデル。
    """
    issue_id: str
    title: str
    category: str
    severity: str
    priority: int
    summary: str
    owner_hint: str = ""
    recommendation_summary: str = ""


@dataclass(slots=True)
class RiskListItem:
    """
    top risk 一覧表示用。
    """
    risk_id: str
    title: str
    category: str
    severity: str
    priority: int
    summary: str = ""
    chips: List[str] = field(default_factory=list)


@dataclass(slots=True)
class ScenarioComparePresentation:
    """
    画面側へ渡す presenter 出力。
    """
    header_title: str
    summary_text: str

    kpi_cards: List[KPIComparisonCard] = field(default_factory=list)
    compare_rows: List[ScenarioCompareRow] = field(default_factory=list)
    top_risk_items: List[RiskListItem] = field(default_factory=list)
    issue_items: List[IssueListItem] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)


# ------------------------------------------------------------
# formatting helpers
# ------------------------------------------------------------

def _fmt_number(value: float, unit: str = "") -> str:
    if unit == "percent":
        return f"{value:.1f}%"
    if unit == "qty":
        return f"{value:,.1f}"
    if unit == "amount":
        return f"{value:,.1f}"
    return f"{value:,.1f}"


def _fmt_delta(delta: float, unit: str = "") -> str:
    if unit == "percent":
        return f"{delta:+.1f}pt"
    if unit == "qty":
        return f"{delta:+,.1f}"
    if unit == "amount":
        return f"{delta:+,.1f}"
    return f"{delta:+,.1f}"


def _badge_for_kpi(kpi: KPIViewModel) -> str:
    if kpi.direction == "positive":
        return "improved"
    if kpi.direction == "negative":
        return "worsened"
    return "unchanged"


def _note_for_kpi(kpi: KPIViewModel) -> str:
    if kpi.key == "total_inventory_qty":
        return "在庫増は資金固定化の可能性"
    if kpi.key == "total_lost_sales_qty":
        return "欠品増はサービス水準低下の可能性"
    if kpi.key == "total_backlog_qty":
        return "未充足需要の増加"
    if kpi.key == "total_profit":
        return "全体採算への影響"
    if kpi.key == "profit_ratio":
        return "収益性の変化"
    if kpi.key == "total_revenue":
        return "需要充足と売上への影響"
    return ""


# ------------------------------------------------------------
# presenters
# ------------------------------------------------------------

def present_kpi_cards(vm: CockpitViewModel) -> List[KPIComparisonCard]:
    cards: List[KPIComparisonCard] = []

    for kpi in vm.top_kpis:
        cards.append(
            KPIComparisonCard(
                key=kpi.key,
                title=kpi.label,
                headline_value=_fmt_number(kpi.after, kpi.unit),
                sub_value=f"{_fmt_delta(kpi.delta, kpi.unit)}  (base: {_fmt_number(kpi.before, kpi.unit)})",
                direction=kpi.direction,
                severity=kpi.severity,
                badge=_badge_for_kpi(kpi),
            )
        )

    return cards


def present_compare_rows(vm: CockpitViewModel) -> List[ScenarioCompareRow]:
    rows: List[ScenarioCompareRow] = []

    for kpi in vm.top_kpis:
        rows.append(
            ScenarioCompareRow(
                metric_key=kpi.key,
                label=kpi.label,
                baseline_value=_fmt_number(kpi.before, kpi.unit),
                scenario_value=_fmt_number(kpi.after, kpi.unit),
                delta_value=_fmt_delta(kpi.delta, kpi.unit),
                direction=kpi.direction,
                severity=kpi.severity,
                note=_note_for_kpi(kpi),
            )
        )

    return rows


def present_top_risks(vm: CockpitViewModel) -> List[RiskListItem]:
    items: List[RiskListItem] = []

    for risk in vm.top_risks:
        chips: List[str] = []
        if risk.category:
            chips.append(risk.category)
        if risk.severity:
            chips.append(risk.severity)
        chips.extend(risk.tags[:2])

        items.append(
            RiskListItem(
                risk_id=risk.risk_id,
                title=risk.title,
                category=risk.category,
                severity=risk.severity,
                priority=risk.priority,
                summary=risk.summary,
                chips=chips,
            )
        )

    return items


def present_issue_list(vm: CockpitViewModel) -> List[IssueListItem]:
    items: List[IssueListItem] = []

    for issue in vm.issues:
        items.append(
            IssueListItem(
                issue_id=issue.issue_id,
                title=issue.title,
                category=issue.category,
                severity=issue.severity,
                priority=issue.priority,
                summary=issue.summary,
                owner_hint=issue.owner_hint,
                recommendation_summary=issue.recommendation_summary,
            )
        )

    return items


def present_scenario_compare(vm: CockpitViewModel) -> ScenarioComparePresentation:
    """
    CockpitViewModel を UI 表示向けの比較表現へ整形する。
    """
    header_title = (
        f"{vm.scenario_summary.baseline_scenario_id} "
        f"vs {vm.scenario_summary.scenario_id}"
    )

    return ScenarioComparePresentation(
        header_title=header_title,
        summary_text=vm.scenario_summary.summary_text,
        kpi_cards=present_kpi_cards(vm),
        compare_rows=present_compare_rows(vm),
        top_risk_items=present_top_risks(vm),
        issue_items=present_issue_list(vm),
        metadata={
            "time_bucket": vm.scenario_summary.time_bucket,
            "issue_count": len(vm.issues),
            "risk_count": len(vm.top_risks),
        },
    )