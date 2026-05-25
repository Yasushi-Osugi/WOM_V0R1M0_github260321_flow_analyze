from __future__ import annotations

import csv
from pathlib import Path

from pysi.capacity.capacity_model import CapacityBucket


def load_capacity_master_csv(path: str | Path) -> list[CapacityBucket]:
    csv_path = Path(path)
    if not csv_path.exists():
        raise ValueError(f"capacity master csv not found: {csv_path}")

    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("capacity master csv has no header")

        required = {
            "scenario_id",
            "node_name",
            "product_name",
            "week",
            "capacity_type",
            "capacity_qty",
        }
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"capacity master csv missing required columns: {sorted(missing)}")

        buckets: list[CapacityBucket] = []
        for idx, row in enumerate(reader, start=2):
            try:
                capacity_type = (row.get("capacity_type") or "").strip().upper()
                if capacity_type not in {"P", "S", "I"}:
                    raise ValueError(f"invalid capacity_type '{capacity_type}'")

                cap_mode = (row.get("cap_mode") or "soft").strip().lower()
                if cap_mode not in {"soft", "hard"}:
                    raise ValueError(f"invalid cap_mode '{cap_mode}'")

                capacity_qty = int(str(row.get("capacity_qty") or "").strip())
                priority = int(str(row.get("priority") or "100").strip() or "100")

                buckets.append(
                    CapacityBucket(
                        scenario_id=(row.get("scenario_id") or "").strip(),
                        node_name=(row.get("node_name") or "").strip(),
                        product_name=(row.get("product_name") or "").strip(),
                        week=(row.get("week") or "").strip(),
                        capacity_type=capacity_type,
                        capacity_qty=capacity_qty,
                        cap_mode=cap_mode,
                        unit=(row.get("unit") or "LOT").strip() or "LOT",
                        priority=priority,
                        calendar_id=(row.get("calendar_id") or "").strip(),
                        comment=(row.get("comment") or "").strip(),
                    )
                )
            except Exception as exc:
                raise ValueError(f"invalid row at line {idx}: {exc}") from exc

    return buckets
