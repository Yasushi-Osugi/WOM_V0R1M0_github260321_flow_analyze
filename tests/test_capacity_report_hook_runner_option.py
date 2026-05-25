from __future__ import annotations

from tools.smoke_capacity_report_hook import (
    _write_capacity_master_smoke_csv,
    run_smoke_runner_with_optional_capacity_report,
)


def test_capacity_report_runner_option_disabled_by_default(tmp_path):
    out_dir = tmp_path / "runner"
    usage_count, violation_count = run_smoke_runner_with_optional_capacity_report(
        output_dir=out_dir
    )

    assert usage_count == 0
    assert violation_count == 0
    assert not (out_dir / "capacity_usage.csv").exists()
    assert not (out_dir / "capacity_violation.csv").exists()


def test_capacity_report_runner_option_enabled_outputs_files(tmp_path):
    out_dir = tmp_path / "runner"
    master_path = tmp_path / "capacity_master.csv"
    _write_capacity_master_smoke_csv(master_path)

    usage_count, violation_count = run_smoke_runner_with_optional_capacity_report(
        output_dir=out_dir,
        enable_capacity_report=True,
        capacity_master_path=master_path,
    )

    assert (out_dir / "capacity_usage.csv").exists()
    assert (out_dir / "capacity_violation.csv").exists()
    assert usage_count > 0
    assert violation_count > 0


def test_capacity_report_runner_option_missing_master_non_strict(tmp_path):
    out_dir = tmp_path / "runner"
    usage_count, violation_count = run_smoke_runner_with_optional_capacity_report(
        output_dir=out_dir,
        enable_capacity_report=True,
        capacity_master_path=tmp_path / "missing_capacity_master.csv",
    )

    assert usage_count == 0
    assert violation_count == 0
