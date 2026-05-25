# Legacy PySI V0R8 Input Loader Mapping

**Version:** v0r1 draft  
**Date:** 2026-05-18  
**Status:** Design memo  
**Target path:** `docs/design/legacy_pysi_v0r8_input_loader_mapping.md`

---

## 1. Purpose

This memo maps the legacy PySI V0R8 input loader implementation to the new WOM input-layer design.

The target legacy file is:

```text
PySI_V0R8_SQL_050_hook4git/pysi/psi_planner_mvp/init_load_plan_data.py
```

This file belongs to an older stage of PySI / WOM where GUI, input loading, PlanNode creation, monthly-to-weekly conversion, Lot_ID generation, allocation, and PSI seeding were tightly coupled.

The purpose of this memo is not to revive the old implementation as-is.

The purpose is to extract its useful design assets and map them to the newer WOM architecture:

```text
Raw input
    ↓
Canonical weekly tables
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
PlanNode PSI seeding
    ↓
Planning engines
```

---

## 2. Legacy File Role

The legacy `init_load_plan_data.py` had a broad responsibility.

It handled:

```text
1. GUI-driven data directory selection
2. loading product_tree_outbound.csv / product_tree_inbound.csv
3. creating physical / GUI node trees
4. creating product-specific PlanNode trees
5. linking GUI nodes and product-specific PlanNodes
6. loading monthly S / P data
7. converting monthly input to weekly data
8. generating Lot_ID lists
9. writing Lot_IDs directly into PSI buckets
10. performing allocation from demand lots to supply weeks
```

In the current WOM design, these responsibilities should be separated.

---

## 3. Legacy Physical Node and PlanNode Separation

The legacy implementation already contained the important distinction between:

```text
Physical / GUI node layer
Planning / product-specific PlanNode layer
```

### 3.1 Physical / GUI layer

The legacy loader first reads:

```text
product_tree_outbound.csv
product_tree_inbound.csv
```

and creates node dictionaries such as:

```text
nodes_outbound
nodes_inbound
root_node_outbound
root_node_inbound
```

These correspond to the physical or GUI-facing network layer.

### 3.2 Product-specific PlanNode layer

The legacy code then creates product-specific planning trees.

Conceptually:

```text
prod_tree_dict_OT[product_name] = outbound product-specific PlanNode root
prod_tree_dict_IN[product_name] = inbound product-specific PlanNode root
```

This is the same concept used in current WOM.

The important point is:

```text
The PSI planning authority belongs to product-specific PlanNode trees,
not to product-independent GUI nodes.
```

### 3.3 GUI node to PlanNode link

The legacy implementation links planning nodes back to GUI nodes through:

```text
gui_node.sku_dict[product_name] = plan_node
```

This means the GUI node can be used as a display shell, while the product-specific PlanNode remains the planning object.

This remains a valid architectural concept.

---

## 4. Legacy P_month to Weekly to Lot_ID Generation

The legacy code contains:

```python
convert_monthly_to_weekly_p(df: pd.DataFrame, lot_size: int)
```

This function performs the following flow:

```text
P_month_data.csv
    ↓
monthly rows
    ↓
daily expansion
    ↓
ISO week aggregation
    ↓
P_lot count calculation
    ↓
P_lot ID generation
```

### 4.1 Legacy monthly-to-daily expansion

The legacy function expands monthly values into daily rows by using the number of days in each month.

Conceptually:

```text
monthly value
    ↓
same value repeated across each day of the month
    ↓
daily rows
```

This implementation should be treated carefully because it may inflate values depending on the intended meaning of the monthly number.

If the monthly value is a monthly total, then daily expansion should distribute the value across days.

If the monthly value is a daily rate, then repeating the value across days is appropriate.

This semantic distinction must be clarified before reuse.

### 4.2 Legacy ISO week conversion

The old code uses ISO week logic:

```text
date → iso_year / iso_week
```

This differs from the newer 4-4-5 calendar approach already introduced in the Plan Input Granularity Adapter.

### 4.3 Legacy P_lot count calculation

The old code calculates:

```python
P_lot = ceil(value / lot_size)
```

This is useful but should now be handled through the newer Lot generation layer.

### 4.4 Legacy P_lot ID generation

The old function:

```python
generate_p_lot_ids(row)
```

creates IDs such as:

```text
P_{node_name}_{iso_year}{iso_week}_{sequence}
```

This is useful as a historical reference, but the current WOM input adapter should use the newer deterministic Lot_ID generation policy.

---

## 5. Legacy set_df_Plots2psi4supply Meaning

The legacy code contains:

```python
set_df_Plots2psi4supply(nodes_outbound, df_weekly, plan_year_st)
```

This function writes generated P_lot IDs directly into:

```python
node.psi4supply[week_index][3]
```

where bucket index `3` means:

```text
P bucket
```

The legacy flow is:

```text
P_month_data.csv
    ↓
weekly P lots
    ↓
P_lot IDs
    ↓
psi4supply[w][P]
```

This is important historically, but it differs from the current safer architecture.

In the new WOM input pipeline, direct writing into `psi4supply` should not be the first design choice.

The preferred current flow is:

```text
Raw plan input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
controlled PlanNode PSI seeding
```

---

## 6. Legacy perform_allocation Meaning

The legacy code also contains:

```python
perform_allocation(node, demand_map, supply_weeks, lot_links_enabled=True)
```

This function:

```text
1. collects demand S_lots
2. checks available supply weeks and capacities
3. assigns demand lots to supply weeks
4. writes allocated lots to node.psi4supply[w][P]
5. optionally records allocation links
```

Conceptually, this is an early version of:

```text
demand lots
    ↓
capacity-aware allocation
    ↓
production week assignment
    ↓
psi4supply[w][P]
```

This is highly relevant to current discussions around:

```text
MOM allocation
capacity-constrained backward planning
with Capacity Forward PUSH Planning
```

However, in the current architecture, this logic should not be reintroduced as a monolithic loader-side function.

It should be separated into:

```text
1. input normalization
2. Lot generation
3. allocation policy / optimization
4. PSI seeding
5. planning execution
6. trace / audit output
```

---

## 7. Mapping to New Plan Input Granularity Adapter

| Legacy concept | Legacy function / location | New WOM equivalent |
|---|---|---|
| Monthly P input | `P_month_data.csv` | `MonthlyPlanInputRow` |
| Monthly-to-weekly conversion | `convert_monthly_to_weekly_p` | `monthly_plan_to_weekly_rows` |
| ISO week mapping | `date.dt.isocalendar()` | `calendar_445.py` or future calendar adapter |
| P_lot count | `ceil(value / lot_size)` | `LotGenerationConfig` / `generate_lots_from_weekly_plan` |
| P_lot ID generation | `generate_p_lot_ids` | deterministic Lot_ID generation in `lot_generation.py` |
| Direct PSI write | `set_df_Plots2psi4supply` | `PsiSeedRecord` + `apply_psi_seed_records_to_plan_nodes` |
| Allocation | `perform_allocation` | future MOM allocation / capacity planning module |
| GUI node to PlanNode link | `sku_dict[product_name] = plan_node` | current physical node / PlanNode separation principle |
| Product-specific trees | `prod_tree_dict_OT / IN` | current product-specific PlanNode tree contract |

---

## 8. What Should Be Migrated

The following ideas should be migrated or reimplemented in the new architecture.

### 8.1 Product-specific PlanNode tree construction concept

Keep the principle:

```text
prod_tree_dict_OT[product_name]
prod_tree_dict_IN[product_name]
```

These product-specific trees are the proper PSI planning targets.

### 8.2 GUI node to PlanNode link concept

Keep the idea:

```text
GUI node is display / navigation shell
PlanNode is planning authority
```

The legacy `sku_dict[product_name] = plan_node` idea remains valuable.

### 8.3 Monthly-to-weekly conversion concept

Migrate the concept, but not the exact implementation blindly.

The new conversion must clarify whether monthly values are:

```text
monthly total
daily rate
weekly-equivalent value
capacity limit
```

### 8.4 Lot_ID generation concept

Migrate the idea of deterministic Lot_ID creation, but use the new `LotHeader` / `LotGenerationConfig` approach.

### 8.5 Allocation link concept

The old `allocation_links` idea should be preserved.

Future allocation should produce traceable links:

```text
demand_lot_id
assigned_mom
assigned_week
capacity_reason
priority_rule
allocation_policy_id
```

This is useful for audit, visualization, and Management Cockpit.

---

## 9. What Should Not Be Migrated As-Is

The following should not be migrated directly.

### 9.1 GUI and loader coupling

The old file mixes GUI, loading, PlanNode creation, PSI seeding, and allocation.

The new WOM architecture should keep these separated.

### 9.2 Direct PSI mutation from raw CSV loader

Avoid this pattern:

```text
CSV loader
    ↓
direct write to node.psi4supply[w][P]
```

Prefer:

```text
CSV loader
    ↓
canonical table
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
PlanNode seeding adapter
```

### 9.3 Unclear monthly value semantics

The old monthly-to-daily expansion repeats monthly value across every day.

This must not be reused until the meaning of the monthly number is clarified.

### 9.4 ISO week assumption as default

The old code uses ISO week aggregation.

Current WOM input adapter MVP uses 4-4-5 mapping.

Both may be needed, but the calendar mode should be explicit.

---

## 10. P_month Plan vs P_capacity Month

A key lesson from the legacy code is that `P_month` can mean different things.

We must distinguish:

```text
P_month plan:
    production requirement / production plan quantity

P_capacity_month:
    production capacity limit for MOM or production node

S_month supply:
    supply / shipment / sales quantity depending on context
```

The old `P_month_data.csv` loader appears to represent production plan lots, not necessarily MOM capacity.

Therefore, this should not be confused with:

```text
MOM capacity CSV
    ↓
weekly_capability
```

A separate capacity input adapter is needed for:

```text
P_capacity_month
    ↓
P_capacity_week
    ↓
env.weekly_capability[product][mom_node][week]
```

---

## 11. Recommended New Loader Refactor Direction

The future loader refactor should introduce clear layers.

### 11.1 Raw input layer

Examples:

```text
S_month_data.csv
P_month_data.csv
S_week_data.csv
P_week_data.csv
P_capacity_month.csv
P_capacity_week.csv
Rice case weekly input
```

### 11.2 Canonical input tables

Examples:

```text
WeeklyPlanRow
WeeklyCapacityRow
CostProfileRow
NodeMappingRow
```

### 11.3 Lot and metadata layer

Examples:

```text
LotHeader
Lot attributes
crop_year
source_granularity
available_week
quality_limit_week
```

### 11.4 PSI seed layer

Examples:

```text
PsiSeedRecord
PsiSeedTable
PlanNode seeding result
```

### 11.5 Planning engine layer

Examples:

```text
Backward Planning
MOM allocation
capacity leveling
demand-to-supply bridge
Forward Planning
```

---

## 12. Suggested Future Module Split

The old `init_load_plan_data.py` responsibilities should be split into modules.

```text
pysi/loaders/tree_loader.py
    load physical / product tree CSV

pysi/loaders/product_plan_tree_builder.py
    build prod_tree_dict_OT / prod_tree_dict_IN

pysi/adapters/plan_input_granularity.py
    monthly / weekly plan normalization

pysi/adapters/lot_generation.py
    LotHeader and Lot_ID generation

pysi/adapters/psi_seed.py
    PsiSeedRecord creation

pysi/adapters/plan_node_seeding.py
    safe PSI bucket mutation

pysi/adapters/capacity_input_granularity.py
    monthly / weekly capacity normalization

pysi/plan/mom_allocation.py
    market-to-MOM allocation policy / future optimization

pysi/plan/capacity_leveling.py
    capacity-constrained lot shifting / leveling

pysi/plan/demand_supply_bridge.py
    canonical psi4demand to psi4supply bridge
```

---

## 13. Relationship to Current Rice Case Work

The Rice Case work has already implemented a cleaner version of the old loader flow.

Current Rice Case path:

```text
Rice weekly input
    ↓
WeeklyPlanRow
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
PlanNode.psi4demand seed
    ↓
Backward Planning smoke
```

Legacy P_month path:

```text
P_month_data.csv
    ↓
weekly P lots
    ↓
P_lot IDs
    ↓
psi4supply[w][P]
```

The Rice Case path is cleaner because it separates:

```text
input meaning
lot identity
PSI seed target
planning execution
```

This should become the future standard.

---

## 14. Current Open Questions

The following items need further confirmation.

```text
1. Which current files load S_month_data.csv and P_month_data.csv?
2. Is old P_month_data.csv still used in the current WOM branch?
3. Is P_month currently interpreted as production requirement or production capacity?
4. Where is env.weekly_capability currently populated?
5. Is there an existing P_capacity_month.csv?
6. Should current monthly plan conversion use ISO week or 4-4-5?
7. Which demand-to-supply bridge implementation should become canonical?
8. Should perform_allocation be retired, refactored, or used as a prototype for MOM allocation?
```

---

## 15. Recommended Next Steps

### Step 1: confirm current monthly loader usage

Run:

```bat
git grep -n "P_month_data"
git grep -n "S_month_data"
git grep -n "sku_P_month_data"
git grep -n "weekly_capability"
git grep -n "convert_monthly_to_weekly_p"
git grep -n "perform_allocation"
```

### Step 2: define capacity input separately

Create:

```text
docs/design/wom_capacity_input_granularity_adapter.md
```

Purpose:

```text
P_capacity_month / P_capacity_week
    ↓
Canonical WeeklyCapacityRow
    ↓
env.weekly_capability
```

### Step 3: define canonical demand-to-supply bridge

Create:

```text
docs/design/wom_demand_to_supply_bridge.md
```

Purpose:

```text
psi4demand
    ↓
psi4supply
```

### Step 4: define MOM allocation and capacity planning

Create:

```text
docs/design/wom_mom_allocation_and_capacity_planning.md
```

Purpose:

```text
market demand lots
    ↓
MOM allocation
    ↓
capacity-constrained planning
```

---

## 16. Summary

The legacy PySI V0R8 `init_load_plan_data.py` should be treated as an important historical implementation reference.

It already contains several key ideas:

```text
product-specific PlanNode trees
GUI node to planning node link
P_month to weekly conversion
Lot_ID generation
direct PSI seeding
allocation links
```

However, its responsibilities are too tightly coupled.

The new WOM direction should preserve the concepts but split the implementation into clear layers:

```text
Raw input
    ↓
Canonical weekly rows
    ↓
LotHeader
    ↓
PsiSeedRecord
    ↓
PlanNode seeding
    ↓
Planning engines
```

The most important design conclusion is:

```text
Do not copy the old loader as-is.
Extract its concepts.
Map them into the new adapter-based WOM architecture.
```