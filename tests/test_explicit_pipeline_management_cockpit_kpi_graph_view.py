from __future__ import annotations

import copy

from pysi.gui.explicit_pipeline_management_cockpit_view import (
    build_explicit_pipeline_kpi_graph_view_model,
)


def test_graph_view_model_no_data_unavailable():
    out = build_explicit_pipeline_kpi_graph_view_model({})
    assert out["available"] is False
    assert out["top_impact_bars"] == []
    assert out["severity_distribution"] == {"error": 0, "warning": 0, "info": 0}
    assert out["impact_composition"] == []
    assert out["weekly_issue_counts"] == []


def test_graph_view_model_top_impact_sort_and_label_and_fields():
    vm = {
        "available": True,
        "top_impact_issues": [
            {"issue_type": "late", "node": "N2", "week": "12", "severity": "warning", "estimated_total_business_impact": 20},
            {"issue_type": "short", "node": "N1", "week": "10", "severity": "error", "estimated_total_business_impact": 100},
            {"issue_type": "cap", "node": "N3", "week": "11", "severity": "info", "estimated_total_business_impact": 50},
        ],
    }
    out = build_explicit_pipeline_kpi_graph_view_model(vm)
    bars = out["top_impact_bars"]
    assert [b["value"] for b in bars] == [100.0, 50.0, 20.0]
    assert bars[0]["label"] == "short / N1 / W10"
    assert bars[0]["severity"] == "error"
    assert bars[0]["issue_type"] == "short"
    assert bars[0]["node"] == "N1"
    assert bars[0]["week"] == "10"


def test_graph_view_model_top_10_limit():
    vm = {
        "available": True,
        "top_impact_issues": [
            {"issue_type": f"i{i}", "node": "N", "week": str(i), "severity": "warning", "estimated_total_business_impact": i}
            for i in range(12)
        ],
    }
    out = build_explicit_pipeline_kpi_graph_view_model(vm)
    assert len(out["top_impact_bars"]) == 10


def test_graph_view_model_severity_distribution_from_issue_summary():
    vm = {
        "available": True,
        "issue_summary": {"error_count": 1, "warning_count": 2, "info_count": 3},
    }
    out = build_explicit_pipeline_kpi_graph_view_model(vm)
    assert out["severity_distribution"] == {"error": 1, "warning": 2, "info": 3}


def test_graph_view_model_impact_composition_rows():
    vm = {
        "available": True,
        "executive_kpi_summary": {
            "estimated_lost_sales_value_total": 10,
            "estimated_margin_impact_total": 20,
            "estimated_inventory_cost_impact_total": 30,
            "estimated_capacity_cost_impact_total": 40,
            "estimated_service_penalty_total": 50,
        },
    }
    out = build_explicit_pipeline_kpi_graph_view_model(vm)
    assert out["impact_composition"] == [
        {"label": "Lost Sales", "value": 10.0},
        {"label": "Margin Impact", "value": 20.0},
        {"label": "Inventory Cost", "value": 30.0},
        {"label": "Capacity Cost", "value": 40.0},
        {"label": "Service Penalty", "value": 50.0},
    ]


def test_graph_view_model_weekly_issue_counts():
    vm = {
        "available": True,
        "top_impact_issues": [
            {"week": "12", "estimated_total_business_impact": 1},
            {"week": "12", "estimated_total_business_impact": 2},
            {"week": "13", "estimated_total_business_impact": 3},
        ],
    }
    out = build_explicit_pipeline_kpi_graph_view_model(vm)
    assert out["weekly_issue_counts"] == [{"week": "12", "count": 2}, {"week": "13", "count": 1}]


def test_graph_view_model_does_not_mutate_input():
    vm = {
        "available": True,
        "top_impact_issues": [{"issue_type": "x", "node": "N", "week": "2", "estimated_total_business_impact": "10"}],
        "messages": ["Cost / KPI values are directional scenario estimates, not formal accounting values."],
    }
    before = copy.deepcopy(vm)
    _ = build_explicit_pipeline_kpi_graph_view_model(vm)
    assert vm == before


def test_graph_view_model_missing_invalid_values_safe_defaults():
    vm = {
        "available": True,
        "top_impact_issues": [
            {"issue_type": None, "node": None, "week": None, "estimated_total_business_impact": "bad"},
            {"issue_type": "x", "node": "n", "week": "W2", "estimated_total_business_impact": None},
        ],
        "issue_summary": {"error_count": None, "warning_count": "2", "info_count": "bad"},
    }
    out = build_explicit_pipeline_kpi_graph_view_model(vm)
    assert out["top_impact_bars"][0]["value"] == 0.0
    assert out["severity_distribution"] == {"error": 0, "warning": 2, "info": 0}
