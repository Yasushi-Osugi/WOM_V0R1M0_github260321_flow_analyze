# pysi/gui/business_animation/business_animation_panel.py

# これは最小の起動パネルです。
# 左に network、右に KPI、上に control を置きます。
# cockpit_tk.py から set_context(ctx) で実データを受け取れる統合版です。

from __future__ import annotations

import json
import tkinter as tk
from dataclasses import asdict, is_dataclass
from pathlib import Path
from tkinter import ttk

from .animation_controller import AnimationController
from .context_models import BusinessAnimationContext
from .network_anim_view import NetworkAnimView
from .replay_builder import build_dummy_snapshots
from .replay_models import (
    EdgeWeeklyMetrics,
    TotalWeeklyMetrics,
    WeeklyReplaySnapshot,
    NodeWeeklyMetrics,
)


class BusinessAnimationPanel(tk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.pack(fill="both", expand=True)

        # standalone demo 用の初期トポロジー
        self.node_positions = {
            "MOM_ASIA": (120, 240),
            "DAD_APAC": (260, 240),
            "DAD_EURO": (420, 180),
            "DAD_AMER": (420, 310),
            "WS_EU": (580, 180),
            "WS_NA": (580, 310),
            "CS_DE": (760, 160),
            "CS_US": (760, 330),
        }
        self.edges = [
            ("MOM_ASIA", "DAD_APAC"),
            ("DAD_APAC", "DAD_EURO"),
            ("DAD_APAC", "DAD_AMER"),
            ("DAD_EURO", "WS_EU"),
            ("DAD_AMER", "WS_NA"),
            ("WS_EU", "CS_DE"),
            ("WS_NA", "CS_US"),
        ]

        # standalone demo 用のダミー snapshot
        self.snapshots: list[WeeklyReplaySnapshot] = build_dummy_snapshots(
            node_ids=list(self.node_positions.keys()),
            edges=self.edges,
            weeks=24,
        )

        # cockpit からの current context
        self.ctx: BusinessAnimationContext | None = None

        self._build_ui()

        self.controller = AnimationController(
            master=self,
            snapshots=self.snapshots,
            on_frame_changed=self._on_frame_changed,
        )
        self.controller.render_current()

    def _build_ui(self) -> None:
        top = tk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)

        ttk.Button(top, text="Play", command=self._on_play).pack(side="left", padx=4)
        ttk.Button(top, text="Pause", command=self._on_pause).pack(side="left", padx=4)
        ttk.Button(top, text="Stop", command=self._on_stop).pack(side="left", padx=4)
        ttk.Button(top, text="<<", command=self._on_back).pack(side="left", padx=4)
        ttk.Button(top, text=">>", command=self._on_forward).pack(side="left", padx=4)

        ttk.Label(top, text="Mode").pack(side="left", padx=(16, 4))
        self.mode_var = tk.StringVar(value="profit")
        mode_combo = ttk.Combobox(
            top,
            textvariable=self.mode_var,
            values=["profit", "revenue", "inventory"],
            width=12,
            state="readonly",
        )
        mode_combo.pack(side="left")
        mode_combo.bind("<<ComboboxSelected>>", self._on_mode_changed)

        ttk.Label(top, text="Speed").pack(side="left", padx=(16, 4))
        self.speed_var = tk.StringVar(value="1.0")
        speed_combo = ttk.Combobox(
            top,
            textvariable=self.speed_var,
            values=["0.5", "1.0", "2.0", "4.0"],
            width=8,
            state="readonly",
        )
        speed_combo.pack(side="left")
        speed_combo.bind("<<ComboboxSelected>>", self._on_speed_changed)

        body = tk.PanedWindow(self, sashrelief="raised", sashwidth=6)
        body.pack(fill="both", expand=True)

        left = tk.Frame(body)
        right = tk.Frame(body, width=280)

        body.add(left, stretch="always")
        body.add(right)

        self.network_view = NetworkAnimView(
            left,
            node_positions=self.node_positions,
            edges=self.edges,
            on_node_selected=self._on_node_selected,
        )
        self.network_view.pack(fill="both", expand=True)

        self.week_var = tk.StringVar(value="Week: -")
        self.total_var = tk.StringVar(value="Total KPI: -")
        self.node_var = tk.StringVar(value="Selected Node: -")
        self.node_kpi_var = tk.StringVar(
            value="Revenue: -\nCost: -\nProfit: -\nInventory: -"
        )

        ttk.Label(
            right, text="Business Animation", font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=8, pady=(10, 8))
        ttk.Label(right, textvariable=self.week_var).pack(
            anchor="w", padx=8, pady=4
        )
        ttk.Label(right, textvariable=self.total_var, justify="left").pack(
            anchor="w", padx=8, pady=4
        )
        ttk.Separator(right, orient="horizontal").pack(fill="x", padx=8, pady=8)
        ttk.Label(right, textvariable=self.node_var).pack(
            anchor="w", padx=8, pady=4
        )
        ttk.Label(right, textvariable=self.node_kpi_var, justify="left").pack(
            anchor="w", padx=8, pady=4
        )

    def _on_play(self) -> None:
        self.controller.play()

    def _on_pause(self) -> None:
        self.controller.pause()

    def _on_stop(self) -> None:
        self.controller.stop()

    def _on_back(self) -> None:
        self.controller.step_backward()

    def _on_forward(self) -> None:
        self.controller.step_forward()

    def _on_mode_changed(self, _event=None) -> None:
        self.controller.set_mode(self.mode_var.get())

    def _on_speed_changed(self, _event=None) -> None:
        self.controller.set_speed(float(self.speed_var.get()))

    def _on_node_selected(self, node_id: str) -> None:
        self.controller.set_selected_node(node_id)

    def _on_frame_changed(self, snapshot: WeeklyReplaySnapshot, state) -> None:
        self.network_view.render_snapshot(snapshot, state)

        self.week_var.set(f"Week: {snapshot.week_no}")
        self.total_var.set(
            "\n".join(
                [
                    f"Total Revenue: {snapshot.total_metrics.revenue:,.0f}",
                    f"Total Cost:    {snapshot.total_metrics.cost:,.0f}",
                    f"Total Profit:  {snapshot.total_metrics.profit:,.0f}",
                    f"Total Inv:     {snapshot.total_metrics.inventory:,.0f}",
                ]
            )
        )

        node_id = state.selected_node_id
        if node_id and node_id in snapshot.node_metrics:
            nm = snapshot.node_metrics[node_id]
            self.node_var.set(f"Selected Node: {node_id}")
            self.node_kpi_var.set(
                "\n".join(
                    [
                        f"Revenue:   {nm.revenue:,.0f}",
                        f"Cost:      {nm.cost:,.0f}",
                        f"Profit:    {nm.profit:,.0f}",
                        f"Inventory: {nm.inventory:,.0f}",
                        f"Cash In:   {nm.cash_in:,.0f}",
                        f"Cash Out:  {nm.cash_out:,.0f}",
                    ]
                )
            )
        else:
            self.node_var.set("Selected Node: -")
            self.node_kpi_var.set("Revenue: -\nCost: -\nProfit: -\nInventory: -")

    # ------------------------------------------------------------------
    # cockpit integration public APIs
    # ------------------------------------------------------------------
    def set_context(self, ctx: BusinessAnimationContext) -> None:
        """
        Receive context from cockpit_tk.py and rebuild animation snapshots.

        Minimal v0.1 policy:
        - keep current panel/controller structure
        - replace dummy snapshots with context-derived snapshots
        - sync selected node from cockpit
        """
        self.ctx = ctx

        try:
            self.node_positions = self._build_node_positions_from_context(ctx)
        except Exception as e:
            print(f"[business_animation] node position build failed: {e}")

        try:
            self.edges = self._normalize_edges(getattr(ctx, "edges", None))
        except Exception as e:
            print(f"[business_animation] edge normalization failed: {e}")

        try:
            self.snapshots = self._build_snapshots_from_context(ctx)
        except Exception as e:
            print(f"[business_animation] snapshot build failed: {e}")
            self.snapshots = []

        try:
            #@STOP
            #self.network_view.node_positions = self.node_positions
            #self.network_view.edges = self.edges
            #@UPDATE
            if hasattr(self.network_view, "rebuild_topology"):
                self.network_view.rebuild_topology(self.node_positions, self.edges)
            else:
                self.network_view.node_positions = self.node_positions
                self.network_view.edges = self.edges
        except Exception as e:
            print(f"[business_animation] network_view topology refresh failed: {e}")




        try:
            self.controller.snapshots = self.snapshots
            self.controller.state.current_index = 0
            self.controller.state.selected_node_id = getattr(ctx, "selected_node", None)
            self.controller.render_current()
        except Exception as e:
            print(f"[business_animation] controller refresh failed: {e}")

    def update_selection(self, node_id: str) -> None:
        """
        Sync selected node from cockpit -> business animation.
        """
        try:
            self.controller.set_selected_node(node_id)
        except Exception as e:
            print(f"[business_animation] update_selection failed: {e}")

    # ------------------------------------------------------------------
    # snapshot building
    # ------------------------------------------------------------------
    def _build_snapshots_from_context(
        self, ctx: BusinessAnimationContext
    ) -> list[WeeklyReplaySnapshot]:
        """
        Build snapshots aligned to replay_models.py / current panel expectations.

        Expected snapshot shape:
          snapshot.week_no
          snapshot.total_metrics.{revenue,cost,profit,inventory}
          snapshot.node_metrics[node_id].{revenue,cost,profit,inventory,cash_in,cash_out}
          snapshot.edge_metrics[(from_node, to_node)].{shipment_count,pulse_strength}
        """
        weeks = self._extract_weeks_from_context(ctx)
        edges = self._normalize_edges(getattr(ctx, "edges", None))
        cash_rows = self._coerce_cashflow_rows(getattr(ctx, "cashflow_df", None))
        trace_events = self._coerce_trace_events(getattr(ctx, "trace_events", None))
        bridge_payload = getattr(ctx, "bridge_payload", None)
        node_ids = self._extract_node_ids_from_context(ctx, edges)

        weekly_totals = self._build_weekly_totals_from_cash_rows(cash_rows, weeks)
        weekly_node_metrics = self._build_weekly_node_metrics_from_cash_rows(
            cash_rows=cash_rows,
            weeks=weeks,
            node_ids=node_ids,
        )
        weekly_edge_metrics = self._build_weekly_edge_metrics(
            weeks=weeks,
            edges=edges,
            trace_events=trace_events,
            bridge_payload=bridge_payload,
        )

        snapshots: list[WeeklyReplaySnapshot] = []

        for w in weeks:
            totals_raw = weekly_totals.get(
                w,
                {"revenue": 0.0, "cost": 0.0, "profit": 0.0, "inventory": 0.0},
            )
            total_metrics = TotalWeeklyMetrics(
                revenue=float(totals_raw.get("revenue", 0.0) or 0.0),
                cost=float(totals_raw.get("cost", 0.0) or 0.0),
                profit=float(totals_raw.get("profit", 0.0) or 0.0),
                inventory=float(totals_raw.get("inventory", 0.0) or 0.0),
                cash_in=float(totals_raw.get("revenue", 0.0) or 0.0),
                cash_out=float(totals_raw.get("cost", 0.0) or 0.0),
            )

            node_metrics: dict[str, NodeWeeklyMetrics] = {}
            raw_nodes = weekly_node_metrics.get(w, {})
            for node_id in node_ids:
                nm = raw_nodes.get(node_id, {})
                node_metrics[node_id] = NodeWeeklyMetrics(
                    node_id=node_id,
                    revenue=float(nm.get("revenue", 0.0) or 0.0),
                    cost=float(nm.get("cost", 0.0) or 0.0),
                    profit=float(nm.get("profit", 0.0) or 0.0),
                    inventory=float(nm.get("inventory", 0.0) or 0.0),
                    cash_in=float(nm.get("cash_in", 0.0) or 0.0),
                    cash_out=float(nm.get("cash_out", 0.0) or 0.0),
                )

            edge_metrics = weekly_edge_metrics.get(w, {})

            snapshots.append(
                WeeklyReplaySnapshot(
                    week_no=int(w),
                    node_metrics=node_metrics,
                    edge_metrics=edge_metrics,
                    total_metrics=total_metrics,
                    active_events=[],
                )
            )

        if not snapshots:
            node_metrics = {
                nid: NodeWeeklyMetrics(node_id=nid)
                for nid in node_ids
            }
            snapshots = [
                WeeklyReplaySnapshot(
                    week_no=1,
                    node_metrics=node_metrics,
                    edge_metrics={},
                    total_metrics=TotalWeeklyMetrics(),
                    active_events=[],
                )
            ]

        return snapshots

    # ------------------------------------------------------------------
    # helpers: topology / extraction
    # ------------------------------------------------------------------



    def _build_node_positions_from_context(self, ctx: BusinessAnimationContext):
        """
        Build canvas-safe node positions.

        Priority:
        1. metadata["node_positions"] if present
           - but normalize into canvas pixel coordinates if they look like logical coords
        2. derive layered layout from edges
        3. fallback to current self.node_positions
        """
        meta = getattr(ctx, "metadata", None) or {}
        explicit = meta.get("node_positions")

        if isinstance(explicit, dict) and explicit:
            # normalize tuple/dict style
            raw = {}
            for nid, pos in explicit.items():
                if isinstance(pos, dict):
                    x = float(pos.get("x", 0.0))
                    y = float(pos.get("y", 0.0))
                else:
                    x, y = pos
                    x = float(x)
                    y = float(y)
                raw[str(nid)] = (x, y)

            # detect logical / normalized coordinates
            xs = [p[0] for p in raw.values()]
            ys = [p[1] for p in raw.values()]
            max_abs_x = max(abs(v) for v in xs) if xs else 0.0
            max_abs_y = max(abs(v) for v in ys) if ys else 0.0

            # If coordinates are too small, treat them as logical coords and scale them.
            # Example: 0..5 / -1..1 style positions from merged layout.
            if max_abs_x <= 20 and max_abs_y <= 20:

                #@STOP
                #left_pad = 140
                #top_pad = 280
                #x_scale = 170
                #y_scale = 160

                left_pad = 140
                top_pad = 280
                x_scale = 170
                y_scale = 160

                min_x = min(xs) if xs else 0.0
                min_y = min(ys) if ys else 0.0

                scaled = {}
                for nid, (x, y) in raw.items():
                    px = int(left_pad + (x - min_x) * x_scale)
                    py = int(top_pad + (y - min_y) * y_scale)
                    scaled[nid] = (px, py)
                return scaled

            # otherwise assume already pixel-ish
            return {nid: (int(x), int(y)) for nid, (x, y) in raw.items()}

        edges = self._normalize_edges(getattr(ctx, "edges", None))
        node_ids = self._extract_node_ids_from_context(ctx, edges)

        if not node_ids:
            return self.node_positions

        children = {}
        parents = {}
        for src, dst in edges:
            children.setdefault(src, []).append(dst)
            parents[dst] = src
            children.setdefault(dst, [])

        roots = [n for n in node_ids if n not in parents]
        if not roots:
            roots = [node_ids[0]]

        levels = {}
        queue = []
        for r in roots:
            levels[r] = 0
            queue.append(r)

        i = 0
        while i < len(queue):
            cur = queue[i]
            i += 1
            for ch in children.get(cur, []):
                if ch not in levels:
                    levels[ch] = levels[cur] + 1
                    queue.append(ch)

        for n in node_ids:
            levels.setdefault(n, 0)

        grouped = {}
        for n, lv in levels.items():
            grouped.setdefault(lv, []).append(n)

        positions = {}
        x_gap = 190
        y_gap = 150
        left_pad = 120
        top_pad = 260

        for lv in sorted(grouped.keys()):
            row = sorted(grouped[lv])
            count = len(row)
            for idx, nid in enumerate(row):
                x = int(left_pad + lv * x_gap)
                y = int(top_pad + (idx - (count - 1) / 2.0) * y_gap)
                positions[nid] = (x, y)

        return positions


    def _extract_weeks_from_context(self, ctx: BusinessAnimationContext) -> list[int]:
        weeks = set()

        cash_rows = self._coerce_cashflow_rows(getattr(ctx, "cashflow_df", None))
        for r in cash_rows:
            w = self._pick_week_value(r)
            if w is not None:
                weeks.add(w)

        trace_events = self._coerce_trace_events(getattr(ctx, "trace_events", None))
        for ev in trace_events:
            w = self._pick_week_value(ev)
            if w is not None:
                weeks.add(w)

        bridge = getattr(ctx, "bridge_payload", None)
        if isinstance(bridge, dict):
            for key in ("weeks", "time_buckets"):
                arr = bridge.get(key)
                if isinstance(arr, list):
                    for v in arr:
                        try:
                            weeks.add(int(v))
                        except Exception:
                            pass

        if not weeks:
            return [1]

        return sorted(weeks)

    def _extract_node_ids_from_context(
        self, ctx: BusinessAnimationContext, edges: list[tuple[str, str]]
    ) -> list[str]:
        node_ids = set()

        node_dict = getattr(ctx, "node_dict", None)
        if isinstance(node_dict, dict):
            for k in node_dict.keys():
                if k:
                    node_ids.add(str(k))

        for src, dst in edges:
            if src:
                node_ids.add(str(src))
            if dst:
                node_ids.add(str(dst))

        root_node = getattr(ctx, "root_node", None)
        if root_node is not None:
            try:
                if hasattr(root_node, "get_all_nodes"):
                    for n in root_node.get_all_nodes():
                        name = getattr(n, "name", None)
                        if name:
                            node_ids.add(str(name))
                else:
                    name = getattr(root_node, "name", None)
                    if name:
                        node_ids.add(str(name))
            except Exception:
                pass

        return sorted(node_ids)

    def _normalize_edges(self, edges) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        if not edges:
            return out

        for e in edges:
            if isinstance(e, (list, tuple)) and len(e) >= 2:
                out.append((str(e[0]), str(e[1])))
            elif isinstance(e, dict):
                src = e.get("from") or e.get("src") or e.get("source") or e.get(
                    "parent"
                )
                dst = e.get("to") or e.get("dst") or e.get("target") or e.get("child")
                if src and dst:
                    out.append((str(src), str(dst)))
        return out

    # ------------------------------------------------------------------
    # helpers: coercion / picking
    # ------------------------------------------------------------------
    def _coerce_cashflow_rows(self, cashflow_df):
        if cashflow_df is None:
            return []

        try:
            if hasattr(cashflow_df, "to_dict"):
                return cashflow_df.to_dict(orient="records")
        except Exception:
            pass

        if isinstance(cashflow_df, list):
            return [r for r in cashflow_df if isinstance(r, dict)]

        return []

    def _coerce_trace_events(self, trace_events):
        if trace_events is None:
            return []
        if isinstance(trace_events, list):
            return [e for e in trace_events if isinstance(e, dict)]
        return []

    def _pick_week_value(self, row):
        for k in ("week", "week_no", "time_bucket", "timebucket"):
            if isinstance(row, dict) and row.get(k) is not None:
                try:
                    return int(row.get(k))
                except Exception:
                    pass
        return None

    def _pick_metric_value(self, row, candidates, default=0.0):
        for k in candidates:
            if isinstance(row, dict) and row.get(k) is not None:
                try:
                    return float(row.get(k))
                except Exception:
                    pass
        return float(default)

    def _pick_node_value(self, row):
        for k in ("node_id", "node_name", "from_node", "to_node"):
            if isinstance(row, dict) and row.get(k):
                return str(row.get(k))
        return None

    # ------------------------------------------------------------------
    # helpers: metric builders
    # ------------------------------------------------------------------
    def _build_weekly_totals_from_cash_rows(
        self, cash_rows, weeks: list[int]
    ) -> dict[int, dict[str, float]]:
        totals = {
            w: {"revenue": 0.0, "cost": 0.0, "profit": 0.0, "inventory": 0.0}
            for w in weeks
        }

        for r in cash_rows:
            w = self._pick_week_value(r)
            if w is None or w not in totals:
                continue

            revenue = self._pick_metric_value(
                r, ["revenue", "sales", "sales_amount", "total_revenue"], 0.0
            )
            cost = self._pick_metric_value(r, ["cost", "total_cost", "expense"], 0.0)
            profit = self._pick_metric_value(
                r, ["profit", "margin", "total_profit"], revenue - cost
            )
            inventory = self._pick_metric_value(
                r, ["inventory", "inventory_value", "inv", "ending_inventory"], 0.0
            )

            totals[w]["revenue"] += revenue
            totals[w]["cost"] += cost
            totals[w]["profit"] += profit
            totals[w]["inventory"] += inventory

        return totals

    def _build_weekly_node_metrics_from_cash_rows(
        self, cash_rows, weeks: list[int], node_ids: list[str]
    ) -> dict[int, dict[str, dict[str, float]]]:
        weekly_nodes = {
            w: {
                nid: {
                    "revenue": 0.0,
                    "cost": 0.0,
                    "profit": 0.0,
                    "inventory": 0.0,
                    "cash_in": 0.0,
                    "cash_out": 0.0,
                }
                for nid in node_ids
            }
            for w in weeks
        }

        for r in cash_rows:
            w = self._pick_week_value(r)
            nid = self._pick_node_value(r)
            if w is None or w not in weekly_nodes or not nid or nid not in weekly_nodes[w]:
                continue

            revenue = self._pick_metric_value(
                r, ["revenue", "sales", "sales_amount", "total_revenue"], 0.0
            )
            cost = self._pick_metric_value(r, ["cost", "total_cost", "expense"], 0.0)
            profit = self._pick_metric_value(
                r, ["profit", "margin", "total_profit"], revenue - cost
            )
            inventory = self._pick_metric_value(
                r, ["inventory", "inventory_value", "inv", "ending_inventory"], 0.0
            )
            cash_in = self._pick_metric_value(r, ["cash_in", "inflow", "cashin"], revenue)
            cash_out = self._pick_metric_value(r, ["cash_out", "outflow", "cashout"], cost)

            weekly_nodes[w][nid]["revenue"] += revenue
            weekly_nodes[w][nid]["cost"] += cost
            weekly_nodes[w][nid]["profit"] += profit
            weekly_nodes[w][nid]["inventory"] += inventory
            weekly_nodes[w][nid]["cash_in"] += cash_in
            weekly_nodes[w][nid]["cash_out"] += cash_out

        return weekly_nodes

    def _build_weekly_edge_metrics(
        self,
        weeks: list[int],
        edges: list[tuple[str, str]],
        trace_events,
        bridge_payload,
    ) -> dict[int, dict[tuple[str, str], EdgeWeeklyMetrics]]:
        """
        Build week -> edge_metrics dict aligned to NetworkAnimView expectations.

        Shape:
          {
            week_no: {
              (from_node, to_node): EdgeWeeklyMetrics(
                  from_node=...,
                  to_node=...,
                  shipment_count=...,
                  pulse_strength=...
              ),
              ...
            }
          }
        """
        weekly_edge_metrics = {
            w: {
                (str(a), str(b)): EdgeWeeklyMetrics(
                    from_node=str(a),
                    to_node=str(b),
                    shipped_qty=0.0,
                    shipment_count=0,
                    pulse_strength=0.0,
                )
                for a, b in edges
            }
            for w in weeks
        }

        for ev in trace_events:
            w = self._pick_week_value(ev)
            if w is None or w not in weekly_edge_metrics:
                continue

            from_node = (
                ev.get("from_node")
                or ev.get("from_node_id")
                or ev.get("src")
                or ev.get("source")
            )
            to_node = (
                ev.get("to_node")
                or ev.get("to_node_id")
                or ev.get("dst")
                or ev.get("target")
            )

            if not from_node or not to_node:
                payload = ev.get("payload")
                if isinstance(payload, dict):
                    from_node = from_node or payload.get("from_node_id") or payload.get(
                        "from_node"
                    )
                    to_node = to_node or payload.get("to_node_id") or payload.get(
                        "to_node"
                    )

            if not from_node or not to_node:
                continue

            edge = (str(from_node), str(to_node))
            if edge not in weekly_edge_metrics[w]:
                continue

            em = weekly_edge_metrics[w][edge]
            em.shipment_count += 1
            em.pulse_strength = min(1.0, em.pulse_strength + 0.35)

            magnitude = self._pick_metric_value(
                ev,
                ["magnitude", "qty", "quantity", "shipped_qty"],
                0.0,
            )
            em.shipped_qty += magnitude

        if isinstance(bridge_payload, dict):
            bridge_events = bridge_payload.get("events") or bridge_payload.get(
                "edge_pulses"
            ) or []
            if isinstance(bridge_events, list):
                for ev in bridge_events:
                    if not isinstance(ev, dict):
                        continue

                    w = self._pick_week_value(ev)
                    if w is None or w not in weekly_edge_metrics:
                        continue

                    from_node = ev.get("from") or ev.get("from_node") or ev.get("src")
                    to_node = ev.get("to") or ev.get("to_node") or ev.get("dst")
                    if not from_node or not to_node:
                        continue

                    edge = (str(from_node), str(to_node))
                    if edge not in weekly_edge_metrics[w]:
                        continue

                    em = weekly_edge_metrics[w][edge]
                    em.shipment_count += int(ev.get("shipment_count", 1) or 1)
                    em.pulse_strength = max(
                        em.pulse_strength,
                        float(ev.get("strength", 1.0) or 1.0),
                    )
                    em.shipped_qty += float(ev.get("shipped_qty", 0.0) or 0.0)

        return weekly_edge_metrics

    # ------------------------------------------------------------------
    # debug utility
    # ------------------------------------------------------------------
    def debug_dump_snapshots(self, output_path=None, max_frames=5):
        def _to_jsonable(obj):
            if is_dataclass(obj):
                return {k: _to_jsonable(v) for k, v in asdict(obj).items()}
            if isinstance(obj, dict):
                return {str(k): _to_jsonable(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_to_jsonable(v) for v in obj]
            if isinstance(obj, tuple):
                return [_to_jsonable(v) for v in obj]
            return obj

        snapshots = getattr(self, "snapshots", None) or []
        preview = snapshots[:max_frames]

        payload = {
            "schema_version": "business_animation_snapshot_replay_models_v0_1",
            "frame_count": len(snapshots),
            "preview_count": len(preview),
            "preview": _to_jsonable(preview),
            "all_frames": _to_jsonable(snapshots),
        }

        if output_path is None:
            output_path = Path("outputs") / "business_animation_snapshot_dump.json"
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"[business_animation] snapshot dump written: {output_path}")
        return str(output_path)
