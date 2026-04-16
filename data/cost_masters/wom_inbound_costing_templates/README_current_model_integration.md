# WOM Inbound Costing: current-model integration and future rule masters

Current model integration
- Keep common masters as-is:
  - product_cost_master.csv
  - node_cost_master.csv
  - lane_cost_master.csv
  - sales_price_master.csv
  - allocation_rule_master.csv
- Add inbound masters:
  - inbound_item_master.csv
  - inbound_bom_usage_master.csv
  - inbound_price_decision_master.csv
  - inbound_adjustment_master.csv
- Future optional rule masters:
  - event_cost_rule_master.csv
  - node_character_cost_rule_master.csv

Recommended current-model integration points
1. load_cost_masters.py
   - extend CostMasterBundle with:
     inbound_item_master
     inbound_bom_usage_master
     inbound_price_decision_master
     inbound_adjustment_master
2. cost_engine.py
   - direct inbound cost = item/BOM/price decision based
   - keep accounting grain at product × node × week
3. allocation_rule_engine.py
   - add target_cost_type candidates:
     inbound_fixed_overhead
     capacity_reservation_cost
     premium_freight_cost
     supplier_support_adjustment
     scrap_loss_cost
     policy_adjustment
4. reporting
   - keep node / supply_point / market / product / monthly outputs
   - treat supply_point as the integrated economic control point

Event-based costing position
- current model remains the accounting source of truth
- event-based costing is a future causal-explanation layer
- recommended usage:
  A. event-causal cost -> event rules
  B. state-holding cost -> current model
  C. policy cost -> current model

Performance-safe design hints for future event rules
- use aggregation_mode to avoid one-cost-line-per-event explosion
- support weekly_rollup / event_cluster / first_event_only
- support attribution_scope choices:
  node_week / lane_week / product_node_week / event_cluster
- keep event rules opt-in by cost category
