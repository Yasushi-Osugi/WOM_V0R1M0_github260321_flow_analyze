"""Pipeline helpers for WeeklyPlanRow -> lots -> PSI seed table."""

from __future__ import annotations

from pysi.adapters.lot_generation import LotGenerationConfig, LotHeader
from pysi.adapters.psi_seed import PsiSeedRecord, build_psi_seed_table, generate_psi_seed_records
from pysi.adapters.weekly_plan_table import WeeklyPlanRow


def weekly_rows_to_lots_and_seed_table(
    rows: list[WeeklyPlanRow],
    *,
    lot_config: LotGenerationConfig | None = None,
    bucket_mapping: dict[str, tuple[str, str]] | None = None,
    row_attributes: dict[int, dict] | None = None,
) -> tuple[list[LotHeader], list[PsiSeedRecord], dict[tuple, list[str]]]:
    lot_headers, seed_records = generate_psi_seed_records(
        rows,
        lot_config=lot_config,
        bucket_mapping=bucket_mapping,
        row_attributes=row_attributes,
    )
    seed_table = build_psi_seed_table(seed_records)
    return lot_headers, seed_records, seed_table
