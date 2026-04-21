# pysi/master_data/money_master_loader.py

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


# ------------------------------------------------------------
# Data classes
# ------------------------------------------------------------

@dataclass(frozen=True)
class NodeMasterRecord:
    node_name: str
    node_character: str
    display_name: str = ""
    country: str = ""
    company: str = ""
    remarks: str = ""


@dataclass(frozen=True)
class NodeCharacterMoneyMasterRecord:
    node_character: str
    revenue_items: List[str]
    variable_cost_items: List[str]
    fixed_cost_items: List[str]
    inventory_value_items: List[str]
    tax_compare_items: List[str]


@dataclass
class MoneyMasterBundle:
    node_master: Dict[str, NodeMasterRecord]
    money_master: Dict[str, NodeCharacterMoneyMasterRecord]

    def get_node(self, node_name: str) -> Optional[NodeMasterRecord]:
        return self.node_master.get(node_name)

    def get_node_character(self, node_name: str) -> Optional[str]:
        rec = self.get_node(node_name)
        return rec.node_character if rec else None

    def get_display_name(self, node_name: str) -> str:
        rec = self.get_node(node_name)
        if rec and rec.display_name:
            return rec.display_name
        return node_name

    def get_money_master_by_node_name(
        self, node_name: str
    ) -> Optional[NodeCharacterMoneyMasterRecord]:
        node_character = self.get_node_character(node_name)
        if not node_character:
            return None
        return self.money_master.get(node_character)

    def get_money_master_by_node_character(
        self, node_character: str
    ) -> Optional[NodeCharacterMoneyMasterRecord]:
        return self.money_master.get(node_character)


# ------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------

def _split_items(value: str) -> List[str]:
    """
    Split pipe-separated master items.
    Empty / whitespace-only values become [].
    """
    if not value:
        return []
    return [x.strip() for x in value.split("|") if x.strip()]


def _require_columns(row: dict, required: List[str], source_name: str) -> None:
    missing = [col for col in required if col not in row]
    if missing:
        raise ValueError(
            f"{source_name}: missing required columns: {', '.join(missing)}"
        )


# ------------------------------------------------------------
# CSV loaders
# ------------------------------------------------------------

def load_node_master_csv(csv_path: str | Path) -> Dict[str, NodeMasterRecord]:
    """
    Load node master CSV.

    Required columns:
      - node_name
      - node_character

    Optional columns:
      - display_name
      - country
      - company
      - remarks
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"node master CSV not found: {path}")

    out: Dict[str, NodeMasterRecord] = {}

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        first_row_checked = False
        for row in reader:
            if not first_row_checked:
                _require_columns(
                    row,
                    required=["node_name", "node_character"],
                    source_name=str(path),
                )
                first_row_checked = True

            node_name = (row.get("node_name") or "").strip()
            if not node_name:
                continue

            rec = NodeMasterRecord(
                node_name=node_name,
                node_character=(row.get("node_character") or "").strip(),
                display_name=(row.get("display_name") or "").strip(),
                country=(row.get("country") or "").strip(),
                company=(row.get("company") or "").strip(),
                remarks=(row.get("remarks") or "").strip(),
            )
            out[node_name] = rec

    return out


def load_node_character_money_master_csv(
    csv_path: str | Path,
) -> Dict[str, NodeCharacterMoneyMasterRecord]:
    """
    Load node_character money master CSV.

    Required columns:
      - node_character
      - revenue_items
      - variable_cost_items
      - fixed_cost_items
      - inventory_value_items
      - tax_compare_items
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"money master CSV not found: {path}")

    out: Dict[str, NodeCharacterMoneyMasterRecord] = {}

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        first_row_checked = False
        for row in reader:
            if not first_row_checked:
                _require_columns(
                    row,
                    required=[
                        "node_character",
                        "revenue_items",
                        "variable_cost_items",
                        "fixed_cost_items",
                        "inventory_value_items",
                        "tax_compare_items",
                    ],
                    source_name=str(path),
                )
                first_row_checked = True

            node_character = (row.get("node_character") or "").strip()
            if not node_character:
                continue

            rec = NodeCharacterMoneyMasterRecord(
                node_character=node_character,
                revenue_items=_split_items(row.get("revenue_items", "")),
                variable_cost_items=_split_items(row.get("variable_cost_items", "")),
                fixed_cost_items=_split_items(row.get("fixed_cost_items", "")),
                inventory_value_items=_split_items(row.get("inventory_value_items", "")),
                tax_compare_items=_split_items(row.get("tax_compare_items", "")),
            )
            out[node_character] = rec

    return out


def load_money_master_bundle(
    node_master_csv: str | Path,
    node_character_money_master_csv: str | Path,
) -> MoneyMasterBundle:
    """
    Load both CSVs and return a single bundle object.
    """
    node_master = load_node_master_csv(node_master_csv)
    money_master = load_node_character_money_master_csv(
        node_character_money_master_csv
    )
    return MoneyMasterBundle(
        node_master=node_master,
        money_master=money_master,
    )


# ------------------------------------------------------------
# Example usage
# ------------------------------------------------------------

if __name__ == "__main__":
    # Adjust these paths for your local test
    node_csv = "node_master_sample.csv"
    money_csv = "node_character_money_master_sample.csv"

    bundle = load_money_master_bundle(node_csv, money_csv)

    test_node = "supply_point"
    print("node_name:", test_node)
    print("display_name:", bundle.get_display_name(test_node))
    print("node_character:", bundle.get_node_character(test_node))

    mm = bundle.get_money_master_by_node_name(test_node)
    if mm:
        print("inventory_value_items:", mm.inventory_value_items)
        print("tax_compare_items:", mm.tax_compare_items)