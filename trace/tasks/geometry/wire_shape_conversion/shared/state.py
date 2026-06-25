"""State objects for wire-shape-conversion construction and rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageDraw

Point = tuple[float, float]
BBox = tuple[float, float, float, float]
Color = tuple[int, int, int]


@dataclass(frozen=True)
class ResolvedProblem:
    source_shape: str
    target_shape: str
    source_values: dict[str, int]
    target_values: dict[str, int]
    answer: int
    formula_family: str
    formula: str
    case_probabilities: dict[str, float]
    answer_support_probabilities: dict[str, float]


@dataclass
class RenderContext:
    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    line_color: Color
    secondary_color: Color
    label_color: Color
    label_stroke_color: Color
    source_fill: Color
    target_fill: Color
    accent_color: Color
    muted_color: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: dict[str, Any]
    background_meta: dict[str, Any]


@dataclass(frozen=True)
class RenderedScene:
    image: Image.Image
    annotation_bboxes: dict[str, BBox]
    label_bboxes: dict[str, BBox]
    scene_entities: tuple[dict[str, Any], ...]
    render_map: dict[str, Any]


__all__ = [
    "BBox",
    "Color",
    "Point",
    "RenderContext",
    "RenderedScene",
    "ResolvedProblem",
]
