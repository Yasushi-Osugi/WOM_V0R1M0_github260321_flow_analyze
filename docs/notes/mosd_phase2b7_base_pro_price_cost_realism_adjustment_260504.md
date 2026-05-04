# MOSD Phase 2B+7 BASE / PRO Price & Cost Realism Adjustment

## Purpose

Adjust BASE and PRO Price & Cost master values to make E2E Lane charts more business-plausible.

## Implemented behavior

- Updated `pysi/master_data/node_product_money_master.csv`.
- Preserved BASE / PRO coverage.
- Kept `supply_point` as a light HQ / PSI allocation node.
- Kept Global Marketing / Brand allocation out of the main E2E operational chart for now.
- Made PRO visibly premium relative to BASE.

## Verification

Confirmed chart generation for:

- `IPHONE_NM_2028_BASE`
- `IPHONE_NM_2028_PRO`
- `CS_US_PREMIUM`