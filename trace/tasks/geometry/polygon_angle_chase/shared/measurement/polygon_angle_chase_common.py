"""Common records and formatting helpers for polygon angle-chase tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Sequence, Tuple

from PIL import Image, ImageDraw

from .....shared.prompt_json_example import dump_prompt_json_examples
from ....shared.scene_transform import LazySceneTransform

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SCENE_ID = "polygon_angle_chase"
PROMPT_BUNDLE_ID = "geometry_polygon_angle_chase_v0"
POLYGON_INTERIOR_NAMESPACE = "polygon_interior_angle_value"
PARALLEL_LINE_NAMESPACE = "parallel_line_angle_value"
SYMMETRY_ANGLE_NAMESPACE = "symmetry_angle_value"
DEGREE_SYMBOL = chr(176)

_QUERY_SIDE_COUNTS: Dict[str, int] = {
    "triangle_interior_angle": 3,
    "quadrilateral_interior_angle": 4,
    "pentagon_interior_angle": 5,
    "hexagon_interior_angle": 6,
}
_PARALLEL_QUERY_IDS: Tuple[str, ...] = ("single_transversal_chain", "two_transversal_angle_sum")
_SINGLE_TRANSVERSAL_RELATIONS: Tuple[str, ...] = ("corresponding_same", "supplementary")
_SYMMETRY_QUERY_IDS: Tuple[str, ...] = (
    "rectangle_diagonal_angle",
    "reflection_axis_angle",
    "isosceles_base_angle_chain",
)
_ISOSCELES_TARGET_ROLES: Tuple[str, ...] = ("base_angle", "apex_angle")
_LABEL_STYLES: Tuple[str, ...] = ("target_expression_mixed", "all_expression")
_VERTEX_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

@dataclass(frozen=True)
class _ResolvedPolygonProblem:
    query_id: str
    side_count: int
    target_index: int
    target_angle_name: str
    labels: Tuple[str, ...]
    numeric_angles: Tuple[int, ...]
    display_angle_labels: Tuple[str, ...]
    answer: int
    label_style: str
    expression_vertex_index: int | None
    query_probabilities: Dict[str, float]
    label_style_probabilities: Dict[str, float]
    witness: Dict[str, Any]

@dataclass(frozen=True)
class _ResolvedParallelLineProblem:
    query_id: str
    relation_id: str
    support_angles: Tuple[int, ...]
    answer: int
    target_angle_label: str
    query_probabilities: Dict[str, float]
    relation_probabilities: Dict[str, float]
    witness: Dict[str, Any]

@dataclass(frozen=True)
class _ResolvedSymmetryAngleProblem:
    query_id: str
    relation_id: str
    support_angle: int
    answer: int
    target_angle_label: str
    target_role: str
    query_probabilities: Dict[str, float]
    target_role_probabilities: Dict[str, float]
    witness: Dict[str, Any]

@dataclass
class _RenderContext:
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
    diagram_style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]
    scene_transform: LazySceneTransform

@dataclass(frozen=True)
class _RenderedPolygonScene:
    image: Image.Image
    annotation_keyed_points: Dict[str, Point]
    annotation_roles: Tuple[str, ...]
    point_label_bboxes: Dict[str, BBox]
    angle_arc_bboxes: Dict[str, BBox]
    angle_label_bboxes: Dict[str, BBox]
    vertices: Tuple[Point, ...]

@dataclass(frozen=True)
class _RenderedParallelLineScene:
    image: Image.Image
    annotation_keyed_points: Dict[str, Point]
    annotation_roles: Tuple[str, ...]
    angle_arc_bboxes: Dict[str, BBox]
    angle_label_bboxes: Dict[str, BBox]
    line_segments: Dict[str, Tuple[Point, Point]]
    intersections: Dict[str, Point]

@dataclass(frozen=True)
class _RenderedSymmetryAngleScene:
    image: Image.Image
    annotation_keyed_points: Dict[str, Point]
    annotation_roles: Tuple[str, ...]
    angle_arc_bboxes: Dict[str, BBox]
    angle_label_bboxes: Dict[str, BBox]
    construction_segments: Dict[str, Tuple[Point, Point]]
    construction_points: Dict[str, Point]

def _query_angle_sum(side_count: int) -> int:
    return int(side_count - 2) * 180

def _polygon_kind(side_count: int) -> str:
    if int(side_count) == 3:
        return "triangle"
    if int(side_count) == 4:
        return "quadrilateral"
    if int(side_count) == 5:
        return "pentagon"
    if int(side_count) == 6:
        return "hexagon"
    return f"{int(side_count)}-gon"

def _angle_name(labels: Sequence[str], index: int) -> str:
    side_count = len(labels)
    prev_label = str(labels[(int(index) - 1) % side_count])
    vertex_label = str(labels[int(index) % side_count])
    next_label = str(labels[(int(index) + 1) % side_count])
    return f"{prev_label}{vertex_label}{next_label}"

def _format_degrees(value: int) -> str:
    return f"{int(value)}{DEGREE_SYMBOL}"

def _format_linear_expression(coefficient: int, constant: int) -> str:
    coeff = int(coefficient)
    const = int(constant)
    if coeff == 1:
        body = "x"
    elif coeff == -1:
        body = "-x"
    else:
        body = f"{coeff}x"
    if const > 0:
        return f"{body}+{const}"
    if const < 0:
        return f"{body}{const}"
    return body

def _format_angle_expression(coefficient: int, constant: int) -> str:
    expression = _format_linear_expression(coefficient, constant)
    if int(coefficient) == 1 and int(constant) == 0:
        return f"x{DEGREE_SYMBOL}"
    return f"({expression}){DEGREE_SYMBOL}"

def _bbox_overlaps(a: BBox, b: BBox, *, pad: float = 3.0) -> bool:
    ax0, ay0, ax1, ay1 = [float(value) for value in a]
    bx0, by0, bx1, by1 = [float(value) for value in b]
    return not (
        ax1 + float(pad) < bx0
        or bx1 + float(pad) < ax0
        or ay1 + float(pad) < by0
        or by1 + float(pad) < ay0
    )

def _assert_non_overlapping(bboxes: Sequence[BBox]) -> None:
    for left_index, left in enumerate(bboxes):
        for right in bboxes[left_index + 1 :]:
            if _bbox_overlaps(left, right, pad=2.0):
                raise ValueError("polygon angle label layout overlaps")

def _make_prompt_examples(annotation_keys: Sequence[str]) -> tuple[str, str]:
    annotation = {
        str(key): [120 + (index * 45), 180 + (index * 18)]
        for index, key in enumerate(annotation_keys)
    }
    return dump_prompt_json_examples(annotation=annotation, answer=85, ensure_ascii=False)


__all__ = [
    '_ResolvedPolygonProblem',
    '_ResolvedParallelLineProblem',
    '_ResolvedSymmetryAngleProblem',
    '_RenderContext',
    '_RenderedPolygonScene',
    '_RenderedParallelLineScene',
    '_RenderedSymmetryAngleScene',
    '_query_angle_sum',
    '_polygon_kind',
    '_angle_name',
    '_format_degrees',
    '_format_linear_expression',
    '_format_angle_expression',
    '_bbox_overlaps',
    '_assert_non_overlapping',
    '_make_prompt_examples',
    'Point',
    'BBox',
    'Color',
    'SCENE_ID',
    'SCENE_ID',
    'PROMPT_BUNDLE_ID',
    'POLYGON_INTERIOR_NAMESPACE',
    'PARALLEL_LINE_NAMESPACE',
    'SYMMETRY_ANGLE_NAMESPACE',
    'DEGREE_SYMBOL',
    '_QUERY_SIDE_COUNTS',
    '_PARALLEL_QUERY_IDS',
    '_SINGLE_TRANSVERSAL_RELATIONS',
    '_SYMMETRY_QUERY_IDS',
    '_ISOSCELES_TARGET_ROLES',
    '_LABEL_STYLES',
    '_VERTEX_LABELS',
]
