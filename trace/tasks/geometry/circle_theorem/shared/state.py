"""State contracts and scene-level constants for circle-theorem diagrams."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....shared.prompt_json_example import dump_prompt_json_examples
from ...shared.background_defaults import load_geometry_background_defaults
from ...shared.noise_defaults import load_geometry_noise_defaults

DOMAIN = "geometry"
SCENE_ID = "circle_theorem"

Point = Tuple[float, float]

BBox = Tuple[float, float, float, float]

def _build_keyed_point_prompt_examples(
    *, annotation_point_labels: Sequence[str]
) -> Tuple[str, str]:
    """Build a clear JSON example for labeled construction-point annotation."""
    example_points = {
        str(label): [120 + (37 * index), 180 + (23 * index)]
        for index, label in enumerate(annotation_point_labels)
    }
    return dump_prompt_json_examples(annotation=example_points, answer=8, ensure_ascii=False)

DIAMETER_CHORD_ANSWER_SUPPORT: Tuple[int, ...] = (4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18)

TANGENT_SECANT_ANSWER_SUPPORT: Tuple[int, ...] = (
    11,
    13,
    14,
    15,
    16,
    17,
    18,
    20,
    21,
    22,
    24,
    25,
    26,
    27,
    28,
    30,
    32,
    33,
    35,
    36,
    39,
    40,
    42,
    44,
    45,
    48,
    49,
    50,
    51,
    52,
    54,
    55,
    56,
    57,
    60,
    63,
    64,
    65,
    66,
    70,
    72,
    75,
    78,
    80,
    84,
    88,
    90,
    96,
    100,
)

SECANT_SECANT_ANSWER_SUPPORT: Tuple[int, ...] = tuple(range(3, 16))

VARIABLE_SECANT_ANSWER_SUPPORT: Tuple[int, ...] = tuple(range(4, 61))

INTERSECTING_CHORDS_ARC_ANSWER_SUPPORT: Tuple[int, ...] = tuple(range(40, 181, 10))

MULTI_STEP_ANGLE_ANSWER_SUPPORT: Tuple[int, ...] = tuple(range(45, 136, 5))

INSCRIBED_ANGLE_ANSWER_SUPPORT: Tuple[int, ...] = tuple(range(20, 81, 5))

CENTRAL_ANGLE_ANSWER_SUPPORT: Tuple[int, ...] = tuple(range(40, 161, 10))

TANGENT_CHORD_ANGLE_ANSWER_SUPPORT: Tuple[int, ...] = tuple(range(25, 76, 5))

EXTERNAL_SECANT_ANGLE_ANSWER_SUPPORT: Tuple[int, ...] = tuple(range(20, 76, 5))

CYCLIC_QUADRILATERAL_ANGLE_SUPPORT: Tuple[int, ...] = tuple(range(45, 136, 5))

TANGENT_SECANT_TARGET_KINDS: Tuple[str, ...] = ("outside", "inside", "tangent")

VARIABLE_SECANT_TARGET_KINDS: Tuple[str, ...] = (
    "outside_first",
    "inside_first",
    "outside_second",
    "inside_second",
)

POINT_LABEL_ALPHABET: Tuple[str, ...] = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

CENTER_LABEL = "O"

BACKGROUND_DEFAULTS = load_geometry_background_defaults(scene_id="circle")

POST_IMAGE_NOISE_DEFAULTS = load_geometry_noise_defaults(scene_id="circle")

@dataclass(frozen=True)
class _Defaults:
    canvas_size_min: int = 720
    canvas_size_max: int = 820
    scene_supersample_scale: int = 1
    outer_margin_px: int = 78
    line_width: int = 4
    line_width_min: int = 3
    line_width_max: int = 5
    circle_line_width: int = 4
    point_radius_px: int = 5
    label_font_size_min: int = 19
    label_font_size_max: int = 25
    measurement_font_size_min: int = 17
    measurement_font_size_max: int = 23
    measurement_label_offset_px: int = 38
    point_label_offset_px: int = 36

@dataclass(frozen=True)
class CircleTheoremProblem:
    """Task-selected numeric target and optional construction target kind."""

    target_answer: int
    target_answer_probabilities: Dict[str, float]
    tangent_secant_target_kind: str | None = None
    tangent_secant_target_kind_probabilities: Dict[str, float] | None = None
    secant_secant_variable_target_kind: str | None = None
    secant_secant_variable_target_kind_probabilities: Dict[str, float] | None = None

@dataclass(frozen=True)
class RenderedCircleTheoremScene:
    """Rendered circle-theorem diagram and projected metadata."""

    image: Image.Image
    answer_value: float
    support_measurement_tokens: List[str]
    annotation_point_labels: List[str]
    token_bboxes: Dict[str, List[float]]
    point_pixels: Dict[str, List[float]]
    point_label_bboxes: Dict[str, List[float]]
    point_model: Dict[str, List[float]]
    segment_pixels: Dict[str, List[List[float]]]
    circle_center_pixel: List[float]
    circle_center_model: List[float]
    circle_radius_model: float
    circle_radius_px: float
    annotation_values: Dict[str, int]
    theorem_trace: Dict[str, Any]
    scene_entities: List[Dict[str, Any]]
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    shape_style: Dict[str, Any]
    render_params: Dict[str, Any]

DEFAULTS = _Defaults()

def _text_bbox_for_center(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Point,
    font,
    stroke_width: int,
) -> BBox:
    bbox = draw.textbbox(
        (0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width))
    )
    width = float(bbox[2] - bbox[0])
    height = float(bbox[3] - bbox[1])
    cx, cy = float(center[0]), float(center[1])
    return (
        float(cx - (0.5 * width)),
        float(cy - (0.5 * height)),
        float(cx + (0.5 * width)),
        float(cy + (0.5 * height)),
    )

def _bbox_to_list(bbox: BBox) -> List[float]:
    return [float(round(value, 2)) for value in bbox]

def _circle_from_three_points(a: Point, b: Point, c: Point) -> Tuple[Point, float]:
    ax, ay = float(a[0]), float(a[1])
    bx, by = float(b[0]), float(b[1])
    cx, cy = float(c[0]), float(c[1])
    determinant = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(determinant) <= 1e-9:
        raise ValueError("cannot build a circle from collinear points")
    ax2ay2 = ax * ax + ay * ay
    bx2by2 = bx * bx + by * by
    cx2cy2 = cx * cx + cy * cy
    ux = (ax2ay2 * (by - cy) + bx2by2 * (cy - ay) + cx2cy2 * (ay - by)) / determinant
    uy = (ax2ay2 * (cx - bx) + bx2by2 * (ax - cx) + cx2cy2 * (bx - ax)) / determinant
    radius = math.hypot(ax - ux, ay - uy)
    return (float(ux), float(uy)), float(radius)

def _sample_point_label_map(rng, canonical_labels: Sequence[str]) -> Dict[str, str]:
    """Map canonical construction labels to random visible one-letter labels."""

    labels = [str(label) for label in canonical_labels]
    if len(set(labels)) != len(labels):
        raise ValueError("canonical point labels must be unique")
    sample_pool = [label for label in POINT_LABEL_ALPHABET if label != CENTER_LABEL]
    if CENTER_LABEL in labels:
        if len(labels) - 1 > len(sample_pool):
            raise ValueError(
                "not enough visible point labels for circle theorem diagram"
            )
        sampled = iter(rng.sample(sample_pool, len(labels) - 1))
        return {
            canonical: (
                CENTER_LABEL if canonical == CENTER_LABEL else str(next(sampled))
            )
            for canonical in labels
        }
    if len(labels) > len(sample_pool):
        raise ValueError("not enough visible point labels for circle theorem diagram")
    visible = list(rng.sample(sample_pool, len(labels)))
    return {canonical: str(sampled) for canonical, sampled in zip(labels, visible)}

def _visible_segment(label_map: Mapping[str, str], *canonical_labels: str) -> str:
    return "".join(str(label_map[str(label)]) for label in canonical_labels)

def _visible_angle(label_map: Mapping[str, str], *canonical_labels: str) -> str:
    return "∠" + _visible_segment(label_map, *canonical_labels)

def _visible_arc(label_map: Mapping[str, str], *canonical_labels: str) -> str:
    return "arc " + _visible_segment(label_map, *canonical_labels)

def _line_intersection(a: Point, b: Point, c: Point, d: Point) -> Point:
    ax, ay = float(a[0]), float(a[1])
    bx, by = float(b[0]), float(b[1])
    cx, cy = float(c[0]), float(c[1])
    dx, dy = float(d[0]), float(d[1])
    denominator = (ax - bx) * (cy - dy) - (ay - by) * (cx - dx)
    if abs(float(denominator)) <= 1e-9:
        raise ValueError("cannot intersect parallel chord lines")
    px = (
        (ax * by - ay * bx) * (cx - dx) - (ax - bx) * (cx * dy - cy * dx)
    ) / denominator
    py = (
        (ax * by - ay * bx) * (cy - dy) - (ay - by) * (cx * dy - cy * dx)
    ) / denominator
    return (float(px), float(py))

def _angle_degrees_at(vertex: Point, arm0: Point, arm1: Point) -> int:
    vx, vy = float(vertex[0]), float(vertex[1])
    v0x, v0y = float(arm0[0]) - vx, float(arm0[1]) - vy
    v1x, v1y = float(arm1[0]) - vx, float(arm1[1]) - vy
    n0 = max(1e-9, math.hypot(v0x, v0y))
    n1 = max(1e-9, math.hypot(v1x, v1y))
    dot = max(-1.0, min(1.0, ((v0x * v1x) + (v0y * v1y)) / (n0 * n1)))
    angle = math.degrees(math.acos(dot))
    if angle > 180.0:
        angle = 360.0 - angle
    return int(round(float(angle)))

__all__ = [
    'BACKGROUND_DEFAULTS',
    'Point',
    'BBox',
    'CENTER_LABEL',
    'CENTRAL_ANGLE_ANSWER_SUPPORT',
    'CYCLIC_QUADRILATERAL_ANGLE_SUPPORT',
    'CircleTheoremProblem',
    'DEFAULTS',
    'DIAMETER_CHORD_ANSWER_SUPPORT',
    'DOMAIN',
    'EXTERNAL_SECANT_ANGLE_ANSWER_SUPPORT',
    'INSCRIBED_ANGLE_ANSWER_SUPPORT',
    'INTERSECTING_CHORDS_ARC_ANSWER_SUPPORT',
    'MULTI_STEP_ANGLE_ANSWER_SUPPORT',
    'POINT_LABEL_ALPHABET',
    'POST_IMAGE_NOISE_DEFAULTS',
    'RenderedCircleTheoremScene',
    'SCENE_ID',
    'SECANT_SECANT_ANSWER_SUPPORT',
    'TANGENT_CHORD_ANGLE_ANSWER_SUPPORT',
    'TANGENT_SECANT_ANSWER_SUPPORT',
    'TANGENT_SECANT_TARGET_KINDS',
    'VARIABLE_SECANT_ANSWER_SUPPORT',
    'VARIABLE_SECANT_TARGET_KINDS',
    '_build_keyed_point_prompt_examples',
    '_Defaults',
    '_text_bbox_for_center',
    '_bbox_to_list',
    '_circle_from_three_points',
    '_sample_point_label_map',
    '_visible_segment',
    '_visible_angle',
    '_visible_arc',
    '_line_intersection',
    '_angle_degrees_at',
]
