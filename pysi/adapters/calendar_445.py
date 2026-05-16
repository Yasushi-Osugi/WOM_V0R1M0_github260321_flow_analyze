"""4-4-5 planning calendar helpers for WOM weekly normalization."""

from __future__ import annotations


_445_WEEKS_PER_MONTH: tuple[int, ...] = (4, 4, 5) * 4


def _normalize_year(year: str | int) -> str:
    return str(year)


def build_445_month_to_weeks_map(year: str | int) -> dict[str, list[str]]:
    """Build mapping from planning month key to planning week keys for a 4-4-5 year."""
    year_key = _normalize_year(year)
    mapping: dict[str, list[str]] = {}

    week_num = 1
    for month_index, month_weeks in enumerate(_445_WEEKS_PER_MONTH, start=1):
        month_key = f"{year_key}-M{month_index:02d}"
        weeks: list[str] = []
        for _ in range(month_weeks):
            weeks.append(f"{year_key}-W{week_num:02d}")
            week_num += 1
        mapping[month_key] = weeks

    return mapping


def build_445_week_to_month_map(year: str | int) -> dict[str, str]:
    """Build inverse mapping from planning week key to planning month key for a 4-4-5 year."""
    month_to_weeks = build_445_month_to_weeks_map(year)
    mapping: dict[str, str] = {}

    for month_key, weeks in month_to_weeks.items():
        for week in weeks:
            mapping[week] = month_key

    return mapping
