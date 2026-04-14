このメモは、現在の WOM の流れ、つまり

* `allocate_markets_to_moms(..)` で MOM subtree の入口を作る
* `inbound_MOM_leveling_vs_capacity(..)` が capacity を見る既存関数として存在する
* `MOM subtree` planning と `MOM -> DAD` handoff が動き始めている

という現状を前提にしています。

````markdown
# level_mom_demand_with_capacity 設計メモ

## 1. 目的

`level_mom_demand_with_capacity(..)` は、  
**`allocate_markets_to_moms(..)` で決まった demand anchored lot の MOM 配分結果に対して、MOM ごとの週次生産能力制約を適用し、実行可能な demand / production 計画へ整形する関数**である。

この関数の役割は、単なる capacity clipping ではない。  
本質は、

- どの MOM が担当するかは policy で決める
- その担当 MOM が本当に処理可能かを capacity で判定する
- overflow を前倒し、secondary MOM、backlog などへ振り分ける

ことである。

この関数は、`allocate_markets_to_moms(..)` と `inbound_backward_MOM_to_leaf(..)` の間に置くのが基本である。

---

## 2. WOM 全体における位置づけ

推奨する flow は以下。

1. Outbound 側で demand anchored lot を形成する
2. `allocate_markets_to_moms(..)` で lot を MOM subtree 入口に配賦する
3. `level_mom_demand_with_capacity(..)` で capacity feasibility を適用する
4. Inbound 側は MOM subtree 単位で planning を行う
5. `allocate_lots_to_dads(..)` で MOM supply lot を DAD subtree に handoff する
6. Outbound 側は DAD subtree 単位で planning を行う
7. 必要なら KPI / root / supply_point 集約は後段で計算する

この中で `level_mom_demand_with_capacity(..)` は、  
**policy allocation と subtree planning の間にある feasibility / adjustment layer** である。

---

## 3. この関数の責務

この関数の責務は、以下に限定する。

1. MOM ごとの週別 demand lot 数を集計する
2. MOM ごとの週次 capacity と比較する
3. 超過分を処理ルールに従って調整する
4. 調整済みの `MOM.psi4demand` を更新する
5. audit / explanation 用の調整結果を返す

### 責務に含めないもの

この関数は以下を担当しない。

- market -> MOM policy 決定そのもの
- DAD への handoff
- outbound routing
- KPI 集約
- 需要予測
- MOM subtree 以下の詳細な backward / forward propagation
- root / supply_point の再集約

---

## 4. 基本思想

### 4.1 policy と capacity は分ける
`allocate_markets_to_moms(..)` は  
**「誰が担当するか」**  
を決める。

`level_mom_demand_with_capacity(..)` は  
**「担当できる量に収まるか」**  
を決める。

この分離が重要である。

### 4.2 feasibility は planning の前に作る
capacity 制約は planning の後から無理やり削るのではなく、  
**subtree planning に入る前に feasible な MOM demand 状態を作る**  
方が自然である。

### 4.3 subtree planning と整合する単位で調整する
Inbound 側は現在 `MOM subtree` 単位で planning する方針である。  
したがって capacity 調整も、MOM node を中心に考えるのが自然である。

---

## 5. 入力

### 想定関数シグネチャ

```python
def level_mom_demand_with_capacity(
    out_root,
    in_root,
    *,
    product: str | None = None,
    weeks: int | None = None,
    mode: str = "forward_pullback",
    overflow_policy: str = "secondary_then_backlog",
    allow_early_build: bool = True,
    allow_secondary_mom: bool = True,
    secondary_policy: dict | None = None,
    backlog_node_name: str | None = None,
    debug: bool = True,
):
    ...
````

### 実質入力データ

* `MOM.psi4demand[w][0]` に置かれた demand anchored lots
* `weekly_capability[product][mom_name][w]`
* MOM node 一覧
* primary allocation 済みの policy 結果
* 必要なら secondary MOM policy

### 既存資産との関係

現行 `engines.py` には `inbound_MOM_leveling_vs_capacity(..)` があり、
MOM の `psi4demand[w][3]` に対して capacity clipping / leveling をしている。
`level_mom_demand_with_capacity(..)` は、その前段または上位版として位置づける。

---

## 6. 出力

### 返り値（推奨）

```python
return out_root, in_root, capacity_result
```

### `capacity_result` の想定内容

* `week_mom_assigned`
* `week_mom_capacity`
* `week_mom_overflow`
* `lot_to_primary_mom`
* `lot_to_final_mom`
* `lot_moves_early`
* `lot_moves_secondary`
* `lot_backlogged`
* `unresolved_lots`

### 実質出力

* `MOM.psi4demand[w][0]` またはその関連 slot の内容が調整される
* 後続 planning に投入可能な feasible 状態になる

---

## 7. capacity の定義

### 基本定義

最小形はこれで十分。

```python
weekly_capability[product][mom_name][w] -> int
```

意味:

* その週にその MOM が処理可能な lot 数上限

### 将来的に持ちたい内訳

* nominal capacity
* effective capacity
* overtime capacity
* maintenance loss
* yield loss
* long vacation adjustment
* line / product family 別 capacity

### 初期実装の原則

最初は
**effective weekly lot capacity**
だけを扱えばよい。

---

## 8. 処理ロジックの基本案

### 8.1 Phase 1: 集計

各 MOM / week について、

* demand lots 数
* capacity
* overflow

を計算する。

### 8.2 Phase 2: overflow 処理

overflow がある場合、優先順位に従って調整する。

推奨順序:

1. 同一 MOM 内で前倒し
2. secondary MOM へ振替
3. backlog / unresolved として残す

### 8.3 Phase 3: 調整結果を PSI に反映

調整後の lot 配置を `MOM.psi4demand` に書き戻す。

### 8.4 Phase 4: audit map を返す

後で説明・可視化・比較ができるように、
lot 単位の移動結果を保持する。

---

## 9. 推奨する overflow policy

### Policy A: forward_pullback

* まず primary MOM に置く
* 超過したら前週へ引き戻す
* それでも無理なら secondary MOM へ逃がす
* 最後に backlog

### Policy B: secondary_then_backlog

* primary MOM で無理なら secondary MOM
* それでも無理なら backlog

### Policy C: strict_primary_only

* primary MOM のみ許可
* overflow は backlog

### 推奨

初期版は **`secondary_then_backlog`** が扱いやすい。

理由:

* 実務上分かりやすい
* debug しやすい
* 計算量が軽い
* 後から前倒しロジックを足しやすい

---

## 10. secondary MOM の考え方

secondary MOM は policy の拡張として扱う。

例:

```python
secondary_policy = {
    "CN": ["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
    "DE": ["MOM_final_assy_EURO", "MOM_final_assy_ASIA"],
}
```

意味:

* 先頭が primary
* capacity 超過時のみ次点を使う

この考え方にすると、`allocate_markets_to_moms(..)` の思想をそのまま拡張できる。

---

## 11. slot の扱い

### 現在の基本

`allocate_markets_to_moms(..)` は `MOM.psi4demand[w][0]` に lot を置く。

### capacity 関数での扱い

初期版では、**slot0 の lot 配置を調整対象とする**のが安全。

理由:

* まだ subtree planning 前
* 需要起点 lot をそのまま持っている
* 調整ロジックが単純になる

### 将来的な拡張

後で必要なら、

* slot0 = demand-facing lot
* slot3 = production-facing lot

の変換タイミングも厳密化する。

---

## 12. 監査・説明可能性

この関数は、WOM における意思決定モジュールの一部になるため、
**説明可能性が極めて重要**である。

最低限、以下を残すべき。

* この lot は primary MOM に入ったか
* capacity 超過で secondary MOM に移ったか
* 何週前倒しされたか
* backlog になったか
* その理由は何か

これは GUI 表示や経営説明に直結する。

---

## 13. 現在の強み

### 13.1 WOM の現構造と整合する

MOM subtree planning の前に入れやすい。

### 13.2 `allocate_markets_to_moms(..)` と責務分離がきれい

policy と feasibility が分かれる。

### 13.3 将来の数理最適化に発展しやすい

現在は heuristic でも、後で optimization core に置き換えやすい。

---

## 14. 現在の注意点

### 14.1 early build の意味づけ

前倒しは inventory 増加やキャッシュ拘束を生む。
単純に前倒しすればよいわけではない。

### 14.2 secondary MOM への振替コスト

secondary MOM は lead time / cost / policy 違反 penalty を持つ可能性がある。

### 14.3 backlog の扱い

backlog をどの node / slot / audit 構造で持つかを明示する必要がある。

### 14.4 root / supply_point 集約との分離

この関数は feasibility 作成に集中し、上位集約表示は後段へ分ける。

---

## 15. 実装段階案

### Phase 1: heuristic 最小版

* week / MOM ごとに lot 数を数える
* 超過分を secondary MOM に振る
* 残りは backlog

### Phase 2: early build 対応

* 同一 MOM 内の前倒しを許可する

### Phase 3: penalty-aware heuristic

* late / early / secondary use に penalty を持たせる

### Phase 4: optimization 版

* min-cost flow / MILP に置き換える

---

## 16. WOM 上位モデルとの整合

WOM の上位意思決定モジュールとしては、以下の構成が望ましい。

1. Forecast / sensing
2. `allocate_markets_to_moms(..)`

   * policy allocation
3. `level_mom_demand_with_capacity(..)`

   * capacity feasibility / leveling
4. Inbound subtree planning
5. `allocate_lots_to_dads(..)`

   * handoff bridge
6. Outbound subtree planning
7. KPI aggregation / cockpit explanation

この構成だと、WOM は

* 誰が担当するか
* 担当できるか
* どう流れるか
* 結果どうなったか

を分離して扱える。

---

## 17. 一言でまとめると

`level_mom_demand_with_capacity(..)` は、

**「policy で決まった MOM 配分結果を、週次 capacity 制約の下で実行可能な demand / production 計画へ整形する feasibility / leveling 関数」**

である。

`allocate_markets_to_moms(..)` が policy layer、
`level_mom_demand_with_capacity(..)` が feasibility layer、
その後の subtree planning が execution layer、
という役割分担が、WOM に最も整合的で見通しが良い。

```

かなり大事なメモです。  
ここが整理できると、WOM は「配分した後に祈る」世界から、「配分した後に実際に回せるか確認する」世界に進みます。だいぶ現実寄りです。

次に一番自然なのは、  
**`level_mom_demand_with_capacity(..)` の最小 skeleton** を Python で起こすことです。
```
