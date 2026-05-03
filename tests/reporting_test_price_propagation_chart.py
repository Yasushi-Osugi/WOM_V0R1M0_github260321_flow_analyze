import pytest

pytest.importorskip("matplotlib")

import csv

from pysi.reporting.price_propagation_chart import (
    build_edge_order_from_trace,
    build_route_order_from_e2e_lane_rows,
    find_route_to_leaf,
    generate_price_waterfall_stacked_bar,
    get_chart_components,
    load_e2e_lane_route,
    select_e2e_lane_route_rows,
    sort_waterfall_rows_by_route,
    sort_rows_by_route,
    stitch_routes,
    build_e2e_lane_route,
)


def _write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_chart_file_is_generated(tmp_path):
    csv_path = tmp_path / "node_price_waterfall.csv"
    _write_csv(
        csv_path,
        ["product", "direction", "sequence_no", "node_name", "purchase_cost_per_lot", "value_added_cost_per_lot", "ship_price_per_lot"],
        [
            {"product": "A", "direction": "inbound", "sequence_no": "1", "node_name": "N1", "purchase_cost_per_lot": "10", "value_added_cost_per_lot": "2", "ship_price_per_lot": "12"},
            {"product": "A", "direction": "inbound", "sequence_no": "2", "node_name": "N2", "purchase_cost_per_lot": "12", "value_added_cost_per_lot": "3", "ship_price_per_lot": "15"},
        ],
    )
    outputs = generate_price_waterfall_stacked_bar(str(csv_path), str(tmp_path / "out"))
    assert len(outputs) == 1
    assert outputs[0].endswith("A_price_waterfall_stacked_bar.png")
    assert (tmp_path / "out" / "A_price_waterfall_stacked_bar.png").exists()


def test_product_filtering_works(tmp_path):
    csv_path = tmp_path / "node_price_waterfall.csv"
    _write_csv(
        csv_path,
        ["product", "node_name", "ship_price_per_lot", "purchase_cost_per_lot"],
        [
            {"product": "PRODUCT_A", "node_name": "N1", "ship_price_per_lot": "11", "purchase_cost_per_lot": "10"},
            {"product": "PRODUCT_B", "node_name": "N2", "ship_price_per_lot": "21", "purchase_cost_per_lot": "20"},
        ],
    )
    outputs = generate_price_waterfall_stacked_bar(str(csv_path), str(tmp_path / "out"), product="PRODUCT_A")
    assert len(outputs) == 1
    assert outputs[0].endswith("PRODUCT_A_price_waterfall_stacked_bar.png")


def test_missing_optional_columns_treated_as_zero(tmp_path):
    csv_path = tmp_path / "node_price_waterfall.csv"
    _write_csv(
        csv_path,
        ["product", "node_name", "ship_price_per_lot", "purchase_cost_per_lot"],
        [
            {"product": "A", "node_name": "N1", "ship_price_per_lot": "11", "purchase_cost_per_lot": "10"},
            {"product": "A", "node_name": "N2", "ship_price_per_lot": "12", "purchase_cost_per_lot": "11"},
        ],
    )
    outputs = generate_price_waterfall_stacked_bar(str(csv_path), str(tmp_path / "out"))
    assert len(outputs) == 1


def test_direction_filtering_works(tmp_path):
    csv_path = tmp_path / "node_price_waterfall.csv"
    _write_csv(
        csv_path,
        ["product", "direction", "node_name", "ship_price_per_lot", "purchase_cost_per_lot"],
        [
            {"product": "A", "direction": "inbound", "node_name": "N1", "ship_price_per_lot": "11", "purchase_cost_per_lot": "10"},
            {"product": "A", "direction": "outbound", "node_name": "N2", "ship_price_per_lot": "12", "purchase_cost_per_lot": "11"},
        ],
    )
    outputs = generate_price_waterfall_stacked_bar(str(csv_path), str(tmp_path / "out"), direction="inbound")
    assert len(outputs) == 1
    assert outputs[0].endswith("A_inbound_price_waterfall_stacked_bar.png")


def test_route_ordering_from_trace_helpers():
    trace_rows = [
        {"product": "P", "direction": "outbound", "from_node": "supply_point", "to_node": "DAD", "sequence_no": "1"},
        {"product": "P", "direction": "outbound", "from_node": "DAD", "to_node": "CS", "sequence_no": "2"},
    ]
    route_nodes = build_edge_order_from_trace(trace_rows, "P", "outbound")
    rows = [{"node_name": "CS"}, {"node_name": "supply_point"}, {"node_name": "DAD"}]
    sorted_rows = sort_rows_by_route(rows, route_nodes)
    assert [r["node_name"] for r in sorted_rows] == ["supply_point", "DAD", "CS"]


def test_leaf_route_filtering_helper():
    trace_rows = [
        {"product": "P", "direction": "outbound", "from_node": "supply_point", "to_node": "DAD_US", "sequence_no": "1"},
        {"product": "P", "direction": "outbound", "from_node": "DAD_US", "to_node": "CS_US", "sequence_no": "2"},
        {"product": "P", "direction": "outbound", "from_node": "supply_point", "to_node": "DAD_EU", "sequence_no": "3"},
        {"product": "P", "direction": "outbound", "from_node": "DAD_EU", "to_node": "CS_EU", "sequence_no": "4"},
    ]
    assert find_route_to_leaf(trace_rows, "P", "CS_US", "outbound") == ["supply_point", "DAD_US", "CS_US"]


def test_delta_only_excludes_purchase_cost():
    components = get_chart_components("delta_only")
    assert "purchase_cost_per_lot" not in components


def test_all_zero_skip_default(tmp_path):
    csv_path = tmp_path / "node_price_waterfall.csv"
    _write_csv(
        csv_path,
        ["product", "node_name", "ship_price_per_lot", "purchase_cost_per_lot", "value_added_cost_per_lot"],
        [{"product": "A", "node_name": "N1", "ship_price_per_lot": "0", "purchase_cost_per_lot": "0", "value_added_cost_per_lot": "0"}],
    )
    outputs = generate_price_waterfall_stacked_bar(str(csv_path), str(tmp_path / "out"))
    assert outputs == []


def test_all_zero_generated_when_requested(tmp_path):
    csv_path = tmp_path / "node_price_waterfall.csv"
    _write_csv(
        csv_path,
        ["product", "node_name", "ship_price_per_lot", "purchase_cost_per_lot", "value_added_cost_per_lot"],
        [{"product": "A", "node_name": "N1", "ship_price_per_lot": "0", "purchase_cost_per_lot": "0", "value_added_cost_per_lot": "0"}],
    )
    outputs = generate_price_waterfall_stacked_bar(str(csv_path), str(tmp_path / "out"), skip_all_zero=False)
    assert len(outputs) == 1
    assert (tmp_path / "out" / "A_price_waterfall_stacked_bar.png").exists()


def test_stitch_routes_avoids_duplicate_supply_point():
    assert stitch_routes(["MOM", "supply_point"], ["supply_point", "DAD", "CS"]) == ["MOM", "supply_point", "DAD", "CS"]


def test_build_e2e_lane_route():
    trace_rows = [
        {"product": "PRODUCT_A", "direction": "inbound", "from_node": "MOM", "to_node": "supply_point", "sequence_no": "1"},
        {"product": "PRODUCT_A", "direction": "outbound", "from_node": "supply_point", "to_node": "DAD", "sequence_no": "2"},
        {"product": "PRODUCT_A", "direction": "outbound", "from_node": "DAD", "to_node": "CS", "sequence_no": "3"},
    ]
    assert build_e2e_lane_route(trace_rows, "PRODUCT_A", "CS") == ["MOM", "supply_point", "DAD", "CS"]


def test_e2e_full_price_chart_generation(tmp_path):
    csv_path = tmp_path / "node_price_waterfall.csv"
    trace_path = tmp_path / "price_propagation_trace.csv"
    _write_csv(csv_path,["product","direction","sequence_no","node_name","purchase_cost_per_lot","value_added_cost_per_lot","ship_price_per_lot"],[
        {"product":"PRODUCT_A","direction":"inbound","sequence_no":"1","node_name":"MOM","purchase_cost_per_lot":"8","value_added_cost_per_lot":"2","ship_price_per_lot":"10"},
        {"product":"PRODUCT_A","direction":"outbound","sequence_no":"2","node_name":"supply_point","purchase_cost_per_lot":"10","value_added_cost_per_lot":"1","ship_price_per_lot":"11"},
        {"product":"PRODUCT_A","direction":"outbound","sequence_no":"3","node_name":"DAD","purchase_cost_per_lot":"11","value_added_cost_per_lot":"2","ship_price_per_lot":"13"},
        {"product":"PRODUCT_A","direction":"outbound","sequence_no":"4","node_name":"CS","purchase_cost_per_lot":"13","value_added_cost_per_lot":"3","ship_price_per_lot":"16"},
    ])
    _write_csv(trace_path,["product","direction","sequence_no","from_node","to_node"],[
        {"product":"PRODUCT_A","direction":"inbound","sequence_no":"1","from_node":"MOM","to_node":"supply_point"},
        {"product":"PRODUCT_A","direction":"outbound","sequence_no":"2","from_node":"supply_point","to_node":"DAD"},
        {"product":"PRODUCT_A","direction":"outbound","sequence_no":"3","from_node":"DAD","to_node":"CS"},
    ])
    outputs = generate_price_waterfall_stacked_bar(str(csv_path), str(tmp_path / "out"), product="PRODUCT_A", leaf_node="CS", price_propagation_trace_csv=str(trace_path), chart_mode="full_price", chart_scope="e2e_primary")
    assert len(outputs) == 1
    assert outputs[0].endswith("PRODUCT_A_CS_e2e_lane_price_cost_structure.png")
    assert (tmp_path / "out" / "PRODUCT_A_CS_e2e_lane_price_cost_structure.png").stat().st_size > 0


def test_e2e_delta_only_chart_generation(tmp_path):
    assert "purchase_cost_per_lot" not in get_chart_components("delta_only")


def test_e2e_fallback_to_outbound_route_when_inbound_missing(tmp_path):
    csv_path = tmp_path / "node_price_waterfall.csv"
    trace_path = tmp_path / "price_propagation_trace.csv"
    _write_csv(csv_path,["product","direction","sequence_no","node_name","purchase_cost_per_lot","value_added_cost_per_lot","ship_price_per_lot"],[
        {"product":"PRODUCT_A","direction":"outbound","sequence_no":"2","node_name":"supply_point","purchase_cost_per_lot":"10","value_added_cost_per_lot":"1","ship_price_per_lot":"11"},
        {"product":"PRODUCT_A","direction":"outbound","sequence_no":"3","node_name":"DAD","purchase_cost_per_lot":"11","value_added_cost_per_lot":"2","ship_price_per_lot":"13"},
        {"product":"PRODUCT_A","direction":"outbound","sequence_no":"4","node_name":"CS","purchase_cost_per_lot":"13","value_added_cost_per_lot":"3","ship_price_per_lot":"16"},
    ])
    _write_csv(trace_path,["product","direction","sequence_no","from_node","to_node"],[
        {"product":"PRODUCT_A","direction":"outbound","sequence_no":"2","from_node":"supply_point","to_node":"DAD"},
        {"product":"PRODUCT_A","direction":"outbound","sequence_no":"3","from_node":"DAD","to_node":"CS"},
    ])
    outputs = generate_price_waterfall_stacked_bar(str(csv_path), str(tmp_path / "out"), product="PRODUCT_A", leaf_node="CS", price_propagation_trace_csv=str(trace_path), chart_scope="e2e_primary")
    assert len(outputs) == 1


def test_e2e_route_display_order():
    trace_rows = [
        {"product": "PRODUCT_A", "direction": "inbound", "from_node": "MOM", "to_node": "supply_point", "sequence_no": "1"},
        {"product": "PRODUCT_A", "direction": "outbound", "from_node": "supply_point", "to_node": "DAD", "sequence_no": "2"},
        {"product": "PRODUCT_A", "direction": "outbound", "from_node": "DAD", "to_node": "CS", "sequence_no": "3"},
    ]
    assert build_e2e_lane_route(trace_rows, "PRODUCT_A", "CS") == ["MOM", "supply_point", "DAD", "CS"]


def test_load_e2e_lane_route_and_build_order(tmp_path):
    route_path = tmp_path / "e2e_lane_route.csv"
    _write_csv(
        route_path,
        ["product", "leaf_node", "inbound_leaf_node", "chart_scope", "sequence_no", "node_name"],
        [
            {"product": "P", "leaf_node": "CS", "inbound_leaf_node": "", "chart_scope": "e2e_primary", "sequence_no": "1", "node_name": "MOM"},
            {"product": "P", "leaf_node": "CS", "inbound_leaf_node": "", "chart_scope": "e2e_primary", "sequence_no": "2", "node_name": "supply_point"},
            {"product": "P", "leaf_node": "CS", "inbound_leaf_node": "", "chart_scope": "e2e_primary", "sequence_no": "3", "node_name": "DAD"},
            {"product": "P", "leaf_node": "CS", "inbound_leaf_node": "", "chart_scope": "e2e_primary", "sequence_no": "4", "node_name": "CS"},
        ],
    )
    rows = load_e2e_lane_route(str(route_path))
    selected = select_e2e_lane_route_rows(rows, product="P", leaf_node="CS", chart_scope="e2e_primary")
    assert build_route_order_from_e2e_lane_rows(selected) == ["MOM", "supply_point", "DAD", "CS"]


def test_sort_waterfall_rows_by_e2e_route_and_exclude_extra_nodes():
    route_nodes = ["MOM", "supply_point", "DAD", "CS"]
    rows = [{"node_name": "CS"}, {"node_name": "DAD"}, {"node_name": "MOM"}, {"node_name": "OTHER_NODE"}, {"node_name": "supply_point"}]
    sorted_rows = sort_waterfall_rows_by_route(rows, route_nodes)
    assert [r["node_name"] for r in sorted_rows] == ["MOM", "supply_point", "DAD", "CS"]


def test_e2e_chart_with_route_csv_allows_unknown_waterfall_direction(tmp_path):
    csv_path = tmp_path / "node_price_waterfall.csv"
    trace_path = tmp_path / "price_propagation_trace.csv"
    route_path = tmp_path / "e2e_lane_route.csv"
    _write_csv(csv_path,["product","direction","sequence_no","node_name","purchase_cost_per_lot","value_added_cost_per_lot","ship_price_per_lot"],[
        {"product":"PRODUCT_A","direction":"unknown","sequence_no":"4","node_name":"CS","purchase_cost_per_lot":"13","value_added_cost_per_lot":"3","ship_price_per_lot":"16"},
        {"product":"PRODUCT_A","direction":"unknown","sequence_no":"3","node_name":"DAD","purchase_cost_per_lot":"11","value_added_cost_per_lot":"2","ship_price_per_lot":"13"},
        {"product":"PRODUCT_A","direction":"unknown","sequence_no":"1","node_name":"MOM","purchase_cost_per_lot":"8","value_added_cost_per_lot":"2","ship_price_per_lot":"10"},
        {"product":"PRODUCT_A","direction":"unknown","sequence_no":"2","node_name":"supply_point","purchase_cost_per_lot":"10","value_added_cost_per_lot":"1","ship_price_per_lot":"11"},
        {"product":"PRODUCT_A","direction":"unknown","sequence_no":"5","node_name":"OTHER_NODE","purchase_cost_per_lot":"1","value_added_cost_per_lot":"1","ship_price_per_lot":"2"},
    ])
    _write_csv(trace_path,["product","direction","sequence_no","from_node","to_node"],[])
    _write_csv(route_path,["product","lane_id","leaf_node","inbound_leaf_node","chart_scope","sequence_no","segment","direction","node_name"],[
        {"product":"PRODUCT_A","lane_id":"L1","leaf_node":"CS","inbound_leaf_node":"","chart_scope":"e2e_primary","sequence_no":"1","segment":"inbound","direction":"IN","node_name":"MOM"},
        {"product":"PRODUCT_A","lane_id":"L1","leaf_node":"CS","inbound_leaf_node":"","chart_scope":"e2e_primary","sequence_no":"2","segment":"bridge","direction":"OUT","node_name":"supply_point"},
        {"product":"PRODUCT_A","lane_id":"L1","leaf_node":"CS","inbound_leaf_node":"","chart_scope":"e2e_primary","sequence_no":"3","segment":"outbound","direction":"OUT","node_name":"DAD"},
        {"product":"PRODUCT_A","lane_id":"L1","leaf_node":"CS","inbound_leaf_node":"","chart_scope":"e2e_primary","sequence_no":"4","segment":"outbound","direction":"OUT","node_name":"CS"},
    ])
    outputs = generate_price_waterfall_stacked_bar(str(csv_path), str(tmp_path / "out"), product="PRODUCT_A", leaf_node="CS", price_propagation_trace_csv=str(trace_path), e2e_lane_route_csv=str(route_path), chart_mode="full_price", chart_scope="e2e_primary")
    assert len(outputs) == 1
    assert (tmp_path / "out" / "PRODUCT_A_CS_e2e_lane_price_cost_structure.png").stat().st_size > 0


def test_e2e_delta_only_chart_generation_with_route_csv(tmp_path):
    csv_path = tmp_path / "node_price_waterfall.csv"
    route_path = tmp_path / "e2e_lane_route.csv"
    _write_csv(csv_path,["product","direction","sequence_no","node_name","purchase_cost_per_lot","value_added_cost_per_lot","ship_price_per_lot"],[
        {"product":"PRODUCT_A","direction":"unknown","sequence_no":"1","node_name":"MOM","purchase_cost_per_lot":"8","value_added_cost_per_lot":"2","ship_price_per_lot":"10"},
        {"product":"PRODUCT_A","direction":"unknown","sequence_no":"2","node_name":"supply_point","purchase_cost_per_lot":"10","value_added_cost_per_lot":"1","ship_price_per_lot":"11"},
        {"product":"PRODUCT_A","direction":"unknown","sequence_no":"3","node_name":"DAD","purchase_cost_per_lot":"11","value_added_cost_per_lot":"2","ship_price_per_lot":"13"},
        {"product":"PRODUCT_A","direction":"unknown","sequence_no":"4","node_name":"CS","purchase_cost_per_lot":"13","value_added_cost_per_lot":"3","ship_price_per_lot":"16"},
    ])
    _write_csv(route_path,["product","lane_id","leaf_node","inbound_leaf_node","chart_scope","sequence_no","node_name"],[
        {"product":"PRODUCT_A","lane_id":"L1","leaf_node":"CS","inbound_leaf_node":"","chart_scope":"e2e_primary","sequence_no":"1","node_name":"MOM"},
        {"product":"PRODUCT_A","lane_id":"L1","leaf_node":"CS","inbound_leaf_node":"","chart_scope":"e2e_primary","sequence_no":"2","node_name":"supply_point"},
        {"product":"PRODUCT_A","lane_id":"L1","leaf_node":"CS","inbound_leaf_node":"","chart_scope":"e2e_primary","sequence_no":"3","node_name":"DAD"},
        {"product":"PRODUCT_A","lane_id":"L1","leaf_node":"CS","inbound_leaf_node":"","chart_scope":"e2e_primary","sequence_no":"4","node_name":"CS"},
    ])
    outputs = generate_price_waterfall_stacked_bar(str(csv_path), str(tmp_path / "out"), product="PRODUCT_A", leaf_node="CS", e2e_lane_route_csv=str(route_path), chart_mode="delta_only", chart_scope="e2e_primary")
    assert len(outputs) == 1
    assert outputs[0].endswith("PRODUCT_A_CS_e2e_lane_added_cost_structure_delta_only.png")
