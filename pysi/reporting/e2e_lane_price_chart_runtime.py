from __future__ import annotations

import os

from pysi.reporting.e2e_lane_route_runtime import export_e2e_lane_route_from_env
from pysi.reporting.price_propagation_chart import generate_price_waterfall_stacked_bar


def generate_e2e_lane_price_chart_from_env(
    env,
    *,
    product_name: str,
    leaf_node: str,
    inbound_leaf_node: str | None = None,
    node_price_waterfall_csv: str = "data/node_price_waterfall.csv",
    price_propagation_trace_csv: str = "data/price_propagation_trace.csv",
    e2e_lane_route_csv: str = "data/e2e_lane_route.csv",
    output_dir: str = "outputs/reporting_mvp/price_propagation",
    supply_point_node: str = "supply_point",
    generate_full_price: bool = True,
    generate_delta_only: bool = True,
    skip_all_zero: bool = True,
) -> dict:
    """Generate E2E lane charts from runtime env with one safe helper call."""
    result = {
        "product_name": product_name,
        "leaf_node": leaf_node,
        "inbound_leaf_node": inbound_leaf_node,
        "e2e_lane_route_csv": e2e_lane_route_csv,
        "generated_files": [],
        "route_rows": [],
        "errors": [],
        "warnings": [],
    }

    if env is None:
        result["errors"].append("env is None")
        return result

    if not (product_name or "").strip():
        result["errors"].append("product_name is required")
        return result

    if not (leaf_node or "").strip():
        result["errors"].append("leaf_node is required")
        return result

    if not os.path.exists(node_price_waterfall_csv):
        result["errors"].append(f"node_price_waterfall_csv not found: {node_price_waterfall_csv}")
        return result

    if not os.path.exists(price_propagation_trace_csv):
        result["warnings"].append(f"price_propagation_trace_csv not found: {price_propagation_trace_csv}")

    try:
        route_rows = export_e2e_lane_route_from_env(
            env,
            product_name=product_name,
            leaf_node=leaf_node,
            inbound_leaf_node=inbound_leaf_node,
            output_path=e2e_lane_route_csv,
            supply_point_node=supply_point_node,
        )
        result["route_rows"] = route_rows

        if not route_rows:
            result["warnings"].append("no e2e lane route rows generated")
            return result

        if generate_full_price:
            result["generated_files"].extend(
                generate_price_waterfall_stacked_bar(
                    node_price_waterfall_csv,
                    output_dir,
                    product=product_name,
                    leaf_node=leaf_node,
                    e2e_lane_route_csv=e2e_lane_route_csv,
                    price_propagation_trace_csv=price_propagation_trace_csv,
                    chart_mode="full_price",
                    chart_scope="e2e_primary",
                    inbound_leaf_node=inbound_leaf_node,
                    supply_point_node=supply_point_node,
                    skip_all_zero=skip_all_zero,
                )
            )

        if generate_delta_only:
            result["generated_files"].extend(
                generate_price_waterfall_stacked_bar(
                    node_price_waterfall_csv,
                    output_dir,
                    product=product_name,
                    leaf_node=leaf_node,
                    e2e_lane_route_csv=e2e_lane_route_csv,
                    price_propagation_trace_csv=price_propagation_trace_csv,
                    chart_mode="delta_only",
                    chart_scope="e2e_primary",
                    inbound_leaf_node=inbound_leaf_node,
                    supply_point_node=supply_point_node,
                    skip_all_zero=skip_all_zero,
                )
            )
    except Exception as exc:  # pragma: no cover - defensive guard for GUI caller safety
        result["errors"].append(str(exc))

    return result
