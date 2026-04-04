#pysi/gui/business_animation/network_anim_view.py

#ここは 固定座標の network canvas です。
#毎フレーム再レイアウトしないので軽いです。

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont

from .replay_models import ReplayState, WeeklyReplaySnapshot


class NetworkAnimView(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        node_positions: dict[str, tuple[int, int]],
        edges: list[tuple[str, str]],
        on_node_selected=None,
    ) -> None:
        super().__init__(master)

        self.node_positions = node_positions
        self.edges = edges
        self.on_node_selected = on_node_selected

        self.canvas = tk.Canvas(self, width=900, height=520, bg="white")
        self.canvas.pack(fill="both", expand=True)

        self._node_circle_ids: dict[str, int] = {}
        self._node_label_ids: dict[str, int] = {}
        self._edge_line_ids: dict[tuple[str, str], int] = {}

        self._build_static_scene()


    def rebuild_topology(
        self,
        node_positions: dict[str, tuple[int, int]],
        edges: list[tuple[str, str]],
    ) -> None:
        self.node_positions = node_positions
        self.edges = edges

        self.canvas.delete("all")
        self._node_circle_ids.clear()
        self._node_label_ids.clear()
        self._edge_line_ids.clear()

        self._build_static_scene()


    def _build_static_scene(self) -> None:
        # edges
        for edge in self.edges:
            src, dst = edge
            x1, y1 = self.node_positions[src]
            x2, y2 = self.node_positions[dst]
            line_id = self.canvas.create_line(x1, y1, x2, y2, width=2, fill="#9aa5b1")
            self._edge_line_ids[edge] = line_id

        # nodes
        for node_id, (x, y) in self.node_positions.items():
            r = 18
            oval_id = self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="#d9e2ec", outline="#486581", width=2)
            label_id = self.canvas.create_text(x, y + 36, text=node_id, font=("Arial", 9))

            self._node_circle_ids[node_id] = oval_id
            self._node_label_ids[node_id] = label_id

            self.canvas.tag_bind(oval_id, "<Button-1>", lambda e, nid=node_id: self._handle_node_click(nid))
            self.canvas.tag_bind(label_id, "<Button-1>", lambda e, nid=node_id: self._handle_node_click(nid))

    def _handle_node_click(self, node_id: str) -> None:
        if self.on_node_selected:
            self.on_node_selected(node_id)

    def render_snapshot(self, snapshot: WeeklyReplaySnapshot, state: ReplayState) -> None:
        self._render_edges(snapshot)
        self._render_nodes(snapshot, state)

    def _render_edges(self, snapshot: WeeklyReplaySnapshot) -> None:
        for edge, line_id in self._edge_line_ids.items():
            em = snapshot.edge_metrics.get(edge)
            if em and em.shipment_count > 0:
                width = 2 + int(4 * em.pulse_strength)
                fill = "#3b82f6"
            else:
                width = 2
                fill = "#9aa5b1"

            self.canvas.itemconfigure(line_id, width=width, fill=fill)

    def _render_nodes(self, snapshot: WeeklyReplaySnapshot, state: ReplayState) -> None:
        for node_id, oval_id in self._node_circle_ids.items():
            nm = snapshot.node_metrics.get(node_id)
            if nm is None:
                continue

            x, y = self.node_positions[node_id]
            radius = self._calc_radius(nm, state.mode)
            fill = self._calc_fill(nm, state.mode)
            outline, outline_w = self._calc_outline(nm, node_id, state)

            self.canvas.coords(oval_id, x - radius, y - radius, x + radius, y + radius)
            self.canvas.itemconfigure(oval_id, fill=fill, outline=outline, width=outline_w)

            mode = getattr(state, "mode", "profit")
            if mode == "revenue":
                metric_value = getattr(nm, "revenue", 0.0)
                metric_tag = "Rev"
            elif mode == "inventory":
                metric_value = getattr(nm, "inventory", 0.0)
                metric_tag = "Inv"
            else:
                metric_value = getattr(nm, "profit", 0.0)
                metric_tag = "Pft"

            if abs(metric_value) >= 1_000_000:
                shown = f"{metric_value/1_000_000:.1f}M"
            else:
                shown = f"{metric_value:,.0f}"

            short_text = f"{node_id}\n{metric_tag}:{shown}"
            self.canvas.itemconfigure(self._node_label_ids[node_id], text=short_text)

    def _calc_radius(self, nm, mode: str) -> int:
        if mode == "revenue":
            base = nm.revenue
        elif mode == "inventory":
            base = nm.inventory * 200.0
        else:
            base = max(0.0, nm.profit + 500000.0)

        r = 14 + int(min(22, base / 300000.0))
        return max(12, min(36, r))

    def _calc_fill(self, nm, mode: str) -> str:
        if mode == "inventory":
            if nm.inventory > 6000:
                return "#f59e0b"
            if nm.inventory > 2500:
                return "#fde68a"
            return "#d1fae5"

        if nm.profit < 0:
            return "#fecaca"
        if nm.profit < 300000:
            return "#fef3c7"
        return "#bfdbfe"

    def _calc_outline(self, nm, node_id: str, state: ReplayState) -> tuple[str, int]:
        if state.selected_node_id == node_id:
            return "#111827", 4
        if nm.profit < 0:
            return "#dc2626", 3
        return "#486581", 2
