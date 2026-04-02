#pysi/bridge/future_demand.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ConsumerStateSnapshot:
    brand_loyalty: float
    repeat_intent: float
    switch_cost_perception: float
    price_sensitivity: float
    habit_strength: float
    well_being_degree: float


@dataclass
class FutureDemandParams:
    alpha_repeat: float = 0.40
    alpha_brand: float = 0.25
    alpha_habit: float = 0.20
    alpha_price: float = 0.30
    alpha_switch: float = 0.15
    alpha_wellbeing: float = 0.30

    min_total_multiplier: float = 0.50
    max_total_multiplier: float = 1.50


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_0_100(x: float) -> float:
    return clamp(x, 0.0, 100.0) / 100.0


def compute_future_demand_multiplier(
    state: ConsumerStateSnapshot,
    params: Optional[FutureDemandParams] = None,
) -> float:
    if params is None:
        params = FutureDemandParams()

    r = normalize_0_100(state.repeat_intent)
    b = normalize_0_100(state.brand_loyalty)
    h = normalize_0_100(state.habit_strength)
    p = normalize_0_100(state.price_sensitivity)
    s = normalize_0_100(state.switch_cost_perception)
    w = normalize_0_100(state.well_being_degree)

    m_repeat = 1.0 + params.alpha_repeat * (r - 0.5)
    m_brand = 1.0 + params.alpha_brand * (b - 0.5)
    m_habit = 1.0 + params.alpha_habit * (h - 0.5)
    m_price = 1.0 - params.alpha_price * p
    m_switch = 1.0 + params.alpha_switch * (s - 0.5)
    m_wellbeing = 1.0 + params.alpha_wellbeing * (w - 0.5)

    total = (
        m_repeat
        * m_brand
        * m_habit
        * m_price
        * m_switch
        * m_wellbeing
    )

    return clamp(total, params.min_total_multiplier, params.max_total_multiplier)


def compute_future_demand(
    baseline_demand: float,
    state: ConsumerStateSnapshot,
    params: Optional[FutureDemandParams] = None,
) -> float:
    multiplier = compute_future_demand_multiplier(state, params=params)
    return max(0.0, baseline_demand * multiplier)
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ConsumerStateSnapshot:
    brand_loyalty: float
    repeat_intent: float
    switch_cost_perception: float
    price_sensitivity: float
    habit_strength: float
    well_being_degree: float


@dataclass
class FutureDemandParams:
    alpha_repeat: float = 0.40
    alpha_brand: float = 0.25
    alpha_habit: float = 0.20
    alpha_price: float = 0.30
    alpha_switch: float = 0.15
    alpha_wellbeing: float = 0.30

    min_total_multiplier: float = 0.50
    max_total_multiplier: float = 1.50


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_0_100(x: float) -> float:
    return clamp(x, 0.0, 100.0) / 100.0


def compute_future_demand_multiplier(
    state: ConsumerStateSnapshot,
    params: Optional[FutureDemandParams] = None,
) -> float:
    if params is None:
        params = FutureDemandParams()

    r = normalize_0_100(state.repeat_intent)
    b = normalize_0_100(state.brand_loyalty)
    h = normalize_0_100(state.habit_strength)
    p = normalize_0_100(state.price_sensitivity)
    s = normalize_0_100(state.switch_cost_perception)
    w = normalize_0_100(state.well_being_degree)

    m_repeat = 1.0 + params.alpha_repeat * (r - 0.5)
    m_brand = 1.0 + params.alpha_brand * (b - 0.5)
    m_habit = 1.0 + params.alpha_habit * (h - 0.5)
    m_price = 1.0 - params.alpha_price * p
    m_switch = 1.0 + params.alpha_switch * (s - 0.5)
    m_wellbeing = 1.0 + params.alpha_wellbeing * (w - 0.5)

    total = (
        m_repeat
        * m_brand
        * m_habit
        * m_price
        * m_switch
        * m_wellbeing
    )

    return clamp(total, params.min_total_multiplier, params.max_total_multiplier)


def compute_future_demand(
    baseline_demand: float,
    state: ConsumerStateSnapshot,
    params: Optional[FutureDemandParams] = None,
) -> float:
    multiplier = compute_future_demand_multiplier(state, params=params)
    return max(0.0, baseline_demand * multiplier)