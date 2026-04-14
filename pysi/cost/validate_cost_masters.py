"""Validation for cost masters used by reporting MVP."""

from __future__ import annotations

from typing import Any


REQUIRED_TOP_KEYS = (
    "node_cost_rates",
    "lane_cost_rates",
    "market_cost_rates",
    "allocation_rules",
)


def validate_cost_masters(cost_masters: dict[str, Any]) -> list[str]:
    """Validate shape and return human-readable errors.

    Empty list means validation passed.
    """
    errors: list[str] = []

    for key in REQUIRED_TOP_KEYS:
        if key not in cost_masters:
            errors.append(f"missing top-level key: {key}")

    for group in ("node_cost_rates", "lane_cost_rates", "market_cost_rates"):
        table = cost_masters.get(group, {})
        if table is None:
            errors.append(f"{group} must be a mapping")
            continue
        if not isinstance(table, dict):
            errors.append(f"{group} must be a mapping")
            continue

        for item_key, category_map in table.items():
            if not isinstance(category_map, dict):
                errors.append(f"{group}.{item_key} must be a mapping")
                continue
            for category, rate in category_map.items():
                if not isinstance(rate, (int, float)):
                    errors.append(
                        f"{group}.{item_key}.{category} must be numeric (got {type(rate).__name__})"
                    )

    rules = cost_masters.get("allocation_rules", [])
    if not isinstance(rules, list):
        errors.append("allocation_rules must be a list")
    else:
        for idx, rule in enumerate(rules):
            if not isinstance(rule, dict):
                errors.append(f"allocation_rules[{idx}] must be an object")

    return errors
