"""Load cost master dictionaries for reporting MVP.

This loader supports:
- direct dictionary input (already-loaded masters)
- a lightweight JSON file path
- a directory containing CSV masters under data/cost_masters
- fallback sample masters for static runs
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


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


def _load_from_directory(base_dir: Path) -> dict[str, Any]:
    node_rows = _read_csv_rows(base_dir / "node_cost_master.csv")
    lane_rows = _read_csv_rows(base_dir / "lane_cost_master.csv")
    market_rows = _read_csv_rows(base_dir / "sales_price_master.csv")
    allocation_rows = _read_csv_rows(base_dir / "allocation_rule_master.csv")

    node_cost_rates: dict[str, dict[str, float]] = {}
    lane_cost_rates: dict[str, dict[str, float]] = {}
    market_cost_rates: dict[str, dict[str, float]] = {}
    allocation_rules: list[dict[str, Any]] = []

    for row in node_rows:
        node_id = (row.get("node_id") or "").strip()
        if not node_id:
            continue

        node_cost_rates[node_id] = {
            "production": _to_float(row.get("production_variable_cost_rate")),
            "inventory": _to_float(row.get("inventory_holding_cost_rate")),
            "sga": _to_float(row.get("local_sga_variable_cost_rate")),
            "depreciation": _to_float(row.get("depreciation_cost_per_period")),
        }

    for row in lane_rows:
        from_node = (row.get("from_node_id") or "").strip()
        to_node = (row.get("to_node_id") or "").strip()
        if not from_node or not to_node:
            continue

        lane_key = f"{from_node}->{to_node}"
        lane_cost_rates[lane_key] = {
            "logistics": _to_float(row.get("freight_cost_per_unit")),
            "tariff": _to_float(row.get("tariff_rate")),
            "insurance": _to_float(row.get("insurance_cost_per_unit")),
            "customs": _to_float(row.get("customs_cost_per_unit")),
            "carbon": _to_float(row.get("carbon_cost_per_unit")),
        }

    for row in market_rows:
        market_id = (row.get("market_id") or "").strip()
        if not market_id:
            continue

        market_cost_rates[market_id] = {
            "sales": _to_float(row.get("channel_cost_rate")),
            "promotion": _to_float(row.get("promotion_cost_rate")),
            "rebate": _to_float(row.get("rebate_rate")) + _to_float(row.get("discount_rate")),
            "returns": _to_float(row.get("expected_return_rate")),
        }

    for row in allocation_rows:
        rule_name = (row.get("rule_id") or "unnamed_rule").strip()
        target_cost_type = (row.get("target_cost_type") or "allocated_pool").strip().lower()
        allocation_base = (row.get("allocation_base") or "").strip().lower()
        source_scope_type = (row.get("source_scope_type") or "").strip().lower()
        source_scope_id = (row.get("source_scope_id") or "").strip()
        target_scope_type = (row.get("target_scope_type") or "").strip().lower()
        target_scope_id = (row.get("target_scope_id") or "").strip()
        weighting_rule = (row.get("weighting_rule") or "").strip().lower()
        fixed_or_variable = (row.get("fixed_or_variable") or "").strip().upper()

        if not source_scope_id:
            continue

        driver = {
            "qty": "sales_units",
            "revenue": "sales_units",   # revenue driver not yet explicitly present in report_input
            "inventory": "qty",
        }.get(allocation_base, "sales_units")

        from_dim = {
            "node": "node",
            "market": "market",
            "corporate": "node",  # treat corporate pool as node-like for now
            "product": "product",
            "total": "node",
        }.get(source_scope_type, "node")

        to_dim = {
            "market": "market",
            "product": "product",
            "node": "node",
            "total": "market",
        }.get(target_scope_type, "market")

        allocation_rules.append(
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

    return {
        "node_cost_rates": node_cost_rates,
        "lane_cost_rates": lane_cost_rates,
        "market_cost_rates": market_cost_rates,
        "allocation_rules": allocation_rules,
    }


def load_cost_masters(source: str | Path | dict[str, Any] | None = None) -> dict[str, Any]:
    """Return normalized cost master payload."""
    if source is None:
        default_dir = Path("data") / "cost_masters"
        if default_dir.exists() and default_dir.is_dir():
            return _load_from_directory(default_dir)
        return _sample_cost_masters()

    if isinstance(source, dict):
        return source

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Cost master file not found: {path}")

    if path.is_dir():
        return _load_from_directory(path)

    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)

    if not isinstance(payload, dict):
        raise ValueError("Cost master file must contain a JSON object")
    return payload