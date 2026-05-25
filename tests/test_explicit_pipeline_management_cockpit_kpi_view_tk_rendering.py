import copy
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

import pytest

from pysi.gui.explicit_pipeline_management_cockpit_view import (
    build_explicit_pipeline_management_cockpit_view_model,
    render_explicit_pipeline_management_cockpit_tk,
)


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
        "status": {
            "explicit_pipeline_result": True,
            "capacity_report": True,
            "issue_candidates": True,
            "cost_kpi_bundle": True,
            "capacity_report_export": True,
            "issue_candidate_export": True,
            "cost_kpi_export": True,
            "reporting_stack_results": False,
        },
        "executive_kpi_summary": {"currency": "USD", "estimated_total_business_impact": 12345.0},
        "capacity_summary": {"capacity_violation_record_count": 2, "lot_exception_record_count": 1},
        "issue_summary": {"planning_issue_candidate_count": 1, "management_issue_candidate_count": 1, "warning_count": 1, "error_count": 0},
        "top_impact_issues": [
            {
                "rank": 1,
                "severity": "warning",
                "issue_type": "capacity",
                "impact_category": "margin",
                "product": "Widget-A",
                "node": "N1",
                "week": 1,
                "capacity_type": "line",
                "estimated_total_business_impact": 1000.0,
                "lot_ids": ["L1"],
                "message": "Issue",
            }
        ],
        "replan_candidates": [
            {
                "status": "candidate_only",
                "command_type": "capacity_replan",
                "issue_type": "capacity",
                "product": "Widget-A",
                "node": "N1",
                "week": 1,
                "expected_benefit_category": "service",
                "message": "Candidate",
                "suggested_action": "Review manually",
            }
        ],
        "health_summary": {
            "health_issue_count": 1,
            "data_quality_risk_issue_count": 0,
            "missing_lot_count": 0,
            "has_error": False,
            "has_warning": True,
            "top_health_issues": [
                {
                    "severity": "warning",
                    "issue_type": "data_quality",
                    "source": "health_check",
                    "message": "Potential issue",
                    "details": ["detail"],
                }
            ],
        },
        "assumption_summary": {
            "available": True,
            "currency": "USD",
            "unit_price_products": ["Widget-A"],
            "unit_margin_products": ["Widget-A"],
            "unit_cost_products": ["Widget-A"],
            "inventory_holding_cost_products": ["Widget-A"],
            "capacity_shortage_penalty_types": ["line"],
            "capacity_overtime_cost_types": ["line"],
            "service_penalty_products": ["Widget-A"],
        },
        "export_summary": {
            "capacity_report_export": {"available": True, "output_dir": "/tmp/out", "file_count": 1, "summary_path": "/tmp/out/summary.json", "assumptions_path": "/tmp/out/assumptions.json", "message": "ok"},
            "issue_candidate_export": {"available": True, "output_dir": "/tmp/out", "file_count": 1, "summary_path": "/tmp/out/summary.json", "assumptions_path": "/tmp/out/assumptions.json", "message": "ok"},
            "cost_kpi_export": {"available": True, "output_dir": "/tmp/out", "file_count": 1, "summary_path": "/tmp/out/summary.json", "assumptions_path": "/tmp/out/assumptions.json", "message": "ok"},
        },
        "next_review_actions": ["Review high impact issues"],
        "messages": ["Cost / KPI values are directional scenario estimates, not formal accounting values."],
    }


def test_render_no_data_view_model():
    root = _make_root_or_skip()
    try:
        vm = build_explicit_pipeline_management_cockpit_view_model(SimpleNamespace())
        window = render_explicit_pipeline_management_cockpit_tk(root, vm)
        assert isinstance(window, tk.Toplevel)
        assert "Explicit Pipeline" in window.title()
        window.destroy()
    finally:
        root.destroy()


def test_render_populated_view_model_no_exception():
    root = _make_root_or_skip()
    try:
        vm = _sample_view_model()
        window = render_explicit_pipeline_management_cockpit_tk(root, vm)
        assert isinstance(window, tk.Toplevel)
        window.destroy()
    finally:
        root.destroy()


def test_candidate_only_visibility_and_no_side_effects():
    root = _make_root_or_skip()
    try:
        vm = _sample_view_model()
        baseline = copy.deepcopy(vm)
        window = render_explicit_pipeline_management_cockpit_tk(root, vm)

        notebook = _find_widget(window, ttk.Notebook)
        assert notebook is not None
        assert "candidate_only" in str(vm["replan_candidates"])
        assert vm == baseline

        assert isinstance(notebook, tk.Widget)
        window.destroy()
    finally:
        root.destroy()
