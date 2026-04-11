はい。
まずは **step3 の planning 範囲を `in_root` 全体ではなく `MOM subtree` に限定する**完成版差分です。
いまの `inbound_backward_MOM_to_leaf()` は `connect_outbound2inbound()` の後に `calc_all_psiS2P2childS_preorder(in_root)` を回しており、その構造が root 起点の全 branch 伝播を招いている可能性が高いです。実際、step3 直後ですでに ASIA / EURO の両 MOM が同じ `unique=92422` を持ち、その後の step3.5 / 4 / 5 では増えていません。  

以下の diff は、**preorder / demand→supply clone / postorder をすべて MOM 起点に限定**します。
`connect_outbound2inbound()` と `allocate_markets_to_moms()` はそのまま残し、まずは step3 の broadcast を止める実験として最小で効く形です。現在の関数本体は、root 接続 → policy → preorder(in_root) → clone(in_root) → post(in_root) という流れです。 

```diff id="jgk4ja"
--- a/pysi/network/tree.py
+++ b/pysi/network/tree.py
@@
 def inbound_backward_MOM_to_leaf(out_root, in_root, layer="demand", mom_policy=None):
-
-    #@STOP
-    ##@ADD for debug
-    #print("[connect] len(out_root.psi4supply) =", len(out_root.psi4supply))
-    #print("[connect] len(in_root.psi4demand) =", len(in_root.psi4demand))
-    #
-    #for i, row in enumerate(in_root.psi4demand[:5]):
-    #    print(f"[connect] in_root.psi4demand[{i}] len =", len(row) if row is not None else None)
-    #
-    #for i, row in enumerate(out_root.psi4supply[:5]):
-    #    print(f"[connect] out_root.psi4supply[{i}] len =", len(row) if row is not None else None)
-
-
     # 1) OUT→IN の接続（root の demand/supply を一致コピー）
     connect_outbound2inbound(out_root, in_root)
-    
 
     # 1.5) 生産配分ポリシー適用
     if mom_policy:
         out_root, in_root = allocate_markets_to_moms(
             out_root,
@@
             debug=True,
         )
 
+    # 1.7) MOM subtree を planning 起点にする
+    # NOTE:
+    #   connect_outbound2inbound() で in_root に outbound 全量が入った状態で
+    #   preorder(in_root) を回すと、root/supply_point 起点で全 MOM branch に
+    #   同じ demand が伝播する危険がある。
+    #   そのため、step3 は MOM 以下だけを対象に backward planning する。
+    mom_list = _find_nodes_by_prefix(in_root, "MOM_")
+    mom_list = sorted(mom_list, key=lambda n: getattr(n, "name", ""))
+
+    if not mom_list:
+        # fallback: 既存挙動
+        mom_list = [in_root]
 
-
-    # 2) PRE-ORDER: inbound の S→P（親） & P→S（子）を伝播（Backward）
-    calc_all_psiS2P2childS_preorder(in_root)  # ← 親P→子Sは demand レイヤに入る
+    # 2) PRE-ORDER: inbound の S→P（親） & P→S（子）を伝播（Backward）
+    #    root 全体ではなく、各 MOM subtree ごとに実行する
+    for a_mom in mom_list:
+        calc_all_psiS2P2childS_preorder(a_mom)
+
     # 3) & 4)  "clone psi4demand to psi4supply"
     def _clone_psi_layer(psi_layer):
         return [[slot[:] for slot in week] for week in psi_layer]
 
     def copy_demand_to_supply_rec(node):
         node.psi4supply = _clone_psi_layer(node.psi4demand)
         for c in node.children:
             copy_demand_to_supply_rec(c)
 
-    copy_demand_to_supply_rec(in_root)
+    for a_mom in mom_list:
+        copy_demand_to_supply_rec(a_mom)
+
     # 5) POST-ORDER: supply レイヤの P/S/CO から I を確定生成
-    calc_all_psi2i4supply_post(in_root)
+    for a_mom in mom_list:
+        calc_all_psi2i4supply_post(a_mom)
+
     return out_root, in_root
```

### この diff の意図

* `connect_outbound2inbound()` は残します
  まずは既存の root 接続を温存します。
* ただし、**step3 の計画生成は MOM subtree 限定**にします
* `copy_demand_to_supply_rec()` と `calc_all_psi2i4supply_post()` も合わせて MOM subtree 限定にします
  preorder だけ変えると後段でまた root 側状態が混ざるので、ここも揃えるのが安全です。

### この diff を入れた後の見どころ

再度、あなたがすでに入れた debug で

* `after step3 inbound_backward_MOM_to_leaf`
* `after step3.5 bridge_inbound_demand_to_supply`

の MOM counts を見てください。
期待値は、**ASIA / EURO の `unique` が分離するか、少なくとも “両 MOM 完全同型” が崩れること**です。 

### 注意点

この差分は、意図的に **`supply_point` / `root` を planning 起点から外す**ので、
inbound 側の上位集約 PSI は以前より薄くなる可能性があります。
ただ、今回の目的はまず **「MOM 配分が壊れている主因を外す」**ことなので、切り分けとしては正しい順番です。

次の一手としては 1つだけです。
この diff 適用後の `after step3 ...` と `after step3.5 ...` の MOM debug を見れば、`bridge_inbound_demand_to_supply(in_root)` まで MOM subtree 化すべきかが決まります。
