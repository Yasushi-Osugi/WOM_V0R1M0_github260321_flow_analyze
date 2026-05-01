# WOM MOSD Phase 2B Runtime Money Integration Design v0.1

> File: `docs/schema/wom_mosd_phase2b_runtime_money_integration_design.md`  
> Status: Living Design Document v0.1  
> Owner: WOM Project / Yasushi Ohsugi × ChatGPT  
> Purpose: Phase 2Aで生成した「値札」masterを、WOM実行時の金額評価・GUI・Management Cockpitが実際に読むための runtime integration / smoke test 設計を定義する。  
> Depends on:
> - `docs/schema/wom_mosd_phase2_money_adapter_design.md`
> - `docs/notes/mosd_phase1_smoke_test_260501.md`
> - Phase 2A implementation: `--include-money`

---

## 1. Purpose

Phase 2A proved that MOSD can generate money and market masters:

```text
MOSD
  ↓
--include-money
  ↓
node_product_money_master.csv
node_character_money_master.csv
market_master.csv
cs_node_to_market_map.csv
product_cost_master.csv
node_cost_master.csv
lane_cost_master.csv
sales_price_master.csv
fx_rate_master.csv
source_assumption_register.csv
```

Phase 2B answers the next question:

```text
Does WOM runtime actually read the price tags?
```

In other words, Phase 2B is not primarily about generating more master files.  
It is about connecting generated money masters to existing WOM runtime, GUI, reports, and Management Cockpit.

---

## 2. Phase 2A vs Phase 2B

### Phase 2A

```text
Goal:
  Generate price tags and market labels.

Focus:
  MOSD → money / market master CSV files.

Success:
  Generated output contains non-zero placeholder money values.
```

### Phase 2B

```text
Goal:
  Make WOM runtime read those price tags.

Focus:
  generated master folder → WOM runtime money evaluation path.

Success:
  WOM GUI / report / cockpit shows non-zero revenue, cost, inventory value, or profit
  for SMART_WASHER_2028_BASE.
```

---

## 3. Key Design Principle

Phase 2B should be implemented as a safe runtime integration layer.

It should not directly overwrite production masters by default.

Recommended principle:

```text
Generated masters are scenario artifacts.
Runtime should be able to use a generated master folder explicitly.
```

Preferred future command:

```bat
python -m main --master-dir outputs/generated_master_data/home_appliance_phase2a_check
```

Near-term safe command:

```bat
python -m pysi.modeling.apply_generated_masters ^
  --generated outputs/generated_master_data/home_appliance_phase2a_check ^
  --target . ^
  --backup-dir outputs/master_backup/home_appliance_phase2b_260501 ^
  --include-money
```

Phase 2B should avoid silent replacement of:

```text
data/
pysi/master_data/
```

---

## 4. Phase 2B Scope

Phase 2B should include:

1. runtime master apply / staging utility
2. master backup / restore support
3. money master loader compatibility check
4. runtime smoke test command
5. generated money values read by WOM runtime
6. smoke test note generation
7. optional cleanup of legacy money fallback conflicts

Phase 2B should not yet include:

1. full cost waterfall
2. complete management accounting engine rewrite
3. complete allocation engine
4. full SaaS scenario management
5. automatic external data search

---

## 5. Current Observation

Phase 2A adapter already generated both Phase 1 and Phase 2A files when `--include-money` was specified.

The generated `node_product_money_master.csv` has non-zero values for the smoke test:

```text
MOM_JP_WASHER_PLANT variable_cost_unit_value = 350
DAD_US_CENTRAL_DC inventory_unit_value = 520
CS_US_ECOM revenue_unit_value = 800
```

The generated market bridge also connects:

```text
CS_US_ECOM → MKT_US_ECOM
```

Therefore, Phase 2B should now verify whether these values are consumed by WOM runtime.

---

## 6. Runtime Integration Options

### Option A: Manual Copy Smoke Test

This is the fastest test method.

Process:

```text
1. Generate Phase 2A masters under outputs/generated_master_data/<model_id>/
2. Backup current runtime masters
3. Copy generated files into runtime locations
4. Run WOM
5. Confirm money values
6. Restore original masters
```

Pros:

```text
fast
simple
good for first smoke test
```

Cons:

```text
manual
error-prone
not suitable as permanent workflow
```

### Option B: Apply Generated Masters Utility

Create a small command-line utility:

```text
pysi/modeling/apply_generated_masters.py
```

Command:

```bat
python -m pysi.modeling.apply_generated_masters ^
  --generated outputs/generated_master_data/home_appliance_phase2a_check ^
  --target . ^
  --backup-dir outputs/master_backup/home_appliance_phase2b_test ^
  --include-money ^
  --dry-run
```

This utility copies generated masters into runtime locations with backup.

Pros:

```text
safe
repeatable
auditable
good for smoke testing
```

Cons:

```text
still copies files into runtime locations
not full runtime parameterization
```

### Option C: Runtime master-dir parameter

Add a runtime parameter to WOM:

```bat
python -m main --master-dir outputs/generated_master_data/home_appliance_phase2a_check
```

Pros:

```text
best long-term architecture
no copying
scenario-friendly
```

Cons:

```text
requires deeper loader/pipeline changes
may touch more existing code
```

### Recommended path

```text
Phase 2B-1:
  implement Option B

Phase 2B-2:
  design Option C

Phase 3:
  implement Option C as generated master runtime mode
```

---

## 7. Runtime File Mapping

When applying generated masters, copy these files.

### Quantity masters

From:

```text
outputs/generated_master_data/<model_id>/data/
```

To:

```text
data/
```

Files:

```text
node_geo.csv
product_tree_inbound.csv
product_tree_outbound.csv
sku_P_month_data.csv
sku_S_month_data.csv
```

### Semantic node master

From:

```text
outputs/generated_master_data/<model_id>/pysi/master_data/node_master.csv
```

To:

```text
pysi/master_data/node_master.csv
```

### Semantic money masters

From:

```text
outputs/generated_master_data/<model_id>/pysi/master_data/
```

To:

```text
pysi/master_data/
```

Files:

```text
node_character_money_master.csv
node_product_money_master.csv
```

### Cost masters

From:

```text
outputs/generated_master_data/<model_id>/data/cost_masters/
```

To:

```text
data/cost_masters/
```

Files:

```text
market_master.csv
cs_node_to_market_map.csv
product_cost_master.csv
node_cost_master.csv
lane_cost_master.csv
sales_price_master.csv
fx_rate_master.csv
```

---

## 8. Backup / Restore Rule

Before copying any generated master into runtime locations, backup the current runtime files.

Recommended backup folder:

```text
outputs/master_backup/<timestamp>_<model_id>/
```

Example:

```text
outputs/master_backup/260501_2300_home_appliance_phase2b/
  data/
  data/cost_masters/
  pysi/master_data/
  manifest.json
```

The backup manifest should record:

```json
{
  "created_at": "260501_2300",
  "generated_source": "outputs/generated_master_data/home_appliance_phase2a_check",
  "target_root": ".",
  "copied_files": [],
  "backed_up_files": []
}
```

Restore command may be added later:

```bat
python -m pysi.modeling.apply_generated_masters ^
  --restore outputs/master_backup/260501_2300_home_appliance_phase2b
```

For Phase 2B first implementation, backup-only is enough. Restore may be manual.

---

## 9. Money Loader Compatibility Check

Before expecting WOM runtime to read the values, inspect the current money loader:

```text
pysi/master_data/money_master_loader.py
```

Key questions:

```text
1. Does it load node_product_money_master.csv?
2. What exact columns does it require?
3. Does it expect scenario_name?
4. Does it expect node_name or node_id?
5. Does it use currency?
6. How are missing values defaulted?
7. Where is it invoked from main / pipeline / cockpit?
```

If current runtime does not use `node_product_money_master.csv`, Phase 2B must add a small bridge.

---

## 10. Runtime Money Bridge

If `node_product_money_master.csv` is loaded but not applied to runtime nodes, add a small bridge function.

Recommended module:

```text
pysi/modeling/runtime_money_bridge.py
```

Purpose:

```text
Read node_product_money_master.csv and attach money attributes to Node instances.
```

Suggested fields attached to node:

```text
node.inventory_unit_value
node.revenue_unit_value
node.variable_cost_unit_value
node.fixed_cost_weekly
node.currency
```

Key:

```text
(node_name, product_name)
```

Pseudo-flow:

```python
for node in all_nodes:
    row = node_product_money[(node.name, product_name)]
    node.inventory_unit_value = row.inventory_unit_value
    node.revenue_unit_value = row.revenue_unit_value
    node.variable_cost_unit_value = row.variable_cost_unit_value
    node.fixed_cost_weekly = row.fixed_cost_weekly
```

This bridge should be additive and safe.

---

## 11. Runtime KPI Calculation

To prove that the register reads the price tags, Phase 2B should calculate a minimal runtime money snapshot.

Recommended minimum formulas:

```text
revenue = S_qty_or_sales_qty * revenue_unit_value
variable_cost = P_or_S_qty * variable_cost_unit_value
inventory_value = I_qty * inventory_unit_value
fixed_cost = fixed_cost_weekly
profit = revenue - variable_cost - fixed_cost
```

The exact quantity bucket can be refined later.  
For the first smoke test, the purpose is not perfect management accounting; it is to prove that non-zero money master values can flow into runtime KPIs.

Recommended output:

```text
outputs/generated_master_data/<model_id>/runtime_money_smoke_report.csv
```

Columns:

```text
product_name
node_name
week
S_qty
P_qty
I_qty
revenue_unit_value
variable_cost_unit_value
inventory_unit_value
fixed_cost_weekly
revenue
variable_cost
inventory_value
fixed_cost
profit
```

---

## 12. GUI / Cockpit Smoke Test

Phase 2B success should be checked in the GUI and / or reporting output.

Minimum visible success:

```text
Product:
  SMART_WASHER_2028_BASE

Node:
  CS_US_ECOM

Expected:
  revenue > 0
```

For node-level checks:

```text
MOM_JP_WASHER_PLANT:
  variable_cost > 0

DAD_US_CENTRAL_DC:
  inventory_value > 0

CS_US_ECOM:
  revenue > 0
```

Total-level check:

```text
total_revenue > 0
total_cost > 0
money values no longer all zero
```

---

## 13. Legacy Money Master Conflict

Current WOM runtime may still use legacy files:

```text
data/offering_price_ASIS_TOBE.csv
data/sku_cost_table_inbound.csv
data/sku_cost_table_outbound.csv
data/tariff_table.csv
```

Phase 2B should not remove these dependencies immediately.

Instead, use the following priority rule:

```text
Priority 1:
  node_product_money_master.csv if available for product-node

Priority 2:
  cost_masters / sales_price_master if mapped

Priority 3:
  legacy money masters as fallback
```

If current code has the reverse priority, Phase 2B may need a small loader priority fix.

---

## 14. Proposed Implementation Phases

### Phase 2B-1: Apply Generated Masters Utility

Create:

```text
pysi/modeling/apply_generated_masters.py
```

Features:

```text
--generated <folder>
--target <repo root>
--backup-dir <folder>
--include-money
--dry-run
```

Acceptance:

```text
dry-run lists files
apply backs up files
apply copies expected files
git status clearly shows copied runtime masters
```

### Phase 2B-2: Runtime Money Bridge Check

Add or verify:

```text
node_product_money_master.csv is loaded
money values attach to runtime node/product
```

Acceptance:

```text
runtime smoke report shows non-zero values
```

### Phase 2B-3: WOM GUI Smoke Test

Temporarily apply generated masters.

Run:

```bat
python -m main
```

Acceptance:

```text
SMART_WASHER_2028_BASE appears
CS_US_ECOM revenue > 0
MOM_JP_WASHER_PLANT cost > 0
DAD_US_CENTRAL_DC inventory value > 0
```

### Phase 2B-4: Smoke Test Note

Create:

```text
docs/notes/mosd_phase2b_runtime_money_smoke_test_260501.md
```

Record:

```text
commands
copied files
screenshots if any
observed values
remaining gaps
```

---

## 15. Codex Implementation Prompt Draft

```text
Implement Phase 2B-1 of MOSD runtime money integration.

Target repository:
Yasushi-Osugi/wom-event-flow-analyzer

Target branch:
feature/costing-two-phase-integration

Read:
- docs/schema/wom_mosd_phase2_money_adapter_design.md
- docs/schema/wom_mosd_phase2b_runtime_money_integration_design.md
- docs/notes/mosd_phase1_smoke_test_260501.md

Goal:
Create a safe utility that applies generated MOSD masters from outputs/generated_master_data/<model_id>/
to the current WOM runtime master locations with backup and dry-run support.

Create:
- pysi/modeling/apply_generated_masters.py
- tests/modeling/test_apply_generated_masters.py

Do not modify WOM planner or GUI.

CLI:
python -m pysi.modeling.apply_generated_masters ^
  --generated outputs/generated_master_data/home_appliance_phase2a_check ^
  --target . ^
  --backup-dir outputs/master_backup/home_appliance_phase2b_test ^
  --include-money ^
  --dry-run

Without --dry-run, copy files.

Copy Phase 1 files:
- data/node_geo.csv
- data/product_tree_inbound.csv
- data/product_tree_outbound.csv
- data/sku_P_month_data.csv
- data/sku_S_month_data.csv
- pysi/master_data/node_master.csv

When --include-money:
- pysi/master_data/node_character_money_master.csv
- pysi/master_data/node_product_money_master.csv
- data/cost_masters/market_master.csv
- data/cost_masters/cs_node_to_market_map.csv
- data/cost_masters/product_cost_master.csv
- data/cost_masters/node_cost_master.csv
- data/cost_masters/lane_cost_master.csv
- data/cost_masters/sales_price_master.csv
- data/cost_masters/fx_rate_master.csv

Requirements:
- Never delete files.
- Always backup target files before overwrite.
- Create manifest.json in backup-dir.
- Support --dry-run.
- Return non-zero exit code on missing generated source files.
- Use standard library only.
- Tests should create temporary generated/target folders and verify backup/copy behavior.

Acceptance:
python -m pytest -q tests/modeling/test_apply_generated_masters.py
```

---

## 16. Phase 2B Acceptance Criteria

Phase 2B should be considered successful when:

```text
1. Phase 2A generated masters can be safely applied to runtime master locations.
2. WOM can launch with generated SMART_WASHER_2028_BASE model.
3. Runtime money values are read from generated node_product_money_master.csv.
4. At least one revenue, cost, inventory value, or profit KPI is non-zero.
5. Original masters can be restored from backup.
6. Smoke test note is recorded.
```

---

## 17. Recommended Next Step

1. Commit this design document.
2. Ask Codex to implement Phase 2B-1 apply utility.
3. Generate Phase 2A masters with `--include-money`.
4. Apply generated masters using dry-run first.
5. Apply for real.
6. Launch WOM.
7. Confirm whether the register reads the price tags.
