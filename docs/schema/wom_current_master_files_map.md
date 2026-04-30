# WOM Current Master Files Map v0.1

> File: `docs/schema/wom_current_master_files_map.md`  
> Status: Living Design Document v0.1  
> Owner: WOM Project / Yasushi Ohsugi × ChatGPT  
> Purpose: Current WOM master files の役割、層構造、key関係、整合ルール、MOSD adapter への接続方針を定義する。  
> Scope: 現行 WOM repository の `data/`, `data/cost_masters/`, `pysi/master_data/` 配下の master files を対象とする。  

---

## 1. Purpose

This document defines the current understanding of WOM master files.

It is a living design document used to align:

1. PSI planning master files
2. legacy money evaluation master files
3. semantic money overlay master files
4. extended costing master files
5. future MOSD / Master Original Source Data schema
6. future MOSD to WOM Master CSV adapter
7. future WOM AI Navigator Seed Prompt v0.4

This document is v0.1.  
The purpose is not to freeze all CSV formats permanently, but to define the current master data map so that future schema, adapter, validator, and AI Navigator functions can be designed consistently.

---

## 2. Current Master File Layer Model

Current WOM master data should be understood as a layered structure.

```text
Layer 0: MOSD / Master Original Source Data
  Future source data layer for industry case modeling.
  Not implemented yet.

Layer 1: Physical World Master
  data/node_geo.csv

Layer 2: Product-specific PSI Tree Master
  data/product_tree_inbound.csv
  data/product_tree_outbound.csv

Layer 3: PSI Quantity Master
  data/sku_P_month_data.csv
  data/sku_S_month_data.csv

Layer 4: Legacy Money Master
  data/sku_cost_table_inbound.csv
  data/sku_cost_table_outbound.csv
  data/offering_price_ASIS_TOBE.csv
  data/tariff_table.csv

Layer 5: Semantic Money Overlay
  pysi/master_data/node_master.csv
  pysi/master_data/node_character_money_master.csv
  pysi/master_data/node_product_money_master.csv

Layer 6: Extended Costing Master / Business Reporting Master
  data/cost_masters/product_cost_master.csv
  data/cost_masters/node_cost_master.csv
  data/cost_masters/lane_cost_master.csv
  data/cost_masters/sales_price_master.csv
  data/cost_masters/sga_marketing_tax_master.csv
  data/cost_masters/fixed_asset_cost_master.csv
  data/cost_masters/allocation_rule_master.csv
  data/cost_masters/market_master.csv
  data/cost_masters/cs_node_to_market_map.csv
  data/cost_masters/fx_rate_master.csv    # planned / recommended

Layer 7: Inbound Costing Experimental Templates
  data/cost_masters/wom_inbound_costing_templates/*.csv

Layer 8: Generated / Work / Backup
  data/cost_masters/work260415_0042/
  data/data_BK*/
```

---

## 3. Master File Inventory

### 3.1 PSI Planning / Quantity Master Files

| file | layer | current status | role |
|---|---:|---|---|
| `data/node_geo.csv` | 1 | active | Physical world map. Holds node latitude / longitude for network visualization. |
| `data/product_tree_inbound.csv` | 2 | active | Product-specific INBOUND planning tree. |
| `data/product_tree_outbound.csv` | 2 | active | Product-specific OUTBOUND planning tree. |
| `data/sku_P_month_data.csv` | 3 | active | Monthly product × node P input. Production / purchase / supply-side quantity profile. |
| `data/sku_S_month_data.csv` | 3 | active | Monthly product × node S input. Sales / shipment / demand-side quantity profile. |

### 3.2 Legacy Money Master Files

| file | layer | current status | role |
|---|---:|---|---|
| `data/sku_cost_table_inbound.csv` | 4 | legacy / active fallback | Product × node inbound cost table. Legacy money evaluation source. |
| `data/sku_cost_table_outbound.csv` | 4 | legacy / active fallback | Product × node outbound cost table. Legacy money evaluation source. |
| `data/offering_price_ASIS_TOBE.csv` | 4 | legacy / active fallback | Product × node sales price scenario table. |
| `data/tariff_table.csv` | 4 | legacy / active fallback | Product × lane tariff table. |

### 3.3 Semantic Money Overlay Files

| file | layer | current status | role |
|---|---:|---|---|
| `pysi/master_data/node_master.csv` | 5 | semantic overlay / active | Defines node_name, node_character, display_name, country, company. |
| `pysi/master_data/node_character_money_master.csv` | 5 | semantic overlay / active | Defines how each node_character should be interpreted in money evaluation. |
| `pysi/master_data/node_product_money_master.csv` | 5 | semantic overlay / prototype | Lightweight node × product valuation master. Needs full coverage expansion. |

### 3.4 Extended Costing Master Files

| file | layer | current status | role |
|---|---:|---|---|
| `data/cost_masters/product_cost_master.csv` | 6 | active candidate | Product cost / price / inventory value basis. |
| `data/cost_masters/node_cost_master.csv` | 6 | active candidate | Node-level cost structure. Labor, machine, utility, inventory holding, SGA, depreciation. |
| `data/cost_masters/lane_cost_master.csv` | 6 | active candidate | Lane-level logistics, insurance, tariff, lead time, risk cost. |
| `data/cost_masters/sales_price_master.csv` | 6 | active candidate | Product × market sales price, rebate, promotion, channel cost. |
| `data/cost_masters/sga_marketing_tax_master.csv` | 6 | active candidate | SGA / marketing / tax assumptions by market / region / node. |
| `data/cost_masters/fixed_asset_cost_master.csv` | 6 | active candidate | Fixed asset, investment, depreciation, maintenance cost. |
| `data/cost_masters/allocation_rule_master.csv` | 6 | active candidate | Cost allocation rules from source scope to target scope. |
| `data/cost_masters/market_master.csv` | 6 | active candidate | Market definition master. market_id is terminal market / channel / segment ID, not country code. |
| `data/cost_masters/cs_node_to_market_map.csv` | 6 | active candidate / bridge | Bridge from WOM OUTBOUND leaf node to market_id. |
| `data/cost_masters/fx_rate_master.csv` | 6 | planned / recommended | Scenario-based FX rate master for multi-currency reporting. |

### 3.5 Inbound Costing Experimental Templates

| file | layer | current status | role |
|---|---:|---|---|
| `event_cost_rule_master.csv` | 7 | experimental | Event-based cost rule template. |
| `inbound_adjustment_master.csv` | 7 | experimental | Inbound cost adjustment template. |
| `inbound_bom_usage_master.csv` | 7 | experimental | BOM usage / inbound component consumption template. |
| `inbound_item_master.csv` | 7 | experimental | Inbound item / material master template. |
| `inbound_price_decision_master.csv` | 7 | experimental | Inbound price decision template. |
| `node_character_cost_rule_master.csv` | 7 | experimental | Node-character based costing rule template. |
| `README_current_model_integration.md` | 7 | experimental note | Current integration notes for inbound costing templates. |

---

## 4. Key Design Principles

### 4.1 node_name is the canonical key

Current WOM master files should use `node_name` as the canonical node key.

```text
node_name = current WOM master key
```

Rules:

- `node_name` is the primary key for node-level references in current WOM master files.
- If `node_id` exists in some extended costing files, it should be treated as a secondary or alias key unless an explicit node_id-to-node_name mapping exists.
- Future DB design may introduce surrogate `node_id`, but current CSV modeling should use `node_name`.
- GUI selectors, PSI graphs, network layout, costing, and reporting should align around `node_name`.

### 4.2 MOM / DAD are reserved node prefixes

`MOM` and `DAD` are reserved naming prefixes.

Rules:

- `MOM_*` indicates INBOUND / manufacturing / upstream production type nodes.
- `DAD_*` indicates OUTBOUND / distribution / delivery type nodes.
- WOM network layout logic may use these prefixes to calculate node positions.
- Renaming MOM / DAD nodes may affect tree generation, GUI layout, costing, reporting, and event visualization.

This is not only a naming convention.  
It is also a GUI layout contract.

### 4.3 supply_point is a reserved common node_name

`supply_point` is a reserved node_name.

Rules:

- `supply_point` connects INBOUND and OUTBOUND trees.
- `supply_point` should be defined once in `pysi/master_data/node_master.csv`.
- `supply_point` may appear in both `product_tree_inbound.csv` and `product_tree_outbound.csv`.
- INBOUND and OUTBOUND references to `supply_point` should be interpreted as the same E2E management point.
- KPI, inventory, cost, allocation, and supply-demand balance may be reaggregated at `supply_point`.
- `supply_point` should not be treated as two independent physical nodes.

Recommended node_master definition:

```text
supply_point,SUPPLY_CHAIN_OFFICE,Global Supply Chain Office,GLOBAL,WOM,internal id kept for backward compatibility
```

### 4.4 root is a virtual node

`root` may appear in tree definitions as a virtual root.

Rules:

- `root` is not necessarily required in `node_master.csv`.
- Validator may exclude `root` from product_tree-to-node_master coverage checks.
- `root` should not be treated as a costing or reporting node unless explicitly defined.

### 4.5 market_id is not country

`market_id` is not a country code.

`market_id` represents:

```text
terminal market
sales channel
consumer segment
customer segment
price policy unit
service policy unit
```

Rules:

- `market_id` is the primary key of `market_master.csv`.
- `country` is an attribute of `market_id`.
- `region`, `channel`, `segment`, `priority_class`, `service_policy`, `price_policy`, and `currency` are also attributes of `market_id`.
- Large countries may contain many market_ids.
- Do not use country code as market_id unless the market model is intentionally country-level.

Recommended example:

```text
market_id = MKT_US_PREMIUM
country   = US
channel   = ONLINE
segment   = PREMIUM
```

### 4.6 cs_node_to_market_map is a formal bridge master

`cs_node_to_market_map.csv` connects WOM OUTBOUND leaf nodes to market management units.

```text
WOM OUTBOUND leaf node
  ↓
cs_node_to_market_map
  ↓
market_id
  ↓
market_master
  ↓
country / region / channel / segment / priority / price policy
```

Rules:

- `node_name` is a supply chain planning node.
- `market_id` is a commercial / management market unit.
- `country` belongs to `market_master`, not to `cs_node_to_market_map`.
- This bridge is required for market P/L, sales allocation, service policy, price policy, and priority analysis.

### 4.7 PAD is not a standard node_character

`PAD` originated as a sample-specific node naming concept.

Current rule:

- PAD is not a standard node_character in current WOM master definition.
- If a node name contains PAD, map it to an existing reusable node_character such as `MOM`, `SUPPLIER`, `FARM`, or `PRODUCTION`, depending on scenario.
- Do not add PAD to `node_character_money_master.csv` unless a reusable accounting behavior is explicitly defined.

---

## 5. File-by-File Definition

### 5.1 `data/node_geo.csv`

Role:

- Defines physical map positions.
- Product-independent.
- Used for network visualization.

Expected key:

```text
node_name
```

Typical columns:

```text
node_name
lat
lon
```

References:

- `node_name` should exist in `pysi/master_data/node_master.csv`, except virtual or display-only nodes if explicitly allowed.

MOSD adapter target:

```text
MOSD.physical_nodes → data/node_geo.csv
```

---

### 5.2 `data/product_tree_inbound.csv`

Role:

- Defines product-specific INBOUND planning tree.
- Represents supplier / material / manufacturing / MOM side flow into supply_point.

Expected key:

```text
Product_name + Parent_node + Child_node
```

Important columns:

```text
Product_name
Parent_node
Child_node
child_node_name
lot_size
leadtime
process_capa
long_vacation_weeks
LT_boat
LT_air
LT_qourier
weeks_year
SS_days
TAX_currency_condition
HS_code
customs_tariff_rate
price_elasticity
cost_standard_flag
AR_lead_time
AP_lead_time
PSI_graph_flag
buffering_stock_flag
```

References:

- `Parent_node` and `Child_node` should exist in `node_master.csv`, except `root`.
- `Product_name` should exist in product master or current active product list.
- `Child_node` may include `supply_point`.

MOSD adapter target:

```text
MOSD.product_plan_edges where bound = IN → data/product_tree_inbound.csv
```

---

### 5.3 `data/product_tree_outbound.csv`

Role:

- Defines product-specific OUTBOUND planning tree.
- Represents supply_point to DAD / warehouse / retailer / consumer / market-side flow.

Expected key:

```text
Product_name + Parent_node + Child_node
```

References:

- `Parent_node` and `Child_node` should exist in `node_master.csv`, except `root`.
- `Product_name` should exist in product master or current active product list.
- `Parent_node` or `Child_node` may include `supply_point`.
- OUTBOUND leaf nodes may be mapped to `market_id` through `cs_node_to_market_map.csv`.

MOSD adapter target:

```text
MOSD.product_plan_edges where bound = OUT → data/product_tree_outbound.csv
```

---

### 5.4 `data/sku_P_month_data.csv`

Role:

- Defines monthly P input by product and node.
- Used for production, purchase, or supply-side capacity / input profile.

Expected key:

```text
product_name + node_name + year
```

Typical columns:

```text
product_name
node_name
year
m1
m2
...
m12
```

References:

- `product_name` should exist in active product list.
- `node_name` should exist in `node_master.csv`.
- `node_name` should generally exist in product_tree_inbound or product_tree_outbound for that product.

MOSD adapter target:

```text
MOSD.quantity_profiles where bucket = P → data/sku_P_month_data.csv
```

---

### 5.5 `data/sku_S_month_data.csv`

Role:

- Defines monthly S input by product and node.
- Used for sales, shipment, or demand-side profile.

Expected key:

```text
product_name + node_name + year
```

References:

- `product_name` should exist in active product list.
- `node_name` should exist in `node_master.csv`.
- Demand / sales nodes should generally be OUTBOUND nodes or market-facing nodes.

MOSD adapter target:

```text
MOSD.quantity_profiles where bucket = S → data/sku_S_month_data.csv
```

---

### 5.6 Legacy money master files

Legacy money master files include:

```text
data/sku_cost_table_inbound.csv
data/sku_cost_table_outbound.csv
data/offering_price_ASIS_TOBE.csv
data/tariff_table.csv
```

Current rule:

- They are legacy / active fallback.
- They should not be removed until extended costing masters fully cover required reporting and scenario use cases.
- They may seed extended costing masters such as `product_cost_master.csv`, `node_cost_master.csv`, `lane_cost_master.csv`, and `sales_price_master.csv`.

---

## 6. Semantic Money Overlay Definitions

### 6.1 `pysi/master_data/node_master.csv`

Role:

- Defines node semantic identity.
- Provides node_character, display_name, country, company, remarks.

Expected key:

```text
node_name
```

Recommended columns:

```text
node_name
node_character
display_name
country
company
remarks
```

Rules:

- `node_name` should be unique.
- `supply_point` should appear once.
- All product_tree nodes except `root` should exist here.
- MOM / DAD prefixes should align with node_character where applicable.
- `PAD` should not be added as standard node_character unless reusable accounting meaning is defined.

MOSD adapter target:

```text
MOSD.physical_nodes / logical_nodes → pysi/master_data/node_master.csv
```

### 6.2 `pysi/master_data/node_character_money_master.csv`

Role:

- Defines accounting interpretation by node_character.
- It is a semantic overlay, not a replacement for cost tables.

Expected key:

```text
node_character
```

Recommended columns:

```text
node_character
revenue_items
variable_cost_items
fixed_cost_items
inventory_value_items
tax_compare_items
```

Examples of node_character:

```text
SUPPLY_CHAIN_OFFICE
MOM
DAD
WS
RT
CS
SUPPLIER
MARKET
CONSUMER
```

### 6.3 `pysi/master_data/node_product_money_master.csv`

Role:

- Lightweight node × product valuation master.
- Supports 2 phase costing and immediate Management Cockpit / GUI money display.
- Should be treated as semantic overlay / generated valuation table, not full replacement for extended costing master.

Expected key:

```text
node_name + product_name
```

Recommended columns:

```text
node_name
product_name
inventory_unit_value
revenue_unit_value
variable_cost_unit_value
fixed_cost_weekly
currency
remarks
```

Current issue:

- Prototype coverage may include only limited products.
- It should be expanded to cover active product × relevant node combinations.

Recommended rule:

```text
product_tree product-node combinations should be covered, either explicitly or via generated fallback.
```

---

## 7. Extended Costing Master Definitions

### 7.1 `data/cost_masters/product_cost_master.csv`

Role:

- Defines product-level cost and value assumptions.
- Supports standard material cost, production cost, purchase cost, inventory valuation.

Expected key:

```text
product_name
```

MOSD adapter target:

```text
MOSD.products.cost_assumptions → product_cost_master.csv
```

### 7.2 `data/cost_masters/node_cost_master.csv`

Role:

- Defines node-level operating cost structure.
- Supports labor, machine, utility, storage, SGA, depreciation-like periodic costs.

Expected key:

```text
node_name
```

Rules:

- Node key should align with `pysi/master_data/node_master.csv`.
- If current sample uses `node_id`, future cleanup should map it to `node_name` or rename to `node_name`.

MOSD adapter target:

```text
MOSD.nodes.cost_assumptions → node_cost_master.csv
```

### 7.3 `data/cost_masters/lane_cost_master.csv`

Role:

- Defines transportation, insurance, tariff, logistics, risk, and lead time by lane.

Expected key:

```text
from_node + to_node + transport_mode + scenario_name + valid_from_week + valid_to_week
```

Rules:

- `from_node` and `to_node` should exist in `node_master.csv`.
- Lane should also exist in product tree or be scenario-specific alternative lane.
- Currency should be convertible using `fx_rate_master.csv`.

MOSD adapter target:

```text
MOSD.lanes.cost_assumptions → lane_cost_master.csv
```

### 7.4 `data/cost_masters/sales_price_master.csv`

Role:

- Defines product × market sales price and commercial deductions.
- Supports price, rebate, promotion, gross-to-net, return rate, channel cost.

Expected key:

```text
product_name + market_id + customer_segment + scenario_name + valid_from_week + valid_to_week
```

Rules:

- `market_id` should exist in `market_master.csv`.
- `market_id` is not country.
- Price currency should be convertible using `fx_rate_master.csv`.

MOSD adapter target:

```text
MOSD.markets.price_assumptions → sales_price_master.csv
```

### 7.5 `data/cost_masters/sga_marketing_tax_master.csv`

Role:

- Defines SGA, marketing, and tax assumptions by market / region / node / product family.

Expected key:

```text
scope_type + scope_id + product_family + scenario_name + valid_from_week + valid_to_week
```

Rules:

- `scope_type` may be market, region, country, node, company.
- `scope_id` should refer to the appropriate master.
- Currency should be convertible using `fx_rate_master.csv`.

### 7.6 `data/cost_masters/fixed_asset_cost_master.csv`

Role:

- Defines fixed asset, investment, depreciation, and maintenance cost.
- Supports management reporting and investment impact analysis.

Expected key:

```text
asset_id + node_name + valid_from_week + valid_to_week
```

Rules:

- `node_name` should exist in `node_master.csv`.
- Currency should be convertible using `fx_rate_master.csv`.

### 7.7 `data/cost_masters/allocation_rule_master.csv`

Role:

- Defines allocation rules for cost pools.
- Used to allocate factory overhead, global SGA, common logistics, shared asset cost, etc.

Expected key:

```text
rule_id + scenario_name + valid_from_week + valid_to_week
```

Recommended columns:

```text
rule_id
cost_pool
source_scope
source_scope_id
target_scope
target_scope_id
allocation_basis
weight
valid_from_week
valid_to_week
scenario_name
remarks
```

Critical rule:

```text
target_scope_id must not be blank.
Use target_scope_id = ALL for all relevant targets.
```

Meaning of `ALL`:

```text
ALL means all relevant targets under target_scope,
filtered by scenario, active_flag, product, mapping, and allocation_basis.
```

Validator rule:

- blank `target_scope_id` should be warning or error.
- `target_scope_id = ALL` is valid.
- `allocation_basis` should be supported by reporting engine.

### 7.8 `data/cost_masters/market_master.csv`

Role:

- Defines market management units.
- `market_id` is the primary key.

Expected key:

```text
market_id
```

Recommended columns:

```text
market_id
market_name
country
region
channel
segment
priority_class
service_policy
price_policy
currency
active_flag
remarks
```

Rules:

- `market_id` is not country.
- `country` is an attribute.
- `channel`, `segment`, `priority_class`, `service_policy`, and `price_policy` are attributes.
- `market_id` should be referenced by `sales_price_master.csv`, `cs_node_to_market_map.csv`, and allocation/reporting processes.

MOSD adapter target:

```text
MOSD.markets → market_master.csv
```

### 7.9 `data/cost_masters/cs_node_to_market_map.csv`

Role:

- Formal bridge master from WOM OUTBOUND leaf node to `market_id`.

Expected key:

```text
scenario_name + product_name + node_name + market_id + valid_from_week + valid_to_week
```

Recommended columns:

```text
node_name
market_id
product_name
allocation_ratio
priority_class
service_policy
price_policy
valid_from_week
valid_to_week
scenario_name
active_flag
remarks
```

Rules:

- `node_name` should exist in `product_tree_outbound.csv`.
- `node_name` should generally be OUTBOUND leaf node.
- `market_id` should exist in `market_master.csv`.
- `allocation_ratio > 0`.
- For the same scenario/product/node/week, allocation_ratio should generally sum to 1.0.
- `country` should not be duplicated here. It belongs to `market_master.csv`.

MOSD adapter target:

```text
MOSD.node_market_mapping → cs_node_to_market_map.csv
```

### 7.10 `data/cost_masters/fx_rate_master.csv`

Role:

- Defines scenario-based and period-based FX conversion rates.
- Required for multi-currency money evaluation and Business Reporting.

Status:

```text
planned / recommended
```

Recommended location:

```text
data/cost_masters/fx_rate_master.csv
```

Recommended columns:

```text
scenario_name
from_currency
to_currency
fx_rate
rate_type
valid_from_week
valid_to_week
source_type
confidence
remarks
```

Recommended example:

```csv
scenario_name,from_currency,to_currency,fx_rate,rate_type,valid_from_week,valid_to_week,source_type,confidence,remarks
BAU,JPY,USD,0.0067,planning_rate,1,52,user_assumption,medium,annual planning rate
BAU,USD,JPY,150.0,planning_rate,1,52,user_assumption,medium,annual planning rate
FX_WEAK_JPY,JPY,USD,0.0059,scenario_rate,10,52,navigator_assumption,low,weak JPY scenario
FX_WEAK_JPY,USD,JPY,170.0,scenario_rate,10,52,navigator_assumption,low,weak JPY scenario
```

Primary key:

```text
scenario_name + from_currency + to_currency + valid_from_week + valid_to_week
```

Validator rules:

- `from_currency != to_currency`
- `fx_rate > 0`
- `valid_from_week <= valid_to_week`
- No overlapping periods for the same scenario/from/to combination
- Reporting currency conversion path must exist
- Do not assume implicit inverse FX rates unless explicitly allowed
- Define both directions when needed

MOSD adapter target:

```text
MOSD.currencies.fx_rates → fx_rate_master.csv
```

---

## 8. Primary Key Summary

| file | primary key |
|---|---|
| `node_geo.csv` | `node_name` |
| `product_tree_inbound.csv` | `Product_name + Parent_node + Child_node` |
| `product_tree_outbound.csv` | `Product_name + Parent_node + Child_node` |
| `sku_P_month_data.csv` | `product_name + node_name + year` |
| `sku_S_month_data.csv` | `product_name + node_name + year` |
| `sku_cost_table_inbound.csv` | `product_name + node_name` |
| `sku_cost_table_outbound.csv` | `product_name + node_name` |
| `offering_price_ASIS_TOBE.csv` | `product_name + node_name` |
| `node_master.csv` | `node_name` |
| `node_character_money_master.csv` | `node_character` |
| `node_product_money_master.csv` | `node_name + product_name` |
| `product_cost_master.csv` | `product_name` |
| `node_cost_master.csv` | `node_name` |
| `lane_cost_master.csv` | `from_node + to_node + transport_mode + scenario_name + valid_from_week + valid_to_week` |
| `sales_price_master.csv` | `product_name + market_id + customer_segment + scenario_name + valid_from_week + valid_to_week` |
| `sga_marketing_tax_master.csv` | `scope_type + scope_id + product_family + scenario_name + valid_from_week + valid_to_week` |
| `fixed_asset_cost_master.csv` | `asset_id + node_name + valid_from_week + valid_to_week` |
| `allocation_rule_master.csv` | `rule_id + scenario_name + valid_from_week + valid_to_week` |
| `market_master.csv` | `market_id` |
| `cs_node_to_market_map.csv` | `scenario_name + product_name + node_name + market_id + valid_from_week + valid_to_week` |
| `fx_rate_master.csv` | `scenario_name + from_currency + to_currency + valid_from_week + valid_to_week` |

---

## 9. Reference Relationships

### 9.1 Node references

```text
product_tree_inbound.Parent_node / Child_node
product_tree_outbound.Parent_node / Child_node
sku_P_month_data.node_name
sku_S_month_data.node_name
node_geo.node_name
node_product_money_master.node_name
node_cost_master.node_name
lane_cost_master.from_node / to_node
fixed_asset_cost_master.node_name
cs_node_to_market_map.node_name
  → pysi/master_data/node_master.node_name
```

Exception:

```text
root may be excluded as virtual node.
```

### 9.2 Product references

```text
product_tree_inbound.Product_name
product_tree_outbound.Product_name
sku_P_month_data.product_name
sku_S_month_data.product_name
sku_cost_table_inbound.product_name
sku_cost_table_outbound.product_name
node_product_money_master.product_name
product_cost_master.product_name
sales_price_master.product_name
cs_node_to_market_map.product_name
  → active product list / future product master
```

### 9.3 Market references

```text
cs_node_to_market_map.market_id
sales_price_master.market_id
allocation_rule_master target_scope_id when target_scope = market and target_scope_id != ALL
  → market_master.market_id
```

### 9.4 Currency references

```text
product_cost_master.currency
node_cost_master.currency
lane_cost_master.currency
sales_price_master.currency
sga_marketing_tax_master.currency
fixed_asset_cost_master.currency
market_master.currency
node_product_money_master.currency
  → fx_rate_master.from_currency / to_currency
```

---

## 10. Master Consistency Rules

### Rule 1: product_tree nodes must exist in node_master

```text
(product_tree_inbound nodes ∪ product_tree_outbound nodes) - {root}
  ⊆ node_master.node_name
```

### Rule 2: supply_point is unique in node_master

```text
count(node_master.node_name == "supply_point") = 1
```

### Rule 3: supply_point may appear in both trees

```text
supply_point may appear in product_tree_inbound
supply_point may appear in product_tree_outbound
```

This is not duplication.  
It is a shared E2E connection point.

### Rule 4: MOM / DAD prefixes are reserved

```text
MOM_* → inbound / manufacturing / upstream production
DAD_* → outbound / distribution / delivery
```

### Rule 5: market_id and country must not be confused

```text
market_id = terminal market / channel / segment
country   = attribute of market_id
```

### Rule 6: cs_node_to_market_map is required for market reporting

Market-level P/L, priority allocation, sales price interpretation, and service policy require:

```text
OUTBOUND leaf node → market_id mapping
```

### Rule 7: allocation target_scope_id must not be blank

Use:

```text
target_scope_id = ALL
```

for all relevant targets.

### Rule 8: multi-currency reporting requires fx_rate_master

Any money evaluation involving multiple currencies requires:

```text
fx_rate_master.csv
```

### Rule 9: PAD is not a standard node_character

PAD should not be added as standard node_character without reusable accounting behavior.

### Rule 10: legacy money masters remain fallback / seed data

Legacy money masters should not be deleted until extended costing masters fully cover required use cases.

---

## 11. Validator Rules

Recommended validator modules:

```text
pysi/modeling/wom_master_validator.py
pysi/modeling/cost_master_validator.py
```

### 11.1 Node validation

- `node_master.node_name` is unique.
- `supply_point` exists once.
- `product_tree` nodes exist in `node_master`, excluding `root`.
- MOM / DAD prefix is consistent with node_character when applicable.
- `node_geo.node_name` exists in `node_master`.

### 11.2 Product validation

- All products in quantity files exist in product trees.
- All products in cost files exist in active product list.
- `node_product_money_master` covers active product-node combinations or has fallback rule.

### 11.3 Tree validation

- INBOUND and OUTBOUND trees are connected through `supply_point`.
- Parent / child references are valid.
- No unexpected cycles unless explicitly allowed.
- Lead times and capacities are non-negative.
- lot_size is positive.

### 11.4 Market validation

- `market_master.market_id` is unique.
- `cs_node_to_market_map.market_id` exists in `market_master`.
- `cs_node_to_market_map.node_name` exists in OUTBOUND tree.
- `allocation_ratio > 0`.
- For same scenario/product/node/week, allocation_ratio should generally sum to 1.0.
- `country` is managed in `market_master`, not duplicated in mapping file.

### 11.5 Costing validation

- `node_cost_master.node_name` exists in `node_master`.
- `lane_cost_master.from_node` and `to_node` exist in `node_master`.
- `sales_price_master.market_id` exists in `market_master`.
- `allocation_rule_master.target_scope_id` is not blank.
- `target_scope_id = ALL` is accepted.
- Currency fields are convertible to reporting currency through `fx_rate_master`.

### 11.6 FX validation

- `from_currency != to_currency`.
- `fx_rate > 0`.
- Valid week ranges do not overlap for same scenario/from/to combination.
- Required reporting currency conversion path exists.
- Inverse rates are not assumed unless a policy explicitly allows it.

---

## 12. MOSD Adapter Output Targets

Future MOSD adapter should generate or update the following WOM masters.

```text
MOSD.physical_nodes
  → data/node_geo.csv
  → pysi/master_data/node_master.csv

MOSD.product_plan_edges where bound = IN
  → data/product_tree_inbound.csv

MOSD.product_plan_edges where bound = OUT
  → data/product_tree_outbound.csv

MOSD.quantity_profiles where bucket = P
  → data/sku_P_month_data.csv

MOSD.quantity_profiles where bucket = S
  → data/sku_S_month_data.csv

MOSD.products.cost_assumptions
  → data/cost_masters/product_cost_master.csv

MOSD.nodes.cost_assumptions
  → data/cost_masters/node_cost_master.csv
  → pysi/master_data/node_product_money_master.csv when lightweight valuation is needed

MOSD.lanes.cost_assumptions
  → data/cost_masters/lane_cost_master.csv

MOSD.markets
  → data/cost_masters/market_master.csv

MOSD.node_market_mapping
  → data/cost_masters/cs_node_to_market_map.csv

MOSD.markets.price_assumptions
  → data/cost_masters/sales_price_master.csv

MOSD.sga_marketing_tax_assumptions
  → data/cost_masters/sga_marketing_tax_master.csv

MOSD.fixed_assets
  → data/cost_masters/fixed_asset_cost_master.csv

MOSD.allocation_rules
  → data/cost_masters/allocation_rule_master.csv

MOSD.currencies.fx_rates
  → data/cost_masters/fx_rate_master.csv
```

---

## 13. Current Status Classification

| classification | meaning |
|---|---|
| active | Current WOM execution depends on this file. |
| legacy | Older format still useful for compatibility or fallback. |
| semantic overlay | Adds accounting / management interpretation rather than replacing base cost data. |
| active candidate | Strong candidate for future正本 in full costing / reporting. |
| experimental | Useful design prototype, not yet full正本. |
| planned | Not yet implemented but recommended for consistency. |
| generated / work | Intermediate, backup, or generated outputs. |

---

## 14. Reporting / Execution Notes

Current cost reporting test run note:

```bash
python -m compileall pysi\reporting
python -m pysi.reporting.sample_env_reporting_run
```

This should be treated as the current reporting execution entry point for sample-level Business Reporting validation.

---

## 15. Open Issues / Future Decisions

### 15.1 Product master正本

Current product identity is spread across product trees, quantity files, and cost files.

Future recommendation:

```text
data/product_master.csv
```

or MOSD product section should become the source for active product list.

### 15.2 node_id vs node_name

Current rule is:

```text
node_name is canonical.
```

Future DB implementation may introduce `node_id` as surrogate key, but CSV master consistency should remain human-readable through `node_name`.

### 15.3 Legacy money master migration

Legacy files:

```text
sku_cost_table_inbound.csv
sku_cost_table_outbound.csv
offering_price_ASIS_TOBE.csv
tariff_table.csv
```

should remain until extended costing masters fully cover reporting and scenario needs.

### 15.4 PAD / agriculture-specific node character

PAD should not be standard node_character for now.

Future agriculture or primary production templates may define:

```text
FARM
AGRI_PRODUCTION
PRIMARY_PRODUCTION
```

instead of PAD.

### 15.5 FX master implementation

`fx_rate_master.csv` should be added before serious multi-currency Business Reporting.

### 15.6 Extended costing master正本化

`data/cost_masters/*.csv` should be treated as the正本候補 for future Business Reporting and 2 phase costing.

---

## 16. Next Documents

This document should be used as the basis for:

```text
1. docs/schema/wom_master_original_source_data_schema.md
2. pysi/modeling/wom_master_adapter.py
3. pysi/modeling/wom_master_validator.py
4. docs/ai_navigator/wom_e2e_supply_chain_navigator_seed_prompt_v0_4.md
```

Recommended next step:

```text
Create MOSD schema v0.1 based on this current master file map.
```
