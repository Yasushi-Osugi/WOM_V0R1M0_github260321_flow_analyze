import csv
import json
from types import SimpleNamespace

from pysi.reporting.explicit_pipeline_capacity_report import ExplicitPipelineCapacityReport
from pysi.reporting.explicit_pipeline_capacity_report_exporter import (
    export_explicit_pipeline_capacity_report,
    maybe_export_explicit_pipeline_capacity_report_from_env,
)


def _synthetic_report() -> ExplicitPipelineCapacityReport:
    return ExplicitPipelineCapacityReport(
        product_name="RICE",
        capacity_usage_records=[
            {
                "record_type": "capacity_usage",
                "product": "RICE",
                "node": "MOM_ASIA",
                "week": 10,
                "capacity_type": "P",
                "capacity": 100,
                "used": 90,
                "remaining": 10,
                "utilization_ratio": 0.9,
                "lot_ids": ["LOT_001"],
                "message": "Usage near full",
            }
        ],
        capacity_violation_records=[
            {
                "record_type": "capacity_violation",
                "product": "RICE",
                "node": "MOM_ASIA",
                "week": 11,
                "capacity_type": "P",
                "severity": "warning",
                "lot_ids": ["LOT_002"],
                "requested": 120,
                "capacity": 100,
                "overflow": 20,
            }
        ],
        lot_exception_records=[
            {
                "record_type": "lot_exception",
                "exception_type": "missing",
                "product": "RICE",
                "lot_id": "LOT_003",
                "node": "MOM_ASIA",
                "week": 12,
            }
        ],
        replan_candidate_records=[
            {
                "record_type": "replan_candidate",
                "command_type": "capacity_replan",
                "product": "RICE",
                "node": "MOM_ASIA",
                "week": 13,
                "capacity_type": "P",
                "lot_ids": ["LOT_004"],
                "suggested_action": "rerun",
            }
        ],
        health_check_records=[
            {
                "record_type": "health_check",
                "check_type": "missing_lot",
                "severity": "error",
                "count": 1,
                "details": {"lot": "LOT_003"},
            }
        ],
        summary={
            "product": "RICE",
            "capacity_usage_record_count": 1,
            "capacity_violation_record_count": 1,
            "lot_exception_record_count": 1,
            "replan_candidate_record_count": 1,
            "health_check_record_count": 1,
            "has_error": True,
            "has_warning": True,
        },
    )


def test_export_synthetic_report(tmp_path):
    report = _synthetic_report()

    result = export_explicit_pipeline_capacity_report(report, output_dir=tmp_path)

    expected = {
        "capacity_usage.csv",
        "capacity_violations.csv",
        "lot_exceptions.csv",
        "replan_candidates.csv",
        "health_checks.csv",
        "summary.json",
        "all_records.csv",
    }
    assert expected.issubset({path.name for path in result.files.values()})
    for filename in expected:
        assert (tmp_path / filename).exists()

    assert result.output_dir == tmp_path
    assert result.summary_path == tmp_path / "summary.json"
    assert result.record_counts == {
        "capacity_usage": 1,
        "capacity_violations": 1,
        "lot_exceptions": 1,
        "replan_candidates": 1,
        "health_checks": 1,
        "all_records": 5,
    }


def test_verify_summary_json(tmp_path):
    report = _synthetic_report()
    export_explicit_pipeline_capacity_report(report, output_dir=tmp_path)

    payload = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert payload["product"] == "RICE"
    assert payload["capacity_usage_record_count"] == 1
    assert payload["capacity_violation_record_count"] == 1
    assert payload["has_error"] is True
    assert payload["has_warning"] is True


def test_verify_csv_content_and_json_encoding(tmp_path):
    report = _synthetic_report()
    export_explicit_pipeline_capacity_report(report, output_dir=tmp_path)

    with (tmp_path / "capacity_usage.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows
    assert rows[0]["product"] == "RICE"
    assert rows[0]["lot_ids"] == '["LOT_001"]'

    with (tmp_path / "lot_exceptions.csv").open(newline="", encoding="utf-8") as f:
        lot_rows = list(csv.DictReader(f))
    assert lot_rows
    assert lot_rows[0]["lot_id"] == "LOT_003"

    with (tmp_path / "all_records.csv").open(newline="", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))
    assert all_rows
    assert any(row.get("record_type") == "health_check" for row in all_rows)


def test_empty_report_export_writes_headers_when_enabled(tmp_path):
    report = ExplicitPipelineCapacityReport(summary={"product": "RICE", "has_error": False, "has_warning": False})
    result = export_explicit_pipeline_capacity_report(
        report,
        output_dir=tmp_path,
        write_empty_files=True,
    )

    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "capacity_usage.csv").exists()
    assert (tmp_path / "all_records.csv").exists()

    with (tmp_path / "capacity_usage.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 1
    assert result.record_counts["all_records"] == 0


def test_empty_report_export_skips_empty_csvs_when_disabled(tmp_path):
    report = ExplicitPipelineCapacityReport(summary={"product": "RICE"})
    export_explicit_pipeline_capacity_report(
        report,
        output_dir=tmp_path,
        write_empty_files=False,
        write_all_records=True,
    )

    assert (tmp_path / "summary.json").exists()
    assert not (tmp_path / "capacity_usage.csv").exists()
    assert not (tmp_path / "capacity_violations.csv").exists()
    assert not (tmp_path / "all_records.csv").exists()


def test_env_helper_noop_without_report(tmp_path):
    env = SimpleNamespace()
    outdir = tmp_path / "exports"
    assert maybe_export_explicit_pipeline_capacity_report_from_env(env, output_dir=outdir) is None
    assert not outdir.exists()


def test_env_helper_attaches_export_result(tmp_path):
    env = SimpleNamespace(explicit_bridge_capacity_pipeline_report=_synthetic_report())

    result = maybe_export_explicit_pipeline_capacity_report_from_env(env, output_dir=tmp_path)

    assert result is env.explicit_bridge_capacity_pipeline_report_export_result
    assert (tmp_path / "summary.json").exists()


def test_export_report_json_when_enabled(tmp_path):
    report = _synthetic_report()
    export_explicit_pipeline_capacity_report(report, output_dir=tmp_path, write_report_json=True)
    assert (tmp_path / "report.json").exists()
