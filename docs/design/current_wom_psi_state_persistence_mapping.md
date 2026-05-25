# Current WOM PSI State Persistence Mapping

**Version:** v0r1 draft  
**Date:** 2026-05-19  
**Status:** Design / implementation mapping memo  
**Target path:** `docs/design/current_wom_psi_state_persistence_mapping.md`

---

## 1. Purpose

This memo maps the current WOM / PySI state persistence implementation.

The purpose is to clarify:

- what has already been implemented for `psi_state` save / load
- how current persistence relates to physical trees and product-specific PlanNode trees
- how `psi_events.parquet`, `parameters.json`, `metadata.json`, and `state_hash.txt` are used
- how current persistence relates to future `PlanningInput` / `PlanningOutput`
- what should become the canonical persistence path
- what should remain legacy

This memo is part of the broader WOM Planning Engine refactoring work.

---

## 2. Background

The current repository contains two broad persistence families.

### 2.1 Newer PSI State Persistence

Primary files:

```text
pysi/io/psi_state_io.py
pysi/io/psi_state_loader.py
```

These implement structured `psi_state` export / load using:

```text
physical tree JSON
product tree JSON
psi_events.parquet
parameters.json
metadata.json
state_hash.txt
```

### 2.2 Legacy Pickle / gpickle Persistence

Legacy files and references remain in:

```text
pysi/gui/app.py
pysi/psi_planner_mvp/init_load_plan_data.py
```

These use `pickle.dump`, `pickle.load`, and `nx.write_gpickle`.

This should be treated as a legacy save/load path.

---

## 3. Current PSI State Directory Structure

The current `psi_state` export structure is:

```text
<save_dir>/
  psi_state/
    physical_tree_outbound.json
    physical_tree_inbound.json
    product_tree_outbound.json
    product_tree_inbound.json
    psi_events.parquet
    parameters.json
    metadata.json
    state_hash.txt
```

This aligns with the previously defined conceptual `psi_state` save format.

---

## 4. Export Implementation

### 4.1 Main export function

The main export function is:

```python
export_psi_state(...)
```

Located in:

```text
pysi/io/psi_state_io.py
```

Conceptual signature:

```python
def export_psi_state(
    save_dir,
    physical_root_out,
    physical_root_in,
    prod_roots_out,
    prod_roots_in,
    weeks,
    params,
    meta,
    office_meta=None,
    fifo_mode="FIFO",
) -> str:
    ...
```

It returns:

```text
state_hash
```

---

### 4.2 Physical tree export

Function:

```python
export_physical_tree(...)
```

Outputs:

```text
physical_tree_outbound.json
physical_tree_inbound.json
```

Purpose:

```text
store physical / GUI / map node world
```

The exported payload contains:

```text
schema_version
bound
nodes
node_name
parent_name
lat / lon
leadtime_days
ss_days
long_vacation_weeks
tags
```

---

### 4.3 Product-specific planning tree export

Function:

```python
export_product_trees(...)
```

Outputs:

```text
product_tree_outbound.json
product_tree_inbound.json
```

Purpose:

```text
store product-specific PlanNode world
```

The exported payload contains:

```text
schema_version
bound
products
product_name
root_node_name
nodes
edges
pricing
costs
```

This is important because WOM has two node worlds:

```text
physical node world
planning PlanNode world
```

The product-specific PlanNode tree is the PSI planning authority.

---

### 4.4 PSI events export

Function:

```python
export_psi_events_parquet(...)
```

calls:

```python
collect_psi_events(...)
```

Output:

```text
psi_events.parquet
```

The exported rows include:

```text
product_name
bound
node_name
iso_index
bucket
seq
lot_id
qty
fifo_mode
```

Current implementation appears to collect from:

```text
prod_roots_out
```

and inspects:

```python
node.psi4demand
```

Important observation:

```text
Current psi_events export is primarily OUT/product-tree demand-layer oriented.
```

Inbound and supply-layer persistence may require future extension.

---

### 4.5 Parameters and metadata export

Functions:

```python
write_json(...)
```

Outputs:

```text
parameters.json
metadata.json
```

Expected contents include:

```text
calendar
scenario
created_at
wom_version
code_hash
psi_state_id
notes
```

---

### 4.6 State hash export

Functions:

```python
compute_state_hash(...)
write_state_hash(...)
```

Output:

```text
state_hash.txt
```

The hash is computed from all files under `psi_state/`, excluding `state_hash.txt`.

This provides reproducibility and integrity checking.

---

## 5. Load Implementation

### 5.1 Main load function

The main load function is:

```python
load_psi_state(base_dir, attach_psi=True, logger=None) -> PsiState
```

Located in:

```text
pysi/io/psi_state_loader.py
```

It loads:

```text
physical trees
product trees
parameters
metadata
state_hash
psi_events.parquet
```

and returns:

```python
PsiState
```

---

### 5.2 Physical tree load

Function:

```python
load_physical_trees(base_dir)
```

Uses:

```python
_build_physical_tree(...)
```

Outputs:

```text
physical_root_out
physical_root_in
```

---

### 5.3 Product-specific PlanNode tree load

Function:

```python
load_product_trees(base_dir)
```

Uses:

```python
_build_product_roots(...)
```

Outputs:

```text
prod_tree_dict_OT
prod_tree_dict_IN
```

Each product root is reconstructed as a `PlanNode`.

If `pysi.network.plan_node.PlanNode` is not available, the loader falls back to `Node`.

---

### 5.4 PSI events attach

Function:

```python
attach_psi_events_from_parquet(...)
```

Behavior:

```text
read psi_state/psi_events.parquet
build product → node_name → PlanNode lookup
initialize psi4demand
append lot_id to psi4demand[w][bucket]
```

Current important behavior:

```python
node.psi4demand[w][idx].append(lot_id)
```

This preserves the V0R8 rule:

```text
PSI buckets contain Lot_ID lists, not quantities.
```

Important current limitation:

```text
The loader attaches psi_events primarily to OUT-side product trees.
Inbound and supply-layer attach are future extensions.
```

---

### 5.5 Hash verification

Functions:

```python
load_state_hash(...)
verify_state_hash(...)
```

Behavior:

```text
read stored state_hash.txt
compute current hash
compare stored vs computed
log warning if mismatch
```

---

## 6. PsiState Dataclass

The current loader defines:

```python
@dataclass
class PsiState:
    base_dir: str
    physical_root_out: Optional[Node]
    physical_root_in: Optional[Node]
    prod_tree_dict_OT: Dict[str, PlanNode]
    prod_tree_dict_IN: Dict[str, PlanNode]
    parameters: dict
    metadata: dict
    state_hash: Optional[str] = None
    psi_events_df: Optional[pd.DataFrame] = None
```

This is a useful structured representation of a loaded planning state.

---

## 7. PsiStatePlanEnv

The loader also defines:

```python
@dataclass
class PsiStatePlanEnv:
    psi_state: PsiState
```

It exposes:

```text
product_name_list
prod_tree_dict_OT
prod_tree_dict_IN
get_roots(product_name)
reload()
```

This is important because it provides a minimal PlanEnv-compatible interface.

Conceptually:

```text
psi_state directory
    ↓
PsiState
    ↓
PsiStatePlanEnv
    ↓
pipeline-compatible environment
```

This can become the bridge between persistence and planning execution.

---

## 8. GUI Save / Load Entry Points

### 8.1 File menu

The GUI `pysi/gui/app.py` includes menu entries:

```text
SAVE: to Directory
LOAD: from Directory
```

For non-SQL mode:

```python
file_menu.add_command(label="SAVE: to Directory", command=self.save_to_directory)
file_menu.add_command(label="LOAD: from Directory", command=self.load_psi_state_from_directory)
```

This confirms that a GUI load entry for psi_state exists.

---

### 8.2 auto_export_psi_state

The GUI also contains:

```python
auto_export_psi_state(...)
```

This function selects:

```text
physical roots
product roots
parameters
metadata
```

and calls:

```python
export_psi_state(...)
```

Important behavior:

```text
if plan_env is provided:
    use plan_env.prod_tree_dict_OT / IN

else:
    fallback to GUI prod_tree_dict_OT / IN
```

This is useful because it supports both SQL-like PlanEnv and GUI-held product trees.

---

## 9. Legacy Pickle / gpickle Persistence

Search results show legacy persistence using:

```text
pickle.dump(...)
pickle.load(...)
nx.write_gpickle(...)
```

Locations include:

```text
pysi/gui/app.py
pysi/psi_planner_mvp/init_load_plan_data.py
```

This legacy approach saved:

```text
app state
root_node_outbound
root_node_inbound
root_node_out_opt
NetworkX graphs
```

This should be treated as legacy.

It is useful for historical continuity but should not be the canonical future persistence path.

---

## 10. Current Persistence Role in Planning Architecture

The current `psi_state` persistence is closer to `PlanningOutput` / `State Snapshot` than to canonical `PlanningInput`.

### 10.1 PlanningOutput side

Current persistence can store:

```text
physical tree
product tree
PSI events
parameters
metadata
state hash
```

This resembles:

```text
PlanningOutput:
    PSI state
    derived event-like rows
    state metadata
    reproducibility hash
```

### 10.2 PlanningInput side

The following are not yet clearly represented as a single canonical package:

```text
network input
demand lots
capacity constraints
initial inventory
routing rules
allocation rules
scenario parameters
cost / price assumptions
```

These are still distributed across:

```text
case datasets
CSV masters
adapter outputs
env attributes
plugins
```

Therefore, future refactoring should distinguish:

```text
PlanningInput persistence
PlanningOutput persistence
```

---

## 11. Relationship to Canonical PlanningInput / PlanningOutput

The TOBE boundary for WOM Planning Engine should eventually define:

```python
@dataclass
class PlanningInput:
    network: object
    demand_lots: list
    capacity_constraints: list
    initial_inventory: list
    routing_rules: list
    allocation_rules: list
    planning_config: object
```

```python
@dataclass
class PlanningOutput:
    psi_state: object
    lot_results: list
    capacity_usage: list
    blocked_lots: list
    events: list
    issues: list
```

Current `psi_state` persistence is a strong candidate for the persisted `PlanningOutput`.

However, persisted `PlanningInput` remains an open design topic.

---

## 12. Current Limitations

### 12.1 OUT-side demand-layer focus

Current `psi_events.parquet` attach appears to reconstruct:

```text
OUT-side product tree psi4demand
```

Future extension may need:

```text
IN-side psi4demand
OUT-side psi4supply
IN-side psi4supply
```

### 12.2 Bucket order consistency

`psi_state_io.py` uses:

```python
BUCKET_CODES = ["P", "CO", "S", "I"]
```

while the canonical V0R8 bucket index convention is:

```text
0: S
1: CO
2: I
3: P
```

The code comment says:

```text
ここは実装に合わせて並び替えてOK
```

This requires careful verification.

Potential issue:

```text
export bucket order and load bucket mapping must match.
```

The loader uses:

```python
BUCKET_IDX = {"S": 0, "CO": 1, "I": 2, "P": 3}
```

Therefore, export logic should be reviewed to ensure bucket codes correctly reflect actual PSI bucket indices.

### 12.3 `qty` currently defaults to 1.0

`collect_psi_events(...)` emits:

```text
qty = 1.0
```

This matches the lot-count assumption but may need future integration with `LotHeader.quantity`.

### 12.4 Inbound / supply state persistence not fully explicit

The current export / load path should be reviewed for complete support of:

```text
prod_tree_dict_IN
psi4supply
inbound PSI events
```

---

## 13. Recommended Next Steps

### Step 1: Verify export / load bucket mapping

Check whether `BUCKET_CODES` in `psi_state_io.py` correctly maps actual PSI indices.

Potential required fix:

```text
BUCKET_CODES should likely be ["S", "CO", "I", "P"]
```

unless current export order is intentionally different.

### Step 2: Create tests for round-trip persistence

Add tests:

```text
PlanNode with known psi4demand bucket contents
    ↓
export_psi_state
    ↓
load_psi_state
    ↓
compare restored psi4demand
```

Test target:

```text
S bucket round-trip
CO bucket round-trip
I bucket round-trip
P bucket round-trip
```

### Step 3: Define PlanningInput persistence

Create design memo:

```text
docs/design/wom_planning_input_persistence.md
```

Purpose:

```text
case dataset
capacity constraints
routing rules
lot attributes
scenario parameters
cost / price assumptions
```

### Step 4: Define PlanningOutput persistence boundary

Create design memo:

```text
docs/design/wom_planning_output_persistence.md
```

or extend this memo.

### Step 5: Connect Rice Case outputs to psi_state persistence

Future flow:

```text
Rice Case seeded PlanNode
    ↓
Backward Planning
    ↓
export_psi_state
    ↓
load_psi_state
    ↓
verify replay / restore
```

---

## 14. Recommended Canonical Direction

The recommended direction is:

```text
Use psi_state_io.py / psi_state_loader.py as the current canonical persistence path.
Treat pickle / gpickle persistence as legacy.
```

Future persistence should be aligned with:

```text
PlanningInput
PlanningOutput
Event Trace
State Snapshot
```

rather than raw GUI object serialization.

---

## 15. Summary

Current WOM already has a structured `psi_state` persistence implementation.

Confirmed current path:

```text
export_psi_state
    ↓
physical_tree_outbound.json
physical_tree_inbound.json
product_tree_outbound.json
product_tree_inbound.json
psi_events.parquet
parameters.json
metadata.json
state_hash.txt
```

and load path:

```text
load_psi_state
    ↓
physical roots
product-specific PlanNode trees
parameters
metadata
state hash
psi_events attached to product trees
PsiStatePlanEnv
```

This implementation is a strong foundation for WOM's future `PlanningOutput` persistence.

The key remaining work is to:

```text
verify bucket mapping correctness
extend inbound / supply persistence if needed
define PlanningInput persistence
connect persistence to Rice Case and future E2E scenario workflows
```

This mapping clarifies that WOM already has a persistence spine. The next step is to align it with the canonical PlanningInput / PlanningOutput architecture.
