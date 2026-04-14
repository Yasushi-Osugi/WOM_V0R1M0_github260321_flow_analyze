承知しました。
以下に、**この表に対応した Python の `kpi_registry` 定義案** を、**そのまま repo に置ける最小 skeleton** として示します。

狙いは次の通りです。

* KPI を **定義データ** として管理する
* `node / supply_point / total_sc / strategic` の4層を同じ形式で扱う
* 数量編・金額編・スコア系を同じ registry で拡張できる
* `compute_fn` を差し替えれば、WOM の現行データ構造に接続できる

---

# ファイル案

`pysi/kpi/kpi_registry.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Literal, Mapping, Optional, Sequence

KPILevel = Literal["node", "supply_point", "total_sc", "strategic"]
KPIScope = Literal[
    "node",
    "supply_point_inbound",
    "supply_point_outbound",
    "supply_point_integrated",
    "total_sc",
    "strategic",
]
KPIValueType = Literal["qty", "amount", "ratio", "days", "count", "score"]

ComputeFn = Callable[[Mapping[str, Any]], Optional[float]]


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator in (0, 0.0, None):
        return default
    return numerator / denominator


def weighted_average(pairs: Sequence[tuple[float, float]], default: float = 0.0) -> float:
    total_weight = sum(w for _, w in pairs)
    if total_weight == 0:
        return default
    return sum(v * w for v, w in pairs) / total_weight


@dataclass(frozen=True)
class KPIDefinition:
    """
    Canonical KPI definition for WOM.

    id:
        Stable internal key.
    label:
        User-facing label.
    level:
        node / supply_point / total_sc / strategic
    scope:
        More detailed placement within the hierarchy.
    value_type:
        qty / amount / ratio / days / count / score
    unit:
        e.g. 'qty', 'JPY', '%', 'days', 'score'
    grain:
        Tuple that describes storage grain, e.g. ('product', 'node', 'week')
    description:
        Human-readable definition.
    formula_text:
        Canonical formula string for docs / UI tooltip.
    depends_on:
        Required raw inputs or upstream KPI IDs.
    display_places:
        Suggested UI placement.
    compute_fn:
        Function that computes the KPI from a context dict.
    """
    id: str
    label: str
    level: KPILevel
    scope: KPIScope
    value_type: KPIValueType
    unit: str
    grain: tuple[str, ...]
    description: str
    formula_text: str
    depends_on: tuple[str, ...] = field(default_factory=tuple)
    display_places: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    enabled: bool = True
    compute_fn: Optional[ComputeFn] = None


# ============================================================
# compute functions: node
# ============================================================

def compute_node_production_qty(ctx: Mapping[str, Any]) -> float:
    return float(ctx.get("P_qty", 0.0))


def compute_node_shipment_qty(ctx: Mapping[str, Any]) -> float:
    return float(ctx.get("S_qty", 0.0))


def compute_node_ending_inventory_qty(ctx: Mapping[str, Any]) -> float:
    i_begin = float(ctx.get("I_begin", 0.0))
    p_qty = float(ctx.get("P_qty", 0.0))
    s_qty = float(ctx.get("S_qty", 0.0))
    return i_begin + p_qty - s_qty


def compute_node_backlog_qty(ctx: Mapping[str, Any]) -> float:
    backlog_begin = float(ctx.get("backlog_begin", 0.0))
    demand_qty = float(ctx.get("demand_qty", 0.0))
    served_qty = float(ctx.get("served_qty", 0.0))
    return backlog_begin + demand_qty - served_qty


def compute_node_capacity_utilization(ctx: Mapping[str, Any]) -> float:
    used_qty = float(ctx.get("used_qty", ctx.get("P_qty", 0.0)))
    cap_qty = float(ctx.get("cap_qty", 0.0))
    return safe_div(used_qty, cap_qty, default=0.0)


def compute_node_stockout_qty(ctx: Mapping[str, Any]) -> float:
    demand_qty = float(ctx.get("demand_qty", 0.0))
    served_qty = float(ctx.get("served_qty", 0.0))
    return max(0.0, demand_qty - served_qty)


def compute_node_fill_rate(ctx: Mapping[str, Any]) -> float:
    demand_qty = float(ctx.get("demand_qty", 0.0))
    served_qty = float(ctx.get("served_qty", 0.0))
    return safe_div(served_qty, demand_qty, default=1.0 if demand_qty == 0 else 0.0)


def compute_node_inventory_days(ctx: Mapping[str, Any]) -> float:
    inventory_qty = float(ctx.get("I_end", ctx.get("inventory_qty", 0.0)))
    avg_weekly_sales = float(ctx.get("avg_weekly_sales", 0.0))
    return safe_div(inventory_qty, avg_weekly_sales, default=0.0)


def compute_node_sales_amount(ctx: Mapping[str, Any]) -> float:
    s_qty = float(ctx.get("S_qty", 0.0))
    sales_price = float(ctx.get("sales_price", 0.0))
    return s_qty * sales_price


def compute_node_purchase_cost(ctx: Mapping[str, Any]) -> float:
    purchase_qty = float(ctx.get("purchase_qty", ctx.get("P_qty", 0.0)))
    purchase_unit_cost = float(ctx.get("purchase_unit_cost", 0.0))
    return purchase_qty * purchase_unit_cost


def compute_node_production_cost(ctx: Mapping[str, Any]) -> float:
    p_qty = float(ctx.get("P_qty", 0.0))
    production_unit_cost = float(ctx.get("production_unit_cost", 0.0))
    return p_qty * production_unit_cost


def compute_node_logistics_cost(ctx: Mapping[str, Any]) -> float:
    ship_qty = float(ctx.get("ship_qty", ctx.get("S_qty", 0.0)))
    logistics_unit_cost = float(ctx.get("logistics_unit_cost", 0.0))
    return ship_qty * logistics_unit_cost


def compute_node_inventory_holding_cost(ctx: Mapping[str, Any]) -> float:
    avg_inventory = float(ctx.get("avg_inventory", ctx.get("I_end", 0.0)))
    holding_cost_rate = float(ctx.get("holding_cost_rate", 0.0))
    return avg_inventory * holding_cost_rate


def compute_node_gross_profit_contribution(ctx: Mapping[str, Any]) -> float:
    sales_amount = float(ctx.get("sales_amount", 0.0))
    purchase_cost = float(ctx.get("purchase_cost", 0.0))
    production_cost = float(ctx.get("production_cost", 0.0))
    logistics_cost = float(ctx.get("logistics_cost", 0.0))
    inventory_cost = float(ctx.get("inventory_holding_cost", 0.0))
    return sales_amount - purchase_cost - production_cost - logistics_cost - inventory_cost


def compute_node_event_count(ctx: Mapping[str, Any]) -> float:
    return float(len(ctx.get("events", [])))


def compute_node_bottleneck_event_count(ctx: Mapping[str, Any]) -> float:
    events = ctx.get("events", [])
    return float(sum(1 for e in events if e.get("event_type") == "bottleneck"))


def compute_node_stockout_event_count(ctx: Mapping[str, Any]) -> float:
    events = ctx.get("events", [])
    return float(sum(1 for e in events if e.get("event_type") == "stockout"))


def compute_node_trust_event_score(ctx: Mapping[str, Any]) -> float:
    """
    Simple example:
    higher is better, penalties for bottleneck/stockout/stagnation.
    """
    base = float(ctx.get("trust_base_score", 100.0))
    bottleneck_events = float(ctx.get("bottleneck_event_count", 0.0))
    stockout_events = float(ctx.get("stockout_event_count", 0.0))
    stagnation_events = float(ctx.get("stagnation_event_count", 0.0))
    return max(
        0.0,
        base
        - 5.0 * bottleneck_events
        - 8.0 * stockout_events
        - 3.0 * stagnation_events,
    )


# ============================================================
# compute functions: supply_point
# ============================================================

def compute_inbound_receipt_qty(ctx: Mapping[str, Any]) -> float:
    return float(ctx.get("inbound_receipt_qty", 0.0))


def compute_inbound_capacity_utilization(ctx: Mapping[str, Any]) -> float:
    used_qty = float(ctx.get("inbound_used_qty", 0.0))
    cap_qty = float(ctx.get("inbound_cap_qty", 0.0))
    return safe_div(used_qty, cap_qty, default=0.0)


def compute_inbound_material_shortage_qty(ctx: Mapping[str, Any]) -> float:
    required_input_qty = float(ctx.get("required_input_qty", 0.0))
    available_input_qty = float(ctx.get("available_input_qty", 0.0))
    return max(0.0, required_input_qty - available_input_qty)


def compute_outbound_shipment_qty(ctx: Mapping[str, Any]) -> float:
    return float(ctx.get("outbound_shipment_qty", 0.0))


def compute_outbound_demand_qty(ctx: Mapping[str, Any]) -> float:
    return float(ctx.get("outbound_demand_qty", 0.0))


def compute_outbound_sales_qty(ctx: Mapping[str, Any]) -> float:
    return float(ctx.get("outbound_sales_qty", 0.0))


def compute_outbound_fill_rate(ctx: Mapping[str, Any]) -> float:
    demand_qty = float(ctx.get("outbound_demand_qty", 0.0))
    served_qty = float(ctx.get("outbound_sales_qty", 0.0))
    return safe_div(served_qty, demand_qty, default=1.0 if demand_qty == 0 else 0.0)


def compute_outbound_stockout_qty(ctx: Mapping[str, Any]) -> float:
    demand_qty = float(ctx.get("outbound_demand_qty", 0.0))
    served_qty = float(ctx.get("outbound_sales_qty", 0.0))
    return max(0.0, demand_qty - served_qty)


def compute_market_priority_compliance(ctx: Mapping[str, Any]) -> float:
    compliant_allocated_qty = float(ctx.get("priority_compliant_allocated_qty", 0.0))
    total_allocated_qty = float(ctx.get("total_allocated_qty", 0.0))
    return safe_div(compliant_allocated_qty, total_allocated_qty, default=1.0 if total_allocated_qty == 0 else 0.0)


def compute_demand_supply_gap_qty(ctx: Mapping[str, Any]) -> float:
    demand_qty = float(ctx.get("outbound_demand_qty", 0.0))
    feasible_supply_qty = float(ctx.get("feasible_supply_qty", 0.0))
    return demand_qty - feasible_supply_qty


def compute_demand_supply_gap_rate(ctx: Mapping[str, Any]) -> float:
    demand_qty = float(ctx.get("outbound_demand_qty", 0.0))
    feasible_supply_qty = float(ctx.get("feasible_supply_qty", 0.0))
    return safe_div(demand_qty - feasible_supply_qty, demand_qty, default=0.0)


def compute_decoupling_inventory_qty(ctx: Mapping[str, Any]) -> float:
    return float(ctx.get("decoupling_inventory_qty", ctx.get("I_end", 0.0)))


def compute_decoupling_inventory_health(ctx: Mapping[str, Any]) -> float:
    """
    Example score:
    100 if within buffer range, then linearly penalize outside range.
    """
    inv = float(ctx.get("decoupling_inventory_qty", 0.0))
    buffer_min = float(ctx.get("buffer_min", 0.0))
    buffer_max = float(ctx.get("buffer_max", 0.0))

    if buffer_min <= inv <= buffer_max:
        return 100.0

    if inv < buffer_min:
        shortage = buffer_min - inv
        return max(0.0, 100.0 - shortage)

    excess = inv - buffer_max
    return max(0.0, 100.0 - excess)


def compute_allocation_efficiency(ctx: Mapping[str, Any]) -> float:
    value_served = float(ctx.get("value_served", 0.0))
    available_supply_qty = float(ctx.get("available_supply_qty", 0.0))
    return safe_div(value_served, available_supply_qty, default=0.0)


def compute_bottleneck_impact_qty(ctx: Mapping[str, Any]) -> float:
    return float(ctx.get("bottleneck_impact_qty", 0.0))


def compute_weekly_psi_balance_score(ctx: Mapping[str, Any]) -> float:
    """
    Example heuristic:
    small backlog, reasonable inventory, and balanced P/S improve the score.
    """
    p_qty = float(ctx.get("P_qty", 0.0))
    s_qty = float(ctx.get("S_qty", 0.0))
    backlog_qty = float(ctx.get("backlog_qty", 0.0))
    inventory_qty = float(ctx.get("I_end", 0.0))
    balance_penalty = abs(p_qty - s_qty) + backlog_qty + max(0.0, inventory_qty - float(ctx.get("buffer_max", inventory_qty)))
    return max(0.0, 100.0 - balance_penalty)


def compute_supply_point_profit_contribution(ctx: Mapping[str, Any]) -> float:
    sales_amount = float(ctx.get("sales_amount", 0.0))
    purchase_cost = float(ctx.get("purchase_cost", 0.0))
    production_cost = float(ctx.get("production_cost", 0.0))
    logistics_cost = float(ctx.get("logistics_cost", 0.0))
    inventory_cost = float(ctx.get("inventory_holding_cost", 0.0))
    return sales_amount - purchase_cost - production_cost - logistics_cost - inventory_cost


def compute_supply_point_cash_pressure(ctx: Mapping[str, Any]) -> float:
    inventory_value = float(ctx.get("inventory_value", 0.0))
    receivable_lag_effect = float(ctx.get("receivable_lag_effect", 0.0))
    payable_lag_effect = float(ctx.get("payable_lag_effect", 0.0))
    return inventory_value + receivable_lag_effect - payable_lag_effect


# ============================================================
# compute functions: total supply chain
# ============================================================

def compute_total_production_qty(ctx: Mapping[str, Any]) -> float:
    return float(ctx.get("total_production_qty", 0.0))


def compute_total_shipment_sales_qty(ctx: Mapping[str, Any]) -> float:
    return float(ctx.get("total_sales_qty", 0.0))


def compute_total_ending_inventory_qty(ctx: Mapping[str, Any]) -> float:
    return float(ctx.get("total_inventory_qty", 0.0))


def compute_total_backlog_qty(ctx: Mapping[str, Any]) -> float:
    return float(ctx.get("total_backlog_qty", 0.0))


def compute_total_fill_rate(ctx: Mapping[str, Any]) -> float:
    total_demand_qty = float(ctx.get("total_demand_qty", 0.0))
    total_served_qty = float(ctx.get("total_served_qty", 0.0))
    return safe_div(total_served_qty, total_demand_qty, default=1.0 if total_demand_qty == 0 else 0.0)


def compute_total_stockout_rate(ctx: Mapping[str, Any]) -> float:
    total_demand_qty = float(ctx.get("total_demand_qty", 0.0))
    total_stockout_qty = float(ctx.get("total_stockout_qty", 0.0))
    return safe_div(total_stockout_qty, total_demand_qty, default=0.0)


def compute_total_inventory_value(ctx: Mapping[str, Any]) -> float:
    return float(ctx.get("total_inventory_value", 0.0))


def compute_total_capacity_utilization(ctx: Mapping[str, Any]) -> float:
    total_used_qty = float(ctx.get("total_used_qty", 0.0))
    total_cap_qty = float(ctx.get("total_cap_qty", 0.0))
    return safe_div(total_used_qty, total_cap_qty, default=0.0)


def compute_capacity_concentration_index(ctx: Mapping[str, Any]) -> float:
    max_util = float(ctx.get("max_node_utilization", 0.0))
    avg_util = float(ctx.get("avg_node_utilization", 0.0))
    return safe_div(max_util, avg_util, default=0.0)


def compute_total_lead_time(ctx: Mapping[str, Any]) -> float:
    return float(ctx.get("avg_end_to_end_lead_time", 0.0))


def compute_plan_stability_score(ctx: Mapping[str, Any]) -> float:
    replanned_qty = float(ctx.get("replanned_qty", 0.0))
    planned_qty = float(ctx.get("planned_qty", 0.0))
    return max(0.0, 1.0 - safe_div(replanned_qty, planned_qty, default=0.0))


def compute_total_sales_amount(ctx: Mapping[str, Any]) -> float:
    return float(ctx.get("total_sales_amount", 0.0))


def compute_total_variable_cost(ctx: Mapping[str, Any]) -> float:
    return float(ctx.get("total_variable_cost", 0.0))


def compute_total_gross_profit(ctx: Mapping[str, Any]) -> float:
    total_sales_amount = float(ctx.get("total_sales_amount", 0.0))
    total_variable_cost = float(ctx.get("total_variable_cost", 0.0))
    return total_sales_amount - total_variable_cost


def compute_total_operating_profit(ctx: Mapping[str, Any]) -> float:
    total_gross_profit = float(ctx.get("total_gross_profit", 0.0))
    fixed_cost = float(ctx.get("fixed_cost", 0.0))
    return total_gross_profit - fixed_cost


def compute_total_profit_margin(ctx: Mapping[str, Any]) -> float:
    total_operating_profit = float(ctx.get("total_operating_profit", 0.0))
    total_sales_amount = float(ctx.get("total_sales_amount", 0.0))
    return safe_div(total_operating_profit, total_sales_amount, default=0.0)


def compute_cash_conversion_pressure(ctx: Mapping[str, Any]) -> float:
    inventory_days = float(ctx.get("inventory_days", 0.0))
    receivable_days = float(ctx.get("receivable_days", 0.0))
    payable_days = float(ctx.get("payable_days", 0.0))
    return inventory_days + receivable_days - payable_days


def compute_supply_chain_roi_proxy(ctx: Mapping[str, Any]) -> float:
    total_operating_profit = float(ctx.get("total_operating_profit", 0.0))
    invested_capital_proxy = float(ctx.get("invested_capital_proxy", 0.0))
    return safe_div(total_operating_profit, invested_capital_proxy, default=0.0)


# ============================================================
# compute functions: strategic
# ============================================================

def compute_customer_fulfillment_score(ctx: Mapping[str, Any]) -> float:
    fill_rate = float(ctx.get("fill_rate", 0.0))
    otif = float(ctx.get("otif", 0.0))
    stockout_rate = float(ctx.get("stockout_rate", 0.0))
    return max(0.0, min(100.0, 100.0 * (0.5 * fill_rate + 0.4 * otif - 0.3 * stockout_rate)))


def compute_employee_workload_health_score(ctx: Mapping[str, Any]) -> float:
    over_capacity_ratio = float(ctx.get("over_capacity_ratio", 0.0))
    return max(0.0, min(100.0, 100.0 * (1.0 - over_capacity_ratio)))


def compute_supplier_stability_score(ctx: Mapping[str, Any]) -> float:
    abrupt_order_change_ratio = float(ctx.get("abrupt_order_change_ratio", 0.0))
    return max(0.0, min(100.0, 100.0 * (1.0 - abrupt_order_change_ratio)))


def compute_balanced_stakeholder_score(ctx: Mapping[str, Any]) -> float:
    return weighted_average(
        [
            (float(ctx.get("customer_fulfillment_score", 0.0)), 0.4),
            (float(ctx.get("employee_workload_health_score", 0.0)), 0.3),
            (float(ctx.get("supplier_stability_score", 0.0)), 0.3),
        ],
        default=0.0,
    )


def compute_profit_sustainability_score(ctx: Mapping[str, Any]) -> float:
    profit_margin = float(ctx.get("profit_margin", 0.0))
    profit_volatility = float(ctx.get("profit_volatility", 0.0))
    score = 100.0 * profit_margin - 50.0 * profit_volatility
    return max(0.0, min(100.0, score))


def compute_inventory_soundness_score(ctx: Mapping[str, Any]) -> float:
    inventory_days = float(ctx.get("inventory_days", 0.0))
    obsolescence_risk = float(ctx.get("obsolescence_risk", 0.0))
    buffer_health = float(ctx.get("buffer_health", 100.0))
    score = buffer_health - inventory_days - 50.0 * obsolescence_risk
    return max(0.0, min(100.0, score))


def compute_capacity_resilience_score(ctx: Mapping[str, Any]) -> float:
    avg_slack_ratio = float(ctx.get("avg_slack_ratio", 0.0))
    bottleneck_concentration = float(ctx.get("bottleneck_concentration", 0.0))
    recovery_ability = float(ctx.get("recovery_ability", 0.0))
    score = 100.0 * (0.4 * avg_slack_ratio + 0.3 * recovery_ability + 0.3 * (1.0 - bottleneck_concentration))
    return max(0.0, min(100.0, score))


def compute_cash_sustainability_score(ctx: Mapping[str, Any]) -> float:
    cash_conversion_pressure = float(ctx.get("cash_conversion_pressure", 0.0))
    total_profit = float(ctx.get("total_profit", 0.0))
    score = 100.0 - cash_conversion_pressure + min(20.0, total_profit / 1_000_000.0)
    return max(0.0, min(100.0, score))


def compute_structural_sustainability_score(ctx: Mapping[str, Any]) -> float:
    return weighted_average(
        [
            (float(ctx.get("profit_sustainability_score", 0.0)), 0.30),
            (float(ctx.get("inventory_soundness_score", 0.0)), 0.25),
            (float(ctx.get("capacity_resilience_score", 0.0)), 0.25),
            (float(ctx.get("cash_sustainability_score", 0.0)), 0.20),
        ],
        default=0.0,
    )


# ============================================================
# registry builder
# ============================================================

def build_kpi_registry() -> Dict[str, KPIDefinition]:
    registry: Dict[str, KPIDefinition] = {}

    def add(kpi: KPIDefinition) -> None:
        if kpi.id in registry:
            raise ValueError(f"Duplicate KPI id: {kpi.id}")
        registry[kpi.id] = kpi

    # --------------------------------------------------------
    # Level 1: node
    # --------------------------------------------------------
    add(KPIDefinition(
        id="node.production_qty",
        label="Node Production Qty",
        level="node",
        scope="node",
        value_type="qty",
        unit="qty",
        grain=("product", "node", "week"),
        description="当該 node の週次生産・調達投入量",
        formula_text="P_qty(node, week)",
        depends_on=("P_qty",),
        display_places=("Node PSI Graph", "Node KPI Panel"),
        tags=("psi", "quantity"),
        compute_fn=compute_node_production_qty,
    ))
    add(KPIDefinition(
        id="node.shipment_qty",
        label="Node Shipment/Sales Qty",
        level="node",
        scope="node",
        value_type="qty",
        unit="qty",
        grain=("product", "node", "week"),
        description="当該 node の週次出荷・販売量",
        formula_text="S_qty(node, week)",
        depends_on=("S_qty",),
        display_places=("Node PSI Graph", "Node KPI Panel"),
        tags=("psi", "quantity"),
        compute_fn=compute_node_shipment_qty,
    ))
    add(KPIDefinition(
        id="node.ending_inventory_qty",
        label="Node Ending Inventory Qty",
        level="node",
        scope="node",
        value_type="qty",
        unit="qty",
        grain=("product", "node", "week"),
        description="週末在庫量",
        formula_text="I_begin + P - S",
        depends_on=("I_begin", "P_qty", "S_qty"),
        display_places=("Node PSI Graph", "Node KPI Panel"),
        tags=("psi", "inventory"),
        compute_fn=compute_node_ending_inventory_qty,
    ))
    add(KPIDefinition(
        id="node.backlog_qty",
        label="Node Backlog Qty",
        level="node",
        scope="node",
        value_type="qty",
        unit="qty",
        grain=("product", "node", "week"),
        description="未充足需要量",
        formula_text="backlog_begin + demand - served",
        depends_on=("backlog_begin", "demand_qty", "served_qty"),
        display_places=("Node KPI Panel", "Alert Panel"),
        tags=("service", "backlog"),
        compute_fn=compute_node_backlog_qty,
    ))
    add(KPIDefinition(
        id="node.capacity_utilization",
        label="Node Capacity Utilization",
        level="node",
        scope="node",
        value_type="ratio",
        unit="%",
        grain=("product", "node", "week"),
        description="能力使用率",
        formula_text="used_qty / cap_qty",
        depends_on=("used_qty", "cap_qty"),
        display_places=("Capacity Panel", "Heatmap"),
        tags=("capacity",),
        compute_fn=compute_node_capacity_utilization,
    ))
    add(KPIDefinition(
        id="node.stockout_qty",
        label="Node Stockout Qty",
        level="node",
        scope="node",
        value_type="qty",
        unit="qty",
        grain=("product", "node", "week"),
        description="欠品数量",
        formula_text="max(0, demand_qty - served_qty)",
        depends_on=("demand_qty", "served_qty"),
        display_places=("Alert Panel", "Node KPI Panel"),
        tags=("service", "stockout"),
        compute_fn=compute_node_stockout_qty,
    ))
    add(KPIDefinition(
        id="node.fill_rate",
        label="Node Fill Rate",
        level="node",
        scope="node",
        value_type="ratio",
        unit="%",
        grain=("product", "node", "week"),
        description="需要充足率",
        formula_text="served_qty / demand_qty",
        depends_on=("demand_qty", "served_qty"),
        display_places=("Service Panel",),
        tags=("service",),
        compute_fn=compute_node_fill_rate,
    ))
    add(KPIDefinition(
        id="node.inventory_days",
        label="Node Inventory Days",
        level="node",
        scope="node",
        value_type="days",
        unit="days",
        grain=("product", "node", "week"),
        description="在庫日数",
        formula_text="I_end / avg_weekly_sales",
        depends_on=("I_end", "avg_weekly_sales"),
        display_places=("Node KPI Panel",),
        tags=("inventory",),
        compute_fn=compute_node_inventory_days,
    ))
    add(KPIDefinition(
        id="node.sales_amount",
        label="Node Sales Amount",
        level="node",
        scope="node",
        value_type="amount",
        unit="JPY",
        grain=("product", "node", "week"),
        description="当該 node の売上金額",
        formula_text="S_qty * sales_price",
        depends_on=("S_qty", "sales_price"),
        display_places=("Financial Panel",),
        tags=("financial", "sales"),
        compute_fn=compute_node_sales_amount,
    ))
    add(KPIDefinition(
        id="node.purchase_cost",
        label="Node Purchase Cost",
        level="node",
        scope="node",
        value_type="amount",
        unit="JPY",
        grain=("product", "node", "week"),
        description="購買費",
        formula_text="purchase_qty * purchase_unit_cost",
        depends_on=("purchase_qty", "purchase_unit_cost"),
        display_places=("Financial Panel",),
        tags=("financial", "cost"),
        compute_fn=compute_node_purchase_cost,
    ))
    add(KPIDefinition(
        id="node.production_cost",
        label="Node Production Cost",
        level="node",
        scope="node",
        value_type="amount",
        unit="JPY",
        grain=("product", "node", "week"),
        description="生産費",
        formula_text="P_qty * production_unit_cost",
        depends_on=("P_qty", "production_unit_cost"),
        display_places=("Financial Panel",),
        tags=("financial", "cost"),
        compute_fn=compute_node_production_cost,
    ))
    add(KPIDefinition(
        id="node.logistics_cost",
        label="Node Logistics Cost",
        level="node",
        scope="node",
        value_type="amount",
        unit="JPY",
        grain=("product", "node", "week"),
        description="物流費",
        formula_text="ship_qty * logistics_unit_cost",
        depends_on=("ship_qty", "logistics_unit_cost"),
        display_places=("Financial Panel",),
        tags=("financial", "cost"),
        compute_fn=compute_node_logistics_cost,
    ))
    add(KPIDefinition(
        id="node.inventory_holding_cost",
        label="Node Inventory Holding Cost",
        level="node",
        scope="node",
        value_type="amount",
        unit="JPY",
        grain=("product", "node", "week"),
        description="在庫保管費",
        formula_text="avg_inventory * holding_cost_rate",
        depends_on=("avg_inventory", "holding_cost_rate"),
        display_places=("Financial Panel",),
        tags=("financial", "inventory"),
        compute_fn=compute_node_inventory_holding_cost,
    ))
    add(KPIDefinition(
        id="node.gross_profit_contribution",
        label="Node Gross Profit Contribution",
        level="node",
        scope="node",
        value_type="amount",
        unit="JPY",
        grain=("product", "node", "week"),
        description="粗利貢献",
        formula_text="sales_amount - purchase_cost - production_cost - logistics_cost - inventory_cost",
        depends_on=("sales_amount", "purchase_cost", "production_cost", "logistics_cost", "inventory_holding_cost"),
        display_places=("Profit Panel",),
        tags=("financial", "profit"),
        compute_fn=compute_node_gross_profit_contribution,
    ))
    add(KPIDefinition(
        id="node.event_count",
        label="Node Event Count",
        level="node",
        scope="node",
        value_type="count",
        unit="count",
        grain=("product", "node", "week"),
        description="発生イベント総数",
        formula_text="count(events)",
        depends_on=("events",),
        display_places=("Event Panel",),
        tags=("event",),
        compute_fn=compute_node_event_count,
    ))
    add(KPIDefinition(
        id="node.bottleneck_event_count",
        label="Node Bottleneck Event Count",
        level="node",
        scope="node",
        value_type="count",
        unit="count",
        grain=("product", "node", "week"),
        description="能力逼迫イベント数",
        formula_text="count(event_type == bottleneck)",
        depends_on=("events",),
        display_places=("Event Panel", "Debug Panel"),
        tags=("event", "bottleneck"),
        compute_fn=compute_node_bottleneck_event_count,
    ))
    add(KPIDefinition(
        id="node.stockout_event_count",
        label="Node Stockout Event Count",
        level="node",
        scope="node",
        value_type="count",
        unit="count",
        grain=("product", "node", "week"),
        description="欠品イベント数",
        formula_text="count(event_type == stockout)",
        depends_on=("events",),
        display_places=("Event Panel",),
        tags=("event", "stockout"),
        compute_fn=compute_node_stockout_event_count,
    ))
    add(KPIDefinition(
        id="node.trust_event_score",
        label="Node TrustEvent Score",
        level="node",
        scope="node",
        value_type="score",
        unit="score",
        grain=("product", "node", "week"),
        description="node単位の健全性評価",
        formula_text="weighted_event_score",
        depends_on=("bottleneck_event_count", "stockout_event_count", "stagnation_event_count"),
        display_places=("Trust Panel",),
        tags=("trust", "health"),
        compute_fn=compute_node_trust_event_score,
    ))

    # --------------------------------------------------------
    # Level 2: supply_point inbound
    # --------------------------------------------------------
    add(KPIDefinition(
        id="supply_point.inbound_receipt_qty",
        label="Inbound Receipt Qty",
        level="supply_point",
        scope="supply_point_inbound",
        value_type="qty",
        unit="qty",
        grain=("product", "supply_point", "week"),
        description="supply_point に到達した入荷量",
        formula_text="sum(inbound_receipts)",
        depends_on=("inbound_receipt_qty",),
        display_places=("SupplyPoint KPI Panel",),
        tags=("inbound", "quantity"),
        compute_fn=compute_inbound_receipt_qty,
    ))
    add(KPIDefinition(
        id="supply_point.inbound_capacity_utilization",
        label="Inbound Capacity Utilization",
        level="supply_point",
        scope="supply_point_inbound",
        value_type="ratio",
        unit="%",
        grain=("product", "supply_point", "week"),
        description="Inbound側能力使用率",
        formula_text="sum(used_qty) / sum(cap_qty)",
        depends_on=("inbound_used_qty", "inbound_cap_qty"),
        display_places=("SupplyPoint KPI Panel",),
        tags=("inbound", "capacity"),
        compute_fn=compute_inbound_capacity_utilization,
    ))
    add(KPIDefinition(
        id="supply_point.inbound_material_shortage_qty",
        label="Inbound Material Shortage Qty",
        level="supply_point",
        scope="supply_point_inbound",
        value_type="qty",
        unit="qty",
        grain=("product", "supply_point", "week"),
        description="部材不足量",
        formula_text="required_input_qty - available_input_qty",
        depends_on=("required_input_qty", "available_input_qty"),
        display_places=("SupplyPoint Alert Panel",),
        tags=("inbound", "shortage"),
        compute_fn=compute_inbound_material_shortage_qty,
    ))

    # --------------------------------------------------------
    # Level 2: supply_point outbound
    # --------------------------------------------------------
    add(KPIDefinition(
        id="supply_point.outbound_shipment_qty",
        label="Outbound Shipment Qty",
        level="supply_point",
        scope="supply_point_outbound",
        value_type="qty",
        unit="qty",
        grain=("product", "supply_point", "week"),
        description="市場・下流への出荷量",
        formula_text="sum(outbound shipments)",
        depends_on=("outbound_shipment_qty",),
        display_places=("SupplyPoint KPI Panel",),
        tags=("outbound", "quantity"),
        compute_fn=compute_outbound_shipment_qty,
    ))
    add(KPIDefinition(
        id="supply_point.outbound_demand_qty",
        label="Outbound Demand Qty",
        level="supply_point",
        scope="supply_point_outbound",
        value_type="qty",
        unit="qty",
        grain=("product", "supply_point", "week"),
        description="受けた総需要量",
        formula_text="sum(requested demand)",
        depends_on=("outbound_demand_qty",),
        display_places=("SupplyPoint KPI Panel",),
        tags=("outbound", "demand"),
        compute_fn=compute_outbound_demand_qty,
    ))
    add(KPIDefinition(
        id="supply_point.outbound_sales_qty",
        label="Outbound Sales Qty",
        level="supply_point",
        scope="supply_point_outbound",
        value_type="qty",
        unit="qty",
        grain=("product", "supply_point", "week"),
        description="最終需要充足量",
        formula_text="sum(served demand)",
        depends_on=("outbound_sales_qty",),
        display_places=("SupplyPoint KPI Panel",),
        tags=("outbound", "sales"),
        compute_fn=compute_outbound_sales_qty,
    ))
    add(KPIDefinition(
        id="supply_point.outbound_fill_rate",
        label="Outbound Fill Rate",
        level="supply_point",
        scope="supply_point_outbound",
        value_type="ratio",
        unit="%",
        grain=("product", "supply_point", "week"),
        description="需要充足率",
        formula_text="served_qty / demand_qty",
        depends_on=("outbound_sales_qty", "outbound_demand_qty"),
        display_places=("SupplyPoint Service Panel",),
        tags=("outbound", "service"),
        compute_fn=compute_outbound_fill_rate,
    ))
    add(KPIDefinition(
        id="supply_point.outbound_stockout_qty",
        label="Outbound Stockout Qty",
        level="supply_point",
        scope="supply_point_outbound",
        value_type="qty",
        unit="qty",
        grain=("product", "supply_point", "week"),
        description="欠品量",
        formula_text="demand_qty - served_qty",
        depends_on=("outbound_demand_qty", "outbound_sales_qty"),
        display_places=("SupplyPoint Alert Panel",),
        tags=("outbound", "stockout"),
        compute_fn=compute_outbound_stockout_qty,
    ))
    add(KPIDefinition(
        id="supply_point.market_priority_compliance",
        label="Market Priority Compliance",
        level="supply_point",
        scope="supply_point_outbound",
        value_type="ratio",
        unit="%",
        grain=("product", "supply_point", "week"),
        description="優先度ルール遵守率",
        formula_text="priority-compliant allocated qty / total allocated qty",
        depends_on=("priority_compliant_allocated_qty", "total_allocated_qty"),
        display_places=("Allocation Panel",),
        tags=("outbound", "allocation"),
        compute_fn=compute_market_priority_compliance,
    ))

    # --------------------------------------------------------
    # Level 2: supply_point integrated
    # --------------------------------------------------------
    add(KPIDefinition(
        id="supply_point.demand_supply_gap_qty",
        label="Demand-Supply Gap Qty",
        level="supply_point",
        scope="supply_point_integrated",
        value_type="qty",
        unit="qty",
        grain=("product", "supply_point", "week"),
        description="需給ギャップ量",
        formula_text="demand_qty - feasible_supply_qty",
        depends_on=("outbound_demand_qty", "feasible_supply_qty"),
        display_places=("Integrated KPI Panel",),
        tags=("integrated", "balance"),
        compute_fn=compute_demand_supply_gap_qty,
    ))
    add(KPIDefinition(
        id="supply_point.demand_supply_gap_rate",
        label="Demand-Supply Gap Rate",
        level="supply_point",
        scope="supply_point_integrated",
        value_type="ratio",
        unit="%",
        grain=("product", "supply_point", "week"),
        description="需給ギャップ率",
        formula_text="(demand - feasible_supply) / demand",
        depends_on=("outbound_demand_qty", "feasible_supply_qty"),
        display_places=("Integrated KPI Panel",),
        tags=("integrated", "balance"),
        compute_fn=compute_demand_supply_gap_rate,
    ))
    add(KPIDefinition(
        id="supply_point.decoupling_inventory_qty",
        label="Decoupling Inventory Qty",
        level="supply_point",
        scope="supply_point_integrated",
        value_type="qty",
        unit="qty",
        grain=("product", "supply_point", "week"),
        description="デカップリング点在庫",
        formula_text="I_end at supply_point",
        depends_on=("decoupling_inventory_qty",),
        display_places=("Inventory Panel",),
        tags=("integrated", "inventory"),
        compute_fn=compute_decoupling_inventory_qty,
    ))
    add(KPIDefinition(
        id="supply_point.decoupling_inventory_health",
        label="Decoupling Inventory Health",
        level="supply_point",
        scope="supply_point_integrated",
        value_type="score",
        unit="score",
        grain=("product", "supply_point", "week"),
        description="在庫健全性",
        formula_text="score(buffer_min <= I <= buffer_max)",
        depends_on=("decoupling_inventory_qty", "buffer_min", "buffer_max"),
        display_places=("Health Panel",),
        tags=("integrated", "inventory", "health"),
        compute_fn=compute_decoupling_inventory_health,
    ))
    add(KPIDefinition(
        id="supply_point.allocation_efficiency",
        label="Allocation Efficiency",
        level="supply_point",
        scope="supply_point_integrated",
        value_type="ratio",
        unit="score",
        grain=("product", "supply_point", "week"),
        description="供給配分効率",
        formula_text="value_served / available_supply_qty",
        depends_on=("value_served", "available_supply_qty"),
        display_places=("Allocation Panel",),
        tags=("integrated", "allocation"),
        compute_fn=compute_allocation_efficiency,
    ))
    add(KPIDefinition(
        id="supply_point.bottleneck_impact_qty",
        label="Bottleneck Impact Qty",
        level="supply_point",
        scope="supply_point_integrated",
        value_type="qty",
        unit="qty",
        grain=("product", "supply_point", "week"),
        description="ボトルネック影響量",
        formula_text="lost_qty attributable to bottleneck",
        depends_on=("bottleneck_impact_qty",),
        display_places=("Bottleneck Panel",),
        tags=("integrated", "bottleneck"),
        compute_fn=compute_bottleneck_impact_qty,
    ))
    add(KPIDefinition(
        id="supply_point.weekly_psi_balance_score",
        label="Weekly PSI Balance Score",
        level="supply_point",
        scope="supply_point_integrated",
        value_type="score",
        unit="score",
        grain=("product", "supply_point", "week"),
        description="P/S/Iバランス健全性",
        formula_text="f(balance of P,S,I,backlog)",
        depends_on=("P_qty", "S_qty", "backlog_qty", "I_end"),
        display_places=("Health Panel",),
        tags=("integrated", "psi", "health"),
        compute_fn=compute_weekly_psi_balance_score,
    ))
    add(KPIDefinition(
        id="supply_point.profit_contribution",
        label="SupplyPoint Profit Contribution",
        level="supply_point",
        scope="supply_point_integrated",
        value_type="amount",
        unit="JPY",
        grain=("product", "supply_point", "week"),
        description="supply_point単位利益貢献",
        formula_text="sales - purchase - production - logistics - inventory cost",
        depends_on=("sales_amount", "purchase_cost", "production_cost", "logistics_cost", "inventory_holding_cost"),
        display_places=("Profit Panel",),
        tags=("integrated", "financial", "profit"),
        compute_fn=compute_supply_point_profit_contribution,
    ))
    add(KPIDefinition(
        id="supply_point.cash_pressure",
        label="SupplyPoint Cash Pressure",
        level="supply_point",
        scope="supply_point_integrated",
        value_type="amount",
        unit="JPY",
        grain=("product", "supply_point", "week"),
        description="キャッシュ圧迫度",
        formula_text="inventory_value + receivable_lag_effect - payable_lag_effect",
        depends_on=("inventory_value", "receivable_lag_effect", "payable_lag_effect"),
        display_places=("Financial Panel",),
        tags=("integrated", "financial", "cash"),
        compute_fn=compute_supply_point_cash_pressure,
    ))

    # --------------------------------------------------------
    # Level 3: total supply chain
    # --------------------------------------------------------
    add(KPIDefinition(
        id="total_sc.production_qty",
        label="Total Production Qty",
        level="total_sc",
        scope="total_sc",
        value_type="qty",
        unit="qty",
        grain=("product", "week"),
        description="全体生産・調達量",
        formula_text="sum(P_qty over all nodes)",
        depends_on=("total_production_qty",),
        display_places=("Total SC Dashboard",),
        tags=("total", "psi"),
        compute_fn=compute_total_production_qty,
    ))
    add(KPIDefinition(
        id="total_sc.shipment_sales_qty",
        label="Total Shipment/Sales Qty",
        level="total_sc",
        scope="total_sc",
        value_type="qty",
        unit="qty",
        grain=("product", "week"),
        description="全体出荷・販売量",
        formula_text="sum(final market sales)",
        depends_on=("total_sales_qty",),
        display_places=("Total SC Dashboard",),
        tags=("total", "psi"),
        compute_fn=compute_total_shipment_sales_qty,
    ))
    add(KPIDefinition(
        id="total_sc.ending_inventory_qty",
        label="Total Ending Inventory Qty",
        level="total_sc",
        scope="total_sc",
        value_type="qty",
        unit="qty",
        grain=("product", "week"),
        description="全体在庫量",
        formula_text="sum(I_end over inventory-holding nodes)",
        depends_on=("total_inventory_qty",),
        display_places=("Total SC Dashboard",),
        tags=("total", "inventory"),
        compute_fn=compute_total_ending_inventory_qty,
    ))
    add(KPIDefinition(
        id="total_sc.backlog_qty",
        label="Total Backlog Qty",
        level="total_sc",
        scope="total_sc",
        value_type="qty",
        unit="qty",
        grain=("product", "week"),
        description="全体未充足需要",
        formula_text="sum(backlog_end)",
        depends_on=("total_backlog_qty",),
        display_places=("Total SC Dashboard",),
        tags=("total", "service"),
        compute_fn=compute_total_backlog_qty,
    ))
    add(KPIDefinition(
        id="total_sc.fill_rate",
        label="Total Fill Rate",
        level="total_sc",
        scope="total_sc",
        value_type="ratio",
        unit="%",
        grain=("product", "week"),
        description="全体充足率",
        formula_text="sum(served demand) / sum(total demand)",
        depends_on=("total_served_qty", "total_demand_qty"),
        display_places=("Total SC Dashboard",),
        tags=("total", "service"),
        compute_fn=compute_total_fill_rate,
    ))
    add(KPIDefinition(
        id="total_sc.stockout_rate",
        label="Total Stockout Rate",
        level="total_sc",
        scope="total_sc",
        value_type="ratio",
        unit="%",
        grain=("product", "week"),
        description="全体欠品率",
        formula_text="sum(stockout_qty) / sum(demand_qty)",
        depends_on=("total_stockout_qty", "total_demand_qty"),
        display_places=("Total SC Dashboard",),
        tags=("total", "service"),
        compute_fn=compute_total_stockout_rate,
    ))
    add(KPIDefinition(
        id="total_sc.inventory_value",
        label="Total Inventory Value",
        level="total_sc",
        scope="total_sc",
        value_type="amount",
        unit="JPY",
        grain=("product", "week"),
        description="総在庫金額",
        formula_text="sum(inventory_qty * unit_value)",
        depends_on=("total_inventory_value",),
        display_places=("Total Financial Dashboard",),
        tags=("total", "financial", "inventory"),
        compute_fn=compute_total_inventory_value,
    ))
    add(KPIDefinition(
        id="total_sc.capacity_utilization",
        label="Total Capacity Utilization",
        level="total_sc",
        scope="total_sc",
        value_type="ratio",
        unit="%",
        grain=("product", "week"),
        description="全体能力使用率",
        formula_text="sum(used_qty) / sum(cap_qty)",
        depends_on=("total_used_qty", "total_cap_qty"),
        display_places=("Capacity Dashboard",),
        tags=("total", "capacity"),
        compute_fn=compute_total_capacity_utilization,
    ))
    add(KPIDefinition(
        id="total_sc.capacity_concentration_index",
        label="Capacity Concentration Index",
        level="total_sc",
        scope="total_sc",
        value_type="score",
        unit="index",
        grain=("product", "week"),
        description="能力偏在指数",
        formula_text="max(node utilization) / avg(utilization)",
        depends_on=("max_node_utilization", "avg_node_utilization"),
        display_places=("Bottleneck Dashboard",),
        tags=("total", "capacity", "bottleneck"),
        compute_fn=compute_capacity_concentration_index,
    ))
    add(KPIDefinition(
        id="total_sc.lead_time",
        label="Total Lead Time",
        level="total_sc",
        scope="total_sc",
        value_type="days",
        unit="days",
        grain=("product", "horizon"),
        description="全体リードタイム",
        formula_text="avg(end-to-end lead time by lot/order)",
        depends_on=("avg_end_to_end_lead_time",),
        display_places=("Flow Dashboard",),
        tags=("total", "flow"),
        compute_fn=compute_total_lead_time,
    ))
    add(KPIDefinition(
        id="total_sc.plan_stability_score",
        label="Plan Stability Score",
        level="total_sc",
        scope="total_sc",
        value_type="score",
        unit="score",
        grain=("product", "horizon"),
        description="計画安定性",
        formula_text="1 - replanned_qty / planned_qty",
        depends_on=("replanned_qty", "planned_qty"),
        display_places=("Planning Dashboard",),
        tags=("total", "planning"),
        compute_fn=compute_plan_stability_score,
    ))
    add(KPIDefinition(
        id="total_sc.sales_amount",
        label="Total Sales Amount",
        level="total_sc",
        scope="total_sc",
        value_type="amount",
        unit="JPY",
        grain=("product", "week"),
        description="総売上",
        formula_text="sum(final sales amount)",
        depends_on=("total_sales_amount",),
        display_places=("Profit Dashboard",),
        tags=("total", "financial", "sales"),
        compute_fn=compute_total_sales_amount,
    ))
    add(KPIDefinition(
        id="total_sc.variable_cost",
        label="Total Variable Cost",
        level="total_sc",
        scope="total_sc",
        value_type="amount",
        unit="JPY",
        grain=("product", "week"),
        description="総変動費",
        formula_text="sum(purchase + production + logistics + holding)",
        depends_on=("total_variable_cost",),
        display_places=("Profit Dashboard",),
        tags=("total", "financial", "cost"),
        compute_fn=compute_total_variable_cost,
    ))
    add(KPIDefinition(
        id="total_sc.gross_profit",
        label="Total Gross Profit",
        level="total_sc",
        scope="total_sc",
        value_type="amount",
        unit="JPY",
        grain=("product", "week"),
        description="総粗利",
        formula_text="sales - variable_cost",
        depends_on=("total_sales_amount", "total_variable_cost"),
        display_places=("Profit Dashboard",),
        tags=("total", "financial", "profit"),
        compute_fn=compute_total_gross_profit,
    ))
    add(KPIDefinition(
        id="total_sc.operating_profit",
        label="Total Operating Profit",
        level="total_sc",
        scope="total_sc",
        value_type="amount",
        unit="JPY",
        grain=("product", "week"),
        description="総営業利益",
        formula_text="gross_profit - fixed_cost",
        depends_on=("total_gross_profit", "fixed_cost"),
        display_places=("Profit Dashboard",),
        tags=("total", "financial", "profit"),
        compute_fn=compute_total_operating_profit,
    ))
    add(KPIDefinition(
        id="total_sc.profit_margin",
        label="Total Profit Margin",
        level="total_sc",
        scope="total_sc",
        value_type="ratio",
        unit="%",
        grain=("product", "week"),
        description="利益率",
        formula_text="operating_profit / sales",
        depends_on=("total_operating_profit", "total_sales_amount"),
        display_places=("Profit Dashboard",),
        tags=("total", "financial", "profit"),
        compute_fn=compute_total_profit_margin,
    ))
    add(KPIDefinition(
        id="total_sc.cash_conversion_pressure",
        label="Cash Conversion Pressure",
        level="total_sc",
        scope="total_sc",
        value_type="days",
        unit="days",
        grain=("product", "horizon"),
        description="キャッシュ循環圧力",
        formula_text="inventory_days + receivable_days - payable_days",
        depends_on=("inventory_days", "receivable_days", "payable_days"),
        display_places=("Financial Dashboard",),
        tags=("total", "financial", "cash"),
        compute_fn=compute_cash_conversion_pressure,
    ))
    add(KPIDefinition(
        id="total_sc.roi_proxy",
        label="Supply Chain ROI Proxy",
        level="total_sc",
        scope="total_sc",
        value_type="ratio",
        unit="%",
        grain=("product", "horizon"),
        description="供給網投資効率の近似指標",
        formula_text="operating_profit / invested_capital_proxy",
        depends_on=("total_operating_profit", "invested_capital_proxy"),
        display_places=("Executive Dashboard",),
        tags=("total", "financial", "roi"),
        compute_fn=compute_supply_chain_roi_proxy,
    ))

    # --------------------------------------------------------
    # Level 4: strategic
    # --------------------------------------------------------
    add(KPIDefinition(
        id="strategic.customer_fulfillment_score",
        label="Customer Fulfillment Score",
        level="strategic",
        scope="strategic",
        value_type="score",
        unit="score",
        grain=("product", "market", "horizon"),
        description="顧客が必要な時に入手できる度合い",
        formula_text="w1*fill_rate + w2*OTIF - w3*stockout_rate",
        depends_on=("fill_rate", "otif", "stockout_rate"),
        display_places=("Strategic Dashboard",),
        tags=("strategic", "customer"),
        compute_fn=compute_customer_fulfillment_score,
    ))
    add(KPIDefinition(
        id="strategic.employee_workload_health_score",
        label="Employee Workload Health Score",
        level="strategic",
        scope="strategic",
        value_type="score",
        unit="score",
        grain=("node_group", "horizon"),
        description="従業員への過負荷抑制度",
        formula_text="1 - over_capacity_ratio",
        depends_on=("over_capacity_ratio",),
        display_places=("Strategic Dashboard",),
        tags=("strategic", "employee"),
        compute_fn=compute_employee_workload_health_score,
    ))
    add(KPIDefinition(
        id="strategic.supplier_stability_score",
        label="Supplier Stability Score",
        level="strategic",
        scope="strategic",
        value_type="score",
        unit="score",
        grain=("supplier", "horizon"),
        description="サプライヤーへの変動押し付け抑制度",
        formula_text="1 - abrupt_order_change_ratio",
        depends_on=("abrupt_order_change_ratio",),
        display_places=("Strategic Dashboard",),
        tags=("strategic", "supplier"),
        compute_fn=compute_supplier_stability_score,
    ))
    add(KPIDefinition(
        id="strategic.balanced_stakeholder_score",
        label="Balanced Stakeholder Score",
        level="strategic",
        scope="strategic",
        value_type="score",
        unit="score",
        grain=("total_sc", "horizon"),
        description="顧客・従業員・サプライヤーの総合健全度",
        formula_text="weighted avg of stakeholder scores",
        depends_on=("customer_fulfillment_score", "employee_workload_health_score", "supplier_stability_score"),
        display_places=("Executive Dashboard",),
        tags=("strategic", "stakeholder"),
        compute_fn=compute_balanced_stakeholder_score,
    ))
    add(KPIDefinition(
        id="strategic.profit_sustainability_score",
        label="Profit Sustainability Score",
        level="strategic",
        scope="strategic",
        value_type="score",
        unit="score",
        grain=("total_sc", "horizon"),
        description="利益構造の持続性",
        formula_text="f(profit_margin, volatility, stability)",
        depends_on=("profit_margin", "profit_volatility"),
        display_places=("Executive Dashboard",),
        tags=("strategic", "sustainability", "profit"),
        compute_fn=compute_profit_sustainability_score,
    ))
    add(KPIDefinition(
        id="strategic.inventory_soundness_score",
        label="Inventory Soundness Score",
        level="strategic",
        scope="strategic",
        value_type="score",
        unit="score",
        grain=("total_sc", "horizon"),
        description="在庫構造の健全性",
        formula_text="f(inventory_days, obsolescence risk, buffer health)",
        depends_on=("inventory_days", "obsolescence_risk", "buffer_health"),
        display_places=("Executive Dashboard",),
        tags=("strategic", "sustainability", "inventory"),
        compute_fn=compute_inventory_soundness_score,
    ))
    add(KPIDefinition(
        id="strategic.capacity_resilience_score",
        label="Capacity Resilience Score",
        level="strategic",
        scope="strategic",
        value_type="score",
        unit="score",
        grain=("total_sc", "horizon"),
        description="能力構造の強靭性",
        formula_text="f(avg slack, bottleneck concentration, recovery ability)",
        depends_on=("avg_slack_ratio", "bottleneck_concentration", "recovery_ability"),
        display_places=("Executive Dashboard",),
        tags=("strategic", "sustainability", "capacity"),
        compute_fn=compute_capacity_resilience_score,
    ))
    add(KPIDefinition(
        id="strategic.cash_sustainability_score",
        label="Cash Sustainability Score",
        level="strategic",
        scope="strategic",
        value_type="score",
        unit="score",
        grain=("total_sc", "horizon"),
        description="資金循環の持続性",
        formula_text="f(cash conversion pressure, inventory value, profit)",
        depends_on=("cash_conversion_pressure", "total_profit"),
        display_places=("Executive Dashboard",),
        tags=("strategic", "sustainability", "cash"),
        compute_fn=compute_cash_sustainability_score,
    ))
    add(KPIDefinition(
        id="strategic.structural_sustainability_score",
        label="Structural Sustainability Score",
        level="strategic",
        scope="strategic",
        value_type="score",
        unit="score",
        grain=("total_sc", "horizon"),
        description="経営構造の持続可能性総合評価",
        formula_text="weighted avg of sustainability sub-scores",
        depends_on=(
            "profit_sustainability_score",
            "inventory_soundness_score",
            "capacity_resilience_score",
            "cash_sustainability_score",
        ),
        display_places=("Board Dashboard",),
        tags=("strategic", "sustainability"),
        compute_fn=compute_structural_sustainability_score,
    ))

    return registry


KPI_REGISTRY: Dict[str, KPIDefinition] = build_kpi_registry()


# ============================================================
# helper APIs
# ============================================================

def get_kpi_definition(kpi_id: str) -> KPIDefinition:
    try:
        return KPI_REGISTRY[kpi_id]
    except KeyError as exc:
        raise KeyError(f"Unknown KPI id: {kpi_id}") from exc


def list_kpis(
    *,
    level: Optional[KPILevel] = None,
    scope: Optional[KPIScope] = None,
    tags: Optional[Iterable[str]] = None,
    enabled_only: bool = True,
) -> list[KPIDefinition]:
    tag_set = set(tags or [])
    items = list(KPI_REGISTRY.values())

    if enabled_only:
        items = [k for k in items if k.enabled]
    if level is not None:
        items = [k for k in items if k.level == level]
    if scope is not None:
        items = [k for k in items if k.scope == scope]
    if tag_set:
        items = [k for k in items if tag_set.intersection(k.tags)]

    return items


def evaluate_kpi(kpi_id: str, ctx: Mapping[str, Any]) -> Optional[float]:
    kpi = get_kpi_definition(kpi_id)
    if kpi.compute_fn is None:
        return None
    return kpi.compute_fn(ctx)
```

---

# この registry の使い方イメージ

```python
from pysi.kpi.kpi_registry import evaluate_kpi, KPI_REGISTRY

ctx = {
    "P_qty": 120,
    "S_qty": 100,
    "I_begin": 30,
    "demand_qty": 110,
    "served_qty": 100,
    "used_qty": 120,
    "cap_qty": 150,
}

ending_inventory = evaluate_kpi("node.ending_inventory_qty", ctx)
fill_rate = evaluate_kpi("node.fill_rate", ctx)
capacity_util = evaluate_kpi("node.capacity_utilization", ctx)

print(ending_inventory)   # 50
print(fill_rate)          # 0.9090...
print(capacity_util)      # 0.8
```

---

# WOM に合わせた設計上のポイント

## 1. `level` と `scope` を分けている

`level="supply_point"` だけだと、

* inbound
* outbound
* integrated

の区別が埋もれます。

そこで `scope` を分けてあります。

これで例えば、

```python
list_kpis(level="supply_point", scope="supply_point_integrated")
```

のように、**需給統合KPIだけ**をUIに出せます。

---

## 2. `formula_text` を registry に持たせている

これは地味に効きます。
将来、

* 画面 tooltip
* 設計書自動生成
* KPI定義CSV出力
* 開発者向け debug 表示

にそのまま使えます。

つまり、registry が **コードと設計書の接点** になります。

---

## 3. `depends_on` を持たせている

ここは後でかなり役に立ちます。

たとえば、

* 生 raw input に依存するKPI
* 他のKPIを前提にするKPI
* 再計算順序の制御

を整理できます。

将来的にはこれを使って、
**KPI dependency graph** を作れます。

---

## 4. `compute_fn` は今は簡易、後で WOM 実データに接続

今の `compute_fn` は、`ctx` から値を読むだけの軽量版です。
将来は、

* `ctx` に node object を渡す
* env / snapshot / aggregate result を渡す
* event store から派生計算する

形に置き換えられます。

つまり今は、**canonical KPI 定義の器を先に作る段階**です。

---

# 次に置くときれいな companion file

この `kpi_registry.py` の次に、相性が良いのは次の2つです。

## 1. `kpi_storage.py`

責務:

* 計算結果を保持する
* grain ごとに保存する

例:

```python
node_kpi[(product, node, week)][kpi_id] = value
supply_point_kpi[(product, supply_point, week)][kpi_id] = value
total_sc_kpi[(product, week)][kpi_id] = value
strategic_kpi[(product, horizon)][kpi_id] = value
```

## 2. `kpi_engine.py`

責務:

* registry を見て KPI を評価する
* node → supply_point → total_sc → strategic の順で再計算する

---

# 初版として特に重要なKPI ID

最初に画面へつなぐなら、このあたりが効きます。

```python
PRIORITY_KPI_IDS = [
    "node.production_qty",
    "node.shipment_qty",
    "node.ending_inventory_qty",
    "node.capacity_utilization",
    "node.stockout_qty",
    "supply_point.inbound_receipt_qty",
    "supply_point.outbound_fill_rate",
    "supply_point.demand_supply_gap_qty",
    "supply_point.decoupling_inventory_health",
    "supply_point.profit_contribution",
    "total_sc.inventory_value",
    "total_sc.operating_profit",
    "strategic.balanced_stakeholder_score",
    "strategic.structural_sustainability_score",
]
```

この14個で、
**現場 → 需給接点 → 全体収益 → 経営評価**
まで一気につながります。

---

# 実務上のひとこと

この registry 方式の良いところは、
KPI を if 文の森に埋めず、**定義資産として外出し**できることです。

WOM のように、

* 数量編 / 金額編
* inbound / outbound
* KPI / TrustEvent / strategic score

が増えていく世界では、
この方式にしておくと後でかなり効きます。
KPI が増えても、コードが「密林」ではなく「植物園」になります。

次に進めるなら、
**この `kpi_registry` に対応した `kpi_engine.py` の最小 skeleton** を出すのが一番自然です。
