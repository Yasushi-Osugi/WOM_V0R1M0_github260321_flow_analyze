from pathlib import Path

import pandas as pd

from pysi.io.psi_state_io import export_psi_state
from pysi.io.psi_state_loader import load_psi_state
from pysi.network.node_base import Node


def test_psi_state_bucket_order_roundtrip(tmp_path: Path):
    weeks = 1
    product_name = "PRODUCT_X"
    node_name = "NODE_A"

    root = Node(node_name)
    root.psi4demand = [[[], [], [], []] for _ in range(weeks)]
    root.psi4supply = [[[], [], [], []] for _ in range(weeks)]

    root.psi4demand[0][0] = ["LOT_S_001"]
    root.psi4demand[0][1] = ["LOT_CO_001"]
    root.psi4demand[0][2] = ["LOT_I_001"]
    root.psi4demand[0][3] = ["LOT_P_001"]

    state_hash = export_psi_state(
        save_dir=str(tmp_path),
        physical_root_out=root,
        physical_root_in=None,
        prod_roots_out={product_name: root},
        prod_roots_in={},
        weeks=weeks,
        params={"calendar": {"weeks": weeks}},
        meta={"scenario": "bucket-order-test"},
    )

    psi_dir = tmp_path / "psi_state"
    assert (psi_dir / "state_hash.txt").is_file()
    assert (psi_dir / "psi_events.parquet").is_file()
    assert isinstance(state_hash, str)
    assert state_hash.startswith("sha256:")

    df = pd.read_parquet(psi_dir / "psi_events.parquet")
    week0 = df[df["iso_index"] == 0]
    expected = {
        "LOT_S_001": "S",
        "LOT_CO_001": "CO",
        "LOT_I_001": "I",
        "LOT_P_001": "P",
    }
    got = dict(zip(week0["lot_id"], week0["bucket"]))
    assert got == expected

    loaded = load_psi_state(str(tmp_path), attach_psi=True)
    restored = loaded.prod_tree_dict_OT[product_name]

    assert restored.psi4demand[0][0] == ["LOT_S_001"]
    assert restored.psi4demand[0][1] == ["LOT_CO_001"]
    assert restored.psi4demand[0][2] == ["LOT_I_001"]
    assert restored.psi4demand[0][3] == ["LOT_P_001"]

    for idx in range(4):
        bucket = restored.psi4demand[0][idx]
        assert isinstance(bucket, list)
        assert all(isinstance(lot_id, str) for lot_id in bucket)
