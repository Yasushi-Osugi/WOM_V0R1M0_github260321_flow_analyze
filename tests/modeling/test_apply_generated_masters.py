import json
from pathlib import Path

from pysi.modeling.apply_generated_masters import MONEY_FILES, PHASE1_FILES, apply_generated_masters


def _write_file(base: Path, rel: Path, content: str) -> None:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _seed_generated(base: Path, include_money: bool = False) -> None:
    for rel in PHASE1_FILES:
        _write_file(base, rel, f"generated:{rel.as_posix()}")
    if include_money:
        for rel in MONEY_FILES:
            _write_file(base, rel, f"generated:{rel.as_posix()}")


def _seed_target(base: Path, files: list[Path]) -> None:
    for rel in files:
        _write_file(base, rel, f"target-old:{rel.as_posix()}")


def test_apply_generated_masters_dry_run(tmp_path: Path):
    generated = tmp_path / "generated"
    target = tmp_path / "target"
    backup = tmp_path / "backup"
    _seed_generated(generated, include_money=False)
    _seed_target(target, PHASE1_FILES)

    summary = apply_generated_masters(str(generated), str(target), str(backup), dry_run=True)

    for rel in PHASE1_FILES:
        assert (target / rel).read_text(encoding="utf-8") == f"target-old:{rel.as_posix()}"
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    assert summary["dry_run"] is True
    assert manifest["dry_run"] is True
    assert len(summary["copied_files"]) == len(PHASE1_FILES)


def test_apply_generated_masters_phase1_apply(tmp_path: Path):
    generated = tmp_path / "generated"
    target = tmp_path / "target"
    backup = tmp_path / "backup"
    _seed_generated(generated, include_money=False)
    _seed_target(target, PHASE1_FILES)

    summary = apply_generated_masters(str(generated), str(target), str(backup), dry_run=False)

    for rel in PHASE1_FILES:
        assert (target / rel).read_text(encoding="utf-8") == f"generated:{rel.as_posix()}"
        assert (backup / rel).exists()
    assert (backup / "manifest.json").exists()
    assert not summary["errors"]


def test_apply_generated_masters_include_money(tmp_path: Path):
    generated = tmp_path / "generated"
    target = tmp_path / "target"
    backup = tmp_path / "backup"
    _seed_generated(generated, include_money=True)
    _seed_target(target, PHASE1_FILES + MONEY_FILES)

    summary = apply_generated_masters(str(generated), str(target), str(backup), include_money=True)

    for rel in MONEY_FILES:
        assert (target / rel).read_text(encoding="utf-8") == f"generated:{rel.as_posix()}"
        assert (backup / rel).exists()
    assert len(summary["copied_files"]) == len(PHASE1_FILES) + len(MONEY_FILES)


def test_apply_generated_masters_missing_generated_file(tmp_path: Path):
    generated = tmp_path / "generated"
    target = tmp_path / "target"
    backup = tmp_path / "backup"
    _seed_generated(generated, include_money=False)
    _seed_target(target, PHASE1_FILES)
    (generated / PHASE1_FILES[0]).unlink()

    summary = apply_generated_masters(str(generated), str(target), str(backup), dry_run=False)

    assert summary["missing_generated_files"]
    assert summary["errors"]
    for rel in PHASE1_FILES[1:]:
        assert (target / rel).read_text(encoding="utf-8") == f"target-old:{rel.as_posix()}"
    assert not (backup / "manifest.json").exists()
