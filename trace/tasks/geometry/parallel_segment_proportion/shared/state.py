"""State containers for parallel-segment proportion diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from PIL import Image, ImageDraw

from trace.tasks.geometry.shared.scene_transform import LazySceneTransform

Point = Tuple[float, float]
Segment = Tuple[Point, Point]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]


@dataclass(frozen=True)
class ParallelProportionPlan:
    """Task-bound construction parameters before pixel rendering."""

    construction_family: str
    answer: float
    target_name: str
    variable_name: str
    labels: Dict[str, str]
    relation: str
    formula_family: str
    answer_support: Tuple[int, ...]
    params: Dict[str, Any]


@dataclass
class RenderContext:
    """Styled render context for one parallel-segment diagram."""

    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    line_color: Color
    secondary_color: Color
    label_color: Color
    label_stroke_color: Color
    accent_color: Color
    fill_color: Color
    muted_color: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]
    scene_transform: LazySceneTransform


@dataclass(frozen=True)
class RenderedParallelProportionScene:
    """Rendered image plus verifier-facing scene fragments."""

    image: Image.Image
    annotation_points: Dict[str, Point]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]


__all__ = [
    "BBox",
    "Color",
    "ParallelProportionPlan",
    "Point",
    "RenderContext",
    "RenderedParallelProportionScene",
    "Segment",
]
