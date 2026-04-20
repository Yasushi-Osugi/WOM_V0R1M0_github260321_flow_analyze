from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from wom_cockpit.ui.cockpit_view_model import CockpitViewModel, KPIViewModel
from wom_cockpit.domain.issue import Issue


# ------------------------------------------------------------
# output model
# ------------------------------------------------------------

@dataclass(slots=True)
class NarrativeBlock:
    """
    経営者向けサマリの段落ブロック。
    """
    title: str
    body: str


@dataclass(slots=True)
class NarrativeReport:
    """
    画面表示・会議メモ・メール下書きの元になる物語化出力。
    """
    headline: str
    executive_summary: str
    blocks: List[NarrativeBlock] = field(default_factory=list)
    closing_message: str = ""


# ------------------------------------------------------------
# helpers
# ------------------------------------------------------------

_SEVERITY_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def _find_kpi(vm: CockpitViewModel, key: str) -> Optional[KPIViewModel]:
    for k in vm.top_kpis:
        if k.key == key:
            return k
    return None


def _top_issue(vm: CockpitViewModel) -> Optional[Issue]:
    if not vm.issues:
        return None
    return sorted(vm.issues, key=lambda x: (x.priority, x.title))[0]


def _format_kpi_phrase(kpi: Optional[KPIViewModel], label: str) -> str:
    if kpi is None:
        return f"{label}の有意な変化は確認されていません"
    sign = "+" if kpi.delta > 0 else ""
    if kpi.unit == "percent":
        return f"{label}は {sign}{kpi.delta:.1f}pt 変化"
    return f"{label}は {sign}{kpi.delta:,.1f} 変化"


def _headline(vm: CockpitViewModel) -> str:
    top = _top_issue(vm)
    if top is None:
        return "シナリオ差分に大きな経営課題は検出されていません"
    return f"{top.title} が最優先の経営論点です"


def _executive_summary(vm: CockpitViewModel) -> str:
    profit = _find_kpi(vm, "total_profit")
    revenue = _find_kpi(vm, "total_revenue")
    inventory = _find_kpi(vm, "total_inventory_qty")
    lost_sales = _find_kpi(vm, "total_lost_sales_qty")
    top = _top_issue(vm)

    parts: List[str] = []
    parts.append(_format_kpi_phrase(revenue, "売上"))
    parts.append(_format_kpi_phrase(profit, "利益"))
    parts.append(_format_kpi_phrase(inventory, "在庫"))
    parts.append(_format_kpi_phrase(lost_sales, "欠品"))

    if top is not None:
        parts.append(f"最優先課題は「{top.title}」です")

    return "。".join(parts) + "。"


def _performance_block(vm: CockpitViewModel) -> NarrativeBlock:
    revenue = _find_kpi(vm, "total_revenue")
    profit = _find_kpi(vm, "total_profit")
    ratio = _find_kpi(vm, "profit_ratio")

    body_parts: List[str] = []

    if revenue:
        body_parts.append(_format_kpi_phrase(revenue, "売上"))
    if profit:
        body_parts.append(_format_kpi_phrase(profit, "利益"))
    if ratio:
        body_parts.append(_format_kpi_phrase(ratio, "利益率"))

    body = "。".join(body_parts) + "。"
    return NarrativeBlock(
        title="収益性の見立て",
        body=body,
    )


def _service_block(vm: CockpitViewModel) -> NarrativeBlock:
    lost_sales = _find_kpi(vm, "total_lost_sales_qty")
    backlog = _find_kpi(vm, "total_backlog_qty")

    body_parts: List[str] = []

    if lost_sales:
        body_parts.append(_format_kpi_phrase(lost_sales, "欠品"))
    if backlog:
        body_parts.append(_format_kpi_phrase(backlog, "バックログ"))

    if not body_parts:
        body_parts.append("サービス水準の大きな変化は確認されていません")

    return NarrativeBlock(
        title="サービス水準の見立て",
        body="。".join(body_parts) + "。",
    )


def _cash_block(vm: CockpitViewModel) -> NarrativeBlock:
    inventory = _find_kpi(vm, "total_inventory_qty")

    if inventory is None:
        body = "在庫由来の資金圧迫は現時点では明確ではありません。"
    else:
        body = _format_kpi_phrase(inventory, "在庫") + "。"
        if inventory.delta > 0:
            body += " 在庫増は運転資本の悪化要因となる可能性があります。"

    return NarrativeBlock(
        title="キャッシュ効率の見立て",
        body=body,
    )


def _risk_block(vm: CockpitViewModel) -> NarrativeBlock:
    top = _top_issue(vm)
    if top is None:
        return NarrativeBlock(
            title="主要リスク",
            body="優先度の高いリスクは検出されていません。",
        )

    body = f"{top.summary}。"
    if top.why_it_matters:
        body += f" {top.why_it_matters}"
    if top.management_question:
        body += f" 経営論点は「{top.management_question}」です。"

    return NarrativeBlock(
        title="主要リスク",
        body=body,
    )


def _action_block(vm: CockpitViewModel) -> NarrativeBlock:
    top = _top_issue(vm)
    if top is None:
        return NarrativeBlock(
            title="推奨アクション",
            body="現時点で追加アクションは必須ではありません。",
        )

    if top.recommendation_summary:
        body = f"第一候補は {top.recommendation_summary}。"
    else:
        body = "トップ課題に対する再シミュレーションと意思決定の優先付けが必要です。"

    return NarrativeBlock(
        title="推奨アクション",
        body=body,
    )


def _closing_message(vm: CockpitViewModel) -> str:
    top = _top_issue(vm)
    if top is None:
        return "現行シナリオは概ね安定しています。"
    return (
        f"今回のシナリオでは「{top.title}」を中心に、"
        "収益・サービス・在庫のトレードオフを確認しながら次アクションを決めるのが妥当です。"
    )


# ------------------------------------------------------------
# public API
# ------------------------------------------------------------

def build_narrative_report(vm: CockpitViewModel) -> NarrativeReport:
    """
    CockpitViewModel から経営者向けサマリ文章を生成する。
    """
    blocks = [
        _performance_block(vm),
        _service_block(vm),
        _cash_block(vm),
        _risk_block(vm),
        _action_block(vm),
    ]

    return NarrativeReport(
        headline=_headline(vm),
        executive_summary=_executive_summary(vm),
        blocks=blocks,
        closing_message=_closing_message(vm),
    )


def render_narrative_text(vm: CockpitViewModel) -> str:
    """
    画面表示やテキスト出力用に、NarrativeReport を単純な文章へ整形する。
    """
    report = build_narrative_report(vm)

    lines: List[str] = []
    lines.append(report.headline)
    lines.append("")
    lines.append(report.executive_summary)
    lines.append("")

    for block in report.blocks:
        lines.append(f"■ {block.title}")
        lines.append(block.body)
        lines.append("")

    if report.closing_message:
        lines.append(report.closing_message)

    return "\n".join(lines).strip()