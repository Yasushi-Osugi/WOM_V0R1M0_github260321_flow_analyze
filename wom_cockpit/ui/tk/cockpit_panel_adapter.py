from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional

from wom_cockpit.ui.cockpit_view_model import CockpitViewModel
from wom_cockpit.ui.scenario_compare_presenter import present_scenario_compare
from wom_cockpit.ui.issue_presenter import (
    present_issue_table_rows,
    present_issue_detail,
    find_issue_by_id,
)
from wom_cockpit.services.narrative_service import render_narrative_text


class CockpitPanelAdapter:
    """
    Tkinter上にWOM cockpit panelを描画する最小adapter。

    使い方:
        panel = CockpitPanelAdapter(parent_frame)
        panel.build()
        panel.render(vm)

    想定:
        - parent は ttk.Frame or tk.Frame
        - render(vm) を run/recompute 後に再呼び出しする
    """

    def __init__(self, parent: tk.Widget) -> None:
        self.parent = parent

        self.root_frame: Optional[ttk.Frame] = None

        self.summary_var = tk.StringVar(value="")
        self.header_var = tk.StringVar(value="WOM Management Cockpit")

        self.kpi_tree: Optional[ttk.Treeview] = None
        self.risk_listbox: Optional[tk.Listbox] = None
        self.issue_tree: Optional[ttk.Treeview] = None
        self.detail_text: Optional[tk.Text] = None
        self.narrative_text: Optional[tk.Text] = None

        self._current_vm: Optional[CockpitViewModel] = None
        self._risk_issue_ids: List[str] = []
        self._issue_id_by_tree_item: Dict[str, str] = {}

    # ------------------------------------------------------------
    # UI build
    # ------------------------------------------------------------

    def build(self) -> ttk.Frame:
        root = ttk.Frame(self.parent)
        root.grid(row=0, column=0, sticky="nsew")

        self.parent.rowconfigure(0, weight=1)
        self.parent.columnconfigure(0, weight=1)

        root.rowconfigure(3, weight=1)
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)

        self.root_frame = root

        # Header
        header = ttk.Label(root, textvariable=self.header_var, font=("", 12, "bold"))
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=(6, 2))

        summary = ttk.Label(
            root,
            textvariable=self.summary_var,
            anchor="w",
            justify="left",
            wraplength=1200,
        )
        summary.grid(row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 6))

        # Upper left: KPI
        kpi_frame = ttk.LabelFrame(root, text="Top KPIs")
        kpi_frame.grid(row=2, column=0, sticky="nsew", padx=6, pady=6)
        kpi_frame.rowconfigure(0, weight=1)
        kpi_frame.columnconfigure(0, weight=1)

        self.kpi_tree = ttk.Treeview(
            kpi_frame,
            columns=("label", "baseline", "scenario", "delta", "direction"),
            show="headings",
            height=6,
        )
        self.kpi_tree.heading("label", text="KPI")
        self.kpi_tree.heading("baseline", text="Baseline")
        self.kpi_tree.heading("scenario", text="Scenario")
        self.kpi_tree.heading("delta", text="Delta")
        self.kpi_tree.heading("direction", text="Direction")

        self.kpi_tree.column("label", width=160, anchor="w")
        self.kpi_tree.column("baseline", width=100, anchor="e")
        self.kpi_tree.column("scenario", width=100, anchor="e")
        self.kpi_tree.column("delta", width=100, anchor="e")
        self.kpi_tree.column("direction", width=100, anchor="center")
        self.kpi_tree.grid(row=0, column=0, sticky="nsew")

        # Upper right: Top Risks
        risk_frame = ttk.LabelFrame(root, text="Top Risks")
        risk_frame.grid(row=2, column=1, sticky="nsew", padx=6, pady=6)
        risk_frame.rowconfigure(0, weight=1)
        risk_frame.columnconfigure(0, weight=1)

        self.risk_listbox = tk.Listbox(risk_frame, height=6, exportselection=False)
        self.risk_listbox.grid(row=0, column=0, sticky="nsew")
        self.risk_listbox.bind("<<ListboxSelect>>", self._on_risk_selected)

        # Lower left: Issue Table
        issue_frame = ttk.LabelFrame(root, text="Issues")
        issue_frame.grid(row=3, column=0, sticky="nsew", padx=6, pady=6)
        issue_frame.rowconfigure(0, weight=1)
        issue_frame.columnconfigure(0, weight=1)

        self.issue_tree = ttk.Treeview(
            issue_frame,
            columns=("priority", "severity", "category", "title", "owner"),
            show="headings",
        )
        self.issue_tree.heading("priority", text="Priority")
        self.issue_tree.heading("severity", text="Severity")
        self.issue_tree.heading("category", text="Category")
        self.issue_tree.heading("title", text="Title")
        self.issue_tree.heading("owner", text="Owner")

        self.issue_tree.column("priority", width=70, anchor="e")
        self.issue_tree.column("severity", width=80, anchor="center")
        self.issue_tree.column("category", width=100, anchor="center")
        self.issue_tree.column("title", width=320, anchor="w")
        self.issue_tree.column("owner", width=110, anchor="center")
        self.issue_tree.grid(row=0, column=0, sticky="nsew")
        self.issue_tree.bind("<<TreeviewSelect>>", self._on_issue_selected)

        # Lower right: detail + narrative
        detail_frame = ttk.LabelFrame(root, text="Issue Detail / Narrative")
        detail_frame.grid(row=3, column=1, sticky="nsew", padx=6, pady=6)
        detail_frame.rowconfigure(0, weight=3)
        detail_frame.rowconfigure(1, weight=2)
        detail_frame.columnconfigure(0, weight=1)

        self.detail_text = tk.Text(detail_frame, wrap="word", height=16)
        self.detail_text.grid(row=0, column=0, sticky="nsew")

        self.narrative_text = tk.Text(detail_frame, wrap="word", height=8)
        self.narrative_text.grid(row=1, column=0, sticky="nsew", pady=(6, 0))

        return root

    # ------------------------------------------------------------
    # render
    # ------------------------------------------------------------

    def render(self, vm: CockpitViewModel) -> None:
        """
        CockpitViewModel を Tk widgets に反映する。
        """
        self._current_vm = vm
        presentation = present_scenario_compare(vm)

        self.header_var.set(presentation.header_title)
        self.summary_var.set(presentation.summary_text)

        self._render_kpis(vm)
        self._render_risks(vm)
        self._render_issues(vm)
        self._render_narrative(vm)

        # 初期詳細は最優先 issue
        if vm.issues:
            self._show_issue_detail(vm.issues[0])
        else:
            self._set_text(self.detail_text, "No issues detected.")

    # ------------------------------------------------------------
    # sub renderers
    # ------------------------------------------------------------

    def _render_kpis(self, vm: CockpitViewModel) -> None:
        if self.kpi_tree is None:
            return

        for item in self.kpi_tree.get_children():
            self.kpi_tree.delete(item)

        for kpi in vm.top_kpis:
            self.kpi_tree.insert(
                "",
                "end",
                values=(
                    kpi.label,
                    f"{kpi.before:.1f}",
                    f"{kpi.after:.1f}",
                    f"{kpi.delta:+.1f}",
                    kpi.direction,
                ),
            )

    def _render_risks(self, vm: CockpitViewModel) -> None:
        if self.risk_listbox is None:
            return

        self.risk_listbox.delete(0, tk.END)
        self._risk_issue_ids = []

        for risk in vm.top_risks:
            self.risk_listbox.insert(
                tk.END,
                f"[{risk.priority}] [{risk.severity}] {risk.title}"
            )
            self._risk_issue_ids.append(risk.risk_id)

    def _render_issues(self, vm: CockpitViewModel) -> None:
        if self.issue_tree is None:
            return

        for item in self.issue_tree.get_children():
            self.issue_tree.delete(item)

        self._issue_id_by_tree_item = {}
        rows = present_issue_table_rows(vm.issues)

        for row in rows:
            item_id = self.issue_tree.insert(
                "",
                "end",
                values=(
                    row.priority,
                    row.severity,
                    row.category,
                    row.title,
                    row.owner_hint,
                ),
            )
            self._issue_id_by_tree_item[item_id] = row.issue_id

    def _render_narrative(self, vm: CockpitViewModel) -> None:
        text = render_narrative_text(vm)
        extra_text = str((vm.metadata or {}).get("narrative_override", "") or "").strip()
        if extra_text:
            if text.strip():
                text = f"{text}\n\n---\n[Management Issue Analyzer]\n{extra_text}"
            else:
                text = extra_text
        self._set_text(self.narrative_text, text)

    # ------------------------------------------------------------
    # event handlers
    # ------------------------------------------------------------

    def _on_issue_selected(self, event=None) -> None:
        if self.issue_tree is None or self._current_vm is None:
            return

        selection = self.issue_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        issue_id = self._issue_id_by_tree_item.get(item_id)
        if not issue_id:
            return

        issue = find_issue_by_id(self._current_vm.issues, issue_id)
        if issue is not None:
            self._show_issue_detail(issue)

    def _on_risk_selected(self, event=None) -> None:
        if self.risk_listbox is None or self._current_vm is None:
            return

        selection = self.risk_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        if idx >= len(self._risk_issue_ids):
            return

        issue_id = self._risk_issue_ids[idx]
        issue = find_issue_by_id(self._current_vm.issues, issue_id)
        if issue is not None:
            self._show_issue_detail(issue)

    # ------------------------------------------------------------
    # detail rendering
    # ------------------------------------------------------------

    def _show_issue_detail(self, issue) -> None:
        detail = present_issue_detail(issue)

        lines: List[str] = []
        lines.append(detail.title)
        lines.append(detail.header_line)
        lines.append("")
        lines.append("Summary")
        lines.append(detail.summary)
        lines.append("")
        lines.append("Why it matters")
        lines.append(detail.why_it_matters)
        lines.append("")
        lines.append("Management question")
        lines.append(detail.management_question)
        lines.append("")
        lines.append("Recommendation summary")
        lines.append(detail.recommendation_summary)
        lines.append("")
        lines.append("Affected")
        lines.append(detail.affected_text)
        lines.append("")
        lines.append("Evidence")
        lines.extend(detail.evidence_lines)
        lines.append("")
        lines.append("Recommended actions")
        lines.extend(detail.action_lines)

        self._set_text(self.detail_text, "\n".join(lines))

    # ------------------------------------------------------------
    # utilities
    # ------------------------------------------------------------

    @staticmethod
    def _set_text(widget: Optional[tk.Text], text: str) -> None:
        if widget is None:
            return
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state="disabled")
