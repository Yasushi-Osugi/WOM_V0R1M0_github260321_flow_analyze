#pysi/bridge/future_demand_adapter.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from pysi.bridge.future_demand import (
    ConsumerStateSnapshot,
    FutureDemandParams,
    compute_future_demand_multiplier,
)


@dataclass
class MonthlyDemandAdjustmentResult:
    consumer_node_id: str
    product_id: str
    baseline_monthly_demand: float
    adjusted_monthly_demand: float
    multiplier: float
    state_snapshot: ConsumerStateSnapshot


ConsumerStateKey = Tuple[str, str]


def build_consumer_state_snapshot_from_dict(state_dict: dict) -> ConsumerStateSnapshot:
    """
    ConsumerStateRepository.get_state_dict(...) の戻り値から
    FutureDemand 計算用 snapshot を組み立てる。
    """
    return ConsumerStateSnapshot(
        brand_loyalty=float(state_dict.get("brand_loyalty", 50.0)),
        repeat_intent=float(state_dict.get("repeat_intent", 50.0)),
        switch_cost_perception=float(state_dict.get("switch_cost_perception", 50.0)),
        price_sensitivity=float(state_dict.get("price_sensitivity", 50.0)),
        habit_strength=float(state_dict.get("habit_strength", 0.0)),
        well_being_degree=float(state_dict.get("well_being_degree", 50.0)),
    )


def adjust_monthly_demand_for_consumer(
    baseline_monthly_demand: float,
    *,
    consumer_node_id: str,
    product_id: str,
    consumer_state_dict: Optional[dict] = None,
    params: Optional[FutureDemandParams] = None,
) -> MonthlyDemandAdjustmentResult:
    """
    1 consumer node × 1 product の monthly demand を consumer state で補正する。

    consumer_state_dict が無ければ、中立状態(50/50/...)を仮定する。
    """
    if consumer_state_dict is None:
        consumer_state_dict = {
            "brand_loyalty": 50.0,
            "repeat_intent": 50.0,
            "switch_cost_perception": 50.0,
            "price_sensitivity": 50.0,
            "habit_strength": 0.0,
            "well_being_degree": 50.0,
        }

    snapshot = build_consumer_state_snapshot_from_dict(consumer_state_dict)
    multiplier = compute_future_demand_multiplier(snapshot, params=params)
    adjusted = max(0.0, float(baseline_monthly_demand) * multiplier)

    return MonthlyDemandAdjustmentResult(
        consumer_node_id=consumer_node_id,
        product_id=product_id,
        baseline_monthly_demand=float(baseline_monthly_demand),
        adjusted_monthly_demand=adjusted,
        multiplier=multiplier,
        state_snapshot=snapshot,
    )


def adjust_monthly_demand_table_for_consumers(
    baseline_monthly_demand_by_key: Dict[ConsumerStateKey, float],
    consumer_state_dict_by_key: Dict[ConsumerStateKey, dict],
    params: Optional[FutureDemandParams] = None,
) -> Dict[ConsumerStateKey, MonthlyDemandAdjustmentResult]:
    """
    複数 consumer node × product の monthly demand をまとめて補正する。

    Parameters
    ----------
    baseline_monthly_demand_by_key:
        {
            (consumer_node_id, product_id): baseline_monthly_demand,
            ...
        }

    consumer_state_dict_by_key:
        {
            (consumer_node_id, product_id): state_dict,
            ...
        }
    """
    out: Dict[ConsumerStateKey, MonthlyDemandAdjustmentResult] = {}

    for key, baseline in baseline_monthly_demand_by_key.items():
        consumer_node_id, product_id = key
        state_dict = consumer_state_dict_by_key.get(key)

        out[key] = adjust_monthly_demand_for_consumer(
            baseline_monthly_demand=baseline,
            consumer_node_id=consumer_node_id,
            product_id=product_id,
            consumer_state_dict=state_dict,
            params=params,
        )

    return out


def result_to_debug_dict(result: MonthlyDemandAdjustmentResult) -> dict:
    return {
        "consumer_node_id": result.consumer_node_id,
        "product_id": result.product_id,
        "baseline_monthly_demand": result.baseline_monthly_demand,
        "adjusted_monthly_demand": result.adjusted_monthly_demand,
        "multiplier": result.multiplier,
        "state_snapshot": {
            "brand_loyalty": result.state_snapshot.brand_loyalty,
            "repeat_intent": result.state_snapshot.repeat_intent,
            "switch_cost_perception": result.state_snapshot.switch_cost_perception,
            "price_sensitivity": result.state_snapshot.price_sensitivity,
            "habit_strength": result.state_snapshot.habit_strength,
            "well_being_degree": result.state_snapshot.well_being_degree,
        },
    }


if __name__ == "__main__":
    baseline = {
        ("CS_CAL", "CAL_RICE_1"): 1000.0,
        ("CS_JPN", "JPN_RICE_1"): 800.0,
    }

    states = {
        ("CS_CAL", "CAL_RICE_1"): {
            "brand_loyalty": 84.4,
            "repeat_intent": 58.6,
            "switch_cost_perception": 0.0,
            "price_sensitivity": 0.2,
            "habit_strength": 0.0,
            "well_being_degree": 68.1,
        },
        ("CS_JPN", "JPN_RICE_1"): {
            "brand_loyalty": 78.0,
            "repeat_intent": 48.0,
            "switch_cost_perception": 0.0,
            "price_sensitivity": 4.7,
            "habit_strength": 0.0,
            "well_being_degree": 59.2,
        },
    }

    adjusted = adjust_monthly_demand_table_for_consumers(baseline, states)
    for k, v in adjusted.items():
        print(k, result_to_debug_dict(v))