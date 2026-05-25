from __future__ import annotations

from tools.smoke_capacity_report_hook import main


def test_smoke_runner_main_creates_reports(tmp_path):
    out_dir = tmp_path / "smoke"
    usage_count, violation_count = main(out_dir)

    assert (out_dir / "capacity_master_smoke.csv").exists()
    assert (out_dir / "capacity_usage.csv").exists()
    assert (out_dir / "capacity_violation.csv").exists()
    assert usage_count > 0
    assert violation_count > 0
