# iPhone New Model Proxy Dataset v0.1

This dataset is a WOM-oriented sample initial dataset for an iPhone-like new model launch case.

## Scope
- Product variants: Base, Pro
- Key parts: 8
- Assembly plants: China, India, Vietnam
- Regional hubs: NA, EU West, India, China, Japan, SEA
- Countries: US, CA, MX, DE, FR, UK, IN, CN, JP, SG, TH, VN
- Channels: 21
- Consumer nodes: 15
- Planning horizon: 2027-01 to 2028-12
- Detailed launch buckets: 2028W34-2028W39

## Notes
- This is a proxy model, not a reconstruction of any real company's full supply chain.
- Most operational parameters are assumptions intended for WOM planning/visualization prototypes.
- All CSV files are encoded in UTF-8 with BOM.

## Suggested load order
1. product_master
2. part_master
3. bom_relation
4. geo_master
5. node_master
6. edge_master
7. channel_master
8. consumer_segment_master
9. calendar_master
10. leadtime_master
11. capacity_master
12. cost_master
13. price_master
14. inventory_master
15. monthly_demand_master
16. scenario_override
17. event_milestone
18. visualization_meta