"""
WOM GUI – main application window.

Layout
------
┌────────────────────────────────────────────────────────────────┐
│  WOM – Weekly Operation Model                          v1r0m0  │
├──────────────┬─────────────────────────────────────────────────┤
│  Left panel  │  Right panel (notebook tabs)                    │
│  ─────────── │  ┌──────────────────────────────────────────┐  │
│  • Config    │  │ Charts  │ KPI Table │ At-Risk │ Scenario Δ│  │
│  • Files     │  └──────────────────────────────────────────┘  │
│  • [Run]     │                                                  │
│  • [Export]  │                                                  │
└──────────────┴─────────────────────────────────────────────────┘
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import pandas as pd

# Matplotlib embedded in Tkinter
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from wom.config import WOMConfig, ScenarioSpec
from wom.data.loader import WOMInputs
from wom.data.schema import Cols
from wom.engine.simulator import WOMSimulator
from wom.engine.scenario import ScenarioManager
from wom.reports.output import write_csv, write_excel
from wom.engine.management import ManagementAnalysisResult

# NetworkX – optional (graceful fallback if not installed)
try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False


# ──────────────────────────────────────────────────────────────────────
# Colour palette
# ──────────────────────────────────────────────────────────────────────
COLOURS = {
    "Base":      "#2196F3",
    "Upside":    "#4CAF50",
    "Downside":  "#F44336",
}
DEFAULT_COLOURS = ["#2196F3", "#4CAF50", "#F44336", "#FF9800", "#9C27B0"]

BG_DARK  = "#1E2A38"
BG_MID   = "#253347"
BG_LIGHT = "#2E3F55"
FG_WHITE = "#ECEFF1"
FG_ACC   = "#64B5F6"
BTN_RUN  = "#4CAF50"
BTN_EXP  = "#FF9800"


# ──────────────────────────────────────────────────────────────────────
# Helper widgets
# ──────────────────────────────────────────────────────────────────────

class LabeledEntry(tk.Frame):
    """A label + entry widget pair."""
    def __init__(self, parent, label: str, default: str = "", width: int = 18, **kw):
        super().__init__(parent, bg=BG_MID, **kw)
        tk.Label(self, text=label, bg=BG_MID, fg=FG_WHITE,
                 font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        self.var = tk.StringVar(value=default)
        tk.Entry(self, textvariable=self.var, width=width,
                 bg=BG_LIGHT, fg=FG_WHITE, insertbackground=FG_WHITE,
                 relief="flat", font=("Segoe UI", 9)).pack(side="left", padx=(4, 0))

    def get(self) -> str:
        return self.var.get().strip()

    def set(self, v: str):
        self.var.set(v)


class FileEntry(tk.Frame):
    """Label + read-only entry + Browse button."""
    def __init__(self, parent, label: str, **kw):
        super().__init__(parent, bg=BG_MID, **kw)
        tk.Label(self, text=label, bg=BG_MID, fg=FG_WHITE,
                 font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
        self.var = tk.StringVar()
        # Pack button first (right-anchored) so it stays visible at any width
        tk.Button(self, text="…", command=self._browse,
                  bg="#37474F", fg=FG_WHITE, relief="flat",
                  font=("Segoe UI", 9, "bold"), width=3,
                  cursor="hand2").pack(side="right", padx=(2, 0))
        tk.Entry(self, textvariable=self.var,
                 bg=BG_LIGHT, fg=FG_ACC, state="readonly",
                 relief="flat", font=("Segoe UI", 9)).pack(side="left", padx=(4, 0), fill="x", expand=True)

    def _browse(self):
        path = filedialog.askopenfilename(
            filetypes=[("CSV / Excel", "*.csv *.xlsx *.xls"), ("All files", "*.*")]
        )
        if path:
            self.var.set(path)

    def get(self) -> str:
        return self.var.get().strip()

    def set(self, v: str):
        self.var.set(v)


# ──────────────────────────────────────────────────────────────────────
# Chart panel
# ──────────────────────────────────────────────────────────────────────

class ChartPanel(tk.Frame):
    """Holds a matplotlib Figure with a toolbar and SKU/chart-type selectors."""

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG_DARK, **kw)
        self._mgr: Optional[ScenarioManager] = None
        self._build()

    def _build(self):
        # Toolbar row
        bar = tk.Frame(self, bg=BG_MID, pady=4)
        bar.pack(fill="x", side="top")

        tk.Label(bar, text="Chart:", bg=BG_MID, fg=FG_WHITE,
                 font=("Segoe UI", 9)).pack(side="left", padx=(8, 2))
        self.chart_var = tk.StringVar(value="Inventory Levels")
        chart_cb = ttk.Combobox(bar, textvariable=self.chart_var, width=22,
                                values=["Inventory Levels", "Fill Rate",
                                        "Stockout Qty", "Weekly Demand vs Supply",
                                        "Capacity Utilisation", "Inv Cover (wks)"],
                                state="readonly", font=("Segoe UI", 9))
        chart_cb.pack(side="left", padx=2)

        tk.Label(bar, text="SKU:", bg=BG_MID, fg=FG_WHITE,
                 font=("Segoe UI", 9)).pack(side="left", padx=(12, 2))
        self.sku_var = tk.StringVar(value="ALL")
        self.sku_cb = ttk.Combobox(bar, textvariable=self.sku_var, width=14,
                                   values=["ALL"], state="readonly",
                                   font=("Segoe UI", 9))
        self.sku_cb.pack(side="left", padx=2)

        tk.Label(bar, text="Region:", bg=BG_MID, fg=FG_WHITE,
                 font=("Segoe UI", 9)).pack(side="left", padx=(8, 2))
        self.reg_var = tk.StringVar(value="ALL")
        self.reg_cb = ttk.Combobox(bar, textvariable=self.reg_var, width=10,
                                   values=["ALL"], state="readonly",
                                   font=("Segoe UI", 9))
        self.reg_cb.pack(side="left", padx=2)

        tk.Button(bar, text="Refresh", command=self.refresh,
                  bg=FG_ACC, fg=BG_DARK, font=("Segoe UI", 9, "bold"),
                  relief="flat", padx=8).pack(side="left", padx=(12, 0))

        # Figure
        self.fig = Figure(figsize=(9, 5), dpi=100, facecolor=BG_DARK)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        toolbar_frame = tk.Frame(self, bg=BG_MID)
        toolbar_frame.pack(fill="x")
        NavigationToolbar2Tk(self.canvas, toolbar_frame)

    def load(self, mgr: ScenarioManager) -> None:
        self._mgr = mgr
        df = mgr.combined()
        skus    = ["ALL"] + sorted(df[Cols.SKU_ID].unique().tolist())
        regions = ["ALL"] + sorted(df[Cols.REGION].unique().tolist())
        self.sku_cb["values"]  = skus
        self.reg_cb["values"]  = regions
        self.sku_var.set("ALL")
        self.reg_var.set("ALL")
        self.refresh()

    def refresh(self) -> None:
        if self._mgr is None:
            return
        chart = self.chart_var.get()
        sku    = self.sku_var.get()
        region = self.reg_var.get()
        self.fig.clf()
        try:
            if chart == "Inventory Levels":
                self._plot_inventory(sku, region)
            elif chart == "Fill Rate":
                self._plot_fill_rate(sku, region)
            elif chart == "Stockout Qty":
                self._plot_stockout(sku, region)
            elif chart == "Weekly Demand vs Supply":
                self._plot_demand_supply(sku, region)
            elif chart == "Capacity Utilisation":
                self._plot_capacity(sku, region)
            elif chart == "Inv Cover (wks)":
                self._plot_cover(sku, region)
        except Exception as e:
            ax = self.fig.add_subplot(111)
            ax.set_facecolor(BG_DARK)
            ax.text(0.5, 0.5, str(e), ha="center", va="center",
                    color="red", transform=ax.transAxes)
        self.canvas.draw()

    def _filtered(self, sku: str, region: str) -> pd.DataFrame:
        df = self._mgr.combined()
        if sku    != "ALL": df = df[df[Cols.SKU_ID] == sku]
        if region != "ALL": df = df[df[Cols.REGION]  == region]
        return df

    def _ax_style(self, ax, title: str, ylabel: str):
        ax.set_facecolor(BG_MID)
        ax.set_title(title, color=FG_WHITE, fontsize=11, pad=8)
        ax.set_xlabel("Week", color=FG_ACC, fontsize=9)
        ax.set_ylabel(ylabel, color=FG_ACC, fontsize=9)
        ax.tick_params(colors=FG_WHITE, labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(BG_LIGHT)
        ax.legend(facecolor=BG_LIGHT, labelcolor=FG_WHITE, fontsize=8)
        self.fig.patch.set_facecolor(BG_DARK)
        # Rotate x-tick labels
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)

    def _plot_inventory(self, sku, region):
        df = self._filtered(sku, region)
        ax = self.fig.add_subplot(111)
        for i, s in enumerate(self._mgr.scenarios()):
            sub = df[df[Cols.SCENARIO] == s].groupby(Cols.WEEK)[Cols.CLOSING_INV].sum()
            c = COLOURS.get(s, DEFAULT_COLOURS[i % len(DEFAULT_COLOURS)])
            ax.plot(sub.index, sub.values, label=s, color=c, linewidth=2, marker="o", markersize=3)
        # Safety stock line (Base scenario average)
        base_ss = df[df[Cols.SCENARIO] == self._mgr.scenarios()[0]].groupby(Cols.WEEK)[Cols.SAFETY_STOCK_QTY].sum()
        ax.fill_between(base_ss.index, base_ss.values, alpha=0.15, color="#FF9800", label="Safety Stock")
        self._ax_style(ax, "Closing Inventory by Week", "Units")

    def _plot_fill_rate(self, sku, region):
        ax = self.fig.add_subplot(111)
        df = self._filtered(sku, region)
        for i, s in enumerate(self._mgr.scenarios()):
            sub = df[df[Cols.SCENARIO] == s].groupby(Cols.WEEK)[Cols.FILL_RATE].mean()
            c = COLOURS.get(s, DEFAULT_COLOURS[i % len(DEFAULT_COLOURS)])
            ax.plot(sub.index, sub.values * 100, label=s, color=c, linewidth=2)
        ax.axhline(95, color="#FF9800", linestyle="--", linewidth=1, label="95% target")
        self._ax_style(ax, "Average Fill Rate by Week (%)", "Fill Rate (%)")
        ax.set_ylim(0, 105)

    def _plot_stockout(self, sku, region):
        ax = self.fig.add_subplot(111)
        df = self._filtered(sku, region)
        weeks = sorted(df[Cols.WEEK].unique())
        n_scenarios = len(self._mgr.scenarios())
        width = 0.8 / n_scenarios
        x = range(len(weeks))
        for i, s in enumerate(self._mgr.scenarios()):
            sub = df[df[Cols.SCENARIO] == s].groupby(Cols.WEEK)[Cols.STOCKOUT_QTY].sum().reindex(weeks, fill_value=0)
            offset = (i - n_scenarios / 2 + 0.5) * width
            c = COLOURS.get(s, DEFAULT_COLOURS[i % len(DEFAULT_COLOURS)])
            ax.bar([xi + offset for xi in x], sub.values, width=width, label=s, color=c, alpha=0.85)
        ax.set_xticks(list(x))
        ax.set_xticklabels(weeks, rotation=45, ha="right", fontsize=7)
        self._ax_style(ax, "Stockout Quantity by Week", "Units")

    def _plot_demand_supply(self, sku, region):
        ax = self.fig.add_subplot(111)
        df = self._filtered(sku, region)
        for i, s in enumerate(self._mgr.scenarios()):
            sub = df[df[Cols.SCENARIO] == s]
            demand  = sub.groupby(Cols.WEEK)[Cols.DEMAND_FCST].sum()
            receipt = sub.groupby(Cols.WEEK)[Cols.SUPPLY_RECEIPT].sum()
            c = COLOURS.get(s, DEFAULT_COLOURS[i % len(DEFAULT_COLOURS)])
            ax.plot(demand.index,  demand.values,  label=f"{s} Demand",  color=c, linewidth=2)
            ax.plot(receipt.index, receipt.values, label=f"{s} Receipt", color=c, linewidth=1.5, linestyle="--")
        self._ax_style(ax, "Weekly Demand vs Supply Receipts", "Units")

    def _plot_capacity(self, sku, region):
        ax = self.fig.add_subplot(111)
        df = self._filtered(sku, region)
        for i, s in enumerate(self._mgr.scenarios()):
            sub = df[df[Cols.SCENARIO] == s].groupby(Cols.WEEK)[Cols.REORDER_QTY].sum()
            c = COLOURS.get(s, DEFAULT_COLOURS[i % len(DEFAULT_COLOURS)])
            ax.bar(range(len(sub)), sub.values, label=f"{s} Orders", color=c, alpha=0.7)
            ax.set_xticks(range(len(sub)))
            ax.set_xticklabels(sub.index, rotation=45, ha="right", fontsize=7)
        self._ax_style(ax, "Replenishment Orders Placed by Week", "Units Ordered")

    def _plot_cover(self, sku, region):
        ax = self.fig.add_subplot(111)
        df = self._filtered(sku, region)
        for i, s in enumerate(self._mgr.scenarios()):
            sub = df[df[Cols.SCENARIO] == s].groupby(Cols.WEEK)[Cols.INV_COVER_WKS].mean()
            c = COLOURS.get(s, DEFAULT_COLOURS[i % len(DEFAULT_COLOURS)])
            ax.plot(sub.index, sub.values, label=s, color=c, linewidth=2)
        ax.axhline(2, color="#FF9800", linestyle="--", linewidth=1, label="2-wk SS floor")
        self._ax_style(ax, "Average Inventory Cover (weeks)", "Weeks of Cover")


# ──────────────────────────────────────────────────────────────────────
# KPI Table panel
# ──────────────────────────────────────────────────────────────────────

class KPITablePanel(tk.Frame):
    """Treeview-based KPI summary table."""

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG_DARK, **kw)
        self._build()

    def _build(self):
        # Filter bar
        bar = tk.Frame(self, bg=BG_MID, pady=4)
        bar.pack(fill="x")
        tk.Label(bar, text="Filter scenario:", bg=BG_MID, fg=FG_WHITE,
                 font=("Segoe UI", 9)).pack(side="left", padx=8)
        self.filter_var = tk.StringVar(value="ALL")
        self.filter_cb = ttk.Combobox(bar, textvariable=self.filter_var, width=14,
                                      values=["ALL"], state="readonly",
                                      font=("Segoe UI", 9))
        self.filter_cb.pack(side="left")
        self.filter_cb.bind("<<ComboboxSelected>>", lambda _: self._apply_filter())

        # Treeview
        cols = ["scenario", "sku_id", "region",
                "total_demand", "total_fulfilled", "total_stockout",
                "avg_fill_rate", "avg_closing_inv", "avg_inv_cover_wks",
                "total_reorder_qty"]
        self.tree = ttk.Treeview(self, columns=cols, show="headings")

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                        background=BG_LIGHT, foreground=FG_WHITE,
                        rowheight=22, fieldbackground=BG_LIGHT,
                        font=("Segoe UI", 9))
        style.configure("Treeview.Heading",
                        background=BG_MID, foreground=FG_ACC,
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#37474F")])

        col_widths = {"scenario": 80, "sku_id": 90, "region": 70,
                      "total_demand": 90, "total_fulfilled": 90,
                      "total_stockout": 90, "avg_fill_rate": 90,
                      "avg_closing_inv": 100, "avg_inv_cover_wks": 110,
                      "total_reorder_qty": 110}
        for c in cols:
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=col_widths.get(c, 90), anchor="center")

        vsb = ttk.Scrollbar(self, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.pack(fill="both", expand=True, side="left")
        vsb.pack(fill="y",  side="right")
        hsb.pack(fill="x",  side="bottom")

        self._df: Optional[pd.DataFrame] = None

    def load(self, mgr: ScenarioManager) -> None:
        self._df = mgr.kpi_summary()
        scenarios = ["ALL"] + sorted(self._df[Cols.SCENARIO].unique().tolist())
        self.filter_cb["values"] = scenarios
        self.filter_var.set("ALL")
        self._apply_filter()

    def _apply_filter(self):
        if self._df is None:
            return
        df = self._df
        sel = self.filter_var.get()
        if sel != "ALL":
            df = df[df[Cols.SCENARIO] == sel]
        self.tree.delete(*self.tree.get_children())
        for _, row in df.iterrows():
            vals = [
                row.get("scenario", ""),
                row.get("sku_id", ""),
                row.get("region", ""),
                f"{row.get('total_demand', 0):,.0f}",
                f"{row.get('total_fulfilled', 0):,.0f}",
                f"{row.get('total_stockout', 0):,.0f}",
                f"{row.get('avg_fill_rate', 0):.1%}",
                f"{row.get('avg_closing_inv', 0):,.1f}",
                f"{row.get('avg_inv_cover_wks', 0):.1f}",
                f"{row.get('total_reorder_qty', 0):,.0f}",
            ]
            self.tree.insert("", "end", values=vals)


# ──────────────────────────────────────────────────────────────────────
# Management Cockpit Panel
# ──────────────────────────────────────────────────────────────────────

class ManagementCockpitPanel(tk.Frame):
    """
    Management Layer cockpit tab.

    Layout (top to bottom):
      ┌─────────────────────────────────────────┐
      │  P&L Summary Table (scenario comparison) │
      ├─────────────────────────────────────────┤
      │  Strategic KPI Cards                     │
      ├─────────────────────────────────────────┤
      │  Tariff & FX (Landed Cost) comparison    │
      ├───────────────────────┬─────────────────┤
      │  CCC Chart            │  GP chart        │
      ├───────────────────────┴─────────────────┤
      │  Issues & Risks list  (Japanese text)    │
      └─────────────────────────────────────────┘
    """

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG_DARK, **kw)
        self._mgr: Optional[ScenarioManager] = None
        self._lc_comparison_df = None
        self._build()

    def _build(self):
        # ── P&L table ────────────────────────────────────────────────
        pl_frame = tk.LabelFrame(self, text="  P&L Summary (Scenario Comparison)  ",
                                 bg=BG_MID, fg=FG_ACC, font=("Segoe UI", 9, "bold"),
                                 relief="groove", bd=1)
        pl_frame.pack(fill="x", padx=8, pady=(8, 4))

        pl_cols = ["scenario", "revenue", "cogs", "gross_profit",
                   "gross_margin%", "inv_value", "ccc_wks", "ar_value", "ap_value"]
        self._pl_tree = ttk.Treeview(pl_frame, columns=pl_cols,
                                     show="headings", height=5)
        pl_widths = {"scenario": 90, "revenue": 110, "cogs": 100,
                     "gross_profit": 110, "gross_margin%": 95,
                     "inv_value": 110, "ccc_wks": 80,
                     "ar_value": 110, "ap_value": 110}
        for c in pl_cols:
            self._pl_tree.heading(c, text=c.replace("_", " ").title())
            self._pl_tree.column(c, width=pl_widths.get(c, 100), anchor="center")

        pl_vsb = ttk.Scrollbar(pl_frame, orient="vertical", command=self._pl_tree.yview)
        self._pl_tree.configure(yscrollcommand=pl_vsb.set)
        self._pl_tree.pack(side="left", fill="x", expand=True)
        pl_vsb.pack(side="right", fill="y")

        # ── Strategic KPI Cards ──────────────────────────────────────
        skpi_frame = tk.LabelFrame(self,
                                   text="  \U0001f3ed Strategic KPI  (Planning Engine)",
                                   bg=BG_MID, fg=FG_ACC,
                                   font=("Segoe UI", 9, "bold"),
                                   relief="groove", bd=1)
        skpi_frame.pack(fill="x", padx=8, pady=(0, 4))

        # 5 KPI cards in a row
        self._skpi_cards: dict[str, dict] = {}
        card_defs = [
            ("fixed_cost_coverage", "固定費吸収率",    "≥ 75%",    "生産量 / CapHard"),
            ("production_leveling", "生産平準化指数",  "≥ 80%",    "1 - 変動係数"),
            ("buffer_retention",    "在庫滞留率",      "20–50%",   "バッファ保有率"),
            ("fill_rate",           "需要充足率",      "≥ 95%",    "出荷 / 需要"),
            ("avg_cap_utilization", "設備稼働率",      "70–90%",   "P / CapHard"),
        ]
        for key, label_ja, target, formula in card_defs:
            card = tk.Frame(skpi_frame, bg=BG_DARK, bd=1, relief="solid",
                            padx=10, pady=6)
            card.pack(side="left", fill="both", expand=True, padx=3, pady=4)

            tk.Label(card, text=label_ja,
                     bg=BG_DARK, fg="#90A4AE",
                     font=("Segoe UI", 8)).pack(anchor="w")

            val_var = tk.StringVar(value="--")
            val_lbl = tk.Label(card, textvariable=val_var,
                               bg=BG_DARK, fg=FG_WHITE,
                               font=("Segoe UI", 14, "bold"))
            val_lbl.pack(anchor="w")

            status_var = tk.StringVar(value="")
            status_lbl = tk.Label(card, textvariable=status_var,
                                  bg=BG_DARK, fg="#90A4AE",
                                  font=("Segoe UI", 8))
            status_lbl.pack(anchor="w")

            tk.Label(card, text=f"目標: {target}  ({formula})",
                     bg=BG_DARK, fg="#546E7A",
                     font=("Segoe UI", 7)).pack(anchor="w")

            self._skpi_cards[key] = {
                "val_var": val_var,
                "val_lbl": val_lbl,
                "status_var": status_var,
                "status_lbl": status_lbl,
            }

        # ── Tariff & FX (Landed Cost) ────────────────────────────────
        lc_frame = tk.LabelFrame(self, text="  🌐 Tariff & FX — Landed Cost Impact  ",
                                 bg=BG_MID, fg="#FFD54F",
                                 font=("Segoe UI", 9, "bold"),
                                 relief="groove", bd=1)
        lc_frame.pack(fill="x", padx=8, pady=(0, 4))

        lc_cols = ["wom_scenario", "lc_scenario", "revenue",
                   "customs_duty", "freight", "landed_gm%",
                   "margin_impact", "tariff_burden%"]
        self._lc_tree = ttk.Treeview(lc_frame, columns=lc_cols,
                                     show="headings", height=4)
        _lc_widths = {"wom_scenario": 80, "lc_scenario": 100, "revenue": 100,
                      "customs_duty": 100, "freight": 80,
                      "landed_gm%": 85, "margin_impact": 95, "tariff_burden%": 95}
        _lc_heads  = {"wom_scenario": "WOM Scen", "lc_scenario": "LC Scenario",
                      "revenue": "Revenue", "customs_duty": "Customs Duty",
                      "freight": "Freight", "landed_gm%": "Landed GM%",
                      "margin_impact": "ΔMargin pp", "tariff_burden%": "Tariff %"}
        for c in lc_cols:
            self._lc_tree.heading(c, text=_lc_heads.get(c, c))
            self._lc_tree.column(c, width=_lc_widths.get(c, 90), anchor="center")
        self._lc_tree.tag_configure("HIGH",   background="#4A1A1A", foreground="#FF6B6B")
        self._lc_tree.tag_configure("MEDIUM", background="#3A2A10", foreground="#FFD740")
        self._lc_tree.tag_configure("OK",     background=BG_LIGHT,  foreground="#69F0AE")

        lc_vsb = ttk.Scrollbar(lc_frame, orient="vertical", command=self._lc_tree.yview)
        self._lc_tree.configure(yscrollcommand=lc_vsb.set)
        self._lc_tree.pack(side="left", fill="x", expand=True)
        lc_vsb.pack(side="right", fill="y")

        # LC narrative text
        self._lc_narrative = tk.Text(
            lc_frame, height=4, width=45,
            bg="#0D1B2A", fg="#FFD54F",
            font=("Segoe UI", 8), relief="flat",
            wrap="word", state="disabled",
        )
        self._lc_narrative.pack(side="left", fill="both", expand=True,
                                padx=(8, 4), pady=2)

        # Charts row ──────────────────────────────────────────────────
        chart_row = tk.Frame(self, bg=BG_DARK)
        chart_row.pack(fill="both", expand=True, padx=8, pady=4)

        # CCC chart (left)
        ccc_frame = tk.LabelFrame(chart_row, text="  CCC (Cash to Cash Cycle, weeks)  ",
                                  bg=BG_MID, fg=FG_ACC, font=("Segoe UI", 9, "bold"),
                                  relief="groove", bd=1)
        ccc_frame.pack(side="left", fill="both", expand=True, padx=(0, 4))

        self._ccc_fig = Figure(figsize=(5, 3), dpi=90, facecolor=BG_DARK)
        self._ccc_canvas = FigureCanvasTkAgg(self._ccc_fig, master=ccc_frame)
        self._ccc_canvas.get_tk_widget().pack(fill="both", expand=True)

        # Gross Profit by scenario chart (right)
        gp_frame = tk.LabelFrame(chart_row, text="  Gross Profit by Scenario  ",
                                 bg=BG_MID, fg=FG_ACC, font=("Segoe UI", 9, "bold"),
                                 relief="groove", bd=1)
        gp_frame.pack(side="left", fill="both", expand=True, padx=(4, 0))

        self._gp_fig = Figure(figsize=(5, 3), dpi=90, facecolor=BG_DARK)
        self._gp_canvas = FigureCanvasTkAgg(self._gp_fig, master=gp_frame)
        self._gp_canvas.get_tk_widget().pack(fill="both", expand=True)

        # ── Issues & Risks ───────────────────────────────────────────
        issue_frame = tk.LabelFrame(self, text="  Management Issues & Risks  ",
                                    bg=BG_MID, fg=FG_ACC, font=("Segoe UI", 9, "bold"),
                                    relief="groove", bd=1)
        issue_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        # Scenario selector
        ctrl = tk.Frame(issue_frame, bg=BG_MID)
        ctrl.pack(fill="x", padx=4, pady=2)
        tk.Label(ctrl, text="Scenario:", bg=BG_MID, fg=FG_WHITE,
                 font=("Segoe UI", 9)).pack(side="left", padx=4)
        self._issue_scen_var = tk.StringVar(value="")
        self._issue_scen_cb = ttk.Combobox(ctrl, textvariable=self._issue_scen_var,
                                           width=14, state="readonly",
                                           font=("Segoe UI", 9))
        self._issue_scen_cb.pack(side="left")
        self._issue_scen_cb.bind("<<ComboboxSelected>>", lambda _: self._refresh_issues())

        # Issues treeview
        iss_cols = ["type", "severity", "scenario", "code", "title_ja"]
        self._issue_tree = ttk.Treeview(issue_frame, columns=iss_cols,
                                        show="headings", height=6)
        iss_widths = {"type": 60, "severity": 70, "scenario": 90,
                      "code": 160, "title_ja": 300}
        for c in iss_cols:
            self._issue_tree.heading(c, text=c.replace("_", " ").title())
            self._issue_tree.column(c, width=iss_widths.get(c, 100), anchor="w")
        self._issue_tree.tag_configure("HIGH",   background="#4A1A1A", foreground="#FF6B6B")
        self._issue_tree.tag_configure("MEDIUM", background="#3A2A10", foreground="#FFB74D")
        self._issue_tree.tag_configure("LOW",    background=BG_LIGHT,  foreground=FG_WHITE)
        self._issue_tree.tag_configure("RISK",   background="#1A2A3A",  foreground="#81D4FA")

        iss_vsb = ttk.Scrollbar(issue_frame, orient="vertical",
                                command=self._issue_tree.yview)
        self._issue_tree.configure(yscrollcommand=iss_vsb.set)
        self._issue_tree.pack(side="left", fill="both", expand=True, pady=(2, 0))
        iss_vsb.pack(side="right", fill="y")

        # Narrative text box
        self._narrative_text = tk.Text(
            issue_frame, height=7, width=60,
            bg="#0D1B2A", fg="#B0BEC5",
            font=("Segoe UI", 9), relief="flat",
            wrap="word", state="disabled",
        )
        self._narrative_text.pack(side="left", fill="both", expand=True,
                                  padx=(8, 0), pady=(2, 0))

        self._mgmt_data: dict = {}

    def load(self, mgr: ScenarioManager) -> None:
        self._mgr = mgr
        self._refresh_pl_table()
        self._refresh_strategic_kpis()
        self._refresh_lc_table()
        self._refresh_charts()
        self._refresh_issue_selector()

    # ── Strategic KPI colours ────────────────────────────────────────
    _STATUS_FG = {"OK": "#69F0AE", "WARN": "#FFD740", "ISSUE": "#FF5252"}
    _STATUS_ICON = {"OK": "✅", "WARN": "⚠️", "ISSUE": "🔴"}

    def _refresh_strategic_kpis(self):
        """Update the 5 Strategic KPI card widgets."""
        skpi = getattr(self._mgr, "strategic_kpi", None) if self._mgr else None
        if skpi is None:
            for card in self._skpi_cards.values():
                card["val_var"].set("--")
                card["status_var"].set("Planning Engine 未実行")
                card["val_lbl"].configure(fg=FG_WHITE)
                card["status_lbl"].configure(fg="#546E7A")
            return

        def _apply(key, value: float, status_fn):
            card = self._skpi_cards[key]
            card["val_var"].set(f"{value:.1%}")
            st = status_fn()
            icon = self._STATUS_ICON.get(st, "")
            card["status_var"].set(f"{icon} {st}")
            card["val_lbl"].configure(fg=self._STATUS_FG.get(st, FG_WHITE))
            card["status_lbl"].configure(fg=self._STATUS_FG.get(st, "#90A4AE"))

        _apply("fixed_cost_coverage", skpi.fixed_cost_coverage,
               skpi.status_fixed_cost_coverage)
        _apply("production_leveling", skpi.production_leveling,
               skpi.status_production_leveling)
        _apply("buffer_retention",    skpi.buffer_retention,
               skpi.status_buffer_retention)
        _apply("fill_rate",           skpi.fill_rate,
               skpi.status_fill_rate)
        _apply("avg_cap_utilization", skpi.avg_cap_utilization,
               skpi.status_cap_utilization)

    def _refresh_lc_table(self):
        """Update the Tariff & FX (Landed Cost) treeview and narrative."""
        lc_df = getattr(self._mgr, "lc_comparison_df", None) if self._mgr else None
        self._lc_tree.delete(*self._lc_tree.get_children())

        self._lc_narrative.configure(state="normal")
        self._lc_narrative.delete("1.0", "end")

        if lc_df is None or lc_df.empty:
            self._lc_narrative.insert("end",
                "（Edge Cost Master / Route Master を設定して\n"
                "Planning Engine を実行すると\nLanded Cost 分析が表示されます）")
            self._lc_narrative.configure(state="disabled")
            return

        for _, row in lc_df.iterrows():
            delta = float(row.get("margin_impact_pp", 0) or 0)
            tag   = "HIGH" if delta < -0.02 else ("MEDIUM" if delta < 0 else "OK")
            self._lc_tree.insert("", "end", tags=(tag,), values=[
                row.get("wom_scenario", ""),
                row.get("lc_scenario",  ""),
                f"${float(row.get('revenue', 0) or 0):,.0f}",
                f"${float(row.get('customs_duty', 0) or 0):,.0f}",
                f"${float(row.get('freight_total', 0) or 0):,.0f}",
                f"{float(row.get('landed_gross_margin', 0) or 0)*100:.1f}%",
                f"{delta*100:+.1f}pp",
                f"{float(row.get('tariff_burden_pct', 0) or 0)*100:.1f}%",
            ])

        # Build narrative
        try:
            from wom.engine.landed_cost import build_lc_narrative
            narrative = build_lc_narrative(lc_df)
        except Exception:
            narrative = "（Landed Cost 分析完了）"
        self._lc_narrative.insert("end", narrative)
        self._lc_narrative.configure(state="disabled")

    def _refresh_pl_table(self):
        if self._mgr is None or self._mgr.scenario_money_kpi is None:
            return
        kpi = self._mgr.scenario_money_kpi
        self._pl_tree.delete(*self._pl_tree.get_children())
        for _, row in kpi.iterrows():
            rev  = float(row.get(Cols.REVENUE,      0) or 0)
            cogs = float(row.get(Cols.COGS,         0) or 0)
            gp   = float(row.get(Cols.GROSS_PROFIT, 0) or 0)
            gm   = float(row.get(Cols.GROSS_MARGIN, 0) or 0)
            inv  = float(row.get(Cols.INV_VALUE_COST,0) or 0)
            ccc  = float(row.get(Cols.CCC_WKS,      0) or 0)
            ar   = float(row.get(Cols.AR_VALUE,     0) or 0)
            ap   = float(row.get(Cols.AP_VALUE,     0) or 0)
            scen = row.get(Cols.SCENARIO, "")
            self._pl_tree.insert("", "end", values=[
                scen,
                f"{rev:,.0f}",
                f"{cogs:,.0f}",
                f"{gp:,.0f}",
                f"{gm*100:.1f}%",
                f"{inv:,.0f}",
                f"{ccc:.1f}",
                f"{ar:,.0f}",
                f"{ap:,.0f}",
            ])

    def _refresh_charts(self):
        if self._mgr is None or self._mgr.scenario_money_kpi is None:
            return
        kpi = self._mgr.scenario_money_kpi
        scenarios = kpi[Cols.SCENARIO].tolist()
        colours = [COLOURS.get(s, DEFAULT_COLOURS[i % len(DEFAULT_COLOURS)])
                   for i, s in enumerate(scenarios)]

        # CCC chart
        self._ccc_fig.clf()
        ax = self._ccc_fig.add_subplot(111)
        ax.set_facecolor(BG_MID)
        self._ccc_fig.patch.set_facecolor(BG_DARK)
        ccc_vals = [float(kpi.loc[kpi[Cols.SCENARIO] == s, Cols.CCC_WKS].iloc[0])
                    if s in kpi[Cols.SCENARIO].values else 0 for s in scenarios]
        bars = ax.bar(range(len(scenarios)), ccc_vals, color=colours, alpha=0.85)
        ax.set_xticks(range(len(scenarios)))
        ax.set_xticklabels(scenarios, color=FG_WHITE, fontsize=9)
        ax.set_ylabel("Weeks", color=FG_ACC, fontsize=8)
        ax.tick_params(colors=FG_WHITE, labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(BG_LIGHT)
        for bar, val in zip(bars, ccc_vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    f"{val:.1f}w", ha="center", va="bottom",
                    color=FG_WHITE, fontsize=8)
        self._ccc_canvas.draw()

        # Gross Profit chart
        self._gp_fig.clf()
        ax2 = self._gp_fig.add_subplot(111)
        ax2.set_facecolor(BG_MID)
        self._gp_fig.patch.set_facecolor(BG_DARK)
        gp_vals  = [float(kpi.loc[kpi[Cols.SCENARIO] == s, Cols.GROSS_PROFIT].iloc[0])
                    if s in kpi[Cols.SCENARIO].values else 0 for s in scenarios]
        rev_vals = [float(kpi.loc[kpi[Cols.SCENARIO] == s, Cols.REVENUE].iloc[0])
                    if s in kpi[Cols.SCENARIO].values else 0 for s in scenarios]
        x = range(len(scenarios))
        ax2.bar(x, rev_vals, color=colours, alpha=0.35, label="Revenue")
        ax2.bar(x, gp_vals,  color=colours, alpha=0.85, label="Gross Profit")
        ax2.set_xticks(list(x))
        ax2.set_xticklabels(scenarios, color=FG_WHITE, fontsize=9)
        ax2.set_ylabel("Value (USD)", color=FG_ACC, fontsize=8)
        ax2.tick_params(colors=FG_WHITE, labelsize=8)
        ax2.legend(facecolor=BG_LIGHT, labelcolor=FG_WHITE, fontsize=8)
        for spine in ax2.spines.values():
            spine.set_edgecolor(BG_LIGHT)
        # Margin % annotations
        for xi, (s, gm_val) in enumerate(zip(scenarios,
                [float(kpi.loc[kpi[Cols.SCENARIO] == s, Cols.GROSS_MARGIN].iloc[0])
                 if s in kpi[Cols.SCENARIO].values else 0 for s in scenarios])):
            ax2.text(xi, gp_vals[xi] * 1.02, f"{gm_val*100:.1f}%",
                     ha="center", va="bottom", color=FG_WHITE, fontsize=8)
        self._gp_canvas.draw()

    def _refresh_issue_selector(self):
        if self._mgr is None:
            return
        self._mgmt_data = getattr(self._mgr, "management_results", {})
        scenarios = list(self._mgmt_data.keys())
        self._issue_scen_cb["values"] = scenarios
        if scenarios:
            self._issue_scen_var.set(scenarios[0])
            self._refresh_issues()
        else:
            self._narrative_text.configure(state="normal")
            self._narrative_text.delete("1.0", "end")
            self._narrative_text.insert("end", "（Base シナリオのみの場合、比較分析は表示されません）")
            self._narrative_text.configure(state="disabled")

    def _refresh_issues(self):
        scen = self._issue_scen_var.get()
        result: Optional[ManagementAnalysisResult] = self._mgmt_data.get(scen)
        self._issue_tree.delete(*self._issue_tree.get_children())
        if result is None:
            return
        for iss in result.issues:
            sev = iss.severity
            self._issue_tree.insert("", "end", tags=(sev,), values=[
                "ISSUE", sev, iss.scenario, iss.code, iss.title_ja
            ])
        for rsk in result.risks:
            self._issue_tree.insert("", "end", tags=("RISK",), values=[
                "RISK", rsk.severity, rsk.scenario, rsk.code, rsk.title_ja
            ])
        # Narrative (management analysis + strategic KPI)
        self._narrative_text.configure(state="normal")
        self._narrative_text.delete("1.0", "end")
        self._narrative_text.insert("end", result.narrative or "（分析結果なし）")
        # Append Strategic KPI narrative if available
        skpi = getattr(self._mgr, "strategic_kpi", None) if self._mgr else None
        if skpi is not None:
            self._narrative_text.insert("end", "\n\n" + skpi.to_narrative_ja())
        self._narrative_text.configure(state="disabled")


# ──────────────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────
# PSI List Panel  (lot-ID based PSI, Steps 3-8)
# ──────────────────────────────────────────────────────────────────────

class PSIListPanel(tk.Frame):
    """
    Shows lot-ID based PSI data (psi4demand or psi4supply) for one PlanNode.

    Layout:
      ┌─ node header (node_id, plan_mode, lt, type) ── [Demand] [Supply] ─┐
      │  Treeview: Week | S | CO | I | P  (lot counts)                     │
      │  ──────────────────────────────────────────────────────────────    │
      │  Lot IDs text box  (shows lot strings for selected row)            │
      │  Summary: totals                                                   │
      └───────────────────────────────────────────────────────────────────┘
    """

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG_DARK, **kw)
        self._node = None           # current PlanNode
        self._layer_var = tk.StringVar(value="supply")
        self._build()

    # ── Layout ──────────────────────────────────────────────────────────

    def _build(self):
        # ── Header: node info + layer toggle ─────────────────────────
        hdr = tk.Frame(self, bg=BG_MID, pady=4)
        hdr.pack(fill="x")

        self._node_var = tk.StringVar(value="No node loaded — use the node selector above")
        tk.Label(hdr, textvariable=self._node_var,
                 bg=BG_MID, fg=FG_ACC,
                 font=("Segoe UI", 8, "bold"),
                 anchor="w").pack(side="left", padx=8, fill="x", expand=True)

        tk.Label(hdr, text="Layer:", bg=BG_MID, fg=FG_WHITE,
                 font=("Segoe UI", 8)).pack(side="right", padx=(0, 4))
        for val, txt in (("demand", "Demand"), ("supply", "Supply")):
            tk.Radiobutton(
                hdr, text=txt, variable=self._layer_var, value=val,
                bg=BG_MID, fg=FG_WHITE, selectcolor=BG_LIGHT,
                activebackground=BG_MID, font=("Segoe UI", 8),
                command=self._refresh,
            ).pack(side="right", padx=2)

        # ── Treeview ─────────────────────────────────────────────────
        tree_frame = tk.Frame(self, bg=BG_DARK)
        tree_frame.pack(fill="both", expand=True, padx=2, pady=2)

        cols = ("week", "S", "CO", "I", "P", "CapH", "CapS")
        self._tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings",
            height=12, selectmode="browse",
        )
        col_cfg = {"week": (90, "w",      True),
                   "S":    (50, "center", False),
                   "CO":   (50, "center", False),
                   "I":    (50, "center", False),
                   "P":    (50, "center", False),
                   "CapH": (52, "center", False),
                   "CapS": (52, "center", False)}
        cap_heads = {"CapH": "CapHard", "CapS": "CapSoft"}
        for col in cols:
            w, anchor, stretch = col_cfg[col]
            self._tree.heading(col, text=cap_heads.get(col, col))
            self._tree.column(col, width=w, anchor=anchor, stretch=stretch)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # Apply dark-theme style
        style = ttk.Style()
        style.configure("PSI.Treeview",
                        background=BG_MID, foreground=FG_WHITE,
                        fieldbackground=BG_MID, rowheight=18,
                        font=("Segoe UI", 8))
        style.configure("PSI.Treeview.Heading",
                        background=BG_LIGHT, foreground=FG_ACC,
                        font=("Segoe UI", 8, "bold"))
        style.map("PSI.Treeview",
                  background=[("selected", "#37474F")],
                  foreground=[("selected", FG_WHITE)])
        self._tree.configure(style="PSI.Treeview")

        # ── Lot detail ───────────────────────────────────────────────
        # ── Capacity chart (always packed; content updated by _refresh) ──
        self._cap_chart_frame = tk.Frame(self, bg=BG_DARK, height=140)
        self._cap_chart_frame.pack_propagate(False)   # keep fixed height
        self._cap_chart_frame.pack(fill="x", padx=2, pady=(0, 2))

        self._cap_fig = Figure(figsize=(5, 1.55), dpi=88, facecolor=BG_DARK)
        self._cap_canvas = FigureCanvasTkAgg(
            self._cap_fig, master=self._cap_chart_frame)
        self._cap_canvas.get_tk_widget().pack(fill="both", expand=True)
        self._cap_chart_visible = True   # always visible

        self._det_frame = tk.LabelFrame(
            self, text="  Lot IDs  ",
            bg=BG_MID, fg=FG_ACC, font=("Segoe UI", 8, "bold"),
            relief="groove", bd=1,
        )
        self._det_frame.pack(fill="x", padx=2, pady=(0, 2))

        inner = tk.Frame(self._det_frame, bg=BG_MID)
        inner.pack(fill="x", padx=4, pady=2)

        self._lot_text = tk.Text(
            inner, height=5, bg=BG_LIGHT, fg=FG_WHITE,
            font=("Consolas", 7), relief="flat", wrap="none",
            state="disabled",
        )
        lot_vsb = ttk.Scrollbar(inner, orient="vertical",
                                command=self._lot_text.yview)
        lot_hsb = ttk.Scrollbar(self._det_frame, orient="horizontal",
                                command=self._lot_text.xview)
        self._lot_text.configure(yscrollcommand=lot_vsb.set,
                                 xscrollcommand=lot_hsb.set)
        lot_vsb.pack(side="right", fill="y")
        self._lot_text.pack(side="left", fill="x", expand=True)
        lot_hsb.pack(fill="x", padx=4, pady=(0, 2))

        # ── Summary bar ──────────────────────────────────────────────
        self._summary_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self._summary_var,
                 bg=BG_DARK, fg="#90A4AE",
                 font=("Segoe UI", 7), anchor="w",
                 ).pack(fill="x", padx=6, pady=(0, 2))

    # ── Data load ────────────────────────────────────────────────────

    def load_node(self, node) -> None:
        """Load a PlanNode and display its PSI data."""
        self._node = node
        self._refresh()

    # ── Internal helpers ─────────────────────────────────────────────

    def _refresh(self):
        if self._node is None:
            return
        node  = self._node
        layer = self._layer_var.get()           # "demand" | "supply"
        psi   = node.psi4demand if layer == "demand" else node.psi4supply

        # Node metadata header
        mode_badges = {
            "pull":     "PULL",
            "push":     "★ PUSH",
            "push_sub": "→ PUSH-SUB",
        }
        mode_str = mode_badges.get(node.plan_mode, node.plan_mode)
        decp_str = " · DECOUPLING" if node.is_decoupling else ""
        self._node_var.set(
            f"{node.node_id}  │  {mode_str}{decp_str}"
            f"  │  lt={node.lt_wks}w  │  {node.node_type}"
        )

        # Clear treeview
        for row_id in self._tree.get_children():
            self._tree.delete(row_id)

        if not node.week_labels or not psi:
            self._summary_var.set("(no PSI data)")
            return

        from wom.model.plan_node import S as S_, CO as CO_, I as I_, P as P_

        tot_s = tot_co = tot_i = tot_p = 0
        has_cap = False

        for w, wk_label in enumerate(node.week_labels):
            sq  = len(psi[w][S_])
            coq = len(psi[w][CO_])
            iq  = len(psi[w][I_])
            pq  = len(psi[w][P_])
            ch  = node.cap_hard(w)
            cs  = node.cap_soft(w)

            tot_s  += sq
            tot_co += coq
            tot_i  += iq
            tot_p  += pq
            if ch > 0 or cs > 0:
                has_cap = True

            # Row colour: capacity violation takes priority
            if ch > 0 and pq > ch:
                tag = "over_hard"
            elif cs > 0 and pq > cs:
                tag = "over_soft"
            elif any([sq, coq, iq, pq]):
                tag = "active"
            else:
                tag = "zero"

            self._tree.insert(
                "", "end", iid=str(w),
                values=(wk_label,
                        sq  if sq  else "—",
                        coq if coq else "—",
                        iq  if iq  else "—",
                        pq  if pq  else "—",
                        f"{ch:.0f}" if ch > 0 else "—",
                        f"{cs:.0f}" if cs > 0 else "—"),
                tags=(tag,),
            )

        self._tree.tag_configure("over_hard",
                                 foreground="#FFCDD2", background="#7B1212")
        self._tree.tag_configure("over_soft",
                                 foreground="#FFE0B2", background="#7B4500")
        self._tree.tag_configure("active",
                                 foreground=FG_WHITE,  background=BG_MID)
        self._tree.tag_configure("zero",
                                 foreground="#546E7A", background=BG_DARK)

        # Capacity chart: always draw (shows "no cap" placeholder if unset)
        self._draw_capacity_chart(node, psi)

        layer_str = "Demand" if layer == "demand" else "Supply"
        self._summary_var.set(
            f"Total {layer_str}:  "
            f"S={tot_s}  CO={tot_co}  I={tot_i}  P={tot_p}"
        )

        # Scroll to first active week
        for iid in self._tree.get_children():
            if self._tree.tag_has("active", iid):
                self._tree.see(iid)
                break

    def _on_select(self, event):
        """Show lot IDs for the selected week row."""
        sel = self._tree.selection()
        if not sel or self._node is None:
            return
        w     = int(sel[0])
        node  = self._node
        layer = self._layer_var.get()
        psi   = node.psi4demand if layer == "demand" else node.psi4supply

        from wom.model.plan_node import S as S_, CO as CO_, I as I_, P as P_

        lines = []
        for bidx, bname in [(S_, "S"), (CO_, "CO"), (I_, "I"), (P_, "P")]:
            lots = psi[w][bidx]
            if lots:
                lines.append(f"── {bname} ({len(lots)} lots) ──")
                lines.extend(f"  {lot}" for lot in lots)
        text = "\n".join(lines) if lines else "(all buckets empty this week)"

        self._lot_text.config(state="normal")
        self._lot_text.delete("1.0", "end")
        self._lot_text.insert("end", text)
        self._lot_text.config(state="disabled")


    def _draw_capacity_chart(self, node, psi):
        """
        Draw P-quantity bars with CapHard (red dashed) and CapSoft (orange
        dotted) reference lines.  Always called; shows placeholder if no cap.
        """
        from wom.model.plan_node import P as P_

        n     = len(node.week_labels)
        p_qty = [len(psi[w][P_]) for w in range(n)]
        ch_v  = [node.cap_hard(w) for w in range(n)]
        cs_v  = [node.cap_soft(w) for w in range(n)]

        max_ch = max(ch_v) if ch_v else 0
        max_cs = max(cs_v) if cs_v else 0

        self._cap_fig.clf()
        ax = self._cap_fig.add_subplot(111)
        ax.set_facecolor(BG_MID)
        self._cap_fig.patch.set_facecolor(BG_DARK)

        # Placeholder when no capacity data
        if max_ch == 0 and max_cs == 0:
            ax.text(0.5, 0.5, "No CapHard / CapSoft set on this node",
                    color="#546E7A", ha="center", va="center",
                    transform=ax.transAxes, fontsize=8)
            ax.set_title("Capacity Chart", color="#546E7A", fontsize=8, pad=3)
            ax.axis("off")
            self._cap_canvas.draw()
            return

        # Bar colours: red = over CapHard, orange = over CapSoft, green = OK
        bar_colors = []
        for w in range(n):
            ch = ch_v[w]; cs = cs_v[w]; p = p_qty[w]
            if ch > 0 and p > ch:
                bar_colors.append("#F44336")
            elif cs > 0 and p > cs:
                bar_colors.append("#FF9800")
            else:
                bar_colors.append("#4CAF50")

        x = list(range(n))
        ax.bar(x, p_qty, color=bar_colors, alpha=0.85, width=0.8)

        # Sealing lines
        if max_ch > 0:
            ax.axhline(max_ch, color="#F44336", linewidth=1.5,
                       linestyle="--", label=f"CapHard = {max_ch:.0f}")
        if max_cs > 0:
            ax.axhline(max_cs, color="#FF9800", linewidth=1.5,
                       linestyle=":",  label=f"CapSoft = {max_cs:.0f}")

        # X-axis ticks: sparse to avoid clutter
        step = max(1, n // 6)
        ticks = list(range(0, n, step))
        ax.set_xticks(ticks)
        ax.set_xticklabels([node.week_labels[i] for i in ticks],
                           rotation=28, ha="right", fontsize=5)

        ax.set_ylabel("P (lots)", color=FG_ACC, fontsize=7)
        ax.set_title("P vs Capacity Limits", color=FG_WHITE, fontsize=8, pad=3)
        ax.tick_params(colors=FG_WHITE, labelsize=5)
        for spine in ax.spines.values():
            spine.set_edgecolor(BG_LIGHT)

        handles = []
        from matplotlib.patches import Patch
        handles.append(Patch(facecolor="#4CAF50", label="P (OK)"))
        if max_cs > 0:
            handles.append(Patch(facecolor="#FF9800", label=f"P > CapSoft"))
        if max_ch > 0:
            handles.append(Patch(facecolor="#F44336", label=f"P > CapHard"))

        import matplotlib.lines as mlines
        if max_ch > 0:
            handles.append(mlines.Line2D([], [], color="#F44336",
                linewidth=1.5, linestyle="--", label=f"CapHard={max_ch:.0f}"))
        if max_cs > 0:
            handles.append(mlines.Line2D([], [], color="#FF9800",
                linewidth=1.5, linestyle=":",  label=f"CapSoft={max_cs:.0f}"))

        ax.legend(handles=handles, facecolor=BG_LIGHT, labelcolor=FG_WHITE,
                  fontsize=6, loc="upper right", ncol=2)

        self._cap_canvas.draw()

# SC Network Cockpit Panel  (PySI-style hammock model)
# ──────────────────────────────────────────────────────────────────────

class SCNetworkPanel(tk.Frame):
    """
    🌐 SC Network tab — split panel inspired by PySI GUI design.

    Left:  NetworkX hammock-model graph (InBound green / OutBound blue)
           Click a node to select it.
    Right: PSI chart (P/S/I bars+line) + Cost/Revenue chart for selected node.
    """

    # Node colour palette
    _NCOLOUR = {
        "global":  "#FF9800",   # orange  – Global HQ nodes
        "mother":  "#9C27B0",   # purple  – Mother Plant
        "sku":     "#4CAF50",   # green   – SKU / production (InBound)
        "region":  "#2196F3",   # blue    – Region (OutBound)
    }
    _HIGHLIGHT = "#FFEB3B"      # yellow  – selected node

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG_DARK, **kw)
        self._mgr: Optional[ScenarioManager] = None
        self._node_map: dict = {}      # node_label → {"sku": str|None, "region": str|None}
        self._selected_node: str = ""
        self._pos: dict = {}           # node_label → (x, y) data coords
        self._scenario_var = tk.StringVar(value="Base")
        self._sc_tree = None           # Step 9: lot-based planning tree (SCTree)
        # ── Event Flow Tracing state ──────────────────────────────────
        self._timeline       = None    # list[WeekSnapshot] after planning
        self._anim_running   = False
        self._anim_week      = 0
        self._anim_speed_ms  = 1000   # ms per week tick
        self._anim_after_id  = None
        self._build()

    # ── Layout ──────────────────────────────────────────────────────

    def _build(self):
        # Control bar
        bar = tk.Frame(self, bg=BG_MID, pady=4)
        bar.pack(fill="x", side="top")

        tk.Label(bar, text="Scenario:", bg=BG_MID, fg=FG_WHITE,
                 font=("Segoe UI", 9)).pack(side="left", padx=(8, 2))
        self._scen_cb = ttk.Combobox(bar, textvariable=self._scenario_var,
                                     width=12, state="readonly",
                                     font=("Segoe UI", 9))
        self._scen_cb.pack(side="left", padx=2)
        self._scen_cb.bind("<<ComboboxSelected>>", lambda _: self._refresh_right())

        # Product selector (shown only in hammock mode after Planning Engine)
        tk.Label(bar, text="Product:", bg=BG_MID, fg=FG_WHITE,
                 font=("Segoe UI", 9)).pack(side="left", padx=(10, 2))
        self._prod_var = tk.StringVar(value="")
        self._prod_cb = ttk.Combobox(bar, textvariable=self._prod_var,
                                     width=14, state="readonly",
                                     font=("Segoe UI", 9))
        self._prod_cb.pack(side="left", padx=2)
        self._prod_cb.bind("<<ComboboxSelected>>",
                           lambda _: self._redraw_hammock())

        self._node_lbl_var = tk.StringVar(value="← Click a node to inspect its PSI / Cost")
        tk.Label(bar, textvariable=self._node_lbl_var,
                 bg=BG_MID, fg=FG_ACC,
                 font=("Segoe UI", 9, "italic")).pack(side="left", padx=16)

        if not HAS_NX:
            tk.Label(self,
                     text="networkx not installed.\nRun:  pip install networkx",
                     bg=BG_DARK, fg="#FF6B6B",
                     font=("Segoe UI", 11)).pack(expand=True)
            return

        # PanedWindow — left: network, right: charts
        paned = tk.PanedWindow(self, orient="horizontal", bg=BG_DARK,
                               sashwidth=5, sashrelief="flat")
        paned.pack(fill="both", expand=True)

        # ── Left: NetworkX graph ─────────────────────────────────────
        lf = tk.Frame(paned, bg=BG_DARK)
        paned.add(lf, minsize=380)

        self._net_fig = Figure(figsize=(5, 7), dpi=90, facecolor=BG_DARK)
        self._net_canvas = FigureCanvasTkAgg(self._net_fig, master=lf)
        self._net_canvas.get_tk_widget().pack(fill="both", expand=True)
        self._net_canvas.mpl_connect("button_press_event", self._on_node_click)

        # ── Event Flow animation controls ─────────────────────────────
        anim_bar = tk.Frame(lf, bg=BG_MID, pady=3)
        anim_bar.pack(fill="x", side="bottom")

        self._anim_play_btn = tk.Button(
            anim_bar, text="▶", width=3,
            command=self._anim_play,
            bg="#1B5E20", fg="white", font=("Segoe UI", 9, "bold"),
            relief="flat", state="disabled")
        self._anim_play_btn.pack(side="left", padx=(6, 2))

        self._anim_pause_btn = tk.Button(
            anim_bar, text="⏸", width=3,
            command=self._anim_pause,
            bg=BG_LIGHT, fg=FG_WHITE, font=("Segoe UI", 9),
            relief="flat", state="disabled")
        self._anim_pause_btn.pack(side="left", padx=2)

        self._anim_stop_btn = tk.Button(
            anim_bar, text="⏹", width=3,
            command=self._anim_stop,
            bg=BG_LIGHT, fg=FG_WHITE, font=("Segoe UI", 9),
            relief="flat", state="disabled")
        self._anim_stop_btn.pack(side="left", padx=2)

        tk.Label(anim_bar, text="Speed:", bg=BG_MID, fg=FG_WHITE,
                 font=("Segoe UI", 8)).pack(side="left", padx=(8, 2))
        self._speed_var = tk.StringVar(value="1×")
        speed_cb = ttk.Combobox(anim_bar, textvariable=self._speed_var,
                                values=["0.5×", "1×", "2×", "4×"],
                                width=5, state="readonly",
                                font=("Segoe UI", 8))
        speed_cb.pack(side="left", padx=2)
        speed_cb.bind("<<ComboboxSelected>>", self._on_speed_change)

        self._week_lbl_var = tk.StringVar(value="Event Flow Tracing  (Run Planning Engine first)")
        tk.Label(anim_bar, textvariable=self._week_lbl_var,
                 bg=BG_MID, fg=FG_ACC,
                 font=("Segoe UI", 8, "italic")).pack(side="left", padx=10)

        # ── Right: sub-notebook (PSI Chart | PSI List) ─────────────
        rf = tk.Frame(paned, bg=BG_DARK)
        paned.add(rf, minsize=380)

        right_nb = ttk.Notebook(rf)
        right_nb.pack(fill="both", expand=True)

        # Tab 1 – PSI Chart (existing matplotlib charts)
        chart_frame = tk.Frame(right_nb, bg=BG_DARK)
        right_nb.add(chart_frame, text="  PSI Chart  ")

        self._psi_fig = Figure(figsize=(5, 3.5), dpi=90, facecolor=BG_DARK)
        self._psi_canvas = FigureCanvasTkAgg(self._psi_fig, master=chart_frame)
        self._psi_canvas.get_tk_widget().pack(fill="both", expand=True)

        self._cost_fig = Figure(figsize=(5, 3.5), dpi=90, facecolor=BG_DARK)
        self._cost_canvas = FigureCanvasTkAgg(self._cost_fig, master=chart_frame)
        self._cost_canvas.get_tk_widget().pack(fill="both", expand=True)

        # Tab 2 – PSI List (lot-ID based, Steps 3-8)
        psi_list_outer = tk.Frame(right_nb, bg=BG_DARK)
        right_nb.add(psi_list_outer, text="  📋 PSI List  ")

        # Node selector bar
        sel_bar = tk.Frame(psi_list_outer, bg=BG_MID, pady=3)
        sel_bar.pack(fill="x")
        tk.Label(sel_bar, text="Node:", bg=BG_MID, fg=FG_WHITE,
                 font=("Segoe UI", 8)).pack(side="left", padx=(8, 2))
        self._psi_node_var = tk.StringVar(value="")
        self._psi_node_cb = ttk.Combobox(
            sel_bar, textvariable=self._psi_node_var,
            width=44, state="readonly", font=("Segoe UI", 8),
        )
        self._psi_node_cb.pack(side="left", padx=2, fill="x", expand=True)
        self._psi_node_cb.bind("<<ComboboxSelected>>",
                               self._on_psi_node_select)

        self._psi_list_panel = PSIListPanel(psi_list_outer)
        self._psi_list_panel.pack(fill="both", expand=True)

    # ── Data load ────────────────────────────────────────────────────

    def load(self, mgr: ScenarioManager) -> None:
        if not HAS_NX:
            return
        self._mgr = mgr
        scenarios = mgr.scenarios()
        self._scen_cb["values"] = scenarios
        if scenarios:
            self._scenario_var.set(scenarios[0])
        if getattr(self, "_hammock_mode", False):
            # Hammock mode: Planning Engine drew the tree — redraw to keep it
            self._redraw_hammock()
        else:
            self._build_graph()
            # Auto-select first Region node
            region_nodes = [k for k in self._node_map if k.startswith("Region:")]
            if region_nodes:
                self._select_node(region_nodes[0])

    # ── Graph construction ───────────────────────────────────────────

    def _build_graph(self):
        df       = self._mgr.combined()
        regions  = sorted(df[Cols.REGION].unique().tolist())
        skus     = sorted(df[Cols.SKU_ID].unique().tolist())

        G = nx.DiGraph()
        G_PROC   = "Global\nProcurement"
        MOTHER   = "Mother\nPlant"
        G_MKT    = "Global\nMarketing"

        # Fixed nodes
        G.add_node(G_PROC,  x=0, y=0,   kind="global",  side="inbound")
        G.add_node(MOTHER,  x=2, y=0,   kind="mother",  side="center")
        G.add_node(G_MKT,   x=4, y=0,   kind="global",  side="outbound")

        # InBound: one node per SKU
        n_s = len(skus)
        for i, sku in enumerate(skus):
            y = (i - (n_s - 1) / 2) * 1.6
            nid = f"SKU:{sku}"
            G.add_node(nid, x=1, y=y, kind="sku", side="inbound")
            G.add_edge(G_PROC, nid)
            G.add_edge(nid, MOTHER)

        # OutBound: one node per Region
        n_r = len(regions)
        for j, reg in enumerate(regions):
            y = (j - (n_r - 1) / 2) * 1.8
            nid = f"Region:{reg}"
            G.add_node(nid, x=3, y=y, kind="region", side="outbound")
            G.add_edge(MOTHER, nid)
            G.add_edge(nid, G_MKT)

        self._G      = G
        self._MOTHER = MOTHER
        self._pos    = {n: (G.nodes[n]["x"], G.nodes[n]["y"]) for n in G.nodes}

        # node_map: clickable nodes → filter
        self._node_map = {}
        for sku in skus:
            self._node_map[f"SKU:{sku}"]      = {"sku": sku,  "region": None}
        for reg in regions:
            self._node_map[f"Region:{reg}"]   = {"sku": None, "region": reg}
        self._node_map[MOTHER]                = {"sku": None, "region": None}

        self._draw_graph()

    # ── Network drawing ──────────────────────────────────────────────

    def _draw_graph(self, highlight: str = ""):
        if not hasattr(self, "_G"):
            return
        G = self._G

        self._net_fig.clf()
        ax = self._net_fig.add_subplot(111)
        ax.set_facecolor(BG_DARK)
        self._net_fig.patch.set_facecolor(BG_DARK)
        ax.axis("off")

        pos = self._pos

        node_colors, node_sizes = [], []
        for node in G.nodes:
            kind  = G.nodes[node].get("kind", "sku")
            is_hl = (node == highlight)
            node_colors.append(self._HIGHLIGHT if is_hl
                               else self._NCOLOUR.get(kind, "#607D8B"))
            node_sizes.append(2400 if is_hl else 1400)

        # Edges
        nx.draw_networkx_edges(G, pos, ax=ax,
                               edge_color="#546E7A",
                               arrows=True, arrowsize=14,
                               arrowstyle="-|>", width=1.5,
                               alpha=0.75,
                               connectionstyle="arc3,rad=0.08")
        # Nodes
        nx.draw_networkx_nodes(G, pos, ax=ax,
                               node_color=node_colors,
                               node_size=node_sizes,
                               alpha=0.92)
        # Labels
        labels = {}
        for node in G.nodes:
            if node.startswith("SKU:"):
                labels[node] = node[4:]
            elif node.startswith("Region:"):
                labels[node] = node[7:]
            else:
                labels[node] = node
        nx.draw_networkx_labels(G, pos, labels=labels, ax=ax,
                                font_color=FG_WHITE,
                                font_size=8, font_weight="bold")

        # InBound / OutBound zone labels
        ax.text(1, ax.get_ylim()[1] * 0.92 if ax.get_ylim()[1] != 0 else 3,
                "← InBound (Supply)",
                color="#4CAF50", fontsize=8, ha="center", style="italic")
        ax.text(3, ax.get_ylim()[1] * 0.92 if ax.get_ylim()[1] != 0 else 3,
                "OutBound (Demand) →",
                color="#2196F3", fontsize=8, ha="center", style="italic")

        # Legend
        from matplotlib.patches import Patch
        legend_elems = [
            Patch(facecolor=self._NCOLOUR["global"], label="Global HQ"),
            Patch(facecolor=self._NCOLOUR["mother"], label="Mother Plant"),
            Patch(facecolor=self._NCOLOUR["sku"],    label="SKU / Prod  [InBound]"),
            Patch(facecolor=self._NCOLOUR["region"], label="Region  [OutBound]"),
            Patch(facecolor=self._HIGHLIGHT,         label="Selected"),
        ]
        ax.legend(handles=legend_elems, loc="lower center",
                  facecolor=BG_MID, labelcolor=FG_WHITE,
                  fontsize=7, framealpha=0.85,
                  ncol=2)

        ax.set_title("SC Network  –  Hammock Model",
                     color=FG_WHITE, fontsize=9, pad=6)

        self._net_canvas.draw()

    # ── Node click ────────────────────────────────────────────────────

    def _on_node_click(self, event):
        if event.inaxes is None:
            return
        cx, cy = event.xdata, event.ydata
        if cx is None or cy is None:
            return

        # Choose position dict: hammock mode or simulation mode
        if getattr(self, "_hammock_mode", False) and hasattr(self, "_pos_hammock"):
            pos_dict = self._pos_hammock
        elif self._pos:
            pos_dict = self._pos
        else:
            return

        best, best_d = None, float("inf")
        for node, (nx_x, nx_y) in pos_dict.items():
            d = ((cx - nx_x) ** 2 + (cy - nx_y) ** 2) ** 0.5
            if d < best_d:
                best_d, best = d, node

        if best_d < 0.6:
            if getattr(self, "_hammock_mode", False):
                self._select_hammock_node(best)
            elif best in self._node_map:
                self._select_node(best)

    def _select_hammock_node(self, node_id: str):
        """Handle click on a hammock-mode node."""
        self._selected_node = node_id
        node_obj = getattr(self, "_node_map_hammock", {}).get(node_id)
        disp = node_obj.node_name if node_obj else node_id
        self._node_lbl_var.set(f"Selected: {disp}")
        self._draw_hammock(highlight=node_id)
        # Auto-select in PSI List
        if node_obj and hasattr(self, "_psi_node_cb"):
            self._psi_node_var.set(node_obj.node_id)
            self._on_psi_node_select(None)
        # Try to refresh right PSI chart if simulation data available
        if self._mgr and node_obj:
            region = None
            # Only extract region for leaf_out nodes (node_id="OUT:leaf_out:REGION:PROD")
            # For dad/mom/supply_point, show all regions (region=None)
            from wom.model.plan_node import NODE_TYPE_LEAF_OUT
            if node_obj.node_type == NODE_TYPE_LEAF_OUT and ":" in node_obj.node_id:
                parts = node_obj.node_id.split(":")
                if len(parts) >= 4:
                    region = parts[2]
            flt  = {"sku": node_obj.product, "region": region}
            scen = self._scenario_var.get()
            self._draw_psi(flt, scen)
            self._draw_cost(flt, scen)

    def _select_node(self, node_label: str):
        self._selected_node = node_label
        disp = node_label.replace("SKU:", "SKU: ").replace("Region:", "Region: ")
        self._node_lbl_var.set(f"Selected: {disp}")
        self._draw_graph(highlight=node_label)
        self._refresh_right()
        self._try_update_psi_list(node_label)   # Step 9

    # ── Right panel: PSI + Cost ───────────────────────────────────────

    def _refresh_right(self):
        if self._mgr is None or not self._selected_node:
            return
        flt  = self._node_map.get(self._selected_node, {})
        scen = self._scenario_var.get()
        self._draw_psi(flt, scen)
        self._draw_cost(flt, scen)

    def _filter_sim(self, flt: dict, scen: str) -> pd.DataFrame:
        df = self._mgr.combined()
        df = df[df[Cols.SCENARIO] == scen]
        if flt.get("sku"):
            df = df[df[Cols.SKU_ID] == flt["sku"]]
        if flt.get("region"):
            df = df[df[Cols.REGION] == flt["region"]]
        return df

    def _ax_dark(self, ax, title: str):
        ax.set_facecolor(BG_MID)
        ax.set_title(title, color=FG_WHITE, fontsize=9, pad=6)
        ax.tick_params(colors=FG_WHITE, labelsize=6)
        ax.set_ylabel("", color=FG_ACC, fontsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(BG_LIGHT)

    def _draw_psi(self, flt: dict, scen: str):
        self._psi_fig.clf()
        ax = self._psi_fig.add_subplot(111)
        ax.set_facecolor(BG_MID)
        self._psi_fig.patch.set_facecolor(BG_DARK)

        df = self._filter_sim(flt, scen)
        if df.empty:
            ax.text(0.5, 0.5, "No data for selection",
                    color=FG_WHITE, ha="center", va="center",
                    transform=ax.transAxes)
            self._psi_canvas.draw()
            return

        wk = (df.groupby(Cols.WEEK)
              .agg(receipt=(Cols.SUPPLY_RECEIPT,   "sum"),
                   sales  =(Cols.DEMAND_FULFILLED, "sum"),
                   inv    =(Cols.CLOSING_INV,      "sum"))
              .reset_index())

        weeks = wk[Cols.WEEK].tolist()
        x = list(range(len(weeks)))
        w = 0.32

        ax.bar([xi - w / 2 for xi in x], wk["receipt"], width=w,
               label="P: Supply Receipt", color="#4CAF50", alpha=0.85)
        ax.bar([xi + w / 2 for xi in x], wk["sales"],   width=w,
               label="S: Sales/Fulfilled", color="#2196F3", alpha=0.85)

        ax2 = ax.twinx()
        ax2.fill_between(x, wk["inv"], alpha=0.18, color="#FF9800")
        ax2.plot(x, wk["inv"], color="#FF9800", linewidth=1.5,
                 marker="o", markersize=3, label="I: Inventory")
        ax2.set_ylabel("Inventory", color="#FF9800", fontsize=7)
        ax2.tick_params(colors=FG_WHITE, labelsize=6)
        ax2.set_facecolor(BG_MID)

        ax.set_xticks(x)
        ax.set_xticklabels(weeks, rotation=45, ha="right", fontsize=5)
        ax.set_ylabel("Units", color=FG_ACC, fontsize=7)
        ax.tick_params(colors=FG_WHITE, labelsize=6)
        for spine in ax.spines.values():
            spine.set_edgecolor(BG_LIGHT)

        node_d = self._selected_node.replace("SKU:", "").replace("Region:", "")
        ax.set_title(f"PSI  ─  {node_d}  [{scen}]", color=FG_WHITE, fontsize=9, pad=6)

        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2,
                  facecolor=BG_LIGHT, labelcolor=FG_WHITE,
                  fontsize=7, loc="upper right")

        self._psi_canvas.draw()

    def _draw_cost(self, flt: dict, scen: str):
        self._cost_fig.clf()
        ax = self._cost_fig.add_subplot(111)
        ax.set_facecolor(BG_MID)
        self._cost_fig.patch.set_facecolor(BG_DARK)

        if self._mgr.weekly_money is None:
            ax.text(0.5, 0.5, "Money PSI not available",
                    color=FG_WHITE, ha="center", va="center",
                    transform=ax.transAxes)
            self._cost_canvas.draw()
            return

        wm = self._mgr.weekly_money
        df = wm[wm[Cols.SCENARIO] == scen].copy()
        if flt.get("sku"):
            df = df[df[Cols.SKU_ID] == flt["sku"]]
        if flt.get("region"):
            df = df[df[Cols.REGION] == flt["region"]]

        if df.empty:
            ax.text(0.5, 0.5, "No data for selection",
                    color=FG_WHITE, ha="center", va="center",
                    transform=ax.transAxes)
            self._cost_canvas.draw()
            return

        wk = (df.groupby(Cols.WEEK)
              .agg(revenue     =(Cols.REVENUE,      "sum"),
                   cogs        =(Cols.COGS,         "sum"),
                   gross_profit=(Cols.GROSS_PROFIT, "sum"))
              .reset_index())

        weeks = wk[Cols.WEEK].tolist()
        x = list(range(len(weeks)))
        w = 0.32

        ax.bar([xi - w / 2 for xi in x], wk["cogs"],         width=w,
               label="COGS",         color="#F44336", alpha=0.80)
        ax.bar([xi + w / 2 for xi in x], wk["gross_profit"], width=w,
               label="Gross Profit", color="#4CAF50", alpha=0.80)
        ax.plot(x, wk["revenue"], "o-",
                color="#FF9800", linewidth=1.8, markersize=4,
                label="Revenue")

        ax.set_xticks(x)
        ax.set_xticklabels(weeks, rotation=45, ha="right", fontsize=5)
        ax.set_ylabel("USD", color=FG_ACC, fontsize=7)
        ax.tick_params(colors=FG_WHITE, labelsize=6)
        for spine in ax.spines.values():
            spine.set_edgecolor(BG_LIGHT)

        node_d = self._selected_node.replace("SKU:", "").replace("Region:", "")
        ax.set_title(f"Cost / Revenue  ─  {node_d}  [{scen}]",
                     color=FG_WHITE, fontsize=9, pad=6)
        ax.legend(facecolor=BG_LIGHT, labelcolor=FG_WHITE, fontsize=7)

        self._cost_canvas.draw()
    # ── Step 9: Planning tree (lot-based PSI) ────────────────────────

    # ── Event Flow Tracing ───────────────────────────────────────────

    def set_timeline(self, timeline) -> None:
        """Called after planning completes with the built EventTimeline."""
        from wom.engine.event_timeline import max_activity
        self._timeline      = timeline
        self._anim_week     = 0
        self._anim_max_act  = max_activity(timeline)
        self._anim_running  = False
        if hasattr(self, "_anim_play_btn"):
            self._anim_play_btn.config(state="normal")
            self._anim_stop_btn.config(state="normal")
        n = len(timeline)
        self._week_lbl_var.set(
            f"Week 0/{n}  ←  press ▶ to animate")

    def _anim_play(self):
        if not self._timeline:
            return
        self._anim_running = True
        self._anim_play_btn.config(state="disabled")
        self._anim_pause_btn.config(state="normal")
        self._anim_stop_btn.config(state="normal")
        self._anim_tick()

    def _anim_pause(self):
        self._anim_running = False
        self._anim_play_btn.config(state="normal")
        self._anim_pause_btn.config(state="disabled")

    def _anim_stop(self):
        self._anim_running = False
        self._anim_week    = 0
        if self._anim_after_id:
            self.after_cancel(self._anim_after_id)
            self._anim_after_id = None
        self._anim_play_btn.config(state="normal")
        self._anim_pause_btn.config(state="disabled")
        # Redraw static graph
        self._draw_graph(highlight=self._selected_node)
        n = len(self._timeline) if self._timeline else 0
        self._week_lbl_var.set(f"Week 0/{n}  ←  press ▶ to animate")

    def _on_speed_change(self, _event=None):
        speed_map = {"0.5×": 2000, "1×": 1000, "2×": 500, "4×": 250}
        self._anim_speed_ms = speed_map.get(self._speed_var.get(), 1000)

    def _anim_tick(self):
        if not self._anim_running or not self._timeline:
            return
        n = len(self._timeline)
        if self._anim_week >= n:
            # Loop back to start
            self._anim_week = 0
        snap = self._timeline[self._anim_week]
        self._draw_graph_animated(snap)
        self._week_lbl_var.set(
            f"Week {self._anim_week + 1}/{n}  |  {snap.week_label}")
        self._anim_week += 1
        self._anim_after_id = self.after(self._anim_speed_ms, self._anim_tick)

    def _draw_graph_animated(self, snap):
        """Redraw the network graph overlaid with one week's activity snapshot."""
        if not hasattr(self, "_G"):
            return
        from wom.engine.event_timeline import max_activity

        G   = self._G
        pos = self._pos
        max_act = self._anim_max_act or 1

        self._net_fig.clf()
        ax = self._net_fig.add_subplot(111)
        ax.set_facecolor(BG_DARK)
        self._net_fig.patch.set_facecolor(BG_DARK)
        ax.axis("off")

        # ── Node colours and sizes ────────────────────────────────────
        node_colors, node_sizes = [], []
        for node in G.nodes:
            kind = G.nodes[node].get("kind", "sku")
            na   = snap.node_activity.get(node)
            if na and na.flow > 0:
                # Active: brighten + scale size
                scale = 1.0 + 2.0 * (na.flow / max_act)
                node_colors.append("#FFEB3B")  # bright yellow when active
                node_sizes.append(int(1400 * min(scale, 3.0)))
            else:
                # Inactive: dim the base colour
                base = self._NCOLOUR.get(kind, "#607D8B")
                node_colors.append(base)
                node_sizes.append(1000)

        # ── Edge colours and widths from edge_flows ───────────────────
        # Build lookup: (src, dst) → EdgeFlow
        flow_map: dict = {}
        for ef in snap.edge_flows:
            key = (ef.src, ef.dst)
            flow_map[key] = flow_map.get(key, 0) + ef.lot_count

        max_flow = snap.max_flow or 1
        edge_colors, edge_widths = [], []
        for u, v in G.edges():
            cnt = flow_map.get((u, v), 0)
            if cnt > 0:
                # Supply: green, Demand: blue-ish
                # Determine direction from graph topology (inbound nodes left of mother)
                u_x = G.nodes[u].get("x", 0)
                v_x = G.nodes[v].get("x", 0)
                if v_x >= u_x:
                    edge_colors.append("#66BB6A")  # supply green
                else:
                    edge_colors.append("#42A5F5")  # demand blue
                edge_widths.append(1.5 + 6.0 * (cnt / max_flow))
            else:
                edge_colors.append("#37474F")  # dim grey
                edge_widths.append(0.8)

        # Draw edges
        edges = list(G.edges())
        for i, (u, v) in enumerate(edges):
            nx.draw_networkx_edges(
                G, pos, edgelist=[(u, v)], ax=ax,
                edge_color=[edge_colors[i]],
                width=edge_widths[i],
                arrows=True, arrowsize=12,
                arrowstyle="-|>", alpha=0.85,
                connectionstyle="arc3,rad=0.08")

        # Draw nodes
        nx.draw_networkx_nodes(G, pos, ax=ax,
                               node_color=node_colors,
                               node_size=node_sizes,
                               alpha=0.93)

        # Labels
        labels = {}
        for node in G.nodes:
            if node.startswith("SKU:"):   labels[node] = node[4:]
            elif node.startswith("Region:"): labels[node] = node[7:]
            else:                            labels[node] = node
        nx.draw_networkx_labels(G, pos, labels=labels, ax=ax,
                                font_color=FG_WHITE,
                                font_size=8, font_weight="bold")

        # Lot-count labels on active edges
        edge_labels = {(u, v): str(flow_map[(u, v)])
                       for u, v in G.edges() if (u, v) in flow_map}
        if edge_labels:
            nx.draw_networkx_edge_labels(
                G, pos, edge_labels=edge_labels, ax=ax,
                font_color="#FFEB3B", font_size=7,
                bbox=dict(boxstyle="round,pad=0.2",
                          fc=BG_MID, ec="none", alpha=0.75))

        # Week label overlay
        ax.set_title(
            f"SC Network  –  {snap.week_label}",
            color=FG_WHITE, fontsize=10, pad=6, fontweight="bold")

        # Inventory bar: show I-count as small text on active nodes
        for node in G.nodes:
            na = snap.node_activity.get(node)
            if na and na.i_count > 0:
                x, y = pos[node]
                ax.text(x, y - 0.28, f"I:{na.i_count}",
                        color="#B0BEC5", fontsize=6, ha="center", va="top")

        # CO warning
        co_nodes = [n for n in G.nodes
                    if snap.node_activity.get(n) and
                    snap.node_activity[n].co_count > 0]
        if co_nodes:
            for cn in co_nodes:
                x, y = pos[cn]
                ax.text(x, y + 0.3, f"CO:{snap.node_activity[cn].co_count}",
                        color="#FF9800", fontsize=6, ha="center", va="bottom",
                        fontweight="bold")

        self._net_canvas.draw()

    def load_planning_tree(self, sc_tree) -> None:
        """
        Load a post-planning SCTree.
        • Populates PSI List node selector
        • Replaces the network graph with E2E hammock layout (Phase B)
        """
        if not hasattr(self, "_psi_list_panel"):
            return   # HAS_NX=False: panel was never built
        self._sc_tree = sc_tree

        # ── Populate PSI List node selector ───────────────────────────
        node_ids = []
        for prod_nm in sc_tree.products:
            for node in sc_tree.iter_all_nodes(prod_nm):
                node_ids.append(node.node_id)
        self._psi_node_cb["values"] = node_ids
        if node_ids:
            self._psi_node_var.set(node_ids[0])
            self._on_psi_node_select(None)

        # ── Switch network view to E2E hammock ────────────────────────
        self._hammock_mode = True
        prods = sc_tree.products
        self._prod_cb["values"] = prods
        if prods:
            self._prod_var.set(prods[0])
        self._redraw_hammock()

    def _redraw_hammock(self):
        """Build and draw the E2E hammock graph for the selected product."""
        if not self._sc_tree or not getattr(self, "_hammock_mode", False):
            return
        prod_nm = self._prod_var.get() or self._sc_tree.products[0]
        try:
            from wom.engine.hammock_layout import (
                build_hammock_graph, node_colour, node_size,
                NODE_COLOUR, NODE_SIZE)
            G, pos = build_hammock_graph(self._sc_tree, prod_nm)
        except Exception as exc:
            print(f"[HammockLayout] build failed: {exc}")
            import traceback; traceback.print_exc()
            return

        self._G_hammock  = G
        self._pos_hammock = pos
        self._prod_selected = prod_nm

        # Build node_map for click handling
        self._node_map_hammock = {}
        for node_id, data in G.nodes(data=True):
            self._node_map_hammock[node_id] = data.get("node_obj")

        self._draw_hammock(highlight="")

    def _draw_hammock(self, highlight: str = ""):
        """Render the hammock graph (replaces _draw_graph in Planning mode)."""
        if not hasattr(self, "_G_hammock"):
            return
        from wom.engine.hammock_layout import node_colour, node_size, NODE_COLOUR
        from matplotlib.patches import Patch

        G   = self._G_hammock
        pos = self._pos_hammock

        self._net_fig.clf()
        ax = self._net_fig.add_subplot(111)
        ax.set_facecolor(BG_DARK)
        self._net_fig.patch.set_facecolor(BG_DARK)
        ax.axis("off")

        colours, sizes = [], []
        for nid in G.nodes:
            nt  = G.nodes[nid].get("node_type", "virtual")
            hl  = (nid == highlight)
            colours.append(node_colour(nt, hl))
            sizes.append(node_size(nt, hl))

        import networkx as nx
        nx.draw_networkx_edges(G, pos, ax=ax,
                               edge_color="#546E7A",
                               arrows=True, arrowsize=14,
                               arrowstyle="-|>", width=1.5,
                               alpha=0.75,
                               connectionstyle="arc3,rad=0.05")
        nx.draw_networkx_nodes(G, pos, ax=ax,
                               node_color=colours,
                               node_size=sizes,
                               alpha=0.92)

        # Labels: use node_name (short) stored in graph
        labels = {nid: G.nodes[nid].get("label", nid)
                  for nid in G.nodes}
        nx.draw_networkx_labels(G, pos, labels=labels, ax=ax,
                                font_color=FG_WHITE,
                                font_size=7, font_weight="bold")

        # Zone annotations
        xs = [x for x, y in pos.values()]
        y_top = max(y for x, y in pos.values()) + 0.8
        if xs:
            ax.text(min(xs) * 0.6, y_top,
                    "← InBound (Supply)",
                    color="#66BB6A", fontsize=8, ha="center", style="italic")
            ax.text(max(xs) * 0.6, y_top,
                    "OutBound (Demand) →",
                    color="#42A5F5", fontsize=8, ha="center", style="italic")

        # Legend
        legend_elems = [
            Patch(facecolor=NODE_COLOUR["supply_point"], label="Supply Point (bridge)"),
            Patch(facecolor=NODE_COLOUR["mom"],          label="MOM  [InBound]"),
            Patch(facecolor=NODE_COLOUR["leaf_in"],      label="Leaf-In  [InBound]"),
            Patch(facecolor=NODE_COLOUR["dad"],          label="DAD  [OutBound]"),
            Patch(facecolor=NODE_COLOUR["leaf_out"],     label="Leaf-Out  [OutBound]"),
            Patch(facecolor=NODE_COLOUR["virtual"],      label="Virtual office"),
            Patch(facecolor="#FFFF00",                   label="Selected"),
        ]
        ax.legend(handles=legend_elems, loc="lower center",
                  facecolor=BG_MID, labelcolor=FG_WHITE,
                  fontsize=6.5, framealpha=0.85, ncol=2)

        prod_nm = getattr(self, "_prod_selected", "")
        ax.set_title(f"SC Network  –  E2E Hammock  [{prod_nm}]",
                     color=FG_WHITE, fontsize=9, pad=6)

        self._net_canvas.draw()

    def _on_psi_node_select(self, event):
        """Called when user picks a node from the PSI List combobox."""
        node_id = self._psi_node_var.get()
        if not self._sc_tree or not node_id:
            return
        for prod_nm in self._sc_tree.products:
            for node in self._sc_tree.iter_all_nodes(prod_nm):
                if node.node_id == node_id:
                    self._psi_list_panel.load_node(node)
                    return

    def _try_update_psi_list(self, node_label: str):
        """
        When a network graph node is clicked, try to auto-select the
        corresponding PlanNode in the PSI List tab.

        Mapping:
          "SKU:{sku}"     → IN:MFG:{sku}          (InBound root / MOM)
          "Region:{reg}"  → first OUT:Sales:{reg}: leaf_out
          "Mother\nPlant" → first MOM node in the tree
        """
        if not hasattr(self, "_psi_list_panel"):
            return
        if self._sc_tree is None:
            return

        sc_tree   = self._sc_tree
        target_id = None

        if node_label.startswith("SKU:"):
            sku       = node_label[4:]
            target_id = f"IN:MFG:{sku}"

        elif node_label.startswith("Region:"):
            region = node_label[7:]
            for prod_nm in sc_tree.products:
                try:
                    ot_root = sc_tree.get_ot_root(prod_nm)
                except Exception:
                    continue
                for node in ot_root.walk_preorder():
                    if f":Sales:{region}:" in node.node_id:
                        target_id = node.node_id
                        break
                if target_id:
                    break

        else:
            # "Mother\nPlant" or other fixed node → pick first IN root
            prods = list(sc_tree.products)
            if prods:
                try:
                    root      = sc_tree.get_in_root(prods[0])
                    target_id = root.node_id
                except Exception:
                    pass

        if not target_id:
            return

        for prod_nm in sc_tree.products:
            for node in sc_tree.iter_all_nodes(prod_nm):
                if node.node_id == target_id:
                    self._psi_node_var.set(target_id)
                    self._psi_list_panel.load_node(node)
                    return



# ──────────────────────────────────────────────────────────────────────
# World Map Panel  (tkintermapview-based SC node visualizer)
# ──────────────────────────────────────────────────────────────────────

# Node type → (marker circle color, marker outside color, label prefix)
_MAP_NODE_STYLE = {
    "procurement":  ("#FF9800", "#E65100", "📦"),
    "mother_plant": ("#9C27B0", "#4A148C", "🏭"),
    "sku_supplier": ("#4CAF50", "#1B5E20", "🔩"),
    "region_dc":    ("#2196F3", "#0D47A1", "🏬"),
    "marketing":    ("#F44336", "#B71C1C", "🌎"),
}

# SC links to draw between node types (src_type → dst_type)
_MAP_LINKS = [
    ("procurement",  "sku_supplier"),   # procurement → each supplier
    ("sku_supplier", "mother_plant"),   # suppliers → mother plant
    ("mother_plant", "region_dc"),      # plant → each DC
    ("region_dc",    "marketing"),      # DCs → marketing HQ
]


class WorldMapPanel(tk.Frame):
    """
    🗺 World Map tab — interactive SC node map using tkintermapview.

    Shows SC nodes as coloured markers on a world map.
    After "Run Planning Engine", overlays lot-flow animation per week.
    """

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG_DARK, **kw)
        self._nodes: list = []           # list of dicts from node_master.csv
        self._markers: list = []         # active TkinterMapView marker objects
        self._paths:   list = []         # active TkinterMapView path objects
        self._timeline = None            # EventTimeline (set after planning)
        self._anim_running  = False
        self._anim_week     = 0
        self._anim_speed_ms = 1000
        self._anim_after_id = None
        self._map_widget    = None
        self._build()

    # ── Layout ───────────────────────────────────────────────────────────

    def _build(self):
        try:
            from tkintermapview import TkinterMapView
            HAS_MAP = True
        except ImportError:
            HAS_MAP = False

        if not HAS_MAP:
            tk.Label(self,
                     text="tkintermapview not installed.\nRun:  pip install tkintermapview",
                     bg=BG_DARK, fg="#FF6B6B",
                     font=("Segoe UI", 11)).pack(expand=True)
            return

        # Control bar
        bar = tk.Frame(self, bg=BG_MID, pady=4)
        bar.pack(fill="x", side="top")

        tk.Label(bar, text="Node Master:", bg=BG_MID, fg=FG_WHITE,
                 font=("Segoe UI", 9)).pack(side="left", padx=(8, 2))
        self._file_var = tk.StringVar(value="")
        self._file_entry = tk.Entry(bar, textvariable=self._file_var,
                                    width=38, bg=BG_LIGHT, fg=FG_WHITE,
                                    font=("Segoe UI", 8), relief="flat")
        self._file_entry.pack(side="left", padx=2)
        tk.Button(bar, text="Browse…",
                  command=self._browse_node_master,
                  bg=BG_LIGHT, fg=FG_WHITE, font=("Segoe UI", 8),
                  relief="flat").pack(side="left", padx=2)
        tk.Button(bar, text="⟳ Reload",
                  command=self._reload,
                  bg="#1565C0", fg="white", font=("Segoe UI", 8),
                  relief="flat").pack(side="left", padx=(6, 2))

        # Animation controls (enabled after planning)
        tk.Label(bar, text="  |", bg=BG_MID, fg="#546E7A").pack(side="left")
        self._map_play_btn = tk.Button(
            bar, text="▶", width=3, command=self._anim_play,
            bg="#1B5E20", fg="white", font=("Segoe UI", 9, "bold"),
            relief="flat", state="disabled")
        self._map_play_btn.pack(side="left", padx=(6, 2))
        self._map_pause_btn = tk.Button(
            bar, text="⏸", width=3, command=self._anim_pause,
            bg=BG_LIGHT, fg=FG_WHITE, font=("Segoe UI", 9),
            relief="flat", state="disabled")
        self._map_pause_btn.pack(side="left", padx=2)
        self._map_stop_btn = tk.Button(
            bar, text="⏹", width=3, command=self._anim_stop,
            bg=BG_LIGHT, fg=FG_WHITE, font=("Segoe UI", 9),
            relief="flat", state="disabled")
        self._map_stop_btn.pack(side="left", padx=2)

        self._map_week_var = tk.StringVar(value="Run Planning Engine to enable animation")
        tk.Label(bar, textvariable=self._map_week_var,
                 bg=BG_MID, fg=FG_ACC,
                 font=("Segoe UI", 8, "italic")).pack(side="left", padx=10)

        # Main split: map (left) + info panel (right)
        paned = tk.PanedWindow(self, orient="horizontal", bg=BG_DARK,
                               sashwidth=5, sashrelief="flat")
        paned.pack(fill="both", expand=True)

        # Map widget
        map_frame = tk.Frame(paned, bg=BG_DARK)
        paned.add(map_frame, minsize=820)

        from tkintermapview import TkinterMapView
        self._map_widget = TkinterMapView(
            map_frame, width=700, height=520,
            corner_radius=0)
        self._map_widget.pack(fill="both", expand=True)
        # Center on world view
        self._map_widget.set_position(20.0, 10.0)
        self._map_widget.set_zoom(2)

        # Info panel (right)
        info_frame = tk.Frame(paned, bg=BG_DARK)
        paned.add(info_frame, minsize=180)

        tk.Label(info_frame, text="Node Info",
                 bg=BG_DARK, fg=FG_ACC,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=8, pady=(8, 2))

        self._info_text = tk.Text(
            info_frame, bg=BG_MID, fg=FG_WHITE,
            font=("Segoe UI", 9), relief="flat",
            wrap="word", state="disabled", width=28)
        self._info_text.pack(fill="both", expand=True, padx=6, pady=4)

        # Legend
        leg = tk.LabelFrame(info_frame, text=" Legend ",
                            bg=BG_DARK, fg=FG_ACC,
                            font=("Segoe UI", 8, "bold"),
                            relief="groove", bd=1)
        leg.pack(fill="x", padx=6, pady=4)
        for ntype, (cc, co, icon) in _MAP_NODE_STYLE.items():
            row = tk.Frame(leg, bg=BG_DARK)
            row.pack(fill="x", padx=4, pady=1)
            tk.Label(row, text="●", fg=cc, bg=BG_DARK,
                     font=("Segoe UI", 10)).pack(side="left")
            tk.Label(row, text=f"{icon} {ntype.replace('_', ' ').title()}",
                     bg=BG_DARK, fg=FG_WHITE,
                     font=("Segoe UI", 8)).pack(side="left", padx=4)

    # ── File operations ───────────────────────────────────────────────────

    def _browse_node_master(self):
        path = filedialog.askopenfilename(
            title="Select node_master.csv",
            filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if path:
            self._file_var.set(path)
            self._reload()

    def load_default(self, csv_path: str) -> None:
        """Load a node master CSV path without user interaction."""
        self._file_var.set(csv_path)
        self._reload()

    def _reload(self):
        path = self._file_var.get()
        if not path or not os.path.exists(path):
            return
        try:
            df = pd.read_csv(path)
            self._nodes = df.to_dict("records")
            self._draw_nodes()
        except Exception as exc:
            messagebox.showerror("World Map", f"Failed to load {path}:\n{exc}")

    # ── Map drawing ───────────────────────────────────────────────────────

    def _draw_nodes(self):
        if self._map_widget is None:
            return
        # Clear existing
        for m in self._markers:
            try: m.delete()
            except Exception: pass
        for p in self._paths:
            try: p.delete()
            except Exception: pass
        self._markers.clear()
        self._paths.clear()

        # Group nodes by type for link drawing
        by_type: dict = {}
        for node in self._nodes:
            ntype = str(node.get("node_type", ""))
            by_type.setdefault(ntype, []).append(node)

        # Draw SC link paths first (beneath markers)
        link_color = "#546E7A"
        for src_type, dst_type in _MAP_LINKS:
            src_nodes = by_type.get(src_type, [])
            dst_nodes = by_type.get(dst_type, [])
            for src in src_nodes:
                for dst in dst_nodes:
                    try:
                        path = self._map_widget.set_path(
                            [(float(src["lat"]), float(src["lon"])),
                             (float(dst["lat"]), float(dst["lon"]))],
                            color=link_color, width=2)
                        self._paths.append(path)
                    except Exception:
                        pass

        # Draw node markers
        for node in self._nodes:
            ntype  = str(node.get("node_type", ""))
            style  = _MAP_NODE_STYLE.get(ntype, ("#607D8B", "#455A64", "📍"))
            cc, co, icon = style
            label  = f"{icon} {node.get('node_name', node.get('node_id', ''))}"
            try:
                marker = self._map_widget.set_marker(
                    float(node["lat"]), float(node["lon"]),
                    text=label,
                    marker_color_circle=cc,
                    marker_color_outside=co,
                    command=lambda m, n=node: self._on_marker_click(m, n),
                    text_color=FG_WHITE,
                    font=("Segoe UI", 8, "bold"))
                self._markers.append(marker)
            except Exception:
                pass

    def _on_marker_click(self, marker, node: dict):
        """Show node info in the right panel."""
        info = []
        info.append(f"🏷  {node.get('node_name', node.get('node_id', ''))}")
        info.append(f"Type:  {node.get('node_type', '')}")
        info.append(f"Lat:   {node.get('lat', '')}")
        info.append(f"Lon:   {node.get('lon', '')}")
        if node.get("sku_id"):
            info.append(f"SKU:   {node['sku_id']}")
        if node.get("region"):
            info.append(f"Region: {node['region']}")
        if node.get("description"):
            info.append(f"\n{node['description']}")
        text = "\n".join(info)
        self._info_text.config(state="normal")
        self._info_text.delete("1.0", "end")
        self._info_text.insert("end", text)
        self._info_text.config(state="disabled")

    # ── EventTimeline animation ───────────────────────────────────────────

    def set_timeline(self, timeline) -> None:
        """Enable lot-flow animation once planning is complete."""
        self._timeline     = timeline
        self._anim_week    = 0
        self._anim_running = False
        if hasattr(self, "_map_play_btn"):
            self._map_play_btn.config(state="normal")
            self._map_stop_btn.config(state="normal")
        n = len(timeline)
        self._map_week_var.set(f"Week 0/{n}  ←  press ▶ to animate")

    def _anim_play(self):
        if not self._timeline:
            return
        self._anim_running = True
        self._map_play_btn.config(state="disabled")
        self._map_pause_btn.config(state="normal")
        self._map_stop_btn.config(state="normal")
        self._map_tick()

    def _anim_pause(self):
        self._anim_running = False
        self._map_play_btn.config(state="normal")
        self._map_pause_btn.config(state="disabled")

    def _anim_stop(self):
        self._anim_running = False
        self._anim_week    = 0
        if self._anim_after_id:
            self.after_cancel(self._anim_after_id)
            self._anim_after_id = None
        self._map_play_btn.config(state="normal")
        self._map_pause_btn.config(state="disabled")
        # Restore static paths
        self._draw_nodes()
        n = len(self._timeline) if self._timeline else 0
        self._map_week_var.set(f"Week 0/{n}  ←  press ▶ to animate")

    def _map_tick(self):
        if not self._anim_running or not self._timeline:
            return
        n = len(self._timeline)
        if self._anim_week >= n:
            self._anim_week = 0
        snap = self._timeline[self._anim_week]
        self._draw_animated_paths(snap)
        self._map_week_var.set(
            f"Week {self._anim_week + 1}/{n}  |  {snap.week_label}")
        self._anim_week += 1
        self._anim_after_id = self.after(self._anim_speed_ms, self._map_tick)

    def _draw_animated_paths(self, snap):
        """Redraw SC paths with widths proportional to this week's lot flows."""
        if self._map_widget is None or not self._nodes:
            return
        # Clear old paths only
        for p in self._paths:
            try: p.delete()
            except Exception: pass
        self._paths.clear()

        # Build lot-flow lookup from snapshot: gui_label -> flow count
        # GUI labels: "Region:{reg}", "Mother Plant", "SKU:{sku}"
        max_flow = snap.max_flow or 1

        # Node position lookup
        node_pos: dict = {}
        for node in self._nodes:
            ntype = str(node.get("node_type", ""))
            if ntype == "mother_plant":
                node_pos["Mother\nPlant"] = (float(node["lat"]), float(node["lon"]))
            elif ntype == "region_dc":
                reg = str(node.get("region", ""))
                node_pos[f"Region:{reg}"] = (float(node["lat"]), float(node["lon"]))
            elif ntype == "sku_supplier":
                sku = str(node.get("sku_id", ""))
                node_pos[f"SKU:{sku}"] = (float(node["lat"]), float(node["lon"]))
            elif ntype == "procurement":
                node_pos["Global\nProcurement"] = (float(node["lat"]), float(node["lon"]))

        # Draw flows
        for ef in snap.edge_flows:
            src_pos = node_pos.get(ef.src)
            dst_pos = node_pos.get(ef.dst)
            if src_pos is None or dst_pos is None:
                continue
            ratio = ef.lot_count / max_flow
            width = max(2, int(2 + 8 * ratio))
            color = "#66BB6A" if ef.direction == "supply" else "#42A5F5"
            if ef.bucket == "CO":
                color = "#FF9800"
            try:
                path = self._map_widget.set_path(
                    [src_pos, dst_pos],
                    color=color, width=width)
                self._paths.append(path)
            except Exception:
                pass

        # Static dim lines for inactive edges
        for src_type, dst_type in _MAP_LINKS:
            for src_node in self._nodes:
                if src_node.get("node_type") != src_type:
                    continue
                for dst_node in self._nodes:
                    if dst_node.get("node_type") != dst_type:
                        continue
                    # Check if this edge already has a flow path
                    s_pos = (float(src_node["lat"]), float(src_node["lon"]))
                    d_pos = (float(dst_node["lat"]), float(dst_node["lon"]))
                    # Add dim background line
                    try:
                        path = self._map_widget.set_path(
                            [s_pos, d_pos],
                            color="#263238", width=1)
                        self._paths.insert(0, path)  # behind flow paths
                    except Exception:
                        pass

# ──────────────────────────────────────────────────────────────────────
# Main application window
# ──────────────────────────────────────────────────────────────────────

class WOMApp(tk.Tk):
    """Top-level WOM application window."""

    def __init__(self):
        super().__init__()
        self.title("WOM – Weekly Operation Model  v1r0m0")
        self.configure(bg=BG_DARK)
        self.geometry("1280x820")
        self.minsize(900, 600)

        self._sim: Optional[WOMSimulator] = None
        self._mgr: Optional[ScenarioManager] = None

        # Detect sample data directory relative to this file
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(os.path.dirname(here))
        self._sample_dir = os.path.join(root, "data", "sample")

        self._build_ui()
        self._try_load_sample_paths()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        # ── Title bar ────────────────────────────────────────────────
        title_bar = tk.Frame(self, bg="#0D1B2A", pady=6)
        title_bar.pack(fill="x")
        tk.Label(title_bar, text="WOM  –  Weekly Operation Model",
                 bg="#0D1B2A", fg=FG_WHITE,
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=16)
        tk.Label(title_bar, text="v1r0m0",
                 bg="#0D1B2A", fg=FG_ACC,
                 font=("Segoe UI", 10)).pack(side="right", padx=16)

        # ── Main area ────────────────────────────────────────────
        main = tk.Frame(self, bg=BG_DARK)
        main.pack(fill="both", expand=True, padx=0, pady=0)

        # Left panel
        left = tk.Frame(main, bg=BG_MID, width=280)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self._build_left_panel(left)

        # Right panel (notebook)
        right = tk.Frame(main, bg=BG_DARK)
        right.pack(side="left", fill="both", expand=True)
        self._build_right_panel(right)

        # ── Status bar ────────────────────────────────────────────
        self._status_var = tk.StringVar(value="Ready. Load data files and click Run.")
        status = tk.Label(self, textvariable=self._status_var,
                          bg="#0D1B2A", fg=FG_ACC,
                          font=("Segoe UI", 9), anchor="w", padx=12)
        status.pack(fill="x", side="bottom")

    def _status(self, msg: str) -> None:
        """Update the status bar text."""
        self._status_var.set(msg)

    def _build_left_panel(self, parent):
        # ── Config section ───────────────────────────────────────────
        sec = tk.LabelFrame(parent, text="  Planning Config  ",
                            bg=BG_MID, fg=FG_ACC, font=("Segoe UI", 9, "bold"),
                            relief="groove", bd=1)
        sec.pack(fill="x", padx=8, pady=(12, 4))

        self._e_start = LabeledEntry(sec, "Start Week:", "2024-W01", width=12)
        self._e_start.pack(fill="x", padx=6, pady=2)

        self._e_weeks = LabeledEntry(sec, "# Weeks:", "26", width=6)
        self._e_weeks.pack(fill="x", padx=6, pady=2)

        self._e_ss = LabeledEntry(sec, "Safety Stock (wks):", "2.0", width=6)
        self._e_ss.pack(fill="x", padx=6, pady=2)

        self._e_lt = LabeledEntry(sec, "Lead Time (wks):", "4", width=6)
        self._e_lt.pack(fill="x", padx=6, pady=2)

        self._e_cap = tk.BooleanVar(value=True)
        tk.Checkbutton(sec, text="Capacity Constrained",
                       variable=self._e_cap, bg=BG_MID, fg=FG_WHITE,
                       selectcolor=BG_LIGHT, activebackground=BG_MID,
                       font=("Segoe UI", 9)).pack(anchor="w", padx=8, pady=2)

        # ── Files section ────────────────────────────────────────────
        fsec = tk.LabelFrame(parent, text="  Input Files  ",
                             bg=BG_MID, fg=FG_ACC, font=("Segoe UI", 9, "bold"),
                             relief="groove", bd=1)
        fsec.pack(fill="x", padx=8, pady=4)

        self._f_sku  = FileEntry(fsec, "SKU Master:")
        self._f_sku.pack(fill="x", padx=6, pady=2)
        self._f_dem  = FileEntry(fsec, "Demand Forecast:")
        self._f_dem.pack(fill="x", padx=6, pady=2)
        self._f_inv  = FileEntry(fsec, "Inventory Master:")
        self._f_inv.pack(fill="x", padx=6, pady=2)
        self._f_cap  = FileEntry(fsec, "Capacity Plan:")
        self._f_cap.pack(fill="x", padx=6, pady=2)
        self._f_node = FileEntry(fsec, "Node Master:")
        self._f_node.pack(fill="x", padx=6, pady=2)

        # ── SC Tree Master (Phase B multi-tier) ───────────────────────
        stsec = tk.LabelFrame(parent, text="  SC Tree Master (Multi-tier)  ",
                              bg=BG_MID, fg="#A5D6A7", font=("Segoe UI", 9, "bold"),
                              relief="groove", bd=1)
        stsec.pack(fill="x", padx=8, pady=4)
        self._f_sc_tree = FileEntry(stsec, "SC Tree Master:")
        self._f_sc_tree.pack(fill="x", padx=6, pady=2)
        tk.Label(stsec,
                 text="(省略時は Demo 2-tier tree を自動生成)",
                 bg=BG_MID, fg="#78909C", font=("Segoe UI", 8)).pack(anchor="w", padx=6)

        # ── Tariff & FX files ─────────────────────────────────────────
        lcsec = tk.LabelFrame(parent, text="  Tariff & FX (Landed Cost)  ",
                              bg=BG_MID, fg="#FFD54F", font=("Segoe UI", 9, "bold"),
                              relief="groove", bd=1)
        lcsec.pack(fill="x", padx=8, pady=4)
        self._f_edge_cost = FileEntry(lcsec, "Edge Cost Master:")
        self._f_edge_cost.pack(fill="x", padx=6, pady=2)
        self._f_route = FileEntry(lcsec, "Route Master:")
        self._f_route.pack(fill="x", padx=6, pady=2)

        # ── Scenarios ────────────────────────────────────────────────
        scsec = tk.LabelFrame(parent, text="  Scenarios  ",
                              bg=BG_MID, fg=FG_ACC, font=("Segoe UI", 9, "bold"),
                              relief="groove", bd=1)
        scsec.pack(fill="x", padx=8, pady=4)

        headers = tk.Frame(scsec, bg=BG_MID)
        headers.pack(fill="x", padx=4)
        for txt, w in [("Name", 8), ("Dem×", 5), ("Sup×", 5)]:
            tk.Label(headers, text=txt, bg=BG_MID, fg=FG_ACC,
                     font=("Segoe UI", 8, "bold"), width=w).pack(side="left")

        self._scenario_rows: list = []
        defaults = [("Base", "1.00", "1.00"),
                    ("Upside", "1.20", "1.00"),
                    ("Downside", "0.80", "1.00")]
        for name, dm, sm in defaults:
            row = tk.Frame(scsec, bg=BG_MID)
            row.pack(fill="x", padx=4, pady=1)
            n_var = tk.StringVar(value=name)
            d_var = tk.StringVar(value=dm)
            s_var = tk.StringVar(value=sm)
            for var, w in [(n_var, 8), (d_var, 5), (s_var, 5)]:
                tk.Entry(row, textvariable=var, width=w,
                         bg=BG_LIGHT, fg=FG_WHITE, insertbackground=FG_WHITE,
                         relief="flat", font=("Segoe UI", 9)).pack(side="left", padx=1)
            self._scenario_rows.append((n_var, d_var, s_var))

        # ── Action buttons ───────────────────────────────────────────
        btns = tk.Frame(parent, bg=BG_MID)
        btns.pack(fill="x", padx=8, pady=8)

        tk.Button(btns, text="▶  Run Simulation",
                  command=self._run_simulation,
                  bg=BTN_RUN, fg="white", font=("Segoe UI", 10, "bold"),
                  relief="flat", pady=6).pack(fill="x", pady=(0, 4))

        tk.Button(btns, text="⚙  Run Planning Engine",
                  command=self._run_planning_engine,
                  bg="#7B1FA2", fg="white", font=("Segoe UI", 10, "bold"),
                  relief="flat", pady=6).pack(fill="x", pady=(0, 4))

        tk.Button(btns, text="⬇  Export to Excel",
                  command=self._export_excel,
                  bg=BTN_EXP, fg="white", font=("Segoe UI", 10, "bold"),
                  relief="flat", pady=6).pack(fill="x", pady=(0, 4))

        tk.Button(btns, text="⬇  Export to CSV",
                  command=self._export_csv,
                  bg=BG_LIGHT, fg=FG_WHITE, font=("Segoe UI", 9),
                  relief="flat", pady=5).pack(fill="x")

        # Progress bar
        self._progress = ttk.Progressbar(parent, mode="indeterminate")
        self._progress.pack(fill="x", padx=8, pady=(8, 0))

        # ── Plugin panel ──────────────────────────────────────────────
        self._build_plugin_panel(parent)

    def _build_plugin_panel(self, parent):
        """Build the Plugin ON/OFF checklist below the progress bar."""
        from wom.plugins import ALL_BUILTIN_PLUGINS

        sec = tk.LabelFrame(parent, text=" Plugins ",
                            bg=BG_DARK, fg="#CE93D8",
                            font=("Segoe UI", 9, "bold"),
                            relief="groove", bd=1)
        sec.pack(fill="x", padx=8, pady=(6, 4))

        self._plugin_vars: dict = {}   # name -> BooleanVar
        self._plugin_instances: dict = {}  # name -> WOMPlugin instance

        for cls in ALL_BUILTIN_PLUGINS:
            inst = cls()
            var  = tk.BooleanVar(value=False)
            self._plugin_vars[inst.name]     = var
            self._plugin_instances[inst.name] = inst

            row = tk.Frame(sec, bg=BG_DARK)
            row.pack(fill="x", padx=4, pady=1)
            tk.Checkbutton(row, variable=var, bg=BG_DARK,
                           fg=FG_WHITE, selectcolor=BG_MID,
                           activebackground=BG_DARK,
                           activeforeground=FG_WHITE).pack(side="left")
            tk.Label(row, text=inst.label, bg=BG_DARK, fg=FG_WHITE,
                     font=("Segoe UI", 8), anchor="w").pack(side="left", fill="x")

    def _build_right_panel(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True)

        style = ttk.Style()
        style.configure("TNotebook",       background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab",   background=BG_MID,  foreground=FG_WHITE,
                        font=("Segoe UI", 9), padding=[10, 4])
        style.map("TNotebook.Tab", background=[("selected", BG_LIGHT)])

        self._chart_panel = ChartPanel(nb)
        nb.add(self._chart_panel, text="  \U0001f4c8 Charts  ")

        self._kpi_panel = KPITablePanel(nb)
        nb.add(self._kpi_panel, text="  \U0001f4ca KPI Table  ")

        # At-risk tab
        self._risk_frame = tk.Frame(nb, bg=BG_DARK)
        nb.add(self._risk_frame, text="  ⚠  At-Risk SKUs  ")
        self._build_risk_tab(self._risk_frame)

        # Scenario delta tab
        self._delta_frame = tk.Frame(nb, bg=BG_DARK)
        nb.add(self._delta_frame, text="  Δ  Scenario Delta  ")
        self._build_delta_tab(self._delta_frame)

        self._mgmt_panel = ManagementCockpitPanel(nb)
        nb.add(self._mgmt_panel, text="  \U0001f4b9 Management  ")

        self._network_panel = SCNetworkPanel(nb)
        nb.add(self._network_panel, text="  \U0001f310 Network  ")

        self._worldmap_panel = WorldMapPanel(nb)
        nb.add(self._worldmap_panel, text="  \U0001f5fa World Map  ")

    def _build_risk_tab(self, parent):
        cols = [Cols.SCENARIO, Cols.SKU_ID, Cols.REGION, Cols.WEEK,
                Cols.FILL_RATE, Cols.INV_COVER_WKS, Cols.STOCKOUT_QTY]
        self._risk_tree = ttk.Treeview(parent, columns=cols, show="headings")
        for c in cols:
            self._risk_tree.heading(c, text=c.replace("_", " ").title())
            self._risk_tree.column(c, width=110, anchor="center")
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self._risk_tree.yview)
        self._risk_tree.configure(yscrollcommand=vsb.set)
        self._risk_tree.pack(fill="both", expand=True, side="left")
        vsb.pack(fill="y", side="right")

    def _build_delta_tab(self, parent):
        # Chart: total stockout Base vs others
        self._delta_fig = Figure(figsize=(9, 5), dpi=100, facecolor=BG_DARK)
        self._delta_canvas = FigureCanvasTkAgg(self._delta_fig, master=parent)
        self._delta_canvas.get_tk_widget().pack(fill="both", expand=True)

    # ------------------------------------------------------------------ #
    # Sample data auto-load
    # ------------------------------------------------------------------ #

    def _try_load_sample_paths(self):
        sd = self._sample_dir
        for attr, fname in [
            ("_f_sku",       "sku_master.csv"),
            ("_f_dem",       "demand_forecast.csv"),
            ("_f_inv",       "inventory_master.csv"),
            ("_f_cap",       "capacity_plan.csv"),
            ("_f_node",      "node_master.csv"),
            ("_f_edge_cost", "edge_cost_master.csv"),
            ("_f_route",     "route_master.csv"),
            ("_f_sc_tree",   "sc_tree_master.csv"),
        ]:
            path = os.path.join(sd, fname)
            if os.path.exists(path):
                getattr(self, attr).set(path)

    # ------------------------------------------------------------------ #
    # Simulation
    # ------------------------------------------------------------------ #

    def _build_config(self) -> WOMConfig:
        scenarios = []
        for n_var, d_var, s_var in self._scenario_rows:
            name = n_var.get().strip()
            if not name:
                continue
            try:
                dm = float(d_var.get())
                sm = float(s_var.get())
            except ValueError:
                dm, sm = 1.0, 1.0
            scenarios.append(ScenarioSpec(name, dm, sm))
        return WOMConfig(
            start_week=self._e_start.get() or "2024-W01",
            num_weeks=int(self._e_weeks.get() or 26),
            safety_stock_weeks=float(self._e_ss.get() or 2.0),
            lead_time_weeks=int(self._e_lt.get() or 4),
            capacity_constrained=self._e_cap.get(),
            scenarios=scenarios or [ScenarioSpec("Base")],
        )

    def _run_simulation(self):
        for attr in ("_f_sku", "_f_dem", "_f_inv", "_f_cap"):
            if not getattr(self, attr).get():
                messagebox.showwarning("Missing Files", f"Please select all 4 input files.")
                return
        self._progress.start(10)
        self._status("Running simulation…")
        t = threading.Thread(target=self._simulate_thread, daemon=True)
        t.start()

    def _simulate_thread(self):
        try:
            config = self._build_config()
            inputs = WOMInputs.from_files(
                sku_master_path=self._f_sku.get(),
                demand_forecast_path=self._f_dem.get(),
                inventory_master_path=self._f_inv.get(),
                capacity_plan_path=self._f_cap.get(),
                weeks=config.weeks,
            )
            self._sim = WOMSimulator(config)
            self._sim.load(inputs)
            self._mgr = self._sim.run(verbose=False)
            self.after(0, self._on_simulation_done)
        except Exception as e:
            import traceback
            self.after(0, lambda: self._on_simulation_error(traceback.format_exc()))

    def _on_simulation_done(self):
        self._progress.stop()
        mgr = self._mgr
        combined = mgr.combined()
        avg_fr = combined[Cols.FILL_RATE].mean()
        total_so = combined[Cols.STOCKOUT_QTY].sum()
        # Money KPI for Base scenario
        money_suffix = ""
        if mgr.scenario_money_kpi is not None:
            base_kpi = mgr.scenario_money_kpi
            base_row = base_kpi[base_kpi[Cols.SCENARIO] == mgr.scenarios()[0]]
            if not base_row.empty:
                rev = float(base_row.iloc[0].get(Cols.REVENUE, 0) or 0)
                gm  = float(base_row.iloc[0].get(Cols.GROSS_MARGIN, 0) or 0)
                ccc = float(base_row.iloc[0].get(Cols.CCC_WKS, 0) or 0)
                money_suffix = (f"  |  Revenue: ${rev:,.0f}  "
                                f"|  Margin: {gm*100:.1f}%  |  CCC: {ccc:.1f}w")
        self._status(
            f"✔ Simulation complete.  "
            f"Scenarios: {len(mgr.scenarios())}  |  "
            f"Avg fill rate: {avg_fr:.1%}  |  "
            f"Total stockout: {total_so:,.0f} units"
            + money_suffix
        )
        # Compute Landed Cost comparison (simulation path)
        try:
            from wom.engine.landed_cost import (
                load_edge_cost_master, load_route_master,
                build_route_index, compare_lc_scenarios)
            edge_path  = self._f_edge_cost.get() if hasattr(self, "_f_edge_cost") else ""
            route_path = self._f_route.get()     if hasattr(self, "_f_route")     else ""
            if (edge_path and os.path.exists(edge_path)
                    and mgr.scenario_money_kpi is not None):
                lc_scens  = load_edge_cost_master(edge_path)
                route_idx = {}
                if route_path and os.path.exists(route_path):
                    route_idx = build_route_index(load_route_master(route_path))
                mgr.lc_comparison_df = compare_lc_scenarios(
                    mgr.scenario_money_kpi, lc_scens, route_idx)
            else:
                mgr.lc_comparison_df = None
        except Exception as _lc_exc:
            print(f"[LandedCost] sim compute failed: {_lc_exc}")

        self._chart_panel.load(mgr)
        self._kpi_panel.load(mgr)
        self._load_risk_tab(mgr)
        self._load_delta_tab(mgr)
        self._mgmt_panel.load(mgr)
        self._network_panel.load(mgr)
        # Load node_master into World Map panel
        node_path = self._f_node.get() if hasattr(self, '_f_node') else ""
        if not node_path:
            # fallback to sample
            node_path = os.path.join(self._sample_dir, "node_master.csv")
        if os.path.exists(node_path):
            self._worldmap_panel.load_default(node_path)

    def _on_simulation_error(self, tb: str):
        self._progress.stop()
        self._status("Error – see details in dialog.")
        messagebox.showerror("Simulation Error", tb)

    def _load_risk_tab(self, mgr: ScenarioManager):
        risk = mgr.at_risk_skus()
        self._risk_tree.delete(*self._risk_tree.get_children())
        if risk.empty:
            self._risk_tree.insert("", "end",
                values=["No at-risk SKUs detected"] + [""] * 6)
            return
        for _, row in risk.iterrows():
            self._risk_tree.insert("", "end", values=[
                row.get(Cols.SCENARIO, ""),
                row.get(Cols.SKU_ID, ""),
                row.get(Cols.REGION, ""),
                row.get(Cols.WEEK, ""),
                f"{row.get(Cols.FILL_RATE, 0):.1%}",
                f"{row.get(Cols.INV_COVER_WKS, 0):.1f}",
                f"{row.get(Cols.STOCKOUT_QTY, 0):,.0f}",
            ])

    def _load_delta_tab(self, mgr: ScenarioManager):
        self._delta_fig.clf()
        ax = self._delta_fig.add_subplot(111)
        ax.set_facecolor(BG_MID)
        self._delta_fig.patch.set_facecolor(BG_DARK)

        summary = mgr.kpi_summary(by=[Cols.SCENARIO])
        scenarios = summary[Cols.SCENARIO].tolist()
        fill_rates = (summary["avg_fill_rate"] * 100).tolist()
        stockouts  = summary["total_stockout"].tolist()

        x = range(len(scenarios))
        bars = ax.bar(x, fill_rates, color=[
            COLOURS.get(s, DEFAULT_COLOURS[i % len(DEFAULT_COLOURS)])
            for i, s in enumerate(scenarios)
        ], alpha=0.85)
        ax.set_xticks(list(x))
        ax.set_xticklabels(scenarios, color=FG_WHITE)
        ax.set_ylabel("Avg Fill Rate (%)", color=FG_ACC)
        ax.set_title("Scenario Comparison – Fill Rate vs Stockout",
                     color=FG_WHITE, fontsize=11)
        ax.set_ylim(0, 105)
        ax.tick_params(colors=FG_WHITE)
        for spine in ax.spines.values():
            spine.set_edgecolor(BG_LIGHT)

        # Annotate with stockout on second axis
        ax2 = ax.twinx()
        ax2.plot(list(x), stockouts, "o--", color="#FF9800",
                 linewidth=2, markersize=8, label="Total Stockout")
        ax2.set_ylabel("Total Stockout (units)", color="#FF9800")
        ax2.tick_params(colors=FG_WHITE)
        ax2.set_facecolor(BG_MID)

        ax2.legend(facecolor=BG_LIGHT, labelcolor=FG_WHITE, fontsize=9,
                   loc="upper right")
        self._delta_canvas.draw()

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    # Planning Engine (lot-based PSI, Steps 3-8)
    # ------------------------------------------------------------------ #

    def _run_planning_engine(self):
        """Build SCTree from input files (or demo data) and run the lot-based planning pipeline."""
        self._progress.start(10)
        self._status("Running Planning Engine (lot-based PSI)…")
        # Build list of active (checked) plugin instances
        self._active_plugins = [
            inst for name, inst in getattr(self, '_plugin_instances', {}).items()
            if self._plugin_vars.get(name, tk.BooleanVar(value=False)).get()
        ]
        threading.Thread(target=self._planning_thread, daemon=True).start()

    def _planning_thread(self):
        try:
            import re
            import datetime
            from wom.model.sc_tree       import build_demo_sc_tree
            from wom.model.lot_generator import assign_demand_lots_from_dict
            from wom.engine.backward_planner import BackwardPlanner
            from wom.engine.plan_copy        import copy_demand_to_supply
            from wom.engine.forward_planner  import ForwardPlanner
            from wom.engine.hook_bus         import (HookBus,
                HOOK_PRE_PLAN, HOOK_POST_BACKWARD,
                HOOK_POST_COPY, HOOK_POST_FORWARD, HOOK_POST_PLAN)

            # ── Build week labels ──────────────────────────────────
            n_weeks = int(self._e_weeks.get() or 26)
            start   = self._e_start.get() or "2024-W01"
            m = re.match(r"(\d{4})-W(\d+)", start)
            yr, wk = (int(m.group(1)), int(m.group(2))) if m else (2024, 1)
            weeks, d = [], datetime.date.fromisocalendar(yr, wk, 1)
            for _ in range(n_weeks):
                yr2, wk2, _ = d.isocalendar()
                weeks.append(f"{yr2}-W{wk2:02d}")
                d += datetime.timedelta(weeks=1)

            # ── SKU master ─────────────────────────────────────────
            sku_path = self._f_sku.get()
            if sku_path and os.path.exists(sku_path):
                sku_df = pd.read_csv(sku_path)
            else:
                sku_df = pd.DataFrame([
                    {"sku_id": "SKU-A", "sku_name": "Product A",
                     "region": "JP", "lead_time_wks": 2},
                    {"sku_id": "SKU-A", "sku_name": "Product A",
                     "region": "US", "lead_time_wks": 2},
                ])
            if "lead_time_wks" not in sku_df.columns:
                sku_df["lead_time_wks"] = 2

            # ── SC Tree: multi-tier master or demo fallback ────────────
            sc_tree_path = (self._f_sc_tree.get()
                            if hasattr(self, "_f_sc_tree") else "")
            if sc_tree_path and os.path.exists(sc_tree_path):
                try:
                    from wom.engine.sc_tree_builder import build_sc_tree_from_master
                    sc_tree_df = pd.read_csv(sc_tree_path)
                    sc_tree = build_sc_tree_from_master(sc_tree_df, weeks)
                    print(f"[SCTreeBuilder] Loaded multi-tier tree from {sc_tree_path}")
                    print(f"  Products: {sc_tree.products}")
                except Exception as _stb_exc:
                    import traceback
                    print(f"[SCTreeBuilder] Failed: {_stb_exc}")
                    traceback.print_exc()
                    sc_tree = build_demo_sc_tree(sku_df, weeks,
                                                 lt_wks_ot=1, lt_wks_in=2)
            else:
                sc_tree = build_demo_sc_tree(sku_df, weeks,
                                             lt_wks_ot=1, lt_wks_in=2)

            # ── Build HookBus and register active plugins ──────────────
            _bus = HookBus()
            _cfg = {"n_weeks": n_weeks, "start_week": start,
                    "cap_path": self._f_cap.get() if hasattr(self, '_f_cap') else ""}
            for _plugin in getattr(self, '_active_plugins', []):
                _plugin.register(_bus)

            # ── Demand ─────────────────────────────────────────────
            demand_dict = {}
            dem_path = self._f_dem.get()
            if dem_path and os.path.exists(dem_path):
                dem_df = pd.read_csv(dem_path)
                req    = {"sku_id", "region", "week", "quantity"}
                if req.issubset(set(dem_df.columns)):
                    for _, row in dem_df.iterrows():
                        key = (str(row["sku_id"]),
                               str(row["region"]),
                               str(row["week"]))
                        demand_dict[key] = (demand_dict.get(key, 0)
                                            + int(row["quantity"]))

            if not demand_dict:
                # Demo demand: 5 lots mid-horizon for each region
                mid = weeks[len(weeks) // 2]
                for sku_id in sc_tree.products:
                    for reg in set(sku_df.get("region", pd.Series(["JP"])).tolist()):
                        demand_dict[(sku_id, reg, mid)] = 5

            assign_demand_lots_from_dict(sc_tree, demand_dict, cpu_size=1)

            # ── Apply capacity from CSV → MOM nodes (cap_hard) ───
            cap_path = self._f_cap.get()
            if cap_path and os.path.exists(cap_path):
                try:
                    cap_df = pd.read_csv(cap_path)
                    req_cap = {"sku_id", "week", "max_supply"}
                    if req_cap.issubset(set(cap_df.columns)):
                        # Sum max_supply across regions → total MOM production cap
                        cap_agg = (cap_df
                                   .groupby(["sku_id", "week"])["max_supply"]
                                   .sum().reset_index())
                        week_idx_map = {wk: i for i, wk in enumerate(weeks)}
                        for prod_nm in sc_tree.products:
                            try:
                                mom = sc_tree.get_in_root(prod_nm)
                                sku_cap = cap_agg[
                                    cap_agg["sku_id"] == prod_nm
                                ]
                                for _, row in sku_cap.iterrows():
                                    w_idx = week_idx_map.get(str(row["week"]))
                                    if w_idx is not None:
                                        mom.set_capacity(
                                            w_idx,
                                            cap_hard=float(row["max_supply"]))
                            except Exception:
                                pass
                except Exception:
                    pass   # capacity load failure is non-fatal

            # ── Run planning pipeline ─────────────────────────────
            _bus.fire(HOOK_PRE_PLAN, sc_tree=sc_tree,
                      weeks=weeks, config=_cfg)
            for prod_nm in sc_tree.products:
                BackwardPlanner(sc_tree).run(prod_nm)
                _bus.fire(HOOK_POST_BACKWARD, sc_tree=sc_tree,
                          prod_nm=prod_nm, weeks=weeks, config=_cfg)
                copy_demand_to_supply(sc_tree, prod_nm)
                _bus.fire(HOOK_POST_COPY, sc_tree=sc_tree,
                          prod_nm=prod_nm, weeks=weeks, config=_cfg)
                ForwardPlanner(sc_tree).run(prod_nm)
                _bus.fire(HOOK_POST_FORWARD, sc_tree=sc_tree,
                          prod_nm=prod_nm, weeks=weeks, config=_cfg)

            _bus.fire(HOOK_POST_PLAN, sc_tree=sc_tree,
                      weeks=weeks, config=_cfg)
            self.after(0, lambda: self._on_planning_done(sc_tree))

        except Exception:
            import traceback
            tb = traceback.format_exc()
            self.after(0, lambda: self._on_planning_error(tb))

    def _on_planning_done(self, sc_tree):
        self._progress.stop()
        n_prods = len(sc_tree.products)
        n_nodes = sum(1 for p in sc_tree.products
                      for _ in sc_tree.iter_all_nodes(p))

        self._network_panel.load_planning_tree(sc_tree)

        # -- Build EventTimeline for animation
        try:
            from wom.engine.event_timeline import build_event_timeline
            timeline = build_event_timeline(sc_tree)
            self._network_panel.set_timeline(timeline)
            self._worldmap_panel.set_timeline(timeline)
        except Exception as exc:
            import traceback
            print(f"[EventTimeline] build failed: {exc}")
            traceback.print_exc()

        # -- Load node_master into World Map (same logic as _on_simulation_done)
        try:
            node_path = self._f_node.get() if hasattr(self, "_f_node") else ""
            if not node_path:
                node_path = os.path.join(self._sample_dir, "node_master.csv")
            if os.path.exists(node_path):
                self._worldmap_panel.load_default(node_path)
        except Exception as _wm_exc:
            print(f"[WorldMap] node load failed: {_wm_exc}")

        # -- Integrate Planning results into KPI/Management tabs
        planning_status = ""
        try:
            from wom.engine.sc_tree_to_df import (
                sc_tree_to_planning_df, apply_inv_value, SCENARIO_PLANNING)
            from wom.engine.money import evaluate_money, build_scenario_money_kpi
            from wom.engine.management import analyze_all_scenarios
            from wom.engine.scenario import ScenarioManager

            # Load sku_master for pricing
            sku_path = self._f_sku.get() if hasattr(self, "_f_sku") else ""
            sku_master = (pd.read_csv(sku_path)
                          if sku_path and os.path.exists(sku_path)
                          else pd.DataFrame())

            # Convert SCTree lots -> quantity DataFrame
            plan_df = sc_tree_to_planning_df(sc_tree,
                                             scenario_name=SCENARIO_PLANNING)
            apply_inv_value(plan_df, sku_master)

            # Merge into existing ScenarioManager (or create one)
            if self._mgr is None:
                self._mgr = ScenarioManager()

            # Remove stale Planning scenario if re-running
            self._mgr._results.pop(SCENARIO_PLANNING, None)
            self._mgr.add(SCENARIO_PLANNING, plan_df)

            # Re-evaluate money KPIs across ALL scenarios
            combined = self._mgr.combined()
            weekly_money, summary_money = evaluate_money(combined, sku_master)
            self._mgr.weekly_money  = weekly_money
            self._mgr.summary_money = summary_money
            scenario_money_kpi = build_scenario_money_kpi(summary_money)
            self._mgr.scenario_money_kpi = scenario_money_kpi

            # Re-run management analysis (only if Base scenario exists)
            if "Base" in self._mgr.scenarios():
                mgmt_results = analyze_all_scenarios(scenario_money_kpi,
                                                     base_scenario="Base")
                self._mgr.management_results = mgmt_results

            # Compute Strategic KPIs from SCTree lots
            try:
                from wom.engine.strategic_kpi import compute_strategic_kpi
                self._mgr.strategic_kpi = compute_strategic_kpi(sc_tree)
            except Exception as _skpi_exc:
                import traceback
                print(f"[StrategicKPI] compute failed: {_skpi_exc}")
                traceback.print_exc()

            # Compute Landed Cost comparison
            try:
                from wom.engine.landed_cost import (
                    load_edge_cost_master, load_route_master,
                    build_route_index, compare_lc_scenarios)
                edge_path  = self._f_edge_cost.get() if hasattr(self, "_f_edge_cost") else ""
                route_path = self._f_route.get()     if hasattr(self, "_f_route")     else ""
                if edge_path and os.path.exists(edge_path):
                    lc_scens = load_edge_cost_master(edge_path)
                    route_idx = {}
                    if route_path and os.path.exists(route_path):
                        route_idx = build_route_index(load_route_master(route_path))
                    self._mgr.lc_comparison_df = compare_lc_scenarios(
                        scenario_money_kpi, lc_scens, route_idx)
                else:
                    self._mgr.lc_comparison_df = None
            except Exception as _lc_exc:
                print(f"[LandedCost] compute failed: {_lc_exc}")

            # Reload all KPI panels
            self._chart_panel.load(self._mgr)
            self._kpi_panel.load(self._mgr)
            self._load_risk_tab(self._mgr)
            self._load_delta_tab(self._mgr)
            self._mgmt_panel.load(self._mgr)
            self._network_panel.load(self._mgr)

            # Build status summary for Planning scenario
            p_rows = plan_df
            avg_fr = p_rows[Cols.FILL_RATE].mean() if not p_rows.empty else 0
            total_so = p_rows[Cols.STOCKOUT_QTY].sum() if not p_rows.empty else 0
            planning_status = (f"  |  Planning: fill {avg_fr:.1%}, "
                               f"stockout {total_so:,.0f}")

        except Exception as exc:
            import traceback
            tb = traceback.format_exc()
            print(f"[Planning->KPI] integration failed: {exc}")
            print(tb)
            planning_status = "  |  Warning: KPI integration error (see console)"

        self._status(
            f"Planning Engine complete. "
            f"Products: {n_prods}  |  Nodes: {n_nodes}"
            + planning_status +
            f"  |  Check Charts/KPI/Management tabs for 'Planning' scenario"
        )

    def _on_planning_error(self, tb: str):
        self._progress.stop()
        self._status_var.set("Planning Engine failed -- see console")
        import tkinter.messagebox as _mb
        _mb.showerror("Planning Engine Error",
                      f"Planning Engine failed:\n\n{tb[:1200]}")

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #

    def _export_csv(self):
        if not self._mgr:
            import tkinter.messagebox as _mb
            _mb.showinfo("No Results", "Run the simulation first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Results to CSV",
        )
        if not path:
            return
        try:
            self._mgr.combined().to_csv(path, index=False)
            self._status_var.set(f"Exported: {path}")
        except Exception as exc:
            import tkinter.messagebox as _mb
            _mb.showerror("Export Error", str(exc))

    def _export_excel(self):
        if not self._mgr:
            import tkinter.messagebox as _mb
            _mb.showinfo("No Results", "Run the simulation first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            title="Export to Excel",
        )
        if not path:
            return
        try:
            from wom.reports.output import write_excel
            out_dir = os.path.dirname(path)
            out_path = write_excel(self._mgr, out_dir)
            self._status_var.set(f"Excel exported: {out_path}")
        except Exception as exc:
            import tkinter.messagebox as _mb
            _mb.showerror("Export Error", str(exc))

    # Status helper
    # ------------------------------------------------------------------ #

    def _status(self, msg: str) -> None:
        self._status_var.set(msg)

# ======================================================================
# Entry point
# ======================================================================
def launch():
    """Entry point called by main.py."""
    WOMApp().mainloop()

# =======================================
