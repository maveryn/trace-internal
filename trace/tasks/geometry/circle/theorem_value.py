"""Circle-theorem value task over composite measurement labeled circle diagrams."""

from __future__ import annotations

import json
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
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
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
)


def _build_measurement_bbox_prompt_examples(*, evidence_count: int) -> Tuple[str, str]:
    """Build a clear JSON example for measurement-label bbox evidence."""
    example_bboxes: List[List[int]] = []
    for index in range(max(0, int(evidence_count))):
        x0 = 10 + (80 * int(index))
        y0 = 20 + (28 * int(index))
        example_bboxes.append([x0, y0, x0 + 60, y0 + 24])
    example_answer = {"answer": 8}
    example_answer_and_evidence = {"evidence": example_bboxes, "answer": 8}
    return (
        json.dumps(
            example_answer_and_evidence,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ),
        json.dumps(
            example_answer, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ),
    )


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
    query_variant: str
    target_answer: int
    query_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    tangent_secant_target_kind: str | None = None
    tangent_secant_target_kind_probabilities: Dict[str, float] | None = None
    secant_secant_variable_target_kind: str | None = None
    secant_secant_variable_target_kind_probabilities: Dict[str, float] | None = None


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    answer_value: int
    evidence_tokens: List[str]
    evidence_bboxes: List[List[float]]
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


def _candidate_diameter_chord_values(target_answer: int) -> List[Dict[str, int]]:
    candidates: List[Dict[str, int]] = []
    for radius in range(8, 41):
        for offset in range(2, radius - 1):
            half_chord_sq = (radius * radius) - (offset * offset)
            half_chord = int(math.isqrt(int(half_chord_sq)))
            if int(half_chord * half_chord) != int(half_chord_sq):
                continue
            answer_value = int(radius - offset)
            if int(answer_value) != int(target_answer):
                continue
            chord_length = int(2 * half_chord)
            diameter_length = int(2 * radius)
            if half_chord < 4 or chord_length > 64:
                continue
            candidates.append(
                {
                    "radius": int(radius),
                    "offset": int(offset),
                    "half_chord": int(half_chord),
                    "diameter": int(diameter_length),
                    "chord": int(chord_length),
                    "answer": int(answer_value),
                }
            )
    return candidates


def _hard_tangent_secant_triple(*, outside: int, internal: int, tangent: int) -> bool:
    if int(outside) < 16 or int(internal) < 10:
        return False
    if len({int(outside), int(internal), int(tangent)}) != 3:
        return False
    if int(tangent) == int(2 * outside) or int(tangent) % int(outside) == 0:
        return False
    if int(internal) in {int(outside), int(2 * outside), int(3 * outside)}:
        return False
    if int(outside) % 2 == 0 and int(internal) == int(outside // 2):
        return False
    return True


def _candidate_tangent_secant_values(
    target_answer: int, *, target_kind: str | None = None
) -> List[Dict[str, int | str]]:
    if target_kind is not None and str(target_kind) not in _TANGENT_SECANT_TARGET_KINDS:
        raise ValueError(f"unsupported tangent secant target kind: {target_kind}")
    candidates: List[Dict[str, int | str]] = []
    for outside in range(16, 81):
        for internal in range(10, 71):
            tangent_sq = int(outside * (outside + internal))
            tangent = int(math.isqrt(tangent_sq))
            if int(tangent * tangent) != int(tangent_sq):
                continue
            if int(tangent) > 100:
                continue
            if not _hard_tangent_secant_triple(
                outside=int(outside), internal=int(internal), tangent=int(tangent)
            ):
                continue
            base_spec = {
                "PA": int(outside),
                "AB": int(internal),
                "PT": int(tangent),
                "PB": int(outside + internal),
            }
            target_options = {
                "outside": ("PA", int(outside)),
                "inside": ("AB", int(internal)),
                "tangent": ("PT", int(tangent)),
            }
            for option_kind, (answer_segment, answer_value) in target_options.items():
                if target_kind is not None and str(option_kind) != str(target_kind):
                    continue
                if int(answer_value) != int(target_answer):
                    continue
                candidates.append(
                    {
                        **base_spec,
                        "target_kind": str(option_kind),
                        "canonical_answer_segment": str(answer_segment),
                        "answer": int(answer_value),
                    }
                )
    return candidates


def _feasible_tangent_secant_target_kinds(target_answer: int) -> Tuple[str, ...]:
    kinds = sorted(
        {
            str(candidate["target_kind"])
            for candidate in _candidate_tangent_secant_values(int(target_answer))
        }
    )
    return tuple(kind for kind in _TANGENT_SECANT_TARGET_KINDS if kind in set(kinds))


def _candidate_secant_secant_values(target_answer: int) -> List[Dict[str, int]]:
    candidates: List[Dict[str, int]] = []
    pa = int(target_answer)
    for ab in range(11, 35):
        power = int(pa * (pa + ab))
        center_x = float(pa + (0.5 * ab))
        for pc in range(3, 25):
            if int(power) % int(pc) != 0:
                continue
            pd = int(power // pc)
            cd = int(pd - pc)
            if not (3 <= int(cd) <= 30):
                continue
            if int(pc) == int(pa) and int(cd) == int(ab):
                continue
            cos_theta = float(pc + pd) / float(2.0 * center_x)
            if 0.25 <= float(cos_theta) <= 0.86:
                candidates.append(
                    {
                        "PA": int(pa),
                        "AB": int(ab),
                        "PB": int(pa + ab),
                        "PC": int(pc),
                        "CD": int(cd),
                        "PD": int(pd),
                        "power": int(power),
                    }
                )
    return candidates


def _candidate_secant_secant_variable_values(
    target_answer: int,
    *,
    target_kind: str | None = None,
) -> List[Dict[str, int | str]]:
    if (
        target_kind is not None
        and str(target_kind) not in _SECANT_SECANT_VARIABLE_TARGET_KINDS
    ):
        raise ValueError(f"unsupported secant secant target kind: {target_kind}")
    candidates: List[Dict[str, int | str]] = []
    for pa in range(4, 31):
        for ab in range(8, 61):
            power = int(pa * (pa + ab))
            center_x = float(pa + (0.5 * ab))
            for pc in range(4, 31):
                if int(power) % int(pc) != 0:
                    continue
                pd = int(power // pc)
                cd = int(pd - pc)
                if not (8 <= int(cd) <= 60):
                    continue
                if int(pc) == int(pa) and int(cd) == int(ab):
                    continue
                cos_theta = float(pc + pd) / float(2.0 * center_x)
                if not (0.20 <= float(cos_theta) <= 0.88):
                    continue
                values = (int(pa), int(ab), int(pc), int(cd))
                if len(set(values)) != 4:
                    continue
                if int(ab) in {int(pa), int(2 * pa), int(3 * pa)}:
                    continue
                if int(cd) in {int(pc), int(2 * pc), int(3 * pc)}:
                    continue
                base_spec = {
                    "PA": int(pa),
                    "AB": int(ab),
                    "PB": int(pa + ab),
                    "PC": int(pc),
                    "CD": int(cd),
                    "PD": int(pd),
                    "power": int(power),
                }
                target_options = {
                    "outside_first": ("PA", int(pa)),
                    "inside_first": ("AB", int(ab)),
                    "outside_second": ("PC", int(pc)),
                    "inside_second": ("CD", int(cd)),
                }
                for option_kind, (
                    answer_segment,
                    answer_value,
                ) in target_options.items():
                    if target_kind is not None and str(option_kind) != str(target_kind):
                        continue
                    if int(answer_value) != int(target_answer):
                        continue
                    candidates.append(
                        {
                            **base_spec,
                            "target_kind": str(option_kind),
                            "canonical_answer_segment": str(answer_segment),
                            "answer": int(answer_value),
                        }
                    )
    return candidates


def _feasible_secant_secant_variable_target_kinds(
    target_answer: int,
) -> Tuple[str, ...]:
    kinds = sorted(
        {
            str(candidate["target_kind"])
            for candidate in _candidate_secant_secant_variable_values(
                int(target_answer)
            )
        }
    )
    return tuple(
        kind for kind in _SECANT_SECANT_VARIABLE_TARGET_KINDS if kind in set(kinds)
    )


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query")
    query_variant, query_variant_probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_QUERY_VARIANTS,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
    )
    query_variant = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(query_variant),
        variant_probabilities=query_variant_probabilities,
        supported_variants=SUPPORTED_QUERY_VARIANTS,
        balance_flag_key="balanced_query_variant_sampling",
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        sampling_namespace=f"{TASK_ID}.query_variant",
    )
    support_key = f"{query_variant}_answer_support"
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key="target_answer",
        fallback_support=_ANSWER_SUPPORT_BY_VARIANT[str(query_variant)],
        namespace=f"{TASK_ID}.{query_variant}.target_answer",
        balanced_flag_key="balanced_answer_sampling",
        namespace_support_permutation=True,
    )
    tangent_secant_target_kind: str | None = None
    tangent_secant_target_kind_probabilities: Dict[str, float] = {}
    secant_secant_variable_target_kind: str | None = None
    secant_secant_variable_target_kind_probabilities: Dict[str, float] = {}
    if str(query_variant) == "tangent_secant_length":
        feasible_target_kinds = _feasible_tangent_secant_target_kinds(
            int(target_answer)
        )
        if not feasible_target_kinds:
            raise ValueError(
                f"unsupported target answer for tangent secant theorem: {target_answer}"
            )
        explicit_target_kind = params.get("tangent_secant_target_kind")
        if explicit_target_kind is not None:
            if str(explicit_target_kind) not in feasible_target_kinds:
                raise ValueError(
                    f"unsupported tangent secant target kind {explicit_target_kind!r} for target answer {target_answer}"
                )
            tangent_secant_target_kind = str(explicit_target_kind)
        else:
            tangent_secant_target_kind = str(rng.choice(feasible_target_kinds))
        probability = 1.0 / float(len(feasible_target_kinds))
        tangent_secant_target_kind_probabilities = {
            str(kind): float(probability) for kind in feasible_target_kinds
        }
    if str(query_variant) == "secant_secant_variable_segment_length":
        feasible_target_kinds = _feasible_secant_secant_variable_target_kinds(
            int(target_answer)
        )
        if not feasible_target_kinds:
            raise ValueError(
                f"unsupported target answer for variable secant secant theorem: {target_answer}"
            )
        explicit_target_kind = params.get("secant_secant_variable_target_kind")
        if explicit_target_kind is not None:
            if str(explicit_target_kind) not in feasible_target_kinds:
                raise ValueError(
                    f"unsupported variable secant secant target kind {explicit_target_kind!r} "
                    f"for target answer {target_answer}"
                )
            secant_secant_variable_target_kind = str(explicit_target_kind)
        else:
            secant_secant_variable_target_kind = str(rng.choice(feasible_target_kinds))
        probability = 1.0 / float(len(feasible_target_kinds))
        secant_secant_variable_target_kind_probabilities = {
            str(kind): float(probability) for kind in feasible_target_kinds
        }
    return _ResolvedQuery(
        query_variant=str(query_variant),
        target_answer=int(target_answer),
        query_variant_probabilities=dict(query_variant_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
        tangent_secant_target_kind=tangent_secant_target_kind,
        tangent_secant_target_kind_probabilities=dict(
            tangent_secant_target_kind_probabilities
        ),
        secant_secant_variable_target_kind=secant_secant_variable_target_kind,
        secant_secant_variable_target_kind_probabilities=dict(
            secant_secant_variable_target_kind_probabilities
        ),
    )


def _model_transform(
    *,
    canvas_size: int,
    margin_px: float,
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
) -> Callable[[Point], Point]:
    width = max(1e-6, float(max_x) - float(min_x))
    height = max(1e-6, float(max_y) - float(min_y))
    usable = max(10.0, float(canvas_size) - (2.0 * float(margin_px)))
    scale = min(float(usable) / float(width), float(usable) / float(height))
    center_x = 0.5 * (float(min_x) + float(max_x))
    center_y = 0.5 * (float(min_y) + float(max_y))
    canvas_center = 0.5 * float(canvas_size)

    def transform(point: Point) -> Point:
        return (
            float(canvas_center + ((float(point[0]) - center_x) * scale)),
            float(canvas_center - ((float(point[1]) - center_y) * scale)),
        )

    transform.scale = float(scale)  # type: ignore[attr-defined]
    return transform


def _draw_centered_text_with_bbox(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Point,
    font,
    fill: Tuple[int, int, int],
    stroke_fill: Tuple[int, int, int],
    stroke_width: int,
) -> BBox:
    draw_text_centered(
        draw,
        text=str(text),
        center=(float(center[0]), float(center[1])),
        font=font,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=int(stroke_width),
    )
    return _text_bbox_for_center(
        draw,
        text=str(text),
        center=(float(center[0]), float(center[1])),
        font=font,
        stroke_width=int(stroke_width),
    )


def _segment_label_center(
    p0: Point, p1: Point, *, side: float, offset_px: float
) -> Point:
    x0, y0 = float(p0[0]), float(p0[1])
    x1, y1 = float(p1[0]), float(p1[1])
    dx, dy = x1 - x0, y1 - y0
    norm = max(1e-6, math.hypot(dx, dy))
    nx, ny = -dy / norm, dx / norm
    return (
        float(0.5 * (x0 + x1) + (float(side) * float(offset_px) * nx)),
        float(0.5 * (y0 + y1) + (float(side) * float(offset_px) * ny)),
    )


def _segment_label_direction(p0: Point, p1: Point, *, side: float) -> Point:
    x0, y0 = float(p0[0]), float(p0[1])
    x1, y1 = float(p1[0]), float(p1[1])
    dx, dy = x1 - x0, y1 - y0
    norm = max(1e-6, math.hypot(dx, dy))
    return (
        float(float(side) * (-dy / norm)),
        float(float(side) * (dx / norm)),
    )


def _circle_boundary_segments(
    center_px: Point, radius_px: float, *, steps: int = 72
) -> List[Tuple[Point, Point]]:
    cx, cy = float(center_px[0]), float(center_px[1])
    radius = float(max(1.0, radius_px))
    count = max(12, int(steps))
    points = [
        (
            float(cx + (radius * math.cos((2.0 * math.pi * index) / float(count)))),
            float(cy + (radius * math.sin((2.0 * math.pi * index) / float(count)))),
        )
        for index in range(count)
    ]
    return [(points[index], points[(index + 1) % count]) for index in range(count)]


def _draw_measurement_label(
    draw: ImageDraw.ImageDraw,
    *,
    token: str,
    p0: Point,
    p1: Point,
    side: float,
    offset_px: float,
    font,
    fill: Tuple[int, int, int],
    stroke_fill: Tuple[int, int, int],
    stroke_width: int,
    blocked_segments: Sequence[Tuple[Point, Point]],
    blocked_points: Sequence[Point],
    occupied_boxes: List[BBox],
    canvas_size: int,
) -> BBox:
    anchor = (
        float(0.5 * (float(p0[0]) + float(p1[0]))),
        float(0.5 * (float(p0[1]) + float(p1[1]))),
    )
    center, bbox = resolve_text_label_center(
        draw,
        text=str(token),
        anchor=anchor,
        base_direction=_segment_label_direction(p0, p1, side=float(side)),
        offset_px=max(36.0, float(offset_px)),
        font=font,
        blocked_segments=blocked_segments,
        blocked_points=blocked_points,
        occupied_boxes=occupied_boxes,
        stroke_width=int(stroke_width),
        line_clearance_px=10.0,
        point_clearance_px=8.0,
        canvas_size=int(canvas_size),
    )
    draw_text_centered(
        draw,
        text=str(token),
        center=center,
        font=font,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=int(stroke_width),
    )
    return tuple(float(value) for value in bbox)


def _screen_angle_path(
    start_angle: float, end_angle: float, *, steps: int
) -> List[Point]:
    start = float(start_angle)
    delta = ((float(end_angle) - start + math.pi) % (2.0 * math.pi)) - math.pi
    count = max(2, int(steps))
    return [
        (
            math.cos(start + (delta * (index / float(count - 1)))),
            math.sin(start + (delta * (index / float(count - 1)))),
        )
        for index in range(count)
    ]


def _draw_angle_annotation(
    draw: ImageDraw.ImageDraw,
    *,
    token: str | None,
    vertex_px: Point,
    arm0_px: Point,
    arm1_px: Point,
    radius_px: float,
    font,
    fill: Tuple[int, int, int],
    stroke_fill: Tuple[int, int, int],
    stroke_width: int,
    line_fill: Tuple[int, int, int],
    line_width: int,
    blocked_segments: Sequence[Tuple[Point, Point]],
    blocked_points: Sequence[Point],
    occupied_boxes: List[BBox],
    canvas_size: int,
) -> BBox | None:
    vx, vy = float(vertex_px[0]), float(vertex_px[1])
    vectors: List[Point] = []
    for point in (arm0_px, arm1_px):
        dx, dy = float(point[0]) - vx, float(point[1]) - vy
        norm = max(1e-6, math.hypot(dx, dy))
        vectors.append((dx / norm, dy / norm))
    angle0 = math.atan2(vectors[0][1], vectors[0][0])
    angle1 = math.atan2(vectors[1][1], vectors[1][0])
    unit_path = _screen_angle_path(angle0, angle1, steps=16)
    path = [
        (vx + (float(radius_px) * ux), vy + (float(radius_px) * uy))
        for ux, uy in unit_path
    ]
    if len(path) >= 2:
        draw.line(path, fill=line_fill, width=max(1, int(line_width)))
    if token is None:
        return None
    midpoint = unit_path[len(unit_path) // 2]
    center, bbox = resolve_text_label_center(
        draw,
        text=str(token),
        anchor=(vx, vy),
        base_direction=(float(midpoint[0]), float(midpoint[1])),
        offset_px=float(radius_px) + 42.0,
        font=font,
        blocked_segments=blocked_segments,
        blocked_points=blocked_points,
        occupied_boxes=occupied_boxes,
        stroke_width=int(stroke_width),
        line_clearance_px=10.0,
        point_clearance_px=8.0,
        canvas_size=int(canvas_size),
    )
    draw_text_centered(
        draw,
        text=str(token),
        center=center,
        font=font,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=int(stroke_width),
    )
    return tuple(float(value) for value in bbox)


def _draw_circle_arc_annotation(
    draw: ImageDraw.ImageDraw,
    *,
    token: str | None,
    center_px: Point,
    radius_px: float,
    start_px: Point,
    end_px: Point,
    font,
    fill: Tuple[int, int, int],
    stroke_fill: Tuple[int, int, int],
    stroke_width: int,
    line_fill: Tuple[int, int, int],
    line_width: int,
    blocked_segments: Sequence[Tuple[Point, Point]],
    blocked_points: Sequence[Point],
    occupied_boxes: List[BBox],
    canvas_size: int,
) -> BBox | None:
    cx, cy = float(center_px[0]), float(center_px[1])
    angle0 = math.atan2(float(start_px[1]) - cy, float(start_px[0]) - cx)
    angle1 = math.atan2(float(end_px[1]) - cy, float(end_px[0]) - cx)
    unit_path = _screen_angle_path(angle0, angle1, steps=28)
    arc_radius = float(radius_px) * 1.012
    path = [(cx + (arc_radius * ux), cy + (arc_radius * uy)) for ux, uy in unit_path]
    if len(path) >= 2:
        draw.line(path, fill=line_fill, width=max(1, int(line_width)))
    if token is None:
        return None
    midpoint = unit_path[len(unit_path) // 2]
    anchor = (
        float(cx + (float(radius_px) * midpoint[0])),
        float(cy + (float(radius_px) * midpoint[1])),
    )
    center, bbox = resolve_text_label_center(
        draw,
        text=str(token),
        anchor=anchor,
        base_direction=(float(midpoint[0]), float(midpoint[1])),
        offset_px=52.0,
        font=font,
        blocked_segments=blocked_segments,
        blocked_points=blocked_points,
        occupied_boxes=occupied_boxes,
        stroke_width=int(stroke_width),
        line_clearance_px=12.0,
        point_clearance_px=8.0,
        canvas_size=int(canvas_size),
    )
    draw_text_centered(
        draw,
        text=str(token),
        center=center,
        font=font,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=int(stroke_width),
    )
    return tuple(float(value) for value in bbox)


def _draw_point_label(
    draw: ImageDraw.ImageDraw,
    *,
    label: str,
    point_px: Point,
    base_direction: Point,
    font,
    fill: Tuple[int, int, int],
    stroke_fill: Tuple[int, int, int],
    stroke_width: int,
    point_label_offset_px: float,
    blocked_segments: Sequence[Tuple[Point, Point]],
    blocked_points: Sequence[Point],
    occupied_boxes: List[BBox],
    canvas_size: int,
) -> BBox:
    center, bbox = resolve_text_label_center(
        draw,
        text=str(label),
        anchor=(float(point_px[0]), float(point_px[1])),
        base_direction=(float(base_direction[0]), float(base_direction[1])),
        offset_px=float(point_label_offset_px),
        font=font,
        blocked_segments=blocked_segments,
        blocked_points=blocked_points,
        occupied_boxes=occupied_boxes,
        stroke_width=int(stroke_width),
        line_clearance_px=8.0,
        point_clearance_px=8.0,
        canvas_size=int(canvas_size),
    )
    draw_text_centered(
        draw,
        text=str(label),
        center=center,
        font=font,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=int(stroke_width),
    )
    occupied_boxes.append(tuple(float(value) for value in bbox))
    return tuple(float(value) for value in bbox)


def _render_base_scene(
    *,
    rng,
    instance_seed: int,
    params: Mapping[str, Any],
    point_model: Mapping[str, Point],
    circle_center: Point,
    circle_radius: float,
    segments: Mapping[str, Tuple[str, str]],
    measurement_specs: Sequence[Tuple[str, str, float]],
    evidence_tokens: Sequence[str],
    annotation_values: Mapping[str, int],
    theorem_trace: Mapping[str, Any],
    angle_marker_specs: Sequence[Mapping[str, Any]] | None = None,
    circle_arc_specs: Sequence[Mapping[str, Any]] | None = None,
) -> _RenderedScene:
    canvas_min = int(
        group_default(_RENDER_DEFAULTS, "canvas_size_min", _DEFAULTS.canvas_size_min)
    )
    canvas_max = int(
        group_default(_RENDER_DEFAULTS, "canvas_size_max", _DEFAULTS.canvas_size_max)
    )
    explicit_canvas_size = params.get("canvas_size")
    if explicit_canvas_size is not None:
        canvas_size = max(256, int(explicit_canvas_size))
    else:
        canvas_size = int(
            rng.randint(min(canvas_min, canvas_max), max(canvas_min, canvas_max))
        )
    margin_px = float(
        params.get(
            "outer_margin_px",
            group_default(
                _RENDER_DEFAULTS, "outer_margin_px", _DEFAULTS.outer_margin_px
            ),
        )
    )
    line_width = int(
        sample_int_render_param(
            rng,
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            key="line_width",
            fallback=_DEFAULTS.line_width,
            minimum_value=1,
        )
    )
    circle_line_width = int(
        params.get(
            "circle_line_width",
            group_default(
                _RENDER_DEFAULTS,
                "circle_line_width",
                max(line_width, _DEFAULTS.circle_line_width),
            ),
        )
    )
    point_radius_px = int(
        params.get(
            "point_radius_px",
            group_default(
                _RENDER_DEFAULTS, "point_radius_px", _DEFAULTS.point_radius_px
            ),
        )
    )
    measurement_offset_px = float(
        params.get(
            "measurement_label_offset_px",
            group_default(
                _RENDER_DEFAULTS,
                "measurement_label_offset_px",
                _DEFAULTS.measurement_label_offset_px,
            ),
        )
    )
    point_label_offset_px = float(
        params.get(
            "point_label_offset_px",
            group_default(
                _RENDER_DEFAULTS,
                "point_label_offset_px",
                _DEFAULTS.point_label_offset_px,
            ),
        )
    )
    label_font_size_px = int(
        rng.randint(
            int(
                group_default(
                    _RENDER_DEFAULTS,
                    "label_font_size_min",
                    _DEFAULTS.label_font_size_min,
                )
            ),
            int(
                group_default(
                    _RENDER_DEFAULTS,
                    "label_font_size_max",
                    _DEFAULTS.label_font_size_max,
                )
            ),
        )
    )
    measurement_font_size_px = int(
        rng.randint(
            int(
                group_default(
                    _RENDER_DEFAULTS,
                    "measurement_font_size_min",
                    _DEFAULTS.measurement_font_size_min,
                )
            ),
            int(
                group_default(
                    _RENDER_DEFAULTS,
                    "measurement_font_size_max",
                    _DEFAULTS.measurement_font_size_max,
                )
            ),
        )
    )

    min_x = float(circle_center[0] - circle_radius)
    max_x = float(circle_center[0] + circle_radius)
    min_y = float(circle_center[1] - circle_radius)
    max_y = float(circle_center[1] + circle_radius)
    for point in point_model.values():
        min_x = min(min_x, float(point[0]))
        max_x = max(max_x, float(point[0]))
        min_y = min(min_y, float(point[1]))
        max_y = max(max_y, float(point[1]))
    pad = max(2.0, 0.12 * max(float(max_x - min_x), float(max_y - min_y)))
    transform = _model_transform(
        canvas_size=int(canvas_size),
        margin_px=float(margin_px),
        min_x=float(min_x - pad),
        min_y=float(min_y - pad),
        max_x=float(max_x + pad),
        max_y=float(max_y + pad),
    )
    point_pixels = {
        label: list(transform(point)) for label, point in point_model.items()
    }
    center_px = transform(circle_center)
    radius_px = float(circle_radius) * float(getattr(transform, "scale"))

    image, background_meta = make_background_canvas(
        canvas_size=int(canvas_size),
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=_BACKGROUND_DEFAULTS,
        fallback_color=(252, 252, 252),
    )
    draw = ImageDraw.Draw(image)
    shape_style = sample_geometry_shape_style(
        rng,
        params=params,
        render_defaults=_RENDER_DEFAULTS,
        anchor_colors=extract_background_anchor_colors(background_meta),
    )
    line_color = tuple(int(value) for value in shape_style.line_color)
    label_color = tuple(int(value) for value in shape_style.label_color)
    stroke_color = tuple(int(value) for value in shape_style.label_stroke_color)
    label_font = load_font(label_font_size_px, bold=True)
    measurement_font = load_font(measurement_font_size_px, bold=True)
    label_stroke_width = max(1, int(round(label_font_size_px * 0.08)))
    measurement_stroke_width = max(1, int(round(measurement_font_size_px * 0.08)))

    circle_bbox = (
        float(center_px[0] - radius_px),
        float(center_px[1] - radius_px),
        float(center_px[0] + radius_px),
        float(center_px[1] + radius_px),
    )
    draw.ellipse(circle_bbox, outline=line_color, width=max(1, int(circle_line_width)))

    segment_pixels: Dict[str, List[List[float]]] = {}
    blocked_segments: List[Tuple[Point, Point]] = []
    for segment_id, (label0, label1) in segments.items():
        p0 = tuple(float(value) for value in point_pixels[str(label0)])
        p1 = tuple(float(value) for value in point_pixels[str(label1)])
        segment_pixels[str(segment_id)] = [list(p0), list(p1)]
        blocked_segments.append((p0, p1))
        draw.line((p0, p1), fill=line_color, width=max(1, int(line_width)))
    circle_blocked_segments = _circle_boundary_segments(center_px, float(radius_px))
    label_blocked_segments: List[Tuple[Point, Point]] = list(blocked_segments) + list(
        circle_blocked_segments
    )

    for point in point_pixels.values():
        px, py = float(point[0]), float(point[1])
        r = max(2, int(point_radius_px))
        draw.ellipse((px - r, py - r, px + r, py + r), fill=line_color)
    blocked_points = [
        tuple(float(value) for value in point) for point in point_pixels.values()
    ]

    occupied_boxes: List[BBox] = []
    token_bboxes: Dict[str, List[float]] = {}
    evidence_bboxes: List[List[float]] = []
    for token, segment_id, side in measurement_specs:
        point_pair = segment_pixels[str(segment_id)]
        bbox = _draw_measurement_label(
            draw,
            token=str(token),
            p0=tuple(point_pair[0]),
            p1=tuple(point_pair[1]),
            side=float(side),
            offset_px=float(measurement_offset_px),
            font=measurement_font,
            fill=label_color,
            stroke_fill=stroke_color,
            stroke_width=int(measurement_stroke_width),
            blocked_segments=label_blocked_segments,
            blocked_points=blocked_points,
            occupied_boxes=occupied_boxes,
            canvas_size=int(canvas_size),
        )
        bbox_list = _bbox_to_list(bbox)
        token_bboxes[str(token)] = list(bbox_list)
        occupied_boxes.append(tuple(float(value) for value in bbox))
        if str(token) in set(str(item) for item in evidence_tokens):
            evidence_bboxes.append(list(bbox_list))

    evidence_token_set = set(str(item) for item in evidence_tokens)
    for spec in angle_marker_specs or ():
        vertex = str(spec["vertex"])
        arm0 = str(spec["arm0"])
        arm1 = str(spec["arm1"])
        token_value = spec.get("token")
        bbox = _draw_angle_annotation(
            draw,
            token=None if token_value is None else str(token_value),
            vertex_px=tuple(float(value) for value in point_pixels[vertex]),
            arm0_px=tuple(float(value) for value in point_pixels[arm0]),
            arm1_px=tuple(float(value) for value in point_pixels[arm1]),
            radius_px=float(spec.get("radius_px", 42.0)),
            font=measurement_font,
            fill=label_color,
            stroke_fill=stroke_color,
            stroke_width=int(measurement_stroke_width),
            line_fill=line_color,
            line_width=max(1, int(line_width) - 1),
            blocked_segments=label_blocked_segments,
            blocked_points=blocked_points,
            occupied_boxes=occupied_boxes,
            canvas_size=int(canvas_size),
        )
        if bbox is not None and token_value is not None:
            bbox_list = _bbox_to_list(bbox)
            token_bboxes[str(token_value)] = list(bbox_list)
            occupied_boxes.append(tuple(float(value) for value in bbox))
            if str(token_value) in evidence_token_set:
                evidence_bboxes.append(list(bbox_list))

    for spec in circle_arc_specs or ():
        start_label = str(spec["start"])
        end_label = str(spec["end"])
        token_value = spec.get("token")
        bbox = _draw_circle_arc_annotation(
            draw,
            token=None if token_value is None else str(token_value),
            center_px=center_px,
            radius_px=float(radius_px),
            start_px=tuple(float(value) for value in point_pixels[start_label]),
            end_px=tuple(float(value) for value in point_pixels[end_label]),
            font=measurement_font,
            fill=label_color,
            stroke_fill=stroke_color,
            stroke_width=int(measurement_stroke_width),
            line_fill=line_color,
            line_width=max(2, int(line_width)),
            blocked_segments=label_blocked_segments,
            blocked_points=blocked_points,
            occupied_boxes=occupied_boxes,
            canvas_size=int(canvas_size),
        )
        if bbox is not None and token_value is not None:
            bbox_list = _bbox_to_list(bbox)
            token_bboxes[str(token_value)] = list(bbox_list)
            occupied_boxes.append(tuple(float(value) for value in bbox))
            if str(token_value) in evidence_token_set:
                evidence_bboxes.append(list(bbox_list))

    point_label_bboxes: Dict[str, List[float]] = {}
    for label, point_px_list in point_pixels.items():
        px, py = float(point_px_list[0]), float(point_px_list[1])
        base_direction = (float(px - center_px[0]), float(py - center_px[1]))
        point_label_bbox = _draw_point_label(
            draw,
            label=str(label),
            point_px=(float(px), float(py)),
            base_direction=base_direction,
            font=label_font,
            fill=label_color,
            stroke_fill=stroke_color,
            stroke_width=int(label_stroke_width),
            point_label_offset_px=float(point_label_offset_px),
            blocked_segments=label_blocked_segments,
            blocked_points=blocked_points,
            occupied_boxes=occupied_boxes,
            canvas_size=int(canvas_size),
        )
        point_label_bboxes[str(label)] = _bbox_to_list(point_label_bbox)

    image, post_noise_meta = apply_post_image_noise(
        image,
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=_POST_IMAGE_NOISE_DEFAULTS,
    )
    scene_entities = [
        {
            "entity_id": "circle_O",
            "type": "circle",
            "center_model": [float(circle_center[0]), float(circle_center[1])],
            "radius_model": float(circle_radius),
            "center_pixel": [
                float(round(center_px[0], 2)),
                float(round(center_px[1], 2)),
            ],
            "radius_px": float(round(radius_px, 2)),
        }
    ]
    scene_entities.extend(
        {
            "entity_id": f"point_{label}",
            "type": "point",
            "label": str(label),
            "model_point": [
                float(point_model[str(label)][0]),
                float(point_model[str(label)][1]),
            ],
            "pixel_point": [
                float(round(point_pixels[str(label)][0], 2)),
                float(round(point_pixels[str(label)][1], 2)),
            ],
        }
        for label in sorted(point_model)
    )
    scene_entities.extend(
        {
            "entity_id": f"segment_{segment_id}",
            "type": "segment",
            "labels": [str(labels[0]), str(labels[1])],
            "pixel_endpoints": [
                list(point) for point in segment_pixels[str(segment_id)]
            ],
        }
        for segment_id, labels in sorted(segments.items())
    )
    scene_entities.extend(
        {
            "entity_id": f"annotation_{index}",
            "type": "measurement_annotation",
            "token": str(token),
            "bbox": list(token_bboxes[str(token)]),
        }
        for index, token in enumerate(token_bboxes)
    )

    return _RenderedScene(
        image=image,
        answer_value=int(theorem_trace["answer_value"]),
        evidence_tokens=[str(token) for token in evidence_tokens],
        evidence_bboxes=[list(bbox) for bbox in evidence_bboxes],
        token_bboxes={str(key): list(value) for key, value in token_bboxes.items()},
        point_pixels={
            str(key): [float(round(value[0], 2)), float(round(value[1], 2))]
            for key, value in point_pixels.items()
        },
        point_label_bboxes={
            str(key): list(value) for key, value in point_label_bboxes.items()
        },
        point_model={
            str(key): [float(value[0]), float(value[1])]
            for key, value in point_model.items()
        },
        segment_pixels={
            str(key): [
                [float(round(point[0], 2)), float(round(point[1], 2))]
                for point in value
            ]
            for key, value in segment_pixels.items()
        },
        circle_center_pixel=[
            float(round(center_px[0], 2)),
            float(round(center_px[1], 2)),
        ],
        circle_center_model=[float(circle_center[0]), float(circle_center[1])],
        circle_radius_model=float(circle_radius),
        circle_radius_px=float(round(radius_px, 2)),
        annotation_values={
            str(key): int(value) for key, value in annotation_values.items()
        },
        theorem_trace=dict(theorem_trace),
        scene_entities=list(scene_entities),
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        shape_style=dict(shape_style.to_trace_dict()),
        render_params={
            "canvas_size": int(canvas_size),
            "line_width": int(line_width),
            "circle_line_width": int(circle_line_width),
            "point_radius_px": int(point_radius_px),
            "label_font_size_px": int(label_font_size_px),
            "measurement_font_size_px": int(measurement_font_size_px),
            "measurement_label_offset_px": float(measurement_offset_px),
            "point_label_offset_px": float(point_label_offset_px),
        },
    )


def _build_diameter_perpendicular_chord_scene(
    rng, *, query: _ResolvedQuery
) -> Dict[str, Any]:
    candidates = _candidate_diameter_chord_values(int(query.target_answer))
    if not candidates:
        raise ValueError(
            f"unsupported target answer for diameter chord theorem: {query.target_answer}"
        )
    spec = dict(candidates[int(rng.randrange(len(candidates)))])
    label_map = _sample_point_label_map(rng, ("O", "B", "D", "E", "A", "C"))
    radius = float(spec["radius"])
    offset = float(spec["offset"])
    half_chord = float(spec["half_chord"])
    canonical_point_model = {
        "O": (0.0, 0.0),
        "B": (0.0, -radius),
        "D": (0.0, radius),
        "E": (0.0, -offset),
        "A": (-half_chord, -offset),
        "C": (half_chord, -offset),
    }
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    diameter_segment = _visible_segment(label_map, "D", "B")
    chord_segment = _visible_segment(label_map, "A", "C")
    answer_segment = _visible_segment(label_map, "B", "E")
    angle_token = f"{_visible_angle(label_map, 'D', 'E', 'C')}=90"
    diameter_token = f"{diameter_segment}={int(spec['diameter'])}"
    chord_token = f"{chord_segment}={int(spec['chord'])}"
    theorem_trace = {
        "theorem": "diameter_perpendicular_chord",
        "label_map": dict(label_map),
        "radius": int(spec["radius"]),
        "center_to_chord_distance": int(spec["offset"]),
        "half_chord_length": int(spec["half_chord"]),
        "diameter_length": int(spec["diameter"]),
        "chord_length": int(spec["chord"]),
        "canonical_answer_segment": "BE",
        "answer_segment": str(answer_segment),
        "answer_value": int(spec["answer"]),
        "distractor_tokens": [str(angle_token)],
    }
    return {
        "point_model": point_model,
        "circle_center": (0.0, 0.0),
        "circle_radius": radius,
        "segments": {
            "DB": (label_map["D"], label_map["B"]),
            "AC": (label_map["A"], label_map["C"]),
            "BE": (label_map["B"], label_map["E"]),
            "DE": (label_map["D"], label_map["E"]),
        },
        "measurement_specs": (
            (diameter_token, "DB", -1.0),
            (chord_token, "AC", -1.0),
            (f"{answer_segment}=?", "BE", 1.0),
        ),
        "angle_marker_specs": (
            {
                "token": angle_token,
                "vertex": label_map["E"],
                "arm0": label_map["D"],
                "arm1": label_map["C"],
                "radius_px": 34.0,
            },
        ),
        "evidence_tokens": (diameter_token, chord_token),
        "annotation_values": {
            str(diameter_segment): int(spec["diameter"]),
            str(chord_segment): int(spec["chord"]),
            str(answer_segment): int(spec["answer"]),
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "diameter_segment": str(diameter_segment),
            "chord_segment": str(chord_segment),
            "intersection_label": str(label_map["E"]),
            "answer_segment": str(answer_segment),
        },
    }


def _build_tangent_secant_scene(rng, *, query: _ResolvedQuery) -> Dict[str, Any]:
    candidates = _candidate_tangent_secant_values(
        int(query.target_answer),
        target_kind=query.tangent_secant_target_kind,
    )
    if not candidates:
        raise ValueError(
            f"unsupported target answer for tangent secant theorem: {query.target_answer}"
        )
    spec = dict(candidates[int(rng.randrange(len(candidates)))])
    label_map = _sample_point_label_map(rng, ("P", "A", "B", "T", "O"))
    outside = float(spec["PA"])
    internal = float(spec["AB"])
    tangent = float(spec["PT"])
    target_kind = str(spec["target_kind"])
    radius = internal / 2.0
    center_x = outside + radius
    center = (center_x, 0.0)
    tangent_x = ((center_x * center_x) - (radius * radius)) / center_x
    tangent_y = (radius * tangent) / center_x
    if abs(math.hypot(tangent_x - center_x, tangent_y) - radius) > 1e-7:
        raise ValueError("sampled tangent point is not on the circle")
    if abs((tangent_x * (tangent_x - center_x)) + (tangent_y * tangent_y)) > 1e-7:
        raise ValueError("sampled tangent point is not perpendicular to the radius")
    canonical_point_model = {
        "P": (0.0, 0.0),
        "A": (outside, 0.0),
        "B": (outside + internal, 0.0),
        "T": (float(tangent_x), float(tangent_y)),
        "O": center,
    }
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    tangent_segment = _visible_segment(label_map, "P", "T")
    outside_segment = _visible_segment(label_map, "P", "A")
    inside_segment = _visible_segment(label_map, "A", "B")
    full_secant_segment = _visible_segment(label_map, "P", "B")
    answer_segment_by_kind = {
        "outside": outside_segment,
        "inside": inside_segment,
        "tangent": tangent_segment,
    }
    answer_segment = str(answer_segment_by_kind[str(target_kind)])
    canonical_answer_segment = str(spec["canonical_answer_segment"])
    known_token_by_segment = {
        "PT": f"{tangent_segment}={int(tangent)}",
        "PA": f"{outside_segment}={int(outside)}",
        "AB": f"{inside_segment}={int(internal)}",
    }
    known_segment_ids_by_kind = {
        "outside": ("PT", "AB"),
        "inside": ("PT", "PA"),
        "tangent": ("PA", "AB"),
    }
    known_segment_ids = known_segment_ids_by_kind[str(target_kind)]
    tokens = tuple(
        str(known_token_by_segment[str(segment_id)]) for segment_id in known_segment_ids
    )
    measurement_specs_by_kind = {
        "outside": (
            (known_token_by_segment["PT"], "PT", -1.0),
            (f"{outside_segment}=?", "PA", 1.0),
            (known_token_by_segment["AB"], "AB", 1.0),
        ),
        "inside": (
            (known_token_by_segment["PT"], "PT", -1.0),
            (known_token_by_segment["PA"], "PA", 1.0),
            (f"{inside_segment}=?", "AB", 1.0),
        ),
        "tangent": (
            (f"{tangent_segment}=?", "PT", -1.0),
            (known_token_by_segment["PA"], "PA", 1.0),
            (known_token_by_segment["AB"], "AB", 1.0),
        ),
    }
    distractor_angle = _visible_angle(label_map, "T", "P", "A")
    distractor_angle_value = _angle_degrees_at(
        canonical_point_model["P"],
        canonical_point_model["T"],
        canonical_point_model["A"],
    )
    distractor_token = f"{distractor_angle}={int(distractor_angle_value)}"
    theorem_trace = {
        "theorem": "tangent_secant",
        "label_map": dict(label_map),
        "target_kind": str(target_kind),
        "PT": int(tangent),
        "PA": int(outside),
        "AB": int(internal),
        "PB": int(outside + internal),
        "canonical_answer_segment": str(canonical_answer_segment),
        "answer_segment": str(answer_segment),
        "answer_value": int(spec["answer"]),
        "power_PT_squared": int(tangent * tangent),
        "power_PA_times_PB": int(outside * (outside + internal)),
        "distractor_tokens": [str(distractor_token)],
    }
    return {
        "point_model": point_model,
        "circle_center": center,
        "circle_radius": float(radius),
        "segments": {
            "PT": (label_map["P"], label_map["T"]),
            "PAB": (label_map["P"], label_map["B"]),
            "PA": (label_map["P"], label_map["A"]),
            "AB": (label_map["A"], label_map["B"]),
            "OB": (label_map["O"], label_map["B"]),
        },
        "measurement_specs": measurement_specs_by_kind[str(target_kind)],
        "angle_marker_specs": (
            {
                "token": distractor_token,
                "vertex": label_map["P"],
                "arm0": label_map["T"],
                "arm1": label_map["A"],
                "radius_px": 36.0,
            },
        ),
        "evidence_tokens": tokens,
        "annotation_values": {
            str(tangent_segment): int(tangent),
            str(outside_segment): int(outside),
            str(inside_segment): int(internal),
            str(full_secant_segment): int(outside + internal),
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "external_point": str(label_map["P"]),
            "tangent_point": str(label_map["T"]),
            "near_point": str(label_map["A"]),
            "far_point": str(label_map["B"]),
            "tangent_segment": str(tangent_segment),
            "inside_segment": str(inside_segment),
            "answer_segment": str(answer_segment),
        },
    }


def _build_secant_secant_scene(rng, *, query: _ResolvedQuery) -> Dict[str, Any]:
    candidates = _candidate_secant_secant_values(int(query.target_answer))
    if not candidates:
        raise ValueError(
            f"unsupported target answer for secant secant theorem: {query.target_answer}"
        )
    spec = dict(candidates[int(rng.randrange(len(candidates)))])
    label_map = _sample_point_label_map(rng, ("P", "A", "B", "C", "D", "O"))
    pa = float(spec["PA"])
    ab = float(spec["AB"])
    pc = float(spec["PC"])
    cd = float(spec["CD"])
    pd = float(spec["PD"])
    radius = ab / 2.0
    center_x = pa + radius
    center = (center_x, 0.0)
    cos_theta = float(pc + pd) / float(2.0 * center_x)
    sin_theta = math.sqrt(max(0.0, 1.0 - (cos_theta * cos_theta)))
    u2 = (float(cos_theta), float(sin_theta))
    canonical_point_model = {
        "P": (0.0, 0.0),
        "A": (pa, 0.0),
        "B": (pa + ab, 0.0),
        "C": (pc * u2[0], pc * u2[1]),
        "D": (pd * u2[0], pd * u2[1]),
        "O": center,
    }
    for label in ("A", "B", "C", "D"):
        distance = math.hypot(
            canonical_point_model[label][0] - center[0],
            canonical_point_model[label][1] - center[1],
        )
        if abs(float(distance) - float(radius)) > 1e-6:
            raise ValueError("sampled secant point is not on the circle")
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    outside_segment = _visible_segment(label_map, "P", "A")
    inside_segment = _visible_segment(label_map, "A", "B")
    full_first_secant = _visible_segment(label_map, "P", "B")
    outside_second_segment = _visible_segment(label_map, "P", "C")
    inside_second_segment = _visible_segment(label_map, "C", "D")
    full_second_secant = _visible_segment(label_map, "P", "D")
    distractor_angle = _visible_angle(label_map, "A", "P", "C")
    distractor_angle_value = _angle_degrees_at(
        canonical_point_model["P"],
        canonical_point_model["A"],
        canonical_point_model["C"],
    )
    tokens = (
        f"{inside_segment}={int(ab)}",
        f"{outside_second_segment}={int(pc)}",
        f"{inside_second_segment}={int(cd)}",
    )
    distractor_token = f"{distractor_angle}={int(distractor_angle_value)}"
    theorem_trace = {
        "theorem": "secant_secant",
        "label_map": dict(label_map),
        "PA": int(pa),
        "AB": int(ab),
        "PB": int(pa + ab),
        "PC": int(pc),
        "CD": int(cd),
        "PD": int(pd),
        "canonical_answer_segment": "PA",
        "answer_segment": str(outside_segment),
        "answer_value": int(pa),
        "power_PA_times_PB": int(pa * (pa + ab)),
        "power_PC_times_PD": int(pc * pd),
        "distractor_tokens": [str(distractor_token)],
    }
    return {
        "point_model": point_model,
        "circle_center": center,
        "circle_radius": float(radius),
        "segments": {
            "PAB": (label_map["P"], label_map["B"]),
            "PCD": (label_map["P"], label_map["D"]),
            "PA": (label_map["P"], label_map["A"]),
            "AB": (label_map["A"], label_map["B"]),
            "PC": (label_map["P"], label_map["C"]),
            "CD": (label_map["C"], label_map["D"]),
        },
        "measurement_specs": (
            (f"{outside_segment}=?", "PA", 1.0),
            (tokens[0], "AB", 1.0),
            (tokens[1], "PC", -1.0),
            (tokens[2], "CD", 1.0),
        ),
        "angle_marker_specs": (
            {
                "token": distractor_token,
                "vertex": label_map["P"],
                "arm0": label_map["A"],
                "arm1": label_map["C"],
                "radius_px": 38.0,
            },
        ),
        "evidence_tokens": tokens,
        "annotation_values": {
            str(outside_segment): int(pa),
            str(inside_segment): int(ab),
            str(full_first_secant): int(pa + ab),
            str(outside_second_segment): int(pc),
            str(inside_second_segment): int(cd),
            str(full_second_secant): int(pd),
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "external_point": str(label_map["P"]),
            "near_point": str(label_map["A"]),
            "far_point": str(label_map["B"]),
            "near_point_alt": str(label_map["C"]),
            "far_point_alt": str(label_map["D"]),
            "inside_segment": str(inside_segment),
            "outside_second_segment": str(outside_second_segment),
            "inside_second_segment": str(inside_second_segment),
            "answer_segment": str(outside_segment),
        },
    }


def _build_secant_secant_variable_scene(
    rng, *, query: _ResolvedQuery
) -> Dict[str, Any]:
    candidates = _candidate_secant_secant_variable_values(
        int(query.target_answer),
        target_kind=query.secant_secant_variable_target_kind,
    )
    if not candidates:
        raise ValueError(
            f"unsupported target answer for variable secant secant theorem: {query.target_answer}"
        )
    spec = dict(candidates[int(rng.randrange(len(candidates)))])
    label_map = _sample_point_label_map(rng, ("P", "A", "B", "C", "D", "O"))
    pa = float(spec["PA"])
    ab = float(spec["AB"])
    pc = float(spec["PC"])
    cd = float(spec["CD"])
    pd = float(spec["PD"])
    target_kind = str(spec["target_kind"])
    canonical_answer_segment = str(spec["canonical_answer_segment"])
    radius = ab / 2.0
    center_x = pa + radius
    center = (center_x, 0.0)
    cos_theta = float(pc + pd) / float(2.0 * center_x)
    sin_theta = math.sqrt(max(0.0, 1.0 - (cos_theta * cos_theta)))
    u2 = (float(cos_theta), float(sin_theta))
    canonical_point_model = {
        "P": (0.0, 0.0),
        "A": (pa, 0.0),
        "B": (pa + ab, 0.0),
        "C": (pc * u2[0], pc * u2[1]),
        "D": (pd * u2[0], pd * u2[1]),
        "O": center,
    }
    for label in ("A", "B", "C", "D"):
        distance = math.hypot(
            canonical_point_model[label][0] - center[0],
            canonical_point_model[label][1] - center[1],
        )
        if abs(float(distance) - float(radius)) > 1e-6:
            raise ValueError("sampled secant point is not on the circle")
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    visible_by_canonical = {
        "PA": _visible_segment(label_map, "P", "A"),
        "AB": _visible_segment(label_map, "A", "B"),
        "PB": _visible_segment(label_map, "P", "B"),
        "PC": _visible_segment(label_map, "P", "C"),
        "CD": _visible_segment(label_map, "C", "D"),
        "PD": _visible_segment(label_map, "P", "D"),
    }
    value_by_canonical = {
        "PA": int(pa),
        "AB": int(ab),
        "PB": int(pa + ab),
        "PC": int(pc),
        "CD": int(cd),
        "PD": int(pd),
    }
    token_by_canonical = {
        canonical: f"{visible_by_canonical[canonical]}={value_by_canonical[canonical]}"
        for canonical in ("PA", "AB", "PC", "CD")
    }
    measurement_token_by_canonical = dict(token_by_canonical)
    measurement_token_by_canonical[str(canonical_answer_segment)] = (
        f"{visible_by_canonical[str(canonical_answer_segment)]}=?"
    )
    tokens = tuple(
        str(token_by_canonical[canonical])
        for canonical in ("PA", "AB", "PC", "CD")
        if str(canonical) != str(canonical_answer_segment)
    )
    distractor_angle = _visible_angle(label_map, "A", "P", "C")
    distractor_angle_value = _angle_degrees_at(
        canonical_point_model["P"],
        canonical_point_model["A"],
        canonical_point_model["C"],
    )
    distractor_token = f"{distractor_angle}={int(distractor_angle_value)}"
    theorem_trace = {
        "theorem": "secant_secant_variable",
        "label_map": dict(label_map),
        "target_kind": str(target_kind),
        "PA": int(pa),
        "AB": int(ab),
        "PB": int(pa + ab),
        "PC": int(pc),
        "CD": int(cd),
        "PD": int(pd),
        "canonical_answer_segment": str(canonical_answer_segment),
        "answer_segment": str(visible_by_canonical[str(canonical_answer_segment)]),
        "answer_value": int(spec["answer"]),
        "power_PA_times_PB": int(pa * (pa + ab)),
        "power_PC_times_PD": int(pc * pd),
        "distractor_tokens": [str(distractor_token)],
    }
    return {
        "point_model": point_model,
        "circle_center": center,
        "circle_radius": float(radius),
        "segments": {
            "PAB": (label_map["P"], label_map["B"]),
            "PCD": (label_map["P"], label_map["D"]),
            "PA": (label_map["P"], label_map["A"]),
            "AB": (label_map["A"], label_map["B"]),
            "PC": (label_map["P"], label_map["C"]),
            "CD": (label_map["C"], label_map["D"]),
        },
        "measurement_specs": (
            (measurement_token_by_canonical["PA"], "PA", 1.0),
            (measurement_token_by_canonical["AB"], "AB", 1.0),
            (measurement_token_by_canonical["PC"], "PC", -1.0),
            (measurement_token_by_canonical["CD"], "CD", 1.0),
        ),
        "angle_marker_specs": (
            {
                "token": distractor_token,
                "vertex": label_map["P"],
                "arm0": label_map["A"],
                "arm1": label_map["C"],
                "radius_px": 38.0,
            },
        ),
        "evidence_tokens": tokens,
        "annotation_values": {
            str(visible_by_canonical[key]): int(value)
            for key, value in value_by_canonical.items()
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "external_point": str(label_map["P"]),
            "near_point": str(label_map["A"]),
            "far_point": str(label_map["B"]),
            "near_point_alt": str(label_map["C"]),
            "far_point_alt": str(label_map["D"]),
            "inside_segment": str(visible_by_canonical["AB"]),
            "outside_second_segment": str(visible_by_canonical["PC"]),
            "inside_second_segment": str(visible_by_canonical["CD"]),
            "answer_segment": str(visible_by_canonical[str(canonical_answer_segment)]),
        },
    }


def _circle_point(radius: float, angle_degrees: float) -> Point:
    angle = math.radians(float(angle_degrees))
    return (float(radius * math.cos(angle)), float(radius * math.sin(angle)))


def _rotated_tangent_unit(angle_degrees: float) -> Point:
    angle = math.radians(float(angle_degrees))
    return (float(-math.sin(angle)), float(math.cos(angle)))


def _add_points(a: Point, b: Point, *, scale: float = 1.0) -> Point:
    return (float(a[0] + (float(scale) * b[0])), float(a[1] + (float(scale) * b[1])))


def _build_intersecting_chords_arc_scene(
    rng, *, query: _ResolvedQuery
) -> Dict[str, Any]:
    target_arc = int(query.target_answer)
    if int(target_arc) % 10 != 0 or not (40 <= int(target_arc) <= 180):
        raise ValueError(
            f"unsupported target answer for intersecting-chords arc theorem: {query.target_answer}"
        )
    label_map = _sample_point_label_map(rng, ("O", "A", "B", "C", "D", "E"))
    known_arc_candidates = [
        value
        for value in range(40, 171, 10)
        if 35 <= int(360 - int(target_arc) - int(value) - 55)
    ]
    if not known_arc_candidates:
        raise ValueError(f"no feasible known arc for target arc: {query.target_answer}")
    known_arc = int(rng.choice(known_arc_candidates))
    gap_bc_candidates = [
        value
        for value in range(45, 131, 5)
        if int(360 - int(known_arc) - int(target_arc) - int(value)) >= 45
    ]
    if not gap_bc_candidates:
        raise ValueError(f"no feasible arc gap for target arc: {query.target_answer}")
    arc_bc = int(rng.choice(gap_bc_candidates))
    arc_da = int(360 - int(known_arc) - int(target_arc) - int(arc_bc))
    angle_value = int((int(known_arc) + int(target_arc)) // 2)
    radius = float(rng.choice((10, 11, 12, 13, 14)))
    rotation = float(rng.choice((35, 50, 65, 80, 95, 110, 125)))
    center = (0.0, 0.0)
    angles = {
        "A": float(rotation),
        "B": float(rotation + known_arc),
        "C": float(rotation + known_arc + arc_bc),
        "D": float(rotation + known_arc + arc_bc + target_arc),
    }
    canonical_point_model = {
        "O": center,
        "A": _circle_point(radius, angles["A"]),
        "B": _circle_point(radius, angles["B"]),
        "C": _circle_point(radius, angles["C"]),
        "D": _circle_point(radius, angles["D"]),
    }
    canonical_point_model["E"] = _line_intersection(
        canonical_point_model["A"],
        canonical_point_model["C"],
        canonical_point_model["B"],
        canonical_point_model["D"],
    )
    observed_angle = _angle_degrees_at(
        canonical_point_model["E"],
        canonical_point_model["A"],
        canonical_point_model["B"],
    )
    if abs(int(observed_angle) - int(angle_value)) > 1:
        raise ValueError("sampled intersecting-chords angle does not match arc theorem")
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    first_chord = _visible_segment(label_map, "A", "C")
    second_chord = _visible_segment(label_map, "B", "D")
    angle_name = _visible_angle(label_map, "A", "E", "B")
    known_arc_name = _visible_arc(label_map, "A", "B")
    answer_arc_name = _visible_arc(label_map, "C", "D")
    distractor_arc_name = _visible_arc(label_map, "B", "C")
    angle_token = f"{angle_name}={int(angle_value)}"
    known_arc_token = f"{known_arc_name}={int(known_arc)}"
    distractor_token = f"{distractor_arc_name}={int(arc_bc)}"
    query_arc_token = f"{answer_arc_name}=?"
    theorem_trace = {
        "theorem": "intersecting_chords_angle",
        "label_map": dict(label_map),
        "angle_AEB": int(angle_value),
        "arc_AB": int(known_arc),
        "arc_BC": int(arc_bc),
        "arc_CD": int(target_arc),
        "arc_DA": int(arc_da),
        "canonical_answer_segment": "arcCD",
        "answer_segment": str(answer_arc_name),
        "answer_value": int(target_arc),
        "arc_sum_for_angle": int(known_arc + target_arc),
        "distractor_tokens": [str(distractor_token)],
    }
    return {
        "point_model": point_model,
        "circle_center": center,
        "circle_radius": float(radius),
        "segments": {
            "AC": (label_map["A"], label_map["C"]),
            "BD": (label_map["B"], label_map["D"]),
        },
        "measurement_specs": tuple(),
        "angle_marker_specs": (
            {
                "token": angle_token,
                "vertex": label_map["E"],
                "arm0": label_map["A"],
                "arm1": label_map["B"],
                "radius_px": 42.0,
            },
        ),
        "circle_arc_specs": (
            {"token": known_arc_token, "start": label_map["A"], "end": label_map["B"]},
            {"token": distractor_token, "start": label_map["B"], "end": label_map["C"]},
            {"token": query_arc_token, "start": label_map["C"], "end": label_map["D"]},
        ),
        "evidence_tokens": (angle_token, known_arc_token),
        "annotation_values": {
            str(angle_name): int(angle_value),
            str(known_arc_name): int(known_arc),
            str(distractor_arc_name): int(arc_bc),
            str(answer_arc_name): int(target_arc),
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "first_chord_segment": str(first_chord),
            "second_chord_segment": str(second_chord),
            "intersection_label": str(label_map["E"]),
            "known_arc": str(known_arc_name),
            "answer_arc": str(answer_arc_name),
            "answer_segment": str(answer_arc_name),
        },
    }


def _build_multi_step_angle_scene(rng, *, query: _ResolvedQuery) -> Dict[str, Any]:
    target_angle = int(query.target_answer)
    if int(target_angle) % 5 != 0 or not (45 <= int(target_angle) <= 135):
        raise ValueError(
            f"unsupported target answer for multi-step circle angle theorem: {query.target_answer}"
        )
    label_map = _sample_point_label_map(rng, ("O", "A", "B", "C", "D", "E"))
    arc_sum = int(2 * int(target_angle))
    known_arc_candidates = [
        value for value in range(40, 171, 10) if 40 <= int(arc_sum - int(value)) <= 170
    ]
    if not known_arc_candidates:
        raise ValueError(
            f"no feasible known arcs for target angle: {query.target_answer}"
        )
    first_arc = int(rng.choice(known_arc_candidates))
    opposite_arc = int(arc_sum - int(first_arc))
    remaining_arc = int(360 - int(first_arc) - int(opposite_arc))
    if int(remaining_arc) < 90:
        raise ValueError(
            f"no feasible remaining arcs for target angle: {query.target_answer}"
        )
    gap_bc_candidates = [
        value
        for value in range(45, int(remaining_arc) - 44, 5)
        if int(remaining_arc - int(value)) >= 45
    ]
    if not gap_bc_candidates:
        raise ValueError(f"no feasible arc gap for target angle: {query.target_answer}")
    arc_bc = int(rng.choice(gap_bc_candidates))
    arc_da = int(remaining_arc - int(arc_bc))
    radius = float(rng.choice((10, 11, 12, 13, 14)))
    rotation = float(rng.choice((30, 45, 60, 75, 90, 105, 120)))
    center = (0.0, 0.0)
    angles = {
        "A": float(rotation),
        "B": float(rotation + first_arc),
        "C": float(rotation + first_arc + arc_bc),
        "D": float(rotation + first_arc + arc_bc + opposite_arc),
    }
    canonical_point_model = {
        "O": center,
        "A": _circle_point(radius, angles["A"]),
        "B": _circle_point(radius, angles["B"]),
        "C": _circle_point(radius, angles["C"]),
        "D": _circle_point(radius, angles["D"]),
    }
    canonical_point_model["E"] = _line_intersection(
        canonical_point_model["A"],
        canonical_point_model["C"],
        canonical_point_model["B"],
        canonical_point_model["D"],
    )
    observed_angle = _angle_degrees_at(
        canonical_point_model["E"],
        canonical_point_model["A"],
        canonical_point_model["B"],
    )
    if abs(int(observed_angle) - int(target_angle)) > 1:
        raise ValueError(
            "sampled multi-step angle does not match intersecting-chords theorem"
        )
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    first_chord = _visible_segment(label_map, "A", "C")
    second_chord = _visible_segment(label_map, "B", "D")
    angle_name = _visible_angle(label_map, "A", "E", "B")
    first_arc_name = _visible_arc(label_map, "A", "B")
    opposite_arc_name = _visible_arc(label_map, "C", "D")
    distractor_arc_name = _visible_arc(label_map, "B", "C")
    answer_angle_token = f"{angle_name}=?"
    first_arc_token = f"{first_arc_name}={int(first_arc)}"
    opposite_arc_token = f"{opposite_arc_name}={int(opposite_arc)}"
    distractor_token = f"{distractor_arc_name}={int(arc_bc)}"
    theorem_trace = {
        "theorem": "intersecting_chords_angle_from_arcs",
        "label_map": dict(label_map),
        "angle_AEB": int(target_angle),
        "arc_AB": int(first_arc),
        "arc_BC": int(arc_bc),
        "arc_CD": int(opposite_arc),
        "arc_DA": int(arc_da),
        "canonical_answer_segment": "angleAEB",
        "answer_segment": str(angle_name),
        "answer_value": int(target_angle),
        "arc_sum_for_angle": int(first_arc + opposite_arc),
        "distractor_tokens": [str(distractor_token)],
    }
    return {
        "point_model": point_model,
        "circle_center": center,
        "circle_radius": float(radius),
        "segments": {
            "AC": (label_map["A"], label_map["C"]),
            "BD": (label_map["B"], label_map["D"]),
        },
        "measurement_specs": tuple(),
        "angle_marker_specs": (
            {
                "token": answer_angle_token,
                "vertex": label_map["E"],
                "arm0": label_map["A"],
                "arm1": label_map["B"],
                "radius_px": 42.0,
            },
        ),
        "circle_arc_specs": (
            {"token": first_arc_token, "start": label_map["A"], "end": label_map["B"]},
            {"token": distractor_token, "start": label_map["B"], "end": label_map["C"]},
            {
                "token": opposite_arc_token,
                "start": label_map["C"],
                "end": label_map["D"],
            },
        ),
        "evidence_tokens": (first_arc_token, opposite_arc_token),
        "annotation_values": {
            str(angle_name): int(target_angle),
            str(first_arc_name): int(first_arc),
            str(distractor_arc_name): int(arc_bc),
            str(opposite_arc_name): int(opposite_arc),
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "first_chord_segment": str(first_chord),
            "second_chord_segment": str(second_chord),
            "intersection_label": str(label_map["E"]),
            "answer_angle": str(angle_name),
            "answer_segment": str(angle_name),
        },
    }


def _build_inscribed_angle_scene(rng, *, query: _ResolvedQuery) -> Dict[str, Any]:
    query_variant = str(query.query_variant)
    if query_variant == "central_angle_from_inscribed":
        central_angle = int(query.target_answer)
        if int(central_angle) % 10 != 0 or not (40 <= int(central_angle) <= 160):
            raise ValueError(f"unsupported central angle answer: {query.target_answer}")
        inscribed_angle = int(central_angle // 2)
        answer_kind = "central"
    elif query_variant in {"inscribed_angle_from_central", "inscribed_angle_from_arc"}:
        inscribed_angle = int(query.target_answer)
        if int(inscribed_angle) % 5 != 0 or not (20 <= int(inscribed_angle) <= 80):
            raise ValueError(
                f"unsupported inscribed angle answer: {query.target_answer}"
            )
        central_angle = int(2 * int(inscribed_angle))
        answer_kind = "inscribed"
    else:
        raise ValueError(f"unsupported inscribed-angle query: {query_variant}")

    radius = float(rng.choice((10, 11, 12, 13, 14)))
    rotation = float(rng.choice((20, 35, 50, 65, 80, 95, 110, 125, 140)))
    c_offset = float(rng.choice((-35, -25, -15, 15, 25, 35)))
    angles = {
        "A": float(rotation - (0.5 * central_angle)),
        "B": float(rotation + (0.5 * central_angle)),
        "C": float(rotation + 180.0 + c_offset),
    }
    center = (0.0, 0.0)
    canonical_point_model = {
        "O": center,
        "A": _circle_point(radius, angles["A"]),
        "B": _circle_point(radius, angles["B"]),
        "C": _circle_point(radius, angles["C"]),
    }
    observed_inscribed = _angle_degrees_at(
        canonical_point_model["C"],
        canonical_point_model["A"],
        canonical_point_model["B"],
    )
    observed_central = _angle_degrees_at(
        canonical_point_model["O"],
        canonical_point_model["A"],
        canonical_point_model["B"],
    )
    if abs(int(observed_inscribed) - int(inscribed_angle)) > 1:
        raise ValueError("sampled inscribed angle does not match intercepted arc")
    if abs(int(observed_central) - int(central_angle)) > 1:
        raise ValueError("sampled central angle does not match intercepted arc")

    label_map = _sample_point_label_map(rng, ("O", "A", "B", "C"))
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    central_angle_name = _visible_angle(label_map, "A", "O", "B")
    inscribed_angle_name = _visible_angle(label_map, "A", "C", "B")
    intercepted_arc_name = _visible_arc(label_map, "A", "B")
    distractor_arc_name = _visible_arc(label_map, "B", "C")
    raw_distractor_arc = float((angles["C"] - angles["B"]) % 360.0)
    distractor_arc = int(
        round(min(raw_distractor_arc, 360.0 - raw_distractor_arc) / 5.0) * 5
    )

    token_by_kind = {
        "central": f"{central_angle_name}={int(central_angle)}",
        "inscribed": f"{inscribed_angle_name}={int(inscribed_angle)}",
        "arc": f"{intercepted_arc_name}={int(central_angle)}",
    }
    if query_variant == "inscribed_angle_from_central":
        evidence_tokens = (token_by_kind["central"],)
        angle_marker_specs = (
            {
                "token": token_by_kind["central"],
                "vertex": label_map["O"],
                "arm0": label_map["A"],
                "arm1": label_map["B"],
                "radius_px": 48.0,
            },
            {
                "token": f"{inscribed_angle_name}=?",
                "vertex": label_map["C"],
                "arm0": label_map["A"],
                "arm1": label_map["B"],
                "radius_px": 42.0,
            },
        )
        circle_arc_specs = (
            {
                "token": f"{distractor_arc_name}={int(distractor_arc)}",
                "start": label_map["B"],
                "end": label_map["C"],
            },
        )
    elif query_variant == "central_angle_from_inscribed":
        evidence_tokens = (token_by_kind["inscribed"],)
        angle_marker_specs = (
            {
                "token": f"{central_angle_name}=?",
                "vertex": label_map["O"],
                "arm0": label_map["A"],
                "arm1": label_map["B"],
                "radius_px": 48.0,
            },
            {
                "token": token_by_kind["inscribed"],
                "vertex": label_map["C"],
                "arm0": label_map["A"],
                "arm1": label_map["B"],
                "radius_px": 42.0,
            },
        )
        circle_arc_specs = (
            {
                "token": f"{distractor_arc_name}={int(distractor_arc)}",
                "start": label_map["B"],
                "end": label_map["C"],
            },
        )
    else:
        evidence_tokens = (token_by_kind["arc"],)
        angle_marker_specs = (
            {
                "token": f"{inscribed_angle_name}=?",
                "vertex": label_map["C"],
                "arm0": label_map["A"],
                "arm1": label_map["B"],
                "radius_px": 42.0,
            },
        )
        circle_arc_specs = (
            {
                "token": token_by_kind["arc"],
                "start": label_map["A"],
                "end": label_map["B"],
            },
            {
                "token": f"{distractor_arc_name}={int(distractor_arc)}",
                "start": label_map["B"],
                "end": label_map["C"],
            },
        )

    answer_name = (
        central_angle_name if answer_kind == "central" else inscribed_angle_name
    )
    answer_value = int(central_angle if answer_kind == "central" else inscribed_angle)
    distractor_token = f"{distractor_arc_name}={int(distractor_arc)}"
    theorem_trace = {
        "theorem": "inscribed_angle",
        "label_map": dict(label_map),
        "central_angle_AOB": int(central_angle),
        "inscribed_angle_ACB": int(inscribed_angle),
        "arc_AB": int(central_angle),
        "arc_BC": int(distractor_arc),
        "canonical_answer_segment": (
            "angleAOB" if answer_kind == "central" else "angleACB"
        ),
        "answer_segment": str(answer_name),
        "answer_value": int(answer_value),
        "distractor_tokens": [str(distractor_token)],
    }
    return {
        "point_model": point_model,
        "circle_center": center,
        "circle_radius": float(radius),
        "segments": {
            "OA": (label_map["O"], label_map["A"]),
            "OB": (label_map["O"], label_map["B"]),
            "CA": (label_map["C"], label_map["A"]),
            "CB": (label_map["C"], label_map["B"]),
        },
        "measurement_specs": tuple(),
        "angle_marker_specs": angle_marker_specs,
        "circle_arc_specs": circle_arc_specs,
        "evidence_tokens": evidence_tokens,
        "annotation_values": {
            str(central_angle_name): int(central_angle),
            str(inscribed_angle_name): int(inscribed_angle),
            str(intercepted_arc_name): int(central_angle),
            str(distractor_arc_name): int(distractor_arc),
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "central_angle": str(central_angle_name),
            "inscribed_angle": str(inscribed_angle_name),
            "intercepted_arc": str(intercepted_arc_name),
            "answer_angle": str(answer_name),
            "answer_segment": str(answer_name),
        },
    }


def _build_tangent_chord_angle_scene(rng, *, query: _ResolvedQuery) -> Dict[str, Any]:
    query_variant = str(query.query_variant)
    tangent_chord_angle = int(query.target_answer)
    if int(tangent_chord_angle) % 5 != 0 or not (25 <= int(tangent_chord_angle) <= 75):
        raise ValueError(
            f"unsupported tangent-chord angle answer: {query.target_answer}"
        )
    if query_variant not in {
        "tangent_chord_angle_from_arc",
        "tangent_chord_angle_from_inscribed",
    }:
        raise ValueError(f"unsupported tangent-chord query: {query_variant}")

    central_angle = int(2 * int(tangent_chord_angle))
    radius = float(rng.choice((10, 11, 12, 13, 14)))
    rotation = float(rng.choice((10, 25, 40, 55, 70, 85, 100, 115, 130)))
    tangent_unit = _rotated_tangent_unit(rotation)
    point_t = _circle_point(radius, rotation)
    point_a = _circle_point(radius, rotation + central_angle)
    arc_ab = int(rng.choice((105, 120, 135, 150)))
    point_b = _circle_point(radius, rotation + central_angle + float(arc_ab))
    point_p = _add_points(point_t, tangent_unit, scale=float(radius * 1.05))
    center = (0.0, 0.0)
    canonical_point_model = {
        "O": center,
        "P": point_p,
        "T": point_t,
        "A": point_a,
        "B": point_b,
    }
    observed_tangent_angle = _angle_degrees_at(
        canonical_point_model["T"],
        canonical_point_model["P"],
        canonical_point_model["A"],
    )
    observed_inscribed = _angle_degrees_at(
        canonical_point_model["B"],
        canonical_point_model["T"],
        canonical_point_model["A"],
    )
    if abs(int(observed_tangent_angle) - int(tangent_chord_angle)) > 1:
        raise ValueError("sampled tangent-chord angle does not match intercepted arc")
    if abs(int(observed_inscribed) - int(tangent_chord_angle)) > 1:
        raise ValueError("sampled inscribed angle does not match tangent-chord angle")

    label_map = _sample_point_label_map(rng, ("O", "P", "T", "A", "B"))
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    tangent_chord_angle_name = _visible_angle(label_map, "P", "T", "A")
    inscribed_angle_name = _visible_angle(label_map, "T", "B", "A")
    intercepted_arc_name = _visible_arc(label_map, "T", "A")
    distractor_arc_name = _visible_arc(label_map, "A", "B")
    distractor_arc = int(arc_ab)
    answer_token = f"{tangent_chord_angle_name}=?"
    arc_token = f"{intercepted_arc_name}={int(central_angle)}"
    inscribed_token = f"{inscribed_angle_name}={int(tangent_chord_angle)}"
    distractor_token = f"{distractor_arc_name}={int(distractor_arc)}"
    if query_variant == "tangent_chord_angle_from_arc":
        evidence_tokens = (arc_token,)
        extra_angle_token: str | None = None
    else:
        evidence_tokens = (inscribed_token,)
        extra_angle_token = inscribed_token

    angle_marker_specs: Tuple[Mapping[str, Any], ...]
    if extra_angle_token is None:
        angle_marker_specs = (
            {
                "token": answer_token,
                "vertex": label_map["T"],
                "arm0": label_map["P"],
                "arm1": label_map["A"],
                "radius_px": 42.0,
            },
        )
    else:
        angle_marker_specs = (
            {
                "token": answer_token,
                "vertex": label_map["T"],
                "arm0": label_map["P"],
                "arm1": label_map["A"],
                "radius_px": 42.0,
            },
            {
                "token": extra_angle_token,
                "vertex": label_map["B"],
                "arm0": label_map["T"],
                "arm1": label_map["A"],
                "radius_px": 38.0,
            },
        )

    circle_arc_specs = (
        {
            "token": (
                arc_token if query_variant == "tangent_chord_angle_from_arc" else None
            ),
            "start": label_map["T"],
            "end": label_map["A"],
        },
        {"token": distractor_token, "start": label_map["A"], "end": label_map["B"]},
    )
    theorem_trace = {
        "theorem": "tangent_chord_angle",
        "label_map": dict(label_map),
        "angle_PTA": int(tangent_chord_angle),
        "angle_TBA": int(tangent_chord_angle),
        "arc_TA": int(central_angle),
        "arc_AB": int(distractor_arc),
        "canonical_answer_segment": "anglePTA",
        "answer_segment": str(tangent_chord_angle_name),
        "answer_value": int(tangent_chord_angle),
        "distractor_tokens": [str(distractor_token)],
    }
    return {
        "point_model": point_model,
        "circle_center": center,
        "circle_radius": float(radius),
        "segments": {
            "PT": (label_map["P"], label_map["T"]),
            "TA": (label_map["T"], label_map["A"]),
            "OT": (label_map["O"], label_map["T"]),
            "BT": (label_map["B"], label_map["T"]),
            "BA": (label_map["B"], label_map["A"]),
        },
        "measurement_specs": tuple(),
        "angle_marker_specs": angle_marker_specs,
        "circle_arc_specs": circle_arc_specs,
        "evidence_tokens": evidence_tokens,
        "annotation_values": {
            str(tangent_chord_angle_name): int(tangent_chord_angle),
            str(inscribed_angle_name): int(tangent_chord_angle),
            str(intercepted_arc_name): int(central_angle),
            str(distractor_arc_name): int(distractor_arc),
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "tangent_chord_angle": str(tangent_chord_angle_name),
            "inscribed_angle": str(inscribed_angle_name),
            "intercepted_arc": str(intercepted_arc_name),
            "answer_angle": str(tangent_chord_angle_name),
            "answer_segment": str(tangent_chord_angle_name),
        },
    }


def _build_scene_payload(rng, *, query: _ResolvedQuery) -> Dict[str, Any]:
    if str(query.query_variant) == "diameter_perpendicular_chord_length":
        return _build_diameter_perpendicular_chord_scene(rng, query=query)
    if str(query.query_variant) == "secant_secant_variable_segment_length":
        return _build_secant_secant_variable_scene(rng, query=query)
    if str(query.query_variant) == "tangent_secant_length":
        return _build_tangent_secant_scene(rng, query=query)
    if str(query.query_variant) == "secant_secant_length":
        return _build_secant_secant_scene(rng, query=query)
    if str(query.query_variant) == "intersecting_chords_arc_measure":
        return _build_intersecting_chords_arc_scene(rng, query=query)
    if str(query.query_variant) == "multi_step_angle_value":
        return _build_multi_step_angle_scene(rng, query=query)
    if str(query.query_variant) in {
        "inscribed_angle_from_central",
        "central_angle_from_inscribed",
        "inscribed_angle_from_arc",
    }:
        return _build_inscribed_angle_scene(rng, query=query)
    if str(query.query_variant) in {
        "tangent_chord_angle_from_arc",
        "tangent_chord_angle_from_inscribed",
    }:
        return _build_tangent_chord_angle_scene(rng, query=query)
    raise ValueError(f"unsupported query_variant: {query.query_variant}")


class GeometryCircleTheoremValueTask:
    """Solve one integer value from a labeled circle-theorem diagram."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = "circle"

    def generate(
        self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int
    ) -> TaskOutput:
        query = _resolve_query(int(instance_seed), params=params)
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.scene")
        last_error: Exception | None = None
        rendered_scene: _RenderedScene | None = None
        selected_scene_payload: Dict[str, Any] | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                scene_payload = _build_scene_payload(rng, query=query)
                rendered_scene = _render_base_scene(
                    rng=rng,
                    instance_seed=int(instance_seed),
                    params=params,
                    point_model=scene_payload["point_model"],
                    circle_center=scene_payload["circle_center"],
                    circle_radius=float(scene_payload["circle_radius"]),
                    segments=scene_payload["segments"],
                    measurement_specs=scene_payload["measurement_specs"],
                    evidence_tokens=scene_payload["evidence_tokens"],
                    annotation_values=scene_payload["annotation_values"],
                    theorem_trace=scene_payload["theorem_trace"],
                    angle_marker_specs=scene_payload.get("angle_marker_specs"),
                    circle_arc_specs=scene_payload.get("circle_arc_specs"),
                )
                selected_scene_payload = dict(scene_payload)
                break
            except Exception as exc:
                last_error = exc
                continue
        if rendered_scene is None or selected_scene_payload is None:
            raise RuntimeError(
                f"failed to generate {self.task_id} instance"
            ) from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_integer",
                "evidence_hint_measurement_tokens",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        evidence_bboxes = [
            [round(float(coord), 3) for coord in bbox]
            for bbox in rendered_scene.evidence_bboxes
        ]
        evidence_points = [
            [
                round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
                round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
            ]
            for bbox in evidence_bboxes
        ]
        json_example, json_example_answer_only = (
            _build_measurement_bbox_prompt_examples(
                evidence_count=len(evidence_bboxes),
            )
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(
                    prompt_defaults["json_output_contract_answer_only"]
                ),
                "evidence_hint": str(
                    prompt_defaults["evidence_hint_measurement_tokens"]
                ),
                "answer_hint": str(prompt_defaults["answer_hint_integer"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                **dict(selected_scene_payload.get("prompt_slots", {})),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(rendered_scene.answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        query_params = {
            "query_variant": str(query.query_variant),
            "variant_probabilities": dict(query.query_variant_probabilities),
            "query_variant_probabilities": dict(query.query_variant_probabilities),
            "target_answer": int(query.target_answer),
            "target_answer_probabilities": dict(query.target_answer_probabilities),
        }
        if query.tangent_secant_target_kind is not None:
            query_params["tangent_secant_target_kind"] = str(
                query.tangent_secant_target_kind
            )
            query_params["tangent_secant_target_kind_probabilities"] = dict(
                query.tangent_secant_target_kind_probabilities or {}
            )
        if query.secant_secant_variable_target_kind is not None:
            query_params["secant_secant_variable_target_kind"] = str(
                query.secant_secant_variable_target_kind
            )
            query_params["secant_secant_variable_target_kind_probabilities"] = dict(
                query.secant_secant_variable_target_kind_probabilities or {}
            )
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_circle_theorem_value",
                "entities": list(rendered_scene.scene_entities),
                "relations": {
                    "query_variant": str(query.query_variant),
                    "answer_segment": str(
                        rendered_scene.theorem_trace["answer_segment"]
                    ),
                    "answer_value": int(rendered_scene.answer_value),
                    "theorem": str(rendered_scene.theorem_trace["theorem"]),
                },
            },
            "query_spec": {
                "query_variant": str(query.query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(
                    prompt_artifacts.prompt_variant_active_key
                ),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_size": int(rendered_scene.image.size[0]),
                "coord_space": "pixel",
                "background_style": dict(rendered_scene.background_meta),
                "post_image_noise": dict(rendered_scene.post_noise_meta),
                "shape_style": dict(rendered_scene.shape_style),
                **dict(rendered_scene.render_params),
            },
            "render_map": {
                "point_pixels": dict(rendered_scene.point_pixels),
                "point_label_bboxes": dict(rendered_scene.point_label_bboxes),
                "point_model": dict(rendered_scene.point_model),
                "segment_pixels": dict(rendered_scene.segment_pixels),
                "circle_center_pixel": list(rendered_scene.circle_center_pixel),
                "circle_center_model": list(rendered_scene.circle_center_model),
                "circle_radius_px": float(rendered_scene.circle_radius_px),
                "circle_radius_model": float(rendered_scene.circle_radius_model),
                "measurement_token_bboxes": dict(rendered_scene.token_bboxes),
                "coord_space": "pixel",
            },
            "execution_trace": {
                "query_variant": str(query.query_variant),
                "query_variant_probabilities": dict(query.query_variant_probabilities),
                "variant_probabilities": dict(query.query_variant_probabilities),
                "target_answer": int(query.target_answer),
                "target_answer_probabilities": dict(query.target_answer_probabilities),
                "answer_type": "integer",
                "answer_value": int(rendered_scene.answer_value),
                "evidence_tokens": list(rendered_scene.evidence_tokens),
                "annotation_values": dict(rendered_scene.annotation_values),
                **dict(rendered_scene.theorem_trace),
            },
            "witness_symbolic": {
                "type": "circle_theorem_measurement_tokens",
                "query_variant": str(query.query_variant),
                "answer_segment": str(rendered_scene.theorem_trace["answer_segment"]),
                "answer_value": int(rendered_scene.answer_value),
                "evidence_tokens": list(rendered_scene.evidence_tokens),
                "source_witness_type": "object_set",
                "original_evidence_value": list(rendered_scene.evidence_tokens),
                "annotation_values": dict(rendered_scene.annotation_values),
            },
            "projected_evidence": {
                "type": "bbox_set",
                "bbox_set": list(evidence_bboxes),
                "pixel_bbox_set": list(evidence_bboxes),
                "point_set": list(evidence_points),
                "pixel_point_set": list(evidence_points),
            },
        }

        complexity = build_geometry_circle_theorem_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            query_variant=str(query.query_variant),
            annotation_count=len(rendered_scene.token_bboxes),
            answer_value=int(rendered_scene.answer_value),
        )

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=rendered_scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant=str(query.query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometryCircleDiameterPerpendicularChordLengthValueTask(
    FixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve a length in a diameter-perpendicular-chord diagram."""

    task_id = "task_geometry__circle_theorem__diameter_perpendicular_chord_length_value"
    fixed_query_variant = "diameter_perpendicular_chord_length"
    public_scene_id = "circle_theorem"


@register_task
class GeometryCircleTangentSecantLengthValueTask(
    FixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve a length in a tangent-secant diagram."""

    task_id = "task_geometry__circle_theorem__tangent_secant_length_value"
    fixed_query_variant = "tangent_secant_length"
    public_scene_id = "circle_theorem"


@register_task
class GeometryCircleSecantSecantLengthValueTask(
    MultiFixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve a length in a secant-secant diagram."""

    task_id = "task_geometry__circle_theorem__secant_secant_length_value"
    fixed_query_variants = (
        "secant_secant_length",
        "secant_secant_variable_segment_length",
    )
    public_scene_id = "circle_theorem"


@register_task
class GeometryCircleIntersectingChordsArcMeasureValueTask(
    FixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve an arc measure in an intersecting-chords diagram."""

    task_id = "task_geometry__circle_theorem__intersecting_chords_arc_measure_value"
    fixed_query_variant = "intersecting_chords_arc_measure"
    public_scene_id = "circle_theorem"


@register_task
class GeometryCircleInscribedAngleValueTask(
    MultiFixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve a central or inscribed angle from the inscribed-angle theorem."""

    task_id = "task_geometry__circle_theorem__inscribed_angle_value"
    fixed_query_variants = (
        "inscribed_angle_from_central",
        "central_angle_from_inscribed",
        "inscribed_angle_from_arc",
    )
    public_scene_id = "circle_theorem"


@register_task
class GeometryCircleTangentChordAngleValueTask(
    MultiFixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve a tangent-chord angle from an arc or matching inscribed angle."""

    task_id = "task_geometry__circle_theorem__tangent_chord_angle_value"
    fixed_query_variants = (
        "tangent_chord_angle_from_arc",
        "tangent_chord_angle_from_inscribed",
    )
    public_scene_id = "circle_theorem"


@register_task
class GeometryCircleMultiStepAngleValueTask(
    FixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve an angle from multiple arc measurements in an intersecting-chords diagram."""

    task_id = "task_geometry__circle_theorem__multi_step_angle_value"
    fixed_query_variant = "multi_step_angle_value"
    public_scene_id = "circle_theorem"


__all__ = [
    "GeometryCircleDiameterPerpendicularChordLengthValueTask",
    "GeometryCircleIntersectingChordsArcMeasureValueTask",
    "GeometryCircleInscribedAngleValueTask",
    "GeometryCircleMultiStepAngleValueTask",
    "GeometryCircleSecantSecantLengthValueTask",
    "GeometryCircleTangentChordAngleValueTask",
    "GeometryCircleTangentSecantLengthValueTask",
    "GeometryCircleTheoremValueTask",
]
