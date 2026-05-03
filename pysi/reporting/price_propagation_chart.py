from __future__ import annotations

import csv
import os
import re
from collections import defaultdict
from typing import Any

STACK_COMPONENTS = [
    "purchase_cost_per_lot",
    "value_added_cost_per_lot",
    "variable_cost_per_lot",
    "fixed_cost_per_lot",
    "logistics_cost_per_lot",
    "inventory_handling_cost_per_lot",
    "tax_tariff_cost_per_lot",
    "target_profit_per_lot",
]


def _as_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _sanitize_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    cleaned = cleaned.strip("._")
    return cleaned or "unknown"


def load_node_price_waterfall(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sort_waterfall_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    has_sequence = any((row.get("sequence_no") or "").strip() != "" for row in rows)
    if not has_sequence:
        return rows
    return [
        row
        for _, row in sorted(
            enumerate(rows),
            key=lambda pair: (_as_float(pair[1].get("sequence_no")), pair[0]),
        )
    ]


def group_rows_by_product_and_direction(rows: list[dict[str, str]]) -> dict[tuple[str, str | None], list[dict[str, str]]]:
    grouped: dict[tuple[str, str | None], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row.get("product", ""), row.get("direction") or None)].append(row)
    return grouped


def build_chart_title(product: str, direction: str | None) -> str:
    if direction:
        return f"Price Waterfall Stacked Bar - {product} ({direction})"
    return f"Price Waterfall Stacked Bar - {product}"


def _render_stacked_chart(rows: list[dict[str, str]], output_path: str, title: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sorted_rows = sort_waterfall_rows(rows)

    node_labels = [r.get("node_name", "") for r in sorted_rows]
    x = list(range(len(sorted_rows)))

    fig, ax = plt.subplots(figsize=(max(8, len(sorted_rows) * 1.2), 5))
    bottoms = [0.0] * len(sorted_rows)

    for component in STACK_COMPONENTS:
        values = [_as_float(r.get(component)) for r in sorted_rows]
        ax.bar(x, values, bottom=bottoms, label=component)
        bottoms = [b + v for b, v in zip(bottoms, values)]

    for i, row in enumerate(sorted_rows):
        ship_price = _as_float(row.get("ship_price_per_lot"))
        ax.text(i, bottoms[i], f"{ship_price:.2f}", ha="center", va="bottom", fontsize=8)

    ax.set_title(title)
    ax.set_xlabel("Node")
    ax.set_ylabel("Amount per lot")
    ax.set_xticks(x)
    ax.set_xticklabels(node_labels, rotation=45, ha="right")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def generate_price_waterfall_stacked_bar(
    node_price_waterfall_csv: str,
    output_dir: str,
    *,
    product: str | None = None,
    direction: str | None = None,
) -> list[str]:
    rows = load_node_price_waterfall(node_price_waterfall_csv)
    os.makedirs(output_dir, exist_ok=True)

    filtered = []
    for row in rows:
        if product is not None and row.get("product") != product:
            continue
        if direction is not None and (row.get("direction") or None) != direction:
            continue
        filtered.append(row)

    grouped = group_rows_by_product_and_direction(filtered)
    generated: list[str] = []

    if direction is None:
        product_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
        for (prod, _dir), group in grouped.items():
            product_rows[prod].extend(group)

        for prod, prod_rows in product_rows.items():
            if not prod_rows:
                continue
            out = os.path.join(output_dir, f"{_sanitize_filename(prod)}_price_waterfall_stacked_bar.png")
            _render_stacked_chart(prod_rows, out, build_chart_title(prod, None))
            generated.append(out)
    else:
        for (prod, dir_key), prod_rows in grouped.items():
            if not prod_rows:
                continue
            direction_name = dir_key or "unknown"
            out = os.path.join(
                output_dir,
                f"{_sanitize_filename(prod)}_{_sanitize_filename(direction_name)}_price_waterfall_stacked_bar.png",
            )
            _render_stacked_chart(prod_rows, out, build_chart_title(prod, dir_key))
            generated.append(out)

    return generated
