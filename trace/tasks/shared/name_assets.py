"""Shared short-name asset helpers reused across domains."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Tuple


_ASSET_ROOT = Path(__file__).resolve().parents[3] / "assets"
_DEFAULT_SHORT_NAME_MANIFEST = "series_legend_names_random_name_2to4.txt"


def asset_root() -> Path:
    """Return the repo-local shared asset root."""

    return _ASSET_ROOT


@lru_cache(maxsize=32)
def load_name_manifest(*, asset_group: str, manifest_name: str) -> Tuple[str, ...]:
    """Load one vendored name manifest as a deterministic tuple."""

    path = asset_root() / str(asset_group) / str(manifest_name)
    if not path.exists():
        raise FileNotFoundError(path)
    names = tuple(
        str(line).strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if str(line).strip()
    )
    if not names:
        raise ValueError(f"name manifest {path} resolved no names")
    return names


def load_short_name_manifest(manifest_name: str = _DEFAULT_SHORT_NAME_MANIFEST) -> Tuple[str, ...]:
    """Load the canonical short-name manifest used for visible person-style labels."""

    return load_name_manifest(asset_group="charts", manifest_name=str(manifest_name))


__all__ = [
    "asset_root",
    "load_name_manifest",
    "load_short_name_manifest",
]
