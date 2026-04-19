from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_csv_dicts(path: Path, rows: list[dict[str, Any]]) -> Path:
    _ensure_parent_dir(path)

    if not rows:
        with path.open("w", encoding="utf-8-sig", newline="") as fp:
            fp.write("")
        return path

    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)

    with path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return path


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _top_row(rows: list[dict[str, Any]], key: str = "total_cost") -> dict[str, Any] | None:
    if not rows:
        return None
    return max(rows, key=lambda r: _safe_float(r.get(key)))


def _sum_rows(rows: list[dict[str, Any]], key: str = "total_cost") -> float:
    return sum(_safe_float(r.get(key)) for r in rows)


def _trend_snapshot(monthly_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(monthly_rows) < 2:
        return {
            "latest_month": monthly_rows[-1]["month"] if monthly_rows else "N/A",
            "latest_value": _safe_float(monthly_rows[-1]["total_cost"]) if monthly_rows else 0.0,
            "previous_month": "N/A",
            "previous_value": 0.0,
            "delta": 0.0,
            "delta_pct": 0.0,
            "arrow": "→",
        }

    ordered = sorted(monthly_rows, key=lambda r: str(r.get("month", "")))
    prev_row = ordered[-2]
    latest_row = ordered[-1]

    prev_val = _safe_float(prev_row.get("total_cost"))
    latest_val = _safe_float(latest_row.get("total_cost"))
    delta = latest_val - prev_val
    delta_pct = (delta / prev_val * 100.0) if prev_val else 0.0

    if delta > 0:
        arrow = "↑"
    elif delta < 0:
        arrow = "↓"
    else:
        arrow = "→"

    return {
        "latest_month": latest_row.get("month", "N/A"),
        "latest_value": latest_val,
        "previous_month": prev_row.get("month", "N/A"),
        "previous_value": prev_val,
        "delta": delta,
        "delta_pct": delta_pct,
        "arrow": arrow,
    }


def _strategic_health_score(report: dict[str, Any]) -> tuple[int, list[str]]:
    """
    Heuristic executive overlay.
    This is intentionally explainable and lightweight.

    Inputs used:
    - top pain point concentration
    - top market concentration
    - latest month concentration
    - allocation presence
    """
    reasons: list[str] = []

    total_cost = _safe_float((report.get("product_total") or {}).get("total_cost"))
    if total_cost <= 0:
        return 50, ["total_cost unavailable; default neutral score applied"]

    pain_points = report.get("pain_points", []) or []
    top_pain = pain_points[0] if pain_points else {}
    top_pain_value = _safe_float(top_pain.get("value"))
    top_pain_ratio = (top_pain_value / total_cost) if total_cost else 0.0

    market_rows = report.get("market_report", []) or []
    top_market = _top_row(market_rows)
    market_total = _sum_rows(market_rows)
    top_market_ratio = (_safe_float(top_market.get("total_cost")) / market_total) if top_market and market_total else 0.0

    monthly_rows = report.get("monthly_cost_report", []) or []
    latest_month_value = 0.0
    monthly_total = _safe_float((report.get("monthly_total") or {}).get("total_cost"))
    if monthly_rows:
        latest_month_row = sorted(monthly_rows, key=lambda r: str(r.get("month", "")))[-1]
        latest_month_value = _safe_float(latest_month_row.get("total_cost"))
    latest_month_ratio = (latest_month_value / monthly_total) if monthly_total else 0.0

    allocation_rows = len(report.get("allocation_breakdown", []) or [])

    score = 100.0

    # concentration penalties
    score -= min(35.0, top_pain_ratio * 40.0)
    score -= min(20.0, top_market_ratio * 25.0)
    score -= min(20.0, latest_month_ratio * 20.0)

    # modest bonus for explicit allocation visibility
    if allocation_rows > 0:
        score += 5.0
        reasons.append("allocation breakdown is visible")
    else:
        reasons.append("allocation breakdown is absent")

    if top_pain_ratio > 0.70:
        reasons.append("cost burden is highly concentrated in one pain point")
    if top_market_ratio > 0.35:
        reasons.append("market cost concentration is relatively high")
    if latest_month_ratio > 0.80:
        reasons.append("cost is heavily concentrated in the latest visible month")

    score = max(0, min(100, int(round(score))))
    if not reasons:
        reasons.append("no major concentration warning detected")

    return score, reasons


def _build_executive_headline(report: dict[str, Any]) -> list[str]:
    lines: list[str] = []

    total_cost = _safe_float((report.get("product_total") or {}).get("total_cost"))
    pain_points = report.get("pain_points", []) or []
    top_pain = pain_points[0] if pain_points else None
    if top_pain:
        top_pain_name = str(top_pain.get("pain_point", "UNKNOWN"))
        top_pain_value = _safe_float(top_pain.get("value"))
        ratio = (top_pain_value / total_cost) if total_cost else 0.0

        if top_pain_name == "supply_point" and ratio > 0.70:
            lines.append("Supply-point burden dominates the current cost structure and needs management attention.")
        elif ratio > 0.50:
            lines.append(f"Cost concentration is high at {top_pain_name}, indicating a localized management pain point.")
        else:
            lines.append("Cost concentration is present but not dominated by a single node.")

    market_rows = report.get("market_report", []) or []
    top_market = _top_row(market_rows)
    market_total = _sum_rows(market_rows)
    if top_market:
        market_name = str(top_market.get("market", "UNKNOWN"))
        market_value = _safe_float(top_market.get("total_cost"))
        market_ratio = (market_value / market_total) if market_total else 0.0
        lines.append(f"Market burden is led by {market_name} ({market_ratio:.1%} of visible market cost).")

    monthly_rows = report.get("monthly_cost_report", []) or []
    trend = _trend_snapshot(monthly_rows)
    if monthly_rows:
        lines.append(
            f"Latest monthly cost view is {trend['arrow']} {trend['latest_month']} "
            f"(Δ {trend['delta']:,.2f}, {trend['delta_pct']:.1f}%)."
        )

    return lines[:3] if lines else ["Management summary is available, but executive signal extraction is still limited."]


def _build_recommended_actions(report: dict[str, Any], max_items: int = 4) -> list[str]:
    actions: list[str] = []

    total_cost = _safe_float((report.get("product_total") or {}).get("total_cost"))
    pain_points = report.get("pain_points", []) or []
    if pain_points:
        top = pain_points[0]
        top_name = str(top.get("pain_point", "UNKNOWN"))
        top_value = _safe_float(top.get("value"))
        ratio = (top_value / total_cost) if total_cost else 0.0

        if top_name == "supply_point" and ratio > 0.70:
            actions.append("Inspect supply_point integrated P/L, decoupling inventory burden, and upstream allocation logic.")
        elif top_name.startswith("WS_"):
            actions.append(f"Review warehouse/buffer cost structure and regional allocation basis at {top_name}.")
        elif top_name.startswith("DAD_"):
            actions.append(f"Review distribution node economics and service protection burden at {top_name}.")
        else:
            actions.append(f"Review the operating role and cost structure at {top_name}.")

    market_rows = report.get("market_report", []) or []
    top_market = _top_row(market_rows)
    market_total = _sum_rows(market_rows)
    if top_market and market_total:
        market_name = str(top_market.get("market", "UNKNOWN"))
        market_ratio = _safe_float(top_market.get("total_cost")) / market_total
        if market_ratio > 0.30:
            actions.append(f"Recheck pricing, service assumptions, and channel mix for {market_name}.")

    monthly_rows = report.get("monthly_cost_report", []) or []
    trend = _trend_snapshot(monthly_rows)
    if monthly_rows and abs(_safe_float(trend["delta_pct"])) > 20.0:
        actions.append("Review the latest month concentration for inventory carry, period mapping, and allocation timing effects.")

    allocation_rows = len(report.get("allocation_breakdown", []) or [])
    if allocation_rows > 0:
        actions.append("Use allocation_breakdown.csv to verify whether fixed/common cost attribution matches management intent.")

    return actions[:max_items]


def build_report_markdown(
    report: dict[str, Any],
    *,
    top_n_pain_points: int = 5,
    include_generated_artifacts: bool = True,
) -> str:
    meta = report.get("meta", {}) or {}
    product_rows = report.get("product_report", []) or []
    node_rows = report.get("node_report", []) or []
    market_rows = report.get("market_report", []) or []
    monthly_rows = report.get("monthly_cost_report", []) or []
    pain_points = (report.get("pain_points", []) or [])[:top_n_pain_points]

    product_total = report.get("product_total") or {}
    monthly_total = report.get("monthly_total") or {}

    total_cost = _safe_float(product_total.get("total_cost") or monthly_total.get("total_cost"))
    score, score_reasons = _strategic_health_score(report)
    headlines = _build_executive_headline(report)
    actions = _build_recommended_actions(report)
    trend = _trend_snapshot(monthly_rows)

    lines: list[str] = []
    lines.append("# WOM Business Report Summary")
    lines.append("")

    lines.append("## Scenario")
    lines.append(f"- Records: {meta.get('record_count', 0)}")
    lines.append(f"- Cost lines: {meta.get('cost_line_count', 0)}")
    lines.append(f"- Product rows: {len(product_rows)}")
    lines.append(f"- Node rows: {len(node_rows)}")
    lines.append(f"- Market rows: {len(market_rows)}")
    lines.append(f"- Allocation rows: {len(report.get('allocation_breakdown', []) or [])}")
    lines.append("")

    lines.append("## Executive Headline")
    for item in headlines:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Strategic Health Score")
    lines.append(f"- Score: {score}/100")
    lines.append(f"- Interpretation: {score_reasons[0]}")
    lines.append("")

    lines.append("## Business Result")
    lines.append(f"- Product total cost: {total_cost:,.2f}")
    lines.append(f"- Monthly total cost: {_safe_float(monthly_total.get('total_cost')):,.2f}")
    if product_rows:
        top_product = _top_row(product_rows)
        lines.append(f"- Primary product row: {top_product.get('product', 'UNKNOWN')} = {_safe_float(top_product.get('total_cost')):,.2f}")
    if market_rows:
        top_market = _top_row(market_rows)
        lines.append(f"- Highest market burden: {top_market.get('market', 'UNKNOWN')} = {_safe_float(top_market.get('total_cost')):,.2f}")
    lines.append("")

    lines.append("## Trend Snapshot")
    lines.append(
        f"- {trend['previous_month']} -> {trend['latest_month']}: "
        f"{trend['arrow']} {trend['delta']:,.2f} ({trend['delta_pct']:.1f}%)"
    )
    lines.append(f"- Latest visible month total: {trend['latest_value']:,.2f}")
    lines.append("")

    lines.append("## Top Pain Points")
    if pain_points:
        for row in pain_points:
            lines.append(f"- {row.get('pain_point', 'UNKNOWN')}: {_safe_float(row.get('value')):,.2f}")
    else:
        lines.append("- No pain points detected.")
    lines.append("")

    lines.append("## Recommended Next Actions")
    if actions:
        for item in actions:
            lines.append(f"- {item}")
    else:
        lines.append("- No immediate action recommendation generated.")
    lines.append("")

    if include_generated_artifacts:
        lines.append("## Generated Artifacts")
        lines.append("- business_report.json")
        lines.append("- summary.md")
        lines.append("- product_report.csv")
        lines.append("- node_report.csv")
        lines.append("- market_report.csv")
        lines.append("- cost_waterfall.csv")
        lines.append("- pain_points.csv")
        lines.append("- allocation_breakdown.csv")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def export_report_json(report: dict[str, Any], output_path: str | Path, *, indent: int = 2) -> Path:
    path = Path(output_path)
    _ensure_parent_dir(path)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=indent)
    return path


def export_report_markdown(
    report: dict[str, Any],
    output_path: str | Path,
    *,
    top_n_pain_points: int = 5,
) -> Path:
    path = Path(output_path)
    _ensure_parent_dir(path)
    markdown = build_report_markdown(report, top_n_pain_points=top_n_pain_points)
    with path.open("w", encoding="utf-8") as fp:
        fp.write(markdown)
    return path


def export_report_bundle(
    report: dict[str, Any],
    output_dir: str | Path,
    *,
    file_stem: str | None = None,
    markdown_top_n_rows: int = 10,
) -> dict[str, Path]:
    """
    Export the standard WOM reporting MVP bundle.

    The current pipeline expects these keys:
    - json
    - markdown
    - product_report
    - node_report
    - market_report
    - cost_waterfall
    - pain_points
    - allocation_breakdown
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {}

    paths["json"] = export_report_json(report, out_dir / "business_report.json")
    paths["markdown"] = export_report_markdown(
        report,
        out_dir / "summary.md",
        top_n_pain_points=min(markdown_top_n_rows, 5),
    )

    paths["product_report"] = _write_csv_dicts(out_dir / "product_report.csv", report.get("product_report", []) or [])
    paths["node_report"] = _write_csv_dicts(out_dir / "node_report.csv", report.get("node_report", []) or [])
    paths["market_report"] = _write_csv_dicts(out_dir / "market_report.csv", report.get("market_report", []) or [])
    paths["cost_waterfall"] = _write_csv_dicts(out_dir / "cost_waterfall.csv", report.get("cost_waterfall", []) or [])
    paths["pain_points"] = _write_csv_dicts(out_dir / "pain_points.csv", report.get("pain_points", []) or [])
    paths["allocation_breakdown"] = _write_csv_dicts(
        out_dir / "allocation_breakdown.csv",
        report.get("allocation_breakdown", []) or [],
    )

    return paths
