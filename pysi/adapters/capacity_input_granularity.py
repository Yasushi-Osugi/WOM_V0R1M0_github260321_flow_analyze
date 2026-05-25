"""Adapter functions to normalize monthly/weekly capacity rows into weekly canonical rows."""

from __future__ import annotations

from dataclasses import dataclass

from pysi.adapters.calendar_445 import build_445_month_to_weeks_map


@dataclass
class WeeklyCapacityRow:
    scenario_id: str
    product_id: str
    capacity_owner_type: str
    capacity_owner_id: str
    week: str
    capacity_type: str
    capacity_qty: float
    cap_mode: str = "hard"
    unit: str = "LOT"
    source_granularity: str = "weekly"
    source_id: str = ""
    comment: str = ""


@dataclass
class MonthlyCapacityInputRow:
    scenario_id: str
    product_id: str
    capacity_owner_type: str
    capacity_owner_id: str
    month: str
    capacity_type: str
    capacity_qty: float
    cap_mode: str = "hard"
    unit: str = "LOT"
    source_id: str = ""
    comment: str = ""


@dataclass
class WeeklyCapacityInputRow:
    scenario_id: str
    product_id: str
    capacity_owner_type: str
    capacity_owner_id: str
    week: str
    capacity_type: str
    capacity_qty: float
    cap_mode: str = "hard"
    unit: str = "LOT"
    source_id: str = ""
    comment: str = ""


def _build_four_week_month_map(year: str | int) -> dict[str, list[str]]:
    year_key = str(year)
    mapping: dict[str, list[str]] = {}
    for month_index in range(1, 13):
        month_key = f"{year_key}-M{month_index:02d}"
        week_start = (month_index - 1) * 4 + 1
        mapping[month_key] = [f"{year_key}-W{week_start + i:02d}" for i in range(4)]
    return mapping


def monthly_capacity_to_weekly_rows(
    monthly_rows: list[MonthlyCapacityInputRow],
    *,
    calendar_mode: str = "445",
    distribution_rule: str = "even",
) -> list[WeeklyCapacityRow]:
    if calendar_mode not in {"445", "four_week_month"}:
        raise ValueError(f"Unsupported calendar_mode: {calendar_mode}")
    if distribution_rule != "even":
        raise ValueError(f"Unsupported distribution_rule: {distribution_rule}")

    weekly_rows: list[WeeklyCapacityRow] = []
    month_cache: dict[str, list[str]] = {}

    for row in monthly_rows:
        if row.month not in month_cache:
            year = row.month.split("-M", maxsplit=1)[0]
            if calendar_mode == "445":
                month_cache.update(build_445_month_to_weeks_map(year))
            else:
                month_cache.update(_build_four_week_month_map(year))

        weeks = month_cache.get(row.month)
        if not weeks:
            raise ValueError(f"Unknown planning month for calendar_mode={calendar_mode}: {row.month}")

        weekly_capacity = row.capacity_qty / len(weeks)
        for week in weeks:
            weekly_rows.append(
                WeeklyCapacityRow(
                    scenario_id=row.scenario_id,
                    product_id=row.product_id,
                    capacity_owner_type=row.capacity_owner_type,
                    capacity_owner_id=row.capacity_owner_id,
                    week=week,
                    capacity_type=row.capacity_type,
                    capacity_qty=weekly_capacity,
                    cap_mode=row.cap_mode,
                    unit=row.unit,
                    source_granularity="monthly",
                    source_id=row.source_id,
                    comment=row.comment,
                )
            )

    return weekly_rows


def weekly_capacity_to_weekly_rows(
    weekly_rows: list[WeeklyCapacityInputRow],
    *,
    source_granularity: str = "weekly",
) -> list[WeeklyCapacityRow]:
    normalized_rows: list[WeeklyCapacityRow] = []
    for row in weekly_rows:
        normalized_rows.append(
            WeeklyCapacityRow(
                scenario_id=row.scenario_id,
                product_id=row.product_id,
                capacity_owner_type=row.capacity_owner_type,
                capacity_owner_id=row.capacity_owner_id,
                week=row.week,
                capacity_type=row.capacity_type,
                capacity_qty=row.capacity_qty,
                cap_mode=row.cap_mode,
                unit=row.unit,
                source_granularity=source_granularity,
                source_id=row.source_id,
                comment=row.comment,
            )
        )
    return normalized_rows


def normalize_capacity_input_to_weekly_rows(
    *,
    input_mode: str,
    monthly_rows: list[MonthlyCapacityInputRow] | None = None,
    weekly_rows: list[WeeklyCapacityInputRow] | None = None,
    calendar_mode: str = "445",
    distribution_rule: str = "even",
) -> list[WeeklyCapacityRow]:
    if input_mode == "monthly_capacity":
        return monthly_capacity_to_weekly_rows(
            monthly_rows or [],
            calendar_mode=calendar_mode,
            distribution_rule=distribution_rule,
        )
    if input_mode == "weekly_capacity":
        return weekly_capacity_to_weekly_rows(weekly_rows or [], source_granularity="weekly")
    if input_mode == "case_weekly_capacity":
        return weekly_capacity_to_weekly_rows(weekly_rows or [], source_granularity="case_weekly")
    raise ValueError(f"Unsupported input_mode: {input_mode}")


def normalize_capacity_owner_name(owner_id: str) -> str:
    if owner_id.startswith("DAD"):
        return "MOM" + owner_id[3:]
    return owner_id


def weekly_capacity_rows_to_weekly_capability(
    rows: list[WeeklyCapacityRow],
    *,
    weeks_count: int,
    normalize_owner_name: bool = True,
    capacity_type_filter: str = "P",
) -> dict[str, dict[str, list[int]]]:
    weekly_capability: dict[str, dict[str, list[int]]] = {}

    for row in rows:
        if capacity_type_filter and row.capacity_type != capacity_type_filter:
            continue

        owner_id = normalize_capacity_owner_name(row.capacity_owner_id) if normalize_owner_name else row.capacity_owner_id
        week_idx = int(row.week.split("-W", maxsplit=1)[1]) - 1
        if week_idx < 0 or week_idx >= weeks_count:
            continue

        weekly_capability.setdefault(row.product_id, {})
        weekly_capability[row.product_id].setdefault(owner_id, [0] * weeks_count)
        weekly_capability[row.product_id][owner_id][week_idx] += int(row.capacity_qty)

    return weekly_capability
