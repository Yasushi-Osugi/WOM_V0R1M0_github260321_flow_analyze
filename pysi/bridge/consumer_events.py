# pysi/bridge/consumer_events.py

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional


class MomentOfTruthType(str, Enum):
    EXPERIENCE_POSITIVE = "experience_positive"
    EXPERIENCE_NEGATIVE = "experience_negative"
    VALUE_EXPECTATION_MET = "value_expectation_met"
    VALUE_EXPECTATION_FAILED = "value_expectation_failed"
    STOCKOUT_EXPERIENCED = "stockout_experienced"
    PRICE_RESISTANCE_FELT = "price_resistance_felt"


@dataclass(frozen=True)
class MomentOfTruthEvent:
    event_type: MomentOfTruthType
    consumer_node_id: str
    product_id: str
    time_bucket: str
    lot_id: str = ""
    score_delta: float = 0.0
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WellBeingState:
    consumer_node_id: str
    product_id: str

    satisfaction_stock: float = 0.0
    brand_loyalty: float = 0.0
    repeat_intent: float = 0.0
    switch_cost_perception: float = 0.0
    price_sensitivity: float = 0.0
    habit_strength: float = 0.0
    well_being_degree: float = 0.0

    last_time_bucket: str = ""
    history_count: int = 0


def apply_mot_event_to_wellbeing_state(
    state: WellBeingState,
    event: MomentOfTruthEvent,
) -> WellBeingState:
    if state.consumer_node_id != event.consumer_node_id or state.product_id != event.product_id:
        raise ValueError("State and event target do not match")

    score = float(event.score_delta or 0.0)

    if event.event_type == MomentOfTruthType.EXPERIENCE_POSITIVE:
        state.satisfaction_stock += 1.0 + score
        state.brand_loyalty += 0.5 + score * 0.5
        state.repeat_intent += 0.5 + score * 0.3
        state.habit_strength += 0.2

    elif event.event_type == MomentOfTruthType.EXPERIENCE_NEGATIVE:
        state.satisfaction_stock -= 1.0 + abs(score)
        state.brand_loyalty -= 0.5 + abs(score) * 0.5
        state.repeat_intent -= 0.5 + abs(score) * 0.3
        state.price_sensitivity += 0.2
        state.habit_strength -= 0.1

    elif event.event_type == MomentOfTruthType.VALUE_EXPECTATION_MET:
        state.well_being_degree += 1.0 + score
        state.repeat_intent += 0.3
        state.brand_loyalty += 0.2

    elif event.event_type == MomentOfTruthType.VALUE_EXPECTATION_FAILED:
        state.well_being_degree -= 1.0 + abs(score)
        state.repeat_intent -= 0.4
        state.brand_loyalty -= 0.3
        state.switch_cost_perception -= 0.2

    elif event.event_type == MomentOfTruthType.STOCKOUT_EXPERIENCED:
        state.well_being_degree -= 0.8
        state.repeat_intent -= 0.6
        state.brand_loyalty -= 0.4
        state.switch_cost_perception -= 0.5

    elif event.event_type == MomentOfTruthType.PRICE_RESISTANCE_FELT:
        state.price_sensitivity += 0.8 + abs(score)
        state.repeat_intent -= 0.3
        state.well_being_degree -= 0.2

    state.last_time_bucket = event.time_bucket
    state.history_count += 1
    return state
