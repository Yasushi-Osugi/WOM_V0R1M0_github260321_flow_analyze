# Japanese Rice Supply Chain Modeling Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-15  
**Status:** Design memo  
**Target path:** `docs/design/case_japanese_rice_supply_chain_modeling.md`

**Related design documents:**

- `docs/design/case_japanese_rice_supply_chain_as_is_research.md`
- `docs/design/wom_case_modeling_base_dataset.md`
- `docs/design/wom_e2e_constraint_management.md`
- `docs/design/wom_planning_operations_commands.md`

---

## 1. Purpose

This memo defines how to model the **Japanese Rice Supply Chain** as a WOM case study.

The goal is to convert a real-world rice supply chain narrative into a structured WOM model that can support:

- PSI quantity simulation
- capacity-aware planning
- inventory evaluation
- cost / price sensitivity analysis
- KPI evaluation
- scenario comparison
- management issue generation

This memo is intended to answer the next-step promise from the earlier Rice Case note article:

```text
How should the rice supply chain scenario be simulated in WOM / PSI Planner?

How should parameters be set?

How should cost and price sensitivity be evaluated?

How should scenarios be compared and prioritized?
```

This memo does not attempt to reproduce the old PySI V0R8 Rice Model as-is.

Instead, it applies the current WOM Modeling Process:

```text
Real-world Supply Chain Case
    ↓
WOM Case Modeling Base Dataset
    ↓
Adapter
    ↓
WOM Planning Engine
    ↓
PSI / Capacity / Cost / KPI outputs
    ↓
Visualization
    ↓
Management Issue
```

---

## 2. Modeling Position

The Rice Case is a comprehensive WOM case because it includes:

- seasonal supply concentration
- annual inventory drawdown
- storage capacity
- milling / processing
- logistics
- price and cost structure
- policy and institutional factors
- scenario planning

The Rice Case is different from the COVID Vaccine Case.

```text
COVID Vaccine Case:
    Forward PUSH with Capacity demonstration
    focus = deliver and administer available lots under capacity constraints

Rice Case:
    full WOM Modeling Process demonstration
    focus = annual PSI synchronization, inventory, cost, price, and scenario evaluation
```

Therefore, the Rice Case should be used as a general template for WOM Case Modeling.

---

## 3. Scope

### 3.1 Phase 1 Scope

The first Rice Case model should focus on a simplified domestic Japanese rice supply chain.

Target flow:

```text
Producer Region
    ↓
Collection / JA / Aggregator
    ↓
Brown Rice Storage
    ↓
Milling
    ↓
Packaging
    ↓
Wholesaler
    ↓
Retail / Food Service
    ↓
Final Demand
```

Phase 1 should include:

- one-year planning horizon
- weekly buckets
- seasonal harvest supply
- annual demand
- inventory accumulation and drawdown
- storage capacity
- milling capacity
- transport capacity
- basic cost / price evaluation
- AS IS / TO BE / CAN BE / WILL BE / LET IT BE scenarios

### 3.2 Out of Scope for Phase 1

Phase 1 does not need to include:

- individual farm-level modeling
- detailed subsidy and policy accounting
- full national rice statistics integration
- all rice varieties and grades
- detailed government reserve operation
- full import rice trade model
- full optimization

These can be added later.

---

## 4. WOM Interpretation

### 4.1 Core Modeling Question

The core modeling question is:

```text
How does the Japanese rice supply chain synchronize
seasonal harvest supply,
annual demand,
inventory,
storage capacity,
processing capacity,
price,
cost,
and policy constraints
over weekly planning buckets?
```

### 4.2 Core WOM Interpretation

Rice is not only a production quantity problem.

It is an annual PSI synchronization problem:

```text
harvest concentration
    ↓
inventory buildup
    ↓
storage burden
    ↓
milling / packaging / shipment
    ↓
annual demand fulfillment
    ↓
cost / price / profit / cash evaluation
```

---

## 5. Network Definition

### 5.1 Initial Node Set

The first model should use a small but meaningful node set.

```text
PRODUCER_NIIGATA
    producer region

COLLECTION_NIIGATA
    collection / drying / adjustment

BROWN_STORAGE_EAST
    brown rice storage

MILL_EAST
    milling node

PACKAGING_EAST
    packaging node

WHOLESALER_EAST
    wholesale distribution

RETAIL_TOKYO
    household retail market

FOOD_SERVICE_TOKYO
    food service market

DEMAND_HOUSEHOLD_TOKYO
    household demand

DEMAND_FOOD_SERVICE_TOKYO
    food service demand
```

### 5.2 Optional Expansion Nodes

Later versions may add:

```text
PRODUCER_HOKKAIDO
PRODUCER_AKITA
PRODUCER_KYUSHU
BROWN_STORAGE_WEST
MILL_WEST
RETAIL_OSAKA
RETAIL_NAGOYA
EXPORT_MARKET
GOV_RESERVE_STORAGE
IMPORT_RICE_SUPPLY
```

---

## 6. Lane Definition

### 6.1 Initial Lane Set

```text
LANE_PRODUCER_TO_COLLECTION
    PRODUCER_NIIGATA → COLLECTION_NIIGATA

LANE_COLLECTION_TO_STORAGE
    COLLECTION_NIIGATA → BROWN_STORAGE_EAST

LANE_STORAGE_TO_MILL
    BROWN_STORAGE_EAST → MILL_EAST

LANE_MILL_TO_PACKAGING
    MILL_EAST → PACKAGING_EAST

LANE_PACKAGING_TO_WHOLESALER
    PACKAGING_EAST → WHOLESALER_EAST

LANE_WHOLESALER_TO_RETAIL
    WHOLESALER_EAST → RETAIL_TOKYO

LANE_WHOLESALER_TO_FOOD_SERVICE
    WHOLESALER_EAST → FOOD_SERVICE_TOKYO
```

### 6.2 Lane Attributes

Each lane should eventually carry:

```text
lane_id
from_node_id
to_node_id
transport_mode
leadtime_weeks
transport_capacity
transport_cost
is_alternative
priority
```

For the MVP, leadtime can be simplified to:

```text
leadtime_weeks = 1
```

---

## 7. Product Definition

### 7.1 Initial Product Classes

The first model should use a limited number of product classes.

```text
BROWN_RICE_STANDARD
MILLED_RICE_STANDARD
PACKAGED_RICE_STANDARD
PACKAGED_RICE_PREMIUM
```

### 7.2 Optional Product Classes

Later versions may add:

```text
BROWN_RICE_PREMIUM
MILLED_RICE_PREMIUM
FOOD_SERVICE_RICE
RESERVE_RICE
IMPORTED_RICE
EXPORT_RICE
```

### 7.3 Product Transformation

The simplified transformation chain is:

```text
BROWN_RICE_STANDARD
    ↓ milling
MILLED_RICE_STANDARD
    ↓ packaging
PACKAGED_RICE_STANDARD
    ↓ retail / food service demand
CONSUMED_RICE
```

For premium scenario:

```text
BROWN_RICE_PREMIUM
    ↓ milling
MILLED_RICE_PREMIUM
    ↓ packaging
PACKAGED_RICE_PREMIUM
```

---

## 8. Lot Definition

### 8.1 Rice Lot Concept

A rice lot should represent a meaningful planning unit.

Initial assumption:

```text
1 lot = 1,000 kg
```

This can be adjusted later.

### 8.2 Suggested Lot Header

```python
lot = {
    "lot_id": "RICE-JP-2026W40-000001",
    "product_id": "BROWN_RICE_STANDARD",
    "origin_region": "NIIGATA",
    "harvest_week": "2026-W40",
    "current_node": "COLLECTION_NIIGATA",
    "quality_grade": "standard",
    "brand_class": "domestic_standard",
    "quantity_kg": 1000,
    "available_week": "2026-W40",
    "due_week": "2026-W44",
    "expiry_or_quality_limit_week": "2027-W40",
    "quality_status": "usable",
    "priority": 100,
}
```

### 8.3 Required Lot Fields for MVP

```text
lot_id
product_id
quantity_kg
current_node
available_week
quality_status
```

### 8.4 Additional Lot Fields for Money / KPI Evaluation

```text
origin_region
quality_grade
brand_class
harvest_week
expiry_or_quality_limit_week
purchase_cost
current_inventory_value
target_market
```

---

## 9. PSI Definition for Rice

### 9.1 Producer / Collection Node

```text
P:
    harvested / collected rice lots

S:
    lots shipped to storage / mill / downstream node

I:
    rice inventory at producer / collection node
```

### 9.2 Storage Node

```text
P:
    lots received into storage

S:
    lots released to milling / downstream node

I:
    stored rice inventory
```

### 9.3 Milling Node

```text
P:
    milled output / processed lots

S:
    lots shipped to packaging / wholesaler

I:
    milled rice inventory
```

### 9.4 Retail / Food Service Node

```text
P:
    lots received into retail / food service node

S:
    lots sold / consumed

I:
    market-side inventory
```

### 9.5 Key PSI Pattern

The most important Rice PSI pattern is:

```text
Harvest season:
    P rises sharply
    I rises sharply

Post-harvest period:
    S continues weekly
    I declines gradually
```

This is the central visual pattern of the Rice Case.

---

## 10. Time Structure

### 10.1 Planning Horizon

Initial model:

```text
52 weeks
```

Optional extension:

```text
104 weeks
```

for multi-year carryover and old-crop / new-crop inventory.

### 10.2 Harvest Supply Pattern

Initial simplified supply pattern:

```text
W38-W44:
    harvest supply peak

Other weeks:
    no new harvest supply or small adjustment supply
```

### 10.3 Demand Pattern

Initial simplified demand pattern:

```text
weekly demand = annual demand / 52
```

Later versions can add:

```text
seasonal demand fluctuation
new year demand
food-service seasonality
tourism demand
school lunch demand
```

---

## 11. Capacity Definition

### 11.1 Storage Capacity

```text
storage_capacity:
    maximum inventory that storage node can hold
```

WOM mapping:

```text
I capacity
```

### 11.2 Milling Capacity

```text
milling_capacity:
    maximum weekly brown rice processing quantity
```

WOM mapping:

```text
P capacity or process capacity
```

### 11.3 Packaging Capacity

```text
packaging_capacity:
    maximum weekly packaged rice output
```

WOM mapping:

```text
P / S capacity
```

### 11.4 Transport Capacity

```text
transport_capacity:
    maximum weekly shipment through a lane
```

WOM mapping:

```text
flow capacity / S capacity
```

### 11.5 Market Absorption

```text
market_absorption:
    maximum weekly sales / consumption
```

WOM mapping:

```text
S demand / sales capacity
```

---

## 12. Cost and Price Model

### 12.1 Cost Categories

Initial cost categories:

```text
purchase_cost
drying_adjustment_cost
storage_cost_per_lot_week
milling_cost_per_lot
packaging_cost_per_lot
transport_cost_per_lot
wholesale_handling_cost
retail_handling_cost
inventory_holding_cost
quality_loss_cost
```

### 12.2 Price Categories

Initial price categories:

```text
producer_price
wholesale_price
retail_price
food_service_price
premium_brand_price
discount_price
```

### 12.3 Money Evaluation Outputs

WOM should calculate:

```text
revenue
variable_cost
storage_cost
transport_cost
gross_profit
operating_profit_proxy
inventory_value
cash_conversion_pressure
```

### 12.4 Sensitivity Parameters

Parameters for sensitivity analysis:

```text
selling_price
purchase_price
storage_cost
transport_cost
milling_cost
demand_qty
premium_price_uplift
inventory_loss_rate
```

---

## 13. Scenario Definitions

Use the five-view scenario framework.

### 13.1 AS IS

Purpose:

```text
understand current inventory, cost, revenue, and price structure
```

Typical parameters:

```text
current harvest volume
current demand
current price
current storage cost
current transport cost
current milling capacity
```

Expected outputs:

```text
inventory curve
storage burden
profitability
cash pressure
```

### 13.2 TO BE

Purpose:

```text
define desirable future
```

Candidate changes:

```text
premium brand strategy
higher selling price
export market addition
producer income improvement
inventory quality improvement
```

### 13.3 CAN BE

Purpose:

```text
define realistically executable actions
```

Candidate actions:

```text
storage cost reduction
milling capacity improvement
direct sales channel increase
demand smoothing
brown rice distributed storage
transport efficiency improvement
```

### 13.4 WILL BE

Purpose:

```text
show risks if no action is taken
```

Candidate assumptions:

```text
domestic rice demand decline
price decline
inventory overhang
storage cost increase
cash pressure
producer sustainability risk
```

### 13.5 LET IT BE

Purpose:

```text
define areas intentionally not optimized
```

Candidate areas:

```text
government reserve rice
minimum access rice
policy constraints
food security reserve
```

---

## 14. KPI and Evaluation

### 14.1 Quantity KPIs

```text
production_qty
shipment_qty
ending_inventory_qty
backlog_qty
fill_rate
stockout_qty
inventory_days
```

### 14.2 Capacity KPIs

```text
storage_utilization
milling_utilization
transport_utilization
capacity_concentration_index
```

### 14.3 Cost / Profit KPIs

```text
revenue
variable_cost
storage_cost
transport_cost
gross_profit
profit_margin
inventory_value
cash_conversion_pressure
```

### 14.4 Strategic KPIs

```text
customer_fulfillment_score
producer_sustainability_score
inventory_soundness_score
capacity_resilience_score
profit_sustainability_score
structural_sustainability_score
```

### 14.5 Scenario Comparison

Scenario comparison should use:

```text
baseline scenario
scenario result
KPIDelta
direction
significance
management issue
```

---

## 15. Visualization Design

### 15.1 PSI Curve

Show weekly:

```text
P
S
I
```

The Rice Case should clearly show:

```text
harvest peak P
post-harvest inventory I
annual shipment / consumption S
```

### 15.2 Inventory and Storage Capacity Chart

Show:

```text
inventory level
storage capacity
overflow risk
storage utilization
```

### 15.3 Cost and Profit Waterfall

Show:

```text
sales revenue
purchase cost
storage cost
milling cost
transport cost
gross profit
profit margin
```

### 15.4 Scenario Comparison Chart

Show:

```text
AS IS vs TO BE vs CAN BE vs WILL BE
```

using key KPIs such as:

```text
inventory_value
profit_margin
storage_cost
capacity_utilization
producer_sustainability_score
```

---

## 16. Adapter to Current WOM CSV

The Rice Case should use the WOM Case Modeling Base Dataset first.

Then an adapter converts it into current WOM inputs.

```text
Rice Case Master Dataset
    ↓
Adapter
    ↓
Current WOM CSV files / internal model
    ↓
WOM Planning Engine
```

Adapter responsibilities:

```text
node_master → current node master
lane_master → tree / edge definition
product_master → product list
lot_master / supply_plan / demand_plan → PSI seed data
capacity_master → current capacity master
cost_price_master → costing input
```

---

## 17. Master Dataset Required

The Rice Case should eventually define:

```text
rice_scenario_master.csv
rice_node_master.csv
rice_lane_master.csv
rice_product_master.csv
rice_lot_master.csv
rice_supply_plan.csv
rice_demand_plan.csv
rice_capacity_master.csv
rice_cost_price_master.csv
rice_kpi_policy_master.csv
rice_scenario_parameter_master.csv
rice_assumption_log.csv
```

These should follow the common definitions in:

```text
docs/design/wom_case_modeling_base_dataset.md
```

---

## 18. Initial MVP Model

### 18.1 MVP Scope

```text
single product:
    PACKAGED_RICE_STANDARD

one producer region:
    PRODUCER_NIIGATA

one collection node:
    COLLECTION_NIIGATA

one storage node:
    BROWN_STORAGE_EAST

one milling node:
    MILL_EAST

one wholesaler:
    WHOLESALER_EAST

two demand markets:
    RETAIL_TOKYO
    FOOD_SERVICE_TOKYO

52 weekly buckets
```

### 18.2 MVP Supply Pattern

```text
W40:
    large harvest supply input

W41-W44:
    additional harvest supply input

Other weeks:
    no production input
```

### 18.3 MVP Demand Pattern

```text
weekly household demand:
    constant weekly demand

weekly food-service demand:
    constant weekly demand
```

### 18.4 MVP Evaluation

MVP should evaluate:

```text
inventory buildup
inventory drawdown
storage cost
milling capacity utilization
gross profit
scenario delta vs AS IS
```

---

## 19. Implementation Roadmap

### Phase 1: Modeling Design

```text
case_japanese_rice_supply_chain_as_is_research.md
case_japanese_rice_supply_chain_modeling.md
case_japanese_rice_master_dataset.md
case_japanese_rice_simulation_plan.md
```

### Phase 2: Master Dataset

Create sample Rice master CSV files.

### Phase 3: Adapter

Convert Rice Case Master Dataset into current WOM input.

### Phase 4: Smoke Runner

Run small PSI simulation.

### Phase 5: Cost / Price Sensitivity

Add money evaluation.

### Phase 6: Scenario Comparison

Compare AS IS / TO BE / CAN BE / WILL BE / LET IT BE.

### Phase 7: Note Article Draft

Answer the earlier Rice Case note article's next-step promise.

---

## 20. Relationship with Note Article

This model should support a follow-up note article.

Proposed title:

```text
米のサプライチェーンをWOMでシミュレーションする
――パラメータ設定、価格感度分析、シナリオ比較の実例
```

The article should answer:

```text
1. How the Rice Case is modeled
2. What master data is prepared
3. How AS IS is simulated
4. How cost / price sensitivity is added
5. How scenarios are compared
6. What management issues are revealed
```

---

## 21. Summary

The Japanese Rice Supply Chain Case is a core WOM modeling case.

It demonstrates:

```text
seasonal supply concentration
annual inventory drawdown
storage burden
capacity constraints
cost / price evaluation
scenario comparison
management issue generation
```

The key message is:

```text
Rice is not only a production quantity problem.

It is an annual PSI synchronization problem
between harvest concentration, storage capacity,
processing capacity, demand, price, cost, and policy constraints.
```

The next design memo should be:

```text
docs/design/case_japanese_rice_master_dataset.md
```

which defines the concrete CSV schemas and sample rows for the Rice Case.
