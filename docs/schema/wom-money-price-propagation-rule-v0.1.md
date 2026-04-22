# WOM 金額編 Price Propagation ルール表 v0.1

## 1. 目的

本書は、WOM における金額編の価格伝播ルールを定義する。

WOM の金額編では、`node × product × week` を基本の評価単位とし、各 node において次の金額要素を扱う。

- purchase cost
- ship price
- inventory value
- variable cost
- fixed cost
- tax
- profit

特に、サプライチェーン上の親子 node の関係について、以下の原則を中核ルールとする。

```text
purchase_cost_per_lot@child = ship_price_per_lot@parent
```

このルールにより、前工程・前拠点の出荷価格が、次工程・次拠点の購入原価として連鎖する。

---

## 2. 基本思想

### 2.1 cost object
WOM の共通ロット 1 単位を、金額計算の最小単位とする。

```text
1 common lot = 1 cost object
```

### 2.2 B/S と P/L の分離
- `inventory_value` は B/S 残高である
- P/L には `inventory_value` そのものではなく、在庫増減額または払出原価として反映する

### 2.3 manual override 優先
master に明示設定がある場合、その値を最優先する。  
自動補完は、明示値がない場合にのみ適用する。

### 2.4 local profit と consolidated profit の分離
- node 単体では内部売上・内部購入を持ってよい
- E2E 連結では内部利益を消去し、連結利益を別計算する

---

## 3. 対象 master

本ルール表では、以下の master を前提とする。

### 3.1 node_master.csv
物理 node 台帳。  
`node_name`、`node_character`、display/country/company/capability 等を保持する。

### 3.2 node_character_policy_master.csv
node_character ごとの標準会計ポリシー。  
標準税率、標準固定費 basis、標準 carrying rate などを保持する。

### 3.3 node_product_money_master.csv
`node_name × product_name` ごとの標準単価・固定費を保持する。

主な列:
- `purchase_cost_per_lot`
- `ship_price_per_lot`
- `inventory_unit_value_per_lot`
- `variable_cost_per_lot`
- `fixed_cost_per_week`
- `tax_rate`

### 3.4 edge_product_money_master.csv
`from_node × to_node × product_name` ごとの transfer price / freight / insurance / duty 等を保持する。

### 3.5 valuation_policy_master.csv
在庫評価法、払出原価計算方法、price propagation method 等を保持する。

---

## 4. ルール適用順序

価格伝播・金額補完は、以下の順で行うことを推奨する。

1. `node_master` を読む
2. `node_character_policy_master` を読む
3. `valuation_policy_master` を読む
4. `edge_product_money_master` の manual 値を読む
5. `node_product_money_master` の manual 値を読む
6. 親子 edge に沿って `purchase_cost_per_lot` を補完
7. `variable_cost_per_lot / fixed_cost_per_week` を補完
8. `ship_price_per_lot` を補完
9. `inventory_unit_value_per_lot` を補完
10. `tax_rate` を補完
11. P/L / B/S 評価へ流す

---

## 5. Price Propagation ルール表

| Rule ID | Target | 粒度 | 優先順位 | 自動補完ルール | fallback | 備考 |
|---|---|---|---:|---|---|---|
| PR001 | `edge_product_money_master.transfer_price_per_lot` | from_node × to_node × product × time | 1 | 明示値があればそのまま採用 | なし | edge 原価格 |
| PR002 | `edge_product_money_master.transfer_price_per_lot` | from_node × to_node × product × time | 2 | 親 node の `ship_price_per_lot` を継承 | なし | edge 側未設定時の補完 |
| PR010 | `node_product_money_master.purchase_cost_per_lot` | node × product × time | 1 | 明示値があればそのまま採用 | なし | manual override |
| PR011 | `node_product_money_master.purchase_cost_per_lot` | node × product × time | 2 | `edge.transfer_price_per_lot + freight + insurance + duty + handling` | `prev_node.ship_price_per_lot` | CIF/DDP 条件をここで反映 |
| PR020 | `node_product_money_master.variable_cost_per_lot` | node × product × time | 1 | 明示値があればそのまま採用 | なし | manual override |
| PR021 | `node_product_money_master.variable_cost_per_lot` | node × product × time | 2 | `purchase_cost_per_lot × default_variable_cost_rate` | 0 | policy master に rate がある場合 |
| PR030 | `node_product_money_master.fixed_cost_per_week` | node × product × week | 1 | 明示値があればそのまま採用 | なし | manual override |
| PR031 | `node_product_money_master.fixed_cost_per_week` | node × product × week | 2 | `node_character` 標準固定費を適用 | 0 | policy master に標準額がある場合 |
| PR040 | `node_product_money_master.ship_price_per_lot` | node × product × time | 1 | 明示値があればそのまま採用 | なし | manual override |
| PR041 | `node_product_money_master.ship_price_per_lot` | node × product × time | 2 | `purchase_cost_per_lot + variable_cost_per_lot + allocated_fixed_cost_per_lot + target_profit_unit` | `purchase_cost_per_lot` | node 出荷価格の自動計算 |
| PR050 | `node_product_money_master.inventory_unit_value_per_lot` | node × product × time | 1 | 明示値があればそのまま採用 | なし | manual override |
| PR051 | `node_product_money_master.inventory_unit_value_per_lot` | node × product × time | 2 | `purchase_cost_per_lot` | 0 | merchandise / warehouse の最小版 |
| PR052 | `node_product_money_master.inventory_unit_value_per_lot` | node × product × time | 3 | `purchase_cost_per_lot + capitalizable_variable_cost_per_lot + capitalizable_fixed_cost_per_lot` | PR051 | MOM / PAD などの加工在庫向け |
| PR060 | `node_product_money_master.tax_rate` | node × product × time | 1 | 明示値があればそのまま採用 | なし | manual override |
| PR061 | `node_product_money_master.tax_rate` | node × product × time | 2 | `node_character_policy_master.default_tax_rate` | valuation policy default | 標準税率 |
| PR070 | `local_revenue` | node × product × week | n/a | `shipped_lots × ship_price_per_lot` | 0 | node 単体採算用 |
| PR071 | `local_purchase_cost` | node × product × week | n/a | `inbound_lots × purchase_cost_per_lot` | 0 | node 単体採算用 |
| PR072 | `ending_inventory_value` | node × product × week | n/a | `ending_inventory_lots × inventory_unit_value_per_lot` | 0 | B/S 残高 |
| PR073 | `variable_cost` | node × product × week | n/a | `throughput_lots × variable_cost_per_lot` | 0 | P/L 費用 |
| PR074 | `fixed_cost` | node × product × week | n/a | `fixed_cost_per_week` | 0 | P/L 費用 |
| PR080 | `issue_cost` | node × product × week | n/a | `opening_inventory_value + inbound_value - ending_inventory_value` | `inventory_delta` | P/L に落とす在庫費用 |
| PR090 | `consolidated_revenue` | E2E | n/a | external node のみ計上 | internal transfer revenue 消去 | 連結採算 |
| PR091 | `consolidated_profit` | E2E | n/a | external revenue - external/actual costs | internal margin 消去 | 全体利益 |

---

## 6. 主要ルールの意味

### 6.1 購入原価の伝播
```text
purchase_cost_per_lot@child
= ship_price_per_lot@parent
```

必要に応じて、edge master の物流付加費を加算する。

```text
purchase_cost_per_lot@child
= transfer_price_per_lot
+ freight_cost_per_lot
+ insurance_cost_per_lot
+ duty_cost_per_lot
+ handling_cost_per_lot
```

### 6.2 出荷価格の計算
```text
ship_price_per_lot@node
= purchase_cost_per_lot
+ variable_cost_per_lot
+ allocated_fixed_cost_per_lot
+ target_profit_unit
```

### 6.3 在庫残高評価
```text
ending_inventory_value
= ending_inventory_lots × inventory_unit_value_per_lot
```

### 6.4 変動費
```text
variable_cost
= throughput_lots × variable_cost_per_lot
```

### 6.5 固定費
```text
fixed_cost
= fixed_cost_per_week
```

### 6.6 P/L に落とす在庫費用
```text
issue_cost
= opening_inventory_value + inbound_value - ending_inventory_value
