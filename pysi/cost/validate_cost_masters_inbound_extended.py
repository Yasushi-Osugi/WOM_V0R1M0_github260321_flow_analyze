"""Validation for cost masters used by reporting MVP + inbound extension.

Design goals:
- keep backward compatibility with the current validate_cost_masters(cost_masters) -> list[str]
- accept either a plain dict payload or a bundle-like object with to_legacy_payload()
- validate current outbound/reporting MVP keys
- optionally validate inbound extension masters when present or when require_inbound=True
"""

from __future__ import annotations

from typing import Any


REQUIRED_TOP_KEYS = (
    "node_cost_rates",
    "lane_cost_rates",
    "market_cost_rates",
    "allocation_rules",
)

OPTIONAL_OUTBOUND_ROW_KEYS = (
    "product_rows",
    "node_rows",
    "lane_rows",
    "sales_price_rows",
    "allocation_rule_rows",
    "market_rows",
    "cs_node_to_market_rows",
    "sga_rows",
    "fixed_asset_rows",
)

OPTIONAL_INBOUND_KEYS = (
    "inbound_item_rows",
    "inbound_bom_rows",
    "inbound_price_decision_rows",
    "inbound_adjustment_rows",
    "inbound_item_lookup",
    "inbound_bom_by_parent",
    "inbound_price_decision_lookup",
    "inbound_adjustment_by_product",
    "inbound_adjustment_by_item",
)

VALID_DECISION_PHASES = {"target", "quote", "contract", "actual"}
VALID_DIRECTION_SCOPES = {"inbound", "outbound", "both"}
VALID_ALLOCATION_DIMS = {"node", "market", "product", "total"}
VALID_COST_TYPES = {"FIXED", "VARIABLE", ""}


def _normalize_payload(cost_masters: Any) -> dict[str, Any]:
    if isinstance(cost_masters, dict):
        return cost_masters

    to_legacy = getattr(cost_masters, "to_legacy_payload", None)
    if callable(to_legacy):
        payload = to_legacy()
        if isinstance(payload, dict):
            return payload

    # fallback: very light duck-typing for bundle-like objects
    payload: dict[str, Any] = {}
    for key in REQUIRED_TOP_KEYS + OPTIONAL_OUTBOUND_ROW_KEYS + OPTIONAL_INBOUND_KEYS:
        if hasattr(cost_masters, key):
            payload[key] = getattr(cost_masters, key)
    return payload


def _is_mapping(x: Any) -> bool:
    return isinstance(x, dict)


def _is_list_of_dicts(x: Any) -> bool:
    return isinstance(x, list) and all(isinstance(v, dict) for v in x)


def _safe_str(x: Any) -> str:
    return str(x or "").strip()


def _truthy(x: Any) -> bool:
    return _safe_str(x).lower() in {"1", "true", "yes", "y", "on"}


def _add_type_error(errors: list[str], key: str, expected: str, got: Any) -> None:
    errors.append(f"{key} must be {expected} (got {type(got).__name__})")


def _validate_rate_tables(payload: dict[str, Any], errors: list[str]) -> None:
    for group in ("node_cost_rates", "lane_cost_rates", "market_cost_rates"):
        table = payload.get(group, {})
        if table is None:
            errors.append(f"{group} must be a mapping")
            continue
        if not isinstance(table, dict):
            errors.append(f"{group} must be a mapping")
            continue

        for item_key, category_map in table.items():
            if not isinstance(category_map, dict):
                errors.append(f"{group}.{item_key} must be a mapping")
                continue
            for category, rate in category_map.items():
                if not isinstance(rate, (int, float)):
                    errors.append(
                        f"{group}.{item_key}.{category} must be numeric (got {type(rate).__name__})"
                    )


def _validate_allocation_rules(payload: dict[str, Any], errors: list[str]) -> None:
    rules = payload.get("allocation_rules", [])
    if not isinstance(rules, list):
        errors.append("allocation_rules must be a list")
        return

    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f"allocation_rules[{idx}] must be an object")
            continue

        if not _safe_str(rule.get("name")):
            errors.append(f"allocation_rules[{idx}].name is required")

        from_dim = _safe_str(rule.get("from_dim"))
        to_dim = _safe_str(rule.get("to_dim"))

        if from_dim and from_dim not in VALID_ALLOCATION_DIMS:
            errors.append(
                f"allocation_rules[{idx}].from_dim must be one of {sorted(VALID_ALLOCATION_DIMS)}"
            )
        if to_dim and to_dim not in VALID_ALLOCATION_DIMS:
            errors.append(
                f"allocation_rules[{idx}].to_dim must be one of {sorted(VALID_ALLOCATION_DIMS)}"
            )

        if "from_key" not in rule or _safe_str(rule.get("from_key")) == "":
            errors.append(f"allocation_rules[{idx}].from_key is required")

        pool_categories = rule.get("pool_categories", [])
        if not isinstance(pool_categories, list):
            errors.append(f"allocation_rules[{idx}].pool_categories must be a list")
        else:
            for j, cat in enumerate(pool_categories):
                if not isinstance(cat, str):
                    errors.append(f"allocation_rules[{idx}].pool_categories[{j}] must be a string")

        fixed_or_variable = _safe_str(rule.get("fixed_or_variable")).upper()
        if fixed_or_variable not in VALID_COST_TYPES:
            errors.append(
                f"allocation_rules[{idx}].fixed_or_variable must be one of {sorted(v for v in VALID_COST_TYPES if v)}"
            )


def _validate_optional_row_groups(payload: dict[str, Any], errors: list[str]) -> None:
    for key in OPTIONAL_OUTBOUND_ROW_KEYS:
        if key not in payload:
            continue
        value = payload.get(key)
        if not _is_list_of_dicts(value):
            _add_type_error(errors, key, "a list[dict]", value)


def _validate_lookup_shapes(payload: dict[str, Any], errors: list[str]) -> None:
    lookup_keys = (
        "product_cost_lookup",
        "sales_price_lookup",
        "market_entity_lookup",
        "cs_node_to_market_lookup",
        "node_lookup",
        "lane_lookup",
        "sga_lookup",
        "fixed_asset_lookup",
    )
    for key in lookup_keys:
        if key not in payload:
            continue
        value = payload.get(key)
        if not _is_mapping(value):
            _add_type_error(errors, key, "a mapping", value)


def _validate_inbound_shapes(payload: dict[str, Any], errors: list[str], require_inbound: bool) -> None:
    has_any_inbound = any(k in payload and payload.get(k) not in (None, {}, []) for k in OPTIONAL_INBOUND_KEYS)

    if require_inbound and not has_any_inbound:
        errors.append("inbound masters are required but no inbound payload was found")
        return

    if not has_any_inbound:
        return

    # row groups
    for key in (
        "inbound_item_rows",
        "inbound_bom_rows",
        "inbound_price_decision_rows",
        "inbound_adjustment_rows",
    ):
        value = payload.get(key, [])
        if not _is_list_of_dicts(value):
            _add_type_error(errors, key, "a list[dict]", value)

    # lookup groups
    for key in (
        "inbound_item_lookup",
        "inbound_bom_by_parent",
        "inbound_price_decision_lookup",
        "inbound_adjustment_by_product",
        "inbound_adjustment_by_item",
    ):
        value = payload.get(key, {})
        if not _is_mapping(value):
            _add_type_error(errors, key, "a mapping", value)

    if errors:
        return

    _validate_inbound_row_content(payload, errors)


def _validate_inbound_row_content(payload: dict[str, Any], errors: list[str]) -> None:
    item_rows = list(payload.get("inbound_item_rows", []))
    bom_rows = list(payload.get("inbound_bom_rows", []))
    price_rows = list(payload.get("inbound_price_decision_rows", []))
    adj_rows = list(payload.get("inbound_adjustment_rows", []))

    inbound_item_lookup = payload.get("inbound_item_lookup", {})
    product_cost_lookup = payload.get("product_cost_lookup", {})

    item_ids = set()
    for idx, row in enumerate(item_rows):
        item_id = _safe_str(row.get("item_id"))
        if not item_id:
            errors.append(f"inbound_item_rows[{idx}].item_id is required")
            continue
        item_ids.add(item_id)

        if not _safe_str(row.get("base_uom")):
            errors.append(f"inbound_item_rows[{idx}].base_uom is required")

        active_flag = row.get("active_flag")
        if active_flag not in (None, "", 0, 1, "0", "1", True, False, "true", "false", "TRUE", "FALSE", "yes", "no", "Y", "N", "on", "off"):
            errors.append(f"inbound_item_rows[{idx}].active_flag should be boolean-like")

    for item_id in inbound_item_lookup.keys():
        if item_ids and item_id not in item_ids:
            errors.append(f"inbound_item_lookup contains unknown item_id: {item_id}")

    for idx, row in enumerate(bom_rows):
        parent_product_id = _safe_str(row.get("parent_product_id"))
        component_item_id = _safe_str(row.get("component_item_id"))

        if not parent_product_id:
            errors.append(f"inbound_bom_rows[{idx}].parent_product_id is required")
        if not component_item_id:
            errors.append(f"inbound_bom_rows[{idx}].component_item_id is required")

        if component_item_id and inbound_item_lookup and component_item_id not in inbound_item_lookup:
            errors.append(
                f"inbound_bom_rows[{idx}].component_item_id not found in inbound_item_lookup: {component_item_id}"
            )

        if parent_product_id and product_cost_lookup and parent_product_id not in product_cost_lookup:
            # soft consistency check: parent product should ideally exist in outbound product lookup
            errors.append(
                f"inbound_bom_rows[{idx}].parent_product_id not found in product_cost_lookup: {parent_product_id}"
            )

        qty = row.get("qty_per_parent")
        try:
            if qty in (None, ""):
                raise ValueError
            float(qty)
        except Exception:
            errors.append(f"inbound_bom_rows[{idx}].qty_per_parent must be numeric")

    decision_keys = set()
    for idx, row in enumerate(price_rows):
        supplier_id = _safe_str(row.get("supplier_id"))
        item_id = _safe_str(row.get("item_id"))
        decision_phase = _safe_str(row.get("decision_phase")).lower()

        if not supplier_id:
            errors.append(f"inbound_price_decision_rows[{idx}].supplier_id is required")
        if not item_id:
            errors.append(f"inbound_price_decision_rows[{idx}].item_id is required")
        if not decision_phase:
            errors.append(f"inbound_price_decision_rows[{idx}].decision_phase is required")
        elif decision_phase not in VALID_DECISION_PHASES:
            errors.append(
                f"inbound_price_decision_rows[{idx}].decision_phase must be one of {sorted(VALID_DECISION_PHASES)}"
            )

        if item_id and inbound_item_lookup and item_id not in inbound_item_lookup:
            errors.append(
                f"inbound_price_decision_rows[{idx}].item_id not found in inbound_item_lookup: {item_id}"
            )

        price_value = row.get("price_value")
        try:
            if price_value in (None, ""):
                raise ValueError
            float(price_value)
        except Exception:
            errors.append(f"inbound_price_decision_rows[{idx}].price_value must be numeric")

        if not _safe_str(row.get("price_uom")):
            errors.append(f"inbound_price_decision_rows[{idx}].price_uom is required")

        key = (supplier_id, item_id, decision_phase)
        if supplier_id and item_id and decision_phase:
            decision_keys.add(key)

    for idx, row in enumerate(adj_rows):
        related_decision_id = _safe_str(row.get("related_decision_id"))
        supplier_id = _safe_str(row.get("supplier_id"))
        item_id = _safe_str(row.get("item_id"))
        product_id = _safe_str(row.get("product_id"))

        if not _safe_str(row.get("adjustment_type")):
            errors.append(f"inbound_adjustment_rows[{idx}].adjustment_type is required")

        if not item_id and not product_id:
            errors.append(
                f"inbound_adjustment_rows[{idx}] must have at least one of item_id or product_id"
            )

        if item_id and inbound_item_lookup and item_id not in inbound_item_lookup:
            errors.append(
                f"inbound_adjustment_rows[{idx}].item_id not found in inbound_item_lookup: {item_id}"
            )

        amount_value = row.get("amount_value")
        try:
            if amount_value in (None, ""):
                raise ValueError
            float(amount_value)
        except Exception:
            errors.append(f"inbound_adjustment_rows[{idx}].amount_value must be numeric")

        # weak consistency: if related_decision_id is present, supplier/item should also be present
        if related_decision_id and not supplier_id:
            errors.append(
                f"inbound_adjustment_rows[{idx}].supplier_id is recommended/required when related_decision_id is present"
            )

    # validate lookup content shape minimally
    for parent_key, rows in payload.get("inbound_bom_by_parent", {}).items():
        if not isinstance(rows, list):
            errors.append(f"inbound_bom_by_parent[{parent_key}] must be a list")
            continue
        for j, row in enumerate(rows):
            if not isinstance(row, dict):
                errors.append(f"inbound_bom_by_parent[{parent_key}][{j}] must be an object")

    for key, rows in payload.get("inbound_price_decision_lookup", {}).items():
        if not isinstance(rows, list):
            errors.append(f"inbound_price_decision_lookup[{key}] must be a list")
            continue
        for j, row in enumerate(rows):
            if not isinstance(row, dict):
                errors.append(f"inbound_price_decision_lookup[{key}][{j}] must be an object")

    for key, rows in payload.get("inbound_adjustment_by_product", {}).items():
        if not isinstance(rows, list):
            errors.append(f"inbound_adjustment_by_product[{key}] must be a list")

    for key, rows in payload.get("inbound_adjustment_by_item", {}).items():
        if not isinstance(rows, list):
            errors.append(f"inbound_adjustment_by_item[{key}] must be a list")


def validate_cost_masters(
    cost_masters: Any,
    *,
    require_inbound: bool = False,
) -> list[str]:
    """Validate shape and return human-readable errors.

    Empty list means validation passed.

    Parameters
    ----------
    cost_masters:
        Either:
        - legacy dict payload
        - extended dict payload with inbound keys
        - bundle-like object exposing to_legacy_payload()

    require_inbound:
        If True, inbound master presence and shape are required.
    """
    payload = _normalize_payload(cost_masters)
    errors: list[str] = []

    for key in REQUIRED_TOP_KEYS:
        if key not in payload:
            errors.append(f"missing top-level key: {key}")

    _validate_rate_tables(payload, errors)
    _validate_allocation_rules(payload, errors)
    _validate_optional_row_groups(payload, errors)
    _validate_lookup_shapes(payload, errors)
    _validate_inbound_shapes(payload, errors, require_inbound=require_inbound)

    return errors
