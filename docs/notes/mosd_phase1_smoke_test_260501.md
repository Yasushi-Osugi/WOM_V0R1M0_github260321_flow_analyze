# MOSD Phase 1 Smoke Test 260501

## Purpose

Verify that MOSD-generated Phase 1 WOM master files can be loaded by WOM and displayed in GUI / Network / World Map / PSI Graph.

## Input

- samples/mosd/home_appliance_sample_v0_1.json
- product: SMART_WASHER_2028_BASE

## Adapter command

python -m pysi.modeling.wom_master_adapter ^
  --mosd samples/mosd/home_appliance_sample_v0_1.json ^
  --output outputs/generated_master_data/home_appliance_sample_001 ^
  --overwrite

## Generated files

- data/node_geo.csv
- data/product_tree_inbound.csv
- data/product_tree_outbound.csv
- data/sku_P_month_data.csv
- data/sku_S_month_data.csv
- pysi/master_data/node_master.csv

## Test operation

Generated files were temporarily copied to:

- data/
- pysi/master_data/

Then WOM was launched.

## Result

- SMART_WASHER_2028_BASE appeared in Product selector.
- Generated nodes appeared in Node selector.
- E2E network displayed generated product tree.
- World map displayed generated nodes.
- PSI graph displayed generated quantity profile.
- Money values were zero because Phase 2 costing masters are not generated yet.

## Fix applied

Removed hardcoded debug check for IPHONE_NM_2028_BASE in:

- pysi/core/wom_pipeline.py

Commit:

- 98684e4 Remove hardcoded product debug check from WOM pipeline

## Conclusion

MOSD Phase 1 adapter successfully generated WOM quantity master skeleton that can be loaded and visualized by WOM.