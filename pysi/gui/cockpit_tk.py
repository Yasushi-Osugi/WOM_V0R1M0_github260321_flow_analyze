# pysi/gui/cockpit_tk.py

# 目的：
# Product選択
# MOM選択（node_geo.csv の MOM* から）
# KPI（Profit / Service / CCC(暫定) / Util / Inventory / NetCash）
# タブ切替：MOM PSI×Cap / Service / Cashflow（全体/選択MOM）

from __future__ import annotations

import os
import math
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from dataclasses import dataclass

import threading

import numpy as np

# for events dump
from pysi.bridge.dump_rows import build_dump_rows_from_product_plan_tree

# for getting money evaluation results 
try:
    from pysi.evaluate.money_evaluator import evaluate_money_by_node
except Exception:
    evaluate_money_by_node = None


# management cockpit
try:
    from wom_cockpit.services.delta_detector import compare_snapshots
    from wom_cockpit.services.fact_extractor import extract_management_facts
    from wom_cockpit.services.issue_engine import generate_issues
    from wom_cockpit.domain.issue import Issue, RecommendedAction
    from wom_cockpit.ui.cockpit_view_model import build_cockpit_view_model, RiskViewModel
    from wom_cockpit.ui.tk.cockpit_panel_adapter import CockpitPanelAdapter
    _WOM_MANAGEMENT_COCKPIT_AVAILABLE = True
except Exception as e:
    print("[management_cockpit] import skipped:", e)
    compare_snapshots = None
    extract_management_facts = None
    generate_issues = None
    Issue = None
    RecommendedAction = None
    build_cockpit_view_model = None
    RiskViewModel = None
    CockpitPanelAdapter = None
    _WOM_MANAGEMENT_COCKPIT_AVAILABLE = False

try:
    from pysi.reporting.management_issue_analyzer import analyze_management_delta
except Exception as e:
    print("[management_issue_analyzer] import skipped:", e)
    analyze_management_delta = None

# optional snapshot builder for management cockpit
try:
    from pysi.bridge.state_snapshot import SnapshotBuildContext, build_snapshot_from_v0r8
except Exception:
    SnapshotBuildContext = None
    build_snapshot_from_v0r8 = None

# consumer node CSV input
from pysi.bridge.event_rules import initialize_consumer_experience_inputs

# ISSUE MANAGEMENT
try:
    from wom_cockpit.adapters.bridge_snapshot_adapter import (
        adapt_planning_snapshot_to_state_snapshot,
    )
except Exception:
    adapt_planning_snapshot_to_state_snapshot = None


# world map backend switch
USE_TKMAP = True

if USE_TKMAP:
    from pysi.gui.world_map_view_tkmap import show_world_map_tkmap as _show_world_map
else:
    from pysi.gui.world_map_view import show_world_map as _show_world_map


# business_animation
try:
    from pysi.gui.business_animation.business_animation_panel import BusinessAnimationPanel
    from pysi.gui.business_animation.context_models import BusinessAnimationContext
except Exception:
    BusinessAnimationPanel = None
    BusinessAnimationContext = None



# cockpit_tk.py の上部に追加
try:
    from pysi.gui.world_map_view import show_world_map
except ImportError:
    # パスが通っていない場合のデバッグ用
    def show_world_map(*args, **kwargs):
        print("[Error] world_map_view.py could not be imported.")

# ----------------------------
# UI Selection State
# ----------------------------
@dataclass
class SelectionState:
    """Single source of truth for GUI selection.

    Key design: use node_name (Node.name) as the common key across
    - world map (geo dict)
    - supply chain network
    - PSI mini view
    """
    selected_node: str | None = None
    selected_product: str | None = None
    selected_week: int | None = None


# ---- Step Workbench: data / helpers ---------------------------------

@dataclass
class StepContext:
    step_type: str                  # "demand" / "supply"
    direction: str                  # "outbound" / "inbound"
    execution_scope: str = "one_step"
    step_count: int = 1
    decoupling_node: str | None = None
    bottleneck_node: str | None = None
    capacity_ratio: float | None = None
    push_pull_mode: str | None = None
    priority_rule: str | None = None


def _normalize_step_type(value: str) -> str:
    v = (value or "").strip().lower()
    if v in ("demand", "dm"):
        return "demand"
    if v in ("supply", "sp"):
        return "supply"
    raise ValueError(f"Unsupported step_type: {value}")


def _normalize_direction(value: str) -> str:
    v = (value or "").strip().lower()
    if v in ("outbound", "out"):
        return "outbound"
    if v in ("inbound", "in"):
        return "inbound"
    raise ValueError(f"Unsupported direction: {value}")


def _safe_capture_snapshot(env, ctx: StepContext):
    try:
        from pysi.bridge.state_snapshot import SnapshotBuildContext, build_snapshot_from_v0r8

        time_bucket = str(getattr(env, "current_time_bucket", "202601"))
        return build_snapshot_from_v0r8(
            env_or_root=env,
            time_bucket=time_bucket,
            ctx=SnapshotBuildContext(
                product_id=getattr(env, "product_selected", None)
            ),
        )
    except Exception as e:
        print(f"[step] snapshot capture skipped: {e}")
        return None


def _safe_extract_bridge(previous, current):
    if previous is None or current is None:
        return {
            "events": [],
            "kernel_flow_events": [],
            "sidecar_events": [],
        }

    try:
        from pysi.bridge.event_extractor import ExtractContext, extract_events
        from pysi.bridge.event_mapper import map_bridge_events_to_kernel_v1

        bridge_events = extract_events(
            previous_state=previous,
            current_state=current,
            ctx=ExtractContext(time_bucket=current.time_bucket, seq_start=1),
        )
        mapped = map_bridge_events_to_kernel_v1(bridge_events)

        return {
            "events": bridge_events,
            "kernel_flow_events": mapped.flow_events,
            "sidecar_events": mapped.sidecar_events,
        }
    except Exception as e:
        print(f"[step] bridge extraction skipped: {e}")
        return {
            "events": [],
            "kernel_flow_events": [],
            "sidecar_events": [],
        }


def _run_demand_outbound_step(env, ctx: StepContext, tracer=None):
    print("[step] running demand/outbound")
    if hasattr(env, "demand_planning4multi_product"):
        env.demand_planning4multi_product()
    if hasattr(env, "demand_leveling4multi_prod"):
        env.demand_leveling4multi_prod()


def _run_demand_inbound_step(env, ctx: StepContext, tracer=None):
    print("[step] running demand/inbound")
    if hasattr(env, "demand_planning4multi_product"):
        env.demand_planning4multi_product()
    if hasattr(env, "demand_leveling4multi_prod"):
        env.demand_leveling4multi_prod()


def _run_supply_outbound_step(env, ctx: StepContext, tracer=None):
    print("[step] running supply/outbound")
    print("[trace] tracer is None:", tracer is None)
    print(
        "[trace] outbound root candidate:",
        getattr(env, "root_node_outbound_byprod", None),
        getattr(env, "root_node_outbound", None),
        getattr(env, "root", None),
    )
    print(
        "[trace] decouple candidate:",
        getattr(env, "decouple_node_names", None),
        getattr(env, "decouple_nodes", None),
    )

    if ctx.decoupling_node is not None:
        setattr(env, "decoupling_node_selected", ctx.decoupling_node)
    if ctx.push_pull_mode is not None:
        setattr(env, "push_pull_mode", ctx.push_pull_mode)

    if tracer is None:
        if hasattr(env, "supply_planning4multi_product"):
            env.supply_planning4multi_product()
    else:
        try:
            from pysi.plan.engines import push_pull_all_psi2i_decouple4supply5
        except Exception:
            try:
                from pysi.core.engines import push_pull_all_psi2i_decouple4supply5
            except Exception as e:
                print(f"[trace] engines import failed: {e}")
                if hasattr(env, "supply_planning4multi_product"):
                    env.supply_planning4multi_product()
                return

        root = (
            getattr(env, "root_node_outbound_byprod", None)
            or getattr(env, "root_node_outbound", None)
            or getattr(env, "root", None)
        )
        decouple_nodes = (
            getattr(env, "decouple_node_names", None)
            or getattr(env, "decouple_nodes", None)
            or []
        )

        if root is not None:
            push_pull_all_psi2i_decouple4supply5(root, decouple_nodes, tracer=tracer)
        else:
            print("[trace] outbound trace skipped: root not found")
            if hasattr(env, "supply_planning4multi_product"):
                env.supply_planning4multi_product()



def _run_supply_inbound_step(env, ctx: StepContext, tracer=None):
    print("[step] running supply/inbound")

    if ctx.bottleneck_node is not None:
        setattr(env, "bottleneck_node_selected", ctx.bottleneck_node)
    if ctx.capacity_ratio is not None:
        setattr(env, "capacity_ratio", ctx.capacity_ratio)

    if hasattr(env, "supply_planning4multi_product"):
        env.supply_planning4multi_product()


def _dispatch_step(env, ctx: StepContext, tracer=None):
    if ctx.step_type == "demand" and ctx.direction == "outbound":
        return _run_demand_outbound_step(env, ctx, tracer=tracer)
    if ctx.step_type == "demand" and ctx.direction == "inbound":
        return _run_demand_inbound_step(env, ctx, tracer=tracer)
    if ctx.step_type == "supply" and ctx.direction == "outbound":
        return _run_supply_outbound_step(env, ctx, tracer=tracer)
    if ctx.step_type == "supply" and ctx.direction == "inbound":
        return _run_supply_inbound_step(env, ctx, tracer=tracer)

    raise ValueError(f"Unsupported step combination: {ctx}")



import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


from pysi.gui.network_viewer_patched import show_network_E2E_matplotlib

from pysi.gui.psi_profit_animation_window import open_psi_profit_animation_window
from pysi.gui.psi_profit_animation_adapter import build_provider_from_cockpit_context




# ----------------------------
# Helpers: tree traversal
# ----------------------------
def iter_nodes(root):
    stack = [root]
    while stack:
        n = stack.pop()
        if n is None:
            continue
        yield n
        for c in getattr(n, "children", []) or []:
            stack.append(c)

def find_node_by_name(root, name: str):
    for n in iter_nodes(root):
        if getattr(n, "name", None) == name:
            return n
    return None

def leaf_nodes(root):
    leaves = []
    for n in iter_nodes(root):
        ch = getattr(n, "children", []) or []
        if not ch:
            leaves.append(n)
    return leaves

def count_lots(x):
    # x is list of lot_id
    return len(x) if x else 0


def build_edges_from_root(root):
    edges = []
    try:
        for n in iter_nodes(root):
            for c in getattr(n, "children", []) or []:
                edges.append((getattr(n, "name", ""), getattr(c, "name", "")))
    except Exception:
        pass
    return edges


def make_E2E_positions(root_node_outbound, root_node_inbound,
                     dx=1.2, dy=0.9, office_margin=1.0):
    from collections import defaultdict, deque

    def bfs_layout(root):
        """children を辿って BFS。x=depth*dx, y=同深さで整列。"""
        if not root:
            return {}

        edges = []
        st, seen, nodes = [root], set(), set()
        while st:
            p = st.pop()
            if id(p) in seen:
                continue
            seen.add(id(p))
            pn = getattr(p, "name", "")
            if pn:
                nodes.add(pn)
            for c in getattr(p, "children", []) or []:
                cn = getattr(c, "name", "")
                if pn and cn:
                    edges.append((pn, cn))
                st.append(c)

        if not nodes:
            return {}

        indeg = defaultdict(int)
        for u, v in edges:
            indeg[v] += 1

        roots = [n for n in nodes if indeg[n] == 0]
        if not roots:
            roots = ["supply_point"] if "supply_point" in nodes else [next(iter(nodes))]

        depth = {}
        for r in roots:
            dq = deque([(r, 0)])
            while dq:
                n, d = dq.popleft()
                if d < depth.get(n, 10**9):
                    depth[n] = d
                    for (u, v) in edges:
                        if u == n:
                            dq.append((v, d + 1))

        by_d = defaultdict(list)
        for n, d in depth.items():
            by_d[d].append(n)

        pos = {}
        for d, arr in by_d.items():
            arr.sort()
            mid = (len(arr) - 1) / 2.0
            for i, n in enumerate(arr):
                pos[n] = (d * dx, -(i - mid) * dy)
        return pos

    pos_out = bfs_layout(root_node_outbound)
    if "supply_point" in pos_out:
        spx = pos_out["supply_point"][0]
        pos_out = {n: (x - spx, y) for n, (x, y) in pos_out.items()}

    pos_in = bfs_layout(root_node_inbound)
    if "supply_point" in pos_in:
        spx = pos_in["supply_point"][0]
        pos_in = {n: (x - spx, y) for n, (x, y) in pos_in.items()}
    pos_in = {n: (-x, y) for n, (x, y) in pos_in.items()}

    pos = dict(pos_in)
    pos.update(pos_out)
    pos["supply_point"] = (0.0, 0.0)

    print("pos_out => ", pos_out)
    print("pos_in => ", pos_in)
    print("pos_mmerged => ", pos)
    return pos


# ----------------------------
# Service KPI (JIT deviation)
# ----------------------------
def _percentile(sorted_vals, p: float) -> float:
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    k = int(round((n - 1) * p))
    k = max(0, min(n - 1, k))
    return float(sorted_vals[k])

def compute_service_jit_for_product(root_outbound, weeks_count: int | None = None):
    W = weeks_count or len(root_outbound.psi4demand)
    leaves = leaf_nodes(root_outbound)

    demand_week = {}
    ship_week = {}

    for lf in leaves:
        for w in range(min(W, len(lf.psi4demand))):
            for lot_id in (lf.psi4demand[w][0] or []):
                if lot_id not in demand_week:
                    demand_week[lot_id] = w

        for w in range(min(W, len(lf.psi4supply))):
            for lot_id in (lf.psi4supply[w][0] or []):
                if lot_id not in ship_week:
                    ship_week[lot_id] = w

    diffs_abs = []
    late = []
    early = []
    unfilled = 0
    filled = 0

    for lot_id, dw in demand_week.items():
        sw = ship_week.get(lot_id)
        if sw is None:
            unfilled += 1
            continue
        filled += 1
        d = sw - dw
        diffs_abs.append(abs(d))
        if d > 0:
            late.append(float(d))
        elif d < 0:
            early.append(float(abs(d)))

    diffs_abs.sort()

    jit_mad = (sum(diffs_abs) / len(diffs_abs)) if diffs_abs else 0.0
    jit_p95 = _percentile(diffs_abs, 0.95)
    avg_late = (sum(late) / len(late)) if late else 0.0
    avg_early = (sum(early) / len(early)) if early else 0.0

    return {
        "jit_mad_weeks": jit_mad,
        "jit_p95_weeks": jit_p95,
        "unfilled_lots": unfilled,
        "filled_lots": filled,
        "total_demand_lots": len(demand_week),
        "avg_late_weeks": avg_late,
        "avg_early_weeks": avg_early,
    }


# ----------------------------
# Inventory / Utilization
# ----------------------------
def compute_total_inventory_lots(root_outbound, weeks_count: int | None = None):
    # simplest: sum of I lots count across nodes for a representative week (last week) and/or average
    W = weeks_count or len(root_outbound.psi4supply)
    if W <= 0:
        return 0, 0.0

    inv_per_week = []
    for w in range(W):
        s = 0
        for n in iter_nodes(root_outbound):
            try:
                s += count_lots(n.psi4supply[w][2])
            except Exception:
                pass
        inv_per_week.append(s)

    return int(inv_per_week[-1]), float(sum(inv_per_week) / len(inv_per_week))

def compute_utilization_series(env, product: str, mom_name: str, root_outbound):
    # used_lots: MOM node P lots if available else root_outbound P lots
    # cap_lots: env.weekly_capability[product][mom_name][w]
    cap = (((getattr(env, "weekly_capability", {}) or {}).get(product, {}) or {}).get(mom_name, None))
    if cap is None:
        return None, None

    W = len(cap)
    mom = find_node_by_name(root_outbound, mom_name)  # outbound tree may contain MOM. If not, use root_outbound.
    node_for_used = mom if mom is not None else root_outbound

    used = []
    for w in range(W):
        # P slot: try attr=3 (Purchase/Production) in your convention,
        # but fallback if missing
        p_lots = None
        try:
            p_lots = node_for_used.psi4supply[w][3]
        except Exception:
            p_lots = None
        if p_lots is None:
            try:
                p_lots = node_for_used.psi4supply[w][0]  # fallback to S if P not available
            except Exception:
                p_lots = []
        used.append(count_lots(p_lots))

    util = []
    for u, c in zip(used, cap):
        if c and c > 0:
            util.append(u / c)
        else:
            util.append(0.0)
    return np.array(used, dtype=float), np.array(util, dtype=float)


# ----------------------------
# Cashflow: compute df (NO CSV required)
# ----------------------------
def shift_right(values, k: int):
    """Non-circular shift (delay)."""
    values = np.array(values, dtype=float)
    if k <= 0:
        return values
    out = np.zeros_like(values)
    if k < len(values):
        out[k:] = values[:-k]
    return out

def build_cashflow_df_outbound(root_outbound, output_period: int):
    """
    returns DataFrame like your CSV but in-memory.
    """
    data = []
    week_cols = [f"w{i+1}" for i in range(output_period)]

    def collect(node, level, position):
        ar_days = getattr(node, "AR_lead_time", 0) or 0
        ap_days = getattr(node, "AP_lead_time", 0) or 0
        ar_shift = int(ar_days // 7)
        ap_shift = int(ap_days // 7)

        weekly_in = None
        weekly_out = None

        for attr in range(4):  # 0:S, 1:CarryOver, 2:I, 3:P (your convention)
            if attr == 0:
                price = getattr(node, "cs_price_sales_shipped", 0) or 0
            elif attr in [1, 2]:
                price = getattr(node, "cs_purchase_total_cost", 0) or 0
            elif attr == 3:
                price = getattr(node, "cs_direct_materials_costs", 0) or 0
            else:
                price = 0

            base = [getattr(node, "name", ""), level, position, price, attr]
            vals = []
            for w in range(output_period):
                try:
                    vals.append(count_lots(node.psi4supply[w][attr]) * price)
                except Exception:
                    vals.append(0)
            data.append(base + vals)

            if attr == 0:
                weekly_in = shift_right(vals, ar_shift)
                data.append([getattr(node, "name", ""), level, position, price, "IN"] + list(vals))
            elif attr == 3:
                weekly_out = shift_right(vals, ap_shift)
                data.append([getattr(node, "name", ""), level, position, price, "OUT"] + list(vals))

        if weekly_in is None:
            weekly_in = np.zeros(output_period)
        if weekly_out is None:
            weekly_out = np.zeros(output_period)
        net = np.array(weekly_in) - np.array(weekly_out)
        data.append([getattr(node, "name", ""), level, position, 0, "NET"] + list(net))

        for i, child in enumerate(getattr(node, "children", []) or []):
            collect(child, level + 1, i + 1)

    collect(root_outbound, 0, 1)

    cols = ["node_name", "Level", "Position", "Price", "PSI_attribute"] + week_cols
    return pd.DataFrame(data, columns=cols)

def build_animation_kpi_df_from_cashflow(df_cash: pd.DataFrame) -> pd.DataFrame:
    """
    Convert build_cashflow_df_outbound() style wide cashflow DataFrame
    into long-form animation KPI DataFrame.

    Input:
        node_name, Level, Position, Price, PSI_attribute, w1, w2, ... wN

    Output:
        week_no, node_name, revenue, cost, profit, inventory, cash_in, cash_out, net_cash
    """
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



def cashflow_kpis_from_df(df, node_name: str | None = None):
    week_cols = [c for c in df.columns if c.startswith("w")]
    d = df
    if node_name is not None:
        d = d[d["node_name"] == node_name]

    dnet = d[d["PSI_attribute"] == "NET"]
    if dnet.empty:
        return {"net_cash_min": 0.0, "net_cash_sum": 0.0, "cum_net_cash_min": 0.0}

    net = dnet[week_cols].sum(axis=0).astype(float).values
    net_cash_min = float(net.min()) if len(net) else 0.0
    net_cash_sum = float(net.sum()) if len(net) else 0.0
    cum = net.cumsum() if len(net) else np.array([])
    cum_min = float(cum.min()) if len(cum) else 0.0
    return {"net_cash_min": net_cash_min, "net_cash_sum": net_cash_sum, "cum_net_cash_min": cum_min}


# ----------------------------
# Plotters (matplotlib embedding)
# ----------------------------
def clear_frame(frame):
    for w in frame.winfo_children():
        w.destroy()

#@STOP
#def plot_mom_psi_cap(frame, env, product: str, mom_name: str, root_outbound):
def plot_mom_psi_cap(
    frame,
    env,
    product: str,
    mom_name: str,
    root_outbound,
    *,
    step_type="Supply",
    direction="Outbound",
    debug=True,
):



    clear_frame(frame)

    # NOTE:
    # ここは「MOM固定」ではなく、cockpit の選択ノード（leaf/WS/PAD/MOM 何でも）を描けるようにする。
    node_name = mom_name  # 引数名は互換維持。実体は「描画したいノード名」

    # node の解決：env.node_dict があれば最優先（outbound/inbound両方を含められる）
    node = None
    node_dict = getattr(env, "node_dict", None)
    if isinstance(node_dict, dict) and node_name:
        node = node_dict.get(node_name)
    if node is None and node_name:
        node = find_node_by_name(root_outbound, node_name)
    if node is None:
        node = root_outbound

    # capability は「そのノードに定義されていれば重ねる」。無ければ PSI だけ描く。
    cap = (((getattr(env, "weekly_capability", {}) or {}).get(product, {}) or {}).get(node_name, None))

    # 描画期間W：capがあればcap優先、無ければpsi長
    psi_supply = getattr(node, "psi4supply", None) or []
    psi_demand = getattr(node, "psi4demand", None) or []
    W = 0
    if cap is not None:
        W = len(cap)
    W = max(W, len(psi_supply), len(psi_demand))
    if W <= 0:
        tk.Label(frame, text=f"No PSI data for {product}:{node_name}").pack()
        return

    # series: S lots, I lots, P lots (fallback)
    s_series = []
    i_series = []
    p_series = []
    for w in range(W):
        try:
            if w < len(psi_supply):
                s_series.append(count_lots(psi_supply[w][0]))
            else:
                s_series.append(count_lots(psi_demand[w][0]) if w < len(psi_demand) else 0)
        except Exception:
            s_series.append(0)
        try:
            i_series.append(count_lots(psi_supply[w][2]) if w < len(psi_supply) else 0)
        except Exception:
            i_series.append(0)
        try:
            p_series.append(count_lots(psi_supply[w][3]) if w < len(psi_supply) else 0)
        except Exception:
            p_series.append(0)

    fig, ax = plt.subplots(figsize=(8.6, 3.2), dpi=110)
    x = np.arange(1, W + 1)

    ax.plot(x, s_series, marker="o", linewidth=1, markersize=2, label="S (Ship/Sales lots)")
    ax.plot(x, p_series, marker="o", linewidth=1, markersize=2, label="P (Production lots)")
    ax.plot(x, i_series, marker="o", linewidth=1, markersize=2, label="I (Inventory lots)")

    #@STOP
    #if cap is not None:
    #    ax.plot(x, cap, marker=None, linewidth=2, label="Capability (lots/week)")

    if cap is not None:
        # cap length must match W; pad with NaN (line breaks) or trim.
        cap_list = list(cap)
        if len(cap_list) < W:
            cap_list = cap_list + [float("nan")] * (W - len(cap_list))
        elif len(cap_list) > W:
            cap_list = cap_list[:W]
        ax.plot(x, cap_list, marker=None, linewidth=2, label="Capability (lots/week)")



    title = f"{product} / {node_name} : PSI"
    if cap is not None:
        title += " vs Capability"
    ax.set_title(title)
    ax.set_xlabel("Week")
    ax.set_ylabel("Lots")
    ax.legend(loc="upper left", fontsize=9)

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)
    plt.close(fig)

def plot_service(frame, env, product: str, root_outbound):
    clear_frame(frame)
    k = compute_service_jit_for_product(root_outbound)

    txt = (
        f"Service (Leaf JIT)\n\n"
        f"JIT MAD (weeks)     : {k['jit_mad_weeks']:.2f}\n"
        f"JIT P95 (weeks)     : {k['jit_p95_weeks']:.2f}\n"
        f"Unfilled lots       : {k['unfilled_lots']}\n"
        f"Filled lots         : {k['filled_lots']}\n"
        f"Total demand lots   : {k['total_demand_lots']}\n"
        f"Avg Late (weeks)    : {k['avg_late_weeks']:.2f}\n"
        f"Avg Early (weeks)   : {k['avg_early_weeks']:.2f}\n"
    )
    lab = tk.Label(frame, text=txt, justify="left", font=("Segoe UI", 11))
    lab.pack(anchor="w", padx=10, pady=10)

def plot_cashflow(frame, df_cash, title: str, node_name: str | None = None):
    clear_frame(frame)

    week_cols = [c for c in df_cash.columns if c.startswith("w")]
    d = df_cash
    if node_name is not None:
        d = d[d["node_name"] == node_name]

    # sum across rows for each attribute
    def series(attr):
        dd = d[d["PSI_attribute"] == attr]
        if dd.empty:
            return np.zeros(len(week_cols))
        return dd[week_cols].sum(axis=0).astype(float).values

    cash_in = series("IN")
    cash_out = series("OUT")
    net = series("NET")

    W = len(week_cols)
    x = np.arange(1, W + 1)

    fig, ax1 = plt.subplots(figsize=(8.6, 3.2), dpi=110)
    bar_w = 0.35
    ax1.bar(x - bar_w / 2, cash_in, width=bar_w, alpha=0.7, label="Cash In")
    ax1.bar(x + bar_w / 2, cash_out, width=bar_w, alpha=0.7, label="Cash Out")
    ax2 = ax1.twinx()
    ax2.plot(x, net, marker="o", linewidth=1, markersize=2, label="Net Cash")

    ax1.set_title(title)
    ax1.set_xlabel("Week")
    ax1.set_ylabel("Cash In/Out")
    ax2.set_ylabel("Net Cash")

    ax1.legend(loc="upper left", fontsize=9)
    ax2.legend(loc="upper right", fontsize=9)

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)
    plt.close(fig)


# ----------------------------
# Cockpit UI
# ----------------------------
class WOMCockpit(tk.Tk):
    def __init__(self, env, rerun_fn=None):
        super().__init__()
        self.env = env
        self.rerun_fn = rerun_fn  # ★ injected from main4cockpit.py
        self.title("WOM Cockpit (Minimal)")
        self.geometry("1100x700")

        # resolve product list
        self.products = sorted(list((getattr(env, "prod_tree_dict_OT", {}) or {}).keys()))
        if not self.products and getattr(env, "product_selected", None):
            self.products = [env.product_selected]

        # semantic subsets / selector candidates
        self.moms_geo = self._load_moms_from_geo()
        self.moms = self._resolve_moms()   # inbound manufacturing subset
        self.node_names = self._resolve_selectable_node_names()  # GUI main selector candidates
        self.dads = self._resolve_dads()   # outbound distribution subset

        # state vars
        self.var_product = tk.StringVar(value=getattr(env, "product_selected", self.products[0] if self.products else ""))
        self.var_leaf_node = tk.StringVar(value="")
        self.var_node = tk.StringVar(value=self.node_names[0] if self.node_names else "")
        # temporary alias during migration
        self.var_mom = self.var_node

        # step workbench state
        self.var_step_type = tk.StringVar(value="Supply")
        self.var_direction = tk.StringVar(value="Outbound")

        # optional future controls
        self.var_decoupling_node = tk.StringVar(value="")
        self.var_bottleneck_node = tk.StringVar(value="")
        self.var_capacity_ratio = tk.StringVar(value="")
        self.var_push_pull_mode = tk.StringVar(value="COMBINED")
        self.var_priority_rule = tk.StringVar(value="Default")

        self.current_mode = "recompute"
        self.step_seq = 0
        self.last_step_context = None
        self.last_bridge_payload = {"events": [], "kernel_flow_events": [], "sidecar_events": []}
        self.last_dad_handoff_result = None

        # management cockpit state
        self.management_cockpit_win = None
        self.management_cockpit_panel = None
        self.management_cockpit_status_var = tk.StringVar(value="Management cockpit: idle")
        self._last_management_snapshot = None

        # trace on/off
        self.var_trace_enabled = tk.BooleanVar(value=False)
        self.trace_event_sink = []

        # trace viewer state
        self.trace_viewer_win = None
        self.trace_tree = None
        self.trace_row_event_map = {}
        self.trace_count_var = tk.StringVar(value="0 events")
        self.trace_filter_event_type = tk.StringVar(value="")
        self.trace_filter_node_id = tk.StringVar(value="")
        self.trace_filter_lot_id = tk.StringVar(value="")
        self.trace_filter_time_bucket = tk.StringVar(value="")


        # business animation
        self.business_animation_window = None
        self.business_animation_panel = None


        # animation viewer state
        self.anim_viewer_win = None
        self.anim_canvas = None
        self.anim_lot_id_var = tk.StringVar(value="")
        self.anim_status_var = tk.StringVar(value="No lot loaded")
        self.anim_frames = []
        self.anim_index = 0
        self.anim_playing = False
        self.anim_after_id = None
        self.anim_interval_ms = 700

        # PSI accumulated + profit ratio animation window state
        self.psi_profit_anim_win = None

        # selection state (node_name common key)
        self.state = SelectionState(
            selected_node=self.var_node.get() if self.var_node.get() else None,
            selected_product=self.var_product.get() if self.var_product.get() else None,
        )

        # top controls
        self._build_header()

        # L1: PSI mini (selected node)
        self.l1_frame = ttk.Labelframe(self, text="L1: Selected Node PSI (mini)")
        self.l1_frame.pack(fill="x", padx=10, pady=(0, 6))

        #@UPDATE
        self.l1_text = tk.Text(self.l1_frame, height=14, wrap="word")
        
        self.l1_text.pack(fill="x", padx=6, pady=6)

        # KPI panel
        self.kpi_frame = ttk.Frame(self)
        self.kpi_frame.pack(fill="x", padx=10, pady=8)
        self.kpi_labels = {}
        self._build_kpi_cards()

        # tabs
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_psi = ttk.Frame(self.nb)
        self.tab_service = ttk.Frame(self.nb)
        self.tab_cash = ttk.Frame(self.nb)

        self.nb.add(self.tab_psi, text="Node PSI × Capability")
        self.nb.add(self.tab_service, text="Service (Leaf JIT)")
        self.nb.add(self.tab_cash, text="Cashflow (Total / Selected Node)")

        # tab inner frames
        self.frame_psi_plot = ttk.Frame(self.tab_psi)
        self.frame_psi_plot.pack(fill="both", expand=True)

        self.frame_service = ttk.Frame(self.tab_service)
        self.frame_service.pack(fill="both", expand=True)

        self.frame_cash_controls = ttk.Frame(self.tab_cash)
        self.frame_cash_controls.pack(fill="x", padx=5, pady=5)

        self.frame_cash_total = ttk.Frame(self.tab_cash)
        self.frame_cash_total.pack(fill="both", expand=True)

        # cash controls (Total vs MOM)
        self.var_cash_mode = tk.StringVar(value="TOTAL")
        ttk.Radiobutton(self.frame_cash_controls, text="Total (Outbound sum)", variable=self.var_cash_mode, value="TOTAL", command=self.refresh).pack(side="left")
        ttk.Radiobutton(self.frame_cash_controls, text="Selected Node", variable=self.var_cash_mode, value="MOM", command=self.refresh).pack(side="left", padx=10)

        # cached cash df
        self.df_cash = None
        self.df_animation_kpi = None

        # initial draw
        self.refresh_leaf_node_dropdown()
        self.refresh()

        # condumer node CSV input
        csv_path = os.path.join(os.getcwd(), "data", "consumer_experience_input.csv")
        initialize_consumer_experience_inputs(csv_path)

        # decouple nodes list
        self.decouple_node_selected = [] 

        # seed initial management snapshot after first UI paint
        try:
            self.after(200, self._capture_initial_management_snapshot)
        except Exception:
            pass

        # CAPACITY
        self.last_capacity_result = None


    def _build_header(self):
        frm = ttk.Frame(self)
        frm.pack(fill="x", padx=10, pady=10)

        # --------------------------------------------------
        # Row 1: Action menu
        # --------------------------------------------------
        action_row = ttk.Frame(frm)
        action_row.pack(fill="x", pady=(0, 6))

        ttk.Button(action_row, text="Network", command=self.open_network).pack(side="left", padx=(0, 6))
        ttk.Button(action_row, text="World", command=self.open_world_map).pack(side="left", padx=(0, 6))
        ttk.Button(action_row, text="Run (recompute)", command=self.run_and_refresh).pack(side="left", padx=(0, 6))
        ttk.Button(action_row, text="Refresh", command=self.refresh).pack(side="left", padx=(0, 6))

        ttk.Checkbutton(action_row, text="Trace", variable=self.var_trace_enabled).pack(side="left", padx=(12, 6))
        ttk.Button(action_row, text="Trace Viewer", command=self.open_trace_viewer).pack(side="left", padx=(0, 6))
        ttk.Button(action_row, text="Price & Cost Structure", command=self.on_generate_price_cost_structure_chart).pack(side="left", padx=(0, 6))
        ttk.Button(action_row, text="Mgmt Cockpit", command=self.open_management_cockpit).pack(side="left", padx=(0, 6))
        ttk.Button(action_row, text="Business Animation", command=self.open_business_animation).pack(side="left", padx=(0, 6))
        ttk.Button(action_row, text="PSI累計+利益率", command=self.open_psi_profit_animation).pack(side="left", padx=(0, 6))
        ttk.Button(action_row, text="Animation Viewer", command=self.open_animation_viewer).pack(side="left", padx=(0, 6))

        ttk.Button(action_row, text="Run Full Plan", command=self.run_full_plan).pack(side="right", padx=(6, 0))
        ttk.Button(action_row, text="Run Step", command=self.run_step).pack(side="right")

        # --------------------------------------------------
        # Row 2: Basic selection
        # --------------------------------------------------
        select_row = ttk.Frame(frm)
        select_row.pack(fill="x")

        ttk.Label(select_row, text="Product:", width=10).pack(side="left")
        self.cb_product = ttk.Combobox(
            select_row,
            textvariable=self.var_product,
            values=self.products,
            width=35,
            state="readonly",
        )
        self.cb_product.pack(side="left", padx=5)
        self.cb_product.bind("<<ComboboxSelected>>", lambda e: self.on_change_product())

        ttk.Label(select_row, text="Leaf:", width=6).pack(side="left", padx=(20, 0))
        self.cb_leaf_node = ttk.Combobox(
            select_row,
            textvariable=self.var_leaf_node,
            values=[],
            width=24,
            state="readonly",
        )
        self.cb_leaf_node.pack(side="left", padx=5)

        ttk.Label(select_row, text="Node:", width=6).pack(side="left", padx=(20, 0))
        self.cb_node = ttk.Combobox(
            select_row,
            textvariable=self.var_node,
            values=self.node_names,
            width=28,
            state="readonly",
        )
        self.cb_node.pack(side="left", padx=5)
        self.cb_node.bind("<<ComboboxSelected>>", lambda e: self.on_change_node())

        ttk.Label(select_row, text="Step:", width=6).pack(side="left", padx=(20, 0))
        self.cb_step_type = ttk.Combobox(
            select_row,
            textvariable=self.var_step_type,
            values=["Demand", "Supply"],
            width=10,
            state="readonly",
        )
        self.cb_step_type.pack(side="left", padx=5)

        ttk.Label(select_row, text="Dir:", width=4).pack(side="left")
        self.cb_direction = ttk.Combobox(
            select_row,
            textvariable=self.var_direction,
            values=["Outbound", "Inbound"],
            width=10,
            state="readonly",
        )
        self.cb_direction.pack(side="left", padx=5)





    def _get_current_root_for_business_animation(self):
        root = getattr(self, "root_node_outbound", None)
        if root is not None:
            return root

        direction = str(self.var_direction.get()).strip().upper() if hasattr(self, "var_direction") else "OUT"
        if direction.startswith("IN"):
            return getattr(self.env, "root_node_inbound", None) or getattr(self, "root_node_inbound", None)

        prod = self.var_product.get().strip() if hasattr(self, "var_product") else ""
        env = self.env
        if prod:
            return (
                (getattr(env, "prod_tree_dict_OT", {}) or {}).get(prod)
                or getattr(env, "root_node_outbound", None)
                or getattr(self, "root_node_outbound", None)
                or getattr(env, "root", None)
                or getattr(self, "root", None)
            )

        return (
            getattr(env, "root_node_outbound", None)
            or getattr(self, "root_node_outbound", None)
            or getattr(env, "root", None)
            or getattr(self, "root", None)
        )

    def _get_current_edges_for_business_animation(self):
        edges = getattr(self, "current_planning_tree_edges", None)
        if edges:
            return list(edges)

        bridge = getattr(self, "last_bridge_payload", None) or getattr(self, "bridge_payload", None)
        if isinstance(bridge, dict):
            candidate = bridge.get("planning_tree_edges") or bridge.get("edges")
            if candidate:
                return list(candidate)

        root = self._get_current_root_for_business_animation()
        if root is None:
            return []
        return build_edges_from_root(root)

    def build_business_animation_context(self):
        if BusinessAnimationContext is None:
            return None

        try:
            product_name = str(self.var_product.get()).strip()
        except Exception:
            product_name = getattr(self.env, "product_selected", None)

        try:
            direction = str(self.var_direction.get()).strip()
        except Exception:
            direction = "Outbound"

        scenario_name = getattr(self, "current_mode", "recompute")
        selected_node = getattr(self.state, "selected_node", None) or None

        root_node = self._get_current_root_for_business_animation()
        edges = self._get_current_edges_for_business_animation()

        node_dict = {}
        try:
            env_node_dict = getattr(self.env, "node_dict", None)
            if isinstance(env_node_dict, dict) and env_node_dict:
                node_dict = dict(env_node_dict)
            elif root_node is not None:
                for n in iter_nodes(root_node):
                    nn = getattr(n, "name", None)
                    if nn:
                        node_dict[nn] = n
        except Exception:
            pass

        trace_events = list(getattr(self, "trace_event_sink", []) or [])
        bridge_payload = getattr(self, "last_bridge_payload", None) or {}

        #@STOP
        #cashflow_df = getattr(self, "df_cash", None)
        #@UPDATE
        cashflow_df = getattr(self, "df_animation_kpi", None)
        if cashflow_df is None:
            cashflow_df = build_animation_kpi_df_from_cashflow(getattr(self, "df_cash", None))

        pos_e2e = None
        try:
            root_out = (
                getattr(self.env, "root_node_outbound", None)
                or getattr(self, "root_node_outbound", None)
            )
            root_in = (
                getattr(self.env, "root_node_inbound", None)
                or getattr(self, "root_node_inbound", None)
            )
            if root_out is not None or root_in is not None:
                pos_e2e = make_E2E_positions(
                    root_node_outbound=root_out,
                    root_node_inbound=root_in,
                    dx=1.0,
                    dy=1.0,
                    office_margin=1.0,
                )
        except Exception as e:
            print(f"[business_animation] make_E2E_positions skipped: {e}")
            pos_e2e = None

        metadata = {
            "source": "cockpit_tk",
            "product_name": product_name,
            "direction": direction,
            "scenario_name": scenario_name,
            "node_positions": pos_e2e,
        }

        return BusinessAnimationContext(
            product_name=product_name,
            scenario_name=scenario_name,
            direction=direction,
            selected_node=selected_node,
            root_node=root_node,
            node_dict=node_dict,
            edges=edges,
            trace_events=trace_events,
            bridge_payload=bridge_payload,
            cashflow_df=cashflow_df,
            metadata=metadata,
        )


    #@STOP
    #def open_node_selector(self):
    #    prod = self.var_product.get() if self.var_product.get() else None
    #    if not prod:
    #        return
    #    from pysi.gui.node_selector import open_node_selector
    #    open_node_selector(self.root, self.env, prod, on_select=self.set_selected_node)

    def open_node_selector(self):
        """Open V0R7-like tree selector to pick any node."""
        prod = self.var_product.get() if self.var_product.get() else None
        if not prod:
            return

        from pysi.gui.node_selector import open_node_selector as _open_node_selector
        _open_node_selector(self, self.env, prod, on_select=self.set_selected_node)





    # ----------------------------
    # Selection plumbing (single entry point)
    # ----------------------------

    #@STOP
    #def set_selected_node(self, node_name: str | None, *, source: str = ""):
    #    """Update selection state and refresh dependent views.
    #    node_name is the common key across map/network/PSI.
    #    """
    #    self.state.selected_node = node_name
    #    self.state.selected_product = self.var_product.get() if self.var_product.get() else None
    #    self.render_l1_psi_mini()

    def _ensure_env_node_dict(self):
        """Build env.node_dict once (node_name -> Node) from available trees.
        Keeps L1 rendering fast without repeated traversals.
        """
        env = self.env
        if isinstance(getattr(env, "node_dict", None), dict) and env.node_dict:
            return

        node_dict = {}
        roots = []
        prod = self.var_product.get()
        if prod:
            roots.append((getattr(env, "prod_tree_dict_OT", {}) or {}).get(prod))
            roots.append((getattr(env, "prod_tree_dict_IN", {}) or {}).get(prod))
        if not prod:
            for r in (getattr(env, "prod_tree_dict_OT", {}) or {}).values():
                roots.append(r)
            for r in (getattr(env, "prod_tree_dict_IN", {}) or {}).values():
                roots.append(r)

        for root in roots:
            if not root:
                continue
            for n in iter_nodes(root):
                name = getattr(n, "name", None)
                if name and name not in node_dict:
                    node_dict[name] = n

        env.node_dict = node_dict


    def _get_money_row_for_selected_node(self, node_name: str | None):
        if not node_name:
            return None

        candidates = [
            getattr(self.env, "node_money_rows", None),
            getattr(self.env, "money_node_rows", None),
        ]

        money_payload = getattr(self.env, "money_result", None)
        if isinstance(money_payload, dict):
            candidates.append(money_payload.get("node_money_rows"))

        product_name = None
        try:
            product_name = str(self.var_product.get()).strip()
        except Exception:
            product_name = None

        # 1) prefer already evaluated rows
        for rows in candidates:
            if not isinstance(rows, list):
                continue
            for r in rows:
                if not isinstance(r, dict):
                    continue
                if (r.get("node_name") or "").strip() != node_name:
                    continue
                row_product = (r.get("product") or "").strip()
                if product_name and row_product and row_product != product_name:
                    continue
                return r

        # 2) fallback: evaluate on demand
        if evaluate_money_by_node is not None:
            try:
                rows = evaluate_money_by_node(self.env)
            except Exception as e:
                print(f"[L1] evaluate_money_by_node fallback skipped: {e}")
                return None

            if isinstance(rows, list):
                for r in rows:
                    if not isinstance(r, dict):
                        continue
                    if (r.get("node_name") or "").strip() != node_name:
                        continue
                    row_product = (r.get("product") or "").strip()
                    if product_name and row_product and row_product != product_name:
                        continue
                    return r

        return None


    def _format_money_debug_lines(self, node_name: str | None) -> list[str]:
        row = self._get_money_row_for_selected_node(node_name)
        if not row:
            return []

        def _fmt(v):
            try:
                return f"{float(v):,.2f}"
            except Exception:
                return "-"

        lines = []
        node_character = row.get("node_character")
        if node_character:
            lines.append(f"node_character: {node_character}")

        lines.extend(
            [
                f"revenue:        {_fmt(row.get('revenue'))}",
                f"variable_cost:  {_fmt(row.get('variable_cost'))}",
                f"fixed_cost:     {_fmt(row.get('fixed_cost'))}",
                f"inventory_value:{_fmt(row.get('inventory_value'))}",
                f"profit:         {_fmt(row.get('profit'))}",
            ]
        )
        return lines





    def l1_clear(self):
        self.l1_text.delete("1.0", "end")

    def l1_show_text(self, s: str):
        self.l1_clear()
        self.l1_text.insert("end", s)


    def render_l1_psi_mini(self):
        node_name = getattr(self.state, "selected_node", None)
        if not node_name:
            self.l1_show_text("[L1] no node selected")
            return

        self._ensure_env_node_dict()
        node_dict = getattr(self.env, "node_dict", None)
        if not isinstance(node_dict, dict):
            self.l1_show_text("[L1] env.node_dict not available")
            return

        node = node_dict.get(node_name)
        if node is None:
            self.l1_show_text(f"[L1] node not found: {node_name}")
            return

        self.l1_draw_mini_from_node(node)



    def l1_draw_mini_from_node(self, node):
        """Default mini view: last 10 weeks of S/I/P lot counts (supply layer)."""
        def cnt(x):
            return len(x) if x else 0

        psi4 = getattr(node, "psi4supply", None) or []

        #@RESET
        # keep mini text compact so money debug lines remain visible
        #W = min(10, len(psi4))
        W = min(5, len(psi4))

        lines = [f"node: {getattr(node, 'name', '')}", ""]

        #@STOP@GO
        for w in range(W):
            try:
                S = cnt(psi4[w][0])
                I = cnt(psi4[w][2])
                P = cnt(psi4[w][3])
            except Exception:
                S = I = P = 0
            lines.append(f"w{w+1:02d}  S:{S:4d}  I:{I:4d}  P:{P:4d}")
        
        if W == 0:
            lines.append("(psi4supply is empty)")


        #@ADD "MONEY attribute" on "node&product"
        money_lines = self._format_money_debug_lines(getattr(node, "name", None))
        if money_lines:
            lines.extend([""] + money_lines)
        
        self.l1_show_text("\n".join(lines))

    # ----------------------------
    # World Map integration
    # ----------------------------

    def open_world_map(self):
        """Open World Map view and wire click -> set_selected_node()."""
        prod = self.var_product.get() if self.var_product.get() else None
        if not prod:
            return None

        parent = self  # tk.Tk なので self が親

        # Preferred: env has show_world_map that accepts on_select callback.
        if hasattr(self.env, "show_world_map"):
            fn = getattr(self.env, "show_world_map")
            try:
                self._world_map_view = fn(
                    product_name=prod,
                    on_select=self.set_selected_node,
                    parent_tk=parent,
                )
                return self._world_map_view
            except TypeError:
                # old signature fallback
                try:
                    self._world_map_view = fn(product_name=prod, on_select=self.set_selected_node)
                    return self._world_map_view
                except TypeError:
                    self._world_map_view = fn(product_name=prod)
                    return self._world_map_view

        # Fallback: helper module
        try:
            #@STOP
            #from pysi.gui.world_map_view import show_world_map  # type: ignore
            #self._world_map_view = show_world_map(
            #    self.env,
            #    product_name=prod,
            #    on_select=self.set_selected_node,
            #    parent_tk=parent,
            #)

            #@STOP2
            #self._world_map_view = _show_world_map(
            #    env,
            #    product_name=prod,
            #    on_select=cb,
            #    parent_tk=root,
            #    title="Global Supply Chain Map",
            #)

            self._world_map_view = _show_world_map(
                self.env,
                product_name=prod,
                on_select=self.set_selected_node,
                parent_tk=parent,
                title="Global Supply Chain Map",
            )



            return self._world_map_view
        except Exception as e:
            self.l1_show_text(f"[World Map] not available: {e}")
            return None
        
        
    def _build_kpi_cards(self):
        # simple label grid (not fancy cards, but clean)
        for i, key in enumerate(["Profit", "Service(JIT MAD)", "CCC(placeholder)", "Utilization", "Inventory(last/avg)", "NetCash(min/cum_min)"]):
            lab = ttk.Label(self.kpi_frame, text=f"{key}: -", anchor="w")
            lab.grid(row=0, column=i, sticky="w", padx=8)
            self.kpi_labels[key] = lab

    def _load_moms_from_geo(self):
        # env.load_directory should exist in your code; fallback to current dir
        base = getattr(self.env, "load_directory", ".")
        path = os.path.join(base, "node_geo.csv")
        if not os.path.exists(path):
            return []
        df = pd.read_csv(path, encoding="utf-8-sig")
        moms = sorted(df["node_name"].astype(str)[df["node_name"].astype(str).str.startswith("MOM")].unique().tolist())
        return moms

    def _resolve_moms(self):
        # prefer MOMs that exist in weekly_capability for current product (if any)
        wc = getattr(self.env, "weekly_capability", {}) or {}
        prod = getattr(self.env, "product_selected", None)
        cap_keys = set((wc.get(prod, {}) or {}).keys()) if prod else set()

        if cap_keys:
            moms = [m for m in (self.moms_geo or sorted(list(cap_keys))) if m in cap_keys]
            return moms or sorted(list(cap_keys))
        return self.moms_geo

    def _resolve_selectable_node_names(self):
        """
        GUI の node selector に出す node.name 一覧を返す。

        優先順位:
          1) env.node_dict の keys
          2) 現在 product の outbound / inbound tree を走査して収集
        """
        try:
            self._ensure_env_node_dict()
        except Exception:
            pass

        node_dict = getattr(self.env, "node_dict", None)
        if isinstance(node_dict, dict) and node_dict:
            return sorted(str(k) for k in node_dict.keys() if k)

        prod = None
        try:
            prod = self.var_product.get()
        except Exception:
            prod = getattr(self.env, "product_selected", None)

        names = set()
        root_ot = (getattr(self.env, "prod_tree_dict_OT", {}) or {}).get(prod, None)
        root_in = (getattr(self.env, "prod_tree_dict_IN", {}) or {}).get(prod, None)

        for root in (root_ot, root_in):
            if root is None:
                continue
            for n in iter_nodes(root):
                nm = getattr(n, "name", None)
                if nm:
                    names.add(str(nm))

        return sorted(names)

    def _resolve_dads(self):
        """Return DAD subset by prefix."""
        node_names = []
        if hasattr(self, "node_names") and isinstance(self.node_names, list):
            node_names = self.node_names
        else:
            try:
                node_names = self._resolve_selectable_node_names()
            except Exception:
                node_names = []

        dads = []
        for nm in node_names:
            s = str(nm or "").strip()
            if s.startswith("DAD"):
                dads.append(s)

        return sorted(set(dads))

    def refresh_leaf_node_dropdown(self):
        product_name = (self.var_product.get() or "").strip()
        if not product_name:
            self.cb_leaf_node["values"] = []
            self.var_leaf_node.set("")
            return

        try:
            from pysi.reporting.leaf_node_candidates import get_leaf_node_candidates_for_product

            candidates = get_leaf_node_candidates_for_product(
                self.env,
                product_name=product_name,
            )
        except Exception as e:
            print(f"[price-cost-structure] leaf dropdown refresh skipped: {e}")
            candidates = []

        self.cb_leaf_node["values"] = candidates
        if candidates:
            if self.var_leaf_node.get() not in candidates:
                self.var_leaf_node.set(candidates[0])
        else:
            self.var_leaf_node.set("")

    def on_change_node(self):
        node_name = (self.var_node.get() or "").strip()
        if not node_name:
            return
        self.set_selected_node(node_name, source="node_combobox")

    def on_change_product(self):
        # update env.product_selected then refresh selector candidates
        self.env.product_selected = self.var_product.get()

        #@ ADD for PSI accumed animation
        self.state.selected_product = self.var_product.get().strip() if self.var_product.get() else None

        self.products = sorted(list((getattr(self.env, "prod_tree_dict_OT", {}) or {}).keys())) or self.products
        self.moms = self._resolve_moms()
        self.node_names = self._resolve_selectable_node_names()
        self.dads = self._resolve_dads()

        self.cb_node["values"] = self.node_names
        if self.node_names and self.var_node.get() not in self.node_names:
            self.var_node.set(self.node_names[0])

        # SelectionState も current selector に合わせる
        self.state.selected_node = self.var_node.get().strip() if self.var_node.get() else None

        # decouple default
        prod = self.var_product.get()
        self.decouple_node_selected = self._detect_default_decouple_nodes(prod)

        self.refresh_leaf_node_dropdown()
        self.refresh()

        try:
            if self.business_animation_panel is not None:
                ctx = self.build_business_animation_context()
                if ctx is not None:
                    self.business_animation_panel.set_context(ctx)
        except Exception:
            pass

    def on_generate_price_cost_structure_chart(self):
        """Thin GUI adapter to generate E2E lane price/cost structure charts."""
        product_name = (self.var_product.get() or "").strip()
        if not product_name:
            messagebox.showwarning("Price & Cost Structure", "Please select a product.")
            return

        self.refresh_leaf_node_dropdown()
        leaf_node = (self.var_leaf_node.get() or "").strip()
        if not leaf_node:
            messagebox.showwarning(
                "Price & Cost Structure",
                "No leaf node candidates found for selected product.",
            )
            return

        try:
            from pysi.reporting.e2e_lane_price_chart_runtime import (
                generate_e2e_lane_price_chart_from_env,
            )

            result = generate_e2e_lane_price_chart_from_env(
                self.env,
                product_name=product_name,
                leaf_node=leaf_node,
            )

            errors = result.get("errors") or []
            warnings = result.get("warnings") or []
            files = result.get("generated_files") or []

            print("[price-cost-structure]", result)

            if errors:
                messagebox.showerror(
                    "Price & Cost Structure",
                    "\n".join(str(e) for e in errors),
                )
                return

            msg_lines = []
            if files:
                msg_lines.append("Generated chart files:")
                msg_lines.extend(str(p) for p in files)
            else:
                msg_lines.append("No chart files were generated.")
                msg_lines.append("")
                msg_lines.append("Possible reasons:")
                msg_lines.append("- selected product has all-zero price/cost values")
                msg_lines.append("- no matching E2E route rows")
                msg_lines.append("- no matching node_price_waterfall rows")
                msg_lines.append("- Run Full Plan has not been executed")

            if warnings:
                msg_lines.append("")
                msg_lines.append("Warnings:")
                msg_lines.extend(str(w) for w in warnings)

            messagebox.showinfo("Price & Cost Structure", "\n".join(msg_lines))
        except Exception as exc:
            messagebox.showerror("Price & Cost Structure", str(exc))



    def run_and_refresh(self):
        """
        ★ rerun_fn があれば：pipeline を再実行して env を差し替え
        ★ なければ：従来フォールバック（軽量再計算）
        """
        self.current_mode = "recompute"
        prod = self.var_product.get()

        baseline_snapshot = None
        try:
            baseline_snapshot = self._build_management_snapshot()
        except Exception as e:
            print("[management_cockpit] baseline snapshot skipped:", e)

        if callable(self.rerun_fn):
            try:
                new_env = self.rerun_fn(product=prod)
            except TypeError:
                # 互換用（万が一 positional のみだった場合）
                new_env = self.rerun_fn(prod)

            if new_env is not None:
                # env swap
                self.env = new_env

                # lists refresh (product / subsets / node selector)
                self.products = sorted(list((getattr(self.env, "prod_tree_dict_OT", {}) or {}).keys())) or self.products
                self.moms_geo = self._load_moms_from_geo()
                self.moms = self._resolve_moms()
                self.node_names = self._resolve_selectable_node_names()
                self.dads = self._resolve_dads()

                # combobox update
                self.cb_product["values"] = self.products
                self.cb_node["values"] = self.node_names

                # keep selection stable
                if self.products and prod not in self.products:
                    prod = self.products[0]
                self.var_product.set(prod)
                self.env.product_selected = prod

                if self.node_names:
                    current_node = self.state.selected_node or self.var_node.get()
                    if current_node not in self.node_names:
                        self.var_node.set(self.node_names[0])
                    else:
                        self.var_node.set(current_node)

                self.state.selected_product = prod
                self.state.selected_node = self.var_node.get().strip() if self.var_node.get() else None
        else:
            # fallback: only call evaluation if exists
            if hasattr(self.env, "demand_leveling4multi_prod"):
                self.env.demand_leveling4multi_prod()

        scenario_snapshot = None
        try:
            scenario_snapshot = self._build_management_snapshot()
        except Exception as e:
            print("[management_cockpit] scenario snapshot skipped:", e)

        try:
            self.refresh_management_cockpit(
                baseline_snapshot=baseline_snapshot,
                scenario_snapshot=scenario_snapshot,
            )
        except Exception as e:
            print("[management_cockpit] refresh after run_and_refresh skipped:", e)

        self.refresh()

# ********
# planning engine
# ********
    #def run_full_plan(self):
    #    """
    #    GUI entry point for full integrated planning.
    #    """
    #    try:
    #        self._run_planning_sequence(use_selected_decouples=True)
    #        print("[full-plan] completed")
    #    except Exception as e:
    #        try:
    #            messagebox.showerror("Run Full Plan", f"Full planning failed.\n\n{e}")
    #        except Exception:
    #            print("[ERROR] Run Full Plan:", e)


    def run_full_plan(self):
        self.current_mode = "full_plan"
        baseline_snapshot = None
        try:
            baseline_snapshot = self._build_management_snapshot()
        except Exception as e:
            print("[management_cockpit] baseline snapshot skipped before full plan:", e)

        try:
            self._run_planning_sequence(use_selected_decouples=True)

            scenario_snapshot = None
            try:
                scenario_snapshot = self._build_management_snapshot()
            except Exception as e:
                print("[management_cockpit] scenario snapshot skipped after full plan:", e)

            try:
                self.refresh_management_cockpit(
                    baseline_snapshot=baseline_snapshot,
                    scenario_snapshot=scenario_snapshot,
                )
            except Exception as e:
                print("[management_cockpit] refresh after full plan skipped:", e)

            self.refresh()
            print("[full-plan] completed")
        except Exception as e:
            import traceback
            traceback.print_exc()

            try:
                messagebox.showerror(
                    "Run Full Plan",
                    f"Full planning failed.\n\n{e}"
                )
            except Exception:
                print("[ERROR] Run Full Plan:", e)


    def _run_planning_sequence(self, *, use_selected_decouples: bool = True):
        import pysi.plan.engines as eng

        prod = (self.var_product.get() or "").strip()

        out_root = None
        in_root = None

        try:
            out_root = (getattr(self.env, "prod_tree_dict_OT", {}) or {}).get(prod)
        except Exception:
            pass

        try:
            in_root = (getattr(self.env, "prod_tree_dict_IN", {}) or {}).get(prod)
        except Exception:
            pass

        if out_root is None:
            out_root = getattr(self.env, "root_node_outbound", None)

        if in_root is None:
            in_root = getattr(self.env, "root_node_inbound", None)

        if not (out_root and in_root):
            print(
                f"[WARN] roots not ready for product={prod} "
                f"(out_root={out_root is not None}, in_root={in_root is not None})"
            )
            return

        #@ADD for debug
        print("[root-check] prod =", prod)

        print("[root-check] has self.prod_tree_dict_OT =", hasattr(self, "prod_tree_dict_OT"))
        print("[root-check] has self.prod_tree_dict_IN =", hasattr(self, "prod_tree_dict_IN"))
        print("[root-check] has self.env.prod_tree_dict_OT =", hasattr(self.env, "prod_tree_dict_OT"))
        print("[root-check] has self.env.prod_tree_dict_IN =", hasattr(self.env, "prod_tree_dict_IN"))

        print("[root-check] self root out id =", id(getattr(self, "root_node_outbound", None)))
        print("[root-check] self root in  id =", id(getattr(self, "root_node_inbound", None)))
        print("[root-check] env  root out id =", id(getattr(self.env, "root_node_outbound", None)))
        print("[root-check] env  root in  id =", id(getattr(self.env, "root_node_inbound", None)))

        sr_out = (getattr(self, "prod_tree_dict_OT", {}) or {}).get(prod)
        sr_in  = (getattr(self, "prod_tree_dict_IN", {}) or {}).get(prod)
        er_out = (getattr(self.env, "prod_tree_dict_OT", {}) or {}).get(prod)
        er_in  = (getattr(self.env, "prod_tree_dict_IN", {}) or {}).get(prod)

        print("[root-check] self prod out id =", id(sr_out) if sr_out else None)
        print("[root-check] self prod in  id =", id(sr_in) if sr_in else None)
        print("[root-check] env  prod out id =", id(er_out) if er_out else None)
        print("[root-check] env  prod in  id =", id(er_in) if er_in else None)

        print("[root-check] self prod out len =", len(sr_out.psi4supply) if sr_out and getattr(sr_out, "psi4supply", None) else None)
        print("[root-check] self prod in  len =", len(sr_in.psi4demand) if sr_in and getattr(sr_in, "psi4demand", None) else None)
        print("[root-check] env  prod out len =", len(er_out.psi4supply) if er_out and getattr(er_out, "psi4supply", None) else None)
        print("[root-check] env  prod in  len =", len(er_in.psi4demand) if er_in and getattr(er_in, "psi4demand", None) else None)

        print("[root-check] out_root name =", getattr(out_root, "name", None))
        print("[root-check] in_root  name =", getattr(in_root, "name", None))




        selected_node_name = (self.state.selected_node or "").strip() if getattr(self, "state", None) else ""
        if selected_node_name.startswith("MOM"):
            mom_name = selected_node_name
        elif getattr(self, "moms", None):
            mom_name = self.moms[0]
        else:
            mom_name = "MOM"
        decouples = (getattr(self, "decouple_node_selected", []) or []) if use_selected_decouples else None

        print(f"[full-plan] product={prod}")
        print(f"[full-plan] mom_name={mom_name}")
        print(f"[full-plan] decouples={decouples}")

        print("[full-plan] step1 outbound_backward_leaf_to_MOM")
        out_root, in_root = eng.outbound_backward_leaf_to_MOM(out_root, in_root, layer="demand")

        #@STOP
        # 旧 capacity leveling。新しい flow では
        # step2.4 allocate_markets_to_moms
        # step2.5 level_mom_demand_with_capacity
        # に置き換える。
        #print("[full-plan] step2 inbound_MOM_leveling_vs_capacity")
        #out_root, in_root = eng.inbound_MOM_leveling_vs_capacity(out_root, in_root, mom_name=mom_name)




        # ********
        # INBOUND Planning
        # ********

        #@STOP
        #@ COPY demand 2 supply
        #def _copy_slot0_demand_to_supply(root):
        #    stack = [root]
        #    while stack:
        #        n = stack.pop()
        #        d = getattr(n, "psi4demand", None)
        #        s = getattr(n, "psi4supply", None)
        #        if isinstance(d, list) and isinstance(s, list):
        #            weeks = min(len(d), len(s))
        #            for w in range(weeks):
        #                if len(d[w]) > 0 and len(s[w]) > 0:
        #                    s[w][0] = list(d[w][0])
        #        stack.extend(getattr(n, "children", []) or [])

        #@STOP
        #print("[full-plan] step3 inbound_backward_MOM_to_leaf")
        #out_root, in_root = eng.inbound_backward_MOM_to_leaf(out_root, in_root, layer="demand")

        # ********
        # Define Production Allocate Policy
        # ********
        MOM_POLICY_IPHONE = {
            "CN": ["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
            "JP": ["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
            "US": ["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
            "DE": ["MOM_final_assy_EURO", "MOM_final_assy_ASIA"],
            "UK": ["MOM_final_assy_EURO", "MOM_final_assy_ASIA"],
            "DEFAULT": ["MOM_final_assy_ASIA"],
        }

        # ********
        # MOM ALLOCATION
        # ********
        print("[full-plan] step2.4 allocate_markets_to_moms")
        out_root, in_root = eng.allocate_markets_to_moms(
            out_root,
            in_root,
            policy=MOM_POLICY_IPHONE,
            source_layer="outbound_supply",
            debug=True,
        )



        #@STOP
        #print("[full-plan] step3 inbound_backward_MOM_to_leaf")
        #out_root, in_root = eng.inbound_backward_MOM_to_leaf(
        #    out_root,
        #    in_root,
        #    layer="demand",
        #    mom_policy=MOM_POLICY_IPHONE,
        #)


        # CAPACITY 
        out_root, in_root, capacity_result = eng.level_mom_demand_with_capacity(
            out_root,
            in_root,
            product=prod,
            secondary_policy=MOM_POLICY_IPHONE,
            debug=True,
        )

        self.last_capacity_result = capacity_result

        assigned_map = capacity_result.get("week_mom_assigned", {}) if isinstance(capacity_result, dict) else {}
        capacity_map = capacity_result.get("week_mom_capacity", {}) if isinstance(capacity_result, dict) else {}
        overflow_map = capacity_result.get("week_mom_overflow", {}) if isinstance(capacity_result, dict) else {}
        moved_secondary = capacity_result.get("lot_moves_secondary", []) if isinstance(capacity_result, dict) else []
        backlogged = capacity_result.get("lot_backlogged", []) if isinstance(capacity_result, dict) else []

        assigned_summary = {}
        capacity_summary = {}
        overflow_summary = {}

        for (_, mom_name), cnt in assigned_map.items():
            assigned_summary[mom_name] = assigned_summary.get(mom_name, 0) + cnt

        for (_, mom_name), cnt in capacity_map.items():
            capacity_summary[mom_name] = capacity_summary.get(mom_name, 0) + cnt

        for (_, mom_name), cnt in overflow_map.items():
            overflow_summary[mom_name] = overflow_summary.get(mom_name, 0) + cnt

        print(
            "[full-plan] step2.5 capacity summary:",
            "assigned_total=", assigned_summary,
            "capacity_total=", capacity_summary,
            "overflow_total=", overflow_summary,
            "moved_secondary=", len(moved_secondary),
            "backlogged=", len(backlogged),
        )





        #@DEBUG
        print("[full-plan] step3 inbound_backward_MOM_to_leaf")
        #out_root, in_root = eng.inbound_backward_MOM_to_leaf(out_root, in_root)
        out_root, in_root = eng.inbound_backward_MOM_to_leaf(
            out_root,
            in_root,
            layer="demand",

            #@STOP
            #mom_policy=MOM_POLICY_IPHONE,
            mom_policy=None,   # ここでは再配分しない
        )
        self._debug_dump_mom_lot_counts(
            in_root,
            label="after step3 inbound_backward_MOM_to_leaf",
            focus_names=["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
        )


        #print("[full-plan] step3.5 inbound demand->supply bridge")
        #_copy_slot0_demand_to_supply(in_root)

        # *********************
        # Plan Engine STOP
        # *********************
        #print("[full-plan] step3.5 inbound_seed_supply_from_demand")
        #eng.bridge_inbound_demand_to_supply (in_root)\

        #print("[full-plan] step4 inbound_forward_leaf_to_MOM")
        #out_root, in_root = eng.inbound_forward_leaf_to_MOM(out_root, in_root, layer="supply")

        #print("[full-plan] step5 push_pull")
        #out_root, in_root = eng.push_pull(out_root, in_root, decouple_nodes=decouples)


        # *********************
        # Plan Engine DEBUG
        # *********************
        print("[full-plan] step3.5 inbound_seed_supply_from_demand")
        eng.bridge_inbound_demand_to_supply(in_root)
        self._debug_dump_mom_lot_counts(
            in_root,
            label="after step3.5 bridge_inbound_demand_to_supply",
            focus_names=["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
        )

        print("[full-plan] step4 inbound_forward_leaf_to_MOM")
        out_root, in_root = eng.inbound_forward_leaf_to_MOM(out_root, in_root, layer="supply")
        self._debug_dump_mom_lot_counts(
            in_root,
            label="after step4 inbound_forward_leaf_to_MOM",
            focus_names=["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
        )

        print("[full-plan] step4.5 allocate_lots_to_dads")
        out_root, in_root, handoff_result = eng.allocate_lots_to_dads(
            out_root,
            in_root,
            source_moms=["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
            source_slot=0,   # MOM.psi4supply[w][0:S]
            seed_slot=3,     # DAD.psi4supply[w][3:P]
            debug=True,
        )
        self.last_dad_handoff_result = handoff_result

        dad_counts = handoff_result.get("week_dad_counts", {}) if isinstance(handoff_result, dict) else {}
        dad_summary = {}
        for (_, dad_name), cnt in dad_counts.items():
            dad_summary[dad_name] = dad_summary.get(dad_name, 0) + cnt
        print(
            "[full-plan] step4.5 handoff summary:",
            "dad_total=", dad_summary,
            "unresolved_lots=", len(handoff_result.get("unresolved_lots", [])) if isinstance(handoff_result, dict) else -1,
            "unresolved_leafs=", len(handoff_result.get("unresolved_leafs", [])) if isinstance(handoff_result, dict) else -1,
        )


        print("[full-plan] step5 push_pull")

        #@STOP planning from root       
        #out_root, in_root = eng.push_pull(out_root, in_root, decouple_nodes=decouples)

        seeded_dads = sorted(dad_summary.keys())
        print("[full-plan] step5 seeded_dads =", seeded_dads)
        out_root, in_root = eng.push_pull(
            out_root,
            in_root,
            decouple_nodes=decouples,
            seeded_dads=seeded_dads,
        )

        self._debug_dump_mom_lot_counts(
            in_root,
            label="after step5 push_pull",
            focus_names=["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
        )





        self.root_node_outbound = out_root
        self.root_node_inbound = in_root

        try:
            self.env.root_node_outbound = out_root
        except Exception:
            pass

        try:
            self.env.root_node_inbound = in_root
        except Exception:
            pass

        try:
            self.update_evaluation_results4multi_product()
            self._ensure_cost_df()
        except Exception as e:
            print("[WARN] evaluation:", e)

        try:
            self.refresh()
        except Exception as e:
            print("[WARN] refresh views:", e)


# ********
# helper
# ********
    def _dbg_total_and_unique_lots(self, psi, slot_idx=0):
        total = 0
        uniq = set()

        for week in (psi or []):
            try:
                lots = week[slot_idx] or []
            except Exception:
                lots = []

            total += len(lots)
            for lot in lots:
                uniq.add(str(lot))

        return total, len(uniq)

    def _dbg_nonzero_weeks(self, psi, slot_idx=0, limit=8):
        hits = []
        for w, week in enumerate(psi or [], start=1):
            try:
                cnt = len(week[slot_idx] or [])
            except Exception:
                cnt = 0

            if cnt:
                hits.append((w, cnt))
                if len(hits) >= limit:
                    break
        return hits

    def _debug_dump_mom_lot_counts(self, in_root, label="", focus_names=None):
        """
        MOM別の demand/supply lot 状況を表示する。
        total と unique を両方出すので、append重複の検出に使いやすい。
        slot convention:
          0 = S
          2 = I
          3 = P
        """
        if in_root is None:
            print(f"[mom-debug] {label} : in_root is None")
            return

        names_filter = set(focus_names or [])

        stack = [in_root]
        moms = []
        seen = set()

        while stack:
            n = stack.pop()
            if n is None:
                continue
            if id(n) in seen:
                continue
            seen.add(id(n))

            nm = str(getattr(n, "name", "") or "")
            if nm.startswith("MOM"):
                if not names_filter or nm in names_filter:
                    moms.append(n)

            for c in getattr(n, "children", []) or []:
                stack.append(c)

        moms = sorted(moms, key=lambda x: str(getattr(x, "name", "")))

        print("=" * 110)
        print(f"[mom-debug] {label}")
        if not moms:
            print("[mom-debug] no MOM nodes found under in_root")
            print("=" * 110)
            return

        for mom in moms:
            nm = str(getattr(mom, "name", "") or "")
            psi_d = getattr(mom, "psi4demand", None) or []
            psi_s = getattr(mom, "psi4supply", None) or []

            dS_total, dS_unique = self._dbg_total_and_unique_lots(psi_d, 0)
            dI_total, dI_unique = self._dbg_total_and_unique_lots(psi_d, 2)
            dP_total, dP_unique = self._dbg_total_and_unique_lots(psi_d, 3)

            sS_total, sS_unique = self._dbg_total_and_unique_lots(psi_s, 0)
            sI_total, sI_unique = self._dbg_total_and_unique_lots(psi_s, 2)
            sP_total, sP_unique = self._dbg_total_and_unique_lots(psi_s, 3)

            dS_nz = self._dbg_nonzero_weeks(psi_d, 0, limit=8)
            sS_nz = self._dbg_nonzero_weeks(psi_s, 0, limit=8)
            dP_nz = self._dbg_nonzero_weeks(psi_d, 3, limit=8)
            sP_nz = self._dbg_nonzero_weeks(psi_s, 3, limit=8)

            print(
                f"[mom-debug] {nm} | "
                f"demand S total={dS_total} unique={dS_unique}, "
                f"I total={dI_total} unique={dI_unique}, "
                f"P total={dP_total} unique={dP_unique}"
            )
            print(
                f"[mom-debug] {nm} | "
                f"supply S total={sS_total} unique={sS_unique}, "
                f"I total={sI_total} unique={sI_unique}, "
                f"P total={sP_total} unique={sP_unique}"
            )
            print(
                f"[mom-debug] {nm} | "
                f"demand_nz_S={dS_nz} | supply_nz_S={sS_nz}"
            )
            print(
                f"[mom-debug] {nm} | "
                f"demand_nz_P={dP_nz} | supply_nz_P={sP_nz}"
            )

        print("=" * 110)





    def _detect_default_decouple_nodes(self, product_name=None):
        """
        decouple / buffer node candidates.
        Priority:
        1. stock_buffer / decouple_node flag
        2. node name starts with 'DAD'
        """
        names = set()
        root = None

        try:
            if product_name and getattr(self.env, "prod_tree_dict_OT", None):
                root = self.env.prod_tree_dict_OT.get(product_name)
        except Exception:
            root = None

        if root is None:
            root = getattr(self, "root_node_outbound", None)

        if root is None:
            return []

        stack = [root]

        while stack:
            n = stack.pop()

            if getattr(n, "stock_buffer", False) or getattr(n, "decouple_node", False):
                names.add(getattr(n, "name", ""))
            elif str(getattr(n, "name", "")).startswith("DAD"):
                names.add(getattr(n, "name", ""))

            for c in getattr(n, "children", []) or []:
                stack.append(c)

        return sorted([x for x in names if x])



    def _get_graph_edges_for_event_inference(self):
        """
        event inference 用の edge 集合を返す。

        優先順位:
        1. current product の planning tree を make_highlight_flow と同じ walk で辿る
        2. fallback として GUI / networkX graph
        """
        edges = set()

        product_name = (self.var_product.get() or "").strip()
        if not product_name:
            return edges

        # direction 解釈
        direction = "OUT"
        raw_direction = ""
        if hasattr(self, "var_direction"):
            try:
                raw_direction = (self.var_direction.get() or "").strip().lower()
            except Exception:
                raw_direction = ""

        if raw_direction in ("inbound", "in"):
            direction = "IN"

        # --------------------------------------------------
        # 1) planning tree edges
        #    make_highlight_flow() と同じ tree walk を使う
        # --------------------------------------------------
        try:
            prod_tree_dict_OT = getattr(self.env, "prod_tree_dict_OT", {}) or {}
            prod_tree_dict_IN = getattr(self.env, "prod_tree_dict_IN", {}) or {}

            prod_tree_OT = prod_tree_dict_OT.get(product_name)
            prod_tree_IN = prod_tree_dict_IN.get(product_name)

            highlight_flow = {}

            def walk_tree(plan_node):
                if plan_node is None:
                    return
                for child in getattr(plan_node, "children", []) or []:
                    from_node = getattr(plan_node, "name", None) or getattr(plan_node, "node_id", None)
                    to_node = getattr(child, "name", None) or getattr(child, "node_id", None)
                    if from_node is not None and to_node is not None:
                        if from_node not in highlight_flow:
                            highlight_flow[from_node] = {}
                        highlight_flow[from_node][to_node] = 1.0
                        edges.add((str(from_node), str(to_node)))
                    walk_tree(child)

            # make_highlight_flow と同様に outbound / inbound の両方を歩けるようにする
            if direction == "OUT":
                if prod_tree_OT is not None:
                    print("[trace] highlight-style outbound root =", getattr(prod_tree_OT, "name", None))
                    walk_tree(prod_tree_OT)
            else:
                if prod_tree_IN is not None:
                    print("[trace] highlight-style inbound root =", getattr(prod_tree_IN, "name", None))
                    walk_tree(prod_tree_IN)

            if edges:
                print(
                    f"[trace] planning-tree edges for product={product_name}, direction={direction}: {len(edges)}"
                )
                print("[trace] planning-tree edge sample:", list(edges)[:10])
                return edges

        except Exception as e:
            print(f"[trace] planning-tree edge extraction skipped: {e}")

        # --------------------------------------------------
        # 2) fallback: GUI/networkX graph
        # --------------------------------------------------
        try:
            viewer = getattr(self, "_network_viewer", None)
            if viewer is not None:
                for attr_name in ("G", "graph", "_graph"):
                    g = getattr(viewer, attr_name, None)
                    if g is not None:
                        try:
                            for u, v in g.edges():
                                edges.add((str(u), str(v)))
                        except Exception:
                            pass
                        if edges:
                            print(f"[trace] fallback viewer graph edges: {len(edges)}")
                            return edges
        except Exception:
            pass

        try:
            for attr_name in ("G", "graph", "_graph"):
                g = getattr(self, attr_name, None)
                if g is not None:
                    try:
                        for u, v in g.edges():
                            edges.add((str(u), str(v)))
                    except Exception:
                        pass
                    if edges:
                        print(f"[trace] fallback cockpit graph edges: {len(edges)}")
                        return edges
        except Exception:
            pass

        return edges







    def _get_node_char_by_node_id(self):
        """
        node_id -> Node Character の辞書を返す。
        優先順位:
        1) self.node_char_by_node_id
        2) self.env.node_char_by_node_id
        3) cockpit 側の最小 fallback 推定
        """
        d = getattr(self, "node_char_by_node_id", None)
        if isinstance(d, dict) and d:
            return d

        d = getattr(self.env, "node_char_by_node_id", None)
        if isinstance(d, dict) and d:
            return d

        d = self._build_default_node_char_by_node_id()
        self.node_char_by_node_id = d
        return d

    def _build_default_node_char_by_node_id(self):
        """
        GUI 側の最小 fallback node character を作る。
        目的:
        - event_rules.py に consumer / retail / warehouse / dc の最低限の意味を渡す
        - 特に CS_CAL のような consumer node を consumer として解釈できるようにする

        ルールは暫定:
        - supply_point => supplier
        - CS*         => consumer
        - RT*         => retail
        - WS* / GR_WS*=> warehouse
        - DAD* / GR_* => dc
        - MOM* / PAD* => factory
        """
        out = {}

        def put(node_id, **kwargs):
            nid = str(node_id or "").strip()
            if not nid:
                return
            if nid not in out:
                out[nid] = {"node_role": "generic"}
            out[nid].update(kwargs)

        # 明示ルール
        put("supply_point", node_role="supplier", can_purchase=True, can_store=True, can_ship=True)
        put("root", node_role="root")

        # 現在 product の planning tree を起点に node 名を収集
        product_name = (self.var_product.get() or "").strip()
        roots = []
        try:
            prod_tree_dict_OT = getattr(self.env, "prod_tree_dict_OT", {}) or {}
            prod_tree_dict_IN = getattr(self.env, "prod_tree_dict_IN", {}) or {}
            if product_name:
                roots.append(prod_tree_dict_OT.get(product_name))
                roots.append(prod_tree_dict_IN.get(product_name))
        except Exception:
            pass

        def walk(root):
            stack = [root]
            seen = set()
            while stack:
                node = stack.pop()
                if node is None:
                    continue
                node_key = id(node)
                if node_key in seen:
                    continue
                seen.add(node_key)
                yield node
                for child in getattr(node, "children", []) or []:
                    stack.append(child)

        for root in roots:
            for node in walk(root):
                nid = str(getattr(node, "name", None) or getattr(node, "node_id", None) or "").strip()
                if not nid:
                    continue

                upper = nid.upper()

                if upper.startswith("CS"):
                    put(
                        nid,
                        node_role="consumer",
                        can_store=True,
                        can_sell=True,
                    )
                elif upper.startswith("RT"):
                    put(
                        nid,
                        node_role="retail",
                        can_store=True,
                        can_sell=True,
                    )
                elif upper.startswith("WS") or upper.startswith("GR_WS"):
                    put(
                        nid,
                        node_role="warehouse",
                        can_store=True,
                        can_ship=True,
                    )
                elif upper.startswith("DAD") or upper.startswith("GR_"):
                    put(
                        nid,
                        node_role="dc",
                        can_store=True,
                        can_ship=True,
                        can_allocate=True,
                        is_decoupling_point=True,
                    )
                elif upper.startswith("MOM") or upper.startswith("PAD"):
                    put(
                        nid,
                        node_role="factory",
                        can_produce=True,
                        can_purchase=True,
                        can_store=True,
                    )
                else:
                    put(nid, node_role="generic")

        print("[trace] fallback node_char count =", len(out))
        print("[trace] fallback node_char sample =", list(out.items())[:10])
        print("[trace] fallback node_char[CS_CAL] =", out.get("CS_CAL"))
        return out

    def infer_and_append_trace_events_from_rows(self, rows):
        """
        PSI dump rows から canonical event を推定し、
        self.trace_event_sink に append する。
        """
        from collections import defaultdict
        from pysi.bridge.event_rules import (
            infer_events_for_lot_rows,
            canonical_events_to_trace_dicts,
        )

        if not rows:
            return []

        node_char_by_node_id = self._get_node_char_by_node_id()
        graph_edges = self._get_graph_edges_for_event_inference()

        print("[trace] actual node_char[CS_CAL] =", node_char_by_node_id.get("CS_CAL"))
        print("[trace] actual node_char[RT_CAL] =", node_char_by_node_id.get("RT_CAL"))
        print("[trace] actual node_char[WS2CAL] =", node_char_by_node_id.get("WS2CAL"))
        print("[trace] actual node_char[DADCAL] =", node_char_by_node_id.get("DADCAL"))

        lots = defaultdict(list)
        for row in rows:
            lot_id = str(row.get("lot_id", "") or "").strip()
            if not lot_id:
                continue
            lots[lot_id].append(row)

        next_sequence_no = len(self.trace_event_sink) + 1
        added_trace_dicts = []

        for lot_id in sorted(lots.keys()):
            inferred_events = infer_events_for_lot_rows(
                rows=lots[lot_id],
                node_char_by_node_id=node_char_by_node_id,
                graph_edges=graph_edges,
            )

            trace_dicts = canonical_events_to_trace_dicts(
                inferred_events,
                start_sequence_no=next_sequence_no,
            )

            self.trace_event_sink.extend(trace_dicts)
            added_trace_dicts.extend(trace_dicts)
            next_sequence_no += len(trace_dicts)

        if added_trace_dicts and self.trace_tree is not None:
            self._reload_trace_viewer()

        return added_trace_dicts






    def run_step(self):
        """
        Step-by-step planning の最小実装
        - self.env を fresh に作り直さない
        - 現在の env に対して selected step を実行
        - step 前後 snapshot から bridge payload を作る
        """
        if self.env is None:
            print("[step] skipped: self.env is None")
            return

        try:
            raw_step_type = self.var_step_type.get()
            raw_direction = self.var_direction.get()
            cap_text = self.var_capacity_ratio.get().strip()

            ctx = StepContext(
                step_type=_normalize_step_type(raw_step_type),
                direction=_normalize_direction(raw_direction),
                execution_scope="one_step",
                step_count=1,
                decoupling_node=self.var_decoupling_node.get().strip() or None,
                bottleneck_node=self.var_bottleneck_node.get().strip() or None,
                capacity_ratio=float(cap_text) if cap_text else None,
                push_pull_mode=self.var_push_pull_mode.get().strip() or None,
                priority_rule=self.var_priority_rule.get().strip() or None,
            )

            print(f"[step] ctx={ctx}")

            trace_enabled = bool(self.var_trace_enabled.get())
            if trace_enabled:
                from pysi.network.node_base import PlanningEventTracer

                self.trace_event_sink = []
                tracer = PlanningEventTracer(
                    run_id=f"step_run_{self.step_seq + 1}",
                    scenario_id="gui_step",
                    event_sink=self.trace_event_sink,
                    emitter="cockpit_run_step",
                )
                print("[trace] enabled for run_step")
            else:
                tracer = None
                print("[trace] disabled for run_step")

            prod = self.var_product.get()
            if prod:
                self.env.product_selected = prod

            #@STOP
            #before_snapshot = _safe_capture_snapshot(self.env, ctx)
            #_dispatch_step(self.env, ctx, tracer=tracer)
            #
            #after_snapshot = _safe_capture_snapshot(self.env, ctx)
            #bridge_payload = _safe_extract_bridge(before_snapshot, after_snapshot)

            #@ADD

            before_snapshot = _safe_capture_snapshot(self.env, ctx)

            print("[step] before snapshot exists:", before_snapshot is not None)
            print("[step] before lots:", len(getattr(before_snapshot, "lots", []) or []))
            print("[step] before inventory:", len(getattr(before_snapshot, "inventory", []) or []))

            before_lots = list(getattr(before_snapshot, "lots", []) or [])
            before_inv = list(getattr(before_snapshot, "inventory", []) or [])

            # ---- before: raw snapshot contents ----
            print("[step] before first 3 lots raw:", before_lots[:3])
            print("[step] before first 5 inventory raw:", before_inv[:5])

            print("[step] before lot[0] type:", type(before_lots[0]).__name__ if before_lots else None)
            print("[step] before lot[0] dir sample:", dir(before_lots[0])[:20] if before_lots else None)
            print("[step] before lot[0] repr:", repr(before_lots[0])[:300] if before_lots else None)

            print("[step] before inv[0] type:", type(before_inv[0]).__name__ if before_inv else None)
            print("[step] before inv[0] dir sample:", dir(before_inv[0])[:20] if before_inv else None)
            print("[step] before inv[0] repr:", repr(before_inv[0])[:300] if before_inv else None)

            before_bindings = getattr(before_snapshot, "bindings", None)
            if before_bindings is None:
                before_bindings = getattr(before_snapshot, "lot_demand_bindings", None)
            if before_bindings is None:
                before_bindings = []
            print("[step] before binding count:", len(before_bindings or []))

            #@ DUMP
            from dataclasses import asdict, is_dataclass

            before_snapshot = _safe_capture_snapshot(self.env, ctx)

            print("[step] before snapshot exists:", before_snapshot is not None)

            if before_snapshot is not None:
                print("[step] before snapshot type:", type(before_snapshot).__name__)
                print("[step] before snapshot time_bucket:", getattr(before_snapshot, "time_bucket", None))

                # ---- lots ----
                before_lot_keys = list((getattr(before_snapshot, "lots", {}) or {}).keys())
                before_lot_vals = list((getattr(before_snapshot, "lots", {}) or {}).values())
                print("[step] before lots count:", len(before_lot_keys))
                print("[step] before lot keys sample:", before_lot_keys[:5])
                print("[step] before lot values sample:", [repr(x) for x in before_lot_vals[:3]])

                # ---- inventory ----
                before_inv_items = list((getattr(before_snapshot, "inventory", {}) or {}).items())
                print("[step] before inventory count:", len(before_inv_items))
                print("[step] before inventory items sample:", before_inv_items[:5])

                # ---- backlog ----
                before_backlog_items = list((getattr(before_snapshot, "backlog", {}) or {}).items())
                print("[step] before backlog count:", len(before_backlog_items))
                print("[step] before backlog items sample:", before_backlog_items[:5])

                # ---- bindings ----
                before_bind_items = list((getattr(before_snapshot, "lot_demand_bindings", {}) or {}).items())
                print("[step] before binding count:", len(before_bind_items))
                print("[step] before binding items sample:", [(k, repr(v)) for k, v in before_bind_items[:5]])

                # ---- allocation pairs ----
                before_alloc_items = list((getattr(before_snapshot, "allocation_pairs", {}) or {}).items())
                print("[step] before allocation_pairs count:", len(before_alloc_items))
                print("[step] before allocation_pairs sample:", before_alloc_items[:5])

                # ---- optional full dict dump (shortened) ----
                if is_dataclass(before_snapshot):
                    before_dump = asdict(before_snapshot)
                    print("[step] before snapshot asdict keys:", list(before_dump.keys()))
                    print("[step] before snapshot asdict summary:", {
                        "time_bucket": before_dump.get("time_bucket"),
                        "lots": len(before_dump.get("lots", {}) or {}),
                        "inventory": len(before_dump.get("inventory", {}) or {}),
                        "backlog": len(before_dump.get("backlog", {}) or {}),
                        "lot_demand_bindings": len(before_dump.get("lot_demand_bindings", {}) or {}),
                        "allocation_pairs": len(before_dump.get("allocation_pairs", {}) or {}),
                    })

            #@STOP
            #_dispatch_step(self.env, ctx)
            
            #@UPDATE for Trace
            _dispatch_step(self.env, ctx, tracer=tracer)


            after_snapshot = _safe_capture_snapshot(self.env, ctx)

            print("[step] after snapshot exists:", after_snapshot is not None)
            print("[step] after lots:", len(getattr(after_snapshot, "lots", []) or []))
            print("[step] after inventory:", len(getattr(after_snapshot, "inventory", []) or []))

            after_lots = list(getattr(after_snapshot, "lots", []) or [])
            after_inv = list(getattr(after_snapshot, "inventory", []) or [])

            # ---- after: raw snapshot contents ----
            print("[step] after first 3 lots raw:", after_lots[:3])
            print("[step] after first 5 inventory raw:", after_inv[:5])

            print("[step] after lot[0] type:", type(after_lots[0]).__name__ if after_lots else None)
            print("[step] after lot[0] dir sample:", dir(after_lots[0])[:20] if after_lots else None)
            print("[step] after lot[0] repr:", repr(after_lots[0])[:300] if after_lots else None)

            print("[step] after inv[0] type:", type(after_inv[0]).__name__ if after_inv else None)
            print("[step] after inv[0] dir sample:", dir(after_inv[0])[:20] if after_inv else None)
            print("[step] after inv[0] repr:", repr(after_inv[0])[:300] if after_inv else None)

            after_bindings = getattr(after_snapshot, "bindings", None)
            if after_bindings is None:
                after_bindings = getattr(after_snapshot, "lot_demand_bindings", None)
            if after_bindings is None:
                after_bindings = []
            print("[step] after binding count:", len(after_bindings or []))

            # ---- set diff: lots / inventory keys ----
            before_lot_set = set(before_lots)
            after_lot_set = set(after_lots)
            added_lots = sorted(list(after_lot_set - before_lot_set))
            removed_lots = sorted(list(before_lot_set - after_lot_set))

            print("[step] added lots count:", len(added_lots))
            print("[step] removed lots count:", len(removed_lots))
            print("[step] added lots sample:", added_lots[:10])
            print("[step] removed lots sample:", removed_lots[:10])

            before_inv_set = set(before_inv)
            after_inv_set = set(after_inv)
            added_inv = sorted(list(after_inv_set - before_inv_set))
            removed_inv = sorted(list(before_inv_set - after_inv_set))

            print("[step] added inventory keys count:", len(added_inv))
            print("[step] removed inventory keys count:", len(removed_inv))
            print("[step] added inventory keys sample:", added_inv[:10])
            print("[step] removed inventory keys sample:", removed_inv[:10])

            # ---- bindings diff (count only for now) ----
            print("[step] binding count delta:", len(after_bindings or []) - len(before_bindings or []))

            #@ DUMP
            after_snapshot = _safe_capture_snapshot(self.env, ctx)

            print("[step] after snapshot exists:", after_snapshot is not None)

            if after_snapshot is not None:
                print("[step] after snapshot type:", type(after_snapshot).__name__)
                print("[step] after snapshot time_bucket:", getattr(after_snapshot, "time_bucket", None))

                # ---- lots ----
                after_lot_keys = list((getattr(after_snapshot, "lots", {}) or {}).keys())
                after_lot_vals = list((getattr(after_snapshot, "lots", {}) or {}).values())
                print("[step] after lots count:", len(after_lot_keys))
                print("[step] after lot keys sample:", after_lot_keys[:5])
                print("[step] after lot values sample:", [repr(x) for x in after_lot_vals[:3]])

                # ---- inventory ----
                after_inv_items = list((getattr(after_snapshot, "inventory", {}) or {}).items())
                print("[step] after inventory count:", len(after_inv_items))
                print("[step] after inventory items sample:", after_inv_items[:5])

                # ---- backlog ----
                after_backlog_items = list((getattr(after_snapshot, "backlog", {}) or {}).items())
                print("[step] after backlog count:", len(after_backlog_items))
                print("[step] after backlog items sample:", after_backlog_items[:5])

                # ---- bindings ----
                after_bind_items = list((getattr(after_snapshot, "lot_demand_bindings", {}) or {}).items())
                print("[step] after binding count:", len(after_bind_items))
                print("[step] after binding items sample:", [(k, repr(v)) for k, v in after_bind_items[:5]])

                # ---- allocation pairs ----
                after_alloc_items = list((getattr(after_snapshot, "allocation_pairs", {}) or {}).items())
                print("[step] after allocation_pairs count:", len(after_alloc_items))
                print("[step] after allocation_pairs sample:", after_alloc_items[:5])

                # ---- optional full dict dump (shortened) ----
                if is_dataclass(after_snapshot):
                    after_dump = asdict(after_snapshot)
                    print("[step] after snapshot asdict keys:", list(after_dump.keys()))
                    print("[step] after snapshot asdict summary:", {
                        "time_bucket": after_dump.get("time_bucket"),
                        "lots": len(after_dump.get("lots", {}) or {}),
                        "inventory": len(after_dump.get("inventory", {}) or {}),
                        "backlog": len(after_dump.get("backlog", {}) or {}),
                        "lot_demand_bindings": len(after_dump.get("lot_demand_bindings", {}) or {}),
                        "allocation_pairs": len(after_dump.get("allocation_pairs", {}) or {}),
                    })




            # ---- optional full dict dump (shortened) ----
            if is_dataclass(after_snapshot):
                after_dump = asdict(after_snapshot)
                print("[step] after snapshot asdict keys:", list(after_dump.keys()))
                print("[step] after snapshot asdict summary:", {
                    "time_bucket": after_dump.get("time_bucket"),
                    "lots": len(after_dump.get("lots", {}) or {}),
                    "inventory": len(after_dump.get("inventory", {}) or {}),
                    "backlog": len(after_dump.get("backlog", {}) or {}),
                    "lot_demand_bindings": len(after_dump.get("lot_demand_bindings", {}) or {}),
                    "allocation_pairs": len(after_dump.get("allocation_pairs", {}) or {}),
                })





            # --------------------------------------------------
            # current product planning tree -> dump rows -> inferred events
            # --------------------------------------------------
            try:
                step_dir = "OUT"
                raw_direction = (self.var_direction.get() or "").strip().lower()
                if raw_direction in ("inbound", "in"):
                    step_dir = "IN"

                self.build_and_append_inferred_trace_for_current_product(direction=step_dir)

            except Exception as e:
                print(f"[trace] build_and_append_inferred_trace_for_current_product skipped: {e}")





            bridge_payload = _safe_extract_bridge(before_snapshot, after_snapshot)



            self.last_bridge_payload = bridge_payload
            self.current_mode = "step"
            self.step_seq += 1
            self.last_step_context = ctx

            setattr(self.env, "_bridge_events", bridge_payload.get("events", []))
            setattr(self.env, "_bridge_kernel_flow_events", bridge_payload.get("kernel_flow_events", []))
            setattr(self.env, "_bridge_sidecar_events", bridge_payload.get("sidecar_events", []))

            print(
                "[step] bridge payload:",
                len(bridge_payload.get("events", [])),
                len(bridge_payload.get("kernel_flow_events", [])),
                len(bridge_payload.get("sidecar_events", [])),
            )

            if trace_enabled:
                print("[trace] event count:", len(self.trace_event_sink))
                print("[trace] first 5 events:", self.trace_event_sink[:5])
        except Exception as e:
            print(f"[step] failed: {e}")
            raise
        finally:
            if self.trace_viewer_win is not None and self.trace_viewer_win.winfo_exists():
                self._reload_trace_viewer()
            self.refresh()

# ********
# event dump
# ********
    def build_dump_rows_for_current_product(self, direction="OUT"):
        """
        現在選択中 product の planning tree から dump rows を作る。
        dump rows の本体ロジックは pysi.bridge.dump_rows 側へ委譲する。
        """
        product_name = (self.var_product.get() or "").strip()
        if not product_name:
            return []

        try:
            prod_tree_dict_OT = getattr(self.env, "prod_tree_dict_OT", {}) or {}
            prod_tree_dict_IN = getattr(self.env, "prod_tree_dict_IN", {}) or {}

            rows = build_dump_rows_from_product_plan_tree(
                product_name=product_name,
                direction=direction,
                prod_tree_dict_OT=prod_tree_dict_OT,
                prod_tree_dict_IN=prod_tree_dict_IN,
            )

            print(
                f"[trace] dump rows for product={product_name}, direction={direction}: {len(rows)}"
            )
            return rows

        except Exception as e:
            print(f"[trace] build_dump_rows_for_current_product skipped: {e}")
            return []


    def build_and_append_inferred_trace_for_current_product(self, direction="OUT"):
        """
        現在選択中 product の planning tree から dump rows を作り、
        canonical event 推定結果を self.trace_event_sink に append する。
        """
        rows = self.build_dump_rows_for_current_product(direction=direction)
        if not rows:
            return []

        added_trace_dicts = self.infer_and_append_trace_events_from_rows(rows)

        print(
            f"[trace] inferred canonical events for current product: {len(added_trace_dicts)}"
        )
        if added_trace_dicts:
            print("[trace] first 5 inferred events:", added_trace_dicts[:5])

        return added_trace_dicts





    def _get_filtered_trace_events(self):
        events = list(self.trace_event_sink or [])

        event_type = self.trace_filter_event_type.get().strip()
        node_id = self.trace_filter_node_id.get().strip()
        lot_id = self.trace_filter_lot_id.get().strip()
        time_bucket = self.trace_filter_time_bucket.get().strip()

        out = []
        for ev in events:
            if event_type and str(ev.get("event_type", "")) != event_type:
                continue
            if node_id and str(ev.get("node_id", "")) != node_id:
                continue

            ev_lot_id = str(ev.get("lot_id", "") or "")
            if lot_id and lot_id not in ev_lot_id:
                continue

            if time_bucket and str(ev.get("time_bucket", "")) != time_bucket:
                continue
            out.append(ev)
        return out

    def _format_trace_event_detail(self, ev):
        payload = ev.get("payload", {})
        try:
            if isinstance(payload, (dict, list)):
                payload_text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
            else:
                payload_text = str(payload)
        except Exception:
            payload_text = str(payload)

        try:
            raw_text = json.dumps(ev, ensure_ascii=False, indent=2, default=str)
        except Exception:
            raw_text = str(ev)

        lines = [
            f"sequence_no : {ev.get('sequence_no', '')}",
            f"event_type  : {ev.get('event_type', '')}",
            f"node_id     : {ev.get('node_id', '')}",
            f"lot_id      : {ev.get('lot_id', '')}",
            f"time_bucket : {ev.get('time_bucket', '')}",
            "",
            "[payload]",
            payload_text,
            "",
            "[raw event]",
            raw_text,
        ]
        return "\n".join(lines)

    def _show_trace_event_detail(self, ev):
        win = tk.Toplevel(self)
        win.title("Trace Event Detail")
        win.geometry("860x520")

        frm = ttk.Frame(win, padding=8)
        frm.pack(fill="both", expand=True)

        txt = tk.Text(frm, wrap="none")
        vsb = ttk.Scrollbar(frm, orient="vertical", command=txt.yview)
        hsb = ttk.Scrollbar(frm, orient="horizontal", command=txt.xview)
        txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        txt.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frm.rowconfigure(0, weight=1)
        frm.columnconfigure(0, weight=1)

        txt.insert("1.0", self._format_trace_event_detail(ev))
        txt.configure(state="disabled")

    def _on_trace_row_double_click(self, _event=None):
        if self.trace_tree is None:
            return
        sel = self.trace_tree.selection()
        if not sel:
            return
        iid = sel[0]
        ev = self.trace_row_event_map.get(iid)
        if ev is None:
            return
        self._show_trace_event_detail(ev)

    def follow_selected_lot(self):
        if self.trace_tree is None:
            return

        sel = self.trace_tree.selection()
        if not sel:
            messagebox.showinfo("Trace Viewer", "Please select one row first.")
            return

        iid = sel[0]
        ev = self.trace_row_event_map.get(iid)
        if ev is None:
            messagebox.showinfo("Trace Viewer", "Selected row has no event payload.")
            return

        lot_id = str(ev.get("lot_id", "") or "").strip()
        if not lot_id:
            messagebox.showinfo("Trace Viewer", "Selected row has no lot_id.")
            return

        self.trace_filter_lot_id.set(lot_id)
        self._reload_trace_viewer()

    def export_trace_csv(self):
        events = self._get_filtered_trace_events()
        if not events:
            messagebox.showinfo("Trace Viewer", "No trace events to export.")
            return

        product = (self.var_product.get() or "trace").strip() or "trace"
        path = filedialog.asksaveasfilename(
            title="Export Trace Events CSV",
            defaultextension=".csv",
            initialfile=f"trace_events_{product}.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            import csv

            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["sequence_no", "event_type", "node_id", "lot_id", "time_bucket", "payload"])
                for ev in events:
                    payload = ev.get("payload", {})
                    try:
                        if isinstance(payload, (dict, list)):
                            payload_text = json.dumps(payload, ensure_ascii=False, default=str)
                        else:
                            payload_text = str(payload)
                    except Exception:
                        payload_text = str(payload)

                    writer.writerow([
                        ev.get("sequence_no", ""),
                        ev.get("event_type", ""),
                        ev.get("node_id", ""),
                        ev.get("lot_id", ""),
                        ev.get("time_bucket", ""),
                        payload_text,
                    ])

            messagebox.showinfo("Trace Viewer", f"Exported {len(events)} events to:\n{path}")
        except Exception as e:
            messagebox.showerror("Trace Viewer", f"CSV export failed:\n{e}")

    def _reload_trace_viewer(self):
        if self.trace_tree is None:
            return

        tree = self.trace_tree
        self.trace_row_event_map = {}
        for iid in tree.get_children():
            tree.delete(iid)

        events = self._get_filtered_trace_events()
        self.trace_count_var.set(f"{len(events)} events")

        max_rows = 2000
        for ev in events[:max_rows]:
            payload = ev.get("payload", {})
            payload_text = str(payload) if isinstance(payload, dict) else str(payload)

            iid = tree.insert(
                "",
                "end",
                values=(
                    ev.get("sequence_no", ""),
                    ev.get("event_type", ""),
                    ev.get("node_id", ""),
                    ev.get("lot_id", ""),
                    ev.get("time_bucket", ""),
                    payload_text[:120],
                ),
            )
            self.trace_row_event_map[iid] = ev

        if len(events) > max_rows:
            tree.insert(
                "",
                "end",
                values=("", "...", "", "", "", f"(truncated: showing first {max_rows} rows)")
            )

    def clear_trace_filters(self):
        self.trace_filter_event_type.set("")
        self.trace_filter_node_id.set("")
        self.trace_filter_lot_id.set("")
        self.trace_filter_time_bucket.set("")
        self._reload_trace_viewer()

    def open_trace_viewer(self):
        if self.trace_viewer_win is not None and self.trace_viewer_win.winfo_exists():
            self.trace_viewer_win.lift()
            self._reload_trace_viewer()
            return

        win = tk.Toplevel(self)
        win.title("Trace Viewer")
        win.geometry("1100x520")
        self.trace_viewer_win = win

        frm_filter = ttk.Frame(win, padding=8)
        frm_filter.pack(fill="x")

        ttk.Label(frm_filter, text="event_type").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(frm_filter, textvariable=self.trace_filter_event_type, width=18).grid(row=1, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(frm_filter, text="node_id").grid(row=0, column=1, sticky="w", padx=4, pady=2)
        ttk.Entry(frm_filter, textvariable=self.trace_filter_node_id, width=18).grid(row=1, column=1, sticky="w", padx=4, pady=2)
        ttk.Label(frm_filter, text="lot_id").grid(row=0, column=2, sticky="w", padx=4, pady=2)
        ttk.Entry(frm_filter, textvariable=self.trace_filter_lot_id, width=24).grid(row=1, column=2, sticky="w", padx=4, pady=2)
        ttk.Label(frm_filter, text="time_bucket").grid(row=0, column=3, sticky="w", padx=4, pady=2)
        ttk.Entry(frm_filter, textvariable=self.trace_filter_time_bucket, width=12).grid(row=1, column=3, sticky="w", padx=4, pady=2)
        ttk.Button(frm_filter, text="Apply Filter", command=self._reload_trace_viewer).grid(row=1, column=4, sticky="w", padx=8, pady=2)
        ttk.Button(frm_filter, text="Clear", command=self.clear_trace_filters).grid(row=1, column=5, sticky="w", padx=4, pady=2)
        ttk.Button(frm_filter, text="Reload", command=self._reload_trace_viewer).grid(row=1, column=6, sticky="w", padx=4, pady=2)
        ttk.Button(frm_filter, text="Follow Lot", command=self.follow_selected_lot).grid(row=1, column=7, sticky="w", padx=8, pady=2)
        ttk.Button(frm_filter, text="Export CSV", command=self.export_trace_csv).grid(row=1, column=8, sticky="w", padx=8, pady=2)
        ttk.Label(frm_filter, textvariable=self.trace_count_var).grid(row=1, column=9, sticky="e", padx=12, pady=2)

        frm_table = ttk.Frame(win, padding=(8, 0, 8, 8))
        frm_table.pack(fill="both", expand=True)

        cols = ("sequence_no", "event_type", "node_id", "lot_id", "time_bucket", "payload")
        tree = ttk.Treeview(frm_table, columns=cols, show="headings")
        self.trace_tree = tree

        for c in cols:
            tree.heading(c, text=c)

        tree.column("sequence_no", width=90, anchor="e")
        tree.column("event_type", width=180, anchor="w")
        tree.column("node_id", width=120, anchor="w")
        tree.column("lot_id", width=260, anchor="w")
        tree.column("time_bucket", width=90, anchor="center")
        tree.column("payload", width=320, anchor="w")
        tree.bind("<Double-1>", self._on_trace_row_double_click)

        vsb = ttk.Scrollbar(frm_table, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frm_table, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frm_table.rowconfigure(0, weight=1)
        frm_table.columnconfigure(0, weight=1)

        self._reload_trace_viewer()


    def use_current_filter_for_animation(self):
        self.anim_lot_id_var.set(self.trace_filter_lot_id.get().strip())

    def _animation_sort_key(self, ev):
        tb = str(ev.get("time_bucket", "") or "")
        seq = ev.get("sequence_no", 0)
        try:
            tb_key = int(tb)
        except Exception:
            tb_key = tb
        try:
            seq_key = int(seq)
        except Exception:
            seq_key = 0
        return (tb_key, seq_key)

    def _build_lot_animation_frames(self, selected_lot_id: str):
        selected_lot_id = (selected_lot_id or "").strip()
        if not selected_lot_id:
            return []

        events = list(self.trace_event_sink or [])
        frames = []
        for ev in events:
            ev_lot_id = str(ev.get("lot_id", "") or "")
            if selected_lot_id not in ev_lot_id:
                continue
            node_id = str(ev.get("node_id", "") or "").strip()
            time_bucket = str(ev.get("time_bucket", "") or "").strip()
            if not node_id or not time_bucket:
                continue
            frames.append({
                "sequence_no": ev.get("sequence_no", ""),
                "event_type": ev.get("event_type", ""),
                "node_id": node_id,
                "lot_id": ev_lot_id,
                "time_bucket": time_bucket,
                "payload": ev.get("payload", {}),
            })

        frames.sort(key=self._animation_sort_key)
        return frames

    def _get_animation_node_positions(self, frames):
        known_positions = {
            "supply_point": (90, 180),
            "DADCAL": (240, 180),
            "WS1CAL": (390, 100),
            "WS2CAL": (390, 260),
            "RT_CAL": (540, 180),
            "CS_CAL": (690, 180),
        }
        node_ids = []
        for fr in frames:
            nid = fr.get("node_id")
            if nid and nid not in node_ids:
                node_ids.append(nid)

        positions = {}
        for nid in node_ids:
            if nid in known_positions:
                positions[nid] = known_positions[nid]

        unknown = [nid for nid in node_ids if nid not in positions]
        for i, nid in enumerate(unknown):
            col = i % 4
            row = i // 4
            positions[nid] = (120 + col * 170, 360 + row * 90)

        return positions

    def _draw_animation_frame(self):
        if self.anim_canvas is None:
            return

        canvas = self.anim_canvas
        canvas.delete("all")

        w = max(canvas.winfo_width(), 760)
        h = max(canvas.winfo_height(), 420)
        canvas.create_rectangle(0, 0, w, h, fill="white", outline="")

        if not self.anim_frames:
            canvas.create_text(
                w // 2,
                h // 2,
                text="No animation frames. Follow Lot or load a lot_id first.",
                font=("Segoe UI", 12),
            )
            self.anim_status_var.set("No lot loaded")
            return

        frame = self.anim_frames[self.anim_index]
        positions = self._get_animation_node_positions(self.anim_frames)

        default_edges = [
            ("supply_point", "DADCAL"),
            ("DADCAL", "WS1CAL"),
            ("DADCAL", "WS2CAL"),
            ("WS1CAL", "RT_CAL"),
            ("WS2CAL", "RT_CAL"),
            ("RT_CAL", "CS_CAL"),
        ]
        for a, b in default_edges:
            if a in positions and b in positions:
                x1, y1 = positions[a]
                x2, y2 = positions[b]
                canvas.create_line(x1, y1, x2, y2, fill="#B0B7C3", width=2)

        current_node = frame.get("node_id", "")
        lot_id = frame.get("lot_id", "")
        time_bucket = frame.get("time_bucket", "")
        event_type = frame.get("event_type", "")

        for nid, (x, y) in positions.items():
            is_current = (nid == current_node)
            r = 24 if is_current else 18
            fill = "#FFD966" if is_current else "#F7F9FC"
            width = 3 if is_current else 1
            outline = "#C27C0E" if is_current else "#607080"
            canvas.create_oval(x - r, y - r, x + r, y + r, fill=fill, outline=outline, width=width)
            canvas.create_text(x, y + 34, text=nid, font=("Segoe UI", 9))

        title = f"Lot: {lot_id}    Week: {time_bucket}    Node: {current_node}    Event: {event_type}"
        canvas.create_text(18, 18, text=title, anchor="w", font=("Segoe UI", 11, "bold"))
        canvas.create_text(
            18,
            42,
            text=f"Frame {self.anim_index + 1} / {len(self.anim_frames)}",
            anchor="w",
            font=("Segoe UI", 10),
        )

        self.anim_status_var.set(
            f"Lot={lot_id} | Week={time_bucket} | Node={current_node} | Frame {self.anim_index + 1}/{len(self.anim_frames)}"
        )

    def _load_animation_frames(self):
        lot_id = self.anim_lot_id_var.get().strip()
        self.pause_animation()
        self.anim_frames = self._build_lot_animation_frames(lot_id)
        self.anim_index = 0
        self._draw_animation_frame()
        if not self.anim_frames:
            messagebox.showinfo("Animation Viewer", "No frames found for the selected lot_id.")

    def _animation_tick(self):
        if not self.anim_playing:
            return
        if not self.anim_frames:
            self.anim_playing = False
            return
        if self.anim_index < len(self.anim_frames) - 1:
            self.anim_index += 1
            self._draw_animation_frame()
            if self.anim_viewer_win is not None and self.anim_viewer_win.winfo_exists():
                self.anim_after_id = self.anim_viewer_win.after(self.anim_interval_ms, self._animation_tick)
        else:
            self.anim_playing = False
            self.anim_after_id = None

    def play_animation(self):
        if not self.anim_frames:
            self._load_animation_frames()
        if not self.anim_frames:
            return
        if self.anim_playing:
            return
        self.anim_playing = True
        self.anim_after_id = None
        if self.anim_viewer_win is not None and self.anim_viewer_win.winfo_exists():
            self.anim_after_id = self.anim_viewer_win.after(self.anim_interval_ms, self._animation_tick)

    def pause_animation(self):
        self.anim_playing = False
        if self.anim_after_id and self.anim_viewer_win is not None and self.anim_viewer_win.winfo_exists():
            try:
                self.anim_viewer_win.after_cancel(self.anim_after_id)
            except Exception:
                pass
        self.anim_after_id = None

    def next_animation_frame(self):
        self.pause_animation()
        if not self.anim_frames:
            return
        if self.anim_index < len(self.anim_frames) - 1:
            self.anim_index += 1
        self._draw_animation_frame()

    def prev_animation_frame(self):
        self.pause_animation()
        if not self.anim_frames:
            return
        if self.anim_index > 0:
            self.anim_index -= 1
        self._draw_animation_frame()

    def _close_animation_viewer(self):
        self.pause_animation()
        if self.anim_viewer_win is not None and self.anim_viewer_win.winfo_exists():
            self.anim_viewer_win.destroy()
        self.anim_viewer_win = None
        self.anim_canvas = None

    def open_animation_viewer(self):
        if self.anim_viewer_win is not None and self.anim_viewer_win.winfo_exists():
            self.anim_viewer_win.lift()
            self._draw_animation_frame()
            return

        win = tk.Toplevel(self)
        win.title("Animation Viewer")
        win.geometry("920x560")
        self.anim_viewer_win = win
        win.protocol("WM_DELETE_WINDOW", self._close_animation_viewer)

        frm_ctrl = ttk.Frame(win, padding=8)
        frm_ctrl.pack(fill="x")

        ttk.Label(frm_ctrl, text="lot_id").pack(side="left")
        ttk.Entry(frm_ctrl, textvariable=self.anim_lot_id_var, width=36).pack(side="left", padx=6)
        ttk.Button(frm_ctrl, text="Use Current Filter", command=self.use_current_filter_for_animation).pack(side="left", padx=4)
        ttk.Button(frm_ctrl, text="Load", command=self._load_animation_frames).pack(side="left", padx=4)
        ttk.Button(frm_ctrl, text="Play", command=self.play_animation).pack(side="left", padx=4)
        ttk.Button(frm_ctrl, text="Pause", command=self.pause_animation).pack(side="left", padx=4)
        ttk.Button(frm_ctrl, text="Prev", command=self.prev_animation_frame).pack(side="left", padx=4)
        ttk.Button(frm_ctrl, text="Next", command=self.next_animation_frame).pack(side="left", padx=4)

        ttk.Label(frm_ctrl, textvariable=self.anim_status_var).pack(side="right", padx=8)

        frm_canvas = ttk.Frame(win, padding=(8, 0, 8, 8))
        frm_canvas.pack(fill="both", expand=True)

        canvas = tk.Canvas(frm_canvas, background="white")
        canvas.pack(fill="both", expand=True)
        self.anim_canvas = canvas
        canvas.bind("<Configure>", lambda _e: self._draw_animation_frame())

        if self.trace_filter_lot_id.get().strip() and not self.anim_lot_id_var.get().strip():
            self.anim_lot_id_var.set(self.trace_filter_lot_id.get().strip())

        self._draw_animation_frame()

    def open_business_animation(self):
        """
        Open Business Performance Animation viewer in a separate Toplevel.

        Placement policy:
        - Keep this next to open_animation_viewer() because both are viewer windows.
        - Reuse current cockpit selection (product / direction / selected node).
        - If already open, just lift/focus and refresh the context.
        """
        if BusinessAnimationPanel is None:
            messagebox.showerror(
                "Business Animation",
                "business_animation module could not be imported.\n"
                "Please check pysi/gui/business_animation/ placement."
            )
            return

        # already opened -> focus + refresh context
        if self.business_animation_window is not None:
            try:
                if self.business_animation_window.winfo_exists():
                    try:
                        ctx = self.build_business_animation_context()
                        if ctx is not None and self.business_animation_panel is not None:
                            self.business_animation_panel.set_context(ctx)
                    except Exception as e:
                        print(f"[business_animation] refresh-on-open skipped: {e}")

                    self.business_animation_window.deiconify()
                    self.business_animation_window.lift()
                    self.business_animation_window.focus_force()
                    return
            except Exception:
                self.business_animation_window = None
                self.business_animation_panel = None

        # create new window
        win = tk.Toplevel(self)
        win.title("WOM Business Performance Animation v0.1")
        win.geometry("1280x720")
        self.business_animation_window = win

        panel = BusinessAnimationPanel(win)
        panel.pack(fill="both", expand=True)
        self.business_animation_panel = panel

        # initial context push
        try:
            ctx = self.build_business_animation_context()
            if ctx is not None:
                panel.set_context(ctx)
        except Exception as e:
            print(f"[business_animation] initial context push failed: {e}")

        def _on_close():
            try:
                if self.business_animation_panel is not None:
                    try:
                        if hasattr(self.business_animation_panel, "controller") and self.business_animation_panel.controller is not None:
                            self.business_animation_panel.controller.pause()
                    except Exception:
                        pass
            finally:
                self.business_animation_panel = None
                self.business_animation_window = None
                win.destroy()

        win.protocol("WM_DELETE_WINDOW", _on_close)

        #@ADD for animation
        
    def _get_selected_node_id_for_psi_profit_animation(self):
        """
        Resolve selected node id for PSI/profit animation.
        Priority:
        1. state.selected_node
        2. explicit attrs if already maintained
        3. selected/current node object
        4. var_mom fallback
        """
        try:
            selected = getattr(self.state, "selected_node", None)
            if selected:
                return str(selected)
        except Exception:
            pass

        for attr_name in ["selected_node_id", "current_node_id", "node_id_selected"]:
            try:
                value = getattr(self, attr_name, None)
                if value:
                    return str(value)
            except Exception:
                pass

        for attr_name in ["selected_node_obj", "current_node"]:
            try:
                obj = getattr(self, attr_name, None)
                if obj is None:
                    continue
                if isinstance(obj, dict):
                    value = obj.get("node_id") or obj.get("name")
                else:
                    value = getattr(obj, "node_id", None) or getattr(obj, "name", None)
                if value:
                    return str(value)
            except Exception:
                pass

        try:
            mom = self.var_mom.get().strip()
            if mom:
                return mom
        except Exception:
            pass

        return None

    def _get_selected_product_id_for_psi_profit_animation(self):
        """
        Resolve selected product id for PSI/profit animation.
        Priority:
        1. state.selected_product
        2. explicit attrs
        3. var_product
        4. env.product_selected
        """
        try:
            selected = getattr(self.state, "selected_product", None)
            if selected:
                return str(selected)
        except Exception:
            pass

        for attr_name in ["selected_product_id", "current_product_id", "product_id_selected"]:
            try:
                value = getattr(self, attr_name, None)
                if value:
                    return str(value)
            except Exception:
                pass

        try:
            product = self.var_product.get().strip()
            if product:
                return product
        except Exception:
            pass

        try:
            env_product = getattr(self.env, "product_selected", None)
            if env_product:
                return str(env_product)
        except Exception:
            pass

        return None

    def build_psi_profit_animation_provider(self):
        """
        Build data provider for PSI accumulated + profit ratio window.
        Adapter side absorbs WOM internal data structure differences.
        """
        node_id = self._get_selected_node_id_for_psi_profit_animation()
        product_id = self._get_selected_product_id_for_psi_profit_animation()

        provider = build_provider_from_cockpit_context(
            cockpit=self,
            node_id=node_id,
            product_id=product_id,
        )
        return provider, node_id, product_id

    def open_psi_profit_animation(self):
        """
        Open PSI accumulated + profit ratio animation in a dedicated Toplevel.
        Reuses current cockpit selection and KPI/PSI context.
        """
        if self.psi_profit_anim_win is not None:
            try:
                if self.psi_profit_anim_win.winfo_exists():
                    self.psi_profit_anim_win.deiconify()
                    self.psi_profit_anim_win.lift()
                    self.psi_profit_anim_win.focus_force()
                    return
            except Exception:
                self.psi_profit_anim_win = None

        provider, node_id, product_id = self.build_psi_profit_animation_provider()

        try:
            win = open_psi_profit_animation_window(
                master=self,
                title="WOM PSI Accumulated + Profit Ratio",
                data_provider=provider,
                node_id=node_id,
                product_id=product_id,
                interval_ms=1000,   # 1 week = 1 sec
            )
            self.psi_profit_anim_win = win

            def _on_close():
                try:
                    self.psi_profit_anim_win = None
                    win.destroy()
                except Exception:
                    self.psi_profit_anim_win = None

            win.protocol("WM_DELETE_WINDOW", _on_close)

        except Exception as e:
            try:
                messagebox.showerror(
                    "PSI累計+利益率",
                    f"Failed to open PSI/profit animation window.\n\n{e}",
                )
            except Exception:
                print(f"[psi_profit_animation] open failed: {e}")



    # ------------------------------------------------------------
    # Management cockpit
    # ------------------------------------------------------------
    def _capture_initial_management_snapshot(self):
        """
        初回表示後の現状態を baseline 候補として保持する。
        """
        try:
            snap = self._build_management_snapshot()
            if snap is not None:
                self._last_management_snapshot = snap
                self.management_cockpit_status_var.set(
                    f"Management cockpit: baseline ready ({getattr(snap, 'scenario_id', '-')})"
                )
        except Exception as e:
            print("[management_cockpit] initial snapshot skipped:", e)

    def _build_management_snapshot_OLD(self):
        """
        現在の env / product から StateSnapshot を構築する。
        """
        if build_snapshot_from_v0r8 is None or SnapshotBuildContext is None:
            return None

        product_id = None
        try:
            product_id = self.var_product.get().strip() if self.var_product.get() else None
        except Exception:
            product_id = getattr(self.env, "product_selected", None)

        try:
            time_bucket = str(getattr(self.env, "current_time_bucket", "202601"))
        except Exception:
            time_bucket = "202601"

        snap = build_snapshot_from_v0r8(
            env_or_root=self.env,
            time_bucket=time_bucket,
            ctx=SnapshotBuildContext(product_id=product_id),
        )

        try:
            if not getattr(snap, "scenario_name", ""):
                snap.scenario_name = str(getattr(self, "current_mode", "cockpit"))
        except Exception:
            pass

        return snap

    def _build_management_snapshot(self):
        if build_snapshot_from_v0r8 is None or SnapshotBuildContext is None:
            return None

        product_id = None
        try:
            product_id = self.var_product.get().strip() if self.var_product.get() else None
        except Exception:
            product_id = getattr(self.env, "product_selected", None)

        try:
            time_bucket = str(getattr(self.env, "current_time_bucket", "202601"))
        except Exception:
            time_bucket = "202601"

        planning_snapshot = build_snapshot_from_v0r8(
            env_or_root=self.env,
            time_bucket=time_bucket,
            ctx=SnapshotBuildContext(product_id=product_id),
        )

        if planning_snapshot is None:
            return None

        if adapt_planning_snapshot_to_state_snapshot is None:
            return planning_snapshot

        scenario_id = str(getattr(self, "current_mode", "cockpit"))
        snapshot_id = f"{scenario_id}::{product_id or 'UNKNOWN'}::{time_bucket}"

        return adapt_planning_snapshot_to_state_snapshot(
            planning_snapshot,
            snapshot_id=snapshot_id,
            scenario_id=scenario_id,
            scenario_name=scenario_id,
            env=self.env,
        )



    def _ensure_management_cockpit_window(self):
        """
        Toplevel 上に management cockpit panel を生成する。
        """
        if not _WOM_MANAGEMENT_COCKPIT_AVAILABLE:
            messagebox.showwarning(
                "Management Cockpit",
                "wom_cockpit modules are not available.\nPlease place wom_cockpit package into repo first.",
            )
            return None

        if self.management_cockpit_win is not None:
            try:
                if self.management_cockpit_win.winfo_exists():
                    return self.management_cockpit_win
            except Exception:
                pass

        win = tk.Toplevel(self)
        win.title("WOM Management Cockpit")
        win.geometry("1400x900")

        top = ttk.Frame(win)
        top.pack(fill="x", padx=6, pady=6)

        ttk.Label(
            top,
            textvariable=self.management_cockpit_status_var,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        ttk.Button(
            top,
            text="Refresh from current state",
            command=lambda: self.refresh_management_cockpit(
                baseline_snapshot=self._last_management_snapshot,
                scenario_snapshot=self._build_management_snapshot(),
            ),
        ).pack(side="right")

        body = ttk.Frame(win)
        body.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        self.management_cockpit_panel = CockpitPanelAdapter(body)
        self.management_cockpit_panel.build()

        self.management_cockpit_win = win
        return win

    def open_management_cockpit(self):
        """
        Management cockpit window を開く。
        初回は baseline=current state で描画を試みる。
        """
        win = self._ensure_management_cockpit_window()
        if win is None:
            return

        try:
            current = self._build_management_snapshot()

            #@STOP
            #baseline = self._last_management_snapshot or current

            baseline = self._last_management_snapshot

            if baseline is None:
                baseline = current
                self._last_management_snapshot = baseline


            self.refresh_management_cockpit(
                baseline_snapshot=baseline,
                scenario_snapshot=current,
            )
            win.lift()
        except Exception as e:
            print("[management_cockpit] open skipped:", e)

    def refresh_management_cockpit_OLD(self, baseline_snapshot=None, scenario_snapshot=None):
        """
        baseline/scenario snapshot から management cockpit を更新する。
        """
        if not _WOM_MANAGEMENT_COCKPIT_AVAILABLE:
            return

        if baseline_snapshot is None and scenario_snapshot is None:
            return

        if scenario_snapshot is None:
            scenario_snapshot = self._build_management_snapshot()
        if baseline_snapshot is None:
            baseline_snapshot = self._last_management_snapshot or scenario_snapshot

        if baseline_snapshot is None or scenario_snapshot is None:
            return

        self._ensure_management_cockpit_window()
        if self.management_cockpit_panel is None:
            return

        plan_delta = compare_snapshots(baseline_snapshot, scenario_snapshot)
        facts = extract_management_facts(plan_delta)
        issues = generate_issues(facts, group_similar_facts=False)
        vm = build_cockpit_view_model(plan_delta, issues)

        self.management_cockpit_panel.render(vm)
        self.management_cockpit_status_var.set(
            f"Management cockpit: {baseline_snapshot.scenario_id} -> {scenario_snapshot.scenario_id} / issues={len(issues)}"
        )

        # baseline は自動追随させない
        #self._last_management_snapshot = scenario_snapshot

    @staticmethod
    def _is_management_demo_scenario(scenario_name: str) -> bool:
        if not scenario_name:
            return False
        name = scenario_name.lower()
        return any(
            token in name
            for token in ("demo", "sample", "demand_surge", "demand_down", "port_stop")
        )

    @staticmethod
    #@STOP
    #def _extract_management_analyzer_input(snapshot, plan_delta) -> dict[str, float]:
    def _extract_management_analyzer_input(snapshot, plan_delta, side: str = "after") -> dict[str, float]:

        summary = getattr(plan_delta, "summary_delta", None)
        if summary is not None:
            return {
                "revenue": float(getattr(getattr(summary, "total_revenue", None), side, 0.0) or 0.0),
                "profit": float(getattr(getattr(summary, "total_profit", None), side, 0.0) or 0.0),
                "profit_ratio": float(getattr(getattr(summary, "profit_ratio", None), side, 0.0) or 0.0),
                "inventory": float(getattr(getattr(summary, "total_inventory_qty", None), side, 0.0) or 0.0),
                "shortage": float(getattr(getattr(summary, "total_lost_sales_qty", None), side, 0.0) or 0.0),
                "backlog": float(getattr(getattr(summary, "total_backlog_qty", None), side, 0.0) or 0.0),
            }

        kpi = getattr(snapshot, "kpi_summary", None)
        if kpi is None:
            return {
                "revenue": 0.0,
                "profit": 0.0,
                "profit_ratio": 0.0,
                "inventory": 0.0,
                "shortage": 0.0,
                "backlog": 0.0,
            }
        return {
            "revenue": float(getattr(kpi, "total_revenue", 0.0) or 0.0),
            "profit": float(getattr(kpi, "total_profit", 0.0) or 0.0),
            "profit_ratio": float(getattr(kpi, "profit_ratio", 0.0) or 0.0),
            "inventory": float(getattr(kpi, "total_inventory_qty", 0.0) or 0.0),
            "shortage": float(getattr(kpi, "total_lost_sales_qty", 0.0) or 0.0),
            "backlog": float(getattr(kpi, "total_backlog_qty", 0.0) or 0.0),
        }

    def _apply_management_analyzer(self, vm, baseline_snapshot, scenario_snapshot, plan_delta):
        if analyze_management_delta is None or Issue is None or RiskViewModel is None:
            return vm

        priority_map = {"High": 10, "Medium": 50, "Low": 90}
        severity_map = {"Critical": "critical", "Warning": "high", "Info": "low"}
        issue_type_map = {"Opportunity": "opportunity"}

        baseline_input = self._extract_management_analyzer_input(baseline_snapshot, plan_delta, side="before")
        scenario_input = self._extract_management_analyzer_input(scenario_snapshot, plan_delta, side="after")
        scenario_name = str(
            getattr(scenario_snapshot, "scenario_name", None)
            or getattr(scenario_snapshot, "scenario_id", None)
            or "Scenario"
        )
        demo_mode = self._is_management_demo_scenario(scenario_name)

        result = analyze_management_delta(
            baseline_input,
            scenario_input,
            scenario_name=scenario_name,
            demo_mode=demo_mode,
        )

        mapped_issues = []
        issue_id_by_title = {}
        for idx, src in enumerate(result.issues, start=1):
            issue_id = f"mgmt_analyzer::{idx}"
            mapped_issues.append(
                Issue(
                    issue_id=issue_id,
                    issue_type=issue_type_map.get(src.category, "risk"),
                    category=src.category,
                    title=src.title,
                    summary=src.reason,
                    severity=severity_map.get(src.severity, "medium"),
                    priority=priority_map.get(src.priority, 50),
                    why_it_matters=src.reason,
                    management_question=f"{src.related_kpi} をどのように改善するか？",
                    recommendation_summary=src.suggested_action,
                    recommended_actions=[
                        RecommendedAction(
                            action_id=f"mgmt_action::{idx}",
                            action_type="management_action",
                            title=src.suggested_action,
                            description=src.suggested_action,
                        )
                    ],
                    owner_hint=src.owner,
                    tags=[src.related_kpi],
                    attributes={
                        "baseline_value": src.baseline_value,
                        "scenario_value": src.scenario_value,
                        "delta_value": src.delta_value,
                    },
                )
            )
            issue_id_by_title.setdefault(src.title, issue_id)

        vm.issues = mapped_issues
        vm.top_risks = [
            RiskViewModel(
                risk_id=issue_id_by_title.get(risk.risk_name, f"mgmt_analyzer::risk::{risk.rank}"),
                title=risk.risk_name,
                category="Management",
                severity=severity_map.get(risk.severity, "medium"),
                priority=risk.rank,
                summary=risk.description,
            )
            for risk in result.risks
        ]
        if result.narrative:
            vm.metadata["narrative_override"] = result.narrative
        vm.metadata["management_analyzer_input"] = {
            "baseline": baseline_input,
            "scenario": scenario_input,
            "scenario_name": scenario_name,
            "demo_mode": demo_mode,
        }
        vm.metadata["issue_count"] = len(mapped_issues)
        vm.metadata["issue_count_analyzer"] = len(mapped_issues)
        return vm

    def refresh_management_cockpit(self, baseline_snapshot=None, scenario_snapshot=None):
        if not _WOM_MANAGEMENT_COCKPIT_AVAILABLE:
            return

        self.management_cockpit_status_var.set("Management cockpit: refreshing...")
        self.update_idletasks()

        if baseline_snapshot is None and scenario_snapshot is None:
            return

        if scenario_snapshot is None:
            scenario_snapshot = self._build_management_snapshot()
        if baseline_snapshot is None:
            baseline_snapshot = self._last_management_snapshot or scenario_snapshot

        if baseline_snapshot is None or scenario_snapshot is None:
            return

        self._ensure_management_cockpit_window()
        if self.management_cockpit_panel is None:
            return

        plan_delta = compare_snapshots(baseline_snapshot, scenario_snapshot)
        facts = extract_management_facts(plan_delta)
        issues = generate_issues(facts, group_similar_facts=False)
        vm = build_cockpit_view_model(plan_delta, issues)
        try:
            vm = self._apply_management_analyzer(vm, baseline_snapshot, scenario_snapshot, plan_delta)
        except Exception as e:
            print("[management_issue_analyzer] apply skipped:", e)

        self.management_cockpit_panel.render(vm)

        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self.management_cockpit_status_var.set(
            f"Management cockpit: {baseline_snapshot.scenario_id} -> {scenario_snapshot.scenario_id} / issues={len(issues)} / refreshed {ts}"
        )


    def refresh(self):
        prod = self.var_product.get()
        node_name_from_ui = self.var_node.get().strip() if hasattr(self, "var_node") and self.var_node.get() else ""

        # roots by product
        root_ot = (getattr(self.env, "prod_tree_dict_OT", {}) or {}).get(prod, None)
        if root_ot is None and hasattr(self.env, "root_node_outbound_byprod"):
            root_ot = self.env.root_node_outbound_byprod

        if root_ot is None:
            return

        # PSIグラフの対象ノードは「選択ノード」を優先
        selected_node = getattr(self.state, "selected_node", None)
        node_for_plot = selected_node or node_name_from_ui

        # update eval profit
        if hasattr(self.env, "update_evaluation_results4multi_product"):
            try:
                self.env.update_evaluation_results4multi_product()
            except Exception:
                pass

        total_profit = float(getattr(self.env, "total_profit", 0) or 0)
        total_revenue = float(getattr(self.env, "total_revenue", 0) or 0)
        profit_ratio = (total_profit / total_revenue) if total_revenue else 0.0

        # Service
        svc = compute_service_jit_for_product(root_ot)
        jit_mad = svc["jit_mad_weeks"]
        unfilled = svc["unfilled_lots"]

        # Inventory
        inv_last, inv_avg = compute_total_inventory_lots(root_ot)

        # Utilization (series mean)
        used, util = compute_utilization_series(self.env, prod, node_for_plot, root_ot)
        util_mean = float(util.mean()) if util is not None and len(util) else 0.0

        # Cashflow DF (cache per refresh)
        output_period = 53 * int(getattr(root_ot, "plan_range", 1))
        self.df_cash = build_cashflow_df_outbound(root_ot, output_period=output_period)
        self.df_animation_kpi = build_animation_kpi_df_from_cashflow(self.df_cash)

        # Cash KPIs: total + selected node
        cash_total = cashflow_kpis_from_df(self.df_cash, node_name=None)
        cash_node = cashflow_kpis_from_df(self.df_cash, node_name=node_for_plot) if node_for_plot else {"net_cash_min": 0, "cum_net_cash_min": 0}

        # KPI labels
        self.kpi_labels["Profit"].configure(text=f"Profit: {total_profit:,.0f}   (Rev {total_revenue:,.0f}, Margin {profit_ratio*100:.1f}%)")
        self.kpi_labels["Service(JIT MAD)"].configure(text=f"Service(JIT): MAD {jit_mad:.2f}w / Unfilled {unfilled}")
        self.kpi_labels["CCC(placeholder)"].configure(text="CCC: (hook later)  ※暫定")
        self.kpi_labels["Utilization"].configure(text=f"Utilization({node_for_plot}): {util_mean*100:.1f}%")
        self.kpi_labels["Inventory(last/avg)"].configure(text=f"Inventory: last {inv_last:,} lots / avg {inv_avg:,.1f} lots")
        self.kpi_labels["NetCash(min/cum_min)"].configure(
            text=f"NetCash Total: min {cash_total['net_cash_min']:,.0f}, cum_min {cash_total['cum_net_cash_min']:,.0f}  |  "
                 f"{node_for_plot}: min {cash_node['net_cash_min']:,.0f}, cum_min {cash_node['cum_net_cash_min']:,.0f}"
        )

        # plots
        plot_mom_psi_cap(
            self.frame_psi_plot,
            self.env,
            prod,
            node_for_plot,
            root_ot,
            step_type=self.var_step_type.get(),
            direction=self.var_direction.get(),
            debug=True,
        )

        plot_service(self.frame_service, self.env, prod, root_ot)

        mode = self.var_cash_mode.get()
        if mode == "TOTAL":
            plot_cashflow(self.frame_cash_total, self.df_cash, title=f"Cashflow TOTAL (Outbound sum) : {prod}", node_name=None)
        else:
            plot_cashflow(
                self.frame_cash_total,
                self.df_cash,
                title=f"Cashflow Selected Node : {prod} / {node_for_plot}",
                node_name=node_for_plot if node_for_plot else None,
            )

        try:
            if self.business_animation_panel is not None:
                ctx = self.build_business_animation_context()
                if ctx is not None:
                    self.business_animation_panel.set_context(ctx)
        except Exception:
            pass

    #@STOP
    #def open_network(self):
    #    prod = self.var_product.get() if self.var_product.get() else None
    #    if not prod:
    #        return
    #    show_network_E2E_matplotlib(
    #        self.env,
    #        product_name=prod,
    #        on_select=self.set_selected_node,   # ←ここがCの心臓
    #    )


    def open_network(self):
        prod = self.var_product.get() if self.var_product.get() else None
        if not prod:
            return
        
        #@STOP
        #from pysi.gui.network_viewer_patched import show_network_E2E_matplotlib

        self._network_viewer = show_network_E2E_matplotlib(
            self.env,
            product_name=prod,
            on_select=self.set_selected_node,
        )

    #@STOP
    #def set_selected_node(self, node_name: str, source: str = ""):
    #    """Update selection state and refresh dependent views.
    #    node_name is the common key across map/network/PSI.
    #    """
    #    self.selected_node_id = node_name
    #    self.state.selected_node = node_name
    #    self.state.selected_product = self.var_product.get() if self.var_product.get() else None
    #
    #    try:
    #        if node_name and hasattr(self, "var_node") and self.var_node.get() != node_name:
    #            self.var_node.set(node_name)
    #    except Exception:
    #        pass

    #@UPDATE wrapping with "_apply()"
    def set_selected_node(self, node_name: str, source: str = ""):
        def _apply():

            self.state.selected_node = node_name

            #@ADD for "node_name" linking
            try:
                self.var_node.set(node_name)
            except Exception:
                pass


            self.state.selected_product = self.var_product.get() if self.var_product.get() else None

            try:
                self.render_l1_psi_mini()
            except Exception:
                pass

            if hasattr(self, "_network_viewer") and self._network_viewer:
                try:
                    self._network_viewer.set_selected_node(node_name)
                except Exception:
                    pass

            if hasattr(self, "_world_map_view") and self._world_map_view:
                try:
                    self._world_map_view.set_selected_node(node_name)
                except Exception:
                    pass

            try:
                self.refresh()
            except Exception:
                pass

        if threading.current_thread() is threading.main_thread():
            _apply()
        else:
            self.after(0, _apply)







# ...既存処理...
        if hasattr(self, "_network_viewer") and self._network_viewer:
            try:
                self._network_viewer.set_selected_node(node_name)
            except Exception:
                pass


        # ---- A: Network Viewer にも同期（ここを追加） ----
        viewer = getattr(self, "_network_viewer", None)
        if viewer is not None:
            try:
                viewer.set_selected_node(node_name)
            except Exception:
                pass

        # （Cで使う）WorldMapにも同期したいので、ハンドルがあれば反映
        wmv = getattr(self, "_world_map_view", None)
        if wmv is not None:
            try:
                wmv.set_selected_node(node_name)  # ← Cで world_map_view に追加する
            except Exception:
                pass

        try:
            if getattr(self, "business_animation_panel", None) is not None:
                self.business_animation_panel.update_selection(node_name)
        except Exception:
            pass
        # -----------------------------------------------

        self.render_l1_psi_mini()
        self.refresh()

def launch_cockpit(env, rerun_fn=None):
    app = WOMCockpit(env, rerun_fn=rerun_fn)
    app.mainloop()
