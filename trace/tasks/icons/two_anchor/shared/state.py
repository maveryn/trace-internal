"""State payloads for rendered two-anchor icon scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class TwoAnchorScenePayload:
    """Trace-ready payload for one two-anchor strip scene."""

    object_count: int
    target_count: int
    distractor_count: int
    strip_axis: str
    anchor_icon_id: str
    anchor_tint_rgb: Tuple[int, int, int]
    anchor_rotation_degrees: int
    anchor_a_center_xy: Tuple[float, float]
    anchor_b_center_xy: Tuple[float, float]
    strip_boundary_margin_px: int
    scene_icon_ids: Tuple[str, ...]
    scene_tints_rgb: Tuple[Tuple[int, int, int], ...]
    scene_rotations_degrees: Tuple[int, ...]
    matching_scene_indices: Tuple[int, ...]
    matching_bboxes: Tuple[Tuple[int, int, int, int], ...]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    panel_geometry: Dict[str, Any]
    scene_instances: Tuple[Dict[str, Any], ...]
    anchor_instances: Tuple[Dict[str, Any], Dict[str, Any]]


__all__ = ["TwoAnchorScenePayload"]

