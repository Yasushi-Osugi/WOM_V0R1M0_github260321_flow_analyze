# WOM Master Original Source Data Schema v0.1

> File: `docs/schema/wom_master_original_source_data_schema.md`  
> Status: Living Design Document v0.1  
> Owner: WOM Project / Yasushi Ohsugi × ChatGPT  
> Purpose: Real / virtual industry case information を、WOM master CSV filesへ変換可能な中間データ構造として定義する。  
> Depends on: `docs/schema/wom_current_master_files_map.md`  
> Next implementation target: `pysi/modeling/wom_master_adapter.py`

---

## 1. Purpose

This document defines **WOM Master Original Source Data**, abbreviated as **MOSD**.

MOSD is the source-side canonical data structure used to generate WOM master CSV files.

MOSD is not the same as WOM master CSV files.  
MOSD is an upstream modeling layer that captures business case information before it is transformed into current WOM master formats.

The purpose of MOSD is to support the following workflow:

```text
Industry case / user request / public information / hypothetical assumptions
  ↓
WOM Master Original Source Data
  ↓
MOSD → WOM Master CSV Adapter
  ↓
WOM master files
  ↓
WOM planning / costing / reporting / Management Cockpit
```

MOSD is designed for:

1. AI-assisted WOM modeling
2. Industry scenario generation
3. Master data auto-generation
4. Human review before WOM execution
5. Clear separation of facts, assumptions, templates, and placeholders
6. Future WOM Navigator Seed Prompt v0.4

---

## 2. Core Design Principles

### 2.1 MOSD is source data, not execution data

MOSD is not directly loaded by the current WOM planning engine.

MOSD is transformed into current WOM master files, such as:

```text
data/node_geo.csv
data/product_tree_inbound.csv
data/product_tree_outbound.csv
data/sku_P_month_data.csv
data/sku_S_month_data.csv
data/cost_masters/*.csv
pysi/master_data/*.csv
```

### 2.2 Every important value should carry source metadata

MOSD should distinguish:

```text
user_provided
public_reference
industry_template
navigator_assumption
system_default
placeholder_required
```

MOSD should also carry confidence:

```text
high
medium
low
placeholder
```

This is essential because WOM may be used for management scenario discussion.  
A user-provided capacity number and an AI-assumed capacity number must never be silently mixed.

### 2.3 node_name is the current WOM node key

MOSD must align with the current WOM rule:

```text
node_name is the canonical node key.
```

Future database implementations may introduce surrogate node IDs, but MOSD v0.1 should generate human-readable `node_name`.

### 2.4 market_id is not country

MOSD must distinguish:

```text
market_id = terminal market / sales channel / customer segment
country   = geographic attribute
```

Example:

```text
market_id = MKT_US_PREMIUM
country   = US
```

### 2.5 supply_point is a reserved common node_name

MOSD should include exactly one logical `supply_point` per product model unless an advanced multi-supply-point model is explicitly defined.

`supply_point` connects INBOUND and OUTBOUND trees.

### 2.6 MOM and DAD prefixes are reserved

MOSD adapter should generate WOM node_names consistent with reserved prefixes when roles are clear.

```text
role = MOM → node_name should generally start with MOM_
role = DAD → node_name should generally start with DAD_
```

This supports current WOM network layout behavior.

### 2.7 MOSD should support both real and hypothetical cases

MOSD may describe:

```text
real company case
public case study
industry template
hypothetical demonstration
education sample
simulation benchmark
```

Therefore, the schema must contain:

```text
case_type
source_type
confidence
assumption_notes
human_review_required
```

---

## 3. Top-Level MOSD Structure

Recommended file format:

```text
YAML or JSON
```

Recommended filename pattern:

```text
mosd_<industry>_<case_name>_v0_1.yaml
```

Example:

```text
samples/mosd/home_appliance_sample_v0_1.yaml
samples/mosd/pharma_cold_chain_sample_v0_1.yaml
```

Top-level structure:

```yaml
schema_version: wom_mosd_v0_1
model_id: home_appliance_sample_001
model_name: Home Appliance Sample Supply Chain
case_type: hypothetical_demo
industry: home_appliance
planning_horizon:
  start_year: 2028
  start_week: 1
  end_year: 2028
  end_week: 52
reporting_currency: USD
source_policy:
  default_source_type: navigator_assumption
  default_confidence: low
human_review_required: true

products: []
physical_nodes: []
product_plan_edges: []
quantity_profiles: []
markets: []
node_market_mapping: []
cost_assumptions: {}
currencies: {}
scenarios: []
metadata: {}
```

---

## 4. Top-Level Fields

| field | required | type | meaning |
|---|---:|---|---|
| `schema_version` | Yes | string | MOSD schema version. |
| `model_id` | Yes | string | Unique model identifier. |
| `model_name` | Yes | string | Human-readable model name. |
| `case_type` | Yes | enum | real_case / public_case / hypothetical_demo / education_sample / benchmark. |
| `industry` | Yes | string | Industry category. |
| `planning_horizon` | Yes | object | Planning period. |
| `reporting_currency` | Yes | string | Currency used for reporting. |
| `source_policy` | Yes | object | Default source and confidence rules. |
| `human_review_required` | Yes | boolean | Whether human review is required before business use. |
| `products` | Yes | list | Product definitions. |
| `physical_nodes` | Yes | list | Physical / logical node definitions. |
| `product_plan_edges` | Yes | list | Product-specific IN/OUT planning tree edges. |
| `quantity_profiles` | Yes | list | P/S quantity input profiles. |
| `markets` | Recommended | list | Market definitions. |
| `node_market_mapping` | Recommended | list | OUTBOUND leaf node to market_id mapping. |
| `cost_assumptions` | Recommended | object | Product, node, lane, price, SGA, asset, allocation assumptions. |
| `currencies` | Recommended | object | FX rate assumptions. |
| `scenarios` | Recommended | list | Scenario definitions. |
| `metadata` | Recommended | object | Author, date, notes, version, source list. |

---

## 5. Source Metadata Standard

MOSD should use the following metadata fields when possible.

```yaml
source_type: user_provided
source_ref: customer_workshop_2028_01
confidence: high
assumption_note: Provided by customer planning team.
human_review_required: false
```

### 5.1 source_type

Allowed values:

```text
user_provided
public_reference
industry_template
navigator_assumption
system_default
placeholder_required
derived_from_existing_wom_master
```

### 5.2 confidence

Allowed values:

```text
high
medium
low
placeholder
```

### 5.3 human_review_required

Recommended rule:

```text
human_review_required = true
```

when source_type is:

```text
navigator_assumption
placeholder_required
public_reference
industry_template
```

unless explicitly confirmed by the user.

---

## 6. planning_horizon

Example:

```yaml
planning_horizon:
  start_year: 2028
  start_week: 1
  end_year: 2028
  end_week: 52
  weeks_per_year: 52
  monthly_input_mode: true
```

Mapping target:

```text
quantity_profiles → sku_P_month_data.csv / sku_S_month_data.csv
valid_from_week / valid_to_week fields in cost_masters
```

---

## 7. products

### 7.1 Purpose

Defines products or product families to be modeled in WOM.

### 7.2 Schema

```yaml
products:
  - product_name: IPHONE_NM_2028_BASE
    product_family: IPHONE
    lot_size: 1
    unit_name: unit
    planning_unit: CPU
    lifecycle_stage: launch
    default_price_policy: BASE_PRICE
    default_cost_tag: BASE_COST
    active_flag: true
    source_type: user_provided
    confidence: high
```

### 7.3 Mapping targets

```text
product_tree_inbound.csv.Product_name
product_tree_outbound.csv.Product_name
sku_P_month_data.csv.product_name
sku_S_month_data.csv.product_name
data/cost_masters/product_cost_master.csv
pysi/master_data/node_product_money_master.csv
```

Future target:

```text
data/product_master.csv
```

---

## 8. physical_nodes

### 8.1 Purpose

Defines physical or logical supply chain nodes.

A node may represent:

```text
factory
warehouse
distribution center
retailer
consumer segment
supplier
market-facing node
office
supply_point
```

### 8.2 Schema

```yaml
physical_nodes:
  - node_name: supply_point
    node_character: SUPPLY_CHAIN_OFFICE
    display_name: Global Supply Chain Office
    role: SUPPLY_POINT
    bound: BOTH
    country: GLOBAL
    region: GLOBAL
    company: WOM
    lat: null
    lon: null
    can_produce: false
    can_purchase: false
    can_store: true
    can_ship: true
    can_sell: false
    active_flag: true
    source_type: system_default
    confidence: high

  - node_name: MOM_FINAL_ASSY_ASIA
    node_character: MOM
    display_name: Final Assembly Asia
    role: MOM
    bound: IN
    country: JP
    region: APAC
    company: SAMPLE_CO
    lat: 35.0
    lon: 139.0
    can_produce: true
    can_purchase: false
    can_store: true
    can_ship: true
    can_sell: false
    active_flag: true
    source_type: navigator_assumption
    confidence: low
```

### 8.3 Required rules

```text
node_name must be unique.
supply_point should exist once.
MOM_* and DAD_* prefixes are reserved.
PAD is not a standard node_character.
```

### 8.4 Mapping targets

```text
data/node_geo.csv
pysi/master_data/node_master.csv
data/cost_masters/node_cost_master.csv
```

---

## 9. product_plan_edges

### 9.1 Purpose

Defines product-specific INBOUND and OUTBOUND planning tree edges.

MOSD separates physical node definitions from product-specific plan tree structure.

### 9.2 Schema

```yaml
product_plan_edges:
  - product_name: IPHONE_NM_2028_BASE
    bound: IN
    parent_node: MOM_FINAL_ASSY_ASIA
    child_node: supply_point
    edge_type: INBOUND_SUPPLY
    transport_mode: truck
    leadtime_days: 7
    lot_size: 1
    process_capa: 100
    ss_days: 7
    long_vacation_weeks: []
    psi_graph_flag: true
    buffering_stock_flag: false
    source_type: navigator_assumption
    confidence: low

  - product_name: IPHONE_NM_2028_BASE
    bound: OUT
    parent_node: supply_point
    child_node: DAD_US
    edge_type: OUTBOUND_SUPPLY
    transport_mode: ocean
    leadtime_days: 21
    lot_size: 1
    process_capa: 100
    ss_days: 7
    source_type: navigator_assumption
    confidence: low
```

### 9.3 Mapping targets

```text
bound = IN  → data/product_tree_inbound.csv
bound = OUT → data/product_tree_outbound.csv
```

### 9.4 Validation rules

```text
parent_node exists in physical_nodes or is root.
child_node exists in physical_nodes.
product_name exists in products.
bound is IN or OUT.
leadtime_days >= 0.
lot_size > 0.
IN and OUT trees connect through supply_point.
```

---

## 10. quantity_profiles

### 10.1 Purpose

Defines P and S input quantities.

MOSD can store quantity profiles in long format.  
The adapter converts them to current WOM monthly wide format.

### 10.2 Schema

```yaml
quantity_profiles:
  - product_name: IPHONE_NM_2028_BASE
    node_name: MOM_FINAL_ASSY_ASIA
    bucket: P
    year: 2028
    month: 1
    quantity: 100
    quantity_type: capacity
    scenario_name: BAU
    source_type: user_provided
    confidence: high

  - product_name: IPHONE_NM_2028_BASE
    node_name: CS_US_PREMIUM
    bucket: S
    year: 2028
    month: 1
    quantity: 80
    quantity_type: demand
    scenario_name: BAU
    source_type: navigator_assumption
    confidence: low
```

### 10.3 Mapping targets

```text
bucket = P → data/sku_P_month_data.csv
bucket = S → data/sku_S_month_data.csv
```

### 10.4 Adapter transformation

MOSD long format:

```text
product_name, node_name, year, month, bucket, quantity
```

Current WOM wide format:

```text
product_name, node_name, year, m1, m2, ..., m12
```

### 10.5 Validation rules

```text
bucket is P or S.
quantity >= 0.
product_name exists in products.
node_name exists in physical_nodes.
month is 1..12.
scenario_name exists or defaults to BAU.
```

---

## 11. markets

### 11.1 Purpose

Defines management market units.

A market is not necessarily a country.  
A market may represent:

```text
country × region × channel × segment × price policy × service policy
```

### 11.2 Schema

```yaml
markets:
  - market_id: MKT_US_PREMIUM
    market_name: US Premium Market
    country: US
    region: NA
    channel: ONLINE
    segment: PREMIUM
    priority_class: A
    service_policy: HIGH_SERVICE
    price_policy: PREMIUM_PRICE
    currency: USD
    active_flag: true
    source_type: navigator_assumption
    confidence: low
```

### 11.3 Mapping target

```text
data/cost_masters/market_master.csv
```

### 11.4 Validation rules

```text
market_id is unique.
country is an attribute, not the key.
currency should be convertible to reporting_currency.
active_flag is true or false.
```

---

## 12. node_market_mapping

### 12.1 Purpose

Connects WOM OUTBOUND leaf nodes to management markets.

```text
WOM OUTBOUND leaf node
  ↓
node_market_mapping
  ↓
market_id
  ↓
market_master
```

### 12.2 Schema

```yaml
node_market_mapping:
  - node_name: CS_US_PREMIUM
    market_id: MKT_US_PREMIUM
    product_name: IPHONE_NM_2028_BASE
    allocation_ratio: 1.0
    priority_class: A
    service_policy: HIGH_SERVICE
    price_policy: PREMIUM_PRICE
    valid_from_week: 1
    valid_to_week: 52
    scenario_name: BAU
    active_flag: true
    source_type: navigator_assumption
    confidence: low
```

### 12.3 Mapping target

```text
data/cost_masters/cs_node_to_market_map.csv
```

### 12.4 Validation rules

```text
node_name exists in OUTBOUND product tree.
market_id exists in markets.
product_name exists in products.
allocation_ratio > 0.
For same scenario/product/node/week, allocation_ratio should generally sum to 1.0.
country is not duplicated here.
```

---

## 13. cost_assumptions

`cost_assumptions` groups all money-side assumptions.

Recommended structure:

```yaml
cost_assumptions:
  product_costs: []
  node_costs: []
  lane_costs: []
  sales_prices: []
  sga_marketing_tax: []
  fixed_assets: []
  allocation_rules: []
```

---

## 14. cost_assumptions.product_costs

### 14.1 Schema

```yaml
cost_assumptions:
  product_costs:
    - product_name: IPHONE_NM_2028_BASE
      product_family: IPHONE
      base_sales_price: 1000
      standard_material_cost: 350
      standard_production_cost: 120
      purchase_cost: 0
      inventory_unit_value: 470
      currency: USD
      scenario_name: BAU
      source_type: navigator_assumption
      confidence: low
```

### 14.2 Mapping target

```text
data/cost_masters/product_cost_master.csv
```

---

## 15. cost_assumptions.node_costs

### 15.1 Schema

```yaml
cost_assumptions:
  node_costs:
    - node_name: MOM_FINAL_ASSY_ASIA
      node_character: MOM
      direct_labor_cost_rate: 10
      machine_cost_rate: 20
      utility_cost_rate: 5
      inventory_holding_cost_rate: 0.01
      local_sga_fixed_cost: 100000
      local_sga_variable_cost_rate: 0.02
      depreciation_cost_per_period: 50000
      capacity_cost_basis: capacity_qty
      currency: USD
      scenario_name: BAU
      source_type: navigator_assumption
      confidence: low
```

### 15.2 Mapping targets

```text
data/cost_masters/node_cost_master.csv
pysi/master_data/node_product_money_master.csv when lightweight valuation is needed
```

---

## 16. cost_assumptions.lane_costs

### 16.1 Schema

```yaml
cost_assumptions:
  lane_costs:
    - from_node: supply_point
      to_node: DAD_US
      transport_mode: ocean
      freight_cost_per_unit: 20
      insurance_cost_per_unit: 2
      tariff_rate: 0.05
      customs_cost_per_unit: 3
      lead_time_days: 21
      special_risk_cost_rate: 0.02
      currency: USD
      scenario_name: BAU
      valid_from_week: 1
      valid_to_week: 52
      source_type: navigator_assumption
      confidence: low
```

### 16.2 Mapping target

```text
data/cost_masters/lane_cost_master.csv
```

---

## 17. cost_assumptions.sales_prices

### 17.1 Schema

```yaml
cost_assumptions:
  sales_prices:
    - product_name: IPHONE_NM_2028_BASE
      market_id: MKT_US_PREMIUM
      customer_segment: PREMIUM
      sales_price: 1200
      rebate_rate: 0.03
      promotion_cost_rate: 0.05
      gross_to_net_adjustment: 0.02
      expected_return_rate: 0.01
      currency: USD
      scenario_name: BAU
      valid_from_week: 1
      valid_to_week: 52
      source_type: navigator_assumption
      confidence: low
```

### 17.2 Mapping target

```text
data/cost_masters/sales_price_master.csv
```

---

## 18. cost_assumptions.sga_marketing_tax

### 18.1 Schema

```yaml
cost_assumptions:
  sga_marketing_tax:
    - scope_type: market
      scope_id: MKT_US_PREMIUM
      product_family: IPHONE
      sga_fixed_cost: 200000
      sga_variable_rate: 0.03
      marketing_fixed_cost: 50000
      marketing_variable_rate: 0.05
      tax_rate: 0.08
      currency: USD
      scenario_name: BAU
      valid_from_week: 1
      valid_to_week: 52
      source_type: navigator_assumption
      confidence: low
```

### 18.2 Mapping target

```text
data/cost_masters/sga_marketing_tax_master.csv
```

---

## 19. cost_assumptions.fixed_assets

### 19.1 Schema

```yaml
cost_assumptions:
  fixed_assets:
    - asset_id: LINE01
      node_name: MOM_FINAL_ASSY_ASIA
      asset_type: production_line
      investment_amount: 10000000
      depreciation_method: straight_line
      depreciation_periods: 260
      period_cost: 38461
      maintenance_cost_per_period: 5000
      currency: USD
      valid_from_week: 1
      valid_to_week: 260
      source_type: navigator_assumption
      confidence: low
```

### 19.2 Mapping target

```text
data/cost_masters/fixed_asset_cost_master.csv
```

---

## 20. cost_assumptions.allocation_rules

### 20.1 Schema

```yaml
cost_assumptions:
  allocation_rules:
    - rule_id: RULE_GLOBAL_SGA
      cost_pool: GLOBAL_SGA
      source_scope: company
      source_scope_id: SAMPLE_CO
      target_scope: market
      target_scope_id: ALL
      allocation_basis: revenue_share
      weight: 1.0
      valid_from_week: 1
      valid_to_week: 52
      scenario_name: BAU
      source_type: navigator_assumption
      confidence: low
```

### 20.2 Mapping target

```text
data/cost_masters/allocation_rule_master.csv
```

### 20.3 Rules

```text
target_scope_id must not be blank.
Use target_scope_id = ALL for all relevant targets.
```

---

## 21. currencies

### 21.1 Purpose

Defines reporting currency and FX assumptions.

### 21.2 Schema

```yaml
currencies:
  reporting_currency: USD
  fx_rates:
    - scenario_name: BAU
      from_currency: JPY
      to_currency: USD
      fx_rate: 0.0067
      rate_type: planning_rate
      valid_from_week: 1
      valid_to_week: 52
      source_type: user_provided
      confidence: medium
      remarks: annual planning rate

    - scenario_name: BAU
      from_currency: USD
      to_currency: JPY
      fx_rate: 150.0
      rate_type: planning_rate
      valid_from_week: 1
      valid_to_week: 52
      source_type: user_provided
      confidence: medium
      remarks: annual planning rate
```

### 21.3 Mapping target

```text
data/cost_masters/fx_rate_master.csv
```

### 21.4 Validation rules

```text
from_currency != to_currency.
fx_rate > 0.
valid_from_week <= valid_to_week.
Do not assume inverse FX rates unless explicitly allowed.
```

---

## 22. scenarios

### 22.1 Purpose

Defines future scenarios that may change demand, supply, cost, price, lead time, allocation, or FX assumptions.

### 22.2 Schema

```yaml
scenarios:
  - scenario_name: BAU
    scenario_type: baseline
    start_week: 1
    end_week: 52
    description: Business as usual.
    active_flag: true

  - scenario_name: PORT_STOP
    scenario_type: logistics_disruption
    start_week: 10
    end_week: 14
    description: Main port capacity is stopped and alternative route is used.
    affected_nodes:
      - DAD_US
    affected_edges:
      - from_node: supply_point
        to_node: DAD_US
    changed_assumptions:
      - target: lane_costs
        field: freight_cost_per_unit
        baseline_value: 20
        scenario_value: 60
      - target: lane_costs
        field: lead_time_days
        baseline_value: 21
        scenario_value: 35
```

### 22.3 Mapping targets

```text
scenario_name fields across cost_masters
future scenario_master.csv
future scenario override tables
```

---

## 23. metadata

### 23.1 Schema

```yaml
metadata:
  created_by: WOM Navigator
  created_date: 2026-04-30
  version: v0.1
  notes:
    - Initial MOSD sample.
  source_documents:
    - name: customer workshop memo
      source_type: user_provided
      confidence: high
    - name: public industry report
      source_type: public_reference
      confidence: medium
```

---

## 24. MOSD to WOM Master CSV Mapping Summary

| MOSD section | WOM output target |
|---|---|
| `products` | product tree product fields, future product_master, product_cost_master |
| `physical_nodes` | `data/node_geo.csv`, `pysi/master_data/node_master.csv` |
| `product_plan_edges[bound=IN]` | `data/product_tree_inbound.csv` |
| `product_plan_edges[bound=OUT]` | `data/product_tree_outbound.csv` |
| `quantity_profiles[bucket=P]` | `data/sku_P_month_data.csv` |
| `quantity_profiles[bucket=S]` | `data/sku_S_month_data.csv` |
| `markets` | `data/cost_masters/market_master.csv` |
| `node_market_mapping` | `data/cost_masters/cs_node_to_market_map.csv` |
| `cost_assumptions.product_costs` | `data/cost_masters/product_cost_master.csv` |
| `cost_assumptions.node_costs` | `data/cost_masters/node_cost_master.csv` |
| `cost_assumptions.lane_costs` | `data/cost_masters/lane_cost_master.csv` |
| `cost_assumptions.sales_prices` | `data/cost_masters/sales_price_master.csv` |
| `cost_assumptions.sga_marketing_tax` | `data/cost_masters/sga_marketing_tax_master.csv` |
| `cost_assumptions.fixed_assets` | `data/cost_masters/fixed_asset_cost_master.csv` |
| `cost_assumptions.allocation_rules` | `data/cost_masters/allocation_rule_master.csv` |
| `currencies.fx_rates` | `data/cost_masters/fx_rate_master.csv` |

---

## 25. Required Adapter Behavior

The MOSD adapter should perform these steps:

```text
1. Load MOSD YAML / JSON.
2. Validate top-level schema.
3. Normalize node_name and market_id.
4. Generate physical master outputs.
5. Generate product-specific plan tree outputs.
6. Generate P/S monthly wide format outputs.
7. Generate market bridge outputs.
8. Generate extended costing master outputs.
9. Generate semantic overlay outputs where needed.
10. Run validator.
11. Write WOM-ready master folder.
12. Produce adapter report.
```

Recommended output folder:

```text
outputs/generated_master_data/<model_id>/
```

Recommended output report:

```text
outputs/generated_master_data/<model_id>/adapter_report.md
```

---

## 26. Required Validator Behavior

The MOSD validator should check:

```text
schema_version is supported
model_id exists
planning_horizon is valid
products are unique
physical_nodes.node_name are unique
supply_point exists once
MOM / DAD prefix rules are respected
product_plan_edges reference existing nodes
INBOUND and OUTBOUND connect through supply_point
quantity_profiles reference valid products and nodes
market_id is unique
node_market_mapping references valid OUTBOUND nodes and markets
allocation target_scope_id is not blank
target_scope_id = ALL is valid
currency conversion path exists
all navigator_assumption and placeholder_required fields are marked for review
```

---

## 27. Human Review Gate

Before MOSD-generated WOM master files are used for business decisions, the following must be reviewed:

```text
1. Demand assumptions
2. Production / supply capacity assumptions
3. Lead time assumptions
4. Cost and price assumptions
5. FX assumptions
6. Allocation rules
7. Market mapping
8. Scenario trigger and duration
9. Any value with source_type = navigator_assumption
10. Any value with confidence = low or placeholder
```

The adapter should produce a list:

```text
Human Review Required Items
```

---

## 28. Minimal MOSD Example

```yaml
schema_version: wom_mosd_v0_1
model_id: home_appliance_sample_001
model_name: Home Appliance Sample
case_type: hypothetical_demo
industry: home_appliance
planning_horizon:
  start_year: 2028
  start_week: 1
  end_year: 2028
  end_week: 52
  weeks_per_year: 52
reporting_currency: USD
source_policy:
  default_source_type: navigator_assumption
  default_confidence: low
human_review_required: true

products:
  - product_name: SMART_WASHER_2028_BASE
    product_family: WASHER
    lot_size: 1
    unit_name: unit
    planning_unit: CPU
    lifecycle_stage: launch
    active_flag: true
    source_type: navigator_assumption
    confidence: low

physical_nodes:
  - node_name: supply_point
    node_character: SUPPLY_CHAIN_OFFICE
    display_name: Global Supply Chain Office
    role: SUPPLY_POINT
    bound: BOTH
    country: GLOBAL
    region: GLOBAL
    company: SAMPLE_CO
    active_flag: true
    source_type: system_default
    confidence: high

  - node_name: MOM_FINAL_ASSY_ASIA
    node_character: MOM
    display_name: Final Assembly Asia
    role: MOM
    bound: IN
    country: JP
    region: APAC
    company: SAMPLE_CO
    lat: 35.0
    lon: 139.0
    can_produce: true
    active_flag: true
    source_type: navigator_assumption
    confidence: low

  - node_name: DAD_US
    node_character: DAD
    display_name: US Distribution
    role: DAD
    bound: OUT
    country: US
    region: NA
    company: SAMPLE_CO
    lat: 40.0
    lon: -75.0
    can_store: true
    can_ship: true
    active_flag: true
    source_type: navigator_assumption
    confidence: low

product_plan_edges:
  - product_name: SMART_WASHER_2028_BASE
    bound: IN
    parent_node: MOM_FINAL_ASSY_ASIA
    child_node: supply_point
    edge_type: INBOUND_SUPPLY
    transport_mode: truck
    leadtime_days: 7
    lot_size: 1
    process_capa: 100
    ss_days: 7
    source_type: navigator_assumption
    confidence: low

  - product_name: SMART_WASHER_2028_BASE
    bound: OUT
    parent_node: supply_point
    child_node: DAD_US
    edge_type: OUTBOUND_SUPPLY
    transport_mode: ocean
    leadtime_days: 21
    lot_size: 1
    process_capa: 100
    ss_days: 7
    source_type: navigator_assumption
    confidence: low
```

---

## 29. Open Issues

### 29.1 product_master.csv

Current WOM does not yet have a single product master正本.  
MOSD `products` may become the source of future `data/product_master.csv`.

### 29.2 node_id

MOSD v0.1 uses `node_name`.  
Future DB versions may introduce `node_id`.

### 29.3 weekly vs monthly quantity input

MOSD v0.1 allows long-format monthly input.  
Future versions may support weekly direct input.

### 29.4 industry templates

Future MOSD templates should be added for:

```text
home appliance
pharmaceutical cold chain
automotive
food
electronics
semiconductor
agriculture
```

### 29.5 source reference enrichment

Future MOSD may support detailed source references:

```text
document_id
URL
interview_id
page_number
confidence_reason
```

---

## 30. Next Implementation Step

Recommended next implementation step:

```text
pysi/modeling/
  mosd_schema.py
  wom_master_adapter.py
  wom_master_validator.py
```

Recommended next documentation step:

```text
docs/schema/wom_mosd_to_wom_master_adapter_design.md
```

Recommended next Navigator step:

```text
docs/ai_navigator/wom_e2e_supply_chain_navigator_seed_prompt_v0_4.md
```
