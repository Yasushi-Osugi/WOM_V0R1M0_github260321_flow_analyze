from types import SimpleNamespace

from pysi.plan.explicit_bridge_capacity_pipeline import ExplicitBridgeCapacityPipelineResult
from pysi.reporting.explicit_pipeline_capacity_report import (
    build_explicit_pipeline_capacity_report,
    maybe_build_explicit_pipeline_capacity_report_from_env,
    report_records_as_rows,
    report_to_dict,
)


def test_build_explicit_pipeline_capacity_report_with_synthetic_result():
    result = ExplicitBridgeCapacityPipelineResult(
        product_name="RICE",
        blocked_lot_ids=["LOT_BLOCKED"],
        overflow_i_lot_ids=["LOT_OVERFLOW"],
        missing_lot_ids=["LOT_MISSING"],
        backlog_lot_ids=["LOT_BACKLOG"],
        shifted_lot_ids=["LOT_SHIFTED"],
        capacity_usage=[
            {
                "node": "MOM_ASIA",
                "week": 10,
                "capacity_type": "P",
                "capacity": 2,
                "used": 2,
                "remaining": 0,
                "utilization_ratio": 1.0,
            }
        ],
        capacity_violations=[
            {
                "node": "MOM_ASIA",
                "week": 10,
                "capacity_type": "P",
                "capacity": 1,
                "requested": 2,
                "overflow": 1,
                "lot_ids": ["LOT_BLOCKED"],
                "source": "weekly_forward_push_with_capacity",
            }
        ],
        replan_commands=[
            {
                "node": "MOM_ASIA",
                "week": 10,
                "capacity_type": "P",
                "lot_ids": ["LOT_BLOCKED"],
            }
        ],
    )

    report = build_explicit_pipeline_capacity_report(result)

    assert report.summary["capacity_usage_record_count"] == 1
    assert report.summary["capacity_violation_record_count"] == 1
    assert report.summary["lot_exception_record_count"] == 5
    assert report.summary["replan_candidate_record_count"] == 1
    assert report.summary["health_check_record_count"] == 1

    exception_types = {record["exception_type"] for record in report.lot_exception_records}
    assert exception_types == {"missing", "blocked", "overflow_i", "backlog", "shifted"}

    usage = report.capacity_usage_records[0]
    assert usage["record_type"] == "capacity_usage"
    assert usage["product"] == "RICE"
    assert usage["node"] == "MOM_ASIA"

    violation = report.capacity_violation_records[0]
    assert violation["record_type"] == "capacity_violation"
    assert violation["severity"] == "warning"
    assert violation["source"] == "weekly_forward_push_with_capacity"

    replan = report.replan_candidate_records[0]
    assert replan["record_type"] == "replan_candidate"
    assert replan["suggested_action"] == "review_capacity_or_rerun_backward_planning"

    checks = {record["check_type"] for record in report.health_check_records}
    assert "missing_lot" in checks

    assert report.summary["has_error"] is True
    assert report.summary["has_warning"] is True


def test_build_explicit_pipeline_capacity_report_empty_result_safety():
    result = ExplicitBridgeCapacityPipelineResult()
    report = build_explicit_pipeline_capacity_report(result)

    assert report.capacity_usage_records == []
    assert report.capacity_violation_records == []
    assert report.lot_exception_records == []
    assert report.replan_candidate_records == []
    assert report.health_check_records == []

    assert report.summary["capacity_usage_record_count"] == 0
    assert report.summary["capacity_violation_record_count"] == 0
    assert report.summary["lot_exception_record_count"] == 0
    assert report.summary["replan_candidate_record_count"] == 0
    assert report.summary["health_check_record_count"] == 0
    assert report.summary["has_error"] is False
    assert report.summary["has_warning"] is False


def test_maybe_build_explicit_pipeline_capacity_report_from_env_noop():
    env = SimpleNamespace()
    assert maybe_build_explicit_pipeline_capacity_report_from_env(env) is None


def test_maybe_build_explicit_pipeline_capacity_report_from_env_attaches_report():
    env = SimpleNamespace(
        explicit_bridge_capacity_pipeline_result=ExplicitBridgeCapacityPipelineResult(product_name="RICE")
    )
    report = maybe_build_explicit_pipeline_capacity_report_from_env(env)

    assert report is env.explicit_bridge_capacity_pipeline_report


def test_serialization_helpers():
    result = ExplicitBridgeCapacityPipelineResult(
        product_name="RICE",
        missing_lot_ids=["LOT_MISSING"],
    )
    report = build_explicit_pipeline_capacity_report(result)

    report_dict = report_to_dict(report)
    rows = report_records_as_rows(report)

    assert isinstance(report_dict, dict)
    assert isinstance(rows, list)
    assert all(isinstance(row, dict) for row in rows)
