from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pysi.planning.capacity_bucket import CapacityBucket
from pysi.planning.capacity_issue import CapacityIssue


@dataclass
class CapacityUsageRecord:
    node_id: str
    product_id: str
    week: Any
    requested_qty: int
    capacity_qty: int | None
    accepted_qty: int
    blocked_qty: int
    used_qty: int
    remaining_qty: int | None


@dataclass
class ForwardPushWithCapacityResult:
    pushed_lots: list[Any] = field(default_factory=list)
    blocked_lots: list[Any] = field(default_factory=list)
    backlog_lots: list[Any] = field(default_factory=list)
    capacity_usage: list[CapacityUsageRecord] = field(default_factory=list)
    capacity_issues: list[CapacityIssue] = field(default_factory=list)


def _lot_id(lot: Any) -> str:
    if isinstance(lot, dict):
        return str(lot.get("lot_id", lot))
    return str(lot)


class ForwardPushWithCapacityPlanner:
    def consume_lots_with_capacity(
        self,
        *,
        node_id: str,
        product_id: str,
        week: Any,
        requested_lots: list[Any],
        capacity_qty: int | None,
    ) -> ForwardPushWithCapacityResult:
        result = ForwardPushWithCapacityResult()

        # MVP policy: when capacity data is missing, treat as unlimited capacity.
        # This preserves compatibility for scenarios without complete capacity masters.
        if capacity_qty is None:
            result.pushed_lots = list(requested_lots)
            result.capacity_usage.append(
                CapacityUsageRecord(
                    node_id=node_id,
                    product_id=product_id,
                    week=week,
                    requested_qty=len(requested_lots),
                    capacity_qty=None,
                    accepted_qty=len(requested_lots),
                    blocked_qty=0,
                    used_qty=len(requested_lots),
                    remaining_qty=None,
                )
            )
            return result

        bucket = CapacityBucket(
            node_id=node_id,
            product_id=product_id,
            week=week,
            capacity_qty=max(capacity_qty, 0),
        )

        accepted_lots, blocked_lots = bucket.consume(requested_lots)

        result.pushed_lots = accepted_lots
        result.blocked_lots = blocked_lots
        result.backlog_lots = list(blocked_lots)

        result.capacity_usage.append(
            CapacityUsageRecord(
                node_id=node_id,
                product_id=product_id,
                week=week,
                requested_qty=len(requested_lots),
                capacity_qty=bucket.capacity_qty,
                accepted_qty=len(accepted_lots),
                blocked_qty=len(blocked_lots),
                used_qty=bucket.used_qty,
                remaining_qty=bucket.remaining_qty,
            )
        )

        if blocked_lots:
            result.capacity_issues.append(
                CapacityIssue(
                    issue_type="CAPACITY_SHORTAGE",
                    node_id=node_id,
                    product_id=product_id,
                    week=week,
                    requested_qty=len(requested_lots),
                    capacity_qty=bucket.capacity_qty,
                    accepted_qty=len(accepted_lots),
                    blocked_qty=len(blocked_lots),
                    blocked_lot_ids=[_lot_id(lot) for lot in blocked_lots],
                    severity="warning",
                    message=(
                        f"Capacity shortage at {node_id}/{product_id}/{week}: "
                        f"requested={len(requested_lots)}, capacity={bucket.capacity_qty}, "
                        f"blocked={len(blocked_lots)}"
                    ),
                )
            )

        return result