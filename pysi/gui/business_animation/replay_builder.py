#pysi/gui/business_animation/replay_builder.py

#これは、まずは既存の planning result からではなくても動くように、
#最小のダミー生成を持たせています。
#あとで build_snapshots_from_wom_result(...) に差し替えればOKです。

from __future__ import annotations

from typing import Iterable

from .replay_models import (
    AnimationEvent,
    EdgeWeeklyMetrics,
    NodeWeeklyMetrics,
    TotalWeeklyMetrics,
    WeeklyReplaySnapshot,
)


def build_dummy_snapshots(
    node_ids: list[str],
    edges: list[tuple[str, str]],
    weeks: int = 20,
) -> list[WeeklyReplaySnapshot]:
    """
    最小の動作確認用ダミーsnapshot生成。
    後で WOM planning result から build_snapshots_from_wom_result() に差し替える。
    """
    snapshots: list[WeeklyReplaySnapshot] = []

    for w in range(1, weeks + 1):
        node_metrics: dict[str, NodeWeeklyMetrics] = {}
        edge_metrics: dict[tuple[str, str], EdgeWeeklyMetrics] = {}
        active_events: list[AnimationEvent] = []

        total_revenue = 0.0
        total_cost = 0.0
        total_inventory = 0.0
        total_cash_in = 0.0
        total_cash_out = 0.0

        for i, node_id in enumerate(node_ids):
            revenue = max(0.0, (w * 100000.0) - (i * 25000.0))
            cost = max(0.0, revenue * 0.72 + (i * 5000.0))
            profit = revenue - cost
            inventory = max(0.0, ((len(node_ids) - i) * 1200.0) - (w * 30.0))
            cash_in = revenue * 0.9
            cash_out = cost * 0.95

            m = NodeWeeklyMetrics(
                node_id=node_id,
                revenue=revenue,
                cost=cost,
                profit=profit,
                inventory=inventory,
                cash_in=cash_in,
                cash_out=cash_out,
                service_level=max(0.0, min(1.0, 0.88 + 0.01 * i - 0.002 * w)),
                capacity_utilization=max(0.0, min(1.0, 0.45 + 0.015 * w)),
                produced_qty=max(0.0, 5000 - i * 300 + w * 20),
                shipped_qty=max(0.0, 4500 - i * 250 + w * 15),
            )
            node_metrics[node_id] = m

            total_revenue += revenue
            total_cost += cost
            total_inventory += inventory
            total_cash_in += cash_in
            total_cash_out += cash_out

        for j, (src, dst) in enumerate(edges):
            shipped_qty = max(0.0, 1000.0 + w * 50.0 - j * 60.0)
            shipment_count = 1 if shipped_qty > 0 else 0
            pulse_strength = min(1.0, shipped_qty / 2500.0)

            e = EdgeWeeklyMetrics(
                from_node=src,
                to_node=dst,
                shipped_qty=shipped_qty,
                shipment_count=shipment_count,
                pulse_strength=pulse_strength,
            )
            edge_metrics[(src, dst)] = e

            if shipment_count > 0:
                active_events.append(
                    AnimationEvent(
                        week_no=w,
                        event_type="shipment",
                        from_node=src,
                        to_node=dst,
                        magnitude=shipped_qty,
                    )
                )

        total = TotalWeeklyMetrics(
            revenue=total_revenue,
            cost=total_cost,
            profit=total_revenue - total_cost,
            inventory=total_inventory,
            cash_in=total_cash_in,
            cash_out=total_cash_out,
            service_level=0.92,
        )

        snapshots.append(
            WeeklyReplaySnapshot(
                week_no=w,
                node_metrics=node_metrics,
                edge_metrics=edge_metrics,
                total_metrics=total,
                active_events=active_events,
            )
        )

    return snapshots


def build_snapshots_from_wom_result(
    node_ids: list[str],
    edges: list[tuple[str, str]],
    weekly_node_rows: Iterable[dict],
    weekly_edge_rows: Iterable[dict],
) -> list[WeeklyReplaySnapshot]:
    """
    後で WOM 実データに接続する本命の入口。
    現時点では枠だけ用意。
    """
    raise NotImplementedError("Connect this builder to WOM result / KPI aggregation.")
