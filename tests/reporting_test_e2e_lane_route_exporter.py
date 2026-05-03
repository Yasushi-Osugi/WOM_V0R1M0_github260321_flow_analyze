import csv

from pysi.reporting.e2e_lane_route_exporter import (
    export_e2e_lane_route,
    find_path_ending_at_supply_point,
    find_path_to_node,
    stitch_inbound_outbound_routes,
)


class Node:
    def __init__(self, name, children=None):
        self.name = name
        self.children = children or []


def test_find_outbound_path_to_leaf():
    root = Node("supply_point", [Node("DAD", [Node("CS")])])
    assert find_path_to_node(root, "CS") == ["supply_point", "DAD", "CS"]


def test_find_inbound_path_to_supply_point():
    root = Node("MOM", [Node("supply_point")])
    assert find_path_ending_at_supply_point(root) == ["MOM", "supply_point"]


def test_stitch_inbound_and_outbound_routes():
    assert stitch_inbound_outbound_routes(["MOM", "supply_point"], ["supply_point", "DAD", "CS"]) == ["MOM", "supply_point", "DAD", "CS"]


def test_export_e2e_lane_route_rows(tmp_path):
    in_root = Node("MOM", [Node("supply_point")])
    out_root = Node("supply_point", [Node("DAD", [Node("CS")])])
    output_path = tmp_path / "e2e_lane_route.csv"

    rows = export_e2e_lane_route(
        product_name="PRODUCT_A",
        prod_tree_dict_IN={"PRODUCT_A": in_root},
        prod_tree_dict_OT={"PRODUCT_A": out_root},
        output_path=str(output_path),
        leaf_node="CS",
    )

    assert [r["node_name"] for r in rows] == ["MOM", "supply_point", "DAD", "CS"]
    assert [r["sequence_no"] for r in rows] == [1, 2, 3, 4]


def test_fallback_outbound_only_if_inbound_missing(tmp_path):
    out_root = Node("supply_point", [Node("DAD", [Node("CS")])])
    output_path = tmp_path / "e2e_lane_route.csv"

    rows = export_e2e_lane_route(
        product_name="PRODUCT_A",
        prod_tree_dict_IN={},
        prod_tree_dict_OT={"PRODUCT_A": out_root},
        output_path=str(output_path),
        leaf_node="CS",
    )

    assert [r["node_name"] for r in rows] == ["supply_point", "DAD", "CS"]
    assert "inbound route not found" in rows[0]["remarks"]


def test_required_columns_exist(tmp_path):
    in_root = Node("MOM", [Node("supply_point")])
    out_root = Node("supply_point", [Node("DAD", [Node("CS")])])
    output_path = tmp_path / "e2e_lane_route.csv"

    export_e2e_lane_route(
        product_name="PRODUCT_A",
        prod_tree_dict_IN={"PRODUCT_A": in_root},
        prod_tree_dict_OT={"PRODUCT_A": out_root},
        output_path=str(output_path),
        leaf_node="CS",
    )

    with open(output_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        row = next(reader)

    for col in [
        "product",
        "lane_id",
        "leaf_node",
        "sequence_no",
        "segment",
        "direction",
        "node_name",
        "parent_node",
        "child_node",
        "is_supply_point",
        "source_tree",
        "remarks",
    ]:
        assert col in row
