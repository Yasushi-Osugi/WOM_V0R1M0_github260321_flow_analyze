#pysi/bridge/consumer_events.py

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any


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

    # -100〜100: 正負あり
    satisfaction_stock: float = 0.0

    # 0〜100: 高いほど強い
    brand_loyalty: float = 50.0
    repeat_intent: float = 50.0
    switch_cost_perception: float = 50.0
    price_sensitivity: float = 50.0
    habit_strength: float = 0.0
    well_being_degree: float = 50.0

    last_time_bucket: str = ""
    history_count: int = 0


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


#@STOP initial test version
#def apply_decay(state: WellBeingState) -> None:
#    """
#    event 適用前の自然減衰。
#    直感:
#    - satisfaction は比較的忘れやすい
#    - brand / well-being はやや長持ち
#    - habit はもっと長持ち
#    """
#    state.satisfaction_stock *= 0.97
#    state.brand_loyalty *= 0.995
#    state.repeat_intent *= 0.99
#    state.switch_cost_perception *= 0.995
#    state.price_sensitivity *= 0.992
#    state.habit_strength *= 0.998
#    state.well_being_degree *= 0.995

#@STOP 2nd tuning
#def apply_decay(state: WellBeingState) -> None:
#    """
#    event 適用前の自然減衰。
#    チューニング方針:
#    - brand / repeat / well-being が 100 に張り付きにくいよう、
#      前回版より少しだけ減衰を強める
#    """
#    state.satisfaction_stock *= 0.965
#    state.brand_loyalty *= 0.992
#    state.repeat_intent *= 0.985
#    state.switch_cost_perception *= 0.992
#    state.price_sensitivity *= 0.990
#    state.habit_strength *= 0.997
#    state.well_being_degree *= 0.990


def apply_decay(state: WellBeingState) -> None:
    state.satisfaction_stock *= 0.965
    state.brand_loyalty *= 0.992
    state.repeat_intent *= 0.985
    state.switch_cost_perception *= 0.992
    state.price_sensitivity *= 0.990
    state.habit_strength *= 0.997
    state.well_being_degree *= 0.988



def apply_mot_event_to_wellbeing_state(
    state: WellBeingState,
    event: MomentOfTruthEvent,
) -> WellBeingState:
    if state.consumer_node_id != event.consumer_node_id or state.product_id != event.product_id:
        raise ValueError("State and event target do not match")

    # 1) まず自然減衰
    apply_decay(state)

    # 2) event 影響量
    score = float(event.score_delta or 0.0)

    #@STOP 2nd tuning
    #if event.event_type == MomentOfTruthType.EXPERIENCE_POSITIVE:
    #    state.satisfaction_stock += 1.4 + score * 0.8
    #    state.brand_loyalty += 0.8 + score * 0.4
    #    state.repeat_intent += 0.9 + score * 0.4
    #    state.habit_strength += 0.25
    #    state.well_being_degree += 1.2 + score * 0.8

    if event.event_type == MomentOfTruthType.EXPERIENCE_POSITIVE:
        state.satisfaction_stock += 1.4 + score * 0.8
        state.brand_loyalty += 0.8 + score * 0.4
        state.repeat_intent += 0.9 + score * 0.4
        state.habit_strength += 0.25
        state.well_being_degree += 0.9 + score * 0.6

    elif event.event_type == MomentOfTruthType.EXPERIENCE_NEGATIVE:
        state.satisfaction_stock -= 4.0 + abs(score)
        state.brand_loyalty -= 2.0 + abs(score) * 0.5
        state.repeat_intent -= 2.5 + abs(score) * 0.4
        state.price_sensitivity += 1.2
        state.habit_strength -= 0.5
        state.well_being_degree -= 2.0 + abs(score)

    #@STOP 2nd tuning
    #elif event.event_type == MomentOfTruthType.VALUE_EXPECTATION_MET:
    #    state.satisfaction_stock += 1.0 + score * 0.8
    #    state.brand_loyalty += 0.6 + score * 0.4
    #    state.repeat_intent += 0.8 + score * 0.4
    #    state.well_being_degree += 1.0 + score * 0.8

    elif event.event_type == MomentOfTruthType.VALUE_EXPECTATION_MET:
        state.satisfaction_stock += 1.0 + score * 0.8
        state.brand_loyalty += 0.6 + score * 0.4
        state.repeat_intent += 0.8 + score * 0.4
        state.well_being_degree += 0.7 + score * 0.6

    elif event.event_type == MomentOfTruthType.VALUE_EXPECTATION_FAILED:
        state.satisfaction_stock -= 2.5 + abs(score)
        state.brand_loyalty -= 1.5 + abs(score) * 0.4
        state.repeat_intent -= 1.8 + abs(score) * 0.4
        state.switch_cost_perception -= 1.0
        state.well_being_degree -= 1.8 + abs(score)

    elif event.event_type == MomentOfTruthType.STOCKOUT_EXPERIENCED:
        state.satisfaction_stock -= 2.0
        state.brand_loyalty -= 2.2
        state.repeat_intent -= 3.2
        state.switch_cost_perception -= 2.0
        state.price_sensitivity += 1.2
        state.well_being_degree -= 2.8

    elif event.event_type == MomentOfTruthType.PRICE_RESISTANCE_FELT:
        state.satisfaction_stock -= 1.0
        state.repeat_intent -= 1.8
        state.price_sensitivity += 2.0 + abs(score)
        state.well_being_degree -= 1.2

    # 3) 飽和処理（レンジ固定）
    state.satisfaction_stock = clamp(state.satisfaction_stock, -100.0, 100.0)
    state.brand_loyalty = clamp(state.brand_loyalty, 0.0, 100.0)
    state.repeat_intent = clamp(state.repeat_intent, 0.0, 100.0)
    state.switch_cost_perception = clamp(state.switch_cost_perception, 0.0, 100.0)
    state.price_sensitivity = clamp(state.price_sensitivity, 0.0, 100.0)
    state.habit_strength = clamp(state.habit_strength, 0.0, 100.0)
    state.well_being_degree = clamp(state.well_being_degree, 0.0, 100.0)

    # 4) metadata 更新
    state.last_time_bucket = event.time_bucket
    state.history_count += 1
    return state
