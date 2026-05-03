from __future__ import annotations

import csv
import os
import re
from collections import defaultdict, deque
from typing import Any

FULL_PRICE_COMPONENTS = [
    "purchase_cost_per_lot",
    "value_added_cost_per_lot",
    "variable_cost_per_lot",
    "fixed_cost_per_lot",
    "logistics_cost_per_lot",
    "inventory_handling_cost_per_lot",
    "tax_tariff_cost_per_lot",
    "target_profit_per_lot",
]

DELTA_ONLY_COMPONENTS = [
    "value_added_cost_per_lot",
    "variable_cost_per_lot",
    "fixed_cost_per_lot",
    "logistics_cost_per_lot",
    "inventory_handling_cost_per_lot",
    "tax_tariff_cost_per_lot",
    "target_profit_per_lot",
]

ZERO_CHECK_COMPONENTS = ["ship_price_per_lot", *FULL_PRICE_COMPONENTS]


def _as_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _sanitize_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    cleaned = cleaned.strip("._")
    return cleaned or "unknown"


def load_node_price_waterfall(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_price_propagation_trace(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_e2e_lane_route(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def select_e2e_lane_route_rows(
    route_rows: list[dict[str, str]],
    *,
    product: str,
    leaf_node: str | None = None,
    chart_scope: str | None = None,
    inbound_leaf_node: str | None = None,
) -> list[dict[str, str]]:
    matched = [r for r in route_rows if r.get("product") == product]

    if leaf_node is not None:
        matched = [r for r in matched if (r.get("leaf_node") or "").strip() == leaf_node]

    if inbound_leaf_node is not None:
        matched = [r for r in matched if (r.get("inbound_leaf_node") or "").strip() == inbound_leaf_node]
    else:
        matched = [r for r in matched if (r.get("inbound_leaf_node") or "").strip() == ""]

    if chart_scope:
        scoped = [r for r in matched if (r.get("chart_scope") or "").strip() == chart_scope]
        if scoped:
            return scoped
    return matched


def build_route_order_from_e2e_lane_rows(route_rows: list[dict[str, str]]) -> list[str]:
    sorted_rows = [
        row
        for _, row in sorted(
            enumerate(route_rows),
            key=lambda pair: (
                0 if str(pair[1].get("sequence_no", "")).strip().replace(".", "", 1).isdigit() else 1,
                _as_float(pair[1].get("sequence_no")),
                pair[0],
            ),
        )
    ]
    route_nodes: list[str] = []
    for row in sorted_rows:
        node_name = (row.get("node_name") or "").strip()
        if node_name and node_name not in route_nodes:
            route_nodes.append(node_name)
    return route_nodes


def sort_waterfall_rows_by_route(waterfall_rows: list[dict[str, str]], route_nodes: list[str]) -> list[dict[str, str]]:
    if not route_nodes:
        return waterfall_rows
    route_set = set(route_nodes)
    selected = [r for r in waterfall_rows if r.get("node_name", "") in route_set]
    return sort_rows_by_route(selected, route_nodes)


def get_chart_components(chart_mode: str) -> list[str]:
    if chart_mode == "full_price":
        return list(FULL_PRICE_COMPONENTS)
    if chart_mode == "delta_only":
        return list(DELTA_ONLY_COMPONENTS)
    raise ValueError(f"Unknown chart_mode: {chart_mode}. Supported modes: full_price, delta_only")


def sort_waterfall_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    has_sequence = any((row.get("sequence_no") or "").strip() != "" for row in rows)
    if not has_sequence:
        return rows
    return [
        row
        for _, row in sorted(
            enumerate(rows),
            key=lambda pair: (_as_float(pair[1].get("sequence_no")), pair[0]),
        )
    ]


def build_edge_order_from_trace(trace_rows: list[dict[str, str]], product: str, direction: str | None = None) -> list[str]:
    rows = [
        r
        for r in trace_rows
        if r.get("product") == product and (direction is None or (r.get("direction") or None) == direction)
    ]
    rows = sorted(rows, key=lambda r: _as_float(r.get("sequence_no")))
    ordered_nodes: list[str] = []
    for row in rows:
        from_node = row.get("from_node", "")
        to_node = row.get("to_node", "")
        if from_node and from_node not in ordered_nodes:
            ordered_nodes.append(from_node)
        if to_node and to_node not in ordered_nodes:
            ordered_nodes.append(to_node)
    return ordered_nodes


def find_route_to_leaf(
    trace_rows: list[dict[str, str]],
    product: str,
    leaf_node: str,
    direction: str | None = None,
) -> list[str]:
    rows = [
        r
        for r in trace_rows
        if r.get("product") == product and (direction is None or (r.get("direction") or None) == direction)
    ]
    if not rows:
        return []

    parents: dict[str, str] = {}
    seq: dict[tuple[str, str], float] = {}
    for row in rows:
        f, t = row.get("from_node", ""), row.get("to_node", "")
        if not f or not t:
            continue
        s = _as_float(row.get("sequence_no"))
        if t not in parents or s < seq.get((parents[t], t), float("inf")):
            parents[t] = f
            seq[(f, t)] = s

    if leaf_node not in parents and all((row.get("from_node") != leaf_node for row in rows)):
        return []

    route = deque([leaf_node])
    seen = {leaf_node}
    while route[0] in parents:
        parent = parents[route[0]]
        if parent in seen:
            break
        route.appendleft(parent)
        seen.add(parent)
    return list(route)


def sort_rows_by_route(rows: list[dict[str, str]], route_nodes: list[str]) -> list[dict[str, str]]:
    if not route_nodes:
        return rows
    by_node = {r.get("node_name", ""): r for r in rows}
    ordered = [by_node[n] for n in route_nodes if n in by_node]
    remaining = [r for r in rows if r.get("node_name", "") not in route_nodes]
    return ordered + remaining


def group_rows_by_product_and_direction(rows: list[dict[str, str]]) -> dict[tuple[str, str | None], list[dict[str, str]]]:
    grouped: dict[tuple[str, str | None], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row.get("product", ""), row.get("direction") or None)].append(row)
    return grouped


def stitch_routes(
    inbound_route: list[str],
    outbound_route: list[str],
    supply_point_node: str = "supply_point",
) -> list[str]:
    if not inbound_route:
        return list(outbound_route)
    if not outbound_route:
        return list(inbound_route)
    if inbound_route[-1] == supply_point_node and outbound_route[0] == supply_point_node:
        return [*inbound_route, *outbound_route[1:]]
    return [*inbound_route, *outbound_route]


def find_primary_inbound_route_to_supply_point(
    trace_rows: list[dict[str, str]],
    product: str,
    supply_point_node: str = "supply_point",
    inbound_leaf_node: str | None = None,
) -> list[str]:
    inbound_rows = [
        r for r in trace_rows if r.get("product") == product and (r.get("direction") or None) == "inbound"
    ]
    if not inbound_rows:
        return []

    if inbound_leaf_node:
        return find_route_to_leaf(inbound_rows, product, supply_point_node, "inbound")

    candidates = []
    to_supply = [r for r in inbound_rows if r.get("to_node") == supply_point_node]
    for row in sorted(to_supply, key=lambda r: _as_float(r.get("sequence_no"))):
        from_node = row.get("from_node")
        if not from_node:
            continue
        route = find_route_to_leaf(inbound_rows, product, supply_point_node, "inbound")
        if route:
            candidates.append(route)
            break
    return candidates[0] if candidates else []


def build_e2e_lane_route(
    trace_rows: list[dict[str, str]],
    product: str,
    leaf_node: str,
    supply_point_node: str = "supply_point",
    inbound_leaf_node: str | None = None,
) -> list[str]:
    outbound_route = find_route_to_leaf(trace_rows, product, leaf_node, "outbound")
    if not outbound_route:
        return []
    inbound_route = find_primary_inbound_route_to_supply_point(
        trace_rows,
        product,
        supply_point_node=supply_point_node,
        inbound_leaf_node=inbound_leaf_node,
    )
    return stitch_routes(inbound_route, outbound_route, supply_point_node=supply_point_node) if inbound_route else outbound_route


def build_chart_title(
    product: str,
    direction: str | None,
    chart_mode: str,
    leaf_node: str | None = None,
    chart_scope: str = "outbound_only",
) -> str:
    if chart_scope == "e2e_primary" and leaf_node:
        if chart_mode == "delta_only":
            return f"E2E Lane Added Cost Structure per Lot - {product} → {leaf_node} [delta only]"
        return f"E2E Lane Price & Cost Structure per Lot - {product} → {leaf_node}"

    title = f"Price Waterfall Stacked Bar - {product}"
    if direction:
        title += f" ({direction})"
    if leaf_node:
        title += f" route to {leaf_node}"
    if chart_mode == "delta_only":
        title += " [delta_only]"
    return title


def is_all_zero_chart(rows: list[dict[str, str]], components: list[str]) -> bool:
    check_components = list(dict.fromkeys([*ZERO_CHECK_COMPONENTS, *components]))
    for row in rows:
        for component in check_components:
            if _as_float(row.get(component)) != 0.0:
                return False
    return True


def _render_stacked_chart(rows: list[dict[str, str]], output_path: str, title: str, components: list[str]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sorted_rows = sort_waterfall_rows(rows)

    node_labels = [r.get("node_name", "") for r in sorted_rows]
    x = list(range(len(sorted_rows)))

    fig, ax = plt.subplots(figsize=(max(8, len(sorted_rows) * 1.2), 5))
    bottoms = [0.0] * len(sorted_rows)

    for component in components:
        values = [_as_float(r.get(component)) for r in sorted_rows]
        ax.bar(x, values, bottom=bottoms, label=component)
        bottoms = [b + v for b, v in zip(bottoms, values)]

    for i, row in enumerate(sorted_rows):
        ship_price = _as_float(row.get("ship_price_per_lot"))
        ax.text(i, bottoms[i], f"{ship_price:.2f}", ha="center", va="bottom", fontsize=8)

    ax.set_title(title)
    ax.set_xlabel("Node")
    ax.set_ylabel("Price / Cost per lot")
    ax.set_xticks(x)
    ax.set_xticklabels(node_labels, rotation=45, ha="right")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def generate_price_waterfall_stacked_bar(
    node_price_waterfall_csv: str,
    output_dir: str,
    *,
    product: str | None = None,
    direction: str | None = None,
    leaf_node: str | None = None,
    price_propagation_trace_csv: str | None = None,
    e2e_lane_route_csv: str | None = None,
    chart_mode: str = "full_price",
    chart_scope: str = "outbound_only",
    inbound_leaf_node: str | None = None,
    supply_point_node: str = "supply_point",
    skip_all_zero: bool = True,
) -> list[str]:
    rows = load_node_price_waterfall(node_price_waterfall_csv)
    trace_rows = load_price_propagation_trace(price_propagation_trace_csv) if price_propagation_trace_csv else []
    e2e_lane_rows = load_e2e_lane_route(e2e_lane_route_csv) if e2e_lane_route_csv else []
    components = get_chart_components(chart_mode)

    os.makedirs(output_dir, exist_ok=True)

    filtered = []
    for row in rows:
        if product is not None and row.get("product") != product:
            continue
        if direction is not None and (row.get("direction") or None) != direction:
            continue
        filtered.append(row)

    if chart_scope not in {"outbound_only", "e2e_primary"}:
        raise ValueError("Unknown chart_scope: {0}. Supported scopes: outbound_only, e2e_primary".format(chart_scope))

    grouped = group_rows_by_product_and_direction(filtered)
    generated: list[str] = []

    if direction is None:
        product_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
        for (prod, _dir), group in grouped.items():
            product_rows[prod].extend(group)

        for prod, prod_rows in product_rows.items():
            if not prod_rows:
                continue
            working_rows = prod_rows
            if leaf_node and chart_scope == "e2e_primary" and e2e_lane_rows:
                route_rows = select_e2e_lane_route_rows(
                    e2e_lane_rows,
                    product=prod,
                    leaf_node=leaf_node,
                    chart_scope=chart_scope,
                    inbound_leaf_node=inbound_leaf_node,
                )
                route_nodes = build_route_order_from_e2e_lane_rows(route_rows)
                if not route_nodes:
                    route_nodes = build_e2e_lane_route(
                        trace_rows, prod, leaf_node, supply_point_node=supply_point_node, inbound_leaf_node=inbound_leaf_node
                    )
            elif leaf_node and chart_scope == "e2e_primary":
                route_nodes = build_e2e_lane_route(
                    trace_rows, prod, leaf_node, supply_point_node=supply_point_node, inbound_leaf_node=inbound_leaf_node
                )
            else:
                route_nodes = find_route_to_leaf(trace_rows, prod, leaf_node) if leaf_node else build_edge_order_from_trace(trace_rows, prod)
            if leaf_node and route_nodes:
                working_rows = sort_waterfall_rows_by_route(working_rows, route_nodes)
            else:
                working_rows = sort_rows_by_route(working_rows, route_nodes)
            if skip_all_zero and is_all_zero_chart(working_rows, components):
                continue
            suffix = "delta_only" if chart_mode == "delta_only" else "stacked_bar"
            if chart_scope == "e2e_primary" and leaf_node and route_nodes:
                out_name = (
                    f"{_sanitize_filename(prod)}_{_sanitize_filename(leaf_node)}_e2e_lane_added_cost_structure_delta_only.png"
                    if chart_mode == "delta_only"
                    else f"{_sanitize_filename(prod)}_{_sanitize_filename(leaf_node)}_e2e_lane_price_cost_structure.png"
                )
            else:
                route_suffix = "_route" if leaf_node and route_nodes else ""
                out_name = f"{_sanitize_filename(prod)}_price_waterfall{route_suffix}_{suffix}.png"
            out = os.path.join(output_dir, out_name)
            _render_stacked_chart(working_rows, out, build_chart_title(prod, None, chart_mode, leaf_node if route_nodes else None, chart_scope=chart_scope), components)
            generated.append(out)
    else:
        for (prod, dir_key), prod_rows in grouped.items():
            if not prod_rows:
                continue
            working_rows = prod_rows
            if leaf_node and chart_scope == "e2e_primary" and e2e_lane_rows:
                route_rows = select_e2e_lane_route_rows(
                    e2e_lane_rows,
                    product=prod,
                    leaf_node=leaf_node,
                    chart_scope=chart_scope,
                    inbound_leaf_node=inbound_leaf_node,
                )
                route_nodes = build_route_order_from_e2e_lane_rows(route_rows)
                if not route_nodes:
                    route_nodes = build_e2e_lane_route(
                        trace_rows, prod, leaf_node, supply_point_node=supply_point_node, inbound_leaf_node=inbound_leaf_node
                    )
            elif leaf_node and chart_scope == "e2e_primary":
                route_nodes = build_e2e_lane_route(
                    trace_rows, prod, leaf_node, supply_point_node=supply_point_node, inbound_leaf_node=inbound_leaf_node
                )
            else:
                route_nodes = (
                    find_route_to_leaf(trace_rows, prod, leaf_node, dir_key)
                    if leaf_node
                    else build_edge_order_from_trace(trace_rows, prod, dir_key)
                )
            if leaf_node and route_nodes:
                working_rows = sort_waterfall_rows_by_route(working_rows, route_nodes)
            else:
                working_rows = sort_rows_by_route(working_rows, route_nodes)
            if skip_all_zero and is_all_zero_chart(working_rows, components):
                continue

            direction_name = dir_key or "unknown"
            suffix = "delta_only" if chart_mode == "delta_only" else "stacked_bar"
            route_suffix = "_route" if leaf_node and route_nodes else ""
            out = os.path.join(
                output_dir,
                f"{_sanitize_filename(prod)}_{_sanitize_filename(direction_name)}_price_waterfall{route_suffix}_{suffix}.png",
            )
            _render_stacked_chart(
                working_rows,
                out,
                build_chart_title(prod, dir_key, chart_mode, leaf_node if route_nodes else None, chart_scope=chart_scope),
                components,
            )
            generated.append(out)

    return generated
