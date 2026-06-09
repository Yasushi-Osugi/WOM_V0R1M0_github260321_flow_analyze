"""
pysi/ppc/ppc_simulator.py

PPC (Price · Profit · Cost) Simulator — WOM v1r0m0 minimum implementation.

Purpose
-------
PPC is a Tree-based, parallel simulation to PSI.
It determines Planned Sales Price at each Leaf node by:

  1. Accumulating minimum cost from HQ → DC → Leaf (Inbound Tree traversal)
  2. Applying price policy per product × market node
  3. Enforcing brand floor protection (no price below brand_floor_price)
  4. Returning sales_price[product][node][week]

PSI answers: how many units ship?
PPC answers: at what price do they sell?

Both outputs feed into the Profit/Cost Evaluator (Table-based).

Usage
-----
CLI:
    python -m pysi.ppc.ppc_simulator --scenario Baseline --data-dir data/

Python:
    from pysi.ppc.ppc_simulator import PPCSimulator
    sim = PPCSimulator(data_dir="data/", scenario_id="Baseline")
    result = sim.run()
    # result.ppc_df  : DataFrame [product_id, node_id, week, sales_price, unit_cost, margin_rate]
    # result.issues  : list of PPCIssue

Output file
-----------
outputs/ppc/<scenario_id>/ppc_result.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PricePolicy:
    """Per-product × market-node price policy."""
    product_id: str
    market_node: str
    base_price: float
    target_margin_rate: float       # e.g. 0.30 = 30%
    minimum_margin_rate: float      # hard floor on margin
    max_discount_rate: float        # max discount from base_price
    brand_floor_price: float        # absolute price floor (brand protection)
    campaign_budget_rate: float     # allowed campaign discount on top of max_discount
    competitor_follow_flag: bool    # False = do NOT follow competitor cuts


@dataclass(frozen=True)
class NodeCostRecord:
    """Cost ratio model per product × node (business-character model)."""
    product_id: str
    node_id: str
    business_unit: str
    sales_price: float              # reference / list price at this node
    material_cost_ratio: float
    labor_cost_ratio: float
    facility_fixed_cost_ratio: float
    logistics_cost_ratio: float
    indirect_cost_ratio: float
    profit_ratio: float

    @property
    def total_cost_ratio(self) -> float:
        return (
            self.material_cost_ratio
            + self.labor_cost_ratio
            + self.facility_fixed_cost_ratio
            + self.logistics_cost_ratio
            + self.indirect_cost_ratio
        )

    def unit_cost(self) -> float:
        """Derived unit cost from reference sales_price and cost ratios."""
        return self.sales_price * self.total_cost_ratio


@dataclass
class PPCResult:
    scenario_id: str
    rows: list[PPCRow] = field(default_factory=list)
    issues: list[PPCIssue] = field(default_factory=list)

    def to_csv_rows(self) -> list[dict]:
        return [asdict(r) for r in self.rows]


@dataclass(frozen=True)
class PPCRow:
    """One row of PPC output: the determined price for product × node × week."""
    product_id: str
    node_id: str
    week: str                       # ISO week YYYYWW
    sales_price: float
    unit_cost: float
    margin_rate: float
    floor_applied: bool             # True if brand_floor_price was enforced
    policy_type: str                # "target" / "minimum" / "floor"


@dataclass(frozen=True)
class PPCIssue:
    """A pricing issue detected during simulation."""
    product_id: str
    node_id: str
    week: str
    issue_type: str                 # BELOW_MINIMUM_MARGIN / AT_BRAND_FLOOR / NO_POLICY
    message: str
    severity: float                 # 0.0 – 1.0


# ---------------------------------------------------------------------------
# Master data loaders
# ---------------------------------------------------------------------------

def load_price_policy(data_dir: Path) -> dict[tuple[str, str], PricePolicy]:
    """
    Load product_price_policy.csv

    Expected columns:
        product_id, market_node, base_price, target_margin_rate,
        minimum_margin_rate, max_discount_rate, brand_floor_price,
        campaign_budget_rate, competitor_follow_flag
    """
    path = data_dir / "product_price_policy.csv"
    if not path.exists():
        logger.warning("product_price_policy.csv not found at %s — using empty policy", path)
        return {}

    policies: dict[tuple[str, str], PricePolicy] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            p = PricePolicy(
                product_id=row["product_id"].strip(),
                market_node=row["market_node"].strip(),
                base_price=float(row["base_price"]),
                target_margin_rate=float(row["target_margin_rate"]),
                minimum_margin_rate=float(row["minimum_margin_rate"]),
                max_discount_rate=float(row["max_discount_rate"]),
                brand_floor_price=float(row["brand_floor_price"]),
                campaign_budget_rate=float(row.get("campaign_budget_rate", "0")),
                competitor_follow_flag=row.get("competitor_follow_flag", "false").strip().lower() == "true",
            )
            policies[(p.product_id, p.market_node)] = p
    logger.info("Loaded %d price policies from %s", len(policies), path)
    return policies


def load_node_cost_master(data_dir: Path) -> dict[tuple[str, str], NodeCostRecord]:
    """
    Load node_cost_master.csv

    Expected columns:
        product_id, node_id, business_unit, sales_price,
        material_cost_ratio, labor_cost_ratio, facility_fixed_cost_ratio,
        logistics_cost_ratio, indirect_cost_ratio, profit_ratio
    """
    path = data_dir / "node_cost_master.csv"
    if not path.exists():
        logger.warning("node_cost_master.csv not found at %s — using empty cost master", path)
        return {}

    costs: dict[tuple[str, str], NodeCostRecord] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            r = NodeCostRecord(
                product_id=row["product_id"].strip(),
                node_id=row["node_id"].strip(),
                business_unit=row.get("business_unit", "").strip(),
                sales_price=float(row["sales_price"]),
                material_cost_ratio=float(row.get("material_cost_ratio", "0")),
                labor_cost_ratio=float(row.get("labor_cost_ratio", "0")),
                facility_fixed_cost_ratio=float(row.get("facility_fixed_cost_ratio", "0")),
                logistics_cost_ratio=float(row.get("logistics_cost_ratio", "0")),
                indirect_cost_ratio=float(row.get("indirect_cost_ratio", "0")),
                profit_ratio=float(row.get("profit_ratio", "0")),
            )
            costs[(r.product_id, r.node_id)] = r
    logger.info("Loaded %d node cost records from %s", len(costs), path)
    return costs


def discover_leaf_nodes(data_dir: Path) -> list[tuple[str, str]]:
    """
    Discover (product_id, node_id) pairs that are Leaf (market) nodes.
    Looks for node_master.csv with a node_type column.
    Falls back to reading psi_result.csv if available.
    Returns list of (product_id, node_id) tuples.
    """
    # Try node_master.csv first
    node_master = data_dir / "node_master.csv"
    if node_master.exists():
        leaves = []
        with open(node_master, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("node_type", "").strip().upper() in ("MARKET", "LEAF"):
                    leaves.append((row.get("product_id", "*").strip(), row["node_id"].strip()))
        if leaves:
            return leaves

    # Fallback: read from psi_result.csv if present
    psi_result = data_dir / "psi_result.csv"
    if psi_result.exists():
        pairs = set()
        with open(psi_result, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("node_type", "").strip().upper() in ("MARKET", "LEAF"):
                    pairs.add((row["product_id"].strip(), row["node_id"].strip()))
        return list(pairs)

    logger.warning("No node_master.csv or psi_result.csv found — leaf node discovery empty")
    return []


def discover_weeks(data_dir: Path, scenario_id: str) -> list[str]:
    """
    Return a sorted list of ISO week strings for the given scenario.
    Looks for scenario_weeks.csv or falls back to psi_result.csv.
    """
    weeks_file = data_dir / "scenario_weeks.csv"
    if weeks_file.exists():
        weeks = []
        with open(weeks_file, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("scenario_id", scenario_id).strip() == scenario_id:
                    weeks.append(row["week"].strip())
        if weeks:
            return sorted(set(weeks))

    psi_result = data_dir / "psi_result.csv"
    if psi_result.exists():
        weeks = set()
        with open(psi_result, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("scenario_id", scenario_id).strip() == scenario_id:
                    weeks.add(row.get("week", row.get("time_bucket", "")).strip())
        if weeks:
            return sorted(weeks - {""})

    # Default: generate 52 weeks of the current plan year
    logger.warning("No week source found — defaulting to 202601..202652")
    return [f"2026{w:02d}" for w in range(1, 53)]


# ---------------------------------------------------------------------------
# Price determination logic
# ---------------------------------------------------------------------------

def determine_price(
    product_id: str,
    node_id: str,
    week: str,
    policy: Optional[PricePolicy],
    cost_record: Optional[NodeCostRecord],
) -> PPCRow:
    """
    Core price determination for one product × node × week.

    Logic:
      1. If no cost record → use fallback unit_cost = 0
      2. If no policy → use cost record's sales_price as-is (no margin check)
      3. Compute target price = unit_cost / (1 - target_margin_rate)
      4. Apply brand floor protection
      5. Record which constraint bound the result
    """
    unit_cost = cost_record.unit_cost() if cost_record else 0.0
    ref_price = cost_record.sales_price if cost_record else 0.0

    if policy is None:
        # No policy: pass through reference price, no margin enforcement
        margin_rate = (ref_price - unit_cost) / ref_price if ref_price > 0 else 0.0
        return PPCRow(
            product_id=product_id,
            node_id=node_id,
            week=week,
            sales_price=ref_price,
            unit_cost=unit_cost,
            margin_rate=round(margin_rate, 4),
            floor_applied=False,
            policy_type="passthrough",
        )

    # Target price from margin target
    if (1.0 - policy.target_margin_rate) > 0:
        target_price = unit_cost / (1.0 - policy.target_margin_rate)
    else:
        target_price = unit_cost * 1.5  # fallback if margin rate >= 100%

    # Minimum price from minimum margin
    if (1.0 - policy.minimum_margin_rate) > 0:
        min_price = unit_cost / (1.0 - policy.minimum_margin_rate)
    else:
        min_price = unit_cost

    # Start from target
    sales_price = target_price
    policy_type = "target"

    # Clamp to base_price × (1 - max_discount)
    max_discounted_price = policy.base_price * (1.0 - policy.max_discount_rate)
    if sales_price < max_discounted_price:
        sales_price = max_discounted_price
        policy_type = "max_discount_floor"

    # Clamp to minimum margin floor
    if sales_price < min_price:
        sales_price = min_price
        policy_type = "minimum"

    # Brand floor protection (absolute — never negotiable)
    floor_applied = False
    if sales_price < policy.brand_floor_price:
        sales_price = policy.brand_floor_price
        floor_applied = True
        policy_type = "floor"

    margin_rate = (sales_price - unit_cost) / sales_price if sales_price > 0 else 0.0

    return PPCRow(
        product_id=product_id,
        node_id=node_id,
        week=week,
        sales_price=round(sales_price, 2),
        unit_cost=round(unit_cost, 2),
        margin_rate=round(margin_rate, 4),
        floor_applied=floor_applied,
        policy_type=policy_type,
    )


def check_issues(row: PPCRow, policy: Optional[PricePolicy]) -> list[PPCIssue]:
    """Generate PPCIssues for a completed PPCRow."""
    issues = []
    if policy is None:
        issues.append(PPCIssue(
            product_id=row.product_id,
            node_id=row.node_id,
            week=row.week,
            issue_type="NO_POLICY",
            message=f"No price policy for {row.product_id} × {row.node_id} — using passthrough",
            severity=0.3,
        ))
    elif row.floor_applied:
        issues.append(PPCIssue(
            product_id=row.product_id,
            node_id=row.node_id,
            week=row.week,
            issue_type="AT_BRAND_FLOOR",
            message=(
                f"Price {row.sales_price} hit brand_floor_price. "
                f"Margin {row.margin_rate:.1%} may be below target."
            ),
            severity=0.7,
        ))
    elif policy and row.margin_rate < policy.minimum_margin_rate:
        issues.append(PPCIssue(
            product_id=row.product_id,
            node_id=row.node_id,
            week=row.week,
            issue_type="BELOW_MINIMUM_MARGIN",
            message=(
                f"Margin {row.margin_rate:.1%} < minimum {policy.minimum_margin_rate:.1%}"
            ),
            severity=0.8,
        ))
    return issues


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------

class PPCSimulator:
    """
    Minimum PPC (Price · Profit · Cost) Simulator.

    Parallel to PSI Simulator — determines sales price per product × node × week.
    Does not depend on PSI output; runs independently.
    Both feed into the Profit/Cost Evaluator.
    """

    def __init__(
        self,
        data_dir: str = "data/",
        scenario_id: str = "Baseline",
        output_dir: str = "outputs/ppc/",
    ):
        self.data_dir = Path(data_dir)
        self.scenario_id = scenario_id
        self.output_dir = Path(output_dir) / scenario_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> PPCResult:
        logger.info("[PPC] Starting simulation for scenario: %s", self.scenario_id)

        price_policies = load_price_policy(self.data_dir)
        cost_master = load_node_cost_master(self.data_dir)
        leaf_nodes = discover_leaf_nodes(self.data_dir)
        weeks = discover_weeks(self.data_dir, self.scenario_id)

        result = PPCResult(scenario_id=self.scenario_id)

        if not leaf_nodes:
            logger.warning("[PPC] No leaf nodes discovered — output will be empty")
        if not weeks:
            logger.warning("[PPC] No weeks discovered — output will be empty")

        for (product_id, node_id) in leaf_nodes:
            policy = price_policies.get((product_id, node_id))
            if policy is None:
                # Try wildcard product match
                policy = price_policies.get(("*", node_id))

            cost_record = cost_master.get((product_id, node_id))

            for week in weeks:
                row = determine_price(product_id, node_id, week, policy, cost_record)
                result.rows.append(row)
                result.issues.extend(check_issues(row, policy))

        self._write_csv(result)
        self._write_summary(result)

        logger.info(
            "[PPC] Done — %d price rows, %d issues", len(result.rows), len(result.issues)
        )
        return result

    def _write_csv(self, result: PPCResult) -> None:
        out = self.output_dir / "ppc_result.csv"
        rows = result.to_csv_rows()
        if not rows:
            logger.warning("[PPC] No rows to write")
            return
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        logger.info("[PPC] Wrote %s (%d rows)", out, len(rows))

    def _write_summary(self, result: PPCResult) -> None:
        out = self.output_dir / "ppc_summary.json"
        floor_count = sum(1 for r in result.rows if r.floor_applied)
        avg_margin = (
            sum(r.margin_rate for r in result.rows) / len(result.rows)
            if result.rows else 0.0
        )
        summary = {
            "scenario_id": result.scenario_id,
            "total_rows": len(result.rows),
            "total_issues": len(result.issues),
            "brand_floor_enforced_count": floor_count,
            "average_margin_rate": round(avg_margin, 4),
            "issues": [asdict(i) for i in result.issues],
        }
        with open(out, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        logger.info("[PPC] Wrote summary: %s", out)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _cli() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="WOM PPC Simulator")
    ap.add_argument("--scenario", default="Baseline", help="Scenario ID")
    ap.add_argument("--data-dir", default="data/", help="Path to master data folder")
    ap.add_argument("--output-dir", default="outputs/ppc/", help="Path to output folder")
    args = ap.parse_args()

    sim = PPCSimulator(
        data_dir=args.data_dir,
        scenario_id=args.scenario,
        output_dir=args.output_dir,
    )
    result = sim.run()

    print(f"\n=== PPC Result: {result.scenario_id} ===")
    print(f"Price rows : {len(result.rows)}")
    print(f"Issues     : {len(result.issues)}")
    floor_count = sum(1 for r in result.rows if r.floor_applied)
    print(f"Brand floor applied : {floor_count}")
    if result.rows:
        avg_margin = sum(r.margin_rate for r in result.rows) / len(result.rows)
        print(f"Avg margin rate     : {avg_margin:.1%}")
    if result.issues:
        print("\nTop issues:")
        for issue in sorted(result.issues, key=lambda i: -i.severity)[:5]:
            print(f"  [{issue.issue_type}] {issue.product_id} × {issue.node_id} "
                  f"week {issue.week} — {issue.message}")


if __name__ == "__main__":
    _cli()
