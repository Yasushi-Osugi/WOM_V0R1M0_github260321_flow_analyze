from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ExplicitPipelineIssueCandidateKPIBundle:
    product_name: str = ""

    enriched_planning_issue_candidates: list[dict] = field(default_factory=list)
    enriched_management_issue_candidates: list[dict] = field(default_factory=list)
    enriched_replan_command_candidates: list[dict] = field(default_factory=list)
    enriched_health_issue_candidates: list[dict] = field(default_factory=list)

    summary: dict[str, Any] = field(default_factory=dict)
    assumptions: dict[str, Any] = field(default_factory=dict)
    message: str = ""


def _to_map(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _extract_quantity(record: dict[str, Any]) -> tuple[float, str]:
    for key in ("quantity", "lot_qty", "qty"):
        raw = record.get(key)
        if isinstance(raw, (int, float)):
            return float(raw), key
    lot_ids = record.get("lot_ids")
    if isinstance(lot_ids, list):
        return float(len(lot_ids)), "lot_count"
    return 0.0, "lot_count"


def _base_enriched(record: dict[str, Any], *, currency: str) -> dict[str, Any]:
    qty, qty_basis = _extract_quantity(record)
    out = dict(record)
    out.update(
        {
            "impact_status": "not_estimated",
            "impact_category": "no_direct_cost_estimate",
            "impact_quantity": qty,
            "impact_quantity_basis": qty_basis,
            "currency": currency,
            "estimated_lost_sales_value": 0.0,
            "estimated_margin_impact": 0.0,
            "estimated_inventory_cost_impact": 0.0,
            "estimated_capacity_cost_impact": 0.0,
            "estimated_service_penalty": 0.0,
            "estimated_total_business_impact": 0.0,
            "kpi_service_risk_score": "none",
            "kpi_inventory_risk_score": "none",
            "kpi_capacity_risk_score": "none",
            "kpi_data_quality_risk_score": "none",
            "cost_kpi_assumption_source": "cost_kpi_context",
        }
    )
    return out


def _set_total(record: dict[str, Any]) -> None:
    record["estimated_total_business_impact"] = (
        float(record.get("estimated_lost_sales_value", 0.0))
        + float(record.get("estimated_margin_impact", 0.0))
        + float(record.get("estimated_inventory_cost_impact", 0.0))
        + float(record.get("estimated_capacity_cost_impact", 0.0))
        + float(record.get("estimated_service_penalty", 0.0))
    )


def enrich_explicit_pipeline_issue_candidates_with_cost_kpi(
    bundle,
    *,
    cost_kpi_context: dict | None = None,
) -> ExplicitPipelineIssueCandidateKPIBundle:
    ctx = _to_map(cost_kpi_context)
    currency = str(ctx.get("currency", ""))
    unit_price = _to_map(ctx.get("unit_price_by_product"))
    unit_margin = _to_map(ctx.get("unit_margin_by_product"))
    inv_holding = _to_map(ctx.get("inventory_holding_cost_per_lot_per_week"))
    capacity_shortage = _to_map(ctx.get("capacity_shortage_penalty_per_lot"))
    service_penalty = _to_map(ctx.get("service_penalty_per_lot"))

    def enrich_planning(item: dict[str, Any]) -> dict[str, Any]:
        row = _base_enriched(item, currency=currency)
        issue_type = str(item.get("issue_type", ""))
        product = str(item.get("product", ""))
        cap_type = str(item.get("capacity_type", ""))
        qty = float(row["impact_quantity"])
        got_any = False

        if issue_type == "capacity_violation":
            row["impact_category"] = "capacity_risk"
            row["kpi_capacity_risk_score"] = "high"
            rate = capacity_shortage.get(cap_type)
            if isinstance(rate, (int, float)):
                row["estimated_capacity_cost_impact"] = qty * float(rate)
                got_any = True
        elif issue_type == "blocked_lot":
            row["impact_category"] = "service_risk"
            row["kpi_service_risk_score"] = "high"
            p = unit_price.get(product)
            if isinstance(p, (int, float)):
                row["estimated_lost_sales_value"] = qty * float(p)
                got_any = True
            m = unit_margin.get(product)
            if isinstance(m, (int, float)):
                row["estimated_margin_impact"] = qty * float(m)
                got_any = True
            s = service_penalty.get(product)
            if isinstance(s, (int, float)):
                row["estimated_service_penalty"] = qty * float(s)
                got_any = True
        elif issue_type == "backlog_lot":
            row["impact_category"] = "service_risk"
            row["kpi_service_risk_score"] = "high"
            s = service_penalty.get(product)
            if isinstance(s, (int, float)):
                row["estimated_service_penalty"] = qty * float(s)
                got_any = True
        elif issue_type == "overflow_inventory":
            row["impact_category"] = "inventory_risk"
            row["kpi_inventory_risk_score"] = "high"
            h = inv_holding.get(product)
            if isinstance(h, (int, float)):
                row["estimated_inventory_cost_impact"] = qty * float(h)
                got_any = True
        elif issue_type == "missing_lot":
            row["impact_category"] = "data_quality_risk"
            row["impact_status"] = "qualitative_only"
            row["kpi_data_quality_risk_score"] = "high"
        elif issue_type == "shifted_lot":
            row["impact_category"] = "no_direct_cost_estimate"
        else:
            row["impact_category"] = "no_direct_cost_estimate"

        if row["impact_status"] != "qualitative_only":
            row["impact_status"] = "estimated" if got_any else "not_estimated"

        _set_total(row)
        return row

    def enrich_management(item: dict[str, Any]) -> dict[str, Any]:
        row = _base_enriched(item, currency=currency)
        issue_type = str(item.get("issue_type", ""))
        product = str(item.get("product", ""))
        cap_type = str(item.get("capacity_type", ""))
        qty = float(row["impact_quantity"])
        got_any = False

        if issue_type in {"capacity_bottleneck", "shipment_capacity_constraint"}:
            row["impact_category"] = "capacity_risk"
            row["kpi_capacity_risk_score"] = "high"
            key = "S" if issue_type == "shipment_capacity_constraint" else cap_type
            rate = capacity_shortage.get(key)
            if isinstance(rate, (int, float)):
                row["estimated_capacity_cost_impact"] = qty * float(rate)
                got_any = True
        elif issue_type == "service_risk":
            row["impact_category"] = "service_risk"
            row["kpi_service_risk_score"] = "high"
            p = unit_price.get(product)
            if isinstance(p, (int, float)):
                row["estimated_lost_sales_value"] = qty * float(p)
                got_any = True
            m = unit_margin.get(product)
            if isinstance(m, (int, float)):
                row["estimated_margin_impact"] = qty * float(m)
                got_any = True
        elif issue_type == "inventory_overflow_risk":
            row["impact_category"] = "inventory_risk"
            row["kpi_inventory_risk_score"] = "high"
            h = inv_holding.get(product)
            if isinstance(h, (int, float)):
                row["estimated_inventory_cost_impact"] = qty * float(h)
                got_any = True
        elif issue_type == "planning_data_quality_risk":
            row["impact_category"] = "data_quality_risk"
            row["impact_status"] = "qualitative_only"
            row["kpi_data_quality_risk_score"] = "high"
        else:
            row["impact_category"] = "no_direct_cost_estimate"

        if row["impact_status"] != "qualitative_only":
            row["impact_status"] = "estimated" if got_any else "not_estimated"

        _set_total(row)
        return row

    def enrich_replan(item: dict[str, Any]) -> dict[str, Any]:
        row = _base_enriched(item, currency=currency)
        row["impact_category"] = "replan_option"
        row["impact_status"] = "qualitative_only"
        action = str(item.get("suggested_action", ""))
        if "capacity" in action:
            row["expected_benefit_category"] = "reduce_capacity_risk"
        elif "service" in action:
            row["expected_benefit_category"] = "reduce_service_risk"
        elif "inventory" in action:
            row["expected_benefit_category"] = "reduce_inventory_risk"
        else:
            row["expected_benefit_category"] = "review_required"
        _set_total(row)
        return row

    def enrich_health(item: dict[str, Any]) -> dict[str, Any]:
        row = _base_enriched(item, currency=currency)
        row["impact_category"] = "data_quality_risk"
        row["impact_status"] = "qualitative_only"
        row["kpi_data_quality_risk_score"] = "high"
        _set_total(row)
        return row

    planning = [enrich_planning(dict(x)) for x in getattr(bundle, "planning_issue_candidates", []) if isinstance(x, dict)]
    management = [enrich_management(dict(x)) for x in getattr(bundle, "management_issue_candidates", []) if isinstance(x, dict)]
    replan = [enrich_replan(dict(x)) for x in getattr(bundle, "replan_command_candidates", []) if isinstance(x, dict)]
    health = [enrich_health(dict(x)) for x in getattr(bundle, "health_issue_candidates", []) if isinstance(x, dict)]

    all_rows = planning + management + replan + health
    summary = {
        "product": getattr(bundle, "product_name", "") or "",
        "currency": currency,
        "planning_issue_candidate_count": len(planning),
        "management_issue_candidate_count": len(management),
        "replan_command_candidate_count": len(replan),
        "health_issue_candidate_count": len(health),
        "estimated_lost_sales_value_total": sum(x["estimated_lost_sales_value"] for x in all_rows),
        "estimated_margin_impact_total": sum(x["estimated_margin_impact"] for x in all_rows),
        "estimated_inventory_cost_impact_total": sum(x["estimated_inventory_cost_impact"] for x in all_rows),
        "estimated_capacity_cost_impact_total": sum(x["estimated_capacity_cost_impact"] for x in all_rows),
        "estimated_service_penalty_total": sum(x["estimated_service_penalty"] for x in all_rows),
        "estimated_total_business_impact": sum(x["estimated_total_business_impact"] for x in all_rows),
        "service_risk_issue_count": sum(1 for x in all_rows if x.get("impact_category") == "service_risk"),
        "inventory_risk_issue_count": sum(1 for x in all_rows if x.get("impact_category") == "inventory_risk"),
        "capacity_risk_issue_count": sum(1 for x in all_rows if x.get("impact_category") == "capacity_risk"),
        "data_quality_risk_issue_count": sum(1 for x in all_rows if x.get("impact_category") == "data_quality_risk"),
        "impact_values_are_directional": True,
        "double_counting_possible": True,
    }

    return ExplicitPipelineIssueCandidateKPIBundle(
        product_name=getattr(bundle, "product_name", "") or "",
        enriched_planning_issue_candidates=planning,
        enriched_management_issue_candidates=management,
        enriched_replan_command_candidates=replan,
        enriched_health_issue_candidates=health,
        summary=summary,
        assumptions=ctx,
        message=getattr(bundle, "message", "") or "",
    )


def maybe_enrich_explicit_pipeline_issue_candidates_with_cost_kpi_from_env(
    env,
    *,
    cost_kpi_context: dict | None = None,
):
    bundle = getattr(env, "explicit_bridge_capacity_issue_candidates", None)
    if bundle is None:
        return None

    kpi_bundle = enrich_explicit_pipeline_issue_candidates_with_cost_kpi(
        bundle,
        cost_kpi_context=cost_kpi_context,
    )
    setattr(env, "explicit_bridge_capacity_issue_candidate_kpi_bundle", kpi_bundle)
    return kpi_bundle


def issue_candidate_kpi_bundle_to_dict(bundle: ExplicitPipelineIssueCandidateKPIBundle) -> dict:
    return asdict(bundle)


def issue_candidate_kpi_bundle_as_rows(bundle: ExplicitPipelineIssueCandidateKPIBundle) -> list[dict]:
    rows: list[dict] = []
    rows.extend(bundle.enriched_planning_issue_candidates)
    rows.extend(bundle.enriched_management_issue_candidates)
    rows.extend(bundle.enriched_replan_command_candidates)
    rows.extend(bundle.enriched_health_issue_candidates)
    return rows
