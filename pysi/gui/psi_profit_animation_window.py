# pysi/gui/psi_profit_animation_window.py 確定版

"""
psi_profit_animation_window.py

WOM 用の Tk + matplotlib 別Window版
- PSI累計グラフ
- 利益率推移
- 1 week = 1 sec animation

adapter 側が返す FrameData をそのまま表示する。
本ファイルは「表示責務」に限定する。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass
from typing import Optional, List, Sequence

import matplotlib
matplotlib.use("TkAgg")

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation


# ============================================================
# Data model
# ============================================================

@dataclass
class FrameData:
    """
    単一フレーム分の描画データ。
    x 軸は週次 bucket を想定。
    """

    week_labels: List[str]

    # 左軸: PSI accumulated / PSI components
    supply_accume: List[float]
    supply_I: List[float]
    supply_P: List[float]

    demand_accume: List[float]
    demand_CO: List[float]
    demand_S: List[float]

    # 右軸
    profit_ratio: List[float]

    # 追加: business weekly series
    weekly_revenue: Optional[List[float]] = None
    weekly_profit: Optional[List[float]] = None

    # optional meta
    title_suffix: str = ""
    total_profit: Optional[float] = None
    total_revenue: Optional[float] = None


class BasePSIProfitDataProvider:
    """
    Adapter 側が実装する provider 基底。
    """

    def get_total_frames(self) -> int:
        raise NotImplementedError

    def get_frame(self, frame_index: int) -> FrameData:
        raise NotImplementedError


# ============================================================
# Sample provider (standalone test用)
# ============================================================

class SamplePSIProfitDataProvider(BasePSIProfitDataProvider):
    def __init__(self, total_frames: int = 20, total_weeks: int = 16) -> None:
        self.total_frames = total_frames
        self.total_weeks = total_weeks

    def get_total_frames(self) -> int:
        return self.total_frames

    def get_frame(self, frame_index: int) -> FrameData:
        weeks = [f"W{w+1}" for w in range(self.total_weeks)]

        supply_p = [max(0, min(20, frame_index + w - 2)) for w in range(self.total_weeks)]
        supply_i = [max(0, (frame_index * 2 + w * 3) % 25) for w in range(self.total_weeks)]

        supply_accume: List[float] = []
        ssum = 0.0
        for v in supply_p:
            ssum += v
            supply_accume.append(ssum)

        demand_s = [max(0, min(18, frame_index + w - 5)) for w in range(self.total_weeks)]
        demand_co = [max(0, (frame_index + w * 2) % 10) for w in range(self.total_weeks)]

        demand_accume: List[float] = []
        dsum = 0.0
        for v in demand_s:
            dsum += v
            demand_accume.append(dsum)

        weekly_revenue = [300 + w * 25 for w in range(self.total_weeks)]
        weekly_profit = [-120 + (frame_index * 8) + (w * 18) for w in range(self.total_weeks)]

        profit_ratio: List[float] = []
        for r, p in zip(weekly_revenue, weekly_profit):
            if abs(r) < 1e-9:
                profit_ratio.append(0.0)
            else:
                profit_ratio.append((p / r) * 100.0)

        return FrameData(
            week_labels=weeks,
            supply_accume=supply_accume,
            supply_I=supply_i,
            supply_P=supply_p,
            demand_accume=demand_accume,
            demand_CO=demand_co,
            demand_S=demand_s,
            profit_ratio=profit_ratio,
            weekly_revenue=weekly_revenue,
            weekly_profit=weekly_profit,
            title_suffix=f"Frame={frame_index}",
            total_profit=sum(weekly_profit),
            total_revenue=sum(weekly_revenue),
        )


# ============================================================
# Helper calculations
# ============================================================

def _safe_sum(values: Sequence[float]) -> float:
    total = 0.0
    for v in values:
        try:
            total += float(v)
        except Exception:
            pass
    return total


def _first_non_negative_week(values: Sequence[float]) -> Optional[int]:
    for i, v in enumerate(values):
        try:
            if float(v) >= 0.0:
                return i + 1
        except Exception:
            pass
    return None


def _cumulative_series(values: Sequence[float]) -> List[float]:
    out: List[float] = []
    acc = 0.0
    for v in values:
        try:
            acc += float(v)
        except Exception:
            pass
        out.append(acc)
    return out


def _estimate_cumulative_profit_from_ratio(
    total_revenue: Optional[float],
    weekly_profit_ratio: Sequence[float],
) -> List[float]:
    """
    fallback用の簡易推計。
    weekly_profit が無い場合だけ使う。
    """
    W = max(1, len(weekly_profit_ratio))
    revenue_per_week = (total_revenue or 0.0) / W
    cumulative: List[float] = []
    acc = 0.0
    for r in weekly_profit_ratio:
        try:
            weekly_profit = revenue_per_week * (float(r) / 100.0)
        except Exception:
            weekly_profit = 0.0
        acc += weekly_profit
        cumulative.append(acc)
    return cumulative


def _first_cumulative_non_negative_week(
    weekly_profit: Optional[Sequence[float]],
    total_revenue: Optional[float],
    weekly_profit_ratio: Sequence[float],
) -> Optional[int]:
    """
    厳密版:
    - weekly_profit があればそれを優先
    - 無ければ従来の簡易推計に fallback
    """
    if weekly_profit is not None and len(weekly_profit) > 0:
        cum = _cumulative_series(weekly_profit)
        return _first_non_negative_week(cum)

    cum_est = _estimate_cumulative_profit_from_ratio(total_revenue, weekly_profit_ratio)
    return _first_non_negative_week(cum_est)


# ============================================================
# Main window
# ============================================================

class PSIProfitAnimationWindow(tk.Toplevel):
    """
    WOM 用の別Window。
    """

    def __init__(
        self,
        master: tk.Misc,
        data_provider: BasePSIProfitDataProvider,
        title: str = "WOM PSI Accumulated + Profit Ratio",
        node_id: Optional[str] = None,
        product_id: Optional[str] = None,
        interval_ms: int = 1000,  # 1 week = 1 sec
    ) -> None:
        super().__init__(master)

        self.title(title)
        self.geometry("1280x820")

        self.data_provider = data_provider
        self.node_id = node_id
        self.product_id = product_id
        self.interval_ms = interval_ms

        self.total_frames = max(1, self.data_provider.get_total_frames())
        self.current_frame = 0
        self.is_paused = False

        # full-frame baseline for fixed x-axis
        self.full_frame = self.data_provider.get_frame(self.total_frames - 1)
        self.full_week_labels = list(self.full_frame.week_labels)
        self.full_x = list(range(len(self.full_week_labels)))

        self._build_ui()
        self._build_animation()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------
    def _build_ui(self) -> None:
        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True)

        top_bar = ttk.Frame(outer)
        top_bar.pack(side="top", fill="x", padx=8, pady=8)

        ttk.Label(
            top_bar,
            text=f"Node: {self.node_id or '-'}    Product: {self.product_id or '-'}"
        ).pack(side="left", padx=4)

        ttk.Button(top_bar, text="Play", command=self.play).pack(side="left", padx=4)
        ttk.Button(top_bar, text="Pause", command=self.pause).pack(side="left", padx=4)
        ttk.Button(top_bar, text="Stop", command=self.stop).pack(side="left", padx=4)
        ttk.Button(top_bar, text="<< Prev", command=self.prev_frame).pack(side="left", padx=4)
        ttk.Button(top_bar, text="Next >>", command=self.next_frame).pack(side="left", padx=4)

        ttk.Label(top_bar, text="Speed").pack(side="left", padx=(20, 4))
        self.speed_var = tk.StringVar(value="1.0")
        speed_combo = ttk.Combobox(
            top_bar,
            textvariable=self.speed_var,
            width=8,
            state="readonly",
            values=["0.5", "1.0", "2.0"],
        )
        speed_combo.pack(side="left")
        speed_combo.bind("<<ComboboxSelected>>", self._on_speed_changed)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(top_bar, textvariable=self.status_var).pack(side="right", padx=4)

        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)

        chart_frame = ttk.Frame(body)
        chart_frame.pack(side="left", fill="both", expand=True)

        info_frame = ttk.LabelFrame(body, text="Management Summary")
        info_frame.pack(side="right", fill="y", padx=8, pady=8)

        self.info_text = tk.Text(info_frame, width=40, height=44)
        self.info_text.pack(fill="both", expand=True, padx=6, pady=6)

        self.figure = Figure(figsize=(10.8, 6.8), dpi=100)
        self.ax_left = self.figure.add_subplot(111)
        self.ax_right = self.ax_left.twinx()

        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True)

    # --------------------------------------------------------
    # Animation
    # --------------------------------------------------------
    def _build_animation(self) -> None:
        self.anim = FuncAnimation(
            self.figure,
            self._update_frame,
            frames=self.total_frames,
            interval=self.interval_ms,
            repeat=False,
            cache_frame_data=False,
        )

    def _update_frame(self, frame_index: int) -> None:
        if self.is_paused:
            return

        self.current_frame = frame_index % self.total_frames
        frame = self.data_provider.get_frame(self.current_frame)
        self._draw_frame(frame)
        self.status_var.set(f"Frame {self.current_frame + 1}/{self.total_frames}")
        self.canvas.draw_idle()

    # --------------------------------------------------------
    # Drawing
    # --------------------------------------------------------
    def _draw_frame_1st(self, frame: FrameData) -> None:
        self.ax_left.clear()
        self.ax_right.clear()

        x = list(range(len(frame.week_labels)))
        bar_width = 0.38

        # ----------------------------
        # 左軸: Supply side
        # ----------------------------
        self.ax_left.bar(
            [v - bar_width / 2 for v in x],
            frame.supply_accume,
            width=bar_width,
            label="Supply PSI Cum.",
            alpha=0.45,
        )
        self.ax_left.bar(
            [v - bar_width / 2 for v in x],
            frame.supply_I,
            width=bar_width,
            bottom=frame.supply_accume,
            label="Supply I (Inventory)",
            alpha=0.72,
        )
        self.ax_left.bar(
            [v - bar_width / 2 for v in x],
            frame.supply_P,
            width=bar_width,
            bottom=[a + b for a, b in zip(frame.supply_accume, frame.supply_I)],
            label="Supply P (Production/Purchase)",
            alpha=0.88,
        )

        # ----------------------------
        # 左軸: Demand side
        # ----------------------------
        self.ax_left.bar(
            [v + bar_width / 2 for v in x],
            frame.demand_accume,
            width=bar_width,
            label="Demand PSI Cum.",
            alpha=0.45,
        )
        self.ax_left.bar(
            [v + bar_width / 2 for v in x],
            frame.demand_CO,
            width=bar_width,
            bottom=frame.demand_accume,
            label="Demand CO (Carry Over)",
            alpha=0.72,
        )
        self.ax_left.bar(
            [v + bar_width / 2 for v in x],
            frame.demand_S,
            width=bar_width,
            bottom=[a + b for a, b in zip(frame.demand_accume, frame.demand_CO)],
            label="Demand S (Shipment/Sales)",
            alpha=0.88,
        )

        self.ax_left.set_xticks(x)
        self.ax_left.set_xticklabels(frame.week_labels, rotation=45)
        self.ax_left.set_ylabel("PSI Volume / Cumulative")
        self.ax_left.set_xlabel("Week")
        self.ax_left.grid(True, axis="y", alpha=0.28)

        # ----------------------------
        # タイトル
        # ----------------------------
        title_parts = ["WOM PSI Accumulated + Profit Ratio"]
        if self.product_id:
            title_parts.append(f"Product={self.product_id}")
        if self.node_id:
            title_parts.append(f"Node={self.node_id}")
        if frame.title_suffix:
            title_parts.append(frame.title_suffix)

        self.ax_left.set_title(" | ".join(title_parts))

        # ----------------------------
        # 右軸: Profit Ratio
        # ----------------------------
        self.ax_right.plot(
            x,
            frame.profit_ratio,
            marker="o",
            linewidth=2.0,
            label="Profit Ratio (%)",
        )
        self.ax_right.axhline(0, linestyle="--", linewidth=1.0)
        self.ax_right.set_ylabel("Profit Ratio (%)")

        # 凡例統合
        left_handles, left_labels = self.ax_left.get_legend_handles_labels()
        right_handles, right_labels = self.ax_right.get_legend_handles_labels()
        self.ax_left.legend(
            left_handles + right_handles,
            left_labels + right_labels,
            loc="upper left",
            fontsize=8,
        )

        self._update_summary(frame)



    def _draw_frame(self, frame: FrameData) -> None:
        self.ax_left.clear()
        self.ax_right.clear()

        # ----------------------------------------
        # 固定 x-axis
        # ----------------------------------------
        full_x = self.full_x
        full_week_labels = self.full_week_labels
        full_n = len(full_week_labels)

        visible_n = len(frame.week_labels)

        def _pad(values, fill=0.0):
            vals = list(values)
            if len(vals) < full_n:
                vals.extend([fill] * (full_n - len(vals)))
            return vals[:full_n]

        def _pad_nan(values):
            vals = list(values)
            if len(vals) < full_n:
                vals.extend([float("nan")] * (full_n - len(vals)))
            return vals[:full_n]

        supply_accume = _pad(frame.supply_accume, fill=0.0)
        demand_accume = _pad(frame.demand_accume, fill=0.0)

        # 利益率は future week を描かない
        if frame.weekly_revenue is not None and len(frame.weekly_revenue) == len(frame.profit_ratio):
            visible_profit_ratio = []
            for r, p in zip(frame.weekly_revenue, frame.profit_ratio):
                if abs(float(r)) < 1e-9:
                    visible_profit_ratio.append(float("nan"))
                else:
                    visible_profit_ratio.append(p)
        else:
            visible_profit_ratio = list(frame.profit_ratio)

        profit_ratio_plot = _pad_nan(visible_profit_ratio)

        # ----------------------------
        # 左軸: 3系列版
        # ----------------------------
        self.ax_left.bar(
            full_x,
            supply_accume,
            width=0.80,
            label="Supply PSI Cum.",
            alpha=0.45,
        )

        self.ax_left.bar(
            full_x,
            demand_accume,
            width=0.48,
            label="Demand PSI Cum.",
            alpha=0.60,
        )

        # X軸ラベルは full frame 基準で間引く
        if full_n <= 12:
            tick_idx = full_x
        elif full_n <= 40:
            tick_idx = list(range(0, full_n, 2))
        elif full_n <= 80:
            tick_idx = list(range(0, full_n, 4))
        else:
            tick_idx = list(range(0, full_n, 8))

        tick_labels = [full_week_labels[i] for i in tick_idx]

        self.ax_left.set_xticks(tick_idx)
        self.ax_left.set_xticklabels(tick_labels, rotation=45)
        self.ax_left.set_xlim(-0.5, full_n - 0.5)
        self.ax_left.set_ylabel("PSI Volume / Cumulative")
        self.ax_left.set_xlabel("Week")
        self.ax_left.grid(True, axis="y", alpha=0.28)
        self.ax_left.set_axisbelow(True)
        self.ax_left.margins(x=0.01)

        # ----------------------------
        # タイトル
        # ----------------------------
        title_parts = ["WOM PSI Accumulated + Profit Ratio"]
        if self.product_id:
            title_parts.append(f"Product={self.product_id}")
        if self.node_id:
            title_parts.append(f"Node={self.node_id}")
        if frame.title_suffix:
            title_parts.append(frame.title_suffix)

        self.ax_left.set_title(" | ".join(title_parts))

        # ----------------------------
        # 右軸: Profit Ratio
        # ----------------------------
        self.ax_right.plot(
            full_x,
            profit_ratio_plot,
            marker="o",
            linewidth=2.0,
            label="Profit Ratio (%)",
        )
        self.ax_right.axhline(0, linestyle="--", linewidth=1.0)
        self.ax_right.set_ylabel("Profit Ratio (%)")

        # 凡例統合
        left_handles, left_labels = self.ax_left.get_legend_handles_labels()
        right_handles, right_labels = self.ax_right.get_legend_handles_labels()
        self.ax_left.legend(
            left_handles + right_handles,
            left_labels + right_labels,
            loc="upper left",
            fontsize=8,
        )

        self._update_summary(frame)


    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------
    def _update_summary(self, frame: FrameData) -> None:
        latest_profit_ratio = frame.profit_ratio[-1] if frame.profit_ratio else None
        break_even_week = _first_non_negative_week(frame.profit_ratio)
        cumulative_break_even_week = _first_cumulative_non_negative_week(
            frame.weekly_profit,
            frame.total_revenue,
            frame.profit_ratio,
        )

        total_supply_p = _safe_sum(frame.supply_P)
        total_supply_i = _safe_sum(frame.supply_I)
        total_demand_s = _safe_sum(frame.demand_S)
        total_demand_co = _safe_sum(frame.demand_CO)

        self.info_text.delete("1.0", tk.END)

        self.info_text.insert(tk.END, "[Context]\n")
        self.info_text.insert(tk.END, f"Node        : {self.node_id or '-'}\n")
        self.info_text.insert(tk.END, f"Product     : {self.product_id or '-'}\n")
        self.info_text.insert(tk.END, f"Frame       : {self.current_frame + 1}/{self.total_frames}\n")
        self.info_text.insert(tk.END, "-" * 42 + "\n")

        self.info_text.insert(tk.END, "[PSI Totals]\n")
        self.info_text.insert(tk.END, f"Supply P    : {total_supply_p:,.2f}\n")
        self.info_text.insert(tk.END, f"Supply I    : {total_supply_i:,.2f}\n")
        self.info_text.insert(tk.END, f"Demand S    : {total_demand_s:,.2f}\n")
        self.info_text.insert(tk.END, f"Demand CO   : {total_demand_co:,.2f}\n")
        self.info_text.insert(tk.END, "-" * 42 + "\n")

        self.info_text.insert(tk.END, "[Business]\n")
        if frame.total_revenue is not None:
            self.info_text.insert(tk.END, f"Total Revenue       : {frame.total_revenue:,.2f}\n")
        if frame.total_profit is not None:
            self.info_text.insert(tk.END, f"Total Profit        : {frame.total_profit:,.2f}\n")
        if latest_profit_ratio is not None:
            self.info_text.insert(tk.END, f"Latest Profit Ratio : {latest_profit_ratio:,.2f}%\n")
        if frame.weekly_profit:
            latest_weekly_profit = frame.weekly_profit[-1]
            self.info_text.insert(tk.END, f"Latest Weekly Profit: {latest_weekly_profit:,.2f}\n")

        self.info_text.insert(
            tk.END,
            f"Break-even Week (ratio>=0) : "
            f"{break_even_week if break_even_week is not None else '-'}\n"
        )
        self.info_text.insert(
            tk.END,
            f"Cumulative Break-even Week : "
            f"{cumulative_break_even_week if cumulative_break_even_week is not None else '-'}\n"
        )
        self.info_text.insert(tk.END, "-" * 42 + "\n")

        self.info_text.insert(tk.END, "[Interpretation]\n")
        self.info_text.insert(
            tk.END,
            "・Supply側で在庫/先行投資が先に立ち上がり、\n"
            "・Demand側で売上/利益が後から立ち上がる、\n"
            "という位相差を読むためのビューです。\n\n"
        )
        self.info_text.insert(
            tk.END,
            "・Profit Ratio が 0% を上回る週は、\n"
            "  単週黒字化の目安です。\n"
        )
        self.info_text.insert(
            tk.END,
            "・Cumulative Break-even Week は、\n"
            "  累計ベースの投資回収タイミングを示します。\n"
        )
        self.info_text.insert(
            tk.END,
            "・Supply I と Demand CO の高さを見ることで、\n"
            "  どこで需給gapを吸収しているかの手掛かりが得られます。\n"
        )

    # --------------------------------------------------------
    # Controls
    # --------------------------------------------------------
    def play(self) -> None:
        self.is_paused = False
        self.status_var.set("Playing")

    def pause(self) -> None:
        self.is_paused = True
        self.status_var.set("Paused")

    def stop(self) -> None:
        self.is_paused = True
        self.current_frame = 0
        self._draw_current_frame_once()
        self.status_var.set("Stopped")

    def prev_frame(self) -> None:
        self.is_paused = True
        self.current_frame = (self.current_frame - 1) % self.total_frames
        self._draw_current_frame_once()

    def next_frame(self) -> None:
        self.is_paused = True
        self.current_frame = (self.current_frame + 1) % self.total_frames
        self._draw_current_frame_once()

    def _draw_current_frame_once(self) -> None:
        frame = self.data_provider.get_frame(self.current_frame)
        self._draw_frame(frame)
        self.status_var.set(f"Frame {self.current_frame + 1}/{self.total_frames}")
        self.canvas.draw_idle()

    def _on_speed_changed(self, _event: Optional[tk.Event] = None) -> None:
        speed = float(self.speed_var.get())
        self.interval_ms = int(1000 / speed) if speed > 0 else 1000

        try:
            self.anim.event_source.stop()
        except Exception:
            pass

        self.anim = FuncAnimation(
            self.figure,
            self._update_frame,
            frames=self.total_frames,
            interval=self.interval_ms,
            repeat=False,
            cache_frame_data=False,
        )

        self.status_var.set(f"Speed changed: {speed}x")

    def _on_close(self) -> None:
        try:
            self.anim.event_source.stop()
        except Exception:
            pass
        self.destroy()


# ============================================================
# Public helper
# ============================================================

def open_psi_profit_animation_window(
    master: tk.Misc,
    title: str = "WOM PSI Accumulated + Profit Ratio",
    data_provider: Optional[BasePSIProfitDataProvider] = None,
    node_id: Optional[str] = None,
    product_id: Optional[str] = None,
    interval_ms: int = 1000,
) -> PSIProfitAnimationWindow:
    provider = data_provider or SamplePSIProfitDataProvider()

    win = PSIProfitAnimationWindow(
        master=master,
        data_provider=provider,
        title=title,
        node_id=node_id,
        product_id=product_id,
        interval_ms=interval_ms,
    )
    return win


# ============================================================
# Standalone test
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Launcher")
    root.geometry("320x120")

    def launch() -> None:
        open_psi_profit_animation_window(
            master=root,
            title="Standalone WOM PSI Accumulated + Profit Ratio",
            data_provider=SamplePSIProfitDataProvider(total_frames=24, total_weeks=20),
            node_id="MOM_ASIA",
            product_id="iPhone16",
            interval_ms=1000,
        )

    ttk.Button(root, text="Open Animation Window", command=launch).pack(pady=30)
    root.mainloop()