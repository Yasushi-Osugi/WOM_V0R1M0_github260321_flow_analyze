from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from pysi.adapters.capacity_input_granularity import (
    MonthlyCapacityInputRow,
    monthly_capacity_to_weekly_rows,
    weekly_capacity_rows_to_weekly_capability,
)
from pysi.core.hooks.core import action

logger = logging.getLogger(__name__)

DEFAULT_FILENAME = "sku_P_month_data.csv"
REQUIRED_COLUMNS = {
    "product_name",
    "node_name",
    "year",
    "m1",
    "m2",
    "m3",
    "m4",
    "m5",
    "m6",
    "m7",
    "m8",
    "m9",
    "m10",
    "m11",
    "m12",
}


@action("pipeline:before_planning", priority=20)
def capacity_provider_monthly_csv(**ctx):
    """Build env.weekly_capability from monthly capacity CSV."""
    env = ctx.get("env")
    if env is None:
        raise RuntimeError("capacity_provider_monthly_csv: env is required in ctx")

    data_dir = Path(ctx.get("data_dir") or ctx.get("csv") or ctx.get("csv_dir") or "data")
    filename = ctx.get("capacity_monthly_csv") or DEFAULT_FILENAME
    csv_path = data_dir / filename

    if not csv_path.exists():
        logger.warning("[CapacityProvider] monthly capacity csv not found: %s (skip)", csv_path)
        return

    # keep compatibility with existing env-driven weeks_count convention
    weeks_count = int(
        ctx.get("weeks_count")
        or ctx.get("plan_weeks")
        or getattr(env, "weeks_count", 0)
        or 53
    )
    scenario_id = str(ctx.get("scenario_id", "BASE"))
    calendar_mode = ctx.get("capacity_calendar_mode") or ctx.get("calendar_mode") or "four_week_month"

    df = pd.read_csv(csv_path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"capacity_provider_monthly_csv: missing columns in {csv_path}: {sorted(missing)}")

    df["product_name"] = df["product_name"].astype(str)
    df["node_name"] = df["node_name"].astype(str)
    df["year"] = df["year"].astype(int)

    month_cols = [f"m{i}" for i in range(1, 13)]
    for col in month_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    monthly_rows: list[MonthlyCapacityInputRow] = []
    for _, row in df.iterrows():
        for month_no in range(1, 13):
            qty = float(row[f"m{month_no}"])
            if qty <= 0:
                continue
            monthly_rows.append(
                MonthlyCapacityInputRow(
                    scenario_id=scenario_id,
                    product_id=str(row["product_name"]),
                    capacity_owner_type="node",
                    capacity_owner_id=str(row["node_name"]),
                    month=f"{int(row['year'])}-M{month_no:02d}",
                    capacity_type="P",
                    capacity_qty=qty,
                    cap_mode="hard",
                    unit="LOT",
                    source_id=DEFAULT_FILENAME,
                    comment="monthly MOM production capacity",
                )
            )

    if not monthly_rows:
        logger.info("[CapacityProvider] no capacity rows >0 in %s (skip)", csv_path)
        env.weekly_capability = {}
        env.weekly_capability_df = pd.DataFrame(columns=["product", "node", "week", "cap_lot"])
        return

    weekly_rows = monthly_capacity_to_weekly_rows(
        monthly_rows,
        calendar_mode=calendar_mode,
        distribution_rule="even",
    )
    env.weekly_capability = weekly_capacity_rows_to_weekly_capability(
        weekly_rows,
        weeks_count=weeks_count,
        normalize_owner_name=True,
        capacity_type_filter="P",
    )

    env.weekly_capability_df = pd.DataFrame(
        [
            {
                "product": r.product_id,
                "node": r.capacity_owner_id,
                "week": r.week,
                "cap_lot": int(r.capacity_qty),
                "source_granularity": r.source_granularity,
                "capacity_type": r.capacity_type,
                "source_id": r.source_id,
            }
            for r in weekly_rows
            if r.capacity_type == "P"
        ]
    )

    logger.info(
        "[CapacityProvider] weekly capability ready: products=%d src=%s",
        len(env.weekly_capability),
        csv_path.name,
    )
