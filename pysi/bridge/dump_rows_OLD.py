#pysi/bridge/dump_rows.py

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


PSI_STATE_ORDER = ("P", "I", "CO", "S")


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
    event inference 用 dump rows を作る。

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
        lot_qty_lookup=lot_qty_lookup,
        sequence_lookup=sequence_lookup,
    )


def build_dump_rows_from_plan_nodes(
    *,
    nodes: Iterable[Any],
    lot_qty_lookup: Optional[Dict[str, float]] = None,
    sequence_lookup: Optional[Dict[str, str]] = None,
) -> List[dict]:
    """
    PlanNode 群の psi list から dump rows を作る。
    """
    rows: List[dict] = []

    lot_qty_lookup = lot_qty_lookup or {}
    sequence_lookup = sequence_lookup or {}

    for node in nodes:
        node_id = _get_plan_node_id(node)
        product_id = _get_plan_node_product_id(node)

        psi_list = _get_plan_node_psi_list(node)
        if not psi_list:
            continue

        for psi_state in PSI_STATE_ORDER:
            week_map = _get_week_map(psi_list, psi_state)
            if not week_map:
                continue

            for week_no, lot_values in week_map.items():
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
                            "time_bucket": str(week_no),
                            "psi_state": str(psi_state),
                            "qty": float(qty),
                            "product_id": str(product_id),
                            "payload": {},
                        }
                    )

    return rows


def _get_product_plan_tree_root(
    *,
    product_name: str,
    direction: str,
    prod_tree_dict_OT: Dict[str, Any],
    prod_tree_dict_IN: Dict[str, Any],
) -> Any:
    """
    product_name と direction から planning tree root を返す。
    """
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


def _get_plan_node_product_id(node: Any) -> str:
    """
    PlanNode 側に product_id があれば使い、無ければ空。
    """
    for attr_name in ("product_id", "sku", "item_id"):
        value = getattr(node, attr_name, None)
        if value is not None:
            return str(value)
    return ""


def _get_plan_node_psi_list(node: Any) -> Any:
    """
    PlanNode が持つ PSI list を返す。
    候補名を複数許容する。
    """
    for attr_name in ("psi_list", "psi4supply", "psi4demand"):
        value = getattr(node, attr_name, None)
        if value is not None:
            return value
    return None


def _get_week_map(psi_list: Any, psi_state: str) -> Dict[Any, Any]:
    """
    psi_list["I"] -> {177: [...], 178: [...]}
    のような week map を返す。
    """
    if isinstance(psi_list, dict):
        value = psi_list.get(psi_state, {})
        if isinstance(value, dict):
            return value
    return {}


def _iter_lot_entries(
    lot_values: Any,
    *,
    lot_qty_lookup: Dict[str, float],
) -> Iterable[tuple[str, float]]:
    """
    week×state の箱に入っている値を (lot_id, qty) へ正規化する。

    対応:
    1. ["LOT_A", "LOT_B"]
    2. [("LOT_A", 100), ("LOT_B", 50)]
    3. {"LOT_A": 100, "LOT_B": 50}
    """
    if lot_values is None:
        return []

    if isinstance(lot_values, dict):
        out = []
        for lot_id, qty in lot_values.items():
            out.append((str(lot_id), _safe_qty(lot_id, qty, lot_qty_lookup)))
        return out

    if isinstance(lot_values, (list, tuple)):
        out = []
        for item in lot_values:
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
