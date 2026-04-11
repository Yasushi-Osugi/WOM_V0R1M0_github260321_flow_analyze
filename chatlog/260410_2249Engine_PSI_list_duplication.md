はい。
`cockpit_tk.py` の **full-plan 実行メソッドの中で、step3.5 / step4 / step5 の直後に差し込める MOM別 debug** を、そのまま貼れる形で出します。

今回の `cockpit_tk.py` では、full-plan の流れは

* `step3 inbound_backward_MOM_to_leaf`
* `step3.5 inbound_seed_supply_from_demand`
* `step4 inbound_forward_leaf_to_MOM`
* `step5 push_pull`

となっており、step3.5 はご指摘の通り `eng.bridge_inbound_demand_to_supply(in_root)` です。

## 1. class `WOMCockpit` の helper セクションに追加する code

`_detect_default_decouple_nodes()` の前後あたり、class 内の helper 群にこれを追加してください。

```python
    def _dbg_total_and_unique_lots(self, psi, slot_idx=0):
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

    def _dbg_nonzero_weeks(self, psi, slot_idx=0, limit=8):
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

    def _debug_dump_mom_lot_counts(self, in_root, label="", focus_names=None):
        """
        MOM別の demand/supply lot 状況を表示する。
        total と unique を両方出すので、append重複の検出に使いやすい。
        slot convention:
          0 = S
          2 = I
          3 = P
        """
        if in_root is None:
            print(f"[mom-debug] {label} : in_root is None")
            return

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
        print(f"[mom-debug] {label}")
        if not moms:
            print("[mom-debug] no MOM nodes found under in_root")
            print("=" * 110)
            return

        for mom in moms:
            nm = str(getattr(mom, "name", "") or "")
            psi_d = getattr(mom, "psi4demand", None) or []
            psi_s = getattr(mom, "psi4supply", None) or []

            dS_total, dS_unique = self._dbg_total_and_unique_lots(psi_d, 0)
            dI_total, dI_unique = self._dbg_total_and_unique_lots(psi_d, 2)
            dP_total, dP_unique = self._dbg_total_and_unique_lots(psi_d, 3)

            sS_total, sS_unique = self._dbg_total_and_unique_lots(psi_s, 0)
            sI_total, sI_unique = self._dbg_total_and_unique_lots(psi_s, 2)
            sP_total, sP_unique = self._dbg_total_and_unique_lots(psi_s, 3)

            dS_nz = self._dbg_nonzero_weeks(psi_d, 0, limit=8)
            sS_nz = self._dbg_nonzero_weeks(psi_s, 0, limit=8)
            dP_nz = self._dbg_nonzero_weeks(psi_d, 3, limit=8)
            sP_nz = self._dbg_nonzero_weeks(psi_s, 3, limit=8)

            print(
                f"[mom-debug] {nm} | "
                f"demand S total={dS_total} unique={dS_unique}, "
                f"I total={dI_total} unique={dI_unique}, "
                f"P total={dP_total} unique={dP_unique}"
            )
            print(
                f"[mom-debug] {nm} | "
                f"supply S total={sS_total} unique={sS_unique}, "
                f"I total={sI_total} unique={sI_unique}, "
                f"P total={sP_total} unique={sP_unique}"
            )
            print(
                f"[mom-debug] {nm} | "
                f"demand_nz_S={dS_nz} | supply_nz_S={sS_nz}"
            )
            print(
                f"[mom-debug] {nm} | "
                f"demand_nz_P={dP_nz} | supply_nz_P={sP_nz}"
            )

        print("=" * 110)
```

## 2. step3.5 / step4 / step5 の直後に差し込む code

`Run Full Plan` の中で、今の step 呼び出しのすぐ後ろにこれを入れてください。
`cockpit_tk.py` の full-plan 部分は、今まさにこの並びになっています。

```python
        print("[full-plan] step3.5 inbound_seed_supply_from_demand")
        eng.bridge_inbound_demand_to_supply(in_root)
        self._debug_dump_mom_lot_counts(
            in_root,
            label="after step3.5 bridge_inbound_demand_to_supply",
            focus_names=["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
        )

        print("[full-plan] step4 inbound_forward_leaf_to_MOM")
        out_root, in_root = eng.inbound_forward_leaf_to_MOM(out_root, in_root, layer="supply")
        self._debug_dump_mom_lot_counts(
            in_root,
            label="after step4 inbound_forward_leaf_to_MOM",
            focus_names=["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
        )

        print("[full-plan] step5 push_pull")
        out_root, in_root = eng.push_pull(out_root, in_root, decouple_nodes=decouples)
        self._debug_dump_mom_lot_counts(
            in_root,
            label="after step5 push_pull",
            focus_names=["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
        )
```

## 3. この debug で何が分かるか

特に見るべきは `total` と `unique` の差です。

たとえば、

```text
[mom-debug] MOM_final_assy_ASIA | demand S total=92422 unique=46211
```

のように `total` が `unique` のほぼ 2倍なら、
かなり強く **append 重複** を疑えます。

逆に、

```text
total=92422 unique=92422
```

なら、単純重複ではなく **本当に別々の lot が入っている**可能性が高いです。

また、`demand_nz_S` / `supply_nz_S` で

* step3.5 直後
* step4 直後
* step5 直後

を比べると、**どの step で ASIA と EURO の両方が膨らむか**が分かります。
今回のログでも step3.5 / 4 / 5 が連続し、その後に `push_pull` が流れているので、この3点観測がいちばん効きます。

## 4. まずの読み方

最初は、この3つだけ見れば十分です。

* step3.5 直後に、ASIA/EURO の `demand S total/unique`
* step3.5 直後に、ASIA/EURO の `supply S total/unique`
* step4 と step5 で、それがどう増減するか

これで、

* `bridge_inbound_demand_to_supply()` が両 MOM に seed しているのか
* `inbound_forward_leaf_to_MOM()` で増えているのか
* `push_pull()` でさらに複写されているのか

が切り分けしやすくなります。

次にそのログが取れたら、**どの step で二重化または両持ちが始まるか**を一緒に見れば、かなり pin point できます。
