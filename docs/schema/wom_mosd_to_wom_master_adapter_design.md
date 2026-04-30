# WOM MOSD to WOM Master CSV Adapter Design v0.1

> File: `docs/schema/wom_mosd_to_wom_master_adapter_design.md`  
> Status: Living Design Document v0.1  
> Owner: WOM Project / Yasushi Ohsugi × ChatGPT  
> Purpose: `WOM Master Original Source Data (MOSD)` を、現行WOMの master CSV files へ変換する adapter の設計を定義する。  
> Depends on:
> - `docs/schema/wom_current_master_files_map.md`
> - `docs/schema/wom_master_original_source_data_schema.md`
> Intended implementation:
> - `pysi/modeling/mosd_schema.py`
> - `pysi/modeling/wom_master_adapter.py`
> - `pysi/modeling/wom_master_validator.py`
> - `pysi/modeling/cost_master_validator.py`

---

## 1. Purpose

This document defines the design of the **MOSD to WOM Master CSV Adapter**.

MOSD stands for **WOM Master Original Source Data**.

The adapter transforms an industry case or hypothetical scenario model described in MOSD YAML / JSON into the current WOM master CSV files.

The adapter is the deterministic transformation layer between:

```text
Business / Industry / Scenario Source Data
  ↓
MOSD YAML / JSON
  ↓
MOSD to WOM Master CSV Adapter
  ↓
WOM master CSV files
  ↓
WOM Planning / Costing / Reporting / Management Cockpit
```

The purpose of this adapter is to separate:

```text
AI / consultant modeling work
  from
reproducible WOM master generation
```

The WOM AI Navigator may help generate MOSD, but Python adapter logic must perform deterministic conversion, validation, and reporting.

---

## 2. Design Position

The adapter belongs between MOSD and current WOM execution files.

```text
WOM Navigator / User / Consultant
  ↓ creates
MOSD
  ↓ converted by
MOSD Adapter
  ↓ writes
WOM master CSV files
  ↓ loaded by
WOM Planner / Costing / Reporting
```

The adapter should not directly run the WOM planning engine in v0.1.

Recommended separation:

```text
Adapter:
  transforms MOSD to CSV

Validator:
  checks MOSD and generated CSV consistency

WOM Engine:
  loads CSV and runs planning

Reporting:
  evaluates KPI, cost, profit, issue, cockpit
```

---

## 3. Target Repository Structure

Recommended module structure:

```text
pysi/
  modeling/
    __init__.py
    mosd_schema.py
    mosd_loader.py
    wom_master_adapter.py
    wom_master_validator.py
    cost_master_validator.py
    adapter_report.py

docs/
  schema/
    wom_current_master_files_map.md
    wom_master_original_source_data_schema.md
    wom_mosd_to_wom_master_adapter_design.md

samples/
  mosd/
    home_appliance_sample_v0_1.yaml
    pharma_cold_chain_sample_v0_1.yaml

outputs/
  generated_master_data/
    <model_id>/
      data/
      pysi/
      adapter_report.md
      validation_report.md
```

---

## 4. Input and Output

### 4.1 Input

Adapter input:

```text
MOSD YAML or JSON
```

Example:

```text
samples/mosd/home_appliance_sample_v0_1.yaml
```

### 4.2 Output

Adapter output folder:

```text
outputs/generated_master_data/<model_id>/
```

Recommended structure:

```text
outputs/generated_master_data/<model_id>/
  data/
    node_geo.csv
    product_tree_inbound.csv
    product_tree_outbound.csv
    sku_P_month_data.csv
    sku_S_month_data.csv

    cost_masters/
      product_cost_master.csv
      node_cost_master.csv
      lane_cost_master.csv
      sales_price_master.csv
      sga_marketing_tax_master.csv
      fixed_asset_cost_master.csv
      allocation_rule_master.csv
      market_master.csv
      cs_node_to_market_map.csv
      fx_rate_master.csv

  pysi/
    master_data/
      node_master.csv
      node_character_money_master.csv
      node_product_money_master.csv

  adapter_report.md
  validation_report.md
  source_assumption_register.csv
```

---

## 5. Adapter Scope v0.1

### 5.1 In Scope

v0.1 should support:

1. Load MOSD YAML / JSON.
2. Validate minimum MOSD schema.
3. Generate physical world masters.
4. Generate product-specific INBOUND / OUTBOUND tree masters.
5. Generate P / S monthly quantity masters.
6. Generate semantic node master.
7. Generate market master and CS node to market map.
8. Generate extended costing masters.
9. Generate FX master if currency data exists.
10. Generate source assumption register.
11. Generate adapter and validation reports.

### 5.2 Out of Scope

v0.1 does not need to:

1. Run the WOM planning engine.
2. Open WOM GUI.
3. Optimize scenario selection.
4. Automatically search public web data.
5. Guarantee business decision validity.
6. Replace human review.
7. Generate all possible legacy money masters if extended costing masters are available.

---

## 6. Core Transformation Policy

### 6.1 MOSD is the source

MOSD is the upstream source.  
WOM CSV files are generated outputs.

### 6.2 Preserve assumptions

Every value in MOSD that has `source_type`, `confidence`, or `human_review_required` should be included in an assumption register.

Recommended output:

```text
source_assumption_register.csv
```

Columns:

```text
section
object_key
field_name
value
source_type
confidence
human_review_required
assumption_note
source_ref
```

### 6.3 Do not silently invent values

If required WOM CSV fields are missing in MOSD, the adapter should use one of the following:

```text
system_default
derived_value
placeholder_required
error
```

The adapter report must clearly state which fields were defaulted, derived, or left as placeholders.

---

## 7. Transformation Flow

Recommended flow:

```text
1. load_mosd()
2. validate_mosd_minimum()
3. normalize_mosd()
4. generate_node_master()
5. generate_node_geo()
6. generate_product_tree_inbound()
7. generate_product_tree_outbound()
8. generate_sku_P_month_data()
9. generate_sku_S_month_data()
10. generate_market_master()
11. generate_cs_node_to_market_map()
12. generate_product_cost_master()
13. generate_node_cost_master()
14. generate_lane_cost_master()
15. generate_sales_price_master()
16. generate_sga_marketing_tax_master()
17. generate_fixed_asset_cost_master()
18. generate_allocation_rule_master()
19. generate_fx_rate_master()
20. generate_node_product_money_master()
21. generate_source_assumption_register()
22. run_generated_csv_validation()
23. write_adapter_report()
```

---

## 8. Data Mapping Summary

| MOSD section | WOM output |
|---|---|
| `products` | Product fields in tree / quantity / cost masters |
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

## 9. Output File Design

### 9.1 `pysi/master_data/node_master.csv`

Generated from:

```text
MOSD.physical_nodes
```

Recommended output columns:

```text
node_name
node_character
display_name
country
company
remarks
```

Rules:

- `node_name` must be unique.
- `supply_point` must exist once.
- `MOM_` and `DAD_` prefixes are reserved.
- `PAD` should not be generated as standard node_character unless explicitly requested.

---

### 9.2 `data/node_geo.csv`

Generated from:

```text
MOSD.physical_nodes
```

Recommended output columns:

```text
node_name
lat
lon
```

Rules:

- If lat/lon are missing, keep blank or null.
- Missing lat/lon should be warning, not error.
- `node_name` should exist in generated `node_master.csv`.

---

### 9.3 `data/product_tree_inbound.csv`

Generated from:

```text
MOSD.product_plan_edges where bound = IN
```

Recommended output columns should follow current WOM sample format:

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

Mapping rules:

```text
Product_name       ← product_name
Parent_node        ← parent_node
Child_node         ← child_node
child_node_name    ← child_node or display_name
lot_size           ← lot_size or product.lot_size
leadtime           ← leadtime_days
process_capa       ← process_capa
SS_days            ← ss_days
PSI_graph_flag     ← psi_graph_flag
buffering_stock_flag ← buffering_stock_flag
```

Missing optional fields may use defaults.

---

### 9.4 `data/product_tree_outbound.csv`

Generated from:

```text
MOSD.product_plan_edges where bound = OUT
```

Same column policy as inbound tree.

Rules:

- OUTBOUND tree should connect from `supply_point` toward market-facing nodes.
- OUTBOUND leaf nodes should be mappable to `market_id` if market reporting is required.

---

### 9.5 `data/sku_P_month_data.csv`

Generated from:

```text
MOSD.quantity_profiles where bucket = P
```

Current WOM output format:

```text
product_name,node_name,year,m1,m2,m3,m4,m5,m6,m7,m8,m9,m10,m11,m12
```

Transformation:

```text
Long MOSD monthly records
  → group by product_name, node_name, year
  → pivot month to m1...m12
```

Default:

```text
missing month quantity = 0
```

---

### 9.6 `data/sku_S_month_data.csv`

Generated from:

```text
MOSD.quantity_profiles where bucket = S
```

Same wide monthly format as P file.

---

### 9.7 `data/cost_masters/market_master.csv`

Generated from:

```text
MOSD.markets
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
- `market_id` must be unique.

---

### 9.8 `data/cost_masters/cs_node_to_market_map.csv`

Generated from:

```text
MOSD.node_market_mapping
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

- `node_name` should exist in OUTBOUND tree.
- `market_id` should exist in market master.
- `allocation_ratio > 0`.
- For the same scenario/product/node/week, allocation ratio should generally sum to 1.0.

---

### 9.9 `data/cost_masters/product_cost_master.csv`

Generated from:

```text
MOSD.cost_assumptions.product_costs
```

Recommended columns:

```text
product_name
product_family
base_sales_price
standard_material_cost
standard_production_cost
purchase_cost
inventory_unit_value
currency
scenario_name
remarks
```

---

### 9.10 `data/cost_masters/node_cost_master.csv`

Generated from:

```text
MOSD.cost_assumptions.node_costs
```

Recommended columns:

```text
node_name
node_character
direct_labor_cost_rate
machine_cost_rate
utility_cost_rate
inventory_holding_cost_rate
local_sga_fixed_cost
local_sga_variable_cost_rate
depreciation_cost_per_period
capacity_cost_basis
currency
scenario_name
remarks
```

---

### 9.11 `data/cost_masters/lane_cost_master.csv`

Generated from:

```text
MOSD.cost_assumptions.lane_costs
```

Recommended columns:

```text
from_node
to_node
transport_mode
freight_cost_per_unit
insurance_cost_per_unit
tariff_rate
customs_cost_per_unit
lead_time_days
special_risk_cost_rate
currency
scenario_name
valid_from_week
valid_to_week
remarks
```

---

### 9.12 `data/cost_masters/sales_price_master.csv`

Generated from:

```text
MOSD.cost_assumptions.sales_prices
```

Recommended columns:

```text
product_name
market_id
customer_segment
sales_price
rebate_rate
promotion_cost_rate
gross_to_net_adjustment
expected_return_rate
currency
scenario_name
valid_from_week
valid_to_week
remarks
```

---

### 9.13 `data/cost_masters/sga_marketing_tax_master.csv`

Generated from:

```text
MOSD.cost_assumptions.sga_marketing_tax
```

Recommended columns:

```text
scope_type
scope_id
product_family
sga_fixed_cost
sga_variable_rate
marketing_fixed_cost
marketing_variable_rate
tax_rate
currency
scenario_name
valid_from_week
valid_to_week
remarks
```

---

### 9.14 `data/cost_masters/fixed_asset_cost_master.csv`

Generated from:

```text
MOSD.cost_assumptions.fixed_assets
```

Recommended columns:

```text
asset_id
node_name
asset_type
investment_amount
depreciation_method
depreciation_periods
period_cost
maintenance_cost_per_period
currency
valid_from_week
valid_to_week
remarks
```

---

### 9.15 `data/cost_masters/allocation_rule_master.csv`

Generated from:

```text
MOSD.cost_assumptions.allocation_rules
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

---

### 9.16 `data/cost_masters/fx_rate_master.csv`

Generated from:

```text
MOSD.currencies.fx_rates
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

Rules:

- `from_currency != to_currency`
- `fx_rate > 0`
- no overlapping period for same scenario/from/to
- inverse rate is not assumed unless explicitly allowed

---

### 9.17 `pysi/master_data/node_product_money_master.csv`

Generated from either:

```text
MOSD.cost_assumptions.node_costs
MOSD.cost_assumptions.product_costs
MOSD.cost_assumptions.sales_prices
```

or from derived lightweight valuation rules.

Recommended output columns:

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

Purpose:

- lightweight valuation table
- semantic overlay for 2 phase costing
- Management Cockpit quick display

Rules:

- Do not treat this as a full replacement for extended costing master.
- This may be generated as fallback or summary from extended costing masters.

---

## 10. Normalization Rules

### 10.1 Node normalization

Rules:

```text
trim whitespace
preserve case unless policy says otherwise
replace spaces with underscore when generating node_name
ensure node_name uniqueness
reserve supply_point
respect MOM_ and DAD_ prefixes
```

### 10.2 Product normalization

Rules:

```text
product_name should be stable and human-readable
avoid spaces
prefer uppercase with underscores
lot_size must be positive
```

### 10.3 Market normalization

Rules:

```text
market_id should be stable and human-readable
market_id is not country
country is an attribute
prefer prefix MKT_
```

Example:

```text
MKT_US_PREMIUM
MKT_JP_APPLE_DIRECT
MKT_CN_ONLINE_MAINSTREAM
```

---

## 11. Default Values

The adapter may use defaults only when the rule is explicit.

Recommended defaults:

| field | default | condition |
|---|---|---|
| `scenario_name` | `BAU` | when not provided |
| `active_flag` | `TRUE` | when not provided |
| `weeks_year` | `52` | when not provided |
| `lot_size` | product.lot_size | when edge lot_size missing |
| monthly quantity | `0` | when missing month |
| `target_scope_id` | error | do not default blank to ALL silently |
| currency | error | unless reporting_currency policy explicitly allows default |

Important:

```text
The adapter should not silently default business-critical values.
```

---

## 12. Validation Design

Validation should occur in two stages.

### 12.1 MOSD validation

Before generating CSV:

```text
schema_version is supported
model_id exists
products are unique
physical_nodes are unique
supply_point exists once
product_plan_edges reference valid nodes and products
quantity_profiles reference valid nodes and products
markets are unique
node_market_mapping references valid nodes and markets
cost assumptions reference valid products, nodes, lanes, markets
currencies are valid
source_type and confidence are present for assumption-heavy values
```

### 12.2 Generated CSV validation

After generating CSV:

```text
all required files exist
all required columns exist
node_name references resolve
product references resolve
market references resolve
currency conversion path exists
allocation target_scope_id is not blank
supply_point appears once in node_master
INBOUND and OUTBOUND connect through supply_point
MOM / DAD reserved prefix rules are not violated
```

---

## 13. Error / Warning Policy

Adapter should classify findings into:

```text
ERROR
WARNING
INFO
```

### 13.1 ERROR

Examples:

```text
missing schema_version
duplicate node_name
missing supply_point
product_plan_edge references unknown node
invalid lot_size <= 0
invalid fx_rate <= 0
blank allocation target_scope_id
```

### 13.2 WARNING

Examples:

```text
missing lat/lon
missing optional cost assumption
node_name does not follow recommended prefix
market exists but no sales price
currency exists but no FX scenario variation
source_type = navigator_assumption
confidence = low
```

### 13.3 INFO

Examples:

```text
default scenario_name BAU applied
missing monthly quantity filled with 0
node_product_money_master derived from extended costing master
```

---

## 14. Adapter Report

The adapter should generate:

```text
adapter_report.md
```

Recommended sections:

```text
1. Model summary
2. Input MOSD file
3. Generated output files
4. Transformation summary
5. Defaults applied
6. Derived values
7. Assumption register summary
8. Validation result summary
9. Human review required items
10. Next recommended action
```

---

## 15. Source Assumption Register

The adapter should generate:

```text
source_assumption_register.csv
```

Purpose:

- make assumptions visible
- distinguish user-provided data from AI-generated placeholders
- support human review
- prevent hidden assumptions from entering management decisions

Recommended columns:

```text
section
object_key
field_name
value
source_type
source_ref
confidence
human_review_required
assumption_note
```

---

## 16. Human Review Gate

Before generated WOM masters are used for actual business decision-making, the following must be reviewed:

```text
demand assumptions
capacity assumptions
lead time assumptions
cost assumptions
price assumptions
FX assumptions
market mapping
allocation rules
scenario changes
all low-confidence values
all navigator assumptions
all placeholders
```

The adapter should mark:

```text
human_review_required = true
```

at model level when any important input is not user confirmed.

---

## 17. Proposed Python API

### 17.1 `mosd_loader.py`

```python
def load_mosd(path: str) -> dict:
    \"\"\"Load MOSD YAML or JSON and return dict.\"\"\"
```

### 17.2 `mosd_schema.py`

```python
def validate_mosd_schema(mosd: dict) -> list:
    \"\"\"Return validation messages for MOSD schema.\"\"\"
```

### 17.3 `wom_master_adapter.py`

```python
def generate_wom_masters(
    mosd_path: str,
    output_dir: str,
    *,
    overwrite: bool = False,
) -> dict:
    \"\"\"Generate WOM master CSV files from MOSD.\"\"\"
```

Returned result:

```python
{
    "model_id": "...",
    "output_dir": "...",
    "generated_files": [...],
    "errors": [...],
    "warnings": [...],
    "human_review_required": True,
}
```

### 17.4 `wom_master_validator.py`

```python
def validate_generated_masters(output_dir: str) -> dict:
    \"\"\"Validate generated WOM master CSV files.\"\"\"
```

### 17.5 CLI entry point

Recommended CLI:

```bash
python -m pysi.modeling.wom_master_adapter \
  --mosd samples/mosd/home_appliance_sample_v0_1.yaml \
  --output outputs/generated_master_data/home_appliance_sample_001 \
  --overwrite
```

---

## 18. Implementation Phases

### Phase 1: Minimal adapter

Generate:

```text
node_geo.csv
node_master.csv
product_tree_inbound.csv
product_tree_outbound.csv
sku_P_month_data.csv
sku_S_month_data.csv
adapter_report.md
```

### Phase 2: Market and costing adapter

Add:

```text
market_master.csv
cs_node_to_market_map.csv
product_cost_master.csv
node_cost_master.csv
lane_cost_master.csv
sales_price_master.csv
```

### Phase 3: Full reporting adapter

Add:

```text
sga_marketing_tax_master.csv
fixed_asset_cost_master.csv
allocation_rule_master.csv
fx_rate_master.csv
node_product_money_master.csv
source_assumption_register.csv
validation_report.md
```

### Phase 4: WOM execution integration

Connect generated master folder to existing WOM loading process.

---

## 19. Test Strategy

Recommended test samples:

```text
samples/mosd/home_appliance_sample_v0_1.yaml
samples/mosd/pharma_cold_chain_sample_v0_1.yaml
```

Recommended tests:

```text
test_load_mosd
test_validate_minimal_mosd
test_generate_node_master
test_generate_product_tree
test_generate_quantity_profiles
test_generate_market_mapping
test_generate_cost_masters
test_validate_generated_masters
```

Recommended test location:

```text
tests/modeling/
  test_mosd_adapter.py
```

---

## 20. Codex Implementation Prompt Draft

Use the following prompt when asking Codex to implement the first skeleton.

```text
Implement a minimal MOSD to WOM Master CSV adapter.

Context:
- Read docs/schema/wom_current_master_files_map.md
- Read docs/schema/wom_master_original_source_data_schema.md
- Read docs/schema/wom_mosd_to_wom_master_adapter_design.md

Create:
- pysi/modeling/__init__.py
- pysi/modeling/mosd_loader.py
- pysi/modeling/mosd_schema.py
- pysi/modeling/wom_master_adapter.py
- pysi/modeling/wom_master_validator.py

Phase 1 scope:
- Load MOSD YAML or JSON
- Validate minimal fields
- Generate:
  - data/node_geo.csv
  - pysi/master_data/node_master.csv
  - data/product_tree_inbound.csv
  - data/product_tree_outbound.csv
  - data/sku_P_month_data.csv
  - data/sku_S_month_data.csv
  - adapter_report.md
- Add a CLI:
  python -m pysi.modeling.wom_master_adapter --mosd <path> --output <dir> --overwrite

Do not modify existing WOM planner behavior.
Do not remove legacy master files.
Use node_name as canonical key.
Respect supply_point, MOM_, DAD_ rules.
```

---

## 21. Open Issues

### 21.1 Exact current loader compatibility

Current WOM loader may expect exact columns and order.  
Adapter implementation should verify current loader behavior before replacing sample master folders.

### 21.2 Product master

MOSD has `products`, but current WOM does not yet have a single product master.  
The adapter should use MOSD products as source for product references.

### 21.3 Weekly vs monthly input

Phase 1 supports monthly wide CSV because current sample master uses `m1...m12`.  
Future adapter may support weekly direct input.

### 21.4 Legacy money master generation

Phase 1 does not generate legacy `sku_cost_table_*`.  
A compatibility generator may be added later if needed.

### 21.5 Source search automation

The adapter should not search external sources.  
Information collection is Navigator / user / consultant responsibility.  
The adapter transforms confirmed or marked MOSD.

---

## 22. Next Step

Recommended next step:

```text
Create Phase 1 adapter skeleton:
pysi/modeling/mosd_loader.py
pysi/modeling/mosd_schema.py
pysi/modeling/wom_master_adapter.py
pysi/modeling/wom_master_validator.py
```

Recommended sample:

```text
samples/mosd/home_appliance_sample_v0_1.yaml
```
