#pysi/plugins/demand_provider_monthly_csv/plugin.py

from __future__ import annotations

import os
import logging
import pandas as pd

from pysi.core.hooks.core import action
from pysi.plan.demand_generate import (
    _normalize_monthly_demand_df_sku,
    convert_monthly_to_weekly_sku,
)
from pysi.bridge.future_demand import FutureDemandParams
from pysi.bridge.future_demand_adapter import adjust_monthly_demand_for_consumer
from pysi.bridge.consumer_state_repository import ConsumerStateRepository

logger = logging.getLogger(__name__)


def _traverse(root):
    st = [root]
    while st:
        n = st.pop()
        yield n
        st.extend(getattr(n, "children", []) or [])


def _make_lot_size_lookup(env):
    """
    lot_size_lookup(product_name, node_name) -> int
    plan_env_main.py と同じ思想：prod_tree_dict_OT から leaf(node_name) を見つけて lot_size を返す
    """
    def _lot_size_lookup(prod_name: str, node_name: str) -> int:
        root = getattr(env, "prod_tree_dict_OT", {}).get(prod_name)
        if root is None:
            return 1
        fn = getattr(root, "find_node", None)
        if callable(fn):
            nd = fn(lambda n: getattr(n, "name", None) == node_name)
            return int(getattr(nd, "lot_size", 1) or 1) if nd else 1
        for n in _traverse(root):
            if getattr(n, "name", None) == node_name:
                return int(getattr(n, "lot_size", 1) or 1)
        return 1

    return _lot_size_lookup



def _is_consumer_node(node_char_by_node_id, node_name: str) -> bool:
    node_char = (node_char_by_node_id or {}).get(str(node_name), {})
    return str(node_char.get("node_role", "")).lower() == "consumer"


def _get_state_dict_safe(consumer_repo, node_name: str, product_name: str) -> dict:
    try:
        return consumer_repo.get_state_dict(node_name, product_name)
    except Exception:
        return {
            "brand_loyalty": 50.0,
            "repeat_intent": 50.0,
            "switch_cost_perception": 50.0,
            "price_sensitivity": 50.0,
            "habit_strength": 0.0,
            "well_being_degree": 50.0,
        }


def _apply_consumer_feedback_to_monthly_demand(df_month: pd.DataFrame, env) -> pd.DataFrame:
    """
    正規化済み monthly demand(df_month) に対して、consumer node の demand だけを
    Future Demand multiplier で補正する。

    想定入力:
      product_name, node_name, year, m1..m12
    """
    if df_month is None or df_month.empty:
        return df_month

    node_char_by_node_id = getattr(env, "node_char_by_node_id", {}) or {}
    consumer_repo = getattr(env, "consumer_state_repo", None)
    if consumer_repo is None:
        consumer_repo = ConsumerStateRepository(debug=False)
        env.consumer_state_repo = consumer_repo

    fd_params = FutureDemandParams()
    month_cols = [c for c in df_month.columns if str(c).startswith("m")]

    adjusted_rows = []
    debug_samples = []

    for _, row in df_month.iterrows():
        row_dict = row.to_dict()
        node_name = str(row_dict.get("node_name", "")).strip()
        product_name = str(row_dict.get("product_name", "")).strip()

        for mcol in month_cols:
            row_dict[f"{mcol}_baseline"] = float(row_dict.get(mcol, 0.0) or 0.0)

        if _is_consumer_node(node_char_by_node_id, node_name):
            state_dict = _get_state_dict_safe(consumer_repo, node_name, product_name)

            baseline_total = 0.0
            adjusted_total = 0.0
            last_multiplier = 1.0

            for mcol in month_cols:
                baseline = float(row_dict.get(mcol, 0.0) or 0.0)

                result = adjust_monthly_demand_for_consumer(
                    baseline_monthly_demand=baseline,
                    consumer_node_id=node_name,
                    product_id=product_name,
                    consumer_state_dict=state_dict,
                    params=fd_params,
                )

                row_dict[mcol] = result.adjusted_monthly_demand
                baseline_total += baseline
                adjusted_total += result.adjusted_monthly_demand
                last_multiplier = result.multiplier

            row_dict["future_demand_multiplier"] = last_multiplier
            row_dict["baseline_monthly_total"] = baseline_total
            row_dict["adjusted_monthly_total"] = adjusted_total
            row_dict["demand_feedback_applied"] = 1

            if len(debug_samples) < 10:
                debug_samples.append({
                    "node_name": node_name,
                    "product_name": product_name,
                    "multiplier": last_multiplier,
                    "baseline_monthly_total": baseline_total,
                    "adjusted_monthly_total": adjusted_total,
                    "state_dict": state_dict,
                })
        else:
            row_dict["future_demand_multiplier"] = 1.0
            row_dict["baseline_monthly_total"] = sum(float(row_dict.get(c, 0.0) or 0.0) for c in month_cols)
            row_dict["adjusted_monthly_total"] = row_dict["baseline_monthly_total"]
            row_dict["demand_feedback_applied"] = 0

        adjusted_rows.append(row_dict)

    df_adjusted = pd.DataFrame(adjusted_rows)

    logger.info("[DemandProvider] consumer feedback monthly adjustment applied: rows=%d", len(df_adjusted))
    logger.info("[DemandProvider] consumer feedback samples: %s", debug_samples[:5])

    env.monthly_demand_baseline_df = df_month.copy()
    env.monthly_demand_adjusted_df = df_adjusted.copy()

    return df_adjusted


@action("pipeline:before_planning", priority=10)
def demand_provider_monthly_csv_to_weekly(env=None, root=None, **kwargs):
    """
    正本仕様：
      入力: sku_S_month_data.csv (優先) / S_month_data.csv
      出力: env.weekly_demand (dict[product_name]=df_weekly_sub)
            env.weekly_demand_df (df_weekly all)
            env.plan_range / env.plan_year_st
    週次DFの列は convert_monthly_to_weekly_sku() の正本仕様：
      product_name, node_name, iso_year, iso_week, value, lot_size, S_lot, lot_id_list ...
    """
    if env is None:
        logger.warning("[DemandProvider] env is None -> skip")
        return

    directory = getattr(env, "directory", None) or getattr(env, "load_directory", None)
    if not directory:
        raise RuntimeError("[DemandProvider] env.directory (or load_directory) is not set")

    new_csv = os.path.join(directory, "sku_S_month_data.csv")
    old_csv = os.path.join(directory, "S_month_data.csv")
    month_csv = new_csv if os.path.exists(new_csv) else old_csv

    if not os.path.exists(month_csv):
        logger.info("[DemandProvider] monthly csv not found: %s / %s", new_csv, old_csv)
        env.weekly_demand = {}
        env.weekly_demand_df = pd.DataFrame()
        return

    # 月次読込
    df_month_raw = pd.read_csv(month_csv, encoding="utf-8-sig")

    # sampleを見た限り year が float の場合があるので、ここで確実にint化
    if "year" in df_month_raw.columns:
        df_month_raw["year"] = pd.to_numeric(df_month_raw["year"], errors="coerce").fillna(0).astype(int)

    # 正規化（列名ゆれ吸収）
    df_month = _normalize_monthly_demand_df_sku(df_month_raw)

    # consumer feedback を monthly demand に反映
    # 最初は feature flag 付きにしておくと安全
    if getattr(env, "enable_consumer_demand_feedback", True):
        df_month = _apply_consumer_feedback_to_monthly_demand(df_month, env)

    lot_size_lookup = _make_lot_size_lookup(env)

    # ★ 正本：df_weekly, plan_range, plan_year_st
    df_weekly, plan_range, plan_year_st = convert_monthly_to_weekly_sku(df_month, lot_size_lookup)

    env.plan_range = int(plan_range)
    env.plan_year_st = int(plan_year_st)

    # dict保持（あなたの方針）
    weekly_dict = {}
    if not df_weekly.empty:
        for prod, g in df_weekly.groupby("product_name"):
            weekly_dict[str(prod)] = g.reset_index(drop=True)

    env.weekly_demand = weekly_dict
    env.weekly_demand_df = df_weekly

    logger.info("[DemandProvider] weekly demand ready: products=%d rows=%d src=%s",
                len(weekly_dict), len(df_weekly), os.path.basename(month_csv))

    # init は「需要生成を剥がした版」にしておく前提
    if hasattr(env, "init_psi_spaces_and_demand") and callable(env.init_psi_spaces_and_demand):
        env.init_psi_spaces_and_demand()

