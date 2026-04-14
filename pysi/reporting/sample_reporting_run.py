"""Static sample run for reporting MVP."""

from __future__ import annotations

from pysi.reporting.report_runner import run_reporting_pipeline


def main() -> None:
    planning_result = {
        "records": [
            {
                "product": "SKU_A",
                "node": "factory_a",
                "from_node": "factory_a",
                "to_node": "dc_japan",
                "week": "2026-W01",
                "qty": 100,
                "market": "jp",
                "sales_units": 80,
            },
            {
                "product": "SKU_B",
                "node": "dc_japan",
                "week": "2026-W02",
                "qty": 70,
                "market": "jp",
                "sales_units": 70,
            },
        ]
    }

    result = run_reporting_pipeline(
        planning_result=planning_result,
        output_dir="outputs/reporting_mvp/sample_reporting_run",
        apply_allocation=False,
    )

    print("[sample_reporting_run] report exported:")
    for key, path in sorted(result["exported"].items()):
        print(f"  - {key}: {path}")


if __name__ == "__main__":
    main()
