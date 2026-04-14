"""Environment-connected sample reporting runner (minimal stub)."""

from __future__ import annotations

from typing import Any

from pysi.reporting.report_runner import run_reporting_pipeline


def get_env() -> Any:
    """Return planning env if available.

    Stub by design: replace with concrete builder when env bootstrap is standardized.
    """
    return None


def main() -> None:
    env = get_env()
    if env is None:
        print("[sample_env_reporting_run] get_env() is stub; using empty env input.")

    result = run_reporting_pipeline(
        env=env,
        output_dir="outputs/reporting_mvp/sample_env_reporting_run",
        apply_allocation=False,
    )

    print("[sample_env_reporting_run] report exported:")
    for key, path in sorted(result["exported"].items()):
        print(f"  - {key}: {path}")


if __name__ == "__main__":
    main()
