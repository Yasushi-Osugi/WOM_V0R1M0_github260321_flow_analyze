from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PSI_S = 0
PSI_CO = 1
PSI_I = 2
PSI_P = 3


@dataclass
class CapacityAwareInboundBackwardPlanningResult:
    product_name: str
    planned_lot_count: int = 0
    capacity_checked_lot_count: int = 0
    accepted_lot_count: int = 0
    shifted_lot_count: int = 0
    backlog_lot_count: int = 0
    capacity_usage_by_mom_week: dict = field(default_factory=dict)
    shifted_lots: list[dict] = field(default_factory=list)
    backlog_lots: list[dict] = field(default_factory=list)
    non_list_bucket_errors: list[dict] = field(default_factory=list)
    non_string_lot_errors: list[dict] = field(default_factory=list)
    message: str = ""


def _walk_nodes(root: Any):
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(reversed(getattr(node, "children", []) or []))


def _normalize_capacity_values(raw: Any, weeks: int) -> list[int]:
    if isinstance(raw, dict):
        return [max(0, int(raw.get(w, 0) or 0)) for w in range(weeks)]
    if isinstance(raw, list):
        return [max(0, int(raw[w] if w < len(raw) else 0 or 0)) for w in range(weeks)]
    if raw is None:
        return [0] * weeks
    try:
        c = max(0, int(raw))
    except (TypeError, ValueError):
        c = 0
    return [c] * weeks


def resolve_mom_weekly_capacity(
    mom,
    *,
    product: str,
    weekly_capability: dict | None,
    weeks: int,
) -> list[int]:
    if weekly_capability and isinstance(weekly_capability, dict):
        by_product = weekly_capability.get(product)
        if isinstance(by_product, dict) and mom.name in by_product:
            return _normalize_capacity_values(by_product[mom.name], weeks)
        if mom.name in weekly_capability:
            return _normalize_capacity_values(weekly_capability[mom.name], weeks)
    if hasattr(mom, "nx_capacity"):
        return _normalize_capacity_values(getattr(mom, "nx_capacity"), weeks)
    return [0] * weeks


def capacity_aware_inbound_backward_planning(
    *,
    in_root,
    product: str,
    weekly_capability: dict | None = None,
    weeks: int | None = None,
    max_early_build_weeks: int = 13,
    priority_rule: str = "FIFO",
    backlog_policy: str = "record_backlog_state",
    debug: bool = False,
) -> CapacityAwareInboundBackwardPlanningResult:
    del priority_rule, backlog_policy, debug
    mom_nodes = [n for n in _walk_nodes(in_root) if str(getattr(n, "name", "")).startswith("MOM")]
    result = CapacityAwareInboundBackwardPlanningResult(product_name=product)
    if not mom_nodes:
        result.message = "No MOM nodes found."
        return result

    for mom in mom_nodes:
        psi = getattr(mom, "psi4demand", None)
        if not isinstance(psi, list):
            result.non_list_bucket_errors.append({"mom": mom.name, "reason": "psi4demand_not_list"})
            continue

        target_weeks = min(weeks if weeks is not None else len(psi), len(psi))
        cap_by_week = resolve_mom_weekly_capacity(
            mom,
            product=product,
            weekly_capability=weekly_capability,
            weeks=target_weeks,
        )

        for w in range(target_weeks):
            if not isinstance(psi[w], list) or len(psi[w]) < 4:
                result.non_list_bucket_errors.append({"mom": mom.name, "week": w, "reason": "invalid_week_bucket"})
                continue
            for b in (PSI_S, PSI_CO, PSI_I, PSI_P):
                if not isinstance(psi[w][b], list):
                    result.non_list_bucket_errors.append({"mom": mom.name, "week": w, "bucket": b, "reason": "bucket_not_list"})
                    psi[w][b] = []

            demand_lots = list(psi[w][PSI_S])
            valid_demand_lots = []
            for lot in demand_lots:
                if isinstance(lot, str):
                    valid_demand_lots.append(lot)
                else:
                    result.non_string_lot_errors.append({"mom": mom.name, "week": w, "bucket": PSI_S, "lot": lot})
            psi[w][PSI_P].extend(valid_demand_lots)
            result.planned_lot_count += len(valid_demand_lots)

        for w in range(target_weeks):
            current_p = psi[w][PSI_P]
            current_lots = [lot for lot in current_p if isinstance(lot, str)]
            if len(current_lots) != len(current_p):
                for lot in current_p:
                    if not isinstance(lot, str):
                        result.non_string_lot_errors.append({"mom": mom.name, "week": w, "bucket": PSI_P, "lot": lot})
                psi[w][PSI_P] = current_lots

            cap_w = cap_by_week[w] if w < len(cap_by_week) else 0
            keep = current_lots[:cap_w]
            overflow = current_lots[cap_w:]
            psi[w][PSI_P] = keep

            result.capacity_checked_lot_count += len(current_lots)
            result.accepted_lot_count += len(keep)

            for lot in overflow:
                placed_week = None
                lower = max(-1, w - max_early_build_weeks)
                for wp in range(w - 1, lower, -1):
                    room = (cap_by_week[wp] if wp < len(cap_by_week) else 0) - len(psi[wp][PSI_P])
                    if room > 0:
                        psi[wp][PSI_P].append(lot)
                        placed_week = wp
                        result.shifted_lot_count += 1
                        result.accepted_lot_count += 1
                        result.shifted_lots.append({
                            "lot_id": lot,
                            "assigned_mom": mom.name,
                            "demand_week": w,
                            "from_week": w,
                            "to_week": wp,
                            "reason": "capacity_overflow_shifted_earlier",
                        })
                        break

                if placed_week is None:
                    result.backlog_lot_count += 1
                    result.backlog_lots.append({
                        "lot_id": lot,
                        "assigned_mom": mom.name,
                        "demand_week": w,
                        "attempted_week": w,
                        "reason": "no_feasible_capacity_in_early_build_window",
                    })

        for w in range(target_weeks):
            result.capacity_usage_by_mom_week[(mom.name, w)] = {
                "used": len(psi[w][PSI_P]),
                "capacity": cap_by_week[w] if w < len(cap_by_week) else 0,
            }

    result.message = "Completed TOBE capacity-aware inbound backward planning MVP."
    return result
