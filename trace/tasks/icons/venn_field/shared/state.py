"""Passive state records for Venn-field icon scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from PIL import Image


@dataclass(frozen=True)
class NamedColorEntry:
    """Resolved semantic color for one procedural named icon."""

    name: str
    rgb: Tuple[int, int, int]
    label: str


@dataclass(frozen=True)
class VennSpec:
    """Pixel-space geometry for the two marked circles."""

    left_center_xy: Tuple[float, float]
    right_center_xy: Tuple[float, float]
    radius_px: float
    left_bbox_xyxy: Tuple[int, int, int, int]
    right_bbox_xyxy: Tuple[int, int, int, int]


@dataclass(frozen=True)
class VennIconPlan:
    """Task-provided icon semantics and requested Venn category."""

    shape_id: str
    color_name: str
    tint_rgb: Tuple[int, int, int]
    fill_style: str
    venn_category: str
    matches_target: bool


@dataclass(frozen=True)
class RenderedVennIcon:
    """Rendered icon record with projected geometry and target flags."""

    instance_id: str
    shape_id: str
    shape_name: str
    color_name: str
    bbox_xyxy: Tuple[int, int, int, int]
    center_xy: Tuple[float, float]
    nominal_size_px: int
    rotation_degrees: int
    tint_rgb: Tuple[int, int, int]
    fill_style: str
    venn_category: str
    inside_left_circle: bool
    inside_right_circle: bool
    matches_target: bool
    counted: bool
    noise_edits: Tuple[Dict[str, Any], ...]
    noise_seed: int | None


@dataclass(frozen=True)
class VennScenePayload:
    """Rendered Venn-field scene plus trace-facing sampling metadata."""

    image: Image.Image
    panel_geometry: Dict[str, Any]
    venn: VennSpec
    target_count: int
    object_count: int
    instances: Tuple[RenderedVennIcon, ...]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]


__all__ = [
    "NamedColorEntry",
    "RenderedVennIcon",
    "VennIconPlan",
    "VennScenePayload",
    "VennSpec",
]
