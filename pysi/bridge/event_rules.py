#pysi/bridge/event_rules.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple


# ------------------------------------------------------------
# Type aliases
# ------------------------------------------------------------

Row = Dict[str, Any]
NodeChar = Dict[str, Any]
GraphEdges = set[Tuple[str, str]]


# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------

PSI_STATE_ORDER = {
    "P": 10,
    "I": 20,
    "CO": 30,
    "S": 40,
}


# ------------------------------------------------------------
# Event model (minimal canonical event)
# ------------------------------------------------------------

@dataclass(frozen=True)
class CanonicalEvent:
    event_type: str
    lot_id: str
    node_id: str
    time_bucket: str
    from_node_id: Optional[str] = None
    to_node_id: Optional[str] = None
    prev_state: Optional[str] = None
    curr_state: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


# ------------------------------------------------------------
# Small helpers
# ------------------------------------------------------------

def safe_str(v: Any) -> str:
    return "" if v is None else str(v)


def get_row_lot_id(row: Row) -> str:
    return safe_str(row.get("lot_id"))


def get_row_node_id(row: Row) -> str:
    return safe_str(row.get("node_id"))


def get_row_time_bucket(row: Row) -> str:
    # "week_no" と "time_bucket" の両方に対応
    if "time_bucket" in row:
        return safe_str(row.get("time_bucket"))
    return safe_str(row.get("week_no"))


def get_row_state(row: Row) -> str:
    # "psi_state" を基本にしつつ、他名でも拾える余地を残す
    if "psi_state" in row:
        return safe_str(row.get("psi_state"))
    if "psi_slot" in row:
        return safe_str(row.get("psi_slot"))
    return ""


def get_state_rank(state: str) -> int:
    return PSI_STATE_ORDER.get(state, 999)


def build_edge(prev_row: Row, curr_row: Row) -> Tuple[str, str]:
    return (get_row_node_id(prev_row), get_row_node_id(curr_row))


def is_same_node(prev_row: Row, curr_row: Row) -> bool:
    return get_row_node_id(prev_row) == get_row_node_id(curr_row)


def is_same_state(prev_row: Row, curr_row: Row) -> bool:
    return get_row_state(prev_row) == get_row_state(curr_row)


def is_pull_allocation_node(node_char: NodeChar) -> bool:
    return bool(node_char.get("is_decoupling_point")) and bool(node_char.get("can_allocate"))


def is_sales_node(node_char: NodeChar) -> bool:
    return bool(node_char.get("can_sell"))


def is_shipping_node(node_char: NodeChar) -> bool:
    return bool(node_char.get("can_ship")) and not bool(node_char.get("can_sell"))


def make_event(
    event_type: str,
    prev_row: Row,
    curr_row: Row,
    *,
    from_node_id: Optional[str] = None,
    to_node_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> CanonicalEvent:
    return CanonicalEvent(
        event_type=event_type,
        lot_id=get_row_lot_id(curr_row) or get_row_lot_id(prev_row),
        node_id=get_row_node_id(curr_row) or get_row_node_id(prev_row),
        time_bucket=get_row_time_bucket(curr_row) or get_row_time_bucket(prev_row),
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        prev_state=get_row_state(prev_row),
        curr_state=get_row_state(curr_row),
        payload=payload or {},
    )


# ------------------------------------------------------------
# Core inference
# ------------------------------------------------------------

def infer_events_from_row_pair(
    prev_row: Row,
    curr_row: Row,
    prev_char: NodeChar,
    curr_char: NodeChar,
    graph_edges: GraphEdges,
) -> List[CanonicalEvent]:
    """
    同一 lot の連続した 2 row から canonical events を推定する。
    判定の土台は row 差分、Node Character は意味づけの触媒。
    """
    events: List[CanonicalEvent] = []

    prev_node = get_row_node_id(prev_row)
    curr_node = get_row_node_id(curr_row)
    prev_state = get_row_state(prev_row)
    curr_state = get_row_state(curr_row)

    # --------------------------------------------------------
    # 0) node change
    # --------------------------------------------------------
    if prev_node != curr_node:
        edge = (prev_node, curr_node)

        if edge not in graph_edges:
            events.append(
                make_event(
                    "lot_transition_unmapped_edge",
                    prev_row,
                    curr_row,
                    from_node_id=prev_node,
                    to_node_id=curr_node,
                    payload={"edge_pair": edge},
                )
            )
            return events

        # departure-side meaning
        if prev_state in ("CO", "S") and prev_char.get("can_ship"):
            events.append(
                make_event(
                    "lot_shipped",
                    prev_row,
                    curr_row,
                    from_node_id=prev_node,
                    to_node_id=curr_node,
                )
            )

        # main transit
        events.append(
            make_event(
                "lot_transit_node_to_node",
                prev_row,
                curr_row,
                from_node_id=prev_node,
                to_node_id=curr_node,
                payload={"edge_pair": edge},
            )
        )

        # arrival-side meaning
        if curr_char.get("is_decoupling_point") and curr_state == "I":
            events.append(
                make_event(
                    "lot_arrived_at_decoupling_stock",
                    prev_row,
                    curr_row,
                    from_node_id=prev_node,
                    to_node_id=curr_node,
                )
            )

        if curr_char.get("can_allocate") and curr_state in ("I", "CO"):
            events.append(
                make_event(
                    "lot_arrived_for_allocation",
                    prev_row,
                    curr_row,
                    from_node_id=prev_node,
                    to_node_id=curr_node,
                )
            )

        if curr_char.get("can_store") and curr_state == "I":
            events.append(
                make_event(
                    "lot_arrived_into_inventory",
                    prev_row,
                    curr_row,
                    from_node_id=prev_node,
                    to_node_id=curr_node,
                )
            )

        if curr_char.get("can_sell") and curr_state == "S":
            events.append(
                make_event(
                    "lot_customer_delivery",
                    prev_row,
                    curr_row,
                    from_node_id=prev_node,
                    to_node_id=curr_node,
                )
            )

        return events

    # --------------------------------------------------------
    # 1) same node, no state change
    # --------------------------------------------------------
    if prev_state == curr_state:
        return events

    # --------------------------------------------------------
    # 2) P -> I
    # --------------------------------------------------------
    if prev_state == "P" and curr_state == "I":
        if curr_char.get("can_produce"):
            events.append(make_event("lot_production_completed", prev_row, curr_row))
        elif curr_char.get("can_purchase") and not curr_char.get("can_produce"):
            events.append(make_event("lot_procurement_received", prev_row, curr_row))
        else:
            events.append(make_event("lot_moved_to_inventory", prev_row, curr_row))
        return events

    # --------------------------------------------------------
    # 3) I -> CO
    # --------------------------------------------------------
    if prev_state == "I" and curr_state == "CO":
        if curr_char.get("is_decoupling_point") and curr_char.get("can_allocate"):
            events.append(make_event("lot_pulled_by_demand", prev_row, curr_row))
            events.append(make_event("lot_allocated", prev_row, curr_row))
        elif curr_char.get("is_decoupling_point"):
            events.append(make_event("demand_bound_to_lot", prev_row, curr_row))
        elif curr_char.get("can_sell"):
            events.append(make_event("lot_sales_committed", prev_row, curr_row))
        elif curr_char.get("can_ship"):
            events.append(make_event("lot_ship_committed", prev_row, curr_row))
        elif curr_char.get("can_allocate"):
            events.append(make_event("lot_allocated", prev_row, curr_row))
        else:
            events.append(make_event("lot_committed_at_node", prev_row, curr_row))
        return events

    # --------------------------------------------------------
    # 4) CO -> S
    # --------------------------------------------------------
    if prev_state == "CO" and curr_state == "S":
        if curr_char.get("can_sell"):
            events.append(make_event("lot_sold", prev_row, curr_row))
        elif curr_char.get("can_ship"):
            events.append(make_event("lot_shipped", prev_row, curr_row))
        else:
            events.append(make_event("lot_released_from_node", prev_row, curr_row))
        return events

    # --------------------------------------------------------
    # 5) I -> S
    # --------------------------------------------------------
    if prev_state == "I" and curr_state == "S":
        if curr_char.get("can_sell"):
            events.append(make_event("lot_sold", prev_row, curr_row))
        elif curr_char.get("can_ship"):
            events.append(make_event("lot_shipped", prev_row, curr_row))
        else:
            events.append(make_event("lot_released_from_node", prev_row, curr_row))
        return events

    # --------------------------------------------------------
    # 6) fallback
    # --------------------------------------------------------
    events.append(make_event("lot_state_changed_unclassified", prev_row, curr_row))
    return events


# ------------------------------------------------------------
# Sort / sequence helpers
# ------------------------------------------------------------

def canonical_sort_key(row: Row) -> Tuple[str, str, int, int, str]:
    """
    bridge 内で同一 lot の row を自然順に並べるための最小 sort key。
    ここでの sequence は LOT の出生 sequence を再付番するものではなく、
    dump row を解釈しやすく並べるための順序キー。
    """
    lot_id = get_row_lot_id(row)
    origin_seq = safe_str(row.get("sequence_no") or row.get("lot_birth_seq") or "")
    tb_str = get_row_time_bucket(row)
    try:
        tb = int(tb_str)
    except Exception:
        tb = 0
    state_rank = get_state_rank(get_row_state(row))
    node_id = get_row_node_id(row)
    return (lot_id, origin_seq, tb, state_rank, node_id)


def sort_rows_for_event_inference(rows: Sequence[Row]) -> List[Row]:
    return sorted(rows, key=canonical_sort_key)


# ------------------------------------------------------------
# Public batch API
# ------------------------------------------------------------

def infer_events_for_lot_rows(
    rows: Sequence[Row],
    node_char_by_node_id: Dict[str, NodeChar],
    graph_edges: GraphEdges,
) -> List[CanonicalEvent]:
    """
    同一 lot の複数 row から event をまとめて推定する。
    """
    sorted_rows = sort_rows_for_event_inference(rows)
    events: List[CanonicalEvent] = []

    if len(sorted_rows) < 2:
        return events

    for prev_row, curr_row in zip(sorted_rows[:-1], sorted_rows[1:]):
        prev_node = get_row_node_id(prev_row)
        curr_node = get_row_node_id(curr_row)

        prev_char = node_char_by_node_id.get(prev_node, {})
        curr_char = node_char_by_node_id.get(curr_node, {})

        pair_events = infer_events_from_row_pair(
            prev_row=prev_row,
            curr_row=curr_row,
            prev_char=prev_char,
            curr_char=curr_char,
            graph_edges=graph_edges,
        )
        events.extend(pair_events)

    return events


# ------------------------------------------------------------
# Tiny example / smoke test
# ------------------------------------------------------------

if __name__ == "__main__":
    graph_edges: GraphEdges = {
        ("supply_point", "DADCAL"),
        ("DADCAL", "WS2CAL"),
        ("WS2CAL", "RT_CAL"),
        ("RT_CAL", "CS_CAL"),
    }

    node_char_by_node_id: Dict[str, NodeChar] = {
        "supply_point": {
            "node_role": "supplier",
            "can_purchase": True,
            "can_store": True,
            "can_ship": True,
        },
        "DADCAL": {
            "node_role": "dc",
            "can_store": True,
            "can_ship": True,
            "can_allocate": True,
            "is_decoupling_point": True,
        },
        "WS2CAL": {
            "node_role": "warehouse",
            "can_store": True,
            "can_ship": True,
        },
        "RT_CAL": {
            "node_role": "retail",
            "can_store": True,
            "can_sell": True,
        },
        "CS_CAL": {
            "node_role": "consumer",
            "can_store": True,
            "can_sell": True,
        },
    }

    rows = [
        {"lot_id": "CS_CAL-CAL_RICE_1-2024340007", "sequence_no": "0007", "time_bucket": "177", "node_id": "supply_point", "psi_state": "I"},
        {"lot_id": "CS_CAL-CAL_RICE_1-2024340007", "sequence_no": "0007", "time_bucket": "178", "node_id": "DADCAL", "psi_state": "I"},
        {"lot_id": "CS_CAL-CAL_RICE_1-2024340007", "sequence_no": "0007", "time_bucket": "179", "node_id": "DADCAL", "psi_state": "CO"},
        {"lot_id": "CS_CAL-CAL_RICE_1-2024340007", "sequence_no": "0007", "time_bucket": "180", "node_id": "WS2CAL", "psi_state": "I"},
    ]

    inferred = infer_events_for_lot_rows(
        rows=rows,
        node_char_by_node_id=node_char_by_node_id,
        graph_edges=graph_edges,
    )

    for ev in inferred:
        print(ev)


def canonical_event_to_trace_dict(event: CanonicalEvent, sequence_no: int) -> dict:
    payload = dict(event.payload or {})
    payload.update({
        "from_node_id": event.from_node_id,
        "to_node_id": event.to_node_id,
        "prev_state": event.prev_state,
        "curr_state": event.curr_state,
    })
    return {
        "sequence_no": sequence_no,
        "event_type": event.event_type,
        "node_id": event.node_id,
        "lot_id": event.lot_id,
        "time_bucket": event.time_bucket,
        "payload": payload,
    }


#@STOP
#def canonical_events_to_trace_dicts(events, start_sequence_no: int = 1) -> list[dict]:
#    return [
#        canonical_event_to_trace_dict(event, sequence_no=i)
#        for i, event in enumerate(events, start=start_sequence_no)
#    ]

def canonical_events_to_trace_dicts(
    events: Sequence[CanonicalEvent],
    start_sequence_no: int = 1,
) -> List[dict]:
    return [
        canonical_event_to_trace_dict(event, sequence_no=i)
        for i, event in enumerate(events, start=start_sequence_no)
    ]



