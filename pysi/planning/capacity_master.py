from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv

VALID_CAPACITY_TYPES = {"P", "S", "I"}
VALID_CAP_MODES = {"soft", "hard"}


@dataclass
class CapacityMasterRecord:
    scenario_id: str
    tree_side: str
    node_name: str
    product_name: str
    week: str
    capacity_type: str
    capacity_qty: int
    cap_mode: str = "soft"
    unit: str = "LOT"
    priority: int = 100
    calendar_id: str = ""
    comment: str = ""


def _req_str(row: dict[str, str], key: str, row_num: int) -> str:
    value = str(row.get(key, "")).strip()
    if not value:
        raise ValueError(f"{key} is required (row {row_num})")
    return value


def load_capacity_master_csv(path: str | Path) -> list[CapacityMasterRecord]:
    records: list[CapacityMasterRecord] = []
    csv_path = Path(path)
    with csv_path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row_num, row in enumerate(reader, start=2):
            scenario_id = _req_str(row, "scenario_id", row_num)
            tree_side = _req_str(row, "tree_side", row_num)
            node_name = _req_str(row, "node_name", row_num)
            product_name = _req_str(row, "product_name", row_num)
            week = _req_str(row, "week", row_num)
            capacity_type = _req_str(row, "capacity_type", row_num)
            if capacity_type not in VALID_CAPACITY_TYPES:
                raise ValueError(f"invalid capacity_type={capacity_type!r} (row {row_num})")

            cap_mode = str(row.get("cap_mode", "") or "soft").strip() or "soft"
            if cap_mode not in VALID_CAP_MODES:
                raise ValueError(f"invalid cap_mode={cap_mode!r} (row {row_num})")

            try:
                capacity_qty = int(str(row.get("capacity_qty", "")).strip())
            except ValueError as exc:
                raise ValueError(f"capacity_qty must be int (row {row_num})") from exc

            priority_raw = str(row.get("priority", "") or "").strip()
            priority = 100 if priority_raw == "" else int(priority_raw)

            records.append(
                CapacityMasterRecord(
                    scenario_id=scenario_id,
                    tree_side=tree_side,
                    node_name=node_name,
                    product_name=product_name,
                    week=week,
                    capacity_type=capacity_type,
                    capacity_qty=capacity_qty,
                    cap_mode=cap_mode,
                    unit=(str(row.get("unit", "") or "LOT").strip() or "LOT"),
                    priority=priority,
                    calendar_id=str(row.get("calendar_id", "")).strip(),
                    comment=str(row.get("comment", "")).strip(),
                )
            )
    return records


def build_capacity_lookup(records: list[CapacityMasterRecord]) -> dict[tuple[str, str, str, str, str, str], CapacityMasterRecord]:
    lookup: dict[tuple[str, str, str, str, str, str], CapacityMasterRecord] = {}
    for record in sorted(records, key=lambda r: r.priority):
        key = (
            record.scenario_id,
            record.tree_side,
            record.node_name,
            record.product_name,
            record.week,
            record.capacity_type,
        )
        lookup.setdefault(key, record)
    return lookup


def get_capacity_record(
    lookup: dict[tuple[str, str, str, str, str, str], CapacityMasterRecord],
    *,
    scenario_id: str,
    tree_side: str,
    node_name: str,
    product_name: str,
    week: str,
    capacity_type: str,
) -> CapacityMasterRecord | None:
    exact = (scenario_id, tree_side, node_name, product_name, week, capacity_type)
    if exact in lookup:
        return lookup[exact]
    wildcard = (scenario_id, tree_side, node_name, "*", week, capacity_type)
    return lookup.get(wildcard)