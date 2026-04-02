#pysi/gui/business_animation/business_animation_panel.py

#これは最小の起動パネルです。
#左に network、右に KPI、上に control を置きます。

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .animation_controller import AnimationController
from .network_anim_view import NetworkAnimView
from .replay_builder import build_dummy_snapshots


class BusinessAnimationPanel(tk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.pack(fill="both", expand=True)

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

        self.snapshots = build_dummy_snapshots(
            node_ids=list(self.node_positions.keys()),
            edges=self.edges,
            weeks=24,
        )

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
        self.node_kpi_var = tk.StringVar(value="Revenue: -\nCost: -\nProfit: -\nInventory: -")

        ttk.Label(right, text="Business Animation", font=("Arial", 12, "bold")).pack(anchor="w", padx=8, pady=(10, 8))
        ttk.Label(right, textvariable=self.week_var).pack(anchor="w", padx=8, pady=4)
        ttk.Label(right, textvariable=self.total_var, justify="left").pack(anchor="w", padx=8, pady=4)
        ttk.Separator(right, orient="horizontal").pack(fill="x", padx=8, pady=8)
        ttk.Label(right, textvariable=self.node_var).pack(anchor="w", padx=8, pady=4)
        ttk.Label(right, textvariable=self.node_kpi_var, justify="left").pack(anchor="w", padx=8, pady=4)

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

    def _on_frame_changed(self, snapshot, state) -> None:
        self.network_view.render_snapshot(snapshot, state)

        self.week_var.set(f"Week: {snapshot.week_no}")
        self.total_var.set(
            "\n".join([
                f"Total Revenue: {snapshot.total_metrics.revenue:,.0f}",
                f"Total Cost:    {snapshot.total_metrics.cost:,.0f}",
                f"Total Profit:  {snapshot.total_metrics.profit:,.0f}",
                f"Total Inv:     {snapshot.total_metrics.inventory:,.0f}",
            ])
        )

        node_id = state.selected_node_id
        if node_id and node_id in snapshot.node_metrics:
            nm = snapshot.node_metrics[node_id]
            self.node_var.set(f"Selected Node: {node_id}")
            self.node_kpi_var.set(
                "\n".join([
                    f"Revenue:   {nm.revenue:,.0f}",
                    f"Cost:      {nm.cost:,.0f}",
                    f"Profit:    {nm.profit:,.0f}",
                    f"Inventory: {nm.inventory:,.0f}",
                    f"Cash In:   {nm.cash_in:,.0f}",
                    f"Cash Out:  {nm.cash_out:,.0f}",
                ])
            )
        else:
            self.node_var.set("Selected Node: -")
            self.node_kpi_var.set("Revenue: -\nCost: -\nProfit: -\nInventory: -")
