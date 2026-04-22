# WOM Event Money Mapping v0.1

## 1. 目的

本書は、WOM の event flow tracing で生成される event を、金額編へ接続するための金額マッピングルールを定義する。

WOM では、数量編の lot event をベースに、各 event に単価を対応づけることで、以下の金額項目を積み上げる。

- revenue
- purchase amount
- inventory value
- variable cost
- fixed cost
- tax
- profit

本ルールにより、event flow tracing から

- 売上・利益・利益率の週次計算
- 1 week = 1 sec animation
- node × product × week 単位の金額評価

を一貫したロジックで実現する。

---

## 2. 基本思想

### 2.1 基本原則
**数量 event × 単価 = 金額**

- lot 数量は event flow tracing から取得する
- 単価は単価補完フェーズの結果から取得する

### 2.2 在庫は残高
- `inventory_value` は B/S 残高である
- event 単発で費用化するのではなく、
  - `week_open`
  - `week_close`
  - `lot_release_from_inventory`
  などを通じて P/L に接続する

### 2.3 固定費は週末計上
固定費は lot event ごとではなく、原則として週末 event で 1 回計上する。

### 2.4 internal / external の分離
event には internal / external の区別を持たせる。

- internal trade
- external sale
- external purchase

これにより、local profit と consolidated profit の両方を計算できる。

---

## 3. 前提 master

本ルールは、以下の金額編 master が存在する前提で定義する。

- `node_master.csv`
- `node_character_policy_master.csv`
- `node_product_money_master.csv`
- `edge_product_money_master.csv`
- `valuation_policy_master.csv`

単価補完フェーズの出力として、少なくとも以下の unit amount が利用可能であることを前提とする。

- `purchase_cost_per_lot`
- `ship_price_per_lot`
- `inventory_unit_value_per_lot`
- `variable_cost_per_lot`
- `fixed_cost_per_week`
- `tax_rate`

---

## 4. event type ごとの金額マッピング表

| event_type | 典型発生場所 | 数量 basis | 主な金額項目 | 単価ソース | P/L / B/S | 説明 |
|---|---|---:|---|---|---|---|
| `lot_purchase` | 最上流調達 / 外部仕入 | purchased_lots | purchase_amount | `purchase_cost_per_lot` | P/L候補 / B/S流入 | 外部仕入。購入金額の起点 |
| `lot_receive` | child node 受入 | inbound_lots | purchase_amount, inventory_in_value | `purchase_cost_per_lot`, `inventory_unit_value_per_lot` | B/S流入 | 親からの受入。internal purchase を含む |
| `lot_ship_internal` | parent node 出荷 | shipped_lots | ship_amount | `ship_price_per_lot` | local P/L | internal 売上。連結では消去候補 |
| `lot_ship_external` | RT / CS 直前 | shipped_lots | revenue | `ship_price_per_lot` | P/L | external 売上 |
| `lot_sell` | RT / CS | sold_lots | revenue | `ship_price_per_lot` | P/L | 売上認識 event。`lot_ship_external` と同義でも可 |
| `lot_move_to_inventory` | 受入直後 / 保管入り | moved_lots | inventory_value_add | `inventory_unit_value_per_lot` | B/S | 在庫残高増加 |
| `lot_release_from_inventory` | 払出 / 出荷引当 | released_lots | inventory_value_release, issue_cost | `inventory_unit_value_per_lot` | B/S減 / P/L | 在庫から払出。費用化の起点 |
| `lot_process` | MOM / PAD / 加工 | processed_lots | variable_cost_add | `variable_cost_per_lot` | P/L または B/S資産化 | 加工・組立の変動費。資産化可否は policy 次第 |
| `lot_transfer` | node 間移送 | transferred_lots | ship_amount, purchase_amount | parent `ship_price_per_lot`, child `purchase_cost_per_lot` | local P/L / B/S | internal transfer の中核 |
| `lot_hold_inventory` | 倉庫 / 滞留 | ending_inventory_lots | carrying_cost(optional) | `inventory_carrying_rate` | P/L | 必須ではない。期間保有コストを積む場合 |
| `lot_writeoff` | 廃棄 / 陳腐化 | writeoff_lots | writeoff_loss | `inventory_unit_value_per_lot` | P/L | 在庫評価減・廃棄損 |
| `lot_return_in` | 返品受入 | returned_lots | inventory_recovery / revenue_reversal | return policy | P/L / B/S | 返品受入 |
| `lot_return_out` | 返品出荷 | returned_lots | revenue_reversal / purchase_reversal | return policy | P/L | 売上取消や逆仕入 |
| `week_open` | 週初 | opening_inventory_lots | opening_inventory_value | `inventory_unit_value_per_lot` | B/S | 期首残高確定 |
| `week_close` | 週末 | ending_inventory_lots | ending_inventory_value, inventory_delta, issue_cost | `inventory_unit_value_per_lot` | B/S / P/L | 週末評価。固定費・税計算の基点 |
| `fixed_cost_accrual_weekly` | 各 node 週末 | 1 | fixed_cost | `fixed_cost_per_week` | P/L | 週次固定費計上 |
| `tax_accrual_weekly` | 各 node 週末 | 1 | tax | `tax_rate` | P/L | 税前利益に対する税額計算 |
| `profit_close_weekly` | 各 node 週末 | 1 | profit_before_tax / after_tax | 集計計算 | P/L | 週次利益確定 |

---

## 5. 最小実装でまず使う event

初期実装では、次の 8 event を優先対象とする。

1. `lot_receive`
2. `lot_ship_internal`
3. `lot_ship_external`
4. `lot_move_to_inventory`
5. `lot_release_from_inventory`
6. `lot_process`
7. `fixed_cost_accrual_weekly`
8. `week_close`

これにより、以下の主要項目が閉じる。

- purchase
- revenue
- inventory
- variable_cost
- fixed_cost
- profit

---

## 6. event ごとの基本計算式

### 6.1 `lot_receive`
```text
purchase_amount = inbound_lots × purchase_cost_per_lot
inventory_in_value = inbound_lots × inventory_unit_value_per_lot
6.2 lot_ship_internal
ship_amount = shipped_lots × ship_price_per_lot
6.3 lot_ship_external
revenue = shipped_lots × ship_price_per_lot
6.4 lot_move_to_inventory
inventory_value_add = moved_lots × inventory_unit_value_per_lot
6.5 lot_release_from_inventory
inventory_value_release = released_lots × inventory_unit_value_per_lot
issue_cost = inventory_value_release
6.6 lot_process
variable_cost_add = processed_lots × variable_cost_per_lot
6.7 fixed_cost_accrual_weekly
fixed_cost = fixed_cost_per_week
6.8 week_close
ending_inventory_value = ending_inventory_lots × inventory_unit_value_per_lot
inventory_delta = ending_inventory_value - opening_inventory_value
profit_before_tax = revenue - issue_cost - variable_cost - fixed_cost
tax = profit_before_tax × tax_rate
profit_after_tax = profit_before_tax - tax
7. event flow tracing と接続する時の実務ルール
7.1 ship / receive は対にする
parent の lot_ship_internal
child の lot_receive

を、同じ transfer event group として扱うことを推奨する。

7.2 inventory は snapshot event を持つ

在庫は flow event だけでは見えにくいため、以下を持つことを推奨する。

week_open
week_close

これにより、週次 animation と B/S 評価が安定する。

7.3 固定費は週末に閉じる

固定費を lot event に按分して都度積むのではなく、原則として週末 event で 1 回計上する。

7.4 internal / external flag を持つ

event には、少なくとも次の区別を持たせることを推奨する。

is_internal_trade
is_external_sale
is_external_purchase

これにより、連結消去が容易になる。

8. 1 week = 1 sec animation への適用

週次アニメーションでは、各秒ごとにその週の event を順に再生し、金額を加算する。

推奨フロー
その週の event を時系列に並べる
event ごとに数量 × 単価で金額を加算する
week_close で在庫残高・固定費・税を閉じる
その週の以下を表示する
revenue
variable_cost
fixed_cost
ending_inventory_value
profit
profit_ratio
animation 上の意味

これにより、event flow tracing は単なる「動きの可視化」ではなく、動きに金額が貼り付いた経営アニメーションへ拡張される。

9. B/S / P/L 上の整理
9.1 B/S 残高
opening_inventory_value
ending_inventory_value
9.2 P/L 項目
revenue
purchase_amount または issue_cost
variable_cost
fixed_cost
tax
profit
9.3 注意点

inventory_value そのものは費用ではない。
P/L に落とす場合は、以下のどちらかで扱う。

inventory_delta
issue_cost

推奨は issue_cost である。

10. local / consolidated の区別
10.1 local node profit

各 node の内部売上・内部購入を含む採算。
拠点管理会計の確認に用いる。

10.2 consolidated E2E profit

サプライチェーン全体を連結した利益。
internal revenue / internal purchase を消去して算定する。

11. 一言サマリ

WOM の event money mapping の基本は次の通りである。

flow event で売上・購入・変動費を積む
inventory event で在庫残高を更新する
week_close event で固定費・税・利益を閉じる

つまり、

event quantity × unit price = amount

を基本としつつ、

在庫は残高
固定費と税は週末 event で閉じる

という構成で、WOM の event-driven cost animation を実現する。