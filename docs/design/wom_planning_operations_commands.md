# WOM Planning Operations Commands Design Memo

**Version:** v0r1 revised with Replan Handler, Loop Guard, and MOM S = DAD P Bridge  
**Date:** 2026-05-13  
**Status:** Design memo  
**Related design:** `docs/design/wom_e2e_constraint_management.md`

---

## 1. Purpose

This memo defines the practical WOM planning operation commands that orchestrate the E2E Constraint Management process.

The target commands are:

- `ReplanCommand`
- `handle_replan_command`
- Backward Planning commands
- Forward Simulation commands
- E2E Evaluation commands
- Management Issue Generation commands

The purpose is to translate WOM's planning architecture into explicit, auditable, and testable operation commands.

This memo is not a GUI design.  
It defines the command layer that can later be called from:

- CLI runners
- GUI buttons
- scenario runners
- Management Cockpit
- LLM-assisted planning navigator

---

## 2. Background

The E2E Constraint Management design defines the following process:

```text
Constraint Detection
    ↓
Alternative Route / Alternative Node Selection
    ↓
    if fully infeasible:
        skip to Management Issue Generation

    if partially infeasible:
        blocked portion → Management Issue Generation
        feasible portion → continue below
    ↓
Bottleneck Identification
    ↓
    if no active bottleneck:
        skip Capacity Allocation and proceed to E2E Evaluation
    ↓
Capacity Allocation at Bottleneck
    ↓
E2E Evaluation
    structured output based on WOM KPI Registry
    ↓
Management Issue Generation
```

The command layer should make this process executable.

Key responsibility boundary:

```text
Backward Planning / psi4demand:
    demand allocation
    capacity bucket assignment
    advance production placement
    alternative node assignment
    unallocated / backlog candidate placement

Forward Planning / psi4supply:
    supply simulation
    inventory movement simulation
    cost / profit evaluation
    capacity consistency validation
    replan command emission

E2E Evaluation:
    KPI calculation
    KPI delta vs baseline
    structured evaluation result

Management Issue Generation:
    issue classification
    impact summary
    recommended actions
    future LLM summarization input
```

---

## 3. Design Principles

### 3.1 Commands are explicit operations

Planning actions should be invoked through explicit commands.

Examples:

```text
detect_e2e_constraints
select_alternative_route_or_node
run_backward_capacity_aware_demand_allocation
run_forward_supply_simulation
validate_forward_capacity_consistency
run_e2e_evaluation
generate_management_issues
handle_replan_command
```

This avoids hidden side effects and makes WOM operation traceable.

---

### 3.2 Commands should support dry-run and commit modes

Each command should eventually support:

```text
dry_run:
    calculate and report what would happen

commit:
    update the target planning state
```

For early MVPs, dry-run may be enough.

---

### 3.3 Forward Planning should not silently rewrite the past

If Forward Planning detects a residual capacity or allocation inconsistency, it should emit a `ReplanCommand`.

It should not directly rewrite earlier demand placement.

---

### 3.4 Replanning is routed through the operations layer

`ReplanCommand` is a structured signal.

It does not execute correction by itself.

The operations command layer decides whether to:

- rerun Backward Planning
- adjust allocation assumptions
- select alternative route / node
- escalate to Management Issue Generation
- log as validation result

---

### 3.5 Evaluation uses KPI Registry

E2E Evaluation should use WOM KPI Registry as the canonical KPI definition layer.

KPI deltas should be structured as `KPIDelta` records.

---

## 4. Common Command Envelope

All planning operation commands should share common metadata.

### 4.1 Suggested Command Envelope

```python
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PlanningCommand:
    command_id: str
    command_type: str
    scenario_id: str
    product_name: str
    start_week: str
    end_week: str
    mode: str = "dry_run"  # dry_run / commit
    requested_by: str = ""
    reason: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
```

### 4.2 Suggested Command Result

```python
@dataclass
class PlanningCommandResult:
    command_id: str
    command_type: str
    scenario_id: str
    status: str  # success / warning / failed / skipped
    message: str = ""
    outputs: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    generated_replan_commands: list[Any] = field(default_factory=list)
    generated_management_issues: list[Any] = field(default_factory=list)
```

### 4.3 Command status convention

```text
success:
    command completed as expected

warning:
    command completed but produced warnings or replan commands

failed:
    command could not complete

skipped:
    command was intentionally skipped, for example due to no feasible route
```

---

## 5. ReplanCommand

### 5.1 Purpose

`ReplanCommand` is emitted when validation or evaluation detects that the current planning state should not be silently corrected in place.

Typical sources:

- Forward Planning capacity consistency validation
- E2E Evaluation
- Management Issue Generation
- Alternative Route / Node Selection

### 5.2 Minimum definition

```python
@dataclass
class ReplanCommand:
    scenario_id: str
    product_name: str
    trigger_source: str
    node_or_flow_name: str
    week: str
    violation_type: str
    severity: str
    suggested_action: str
    message: str
```

### 5.3 Required fields

#### `trigger_source`

```text
forward_planning
capacity_consistency_validation
e2e_evaluation
management_issue_generation
alternative_route_selection
```

#### `violation_type`

```text
capacity_exceeded
route_unavailable
allocation_inconsistency
no_feasible_route
partial_infeasibility
residual_backlog
inventory_over_capacity
capacity_master_missing
```

#### `severity`

```text
blocking
warning
info
```

#### `suggested_action`

```text
rerun_backward_planning
adjust_demand_allocation
select_alternative_route
escalate_to_management
review_capacity_master
log_only
```

### 5.4 Handling policy

```text
severity = blocking:
    route to planning operations command
    candidate actions:
        rerun_backward_planning
        select_alternative_route
        escalate_to_management

severity = warning:
    route to Management Issue Generation
    candidate actions:
        review_capacity_master
        adjust_demand_allocation

severity = info:
    log as validation result
    optional review
```

### 5.5 Important rule

```text
ReplanCommand does not modify the plan directly.
```

It is a structured signal passed to the planning operations command layer.

---

## 6. Handle Replan Command

### 6.1 Purpose

`handle_replan_command` receives a `ReplanCommand` and decides the next operation command.

This command is the missing link between:

```text
Forward Planning / Validation
    emits ReplanCommand
        ↓
Planning Operations Command Layer
    decides the next operation
```

It does not perform the full replanning itself.  
It routes the command to the next planning operation.

---

### 6.2 Suggested input / output dataclasses

```python
@dataclass
class HandleReplanCommandInput:
    replan_command: ReplanCommand
    planning_context: dict = field(default_factory=dict)
```

`planning_context` may include:

- current `psi4demand`
- current `psi4supply`
- capacity master lookup
- route alternatives
- current scenario metadata
- evaluation result
- management policy

```python
@dataclass
class HandleReplanCommandResult:
    replan_command: ReplanCommand
    action_taken: str
    next_command: str
    message: str = ""
    next_command_parameters: dict = field(default_factory=dict)
```

---

### 6.3 Suggested command function

```python
def handle_replan_command(
    command_input: HandleReplanCommandInput,
) -> HandleReplanCommandResult:
    ...
```

### 6.4 Routing rules

Recommended initial routing:

```text
suggested_action = rerun_backward_planning:
    next_command = run_backward_capacity_aware_demand_allocation

suggested_action = adjust_demand_allocation:
    next_command = run_backward_capacity_aware_demand_allocation

suggested_action = select_alternative_route:
    next_command = select_alternative_route_or_node

suggested_action = escalate_to_management:
    next_command = generate_management_issues

suggested_action = review_capacity_master:
    next_command = generate_management_issues or log_only

suggested_action = log_only:
    next_command = none
```

### 6.5 Example

```text
Forward Simulation detects:
    MOM_CHINA / 2026-W08 / P capacity exceeded

Forward Simulation emits:
    ReplanCommand(
        trigger_source="capacity_consistency_validation",
        node_or_flow_name="MOM_CHINA",
        week="2026-W08",
        violation_type="capacity_exceeded",
        severity="blocking",
        suggested_action="rerun_backward_planning",
        message="Forward simulation exceeded allocated capacity bucket."
    )

handle_replan_command routes to:
    run_backward_capacity_aware_demand_allocation
```

---

---

### 6.6 Replan Loop Guard Policy

A replan command may trigger a new planning cycle.

However, WOM must avoid infinite replan loops.

Typical loop risk:

```text
Forward Simulation
    ↓
capacity_exceeded
    ↓
ReplanCommand(severity="blocking", suggested_action="rerun_backward_planning")
    ↓
handle_replan_command
    ↓
run_backward_capacity_aware_demand_allocation
    ↓
Forward Simulation again
    ↓
same capacity_exceeded
    ↓
same ReplanCommand
    ↓
infinite replan loop
```

Minimum loop guard policy:

```text
IF the same violation recurs after replan:
    downgrade severity from blocking to warning
    next_command = generate_management_issues
    message = "Replanning did not resolve the violation. Escalating."
```

Recommended recurrence key:

```text
scenario_id
product_name
node_or_flow_name
week
violation_type
suggested_action
```

Suggested implementation fields for future command context:

```python
replan_attempt_count: int = 0
max_replan_attempts: int = 1
previous_replan_keys: set[str] = field(default_factory=set)
```

Routing policy:

```text
first occurrence:
    route according to suggested_action

same violation after replan:
    stop automatic replanning
    escalate to Management Issue Generation

same violation after max_replan_attempts:
    severity = warning or blocking_escalated
    next_command = generate_management_issues
```

This keeps WOM from repeatedly executing the same planning cycle without resolving the root constraint.


## 7. Constraint and Alternative Route Commands

These commands prepare the feasible network before capacity allocation.

### 7.1 `detect_e2e_constraints`

#### Purpose

Detect constraint candidates in the E2E network.

#### Input

```text
scenario_id
product_name
weeks
nodes
flows / lanes
capacity_master
route_master
```

#### Process

```text
1. scan node capacity
2. scan flow / lane capacity
3. detect capacity = 0
4. detect unavailable node / lane / port
5. detect leadtime increase or route block
6. classify constraint candidates
```

#### Output

```python
@dataclass
class ConstraintDetectionResult:
    scenario_id: str
    product_name: str
    constraint_candidates: list[dict] = field(default_factory=list)
    fully_infeasible: bool = False
    partially_infeasible: bool = False
    message: str = ""
```

---

### 7.2 `select_alternative_route_or_node`

#### Purpose

Select feasible alternative route / node before bottleneck identification and allocation.

This command implements the principle:

```text
route before allocation
```

#### Input

```text
constraint candidates
route alternatives
node alternatives
capacity master
leadtime assumptions
cost assumptions
```

#### Process

```text
1. check blocked route / node
2. search feasible route alternatives
3. search feasible node alternatives
4. evaluate capacity / leadtime / cost
5. split full infeasibility and partial infeasibility
```

#### Output

```python
@dataclass
class AlternativeSelectionResult:
    scenario_id: str
    product_name: str
    feasible_routes: list[dict] = field(default_factory=list)
    blocked_routes: list[dict] = field(default_factory=list)
    feasible_nodes: list[dict] = field(default_factory=list)
    blocked_nodes: list[dict] = field(default_factory=list)
    fully_infeasible: bool = False
    partially_infeasible: bool = False
    generated_management_issue_inputs: list[dict] = field(default_factory=list)
```

### 7.3 Full and partial infeasibility handling

```text
fully infeasible:
    skip Bottleneck Identification
    skip Capacity Allocation
    skip E2E Evaluation
    generate Management Issue directly

partially infeasible:
    blocked portion → Management Issue Generation
    feasible portion → continue to Bottleneck Identification
```

---

## 8. Backward Planning Commands

Backward Planning commands work mainly on `psi4demand`.

They are responsible for capacity-aware demand allocation, advance production, and bottleneck capacity bucket assignment.

---

### 8.1 `run_backward_capacity_aware_demand_allocation`

#### Purpose

Run capacity-aware demand allocation from market demand to E2E capacity buckets.

#### Responsibility

```text
Backward Planning / psi4demand
```

#### Input

```text
scenario_id
product_name
planning weeks
market demand lots
routing / leadtime
capacity master
alternative route / node result
allocation policy
```

#### Process

```text
1. read market demand lots
2. perform outbound demand placement:
       leaf node → DAD node
3. bridge:
       MOM S = DAD P
4. perform inbound demand placement:
       MOM node → inbound leaf node
5. identify capacity bucket for each demand lot
6. check bottleneck capacity limits
7. apply allocation policy if required
8. perform advance production placement if target week is full
9. record unallocated / backlog candidate lots
```

#### Output

```python
@dataclass
class BackwardDemandAllocationResult:
    scenario_id: str
    product_name: str
    allocated_lots_by_bucket: dict = field(default_factory=dict)
    mom_s_equals_dad_p_bridge_summary: dict = field(default_factory=dict)
    advanced_production_lots: dict = field(default_factory=dict)
    unallocated_lots: dict = field(default_factory=dict)
    backlog_candidate_lots: dict = field(default_factory=dict)
    capacity_usage_records: list[Any] = field(default_factory=list)
    capacity_violation_records: list[Any] = field(default_factory=list)
    generated_replan_commands: list[ReplanCommand] = field(default_factory=list)
```

---

### 8.2 `bridge_mom_s_from_dad_p`

#### Purpose

Bridge outbound demand placement into inbound demand placement.

In WOM Backward Planning, DAD production demand is copied to MOM shipment demand.

The correct direction is:

```text
MOM S = DAD P
```

not `DAD P = MOM S`.

#### Why this matters

Backward Planning first allocates demand on the outbound side:

```text
market leaf → DAD
```

This determines DAD-side production requirement:

```text
DAD P
```

Then the inbound side receives this as MOM shipment requirement:

```text
MOM S = DAD P
```

After this bridge, inbound demand allocation proceeds:

```text
MOM node → inbound leaf node
```

#### Input

```text
dad_node
mom_node
product_name
week
dad_p_lots
```

#### Process

```text
1. read DAD P lots
2. copy DAD P lot IDs to MOM S demand bucket
3. preserve lot identity
4. keep traceability from DAD node to MOM node
```

#### Output

```python
@dataclass
class MomSFromDadPBridgeResult:
    dad_node: str
    mom_node: str
    product_name: str
    week: str
    bridged_lots: list = field(default_factory=list)
    source_bucket: str = "DAD.P"
    target_bucket: str = "MOM.S"
```

---

### 8.3 `allocate_demand_to_capacity_bucket`

#### Purpose

Assign demand lots to a specific node / flow / week capacity bucket.

#### Input

```text
node_or_flow
week
product_name
capacity_type
candidate_lots
capacity_limit_qty
allocation_rule
```

#### Process

```text
1. compare candidate lot count with capacity limit
2. if within capacity:
       allocate all lots
3. if over capacity:
       apply bottleneck_allocation policy
       accepted lots → capacity bucket
       overflow lots → overflow list
```

#### Output

```python
@dataclass
class CapacityBucketAllocationResult:
    bucket_key: tuple
    accepted_lots: list = field(default_factory=list)
    overflow_lots: list = field(default_factory=list)
    allocation_rule: str = "FIFO"
    capacity_limit_qty: int | None = None
```

---

### 8.4 `advance_production`

#### Purpose

Move demand placement earlier in time when target-week capacity is full.

#### Why Backward Planning owns this

Forward Planning cannot naturally revise past production placement after time has moved forward.

Backward Planning can naturally search earlier weeks.

#### Input

```text
target_week
candidate_lots
node_or_flow
product_name
capacity_type
advance_window_weeks
capacity master
allocation rule
```

#### Process

```text
1. start from target_week
2. if target_week bucket is full:
       search target_week - 1
3. continue backward within advance_window_weeks
4. allocate lots to earliest feasible bucket according to policy
5. if no bucket is available:
       mark lots as unallocated / backlog candidate
```

#### Output

```python
@dataclass
class AdvanceProductionResult:
    original_week: str
    allocated_week_by_lot: dict = field(default_factory=dict)
    advanced_lots: list = field(default_factory=list)
    unallocated_lots: list = field(default_factory=list)
    message: str = ""
```

---

### 8.5 `reallocate_mom_assignment`

#### Purpose

Reassign demand lots to alternative MOM or supply node when the original MOM is constrained or unavailable.

#### Input

```text
candidate_lots
original_mom
alternative_moms
capacity master
leadtime assumptions
cost assumptions
allocation policy
```

#### Process

```text
1. check original MOM feasibility
2. search alternative MOM candidates
3. evaluate capacity / leadtime / cost
4. allocate lots to feasible MOM
5. record unallocated lots if no MOM is feasible
```

#### Output

```python
@dataclass
class MomReallocationResult:
    original_mom: str
    assigned_mom_by_lot: dict = field(default_factory=dict)
    unallocated_lots: list = field(default_factory=list)
    allocation_summary: dict = field(default_factory=dict)
```

---

## 9. Forward Simulation Commands

Forward Simulation commands work mainly on `psi4supply`.

They simulate supply movement, validate consistency, and emit replan commands when residual inconsistencies remain.

---

### 9.1 `run_forward_supply_simulation`

#### Purpose

Run supply simulation based on demand allocation results.

#### Responsibility

```text
Forward Planning / psi4supply
```

#### Input

```text
scenario_id
product_name
allocated psi4demand state
routing
leadtime
inventory initial state
cost master
price master
capacity master
```

#### Process

```text
1. read allocated demand state from psi4demand
2. simulate production / shipment / inventory movement
3. update psi4supply
4. calculate inventory movement
5. calculate sales / shipment timing
6. calculate cost / profit if cost master exists
7. validate residual capacity consistency
```

#### Output

```python
@dataclass
class ForwardSimulationResult:
    scenario_id: str
    product_name: str
    psi4supply_snapshot: dict = field(default_factory=dict)
    inventory_summary: dict = field(default_factory=dict)
    shipment_summary: dict = field(default_factory=dict)
    cost_profit_summary: dict = field(default_factory=dict)
    capacity_consistency_violations: list[dict] = field(default_factory=list)
    generated_replan_commands: list[ReplanCommand] = field(default_factory=list)
```

---

### 9.2 `validate_forward_capacity_consistency`

#### Purpose

Check whether Forward Simulation output remains consistent with capacity constraints and Backward demand allocation.

#### Input

```text
psi4demand
psi4supply
capacity master
allocation result
forward simulation result
```

#### Process

```text
1. compare planned demand placement vs simulated supply movement
2. check capacity usage against capacity_limit_qty
3. detect route unavailable after simulation
4. detect allocation inconsistency
5. detect inventory over capacity
6. emit ReplanCommand when needed
```

#### Output

```python
@dataclass
class CapacityConsistencyValidationResult:
    is_consistent: bool
    violations: list[dict] = field(default_factory=list)
    generated_replan_commands: list[ReplanCommand] = field(default_factory=list)
```

---

## 10. E2E Evaluation Commands

E2E Evaluation commands calculate KPI outputs and baseline-vs-scenario deltas.

---

### 10.1 `run_e2e_evaluation`

#### Purpose

Evaluate E2E planning result using WOM KPI Registry.

#### Input

```text
scenario_id
baseline_scenario_id
product_name
planning horizon
constraint result
alternative selection result
backward allocation result
forward simulation result
KPI registry
KPI weight profile
```

#### Process

```text
1. calculate node-level KPIs
2. calculate supply-point-level KPIs
3. calculate total supply chain KPIs
4. calculate strategic KPIs
5. compare with baseline if available
6. create KPIDelta records
7. prepare management_issue_inputs
```

#### Output

```python
@dataclass
class KPIDelta:
    kpi_id: str
    baseline_value: float | None
    scenario_value: float | None
    delta: float | None
    delta_ratio: float | None
    direction: str
    significance: str


@dataclass
class E2EEvaluationResult:
    scenario_id: str
    product_name: str
    evaluation_start_week: str
    evaluation_end_week: str

    is_baseline: bool = False
    baseline_scenario_id: str = ""

    kpi_registry_version: str = ""
    kpi_weight_profile: dict = field(default_factory=dict)

    constraint_summary: dict = field(default_factory=dict)
    alternative_route_summary: dict = field(default_factory=dict)
    bottleneck_summary: dict = field(default_factory=dict)
    allocation_summary: dict = field(default_factory=dict)

    node_kpis: dict = field(default_factory=dict)
    supply_point_kpis: dict = field(default_factory=dict)
    total_sc_kpis: dict = field(default_factory=dict)
    strategic_kpis: dict = field(default_factory=dict)

    kpi_delta_vs_baseline: dict[str, KPIDelta] = field(default_factory=dict)
    management_issue_inputs: dict = field(default_factory=dict)
```

---

### 10.2 `compare_evaluation_to_baseline`

#### Purpose

Compare scenario evaluation result against baseline evaluation result.

#### Input

```text
baseline E2EEvaluationResult
scenario E2EEvaluationResult
KPI registry
direction rules
significance thresholds
```

#### Process

```text
1. match KPI IDs
2. calculate scenario - baseline delta
3. calculate delta ratio
4. determine direction:
       improved / worsened / unchanged / not_applicable
5. determine significance:
       critical / warning / info / none
```

#### Output

```python
list[KPIDelta]
```

`KPIDelta` is defined in Section 10.1 and should not be redefined here.

The comparison command returns one `KPIDelta` record per evaluated KPI.

Conceptual result:

```python
@dataclass
class EvaluationComparisonResult:
    baseline_scenario_id: str
    scenario_id: str
    kpi_deltas: dict[str, KPIDelta] = field(default_factory=dict)
```


---

## 11. Management Issue Generation Commands

Management Issue Generation converts structured evaluation results into management issues.

---

### 11.1 `generate_management_issues`

#### Purpose

Generate management issue records from E2E evaluation result.

#### Input

```text
E2EEvaluationResult
issue rules
severity thresholds
management policy
```

#### Process

```text
1. read management_issue_inputs
2. read kpi_delta_vs_baseline
3. classify bottleneck / route / capacity / profit / service issues
4. assign severity
5. generate issue summary
6. generate possible actions
7. prepare optional LLM summarization input
```

#### Output

```python
@dataclass
class ManagementIssue:
    issue_id: str
    scenario_id: str
    issue_type: str
    severity: str
    title: str
    impact_summary: str
    affected_nodes: list[str] = field(default_factory=list)
    affected_flows: list[str] = field(default_factory=list)
    affected_markets: list[str] = field(default_factory=list)
    related_kpis: list[str] = field(default_factory=list)
    possible_actions: list[str] = field(default_factory=list)
    llm_summary_input: dict = field(default_factory=dict)
```

---

### 11.2 Issue type examples

```text
NO_FEASIBLE_ROUTE
PARTIAL_ROUTE_BLOCK
ACTIVE_BOTTLENECK
CAPACITY_OVERLOAD
RESIDUAL_CAPACITY_INCONSISTENCY
BACKLOG_INCREASE
FILL_RATE_DROP
PROFIT_MARGIN_DROP
CAPACITY_RESILIENCE_WEAKNESS
INVENTORY_OVER_CAPACITY
```

---

## 12. End-to-End Command Flow

### 12.1 Standard planning flow

```text
detect_e2e_constraints
    ↓
select_alternative_route_or_node
    ↓
run_backward_capacity_aware_demand_allocation
    ↓
run_forward_supply_simulation
    ↓
validate_forward_capacity_consistency
    ↓
run_e2e_evaluation
    ↓
generate_management_issues
```

### 12.2 Fully infeasible flow

```text
detect_e2e_constraints
    ↓
select_alternative_route_or_node
    ↓
fully infeasible
    ↓
generate_management_issues
```

### 12.3 Partially infeasible flow

```text
detect_e2e_constraints
    ↓
select_alternative_route_or_node
    ↓
split blocked portion and feasible portion
    ↓
blocked portion:
    generate_management_issues

feasible portion:
    run_backward_capacity_aware_demand_allocation
    ↓
    run_forward_supply_simulation
    ↓
    run_e2e_evaluation
    ↓
    generate_management_issues
```

### 12.4 Replan flow

```text
run_forward_supply_simulation
    ↓
validate_forward_capacity_consistency
    ↓
ReplanCommand emitted
    ↓
handle_replan_command
    ↓
rerun backward planning
or select alternative route
or escalate to management
```

---

## 13. Suggested CLI / Runner Commands

Initial implementation should be verified by CLI / runner, not GUI.

Suggested runner names:

```text
pysi/runners/run_wom_constraint_detection_smoke.py
pysi/runners/run_wom_alternative_route_selection_smoke.py
pysi/runners/run_wom_backward_capacity_allocation_smoke.py
pysi/runners/run_wom_forward_simulation_validation_smoke.py
pysi/runners/run_wom_e2e_evaluation_smoke.py
pysi/runners/run_wom_management_issue_generation_smoke.py
pysi/runners/run_wom_replan_command_handling_smoke.py
```

---

## 14. Output Artifacts

Recommended output folder:

```text
outputs/planning_operations/
```

Suggested outputs:

```text
constraint_detection_result.json
alternative_selection_result.json
backward_allocation_result.json
forward_simulation_result.json
capacity_consistency_validation_result.json
e2e_evaluation_result.json
management_issues.json
replan_commands.json
```

CSV outputs may also be created for review:

```text
capacity_usage.csv
capacity_violation.csv
kpi_delta_vs_baseline.csv
management_issue_list.csv
```

---

## 15. Initial Implementation Milestones

### m1: Command dataclasses and skeletons

- `PlanningCommand`
- `PlanningCommandResult`
- `ReplanCommand`
- `HandleReplanCommandInput`
- `HandleReplanCommandResult`
- Replan loop guard policy
- `E2EEvaluationResult`
- `ManagementIssue`

### m2: Backward Capacity-Aware Demand Allocation MVP

Scope:

```text
single product
single MOM
multiple weeks
P capacity only
MOM S = DAD P bridge
advance production search
unallocated lot record
```

### m3: Forward Simulation Validation MVP

Scope:

```text
validate capacity consistency
emit ReplanCommand
do not rewrite past demand placement
```

### m4: E2E Evaluation MVP

Scope:

```text
read KPI registry
calculate selected KPIs
calculate KPIDelta vs baseline
produce E2EEvaluationResult
```

### m5: Management Issue Generation MVP

Scope:

```text
read E2EEvaluationResult
classify issues
generate issue records
prepare LLM summary input
```

---

## 16. Out of Scope for This Memo

This memo does not define:

- GUI layout
- Full optimization
- Detailed route scoring formula
- Detailed KPI compute implementation
- LLM prompt design
- Database persistence schema
- Full scenario management UI

These should be handled in later design documents.

---

## 17. Summary

The WOM Planning Operations Command layer makes E2E Constraint Management executable.

The core idea is:

```text
Detection:
    find constraints

Selection:
    choose feasible route / node

Backward Planning:
    place demand lots into capacity buckets

Forward Simulation:
    simulate supply movement and validate consistency

E2E Evaluation:
    evaluate KPI impact and baseline delta

Management Issue Generation:
    translate evaluation result into executive issues and actions
```

Most important principles:

1. **Commands are explicit and auditable.**
2. **Backward Planning owns capacity-aware demand allocation.**
3. **Backward Planning bridges outbound and inbound demand by `MOM S = DAD P`.**
4. **Forward Planning owns simulation and consistency validation.**
5. **Forward Planning emits `ReplanCommand` instead of silently rewriting the past.**
6. **`handle_replan_command` routes replan signals to the next operation command.**
7. **E2E Evaluation uses KPI Registry and produces structured `E2EEvaluationResult`.**
8. **`kpi_delta_vs_baseline` should use `dict[str, KPIDelta]`.**
9. **`KPIDelta` should be defined once and reused by evaluation comparison commands.**
10. **Management Issue Generation consumes structured evaluation results and produces issue records.**
11. **Full infeasibility and partial infeasibility are handled differently.**
12. **`handle_replan_command` must include a loop guard to avoid infinite replan cycles.**
13. **Initial implementations should be smoke-runner based before GUI integration.**
