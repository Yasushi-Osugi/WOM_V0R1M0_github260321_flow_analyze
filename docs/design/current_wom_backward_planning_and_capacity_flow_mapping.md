# Current WOM Backward Planning and Capacity Flow Mapping

**Version:** v0r2 revised with capacity-provider findings  
**Date:** 2026-05-19  
**Status:** Design / implementation mapping memo  
**Target path:** `docs/design/current_wom_backward_planning_and_capacity_flow_mapping.md`

---

## 1. Purpose

This memo maps the current WOM / PySI V0R8 planning flow around:

- Backward Planning
- `supply_point` connection
- MOM allocation
- MOM capacity leveling
- capacity provider plugins
- demand-to-supply bridge candidates
- future placement of With Capacity Forward PUSH Planning

The goal is to clarify the existing implementation before designing or changing the next bridge or capacity-aware forward planning functions.

---

## 2. Why This Mapping Is Needed

Recent Rice Case work verified this path:

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

Before moving further to:

```text
psi4demand
    ↓
psi4supply
```

or to:

```text
With Capacity Forward PUSH Planning
```

we need to understand the existing engine sequence.

Current WOM already contains several functions that look like:

```text
outbound backward planning
outbound-to-inbound bridge
market-to-MOM allocation
MOM capacity leveling
demand-to-supply bridge
forward PUSH / PULL processing
capacity provider plugins
```

Therefore, the next step is not to create a new bridge blindly.

The next step is to map the current engine and identify canonical functions.

---

## 3. High-Level Current Flow Hypothesis

The current `Run Full Plan` flow can be understood as:

```text
Run Full Plan
    ↓
_run_planning_sequence(...)
    ↓
outbound_backward_leaf_to_MOM(...)
    ↓
outbound → inbound connection
    ↓
MOM allocation
    ↓
MOM capacity feasibility / leveling
    ↓
inbound backward planning by MOM subtree
    ↓
demand-to-supply bridge
    ↓
forward supply planning / PUSH-PULL
```

The exact runtime order should be confirmed by reading `_run_planning_sequence(...)`.

---

## 4. Run Full Plan Entry Point

The GUI button calls:

```python
ttk.Button(action_row, text="Run Full Plan", command=self.run_full_plan)
```

`run_full_plan()` delegates the actual planning sequence to:

```python
self._run_planning_sequence(use_selected_decouples=True)
```

The planning sequence resolves the selected product and obtains product-specific roots:

```text
out_root = env.prod_tree_dict_OT[prod]
in_root  = env.prod_tree_dict_IN[prod]
```

with fallbacks to:

```text
env.root_node_outbound
env.root_node_inbound
```

This confirms that the planning target is the product-specific PlanNode world.

---

## 5. Product-Specific PlanNode Roots

WOM has two node worlds.

```text
Physical layer:
    product-independent GUI / map / NetworkX node world

Planning layer:
    product-specific PlanNode tree world
```

The target roots are:

```text
prod_tree_dict_OT[product_name] → outbound planning tree
prod_tree_dict_IN[product_name] → inbound planning tree
```

The current mapping work and future bridge work should target these PlanNode trees, not physical GUI nodes.

---

## 6. Current Step 1: Outbound Backward Planning

Current function:

```python
outbound_backward_leaf_to_MOM(out_root, in_root, layer="demand")
```

Current behavior:

```python
for n in _iter_postorder(out_root):
    if hasattr(n, "aggregate_children_P_into_parent_S"):
        n.aggregate_children_P_into_parent_S(layer=layer)
    if hasattr(n, "calcS2P"):
        n.calcS2P()
```

Meaning:

```text
market / leaf demand
    ↓
DAD nodes
    ↓
supply_point
```

This is current outbound-side Backward Planning / Demand Allocation.

It should be treated as an existing V0R8 engine asset.

---

## 7. `supply_point` Connection Model

`supply_point` is the conceptual connection node between outbound and inbound planning trees.

```text
OUTBOUND:
    supply_point → DADxxx → market / leaf

INBOUND:
    supply_point → MOMxxx → upstream / leaf
```

`supply_point` is the E2E connection point between demand-side and supply-side planning worlds.

However, implementation must avoid blindly propagating the same demand from `supply_point` into all MOM branches.

Existing inbound logic already recognizes this risk and processes MOM subtrees separately.

---

## 8. Outbound-to-Inbound Connection

Current bridge candidate:

```python
connect_outbound2inbound(out_root, in_root)
```

It appears inside:

```python
inbound_backward_MOM_to_leaf(...)
```

Conceptually:

```text
outbound-side accumulated demand
    ↓
inbound-side demand context
```

Open questions:

```text
1. Does it copy supply_point demand?
2. Does it copy root-level PSI?
3. Does it preserve Lot_IDs?
4. Which buckets are copied?
5. Does it target psi4demand or psi4supply?
```

---

## 9. Processing A: Market-to-MOM Allocation

Current function:

```python
allocate_markets_to_moms(...)
```

Current behavior:

```text
1. collect source lots
2. extract market_key from lot_id
3. select assigned MOM using policy dictionary
4. append lot to selected MOM.psi4demand[w][S]
```

The code comment states the minimum skeleton:

```text
1. source lots を集める
2. lot_id から market_key を抜く
3. policy で担当 MOM を決める
4. 担当 MOM の psi4demand[w][0] に lot を配る
```

This is current WOM's rule-based MOM allocation.

It is not yet a full optimization model.

### Future direction

This can later become an OR / optimization model.

Possible objective functions:

```text
service level
market priority compliance
profit / margin contribution
capacity utilization balance
transport cost
leadtime
strategic priority
```

Possible constraints:

```text
MOM capacity
market demand
leadtime
lane availability
product capability
allocation policy
```

---

## 10. Inbound Backward Planning by MOM Subtree

Current function:

```python
inbound_backward_MOM_to_leaf(...)
```

This identifies MOM nodes:

```python
mom_list = _find_nodes_by_prefix(in_root, "MOM_")
```

and then runs inbound Backward Planning per MOM subtree:

```python
calc_all_psiS2P2childS_preorder(a_mom)
```

Meaning:

```text
MOM.psi4demand[w][S]
    ↓
MOM subtree backward planning
    ↓
upstream / inbound leaf demand allocation
```

This structure avoids propagating identical demand into all MOM branches from `supply_point`.

---

## 11. Processing B: MOM Capacity Leveling

### 11.1 Legacy / simple capacity leveling

Existing function:

```python
inbound_MOM_leveling_vs_capacity(...)
```

This function inspects:

```python
mom.psi4demand[w][3]
```

where bucket `3` is `P`.

If P lots exceed capacity, overflow lots are shifted earlier.

Conceptual logic:

```text
MOM.psi4demand[w][P] exceeds capacity
    ↓
keep lots within capacity in week w
    ↓
overflow lots move to w-1, w-2, ...
```

Capacity source priority:

```text
1. env.weekly_capability[product][mom_name][w]
2. env.weekly_capability[mom_name][w]
3. mom.nx_capacity
```

This corresponds to capacity-constrained backward leveling / advance production.

### 11.2 Current `level_mom_demand_with_capacity`

Search results confirm that:

```text
level_mom_demand_with_capacity
```

is implemented in:

```text
pysi/plan/engines.py
```

and called from:

```text
pysi/gui/cockpit_tk.py::_run_planning_sequence(...)
```

as step2.5.

This means the current Run Full Plan likely uses the newer `level_mom_demand_with_capacity(...)` rather than the older `inbound_MOM_leveling_vs_capacity(...)`.

### 11.3 Required next check

The exact behavior of `level_mom_demand_with_capacity(...)` should be inspected directly.

Important questions:

```text
1. Does it replace inbound_MOM_leveling_vs_capacity?
2. Does it consume env.weekly_capability?
3. Does it work before or after allocate_markets_to_moms?
4. Does it perform advance production?
5. Does it produce capacity_result?
6. How does capacity_result connect to GUI / reporting?
```

---

## 12. P_month Plan vs P_capacity Month

The term `P_month` can mean different things.

These concepts should be separated:

```text
P_month plan:
    production requirement / planned production quantity

P_capacity_month:
    production capacity limit for MOM / production node

S_month supply:
    supply / shipment / sales quantity depending on context
```

The legacy `sku_P_month_data.csv` may represent production plan or demand/plan input in some contexts.

However, in the current plugin `capacity_provider_monthly_csv`, `sku_P_month_data.csv` is used as a monthly capacity input for building `env.weekly_capability`.

The name is therefore overloaded and should be clarified.

---

## 13. Confirmed Capacity Provider Path

The plugin:

```text
pysi/plugins/capacity_provider_monthly_csv/plugin.py
```

builds `env.weekly_capability` from monthly capacity CSV.

Current default input file:

```text
sku_P_month_data.csv
```

Current output:

```text
env.weekly_capability[product][MOMxxx] = [cap_lot per week]
env.weekly_capability_df
```

The plugin normalizes DAD-like names to MOM-like names:

```text
DADxxx → MOMxxx
```

This confirms that a P-month-to-weekly-capability path exists.

### 13.1 Current conversion rule

The current plugin uses a simplified conversion:

```text
1 month = 4 weeks
```

It calculates month offset as:

```text
m_off = (month - 1) * 4
```

and distributes monthly capacity evenly over 4 weeks.

### 13.2 Design issue

This differs from the newer 4-4-5 calendar adapter used by the Plan Input Granularity Adapter.

Current state:

```text
capacity_provider_monthly_csv:
    1 month = 4 weeks

plan_input_granularity_adapter:
    4-4-5 calendar
```

This mismatch should be resolved in a future capacity input adapter.

---

## 14. Demand Provider Path

The plugin:

```text
pysi/plugins/demand_provider_monthly_csv/plugin.py
```

loads monthly demand from:

```text
sku_S_month_data.csv
S_month_data.csv
```

and generates:

```text
env.weekly_demand
env.weekly_demand_df
```

It also calls:

```text
env.init_psi_spaces_and_demand()
```

when available.

This suggests that the demand-side monthly-to-weekly-to-PSI initialization path already exists in plugin form.

The new Plan Input Granularity Adapter is a cleaner, modular version of this idea.

---

## 15. Other Capacity-Related Plugins

### 15.1 `capacity_clip`

The `capacity_clip` plugin works on allocation mutation.

Conceptual role:

```text
proposed shipments
    ↓
edge.capacity
    ↓
clipped shipments
    ↓
receipts recalculation
```

This is closer to forward allocation / shipment feasibility than to MOM P capacity loading.

### 15.2 `capacity_allocator`

The `capacity_allocator` plugin reads:

```text
weekly_constraints.json
```

and applies node and edge capacity limits to proposed shipments.

This is another capacity path, separate from `capacity_provider_monthly_csv`.

### 15.3 Interpretation

There are currently multiple capacity-related mechanisms:

```text
1. monthly capacity provider → env.weekly_capability
2. edge shipment clipper → clipped shipments
3. weekly_constraints allocator → constrained allocation
4. MOM demand leveling → capacity-aware backward planning
```

These should be mapped and unified conceptually, but not merged hastily.

---

## 16. Demand-to-Supply Bridge Candidates

Current engine already has multiple bridge-like functions.

### 16.1 `bridge_inbound_demand_to_supply(root)`

This function:

```text
reads node.psi4demand[w][S]
sets node.psi4supply[w] = [demand_s, [], [], []]
```

Meaning:

```text
demand S
    ↓
supply S seed
```

### 16.2 `copy_demand_to_supply_rec(node)`

Inside `inbound_backward_MOM_to_leaf(...)`, demand is cloned to supply for each MOM subtree.

Conceptual behavior:

```text
node.psi4supply = clone(node.psi4demand)
```

### 16.3 Existing PUSH / PULL helpers

Existing functions include:

```text
copy_S_demand2supply(node)
copy_P_demand2supply(node)
PULL_process(node)
PUSH_process(node)
push_pull_all_psi2i_decouple4supply5(...)
```

These also perform demand-to-supply or supply-side actions.

### 16.4 Design implication

A new bridge should not be added until existing bridge candidates are mapped and a canonical bridge policy is selected.

---

## 17. With Capacity Forward PUSH Placement

Future **With Capacity Forward PUSH Planning** should be placed after the demand-to-supply bridge.

Conceptual position:

```text
Backward Planning:
    demand allocation
    MOM allocation
    MOM capacity leveling
        ↓
Demand-to-Supply Bridge:
    psi4demand → psi4supply
        ↓
Forward Planning:
    with Capacity Forward PUSH Planning
```

Meaning:

```text
psi4demand:
    where and when demand lots should be planned

psi4supply:
    how planned lots actually move under execution / capacity constraints
```

With Capacity Forward PUSH should not replace Backward Planning.

It should validate and simulate supply execution under capacity constraints.

---

## 18. Annual Capacity and ROI Interpretation

MOM capacity has a management-level meaning.

It is not only a weekly algorithmic constraint.

```text
annual demand
    ↓
annual production requirement
    ↓
weekly average production requirement
    ↓
peak weekly capacity requirement
    ↓
MOM capacity shortage / surplus
```

If weekly or seasonal demand repeatedly exceeds MOM capacity:

```text
capacity shortage
    ↓
advance production
    ↓
higher inventory
    ↓
storage / working capital cost
    ↓
potential service loss
    ↓
equipment investment question
```

WOM should eventually support:

```text
capacity increase scenario
investment cost
ROI proxy
capacity utilization
profit / cash impact
long-term sustainability
```

This belongs to Management Cockpit / E2E Evaluation, not to low-level PSI bucket operations alone.

---

## 19. Current Confirmed Implementation Map

Confirmed or strongly indicated current implementation:

```text
Run Full Plan:
    run_full_plan()
        ↓
    _run_planning_sequence(...)

Outbound Backward Planning:
    outbound_backward_leaf_to_MOM(...)

Outbound → Inbound connection:
    connect_outbound2inbound(...)

MOM Allocation:
    allocate_markets_to_moms(...)

MOM Capacity Feasibility / Leveling:
    level_mom_demand_with_capacity(...)
    inbound_MOM_leveling_vs_capacity(...) legacy/simple

Inbound Backward Planning:
    inbound_backward_MOM_to_leaf(...)
    calc_all_psiS2P2childS_preorder(...)

Capacity Input:
    capacity_provider_monthly_csv
        sku_P_month_data.csv
            ↓
        env.weekly_capability

Demand Input:
    demand_provider_monthly_csv
        sku_S_month_data.csv / S_month_data.csv
            ↓
        env.weekly_demand
        init_psi_spaces_and_demand()

Demand-to-Supply bridge candidates:
    bridge_inbound_demand_to_supply(...)
    copy_demand_to_supply_rec(...)
    copy_S_demand2supply(...)
    copy_P_demand2supply(...)

Forward Planning:
    PUSH_process(...)
    PULL_process(...)
    push_pull_all_psi2i_decouple4supply5(...)
    inbound_forward_leaf_to_MOM(...)
```

---

## 20. Current Open Questions

The following must be clarified before designing the next bridge or capacity feature.

```text
1. What is the exact current _run_planning_sequence step order?
2. What exactly does level_mom_demand_with_capacity do?
3. Does level_mom_demand_with_capacity replace inbound_MOM_leveling_vs_capacity?
4. Is inbound_MOM_leveling_vs_capacity still active anywhere?
5. Should capacity_provider_monthly_csv move from 4-week/month to 4-4-5?
6. Does sku_P_month_data.csv currently mean production capacity in all contexts?
7. Is a clearer P_capacity_month.csv needed?
8. Which demand-to-supply bridge function should become canonical?
9. Where should With Capacity Forward PUSH be inserted?
10. How should capacity investment / ROI scenario connect to KPI evaluation?
```

---

## 21. Recommended Next Investigation

### 21.1 Extract `_run_planning_sequence`

Run:

```bat
python -c "from pathlib import Path; lines=Path('pysi/gui/cockpit_tk.py').read_text(encoding='utf-8', errors='ignore').splitlines(); [print(f'{i+1}: {lines[i]}') for i in range(1940,2225)]"
```

This should produce the actual Run Full Plan step order.

### 21.2 Inspect `level_mom_demand_with_capacity`

Run:

```bat
python -c "from pathlib import Path; lines=Path('pysi/plan/engines.py').read_text(encoding='utf-8', errors='ignore').splitlines(); [print(f'{i+1}: {lines[i]}') for i in range(1100,1340)]"
```

### 21.3 Inspect capacity provider

Run:

```bat
python -c "from pathlib import Path; lines=Path('pysi/plugins/capacity_provider_monthly_csv/plugin.py').read_text(encoding='utf-8', errors='ignore').splitlines(); [print(f'{i+1}: {lines[i]}') for i in range(1,180)]"
```

---

## 22. Recommended Design Sequence

Recommended next sequence:

```text
1. Complete current implementation mapping.
2. Identify canonical demand-to-supply bridge.
3. Confirm level_mom_demand_with_capacity behavior.
4. Design WOM capacity input granularity adapter.
5. Decide 4-week/month vs 4-4-5 capacity calendar policy.
6. Design canonical demand-to-supply bridge.
7. Design with Capacity Forward PUSH placement.
8. Design annual capacity / ROI evaluation.
```

---

## 23. Summary

Before adding a new demand-to-supply bridge or extending With Capacity Forward PUSH, WOM should first map its existing engine flow.

Updated key understanding:

```text
Outbound Backward Planning already exists.
MOM allocation already exists as a policy-based function.
level_mom_demand_with_capacity exists and is called from Run Full Plan.
MOM capacity provider exists and populates env.weekly_capability.
Demand-to-supply bridge candidates already exist.
Forward PUSH/PULL functions already exist.
```

Therefore, the next step is not to invent a new bridge from scratch.

The next step is to:

```text
map the current engine,
identify canonical functions,
separate plan vs capacity inputs,
align capacity calendar policy,
and then insert With Capacity Forward PUSH at the correct location.
```

This mapping protects existing WOM implementation assets and prevents duplicate planning logic.
