import csv
from pathlib import Path

from pysi.modeling.mosd_loader import load_mosd
from pysi.modeling.wom_master_adapter import generate_wom_masters
from pysi.modeling.wom_master_validator import validate_generated_masters


def test_sample_mosd_loads():
    mosd = load_mosd("samples/mosd/home_appliance_sample_v0_1.json")
    assert mosd["model_id"] == "home_appliance_sample_001"


def test_generation_outputs(tmp_path: Path):
    out = tmp_path / "generated/home_appliance_sample_001"
    summary = generate_wom_masters("samples/mosd/home_appliance_sample_v0_1.json", str(out), overwrite=True)
    assert not summary["errors"]
    for rel in ["data/node_geo.csv", "data/product_tree_inbound.csv", "data/product_tree_outbound.csv", "data/sku_P_month_data.csv", "data/sku_S_month_data.csv", "pysi/master_data/node_master.csv", "adapter_report.md", "validation_report.md"]:
        assert (out / rel).exists()


def test_generation_include_money(tmp_path: Path):
    out = tmp_path / "generated/home_appliance_sample_001"
    summary = generate_wom_masters("samples/mosd/home_appliance_sample_v0_1.json", str(out), overwrite=True, include_money=True)
    assert not summary["errors"]
    for rel in [
        "pysi/master_data/node_character_money_master.csv",
        "pysi/master_data/node_product_money_master.csv",
        "data/cost_masters/market_master.csv",
        "data/cost_masters/cs_node_to_market_map.csv",
        "data/cost_masters/product_cost_master.csv",
        "data/cost_masters/node_cost_master.csv",
        "data/cost_masters/lane_cost_master.csv",
        "data/cost_masters/sales_price_master.csv",
        "data/cost_masters/fx_rate_master.csv",
        "source_assumption_register.csv",
    ]:
        assert (out / rel).exists()
    with (out / "pysi/master_data/node_product_money_master.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    cs = next(r for r in rows if r["node_name"] == "CS_US_ECOM")
    assert float(cs["revenue_unit_value"]) > 0
    with (out / "data/cost_masters/market_master.csv").open() as fh:
        mk = list(csv.DictReader(fh))
    assert any(r["market_id"] == "MKT_US_ECOM" for r in mk)
    v = validate_generated_masters(str(out))
    assert not v["errors"]
