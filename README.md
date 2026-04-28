# WOM — Weekly Operation Model

WOM (Weekly Operation Model) is an experimental **End-to-End Supply Chain Planning and Management Cockpit**.

WOM visualizes and simulates weekly PSI planning:

- **P**: Production / Purchase
- **S**: Shipment / Sales
- **I**: Inventory

across a global supply chain network.

The goal of WOM is to help business leaders, planners, and consultants understand how future business scenarios propagate through the end-to-end supply chain, including:

- demand changes
- supply capacity constraints
- inventory movements
- cost structure
- revenue and profit
- management risks and issues
- suggested management actions

WOM is still under development, but the current version already includes a working GUI demo, supply chain network visualization, PSI charts, money evaluation, Management Cockpit, and an experimental rule-based Management Issue Analyzer.

---

## Current Demo Capabilities

The current WOM demo can:

- visualize an end-to-end supply chain network
- show PSI time-series charts for each supply chain node
- run weekly supply chain planning
- evaluate sales, cost, profit, and profit ratio
- display node-level and product-level money evaluation
- compare baseline and scenario planning states
- extract management issues from scenario deltas
- generate executive narrative text for risks and suggested actions

---

## Getting Started

Clone the repository:

```bash
git clone https://github.com/Yasushi-Osugi/wom-event-flow-analyzer.git
cd wom-event-flow-analyzer
```

Run the WOM GUI:

```bash
python -m main
```

The initial loading process may take several minutes depending on the supply chain model, master data, and local environment.

When the GUI starts, you can use the cockpit window to:

- visualize the supply chain network
- inspect PSI charts by node
- run full planning
- evaluate revenue, cost, profit, and profit ratio
- open the Management Cockpit
- compare baseline and scenario states
- review Issues, Top Risks, and executive Narrative

---

## Key Features

### 1. Supply Chain Network Visualization

WOM visualizes supply chain nodes and edges as an end-to-end network.

Users can inspect factories, warehouses, distribution nodes, market nodes, and other supply chain entities.

Each node can be linked with PSI behavior, inventory movement, and management-level indicators.

---

### 2. Weekly PSI Planning

WOM simulates weekly production, purchase, shipment, sales, and inventory flows.

The PSI planner shows how supply and demand move through the network over time.

Each node can display its own PSI time-series graph, making it possible to understand where inventory is accumulated, depleted, or delayed.

---

### 3. Money Evaluation

WOM evaluates supply chain plans not only by quantity, but also by money.

Current money evaluation includes:

- revenue
- cost
- profit
- profit ratio
- node-level money evaluation
- product-level money summary
- cost waterfall reporting

This enables WOM to connect operational planning with management-level financial evaluation.

---

### 4. Management Cockpit

WOM includes an experimental **Management Cockpit** for scenario comparison.

The cockpit compares baseline and scenario planning results and shows:

- Top KPIs
- Top Risks
- Management Issues
- Issue Detail
- Executive Narrative

The purpose of the Management Cockpit is to help users understand not only what changed in the plan, but also why it matters from a management perspective.

---

### 5. Management Issue Analyzer

WOM includes a rule-based **Management Issue Analyzer** as the first step toward AI-assisted scenario diagnosis.

The analyzer compares KPI deltas between baseline and scenario plans.

It evaluates:

- revenue
- profit
- profit ratio
- inventory
- shortage
- backlog

and generates:

- management issues
- top risks
- suggested actions
- executive narrative

The analyzer is implemented in:

```text
pysi/reporting/management_issue_analyzer.py
```

It is integrated with the Management Cockpit GUI.

For example, in a demand surge scenario, WOM can show:

- revenue and profit improvement
- supply capacity pressure risk
- opportunity for revenue expansion
- recommended actions such as short-term production increase, supply reallocation, and safety stock review

---

## Scenario Difference Analysis

WOM can compare baseline and scenario planning states and extract issues from KPI deltas.

This supports scenario planning such as:

- demand surge
- demand slowdown
- supply constraint
- logistics disruption
- port stop
- inventory risk
- profit deterioration
- cash efficiency risk

The current rule-based analyzer is intentionally simple and explainable.

Future versions may combine rule-based logic with LLM-based narrative generation and scenario-specific management recommendations.

---

## Concept

WOM is based on the idea that modern planning systems should evolve from static planning tables into simulation-driven management cockpits.

The core concept is:

```text
Future Scenario
↓
Supply Chain Planning
↓
PSI / Cost / Profit / Inventory Simulation
↓
Scenario Difference
↓
Management Issues
↓
Suggested Actions
```

In this sense, WOM is not only a PSI planning tool.

It is an experimental environment for **E2E supply chain scenario planning**.

---

## Why WOM?

Traditional planning systems often rely on static planning tables.

WOM models economic activity as flows of supply through a network over time.

The core principle is:

```text
Flow / Event = source of truth
State = derived view
```

Instead of treating static state tables as the primary source, WOM aims to track planning flows and derive states such as inventory, backlog, capacity usage, and service level.

This approach supports:

- explainable planning
- reproducible simulations
- scenario-based decision support
- AI-assisted management issue analysis

---

## Architecture Overview

WOM combines several layers:

```text
Business Scenario
↓
Demand / Supply Planning
↓
PSI Flow Simulation
↓
Money Evaluation
↓
State Snapshot
↓
Plan Delta
↓
Management Issue Analyzer
↓
Management Cockpit
```

The current implementation includes both quantity-based and money-based evaluation.

---

## Repository Structure

Main areas:

```text
pysi/
  gui/
    cockpit_tk.py

  reporting/
    management_issue_analyzer.py
    business_report_builder.py

  evaluate/
    money_evaluator.py

  cost/
    load_cost_masters.py

  master_data/
    money_master_loader.py

wom_cockpit/
  domain/
  services/
  ui/
```

Important modules:

```text
main.py
pysi/gui/cockpit_tk.py
pysi/reporting/management_issue_analyzer.py
pysi/evaluate/money_evaluator.py
wom_cockpit/ui/tk/cockpit_panel_adapter.py
```

---

## Current Development Status

WOM is an experimental research and development project.

Current focus areas include:

- stabilizing the GUI demo
- improving scenario comparison
- strengthening costing and profit evaluation
- enhancing Management Cockpit
- refining Management Issue Analyzer rules
- preparing 1-minute demo content
- documenting architecture and use cases

---

## Concept Article

A Japanese concept article is available on note:

```text
E2Eサプライチェーン理解に基づく事業経営の重要性
```

The article explains why business leaders need to understand the end-to-end supply chain model and how WOM aims to support scenario-based supply chain management.

Article URL:

```text
https://note.com/osuosu1123/n/n4bca0c3906f9
```

---

## Example Management Cockpit Scenario

In a demand surge scenario, WOM can compare a baseline plan with a scenario plan.

The Management Cockpit can show that:

- revenue increases
- profit improves
- profit ratio improves
- supply capacity pressure risk is detected
- revenue expansion opportunity is detected
- recommended actions are generated

Example recommended actions include:

- short-term production increase
- supply reallocation to priority markets
- safety stock level review
- monitoring of supply capacity constraints

This demonstrates how WOM can move from planning visualization toward management-level scenario diagnosis.

---

## Project Scope

Current scope:

- weekly supply chain planning
- PSI visualization
- quantity-based flow simulation
- money-based evaluation
- scenario comparison
- management issue extraction
- executive narrative generation

Future scope may include:

- richer demand scenario generation
- inbound and outbound planning integration
- alternative logistics route simulation
- stronger costing allocation rules
- LLM-assisted scenario diagnosis
- ERP / BI / database integration

---

## License

This project is released under the MIT License.

---

## Author

Yasushi Osugi