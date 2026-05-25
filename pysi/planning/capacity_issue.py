from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CapacityIssue:
    issue_type: str
    node_id: str
    product_id: str
    week: Any
    requested_qty: int
    capacity_qty: int
    accepted_qty: int
    blocked_qty: int
    blocked_lot_ids: list[str]
    severity: str
    message: str
