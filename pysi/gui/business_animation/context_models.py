#pysi/gui/business_animation/context_models.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BusinessAnimationContext:
    """
    cockpit_tk.py -> business_animation_panel.py へ渡す最小コンテキスト。

    v0.1 の思想:
    - GUI選択状態(product / direction / selected_node)をまとめる
    - network描画用に root / node_dict / edges を持つ
    - replay生成用に trace / bridge / cashflow を持つ
    - scenario は現時点では BASE 固定でもよいが、先に受け口だけ持つ
    """

    # ------------------------------------------------------------
    # GUI / scenario selection
    # ------------------------------------------------------------
    product_name: str
    scenario_name: str = "BASE"
    direction: str = "outbound"          # "outbound" / "inbound"
    selected_node: Optional[str] = None

    # ------------------------------------------------------------
    # Network / planning tree
    # ------------------------------------------------------------
    root_node: Any | None = None
    node_dict: dict[str, Any] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)

    # ------------------------------------------------------------
    # Event / bridge / KPI sources
    # ------------------------------------------------------------
    trace_events: list[dict[str, Any]] = field(default_factory=list)
    bridge_payload: dict[str, Any] = field(default_factory=dict)
    cashflow_df: Any | None = None

    # ------------------------------------------------------------
    # Optional future extensions
    # ------------------------------------------------------------
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """
        最小バリデーション。
        例外を投げることで、呼び出し元で早めに気づけるようにする。
        """
        if not isinstance(self.product_name, str) or not self.product_name.strip():
            raise ValueError("BusinessAnimationContext.product_name must be a non-empty string")

        if self.direction not in ("outbound", "inbound"):
            raise ValueError("BusinessAnimationContext.direction must be 'outbound' or 'inbound'")

        if not isinstance(self.node_dict, dict):
            raise TypeError("BusinessAnimationContext.node_dict must be a dict")

        if not isinstance(self.edges, list):
            raise TypeError("BusinessAnimationContext.edges must be a list")

        if not isinstance(self.trace_events, list):
            raise TypeError("BusinessAnimationContext.trace_events must be a list")

        if not isinstance(self.bridge_payload, dict):
            raise TypeError("BusinessAnimationContext.bridge_payload must be a dict")

        if not isinstance(self.metadata, dict):
            raise TypeError("BusinessAnimationContext.metadata must be a dict")

    @property
    def node_ids(self) -> list[str]:
        """
        node_dict を優先しつつ、edges にしか出ていない node 名も拾う。
        """
        names = set(self.node_dict.keys())
        for src, dst in self.edges:
            names.add(src)
            names.add(dst)
        return sorted(names)

    @property
    def has_trace_events(self) -> bool:
        return bool(self.trace_events)

    @property
    def has_bridge_events(self) -> bool:
        return bool(self.bridge_payload.get("events"))

    @property
    def has_cashflow(self) -> bool:
        return self.cashflow_df is not None

    def get_node(self, node_id: str) -> Any | None:
        """
        node_dict から node object を返す。
        """
        return self.node_dict.get(node_id)

    def to_debug_dict(self) -> dict[str, Any]:
        """
        print / log 用の軽量サマリ。
        DataFrame本体や巨大eventは含めない。
        """
        return {
            "product_name": self.product_name,
            "scenario_name": self.scenario_name,
            "direction": self.direction,
            "selected_node": self.selected_node,
            "root_node_name": getattr(self.root_node, "name", None) if self.root_node is not None else None,
            "node_count": len(self.node_dict),
            "edge_count": len(self.edges),
            "trace_event_count": len(self.trace_events),
            "bridge_event_count": len(self.bridge_payload.get("events", []) or []),
            "has_cashflow": self.has_cashflow,
            "metadata_keys": sorted(self.metadata.keys()),
        }
