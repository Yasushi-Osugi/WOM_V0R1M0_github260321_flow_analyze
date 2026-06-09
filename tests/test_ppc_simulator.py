"""
tests/test_ppc_simulator.py

Test suite for pysi/ppc/ppc_simulator.py — WOM v1r0m0

Covers:
  - Unit cost calculation from cost ratios
  - Price determination logic (target / minimum / brand floor)
  - Brand floor protection enforcement
  - No-policy passthrough
  - Full simulator run with sample master data
  - Output CSV structure validation
"""

import csv
import json
import tempfile
from pathlib import Path

import pytest

# Adjust import path when running from repo root
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pysi.ppc.ppc_simulator import (
    NodeCostRecord,
    PPCSimulator,
    PricePolicy,
    determine_price,
    check_issues,
    load_price_policy,
    load_node_cost_master,
)


# ---------------------------------------------------------------------------
# Fixtures: sample master data
# ---------------------------------------------------------------------------

SAMPLE_POLICY_CSV = """\
product_id,market_node,base_price,target_margin_rate,minimum_margin_rate,max_discount_rate,brand_floor_price,campaign_budget_rate,competitor_follow_flag
RICE_A,MARKET_TOKYO,5000,0.30,0.15,0.10,4000,0.05,false
RICE_A,MARKET_OSAKA,4800,0.28,0.15,0.10,3900,0.05,false
"""

SAMPLE_COST_CSV = """\
product_id,node_id,business_unit,sales_price,material_cost_ratio,labor_cost_ratio,facility_fixed_cost_ratio,logistics_cost_ratio,indirect_cost_ratio,profit_ratio
RICE_A,MARKET_TOKYO,SalesDiv,5000,0.62,0.07,0.08,0.08,0.04,0.11
RICE_A,MARKET_OSAKA,SalesDiv,4800,0.62,0.07,0.08,0.09,0.04,0.10
"""

SAMPLE_NODE_MASTER_CSV = """\
product_id,node_id,node_type
RICE_A,MARKET_TOKYO,MARKET
RICE_A,MARKET_OSAKA,MARKET
"""

SAMPLE_WEEKS_CSV = """\
scenario_id,week
Baseline,202601
Baseline,202602
Baseline,202603
"""


@pytest.fixture
def sample_data_dir(tmp_path):
    """Write sample CSVs into a temp directory and return it."""
    (tmp_path / "product_price_policy.csv").write_text(SAMPLE_POLICY_CSV, encoding="utf-8")
    (tmp_path / "node_cost_master.csv").write_text(SAMPLE_COST_CSV, encoding="utf-8")
    (tmp_path / "node_master.csv").write_text(SAMPLE_NODE_MASTER_CSV, encoding="utf-8")
    (tmp_path / "scenario_weeks.csv").write_text(SAMPLE_WEEKS_CSV, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Unit tests: NodeCostRecord
# ---------------------------------------------------------------------------

class TestNodeCostRecord:
    def _record(self, **kwargs):
        defaults = dict(
            product_id="RICE_A",
            node_id="MARKET_TOKYO",
            business_unit="SalesDiv",
            sales_price=5000.0,
            material_cost_ratio=0.62,
            labor_cost_ratio=0.07,
            facility_fixed_cost_ratio=0.08,
            logistics_cost_ratio=0.08,
            indirect_cost_ratio=0.04,
            profit_ratio=0.11,
        )
        defaults.update(kwargs)
        return NodeCostRecord(**defaults)

    def test_total_cost_ratio(self):
        r = self._record()
        expected = 0.62 + 0.07 + 0.08 + 0.08 + 0.04
        assert abs(r.total_cost_ratio - expected) < 1e-9

    def test_unit_cost_derived_from_price_and_ratios(self):
        r = self._record(sales_price=5000.0,
                         material_cost_ratio=0.60, labor_cost_ratio=0.0,
                         facility_fixed_cost_ratio=0.0, logistics_cost_ratio=0.0,
                         indirect_cost_ratio=0.0)
        assert abs(r.unit_cost() - 3000.0) < 0.01

    def test_unit_cost_zero_when_all_ratios_zero(self):
        r = self._record(
            material_cost_ratio=0, labor_cost_ratio=0,
            facility_fixed_cost_ratio=0, logistics_cost_ratio=0, indirect_cost_ratio=0
        )
        assert r.unit_cost() == 0.0


# ---------------------------------------------------------------------------
# Unit tests: determine_price
# ---------------------------------------------------------------------------

class TestDeterminePrice:
    def _policy(self, **kwargs):
        defaults = dict(
            product_id="RICE_A",
            market_node="MARKET_TOKYO",
            base_price=5000.0,
            target_margin_rate=0.30,
            minimum_margin_rate=0.15,
            max_discount_rate=0.10,
            brand_floor_price=4000.0,
            campaign_budget_rate=0.05,
            competitor_follow_flag=False,
        )
        defaults.update(kwargs)
        return PricePolicy(**defaults)

    def _cost(self, sales_price=5000.0, total_ratio=0.70):
        return NodeCostRecord(
            product_id="RICE_A", node_id="MARKET_TOKYO", business_unit="SalesDiv",
            sales_price=sales_price,
            material_cost_ratio=total_ratio, labor_cost_ratio=0,
            facility_fixed_cost_ratio=0, logistics_cost_ratio=0,
            indirect_cost_ratio=0, profit_ratio=0,
        )

    def test_target_margin_applied(self):
        # unit_cost = 5000 * 0.70 = 3500; target price = 3500 / (1 - 0.30) = 5000
        row = determine_price("RICE_A", "MARKET_TOKYO", "202601",
                              self._policy(), self._cost(total_ratio=0.70))
        assert row.sales_price == 5000.0
        assert row.policy_type == "target"

    def test_brand_floor_enforced_when_cost_too_high(self):
        # Brand floor triggers when the computed price would fall BELOW it.
        # Scenario: very high base_price and very aggressive max_discount
        # forces max_discounted_price below brand_floor_price.
        #
        # base_price = 5000, max_discount = 0.90 → max_discounted_price = 500
        # unit_cost = 5000 * 0.10 = 500 → target = 500 / 0.70 ≈ 714
        # minimum = 500 / 0.85 ≈ 588
        # brand_floor_price = 4500  (well above all computed values)
        # → floor is the binding constraint → floor_applied = True
        cost = self._cost(sales_price=5000.0, total_ratio=0.10)
        policy = self._policy(
            base_price=5000.0,
            target_margin_rate=0.30,
            minimum_margin_rate=0.15,
            max_discount_rate=0.90,   # allows discounting down to 500
            brand_floor_price=4500.0, # floor is above all computed prices
        )
        row = determine_price("RICE_A", "MARKET_TOKYO", "202601", policy, cost)
        assert row.floor_applied is True
        assert row.sales_price == 4500.0
        assert row.policy_type == "floor"

    def test_no_policy_returns_passthrough(self):
        cost = self._cost()
        row = determine_price("RICE_A", "MARKET_TOKYO", "202601", None, cost)
        assert row.policy_type == "passthrough"
        assert row.sales_price == cost.sales_price
        assert row.floor_applied is False

    def test_no_cost_record_gives_zero_unit_cost(self):
        row = determine_price("RICE_A", "MARKET_TOKYO", "202601",
                              self._policy(), None)
        assert row.unit_cost == 0.0

    def test_margin_rate_is_correct(self):
        # unit_cost = 3500, target price = 5000 → margin = 500/5000 = 0.30
        row = determine_price("RICE_A", "MARKET_TOKYO", "202601",
                              self._policy(), self._cost(total_ratio=0.70))
        assert abs(row.margin_rate - 0.30) < 0.01


# ---------------------------------------------------------------------------
# Unit tests: check_issues
# ---------------------------------------------------------------------------

class TestCheckIssues:
    def _row(self, margin_rate=0.30, floor_applied=False, policy_type="target"):
        from pysi.ppc.ppc_simulator import PPCRow
        return PPCRow(
            product_id="RICE_A", node_id="MARKET_TOKYO", week="202601",
            sales_price=5000.0, unit_cost=3500.0,
            margin_rate=margin_rate, floor_applied=floor_applied,
            policy_type=policy_type,
        )

    def _policy(self, minimum_margin_rate=0.15):
        return PricePolicy(
            product_id="RICE_A", market_node="MARKET_TOKYO",
            base_price=5000.0, target_margin_rate=0.30,
            minimum_margin_rate=minimum_margin_rate,
            max_discount_rate=0.10, brand_floor_price=4000.0,
            campaign_budget_rate=0.05, competitor_follow_flag=False,
        )

    def test_no_issues_when_healthy(self):
        issues = check_issues(self._row(), self._policy())
        assert issues == []

    def test_no_policy_generates_no_policy_issue(self):
        issues = check_issues(self._row(), None)
        assert len(issues) == 1
        assert issues[0].issue_type == "NO_POLICY"

    def test_brand_floor_generates_issue(self):
        issues = check_issues(self._row(floor_applied=True, policy_type="floor"), self._policy())
        assert any(i.issue_type == "AT_BRAND_FLOOR" for i in issues)

    def test_below_minimum_margin_generates_issue(self):
        issues = check_issues(self._row(margin_rate=0.05), self._policy(minimum_margin_rate=0.15))
        assert any(i.issue_type == "BELOW_MINIMUM_MARGIN" for i in issues)


# ---------------------------------------------------------------------------
# Integration test: full simulator run
# ---------------------------------------------------------------------------

class TestPPCSimulatorIntegration:
    def test_run_produces_csv(self, sample_data_dir, tmp_path):
        output_dir = tmp_path / "outputs" / "ppc"
        sim = PPCSimulator(
            data_dir=str(sample_data_dir),
            scenario_id="Baseline",
            output_dir=str(output_dir),
        )
        result = sim.run()

        # rows produced
        assert len(result.rows) > 0, "Expected at least one PPC row"

        # output file exists
        out_csv = output_dir / "Baseline" / "ppc_result.csv"
        assert out_csv.exists(), f"Expected {out_csv} to exist"

        # CSV has required columns
        with open(out_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
        for required in ("product_id", "node_id", "week", "sales_price", "unit_cost", "margin_rate"):
            assert required in cols, f"Missing column: {required}"

    def test_sales_price_above_zero(self, sample_data_dir, tmp_path):
        sim = PPCSimulator(
            data_dir=str(sample_data_dir),
            scenario_id="Baseline",
            output_dir=str(tmp_path / "out"),
        )
        result = sim.run()
        assert all(r.sales_price > 0 for r in result.rows), "All sales prices must be > 0"

    def test_brand_floor_never_violated(self, sample_data_dir, tmp_path):
        """No row should have sales_price < brand_floor_price of its policy."""
        policies = load_price_policy(sample_data_dir)
        sim = PPCSimulator(
            data_dir=str(sample_data_dir),
            scenario_id="Baseline",
            output_dir=str(tmp_path / "out"),
        )
        result = sim.run()
        for row in result.rows:
            policy = policies.get((row.product_id, row.node_id))
            if policy:
                assert row.sales_price >= policy.brand_floor_price, (
                    f"Brand floor violated for {row.product_id} × {row.node_id} "
                    f"week {row.week}: {row.sales_price} < {policy.brand_floor_price}"
                )

    def test_deterministic_output(self, sample_data_dir, tmp_path):
        """Same input → same output on two independent runs."""
        def run():
            sim = PPCSimulator(
                data_dir=str(sample_data_dir),
                scenario_id="Baseline",
                output_dir=str(tmp_path / "out"),
            )
            return {(r.product_id, r.node_id, r.week): r.sales_price
                    for r in sim.run().rows}

        run1 = run()
        run2 = run()
        assert run1 == run2, "PPC output must be deterministic"

    def test_summary_json_written(self, sample_data_dir, tmp_path):
        output_dir = tmp_path / "out"
        sim = PPCSimulator(
            data_dir=str(sample_data_dir),
            scenario_id="Baseline",
            output_dir=str(output_dir),
        )
        sim.run()
        summary = output_dir / "Baseline" / "ppc_summary.json"
        assert summary.exists()
        data = json.loads(summary.read_text(encoding="utf-8"))
        assert "total_rows" in data
        assert "average_margin_rate" in data


# ---------------------------------------------------------------------------
# Master data loader tests
# ---------------------------------------------------------------------------

class TestMasterDataLoaders:
    def test_load_price_policy(self, sample_data_dir):
        policies = load_price_policy(sample_data_dir)
        assert ("RICE_A", "MARKET_TOKYO") in policies
        p = policies[("RICE_A", "MARKET_TOKYO")]
        assert p.base_price == 5000.0
        assert p.competitor_follow_flag is False

    def test_load_cost_master(self, sample_data_dir):
        costs = load_node_cost_master(sample_data_dir)
        assert ("RICE_A", "MARKET_TOKYO") in costs
        c = costs[("RICE_A", "MARKET_TOKYO")]
        assert c.sales_price == 5000.0
        assert abs(c.total_cost_ratio - (0.62 + 0.07 + 0.08 + 0.08 + 0.04)) < 1e-9

    def test_missing_csv_returns_empty(self, tmp_path):
        # No CSV files in tmp_path
        policies = load_price_policy(tmp_path)
        costs = load_node_cost_master(tmp_path)
        assert policies == {}
        assert costs == {}
