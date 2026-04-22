# WOM 金額編 処理フロー v0.1

## 1. 目的

本書は、WOM における金額編の処理フローを定義する。

WOM 金額編では、数量編の PSI 計画結果を前提として、`node × product × week` 単位で以下を評価する。

- revenue
- purchase amount
- inventory value
- variable cost
- fixed cost
- tax
- profit

本フローは、次の 2 フェーズで構成される。

1. **単価補完フェーズ**
2. **週次金額計算フェーズ**

---

## 2. 全体像

WOM 金額編の全体処理は、概念的には以下の順で行う。

```text
master
→ 単価補完
→ 単価表
→ PSI週次数量
→ 週次金額計算
→ node×product×week 金額表
このとき、
•	master は 単価の世界 
•	PSI は 数量の世界 
•	evaluator は 金額化の世界 
を担う。
________________________________________
3. 基本思想
3.1 最小 cost object
WOM の共通ロット 1 単位を、金額計算の最小単位とする。
1 common lot = 1 cost object
3.2 B/S と P/L の分離
•	inventory_value は B/S 残高 
•	P/L に入るのは inventory_value そのものではなく、 
o	inventory delta 
o	または issue cost
として扱う 
3.3 単価と数量の分離
•	単価は master から決める 
•	金額は 単価 × 数量 で計算する 
3.4 local と consolidated の分離
•	各 node の採算確認には local node profit 
•	サプライチェーン全体の利益確認には consolidated E2E profit 
を用いる。
________________________________________
4. フェーズ1: 単価補完フェーズ
4.1 目的
単価補完フェーズの目的は、node × product および edge × product の金額条件を確定し、週次数量計算に必要な unit price / unit cost を整備することである。
このフェーズの成果物は、少なくとも次の単価表である。
•	purchase_cost_per_lot 
•	ship_price_per_lot 
•	inventory_unit_value_per_lot 
•	variable_cost_per_lot 
•	fixed_cost_per_week 
•	tax_rate 
________________________________________
4.2 入力 master
単価補完フェーズでは、以下の master を読み込む。
4.2.1 node_master.csv
物理 node 台帳。
主な役割:
•	node_name 
•	node_character 
•	company / country 
•	capability 
4.2.2 node_character_policy_master.csv
node_character ごとの標準会計ポリシー。
主な役割:
•	標準税率 
•	標準 carrying rate 
•	標準 fixed cost basis 
•	fallback rule 
4.2.3 node_product_money_master.csv
node_name × product_name の明示単価・固定費。
主な役割:
•	purchase cost 
•	ship price 
•	inventory value 
•	variable cost 
•	fixed cost 
•	tax 
4.2.4 edge_product_money_master.csv
from_node × to_node × product_name の価格・物流条件。
主な役割:
•	transfer price 
•	freight 
•	insurance 
•	duty 
•	handling 
•	incoterm 
4.2.5 valuation_policy_master.csv
在庫評価法・払出原価計算法・価格伝播方法。
________________________________________
4.3 処理手順
4.3.1 対象 node × product の母集合を作る
対象は少なくとも以下から作成する。
•	PSI tree 上に存在する node 
•	シナリオ対象 product 
•	money master に現れる node × product 
対象の最小粒度は以下とする。
(node_name, product_name)
________________________________________
4.3.2 edge × product の原単価を確定する
対象キー:
(from_node, to_node, product_name, effective period)
ここで確定する主な項目:
•	transfer_price_per_lot 
•	freight_cost_per_lot 
•	insurance_cost_per_lot 
•	duty_cost_per_lot 
•	handling_cost_per_lot 
優先順位:
1.	edge master の明示値 
2.	親 node の ship_price_per_lot 継承 
3.	fallback なし 
________________________________________
4.3.3 child node の purchase_cost_per_lot を補完する
基本式:
purchase_cost_per_lot@child
= transfer_price_per_lot
+ freight_cost_per_lot
+ insurance_cost_per_lot
+ duty_cost_per_lot
+ handling_cost_per_lot
最小版では、以下の簡略形を採用してもよい。
purchase_cost_per_lot@child = ship_price_per_lot@parent
この処理により、以下の関係を成立させる。
PURCHASE COST@child = SHIP PRICE@parent
________________________________________
4.3.4 variable_cost_per_lot を補完する
優先順位:
1.	node_product_money_master の明示値 
2.	node_character_policy_master の標準 rate / 標準額 
3.	fallback 0 
例:
•	MOM: 製造加工変動費 
•	DAD: yard handling 費 
•	WS: warehouse handling / storage 費 
•	RT / CS: 販売変動費（必要時） 
________________________________________
4.3.5 fixed_cost_per_week を補完する
優先順位:
1.	node_product_money_master の明示値 
2.	node_character_policy_master の標準固定費 
3.	fallback 0 
最小版では、固定費は per week で保持する。
________________________________________
4.3.6 ship_price_per_lot を補完する
優先順位:
1.	node_product_money_master の明示値 
2.	自動計算 
自動計算式:
ship_price_per_lot
= purchase_cost_per_lot
+ variable_cost_per_lot
+ allocated_fixed_cost_per_lot
+ target_profit_unit
最小版では、allocated_fixed_cost_per_lot は簡略扱いでよい。
________________________________________
4.3.7 inventory_unit_value_per_lot を補完する
優先順位:
1.	node_product_money_master の明示値 
2.	purchase_cost_per_lot 
3.	加工 node の場合は
purchase_cost_per_lot + capitalizable costs 
最小版では、以下を採用できる。
inventory_unit_value_per_lot = purchase_cost_per_lot
________________________________________
4.3.8 tax_rate を補完する
優先順位:
1.	node_product_money_master の明示値 
2.	node_character_policy_master.default_tax_rate 
3.	valuation_policy_master の default 
________________________________________
4.4 単価補完フェーズの出力
このフェーズの出力は、各 node × product に対する単価表である。
node_name
product_name
purchase_cost_per_lot
ship_price_per_lot
inventory_unit_value_per_lot
variable_cost_per_lot
fixed_cost_per_week
tax_rate
この出力が、週次金額計算フェーズの入力になる。
________________________________________
5. フェーズ2: 週次金額計算フェーズ
5.1 目的
週次金額計算フェーズの目的は、PSI の週次数量を用いて、各週の金額を算出することである。
このフェーズでは、node × product × week 単位で以下を計算する。
•	revenue 
•	purchase amount 
•	variable cost 
•	fixed cost 
•	ending inventory value 
•	issue cost 
•	tax 
•	profit 
________________________________________
5.2 入力
5.2.1 単価表
フェーズ1で補完した単価表。
5.2.2 PSI 週次数量
最低限必要な数量は次の通り。
•	shipped_lots 
•	inbound_lots 
•	throughput_lots 
•	opening_inventory_lots 
•	ending_inventory_lots 
必要に応じて追加:
•	produced_lots 
•	sold_lots 
•	scrapped_lots 
________________________________________
5.3 処理手順
5.3.1 revenue を計算する
基本式:
revenue = shipped_lots × ship_price_per_lot
最小版では、まず CS / RT など external に近い node から開始してもよい。
拡張版では、すべての node が internal revenue を持つ。
________________________________________
5.3.2 purchase amount を計算する
基本式:
purchase_amount = inbound_lots × purchase_cost_per_lot
これにより、親 node の出荷額と子 node の購入額が数量ベースでつながる。
________________________________________
5.3.3 variable cost を計算する
基本式:
variable_cost = throughput_lots × variable_cost_per_lot
最小版では、throughput_lots は出荷 lot または処理対象 lot を用いればよい。
________________________________________
5.3.4 fixed cost を計算する
基本式:
fixed_cost = fixed_cost_per_week
最小版では、週次固定費をそのまま使う。
将来は product / capacity / utilization ベースの配賦へ拡張可能。
________________________________________
5.3.5 ending inventory value を計算する
基本式:
ending_inventory_value
= ending_inventory_lots × inventory_unit_value_per_lot
これは B/S 残高である。
________________________________________
5.3.6 inventory delta / issue cost を計算する
P/L に在庫を反映するため、以下を計算する。
最小版
inventory_delta
= ending_inventory_value - opening_inventory_value
推奨版
issue_cost
= opening_inventory_value + inbound_value - ending_inventory_value
WOM 金額編としては、推奨版の方が管理会計上自然である。
________________________________________
5.3.7 local profit を計算する
各 node × product × week に対して、税前利益を計算する。
profit_before_tax
= revenue
- issue_cost or purchase-related cost
- variable_cost
- fixed_cost
その後、税を計算する。
tax = profit_before_tax × tax_rate
profit_after_tax = profit_before_tax - tax
________________________________________
5.3.8 consolidated profit を別計算する
E2E 全体の利益を算出する場合、internal revenue / internal purchase を消去する。
つまり、連結ベースでは、
•	external revenue のみ残す 
•	internal transfer margin は消す 
これにより、
•	local node profit 
•	consolidated E2E profit 
を分離して扱う。
________________________________________
5.4 週次金額計算フェーズの出力
このフェーズの出力は、各 node × product × week に対する週次金額表である。
week
node_name
product_name
shipped_lots
inbound_lots
ending_inventory_lots
revenue
purchase_amount
variable_cost
fixed_cost
ending_inventory_value
issue_cost
profit_before_tax
tax
profit_after_tax
________________________________________
6. フェーズ間の関係
フェーズ1の出力
•	単価表 
フェーズ2の入力
•	単価表 
•	PSI週次数量 
フェーズ2の出力
•	週次金額表 
したがって、WOM 金額編全体は以下の流れで表現できる。
master
→ 単価補完
→ 単価表
→ PSI数量
→ 週次金額計算
→ node×product×week金額表
________________________________________
7. 実務上のポイント
7.1 単価と数量を混ぜない
•	master は unit amount の世界 
•	PSI は qty の世界 
•	evaluator は amount の世界 
として分離する。
7.2 inventory_value は残高
•	B/S の残高として保持する 
•	P/L には増減または払出原価として反映する 
7.3 local と consolidated を分ける
•	node 単体の内部採算 
•	全社連結利益 
を混同しない。
7.4 構成比は結果であり、入力ではない
入力 master は、共通ロット 1 単位あたりの金額を持つ。
構成比は、計算結果を report で可視化する際に使う。
________________________________________
8. 一言サマリ
単価補完フェーズ
親子 edge と node の master から、1 lot あたりの価格・原価・在庫評価単価を確定するフェーズ
週次金額計算フェーズ
確定した単価に weekly の lot 数量を掛けて、売上・購入・在庫・費用・利益を計算するフェーズ

