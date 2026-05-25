"""Adapter functions to normalize monthly/weekly raw plan rows into weekly canonical rows."""

from __future__ import annotations

from pysi.adapters.calendar_445 import build_445_month_to_weeks_map
from pysi.adapters.weekly_plan_table import (
    ALLOWED_PLAN_TYPES,
    ALLOWED_SOURCE_GRANULARITIES,
    MonthlyPlanInputRow,
    WeeklyPlanInputRow,
    WeeklyPlanRow,
)


def _validate_plan_type(plan_type: str) -> None:
    if plan_type not in ALLOWED_PLAN_TYPES:
        raise ValueError(f"Unsupported plan_type: {plan_type}")


def _validate_source_granularity(source_granularity: str) -> None:
    if source_granularity not in ALLOWED_SOURCE_GRANULARITIES:
        raise ValueError(f"Unsupported source_granularity: {source_granularity}")


def monthly_plan_to_weekly_rows(
    monthly_rows: list[MonthlyPlanInputRow],
    *,
    calendar_mode: str = "445",
    distribution_rule: str = "even",
) -> list[WeeklyPlanRow]:
    if calendar_mode != "445":
        raise ValueError(f"Unsupported calendar_mode: {calendar_mode}")
    if distribution_rule != "even":
        raise ValueError(f"Unsupported distribution_rule: {distribution_rule}")

    weekly_rows: list[WeeklyPlanRow] = []
    month_cache: dict[str, list[str]] = {}

    for row in monthly_rows:
        _validate_plan_type(row.plan_type)
        if row.month not in month_cache:
            year = row.month.split("-M", maxsplit=1)[0]
            month_cache.update(build_445_month_to_weeks_map(year))

        weeks = month_cache.get(row.month)
        if not weeks:
            raise ValueError(f"Unknown planning month for calendar_mode=445: {row.month}")

        weekly_quantity = row.quantity / len(weeks)
        for week in weeks:
            weekly_rows.append(
                WeeklyPlanRow(
                    scenario_id=row.scenario_id,
                    product_id=row.product_id,
                    node_id=row.node_id,
                    week=week,
                    plan_type=row.plan_type,
                    quantity=weekly_quantity,
                    source_granularity="monthly",
                    source_id=row.source_id,
                    comment=row.comment,
                )
            )

    return weekly_rows


def weekly_plan_to_weekly_rows(
    weekly_rows: list[WeeklyPlanInputRow],
    *,
    source_granularity: str = "weekly",
) -> list[WeeklyPlanRow]:
    _validate_source_granularity(source_granularity)

    normalized_rows: list[WeeklyPlanRow] = []
    for row in weekly_rows:
        _validate_plan_type(row.plan_type)
        normalized_rows.append(
            WeeklyPlanRow(
                scenario_id=row.scenario_id,
                product_id=row.product_id,
                node_id=row.node_id,
                week=row.week,
                plan_type=row.plan_type,
                quantity=row.quantity,
                source_granularity=source_granularity,
                source_id=row.source_id,
                comment=row.comment,
            )
        )
    return normalized_rows


def case_weekly_plan_to_weekly_rows(
    rows: list[WeeklyPlanInputRow],
    *,
    source_id: str,
) -> list[WeeklyPlanRow]:
    normalized = weekly_plan_to_weekly_rows(rows, source_granularity="case_weekly")
    if source_id:
        for row in normalized:
            if not row.source_id:
                row.source_id = source_id
    return normalized


def normalize_plan_input_to_weekly_rows(
    *,
    input_mode: str,
    monthly_rows: list[MonthlyPlanInputRow] | None = None,
    weekly_rows: list[WeeklyPlanInputRow] | None = None,
    calendar_mode: str = "445",
    distribution_rule: str = "even",
    source_id: str = "",
) -> list[WeeklyPlanRow]:
    if input_mode == "monthly_sp":
        return monthly_plan_to_weekly_rows(
            monthly_rows or [],
            calendar_mode=calendar_mode,
            distribution_rule=distribution_rule,
        )
    if input_mode == "weekly_sp":
        return weekly_plan_to_weekly_rows(weekly_rows or [], source_granularity="weekly")
    if input_mode == "case_weekly":
        return case_weekly_plan_to_weekly_rows(weekly_rows or [], source_id=source_id)

    raise ValueError(f"Unsupported input_mode: {input_mode}")
