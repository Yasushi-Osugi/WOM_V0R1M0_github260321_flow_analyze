# WOM — Weekly Operation Model

At first, starter "phthon -m main" will show you WOM UI that will take some minutes for loading Supply Chain Model.

WOM (Weekly Operation Model) is an experimental planning framework for modeling and simulating economic activity through supply chain flows.

The project explores how **planning systems can evolve from static planning tools into dynamic simulation-based decision engines**.

WOM is designed as a **planning kernel** that integrates:

- demand modeling
- supply chain flow simulation
- evaluation of system performance
- decision search and corrective planning actions

---
WOM System Architecture Map

Human Objectives
        ↓
   AI Research
        ↓
   WOM Architecture
        ↓
   Planning Kernel
        ↓
Demand → Flow → State
        ↓
   Evaluation
        ↓
    Resolver
        ↓
    Operator
        ↓
   Re-simulation
---
# Why WOM?

Traditional planning systems rely on static planning tables.

WOM models economic activity as **flows of supply through a network over time**.

The core principle is:

Flow/Event = source of truth  
State = derived view

Instead of maintaining static state tables, WOM tracks **events and flows**, from which planning states such as inventory or backlog are derived.

This approach enables:

- explainable planning
- reproducible simulations
- AI-assisted decision search

---

# Core Planning Loop

The WOM engine operates as a closed-loop planning system.


Demand
↓
Flow Simulation
↓
State Derivation
↓
Evaluation
↓
Resolver Decision
↓
Operator Application
↓
Re-Simulation


This loop transforms WOM from a planning calculator into a **simulation-driven planning engine**.

---

# Core Concepts

The WOM model is built around six fundamental concepts.

CPU  
Price  
Lot  
Flow  
Resolver  
Evaluation  

### CPU (Common Planning Unit)

The fundamental unit of demand, such as a household consumption unit or market demand segment.

### Price

Market signal influencing supply and demand behavior.

### Lot

The basic supply object used by the planning system.

### Flow

Movement of lots through the supply chain network.

### Resolver

Decision engine that searches for corrective actions.

### Evaluation

Objective function measuring plan quality.

---

# Architecture Overview

The WOM system architecture can be understood as a layered model.

Human Objectives  
↓  
AI Research Design  
↓  
Software Architecture  
↓  
Planning Kernel  
↓  
Mathematical Model  
↓  
Economic System Model  

This layered structure allows WOM to function both as a **planning engine and a research platform**.

---

# Planning Engine Modules

The WOM planning engine consists of four core modules.


demand_model.py
flow_engine.py
evaluation.py
resolver.py


| Module | Responsibility |
|------|------|
| demand_model | demand generation |
| flow_engine | supply chain simulation |
| evaluation | plan scoring |
| resolver | decision search |

---

# Data Model

The WOM planning system uses an event-based data model.

Key entities include:

Lot  
Event  
Flow  
State  
TrustEvent  
Operator  

Events represent the **true record of system activity**, while states are derived views computed from event streams.

---

# Repository Structure

The repository contains a set of architecture and design documents.

Core documents include:


ARCHITECTURE.md
WOM_META_ARCHITECTURE.md
WOM_PLANNING_ENGINE_ARCHITECTURE.md
WOM_EXECUTION_MODEL.md
WOM_DATA_MODEL.md
WOM_SYSTEM_DESIGN_INDEX.md


These documents collectively define the WOM planning system.

---

# AI-Assisted Development

The project is designed to support **AI-assisted development workflows**.

Documentation such as:

AGENTS.md  
INTERFACE_SPEC.md  
DEV_ROADMAP.md  

enables collaboration between:

- human architects
- AI design agents
- code generation systems

---

# Project Scope

Current focus areas:

- weekly supply chain planning
- event-based flow simulation
- explainable planning artifacts
- deterministic planning engines

The project may later expand into broader economic system modeling.

---

# Project Status

WOM is an experimental research and development project.

Current priorities include:

- stabilizing the planning kernel
- improving modular architecture
- enabling AI-assisted development

---

# Getting Started


Recommended reading order:

REPO_BOOTSTRAP.md  
ARCHITECTURE_MAP.md  
ARCHITECTURE.md  
WOM_PLANNING_ENGINE_ARCHITECTURE.md  
WOM_EXECUTION_MODEL.md  
WOM_DATA_MODEL.md  

These documents provide a structured introduction to the system.

---

# Summary

WOM combines:

- supply chain flow simulation
- deterministic planning engines
- decision search mechanisms
- structured planning artifacts

into a unified planning framework.

The project explores how **planning systems can be built as simulation-driven economic engines**.

---
WOM Economic OS Architecture (Final Conceptual Diagram)
                    ┌─────────────────────────────┐
                    │        Human Objectives      │
                    │  Wellbeing / Stability /    │
                    │  Productivity / Sustainability │
                    └───────────────┬─────────────┘
                                    │
                                    ▼
                         ┌───────────────────┐
                         │     Evaluation     │
                         │  Objective Function│
                         │                   │
                         │ U(plan)            │
                         │ = w1 Service       │
                         │ + w2 Profit        │
                         │ - w3 Cost          │
                         │ - w4 Risk          │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │      Resolver      │
                         │ Decision / Search  │
                         │                   │
                         │ Operator Selection │
                         └─────────┬─────────┘
                                   │
                                   ▼
       ┌─────────────────────────────────────────────────────┐
       │                  WOM Planning Kernel                 │
       │                                                     │
       │                                                     │
       │   CPU (Common Planning Unit)                       │
       │          ↓                                          │
       │   Demand Generation                                 │
       │          ↓                                          │
       │   LOT Creation                                      │
       │          ↓                                          │
       │   Flow Simulation                                   │
       │                                                     │
       │   Production → Shipment → Arrival → Sales           │
       │                                                     │
       │          ↓                                          │
       │   State Derivation                                  │
       │                                                     │
       │   Inventory / Capacity / Backlog / Service          │
       │                                                     │
       └─────────────────────────┬───────────────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │      Price       │
                        │ Economic Signal  │
                        │ Demand Response  │
                        └─────────┬────────┘
                                  │
                                  ▼
                     ┌────────────────────────┐
                     │    Economic Network    │
                     │                        │
                     │ Factory → Warehouse    │
                     │        → Market        │
                     │                        │
                     │ Nodes / Edges / Flow   │
                     └──────────┬─────────────┘
                                │
                                ▼
                     ┌────────────────────────┐
                     │     Agents / Actors    │
                     │                        │
                     │ Firms                  │
                     │ Consumers              │
                     │ Logistics providers    │
                     │ Governments            │
                     └────────────────────────┘
---

# License

This project is released under the MIT License.

---

# Author

Yasushi Osugi
