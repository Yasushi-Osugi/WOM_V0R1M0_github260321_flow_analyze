#pysi/bridge/canonical_events.py

# canonical_events.py skeleton は、
# •	P_TO_I / I_TO_S / S_TO_NEXT_P を最上位骨格に置き 
# •	物理・業務・金額の意味を分離し 
# •	現行の event_rules.py / trace_event_sink と共存できる


from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


# ============================================================
# Layer 1: Canonical PSI Transition
# ============================================================

class CanonicalEventType(str, Enum):
    """
    WOM Canonical Event Layer v0.1
    最上位の普遍的な PSI 状態遷移。
    """
    P_TO_I = "P_TO_I"
    I_TO_S = "I_TO_S"
    S_TO_NEXT_P = "S_TO_NEXT_P"


# ============================================================
# Layer 2: Physical Event
# ============================================================

class PhysicalEventType(str, Enum):
    """
    モノの物理的な移動・配置変化。
    """
    RECEIPT_TO_INVENTORY = "receipt_to_inventory"
    INVENTORY_TO_DISPATCH = "inventory_to_dispatch"
    DISPATCH_TO_RECEIPT = "dispatch_to_receipt"


# ============================================================
# Layer 3: Business Event
# ============================================================

class BusinessEventType(str, Enum):
    """
    業務・現場オペレーションとしての意味。
    """
    PUTAWAY_COMPLETED = "putaway_completed"
    PRODUCTION_COMPLETED = "production_completed"
    PROCUREMENT_RECEIVED = "procurement_received"

    SHIPMENT_PREPARATION = "shipment_preparation"
    SALE_EXECUTION = "sale_execution"
    CONSUMPTION_EXECUTION = "consumption_execution"

    SHIPMENT_TRANSPORT_RECEIPT = "shipment_transport_receipt"
    GOODS_TRANSFER = "goods_transfer"
    HANDOVER_COMPLETED = "handover_completed"

    GOODS_RECEIVED = "goods_received"
    SHIPMENT_RELEASED = "shipment_released"


# ============================================================
# Layer 4: Financial Event
# ============================================================

class FinancialEventType(str, Enum):
    """
    経営・会計・金額としての意味。
    """
    INVENTORY_CAPITALIZED = "inventory_capitalized"
    RECEIPT_COST_BOOKED = "receipt_cost_booked"

    REVENUE_RECOGNIZED = "revenue_recognized"
    INVENTORY_RELEASED = "inventory_released"
    INTERNAL_TRANSFER_OUT = "internal_transfer_out"

    PURCHASE_ACCRUED = "purchase_accrued"
    TRANSFER_PRICED = "transfer_priced"
    BILLING_TRIGGERED = "billing_triggered"


# ============================================================
# Canonical Event Record
# ============================================================

@dataclass(frozen=True)
class CanonicalEventRecord:
    """
    WOM event の統合レコード。

    設計方針:
    - canonical_event は最も安定した骨格
    - physical/business/financial は context により補完される
    - event_rules.py の既存 event_type と共存できるように operational_event_type を持つ
    """
    canonical_event: CanonicalEventType
    lot_id: str
    node_id: str
    time_bucket: str

    # layer 2-4
    physical_event: Optional[PhysicalEventType] = None
    business_event: Optional[BusinessEventType] = None
    financial_event: Optional[FinancialEventType] = None

    # current event_rules.py 互換の operational label
    operational_event_type: Optional[str] = None

    # cross-node の場合に使用
    from_node_id: Optional[str] = None
    to_node_id: Optional[str] = None

    # PSI state context
    prev_state: Optional[str] = None
    curr_state: Optional[str] = None

    # optional context
    product_id: Optional[str] = None
    quantity: float = 1.0
    payload: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# Factory helpers
# ============================================================

def make_p_to_i_event(
    *,
    lot_id: str,
    node_id: str,
    time_bucket: str,
    operational_event_type: Optional[str] = None,
    business_event: Optional[BusinessEventType] = None,
    financial_event: Optional[FinancialEventType] = None,
    prev_state: str = "P",
    curr_state: str = "I",
    product_id: Optional[str] = None,
    quantity: float = 1.0,
    payload: Optional[Dict[str, Any]] = None,
) -> CanonicalEventRecord:
    return CanonicalEventRecord(
        canonical_event=CanonicalEventType.P_TO_I,
        physical_event=PhysicalEventType.RECEIPT_TO_INVENTORY,
        business_event=business_event,
        financial_event=financial_event,
        operational_event_type=operational_event_type,
        lot_id=lot_id,
        node_id=node_id,
        time_bucket=time_bucket,
        prev_state=prev_state,
        curr_state=curr_state,
        product_id=product_id,
        quantity=quantity,
        payload=payload or {},
    )


def make_i_to_s_event(
    *,
    lot_id: str,
    node_id: str,
    time_bucket: str,
    operational_event_type: Optional[str] = None,
    business_event: Optional[BusinessEventType] = None,
    financial_event: Optional[FinancialEventType] = None,
    prev_state: str = "I",
    curr_state: str = "S",
    product_id: Optional[str] = None,
    quantity: float = 1.0,
    payload: Optional[Dict[str, Any]] = None,
) -> CanonicalEventRecord:
    return CanonicalEventRecord(
        canonical_event=CanonicalEventType.I_TO_S,
        physical_event=PhysicalEventType.INVENTORY_TO_DISPATCH,
        business_event=business_event,
        financial_event=financial_event,
        operational_event_type=operational_event_type,
        lot_id=lot_id,
        node_id=node_id,
        time_bucket=time_bucket,
        prev_state=prev_state,
        curr_state=curr_state,
        product_id=product_id,
        quantity=quantity,
        payload=payload or {},
    )


def make_s_to_next_p_event(
    *,
    lot_id: str,
    from_node_id: str,
    to_node_id: str,
    time_bucket: str,
    operational_event_type: Optional[str] = None,
    business_event: Optional[BusinessEventType] = None,
    financial_event: Optional[FinancialEventType] = None,
    prev_state: str = "S",
    curr_state: str = "P",
    product_id: Optional[str] = None,
    quantity: float = 1.0,
    payload: Optional[Dict[str, Any]] = None,
) -> CanonicalEventRecord:
    return CanonicalEventRecord(
        canonical_event=CanonicalEventType.S_TO_NEXT_P,
        physical_event=PhysicalEventType.DISPATCH_TO_RECEIPT,
        business_event=business_event,
        financial_event=financial_event,
        operational_event_type=operational_event_type,
        lot_id=lot_id,
        node_id=to_node_id,
        time_bucket=time_bucket,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        prev_state=prev_state,
        curr_state=curr_state,
        product_id=product_id,
        quantity=quantity,
        payload=payload or {},
    )


# ============================================================
# Trace / dict adapter
# ============================================================

def canonical_event_record_to_dict(event: CanonicalEventRecord) -> Dict[str, Any]:
    return {
        "canonical_event": event.canonical_event.value,
        "physical_event": event.physical_event.value if event.physical_event else None,
        "business_event": event.business_event.value if event.business_event else None,
        "financial_event": event.financial_event.value if event.financial_event else None,
        "operational_event_type": event.operational_event_type,
        "lot_id": event.lot_id,
        "node_id": event.node_id,
        "time_bucket": event.time_bucket,
        "from_node_id": event.from_node_id,
        "to_node_id": event.to_node_id,
        "prev_state": event.prev_state,
        "curr_state": event.curr_state,
        "product_id": event.product_id,
        "quantity": event.quantity,
        "payload": dict(event.payload or {}),
    }


def canonical_event_record_to_trace_dict(
    event: CanonicalEventRecord,
    sequence_no: int,
) -> Dict[str, Any]:
    payload = dict(event.payload or {})
    payload.update(
        {
            "canonical_event": event.canonical_event.value,
            "physical_event": event.physical_event.value if event.physical_event else None,
            "business_event": event.business_event.value if event.business_event else None,
            "financial_event": event.financial_event.value if event.financial_event else None,
            "from_node_id": event.from_node_id,
            "to_node_id": event.to_node_id,
            "prev_state": event.prev_state,
            "curr_state": event.curr_state,
        }
    )

    return {
        "sequence_no": sequence_no,
        "event_type": event.operational_event_type or event.canonical_event.value,
        "node_id": event.node_id,
        "lot_id": event.lot_id,
        "time_bucket": event.time_bucket,
        "product_id": event.product_id,
        "quantity": event.quantity,
        "payload": payload,
    }


# ============================================================
# Tiny smoke test
# ============================================================

if __name__ == "__main__":
    e1 = make_p_to_i_event(
        lot_id="LOT_001",
        node_id="DADCAL",
        time_bucket="25",
        operational_event_type="lot_moved_to_inventory",
        business_event=BusinessEventType.PUTAWAY_COMPLETED,
        financial_event=FinancialEventType.INVENTORY_CAPITALIZED,
    )

    e2 = make_i_to_s_event(
        lot_id="LOT_001",
        node_id="DADCAL",
        time_bucket="26",
        operational_event_type="lot_ship_committed",
        business_event=BusinessEventType.SHIPMENT_PREPARATION,
        financial_event=FinancialEventType.INTERNAL_TRANSFER_OUT,
    )

    e3 = make_s_to_next_p_event(
        lot_id="LOT_001",
        from_node_id="DADCAL",
        to_node_id="WS1CAL",
        time_bucket="26",
        operational_event_type="lot_transit_node_to_node",
        business_event=BusinessEventType.SHIPMENT_TRANSPORT_RECEIPT,
        financial_event=FinancialEventType.TRANSFER_PRICED,
    )

    for i, ev in enumerate([e1, e2, e3], start=1):
        print(canonical_event_record_to_trace_dict(ev, i))
