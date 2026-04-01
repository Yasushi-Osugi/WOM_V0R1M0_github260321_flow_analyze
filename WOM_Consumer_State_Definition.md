# WOM Consumer State の意味づけ表 v0.1

WOM における consumer state は、消費者の心の中に蓄積される  
**体験・信頼・再購買意向・生活価値** を表す状態変数群である。  
これにより、消費体験を将来需要と経営評価へ接続する。

---

## Consumer State 一覧

| State名 | 推奨レンジ | 高い値の意味 | 低い値の意味 | 主に何で動くか | 経営的な読み方 |
|---|---:|---|---|---|---|
| `satisfaction_stock` | -100 〜 100 | 満足体験が蓄積している | 不満体験が蓄積している | 品質、欠品、価格、苦情 | 顧客体験の温度感 |
| `brand_loyalty` | 0 〜 100 | ブランド支持・信頼が強い | ブランド支持が弱い | 継続満足、品質不満、欠品 | ブランド資産の強さ |
| `repeat_intent` | 0 〜 100 | 次回も買いたい気持ちが強い | 次回購買意向が弱い | 直近体験、価格感、欠品 | 近未来需要の強さ |
| `switch_cost_perception` | 0 〜 100 | 他ブランドへ替えにくい | 替えやすい | 習慣、ブランド信頼、欠品 | 顧客維持力 |
| `price_sensitivity` | 0 〜 100 | 価格変化に敏感 | 価格に鈍感 | 価格抵抗、不満、代替比較 | 値上げ耐性の弱さ |
| `habit_strength` | 0 〜 100 | 習慣購買が定着している | 習慣化していない | 継続利用、反復消費 | 安定需要の土台 |
| `well_being_degree` | 0 〜 100 | 生活充実への寄与が大きい | 生活価値への寄与が小さい | 総合体験、使いやすさ、満足 | 目的関数そのもの |

---

## 各 State の意味

### `satisfaction_stock`
消費者の中に蓄積された、満足と不満の在庫。  
短中期の感情バッファとして機能する。

- 高い: 良い体験が続いている
- 低い: 不満が蓄積している

---

### `brand_loyalty`
ブランドに対する支持・信頼・好意の蓄積。  
WOM における **ブランド資産の状態変数**。

- 高い: 他社より優先して選ばれやすい
- 低い: 代替品へ流れやすい

---

### `repeat_intent`
次回も買うつもりかどうかを表す再購買意向。  
WOM において **将来需要へ最も直接つながる state**。

- 高い: 次の需要が発生しやすい
- 低い: 次回購買が不透明

---

### `switch_cost_perception`
他ブランドへ切り替えるときの心理的・実務的コスト感。

- 高い: 替えにくい
- 低い: 替えやすい

これは **顧客維持力** に近い意味を持つ。

---

### `price_sensitivity`
価格差・値上げ・割高感にどれだけ敏感かを表す。

- 高い: 少し高いだけで不満になりやすい
- 低い: 価格より品質やブランドを重視しやすい

これは **値上げ耐性の逆指標** として読める。

---

### `habit_strength`
その商品を生活の中で習慣的に使っている強さ。

- 高い: 自然に継続購買する
- 低い: 習慣化していない

これは **安定需要の基盤** を表す。

---

### `well_being_degree`
その商品・ブランドが、消費者の生活充実にどれだけ寄与しているかを表す総合指標。  
WOM における consumer side の最上位目的関数に最も近い state。

- 高い: 生活価値への寄与が大きい
- 低い: 不満や失望が生活価値を下げている

---

## Consumer State の役割分担

### 近い将来の需要に効くもの
- `repeat_intent`
- `price_sensitivity`
- `switch_cost_perception`

### ブランド資産として効くもの
- `brand_loyalty`
- `habit_strength`

### 体験の蓄積を表すもの
- `satisfaction_stock`

### 最上位の生活価値を表すもの
- `well_being_degree`

---

## 経営者向けの一言説明

| State名 | 一言説明 |
|---|---|
| `brand_loyalty` | このブランドが選ばれ続ける力 |
| `repeat_intent` | 次回需要の強さ |
| `price_sensitivity` | 値上げに対する脆さ |
| `habit_strength` | 習慣需要の強さ |
| `well_being_degree` | この商品が生活をどれだけ良くしているか |

---

## 読み方の例

### 例1: 理想状態
- `brand_loyalty` 高い
- `repeat_intent` 高い
- `well_being_degree` 高い

→ ブランド支持も強く、未来需要も強く、生活価値にも寄与している。

### 例2: ブランドは強いが価格が重い
- `brand_loyalty` 高い
- `repeat_intent` 低い
- `price_sensitivity` 高い

→ ブランドは好きだが、高くて買い続けにくい。

### 例3: 離反リスクが高い
- `brand_loyalty` 低い
- `repeat_intent` 低い
- `switch_cost_perception` 低い

→ 他ブランドへ流れやすい。

### 例4: Moment of Truth で失敗
- `satisfaction_stock` 低い
- `well_being_degree` 低い
- complaint 系 event が多い

→ 消費体験が生活価値を傷つけている。

---

## WOMらしい整理

WOM の言葉で整理すると、consumer state は次のように読める。

- `satisfaction_stock`  
  = 体験の蓄積
- `brand_loyalty`  
  = 信頼の蓄積
- `repeat_intent`  
  = 次回需要の予兆
- `well_being_degree`  
  = 生活価値への寄与
- `price_sensitivity` / `switch_cost_perception`  
  = 離反リスクの媒介変数
- `habit_strength`  
  = 継続需要の慣性

---

## まとめ

consumer state とは、消費者の心の中に蓄積される  
**体験・信頼・再購買意向・生活価値** の状態変数群である。

WOM では、これらを通じて

- 消費体験
- ブランド力
- 将来需要
- 経営評価

をひとつのモデルの中で接続する。