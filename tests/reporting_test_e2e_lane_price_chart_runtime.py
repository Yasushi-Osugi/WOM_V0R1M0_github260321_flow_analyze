import csv

import pytest

pytest.importorskip("matplotlib")

from pysi.reporting.e2e_lane_price_chart_runtime import generate_e2e_lane_price_chart_from_env


class Node:
    def __init__(self, name, children=None):
        self.name = name
        self.children = children or []


class FakeEnv:
    def __init__(self, prod_tree_dict_IN=None, prod_tree_dict_OT=None):
        self.prod_tree_dict_IN = prod_tree_dict_IN if prod_tree_dict_IN is not None else {}
        self.prod_tree_dict_OT = prod_tree_dict_OT if prod_tree_dict_OT is not None else {}


def _write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_env():
    in_root = Node("MOM", [Node("supply_point")])
    out_root = Node("supply_point", [Node("DAD", [Node("CS")])])
    return FakeEnv(prod_tree_dict_IN={"PRODUCT_A": in_root}, prod_tree_dict_OT={"PRODUCT_A": out_root})


def _write_inputs(tmp_path):
    waterfall_path = tmp_path / "node_price_waterfall.csv"
    trace_path = tmp_path / "price_propagation_trace.csv"
    _write_csv(
        waterfall_path,
        ["product", "direction", "sequence_no", "node_name", "purchase_cost_per_lot", "value_added_cost_per_lot", "ship_price_per_lot"],
        [
            {"product": "PRODUCT_A", "direction": "inbound", "sequence_no": "1", "node_name": "MOM", "purchase_cost_per_lot": "8", "value_added_cost_per_lot": "2", "ship_price_per_lot": "10"},
            {"product": "PRODUCT_A", "direction": "outbound", "sequence_no": "2", "node_name": "supply_point", "purchase_cost_per_lot": "10", "value_added_cost_per_lot": "1", "ship_price_per_lot": "11"},
            {"product": "PRODUCT_A", "direction": "outbound", "sequence_no": "3", "node_name": "DAD", "purchase_cost_per_lot": "11", "value_added_cost_per_lot": "2", "ship_price_per_lot": "13"},
            {"product": "PRODUCT_A", "direction": "outbound", "sequence_no": "4", "node_name": "CS", "purchase_cost_per_lot": "13", "value_added_cost_per_lot": "3", "ship_price_per_lot": "16"},
        ],
    )
    _write_csv(
        trace_path,
        ["product", "direction", "sequence_no", "from_node", "to_node"],
        [
            {"product": "PRODUCT_A", "direction": "inbound", "sequence_no": "1", "from_node": "MOM", "to_node": "supply_point"},
            {"product": "PRODUCT_A", "direction": "outbound", "sequence_no": "2", "from_node": "supply_point", "to_node": "DAD"},
            {"product": "PRODUCT_A", "direction": "outbound", "sequence_no": "3", "from_node": "DAD", "to_node": "CS"},
        ],
    )
    return waterfall_path, trace_path


def test_one_shot_generates_route_and_both_charts(tmp_path):
    env = _build_env()
    waterfall_path, trace_path = _write_inputs(tmp_path)
    route_path = tmp_path / "e2e_lane_route.csv"
    output_dir = tmp_path / "out"

    result = generate_e2e_lane_price_chart_from_env(
        env,
        product_name="PRODUCT_A",
        leaf_node="CS",
        node_price_waterfall_csv=str(waterfall_path),
        price_propagation_trace_csv=str(trace_path),
        e2e_lane_route_csv=str(route_path),
        output_dir=str(output_dir),
    )

    assert result["errors"] == []
    assert result["route_rows"]
    assert len(result["generated_files"]) == 2
    assert route_path.exists()
    for output in result["generated_files"]:
        assert output.endswith(".png")
        assert output_dir.joinpath(output.split("/")[-1]).exists()


def test_full_price_only(tmp_path):
    env = _build_env()
    waterfall_path, trace_path = _write_inputs(tmp_path)
    result = generate_e2e_lane_price_chart_from_env(
        env,
        product_name="PRODUCT_A",
        leaf_node="CS",
        node_price_waterfall_csv=str(waterfall_path),
        price_propagation_trace_csv=str(trace_path),
        e2e_lane_route_csv=str(tmp_path / "route.csv"),
        output_dir=str(tmp_path / "out"),
        generate_delta_only=False,
    )
    assert len(result["generated_files"]) == 1
    assert result["generated_files"][0].endswith("e2e_lane_price_cost_structure.png")


def test_delta_only_only(tmp_path):
    env = _build_env()
    waterfall_path, trace_path = _write_inputs(tmp_path)
    result = generate_e2e_lane_price_chart_from_env(
        env,
        product_name="PRODUCT_A",
        leaf_node="CS",
        node_price_waterfall_csv=str(waterfall_path),
        price_propagation_trace_csv=str(trace_path),
        e2e_lane_route_csv=str(tmp_path / "route.csv"),
        output_dir=str(tmp_path / "out"),
        generate_full_price=False,
    )
    assert len(result["generated_files"]) == 1
    assert result["generated_files"][0].endswith("e2e_lane_added_cost_structure_delta_only.png")


def test_env_none_safe():
    result = generate_e2e_lane_price_chart_from_env(None, product_name="PRODUCT_A", leaf_node="CS")
    assert result["errors"]
    assert result["generated_files"] == []


def test_blank_product_safe(tmp_path):
    result = generate_e2e_lane_price_chart_from_env(_build_env(), product_name="", leaf_node="CS")
    assert result["errors"]
    assert result["generated_files"] == []


def test_blank_leaf_safe():
    result = generate_e2e_lane_price_chart_from_env(_build_env(), product_name="PRODUCT_A", leaf_node="")
    assert result["errors"]
    assert result["generated_files"] == []


def test_missing_waterfall_csv_safe(tmp_path):
    env = _build_env()
    _, trace_path = _write_inputs(tmp_path)
    result = generate_e2e_lane_price_chart_from_env(
        env,
        product_name="PRODUCT_A",
        leaf_node="CS",
        node_price_waterfall_csv=str(tmp_path / "missing.csv"),
        price_propagation_trace_csv=str(trace_path),
    )
    assert result["errors"] or result["warnings"]
    assert result["generated_files"] == []
