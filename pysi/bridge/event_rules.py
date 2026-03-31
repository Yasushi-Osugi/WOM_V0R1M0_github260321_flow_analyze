#pysi/bridge/event_rules.py

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from pysi.bridge.canonical_events import (
    BusinessEventType,
    CanonicalEventRecord,
    CanonicalEventType,
    canonical_event_record_to_trace_dict,
    make_i_to_s_event,
    make_p_to_i_event,
    make_s_to_next_p_event,
)
from pysi.bridge.consumer_events import (
    MomentOfTruthEvent,
    MomentOfTruthType,
)
from pysi.bridge.consumer_state_repository import ConsumerStateRepository
from pysi.bridge.consumer_experience_input import (
    ConsumerExperienceInput,
    load_consumer_experience_inputs,
    lookup_consumer_experience,
)


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
# Module-level repositories / caches
# ------------------------------------------------------------

_CONSUMER_STATE_REPO = ConsumerStateRepository()
_CONSUMER_EXPERIENCE_INPUTS: Dict[Tuple[str, str, str, str], ConsumerExperienceInput] = {}


# ------------------------------------------------------------
# Initialization helper
# ------------------------------------------------------------

def initialize_consumer_experience_inputs(csv_path: str) -> None:
    """
    consumer_experience_input.csv を読み込み、module-level cache に保持する。
    """
    global _CONSUMER_EXPERIENCE_INPUTS
    _CONSUMER_EXPERIENCE_INPUTS = load_consumer_experience_inputs(csv_path)
    print("[trace] consumer experience inputs loaded:", len(_CONSUMER_EXPERIENCE_INPUTS))


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
    if "time_bucket" in row:
        return safe_str(row.get("time_bucket"))
    return safe_str(row.get("week_no"))


def get_row_state(row: Row) -> str:
    if "psi_state" in row:
        return safe_str(row.get("psi_state"))
    if "psi_slot" in row:
        return safe_str(row.get("psi_slot"))
    return ""


def get_row_product_id(row: Row) -> str:
    return safe_str(row.get("product_id"))


def get_state_rank(state: str) -> int:
    return PSI_STATE_ORDER.get(state, 999)


def build_edge(prev_row: Row, curr_row: Row) -> Tuple[str, str]:
    return (get_row_node_id(prev_row), get_row_node_id(curr_row))


def is_pull_allocation_node(node_char: NodeChar) -> bool:
    return bool(node_char.get("is_decoupling_point")) and bool(node_char.get("can_allocate"))


def is_sales_node(node_char: NodeChar) -> bool:
    return bool(node_char.get("can_sell"))


def is_shipping_node(node_char: NodeChar) -> bool:
    return bool(node_char.get("can_ship")) and not bool(node_char.get("can_sell"))


def is_consumer_node(node_char: NodeChar) -> bool:
    return safe_str(node_char.get("node_role")).lower() == "consumer"


# ------------------------------------------------------------
# Consumer MOT helper
# ------------------------------------------------------------

def _build_consumer_mot_event(curr_row: Row, curr_char: NodeChar) -> MomentOfTruthEvent:
    """
    consumer node の I->S に対して Moment of Truth event を生成する。

    優先順位:
    1) consumer_experience_input.csv の観測入力
    2) fallback として value_expectation_met / score_delta=0.2
    """
    consumer_node_id = get_row_node_id(curr_row)
    product_id = get_row_product_id(curr_row)
    time_bucket = get_row_time_bucket(curr_row)
    lot_id = get_row_lot_id(curr_row)

    exp = lookup_consumer_experience(
        _CONSUMER_EXPERIENCE_INPUTS,
        lot_id=lot_id,
        consumer_node_id=consumer_node_id,
        product_id=product_id,
        time_bucket=time_bucket,
    )

    # fallback: 入力が無い場合は従来どおり
    if exp is None:
        return MomentOfTruthEvent(
            event_type=MomentOfTruthType.VALUE_EXPECTATION_MET,
            consumer_node_id=consumer_node_id,
            product_id=product_id,
            time_bucket=time_bucket,
            lot_id=lot_id,
            score_delta=0.2,
            payload={
                "source": "event_rules.consumer.I_TO_S.fallback",
                "node_role": curr_char.get("node_role"),
            },
        )

    # 1) stockout
    if exp.availability_ok == 0:
        event_type = MomentOfTruthType.STOCKOUT_EXPERIENCED
        score_delta = -1.0

    # 2) price resistance
    elif exp.reference_price > 0 and exp.price_paid > exp.reference_price * 1.1:
        event_type = MomentOfTruthType.PRICE_RESISTANCE_FELT
        score_delta = -0.4

    # 3) negative experience
    elif exp.quality_score < 2.5 or exp.complaint_flag == 1:
        event_type = MomentOfTruthType.EXPERIENCE_NEGATIVE
        score_delta = -0.8

    # 4) expectation met
    else:
        event_type = MomentOfTruthType.VALUE_EXPECTATION_MET
        score_delta = 0.2

    return MomentOfTruthEvent(
        event_type=event_type,
        consumer_node_id=consumer_node_id,
        product_id=product_id,
        time_bucket=time_bucket,
        lot_id=lot_id,
        score_delta=score_delta,
        payload={
            "source": "consumer_experience_input.csv",
            "availability_ok": exp.availability_ok,
            "price_paid": exp.price_paid,
            "reference_price": exp.reference_price,
            "quality_score": exp.quality_score,
            "complaint_flag": exp.complaint_flag,
            "node_role": curr_char.get("node_role"),
        },
    )


# ------------------------------------------------------------
# Compatibility wrapper:
# old make_event() API -> CanonicalEventRecord
# ------------------------------------------------------------

def make_event(
    event_type: str,
    prev_row: Row,
    curr_row: Row,
    *,
    from_node_id: Optional[str] = None,
    to_node_id: Optional[str] = None,
    business_event: Optional[BusinessEventType] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> CanonicalEventRecord:
    """
    旧 make_event API を保ちながら、
    内部では CanonicalEventRecord を返す互換ラッパー。
    """
    prev_state = get_row_state(prev_row)
    curr_state = get_row_state(curr_row)

    lot_id = get_row_lot_id(curr_row) or get_row_lot_id(prev_row)
    node_id = get_row_node_id(curr_row) or get_row_node_id(prev_row)
    time_bucket = get_row_time_bucket(curr_row) or get_row_time_bucket(prev_row)
    product_id = get_row_product_id(curr_row) or get_row_product_id(prev_row)

    payload = payload or {}

    # --------------------------------------------------------
    # 1) cross-node S -> next P
    # --------------------------------------------------------
    if from_node_id and to_node_id and prev_state == "S" and curr_state == "P":
        return make_s_to_next_p_event(
            lot_id=lot_id,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            time_bucket=time_bucket,
            operational_event_type=event_type,
            business_event=business_event,
            prev_state=prev_state,
            curr_state=curr_state,
            product_id=product_id,
            payload=payload,
        )

    # --------------------------------------------------------
    # 2) same-node P -> I
    # --------------------------------------------------------
    if prev_state == "P" and curr_state == "I":
        return make_p_to_i_event(
            lot_id=lot_id,
            node_id=node_id,
            time_bucket=time_bucket,
            operational_event_type=event_type,
            business_event=business_event,
            prev_state=prev_state,
            curr_state=curr_state,
            product_id=product_id,
            payload=payload,
        )

    # --------------------------------------------------------
    # 3) same-node I -> S / CO -> S
    # --------------------------------------------------------
    if (prev_state == "I" and curr_state == "S") or (prev_state == "CO" and curr_state == "S"):
        return make_i_to_s_event(
            lot_id=lot_id,
            node_id=node_id,
            time_bucket=time_bucket,
            operational_event_type=event_type,
            business_event=business_event,
            prev_state=prev_state,
            curr_state=curr_state,
            product_id=product_id,
            payload=payload,
        )

    # --------------------------------------------------------
    # 4) fallback
    # --------------------------------------------------------
    canonical_event = (
        CanonicalEventType.S_TO_NEXT_P
        if (from_node_id and to_node_id)
        else CanonicalEventType.I_TO_S
    )

    return CanonicalEventRecord(
        canonical_event=canonical_event,
        lot_id=lot_id,
        node_id=node_id,
        time_bucket=time_bucket,
        operational_event_type=event_type,
        business_event=business_event,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        prev_state=prev_state,
        curr_state=curr_state,
        product_id=product_id,
        payload=payload,
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
) -> List[CanonicalEventRecord]:
    """
    同一 lot の連続した 2 row から canonical events を推定する。
    判定の土台は row 差分、Node Character は意味づけの触媒。
    """
    events: List[CanonicalEventRecord] = []

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
                    business_event=BusinessEventType.SHIPMENT_RELEASED,
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
                business_event=BusinessEventType.SHIPMENT_TRANSPORT_RECEIPT,
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
                    business_event=BusinessEventType.GOODS_RECEIVED,
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
                    business_event=BusinessEventType.GOODS_RECEIVED,
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
                    business_event=BusinessEventType.GOODS_RECEIVED,
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
                    business_event=BusinessEventType.HANDOVER_COMPLETED,
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
            events.append(
                make_event(
                    "lot_production_completed",
                    prev_row,
                    curr_row,
                    business_event=BusinessEventType.PRODUCTION_COMPLETED,
                )
            )
        elif curr_char.get("can_purchase") and not curr_char.get("can_produce"):
            events.append(
                make_event(
                    "lot_procurement_received",
                    prev_row,
                    curr_row,
                    business_event=BusinessEventType.PROCUREMENT_RECEIVED,
                )
            )
        else:
            events.append(
                make_event(
                    "lot_moved_to_inventory",
                    prev_row,
                    curr_row,
                    business_event=BusinessEventType.PUTAWAY_COMPLETED,
                )
            )
        return events

    # --------------------------------------------------------
    # 3) I -> CO
    # --------------------------------------------------------
    if prev_state == "I" and curr_state == "CO":
        if curr_char.get("is_decoupling_point") and curr_char.get("can_allocate"):
            events.append(
                make_event(
                    "lot_pulled_by_demand",
                    prev_row,
                    curr_row,
                    business_event=BusinessEventType.HANDOVER_COMPLETED,
                )
            )
            events.append(
                make_event(
                    "lot_allocated",
                    prev_row,
                    curr_row,
                    business_event=BusinessEventType.HANDOVER_COMPLETED,
                )
            )
        elif curr_char.get("is_decoupling_point"):
            events.append(
                make_event(
                    "demand_bound_to_lot",
                    prev_row,
                    curr_row,
                    business_event=BusinessEventType.HANDOVER_COMPLETED,
                )
            )
        elif curr_char.get("can_sell"):
            events.append(
                make_event(
                    "lot_sales_committed",
                    prev_row,
                    curr_row,
                    business_event=BusinessEventType.SALE_EXECUTION,
                )
            )
        elif curr_char.get("can_ship"):
            events.append(
                make_event(
                    "lot_ship_committed",
                    prev_row,
                    curr_row,
                    business_event=BusinessEventType.SHIPMENT_PREPARATION,
                )
            )
        elif curr_char.get("can_allocate"):
            events.append(
                make_event(
                    "lot_allocated",
                    prev_row,
                    curr_row,
                    business_event=BusinessEventType.HANDOVER_COMPLETED,
                )
            )
        else:
            events.append(
                make_event(
                    "lot_committed_at_node",
                    prev_row,
                    curr_row,
                    business_event=BusinessEventType.HANDOVER_COMPLETED,
                )
            )
        return events

    # --------------------------------------------------------
    # 4) CO -> S
    # --------------------------------------------------------
    if prev_state == "CO" and curr_state == "S":
        if curr_char.get("can_sell"):
            events.append(
                make_event(
                    "lot_sold",
                    prev_row,
                    curr_row,
                    business_event=BusinessEventType.SALE_EXECUTION,
                )
            )
        elif curr_char.get("can_ship"):
            events.append(
                make_event(
                    "lot_shipped",
                    prev_row,
                    curr_row,
                    business_event=BusinessEventType.SHIPMENT_RELEASED,
                )
            )
        else:
            events.append(
                make_event(
                    "lot_released_from_node",
                    prev_row,
                    curr_row,
                    business_event=BusinessEventType.HANDOVER_COMPLETED,
                )
            )
        return events

    # --------------------------------------------------------
    # 5) I -> S
    # --------------------------------------------------------
    if prev_state == "I" and curr_state == "S":
        # consumer special branch
        if is_consumer_node(curr_char):
            mot_event = _build_consumer_mot_event(curr_row, curr_char)
            wb_state = _CONSUMER_STATE_REPO.apply_event(mot_event)

            events.append(
                make_event(
                    "consumer_consumption_completed",
                    prev_row,
                    curr_row,
                    business_event=BusinessEventType.CONSUMPTION_EXECUTION,
                    payload={
                        "mot_event_type": mot_event.event_type.value,
                        "mot_score_delta": mot_event.score_delta,
                        "mot_payload": dict(mot_event.payload or {}),
                        "well_being_state": {
                            "consumer_node_id": wb_state.consumer_node_id,
                            "product_id": wb_state.product_id,
                            "satisfaction_stock": wb_state.satisfaction_stock,
                            "brand_loyalty": wb_state.brand_loyalty,
                            "repeat_intent": wb_state.repeat_intent,
                            "switch_cost_perception": wb_state.switch_cost_perception,
                            "price_sensitivity": wb_state.price_sensitivity,
                            "habit_strength": wb_state.habit_strength,
                            "well_being_degree": wb_state.well_being_degree,
                            "last_time_bucket": wb_state.last_time_bucket,
                            "history_count": wb_state.history_count,
                        },
                    },
                )
            )
            return events

        if curr_char.get("can_sell"):
            events.append(
                make_event(
                    "lot_sold",
                    prev_row,
                    curr_row,
                    business_event=BusinessEventType.SALE_EXECUTION,
                )
            )
        elif curr_char.get("can_ship"):
            events.append(
                make_event(
                    "lot_shipped",
                    prev_row,
                    curr_row,
                    business_event=BusinessEventType.SHIPMENT_RELEASED,
                )
            )
        else:
            events.append(
                make_event(
                    "lot_released_from_node",
                    prev_row,
                    curr_row,
                    business_event=BusinessEventType.HANDOVER_COMPLETED,
                )
            )
        return events

    # --------------------------------------------------------
    # 6) fallback
    # --------------------------------------------------------
    events.append(
        make_event(
            "lot_state_changed_unclassified",
            prev_row,
            curr_row,
        )
    )
    return events


# ------------------------------------------------------------
# Sort / sequence helpers
# ------------------------------------------------------------

def canonical_sort_key(row: Row) -> Tuple[str, str, int, int, str]:
    """
    bridge 内で同一 lot の row を自然順に並べるための最小 sort key。
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
) -> List[CanonicalEventRecord]:
    sorted_rows = sort_rows_for_event_inference(rows)
    events: List[CanonicalEventRecord] = []

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
# Trace adapter
# ------------------------------------------------------------

def canonical_event_to_trace_dict(event: CanonicalEventRecord, sequence_no: int) -> dict:
    return canonical_event_record_to_trace_dict(event, sequence_no)


def canonical_events_to_trace_dicts(
    events: Sequence[CanonicalEventRecord],
    start_sequence_no: int = 1,
) -> List[dict]:
    return [
        canonical_event_to_trace_dict(event, sequence_no=i)
        for i, event in enumerate(events, start=start_sequence_no)
    ]


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
        {
            "lot_id": "CS_CAL-CAL_RICE_1-2024340007",
            "sequence_no": "0007",
            "time_bucket": "177",
            "node_id": "RT_CAL",
            "product_id": "CAL_RICE_1",
            "psi_state": "I",
        },
        {
            "lot_id": "CS_CAL-CAL_RICE_1-2024340007",
            "sequence_no": "0007",
            "time_bucket": "178",
            "node_id": "CS_CAL",
            "product_id": "CAL_RICE_1",
            "psi_state": "P",
        },
        {
            "lot_id": "CS_CAL-CAL_RICE_1-2024340007",
            "sequence_no": "0007",
            "time_bucket": "179",
            "node_id": "CS_CAL",
            "product_id": "CAL_RICE_1",
            "psi_state": "I",
        },
        {
            "lot_id": "CS_CAL-CAL_RICE_1-2024340007",
            "sequence_no": "0007",
            "time_bucket": "180",
            "node_id": "CS_CAL",
            "product_id": "CAL_RICE_1",
            "psi_state": "S",
        },
    ]

    inferred = infer_events_for_lot_rows(
        rows=rows,
        node_char_by_node_id=node_char_by_node_id,
        graph_edges=graph_edges,
    )

    for i, ev in enumerate(inferred, start=1):
        print(canonical_event_to_trace_dict(ev, i))
