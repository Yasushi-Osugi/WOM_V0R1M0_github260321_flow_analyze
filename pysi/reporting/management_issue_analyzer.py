from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ManagementIssue:
    priority: str
    severity: str
    category: str
    title: str
    owner: str
    reason: str
    suggested_action: str
    related_kpi: str
    baseline_value: float
    scenario_value: float
    delta_value: float


@dataclass
class ManagementRisk:
    rank: int
    risk_name: str
    severity: str
    description: str


@dataclass
class ManagementAnalysisResult:
    issues: list[ManagementIssue]
    risks: list[ManagementRisk]
    narrative: str


DEFAULT_THRESHOLDS = {
    "profit_ratio_drop_pt": -3.0,
    "inventory_delta_abs": 1.0,
}


def _num(d: dict[str, Any], key: str) -> float:
    try:
        return float(d.get(key, 0.0) or 0.0)
    except Exception:
        return 0.0


def analyze_management_delta(
    baseline: dict[str, Any],
    scenario: dict[str, Any],
    scenario_name: str = "Scenario",
    demo_mode: bool = False,
    thresholds: dict[str, float] | None = None,
) -> ManagementAnalysisResult:
    th = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        th.update(thresholds)

    keys = ["revenue", "profit", "profit_ratio", "inventory", "shortage", "backlog"]
    b = {k: _num(baseline, k) for k in keys}
    s = {k: _num(scenario, k) for k in keys}
    d = {k: s[k] - b[k] for k in keys}

    issues: list[ManagementIssue] = []

    def add(priority, severity, category, title, owner, reason, action, k):
        issues.append(
            ManagementIssue(
                priority=priority,
                severity=severity,
                category=category,
                title=title,
                owner=owner,
                reason=reason,
                suggested_action=action,
                related_kpi=k,
                baseline_value=b.get(k, 0.0),
                scenario_value=s.get(k, 0.0),
                delta_value=d.get(k, 0.0),
            )
        )

    if s["profit"] < b["profit"]:
        add(
            "High", "Warning", "Profitability", "利益悪化", "Management",
            "Scenario利益がBaseline利益を下回っています。",
            "コスト構造、価格条件、供給配分を見直してください。",
            "profit",
        )

    if d["profit_ratio"] <= th["profit_ratio_drop_pt"]:
        add(
            "High", "Warning", "Profitability", "利益率低下", "Management",
            "利益率が一定以上低下しています。",
            "低採算市場・低採算製品への供給配分を見直してください。",
            "profit_ratio",
        )

    if d["revenue"] > 0 and d["profit"] < 0:
        add(
            "High", "Critical", "Profitability", "売上増・利益減", "Management",
            "売上増加にもかかわらず利益が悪化しています。",
            "価格条件、物流費、製造コスト、供給配分を確認してください。",
            "profit",
        )

    if d["shortage"] > 0:
        add(
            "High", "Critical", "Service", "欠品リスク増加", "SCM",
            "欠品が増加しています。",
            "優先市場への供給再配分、短期増産を検討してください。",
            "shortage",
        )

    if d["backlog"] > 0:
        add(
            "High", "Warning", "Service", "バックログ増加", "SCM",
            "バックログが増加しています。",
            "供給能力・輸送能力を調整してください。",
            "backlog",
        )

    if d["inventory"] > th["inventory_delta_abs"]:
        add(
            "Medium", "Warning", "Inventory", "在庫滞留リスク", "SCM",
            "在庫が増加しています。",
            "需要見直し、減産、販促、在庫再配分を検討してください。",
            "inventory",
        )

    if d["inventory"] < -th["inventory_delta_abs"] and d["revenue"] > 0:
        add(
            "Medium", "Info", "Inventory", "在庫急減", "SCM",
            "売上増に伴い在庫が急減しています。",
            "安全在庫水準を確認してください。",
            "inventory",
        )

    if d["inventory"] > 0 and d["profit"] < 0:
        add(
            "High", "Warning", "Cash", "キャッシュ悪化リスク", "Finance",
            "在庫増加と利益悪化が同時に発生しています。",
            "在庫投資と損益悪化の関係を確認してください。",
            "inventory",
        )

    if d["revenue"] > 0 and d["profit"] > 0 and d["shortage"] == 0 and d["backlog"] == 0:
        add(
            "Low", "Info", "Opportunity", "収益機会拡大", "Management",
            "売上・利益ともに改善しています。",
            "成長シナリオとして供給能力拡張の余地を検討してください。",
            "revenue",
        )

    if demo_mode:
        name = scenario_name.lower()
        if "demand_surge" in name or "demand surge" in name or "需要増" in scenario_name:
            add(
                "Medium", "Warning", "Capacity", "供給能力逼迫リスク", "Production",
                "需要増により供給能力が逼迫する可能性があります。",
                "短期増産、優先市場への供給再配分、安全在庫水準の確認を検討してください。",
                "revenue",
            )
        if "demand_down" in name or "demand slowdown" in name or "需要減" in scenario_name:
            add(
                "High", "Warning", "Inventory", "在庫滞留リスク", "SCM",
                "需要減により在庫滞留が発生する可能性があります。",
                "早期減産、販売促進、在庫再配分を検討してください。",
                "inventory",
            )
        if "port_stop" in name or "port stop" in name or "港湾停止" in scenario_name:
            add(
                "High", "Critical", "Logistics", "物流遅延リスク", "Logistics",
                "港湾停止により輸送遅延が発生する可能性があります。",
                "代替輸送ルート、出荷優先順位、拠点間在庫再配分を検討してください。",
                "backlog",
            )

    issues = _sort_issues(issues)
    risks = _make_risks(issues)
    narrative = _make_narrative(b, s, d, issues)

    return ManagementAnalysisResult(issues=issues, risks=risks, narrative=narrative)


def _sort_issues(issues: list[ManagementIssue]) -> list[ManagementIssue]:
    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    severity_rank = {"Critical": 0, "Warning": 1, "Info": 2}
    return sorted(
        issues,
        key=lambda x: (
            priority_rank.get(x.priority, 9),
            severity_rank.get(x.severity, 9),
        ),
    )


def _make_risks(issues: list[ManagementIssue]) -> list[ManagementRisk]:
    risks: list[ManagementRisk] = []
    negative = [i for i in issues if i.category != "Opportunity"]

    for idx, issue in enumerate(negative[:3], start=1):
        risks.append(
            ManagementRisk(
                rank=idx,
                risk_name=issue.title,
                severity=issue.severity,
                description=issue.reason,
            )
        )

    return risks


def _make_narrative(
    b: dict[str, float],
    s: dict[str, float],
    d: dict[str, float],
    issues: list[ManagementIssue],
) -> str:
    negative_issues = [i for i in issues if i.category != "Opportunity"]
    opportunity_issues = [i for i in issues if i.category == "Opportunity"]

    lines: list[str] = []

    lines.append(
        f"シナリオ差分分析の結果、売上は {d['revenue']:+,.1f}、利益は {d['profit']:+,.1f} 変化しました。"
    )
    lines.append(f"利益率は {d['profit_ratio']:+.1f}pt 変化しています。")
    lines.append("")

    lines.append("■ 収益性の見立て")
    if d["revenue"] > 0 and d["profit"] > 0:
        lines.append("売上・利益ともに改善しており、収益性の観点ではポジティブなシナリオです。")
    elif d["revenue"] > 0 and d["profit"] < 0:
        lines.append("売上は増加していますが、利益は悪化しています。成長の質を確認する必要があります。")
    elif d["profit"] < 0:
        lines.append("利益が悪化しています。需要、価格、コスト、供給制約のどこで損益悪化が発生しているか確認してください。")
    else:
        lines.append("売上・利益の変化は限定的です。大きな収益性変化は検出されていません。")
    lines.append("")

    lines.append("■ サービス水準の見立て")
    if d["shortage"] > 0 or d["backlog"] > 0:
        lines.append("欠品またはバックログが増加しており、顧客サービス水準の低下リスクがあります。")
    else:
        lines.append("欠品・バックログの大きな悪化は検出されていません。")
    lines.append("")

    lines.append("■ キャッシュ効率の見立て")
    if d["inventory"] > 0:
        lines.append("在庫が増加しており、キャッシュ固定化や滞留在庫のリスクがあります。")
    elif d["inventory"] < 0:
        lines.append("在庫が減少しています。需要増に伴う健全な在庫消費か、安全在庫低下かを確認してください。")
    else:
        lines.append("在庫の大きな変化は検出されていません。")
    lines.append("")

    lines.append("■ 主要Issue")
    if negative_issues:
        high_count = sum(1 for i in negative_issues if i.priority == "High")
        lines.append(f"優先度の高いIssueが {high_count} 件、全体で {len(negative_issues)} 件検出されました。")
        lines.append(f"特に注意すべき課題は「{negative_issues[0].title}」です。")
    else:
        lines.append("シナリオ差分に大きな経営課題は検出されていません。")
        if opportunity_issues:
            lines.append("収益機会拡大が見込まれます。")
    lines.append("")

    lines.append("■ 推奨アクション")
    if negative_issues:
        for idx, issue in enumerate(negative_issues[:3], start=1):
            lines.append(f"{idx}. {issue.suggested_action}")
    else:
        lines.append("現時点では緊急対応は不要です。ただし、シナリオ前提、需要変動、供給能力、重点市場への配分方針を継続的に確認してください。")

    return "\n".join(lines)
