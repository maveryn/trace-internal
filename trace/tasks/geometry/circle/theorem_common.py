"""Shared circle-theorem constants and geometry helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.prompt_json_example import dump_prompt_json_examples
from ...shared.support_sampling import resolve_integer_choice
from ...shared.text_rendering import (
    draw_text_centered,
    load_font,
    resolve_text_label_center,
)
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.background_defaults import load_geometry_background_defaults
from ..shared.complexity import build_geometry_circle_theorem_complexity
from ..shared.fixed_query_task import (
    FixedGeometryQueryTaskMixin,
    MultiFixedGeometryQueryTaskMixin,
)
from ..shared.noise_defaults import load_geometry_noise_defaults
from ..shared.render_variation import sample_int_render_param
from ..shared.shape_style import (
    extract_background_anchor_colors,
    sample_geometry_shape_style,
)

Point = Tuple[float, float]

BBox = Tuple[float, float, float, float]

TASK_ID = "geometry_circle_theorem_value_base"

SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "diameter_perpendicular_chord_length",
    "secant_secant_variable_segment_length",
    "tangent_secant_length",
    "secant_secant_length",
    "intersecting_chords_arc_measure",
    "multi_step_angle_value",
    "inscribed_angle_from_central",
    "central_angle_from_inscribed",
    "inscribed_angle_from_arc",
    "tangent_chord_angle_from_arc",
    "tangent_chord_angle_from_inscribed",
    "external_two_secants_angle_from_arcs",
    "opposite_angle_supplement",
    "exterior_angle_from_opposite_interior",
)

def _build_keyed_point_prompt_examples(
    *, annotation_point_labels: Sequence[str]
) -> Tuple[str, str]:
    """Build a clear JSON example for labeled construction-point annotation."""
    example_points = {
        str(label): [120 + (37 * index), 180 + (23 * index)]
        for index, label in enumerate(annotation_point_labels)
    }
    return dump_prompt_json_examples(annotation=example_points, answer=8, ensure_ascii=False)

_DIAMETER_SUPPORT: Tuple[int, ...] = (4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18)

_TANGENT_SECANT_SUPPORT: Tuple[int, ...] = (
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

_SECANT_SECANT_SUPPORT: Tuple[int, ...] = tuple(range(3, 16))

_SECANT_SECANT_VARIABLE_SUPPORT: Tuple[int, ...] = tuple(range(4, 61))

_INTERSECTING_CHORDS_ARC_SUPPORT: Tuple[int, ...] = tuple(range(40, 181, 10))

_MULTI_STEP_ANGLE_SUPPORT: Tuple[int, ...] = tuple(range(45, 136, 5))

_INSCRIBED_ANGLE_SUPPORT: Tuple[int, ...] = tuple(range(20, 81, 5))

_CENTRAL_ANGLE_SUPPORT: Tuple[int, ...] = tuple(range(40, 161, 10))

_TANGENT_CHORD_ANGLE_SUPPORT: Tuple[int, ...] = tuple(range(25, 76, 5))

_EXTERNAL_SECANT_ANGLE_SUPPORT: Tuple[int, ...] = tuple(range(20, 76, 5))

_CYCLIC_QUADRILATERAL_ANGLE_SUPPORT: Tuple[int, ...] = tuple(range(45, 136, 5))

_ANSWER_SUPPORT_BY_VARIANT: Dict[str, Tuple[int, ...]] = {
    "diameter_perpendicular_chord_length": _DIAMETER_SUPPORT,
    "secant_secant_variable_segment_length": _SECANT_SECANT_VARIABLE_SUPPORT,
    "tangent_secant_length": _TANGENT_SECANT_SUPPORT,
    "secant_secant_length": _SECANT_SECANT_SUPPORT,
    "intersecting_chords_arc_measure": _INTERSECTING_CHORDS_ARC_SUPPORT,
    "multi_step_angle_value": _MULTI_STEP_ANGLE_SUPPORT,
    "inscribed_angle_from_central": _INSCRIBED_ANGLE_SUPPORT,
    "central_angle_from_inscribed": _CENTRAL_ANGLE_SUPPORT,
    "inscribed_angle_from_arc": _INSCRIBED_ANGLE_SUPPORT,
    "tangent_chord_angle_from_arc": _TANGENT_CHORD_ANGLE_SUPPORT,
    "tangent_chord_angle_from_inscribed": _TANGENT_CHORD_ANGLE_SUPPORT,
    "external_two_secants_angle_from_arcs": _EXTERNAL_SECANT_ANGLE_SUPPORT,
    "opposite_angle_supplement": _CYCLIC_QUADRILATERAL_ANGLE_SUPPORT,
    "exterior_angle_from_opposite_interior": _CYCLIC_QUADRILATERAL_ANGLE_SUPPORT,
}

_TANGENT_SECANT_TARGET_KINDS: Tuple[str, ...] = ("outside", "inside", "tangent")

_SECANT_SECANT_VARIABLE_TARGET_KINDS: Tuple[str, ...] = (
    "outside_first",
    "inside_first",
    "outside_second",
    "inside_second",
)

_POINT_LABEL_ALPHABET: Tuple[str, ...] = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

_CENTER_LABEL = "O"

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "circle")

_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = (
    split_generation_rendering_prompt_defaults(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=TASK_ID,
    )
)

_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="circle")

_POST_IMAGE_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="circle")

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
class _ResolvedQuery:
    query_id: str
    target_answer: int
    query_id_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    tangent_secant_target_kind: str | None = None
    tangent_secant_target_kind_probabilities: Dict[str, float] | None = None
    secant_secant_variable_target_kind: str | None = None
    secant_secant_variable_target_kind_probabilities: Dict[str, float] | None = None

@dataclass(frozen=True)
class _RenderedScene:
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

_DEFAULTS = _Defaults()

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
    sample_pool = [label for label in _POINT_LABEL_ALPHABET if label != _CENTER_LABEL]
    if _CENTER_LABEL in labels:
        if len(labels) - 1 > len(sample_pool):
            raise ValueError(
                "not enough visible point labels for circle theorem diagram"
            )
        sampled = iter(rng.sample(sample_pool, len(labels) - 1))
        return {
            canonical: (
                _CENTER_LABEL if canonical == _CENTER_LABEL else str(next(sampled))
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
    'Point',
    'BBox',
    'TASK_ID',
    'SUPPORTED_QUERY_IDS',
    '_build_keyed_point_prompt_examples',
    '_DIAMETER_SUPPORT',
    '_TANGENT_SECANT_SUPPORT',
    '_SECANT_SECANT_SUPPORT',
    '_SECANT_SECANT_VARIABLE_SUPPORT',
    '_INTERSECTING_CHORDS_ARC_SUPPORT',
    '_MULTI_STEP_ANGLE_SUPPORT',
    '_INSCRIBED_ANGLE_SUPPORT',
    '_CENTRAL_ANGLE_SUPPORT',
    '_TANGENT_CHORD_ANGLE_SUPPORT',
    '_EXTERNAL_SECANT_ANGLE_SUPPORT',
    '_CYCLIC_QUADRILATERAL_ANGLE_SUPPORT',
    '_ANSWER_SUPPORT_BY_VARIANT',
    '_TANGENT_SECANT_TARGET_KINDS',
    '_SECANT_SECANT_VARIABLE_TARGET_KINDS',
    '_POINT_LABEL_ALPHABET',
    '_CENTER_LABEL',
    '_TASK_GROUP_DEFAULTS',
    '_GEN_DEFAULTS',
    '_RENDER_DEFAULTS',
    '_PROMPT_DEFAULTS',
    '_BACKGROUND_DEFAULTS',
    '_POST_IMAGE_NOISE_DEFAULTS',
    '_Defaults',
    '_ResolvedQuery',
    '_RenderedScene',
    '_DEFAULTS',
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
