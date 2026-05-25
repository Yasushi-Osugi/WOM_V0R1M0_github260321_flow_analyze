from dataclasses import dataclass

import pytest

from pysi.adapters.plan_node_seeding import apply_psi_seed_records_to_plan_nodes
from pysi.adapters.psi_seed import PsiSeedRecord


@dataclass
class MockPlanNode:
    name: str
    psi4demand: list
    psi4supply: list


def make_mock_plan_node(name: str, weeks: int) -> MockPlanNode:
    return MockPlanNode(
        name=name,
        psi4demand=[[[], [], [], []] for _ in range(weeks)],
        psi4supply=[[[], [], [], []] for _ in range(weeks)],
    )


def _seed(layer: str, bucket: str, lot_id: str, week: str = "2026-W01", node_id: str = "NODE_A") -> PsiSeedRecord:
    return PsiSeedRecord(
        scenario_id="BASE",
        product_id="PRODUCT_X",
        node_id=node_id,
        week=week,
        layer=layer,
        bucket=bucket,
        lot_id=lot_id,
        quantity=1.0,
    )


def test_demand_s_seed_goes_to_psi4demand_s_bucket():
    node = make_mock_plan_node("NODE_A", weeks=2)
    apply_psi_seed_records_to_plan_nodes(
        [_seed("demand", "S", "LOT_001")],
        plan_node_lookup={"NODE_A": node},
        week_indexer={"2026-W01": 0},
    )
    assert node.psi4demand[0][0] == ["LOT_001"]


def test_demand_p_seed_goes_to_psi4demand_p_bucket():
    node = make_mock_plan_node("NODE_A", weeks=2)
    apply_psi_seed_records_to_plan_nodes(
        [_seed("demand", "P", "LOT_P")],
        plan_node_lookup={"NODE_A": node},
        week_indexer={"2026-W01": 0},
    )
    assert node.psi4demand[0][3] == ["LOT_P"]


def test_supply_i_seed_goes_to_psi4supply_i_bucket():
    node = make_mock_plan_node("NODE_A", weeks=2)
    apply_psi_seed_records_to_plan_nodes(
        [_seed("supply", "I", "LOT_I")],
        plan_node_lookup={"NODE_A": node},
        week_indexer={"2026-W01": 0},
    )
    assert node.psi4supply[0][2] == ["LOT_I"]


def test_multiple_records_preserve_lot_order_in_same_bucket():
    node = make_mock_plan_node("NODE_A", weeks=2)
    apply_psi_seed_records_to_plan_nodes(
        [_seed("demand", "S", "LOT_001"), _seed("demand", "S", "LOT_002"), _seed("demand", "S", "LOT_003")],
        plan_node_lookup={"NODE_A": node},
        week_indexer={"2026-W01": 0},
    )
    assert node.psi4demand[0][0] == ["LOT_001", "LOT_002", "LOT_003"]


def test_dry_run_does_not_mutate_plan_node():
    node = make_mock_plan_node("NODE_A", weeks=2)
    result = apply_psi_seed_records_to_plan_nodes(
        [_seed("demand", "S", "LOT_001")],
        plan_node_lookup={"NODE_A": node},
        week_indexer={"2026-W01": 0},
        dry_run=True,
    )
    assert node.psi4demand[0][0] == []
    assert result.seeded_count == 1
    assert result.dry_run is True


def test_missing_node_is_recorded_and_skipped():
    node = make_mock_plan_node("NODE_A", weeks=2)
    result = apply_psi_seed_records_to_plan_nodes(
        [_seed("demand", "S", "LOT_001", node_id="MISSING_NODE")],
        plan_node_lookup={"NODE_A": node},
        week_indexer={"2026-W01": 0},
    )
    assert result.seeded_count == 0
    assert result.skipped_count == 1
    assert result.missing_node_ids == ["MISSING_NODE"]


def test_invalid_week_is_recorded_and_skipped():
    node = make_mock_plan_node("NODE_A", weeks=2)
    result = apply_psi_seed_records_to_plan_nodes(
        [_seed("demand", "S", "LOT_001", week="2026-W99")],
        plan_node_lookup={"NODE_A": node},
        week_indexer={"2026-W01": 0},
    )
    assert result.seeded_count == 0
    assert result.skipped_count == 1
    assert result.invalid_weeks == [{"node_id": "NODE_A", "week": "2026-W99"}]


def test_invalid_bucket_raises_value_error():
    node = make_mock_plan_node("NODE_A", weeks=2)
    with pytest.raises(ValueError):
        apply_psi_seed_records_to_plan_nodes(
            [_seed("demand", "X", "LOT_BAD")],
            plan_node_lookup={"NODE_A": node},
            week_indexer={"2026-W01": 0},
        )


def test_existing_bucket_contents_not_overwritten():
    node = make_mock_plan_node("NODE_A", weeks=2)
    node.psi4demand[0][0].append("EXISTING")
    apply_psi_seed_records_to_plan_nodes(
        [_seed("demand", "S", "LOT_001")],
        plan_node_lookup={"NODE_A": node},
        week_indexer={"2026-W01": 0},
    )
    assert node.psi4demand[0][0] == ["EXISTING", "LOT_001"]


def test_psi_buckets_contain_lot_ids_not_numeric_quantities():
    node = make_mock_plan_node("NODE_A", weeks=2)
    apply_psi_seed_records_to_plan_nodes(
        [_seed("demand", "S", "LOT_001")],
        plan_node_lookup={"NODE_A": node},
        week_indexer={"2026-W01": 0},
    )
    bucket = node.psi4demand[0][0]
    assert isinstance(bucket, list)
    assert all(isinstance(item, str) for item in bucket)
    assert bucket == ["LOT_001"]


def test_rice_w40_w41_boundary_maps_to_week_indexes_39_and_40():
    node = make_mock_plan_node("PRODUCER_NIIGATA", weeks=41)
    apply_psi_seed_records_to_plan_nodes(
        [
            _seed("demand", "S", "LOT_W40", week="2026-W40", node_id="PRODUCER_NIIGATA"),
            _seed("demand", "S", "LOT_W41", week="2026-W41", node_id="PRODUCER_NIIGATA"),
        ],
        plan_node_lookup={"PRODUCER_NIIGATA": node},
        week_indexer={"2026-W40": 39, "2026-W41": 40},
    )
    assert node.psi4demand[39][0] == ["LOT_W40"]
    assert node.psi4demand[40][0] == ["LOT_W41"]
