# WOM E2E Constraint Management Design Memo

**Version:** v0r3 revised with KPI Registry Alignment, Replan Command, and Partial Feasibility Handling
**Date:** 2026-05-13
**Status:** Design memo

---

## 1. Purpose

This memo defines the E2E constraint management concept in WOM.

The purpose is to clarify the relationship between:

```text
Buffer
Constraint
Bottleneck
Alternative Route / Node Selection
Capacity Allocation at Bottleneck
E2E Evaluation
Management Issue Generation
```

This memo also clarifies:

```text
the role of bottleneck_allocation.py
the responsibility boundary between Backward Planning and Forward Planning
the relationship between E2E Evaluation and WOM KPI Registry
the role of replan command
the handling of full infeasibility vs partial infeasibility
```

---

## 2. Key Principle

In WOM, a buffer is not automatically a bottleneck.

An outbound buffer inventory point normally has enough capacity to absorb demand variation.

Therefore, it should be understood as:

```text
demand variation absorption point
inventory buffer
decoupling point
```

not as a bottleneck.

A bottleneck is the E2E system constraint that limits the overall flow of lots.

The bottleneck may appear in:

```text
inbound process
MOM production capacity
material supply
logistics lane
port
customs
transport mode
cold chain storage
```

The location of the bottleneck may change by scenario.

---

## 3. Buffer vs Bottleneck

### 3.1 Buffer

A buffer absorbs variation.

Examples:

```text
DAD inventory
market inventory
safety stock
transport inventory
cold chain buffer stock
```

A buffer is normally designed to have enough capacity to absorb demand and supply variation.

It is not a bottleneck under normal conditions.

However, under extraordinary events such as port shutdown, logistics disruption, or lane capacity becoming zero, a buffer node or logistics lane may become an active constraint.

### 3.2 Bottleneck

A bottleneck constrains E2E throughput.

Examples:

```text
minimum capacity process
slowest inbound node
port closure
lane capacity = 0
MOM capacity shortage
material shortage
transport constraint
```

A bottleneck is not defined by tree side.

It is defined by whether the point limits E2E flow relative to actual demand.

Important:

```text
A node / flow with the minimum capacity_limit is an active bottleneck
only when actual demand lot inflow exceeds its capacity_limit in that week.
```

If total demand is below all capacity limits:

```text
IF total demand lots/week < MIN(capacity_limit lots/week) across all nodes / flows:
    → No active bottleneck exists in that week
    → E2E flow is unconstrained
```

Therefore, bottleneck status is a function of both capacity structure and demand volume.

---

## 4. E2E Constraint Management Process

The recommended WOM process is:

```text
1. Constraint Detection
2. Alternative Route / Alternative Node Selection
3. Bottleneck Identification
4. Capacity Allocation at Bottleneck
5. E2E Evaluation
6. Management Issue Generation
```

Planning responsibility:

```text
Steps 1-4:
    primarily Backward Planning / psi4demand responsibility

Steps 5-6:
    shared by Backward Planning output and Forward Planning / psi4supply validation

Forward Planning:
    detects residual capacity violations as Capacity Consistency Validation
    and triggers replan command if needed
```

---

## 5. Step 1: Constraint Detection

Constraint Detection searches the E2E network for constraint candidates.

Target examples:

```text
node capacity shortage
lane capacity shortage
lane capacity = 0
port closure
customs delay
transport leadtime increase
MOM unavailable
warehouse unavailable
material shortage
cold storage unavailable
```

At this stage, WOM detects constraint candidates.

Not every constraint candidate is the final bottleneck.

---

## 6. Step 2: Alternative Route / Alternative Node Selection

If a strong physical constraint exists, such as:

```text
lane capacity = 0
port closed
node unavailable
customs blocked
```

then alternative route or alternative node selection should be performed before capacity allocation.

Reason:

If the route or node changes, then the following may also change:

```text
leadtime
cost
available capacity
arrival week
assigned MOM
assigned DAD
transport mode
```

Therefore, WOM should first decide the feasible route / node structure.

Example:

```text
Hormuz lane capacity = 0
    ↓
select alternative sea lane
or select alternative air lane
or select alternative port
or select alternative regional DC
```

The principle is:

```text
route before allocation
```

### 6.1 When No Feasible Alternative Exists

If no feasible route or node is found after Step 2, for example:

```text
all routes blocked
no alternative MOM available
no alternative lane available
critical node unavailable
```

WOM should skip Steps 3-5 and proceed directly to Step 6.

```text
IF no feasible route or node found:
    → skip Bottleneck Identification
    → skip Capacity Allocation
    → skip E2E Evaluation
    → generate management issue directly:
      "No feasible route available. Supply is fully blocked."
```

This short-circuit path prevents implementation complexity from spreading across Steps 3-5 when the network is structurally infeasible.

### 6.2 Partial Block and Partial Feasibility

The short-circuit path in Section 6.1 should be applied only when the entire relevant E2E network is structurally infeasible.

In real scenarios, constraints may be partial.

Example:

```text
MOM_CHINA → DAD_US:
    lane capacity = 0
    blocked

MOM_CHINA → DAD_EU:
    alternative route available
    feasible
```

In such cases, WOM should not stop the entire E2E evaluation.

Recommended behavior:

```text
IF constraint is partial:
    blocked routes / blocked node pairs:
        generate management issue for the blocked portion

    feasible routes / feasible node pairs:
        continue to Bottleneck Identification
        continue to Capacity Allocation if needed
        continue to E2E Evaluation
```

Only the infeasible sub-network should be short-circuited.

The feasible sub-network should remain in the planning and evaluation flow.

This distinction is important for multi-market, multi-MOM, and multi-lane WOM scenarios.

Conceptual rule:

```text
full infeasibility:
    skip Steps 3-5 and generate management issue directly

partial infeasibility:
    split the network into blocked portion and feasible portion
    blocked portion → Management Issue Generation
    feasible portion → continue normal E2E Constraint Management flow
```

This avoids treating a partial logistics disruption as a full E2E supply chain shutdown.

---

## 7. Step 3: Bottleneck Identification

After alternative route / node selection, WOM identifies the actual E2E bottleneck.

### 7.1 Definition

WOM defines each node / flow as having:

```text
capacity_limit_lots_per_week
```

The primary bottleneck candidate is identified as:

```text
bottleneck_candidate = argmin(capacity_limit_lots_per_week)
                       across E2E nodes and flows
```

This is consistent with WOM's weekly bucket structure and MEO lot-based flow model.

### 7.2 Active Bottleneck Condition

A bottleneck candidate becomes an active bottleneck only when:

```text
actual demand lot inflow lots/week > capacity_limit lots/week
```

If demand is below all capacity limits in a given week, no active bottleneck exists and Capacity Allocation at Bottleneck is not required.

If no active bottleneck exists, Capacity Allocation at Bottleneck is skipped.

However, E2E Evaluation should still be performed.

Reason:

```text
no active bottleneck
    does not mean
no evaluation is needed
```

E2E Evaluation should confirm that the plan is feasible and should record the unconstrained or non-bottleneck baseline state.

This is important for scenario comparison.

Example:

```text
Scenario A:
    no active bottleneck
    capacity utilization is low
    fill rate is high

Scenario B:
    active bottleneck exists
    capacity allocation is required
    backlog or delay occurs
```

Both scenarios should produce `E2EEvaluationResult` so that WOM can compare them.

### 7.3 Relationship with Backward Planning

Backward Planning / psi4demand is responsible for resolving demand lot concentration at bottleneck nodes in advance, including advance production placement.

The Backward Planning flow is:

```text
Outbound tree:
    leaf node → DAD node
    demand allocation

DAD P = MOM S:
    demand copy / bridge

Inbound tree:
    MOM node → inbound leaf node
    demand allocation

At bottleneck:
    advance production placement if capacity_limit is exceeded in target week
```

Therefore, when Forward Planning / psi4supply runs, demand lots should already be allocated within capacity limits.

Forward Planning detects residual capacity violations as part of Capacity Consistency Validation and triggers a replan command if violations remain.

### 7.4 Current Implementation Policy

In the current design stage, static MIN identification is used:

```text
bottleneck_candidate = argmin(capacity_limit_lots_per_week)
```

Future versions may extend this with active bottleneck confirmation by comparing actual weekly demand lot inflow against capacity_limit.

However, in WOM's standard planning sequence, demand lot concentration should be handled by Backward Planning before Forward Planning runs.

---

## 8. Step 4: Capacity Allocation at Bottleneck

Capacity Allocation should be applied at the identified active bottleneck, not at every constraint candidate.

The process is:

```text
identify active bottleneck
    ↓
collect candidate demand lots
    ↓
check available capacity_limit lots/week
    ↓
apply allocation rule
    ↓
accepted lots → assigned to bottleneck capacity bucket
    ↓
overflow lots → recorded as blocked / backlog / alternative candidates
```

The current v0r3 module:

```text
pysi/planning/bottleneck_allocation.py
```

should be understood as:

```text
E2E bottleneck lot allocation policy library
```

It currently supports:

```text
FIFO
LOT_PRIORITY
DUE_WEEK_PRIORITY
```

This module can be reused wherever WOM needs to order lots at a constrained E2E bottleneck, whether at an inbound process, a logistics lane, or an emergency constraint point.

The module is one policy component inside E2E Constraint Management.

It does not define the full E2E constraint process by itself.

---

## 9. Step 5: E2E Evaluation

After bottleneck allocation, WOM evaluates the E2E result.

This step is called:

```text
E2E Evaluation
```

not Impact Propagation.

Reason:

The purpose is not to propagate an impact automatically.

The purpose is to evaluate the result of constraints, route changes, and allocation across the full E2E supply chain.

---

## 10. E2E Evaluation and WOM KPI Registry

E2E Evaluation should not define KPIs ad hoc.

It should use the WOM KPI Registry as the canonical KPI definition layer.

The KPI Registry is designed to manage KPI definitions as data, and to handle KPI levels such as:

```text
node
supply_point
total_sc
strategic
```

E2E Evaluation should calculate and compare KPIs across these four levels.

```text
E2E Evaluation =
    constraint / route / allocation results
    evaluated through WOM KPI Registry
    across node / supply_point / total_sc / strategic levels
```

### 10.1 Node Level Evaluation

Node-level KPIs evaluate local operational effects.

Examples:

```text
node.production_qty
node.shipment_qty
node.ending_inventory_qty
node.backlog_qty
node.capacity_utilization
node.stockout_qty
node.fill_rate
node.inventory_days
node.sales_amount
node.production_cost
node.logistics_cost
node.gross_profit_contribution
```

Typical use in E2E Constraint Management:

```text
Which node is constrained?
How much capacity is used?
How many lots are blocked?
How much inventory remains?
How much local profit contribution is affected?
```

### 10.2 Supply Point Level Evaluation

Supply Point KPIs evaluate the interaction between inbound supply and outbound demand.

Examples:

```text
supply_point.inbound_material_shortage_qty
supply_point.outbound_demand_qty
supply_point.outbound_sales_qty
supply_point.outbound_fill_rate
supply_point.outbound_stockout_qty
supply_point.market_priority_compliance
supply_point.demand_supply_gap_qty
supply_point.demand_supply_gap_rate
supply_point.decoupling_inventory_qty
supply_point.weekly_psi_balance_score
supply_point.profit_contribution
supply_point.cash_pressure
```

Typical use:

```text
Did inbound shortage affect outbound fulfillment?
Did supply point inventory absorb demand variation?
Did capacity allocation follow market priority?
Did demand and feasible supply diverge?
```

### 10.3 Total Supply Chain Level Evaluation

Total Supply Chain KPIs evaluate E2E performance.

Examples:

```text
total_sc.production_qty
total_sc.shipment_sales_qty
total_sc.ending_inventory_qty
total_sc.backlog_qty
total_sc.fill_rate
total_sc.stockout_rate
total_sc.inventory_value
total_sc.capacity_utilization
total_sc.capacity_concentration_index
total_sc.lead_time
total_sc.plan_stability_score
total_sc.sales_amount
total_sc.variable_cost
total_sc.gross_profit
total_sc.operating_profit
total_sc.profit_margin
total_sc.cash_conversion_pressure
total_sc.roi_proxy
```

Typical use:

```text
How much E2E flow was constrained?
Where is capacity concentrated?
How much backlog or stockout was created?
What was the total profit / cost / cash impact?
```

### 10.4 Strategic Level Evaluation

Strategic KPIs connect planning results to WOM's strategic objectives.

Examples:

```text
strategic.customer_fulfillment_score
strategic.employee_workload_health_score
strategic.supplier_stability_score
strategic.balanced_stakeholder_score
strategic.profit_sustainability_score
strategic.inventory_soundness_score
strategic.capacity_resilience_score
strategic.cash_sustainability_score
strategic.structural_sustainability_score
```

Typical use:

```text
Does the plan maintain customer fulfillment?
Does it avoid excessive capacity stress?
Does it preserve supplier stability?
Does it improve cost structure resilience?
Does it support long-term business sustainability?
```

### 10.5 KPI Registry Alignment Requirements

E2E Evaluation depends on WOM KPI Registry.

Therefore, the KPI Registry should be aligned with E2E Constraint Management.

#### 10.5.1 capacity_limit_lots_per_week as Canonical Capacity Reference

Bottleneck Identification uses:

```text
capacity_limit_lots_per_week
```

as the reference value for identifying the minimum throughput point across E2E nodes and flows.

However, `capacity_limit_lots_per_week` is not originally a performance result KPI.

It is a capacity constraint parameter.

Therefore, WOM should distinguish:

```text
capacity_limit_qty:
    master / constraint parameter

capacity_utilization:
    KPI calculated from used capacity and capacity_limit_qty
```

Recommended policy:

```text
Source of truth:
    capacity_master.csv / capacity I/O layer

Evaluation reference:
    E2E Evaluation may expose capacity_limit_qty as a read-only reference metric

KPI:
    capacity_utilization, capacity_concentration_index, backlog_qty, fill_rate, etc.
```

This keeps the boundary clear between:

```text
capacity master value
```

and:

```text
performance KPI
```

Recommended capacity reference definition for node capacity:

```python
id="node.capacity_limit_qty"
label="Node Capacity Limit (lots/week)"
level="node"
scope="node"
value_type="qty"
unit="lots/week"
description="Weekly processing capacity limit of the node. This is a constraint parameter referenced by bottleneck identification."
formula_text="lookup_capacity_master(node, product, week, capacity_type)"
```

For flow / lane constraints:

```python
id="flow.capacity_limit_qty"
label="Flow Capacity Limit (lots/week)"
level="flow"
scope="flow"
value_type="qty"
unit="lots/week"
description="Weekly flow or lane capacity limit. This is a constraint parameter referenced by logistics bottleneck identification."
formula_text="lookup_capacity_master(flow, product, week, capacity_type)"
```

Important:

```text
capacity_limit_qty may be exposed through the registry for evaluation consistency,
but it should be treated as a reference metric / constraint parameter,
not as a result KPI.
```

The actual KPI is, for example:

```text
node.capacity_utilization = used_capacity_qty / capacity_limit_qty
```

This connects the E2E bottleneck definition:

```text
bottleneck_candidate = argmin(capacity_limit_lots_per_week)
```

with the canonical capacity master / capacity I/O layer, without confusing master data and KPI results.

#### 10.5.2 Strategic KPI Weighting Should Be Scenario-Configurable

Strategic KPIs may aggregate multiple lower-level indicators.

For example:

```text
balanced_stakeholder_score
capacity_resilience_score
profit_sustainability_score
structural_sustainability_score
```

These scores should not hard-code management weights in the compute function.

Recommended policy:

```text
weights should be read from scenario context / management policy / evaluation context
```

Example:

```python
w_customer = float(ctx.get("w_customer", 0.4))
w_employee = float(ctx.get("w_employee", 0.3))
w_supplier = float(ctx.get("w_supplier", 0.3))
```

Reason:

WOM is a management intention tool.

Different scenarios may intentionally use different evaluation weights.

Examples:

```text
customer fulfillment priority scenario
cash preservation scenario
supplier stability scenario
capacity resilience scenario
profit margin priority scenario
```

Therefore, strategic KPI weights should be part of scenario / management policy input.

#### 10.5.3 Strategic KPI Grain Convention

Strategic KPIs should use a consistent grain.

Recommended default:

```text
strategic grain = ("total_sc", "horizon")
```

Reason:

Strategic KPIs evaluate the entire supply chain or business strategy over an evaluation horizon.

Market-level or supply-point-level evaluation should be handled at lower KPI levels:

```text
market / channel view:
    supply_point level

node view:
    node level

E2E strategic view:
    strategic level
```

This keeps KPI storage keys simple and avoids mixing market-specific and total supply chain strategic indicators in the same layer.

If market-specific strategic evaluation becomes necessary later, it should be introduced explicitly as a separate scope, not mixed into the default strategic grain.

Recommended convention:

```text
node:
    ("product", "node", "week")

supply_point:
    ("product", "supply_point", "week")

total_sc:
    ("product", "week")

strategic:
    ("total_sc", "horizon")
```

---

## 11. E2E Evaluation Output Structure

E2E Evaluation produces a structured evaluation result.

This result becomes the direct input to Management Issue Generation and future LLM-based natural language summarization.

Suggested dataclasses:

```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KPIDelta:
    kpi_id: str
    baseline_value: Optional[float]
    scenario_value: Optional[float]
    delta: Optional[float]
    delta_ratio: Optional[float]
    direction: str
    significance: str
```

Field meanings:

```text
kpi_id:
    KPI identifier such as total_sc.fill_rate or strategic.capacity_resilience_score

baseline_value:
    KPI value in baseline scenario

scenario_value:
    KPI value in current scenario

delta:
    scenario_value - baseline_value

delta_ratio:
    delta / baseline_value, if baseline_value is not zero

direction:
    improved / worsened / unchanged / not_applicable

significance:
    critical / warning / info / none
```

Suggested E2E Evaluation result:

```python
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

`management_issue_inputs` contains pre-classified inputs for Management Issue Generation.

Expected contents include:

```text
bottleneck_node
bottleneck_flow
blocked_lots
affected_markets
affected_supply_points
severity
suggested_actions
```

The formal structure of `management_issue_inputs` will be defined in the Management Issue Generation design memo.

`is_baseline` indicates whether this result itself is the baseline evaluation.

`baseline_scenario_id` identifies the baseline scenario used for comparison.

Recommended usage:

```text
Baseline result:
    scenario_id = "BASE"
    is_baseline = True
    baseline_scenario_id = ""

Scenario result:
    scenario_id = "HORMUZ_BLOCK"
    is_baseline = False
    baseline_scenario_id = "BASE"
```

This allows WOM to clearly express:

```text
this scenario was evaluated against which baseline
```

and supports:

```text
Baseline vs Scenario comparison
Management Issue Generation
LLM-based scenario summary
```

`kpi_registry_version` identifies the KPI definition set used for the evaluation.

`kpi_weight_profile` stores scenario-specific evaluation weights.

Examples:

```text
customer fulfillment priority
capacity resilience priority
cash preservation priority
profit sustainability priority
```

This allows Management Issue Generation to explain not only what happened, but also why the issue is important under the selected management intention.

`kpi_delta_vs_baseline` is one of the most important fields for WOM.

Reason:

```text
Baseline vs Scenario comparison
    ↓
KPI delta detection
    ↓
management issue classification
    ↓
LLM-based natural language summarization
```

This structure allows WOM to identify:

```text
which KPI changed
how much it changed
whether the change is good or bad
how serious it is
```

Data flow:

```text
Step 5 output → E2EEvaluationResult
Step 6 input  → E2EEvaluationResult
Step 6 output → ManagementIssue list
```

---

## 12. Step 6: Management Issue Generation

Management Issue Generation converts the E2E Evaluation result into management-level issues and recommended actions.

Example:

```text
Issue:
MOM_CHINA W08 production capacity is the current E2E bottleneck.

Impact:
20 lots cannot be allocated within the requested production week.
DAD_US supply will be delayed by 1 week.
Capacity utilization: 100%.
Fill rate impact: -8%.
Gross profit impact: -X.
Capacity resilience score worsened.

Possible actions:
1. advance production to W07
2. shift demand to MOM_VIETNAM
3. use alternative lane
4. prioritize high-margin lots
5. add temporary capacity
```

This is where WOM becomes a management support tool, not only a planning calculator.

Future extension:

```text
structured E2EEvaluationResult
    ↓
rule-based issue classification
    ↓
LLM-based natural language summarization
    ↓
Management Cockpit message
```

---

## 13. Responsibility Boundary: Backward vs Forward Planning

### 13.1 Backward Planning / psi4demand

Backward Planning is responsible for:

```text
demand allocation
outbound tree demand placement: leaf → DAD
DAD P = MOM S copy
inbound tree demand placement: MOM → inbound leaf
capacity bucket assignment
advance production placement at bottleneck
alternative node assignment
unallocated / backlog candidate placement
```

Capacity problems that require advance production should be handled here.

Reason:

Backward Planning can naturally move demand placement earlier in time.

It resolves demand lot concentration at bottleneck nodes before Forward Planning runs.

### 13.2 Forward Planning / psi4supply

Forward Planning is responsible for:

```text
supply simulation
inventory movement simulation
shipment simulation
cost / profit evaluation
KPI evaluation support
capacity consistency validation
issue detection
```

Forward Planning should not become the primary engine for revising past production placement.

If Forward Planning detects a capacity violation, it should trigger a replan command rather than silently rewriting the past.

### 13.3 Replan Command

If Forward Planning detects a residual capacity violation, it should not silently rewrite past demand placement.

Instead, it should emit a replan command.

A replan command is a signal emitted by Forward Planning when the current demand allocation plan appears to violate capacity, route, or allocation consistency constraints.

Minimum definition:

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

Required fields:

```text
trigger_source:
    forward_planning
    capacity_consistency_validation
    e2e_evaluation
    management_issue_generation

node_or_flow_name:
    node / flow / lane where the issue was detected

week:
    planning week where the issue occurred

violation_type:
    capacity_exceeded
    route_unavailable
    allocation_inconsistency
    no_feasible_route
    residual_backlog
    inventory_over_capacity

severity:
    blocking
    warning
    info

suggested_action:
    rerun_backward_planning
    adjust_demand_allocation
    select_alternative_route
    escalate_to_management
    review_capacity_master
```

Important:

```text
A replan command does not modify the plan directly.
```

It requests one of the following actions:

```text
rerun Backward Planning
adjust allocation assumptions
select an alternative route / node
escalate to Management Issue Generation
```

This keeps the responsibility boundary clear.

```text
Forward Planning:
    detects residual inconsistency

Replan Command:
    requests correction

Backward Planning:
    performs demand reallocation / advance production / rerouting
```

### 13.4 Replan Command Handling Policy

This memo defines the minimum structure of `ReplanCommand`.

The detailed execution of replan commands should be defined in:

```text
docs/design/wom_planning_operations_commands.md
```

At this design stage, WOM only defines the expected handling policy.

Recommended initial handling policy:

```text
severity = blocking:
    route to planning operations command
    candidate action:
        rerun_backward_planning
        select_alternative_route
        escalate_to_management

severity = warning:
    route to Management Issue Generation
    candidate action:
        review_capacity_master
        adjust_demand_allocation

severity = info:
    log as validation result
    optional review
```

Important:

```text
ReplanCommand does not execute the correction by itself.
```

It is a structured signal passed from validation / evaluation to the planning operations layer.

This avoids mixing:

```text
detection
command routing
actual replanning execution
```

inside Forward Planning.

---

## 14. Role of bottleneck_allocation.py

The current v0r3 module:

```text
pysi/planning/bottleneck_allocation.py
```

is not limited to Forward Planning or to inbound processing.

It should be positioned as a reusable policy module for E2E bottleneck allocation.

Possible use cases:

```text
Inbound bottleneck:
    allocate demand lots to constrained production / process capacity

Logistics bottleneck:
    allocate shipment lots to constrained lane / route capacity

Emergency constraint:
    allocate lots to alternative route / node candidates

Backward Planning:
    order lots before assignment to capacity bucket

Forward validation:
    test which lots would pass a capacity gate under a selected policy
```

The module should not define the whole E2E constraint process by itself.

It is one policy component inside E2E Constraint Management.

---

## 15. Relationship with Existing Capacity I/O

The v0r2 capacity I/O layer provides:

```text
capacity_master.csv loader
capacity lookup
CapacityUsage
CapacityViolation
usage / violation CSV export
```

These should be reused by E2E Constraint Management.

Capacity data should remain grounded in:

```text
scenario_id
tree_side
node_name
product_name
week
capacity_type
capacity_qty
cap_mode
unit
priority
calendar_id
comment
```

P/S capacity and I capacity should be handled with different semantics.

```text
P / S capacity:
    weekly flow upper bound

I capacity:
    end-of-week stock upper bound
```

---

## 16. Future Design Topics

Based on this memo, the next design topics are:

```text
1. Capacity / KPI Registry Alignment for E2E Evaluation
   - clarify capacity_limit_qty as capacity master reference, not result KPI
   - expose capacity_limit_qty as reference metric if useful
   - define strategic KPI grain convention
   - externalize strategic KPI weights into scenario / evaluation context

2. WOM Planning Operations Commands
   docs/design/wom_planning_operations_commands.md
   - define replan command handling policy
   - define command dispatcher / handler
   - define backward planning command
   - define forward simulation command
   - define E2E evaluation command
   - define management issue generation command

3. Backward Capacity-Aware Demand Allocation
   - advance production placement
   - MOM allocation
   - bottleneck capacity bucket assignment
   - unallocated / backlog handling

4. Alternative Route / Node Selection
   - feasibility check
   - route scoring
   - fallback to no-feasible-route handling

5. E2E Evaluation Report
   - structured output definition
   - KPI Registry integration
   - KPIDelta calculation
   - baseline vs scenario comparison

6. Management Issue Generation
   - rule-based issue classification
   - severity classification
   - LLM summarization interface
```

The next immediate design memo should be:

```text
docs/design/wom_planning_operations_commands.md
```

However, before implementing E2E Evaluation, WOM should align the KPI / capacity reference definitions with this design.

---

## 17. Summary

The WOM E2E Constraint Management flow is:

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

The most important design principles are:

```text
1. Buffer is not bottleneck.

2. Bottleneck is the current E2E system constraint,
   defined as MIN(capacity_limit lots/week) where demand exceeds capacity.

3. If total demand < all capacity_limits, no active bottleneck exists.

4. Route selection must happen before allocation when physical constraints exist.

5. If no feasible route exists, skip to Management Issue Generation directly.

6. Backward Planning resolves demand lot concentration at bottleneck,
   including advance production, before Forward Planning runs.

7. Forward Planning validates capacity consistency and triggers replan if needed.

8. E2E Evaluation should use WOM KPI Registry as the canonical KPI layer.

9. E2E Evaluation produces a structured result,
   which feeds directly into Management Issue Generation
   and future LLM-based summarization.

10. bottleneck_allocation.py is a policy component,
    not the whole E2E constraint management process.

11. Bottleneck identification depends on a canonical capacity_limit_lots_per_week reference.

12. Strategic KPI weights should be scenario-configurable, not hard-coded.

13. Strategic KPI grain should be standardized as ("total_sc", "horizon") unless explicitly extended.

14. If no active bottleneck exists, Capacity Allocation is skipped, but E2E Evaluation should still run.

15. capacity_limit_qty is primarily a capacity master / constraint parameter, not a result KPI.

16. capacity_utilization is the KPI calculated from capacity usage and capacity_limit_qty.

17. kpi_delta_vs_baseline should use structured KPIDelta records to support Management Issue Generation.

18. Forward Planning should emit a replan command when residual capacity inconsistency is detected, rather than silently rewriting the plan.

19. If only part of the E2E network is infeasible, WOM should short-circuit only the blocked portion and continue planning / evaluation for the feasible portion.

20. E2EEvaluationResult should identify whether it is a baseline result and which baseline scenario it is compared against.

21. ReplanCommand is a structured signal. Its execution should be handled by the planning operations command layer, not by Forward Planning itself.
```
