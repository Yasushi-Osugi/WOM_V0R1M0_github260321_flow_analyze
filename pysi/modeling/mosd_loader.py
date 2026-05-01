"""Loader for WOM Master Original Source Data (MOSD)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_mosd(path: str) -> dict[str, Any]:
    """Load MOSD YAML or JSON file and return dict.

    Supported extensions: .yaml, .yml, .json.
    """
    src = Path(path)
    ext = src.suffix.lower()

    if ext == ".json":
        with src.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    elif ext in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "YAML support requires PyYAML. Install with `pip install pyyaml`."
            ) from exc
        with src.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    else:
        raise ValueError(f"Unsupported MOSD extension: {ext}")

    if not isinstance(data, dict):
        raise ValueError("MOSD root must be a mapping/object.")
    return data
