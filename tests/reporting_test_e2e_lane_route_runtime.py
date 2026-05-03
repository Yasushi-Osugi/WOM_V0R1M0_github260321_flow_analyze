import csv

from pysi.reporting.e2e_lane_route_runtime import export_e2e_lane_route_from_env


class Node:
    def __init__(self, name, children=None):
        self.name = name
        self.children = children or []


class FakeEnv:
    def __init__(self, prod_tree_dict_IN=None, prod_tree_dict_OT=None):
        self.prod_tree_dict_IN = prod_tree_dict_IN if prod_tree_dict_IN is not None else {}
        self.prod_tree_dict_OT = prod_tree_dict_OT if prod_tree_dict_OT is not None else {}


class EmptyEnv:
    pass


def test_export_route_from_runtime_env(tmp_path):
    in_root = Node("MOM", [Node("supply_point")])
    out_root = Node("supply_point", [Node("DAD", [Node("CS")])])
    env = FakeEnv(prod_tree_dict_IN={"PRODUCT_A": in_root}, prod_tree_dict_OT={"PRODUCT_A": out_root})
    output_path = tmp_path / "e2e_lane_route.csv"

    rows = export_e2e_lane_route_from_env(
        env,
        product_name="PRODUCT_A",
        leaf_node="CS",
        output_path=str(output_path),
    )

    assert rows
    assert output_path.exists()
    assert [r["node_name"] for r in rows] == ["MOM", "supply_point", "DAD", "CS"]

    with open(output_path, newline="", encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))
    assert [r["node_name"] for r in csv_rows] == ["MOM", "supply_point", "DAD", "CS"]


def test_missing_inbound_tree_falls_back_safely(tmp_path):
    out_root = Node("supply_point", [Node("DAD", [Node("CS")])])
    env = FakeEnv(prod_tree_dict_IN={}, prod_tree_dict_OT={"PRODUCT_A": out_root})
    output_path = tmp_path / "e2e_lane_route.csv"

    rows = export_e2e_lane_route_from_env(
        env,
        product_name="PRODUCT_A",
        leaf_node="CS",
        output_path=str(output_path),
    )

    assert [r["node_name"] for r in rows] == ["supply_point", "DAD", "CS"]
    assert "inbound route not found" in rows[0]["remarks"]


def test_missing_env_attrs_returns_empty_safely():
    assert export_e2e_lane_route_from_env(EmptyEnv(), product_name="PRODUCT_A", leaf_node="CS") == []


def test_env_none_returns_empty_safely():
    assert export_e2e_lane_route_from_env(None, product_name="PRODUCT_A", leaf_node="CS") == []


def test_blank_product_name_returns_empty_safely():
    env = FakeEnv()
    assert export_e2e_lane_route_from_env(env, product_name="", leaf_node="CS") == []
    assert export_e2e_lane_route_from_env(env, product_name="   ", leaf_node="CS") == []


def test_optional_inbound_leaf_node_is_passed_through(tmp_path):
    in_root = Node("MOM", [Node("supply_point"), Node("MOM_ALT", [Node("supply_point")])])
    out_root = Node("supply_point", [Node("DAD", [Node("CS")])])
    env = FakeEnv(prod_tree_dict_IN={"PRODUCT_A": in_root}, prod_tree_dict_OT={"PRODUCT_A": out_root})
    output_path = tmp_path / "e2e_lane_route.csv"

    rows = export_e2e_lane_route_from_env(
        env,
        product_name="PRODUCT_A",
        leaf_node="CS",
        inbound_leaf_node="MOM",
        output_path=str(output_path),
    )

    assert rows
    assert rows[0]["node_name"] == "MOM"
