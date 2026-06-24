"""State containers for the triangle-congruence correspondence scene."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple

from PIL import Image, ImageDraw

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]
Side = Tuple[int, int]

DOMAIN = "geometry"
SCENE_ID = "triangle_congruence_correspondence"
SCENE_KIND = "congruent_triangle_pair"
PROMPT_BUNDLE_ID = "geometry_triangle_congruence_correspondence_v1"
SCENE_PROMPT_KEY = "triangle_congruence_correspondence_scene"

MEASUREMENT_SIDE = "side_length_transfer"
MEASUREMENT_ANGLE = "angle_measure_transfer"
MEASUREMENT_ALGEBRAIC_SIDE = "algebraic_side_length_transfer"


@dataclass(frozen=True)
class TriangleCongruenceCase:
    """Resolved congruent-triangle construction before rendering."""

    measurement_family: str
    layout_kind: str
    answer: int
    target_name: str
    relation: str
    source_target_side_value: int | None = None
    target_target_side_value: int | None = None
    source_angle_value: int | None = None
    target_angle_value: int | None = None
    x_value: int | None = None
    source_target_expression: str | None = None
    source_support_expression: str | None = None
    target_support_expression: str | None = None
    target_side: Side = (0, 1)
    source_side: Side = (0, 1)
    support_side: Side = (1, 2)
    target_angle_index: int = 0
    source_angle_index: int = 0
    show_statement: bool = False


@dataclass(frozen=True)
class TriangleCongruenceProblem:
    """Task-bound formula and render instructions for one sample."""

    case: TriangleCongruenceCase
    reasoning_steps: int
    layout_seed: int
    answer_support_probabilities: Mapping[str, float]


@dataclass
class RenderContext:
    """Canvas, style, and font handles used by rendering primitives."""

    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    line_color: Color
    secondary_color: Color
    label_color: Color
    label_stroke_color: Color
    accent_color: Color
    source_fill: Color
    target_fill: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: dict[str, Any]
    background_meta: dict[str, Any]


@dataclass(frozen=True)
class TriangleGeometry:
    """Pixel vertices and visible labels for the two congruent triangles."""

    source_vertices: tuple[Point, Point, Point]
    target_vertices: tuple[Point, Point, Point]
    source_labels: tuple[str, str, str]
    target_labels: tuple[str, str, str]
    statement: str


@dataclass(frozen=True)
class RenderedTriangleCongruenceScene:
    """Rendered image plus projected geometry metadata."""

    image: Image.Image
    geometry: TriangleGeometry
    annotation_keyed_points: Mapping[str, Point]
    point_label_bboxes: Mapping[str, BBox]
    readout_bboxes: Mapping[str, BBox]
    construction_bboxes: Mapping[str, BBox]
    render_map: Mapping[str, Any]
