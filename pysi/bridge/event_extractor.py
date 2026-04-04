from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from pysi.bridge.event_schema import (
    ArrivalEvent,
    BindEvent,
    BridgeEvent,
    InventoryMoveEvent,
    PullRequestEvent,
    ShipmentEvent,
    validate_event,
)
from pysi.bridge.state_snapshot import PlanningStateSnapshot


@dataclass(frozen=True)
class ExtractContext:
    time_bucket: str
    seq_start: int = 0
    epsilon: float = 1e-9


def _next_seq(counter: Dict[str, int]) -> int:
    counter["seq"] += 1
    return counter["seq"]


def extract_events(
    previous_state: PlanningStateSnapshot,
    current_state: PlanningStateSnapshot,
    ctx: ExtractContext,
) -> List[BridgeEvent]:
    seq = {"seq": ctx.seq_start - 1}
    out: List[BridgeEvent] = []

    # used for residual accounting in inventory_move (v0.1 minimal scope)
    # NOTE:
    # - explained_delta currently includes shipment/arrival-centered effects.
    # - bind/pull_request inventory effects are intentionally not included yet;
    #   they can be added after domain rules are finalized.
    explained_by_node_product: Dict[Tuple[str, str], float] = {}

    all_lots = sorted(set(previous_state.lots.keys()) | set(current_state.lots.keys()))

    # v0.1 simplified transition rule:
    # - shipment: at_node -> in_transit
    # - arrival : in_transit -> at_node
    # Future extension:
    # - strict node->edge->node transition chain with explicit transit states.
    for lot_id in all_lots:
        p = previous_state.lots.get(lot_id)
        c = current_state.lots.get(lot_id)
        if not p or not c:
            continue
        if p.product_id != c.product_id:
            continue

        if p.status == "at_node" and c.status == "in_transit":
            from_node = p.current_node or p.from_node
            to_node = c.to_node or (c.current_edge[1] if c.current_edge else None)
            if from_node and to_node:
                e = ShipmentEvent(
                    event_id=f"evt-ship-{lot_id}-{ctx.time_bucket}",
                    time_bucket=ctx.time_bucket,
                    product_id=c.product_id,
                    quantity_cpu=c.quantity_cpu,
                    creation_sequence=_next_seq(seq),
                    stable_object_id=lot_id,
                    source_ref="v0r8_state_diff",
                    diff_basis="lot_position_diff",
                    lot_id=lot_id,
                    from_node=from_node,
                    to_node=to_node,
                )
                validate_event(e)
                out.append(e)
                key = (from_node, c.product_id)
                explained_by_node_product[key] = explained_by_node_product.get(key, 0.0) - c.quantity_cpu

        if p.status == "in_transit" and c.status == "at_node":
            from_node = p.from_node or (p.current_edge[0] if p.current_edge else None) or p.current_node
            to_node = c.current_node or c.to_node
            if from_node and to_node:
                e = ArrivalEvent(
                    event_id=f"evt-arr-{lot_id}-{ctx.time_bucket}",
                    time_bucket=ctx.time_bucket,
                    product_id=c.product_id,
                    quantity_cpu=c.quantity_cpu,
                    creation_sequence=_next_seq(seq),
                    stable_object_id=lot_id,
                    source_ref="v0r8_state_diff",
                    diff_basis="lot_position_diff",
                    lot_id=lot_id,
                    from_node=from_node,
                    to_node=to_node,
                )
                validate_event(e)
                out.append(e)
                key = (to_node, c.product_id)
                explained_by_node_product[key] = explained_by_node_product.get(key, 0.0) + c.quantity_cpu

    # bind priority #1: binding snapshot diff
    prev_bind = previous_state.lot_demand_bindings
    cur_bind = current_state.lot_demand_bindings
    used_bind_keys = set()

    for key in sorted(set(cur_bind.keys()) - set(prev_bind.keys())):
        b = cur_bind[key]
        e = BindEvent(
            event_id=f"evt-bind-{b.lot_id}-{b.demand_id}-{ctx.time_bucket}",
            time_bucket=ctx.time_bucket,
            product_id=b.product_id,
            quantity_cpu=b.quantity_cpu,
            creation_sequence=_next_seq(seq),
            stable_object_id=f"{b.lot_id}:{b.demand_id}",
            source_ref="binding_snapshot_diff",
            diff_basis="binding_snapshot_diff",
            lot_id=b.lot_id,
            demand_id=b.demand_id,
            to_node=b.node_id,
        )
        validate_event(e)
        out.append(e)
        used_bind_keys.add(key)

    # bind priority #2: allocation pseudo bind
    prev_alloc = previous_state.allocation_pairs
    cur_alloc = current_state.allocation_pairs
    for lot_id, demand_id in sorted(set(cur_alloc.keys()) - set(prev_alloc.keys())):
        if (lot_id, demand_id) in used_bind_keys:
            continue
        lot_cur = current_state.lots.get(lot_id)
        if not lot_cur:
            continue
        qty = float(cur_alloc[(lot_id, demand_id)])
        e = BindEvent(
            event_id=f"evt-bind-alloc-{lot_id}-{demand_id}-{ctx.time_bucket}",
            time_bucket=ctx.time_bucket,
            product_id=lot_cur.product_id,
            quantity_cpu=max(qty, 0.0),
            creation_sequence=_next_seq(seq),
            stable_object_id=f"{lot_id}:{demand_id}",
            source_ref="allocation_pseudo_bind",
            diff_basis="allocation_delta",
            lot_id=lot_id,
            demand_id=demand_id,
            to_node=lot_cur.current_node or lot_cur.to_node or "unknown",
        )
        validate_event(e)
        out.append(e)

    # pull_request from backlog increase
    all_backlog_keys = sorted(set(previous_state.backlog.keys()) | set(current_state.backlog.keys()))
    for node_id, product_id in all_backlog_keys:
        b_prev = float(previous_state.backlog.get((node_id, product_id), 0.0))
        b_cur = float(current_state.backlog.get((node_id, product_id), 0.0))
        delta = b_cur - b_prev
        if delta > ctx.epsilon:
            e = PullRequestEvent(
                event_id=f"evt-pull-{node_id}-{product_id}-{ctx.time_bucket}",
                time_bucket=ctx.time_bucket,
                product_id=product_id,
                quantity_cpu=delta,
                creation_sequence=_next_seq(seq),
                stable_object_id=f"{node_id}:{product_id}",
                source_ref="v0r8_state_diff",
                diff_basis="backlog_delta",
                to_node=node_id,
                reason_code="shortage",
            )
            validate_event(e)
            out.append(e)

    # inventory_move residual only
    all_inv_keys = sorted(set(previous_state.inventory.keys()) | set(current_state.inventory.keys()))
    for node_id, product_id in all_inv_keys:
        observed = float(current_state.inventory.get((node_id, product_id), 0.0)) - float(
            previous_state.inventory.get((node_id, product_id), 0.0)
        )
        explained = float(explained_by_node_product.get((node_id, product_id), 0.0))
        residual = observed - explained
        if abs(residual) > ctx.epsilon:
            # policy: quantity_cpu = abs(residual), sign is preserved in metadata["residual_qty"]
            e = InventoryMoveEvent(
                event_id=f"evt-imv-{node_id}-{product_id}-{ctx.time_bucket}",
                time_bucket=ctx.time_bucket,
                product_id=product_id,
                quantity_cpu=abs(residual),
                creation_sequence=_next_seq(seq),
                stable_object_id=f"{node_id}:{product_id}",
                source_ref="v0r8_state_diff",
                diff_basis="inventory_residual",
                to_node=node_id,
                reason_code="residual_adjustment",
                metadata={
                    "observed_inventory_delta": observed,
                    "explained_delta": explained,
                    "residual_qty": residual,
                },
            )
            validate_event(e)
            out.append(e)

    priority = {
        "shipment": 10,
        "arrival": 20,
        "pull_request": 30,
        "bind": 40,
        "inventory_move": 50,
    }
    out.sort(
        key=lambda e: (
            e.time_bucket,
            priority[e.event_type],
            e.stable_object_id,
            e.creation_sequence,
            e.event_id,
        )
    )
    return out
