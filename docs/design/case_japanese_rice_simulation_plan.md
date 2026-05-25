# Japanese Rice Case Simulation Plan Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-15  
**Status:** Design memo  
**Target path:** `docs/design/case_japanese_rice_simulation_plan.md`

**Related design documents:**

- `docs/design/case_japanese_rice_supply_chain_as_is_research.md`
- `docs/design/wom_case_modeling_base_dataset.md`
- `docs/design/case_japanese_rice_supply_chain_modeling.md`
- `docs/design/case_japanese_rice_master_dataset.md`
- `docs/design/wom_e2e_constraint_management.md`
- `docs/design/wom_planning_operations_commands.md`

---

## 1. Purpose

This memo defines the simulation plan for the **Japanese Rice Supply Chain WOM Case Study**.

The purpose is to answer the next-step promise from the earlier Rice Case note article:

```text
How should the rice supply chain scenario be simulated in WOM / PSI Planner?

How should parameters be set?

How should cost and price sensitivity be evaluated?

How should scenarios be compared and prioritized?
```

This memo defines:

- simulation objectives
- scenario set
- parameter settings
- quantity PSI simulation approach
- cost / price sensitivity approach
- KPI and evaluation approach
- scenario comparison and prioritization method
- expected charts and reports
- implementation roadmap

This memo is not yet the implementation request.

It is a design bridge between Rice Case master data and WOM execution.

---

## 2. Simulation Philosophy

The Rice Case should demonstrate WOM as a modeling and simulation method, not just as a Python tool.

The intended flow is:

```text
Rice Supply Chain AS-IS Research
    ↓
Rice Case Master Dataset
    ↓
Adapter
    ↓
WOM Planning Engine
    ↓
Quantity PSI Simulation
    ↓
Cost / Price Evaluation
    ↓
KPI Delta vs Baseline
    ↓
Scenario Comparison
    ↓
Management Issue Generation
```

The key idea is:

```text
Rice is not only a production quantity problem.

It is an annual PSI synchronization problem
between harvest concentration, storage capacity,
processing capacity, demand, price, cost, and policy constraints.
```

---

## 3. Simulation Scope

### 3.1 Initial MVP Scope

The first simulation should be intentionally small.

```text
planning horizon:
    52 weeks

products:
    PACKAGED_RICE_STANDARD

producer region:
    PRODUCER_NIIGATA

nodes:
    PRODUCER_NIIGATA
    COLLECTION_NIIGATA
    BROWN_STORAGE_EAST
    MILL_EAST
    PACKAGING_EAST
    WHOLESALER_EAST
    RETAIL_TOKYO
    FOOD_SERVICE_TOKYO
    DEMAND_HOUSEHOLD_TOKYO
    DEMAND_FOOD_SERVICE_TOKYO

demand markets:
    household
    food service
```

### 3.2 Later Expansion Scope

Later versions may add:

- multiple producer regions
- premium rice product
- reserve rice
- imported rice
- export market
- multiple retail regions
- regional storage alternatives
- detailed policy constraints
- E2E Evaluation and Management Issue Generation

---

## 4. Baseline Scenario: RICE_AS_IS

### 4.1 Purpose

`RICE_AS_IS` defines the baseline simulation.

It is the reference scenario for all comparisons.

### 4.2 Basic Assumptions

```text
scenario_id:
    RICE_AS_IS

planning horizon:
    2026-W01 to 2026-W52

supply:
    harvest concentrated in W40-W44

demand:
    stable weekly demand

product:
    PACKAGED_RICE_STANDARD

cost:
    current assumed purchase / storage / milling / packaging / transport costs

price:
    current assumed selling price
```

### 4.3 Baseline Parameters

The first parameter values can be simplified assumptions.

They should later be replaced by real data.

```text
lot_size:
    1 lot = 1,000 kg

harvest supply:
    W40: 20 lots
    W41: 30 lots
    W42: 30 lots
    W43: 15 lots
    W44: 5 lots
    total: 100 lots

weekly household demand:
    1.0 lot / week

weekly food-service demand:
    0.6 lot / week

annual demand:
    83.2 lots
```

### 4.4 Expected AS-IS Behavior

Expected PSI pattern:

```text
Before harvest:
    inventory is low or carried over from prior year

Harvest weeks:
    P increases sharply
    I increases sharply

Post-harvest:
    S continues weekly
    I declines gradually
```

Expected management insight:

```text
AS-IS shows the inventory burden and cash pressure created by seasonal harvest concentration.
```

---

## 5. Scenario Framework

The simulation should use the five-view scenario framework.

```text
AS IS
TO BE
CAN BE
WILL BE
LET IT BE
```

Each scenario should change a limited set of parameters so that results are explainable.

---

## 6. Scenario 1: AS IS

### 6.1 Purpose

Understand the current structure.

### 6.2 Parameters

```text
harvest_qty:
    baseline

weekly_demand:
    baseline

selling_price:
    baseline

storage_cost:
    baseline

milling_cost:
    baseline

transport_cost:
    baseline

capacity:
    baseline
```

### 6.3 Main KPIs

```text
ending_inventory_qty
inventory_value
storage_cost
gross_profit
profit_margin
cash_conversion_pressure
fill_rate
```

### 6.4 Expected Findings

```text
seasonal inventory buildup
annual inventory drawdown
storage burden
baseline profit structure
cash tied up in inventory
```

---

## 7. Scenario 2: TO BE

### 7.1 Purpose

Evaluate a desirable future strategy.

Potential theme:

```text
premium rice / brand value strategy
```

### 7.2 Parameter Changes

Example:

```text
premium_product_mix:
    increase

selling_price:
    +10%

packaging_cost:
    +3%

marketing / brand cost:
    optional future parameter

demand:
    slightly lower volume, higher price
```

### 7.3 Main KPIs

```text
sales_amount
gross_profit
profit_margin
inventory_value
premium_mix_ratio
producer_sustainability_score
profit_sustainability_score
```

### 7.4 Expected Findings

```text
higher price may improve profit margin
premium strategy may reduce volume risk
inventory quality and brand management become important
```

---

## 8. Scenario 3: CAN BE

### 8.1 Purpose

Evaluate realistically executable operational improvements.

Potential theme:

```text
storage cost reduction and inventory control
```

### 8.2 Parameter Changes

Example:

```text
storage_cost_per_lot_week:
    -15%

milling_capacity:
    +10%

transport_cost:
    -5%

demand_smoothing:
    optional
```

### 8.3 Main KPIs

```text
storage_cost
inventory_value
capacity_utilization
gross_profit
cash_conversion_pressure
inventory_soundness_score
```

### 8.4 Expected Findings

```text
storage cost reduction improves cash pressure
capacity improvement may reduce bottleneck risk
operational improvements may be more feasible than price reform
```

---

## 9. Scenario 4: WILL BE

### 9.1 Purpose

Evaluate risk if no corrective action is taken.

Potential theme:

```text
domestic demand decline and inventory overhang
```

### 9.2 Parameter Changes

Example:

```text
household demand:
    -10%

food-service demand:
    -5%

selling_price:
    -5%

storage_cost:
    unchanged or +5%

harvest_qty:
    unchanged
```

### 9.3 Main KPIs

```text
ending_inventory_qty
inventory_value
storage_cost
stockout_qty
backlog_qty
gross_profit
profit_margin
cash_conversion_pressure
producer_sustainability_score
```

### 9.4 Expected Findings

```text
demand decline creates inventory overhang
price decline worsens profit margin
cash conversion pressure increases
producer sustainability weakens
```

---

## 10. Scenario 5: LET IT BE

### 10.1 Purpose

Identify areas that should not be directly optimized in the first simulation.

Potential theme:

```text
policy reserve / minimum access / food security constraints
```

### 10.2 Treatment

In WOM, LET IT BE areas should be modeled as external constraints or reference flows, not decision variables.

Examples:

```text
government reserve rice:
    external policy constraint

minimum access rice:
    external import / policy constraint

food security reserve:
    not optimized by business scenario
```

### 10.3 Main KPIs

```text
reserve_inventory_qty
policy_constrained_qty
structural_sustainability_score
food_security_buffer_indicator
```

### 10.4 Expected Findings

```text
some flows should remain outside direct operational optimization
policy constraints should be visible but not necessarily changed
```

---

## 11. Parameter Setting

### 11.1 Parameter Categories

Rice simulation parameters should be grouped as:

```text
supply parameters
demand parameters
capacity parameters
cost parameters
price parameters
scenario policy parameters
KPI weight parameters
```

### 11.2 Supply Parameters

```text
harvest_qty_by_week
producer_region_mix
product_mix
old_crop_carryover_qty
```

### 11.3 Demand Parameters

```text
weekly_household_demand
weekly_food_service_demand
demand_growth_rate
demand_decline_rate
seasonality_factor
```

### 11.4 Capacity Parameters

```text
storage_capacity
milling_capacity
packaging_capacity
transport_capacity
market_absorption_capacity
```

### 11.5 Cost Parameters

```text
purchase_cost
storage_cost_per_lot_week
milling_cost_per_lot
packaging_cost_per_lot
transport_cost_per_lot
inventory_holding_cost
quality_loss_cost
```

### 11.6 Price Parameters

```text
selling_price_standard
selling_price_premium
discount_price
food_service_price
export_price
```

### 11.7 KPI Weight Parameters

```text
w_profit
w_inventory
w_customer_fulfillment
w_producer_sustainability
w_capacity_resilience
```

These should be scenario-configurable.

---

## 12. Cost / Price Sensitivity Analysis

### 12.1 Purpose

Cost / price sensitivity analysis evaluates how changes in price and cost assumptions affect economic outcomes.

### 12.2 Target Variables

Recommended first sensitivity variables:

```text
selling_price
storage_cost
transport_cost
milling_cost
demand_qty
```

### 12.3 Simple Sensitivity Grid

Example:

| Parameter | Low | Base | High |
|---|---:|---:|---:|
| selling_price | -10% | 0% | +10% |
| storage_cost | -15% | 0% | +15% |
| demand_qty | -10% | 0% | +10% |
| transport_cost | -10% | 0% | +10% |

### 12.4 Sensitivity Output

The sensitivity result should show:

```text
gross_profit change
profit_margin change
inventory_value change
cash_conversion_pressure change
storage_cost change
fill_rate change
```

### 12.5 Example Interpretation

```text
If selling price increases by 10%:
    profit margin improves,
    but demand may decline depending on elasticity.

If storage cost increases by 15%:
    inventory burden becomes a major management issue.

If demand declines by 10%:
    inventory overhang and cash pressure increase.
```

---

## 13. Simulation Execution Flow

### 13.1 Standard Flow

```text
load Rice Case Master Dataset
    ↓
apply scenario parameters
    ↓
adapter to current WOM input
    ↓
run WOM planning engine
    ↓
generate PSI outputs
    ↓
calculate cost / price evaluation
    ↓
calculate KPIs
    ↓
compare against baseline
    ↓
generate management issues
```

### 13.2 AS-IS First Principle

All scenario comparison should start from `RICE_AS_IS`.

```text
RICE_AS_IS:
    baseline result

scenario:
    compared against RICE_AS_IS
```

### 13.3 Scenario Comparison Flow

```text
run RICE_AS_IS
    ↓
run selected scenario
    ↓
calculate KPIDelta
    ↓
classify improvement / worsening
    ↓
generate management issue
```

---

## 14. Expected Output Files

### 14.1 Quantity Outputs

```text
rice_psi_summary.csv
rice_inventory_by_week.csv
rice_supply_by_week.csv
rice_demand_by_week.csv
rice_capacity_usage.csv
rice_capacity_violation.csv
```

### 14.2 Money Outputs

```text
rice_cost_summary.csv
rice_revenue_summary.csv
rice_profit_summary.csv
rice_inventory_value.csv
rice_cash_pressure.csv
```

### 14.3 KPI Outputs

```text
rice_kpi_summary.csv
rice_kpi_delta_vs_baseline.csv
rice_scenario_comparison.csv
```

### 14.4 Issue Outputs

```text
rice_management_issues.csv
rice_management_issues.json
```

---

## 15. Visualization Plan

### 15.1 PSI Chart

Show weekly:

```text
P
S
I
```

The expected Rice pattern:

```text
P spike during harvest weeks
I rises after harvest
S continues weekly
I gradually declines
```

### 15.2 Inventory and Storage Capacity Chart

Show:

```text
inventory level
storage capacity
storage utilization
```

This chart should make inventory burden visible.

### 15.3 Cost / Profit Chart

Show:

```text
revenue
purchase cost
storage cost
milling cost
transport cost
gross profit
profit margin
```

### 15.4 Scenario Comparison Chart

Compare:

```text
AS IS
TO BE
CAN BE
WILL BE
LET IT BE
```

using key KPIs:

```text
profit_margin
inventory_value
storage_cost
cash_conversion_pressure
producer_sustainability_score
inventory_soundness_score
```

### 15.5 Management Issue View

Show issue cards such as:

```text
Inventory overhang risk
Storage cost pressure
Profit margin decline
Demand decline risk
Premium strategy opportunity
```

---

## 16. Scenario Prioritization

### 16.1 Purpose

Scenario prioritization ranks candidate actions.

### 16.2 Suggested Criteria

```text
profit impact
inventory reduction
cash pressure improvement
feasibility
implementation cost
producer sustainability
customer fulfillment
policy compatibility
```

### 16.3 Simple Prioritization Matrix

| Scenario | Profit Impact | Inventory Impact | Feasibility | Strategic Fit | Priority |
|---|---:|---:|---:|---:|---:|
| CAN_BE_STORAGE | High | High | High | Medium | 1 |
| TO_BE_PREMIUM | High | Medium | Medium | High | 2 |
| WILL_BE_DEMAND_DECLINE | Negative | Negative | N/A | Risk | Watch |
| LET_IT_BE_POLICY | Neutral | Neutral | N/A | Constraint | Reference |

### 16.4 Interpretation

```text
CAN BE scenarios:
    should identify realistic operational actions

TO BE scenarios:
    should identify desirable strategic direction

WILL BE scenarios:
    should show risk if no action is taken

LET IT BE scenarios:
    should define constraints or areas not directly optimized
```

---

## 17. Management Issue Generation

### 17.1 Example Issue: Inventory Overhang

```text
Issue Type:
    INVENTORY_OVERHANG

Impact:
    ending inventory remains high after demand period
    storage cost increases
    cash conversion pressure worsens

Suggested Actions:
    demand smoothing
    direct sales channel
    storage cost reduction
    export or premium product strategy
```

### 17.2 Example Issue: Profit Margin Decline

```text
Issue Type:
    PROFIT_MARGIN_DECLINE

Impact:
    selling price decline or cost increase reduces margin

Suggested Actions:
    premium strategy
    cost reduction
    product mix change
    channel strategy
```

### 17.3 Example Issue: Storage Capacity Pressure

```text
Issue Type:
    STORAGE_CAPACITY_PRESSURE

Impact:
    harvest concentration creates high storage utilization

Suggested Actions:
    distributed storage
    earlier shipment
    improved demand smoothing
    temporary storage capacity
```

---

## 18. Minimum Smoke Scenario

### 18.1 Smoke Input

```text
product:
    PACKAGED_RICE_STANDARD

harvest supply:
    W40: 20 lots
    W41: 30 lots
    W42: 30 lots
    W43: 15 lots
    W44: 5 lots

weekly demand:
    household: 1.0 lot/week
    food service: 0.6 lot/week

storage capacity:
    100 lots

milling capacity:
    5 lots/week

transport capacity:
    5 lots/week
```

### 18.2 Expected Smoke Output

```text
harvest P spike:
    W40-W44

inventory buildup:
    after harvest

inventory drawdown:
    through weekly demand

capacity usage:
    milling and transport within capacity

money evaluation:
    revenue / cost / profit calculated
```

---

## 19. Relationship with Note Article

This simulation plan should directly support the follow-up note article.

Proposed article title:

```text
米のサプライチェーンをWOMでシミュレーションする
――パラメータ設定、価格感度分析、シナリオ比較の実例
```

The article should answer:

```text
1. What is the Rice Case model?
2. What data is prepared?
3. How is AS IS simulated?
4. How are parameters changed?
5. How is cost / price sensitivity evaluated?
6. How are scenarios compared?
7. What management issues are found?
8. Which actions should be prioritized?
```

---

## 20. Implementation Roadmap

### Phase 1: Design and Master Dataset

```text
AS-IS research
modeling design
master dataset design
simulation plan
```

### Phase 2: Adapter and Smoke Runner

```text
case dataset → current WOM input adapter
rice smoke runner
quantity PSI output
```

### Phase 3: Cost / Price Evaluation

```text
cost_price_master
revenue / cost / profit calculation
inventory value calculation
```

### Phase 4: KPI and Scenario Comparison

```text
KPI summary
KPIDelta vs AS IS
scenario ranking
```

### Phase 5: Note Article

```text
public explanation
charts and tables
findings
management implications
```

---

## 21. Summary

This simulation plan defines how to answer the Rice Case note article's next-step promise.

The key message is:

```text
The Japanese rice supply chain can be modeled as
an annual PSI synchronization problem.

The challenge is not only how much rice is produced,
but how harvest concentration, inventory, storage,
processing, demand, cost, and price interact over time.
```

The first implementation should be small.

But it should already show:

```text
AS IS baseline
parameter changes
cost / price sensitivity
scenario comparison
management issue candidates
```

The next step after this memo is to prepare a Codex request or implementation plan for:

```text
Rice Case smoke runner and adapter MVP
```
