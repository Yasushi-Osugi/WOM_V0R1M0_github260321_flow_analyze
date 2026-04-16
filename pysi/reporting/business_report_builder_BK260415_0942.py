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


def _is_blank_market(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _build_market_report_allocated_view(cost_lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Allocated-view market report.

    Policy:
    - exclude blank market buckets
    - include any line that has a concrete market id
      (this includes both direct market-tagged lines and allocated lines)
    """
    agg = defaultdict(float)

    for line in cost_lines:
        market = line.get("market")
        if _is_blank_market(market):
            continue

        agg[str(market)] += float(line.get("amount", 0.0) or 0.0)

    return [{"market": key, "total_cost": value} for key, value in sorted(agg.items())]


def _safe_week_to_month_label(week_value: Any) -> str:
    """
    Make monthly report more robust for mixed week representations.

    Current inputs may be:
    - "2026-W01"
    - "ALL"
    - 0, 1, 2 ...
    - None
    """
    if week_value is None:
        return "UNKNOWN"

    if isinstance(week_value, int):
        # reporting MVP currently uses zero-based week index in some paths
        return week_to_month_label(f"2026-W{week_value + 1:02d}")

    text = str(week_value).strip()
    if not text:
        return "UNKNOWN"

    if text.upper() == "ALL":
        return "ALL"

    if text.isdigit():
        return week_to_month_label(f"2026-W{int(text) + 1:02d}")

    return week_to_month_label(text)


def build_business_report(
    report_input: dict[str, Any],
    cost_lines: list[dict[str, Any]],
    allocation_breakdown: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    kpi = build_kpi_rows(cost_lines)

    monthly = defaultdict(float)
    for line in cost_lines:
        month_label = _safe_week_to_month_label(line.get("week", "UNKNOWN"))
        monthly[month_label] += float(line.get("amount", 0.0) or 0.0)

    monthly_cost_report = [
        {"month": month, "total_cost": value} for month, value in sorted(monthly.items())
    ]

    cost_waterfall = _build_cost_waterfall(cost_lines)
    pain_points = _build_pain_points(kpi["node_report"])

    # IMPORTANT:
    # market_report is not taken from build_kpi_rows anymore.
    # We expose only allocated/concrete market view here.
    market_report = _build_market_report_allocated_view(cost_lines)

    return {
        "meta": {
            "record_count": len(report_input.get("records", [])),
            "cost_line_count": len(cost_lines),
        },
        "product_report": kpi["product_report"],
        "node_report": kpi["node_report"],
        "market_report": market_report,
        "monthly_cost_report": monthly_cost_report,
        "cost_waterfall": cost_waterfall,
        "pain_points": pain_points,
        "allocation_breakdown": allocation_breakdown or [],
    }