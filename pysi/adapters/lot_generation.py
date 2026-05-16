"""Lot generation helpers for canonical weekly plan rows."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil, floor, isclose
from typing import Any

from pysi.adapters.weekly_plan_table import WeeklyPlanRow


@dataclass
class LotHeader:
    lot_id: str
    scenario_id: str
    product_id: str
    node_id: str
    week: str
    plan_type: str
    quantity: float
    lot_size: float
    source_granularity: str
    source_id: str = ""
    sequence_no: int = 0
    quality_status: str = "usable"
    priority: int = 100
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class LotGenerationConfig:
    lot_size: float = 1.0
    quantity_mode: str = "lot_count"
    lot_id_prefix: str = ""
    allow_fractional_last_lot: bool = True
    sequence_digits: int = 6


def _sanitize_lot_token(value: str) -> str:
    sanitized = value.strip().replace(" ", "_").replace("/", "_").replace(":", "_")
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    return sanitized


def _build_lot_id(row: WeeklyPlanRow, *, seq: int, cfg: LotGenerationConfig) -> str:
    parts: list[str] = []
    if cfg.lot_id_prefix:
        parts.append(_sanitize_lot_token(cfg.lot_id_prefix))
    parts.extend(
        [
            _sanitize_lot_token(row.scenario_id),
            _sanitize_lot_token(row.product_id),
            _sanitize_lot_token(row.node_id),
            _sanitize_lot_token(row.week),
            _sanitize_lot_token(row.plan_type),
            str(seq).zfill(cfg.sequence_digits),
        ]
    )
    return "-".join(parts)


def _lot_quantities(quantity: float, cfg: LotGenerationConfig) -> list[float]:
    if cfg.quantity_mode == "single_lot":
        return [quantity]

    if cfg.quantity_mode == "lot_count":
        whole = floor(quantity)
        remainder = round(quantity - whole, 12)
        lots = [cfg.lot_size] * whole
        if remainder > 0:
            if cfg.allow_fractional_last_lot:
                lots.append(remainder * cfg.lot_size)
            else:
                lots.append(cfg.lot_size)
        return lots

    if cfg.quantity_mode == "physical_quantity":
        if cfg.lot_size <= 0:
            raise ValueError("lot_size must be > 0 for physical_quantity mode")
        count = ceil(quantity / cfg.lot_size)
        lots = [cfg.lot_size] * max(count, 0)
        if lots and cfg.allow_fractional_last_lot:
            remainder = quantity - (cfg.lot_size * (count - 1))
            if remainder > 0:
                lots[-1] = remainder
        return lots

    raise ValueError(f"Unsupported quantity_mode: {cfg.quantity_mode}")


def generate_lots_from_weekly_plan(
    row: WeeklyPlanRow,
    *,
    config: LotGenerationConfig | None = None,
    attributes: dict | None = None,
) -> list[LotHeader]:
    cfg = config or LotGenerationConfig()
    if row.quantity < 0:
        raise ValueError("WeeklyPlanRow.quantity must be >= 0")
    if isclose(row.quantity, 0.0, abs_tol=1e-12):
        return []

    lot_quantities = _lot_quantities(float(row.quantity), cfg)
    headers: list[LotHeader] = []
    for idx, lot_quantity in enumerate(lot_quantities, start=1):
        headers.append(
            LotHeader(
                lot_id=_build_lot_id(row, seq=idx, cfg=cfg),
                scenario_id=row.scenario_id,
                product_id=row.product_id,
                node_id=row.node_id,
                week=row.week,
                plan_type=row.plan_type,
                quantity=float(lot_quantity),
                lot_size=cfg.lot_size,
                source_granularity=row.source_granularity,
                source_id=row.source_id,
                sequence_no=idx,
                attributes=dict(attributes or {}),
            )
        )
    return headers
