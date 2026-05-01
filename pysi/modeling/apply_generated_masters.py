from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

PHASE1_FILES = [
    Path("data/node_geo.csv"),
    Path("data/product_tree_inbound.csv"),
    Path("data/product_tree_outbound.csv"),
    Path("data/sku_P_month_data.csv"),
    Path("data/sku_S_month_data.csv"),
    Path("pysi/master_data/node_master.csv"),
]

MONEY_FILES = [
    Path("pysi/master_data/node_character_money_master.csv"),
    Path("pysi/master_data/node_product_money_master.csv"),
    Path("data/cost_masters/market_master.csv"),
    Path("data/cost_masters/cs_node_to_market_map.csv"),
    Path("data/cost_masters/product_cost_master.csv"),
    Path("data/cost_masters/node_cost_master.csv"),
    Path("data/cost_masters/lane_cost_master.csv"),
    Path("data/cost_masters/sales_price_master.csv"),
    Path("data/cost_masters/fx_rate_master.csv"),
]


def _to_posix(paths: list[Path]) -> list[str]:
    return [p.as_posix() for p in paths]


def apply_generated_masters(
    generated_dir: str,
    target_root: str,
    backup_dir: str,
    *,
    include_money: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    generated = Path(generated_dir).resolve()
    target = Path(target_root).resolve()
    backup = Path(backup_dir).resolve()

    files = PHASE1_FILES + (MONEY_FILES if include_money else [])

    missing_generated: list[Path] = []
    missing_target: list[Path] = []
    errors: list[str] = []
    warnings: list[str] = []
    copied: list[Path] = []
    backed_up: list[Path] = []

    for rel in files:
        if not (generated / rel).exists():
            missing_generated.append(rel)

    summary: dict[str, Any] = {
        "generated_dir": str(generated),
        "target_root": str(target),
        "backup_dir": str(backup),
        "generated_source": str(generated),
        "include_money": include_money,
        "dry_run": dry_run,
        "copied_files": [],
        "backed_up_files": [],
        "missing_generated_files": _to_posix(missing_generated),
        "missing_target_files": [],
        "errors": [],
        "warnings": [],
    }

    if missing_generated:
        errors.append("Missing required generated files; no files were applied.")
        summary["errors"] = errors
        summary["warnings"] = warnings
        return summary

    for rel in files:
        source_path = (generated / rel).resolve()
        target_path = (target / rel).resolve()

        try:
            target_path.relative_to(target)
        except ValueError:
            errors.append(f"Refusing to copy outside target_root: {target_path}")
            continue

        if target_path.exists():
            backup_path = backup / rel
            backed_up.append(rel)
            if not dry_run:
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target_path, backup_path)
        else:
            missing_target.append(rel)

        copied.append(rel)
        if not dry_run:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)

    summary["copied_files"] = _to_posix(copied)
    summary["backed_up_files"] = _to_posix(backed_up)
    summary["missing_target_files"] = _to_posix(missing_target)
    summary["errors"] = errors
    summary["warnings"] = warnings

    backup.mkdir(parents=True, exist_ok=True)
    manifest_path = backup / "manifest.json"
    manifest_payload = {
        "generated_source": summary["generated_source"],
        "target_root": summary["target_root"],
        "include_money": include_money,
        "dry_run": dry_run,
        "copied_files": summary["copied_files"],
        "backed_up_files": summary["backed_up_files"],
        "missing_generated_files": summary["missing_generated_files"],
        "missing_target_files": summary["missing_target_files"],
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return summary


def _main() -> int:
    parser = argparse.ArgumentParser(description="Apply generated MOSD masters to runtime master locations")
    parser.add_argument("--generated", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--backup-dir", required=True)
    parser.add_argument("--include-money", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    summary = apply_generated_masters(
        generated_dir=args.generated,
        target_root=args.target,
        backup_dir=args.backup_dir,
        include_money=args.include_money,
        dry_run=args.dry_run,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if summary.get("missing_generated_files") or summary.get("errors") else 0


if __name__ == "__main__":
    sys.exit(_main())
