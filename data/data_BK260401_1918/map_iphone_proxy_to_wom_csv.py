
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent
SRC = BASE / "iphone_proxy_dataset_v0_1"
OUT = BASE / "iphone_wom_mapped_v0_1"
OUT.mkdir(exist_ok=True)

def load(name):
    return pd.read_csv(SRC / name)

product_master = load("product_master.csv")
part_master = load("part_master.csv")
bom_relation = load("bom_relation.csv")
node_master = load("node_master.csv")
edge_master = load("edge_master.csv")
channel_master = load("channel_master.csv")
consumer_segment = load("consumer_segment_master.csv")
capacity_master = load("capacity_master.csv")
cost_master = load("cost_master.csv")
price_master = load("price_master.csv")
leadtime_master = load("leadtime_master.csv")
monthly_demand = load("monthly_demand_master.csv")
geo_master = load("geo_master.csv")

# --------------------------------
# 1) node_geo.csv
# --------------------------------
node_geo = node_master[["node_id","lat","lon"]].rename(columns={"node_id":"node_name"})
node_geo.to_csv(OUT / "node_geo.csv", index=False, encoding="utf-8-sig")

# --------------------------------
# Assumption tables
# --------------------------------
node_type_defaults = {
    "PART_PLANT": {"process_capa": 999999, "SS_days": 7, "PSI_graph_flag":"OFF", "buffering_stock_flag":"OFF"},
    "ASSEMBLY_PLANT": {"process_capa": 250000, "SS_days": 7, "PSI_graph_flag":"ON", "buffering_stock_flag":"OFF"},
    "REGIONAL_HUB": {"process_capa": 200000, "SS_days": 14, "PSI_graph_flag":"ON", "buffering_stock_flag":"ON"},
    "COUNTRY_DC": {"process_capa": 100000, "SS_days": 10, "PSI_graph_flag":"ON", "buffering_stock_flag":"ON"},
    "CHANNEL_NODE": {"process_capa": 100000, "SS_days": 5, "PSI_graph_flag":"ON", "buffering_stock_flag":"OFF"},
    "CONSUMER_NODE": {"process_capa": 999999, "SS_days": 0, "PSI_graph_flag":"ON", "buffering_stock_flag":"OFF"},
}
node_type_map = dict(zip(node_master["node_id"], node_master["node_type"]))

def get_lt_days(f, t):
    m = leadtime_master[(leadtime_master["from_node_id"] == f) & (leadtime_master["to_node_id"] == t)]
    if len(m):
        return int(m.iloc[0]["lt_days"])
    return 1

# --------------------------------
# 2) product_tree_outbound.csv
# root -> assembly -> hub -> country -> channel -> consumer
# --------------------------------
out_rows = []
products = list(product_master["product_id"])
for p in products:
    roots = node_master[node_master["node_type"] == "ASSEMBLY_PLANT"]["node_id"].tolist()
    for asm in roots:
        nd = node_master[node_master["node_id"] == asm].iloc[0]
        dflt = node_type_defaults.get(nd["node_type"], {})
        out_rows.append({
            "Product_name": p, "Parent_node":"root", "Child_node": asm, "child_node_name": asm,
            "lot_size": 1000, "leadtime": 1, "process_capa": dflt.get("process_capa",100000),
            "long_vacation_weeks":"[]", "LT_boat": 21, "LT_air": 7, "LT_qourier": 3, "weeks_year": 52,
            "SS_days": dflt.get("SS_days",7), "TAX_currency_condition":"profile", "HS_code":"",
            "customs_tariff_rate": 0, "price_elasticity": 0, "cost_standard_flag":0, "AR_lead_time":30,
            "AP_lead_time":45, "PSI_graph_flag": dflt.get("PSI_graph_flag","ON"),
            "buffering_stock_flag": dflt.get("buffering_stock_flag","OFF")
        })

    for _, e in edge_master[edge_master["edge_type"].isin(["FG_OUTBOUND","COUNTRY_REPLENISH","CHANNEL_SUPPLY","SELL_THROUGH"])].iterrows():
        child = e["to_node_id"]
        nd = node_master[node_master["node_id"] == child].iloc[0]
        dflt = node_type_defaults.get(nd["node_type"], {})
        out_rows.append({
            "Product_name": p, "Parent_node": e["from_node_id"], "Child_node": child, "child_node_name": child,
            "lot_size": 1000, "leadtime": int(e["default_lt_days"]), "process_capa": dflt.get("process_capa",100000),
            "long_vacation_weeks":"[]", "LT_boat": 21 if e["transport_mode"]=="OCEAN" else int(e["default_lt_days"]),
            "LT_air": 7 if e["transport_mode"]=="AIR" else int(e["default_lt_days"]),
            "LT_qourier": 3 if e["transport_mode"] in ["AIR","DIGITAL_SELLTHROUGH"] else int(e["default_lt_days"]),
            "weeks_year": 52, "SS_days": dflt.get("SS_days",7), "TAX_currency_condition":"profile", "HS_code":"",
            "customs_tariff_rate": 0, "price_elasticity": 0, "cost_standard_flag":0, "AR_lead_time":30,
            "AP_lead_time":45, "PSI_graph_flag": dflt.get("PSI_graph_flag","ON"),
            "buffering_stock_flag": dflt.get("buffering_stock_flag","OFF")
        })

product_tree_outbound = pd.DataFrame(out_rows).drop_duplicates()
product_tree_outbound.to_csv(OUT / "product_tree_outbound.csv", index=False, encoding="utf-8-sig")

# --------------------------------
# 3) product_tree_inbound.csv
# root -> generic supply_point -> part plants -> assembly plants
# Product_name uses part_id because inbound in this proxy is part-centric.
# --------------------------------
in_rows = []
part_plants = node_master[node_master["node_type"] == "PART_PLANT"]["node_id"].tolist()
assembly_plants = node_master[node_master["node_type"] == "ASSEMBLY_PLANT"]["node_id"].tolist()

for part in part_master["part_id"]:
    # root -> supply_point
    in_rows.append({
        "Product_name": part, "Parent_node":"root", "Child_node":"supply_point", "child_node_name":"supply_point",
        "lot_size": int(part_master.loc[part_master["part_id"]==part, "standard_lot_size"].iloc[0]),
        "leadtime": 1, "process_capa": 999999, "long_vacation_weeks":"[]",
        "LT_boat":21, "LT_air":7, "LT_qourier":3, "weeks_year":52, "SS_days":7,
        "TAX_currency_condition":"profile", "HS_code":"", "customs_tariff_rate":0, "price_elasticity":0,
        "cost_standard_flag":0, "AR_lead_time":30, "AP_lead_time":45, "PSI_graph_flag":"OFF", "buffering_stock_flag":"OFF"
    })
    plants = []
    if part == "SOC_A18": plants = ["SOC_TAIWAN_FAB"]
    elif part == "OLED_68": plants = ["DISPLAY_KOREA_PLANT"]
    elif part == "MEM_256": plants = ["MEM_CHINA_PLANT"]
    elif part == "CAM_PRO": plants = ["CAM_JAPAN_MODULE"]
    elif part == "BATT_X": plants = ["BATT_CHINA_PLANT"]
    elif part == "HOUSING_AL": plants = ["HOUSING_VN_PLANT"]
    elif part == "PCB_MAIN": plants = ["PCB_TH_PLANT"]
    elif part == "PKG_BOX": plants = ["PKG_INDIA_PLANT"]

    for pp in plants:
        in_rows.append({
            "Product_name": part, "Parent_node":"supply_point", "Child_node":pp, "child_node_name":pp,
            "lot_size": int(part_master.loc[part_master["part_id"]==part, "standard_lot_size"].iloc[0]),
            "leadtime": 1, "process_capa": 999999, "long_vacation_weeks":"[]",
            "LT_boat":21, "LT_air":7, "LT_qourier":3, "weeks_year":52, "SS_days":7,
            "TAX_currency_condition":"profile", "HS_code":"", "customs_tariff_rate":0, "price_elasticity":0,
            "cost_standard_flag":0, "AR_lead_time":30, "AP_lead_time":45, "PSI_graph_flag":"OFF", "buffering_stock_flag":"OFF"
        })
        for asm in assembly_plants:
            lt = get_lt_days(pp, asm)
            in_rows.append({
                "Product_name": part, "Parent_node":pp, "Child_node":asm, "child_node_name":asm,
                "lot_size": int(part_master.loc[part_master["part_id"]==part, "standard_lot_size"].iloc[0]),
                "leadtime": lt, "process_capa": 999999, "long_vacation_weeks":"[]",
                "LT_boat":21, "LT_air":lt, "LT_qourier":max(1, lt-2), "weeks_year":52, "SS_days":7,
                "TAX_currency_condition":"profile", "HS_code":"", "customs_tariff_rate":0, "price_elasticity":0,
                "cost_standard_flag":0, "AR_lead_time":30, "AP_lead_time":45, "PSI_graph_flag":"OFF", "buffering_stock_flag":"OFF"
            })
product_tree_inbound = pd.DataFrame(in_rows).drop_duplicates()
product_tree_inbound.to_csv(OUT / "product_tree_inbound.csv", index=False, encoding="utf-8-sig")

# --------------------------------
# 4) offering_price_ASIS_TOBE.csv
# Use product/country-channel proxy. node_name uses WOM node id at sales-side nodes.
# --------------------------------
sales_nodes = node_master[node_master["node_type"].isin(["ASSEMBLY_PLANT","REGIONAL_HUB","COUNTRY_DC","CHANNEL_NODE","CONSUMER_NODE"])]["node_id"].tolist()
price_rows = []
for _, p in price_master.iterrows():
    geo = p["country_geo_id"]
    # map to channel node ids if available
    channel_id = str(p["channel_id"]) if pd.notna(p["channel_id"]) else ""
    node_name = ""
    if channel_id == "US_APPLE_ONLINE": node_name = "CHANNEL_US_APPLE_ONLINE"
    elif channel_id == "US_CARRIER": node_name = "CHANNEL_US_CARRIER"
    elif channel_id == "DE_APPLE_ONLINE": node_name = "CHANNEL_DE_APPLE_ONLINE"
    elif channel_id == "IN_ECOM": node_name = "CHANNEL_IN_ECOM"
    elif channel_id == "CN_APPLE_ONLINE": node_name = "CHANNEL_CN_APPLE_ONLINE"
    elif channel_id == "JP_APPLE_RETAIL": node_name = "CHANNEL_JP_APPLE_RETAIL"
    else:
        node_name = f"COUNTRY_NODE_{geo.replace('COUNTRY_','')}"
    price_rows.append({
        "product_name": p["product_id"],
        "node_name": node_name,
        "offering_price_ASIS": p["net_price"],
        "offering_price_TOBE": p["net_price"] * 1.03
    })
offering_price = pd.DataFrame(price_rows).drop_duplicates()
offering_price.to_csv(OUT / "offering_price_ASIS_TOBE.csv", index=False, encoding="utf-8-sig")

# --------------------------------
# 5) sku_cost_table_inbound.csv / outbound.csv
# --------------------------------
cost_cols = [
    "product_name","node_name","price_sales_shipped","cost_total","profit","marketing_promotion","sales_admin_cost",
    "SGA_total","logistics_costs","warehouse_cost","direct_materials_costs","tariff_cost","purchase_total_cost",
    "prod_indirect_labor","prod_indirect_others","direct_labor_costs","depreciation_others","manufacturing_overhead"
]

# helper base
def cost_row(prod, node, price, cost_total, direct_mat, logi, wh, dl, pil, pio, dep, mkt=0, sga=0, tariff=0):
    purchase = direct_mat + tariff + logi
    profit = price - cost_total
    return {
        "product_name": prod, "node_name": node, "price_sales_shipped": round(price,2), "cost_total": round(cost_total,2),
        "profit": round(profit,2), "marketing_promotion": round(mkt,2), "sales_admin_cost": round(sga,2),
        "SGA_total": round(mkt+sga,2), "logistics_costs": round(logi,2), "warehouse_cost": round(wh,2),
        "direct_materials_costs": round(direct_mat,2), "tariff_cost": round(tariff,2), "purchase_total_cost": round(purchase,2),
        "prod_indirect_labor": round(pil,2), "prod_indirect_others": round(pio,2), "direct_labor_costs": round(dl,2),
        "depreciation_others": round(dep,2), "manufacturing_overhead": round(pil+pio+dep,2)
    }

# inbound part costs
in_cost_rows = []
part_cost_map = cost_master[cost_master["cost_type"]=="PROCUREMENT_COST"].set_index("product_or_part_id")["amount"].to_dict()
for part, cost in part_cost_map.items():
    source_nodes = product_tree_inbound[product_tree_inbound["Product_name"]==part]["Child_node"].unique().tolist()
    for node in source_nodes:
        if node == "supply_point":
            continue
        in_cost_rows.append(cost_row(part, node, price=cost*1.05, cost_total=cost*1.00, direct_mat=cost*0.75, logi=cost*0.08, wh=0, dl=cost*0.07, pil=cost*0.03, pio=0, dep=cost*0.07, sga=cost*0.02))
sku_cost_inbound = pd.DataFrame(in_cost_rows)[cost_cols].drop_duplicates()
sku_cost_inbound.to_csv(OUT / "sku_cost_table_inbound.csv", index=False, encoding="utf-8-sig")

# outbound finished-goods costs
out_cost_rows = []
base_price_us = float(price_master[(price_master["product_id"]=="IPHONE_NM_2028_BASE") & (price_master["country_geo_id"]=="COUNTRY_US")]["net_price"].iloc[0])
bom_base = sum(part_cost_map.values())
asm_costs = cost_master[cost_master["cost_type"]=="ASSEMBLY_COST"].set_index("object_id")["amount"].to_dict()
for prod in ["IPHONE_NM_2028_BASE","IPHONE_NM_2028_PRO"]:
    for node in sales_nodes:
        nt = node_type_map[node]
        price = base_price_us if prod.endswith("BASE") else base_price_us * 1.20
        direct_mat = bom_base * (1.0 if prod.endswith("BASE") else 1.12)
        asm = asm_costs.get(node, 0)
        wh = 2.0 if nt in ["REGIONAL_HUB","COUNTRY_DC"] else 0.5 if nt=="CHANNEL_NODE" else 0
        logi = 8.0 if nt=="REGIONAL_HUB" else 3.0 if nt=="COUNTRY_DC" else 1.5 if nt=="CHANNEL_NODE" else 0.5 if nt=="CONSUMER_NODE" else 6.0 if nt=="ASSEMBLY_PLANT" else 0
        dl = asm if asm else 2.0 if nt=="CHANNEL_NODE" else 1.0
        pil = 1.0 if nt=="ASSEMBLY_PLANT" else 0
        dep = 1.5 if nt=="ASSEMBLY_PLANT" else 0
        sga = 12.0 if nt=="CHANNEL_NODE" else 8.0 if nt=="COUNTRY_DC" else 4.0 if nt=="REGIONAL_HUB" else 2.0
        mkt = 6.0 if nt in ["CHANNEL_NODE","CONSUMER_NODE"] else 1.0
        tariff = 0.0
        total = direct_mat + logi + wh + dl + pil + dep + sga + mkt + tariff
        out_cost_rows.append(cost_row(prod, node, price, total, direct_mat, logi, wh, dl, pil, 0, dep, mkt=mkt, sga=sga, tariff=tariff))
sku_cost_outbound = pd.DataFrame(out_cost_rows)[cost_cols].drop_duplicates()
sku_cost_outbound.to_csv(OUT / "sku_cost_table_outbound.csv", index=False, encoding="utf-8-sig")

# --------------------------------
# 6) sku_P_month_data.csv
# Monthly production at assembly plants using launch ramp
# --------------------------------
months = [f"m{i}" for i in range(1,13)]
prod_rows = []
prod_profile = [0,0,0,0,0,50000,120000,220000,420000,460000,300000,180000]
for prod in ["IPHONE_NM_2028_BASE","IPHONE_NM_2028_PRO"]:
    split = {
        "ASM_CHINA_MAIN": [0.45,0.42,0.40,0.38,0.36,0.35,0.34,0.33,0.32,0.32,0.31,0.30],
        "ASM_INDIA_MAIN": [0.35,0.36,0.37,0.38,0.39,0.40,0.41,0.42,0.43,0.43,0.44,0.45],
        "ASM_VIETNAM_MAIN":[0.20,0.22,0.23,0.24,0.25,0.25,0.25,0.25,0.25,0.25,0.25,0.25],
    }
    factor = 1.0 if prod.endswith("BASE") else 0.35
    for node, ratio_list in split.items():
        row = {"product_name": prod, "node_name": node, "year": 2028}
        for i,m in enumerate(months):
            row[m] = round(prod_profile[i] * ratio_list[i] * factor, 1)
        prod_rows.append(row)
sku_P_month = pd.DataFrame(prod_rows)
sku_P_month.to_csv(OUT / "sku_P_month_data.csv", index=False, encoding="utf-8-sig")

# --------------------------------
# 7) sku_S_month_data.csv
# Monthly sell-out from demand
# --------------------------------
sales_rows = []
dem = monthly_demand[monthly_demand["product_id"]=="IPHONE_NM_2028_BASE"].copy()
country_for_consumer = node_master.set_index("node_id")["geo_id"].to_dict()

# map consumers to top market nodes close to existing WOM pattern: use consumer nodes directly
for consumer_node, grp in dem.groupby("consumer_node_id"):
    row = {"product_name":"IPHONE_NM_2028_BASE", "node_name": consumer_node, "year": 2028}
    for m in range(1,13):
        qty = grp.loc[grp["bucket_month"]==f"2028-{m:02d}", "final_demand_qty"]
        row[f"m{m}"] = float(qty.iloc[0]) if len(qty) else 0.0
    sales_rows.append(row)
# add pro as 30% of base for premium segments
for consumer_node, grp in dem.groupby("consumer_node_id"):
    row = {"product_name":"IPHONE_NM_2028_PRO", "node_name": consumer_node, "year": 2028}
    premium = any(tag in consumer_node for tag in ["PREMIUM","EARLY"])
    factor = 0.35 if premium else 0.12
    for m in range(1,13):
        qty = grp.loc[grp["bucket_month"]==f"2028-{m:02d}", "final_demand_qty"]
        base = float(qty.iloc[0]) if len(qty) else 0.0
        row[f"m{m}"] = round(base * factor, 1)
    sales_rows.append(row)
sku_S_month = pd.DataFrame(sales_rows)
sku_S_month.to_csv(OUT / "sku_S_month_data.csv", index=False, encoding="utf-8-sig")

# --------------------------------
# 8) tariff_table.csv
# Use edge-level tariffs for international FG flows as proxy
# --------------------------------
tariff_rows = []
for _, e in edge_master[edge_master["edge_type"].isin(["FG_OUTBOUND","COUNTRY_REPLENISH"])].iterrows():
    from_geo = node_master.set_index("node_id").loc[e["from_node_id"], "geo_id"]
    to_geo = node_master.set_index("node_id").loc[e["to_node_id"], "geo_id"]
    rate = 0.0
    if "ASM_CHINA" in e["from_node_id"] and "RH_NA" in e["to_node_id"]:
        rate = 0.10
    elif "ASM_CHINA" in e["from_node_id"] and "RH_EU_WEST" in e["to_node_id"]:
        rate = 0.04
    elif "ASM_INDIA" in e["from_node_id"] and "RH_NA" in e["to_node_id"]:
        rate = 0.02
    elif "ASM_INDIA" in e["from_node_id"] and "RH_EU_WEST" in e["to_node_id"]:
        rate = 0.01
    tariff_rows.append({
        "product_name":"IPHONE_NM_2028_BASE",
        "from_node": e["from_node_id"],
        "to_node": e["to_node_id"],
        "tariff_rate": rate
    })
tariff_table = pd.DataFrame(tariff_rows).drop_duplicates()
tariff_table.to_csv(OUT / "tariff_table.csv", index=False, encoding="utf-8-sig")

print(f"Created mapped files in {OUT}")
