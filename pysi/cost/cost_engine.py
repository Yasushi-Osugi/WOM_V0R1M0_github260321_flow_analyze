"""Cost calculation skeleton at product × node × week grain."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def _lane_key(row: dict[str, Any]) -> str | None:
    from_node = row.get("from_node")
    to_node = row.get("to_node")
    if from_node and to_node:
        return f"{from_node}->{to_node}"
    return None


def run_cost_engine(
    report_input: dict[str, Any],
    cost_masters: dict[str, Any],
) -> dict[str, Any]:
    """Compute base cost lines.

    report_input expected keys:
      - records: list[dict] with product/node/week/qty and optional lane+market fields
    """
    records = list(report_input.get("records", []))

    node_rates = cost_masters.get("node_cost_rates", {})
    lane_rates = cost_masters.get("lane_cost_rates", {})
    market_rates = cost_masters.get("market_cost_rates", {})

    cost_lines: list[dict[str, Any]] = []
    totals = defaultdict(float)

    for rec in records:
        product = rec.get("product", "UNKNOWN")
        node = rec.get("node", "UNKNOWN")
        week = rec.get("week", "0000-W00")
        qty = float(rec.get("qty", 0.0) or 0.0)
        market = rec.get("market")

        for category, rate in node_rates.get(node, {}).items():
            amount = qty * float(rate)
            line = {
                "product": product,
                "node": node,
                "week": week,
                "market": market,
                "cost_type": "node",
                "cost_category": category,
                "amount": amount,
                "allocation_status": "original",
            }
            cost_lines.append(line)
            totals["total_cost"] += amount

        lk = _lane_key(rec)
        if lk:
            for category, rate in lane_rates.get(lk, {}).items():
                amount = qty * float(rate)
                line = {
                    "product": product,
                    "node": rec.get("to_node") or node,
                    "week": week,
                    "market": market,
                    "cost_type": "lane",
                    "cost_category": category,
                    "amount": amount,
                    "allocation_status": "original",
                    "lane": lk,
                }
                cost_lines.append(line)
                totals["total_cost"] += amount

        if market:
            for category, rate in market_rates.get(market, {}).items():
                amount = qty * float(rate)
                line = {
                    "product": product,
                    "node": node,
                    "week": week,
                    "market": market,
                    "cost_type": "market",
                    "cost_category": category,
                    "amount": amount,
                    "allocation_status": "original",
                }
                cost_lines.append(line)
                totals["total_cost"] += amount

    return {
        "cost_lines": cost_lines,
        "totals": dict(totals),
        "meta": {"record_count": len(records), "line_count": len(cost_lines)},
    }
