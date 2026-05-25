from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pysi.plan.bridges.e2e_bridge_forward_capacity_smoke import run_e2e_bridge_forward_capacity_smoke


@dataclass
class ExplicitBridgeCapacityPipelineResult:
    product_name: str = ""

    bridge_a_result: Any | None = None
    mom_allocation_result: Any | None = None
    backward_capacity_result: Any | None = None
    bridge_b_result: Any | None = None
    forward_capacity_result: Any | None = None
    smoke_result: Any | None = None

    source_lot_ids: list[str] = field(default_factory=list)
    missing_lot_ids: list[str] = field(default_factory=list)

    shifted_lot_ids: list[str] = field(default_factory=list)
    backlog_lot_ids: list[str] = field(default_factory=list)
    accepted_lot_ids: list[str] = field(default_factory=list)
    blocked_lot_ids: list[str] = field(default_factory=list)
    overflow_i_lot_ids: list[str] = field(default_factory=list)

    capacity_usage: list[dict] = field(default_factory=list)
    capacity_violations: list[dict] = field(default_factory=list)
    replan_commands: list[dict] = field(default_factory=list)

    non_list_bucket_errors: list[dict] = field(default_factory=list)
    non_string_lot_errors: list[dict] = field(default_factory=list)

    message: str = ""


def run_explicit_bridge_capacity_pipeline(
    *,
    outbound_root,
    inbound_root,
    product: str,
    mom_policy: dict,
    backward_weekly_capability: dict,
    forward_weekly_capacity: dict,
    bridge_a_mode: str = "replace",
    bridge_b_policy: str = "s_p_only",
    bridge_b_mode: str = "replace",
    max_early_build_weeks: int = 13,
    cap_i_mode: str = "soft",
    debug: bool = False,
) -> ExplicitBridgeCapacityPipelineResult:
    """Run the explicit bridge + capacity pipeline through the validated smoke flow.

    MVP note:
    - This wrapper intentionally reuses run_e2e_bridge_forward_capacity_smoke(...) to
      avoid duplicating planning logic while providing a stable, runner-specific result
      contract for later run_full_plan integration.
    - Stage-specific result objects are currently not exposed by the smoke wrapper;
      those fields remain None for now and can be populated in a future direct-composition phase.
    """

    smoke_result = run_e2e_bridge_forward_capacity_smoke(
        outbound_root=outbound_root,
        inbound_root=inbound_root,
        product=product,
        mom_policy=mom_policy,
        backward_weekly_capability=backward_weekly_capability,
        forward_weekly_capacity=forward_weekly_capacity,
        bridge_a_mode=bridge_a_mode,
        bridge_b_policy=bridge_b_policy,
        bridge_b_mode=bridge_b_mode,
        max_early_build_weeks=max_early_build_weeks,
        cap_i_mode=cap_i_mode,
        debug=debug,
    )

    blocked_lot_ids = sorted(set(getattr(smoke_result, "blocked_lot_ids", []) or []))
    overflow_i_lot_ids = sorted(set(getattr(smoke_result, "overflow_i_lot_ids", []) or []))
    # accepted_lot_ids is limited by smoke output availability in MVP; keep empty unless
    # explicit accepted lot IDs become available from lower layers.
    accepted_lot_ids: list[str] = []

    return ExplicitBridgeCapacityPipelineResult(
        product_name=product,
        smoke_result=smoke_result,
        source_lot_ids=[],
        missing_lot_ids=list(getattr(smoke_result, "missing_lot_ids", []) or []),
        shifted_lot_ids=[],
        backlog_lot_ids=[],
        accepted_lot_ids=accepted_lot_ids,
        blocked_lot_ids=blocked_lot_ids,
        overflow_i_lot_ids=overflow_i_lot_ids,
        capacity_usage=[],
        capacity_violations=[],
        replan_commands=[],
        non_list_bucket_errors=list(getattr(smoke_result, "non_list_bucket_errors", []) or []),
        non_string_lot_errors=list(getattr(smoke_result, "non_string_lot_errors", []) or []),
        message=(
            "Explicit bridge + capacity pipeline completed via smoke wrapper "
            "(Bridge A -> MOM allocation -> backward capacity planning -> Bridge B -> forward capacity)."
        ),
    )


def maybe_run_explicit_bridge_capacity_pipeline(ctx: dict) -> ExplicitBridgeCapacityPipelineResult | None:
    """Conditionally run the explicit bridge+capacity pipeline based on a ctx feature flag."""
    if not ctx.get("enable_explicit_bridge_capacity_pipeline", False):
        return None

    required_keys = [
        "explicit_pipeline_outbound_root",
        "explicit_pipeline_inbound_root",
        "explicit_pipeline_product",
        "explicit_pipeline_mom_policy",
        "explicit_pipeline_backward_weekly_capability",
        "explicit_pipeline_forward_weekly_capacity",
    ]

    for key in required_keys:
        if key not in ctx:
            raise ValueError(f"explicit bridge capacity pipeline enabled but missing ctx key: {key}")

    result = run_explicit_bridge_capacity_pipeline(
        outbound_root=ctx["explicit_pipeline_outbound_root"],
        inbound_root=ctx["explicit_pipeline_inbound_root"],
        product=ctx["explicit_pipeline_product"],
        mom_policy=ctx["explicit_pipeline_mom_policy"],
        backward_weekly_capability=ctx["explicit_pipeline_backward_weekly_capability"],
        forward_weekly_capacity=ctx["explicit_pipeline_forward_weekly_capacity"],
        bridge_a_mode=ctx.get("explicit_pipeline_bridge_a_mode", "replace"),
        bridge_b_policy=ctx.get("explicit_pipeline_bridge_b_policy", "s_p_only"),
        bridge_b_mode=ctx.get("explicit_pipeline_bridge_b_mode", "replace"),
        max_early_build_weeks=ctx.get("explicit_pipeline_max_early_build_weeks", 13),
        cap_i_mode=ctx.get("explicit_pipeline_cap_i_mode", "soft"),
        debug=ctx.get("explicit_pipeline_debug", False),
    )
    ctx["explicit_bridge_capacity_pipeline_result"] = result
    return result


def maybe_run_explicit_bridge_capacity_pipeline_from_env(
    *,
    env,
    outbound_root,
    inbound_root,
    product,
    mom_policy,
    backward_weekly_capability=None,
    forward_weekly_capacity=None,
):
    """
    Small adapter for run_full_plan / planning-sequence integration.
    Defaults the feature flag to False and allows env-level overrides.
    """
    ctx = {
        "enable_explicit_bridge_capacity_pipeline": getattr(
            env,
            "enable_explicit_bridge_capacity_pipeline",
            False,
        ),
    }
    required_values = {
        "explicit_pipeline_outbound_root": outbound_root,
        "explicit_pipeline_inbound_root": inbound_root,
        "explicit_pipeline_product": product,
        "explicit_pipeline_mom_policy": mom_policy,
        "explicit_pipeline_backward_weekly_capability": backward_weekly_capability,
        "explicit_pipeline_forward_weekly_capacity": forward_weekly_capacity,
    }
    for key, value in required_values.items():
        if value is not None:
            ctx[key] = value
    for key in (
        "explicit_pipeline_bridge_a_mode",
        "explicit_pipeline_bridge_b_policy",
        "explicit_pipeline_bridge_b_mode",
        "explicit_pipeline_max_early_build_weeks",
        "explicit_pipeline_cap_i_mode",
        "explicit_pipeline_debug",
    ):
        if hasattr(env, key):
            ctx[key] = getattr(env, key)

    result = maybe_run_explicit_bridge_capacity_pipeline(ctx)
    if result is not None:
        setattr(env, "explicit_bridge_capacity_pipeline_result", result)
    return result
