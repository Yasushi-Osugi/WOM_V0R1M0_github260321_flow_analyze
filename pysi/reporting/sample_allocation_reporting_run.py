"""Static sample run with allocation enabled."""

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
                "sales_units": 60,
            },
            {
                "product": "SKU_A",
                "node": "factory_a",
                "week": "2026-W02",
                "qty": 50,
                "market": "us",
                "sales_units": 40,
            },
        ]
    }

    result = run_reporting_pipeline(
        planning_result=planning_result,
        output_dir="outputs/reporting_mvp/sample_allocation_reporting_run",
        apply_allocation=True,
    )

    print("[sample_allocation_reporting_run] report exported:")
    for key, path in sorted(result["exported"].items()):
        print(f"  - {key}: {path}")

    print(
        "[sample_allocation_reporting_run] allocation rows:",
        len(result["report"].get("allocation_breakdown", [])),
    )


if __name__ == "__main__":
    main()
