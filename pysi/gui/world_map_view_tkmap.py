# ------------------------------------------------------------
# pysi/gui/world_map_view_tkmap.py
# ------------------------------------------------------------
# TkinterMapView ベースの世界地図 GUI
#
# 既存の world_map_view.py との互換性:
#   - show_world_map_tkmap(env, product_name, on_select, parent_tk, title)
#     を呼ぶだけで動く (cockpit_tk.py から最小変更で切り替え可能)
#   - on_select(node_name, source="world_map") のコールバックシグネチャは同じ
#   - env / geo_lookup / prod_tree_dict_OT / prod_tree_dict_IN などの
#     データ構造は world_map_view.py と共通
#
# 役割分担:
#   TkinterMapView 側 ... 背景地図, パン/ズーム, node marker, edge polyline, click
#   Matplotl
#   Matplotlib 側    ... PSI/KPI chart や補助ビュー
#
# 依存:
#   python -m pip install tkintermapview
#
# DESIGN NOTES:
#   - node marker は TkinterMapView.set_marker() で配置
#   - edge は TkinterMapView.set_path() で polyline 描画
#   - antimeridian をまたぐ edge は中間点を挿入して折り返しを防ぐ
#   - selected node は marker を remove -> 再生成してハイライト
#   - node 名 prefix で色分け (MOM_, DAD_, WS_, RT_, CS_ など)
# ------------------------------------------------------------

from __future__ import annotations

import os
import csv
import math
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

OnSelect = Callable[[str], None]


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------
def show_world_map_tkmap(
    env: Any,
    product_name: str | None = None,
    on_select: Optional[OnSelect] = None,
    *,
    parent_tk: Any | None = None,
    title: str = "Global Supply Chain Map",
) -> "WorldMapViewTk":
    """既存 show_world_map(...) とほぼ同じ入口。"""
    view = WorldMapViewTk(
        env,
        product_name=product_name,
        on_select=on_select,
        parent_tk=parent_tk,
        title=title,
    )
    view.show()
    return view


# ------------------------------------------------------------
# Geo lookup helpers
# ------------------------------------------------------------
def _resolve_data_dir(env: Any) -> Optional[str]:
    if env is None:
        return None

    d = getattr(env, "data_dir", None)
    if isinstance(d, str) and d.strip():
        return d

    cfg = getattr(env, "cfg", None)
    if cfg is not None:
        for attr in ("DATA_DIRECTORY", "data_dir"):
            d2 = getattr(cfg, attr, None)
            if isinstance(d2, str) and d2.strip():
                return d2

    return None


def _geo_lookup_from_csv(env: Any) -> Dict[str, Tuple[float, float]]:
    data_dir = _resolve_data_dir(env)
    if not data_dir:
        return {}

    path = os.path.join(data_dir, "node_geo.csv")
    if not os.path.exists(path):
        return {}

    geo: Dict[str, Tuple[float, float]] = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("node_name") or row.get("name") or "").strip()
            if not name:
                continue
            try:
                geo[name] = (float(row["lat"]), float(row["lon"]))
            except Exception:
                continue
    return geo


# ------------------------------------------------------------
# Distance helper
# ------------------------------------------------------------
def _haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371.0
    la1 = math.radians(lat1)
    la2 = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    dlat = math.radians(lat2 - lat1)
    a = math.sin(dlat / 2.0) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlon / 2.0) ** 2
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(1e-12, 1.0 - a)))


# ------------------------------------------------------------
# Antimeridian helper
# ------------------------------------------------------------
def _edge_waypoints(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> List[Tuple[float, float]]:
    """
    TkinterMapView.set_path に渡す (lat, lon) の点列を返す。
    経度差が大きいときは中間点を入れて太平洋側への変な折れを抑える。
    """
    dlon = lon2 - lon1
    if abs(dlon) <= 180.0:
        return [(lat1, lon1), (lat2, lon2)]

    n = 6
    pts: List[Tuple[float, float]] = []
    for i in range(n + 1):
        t = i / n
        lat = lat1 + t * (lat2 - lat1)
        lon = lon1 + t * dlon
        lon = ((lon + 180.0) % 360.0) - 180.0
        pts.append((lat, lon))
    return pts


# ============================================================
# Main class
# ============================================================
class WorldMapViewTk:
    # ---- base colors ----
    _COLOR_DEFAULT = "#1f77b4"
    _COLOR_HUB = "#444444"
    _COLOR_SELECTED = "#d62728"

    _COLOR_EDGE_ALL = "#bbbbbb"
    _COLOR_EDGE_OT = "royalblue"
    _COLOR_EDGE_IN = "seagreen"

    _HUB_NAMES = {"sales_office", "procurement_office", "supply_point"}

    def __init__(
        self,
        env: Any,
        *,
        product_name: str | None = None,
        on_select: Optional[OnSelect] = None,
        parent_tk: Any | None = None,
        title: str = "Global Supply Chain Map",
    ):
        self.env = env
        self.product_name = product_name
        self._on_select_cb = on_select
        self.parent_tk = parent_tk
        self.title = title

        self._pos: Dict[str, Tuple[float, float]] = {}   # node_name -> (lat, lon)
        self._nodes: Dict[str, Any] = {}
        self._markers: Dict[str, Any] = {}
        self._paths: List[Any] = []

        self._map_widget = None
        self._top: Optional[tk.Toplevel] = None
        self._selected_node: Optional[str] = None
        self._info_var: Optional[tk.StringVar] = None

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------
    def show(self) -> None:
        try:
            from tkintermapview import TkinterMapView
        except ImportError:
            self._fallback_error()
            return

        if self.parent_tk is not None:
            self._top = tk.Toplevel(self.parent_tk)
        else:
            self._top = tk.Tk()

        self._top.title(self.title)
        self._top.geometry("1300x750")
        self._top.configure(bg="#f0f0f0")

        main_frame = tk.Frame(self._top, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=4, pady=4)

        map_frame = tk.Frame(main_frame, bg="#cccccc", relief="sunken", bd=1)
        map_frame.pack(side="left", fill="both", expand=True)

        right_frame = tk.Frame(main_frame, bg="#f0f0f0", width=220)
        right_frame.pack(side="right", fill="y", padx=(4, 0))
        right_frame.pack_propagate(False)

        self._map_widget = TkinterMapView(map_frame, corner_radius=0)
        self._map_widget.pack(fill="both", expand=True)

        geo = self._load_geo()
        nodes_all = self._collect_all_nodes()
        all_edges = self._collect_all_edges()
        ot_edges, in_edges, selected_names = self._collect_highlight_edges()

        missing = self._build_pos(nodes_all, geo)
        if missing:
            print(f"[TKMAP] missing geo (first 20): {missing[:20]}")

        self._set_initial_view(selected_names)
        self._draw_edges(all_edges, ot_edges, in_edges)
        self._draw_markers(nodes_all, selected_names)
        self._build_legend_panel(right_frame)

        self._map_widget.add_right_click_menu_command(
            label="Reset view",
            command=lambda coords: self._reset_view(),
            pass_coords=True,
        )

        print(f"[TKMAP] ready: {len(self._pos)} nodes, {len(self._paths)} paths")

        if self.parent_tk is None:
            self._top.mainloop()

    def set_selected_node(self, node_name: str) -> None:
        if not node_name or node_name not in self._pos:
            return
        self._highlight_node(node_name)

    # ----------------------------------------------------------
    # Data collection
    # ----------------------------------------------------------
    def _load_geo(self) -> Dict[str, Tuple[float, float]]:
        geo: Dict[str, Tuple[float, float]] = {}
        if hasattr(self.env, "geo_lookup") and callable(self.env.geo_lookup):
            try:
                geo = self.env.geo_lookup() or {}
            except Exception as e:
                print(f"[TKMAP] env.geo_lookup() failed: {e}")
        if not geo:
            geo = _geo_lookup_from_csv(self.env)
        print(f"[TKMAP] geo_lookup: {len(geo)} entries")
        return geo

    def _walk_nodes(self, root) -> Iterable[Any]:
        if root is None:
            return []
        stack = [root]
        out = []
        while stack:
            n = stack.pop()
            if n is None:
                continue
            out.append(n)
            for c in (getattr(n, "children", None) or []):
                stack.append(c)
        return out

    def _iter_parent_child(self, root) -> Iterable[Tuple[Any, Any]]:
        if root is None:
            return []
        out = []
        stack = [root]
        while stack:
            p = stack.pop()
            if p is None:
                continue
            for c in (getattr(p, "children", None) or []):
                out.append((p, c))
                stack.append(c)
        return out

    def _collect_all_nodes(self) -> Dict[str, Any]:
        nodes: Dict[str, Any] = {}

        for attr in ("prod_tree_dict_OT", "prod_tree_dict_IN"):
            d = getattr(self.env, attr, None)
            if d:
                for root in d.values():
                    for n in self._walk_nodes(root):
                        name = getattr(n, "name", None)
                        if name:
                            nodes[name] = n

        if not nodes:
            nodes = {
                **({} if not getattr(self.env, "nodes_outbound", None) else self.env.nodes_outbound),
                **({} if not getattr(self.env, "nodes_inbound", None) else self.env.nodes_inbound),
            }

        self._nodes = nodes
        return nodes

    def _collect_all_edges(self) -> set:
        G = getattr(self.env, "G", None)
        if G is not None and hasattr(G, "edges"):
            try:
                return set(G.edges())
            except Exception:
                pass

        edges: set = set()
        for attr in ("prod_tree_dict_OT", "prod_tree_dict_IN"):
            d = getattr(self.env, attr, None)
            if d:
                for root in d.values():
                    for p, c in self._iter_parent_child(root):
                        pn = getattr(p, "name", "") or ""
                        cn = getattr(c, "name", "") or ""
                        edges.add((pn, cn))
        return edges

    def _collect_highlight_edges(self):
        ot_edges: set = set()
        in_edges: set = set()
        selected: set = set()

        if not self.product_name:
            return ot_edges, in_edges, selected

        for attr, target in (("prod_tree_dict_OT", ot_edges), ("prod_tree_dict_IN", in_edges)):
            d = getattr(self.env, attr, None)
            if not d:
                continue
            root = d.get(self.product_name)
            if not root:
                continue

            for p, c in self._iter_parent_child(root):
                pn = getattr(p, "name", "") or ""
                cn = getattr(c, "name", "") or ""
                target.add((pn, cn))

            for n in self._walk_nodes(root):
                nm = getattr(n, "name", None)
                if nm:
                    selected.add(nm)

        return ot_edges, in_edges, selected

    def _build_pos(self, nodes_all: Dict[str, Any], geo: Dict[str, Tuple[float, float]]) -> List[str]:
        missing = []
        for name in nodes_all:
            g = geo.get(name)
            if not g:
                missing.append(name)
                continue
            self._pos[name] = (float(g[0]), float(g[1]))   # (lat, lon)
        return missing

    # ----------------------------------------------------------
    # View
    # ----------------------------------------------------------
    def _set_initial_view(self, selected_names: set) -> None:
        if not self._pos:
            self._map_widget.set_position(20.0, 0.0)
            self._map_widget.set_zoom(2)
            return

        focus = [self._pos[n] for n in selected_names if n in self._pos] or list(self._pos.values())
        lats = [p[0] for p in focus]
        lons = [p[1] for p in focus]

        lat_c = (min(lats) + max(lats)) / 2.0
        lon_c = (min(lons) + max(lons)) / 2.0

        try:
            self._map_widget.fit_bounding_box(
                (max(lats) + 5, min(lons) - 5),
                (min(lats) - 5, max(lons) + 5),
            )
        except Exception:
            self._map_widget.set_position(lat_c, lon_c)
            self._map_widget.set_zoom(2)

    def _reset_view(self) -> None:
        if not self._pos:
            return
        lats = [p[0] for p in self._pos.values()]
        lons = [p[1] for p in self._pos.values()]
        try:
            self._map_widget.fit_bounding_box(
                (max(lats) + 5, min(lons) - 5),
                (min(lats) - 5, max(lons) + 5),
            )
        except Exception:
            pass

    # ----------------------------------------------------------
    # Marker helpers
    # ----------------------------------------------------------
    def _node_color(self, node_name: str, *, selected: bool = False) -> str:
        if selected:
            return self._COLOR_SELECTED

        if node_name in self._HUB_NAMES:
            return self._COLOR_HUB

        up = node_name.upper()

        if up.startswith("MOM_"):
            return "#c0392b"   # factory / manufacturing
        if up.startswith("PAD_") or up.startswith("DAD_"):
            return "#8e44ad"   # parent / distribution hub
        if up.startswith("WS_"):
            return "#2980b9"   # warehouse
        if up.startswith("RT_"):
            return "#16a085"   # retail
        if up.startswith("CS_"):
            return "#f39c12"   # customer / consumer
        if up.startswith("PROC_") or up.startswith("SUP_"):
            return "#555555"   # procurement / supplier-ish

        return self._COLOR_DEFAULT

    def _make_marker_cb(self, node_name: str) -> Callable:
        def _cb(marker):
            self._on_marker_click(node_name)
        return _cb

    def _remove_marker(self, node_name: str) -> None:
        marker = self._markers.get(node_name)
        if marker is None:
            return
        try:
            marker.delete()
        except Exception:
            try:
                marker.destroy()
            except Exception:
                pass
        self._markers.pop(node_name, None)

    def _create_marker(self, node_name: str, *, selected: bool = False) -> None:
        if node_name not in self._pos:
            return

        lat, lon = self._pos[node_name]
        color = self._node_color(node_name, selected=selected)

        marker = self._map_widget.set_marker(
            lat,
            lon,
            text=node_name,
            marker_color_circle=color,
            marker_color_outside=color,
            command=self._make_marker_cb(node_name),
        )
        self._markers[node_name] = marker

    # ----------------------------------------------------------
    # Draw
    # ----------------------------------------------------------
    def _draw_markers(self, nodes_all: Dict[str, Any], selected_names: set) -> None:
        for name in self._pos.keys():
            self._create_marker(name, selected=(name in selected_names))

        if selected_names:
            try:
                self._selected_node = sorted(selected_names)[0]
            except Exception:
                self._selected_node = None
        else:
            self._selected_node = None

    def _draw_edges(self, all_edges: set, ot_edges: set, in_edges: set) -> None:
        for u, v in all_edges:
            if u in self._pos and v in self._pos:
                pts = _edge_waypoints(*self._pos[u], *self._pos[v])
                path = self._map_widget.set_path(pts, color=self._COLOR_EDGE_ALL, width=1)
                self._paths.append(path)

        for u, v in ot_edges:
            if u in self._pos and v in self._pos:
                pts = _edge_waypoints(*self._pos[u], *self._pos[v])
                path = self._map_widget.set_path(pts, color=self._COLOR_EDGE_OT, width=3)
                self._paths.append(path)

        for u, v in in_edges:
            if u in self._pos and v in self._pos:
                pts = _edge_waypoints(*self._pos[v], *self._pos[u])
                path = self._map_widget.set_path(pts, color=self._COLOR_EDGE_IN, width=3)
                self._paths.append(path)

    def _clear_highlight_markers(self) -> None:
        if self._selected_node and self._selected_node in self._pos:
            old_name = self._selected_node
            self._remove_marker(old_name)
            self._create_marker(old_name, selected=False)
        self._selected_node = None

    def _highlight_node(self, node_name: str) -> None:
        if node_name not in self._pos:
            return

        if self._selected_node and self._selected_node != node_name:
            self._remove_marker(self._selected_node)
            self._create_marker(self._selected_node, selected=False)

        self._remove_marker(node_name)
        self._create_marker(node_name, selected=True)
        self._selected_node = node_name

        lat, lon = self._pos[node_name]
        self._map_widget.set_position(lat, lon)

        try:
            z = self._map_widget.zoom
            if z < 4:
                self._map_widget.set_zoom(4)
        except Exception:
            pass

        self._show_info_popup(node_name, lat, lon)

    def _show_info_popup(self, node_name: str, lat: float, lon: float) -> None:
        if self._info_var is None:
            return

        node = self._nodes.get(node_name)
        lines = [f"▶ {node_name}", f"lat: {lat:.3f}  lon: {lon:.3f}"]
        if node is not None:
            for k in ("node_type", "capacity", "cost_coeff", "revenue_coeff"):
                if hasattr(node, k):
                    lines.append(f"{k}: {getattr(node, k)}")
        self._info_var.set("\n".join(lines))

    # ----------------------------------------------------------
    # Legend / right panel
    # ----------------------------------------------------------
    def _build_legend_panel(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Legend",
            font=("Helvetica", 11, "bold"),
            bg="#f0f0f0",
            anchor="w",
        ).pack(fill="x", padx=8, pady=(8, 2))

        legend_items = [
            (self._COLOR_EDGE_ALL, "All edges"),
            (self._COLOR_EDGE_OT, "Outbound (product)"),
            (self._COLOR_EDGE_IN, "Inbound (product)"),
            ("#c0392b", "MOM / Factory"),
            ("#8e44ad", "PAD / DAD Hub"),
            ("#2980b9", "WS"),
            ("#16a085", "RT"),
            ("#f39c12", "CS"),
            (self._COLOR_HUB, "Office / Supply Point"),
            (self._COLOR_SELECTED, "Selected node"),
        ]

        for color, label in legend_items:
            row = tk.Frame(parent, bg="#f0f0f0")
            row.pack(fill="x", padx=8, pady=1)
            tk.Canvas(row, width=24, height=10, bg=color, highlightthickness=0).pack(side="left")
            tk.Label(row, text=f"  {label}", bg="#f0f0f0", font=("Helvetica", 9)).pack(side="left")

        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=8, pady=8)

        tk.Label(
            parent,
            text="Selected node",
            font=("Helvetica", 10, "bold"),
            bg="#f0f0f0",
            anchor="w",
        ).pack(fill="x", padx=8)

        self._info_var = tk.StringVar(value="(click a marker)")
        tk.Label(
            parent,
            textvariable=self._info_var,
            bg="#f8f8f8",
            relief="groove",
            justify="left",
            font=("Courier", 9),
            anchor="nw",
            wraplength=190,
        ).pack(fill="x", padx=8, pady=4)

        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=8, pady=8)

        tk.Button(
            parent,
            text="Reset view",
            command=self._reset_view,
            bg="#e0e0e0",
        ).pack(fill="x", padx=8, pady=2)

        if self.product_name:
            tk.Label(
                parent,
                text=f"Product:\n{self.product_name}",
                bg="#f0f0f0",
                font=("Helvetica", 9),
                anchor="w",
                justify="left",
            ).pack(fill="x", padx=8, pady=(8, 0))

        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=8, pady=8)

        tk.Label(
            parent,
            text=f"Nodes: {len(self._pos)}\nPaths: {len(self._paths)}",
            bg="#f0f0f0",
            font=("Helvetica", 9),
            anchor="w",
        ).pack(fill="x", padx=8)

    # ----------------------------------------------------------
    # Click handler
    # ----------------------------------------------------------
    def _on_marker_click(self, node_name: str) -> None:
        if node_name not in self._pos:
            return

        self._highlight_node(node_name)

        cb = self._on_select_cb
        if callable(cb):
            try:
                cb(node_name, source="world_map")
            except TypeError:
                cb(node_name)

    # ----------------------------------------------------------
    # Fallback
    # ----------------------------------------------------------
    def _fallback_error(self) -> None:
        msg = (
            "tkintermapview が見つかりません。\n\n"
            "以下のコマンドでインストールしてください:\n"
            "    python -m pip install tkintermapview\n\n"
            "インストール後に再起動してください。"
        )
        try:
            import tkinter.messagebox as mb
            if self.parent_tk:
                mb.showerror("依存ライブラリ不足", msg, parent=self.parent_tk)
            else:
                root = tk.Tk()
                root.withdraw()
                mb.showerror("依存ライブラリ不足", msg)
                root.destroy()
        except Exception:
            print(f"[TKMAP ERROR] {msg}")


# ============================================================
# cockpit_tk.py からの切り替えガイド
# ============================================================
#
# USE_TKMAP = True
#
# if USE_TKMAP:
#     from pysi.gui.world_map_view_tkmap import show_world_map_tkmap as _show_world_map
# else:
#     from pysi.gui.world_map_view import show_world_map as _show_world_map
#
# _show_world_map(env, product_name=prod, on_select=cb, parent_tk=root)
#
# ============================================================


# ============================================================
# Standalone demo
# ============================================================
if __name__ == "__main__":
    import types

    env = types.SimpleNamespace()

    _DEMO_GEO = {
        "Tokyo_HQ": (35.68, 139.69),
        "London_DC": (51.51, -0.13),
        "NewYork_WH": (40.71, -74.01),
        "Singapore_HUB": (1.35, 103.82),
        "Sydney_RT": (-33.87, 151.21),
        "Paris_MOM": (48.85, 2.35),
        "Shanghai_FAC": (31.23, 121.47),
        "Dubai_WH": (25.20, 55.27),
        "DAD_EURO": (50.11, 8.68),
        "WS_EURO": (52.52, 13.40),
        "RT_EURO": (41.90, 12.50),
        "CS_EURO": (48.86, 2.35),
    }
    env.geo_lookup = lambda: _DEMO_GEO

    class _N:
        def __init__(self, name, node_type="factory"):
            self.name = name
            self.node_type = node_type
            self.children = []

    root_ot = _N("Tokyo_HQ", "HQ")
    c1 = _N("Shanghai_FAC")
    c2 = _N("Singapore_HUB")
    c3 = _N("DAD_EURO")
    c4 = _N("WS_EURO")
    c5 = _N("RT_EURO")
    c6 = _N("CS_EURO")
    c7 = _N("London_DC")
    c8 = _N("NewYork_WH")
    c9 = _N("Sydney_RT")
    c10 = _N("Paris_MOM")
    c11 = _N("Dubai_WH")

    root_ot.children.extend([c1, c2])
    c2.children.extend([c3, c7, c8, c9, c10, c11])
    c3.children.append(c4)
    c4.children.append(c5)
    c5.children.append(c6)

    env.prod_tree_dict_OT = {"DEMO_PRODUCT": root_ot}
    env.prod_tree_dict_IN = {}

    def _on_select(name, source=None):
        print(f"[SELECT] {name}  source={source}")

    show_world_map_tkmap(
        env,
        product_name="DEMO_PRODUCT",
        on_select=_on_select,
        parent_tk=None,
        title="WOM Supply Chain Map (TkinterMapView版)",
    )