# Edge-Based Price Condition Model v0.1

## 1. 目的

本書は、WOM における金額編の中心概念として、**Edge-Based Price Condition Model** を定義する。

本モデルの基本思想は、次の一文で表現できる。

```text
Edge Master defines Price Conditions.

すなわち、価格条件は node に属する静的属性ではなく、edge 上の取引条件・物流条件として定義される。

この考え方により、WOM は以下を simple かつ汎用的に表現できる。

親子 node 間の価格伝播
internal / external 価格の区別
freight / insurance / duty / handling の付加
price condition と weekly quantity の分離
event flow tracing と金額編の自然な接続
2. 背景

従来、金額編を node 中心で定義すると、以下の問題が起きやすい。

価格が「どこからどこへ流れるか」を表現しにくい
freight / insurance / duty などの物流付加費の置き場が曖昧になる
CIF / DDP / EXW などの trade condition が node に押し込まれて不自然になる
親 node の出荷価格と子 node の購入原価の連鎖が明示しにくい

一方、サプライチェーン上の価格は、本来次の条件で決まる。

from_node
to_node
product
time bucket
incoterm
trade / logistics conditions

したがって、価格条件は node よりも edge に定義する方が自然である。

3. 基本概念
3.1 node の役割

node は、拠点の業務意味を表す。

例:

MOM
DAD
WS
RT
CS

node が持つ主な意味は次の通り。

business role
organization / company
country / region
capability
固有の補助原価条件
inventory / fixed cost の残高・期間属性

つまり、node は business role を定義する。

3.2 edge の役割

edge は、拠点間の流れに付随する commercial / logistics condition を表す。

edge が持つ主な意味は次の通り。

transfer_price_per_lot
freight_cost_per_lot
insurance_cost_per_lot
duty_cost_per_lot
handling_cost_per_lot
incoterm
effective period

つまり、edge は price condition を定義する。

3.3 PSI の役割

PSI は weekly quantity を保持する。

例:

shipped_lots
inbound_lots
produced_lots
opening_inventory_lots
ending_inventory_lots
throughput_lots

PSI は金額を直接持たない。
金額は、単価補完後に unit price × quantity で評価する。

4. コア原則
4.1 価格条件は edge に定義する
Edge Master defines Price Conditions.

この原則により、価格は「拠点の属性」ではなく「流れの条件」として扱われる。

4.2 購入原価は親の出荷価格から伝播する

本モデルの中核式は次の通り。

purchase_cost_per_lot@child = ship_price_per_lot@parent

必要に応じて、edge 上の物流条件を加算する。

purchase_cost_per_lot@child
= transfer_price_per_lot
+ freight_cost_per_lot
+ insurance_cost_per_lot
+ duty_cost_per_lot
+ handling_cost_per_lot

これにより、次の業務関係が明示される。

PURCHASE COST@child = SHIP PRICE@parent
4.3 金額評価は単価 × 数量で行う

本モデルにおける全金額評価は、次の原則に従う。

amount = unit price × quantity

ここで、

unit price は master から補完される
quantity は PSI または event flow tracing から取得する
5. WOM 全体アーキテクチャ上の位置づけ

Edge-Based Price Condition Model を採用すると、WOM は次の 3 層で整理できる。

Layer 1: Edge Master

価格条件を定義する層

例:

transfer price
freight
insurance
duty
handling
incoterm
Layer 2: PSI

週次数量を保持する層

例:

S / I / P
inbound / outbound lots
weekly inventory lots
Layer 3: Money Evaluation

単価 × 数量で金額評価する層

例:

revenue
purchase amount
inventory value
variable cost
fixed cost
tax
profit

この 3 層分離により、WOM の金額編は simple かつ generic になる。

6. master 構成との対応

本モデルは、WOM 金額編 master 構成 v0.2 と整合する。

6.1 node_master.csv

定義対象:

node の物理・業務属性
node_character
company / country / capability
6.2 node_character_policy_master.csv

定義対象:

node_character ごとの標準ポリシー
standard rate / fallback rule
6.3 node_product_money_master.csv

定義対象:

node × product の結果単価または override 値
purchase / ship / inventory / variable / fixed / tax
6.4 edge_product_money_master.csv

定義対象:

from_node × to_node × product の価格条件
price propagation の起点
6.5 valuation_policy_master.csv

定義対象:

inventory valuation
issue cost method
price propagation method
7. このモデルで表現できるもの

本モデルにより、次の表現が自然になる。

7.1 internal transfer price

例:

MOM → DAD
DAD → WS
WS → RT
7.2 external selling price

例:

RT → CS
direct online → consumer
7.3 logistics adders

例:

freight
insurance
duty
handling
7.4 incoterm 差異

例:

EXW
CIF
DDP
7.5 time-dependent price conditions

例:

period-based transfer price revision
tariff change
emergency logistics premium
8. このモデルで解決できる課題
8.1 親子間価格の整合

親 node の出荷価格と、子 node の購入原価が自然につながる。

8.2 物流費の置き場の明確化

freight / insurance / duty / handling を node ではなく edge に置ける。

8.3 internal / external price の分離

local profit と consolidated profit を分けて扱いやすくなる。

8.4 price propagation の標準化

価格連鎖のルールを master ベースで標準化できる。

8.5 event flow への接続

ship / receive / transfer event に、対応する price condition を直接ひも付けられる。

9. 注意点
9.1 在庫は edge ではなく node に残る

inventory_value は B/S 残高であり、flow の属性ではなく node 側の残高である。

したがって、価格条件は edge に置くが、在庫残高は node に保持する。

9.2 固定費は原則 node 側

固定費は通常、拠点単位・期間単位で発生するため、原則として node 側で扱う。

例:

fixed_cost_per_week
facility fixed charge
labor fixed charge
9.3 連結利益では内部利益を消去する

edge 上に internal transfer price を持たせると、node 単位の local profit は見やすくなる。

ただし、サプライチェーン全体の consolidated profit を計算する場合は、internal revenue / internal margin を消去する必要がある。

10. 最小実装の考え方

最初の実装では、次の順で導入するのが自然である。

Step 1

edge_product_money_master.csv に manual の transfer price を持つ

Step 2

purchase_cost_per_lot@child = prev ship price を補完する

Step 3

物流費を add-on として purchase cost に加算する

Step 4

ship_price_per_lot を node 側で再計算する

Step 5

PSI 数量を掛けて weekly amount を計算する

11. 処理イメージ

本モデルの概念フローは次の通り。

edge master
→ price condition
→ purchase / ship unit price propagation
→ node product unit price table
→ PSI weekly quantities
→ money evaluation

より簡潔には、次の 3 行で表現できる。

Edge Master defines Price Conditions.
PSI holds Weekly Quantities.
Money Evaluation = Unit Price × Quantity.
12. 一言サマリ

Edge-Based Price Condition Model とは、

価格は node に属する属性ではなく、edge に定義される取引条件である

という考え方である。

このモデルにより WOM は、

node は business role
edge は price condition
PSI は quantity
money evaluation は unit price × quantity

という、simple で汎用的な supply chain cost model を持つことができる。