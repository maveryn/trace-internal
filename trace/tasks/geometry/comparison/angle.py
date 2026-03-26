"""Graph-paper geometry comparison task over multiple labeled angles."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ....core.sampling import normalize_positive_weights, weighted_choice
from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.comparison_sampling import (
    ComparisonGapMetrics,
    comparison_gap_is_valid,
    compute_comparison_gap_metrics,
)
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.geometry_primitives import Point, point_inside_square_canvas
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
from ..shared.angle_geometry import primitive_angle_pair_catalog
from ..shared.background_defaults import POST_IMAGE_BACKGROUND_DEFAULTS
from ..shared.graph_paper import offset_point_by_grid_vector
from ..shared.graph_rendering import graph_paper_grid_from_frame, scale_point
from ..shared.labeled_point_evidence import graph_point_set_evidence_artifacts
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
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
from ..shared.variant_sampling import has_non_null_param, is_uniform_probability_map
from .defaults import COMPARISON_SHARED_DEFAULTS

_QUERY_TYPES: Tuple[str, str] = ("largest", "smallest")
_ANSWER_LABEL_POOL: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for angle-comparison generation."""

    canvas_size_min: int = COMPARISON_SHARED_DEFAULTS.canvas_size_min
    canvas_size_max: int = COMPARISON_SHARED_DEFAULTS.canvas_size_max
    graph_cells_min: int = COMPARISON_SHARED_DEFAULTS.graph_cells_min
    graph_cells_max: int = COMPARISON_SHARED_DEFAULTS.graph_cells_max
    line_width: int = COMPARISON_SHARED_DEFAULTS.line_width
    label_offset_px: float = COMPARISON_SHARED_DEFAULTS.label_offset_px
    label_font_size_min: int = COMPARISON_SHARED_DEFAULTS.label_font_size_min
    label_font_size_max: int = COMPARISON_SHARED_DEFAULTS.label_font_size_max
    label_stroke_width: int = COMPARISON_SHARED_DEFAULTS.label_stroke_width
    object_count_min: int = COMPARISON_SHARED_DEFAULTS.object_count_min
    object_count_max: int = COMPARISON_SHARED_DEFAULTS.object_count_max
    min_angle: int = 30
    max_angle: int = 150
    angle_step: int = 1
    max_catalog_quantization_error_degrees: float = 2.0
    max_abs_vector_component: int = 8
    min_ray_length_units: float = 2.0
    min_normalized_gap: float = COMPARISON_SHARED_DEFAULTS.min_normalized_gap
    min_absolute_gap_degrees: float = 10.0
    object_label_offset_px: float = 14.0


@dataclass(frozen=True)
class _AngleObject:
    """One labeled angle object rendered in the comparison scene."""

    label: str
    vertex: Point
    point_a: Point
    point_b: Point
    target_angle_degrees: int
    raw_angle_degrees: float


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready scene payload for one multi-angle comparison instance."""

    query_type: str
    object_count: int
    objects: Tuple[_AngleObject, ...]
    winner_metrics: ComparisonGapMetrics
    winner_label: str
    evidence_points_by_label: Dict[str, Point]
    object_label_centers: Dict[str, List[float]]
    render_anchor: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "comparison")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_geometry_comparison_angle",
)


def _resolve_query_type(rng, *, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve comparison query type with weighted defaults."""

    explicit = params.get("query_type")
    if explicit is not None:
        selected = str(explicit).strip().lower()
        if selected not in set(_QUERY_TYPES):
            raise ValueError(f"unsupported query_type: {selected}")
        return selected, {key: (1.0 if key == selected else 0.0) for key in sorted(_QUERY_TYPES)}

    raw_weights = params.get(
        "query_type_weights",
        group_default(_GEN_DEFAULTS, "query_type_weights", {key: 1.0 for key in _QUERY_TYPES}),
    )
    if not isinstance(raw_weights, Mapping):
        raise ValueError("query_type_weights must be a mapping when provided")
    weights = {
        str(key): float(value)
        for key, value in raw_weights.items()
        if str(key) in set(_QUERY_TYPES)
    }
    probabilities = normalize_positive_weights(weights, default_keys=_QUERY_TYPES)
    selected = weighted_choice(rng, probabilities, sort_keys=True)
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_object_count(rng, *, params: Mapping[str, Any]) -> Tuple[int, Dict[str, float]]:
    """Resolve how many compared angles appear in the scene."""

    min_count = int(params.get("object_count_min", group_default(_GEN_DEFAULTS, "object_count_min", _DEFAULTS.object_count_min)))
    max_count = int(params.get("object_count_max", group_default(_GEN_DEFAULTS, "object_count_max", _DEFAULTS.object_count_max)))
    if min_count < 2 or min_count > max_count:
        raise ValueError("invalid object_count_min/object_count_max for comparison angle task")
    supported_counts = [int(value) for value in range(int(min_count), int(max_count) + 1)]

    explicit = params.get("object_count")
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(supported_counts):
            raise ValueError("object_count is outside configured supported range")
        return int(selected), {str(value): (1.0 if int(value) == int(selected) else 0.0) for value in supported_counts}

    raw_weights = params.get(
        "object_count_weights",
        group_default(_GEN_DEFAULTS, "object_count_weights", {str(value): 1.0 for value in supported_counts}),
    )
    if not isinstance(raw_weights, Mapping):
        raise ValueError("object_count_weights must be a mapping when provided")
    weights = {
        str(key): float(value)
        for key, value in raw_weights.items()
        if str(key) in {str(value) for value in supported_counts}
    }
    probabilities = normalize_positive_weights(weights, default_keys=[str(value) for value in supported_counts])
    selected = int(weighted_choice(rng, probabilities, sort_keys=True))
    return int(selected), {str(key): float(value) for key, value in sorted(probabilities.items(), key=lambda item: int(item[0]))}


def _resolve_winner_label(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve the intended winning answer label for one comparison scene."""

    explicit = params.get("winner_label")
    if explicit is not None:
        selected = str(explicit).strip().upper()
        if selected not in set(_ANSWER_LABEL_POOL):
            raise ValueError(f"unsupported winner_label: {selected}")
        return selected, {key: (1.0 if key == selected else 0.0) for key in _ANSWER_LABEL_POOL}

    raw_weights = params.get("winner_label_weights", {key: 1.0 for key in _ANSWER_LABEL_POOL})
    if not isinstance(raw_weights, Mapping):
        raise ValueError("winner_label_weights must be a mapping when provided")
    weights = {
        str(key).upper(): float(value)
        for key, value in raw_weights.items()
        if str(key).upper() in set(_ANSWER_LABEL_POOL)
    }
    probabilities = normalize_positive_weights(weights, default_keys=_ANSWER_LABEL_POOL)
    selected = str(weighted_choice(rng, probabilities, sort_keys=True)).upper()

    enabled = bool(params.get("balanced_sampling", group_default(_GEN_DEFAULTS, "balanced_sampling", True)))
    overridden = any(has_non_null_param(params, key) for key in ("winner_label", "winner_label_weights"))
    if bool(enabled) and (not overridden) and is_uniform_probability_map(probabilities):
        sampling_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace="comparison_winner_label",
        )
        selected = str(_ANSWER_LABEL_POOL[int(sampling_index) % len(_ANSWER_LABEL_POOL)])
    return selected, {str(key): float(value) for key, value in sorted(probabilities.items())}


def _apply_balanced_axes(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_type: str,
    query_type_probabilities: Mapping[str, float],
    object_count: int,
    object_count_probabilities: Mapping[str, float],
) -> Tuple[str, Dict[str, float], int, Dict[str, float]]:
    """Apply deterministic balanced defaults over query type and object count."""

    enabled = bool(params.get("balanced_sampling", group_default(_GEN_DEFAULTS, "balanced_sampling", True)))
    resolved_query = str(query_type)
    resolved_count = int(object_count)
    query_probs = {str(key): float(value) for key, value in query_type_probabilities.items()}
    count_probs = {str(key): float(value) for key, value in object_count_probabilities.items()}
    if not bool(enabled):
        return resolved_query, query_probs, resolved_count, count_probs

    sampling_index = abs(int(params.get("_sampling_index", instance_seed)))

    query_overridden = any(has_non_null_param(params, key) for key in ("query_type", "query_type_weights"))
    if (not query_overridden) and is_uniform_probability_map(query_probs):
        resolved_query = str(_QUERY_TYPES[int(sampling_index) % len(_QUERY_TYPES)])

    count_overridden = any(has_non_null_param(params, key) for key in ("object_count", "object_count_weights"))
    sorted_counts = [int(value) for value in sorted((int(key) for key in count_probs.keys()))]
    if (not count_overridden) and is_uniform_probability_map(count_probs) and sorted_counts:
        count_index = int(sampling_index // max(1, len(_QUERY_TYPES))) % len(sorted_counts)
        resolved_count = int(sorted_counts[count_index])

    return resolved_query, query_probs, resolved_count, count_probs


def _complexity_score(*, object_count: int, gap_normalized: float) -> float:
    """Compute a lightweight complexity proxy for comparison scenes."""

    count_factor = min(1.0, max(0.0, (float(object_count) - 4.0) / 2.0))
    ambiguity_factor = 1.0 - min(1.0, max(0.0, float(gap_normalized)))
    return max(0.0, min(1.0, 0.38 + (0.22 * count_factor) + (0.34 * ambiguity_factor)))


def _graph_units_to_pixel(point_units: Tuple[int, int], *, graph_origin: Point, graph_spacing: int) -> Point:
    """Project one integer graph-unit point into canonical pixel space."""

    return (
        float(graph_origin[0]) + (float(point_units[0]) * float(graph_spacing)),
        float(graph_origin[1]) - (float(point_units[1]) * float(graph_spacing)),
    )


def _slot_centers_graph_units(*, object_count: int, graph_cells: int, rng) -> List[Tuple[int, int]]:
    """Resolve a subset of well-separated graph-unit slot centers for angle objects."""

    half_span = max(6, int(graph_cells // 2))
    x_step = min(max(4, int(round(float(graph_cells) * 0.26))), max(4, int(half_span - 3)))
    y_step = min(max(4, int(round(float(graph_cells) * 0.20))), max(4, int(half_span - 3)))
    all_slots = [
        (-int(x_step), int(y_step)),
        (0, int(y_step)),
        (int(x_step), int(y_step)),
        (-int(x_step), -int(y_step)),
        (0, -int(y_step)),
        (int(x_step), -int(y_step)),
    ]
    rng.shuffle(all_slots)
    return list(all_slots[: int(object_count)])


def _sample_target_angles(
    rng,
    *,
    candidate_angles: Sequence[int],
    object_count: int,
    query_type: str,
    min_normalized_gap: float,
    min_absolute_gap_degrees: float,
) -> List[int]:
    """Sample distinct target angles whose winner gap is visually meaningful."""

    candidates = [int(value) for value in candidate_angles]
    if len(candidates) < int(object_count):
        raise ValueError("not enough feasible angle candidates for requested object_count")
    for _ in range(800):
        selected = [int(value) for value in rng.sample(candidates, int(object_count))]
        if comparison_gap_is_valid(
            [float(value) for value in selected],
            query_type=str(query_type),
            min_normalized_gap=float(min_normalized_gap),
            min_absolute_gap=float(min_absolute_gap_degrees),
        ):
            return selected
    raise ValueError("failed to sample comparison angles with the configured gap rule")


def _screen_bisector_direction(obj: _AngleObject) -> Point:
    """Return one stable screen-space bisector direction for object-label placement."""

    vec_a = (float(obj.point_a[0]) - float(obj.vertex[0]), float(obj.point_a[1]) - float(obj.vertex[1]))
    vec_b = (float(obj.point_b[0]) - float(obj.vertex[0]), float(obj.point_b[1]) - float(obj.vertex[1]))
    mag_a = math.hypot(float(vec_a[0]), float(vec_a[1]))
    mag_b = math.hypot(float(vec_b[0]), float(vec_b[1]))
    if mag_a <= 1e-9 or mag_b <= 1e-9:
        return (1.0, -1.0)
    bisector = (
        (float(vec_a[0]) / float(mag_a)) + (float(vec_b[0]) / float(mag_b)),
        (float(vec_a[1]) / float(mag_a)) + (float(vec_b[1]) / float(mag_b)),
    )
    if math.hypot(float(bisector[0]), float(bisector[1])) <= 1e-9:
        return (float(-(vec_a[1]) / float(mag_a)), float(vec_a[0] / float(mag_a)))
    return bisector


def _draw_angle_scene(
    draw: ImageDraw.ImageDraw,
    *,
    objects: Sequence[_AngleObject],
    scene_scale: int,
    line_width: int,
    label_font_size_px: int,
    label_stroke_width: int,
    object_label_offset_px: float,
    render_canvas_size: int,
    shape_style: GeometryShapeStyle,
) -> Dict[str, List[float]]:
    """Draw all angles plus comparison labels and return unscaled label centers."""

    scaled_objects = [
        {
            "label": str(obj.label),
            "vertex": scale_point(obj.vertex, int(scene_scale)),
            "point_a": scale_point(obj.point_a, int(scene_scale)),
            "point_b": scale_point(obj.point_b, int(scene_scale)),
            "raw": obj,
        }
        for obj in objects
    ]
    blocked_segments: List[Tuple[Point, Point]] = []
    line_color = tuple(int(value) for value in shape_style.line_color)
    for scaled in scaled_objects:
        point_a = scaled["point_a"]
        vertex = scaled["vertex"]
        point_b = scaled["point_b"]
        draw.line([point_a[0], point_a[1], vertex[0], vertex[1]], fill=line_color, width=max(1, int(line_width)))
        draw.line([vertex[0], vertex[1], point_b[0], point_b[1]], fill=line_color, width=max(1, int(line_width)))
        blocked_segments.extend(
            [
                ((float(point_a[0]), float(point_a[1])), (float(vertex[0]), float(vertex[1]))),
                ((float(vertex[0]), float(vertex[1])), (float(point_b[0]), float(point_b[1]))),
            ]
        )

    font = load_font(int(label_font_size_px), bold=True)
    occupied_boxes: List[Tuple[float, float, float, float]] = []
    label_centers: Dict[str, List[float]] = {}
    for scaled in scaled_objects:
        obj = scaled["raw"]
        direction = _screen_bisector_direction(obj)
        center, bbox = resolve_text_label_center(
            draw,
            text=str(obj.label),
            anchor=(float(scaled["vertex"][0]), float(scaled["vertex"][1])),
            base_direction=(float(direction[0]), float(direction[1])),
            offset_px=float(object_label_offset_px) * float(scene_scale),
            font=font,
            blocked_segments=blocked_segments,
            occupied_boxes=occupied_boxes,
            stroke_width=int(label_stroke_width),
            line_clearance_px=max(4.0, 0.9 * float(max(1, int(line_width)))),
            canvas_size=int(render_canvas_size),
        )
        draw_text_centered(
            draw,
            text=str(obj.label),
            center=(float(center[0]), float(center[1])),
            font=font,
            fill=tuple(int(value) for value in shape_style.label_color),
            stroke_fill=tuple(int(value) for value in shape_style.label_stroke_color),
            stroke_width=int(label_stroke_width),
        )
        occupied_boxes.append(bbox)
        label_centers[str(obj.label)] = [
            float(center[0]) / float(max(1, int(scene_scale))),
            float(center[1]) / float(max(1, int(scene_scale))),
        ]
    return label_centers


def _sample_scene(
    rng,
    *,
    winner_label: str,
    context: GraphSceneContext,
    query_type: str,
    object_count: int,
    min_angle: int,
    max_angle: int,
    angle_step: int,
    max_catalog_quantization_error_degrees: float,
    max_abs_vector_component: int,
    min_ray_length_units: float,
    min_normalized_gap: float,
    min_absolute_gap_degrees: float,
    line_width: int,
    label_font_size_px: int,
    label_stroke_width: int,
    object_label_offset_px: float,
    draw: ImageDraw.ImageDraw,
    shape_style: GeometryShapeStyle,
) -> _ScenePayload:
    """Sample and draw one multi-angle comparison scene."""

    catalog = primitive_angle_pair_catalog(
        angle_step=int(angle_step),
        min_angle=int(min_angle),
        max_angle=int(max_angle),
        max_abs_vector_component=int(max_abs_vector_component),
        max_quantization_error=float(max_catalog_quantization_error_degrees),
        min_vector_length_units=float(min_ray_length_units),
    )
    candidate_angles = [int(value) for value in sorted(catalog.keys())]
    render_canvas_size = int(context.canvas_size) * int(context.scene_scale)
    endpoint_padding_px = max(3.0, 0.75 * float(context.graph_spacing) * float(context.scene_scale))

    last_error: Exception | None = None
    for _ in range(700):
        labels = [str(label) for label in _ANSWER_LABEL_POOL if str(label) != str(winner_label)]
        rng.shuffle(labels)
        selected_labels = [str(winner_label), *labels[: max(0, int(object_count) - 1)]]
        rng.shuffle(selected_labels)
        slots = _slot_centers_graph_units(object_count=int(object_count), graph_cells=int(context.graph_cells), rng=rng)
        sampled_target_angles = _sample_target_angles(
            rng,
            candidate_angles=candidate_angles,
            object_count=int(object_count),
            query_type=str(query_type),
            min_normalized_gap=float(min_normalized_gap),
            min_absolute_gap_degrees=float(min_absolute_gap_degrees),
        )
        winner_target_angle = (
            int(max(sampled_target_angles))
            if str(query_type) == "largest"
            else int(min(sampled_target_angles))
        )
        other_target_angles = [
            int(value)
            for value in sampled_target_angles
            if int(value) != int(winner_target_angle)
        ]
        rng.shuffle(other_target_angles)

        objects: List[_AngleObject] = []
        try:
            for label, slot_units in zip(selected_labels, slots):
                target_angle = (
                    int(winner_target_angle)
                    if str(label) == str(winner_label)
                    else int(other_target_angles.pop())
                )
                vertex = _graph_units_to_pixel(
                    (int(slot_units[0]), int(slot_units[1])),
                    graph_origin=context.graph_origin,
                    graph_spacing=int(context.graph_spacing),
                )
                pairs = list(catalog[int(target_angle)])
                rng.shuffle(pairs)
                selected_object: _AngleObject | None = None
                for vector_a, vector_b, raw_angle in pairs:
                    if bool(rng.randint(0, 1)):
                        vector_a, vector_b = vector_b, vector_a
                    point_a = offset_point_by_grid_vector(
                        vertex,
                        (int(vector_a[0]), int(vector_a[1])),
                        spacing=int(context.graph_spacing),
                    )
                    point_b = offset_point_by_grid_vector(
                        vertex,
                        (int(vector_b[0]), int(vector_b[1])),
                        spacing=int(context.graph_spacing),
                    )
                    scaled_point_a = scale_point(point_a, int(context.scene_scale))
                    scaled_vertex = scale_point(vertex, int(context.scene_scale))
                    scaled_point_b = scale_point(point_b, int(context.scene_scale))
                    if not (
                        point_inside_square_canvas(
                            scaled_point_a,
                            canvas_size=int(render_canvas_size),
                            padding=float(endpoint_padding_px),
                        )
                        and point_inside_square_canvas(
                            scaled_vertex,
                            canvas_size=int(render_canvas_size),
                            padding=float(endpoint_padding_px),
                        )
                        and point_inside_square_canvas(
                            scaled_point_b,
                            canvas_size=int(render_canvas_size),
                            padding=float(endpoint_padding_px),
                        )
                    ):
                        continue
                    selected_object = _AngleObject(
                        label=str(label),
                        vertex=(float(vertex[0]), float(vertex[1])),
                        point_a=(float(point_a[0]), float(point_a[1])),
                        point_b=(float(point_b[0]), float(point_b[1])),
                        target_angle_degrees=int(target_angle),
                        raw_angle_degrees=float(raw_angle),
                    )
                    break
                if selected_object is None:
                    raise ValueError(f"no feasible angle geometry for target {target_angle}")
                objects.append(selected_object)
        except Exception as exc:
            last_error = exc
            continue

        raw_values = [float(obj.raw_angle_degrees) for obj in objects]
        metrics = compute_comparison_gap_metrics(raw_values, query_type=str(query_type))
        if str(objects[int(metrics.winner_index)].label) != str(winner_label):
            continue
        if not comparison_gap_is_valid(
            raw_values,
            query_type=str(query_type),
            min_normalized_gap=float(min_normalized_gap),
            min_absolute_gap=float(min_absolute_gap_degrees),
        ):
            continue

        label_centers = _draw_angle_scene(
            draw,
            objects=tuple(objects),
            scene_scale=int(context.scene_scale),
            line_width=int(line_width) * int(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            object_label_offset_px=float(object_label_offset_px),
            render_canvas_size=int(render_canvas_size),
            shape_style=shape_style,
        )
        winner = objects[int(metrics.winner_index)]
        return _ScenePayload(
            query_type=str(query_type),
            object_count=int(object_count),
            objects=tuple(objects),
            winner_metrics=metrics,
            winner_label=str(winner.label),
            evidence_points_by_label={
                "ray_a": (float(winner.point_a[0]), float(winner.point_a[1])),
                "vertex": (float(winner.vertex[0]), float(winner.vertex[1])),
                "ray_b": (float(winner.point_b[0]), float(winner.point_b[1])),
            },
            object_label_centers=label_centers,
            render_anchor={
                "winner_label": str(winner.label),
                "winner_vertex": [float(winner.vertex[0]), float(winner.vertex[1])],
            },
        )

    raise RuntimeError("failed to sample angle-comparison scene") from last_error


@register_task
class GeometryComparisonAngleTask:
    """Compare multiple labeled angles and choose the largest/smallest one."""

    task_id = "task_geometry_comparison_angle"
    domain = "geometry"
    task_group = "comparison"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic multi-angle comparison instance."""

        scene_rng = spawn_rng(int(instance_seed), "scene")

        query_type, query_type_probabilities = _resolve_query_type(scene_rng, params=params)
        object_count, object_count_probabilities = _resolve_object_count(scene_rng, params=params)
        winner_label, winner_label_probabilities = _resolve_winner_label(
            scene_rng,
            instance_seed=int(instance_seed),
            params=params,
        )
        query_type, query_type_probabilities, object_count, object_count_probabilities = _apply_balanced_axes(
            instance_seed=int(instance_seed),
            params=params,
            query_type=str(query_type),
            query_type_probabilities=query_type_probabilities,
            object_count=int(object_count),
            object_count_probabilities=object_count_probabilities,
        )

        min_angle = int(params.get("min_angle", group_default(_GEN_DEFAULTS, "min_angle", _DEFAULTS.min_angle)))
        max_angle = int(params.get("max_angle", group_default(_GEN_DEFAULTS, "max_angle", _DEFAULTS.max_angle)))
        angle_step = int(params.get("angle_step", group_default(_GEN_DEFAULTS, "angle_step", _DEFAULTS.angle_step)))
        max_catalog_quantization_error = float(
            params.get(
                "max_catalog_quantization_error_degrees",
                group_default(
                    _GEN_DEFAULTS,
                    "max_catalog_quantization_error_degrees",
                    _DEFAULTS.max_catalog_quantization_error_degrees,
                ),
            )
        )
        max_abs_vector_component = int(
            params.get(
                "max_abs_vector_component",
                group_default(_GEN_DEFAULTS, "max_abs_vector_component", _DEFAULTS.max_abs_vector_component),
            )
        )
        min_ray_length_units = float(
            params.get(
                "min_ray_length_units",
                group_default(_GEN_DEFAULTS, "min_ray_length_units", _DEFAULTS.min_ray_length_units),
            )
        )
        min_normalized_gap = float(
            params.get(
                "min_normalized_gap",
                group_default(_GEN_DEFAULTS, "min_normalized_gap", _DEFAULTS.min_normalized_gap),
            )
        )
        min_absolute_gap_degrees = float(
            params.get(
                "min_absolute_gap_degrees",
                group_default(_GEN_DEFAULTS, "min_absolute_gap_degrees", _DEFAULTS.min_absolute_gap_degrees),
            )
        )
        if int(min_angle) >= int(max_angle):
            raise ValueError("min_angle must be < max_angle for comparison angle task")
        if int(angle_step) <= 0:
            raise ValueError("angle_step must be > 0")
        if float(min_ray_length_units) <= 0.0:
            raise ValueError("min_ray_length_units must be > 0")
        if float(min_normalized_gap) < 0.0:
            raise ValueError("min_normalized_gap must be >= 0")
        if float(min_absolute_gap_degrees) < 0.0:
            raise ValueError("min_absolute_gap_degrees must be >= 0")

        context_params = dict(params)
        context = None
        image = None
        background_meta = None
        shape_style = None
        label_font_size_px = None
        label_stroke_width_scene = None
        line_width = None
        scene_payload: _ScenePayload | None = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            context_attempt = resolve_graph_scene_context(
                scene_rng,
                params=context_params,
                render_defaults=_RENDER_DEFAULTS,
                background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
                fallback_canvas_min=_DEFAULTS.canvas_size_min,
                fallback_canvas_max=_DEFAULTS.canvas_size_max,
                fallback_cells_min=_DEFAULTS.graph_cells_min,
                fallback_cells_max=_DEFAULTS.graph_cells_max,
            )
            line_width_attempt = sample_int_render_param(
                scene_rng,
                params=context_params,
                render_defaults=_RENDER_DEFAULTS,
                key="line_width",
                fallback=_DEFAULTS.line_width,
                minimum_value=1,
            )
            label_font_size_px_attempt = int(
                params.get(
                    "label_font_size_px",
                    resolve_scene_label_font_size_px(
                        canvas_size=int(context_attempt.canvas_size),
                        graph_spacing=int(context_attempt.graph_spacing),
                        scene_scale=int(context_attempt.scene_scale),
                        min_px=int(
                            group_default(
                                _RENDER_DEFAULTS,
                                "label_font_size_min",
                                _DEFAULTS.label_font_size_min,
                            )
                        ),
                        max_px=int(
                            group_default(
                                _RENDER_DEFAULTS,
                                "label_font_size_max",
                                _DEFAULTS.label_font_size_max,
                            )
                        ),
                    ),
                )
            )
            if int(label_font_size_px_attempt) < 6:
                raise ValueError("label_font_size_px must be >= 6")
            label_stroke_width_attempt = sample_int_render_param(
                scene_rng,
                params=context_params,
                render_defaults=_RENDER_DEFAULTS,
                key="label_stroke_width",
                fallback=_DEFAULTS.label_stroke_width,
                minimum_value=1,
            )
            label_stroke_width_scene_attempt = int(
                max(1, int(label_stroke_width_attempt) * int(context_attempt.scene_scale))
            )
            object_label_offset_px = float(
                context_params.get(
                    "object_label_offset_px",
                    group_default(_RENDER_DEFAULTS, "object_label_offset_px", _DEFAULTS.object_label_offset_px),
                )
            )
            image_attempt, draw_attempt, background_meta_attempt = make_graph_scene_canvas(
                instance_seed=int(instance_seed),
                context=context_attempt,
                background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
            )
            shape_style_attempt = sample_geometry_shape_style(
                scene_rng,
                params=context_params,
                render_defaults=_RENDER_DEFAULTS,
                anchor_colors=extract_background_anchor_colors(background_meta_attempt),
            )
            try:
                scene_payload_attempt = _sample_scene(
                    scene_rng,
                    winner_label=str(winner_label),
                    context=context_attempt,
                    query_type=str(query_type),
                    object_count=int(object_count),
                    min_angle=int(min_angle),
                    max_angle=int(max_angle),
                    angle_step=int(angle_step),
                    max_catalog_quantization_error_degrees=float(max_catalog_quantization_error),
                    max_abs_vector_component=int(max_abs_vector_component),
                    min_ray_length_units=float(min_ray_length_units),
                    min_normalized_gap=float(min_normalized_gap),
                    min_absolute_gap_degrees=float(min_absolute_gap_degrees),
                    line_width=int(line_width_attempt),
                    label_font_size_px=int(label_font_size_px_attempt),
                    label_stroke_width=int(label_stroke_width_scene_attempt),
                    object_label_offset_px=float(object_label_offset_px),
                    draw=draw_attempt,
                    shape_style=shape_style_attempt,
                )
                context = context_attempt
                image = image_attempt
                background_meta = background_meta_attempt
                shape_style = shape_style_attempt
                label_font_size_px = int(label_font_size_px_attempt)
                label_stroke_width_scene = int(label_stroke_width_scene_attempt)
                line_width = int(line_width_attempt)
                scene_payload = scene_payload_attempt
                break
            except Exception as exc:
                last_error = exc
                continue

        if (
            scene_payload is None
            or context is None
            or image is None
            or background_meta is None
            or shape_style is None
            or label_font_size_px is None
            or label_stroke_width_scene is None
            or line_width is None
        ):
            raise RuntimeError("failed to generate task_geometry_comparison_angle instance") from last_error

        evidence = graph_point_set_evidence_artifacts(
            points_by_label=scene_payload.evidence_points_by_label,
            graph_origin=context.graph_origin,
            graph_spacing=int(context.graph_spacing),
            witness_type="winning_angle_triplet",
            ordered_labels=("ray_a", "vertex", "ray_b"),
        )
        evidence_value = evidence.get("evidence_value", [])
        if (
            not isinstance(evidence_value, list)
            or len(evidence_value) != 3
            or any(not isinstance(point, list) or len(point) != 2 for point in evidence_value)
            or any(not isinstance(coord, int) for point in evidence_value for coord in point)
        ):
            raise RuntimeError("comparison-angle evidence must include three integer graph-lattice points")

        image, background_meta_final, post_noise_meta = finalize_graph_scene_image(
            image,
            instance_seed=int(instance_seed),
            context=context,
            background_meta=background_meta,
            noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text_largest",
                "question_text_smallest",
                "evidence_hint",
                "answer_hint",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_text_key = "question_text_largest" if str(query_type) == "largest" else "question_text_smallest"
        question_text = str(prompt_defaults[str(question_text_key)])
        json_example, json_example_answer_only = build_prompt_json_examples(
            evidence_value=evidence_value,
            answer_type="option_letter",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(question_text),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        winner_label = str(scene_payload.winner_label)
        answer_gt = TypedValue(type="option_letter", value=str(winner_label))
        evidence_gt = TypedValue(type="graph_point_set", value=list(evidence_value))

        values_by_label = {
            str(obj.label): round(float(obj.raw_angle_degrees), 6)
            for obj in scene_payload.objects
        }
        query_params = {
            "query_type": str(query_type),
            "query_type_probabilities": dict(query_type_probabilities),
            "object_count": int(object_count),
            "object_count_probabilities": dict(object_count_probabilities),
            "winner_label": str(winner_label),
            "winner_label_probabilities": dict(winner_label_probabilities),
            "min_angle": int(min_angle),
            "max_angle": int(max_angle),
            "angle_step": int(angle_step),
            "min_normalized_gap": float(min_normalized_gap),
            "min_absolute_gap_degrees": float(min_absolute_gap_degrees),
            "max_abs_vector_component": int(max_abs_vector_component),
            "min_ray_length_units": float(min_ray_length_units),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_2d_angle_comparison",
                "entities": [
                    {
                        "entity_id": f"angle_{str(obj.label)}",
                        "entity_type": "angle",
                        "attrs": {
                            "label": str(obj.label),
                            "target_angle_degrees": int(obj.target_angle_degrees),
                            "raw_angle_degrees": float(obj.raw_angle_degrees),
                            "points": {
                                "arm_a": [float(obj.point_a[0]), float(obj.point_a[1])],
                                "vertex": [float(obj.vertex[0]), float(obj.vertex[1])],
                                "arm_b": [float(obj.point_b[0]), float(obj.point_b[1])],
                            },
                        },
                    }
                    for obj in scene_payload.objects
                ],
                "relations": {
                    "comparison_target": "angle_measure",
                    "query_type": str(query_type),
                    "winner_label": str(winner_label),
                },
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
                "task_variant": "primitive_angle_set",
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_size": int(context.canvas_size),
                "coord_space": "pixel",
                "background_style": dict(background_meta_final),
                "post_image_noise": dict(post_noise_meta),
                "shape_style": dict(shape_style.to_trace_dict()),
                "text_style": {
                    "font_size_px": int(label_font_size_px),
                    "stroke_width_px": int(label_stroke_width_scene),
                },
                "graph_coordinate_frame": dict(context.graph_frame),
                "graph_paper_grid": graph_paper_grid_from_frame(context.graph_frame),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {"winner": dict(scene_payload.render_anchor)},
                "object_label_centers": dict(scene_payload.object_label_centers),
            },
            "execution_trace": {
                "scene_variant": "primitive_angle_set",
                "query_type": str(query_type),
                "query_type_probabilities": dict(query_type_probabilities),
                "object_count": int(object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "winner_label_target": str(winner_label),
                "winner_label_probabilities": dict(winner_label_probabilities),
                "object_labels": [str(obj.label) for obj in scene_payload.objects],
                "values_by_label": dict(values_by_label),
                "winner_label": str(winner_label),
                "winner_value": float(scene_payload.winner_metrics.winner_value),
                "runner_up_value": float(scene_payload.winner_metrics.runner_up_value),
                "winner_gap_abs": float(scene_payload.winner_metrics.gap_abs),
                "winner_gap_normalized": float(scene_payload.winner_metrics.gap_normalized),
                "required_evidence_labels": ["ray_a", "vertex", "ray_b"],
                "question_format": "label_choice_no_text_options",
            },
            "witness_symbolic": {
                **dict(evidence["witness_symbolic"]),
                "winner_label": str(winner_label),
            },
            "projected_evidence": dict(evidence["projected_evidence"]),
        }

        complexity = TaskComplexity(
            complexity_score=_complexity_score(
                object_count=int(object_count),
                gap_normalized=float(scene_payload.winner_metrics.gap_normalized),
            ),
            complexity_components={
                "object_count": int(object_count),
                "gap_normalized": float(scene_payload.winner_metrics.gap_normalized),
                "query_type": str(query_type),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant="primitive_angle_set",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
