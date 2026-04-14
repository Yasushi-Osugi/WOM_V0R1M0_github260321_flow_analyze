これは、現在の `allocate_markets_to_moms(..)` を **Inbound 側の policy executor** と位置づけたうえで、その対称関数として **Outbound 側の handoff bridge** を定義する設計メモです。
現行の `push_pull(..)` は `out_root` に対して動く supply-layer engine であり、IN→OUT の橋はまだ持っていません。また `allocate_markets_to_moms(..)` は、lot を subtree の入口へ振り分ける実行関数としてすでに存在します。したがって、`allocate_lots_to_dads(..)` はその対称な bridge layer として置くのが自然です。 

````markdown
# allocate_lots_to_dads 設計メモ

## 1. 目的

`allocate_lots_to_dads(..)` は、**MOM subtree で確定した supply lot を、どの DAD subtree に入れるか決める handoff bridge 関数**である。

この関数は、Inbound 側の MOM node で確定した出荷 lot を読み取り、
lot が持つ demand anchor 情報に基づいて最終消費地 leaf を特定し、
その leaf を担当する DAD node を決め、
Outbound 側の DAD subtree の入口へ lot を seed する。

この関数は、`allocate_markets_to_moms(..)` の対称関数として位置づける。

- `allocate_markets_to_moms(..)`  
  demand anchored lot → MOM subtree 入口
- `allocate_lots_to_dads(..)`  
  MOM 確定 supply lot → DAD subtree 入口

---

## 2. 設計上の位置づけ

WOM の全体構成において、役割分担は以下とする。

1. Outbound 側で demand anchored lot を形成する
2. `allocate_markets_to_moms(..)` で MOM subtree に demand を配賦する
3. Inbound 側は MOM subtree 単位で planning する
4. `allocate_lots_to_dads(..)` で MOM supply lot を DAD subtree に handoff する
5. Outbound 側は DAD subtree 単位で planning する
6. 必要に応じて上位ノード KPI を後段集約する

ここで `allocate_lots_to_dads(..)` は、**Inbound planning と Outbound planning を接続する唯一の明示的 bridge layer** とする。

---

## 3. この関数の責務

この関数の責務は、以下の 5 点に限定する。

1. source lots を MOM supply layer から読む
2. lot_id から demand anchor / 最終 leaf を特定する
3. leaf から対応する DAD node を特定する
4. 対応 DAD の outbound supply layer 入口に lot を seed する
5. handoff 結果を debug / audit 可能な形で記録する

### 責務に含めないもの

この関数は以下を担当しない。

- DAD subtree 内の forward / push / pull planning
- DAD / WS / RT / leaf の在庫計算
- transport capacity 制約
- service level 最適化
- DAD capacity 制約
- KPI 集約
- MOM 側 capacity 制約
- 需要予測
- DAD subtree の decouple node 決定

---

## 4. 入力

### 関数引数（想定）

- `out_root`
  - outbound tree の root node
- `in_root`
  - inbound tree の root node
- `source_moms: list[str] | None = None`
  - handoff 対象とする MOM node 名の限定。省略時は全 MOM
- `source_slot: int = 0`
  - MOM 側の source slot。基本は `psi4supply[w][0:S]`
- `seed_slot: int = 3`
  - DAD 側の seed 先 slot。基本は `psi4supply[w][3:P]`
- `weeks: int | None = None`
  - 対象週数の上限
- `clear_existing_dad_seed: bool = True`
  - DAD 側 seed slot を再作成前にクリアするか
- `debug: bool = True`
  - debug log を出力するか

### 実質入力データ

- `MOM.psi4supply[w][0]` に存在する確定 supply lots
- lot_id naming rule または lot metadata
- leaf → DAD の routing 定義
- outbound tree 内の `DAD_` prefix node 一覧

---

## 5. 出力

### 返り値（推奨）

```python
return out_root, in_root, handoff_result
````

### `handoff_result` の想定内容

* `lot_to_leaf`
* `lot_to_dad`
* `dad_to_lots`
* `week_dad_counts`
* `unresolved_lots`
* `unresolved_leafs`

### 実質出力

* `out_root` 配下の各 DAD node の `psi4supply[w][3]` が更新される
* debug 時に DAD ごとの handoff summary が出る

この関数の本質は、返り値よりも
**「MOM supply lot を、DAD subtree の入口へ移す」**
破壊的更新である。

---

## 6. 基本アイデア

### 6.1 source

source は MOM 側の確定 supply lot とする。

基本は:

* `mom.psi4supply[w][0]`

理由:

* MOM で出荷ポジションが確定した lot を使いたい
* demand layer ではなく、planning 結果としての supply layer を接続したい

### 6.2 destination

destination は DAD 側の supply layer 入口とする。

基本は:

* `dad.psi4supply[w][3]`

理由:

* DAD にとっては「上流から受け取った lot」を P / receipt / input とみなせる
* その後の subtree planning に既存 supply engine を使いやすい

### 6.3 routing key

lot_id から最終 leaf を特定し、その leaf の親系統から DAD を逆引きする。

基本思想:

* lot の demand anchor を信頼する
* bridge 層は routing を再発明しない
* leaf → DAD の tree 構造に従う

---

## 7. 想定アルゴリズム

1. Inbound tree から対象 MOM node を集める
2. Outbound tree から DAD node を集める
3. 必要なら DAD seed slot をクリアする
4. 各 week について、各 MOM の source lot を走査する
5. 各 lot について:

   * lot_id から leaf を特定
   * leaf から担当 DAD を特定
   * `DAD.psi4supply[w][3]` に append
6. debug / audit 用の assignment map を蓄積する
7. summary を返す

---

## 8. 参照すべき既存関数との関係

### 8.1 `allocate_markets_to_moms(..)` との対称性

`allocate_markets_to_moms(..)` は、

* source lots を読む
* lot_id から市場キーを取る
* policy で MOM を決める
* MOM demand slot に書く

関数である。

`allocate_lots_to_dads(..)` も同様に、

* source lots を読む
* lot_id から leaf / market を取る
* tree / policy で DAD を決める
* DAD supply slot に書く

という対称構造にする。

### 8.2 `push_pull(..)` との関係

現行 `push_pull(..)` は `out_root` に対して supply planning を行うが、
IN→OUT の handoff は持っていない。

したがって、`allocate_lots_to_dads(..)` は
`push_pull(..)` を呼ぶ前段の bridge layer として置く。

### 8.3 DAD subtree planning との関係

bridge 後の outbound planning は、理想的には `out_root` 全体ではなく、
各 DAD subtree 単位で実行する。

理由:

* root 起点で全 branch へ broadcast する事故を避ける
* inbound 側の `MOM subtree planning` と対称に設計する
* 責務分離が明確になる

---

## 9. 重要な前提条件

### 前提 1: lot_id から leaf が特定できる

現在は naming rule に基づく実装が想定される。
将来的には explicit metadata 化が望ましい。

### 前提 2: leaf → DAD の routing が tree から一意に引ける

outbound tree 上で leaf の祖先をたどることで DAD を特定できる必要がある。

### 前提 3: MOM 側 source lot は確定済みである

handoff 前に MOM subtree planning が完了していることを前提にする。

### 前提 4: 1 lot は 1 DAD にしか handoff しない

split shipment はこの関数では扱わない。
必要なら将来拡張とする。

---

## 10. 推奨する slot 意味づけ

### MOM 側

* source: `psi4supply[w][0:S]`

### DAD 側

* seed: `psi4supply[w][3:P]`

### 理由

* MOM では「出荷確定 lot」
* DAD では「受け取り lot / 上流からの入力」

という意味づけができる。

bridge 関数は slot semantic を壊さない範囲で最小にする。

---

## 11. 現在の強み

### 11.1 既存 engine を活かせる

bridge 後は既存の outbound subtree planning を利用できる。
新しい end-to-end 専用 engine を作らなくてよい。

### 11.2 責務分離が明確

* MOM までは製造責務
* DAD 以下は流通責務
* bridge は handoff 専任

### 11.3 debug しやすい

handoff map を持てば、
「どの lot がどの DAD に渡ったか」を検証しやすい。

---

## 12. 現在の注意点

### 12.1 lot_id naming rule 依存

現在の設計は demand anchor 情報を lot_id に依存しやすい。
将来的には lot metadata 分離が望ましい。

### 12.2 DAD seed slot の再初期化

`clear_existing_dad_seed` の扱いを誤ると stale lot が残る可能性がある。

### 12.3 root/supply_point 集約は別問題

bridge 後に DAD subtree planning を行うと、
root や supply_point の PSI 集約は自動では整わない可能性がある。
必要なら後段で再集約する。

### 12.4 DAD subtree planning 範囲

`out_root` 全体に `push_pull(..)` をかけると、再び全 branch 展開の事故が起こる可能性がある。
将来的には DAD subtree 単位での実行が望ましい。

---

## 13. 将来拡張点

### 13.1 `lot_to_dad` map を返す

handoff audit のために必須級。

### 13.2 leaf -> DAD 解決を metadata 化する

routing key を naming rule 依存から分離する。

### 13.3 split shipment 対応

1 lot -> 1 DAD ではなく、部分配分に拡張する。

### 13.4 DAD capacity-aware handoff

現時点では handoff は routing のみ。
将来的には transport / DAD capacity を見た secondary routing もありうる。

### 13.5 handoff event 化

`MOM -> DAD` を canonical event として記録すると、
WOM event analyzer と整合しやすい。

---

## 14. 推奨する実装順序

### Phase 1

`allocate_lots_to_dads(..)` を lot copy bridge として最小実装する

### Phase 2

handoff 結果を debug / audit map として返す

### Phase 3

DAD subtree planning を `out_root` 全体ではなく DAD 単位に寄せる

### Phase 4

必要に応じて root / supply_point KPI を後段集約する

---

## 15. 一言でまとめると

`allocate_lots_to_dads(..)` は、

**「MOM subtree で確定した supply lot を、どの DAD subtree に handoff するか決める bridge 関数」**

である。

この関数を `allocate_markets_to_moms(..)` の対称関数として定義することで、

* Inbound 側は MOM subtree planning
* Outbound 側は DAD subtree planning
* IN/OUT 間は handoff bridge

という、見通しの良い責務分離が成立する。

```

---

補足だけ一言です。  
この設計になると、WOM の中で **MOM と DAD が「経済流の受け渡し面」**になります。  
かなり美しい構造です。製造と流通の握手が、ようやく図面に描ける感じです。

次に自然なのは、  
**`allocate_lots_to_dads(..)` の最小 skeleton** を Python で起こすことです。
```
