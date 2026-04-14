"""Bridge cost lines to KPI rows for reporting."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def build_kpi_rows(cost_lines: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_product = defaultdict(float)
    by_node = defaultdict(float)
    by_market = defaultdict(float)

    for line in cost_lines:
        amount = float(line.get("amount", 0.0) or 0.0)
        by_product[str(line.get("product", "UNKNOWN"))] += amount
        by_node[str(line.get("node", "UNKNOWN"))] += amount
        by_market[str(line.get("market", "UNASSIGNED"))] += amount

    product_rows = [
        {"product": key, "total_cost": value}
        for key, value in sorted(by_product.items(), key=lambda kv: kv[0])
    ]
    node_rows = [
        {"node": key, "total_cost": value}
        for key, value in sorted(by_node.items(), key=lambda kv: kv[0])
    ]
    market_rows = [
        {"market": key, "total_cost": value}
        for key, value in sorted(by_market.items(), key=lambda kv: kv[0])
    ]

    return {
        "product_report": product_rows,
        "node_report": node_rows,
        "market_report": market_rows,
    }
