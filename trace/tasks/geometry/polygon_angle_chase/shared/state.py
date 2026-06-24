"""State records for polygon angle-chase scene primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from PIL import Image, ImageDraw

from ...shared.scene_transform import LazySceneTransform

Point = tuple[float, float]
BBox = tuple[float, float, float, float]
Color = tuple[int, int, int]


@dataclass(frozen=True)
class PolygonAnglePlan:
    """Resolved numeric/algebraic polygon angle-chase construction."""

    side_count: int
    target_index: int
    target_angle_name: str
    labels: tuple[str, ...]
    numeric_angles: tuple[int, ...]
    display_angle_labels: tuple[str, ...]
    answer: int
    label_style: str
    label_style_probabilities: Mapping[str, float]
    witness: Mapping[str, Any]


@dataclass(frozen=True)
class ParallelAnglePlan:
    """Resolved parallel-line angle construction."""

    construction_kind: str
    relation_id: str
    support_angles: tuple[int, ...]
    answer: int
    target_angle_label: str
    relation_probabilities: Mapping[str, float]
    witness: Mapping[str, Any]


@dataclass(frozen=True)
class SymmetryAnglePlan:
    """Resolved symmetry/equal-side angle construction."""

    construction_kind: str
    relation_id: str
    support_angle: int
    answer: int
    target_angle_label: str
    target_role: str
    target_role_probabilities: Mapping[str, float]
    witness: Mapping[str, Any]


@dataclass
class RenderContext:
    """Canvas and sampled style state for one rendered scene."""

    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    line_color: Color
    secondary_color: Color
    label_color: Color
    label_stroke_color: Color
    fill_color: Color
    accent_color: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: dict[str, Any]
    background_meta: dict[str, Any]
    scene_transform: LazySceneTransform


@dataclass(frozen=True)
class RenderedPolygonAngleScene:
    """Rendered polygon angle scene plus projected visual witnesses."""

    image: Image.Image
    annotation_keyed_points: dict[str, Point]
    annotation_roles: tuple[str, ...]
    point_label_bboxes: dict[str, BBox]
    angle_arc_bboxes: dict[str, BBox]
    angle_label_bboxes: dict[str, BBox]
    vertices: tuple[Point, ...]


@dataclass(frozen=True)
class RenderedParallelAngleScene:
    """Rendered parallel-line scene plus projected visual witnesses."""

    image: Image.Image
    annotation_keyed_points: dict[str, Point]
    annotation_roles: tuple[str, ...]
    angle_arc_bboxes: dict[str, BBox]
    angle_label_bboxes: dict[str, BBox]
    line_segments: dict[str, tuple[Point, Point]]
    intersections: dict[str, Point]


@dataclass(frozen=True)
class RenderedSymmetryAngleScene:
    """Rendered symmetry angle scene plus projected visual witnesses."""

    image: Image.Image
    annotation_keyed_points: dict[str, Point]
    annotation_roles: tuple[str, ...]
    angle_arc_bboxes: dict[str, BBox]
    angle_label_bboxes: dict[str, BBox]
    construction_segments: dict[str, tuple[Point, Point]]
    construction_points: dict[str, Point]


__all__ = [
    "BBox",
    "Color",
    "ParallelAnglePlan",
    "Point",
    "PolygonAnglePlan",
    "RenderContext",
    "RenderedParallelAngleScene",
    "RenderedPolygonAngleScene",
    "RenderedSymmetryAngleScene",
    "SymmetryAnglePlan",
]
