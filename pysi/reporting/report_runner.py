"""Run end-to-end reporting pipeline for WOM cost/reporting MVP."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pysi.cost.allocation_rule_engine import apply_allocation_rules
from pysi.cost.cost_engine import run_cost_engine
from pysi.cost.load_cost_masters import load_cost_masters
from pysi.cost.validate_cost_masters import validate_cost_masters
from pysi.reporting.business_report_builder import build_business_report
from pysi.reporting.report_exporter import export_report_bundle
from pysi.reporting.report_input_builder import build_report_input


def run_reporting_pipeline(
    planning_result: dict[str, Any] | None = None,
    env: Any = None,
    cost_master_source: dict[str, Any] | str | None = None,
    output_dir: str | Path = "outputs/reporting_mvp",
    apply_allocation: bool = True,
) -> dict[str, Any]:
    report_input = build_report_input(planning_result=planning_result, env=env)

    cost_masters = load_cost_masters(cost_master_source)
    errors = validate_cost_masters(cost_masters)
    if errors:
        raise ValueError("Invalid cost masters: " + "; ".join(errors))

    cost_result = run_cost_engine(report_input=report_input, cost_masters=cost_masters)

    allocation_breakdown: list[dict[str, Any]] = []
    final_cost_lines = cost_result["cost_lines"]

    if apply_allocation:
        allocation_result = apply_allocation_rules(
            cost_result=cost_result,
            allocation_rules=list(cost_masters.get("allocation_rules", [])),
            report_input=report_input,
        )
        final_cost_lines = allocation_result["cost_lines_after"]
        allocation_breakdown = allocation_result["allocation_breakdown"]

    report = build_business_report(
        report_input=report_input,
        cost_lines=final_cost_lines,
        allocation_breakdown=allocation_breakdown,
    )
    exported = export_report_bundle(report=report, output_dir=output_dir)

    return {
        "report": report,
        "exported": exported,
        "report_input": report_input,
        "cost_masters": cost_masters,
    }
