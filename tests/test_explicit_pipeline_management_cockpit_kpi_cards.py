import copy
import tkinter as tk
from tkinter import ttk

import pytest

from pysi.gui.explicit_pipeline_management_cockpit_view import (
    _build_explicit_pipeline_kpi_cards,
    render_explicit_pipeline_management_cockpit_tk,
)

EXPECTED_TITLES = [
    "Total Business Impact",
    "Capacity Violations",
    "Management Issues",
    "Health Warnings",
    "Replan Candidates",
]


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


def _collect_label_texts(root):
    texts = []
    if isinstance(root, ttk.Label):
        texts.append(str(root.cget("text")))
    if isinstance(root, ttk.LabelFrame):
        texts.append(str(root.cget("text")))
    for child in root.winfo_children():
        texts.extend(_collect_label_texts(child))
    return texts


def test_kpi_cards_populated_view_model():
    view_model = {
        "available": True,
        "executive_kpi_summary": {"estimated_total_business_impact": 1250000, "currency": "JPY"},
        "capacity_summary": {"capacity_violation_record_count": 2},
        "issue_summary": {
            "management_issue_candidate_count": 3,
            "health_issue_candidate_count": 1,
            "replan_command_candidate_count": 9,
        },
        "health_summary": {"health_issue_count": 4},
        "replan_candidates": [{"id": 1}, {"id": 2}],
    }

    cards = _build_explicit_pipeline_kpi_cards(view_model)
    assert len(cards) == 5
    assert [c["title"] for c in cards] == EXPECTED_TITLES
    assert cards[0]["value"] == "1,250,000"
    assert cards[0]["unit"] == "JPY"
    assert cards[0]["status"] == "warning"
    assert cards[1]["value"] == "2"
    assert cards[1]["unit"] == "records"
    assert cards[2]["value"] == "3"
    assert cards[2]["unit"] == "issues"
    assert cards[3]["value"] == "4"
    assert cards[3]["unit"] == "warnings"
    assert cards[4]["value"] == "2"
    assert cards[4]["unit"] == "candidates"


def test_kpi_cards_no_data_view_model():
    cards = _build_explicit_pipeline_kpi_cards({"available": False})
    assert len(cards) == 5
    assert [c["title"] for c in cards] == EXPECTED_TITLES
    assert all(c["value"] == "N/A" for c in cards)
    assert all(c["status"] == "unknown" for c in cards)


def test_summary_tab_renders_cards_and_tabs_and_no_mutation():
    root = _make_root_or_skip()
    try:
        vm = {
            "available": True,
            "product": "Widget-A",
            "status": {},
            "executive_kpi_summary": {"estimated_total_business_impact": 100, "currency": "USD"},
            "capacity_summary": {"capacity_violation_record_count": 1, "lot_exception_record_count": 0},
            "issue_summary": {
                "planning_issue_candidate_count": 0,
                "management_issue_candidate_count": 1,
                "warning_count": 1,
                "error_count": 0,
                "health_issue_candidate_count": 1,
                "replan_command_candidate_count": 1,
            },
            "top_impact_issues": [],
            "replan_candidates": [{"status": "candidate_only"}],
            "health_summary": {"health_issue_count": 1, "top_health_issues": []},
            "assumption_summary": {},
            "export_summary": {},
            "messages": [],
            "next_review_actions": [],
        }
        baseline = copy.deepcopy(vm)
        _ = _build_explicit_pipeline_kpi_cards(vm)
        window = render_explicit_pipeline_management_cockpit_tk(root, vm)
        notebook = _find_widget(window, ttk.Notebook)
        assert notebook is not None
        tabs = [notebook.tab(tab_id, "text") for tab_id in notebook.tabs()]
        assert tabs == ["Summary", "Graphs", "Top Issues", "Replan Candidates", "Health", "Assumptions / Exports", "Messages"]
        all_texts = _collect_label_texts(window)
        for title in EXPECTED_TITLES:
            assert title in all_texts
        assert vm == baseline
        window.destroy()
    finally:
        root.destroy()
