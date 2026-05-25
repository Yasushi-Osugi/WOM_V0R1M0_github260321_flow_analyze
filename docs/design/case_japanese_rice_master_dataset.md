# Japanese Rice Case Master Dataset Design Memo

**Version:** v0r1 draft  
**Date:** 2026-05-15  
**Status:** Design memo  
**Target path:** `docs/design/case_japanese_rice_master_dataset.md`

**Related design documents:**

- `docs/design/case_japanese_rice_supply_chain_as_is_research.md`
- `docs/design/wom_case_modeling_base_dataset.md`
- `docs/design/case_japanese_rice_supply_chain_modeling.md`
- `docs/design/wom_e2e_constraint_management.md`
- `docs/design/wom_planning_operations_commands.md`

---

## 1. Purpose

This memo defines the **master dataset** for the Japanese Rice Supply Chain WOM case study.

The purpose is to convert the Rice Case modeling design into concrete CSV schemas and sample rows.

This memo is not yet the final implementation dataset.

It defines the ideal case-level master dataset first, then prepares for adapter mapping to the current WOM Planning Engine.

The intended flow is:

```text
Japanese Rice Supply Chain AS-IS Research
    ↓
Rice Case Modeling Design
    ↓
Rice Case Master Dataset
    ↓
Adapter to Current WOM CSV / Internal Model
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

## 2. Design Principle

### 2.1 Case dataset first, adapter second

The Rice Case should not be forced directly into the current WOM CSV format.

Instead, define a business-friendly and modeling-friendly dataset first.

```text
Rice Case Master Dataset:
    expresses real-world rice supply chain structure

Adapter:
    converts Rice Case Master Dataset into current WOM input files
```

### 2.2 Lot identity should be preserved

Rice should be represented as meaningful lots.

A lot may represent:

```text
harvest lot
brown rice lot
milled rice lot
packaged rice lot
premium rice lot
reserve rice lot
```

### 2.3 Quantity and money must be connected

The Rice Case should support both:

```text
quantity simulation:
    P / S / I / capacity

money simulation:
    price / cost / inventory value / profit / cash pressure
```

### 2.4 Scenario comparison must be supported

The dataset should support the five-view scenario framework:

```text
AS IS
TO BE
CAN BE
WILL BE
LET IT BE
```

---

## 3. File Set Overview

The Rice Case Master Dataset should include the following CSV files.

```text
case_japanese_rice/
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
    rice_adapter_mapping_master.csv
```

For the first MVP, the required files are:

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
rice_assumption_log.csv
```

`rice_lot_master.csv` may be generated from supply plan in the first MVP, but the schema should be defined.

---

## 4. rice_scenario_master.csv

### 4.1 Purpose

Defines Rice Case scenarios.

### 4.2 Schema

```csv
scenario_id,scenario_name,baseline_scenario_id,description,start_week,end_week,scenario_type,is_baseline,comment
```

### 4.3 Sample Rows

```csv
scenario_id,scenario_name,baseline_scenario_id,description,start_week,end_week,scenario_type,is_baseline,comment
RICE_AS_IS,Rice AS-IS,,Current simplified Japanese rice supply chain,2026-W01,2026-W52,AS_IS,true,baseline scenario
RICE_TO_BE_PREMIUM,Rice TO-BE Premium Strategy,RICE_AS_IS,Premium rice price uplift and brand strengthening,2026-W01,2026-W52,TO_BE,false,price uplift scenario
RICE_CAN_BE_STORAGE,Rice CAN-BE Storage Improvement,RICE_AS_IS,Storage cost reduction and inventory control,2026-W01,2026-W52,CAN_BE,false,realistic improvement scenario
RICE_WILL_BE_DEMAND_DECLINE,Rice WILL-BE Demand Decline,RICE_AS_IS,Domestic demand decline and inventory overhang risk,2026-W01,2026-W52,WILL_BE,false,risk scenario
RICE_LET_IT_BE_POLICY,Rice LET-IT-BE Policy Constraint,RICE_AS_IS,Policy reserve and minimum access treated as external constraints,2026-W01,2026-W52,LET_IT_BE,false,policy area not optimized
```

### 4.4 Notes

`baseline_scenario_id` is used for `KPIDelta` comparison.

`scenario_type` should follow:

```text
AS_IS
TO_BE
CAN_BE
WILL_BE
LET_IT_BE
OTHER
```

---

## 5. rice_node_master.csv

### 5.1 Purpose

Defines rice supply chain nodes.

### 5.2 Schema

```csv
scenario_id,node_id,node_name,node_type,tree_side,region,country,role,storage_type,is_buffer,is_bottleneck_candidate,comment
```

### 5.3 Sample Rows

```csv
scenario_id,node_id,node_name,node_type,tree_side,region,country,role,storage_type,is_buffer,is_bottleneck_candidate,comment
RICE_AS_IS,PRODUCER_NIIGATA,Producer Niigata,producer,INBOUND,NIIGATA,JP,rice production,none,false,true,aggregate producer region
RICE_AS_IS,COLLECTION_NIIGATA,Collection Niigata,collection,INBOUND,NIIGATA,JP,collection drying adjustment,warehouse,true,true,collection and adjustment node
RICE_AS_IS,BROWN_STORAGE_EAST,Brown Rice Storage East,storage,E2E,EAST,JP,brown rice storage,warehouse,true,true,seasonal inventory node
RICE_AS_IS,MILL_EAST,Milling East,milling,E2E,EAST,JP,milling process,none,false,true,milling capacity node
RICE_AS_IS,PACKAGING_EAST,Packaging East,packaging,E2E,EAST,JP,packaging process,none,false,true,packaging capacity node
RICE_AS_IS,WHOLESALER_EAST,Wholesaler East,wholesaler,OUTBOUND,EAST,JP,wholesale distribution,warehouse,true,true,wholesale inventory node
RICE_AS_IS,RETAIL_TOKYO,Retail Tokyo,retail,OUTBOUND,TOKYO,JP,household retail sales,store,true,false,household market node
RICE_AS_IS,FOOD_SERVICE_TOKYO,Food Service Tokyo,food_service,OUTBOUND,TOKYO,JP,food service demand,store,true,false,food service market node
RICE_AS_IS,DEMAND_HOUSEHOLD_TOKYO,Demand Household Tokyo,demand,OUTBOUND,TOKYO,JP,household consumption,none,false,false,final household demand
RICE_AS_IS,DEMAND_FOOD_SERVICE_TOKYO,Demand Food Service Tokyo,demand,OUTBOUND,TOKYO,JP,food service consumption,none,false,false,final food-service demand
```

### 5.4 Node Type Candidates

```text
producer
collection
storage
milling
packaging
wholesaler
retail
food_service
demand
reserve_storage
import_supply
export_market
```

---

## 6. rice_lane_master.csv

### 6.1 Purpose

Defines flows between nodes.

### 6.2 Schema

```csv
scenario_id,lane_id,from_node_id,to_node_id,lane_type,tree_side,transport_mode,leadtime_weeks,cold_chain_required,is_alternative,priority,comment
```

### 6.3 Sample Rows

```csv
scenario_id,lane_id,from_node_id,to_node_id,lane_type,tree_side,transport_mode,leadtime_weeks,cold_chain_required,is_alternative,priority,comment
RICE_AS_IS,LANE_PRODUCER_TO_COLLECTION,PRODUCER_NIIGATA,COLLECTION_NIIGATA,transport,INBOUND,truck,1,false,false,1,producer to collection
RICE_AS_IS,LANE_COLLECTION_TO_STORAGE,COLLECTION_NIIGATA,BROWN_STORAGE_EAST,transport,INBOUND,truck,1,false,false,1,collection to storage
RICE_AS_IS,LANE_STORAGE_TO_MILL,BROWN_STORAGE_EAST,MILL_EAST,transfer,E2E,truck,1,false,false,1,storage to milling
RICE_AS_IS,LANE_MILL_TO_PACKAGING,MILL_EAST,PACKAGING_EAST,process,E2E,internal,0,false,false,1,milling to packaging
RICE_AS_IS,LANE_PACKAGING_TO_WHOLESALER,PACKAGING_EAST,WHOLESALER_EAST,transport,OUTBOUND,truck,1,false,false,1,packaging to wholesaler
RICE_AS_IS,LANE_WHOLESALER_TO_RETAIL,WHOLESALER_EAST,RETAIL_TOKYO,transport,OUTBOUND,truck,1,false,false,1,wholesaler to retail
RICE_AS_IS,LANE_WHOLESALER_TO_FOOD_SERVICE,WHOLESALER_EAST,FOOD_SERVICE_TOKYO,transport,OUTBOUND,truck,1,false,false,1,wholesaler to food service
RICE_AS_IS,LANE_RETAIL_TO_HOUSEHOLD,RETAIL_TOKYO,DEMAND_HOUSEHOLD_TOKYO,demand,OUTBOUND,none,0,false,false,1,retail to household demand
RICE_AS_IS,LANE_FOOD_SERVICE_TO_DEMAND,FOOD_SERVICE_TOKYO,DEMAND_FOOD_SERVICE_TOKYO,demand,OUTBOUND,none,0,false,false,1,food service to final demand
```

### 6.4 Lane Type Candidates

```text
transport
process
transfer
demand
policy
import
export
```

---

## 7. rice_product_master.csv

### 7.1 Purpose

Defines rice product classes.

### 7.2 Schema

```csv
scenario_id,product_id,product_name,product_family,unit,lot_size,grade,brand_class,temperature_class,shelf_life_weeks,comment
```

### 7.3 Sample Rows

```csv
scenario_id,product_id,product_name,product_family,unit,lot_size,grade,brand_class,temperature_class,shelf_life_weeks,comment
RICE_AS_IS,BROWN_RICE_STANDARD,Brown Rice Standard,rice,kg,1000,standard,domestic_standard,ambient,52,brown rice lot
RICE_AS_IS,MILLED_RICE_STANDARD,Milled Rice Standard,rice,kg,1000,standard,domestic_standard,ambient,26,milled rice
RICE_AS_IS,PACKAGED_RICE_STANDARD,Packaged Rice Standard,rice,kg,1000,standard,domestic_standard,ambient,26,consumer packaged rice
RICE_AS_IS,PACKAGED_RICE_PREMIUM,Packaged Rice Premium,rice,kg,1000,premium,premium_brand,ambient,26,premium packaged rice
RICE_AS_IS,RESERVE_RICE,Reserve Rice,rice,kg,1000,standard,policy_reserve,ambient,104,government reserve candidate
RICE_AS_IS,IMPORTED_RICE,Imported Rice,rice,kg,1000,standard,imported,ambient,52,imported rice candidate
```

---

## 8. rice_lot_master.csv

### 8.1 Purpose

Defines rice lots as MEO planning objects.

### 8.2 Schema

```csv
scenario_id,lot_id,product_id,quantity,current_node_id,target_node_id,target_region,available_week,due_week,expiry_week,quality_status,priority,comment
```

### 8.3 Sample Rows

```csv
scenario_id,lot_id,product_id,quantity,current_node_id,target_node_id,target_region,available_week,due_week,expiry_week,quality_status,priority,comment
RICE_AS_IS,RICE-JP-2026W40-000001,BROWN_RICE_STANDARD,1000,COLLECTION_NIIGATA,BROWN_STORAGE_EAST,EAST,2026-W40,2026-W44,2027-W40,usable,100,harvest lot 1
RICE_AS_IS,RICE-JP-2026W40-000002,BROWN_RICE_STANDARD,1000,COLLECTION_NIIGATA,BROWN_STORAGE_EAST,EAST,2026-W40,2026-W44,2027-W40,usable,100,harvest lot 2
RICE_AS_IS,RICE-JP-2026W41-000001,BROWN_RICE_STANDARD,1000,COLLECTION_NIIGATA,BROWN_STORAGE_EAST,EAST,2026-W41,2026-W45,2027-W41,usable,100,harvest lot 3
```

### 8.4 MVP Note

For the first Rice MVP, `rice_lot_master.csv` may be generated automatically from `rice_supply_plan.csv`.

However, the schema should be retained because WOM's modeling principle is lot-based.

---

## 9. rice_supply_plan.csv

### 9.1 Purpose

Defines weekly rice supply.

### 9.2 Schema

```csv
scenario_id,node_id,product_id,week,supply_qty,supply_type,source_type,comment
```

### 9.3 Sample Rows

```csv
scenario_id,node_id,product_id,week,supply_qty,supply_type,source_type,comment
RICE_AS_IS,PRODUCER_NIIGATA,BROWN_RICE_STANDARD,2026-W40,20000,harvest,internal,harvest peak week 1
RICE_AS_IS,PRODUCER_NIIGATA,BROWN_RICE_STANDARD,2026-W41,30000,harvest,internal,harvest peak week 2
RICE_AS_IS,PRODUCER_NIIGATA,BROWN_RICE_STANDARD,2026-W42,30000,harvest,internal,harvest peak week 3
RICE_AS_IS,PRODUCER_NIIGATA,BROWN_RICE_STANDARD,2026-W43,15000,harvest,internal,harvest tail
RICE_AS_IS,PRODUCER_NIIGATA,BROWN_RICE_STANDARD,2026-W44,5000,harvest,internal,harvest tail
```

### 9.4 MVP Supply Pattern

For the first model:

```text
W40-W44:
    harvest input

Other weeks:
    supply_qty = 0
```

---

## 10. rice_demand_plan.csv

### 10.1 Purpose

Defines weekly demand.

### 10.2 Schema

```csv
scenario_id,demand_node_id,region,product_id,week,demand_qty,demand_type,priority,comment
```

### 10.3 Sample Rows

```csv
scenario_id,demand_node_id,region,product_id,week,demand_qty,demand_type,priority,comment
RICE_AS_IS,DEMAND_HOUSEHOLD_TOKYO,TOKYO,PACKAGED_RICE_STANDARD,2026-W01,1000,household,100,weekly household demand
RICE_AS_IS,DEMAND_HOUSEHOLD_TOKYO,TOKYO,PACKAGED_RICE_STANDARD,2026-W02,1000,household,100,weekly household demand
RICE_AS_IS,DEMAND_FOOD_SERVICE_TOKYO,TOKYO,PACKAGED_RICE_STANDARD,2026-W01,600,food_service,100,weekly food service demand
RICE_AS_IS,DEMAND_FOOD_SERVICE_TOKYO,TOKYO,PACKAGED_RICE_STANDARD,2026-W02,600,food_service,100,weekly food service demand
```

### 10.4 MVP Demand Pattern

For MVP:

```text
household weekly demand:
    constant

food service weekly demand:
    constant
```

Later versions may add seasonality.

---

## 11. rice_capacity_master.csv

### 11.1 Purpose

Defines node and lane capacity.

### 11.2 Schema

```csv
scenario_id,capacity_owner_type,capacity_owner_id,product_id,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
```

### 11.3 Sample Rows

```csv
scenario_id,capacity_owner_type,capacity_owner_id,product_id,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
RICE_AS_IS,node,BROWN_STORAGE_EAST,BROWN_RICE_STANDARD,2026-W40,I,100000,hard,kg,100,STD_CAL,brown rice storage capacity
RICE_AS_IS,node,MILL_EAST,BROWN_RICE_STANDARD,2026-W40,P,5000,hard,kg,100,STD_CAL,milling capacity
RICE_AS_IS,node,PACKAGING_EAST,MILLED_RICE_STANDARD,2026-W40,P,5000,hard,kg,100,STD_CAL,packaging capacity
RICE_AS_IS,lane,LANE_PACKAGING_TO_WHOLESALER,PACKAGED_RICE_STANDARD,2026-W40,S,5000,hard,kg,100,STD_CAL,transport capacity
RICE_AS_IS,node,WHOLESALER_EAST,PACKAGED_RICE_STANDARD,2026-W40,I,30000,hard,kg,100,STD_CAL,wholesaler storage capacity
```

### 11.4 Adapter Note

Current v0r2 `capacity_master.csv` uses:

```csv
scenario_id,tree_side,node_name,product_name,week,capacity_type,capacity_qty,cap_mode,unit,priority,calendar_id,comment
```

Adapter should map:

```text
capacity_owner_id → node_name
product_id → product_name
capacity_owner_type = lane → pseudo node or future flow-capacity support
```

---

## 12. rice_cost_price_master.csv

### 12.1 Purpose

Defines cost and price assumptions.

### 12.2 Schema

```csv
scenario_id,owner_type,owner_id,product_id,week,cost_price_type,unit_value,unit,currency,comment
```

### 12.3 Sample Rows

```csv
scenario_id,owner_type,owner_id,product_id,week,cost_price_type,unit_value,unit,currency,comment
RICE_AS_IS,node,PRODUCER_NIIGATA,BROWN_RICE_STANDARD,2026-W40,purchase_price,250,kg,JPY,producer purchase price
RICE_AS_IS,node,BROWN_STORAGE_EAST,BROWN_RICE_STANDARD,2026-W40,storage_cost_per_lot_week,50,kg,JPY,storage cost assumption
RICE_AS_IS,node,MILL_EAST,BROWN_RICE_STANDARD,2026-W40,milling_cost_per_lot,30,kg,JPY,milling cost assumption
RICE_AS_IS,lane,LANE_PACKAGING_TO_WHOLESALER,PACKAGED_RICE_STANDARD,2026-W40,transport_cost_per_lot,20,kg,JPY,transport cost assumption
RICE_AS_IS,node,RETAIL_TOKYO,PACKAGED_RICE_STANDARD,2026-W40,selling_price,500,kg,JPY,retail selling price
```

### 12.4 Cost / Price Types

```text
purchase_price
selling_price
storage_cost_per_lot_week
milling_cost_per_lot
packaging_cost_per_lot
transport_cost_per_lot
wholesale_handling_cost
retail_handling_cost
waste_cost_per_lot
```

---

## 13. rice_kpi_policy_master.csv

### 13.1 Purpose

Defines KPI evaluation rules and management intention.

### 13.2 Schema

```csv
scenario_id,kpi_id,weight,warning_threshold,critical_threshold,direction,comment
```

### 13.3 Sample Rows

```csv
scenario_id,kpi_id,weight,warning_threshold,critical_threshold,direction,comment
RICE_AS_IS,total_sc.inventory_value,0.20,10000000,20000000,lower_is_better,inventory burden
RICE_AS_IS,total_sc.profit_margin,0.30,0.05,0.02,higher_is_better,profitability
RICE_AS_IS,total_sc.capacity_utilization,0.10,0.90,0.98,lower_is_better,capacity stress
RICE_AS_IS,strategic.profit_sustainability_score,0.20,0.60,0.40,higher_is_better,profit sustainability
RICE_AS_IS,strategic.inventory_soundness_score,0.20,0.60,0.40,higher_is_better,inventory soundness
```

---

## 14. rice_scenario_parameter_master.csv

### 14.1 Purpose

Defines scenario-specific parameter changes.

### 14.2 Schema

```csv
scenario_id,parameter_id,target_type,target_id,product_id,week,value,unit,comment
```

### 14.3 Sample Rows

```csv
scenario_id,parameter_id,target_type,target_id,product_id,week,value,unit,comment
RICE_TO_BE_PREMIUM,premium_price_increase,node,RETAIL_TOKYO,PACKAGED_RICE_PREMIUM,2026-W01,0.10,ratio,10 percent premium price uplift
RICE_CAN_BE_STORAGE,storage_cost_reduction,node,BROWN_STORAGE_EAST,BROWN_RICE_STANDARD,2026-W40,-0.15,ratio,15 percent storage cost reduction
RICE_WILL_BE_DEMAND_DECLINE,household_demand_decline,demand,DEMAND_HOUSEHOLD_TOKYO,PACKAGED_RICE_STANDARD,2026-W01,-0.10,ratio,10 percent demand decline
```

### 14.4 Scenario Parameter Examples

```text
selling price change
demand change
storage cost change
transport cost change
milling capacity change
product mix change
```

---

## 15. rice_assumption_log.csv

### 15.1 Purpose

Documents assumptions.

This is important because initial Rice Case may use simplified assumptions.

### 15.2 Schema

```csv
scenario_id,assumption_id,category,description,value,source,confidence,comment
```

### 15.3 Sample Rows

```csv
scenario_id,assumption_id,category,description,value,source,confidence,comment
RICE_AS_IS,ASSUMP_WEEKLY_DEMAND,DEMAND,Weekly demand is evenly distributed across the year,annual demand / 52,model assumption,medium,replace with statistical profile later
RICE_AS_IS,ASSUMP_LOT_SIZE,LOT,One rice lot equals 1000 kg,1000 kg,model assumption,high,MVP lot size
RICE_AS_IS,ASSUMP_HARVEST_WEEKS,SUPPLY,Harvest peak is modeled from W40 to W44,W40-W44,model assumption,medium,needs real data validation
RICE_AS_IS,ASSUMP_STORAGE_COST,COST,Storage cost is simplified as fixed cost per kg per week,50 JPY/kg/week,model assumption,low,replace with realistic estimate later
```

---

## 16. rice_adapter_mapping_master.csv

### 16.1 Purpose

Defines mapping from Rice Case Master Dataset to current WOM input files.

### 16.2 Schema

```csv
case_dataset,case_field,wom_target_file,wom_target_field,transform_rule,comment
```

### 16.3 Sample Rows

```csv
case_dataset,case_field,wom_target_file,wom_target_field,transform_rule,comment
rice_node_master,node_id,node_master_sample.csv,node_name,copy,node id maps to WOM node name
rice_lane_master,from_node_id,node_relation.csv,parent_node,copy,source node
rice_lane_master,to_node_id,node_relation.csv,child_node,copy,destination node
rice_product_master,product_id,product_master.csv,product_name,copy,product id maps to WOM product name
rice_capacity_master,capacity_owner_id,capacity_master_sample.csv,node_name,pseudo_lane_if_owner_type_lane,lane capacity represented as pseudo node in current v0r2
rice_cost_price_master,unit_value,cost_price_master.csv,value,copy,cost and price value
```

---

## 17. Directory Layout

Suggested directory layout:

```text
case_data/
    japanese_rice/
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
        rice_adapter_mapping_master.csv
```

Alternative future package layout:

```text
pysi/cases/japanese_rice/
    data/
        ...
    adapters/
        ...
    runners/
        ...
```

---

## 18. MVP Dataset Scope

The first implementation should use a small dataset.

### 18.1 Minimal Nodes

```text
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
```

### 18.2 Minimal Products

```text
BROWN_RICE_STANDARD
MILLED_RICE_STANDARD
PACKAGED_RICE_STANDARD
```

### 18.3 Minimal Scenarios

```text
RICE_AS_IS
RICE_CAN_BE_STORAGE
RICE_WILL_BE_DEMAND_DECLINE
```

### 18.4 Minimal Evaluation

```text
quantity PSI
inventory buildup / drawdown
storage capacity
milling capacity
storage cost
selling price
gross profit
KPI delta vs AS IS
```

---

## 19. Relationship with Note Article

This dataset should support a follow-up note article:

```text
米のサプライチェーンをWOMでシミュレーションする
――パラメータ設定、価格感度分析、シナリオ比較の実例
```

The article should demonstrate:

```text
1. How the Rice Case is modeled
2. What master data is prepared
3. How AS IS is simulated
4. How cost / price sensitivity is added
5. How scenarios are compared
6. What management issues are revealed
```

---

## 20. Summary

The Japanese Rice Master Dataset defines the concrete CSV interface for modeling Rice Case in WOM.

The key point is:

```text
Do not model Rice Case directly from the current WOM CSV format.

Instead:
    define business-friendly Rice Case Master Dataset
    then use Adapter to connect to current WOM Planning Engine.
```

This enables the Rice Case to become a reusable demonstration of:

```text
WOM Modeling Process
quantity simulation
money evaluation
scenario comparison
management issue generation
```

The next step is to create:

```text
docs/design/case_japanese_rice_simulation_plan.md
```

which defines AS IS / TO BE / CAN BE / WILL BE / LET IT BE simulation scenarios and parameter settings.
