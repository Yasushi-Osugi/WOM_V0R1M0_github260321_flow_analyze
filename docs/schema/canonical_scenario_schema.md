# Canonical Scenario Schema

Version: v0.1  
Status: Draft  
Owner: WOM Core  
Purpose: Define the minimum common scenario data structure for WOM core planning, visualization, comparison, and future auto-generation.

---

## 1. Objective

WOM currently receives scenario information through multiple CSV files with overlapping responsibilities:

- monthly demand series
- monthly supply series
- outbound / inbound network trees
- cost tables
- offering price overrides
- tariff tables
- node geo information

The purpose of this canonical schema is to normalize those inputs into a stable core structure so that WOM can support:

- outbound planning
- inbound planning
- inbound / outbound comparison
- cost / price / profit analysis
- scenario auto-generation
- balancing simulation
- future lane-change and tax-aware extensions

This schema is designed to preserve current WOM logic while separating mixed concerns that are currently bundled in tree files.

---

## 2. Source files used for this definition

The current schema proposal is based on the following uploaded source files:

- `sku_S_month_data.csv`
- `sku_P_month_data.csv`
- `product_tree_outbound.csv`
- `product_tree_inbound.csv`
- `sku_cost_table_outbound.csv`
- `sku_cost_table_inbound.csv`
- `offering_price_ASIS_TOBE.csv`
- `tariff_table.csv`
- `node_geo.csv`

Observed examples from these files include:

- demand is stored by `product_name`, `node_name`, `year`, `m1..m12`
- supply is stored by `product_name`, `node_name`, `year`, `m1..m12`
- tree files mix lane structure and node/product/lane attributes such as `lot_size`, `leadtime`, `process_capa`, `LT_boat`, `HS_code`, `AR_lead_time`, and `buffering_stock_flag`
- cost tables are already node-based and product-based
- tariff is stored separately by `product_name`, `from_node`, `to_node`
- geo coordinates are node-based

---

## 3. Canonical design principles

The canonical schema follows these principles:

1. One scenario must be storable, rerunnable, and comparable as a single coherent unit.
2. Outbound and inbound must share the same structural model.
3. Quantity model and value model must be separable but linkable.
4. Tree structure and attribute tables must be separated.
5. Source period and planning period must both be explicit.
6. Units of measure must be explicit.
7. Missing values must be permitted when the source files are incomplete, but such gaps must be visible and auditable.

---

## 4. Core entities

The canonical schema consists of the following logical entities:

1. `scenario_header`
2. `product_master`
3. `node_master`
4. `lane_master`
5. `demand_series`
6. `supply_series`
7. `value_profile`
8. `tariff_profile`
9. `price_override_profile`

Optional future entities:

- `scenario_policy`
- `inventory_opening`
- `capacity_override`
- `service_policy`
- `compare_config`

---

## 5. Canonical entity definitions

### 5.1 scenario_header

This is the scenario-level control table.

| field | type | required | description |
|---|---|---:|---|
| scenario_id | string | Yes | Unique scenario identifier |
| scenario_name | string | Yes | Human-readable scenario name |
| version | string | Yes | Schema or scenario version |
| as_of_date | date | Yes | Baseline date for the scenario |
| planning_scope | enum | Yes | `outbound`, `inbound`, or `both` |
| source_period_type | enum | Yes | `month`, `week`, or other source granularity |
| planning_period_type | enum | Yes | WOM execution granularity, currently expected to be `week` |
| base_currency | string | Yes | Currency code such as `USD` |
| baseline_scenario_id | string | No | Optional reference for before/after comparison |
| notes | string | No | Optional notes |

#### Initial default rules
- `source_period_type = month`
- `planning_period_type = week`
- `planning_scope` must be explicit and never inferred
- `base_currency` must be explicitly set because current files do not contain a currency field

---

### 5.2 product_master

This is the normalized product definition.

| field | type | required | description |
|---|---|---:|---|
| scenario_id | string | Yes | Scenario reference |
| product_id | string | Yes | Internal product identifier |
| product_name | string | Yes | Product name from current files |
| units_per_lot | number | Yes | Quantity represented by one lot |
| weeks_year | integer | Yes | Weeks per year |
| hs_code | string | No | Harmonized code |
| price_elasticity | number | No | Price elasticity parameter |
| cost_standard_flag | string/int | No | Cost standard setting flag |

#### Mapping notes
Current tree files already contain `lot_size`, `weeks_year`, `HS_code`, `price_elasticity`, and `cost_standard_flag`. Those should be normalized into `product_master` instead of duplicated on every lane row.

---

### 5.3 node_master

This is the normalized node definition.

| field | type | required | description |
|---|---|---:|---|
| scenario_id | string | Yes | Scenario reference |
| node_id | string | Yes | Internal node identifier |
| node_name | string | Yes | Node name |
| node_type | enum | Yes | Functional node type |
| direction_scope | enum | Yes | `outbound`, `inbound`, or `both` |
| lat | number | No | Latitude |
| lon | number | No | Longitude |
| psi_graph_flag | string | No | Current PSI visualization flag |
| buffering_stock_flag | string | No | Buffering stock indicator |
| long_vacation_weeks | string/json | No | Long vacation weeks definition |
| default_currency | string | No | Optional node currency |

#### Initial node_type inference rule
Until a dedicated node-type master exists, the following naming-based inference is acceptable as a draft convention:

| node prefix / name | inferred node_type |
|---|---|
| `root` | root |
| `supply_point` | source |
| `MOM_` | mother_assembly |
| `PAD_` | postponement_or_downstream_assembly |
| `DAD_` | demand_allocation_hub |
| `WS_` | warehouse |
| `RT_` | retail_channel |
| `CS_` | consumer_market |

This is an initial heuristic only. Final node type should be explicitly overridable.

---

### 5.4 lane_master

This is the normalized network structure table.

| field | type | required | description |
|---|---|---:|---|
| scenario_id | string | Yes | Scenario reference |
| direction | enum | Yes | `outbound` or `inbound` |
| product_name | string | Yes | Product name |
| parent_node | string | Yes | Parent node |
| child_node | string | Yes | Child node |
| leadtime_weeks | number | Yes | Standard lead time in weeks |
| process_capa_per_bucket | number | Yes | Capacity per planning bucket |
| ss_days | number | No | Safety stock days |
| lt_boat | number | No | Boat lead time |
| lt_air | number | No | Air lead time |
| lt_courier | number | No | Courier lead time |
| ar_lead_time | number | No | Accounts receivable lead time |
| ap_lead_time | number | No | Accounts payable lead time |
| tax_currency_condition | string | No | Tax/currency profile condition |
| customs_tariff_rate_default | number | No | Default tariff rate for this lane |
| active_flag | boolean | Yes | Whether this lane is active |

#### Mapping notes
Current outbound and inbound tree files mix structure and attributes. In canonical form:
- parent-child topology belongs to `lane_master`
- product defaults belong to `product_master`
- node definitions belong to `node_master`

---

### 5.5 demand_series

This is the normalized monthly demand table.

| field | type | required | description |
|---|---|---:|---|
| scenario_id | string | Yes | Scenario reference |
| product_name | string | Yes | Product name |
| node_name | string | Yes | Demand node |
| period_type | enum | Yes | Current source is `month` |
| period_id | string | Yes | Period identifier such as `2028-09` |
| quantity | number | Yes | Demand quantity |
| quantity_uom | string | Yes | Unit of measure |
| source_tag | string | No | Optional lineage tag |

#### Unit rule
Current `sku_S_month_data.csv` should be treated as `quantity_uom = units` unless explicitly overridden later.

---

### 5.6 supply_series

This is the normalized monthly supply table.

| field | type | required | description |
|---|---|---:|---|
| scenario_id | string | Yes | Scenario reference |
| product_name | string | Yes | Product name |
| node_name | string | Yes | Supply node |
| period_type | enum | Yes | Current source is `month` |
| period_id | string | Yes | Period identifier such as `2028-09` |
| quantity | number | Yes | Supply quantity |
| quantity_uom | string | Yes | Unit of measure |
| source_tag | string | No | Optional lineage tag |

#### Unit rule
Current `sku_P_month_data.csv` should be treated as `quantity_uom = lots` unless explicitly overridden later.

This is critical because current values such as `14`, `42`, `84`, `126`, `140` strongly suggest lot counts rather than unit counts, especially when tree files define `lot_size = 1000`.

---

### 5.7 value_profile

This is the normalized cost/price/profit table.

| field | type | required | description |
|---|---|---:|---|
| scenario_id | string | Yes | Scenario reference |
| direction | enum | Yes | `outbound` or `inbound` |
| product_name | string | Yes | Product name |
| node_name | string | Yes | Node name |
| price_sales_shipped | number | No | Sales price when shipped |
| cost_total | number | No | Total cost |
| profit | number | No | Profit |
| marketing_promotion | number | No | Marketing promotion cost |
| sales_admin_cost | number | No | Sales administration cost |
| sga_total | number | No | SG&A |
| logistics_costs | number | No | Logistics cost |
| warehouse_cost | number | No | Warehouse cost |
| direct_materials_costs | number | No | Direct materials cost |
| tariff_cost | number | No | Tariff cost |
| purchase_total_cost | number | No | Purchase total cost |
| prod_indirect_labor | number | No | Production indirect labor |
| prod_indirect_others | number | No | Production indirect others |
| direct_labor_costs | number | No | Direct labor cost |
| depreciation_others | number | No | Depreciation and others |
| manufacturing_overhead | number | No | Manufacturing overhead |

#### Mapping notes
Current outbound and inbound cost tables map directly into this entity, with `direction` used to keep the two contexts separate.

#### Missing-data policy
If a node exists in the network tree but not in the cost table:
- allow `value_profile` row to be absent
- permit inheritance or fallback in later processing
- log a warning during scenario validation

---

### 5.8 tariff_profile

This is the explicit tariff override table.

| field | type | required | description |
|---|---|---:|---|
| scenario_id | string | Yes | Scenario reference |
| product_name | string | Yes | Product name |
| from_node | string | Yes | Origin node |
| to_node | string | Yes | Destination node |
| tariff_rate | number | Yes | Applied tariff rate |
| precedence | enum | Yes | `override` or `default` |

#### Rule
`tariff_profile` overrides `lane_master.customs_tariff_rate_default` when both are present.

---

### 5.9 price_override_profile

This is the ASIS/TOBE pricing override table.

| field | type | required | description |
|---|---|---:|---|
| scenario_id | string | Yes | Scenario reference |
| product_name | string | Yes | Product name |
| node_name | string | Yes | Node name |
| offering_price_asis | number | No | ASIS offering price |
| offering_price_tobe | number | No | TOBE offering price |

#### Current-state note
The uploaded `offering_price_ASIS_TOBE.csv` currently contains zeros only. This means the table is structurally useful but not yet analytically meaningful. It should remain optional in v0.1.

---

## 6. Mapping from current files to canonical entities

| current file | canonical entity |
|---|---|
| `product_tree_outbound.csv` | `lane_master` + part of `product_master` + part of `node_master` |
| `product_tree_inbound.csv` | `lane_master` + part of `product_master` + part of `node_master` |
| `sku_S_month_data.csv` | `demand_series` |
| `sku_P_month_data.csv` | `supply_series` |
| `sku_cost_table_outbound.csv` | `value_profile` with `direction = outbound` |
| `sku_cost_table_inbound.csv` | `value_profile` with `direction = inbound` |
| `tariff_table.csv` | `tariff_profile` |
| `offering_price_ASIS_TOBE.csv` | `price_override_profile` |
| `node_geo.csv` | `node_master.lat`, `node_master.lon` |

---

## 7. Required supplements not currently present in the uploaded files

The current inputs are already rich, but several items are not explicitly present and must be added in canonical form.

### 7.1 Scenario control fields
The following must be explicitly added:
- `scenario_id`
- `scenario_name`
- `version`
- `as_of_date`
- `planning_scope`
- `source_period_type`
- `planning_period_type`
- `base_currency`

### 7.2 Explicit unit-of-measure fields
The current files do not explicitly declare units. This must be fixed.

Required normalization:
- `demand_series.quantity_uom = units`
- `supply_series.quantity_uom = lots`
- `product_master.units_per_lot = lot_size`

This is one of the most important canonical rules because later inbound planning, cost analysis, auto-generation, and balancing simulation all depend on unit consistency.

### 7.3 Explicit node types
Node type is not explicitly stored in the current files and must either be:
- inferred with a rule
- or added as a proper master table

### 7.4 Opening state and policy objects
The following are not currently represented explicitly:
- opening inventory
- opening backlog
- service policy
- capacity override
- scenario policy switches

These should be treated as future optional canonical extensions. For v0.1 they may default to null or zero.

---

## 8. Normalization rules

### Rule 1: Separate structure from attributes
Tree files must no longer carry mixed responsibilities in the canonical model.
- topology goes to `lane_master`
- product defaults go to `product_master`
- node properties go to `node_master`

### Rule 2: Demand and supply series must be long-form
`year + m1..m12` should be normalized into:
- `period_type`
- `period_id`
- `quantity`

Example:
- `year = 2028`, `m9 = 70000`
- becomes `period_id = 2028-09`, `quantity = 70000`

### Rule 3: Monthly input and weekly planning must both remain explicit
Do not lose the distinction between:
- source monthly inputs
- weekly planning execution

### Rule 4: Inbound and outbound share the same schema
Direction is a property of the lane/scenario, not a separate schema.

### Rule 5: Value-model records may be incomplete
Incomplete value rows should not break canonical ingestion. They should remain visible as incomplete.

---

## 9. Validation checks required for v0.1

Before a scenario is accepted, the following checks should run:

1. every `product_name` in demand/supply exists in `product_master`
2. every `node_name` in demand/supply/value/tariff exists in `node_master`
3. every lane references valid nodes
4. `quantity_uom` is explicitly populated
5. `units_per_lot` is present for all products
6. inbound and outbound directions are valid
7. tariff rows reference valid lane endpoints
8. geo coordinates are optional, but missing geo should be logged if lane auto-generation is expected
9. cost/value missing rows should be logged, not silently ignored

---

## 10. Minimal canonical example

### scenario_header
```yaml
scenario_id: SCN_IPHONE_2028_ASIS
scenario_name: iPhone 2028 ASIS baseline
version: v0.1
as_of_date: 2028-01-01
planning_scope: both
source_period_type: month
planning_period_type: week
base_currency: USD
baseline_scenario_id: null
notes: "baseline canonical scenario"
product_master
- scenario_id: SCN_IPHONE_2028_ASIS
  product_id: IPHONE_NM_2028_BASE
  product_name: IPHONE_NM_2028_BASE
  units_per_lot: 1000
  weeks_year: 52
  hs_code: "8517.13"
  price_elasticity: 0
  cost_standard_flag: 0
node_master
- scenario_id: SCN_IPHONE_2028_ASIS
  node_id: DAD_FAS_AMER
  node_name: DAD_FAS_AMER
  node_type: demand_allocation_hub
  direction_scope: outbound
  lat: null
  lon: null
  psi_graph_flag: ON
  buffering_stock_flag: OFF
lane_master
- scenario_id: SCN_IPHONE_2028_ASIS
  direction: outbound
  product_name: IPHONE_NM_2028_BASE
  parent_node: supply_point
  child_node: DAD_FAS_AMER
  leadtime_weeks: 1
  process_capa_per_bucket: 220000
  ss_days: 7
  lt_boat: 21
  lt_air: 1
  lt_courier: 3
  ar_lead_time: 30
  ap_lead_time: 45
  tax_currency_condition: profile
  customs_tariff_rate_default: 0
  active_flag: true
demand_series
- scenario_id: SCN_IPHONE_2028_ASIS
  product_name: IPHONE_NM_2028_BASE
  node_name: CS_US_PREMIUM
  period_type: month
  period_id: 2028-09
  quantity: 70000
  quantity_uom: units
supply_series
- scenario_id: SCN_IPHONE_2028_ASIS
  product_name: IPHONE_NM_2028_BASE
  node_name: MOM_final_assy_ASIA
  period_type: month
  period_id: 2028-09
  quantity: 140
  quantity_uom: lots
11. What this schema enables next

Once this canonical schema is fixed, WOM can move more safely to:

inbound planning engine and visualization
inbound / outbound comparison standardization
cost / price / profit master stabilization
dataset auto-generation from business cases
demand / supply balancing simulation
future lane-change and tax-aware features

This is why canonical schema definition is the first practical foundation task.

12. Summary

The uploaded inputs already contain enough information to define a strong v0.1 canonical scenario schema.

The main remaining work is not inventing entirely new data, but:

separating mixed concerns
normalizing monthly series
making units explicit
adding scenario control fields
formalizing optional missing values

The most critical decisions in v0.1 are:

outbound and inbound use the same schema
quantity units must be explicit
lots and units must be linked through units_per_lot
tree structure must be separated from product and node attributes
value-model incompleteness must be visible, not hidden
