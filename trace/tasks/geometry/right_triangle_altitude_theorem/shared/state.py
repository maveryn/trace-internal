"""State containers for right-triangle altitude theorem diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple

from PIL import Image, ImageDraw

from trace.tasks.geometry.shared.scene_transform import LazySceneTransform

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]


@dataclass(frozen=True)
class TheoremValues:
    """Integer measurements satisfying right-triangle altitude relations."""

    left_projection: int
    right_projection: int
    altitude: int
    left_leg: int | None = None
    right_leg: int | None = None

    @property
    def hypotenuse(self) -> int:
        return int(self.left_projection) + int(self.right_projection)


@dataclass(frozen=True)
class RightTriangleAltitudeProblem:
    """One solved right-triangle altitude theorem case."""

    answer: int
    target_name: str
    target_role: str
    relation: str
    values: TheoremValues
    visible_labels: Mapping[str, str]
    case_index: int
    layout_seed: int


@dataclass
class RenderContext:
    """Styled canvas resources for one rendered scene."""

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
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: dict[str, Any]
    background_meta: dict[str, Any]
    scene_transform: LazySceneTransform


@dataclass(frozen=True)
class SceneGeometry:
    """Projected labeled construction points for the scene."""

    points: dict[str, Point]
    labels: dict[str, str]


@dataclass(frozen=True)
class RenderedRightTriangleAltitudeScene:
    """Rendered image and projected annotation geometry."""

    image: Image.Image
    geometry: SceneGeometry
    annotation_points: dict[str, Point]
    point_label_bboxes: dict[str, BBox]
    readout_bboxes: dict[str, BBox]
    construction_bboxes: dict[str, BBox]
    render_map: dict[str, Any]


__all__ = [
    "BBox",
    "Color",
    "Point",
    "RenderContext",
    "RenderedRightTriangleAltitudeScene",
    "RightTriangleAltitudeProblem",
    "SceneGeometry",
    "TheoremValues",
]
