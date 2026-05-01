# WOM MOSD Phase 2 Money Adapter Design v0.1

> File: `docs/schema/wom_mosd_phase2_money_adapter_design.md`  
> Status: Living Design Document v0.1  
> Owner: WOM Project / Yasushi Ohsugi × ChatGPT  
> Purpose: MOSD Phase 1で生成したWOM数量編master skeletonに対して、金額編・市場編・軽量costing masterを追加生成するためのPhase 2 adapter設計を定義する。  
> Depends on:
> - `docs/schema/wom_current_master_files_map.md`
> - `docs/schema/wom_master_original_source_data_schema.md`
> - `docs/schema/wom_mosd_to_wom_master_adapter_design.md`
> - `docs/notes/mosd_phase1_smoke_test_260501.md`
> Intended implementation:
> - Extend `pysi/modeling/wom_master_adapter.py`
> - Extend `pysi/modeling/wom_master_validator.py`
> - Optionally add `pysi/modeling/money_master_adapter.py`
> - Optionally add `pysi/modeling/money_master_validator.py`

---

## 1. Purpose

This document defines **Phase 2** of the MOSD to WOM Master CSV adapter.

Phase 1 proved that MOSD can generate the WOM quantity-side master skeleton:

```text
MOSD
  ↓
node_geo.csv
product_tree_inbound.csv
product_tree_outbound.csv
sku_P_month_data.csv
sku_S_month_data.csv
node_master.csv
  ↓
WOM GUI / Network / World Map / PSI Graph
```

Phase 2 adds money and market meaning to the generated model.

In simple terms:

```text
Phase 1:
  Put the box on WOM's conveyor belt.

Phase 2:
  Attach market labels, price tags, cost tags, and inventory value tags to the box.
```

The practical goal of Phase 2 is:

```text
Generated WOM model should not show all money KPIs as zero.
```

---

## 2. Phase 2 Scope

Phase 2 extends MOSD adapter output from quantity-only master generation to:

1. market master generation
2. CS node to market mapping
3. lightweight node-product money valuation
4. basic product / node / lane / sales price costing masters
5. FX master generation
6. validator extension for money-side consistency
7. adapter report extension for money assumptions

---

## 3. Phase 2A / Phase 2B Split

Phase 2 should be implemented in two steps.

### 3.1 Phase 2A: Minimal Money Overlay

Phase 2A should generate the minimum masters needed to make generated WOM models display non-zero money values where the existing WOM money evaluation path can use them.

Primary target:

```text
pysi/master_data/node_product_money_master.csv
```

Supporting targets:

```text
pysi/master_data/node_character_money_master.csv
data/cost_masters/market_master.csv
data/cost_masters/cs_node_to_market_map.csv
```

Phase 2A success criterion:

```text
For SMART_WASHER_2028_BASE, generated nodes can have:
- inventory_unit_value
- revenue_unit_value
- variable_cost_unit_value
- fixed_cost_weekly
```

Even if values are placeholder assumptions, they must be explicit and traceable.

### 3.2 Phase 2B: Extended Costing Masters

Phase 2B should generate normalized cost masters for Business Reporting and future Management Cockpit integration.

Targets:

```text
data/cost_masters/product_cost_master.csv
data/cost_masters/node_cost_master.csv
data/cost_masters/lane_cost_master.csv
data/cost_masters/sales_price_master.csv
data/cost_masters/sga_marketing_tax_master.csv
data/cost_masters/fixed_asset_cost_master.csv
data/cost_masters/allocation_rule_master.csv
data/cost_masters/fx_rate_master.csv
```

Phase 2B success criterion:

```text
MOSD can generate a coherent lightweight costing dataset
suitable for future Cost Waterfall / Market P/L / Management Cockpit reporting.
```

---

## 4. Phase 2 Design Principles

### 4.1 Do not overwrite existing production masters by default

Generated masters should continue to be written under:

```text
outputs/generated_master_data/<model_id>/
```

Do not directly overwrite:

```text
data/
pysi/master_data/
```

unless explicitly copied by the user or a future execution option is implemented.

### 4.2 Keep generated assumptions visible

All placeholder money values must be traceable.

Recommended metadata:

```text
source_type
confidence
human_review_required
remarks
```

### 4.3 Support dummy values intentionally

Phase 2A may use placeholder values for smoke testing.

However, placeholder values must be marked clearly.

Example:

```text
remarks = generated placeholder; human review required
```

### 4.4 Do not treat node_master.csv as money value master

`node_master.csv` defines semantic identity of nodes.

It does not define:

```text
revenue value
inventory value
variable cost
fixed cost
currency
```

Those values belong primarily to:

```text
node_product_money_master.csv
cost_masters/*.csv
```

### 4.5 Legacy money masters remain fallback

The following legacy files may still be referenced by existing WOM paths:

```text
data/offering_price_ASIS_TOBE.csv
data/sku_cost_table_inbound.csv
data/sku_cost_table_outbound.csv
data/tariff_table.csv
```

Phase 2 does not need to replace them immediately.  
Phase 2 should first generate semantic and extended money masters in generated output folders.

---

## 5. MOSD Sections Required for Phase 2

Phase 2 uses or extends these MOSD sections:

```yaml
markets: []
node_market_mapping: []
cost_assumptions:
  product_costs: []
  node_costs: []
  lane_costs: []
  sales_prices: []
  sga_marketing_tax: []
  fixed_assets: []
  allocation_rules: []
currencies:
  reporting_currency: USD
  fx_rates: []
```

Additionally, Phase 2A may introduce a convenience section:

```yaml
money_overlay:
  node_product_values: []
  node_character_rules: []
```

This section is optional.  
If it is absent, the adapter may derive `node_product_money_master.csv` from cost assumptions.

---

## 6. Phase 2A MOSD Extension: money_overlay

### 6.1 Purpose

`money_overlay` provides a lightweight way to define money values directly for each node-product combination.

This is useful for:

1. smoke testing
2. demo scenarios
3. Management Cockpit quick display
4. cases where full costing masters are not ready

### 6.2 Schema

```yaml
money_overlay:
  node_product_values:
    - node_name: supply_point
      product_name: SMART_WASHER_2028_BASE
      inventory_unit_value: 500
      revenue_unit_value: 0
      variable_cost_unit_value: 0
      fixed_cost_weekly: 0
      currency: USD
      scenario_name: BAU
      source_type: navigator_assumption
      confidence: low
      remarks: generated placeholder

    - node_name: MOM_JP_WASHER_PLANT
      product_name: SMART_WASHER_2028_BASE
      inventory_unit_value: 450
      revenue_unit_value: 0
      variable_cost_unit_value: 350
      fixed_cost_weekly: 10000
      currency: USD
      scenario_name: BAU
      source_type: navigator_assumption
      confidence: low
      remarks: generated placeholder

    - node_name: DAD_US_CENTRAL_DC
      product_name: SMART_WASHER_2028_BASE
      inventory_unit_value: 520
      revenue_unit_value: 0
      variable_cost_unit_value: 30
      fixed_cost_weekly: 5000
      currency: USD
      scenario_name: BAU
      source_type: navigator_assumption
      confidence: low
      remarks: generated placeholder

    - node_name: CS_US_ECOM
      product_name: SMART_WASHER_2028_BASE
      inventory_unit_value: 0
      revenue_unit_value: 800
      variable_cost_unit_value: 0
      fixed_cost_weekly: 0
      currency: USD
      scenario_name: BAU
      source_type: navigator_assumption
      confidence: low
      remarks: generated placeholder
```

### 6.3 Mapping Target

```text
pysi/master_data/node_product_money_master.csv
```

### 6.4 Output Columns

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

Optional future columns:

```text
scenario_name
source_type
confidence
valid_from_week
valid_to_week
```

For Phase 2A, keep compatibility with current loader first.

---

## 7. node_character_money_master Generation

### 7.1 Purpose

`node_character_money_master.csv` defines how node characters are interpreted in money evaluation.

### 7.2 Recommended Default Rows

Phase 2A should generate a minimal default table if MOSD does not provide one.

```csv
node_character,revenue_items,variable_cost_items,fixed_cost_items,inventory_value_items,tax_compare_items
SUPPLY_CHAIN_OFFICE,,,fixed_cost_weekly,inventory_unit_value,
MOM,,variable_cost_unit_value,fixed_cost_weekly,inventory_unit_value,
DAD,,variable_cost_unit_value,fixed_cost_weekly,inventory_unit_value,
CS,revenue_unit_value,,,,
```

Additional characters may be included:

```text
WS
RT
SUPPLIER
MARKET
CONSUMER
```

### 7.3 Mapping Target

```text
pysi/master_data/node_character_money_master.csv
```

### 7.4 Rule

If existing `node_character_money_master.csv` is more complete, Phase 2A should be able to copy or preserve the existing one.

Implementation options:

```text
Option A:
  Always generate a minimal default table.

Option B:
  If MOSD provides node_character_rules, generate from MOSD.
  Otherwise, copy current repository default if available.
  Otherwise, generate minimal default.

Recommended for Phase 2A:
  Option B
```

---

## 8. Market Master Generation

### 8.1 Purpose

`market_master.csv` defines market management units.

Market is not country.

```text
market_id = terminal market / channel / segment / service-policy / price-policy unit
country   = attribute of market_id
```

### 8.2 MOSD Schema

```yaml
markets:
  - market_id: MKT_US_ECOM
    market_name: US E-commerce Home Appliance Market
    country: US
    region: NA
    channel: ECOM
    segment: MAINSTREAM
    priority_class: A
    service_policy: NORMAL_SERVICE
    price_policy: BASE_PRICE
    currency: USD
    active_flag: true
    source_type: navigator_assumption
    confidence: low
```

### 8.3 Mapping Target

```text
data/cost_masters/market_master.csv
```

### 8.4 Output Columns

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

---

## 9. CS Node to Market Map Generation

### 9.1 Purpose

`cs_node_to_market_map.csv` connects WOM OUTBOUND leaf nodes to market units.

```text
WOM OUTBOUND leaf node
  ↓
cs_node_to_market_map
  ↓
market_id
  ↓
market_master
```

### 9.2 MOSD Schema

```yaml
node_market_mapping:
  - node_name: CS_US_ECOM
    market_id: MKT_US_ECOM
    product_name: SMART_WASHER_2028_BASE
    allocation_ratio: 1.0
    priority_class: A
    service_policy: NORMAL_SERVICE
    price_policy: BASE_PRICE
    valid_from_week: 1
    valid_to_week: 52
    scenario_name: BAU
    active_flag: true
    source_type: navigator_assumption
    confidence: low
```

### 9.3 Mapping Target

```text
data/cost_masters/cs_node_to_market_map.csv
```

### 9.4 Output Columns

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

### 9.5 Validation Rules

```text
node_name exists in generated OUTBOUND product tree.
market_id exists in market_master.
product_name exists in products.
allocation_ratio > 0.
For same scenario/product/node/week, allocation_ratio should generally sum to 1.0.
```

---

## 10. Product Cost Master Generation

### 10.1 MOSD Schema

```yaml
cost_assumptions:
  product_costs:
    - product_name: SMART_WASHER_2028_BASE
      product_family: WASHER
      base_sales_price: 800
      standard_material_cost: 300
      standard_production_cost: 120
      purchase_cost: 0
      inventory_unit_value: 420
      currency: USD
      scenario_name: BAU
      source_type: navigator_assumption
      confidence: low
      remarks: generated placeholder
```

### 10.2 Mapping Target

```text
data/cost_masters/product_cost_master.csv
```

### 10.3 Output Columns

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

## 11. Node Cost Master Generation

### 11.1 MOSD Schema

```yaml
cost_assumptions:
  node_costs:
    - node_name: MOM_JP_WASHER_PLANT
      node_character: MOM
      direct_labor_cost_rate: 20
      machine_cost_rate: 30
      utility_cost_rate: 5
      inventory_holding_cost_rate: 0.01
      local_sga_fixed_cost: 10000
      local_sga_variable_cost_rate: 0.02
      depreciation_cost_per_period: 5000
      capacity_cost_basis: capacity_qty
      currency: USD
      scenario_name: BAU
      source_type: navigator_assumption
      confidence: low
      remarks: generated placeholder
```

### 11.2 Mapping Target

```text
data/cost_masters/node_cost_master.csv
```

### 11.3 Output Columns

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

## 12. Lane Cost Master Generation

### 12.1 MOSD Schema

```yaml
cost_assumptions:
  lane_costs:
    - from_node: supply_point
      to_node: DAD_US_CENTRAL_DC
      transport_mode: ocean
      freight_cost_per_unit: 40
      insurance_cost_per_unit: 3
      tariff_rate: 0.05
      customs_cost_per_unit: 5
      lead_time_days: 21
      special_risk_cost_rate: 0.02
      currency: USD
      scenario_name: BAU
      valid_from_week: 1
      valid_to_week: 52
      source_type: navigator_assumption
      confidence: low
      remarks: generated placeholder
```

### 12.2 Mapping Target

```text
data/cost_masters/lane_cost_master.csv
```

### 12.3 Output Columns

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

## 13. Sales Price Master Generation

### 13.1 MOSD Schema

```yaml
cost_assumptions:
  sales_prices:
    - product_name: SMART_WASHER_2028_BASE
      market_id: MKT_US_ECOM
      customer_segment: MAINSTREAM
      sales_price: 800
      rebate_rate: 0.02
      promotion_cost_rate: 0.03
      gross_to_net_adjustment: 0.01
      expected_return_rate: 0.01
      currency: USD
      scenario_name: BAU
      valid_from_week: 1
      valid_to_week: 52
      source_type: navigator_assumption
      confidence: low
      remarks: generated placeholder
```

### 13.2 Mapping Target

```text
data/cost_masters/sales_price_master.csv
```

### 13.3 Output Columns

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

## 14. FX Rate Master Generation

### 14.1 MOSD Schema

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
      source_type: navigator_assumption
      confidence: low
      remarks: generated placeholder
```

### 14.2 Mapping Target

```text
data/cost_masters/fx_rate_master.csv
```

### 14.3 Output Columns

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

### 14.4 Validation Rules

```text
from_currency != to_currency
fx_rate > 0
valid_from_week <= valid_to_week
do not assume inverse FX rates unless explicitly enabled
```

---

## 15. Adapter Output Structure

Phase 2 should continue using the generated output folder.

```text
outputs/generated_master_data/<model_id>/
  data/
    node_geo.csv
    product_tree_inbound.csv
    product_tree_outbound.csv
    sku_P_month_data.csv
    sku_S_month_data.csv

    cost_masters/
      market_master.csv
      cs_node_to_market_map.csv
      product_cost_master.csv
      node_cost_master.csv
      lane_cost_master.csv
      sales_price_master.csv
      fx_rate_master.csv
      sga_marketing_tax_master.csv       # Phase 2B optional
      fixed_asset_cost_master.csv        # Phase 2B optional
      allocation_rule_master.csv         # Phase 2B optional

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

## 16. Adapter Behavior Extension

Phase 2 should extend `generate_wom_masters()` or introduce a mode.

### 16.1 Recommended Option

Keep one entrypoint:

```python
generate_wom_masters(
    mosd_path: str,
    output_dir: str,
    *,
    overwrite: bool = False,
    include_money: bool = False,
) -> dict:
    ...
```

CLI:

```bash
python -m pysi.modeling.wom_master_adapter ^
  --mosd samples/mosd/home_appliance_sample_v0_1.json ^
  --output outputs/generated_master_data/home_appliance_sample_001 ^
  --overwrite ^
  --include-money
```

### 16.2 Alternative Option

Always generate money masters when MOSD contains money sections.

```text
If money sections exist:
  generate money masters
Else:
  generate quantity only
```

Recommended for Phase 2A:

```text
Use --include-money flag first.
```

This makes the behavior explicit and reduces accidental changes.

---

## 17. Derivation Rules for node_product_money_master.csv

Phase 2A should support two ways to generate node-product values.

### 17.1 Direct Mode

Use:

```yaml
money_overlay.node_product_values
```

directly.

This is preferred for smoke testing.

### 17.2 Derived Mode

If direct values are absent, derive approximate values from:

```text
product_costs
node_costs
sales_prices
node_character
```

Recommended simple derivation:

```text
For MOM:
  inventory_unit_value = product.standard_material_cost + product.standard_production_cost
  variable_cost_unit_value = product.standard_material_cost + product.standard_production_cost
  revenue_unit_value = 0

For DAD:
  inventory_unit_value = product.inventory_unit_value or product base cost
  variable_cost_unit_value = lane freight or node handling placeholder
  revenue_unit_value = 0

For CS:
  revenue_unit_value = sales_price for mapped market
  inventory_unit_value = 0
  variable_cost_unit_value = 0

For supply_point:
  inventory_unit_value = product.inventory_unit_value
  revenue_unit_value = 0
  variable_cost_unit_value = 0
```

All derived values must be marked in remarks.

---

## 18. Validation Design

### 18.1 Phase 2A Validation

```text
node_product_money_master:
  node_name exists in node_master
  product_name exists in products
  numeric fields are >= 0
  currency exists
  at least one row per product-node pair where money evaluation is expected

node_character_money_master:
  all node_character in node_master exists in node_character_money_master
```

### 18.2 Market Validation

```text
market_master.market_id is unique
cs_node_to_market_map.market_id exists in market_master
cs_node_to_market_map.node_name exists in OUTBOUND product tree
cs_node_to_market_map.product_name exists in products
allocation_ratio > 0
target_scope_id blank is not allowed in allocation rules
```

### 18.3 Cost Master Validation

```text
product_cost_master.product_name exists in products
node_cost_master.node_name exists in node_master
lane_cost_master.from_node/to_node exist in node_master
sales_price_master.market_id exists in market_master
sales_price_master.product_name exists in products
fx_rate_master.fx_rate > 0
```

---

## 19. Adapter Report Extension

`adapter_report.md` should add a Phase 2 section.

Recommended sections:

```text
## Money Master Generation

Generated:
- node_character_money_master.csv
- node_product_money_master.csv
- market_master.csv
- cs_node_to_market_map.csv
- product_cost_master.csv
- node_cost_master.csv
- lane_cost_master.csv
- sales_price_master.csv
- fx_rate_master.csv

## Placeholder Money Values

List all rows where:
- source_type = navigator_assumption
- confidence = low
- remarks contains placeholder

## Human Review Required

List money-sensitive values:
- price
- cost
- inventory value
- FX
- market mapping
- allocation ratio
```

---

## 20. source_assumption_register.csv Extension

Phase 2 should generate or extend:

```text
source_assumption_register.csv
```

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

Money fields should always be included when source_type is not `user_provided`.

---

## 21. Phase 2A Acceptance Criteria

After implementation, this command should work:

```bat
python -m pysi.modeling.wom_master_adapter ^
  --mosd samples/mosd/home_appliance_sample_v0_1.json ^
  --output outputs/generated_master_data/home_appliance_sample_001 ^
  --overwrite ^
  --include-money
```

Expected generated files include Phase 1 files plus:

```text
outputs/generated_master_data/home_appliance_sample_001/pysi/master_data/node_character_money_master.csv
outputs/generated_master_data/home_appliance_sample_001/pysi/master_data/node_product_money_master.csv
outputs/generated_master_data/home_appliance_sample_001/data/cost_masters/market_master.csv
outputs/generated_master_data/home_appliance_sample_001/data/cost_masters/cs_node_to_market_map.csv
outputs/generated_master_data/home_appliance_sample_001/data/cost_masters/product_cost_master.csv
outputs/generated_master_data/home_appliance_sample_001/data/cost_masters/node_cost_master.csv
outputs/generated_master_data/home_appliance_sample_001/data/cost_masters/lane_cost_master.csv
outputs/generated_master_data/home_appliance_sample_001/data/cost_masters/sales_price_master.csv
outputs/generated_master_data/home_appliance_sample_001/data/cost_masters/fx_rate_master.csv
outputs/generated_master_data/home_appliance_sample_001/source_assumption_register.csv
```

Minimal success:

```text
node_product_money_master.csv exists
SMART_WASHER_2028_BASE has rows for:
- supply_point
- MOM_JP_WASHER_PLANT
- DAD_US_CENTRAL_DC
- CS_US_ECOM

Money values are non-zero where expected:
- MOM variable_cost_unit_value > 0
- DAD inventory_unit_value > 0
- CS revenue_unit_value > 0
```

---

## 22. Phase 2A Codex Implementation Prompt Draft

```text
Implement Phase 2A of the MOSD to WOM Master CSV Adapter.

Target repository:
Yasushi-Osugi/wom-event-flow-analyzer

Target branch:
feature/costing-two-phase-integration

Read:
- docs/schema/wom_current_master_files_map.md
- docs/schema/wom_master_original_source_data_schema.md
- docs/schema/wom_mosd_to_wom_master_adapter_design.md
- docs/schema/wom_mosd_phase2_money_adapter_design.md
- docs/notes/mosd_phase1_smoke_test_260501.md

Context:
Phase 1 adapter already generates:
- node_geo.csv
- product_tree_inbound.csv
- product_tree_outbound.csv
- sku_P_month_data.csv
- sku_S_month_data.csv
- node_master.csv
- adapter_report.md
- validation_report.md

Goal:
Extend the adapter to generate Phase 2A money and market masters.

Requirements:
1. Add CLI flag:
   --include-money

2. When --include-money is provided, generate:
   - pysi/master_data/node_character_money_master.csv
   - pysi/master_data/node_product_money_master.csv
   - data/cost_masters/market_master.csv
   - data/cost_masters/cs_node_to_market_map.csv
   - data/cost_masters/product_cost_master.csv
   - data/cost_masters/node_cost_master.csv
   - data/cost_masters/lane_cost_master.csv
   - data/cost_masters/sales_price_master.csv
   - data/cost_masters/fx_rate_master.csv
   - source_assumption_register.csv

3. Extend sample MOSD JSON/YAML:
   - add markets
   - add node_market_mapping
   - add money_overlay.node_product_values
   - add cost_assumptions.product_costs
   - add cost_assumptions.node_costs
   - add cost_assumptions.lane_costs
   - add cost_assumptions.sales_prices
   - add currencies.fx_rates

4. Use direct money_overlay.node_product_values for node_product_money_master.csv.
   If absent, implement simple derived fallback.

5. Keep existing Phase 1 behavior unchanged when --include-money is not specified.

6. Do not modify existing WOM planner, GUI, or production master CSV files.

7. Generated output must stay under:
   outputs/generated_master_data/<model_id>/

8. Extend validators for:
   - node_product_money_master node/product references
   - market_id references
   - numeric money fields >= 0
   - fx_rate > 0

9. Extend tests:
   - existing tests still pass
   - new test with --include-money verifies money files exist
   - node_product_money_master contains CS_US_ECOM revenue value > 0

10. Use standard library only.
    Do not add new dependencies.

Acceptance command:
python -m pysi.modeling.wom_master_adapter ^
  --mosd samples/mosd/home_appliance_sample_v0_1.json ^
  --output outputs/generated_master_data/home_appliance_sample_001 ^
  --overwrite ^
  --include-money

Please create a focused additive PR implementing Phase 2A only.
```

---

## 23. Open Issues

### 23.1 Existing WOM money evaluation path

The current WOM execution path may still use legacy money masters:

```text
offering_price_ASIS_TOBE.csv
sku_cost_table_inbound.csv
sku_cost_table_outbound.csv
tariff_table.csv
```

Phase 2A should not try to remove those dependencies.  
A later phase may add compatibility generation for legacy money masters if required.

### 23.2 Exact loader expectations for node_product_money_master.csv

Before finalizing Phase 2A implementation, confirm the current loader behavior in:

```text
pysi/master_data/money_master_loader.py
```

Important points:

```text
required columns
optional columns
default handling
currency handling
node_character dependency
```

### 23.3 Management Cockpit integration

Phase 2A may create non-zero money values, but Management Cockpit may require additional aggregation hooks.

This should be tested after generated money masters are copied into runtime master locations.

### 23.4 Phase 2B timing

Do not overbuild Phase 2A.  
Phase 2B should handle:

```text
SGA
fixed asset
allocation rules
FX scenario comparison
cost waterfall
market P/L
```

---

## 24. Recommended Next Step

1. Commit this design document.
2. Ask Codex to implement Phase 2A using the prompt in this document.
3. Run adapter with `--include-money`.
4. Temporarily copy generated Phase 2A masters into runtime locations.
5. Launch WOM and confirm that generated model has non-zero money values where expected.
6. Record smoke test results in:

```text
docs/notes/mosd_phase2a_money_smoke_test_260501.md
```
