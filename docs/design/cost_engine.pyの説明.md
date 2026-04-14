承知しました。
以下に、前回の `load_cost_masters.py` に自然につながる **`cost_engine.py` の最小 skeleton** を、WOM の Now フェーズ向けに置きます。

この最小版の狙いは、

* `CostMasterBundle` を読み込んで使える
* `product × node × week` の粒度で node コストを計算できる
* `from_node × to_node × week` の粒度で lane コストを計算できる
* node / lane の結果を total に集約できる
* 後で `PSI Planning Engine` や `KPI engine` に接続しやすい

という形にすることです。

---

## ファイル案

`pysi/cost/cost_engine.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from pysi.cost.load_cost_masters import (
    CostMasterBundle,
    find_lane_master,
    find_node_master,
    find_product_master,
    find_sales_price_master,
)


# ============================================================
# result models
# ============================================================

@dataclass
class NodeCostRecord:
    scenario_id: str
    product_id: str
    node_id: str
    week: int
    market_id: Optional[str] = None

    qty_ctx: Dict[str, float] = field(default_factory=dict)

    revenue: float = 0.0
    material_cost: float = 0.0
    purchase_cost: float = 0.0
    production_cost: float = 0.0
    logistics_cost: float = 0.0
    inventory_holding_cost: float = 0.0

    sga_variable_cost: float = 0.0
    sga_fixed_cost: float = 0.0
    marketing_variable_cost: float = 0.0
    marketing_fixed_cost: float = 0.0

    depreciation_cost: float = 0.0
    allocated_fixed_cost: float = 0.0
    tax_cost: float = 0.0

    gross_profit: float = 0.0
    operating_profit: float = 0.0

    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "product_id": self.product_id,
            "node_id": self.node_id,
            "week": self.week,
            "market_id": self.market_id,
            **self.qty_ctx,
            "revenue": self.revenue,
            "material_cost": self.material_cost,
            "purchase_cost": self.purchase_cost,
            "production_cost": self.production_cost,
            "logistics_cost": self.logistics_cost,
            "inventory_holding_cost": self.inventory_holding_cost,
            "sga_variable_cost": self.sga_variable_cost,
            "sga_fixed_cost": self.sga_fixed_cost,
            "marketing_variable_cost": self.marketing_variable_cost,
            "marketing_fixed_cost": self.marketing_fixed_cost,
            "depreciation_cost": self.depreciation_cost,
            "allocated_fixed_cost": self.allocated_fixed_cost,
            "tax_cost": self.tax_cost,
            "gross_profit": self.gross_profit,
            "operating_profit": self.operating_profit,
            **self.extra,
        }


@dataclass
class LaneCostRecord:
    scenario_id: str
    product_id: str
    from_node_id: str
    to_node_id: str
    week: int
    shipment_qty: float

    freight_cost: float = 0.0
    insurance_cost: float = 0.0
    tariff_cost: float = 0.0
    customs_cost: float = 0.0
    risk_cost: float = 0.0
    carbon_cost: float = 0.0
    lane_fixed_cost: float = 0.0

    total_lane_cost: float = 0.0
    unit_lane_cost: float = 0.0

    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "product_id": self.product_id,
            "from_node_id": self.from_node_id,
            "to_node_id": self.to_node_id,
            "week": self.week,
            "shipment_qty": self.shipment_qty,
            "freight_cost": self.freight_cost,
            "insurance_cost": self.insurance_cost,
            "tariff_cost": self.tariff_cost,
            "customs_cost": self.customs_cost,
            "risk_cost": self.risk_cost,
            "carbon_cost": self.carbon_cost,
            "lane_fixed_cost": self.lane_fixed_cost,
            "total_lane_cost": self.total_lane_cost,
            "unit_lane_cost": self.unit_lane_cost,
            **self.extra,
        }


@dataclass
class TotalCostSummary:
    scenario_id: str
    period_key: str

    total_revenue: float = 0.0
    total_material_cost: float = 0.0
    total_purchase_cost: float = 0.0
    total_production_cost: float = 0.0
    total_logistics_cost: float = 0.0
    total_inventory_holding_cost: float = 0.0
    total_sga_variable_cost: float = 0.0
    total_sga_fixed_cost: float = 0.0
    total_marketing_variable_cost: float = 0.0
    total_marketing_fixed_cost: float = 0.0
    total_depreciation_cost: float = 0.0
    total_allocated_fixed_cost: float = 0.0
    total_tax_cost: float = 0.0

    total_gross_profit: float = 0.0
    total_operating_profit: float = 0.0

    def to_dict(self) -> Dict[str, float | str]:
        return {
            "scenario_id": self.scenario_id,
            "period_key": self.period_key,
            "total_revenue": self.total_revenue,
            "total_material_cost": self.total_material_cost,
            "total_purchase_cost": self.total_purchase_cost,
            "total_production_cost": self.total_production_cost,
            "total_logistics_cost": self.total_logistics_cost,
            "total_inventory_holding_cost": self.total_inventory_holding_cost,
            "total_sga_variable_cost": self.total_sga_variable_cost,
            "total_sga_fixed_cost": self.total_sga_fixed_cost,
            "total_marketing_variable_cost": self.total_marketing_variable_cost,
            "total_marketing_fixed_cost": self.total_marketing_fixed_cost,
            "total_depreciation_cost": self.total_depreciation_cost,
            "total_allocated_fixed_cost": self.total_allocated_fixed_cost,
            "total_tax_cost": self.total_tax_cost,
            "total_gross_profit": self.total_gross_profit,
            "total_operating_profit": self.total_operating_profit,
        }


# ============================================================
# engine
# ============================================================

@dataclass
class CostEngine:
    masters: CostMasterBundle
    default_scenario_id: str = "BASE"

    def compute_node_cost(
        self,
        *,
        product_id: str,
        node_id: str,
        week: int,
        qty_ctx: Mapping[str, Any],
        market_id: Optional[str] = None,
        scenario_id: Optional[str] = None,
    ) -> NodeCostRecord:
        """
        Minimal node-level cost calculation.

        qty_ctx expected keys (typical):
            P_qty
            S_qty
            I_begin
            I_end
            avg_inventory
            ship_qty
            purchase_qty
            served_qty
            logistics_cost   # optional; can be injected from lane results
            allocated_fixed_cost  # optional pre-allocation
        """
        scenario = scenario_id or self.default_scenario_id

        product = self._require_product(product_id)
        node = self._require_node(node_id)

        normalized_qty = self._normalize_qty_ctx(qty_ctx)

        record = NodeCostRecord(
            scenario_id=scenario,
            product_id=product_id,
            node_id=node_id,
            week=week,
            market_id=market_id,
            qty_ctx=normalized_qty,
        )

        sales_price = self._resolve_sales_price(
            scenario_id=scenario,
            product_id=product_id,
            market_id=market_id,
            fallback=float(product.get("base_sales_price") or 0.0),
        )

        material_unit_cost = self._f(product.get("standard_material_cost"))
        production_unit_cost_from_product = self._f(product.get("standard_production_cost"))
        production_cost_rate_from_node = self._f(node.get("production_variable_cost_rate"))
        holding_cost_rate = self._f(node.get("inventory_holding_cost_rate"))

        p_qty = normalized_qty["P_qty"]
        s_qty = normalized_qty["S_qty"]
        purchase_qty = normalized_qty["purchase_qty"]
        avg_inventory = normalized_qty["avg_inventory"]

        record.revenue = s_qty * sales_price

        # 管理会計の初版として、材料費は production/purchase 起点のどちらかで付与
        record.material_cost = p_qty * material_unit_cost
        record.purchase_cost = purchase_qty * self._f(product.get("standard_purchase_cost"))
        record.production_cost = p_qty * (
            production_cost_rate_from_node
            if production_cost_rate_from_node > 0
            else production_unit_cost_from_product
        )
        record.inventory_holding_cost = avg_inventory * holding_cost_rate

        # lane から渡された物流費があれば優先
        record.logistics_cost = self._f(normalized_qty.get("logistics_cost"))

        sga_scope = self._find_sga_scope(
            scenario_id=scenario,
            node_id=node_id,
            market_id=market_id,
        )

        record.sga_variable_cost = record.revenue * self._f(sga_scope.get("sga_variable_cost_rate"))
        record.sga_fixed_cost = self._f(sga_scope.get("sga_fixed_cost"))
        record.marketing_variable_cost = record.revenue * self._f(sga_scope.get("marketing_variable_cost_rate"))
        record.marketing_fixed_cost = self._f(sga_scope.get("marketing_fixed_cost"))

        record.depreciation_cost = self._resolve_node_depreciation_cost(node_id=node_id)
        record.allocated_fixed_cost = self._f(normalized_qty.get("allocated_fixed_cost"))

        pretax_operating = (
            record.revenue
            - record.material_cost
            - record.purchase_cost
            - record.production_cost
            - record.logistics_cost
            - record.inventory_holding_cost
            - record.sga_variable_cost
            - record.sga_fixed_cost
            - record.marketing_variable_cost
            - record.marketing_fixed_cost
            - record.depreciation_cost
            - record.allocated_fixed_cost
        )

        tax_rate = self._resolve_tax_rate(sga_scope)
        record.tax_cost = max(0.0, pretax_operating) * tax_rate

        record.gross_profit = (
            record.revenue
            - record.material_cost
            - record.purchase_cost
            - record.production_cost
            - record.logistics_cost
            - record.inventory_holding_cost
        )

        record.operating_profit = pretax_operating - record.tax_cost

        record.extra = {
            "node_type": node.get("node_type"),
            "sales_price": sales_price,
            "holding_cost_rate": holding_cost_rate,
            "tax_rate": tax_rate,
        }

        return record

    def compute_lane_cost(
        self,
        *,
        product_id: str,
        from_node_id: str,
        to_node_id: str,
        week: int,
        shipment_qty: float,
        scenario_id: Optional[str] = None,
        declared_unit_value: Optional[float] = None,
    ) -> LaneCostRecord:
        """
        Minimal lane-level cost calculation.

        Tariff base:
            declared_unit_value if provided
            else inventory_unit_value
            else base_sales_price
        """
        scenario = scenario_id or self.default_scenario_id

        product = self._require_product(product_id)
        lane = self._require_lane(
            scenario_id=scenario,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
        )

        qty = self._f(shipment_qty)
        unit_value = (
            self._f(declared_unit_value)
            if declared_unit_value is not None
            else self._f(product.get("inventory_unit_value")) or self._f(product.get("base_sales_price"))
        )

        record = LaneCostRecord(
            scenario_id=scenario,
            product_id=product_id,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            week=week,
            shipment_qty=qty,
        )

        freight_unit = self._f(lane.get("freight_cost_per_unit"))
        insurance_unit = self._f(lane.get("insurance_cost_per_unit"))
        tariff_rate = self._f(lane.get("tariff_rate"))
        customs_unit = self._f(lane.get("customs_cost_per_unit"))
        risk_rate = self._f(lane.get("special_risk_cost_rate"))
        carbon_unit = self._f(lane.get("carbon_cost_per_unit"))
        lane_fixed = self._f(lane.get("lane_fixed_cost_per_period"))

        record.freight_cost = qty * freight_unit
        record.insurance_cost = qty * insurance_unit
        record.tariff_cost = qty * unit_value * tariff_rate
        record.customs_cost = qty * customs_unit
        record.risk_cost = qty * unit_value * risk_rate
        record.carbon_cost = qty * carbon_unit
        record.lane_fixed_cost = lane_fixed

        record.total_lane_cost = (
            record.freight_cost
            + record.insurance_cost
            + record.tariff_cost
            + record.customs_cost
            + record.risk_cost
            + record.carbon_cost
            + record.lane_fixed_cost
        )
        record.unit_lane_cost = record.total_lane_cost / qty if qty > 0 else 0.0

        record.extra = {
            "transport_mode": lane.get("transport_mode"),
            "lead_time_days": lane.get("lead_time_days"),
            "declared_unit_value": unit_value,
        }

        return record

    def allocate_fixed_costs(
        self,
        *,
        scenario_id: Optional[str] = None,
        node_cost_records: Sequence[NodeCostRecord],
    ) -> Dict[Tuple[str, str, int], float]:
        """
        Minimal placeholder for allocation rule application.

        Current behavior:
            returns zero allocation for every record.

        Future direction:
            - read allocation_rule_master
            - allocate plant / warehouse / HQ costs
            - support qty / revenue / inventory bases
        """
        allocations: Dict[Tuple[str, str, int], float] = {}
        for rec in node_cost_records:
            key = (rec.product_id, rec.node_id, rec.week)
            allocations[key] = 0.0
        return allocations

    def apply_lane_costs_to_nodes(
        self,
        *,
        node_cost_records: Sequence[NodeCostRecord],
        lane_cost_records: Sequence[LaneCostRecord],
        mode: str = "to_node",
    ) -> List[NodeCostRecord]:
        """
        Inject lane cost into node records.

        mode:
            "to_node"   -> charge logistics cost to arrival node
            "from_node" -> charge logistics cost to departure node
            "split"     -> half/half
        """
        idx: Dict[Tuple[str, str, int], NodeCostRecord] = {
            (r.product_id, r.node_id, r.week): r for r in node_cost_records
        }

        for lane_rec in lane_cost_records:
            total = lane_rec.total_lane_cost

            if mode == "to_node":
                key = (lane_rec.product_id, lane_rec.to_node_id, lane_rec.week)
                if key in idx:
                    idx[key].logistics_cost += total

            elif mode == "from_node":
                key = (lane_rec.product_id, lane_rec.from_node_id, lane_rec.week)
                if key in idx:
                    idx[key].logistics_cost += total

            elif mode == "split":
                half = total / 2.0
                key_from = (lane_rec.product_id, lane_rec.from_node_id, lane_rec.week)
                key_to = (lane_rec.product_id, lane_rec.to_node_id, lane_rec.week)
                if key_from in idx:
                    idx[key_from].logistics_cost += half
                if key_to in idx:
                    idx[key_to].logistics_cost += half

            else:
                raise ValueError(f"Unsupported mode: {mode}")

        # logistics cost changed, so recompute profits only
        updated: List[NodeCostRecord] = []
        for rec in idx.values():
            self._recompute_profit_fields(rec)
            updated.append(rec)

        return updated

    def summarize_total(
        self,
        *,
        scenario_id: Optional[str] = None,
        period_key: str,
        node_cost_records: Sequence[NodeCostRecord],
    ) -> TotalCostSummary:
        scenario = scenario_id or self.default_scenario_id
        out = TotalCostSummary(
            scenario_id=scenario,
            period_key=period_key,
        )

        for rec in node_cost_records:
            out.total_revenue += rec.revenue
            out.total_material_cost += rec.material_cost
            out.total_purchase_cost += rec.purchase_cost
            out.total_production_cost += rec.production_cost
            out.total_logistics_cost += rec.logistics_cost
            out.total_inventory_holding_cost += rec.inventory_holding_cost
            out.total_sga_variable_cost += rec.sga_variable_cost
            out.total_sga_fixed_cost += rec.sga_fixed_cost
            out.total_marketing_variable_cost += rec.marketing_variable_cost
            out.total_marketing_fixed_cost += rec.marketing_fixed_cost
            out.total_depreciation_cost += rec.depreciation_cost
            out.total_allocated_fixed_cost += rec.allocated_fixed_cost
            out.total_tax_cost += rec.tax_cost
            out.total_gross_profit += rec.gross_profit
            out.total_operating_profit += rec.operating_profit

        return out

    # --------------------------------------------------------
    # helpers
    # --------------------------------------------------------
    def _normalize_qty_ctx(self, qty_ctx: Mapping[str, Any]) -> Dict[str, float]:
        p_qty = self._f(qty_ctx.get("P_qty"))
        s_qty = self._f(qty_ctx.get("S_qty"))
        i_begin = self._f(qty_ctx.get("I_begin"))
        i_end = self._f(qty_ctx.get("I_end"))
        avg_inventory = self._f(qty_ctx.get("avg_inventory"))
        purchase_qty = self._f(qty_ctx.get("purchase_qty"))
        ship_qty = self._f(qty_ctx.get("ship_qty"))
        served_qty = self._f(qty_ctx.get("served_qty"))
        logistics_cost = self._f(qty_ctx.get("logistics_cost"))
        allocated_fixed_cost = self._f(qty_ctx.get("allocated_fixed_cost"))

        if avg_inventory == 0.0:
            avg_inventory = (i_begin + i_end) / 2.0

        if purchase_qty == 0.0:
            purchase_qty = p_qty

        if ship_qty == 0.0:
            ship_qty = s_qty

        if served_qty == 0.0:
            served_qty = s_qty

        return {
            "P_qty": p_qty,
            "S_qty": s_qty,
            "I_begin": i_begin,
            "I_end": i_end,
            "avg_inventory": avg_inventory,
            "purchase_qty": purchase_qty,
            "ship_qty": ship_qty,
            "served_qty": served_qty,
            "logistics_cost": logistics_cost,
            "allocated_fixed_cost": allocated_fixed_cost,
        }

    def _recompute_profit_fields(self, rec: NodeCostRecord) -> None:
        pretax_operating = (
            rec.revenue
            - rec.material_cost
            - rec.purchase_cost
            - rec.production_cost
            - rec.logistics_cost
            - rec.inventory_holding_cost
            - rec.sga_variable_cost
            - rec.sga_fixed_cost
            - rec.marketing_variable_cost
            - rec.marketing_fixed_cost
            - rec.depreciation_cost
            - rec.allocated_fixed_cost
        )
        tax_rate = self._f(rec.extra.get("tax_rate"))
        rec.tax_cost = max(0.0, pretax_operating) * tax_rate
        rec.gross_profit = (
            rec.revenue
            - rec.material_cost
            - rec.purchase_cost
            - rec.production_cost
            - rec.logistics_cost
            - rec.inventory_holding_cost
        )
        rec.operating_profit = pretax_operating - rec.tax_cost

    def _require_product(self, product_id: str) -> Dict[str, Any]:
        row = find_product_master(self.masters, product_id=product_id)
        if row is None:
            raise KeyError(f"Product master not found: {product_id}")
        return row

    def _require_node(self, node_id: str) -> Dict[str, Any]:
        row = find_node_master(self.masters, node_id=node_id)
        if row is None:
            raise KeyError(f"Node master not found: {node_id}")
        return row

    def _require_lane(
        self,
        *,
        scenario_id: str,
        from_node_id: str,
        to_node_id: str,
    ) -> Dict[str, Any]:
        row = find_lane_master(
            self.masters,
            scenario_id=scenario_id,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
        )
        if row is None:
            raise KeyError(
                f"Lane master not found: scenario={scenario_id}, "
                f"from={from_node_id}, to={to_node_id}"
            )
        return row

    def _resolve_sales_price(
        self,
        *,
        scenario_id: str,
        product_id: str,
        market_id: Optional[str],
        fallback: float,
    ) -> float:
        if not market_id:
            return fallback

        row = find_sales_price_master(
            self.masters,
            scenario_id=scenario_id,
            product_id=product_id,
            market_id=market_id,
        )
        if row is None:
            return fallback

        base_price = self._f(row.get("sales_price"))
        rebate_rate = self._f(row.get("rebate_rate"))
        discount_rate = self._f(row.get("discount_rate"))
        gross_to_net = self._f(row.get("gross_to_net_adjustment"))
        expected_return_rate = self._f(row.get("expected_return_rate"))

        net_factor = 1.0 - rebate_rate - discount_rate - gross_to_net - expected_return_rate
        net_factor = max(0.0, net_factor)
        return base_price * net_factor

    def _find_sga_scope(
        self,
        *,
        scenario_id: str,
        node_id: str,
        market_id: Optional[str],
    ) -> Dict[str, Any]:
        """
        Priority:
          1. market scope
          2. node scope
          3. empty defaults
        """
        if market_id:
            key = (scenario_id, "market", market_id)
            if key in self.masters.sga_by_scope:
                return self.masters.sga_by_scope[key]

        node_key = (scenario_id, "node", node_id)
        if node_key in self.masters.sga_by_scope:
            return self.masters.sga_by_scope[node_key]

        corporate_key = (scenario_id, "corporate", "HQ")
        if corporate_key in self.masters.sga_by_scope:
            return self.masters.sga_by_scope[corporate_key]

        return {}

    def _resolve_node_depreciation_cost(self, *, node_id: str) -> float:
        total = 0.0

        node_master = self.masters.node_by_id.get(node_id)
        if node_master:
            total += self._f(node_master.get("depreciation_cost_per_period"))

        for row in self.masters.fixed_asset_rows:
            if str(row.get("node_id") or "").strip() == node_id:
                total += self._f(row.get("depreciation_per_period"))

        return total

    def _resolve_tax_rate(self, sga_scope: Mapping[str, Any]) -> float:
        return (
            self._f(sga_scope.get("corporate_tax_rate"))
            + self._f(sga_scope.get("local_tax_rate"))
            + self._f(sga_scope.get("import_tax_rate"))
        )

    def _f(self, value: Any) -> float:
        if value is None:
            return 0.0
        try:
            return float(value)
        except Exception:
            return 0.0
```

---

## 使い方イメージ

```python
from pysi.cost.load_cost_masters import load_cost_masters
from pysi.cost.cost_engine import CostEngine

masters = load_cost_masters("./data/cost_masters")
engine = CostEngine(masters=masters, default_scenario_id="BASE")

node_rec = engine.compute_node_cost(
    product_id="IPHONE_STD",
    node_id="MOM_JP",
    week=25,
    market_id="US",
    qty_ctx={
        "P_qty": 120,
        "S_qty": 100,
        "I_begin": 30,
        "I_end": 50,
        "avg_inventory": 40,
    },
)

lane_rec = engine.compute_lane_cost(
    product_id="IPHONE_STD",
    from_node_id="MOM_JP",
    to_node_id="DAD_EU",
    week=25,
    shipment_qty=100,
)

node_rec_2 = engine.compute_node_cost(
    product_id="IPHONE_STD",
    node_id="DAD_EU",
    week=25,
    market_id="US",
    qty_ctx={
        "P_qty": 0,
        "S_qty": 100,
        "I_begin": 80,
        "I_end": 60,
        "avg_inventory": 70,
    },
)

updated_nodes = engine.apply_lane_costs_to_nodes(
    node_cost_records=[node_rec, node_rec_2],
    lane_cost_records=[lane_rec],
    mode="to_node",
)

summary = engine.summarize_total(
    period_key="2026-W25",
    node_cost_records=updated_nodes,
)

print(node_rec.to_dict())
print(lane_rec.to_dict())
print(summary.to_dict())
```

---

## この skeleton の考え方

この最小版は、かなり意図的に **「管理会計の初版」** に寄せています。

まず node で計算するものは、

* revenue
* material_cost
* purchase_cost
* production_cost
* inventory_holding_cost
* SG&A
* marketing
* depreciation
* allocated_fixed_cost
* tax
* gross_profit
* operating_profit

です。

そして lane で計算するものは、

* freight
* insurance
* tariff
* customs
* risk
* carbon
* lane fixed cost

です。

つまり、

**node で発生する費用** と
**lane で発生する費用**
を分けて持つ設計です。

これは前回の master 設計と噛み合っています。

---

## 今の時点での割り切り

この skeleton では、まだ次の部分は deliberately 軽くしています。

### 1. 固定費配賦

`allocate_fixed_costs()` は placeholder です。
ここは `allocation_rule_master.csv` を本格利用する段階で厚くすれば十分です。

### 2. lot 単位コスト追跡

今は `product × node × week` です。
Now フェーズとしてはこれで十分です。

### 3. FX / tariff master の高度利用

lane 側で `tariff_rate` をそのまま使っています。
将来は country pair や period を見て引く形へ拡張できます。

---

## 先に見つけておくとよいポイント

この skeleton で実装を始めると、最初に効いてくる論点はたぶんこの3つです。

### A. 材料費をどこで持つか

今は `P_qty × standard_material_cost` にしています。
製品によっては、

* 調達 node で持つ
* 生産 node で持つ
  の考え方が分かれるので、ここは後で固定するとよいです。

### B. 減価償却の二重計上

`node_cost_master` と `fixed_asset_cost_master` の両方に減価償却が入るので、
運用ではどちらを正本にするか決めた方が安全です。
今は skeleton なので両方足しています。

### C. lane cost をどちらの node に寄せるか

`apply_lane_costs_to_nodes()` では

* 到着 node
* 出発 node
* split

を選べるようにしています。
ここは管理会計の見せ方に直結します。

---

## 次に自然につながるもの

この `cost_engine.py` の次は、かなり自然に次のどちらかです。

### 1. `validate_cost_masters()`

network node / edge と master の整合を確認する関数です。
かなり実務的に効きます。

### 2. `cost_to_kpi_adapter.py`

`NodeCostRecord` や `TotalCostSummary` を、

* `node.sales_amount`
* `node.production_cost`
* `total_sc.operating_profit`
  のような KPI へ渡す橋です。

今の流れなら、次は **`cost_to_kpi_adapter.py` の最小 skeleton** がかなりきれいにつながります。
