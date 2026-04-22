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


@dataclass(frozen=True)
class NodeProductMoneyMasterRecord:
    node_name: str
    product_name: str
    inventory_unit_value: float = 0.0
    revenue_unit_value: float = 0.0
    variable_cost_unit_value: float = 0.0
    fixed_cost_weekly: float = 0.0
    currency: str = ""
    remarks: str = ""


@dataclass
class MoneyMasterBundle:
    node_master: Dict[str, NodeMasterRecord]
    money_master: Dict[str, NodeCharacterMoneyMasterRecord]
    node_product_money_master: Dict[tuple[str, str], NodeProductMoneyMasterRecord]

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

    def get_node_product_money(
        self, node_name: str, product_name: str
    ) -> Optional[NodeProductMoneyMasterRecord]:
        return self.node_product_money_master.get((node_name, product_name))

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


def _to_float(value: str) -> float:
    if value is None:
        return 0.0
    s = str(value).strip()
    if not s:
        return 0.0
    return float(s)

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


def load_node_product_money_master_csv(
    csv_path: str | Path,
) -> Dict[tuple[str, str], NodeProductMoneyMasterRecord]:
    """
    Load node_name x product_name money master CSV.

    Required columns:
      - node_name
      - product_name

    Optional columns:
      - inventory_unit_value
      - revenue_unit_value
      - variable_cost_unit_value
      - fixed_cost_weekly
      - currency
      - remarks
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"node product money master CSV not found: {path}")

    out: Dict[tuple[str, str], NodeProductMoneyMasterRecord] = {}

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        first_row_checked = False
        for row in reader:
            if not first_row_checked:
                _require_columns(
                    row,
                    required=["node_name", "product_name"],
                    source_name=str(path),
                )
                first_row_checked = True

            node_name = (row.get("node_name") or "").strip()
            product_name = (row.get("product_name") or "").strip()
            if not node_name or not product_name:
                continue

            rec = NodeProductMoneyMasterRecord(
                node_name=node_name,
                product_name=product_name,
                inventory_unit_value=_to_float(row.get("inventory_unit_value", "")),
                revenue_unit_value=_to_float(row.get("revenue_unit_value", "")),
                variable_cost_unit_value=_to_float(row.get("variable_cost_unit_value", "")),
                fixed_cost_weekly=_to_float(row.get("fixed_cost_weekly", "")),
                currency=(row.get("currency") or "").strip(),
                remarks=(row.get("remarks") or "").strip(),
            )
            out[(node_name, product_name)] = rec

    return out



def load_money_master_bundle(
    node_master_csv: str | Path,
    node_character_money_master_csv: str | Path,
    node_product_money_master_csv: str | Path | None = None,
) -> MoneyMasterBundle:
    """
    Load CSV masters and return a single bundle object.
    """
    node_master = load_node_master_csv(node_master_csv)
    money_master = load_node_character_money_master_csv(
        node_character_money_master_csv
    )

    node_product_money_master: Dict[tuple[str, str], NodeProductMoneyMasterRecord] = {}
    if node_product_money_master_csv:
        node_product_money_master = load_node_product_money_master_csv(
            node_product_money_master_csv
        )

    return MoneyMasterBundle(
        node_master=node_master,
        money_master=money_master,
        node_product_money_master=node_product_money_master,
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