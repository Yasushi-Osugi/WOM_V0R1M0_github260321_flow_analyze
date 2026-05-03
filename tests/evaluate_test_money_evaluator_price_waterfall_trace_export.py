import csv
from dataclasses import dataclass

from pysi.evaluate.money_evaluator import evaluate_money_by_node, build_kpi_summary, build_product_money_summary
from pysi.evaluate.money_output_exporter import export_money_outputs


@dataclass
class _MoneyRow:
    purchase_cost_per_lot: float = 0.0
    ship_price_per_lot: float = 0.0
    inventory_unit_value_per_lot: float = 0.0
    variable_cost_per_lot: float = 0.0
    fixed_cost_per_week: float = 0.0
    fixed_cost_per_lot: float = 0.0
    value_added_cost_per_lot: float = 0.0
    logistics_cost_per_lot: float = 0.0
    inventory_handling_cost_per_lot: float = 0.0
    tax_rate: float = 0.0
    tax_tariff_cost_per_lot: float = 0.0
    target_profit_per_lot: float = 0.0


class _Node:
    def __init__(self, name, children=None):
        self.name = name
        self.children = children or []
        self.psi4supply = []


class _Bundle:
    def __init__(self, node_product_rows):
        self._node_product_rows = node_product_rows

    def get_node_character(self, node_name):
        return "DAD" if "DAD" in node_name else "CS"

    def get_node_product_money(self, node_name, product_name):
        return self._node_product_rows.get((node_name, product_name))

    def get_node_character_policy(self, node_character):
        return None

    def get_edge_product_money(self, from_node, to_node, product_name):
        return None

    def get_valuation_policy(self, product_name):
        return None


class _Env:
    def __init__(self, root, bundle):
        self.prod_tree_dict_OT = {"P": root}
        self.prod_tree_dict_IN = {}
        self.money_master_bundle = bundle


def _make_env(child_purchase=700.0, child_ship=850.0, child_inventory=9999.0):
    child = _Node("CS_US_ECOM")
    parent = _Node("DAD_US_CENTRAL_DC", children=[child])
    parent.psi4supply = [[[1], [1], [], [1]]]
    child.psi4supply = [[[1], [1], [], [1]]]
    bundle = _Bundle(
        {
            ("DAD_US_CENTRAL_DC", "P"): _MoneyRow(ship_price_per_lot=700.0),
            ("CS_US_ECOM", "P"): _MoneyRow(
                purchase_cost_per_lot=child_purchase,
                ship_price_per_lot=child_ship,
                fixed_cost_per_lot=20.0,
                target_profit_per_lot=100.0,
                inventory_unit_value_per_lot=child_inventory,
            ),
        }
    )
    return _Env(parent, bundle)


def _run_export(tmp_path, env):
    node_rows = evaluate_money_by_node(env)
    paths = export_money_outputs(
        str(tmp_path),
        node_rows,
        build_kpi_summary(node_rows),
        build_product_money_summary(node_rows),
        env=env,
    )
    return paths


def test_node_price_waterfall_columns_exist(tmp_path):
    paths = _run_export(tmp_path, _make_env())
    with open(paths["node_price_waterfall_csv"], newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
    for col in ["product", "node_name", "purchase_cost_per_lot", "ship_price_per_lot", "fixed_cost_per_lot", "target_profit_per_lot", "price_formation_mode"]:
        assert col in headers


def test_inventory_unit_value_remains_separate(tmp_path):
    paths = _run_export(tmp_path, _make_env(child_purchase=700.0, child_ship=850.0, child_inventory=9999.0))
    with open(paths["node_price_waterfall_csv"], newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    child = [r for r in rows if r["node_name"] == "CS_US_ECOM"][0]
    assert float(child["inventory_unit_value_per_lot"]) == 9999.0
    assert float(child["ship_price_per_lot"]) == 850.0


def test_price_propagation_trace_parent_child_movement(tmp_path):
    paths = _run_export(tmp_path, _make_env(child_purchase=700.0, child_ship=850.0))
    with open(paths["price_propagation_trace_csv"], newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    row = rows[0]
    assert float(row["delta_parent_ship_to_child_purchase"]) == 0.0
    assert float(row["delta_child_purchase_to_child_ship"]) == 150.0


def test_explicit_child_purchase_cost_is_visible(tmp_path):
    paths = _run_export(tmp_path, _make_env(child_purchase=650.0, child_ship=850.0))
    with open(paths["price_propagation_trace_csv"], newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    row = rows[0]
    assert row["purchase_cost_source"] == "explicit"
    assert float(row["delta_parent_ship_to_child_purchase"]) == -50.0
