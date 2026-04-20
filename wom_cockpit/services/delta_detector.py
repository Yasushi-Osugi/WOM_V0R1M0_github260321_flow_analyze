# ********
# STARTER
# ********
#from wom_cockpit.services.delta_detector import compare_snapshots
#
#delta = compare_snapshots(baseline_snapshot, scenario_snapshot)
#
#print(delta.delta_id)
#print(delta.summary_delta.total_profit.before, "->", delta.summary_delta.total_profit.after)
#
#for node_id, nd in delta.node_deltas.items():
#    if nd.changed_fields:
#        print(node_id, nd.changed_fields)

#この skeleton のポイント
#
#この版は、あえてまだ次を入れていません。
#
#変化量のしきい値分類
#重要度判定
#percentage change の異常値制御
#attributes の深掘り比較
#policy_changes の自動推定
#構造変化の自然言語化
#
#その代わり、PlanDelta をまず安定して返す ことに集中しています。
#経営cockpitは、まず「差分が正しく取れる」ことが命です。ここがズレると、
#後段の課題生成が全部ポエムになります。ポエムは経営会議では便利そうで便利ではありません。

from __future__ import annotations

from dataclasses import fields
from typing import Dict, Iterable, List, Optional, Set

from wom_cockpit.domain.state_snapshot import (
    StateSnapshot,
    NodeSnapshot,
    LaneSnapshot,
    NetworkSummary,
)
from wom_cockpit.domain.plan_delta import (
    PlanDelta,
    NodeDelta,
    LaneDelta,
    SummaryDelta,
    ValueDelta,
)


# ------------------------------------------------------------
# basic helpers
# ------------------------------------------------------------

_NUMERIC_NODE_FIELDS = [
    "demand_qty",
    "supply_qty",
    "inventory_qty",
    "backlog_qty",
    "lost_sales_qty",
    "revenue",
    "cost",
    "profit",
    "production_utilization",
    "shipment_utilization",
    "inventory_utilization",
]

_NUMERIC_LANE_FIELDS = [
    "flow_qty",
    "lead_time",
    "capacity",
    "utilization",
    "cost",
    "tariff_cost",
]

_NUMERIC_SUMMARY_FIELDS = [
    "total_demand_qty",
    "total_supply_qty",
    "total_inventory_qty",
    "total_backlog_qty",
    "total_lost_sales_qty",
    "total_revenue",
    "total_cost",
    "total_profit",
    "profit_ratio",
    "avg_production_utilization",
    "avg_shipment_utilization",
    "avg_inventory_utilization",
]


def _safe_float(value: object) -> float:
    """
    None や非数値っぽいものを 0.0 に寄せる簡易変換。
    """
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _make_value_delta(before: object, after: object) -> ValueDelta:
    return ValueDelta(before=_safe_float(before), after=_safe_float(after))


def _changed(before: object, after: object, tolerance: float = 1e-9) -> bool:
    """
    数値差分の有無を判定。
    """
    b = _safe_float(before)
    a = _safe_float(after)
    return abs(a - b) > tolerance


# ------------------------------------------------------------
# node / lane / summary compare
# ------------------------------------------------------------

def _compare_node(
    before_node: Optional[NodeSnapshot],
    after_node: Optional[NodeSnapshot],
) -> NodeDelta:
    """
    NodeSnapshot 2つから NodeDelta を作る。
    片方が None の場合は 0 埋め比較。
    """
    node_id = (
        after_node.node_id if after_node is not None
        else before_node.node_id if before_node is not None
        else ""
    )
    node_name = (
        after_node.node_name if after_node is not None
        else before_node.node_name if before_node is not None
        else ""
    )
    node_type = (
        after_node.node_type if after_node is not None
        else before_node.node_type if before_node is not None
        else ""
    )

    delta = NodeDelta(
        node_id=node_id,
        node_name=node_name,
        node_type=node_type,
    )

    for field_name in _NUMERIC_NODE_FIELDS:
        before_value = getattr(before_node, field_name, 0.0) if before_node else 0.0
        after_value = getattr(after_node, field_name, 0.0) if after_node else 0.0
        setattr(delta, field_name, _make_value_delta(before_value, after_value))

        if _changed(before_value, after_value):
            delta.changed_fields.append(field_name)

    return delta


def _compare_lane(
    before_lane: Optional[LaneSnapshot],
    after_lane: Optional[LaneSnapshot],
) -> LaneDelta:
    """
    LaneSnapshot 2つから LaneDelta を作る。
    片方が None の場合は 0 埋め比較。
    """
    lane_id = (
        after_lane.lane_id if after_lane is not None
        else before_lane.lane_id if before_lane is not None
        else ""
    )
    from_node_id = (
        after_lane.from_node_id if after_lane is not None
        else before_lane.from_node_id if before_lane is not None
        else ""
    )
    to_node_id = (
        after_lane.to_node_id if after_lane is not None
        else before_lane.to_node_id if before_lane is not None
        else ""
    )

    delta = LaneDelta(
        lane_id=lane_id,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        active_before=before_lane.active if before_lane is not None else False,
        active_after=after_lane.active if after_lane is not None else False,
    )

    for field_name in _NUMERIC_LANE_FIELDS:
        before_value = getattr(before_lane, field_name, 0.0) if before_lane else 0.0
        after_value = getattr(after_lane, field_name, 0.0) if after_lane else 0.0
        setattr(delta, field_name, _make_value_delta(before_value, after_value))

        if _changed(before_value, after_value):
            delta.changed_fields.append(field_name)

    if delta.active_before != delta.active_after:
        delta.changed_fields.append("active")

    return delta


def _compare_summary(
    before_summary: Optional[NetworkSummary],
    after_summary: Optional[NetworkSummary],
) -> SummaryDelta:
    """
    NetworkSummary 2つから SummaryDelta を作る。
    """
    delta = SummaryDelta()

    for field_name in _NUMERIC_SUMMARY_FIELDS:
        before_value = getattr(before_summary, field_name, 0.0) if before_summary else 0.0
        after_value = getattr(after_summary, field_name, 0.0) if after_summary else 0.0
        setattr(delta, field_name, _make_value_delta(before_value, after_value))

    return delta


# ------------------------------------------------------------
# public API
# ------------------------------------------------------------

def compare_snapshots(
    baseline: StateSnapshot,
    scenario: StateSnapshot,
    *,
    delta_id: Optional[str] = None,
    include_unchanged_nodes: bool = True,
    include_unchanged_lanes: bool = True,
) -> PlanDelta:
    """
    baseline と scenario の2つの StateSnapshot を比較し、
    PlanDelta を返す最小実装。

    Parameters
    ----------
    baseline : StateSnapshot
        比較元
    scenario : StateSnapshot
        比較先
    delta_id : Optional[str]
        明示指定がなければ自動生成
    include_unchanged_nodes : bool
        True の場合、差分がない node も node_deltas に含める
    include_unchanged_lanes : bool
        True の場合、差分がない lane も lane_deltas に含める
    """
    resolved_delta_id = (
        delta_id
        or f"delta::{baseline.snapshot_id}__vs__{scenario.snapshot_id}"
    )

    plan_delta = PlanDelta(
        delta_id=resolved_delta_id,
        baseline_snapshot_id=baseline.snapshot_id,
        scenario_snapshot_id=scenario.snapshot_id,
        baseline_scenario_id=baseline.scenario_id,
        scenario_id=scenario.scenario_id,
        time_bucket=scenario.time_bucket or baseline.time_bucket,
    )

    # --------------------------------------------------------
    # summary delta
    # --------------------------------------------------------
    plan_delta.summary_delta = _compare_summary(
        baseline.summary,
        scenario.summary,
    )

    # --------------------------------------------------------
    # node delta
    # --------------------------------------------------------
    baseline_node_ids: Set[str] = set(baseline.nodes.keys())
    scenario_node_ids: Set[str] = set(scenario.nodes.keys())
    all_node_ids = baseline_node_ids | scenario_node_ids

    plan_delta.added_nodes = sorted(list(scenario_node_ids - baseline_node_ids))
    plan_delta.removed_nodes = sorted(list(baseline_node_ids - scenario_node_ids))

    for node_id in sorted(all_node_ids):
        before_node = baseline.nodes.get(node_id)
        after_node = scenario.nodes.get(node_id)

        node_delta = _compare_node(before_node, after_node)

        if include_unchanged_nodes or node_delta.changed_fields:
            plan_delta.node_deltas[node_id] = node_delta

    # --------------------------------------------------------
    # lane delta
    # --------------------------------------------------------
    baseline_lane_ids: Set[str] = set(baseline.lanes.keys())
    scenario_lane_ids: Set[str] = set(scenario.lanes.keys())
    all_lane_ids = baseline_lane_ids | scenario_lane_ids

    plan_delta.added_lanes = sorted(list(scenario_lane_ids - baseline_lane_ids))
    plan_delta.removed_lanes = sorted(list(baseline_lane_ids - scenario_lane_ids))

    for lane_id in sorted(all_lane_ids):
        before_lane = baseline.lanes.get(lane_id)
        after_lane = scenario.lanes.get(lane_id)

        lane_delta = _compare_lane(before_lane, after_lane)

        if include_unchanged_lanes or lane_delta.changed_fields:
            plan_delta.lane_deltas[lane_id] = lane_delta

    # --------------------------------------------------------
    # structural change hints
    # --------------------------------------------------------
    if plan_delta.added_nodes:
        plan_delta.structural_changes.append(
            f"added_nodes:{','.join(plan_delta.added_nodes)}"
        )
    if plan_delta.removed_nodes:
        plan_delta.structural_changes.append(
            f"removed_nodes:{','.join(plan_delta.removed_nodes)}"
        )
    if plan_delta.added_lanes:
        plan_delta.structural_changes.append(
            f"added_lanes:{','.join(plan_delta.added_lanes)}"
        )
    if plan_delta.removed_lanes:
        plan_delta.structural_changes.append(
            f"removed_lanes:{','.join(plan_delta.removed_lanes)}"
        )

    return plan_delta