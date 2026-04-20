from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any

from wom_cockpit.domain.issue import Issue, RecommendedAction


# ------------------------------------------------------------
# Tk-friendly row models
# ------------------------------------------------------------

@dataclass(slots=True)
class IssueTableRow:
    """
    Treeview 等に載せる1行分の軽量表現。
    """
    issue_id: str
    priority: int
    severity: str
    category: str
    title: str
    owner_hint: str
    summary: str


@dataclass(slots=True)
class IssueDetailView:
    """
    右ペイン詳細表示用。
    """
    issue_id: str
    title: str
    header_line: str
    summary: str
    why_it_matters: str
    management_question: str
    recommendation_summary: str
    affected_text: str
    evidence_lines: List[str] = field(default_factory=list)
    action_lines: List[str] = field(default_factory=list)


# ------------------------------------------------------------
# formatting helpers
# ------------------------------------------------------------

def _join_or_dash(values: List[str], sep: str = ", ") -> str:
    return sep.join([v for v in values if v]) if values else "-"


def _format_evidence_lines(issue: Issue) -> List[str]:
    lines: List[str] = []
    for ev in issue.evidence:
        metric = ev.metric_name or "-"
        unit = f" {ev.unit}" if ev.unit else ""
        lines.append(
            f"- [{ev.ref_type}] {ev.ref_id} / {metric}: {ev.before:.1f} -> {ev.after:.1f}{unit}"
            + (f" / {ev.note}" if ev.note else "")
        )
    return lines or ["- evidence not available"]


def _format_action_lines(actions: List[RecommendedAction]) -> List[str]:
    lines: List[str] = []
    for a in actions:
        lines.append(
            f"- {a.title} ({a.action_type})"
            + (f" / effect: {a.expected_effect}" if a.expected_effect else "")
            + (f" / feasibility: {a.feasibility}" if a.feasibility else "")
            + (f" / urgency: {a.urgency}" if a.urgency else "")
        )
    return lines or ["- no recommended actions"]


# ------------------------------------------------------------
# presenters
# ------------------------------------------------------------

def present_issue_table_rows(issues: List[Issue]) -> List[IssueTableRow]:
    """
    Issue一覧を表形式表示用の行へ変換する。
    """
    rows: List[IssueTableRow] = []

    for issue in sorted(issues, key=lambda x: (x.priority, x.title)):
        rows.append(
            IssueTableRow(
                issue_id=issue.issue_id,
                priority=issue.priority,
                severity=issue.severity,
                category=issue.category,
                title=issue.title,
                owner_hint=issue.owner_hint,
                summary=issue.summary,
            )
        )

    return rows


def present_issue_detail(issue: Issue) -> IssueDetailView:
    """
    単一Issueを詳細表示用テキスト群へ変換する。
    """
    header_line = (
        f"[priority={issue.priority}] "
        f"[severity={issue.severity}] "
        f"[category={issue.category}] "
        f"[owner={issue.owner_hint or '-'}]"
    )

    affected_parts = [
        f"nodes={_join_or_dash(issue.affected_nodes)}",
        f"lanes={_join_or_dash(issue.affected_lanes)}",
        f"regions={_join_or_dash(issue.affected_regions)}",
        f"markets={_join_or_dash(issue.affected_markets)}",
        f"products={_join_or_dash(issue.affected_products)}",
    ]

    return IssueDetailView(
        issue_id=issue.issue_id,
        title=issue.title,
        header_line=header_line,
        summary=issue.summary,
        why_it_matters=issue.why_it_matters or "-",
        management_question=issue.management_question or "-",
        recommendation_summary=issue.recommendation_summary or "-",
        affected_text=" / ".join(affected_parts),
        evidence_lines=_format_evidence_lines(issue),
        action_lines=_format_action_lines(issue.recommended_actions),
    )


def find_issue_by_id(issues: List[Issue], issue_id: str) -> Issue | None:
    for issue in issues:
        if issue.issue_id == issue_id:
            return issue
    return None