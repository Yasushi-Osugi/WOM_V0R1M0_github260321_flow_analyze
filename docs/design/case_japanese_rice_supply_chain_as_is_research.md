# Japanese Rice Supply Chain AS-IS Research Memo

**Version:** v0r1 draft  
**Date:** 2026-05-14  
**Status:** Research memo / modeling preparation  
**Target path:** `docs/design/case_japanese_rice_supply_chain_as_is_research.md`

---

## 1. Purpose

This memo defines the AS-IS research framework for modeling the Japanese rice supply chain as a WOM case study.

The purpose is not to complete a full industry white paper. The purpose is to identify the minimum real-world structure required to model Japanese rice supply chain behavior in WOM.

```text
real-world rice supply chain
    ↓
AS-IS research memo
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

The final goal is to answer the next-step promise from the earlier Rice Case note article:

```text
How should the rice supply chain scenario be simulated in WOM / PSI Planner?

How should parameters be set?

How should cost and price sensitivity be evaluated?

How should scenarios be compared and prioritized?
```

Reference note:

```text
米のサプライチェーンを可視化する: 5つの視座で描く未来戦略
https://note.com/osuosu1123/n/n89402e2c8ef8
```

---

## 2. Scope

### 2.1 Target Scope

The initial AS-IS research should focus on the Japanese domestic rice supply chain.

Target flow:

```text
Producer / farm
    ↓
collection / drying / adjustment
    ↓
brown rice storage
    ↓
milling
    ↓
packaging
    ↓
wholesale
    ↓
retail / food service
    ↓
final consumption
```

The focus is on:

- harvested rice
- brown rice
- milled rice
- packaged rice
- domestic distribution
- inventory and storage
- cost and price structure
- demand and consumption
- scenario planning

### 2.2 Out of Scope for the First AS-IS Memo

The first memo does not need to fully model:

- individual farmer-level operations
- detailed crop cultivation process
- detailed subsidy / policy mechanism
- full global rice trade network
- exact government reserve release mechanics
- detailed regional retail price formation
- all varieties and grades

These can be added later.

---

## 3. Research Positioning

This AS-IS research memo is a bridge between narrative case understanding and WOM modeling.

It should answer:

```text
What exists in the real world?
    ↓
What should be represented in WOM?
    ↓
What should become node / lane / product / lot / PSI / capacity / cost / KPI?
```

This memo should not be confused with the final WOM master dataset.

The relationship is:

```text
AS-IS research:
    describes real-world structure

WOM Case Modeling Base Dataset:
    standardizes modeling entities

Rice Case Master Dataset:
    defines actual CSVs for this case

Current WOM CSV Adapter:
    transforms case dataset into current WOM engine inputs
```

---

## 4. Key Characteristics of Rice Supply Chain

Japanese rice supply chain has several characteristics that make it a strong WOM case.

### 4.1 Seasonal supply concentration

Rice production is highly seasonal.

A large volume of supply appears around harvest season.

WOM implication:

```text
P increases sharply around harvest season
I increases after harvest
S continues through the year
I decreases gradually as demand is fulfilled
```

This is one of the clearest examples of PSI behavior.

### 4.2 Inventory-heavy structure

Rice must be stored across the year.

Inventory is not just a passive result. Inventory is a central economic object.

WOM implication:

```text
inventory_qty
inventory_value
storage_capacity
storage_cost
inventory_age
quality deterioration risk
```

should be modeled explicitly.

### 4.3 Product transformation

Rice changes form through the supply chain.

Typical forms:

```text
paddy rice
brown rice
milled rice
packaged rice
cooked rice / food-service demand
```

Initial WOM modeling may simplify this into:

```text
brown rice
milled rice
packaged rice
```

### 4.4 Quality / brand differentiation

Rice is not a single homogeneous product.

Examples:

```text
premium branded rice
standard domestic rice
government reserve rice
imported rice
food-service rice
```

WOM implication:

```text
product_id
grade
brand
origin_region
price class
quality class
```

should be represented.

### 4.5 Cost and price structure

The Rice Case is not only a quantity simulation.

It should connect quantity PSI with money evaluation.

Important cost / price elements:

```text
purchase price
drying / adjustment cost
storage cost
milling cost
packaging cost
transport cost
wholesale margin
retail price
food-service selling price
inventory holding cost
cash conversion pressure
```

### 4.6 Policy and institutional factors

Rice has strong policy and institutional dimensions.

Examples:

```text
government reserve rice
imported rice / minimum access rice
food security considerations
price stabilization
domestic production sustainability
```

WOM implication:

Some areas should be treated as:

```text
LET IT BE:
    intentionally not optimized or not directly changed
```

This connects to the AS IS / TO BE / CAN BE / WILL BE / LET IT BE scenario framework.

---

## 5. Supply Chain Players

The following players should be considered.

### 5.1 Producer / Farm

Role:

```text
produce rice
harvest rice
ship paddy or brown rice to collection / JA / buyer
```

WOM candidate node type:

```text
PRODUCER
```

Initial modeling level:

```text
aggregate producer region
```

rather than individual farms.

### 5.2 Collection / JA / Aggregator

Role:

```text
collect rice from producers
perform drying / adjustment
aggregate lots
manage initial storage
sell or transfer to wholesalers / processors
```

WOM candidate node type:

```text
COLLECTION_CENTER
JA_AGGREGATOR
```

### 5.3 Storage / Warehouse

Role:

```text
store brown rice or milled rice
hold seasonal inventory
manage quality and inventory age
```

WOM candidate node type:

```text
BROWN_RICE_STORAGE
MILLED_RICE_STORAGE
```

### 5.4 Milling / Processing

Role:

```text
mill brown rice into milled rice
adjust product grade / packaging specification
```

WOM candidate node type:

```text
MILLING_NODE
```

### 5.5 Packaging

Role:

```text
package rice into consumer or business-use units
```

WOM candidate node type:

```text
PACKAGING_NODE
```

### 5.6 Wholesaler

Role:

```text
procure rice
hold inventory
sell to retail / food service
```

WOM candidate node type:

```text
WHOLESALER
```

### 5.7 Retail / Food Service

Role:

```text
retail sales to household
supply food-service demand
```

WOM candidate node type:

```text
RETAIL
FOOD_SERVICE
```

### 5.8 Final Demand

Role:

```text
household consumption
restaurant / food-service consumption
institutional consumption
```

WOM candidate node type:

```text
DEMAND_MARKET
```

---

## 6. Physical Flow

### 6.1 Conceptual Physical Flow

```text
paddy / harvested rice
    ↓
drying / adjustment
    ↓
brown rice
    ↓
storage
    ↓
milling
    ↓
milled rice
    ↓
packaging
    ↓
wholesale
    ↓
retail / food service
    ↓
consumption
```

### 6.2 Initial WOM Simplification

For the first WOM case, use the following simplified product transformation.

```text
BROWN_RICE
    ↓ milling
MILLED_RICE
    ↓ packaging / distribution
PACKAGED_RICE
    ↓ demand
CONSUMED_RICE
```

WOM does not need to represent every physical process in the first case.

The initial focus should be:

```text
seasonal supply
inventory accumulation
inventory drawdown
milling / shipment capacity
cost / price evaluation
```

---

## 7. Time Structure

### 7.1 Weekly Bucket

WOM uses weekly buckets.

Rice case should also be modeled weekly.

### 7.2 Harvest Season

The largest supply event occurs around harvest season.

In the initial model, the supply pattern can be simplified as:

```text
harvest weeks:
    large P input

non-harvest weeks:
    small or zero new production input
```

### 7.3 Annual Drawdown

Demand continues through the year.

Rice inventory is consumed gradually after harvest.

WOM implication:

```text
I rises sharply after harvest
I decreases gradually through weekly S
```

### 7.4 Modeling Horizon

Recommended initial horizon:

```text
52 weeks
```

Optional:

```text
104 weeks
```

for multi-year carryover and inventory aging.

---

## 8. PSI Interpretation for Rice

### 8.1 Producer / Collection Node

```text
P:
    harvested / collected rice lots

S:
    lots shipped to storage / mill / wholesaler

I:
    rice inventory at producer / collection node
```

### 8.2 Storage Node

```text
P:
    lots received into storage

S:
    lots released to milling / downstream distribution

I:
    stored rice inventory
```

### 8.3 Milling Node

```text
P:
    milling output or processed lots

S:
    lots shipped to packaging / wholesaler

I:
    milled rice inventory
```

### 8.4 Retail / Market Node

```text
P:
    lots received into retail / market node

S:
    lots sold / consumed

I:
    retail inventory
```

---

## 9. Capacity Structure

The following capacity candidates should be investigated.

### 9.1 Storage Capacity

```text
warehouse capacity
brown rice storage capacity
milled rice storage capacity
```

WOM relevance:

```text
I capacity
```

### 9.2 Milling Capacity

```text
weekly milling throughput
```

WOM relevance:

```text
P capacity or processing capacity
```

### 9.3 Packaging Capacity

```text
weekly packaging throughput
```

WOM relevance:

```text
P / S capacity
```

### 9.4 Transport Capacity

```text
regional transport capacity
lane capacity
```

WOM relevance:

```text
S capacity / flow capacity
```

### 9.5 Market Absorption Capacity

```text
weekly demand / sales capacity
```

WOM relevance:

```text
S demand / sales capacity
```

---

## 10. Cost and Price Structure

Rice Case should connect quantity planning to monetary evaluation.

### 10.1 Cost Elements

Candidate cost elements:

```text
purchase_cost
drying_adjustment_cost
storage_cost_per_lot_week
milling_cost
packaging_cost
transport_cost
wholesale_handling_cost
retail_handling_cost
inventory_holding_cost
waste_or_quality_loss_cost
```

### 10.2 Price Elements

Candidate price elements:

```text
producer_price
wholesale_price
retail_price
food_service_price
brand_premium_price
discount_price
```

### 10.3 Money Evaluation

WOM should evaluate:

```text
revenue
variable cost
gross profit
operating profit proxy
inventory value
cash conversion pressure
```

### 10.4 Sensitivity Analysis

Parameters for sensitivity analysis:

```text
selling_price
purchase_price
storage_cost
transport_cost
milling_cost
demand_qty
inventory_loss_rate
```

---

## 11. Policy and Institutional Factors

Rice supply chain includes policy-related elements.

Candidate areas:

```text
government reserve rice
imported rice
minimum access rice
food security policy
price stabilization
regional production support
domestic rice production sustainability
```

WOM modeling should separate:

```text
decision variables:
    can be changed in scenario

policy constraints:
    treated as external or LET IT BE
```

---

## 12. Scenario Framework

Use the five-view scenario structure.

### 12.1 AS IS

Purpose:

```text
understand current inventory, cost, revenue, and price structure
```

Focus:

```text
seasonal inventory accumulation
storage burden
profit by node / product
current price structure
```

### 12.2 TO BE

Purpose:

```text
define desirable future
```

Candidate themes:

```text
premium brand rice
export opportunity
higher value-added products
sustainable producer income
```

### 12.3 CAN BE

Purpose:

```text
define realistically executable options
```

Candidate actions:

```text
direct channel increase
storage cost reduction
milling / packaging efficiency improvement
brown rice distributed storage
demand smoothing
```

### 12.4 WILL BE

Purpose:

```text
show risks if no action is taken
```

Candidate risks:

```text
inventory overhang
price decline
profit margin decline
cash pressure
domestic rice demand decline
producer sustainability risk
```

### 12.5 LET IT BE

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

## 13. WOM Modeling Implications

### 13.1 Node Candidates

```text
PRODUCER_REGION
COLLECTION_CENTER
BROWN_RICE_STORAGE
MILLING_NODE
PACKAGING_NODE
WHOLESALER
RETAIL_MARKET
FOOD_SERVICE_MARKET
DEMAND_MARKET
```

### 13.2 Lane Candidates

```text
producer → collection
collection → storage
storage → milling
milling → packaging
packaging → wholesaler
wholesaler → retail
wholesaler → food_service
retail → demand
```

### 13.3 Product Candidates

```text
BROWN_RICE_STANDARD
MILLED_RICE_STANDARD
MILLED_RICE_PREMIUM
PACKAGED_RICE_STANDARD
PACKAGED_RICE_PREMIUM
RESERVE_RICE
IMPORTED_RICE
```

### 13.4 Lot Candidates

Lot should represent a meaningful planning unit.

Candidate lot header:

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
    "expiry_or_quality_limit_week": "2027-W40",
}
```

---

## 14. KPI Candidates

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

---

## 15. Research Questions

The following questions should be answered or treated as assumptions.

### 15.1 Network Questions

```text
What is the appropriate node granularity?
Should JA / collection be modeled explicitly?
Should storage and milling be separate nodes?
Should household and food-service markets be separated?
```

### 15.2 Product Questions

```text
How many rice product classes are required?
Should brown rice and milled rice be separate product IDs?
How should reserve rice and imported rice be represented?
```

### 15.3 Time Questions

```text
Which weeks represent harvest peak?
How should annual demand be distributed weekly?
How should old crop / new crop carryover be represented?
```

### 15.4 Cost / Price Questions

```text
What cost items are required for first money simulation?
Which prices are scenario parameters?
How should brand premium be represented?
```

### 15.5 Policy Questions

```text
Which constraints are LET IT BE?
Which variables can be changed in CAN BE scenarios?
How should government reserve rice be represented?
```

---

## 16. Data Sources to Investigate

This memo is an AS-IS research scaffold.

Actual data should be collected from reliable sources such as:

```text
MAFF statistics
rice supply-demand outlook
rice production statistics
rice inventory statistics
rice consumption statistics
rice price statistics
industry reports
retail price observations
logistics / storage cost assumptions
```

The first modeling version may use simplified assumptions.

However, all assumptions should be explicitly documented.

---

## 17. Open Assumptions for Initial Model

The first Rice Case model may start with these assumptions.

```text
one-year planning horizon
weekly bucket
single producer region or 2-3 producer regions
one collection node
one storage node
one milling node
one wholesaler
two demand markets:
    household
    food service
two product classes:
    standard rice
    premium rice
```

This is enough to test:

```text
harvest season inventory surge
annual inventory drawdown
storage cost accumulation
price sensitivity
profitability by product class
scenario comparison
```

---

## 18. Relationship with Future WOM Case Modeling Dataset

This AS-IS research memo should feed into:

```text
docs/design/wom_case_modeling_base_dataset.md
docs/design/case_japanese_rice_supply_chain_modeling.md
docs/design/case_japanese_rice_master_dataset.md
docs/design/case_japanese_rice_simulation_plan.md
```

The modeling flow should be:

```text
AS-IS research
    ↓
WOM Case Modeling Base Dataset
    ↓
Rice Case Modeling Design
    ↓
Rice Master Dataset
    ↓
Adapter to Current WOM CSV
    ↓
Simulation Plan
    ↓
Evaluation and Management Issue
```

---

## 19. Summary

Japanese rice supply chain is a strong WOM case because it combines:

```text
seasonal supply concentration
annual inventory drawdown
storage burden
processing / milling
distribution
price and cost structure
policy constraints
scenario planning
```

This AS-IS research memo is the first step toward turning the Rice Case into a full WOM Case Study.

The most important modeling insight is:

```text
Rice is not only a production quantity problem.

It is an annual PSI synchronization problem
between harvest concentration, storage capacity,
processing capacity, demand, price, cost, and policy constraints.
```

The next step is to define:

```text
docs/design/wom_case_modeling_base_dataset.md
```

and then map this AS-IS research into a structured Rice Case model.
