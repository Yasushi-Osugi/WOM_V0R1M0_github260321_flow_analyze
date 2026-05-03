from __future__ import annotations

from pysi.reporting.e2e_lane_route_exporter import export_e2e_lane_route


def export_e2e_lane_route_from_env(
    env,
    *,
    product_name: str,
    leaf_node: str | None = None,
    inbound_leaf_node: str | None = None,
    output_path: str = "data/e2e_lane_route.csv",
    supply_point_node: str = "supply_point",
) -> list[dict]:
    """Export E2E lane route CSV from WOM runtime env."""
    if env is None:
        return []

    if not (product_name or "").strip():
        return []

    prod_tree_dict_IN = getattr(env, "prod_tree_dict_IN", {}) or {}
    prod_tree_dict_OT = getattr(env, "prod_tree_dict_OT", {}) or {}

    if not prod_tree_dict_IN and not prod_tree_dict_OT:
        return []

    return export_e2e_lane_route(
        product_name=product_name,
        prod_tree_dict_IN=prod_tree_dict_IN,
        prod_tree_dict_OT=prod_tree_dict_OT,
        output_path=output_path,
        leaf_node=leaf_node,
        inbound_leaf_node=inbound_leaf_node,
        supply_point_node=supply_point_node,
    )
