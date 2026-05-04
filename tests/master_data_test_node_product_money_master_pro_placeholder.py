import csv
from pathlib import Path


def test_pro_money_master_rows_cover_base_nodes_and_have_nonzero_values():
    path = Path("pysi/master_data/node_product_money_master.csv")
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    assert rows

    product_col = "product_name" if "product_name" in rows[0] else "product"
    node_col = "node_name" if "node_name" in rows[0] else "node"

    base_nodes = {
        r[node_col]
        for r in rows
        if r.get(product_col) == "IPHONE_NM_2028_BASE"
    }
    pro_rows = [
        r
        for r in rows
        if r.get(product_col) == "IPHONE_NM_2028_PRO"
    ]
    pro_nodes = {r[node_col] for r in pro_rows}

    assert base_nodes
    assert base_nodes <= pro_nodes

    money_fields = [
        "inventory_unit_value",
        "revenue_unit_value",
        "variable_cost_unit_value",
        "fixed_cost_weekly",
        "purchase_cost_per_lot",
        "value_added_cost_per_lot",
        "variable_cost_per_lot",
        "fixed_cost_per_week",
        "logistics_cost_per_lot",
        "inventory_handling_cost_per_lot",
        "tax_tariff_cost_per_lot",
        "target_profit_per_lot",
        "inventory_unit_value_per_lot",
        "ship_price_per_lot",
    ]

    total = 0.0
    for row in pro_rows:
        for field in money_fields:
            if field not in row:
                continue
            try:
                total += float((row.get(field) or 0) or 0)
            except ValueError:
                pass

    assert total > 0.0