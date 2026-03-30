#pysi/bridge/consumer_state_repository.py

from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Tuple

from pysi.bridge.consumer_events import (
    MomentOfTruthEvent,
    WellBeingState,
    apply_mot_event_to_wellbeing_state,
)


class ConsumerStateRepository:
    """
    consumer_node_id × product_id ごとの WellBeingState を保持する最小 in-memory repository。
    """

    def __init__(self):
        self._states: Dict[Tuple[str, str], WellBeingState] = {}

    def get_or_create(self, consumer_node_id: str, product_id: str) -> WellBeingState:
        key = (str(consumer_node_id), str(product_id))
        if key not in self._states:
            self._states[key] = WellBeingState(
                consumer_node_id=str(consumer_node_id),
                product_id=str(product_id),
            )
        return self._states[key]

    def apply_event(self, event: MomentOfTruthEvent) -> WellBeingState:
        state = self.get_or_create(event.consumer_node_id, event.product_id)
        updated = apply_mot_event_to_wellbeing_state(state, event)
        self._states[(event.consumer_node_id, event.product_id)] = updated
        return updated

    def get_state_dict(self, consumer_node_id: str, product_id: str) -> dict:
        state = self.get_or_create(consumer_node_id, product_id)
        return asdict(state)

    def export_all_states(self) -> Dict[Tuple[str, str], dict]:
        return {k: asdict(v) for k, v in self._states.items()}
