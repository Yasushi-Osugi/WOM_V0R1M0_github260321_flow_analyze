# WOM Case Modeling Base Dataset Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-15  
**Status:** Design memo  
**Target path:** `docs/design/wom_case_modeling_base_dataset.md`

---

## 1. Purpose

This memo defines the **WOM Case Modeling Base Dataset**.

The purpose is to create a common modeling dataset structure that can be used for multiple WOM case studies, such as:

- Japanese Rice Supply Chain Case
- COVID Vaccine Supply Chain Case
- Automotive parts supply chain
- Semiconductor supply chain
- Food / agriculture supply chain
- Pharmaceutical / cold-chain supply chain

The key design principle is:

```text
Do not force real-world case modeling to start from the current WOM CSV file format.

Instead:
    define an ideal case modeling dataset first
    then connect it to the current WOM Planning Engine through adapters
```

The intended modeling flow is:

```text
Real-world Supply Chain Case
    ↓
WOM Case Modeling Base Dataset
    ↓
Adapter
    ↓
Current WOM CSV Master Files / Internal Model
    ↓
WOM Planning Engine
    ↓
PSI / Capacity / Cost / KPI outputs
    ↓
Visualization
    ↓
Management Issue
```

This design turns WOM from a Python tool into a reusable **supply chain modeling methodology**.

---

## 2. Background

WOM development has accumulated several important functional components:

```text
PSI planning engine
Lot-based planning
capacity-aware PUSH
capacity master I/O
bottleneck allocation policy
cost / price simulation foundations
KPI registry
management issue analyzer
case study design
```

However, case studies should not be forced to directly match the current WOM CSV structure.

The current WOM CSV files are implementation-oriented.

A case study needs a more natural modeling layer that represents the real-world supply chain first.

Therefore, this memo defines a base dataset layer:

```text
WOM Case Modeling Base Dataset
```

This layer should be:

- understandable by business users
- compatible with AI-assisted narrative modeling
- convertible to current WOM inputs
- extensible to cost / KPI / scenario evaluation
- reusable across case studies

---

## 3. Design Principles

### 3.1 Real-world first, engine second

The base dataset should express real-world supply chain structure first.

Then an adapter should convert it into current WOM engine inputs.

```text
case model:
    business-friendly, scenario-oriented

adapter:
    implementation-oriented

WOM engine:
    executable planning logic
```

### 3.2 Lot is the primary planning object

WOM should preserve lot-level identity wherever possible.

A lot is not just quantity.

A lot may carry:

```text
product
origin
quality
grade
expiry / shelf life
current node
target node
scenario status
cost / price attributes
```

This is especially important for:

- vaccine lots
- rice harvest lots
- premium products
- constrained supply lots
- priority lots

### 3.3 Weekly bucket is the time foundation

The base dataset should use weekly time buckets.

```text
week = YYYY-Www
```

or a compatible internal WOM week key.

### 3.4 Quantity and money should be connected

The dataset should support both:

```text
quantity planning:
    P / S / I lot flow

money planning:
    revenue / cost / profit / inventory value / cash impact
```

### 3.5 KPI and issue generation should be prepared from the beginning

The base dataset should include scenario and KPI policy inputs so that E2E Evaluation and Management Issue Generation can be built naturally.

---

## 4. Dataset Layers

The WOM Case Modeling Base Dataset is composed of the following layers.

```text
1. scenario_master
2. node_master
3. lane_master
4. product_master
5. lot_master
6. supply_plan
7. demand_plan
8. capacity_master
9. cost_price_master
10. kpi_policy_master
11. scenario_parameter_master
12. adapter_mapping_master
```

The first practical version does not need all layers to be complete.

However, the structure should be stable enough to support future expansion.

---

## 5. scenario_master

### 5.1 Purpose

Defines planning scenarios.

Examples:

```text
AS_IS
TO_BE
CAN_BE
WILL_BE
LET_IT_BE
COVID_BASE
COVID_TRANSPORT_BOTTLENECK
RICE_AS_IS
RICE_PRICE_SENSITIVITY
```

### 5.2 Schema

```csv
scenario_id,scenario_name,baseline_scenario_id,description,start_week,end_week,scenario_type,is_baseline,comment
```

### 5.3 Column Definition

| Column | Meaning |
|---|---|
| scenario_id | unique scenario identifier |
| scenario_name | human-readable name |
| baseline_scenario_id | scenario used for comparison |
| description | scenario description |
| start_week | planning start week |
| end_week | planning end week |
| scenario_type | AS_IS / TO_BE / CAN_BE / WILL_BE / LET_IT_BE / OTHER |
| is_baseline | true / false |
| comment | free text |

### 5.4 Example

```csv
scenario_id,scenario_name,baseline_scenario_id,description,start_week,end_week,scenario_type,is_baseline,comment
RICE_AS_IS,Rice AS-IS,,Current Japanese rice supply chain,2026-W01,2026-W52,AS_IS,true,baseline scenario
RICE_CAN_BE_STORAGE,Rice CAN-BE Storage Improvement,RICE_AS_IS,Reduce storage cost and improve inventory control,2026-W01,2026-W52,CAN_BE,false,scenario comparison
COVID_BASE,COVID Vaccine Base,,Base vaccine distribution scenario,2026-W40,2026-W44,AS_IS,true,smoke scenario
```

---

## 6. node_master

### 6.1 Purpose

Defines supply chain nodes.

Nodes should represent real-world entities at the modeling granularity appropriate for the case.

### 6.2 Schema

```csv
scenario_id,node_id,node_name,node_type,tree_side,region,country,role,storage_type,is_buffer,is_bottleneck_candidate,comment
```

### 6.3 Column Definition

| Column | Meaning |
|---|---|
| scenario_id | scenario identifier |
| node_id | unique node ID |
| node_name | display name |
| node_type | producer / collection / dc / clinic / mill / retail / demand etc. |
| tree_side | INBOUND / OUTBOUND / E2E |
| region | region or prefecture |
| country | country |
| role | business role |
| storage_type | normal / cold / frozen / warehouse / none |
| is_buffer | true if node is designed as inventory buffer |
| is_bottleneck_candidate | true if node can be capacity constraint |
| comment | free text |

### 6.4 Example: Rice

```csv
scenario_id,node_id,node_name,node_type,tree_side,region,country,role,storage_type,is_buffer,is_bottleneck_candidate,comment
RICE_AS_IS,PRODUCER_NIIGATA,Producer Niigata,producer,INBOUND,NIIGATA,JP,rice production,none,false,true,aggregate producer node
RICE_AS_IS,COLLECTION_NIIGATA,Collection Niigata,collection,INBOUND,NIIGATA,JP,collection and adjustment,warehouse,true,true,collection and drying node
RICE_AS_IS,BROWN_STORAGE_EAST,Brown Rice Storage East,storage,E2E,EAST,JP,brown rice storage,warehouse,true,true,seasonal inventory node
RICE_AS_IS,MILL_EAST,Milling East,milling,E2E,EAST,JP,milling process,none,false,true,milling capacity node
RICE_AS_IS,RETAIL_TOKYO,Retail Tokyo,retail,OUTBOUND,TOKYO,JP,retail sales,store,true,false,market-side buffer
```

### 6.5 Example: Vaccine

```csv
scenario_id,node_id,node_name,node_type,tree_side,region,country,role,storage_type,is_buffer,is_bottleneck_candidate,comment
COVID_BASE,CENTRAL_DC,Central DC,central_dc,OUTBOUND,NATIONAL,JP,national vaccine stock,cold,true,true,central supply node
COVID_BASE,PREF_DC_TOKYO,Pref DC Tokyo,regional_dc,OUTBOUND,TOKYO,JP,regional distribution,cold,true,true,regional stock node
COVID_BASE,CLINIC_TOKYO_01,Clinic Tokyo 01,clinic,OUTBOUND,TOKYO,JP,vaccination site,cold,true,true,clinic vaccination node
```

---

## 7. lane_master

### 7.1 Purpose

Defines flows between nodes.

Lanes may represent physical transportation, transfer, or logical supply relationships.

### 7.2 Schema

```csv
scenario_id,lane_id,from_node_id,to_node_id,lane_type,tree_side,transport_mode,leadtime_weeks,cold_chain_required,is_alternative,priority,comment
```

### 7.3 Column Definition

| Column | Meaning |
|---|---|
| lane_id | unique lane identifier |
| from_node_id | source node |
| to_node_id | destination node |
| lane_type | transport / process / transfer / demand |
| tree_side | INBOUND / OUTBOUND / E2E |
| transport_mode | truck / rail / sea / air / internal etc. |
| leadtime_weeks | leadtime in weeks |
| cold_chain_required | true / false |
| is_alternative | true if alternative route |
| priority | route priority |
| comment | free text |

### 7.4 Example: Rice

```csv
scenario_id,lane_id,from_node_id,to_node_id,lane_type,tree_side,transport_mode,leadtime_weeks,cold_chain_required,is_alternative,priority,comment
RICE_AS_IS,LANE_PRODUCER_TO_COLLECTION,PRODUCER_NIIGATA,COLLECTION_NIIGATA,transport,INBOUND,truck,1,false,false,1,producer to collection
RICE_AS_IS,LANE_STORAGE_TO_MILL,BROWN_STORAGE_EAST,MILL_EAST,transfer,E2E,truck,1,false,false,1,storage to milling
RICE_AS_IS,LANE_MILL_TO_RETAIL,MILL_EAST,RETAIL_TOKYO,transport,OUTBOUND,truck,1,false,false,1,milled rice to retail
```

### 7.5 Example: Vaccine

```csv
scenario_id,lane_id,from_node_id,to_node_id,lane_type,tree_side,transport_mode,leadtime_weeks,cold_chain_required,is_alternative,priority,comment
COVID_BASE,LANE_CENTRAL_TO_TOKYO,CENTRAL_DC,PREF_DC_TOKYO,transport,OUTBOUND,cold_truck,1,true,false,1,central to Tokyo
COVID_BASE,LANE_TOKYO_TO_CLINIC,PREF_DC_TOKYO,CLINIC_TOKYO_01,transport,OUTBOUND,cold_truck,1,true,false,1,regional to clinic
```

---

## 8. product_master

### 8.1 Purpose

Defines product and product family.

### 8.2 Schema

```csv
scenario_id,product_id,product_name,product_family,unit,lot_size,grade,brand_class,temperature_class,shelf_life_weeks,comment
```

### 8.3 Example: Rice

```csv
scenario_id,product_id,product_name,product_family,unit,lot_size,grade,brand_class,temperature_class,shelf_life_weeks,comment
RICE_AS_IS,BROWN_RICE_STANDARD,Brown Rice Standard,rice,kg,1000,standard,domestic_standard,ambient,52,brown rice lot
RICE_AS_IS,MILLED_RICE_PREMIUM,Milled Rice Premium,rice,kg,1000,premium,premium_brand,ambient,26,premium milled rice
```

### 8.4 Example: Vaccine

```csv
scenario_id,product_id,product_name,product_family,unit,lot_size,grade,brand_class,temperature_class,shelf_life_weeks,comment
COVID_BASE,COVID_VACCINE_PFIZER,COVID Vaccine Pfizer,vaccine,dose_lot,100,standard,pfizer,cold,8,vaccine lot
```

---

## 9. lot_master

### 9.1 Purpose

Defines lot-level planning objects.

Lot identity is central to WOM.

### 9.2 Schema

```csv
scenario_id,lot_id,product_id,quantity,current_node_id,target_node_id,target_region,available_week,due_week,expiry_week,quality_status,priority,comment
```

### 9.3 Column Definition

| Column | Meaning |
|---|---|
| lot_id | unique lot identifier |
| product_id | product identifier |
| quantity | quantity in product unit |
| current_node_id | current node |
| target_node_id | target node if known |
| target_region | target market / region |
| available_week | first available week |
| due_week | required demand / delivery week |
| expiry_week | expiry or quality limit week |
| quality_status | usable / expired / quarantine / damaged |
| priority | allocation priority |
| comment | free text |

### 9.4 Example: Rice

```csv
scenario_id,lot_id,product_id,quantity,current_node_id,target_node_id,target_region,available_week,due_week,expiry_week,quality_status,priority,comment
RICE_AS_IS,RICE-JP-2026W40-000001,BROWN_RICE_STANDARD,1000,COLLECTION_NIIGATA,BROWN_STORAGE_EAST,EAST,2026-W40,2026-W44,2027-W40,usable,100,harvest lot
```

### 9.5 Example: Vaccine

```csv
scenario_id,lot_id,product_id,quantity,current_node_id,target_node_id,target_region,available_week,due_week,expiry_week,quality_status,priority,comment
COVID_BASE,VAC-PFZ-2026W40-000001,COVID_VACCINE_PFIZER,100,CENTRAL_DC,CLINIC_TOKYO_01,TOKYO,2026-W40,2026-W40,2026-W48,usable,100,vaccine lot
```

---

## 10. supply_plan

### 10.1 Purpose

Defines external or planned supply.

This is especially useful when supply is given from outside the modeled network.

### 10.2 Schema

```csv
scenario_id,node_id,product_id,week,supply_qty,supply_type,source_type,comment
```

### 10.3 Example: Rice

```csv
scenario_id,node_id,product_id,week,supply_qty,supply_type,source_type,comment
RICE_AS_IS,PRODUCER_NIIGATA,BROWN_RICE_STANDARD,2026-W40,50000,harvest,internal,harvest peak
```

### 10.4 Example: Vaccine

```csv
scenario_id,node_id,product_id,week,supply_qty,supply_type,source_type,comment
COVID_BASE,CENTRAL_DC,COVID_VACCINE_PFIZER,2026-W40,300,external_supply,manufacturer_assumption,weekly vaccine supply into Japan
```

---

## 11. demand_plan

### 11.1 Purpose

Defines demand by market / region / node / week.

### 11.2 Schema

```csv
scenario_id,demand_node_id,region,product_id,week,demand_qty,demand_type,priority,comment
```

### 11.3 Example: Rice

```csv
scenario_id,demand_node_id,region,product_id,week,demand_qty,demand_type,priority,comment
RICE_AS_IS,DEMAND_HOUSEHOLD_TOKYO,TOKYO,PACKAGED_RICE_STANDARD,2026-W01,1000,household,100,weekly household demand
```

### 11.4 Example: Vaccine

```csv
scenario_id,demand_node_id,region,product_id,week,demand_qty,demand_type,priority,comment
COVID_BASE,DEMAND_TOKYO,TOKYO,COVID_VACCINE_PFIZER,2026-W40,150,vaccination,100,Tokyo weekly vaccination demand
```

---

## 12. capacity_master

### 12.1 Purpose

Defines capacity constraints.

This layer should cover both node and lane capacity.

### 12.2 Schema

```csv
scenario_id,capacity_owner_type,capacity_owner_id,product_id,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
```

### 12.3 Column Definition

| Column | Meaning |
|---|---|
| capacity_owner_type | node / lane / flow |
| capacity_owner_id | node_id or lane_id |
| capacity_type | P / S / I / transport / storage / process / vaccination |
| capacity_qty | capacity quantity |
| cap_mode | hard / soft |
| unit | LOT / kg / dose / etc. |
| priority | rule priority |
| calendar_id | calendar reference |
| comment | free text |

### 12.4 Adapter note

Current v0r2 capacity master uses:

```csv
scenario_id,tree_side,node_name,product_name,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
```

The adapter should map:

```text
capacity_owner_id → node_name
product_id → product_name
capacity_type → P / S / I when required
lane capacity → pseudo node_name or future flow capacity support
```

### 12.5 Example: Rice

```csv
scenario_id,capacity_owner_type,capacity_owner_id,product_id,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
RICE_AS_IS,node,BROWN_STORAGE_EAST,BROWN_RICE_STANDARD,2026-W40,I,100000,hard,kg,100,STD_CAL,brown rice storage capacity
RICE_AS_IS,node,MILL_EAST,BROWN_RICE_STANDARD,2026-W40,P,5000,hard,kg,100,STD_CAL,milling capacity
```

### 12.6 Example: Vaccine

```csv
scenario_id,capacity_owner_type,capacity_owner_id,product_id,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
COVID_BASE,lane,LANE_CENTRAL_TO_TOKYO,COVID_VACCINE_PFIZER,2026-W40,S,100,hard,LOT,100,COLD_CAL,transport capacity
COVID_BASE,node,CLINIC_TOKYO_01,COVID_VACCINE_PFIZER,2026-W40,S,90,hard,LOT,100,COLD_CAL,vaccination capacity
```

---

## 13. cost_price_master

### 13.1 Purpose

Defines cost and price assumptions.

### 13.2 Schema

```csv
scenario_id,owner_type,owner_id,product_id,week,cost_price_type,unit_value,unit,currency,comment
```

### 13.3 Cost / price types

Examples:

```text
purchase_price
selling_price
storage_cost_per_lot_week
transport_cost_per_lot
milling_cost_per_lot
packaging_cost_per_lot
waste_cost_per_lot
vaccination_handling_cost_per_lot
```

### 13.4 Example: Rice

```csv
scenario_id,owner_type,owner_id,product_id,week,cost_price_type,unit_value,unit,currency,comment
RICE_AS_IS,node,BROWN_STORAGE_EAST,BROWN_RICE_STANDARD,2026-W40,storage_cost_per_lot_week,50,kg,JPY,storage cost assumption
RICE_AS_IS,node,RETAIL_TOKYO,PACKAGED_RICE_STANDARD,2026-W40,selling_price,500,kg,JPY,retail selling price
```

### 13.5 Example: Vaccine

```csv
scenario_id,owner_type,owner_id,product_id,week,cost_price_type,unit_value,unit,currency,comment
COVID_BASE,lane,LANE_CENTRAL_TO_TOKYO,COVID_VACCINE_PFIZER,2026-W40,transport_cost_per_lot,1000,LOT,JPY,cold chain transport cost
```

---

## 14. kpi_policy_master

### 14.1 Purpose

Defines KPI evaluation policy and management intention.

### 14.2 Schema

```csv
scenario_id,kpi_id,weight,warning_threshold,critical_threshold,direction,comment
```

### 14.3 Column Definition

| Column | Meaning |
|---|---|
| kpi_id | KPI identifier |
| weight | scenario-specific importance |
| warning_threshold | warning threshold |
| critical_threshold | critical threshold |
| direction | higher_is_better / lower_is_better |
| comment | free text |

### 14.4 Example

```csv
scenario_id,kpi_id,weight,warning_threshold,critical_threshold,direction,comment
RICE_AS_IS,total_sc.inventory_value,0.2,10000000,20000000,lower_is_better,inventory burden
RICE_AS_IS,total_sc.profit_margin,0.3,0.05,0.02,higher_is_better,profitability
COVID_BASE,total_sc.fill_rate,0.4,0.9,0.8,higher_is_better,vaccination fulfillment
```

---

## 15. scenario_parameter_master

### 15.1 Purpose

Defines scenario-specific parameter changes.

### 15.2 Schema

```csv
scenario_id,parameter_id,target_type,target_id,product_id,week,value,unit,comment
```

### 15.3 Example: Rice

```csv
scenario_id,parameter_id,target_type,target_id,product_id,week,value,unit,comment
RICE_CAN_BE_STORAGE,storage_cost_reduction,node,BROWN_STORAGE_EAST,BROWN_RICE_STANDARD,2026-W40,-0.15,ratio,15 percent storage cost reduction
RICE_TO_BE_PREMIUM,premium_price_increase,node,RETAIL_TOKYO,PACKAGED_RICE_PREMIUM,2026-W01,0.10,ratio,10 percent premium price uplift
```

### 15.4 Example: Vaccine

```csv
scenario_id,parameter_id,target_type,target_id,product_id,week,value,unit,comment
COVID_TRANSPORT_UP,transport_capacity_increase,lane,LANE_CENTRAL_TO_TOKYO,COVID_VACCINE_PFIZER,2026-W40,20,LOT,temporary additional transport capacity
```

---

## 16. adapter_mapping_master

### 16.1 Purpose

Defines how the ideal case dataset maps to current WOM input structures.

### 16.2 Schema

```csv
case_dataset,case_field,wom_target_file,wom_target_field,transform_rule,comment
```

### 16.3 Example

```csv
case_dataset,case_field,wom_target_file,wom_target_field,transform_rule,comment
node_master,node_id,node_master_sample.csv,node_name,copy,node ID maps to WOM node name
lane_master,from_node_id,node_relation.csv,parent_node,copy,source node
lane_master,to_node_id,node_relation.csv,child_node,copy,destination node
capacity_master,capacity_owner_id,capacity_master_sample.csv,node_name,pseudo_lane_if_owner_type_lane,lane capacity as pseudo node for current v0r2
product_master,product_id,product_master.csv,product_name,copy,product mapping
```

---

## 17. Metadata and Assumption Logging

Each case should maintain explicit assumption metadata.

Suggested file:

```text
case_assumption_log.csv
```

Schema:

```csv
scenario_id,assumption_id,category,description,value,source,confidence,comment
```

Example:

```csv
scenario_id,assumption_id,category,description,value,source,confidence,comment
RICE_AS_IS,ASSUMP_RICE_WEEKLY_DEMAND,DEMAND,Weekly demand is evenly distributed across the year,1/52 of annual demand,model assumption,medium,replace with statistical demand profile later
COVID_BASE,ASSUMP_COLD_CHAIN_SIMPLIFY,CAPACITY,Cold chain capacity treated as transport capacity,true,model assumption,medium,Phase 1 simplification
```

---

## 18. Relationship with WOM Planning Engine

The base dataset should not directly depend on the internal engine format.

The relationship should be:

```text
WOM Case Modeling Base Dataset
    ↓
case-specific adapter
    ↓
current WOM CSV / internal model
    ↓
WOM Planning Engine
```

This keeps case modeling stable even if the internal engine evolves.

---

## 19. Initial Implementation Strategy

### 19.1 Step 1: Define schemas

Create design documents first.

```text
wom_case_modeling_base_dataset.md
case_japanese_rice_master_dataset.md
case_covid_vaccine_master_dataset.md
```

### 19.2 Step 2: Create sample CSVs

For Rice Case:

```text
rice_scenario_master.csv
rice_node_master.csv
rice_lane_master.csv
rice_product_master.csv
rice_supply_plan.csv
rice_demand_plan.csv
rice_capacity_master.csv
rice_cost_price_master.csv
rice_kpi_policy_master.csv
```

### 19.3 Step 3: Build adapter

Adapter should transform case dataset into current WOM engine input.

### 19.4 Step 4: Validate with smoke runner

Start with small case.

```text
single product
few nodes
few weeks
known expected output
```

### 19.5 Step 5: Add visualization and KPI

Generate:

```text
PSI summary
capacity summary
cost summary
KPI summary
management issue candidates
```

---

## 20. Summary

The WOM Case Modeling Base Dataset is the standard interface between real-world supply chain cases and the WOM Planning Engine.

The core concept is:

```text
real-world case
    ↓
business-friendly case dataset
    ↓
adapter
    ↓
WOM engine
    ↓
evaluation / visualization / issue generation
```

Most important principles:

1. **Do not start case modeling from current internal WOM CSV constraints.**
2. **Start from an ideal case modeling dataset that represents the real-world supply chain.**
3. **Use adapters to connect to the current WOM Planning Engine.**
4. **Preserve lot identity wherever possible.**
5. **Support both quantity and money evaluation.**
6. **Prepare KPI and management issue generation from the beginning.**
7. **Keep assumptions explicit.**
8. **Make the dataset reusable across Rice, Vaccine, and future cases.**
