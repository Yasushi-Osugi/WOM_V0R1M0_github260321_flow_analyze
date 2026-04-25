from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class NodeMasterRecord:
    node_name: str
    node_character: str
    display_name: str = ""
    country: str = ""
    company: str = ""
    currency: str = ""
    remarks: str = ""


@dataclass(frozen=True)
class NodeCharacterPolicyRecord:
    node_character: str
    default_inventory_carrying_rate: float = 0.0
    default_target_profit_margin: float = 0.0
    default_tax_rate: float = 0.0
    default_fixed_cost_basis: str = ""
    remarks: str = ""

    # backward-compatible item-list semantics used by legacy money-master model
    @property
    def revenue_items(self) -> List[str]:
        return []

    @property
    def variable_cost_items(self) -> List[str]:
        return []

    @property
    def fixed_cost_items(self) -> List[str]:
        return []

    @property
    def inventory_value_items(self) -> List[str]:
        return []

    @property
    def tax_compare_items(self) -> List[str]:
        return []


@dataclass(frozen=True)
class EdgeProductMoneyRecord:
    from_node: str
    to_node: str
    product_name: str
    transfer_price_per_lot: float = 0.0
    freight_cost_per_lot: float = 0.0
    insurance_cost_per_lot: float = 0.0
    duty_cost_per_lot: float = 0.0
    handling_cost_per_lot: float = 0.0
    incoterm: str = ""
    currency: str = ""
    effective_from_week: str = ""
    effective_to_week: str = ""
    remarks: str = ""


@dataclass(frozen=True)
class NodeProductMoneyMasterRecord:
    node_name: str
    product_name: str
    purchase_cost_per_lot: float = 0.0
    ship_price_per_lot: float = 0.0
    inventory_unit_value_per_lot: float = 0.0
    variable_cost_per_lot: float = 0.0
    fixed_cost_per_week: float = 0.0
    tax_rate: float = 0.0
    currency: str = ""
    effective_from_week: str = ""
    effective_to_week: str = ""
    remarks: str = ""

    @property
    def inventory_unit_value(self) -> float:
        return self.inventory_unit_value_per_lot

    @property
    def revenue_unit_value(self) -> float:
        return self.ship_price_per_lot

    @property
    def variable_cost_unit_value(self) -> float:
        return self.variable_cost_per_lot

    @property
    def fixed_cost_weekly(self) -> float:
        return self.fixed_cost_per_week


@dataclass(frozen=True)
class ValuationPolicyRecord:
    product_name: str
    inventory_valuation_method: str = ""
    issue_cost_method: str = ""
    inventory_carrying_rate: float = 0.0
    obsolescence_rate: float = 0.0
    price_propagation_method: str = ""
    remarks: str = ""


@dataclass
class MoneyMasterBundle:
    node_master: Dict[str, NodeMasterRecord]
    node_character_policy_master: Dict[str, NodeCharacterPolicyRecord]
    edge_product_money_master: Dict[tuple[str, str, str], EdgeProductMoneyRecord]
    node_product_money_master: Dict[tuple[str, str], NodeProductMoneyMasterRecord]
    valuation_policy_master: Dict[str, ValuationPolicyRecord]

    def get_node(self, node_name: str) -> Optional[NodeMasterRecord]:
        return self.node_master.get(node_name)

    def get_node_character(self, node_name: str) -> Optional[str]:
        rec = self.get_node(node_name)
        return rec.node_character if rec else None

    def get_display_name(self, node_name: str) -> str:
        rec = self.get_node(node_name)
        return rec.display_name if rec and rec.display_name else node_name

    # backward compatibility
    def get_money_master_by_node_name(self, node_name: str) -> Optional[NodeCharacterPolicyRecord]:
        node_character = self.get_node_character(node_name)
        if not node_character:
            return None
        return self.node_character_policy_master.get(node_character)

    def get_money_master_by_node_character(self, node_character: str) -> Optional[NodeCharacterPolicyRecord]:
        return self.node_character_policy_master.get(node_character)

    def get_node_character_policy(self, node_character: str) -> Optional[NodeCharacterPolicyRecord]:
        return self.node_character_policy_master.get(node_character)

    def get_node_product_money(self, node_name: str, product_name: str) -> Optional[NodeProductMoneyMasterRecord]:
        return self.node_product_money_master.get((node_name, product_name))

    def get_edge_product_money(self, from_node: str, to_node: str, product_name: str) -> Optional[EdgeProductMoneyRecord]:
        return self.edge_product_money_master.get((from_node, to_node, product_name))

    def get_valuation_policy(self, product_name: str) -> Optional[ValuationPolicyRecord]:
        return self.valuation_policy_master.get(product_name)


def _require_columns(fieldnames: List[str], required: List[str], source_name: str) -> None:
    missing = [col for col in required if col not in set(fieldnames)]
    if missing:
        raise ValueError(f"{source_name}: missing required columns: {', '.join(missing)}")


def _to_float(value: str) -> float:
    if value is None:
        return 0.0
    s = str(value).strip()
    if not s:
        return 0.0
    return float(s)


def load_node_master_csv(csv_path: str | Path) -> Dict[str, NodeMasterRecord]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"node master CSV not found: {path}")

    out: Dict[str, NodeMasterRecord] = {}
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        _require_columns(reader.fieldnames or [], ["node_name", "node_character"], str(path))
        for row in reader:
            node_name = (row.get("node_name") or "").strip()
            if not node_name:
                continue
            out[node_name] = NodeMasterRecord(
                node_name=node_name,
                node_character=(row.get("node_character") or "").strip(),
                display_name=(row.get("display_name") or "").strip(),
                country=(row.get("country") or "").strip(),
                company=(row.get("company") or "").strip(),
                currency=(row.get("currency") or "").strip(),
                remarks=(row.get("remarks") or "").strip(),
            )
    return out


def load_node_character_policy_master_csv(csv_path: str | Path) -> Dict[str, NodeCharacterPolicyRecord]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"node character policy master CSV not found: {path}")

    out: Dict[str, NodeCharacterPolicyRecord] = {}
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        _require_columns(reader.fieldnames or [], ["node_character"], str(path))
        for row in reader:
            node_character = (row.get("node_character") or "").strip()
            if not node_character:
                continue
            out[node_character] = NodeCharacterPolicyRecord(
                node_character=node_character,
                default_inventory_carrying_rate=_to_float(row.get("default_inventory_carrying_rate", "")),
                default_target_profit_margin=_to_float(row.get("default_target_profit_margin", "")),
                default_tax_rate=_to_float(row.get("default_tax_rate", "")),
                default_fixed_cost_basis=(row.get("default_fixed_cost_basis") or "").strip(),
                remarks=(row.get("remarks") or "").strip(),
            )
    return out


def load_edge_product_money_master_csv(csv_path: str | Path) -> Dict[tuple[str, str, str], EdgeProductMoneyRecord]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"edge product money master CSV not found: {path}")

    out: Dict[tuple[str, str, str], EdgeProductMoneyRecord] = {}
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        _require_columns(reader.fieldnames or [], ["from_node", "to_node", "product_name"], str(path))
        for row in reader:
            from_node = (row.get("from_node") or "").strip()
            to_node = (row.get("to_node") or "").strip()
            product_name = (row.get("product_name") or "").strip()
            if not from_node or not to_node or not product_name:
                continue
            key = (from_node, to_node, product_name)
            out[key] = EdgeProductMoneyRecord(
                from_node=from_node,
                to_node=to_node,
                product_name=product_name,
                transfer_price_per_lot=_to_float(row.get("transfer_price_per_lot", "")),
                freight_cost_per_lot=_to_float(row.get("freight_cost_per_lot", "")),
                insurance_cost_per_lot=_to_float(row.get("insurance_cost_per_lot", "")),
                duty_cost_per_lot=_to_float(row.get("duty_cost_per_lot", "")),
                handling_cost_per_lot=_to_float(row.get("handling_cost_per_lot", "")),
                incoterm=(row.get("incoterm") or "").strip(),
                currency=(row.get("currency") or "").strip(),
                effective_from_week=(row.get("effective_from_week") or "").strip(),
                effective_to_week=(row.get("effective_to_week") or "").strip(),
                remarks=(row.get("remarks") or "").strip(),
            )
    return out


def load_node_product_money_master_csv(csv_path: str | Path) -> Dict[tuple[str, str], NodeProductMoneyMasterRecord]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"node product money master CSV not found: {path}")

    out: Dict[tuple[str, str], NodeProductMoneyMasterRecord] = {}
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        _require_columns(reader.fieldnames or [], ["node_name", "product_name"], str(path))
        for row in reader:
            node_name = (row.get("node_name") or "").strip()
            product_name = (row.get("product_name") or "").strip()
            if not node_name or not product_name:
                continue
            out[(node_name, product_name)] = NodeProductMoneyMasterRecord(
                node_name=node_name,
                product_name=product_name,
                purchase_cost_per_lot=_to_float(row.get("purchase_cost_per_lot", "")),
                ship_price_per_lot=_to_float(row.get("ship_price_per_lot", row.get("revenue_unit_value", ""))),
                inventory_unit_value_per_lot=_to_float(row.get("inventory_unit_value_per_lot", row.get("inventory_unit_value", ""))),
                variable_cost_per_lot=_to_float(row.get("variable_cost_per_lot", row.get("variable_cost_unit_value", ""))),
                fixed_cost_per_week=_to_float(row.get("fixed_cost_per_week", row.get("fixed_cost_weekly", ""))),
                tax_rate=_to_float(row.get("tax_rate", "")),
                currency=(row.get("currency") or "").strip(),
                effective_from_week=(row.get("effective_from_week") or "").strip(),
                effective_to_week=(row.get("effective_to_week") or "").strip(),
                remarks=(row.get("remarks") or "").strip(),
            )
    return out


def load_valuation_policy_master_csv(csv_path: str | Path) -> Dict[str, ValuationPolicyRecord]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"valuation policy master CSV not found: {path}")

    out: Dict[str, ValuationPolicyRecord] = {}
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        _require_columns(reader.fieldnames or [], ["product_name"], str(path))
        for row in reader:
            product_name = (row.get("product_name") or "").strip()
            if not product_name:
                continue
            out[product_name] = ValuationPolicyRecord(
                product_name=product_name,
                inventory_valuation_method=(row.get("inventory_valuation_method") or "").strip(),
                issue_cost_method=(row.get("issue_cost_method") or "").strip(),
                inventory_carrying_rate=_to_float(row.get("inventory_carrying_rate", "")),
                obsolescence_rate=_to_float(row.get("obsolescence_rate", "")),
                price_propagation_method=(row.get("price_propagation_method") or "").strip(),
                remarks=(row.get("remarks") or "").strip(),
            )
    return out


def _load_optional(loader, csv_path: str | Path | None):
    if not csv_path:
        return {}
    p = Path(csv_path)
    if not p.exists():
        return {}
    try:
        return loader(p)
    except Exception:
        return {}


def load_money_master_bundle(
    node_master_csv: str | Path,
    node_character_money_master_csv: str | Path | None = None,
    node_product_money_master_csv: str | Path | None = None,
    *,
    node_character_policy_master_csv: str | Path | None = None,
    edge_product_money_master_csv: str | Path | None = None,
    valuation_policy_master_csv: str | Path | None = None,
) -> MoneyMasterBundle:
    node_master = load_node_master_csv(node_master_csv)

    policy_path = node_character_policy_master_csv or node_character_money_master_csv
    node_character_policy_master = _load_optional(load_node_character_policy_master_csv, policy_path)

    node_product_money_master = _load_optional(load_node_product_money_master_csv, node_product_money_master_csv)
    edge_product_money_master = _load_optional(load_edge_product_money_master_csv, edge_product_money_master_csv)
    valuation_policy_master = _load_optional(load_valuation_policy_master_csv, valuation_policy_master_csv)

    return MoneyMasterBundle(
        node_master=node_master,
        node_character_policy_master=node_character_policy_master,
        edge_product_money_master=edge_product_money_master,
        node_product_money_master=node_product_money_master,
        valuation_policy_master=valuation_policy_master,
    )
