from dataclasses import dataclass, field
from typing import Any

from pysi.cases.japanese_rice import build_default_rice_case_dataset, build_rice_week_indexer
from pysi.cases.japanese_rice.rice_backward_planning_after_seed import (
    collect_lot_ids_from_demand_tree,
    run_rice_backward_planning_after_seed_smoke,
)


@dataclass
class _PlanNode:
    name: str
    children: list[Any] = field(default_factory=list)
    parent: Any = None
    psi4demand: list = field(default_factory=list)
    psi4supply: list = field(default_factory=list)

    def aggregate_children_P_into_parent_S(self, layer: str = "demand"):
        if layer != "demand":
            return
        for week in range(len(self.psi4demand)):
            parent_s = self.psi4demand[week][0]
            for child in self.children:
                parent_s.extend(child.psi4demand[week][3])

    def calcS2P(self):
        for week in range(len(self.psi4demand)):
            self.psi4demand[week][3].extend(self.psi4demand[week][0])


def _make_node(name: str, weeks: int = 156) -> _PlanNode:
    return _PlanNode(
        name=name,
        psi4demand=[[[], [], [], []] for _ in range(weeks)],
        psi4supply=[[[], [], [], []] for _ in range(weeks)],
    )


def _build_roots(weeks: int = 156):
    out_root = _make_node("ROOT_RICE", weeks)
    dad = _make_node("DAD_RICE", weeks)
    producer = _make_node("PRODUCER_NIIGATA", weeks)
    household = _make_node("DEMAND_HOUSEHOLD_TOKYO", weeks)
    food_service = _make_node("DEMAND_FOOD_SERVICE_TOKYO", weeks)

    out_root.children = [dad]
    dad.parent = out_root
    dad.children = [producer, household, food_service]
    producer.parent = dad
    household.parent = dad
    food_service.parent = dad

    in_root = _make_node("INBOUND_ROOT_RICE", weeks)
    return out_root, in_root, dad, producer, household, food_service


def test_backward_planning_after_seed_smoke_preserves_lot_ids_and_psi_structure():
    dataset = build_default_rice_case_dataset()
    out_root, in_root, dad, producer, household, food_service = _build_roots()

    result = run_rice_backward_planning_after_seed_smoke(
        out_root=out_root,
        in_root=in_root,
        product_name="PACKAGED_RICE_STANDARD",
        case_data=dataset,
        dry_run_seed=False,
    )

    assert result.seed_count > 0
    assert result.backward_planning_ran is True
    assert result.non_list_bucket_errors == []
    assert result.non_string_lot_errors == []
    assert result.missing_lot_ids_after == set()

    assert household.psi4demand[0][0]
    assert food_service.psi4demand[0][0]
    assert dad.psi4demand[0][0] or dad.psi4demand[0][3]

    for node in [out_root, dad, producer, household, food_service, in_root]:
        for week in node.psi4demand:
            assert isinstance(week, list)
            for bucket in week:
                assert isinstance(bucket, list)
                assert all(isinstance(item, str) for item in bucket)
                assert not any(isinstance(item, (int, float)) for item in bucket)


def test_w40_w41_boundary_remains_valid_after_smoke():
    dataset = build_default_rice_case_dataset()
    out_root, in_root, _, producer, _, _ = _build_roots()

    result = run_rice_backward_planning_after_seed_smoke(
        out_root=out_root,
        in_root=in_root,
        product_name="PACKAGED_RICE_STANDARD",
        case_data=dataset,
    )

    week_indexer = build_rice_week_indexer(2026, 2028)
    assert week_indexer["2026-W40"] == 39
    assert week_indexer["2026-W41"] == 40
    assert producer.psi4demand[39][3]
    assert producer.psi4demand[40][3]
    assert collect_lot_ids_from_demand_tree(out_root)
    assert result.missing_lot_ids_after == set()
