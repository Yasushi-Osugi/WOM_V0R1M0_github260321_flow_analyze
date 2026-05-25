from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CapacityBucket:
    """Weekly capacity bucket for a single node/product/week key."""

    node_id: str
    product_id: str
    week: Any
    capacity_qty: int
    used_qty: int = 0

    @property
    def remaining_qty(self) -> int:
        return max(self.capacity_qty - self.used_qty, 0)

    def consume(self, requested_lots: list[Any]) -> tuple[list[Any], list[Any]]:
        """Consume lots with first-in, first-pushed rule."""
        accepted_count = min(len(requested_lots), self.remaining_qty)
        accepted_lots = list(requested_lots[:accepted_count])
        blocked_lots = list(requested_lots[accepted_count:])
        self.used_qty += accepted_count
        return accepted_lots, blocked_lots
