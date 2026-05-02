from dataclasses import dataclass

from pysi.evaluate.money_evaluator import _build_unit_price_table, _build_weekly_money_rows


@dataclass
class _MoneyRow:
    purchase_cost_per_lot: float = 0.0
    ship_price_per_lot: float = 0.0
    inventory_unit_value_per_lot: float = 0.0
    variable_cost_per_lot: float = 0.0
    fixed_cost_per_week: float = 0.0
    tax_rate: float = 0.0


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
        self.prod_tree_dict_OT = {"SMART_WASHER_2028_BASE": root}
        self.prod_tree_dict_IN = {}
        self.money_master_bundle = bundle


def _make_env(child_purchase_cost=0.0):
    child = _Node("CS_US_ECOM")
    parent = _Node("DAD_US_CENTRAL_DC", children=[child])
    parent.psi4supply = [[[1], [1], [], [1]]]
    child.psi4supply = [[[1], [1, 2], [], [1, 2]]]

    bundle = _Bundle(
        {
            ("DAD_US_CENTRAL_DC", "SMART_WASHER_2028_BASE"): _MoneyRow(ship_price_per_lot=700.0),
            ("CS_US_ECOM", "SMART_WASHER_2028_BASE"): _MoneyRow(
                ship_price_per_lot=800.0,
                purchase_cost_per_lot=child_purchase_cost,
            ),
        }
    )
    return _Env(parent, bundle)


def test_parent_ship_price_propagates_to_child_purchase_cost_when_zero():
    env = _make_env(child_purchase_cost=0.0)
    table = _build_unit_price_table(env)
    child = table[("CS_US_ECOM", "SMART_WASHER_2028_BASE")]
    assert child.purchase_cost_per_lot == 700.0


def test_explicit_child_purchase_cost_is_not_overwritten():
    env = _make_env(child_purchase_cost=650.0)
    table = _build_unit_price_table(env)
    child = table[("CS_US_ECOM", "SMART_WASHER_2028_BASE")]
    assert child.purchase_cost_per_lot == 650.0


def test_purchase_amount_becomes_non_zero_with_propagated_purchase_cost():
    env = _make_env(child_purchase_cost=0.0)
    table = _build_unit_price_table(env)
    weekly = _build_weekly_money_rows(env, table)
    child_week = [r for r in weekly if r.node_name == "CS_US_ECOM"][0]
    assert child_week.purchase_amount > 0.0


def test_revenue_uses_ship_price_unchanged():
    env = _make_env(child_purchase_cost=0.0)
    table = _build_unit_price_table(env)
    weekly = _build_weekly_money_rows(env, table)
    child_week = [r for r in weekly if r.node_name == "CS_US_ECOM"][0]
    assert child_week.revenue == 800.0
