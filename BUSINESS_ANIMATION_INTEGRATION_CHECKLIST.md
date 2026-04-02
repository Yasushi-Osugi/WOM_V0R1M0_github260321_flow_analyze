# BUSINESS_ANIMATION_INTEGRATION_CHECKLIST

## 1. 目的

このチェックリストは、latest の `pysi/gui/cockpit_tk.py` に対して  
**Business Performance Animation v0.1** を安全に統合するための実装手順を、  
**ファイルの上から順に** 整理したものです。 

狙いは次の3点です。

- `cockpit_tk.py` の現在の選択状態（product / direction / selected node）を、Business Animation へ渡す
- `df_cash`、`trace_event_sink`、`last_bridge_payload` を animation 側へ流し込む
- node 選択と refresh に追随する **別 Toplevel viewer** として Business Animation を起動する

この統合は、既存の

- `Animation Viewer`
- `Trace Viewer`
- `World Map`
- `Network`

を壊さず、**Business KPI replay 専用の可視化窓を追加する** 方針です。 

---

## 2. 事前前提

Business Animation 側に最低限、以下のファイルが存在することを前提とします。

```text
pysi/gui/business_animation/
    __init__.py
    context_models.py
    replay_models.py
    animation_controller.py
    network_anim_view.py
    business_animation_panel.py