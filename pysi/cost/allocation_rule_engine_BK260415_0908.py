"""Allocation rule engine skeleton.

Allocation is intentionally centralized here.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def _group_sum(lines: list[dict[str, Any]], dim: str, key: str, categories: set[str]) -> float:
    return sum(
        float(line.get("amount", 0.0) or 0.0)
        for line in lines
        if line.get(dim) == key and line.get("cost_category") in categories
    )


def _driver_weights(report_input: dict[str, Any], to_dim: str, driver: str) -> dict[str, float]:
    weights = defaultdict(float)
    for rec in report_input.get("records", []):
        bucket = rec.get(to_dim)
        if bucket is None:
            continue
        weights[bucket] += float(rec.get(driver, 0.0) or 0.0)
    total = sum(weights.values())
    if total <= 0:
        # fallback equal split across discovered keys
        keys = list(weights.keys())
        if not keys:
            return {}
        eq = 1.0 / len(keys)
        return {k: eq for k in keys}
    return {k: v / total for k, v in weights.items()}


def apply_allocation_rules(
    cost_result: dict[str, Any],
    allocation_rules: list[dict[str, Any]],
    report_input: dict[str, Any],
) -> dict[str, Any]:
    """Apply simple pool allocation and keep before/after trace."""
    source_lines = list(cost_result.get("cost_lines", []))
    allocated_lines = list(source_lines)
    breakdown: list[dict[str, Any]] = []

    for rule in allocation_rules:
        from_dim = rule.get("from_dim", "node")
        to_dim = rule.get("to_dim", "market")
        from_key = rule.get("from_key")
        driver = rule.get("driver", "sales_units")
        categories = set(rule.get("pool_categories", []))

        if from_key is None or not categories:
            continue

        pool_total = _group_sum(allocated_lines, from_dim, from_key, categories)
        if pool_total <= 0:
            continue

        weights = _driver_weights(report_input=report_input, to_dim=to_dim, driver=driver)
        if not weights:
            continue

        for target_key, weight in weights.items():
            amount = pool_total * weight
            allocated_lines.append(
                {
                    "product": "ALL",
                    "node": from_key,
                    "week": "ALL",
                    "market": target_key if to_dim == "market" else None,
                    "cost_type": "allocation",
                    "cost_category": "allocated_pool",
                    "amount": amount,
                    "allocation_status": "allocated",
                    "allocation_rule": rule.get("name", "unnamed_rule"),
                    "from_dim": from_dim,
                    "to_dim": to_dim,
                    "driver": driver,
                    "weight": weight,
                }
            )
            breakdown.append(
                {
                    "rule_name": rule.get("name", "unnamed_rule"),
                    "from_key": from_key,
                    "to_key": target_key,
                    "driver": driver,
                    "weight": weight,
                    "allocated_amount": amount,
                }
            )

    return {
        "cost_lines_before": source_lines,
        "cost_lines_after": allocated_lines,
        "allocation_breakdown": breakdown,
    }
