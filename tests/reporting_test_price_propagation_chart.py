import pytest

pytest.importorskip("matplotlib")

import csv

from pysi.reporting.price_propagation_chart import generate_price_waterfall_stacked_bar


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
    assert (tmp_path / "out" / "A_price_waterfall_stacked_bar.png").stat().st_size > 0


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
    assert not (tmp_path / "out" / "PRODUCT_B_price_waterfall_stacked_bar.png").exists()


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
    assert (tmp_path / "out" / "A_price_waterfall_stacked_bar.png").stat().st_size > 0


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
    assert not (tmp_path / "out" / "A_outbound_price_waterfall_stacked_bar.png").exists()
