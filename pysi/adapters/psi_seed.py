"""PSI seed record generation from canonical weekly plan rows."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from pysi.adapters.lot_generation import LotGenerationConfig, LotHeader, generate_lots_from_weekly_plan
from pysi.adapters.weekly_plan_table import WeeklyPlanRow

DEFAULT_BUCKET_MAPPING: dict[str, tuple[str, str]] = {
    "demand": ("demand", "S"),
    "S": ("demand", "S"),
    "supply": ("demand", "P"),
    "P": ("demand", "P"),
    "initial_inventory": ("supply", "I"),
}


@dataclass
class PsiSeedRecord:
    scenario_id: str
    product_id: str
    node_id: str
    week: str
    layer: str
    bucket: str
    lot_id: str
    quantity: float
    source_id: str = ""


def generate_psi_seed_records(
    rows: list[WeeklyPlanRow],
    *,
    lot_config: LotGenerationConfig | None = None,
    bucket_mapping: dict[str, tuple[str, str]] | None = None,
    row_attributes: dict[int, dict] | None = None,
) -> tuple[list[LotHeader], list[PsiSeedRecord]]:
    mapping = dict(DEFAULT_BUCKET_MAPPING)
    if bucket_mapping:
        mapping.update(bucket_mapping)

    lot_headers: list[LotHeader] = []
    seed_records: list[PsiSeedRecord] = []

    for idx, row in enumerate(rows):
        if row.plan_type not in mapping:
            raise ValueError(f"Unsupported plan_type for PSI seed mapping: {row.plan_type}")

        layer, bucket = mapping[row.plan_type]
        attributes = (row_attributes or {}).get(idx)
        row_lots = generate_lots_from_weekly_plan(row, config=lot_config, attributes=attributes)
        lot_headers.extend(row_lots)

        for lot in row_lots:
            seed_records.append(
                PsiSeedRecord(
                    scenario_id=lot.scenario_id,
                    product_id=lot.product_id,
                    node_id=lot.node_id,
                    week=lot.week,
                    layer=layer,
                    bucket=bucket,
                    lot_id=lot.lot_id,
                    quantity=lot.quantity,
                    source_id=lot.source_id,
                )
            )

    return lot_headers, seed_records


def build_psi_seed_table(seed_records: list[PsiSeedRecord]) -> dict[tuple, list[str]]:
    table: dict[tuple, list[str]] = defaultdict(list)
    for record in seed_records:
        key = (
            record.scenario_id,
            record.product_id,
            record.node_id,
            record.week,
            record.layer,
            record.bucket,
        )
        table[key].append(record.lot_id)
    return dict(table)
