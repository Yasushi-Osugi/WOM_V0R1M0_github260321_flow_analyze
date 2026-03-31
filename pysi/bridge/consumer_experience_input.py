#pysi/bridge/consumer_experience_input.py

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class ConsumerExperienceInput:
    lot_id: str
    consumer_node_id: str
    product_id: str
    time_bucket: str

    availability_ok: int
    price_paid: float
    reference_price: float
    quality_score: float
    complaint_flag: int


ExperienceKey = Tuple[str, str, str, str]


def _to_int(v, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _to_float(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def load_consumer_experience_inputs(csv_path: str | Path) -> Dict[ExperienceKey, ConsumerExperienceInput]:
    path = Path(csv_path)
    out: Dict[ExperienceKey, ConsumerExperienceInput] = {}

    if not path.exists():
        return out

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = ConsumerExperienceInput(
                lot_id=str(row.get("lot_id", "")).strip(),
                consumer_node_id=str(row.get("consumer_node_id", "")).strip(),
                product_id=str(row.get("product_id", "")).strip(),
                time_bucket=str(row.get("time_bucket", "")).strip(),
                availability_ok=_to_int(row.get("availability_ok", 0)),
                price_paid=_to_float(row.get("price_paid", 0.0)),
                reference_price=_to_float(row.get("reference_price", 0.0)),
                quality_score=_to_float(row.get("quality_score", 0.0)),
                complaint_flag=_to_int(row.get("complaint_flag", 0)),
            )
            key: ExperienceKey = (
                item.lot_id,
                item.consumer_node_id,
                item.product_id,
                item.time_bucket,
            )
            out[key] = item

    return out


def lookup_consumer_experience(
    table: Dict[ExperienceKey, ConsumerExperienceInput],
    *,
    lot_id: str,
    consumer_node_id: str,
    product_id: str,
    time_bucket: str,
) -> Optional[ConsumerExperienceInput]:
    return table.get((lot_id, consumer_node_id, product_id, time_bucket))
