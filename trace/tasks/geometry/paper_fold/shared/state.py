"""State containers for paper-fold diagram rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from PIL import Image, ImageDraw

from trace.tasks.geometry.shared.scene_transform import LazySceneTransform

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]


@dataclass(frozen=True)
class FoldGeometry:
    """Analytic folded-corner geometry before pixel projection."""

    height_units: float
    folded_offset_units: float
    width_units: float
    upper_segment_units: float
    lower_segment_units: float
    half_angle_degrees: float
    total_angle_degrees: float


@dataclass(frozen=True)
class FoldAnglePlan:
    """Task-bound numeric fold-angle plan for one sample."""

    answer: float
    geometry: FoldGeometry
    params: Dict[str, Any]
    support_probabilities: Dict[str, float]


@dataclass
class RenderContext:
    """Render context for one final paper-fold image."""

    rng: Any
    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    background_color: Color
    line_color: Color
    label_color: Color
    label_stroke_color: Color
    paper_fill_color: Color
    folded_fill_color: Color
    crease_color: Color
    dashed_color: Color
    line_width: int
    font: Any
    small_font: Any
    point_font: Any
    scene_transform: LazySceneTransform


@dataclass(frozen=True)
class RenderedPaperFoldScene:
    """Rendered paper-fold scene plus verifier payload fragments."""

    image: Image.Image
    answer: float
    annotation_bboxes: Mapping[str, BBox]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]
    reasoning_steps: int


__all__ = [
    "BBox",
    "Color",
    "FoldAnglePlan",
    "FoldGeometry",
    "Point",
    "RenderContext",
    "RenderedPaperFoldScene",
]
