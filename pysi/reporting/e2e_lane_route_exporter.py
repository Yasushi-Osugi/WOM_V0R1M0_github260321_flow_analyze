import csv
from typing import Any


REQUIRED_COLUMNS = [
    "product",
    "lane_id",
    "leaf_node",
    "inbound_leaf_node",
    "chart_scope",
    "sequence_no",
    "segment",
    "direction",
    "node_name",
    "node_character",
    "parent_node",
    "child_node",
    "depth",
    "is_supply_point",
    "route_role",
    "source_tree",
    "remarks",
]


def get_plan_node_name(node: Any) -> str:
    if node is None:
        return ""
    for attr in ("name", "node_name", "node_id"):
        value = getattr(node, attr, "")
        if value:
            return str(value)
    return ""


def get_plan_children(node: Any) -> list[Any]:
    if node is None:
        return []

    for attr in ("children", "child_nodes"):
        children = getattr(node, attr, None)
        if children is None:
            continue
        if isinstance(children, dict):
            return list(children.values())
        if isinstance(children, (list, tuple)):
            return list(children)
    return []


def find_path_to_node(root, target_node_name: str) -> list[str]:
    if root is None or not target_node_name:
        return []

    def _dfs(node, path: list[str]) -> list[str]:
        node_name = get_plan_node_name(node)
        current_path = path + [node_name]
        if node_name == target_node_name:
            return current_path
        for child in get_plan_children(node):
            found = _dfs(child, current_path)
            if found:
                return found
        return []

    return _dfs(root, [])


def find_path_ending_at_supply_point(root, supply_point_node: str = "supply_point") -> list[str]:
    return find_path_to_node(root, supply_point_node)


def _find_first_leaf_path(root) -> list[str]:
    if root is None:
        return []

    def _dfs(node, path: list[str]) -> list[str]:
        node_name = get_plan_node_name(node)
        current_path = path + [node_name]
        children = get_plan_children(node)
        if not children:
            return current_path
        for child in children:
            found = _dfs(child, current_path)
            if found:
                return found
        return []

    return _dfs(root, [])


def stitch_inbound_outbound_routes(inbound_route: list[str], outbound_route: list[str], supply_point_node: str = "supply_point") -> list[str]:
    if inbound_route and outbound_route and inbound_route[-1] == supply_point_node and outbound_route[0] == supply_point_node:
        return inbound_route[:-1] + outbound_route
    return (inbound_route or []) + (outbound_route or [])


def build_e2e_lane_route_from_plan_trees(*, product_name: str, prod_tree_dict_IN: dict, prod_tree_dict_OT: dict, leaf_node: str | None = None, inbound_leaf_node: str | None = None, supply_point_node: str = "supply_point") -> list[str]:
    route, _ = _build_route_and_meta(
        product_name=product_name,
        prod_tree_dict_IN=prod_tree_dict_IN,
        prod_tree_dict_OT=prod_tree_dict_OT,
        leaf_node=leaf_node,
        inbound_leaf_node=inbound_leaf_node,
        supply_point_node=supply_point_node,
    )
    return route


def _build_route_and_meta(*, product_name: str, prod_tree_dict_IN: dict, prod_tree_dict_OT: dict, leaf_node: str | None = None, inbound_leaf_node: str | None = None, supply_point_node: str = "supply_point"):
    remarks = []
    inbound_root = (prod_tree_dict_IN or {}).get(product_name)
    outbound_root = (prod_tree_dict_OT or {}).get(product_name)

    if leaf_node:
        outbound_route = find_path_to_node(outbound_root, leaf_node)
    else:
        outbound_route = _find_first_leaf_path(outbound_root)
        remarks.append("leaf_node not specified; selected stable first leaf route")

    if inbound_leaf_node:
        inbound_route = find_path_to_node(inbound_root, supply_point_node)
        if inbound_route and inbound_leaf_node in inbound_route:
            inbound_route = inbound_route[inbound_route.index(inbound_leaf_node):]
    else:
        inbound_route = find_path_ending_at_supply_point(inbound_root, supply_point_node=supply_point_node)

    if not inbound_route and outbound_route:
        remarks.append("inbound route not found; exported outbound route only")
    if inbound_route and not outbound_route:
        remarks.append("outbound route not found")
    if not inbound_route and not outbound_route:
        return [], {"remarks": "outbound route not found; inbound route not found", "inbound": [], "outbound": [], "stitched": []}

    stitched_route = stitch_inbound_outbound_routes(inbound_route, outbound_route, supply_point_node=supply_point_node)
    return stitched_route, {
        "remarks": "; ".join(remarks),
        "inbound": inbound_route,
        "outbound": outbound_route,
        "stitched": stitched_route,
    }


def route_nodes_to_rows(*, route_nodes: list[str], product_name: str, lane_id: str, leaf_node: str | None, inbound_leaf_node: str | None, supply_point_node: str = "supply_point", remarks: str = "", inbound_route: list[str] | None = None, outbound_route: list[str] | None = None) -> list[dict]:
    rows = []
    inbound_len = len(inbound_route or [])
    outbound_start = max(inbound_len - 1, 0)
    for idx, node_name in enumerate(route_nodes):
        prev_node = route_nodes[idx - 1] if idx > 0 else ""
        next_node = route_nodes[idx + 1] if idx < len(route_nodes) - 1 else ""
        if idx < inbound_len:
            segment, direction, source_tree = "inbound", "IN", "prod_tree_dict_IN"
        elif idx >= outbound_start:
            segment, direction, source_tree = "outbound", "OUT", "prod_tree_dict_OT"
        else:
            segment, direction, source_tree = "stitch", "OUT", "stitch"

        if node_name == supply_point_node:
            route_role = "supply_point"
        elif idx == 0 and inbound_len:
            route_role = "upstream_source"
        elif leaf_node and node_name == leaf_node:
            route_role = "market_leaf"
        else:
            route_role = "unknown"

        rows.append(
            {
                "product": product_name,
                "lane_id": lane_id,
                "leaf_node": leaf_node or "",
                "inbound_leaf_node": inbound_leaf_node or "",
                "chart_scope": "e2e_primary",
                "sequence_no": idx + 1,
                "segment": segment,
                "direction": direction,
                "node_name": node_name,
                "node_character": "",
                "parent_node": prev_node,
                "child_node": next_node,
                "depth": idx,
                "is_supply_point": str(node_name == supply_point_node),
                "route_role": route_role,
                "source_tree": source_tree,
                "remarks": remarks,
            }
        )
    return rows


def export_e2e_lane_route(*, product_name: str, prod_tree_dict_IN: dict, prod_tree_dict_OT: dict, output_path: str, leaf_node: str | None = None, inbound_leaf_node: str | None = None, supply_point_node: str = "supply_point") -> list[dict]:
    route_nodes, meta = _build_route_and_meta(
        product_name=product_name,
        prod_tree_dict_IN=prod_tree_dict_IN,
        prod_tree_dict_OT=prod_tree_dict_OT,
        leaf_node=leaf_node,
        inbound_leaf_node=inbound_leaf_node,
        supply_point_node=supply_point_node,
    )
    if not route_nodes:
        return []

    lane_leaf = leaf_node or (route_nodes[-1] if route_nodes else "")
    lane_id = f"{product_name}__{lane_leaf}__e2e_primary"
    rows = route_nodes_to_rows(
        route_nodes=route_nodes,
        product_name=product_name,
        lane_id=lane_id,
        leaf_node=leaf_node,
        inbound_leaf_node=inbound_leaf_node,
        supply_point_node=supply_point_node,
        remarks=meta.get("remarks", ""),
        inbound_route=meta.get("inbound", []),
        outbound_route=meta.get("outbound", []),
    )

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return rows
