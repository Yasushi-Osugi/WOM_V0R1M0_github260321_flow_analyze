"""Isolated week->month mapping helper.

Week logic may differ from ISO in future, so keep this mapper independent.
"""

from __future__ import annotations


def week_to_month_label(week_label: str) -> str:
    """Convert YYYY-Www -> YYYY-MM (proxy mapping: 4 weeks per month)."""
    try:
        year_text, week_text = week_label.split("-W", 1)
        week_num = int(week_text)
        month_num = ((week_num - 1) // 4) + 1
        if month_num > 12:
            month_num = 12
        return f"{int(year_text):04d}-{month_num:02d}"
    except Exception:
        return "UNKNOWN"
