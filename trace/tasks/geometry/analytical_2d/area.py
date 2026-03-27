"""Single-object analytical 2D area task."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_default,
    required_group_defaults,
    resolve_optional_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import (
    draw_text_centered,
    load_font,
    resolve_scene_label_font_size_px,
    resolve_text_label_center,
)
from ..shared.background_defaults import load_geometry_background_defaults
from ..shared.annotation_values import (
    build_role_value_evidence,
    format_annotation_value,
)
from ..shared.conic_geometry import (
    conic_render_anchor,
    draw_circle_outline,
    draw_ellipse_outline,
    sample_circle_instance_on_graph_paper,
    sample_ellipse_instance_on_graph_paper,
)
from ..shared.graph_paper import offset_point_by_grid_vector, sample_lattice_point_with_offsets
from ..shared.graph_rendering import graph_paper_grid_from_frame, scale_point
from ..shared.length_geometry import integer_length_vectors
from ..shared.noise_defaults import load_geometry_noise_defaults
from ..shared.polygon_geometry import alphabetic_labels, draw_polygon_outline
from ..shared.render_variation import sample_int_render_param
from ..shared.shape_style import (
    GeometryShapeStyle,
    extract_background_anchor_colors,
    sample_geometry_shape_style,
)
from ..shared.single_object_scene import (
    GraphSceneContext,
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from .defaults import ANALYTICAL_SHARED_DEFAULTS

Point = Tuple[float, float]
Segment = Tuple[Point, Point]

_SHAPES: Tuple[str, ...] = (
    "rectangle",
    "triangle",
    "parallelogram",
    "trapezoid",
    "rhombus",
    "circle",
    "ellipse",
)
_REASONING_MODES: Tuple[str, ...] = ("explicit", "derived")
_INTEGER_SHAPES = {"rectangle", "triangle", "parallelogram", "trapezoid", "rhombus"}
_PI_SHAPES = {"circle", "ellipse"}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable defaults for geometry analytical area generation."""

    canvas_size_min: int = ANALYTICAL_SHARED_DEFAULTS.canvas_size_min
    canvas_size_max: int = ANALYTICAL_SHARED_DEFAULTS.canvas_size_max
    graph_cells_min: int = ANALYTICAL_SHARED_DEFAULTS.graph_cells_min
    graph_cells_max: int = ANALYTICAL_SHARED_DEFAULTS.graph_cells_max
    line_width: int = ANALYTICAL_SHARED_DEFAULTS.line_width
    helper_line_width: int = ANALYTICAL_SHARED_DEFAULTS.helper_line_width
    label_offset_px: float = ANALYTICAL_SHARED_DEFAULTS.label_offset_px
    label_font_size_min: int = ANALYTICAL_SHARED_DEFAULTS.label_font_size_min
    label_font_size_max: int = ANALYTICAL_SHARED_DEFAULTS.label_font_size_max
    label_stroke_width: int = ANALYTICAL_SHARED_DEFAULTS.label_stroke_width
    answer_min: int = ANALYTICAL_SHARED_DEFAULTS.answer_min
    answer_max: int = ANALYTICAL_SHARED_DEFAULTS.answer_max
    side_min: int = 2
    side_max: int = 12
    right_triangle_max_component: int = 18


@dataclass(frozen=True)
class _AnnotationSpec:
    """One annotation label placement request."""

    ann_id: str
    text: str
    anchor: Point
    base_direction: Point
    offset_scale: float = 1.0
    point_a: Point | None = None
    point_b: Point | None = None


@dataclass(frozen=True)
class _CaseArtifacts:
    """Sampled analytical-shape case payload before prompt composition."""

    shape_variant: str
    reasoning_mode: str
    case_id: str
    question_key: str
    answer_type: str
    answer_scalar: int
    answer_value: int | str
    formula_expression: str
    evidence_ids: Tuple[str, ...]
    evidence_label_values: Dict[str, Any]
    evidence_annotations: Dict[str, str]
    annotation_centers: Dict[str, List[float]]
    entity: Dict[str, Any]
    render_anchor: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "analytical_2d")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_geometry_analytical_2d_area",
)
ANALYTICAL_POST_IMAGE_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="analytical_2d")
ANALYTICAL_POST_IMAGE_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="analytical_2d")


def _pi_expression(value: int) -> str:
    """Format one integer coefficient as canonical `kπ` text."""
    coefficient = int(value)
    if int(coefficient) == 1:
        return "π"
    return f"{int(coefficient)}π"


def _required_prompt_text(prompt_defaults: Mapping[str, Any], *, preferred_keys: Sequence[str], context: str) -> str:
    """Return first available non-empty prompt text among ordered key candidates."""
    for key in preferred_keys:
        if str(key) in prompt_defaults:
            return str(required_group_default(prompt_defaults, str(key), context=context))
    raise ValueError(f"missing required prompt key in {context}: one of {list(preferred_keys)}")


def _answer_bounds(params: Mapping[str, Any], *, gen_defaults: Mapping[str, Any]) -> Tuple[int, int]:
    """Resolve integer answer bounds for analytical area variants."""
    answer_min, answer_max = resolve_optional_int_bounds(
        params,
        gen_defaults,
        min_key="answer_min",
        max_key="answer_max",
        context="generation defaults for task_geometry_analytical_2d_area",
    )
    resolved_min = int(_DEFAULTS.answer_min if answer_min is None else answer_min)
    resolved_max = int(_DEFAULTS.answer_max if answer_max is None else answer_max)
    if int(resolved_min) > int(resolved_max):
        raise ValueError("answer_min must be <= answer_max")
    return int(resolved_min), int(resolved_max)


def _resolve_shape_and_mode(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[str, Dict[str, float], str, Dict[str, float]]:
    """Resolve shape/mode variants with weighted sampling and deterministic balancing."""
    shape_variant, shape_probs = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=_SHAPES,
        explicit_key="shape_variant",
        weights_key="shape_weights",
    )
    shape_variant = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(shape_variant),
        variant_probabilities=shape_probs,
        supported_variants=_SHAPES,
        balance_flag_key="balanced_shape_sampling",
        explicit_key="shape_variant",
        weights_key="shape_weights",
    )

    reasoning_mode, mode_probs = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=_REASONING_MODES,
        explicit_key="reasoning_mode",
        weights_key="mode_weights",
    )
    reasoning_mode = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(reasoning_mode),
        variant_probabilities=mode_probs,
        supported_variants=_REASONING_MODES,
        balance_flag_key="balanced_mode_sampling",
        explicit_key="reasoning_mode",
        weights_key="mode_weights",
    )
    return str(shape_variant), dict(shape_probs), str(reasoning_mode), dict(mode_probs)


@lru_cache(maxsize=8)
def _right_triangle_triplets(max_component: int) -> Tuple[Tuple[int, int, int], ...]:
    """Return sorted unique integer right-triangle triplets `(a, b, c)`."""
    vectors = integer_length_vectors(
        max_abs_component=max(2, int(max_component)),
        min_edge_length=1,
        max_edge_length=max(4, int(2 * int(max_component))),
    )
    out: set[Tuple[int, int, int]] = set()
    for dx, dy, length in vectors:
        a = abs(int(dx))
        b = abs(int(dy))
        c = int(length)
        if int(a) == 0 or int(b) == 0:
            continue
        lo, hi = sorted((int(a), int(b)))
        out.add((int(lo), int(hi), int(c)))
    return tuple(sorted(out))


def _analytical_unit_spacing_px(context: GraphSceneContext) -> int:
    """Return per-unit pixel spacing for analytical 2D scenes.

    Analytical tasks do not render graph paper, so unit spacing is decoupled
    from graph-cell counts and controlled by analytical render params.
    """
    raw_value = context.render_params.get("analytical_unit_spacing_px", context.graph_spacing)
    spacing_px = int(raw_value)
    if int(spacing_px) < 2:
        raise ValueError("analytical_unit_spacing_px must be >= 2")
    return int(spacing_px)


def _analytical_unit_padding_px(context: GraphSceneContext) -> int:
    """Return canvas padding in pixels reserved for analytical-shape placement."""
    raw_value = context.render_params.get("analytical_unit_padding_px", 20)
    padding_px = int(raw_value)
    if int(padding_px) < 0:
        raise ValueError("analytical_unit_padding_px must be >= 0")
    return int(padding_px)


def _unit_cap(context: GraphSceneContext) -> int:
    """Return conservative per-axis unit span cap for analytical scenes."""
    spacing_px = int(_analytical_unit_spacing_px(context))
    padding_px = int(_analytical_unit_padding_px(context))
    usable_px = max(8, int(context.canvas_size) - (2 * int(padding_px)))
    return max(4, int(usable_px // max(1, int(spacing_px))) - 2)


def _place_points_on_lattice(
    rng,
    *,
    context: GraphSceneContext,
    unit_points: Mapping[str, Tuple[int, int]],
    padding_units: int,
) -> Dict[str, Point]:
    """Place relative unit offsets on lattice under in-canvas constraints."""
    spacing_px = int(_analytical_unit_spacing_px(context))
    base_padding_px = int(_analytical_unit_padding_px(context))
    offsets = [tuple((int(offset[0]), int(offset[1]))) for offset in unit_points.values()]
    anchor = sample_lattice_point_with_offsets(
        rng,
        canvas_size=int(context.canvas_size),
        spacing=int(spacing_px),
        x_offsets=[int(offset[0]) for offset in offsets],
        y_offsets=[int(offset[1]) for offset in offsets],
        lattice_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
        padding=int(base_padding_px + (max(0, int(padding_units)) * int(spacing_px))),
    )
    return {
        str(key): offset_point_by_grid_vector(
            (float(anchor[0]), float(anchor[1])),
            (int(offset[0]), int(offset[1])),
            spacing=int(spacing_px),
        )
        for key, offset in unit_points.items()
    }


def _polygon_segments(vertices: Sequence[Point]) -> List[Segment]:
    """Return closed edge segment list for one polygon vertex sequence."""
    return [
        (
            (float(vertices[index][0]), float(vertices[index][1])),
            (float(vertices[(index + 1) % len(vertices)][0]), float(vertices[(index + 1) % len(vertices)][1])),
        )
        for index in range(len(vertices))
    ]


def _polygon_centroid(vertices: Sequence[Point]) -> Point:
    """Return arithmetic centroid of one polygon vertex sequence."""
    return (
        float(sum(float(point[0]) for point in vertices) / float(len(vertices))),
        float(sum(float(point[1]) for point in vertices) / float(len(vertices))),
    )


def _segment_midpoint(point_a: Point, point_b: Point) -> Point:
    """Return midpoint for one segment."""
    return (
        0.5 * (float(point_a[0]) + float(point_b[0])),
        0.5 * (float(point_a[1]) + float(point_b[1])),
    )


def _edge_annotation(
    *,
    ann_id: str,
    text: str,
    point_a: Point,
    point_b: Point,
    centroid: Point,
    offset_scale: float = 1.0,
) -> _AnnotationSpec:
    """Build one annotation aligned to a polygon edge and pushed outward."""
    mid_x, mid_y = _segment_midpoint(point_a, point_b)
    edge_dx = float(point_b[0]) - float(point_a[0])
    edge_dy = float(point_b[1]) - float(point_a[1])
    perp = (-float(edge_dy), float(edge_dx))
    outward = (float(mid_x) - float(centroid[0]), float(mid_y) - float(centroid[1]))
    if (float(perp[0]) * float(outward[0])) + (float(perp[1]) * float(outward[1])) < 0.0:
        perp = (-float(perp[0]), -float(perp[1]))
    return _AnnotationSpec(
        ann_id=str(ann_id),
        text=str(text),
        anchor=(float(mid_x), float(mid_y)),
        base_direction=(float(perp[0]), float(perp[1])),
        offset_scale=float(offset_scale),
        point_a=(float(point_a[0]), float(point_a[1])),
        point_b=(float(point_b[0]), float(point_b[1])),
    )


def _segment_annotation(
    *,
    ann_id: str,
    text: str,
    point_a: Point,
    point_b: Point,
    direction: Point | None = None,
    anchor_fraction: float = 0.5,
    offset_scale: float = 1.0,
) -> _AnnotationSpec:
    """Build one annotation aligned to an arbitrary segment."""
    frac = max(0.0, min(1.0, float(anchor_fraction)))
    mid_x = float(point_a[0]) + (float(point_b[0]) - float(point_a[0])) * float(frac)
    mid_y = float(point_a[1]) + (float(point_b[1]) - float(point_a[1])) * float(frac)
    if direction is None:
        edge_dx = float(point_b[0]) - float(point_a[0])
        edge_dy = float(point_b[1]) - float(point_a[1])
        base_direction = (-float(edge_dy), float(edge_dx))
    else:
        base_direction = (float(direction[0]), float(direction[1]))
    return _AnnotationSpec(
        ann_id=str(ann_id),
        text=str(text),
        anchor=(float(mid_x), float(mid_y)),
        base_direction=(float(base_direction[0]), float(base_direction[1])),
        offset_scale=float(offset_scale),
        point_a=(float(point_a[0]), float(point_a[1])),
        point_b=(float(point_b[0]), float(point_b[1])),
    )


def _point_key(point: Point, *, scale: int = 1000) -> Tuple[int, int]:
    """Return one hashable key for point-equivalence under small float noise."""
    return (
        int(round(float(point[0]) * float(scale))),
        int(round(float(point[1]) * float(scale))),
    )


def _materialize_case_annotations(
    rng,
    *,
    annotations: Sequence[_AnnotationSpec],
    evidence_label_values: Mapping[str, Any],
    extra_points: Sequence[Point] | None = None,
) -> Tuple[List[_AnnotationSpec], Dict[str, str], Dict[str, Point]]:
    """Build value-only annotation text + endpoint-based annotation tokens."""
    point_key_to_point: Dict[Tuple[int, int], Point] = {}
    ordered_keys: List[Tuple[int, int]] = []
    for annotation in annotations:
        if annotation.point_a is None or annotation.point_b is None:
            raise ValueError("annotation endpoints are required for analytical area evidence labeling")
        for point in (annotation.point_a, annotation.point_b):
            key = _point_key((float(point[0]), float(point[1])))
            if key not in point_key_to_point:
                point_key_to_point[key] = (float(point[0]), float(point[1]))
                ordered_keys.append(key)
    if extra_points:
        for point in extra_points:
            key = _point_key((float(point[0]), float(point[1])))
            if key not in point_key_to_point:
                point_key_to_point[key] = (float(point[0]), float(point[1]))
                ordered_keys.append(key)

    labels = alphabetic_labels(len(ordered_keys), start_index=int(rng.randrange(26)))
    point_key_to_label = {key: str(label) for key, label in zip(ordered_keys, labels)}
    point_label_positions = {
        str(point_key_to_label[key]): (float(point_key_to_point[key][0]), float(point_key_to_point[key][1]))
        for key in ordered_keys
    }

    role_to_token: Dict[str, str] = {}
    out: List[_AnnotationSpec] = []
    for annotation in annotations:
        role = str(annotation.ann_id)
        point_a = annotation.point_a
        point_b = annotation.point_b
        if point_a is None or point_b is None:
            raise ValueError("annotation endpoints are required for analytical area evidence labeling")
        a_key = _point_key((float(point_a[0]), float(point_a[1])))
        b_key = _point_key((float(point_b[0]), float(point_b[1])))
        token = f"{point_key_to_label[a_key]}{point_key_to_label[b_key]}"
        role_to_token[role] = str(token)
        value = evidence_label_values.get(role, "")
        out.append(
            _AnnotationSpec(
                ann_id=role,
                text=format_annotation_value(value),
                anchor=(float(annotation.anchor[0]), float(annotation.anchor[1])),
                base_direction=(float(annotation.base_direction[0]), float(annotation.base_direction[1])),
                offset_scale=float(annotation.offset_scale),
                point_a=(float(point_a[0]), float(point_a[1])),
                point_b=(float(point_b[0]), float(point_b[1])),
            )
        )
    return out, role_to_token, point_label_positions


def _draw_annotations(
    draw: ImageDraw.ImageDraw,
    *,
    annotations: Sequence[_AnnotationSpec],
    blocked_segments: Sequence[Segment],
    fixed_centers: Mapping[str, Point] | None = None,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
) -> Tuple[Dict[str, List[float]], List[Tuple[float, float, float, float]]]:
    """Draw annotation labels with overlap-aware placement and return centers."""
    scene_scale = max(1, int(context.scene_scale))
    font = load_font(int(label_font_size_px), bold=True)
    stroke_width = max(1, int(label_stroke_width))
    blocked_scaled = [
        (
            scale_point((float(seg_a[0]), float(seg_a[1])), int(scene_scale)),
            scale_point((float(seg_b[0]), float(seg_b[1])), int(scene_scale)),
        )
        for seg_a, seg_b in blocked_segments
    ]
    occupied_boxes: List[Tuple[float, float, float, float]] = []
    out: Dict[str, List[float]] = {}
    occupied_padding = max(4.0, 2.0 * float(scene_scale))
    for annotation in annotations:
        fixed_center = None
        if fixed_centers is not None:
            fixed_value = fixed_centers.get(str(annotation.ann_id))
            if fixed_value is not None:
                fixed_center = (float(fixed_value[0]), float(fixed_value[1]))
        if fixed_center is None:
            scaled_anchor = scale_point(
                (float(annotation.anchor[0]), float(annotation.anchor[1])),
                int(scene_scale),
            )
            adjusted_offset = float(
                max(
                    12.0,
                    float(label_offset_px) * 1.25 * max(0.5, float(annotation.offset_scale)),
                )
            )
            center, bbox = resolve_text_label_center(
                draw,
                text=str(annotation.text),
                anchor=(float(scaled_anchor[0]), float(scaled_anchor[1])),
                base_direction=(float(annotation.base_direction[0]), float(annotation.base_direction[1])),
                offset_px=float(adjusted_offset),
                font=font,
                blocked_segments=blocked_scaled,
                occupied_boxes=occupied_boxes,
                stroke_width=int(stroke_width),
                line_clearance_px=max(4.0, 2.4 * float(scene_scale)),
                canvas_size=int(context.canvas_size) * int(scene_scale),
            )
        else:
            scaled_center = scale_point((float(fixed_center[0]), float(fixed_center[1])), int(scene_scale))
            center = (float(scaled_center[0]), float(scaled_center[1]))
            text_bbox = draw.textbbox(
                (0.0, 0.0),
                str(annotation.text),
                font=font,
                stroke_width=int(stroke_width),
            )
            text_width = max(1.0, float(text_bbox[2]) - float(text_bbox[0]))
            text_height = max(1.0, float(text_bbox[3]) - float(text_bbox[1]))
            half_w = 0.5 * float(text_width)
            half_h = 0.5 * float(text_height)
            bbox = (
                float(center[0]) - float(half_w),
                float(center[1]) - float(half_h),
                float(center[0]) + float(half_w),
                float(center[1]) + float(half_h),
            )
        draw_text_centered(
            draw,
            text=str(annotation.text),
            center=(float(center[0]), float(center[1])),
            font=font,
            fill=tuple(int(value) for value in shape_style.label_color),
            stroke_fill=tuple(int(value) for value in shape_style.label_stroke_color),
            stroke_width=int(stroke_width),
        )
        occupied_boxes.append(
            (
                float(bbox[0]) - float(occupied_padding),
                float(bbox[1]) - float(occupied_padding),
                float(bbox[2]) + float(occupied_padding),
                float(bbox[3]) + float(occupied_padding),
            )
        )
        out[str(annotation.ann_id)] = [
            float(center[0]) / float(scene_scale),
            float(center[1]) / float(scene_scale),
        ]
    return out, occupied_boxes


def _draw_point_labels(
    draw: ImageDraw.ImageDraw,
    *,
    point_label_positions: Mapping[str, Point],
    blocked_segments: Sequence[Segment],
    occupied_boxes: Sequence[Tuple[float, float, float, float]],
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
) -> None:
    """Draw endpoint/vertex labels used by evidence annotation tokens."""
    if not point_label_positions:
        return

    def _placement_hints() -> Dict[str, Tuple[Point, int]]:
        """Build preferred outward directions and incident-segment counts per point label."""
        hints: Dict[str, Tuple[Point, int]] = {}
        tolerance_px = 1e-3
        for label, point in point_label_positions.items():
            point_x, point_y = float(point[0]), float(point[1])
            accum_x = 0.0
            accum_y = 0.0
            incident = 0
            for seg_a, seg_b in blocked_segments:
                ax, ay = float(seg_a[0]), float(seg_a[1])
                bx, by = float(seg_b[0]), float(seg_b[1])
                if math.hypot(point_x - ax, point_y - ay) <= float(tolerance_px):
                    dx, dy = float(point_x - bx), float(point_y - by)
                    norm = math.hypot(dx, dy)
                    if norm > 1e-6:
                        accum_x += float(dx / norm)
                        accum_y += float(dy / norm)
                    incident += 1
                if math.hypot(point_x - bx, point_y - by) <= float(tolerance_px):
                    dx, dy = float(point_x - ax), float(point_y - ay)
                    norm = math.hypot(dx, dy)
                    if norm > 1e-6:
                        accum_x += float(dx / norm)
                        accum_y += float(dy / norm)
                    incident += 1
            hints[str(label)] = ((float(accum_x), float(accum_y)), int(incident))
        return hints

    scene_scale = max(1, int(context.scene_scale))
    font = load_font(int(label_font_size_px), bold=True)
    stroke_width = max(1, int(label_stroke_width))
    point_hints = _placement_hints()
    blocked_scaled = [
        (
            scale_point((float(seg_a[0]), float(seg_a[1])), int(scene_scale)),
            scale_point((float(seg_b[0]), float(seg_b[1])), int(scene_scale)),
        )
        for seg_a, seg_b in blocked_segments
    ]
    occupied: List[Tuple[float, float, float, float]] = list(occupied_boxes)
    canvas_center = (
        0.5 * float(int(context.canvas_size) * int(scene_scale)),
        0.5 * float(int(context.canvas_size) * int(scene_scale)),
    )
    for label, point in sorted(point_label_positions.items()):
        scaled_anchor = scale_point((float(point[0]), float(point[1])), int(scene_scale))
        hint_direction, incident_count = point_hints.get(str(label), ((0.0, 0.0), 0))
        direction = (
            float(hint_direction[0]),
            float(hint_direction[1]),
        )
        if abs(float(direction[0])) + abs(float(direction[1])) < 1e-6:
            direction = (
                float(scaled_anchor[0]) - float(canvas_center[0]),
                float(scaled_anchor[1]) - float(canvas_center[1]),
            )
        if abs(float(direction[0])) + abs(float(direction[1])) < 1e-6:
            direction = (1.0, -1.0)
        incident_scale = 1.15 + (0.15 * float(max(0, int(incident_count) - 1)))
        offset_px = float(max(10.0, float(label_offset_px) * float(incident_scale)))
        center, bbox = resolve_text_label_center(
            draw,
            text=str(label),
            anchor=(float(scaled_anchor[0]), float(scaled_anchor[1])),
            base_direction=(float(direction[0]), float(direction[1])),
            offset_px=float(offset_px),
            font=font,
            blocked_segments=blocked_scaled,
            occupied_boxes=occupied,
            stroke_width=int(stroke_width),
            line_clearance_px=max(3.0, (2.0 + (0.5 * float(max(0, int(incident_count) - 1)))) * float(scene_scale)),
            canvas_size=int(context.canvas_size) * int(scene_scale),
        )
        draw_text_centered(
            draw,
            text=str(label),
            center=(float(center[0]), float(center[1])),
            font=font,
            fill=tuple(int(value) for value in shape_style.label_color),
            stroke_fill=tuple(int(value) for value in shape_style.label_stroke_color),
            stroke_width=int(stroke_width),
        )
        occupied_padding = max(4.0, 2.0 * float(scene_scale))
        occupied.append(
            (
                float(bbox[0]) - float(occupied_padding),
                float(bbox[1]) - float(occupied_padding),
                float(bbox[2]) + float(occupied_padding),
                float(bbox[3]) + float(occupied_padding),
            )
        )


def _draw_case_annotations(
    draw: ImageDraw.ImageDraw,
    *,
    rng,
    annotations: Sequence[_AnnotationSpec],
    evidence_label_values: Mapping[str, Any],
    blocked_segments: Sequence[Segment],
    fixed_centers: Mapping[str, Point] | None = None,
    extra_points: Sequence[Point] | None = None,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
) -> Tuple[Dict[str, List[float]], Dict[str, str]]:
    """Render value labels and endpoint vertex labels; return centers + role-token map."""
    value_annotations, role_to_token, point_label_positions = _materialize_case_annotations(
        rng,
        annotations=annotations,
        evidence_label_values=evidence_label_values,
        extra_points=extra_points,
    )
    centers, occupied_boxes = _draw_annotations(
        draw,
        annotations=value_annotations,
        blocked_segments=blocked_segments,
        fixed_centers=fixed_centers,
        context=context,
        shape_style=shape_style,
        label_offset_px=float(label_offset_px),
        label_font_size_px=int(label_font_size_px),
        label_stroke_width=int(label_stroke_width),
    )
    _draw_point_labels(
        draw,
        point_label_positions=point_label_positions,
        blocked_segments=blocked_segments,
        occupied_boxes=occupied_boxes,
        context=context,
        shape_style=shape_style,
        label_offset_px=float(label_offset_px),
        label_font_size_px=int(label_font_size_px),
        label_stroke_width=int(label_stroke_width),
    )
    return dict(centers), dict(role_to_token)


def _polygon_entity(
    *,
    entity_type: str,
    vertices: Sequence[Point],
    attrs: Mapping[str, Any],
) -> Dict[str, Any]:
    """Build one polygon-shaped scene entity payload."""
    entity_attrs = dict(attrs)
    entity_attrs["vertices"] = [[float(point[0]), float(point[1])] for point in vertices]
    return {
        "entity_id": "shape_1",
        "entity_type": str(entity_type),
        "attrs": entity_attrs,
    }


def _polygon_render_anchor(vertices: Sequence[Point]) -> Dict[str, Any]:
    """Build one deterministic polygon render anchor."""
    polyline = [[float(point[0]), float(point[1])] for point in vertices]
    return {
        "point": list(polyline[0]),
        "polyline": [*polyline, list(polyline[0])],
        "coord_space": "pixel",
    }


def _sample_rectangle_explicit_case(
    rng,
    *,
    draw: ImageDraw.ImageDraw,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
    gen_defaults: Mapping[str, Any],
) -> _CaseArtifacts:
    """Sample one explicit-rectangle area case and render it."""
    unit_cap = _unit_cap(context)
    side_min = max(2, int(group_default(gen_defaults, "side_min", _DEFAULTS.side_min)))
    side_max = max(side_min, int(group_default(gen_defaults, "side_max", _DEFAULTS.side_max)))
    side_max = min(int(side_max), int(unit_cap))
    if int(side_min) > int(side_max):
        raise ValueError("no feasible rectangle side range for current graph context")
    for _ in range(160):
        width = int(rng.randint(int(side_min), int(side_max)))
        height = int(rng.randint(int(side_min), int(side_max)))
        area = int(width * height)
        if int(area) < int(answer_min) or int(area) > int(answer_max):
            continue
        points = _place_points_on_lattice(
            rng,
            context=context,
            unit_points={
                "a": (0, 0),
                "b": (int(width), 0),
                "c": (int(width), int(height)),
                "d": (0, int(height)),
            },
            padding_units=1,
        )
        vertices = [points["a"], points["b"], points["c"], points["d"]]
        draw_polygon_outline(
            draw,
            vertices=[scale_point(point, int(context.scene_scale)) for point in vertices],
            line_width=max(1, int(line_width) * int(context.scene_scale)),
            line_color=tuple(int(value) for value in shape_style.line_color),
        )
        segments = _polygon_segments(vertices)
        centroid = _polygon_centroid(vertices)
        annotations = [
            _edge_annotation(
                ann_id="w",
                text=f"w={int(width)}",
                point_a=points["a"],
                point_b=points["b"],
                centroid=centroid,
            ),
            _edge_annotation(
                ann_id="h",
                text=f"h={int(height)}",
                point_a=points["b"],
                point_b=points["c"],
                centroid=centroid,
            ),
        ]
        evidence_values = {"w": int(width), "h": int(height)}
        centers, evidence_annotations = _draw_case_annotations(
            draw,
            rng=rng,
            annotations=annotations,
            evidence_label_values=evidence_values,
            blocked_segments=segments,
            extra_points=vertices,
            context=context,
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(context.scene_scale)),
        )
        return _CaseArtifacts(
            shape_variant="rectangle",
            reasoning_mode="explicit",
            case_id="rectangle_explicit",
            question_key="question_text_rectangle_explicit",
            answer_type="integer",
            answer_scalar=int(area),
            answer_value=int(area),
            formula_expression="A = w * h",
            evidence_ids=("w", "h"),
            evidence_label_values=dict(evidence_values),
            evidence_annotations=dict(evidence_annotations),
            annotation_centers=dict(centers),
            entity=_polygon_entity(
                entity_type="rectangle",
                vertices=vertices,
                attrs={
                    "shape_variant": "rectangle",
                    "reasoning_mode": "explicit",
                    "width_units": int(width),
                    "height_units": int(height),
                    "area_square_units": int(area),
                },
            ),
            render_anchor=_polygon_render_anchor(vertices),
        )
    raise ValueError("failed to sample rectangle explicit case")


def _sample_rectangle_derived_case(
    rng,
    *,
    draw: ImageDraw.ImageDraw,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
    gen_defaults: Mapping[str, Any],
) -> _CaseArtifacts:
    """Sample one rectangle side+diagonal derived-area case and render it."""
    unit_cap = _unit_cap(context)
    max_component = int(group_default(gen_defaults, "right_triangle_max_component", _DEFAULTS.right_triangle_max_component))
    triplets = [
        (int(a), int(b), int(c))
        for a, b, c in _right_triangle_triplets(max_component)
        if int(a) <= int(unit_cap) and int(b) <= int(unit_cap)
    ]
    if not triplets:
        raise ValueError("no feasible right-triangle triplets for rectangle derived case")
    for _ in range(200):
        leg_a, leg_b, hyp = triplets[int(rng.randrange(len(triplets)))]
        known_side = int(leg_a if bool(rng.randrange(2)) else leg_b)
        other_side = int(leg_b if int(known_side) == int(leg_a) else leg_a)
        width = int(known_side)
        height = int(other_side)
        area = int(width * height)
        if int(area) < int(answer_min) or int(area) > int(answer_max):
            continue
        points = _place_points_on_lattice(
            rng,
            context=context,
            unit_points={
                "a": (0, 0),
                "b": (int(width), 0),
                "c": (int(width), int(height)),
                "d": (0, int(height)),
            },
            padding_units=1,
        )
        vertices = [points["a"], points["b"], points["c"], points["d"]]
        draw_polygon_outline(
            draw,
            vertices=[scale_point(point, int(context.scene_scale)) for point in vertices],
            line_width=max(1, int(line_width) * int(context.scene_scale)),
            line_color=tuple(int(value) for value in shape_style.line_color),
        )
        draw.line(
            [scale_point(points["a"], int(context.scene_scale)), scale_point(points["c"], int(context.scene_scale))],
            fill=tuple(int(value) for value in shape_style.line_color),
            width=max(1, int(helper_line_width) * int(context.scene_scale)),
        )
        segments = _polygon_segments(vertices) + [
            ((float(points["a"][0]), float(points["a"][1])), (float(points["c"][0]), float(points["c"][1])))
        ]
        centroid = _polygon_centroid(vertices)
        annotations = [
            _edge_annotation(
                ann_id="s",
                text=f"s={int(known_side)}",
                point_a=points["a"],
                point_b=points["b"],
                centroid=centroid,
            ),
            _segment_annotation(
                ann_id="d",
                text=f"d={int(hyp)}",
                point_a=points["a"],
                point_b=points["c"],
            ),
        ]
        evidence_values = {"s": int(known_side), "d": int(hyp)}
        centers, evidence_annotations = _draw_case_annotations(
            draw,
            rng=rng,
            annotations=annotations,
            evidence_label_values=evidence_values,
            blocked_segments=segments,
            extra_points=vertices,
            context=context,
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(context.scene_scale)),
        )
        return _CaseArtifacts(
            shape_variant="rectangle",
            reasoning_mode="derived",
            case_id="rectangle_derived",
            question_key="question_text_rectangle_derived",
            answer_type="integer",
            answer_scalar=int(area),
            answer_value=int(area),
            formula_expression="A = s * sqrt(d^2 - s^2)",
            evidence_ids=("s", "d"),
            evidence_label_values=dict(evidence_values),
            evidence_annotations=dict(evidence_annotations),
            annotation_centers=dict(centers),
            entity=_polygon_entity(
                entity_type="rectangle",
                vertices=vertices,
                attrs={
                    "shape_variant": "rectangle",
                    "reasoning_mode": "derived",
                    "known_side_units": int(known_side),
                    "inferred_side_units": int(other_side),
                    "diagonal_units": int(hyp),
                    "area_square_units": int(area),
                },
            ),
            render_anchor=_polygon_render_anchor(vertices),
        )
    raise ValueError("failed to sample rectangle derived case")


def _sample_triangle_explicit_case(
    rng,
    *,
    draw: ImageDraw.ImageDraw,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
    gen_defaults: Mapping[str, Any],
) -> _CaseArtifacts:
    """Sample one explicit right-triangle area case and render it."""
    unit_cap = _unit_cap(context)
    side_min = max(2, int(group_default(gen_defaults, "side_min", _DEFAULTS.side_min)))
    side_max = max(side_min, int(group_default(gen_defaults, "side_max", _DEFAULTS.side_max)))
    side_max = min(int(side_max), int(unit_cap))
    if int(side_min) > int(side_max):
        raise ValueError("no feasible triangle side range for current graph context")
    for _ in range(180):
        base = int(rng.randint(int(side_min), int(side_max)))
        height = int(rng.randint(int(side_min), int(side_max)))
        if int(base * height) % 2 != 0:
            continue
        area = int((int(base) * int(height)) // 2)
        if int(area) < int(answer_min) or int(area) > int(answer_max):
            continue
        points = _place_points_on_lattice(
            rng,
            context=context,
            unit_points={
                "a": (0, 0),
                "b": (int(base), 0),
                "c": (0, int(height)),
            },
            padding_units=1,
        )
        vertices = [points["a"], points["b"], points["c"]]
        draw_polygon_outline(
            draw,
            vertices=[scale_point(point, int(context.scene_scale)) for point in vertices],
            line_width=max(1, int(line_width) * int(context.scene_scale)),
            line_color=tuple(int(value) for value in shape_style.line_color),
        )
        segments = _polygon_segments(vertices)
        centroid = _polygon_centroid(vertices)
        annotations = [
            _edge_annotation(
                ann_id="b",
                text=f"b={int(base)}",
                point_a=points["a"],
                point_b=points["b"],
                centroid=centroid,
            ),
            _edge_annotation(
                ann_id="h",
                text=f"h={int(height)}",
                point_a=points["a"],
                point_b=points["c"],
                centroid=centroid,
            ),
        ]
        evidence_values = {"b": int(base), "h": int(height)}
        centers, evidence_annotations = _draw_case_annotations(
            draw,
            rng=rng,
            annotations=annotations,
            evidence_label_values=evidence_values,
            blocked_segments=segments,
            extra_points=vertices,
            context=context,
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(context.scene_scale)),
        )
        return _CaseArtifacts(
            shape_variant="triangle",
            reasoning_mode="explicit",
            case_id="triangle_explicit",
            question_key="question_text_triangle_explicit",
            answer_type="integer",
            answer_scalar=int(area),
            answer_value=int(area),
            formula_expression="A = (b * h) / 2",
            evidence_ids=("b", "h"),
            evidence_label_values=dict(evidence_values),
            evidence_annotations=dict(evidence_annotations),
            annotation_centers=dict(centers),
            entity=_polygon_entity(
                entity_type="triangle",
                vertices=vertices,
                attrs={
                    "shape_variant": "triangle",
                    "reasoning_mode": "explicit",
                    "base_units": int(base),
                    "height_units": int(height),
                    "area_square_units": int(area),
                },
            ),
            render_anchor=_polygon_render_anchor(vertices),
        )
    raise ValueError("failed to sample triangle explicit case")


def _sample_triangle_derived_case(
    rng,
    *,
    draw: ImageDraw.ImageDraw,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
    gen_defaults: Mapping[str, Any],
) -> _CaseArtifacts:
    """Sample one right-triangle leg+hypotenuse derived-area case and render it."""
    unit_cap = _unit_cap(context)
    max_component = int(group_default(gen_defaults, "right_triangle_max_component", _DEFAULTS.right_triangle_max_component))
    triplets = [
        (int(a), int(b), int(c))
        for a, b, c in _right_triangle_triplets(max_component)
        if int(a) <= int(unit_cap) and int(b) <= int(unit_cap)
    ]
    if not triplets:
        raise ValueError("no feasible right-triangle triplets for triangle derived case")
    for _ in range(200):
        leg_a, leg_b, hyp = triplets[int(rng.randrange(len(triplets)))]
        known_leg = int(leg_a if bool(rng.randrange(2)) else leg_b)
        other_leg = int(leg_b if int(known_leg) == int(leg_a) else leg_a)
        product = int(known_leg * other_leg)
        if int(product) % 2 != 0:
            continue
        area = int(product // 2)
        if int(area) < int(answer_min) or int(area) > int(answer_max):
            continue
        points = _place_points_on_lattice(
            rng,
            context=context,
            unit_points={
                "a": (0, 0),
                "b": (int(known_leg), 0),
                "c": (0, int(other_leg)),
            },
            padding_units=1,
        )
        vertices = [points["a"], points["b"], points["c"]]
        draw_polygon_outline(
            draw,
            vertices=[scale_point(point, int(context.scene_scale)) for point in vertices],
            line_width=max(1, int(line_width) * int(context.scene_scale)),
            line_color=tuple(int(value) for value in shape_style.line_color),
        )
        segments = _polygon_segments(vertices)
        centroid = _polygon_centroid(vertices)
        annotations = [
            _edge_annotation(
                ann_id="leg",
                text=f"leg={int(known_leg)}",
                point_a=points["a"],
                point_b=points["b"],
                centroid=centroid,
            ),
            _edge_annotation(
                ann_id="hyp",
                text=f"hyp={int(hyp)}",
                point_a=points["b"],
                point_b=points["c"],
                centroid=centroid,
            ),
        ]
        evidence_values = {"leg": int(known_leg), "hyp": int(hyp)}
        centers, evidence_annotations = _draw_case_annotations(
            draw,
            rng=rng,
            annotations=annotations,
            evidence_label_values=evidence_values,
            blocked_segments=segments,
            extra_points=vertices,
            context=context,
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(context.scene_scale)),
        )
        return _CaseArtifacts(
            shape_variant="triangle",
            reasoning_mode="derived",
            case_id="triangle_derived",
            question_key="question_text_triangle_derived",
            answer_type="integer",
            answer_scalar=int(area),
            answer_value=int(area),
            formula_expression="A = (leg * sqrt(hyp^2 - leg^2)) / 2",
            evidence_ids=("leg", "hyp"),
            evidence_label_values=dict(evidence_values),
            evidence_annotations=dict(evidence_annotations),
            annotation_centers=dict(centers),
            entity=_polygon_entity(
                entity_type="triangle",
                vertices=vertices,
                attrs={
                    "shape_variant": "triangle",
                    "reasoning_mode": "derived",
                    "known_leg_units": int(known_leg),
                    "inferred_leg_units": int(other_leg),
                    "hypotenuse_units": int(hyp),
                    "area_square_units": int(area),
                },
            ),
            render_anchor=_polygon_render_anchor(vertices),
        )
    raise ValueError("failed to sample triangle derived case")


def _sample_parallelogram_explicit_case(
    rng,
    *,
    draw: ImageDraw.ImageDraw,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
    gen_defaults: Mapping[str, Any],
) -> _CaseArtifacts:
    """Sample one explicit parallelogram area case and render it."""
    unit_cap = _unit_cap(context)
    side_min = max(2, int(group_default(gen_defaults, "side_min", _DEFAULTS.side_min)))
    side_max = max(side_min, int(group_default(gen_defaults, "side_max", _DEFAULTS.side_max)))
    side_max = min(int(side_max), int(unit_cap))
    if int(side_min) > int(side_max):
        raise ValueError("no feasible parallelogram side range for current graph context")
    for _ in range(200):
        base = int(rng.randint(int(side_min), int(side_max)))
        height = int(rng.randint(int(side_min), int(side_max)))
        offset_max = max(1, min(4, int(unit_cap) - int(base)))
        if int(offset_max) <= 0:
            continue
        offset = int(rng.randint(1, int(offset_max)))
        area = int(base * height)
        if int(area) < int(answer_min) or int(area) > int(answer_max):
            continue
        points = _place_points_on_lattice(
            rng,
            context=context,
            unit_points={
                "a": (0, 0),
                "b": (int(base), 0),
                "c": (int(base + offset), int(height)),
                "d": (int(offset), int(height)),
                "dp": (int(offset), 0),
            },
            padding_units=1,
        )
        vertices = [points["a"], points["b"], points["c"], points["d"]]
        draw_polygon_outline(
            draw,
            vertices=[scale_point(point, int(context.scene_scale)) for point in vertices],
            line_width=max(1, int(line_width) * int(context.scene_scale)),
            line_color=tuple(int(value) for value in shape_style.line_color),
        )
        draw.line(
            [scale_point(points["d"], int(context.scene_scale)), scale_point(points["dp"], int(context.scene_scale))],
            fill=tuple(int(value) for value in shape_style.line_color),
            width=max(1, int(helper_line_width) * int(context.scene_scale)),
        )
        segments = _polygon_segments(vertices) + [
            ((float(points["d"][0]), float(points["d"][1])), (float(points["dp"][0]), float(points["dp"][1])))
        ]
        centroid = _polygon_centroid(vertices)
        annotations = [
            _edge_annotation(
                ann_id="b",
                text=f"b={int(base)}",
                point_a=points["a"],
                point_b=points["b"],
                centroid=centroid,
            ),
            _segment_annotation(
                ann_id="h",
                text=f"h={int(height)}",
                point_a=points["d"],
                point_b=points["dp"],
                direction=(-1.0, 0.0),
            ),
        ]
        evidence_values = {"b": int(base), "h": int(height)}
        centers, evidence_annotations = _draw_case_annotations(
            draw,
            rng=rng,
            annotations=annotations,
            evidence_label_values=evidence_values,
            blocked_segments=segments,
            extra_points=vertices,
            context=context,
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(context.scene_scale)),
        )
        return _CaseArtifacts(
            shape_variant="parallelogram",
            reasoning_mode="explicit",
            case_id="parallelogram_explicit",
            question_key="question_text_parallelogram_explicit",
            answer_type="integer",
            answer_scalar=int(area),
            answer_value=int(area),
            formula_expression="A = b * h",
            evidence_ids=("b", "h"),
            evidence_label_values=dict(evidence_values),
            evidence_annotations=dict(evidence_annotations),
            annotation_centers=dict(centers),
            entity=_polygon_entity(
                entity_type="parallelogram",
                vertices=vertices,
                attrs={
                    "shape_variant": "parallelogram",
                    "reasoning_mode": "explicit",
                    "base_units": int(base),
                    "height_units": int(height),
                    "horizontal_offset_units": int(offset),
                    "area_square_units": int(area),
                },
            ),
            render_anchor=_polygon_render_anchor(vertices),
        )
    raise ValueError("failed to sample parallelogram explicit case")


def _sample_parallelogram_derived_case(
    rng,
    *,
    draw: ImageDraw.ImageDraw,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
    gen_defaults: Mapping[str, Any],
) -> _CaseArtifacts:
    """Sample one derived parallelogram area case and render it."""
    unit_cap = _unit_cap(context)
    max_component = int(group_default(gen_defaults, "right_triangle_max_component", _DEFAULTS.right_triangle_max_component))
    triplets = [
        (int(a), int(b), int(c))
        for a, b, c in _right_triangle_triplets(max_component)
        if int(a) >= 1 and int(b) >= 1 and int(c) >= 2
    ]
    side_min = max(2, int(group_default(gen_defaults, "side_min", _DEFAULTS.side_min)))
    side_max = max(side_min, int(group_default(gen_defaults, "side_max", _DEFAULTS.side_max)))
    side_max = min(int(side_max), int(unit_cap))
    if not triplets or int(side_min) > int(side_max):
        raise ValueError("no feasible parameters for parallelogram derived case")
    for _ in range(240):
        offset, height, side_len = triplets[int(rng.randrange(len(triplets)))]
        if int(offset) > 5:
            continue
        if int(height) > int(unit_cap):
            continue
        base_max = int(unit_cap) - int(offset)
        if int(base_max) < int(side_min):
            continue
        base = int(rng.randint(int(side_min), int(min(int(side_max), int(base_max)))))
        area = int(base * height)
        if int(area) < int(answer_min) or int(area) > int(answer_max):
            continue
        points = _place_points_on_lattice(
            rng,
            context=context,
            unit_points={
                "a": (0, 0),
                "b": (int(base), 0),
                "c": (int(base + offset), int(height)),
                "d": (int(offset), int(height)),
                "dp": (int(offset), 0),
            },
            padding_units=1,
        )
        vertices = [points["a"], points["b"], points["c"], points["d"]]
        draw_polygon_outline(
            draw,
            vertices=[scale_point(point, int(context.scene_scale)) for point in vertices],
            line_width=max(1, int(line_width) * int(context.scene_scale)),
            line_color=tuple(int(value) for value in shape_style.line_color),
        )
        draw.line(
            [scale_point(points["a"], int(context.scene_scale)), scale_point(points["dp"], int(context.scene_scale))],
            fill=tuple(int(value) for value in shape_style.line_color),
            width=max(1, int(helper_line_width) * int(context.scene_scale)),
        )
        segments = _polygon_segments(vertices) + [
            ((float(points["a"][0]), float(points["a"][1])), (float(points["dp"][0]), float(points["dp"][1])))
        ]
        centroid = _polygon_centroid(vertices)
        annotations = [
            _edge_annotation(
                ann_id="b",
                text=f"b={int(base)}",
                point_a=points["a"],
                point_b=points["b"],
                centroid=centroid,
            ),
            _edge_annotation(
                ann_id="s",
                text=f"s={int(side_len)}",
                point_a=points["a"],
                point_b=points["d"],
                centroid=centroid,
            ),
            _segment_annotation(
                ann_id="o",
                text=f"o={int(offset)}",
                point_a=points["a"],
                point_b=points["dp"],
                direction=(0.0, -1.0),
            ),
        ]
        evidence_values = {"b": int(base), "s": int(side_len), "o": int(offset)}
        centers, evidence_annotations = _draw_case_annotations(
            draw,
            rng=rng,
            annotations=annotations,
            evidence_label_values=evidence_values,
            blocked_segments=segments,
            extra_points=vertices,
            context=context,
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(context.scene_scale)),
        )
        return _CaseArtifacts(
            shape_variant="parallelogram",
            reasoning_mode="derived",
            case_id="parallelogram_derived",
            question_key="question_text_parallelogram_derived",
            answer_type="integer",
            answer_scalar=int(area),
            answer_value=int(area),
            formula_expression="A = b * sqrt(s^2 - o^2)",
            evidence_ids=("b", "s", "o"),
            evidence_label_values=dict(evidence_values),
            evidence_annotations=dict(evidence_annotations),
            annotation_centers=dict(centers),
            entity=_polygon_entity(
                entity_type="parallelogram",
                vertices=vertices,
                attrs={
                    "shape_variant": "parallelogram",
                    "reasoning_mode": "derived",
                    "base_units": int(base),
                    "side_units": int(side_len),
                    "offset_units": int(offset),
                    "inferred_height_units": int(height),
                    "area_square_units": int(area),
                },
            ),
            render_anchor=_polygon_render_anchor(vertices),
        )
    raise ValueError("failed to sample parallelogram derived case")


def _sample_trapezoid_explicit_case(
    rng,
    *,
    draw: ImageDraw.ImageDraw,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
    gen_defaults: Mapping[str, Any],
) -> _CaseArtifacts:
    """Sample one explicit trapezoid area case and render it."""
    unit_cap = _unit_cap(context)
    side_min = max(2, int(group_default(gen_defaults, "side_min", _DEFAULTS.side_min)))
    side_max = max(side_min, int(group_default(gen_defaults, "side_max", _DEFAULTS.side_max)))
    side_max = min(int(side_max), int(unit_cap))
    if int(side_min) > int(side_max):
        raise ValueError("no feasible trapezoid side range for current graph context")
    for _ in range(240):
        half_diff = int(rng.randint(1, max(1, int(unit_cap // 3))))
        base_2_max = int(unit_cap) - (2 * int(half_diff))
        if int(base_2_max) < int(side_min):
            continue
        base_2 = int(rng.randint(int(side_min), int(min(int(side_max), int(base_2_max)))))
        base_1 = int(base_2 + (2 * int(half_diff)))
        height = int(rng.randint(int(side_min), int(side_max)))
        numerator = int((int(base_1) + int(base_2)) * int(height))
        if int(numerator) % 2 != 0:
            continue
        area = int(numerator // 2)
        if int(area) < int(answer_min) or int(area) > int(answer_max):
            continue
        points = _place_points_on_lattice(
            rng,
            context=context,
            unit_points={
                "a": (0, 0),
                "b": (int(base_1), 0),
                "c": (int(base_1 - half_diff), int(height)),
                "d": (int(half_diff), int(height)),
                "dp": (int(half_diff), 0),
            },
            padding_units=1,
        )
        vertices = [points["a"], points["b"], points["c"], points["d"]]
        draw_polygon_outline(
            draw,
            vertices=[scale_point(point, int(context.scene_scale)) for point in vertices],
            line_width=max(1, int(line_width) * int(context.scene_scale)),
            line_color=tuple(int(value) for value in shape_style.line_color),
        )
        draw.line(
            [scale_point(points["d"], int(context.scene_scale)), scale_point(points["dp"], int(context.scene_scale))],
            fill=tuple(int(value) for value in shape_style.line_color),
            width=max(1, int(helper_line_width) * int(context.scene_scale)),
        )
        segments = _polygon_segments(vertices) + [
            ((float(points["d"][0]), float(points["d"][1])), (float(points["dp"][0]), float(points["dp"][1])))
        ]
        centroid = _polygon_centroid(vertices)
        annotations = [
            _edge_annotation(
                ann_id="b1",
                text=f"b1={int(base_1)}",
                point_a=points["a"],
                point_b=points["b"],
                centroid=centroid,
            ),
            _edge_annotation(
                ann_id="b2",
                text=f"b2={int(base_2)}",
                point_a=points["d"],
                point_b=points["c"],
                centroid=centroid,
            ),
            _segment_annotation(
                ann_id="h",
                text=f"h={int(height)}",
                point_a=points["d"],
                point_b=points["dp"],
                direction=(-1.0, 0.0),
            ),
        ]
        evidence_values = {"b1": int(base_1), "b2": int(base_2), "h": int(height)}
        centers, evidence_annotations = _draw_case_annotations(
            draw,
            rng=rng,
            annotations=annotations,
            evidence_label_values=evidence_values,
            blocked_segments=segments,
            extra_points=vertices,
            context=context,
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(context.scene_scale)),
        )
        return _CaseArtifacts(
            shape_variant="trapezoid",
            reasoning_mode="explicit",
            case_id="trapezoid_explicit",
            question_key="question_text_trapezoid_explicit",
            answer_type="integer",
            answer_scalar=int(area),
            answer_value=int(area),
            formula_expression="A = ((b1 + b2) * h) / 2",
            evidence_ids=("b1", "b2", "h"),
            evidence_label_values=dict(evidence_values),
            evidence_annotations=dict(evidence_annotations),
            annotation_centers=dict(centers),
            entity=_polygon_entity(
                entity_type="trapezoid",
                vertices=vertices,
                attrs={
                    "shape_variant": "trapezoid",
                    "reasoning_mode": "explicit",
                    "base1_units": int(base_1),
                    "base2_units": int(base_2),
                    "height_units": int(height),
                    "half_base_difference_units": int(half_diff),
                    "area_square_units": int(area),
                },
            ),
            render_anchor=_polygon_render_anchor(vertices),
        )
    raise ValueError("failed to sample trapezoid explicit case")


def _sample_trapezoid_derived_case(
    rng,
    *,
    draw: ImageDraw.ImageDraw,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
    gen_defaults: Mapping[str, Any],
) -> _CaseArtifacts:
    """Sample one derived trapezoid area case and render it."""
    unit_cap = _unit_cap(context)
    max_component = int(group_default(gen_defaults, "right_triangle_max_component", _DEFAULTS.right_triangle_max_component))
    triplets = [
        (int(a), int(b), int(c))
        for a, b, c in _right_triangle_triplets(max_component)
        if int(a) >= 1 and int(b) >= 1 and int(c) >= 2
    ]
    side_min = max(2, int(group_default(gen_defaults, "side_min", _DEFAULTS.side_min)))
    side_max = max(side_min, int(group_default(gen_defaults, "side_max", _DEFAULTS.side_max)))
    side_max = min(int(side_max), int(unit_cap))
    if not triplets or int(side_min) > int(side_max):
        raise ValueError("no feasible parameters for trapezoid derived case")
    for _ in range(260):
        half_diff, height, leg = triplets[int(rng.randrange(len(triplets)))]
        if int(half_diff) > 5:
            continue
        base_2_max = int(unit_cap) - (2 * int(half_diff))
        if int(base_2_max) < int(side_min):
            continue
        base_2 = int(rng.randint(int(side_min), int(min(int(side_max), int(base_2_max)))))
        base_1 = int(base_2 + (2 * int(half_diff)))
        numerator = int((int(base_1) + int(base_2)) * int(height))
        if int(numerator) % 2 != 0:
            continue
        area = int(numerator // 2)
        if int(area) < int(answer_min) or int(area) > int(answer_max):
            continue
        points = _place_points_on_lattice(
            rng,
            context=context,
            unit_points={
                "a": (0, 0),
                "b": (int(base_1), 0),
                "c": (int(base_1 - half_diff), int(height)),
                "d": (int(half_diff), int(height)),
            },
            padding_units=1,
        )
        vertices = [points["a"], points["b"], points["c"], points["d"]]
        draw_polygon_outline(
            draw,
            vertices=[scale_point(point, int(context.scene_scale)) for point in vertices],
            line_width=max(1, int(line_width) * int(context.scene_scale)),
            line_color=tuple(int(value) for value in shape_style.line_color),
        )
        segments = _polygon_segments(vertices)
        centroid = _polygon_centroid(vertices)
        annotations = [
            _edge_annotation(
                ann_id="b1",
                text=f"b1={int(base_1)}",
                point_a=points["a"],
                point_b=points["b"],
                centroid=centroid,
            ),
            _edge_annotation(
                ann_id="b2",
                text=f"b2={int(base_2)}",
                point_a=points["d"],
                point_b=points["c"],
                centroid=centroid,
            ),
            _edge_annotation(
                ann_id="leg",
                text=f"leg={int(leg)}",
                point_a=points["a"],
                point_b=points["d"],
                centroid=centroid,
            ),
        ]
        evidence_values = {"b1": int(base_1), "b2": int(base_2), "leg": int(leg)}
        centers, evidence_annotations = _draw_case_annotations(
            draw,
            rng=rng,
            annotations=annotations,
            evidence_label_values=evidence_values,
            blocked_segments=segments,
            extra_points=vertices,
            context=context,
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(context.scene_scale)),
        )
        return _CaseArtifacts(
            shape_variant="trapezoid",
            reasoning_mode="derived",
            case_id="trapezoid_derived",
            question_key="question_text_trapezoid_derived",
            answer_type="integer",
            answer_scalar=int(area),
            answer_value=int(area),
            formula_expression="A = ((b1 + b2) * sqrt(leg^2 - ((b1-b2)/2)^2)) / 2",
            evidence_ids=("b1", "b2", "leg"),
            evidence_label_values=dict(evidence_values),
            evidence_annotations=dict(evidence_annotations),
            annotation_centers=dict(centers),
            entity=_polygon_entity(
                entity_type="trapezoid",
                vertices=vertices,
                attrs={
                    "shape_variant": "trapezoid",
                    "reasoning_mode": "derived",
                    "base1_units": int(base_1),
                    "base2_units": int(base_2),
                    "leg_units": int(leg),
                    "inferred_height_units": int(height),
                    "half_base_difference_units": int(half_diff),
                    "area_square_units": int(area),
                },
            ),
            render_anchor=_polygon_render_anchor(vertices),
        )
    raise ValueError("failed to sample trapezoid derived case")


def _sample_rhombus_explicit_case(
    rng,
    *,
    draw: ImageDraw.ImageDraw,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
) -> _CaseArtifacts:
    """Sample one explicit rhombus area case and render it."""
    unit_cap = _unit_cap(context)
    half_cap = max(1, int(unit_cap // 2))
    for _ in range(220):
        half_d1 = int(rng.randint(1, int(half_cap)))
        half_d2 = int(rng.randint(1, int(half_cap)))
        area = int(2 * int(half_d1) * int(half_d2))
        if int(area) < int(answer_min) or int(area) > int(answer_max):
            continue
        points = _place_points_on_lattice(
            rng,
            context=context,
            unit_points={
                "a": (-int(half_d1), 0),
                "b": (0, int(half_d2)),
                "c": (int(half_d1), 0),
                "d": (0, -int(half_d2)),
                "o": (0, 0),
            },
            padding_units=1,
        )
        vertices = [points["a"], points["b"], points["c"], points["d"]]
        draw_polygon_outline(
            draw,
            vertices=[scale_point(point, int(context.scene_scale)) for point in vertices],
            line_width=max(1, int(line_width) * int(context.scene_scale)),
            line_color=tuple(int(value) for value in shape_style.line_color),
        )
        draw.line(
            [scale_point(points["a"], int(context.scene_scale)), scale_point(points["c"], int(context.scene_scale))],
            fill=tuple(int(value) for value in shape_style.line_color),
            width=max(1, int(helper_line_width) * int(context.scene_scale)),
        )
        draw.line(
            [scale_point(points["b"], int(context.scene_scale)), scale_point(points["d"], int(context.scene_scale))],
            fill=tuple(int(value) for value in shape_style.line_color),
            width=max(1, int(helper_line_width) * int(context.scene_scale)),
        )
        segments = _polygon_segments(vertices) + [
            ((float(points["a"][0]), float(points["a"][1])), (float(points["c"][0]), float(points["c"][1]))),
            ((float(points["b"][0]), float(points["b"][1])), (float(points["d"][0]), float(points["d"][1]))),
        ]
        annotations = [
            _segment_annotation(
                ann_id="d1",
                text=f"d1={int(2 * half_d1)}",
                point_a=points["a"],
                point_b=points["c"],
                direction=(1.0, 0.0),
                anchor_fraction=0.64,
                offset_scale=1.55,
            ),
            _segment_annotation(
                ann_id="d2",
                text=f"d2={int(2 * half_d2)}",
                point_a=points["b"],
                point_b=points["d"],
                direction=(0.0, -1.0),
                anchor_fraction=0.42,
                offset_scale=1.25,
            ),
        ]
        evidence_values = {"d1": int(2 * half_d1), "d2": int(2 * half_d2)}
        center_x, center_y = float(points["o"][0]), float(points["o"][1])
        span_x = abs(float(points["c"][0]) - float(points["o"][0]))
        span_y = abs(float(points["o"][1]) - float(points["b"][1]))
        fixed_centers = {
            "d1": (
                float(center_x + (0.50 * span_x)),
                float(center_y + (0.12 * span_y)),
            ),
            "d2": (
                float(center_x + (0.12 * span_x)),
                float(center_y - (0.50 * span_y)),
            ),
        }
        centers, evidence_annotations = _draw_case_annotations(
            draw,
            rng=rng,
            annotations=annotations,
            evidence_label_values=evidence_values,
            blocked_segments=segments,
            fixed_centers=fixed_centers,
            extra_points=vertices,
            context=context,
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(context.scene_scale)),
        )
        d1 = int(2 * int(half_d1))
        d2 = int(2 * int(half_d2))
        return _CaseArtifacts(
            shape_variant="rhombus",
            reasoning_mode="explicit",
            case_id="rhombus_explicit",
            question_key="question_text_rhombus_explicit",
            answer_type="integer",
            answer_scalar=int(area),
            answer_value=int(area),
            formula_expression="A = (d1 * d2) / 2",
            evidence_ids=("d1", "d2"),
            evidence_label_values={"d1": int(d1), "d2": int(d2)},
            evidence_annotations=dict(evidence_annotations),
            annotation_centers=dict(centers),
            entity=_polygon_entity(
                entity_type="rhombus",
                vertices=vertices,
                attrs={
                    "shape_variant": "rhombus",
                    "reasoning_mode": "explicit",
                    "diagonal1_units": int(d1),
                    "diagonal2_units": int(d2),
                    "area_square_units": int(area),
                },
            ),
            render_anchor=_polygon_render_anchor(vertices),
        )
    raise ValueError("failed to sample rhombus explicit case")


def _sample_rhombus_derived_case(
    rng,
    *,
    draw: ImageDraw.ImageDraw,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
    gen_defaults: Mapping[str, Any],
) -> _CaseArtifacts:
    """Sample one rhombus side+diagonal derived-area case and render it."""
    unit_cap = _unit_cap(context)
    max_component = int(group_default(gen_defaults, "right_triangle_max_component", _DEFAULTS.right_triangle_max_component))
    triplets = [
        (int(a), int(b), int(c))
        for a, b, c in _right_triangle_triplets(max_component)
        if int(a) >= 1 and int(b) >= 1 and int(c) >= 2
    ]
    if not triplets:
        raise ValueError("no feasible triplets for rhombus derived case")
    for _ in range(260):
        half_d1, half_d2, side_len = triplets[int(rng.randrange(len(triplets)))]
        if int(half_d1) > int(unit_cap // 2) or int(half_d2) > int(unit_cap // 2):
            continue
        area = int(2 * int(half_d1) * int(half_d2))
        if int(area) < int(answer_min) or int(area) > int(answer_max):
            continue
        points = _place_points_on_lattice(
            rng,
            context=context,
            unit_points={
                "a": (-int(half_d1), 0),
                "b": (0, int(half_d2)),
                "c": (int(half_d1), 0),
                "d": (0, -int(half_d2)),
            },
            padding_units=1,
        )
        vertices = [points["a"], points["b"], points["c"], points["d"]]
        draw_polygon_outline(
            draw,
            vertices=[scale_point(point, int(context.scene_scale)) for point in vertices],
            line_width=max(1, int(line_width) * int(context.scene_scale)),
            line_color=tuple(int(value) for value in shape_style.line_color),
        )
        draw.line(
            [scale_point(points["a"], int(context.scene_scale)), scale_point(points["c"], int(context.scene_scale))],
            fill=tuple(int(value) for value in shape_style.line_color),
            width=max(1, int(helper_line_width) * int(context.scene_scale)),
        )
        segments = _polygon_segments(vertices) + [
            ((float(points["a"][0]), float(points["a"][1])), (float(points["c"][0]), float(points["c"][1])))
        ]
        centroid = _polygon_centroid(vertices)
        d1 = int(2 * int(half_d1))
        annotations = [
            _edge_annotation(
                ann_id="s",
                text=f"s={int(side_len)}",
                point_a=points["a"],
                point_b=points["b"],
                centroid=centroid,
            ),
            _segment_annotation(
                ann_id="d1",
                text=f"d1={int(d1)}",
                point_a=points["a"],
                point_b=points["c"],
                direction=(0.0, -1.0),
            ),
        ]
        evidence_values = {"s": int(side_len), "d1": int(d1)}
        centers, evidence_annotations = _draw_case_annotations(
            draw,
            rng=rng,
            annotations=annotations,
            evidence_label_values=evidence_values,
            blocked_segments=segments,
            extra_points=vertices,
            context=context,
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(context.scene_scale)),
        )
        return _CaseArtifacts(
            shape_variant="rhombus",
            reasoning_mode="derived",
            case_id="rhombus_derived",
            question_key="question_text_rhombus_derived",
            answer_type="integer",
            answer_scalar=int(area),
            answer_value=int(area),
            formula_expression="A = (d1 * sqrt(4*s^2 - d1^2)) / 2",
            evidence_ids=("s", "d1"),
            evidence_label_values=dict(evidence_values),
            evidence_annotations=dict(evidence_annotations),
            annotation_centers=dict(centers),
            entity=_polygon_entity(
                entity_type="rhombus",
                vertices=vertices,
                attrs={
                    "shape_variant": "rhombus",
                    "reasoning_mode": "derived",
                    "side_units": int(side_len),
                    "diagonal1_units": int(d1),
                    "inferred_diagonal2_units": int(2 * int(half_d2)),
                    "area_square_units": int(area),
                },
            ),
            render_anchor=_polygon_render_anchor(vertices),
        )
    raise ValueError("failed to sample rhombus derived case")


def _sample_circle_explicit_case(
    rng,
    *,
    draw: ImageDraw.ImageDraw,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
    gen_defaults: Mapping[str, Any],
) -> _CaseArtifacts:
    """Sample one explicit circle area case and render it."""
    radius_min = max(1, int(group_default(gen_defaults, "circle_radius_min", 2)))
    radius_max = max(radius_min, int(group_default(gen_defaults, "circle_radius_max", 10)))
    radius_max = min(int(radius_max), max(1, int(_unit_cap(context) // 2)))
    if int(radius_min) > int(radius_max):
        raise ValueError("no feasible circle radius range for current graph context")
    for _ in range(180):
        spacing_px = int(_analytical_unit_spacing_px(context))
        radius = int(rng.randint(int(radius_min), int(radius_max)))
        area_coeff = int(radius * radius)
        if int(area_coeff) < int(answer_min) or int(area_coeff) > int(answer_max):
            continue
        instance = sample_circle_instance_on_graph_paper(
            rng,
            canvas_size=int(context.canvas_size),
            graph_spacing=int(spacing_px),
            graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
            radii=[int(radius)],
            padding_units=1,
            max_attempts=32,
        )
        center = (float(instance.center[0]), float(instance.center[1]))
        radius_point = offset_point_by_grid_vector(center, (int(radius), 0), spacing=int(spacing_px))
        draw_circle_outline(
            draw,
            center=scale_point(center, int(context.scene_scale)),
            radius_px=int(instance.radius_units) * int(spacing_px) * int(context.scene_scale),
            line_width=max(1, int(line_width) * int(context.scene_scale)),
            line_color=tuple(int(value) for value in shape_style.line_color),
        )
        draw.line(
            [scale_point(center, int(context.scene_scale)), scale_point(radius_point, int(context.scene_scale))],
            fill=tuple(int(value) for value in shape_style.line_color),
            width=max(1, int(helper_line_width) * int(context.scene_scale)),
        )
        segments = [((float(center[0]), float(center[1])), (float(radius_point[0]), float(radius_point[1])))]
        annotations = [
            _segment_annotation(
                ann_id="r",
                text=f"r={int(radius)}",
                point_a=center,
                point_b=radius_point,
                direction=(0.0, -1.0),
            )
        ]
        evidence_values = {"r": int(radius)}
        centers, evidence_annotations = _draw_case_annotations(
            draw,
            rng=rng,
            annotations=annotations,
            evidence_label_values=evidence_values,
            blocked_segments=segments,
            context=context,
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(context.scene_scale)),
        )
        return _CaseArtifacts(
            shape_variant="circle",
            reasoning_mode="explicit",
            case_id="circle_explicit",
            question_key="question_text_circle_explicit",
            answer_type="pi_expression",
            answer_scalar=int(area_coeff),
            answer_value=_pi_expression(int(area_coeff)),
            formula_expression="A = π * r^2",
            evidence_ids=("r",),
            evidence_label_values=dict(evidence_values),
            evidence_annotations=dict(evidence_annotations),
            annotation_centers=dict(centers),
            entity={
                "entity_id": "shape_1",
                "entity_type": "circle",
                "attrs": {
                    "shape_variant": "circle",
                    "reasoning_mode": "explicit",
                    "center": [float(center[0]), float(center[1])],
                    "radius_units": int(radius),
                    "area_pi_coefficient": int(area_coeff),
                },
            },
            render_anchor=conic_render_anchor(
                center=center,
                semi_axis_x_px=int(radius) * int(spacing_px),
                semi_axis_y_px=int(radius) * int(spacing_px),
            ),
        )
    raise ValueError("failed to sample circle explicit case")


def _sample_circle_derived_case(
    rng,
    *,
    draw: ImageDraw.ImageDraw,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
    gen_defaults: Mapping[str, Any],
) -> _CaseArtifacts:
    """Sample one circle diameter-derived area case and render it."""
    radius_min = max(1, int(group_default(gen_defaults, "circle_radius_min", 2)))
    radius_max = max(radius_min, int(group_default(gen_defaults, "circle_radius_max", 10)))
    radius_max = min(int(radius_max), max(1, int(_unit_cap(context) // 2)))
    if int(radius_min) > int(radius_max):
        raise ValueError("no feasible circle radius range for current graph context")
    for _ in range(180):
        spacing_px = int(_analytical_unit_spacing_px(context))
        radius = int(rng.randint(int(radius_min), int(radius_max)))
        area_coeff = int(radius * radius)
        if int(area_coeff) < int(answer_min) or int(area_coeff) > int(answer_max):
            continue
        diameter = int(2 * int(radius))
        instance = sample_circle_instance_on_graph_paper(
            rng,
            canvas_size=int(context.canvas_size),
            graph_spacing=int(spacing_px),
            graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
            radii=[int(radius)],
            padding_units=1,
            max_attempts=32,
        )
        center = (float(instance.center[0]), float(instance.center[1]))
        left_point = offset_point_by_grid_vector(center, (-int(radius), 0), spacing=int(spacing_px))
        right_point = offset_point_by_grid_vector(center, (int(radius), 0), spacing=int(spacing_px))
        draw_circle_outline(
            draw,
            center=scale_point(center, int(context.scene_scale)),
            radius_px=int(instance.radius_units) * int(spacing_px) * int(context.scene_scale),
            line_width=max(1, int(line_width) * int(context.scene_scale)),
            line_color=tuple(int(value) for value in shape_style.line_color),
        )
        draw.line(
            [scale_point(left_point, int(context.scene_scale)), scale_point(right_point, int(context.scene_scale))],
            fill=tuple(int(value) for value in shape_style.line_color),
            width=max(1, int(helper_line_width) * int(context.scene_scale)),
        )
        segments = [((float(left_point[0]), float(left_point[1])), (float(right_point[0]), float(right_point[1])))]
        annotations = [
            _segment_annotation(
                ann_id="d",
                text=f"d={int(diameter)}",
                point_a=left_point,
                point_b=right_point,
                direction=(0.0, -1.0),
            )
        ]
        evidence_values = {"d": int(diameter)}
        centers, evidence_annotations = _draw_case_annotations(
            draw,
            rng=rng,
            annotations=annotations,
            evidence_label_values=evidence_values,
            blocked_segments=segments,
            context=context,
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(context.scene_scale)),
        )
        return _CaseArtifacts(
            shape_variant="circle",
            reasoning_mode="derived",
            case_id="circle_derived",
            question_key="question_text_circle_derived",
            answer_type="pi_expression",
            answer_scalar=int(area_coeff),
            answer_value=_pi_expression(int(area_coeff)),
            formula_expression="A = π * (d/2)^2",
            evidence_ids=("d",),
            evidence_label_values=dict(evidence_values),
            evidence_annotations=dict(evidence_annotations),
            annotation_centers=dict(centers),
            entity={
                "entity_id": "shape_1",
                "entity_type": "circle",
                "attrs": {
                    "shape_variant": "circle",
                    "reasoning_mode": "derived",
                    "center": [float(center[0]), float(center[1])],
                    "radius_units": int(radius),
                    "diameter_units": int(diameter),
                    "area_pi_coefficient": int(area_coeff),
                },
            },
            render_anchor=conic_render_anchor(
                center=center,
                semi_axis_x_px=int(radius) * int(spacing_px),
                semi_axis_y_px=int(radius) * int(spacing_px),
            ),
        )
    raise ValueError("failed to sample circle derived case")


def _sample_ellipse_explicit_case(
    rng,
    *,
    draw: ImageDraw.ImageDraw,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
    gen_defaults: Mapping[str, Any],
) -> _CaseArtifacts:
    """Sample one explicit ellipse area case and render it."""
    axis_min = max(1, int(group_default(gen_defaults, "ellipse_axis_min", 2)))
    axis_max = max(axis_min, int(group_default(gen_defaults, "ellipse_axis_max", 10)))
    axis_max = min(int(axis_max), max(1, int(_unit_cap(context) // 2)))
    if int(axis_min) > int(axis_max):
        raise ValueError("no feasible ellipse axis range for current graph context")
    for _ in range(220):
        spacing_px = int(_analytical_unit_spacing_px(context))
        semi_major = int(rng.randint(int(axis_min), int(axis_max)))
        semi_minor = int(rng.randint(int(axis_min), int(semi_major)))
        area_coeff = int(semi_major * semi_minor)
        if int(area_coeff) < int(answer_min) or int(area_coeff) > int(answer_max):
            continue
        instance = sample_ellipse_instance_on_graph_paper(
            rng,
            canvas_size=int(context.canvas_size),
            graph_spacing=int(spacing_px),
            graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
            axis_pairs=[(int(semi_major), int(semi_minor))],
            padding_units=1,
            max_attempts=32,
        )
        center = (float(instance.center[0]), float(instance.center[1]))
        axis_x_end = offset_point_by_grid_vector(center, (int(semi_major), 0), spacing=int(spacing_px))
        axis_y_end = offset_point_by_grid_vector(center, (0, int(semi_minor)), spacing=int(spacing_px))
        draw_ellipse_outline(
            draw,
            center=scale_point(center, int(context.scene_scale)),
            semi_axis_x_px=int(semi_major) * int(spacing_px) * int(context.scene_scale),
            semi_axis_y_px=int(semi_minor) * int(spacing_px) * int(context.scene_scale),
            line_width=max(1, int(line_width) * int(context.scene_scale)),
            line_color=tuple(int(value) for value in shape_style.line_color),
        )
        draw.line(
            [scale_point(center, int(context.scene_scale)), scale_point(axis_x_end, int(context.scene_scale))],
            fill=tuple(int(value) for value in shape_style.line_color),
            width=max(1, int(helper_line_width) * int(context.scene_scale)),
        )
        draw.line(
            [scale_point(center, int(context.scene_scale)), scale_point(axis_y_end, int(context.scene_scale))],
            fill=tuple(int(value) for value in shape_style.line_color),
            width=max(1, int(helper_line_width) * int(context.scene_scale)),
        )
        segments = [
            ((float(center[0]), float(center[1])), (float(axis_x_end[0]), float(axis_x_end[1]))),
            ((float(center[0]), float(center[1])), (float(axis_y_end[0]), float(axis_y_end[1]))),
        ]
        annotations = [
            _segment_annotation(
                ann_id="a",
                text=f"a={int(semi_major)}",
                point_a=center,
                point_b=axis_x_end,
                direction=(0.0, -1.0),
            ),
            _segment_annotation(
                ann_id="b",
                text=f"b={int(semi_minor)}",
                point_a=center,
                point_b=axis_y_end,
                direction=(1.0, 0.0),
            ),
        ]
        evidence_values = {"a": int(semi_major), "b": int(semi_minor)}
        centers, evidence_annotations = _draw_case_annotations(
            draw,
            rng=rng,
            annotations=annotations,
            evidence_label_values=evidence_values,
            blocked_segments=segments,
            context=context,
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(context.scene_scale)),
        )
        return _CaseArtifacts(
            shape_variant="ellipse",
            reasoning_mode="explicit",
            case_id="ellipse_explicit",
            question_key="question_text_ellipse_explicit",
            answer_type="pi_expression",
            answer_scalar=int(area_coeff),
            answer_value=_pi_expression(int(area_coeff)),
            formula_expression="A = π * a * b",
            evidence_ids=("a", "b"),
            evidence_label_values=dict(evidence_values),
            evidence_annotations=dict(evidence_annotations),
            annotation_centers=dict(centers),
            entity={
                "entity_id": "shape_1",
                "entity_type": "ellipse",
                "attrs": {
                    "shape_variant": "ellipse",
                    "reasoning_mode": "explicit",
                    "center": [float(center[0]), float(center[1])],
                    "semi_axis_x_units": int(semi_major),
                    "semi_axis_y_units": int(semi_minor),
                    "area_pi_coefficient": int(area_coeff),
                },
            },
            render_anchor=conic_render_anchor(
                center=center,
                semi_axis_x_px=int(semi_major) * int(spacing_px),
                semi_axis_y_px=int(semi_minor) * int(spacing_px),
            ),
        )
    raise ValueError("failed to sample ellipse explicit case")


def _sample_ellipse_derived_case(
    rng,
    *,
    draw: ImageDraw.ImageDraw,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
    gen_defaults: Mapping[str, Any],
) -> _CaseArtifacts:
    """Sample one ellipse semimajor+focus derived-area case and render it."""
    axis_cap = max(2, int(_unit_cap(context) // 2))
    max_component = int(group_default(gen_defaults, "right_triangle_max_component", _DEFAULTS.right_triangle_max_component))
    triplets = [
        (int(a), int(b), int(c))
        for a, b, c in _right_triangle_triplets(max_component)
        if int(c) <= int(axis_cap)
    ]
    if not triplets:
        raise ValueError("no feasible triplets for ellipse derived case")
    for _ in range(260):
        spacing_px = int(_analytical_unit_spacing_px(context))
        semi_minor, focal, semi_major = triplets[int(rng.randrange(len(triplets)))]
        if int(semi_major) <= int(semi_minor):
            continue
        area_coeff = int(semi_major * semi_minor)
        if int(area_coeff) < int(answer_min) or int(area_coeff) > int(answer_max):
            continue
        instance = sample_ellipse_instance_on_graph_paper(
            rng,
            canvas_size=int(context.canvas_size),
            graph_spacing=int(spacing_px),
            graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
            axis_pairs=[(int(semi_major), int(semi_minor))],
            padding_units=1,
            max_attempts=32,
        )
        center = (float(instance.center[0]), float(instance.center[1]))
        axis_x_end = offset_point_by_grid_vector(center, (int(semi_major), 0), spacing=int(spacing_px))
        focus_point = offset_point_by_grid_vector(center, (int(focal), 0), spacing=int(spacing_px))
        draw_ellipse_outline(
            draw,
            center=scale_point(center, int(context.scene_scale)),
            semi_axis_x_px=int(semi_major) * int(spacing_px) * int(context.scene_scale),
            semi_axis_y_px=int(semi_minor) * int(spacing_px) * int(context.scene_scale),
            line_width=max(1, int(line_width) * int(context.scene_scale)),
            line_color=tuple(int(value) for value in shape_style.line_color),
        )
        draw.line(
            [scale_point(center, int(context.scene_scale)), scale_point(axis_x_end, int(context.scene_scale))],
            fill=tuple(int(value) for value in shape_style.line_color),
            width=max(1, int(helper_line_width) * int(context.scene_scale)),
        )
        draw.line(
            [scale_point(center, int(context.scene_scale)), scale_point(focus_point, int(context.scene_scale))],
            fill=tuple(int(value) for value in shape_style.line_color),
            width=max(1, int(helper_line_width) * int(context.scene_scale)),
        )
        focus_marker = scale_point(focus_point, int(context.scene_scale))
        marker_radius = max(2, int(context.scene_scale))
        draw.ellipse(
            [
                float(focus_marker[0]) - float(marker_radius),
                float(focus_marker[1]) - float(marker_radius),
                float(focus_marker[0]) + float(marker_radius),
                float(focus_marker[1]) + float(marker_radius),
            ],
            fill=tuple(int(value) for value in shape_style.line_color),
        )
        segments = [
            ((float(center[0]), float(center[1])), (float(axis_x_end[0]), float(axis_x_end[1]))),
            ((float(center[0]), float(center[1])), (float(focus_point[0]), float(focus_point[1]))),
        ]
        annotations = [
            _segment_annotation(
                ann_id="a",
                text=f"a={int(semi_major)}",
                point_a=center,
                point_b=axis_x_end,
                direction=(0.0, -1.0),
            ),
            _segment_annotation(
                ann_id="c",
                text=f"c={int(focal)}",
                point_a=center,
                point_b=focus_point,
                direction=(0.0, 1.0),
            ),
        ]
        evidence_values = {"a": int(semi_major), "c": int(focal)}
        centers, evidence_annotations = _draw_case_annotations(
            draw,
            rng=rng,
            annotations=annotations,
            evidence_label_values=evidence_values,
            blocked_segments=segments,
            context=context,
            shape_style=shape_style,
            label_offset_px=float(label_offset_px) * float(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=max(1, int(label_stroke_width) * int(context.scene_scale)),
        )
        return _CaseArtifacts(
            shape_variant="ellipse",
            reasoning_mode="derived",
            case_id="ellipse_derived",
            question_key="question_text_ellipse_derived",
            answer_type="pi_expression",
            answer_scalar=int(area_coeff),
            answer_value=_pi_expression(int(area_coeff)),
            formula_expression="A = π * a * sqrt(a^2 - c^2)",
            evidence_ids=("a", "c"),
            evidence_label_values=dict(evidence_values),
            evidence_annotations=dict(evidence_annotations),
            annotation_centers=dict(centers),
            entity={
                "entity_id": "shape_1",
                "entity_type": "ellipse",
                "attrs": {
                    "shape_variant": "ellipse",
                    "reasoning_mode": "derived",
                    "center": [float(center[0]), float(center[1])],
                    "semi_axis_x_units": int(semi_major),
                    "semi_axis_y_units": int(semi_minor),
                    "focal_distance_units": int(focal),
                    "area_pi_coefficient": int(area_coeff),
                },
            },
            render_anchor=conic_render_anchor(
                center=center,
                semi_axis_x_px=int(semi_major) * int(spacing_px),
                semi_axis_y_px=int(semi_minor) * int(spacing_px),
            ),
        )
    raise ValueError("failed to sample ellipse derived case")


def _sample_case(
    rng,
    *,
    shape_variant: str,
    reasoning_mode: str,
    draw: ImageDraw.ImageDraw,
    context: GraphSceneContext,
    shape_style: GeometryShapeStyle,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    answer_min: int,
    answer_max: int,
    gen_defaults: Mapping[str, Any],
) -> _CaseArtifacts:
    """Dispatch one shape/mode pair to the concrete case sampler."""
    key = f"{str(shape_variant)}_{str(reasoning_mode)}"
    if key == "rectangle_explicit":
        return _sample_rectangle_explicit_case(
            rng,
            draw=draw,
            context=context,
            shape_style=shape_style,
            line_width=int(line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            gen_defaults=gen_defaults,
        )
    if key == "rectangle_derived":
        return _sample_rectangle_derived_case(
            rng,
            draw=draw,
            context=context,
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            gen_defaults=gen_defaults,
        )
    if key == "triangle_explicit":
        return _sample_triangle_explicit_case(
            rng,
            draw=draw,
            context=context,
            shape_style=shape_style,
            line_width=int(line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            gen_defaults=gen_defaults,
        )
    if key == "triangle_derived":
        return _sample_triangle_derived_case(
            rng,
            draw=draw,
            context=context,
            shape_style=shape_style,
            line_width=int(line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            gen_defaults=gen_defaults,
        )
    if key == "parallelogram_explicit":
        return _sample_parallelogram_explicit_case(
            rng,
            draw=draw,
            context=context,
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            gen_defaults=gen_defaults,
        )
    if key == "parallelogram_derived":
        return _sample_parallelogram_derived_case(
            rng,
            draw=draw,
            context=context,
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            gen_defaults=gen_defaults,
        )
    if key == "trapezoid_explicit":
        return _sample_trapezoid_explicit_case(
            rng,
            draw=draw,
            context=context,
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            gen_defaults=gen_defaults,
        )
    if key == "trapezoid_derived":
        return _sample_trapezoid_derived_case(
            rng,
            draw=draw,
            context=context,
            shape_style=shape_style,
            line_width=int(line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            gen_defaults=gen_defaults,
        )
    if key == "rhombus_explicit":
        return _sample_rhombus_explicit_case(
            rng,
            draw=draw,
            context=context,
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
        )
    if key == "rhombus_derived":
        return _sample_rhombus_derived_case(
            rng,
            draw=draw,
            context=context,
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            gen_defaults=gen_defaults,
        )
    if key == "circle_explicit":
        return _sample_circle_explicit_case(
            rng,
            draw=draw,
            context=context,
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            gen_defaults=gen_defaults,
        )
    if key == "circle_derived":
        return _sample_circle_derived_case(
            rng,
            draw=draw,
            context=context,
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            gen_defaults=gen_defaults,
        )
    if key == "ellipse_explicit":
        return _sample_ellipse_explicit_case(
            rng,
            draw=draw,
            context=context,
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            gen_defaults=gen_defaults,
        )
    if key == "ellipse_derived":
        return _sample_ellipse_derived_case(
            rng,
            draw=draw,
            context=context,
            shape_style=shape_style,
            line_width=int(line_width),
            helper_line_width=int(helper_line_width),
            label_offset_px=float(label_offset_px),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            gen_defaults=gen_defaults,
        )
    raise ValueError(f"unsupported shape/mode pair: {key}")


@register_task
class GeometryAnalyticalArea2DTask:
    """Measure area from annotated single-shape analytical geometry scenes."""

    task_id = "task_geometry_analytical_2d_area"
    domain = "geometry"
    task_group = "analytical_2d"

    def _complexity(
        self,
        *,
        shape_variant: str,
        reasoning_mode: str,
        answer_scalar: int,
        answer_max: int,
    ) -> TaskComplexity:
        """Compute task complexity from shape family, mode, and answer magnitude."""
        shape_weight = {
            "rectangle": 0.20,
            "triangle": 0.30,
            "parallelogram": 0.40,
            "trapezoid": 0.52,
            "rhombus": 0.58,
            "circle": 0.46,
            "ellipse": 0.62,
        }.get(str(shape_variant), 0.50)
        mode_weight = 0.0 if str(reasoning_mode) == "explicit" else 0.28
        magnitude = 0.0
        if int(answer_max) > 0:
            magnitude = min(1.0, float(answer_scalar) / float(max(1, int(answer_max))))
        score = max(0.0, min(1.0, 0.26 + (0.42 * float(shape_weight)) + (0.22 * float(mode_weight)) + (0.10 * float(magnitude))))
        return TaskComplexity(
            complexity_score=float(score),
            complexity_components={
                "shape_variant": str(shape_variant),
                "reasoning_mode": str(reasoning_mode),
                "answer_scalar": int(answer_scalar),
                "shape_component": float(shape_weight),
                "mode_component": float(mode_weight),
                "magnitude_component": float(magnitude),
            },
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic analytical area instance."""
        task_group_defaults = get_task_group_defaults(self.domain, self.task_group)
        gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            task_group_defaults if isinstance(task_group_defaults, Mapping) else {},
            task_id=str(self.task_id),
        )
        answer_min, answer_max = _answer_bounds(params, gen_defaults=gen_defaults)
        scene_rng = spawn_rng(int(instance_seed), "scene")
        shape_variant, shape_probs, reasoning_mode, mode_probs = _resolve_shape_and_mode(
            scene_rng,
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
        )
        context_params = dict(params)
        if "analytical_unit_spacing_px" not in context_params:
            context_params["analytical_unit_spacing_px"] = int(
                group_default(render_defaults, "analytical_unit_spacing_px", 10)
            )
        if "analytical_unit_padding_px" not in context_params:
            context_params["analytical_unit_padding_px"] = int(
                group_default(render_defaults, "analytical_unit_padding_px", 20)
            )

        line_width = sample_int_render_param(
            scene_rng,
            params=context_params,
            render_defaults=render_defaults,
            key="line_width",
            fallback=int(_DEFAULTS.line_width),
            min_key="line_width_min",
            max_key="line_width_max",
            minimum_value=1,
        )
        helper_line_width = sample_int_render_param(
            scene_rng,
            params=context_params,
            render_defaults=render_defaults,
            key="helper_line_width",
            fallback=int(_DEFAULTS.helper_line_width),
            min_key="helper_line_width_min",
            max_key="helper_line_width_max",
            minimum_value=1,
        )
        label_stroke_width = sample_int_render_param(
            scene_rng,
            params=context_params,
            render_defaults=render_defaults,
            key="label_stroke_width",
            fallback=int(_DEFAULTS.label_stroke_width),
            min_key="label_stroke_width_min",
            max_key="label_stroke_width_max",
            minimum_value=1,
        )

        attempt_budget = max(1, int(max_attempts))
        case: _CaseArtifacts | None = None
        context: GraphSceneContext | None = None
        image = None
        background_meta: Dict[str, Any] = {}
        shape_style: GeometryShapeStyle | None = None
        last_error: Exception | None = None

        for _ in range(int(attempt_budget)):
            try:
                context = resolve_graph_scene_context(
                    scene_rng,
                    params=context_params,
                    render_defaults=render_defaults,
                    background_defaults=ANALYTICAL_POST_IMAGE_BACKGROUND_DEFAULTS,
                    fallback_canvas_min=_DEFAULTS.canvas_size_min,
                    fallback_canvas_max=_DEFAULTS.canvas_size_max,
                    fallback_cells_min=_DEFAULTS.graph_cells_min,
                    fallback_cells_max=_DEFAULTS.graph_cells_max,
                    require_graph_paper_background=False,
                )
                label_offset_px = float(group_default(render_defaults, "label_offset_px", _DEFAULTS.label_offset_px))
                label_font_size_px = resolve_scene_label_font_size_px(
                    canvas_size=int(context.canvas_size),
                    graph_spacing=int(_analytical_unit_spacing_px(context)),
                    scene_scale=int(context.scene_scale),
                    min_px=int(group_default(render_defaults, "label_font_size_min", _DEFAULTS.label_font_size_min)),
                    max_px=int(group_default(render_defaults, "label_font_size_max", _DEFAULTS.label_font_size_max)),
                )
                image, draw, background_meta = make_graph_scene_canvas(
                    instance_seed=int(instance_seed),
                    context=context,
                    background_defaults=ANALYTICAL_POST_IMAGE_BACKGROUND_DEFAULTS,
                    require_graph_paper=False,
                )
                shape_style = sample_geometry_shape_style(
                    scene_rng,
                    params=context_params,
                    render_defaults=render_defaults,
                    anchor_colors=extract_background_anchor_colors(background_meta),
                )
                case = _sample_case(
                    scene_rng,
                    shape_variant=str(shape_variant),
                    reasoning_mode=str(reasoning_mode),
                    draw=draw,
                    context=context,
                    shape_style=shape_style,
                    line_width=int(line_width),
                    helper_line_width=int(helper_line_width),
                    label_offset_px=float(label_offset_px),
                    label_font_size_px=int(label_font_size_px),
                    label_stroke_width=int(label_stroke_width),
                    answer_min=int(answer_min),
                    answer_max=int(answer_max),
                    gen_defaults=gen_defaults,
                )
                break
            except Exception as exc:
                last_error = exc
                case = None
                context = None
                image = None
                shape_style = None
                continue

        if case is None or context is None or image is None or shape_style is None:
            raise RuntimeError("failed to generate task_geometry_analytical_2d_area instance") from last_error

        image, background_meta_final, post_noise_meta = finalize_graph_scene_image(
            image,
            instance_seed=int(instance_seed),
            context=context,
            background_meta=background_meta,
            noise_defaults=ANALYTICAL_POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_required = required_group_defaults(
            prompt_defaults,
            (
                "bundle_id",
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "evidence_hint_measurement_map",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        evidence_roles = [str(item) for item in case.evidence_ids]
        required_annotations = [
            str(case.evidence_annotations[role])
            for role in evidence_roles
            if str(role) in case.evidence_annotations
        ]
        evidence_map = build_role_value_evidence(
            roles=evidence_roles,
            role_to_annotation=case.evidence_annotations,
            role_to_value=case.evidence_label_values,
        )
        evidence_hint_base = str(prompt_required["evidence_hint_measurement_map"]).strip()
        if evidence_hint_base and evidence_hint_base[-1] not in {".", "!", "?", ":", ";"}:
            evidence_hint_base = f"{evidence_hint_base}."
        evidence_hint = (
            f"{evidence_hint_base} Required annotations: {', '.join(required_annotations)}"
            if evidence_hint_base
            else f"Required annotations: {', '.join(required_annotations)}"
        )
        answer_family = "pi" if str(case.answer_type) == "pi_expression" else "integer"
        question_text = _required_prompt_text(
            prompt_defaults,
            preferred_keys=(str(case.question_key), "question_text"),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_hint = _required_prompt_text(
            prompt_defaults,
            preferred_keys=(f"answer_hint_{answer_family}", "answer_hint"),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = build_prompt_json_examples(
            evidence_value=evidence_map,
            answer_type=str(case.answer_type),
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_required["bundle_id"]),
            task_family_key=str(prompt_required["task_family_key"]),
            task_key=str(prompt_required["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_required["object_description"]),
                "question_text": str(question_text),
                "json_output_contract": str(prompt_required["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_required["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(answer_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        if str(case.answer_type) == "pi_expression":
            answer_gt = TypedValue(type="pi_expression", value=str(case.answer_value))
        else:
            answer_gt = TypedValue(type="integer", value=int(case.answer_value))
        evidence_gt = TypedValue(type="measurement_ref_map", value=dict(evidence_map))
        complexity = self._complexity(
            shape_variant=str(case.shape_variant),
            reasoning_mode=str(case.reasoning_mode),
            answer_scalar=int(case.answer_scalar),
            answer_max=int(answer_max),
        )

        annotation_centers_by_token = {
            str(case.evidence_annotations[key]): [float(case.annotation_centers[key][0]), float(case.annotation_centers[key][1])]
            for key in evidence_roles
            if key in case.annotation_centers and key in case.evidence_annotations
        }
        projected_point_set = [
            [float(annotation_centers_by_token[key][0]), float(annotation_centers_by_token[key][1])]
            for key in required_annotations
            if key in annotation_centers_by_token
        ]
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_2d_analytical_area",
                "entities": [dict(case.entity)],
                "relations": {},
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "graph_unit": {
                        "origin_pixel": list(context.graph_frame["origin_pixel"]),
                        "spacing_px": int(context.graph_frame["spacing_px"]),
                        "x_positive": str(context.graph_frame["x_positive"]),
                        "y_positive": str(context.graph_frame["y_positive"]),
                    },
                },
            },
            "query_spec": {
                "task_variant": str(case.case_id),
                "template_id": "geometry_analytical_area_v1",
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "shape_variant": str(case.shape_variant),
                    "reasoning_mode": str(case.reasoning_mode),
                    "shape_probabilities": dict(shape_probs),
                    "mode_probabilities": dict(mode_probs),
                    "answer_min": int(answer_min),
                    "answer_max": int(answer_max),
                },
            },
            "render_spec": {
                "canvas_size": int(context.canvas_size),
                "coord_space": "pixel",
                "background_style": dict(background_meta_final),
                "post_image_noise": dict(post_noise_meta),
                "shape_style": dict(shape_style.to_trace_dict()),
                "graph_coordinate_frame": dict(context.graph_frame),
                "graph_paper_grid": graph_paper_grid_from_frame(context.graph_frame),
            },
            "render_map": {
                "entity_id": str(case.entity["entity_id"]),
                "instance_anchor": dict(case.render_anchor),
                "annotation_labels": dict(case.evidence_annotations),
                "annotation_centers": dict(annotation_centers_by_token),
                "coord_space": "pixel",
            },
            "execution_trace": {
                "shape_variant": str(case.shape_variant),
                "reasoning_mode": str(case.reasoning_mode),
                "case_id": str(case.case_id),
                "formula_expression": str(case.formula_expression),
                "answer_type": str(case.answer_type),
                "answer_scalar": int(case.answer_scalar),
                "answer_value": case.answer_value,
                "evidence_ids": list(required_annotations),
                "evidence_roles": list(evidence_roles),
                "required_annotations": list(required_annotations),
                "evidence_label_values": dict(case.evidence_label_values),
                "evidence_annotations": dict(case.evidence_annotations),
                "evidence_map": dict(evidence_map),
                "shape_probabilities": dict(shape_probs),
                "mode_probabilities": dict(mode_probs),
                "answer_min": int(answer_min),
                "answer_max": int(answer_max),
            },
            "witness_symbolic": {
                "type": "annotation_measurement_map",
                "case_id": str(case.case_id),
                "shape_variant": str(case.shape_variant),
                "reasoning_mode": str(case.reasoning_mode),
                "formula_expression": str(case.formula_expression),
                "annotation_ids": list(required_annotations),
                "annotation_values": dict(evidence_map),
                "annotation_labels": dict(case.evidence_annotations),
                "measurement_ref_map": dict(evidence_map),
            },
            "projected_evidence": {
                "measurement_ref_map": dict(evidence_map),
                "id_set": list(required_annotations),
                "pixel_point_set": list(projected_point_set),
                "annotation_labels": dict(case.evidence_annotations),
                "pixel_annotation_centers": dict(annotation_centers_by_token),
            },
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img_0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(case.case_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
