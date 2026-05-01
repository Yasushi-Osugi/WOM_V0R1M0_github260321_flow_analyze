"""Schema checks for MOSD v0.1 minimal adapter support."""

from __future__ import annotations

from typing import Any


LOW_CONF = {"low", "placeholder"}


def _msg(level: str, code: str, message: str) -> dict[str, str]:
    return {"level": level, "code": code, "message": message}


def validate_mosd_schema(mosd: dict) -> list[dict]:
    """Validate minimum MOSD schema and return message dictionaries."""
    if not isinstance(mosd, dict):
        raise TypeError("MOSD input must be dict.")

    msgs: list[dict[str, str]] = []
    required_lists = ["products", "physical_nodes", "product_plan_edges", "quantity_profiles"]

    for key in ["schema_version", "model_id"]:
        if not mosd.get(key):
            msgs.append(_msg("ERROR", f"MISSING_{key.upper()}", f"Missing required field: {key}"))
    for key in required_lists:
        val = mosd.get(key)
        if not isinstance(val, list):
            msgs.append(_msg("ERROR", f"INVALID_{key.upper()}", f"{key} must be a list"))

    nodes = mosd.get("physical_nodes", []) if isinstance(mosd.get("physical_nodes"), list) else []
    products = mosd.get("products", []) if isinstance(mosd.get("products"), list) else []
    edges = mosd.get("product_plan_edges", []) if isinstance(mosd.get("product_plan_edges"), list) else []
    qtys = mosd.get("quantity_profiles", []) if isinstance(mosd.get("quantity_profiles"), list) else []

    node_names = [str(n.get("node_name", "")) for n in nodes if isinstance(n, dict)]
    if len(set(node_names)) != len(node_names):
        msgs.append(_msg("ERROR", "DUP_NODE_NAME", "physical_nodes.node_name must be unique"))

    if node_names.count("supply_point") != 1:
        msgs.append(_msg("ERROR", "SUPPLY_POINT_COUNT", "supply_point must exist exactly once"))

    product_names = [str(p.get("product_name", "")) for p in products if isinstance(p, dict)]
    if len(set(product_names)) != len(product_names):
        msgs.append(_msg("ERROR", "DUP_PRODUCT_NAME", "products.product_name must be unique"))

    node_set = set(node_names)
    prod_set = set(product_names)

    for idx, edge in enumerate(edges):
        if not isinstance(edge, dict):
            msgs.append(_msg("ERROR", "EDGE_TYPE", f"product_plan_edges[{idx}] must be object"))
            continue
        pn = edge.get("product_name")
        if pn not in prod_set:
            msgs.append(_msg("ERROR", "EDGE_PRODUCT_REF", f"Edge {idx} references unknown product_name: {pn}"))
        parent, child = edge.get("parent_node"), edge.get("child_node")
        if parent != "root" and parent not in node_set:
            msgs.append(_msg("ERROR", "EDGE_PARENT_REF", f"Edge {idx} parent_node unknown: {parent}"))
        if child not in node_set:
            msgs.append(_msg("ERROR", "EDGE_CHILD_REF", f"Edge {idx} child_node unknown: {child}"))
        if "lot_size" in edge and edge.get("lot_size") is not None and float(edge.get("lot_size", 0)) <= 0:
            msgs.append(_msg("ERROR", "EDGE_LOT_SIZE", f"Edge {idx} lot_size must be > 0"))
        if "leadtime_days" in edge and edge.get("leadtime_days") is not None and float(edge.get("leadtime_days", 0)) < 0:
            msgs.append(_msg("ERROR", "EDGE_LEADTIME", f"Edge {idx} leadtime_days must be >= 0"))

    for idx, q in enumerate(qtys):
        if not isinstance(q, dict):
            msgs.append(_msg("ERROR", "QTY_TYPE", f"quantity_profiles[{idx}] must be object"))
            continue
        if q.get("product_name") not in prod_set:
            msgs.append(_msg("ERROR", "QTY_PRODUCT_REF", f"Quantity {idx} references unknown product_name"))
        if q.get("node_name") not in node_set:
            msgs.append(_msg("ERROR", "QTY_NODE_REF", f"Quantity {idx} references unknown node_name"))
        if q.get("bucket") not in {"P", "S"}:
            msgs.append(_msg("ERROR", "QTY_BUCKET", f"Quantity {idx} bucket must be P or S"))
        month = q.get("month")
        if not isinstance(month, int) or not (1 <= month <= 12):
            msgs.append(_msg("ERROR", "QTY_MONTH", f"Quantity {idx} month must be 1..12"))
        try:
            qty = float(q.get("quantity", 0))
            if qty < 0:
                msgs.append(_msg("ERROR", "QTY_NEGATIVE", f"Quantity {idx} must be >= 0"))
        except (TypeError, ValueError):
            msgs.append(_msg("ERROR", "QTY_NUMBER", f"Quantity {idx} quantity must be numeric"))

    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        name = str(node.get("node_name", ""))
        role = str(node.get("role", ""))
        nc = str(node.get("node_character", ""))
        if name.startswith("MOM_") and "MOM" not in {role, nc}:
            msgs.append(_msg("WARNING", "PREFIX_MOM_INCONSISTENT", f"Node {idx} MOM_ prefix inconsistent"))
        if name.startswith("DAD_") and "DAD" not in {role, nc}:
            msgs.append(_msg("WARNING", "PREFIX_DAD_INCONSISTENT", f"Node {idx} DAD_ prefix inconsistent"))
        st = str(node.get("source_type", ""))
        conf = str(node.get("confidence", ""))
        if st == "navigator_assumption" or conf in LOW_CONF:
            msgs.append(_msg("WARNING", "LOW_CONFIDENCE_NODE", f"Node {name} has assumption/low confidence metadata"))

    for section_name, items in (("products", products), ("product_plan_edges", edges), ("quantity_profiles", qtys)):
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            st = str(item.get("source_type", ""))
            conf = str(item.get("confidence", ""))
            if st == "navigator_assumption" or conf in LOW_CONF:
                msgs.append(_msg("WARNING", "LOW_CONFIDENCE_DATA", f"{section_name}[{i}] has assumption/low confidence metadata"))

    msgs.append(_msg("INFO", "SCHEMA_VALIDATION_DONE", "MOSD schema validation completed"))
    return msgs
