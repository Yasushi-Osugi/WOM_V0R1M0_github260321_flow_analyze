# pysi/plan/engines.py

# this "annotations" be the top position
from __future__ import annotations

from collections import deque
import inspect
from pysi.network.tree import *

# 既存のNode/PlanNode側にある想定のメソッドを呼び出す薄いラッパ
# - n.aggregate_children_P_into_parent_S(layer=...)
# - n.calcS2P(layer=...)
# - n.calcS2P_4supply()
# - n.calcPS2I4supply()
def _iter_postorder(root):
    st = [(root, False)]
    while st:
        n, done = st.pop()
        if not n:
            continue
        if done:
            yield n
        else:
            st.append((n, True))
            for c in getattr(n, "children", []) or []:
                st.append((c, False))


def _find(root, name: str):
    for n in _iter_postorder(root):
        if getattr(n, "name", None) == name:
            return n
    return None


def outbound_backward_leaf_to_MOM(out_root, in_root, layer="demand"):
    # 子P→親Sの集約 → 各ノードのS→P（SS/LV/休暇はノード実装に委譲）
    for n in _iter_postorder(out_root):
        if hasattr(n, "aggregate_children_P_into_parent_S"):
            n.aggregate_children_P_into_parent_S(layer=layer)
        if hasattr(n, "calcS2P"):
            n.calcS2P()  # .\pysi\network\node_base.py layer="demand" is default
            # n.calcS2P(layer=layer)
    return out_root, in_root


def inbound_MOM_leveling_vs_capacity(out_root, in_root, mom_name="MOM"):
    """
    Inbound (MOM) 側で、leaf から積み上がった P ロットを MOM の capacity で envelope し、
    overflow を前倒し(平準化)する簡易ロジック。

    ※ 従来は mom.nx_capacity (単一cap) のみ参照していたが、
       _wom_env.weekly_capability[...] があれば週次capで envelope する。
       (後方互換: weekly_capability が無ければ従来通り cap=nx_capacity)

    ★対応形式
      1) product階層あり: env.weekly_capability[product][mom_name][w]
      2) 旧形式:          env.weekly_capability[mom_name][w]
      3) どちらも無い:    mom.nx_capacity
    """
    #@STOP
    #mom = getattr(in_root, "children", {}).get(mom_name)
    mom = _find(in_root, mom_name)
    
    if mom is None:
        return out_root, in_root

    psi = getattr(mom, "psi4demand", None)
    if not psi:
        return out_root, in_root

    W = len(psi)
    cap = int(getattr(mom, "nx_capacity", 0) or 0)
    if cap <= 0:
        return out_root, in_root

    # env を inbound 側 or outbound 側の root から拾う（wom_pipeline の実装差を吸収）
    env = getattr(in_root, "_wom_env", None) or getattr(out_root, "_wom_env", None)

    for w in range(W):
        wc = (getattr(env, "weekly_capability", {}) or {}) if env else {}

        # 1) product階層あり: wc[product][mom_name][w]
        # 2) 旧形式: wc[mom_name][w]
        # 3) どちらも無い: cap（nx_capacity）で後方互換
        product = (
            getattr(env, "product", None)
            or getattr(out_root, "product_name", None)
            or getattr(in_root, "product_name", None)
        )

        series = None
        if product and isinstance(wc.get(product, None), dict):
            series = wc.get(product, {}).get(mom_name, None)
        if series is None:
            series = wc.get(mom_name, None)

        cap_w = int(
            (series[w] if (isinstance(series, (list, tuple)) and len(series) > w) else cap)
        )

        lots = mom.psi4demand[w][3]  # Pスロット
        if len(lots) > cap_w:
            overflow = lots[cap_w:]
            mom.psi4demand[w][3] = lots[:cap_w]

            # 前倒しへ平準化
            wp = w - 1
            while overflow and wp >= 0:
                room = max(0, cap_w - len(mom.psi4demand[wp][3]))
                if room:
                    take, overflow = overflow[:room], overflow[room:]
                    mom.psi4demand[wp][3].extend(take)
                wp -= 1

    return out_root, in_root


# =============================================================
def deep_copy_psi(psi):
    # psi[w][k] は lot_id のリスト想定
    return [[lst.copy() for lst in week] for week in psi]


def build_node_psi_dict(node, layer="demand", d=None):
    if d is None:
        d = {}
    psi = node.psi4demand if layer == "demand" else node.psi4supply
    d[node.name] = deep_copy_psi(psi)
    for c in node.children:
        build_node_psi_dict(c, layer, d)
    return d


def deep_copy_psi_dict(d_src):
    return {name: deep_copy_psi(psi) for name, psi in d_src.items()}


def re_connect_suppy_dict2psi(node, node_psi_dict_In4Sp):
    # 供給レイヤの実体を「辞書の配列」に統一（以後 GUI も同じ物を見る）
    node.psi4supply = node_psi_dict_In4Sp[node.name]
    for c in node.children:
        re_connect_suppy_dict2psi(c, node_psi_dict_In4Sp)

#@CHANGE
#def inbound_backward_MOM_to_leaf(out_root, in_root, layer="demand"):
def inbound_backward_MOM_to_leaf(out_root, in_root, layer="demand", mom_policy=None):

    #@STOP
    ##@ADD for debug
    #print("[connect] len(out_root.psi4supply) =", len(out_root.psi4supply))
    #print("[connect] len(in_root.psi4demand) =", len(in_root.psi4demand))
    #
    #for i, row in enumerate(in_root.psi4demand[:5]):
    #    print(f"[connect] in_root.psi4demand[{i}] len =", len(row) if row is not None else None)
    #
    #for i, row in enumerate(out_root.psi4supply[:5]):
    #    print(f"[connect] out_root.psi4supply[{i}] len =", len(row) if row is not None else None)


    # 1) OUT→IN の接続（root の demand/supply を一致コピー）
    connect_outbound2inbound(out_root, in_root)

    # 1.5) 生産配分ポリシー適用
    if mom_policy:
        out_root, in_root = allocate_markets_to_moms(
            out_root,
            in_root,
            policy=mom_policy,
            source_layer="outbound_supply",
            debug=True,
        )

    # 1.7) MOM subtree を planning 起点にする
    # NOTE:
    #   connect_outbound2inbound() で in_root に outbound 全量が入った状態で
    #   preorder(in_root) を回すと、root/supply_point 起点で全 MOM branch に
    #   同じ demand が伝播する危険がある。
    #   そのため、step3 は MOM 以下だけを対象に backward planning する。
    mom_list = _find_nodes_by_prefix(in_root, "MOM_")
    mom_list = sorted(mom_list, key=lambda n: getattr(n, "name", ""))

    if not mom_list:
        # fallback: 既存挙動
        mom_list = [in_root]

    # 2) PRE-ORDER: inbound の S→P（親） & P→S（子）を伝播（Backward）
    #    root 全体ではなく、各 MOM subtree ごとに実行する
    for a_mom in mom_list:
        calc_all_psiS2P2childS_preorder(a_mom)

    # 3) & 4) "clone psi4demand to psi4supply"
    def _clone_psi_layer(psi_layer):
        return [[slot[:] for slot in week] for week in psi_layer]

    def copy_demand_to_supply_rec(node):
        node.psi4supply = _clone_psi_layer(node.psi4demand)
        for c in node.children:
            copy_demand_to_supply_rec(c)

    for a_mom in mom_list:
        copy_demand_to_supply_rec(a_mom)

    # 5) POST-ORDER: supply レイヤの P/S/CO から I を確定生成
    for a_mom in mom_list:
        calc_all_psi2i4supply_post(a_mom)

    return out_root, in_root

def bridge_inbound_demand_to_supply(root):
    stack = [root]
    while stack:
        n = stack.pop()
        d = getattr(n, "psi4demand", None)
        s = getattr(n, "psi4supply", None)

        if isinstance(d, list) and isinstance(s, list):
            weeks = min(len(d), len(s))
            for w in range(weeks):
                demand_s = list(d[w][0]) if len(d[w]) > 0 else []
                # supply layer を clean seed
                s[w] = [demand_s, [], [], []]

        stack.extend(getattr(n, "children", []) or [])



# =============================================================
def inbound_forward_leaf_to_MOM(out_root, in_root, layer="supply"):
    for n in _iter_postorder(in_root):
        if hasattr(n, "calcPS2I4supply"):
            n.calcPS2I4supply()
    return out_root, in_root


# *************************************************
# PUSH and PULL engine
# *************************************************
def copy_S_demand2supply(node):  # TOBE 240926
    # 明示的に.copyする。
    plan_len = 53 * node.plan_range
    for w in range(0, plan_len):
        node.psi4supply[w][0] = node.psi4demand[w][0].copy()


def copy_P_demand2supply(node):  # TOBE 240926
    # 明示的に.copyする。
    plan_len = 53 * node.plan_range
    for w in range(0, plan_len):
        node.psi4supply[w][3] = node.psi4demand[w][3].copy()


def PUSH_process(node, tracer=None):
    if tracer is None:
        node.calcPS2I4supply()  # calc_psi with PULL_S
        print(f"PUSH_process applied to {node.name}")
    else:
        node.calcPS2I4supply_trace(tracer=tracer)  # native emit path
        print(f"PUSH_process_trace applied to {node.name}")


def PULL_process(node, tracer=None):
    copy_S_demand2supply(node)
    copy_P_demand2supply(node)
    if tracer is None:
        node.calcPS2I4supply()  # calc_psi with PULL_S&P
        print(f"PULL_process applied to {node.name}")
    else:
        node.calcPS2I4supply_trace(tracer=tracer)  # native emit path
        print(f"PULL_process_trace applied to {node.name}")


def apply_pull_process(node, tracer=None):
    for child in node.children:
        PULL_process(child, tracer=tracer)
        apply_pull_process(child, tracer=tracer)


def push_pull_all_psi2i_decouple4supply5(node, decouple_nodes, tracer=None):
    print("node in supply_proc", node.name)
    if node.name in decouple_nodes:
        if tracer is None:
            node.calcPS2I4supply()  # calc_psi with PULL_S
        else:
            node.calcPS2I4supply_trace(tracer=tracer)  # native emit path
        copy_S_demand2supply(node)
        PUSH_process(node, tracer=tracer)
        apply_pull_process(node, tracer=tracer)
    else:
        PUSH_process(node, tracer=tracer)
        for child in node.children:
            push_pull_all_psi2i_decouple4supply5(child, decouple_nodes, tracer=tracer)


# *****************
# helper for make_nodes_decouple_all
# *****************
def find_depth(node):
    if not node.parent:
        return 0
    else:
        return find_depth(node.parent) + 1


def find_all_leaves(node, leaves, depth=0):
    if not node.children:
        leaves.append((node, depth))  # (leafノード, 深さ) のタプルを追加
    else:
        for child in node.children:
            find_all_leaves(child, leaves, depth + 1)


def make_nodes_decouple_all(node):
    leaves = []
    leaves_name = []
    nodes_decouple = []
    find_all_leaves(node, leaves)
    pickup_list = sorted(leaves, key=lambda x: x[1], reverse=True)
    pickup_list = [leaf[0] for leaf in pickup_list]  # 深さ情報を取り除く
    for nd in pickup_list:
        nodes_decouple.append(nd.name)
    nodes_decouple_all = []
    while len(pickup_list) > 0:
        nodes_decouple_all.append(nodes_decouple.copy())
        current_node = pickup_list.pop(0)
        del nodes_decouple[0]
        parent_node = current_node.parent
        if parent_node is None:
            break
        if current_node.parent:
            depth = find_depth(parent_node)
            inserted = False
            for idx, node in enumerate(pickup_list):
                if find_depth(node) <= depth:
                    pickup_list.insert(idx, parent_node)
                    nodes_decouple.insert(idx, parent_node.name)
                    inserted = True
                    break
            if not inserted:
                pickup_list.append(parent_node)
                nodes_decouple.append(parent_node.name)
            for child in parent_node.children:
                if child in pickup_list:
                    pickup_list.remove(child)
                    nodes_decouple.remove(child.name)
        else:
            print("error: node dupplicated", parent_node.name)
    return nodes_decouple_all


# *************************************************
# GPT defined "PUSH and PULL engine"
# *************************************************
from typing import Iterable, Optional


def _normalize_decouple_nodes(decouple_nodes: Optional[Iterable]) -> list[str]:
    if not decouple_nodes:
        return []
    sample = next(iter(decouple_nodes))
    if hasattr(sample, "name"):  # Node の可能性
        return [n.name for n in decouple_nodes]
    return list(decouple_nodes)



def _subtree_name_set(root) -> set[str]:
    names = set()
    for n in _traverse(root):
        nm = str(getattr(n, "name", "") or "")
        if nm:
            names.add(nm)
    return names



def _filter_decouple_candidate_sets_to_subtree(candidate_sets, subtree_names: set[str]):
    """
    make_nodes_decouple_all(...) の候補列から、
    subtree 内に存在する node 名だけを残す。
    空になった候補列は捨てる。
    """
    filtered = []
    for group in candidate_sets or []:
        kept = [nm for nm in (group or []) if nm in subtree_names]
        if kept:
            filtered.append(kept)
    return filtered

def _resolve_seeded_dad_nodes(out_root, seeded_dads=None, handoff_result=None):
    """
    step4.5 の handoff 結果から、実行対象の DAD node list を返す。
    優先順位:
      1) 明示引数 seeded_dads
      2) handoff_result["dad_to_lots"]
      3) handoff_result["week_dad_counts"]
    """
    dad_names = []

    if seeded_dads:
        for x in seeded_dads:
            if hasattr(x, "name"):
                dad_names.append(getattr(x, "name", None))
            else:
                dad_names.append(str(x))

    elif isinstance(handoff_result, dict):
        if handoff_result.get("dad_to_lots"):
            dad_names.extend(list(handoff_result.get("dad_to_lots", {}).keys()))
        elif handoff_result.get("week_dad_counts"):
            for (_, dad_name), cnt in handoff_result.get("week_dad_counts", {}).items():
                if cnt:
                    dad_names.append(dad_name)

    # unique preserving order
    seen = set()
    uniq_names = []
    for nm in dad_names:
        if nm and nm not in seen:
            seen.add(nm)
            uniq_names.append(nm)

    dad_nodes = []
    for nm in uniq_names:
        node = _find_node_by_name(out_root, nm)
        if node is not None:
            dad_nodes.append(node)

    return dad_nodes

#@STOP
#def push_pull(out_root, in_root, decouple_nodes=None):
def push_pull(out_root, in_root, decouple_nodes=None, *, seeded_dads=None, handoff_result=None):

    """
    out_root, in_root を破壊的に更新して返す。
    GUI には一切依存しない（self.* を触らない）。
    """

    names = _normalize_decouple_nodes(decouple_nodes)
    dad_nodes = _resolve_seeded_dad_nodes(out_root, seeded_dads=seeded_dads, handoff_result=handoff_result)

    # DAD subtree ごとに実行する新モード
    if dad_nodes:
        print(f"[push_pull] using seeded DAD roots = {[n.name for n in dad_nodes]}")

        for dad in dad_nodes:
            subtree_names = _subtree_name_set(dad)

            # GUI で選んだ decouple_nodes があれば、その subtree に属するものだけ使う
            names_in_subtree = [nm for nm in names if nm in subtree_names]

            # 指定が無い / subtree に該当無しなら、その DAD subtree で自動決定
            if not names_in_subtree:
                nodes_decouple_all = make_nodes_decouple_all(dad)
                nodes_decouple_all = _filter_decouple_candidate_sets_to_subtree(
                    nodes_decouple_all,
                    subtree_names,
                )


                print(f"[push_pull][{dad.name}] auto decouple candidates = {nodes_decouple_all}")

                if not nodes_decouple_all:

                    #@STOP
                    #print(f"[WARN] push_pull: no decouple candidates found under {dad.name}")
                    #continue

                    #@ADD
                    # subtree 内に候補が無い場合は、DAD 自身を decouple とみなす
                    names_in_subtree = [dad.name]
                else:
                    # まずは DAD 自身を優先する
                    picked = None
                    for group in nodes_decouple_all:
                        if dad.name in group:
                            picked = [dad.name]
                            break

                    # DAD 自身が候補列に無ければ、旧 heuristic を subtree 限定で適用
                    if picked is None:
                        picked = (
                            nodes_decouple_all[-2]
                            if len(nodes_decouple_all) >= 2
                            else nodes_decouple_all[-1]
                        )

                    names_in_subtree = picked

                #@STOP
                #names_in_subtree = (
                #    nodes_decouple_all[-2]
                #    if len(nodes_decouple_all) >= 2
                #    else nodes_decouple_all[-1]
                #)

            print(f"[push_pull][{dad.name}] using decouple names = {names_in_subtree}")
            push_pull_all_psi2i_decouple4supply5(dad, names_in_subtree)

        return out_root, in_root

    # 旧来の root 起点 fallback
    if not names:
        nodes_decouple_all = make_nodes_decouple_all(out_root)

        #@ADD for debug
        print(f"[push_pull] auto decouple candidates = {nodes_decouple_all}")

        if not nodes_decouple_all:
            print("[WARN] push_pull: no decouple candidates found")
            return out_root, in_root

        names = nodes_decouple_all[-2] if len(nodes_decouple_all) >= 2 else nodes_decouple_all[-1]

    #@ADD for debug
    print(f"[push_pull] using decouple names = {names}")

    push_pull_all_psi2i_decouple4supply5(out_root, names)

    return out_root, in_root


# *************************************************
# end of PUSH and PULL engine
# *************************************************
def outbound_forward_push_DAD_to_buffer(root, layer="supply", dad_name="DAD", buffer_name="BUFFER"):
    dad = _find(root, dad_name)
    buf = _find(root, buffer_name)
    if not dad or not buf:
        return root
    psi = getattr(buf, "psi4supply", None)
    if not psi:
        return root
    W = len(psi)
    for w in range(W):
        buf.psi4supply[w][0] = list(getattr(dad.psi4supply[w], 0, []) or dad.psi4supply[w][0])
    if hasattr(buf, "calcS2P_4supply"):
        buf.calcS2P_4supply()
    if hasattr(buf, "calcPS2I4supply"):
        buf.calcPS2I4supply()
    return root


def outbound_backward_pull_buffer_to_leaf(root, layer="supply", buffer_name="BUFFER"):
    buf = _find(root, buffer_name)
    if not buf:
        return root
    q = deque([buf])
    while q:
        p = q.popleft()
        chs = getattr(p, "children", []) or []
        q.extend(chs)
        if not chs:
            continue
        W = len(getattr(p, "psi4supply", []) or [])
        for w in range(W):
            s_lots = p.psi4supply[w][0]
            if not s_lots:
                continue
            share = max(1, len(s_lots) // len(chs))
            k = 0
            for c in chs:
                take = s_lots[k : k + share]
                if take:
                    c.psi4supply[w][3].extend(take)  # 子のPへ
                k += share
    for n in _iter_postorder(root):
        if hasattr(n, "calcPS2I4supply"):
            n.calcPS2I4supply()
    return root


def run_engine_safenet(out_root, in_root, decouple_nodes, mode: str, layer: str = "demand", **kw):
    import inspect

    def _call(fn, *args, **kwargs):
        params = inspect.signature(fn).parameters
        filt = {k: v for k, v in kwargs.items() if k in params}
        return fn(*args, **filt)

    if mode == "outbound_backward_leaf_to_MOM":
        return outbound_backward_leaf_to_MOM(out_root, in_root, layer=layer)

    if mode == "inbound_MOM_leveling_vs_capacity":
        return _call(inbound_MOM_leveling_vs_capacity, out_root, in_root, **kw)

    if mode == "inbound_backward_MOM_to_leaf":
        return inbound_backward_MOM_to_leaf(out_root, in_root, layer=layer)

    if mode == "inbound_forward_leaf_to_MOM":
        return inbound_forward_leaf_to_MOM(out_root, in_root, layer="supply")

    if mode == "outbound_forward_push_DAD_to_buffer":
        return _call(push_pull, out_root, in_root, decouple_nodes=decouple_nodes, **kw)

    if mode == "outbound_backward_pull_buffer_to_leaf":
        return _call(outbound_backward_pull_buffer_to_leaf, out_root, layer="supply", **kw)

    raise ValueError(f"unknown mode={mode}")


def run_engine(out_root, in_root, decouple_nodes, mode: str, layer: str = "demand", **kw):
    if mode == "outbound_backward_leaf_to_MOM":
        return outbound_backward_leaf_to_MOM(out_root, in_root, layer=layer)

    if mode == "inbound_MOM_leveling_vs_capacity":

        def _only_accepted_kwargs(func, kw: dict) -> dict:
            try:
                params = inspect.signature(func).parameters
                return {k: v for k, v in kw.items() if k in params}
            except Exception:
                return {}

        safe_kw = _only_accepted_kwargs(inbound_MOM_leveling_vs_capacity, kw)
        return inbound_MOM_leveling_vs_capacity(out_root, in_root, **safe_kw)

    if mode == "inbound_backward_MOM_to_leaf":
        return inbound_backward_MOM_to_leaf(out_root, in_root, layer=layer)

    if mode == "inbound_forward_leaf_to_MOM":
        return inbound_forward_leaf_to_MOM(out_root, in_root, layer="supply")

    if mode == "outbound_forward_push_DAD_to_buffer":
        return push_pull(out_root, in_root, decouple_nodes, **kw)

    if mode == "outbound_backward_pull_buffer_to_leaf":
        return outbound_backward_pull_buffer_to_leaf(out_root, in_root, layer="supply", **kw)

    raise ValueError(f"unknown mode={mode}")

# ************
# Production Allocation Policy
# ************
import re
from collections import defaultdict


def _traverse(root):
    stack = [root]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(getattr(n, "children", []) or [])


def _find_nodes_by_prefix(root, prefix: str):
    return [n for n in _traverse(root) if str(getattr(n, "name", "")).startswith(prefix)]


def _find_node_by_name(root, name: str):
    for n in _traverse(root):
        if getattr(n, "name", None) == name:
            return n
    return None


def _default_market_key_from_lot(lot_id: str) -> str:
    """
    lot_id から市場キーを抜く最小版。
    まずは lot_id / anchor 情報に 'RT_CN_', 'RT_DE_' のような市場トークンが
    含まれている前提で、そこから region を返す。

    例:
      RT_CN_ONLINES_CN_PREMIUM_2028010001 -> 'CN'
      RT_DE_ONLINES_DE_PREMIUM_2028010001 -> 'DE'
    """
    s = str(lot_id or "")
    m = re.search(r"RT_([A-Z]{2})_", s)
    if m:
        return m.group(1)
    return "DEFAULT"


def _choose_mom_name(market_key: str, policy: dict, mom_nodes: list[str]) -> str | None:
    """
    policy 例:
    {
        "CN": ["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
        "JP": ["MOM_final_assy_ASIA", "MOM_final_assy_EURO"],
        "DE": ["MOM_final_assy_EURO", "MOM_final_assy_ASIA"],
        "UK": ["MOM_final_assy_EURO", "MOM_final_assy_ASIA"],
        "DEFAULT": ["MOM_final_assy_ASIA"]
    }
    """
    cands = policy.get(market_key) or policy.get("DEFAULT") or []
    for nm in cands:
        if nm in mom_nodes:
            return nm
    return mom_nodes[0] if mom_nodes else None


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

    想定用途:
      connect_outbound2inbound() の直後に呼ぶ
    """

    mom_nodes = _find_nodes_by_prefix(in_root, "MOM_")
    mom_name_list = [n.name for n in mom_nodes]

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

    # 既存の MOM demand を一旦クリア
    if clear_existing_mom_demand:
        for mom in mom_nodes:
            psi = getattr(mom, "psi4demand", None)
            if not isinstance(psi, list):
                continue
            for w in range(min(W, len(psi))):
                psi[w][0] = []

    allocation_log = defaultdict(int)

    # lot ごとに primary MOM を決める
    for w in range(W):
        if source_layer == "outbound_supply":
            lots = list(base[w][0]) if len(base[w]) > 0 else []
        else:
            lots = list(base[w][0]) if len(base[w]) > 0 else []

        for lot in lots:
            market_key = _default_market_key_from_lot(lot)
            mom_name = _choose_mom_name(market_key, policy, mom_name_list)
            if mom_name is None:
                continue

            mom = _find_node_by_name(in_root, mom_name)
            if mom is None:
                continue

            mom.psi4demand[w][0].append(lot)
            allocation_log[(w, mom_name)] += 1

    if debug:
        print("[allocate_markets_to_moms] policy =", policy)
        print("[allocate_markets_to_moms] moms =", mom_name_list)

        sample = defaultdict(int)
        for (_, mom_name), cnt in allocation_log.items():
            sample[mom_name] += cnt
        print("[allocate_markets_to_moms] total allocated by MOM =", dict(sample))

    return out_root, in_root


# =============================================================
# MOM -> DAD handoff bridge
# =============================================================
#1. **MOM 側の確定 supply** を読む
#   今は `mom.psi4supply[w][0]` を source にしています。
#
#2. **leaf を lot_id から解決**する
#   ここは最小版なので naming rule 依存です。後で metadata に置き換える前提です。
#
#3. **DAD 側の `psi4supply[w][3]` に seed**する
#   これで、その後の outbound planning を DAD subtree から回しやすくなります。

def _find_ancestor_by_prefix(root, target_name: str, prefix: str):
    """
    out_root から target_name を持つ node を見つけ、
    その祖先をたどって最初に prefix に一致する node を返す。
    """
    target = _find_node_by_name(root, target_name)
    if target is None:
        return None

    cur = getattr(target, "parent", None)
    while cur is not None:
        nm = str(getattr(cur, "name", "") or "")
        if nm.startswith(prefix):
            return cur
        cur = getattr(cur, "parent", None)
    return None


def _default_leaf_name_from_lot(lot_id: str) -> str | None:
    """
    最小版:
    lot_id 文字列の中から leaf(CS_*) 名を推定する。

    想定例:
      RT_CN_ONLINES_CN_PREMIUM_2028010001
      -> CS_CN_PREMIUM

    NOTE:
      現段階では naming rule 依存の暫定版。
      将来的には lot metadata / demand anchor object へ置き換えたい。
    """
    s = str(lot_id or "")

    # まず明示的な CS_ token を優先
    m = re.search(r"(CS_[A-Z0-9_]+)", s)
    if m:
        return m.group(1)

    # 最小フォールバック:
    # RT_XX_*** の lot から市場 suffix を拾って CS_XX_*** を組み立てる
    # ここは実データに合わせて後で強化する前提
    m2 = re.search(r"RT_([A-Z]{2})_([A-Z0-9_]+)", s)
    if m2:
        return f"CS_{m2.group(1)}_{m2.group(2)}"

    return None


def _build_leaf_to_dad_map(out_root):
    """
    outbound tree から leaf(CS_*) -> DAD_* の対応表を作る。
    """
    mapping = {}
    for n in _traverse(out_root):
        nm = str(getattr(n, "name", "") or "")
        if nm.startswith("CS_"):
            dad = _find_ancestor_by_prefix(out_root, nm, "DAD_")
            if dad is not None:
                mapping[nm] = dad.name
    return mapping


def allocate_lots_to_dads(
    out_root,
    in_root,
    *,
    source_moms: list[str] | None = None,
    source_slot: int = 0,   # MOM side source: psi4supply[w][0:S]
    seed_slot: int = 3,     # DAD side seed:   psi4supply[w][3:P]
    weeks: int | None = None,
    clear_existing_dad_seed: bool = True,
    debug: bool = True,
):
    """
    MOM subtree で確定した supply lot を、対応する DAD subtree 入口へ handoff する最小 skeleton。

    基本思想:
      1) MOM.psi4supply[w][source_slot] を読む
      2) lot_id から最終 leaf(CS_*) を推定する
      3) leaf -> DAD を outbound tree から逆引きする
      4) DAD.psi4supply[w][seed_slot] に seed する

    返り値:
      out_root, in_root, handoff_result
    """

    # 1) MOM / DAD 候補
    all_moms = _find_nodes_by_prefix(in_root, "MOM_")
    if source_moms:
        moms = [m for m in all_moms if m.name in set(source_moms)]
    else:
        moms = all_moms

    dad_nodes = _find_nodes_by_prefix(out_root, "DAD_")
    dad_map = {n.name: n for n in dad_nodes}

    if not moms:
        if debug:
            print("[allocate_lots_to_dads] no MOM nodes found")
        return out_root, in_root, {
            "lot_to_leaf": {},
            "lot_to_dad": {},
            "dad_to_lots": {},
            "week_dad_counts": {},
            "unresolved_lots": [],
            "unresolved_leafs": [],
        }

    if not dad_nodes:
        if debug:
            print("[allocate_lots_to_dads] no DAD nodes found")
        return out_root, in_root, {
            "lot_to_leaf": {},
            "lot_to_dad": {},
            "dad_to_lots": {},
            "week_dad_counts": {},
            "unresolved_lots": [],
            "unresolved_leafs": [],
        }

    # 2) leaf -> DAD map
    leaf_to_dad = _build_leaf_to_dad_map(out_root)

    # 3) 対象週数
    W = 0
    for mom in moms:
        psi = getattr(mom, "psi4supply", None) or []
        W = max(W, len(psi))
    if weeks is not None:
        W = min(W, int(weeks))

    # 4) 必要なら DAD seed slot を clear
    if clear_existing_dad_seed:
        for dad in dad_nodes:
            psi = getattr(dad, "psi4supply", None)
            if not isinstance(psi, list):
                continue
            for w in range(min(W, len(psi))):
                psi[w][seed_slot] = []

    # 5) audit structures
    lot_to_leaf = {}
    lot_to_dad = {}
    dad_to_lots = defaultdict(list)
    week_dad_counts = defaultdict(int)
    unresolved_lots = []
    unresolved_leafs = []

    # duplicate handoff 防止用
    seeded_once = set()   # (w, lot_str)

    # 6) MOM -> DAD handoff
    for mom in moms:
        psi = getattr(mom, "psi4supply", None) or []

        for w in range(min(W, len(psi))):
            try:
                lots = list(psi[w][source_slot] or [])
            except Exception:
                lots = []

            if debug and w < 5 and lots:
                print(
                    f"[allocate_lots_to_dads][source] mom={mom.name} w={w} "
                    f"lot_count={len(lots)} head={[str(x) for x in lots[:5]]}"
                )

            for lot in lots:
                lot_str = str(lot)

                # 同じ週・同じ lot の二重 seed を避ける
                key = (w, lot_str)
                if key in seeded_once:
                    if debug:
                        print(
                            f"[allocate_lots_to_dads][DUP-SEED-SKIP] "
                            f"mom={mom.name} w={w} lot={lot_str}"
                        )
                    continue
                seeded_once.add(key)

                leaf_name = _default_leaf_name_from_lot(lot_str)
                lot_to_leaf[lot_str] = leaf_name

                if not leaf_name:
                    unresolved_lots.append((w, mom.name, lot_str, "leaf_not_resolved"))
                    if debug:
                        print(
                            f"[allocate_lots_to_dads][UNRESOLVED-LEAF] "
                            f"mom={mom.name} w={w} lot={lot_str}"
                        )
                    continue

                dad_name = leaf_to_dad.get(leaf_name)
                lot_to_dad[lot_str] = dad_name

                if not dad_name:
                    unresolved_leafs.append((w, mom.name, lot_str, leaf_name, "dad_not_resolved"))
                    if debug:
                        print(
                            f"[allocate_lots_to_dads][UNRESOLVED-DAD] "
                            f"mom={mom.name} w={w} lot={lot_str} leaf={leaf_name}"
                        )
                    continue

                dad = dad_map.get(dad_name)
                if dad is None:
                    unresolved_leafs.append((w, mom.name, lot_str, leaf_name, "dad_node_missing"))
                    if debug:
                        print(
                            f"[allocate_lots_to_dads][MISSING-DAD-NODE] "
                            f"mom={mom.name} w={w} lot={lot_str} leaf={leaf_name} dad={dad_name}"
                        )
                    continue

                dad.psi4supply[w][seed_slot].append(lot)
                dad_to_lots[dad_name].append(lot_str)
                week_dad_counts[(w, dad_name)] += 1

                if debug and w < 5:
                    print(
                        f"[allocate_lots_to_dads][handoff] "
                        f"mom={mom.name} w={w} lot={lot_str} leaf={leaf_name} dad={dad_name}"
                    )

    handoff_result = {
        "lot_to_leaf": lot_to_leaf,
        "lot_to_dad": lot_to_dad,
        "dad_to_lots": dict(dad_to_lots),
        "week_dad_counts": dict(week_dad_counts),
        "unresolved_lots": unresolved_lots,
        "unresolved_leafs": unresolved_leafs,
    }

    if debug:
        print("=" * 110)
        print("[allocate_lots_to_dads] moms =", [m.name for m in moms])
        print("[allocate_lots_to_dads] dads =", list(dad_map.keys()))

        dad_summary = defaultdict(int)
        for (_, dad_name), cnt in week_dad_counts.items():
            dad_summary[dad_name] += cnt
        print("[allocate_lots_to_dads] total handed off by DAD =", dict(dad_summary))

        print("[allocate_lots_to_dads] unresolved_lots =", len(unresolved_lots))
        print("[allocate_lots_to_dads] unresolved_leafs =", len(unresolved_leafs))
        if unresolved_lots:
            print("[allocate_lots_to_dads] unresolved_lots head =", unresolved_lots[:10])
        if unresolved_leafs:
            print("[allocate_lots_to_dads] unresolved_leafs head =", unresolved_leafs[:10])
        print("=" * 110)

    return out_root, in_root, handoff_result

# =============================================================
# MOM demand feasibility / leveling
# =============================================================

def _resolve_product_name_for_capacity(out_root, in_root, product=None):
    """
    capacity lookup 用の product 名を解決する。
    """
    if product:
        return product

    env = getattr(in_root, "_wom_env", None) or getattr(out_root, "_wom_env", None)
    if env is not None:
        return (
            getattr(env, "product", None)
            or getattr(env, "product_selected", None)
            or getattr(out_root, "product_name", None)
            or getattr(in_root, "product_name", None)
        )

    return getattr(out_root, "product_name", None) or getattr(in_root, "product_name", None)


def _resolve_weekly_capacity_series(out_root, in_root, mom, product=None):
    """
    週次 capacity series を返す。
    優先順位:
      1) env.weekly_capability[product][mom_name]
      2) env.weekly_capability[mom_name]
      3) mom.nx_capacity の定数 series
    """
    env = getattr(in_root, "_wom_env", None) or getattr(out_root, "_wom_env", None)
    mom_name = getattr(mom, "name", None)
    psi = getattr(mom, "psi4demand", None) or []
    W = len(psi)

    wc = (getattr(env, "weekly_capability", {}) or {}) if env else {}
    product_name = _resolve_product_name_for_capacity(out_root, in_root, product=product)

    series = None
    if product_name and isinstance(wc.get(product_name, None), dict):
        series = wc.get(product_name, {}).get(mom_name, None)

    if series is None:
        series = wc.get(mom_name, None)

    if isinstance(series, (list, tuple)):
        if len(series) >= W:
            return list(series[:W])
        if len(series) < W:
            pad_val = int(series[-1]) if series else 0
            return list(series) + [pad_val] * (W - len(series))

    cap = int(getattr(mom, "nx_capacity", 0) or 0)
    return [cap] * W


def _lot_market_key_for_capacity(lot):
    """
    lot -> market key の最小版。
    allocate_markets_to_moms(..) と同じ抽出関数を使う。
    """
    return _default_market_key_from_lot(lot)


def level_mom_demand_with_capacity(
    out_root,
    in_root,
    *,
    product: str | None = None,
    weeks: int | None = None,
    overflow_policy: str = "secondary_then_backlog",
    allow_secondary_mom: bool = True,
    secondary_policy: dict | None = None,
    debug: bool = True,
):
    """
    最小 skeleton:
      1) MOM.psi4demand[w][0] の lot を capacity と比較
      2) 超過した lot を secondary MOM に振る
      3) 収まらない分は backlog 扱いにする
      4) 調整済み MOM demand を返す

    NOTE:
      - 現段階では slot0 を調整対象とする
      - early build / 前倒しはまだ実装しない
      - backlog は node に書かず、result に記録する
    """

    mom_nodes = _find_nodes_by_prefix(in_root, "MOM_")
    mom_nodes = sorted(mom_nodes, key=lambda n: getattr(n, "name", ""))

    if not mom_nodes:
        if debug:
            print("[level_mom_demand_with_capacity] no MOM nodes found")
        return out_root, in_root, {
            "week_mom_assigned": {},
            "week_mom_capacity": {},
            "week_mom_overflow": {},
            "lot_to_primary_mom": {},
            "lot_to_final_mom": {},
            "lot_moves_secondary": [],
            "lot_backlogged": [],
            "unresolved_lots": [],
        }

    W = 0
    for mom in mom_nodes:
        psi = getattr(mom, "psi4demand", None) or []
        W = max(W, len(psi))
    if weeks is not None:
        W = min(W, int(weeks))

    # 1) 現在の割当状態を読む
    #    current_assignments[(w, mom_name)] = [lot1, lot2, ...]
    current_assignments = defaultdict(list)
    lot_to_primary_mom = {}

    for mom in mom_nodes:
        psi = getattr(mom, "psi4demand", None) or []
        for w in range(min(W, len(psi))):
            try:
                lots = list(psi[w][0] or [])
            except Exception:
                lots = []
            current_assignments[(w, mom.name)] = lots
            for lot in lots:
                lot_to_primary_mom[str(lot)] = mom.name

    # 2) capacity series を MOM ごとに解決
    mom_capacity = {}
    for mom in mom_nodes:
        mom_capacity[mom.name] = _resolve_weekly_capacity_series(
            out_root, in_root, mom, product=product
        )

    # 3) working copy
    adjusted_assignments = {
        (w, mom.name): list(current_assignments.get((w, mom.name), []))
        for mom in mom_nodes
        for w in range(W)
    }

    lot_to_final_mom = dict(lot_to_primary_mom)
    lot_moves_secondary = []
    lot_backlogged = []
    unresolved_lots = []

    # 4) overflow 処理
    #
    #    初期版:
    #      primary MOM で収まるだけ残す
    #      overflow は secondary MOM を探す
    #      収まらなければ backlog
    #
    for mom in mom_nodes:
        mom_name = mom.name

        for w in range(W):
            lots = adjusted_assignments[(w, mom_name)]
            cap_series = mom_capacity.get(mom_name, [])
            cap_w = int(cap_series[w]) if w < len(cap_series) else 0

            assigned_count = len(lots)
            overflow = max(0, assigned_count - cap_w)
            if overflow <= 0:
                continue

            if debug:
                print(
                    f"[level_mom_demand_with_capacity][overflow] "
                    f"mom={mom_name} w={w} assigned={assigned_count} cap={cap_w} overflow={overflow}"
                )

            keep = lots[:cap_w]
            spill = lots[cap_w:]
            adjusted_assignments[(w, mom_name)] = keep

            for lot in spill:
                lot_str = str(lot)
                moved = False

                if allow_secondary_mom and secondary_policy:
                    market_key = _lot_market_key_for_capacity(lot)
                    mom_candidates = secondary_policy.get(market_key) or secondary_policy.get("DEFAULT") or []

                    for cand_name in mom_candidates:
                        if cand_name == mom_name:
                            continue

                        # secondary MOM が実在するか
                        if cand_name not in mom_capacity:
                            continue

                        cand_lots = adjusted_assignments[(w, cand_name)]
                        cand_cap_series = mom_capacity.get(cand_name, [])
                        cand_cap_w = int(cand_cap_series[w]) if w < len(cand_cap_series) else 0

                        if len(cand_lots) < cand_cap_w:
                            cand_lots.append(lot)
                            adjusted_assignments[(w, cand_name)] = cand_lots
                            lot_to_final_mom[lot_str] = cand_name
                            lot_moves_secondary.append(
                                {
                                    "week": w,
                                    "lot": lot_str,
                                    "from_mom": mom_name,
                                    "to_mom": cand_name,
                                    "reason": "capacity_overflow",
                                }
                            )
                            moved = True

                            if debug:
                                print(
                                    f"[level_mom_demand_with_capacity][secondary] "
                                    f"w={w} lot={lot_str} {mom_name} -> {cand_name}"
                                )
                            break

                if not moved:
                    lot_to_final_mom[lot_str] = None
                    lot_backlogged.append(
                        {
                            "week": w,
                            "lot": lot_str,
                            "from_mom": mom_name,
                            "reason": "capacity_overflow_no_room",
                        }
                    )
                    if debug:
                        print(
                            f"[level_mom_demand_with_capacity][backlog] "
                            f"w={w} lot={lot_str} from_mom={mom_name}"
                        )

    # 5) 調整結果を MOM.psi4demand[w][0] に書き戻す
    for mom in mom_nodes:
        psi = getattr(mom, "psi4demand", None)
        if not isinstance(psi, list):
            continue

        for w in range(min(W, len(psi))):
            psi[w][0] = list(adjusted_assignments.get((w, mom.name), []))

    # 6) 結果集計
    week_mom_assigned = {}
    week_mom_capacity = {}
    week_mom_overflow = {}

    for mom in mom_nodes:
        mom_name = mom.name
        for w in range(W):
            assigned = len(adjusted_assignments[(w, mom_name)])
            cap_w = int(mom_capacity[mom_name][w]) if w < len(mom_capacity[mom_name]) else 0
            overflow = max(0, assigned - cap_w)

            week_mom_assigned[(w, mom_name)] = assigned
            week_mom_capacity[(w, mom_name)] = cap_w
            week_mom_overflow[(w, mom_name)] = overflow

    capacity_result = {
        "week_mom_assigned": week_mom_assigned,
        "week_mom_capacity": week_mom_capacity,
        "week_mom_overflow": week_mom_overflow,
        "lot_to_primary_mom": lot_to_primary_mom,
        "lot_to_final_mom": lot_to_final_mom,
        "lot_moves_secondary": lot_moves_secondary,
        "lot_backlogged": lot_backlogged,
        "unresolved_lots": unresolved_lots,
    }

    if debug:
        print("=" * 110)
        print("[level_mom_demand_with_capacity] moms =", [m.name for m in mom_nodes])

        summary_assigned = defaultdict(int)
        summary_capacity = defaultdict(int)
        for (w, mom_name), cnt in week_mom_assigned.items():
            summary_assigned[mom_name] += cnt
        for (w, mom_name), cnt in week_mom_capacity.items():
            summary_capacity[mom_name] += cnt

        print("[level_mom_demand_with_capacity] assigned_total_by_mom =", dict(summary_assigned))
        print("[level_mom_demand_with_capacity] capacity_total_by_mom =", dict(summary_capacity))
        print("[level_mom_demand_with_capacity] moved_secondary =", len(lot_moves_secondary))
        print("[level_mom_demand_with_capacity] backlogged =", len(lot_backlogged))

        if lot_moves_secondary:
            print("[level_mom_demand_with_capacity] moved_secondary head =", lot_moves_secondary[:10])
        if lot_backlogged:
            print("[level_mom_demand_with_capacity] backlogged head =", lot_backlogged[:10])

        print("=" * 110)

    return out_root, in_root, capacity_result


    # =============================================================
# MOM demand feasibility / leveling
# =============================================================

def _resolve_product_name_for_capacity(out_root, in_root, product=None):
    """
    capacity lookup 用の product 名を解決する。
    優先順位:
      1) 明示引数 product
      2) env.product
      3) env.product_selected
      4) out_root.product_name / in_root.product_name
    """
    if product:
        return product

    env = getattr(in_root, "_wom_env", None) or getattr(out_root, "_wom_env", None)
    if env is not None:
        return (
            getattr(env, "product", None)
            or getattr(env, "product_selected", None)
            or getattr(out_root, "product_name", None)
            or getattr(in_root, "product_name", None)
        )

    return getattr(out_root, "product_name", None) or getattr(in_root, "product_name", None)


def _resolve_weekly_capacity_series(out_root, in_root, mom, product=None):
    """
    週次 capacity series を返す。
    優先順位:
      1) env.weekly_capability[product][mom_name]
      2) env.weekly_capability[mom_name]
      3) mom.nx_capacity の定数 series
    """
    env = getattr(in_root, "_wom_env", None) or getattr(out_root, "_wom_env", None)
    mom_name = getattr(mom, "name", None)
    psi = getattr(mom, "psi4demand", None) or []
    W = len(psi)

    wc = (getattr(env, "weekly_capability", {}) or {}) if env else {}
    product_name = _resolve_product_name_for_capacity(out_root, in_root, product=product)

    series = None

    # 1) product 階層あり: weekly_capability[product][mom_name]
    if product_name and isinstance(wc.get(product_name, None), dict):
        series = wc.get(product_name, {}).get(mom_name, None)

    # 2) 旧形式: weekly_capability[mom_name]
    if series is None:
        series = wc.get(mom_name, None)

    # list / tuple ならそのまま series 化
    if isinstance(series, (list, tuple)):
        if len(series) >= W:
            return list(series[:W])
        if len(series) < W:
            pad_val = int(series[-1]) if series else 0
            return list(series) + [pad_val] * (W - len(series))

    # 3) fallback: nx_capacity を全週に適用
    cap = int(getattr(mom, "nx_capacity", 0) or 0)
    return [cap] * W


def _lot_market_key_for_capacity(lot):
    """
    lot -> market key の最小版。
    allocate_markets_to_moms(..) と同じ抽出関数を使う。
    """
    return _default_market_key_from_lot(lot)


def level_mom_demand_with_capacity(
    out_root,
    in_root,
    *,
    product: str | None = None,
    weeks: int | None = None,
    overflow_policy: str = "secondary_then_backlog",
    allow_secondary_mom: bool = True,
    secondary_policy: dict | None = None,
    debug: bool = True,
):
    """
    MOM ごとの demand lot 配分結果に、週次 capacity 制約を適用する最小 skeleton。

    役割:
      1) MOM.psi4demand[w][0] の lot を capacity と比較
      2) 超過した lot を secondary MOM に振る
      3) 収まらない分は backlog 扱いにする
      4) 調整済み MOM demand を返す

    NOTE:
      - 現段階では slot0 を調整対象とする
      - early build / 前倒しはまだ実装しない
      - backlog は node に書かず、result に記録する
      - overflow_policy は将来拡張用。現段階では
        "secondary_then_backlog" を前提に動く
    """

    mom_nodes = _find_nodes_by_prefix(in_root, "MOM_")
    mom_nodes = sorted(mom_nodes, key=lambda n: getattr(n, "name", ""))

    if not mom_nodes:
        if debug:
            print("[level_mom_demand_with_capacity] no MOM nodes found")
        return out_root, in_root, {
            "week_mom_assigned": {},
            "week_mom_capacity": {},
            "week_mom_overflow": {},
            "lot_to_primary_mom": {},
            "lot_to_final_mom": {},
            "lot_moves_secondary": [],
            "lot_backlogged": [],
            "unresolved_lots": [],
        }

    W = 0
    for mom in mom_nodes:
        psi = getattr(mom, "psi4demand", None) or []
        W = max(W, len(psi))
    if weeks is not None:
        W = min(W, int(weeks))

    product_name = _resolve_product_name_for_capacity(out_root, in_root, product=product)

    # 1) 現在の割当状態を読む
    # current_assignments[(w, mom_name)] = [lot1, lot2, ...]
    current_assignments = defaultdict(list)
    lot_to_primary_mom = {}

    for mom in mom_nodes:
        psi = getattr(mom, "psi4demand", None) or []
        for w in range(min(W, len(psi))):
            try:
                lots = list(psi[w][0] or [])
            except Exception:
                lots = []
            current_assignments[(w, mom.name)] = lots
            for lot in lots:
                lot_to_primary_mom[str(lot)] = mom.name

    # 2) capacity series を MOM ごとに解決
    mom_capacity = {}
    for mom in mom_nodes:
        mom_capacity[mom.name] = _resolve_weekly_capacity_series(
            out_root,
            in_root,
            mom,
            product=product_name,
        )

    # 3) working copy
    adjusted_assignments = {
        (w, mom.name): list(current_assignments.get((w, mom.name), []))
        for mom in mom_nodes
        for w in range(W)
    }

    lot_to_final_mom = dict(lot_to_primary_mom)
    lot_moves_secondary = []
    lot_backlogged = []
    unresolved_lots = []

    # 4) overflow 処理
    # 初期版:
    #   primary MOM に収まるだけ残す
    #   overflow は secondary MOM を探す
    #   収まらなければ backlog
    for mom in mom_nodes:
        mom_name = mom.name

        for w in range(W):
            lots = adjusted_assignments[(w, mom_name)]
            cap_series = mom_capacity.get(mom_name, [])
            cap_w = int(cap_series[w]) if w < len(cap_series) else 0

            assigned_count = len(lots)
            overflow = max(0, assigned_count - cap_w)

            if overflow <= 0:
                continue

            if debug:
                print(
                    f"[level_mom_demand_with_capacity][overflow] "
                    f"mom={mom_name} w={w} assigned={assigned_count} cap={cap_w} overflow={overflow}"
                )

            keep = lots[:cap_w]
            spill = lots[cap_w:]
            adjusted_assignments[(w, mom_name)] = keep

            for lot in spill:
                lot_str = str(lot)
                moved = False

                if allow_secondary_mom and secondary_policy and overflow_policy == "secondary_then_backlog":
                    market_key = _lot_market_key_for_capacity(lot)
                    mom_candidates = secondary_policy.get(market_key) or secondary_policy.get("DEFAULT") or []

                    for cand_name in mom_candidates:
                        if cand_name == mom_name:
                            continue
                        if cand_name not in mom_capacity:
                            continue

                        cand_lots = adjusted_assignments[(w, cand_name)]
                        cand_cap_series = mom_capacity.get(cand_name, [])
                        cand_cap_w = int(cand_cap_series[w]) if w < len(cand_cap_series) else 0

                        if len(cand_lots) < cand_cap_w:
                            cand_lots.append(lot)
                            adjusted_assignments[(w, cand_name)] = cand_lots
                            lot_to_final_mom[lot_str] = cand_name
                            lot_moves_secondary.append(
                                {
                                    "week": w,
                                    "lot": lot_str,
                                    "from_mom": mom_name,
                                    "to_mom": cand_name,
                                    "reason": "capacity_overflow",
                                }
                            )
                            moved = True

                            if debug:
                                print(
                                    f"[level_mom_demand_with_capacity][secondary] "
                                    f"w={w} lot={lot_str} {mom_name} -> {cand_name}"
                                )
                            break

                if not moved:
                    lot_to_final_mom[lot_str] = None
                    lot_backlogged.append(
                        {
                            "week": w,
                            "lot": lot_str,
                            "from_mom": mom_name,
                            "reason": "capacity_overflow_no_room",
                        }
                    )
                    if debug:
                        print(
                            f"[level_mom_demand_with_capacity][backlog] "
                            f"w={w} lot={lot_str} from_mom={mom_name}"
                        )

    # 5) 調整結果を MOM.psi4demand[w][0] に書き戻す
    for mom in mom_nodes:
        psi = getattr(mom, "psi4demand", None)
        if not isinstance(psi, list):
            continue

        for w in range(min(W, len(psi))):
            psi[w][0] = list(adjusted_assignments.get((w, mom.name), []))

    # 6) 結果集計
    week_mom_assigned = {}
    week_mom_capacity = {}
    week_mom_overflow = {}

    for mom in mom_nodes:
        mom_name = mom.name
        for w in range(W):
            assigned = len(adjusted_assignments[(w, mom_name)])
            cap_w = int(mom_capacity[mom_name][w]) if w < len(mom_capacity[mom_name]) else 0
            overflow = max(0, assigned - cap_w)

            week_mom_assigned[(w, mom_name)] = assigned
            week_mom_capacity[(w, mom_name)] = cap_w
            week_mom_overflow[(w, mom_name)] = overflow

    capacity_result = {
        "week_mom_assigned": week_mom_assigned,
        "week_mom_capacity": week_mom_capacity,
        "week_mom_overflow": week_mom_overflow,
        "lot_to_primary_mom": lot_to_primary_mom,
        "lot_to_final_mom": lot_to_final_mom,
        "lot_moves_secondary": lot_moves_secondary,
        "lot_backlogged": lot_backlogged,
        "unresolved_lots": unresolved_lots,
    }

    if debug:
        print("=" * 110)
        print("[level_mom_demand_with_capacity] product =", product_name)
        print("[level_mom_demand_with_capacity] moms =", [m.name for m in mom_nodes])

        summary_assigned = defaultdict(int)
        summary_capacity = defaultdict(int)

        for (w, mom_name), cnt in week_mom_assigned.items():
            summary_assigned[mom_name] += cnt

        for (w, mom_name), cnt in week_mom_capacity.items():
            summary_capacity[mom_name] += cnt

        print("[level_mom_demand_with_capacity] assigned_total_by_mom =", dict(summary_assigned))
        print("[level_mom_demand_with_capacity] capacity_total_by_mom =", dict(summary_capacity))
        print(
            "[level_mom_demand_with_capacity] weekly_capacity_head =",
            {m.name: mom_capacity.get(m.name, [])[:8] for m in mom_nodes}
        )
        print("[level_mom_demand_with_capacity] moved_secondary =", len(lot_moves_secondary))
        print("[level_mom_demand_with_capacity] backlogged =", len(lot_backlogged))

        if lot_moves_secondary:
            print("[level_mom_demand_with_capacity] moved_secondary head =", lot_moves_secondary[:10])
        if lot_backlogged:
            print("[level_mom_demand_with_capacity] backlogged head =", lot_backlogged[:10])

        print("=" * 110)

    return out_root, in_root, capacity_result