import csv
import json
from types import SimpleNamespace

from pysi.reporting.explicit_pipeline_issue_candidate_exporter import (
    export_explicit_pipeline_issue_candidates,
    maybe_export_explicit_pipeline_issue_candidates_from_env,
)
from pysi.reporting.explicit_pipeline_issue_candidates import ExplicitPipelineIssueCandidateBundle


def _synthetic_bundle() -> ExplicitPipelineIssueCandidateBundle:
    return ExplicitPipelineIssueCandidateBundle(
        product_name="RICE",
        planning_issue_candidates=[
            {
                "candidate_type": "planning_issue",
                "issue_type": "capacity_violation",
                "severity": "warning",
                "product": "RICE",
                "node": "MOM_ASIA",
                "week": 11,
                "capacity_type": "P",
                "lot_ids": ["LOT_001"],
                "evidence_record_type": "capacity_violation",
                "source": "explicit_pipeline_capacity_report",
                "message": "P capacity violation at MOM_ASIA week 11",
                "suggested_action": "review_capacity_or_rerun_backward_planning",
            }
        ],
        management_issue_candidates=[
            {
                "candidate_type": "management_issue",
                "issue_type": "capacity_bottleneck",
                "severity": "warning",
                "product": "RICE",
                "node": "MOM_ASIA",
                "week": 11,
                "capacity_type": "P",
                "lot_ids": ["LOT_001"],
                "business_theme": "supply_capacity_constraint",
                "evidence_record_type": "capacity_violation",
                "source": "explicit_pipeline_capacity_report",
                "message": "Capacity bottleneck candidate detected",
                "suggested_decision": "review capacity",
            }
        ],
        replan_command_candidates=[
            {
                "candidate_type": "replan_command_candidate",
                "command_type": "capacity_replan",
                "status": "candidate_only",
                "product": "RICE",
                "node": "MOM_ASIA",
                "week": 12,
                "capacity_type": "P",
                "lot_ids": ["LOT_002"],
                "source": "explicit_pipeline_capacity_report",
                "message": "Candidate replan command generated",
                "suggested_action": "review_capacity_or_rerun_backward_planning",
            }
        ],
        health_issue_candidates=[
            {
                "candidate_type": "health_issue",
                "issue_type": "missing_lot",
                "severity": "error",
                "product": "RICE",
                "details": ["LOT_003"],
                "evidence_record_type": "lot_exception",
                "source": "explicit_pipeline_capacity_report",
                "message": "Structural PSI health issue detected",
            }
        ],
        summary={
            "product": "RICE",
            "planning_issue_candidate_count": 1,
            "management_issue_candidate_count": 1,
            "replan_command_candidate_count": 1,
            "health_issue_candidate_count": 1,
            "has_error": True,
            "has_warning": True,
        },
    )


def test_export_synthetic_candidate_bundle(tmp_path):
    bundle = _synthetic_bundle()

    result = export_explicit_pipeline_issue_candidates(bundle, output_dir=tmp_path)

    expected = {
        "planning_issues.csv",
        "management_issues.csv",
        "replan_command_candidates.csv",
        "health_issues.csv",
        "summary.json",
        "all_issue_candidates.csv",
    }
    assert expected.issubset({path.name for path in result.files.values()})
    for filename in expected:
        assert (tmp_path / filename).exists()

    assert result.output_dir == tmp_path
    assert result.summary_path == tmp_path / "summary.json"
    assert result.record_counts == {
        "planning_issues": 1,
        "management_issues": 1,
        "replan_command_candidates": 1,
        "health_issues": 1,
        "all_issue_candidates": 4,
    }


def test_verify_summary_json(tmp_path):
    bundle = _synthetic_bundle()
    export_explicit_pipeline_issue_candidates(bundle, output_dir=tmp_path)

    payload = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert payload["product"] == "RICE"
    assert payload["planning_issue_candidate_count"] == 1
    assert payload["management_issue_candidate_count"] == 1
    assert payload["has_error"] is True
    assert payload["has_warning"] is True


def test_verify_csv_content_and_json_encoding(tmp_path):
    bundle = _synthetic_bundle()
    export_explicit_pipeline_issue_candidates(bundle, output_dir=tmp_path)

    with (tmp_path / "planning_issues.csv").open(newline="", encoding="utf-8") as f:
        planning_rows = list(csv.DictReader(f))
    assert planning_rows
    assert planning_rows[0]["product"] == "RICE"
    assert planning_rows[0]["lot_ids"] == '["LOT_001"]'

    with (tmp_path / "management_issues.csv").open(newline="", encoding="utf-8") as f:
        management_rows = list(csv.DictReader(f))
    assert management_rows
    assert management_rows[0]["issue_type"] == "capacity_bottleneck"

    with (tmp_path / "replan_command_candidates.csv").open(newline="", encoding="utf-8") as f:
        replan_rows = list(csv.DictReader(f))
    assert replan_rows
    assert replan_rows[0]["status"] == "candidate_only"

    with (tmp_path / "all_issue_candidates.csv").open(newline="", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))
    assert all_rows
    assert any(row.get("candidate_type") == "management_issue" for row in all_rows)


def test_empty_bundle_export_writes_headers_when_enabled(tmp_path):
    bundle = ExplicitPipelineIssueCandidateBundle(summary={"product": "RICE", "has_error": False, "has_warning": False})
    result = export_explicit_pipeline_issue_candidates(bundle, output_dir=tmp_path, write_empty_files=True)

    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "planning_issues.csv").exists()
    assert (tmp_path / "all_issue_candidates.csv").exists()

    with (tmp_path / "planning_issues.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 1
    assert result.record_counts["all_issue_candidates"] == 0


def test_empty_bundle_export_skips_empty_csvs_when_disabled(tmp_path):
    bundle = ExplicitPipelineIssueCandidateBundle(summary={"product": "RICE"})
    export_explicit_pipeline_issue_candidates(bundle, output_dir=tmp_path, write_empty_files=False)

    assert (tmp_path / "summary.json").exists()
    assert not (tmp_path / "planning_issues.csv").exists()
    assert not (tmp_path / "management_issues.csv").exists()
    assert not (tmp_path / "all_issue_candidates.csv").exists()


def test_env_helper_noop_without_bundle(tmp_path):
    env = SimpleNamespace()
    outdir = tmp_path / "exports"
    assert maybe_export_explicit_pipeline_issue_candidates_from_env(env, output_dir=outdir) is None
    assert not outdir.exists()


def test_env_helper_attaches_export_result(tmp_path):
    env = SimpleNamespace(explicit_bridge_capacity_issue_candidates=_synthetic_bundle())

    result = maybe_export_explicit_pipeline_issue_candidates_from_env(env, output_dir=tmp_path)

    assert result is env.explicit_bridge_capacity_issue_candidate_export_result
    assert (tmp_path / "summary.json").exists()


def test_export_bundle_json_when_enabled(tmp_path):
    bundle = _synthetic_bundle()
    export_explicit_pipeline_issue_candidates(bundle, output_dir=tmp_path, write_bundle_json=True)
    assert (tmp_path / "issue_candidate_bundle.json").exists()
