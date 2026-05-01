"""MOSD modeling utilities for WOM master generation."""

from .mosd_loader import load_mosd
from .mosd_schema import validate_mosd_schema
from .wom_master_validator import validate_generated_masters

__all__ = ["load_mosd", "validate_mosd_schema", "generate_wom_masters", "validate_generated_masters"]


def generate_wom_masters(*args, **kwargs):
    from .wom_master_adapter import generate_wom_masters as _impl
    return _impl(*args, **kwargs)
