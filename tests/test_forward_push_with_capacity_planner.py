from pysi.planning.forward_push_with_capacity_planner import ForwardPushWithCapacityPlanner


def _lots(qty: int) -> list[dict[str, str]]:
    return [{"lot_id": f"L{i:03d}"} for i in range(1, qty + 1)]


def _run(requested_qty: int, capacity_qty: int | None):
    planner = ForwardPushWithCapacityPlanner()
    return planner.consume_lots_with_capacity(
        node_id="MOM_A",
        product_id="PRODUCT_X",
        week="2026-W01",
        requested_lots=_lots(requested_qty),
        capacity_qty=capacity_qty,
    )


def test_capacity_sufficient_all_accepted():
    result = _run(80, 100)
    assert len(result.pushed_lots) == 80
    assert len(result.blocked_lots) == 0
    assert len(result.capacity_issues) == 0


def test_capacity_insufficient_shortage_issue_generated():
    result = _run(120, 100)
    assert len(result.pushed_lots) == 100
    assert len(result.blocked_lots) == 20
    assert len(result.capacity_issues) == 1
    assert result.capacity_issues[0].issue_type == "CAPACITY_SHORTAGE"


def test_zero_capacity_blocks_all_lots():
    result = _run(20, 0)
    assert len(result.pushed_lots) == 0
    assert len(result.blocked_lots) == 20
    assert len(result.capacity_issues) == 1


def test_missing_capacity_means_unlimited_capacity():
    result = _run(120, None)
    assert len(result.pushed_lots) == 120
    assert len(result.blocked_lots) == 0
    assert len(result.capacity_issues) == 0
