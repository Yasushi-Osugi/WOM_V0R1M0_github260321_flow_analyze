from pathlib import Path
from types import SimpleNamespace

from pysi.plugins.capacity_provider_monthly_csv.plugin import capacity_provider_monthly_csv


REQUIRED_HEADER = "product_name,node_name,year,m1,m2,m3,m4,m5,m6,m7,m8,m9,m10,m11,m12\n"


def _write_csv(path: Path, body_line: str) -> None:
    path.write_text(REQUIRED_HEADER + body_line, encoding="utf-8")


def test_missing_csv_does_not_crash(tmp_path):
    env = SimpleNamespace(weeks_count=53)
    capacity_provider_monthly_csv(env=env, data_dir=str(tmp_path))


def test_default_four_week_month_and_dad_to_mom(tmp_path):
    _write_csv(
        tmp_path / "sku_P_month_data.csv",
        "PRODUCT_X,DAD_CHINA,2026,400,0,0,0,0,0,0,0,0,0,0,0\n",
    )
    env = SimpleNamespace(weeks_count=53)

    capacity_provider_monthly_csv(env=env, data_dir=str(tmp_path))

    arr = env.weekly_capability["PRODUCT_X"]["MOM_CHINA"]
    assert arr[0] == 100
    assert arr[1] == 100
    assert arr[2] == 100
    assert arr[3] == 100


def test_optional_445_mode_m3_500_spreads_w09_to_w13(tmp_path):
    _write_csv(
        tmp_path / "sku_P_month_data.csv",
        "PRODUCT_X,DAD_CHINA,2026,0,0,500,0,0,0,0,0,0,0,0,0\n",
    )
    env = SimpleNamespace(weeks_count=53)

    capacity_provider_monthly_csv(
        env=env,
        data_dir=str(tmp_path),
        capacity_calendar_mode="445",
    )

    arr = env.weekly_capability["PRODUCT_X"]["MOM_CHINA"]
    assert arr[8:13] == [100, 100, 100, 100, 100]


def test_weekly_capability_df_exists_and_has_compatible_columns(tmp_path):
    _write_csv(
        tmp_path / "sku_P_month_data.csv",
        "PRODUCT_X,DAD_CHINA,2026,400,0,0,0,0,0,0,0,0,0,0,0\n",
    )
    env = SimpleNamespace(weeks_count=53)

    capacity_provider_monthly_csv(env=env, data_dir=str(tmp_path))

    assert hasattr(env, "weekly_capability_df")
    cols = set(env.weekly_capability_df.columns)
    assert {"product", "node", "week", "cap_lot"}.issubset(cols)
