from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pysi.planning.capacity_io import (
    CapacityUsage,
    CapacityViolation,
    export_capacity_usage_csv,
    export_capacity_violation_csv,
    run_forward_push_with_capacity_from_master,
)
from pysi.planning.capacity_master import CapacityMasterRecord, build_capacity_lookup

SCENARIO_ID = "COVID_BASE"
PRODUCT_NAME = "COVID_VACCINE_PFIZER"
WEEK = "2026-W40"
TREE_SIDE = "OUTBOUND"
CAPACITY_TYPE = "S"

REGIONAL_DEMAND = {"TOKYO": 150, "OSAKA": 120, "AICHI": 80}
TRANSPORT_CAPACITY = {"TOKYO": 100, "OSAKA": 80, "AICHI": 50}
VACCINATION_CAPACITY = {"TOKYO": 90, "OSAKA": 70, "AICHI": 50}


@dataclass
class RegionFlow:
    requested: int
    capacity: int
    accepted: int
    blocked: int


@dataclass
class VaccinationFlow:
    clinic_inventory: int
    vaccination_capacity: int
    administered: int
    remaining: int


def make_vaccine_lots(qty: int = 300) -> list[dict[str, object]]:
    return [
        {
            "lot_id": f"VAC-PFZ-2026W40-{i:06d}",
            "product_id": PRODUCT_NAME,
            "dose_qty": 100,
            "current_node": "CENTRAL_DC",
            "target_region": None,
            "target_node": None,
            "week_available": WEEK,
            "expiry_week": "2026-W48",
            "quality_status": "usable",
        }
        for i in range(1, qty + 1)
    ]


def _build_capacity_lookup():
    records: list[CapacityMasterRecord] = []
    for region, qty in TRANSPORT_CAPACITY.items():
        records.append(
            CapacityMasterRecord(
                scenario_id=SCENARIO_ID,
                tree_side=TREE_SIDE,
                node_name=f"LANE_CENTRAL_TO_{region}",
                product_name=PRODUCT_NAME,
                week=WEEK,
                capacity_type=CAPACITY_TYPE,
                capacity_qty=qty,
                cap_mode="hard",
                unit="LOT",
                priority=100,
                calendar_id="COLD_CAL",
                comment=f"transport capacity central to {region.title()}",
            )
        )
    for region, qty in VACCINATION_CAPACITY.items():
        records.append(
            CapacityMasterRecord(
                scenario_id=SCENARIO_ID,
                tree_side=TREE_SIDE,
                node_name=f"CLINIC_{region}_01",
                product_name=PRODUCT_NAME,
                week=WEEK,
                capacity_type=CAPACITY_TYPE,
                capacity_qty=qty,
                cap_mode="hard",
                unit="LOT",
                priority=100,
                calendar_id="COLD_CAL",
                comment=f"vaccination capacity {region.title()}",
            )
        )
    return build_capacity_lookup(records)


def _eligible_lots(lots: list[dict[str, object]]) -> list[dict[str, object]]:
    return [lot for lot in lots if lot["quality_status"] == "usable" and str(lot["expiry_week"]) >= WEEK]


def run_smoke(export_csv: bool = True) -> dict[str, object]:
    all_lots = make_vaccine_lots(300)
    eligible = _eligible_lots(all_lots)
    lookup = _build_capacity_lookup()

    usages: list[CapacityUsage] = []
    violations: list[CapacityViolation] = []
    transport: dict[str, RegionFlow] = {}
    vaccination: dict[str, VaccinationFlow] = {}

    for region, demand_qty in REGIONAL_DEMAND.items():
        requested_lots = [dict(lot, target_region=region) for lot in eligible[:demand_qty]]
        # MVP simplification: each region independently slices from central lots to
        # validate capacity gate behavior; strict global central inventory depletion
        # and region-priority allocation are intentionally deferred.
        transport_result, usage, violation = run_forward_push_with_capacity_from_master(
            scenario_id=SCENARIO_ID,
            tree_side=TREE_SIDE,
            node_name=f"LANE_CENTRAL_TO_{region}",
            product_name=PRODUCT_NAME,
            week=WEEK,
            capacity_type=CAPACITY_TYPE,
            requested_lots=requested_lots,
            capacity_lookup=lookup,
        )
        if usage:
            usages.append(usage)
        if violation:
            violations.append(violation)

        accepted = [dict(lot, current_node=f"CLINIC_{region}_01", target_node=f"CLINIC_{region}_01") for lot in transport_result.pushed_lots]
        transport[region] = RegionFlow(
            requested=demand_qty,
            capacity=TRANSPORT_CAPACITY[region],
            accepted=len(transport_result.pushed_lots),
            blocked=len(transport_result.blocked_lots),
        )

        vacc_result, v_usage, v_violation = run_forward_push_with_capacity_from_master(
            scenario_id=SCENARIO_ID,
            tree_side=TREE_SIDE,
            node_name=f"CLINIC_{region}_01",
            product_name=PRODUCT_NAME,
            week=WEEK,
            capacity_type=CAPACITY_TYPE,
            requested_lots=accepted,
            capacity_lookup=lookup,
        )
        if v_usage:
            usages.append(v_usage)
        if v_violation:
            violations.append(v_violation)

        vaccination[region] = VaccinationFlow(
            clinic_inventory=len(accepted),
            vaccination_capacity=VACCINATION_CAPACITY[region],
            administered=len(vacc_result.pushed_lots),
            remaining=len(vacc_result.blocked_lots),
        )

    if export_csv:
        out_dir = Path("outputs/covid_vaccine")
        export_capacity_usage_csv(usages, out_dir / "capacity_usage.csv")
        export_capacity_violation_csv(violations, out_dir / "capacity_violation.csv")

    return {
        "lots": all_lots,
        "transport": transport,
        "vaccination": vaccination,
        "usages": usages,
        "violations": violations,
    }


def main() -> None:
    result = run_smoke(export_csv=True)
    transport = result["transport"]
    vaccination = result["vaccination"]
    print("=== COVID vaccine with-capacity PUSH smoke ===")
    print(f"scenario: {SCENARIO_ID}")
    print(f"week: {WEEK}")
    print(f"product: {PRODUCT_NAME}\n")
    print("initial supply at CENTRAL_DC: 300 lots\n")
    print("transport:")
    for region in ("TOKYO", "OSAKA", "AICHI"):
        row = transport[region]
        print(f"  {region} requested {row.requested} / capacity {row.capacity} / accepted {row.accepted} / blocked {row.blocked}")
    print("\nvaccination:")
    for region in ("TOKYO", "OSAKA", "AICHI"):
        row = vaccination[region]
        print(
            f"  {region} clinic inventory {row.clinic_inventory} / vaccination capacity {row.vaccination_capacity} "
            f"/ administered {row.administered} / remaining {row.remaining}"
        )
    transported = sum(x.accepted for x in transport.values())
    transport_blocked = sum(x.blocked for x in transport.values())
    administered = sum(x.administered for x in vaccination.values())
    remaining = sum(x.remaining for x in vaccination.values())
    print("\nsummary:")
    print("  total supply: 300")
    print(f"  transported lots: {transported}")
    print(f"  transport blocked lots: {transport_blocked}")
    print(f"  administered lots: {administered}")
    print(f"  clinic remaining usable inventory: {remaining}")


if __name__ == "__main__":
    main()
