from __future__ import annotations

from pysi.planning.forward_push_with_capacity_planner import ForwardPushWithCapacityPlanner


def _make_lots(prefix: str, qty: int) -> list[dict[str, str]]:
    return [{"lot_id": f"{prefix}-{i:03d}"} for i in range(1, qty + 1)]


def run_case(planner: ForwardPushWithCapacityPlanner, requested_qty: int, capacity_qty: int) -> None:
    result = planner.consume_lots_with_capacity(
        node_id="MOM_A",
        product_id="PRODUCT_X",
        week="2026-W01",
        requested_lots=_make_lots("LOT", requested_qty),
        capacity_qty=capacity_qty,
    )

    usage = result.capacity_usage[0]
    issue_type = result.capacity_issues[0].issue_type if result.capacity_issues else "none"

    print(f"requested lots: {requested_qty}")
    print(f"capacity: {capacity_qty}")
    print(f"accepted lots: {len(result.pushed_lots)}")
    print(f"blocked lots: {len(result.blocked_lots)}")
    print(f"capacity usage: {usage.used_qty} / {usage.capacity_qty}")
    print(f"capacity issue: {issue_type}")


def main() -> None:
    planner = ForwardPushWithCapacityPlanner()

    print("=== bottleneck case (120 requested, 100 capacity) ===")
    run_case(planner, requested_qty=120, capacity_qty=100)

    print("\n=== non-bottleneck case (80 requested, 100 capacity) ===")
    run_case(planner, requested_qty=80, capacity_qty=100)


if __name__ == "__main__":
    main()
