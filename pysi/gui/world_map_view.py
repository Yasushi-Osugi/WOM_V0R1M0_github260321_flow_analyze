# ------------------------------------------------------------
# pysi/gui/world_map_view.py
# ------------------------------------------------------------
# World Map view extracted from huge gui/app.py
#
# Goal:
#   - Keep cockpit_tk.py light: only "import and call"
#   - Keep app.py compatibility: PSIPlannerApp.show_world_map delegates here
#   - Preserve original flow:
#       show() -> build pos/nodes/edges -> save _map_* -> mpl_connect -> _on_map_click
#
# Callback:
#   on_select(node_name, source="world_map")  # keyword arg allowed
#
# BUG FIXES (zoom/slide):
#   [FIX-1] _auto_fit was defined 3 times; only the last definition was active.
#           Removed the first two duplicate definitions.
#   [FIX-2] _on_map_motion and _on_map_scroll referenced self.canvas_network
#           (non-existent attribute). Changed to self.state.canvas.
#   [FIX-3] _install_map_interactions re-registered scroll_event and
#           key_press_event which are already registered in _connect_base_events,
#           causing double-firing on every event. Removed the duplicates.
#   [FIX-4] _on_map_key defined _fit_lonlat as a local function shadow, making
#           self._fit_lonlat unreachable. Removed the local shadows; the method
#           is called directly.
#   [FIX-5] _fit_lonlat called set_extent(crs=map_crs) (projection coords) but
#           Cartopy's set_extent expects lon/lat (PlateCarree) when crs=data_crs.
#           Fixed to always pass crs=data_crs and supply lon/lat extents.
#   [FIX-6] _on_map_release still referenced legacy _map_panning / _set_map_cursor
#           attributes. Replaced with the pan_state dict used by _on_map_press/motion.
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Any

import os
import csv

import time

import matplotlib.pyplot as plt

OnSelect = Callable[[str], None]  # we may call with keyword arg source="world_map"


# ------------------------------------------------------------
# Geo lookup (CSV) unified resolver
# ------------------------------------------------------------
def _resolve_data_dir(env: Any) -> Optional[str]:
    if env is None:
        return None

    d = getattr(env, "data_dir", None)
    if isinstance(d, str) and d.strip():
        return d

    cfg = getattr(env, "cfg", None)
    if cfg is not None:
        d2 = getattr(cfg, "DATA_DIRECTORY", None)
        if isinstance(d2, str) and d2.strip():
            return d2
        d3 = getattr(cfg, "data_dir", None)
        if isinstance(d3, str) and d3.strip():
            return d3

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
                lat = float(row.get("lat"))
                lon = float(row.get("lon"))
            except Exception:
                continue
            geo[name] = (lat, lon)
    return geo


def show_world_map(
    env: Any,
    product_name: str | None = None,
    on_select: Optional[Callable[[str], None]] = None,
    *,
    parent_tk: Any | None = None,
    title: str = "Global Supply Chain Map",
) -> "WorldMapView":
    view = WorldMapView(
        env,
        product_name=product_name,
        on_select=on_select,
        parent_tk=parent_tk,
        title=title,
    )
    view.show()
    return view


@dataclass
class _MapState:
    ax: Any | None = None
    fig: Any | None = None
    canvas: Any | None = None

    used_cartopy: bool = False
    data_crs: Any | None = None

    pos: Dict[str, Tuple[float, float]] = None   # node_name -> (lon, lat)
    nodes: Dict[str, Any] = None
    all_edges: List[Tuple[str, str]] = None
    high_edges: List[Tuple[str, str]] = None

    anno_artist: Any | None = None
    highlight_artists: List[Any] = None

    cids: List[int] = None


class WorldMapView:
    def __init__(
        self,
        env: Any,
        *,
        product_name: str | None = None,
        on_select: Optional[Callable[[str], None]] = None,
        parent_tk: Any | None = None,
        title: str = "Global Supply Chain Map",
    ):
        self.env = env
        self.product_name = product_name
        self._map_on_select = on_select
        self.parent_tk = parent_tk
        self.title = title

        self.state = _MapState(
            pos={},
            nodes={},
            all_edges=[],
            high_edges=[],
            highlight_artists=[],
            cids=[],
        )

        self.world_map_mode = getattr(env, "world_map_mode", "global")
        self.world_map_fit = getattr(env, "world_map_fit", True)
        self._map_drag_threshold = 5
        self._map_last_draw_ts = 0.0
        self._map_redraw_interval = 0.03


    def set_selected_node(self, node_name: str) -> None:
        if not node_name:
            return
        try:
            self._clear_map_highlights()
        except Exception:
            pass

        ax = getattr(self, "_map_ax", None)
        pos = getattr(self, "_map_pos", None)
        if ax is None or not pos or node_name not in pos:
            return

        x, y = pos[node_name]
        try:
            self._annotate_node(ax, node_name, x, y)
        except Exception:
            try:
                ax.plot([x], [y], marker="o", markersize=10)
                ax.text(x, y, node_name, fontsize=9)
            except Exception:
                pass

        try:
            canvas = getattr(self, "_map_canvas", None)
            if canvas is not None:
                canvas.draw_idle()
        except Exception:
            pass

    # ------------------------------------------------------------
    # Main entry
    # ------------------------------------------------------------
    def show(self) -> None:
        ax, fig, canvas = self._ensure_axes_and_canvas()

        nodes_all = self._collect_all_nodes(self.env)

        geo: Dict[str, Tuple[float, float]] = {}
        if hasattr(self.env, "geo_lookup"):
            try:
                geo = self.env.geo_lookup() or {}
            except Exception:
                geo = {}

        print("[WORLD-MAP] geo_lookup keys sample:", list(geo.keys())[:20])
        print("[WORLD-MAP] nodes_all sample:", list(nodes_all.keys())[:20])

        used_cartopy, data_crs, ax = self._setup_background(ax, fig)

        pos, missing_geo = self._draw_nodes(
            ax, nodes_all, geo, used_cartopy=used_cartopy, data_crs=data_crs
        )
        if missing_geo:
            print(f"[WORLD-MAP] missing geo for nodes (first 20): {missing_geo[:20]}")

        all_edges = self._collect_all_edges(self.env)
        highlight_edges_ot, highlight_edges_in, selected_names = (
            self._collect_highlight_edges(self.env, self.product_name)
        )

        self._draw_edges(
            ax,
            pos,
            all_edges=all_edges,
            highlight_edges_ot=highlight_edges_ot,
            highlight_edges_in=highlight_edges_in,
            used_cartopy=used_cartopy,
            data_crs=data_crs,
        )

        self._draw_decluttered_labels(
            ax,
            pos,
            used_cartopy=used_cartopy,
            data_crs=data_crs,
        )

        self._auto_fit(ax, pos, selected_names, used_cartopy=used_cartopy, data_crs=data_crs)
        self._draw_legend(ax)

        # ---- state save ----
        self._disconnect_events()
        self.state.ax = ax
        self.state.fig = fig
        self.state.canvas = canvas
        self.state.used_cartopy = used_cartopy
        self.state.data_crs = data_crs
        self.state.pos = pos
        self.state.nodes = nodes_all
        self.state.all_edges = list(all_edges)
        self.state.high_edges = list(highlight_edges_ot | highlight_edges_in)

        # legacy compat
        self._map_ax = ax
        self._map_canvas = canvas
        self._map_used_cartopy = used_cartopy
        self._map_data_crs = data_crs
        self._map_pos = pos
        self._map_nodes = nodes_all
        self._map_high_edges = list(highlight_edges_ot | highlight_edges_in)
        self._map_edges_all = list(all_edges)

        # [FIX-3] _connect_base_events registers scroll + key already.
        # _install_map_interactions must NOT re-register those events.
        self._connect_base_events()
        self._install_map_interactions()

        if canvas is not None:
            try:
                canvas.draw_idle()
            except Exception:
                pass
        else:
            plt.show(block=False)

    # ------------------------------------------------------------
    # Canvas / Axes
    # ------------------------------------------------------------
    def _ensure_axes_and_canvas(self):
        fig, ax = plt.subplots(figsize=(11, 6), dpi=110)
        try:
            fig.canvas.manager.set_window_title(self.title)
        except Exception:
            pass
        canvas = fig.canvas

        if self.parent_tk is not None:
            try:
                import tkinter as tk
                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

                top = tk.Toplevel(self.parent_tk)
                top.title(self.title)
                top.geometry("1200x700")
                tk_canvas = FigureCanvasTkAgg(fig, master=top)
                tk_canvas.draw()
                tk_canvas.get_tk_widget().pack(fill="both", expand=True)
                canvas = tk_canvas
            except Exception as e:
                print(f"[WORLD-MAP] Tk embedding failed, fallback to plt.show(): {e}")

        return ax, fig, canvas

    # ------------------------------------------------------------
    # Data collection
    # ------------------------------------------------------------
    def _geo_lookup(self, env) -> Dict[str, Tuple[float, float]]:
        GEO: Dict[str, Tuple[float, float]] = {}

        if hasattr(env, "geo_lookup") and callable(getattr(env, "geo_lookup")):
            try:
                GEO = env.geo_lookup() or {}
            except Exception as e:
                print(f"[WORLD-MAP] env.geo_lookup() failed: {e}")
                GEO = {}
        else:
            print("[WORLD-MAP] env.geo_lookup() not found. Fallback to CSV.")

        if not GEO:
            GEO = _geo_lookup_from_csv(env)

        try:
            print("[WORLD-MAP] data_dir resolved:", _resolve_data_dir(env))
            print("[WORLD-MAP] geo_lookup size:", len(GEO))
        except Exception:
            pass

        return GEO

    def _collect_all_nodes(self, env) -> Dict[str, Any]:
        nodes_all: Dict[str, Any] = {}

        if getattr(env, "prod_tree_dict_OT", None):
            for _prod, _root in env.prod_tree_dict_OT.items():
                for n in self._walk_nodes(_root):
                    name = getattr(n, "name", None)
                    if name:
                        nodes_all[name] = n

        if getattr(env, "prod_tree_dict_IN", None):
            for _prod, _root in env.prod_tree_dict_IN.items():
                for n in self._walk_nodes(_root):
                    name = getattr(n, "name", None)
                    if name:
                        nodes_all[name] = n

        if not nodes_all:
            nodes_out = getattr(env, "nodes_outbound", {}) or {}
            nodes_in = getattr(env, "nodes_inbound", {}) or {}
            nodes_all = {**nodes_out, **nodes_in}

        return nodes_all

    def _collect_all_edges(self, env) -> set[Tuple[str, str]]:
        all_edges: set[Tuple[str, str]] = set()

        G = getattr(env, "G", None)
        if G is not None and hasattr(G, "edges"):
            try:
                return set(G.edges())
            except Exception:
                pass

        if getattr(env, "prod_tree_dict_OT", None):
            for _prod, _root in env.prod_tree_dict_OT.items():
                for p, c in self._iter_parent_child(_root):
                    all_edges.add(
                        (getattr(p, "name", "") or "", getattr(c, "name", "") or "")
                    )

        if getattr(env, "prod_tree_dict_IN", None):
            for _prod, _root in env.prod_tree_dict_IN.items():
                for p, c in self._iter_parent_child(_root):
                    all_edges.add(
                        (getattr(p, "name", "") or "", getattr(c, "name", "") or "")
                    )

        return all_edges

    def _collect_highlight_edges(self, env, product_name: str | None):
        highlight_edges_ot: set[Tuple[str, str]] = set()
        highlight_edges_in: set[Tuple[str, str]] = set()
        selected_names: set[str] = set()

        if not product_name:
            return highlight_edges_ot, highlight_edges_in, selected_names

        root_ot = (
            (getattr(env, "prod_tree_dict_OT", {}) or {}).get(product_name)
            if getattr(env, "prod_tree_dict_OT", None)
            else None
        )
        if root_ot:
            for p, c in self._iter_parent_child(root_ot):
                highlight_edges_ot.add(
                    (getattr(p, "name", "") or "", getattr(c, "name", "") or "")
                )
            for n in self._walk_nodes(root_ot):
                nm = getattr(n, "name", None)
                if nm:
                    selected_names.add(nm)

        root_in = (
            (getattr(env, "prod_tree_dict_IN", {}) or {}).get(product_name)
            if getattr(env, "prod_tree_dict_IN", None)
            else None
        )
        if root_in:
            for p, c in self._iter_parent_child(root_in):
                highlight_edges_in.add(
                    (getattr(p, "name", "") or "", getattr(c, "name", "") or "")
                )
            for n in self._walk_nodes(root_in):
                nm = getattr(n, "name", None)
                if nm:
                    selected_names.add(nm)

        return highlight_edges_ot, highlight_edges_in, selected_names

    # ------------------------------------------------------------
    # Background / draw
    # ------------------------------------------------------------
    def _setup_background(self, ax, fig):
        used_cartopy = False
        data_crs = None

        ax.clear()
        ax.set_title(self.title, fontsize=12)

        try:
            import cartopy.crs as ccrs
            import cartopy.feature as cfeature

            fig = ax.figure
            ax.remove()
            proj_map = ccrs.PlateCarree(central_longitude=0)
            ax = fig.add_subplot(111, projection=proj_map)

            ax.add_feature(cfeature.OCEAN.with_scale("110m"), facecolor="#e6f2ff")
            ax.add_feature(cfeature.LAND.with_scale("110m"), facecolor="#f6f6f6")
            ax.add_feature(
                cfeature.COASTLINE.with_scale("110m"), linewidth=0.4, edgecolor="#555"
            )
            ax.add_feature(
                cfeature.BORDERS.with_scale("110m"), linewidth=0.4, edgecolor="#777"
            )
            ax.set_global()

            gl = ax.gridlines(
                draw_labels=True, linewidth=0.2, color="gray", alpha=0.5, linestyle="--"
            )
            gl.top_labels = gl.right_labels = False

            used_cartopy = True
            data_crs = ccrs.PlateCarree()
        except Exception:
            ax.set_xlim(-180, 180)
            ax.set_ylim(-90, 90)
            ax.set_facecolor("#e6f2ff")

        return used_cartopy, data_crs, ax

    def _draw_nodes(
        self,
        ax,
        nodes_all: Dict[str, Any],
        geo: Dict[str, Tuple[float, float]],
        *,
        used_cartopy: bool,
        data_crs,
    ):
        pos: Dict[str, Tuple[float, float]] = {}
        hub = {"sales_office", "procurement_office", "supply_point"}
        missing_geo: List[str] = []

        for name, node in nodes_all.items():
            g = geo.get(name)
            if not g:
                missing_geo.append(name)
                continue
            lat, lon = float(g[0]), float(g[1])
            x, y = lon, lat
            pos[name] = (x, y)

            color = "#1f77b4" if name not in hub else "#444444"
            ms = 15 if name not in hub else 30

            if used_cartopy and data_crs is not None:
                ax.plot(
                    x, y, "o", ms=max(ms, 12), mfc=color, alpha=0.15,
                    mec="none", transform=data_crs, zorder=3,
                )
                ax.plot(
                    x, y, "o", ms=7, mfc=color, mec="white", mew=0.8,
                    transform=data_crs, zorder=4,
                )
                #ax.text(x, y, f" {name}", fontsize=8, va="bottom",
                #        transform=data_crs, zorder=4)
            else:
                ax.plot(
                    x, y, "o", ms=max(ms, 12), mfc=color, alpha=0.15,
                    mec="none", zorder=3,
                )
                ax.plot(x, y, "o", ms=7, mfc=color, mec="white", mew=0.8, zorder=4)
                #ax.text(x, y, f" {name}", fontsize=8, va="bottom", zorder=4)

        return pos, missing_geo

    def _wrap_proj_x(self, x: float) -> float:
        return ((float(x) + 180.0) % 360.0) - 180.0

    def _normalize_proj_extent(self, xmin: float, xmax: float):
        width = float(xmax) - float(xmin)
        cx = 0.5 * (float(xmin) + float(xmax))
        cx = self._wrap_proj_x(cx)
        return cx - width / 2.0, cx + width / 2.0

    def _project_xy(self, lon: float, lat: float):
        ax = getattr(self, "_map_ax", None)
        data_crs = getattr(self, "_map_data_crs", None)
        if ax is None or data_crs is None:
            return float(lon), float(lat)
        try:
            map_crs = ax.projection
            x, y = map_crs.transform_point(float(lon), float(lat), src_crs=data_crs)
            return float(x), float(y)
        except Exception:
            return float(lon), float(lat)

    def _draw_decluttered_labels(
        self,
        ax,
        pos: Dict[str, Tuple[float, float]],
        *,
        used_cartopy: bool,
        data_crs,
    ):
        if not pos:
            return

        map_crs = getattr(ax, "projection", None) if used_cartopy else None
        names = list(pos.keys())
        visited = set()
        clusters = []

        # cluster は projection 座標で行う
        proj_pos = {}
        for name, (lon, lat) in pos.items():
            if used_cartopy and data_crs is not None and map_crs is not None:
                proj_pos[name] = self._project_xy(lon, lat)
            else:
                proj_pos[name] = (lon, lat)

        x_thr = 0.6
        y_thr = 0.6

        for name in names:
            if name in visited:
                continue

            x0, y0 = proj_pos[name]
            cluster = [name]
            visited.add(name)

            for other in names:
                if other in visited:
                    continue
                x1, y1 = proj_pos[other]
                if abs(x1 - x0) <= x_thr and abs(y1 - y0) <= y_thr:
                    cluster.append(other)
                    visited.add(other)

            clusters.append(cluster)

        for cluster in clusters:
            if len(cluster) == 1:
                name = cluster[0]
                lon, lat = pos[name]
                if used_cartopy and data_crs is not None:
                    ax.text(
                        lon, lat, f" {name}",
                        fontsize=8, va="bottom",
                        transform=data_crs, zorder=6,
                    )
                else:
                    ax.text(lon, lat, f" {name}", fontsize=8, va="bottom", zorder=6)
                continue

            pts = [proj_pos[n] for n in cluster]
            anchor_x = max(p[0] for p in pts) + 0.25
            anchor_y = sum(p[1] for p in pts) / len(pts)

            cluster_sorted = sorted(cluster)
            step = 0.18
            start_y = anchor_y + step * (len(cluster_sorted) - 1) / 2.0

            for i, name in enumerate(cluster_sorted):
                x, y = proj_pos[name]
                lx = anchor_x
                ly = start_y - i * step

                if used_cartopy and map_crs is not None:
                    ax.plot(
                        [x, lx], [y, ly],
                        color="#666666", lw=0.5, alpha=0.7,
                        transform=map_crs, zorder=5,
                    )
                    ax.text(
                        lx, ly, name,
                        fontsize=8, va="center", ha="left",
                        bbox=dict(fc="white", ec="none", alpha=0.6, pad=0.2),
                        transform=map_crs, zorder=6,
                    )
                else:
                    ax.plot([x, lx], [y, ly], color="#666666", lw=0.5, alpha=0.7, zorder=5)
                    ax.text(
                        lx, ly, name,
                        fontsize=8, va="center", ha="left",
                        bbox=dict(fc="white", ec="none", alpha=0.6, pad=0.2),
                        zorder=6,
                    )

    def _draw_edges(
        self,
        ax,
        pos: Dict[str, Tuple[float, float]],
        *,
        all_edges: set[Tuple[str, str]],
        highlight_edges_ot: set[Tuple[str, str]],
        highlight_edges_in: set[Tuple[str, str]],
        used_cartopy: bool,
        data_crs,
    ):
        try:
            import cartopy.crs as ccrs
        except Exception:
            ccrs = None

        def _seg(u: str, v: str, color: str, lw: float, *, arrow: bool = False, z: int = 3):
            if u not in pos or v not in pos:
                return
            x1, y1 = pos[u]
            x2, y2 = pos[v]
            if used_cartopy and ccrs is not None:
                ax.plot(
                    [x1, x2], [y1, y2], color=color, lw=lw, alpha=0.8,
                    transform=ccrs.Geodetic(), zorder=z,
                )
                if arrow and data_crs is not None:
                    ax.plot(x2, y2, marker=">", color=color, ms=6,
                            transform=data_crs, zorder=z + 1)
            else:
                ax.plot([x1, x2], [y1, y2], color=color, lw=lw, alpha=0.8, zorder=z)
                if arrow:
                    ax.plot(x2, y2, marker=">", color=color, ms=6, zorder=z + 1)

        for u, v in all_edges:
            _seg(u, v, "#cccccc", 1.0, arrow=False, z=3)

        for u, v in highlight_edges_ot:
            _seg(u, v, "royalblue", 2.2, arrow=True, z=5)

        for u, v in highlight_edges_in:
            _seg(v, u, "seagreen", 2.2, arrow=True, z=5)

    # [FIX-1] _auto_fit was defined 3 times; only the final (correct) version is kept.
    def _auto_fit(
        self,
        ax,
        pos: Dict[str, Tuple[float, float]],
        selected_names: set[str],
        *,
        used_cartopy: bool,
        data_crs=None,
    ):
        fit = bool(getattr(self, "world_map_fit", True))
        if not pos:
            return

        fit_keys = [k for k in selected_names if k in pos] or list(pos.keys())
        lons = [float(pos[k][0]) for k in fit_keys]
        lats = [float(pos[k][1]) for k in fit_keys]
        if not lons or not lats:
            return

        lat_min, lat_max = min(lats), max(lats)
        lat_span = max(1e-6, lat_max - lat_min)

        # Determine minimum bounding longitude interval (handles antimeridian)
        lons360 = sorted(((lon % 360.0) + 360.0) % 360.0 for lon in lons)

        if len(lons360) == 1:
            lon_min360 = lon_max360 = lons360[0]
        else:
            gaps = [(lons360[i + 1] - lons360[i], i) for i in range(len(lons360) - 1)]
            gaps.append(((lons360[0] + 360.0) - lons360[-1], len(lons360) - 1))
            gap, idx = max(gaps, key=lambda t: t[0])
            start = lons360[(idx + 1) % len(lons360)]
            end = lons360[idx]
            if end < start:
                end += 360.0
            lon_min360, lon_max360 = start, end

        lon_span = max(1e-6, lon_max360 - lon_min360)
        lon_pad = max(5.0, lon_span * 0.08)
        lat_pad = max(3.0, lat_span * 0.10)

        # Avoid flat "band" display when coverage is near-global
        if used_cartopy and lon_span > 220.0:
            try:
                ax.set_global()
            except Exception:
                pass
            return

        # Aspect correction: widen lat range if the view would be too squashed
        if used_cartopy:
            try:
                bbox = ax.get_window_extent()
                aspect = float(bbox.width) / max(1.0, float(bbox.height))
            except Exception:
                aspect = 16.0 / 9.0

            target_lat_span = (lon_span + 2 * lon_pad) / max(0.5, aspect)
            cur_lat_span = lat_span + 2 * lat_pad
            if cur_lat_span < target_lat_span:
                lat_pad += (target_lat_span - cur_lat_span) / 2.0

        if not fit:
            if used_cartopy:
                try:
                    ax.set_global()
                except Exception:
                    pass
            else:
                ax.set_xlim(-180, 180)
                ax.set_ylim(-90, 90)
            return

        xmin = lon_min360 - lon_pad
        xmax = lon_max360 + lon_pad
        ymin = max(-89.5, lat_min - lat_pad)
        ymax = min(89.5, lat_max + lat_pad)

        if used_cartopy:
            try:
                # [FIX-5] Always supply lon/lat extent with crs=data_crs (PlateCarree).
                ax.set_extent([xmin, xmax, ymin, ymax], crs=data_crs)
            except Exception:
                pass
        else:
            def _to180(v):
                return ((v + 180.0) % 360.0) - 180.0

            ax.set_xlim(_to180(xmin), _to180(xmax))
            ax.set_ylim(ymin, ymax)

    def _draw_legend(self, ax):
        ax.plot([], [], color="#cccccc", lw=1.2, label="All edges")
        ax.plot([], [], color="royalblue", lw=2.2, label="Outbound (product)")
        ax.plot([], [], color="seagreen", lw=2.2, label="Inbound (product)")
        ax.legend(loc="lower left", fontsize=8)

    # ------------------------------------------------------------
    # Event wiring
    # ------------------------------------------------------------
    def _disconnect_events(self):
        if not self.state.canvas or not self.state.cids:
            return
        try:
            canvas = self.state.canvas
            if hasattr(canvas, "mpl_disconnect"):
                for cid in list(self.state.cids):
                    canvas.mpl_disconnect(cid)
        except Exception:
            pass
        self.state.cids = []

    def _connect_base_events(self):
        """Register scroll and key events ONCE. Click is resolved on release."""
        if not self.state.canvas:
            return
        canvas = self.state.canvas
        if hasattr(canvas, "mpl_connect"):
            self.state.cids = [
                canvas.mpl_connect("scroll_event", self._on_map_scroll),
                #@STOP
                #canvas.mpl_connect("button_press_event", self._on_map_click),
                canvas.mpl_connect("key_press_event", self._on_map_key),
            ]

    # [FIX-3] Removed scroll_event and key_press_event registrations; they are
    # already done in _connect_base_events.  Only pan (press/release/motion) is
    # wired here so there is no double-firing.
    def _install_map_interactions(self):
        canvas = getattr(self, "_map_canvas", None) or getattr(self.state, "canvas", None)
        if canvas is None:
            return

        for cid in getattr(self, "_map_pan_zoom_cids", []):
            try:
                canvas.mpl_disconnect(cid)
            except Exception:
                pass

        #@STOP
        #self._map_pan_state = {"dragging": False, "last_pos": None}
        self._map_pan_state = {
            "pressed": False,
            "dragging": False,
            "last_pos": None,
            "press_pixel": None,
        }

        # [FIX-3] Only press/release/motion — scroll & key handled by _connect_base_events
        self._map_pan_zoom_cids = [
            canvas.mpl_connect("button_press_event", self._on_map_press),
            canvas.mpl_connect("button_release_event", self._on_map_release),
            canvas.mpl_connect("motion_notify_event", self._on_map_motion),
        ]

    # ------------------------------------------------------------
    # Click handler
    # ------------------------------------------------------------
    def _on_map_click(self, event):
        ax = self.state.ax
        if ax is None or getattr(event, "inaxes", None) is not ax:
            return

        pair = self._event_lonlat(event)
        if not pair:
            self._clear_map_highlights()
            return
        x, y = pair

        pos = self.state.pos or {}
        if not pos:
            return

        used_cartopy = bool(self.state.used_cartopy)
        data_crs = self.state.data_crs


        hit_radius_km = self._click_hit_radius_km()
        hit = None
        best_km = 1e18


        for name, (lon, lat) in pos.items():

            d_km = self._haversine_km(x, y, lon, lat)
            if d_km < best_km:
                hit = name
                best_km = d_km

        if hit is None or best_km > hit_radius_km:
            self._clear_map_highlights()
            return

        self._clear_map_highlights()

        node = (self.state.nodes or {}).get(hit)
        info = hit
        if node is not None:
            rows = []
            for k in ("lat", "lon", "node_type", "capacity", "cost_coeff", "revenue_coeff"):
                if hasattr(node, k):
                    rows.append(f"{k}: {getattr(node, k)}")
            if rows:
                info = hit + "\n" + "\n".join(rows)

        if used_cartopy and data_crs is not None:
            anno = ax.annotate(
                info,
                xy=pos[hit],
                xytext=(6, 6),
                textcoords="offset points",
                fontsize=9,
                bbox=dict(boxstyle="round", fc="w", ec="#333", alpha=0.9),
                transform=data_crs,
                zorder=10,
            )
            (ring,) = ax.plot(
                [pos[hit][0]], [pos[hit][1]],
                "o", ms=18, mfc="none", mec="red", mew=2,
                alpha=0.7, transform=data_crs, zorder=9,
            )
        else:
            anno = ax.annotate(
                info,
                xy=pos[hit],
                xytext=(6, 6),
                textcoords="offset points",
                fontsize=9,
                bbox=dict(boxstyle="round", fc="w", ec="#333", alpha=0.9),
                zorder=10,
            )
            (ring,) = ax.plot(
                [pos[hit][0]], [pos[hit][1]],
                "o", ms=18, mfc="none", mec="red", mew=2,
                alpha=0.7, zorder=9,
            )

        self.state.anno_artist = anno
        self.state.highlight_artists = [ring, anno]

        if self.state.canvas is not None:
            try:
                self.state.canvas.draw_idle()
            except Exception:
                pass

        cb = getattr(self, "_map_on_select", None)
        if callable(cb):
            try:
                cb(hit, source="world_map")
            except TypeError:
                cb(hit)

        # center selected node in the current view
        try:
            hit_lon, hit_lat = pos[hit]
            self._center_map_on(hit_lon, hit_lat)
        except Exception:
            pass


    # ------------------------------------------------------------
    # Pan / Zoom handlers
    # ------------------------------------------------------------
    def _event_lonlat(self, event) -> Optional[Tuple[float, float]]:
        x = getattr(event, "xdata", None)
        y = getattr(event, "ydata", None)
        if x is None or y is None:
            return None

        used_cartopy = bool(getattr(self.state, "used_cartopy", False))
        data_crs = getattr(self.state, "data_crs", None)
        ax = getattr(self.state, "ax", None)

        if used_cartopy and data_crs is not None and ax is not None:
            try:
                map_crs = ax.projection
                lon, lat = data_crs.transform_point(float(x), float(y), src_crs=map_crs)
                return float(lon), float(lat)
            except Exception:
                return None

        return float(x), float(y)

    def _haversine_km(self, lon1, lat1, lon2, lat2):
        import math

        r = 6371.0
        lon1 = math.radians(float(lon1))
        lat1 = math.radians(float(lat1))
        lon2 = math.radians(float(lon2))
        lat2 = math.radians(float(lat2))

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = (
            math.sin(dlat / 2.0) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(1e-12, 1.0 - a)))
        return r * c

    def _click_hit_radius_km(self):
        # まずは固定半径100kmで安定させる
        return 100.0


    def _on_map_press(self, event):
        ax = getattr(self, "_map_ax", None)
        if ax is None or event.inaxes is not ax or event.xdata is None or event.ydata is None:
            return


        # left-click: start press, drag is decided by movement threshold
        if event.button == 1:
            self._map_pan_state["pressed"] = True
            self._map_pan_state["dragging"] = False
            self._map_pan_state["last_pos"] = (event.xdata, event.ydata)

            self._map_pan_state["press_pixel"] = (event.x, event.y)

            try:
                self._clear_map_highlights()
            except Exception:
                pass

    # [FIX-6] Removed references to legacy _map_panning / _set_map_cursor.
    def _on_map_release(self, event):

        pan = getattr(self, "_map_pan_state", {})
        if event.button != 1:
            return

        was_dragging = bool(pan.get("dragging"))
        # treat as click only if drag did not start
        if pan.get("pressed") and not was_dragging:
            try:
                self._on_map_click(event)
            except Exception:
                pass

        pan["pressed"] = False
        pan["dragging"] = False
        pan["last_pos"] = None
        pan["press_pixel"] = None

        canvas = self.state.canvas
        if canvas is not None:
            try:
                canvas.draw_idle()
            except Exception:
                pass


    def _on_map_motion(self, event):
        ax = getattr(self, "_map_ax", None)
        pan = getattr(self, "_map_pan_state", {})
        if (
            not pan.get("pressed")
            or event.inaxes is not ax
            or event.xdata is None
            or event.ydata is None
        ):
            return

        # start dragging only after threshold to avoid hand-shake misclassification
        if not pan.get("dragging"):
            px0, py0 = pan.get("press_pixel") or (None, None)
            if px0 is None or py0 is None or event.x is None or event.y is None:
                return

            dx_pix = event.x - px0
            dy_pix = event.y - py0
            if (dx_pix * dx_pix + dy_pix * dy_pix) < (self._map_drag_threshold ** 2):
                return

            pan["dragging"] = True


        last_x, last_y = pan["last_pos"]
        dx = float(event.xdata) - float(last_x)
        dy = float(event.ydata) - float(last_y)

        used_cartopy = getattr(self, "_map_used_cartopy", False)

        if used_cartopy:
            try:
                map_crs = ax.projection
                xmin, xmax, ymin, ymax = ax.get_extent(crs=map_crs)

                new_xmin = xmin - dx
                new_xmax = xmax - dx
                new_ymin = max(-90.0, min(90.0, ymin - dy))
                new_ymax = max(-90.0, min(90.0, ymax - dy))
                # NOTE: _normalize_proj_extent を削除 → 経度ラップをしないことで左右無限パンを許可

                if new_xmin >= new_xmax or new_ymin >= new_ymax:
                    return

                ax.set_extent([new_xmin, new_xmax, new_ymin, new_ymax], crs=map_crs)
                ax.set_aspect("auto")
            except Exception:
                pass
        else:
            xmin, xmax = ax.get_xlim()
            ymin, ymax = ax.get_ylim()
            ax.set_xlim(xmin - dx, xmax - dx)
            ax.set_ylim(ymin - dy, ymax - dy)

        pan["last_pos"] = (event.xdata, event.ydata)

        now = time.monotonic()
        if (now - getattr(self, "_map_last_draw_ts", 0.0)) >= self._map_redraw_interval:
            self._map_last_draw_ts = now
            canvas = self.state.canvas
            if canvas is not None:
                try:
                    canvas.draw_idle()
                except Exception:
                    pass



    # [FIX-2] Changed canvas reference from self.canvas_network to self.state.canvas.
    def _on_map_scroll(self, event):
        ax = getattr(self, "_map_ax", None)
        if ax is None or event.inaxes is not ax or event.xdata is None or event.ydata is None:
            return

        base_scale = 1.2
        if event.button == "up":
            scale_factor = 1.0 / base_scale
        elif event.button == "down":
            scale_factor = base_scale
        else:
            return

        used_cartopy = getattr(self, "_map_used_cartopy", False)

        if used_cartopy:
            try:
                map_crs = ax.projection
                xmin, xmax, ymin, ymax = ax.get_extent(crs=map_crs)
                cx, cy = float(event.xdata), float(event.ydata)
            except Exception:
                return
        else:
            xmin, xmax = ax.get_xlim()
            ymin, ymax = ax.get_ylim()
            cx, cy = float(event.xdata), float(event.ydata)

        new_xmin = cx + (xmin - cx) * scale_factor
        new_xmax = cx + (xmax - cx) * scale_factor
        new_ymin = cy + (ymin - cy) * scale_factor
        new_ymax = cy + (ymax - cy) * scale_factor

        if used_cartopy:
            new_ymin = max(-90.0, min(90.0, new_ymin))
            new_ymax = max(-90.0, min(90.0, new_ymax))
            # NOTE: _normalize_proj_extent を削除 → 経度ラップをしないことで左右無限パンを許可

            # 最小表示幅を保証
            min_x_span = 1.0
            min_y_span = 1.0

            if (new_xmax - new_xmin) < min_x_span:
                mid = 0.5 * (new_xmin + new_xmax)
                new_xmin = mid - min_x_span / 2.0
                new_xmax = mid + min_x_span / 2.0
                new_xmin, new_xmax = self._normalize_proj_extent(new_xmin, new_xmax)

            if (new_ymax - new_ymin) < min_y_span:
                mid = 0.5 * (new_ymin + new_ymax)
                new_ymin = mid - min_y_span / 2.0
                new_ymax = mid + min_y_span / 2.0

            if new_xmin >= new_xmax or new_ymin >= new_ymax:
                return

            try:
                ax.set_extent([new_xmin, new_xmax, new_ymin, new_ymax], crs=map_crs)
                ax.set_aspect("auto")
            except Exception:
                pass
        else:
            ax.set_xlim(new_xmin, new_xmax)
            ax.set_ylim(new_ymin, new_ymax)

        canvas = self.state.canvas
        if canvas is not None:
            try:
                canvas.draw_idle()
            except Exception:
                pass

    def _center_map_on(self, lon: float, lat: float):
        ax = getattr(self, "_map_ax", None)
        if ax is None:
            return

        used_cartopy = getattr(self, "_map_used_cartopy", False)

        if used_cartopy:
            try:
                map_crs = ax.projection
                xmin, xmax, ymin, ymax = ax.get_extent(crs=map_crs)

                width = xmax - xmin
                height = ymax - ymin
                if width <= 0 or height <= 0:
                    return

                # クリック点を投影座標へ
                data_crs = getattr(self, "_map_data_crs", None)
                if data_crs is None:
                    return
                cx, cy = map_crs.transform_point(lon, lat, src_crs=data_crs)

                new_xmin = cx - width / 2.0
                new_xmax = cx + width / 2.0
                new_ymin = cy - height / 2.0
                new_ymax = cy + height / 2.0

                # NOTE: _normalize_proj_extent を削除 → 経度ラップをしないことで左右無限パンを許可
                new_ymin = max(-90.0, min(90.0, new_ymin))
                new_ymax = max(-90.0, min(90.0, new_ymax))

                if new_xmin >= new_xmax or new_ymin >= new_ymax:
                    return

                ax.set_extent([new_xmin, new_xmax, new_ymin, new_ymax], crs=map_crs)
                ax.set_aspect("auto")
            except Exception:
                return
        else:
            try:
                xmin, xmax = ax.get_xlim()
                ymin, ymax = ax.get_ylim()
                width = xmax - xmin
                height = ymax - ymin
                ax.set_xlim(lon - width / 2.0, lon + width / 2.0)
                ax.set_ylim(lat - height / 2.0, lat + height / 2.0)
            except Exception:
                return

        canvas = self.state.canvas
        if canvas is not None:
            try:
                canvas.draw_idle()
            except Exception:
                pass

    # [FIX-4] Removed duplicate local _fit_lonlat definitions from inside this
    # method.  self._fit_lonlat (the class method below) is called directly.
    def _on_map_key(self, event):
        """f=selected product fit, a=all nodes, w=world, esc=clear highlights"""
        if event.key == "escape":
            self._clear_map_highlights()
            return

        ax = getattr(self, "_map_ax", None)
        if ax is None:
            return

        used_cartopy = getattr(self, "_map_used_cartopy", False)
        pos = getattr(self, "_map_pos", {})
        highlight_edges = getattr(self, "_map_high_edges", [])

        if event.key == "a":
            if pos:
                all_lons = [p[0] for p in pos.values()]
                all_lats = [p[1] for p in pos.values()]
                self._fit_lonlat(all_lons, all_lats, edges=None)

        elif event.key == "w":
            if used_cartopy:
                try:
                    ax.set_global()
                except Exception:
                    pass
            else:
                ax.set_xlim(-180, 180)
                ax.set_ylim(-90, 90)

        elif event.key == "f":
            nodes = set(u for u, v in highlight_edges) | set(v for u, v in highlight_edges)
            if nodes:
                lons = [pos[n][0] for n in nodes if n in pos]
                lats = [pos[n][1] for n in nodes if n in pos]
                if lons and lats:
                    self._fit_lonlat(lons, lats, edges=highlight_edges)

        canvas = self.state.canvas
        if canvas is not None:
            try:
                canvas.draw_idle()
            except Exception:
                pass

    # [FIX-5] _fit_lonlat: set_extent now correctly passes lon/lat extents with
    # crs=data_crs (PlateCarree) instead of projection coordinates with crs=map_crs.
    def _fit_lonlat(self, lons: Sequence[float], lats: Sequence[float], edges=None):
        """
        Fit the view so all given lon/lat points are visible.

        Horizontal focus:
          - If edges are given, the 'from' nodes are placed near the left 5% of
            the viewport.
          - Otherwise the easternmost-minimum (0-360) node is used as focal point.

        Vertical extent is filled to the axes aspect ratio.
        """
        import numpy as np

        ax = getattr(self, "_map_ax", None)
        used_cartopy = getattr(self, "_map_used_cartopy", False)
        data_crs = getattr(self, "_map_data_crs", None)

        if ax is None or not lons or not lats:
            return

        pos = getattr(self, "_map_pos", {})

        def _min_east_positive(lon_list):
            if not lon_list:
                return None
            arr = np.asarray(lon_list, dtype=float)
            arr360 = (arr + 360.0) % 360.0
            return float(arr[int(np.argmin(arr360))])

        # Choose focal longitude
        focal_candidates: List[float] = []
        if edges:
            from_nodes = {u for u, _v in edges}
            focal_candidates = [pos[n][0] for n in from_nodes if n in pos]
        focal_lon = _min_east_positive(focal_candidates) or _min_east_positive(list(lons))

        lat_min = float(np.min(lats))
        lat_max = float(np.max(lats))
        if not (np.isfinite(lat_min) and np.isfinite(lat_max)):
            return
        if np.isclose(lat_min, lat_max):
            lat_max = lat_min + 1.0
        lat_min = max(-89.0, lat_min)
        lat_max = min(89.0, lat_max)

        try:
            bbox = ax.get_window_extent()
            axes_aspect = float(bbox.width) / float(bbox.height)
        except Exception:
            axes_aspect = 4.0 / 3.0

        if used_cartopy and data_crs is not None:
            try:
                map_crs = ax.projection
                pts = map_crs.transform_points(
                    data_crs,
                    np.array([focal_lon, focal_lon], dtype=float),
                    np.array([lat_min, lat_max], dtype=float),
                )
                proj_y0 = float(min(pts[0, 1], pts[1, 1]))
                proj_y1 = float(max(pts[0, 1], pts[1, 1]))
                proj_y_span = proj_y1 - proj_y0
                proj_x_span = proj_y_span * axes_aspect
                proj_focal_x = float(pts[0, 0])

                LEFT_FRAC = 0.05
                proj_x0 = proj_focal_x - proj_x_span * LEFT_FRAC
                proj_x1 = proj_focal_x + proj_x_span * (1.0 - LEFT_FRAC)

                pad_y = proj_y_span * 0.05
                proj_y0 -= pad_y
                proj_y1 += pad_y

                # [FIX-5] Convert back to lon/lat so set_extent receives geographic
                # coordinates consistent with crs=data_crs (PlateCarree).
                corners = data_crs.transform_points(
                    map_crs,
                    np.array([proj_x0, proj_x1], dtype=float),
                    np.array([proj_y0, proj_y1], dtype=float),
                )
                extent_lon_min = float(corners[0, 0])
                extent_lon_max = float(corners[1, 0])
                extent_lat_min = float(corners[0, 1])
                extent_lat_max = float(corners[1, 1])

                ax.set_extent(
                    [extent_lon_min, extent_lon_max, extent_lat_min, extent_lat_max],
                    crs=data_crs,
                )
            except Exception as e:
                print(f"[WORLD-MAP] _fit_lonlat cartopy path failed: {e}")
        else:
            # Plain matplotlib axes
            lon_span = max(1.0, float(np.max(lons)) - float(np.min(lons)))
            lat_span = lat_max - lat_min
            target_lon_span = lat_span * axes_aspect
            lon_pad = max(5.0, (target_lon_span - lon_span) / 2.0)
            ax.set_xlim(focal_lon - lon_span * 0.05 - lon_pad,
                        focal_lon + lon_span * 0.95 + lon_pad)
            ax.set_ylim(lat_min - lat_span * 0.05, lat_max + lat_span * 0.05)

        canvas = self.state.canvas
        if canvas is not None:
            try:
                canvas.draw_idle()
            except Exception:
                pass

    # ------------------------------------------------------------
    # Highlight management
    # ------------------------------------------------------------
    def _clear_map_highlights(self):
        if self.state.highlight_artists:
            for a in list(self.state.highlight_artists):
                try:
                    a.remove()
                except Exception:
                    pass
        self.state.highlight_artists = []
        self.state.anno_artist = None
        if self.state.canvas is not None:
            try:
                self.state.canvas.draw_idle()
            except Exception:
                pass

    # ------------------------------------------------------------
    # Tree traversal helpers
    # ------------------------------------------------------------
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
            children = getattr(n, "children", None) or []
            for c in children:
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
            children = getattr(p, "children", None) or []
            for c in children:
                out.append((p, c))
                stack.append(c)
        return out

    # ---- stubs (implement if needed) ----
    def _collect_geo_points(self):
        raise NotImplementedError

    def _apply_world_limits(self, ax, pts, mode: str):
        raise NotImplementedError