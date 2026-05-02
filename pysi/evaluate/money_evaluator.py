from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List


@dataclass
class UnitPriceRecord:
    node_name: str
    product: str
    node_character: str
    purchase_cost_per_lot: float = 0.0
    ship_price_per_lot: float = 0.0
    inventory_unit_value_per_lot: float = 0.0
    variable_cost_per_lot: float = 0.0
    fixed_cost_per_week: float = 0.0
    fixed_cost_per_lot: float = 0.0
    value_added_cost_per_lot: float = 0.0
    logistics_cost_per_lot: float = 0.0
    inventory_handling_cost_per_lot: float = 0.0
    tax_tariff_cost_per_lot: float = 0.0
    target_profit_per_lot: float = 0.0
    price_formation_mode: str = "fallback_zero"
    tax_rate: float = 0.0


@dataclass
class WeeklyMoneyRecord:
    product: str
    node_name: str
    node_character: str
    week: int
    shipped_lots: float
    inbound_lots: float
    throughput_lots: float
    ending_inventory_lots: float
    revenue: float
    purchase_amount: float
    variable_cost: float
    fixed_cost: float
    ending_inventory_value: float
    issue_cost: float
    profit_before_tax: float
    tax: float
    profit_after_tax: float


def _safe_float(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def _walk_nodes(root: Any) -> Iterable[Any]:
    stack = [root]
    seen = set()
    while stack:
        node = stack.pop()
        if node is None:
            continue
        oid = id(node)
        if oid in seen:
            continue
        seen.add(oid)
        yield node
        for c in getattr(node, "children", []) or []:
            stack.append(c)


def _legacy_node_character(node_name: str) -> str:
    n = (node_name or "").strip().lower()
    if n == "supply_point":
        return "SUPPLY_CHAIN_OFFICE"
    if n.startswith("market"):
        return "CS"
    if n.startswith("dc"):
        return "DAD"
    if n.startswith("plant"):
        return "MOM"
    return "unknown"


def _count_lots(x: Any) -> int:
    try:
        return len(x or [])
    except Exception:
        return 0


def _collect_product_trees(env: Any) -> Dict[str, List[Any]]:
    ot = getattr(env, "prod_tree_dict_OT", {}) or {}
    inn = getattr(env, "prod_tree_dict_IN", {}) or {}
    out: Dict[str, List[Any]] = defaultdict(list)
    for product, root in ot.items():
        if root is not None:
            out[product].append(root)
    for product, root in inn.items():
        if root is not None:
            out[product].append(root)
    return out


def _collect_node_parent_map(roots: List[Any]) -> Dict[str, str]:
    parent_of: Dict[str, str] = {}
    for root in roots:
        for node in _walk_nodes(root):
            node_name = (getattr(node, "name", "") or getattr(node, "id", "") or "").strip()
            for child in getattr(node, "children", []) or []:
                child_name = (getattr(child, "name", "") or getattr(child, "id", "") or "").strip()
                if child_name and child_name not in parent_of:
                    parent_of[child_name] = node_name
    return parent_of


def _explicit_node_price(bundle: Any, node_name: str, product: str):
    if bundle is None:
        return None
    try:
        return bundle.get_node_product_money(node_name, product)
    except Exception:
        return None


def _policy(bundle: Any, node_character: str):
    if bundle is None:
        return None
    try:
        return bundle.get_node_character_policy(node_character)
    except Exception:
        return None


def _valuation_policy(bundle: Any, product: str):
    if bundle is None:
        return None
    try:
        return bundle.get_valuation_policy(product)
    except Exception:
        return None


def _edge_price(bundle: Any, parent_name: str, child_name: str, product: str) -> float:
    if bundle is None:
        return 0.0
    try:
        rec = bundle.get_edge_product_money(parent_name, child_name, product)
    except Exception:
        rec = None
    if rec is None:
        return 0.0
    return (
        _safe_float(getattr(rec, "transfer_price_per_lot", 0.0))
        + _safe_float(getattr(rec, "freight_cost_per_lot", 0.0))
        + _safe_float(getattr(rec, "insurance_cost_per_lot", 0.0))
        + _safe_float(getattr(rec, "duty_cost_per_lot", 0.0))
        + _safe_float(getattr(rec, "handling_cost_per_lot", 0.0))
    )


def _calculate_fixed_cost_per_lot(explicit: Any, fixed_cost_per_week: float) -> float:
    explicit_fixed_per_lot = _safe_float(getattr(explicit, "fixed_cost_per_lot", 0.0)) if explicit else 0.0
    if explicit_fixed_per_lot > 0.0:
        return explicit_fixed_per_lot

    # Preferred basis is standard_volume_lots_per_week, then safe fallback 1.0.
    basis = _safe_float(getattr(explicit, "standard_volume_lots_per_week", 0.0)) if explicit else 0.0
    if basis <= 0.0:
        basis = 1.0
    return fixed_cost_per_week / basis if fixed_cost_per_week > 0.0 else 0.0


def _form_ship_price_per_lot(rec: UnitPriceRecord, explicit_ship: float) -> tuple[float, str]:
    if explicit_ship > 0.0:
        return explicit_ship, "explicit_ship_price"
    components = [
        rec.purchase_cost_per_lot,
        rec.value_added_cost_per_lot,
        rec.variable_cost_per_lot,
        rec.fixed_cost_per_lot,
        rec.logistics_cost_per_lot,
        rec.inventory_handling_cost_per_lot,
        rec.tax_tariff_cost_per_lot,
        rec.target_profit_per_lot,
    ]
    ship = sum(components)
    if ship == 0.0:
        return 0.0, "fallback_zero"
    return ship, "calculated_from_cost_components"


def _build_unit_price_table(env: Any) -> Dict[tuple[str, str], UnitPriceRecord]:
    bundle = getattr(env, "money_master_bundle", None)
    products_to_roots = _collect_product_trees(env)
    table: Dict[tuple[str, str], UnitPriceRecord] = {}

    for product, roots in products_to_roots.items():
        node_names = set()
        for root in roots:
            for node in _walk_nodes(root):
                name = (getattr(node, "name", "") or getattr(node, "id", "") or "").strip()
                if name:
                    node_names.add(name)

        parent_map = _collect_node_parent_map(roots)

        for node_name in node_names:
            node_character = None
            if bundle is not None:
                try:
                    node_character = bundle.get_node_character(node_name)
                except Exception:
                    node_character = None
            node_character = node_character or _legacy_node_character(node_name)

            explicit = _explicit_node_price(bundle, node_name, product)
            policy = _policy(bundle, node_character)
            purchase = _safe_float(getattr(explicit, "purchase_cost_per_lot", 0.0)) if explicit else 0.0
            ship = _safe_float(getattr(explicit, "ship_price_per_lot", 0.0)) if explicit else 0.0
            inventory = _safe_float(getattr(explicit, "inventory_unit_value_per_lot", 0.0)) if explicit else 0.0
            variable = _safe_float(getattr(explicit, "variable_cost_per_lot", 0.0)) if explicit else 0.0
            fixed = _safe_float(getattr(explicit, "fixed_cost_per_week", 0.0)) if explicit else 0.0
            value_added = _safe_float(getattr(explicit, "value_added_cost_per_lot", 0.0)) if explicit else 0.0
            logistics = _safe_float(getattr(explicit, "logistics_cost_per_lot", 0.0)) if explicit else 0.0
            inventory_handling = _safe_float(getattr(explicit, "inventory_handling_cost_per_lot", 0.0)) if explicit else 0.0
            target_profit = _safe_float(getattr(explicit, "target_profit_per_lot", 0.0)) if explicit else 0.0
            tax_rate = _safe_float(getattr(explicit, "tax_rate", 0.0)) if explicit else 0.0
            fixed_per_lot = _calculate_fixed_cost_per_lot(explicit, fixed)
            explicit_tax_tariff = _safe_float(getattr(explicit, "tax_tariff_cost_per_lot", 0.0)) if explicit else 0.0
            tax_base = purchase if purchase > 0.0 else ship
            tax_tariff = explicit_tax_tariff if explicit_tax_tariff > 0.0 else tax_rate * tax_base

            if tax_rate == 0.0 and policy is not None:
                tax_rate = _safe_float(getattr(policy, "default_tax_rate", 0.0))
            table[(node_name, product)] = UnitPriceRecord(
                node_name=node_name,
                product=product,
                node_character=node_character,
                purchase_cost_per_lot=purchase,
                ship_price_per_lot=ship,
                inventory_unit_value_per_lot=inventory,
                variable_cost_per_lot=variable,
                fixed_cost_per_week=fixed,
                fixed_cost_per_lot=fixed_per_lot,
                value_added_cost_per_lot=value_added,
                logistics_cost_per_lot=logistics,
                inventory_handling_cost_per_lot=inventory_handling,
                tax_tariff_cost_per_lot=tax_tariff,
                target_profit_per_lot=target_profit,
                tax_rate=tax_rate,
            )

        for _ in range(4):
            changed = False
            for node_name in sorted(node_names):
                key = (node_name, product)
                rec = table[key]
                explicit = _explicit_node_price(bundle, node_name, product)
                parent_name = parent_map.get(node_name, "")
                explicit_purchase = _safe_float(getattr(explicit, "purchase_cost_per_lot", 0.0)) if explicit else 0.0

                # Phase 2B+1: explicit non-zero child purchase cost is authoritative.
                # When explicit is missing OR explicitly zero, allow additive fallback propagation.
                if rec.purchase_cost_per_lot == 0.0 and explicit_purchase == 0.0:
                    edge_cost = _edge_price(bundle, parent_name, node_name, product)
                    if edge_cost > 0:
                        rec.purchase_cost_per_lot = edge_cost
                        changed = True
                    elif parent_name and (parent_name, product) in table:
                        parent_ship = table[(parent_name, product)].ship_price_per_lot
                        if parent_ship > 0:
                            rec.purchase_cost_per_lot = parent_ship
                            changed = True

                # MVP rule: without explicit variable-cost master field, keep 0.0 fallback.

                explicit_ship = _safe_float(getattr(explicit, "ship_price_per_lot", 0.0)) if explicit else 0.0
                if rec.tax_tariff_cost_per_lot == 0.0:
                    tax_base = rec.purchase_cost_per_lot if rec.purchase_cost_per_lot > 0.0 else explicit_ship
                    rec.tax_tariff_cost_per_lot = rec.tax_rate * tax_base
                ship, mode = _form_ship_price_per_lot(rec, explicit_ship)
                if rec.ship_price_per_lot != ship:
                    rec.ship_price_per_lot = ship
                    changed = True
                rec.price_formation_mode = mode

                if rec.inventory_unit_value_per_lot == 0.0 and explicit is None:
                    rec.inventory_unit_value_per_lot = rec.purchase_cost_per_lot
                    if rec.inventory_unit_value_per_lot > 0:
                        changed = True

            if not changed:
                break

    return table


def _build_weekly_money_rows(env: Any, price_table: Dict[tuple[str, str], UnitPriceRecord]) -> List[WeeklyMoneyRecord]:
    products_to_roots = _collect_product_trees(env)
    weekly_rows: List[WeeklyMoneyRecord] = []

    seen = set()
    for product, roots in products_to_roots.items():
        for root in roots:
            for node in _walk_nodes(root):
                node_name = (getattr(node, "name", "") or getattr(node, "id", "") or "").strip()
                if not node_name:
                    continue
                key_unique = (node_name, product)
                if key_unique in seen:
                    continue
                seen.add(key_unique)

                unit = price_table.get(key_unique)
                if unit is None:
                    continue

                psi4supply = getattr(node, "psi4supply", None) or []
                opening_inventory_lots = 0
                for week_idx, slot in enumerate(psi4supply):
                    shipped_lots = _count_lots(slot[0] if len(slot) > 0 else [])
                    inbound_lots = _count_lots(slot[1] if len(slot) > 1 else [])
                    ending_inventory_lots = _count_lots(slot[2] if len(slot) > 2 else [])
                    throughput_lots = _count_lots(slot[3] if len(slot) > 3 else [])
                    if throughput_lots == 0:
                        throughput_lots = shipped_lots

                    revenue = shipped_lots * unit.ship_price_per_lot
                    purchase_amount = inbound_lots * unit.purchase_cost_per_lot
                    variable_cost = throughput_lots * unit.variable_cost_per_lot
                    fixed_cost = unit.fixed_cost_per_week

                    ending_inventory_value = ending_inventory_lots * unit.inventory_unit_value_per_lot
                    opening_inventory_value = opening_inventory_lots * unit.inventory_unit_value_per_lot
                    inbound_inventory_value = inbound_lots * unit.inventory_unit_value_per_lot

                    bundle = getattr(env, "money_master_bundle", None)
                    valuation = _valuation_policy(bundle, product)
                    issue_method = (getattr(valuation, "issue_cost_method", "") or "").upper()
                    if issue_method == "OPENING_PLUS_INBOUND_MINUS_ENDING":
                        issue_cost = opening_inventory_value + inbound_inventory_value - ending_inventory_value
                    else:
                        issue_cost = shipped_lots * unit.inventory_unit_value_per_lot

                    profit_before_tax = revenue - issue_cost - variable_cost - fixed_cost
                    tax = max(profit_before_tax, 0.0) * unit.tax_rate
                    profit_after_tax = profit_before_tax - tax

                    weekly_rows.append(
                        WeeklyMoneyRecord(
                            product=product,
                            node_name=node_name,
                            node_character=unit.node_character,
                            week=week_idx,
                            shipped_lots=float(shipped_lots),
                            inbound_lots=float(inbound_lots),
                            throughput_lots=float(throughput_lots),
                            ending_inventory_lots=float(ending_inventory_lots),
                            revenue=revenue,
                            purchase_amount=purchase_amount,
                            variable_cost=variable_cost,
                            fixed_cost=fixed_cost,
                            ending_inventory_value=ending_inventory_value,
                            issue_cost=issue_cost,
                            profit_before_tax=profit_before_tax,
                            tax=tax,
                            profit_after_tax=profit_after_tax,
                        )
                    )
                    opening_inventory_lots = ending_inventory_lots

    return weekly_rows


def evaluate_money_by_node(env: Any) -> List[Dict[str, Any]]:
    price_table = _build_unit_price_table(env)
    weekly_rows = _build_weekly_money_rows(env, price_table)

    agg = defaultdict(
        lambda: {
            "product": "",
            "node_name": "",
            "node_character": "",
            "week_count": 0,
            "revenue": 0.0,
            "purchase_amount": 0.0,
            "variable_cost": 0.0,
            "fixed_cost": 0.0,
            "ending_inventory_value": 0.0,
            "issue_cost": 0.0,
            "profit_before_tax": 0.0,
            "tax": 0.0,
            "profit_after_tax": 0.0,
        }
    )

    for wr in weekly_rows:
        key = (wr.product, wr.node_name)
        row = agg[key]
        row["product"] = wr.product
        row["product_name"] = wr.product
        row["node_name"] = wr.node_name
        row["node_character"] = wr.node_character
        row["week_count"] += 1
        row["revenue"] += wr.revenue
        row["purchase_amount"] += wr.purchase_amount
        row["variable_cost"] += wr.variable_cost
        row["fixed_cost"] += wr.fixed_cost
        row["ending_inventory_value"] = wr.ending_inventory_value
        row["issue_cost"] += wr.issue_cost
        row["profit_before_tax"] += wr.profit_before_tax
        row["tax"] += wr.tax
        row["profit_after_tax"] += wr.profit_after_tax

    out = []
    for (product, node_name), row in sorted(agg.items()):
        unit = price_table.get((node_name, product))
        if unit is not None:
            row.update(
                {
                    "purchase_cost_per_lot": unit.purchase_cost_per_lot,
                    "ship_price_per_lot": unit.ship_price_per_lot,
                    "inventory_unit_value_per_lot": unit.inventory_unit_value_per_lot,
                    "variable_cost_per_lot": unit.variable_cost_per_lot,
                    "fixed_cost_per_week": unit.fixed_cost_per_week,
                    "fixed_cost_per_lot": unit.fixed_cost_per_lot,
                    "value_added_cost_per_lot": unit.value_added_cost_per_lot,
                    "logistics_cost_per_lot": unit.logistics_cost_per_lot,
                    "inventory_handling_cost_per_lot": unit.inventory_handling_cost_per_lot,
                    "tax_tariff_cost_per_lot": unit.tax_tariff_cost_per_lot,
                    "target_profit_per_lot": unit.target_profit_per_lot,
                    "price_formation_mode": unit.price_formation_mode,
                    "tax_rate": unit.tax_rate,
                }
            )

        # backward-compatible aliases
        row["inventory_value"] = row["ending_inventory_value"]
        row["tax_base"] = row["profit_before_tax"]
        row["profit"] = row["profit_after_tax"]
        out.append(row)

    kpi_summary_rows = build_kpi_summary(out)
    product_money_summary_rows = build_product_money_summary(out)

    try:
        env.money_unit_price_rows = [asdict(v) for v in sorted(price_table.values(), key=lambda x: (x.product, x.node_name))]
        env.money_weekly_rows = [asdict(v) for v in weekly_rows]

        # GUI/backward compatibility bridge
        env.node_money_rows = out
        env.money_node_rows = out

        prev_money = getattr(env, "money_result", None)
        money_result = dict(prev_money) if isinstance(prev_money, dict) else {}
        money_result["node_money_rows"] = out
        money_result["kpi_summary_rows"] = kpi_summary_rows
        money_result["product_money_summary_rows"] = product_money_summary_rows
        money_result["money_unit_price_rows"] = env.money_unit_price_rows
        money_result["money_weekly_rows"] = env.money_weekly_rows
        env.money_result = money_result
    except Exception:
        pass

    return out


def build_kpi_summary(node_money_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    total_revenue = sum(_safe_float(r.get("revenue")) for r in node_money_rows)
    total_purchase_amount = sum(_safe_float(r.get("purchase_amount")) for r in node_money_rows)
    total_variable_cost = sum(_safe_float(r.get("variable_cost")) for r in node_money_rows)
    total_fixed_cost = sum(_safe_float(r.get("fixed_cost")) for r in node_money_rows)
    total_ending_inventory_value = sum(_safe_float(r.get("ending_inventory_value")) for r in node_money_rows)
    total_issue_cost = sum(_safe_float(r.get("issue_cost")) for r in node_money_rows)
    total_profit_before_tax = sum(_safe_float(r.get("profit_before_tax")) for r in node_money_rows)
    total_tax = sum(_safe_float(r.get("tax")) for r in node_money_rows)
    total_profit_after_tax = sum(_safe_float(r.get("profit_after_tax")) for r in node_money_rows)

    return [
        {
            "node_count": len({r.get("node_name") for r in node_money_rows}),
            "product_count": len({r.get("product") for r in node_money_rows}),
            "total_revenue": total_revenue,
            "total_purchase_amount": total_purchase_amount,
            "total_variable_cost": total_variable_cost,
            "total_fixed_cost": total_fixed_cost,
            "total_ending_inventory_value": total_ending_inventory_value,
            "total_issue_cost": total_issue_cost,
            "total_profit_before_tax": total_profit_before_tax,
            "total_tax": total_tax,
            "total_profit_after_tax": total_profit_after_tax,
            "profit_ratio": (total_profit_after_tax / total_revenue) if total_revenue else 0.0,
            # backward-compatible fields
            "total_inventory_value": total_ending_inventory_value,
            "total_tax_base": total_profit_before_tax,
            "total_profit": total_profit_after_tax,
        }
    ]


def build_product_money_summary(node_money_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    agg = defaultdict(
        lambda: {
            "product": "",
            "node_count": 0,
            "total_revenue": 0.0,
            "total_purchase_amount": 0.0,
            "total_variable_cost": 0.0,
            "total_fixed_cost": 0.0,
            "total_ending_inventory_value": 0.0,
            "total_issue_cost": 0.0,
            "total_profit_before_tax": 0.0,
            "total_tax": 0.0,
            "total_profit_after_tax": 0.0,
        }
    )
    nodes = defaultdict(set)

    for r in node_money_rows:
        p = (r.get("product") or "").strip()
        d = agg[p]
        d["product"] = p
        d["total_revenue"] += _safe_float(r.get("revenue"))
        d["total_purchase_amount"] += _safe_float(r.get("purchase_amount"))
        d["total_variable_cost"] += _safe_float(r.get("variable_cost"))
        d["total_fixed_cost"] += _safe_float(r.get("fixed_cost"))
        d["total_ending_inventory_value"] += _safe_float(r.get("ending_inventory_value"))
        d["total_issue_cost"] += _safe_float(r.get("issue_cost"))
        d["total_profit_before_tax"] += _safe_float(r.get("profit_before_tax"))
        d["total_tax"] += _safe_float(r.get("tax"))
        d["total_profit_after_tax"] += _safe_float(r.get("profit_after_tax"))
        nodes[p].add(r.get("node_name"))

    out = []
    for p, d in agg.items():
        d["node_count"] = len(nodes[p])
        d["profit_ratio"] = (d["total_profit_after_tax"] / d["total_revenue"]) if d["total_revenue"] else 0.0
        # backward-compatible fields
        d["total_inventory_value"] = d["total_ending_inventory_value"]
        d["total_tax_base"] = d["total_profit_before_tax"]
        d["total_profit"] = d["total_profit_after_tax"]
        out.append(d)

    return sorted(out, key=lambda x: x["product"])
