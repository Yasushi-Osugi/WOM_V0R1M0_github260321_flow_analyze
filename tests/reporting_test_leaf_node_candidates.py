from types import SimpleNamespace

from pysi.reporting.leaf_node_candidates import get_leaf_node_candidates_for_product


class FakeNode:
    def __init__(self, name, children=None):
        self.name = name
        self.children = children or []


def test_product_specific_plan_tree_leaves_priority():
    tree = FakeNode("supply_point", [FakeNode("DAD", [FakeNode("CS_B"), FakeNode("CS_A")])])
    env = SimpleNamespace(prod_tree_dict_OT={"P": tree}, leaf_nodes_out=["X"])
    assert get_leaf_node_candidates_for_product(env, product_name="P") == ["CS_A", "CS_B"]


def test_fallback_to_env_leaf_nodes_out():
    env = SimpleNamespace(prod_tree_dict_OT={}, leaf_nodes_out=["CS_B", "CS_A"])
    assert get_leaf_node_candidates_for_product(env, product_name="P") == ["CS_A", "CS_B"]


def test_fallback_to_trace_csv(tmp_path):
    trace = tmp_path / "price_propagation_trace.csv"
    trace.write_text(
        "product,direction,from_node,to_node\n"
        "P,outbound,supply_point,DAD\n"
        "P,outbound,DAD,CS_A\n"
        "P,outbound,DAD,CS_B\n",
        encoding="utf-8",
    )
    env = SimpleNamespace(prod_tree_dict_OT={}, leaf_nodes_out=[])
    assert get_leaf_node_candidates_for_product(env, product_name="P", price_propagation_trace_csv=str(trace)) == ["CS_A", "CS_B"]


def test_trace_fallback_product_filter(tmp_path):
    trace = tmp_path / "price_propagation_trace.csv"
    trace.write_text(
        "product,direction,from_node,to_node\n"
        "P1,outbound,supply_point,DAD\n"
        "P1,outbound,DAD,CS_A\n"
        "P2,outbound,supply_point,DAD2\n"
        "P2,outbound,DAD2,CS_Z\n",
        encoding="utf-8",
    )
    env = SimpleNamespace(prod_tree_dict_OT={}, leaf_nodes_out=[])
    assert get_leaf_node_candidates_for_product(env, product_name="P1", price_propagation_trace_csv=str(trace)) == ["CS_A"]


def test_sorted_unique_output():
    env = SimpleNamespace(prod_tree_dict_OT={}, leaf_nodes_out=["CS_B", "CS_A", "CS_A", "CS_B"])
    assert get_leaf_node_candidates_for_product(env, product_name="P") == ["CS_A", "CS_B"]


def test_object_leaf_nodes_out_extract_name():
    env = SimpleNamespace(
        prod_tree_dict_OT={},
        leaf_nodes_out=[SimpleNamespace(name="CS_B"), SimpleNamespace(name="CS_A")],
    )
    assert get_leaf_node_candidates_for_product(env, product_name="P") == ["CS_A", "CS_B"]
