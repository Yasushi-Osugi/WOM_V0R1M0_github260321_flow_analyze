"""Canonical and raw row types for plan input granularity normalization."""

from __future__ import annotations

from dataclasses import dataclass

ALLOWED_PLAN_TYPES: set[str] = {"S", "P", "demand", "supply", "initial_inventory"}
ALLOWED_SOURCE_GRANULARITIES: set[str] = {"monthly", "weekly", "case_weekly"}


@dataclass
class WeeklyPlanRow:
    scenario_id: str
    product_id: str
    node_id: str
    week: str
    plan_type: str
    quantity: float
    source_granularity: str
    source_id: str = ""
    comment: str = ""


@dataclass
class MonthlyPlanInputRow:
    scenario_id: str
    product_id: str
    node_id: str
    month: str
    plan_type: str
    quantity: float
    source_id: str = ""
    comment: str = ""


@dataclass
class WeeklyPlanInputRow:
    scenario_id: str
    product_id: str
    node_id: str
    week: str
    plan_type: str
    quantity: float
    source_id: str = ""
    comment: str = ""
