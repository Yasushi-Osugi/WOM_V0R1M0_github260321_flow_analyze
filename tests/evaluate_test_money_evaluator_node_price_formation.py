from dataclasses import dataclass

from pysi.evaluate.money_evaluator import _build_unit_price_table


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
    standard_volume_lots_per_week: float = 0.0


class _Node:
    def __init__(self, name, children=None):
        self.name = name
        self.children = children or []
        self.psi4supply = []


class _Bundle:
    def __init__(self, node_product_rows):
        self._node_product_rows = node_product_rows

    def get_node_character(self, node_name):
        return "DAD"

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


def _build_env(row):
    node = _Node("N")
    bundle = _Bundle({("N", "P"): row})
    return _Env(node, bundle)


def test_explicit_ship_price_is_preserved():
    env = _build_env(
        _MoneyRow(
            purchase_cost_per_lot=600,
            variable_cost_per_lot=50,
            fixed_cost_per_lot=20,
            target_profit_per_lot=100,
            ship_price_per_lot=900,
        )
    )
    row = _build_unit_price_table(env)[("N", "P")]
    assert row.ship_price_per_lot == 900
    assert row.price_formation_mode == "explicit_ship_price"


def test_ship_price_calculated_when_explicit_zero():
    env = _build_env(
        _MoneyRow(
            purchase_cost_per_lot=600,
            value_added_cost_per_lot=40,
            variable_cost_per_lot=50,
            fixed_cost_per_lot=20,
            logistics_cost_per_lot=30,
            tax_tariff_cost_per_lot=10,
            target_profit_per_lot=100,
            ship_price_per_lot=0,
        )
    )
    row = _build_unit_price_table(env)[("N", "P")]
    assert row.ship_price_per_lot == 850
    assert row.price_formation_mode == "calculated_from_cost_components"


def test_inventory_unit_value_is_not_added_to_ship_price():
    env = _build_env(
        _MoneyRow(
            purchase_cost_per_lot=600,
            inventory_unit_value_per_lot=9999,
            variable_cost_per_lot=50,
            target_profit_per_lot=100,
            ship_price_per_lot=0,
        )
    )
    row = _build_unit_price_table(env)[("N", "P")]
    assert row.ship_price_per_lot == 750


def test_fixed_cost_per_lot_allocation_from_standard_volume():
    env = _build_env(
        _MoneyRow(
            fixed_cost_per_week=1000,
            standard_volume_lots_per_week=100,
            ship_price_per_lot=1,
        )
    )
    row = _build_unit_price_table(env)[("N", "P")]
    assert row.fixed_cost_per_lot == 10
