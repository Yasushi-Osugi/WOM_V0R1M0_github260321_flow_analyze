#pysi/gui/business_animation/animation_controller.py

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from .replay_models import ReplayState, WeeklyReplaySnapshot


class AnimationController:
    """
    Tkinter の after() を使って 1week=1sec の replay を制御する。
    """

    def __init__(
        self,
        master: tk.Misc,
        snapshots: list[WeeklyReplaySnapshot],
        on_frame_changed: Callable[[WeeklyReplaySnapshot, ReplayState], None],
    ) -> None:
        self.master = master
        self.snapshots = snapshots
        self.on_frame_changed = on_frame_changed
        self.state = ReplayState()

        self._after_id: Optional[str] = None
        self.base_interval_ms = 1000  # 1week = 1sec

    def get_current_snapshot(self) -> WeeklyReplaySnapshot:
        return self.snapshots[self.state.current_index]

    def render_current(self) -> None:
        snapshot = self.get_current_snapshot()
        self.on_frame_changed(snapshot, self.state)

    def play(self) -> None:
        if not self.snapshots:
            return
        self.state.is_playing = True
        self._schedule_next()

    def pause(self) -> None:
        self.state.is_playing = False
        if self._after_id is not None:
            self.master.after_cancel(self._after_id)
            self._after_id = None

    def stop(self) -> None:
        self.pause()
        self.state.current_index = 0
        self.render_current()

    def step_forward(self) -> None:
        self.pause()
        if self.state.current_index < len(self.snapshots) - 1:
            self.state.current_index += 1
        self.render_current()

    def step_backward(self) -> None:
        self.pause()
        if self.state.current_index > 0:
            self.state.current_index -= 1
        self.render_current()

    def set_speed(self, speed_mult: float) -> None:
        self.state.speed_mult = max(0.25, speed_mult)

    def set_mode(self, mode: str) -> None:
        self.state.mode = mode
        self.render_current()

    def set_selected_node(self, node_id: str | None) -> None:
        self.state.selected_node_id = node_id
        self.render_current()

    def _schedule_next(self) -> None:
        if not self.state.is_playing:
            return

        interval = int(self.base_interval_ms / self.state.speed_mult)
        self._after_id = self.master.after(interval, self._tick)

    def _tick(self) -> None:
        if not self.state.is_playing:
            return

        if self.state.current_index < len(self.snapshots) - 1:
            self.state.current_index += 1
            self.render_current()
            self._schedule_next()
        else:
            self.pause()
