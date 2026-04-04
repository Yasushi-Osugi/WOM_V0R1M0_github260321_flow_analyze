#pysi/bridge/dump_rows.py

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


# ============================================================
# WOM PSI slot rule
#   0: Sales
#   1: CarryOver
#   2: Inventory
#   3: Purchase
# ============================================================

SLOT_INDEX_TO_STATE = {
    0: "S",
    1: "CO",
    2: "I",
    3: "P",
}


# ============================================================
# Public API
# ============================================================

def build_dump_rows_from_product_plan_tree(
    *,
    product_name: str,
    direction: str,
    prod_tree_dict_OT: Dict[str, Any],
    prod_tree_dict_IN: Dict[str, Any],
    lot_qty_lookup: Optional[Dict[str, float]] = None,
    sequence_lookup: Optional[Dict[str, str]] = None,
) -> List[dict]:
    """
    product_name と direction に対応する PlanNode tree から
    WOM 実データ対応の dump rows を作る。

    Parameters
    ----------
    product_name:
        対象製品名
    direction:
        "OUT" / "IN" を想定
    prod_tree_dict_OT:
        product_name -> outbound planning tree root
    prod_tree_dict_IN:
        product_name -> inbound planning tree root
    lot_qty_lookup:
        lot_id -> qty の辞書。無ければ qty=1.0 fallback
    sequence_lookup:
        lot_id -> sequence_no の辞書。無ければ lot_id 末尾数字を fallback

    Returns
    -------
    List[dict]
        event_rules.py に渡せる dump rows
    """
    root = _get_product_plan_tree_root(
        product_name=product_name,
        direction=direction,
        prod_tree_dict_OT=prod_tree_dict_OT,
        prod_tree_dict_IN=prod_tree_dict_IN,
    )
    if root is None:
        return []

    nodes = list(_walk_plan_tree(root))

    return build_dump_rows_from_plan_nodes(
        nodes=nodes,
        product_name=product_name,
        direction=direction,
        lot_qty_lookup=lot_qty_lookup,
        sequence_lookup=sequence_lookup,
    )


def build_dump_rows_from_plan_nodes(
    *,
    nodes: Iterable[Any],
    product_name: str,
    direction: str,
    lot_qty_lookup: Optional[Dict[str, float]] = None,
    sequence_lookup: Optional[Dict[str, str]] = None,
) -> List[dict]:
    """
    PlanNode 群の WOM 実データ psi4supply / psi4demand から dump rows を作る。

    実データ前提:
      psi[w][slot_index]
      slot_index:
        0 = Sales
        1 = CarryOver
        2 = Inventory
        3 = Purchase
    """
    rows: List[dict] = []

    lot_qty_lookup = lot_qty_lookup or {}
    sequence_lookup = sequence_lookup or {}

    direction_upper = str(direction).upper()

    for node in nodes:
        node_id = _get_plan_node_id(node)

        psi = _get_plan_node_psi(node, direction_upper=direction_upper)
        if not psi:
            continue

        # psi は week 軸の list/tuple を想定
        for week_idx, week_bucket in enumerate(psi, start=1):
            if not isinstance(week_bucket, (list, tuple)):
                continue

            for slot_index, lot_values in enumerate(week_bucket):
                psi_state = SLOT_INDEX_TO_STATE.get(slot_index)
                if not psi_state:
                    continue

                for lot_id, qty in _iter_lot_entries(
                    lot_values,
                    lot_qty_lookup=lot_qty_lookup,
                ):
                    rows.append(
                        {
                            "lot_id": str(lot_id),
                            "sequence_no": str(
                                sequence_lookup.get(lot_id) or _infer_sequence_no_from_lot_id(lot_id)
                            ),
                            "node_id": str(node_id),
                            "time_bucket": str(week_idx),
                            "psi_state": str(psi_state),
                            "qty": float(qty),
                            "product_id": str(product_name),
                            "payload": {
                                "direction": direction_upper,
                                "slot_index": slot_index,
                                "slot_name": psi_state,
                            },
                        }
                    )

    return rows


# ============================================================
# Tree / node access
# ============================================================

def _get_product_plan_tree_root(
    *,
    product_name: str,
    direction: str,
    prod_tree_dict_OT: Dict[str, Any],
    prod_tree_dict_IN: Dict[str, Any],
) -> Any:
    direction_upper = str(direction).upper()

    if direction_upper in ("OUT", "OT", "OUTBOUND"):
        return prod_tree_dict_OT.get(product_name)

    if direction_upper in ("IN", "INBOUND"):
        return prod_tree_dict_IN.get(product_name)

    return None


def _walk_plan_tree(root: Any) -> Iterable[Any]:
    """
    PlanNode tree を DFS で列挙する。
    """
    stack = [root]
    seen = set()

    while stack:
        node = stack.pop()
        node_key = id(node)
        if node_key in seen:
            continue
        seen.add(node_key)

        yield node

        children = _get_plan_children(node)
        for child in reversed(children):
            stack.append(child)


def _get_plan_children(node: Any) -> List[Any]:
    """
    PlanNode の children を柔らかく取る。
    """
    for attr_name in ("children", "child_nodes"):
        value = getattr(node, attr_name, None)
        if isinstance(value, (list, tuple)):
            return list(value)
        if isinstance(value, dict):
            return list(value.values())
    return []


def _get_plan_node_id(node: Any) -> str:
    """
    PlanNode の識別子。
    基本は name を node_id とみなす。
    """
    for attr_name in ("node_id", "name", "node_name"):
        value = getattr(node, attr_name, None)
        if value is not None:
            return str(value)
    return ""


def _get_plan_node_psi(node: Any, *, direction_upper: str) -> Any:
    """
    WOM 実データ上の PSI 配列を返す。

    OUT 系:
      psi4supply を優先
    IN 系:
      psi4demand を優先

    fallback も少し持たせる。
    """
    if direction_upper in ("OUT", "OT", "OUTBOUND"):
        for attr_name in ("psi4supply", "psi_list", "psi4demand"):
            value = getattr(node, attr_name, None)
            if value is not None:
                return value

    if direction_upper in ("IN", "INBOUND"):
        for attr_name in ("psi4demand", "psi_list", "psi4supply"):
            value = getattr(node, attr_name, None)
            if value is not None:
                return value

    return None


# ============================================================
# Lot entry normalization
# ============================================================

def _iter_lot_entries(
    lot_values: Any,
    *,
    lot_qty_lookup: Dict[str, float],
) -> Iterable[tuple[str, float]]:
    """
    week×slot の箱に入っている値を (lot_id, qty) に正規化する。

    対応形式:
    1. ["LOT_A", "LOT_B"]
    2. [("LOT_A", 100), ("LOT_B", 50)]
    3. {"LOT_A": 100, "LOT_B": 50}
    4. []
    """
    if lot_values is None:
        return []

    # dict[lot_id] = qty
    if isinstance(lot_values, dict):
        out = []
        for lot_id, qty in lot_values.items():
            out.append((str(lot_id), _safe_qty(lot_id, qty, lot_qty_lookup)))
        return out

    # list / tuple
    if isinstance(lot_values, (list, tuple)):
        out = []
        for item in lot_values:
            # pair form
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                lot_id = str(item[0])
                qty = _safe_qty(lot_id, item[1], lot_qty_lookup)
                out.append((lot_id, qty))
            else:
                lot_id = str(item)
                qty = _safe_qty(lot_id, None, lot_qty_lookup)
                out.append((lot_id, qty))
        return out

    return []


def _safe_qty(lot_id: str, qty_value: Any, lot_qty_lookup: Dict[str, float]) -> float:
    if qty_value is not None:
        try:
            return float(qty_value)
        except Exception:
            pass

    if lot_id in lot_qty_lookup:
        try:
            return float(lot_qty_lookup[lot_id])
        except Exception:
            pass

    return 1.0


def _infer_sequence_no_from_lot_id(lot_id: str) -> str:
    """
    sequence_no の最小 fallback。
    bridge が再付番するのではなく、lot_id 末尾数字を拾うだけ。
    """
    tail_digits: List[str] = []
    for ch in reversed(str(lot_id)):
        if ch.isdigit():
            tail_digits.append(ch)
        else:
            break

    if tail_digits:
        return "".join(reversed(tail_digits))

    return ""


# ============================================================
# Tiny smoke test
# ============================================================

if __name__ == "__main__":
    class PlanNode:
        def __init__(self, name, psi4supply=None, psi4demand=None, children=None):
            self.name = name
            self.psi4supply = psi4supply or []
            self.psi4demand = psi4demand or []
            self.children = children or []

    # week1: I に LOT_A
    # week2: CO に LOT_A
    # week3: S に LOT_A
    node_leaf = PlanNode(
        "CS_CAL",
        psi4supply=[
            [[], [], ["CS_CAL-CAL_RICE_1-2024340007"], []],   # w1: S,CO,I,P
            [[], ["CS_CAL-CAL_RICE_1-2024340007"], [], []],   # w2
            [["CS_CAL-CAL_RICE_1-2024340007"], [], [], []],   # w3
        ],
    )
    root = PlanNode("supply_point", children=[node_leaf])

    rows = build_dump_rows_from_plan_nodes(
        nodes=[root, node_leaf],
        product_name="CAL_RICE_1",
        direction="OUT",
    )
    for r in rows:
        print(r)