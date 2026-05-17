"""PlanNode PSI seeding from PsiSeedRecord rows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from pysi.adapters.psi_seed import PsiSeedRecord

PSI_BUCKET_INDEX: dict[str, int] = {
    "S": 0,
    "CO": 1,
    "I": 2,
    "P": 3,
}

_LAYER_TO_ATTR: dict[str, str] = {
    "demand": "psi4demand",
    "supply": "psi4supply",
}


@dataclass
class PlanNodeSeedingResult:
    scenario_id: str
    product_id: str
    seeded_count: int = 0
    skipped_count: int = 0
    missing_node_ids: list[str] = field(default_factory=list)
    invalid_weeks: list[dict] = field(default_factory=list)
    invalid_buckets: list[dict] = field(default_factory=list)
    seeded_by_key: dict[tuple, int] = field(default_factory=dict)
    dry_run: bool = False


def _resolve_week_index(week: str, week_indexer: dict[str, int] | Callable[[str], int]) -> int:
    if callable(week_indexer):
        return week_indexer(week)
    return week_indexer[week]


def apply_psi_seed_records_to_plan_nodes(
    seed_records: list[PsiSeedRecord],
    *,
    plan_node_lookup: dict[str, Any],
    week_indexer: dict[str, int] | Callable[[str], int],
    dry_run: bool = False,
) -> PlanNodeSeedingResult:
    scenario_id = seed_records[0].scenario_id if seed_records else ""
    product_id = seed_records[0].product_id if seed_records else ""
    result = PlanNodeSeedingResult(
        scenario_id=scenario_id,
        product_id=product_id,
        dry_run=dry_run,
    )

    for record in seed_records:
        if record.layer not in _LAYER_TO_ATTR:
            raise ValueError(f"Unsupported PSI layer: {record.layer}")
        if record.bucket not in PSI_BUCKET_INDEX:
            raise ValueError(f"Unsupported PSI bucket: {record.bucket}")

        node = plan_node_lookup.get(record.node_id)
        if node is None:
            result.skipped_count += 1
            if record.node_id not in result.missing_node_ids:
                result.missing_node_ids.append(record.node_id)
            continue

        try:
            week_index = _resolve_week_index(record.week, week_indexer)
        except (KeyError, ValueError, TypeError):
            result.skipped_count += 1
            result.invalid_weeks.append({"node_id": record.node_id, "week": record.week})
            continue

        psi_by_week = getattr(node, _LAYER_TO_ATTR[record.layer])
        if not isinstance(week_index, int) or week_index < 0 or week_index >= len(psi_by_week):
            result.skipped_count += 1
            result.invalid_weeks.append({"node_id": record.node_id, "week": record.week, "index": week_index})
            continue

        bucket_index = PSI_BUCKET_INDEX[record.bucket]
        bucket_list = psi_by_week[week_index][bucket_index]
        if not isinstance(bucket_list, list):
            raise TypeError(
                f"Target PSI bucket is not a list: node_id={record.node_id}, week={record.week}, "
                f"layer={record.layer}, bucket={record.bucket}"
            )

        if not dry_run:
            bucket_list.append(record.lot_id)

        result.seeded_count += 1
        seed_key = (record.node_id, record.week, record.layer, record.bucket)
        result.seeded_by_key[seed_key] = result.seeded_by_key.get(seed_key, 0) + 1

    return result
