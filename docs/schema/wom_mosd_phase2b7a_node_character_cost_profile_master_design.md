# WOM MOSD Phase 2B+7a Node Character Based Cost Profile Master Design## 1. PurposePhase 2B+7a defines the design for introducing a node-character-based cost profile master.The purpose is to move from manually tuned `node_product_money_master.csv` values toward a repeatable WOM costing master generation process.Current Phase 2B+7 adjusted:```textpysi/master_data/node_product_money_master.csv
directly so that BASE / PRO Price & Cost Structure charts look more natural.
Phase 2B+7a defines the next modeling layer:
node_character_cost_profile_master.csv× product_price_tier_master.csv× region / country factor→ node_product_money_master.csv
This makes WOM costing model generation more scalable, consistent, and explainable.

2. Background
After Phase 2B+7, the E2E Lane Price & Cost Structure charts for:
IPHONE_NM_2028_BASEIPHONE_NM_2028_PRO
became more natural.
However, the current master values are still embedded directly in:
pysi/master_data/node_product_money_master.csv
This is useful for testing, but not ideal for model building.
For future WOM modeling, cost structure should be generated from higher-level assumptions:
node characterproduct tierregion / country cost factorscenario
This phase defines the master structure for that approach.

3. Design Concept
The core concept is:
node_character→ standard cost structure profile
Then:
product tier→ target price / premium level
Then:
country / region→ labor / operating cost adjustment
Together:
node_character_cost_profile× product_price_tier× region_factor→ node_product_money_master
This allows WOM to generate product-node money values consistently.

4. Scope
In scope


Define node_character_cost_profile_master.csv.


Define product_price_tier_master.csv.


Define region_cost_factor_master.csv.


Define how these masters generate node_product_money_master.csv.


Define mapping to current WOM money master columns.


Define supply_point special handling.


Define BASE / PRO initial profiles.


Define tests and verification approach.


Not in scope


Real-world Apple cost estimation.


EDGAR / SEC data ingestion.


Automatic public financial data scraping.


GUI integration.


Management Cockpit integration.


Tax / trade policy scenario logic.


Fan-in E2E chart logic.


Full preprocessor implementation in this design-only phase.



5. Master 1: node_character_cost_profile_master.csv
5.1 Purpose
This master defines standard cost component ratios by node character.
Each row represents:
node_character × profile_id
The profile describes how the node's ship_price or own allocated cost is composed.
5.2 Proposed path
pysi/master_data/node_character_cost_profile_master.csv
or, during early modeling:
data/cost_masters/node_character_cost_profile_master.csv
5.3 Columns
node_character,profile_id,profile_basis,purchase_pct,value_added_pct,variable_pct,fixed_pct,sga_pct,tax_pct,target_profit_pct,remarks
5.4 Column definitions
ColumnMeaningnode_characterWOM node character, e.g. CS, RT, WS, DAD, MOM, PAD, supply_pointprofile_idCost profile identifierprofile_basisship_price or own_allocated_costpurchase_pctPurchase / acquisition cost ratiovalue_added_pctManufacturing / assembly / business value-add ratiovariable_pctVariable operating / logistics / handling cost ratiofixed_pctFixed cost / facility / staff allocation ratiosga_pctSelling, general, channel, or business management cost ratiotax_pctTax / tariff / compliance cost ratiotarget_profit_pctTarget profit or margin ratioremarksExplanation

6. node_character_cost_profile_master v0.1
6.1 Outbound side
node_character,profile_id,profile_basis,purchase_pct,value_added_pct,variable_pct,fixed_pct,sga_pct,tax_pct,target_profit_pct,remarksDAD,DAD_SALES_HQ_STD,ship_price,0.58,0.00,0.05,0.12,0.07,0.03,0.15,Sales subsidiary HQ / finished goods receivingWS,WS_STD,ship_price,0.76,0.00,0.08,0.08,0.00,0.03,0.05,Warehouse / storage cost centerRT,RT_CHANNEL_STD,ship_price,0.68,0.00,0.08,0.08,0.08,0.03,0.05,Regional retail / channel operationCS,CS_CHANNEL_STD,ship_price,0.50,0.00,0.10,0.12,0.10,0.03,0.15,Sales channel / market front
6.2 Inbound side
node_character,profile_id,profile_basis,purchase_pct,value_added_pct,variable_pct,fixed_pct,sga_pct,tax_pct,target_profit_pct,remarksPAD,PAD_PROCUREMENT_STD,ship_price,0.65,0.08,0.05,0.07,0.05,0.03,0.07,Parts aggregation / procurement nodeMOM,MOM_ASSEMBLY_STD,ship_price,0.55,0.18,0.05,0.10,0.03,0.03,0.06,Final assembly / mother plantEMS,EMS_CONTRACT_MFG_STD,ship_price,0.60,0.15,0.05,0.10,0.02,0.03,0.05,Contract manufacturingsupplier_material,SUPPLIER_MATERIAL_STD,ship_price,0.45,0.25,0.05,0.10,0.03,0.02,0.10,Material / core component supplier
6.3 supply_point special profile
supply_point is not a physical product trading node.
It is a HQ / PSI / supply-demand coordination / business control node.
Therefore, it should not be modeled as:
purchase cost + margin = ship price
Instead, it should be modeled as:
own allocated HQ / PSI cost = 100%
node_character,profile_id,profile_basis,purchase_pct,value_added_pct,variable_pct,fixed_pct,sga_pct,tax_pct,target_profit_pct,remarkssupply_point,SP_HQ_PSI_ALLOC,own_allocated_cost,0.00,0.00,0.10,0.70,0.15,0.00,0.00,HQ / PSI / business management allocation node
For supply_point, profile_basis = own_allocated_cost.
This means:
purchase_pct does not represent product purchase cost.fixed_pct and sga_pct represent HQ / PSI / planning / business management allocation.
Global Marketing / Brand Management is not included in the main E2E physical supply chain chart in Phase 2B+7a.
It may be handled later as:
brand_allocation_cost_per_lotglobal_marketing_allocation_per_lotbrand_royalty_cost_per_lot

7. Master 2: product_price_tier_master.csv
7.1 Purpose
This master defines product-level price and cost tier assumptions.
7.2 Proposed path
pysi/master_data/product_price_tier_master.csv
or:
data/cost_masters/product_price_tier_master.csv
7.3 Columns
product_name,price_tier,target_market_price,inventory_base_value,premium_factor,remarks
7.4 Example
product_name,price_tier,target_market_price,inventory_base_value,premium_factor,remarksIPHONE_NM_2028_BASE,mainstream,899,520,1.00,Mainstream modelIPHONE_NM_2028_PRO,premium,1299,680,1.35,Premium model
7.5 Meaning
ColumnMeaningproduct_nameProduct IDprice_tiermainstream / premium / economy / luxurytarget_market_priceIntended CS-level market-facing priceinventory_base_valueApproximate acquisition / inventory valuation basepremium_factorProduct premium factor vs base modelremarksExplanation

8. Master 3: region_cost_factor_master.csv
8.1 Purpose
This master defines country / region cost adjustment factors.
Mainly applies to:
value_added_pctvariable_pctfixed_pctsga_pct
8.2 Proposed path
pysi/master_data/region_cost_factor_master.csv
or:
data/cost_masters/region_cost_factor_master.csv
8.3 Columns
country_or_region,labor_cost_factor,operating_cost_factor,logistics_cost_factor,sga_cost_factor,remarks
8.4 Example
country_or_region,labor_cost_factor,operating_cost_factor,logistics_cost_factor,sga_cost_factor,remarksUS,1.30,1.20,1.10,1.30,High labor and sales administration costEU,1.20,1.15,1.10,1.20,High labor and compliance costJP,1.10,1.10,1.00,1.10,Japan marketCN,0.75,0.85,0.90,0.80,China manufacturing and marketIN,0.55,0.70,0.90,0.65,India lower labor costAPAC,0.75,0.85,0.95,0.80,Asia Pacific averageGLOBAL,1.00,1.00,1.00,1.00,Default global factor
8.5 Fixed cost adjustment
Fixed cost should not fully follow labor factor.
Recommended adjustment:
adjusted_fixed_cost=base_fixed_cost × (0.5 + 0.5 × labor_cost_factor)
This reflects that fixed cost includes both labor-sensitive and non-labor-sensitive items.

9. Generation Logic
9.1 Inputs
node_character_cost_profile_master.csvproduct_price_tier_master.csvregion_cost_factor_master.csvnode master / node character mapping
9.2 Output
pysi/master_data/node_product_money_master.csv
9.3 Conceptual flow
for each product:  read product price tierfor each node:  determine node_character  determine region / country  get node_character cost profile  apply product tier price  apply region / country factors  calculate node-product money values  write node_product_money_master row

10. Mapping to Current node_product_money_master.csv
Current simplified columns may include:
node_nameproduct_nameinventory_unit_valuerevenue_unit_valuevariable_cost_unit_valuefixed_cost_weekly
Mapping:
ConceptCurrent columninventory / acquisition-like valueinventory_unit_valueship / revenue pricerevenue_unit_valuevariable / logistics / handling / SGA approximationvariable_cost_unit_valuefixed / HQ / facility / staff allocationfixed_cost_weekly
If richer columns exist later:
purchase_cost_per_lotvalue_added_cost_per_lotlogistics_cost_per_lotsga_cost_per_lottax_tariff_cost_per_lottarget_profit_per_lotship_price_per_lot
then the generation logic should map directly to those fields.

11. Current Phase 2B+7a Recommended Simplified Calculation
For current simplified master:
11.1 revenue_unit_value
Use role-based target price ladder.
Example for BASE:
supply_point: 20MOM/PAD:      550 - 650DAD:          700 - 760WS:           760 - 800RT:           820 - 880CS:           899 - 950
Example for PRO:
supply_point: 30MOM/PAD:      720 - 850DAD:          950 - 1050WS:           1000 - 1100RT:           1150 - 1250CS:           1199 - 1299
11.2 inventory_unit_value
Use acquisition-like value.
For most physical nodes:
BASE inventory_unit_value ≈ revenue_unit_value × purchase_pctPRO  inventory_unit_value ≈ revenue_unit_value × purchase_pct
For supply_point:
inventory_unit_value = 0
because supply_point is not a physical inventory node in this interpretation.
11.3 variable_cost_unit_value
Approximate:
variable_cost_unit_value=revenue_unit_value × (variable_pct + sga_pct)× applicable region factor
For supply_point, use small HQ/PSI variable allocation:
BASE: 4PRO: 6
11.4 fixed_cost_weekly
Approximate:
fixed_cost_weekly=revenue_unit_value × fixed_pct × fixed_scale
Since this is weekly fixed cost, use a scaling convention.
For demonstration:
fixed_scale = 10
For supply_point:
BASE: 16PRO: 24
or another small per-product allocation value.

12. supply_point Handling
supply_point must be kept small in the E2E Lane chart.
It should represent:
HQ / PSI / business management allocation
not:
product purchase and resale
Recommended current simplified values:
node_name,product_name,inventory_unit_value,revenue_unit_value,variable_cost_unit_value,fixed_cost_weeklysupply_point,IPHONE_NM_2028_BASE,0,20,4,16supply_point,IPHONE_NM_2028_PRO,0,30,6,24
This keeps supply_point visible but not dominant.

13. Global Marketing / Brand Management Handling
Global Marketing / Brand Management is a major cost layer, but it should not be fully embedded in the E2E physical supply chain chart in Phase 2B+7a.
Recommended treatment:
Not included in main E2E operational cost stack for now.Handled later as reference / allocation layer.
Possible future fields:
global_brand_allocation_per_lotglobal_marketing_allocation_per_lotbrand_royalty_cost_per_lot
Future interpretation:
CS / regional business earns profitthen brand / marketing / royalty allocation reduces remitted profit
This should be handled in a later phase.

14. Tests
Add test file:
tests/master_data_test_node_character_cost_profile_master.py
Suggested assertions if master files are added:
- node_character_cost_profile_master.csv exists- required node_character profiles exist:  DAD, WS, RT, CS, MOM, PAD, supply_point- each ship_price-based profile sums to approximately 1.0- supply_point profile_basis is own_allocated_cost- supply_point purchase_pct == 0
Add test file:
tests/master_data_test_base_pro_money_master_realism.py
Suggested assertions:
- BASE rows exist- PRO rows exist- PRO covers at least BASE nodes- PRO total revenue_unit_value > BASE total revenue_unit_value- PRO total inventory_unit_value > BASE total inventory_unit_value- supply_point inventory_unit_value == 0- supply_point revenue_unit_value is small relative to CS revenue_unit_value
Avoid exact-value tests unless values are intentionally fixed.

15. Manual Verification
After generating / updating node_product_money_master.csv:
python -m main
Run Full Plan.
Check:
Product: IPHONE_NM_2028_BASELeaf:    CS_US_MAINSTREAMProduct: IPHONE_NM_2028_PROLeaf:    CS_US_PREMIUM
Both should generate:
full_price E2E lane chartdelta_only E2E lane chart
Expected visual result:
PRO final price > BASE final pricesupply_point remains smallCS shows market-facing priceDAD/WS/RT show operational cost structure

16. Acceptance Criteria
Phase 2B+7a is accepted when:


node_character cost profile master is defined.


product price tier master is defined.


region cost factor master is defined or at least designed.


supply_point is treated as HQ / PSI allocation node, not product trading node.


Global Marketing / Brand Management is excluded from main E2E chart for now.


BASE and PRO cost structures remain chartable.


PRO appears as premium relative to BASE.


Existing Phase 2B tests pass.


Runtime output CSV / PNG files are not committed.



17. Future Phase 2B+7b
Possible next phase:
Node Character Cost Profile Preprocessor
This would implement:
node_character_cost_profile_master.csv× product_price_tier_master.csv× region_cost_factor_master.csv→ node_product_money_master.csv
as an actual generator.

18. Summary
Phase 2B+7a defines the master structure that explains where realistic node_product_money_master.csv values should come from.
The key transition is:
manual node_product_money_master tuning↓node_character based cost profile generation
This makes WOM costing model building more repeatable, scalable, and explainable.
This is the natural next modeling layer after Phase 2B+7.