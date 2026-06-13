"""Passive state objects for mirror-grid icon scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class MirrorGridScenePayload:
    """Trace-ready payload for one rendered mirror-grid scene."""

    object_count: int
    target_count: int
    distractor_count: int
    reference_symmetry_kind: str
    cell_labels: Tuple[str, ...]
    matching_labels: Tuple[str, ...]
    scene_cell_symmetry_kinds: Tuple[str, ...]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    panel_geometry: Dict[str, Any]
    reference_cell: Dict[str, Any]
    scene_cells: Tuple[Dict[str, Any], ...]


__all__ = ["MirrorGridScenePayload"]

