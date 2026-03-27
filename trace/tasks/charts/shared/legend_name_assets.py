"""Shared chart legend-name asset helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Tuple


_ASSET_ROOT = Path(__file__).resolve().parents[4] / "assets" / "charts"
_DEFAULT_MANIFEST = "series_legend_names_random_name_2to4.txt"


def chart_asset_root() -> Path:
    """Return the TRACE-side chart asset root."""

    return _ASSET_ROOT


@lru_cache(maxsize=16)
def load_legend_name_manifest(manifest_name: str = _DEFAULT_MANIFEST) -> Tuple[str, ...]:
    """Load one vendored chart legend-name manifest as a deterministic tuple."""

    path = chart_asset_root() / str(manifest_name)
    if not path.exists():
        raise FileNotFoundError(path)
    names = tuple(
        str(line).strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if str(line).strip()
    )
    if not names:
        raise ValueError(f"legend-name manifest {path} resolved no names")
    return names


__all__ = [
    "chart_asset_root",
    "load_legend_name_manifest",
]
