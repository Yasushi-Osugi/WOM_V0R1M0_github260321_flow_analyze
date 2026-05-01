from pathlib import Path

from pysi.modeling.mosd_loader import load_mosd
from pysi.modeling.wom_master_adapter import generate_wom_masters


def test_sample_mosd_loads():
    mosd = load_mosd("samples/mosd/home_appliance_sample_v0_1.json")
    assert mosd["model_id"] == "home_appliance_sample_001"


def test_generation_outputs(tmp_path: Path):
    out = tmp_path / "generated/home_appliance_sample_001"
    summary = generate_wom_masters(
        "samples/mosd/home_appliance_sample_v0_1.json", str(out), overwrite=True
    )
    assert not summary["errors"]

    required = [
        "data/node_geo.csv",
        "data/product_tree_inbound.csv",
        "data/product_tree_outbound.csv",
        "data/sku_P_month_data.csv",
        "data/sku_S_month_data.csv",
        "pysi/master_data/node_master.csv",
        "adapter_report.md",
        "validation_report.md",
    ]
    for rel in required:
        assert (out / rel).exists()

    node_master = (out / "pysi/master_data/node_master.csv").read_text(encoding="utf-8")
    assert node_master.count("supply_point") == 1

    p_month = (out / "data/sku_P_month_data.csv").read_text(encoding="utf-8")
    s_month = (out / "data/sku_S_month_data.csv").read_text(encoding="utf-8")
    assert "m12" in p_month
    assert "m12" in s_month
