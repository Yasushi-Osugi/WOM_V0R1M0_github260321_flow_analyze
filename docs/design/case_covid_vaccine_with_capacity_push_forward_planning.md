# COVID Vaccine Supply Chain Model
## With Capacity PUSH Forward Planning Case

**Version:** v0r1 draft  
**Date:** 2026-05-14  
**Status:** Design memo  
**Target path:** `docs/design/case_covid_vaccine_with_capacity_push_forward_planning.md`

---

## 1. Purpose

This memo defines a concrete WOM case model for:

```text
With Capacity PUSH Forward Planning
```

using a COVID vaccine supply chain as the reference scenario.

The purpose is to clarify how WOM should handle **Forward Planning with capacity constraints** when upstream supply lots are already available and must be pushed downstream under practical constraints such as:

- transport capacity
- storage capacity
- cold-chain capacity
- vaccination capacity
- expiry risk
- regional demand imbalance

This case is intended to become a practical demonstration model for the current WOM development theme:

```text
capacity-aware controlled PUSH
```

or in Japanese:

```text
能力制約を考慮した制御型PUSH配分
```

---

## 2. Scope

### 2.1 Phase 1 Scope: Japan Market Distribution and Vaccination Model

The first implementation should focus on the Japan market model.

```text
External manufacturer supply
    ↓
Japan central receiving / central DC
    ↓
Prefecture / regional DC
    ↓
Wholesaler / cold-chain logistics
    ↓
Clinic / vaccination site
    ↓
Administered vaccination demand
```

The upstream manufacturers, such as Pfizer and Moderna, are treated as external supply assumptions in Phase 1.

```text
Pfizer weekly supply plan  → external input
Moderna weekly supply plan → external input
```

### 2.2 Out of Scope for Phase 1

Phase 1 does not model:

- Pfizer / Moderna manufacturing capacity
- upstream raw material constraints
- overseas plant network
- international procurement
- full import customs leadtime modeling
- detailed temperature-band optimization
- multi-country global allocation

These can be added in later phases.

---

## 3. WOM Interpretation

This case should be interpreted as a **Forward PUSH with Capacity** model.

The core question is:

```text
Given available vaccine lots at an upstream node,
how should WOM push those lots downstream week by week
while respecting transport, storage, and vaccination capacity?
```

This is different from Backward Demand Allocation.

In this case, supply already exists or is externally supplied into Japan. The model focuses on how to distribute and consume those lots through the domestic network.

---

## 4. Network Definition

### 4.1 Minimal Phase 1 Network

The initial demo should use only a small number of nodes.

```text
SUPPLY_SOURCE_JP
    Japan domestic vaccine supply input

CENTRAL_DC
    national central receiving / storage point

PREF_DC_TOKYO
PREF_DC_OSAKA
PREF_DC_AICHI
    prefecture / regional distribution centers

WHOLESALER_TOKYO
WHOLESALER_OSAKA
WHOLESALER_AICHI
    pharmaceutical wholesalers / cold-chain logistics nodes

CLINIC_TOKYO_01
CLINIC_OSAKA_01
CLINIC_AICHI_01
    vaccination sites / medical institutions

DEMAND_TOKYO
DEMAND_OSAKA
DEMAND_AICHI
    administered dose demand
```

### 4.2 Initial Region Set

For the first demo, use three regions:

```text
TOKYO
OSAKA
AICHI
```

This is enough to demonstrate:

- regional allocation
- transport bottleneck
- clinic capacity bottleneck
- regional demand surge
- expiry risk

---

## 5. Phase 2 and Later Expansion

### Phase 2: Manufacturer Inbound Supply Model

Add manufacturer supply assumptions and inbound leadtime.

```text
PFIZER_SUPPLY
MODERNA_SUPPLY
    ↓
IMPORT_LANE
    ↓
SUPPLY_SOURCE_JP
```

### Phase 3: Manufacturer Capacity Model

Add manufacturing capacity and upstream constraints.

```text
PFIZER_MANUFACTURING_NODE
MODERNA_MANUFACTURING_NODE
RAW_MATERIAL_SUPPLY
INTERNATIONAL_LANE
IMPORT_CUSTOMS
```

### Phase 4: Variant / Product Switching Scenario

Add product switching and expiry/disposal scenarios.

```text
old vaccine lots
new variant vaccine lots
expiry risk
replacement supply
waste / quarantine / disposal
```

---

## 6. PSI Definition for Vaccine Model

WOM uses P/S/I as the common planning structure.

In this vaccine case:

```text
P = supplied / delivered / allocated lots into the node during the week
S = shipped to downstream node or administered at vaccination site
I = usable stock remaining at end of week
```

### 6.1 DC Node Semantics

For DC / wholesaler nodes:

```text
P:
    vaccine lots received into the node

S:
    vaccine lots shipped to downstream node

I:
    usable inventory remaining at the node
```

### 6.2 Clinic Node Semantics

For clinic / vaccination site nodes:

```text
P:
    vaccine lots delivered to the clinic

S:
    administered vaccination lots / doses

I:
    usable clinic inventory remaining at end of week
```

Important:

```text
Same S bucket has different business meaning by node role.

DC node:
    S = shipment to downstream

Clinic node:
    S = administered vaccination
```

This must be made explicit in reports and UI labels.

---

## 7. Lot Definition

Vaccine lots require richer lot headers than a normal product lot.

### 7.1 Suggested Lot Header

```python
lot = {
    "lot_id": "VAC-PFZ-2026W40-000001",
    "product_id": "COVID_VACCINE_PFIZER",
    "manufacturer": "Pfizer",
    "dose_qty": 100,
    "origin": "SUPPLY_SOURCE_JP",
    "current_node": "CENTRAL_DC",
    "target_region": "TOKYO",
    "target_node": "CLINIC_TOKYO_01",
    "week_available": "2026-W40",
    "expiry_week": "2026-W48",
    "temperature_class": "frozen_or_cold",
    "quality_status": "usable",
    "allocation_status": "unallocated",
}
```

### 7.2 Minimal Required Fields for MVP

```text
lot_id
product_id
dose_qty
current_node
target_node
target_region
week_available
expiry_week
quality_status
```

### 7.3 Expiry Handling

In the first MVP:

```text
If expiry_week < current_week:
    exclude lot from allocation target
    record as expired_lot
```

Future versions may model:

- usable inventory
- expired inventory
- quarantine inventory
- disposal / waste
- FEFO allocation

---

## 8. Capacity Definition

The vaccine model has multiple capacity types.

### 8.1 Capacity Types

```text
supply_capacity:
    weekly supply lots entering Japan market

transport_capacity:
    weekly lots transferable through a lane

storage_capacity:
    maximum lots a node can store at end of week

cold_chain_capacity:
    lots that can be transported or stored under required temperature condition

vaccination_capacity:
    weekly administered dose capacity at clinic / vaccination site

handling_capacity:
    weekly processing / receiving / picking capacity at wholesaler or DC
```

### 8.2 MVP Capacity Types

For the first implementation, focus on:

```text
transport_capacity
storage_capacity
vaccination_capacity
```

Cold-chain capacity can initially be treated as a flag or a subtype of transport/storage capacity.

```text
cold_chain_required = True
cold_chain_capacity = transport_capacity under cold-chain condition
```

### 8.3 Capacity Master Mapping

The existing v0r2 capacity I/O structure can be reused.

Suggested mapping:

```text
P capacity:
    receiving / supply-in capacity at node

S capacity:
    shipment capacity or vaccination capacity

I capacity:
    storage capacity at node
```

For clinic nodes:

```text
S capacity = vaccination_capacity
```

For logistics lanes:

```text
flow capacity = transport_capacity
```

---

## 9. With Capacity PUSH Forward Planning Logic

### 9.1 Core Principle

The algorithm starts from available upstream lots and pushes them downstream under capacity constraints.

```text
available upstream lots
    ↓
lane capacity check
    ↓
downstream storage capacity check
    ↓
downstream demand gap check
    ↓
accepted lots move downstream
    ↓
blocked lots are recorded
```

### 9.2 Minimal Algorithm

```python
for week in planning_weeks:
    for lane in forward_lanes:
        upstream = lane.from_node
        downstream = lane.to_node

        available_lots = upstream.get_usable_inventory(week)
        demand_gap = (
            downstream.get_required_qty(week)
            - downstream.get_inventory_qty(week)
        )

        lane_cap = lane.get_capacity(week)
        storage_cap = downstream.get_remaining_storage_capacity(week)

        push_qty = min(
            len(available_lots),
            demand_gap,
            lane_cap,
            storage_cap,
        )

        accepted_lots = available_lots[:push_qty]
        blocked_lots = available_lots[push_qty:]

        move_lots(
            accepted_lots,
            from_node=upstream,
            to_node=downstream,
            week=week,
        )

        record_capacity_result(
            week=week,
            lane=lane,
            accepted_lots=accepted_lots,
            blocked_lots=blocked_lots,
        )
```

### 9.3 Clinic-Side Vaccination Consumption

For clinic nodes:

```python
for clinic in clinic_nodes:
    usable_stock = clinic.get_usable_inventory(week)
    demand = clinic.get_demand(week)
    vaccination_cap = clinic.get_vaccination_capacity(week)

    administered_qty = min(
        len(usable_stock),
        demand,
        vaccination_cap,
    )

    administered_lots = usable_stock[:administered_qty]

    clinic.record_S_as_administered(
        week=week,
        lots=administered_lots,
    )
```

---

## 10. Relationship with Existing v0r2 / v0r3 Components

This case should reuse existing with-capacity components.

### 10.1 v0r2-m1

```text
Forward PUSH with Capacity planner MVP:
    accepted / blocked lot split
```

### 10.2 v0r2-m2

```text
capacity_master.csv loader
CapacityUsage
CapacityViolation
usage / violation CSV export
```

### 10.3 v0r2-m3

```text
psi4demand / psi4supply adapter
accepted lots written to psi4supply
blocked lots recorded separately
```

### 10.4 v0r3

```text
bottleneck_allocation.py
FIFO
LOT_PRIORITY
DUE_WEEK_PRIORITY
```

### 10.5 Additional Policy Needed for Vaccine Model

The vaccine model should add:

```text
FEFO = First Expired, First Out
```

This is more natural than FIFO for vaccine lots.

Proposed future rule:

```text
FEFO:
    sort lots by expiry_week ascending
    earliest expiry lots are pushed / administered first
```

---

## 11. Blocked Lot Handling

Blocked lots should not disappear.

### 11.1 Blocked Reasons

Examples:

```text
lane_capacity_exceeded
storage_capacity_exceeded
vaccination_capacity_exceeded
cold_chain_capacity_exceeded
demand_gap_zero
expired_lot
quality_not_usable
```

### 11.2 Suggested Blocked Lot Record

```python
blocked_record = {
    "week": "2026-W40",
    "lot_id": "VAC-PFZ-2026W40-000001",
    "product_id": "COVID_VACCINE_PFIZER",
    "from_node": "CENTRAL_DC",
    "to_node": "PREF_DC_TOKYO",
    "blocked_reason": "transport_capacity_exceeded",
    "capacity_type": "transport_capacity",
    "next_action": "retry_next_week",
}
```

### 11.3 Expired Lots

Expired lots should be recorded separately.

```python
expired_record = {
    "week": "2026-W49",
    "lot_id": "VAC-PFZ-2026W40-000001",
    "expired_at_node": "CLINIC_TOKYO_01",
    "expiry_week": "2026-W48",
    "dose_qty": 100,
}
```

---

## 12. KPI and Reports

### 12.1 Operational KPIs

```text
weekly administered doses by region
weekly shortage lots by region
weekly usable inventory by node
blocked lots by reason
expired lots
transport utilization
storage utilization
vaccination capacity utilization
```

### 12.2 E2E Evaluation KPIs

Use WOM KPI Registry where possible.

Candidate KPI mapping:

```text
node.capacity_utilization
node.backlog_qty
node.ending_inventory_qty
node.stockout_qty
node.fill_rate

supply_point.demand_supply_gap_qty
supply_point.demand_supply_gap_rate
supply_point.outbound_fill_rate
supply_point.weekly_psi_balance_score

total_sc.backlog_qty
total_sc.fill_rate
total_sc.capacity_utilization
total_sc.capacity_concentration_index
total_sc.inventory_value

strategic.customer_fulfillment_score
strategic.capacity_resilience_score
strategic.inventory_soundness_score
strategic.structural_sustainability_score
```

### 12.3 Vaccine-Specific KPIs

Additional case-specific KPIs:

```text
administered_dose_qty
regional_vaccination_fill_rate
expired_dose_qty
expiry_risk_qty
cold_chain_blocked_qty
vaccination_capacity_utilization
regional_equity_score
```

---

## 13. Scenario Patterns

### Scenario 1: Base Case

Supply, transport, storage, and vaccination capacity are balanced.

Expected result:

```text
no major shortage
no major expiry
stable vaccination flow
```

### Scenario 2: Transport Bottleneck

Central DC has enough stock, but regional transport capacity is insufficient.

Expected result:

```text
central stock remains high
regional shortage occurs
blocked lots due to transport capacity
administered dose count is lower than supply availability
```

### Scenario 3: Vaccination Capacity Bottleneck

Clinics receive vaccine inventory, but vaccination capacity is insufficient.

Expected result:

```text
clinic inventory increases
administered doses lag
expiry risk increases
vaccination capacity utilization reaches 100%
```

### Scenario 4: Regional Demand Surge

One region experiences demand surge.

Expected result:

```text
regional shortage appears
priority allocation becomes visible
fairness vs focus allocation trade-off appears
```

### Scenario 5: Expiry Risk / FEFO Need

Lots with early expiry remain unused.

Expected result:

```text
expiry risk lots appear
FIFO may waste lots
FEFO policy reduces expiry waste
```

---

## 14. Implementation Roadmap

### Phase 1: Minimal Japan Market Forward PUSH Model

Implement:

```text
three regions
central DC
regional DCs
clinic nodes
weekly supply input
transport capacity
storage capacity
vaccination capacity
accepted / blocked lot records
```

### Phase 2: Add Expiry and FEFO

Implement:

```text
expiry_week
usable / expired lot filtering
FEFO allocation policy
expiry risk report
```

### Phase 3: Add Manufacturer Supply Model

Implement:

```text
Pfizer / Moderna weekly supply input
manufacturer-specific lot headers
import lane
import leadtime
```

### Phase 4: Add E2E Evaluation and Management Issue Generation

Implement:

```text
E2EEvaluationResult
KPIDelta vs baseline
management issue generation
LLM summary input
```

---

## 15. Suggested Files

### 15.1 Design

```text
docs/design/case_covid_vaccine_with_capacity_push_forward_planning.md
```

### 15.2 Future implementation candidates

```text
pysi/cases/covid_vaccine/scenario_builder.py
pysi/cases/covid_vaccine/run_covid_vaccine_with_capacity_push_smoke.py
pysi/cases/covid_vaccine/covid_vaccine_lot_factory.py
pysi/cases/covid_vaccine/covid_vaccine_capacity_master_sample.csv
tests/test_covid_vaccine_with_capacity_push.py
```

---

## 16. MVP Smoke Test

### 16.1 Smoke Input

```text
week: 2026-W40
supply at CENTRAL_DC: 300 lots

regions:
    TOKYO demand: 150
    OSAKA demand: 120
    AICHI demand: 80

transport capacity:
    CENTRAL_DC → PREF_DC_TOKYO: 100
    CENTRAL_DC → PREF_DC_OSAKA: 80
    CENTRAL_DC → PREF_DC_AICHI: 50

vaccination capacity:
    CLINIC_TOKYO_01: 90
    CLINIC_OSAKA_01: 70
    CLINIC_AICHI_01: 50
```

### 16.2 Expected Output

```text
accepted lots by lane
blocked lots by lane
usable inventory by node
administered doses by clinic
shortage by region
capacity usage records
capacity violation records
```

---

## 17. Relationship with WOM Message

This case communicates the core WOM message:

```text
Vaccine supply is not enough by itself.

Lots must be synchronized weekly across transport capacity,
storage capacity, vaccination capacity, demand, and expiry risk.

With Capacity PUSH Forward Planning shows
what can actually be delivered and administered.
```

In Japanese:

```text
ワクチンは、在庫があるだけでは不十分である。

輸送能力、保管能力、接種能力、地域需要、有効期限を見ながら、
週次でLotを同期させる必要がある。

With Capacity PUSH Forward Planningは、
実際に届けられ、接種できる計画を可視化する。
```

---

## 18. Summary

The COVID vaccine Japan market model is a strong reference case for WOM With Capacity PUSH Forward Planning.

The initial model should focus on:

```text
external weekly vaccine supply
Japan domestic distribution
transport capacity
storage capacity
vaccination capacity
usable / blocked / expired lots
regional demand
```

The key planning question is:

```text
Given available vaccine lots,
how should WOM push those lots downstream week by week
under capacity constraints?
```

This case should become the first practical demonstration of:

```text
capacity-aware controlled PUSH
```

in WOM.
