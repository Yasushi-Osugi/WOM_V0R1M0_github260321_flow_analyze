"""Load cost master dictionaries and optional bundle for reporting MVP + inbound extension.

This version keeps backward compatibility with the current dict-based MVP while
adding a lightweight CostMasterBundle and inbound CSV loading.

Main ideas:
- CSV remains source of truth
- pandas/SQL are NOT required; loader uses csv.DictReader
- engine can keep consuming plain dict payloads
- bundle keeps raw rows + in-memory lookups for future extension
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ----------------------------------------------------------------------
# Bundle
# ----------------------------------------------------------------------

@dataclass
class CostMasterBundle:
    # ---- current outbound / reporting MVP raw rows ----
    product_rows: list[dict[str, Any]] = field(default_factory=list)
    node_rows: list[dict[str, Any]] = field(default_factory=list)
    lane_rows: list[dict[str, Any]] = field(default_factory=list)
    sales_price_rows: list[dict[str, Any]] = field(default_factory=list)
    allocation_rule_rows: list[dict[str, Any]] = field(default_factory=list)
    market_rows: list[dict[str, Any]] = field(default_factory=list)
    cs_node_to_market_rows: list[dict[str, Any]] = field(default_factory=list)
    sga_rows: list[dict[str, Any]] = field(default_factory=list)
    fixed_asset_rows: list[dict[str, Any]] = field(default_factory=list)

    # ---- inbound raw rows ----
    inbound_item_rows: list[dict[str, Any]] = field(default_factory=list)
    inbound_bom_rows: list[dict[str, Any]] = field(default_factory=list)
    inbound_price_decision_rows: list[dict[str, Any]] = field(default_factory=list)
    inbound_adjustment_rows: list[dict[str, Any]] = field(default_factory=list)

    # ---- current MVP lookups used directly by engines/reporting ----
    node_cost_rates: dict[str, dict[str, float]] = field(default_factory=dict)
    lane_cost_rates: dict[str, dict[str, float]] = field(default_factory=dict)
    market_cost_rates: dict[str, dict[str, float]] = field(default_factory=dict)
    allocation_rules: list[dict[str, Any]] = field(default_factory=list)

    # ---- additional outbound/helper lookups ----
    product_cost_lookup: dict[str, dict[str, Any]] = field(default_factory=dict)
    sales_price_lookup: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    market_entity_lookup: dict[str, dict[str, Any]] = field(default_factory=dict)
    cs_node_to_market_lookup: dict[tuple[str, Optional[str]], str] = field(default_factory=dict)
    node_lookup: dict[str, dict[str, Any]] = field(default_factory=dict)
    lane_lookup: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    sga_lookup: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    fixed_asset_lookup: dict[tuple[str, str], list[dict[str, Any]]] = field(default_factory=dict)

    # ---- inbound lookups ----
    inbound_item_lookup: dict[str, dict[str, Any]] = field(default_factory=dict)
    inbound_bom_by_parent: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    inbound_price_decision_lookup: dict[tuple[str, str, str], list[dict[str, Any]]] = field(default_factory=dict)
    inbound_adjustment_by_product: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    inbound_adjustment_by_item: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    # ---- meta ----
    source_dir: str | None = None

    def to_legacy_payload(self) -> dict[str, Any]:
        """Return current dict-style payload while preserving extra sections.

        Existing callers can continue to use:
        - node_cost_rates
        - lane_cost_rates
        - market_cost_rates
        - allocation_rules

        New callers can also use the extra keys gradually.
        """
        return {
            # current MVP keys
            "node_cost_rates": self.node_cost_rates,
            "lane_cost_rates": self.lane_cost_rates,
            "market_cost_rates": self.market_cost_rates,
            "allocation_rules": self.allocation_rules,

            # useful extra rows / lookups
            "product_rows": self.product_rows,
            "node_rows": self.node_rows,
            "lane_rows": self.lane_rows,
            "sales_price_rows": self.sales_price_rows,
            "allocation_rule_rows": self.allocation_rule_rows,
            "market_rows": self.market_rows,
            "cs_node_to_market_rows": self.cs_node_to_market_rows,
            "sga_rows": self.sga_rows,
            "fixed_asset_rows": self.fixed_asset_rows,

            "product_cost_lookup": self.product_cost_lookup,
            "sales_price_lookup": self.sales_price_lookup,
            "market_entity_lookup": self.market_entity_lookup,
            "cs_node_to_market_lookup": self.cs_node_to_market_lookup,
            "node_lookup": self.node_lookup,
            "lane_lookup": self.lane_lookup,
            "sga_lookup": self.sga_lookup,
            "fixed_asset_lookup": self.fixed_asset_lookup,

            # inbound extension
            "inbound_item_rows": self.inbound_item_rows,
            "inbound_bom_rows": self.inbound_bom_rows,
            "inbound_price_decision_rows": self.inbound_price_decision_rows,
            "inbound_adjustment_rows": self.inbound_adjustment_rows,
            "inbound_item_lookup": self.inbound_item_lookup,
            "inbound_bom_by_parent": self.inbound_bom_by_parent,
            "inbound_price_decision_lookup": self.inbound_price_decision_lookup,
            "inbound_adjustment_by_product": self.inbound_adjustment_by_product,
            "inbound_adjustment_by_item": self.inbound_adjustment_by_item,

            "meta": {
                "source_dir": self.source_dir,
                "has_inbound": bool(
                    self.inbound_item_rows
                    or self.inbound_bom_rows
                    or self.inbound_price_decision_rows
                    or self.inbound_adjustment_rows
                ),
            },
        }


# ----------------------------------------------------------------------
# Base helpers
# ----------------------------------------------------------------------

def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fp:
        return list(csv.DictReader(fp))


def _to_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def _truthy(value: Any) -> bool:
    s = str(value or "").strip().lower()
    return s in {"1", "true", "yes", "y", "on"}


def _safe_key(value: Any) -> str:
    return str(value or "").strip()


def _sample_cost_masters() -> dict[str, Any]:
    return {
        "node_cost_rates": {
            "factory_a": {
                "production": 12.0,
                "inventory": 0.8,
                "sga": 1.5,
                "depreciation": 0.5,
            },
            "dc_japan": {
                "production": 0.0,
                "inventory": 0.9,
                "sga": 1.2,
                "depreciation": 0.3,
            },
        },
        "lane_cost_rates": {
            "factory_a->dc_japan": {
                "logistics": 2.5,
                "tariff": 0.3,
                "insurance": 0.2,
            }
        },
        "market_cost_rates": {
            "jp": {"sales": 3.0, "promotion": 1.2, "rebate": 0.4},
        },
        "allocation_rules": [
            {
                "name": "factory_to_market_by_sales",
                "driver": "sales_units",
                "from_dim": "node",
                "to_dim": "market",
                "from_key": "factory_a",
                "pool_categories": ["production", "sga", "depreciation"],
            }
        ],
    }


# ----------------------------------------------------------------------
# Outbound/current-model loader
# ----------------------------------------------------------------------

def _build_outbound_bundle(base_dir: Path) -> CostMasterBundle:
    bundle = CostMasterBundle(source_dir=str(base_dir))

    bundle.product_rows = _read_csv_rows(base_dir / "product_cost_master.csv")
    bundle.node_rows = _read_csv_rows(base_dir / "node_cost_master.csv")
    bundle.lane_rows = _read_csv_rows(base_dir / "lane_cost_master.csv")
    bundle.sales_price_rows = _read_csv_rows(base_dir / "sales_price_master.csv")
    bundle.allocation_rule_rows = _read_csv_rows(base_dir / "allocation_rule_master.csv")
    bundle.market_rows = _read_csv_rows(base_dir / "market_master.csv")
    bundle.cs_node_to_market_rows = _read_csv_rows(base_dir / "cs_node_to_market_map.csv")
    bundle.sga_rows = _read_csv_rows(base_dir / "sga_marketing_tax_master.csv")
    bundle.fixed_asset_rows = _read_csv_rows(base_dir / "fixed_asset_cost_master.csv")

    # ---- product lookup ----
    for row in bundle.product_rows:
        product_id = _safe_key(row.get("product_id") or row.get("product_name"))
        if product_id:
            bundle.product_cost_lookup[product_id] = row

    # ---- node lookup / current MVP node rates ----
    for row in bundle.node_rows:
        node_id = _safe_key(row.get("node_id") or row.get("node_name"))
        if not node_id:
            continue

        bundle.node_lookup[node_id] = row
        bundle.node_cost_rates[node_id] = {
            "production": _to_float(row.get("production_variable_cost_rate")),
            "inventory": _to_float(row.get("inventory_holding_cost_rate")),
            "sga": _to_float(row.get("local_sga_variable_cost_rate")),
            "depreciation": _to_float(row.get("depreciation_cost_per_period")),
            # kept for future extensions; current cost_engine ignores extras
            "warehouse_handling": _to_float(row.get("warehouse_handling_cost_rate")),
            "direct_labor": _to_float(row.get("direct_labor_cost_rate")),
            "machine": _to_float(row.get("machine_cost_rate")),
            "utility": _to_float(row.get("utility_cost_rate")),
            "maintenance": _to_float(row.get("maintenance_fixed_cost")),
            "overtime": _to_float(row.get("overtime_cost_rate")),
            "scrap_loss": _to_float(row.get("scrap_loss_cost_rate")),
        }

    # ---- lane lookup / current MVP lane rates ----
    for row in bundle.lane_rows:
        from_node = _safe_key(row.get("from_node_id"))
        to_node = _safe_key(row.get("to_node_id"))
        if not from_node or not to_node:
            continue

        lane_key = (from_node, to_node)
        lane_str = f"{from_node}->{to_node}"
        bundle.lane_lookup[lane_key] = row
        bundle.lane_cost_rates[lane_str] = {
            "logistics": _to_float(row.get("freight_cost_per_unit")),
            "tariff": _to_float(row.get("tariff_rate")),
            "insurance": _to_float(row.get("insurance_cost_per_unit")),
            "customs": _to_float(row.get("customs_cost_per_unit")),
            "carbon": _to_float(row.get("carbon_cost_per_unit")),
            # future-facing extras
            "lane_fixed": _to_float(row.get("lane_fixed_cost_per_period")),
            "special_risk": _to_float(row.get("special_risk_cost_rate")),
        }

    # ---- sales price rows -> lookups and current MVP market rates ----
    for row in bundle.sales_price_rows:
        product_id = _safe_key(row.get("product_id"))
        market_id = _safe_key(row.get("market_id"))
        if not market_id:
            continue

        if product_id:
            bundle.sales_price_lookup[(product_id, market_id)] = row

        # NOTE:
        # current cost_engine expects market_cost_rates keyed only by market.
        # We keep that behavior for backward compatibility.
        # If multiple products share the same market_id, the latest row wins.
        bundle.market_cost_rates[market_id] = {
            "sales": _to_float(row.get("channel_cost_rate")),
            "promotion": _to_float(row.get("promotion_cost_rate")),
            "rebate": _to_float(row.get("rebate_rate")) + _to_float(row.get("discount_rate")),
            "returns": _to_float(row.get("expected_return_rate")),
            "gross_to_net": _to_float(row.get("gross_to_net_adjustment")),
        }

    # ---- market entity bridge ----
    for row in bundle.market_rows:
        market_id = _safe_key(row.get("market_id"))
        if market_id:
            bundle.market_entity_lookup[market_id] = row

    for row in bundle.cs_node_to_market_rows:
        cs_node = _safe_key(row.get("cs_node"))
        product_name = _safe_key(row.get("product_name"))
        market_id = _safe_key(row.get("market_id"))
        if not cs_node or not market_id:
            continue

        bundle.cs_node_to_market_lookup[(cs_node, product_name or None)] = market_id

    # ---- SGA / fixed asset helper lookups ----
    for row in bundle.sga_rows:
        scope_type = _safe_key(row.get("scope_type"))
        scope_id = _safe_key(row.get("scope_id"))
        if scope_type and scope_id:
            bundle.sga_lookup[(scope_type, scope_id)] = row

    for row in bundle.fixed_asset_rows:
        node_id = _safe_key(row.get("node_id"))
        asset_id = _safe_key(row.get("asset_id"))
        if node_id and asset_id:
            bundle.fixed_asset_lookup.setdefault((node_id, asset_id), []).append(row)

    # ---- allocation rules -> engine rules ----
    for row in bundle.allocation_rule_rows:
        rule_name = _safe_key(row.get("rule_id") or "unnamed_rule")
        target_cost_type = _safe_key(row.get("target_cost_type") or "allocated_pool").lower()
        allocation_base = _safe_key(row.get("allocation_base")).lower()
        source_scope_type = _safe_key(row.get("source_scope_type")).lower()
        source_scope_id = _safe_key(row.get("source_scope_id"))
        target_scope_type = _safe_key(row.get("target_scope_type")).lower()
        target_scope_id = _safe_key(row.get("target_scope_id"))
        weighting_rule = _safe_key(row.get("weighting_rule")).lower()
        fixed_or_variable = _safe_key(row.get("fixed_or_variable")).upper()

        if not source_scope_id:
            continue

        driver = {
            "qty": "sales_units",
            "revenue": "sales_units",   # explicit revenue driver not yet in report_input
            "inventory": "qty",
        }.get(allocation_base, "sales_units")

        from_dim = {
            "node": "node",
            "market": "market",
            "corporate": "node",
            "product": "product",
            "total": "node",
        }.get(source_scope_type, "node")

        to_dim = {
            "market": "market",
            "product": "product",
            "node": "node",
            "total": "market",
        }.get(target_scope_type, "market")

        bundle.allocation_rules.append(
            {
                "name": rule_name,
                "driver": driver,
                "from_dim": from_dim,
                "to_dim": to_dim,
                "from_key": source_scope_id,
                "to_key": target_scope_id,
                "pool_categories": [target_cost_type],
                "weighting_rule": weighting_rule or "proportional",
                "fixed_or_variable": fixed_or_variable or "FIXED",
                "raw_row": row,
            }
        )

    return bundle


# ----------------------------------------------------------------------
# Inbound loader
# ----------------------------------------------------------------------

def load_inbound_cost_masters(base_dir: str | Path) -> dict[str, Any]:
    """Load inbound extension masters from CSV directory.

    Expected optional files:
    - inbound_item_master.csv
    - inbound_bom_usage_master.csv
    - inbound_price_decision_master.csv
    - inbound_adjustment_master.csv

    Returns a plain dict so current code can adopt it gradually.
    """
    base_path = Path(base_dir)

    item_rows = _read_csv_rows(base_path / "inbound_item_master.csv")
    bom_rows = _read_csv_rows(base_path / "inbound_bom_usage_master.csv")
    price_rows = _read_csv_rows(base_path / "inbound_price_decision_master.csv")
    adj_rows = _read_csv_rows(base_path / "inbound_adjustment_master.csv")

    inbound_item_lookup: dict[str, dict[str, Any]] = {}
    inbound_bom_by_parent: dict[str, list[dict[str, Any]]] = {}
    inbound_price_decision_lookup: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    inbound_adjustment_by_product: dict[str, list[dict[str, Any]]] = {}
    inbound_adjustment_by_item: dict[str, list[dict[str, Any]]] = {}

    for row in item_rows:
        item_id = _safe_key(row.get("item_id"))
        if item_id:
            inbound_item_lookup[item_id] = row

    for row in bom_rows:
        parent_product_id = _safe_key(row.get("parent_product_id"))
        if parent_product_id:
            inbound_bom_by_parent.setdefault(parent_product_id, []).append(row)

    for row in price_rows:
        supplier_id = _safe_key(row.get("supplier_id"))
        item_id = _safe_key(row.get("item_id"))
        decision_phase = _safe_key(row.get("decision_phase")).lower()
        if supplier_id and item_id and decision_phase:
            key = (supplier_id, item_id, decision_phase)
            inbound_price_decision_lookup.setdefault(key, []).append(row)

    for row in adj_rows:
        product_id = _safe_key(row.get("product_id"))
        item_id = _safe_key(row.get("item_id"))

        if product_id:
            inbound_adjustment_by_product.setdefault(product_id, []).append(row)
        if item_id:
            inbound_adjustment_by_item.setdefault(item_id, []).append(row)

    return {
        "inbound_item_rows": item_rows,
        "inbound_bom_rows": bom_rows,
        "inbound_price_decision_rows": price_rows,
        "inbound_adjustment_rows": adj_rows,
        "inbound_item_lookup": inbound_item_lookup,
        "inbound_bom_by_parent": inbound_bom_by_parent,
        "inbound_price_decision_lookup": inbound_price_decision_lookup,
        "inbound_adjustment_by_product": inbound_adjustment_by_product,
        "inbound_adjustment_by_item": inbound_adjustment_by_item,
    }


def _attach_inbound_to_bundle(bundle: CostMasterBundle, inbound_payload: dict[str, Any]) -> CostMasterBundle:
    bundle.inbound_item_rows = list(inbound_payload.get("inbound_item_rows", []))
    bundle.inbound_bom_rows = list(inbound_payload.get("inbound_bom_rows", []))
    bundle.inbound_price_decision_rows = list(inbound_payload.get("inbound_price_decision_rows", []))
    bundle.inbound_adjustment_rows = list(inbound_payload.get("inbound_adjustment_rows", []))

    bundle.inbound_item_lookup = dict(inbound_payload.get("inbound_item_lookup", {}))
    bundle.inbound_bom_by_parent = dict(inbound_payload.get("inbound_bom_by_parent", {}))
    bundle.inbound_price_decision_lookup = dict(inbound_payload.get("inbound_price_decision_lookup", {}))
    bundle.inbound_adjustment_by_product = dict(inbound_payload.get("inbound_adjustment_by_product", {}))
    bundle.inbound_adjustment_by_item = dict(inbound_payload.get("inbound_adjustment_by_item", {}))
    return bundle


# ----------------------------------------------------------------------
# Public loader
# ----------------------------------------------------------------------

def load_cost_masters(
    source: str | Path | dict[str, Any] | None = None,
    *,
    include_inbound: bool = False,
    return_bundle: bool = False,
) -> dict[str, Any] | CostMasterBundle:
    """Return normalized cost master payload.

    Parameters
    ----------
    source:
        - None -> use data/cost_masters if exists, else sample payload
        - dict -> return as-is (or wrap lightly if return_bundle=True)
        - Path/str directory -> load CSV masters from directory
        - Path/str file -> load JSON payload
    include_inbound:
        When True and source is a directory, also load inbound extension CSVs.
    return_bundle:
        When True, return CostMasterBundle instead of legacy dict payload.
    """
    if source is None:
        default_dir = Path("data") / "cost_masters"
        if default_dir.exists() and default_dir.is_dir():
            bundle = _build_outbound_bundle(default_dir)
            if include_inbound:
                inbound_payload = load_inbound_cost_masters(default_dir)
                bundle = _attach_inbound_to_bundle(bundle, inbound_payload)
            return bundle if return_bundle else bundle.to_legacy_payload()

        payload = _sample_cost_masters()
        if return_bundle:
            # very lightweight wrapper for sample / tests
            bundle = CostMasterBundle()
            bundle.node_cost_rates = dict(payload.get("node_cost_rates", {}))
            bundle.lane_cost_rates = dict(payload.get("lane_cost_rates", {}))
            bundle.market_cost_rates = dict(payload.get("market_cost_rates", {}))
            bundle.allocation_rules = list(payload.get("allocation_rules", []))
            return bundle
        return payload

    if isinstance(source, dict):
        if return_bundle:
            # wrap dict minimally without forcing full migration
            bundle = CostMasterBundle()
            bundle.node_cost_rates = dict(source.get("node_cost_rates", {}))
            bundle.lane_cost_rates = dict(source.get("lane_cost_rates", {}))
            bundle.market_cost_rates = dict(source.get("market_cost_rates", {}))
            bundle.allocation_rules = list(source.get("allocation_rules", []))

            bundle.product_rows = list(source.get("product_rows", []))
            bundle.node_rows = list(source.get("node_rows", []))
            bundle.lane_rows = list(source.get("lane_rows", []))
            bundle.sales_price_rows = list(source.get("sales_price_rows", []))
            bundle.allocation_rule_rows = list(source.get("allocation_rule_rows", []))
            bundle.market_rows = list(source.get("market_rows", []))
            bundle.cs_node_to_market_rows = list(source.get("cs_node_to_market_rows", []))
            bundle.sga_rows = list(source.get("sga_rows", []))
            bundle.fixed_asset_rows = list(source.get("fixed_asset_rows", []))

            bundle.product_cost_lookup = dict(source.get("product_cost_lookup", {}))
            bundle.sales_price_lookup = dict(source.get("sales_price_lookup", {}))
            bundle.market_entity_lookup = dict(source.get("market_entity_lookup", {}))
            bundle.cs_node_to_market_lookup = dict(source.get("cs_node_to_market_lookup", {}))
            bundle.node_lookup = dict(source.get("node_lookup", {}))
            bundle.lane_lookup = dict(source.get("lane_lookup", {}))
            bundle.sga_lookup = dict(source.get("sga_lookup", {}))
            bundle.fixed_asset_lookup = dict(source.get("fixed_asset_lookup", {}))

            bundle = _attach_inbound_to_bundle(bundle, source)
            return bundle
        return source

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Cost master file not found: {path}")

    if path.is_dir():
        bundle = _build_outbound_bundle(path)
        if include_inbound:
            inbound_payload = load_inbound_cost_masters(path)
            bundle = _attach_inbound_to_bundle(bundle, inbound_payload)
        return bundle if return_bundle else bundle.to_legacy_payload()

    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)

    if not isinstance(payload, dict):
        raise ValueError("Cost master file must contain a JSON object")

    if return_bundle:
        return load_cost_masters(payload, include_inbound=include_inbound, return_bundle=True)

    return payload
