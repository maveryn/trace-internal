"""State types for split-triangle angle-chase diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from PIL import Image, ImageDraw

from trace.tasks.geometry.shared.scene_transform import LazySceneTransform

DOMAIN = "geometry"
SCENE_ID = "split_triangle_angle_chase"
DEGREE_SYMBOL = chr(176)

Point = tuple[float, float]
BBox = tuple[float, float, float, float]
Color = tuple[int, int, int]


@dataclass(frozen=True)
class SplitTriangleAngleCase:
    """One theorem case selected by the public task before rendering."""

    render_kind: str
    relation: str
    answer: int
    target_name: str
    labels: Mapping[str, str]
    values: Mapping[str, float | int | str]
    variable_name: str = "x"


@dataclass
class RenderContext:
    """Pillow drawing context plus sampled diagram style and transform."""

    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    line_color: Color
    secondary_color: Color
    label_color: Color
    label_stroke_color: Color
    label_backing_color: Color
    fill_color: Color
    alt_fill_color: Color
    muted_color: Color
    accent_color: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: dict[str, Any]
    background_meta: dict[str, Any]
    scene_transform: LazySceneTransform


@dataclass(frozen=True)
class RenderedSplitTriangleScene:
    """Rendered image and point/bbox metadata for one split-triangle diagram."""

    image: Image.Image
    annotation_points: dict[str, Point]
    render_map: dict[str, Any]


__all__ = [
    "BBox",
    "Color",
    "DEGREE_SYMBOL",
    "DOMAIN",
    "Point",
    "RenderContext",
    "RenderedSplitTriangleScene",
    "SCENE_ID",
    "SplitTriangleAngleCase",
]
