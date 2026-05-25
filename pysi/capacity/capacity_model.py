from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class CapacityBucket:
    scenario_id: str
    node_name: str
    product_name: str
    week: int | str
    capacity_type: Literal["P", "S", "I"]
    capacity_qty: int
    cap_mode: Literal["soft", "hard"] = "soft"
    unit: str = "LOT"
    priority: int = 100
    calendar_id: str = ""
    comment: str = ""


@dataclass
class CapacityUsage:
    scenario_id: str
    tree_side: str
    node_name: str
    product_name: str
    week: int | str
    capacity_type: Literal["P", "S", "I"]
    capacity_qty: int
    used_qty: int
    used_lot_ids: list[str]

    @property
    def remaining_qty(self) -> int:
        return max(self.capacity_qty - self.used_qty, 0)

    @property
    def utilization(self) -> float:
        if self.capacity_qty <= 0:
            return 0.0
        return self.used_qty / self.capacity_qty


@dataclass
class CapacityViolation:
    scenario_id: str
    tree_side: str
    node_name: str
    product_name: str
    week: int | str
    capacity_type: Literal["P", "S", "I"]
    cap_mode: Literal["soft", "hard"]
    capacity_qty: int
    required_qty: int
    overflow_qty: int
    violation_type: str
    overflow_lot_ids: list[str]
    action: str
