# MOSD Phase 2B+6 PRO Price & Cost Master Placeholder

## Purpose

Add placeholder Price & Cost master values for `IPHONE_NM_2028_PRO`.

## Background

`IPHONE_NM_2028_PRO` existed in PSI and route outputs, but its price/cost values were all zero in `node_price_waterfall.csv`. This caused Price & Cost Structure chart generation to return no files.

## Implemented behavior

- Preserved existing `IPHONE_NM_2028_BASE` rows.
- Added corresponding `IPHONE_NM_2028_PRO` rows in `pysi/master_data/node_product_money_master.csv`.
- Used BASE as reference where possible.
- Applied premium placeholder values for PRO.
- Did not change evaluator, planner, GUI, or chart logic.

## Verification

Confirmed that `IPHONE_NM_2028_PRO × CS_US_PREMIUM` generates:

- E2E lane price & cost structure chart
- E2E lane added cost structure delta-only chart