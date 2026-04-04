# pysi/plugins/event_extractor/plugin.py

from __future__ import annotations

from typing import Any

# 既存 plugin 群の import 流儀に合わせてください。
# もしこの import で通らない場合は、repo 内の他 plugin が使っている
# action の import パスに合わせて修正してください。
from pysi.core.hooks.core import action

from pysi.bridge.event_extractor import ExtractContext, extract_events
from pysi.bridge.event_mapper import map_bridge_events_to_kernel_v1
from pysi.bridge.state_snapshot import SnapshotBuildContext, build_snapshot_from_v0r8


def _pick_time_bucket(env: Any) -> str:
    """
    TEMP fallback policy (bridge v0.1):
      1) use env.current_time_bucket if present
      2) otherwise fallback to fixed bucket ("202601")

    Future:
      derive from planning cycle / scenario calendar.
    """
    return str(getattr(env, "current_time_bucket", "202601"))


def _capture_snapshot(env: Any):
    tb = _pick_time_bucket(env)
    return build_snapshot_from_v0r8(
        env_or_root=env,
        time_bucket=tb,
        ctx=SnapshotBuildContext(product_id=getattr(env, "product_selected", None)),
    )


@action("pipeline:after_supply_planning", priority=50)
def on_after_supply_planning(*, env=None, root=None, **kwargs):
    """
    Initial-cycle behavior:
      if previous snapshot is absent, no state diff is computed.
      bridge events / mapped events are kept empty for the cycle.
    """
    if env is None:
        print("[bridge] skipped: env is None")
        return

    print("[bridge] on_after_supply_planning invoked")

    previous = getattr(env, "_bridge_prev_snapshot", None)
    current = _capture_snapshot(env)

    print(f"[bridge] current snapshot time_bucket={current.time_bucket}")
    print(f"[bridge] previous snapshot exists={previous is not None}")

    setattr(env, "_bridge_prev_snapshot", current)

    if previous is None:
        print("[bridge] first cycle: previous snapshot is None, bridge events kept empty")
        setattr(env, "_bridge_events", [])
        setattr(env, "_bridge_kernel_flow_events", [])
        setattr(env, "_bridge_sidecar_events", [])
        return

    bridge_events = extract_events(
        previous_state=previous,
        current_state=current,
        ctx=ExtractContext(time_bucket=current.time_bucket, seq_start=1),
    )
    mapped = map_bridge_events_to_kernel_v1(bridge_events)

    print(f"[bridge] extracted bridge events={len(bridge_events)}")
    print(
        f"[bridge] mapped flow events={len(mapped.flow_events)} "
        f"sidecar events={len(mapped.sidecar_events)}"
    )

    setattr(env, "_bridge_events", bridge_events)
    setattr(env, "_bridge_kernel_flow_events", mapped.flow_events)
    setattr(env, "_bridge_sidecar_events", mapped.sidecar_events)