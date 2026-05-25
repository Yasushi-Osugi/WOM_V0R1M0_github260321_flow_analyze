import copy
import tkinter as tk
from tkinter import ttk

import pytest

from pysi.gui.explicit_pipeline_management_cockpit_view import render_explicit_pipeline_management_cockpit_tk


def _make_root_or_skip():
    try:
        root = tk.Tk()
        root.withdraw()
        return root
    except tk.TclError as exc:
        pytest.skip(f"Tk unavailable: {exc}")


def _find_widget(root, widget_type):
    if isinstance(root, widget_type):
        return root
    for child in root.winfo_children():
        found = _find_widget(child, widget_type)
        if found is not None:
            return found
    return None


def _sample_view_model():
    return {
        "available": True,
        "product": "Widget-A",
        "status": {},
        "executive_kpi_summary": {
            "currency": "USD",
            "estimated_total_business_impact": 12000.0,
            "estimated_lost_sales_value_total": 8000.0,
            "estimated_margin_impact_total": 1500.0,
            "estimated_inventory_cost_impact_total": 1200.0,
            "estimated_capacity_cost_impact_total": 800.0,
            "estimated_service_penalty_total": 500.0,
        },
        "capacity_summary": {},
        "issue_summary": {"error_count": 1, "warning_count": 2, "info_count": 3},
        "top_impact_issues": [
            {
                "rank": 1,
                "severity": "error",
                "issue_type": "capacity",
                "impact_category": "lost_sales",
                "product": "Widget-A",
                "node": "N1",
                "week": "W01",
                "estimated_total_business_impact": 10000.0,
            },
            {
                "rank": 2,
                "severity": "warning",
                "issue_type": "service",
                "impact_category": "penalty",
                "product": "Widget-A",
                "node": "N2",
                "week": "W02",
                "estimated_total_business_impact": 2000.0,
            },
        ],
        "replan_candidates": [],
        "health_summary": {"top_health_issues": []},
        "assumption_summary": {},
        "export_summary": {},
        "next_review_actions": [],
        "messages": [
            "Cost / KPI values are directional scenario estimates, not formal accounting values.",
            "Double counting may be possible depending on assumptions.",
        ],
    }


def _tab_texts(notebook: ttk.Notebook):
    return [notebook.tab(tab_id, "text") for tab_id in notebook.tabs()]


def test_graphs_tab_appears():
    root = _make_root_or_skip()
    try:
        window = render_explicit_pipeline_management_cockpit_tk(root, _sample_view_model())
        notebook = _find_widget(window, ttk.Notebook)
        assert notebook is not None
        assert "Graphs" in _tab_texts(notebook)
        window.destroy()
    finally:
        root.destroy()


def test_graphs_tab_exists_for_empty_model():
    root = _make_root_or_skip()
    try:
        window = render_explicit_pipeline_management_cockpit_tk(root, {"available": False})
        assert isinstance(window, tk.Toplevel)
        notebook = _find_widget(window, ttk.Notebook)
        assert notebook is not None
        assert "Graphs" in _tab_texts(notebook)
        window.destroy()
    finally:
        root.destroy()


def test_populated_model_renders_with_graphs_tab():
    root = _make_root_or_skip()
    try:
        window = render_explicit_pipeline_management_cockpit_tk(root, _sample_view_model())
        assert isinstance(window, tk.Toplevel)
        notebook = _find_widget(window, ttk.Notebook)
        assert notebook is not None
        assert "Graphs" in _tab_texts(notebook)
        window.destroy()
    finally:
        root.destroy()


def test_core_tabs_still_present_with_graphs():
    root = _make_root_or_skip()
    try:
        window = render_explicit_pipeline_management_cockpit_tk(root, _sample_view_model())
        notebook = _find_widget(window, ttk.Notebook)
        assert notebook is not None
        tabs = _tab_texts(notebook)
        for required in ["Summary", "Graphs", "Top Issues", "Replan Candidates", "Health", "Assumptions / Exports", "Messages"]:
            assert required in tabs
        window.destroy()
    finally:
        root.destroy()


def test_renderer_has_no_side_effects_on_input_view_model():
    root = _make_root_or_skip()
    try:
        view_model = _sample_view_model()
        baseline = copy.deepcopy(view_model)
        window = render_explicit_pipeline_management_cockpit_tk(root, view_model)
        assert view_model == baseline
        window.destroy()
    finally:
        root.destroy()
