from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ExplicitPipelineCapacityReport:
    product_name: str = ""

    capacity_usage_records: list[dict] = field(default_factory=list)
    capacity_violation_records: list[dict] = field(default_factory=list)
    lot_exception_records: list[dict] = field(default_factory=list)
    replan_candidate_records: list[dict] = field(default_factory=list)
    health_check_records: list[dict] = field(default_factory=list)

    summary: dict[str, Any] = field(default_factory=dict)
    message: str = ""


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    return []


def _as_record(item: Any) -> dict[str, Any]:
    return dict(item) if isinstance(item, dict) else {}


def build_explicit_pipeline_capacity_report(
    pipeline_result,
    *,
    product_name: str | None = None,
) -> ExplicitPipelineCapacityReport:
    product = product_name or getattr(pipeline_result, "product_name", "") or ""
    message = getattr(pipeline_result, "message", "") or ""

    missing_lot_ids = _as_list(getattr(pipeline_result, "missing_lot_ids", []))
    blocked_lot_ids = _as_list(getattr(pipeline_result, "blocked_lot_ids", []))
    overflow_i_lot_ids = _as_list(getattr(pipeline_result, "overflow_i_lot_ids", []))
    backlog_lot_ids = _as_list(getattr(pipeline_result, "backlog_lot_ids", []))
    shifted_lot_ids = _as_list(getattr(pipeline_result, "shifted_lot_ids", []))
    non_list_bucket_errors = _as_list(getattr(pipeline_result, "non_list_bucket_errors", []))
    non_string_lot_errors = _as_list(getattr(pipeline_result, "non_string_lot_errors", []))

    capacity_usage_records: list[dict] = []
    for raw in _as_list(getattr(pipeline_result, "capacity_usage", [])):
        row = _as_record(raw)
        row.setdefault("record_type", "capacity_usage")
        row.setdefault("product", product)
        row.setdefault("node", "")
        row.setdefault("week", None)
        row.setdefault("capacity_type", "")
        row.setdefault("capacity", None)
        row.setdefault("used", None)
        row.setdefault("remaining", None)
        row.setdefault("source", "explicit_bridge_capacity_pipeline")
        capacity_usage_records.append(row)

    capacity_violation_records: list[dict] = []
    for raw in _as_list(getattr(pipeline_result, "capacity_violations", [])):
        row = _as_record(raw)
        row.setdefault("record_type", "capacity_violation")
        row.setdefault("product", product)
        row.setdefault("node", "")
        row.setdefault("week", None)
        row.setdefault("capacity_type", "")
        row.setdefault("severity", "warning")
        row.setdefault("lot_ids", [])
        row.setdefault("source", "explicit_bridge_capacity_pipeline")
        capacity_violation_records.append(row)

    lot_exception_specs = {
        "missing": (
            missing_lot_ids,
            "Lot missing from final demand/supply/backlog/blocked/overflow universe",
        ),
        "blocked": (blocked_lot_ids, "Lot blocked by capacity"),
        "overflow_i": (overflow_i_lot_ids, "Lot contributes to inventory overflow"),
        "backlog": (backlog_lot_ids, "Lot remains in backlog"),
        "shifted": (shifted_lot_ids, "Lot shifted by capacity-aware planning"),
    }
    lot_exception_records: list[dict] = []
    for exception_type, (lot_ids, default_message) in lot_exception_specs.items():
        for lot_id in lot_ids:
            lot_exception_records.append(
                {
                    "record_type": "lot_exception",
                    "exception_type": exception_type,
                    "product": product,
                    "lot_id": lot_id,
                    "node": "",
                    "week": None,
                    "source": "explicit_bridge_capacity_pipeline",
                    "message": default_message,
                }
            )

    replan_candidate_records: list[dict] = []
    for raw in _as_list(getattr(pipeline_result, "replan_commands", [])):
        row = _as_record(raw)
        row.setdefault("record_type", "replan_candidate")
        row.setdefault("command_type", "capacity_replan")
        row.setdefault("product", product)
        row.setdefault("node", "")
        row.setdefault("week", None)
        row.setdefault("capacity_type", "")
        row.setdefault("lot_ids", [])
        row.setdefault("suggested_action", "review_capacity_or_rerun_backward_planning")
        row.setdefault("source", "explicit_bridge_capacity_pipeline")
        replan_candidate_records.append(row)

    health_check_records: list[dict] = []
    if missing_lot_ids:
        health_check_records.append(
            {
                "record_type": "health_check",
                "check_type": "missing_lot",
                "severity": "error",
                "count": len(missing_lot_ids),
                "details": list(missing_lot_ids),
                "source": "explicit_bridge_capacity_pipeline",
            }
        )
    if non_list_bucket_errors:
        health_check_records.append(
            {
                "record_type": "health_check",
                "check_type": "non_list_bucket_error",
                "severity": "error",
                "count": len(non_list_bucket_errors),
                "details": list(non_list_bucket_errors),
                "source": "explicit_bridge_capacity_pipeline",
            }
        )
    if non_string_lot_errors:
        health_check_records.append(
            {
                "record_type": "health_check",
                "check_type": "non_string_lot_error",
                "severity": "error",
                "count": len(non_string_lot_errors),
                "details": list(non_string_lot_errors),
                "source": "explicit_bridge_capacity_pipeline",
            }
        )

    has_error = bool(
        len(missing_lot_ids) > 0
        or any(record.get("severity") == "error" for record in health_check_records)
    )
    has_warning = bool(capacity_violation_records or lot_exception_records)

    summary = {
        "product": product,
        "capacity_usage_record_count": len(capacity_usage_records),
        "capacity_violation_record_count": len(capacity_violation_records),
        "lot_exception_record_count": len(lot_exception_records),
        "replan_candidate_record_count": len(replan_candidate_records),
        "health_check_record_count": len(health_check_records),
        "missing_lot_count": len(missing_lot_ids),
        "blocked_lot_count": len(blocked_lot_ids),
        "overflow_i_lot_count": len(overflow_i_lot_ids),
        "backlog_lot_count": len(backlog_lot_ids),
        "shifted_lot_count": len(shifted_lot_ids),
        "has_error": has_error,
        "has_warning": has_warning,
    }

    return ExplicitPipelineCapacityReport(
        product_name=product,
        capacity_usage_records=capacity_usage_records,
        capacity_violation_records=capacity_violation_records,
        lot_exception_records=lot_exception_records,
        replan_candidate_records=replan_candidate_records,
        health_check_records=health_check_records,
        summary=summary,
        message=message,
    )


def report_to_dict(report: ExplicitPipelineCapacityReport) -> dict:
    return asdict(report)


def report_records_as_rows(report: ExplicitPipelineCapacityReport) -> list[dict]:
    rows: list[dict] = []
    rows.extend(report.capacity_usage_records)
    rows.extend(report.capacity_violation_records)
    rows.extend(report.lot_exception_records)
    rows.extend(report.replan_candidate_records)
    rows.extend(report.health_check_records)
    return rows


def maybe_build_explicit_pipeline_capacity_report_from_env(env):
    pipeline_result = getattr(env, "explicit_bridge_capacity_pipeline_result", None)
    if pipeline_result is None:
        return None

    report = build_explicit_pipeline_capacity_report(pipeline_result)
    setattr(env, "explicit_bridge_capacity_pipeline_report", report)
    return report
