"""Single-object geometry angle-measurement task."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.sampling import normalize_positive_weights, weighted_choice
from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.geometry_primitives import Point
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import resolve_scene_label_font_size_px
from ..shared.angle_geometry import (
    draw_labeled_angle,
    primitive_angle_pair_catalog,
    sample_primitive_angle,
)
from ..shared.graph_paper import offset_point_by_grid_vector, sample_lattice_point_with_offsets
from ..shared.graph_rendering import graph_paper_grid_from_frame, scale_point
from ..shared.labeled_point_evidence import graph_point_set_evidence_artifacts
from ..shared.polygon_geometry import alphabetic_labels
from ..shared.render_variation import sample_int_render_param
from ..shared.shape_style import (
    GeometryShapeStyle,
    extract_background_anchor_colors,
    sample_geometry_shape_style,
)
from ..shared.single_object_scene import (
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)
from ..shared.background_defaults import POST_IMAGE_BACKGROUND_DEFAULTS
from .defaults import MEASUREMENT_SHARED_DEFAULTS
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS

_INTERSECTION_SOURCE_KIND = "intersection_lines"
_SOURCE_KINDS: Tuple[str, str] = ("primitive_angle", _INTERSECTION_SOURCE_KIND)


def _scene_variant_for_source_kind(source_kind: str) -> str:
    """Map one source-kind category to task-level `scene_variant`."""
    kind = str(source_kind)
    if kind == "primitive_angle":
        return "primitive_angle"
    if kind == _INTERSECTION_SOURCE_KIND:
        return "intersection_angle"
    raise ValueError(f"unsupported source_kind for scene_variant mapping: {kind}")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable defaults for single-object angle measurement."""

    canvas_size_min: int = MEASUREMENT_SHARED_DEFAULTS.canvas_size_min
    canvas_size_max: int = MEASUREMENT_SHARED_DEFAULTS.canvas_size_max
    graph_cells_min: int = MEASUREMENT_SHARED_DEFAULTS.graph_cells_min
    graph_cells_max: int = MEASUREMENT_SHARED_DEFAULTS.graph_cells_max
    min_angle: int = 30
    max_angle: int = 150
    angle_step: int = 1
    quantization_tolerance_degrees: float = 0.05
    max_abs_vector_component: int = 20
    min_ray_length_units: int = 2
    line_width: int = MEASUREMENT_SHARED_DEFAULTS.line_width
    label_offset_px: float = MEASUREMENT_SHARED_DEFAULTS.label_offset_px
    label_font_size_min: int = MEASUREMENT_SHARED_DEFAULTS.label_font_size_min
    label_font_size_max: int = MEASUREMENT_SHARED_DEFAULTS.label_font_size_max
    label_stroke_width: int = MEASUREMENT_SHARED_DEFAULTS.label_stroke_width


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "measurement")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_geometry_measurement_angle",
)


def _complexity_score(*, source_kind: str, angle_degrees: float) -> float:
    """Compute a lightweight complexity proxy for angle measurement."""
    centered = 1.0 - min(1.0, abs(float(angle_degrees) - 90.0) / 90.0)
    source_bonus = 0.18 if str(source_kind) == _INTERSECTION_SOURCE_KIND else 0.0
    return max(0.0, min(1.0, 0.42 + (0.4 * centered) + source_bonus))


def _angle_question_text(*, label_a: str, label_v: str, label_b: str) -> str:
    """Return canonical angle-measure question text for one label triplet."""
    return f"What is the measure of angle {str(label_a)}{str(label_v)}{str(label_b)} in degrees?"


def _resolve_source_kind(
    rng,
    *,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve shape source kind with near-uniform category sampling by default."""
    supported_kinds = [str(kind) for kind in _SOURCE_KINDS]
    supported_set = set(supported_kinds)

    explicit_source = params.get("source_kind")
    if explicit_source is not None:
        selected = str(explicit_source).strip()
        if selected not in supported_set:
            raise ValueError(f"unsupported source_kind: {selected}")
        return selected, {kind: (1.0 if kind == selected else 0.0) for kind in sorted(supported_set)}

    explicit_variant = params.get("scene_variant")
    if explicit_variant is not None:
        selected_variant = str(explicit_variant).strip()
        if selected_variant == "primitive_angle":
            return "primitive_angle", {kind: (1.0 if kind == "primitive_angle" else 0.0) for kind in sorted(supported_set)}
        if selected_variant in {"intersection_angle", _INTERSECTION_SOURCE_KIND}:
            return _INTERSECTION_SOURCE_KIND, {
                kind: (1.0 if kind == _INTERSECTION_SOURCE_KIND else 0.0) for kind in sorted(supported_set)
            }
        raise ValueError(f"unsupported scene_variant: {selected_variant}")

    raw_weights = params.get(
        "source_kind_weights",
        group_default(
            _GEN_DEFAULTS,
            "source_kind_weights",
            {kind: 1.0 for kind in _SOURCE_KINDS},
        ),
    )
    if not isinstance(raw_weights, Mapping):
        raise ValueError("source_kind_weights must be a mapping when provided")
    weights = {
        str(key): float(value)
        for key, value in raw_weights.items()
        if str(key) in supported_set
    }
    probabilities = normalize_positive_weights(weights, default_keys=supported_kinds)
    selected_kind = weighted_choice(rng, probabilities, sort_keys=True)
    return str(selected_kind), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _angle_candidates(*, min_angle: int, max_angle: int, angle_step: int) -> List[int]:
    """Return sorted feasible angle candidates for one configured range."""
    step = int(angle_step)
    low = int(min_angle)
    high = int(max_angle)
    if step <= 0:
        raise ValueError("angle_step must be > 0")
    if low > high:
        raise ValueError("min_angle must be <= max_angle")
    if low % step != 0 or high % step != 0:
        raise ValueError("min_angle and max_angle must align with angle_step")
    candidates = [int(value) for value in range(low, high + 1, step)]
    if not candidates:
        raise ValueError("no feasible target angles for configured range")
    return candidates


def _resolve_target_angle(
    rng,
    *,
    params: Mapping[str, Any],
    min_angle: int,
    max_angle: int,
    angle_step: int,
    candidate_values: Sequence[int] | None = None,
) -> Tuple[int, Dict[str, float]]:
    """Resolve one target angle with uniform-by-default sampling over feasible values."""
    if candidate_values is None:
        candidates = _angle_candidates(min_angle=int(min_angle), max_angle=int(max_angle), angle_step=int(angle_step))
    else:
        candidates = sorted({int(value) for value in candidate_values})
        if not candidates:
            raise ValueError("candidate_values must include at least one angle")

    explicit = params.get("target_angle")
    if explicit is not None:
        target = int(explicit)
        if target not in set(candidates):
            raise ValueError("target_angle is outside configured angle range")
        probabilities = {str(value): (1.0 if value == target else 0.0) for value in candidates}
        return int(target), probabilities

    raw_weights = params.get(
        "target_angle_weights",
        group_default(_GEN_DEFAULTS, "target_angle_weights", {str(value): 1.0 for value in candidates}),
    )
    if isinstance(raw_weights, Mapping):
        weights: Dict[str, float] = {}
        candidate_set = set(candidates)
        for key, value in raw_weights.items():
            try:
                angle_value = int(str(key))
            except Exception:
                continue
            if int(angle_value) not in candidate_set:
                continue
            weights[str(angle_value)] = float(value)
        probabilities = normalize_positive_weights(weights, default_keys=[str(value) for value in candidates])
    else:
        probabilities = normalize_positive_weights({}, default_keys=[str(value) for value in candidates])
    selected_key = weighted_choice(rng, probabilities, sort_keys=True)
    selected_value = int(selected_key)
    return selected_value, {str(key): float(value) for key, value in sorted(probabilities.items(), key=lambda item: int(item[0]))}


def _is_uniform_probability_map(probabilities: Mapping[str, float], *, tol: float = 1e-9) -> bool:
    """Return true when all positive probabilities are approximately equal."""
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if not positives:
        return False
    return max(positives) - min(positives) <= float(tol)


def _has_non_null_param(params: Mapping[str, Any], key: str) -> bool:
    """Return true when one non-null key override is provided."""
    return key in params and params.get(key) is not None


def _resolve_balanced_source_and_target(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    source_kind: str,
    source_kind_probabilities: Mapping[str, float],
    supported_source_kinds: Sequence[str],
    target_angle: int,
    target_angle_probabilities: Mapping[str, float],
    angle_candidates: Sequence[int],
) -> Tuple[str, Dict[str, float], int, Dict[str, float]]:
    """Apply deterministic balanced defaults over source+target when not overridden.

    Policy:
    - enabled by default via `balanced_sampling=true`,
    - never overrides explicit user controls (`source_kind`, `scene_variant`,
      `source_kind_weights`, `target_angle`, `target_angle_weights`),
    - only applies to dimensions whose probability maps are uniform.
    """
    enabled = bool(params.get("balanced_sampling", group_default(_GEN_DEFAULTS, "balanced_sampling", True)))
    resolved_source = str(source_kind)
    resolved_target = int(target_angle)
    source_probs = {str(key): float(value) for key, value in source_kind_probabilities.items()}
    target_probs = {str(key): float(value) for key, value in target_angle_probabilities.items()}
    if not bool(enabled):
        return resolved_source, source_probs, resolved_target, target_probs

    source_overridden = any(
        _has_non_null_param(params, key) for key in ("source_kind", "scene_variant", "source_kind_weights")
    )
    target_overridden = any(_has_non_null_param(params, key) for key in ("target_angle", "target_angle_weights"))
    source_uniform = _is_uniform_probability_map(source_probs)
    target_uniform = _is_uniform_probability_map(target_probs)
    source_values = [str(item) for item in supported_source_kinds]
    angle_values = [int(value) for value in angle_candidates]
    if not source_values or not angle_values:
        return resolved_source, source_probs, resolved_target, target_probs

    sampling_index = params.get("_sampling_index", instance_seed)
    seed_value = abs(int(sampling_index))
    if (not source_overridden) and (not target_overridden) and source_uniform and target_uniform:
        source_count = int(len(source_values))
        angle_count = int(len(angle_values))
        source_index = int(seed_value % source_count)
        angle_index = int((seed_value // source_count) % angle_count)
        resolved_source = str(source_values[source_index])
        resolved_target = int(angle_values[angle_index])
        return resolved_source, source_probs, resolved_target, target_probs
    if (not source_overridden) and source_uniform:
        source_index = int(seed_value % len(source_values))
        resolved_source = str(source_values[source_index])
    if (not target_overridden) and target_uniform:
        resolved_target = int(angle_values[int(seed_value % len(angle_values))])
    return resolved_source, source_probs, resolved_target, target_probs


def _offset_span_units(offsets: Sequence[int]) -> int:
    """Return inclusive span (`max-min`) across integer offsets."""
    values = [int(value) for value in offsets]
    return int(max(values) - min(values))


def _intersection_offsets_for_angle_source(
    *,
    vector_a: Tuple[int, int],
    vector_b: Tuple[int, int],
) -> List[Tuple[int, int]]:
    """Build base line-intersection offsets around one target vertex at `(0, 0)`."""
    va_x, va_y = int(vector_a[0]), int(vector_a[1])
    vb_x, vb_y = int(vector_b[0]), int(vector_b[1])
    return [
        (va_x, va_y),
        (-va_x, -va_y),
        (vb_x, vb_y),
        (-vb_x, -vb_y),
    ]


@lru_cache(maxsize=128)
def _primitive_feasible_angles_for_offset_limit(
    *,
    min_angle: int,
    max_angle: int,
    angle_step: int,
    max_abs_vector_component: int,
    quantization_tolerance_degrees: float,
    min_ray_length_units: float,
    max_offset_units: int,
) -> Tuple[int, ...]:
    """Return primitive-angle feasible targets under one offset-unit cap."""
    catalog = primitive_angle_pair_catalog(
        angle_step=int(angle_step),
        min_angle=int(min_angle),
        max_angle=int(max_angle),
        max_abs_vector_component=int(max_abs_vector_component),
        max_quantization_error=float(quantization_tolerance_degrees),
        min_vector_length_units=float(min_ray_length_units),
    )
    limit = max(1, int(max_offset_units))
    feasible: List[int] = []
    for angle_value, pairs in sorted(catalog.items()):
        accepted = any(
            _offset_span_units((0, int(vector_a[0]), int(vector_b[0]))) <= int(limit)
            and _offset_span_units((0, int(vector_a[1]), int(vector_b[1]))) <= int(limit)
            for vector_a, vector_b, _raw in pairs
        )
        if accepted:
            feasible.append(int(angle_value))
    return tuple(feasible)


@lru_cache(maxsize=128)
def _intersection_feasible_angles_for_offset_limit(
    *,
    min_angle: int,
    max_angle: int,
    angle_step: int,
    max_abs_vector_component: int,
    quantization_tolerance_degrees: float,
    min_ray_length_units: float,
    max_offset_units: int,
) -> Tuple[int, ...]:
    """Return line-intersection feasible target angles under one offset-unit cap."""
    catalog = primitive_angle_pair_catalog(
        angle_step=int(angle_step),
        min_angle=int(min_angle),
        max_angle=int(max_angle),
        max_abs_vector_component=int(max_abs_vector_component),
        max_quantization_error=float(quantization_tolerance_degrees),
        min_vector_length_units=float(min_ray_length_units),
    )
    feasible: List[int] = []
    limit = max(1, int(max_offset_units))
    for angle_value, pairs in sorted(catalog.items()):
        accepted = False
        for vector_a, vector_b, _raw in pairs:
            offsets = _intersection_offsets_for_angle_source(
                vector_a=(int(vector_a[0]), int(vector_a[1])),
                vector_b=(int(vector_b[0]), int(vector_b[1])),
            )
            x_offsets = [int(offset[0]) for offset in offsets]
            y_offsets = [int(offset[1]) for offset in offsets]
            if _offset_span_units(x_offsets) <= int(limit) and _offset_span_units(y_offsets) <= int(limit):
                accepted = True
                break
        if accepted:
            feasible.append(int(angle_value))
    return tuple(feasible)


@lru_cache(maxsize=512)
def _required_graph_cells_for_primitive_target(
    *,
    target_angle: int,
    min_angle: int,
    max_angle: int,
    angle_step: int,
    max_abs_vector_component: int,
    quantization_tolerance_degrees: float,
    min_ray_length_units: float,
) -> int:
    """Return minimum graph-cell count needed for one primitive target angle."""
    catalog = primitive_angle_pair_catalog(
        angle_step=int(angle_step),
        min_angle=int(min_angle),
        max_angle=int(max_angle),
        max_abs_vector_component=int(max_abs_vector_component),
        max_quantization_error=float(quantization_tolerance_degrees),
        min_vector_length_units=float(min_ray_length_units),
    )
    pairs = list(catalog.get(int(target_angle), ()))
    if not pairs:
        raise ValueError("target_angle has no primitive vector pairs")
    min_offset_units = min(
        max(
            _offset_span_units((0, int(vector_a[0]), int(vector_b[0]))),
            _offset_span_units((0, int(vector_a[1]), int(vector_b[1]))),
        )
        for vector_a, vector_b, _raw in pairs
    )
    return int(min_offset_units + 4)


@lru_cache(maxsize=512)
def _required_graph_cells_for_intersection_target(
    *,
    target_angle: int,
    min_angle: int,
    max_angle: int,
    angle_step: int,
    max_abs_vector_component: int,
    quantization_tolerance_degrees: float,
    min_ray_length_units: float,
) -> int:
    """Return minimum graph-cell count needed for one line-intersection target angle."""
    catalog = primitive_angle_pair_catalog(
        angle_step=int(angle_step),
        min_angle=int(min_angle),
        max_angle=int(max_angle),
        max_abs_vector_component=int(max_abs_vector_component),
        max_quantization_error=float(quantization_tolerance_degrees),
        min_vector_length_units=float(min_ray_length_units),
    )
    pairs = list(catalog.get(int(target_angle), ()))
    if not pairs:
        raise ValueError("target_angle has no line-intersection vector pairs")
    min_offset_units = None
    for vector_a, vector_b, _raw in pairs:
        offsets = _intersection_offsets_for_angle_source(
            vector_a=(int(vector_a[0]), int(vector_a[1])),
            vector_b=(int(vector_b[0]), int(vector_b[1])),
        )
        x_offsets = [int(offset[0]) for offset in offsets]
        y_offsets = [int(offset[1]) for offset in offsets]
        offset_units = max(_offset_span_units(x_offsets), _offset_span_units(y_offsets))
        if min_offset_units is None or int(offset_units) < int(min_offset_units):
            min_offset_units = int(offset_units)
    if min_offset_units is None:
        raise ValueError("target_angle has no line-intersection offset candidates")
    return int(min_offset_units + 2)


def _build_primitive_scene(
    rng,
    *,
    canvas_size: int,
    graph_spacing: int,
    graph_origin: Point,
    min_angle: int,
    max_angle: int,
    angle_step: int,
    quantization_tolerance_degrees: float,
    max_abs_vector_component: int,
    min_ray_length_units: float,
    target_angle: int,
    line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    draw,
    scene_scale: int,
    shape_style: GeometryShapeStyle,
) -> Dict[str, Any]:
    """Sample/draw a primitive-angle scene and return trace-ready payloads."""
    sample = sample_primitive_angle(
        rng,
        canvas_size=int(canvas_size),
        graph_spacing=int(graph_spacing),
        graph_origin=(float(graph_origin[0]), float(graph_origin[1])),
        min_angle=int(min_angle),
        max_angle=int(max_angle),
        angle_step=int(angle_step),
        max_quantization_error=float(quantization_tolerance_degrees),
        max_abs_vector_component=int(max_abs_vector_component),
        min_vector_length_units=float(min_ray_length_units),
        target_angle=int(target_angle),
    )
    point_a = scale_point(sample.point_a, int(scene_scale))
    vertex = scale_point(sample.vertex, int(scene_scale))
    point_b = scale_point(sample.point_b, int(scene_scale))
    draw_labeled_angle(
        draw,
        vertex=vertex,
        point_a=point_a,
        point_b=point_b,
        labels=sample.labels,
        line_width=max(1, int(line_width) * int(scene_scale)),
        label_offset_px=float(label_offset_px) * float(scene_scale),
        font_size_px=int(label_font_size_px),
        text_stroke_width=max(1, int(label_stroke_width)),
        line_color=tuple(int(value) for value in shape_style.line_color),
        label_color=tuple(int(value) for value in shape_style.label_color),
        label_stroke_color=tuple(int(value) for value in shape_style.label_stroke_color),
        canvas_size=int(canvas_size) * int(scene_scale),
    )
    label_a, label_v, label_b = sample.labels
    return {
        "scene_variant": "primitive_angle",
        "source_kind": "primitive_angle",
        "raw_angle_degrees": float(sample.raw_angle_degrees),
        "question_text": _angle_question_text(label_a=label_a, label_v=label_v, label_b=label_b),
        "object_description": "a labeled angle",
        "entity": {
            "entity_id": "angle_1",
            "entity_type": "angle",
            "attrs": {
                "source_kind": "primitive_angle",
                "angle_degrees": int(sample.angle_degrees),
                "raw_angle_degrees": float(sample.raw_angle_degrees),
                "labels": [str(label_a), str(label_v), str(label_b)],
                "points": {
                    "arm_a": [float(sample.point_a[0]), float(sample.point_a[1])],
                    "vertex": [float(sample.vertex[0]), float(sample.vertex[1])],
                    "arm_b": [float(sample.point_b[0]), float(sample.point_b[1])],
                },
            },
        },
        "anchor": {
            "point": [float(sample.vertex[0]), float(sample.vertex[1])],
            "polyline": [
                [float(sample.point_a[0]), float(sample.point_a[1])],
                [float(sample.vertex[0]), float(sample.vertex[1])],
                [float(sample.point_b[0]), float(sample.point_b[1])],
            ],
            "coord_space": "pixel",
        },
        "evidence_points": [
            (float(sample.point_a[0]), float(sample.point_a[1])),
            (float(sample.vertex[0]), float(sample.vertex[1])),
            (float(sample.point_b[0]), float(sample.point_b[1])),
        ],
        "target_labels": [str(label_a), str(label_v), str(label_b)],
    }


def _build_intersection_scene(
    rng,
    *,
    canvas_size: int,
    graph_spacing: int,
    graph_origin: Point,
    min_angle: int,
    max_angle: int,
    angle_step: int,
    quantization_tolerance_degrees: float,
    max_abs_vector_component: int,
    min_ray_length_units: float,
    target_angle: int,
    line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    draw,
    scene_scale: int,
    shape_style: GeometryShapeStyle,
) -> Dict[str, Any]:
    """Sample/draw one line-intersection scene and return trace-ready payloads."""
    catalog = primitive_angle_pair_catalog(
        angle_step=int(angle_step),
        min_angle=int(min_angle),
        max_angle=int(max_angle),
        max_quantization_error=float(quantization_tolerance_degrees),
        max_abs_vector_component=int(max_abs_vector_component),
        min_vector_length_units=float(min_ray_length_units),
    )
    if int(target_angle) not in set(catalog.keys()):
        raise ValueError("target_angle not feasible for line-intersection construction")
    pairs = list(catalog[int(target_angle)])
    if not pairs:
        raise ValueError("no vector pairs available for target_angle")

    max_span_units = max(1, int(canvas_size // max(1, int(graph_spacing))) - 2)
    pair_candidates: List[Tuple[Tuple[int, int], Tuple[int, int], float, List[Tuple[int, int]]]] = []
    for vector_a, vector_b, raw_angle in pairs:
        offsets = _intersection_offsets_for_angle_source(
            vector_a=(int(vector_a[0]), int(vector_a[1])),
            vector_b=(int(vector_b[0]), int(vector_b[1])),
        )
        x_offsets = [int(offset[0]) for offset in offsets]
        y_offsets = [int(offset[1]) for offset in offsets]
        if _offset_span_units(x_offsets) > int(max_span_units) or _offset_span_units(y_offsets) > int(max_span_units):
            continue
        pair_candidates.append(
            (
                (int(vector_a[0]), int(vector_a[1])),
                (int(vector_b[0]), int(vector_b[1])),
                float(raw_angle),
                [(int(offset[0]), int(offset[1])) for offset in offsets],
            )
        )
    if not pair_candidates:
        raise ValueError("no feasible line-intersection vector candidates for current canvas/grid settings")

    for _ in range(260):
        vector_a, vector_b, raw_angle, offsets = rng.choice(pair_candidates)
        try:
            vertex = sample_lattice_point_with_offsets(
                rng,
                canvas_size=int(canvas_size),
                spacing=int(graph_spacing),
                x_offsets=[0, *[int(offset[0]) for offset in offsets]],
                y_offsets=[0, *[int(offset[1]) for offset in offsets]],
                lattice_origin=(float(graph_origin[0]), float(graph_origin[1])),
                padding=int(1 * int(graph_spacing)),
            )
        except ValueError:
            continue

        point_a = offset_point_by_grid_vector((float(vertex[0]), float(vertex[1])), vector_a, spacing=int(graph_spacing))
        point_a_opposite = offset_point_by_grid_vector(
            (float(vertex[0]), float(vertex[1])),
            (-int(vector_a[0]), -int(vector_a[1])),
            spacing=int(graph_spacing),
        )
        point_b = offset_point_by_grid_vector((float(vertex[0]), float(vertex[1])), vector_b, spacing=int(graph_spacing))
        point_b_opposite = offset_point_by_grid_vector(
            (float(vertex[0]), float(vertex[1])),
            (-int(vector_b[0]), -int(vector_b[1])),
            spacing=int(graph_spacing),
        )

        line_px = max(1, int(line_width) * int(scene_scale))
        draw.line(
            [
                scale_point(point_a_opposite, int(scene_scale)),
                scale_point(vertex, int(scene_scale)),
                scale_point(point_a, int(scene_scale)),
            ],
            fill=tuple(int(value) for value in shape_style.line_color),
            width=int(line_px),
        )
        draw.line(
            [
                scale_point(point_b_opposite, int(scene_scale)),
                scale_point(vertex, int(scene_scale)),
                scale_point(point_b, int(scene_scale)),
            ],
            fill=tuple(int(value) for value in shape_style.line_color),
            width=int(line_px),
        )

        labels = alphabetic_labels(3, start_index=int(rng.randrange(26)))
        label_a, label_v, label_b = (str(labels[0]), str(labels[1]), str(labels[2]))
        draw_labeled_angle(
            draw,
            vertex=scale_point(vertex, int(scene_scale)),
            point_a=scale_point(point_a, int(scene_scale)),
            point_b=scale_point(point_b, int(scene_scale)),
            labels=(label_a, label_v, label_b),
            line_width=max(1, int(line_width) * int(scene_scale)),
            label_offset_px=float(label_offset_px) * float(scene_scale),
            font_size_px=int(label_font_size_px),
            text_stroke_width=max(1, int(label_stroke_width)),
            line_color=tuple(int(value) for value in shape_style.line_color),
            label_color=tuple(int(value) for value in shape_style.label_color),
            label_stroke_color=tuple(int(value) for value in shape_style.label_stroke_color),
            blocked_segments=[
                (
                    scale_point(point_a_opposite, int(scene_scale)),
                    scale_point(vertex, int(scene_scale)),
                ),
                (
                    scale_point(vertex, int(scene_scale)),
                    scale_point(point_a, int(scene_scale)),
                ),
                (
                    scale_point(point_b_opposite, int(scene_scale)),
                    scale_point(vertex, int(scene_scale)),
                ),
                (
                    scale_point(vertex, int(scene_scale)),
                    scale_point(point_b, int(scene_scale)),
                ),
            ],
            canvas_size=int(canvas_size) * int(scene_scale),
        )

        return {
            "scene_variant": "intersection_angle",
            "source_kind": _INTERSECTION_SOURCE_KIND,
            "raw_angle_degrees": float(raw_angle),
            "question_text": _angle_question_text(label_a=label_a, label_v=label_v, label_b=label_b),
            "object_description": "two intersecting line segments",
            "entity": {
                "entity_id": "intersection_1",
                "entity_type": "line_intersection",
                "attrs": {
                    "source_kind": _INTERSECTION_SOURCE_KIND,
                    "angle_degrees": int(target_angle),
                    "raw_angle_degrees": float(raw_angle),
                    "labels": [label_a, label_v, label_b],
                    "points": {
                        "line_a": [
                            [float(point_a_opposite[0]), float(point_a_opposite[1])],
                            [float(vertex[0]), float(vertex[1])],
                            [float(point_a[0]), float(point_a[1])],
                        ],
                        "line_b": [
                            [float(point_b_opposite[0]), float(point_b_opposite[1])],
                            [float(vertex[0]), float(vertex[1])],
                            [float(point_b[0]), float(point_b[1])],
                        ],
                        "target": {
                            "arm_a": [float(point_a[0]), float(point_a[1])],
                            "vertex": [float(vertex[0]), float(vertex[1])],
                            "arm_b": [float(point_b[0]), float(point_b[1])],
                        },
                    },
                },
            },
            "anchor": {
                "point": [float(vertex[0]), float(vertex[1])],
                "polyline": [
                    [float(point_a_opposite[0]), float(point_a_opposite[1])],
                    [float(vertex[0]), float(vertex[1])],
                    [float(point_a[0]), float(point_a[1])],
                ],
                "coord_space": "pixel",
            },
            "evidence_points": [
                (float(point_a[0]), float(point_a[1])),
                (float(vertex[0]), float(vertex[1])),
                (float(point_b[0]), float(point_b[1])),
            ],
            "target_labels": [label_a, label_v, label_b],
        }

    raise ValueError("failed to sample line-intersection angle scene")


@register_task
class GeometryAngleMeasure2DTask:
    """Measure one 2D angle from primitive or intersection sources."""

    task_id = "task_geometry_measurement_angle"
    domain = "geometry"
    task_group = "measurement"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic angle-measurement instance."""
        scene_rng = spawn_rng(instance_seed, "scene")

        min_angle = int(params.get("min_angle", group_default(_GEN_DEFAULTS, "min_angle", _DEFAULTS.min_angle)))
        max_angle = int(params.get("max_angle", group_default(_GEN_DEFAULTS, "max_angle", _DEFAULTS.max_angle)))
        angle_step = int(params.get("angle_step", group_default(_GEN_DEFAULTS, "angle_step", _DEFAULTS.angle_step)))
        quantization_tolerance_degrees = float(
            params.get(
                "quantization_tolerance_degrees",
                group_default(_GEN_DEFAULTS, "quantization_tolerance_degrees", _DEFAULTS.quantization_tolerance_degrees),
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
        line_width = sample_int_render_param(
            scene_rng,
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            key="line_width",
            fallback=int(_DEFAULTS.line_width),
            min_key="line_width_min",
            max_key="line_width_max",
            minimum_value=1,
        )
        label_offset_px = float(
            params.get("label_offset_px", group_default(_RENDER_DEFAULTS, "label_offset_px", _DEFAULTS.label_offset_px))
        )
        label_font_size_min, label_font_size_max = resolve_required_int_bounds(
            params,
            _RENDER_DEFAULTS,
            min_key="label_font_size_min",
            max_key="label_font_size_max",
            fallback_min=int(_DEFAULTS.label_font_size_min),
            fallback_max=int(_DEFAULTS.label_font_size_max),
            context=f"rendering defaults for {self.task_id}",
        )
        label_stroke_width = sample_int_render_param(
            scene_rng,
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            key="label_stroke_width",
            fallback=int(_DEFAULTS.label_stroke_width),
            min_key="label_stroke_width_min",
            max_key="label_stroke_width_max",
            minimum_value=1,
        )
        if float(quantization_tolerance_degrees) < 0.0:
            raise ValueError("quantization_tolerance_degrees must be >= 0")
        if int(max_abs_vector_component) < 4:
            raise ValueError("max_abs_vector_component must be >= 4")
        if float(min_ray_length_units) < 0.0:
            raise ValueError("min_ray_length_units must be >= 0")

        supported_source_kinds = [str(kind) for kind in _SOURCE_KINDS]
        catalog = primitive_angle_pair_catalog(
            angle_step=int(angle_step),
            min_angle=int(min_angle),
            max_angle=int(max_angle),
            max_quantization_error=float(quantization_tolerance_degrees),
            max_abs_vector_component=int(max_abs_vector_component),
            min_vector_length_units=float(min_ray_length_units),
        )
        angle_candidates = sorted(int(value) for value in catalog.keys())
        if not angle_candidates:
            raise ValueError("no feasible target angles for configured geometry constraints")
        source_kind, source_kind_probabilities = _resolve_source_kind(
            scene_rng,
            params=params,
        )
        if "graph_cells" in params:
            graph_cells_cap = int(params.get("graph_cells", _DEFAULTS.graph_cells_max))
        else:
            graph_cells_cap = int(
                params.get(
                    "graph_cells_max",
                    group_default(_RENDER_DEFAULTS, "graph_cells_max", _DEFAULTS.graph_cells_max),
                )
            )
        primitive_offset_limit = max(1, int(graph_cells_cap) - 4)
        shape_offset_limit = max(1, int(graph_cells_cap) - 2)

        def _resolve_source_candidates(kind: str) -> List[int]:
            resolved_kind = str(kind)
            if resolved_kind == "primitive_angle":
                primitive_candidates = list(
                    _primitive_feasible_angles_for_offset_limit(
                        min_angle=int(min_angle),
                        max_angle=int(max_angle),
                        angle_step=int(angle_step),
                        max_abs_vector_component=int(max_abs_vector_component),
                        quantization_tolerance_degrees=float(quantization_tolerance_degrees),
                        min_ray_length_units=float(min_ray_length_units),
                        max_offset_units=int(primitive_offset_limit),
                    )
                )
                return [int(value) for value in primitive_candidates] if primitive_candidates else list(angle_candidates)
            if resolved_kind == _INTERSECTION_SOURCE_KIND:
                intersection_candidates = list(
                    _intersection_feasible_angles_for_offset_limit(
                        min_angle=int(min_angle),
                        max_angle=int(max_angle),
                        angle_step=int(angle_step),
                        max_abs_vector_component=int(max_abs_vector_component),
                        quantization_tolerance_degrees=float(quantization_tolerance_degrees),
                        min_ray_length_units=float(min_ray_length_units),
                        max_offset_units=int(shape_offset_limit),
                    )
                )
                return [int(value) for value in intersection_candidates] if intersection_candidates else list(angle_candidates)
            raise ValueError(f"unsupported source_kind: {resolved_kind}")

        target_candidates_for_source = _resolve_source_candidates(str(source_kind))
        target_angle, target_angle_probabilities = _resolve_target_angle(
            scene_rng,
            params=params,
            min_angle=int(min_angle),
            max_angle=int(max_angle),
            angle_step=int(angle_step),
            candidate_values=target_candidates_for_source,
        )
        (
            source_kind,
            source_kind_probabilities,
            target_angle,
            target_angle_probabilities,
        ) = _resolve_balanced_source_and_target(
            instance_seed=int(instance_seed),
            params=params,
            source_kind=str(source_kind),
            source_kind_probabilities=source_kind_probabilities,
            supported_source_kinds=supported_source_kinds,
            target_angle=int(target_angle),
            target_angle_probabilities=target_angle_probabilities,
            angle_candidates=target_candidates_for_source,
        )
        target_candidates_for_source = _resolve_source_candidates(str(source_kind))
        if int(target_angle) not in set(target_candidates_for_source):
            sampling_index = params.get("_sampling_index", instance_seed)
            selected = int(target_candidates_for_source[abs(int(sampling_index)) % len(target_candidates_for_source)])
            target_angle = int(selected)
            target_angle_probabilities = {
                str(value): (1.0 if int(value) == int(selected) else 0.0) for value in target_candidates_for_source
            }
        required_graph_cells = None
        if str(source_kind) == "primitive_angle":
            required_graph_cells = _required_graph_cells_for_primitive_target(
                target_angle=int(target_angle),
                min_angle=int(min_angle),
                max_angle=int(max_angle),
                angle_step=int(angle_step),
                max_abs_vector_component=int(max_abs_vector_component),
                quantization_tolerance_degrees=float(quantization_tolerance_degrees),
                min_ray_length_units=float(min_ray_length_units),
            )
        elif str(source_kind) == _INTERSECTION_SOURCE_KIND:
            required_graph_cells = _required_graph_cells_for_intersection_target(
                target_angle=int(target_angle),
                min_angle=int(min_angle),
                max_angle=int(max_angle),
                angle_step=int(angle_step),
                max_abs_vector_component=int(max_abs_vector_component),
                quantization_tolerance_degrees=float(quantization_tolerance_degrees),
                min_ray_length_units=float(min_ray_length_units),
            )
        else:
            raise ValueError(f"unsupported source_kind: {source_kind}")
        context_params = dict(params)
        if "graph_cells" in context_params:
            fixed_cells = int(context_params.get("graph_cells", 0))
            if int(fixed_cells) < int(required_graph_cells):
                raise ValueError("graph_cells is too small for the selected angle/source geometry")
        else:
            current_min_cells = int(
                context_params.get(
                    "graph_cells_min",
                    group_default(_RENDER_DEFAULTS, "graph_cells_min", _DEFAULTS.graph_cells_min),
                )
            )
            current_max_cells = int(
                context_params.get(
                    "graph_cells_max",
                    group_default(_RENDER_DEFAULTS, "graph_cells_max", _DEFAULTS.graph_cells_max),
                )
            )
            resolved_min_cells = max(int(current_min_cells), int(required_graph_cells))
            resolved_max_cells = max(int(current_max_cells), int(resolved_min_cells))
            context_params["graph_cells_min"] = int(resolved_min_cells)
            context_params["graph_cells_max"] = int(resolved_max_cells)
        context = None
        image = None
        background_meta = None
        shape_style = None
        label_font_size_px = None
        label_stroke_width_scene = None
        scene_payload: Dict[str, Any] | None = None
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
            label_font_size_px_attempt = int(
                params.get(
                    "label_font_size_px",
                    resolve_scene_label_font_size_px(
                        canvas_size=int(context_attempt.canvas_size),
                        graph_spacing=int(context_attempt.graph_spacing),
                        scene_scale=int(context_attempt.scene_scale),
                        min_px=int(label_font_size_min),
                        max_px=int(label_font_size_max),
                    ),
                )
            )
            if int(label_font_size_px_attempt) < 6:
                raise ValueError("label_font_size_px must be >= 6")
            label_stroke_width_scene_attempt = int(max(1, int(label_stroke_width) * int(context_attempt.scene_scale)))
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
                if str(source_kind) == "primitive_angle":
                    scene_payload = _build_primitive_scene(
                        scene_rng,
                        canvas_size=int(context_attempt.canvas_size),
                        graph_spacing=int(context_attempt.graph_spacing),
                        graph_origin=(float(context_attempt.graph_origin[0]), float(context_attempt.graph_origin[1])),
                        min_angle=int(min_angle),
                        max_angle=int(max_angle),
                        angle_step=int(angle_step),
                        quantization_tolerance_degrees=float(quantization_tolerance_degrees),
                        max_abs_vector_component=int(max_abs_vector_component),
                        min_ray_length_units=float(min_ray_length_units),
                        target_angle=int(target_angle),
                        line_width=int(line_width),
                        label_offset_px=float(label_offset_px),
                        label_font_size_px=int(label_font_size_px_attempt),
                        label_stroke_width=int(label_stroke_width_scene_attempt),
                        draw=draw_attempt,
                        scene_scale=int(context_attempt.scene_scale),
                        shape_style=shape_style_attempt,
                    )
                elif str(source_kind) == _INTERSECTION_SOURCE_KIND:
                    scene_payload = _build_intersection_scene(
                        scene_rng,
                        canvas_size=int(context_attempt.canvas_size),
                        graph_spacing=int(context_attempt.graph_spacing),
                        graph_origin=(float(context_attempt.graph_origin[0]), float(context_attempt.graph_origin[1])),
                        min_angle=int(min_angle),
                        max_angle=int(max_angle),
                        angle_step=int(angle_step),
                        quantization_tolerance_degrees=float(quantization_tolerance_degrees),
                        max_abs_vector_component=int(max_abs_vector_component),
                        min_ray_length_units=float(min_ray_length_units),
                        target_angle=int(target_angle),
                        line_width=int(line_width),
                        label_offset_px=float(label_offset_px),
                        label_font_size_px=int(label_font_size_px_attempt),
                        label_stroke_width=int(label_stroke_width_scene_attempt),
                        draw=draw_attempt,
                        scene_scale=int(context_attempt.scene_scale),
                        shape_style=shape_style_attempt,
                    )
                else:
                    raise ValueError(f"unsupported source_kind: {source_kind}")
                context = context_attempt
                image = image_attempt
                background_meta = background_meta_attempt
                shape_style = shape_style_attempt
                label_font_size_px = int(label_font_size_px_attempt)
                label_stroke_width_scene = int(label_stroke_width_scene_attempt)
                break
            except Exception as exc:  # bounded retry path
                last_error = exc
                continue
        if scene_payload is None or context is None or image is None or background_meta is None or shape_style is None:
            raise RuntimeError("failed to generate task_geometry_measurement_angle instance") from last_error

        question_text = str(scene_payload["question_text"])

        evidence_points = scene_payload.get("evidence_points", [])
        if not isinstance(evidence_points, list) or len(evidence_points) != 3:
            raise RuntimeError("angle evidence points must include [ray_endpoint_a, vertex, ray_endpoint_b]")
        target_labels = [str(label) for label in scene_payload.get("target_labels", [])]
        if len(target_labels) != 3:
            raise RuntimeError("angle evidence labels must include exactly three labels")
        evidence_points_by_label = {
            str(target_labels[0]): evidence_points[0],
            str(target_labels[1]): evidence_points[1],
            str(target_labels[2]): evidence_points[2],
        }
        evidence = graph_point_set_evidence_artifacts(
            points_by_label=evidence_points_by_label,
            graph_origin=context.graph_origin,
            graph_spacing=int(context.graph_spacing),
            witness_type="angle_triplet",
            ordered_labels=list(target_labels),
        )
        evidence_value = evidence.get("evidence_value", [])
        if (
            not isinstance(evidence_value, list)
            or len(evidence_value) != 3
            or any(not isinstance(point, list) or len(point) != 2 for point in evidence_value)
            or any(not isinstance(coord, int) for point in evidence_value for coord in point)
        ):
            raise RuntimeError("angle triplet evidence must include three integer graph-lattice points")

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
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_bundle_id = str(prompt_defaults["bundle_id"])
        prompt_task_family_key = str(prompt_defaults["task_family_key"])
        prompt_task_key = str(prompt_defaults["task_key"])
        json_output_contract = str(prompt_defaults["json_output_contract"])
        json_output_contract_answer_only = str(prompt_defaults["json_output_contract_answer_only"])
        evidence_hint = str(prompt_defaults["evidence_hint"])
        answer_hint = str(prompt_defaults["answer_hint"])
        json_example = str(prompt_defaults["json_example"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=prompt_bundle_id,
            task_family_key=prompt_task_family_key,
            task_key=prompt_task_key,
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(scene_payload["object_description"]),
                "question_text": str(question_text),
                "json_output_contract": str(json_output_contract),
                "json_output_contract_answer_only": str(json_output_contract_answer_only),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(answer_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        raw_angle_degrees = float(scene_payload["raw_angle_degrees"])
        answer_value = int(target_angle)
        if abs(float(raw_angle_degrees) - float(answer_value)) > 0.05 + 1e-9:
            raise RuntimeError("resolved angle exceeds nearest-integer rounding tolerance")
        scene_variant_value = str(scene_payload["scene_variant"])
        source_kind_value = str(scene_payload["source_kind"])
        task_variant_probabilities: Dict[str, float] = {}
        for source_kind_key, probability in source_kind_probabilities.items():
            variant_key = _scene_variant_for_source_kind(str(source_kind_key))
            task_variant_probabilities[str(variant_key)] = float(task_variant_probabilities.get(str(variant_key), 0.0)) + float(probability)
        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_2d_angle_measurement",
                "entities": [dict(scene_payload["entity"])],
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
                "task_variant": str(scene_variant_value),
                "template_id": "geometry_angle_measure_v1",
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(scene_variant_value),
                    "source_kind": str(source_kind_value),
                    "source_kind_probabilities": dict(source_kind_probabilities),
                    "target_angle": int(target_angle),
                    "target_angle_probabilities": dict(target_angle_probabilities),
                    "angle_step": int(angle_step),
                    "quantization_tolerance_degrees": float(quantization_tolerance_degrees),
                    "max_abs_vector_component": int(max_abs_vector_component),
                    "min_ray_length_units": float(min_ray_length_units),
                    "min_angle": int(min_angle),
                    "max_angle": int(max_angle),
                    "answer_rounding": "nearest_integer_degree",
                    "required_graph_cells": int(required_graph_cells),
                },
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
            "render_map": {"image_id": "img0", "anchors": {"target": dict(scene_payload["anchor"])}},
            "execution_trace": {
                "scene_variant": str(scene_variant_value),
                "source_kind": str(source_kind_value),
                "target_angle": int(target_angle),
                "answer_value": int(answer_value),
                "raw_angle_degrees": float(raw_angle_degrees),
                "angle_degrees": int(answer_value),
                "target_labels": list(scene_payload["target_labels"]),
                "required_evidence_labels": list(target_labels),
                "question_format": "numeric_open",
                "feasible_target_angles": [int(value) for value in target_candidates_for_source],
                "feasible_answer_values": [int(value) for value in target_candidates_for_source],
                "task_variant_probabilities": {str(key): float(value) for key, value in sorted(task_variant_probabilities.items())},
            },
            "witness_symbolic": dict(evidence["witness_symbolic"]),
            "projected_evidence": dict(evidence["projected_evidence"]),
        }

        complexity = TaskComplexity(
            complexity_score=_complexity_score(source_kind=source_kind_value, angle_degrees=answer_value),
            complexity_components={
                "scene_variant": str(scene_variant_value),
                "source_kind": str(source_kind_value),
                "angle_degrees": int(answer_value),
            },
        )

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(answer_value)),
            evidence_gt=TypedValue(type=str(evidence["evidence_type"]), value=evidence["evidence_value"]),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(scene_variant_value),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
