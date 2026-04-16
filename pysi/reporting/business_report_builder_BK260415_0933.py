"""Build business-facing report artifacts from cost/KPI data."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from pysi.cost.cost_to_kpi_adapter import build_kpi_rows
from pysi.reporting.monthly_period_mapper import week_to_month_label


def _build_cost_waterfall(cost_lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    agg = defaultdict(float)
    for line in cost_lines:
        key = f"{line.get('cost_type', 'unknown')}:{line.get('cost_category', 'unknown')}"
        agg[key] += float(line.get("amount", 0.0) or 0.0)
    return [{"step": key, "amount": value} for key, value in sorted(agg.items())]


def _build_pain_points(node_report: list[dict[str, Any]], top_n: int = 5) -> list[dict[str, Any]]:
    sorted_rows = sorted(node_report, key=lambda r: float(r.get("total_cost", 0.0)), reverse=True)
    out: list[dict[str, Any]] = []
    for row in sorted_rows[:top_n]:
        out.append(
            {
                "pain_point": row.get("node", "UNKNOWN"),
                "metric": "total_cost",
                "value": float(row.get("total_cost", 0.0) or 0.0),
            }
        )
    return out


def build_business_report(
    report_input: dict[str, Any],
    cost_lines: list[dict[str, Any]],
    allocation_breakdown: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    kpi = build_kpi_rows(cost_lines)

    monthly = defaultdict(float)
    for line in cost_lines:
        month_label = week_to_month_label(str(line.get("week", "UNKNOWN")))
        monthly[month_label] += float(line.get("amount", 0.0) or 0.0)

    monthly_cost_report = [
        {"month": month, "total_cost": value} for month, value in sorted(monthly.items())
    ]

    cost_waterfall = _build_cost_waterfall(cost_lines)
    pain_points = _build_pain_points(kpi["node_report"])

    return {
        "meta": {
            "record_count": len(report_input.get("records", [])),
            "cost_line_count": len(cost_lines),
        },
        "product_report": kpi["product_report"],
        "node_report": kpi["node_report"],
        "market_report": kpi["market_report"],
        "monthly_cost_report": monthly_cost_report,
        "cost_waterfall": cost_waterfall,
        "pain_points": pain_points,
        "allocation_breakdown": allocation_breakdown or [],
    }
