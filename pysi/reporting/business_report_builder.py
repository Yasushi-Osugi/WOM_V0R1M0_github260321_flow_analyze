"""Build business-facing report artifacts from cost/KPI data."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from pysi.cost.cost_to_kpi_adapter import build_kpi_rows
from pysi.reporting.monthly_period_mapper import week_to_month_label


def _safe_amount(line: dict[str, Any]) -> float:
    try:
        return float(line.get("amount", 0.0) or 0.0)
    except Exception:
        return 0.0


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _is_total_label(value: Any) -> bool:
    text = str(value or "").strip().upper()
    return text in {"ALL", "TOTAL"}


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
        return week_to_month_label(f"2026-W{week_value + 1:02d}")

    text = str(week_value).strip()
    if not text:
        return "UNKNOWN"

    if text.upper() == "ALL":
        return "ALL"

    if text.isdigit():
        return week_to_month_label(f"2026-W{int(text) + 1:02d}")

    try:
        return week_to_month_label(text)
    except Exception:
        return "UNKNOWN"


def _build_cost_waterfall(cost_lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    agg = defaultdict(float)
    for line in cost_lines:
        key = f"{line.get('cost_type', 'unknown')}:{line.get('cost_category', 'unknown')}"
        agg[key] += _safe_amount(line)
    return [{"step": key, "amount": value} for key, value in sorted(agg.items(), key=lambda kv: kv[0])]


def _build_pain_points(node_report: list[dict[str, Any]], top_n: int = 5) -> list[dict[str, Any]]:
    ranked = sorted(node_report, key=lambda r: float(r.get("total_cost", 0.0) or 0.0), reverse=True)
    out: list[dict[str, Any]] = []
    for row in ranked[:top_n]:
        out.append(
            {
                "pain_point": row.get("node", "UNKNOWN"),
                "metric": "total_cost",
                "value": float(row.get("total_cost", 0.0) or 0.0),
            }
        )
    return out


def _build_market_report_allocated_view(cost_lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Allocated-view market report.

    Policy:
    - exclude blank market buckets
    - exclude synthetic market labels such as ALL
    - include any line that has a concrete market id
      (this includes both direct market-tagged lines and allocated lines)
    """
    agg = defaultdict(float)

    for line in cost_lines:
        market = line.get("market")
        if _is_blank(market) or _is_total_label(market):
            continue

        agg[str(market).strip()] += _safe_amount(line)

    return [{"market": key, "total_cost": value} for key, value in sorted(agg.items(), key=lambda kv: kv[0])]


def _build_monthly_cost_report(cost_lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    monthly = defaultdict(float)

    for line in cost_lines:
        month_label = _safe_week_to_month_label(line.get("week", "UNKNOWN"))

        # monthly report is a period view only; synthetic ALL is handled separately
        if month_label == "ALL":
            continue

        monthly[month_label] += _safe_amount(line)

    return [{"month": month, "total_cost": value} for month, value in sorted(monthly.items(), key=lambda kv: kv[0])]


def _build_product_report_from_cost_lines(cost_lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Build product report directly from cost_lines and exclude synthetic ALL rows.

    Why direct build?
    - some KPI adapters may still carry a synthetic product='ALL'
    - total reconciliation should not depend on whether that synthetic row exists
    """
    agg = defaultdict(float)

    for line in cost_lines:
        product = line.get("product")

        if _is_blank(product) or _is_total_label(product):
            continue

        agg[str(product).strip()] += _safe_amount(line)

    return [{"product": key, "total_cost": value} for key, value in sorted(agg.items(), key=lambda kv: kv[0])]


def _compute_grand_total_from_report_rows(
    product_report: list[dict[str, Any]],
    monthly_cost_report: list[dict[str, Any]],
) -> float:
    """
    Compute one canonical report total from report-facing rows, not raw cost_lines.

    Why?
    - raw cost_lines may contain both original and allocated lines
    - summing raw cost_lines can overcount after allocation
    - report total should match what management sees in product/monthly views

    Policy:
    1. prefer concrete product_report sum
    2. fallback to monthly_cost_report sum
    """
    product_total = sum(float(r.get("total_cost", 0.0) or 0.0) for r in product_report)
    if product_total:
        return product_total

    monthly_total = sum(float(r.get("total_cost", 0.0) or 0.0) for r in monthly_cost_report)
    return monthly_total


def build_business_report(
    report_input: dict[str, Any],
    cost_lines: list[dict[str, Any]],
    allocation_breakdown: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    allocation_breakdown = allocation_breakdown or []

    # Keep existing KPI adapter usage for node view compatibility
    kpi = build_kpi_rows(cost_lines)

    # product report: concrete products only
    product_report = _build_product_report_from_cost_lines(cost_lines)

    # node report: keep gross operational view
    node_report = kpi.get("node_report", [])

    # market report: allocated view only
    market_report = _build_market_report_allocated_view(cost_lines)

    # monthly report: period rows only
    monthly_cost_report = _build_monthly_cost_report(cost_lines)

    # canonical report-facing total
    grand_total = _compute_grand_total_from_report_rows(
        product_report=product_report,
        monthly_cost_report=monthly_cost_report,
    )

    product_total = {
        "label": "ALL",
        "total_cost": grand_total,
    }

    monthly_total = {
        "label": "ALL",
        "total_cost": grand_total,
    }

    cost_waterfall = _build_cost_waterfall(cost_lines)
    pain_points = _build_pain_points(node_report=node_report, top_n=5)

    return {
        "meta": {
            "record_count": len(report_input.get("records", [])),
            "cost_line_count": len(cost_lines),
        },
        "product_report": product_report,
        "product_total": product_total,
        "node_report": node_report,
        "market_report": market_report,
        "monthly_cost_report": monthly_cost_report,
        "monthly_total": monthly_total,
        "cost_waterfall": cost_waterfall,
        "pain_points": pain_points,
        "allocation_breakdown": allocation_breakdown,
    }