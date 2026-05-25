from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ExplicitPipelineIssueCandidateBundle:
    product_name: str = ""

    planning_issue_candidates: list[dict] = field(default_factory=list)
    management_issue_candidates: list[dict] = field(default_factory=list)
    replan_command_candidates: list[dict] = field(default_factory=list)
    health_issue_candidates: list[dict] = field(default_factory=list)

    summary: dict[str, Any] = field(default_factory=dict)
    message: str = ""


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    return []


def _as_record(item: Any) -> dict[str, Any]:
    return dict(item) if isinstance(item, dict) else {}


def _normalized_severity(value: Any, default: str) -> str:
    if isinstance(value, str) and value.lower() in {"error", "warning", "info"}:
        return value.lower()
    return default


def _extract_lot_ids(record: dict[str, Any]) -> list[str]:
    lot_ids = record.get("lot_ids")
    if isinstance(lot_ids, list):
        return [x for x in lot_ids if isinstance(x, str)]
    lot_id = record.get("lot_id")
    if isinstance(lot_id, str):
        return [lot_id]
    return []


def build_explicit_pipeline_issue_candidates(report, *, product_name: str | None = None) -> ExplicitPipelineIssueCandidateBundle:
    product = product_name or getattr(report, "product_name", "") or ""
    message = getattr(report, "message", "") or ""

    planning_issue_candidates: list[dict] = []
    management_issue_candidates: list[dict] = []
    replan_command_candidates: list[dict] = []
    health_issue_candidates: list[dict] = []

    for raw in _as_list(getattr(report, "capacity_violation_records", [])):
        row = _as_record(raw)
        severity = _normalized_severity(row.get("severity"), "warning")
        lot_ids = _extract_lot_ids(row)
        node = row.get("node", "")
        week = row.get("week")
        capacity_type = row.get("capacity_type", "")

        planning_issue_candidates.append(
            {
                "candidate_type": "planning_issue",
                "issue_type": "capacity_violation",
                "severity": severity,
                "product": row.get("product", product) or product,
                "node": node,
                "week": week,
                "capacity_type": capacity_type,
                "lot_ids": lot_ids,
                "evidence_record_type": "capacity_violation",
                "source": "explicit_pipeline_capacity_report",
                "message": f"{capacity_type} capacity violation at {node} week {week}",
                "suggested_action": "review_capacity_or_rerun_backward_planning",
            }
        )

        if severity in {"warning", "error"}:
            issue_type = {
                "P": "capacity_bottleneck",
                "S": "shipment_capacity_constraint",
                "I": "inventory_overflow_risk",
            }.get(capacity_type, "capacity_bottleneck")
            management_issue_candidates.append(
                {
                    "candidate_type": "management_issue",
                    "issue_type": issue_type,
                    "severity": severity,
                    "product": row.get("product", product) or product,
                    "node": node,
                    "week": week,
                    "capacity_type": capacity_type,
                    "lot_ids": lot_ids,
                    "business_theme": "supply_capacity_constraint",
                    "evidence_record_type": "capacity_violation",
                    "source": "explicit_pipeline_capacity_report",
                    "message": f"Capacity bottleneck candidate detected at {node} week {week}",
                    "suggested_decision": "review capacity, allocation policy, or early-build scenario",
                }
            )

    lot_map = {
        "blocked": ("blocked_lot", "warning", "service_risk", True),
        "overflow_i": ("overflow_inventory", "warning", "inventory_overflow_risk", True),
        "backlog": ("backlog_lot", "warning", "service_risk", True),
        "shifted": ("shifted_lot", "info", None, False),
        "missing": ("missing_lot", "error", "planning_data_quality_risk", True),
    }
    for raw in _as_list(getattr(report, "lot_exception_records", [])):
        row = _as_record(raw)
        exception_type = row.get("exception_type", "")
        mapped = lot_map.get(exception_type)
        if mapped is None:
            continue
        issue_type, default_severity, mgmt_issue_type, elevate = mapped
        severity = _normalized_severity(row.get("severity"), default_severity)
        lot_ids = _extract_lot_ids(row)

        planning_issue_candidates.append(
            {
                "candidate_type": "planning_issue",
                "issue_type": issue_type,
                "severity": severity,
                "product": row.get("product", product) or product,
                "node": row.get("node", ""),
                "week": row.get("week"),
                "lot_ids": lot_ids,
                "evidence_record_type": "lot_exception",
                "source": "explicit_pipeline_capacity_report",
                "message": row.get("message") or f"Lot exception detected: {exception_type}",
                "suggested_action": "review_capacity_or_rerun_backward_planning",
            }
        )

        if elevate and mgmt_issue_type:
            management_issue_candidates.append(
                {
                    "candidate_type": "management_issue",
                    "issue_type": mgmt_issue_type,
                    "severity": severity,
                    "product": row.get("product", product) or product,
                    "node": row.get("node", ""),
                    "week": row.get("week"),
                    "lot_ids": lot_ids,
                    "business_theme": "supply_execution_risk",
                    "evidence_record_type": "lot_exception",
                    "source": "explicit_pipeline_capacity_report",
                    "message": f"Management issue candidate detected from lot exception: {exception_type}",
                    "suggested_decision": "review capacity, allocation policy, or early-build scenario",
                }
            )

        if exception_type == "missing":
            health_issue_candidates.append(
                {
                    "candidate_type": "health_issue",
                    "issue_type": "missing_lot",
                    "severity": "error",
                    "product": row.get("product", product) or product,
                    "details": lot_ids,
                    "evidence_record_type": "lot_exception",
                    "source": "explicit_pipeline_capacity_report",
                    "message": "Structural PSI health issue detected",
                }
            )

    for raw in _as_list(getattr(report, "health_check_records", [])):
        row = _as_record(raw)
        severity = _normalized_severity(row.get("severity"), "error")
        issue_type = row.get("check_type", "unknown_health_check")
        issue = {
            "candidate_type": "health_issue",
            "issue_type": issue_type,
            "severity": severity,
            "product": product,
            "details": _as_list(row.get("details", [])),
            "evidence_record_type": "health_check",
            "source": "explicit_pipeline_capacity_report",
            "message": "Structural PSI health issue detected",
        }
        health_issue_candidates.append(issue)

        if severity == "error":
            management_issue_candidates.append(
                {
                    "candidate_type": "management_issue",
                    "issue_type": "planning_data_quality_risk",
                    "severity": "error",
                    "product": product,
                    "node": row.get("node", ""),
                    "week": row.get("week"),
                    "lot_ids": _extract_lot_ids(row),
                    "business_theme": "planning_data_quality",
                    "evidence_record_type": "health_check",
                    "source": "explicit_pipeline_capacity_report",
                    "message": "Data quality management issue candidate detected from health check",
                    "suggested_decision": "review data quality and lot structure integrity",
                }
            )

    for raw in _as_list(getattr(report, "replan_candidate_records", [])):
        row = _as_record(raw)
        replan_command_candidates.append(
            {
                "candidate_type": "replan_command_candidate",
                "command_type": row.get("command_type", "capacity_replan"),
                "status": "candidate_only",
                "product": row.get("product", product) or product,
                "node": row.get("node", ""),
                "week": row.get("week"),
                "capacity_type": row.get("capacity_type", ""),
                "lot_ids": _extract_lot_ids(row),
                "source": "explicit_pipeline_capacity_report",
                "message": "Candidate replan command generated from capacity report",
                "suggested_action": row.get(
                    "suggested_action", "review_capacity_or_rerun_backward_planning"
                ),
            }
        )

    sev = {"error": 0, "warning": 0, "info": 0}
    for bucket in (
        planning_issue_candidates,
        management_issue_candidates,
        replan_command_candidates,
        health_issue_candidates,
    ):
        for item in bucket:
            level = item.get("severity")
            if level in sev:
                sev[level] += 1

    summary = {
        "product": product,
        "planning_issue_candidate_count": len(planning_issue_candidates),
        "management_issue_candidate_count": len(management_issue_candidates),
        "replan_command_candidate_count": len(replan_command_candidates),
        "health_issue_candidate_count": len(health_issue_candidates),
        "error_count": sev["error"],
        "warning_count": sev["warning"],
        "info_count": sev["info"],
        "has_error": sev["error"] > 0,
        "has_warning": sev["warning"] > 0,
    }

    return ExplicitPipelineIssueCandidateBundle(
        product_name=product,
        planning_issue_candidates=planning_issue_candidates,
        management_issue_candidates=management_issue_candidates,
        replan_command_candidates=replan_command_candidates,
        health_issue_candidates=health_issue_candidates,
        summary=summary,
        message=message,
    )


def issue_candidates_to_dict(bundle: ExplicitPipelineIssueCandidateBundle) -> dict:
    return asdict(bundle)


def issue_candidates_as_rows(bundle: ExplicitPipelineIssueCandidateBundle) -> list[dict]:
    rows: list[dict] = []
    rows.extend(bundle.planning_issue_candidates)
    rows.extend(bundle.management_issue_candidates)
    rows.extend(bundle.replan_command_candidates)
    rows.extend(bundle.health_issue_candidates)
    return rows


def maybe_build_explicit_pipeline_issue_candidates_from_env(env):
    report = getattr(env, "explicit_bridge_capacity_pipeline_report", None)
    if report is None:
        return None

    bundle = build_explicit_pipeline_issue_candidates(report)
    setattr(env, "explicit_bridge_capacity_issue_candidates", bundle)
    return bundle
