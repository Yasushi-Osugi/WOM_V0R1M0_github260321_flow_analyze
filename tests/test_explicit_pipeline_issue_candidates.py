from types import SimpleNamespace

from pysi.reporting.explicit_pipeline_capacity_report import ExplicitPipelineCapacityReport
from pysi.reporting.explicit_pipeline_issue_candidates import (
    build_explicit_pipeline_issue_candidates,
    issue_candidates_as_rows,
    issue_candidates_to_dict,
    maybe_build_explicit_pipeline_issue_candidates_from_env,
)


def _build_synthetic_report() -> ExplicitPipelineCapacityReport:
    return ExplicitPipelineCapacityReport(
        product_name="RICE",
        capacity_violation_records=[
            {
                "record_type": "capacity_violation",
                "product": "RICE",
                "node": "MOM_ASIA",
                "week": 10,
                "capacity_type": "P",
                "severity": "warning",
                "lot_ids": ["LOT_CAP_P"],
            }
        ],
        lot_exception_records=[
            {"record_type": "lot_exception", "exception_type": "blocked", "product": "RICE", "lot_id": "LOT_BLOCKED"},
            {"record_type": "lot_exception", "exception_type": "overflow_i", "product": "RICE", "lot_id": "LOT_OVERFLOW"},
            {"record_type": "lot_exception", "exception_type": "backlog", "product": "RICE", "lot_id": "LOT_BACKLOG"},
            {"record_type": "lot_exception", "exception_type": "shifted", "product": "RICE", "lot_id": "LOT_SHIFTED"},
            {"record_type": "lot_exception", "exception_type": "missing", "product": "RICE", "lot_id": "LOT_MISSING"},
        ],
        health_check_records=[
            {
                "record_type": "health_check",
                "check_type": "non_string_lot_error",
                "severity": "error",
                "details": ["bucket[3]=123"],
            }
        ],
        replan_candidate_records=[
            {
                "record_type": "replan_candidate",
                "command_type": "capacity_replan",
                "product": "RICE",
                "node": "MOM_ASIA",
                "week": 10,
                "capacity_type": "P",
                "lot_ids": ["LOT_REPLAN"],
            }
        ],
    )


def test_build_explicit_pipeline_issue_candidates_with_all_record_types():
    bundle = build_explicit_pipeline_issue_candidates(_build_synthetic_report())

    assert len(bundle.planning_issue_candidates) == 6
    assert len(bundle.management_issue_candidates) == 6
    assert len(bundle.health_issue_candidates) == 2
    assert len(bundle.replan_command_candidates) == 1

    assert bundle.summary["planning_issue_candidate_count"] == 6
    assert bundle.summary["management_issue_candidate_count"] == 6
    assert bundle.summary["health_issue_candidate_count"] == 2
    assert bundle.summary["replan_command_candidate_count"] == 1
    assert bundle.summary["error_count"] == 5
    assert bundle.summary["warning_count"] == 8
    assert bundle.summary["info_count"] == 1
    assert bundle.summary["has_error"] is True
    assert bundle.summary["has_warning"] is True


def test_build_explicit_pipeline_issue_candidates_empty_report_safety():
    bundle = build_explicit_pipeline_issue_candidates(ExplicitPipelineCapacityReport())

    assert bundle.planning_issue_candidates == []
    assert bundle.management_issue_candidates == []
    assert bundle.health_issue_candidates == []
    assert bundle.replan_command_candidates == []
    assert bundle.summary["planning_issue_candidate_count"] == 0
    assert bundle.summary["management_issue_candidate_count"] == 0
    assert bundle.summary["health_issue_candidate_count"] == 0
    assert bundle.summary["replan_command_candidate_count"] == 0
    assert bundle.summary["error_count"] == 0
    assert bundle.summary["warning_count"] == 0
    assert bundle.summary["info_count"] == 0
    assert bundle.summary["has_error"] is False
    assert bundle.summary["has_warning"] is False


def test_lot_id_preservation_in_candidates():
    bundle = build_explicit_pipeline_issue_candidates(_build_synthetic_report())

    blocked = next(c for c in bundle.planning_issue_candidates if c["issue_type"] == "blocked_lot")
    overflow = next(c for c in bundle.planning_issue_candidates if c["issue_type"] == "overflow_inventory")
    replan = bundle.replan_command_candidates[0]

    assert "LOT_BLOCKED" in blocked["lot_ids"]
    assert "LOT_OVERFLOW" in overflow["lot_ids"]
    assert "LOT_REPLAN" in replan["lot_ids"]


def test_replan_candidates_are_candidate_only():
    bundle = build_explicit_pipeline_issue_candidates(_build_synthetic_report())
    assert all(row["status"] == "candidate_only" for row in bundle.replan_command_candidates)


def test_maybe_build_explicit_pipeline_issue_candidates_from_env_noop():
    env = SimpleNamespace()
    assert maybe_build_explicit_pipeline_issue_candidates_from_env(env) is None


def test_maybe_build_explicit_pipeline_issue_candidates_from_env_attaches_bundle():
    env = SimpleNamespace(explicit_bridge_capacity_pipeline_report=_build_synthetic_report())
    bundle = maybe_build_explicit_pipeline_issue_candidates_from_env(env)

    assert bundle is env.explicit_bridge_capacity_issue_candidates


def test_issue_candidate_serialization_helpers():
    bundle = build_explicit_pipeline_issue_candidates(_build_synthetic_report())

    bundle_dict = issue_candidates_to_dict(bundle)
    rows = issue_candidates_as_rows(bundle)

    assert isinstance(bundle_dict, dict)
    assert isinstance(rows, list)
    assert all(isinstance(row, dict) for row in rows)
