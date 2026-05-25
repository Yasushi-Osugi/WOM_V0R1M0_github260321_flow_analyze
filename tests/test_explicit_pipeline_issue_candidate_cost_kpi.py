from types import SimpleNamespace

from pysi.reporting.explicit_pipeline_issue_candidates import ExplicitPipelineIssueCandidateBundle
from pysi.reporting.explicit_pipeline_issue_candidate_cost_kpi import (
    enrich_explicit_pipeline_issue_candidates_with_cost_kpi,
    issue_candidate_kpi_bundle_as_rows,
    issue_candidate_kpi_bundle_to_dict,
    maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env,
)


def _sample_bundle() -> ExplicitPipelineIssueCandidateBundle:
    return ExplicitPipelineIssueCandidateBundle(
        product_name="RICE",
        planning_issue_candidates=[
            {"issue_type": "blocked_lot", "product": "RICE", "node": "N1", "week": 1, "lot_ids": ["L1", "L2"]},
            {"issue_type": "overflow_inventory", "product": "RICE", "node": "N1", "week": 1, "lot_ids": ["L3"]},
            {"issue_type": "capacity_violation", "product": "RICE", "node": "N2", "week": 2, "capacity_type": "P", "lot_ids": ["L4", "L5", "L6"]},
            {"issue_type": "missing_lot", "product": "RICE", "node": "N2", "week": 2, "lot_ids": ["M1"]},
        ],
        management_issue_candidates=[
            {"issue_type": "service_risk", "product": "RICE", "node": "N3", "week": 2, "lot_ids": ["L7"]},
            {"issue_type": "capacity_bottleneck", "product": "RICE", "node": "N3", "week": 2, "capacity_type": "P", "lot_ids": ["L8", "L9"]},
        ],
        replan_command_candidates=[
            {
                "candidate_type": "replan_command_candidate",
                "status": "candidate_only",
                "product": "RICE",
                "node": "N4",
                "week": 3,
                "capacity_type": "P",
                "lot_ids": ["L10"],
                "suggested_action": "review_capacity_or_rerun_backward_planning",
            }
        ],
        health_issue_candidates=[
            {"issue_type": "non_string_lot_error", "product": "RICE", "details": ["bad lot"]}
        ],
    )


def _context() -> dict:
    return {
        "currency": "JPY",
        "unit_price_by_product": {"RICE": 1000.0},
        "unit_margin_by_product": {"RICE": 250.0},
        "inventory_holding_cost_per_lot_per_week": {"RICE": 10.0},
        "capacity_shortage_penalty_per_lot": {"P": 100.0, "S": 80.0},
        "service_penalty_per_lot": {"RICE": 200.0},
    }


def test_enrich_with_assumptions_and_summary_totals():
    bundle = _sample_bundle()
    enriched = enrich_explicit_pipeline_issue_candidates_with_cost_kpi(bundle, cost_kpi_context=_context())

    blocked = enriched.enriched_planning_issue_candidates[0]
    assert blocked["estimated_lost_sales_value"] == 2000.0
    assert blocked["estimated_margin_impact"] == 500.0
    assert blocked["estimated_service_penalty"] == 400.0
    assert blocked["impact_status"] == "estimated"

    overflow = enriched.enriched_planning_issue_candidates[1]
    assert overflow["estimated_inventory_cost_impact"] == 10.0

    violation = enriched.enriched_planning_issue_candidates[2]
    assert violation["estimated_capacity_cost_impact"] == 300.0
    assert violation["kpi_capacity_risk_score"] == "high"

    missing = enriched.enriched_planning_issue_candidates[3]
    assert missing["impact_status"] == "qualitative_only"

    mgmt_service = enriched.enriched_management_issue_candidates[0]
    assert mgmt_service["estimated_lost_sales_value"] == 1000.0
    assert mgmt_service["estimated_margin_impact"] == 250.0

    mgmt_cap = enriched.enriched_management_issue_candidates[1]
    assert mgmt_cap["estimated_capacity_cost_impact"] == 200.0

    assert enriched.enriched_replan_command_candidates[0]["status"] == "candidate_only"
    assert enriched.enriched_health_issue_candidates[0]["impact_status"] == "qualitative_only"

    rows = issue_candidate_kpi_bundle_as_rows(enriched)
    assert enriched.summary["estimated_total_business_impact"] == sum(
        x["estimated_total_business_impact"] for x in rows
    )
    assert enriched.summary["service_risk_issue_count"] == 2
    assert enriched.summary["inventory_risk_issue_count"] == 1
    assert enriched.summary["capacity_risk_issue_count"] == 2
    assert enriched.summary["data_quality_risk_issue_count"] == 2
    assert enriched.summary["currency"] == "JPY"


def test_missing_assumptions_still_enriches_without_errors():
    enriched = enrich_explicit_pipeline_issue_candidates_with_cost_kpi(_sample_bundle(), cost_kpi_context={})
    rows = issue_candidate_kpi_bundle_as_rows(enriched)
    assert rows
    for row in rows:
        assert row["impact_status"] in {"not_estimated", "qualitative_only"}
        assert row["estimated_lost_sales_value"] == 0.0
        assert row["estimated_margin_impact"] == 0.0
        assert row["estimated_inventory_cost_impact"] == 0.0
        assert row["estimated_capacity_cost_impact"] == 0.0
        assert row["estimated_service_penalty"] == 0.0


def test_lot_id_preservation_and_serialization_helpers():
    enriched = enrich_explicit_pipeline_issue_candidates_with_cost_kpi(_sample_bundle(), cost_kpi_context=_context())
    assert enriched.enriched_planning_issue_candidates[0]["lot_ids"] == ["L1", "L2"]
    assert isinstance(issue_candidate_kpi_bundle_to_dict(enriched), dict)
    assert isinstance(issue_candidate_kpi_bundle_as_rows(enriched), list)


def test_env_helper_noop_and_attach():
    env = SimpleNamespace()
    assert maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env(env) is None

    env.explicit_bridge_capacity_issue_candidates = _sample_bundle()
    result = maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env(
        env,
        cost_kpi_context=_context(),
    )
    assert result is env.explicit_bridge_capacity_issue_candidate_kpi_bundle
