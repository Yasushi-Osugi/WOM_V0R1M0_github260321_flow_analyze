# pysi/gui/psi_profit_animation_adapter.py

"""
psi_profit_animation_adapter.py

WOM 向け adapter
- cockpit_tk の現在選択状態から node/product を解決
- cash KPI は df_animation_kpi を最優先で使用
- なければ df_cash から local converter で再構成
- PSI は env.node_dict 優先、次に tree walk
- node.psi4supply / psi4demand から FrameData 用系列へ変換
- weekly_profit を window へ渡し、累計黒字化週を厳密算定可能にする

今回の版の主目的:
- Frame 1/1 ではなく Frame 1/N
- 週を1つずつ開示する
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, List, Sequence

import pandas as pd

from pysi.gui.psi_profit_animation_window import (
    BasePSIProfitDataProvider,
    FrameData,
)


# ============================================================
# Utility
# ============================================================

def _count_lots(x: Any) -> int:
    if x is None:
        return 0
    try:
        return len(x)
    except Exception:
        return 0


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _normalize_len(values: Sequence[Any], size: int, fill: float = 0.0) -> List[float]:
    out = [_safe_float(v, fill) for v in list(values[:size])]
    if len(out) < size:
        out.extend([fill] * (size - len(out)))
    return out


def _cumsum(values: Sequence[Any]) -> List[float]:
    total = 0.0
    out: List[float] = []
    for v in values:
        total += _safe_float(v)
        out.append(total)
    return out


def _calc_profit_ratio(revenue: Sequence[float], profit: Sequence[float]) -> List[float]:
    out: List[float] = []
    for r, p in zip(revenue, profit):
        r_val = _safe_float(r)
        p_val = _safe_float(p)
        # 売上が小さすぎる週は比率を出さない
        if abs(r_val) < 1e-12:
            out.append(0.0)
        else:
            out.append((p_val / r_val) * 100.0)
    return out


def _default_week_labels(size: int) -> List[str]:
    return [f"W{i + 1}" for i in range(size)]


def _iter_nodes(root: Any):
    stack = [root]
    while stack:
        n = stack.pop()
        if n is None:
            continue
        yield n
        for c in getattr(n, "children", []) or []:
            stack.append(c)


def _find_node_by_name(root: Any, name: str):
    for n in _iter_nodes(root):
        if getattr(n, "name", None) == name:
            return n
    return None


# ============================================================
# Local KPI converter (循環 import 回避)
# ============================================================

def _build_animation_kpi_df_from_cashflow_local(df_cash: pd.DataFrame) -> pd.DataFrame:
    if df_cash is None or df_cash.empty:
        return pd.DataFrame(
            columns=[
                "week_no",
                "node_name",
                "revenue",
                "cost",
                "profit",
                "inventory",
                "cash_in",
                "cash_out",
                "net_cash",
            ]
        )

    week_cols = [c for c in df_cash.columns if str(c).startswith("w")]
    if not week_cols:
        return pd.DataFrame(
            columns=[
                "week_no",
                "node_name",
                "revenue",
                "cost",
                "profit",
                "inventory",
                "cash_in",
                "cash_out",
                "net_cash",
            ]
        )

    keep_cols = ["node_name", "PSI_attribute"] + week_cols
    long_df = df_cash[keep_cols].melt(
        id_vars=["node_name", "PSI_attribute"],
        value_vars=week_cols,
        var_name="week_label",
        value_name="amount",
    ).copy()

    long_df["week_no"] = (
        long_df["week_label"].astype(str).str.extract(r"w(\d+)", expand=False).fillna("0").astype(int)
    )
    long_df["node_name"] = long_df["node_name"].astype(str)
    long_df["amount"] = pd.to_numeric(long_df["amount"], errors="coerce").fillna(0.0)

    def _norm_attr(x):
        s = str(x).strip().upper()
        if s == "0":
            return "S"
        if s == "1":
            return "CO"
        if s == "2":
            return "I"
        if s == "3":
            return "P"
        if s in ("IN", "OUT", "NET"):
            return s
        return s

    long_df["attr_norm"] = long_df["PSI_attribute"].map(_norm_attr)

    pivot = (
        long_df.pivot_table(
            index=["node_name", "week_no"],
            columns="attr_norm",
            values="amount",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
        .copy()
    )

    for c in ["S", "P", "I", "IN", "OUT", "NET"]:
        if c not in pivot.columns:
            pivot[c] = 0.0

    pivot["revenue"] = pivot["S"].where(pivot["S"] != 0.0, pivot["IN"])
    pivot["cost"] = pivot["P"].where(pivot["P"] != 0.0, pivot["OUT"])
    pivot["inventory"] = pivot["I"]
    pivot["cash_in"] = pivot["IN"]
    pivot["cash_out"] = pivot["OUT"]
    pivot["net_cash"] = pivot["NET"].where(
        pivot["NET"] != 0.0,
        pivot["cash_in"] - pivot["cash_out"],
    )
    pivot["profit"] = pivot["revenue"] - pivot["cost"]

    return (
        pivot[
            [
                "week_no",
                "node_name",
                "revenue",
                "cost",
                "profit",
                "inventory",
                "cash_in",
                "cash_out",
                "net_cash",
            ]
        ]
        .sort_values(["week_no", "node_name"])
        .reset_index(drop=True)
    )


# ============================================================
# Internal record
# ============================================================

@dataclass
class WeeklyPSIRecord:
    week_labels: List[str]

    supply_P: List[float]
    supply_I: List[float]
    demand_S: List[float]
    demand_CO: List[float]

    weekly_revenue: List[float]
    weekly_profit: List[float]

    title_suffix: str = ""
    total_revenue: Optional[float] = None
    total_profit: Optional[float] = None


def weekly_record_to_frame_data(
    record: WeeklyPSIRecord,
    visible_weeks: Optional[int] = None,
) -> FrameData:
    """
    0..visible_weeks-1 までだけを見せる。
    これにより Frame 1/N で週を1つずつ開示できる。
    """
    total_size = len(record.week_labels)
    if total_size <= 0:
        total_size = 1

    visible = total_size if visible_weeks is None else max(1, min(total_size, visible_weeks))

    week_labels = list(record.week_labels[:visible])

    supply_p = _normalize_len(record.supply_P[:visible], visible)
    supply_i = _normalize_len(record.supply_I[:visible], visible)
    demand_s = _normalize_len(record.demand_S[:visible], visible)
    demand_co = _normalize_len(record.demand_CO[:visible], visible)

    weekly_revenue = _normalize_len(record.weekly_revenue[:visible], visible)
    weekly_profit = _normalize_len(record.weekly_profit[:visible], visible)

    return FrameData(
        week_labels=week_labels,
        supply_accume=_cumsum(supply_p),
        supply_I=supply_i,
        supply_P=supply_p,
        demand_accume=_cumsum(demand_s),
        demand_CO=demand_co,
        demand_S=demand_s,
        profit_ratio=_calc_profit_ratio(weekly_revenue, weekly_profit),
        weekly_revenue=weekly_revenue,
        weekly_profit=weekly_profit,
        title_suffix=record.title_suffix,
        total_revenue=sum(weekly_revenue),
        total_profit=sum(weekly_profit),
    )


# ============================================================
# Provider
# ============================================================

class WOMPSIProfitDataProvider(BasePSIProfitDataProvider):
    """
    現段階では「選択中 node の全週データを 1週ずつ開示する」provider。
    """
    def __init__(self, frame_records: List[WeeklyPSIRecord]) -> None:
        self.frame_records = frame_records or [_build_empty_record("empty")]
        self.base_record = self.frame_records[0]

    def get_total_frames(self) -> int:
        return max(1, len(self.base_record.week_labels))

    def get_frame(self, frame_index: int) -> FrameData:
        visible = max(1, min(len(self.base_record.week_labels), frame_index + 1))
        return weekly_record_to_frame_data(self.base_record, visible_weeks=visible)


# ============================================================
# Resolve current cockpit context
# ============================================================

def _resolve_selected_node_name(cockpit: Any) -> Optional[str]:
    state = getattr(cockpit, "state", None)
    if state is not None:
        value = getattr(state, "selected_node", None)
        if value:
            return str(value)

    for attr_name in ("selected_node_id", "current_node_id", "node_id_selected"):
        value = getattr(cockpit, attr_name, None)
        if value:
            return str(value)

    for attr_name in ("selected_node_obj", "current_node"):
        obj = getattr(cockpit, attr_name, None)
        if obj is None:
            continue
        if isinstance(obj, dict):
            value = obj.get("node_id") or obj.get("name")
        else:
            value = getattr(obj, "node_id", None) or getattr(obj, "name", None)
        if value:
            return str(value)

    var_mom = getattr(cockpit, "var_mom", None)
    if var_mom is not None:
        try:
            value = var_mom.get().strip()
            if value:
                return value
        except Exception:
            pass

    return None


def _resolve_selected_product(cockpit: Any) -> Optional[str]:
    state = getattr(cockpit, "state", None)
    if state is not None:
        value = getattr(state, "selected_product", None)
        if value:
            return str(value)

    for attr_name in ("selected_product_id", "current_product_id", "product_id_selected"):
        value = getattr(cockpit, attr_name, None)
        if value:
            return str(value)

    var_product = getattr(cockpit, "var_product", None)
    if var_product is not None:
        try:
            value = var_product.get().strip()
            if value:
                return value
        except Exception:
            pass

    env = getattr(cockpit, "env", None)
    if env is not None:
        value = getattr(env, "product_selected", None)
        if value:
            return str(value)

    return None


def _resolve_root_outbound(env: Any, product: Optional[str]) -> Any:
    if env is None:
        return None

    byprod = getattr(env, "root_node_outbound_byprod", None)

    if isinstance(byprod, dict):
        if product and product in byprod:
            return byprod[product]
        if len(byprod) == 1:
            return next(iter(byprod.values()))

    if byprod is not None and not isinstance(byprod, dict):
        return byprod

    return getattr(env, "root_node_outbound", None) or getattr(env, "root", None)


def _resolve_node(env: Any, root_outbound: Any, node_name: Optional[str]) -> Any:
    if root_outbound is None and env is None:
        return None

    if not node_name:
        return root_outbound

    node_dict = getattr(env, "node_dict", None)
    if isinstance(node_dict, dict):
        node = node_dict.get(node_name)
        if node is not None:
            return node

    try:
        node = _find_node_by_name(root_outbound, node_name) if root_outbound is not None else None
        if node is not None:
            return node
    except Exception:
        pass

    return root_outbound


# ============================================================
# KPI extraction
# ============================================================

def _ensure_animation_kpi_df(cockpit: Any, env: Any, root_outbound: Any) -> pd.DataFrame:
    """
    Priority:
    1. cockpit.df_animation_kpi
    2. cockpit.df_cash -> local converter
    3. empty DataFrame fallback
    """
    df_animation_kpi = getattr(cockpit, "df_animation_kpi", None)
    if isinstance(df_animation_kpi, pd.DataFrame) and not df_animation_kpi.empty:
        return df_animation_kpi.copy()

    df_cash = getattr(cockpit, "df_cash", None)
    if isinstance(df_cash, pd.DataFrame) and not df_cash.empty:
        try:
            return _build_animation_kpi_df_from_cashflow_local(df_cash)
        except Exception:
            pass

    return pd.DataFrame(
        columns=[
            "week_no",
            "node_name",
            "revenue",
            "cost",
            "profit",
            "inventory",
            "cash_in",
            "cash_out",
            "net_cash",
        ]
    )


def _kpi_series_for_node(
    df_animation_kpi: pd.DataFrame,
    node_name: str,
    size: int,
) -> tuple[List[float], List[float]]:
    revenue = [0.0] * size
    profit = [0.0] * size

    if df_animation_kpi is None or df_animation_kpi.empty:
        return revenue, profit

    sub = df_animation_kpi[df_animation_kpi["node_name"].astype(str) == str(node_name)].copy()
    if sub.empty:
        return revenue, profit

    if "week_no" in sub.columns:
        sub["week_no"] = pd.to_numeric(sub["week_no"], errors="coerce").fillna(0).astype(int)
        sub = sub.sort_values("week_no")

    for _, row in sub.iterrows():
        w = int(_safe_float(row.get("week_no", 0), 0.0))
        idx = w - 1
        if 0 <= idx < size:
            revenue[idx] = _safe_float(row.get("revenue", 0.0))
            profit[idx] = _safe_float(row.get("profit", 0.0))

    return revenue, profit


# ============================================================
# PSI extraction
# ============================================================

def _series_from_node_psi(
    node: Any,
    size_hint: int = 0,
) -> tuple[List[float], List[float], List[float], List[float], int]:
    """
    cockpit_tk.plot_mom_psi_cap() の見方に寄せる。

    - S : psi_supply[w][0] を優先、無ければ psi_demand[w][0]
    - I : psi_supply[w][2]
    - P : psi_supply[w][3]
    - CO: psi_demand[w][1]
    """
    psi_supply = getattr(node, "psi4supply", None) or []
    psi_demand = getattr(node, "psi4demand", None) or []

    W = max(size_hint, len(psi_supply), len(psi_demand), 1)

    s_series: List[float] = []
    i_series: List[float] = []
    p_series: List[float] = []
    co_series: List[float] = []

    for w in range(W):
        try:
            if w < len(psi_supply):
                s_series.append(float(_count_lots(psi_supply[w][0])))
            elif w < len(psi_demand):
                s_series.append(float(_count_lots(psi_demand[w][0])))
            else:
                s_series.append(0.0)
        except Exception:
            s_series.append(0.0)

        try:
            i_series.append(float(_count_lots(psi_supply[w][2])) if w < len(psi_supply) else 0.0)
        except Exception:
            i_series.append(0.0)

        try:
            p_series.append(float(_count_lots(psi_supply[w][3])) if w < len(psi_supply) else 0.0)
        except Exception:
            p_series.append(0.0)

        try:
            co_series.append(float(_count_lots(psi_demand[w][1])) if w < len(psi_demand) else 0.0)
        except Exception:
            co_series.append(0.0)

    return p_series, i_series, s_series, co_series, W


# ============================================================
# Record builder
# ============================================================

def _build_empty_record(title_suffix: str = "empty", weeks: int = 20) -> WeeklyPSIRecord:
    week_labels = _default_week_labels(weeks)
    zeros = [0.0] * weeks
    return WeeklyPSIRecord(
        week_labels=week_labels,
        supply_P=zeros[:],
        supply_I=zeros[:],
        demand_S=zeros[:],
        demand_CO=zeros[:],
        weekly_revenue=zeros[:],
        weekly_profit=zeros[:],
        title_suffix=title_suffix,
        total_revenue=0.0,
        total_profit=0.0,
    )


def _build_record_from_context(
    *,
    node: Any,
    node_name: str,
    product_id: Optional[str],
    df_animation_kpi: pd.DataFrame,
) -> WeeklyPSIRecord:
    supply_p, supply_i, demand_s, demand_co, W = _series_from_node_psi(node)
    week_labels = _default_week_labels(W)

    weekly_revenue, weekly_profit = _kpi_series_for_node(
        df_animation_kpi,
        node_name=node_name,
        size=W,
    )

    title_bits = []
    if product_id:
        title_bits.append(str(product_id))
    if node_name:
        title_bits.append(str(node_name))
    title_suffix = " / ".join(title_bits) if title_bits else "PSI"

    return WeeklyPSIRecord(
        week_labels=week_labels,
        supply_P=supply_p,
        supply_I=supply_i,
        demand_S=demand_s,
        demand_CO=demand_co,
        weekly_revenue=weekly_revenue,
        weekly_profit=weekly_profit,
        title_suffix=title_suffix,
        total_revenue=sum(weekly_revenue),
        total_profit=sum(weekly_profit),
    )


# ============================================================
# Public builder
# ============================================================

def build_provider_from_cockpit_context(
    cockpit: Any,
    node_id: Optional[str] = None,
    product_id: Optional[str] = None,
) -> WOMPSIProfitDataProvider:
    """
    cockpit_tk から呼ぶ公開入口。
    成功条件:
    - 選択中 node の全週 PSI + weekly profit を安定表示
    - Frame 1/N で週を1つずつ開示
    """
    env = getattr(cockpit, "env", None)

    resolved_node_name = node_id or _resolve_selected_node_name(cockpit)
    resolved_product_id = product_id or _resolve_selected_product(cockpit)

    root_outbound = _resolve_root_outbound(env, resolved_product_id)
    df_animation_kpi = _ensure_animation_kpi_df(cockpit, env, root_outbound)

    node = _resolve_node(env, root_outbound, resolved_node_name)

    if node is None:
        return WOMPSIProfitDataProvider(
            [_build_empty_record(title_suffix=resolved_node_name or "empty")]
        )

    actual_node_name = getattr(node, "name", None) or resolved_node_name or "node"

    record = _build_record_from_context(
        node=node,
        node_name=str(actual_node_name),
        product_id=resolved_product_id,
        df_animation_kpi=df_animation_kpi,
    )

    return WOMPSIProfitDataProvider([record])