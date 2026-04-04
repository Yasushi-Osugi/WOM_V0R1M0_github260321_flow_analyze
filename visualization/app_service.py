# pysi/visualization/app_service.py

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from pysi.core.kernel.minimal_kernel import (
    DemandEvent,
    Lot,
    PlanningKernel,
)

from visualization.snapshot_adapter import build_snapshots_from_kernel_result

from visualization.viewmodels import (
    EdgeViewModel,
    EventRowViewModel,
    LotViewModel,
    NodeViewModel,
    PSIViewModel,
)


def build_demo_master_data() -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Node / edge master used by the visualizer.
    This is intentionally simple and readable.
    """
    node_master = {
        "factory_A": {
            "type": "factory",
            "x": 0.0,
            "y": 0.8,
            "overflow_threshold": 450.0,
            "product_id": "P1",
        },
        "market_TYO": {
            "type": "market",
            "x": 10.0,
            "y": 0.0,
            "overflow_threshold": 120.0,
            "product_id": "P1",
        },
        "market_OSA": {
            "type": "market",
            "x": 10.0,
            "y": 1.6,
            "overflow_threshold": 120.0,
            "product_id": "P1",
        },
    }

    edge_master = [
        {
            "from_node": "factory_A",
            "to_node": "market_TYO",
            "capacity": 100.0,
            "lead_time_weeks": 0,
        },
        {
            "from_node": "factory_A",
            "to_node": "market_OSA",
            "capacity": 100.0,
            "lead_time_weeks": 0,
        },
    ]

    return node_master, edge_master


def build_demo_kernel_inputs() -> Tuple[List[Lot], List[DemandEvent], Dict[str, Any]]:
    """
    Demo scenario aligned with minimal_kernel._demo().
    """
    lots = [
        Lot("lot-1", "P1", "factory_A", "market_TYO", 70.0, "202601"),
        Lot("lot-2", "P1", "factory_A", "market_OSA", 20.0, "202601"),
    ]

    demand_events = [
        DemandEvent("d-1", "market_TYO", "P1", "202602", 100.0),
        DemandEvent("d-2", "market_OSA", "P1", "202602", 20.0),
    ]

    kernel_kwargs = {
        "max_iterations": 3,
        "lead_time_weeks": 0,
        "capacity_limit": 100.0,
        "production_nodes": {"factory_A"},
        "upstream_by_node": {
            "market_TYO": "factory_A",
            "market_OSA": "factory_A",
        },
    }

    return lots, demand_events, kernel_kwargs


def run_kernel_scenario(
    lots: List[Lot],
    demand_events: List[DemandEvent],
    *,
    node_master: Dict[str, Dict[str, Any]],
    edge_master: List[Dict[str, Any]],
    initial_flow_events=None,
    max_iterations: int = 3,
    capacity_limit: float = 100.0,
    lead_time_weeks: int = 0,
    production_nodes=None,
    upstream_by_node=None,
    bridge_payload: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Top-level application service:
        kernel.run() -> snapshot_adapter -> visualizer snapshots
    """
    kernel = PlanningKernel()

    result = kernel.run(
        lots=lots,
        demand_events=demand_events,
        initial_flow_events=initial_flow_events,
        max_iterations=max_iterations,
        capacity_limit=capacity_limit,
        lead_time_weeks=lead_time_weeks,
        production_nodes=production_nodes,
        upstream_by_node=upstream_by_node,
    )

    # Minimal bridge injection point (short-term demo):
    # if bridge flow_events exist, prefer them for visualization replay.
    if bridge_payload:
        result["bridge"] = bridge_payload
        bridge_flow = bridge_payload.get("flow_events") or []
        if bridge_flow:
            result["flow_events"] = list(bridge_flow)

    snapshots, time_buckets = build_snapshots_from_kernel_result(
        kernel_result=result,
        demand_events=demand_events,
        node_master=node_master,
        edge_master=edge_master,
        default_product_id="P1",
    )

    return {
        "kernel_result": result,
        "snapshots": snapshots,
        "time_buckets": time_buckets,
        "node_master": node_master,
        "edge_master": edge_master,
    }


def build_demo_runtime(pipeline_result: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Fast entry point for visualizer app.
    """
    node_master, edge_master = build_demo_master_data()
    lots, demand_events, kernel_kwargs = build_demo_kernel_inputs()
    bridge_payload = (pipeline_result or {}).get("bridge") if isinstance(pipeline_result, dict) else None

    runtime = run_kernel_scenario(
        lots=lots,
        demand_events=demand_events,
        node_master=node_master,
        edge_master=edge_master,
        bridge_payload=bridge_payload,
        **kernel_kwargs,
    )

    runtime["lots"] = lots
    runtime["demand_events"] = demand_events
    return runtime
