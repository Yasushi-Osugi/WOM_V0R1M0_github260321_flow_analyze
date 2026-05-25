from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from typing import Any
from tkinter import ttk

SEVERITY_PRIORITY = {
    "error": 0,
    "warning": 1,
    "info": 2,
    "none": 3,
    "": 4,
}


def _getattr(obj: Any, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default) if obj is not None else default


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _get_summary(obj: Any) -> dict[str, Any]:
    return _as_dict(_getattr(obj, "summary", {}))


def _to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _severity_rank(value: Any) -> int:
    key = str(value or "").lower()
    return SEVERITY_PRIORITY.get(key, 5)


def _path_to_str(value: Any) -> str:
    if isinstance(value, Path):
        return value.as_posix()
    return str(value) if isinstance(value, str) else ""


def _export_result_to_summary(value: Any) -> dict[str, Any]:
    if value is None:
        return {"available": False}
    files = _as_dict(_getattr(value, "files", {}))
    return {
        "available": True,
        "output_dir": _path_to_str(_getattr(value, "output_dir", "")),
        "file_count": len(files),
        "files": {str(k): _path_to_str(v) for k, v in files.items()},
        "record_counts": _as_dict(_getattr(value, "record_counts", {})),
        "summary_path": _path_to_str(_getattr(value, "summary_path", "")),
        "assumptions_path": _path_to_str(_getattr(value, "assumptions_path", "")),
        "message": str(_getattr(value, "message", "") or ""),
    }


def _bool_label(value: Any) -> str:
    return "Yes" if bool(value) else "No"


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return _bool_label(value)
    if isinstance(value, (int, float)):
        if isinstance(value, float):
            return f"{value:,.2f}"
        return f"{value:,}"
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, list):
        return ", ".join(_format_value(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value)


def _rows_from_dict(data: dict[str, Any]) -> list[tuple[str, str]]:
    return [(str(k), _format_value(v)) for k, v in data.items()]


def _insert_tree_rows(tree: ttk.Treeview, rows: list[tuple[str, ...]]) -> None:
    for row in rows:
        tree.insert("", "end", values=row)


def _create_key_value_tree(parent: tk.Widget, rows: list[tuple[str, str]]) -> ttk.Treeview:
    container = ttk.Frame(parent)
    container.pack(fill="both", expand=True)
    tree = ttk.Treeview(container, columns=("key", "value"), show="headings", height=12)
    tree.heading("key", text="Key")
    tree.heading("value", text="Value")
    tree.column("key", width=320, anchor="w")
    tree.column("value", width=700, anchor="w")
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    _insert_tree_rows(tree, rows)
    return tree


def _create_table(parent: tk.Widget, columns: list[str], rows: list[dict[str, Any]]) -> ttk.Treeview:
    container = ttk.Frame(parent)
    container.pack(fill="both", expand=True)
    tree = ttk.Treeview(container, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=140, anchor="w")
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    _insert_tree_rows(tree, [tuple(_format_value(row.get(col, "")) for col in columns) for row in rows])
    return tree


def _truncate_label(label: Any, max_len: int = 40) -> str:
    text = str(label or "")
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _draw_chart_message(canvas: tk.Canvas, message: str) -> None:
    canvas.delete("all")
    width = int(canvas.cget("width"))
    height = int(canvas.cget("height"))
    canvas.create_text(width / 2, height / 2, text=message, fill="#333333", font=("TkDefaultFont", 10), justify="center")


def _draw_horizontal_bar_chart(canvas: tk.Canvas, rows: list[dict[str, Any]], *, label_key: str = "label", value_key: str = "value", empty_message: str) -> None:
    canvas.delete("all")
    valid_rows = [row for row in rows if isinstance(row, dict)]
    max_value = max((_to_float(row.get(value_key, 0.0)) for row in valid_rows), default=0.0)
    if not valid_rows or max_value <= 0:
        _draw_chart_message(canvas, empty_message)
        return
    width = int(canvas.cget("width"))
    height = int(canvas.cget("height"))
    top, bottom = 12, height - 12
    bar_start, value_x = 190, width - 8
    bar_max_width = max(1, value_x - bar_start - 68)
    row_height = max(16, int((bottom - top) / max(1, len(valid_rows))))
    for idx, row in enumerate(valid_rows):
        value = max(0.0, _to_float(row.get(value_key, 0.0)))
        y = top + idx * row_height + row_height / 2
        bar_h = min(16, int(row_height * 0.6))
        canvas.create_text(6, y, text=_truncate_label(row.get(label_key, "")), anchor="w", fill="#111111", font=("TkDefaultFont", 9))
        bar_width = (value / max_value) * bar_max_width if max_value > 0 else 0
        canvas.create_rectangle(bar_start, y - bar_h / 2, bar_start + bar_width, y + bar_h / 2, fill="#5B8FF9", outline="#5B8FF9")
        canvas.create_text(value_x, y, text=_format_value(value), anchor="e", fill="#111111", font=("TkDefaultFont", 9))


def _draw_distribution_bar_chart(canvas: tk.Canvas, rows: list[dict[str, Any]], *, label_key: str = "label", value_key: str = "value", empty_message: str) -> None:
    canvas.delete("all")
    valid_rows = [row for row in rows if isinstance(row, dict)]
    max_value = max((_to_float(row.get(value_key, 0.0)) for row in valid_rows), default=0.0)
    if not valid_rows or max_value <= 0:
        _draw_chart_message(canvas, empty_message)
        return
    width = int(canvas.cget("width"))
    height = int(canvas.cget("height"))
    top, bottom = 16, height - 34
    left, right = 28, width - 18
    chart_h = max(1, bottom - top)
    count = max(1, len(valid_rows))
    slot_w = max(20, int((right - left) / count))
    bar_w = max(10, int(slot_w * 0.55))
    canvas.create_line(left, bottom, right, bottom, fill="#888888")
    for idx, row in enumerate(valid_rows):
        value = max(0.0, _to_float(row.get(value_key, 0.0)))
        label = _truncate_label(row.get(label_key, ""), 16)
        x_center = left + int((idx + 0.5) * slot_w)
        bar_h = (value / max_value) * (chart_h - 6) if max_value > 0 else 0
        x0, x1 = x_center - bar_w / 2, x_center + bar_w / 2
        y0, y1 = bottom - bar_h, bottom
        canvas.create_rectangle(x0, y0, x1, y1, fill="#7C7C7C", outline="#7C7C7C")
        canvas.create_text(x_center, y0 - 6, text=_format_value(int(value) if float(value).is_integer() else value), anchor="s", fill="#111111", font=("TkDefaultFont", 9))
        canvas.create_text(x_center, bottom + 4, text=label, anchor="n", fill="#111111", font=("TkDefaultFont", 9))


def _create_canvas_chart_frame(parent: tk.Widget, title: str) -> tuple[ttk.Frame, tk.Canvas]:
    frame = ttk.LabelFrame(parent, text=title, padding=6)
    canvas = tk.Canvas(frame, width=520, height=240, bg="white", highlightthickness=1, highlightbackground="#d2d2d2")
    canvas.pack(fill="both", expand=True)
    return frame, canvas


def _create_graphs_tab(notebook: ttk.Notebook, graph_model: dict[str, Any]) -> None:
    tab = ttk.Frame(notebook, padding=8)
    notebook.add(tab, text="Graphs")
    for i in (0, 1):
        tab.grid_columnconfigure(i, weight=1)
        tab.grid_rowconfigure(i, weight=1)
    top_frame, top_canvas = _create_canvas_chart_frame(tab, "Top Business Impact")
    comp_frame, comp_canvas = _create_canvas_chart_frame(tab, "Cost / KPI Impact Composition")
    sev_frame, sev_canvas = _create_canvas_chart_frame(tab, "Issue Severity Distribution")
    week_frame, week_canvas = _create_canvas_chart_frame(tab, "Weekly Issue Count")
    top_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 6))
    comp_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 6))
    sev_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(6, 6))
    week_frame.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(6, 6))
    _draw_horizontal_bar_chart(top_canvas, _as_list(graph_model.get("top_impact_bars", [])), empty_message="No top impact issues are available.")
    _draw_horizontal_bar_chart(comp_canvas, _as_list(graph_model.get("impact_composition", [])), empty_message="No Cost / KPI impact composition is available.")
    sev = _as_dict(graph_model.get("severity_distribution", {}))
    _draw_distribution_bar_chart(
        sev_canvas,
        [{"label": "error", "value": sev.get("error", 0)}, {"label": "warning", "value": sev.get("warning", 0)}, {"label": "info", "value": sev.get("info", 0)}],
        empty_message="No issue severity counts are available.",
    )
    week_rows = [{"label": str(row.get("week", "")), "value": row.get("count", 0)} for row in _as_list(graph_model.get("weekly_issue_counts", [])) if isinstance(row, dict)]
    _draw_distribution_bar_chart(week_canvas, week_rows, empty_message="No week-level issue data is available.")
    messages = [str(m) for m in _as_list(graph_model.get("messages", [])) if m is not None][:3]
    if messages:
        ttk.Label(tab, text="Graph Notes / Caveats").grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        for idx, message in enumerate(messages):
            ttk.Label(tab, text=f"{idx + 1}. {message}", justify="left", wraplength=1080).grid(row=3 + idx, column=0, columnspan=2, sticky="w")



def _to_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _make_top_impact_label(row: dict[str, Any]) -> str:
    issue_type = str(row.get("issue_type") or "issue")
    node = str(row.get("node") or "")
    week_value = str(row.get("week") or "")
    if week_value and not week_value.lower().startswith("w"):
        week_value = f"W{week_value}"
    return f"{issue_type} / {node} / {week_value}"


def _week_sort_key(value: Any) -> tuple[int, int, str]:
    text = str(value or "").strip()
    if not text:
        return (2, 0, "")
    lower = text.lower()
    digits = ""
    if lower.startswith("w"):
        digits = "".join(ch for ch in lower[1:] if ch.isdigit())
    elif text.isdigit():
        digits = text
    if digits:
        return (0, int(digits), text)
    return (1, 0, text)


def build_explicit_pipeline_kpi_graph_view_model(view_model: dict) -> dict:
    model = _as_dict(view_model)
    if not bool(model.get("available")):
        return {
            "available": False,
            "top_impact_bars": [],
            "severity_distribution": {"error": 0, "warning": 0, "info": 0},
            "impact_composition": [],
            "weekly_issue_counts": [],
            "messages": ["No explicit pipeline KPI view data is available for graph rendering."],
        }

    top_rows = []
    for src in _as_list(model.get("top_impact_issues", [])):
        if not isinstance(src, dict):
            continue
        row = {
            "severity": str(src.get("severity") or ""),
            "issue_type": str(src.get("issue_type") or "issue"),
            "node": str(src.get("node") or ""),
            "week": str(src.get("week") or ""),
            "value": _to_float(src.get("estimated_total_business_impact", 0.0)),
        }
        row["label"] = _make_top_impact_label(row)
        top_rows.append(row)

    top_rows.sort(
        key=lambda r: (
            -_to_float(r.get("value")),
            _severity_rank(r.get("severity")),
            str(r.get("issue_type", "")),
            str(r.get("node", "")),
            str(r.get("week", "")),
        )
    )
    top_rows = top_rows[:10]

    issue_summary = _as_dict(model.get("issue_summary", {}))
    severity_distribution = {
        "error": _to_int(issue_summary.get("error_count", 0)),
        "warning": _to_int(issue_summary.get("warning_count", 0)),
        "info": _to_int(issue_summary.get("info_count", 0)),
    }

    executive = _as_dict(model.get("executive_kpi_summary", {}))
    impact_composition = [
        {"label": "Lost Sales", "value": _to_float(executive.get("estimated_lost_sales_value_total", 0.0))},
        {"label": "Margin Impact", "value": _to_float(executive.get("estimated_margin_impact_total", 0.0))},
        {"label": "Inventory Cost", "value": _to_float(executive.get("estimated_inventory_cost_impact_total", 0.0))},
        {"label": "Capacity Cost", "value": _to_float(executive.get("estimated_capacity_cost_impact_total", 0.0))},
        {"label": "Service Penalty", "value": _to_float(executive.get("estimated_service_penalty_total", 0.0))},
    ]

    counts: dict[str, int] = {}
    for row in top_rows:
        week = str(row.get("week") or "").strip()
        if not week:
            continue
        counts[week] = counts.get(week, 0) + 1
    weekly_issue_counts = [{"week": week, "count": counts[week]} for week in sorted(counts.keys(), key=_week_sort_key)]

    messages = ["Graph model is derived from the current read-only KPI view model."]
    existing_messages = [str(m) for m in _as_list(model.get("messages", [])) if m is not None]
    for caveat in [
        "Cost / KPI values are directional scenario estimates, not formal accounting values.",
        "Double counting may be possible depending on assumptions.",
    ]:
        if caveat in existing_messages:
            messages.append(caveat)
    if not top_rows:
        messages.append("No top impact issues are available for graph rendering.")
    if not weekly_issue_counts:
        messages.append("No week-level issue data is available for graph rendering.")

    return {
        "available": True,
        "top_impact_bars": top_rows,
        "severity_distribution": severity_distribution,
        "impact_composition": impact_composition,
        "weekly_issue_counts": weekly_issue_counts,
        "messages": messages,
    }

def _build_na_kpi_card(title: str, unit: str, subtitle: str, source: str) -> dict[str, Any]:
    return {
        "title": title,
        "value": "N/A",
        "unit": unit,
        "subtitle": subtitle,
        "status": "unknown",
        "source": source,
    }


def _status_from_numeric(value: Any) -> str:
    if value is None:
        return "unknown"
    numeric = _to_float(value)
    return "warning" if numeric > 0 else "normal"


def _build_explicit_pipeline_kpi_cards(view_model: dict[str, Any]) -> list[dict[str, Any]]:
    model = _as_dict(view_model)
    specs = [
        ("Total Business Impact", "", "Directional estimate", "executive_kpi_summary.estimated_total_business_impact"),
        ("Capacity Violations", "records", "Capacity pressure", "capacity_summary.capacity_violation_record_count"),
        ("Management Issues", "issues", "Management attention", "issue_summary.management_issue_candidate_count"),
        ("Health Warnings", "warnings", "Data quality / health", "health_summary.health_issue_count | issue_summary.health_issue_candidate_count"),
        ("Replan Candidates", "candidates", "Candidate-only actions", "len(replan_candidates) | issue_summary.replan_command_candidate_count"),
    ]
    if not model or not bool(model.get("available")):
        return [_build_na_kpi_card(*spec) for spec in specs]

    executive = _as_dict(model.get("executive_kpi_summary", {}))
    capacity = _as_dict(model.get("capacity_summary", {}))
    issue = _as_dict(model.get("issue_summary", {}))
    health = _as_dict(model.get("health_summary", {}))

    impact_value = executive.get("estimated_total_business_impact")
    cards = [
        {
            "title": "Total Business Impact",
            "value": _format_value(impact_value) if impact_value is not None else "N/A",
            "unit": str(executive.get("currency", "") or ""),
            "subtitle": "Directional estimate",
            "status": _status_from_numeric(impact_value) if impact_value is not None else "unknown",
            "source": "executive_kpi_summary.estimated_total_business_impact",
        }
    ]

    card_values = [
        ("Capacity Violations", capacity.get("capacity_violation_record_count"), "records", "Capacity pressure", "capacity_summary.capacity_violation_record_count"),
        ("Management Issues", issue.get("management_issue_candidate_count"), "issues", "Management attention", "issue_summary.management_issue_candidate_count"),
        ("Health Warnings", health.get("health_issue_count", issue.get("health_issue_candidate_count")), "warnings", "Data quality / health", "health_summary.health_issue_count | issue_summary.health_issue_candidate_count"),
    ]
    replan_list = model.get("replan_candidates")
    replan_value = len(replan_list) if isinstance(replan_list, list) else issue.get("replan_command_candidate_count")
    card_values.append(("Replan Candidates", replan_value, "candidates", "Candidate-only actions", "len(replan_candidates) | issue_summary.replan_command_candidate_count"))

    for title, raw_value, unit, subtitle, source in card_values:
        if raw_value is None:
            cards.append(_build_na_kpi_card(title, unit, subtitle, source))
            continue
        cards.append({
            "title": title,
            "value": _format_value(_to_int(raw_value)),
            "unit": unit,
            "subtitle": subtitle,
            "status": _status_from_numeric(raw_value),
            "source": source,
        })
    return cards


def _create_kpi_card(parent: tk.Widget, card: dict[str, Any]) -> ttk.Frame:
    frame = ttk.LabelFrame(parent, text=str(card.get("title", "")), padding=8)
    value = str(card.get("value", "N/A") or "N/A")
    unit = str(card.get("unit", "") or "")
    value_text = value if not unit else f"{value} {unit}"
    ttk.Label(frame, text=value_text, font=("TkDefaultFont", 12, "bold")).pack(anchor="w")
    ttk.Label(frame, text=str(card.get("subtitle", ""))).pack(anchor="w", pady=(2, 0))
    ttk.Label(frame, text=f"Status: {card.get('status', 'unknown')}").pack(anchor="w", pady=(2, 0))
    return frame


def _create_kpi_cards_frame(parent: tk.Widget, cards: list[dict[str, Any]]) -> ttk.Frame:
    frame = ttk.Frame(parent)
    frame.pack(fill="x", pady=(0, 8))
    for i in range(5):
        frame.grid_columnconfigure(i, weight=1)
    for idx, card in enumerate(cards):
        card_frame = _create_kpi_card(frame, card)
        card_frame.grid(row=0, column=idx, sticky="nsew", padx=(0 if idx == 0 else 4, 0))
    return frame


def build_explicit_pipeline_management_cockpit_view_model(env) -> dict:
    pipeline_result = _getattr(env, "explicit_bridge_capacity_pipeline_result")
    capacity_report = _getattr(env, "explicit_bridge_capacity_pipeline_report")
    issue_candidates = _getattr(env, "explicit_bridge_capacity_issue_candidates")
    kpi_bundle = _getattr(env, "explicit_bridge_capacity_issue_candidate_kpi_bundle")
    stack_results = _getattr(env, "explicit_bridge_capacity_reporting_stack_results")

    status = {
        "explicit_pipeline_result": pipeline_result is not None,
        "capacity_report": capacity_report is not None,
        "issue_candidates": issue_candidates is not None,
        "cost_kpi_bundle": kpi_bundle is not None,
        "capacity_report_export": _getattr(env, "explicit_bridge_capacity_pipeline_report_export_result") is not None,
        "issue_candidate_export": _getattr(env, "explicit_bridge_capacity_issue_candidate_export_result") is not None,
        "cost_kpi_export": _getattr(env, "explicit_bridge_capacity_issue_candidate_kpi_export_result") is not None,
        "reporting_stack_results": stack_results is not None,
    }
    available = any(
        status[k]
        for k in [
            "explicit_pipeline_result",
            "capacity_report",
            "issue_candidates",
            "cost_kpi_bundle",
            "reporting_stack_results",
        ]
    )

    messages: list[str] = []
    if not available:
        messages.append("No explicit pipeline reporting data is available. Run planning with explicit pipeline enabled.")

    kpi_summary = _get_summary(kpi_bundle)
    executive_kpi_summary = {
        "currency": str(kpi_summary.get("currency", "") or ""),
        "estimated_total_business_impact": _to_float(kpi_summary.get("estimated_total_business_impact", 0.0)),
        "estimated_lost_sales_value_total": _to_float(kpi_summary.get("estimated_lost_sales_value_total", 0.0)),
        "estimated_margin_impact_total": _to_float(kpi_summary.get("estimated_margin_impact_total", 0.0)),
        "estimated_inventory_cost_impact_total": _to_float(kpi_summary.get("estimated_inventory_cost_impact_total", 0.0)),
        "estimated_capacity_cost_impact_total": _to_float(kpi_summary.get("estimated_capacity_cost_impact_total", 0.0)),
        "estimated_service_penalty_total": _to_float(kpi_summary.get("estimated_service_penalty_total", 0.0)),
        "impact_values_are_directional": bool(kpi_summary.get("impact_values_are_directional", True)),
        "double_counting_possible": bool(kpi_summary.get("double_counting_possible", True)),
    }
    if kpi_bundle is None:
        messages.append("Cost / KPI enrichment is not available or the flag is off.")
    else:
        messages.append("Cost / KPI values are directional scenario estimates, not formal accounting values.")
        messages.append("Double counting may be possible depending on assumptions.")

    cap_sum = _get_summary(capacity_report)
    capacity_summary = {
        "available": capacity_report is not None,
        "capacity_usage_record_count": int(cap_sum.get("capacity_usage_record_count", 0) or 0),
        "capacity_violation_record_count": int(cap_sum.get("capacity_violation_record_count", 0) or 0),
        "lot_exception_record_count": int(cap_sum.get("lot_exception_record_count", 0) or 0),
        "replan_candidate_record_count": int(cap_sum.get("replan_candidate_record_count", 0) or 0),
        "health_check_record_count": int(cap_sum.get("health_check_record_count", 0) or 0),
        "has_error": bool(cap_sum.get("has_error", False)),
        "has_warning": bool(cap_sum.get("has_warning", False)),
    }
    capacity_summary.update(cap_sum)
    capacity_summary["available"] = capacity_report is not None

    issue_sum = _get_summary(issue_candidates)
    issue_summary = {
        "planning_issue_candidate_count": int(issue_sum.get("planning_issue_candidate_count", 0) or 0),
        "management_issue_candidate_count": int(issue_sum.get("management_issue_candidate_count", 0) or 0),
        "replan_command_candidate_count": int(issue_sum.get("replan_command_candidate_count", 0) or 0),
        "health_issue_candidate_count": int(issue_sum.get("health_issue_candidate_count", 0) or 0),
        "error_count": int(issue_sum.get("error_count", 0) or 0),
        "warning_count": int(issue_sum.get("warning_count", 0) or 0),
        "info_count": int(issue_sum.get("info_count", 0) or 0),
        "has_error": bool(issue_sum.get("has_error", False)),
        "has_warning": bool(issue_sum.get("has_warning", False)),
    }
    issue_summary.update(issue_sum)
    for k in ["planning_issue_candidate_count", "management_issue_candidate_count", "replan_command_candidate_count", "health_issue_candidate_count", "error_count", "warning_count", "info_count"]:
        issue_summary[k] = int(issue_summary.get(k, 0) or 0)
    if issue_candidates is None:
        messages.append("Issue candidates are not available or the flag is off.")

    mgmt = _as_list(_getattr(kpi_bundle, "enriched_management_issue_candidates", []))
    planning = _as_list(_getattr(kpi_bundle, "enriched_planning_issue_candidates", []))
    sortable = [x for x in (mgmt + planning) if isinstance(x, dict)]
    sortable.sort(key=lambda r: (-_to_float(r.get("estimated_total_business_impact", 0.0)), _severity_rank(r.get("severity")), str(r.get("issue_type", "")), str(r.get("node", "")), str(r.get("week", ""))))
    top_impact_issues = []
    for idx, row in enumerate(sortable[:10], start=1):
        out = dict(row)
        out.setdefault("severity", "")
        out.setdefault("issue_type", "")
        out.setdefault("impact_category", "")
        out.setdefault("product", "")
        out.setdefault("node", "")
        out.setdefault("week", "")
        out.setdefault("capacity_type", "")
        out.setdefault("lot_ids", [])
        out["estimated_total_business_impact"] = _to_float(out.get("estimated_total_business_impact", 0.0))
        out.setdefault("suggested_action", "")
        out.setdefault("suggested_decision", "")
        out.setdefault("message", "")
        out["rank"] = idx
        top_impact_issues.append(out)

    replan_rows = _as_list(_getattr(kpi_bundle, "enriched_replan_command_candidates", [])) or _as_list(
        _getattr(issue_candidates, "replan_command_candidates", [])
    )
    replan_candidates = []
    for raw in replan_rows:
        if not isinstance(raw, dict):
            continue
        row = dict(raw)
        if "status" in row and row["status"] == "candidate_only":
            pass
        row.setdefault("status", "candidate_only")
        row.setdefault("command_type", "")
        row.setdefault("issue_type", "")
        row.setdefault("product", "")
        row.setdefault("node", "")
        row.setdefault("week", "")
        row.setdefault("expected_benefit_category", "")
        row.setdefault("message", "")
        row.setdefault("suggested_action", "")
        replan_candidates.append(row)

    health_rows = _as_list(_getattr(kpi_bundle, "enriched_health_issue_candidates", [])) or _as_list(_getattr(issue_candidates, "health_issue_candidates", []))
    health_checks = _as_list(_getattr(capacity_report, "health_check_records", []))
    top_health_issues = []
    for src in health_rows[:10]:
        if isinstance(src, dict):
            top_health_issues.append({"severity": src.get("severity", ""), "issue_type": src.get("issue_type", ""), "source": src.get("source", ""), "message": src.get("message", ""), "details": src.get("details", [])})
    if not top_health_issues:
        for src in health_checks[:10]:
            if isinstance(src, dict):
                top_health_issues.append({"severity": src.get("severity", ""), "issue_type": src.get("check_type", ""), "source": src.get("source", ""), "message": src.get("message", ""), "details": src.get("details", [])})
    health_summary = {
        "available": bool(health_rows or health_checks),
        "health_issue_count": len([x for x in health_rows if isinstance(x, dict)]) or int(issue_summary.get("health_issue_candidate_count", 0)),
        "data_quality_risk_issue_count": int(kpi_summary.get("data_quality_risk_issue_count", 0) or 0),
        "missing_lot_count": int(cap_sum.get("missing_lot_count", 0) or 0),
        "non_list_bucket_error_count": sum(1 for x in health_checks if isinstance(x, dict) and x.get("check_type") == "non_list_bucket_error"),
        "non_string_lot_error_count": sum(1 for x in health_checks if isinstance(x, dict) and x.get("check_type") == "non_string_lot_error"),
        "has_error": any(isinstance(x, dict) and str(x.get("severity", "")).lower() == "error" for x in (health_rows + health_checks)),
        "has_warning": any(isinstance(x, dict) and str(x.get("severity", "")).lower() == "warning" for x in (health_rows + health_checks)),
        "top_health_issues": top_health_issues,
    }

    assumptions = _as_dict(_getattr(kpi_bundle, "assumptions", {}))
    assumption_summary = {
        "available": bool(assumptions),
        "currency": str(assumptions.get("currency", "") or ""),
        "product_assumption_keys": sorted(assumptions.keys()),
        "unit_price_products": sorted(_as_dict(assumptions.get("unit_price_by_product", {})).keys()),
        "unit_margin_products": sorted(_as_dict(assumptions.get("unit_margin_by_product", {})).keys()),
        "unit_cost_products": sorted(_as_dict(assumptions.get("unit_cost_by_product", {})).keys()),
        "inventory_holding_cost_products": sorted(_as_dict(assumptions.get("inventory_holding_cost_per_lot_per_week", {})).keys()),
        "capacity_shortage_penalty_types": sorted(_as_dict(assumptions.get("capacity_shortage_penalty_per_lot", {})).keys()),
        "capacity_overtime_cost_types": sorted(_as_dict(assumptions.get("capacity_overtime_cost_per_lot", {})).keys()),
        "service_penalty_products": sorted(_as_dict(assumptions.get("service_penalty_per_lot", {})).keys()),
    }

    export_summary = {
        "capacity_report_export": _export_result_to_summary(_getattr(env, "explicit_bridge_capacity_pipeline_report_export_result")),
        "issue_candidate_export": _export_result_to_summary(_getattr(env, "explicit_bridge_capacity_issue_candidate_export_result")),
        "cost_kpi_export": _export_result_to_summary(_getattr(env, "explicit_bridge_capacity_issue_candidate_kpi_export_result")),
    }
    if not any(x.get("available") for x in export_summary.values()):
        messages.append("Export results are not available. Export flags may be off.")

    next_review_actions = []
    if top_impact_issues:
        next_review_actions.append("Review high impact management issues.")
    if capacity_summary.get("has_warning") or capacity_summary.get("has_error"):
        next_review_actions.append("Check capacity violations with high capacity risk.")
    if health_summary.get("health_issue_count", 0) > 0:
        next_review_actions.append("Review data quality health issues.")
    if assumption_summary.get("available"):
        next_review_actions.append("Validate Cost / KPI assumptions before using estimates.")
    if replan_candidates:
        next_review_actions.append("Consider replan candidates manually; they are not executed automatically.")

    product = (
        str(_getattr(kpi_bundle, "product_name", "") or "")
        or str(kpi_summary.get("product", "") or "")
        or str(_getattr(issue_candidates, "product_name", "") or "")
        or str(_get_summary(issue_candidates).get("product", "") or "")
        or str(_getattr(capacity_report, "product_name", "") or "")
        or str(cap_sum.get("product", "") or "")
        or str(_getattr(pipeline_result, "product_name", "") or "")
    )

    return {
        "available": available,
        "product": product,
        "status": status,
        "executive_kpi_summary": executive_kpi_summary,
        "capacity_summary": capacity_summary,
        "issue_summary": issue_summary,
        "top_impact_issues": top_impact_issues,
        "replan_candidates": replan_candidates,
        "health_summary": health_summary,
        "assumption_summary": assumption_summary,
        "export_summary": export_summary,
        "next_review_actions": next_review_actions,
        "messages": messages,
    }


def render_explicit_pipeline_management_cockpit_tk(parent, view_model: dict) -> tk.Toplevel:
    window = tk.Toplevel(parent)
    window.title("Explicit Pipeline Management Cockpit KPI View")
    window.geometry("1200x750")

    root_frame = ttk.Frame(window, padding=8)
    root_frame.pack(fill="both", expand=True)

    if not bool(view_model.get("available", False)):
        ttk.Label(
            root_frame,
            text="No explicit pipeline reporting data is available.\nRun planning with explicit pipeline enabled.",
            justify="left",
        ).pack(anchor="w", pady=(8, 4))

    notebook = ttk.Notebook(root_frame)
    notebook.pack(fill="both", expand=True)

    summary_tab = ttk.Frame(notebook, padding=8)
    notebook.add(summary_tab, text="Summary")
    status = _as_dict(view_model.get("status", {}))
    executive_kpi_summary = _as_dict(view_model.get("executive_kpi_summary", {}))
    capacity_summary = _as_dict(view_model.get("capacity_summary", {}))
    issue_summary = _as_dict(view_model.get("issue_summary", {}))
    summary_rows = [
        ("Product", _format_value(view_model.get("product", ""))),
        ("Available", _format_value(view_model.get("available", False))),
        ("Explicit Pipeline Result", _format_value(status.get("explicit_pipeline_result", False))),
        ("Capacity Report", _format_value(status.get("capacity_report", False))),
        ("Issue Candidates", _format_value(status.get("issue_candidates", False))),
        ("Cost / KPI Bundle", _format_value(status.get("cost_kpi_bundle", False))),
        ("Total Business Impact", _format_value(executive_kpi_summary.get("estimated_total_business_impact", 0.0))),
        ("Currency", _format_value(executive_kpi_summary.get("currency", ""))),
        ("Capacity Violations", _format_value(capacity_summary.get("capacity_violation_record_count", 0))),
        ("Lot Exceptions", _format_value(capacity_summary.get("lot_exception_record_count", 0))),
        ("Planning Issues", _format_value(issue_summary.get("planning_issue_candidate_count", 0))),
        ("Management Issues", _format_value(issue_summary.get("management_issue_candidate_count", 0))),
        ("Warnings", _format_value(issue_summary.get("warning_count", 0))),
        ("Errors", _format_value(issue_summary.get("error_count", 0))),
    ]
    _create_kpi_cards_frame(summary_tab, _build_explicit_pipeline_kpi_cards(view_model))
    _create_key_value_tree(summary_tab, summary_rows)
    _create_graphs_tab(notebook, build_explicit_pipeline_kpi_graph_view_model(view_model))

    top_issues_tab = ttk.Frame(notebook, padding=8)
    notebook.add(top_issues_tab, text="Top Issues")
    top_impact_issues = _as_list(view_model.get("top_impact_issues", []))
    if top_impact_issues:
        _create_table(
            top_issues_tab,
            ["rank", "severity", "issue_type", "impact_category", "product", "node", "week", "capacity_type", "estimated_total_business_impact", "lot_ids", "message"],
            [row for row in top_impact_issues if isinstance(row, dict)],
        )
    else:
        ttk.Label(top_issues_tab, text="No top impact issues are available.").pack(anchor="w")

    replan_tab = ttk.Frame(notebook, padding=8)
    notebook.add(replan_tab, text="Replan Candidates")
    _create_table(
        replan_tab,
        ["status", "command_type", "issue_type", "product", "node", "week", "expected_benefit_category", "message", "suggested_action"],
        [row for row in _as_list(view_model.get("replan_candidates", [])) if isinstance(row, dict)],
    )

    health_tab = ttk.Frame(notebook, padding=8)
    notebook.add(health_tab, text="Health")
    health_summary = _as_dict(view_model.get("health_summary", {}))
    health_counts = ttk.Frame(health_tab)
    health_counts.pack(fill="x", pady=(0, 8))
    _create_key_value_tree(
        health_counts,
        _rows_from_dict(
            {
                "health_issue_count": health_summary.get("health_issue_count", 0),
                "data_quality_risk_issue_count": health_summary.get("data_quality_risk_issue_count", 0),
                "missing_lot_count": health_summary.get("missing_lot_count", 0),
                "has_error": health_summary.get("has_error", False),
                "has_warning": health_summary.get("has_warning", False),
            }
        ),
    )
    _create_table(
        health_tab,
        ["severity", "issue_type", "source", "message", "details"],
        [row for row in _as_list(health_summary.get("top_health_issues", [])) if isinstance(row, dict)],
    )

    assumptions_exports_tab = ttk.Frame(notebook, padding=8)
    notebook.add(assumptions_exports_tab, text="Assumptions / Exports")
    assumption_summary = _as_dict(view_model.get("assumption_summary", {}))
    ttk.Label(assumptions_exports_tab, text="Assumptions").pack(anchor="w")
    _create_key_value_tree(assumptions_exports_tab, _rows_from_dict(assumption_summary))
    ttk.Label(assumptions_exports_tab, text="Exports").pack(anchor="w", pady=(8, 0))
    export_rows: list[tuple[str, str]] = []
    for name, section in _as_dict(view_model.get("export_summary", {})).items():
        export_rows.append((name, ""))
        export_rows.extend((f"  {k}", _format_value(v)) for k, v in _as_dict(section).items())
    _create_key_value_tree(assumptions_exports_tab, export_rows)

    messages_tab = ttk.Frame(notebook, padding=8)
    notebook.add(messages_tab, text="Messages")
    ttk.Label(messages_tab, text="Messages").pack(anchor="w")
    _create_key_value_tree(messages_tab, [(f"{idx + 1}.", _format_value(msg)) for idx, msg in enumerate(_as_list(view_model.get("messages", [])))])
    ttk.Label(messages_tab, text="Next Review Actions").pack(anchor="w", pady=(8, 0))
    _create_key_value_tree(
        messages_tab,
        [(f"{idx + 1}.", _format_value(msg)) for idx, msg in enumerate(_as_list(view_model.get("next_review_actions", [])))],
    )

    return window
