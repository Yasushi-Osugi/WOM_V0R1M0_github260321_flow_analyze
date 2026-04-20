# ********
# STARTER
# ********
#from wom_cockpit.services.delta_detector import compare_snapshots
#from wom_cockpit.services.fact_extractor import extract_management_facts
#from wom_cockpit.services.issue_engine import generate_issues
#
#plan_delta = compare_snapshots(baseline_snapshot, scenario_snapshot)
#facts = extract_management_facts(plan_delta)
#issues = generate_issues(facts, group_similar_facts=False)
#
#for issue in issues:
#    print(issue.priority, issue.category, issue.title)
#    print("  Q:", issue.management_question)
#    print("  A:", issue.recommendation_summary)



from __future__ import annotations

from typing import List, Dict

from wom_cockpit.domain.management_fact import ManagementFact, EvidenceRef
from wom_cockpit.domain.issue import Issue, RecommendedAction


# ------------------------------------------------------------
# helpers
# ------------------------------------------------------------

_SEVERITY_SCORE = {
    "low": 20,
    "medium": 50,
    "high": 80,
    "critical": 100,
}


def _priority_from_severity(severity: str) -> int:
    """
    Issue.priority は小さいほど優先、という前提の最小実装。
    """
    score = _SEVERITY_SCORE.get(severity, 50)
    return max(1, 101 - score)


def _issue_id_from_fact(fact: ManagementFact) -> str:
    return f"issue::{fact.fact_id}"


def _owner_hint_from_category(category: str) -> str:
    mapping = {
        "service": "SCM / Sales",
        "profitability": "SCM / Finance",
        "cash": "SCM / Finance",
        "resilience": "SCM / Operations",
        "structure": "SCM / Strategy",
        "strategy": "CXO / Strategy",
        "investment": "CXO / Finance",
    }
    return mapping.get(category, "Management")


# ------------------------------------------------------------
# recommendation templates
# ------------------------------------------------------------

def _recommended_actions_for_fact(fact: ManagementFact) -> List[RecommendedAction]:
    actions: List[RecommendedAction] = []

    if fact.category == "service":
        if "lost_sales" in fact.metric_name or "backlog" in fact.metric_name:
            actions.append(
                RecommendedAction(
                    action_id=f"action::{fact.fact_id}::rebalance",
                    action_type="rebalance",
                    title="需給配分ルールを再評価",
                    description="重点市場・重点顧客・優先順位ルールを見直し、供給配分を再計画する。",
                    expected_effect="欠品や未充足需要の抑制",
                    feasibility="high",
                    urgency="high",
                    target_nodes=list(fact.affected_nodes),
                    target_lanes=list(fact.affected_lanes),
                    parameters={"mode": "rebalance_supply_allocation"},
                )
            )
            actions.append(
                RecommendedAction(
                    action_id=f"action::{fact.fact_id}::reroute",
                    action_type="reroute",
                    title="代替レーンを試算",
                    description="輸送経路・輸送モードの代替案を適用して再シミュレーションする。",
                    expected_effect="供給維持力の改善",
                    feasibility="medium",
                    urgency="high",
                    target_nodes=list(fact.affected_nodes),
                    target_lanes=list(fact.affected_lanes),
                    parameters={"mode": "alternative_lane_simulation"},
                )
            )

    elif fact.category == "profitability":
        if "profit" in fact.metric_name or "revenue" in fact.metric_name:
            actions.append(
                RecommendedAction(
                    action_id=f"action::{fact.fact_id}::cost_review",
                    action_type="cost_review",
                    title="収益構造を再点検",
                    description="輸送費・調達費・在庫費・販売価格条件を見直し、利益悪化要因を分解する。",
                    expected_effect="利益率の回復余地を確認",
                    feasibility="high",
                    urgency="medium",
                    target_nodes=list(fact.affected_nodes),
                    target_lanes=list(fact.affected_lanes),
                    parameters={"mode": "profit_bridge_analysis"},
                )
            )

    elif fact.category == "cash":
        if "inventory" in fact.metric_name:
            actions.append(
                RecommendedAction(
                    action_id=f"action::{fact.fact_id}::inventory_policy",
                    action_type="change_policy",
                    title="在庫政策を見直す",
                    description="安全在庫、補充条件、供給ロットの設定を再確認する。",
                    expected_effect="運転資本の圧縮",
                    feasibility="high",
                    urgency="medium",
                    target_nodes=list(fact.affected_nodes),
                    parameters={"mode": "inventory_policy_review"},
                )
            )

    elif fact.category == "resilience":
        if "utilization" in fact.metric_name:
            actions.append(
                RecommendedAction(
                    action_id=f"action::{fact.fact_id}::capacity_review",
                    action_type="add_capacity",
                    title="能力増強または負荷分散を検討",
                    description="生産・出荷・在庫能力の増強、または負荷分散案を評価する。",
                    expected_effect="逼迫リスクの低減",
                    feasibility="medium",
                    urgency="high",
                    target_nodes=list(fact.affected_nodes),
                    parameters={"mode": "capacity_shift_or_expand"},
                )
            )

    elif fact.category == "structure":
        actions.append(
            RecommendedAction(
                action_id=f"action::{fact.fact_id}::structure_review",
                action_type="review_structure",
                title="構造変更の妥当性を確認",
                description="追加・削除されたnode/laneが戦略・運用・採算の観点で妥当か確認する。",
                expected_effect="ネットワーク設計意図の明確化",
                feasibility="high",
                urgency="medium",
                target_nodes=list(fact.affected_nodes),
                target_lanes=list(fact.affected_lanes),
                parameters={"mode": "network_structure_review"},
            )
        )

    return actions


# ------------------------------------------------------------
# narrative helpers
# ------------------------------------------------------------

def _why_it_matters(fact: ManagementFact) -> str:
    if fact.category == "service":
        return "顧客サービス水準や市場信頼の低下につながる可能性がある。"
    if fact.category == "profitability":
        return "売上・利益の悪化は計画全体の採算性を損なう。"
    if fact.category == "cash":
        return "在庫増や資金固定化は運転資本効率を悪化させる。"
    if fact.category == "resilience":
        return "能力逼迫や余裕度低下は外乱時の回復力を弱める。"
    if fact.category == "structure":
        return "ネットワーク構造の変更は長期的な供給責任や採算構造に影響する。"
    return "経営判断に影響する重要な変化である。"


def _management_question(fact: ManagementFact) -> str:
    if fact.category == "service":
        return "供給優先順位、代替供給、またはレーン変更でサービス低下を抑えるべきか。"
    if fact.category == "profitability":
        return "利益悪化を受容するのか、価格・コスト・配分見直しを行うのか。"
    if fact.category == "cash":
        return "在庫水準を維持して供給安定を優先するのか、資金効率を優先して圧縮するのか。"
    if fact.category == "resilience":
        return "能力増強、負荷分散、供給制約受容のどれを選ぶべきか。"
    if fact.category == "structure":
        return "今回のネットワーク構造変更を恒久施策として扱うべきか、一時対応とすべきか。"
    return "この変化に対してどの意思決定を優先すべきか。"


def _recommendation_summary(actions: List[RecommendedAction]) -> str:
    if not actions:
        return ""
    titles = [a.title for a in actions[:2]]
    return " / ".join(titles)


# ------------------------------------------------------------
# single fact -> single issue
# ------------------------------------------------------------

def _issue_from_fact(fact: ManagementFact) -> Issue:
    actions = _recommended_actions_for_fact(fact)

    return Issue(
        issue_id=_issue_id_from_fact(fact),
        issue_type=fact.fact_type if fact.fact_type in {"risk", "opportunity", "tradeoff"} else "strategic_issue",
        category=fact.category,
        title=fact.title,
        summary=fact.description or fact.title,
        severity=fact.severity,
        priority=_priority_from_severity(fact.severity),
        why_it_matters=_why_it_matters(fact),
        management_question=_management_question(fact),
        recommendation_summary=_recommendation_summary(actions),
        related_fact_ids=[fact.fact_id],
        evidence=list(fact.evidence),
        recommended_actions=actions,
        affected_nodes=list(fact.affected_nodes),
        affected_lanes=list(fact.affected_lanes),
        affected_regions=list(fact.affected_regions),
        affected_products=list(fact.affected_products),
        affected_markets=list(fact.affected_markets),
        owner_hint=_owner_hint_from_category(fact.category),
        tags=list(fact.tags),
        attributes=dict(fact.attributes),
    )


# ------------------------------------------------------------
# optional lightweight grouping
# ------------------------------------------------------------

def _groupable_key(fact: ManagementFact) -> str:
    """
    将来拡張用の軽量 grouping key。
    今は category + direction + affected node set を粗く束ねる程度。
    """
    nodes_key = ",".join(sorted(fact.affected_nodes))
    return f"{fact.category}|{fact.direction}|{nodes_key}"


def _merge_facts_to_issue(group: List[ManagementFact]) -> Issue:
    """
    最小版の複数Fact統合。
    最もseverityの高いFactを代表にして、related_fact_ids/evidence を束ねる。
    """
    ranked = sorted(
        group,
        key=lambda f: _SEVERITY_SCORE.get(f.severity, 50),
        reverse=True,
    )
    leader = ranked[0]

    merged_actions: List[RecommendedAction] = []
    seen_action_ids = set()
    merged_evidence: List[EvidenceRef] = []

    related_fact_ids: List[str] = []
    affected_nodes = set()
    affected_lanes = set()
    affected_regions = set()
    affected_products = set()
    affected_markets = set()
    tags = set()

    for fact in ranked:
        related_fact_ids.append(fact.fact_id)
        affected_nodes.update(fact.affected_nodes)
        affected_lanes.update(fact.affected_lanes)
        affected_regions.update(fact.affected_regions)
        affected_products.update(fact.affected_products)
        affected_markets.update(fact.affected_markets)
        tags.update(fact.tags)
        merged_evidence.extend(fact.evidence)

        for action in _recommended_actions_for_fact(fact):
            if action.action_id not in seen_action_ids:
                merged_actions.append(action)
                seen_action_ids.add(action.action_id)

    title = leader.title if len(group) == 1 else f"{leader.category}に関する複合課題"
    summary = leader.description if len(group) == 1 else "複数の経営ファクトが同一論点に収束している。"

    return Issue(
        issue_id=f"issue::group::{_groupable_key(leader)}",
        issue_type=leader.fact_type if leader.fact_type in {"risk", "opportunity", "tradeoff"} else "strategic_issue",
        category=leader.category,
        title=title,
        summary=summary,
        severity=leader.severity,
        priority=_priority_from_severity(leader.severity),
        why_it_matters=_why_it_matters(leader),
        management_question=_management_question(leader),
        recommendation_summary=_recommendation_summary(merged_actions),
        related_fact_ids=related_fact_ids,
        evidence=merged_evidence,
        recommended_actions=merged_actions,
        affected_nodes=sorted(affected_nodes),
        affected_lanes=sorted(affected_lanes),
        affected_regions=sorted(affected_regions),
        affected_products=sorted(affected_products),
        affected_markets=sorted(affected_markets),
        owner_hint=_owner_hint_from_category(leader.category),
        tags=sorted(tags),
        attributes={},
    )


# ------------------------------------------------------------
# public API
# ------------------------------------------------------------

def generate_issues(
    facts: List[ManagementFact],
    *,
    group_similar_facts: bool = False,
) -> List[Issue]:
    """
    ManagementFact の一覧から Issue の一覧を生成する最小実装。

    Parameters
    ----------
    facts : list[ManagementFact]
        fact_extractor の出力
    group_similar_facts : bool
        True の場合、粗い grouping key で似たFactを束ねる

    Returns
    -------
    list[Issue]
    """
    if not facts:
        return []

    if not group_similar_facts:
        issues = [_issue_from_fact(f) for f in facts]
    else:
        buckets: Dict[str, List[ManagementFact]] = {}
        for fact in facts:
            key = _groupable_key(fact)
            buckets.setdefault(key, []).append(fact)
        issues = [_merge_facts_to_issue(group) for group in buckets.values()]

    issues.sort(key=lambda x: (x.priority, x.title))
    return issues