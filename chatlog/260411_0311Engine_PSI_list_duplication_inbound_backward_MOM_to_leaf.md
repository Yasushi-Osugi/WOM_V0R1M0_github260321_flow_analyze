はい。
このログを見る限り、**`inbound_backward_MOM_to_leaf(...)` の中で、同じ 92,422 unique lots が ASIA / EURO の両 MOM に入り、しかも各 MOM 内で 2回化している**ので、debug はこの関数の中で

* **market / leaf → chosen MOM**
* **MOM の `psi4demand` へ書く前後**

を押さえるのが最短です。`step3` の直後ですでに `demand S/P = 184844 total / 92422 unique` が両 MOM で成立しているため、主犯は step3 内部と見てよいです。 

以下、そのまま差し込める最小 debug code を出します。

---

## 1. engine file の上の方に追加する helper

`inbound_backward_MOM_to_leaf(...)` がある engine module に、まずこれを追加してください。

```python id="1rfal6"
def _dbg_ids_head(ids, n=5):
    try:
        return [str(x) for x in (ids or [])[:n]]
    except Exception:
        return []


def _dbg_total_and_unique_slot(psi, slot_idx=0):
    total = 0
    uniq = set()

    for week in (psi or []):
        try:
            lots = week[slot_idx] or []
        except Exception:
            lots = []

        total += len(lots)
        for lot in lots:
            uniq.add(str(lot))

    return total, len(uniq)


def _dbg_nonzero_weeks_slot(psi, slot_idx=0, limit=8):
    hits = []
    for w, week in enumerate(psi or [], start=1):
        try:
            cnt = len(week[slot_idx] or [])
        except Exception:
            cnt = 0
        if cnt:
            hits.append((w, cnt))
            if len(hits) >= limit:
                break
    return hits


def _dbg_dump_moms_in_engine(in_root, label="", focus_names=None):
    names_filter = set(focus_names or [])

    stack = [in_root]
    moms = []
    seen = set()

    while stack:
        n = stack.pop()
        if n is None:
            continue
        if id(n) in seen:
            continue
        seen.add(id(n))

        nm = str(getattr(n, "name", "") or "")
        if nm.startswith("MOM"):
            if not names_filter or nm in names_filter:
                moms.append(n)

        for c in getattr(n, "children", []) or []:
            stack.append(c)

    moms = sorted(moms, key=lambda x: str(getattr(x, "name", "")))

    print("=" * 110)
    print(f"[mom-engine-debug] {label}")

    for mom in moms:
        nm = str(getattr(mom, "name", "") or "")

        psi_d = getattr(mom, "psi4demand", None) or []
        dS_total, dS_unique = _dbg_total_and_unique_slot(psi_d, 0)
        dI_total, dI_unique = _dbg_total_and_unique_slot(psi_d, 2)
        dP_total, dP_unique = _dbg_total_and_unique_slot(psi_d, 3)

        print(
            f"[mom-engine-debug] {nm} | "
            f"demand S total={dS_total} unique={dS_unique}, "
            f"I total={dI_total} unique={dI_unique}, "
            f"P total={dP_total} unique={dP_unique}"
        )
        print(
            f"[mom-engine-debug] {nm} | "
            f"demand_nz_S={_dbg_nonzero_weeks_slot(psi_d, 0)} | "
            f"demand_nz_P={_dbg_nonzero_weeks_slot(psi_d, 3)}"
        )

    print("=" * 110)
```

---

## 2. `inbound_backward_MOM_to_leaf(...)` の入口と出口

関数の最初と最後に、これを入れてください。

```python id="68kqpc"
print("[mom-engine-debug] enter inbound_backward_MOM_to_leaf")
_dbg_dump_moms_in_engine(
    in_root,
    label="before inbound_backward_MOM_to_leaf",
    focus_names=["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
)
```

関数の最後、`return out_root, in_root` の直前にこれです。

```python id="473jul"
_dbg_dump_moms_in_engine(
    in_root,
    label="after inbound_backward_MOM_to_leaf",
    focus_names=["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
)
print("[mom-engine-debug] leave inbound_backward_MOM_to_leaf")
```

これで、**関数に入る前から既に重複しているのか、それとも関数内で増えたのか**がまず分かります。

---

## 3. market → MOM 割当の直後に入れる debug

`mom_policy` を使って、market / leaf / demand lot をどの MOM に振るか決めている箇所の**直後**に入れてください。
変数名は repo に合わせて置換してください。

### 想定

* `leaf_node` または `market_node`
* `chosen_mom_name` または `mom_name`
* `lot_ids`
* `week_no` または `w`

```python id="1f5hvr"
print(
    "[mom-assign]",
    "week=", week_no if 'week_no' in locals() else w,
    "leaf=", getattr(leaf_node, "name", None) if 'leaf_node' in locals() else None,
    "market=", getattr(market_node, "name", None) if 'market_node' in locals() else None,
    "chosen_mom=", chosen_mom_name if 'chosen_mom_name' in locals() else mom_name,
    "lot_count=", len(lot_ids or []),
    "lot_head=", _dbg_ids_head(lot_ids, 5),
)
```

ここで見たいのは、

* 同じ leaf / same week が **ASIA と EURO の両方に割られていないか**
* `lot_head` が同一のまま、2つの MOM に出ていないか

です。

---

## 4. MOM demand append の前後に入れる debug

これが本丸です。
`mom.psi4demand[w][0]` や `mom.psi4demand[w][3]` に対して `extend()` / `append()` している場所の**直前と直後**に入れてください。

### S slot に書く前後

```python id="ic15ff"
before_s = list((mom_node.psi4demand[w][0] or []))
incoming_s = list(lot_ids or [])

print(
    "[mom-write-before:S]",
    "mom=", getattr(mom_node, "name", None),
    "week=", w,
    "before_len=", len(before_s),
    "incoming_len=", len(incoming_s),
    "incoming_head=", _dbg_ids_head(incoming_s, 5),
)

# 既存処理
mom_node.psi4demand[w][0].extend(incoming_s)

after_s = list((mom_node.psi4demand[w][0] or []))
dup_in_after_s = len(after_s) - len(set(str(x) for x in after_s))

print(
    "[mom-write-after:S]",
    "mom=", getattr(mom_node, "name", None),
    "week=", w,
    "after_len=", len(after_s),
    "dup_in_after=", dup_in_after_s,
    "after_head=", _dbg_ids_head(after_s, 5),
)
```

### P slot に書く前後

```python id="v31gmu"
before_p = list((mom_node.psi4demand[w][3] or []))
incoming_p = list(lot_ids_p or lot_ids or [])

print(
    "[mom-write-before:P]",
    "mom=", getattr(mom_node, "name", None),
    "week=", w,
    "before_len=", len(before_p),
    "incoming_len=", len(incoming_p),
    "incoming_head=", _dbg_ids_head(incoming_p, 5),
)

# 既存処理
mom_node.psi4demand[w][3].extend(incoming_p)

after_p = list((mom_node.psi4demand[w][3] or []))
dup_in_after_p = len(after_p) - len(set(str(x) for x in after_p))

print(
    "[mom-write-after:P]",
    "mom=", getattr(mom_node, "name", None),
    "week=", w,
    "after_len=", len(after_p),
    "dup_in_after=", dup_in_after_p,
    "after_head=", _dbg_ids_head(after_p, 5),
)
```

---

## 5. もし `extend()` の前に clear していないなら、これも確認

今回の症状は `total=184844 / unique=92422` なので、**同じ束を 2回 extend した**可能性が濃いです。 

そのため、week 処理の冒頭で slot を clear しているかも見てください。
そこに debug を入れるなら、こうです。

```python id="f7nm7p"
print(
    "[mom-clear-check]",
    "mom=", getattr(mom_node, "name", None),
    "week=", w,
    "slotS_before_clear=", len(mom_node.psi4demand[w][0] or []),
    "slotP_before_clear=", len(mom_node.psi4demand[w][3] or []),
)
```

もし clear をしていないなら、同じ run の中でも二重化しやすいです。

---

## 6. ログの見方

次にあなたが見るべきポイントは、この3つです。

### A

同じ `week / leaf / lot_head` が

* `chosen_mom=ASIA`
* `chosen_mom=EURO`

の両方で出ていないか

### B

`[mom-write-before:S]` の `before_len` が、同じ week で 0 ではなく既に埋まっていないか

### C

`[mom-write-after:S]` の `dup_in_after` が、書いた直後に増えていないか

これで、

* 割当が二重なのか
* append が二重なのか
* clear 漏れなのか

を切り分けられます。

---

## 7. いま最も疑わしいもの

今回の step3 直後ログだけ見ると、最も疑わしいのは次のどちらかです。

* `mom_policy` が **同じ leaf lots を ASIA / EURO 両方へ返している**
* `inbound_backward_MOM_to_leaf()` の中で **同じ lot_ids を 2回 extend している**

step3 の時点で両 MOM が完全同型なので、**step3 内部の割当または書き込み**が本丸です。 

必要なら次に、あなたの `inbound_backward_MOM_to_leaf(...)` の実コード断片を貼ってもらえれば、**どの行の前後にこの debug を置くべきか**をピンポイントで指示できます。

# ****************

ありがとうございます。
この実コードを見ると、**本丸はかなり `allocate_markets_to_moms(...)` 寄り**です。

理由は単純で、この `inbound_backward_MOM_to_leaf(...)` の中で

1. `connect_outbound2inbound(out_root, in_root)`
2. `allocate_markets_to_moms(...)`
3. `calc_all_psiS2P2childS_preorder(in_root)`
4. `copy_demand_to_supply_rec(in_root)`
5. `calc_all_psi2i4supply_post(in_root)`

という順ですが、前のログでは **step3 の時点で demand 側がすでに ASIA/EURO 同型の 184844 / 92422** でした。
その後の `bridge_inbound_demand_to_supply()` は supply を clean seed しているだけなので、**step3 内部の 1) か 1.5)** が主犯候補です。しかも `market→MOM 割当` は 1.5 にしかありません。
なので、debug は

* `inbound_backward_MOM_to_leaf(...)` の中で **connect 前後 / allocate 前後**
* `allocate_markets_to_moms(...)` の中で **market→MOM decision と MOM demand append 前後**

に入れるのが最短です。

---

# まず engine module に追加する helper

```python id="h1ev8j"
def _dbg_ids_head(ids, n=5):
    try:
        return [str(x) for x in (ids or [])[:n]]
    except Exception:
        return []


def _dbg_total_unique_slot(psi, slot_idx=0):
    total = 0
    uniq = set()
    for week in (psi or []):
        try:
            lots = week[slot_idx] or []
        except Exception:
            lots = []
        total += len(lots)
        for lot in lots:
            uniq.add(str(lot))
    return total, len(uniq)


def _dbg_nonzero_weeks_slot(psi, slot_idx=0, limit=8):
    hits = []
    for w, week in enumerate(psi or [], start=1):
        try:
            cnt = len(week[slot_idx] or [])
        except Exception:
            cnt = 0
        if cnt:
            hits.append((w, cnt))
            if len(hits) >= limit:
                break
    return hits


def _dbg_dump_focus_moms(in_root, label="", focus_names=None):
    names_filter = set(focus_names or [])
    stack = [in_root]
    moms = []
    seen = set()

    while stack:
        n = stack.pop()
        if n is None:
            continue
        if id(n) in seen:
            continue
        seen.add(id(n))

        nm = str(getattr(n, "name", "") or "")
        if nm.startswith("MOM"):
            if not names_filter or nm in names_filter:
                moms.append(n)

        stack.extend(getattr(n, "children", []) or [])

    moms = sorted(moms, key=lambda x: str(getattr(x, "name", "")))

    print("=" * 110)
    print(f"[mom-engine-debug] {label}")
    for mom in moms:
        nm = str(getattr(mom, "name", "") or "")
        psi_d = getattr(mom, "psi4demand", None) or []
        psi_s = getattr(mom, "psi4supply", None) or []

        dS_total, dS_unique = _dbg_total_unique_slot(psi_d, 0)
        dP_total, dP_unique = _dbg_total_unique_slot(psi_d, 3)
        sS_total, sS_unique = _dbg_total_unique_slot(psi_s, 0)
        sP_total, sP_unique = _dbg_total_unique_slot(psi_s, 3)

        print(
            f"[mom-engine-debug] {nm} | "
            f"demand S total={dS_total} unique={dS_unique}, "
            f"demand P total={dP_total} unique={dP_unique}, "
            f"supply S total={sS_total} unique={sS_unique}, "
            f"supply P total={sP_total} unique={sP_unique}"
        )
        print(
            f"[mom-engine-debug] {nm} | "
            f"demand_nz_S={_dbg_nonzero_weeks_slot(psi_d, 0)} | "
            f"demand_nz_P={_dbg_nonzero_weeks_slot(psi_d, 3)}"
        )
    print("=" * 110)


def _dbg_overlap_between_two_moms(in_root, mom_a, mom_b, slot_idx=0):
    found = {}
    stack = [in_root]
    seen = set()
    while stack:
        n = stack.pop()
        if n is None:
            continue
        if id(n) in seen:
            continue
        seen.add(id(n))
        nm = str(getattr(n, "name", "") or "")
        if nm in (mom_a, mom_b):
            found[nm] = n
        stack.extend(getattr(n, "children", []) or [])

    if mom_a not in found or mom_b not in found:
        print(f"[mom-overlap] {mom_a}/{mom_b} not found")
        return

    def collect_ids(node):
        ids = []
        psi = getattr(node, "psi4demand", None) or []
        for week in psi:
            try:
                ids.extend([str(x) for x in (week[slot_idx] or [])])
            except Exception:
                pass
        return set(ids)

    a_ids = collect_ids(found[mom_a])
    b_ids = collect_ids(found[mom_b])
    inter = a_ids & b_ids

    print(
        f"[mom-overlap] slot={slot_idx} "
        f"{mom_a}={len(a_ids)} {mom_b}={len(b_ids)} overlap={len(inter)} "
        f"head={list(sorted(inter))[:10]}"
    )
```

---

# `inbound_backward_MOM_to_leaf(...)` にそのまま差し込む debug

あなたの current code に合わせると、この形がそのまま入れやすいです。

```python id="9l5o5m"
def inbound_backward_MOM_to_leaf(out_root, in_root, layer="demand", mom_policy=None):

    print("[mom-engine-debug] enter inbound_backward_MOM_to_leaf")
    _dbg_dump_focus_moms(
        in_root,
        label="before connect_outbound2inbound",
        focus_names=["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
    )

    # 1) OUT→IN の接続（root の demand/supply を一致コピー）
    connect_outbound2inbound(out_root, in_root)

    _dbg_dump_focus_moms(
        in_root,
        label="after connect_outbound2inbound / before allocate_markets_to_moms",
        focus_names=["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
    )
    _dbg_overlap_between_two_moms(
        in_root,
        "MOM_final_assy_ASIA",
        "MOM_final_assy_EURO",
        slot_idx=0,
    )

    # 1.5) 生産配分ポリシー適用
    if mom_policy:
        print("[mom-engine-debug] calling allocate_markets_to_moms")
        out_root, in_root = allocate_markets_to_moms(
            out_root,
            in_root,
            policy=mom_policy,
            source_layer="outbound_supply",
            debug=True,
        )

        _dbg_dump_focus_moms(
            in_root,
            label="after allocate_markets_to_moms / before preorder",
            focus_names=["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
        )
        _dbg_overlap_between_two_moms(
            in_root,
            "MOM_final_assy_ASIA",
            "MOM_final_assy_EURO",
            slot_idx=0,
        )

    # 2) PRE-ORDER
    calc_all_psiS2P2childS_preorder(in_root)

    _dbg_dump_focus_moms(
        in_root,
        label="after calc_all_psiS2P2childS_preorder / before clone demand->supply",
        focus_names=["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
    )
    _dbg_overlap_between_two_moms(
        in_root,
        "MOM_final_assy_ASIA",
        "MOM_final_assy_EURO",
        slot_idx=0,
    )

    # 3) & 4)  "clone psi4demand to psi4supply"
    def _clone_psi_layer(psi_layer):
        return [[slot[:] for slot in week] for week in psi_layer]

    def copy_demand_to_supply_rec(node):
        node.psi4supply = _clone_psi_layer(node.psi4demand)
        for c in node.children:
            copy_demand_to_supply_rec(c)

    copy_demand_to_supply_rec(in_root)

    _dbg_dump_focus_moms(
        in_root,
        label="after copy_demand_to_supply_rec / before calc_all_psi2i4supply_post",
        focus_names=["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
    )

    # 5) POST-ORDER
    calc_all_psi2i4supply_post(in_root)

    _dbg_dump_focus_moms(
        in_root,
        label="after calc_all_psi2i4supply_post / leave inbound_backward_MOM_to_leaf",
        focus_names=["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
    )

    print("[mom-engine-debug] leave inbound_backward_MOM_to_leaf")
    return out_root, in_root
```

---

# 本命: `allocate_markets_to_moms(...)` の中に入れる debug

ここが一番効きます。
あなたが求めている **“market→MOM 割当”** と **“MOM demand append 前後”** は、ここで見るのが正解です。

## 1. 割当前の clear 確認

MOM の demand slot を clear している箇所があるなら、その直前にこれを入れます。

```python id="zkgp6w"
print("[alloc-debug] before clear_existing_mom_demand")
for mom in mom_nodes:
    dS_total, dS_unique = _dbg_total_unique_slot(getattr(mom, "psi4demand", None) or [], 0)
    dP_total, dP_unique = _dbg_total_unique_slot(getattr(mom, "psi4demand", None) or [], 3)
    print(
        f"[alloc-debug] {mom.name} before clear | "
        f"demand S total={dS_total} unique={dS_unique}, "
        f"demand P total={dP_total} unique={dP_unique}"
    )
```

clear の直後にも置きます。

```python id="s563xf"
print("[alloc-debug] after clear_existing_mom_demand")
for mom in mom_nodes:
    dS_total, dS_unique = _dbg_total_unique_slot(getattr(mom, "psi4demand", None) or [], 0)
    dP_total, dP_unique = _dbg_total_unique_slot(getattr(mom, "psi4demand", None) or [], 3)
    print(
        f"[alloc-debug] {mom.name} after clear | "
        f"demand S total={dS_total} unique={dS_unique}, "
        f"demand P total={dP_total} unique={dP_unique}"
    )
```

これで、**clear 不足**がすぐ分かります。

---

## 2. market → MOM decision の debug

lot をどの MOM に入れるか決めた直後に入れます。
変数名はあなたの code に合わせて読み替えてください。

```python id="fzocjc"
print(
    "[mom-assign]",
    "week=", w,
    "market=", market_name if 'market_name' in locals() else getattr(market_node, "name", None),
    "leaf=", getattr(leaf_node, "name", None) if 'leaf_node' in locals() else None,
    "chosen_mom=", chosen_mom_name if 'chosen_mom_name' in locals() else getattr(chosen_mom, "name", None),
    "candidate_moms=", candidate_moms if 'candidate_moms' in locals() else None,
    "lot_count=", len(lot_ids or []),
    "lot_head=", _dbg_ids_head(lot_ids, 5),
)
```

### ここで見たいこと

同じ `week / market / lot_head` が

* `chosen_mom=ASIA`
* `chosen_mom=EURO`

の両方で出たら、**policy 適用で二重配賦**しています。

---

## 3. MOM demand append 前後の debug

MOM へ `psi4demand[w][0]` や `psi4demand[w][3]` に lot を入れる直前と直後に置きます。

### S slot

```python id="4wkcuy"
before_s = list(chosen_mom.psi4demand[w][0] or [])
incoming_s = list(lot_ids or [])

print(
    "[mom-write-before:S]",
    "mom=", chosen_mom.name,
    "week=", w,
    "before_len=", len(before_s),
    "incoming_len=", len(incoming_s),
    "incoming_head=", _dbg_ids_head(incoming_s, 5),
)

# existing code
chosen_mom.psi4demand[w][0].extend(incoming_s)

after_s = list(chosen_mom.psi4demand[w][0] or [])
dup_in_after_s = len(after_s) - len(set(str(x) for x in after_s))

print(
    "[mom-write-after:S]",
    "mom=", chosen_mom.name,
    "week=", w,
    "after_len=", len(after_s),
    "dup_in_after=", dup_in_after_s,
    "after_head=", _dbg_ids_head(after_s, 5),
)
```

### P slot

```python id="ldo9dg"
before_p = list(chosen_mom.psi4demand[w][3] or [])
incoming_p = list(lot_ids or [])

print(
    "[mom-write-before:P]",
    "mom=", chosen_mom.name,
    "week=", w,
    "before_len=", len(before_p),
    "incoming_len=", len(incoming_p),
    "incoming_head=", _dbg_ids_head(incoming_p, 5),
)

# existing code
chosen_mom.psi4demand[w][3].extend(incoming_p)

after_p = list(chosen_mom.psi4demand[w][3] or [])
dup_in_after_p = len(after_p) - len(set(str(x) for x in after_p))

print(
    "[mom-write-after:P]",
    "mom=", chosen_mom.name,
    "week=", w,
    "after_len=", len(after_p),
    "dup_in_after=", dup_in_after_p,
    "after_head=", _dbg_ids_head(after_p, 5),
)
```

---

# 何が分かるか

この debug を入れると、次の3パターンのどれかに絞れます。

### パターン A

`[mom-assign]` で同じ `lot_head` が ASIA と EURO の両方に出る
→ **policy 適用または assign loop が二重**

### パターン B

`[mom-write-before:*]` で `before_len` がすでに埋まっている
→ **clear 漏れ**

### パターン C

`[mom-write-after:*]` で `dup_in_after` が急増する
→ **same MOM に同じ lot を 2回 extend**

---

# いま最も怪しい場所

あなたの `inbound_backward_MOM_to_leaf(...)` を見る限り、やはり最も怪しいのは

```python id="jkyvl0"
out_root, in_root = allocate_markets_to_moms(
    out_root,
    in_root,
    policy=mom_policy,
    source_layer="outbound_supply",
    debug=True,
)
```

です。

その後の

* `calc_all_psiS2P2childS_preorder(in_root)`
* `copy_demand_to_supply_rec(in_root)`

は、**すでに出来上がった demand を伝播・複製**しているだけなので、
重複の原点はここより前である可能性が高いです。これは step3 直後ログとも一致します。 

必要なら次に、`allocate_markets_to_moms(...)` の実コード断片を貼ってもらえれば、
**どの行の前後にこの debug を置くかを本当にピンポイントで指定**します。

# ****************

はい。
この `allocate_markets_to_moms(...)` に対しては、**かなり直接的に debug を差し込めます。**

いまの code から読むと、注目点は2つです。

* `clear_existing_mom_demand` が **slot0 しか clear していない**
* 各 lot が **本当に 1回だけ、1つの MOM にだけ**入っているかを見ていない

特に今回の現象は、

* ASIA / EURO の両方に同じ unique lots
* 各 MOM 内でも `total = 2 * unique`

なので、
**「clear 漏れ」** と **「同じ lot の二重 assign / 二重 append」** を両方見るのが正解です。

---

# そのまま置き換えやすい debug 強化版

以下を、いまの `allocate_markets_to_moms(...)` の代わりに使ってください。
元のロジックはほぼ維持しつつ、debug だけ厚くしています。

```python
from collections import defaultdict


def allocate_markets_to_moms(
    out_root,
    in_root,
    policy: dict,
    *,
    source_layer: str = "outbound_supply",
    weeks: int | None = None,
    clear_existing_mom_demand: bool = True,
    debug: bool = True,
):
    """
    最小骨格:
    1) source lots を集める
    2) lot_id から market_key を抜く
    3) policy で担当 MOM を決める
    4) 担当 MOM の psi4demand[w][0] に lot を配る
    """

    def _dbg_ids_head(ids, n=5):
        try:
            return [str(x) for x in (ids or [])[:n]]
        except Exception:
            return []

    def _dbg_total_unique_slot(psi, slot_idx=0):
        total = 0
        uniq = set()
        for week in (psi or []):
            try:
                lots = week[slot_idx] or []
            except Exception:
                lots = []
            total += len(lots)
            for lot in lots:
                uniq.add(str(lot))
        return total, len(uniq)

    def _dbg_nonzero_weeks_slot(psi, slot_idx=0, limit=8):
        hits = []
        for w_idx, week in enumerate(psi or [], start=1):
            try:
                cnt = len(week[slot_idx] or [])
            except Exception:
                cnt = 0
            if cnt:
                hits.append((w_idx, cnt))
                if len(hits) >= limit:
                    break
        return hits

    mom_nodes = _find_nodes_by_prefix(in_root, "MOM_")
    mom_name_list = [n.name for n in mom_nodes]
    mom_map = {n.name: n for n in mom_nodes}

    if not mom_nodes:
        if debug:
            print("[allocate_markets_to_moms] no MOM nodes found")
        return out_root, in_root

    # 週数
    if source_layer == "outbound_supply":
        base = getattr(out_root, "psi4supply", []) or []
    elif source_layer == "inbound_root_demand":
        base = getattr(in_root, "psi4demand", []) or []
    else:
        raise ValueError(f"unknown source_layer={source_layer}")

    W = min(len(base), len(getattr(in_root, "psi4demand", []) or []))
    if weeks is not None:
        W = min(W, int(weeks))

    if debug:
        print("=" * 110)
        print("[allocate_markets_to_moms] ENTER")
        print("[allocate_markets_to_moms] policy =", policy)
        print("[allocate_markets_to_moms] moms =", mom_name_list)
        print("[allocate_markets_to_moms] source_layer =", source_layer, "W =", W)

        for mom in mom_nodes:
            psi = getattr(mom, "psi4demand", None) or []
            s_total, s_unique = _dbg_total_unique_slot(psi, 0)
            p_total, p_unique = _dbg_total_unique_slot(psi, 3)
            print(
                f"[allocate_markets_to_moms][before-clear] {mom.name} | "
                f"S total={s_total} unique={s_unique} | "
                f"P total={p_total} unique={p_unique} | "
                f"nzS={_dbg_nonzero_weeks_slot(psi, 0)} | "
                f"nzP={_dbg_nonzero_weeks_slot(psi, 3)}"
            )

    # 既存の MOM demand を一旦クリア
    if clear_existing_mom_demand:
        for mom in mom_nodes:
            psi = getattr(mom, "psi4demand", None)
            if not isinstance(psi, list):
                continue
            for w in range(min(W, len(psi))):
                # まずは現状どおり S slot を clear
                psi[w][0] = []
                # ★ debug用途として P slot も見たい場合は以下を有効化
                # psi[w][3] = []

        if debug:
            for mom in mom_nodes:
                psi = getattr(mom, "psi4demand", None) or []
                s_total, s_unique = _dbg_total_unique_slot(psi, 0)
                p_total, p_unique = _dbg_total_unique_slot(psi, 3)
                print(
                    f"[allocate_markets_to_moms][after-clear] {mom.name} | "
                    f"S total={s_total} unique={s_unique} | "
                    f"P total={p_total} unique={p_unique} | "
                    f"nzS={_dbg_nonzero_weeks_slot(psi, 0)} | "
                    f"nzP={_dbg_nonzero_weeks_slot(psi, 3)}"
                )

    allocation_log = defaultdict(int)

    # 同じ週・同じ lot がどの MOM に割り当てられたかを記録
    assigned_once = {}   # key=(w, lot_str) -> mom_name
    duplicate_assign = []

    # lot ごとに primary MOM を決める
    for w in range(W):
        if source_layer == "outbound_supply":
            lots = list(base[w][0]) if len(base[w]) > 0 else []
        else:
            lots = list(base[w][0]) if len(base[w]) > 0 else []

        if debug and w < 5:
            print(
                f"[allocate_markets_to_moms][week-source] w={w} "
                f"source_lot_count={len(lots)} source_head={_dbg_ids_head(lots, 5)}"
            )

        for lot in lots:
            lot_str = str(lot)
            market_key = _default_market_key_from_lot(lot)
            mom_name = _choose_mom_name(market_key, policy, mom_name_list)
            if mom_name is None:
                if debug:
                    print(
                        "[allocate_markets_to_moms][skip] "
                        f"w={w} lot={lot_str} market_key={market_key} mom=None"
                    )
                continue

            mom = mom_map.get(mom_name)
            if mom is None:
                if debug:
                    print(
                        "[allocate_markets_to_moms][skip] "
                        f"w={w} lot={lot_str} market_key={market_key} "
                        f"mom_name={mom_name} not found"
                    )
                continue

            key = (w, lot_str)
            if key in assigned_once:
                prev_mom = assigned_once[key]
                duplicate_assign.append((w, lot_str, prev_mom, mom_name))
                if debug:
                    print(
                        "[allocate_markets_to_moms][DUP-ASSIGN] "
                        f"w={w} lot={lot_str} market_key={market_key} "
                        f"prev_mom={prev_mom} new_mom={mom_name}"
                    )
            else:
                assigned_once[key] = mom_name

            before_len = len(mom.psi4demand[w][0] or [])
            before_head = _dbg_ids_head(mom.psi4demand[w][0], 5)

            if debug and w < 5:
                print(
                    "[allocate_markets_to_moms][assign] "
                    f"w={w} lot={lot_str} market_key={market_key} "
                    f"chosen_mom={mom_name} before_len={before_len} "
                    f"before_head={before_head}"
                )

            mom.psi4demand[w][0].append(lot)
            allocation_log[(w, mom_name)] += 1

            after_len = len(mom.psi4demand[w][0] or [])
            if debug and w < 5:
                print(
                    "[allocate_markets_to_moms][write-after] "
                    f"w={w} lot={lot_str} chosen_mom={mom_name} after_len={after_len}"
                )

    if debug:
        print("[allocate_markets_to_moms] total allocated by MOM per week summary:")
        sample = defaultdict(int)
        for (_, mom_name), cnt in allocation_log.items():
            sample[mom_name] += cnt
        print("[allocate_markets_to_moms] total allocated by MOM =", dict(sample))

        if duplicate_assign:
            print("[allocate_markets_to_moms] duplicate assignments detected:", len(duplicate_assign))
            print("[allocate_markets_to_moms] duplicate sample head =", duplicate_assign[:10])
        else:
            print("[allocate_markets_to_moms] duplicate assignments detected: 0")

        for mom in mom_nodes:
            psi = getattr(mom, "psi4demand", None) or []
            s_total, s_unique = _dbg_total_unique_slot(psi, 0)
            p_total, p_unique = _dbg_total_unique_slot(psi, 3)
            print(
                f"[allocate_markets_to_moms][after-alloc] {mom.name} | "
                f"S total={s_total} unique={s_unique} | "
                f"P total={p_total} unique={p_unique} | "
                f"nzS={_dbg_nonzero_weeks_slot(psi, 0)} | "
                f"nzP={_dbg_nonzero_weeks_slot(psi, 3)}"
            )

        print("[allocate_markets_to_moms] LEAVE")
        print("=" * 110)

    return out_root, in_root
```

---

# この debug で何が分かるか

## 1. clear 漏れ

ここを見ます。

```text
[allocate_markets_to_moms][before-clear] ...
[allocate_markets_to_moms][after-clear] ...
```

### 正常なら

* `after-clear` の `S total=0 unique=0`

### 異常なら

* clear したつもりでも `S total` が残る
* または `P total` が残り続ける

---

## 2. 同じ lot が 2つの MOM に割り当てられているか

ここを見ます。

```text
[allocate_markets_to_moms][DUP-ASSIGN] ...
```

これが出たら、**同じ `(week, lot)` が複数 MOM に assign** されています。

---

## 3. 同じ MOM に同じ lot を二重 append しているか

今回の code は `assigned_once` を `(w, lot)` 単位で見ているので、
同一週の同一 lot が 2回現れれば分かります。

---

# ここで特に怪しい点

今の code を見て、かなり気になるのはこれです。

```python
if clear_existing_mom_demand:
    ...
    for w in range(min(W, len(psi))):
        psi[w][0] = []
```

**slot0 しか clear していません。**

一方、あなたの直近ログでは step3 直後に

* demand S total=184844 / unique=92422
* demand P total=184844 / unique=92422

となっていました。
つまり、`P` 側の stale data が残っている可能性があります。 

なので debug 用としては、一時的にここも試す価値があります。

```python
psi[w][0] = []
psi[w][3] = []
```

ただし、まずは **debug を見てから**の方が安全です。

---

# いま最も見たいログ

次に欲しいのは、この3種類です。

* `[allocate_markets_to_moms][after-clear]`
* `[allocate_markets_to_moms][DUP-ASSIGN]`
* `[allocate_markets_to_moms][after-alloc]`

これで、

* clear 漏れか
* assign 二重か
* append 二重か

をかなり絞れます。

---

# いまの暫定見立て

この code 単体を見る限り、**同じ lot を両 MOM に入れる direct な loop には見えません。**
なので、まず疑う順はこうです。

1. `connect_outbound2inbound(out_root, in_root)` で MOM に既に lot が入っている
2. `clear_existing_mom_demand` が不十分
3. `_find_nodes_by_prefix` / `_find_node_by_name` の対象ノードが想定と違う
4. `base[w][0]` 自体に同じ lot が重複している

必要なら次に、`connect_outbound2inbound(...)` の code を見れば、
かなり pin point できます。

# ****************

いまの connect_outbound2inbound() を見る限り、ここは「root の OUT→IN コピー」専用です。
次は、これが MOM 重複の直接犯か、それとも前段の土台づくりかを、コードとログをつないで詰めます。

Thought for 44s

この connect_outbound2inbound() を見ると、かなり大事なことが分かります。

結論

connect_outbound2inbound() 自体は、MOM に直接 lot を二重配賦していません。
ただし、「inbound root に outbound 全量を丸ごと入れる」ので、その後の preorder 伝播で全 MOM に広がる土台を作っています。
今回の症状だと、直接犯は allocate_markets_to_moms() 単体というより、connect_outbound2inbound() で root に全量を置いたあと、calc_all_psiS2P2childS_preorder(in_root) が各 branch に流している可能性がかなり高いです。

まず、この関数がやっていること
root_node_inbound.psi4demand[w][0] = root_node_outbound.psi4supply[w][0].copy()
...
root_node_inbound.psi4supply[w][3] = root_node_outbound.psi4supply[w][3].copy()

なので、コピー先は inbound root だけです。
MOM_final_assy_ASIA や MOM_final_assy_EURO に直接 append しているわけではありません。

つまり、この関数単独では

ASIA に 92,422 unique
EURO に 同じ 92,422 unique

という配賦は作れません。

では、なぜ怪しいのか

inbound_backward_MOM_to_leaf(...) の流れはこうでした。

connect_outbound2inbound(out_root, in_root)
allocate_markets_to_moms(...)
calc_all_psiS2P2childS_preorder(in_root)
copy_demand_to_supply_rec(in_root)
calc_all_psi2i4supply_post(in_root)

そしてログでは、step3 の直後ですでに ASIA/EURO の両 MOM が完全同型です。
しかも step3.5、step4、step5 ではその数字が変わっていません。

なので、step3 の内部で起きていることはかなりこう読めます。

読み筋
connect_outbound2inbound() が inbound root に outbound 全量を入れる
allocate_markets_to_moms() は MOM の slot0 だけを触る
その後 calc_all_psiS2P2childS_preorder(in_root) が
root から子へ demand を伝播して、結果的に全 MOM に同じ root 由来 lot を流している

要するに、
root に全量がある状態で preorder を回していること自体が危険です。

いまのコードから見える具体的な危険点
1. connect_outbound2inbound() は root demand も root supply も全部埋める

これは inbound root にとっては、かなり強い初期状態です。

2. allocate_markets_to_moms() は MOM の psi4demand[w][0] しか clear していない

P は消していませんし、root 側も消していません。
そのため、policy で MOM に振ったものとは別に、root 由来の demand / P が preorder で流れてくる余地があります。

3. calc_all_psiS2P2childS_preorder(in_root) は名前どおり親→子の伝播をします

関数名からして、root に全量があるなら、全 child branch へ広がるのが自然です。
今回、ASIA/EURO の両 MOM が同型であることとも整合します。

いまの最有力仮説

いま一番自然な仮説はこれです。

仮説
connect_outbound2inbound() が inbound root に outbound 全量をコピー
allocate_markets_to_moms() は MOM slot0 に割当を書く
しかし root 側 demand/P が残っている
calc_all_psiS2P2childS_preorder(in_root) が root 由来 lot を 全 MOM branch に配る
結果として ASIA / EURO の両 MOM に同じ unique lot 群が乗る
total=2*unique になっているのは、
policy で書いた分 + preorder で root から降ってきた分
の二重取りである可能性が高い

これは、step3 直後に

demand S = 184844 / 92422
demand P = 184844 / 92422
supply S/P まで同型

になっているログとかなり合います。

次に入れると効く最小 debug

ここで一番効くのは、root と MOM を同時に見ることです。
connect_outbound2inbound() の直後と allocate_markets_to_moms() の直後、さらに preorder の直後で、in_root と MOM_* を比較します。

A. connect_outbound2inbound() の直後
print("[root-debug] after connect_outbound2inbound")
for slot_idx, slot_name in [(0, "S"), (3, "P")]:
    total = 0
    uniq = set()
    for week in (in_root.psi4demand or []):
        try:
            lots = week[slot_idx] or []
        except Exception:
            lots = []
        total += len(lots)
        for x in lots:
            uniq.add(str(x))
    print(f"[root-debug] in_root demand {slot_name} total={total} unique={len(uniq)}")
B. allocate_markets_to_moms() の直後

同じものを root に対しても出す。
MOM だけでなく root demand が残っているか を見る。

C. calc_all_psiS2P2childS_preorder(in_root) の直後

root と MOM の両方を出す。
ここで

root に 92422 unique
MOM ASIA に 92422 unique
MOM EURO に 92422 unique

となれば、root 由来のブロードキャストの可能性が非常に高いです。

先に試す価値がある修正案

debug の次に試すなら、私はこの2つを候補にします。

修正案1

connect_outbound2inbound() で inbound root の supply まで埋めない
まず demand だけにして、supply は後段で作る。

修正案2

allocate_markets_to_moms() の前に、
root から下流へ preorder させたくない slot を clearする
特に inbound root の demand S/P をどう扱うかを明示する。

どちらが正しいかはモデル意図次第ですが、
少なくとも今は root に全量を持たせたまま preorder がかなり危険です。

一言でいうと

connect_outbound2inbound() は直接 MOM に二重配賦していません。
ただし、inbound root に outbound 全量を丸ごと置いてしまうため、その後の preorder で全 MOM に同じ lot が流れる温床になっている可能性が高いです。
今の第一容疑は、

connect_outbound2inbound() で root に全量投入 → calc_all_psiS2P2childS_preorder(in_root) で branch 全展開

です。

必要なら次に、
connect_outbound2inbound() 直後 / allocate_markets_to_moms() 直後 / preorder 直後に root と MOM を同時に出す debug code を、そのまま貼れる形で出します。