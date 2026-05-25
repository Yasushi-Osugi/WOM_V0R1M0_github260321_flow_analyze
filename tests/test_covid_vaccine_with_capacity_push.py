from pysi.runners.run_covid_vaccine_with_capacity_push_smoke import run_smoke


def test_covid_vaccine_with_capacity_push_smoke_counts_and_identity():
    result = run_smoke(export_csv=False)

    lots = result["lots"]
    assert len(lots) == 300
    assert all(lot["quality_status"] == "usable" for lot in lots)

    transport = result["transport"]
    assert transport["TOKYO"].accepted == 100
    assert transport["TOKYO"].blocked == 50
    assert transport["OSAKA"].accepted == 80
    assert transport["OSAKA"].blocked == 40
    assert transport["AICHI"].accepted == 50
    assert transport["AICHI"].blocked == 30
    assert sum(v.accepted for v in transport.values()) == 230
    assert sum(v.blocked for v in transport.values()) == 120

    vaccination = result["vaccination"]
    assert vaccination["TOKYO"].administered == 90
    assert vaccination["TOKYO"].remaining == 10
    assert vaccination["OSAKA"].administered == 70
    assert vaccination["OSAKA"].remaining == 10
    assert vaccination["AICHI"].administered == 50
    assert vaccination["AICHI"].remaining == 0
    assert sum(v.administered for v in vaccination.values()) == 210
    assert sum(v.remaining for v in vaccination.values()) == 20

    usages = result["usages"]
    violations = result["violations"]
    assert len(usages) == 6
    assert len(violations) == 5
    transport_violations = [v for v in violations if v.node_name.startswith("LANE_CENTRAL_TO_")]
    assert len(transport_violations) == 3

    lot_ids = {lot["lot_id"] for lot in lots}
    used_lot_ids = {lot_id for usage in usages for lot_id in usage.used_lot_ids}
    violation_lot_ids = {lot_id for violation in violations for lot_id in violation.overflow_lot_ids}
    assert used_lot_ids.issubset(lot_ids)
    assert violation_lot_ids.issubset(lot_ids)
