"""
WOM Landed Cost Engine  —  Phase 1
===================================

Adds tariff_rate and FX adjustment to per-route cost calculation.
Enables Trump-tariff / KD-production / reroute scenario comparison
without changing the underlying lot-based planning model.

Calculation model
-----------------
For each (sku_id × region) row in the money KPI:

  1. Look up RouteProfile for (src_region, dst_region) in the chosen scenario.
  2. Apply tariff:
       customs_duty  = COGS × tariff_rate
       (tariff is applied to the CIF cost value of goods at the border)
  3. Apply FX:
       fx_adj_revenue  = revenue  × fx_rate   (home→report currency)
       fx_adj_cogs     = cogs     × fx_rate
       fx_adj_duty     = customs_duty × fx_rate
  4. Add freight:
       freight_total = freight_usd_per_lot × lot_count × fx_rate
  5. Add KD assembly cost (if product_type == "parts"):
       assembly_total = assembly_cost_usd_per_lot × lot_count
  6. Landed Gross Profit:
       landed_gp   = fx_adj_revenue - fx_adj_cogs - fx_adj_duty
                     - freight_total - assembly_total
       landed_gm   = landed_gp / fx_adj_revenue  (if revenue > 0)
  7. Tariff burden %:
       tariff_burden_pct = fx_adj_duty / fx_adj_revenue

Limitations (Phase 1)
---------------------
- Lot count is approximated as demand_fulfilled / cpu_size (default 1)
- Transfer pricing is not modelled (Phase 3)
- CIF vs FOB distinction is simplified to freight included in COGS
- Intra-company elimination is not applied (Phase 3)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# ──────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────

@dataclass
class RouteProfile:
    """Cost parameters for one (src_region, dst_region) lane."""
    src_region: str
    dst_region: str
    tariff_rate: float = 0.0          # 0–1  (e.g., 0.25 = 25 %)
    fx_rate: float = 1.0              # reporting_ccy per trade_ccy
    src_currency: str = "USD"
    dst_currency: str = "USD"
    freight_usd_per_lot: float = 0.0  # flat freight cost per lot
    notes: str = ""


@dataclass
class LandedCostScenario:
    """Named set of RouteProfiles."""
    name: str
    profiles: List[RouteProfile] = field(default_factory=list)

    def get_profile(
        self, src_region: str, dst_region: str
    ) -> Optional[RouteProfile]:
        """Return the first matching RouteProfile, or None."""
        for p in self.profiles:
            if p.src_region == src_region and p.dst_region == dst_region:
                return p
        return None


@dataclass
class RouteAssignment:
    """Maps (sku_id, region) → (src_region, dst_region, hs_code, assembly_cost)."""
    sku_id: str
    region: str
    src_region: str
    dst_region: str
    hs_code: str = ""
    product_type: str = "finished_goods"  # "finished_goods" | "parts"
    assembly_cost_usd_per_lot: float = 0.0


# ──────────────────────────────────────────────────────────────────────
# Loaders
# ──────────────────────────────────────────────────────────────────────

def load_edge_cost_master(path: str) -> Dict[str, LandedCostScenario]:
    """
    Load edge_cost_master.csv into a dict of LandedCostScenario.

    CSV columns:
        scenario, src_region, dst_region, tariff_rate, fx_rate,
        src_currency, dst_currency, freight_usd_per_lot, [notes]
    """
    df = pd.read_csv(path)
    scenarios: Dict[str, LandedCostScenario] = {}

    for _, row in df.iterrows():
        scen_name = str(row["scenario"])
        if scen_name not in scenarios:
            scenarios[scen_name] = LandedCostScenario(name=scen_name)
        profile = RouteProfile(
            src_region=str(row["src_region"]),
            dst_region=str(row["dst_region"]),
            tariff_rate=float(row.get("tariff_rate", 0.0) or 0.0),
            fx_rate=float(row.get("fx_rate", 1.0) or 1.0),
            src_currency=str(row.get("src_currency", "USD") or "USD"),
            dst_currency=str(row.get("dst_currency", "USD") or "USD"),
            freight_usd_per_lot=float(row.get("freight_usd_per_lot", 0.0) or 0.0),
            notes=str(row.get("notes", "") or ""),
        )
        scenarios[scen_name].profiles.append(profile)

    return scenarios


def load_route_master(path: str) -> List[RouteAssignment]:
    """
    Load route_master.csv into a list of RouteAssignment.

    CSV columns:
        sku_id, region, src_region, dst_region, hs_code,
        product_type, assembly_cost_usd_per_lot
    """
    df = pd.read_csv(path)
    assignments = []
    for _, row in df.iterrows():
        assignments.append(RouteAssignment(
            sku_id=str(row["sku_id"]),
            region=str(row["region"]),
            src_region=str(row["src_region"]),
            dst_region=str(row["dst_region"]),
            hs_code=str(row.get("hs_code", "") or ""),
            product_type=str(row.get("product_type", "finished_goods") or "finished_goods"),
            assembly_cost_usd_per_lot=float(row.get("assembly_cost_usd_per_lot", 0.0) or 0.0),
        ))
    return assignments


def build_route_index(
    assignments: List[RouteAssignment],
) -> Dict[Tuple[str, str], RouteAssignment]:
    """Build (sku_id, region) → RouteAssignment lookup dict."""
    return {(a.sku_id, a.region): a for a in assignments}


# ──────────────────────────────────────────────────────────────────────
# Core calculation
# ──────────────────────────────────────────────────────────────────────

def compute_landed_cost_kpi(
    scenario_money_kpi: pd.DataFrame,
    lc_scenario: LandedCostScenario,
    route_index: Dict[Tuple[str, str], RouteAssignment],
    cpu_size_default: float = 1.0,
) -> pd.DataFrame:
    """
    Compute landed-cost-adjusted KPIs for one LandedCostScenario.

    Parameters
    ----------
    scenario_money_kpi : output of build_scenario_money_kpi()
        One row per WOM scenario with revenue, cogs, gross_profit,
        gross_margin, inv_value, ar_value, ap_value, ccc_wks.
    lc_scenario : LandedCostScenario to apply.
    route_index : (sku_id, region) → RouteAssignment mapping.
    cpu_size_default : lots per unit (default 1).

    Returns
    -------
    DataFrame with columns:
        wom_scenario, lc_scenario,
        revenue, cogs, customs_duty, freight_total, assembly_total,
        landed_cogs, landed_gross_profit, landed_gross_margin,
        tariff_burden_pct, fx_gain_loss,
        [all values in reporting currency USD]
    """
    rows = []

    for _, kpi_row in scenario_money_kpi.iterrows():
        wom_scen = kpi_row.get("scenario", "")
        revenue  = float(kpi_row.get("revenue", 0) or 0)
        cogs     = float(kpi_row.get("cogs",    0) or 0)
        gp       = float(kpi_row.get("gross_profit", 0) or 0)

        # Aggregate tariff / freight across all routes that contributed
        # to this WOM scenario.  We use COGS as a proxy for trade value.
        # Split COGS proportionally across routes using route_index keys.
        # (Simplified: apply a blended rate across all registered routes)

        # Collect all routes in this LC scenario
        profiles = lc_scenario.profiles
        if not profiles:
            # No route data → return unadjusted
            rows.append(_no_adjustment_row(wom_scen, lc_scenario.name,
                                           revenue, cogs, gp))
            continue

        # Blended tariff / FX across routes (weighted equally — Phase 1 simplification)
        # In Phase 2, weight by SKU×region volume
        n = len(profiles)
        blended_tariff = sum(p.tariff_rate for p in profiles) / n
        blended_fx     = sum(p.fx_rate     for p in profiles) / n
        blended_freight_per_lot = sum(p.freight_usd_per_lot for p in profiles) / n

        # Estimate lot count from COGS (proxy: cogs / avg_unit_cost=100 as fallback)
        # Better: pass actual lot counts; for Phase 1 we use revenue as proxy
        estimated_lots = max(revenue / 1000.0, 1.0)  # rough proxy

        # Compute adjustments
        customs_duty   = cogs * blended_tariff
        freight_total  = blended_freight_per_lot * estimated_lots
        # Assembly cost: sum from route assignments if product_type=="parts"
        assembly_total = 0.0
        for ra in route_index.values():
            if ra.assembly_cost_usd_per_lot > 0:
                assembly_total += ra.assembly_cost_usd_per_lot * (estimated_lots / max(len(route_index), 1))

        # FX adjustment (revenue / cogs are already in reporting ccy in WOM model;
        # here fx_rate represents any residual FX exposure)
        # Phase 1: fx_gain_loss = (1 - blended_fx) × cogs  (if fx_rate ≠ 1.0)
        fx_gain_loss   = (blended_fx - 1.0) * cogs

        landed_cogs = cogs + customs_duty + freight_total + assembly_total - fx_gain_loss
        landed_gp   = revenue - landed_cogs
        landed_gm   = landed_gp / revenue if revenue > 0 else 0.0
        tariff_burden_pct = customs_duty / revenue if revenue > 0 else 0.0

        rows.append({
            "wom_scenario":       wom_scen,
            "lc_scenario":        lc_scenario.name,
            "revenue":            round(revenue, 0),
            "cogs":               round(cogs, 0),
            "customs_duty":       round(customs_duty, 0),
            "freight_total":      round(freight_total, 0),
            "assembly_total":     round(assembly_total, 0),
            "fx_gain_loss":       round(fx_gain_loss, 0),
            "landed_cogs":        round(landed_cogs, 0),
            "landed_gross_profit":round(landed_gp, 0),
            "landed_gross_margin":round(landed_gm, 4),
            "tariff_burden_pct":  round(tariff_burden_pct, 4),
            "original_gross_margin": round(float(kpi_row.get("gross_margin", 0) or 0), 4),
            "margin_impact_pp":   round(landed_gm - float(kpi_row.get("gross_margin", 0) or 0), 4),
        })

    return pd.DataFrame(rows)


def _no_adjustment_row(wom_scen, lc_scen, revenue, cogs, gp):
    gm = gp / revenue if revenue > 0 else 0.0
    return {
        "wom_scenario": wom_scen, "lc_scenario": lc_scen,
        "revenue": revenue, "cogs": cogs,
        "customs_duty": 0, "freight_total": 0,
        "assembly_total": 0, "fx_gain_loss": 0,
        "landed_cogs": cogs, "landed_gross_profit": gp,
        "landed_gross_margin": gm, "tariff_burden_pct": 0,
        "original_gross_margin": gm, "margin_impact_pp": 0,
    }


# ──────────────────────────────────────────────────────────────────────
# Scenario comparison
# ──────────────────────────────────────────────────────────────────────

def compare_lc_scenarios(
    scenario_money_kpi: pd.DataFrame,
    lc_scenarios: Dict[str, LandedCostScenario],
    route_index: Dict[Tuple[str, str], RouteAssignment],
    cpu_size_default: float = 1.0,
) -> pd.DataFrame:
    """
    Run compute_landed_cost_kpi for all LC scenarios and stack results.

    Returns a DataFrame with one row per (wom_scenario × lc_scenario).
    """
    frames = []
    for lc_name, lc_scen in lc_scenarios.items():
        df = compute_landed_cost_kpi(
            scenario_money_kpi, lc_scen, route_index, cpu_size_default
        )
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# ──────────────────────────────────────────────────────────────────────
# Narrative builder
# ──────────────────────────────────────────────────────────────────────

def build_lc_narrative(comparison_df: pd.DataFrame,
                       base_lc: str = "Base") -> str:
    """Build Japanese executive summary of landed cost scenario comparison."""
    lines = ["【Landed Cost シナリオ分析サマリー】\n"]

    base_rows = comparison_df[comparison_df["lc_scenario"] == base_lc]
    if base_rows.empty:
        return "（Base シナリオデータなし）"

    base_gm  = base_rows["landed_gross_margin"].mean()
    base_rev = base_rows["revenue"].sum()

    for lc_scen in comparison_df["lc_scenario"].unique():
        if lc_scen == base_lc:
            continue
        scen_rows = comparison_df[comparison_df["lc_scenario"] == lc_scen]
        scen_gm   = scen_rows["landed_gross_margin"].mean()
        scen_duty = scen_rows["customs_duty"].sum()
        scen_rev  = scen_rows["revenue"].sum()
        margin_chg = (scen_gm - base_gm) * 100
        duty_pct   = scen_duty / scen_rev * 100 if scen_rev > 0 else 0

        icon = "🔴" if margin_chg < -2 else ("🟡" if margin_chg < 0 else "🟢")
        lines.append(
            f"{icon} [{lc_scen}]  粗利率変化: {margin_chg:+.1f}pp  "
            f"| 関税負担: {duty_pct:.1f}%  "
            f"| 関税額合計: ${scen_duty:,.0f}"
        )

    lines.append("\n（関税・為替シナリオは Planning Engine 実行後に更新されます）")
    return "\n".join(lines)
