"""Geometry graphing-count task over simple plotted functions on graph paper."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ....core.sampling import normalize_positive_weights, weighted_choice
from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import resolve_scene_label_font_size_px
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.background_defaults import load_geometry_background_defaults
from ..shared.complexity import build_geometry_graphing_complexity
from ..shared.fixed_query_task import FixedGeometryQueryTaskMixin, MultiFixedGeometryQueryTaskMixin
from ..shared.function_graph_scene import (
    build_query_line_color,
    draw_function_polyline,
    draw_horizontal_query_line,
    graph_units_to_pixel_float,
)
from ..shared.graph_rendering import graph_paper_grid_from_frame
from ..shared.labeled_point_evidence import (
    empty_graph_point_set_evidence_artifacts,
    graph_point_set_evidence_artifacts,
)
from ..shared.noise_defaults import load_geometry_noise_defaults
from ..shared.shape_style import (
    extract_background_anchor_colors,
    sample_geometry_shape_style,
)
from ..shared.single_object_scene import (
    GraphSceneContext,
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)


TASK_ID = "geometry_graphing_count_base"

REFERENCE_LINE_CROSSING_COUNT = "reference_line_crossing_count"
TURNING_POINT_COUNT = "turning_point_count"
LOCAL_EXTREMUM_COUNT = "local_extremum_count"

X_AXIS_REFERENCE_LINE = "x_axis"
HORIZONTAL_REFERENCE_LINE = "horizontal_line"
SUPPORTED_REFERENCE_LINE_KINDS: Tuple[str, ...] = (
    X_AXIS_REFERENCE_LINE,
    HORIZONTAL_REFERENCE_LINE,
)
MINIMUM_EXTREMUM = "minimum"
MAXIMUM_EXTREMUM = "maximum"
SUPPORTED_EXTREMUM_KINDS: Tuple[str, ...] = (
    MINIMUM_EXTREMUM,
    MAXIMUM_EXTREMUM,
)

SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "quadratic",
    "absolute_value",
    "cubic",
    "sinusoid",
    "piecewise_linear",
)
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    REFERENCE_LINE_CROSSING_COUNT,
    TURNING_POINT_COUNT,
    LOCAL_EXTREMUM_COUNT,
)
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "quadratic": (REFERENCE_LINE_CROSSING_COUNT,),
    "absolute_value": (REFERENCE_LINE_CROSSING_COUNT,),
    "cubic": (REFERENCE_LINE_CROSSING_COUNT,),
    "sinusoid": (
        REFERENCE_LINE_CROSSING_COUNT,
        TURNING_POINT_COUNT,
        LOCAL_EXTREMUM_COUNT,
    ),
    "piecewise_linear": (
        REFERENCE_LINE_CROSSING_COUNT,
        TURNING_POINT_COUNT,
        LOCAL_EXTREMUM_COUNT,
    ),
}

POST_IMAGE_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="graphing")
POST_IMAGE_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="graphing")

GraphPoint = Tuple[int, int]
GraphPolylinePoint = Tuple[float, float]
_TARGET_COUNT_BALANCE_SALT = 330


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallbacks for graphing-family scenes."""

    canvas_size_min: int = 640
    canvas_size_max: int = 720
    graph_cells_min: int = 20
    graph_cells_max: int = 20
    line_width: int = 4
    guide_line_width: int = 3
    label_font_size_min: int = 16
    label_font_size_max: int = 24
    quadratic_reference_line_crossing_support: Tuple[int, ...] = (2,)
    absolute_value_reference_line_crossing_support: Tuple[int, ...] = (2,)
    cubic_reference_line_crossing_support: Tuple[int, ...] = (2, 3)
    sinusoid_reference_line_crossing_support: Tuple[int, ...] = (3, 4)
    sinusoid_turning_support: Tuple[int, ...] = (3, 4)
    sinusoid_local_extremum_support: Tuple[int, ...] = (2,)
    piecewise_reference_line_crossing_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    piecewise_turning_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    piecewise_local_extremum_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    horizontal_line_support: Tuple[int, ...] = (-4, -3, -2, -1, 1, 2, 3, 4)
    piecewise_intersection_x_positions: Tuple[int, ...] = (-9, -7, -5, -3, -2, -1, 0, 1, 2, 3, 5, 7, 9)
    piecewise_turning_x_positions: Tuple[int, ...] = (-9, -7, -5, -3, -2, -1, 0, 1, 2, 3, 5, 7, 9)


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved scene/query axes plus one balanced count target."""

    scene_variant: str
    query_variant: str
    reference_line_kind: str | None
    extremum_kind: str | None
    target_count: int
    scene_variant_probabilities: Dict[str, float]
    query_variant_probabilities: Dict[str, float]
    reference_line_kind_probabilities: Dict[str, float]
    extremum_kind_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _SampledGraphScene:
    """One sampled plotted-function scene before raster rendering."""

    polyline_graph: Tuple[GraphPolylinePoint, ...]
    evidence_graph_points: Tuple[GraphPoint, ...]
    query_line_y: int | None
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]
    execution_trace: Dict[str, Any]
    object_count: int


@dataclass(frozen=True)
class _RenderedGraphScene:
    """Rendered scene plus prompt-facing graph-point evidence artifacts."""

    answer_value: int
    evidence_type: str
    evidence_value: List[List[float]]
    projected_evidence: Dict[str, Any]
    witness_symbolic: Dict[str, Any]
    required_evidence_labels: List[str]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]
    execution_trace: Dict[str, Any]
    object_count: int


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "graphing")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _int_tuple_default(
    defaults: Mapping[str, Any],
    key: str,
    fallback: Sequence[int],
) -> Tuple[int, ...]:
    """Resolve one integer sequence from task-group defaults."""

    raw_value = defaults.get(str(key), fallback)
    if not isinstance(raw_value, Sequence) or isinstance(raw_value, (str, bytes)):
        raise ValueError(f"{key} must be a sequence of integers for {TASK_ID}")
    values = tuple(int(value) for value in raw_value)
    if not values:
        raise ValueError(f"{key} cannot be empty for {TASK_ID}")
    return values


def _count_target_support(*, scene_variant: str, query_variant: str) -> Tuple[int, ...]:
    """Return supported count answers for one compatible scene/query pair."""

    support_map = {
        ("quadratic", REFERENCE_LINE_CROSSING_COUNT): _int_tuple_default(
            _GEN_DEFAULTS,
            "quadratic_reference_line_crossing_support",
            _DEFAULTS.quadratic_reference_line_crossing_support,
        ),
        ("absolute_value", REFERENCE_LINE_CROSSING_COUNT): _int_tuple_default(
            _GEN_DEFAULTS,
            "absolute_value_reference_line_crossing_support",
            _DEFAULTS.absolute_value_reference_line_crossing_support,
        ),
        ("cubic", REFERENCE_LINE_CROSSING_COUNT): _int_tuple_default(
            _GEN_DEFAULTS,
            "cubic_reference_line_crossing_support",
            _DEFAULTS.cubic_reference_line_crossing_support,
        ),
        ("sinusoid", REFERENCE_LINE_CROSSING_COUNT): _int_tuple_default(
            _GEN_DEFAULTS,
            "sinusoid_reference_line_crossing_support",
            _DEFAULTS.sinusoid_reference_line_crossing_support,
        ),
        ("sinusoid", TURNING_POINT_COUNT): _int_tuple_default(
            _GEN_DEFAULTS,
            "sinusoid_turning_support",
            _DEFAULTS.sinusoid_turning_support,
        ),
        ("sinusoid", LOCAL_EXTREMUM_COUNT): _int_tuple_default(
            _GEN_DEFAULTS,
            "sinusoid_local_extremum_support",
            _DEFAULTS.sinusoid_local_extremum_support,
        ),
        ("piecewise_linear", REFERENCE_LINE_CROSSING_COUNT): _int_tuple_default(
            _GEN_DEFAULTS,
            "piecewise_reference_line_crossing_support",
            _DEFAULTS.piecewise_reference_line_crossing_support,
        ),
        ("piecewise_linear", TURNING_POINT_COUNT): _int_tuple_default(
            _GEN_DEFAULTS,
            "piecewise_turning_support",
            _DEFAULTS.piecewise_turning_support,
        ),
        ("piecewise_linear", LOCAL_EXTREMUM_COUNT): _int_tuple_default(
            _GEN_DEFAULTS,
            "piecewise_local_extremum_support",
            _DEFAULTS.piecewise_local_extremum_support,
        ),
    }
    key = (str(scene_variant).strip().lower(), str(query_variant).strip().lower())
    support = support_map.get(key)
    if support is None:
        raise ValueError(f"unsupported graphing scene/query pair: {scene_variant} x {query_variant}")
    return tuple(int(value) for value in support)


def _full_probability_map(supported: Sequence[str], probabilities: Mapping[str, float]) -> Dict[str, float]:
    """Expand one restricted probability map over the full supported domain."""

    positive = {str(key): float(value) for key, value in probabilities.items()}
    return {
        str(key): float(positive.get(str(key), 0.0))
        for key in supported
    }


def _query_target_support(query_variant: str) -> Tuple[int, ...]:
    """Return the union count support for one query across compatible scene families."""

    supports = {
        int(value)
        for scene_variant, query_variants in COMPATIBILITY.items()
        if str(query_variant) in set(str(item) for item in query_variants)
        for value in _count_target_support(scene_variant=str(scene_variant), query_variant=str(query_variant))
    }
    if not supports:
        raise ValueError(f"unsupported graphing query_variant: {query_variant}")
    return tuple(sorted(int(value) for value in supports))


def _resolve_target_count(
    rng,
    *,
    instance_seed: int,
    support: Sequence[int],
    selection_namespace: str,
    params: Mapping[str, Any],
) -> Tuple[int, Dict[str, float]]:
    """Resolve one balanced count answer inside the feasible support.

    We intentionally use a second deterministic salt for target-count cycling
    so it stays decoupled from the separate query-variant balancing stream
    during review collection.
    """

    support = tuple(int(value) for value in support)
    explicit = params.get("target_count")
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"unsupported target_count: {selected}")
        return int(selected), uniform_probability_map(support, selected=int(selected))

    raw_weights = params.get("target_count_weights", {str(value): 1.0 for value in support})
    if not isinstance(raw_weights, Mapping):
        raise ValueError("target_count_weights must be a mapping when provided")
    weights = {
        str(key): float(value)
        for key, value in raw_weights.items()
        if int(key) in set(support)
    }
    probabilities = normalize_positive_weights(weights, default_keys=[str(value) for value in support])
    selected = int(weighted_choice(rng, probabilities, sort_keys=True))

    balanced_enabled = bool(params.get("balanced_sampling", group_default(_GEN_DEFAULTS, "balanced_sampling", True)))
    overridden = any(params.get(key) is not None for key in ("target_count", "target_count_weights"))
    if balanced_enabled and (not overridden):
        ordered_support = [int(value) for value in support]
        selection_index = abs(
            int(hash64(int(instance_seed), str(selection_namespace), _TARGET_COUNT_BALANCE_SALT))
        )
        selected = int(ordered_support[selection_index % len(ordered_support)])
    return int(selected), {
        str(key): float(value)
        for key, value in sorted(probabilities.items(), key=lambda item: int(item[0]))
    }


def _decoupled_scene_sampling_params(*, params: Mapping[str, Any], selection_namespace: str) -> Mapping[str, Any]:
    """No-op hook for scene-cycling call sites."""

    _ = selection_namespace
    return params


def _resolve_parameter_axis(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    supported_values: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one query-parameter axis with optional deterministic balancing."""

    selected, restricted_probs = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=supported_values,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=restricted_probs,
        supported_variants=supported_values,
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{TASK_ID}.{explicit_key}",
    )
    return str(selected), _full_probability_map(supported_values, restricted_probs)


def _resolve_query_parameters(
    rng,
    *,
    instance_seed: int,
    query_variant: str,
    params: Mapping[str, Any],
) -> Tuple[str | None, Dict[str, float], str | None, Dict[str, float]]:
    """Resolve parameter axes that are meaningful for the selected query variant."""

    normalized_query = str(query_variant).strip().lower()
    has_reference_line_kind = params.get("reference_line_kind") is not None
    has_extremum_kind = params.get("extremum_kind") is not None

    if normalized_query == REFERENCE_LINE_CROSSING_COUNT:
        if bool(has_extremum_kind):
            raise ValueError("extremum_kind is only supported for local_extremum_count")
        reference_line_kind, reference_line_probs = _resolve_parameter_axis(
            rng,
            instance_seed=int(instance_seed),
            params=params,
            supported_values=SUPPORTED_REFERENCE_LINE_KINDS,
            explicit_key="reference_line_kind",
            weights_key="reference_line_kind_weights",
            balance_flag_key="balanced_reference_line_kind_sampling",
        )
        return str(reference_line_kind), dict(reference_line_probs), None, {}

    if normalized_query == LOCAL_EXTREMUM_COUNT:
        if bool(has_reference_line_kind):
            raise ValueError("reference_line_kind is only supported for reference_line_crossing_count")
        extremum_kind, extremum_probs = _resolve_parameter_axis(
            rng,
            instance_seed=int(instance_seed),
            params=params,
            supported_values=SUPPORTED_EXTREMUM_KINDS,
            explicit_key="extremum_kind",
            weights_key="extremum_kind_weights",
            balance_flag_key="balanced_extremum_kind_sampling",
        )
        return None, {}, str(extremum_kind), dict(extremum_probs)

    if normalized_query == TURNING_POINT_COUNT:
        if bool(has_reference_line_kind):
            raise ValueError("reference_line_kind is only supported for reference_line_crossing_count")
        if bool(has_extremum_kind):
            raise ValueError("extremum_kind is only supported for local_extremum_count")
        return None, {}, None, {}

    raise ValueError(f"unsupported graphing query_variant: {query_variant}")


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve the chart-style scene/query surface and one count target."""

    axis_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.axes")
    scene_supported = [str(value) for value in SUPPORTED_SCENE_VARIANTS]
    query_supported = [str(value) for value in SUPPORTED_QUERY_VARIANTS]
    compatibility_map = {
        str(scene): tuple(str(query) for query in queries)
        for scene, queries in COMPATIBILITY.items()
    }
    explicit_scene = params.get("scene_variant")
    explicit_query = params.get("query_variant", params.get("query_variant"))
    if explicit_scene is not None and str(explicit_scene) not in set(scene_supported):
        raise ValueError(f"unsupported scene_variant: {explicit_scene}")
    if explicit_query is not None and str(explicit_query) not in set(query_supported):
        raise ValueError(f"unsupported query_variant: {explicit_query}")

    if explicit_scene is not None and explicit_query is not None:
        if str(explicit_query) not in set(compatibility_map.get(str(explicit_scene), ())):
            raise ValueError(f"incompatible geometry scene/query combination: {explicit_scene} + {explicit_query}")
        scene_variant = str(explicit_scene)
        query_variant = str(explicit_query)
        scene_probs = _full_probability_map(scene_supported, {scene_variant: 1.0})
        query_probs = _full_probability_map(query_supported, {query_variant: 1.0})
        support = _count_target_support(scene_variant=scene_variant, query_variant=query_variant)
    else:
        if explicit_query is None:
            selected_query, restricted_query_probs = resolve_variant(
                axis_rng,
                params=params,
                gen_defaults=_GEN_DEFAULTS,
                supported_variants=query_supported,
                explicit_key="query_variant",
                weights_key="query_variant_weights",
            )
            query_variant = apply_balanced_variant_sampling(
                instance_seed=int(instance_seed),
                params=params,
                gen_defaults=_GEN_DEFAULTS,
                selected_variant=str(selected_query),
                variant_probabilities=restricted_query_probs,
                supported_variants=query_supported,
                balance_flag_key="balanced_query_variant_sampling",
                explicit_key="query_variant",
                weights_key="query_variant_weights",
                sampling_namespace=f"{TASK_ID}.query_variant",
            )
            query_probs = _full_probability_map(query_supported, restricted_query_probs)
        else:
            query_variant = str(explicit_query)
            query_probs = _full_probability_map(query_supported, {query_variant: 1.0})

        if explicit_scene is not None:
            scene_variant = str(explicit_scene)
            if str(query_variant) not in set(compatibility_map.get(scene_variant, ())):
                raise ValueError(f"incompatible geometry scene/query combination: {scene_variant} + {query_variant}")
            scene_probs = _full_probability_map(scene_supported, {scene_variant: 1.0})
            support = _count_target_support(scene_variant=scene_variant, query_variant=query_variant)
        else:
            support = _query_target_support(query_variant)
            target_count, target_count_probs = _resolve_target_count(
                axis_rng,
                instance_seed=int(instance_seed),
                support=support,
                selection_namespace=f"{TASK_ID}.target_count.{query_variant}",
                params=params,
            )
            allowed_scenes = [
                scene
                for scene in scene_supported
                if str(query_variant) in set(compatibility_map.get(scene, ()))
                and int(target_count) in set(_count_target_support(scene_variant=scene, query_variant=query_variant))
            ]
            selected_scene, restricted_scene_probs = resolve_variant(
                axis_rng,
                params=params,
                gen_defaults=_GEN_DEFAULTS,
                supported_variants=allowed_scenes,
                explicit_key="scene_variant",
                weights_key="scene_variant_weights",
            )
            scene_sampling_params = _decoupled_scene_sampling_params(
                params=params,
                selection_namespace=f"{TASK_ID}.scene_variant.{query_variant}.{target_count}",
            )
            scene_variant = apply_balanced_variant_sampling(
                instance_seed=int(instance_seed),
                params=scene_sampling_params,
                gen_defaults=_GEN_DEFAULTS,
                selected_variant=str(selected_scene),
                variant_probabilities=restricted_scene_probs,
                supported_variants=allowed_scenes,
                balance_flag_key="balanced_scene_variant_sampling",
                explicit_key="scene_variant",
                weights_key="scene_variant_weights",
                sampling_namespace=f"{TASK_ID}.scene_variant",
            )
            scene_probs = _full_probability_map(scene_supported, restricted_scene_probs)
            reference_line_kind, reference_line_probs, extremum_kind, extremum_probs = _resolve_query_parameters(
                axis_rng,
                instance_seed=int(instance_seed),
                query_variant=str(query_variant),
                params=params,
            )
            return _ResolvedQuery(
                scene_variant=str(scene_variant),
                query_variant=str(query_variant),
                reference_line_kind=reference_line_kind,
                extremum_kind=extremum_kind,
                target_count=int(target_count),
                scene_variant_probabilities=dict(scene_probs),
                query_variant_probabilities=dict(query_probs),
                reference_line_kind_probabilities=dict(reference_line_probs),
                extremum_kind_probabilities=dict(extremum_probs),
                target_count_probabilities=dict(target_count_probs),
            )

    target_count, target_count_probs = _resolve_target_count(
        axis_rng,
        instance_seed=int(instance_seed),
        support=support,
        selection_namespace=f"{TASK_ID}.target_count.{scene_variant}.{query_variant}",
        params=params,
    )
    reference_line_kind, reference_line_probs, extremum_kind, extremum_probs = _resolve_query_parameters(
        axis_rng,
        instance_seed=int(instance_seed),
        query_variant=str(query_variant),
        params=params,
    )
    return _ResolvedQuery(
        scene_variant=str(scene_variant),
        query_variant=str(query_variant),
        reference_line_kind=reference_line_kind,
        extremum_kind=extremum_kind,
        target_count=int(target_count),
        scene_variant_probabilities=dict(scene_probs),
        query_variant_probabilities=dict(query_probs),
        reference_line_kind_probabilities=dict(reference_line_probs),
        extremum_kind_probabilities=dict(extremum_probs),
        target_count_probabilities=dict(target_count_probs),
    )


def _sample_from(values: Sequence[int], rng) -> int:
    """Choose one integer from a non-empty sequence."""

    if not values:
        raise ValueError("sampling support cannot be empty")
    return int(values[int(rng.randrange(len(values)))])


def _quadratic_sample_points(*, a_value: int, h_value: int, k_value: int) -> Tuple[GraphPolylinePoint, ...]:
    """Return dense sample points for a quadratic graph."""

    return tuple(
        (
            float(x_value) / 4.0,
            float(a_value * (((float(x_value) / 4.0) - float(h_value)) ** 2) + float(k_value)),
        )
        for x_value in range(-32, 33)
    )


def _build_quadratic_scene(
    rng,
    *,
    query_variant: str,
    reference_line_kind: str | None,
    target_count: int,
) -> _SampledGraphScene:
    """Sample one integer-lattice quadratic that realizes the requested count."""

    a_value = int(rng.choice((-1, 1)))
    h_value = int(rng.randint(-4, 4))
    query_line_y: int | None = None
    evidence_points: Tuple[GraphPoint, ...]

    if str(query_variant) != REFERENCE_LINE_CROSSING_COUNT:
        raise ValueError(f"unsupported quadratic query_variant: {query_variant}")

    if str(reference_line_kind) == X_AXIS_REFERENCE_LINE:
        if int(target_count) == 0:
            k_value = int(rng.randint(1, 4)) if int(a_value) > 0 else -int(rng.randint(1, 4))
            evidence_points = tuple()
        elif int(target_count) == 2:
            root_delta = int(rng.randint(1, 3))
            h_value = int(rng.randint(-6 + root_delta, 6 - root_delta))
            k_value = int(-a_value * (root_delta**2))
            evidence_points = (
                (int(h_value - root_delta), 0),
                (int(h_value + root_delta), 0),
            )
        else:
            raise ValueError(f"unsupported quadratic reference-line target_count: {target_count}")
    elif str(reference_line_kind) == HORIZONTAL_REFERENCE_LINE:
        if int(target_count) == 0:
            k_value = int(rng.randint(-3, 3))
            query_line_y = int(k_value - rng.randint(1, 3)) if int(a_value) > 0 else int(k_value + rng.randint(1, 3))
            if int(query_line_y) == 0:
                query_line_y += -1 if int(a_value) > 0 else 1
            evidence_points = tuple()
        elif int(target_count) == 2:
            root_delta = int(rng.randint(1, 3))
            h_value = int(rng.randint(-6 + root_delta, 6 - root_delta))
            k_value = int(rng.randint(-3, 3))
            query_line_y = int(k_value + (a_value * (root_delta**2)))
            if int(query_line_y) == 0:
                shift = 1 if int(query_line_y) <= 0 else -1
                k_value += shift
                query_line_y += shift
            evidence_points = (
                (int(h_value - root_delta), int(query_line_y)),
                (int(h_value + root_delta), int(query_line_y)),
            )
        else:
            raise ValueError(f"unsupported quadratic reference-line target_count: {target_count}")
    else:
        raise ValueError(f"unsupported reference_line_kind: {reference_line_kind}")

    sample_points = _quadratic_sample_points(a_value=int(a_value), h_value=int(h_value), k_value=int(k_value))
    return _SampledGraphScene(
        polyline_graph=sample_points,
        evidence_graph_points=tuple(evidence_points),
        query_line_y=(None if query_line_y is None else int(query_line_y)),
        scene_entities=[
            {
                "entity_id": "function_graph",
                "entity_type": "function_graph",
                "family": "quadratic",
                "parameters": {"a": int(a_value), "h": int(h_value), "k": int(k_value)},
            }
        ],
        render_map={
            "scene_variant": "quadratic",
            "function_parameters": {"a": int(a_value), "h": int(h_value), "k": int(k_value)},
            "evidence_points_graph": [list(point) for point in evidence_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        execution_trace={
            "family": "quadratic",
            "parameters": {"a": int(a_value), "h": int(h_value), "k": int(k_value)},
            "evidence_points_graph": [list(point) for point in evidence_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        object_count=1,
    )


def _absolute_value_sample_points(
    *,
    orientation: int,
    slope: int,
    h_value: int,
    k_value: int,
) -> Tuple[GraphPolylinePoint, ...]:
    """Return dense sample points for an absolute-value graph."""

    return tuple(
        (
            float(x_value) / 4.0,
            float((orientation * slope * abs((float(x_value) / 4.0) - float(h_value))) + float(k_value)),
        )
        for x_value in range(-32, 33)
    )


def _build_absolute_value_scene(
    rng,
    *,
    query_variant: str,
    reference_line_kind: str | None,
    target_count: int,
) -> _SampledGraphScene:
    """Sample one integer-lattice absolute-value graph that realizes the requested count."""

    orientation = int(rng.choice((-1, 1)))
    slope = int(rng.choice((1, 2)))
    h_value = int(rng.randint(-4, 4))
    query_line_y: int | None = None
    evidence_points: Tuple[GraphPoint, ...]

    if str(query_variant) != REFERENCE_LINE_CROSSING_COUNT:
        raise ValueError(f"unsupported absolute-value query_variant: {query_variant}")

    if str(reference_line_kind) == X_AXIS_REFERENCE_LINE:
        if int(target_count) == 0:
            root_distance = int(rng.randint(1, 3))
            k_value = int(orientation * slope * root_distance)
            evidence_points = tuple()
        elif int(target_count) == 2:
            root_distance = int(rng.randint(1, 3))
            h_value = int(rng.randint(-6 + root_distance, 6 - root_distance))
            k_value = int(-orientation * slope * root_distance)
            evidence_points = (
                (int(h_value - root_distance), 0),
                (int(h_value + root_distance), 0),
            )
        else:
            raise ValueError(f"unsupported absolute-value reference-line target_count: {target_count}")
    elif str(reference_line_kind) == HORIZONTAL_REFERENCE_LINE:
        if int(target_count) == 0:
            k_value = int(rng.randint(-3, 3))
            query_line_y = int(k_value - rng.randint(1, 3)) if int(orientation) > 0 else int(k_value + rng.randint(1, 3))
            if int(query_line_y) == 0:
                query_line_y += -1 if int(orientation) > 0 else 1
            evidence_points = tuple()
        elif int(target_count) == 2:
            root_distance = int(rng.randint(1, 3))
            h_value = int(rng.randint(-6 + root_distance, 6 - root_distance))
            k_value = int(rng.randint(-3, 3))
            query_line_y = int(k_value + (orientation * slope * root_distance))
            if int(query_line_y) == 0:
                shift = 1 if int(query_line_y) <= 0 else -1
                k_value += shift
                query_line_y += shift
            evidence_points = (
                (int(h_value - root_distance), int(query_line_y)),
                (int(h_value + root_distance), int(query_line_y)),
            )
        else:
            raise ValueError(f"unsupported absolute-value reference-line target_count: {target_count}")
    else:
        raise ValueError(f"unsupported reference_line_kind: {reference_line_kind}")

    sample_points = _absolute_value_sample_points(
        orientation=int(orientation),
        slope=int(slope),
        h_value=int(h_value),
        k_value=int(k_value),
    )
    return _SampledGraphScene(
        polyline_graph=sample_points,
        evidence_graph_points=tuple(evidence_points),
        query_line_y=(None if query_line_y is None else int(query_line_y)),
        scene_entities=[
            {
                "entity_id": "function_graph",
                "entity_type": "function_graph",
                "family": "absolute_value",
                "parameters": {
                    "orientation": int(orientation),
                    "slope": int(slope),
                    "h": int(h_value),
                    "k": int(k_value),
                },
            }
        ],
        render_map={
            "scene_variant": "absolute_value",
            "function_parameters": {
                "orientation": int(orientation),
                "slope": int(slope),
                "h": int(h_value),
                "k": int(k_value),
            },
            "evidence_points_graph": [list(point) for point in evidence_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        execution_trace={
            "family": "absolute_value",
            "parameters": {
                "orientation": int(orientation),
                "slope": int(slope),
                "h": int(h_value),
                "k": int(k_value),
            },
            "evidence_points_graph": [list(point) for point in evidence_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        object_count=1,
    )


def _cubic_sample_points(
    *,
    scale_value: float,
    roots: Sequence[int],
    baseline_y: int,
) -> Tuple[GraphPolylinePoint, ...]:
    """Return dense sample points for one factored cubic graph."""

    root_a, root_b, root_c = (float(value) for value in roots)
    return tuple(
        (
            float(x_value) / 4.0,
            float(
                scale_value
                * (((float(x_value) / 4.0) - root_a) * (((float(x_value) / 4.0) - root_b)) * (((float(x_value) / 4.0) - root_c)))
                + float(baseline_y)
            ),
        )
        for x_value in range(-40, 41)
    )


def _choose_distinct_integers(
    rng,
    *,
    count: int,
    support: Sequence[int],
) -> Tuple[int, ...]:
    """Choose sorted distinct integers from one finite support."""

    values = [int(value) for value in support]
    if int(count) > len(values):
        raise ValueError("requested too many distinct integers")
    rng.shuffle(values)
    return tuple(sorted(int(value) for value in values[: int(count)]))


def _cubic_roots_for_target(
    rng,
    *,
    target_count: int,
) -> Tuple[int, int, int]:
    """Return simple roots with the requested number visible in the graph window."""

    if int(target_count) not in {0, 1, 2, 3}:
        raise ValueError(f"unsupported cubic target_count: {target_count}")
    visible_support = [-7, -5, -3, -1, 1, 3, 5, 7]
    hidden_support = [-15, -13, -11, 11, 13, 15]
    visible_roots = _choose_distinct_integers(rng, count=int(target_count), support=visible_support)
    hidden_roots = _choose_distinct_integers(
        rng,
        count=int(3 - int(target_count)),
        support=hidden_support,
    )
    roots = tuple(sorted((int(value) for value in visible_roots + hidden_roots)))
    return (int(roots[0]), int(roots[1]), int(roots[2]))


def _build_cubic_scene(
    rng,
    *,
    query_variant: str,
    reference_line_kind: str | None,
    target_count: int,
) -> _SampledGraphScene:
    """Sample one factored cubic graph with integer witness coordinates."""

    roots = _cubic_roots_for_target(rng, target_count=int(target_count))
    scale_value = float(rng.choice((-0.012, -0.01, 0.01, 0.012)))
    query_line_y: int | None = None
    visible_roots = tuple(int(root) for root in roots if -9 <= int(root) <= 9)

    if str(query_variant) != REFERENCE_LINE_CROSSING_COUNT:
        raise ValueError(f"unsupported cubic query_variant: {query_variant}")

    if str(reference_line_kind) == X_AXIS_REFERENCE_LINE:
        baseline_y = 0
        evidence_points = tuple(sorted({(int(root), 0) for root in visible_roots}))
    elif str(reference_line_kind) == HORIZONTAL_REFERENCE_LINE:
        baseline_y = int(
            _sample_from(
                [value for value in _int_tuple_default(_GEN_DEFAULTS, "horizontal_line_support", _DEFAULTS.horizontal_line_support) if int(value) != 0],
                rng,
            )
        )
        query_line_y = int(baseline_y)
        evidence_points = tuple(sorted({(int(root), int(query_line_y)) for root in visible_roots}))
    else:
        raise ValueError(f"unsupported reference_line_kind: {reference_line_kind}")

    sample_points = _cubic_sample_points(
        scale_value=float(scale_value),
        roots=roots,
        baseline_y=int(baseline_y),
    )
    parameters = {
        "scale": float(scale_value),
        "roots": [int(value) for value in roots],
        "baseline_y": int(baseline_y),
    }
    return _SampledGraphScene(
        polyline_graph=sample_points,
        evidence_graph_points=tuple(evidence_points),
        query_line_y=(None if query_line_y is None else int(query_line_y)),
        scene_entities=[
            {
                "entity_id": "function_graph",
                "entity_type": "function_graph",
                "family": "cubic",
                "parameters": dict(parameters),
            }
        ],
        render_map={
            "scene_variant": "cubic",
            "function_parameters": dict(parameters),
            "evidence_points_graph": [list(point) for point in evidence_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        execution_trace={
            "family": "cubic",
            "parameters": dict(parameters),
            "evidence_points_graph": [list(point) for point in evidence_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        object_count=1,
    )


def _sinusoid_sample_points(
    *,
    amplitude: int,
    phase_shift: int,
    midline_y: int,
) -> Tuple[GraphPolylinePoint, ...]:
    """Return dense sample points for one constrained cosine curve.

    We use period `12`, so maxima/minima/midline crossings land on integer x
    coordinates for integer `phase_shift`.
    """

    return tuple(
        (
            float(x_value) / 4.0,
            float(
                (float(amplitude) * math.cos((math.pi / 6.0) * (((float(x_value) / 4.0) - float(phase_shift)))))
                + float(midline_y)
            ),
        )
        for x_value in range(-40, 41)
    )


def _positions_in_window(positions: Sequence[int]) -> Tuple[int, ...]:
    """Keep only graph-x positions that are visible in the fixed window."""

    return tuple(int(value) for value in positions if -9 <= int(value) <= 9)


def _sinusoid_maxima_positions(phase_shift: int) -> Tuple[int, ...]:
    """Return visible local maxima x-positions for the constrained cosine family."""

    return _positions_in_window([int(phase_shift + (12 * k_value)) for k_value in range(-2, 3)])


def _sinusoid_minima_positions(phase_shift: int) -> Tuple[int, ...]:
    """Return visible local minima x-positions for the constrained cosine family."""

    return _positions_in_window([int(phase_shift + 6 + (12 * k_value)) for k_value in range(-2, 3)])


def _sinusoid_midline_positions(phase_shift: int) -> Tuple[int, ...]:
    """Return visible midline-intersection x-positions for the constrained cosine family."""

    return _positions_in_window([int(phase_shift + 3 + (6 * k_value)) for k_value in range(-3, 4)])


def _phase_shift_for_sinusoid_count(*, target_count: int, mode: str) -> int:
    """Resolve one integer phase shift whose visible witness count matches the target."""

    candidates: List[int] = []
    for phase_shift in range(-5, 7):
        if str(mode) == "maxima":
            count = len(_sinusoid_maxima_positions(int(phase_shift)))
        elif str(mode) == "minima":
            count = len(_sinusoid_minima_positions(int(phase_shift)))
        elif str(mode) == "midline":
            count = len(_sinusoid_midline_positions(int(phase_shift)))
        else:
            raise ValueError(f"unsupported sinusoid mode: {mode}")
        if int(count) == int(target_count):
            candidates.append(int(phase_shift))
    if not candidates:
        raise ValueError(f"no sinusoid phase_shift supports {mode} target_count={target_count}")
    return int(candidates[0])


def _build_sinusoid_scene(
    rng,
    *,
    query_variant: str,
    reference_line_kind: str | None,
    extremum_kind: str | None,
    target_count: int,
) -> _SampledGraphScene:
    """Sample one constrained cosine curve with integer-coordinate witnesses."""

    amplitude = int(rng.randint(2, 4))
    query_line_y: int | None = None
    midline_y = 0
    evidence_points: Tuple[GraphPoint, ...]

    if str(query_variant) == REFERENCE_LINE_CROSSING_COUNT:
        if str(reference_line_kind) == X_AXIS_REFERENCE_LINE:
            if int(target_count) == 0:
                phase_shift = int(_sample_from(range(-5, 7), rng))
                midline_y = int(rng.choice((amplitude + 1, amplitude + 2, -amplitude - 1, -amplitude - 2)))
                evidence_points = tuple()
            elif int(target_count) in {3, 4}:
                phase_shift = _phase_shift_for_sinusoid_count(target_count=int(target_count), mode="midline")
                midline_y = 0
                evidence_points = tuple((int(x_value), 0) for x_value in _sinusoid_midline_positions(int(phase_shift)))
            else:
                raise ValueError(f"unsupported sinusoid reference-line target_count: {target_count}")
        elif str(reference_line_kind) == HORIZONTAL_REFERENCE_LINE:
            if int(target_count) == 0:
                phase_shift = int(_sample_from(range(-5, 7), rng))
                midline_y = int(_sample_from((-3, -2, -1, 1, 2, 3), rng))
                query_line_y = int(midline_y + rng.choice((amplitude + 1, amplitude + 2, -amplitude - 1, -amplitude - 2)))
                if int(query_line_y) == 0:
                    query_line_y += 1 if int(midline_y) >= 0 else -1
                evidence_points = tuple()
            elif int(target_count) in {3, 4}:
                phase_shift = _phase_shift_for_sinusoid_count(target_count=int(target_count), mode="midline")
                midline_y = int(_sample_from((-3, -2, -1, 1, 2, 3), rng))
                query_line_y = int(midline_y)
                evidence_points = tuple((int(x_value), int(query_line_y)) for x_value in _sinusoid_midline_positions(int(phase_shift)))
            else:
                raise ValueError(f"unsupported sinusoid reference-line target_count: {target_count}")
        else:
            raise ValueError(f"unsupported reference_line_kind: {reference_line_kind}")
    elif str(query_variant) == TURNING_POINT_COUNT:
        if int(target_count) not in {3, 4}:
            raise ValueError(f"unsupported sinusoid turning target_count: {target_count}")
        phase_shift = _phase_shift_for_sinusoid_count(target_count=(1 if int(target_count) == 3 else 2), mode="maxima")
        # Choose the paired minima count that yields the requested total.
        if int(target_count) == 3:
            candidate_phase_shifts = [
                value
                for value in range(-5, 7)
                if len(_sinusoid_maxima_positions(int(value))) + len(_sinusoid_minima_positions(int(value))) == 3
            ]
            phase_shift = int(candidate_phase_shifts[0])
        else:
            candidate_phase_shifts = [
                value
                for value in range(-5, 7)
                if len(_sinusoid_maxima_positions(int(value))) + len(_sinusoid_minima_positions(int(value))) == 4
            ]
            phase_shift = int(candidate_phase_shifts[0])
        midline_y = int(_sample_from((-2, -1, 0, 1, 2), rng))
        evidence_points = tuple(
            (int(x_value), int(midline_y + amplitude)) for x_value in _sinusoid_maxima_positions(int(phase_shift))
        ) + tuple(
            (int(x_value), int(midline_y - amplitude)) for x_value in _sinusoid_minima_positions(int(phase_shift))
        )
    elif str(query_variant) == LOCAL_EXTREMUM_COUNT:
        if int(target_count) not in {1, 2}:
            raise ValueError(f"unsupported sinusoid local-extremum target_count: {target_count}")
        if str(extremum_kind) == MINIMUM_EXTREMUM:
            phase_shift = _phase_shift_for_sinusoid_count(target_count=int(target_count), mode="minima")
            midline_y = int(_sample_from((-2, -1, 0, 1, 2), rng))
            evidence_points = tuple(
                (int(x_value), int(midline_y - amplitude))
                for x_value in _sinusoid_minima_positions(int(phase_shift))
            )
        elif str(extremum_kind) == MAXIMUM_EXTREMUM:
            phase_shift = _phase_shift_for_sinusoid_count(target_count=int(target_count), mode="maxima")
            midline_y = int(_sample_from((-2, -1, 0, 1, 2), rng))
            evidence_points = tuple(
                (int(x_value), int(midline_y + amplitude))
                for x_value in _sinusoid_maxima_positions(int(phase_shift))
            )
        else:
            raise ValueError(f"unsupported extremum_kind: {extremum_kind}")
    else:
        raise ValueError(f"unsupported sinusoid query_variant: {query_variant}")

    sample_points = _sinusoid_sample_points(
        amplitude=int(amplitude),
        phase_shift=int(phase_shift),
        midline_y=int(midline_y),
    )
    parameters = {
        "amplitude": int(amplitude),
        "phase_shift": int(phase_shift),
        "midline_y": int(midline_y),
        "period": 12,
        "family_form": "cosine",
    }
    return _SampledGraphScene(
        polyline_graph=sample_points,
        evidence_graph_points=tuple(evidence_points),
        query_line_y=(None if query_line_y is None else int(query_line_y)),
        scene_entities=[
            {
                "entity_id": "function_graph",
                "entity_type": "function_graph",
                "family": "sinusoid",
                "parameters": dict(parameters),
            }
        ],
        render_map={
            "scene_variant": "sinusoid",
            "function_parameters": dict(parameters),
            "evidence_points_graph": [list(point) for point in evidence_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        execution_trace={
            "family": "sinusoid",
            "parameters": dict(parameters),
            "evidence_points_graph": [list(point) for point in evidence_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        object_count=1,
    )


def _piecewise_polyline_for_intersections(
    rng,
    *,
    target_count: int,
    baseline_y: int,
) -> Tuple[Tuple[GraphPoint, ...], Tuple[GraphPoint, ...]]:
    """Build one lattice polyline whose only baseline crossings are lattice vertices."""

    x_positions = list(
        _int_tuple_default(
            _GEN_DEFAULTS,
            "piecewise_intersection_x_positions",
            _DEFAULTS.piecewise_intersection_x_positions,
        )
    )
    if int(target_count) == 0:
        vertex_count = 4
        start_index = int(rng.randint(0, len(x_positions) - vertex_count))
        selected_x = x_positions[start_index : start_index + vertex_count]
        sign_value = int(rng.choice((-1, 1)))
        vertices = tuple(
            (int(x_value), int(baseline_y + (sign_value * int(rng.randint(2, 4)))))
            for x_value in selected_x
        )
        return vertices, tuple()

    vertex_count = int((2 * int(target_count)) + 1)
    start_index = int(rng.randint(0, len(x_positions) - vertex_count))
    selected_x = x_positions[start_index : start_index + vertex_count]
    sign_start = int(rng.choice((-1, 1)))
    vertices: List[GraphPoint] = []
    evidence_points: List[GraphPoint] = []
    for index, x_value in enumerate(selected_x):
        if index % 2 == 1:
            point = (int(x_value), int(baseline_y))
            vertices.append(point)
            evidence_points.append(point)
            continue
        sign_value = int(sign_start * ((-1) ** (index // 2)))
        magnitude = int(rng.randint(2, 4))
        vertices.append((int(x_value), int(baseline_y + (sign_value * magnitude))))
    return tuple(vertices), tuple(evidence_points)


def _piecewise_polyline_for_turning_points(
    rng,
    *,
    target_count: int,
) -> Tuple[Tuple[GraphPoint, ...], Tuple[GraphPoint, ...]]:
    """Build one lattice polyline with the requested number of turning points."""

    vertex_count = int(target_count) + 2
    x_positions = list(
        _int_tuple_default(
            _GEN_DEFAULTS,
            "piecewise_turning_x_positions",
            _DEFAULTS.piecewise_turning_x_positions,
        )
    )
    start_index = int(rng.randint(0, len(x_positions) - vertex_count))
    selected_x = x_positions[start_index : start_index + vertex_count]
    sign_start = int(rng.choice((-1, 1)))
    vertices: List[GraphPoint] = []
    for index, x_value in enumerate(selected_x):
        sign_value = int(sign_start * ((-1) ** index))
        magnitude = int(rng.randint(2, 5))
        vertices.append((int(x_value), int(sign_value * magnitude)))
    evidence_points = tuple(vertices[1:-1])
    return tuple(vertices), tuple(evidence_points)


def _piecewise_polyline_for_local_extrema(
    rng,
    *,
    target_count: int,
    extremum_kind: str,
) -> Tuple[Tuple[GraphPoint, ...], Tuple[GraphPoint, ...]]:
    """Build one lattice polyline with the requested number of minima or maxima.

    For `target_count > 0`, we alternate between high and low vertices so the
    requested extremum kind appears exactly `target_count` times while the
    opposite kind appears at most `target_count - 1` times. The zero-count case
    uses a monotone polyline, which keeps the witness set empty without
    introducing hidden turning points.
    """

    normalized_kind = str(extremum_kind).strip().lower()
    if normalized_kind not in {"minimum", "maximum"}:
        raise ValueError(f"unsupported extremum_kind: {extremum_kind}")

    x_positions = list(
        _int_tuple_default(
            _GEN_DEFAULTS,
            "piecewise_turning_x_positions",
            _DEFAULTS.piecewise_turning_x_positions,
        )
    )
    if int(target_count) == 0:
        vertex_count = 4
        start_index = int(rng.randint(0, len(x_positions) - vertex_count))
        selected_x = x_positions[start_index : start_index + vertex_count]
        direction = int(rng.choice((-1, 1)))
        step = int(rng.randint(1, 2))
        if int(direction) > 0:
            start_y = int(rng.randint(-7, -2))
        else:
            start_y = int(rng.randint(2, 7))
        vertices = tuple(
            (int(x_value), int(start_y + (direction * step * index)))
            for index, x_value in enumerate(selected_x)
        )
        return vertices, tuple()

    vertex_count = int((2 * int(target_count)) + 1)
    start_index = int(rng.randint(0, len(x_positions) - vertex_count))
    selected_x = x_positions[start_index : start_index + vertex_count]
    starts_high = normalized_kind == "minimum"
    high_values = [int(rng.randint(2, 5)) for _ in selected_x]
    low_values = [-int(rng.randint(2, 5)) for _ in selected_x]
    vertices: List[GraphPoint] = []
    evidence_points: List[GraphPoint] = []
    for index, x_value in enumerate(selected_x):
        use_high = (index % 2 == 0) if starts_high else (index % 2 == 1)
        y_value = int(high_values[index] if use_high else low_values[index])
        point = (int(x_value), int(y_value))
        vertices.append(point)
        if 0 < index < (vertex_count - 1):
            is_target_extremum = (not use_high) if starts_high else use_high
            if is_target_extremum:
                evidence_points.append(point)
    return tuple(vertices), tuple(evidence_points)


def _build_piecewise_linear_scene(
    rng,
    *,
    query_variant: str,
    reference_line_kind: str | None,
    extremum_kind: str | None,
    target_count: int,
) -> _SampledGraphScene:
    """Sample one piecewise-linear graph that realizes the requested count."""

    if str(query_variant) == REFERENCE_LINE_CROSSING_COUNT:
        if str(reference_line_kind) == X_AXIS_REFERENCE_LINE:
            vertices, evidence_points = _piecewise_polyline_for_intersections(
                rng,
                target_count=int(target_count),
                baseline_y=0,
            )
            query_line_y = None
        elif str(reference_line_kind) == HORIZONTAL_REFERENCE_LINE:
            baseline_y = _sample_from(
                _int_tuple_default(
                    _GEN_DEFAULTS,
                    "horizontal_line_support",
                    _DEFAULTS.horizontal_line_support,
                ),
                rng,
            )
            vertices, evidence_points = _piecewise_polyline_for_intersections(
                rng,
                target_count=int(target_count),
                baseline_y=int(baseline_y),
            )
            query_line_y = int(baseline_y)
        else:
            raise ValueError(f"unsupported reference_line_kind: {reference_line_kind}")
    elif str(query_variant) == TURNING_POINT_COUNT:
        vertices, evidence_points = _piecewise_polyline_for_turning_points(
            rng,
            target_count=int(target_count),
        )
        query_line_y = None
    elif str(query_variant) == LOCAL_EXTREMUM_COUNT:
        vertices, evidence_points = _piecewise_polyline_for_local_extrema(
            rng,
            target_count=int(target_count),
            extremum_kind=str(extremum_kind),
        )
        query_line_y = None
    else:
        raise ValueError(f"unsupported piecewise-linear query_variant: {query_variant}")

    return _SampledGraphScene(
        polyline_graph=tuple((float(point[0]), float(point[1])) for point in vertices),
        evidence_graph_points=tuple(evidence_points),
        query_line_y=(None if query_line_y is None else int(query_line_y)),
        scene_entities=[
            {
                "entity_id": "function_graph",
                "entity_type": "function_graph",
                "family": "piecewise_linear",
                "vertices_graph": [list(point) for point in vertices],
            }
        ],
        render_map={
            "scene_variant": "piecewise_linear",
            "polyline_vertices_graph": [list(point) for point in vertices],
            "evidence_points_graph": [list(point) for point in evidence_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        execution_trace={
            "family": "piecewise_linear",
            "polyline_vertices_graph": [list(point) for point in vertices],
            "evidence_points_graph": [list(point) for point in evidence_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        object_count=int(len(vertices)),
    )


def _sample_scene(
    rng,
    *,
    scene_variant: str,
    query_variant: str,
    reference_line_kind: str | None,
    extremum_kind: str | None,
    target_count: int,
) -> _SampledGraphScene:
    """Sample one compatible graphing scene."""

    if str(scene_variant) == "quadratic":
        return _build_quadratic_scene(
            rng,
            query_variant=str(query_variant),
            reference_line_kind=reference_line_kind,
            target_count=int(target_count),
        )
    if str(scene_variant) == "absolute_value":
        return _build_absolute_value_scene(
            rng,
            query_variant=str(query_variant),
            reference_line_kind=reference_line_kind,
            target_count=int(target_count),
        )
    if str(scene_variant) == "cubic":
        return _build_cubic_scene(
            rng,
            query_variant=str(query_variant),
            reference_line_kind=reference_line_kind,
            target_count=int(target_count),
        )
    if str(scene_variant) == "sinusoid":
        return _build_sinusoid_scene(
            rng,
            query_variant=str(query_variant),
            reference_line_kind=reference_line_kind,
            extremum_kind=extremum_kind,
            target_count=int(target_count),
        )
    if str(scene_variant) == "piecewise_linear":
        return _build_piecewise_linear_scene(
            rng,
            query_variant=str(query_variant),
            reference_line_kind=reference_line_kind,
            extremum_kind=extremum_kind,
            target_count=int(target_count),
        )
    raise ValueError(f"unsupported graphing scene_variant: {scene_variant}")


def _build_object_description(
    *,
    prompt_defaults: Mapping[str, Any],
    scene_variant: str,
    query_variant: str,
    reference_line_kind: str | None,
) -> str:
    """Resolve one prompt-facing scene description without hardcoding prose here."""

    suffix = (
        "_with_guide_line"
        if str(query_variant) == REFERENCE_LINE_CROSSING_COUNT
        and str(reference_line_kind) == HORIZONTAL_REFERENCE_LINE
        else ""
    )
    key = f"object_description_{str(scene_variant).strip().lower()}{suffix}"
    value = prompt_defaults.get(key)
    if value is None:
        raise ValueError(f"missing prompt default for {key}")
    return str(value)


def _prompt_default(prompt_defaults: Mapping[str, Any], key: str) -> str:
    """Return one required prompt default string."""

    value = prompt_defaults.get(str(key))
    if value is None:
        raise ValueError(f"missing prompt default for {key}")
    return str(value)


def _reference_line_prompt_description(
    *,
    prompt_defaults: Mapping[str, Any],
    reference_line_kind: str | None,
    query_line_y: int | None,
) -> str:
    """Resolve the prompt description for the selected reference-line parameter."""

    if str(reference_line_kind) == X_AXIS_REFERENCE_LINE:
        return _prompt_default(prompt_defaults, "reference_line_description_x_axis")
    if str(reference_line_kind) == HORIZONTAL_REFERENCE_LINE:
        template = _prompt_default(prompt_defaults, "reference_line_description_horizontal_line")
        if query_line_y is None:
            raise ValueError("horizontal reference-line prompts require query_line_y")
        return str(template).format(query_line_equation=f"y = {int(query_line_y)}")
    return ""


def _extremum_prompt_slots(
    *,
    prompt_defaults: Mapping[str, Any],
    extremum_kind: str | None,
) -> Dict[str, str]:
    """Resolve prompt slots for the selected local-extremum parameter."""

    if str(extremum_kind) == MINIMUM_EXTREMUM:
        suffix = "minimum"
    elif str(extremum_kind) == MAXIMUM_EXTREMUM:
        suffix = "maximum"
    else:
        return {
            "extremum_kind_adjective": "",
            "extremum_visual_description": "",
        }
    return {
        "extremum_kind_adjective": _prompt_default(prompt_defaults, f"extremum_kind_adjective_{suffix}"),
        "extremum_visual_description": _prompt_default(prompt_defaults, f"extremum_visual_description_{suffix}"),
    }


def _pixel_point(point: GraphPoint | GraphPolylinePoint, *, context: GraphSceneContext) -> Tuple[float, float]:
    """Project one graph point into canonical pixel coordinates."""

    return graph_units_to_pixel_float(
        point,
        graph_origin=context.graph_origin,
        graph_spacing=int(context.graph_spacing),
    )


def _render_scene(
    draw: ImageDraw.ImageDraw,
    *,
    context: GraphSceneContext,
    sampled_scene: _SampledGraphScene,
    shape_style,
    line_width: int,
    guide_line_width: int,
    label_font_size_px: int,
) -> _RenderedGraphScene:
    """Render one sampled graphing scene and build evidence artifacts."""

    render_polyline = draw_function_polyline(
        draw,
        polyline_graph=sampled_scene.polyline_graph,
        graph_origin=context.graph_origin,
        graph_spacing=int(context.graph_spacing),
        scene_scale=int(context.scene_scale),
        line_width=int(line_width),
        line_color=shape_style.line_color,
    )
    render_map = dict(sampled_scene.render_map)
    render_map["function_polyline_pixel"] = [
        [round(float(_pixel_point(point, context=context)[0]), 3), round(float(_pixel_point(point, context=context)[1]), 3)]
        for point in sampled_scene.polyline_graph
    ]
    render_map["function_polyline_render"] = [
        [round(float(point[0]), 3), round(float(point[1]), 3)]
        for point in render_polyline
    ]

    if sampled_scene.query_line_y is not None:
        query_line_meta = draw_horizontal_query_line(
            draw,
            y_value=int(sampled_scene.query_line_y),
            x_min=-9,
            x_max=9,
            graph_origin=context.graph_origin,
            graph_spacing=int(context.graph_spacing),
            scene_scale=int(context.scene_scale),
            dash_px=14.0 * float(context.scene_scale),
            gap_px=8.0 * float(context.scene_scale),
            line_width=int(guide_line_width),
            line_color=build_query_line_color(
                line_color=shape_style.line_color,
                label_color=shape_style.label_color,
            ),
            label_text=f"y = {int(sampled_scene.query_line_y)}",
            label_font_size_px=int(label_font_size_px),
            label_color=shape_style.label_color,
            canvas_size=int(context.canvas_size),
        )
        render_map.update(dict(query_line_meta))

    points_by_label = {
        f"point_{index + 1}": _pixel_point(point, context=context)
        for index, point in enumerate(sampled_scene.evidence_graph_points)
    }
    evidence = (
        graph_point_set_evidence_artifacts(
            points_by_label=points_by_label,
            graph_origin=context.graph_origin,
            graph_spacing=int(context.graph_spacing),
            witness_type="graph_feature_points",
            ordered_labels=tuple(points_by_label.keys()),
        )
        if points_by_label
        else empty_graph_point_set_evidence_artifacts(witness_type="graph_feature_points")
    )
    return _RenderedGraphScene(
        answer_value=int(len(sampled_scene.evidence_graph_points)),
        evidence_type=str(evidence["evidence_type"]),
        evidence_value=[list(point) for point in evidence["evidence_value"]],
        projected_evidence=dict(evidence["projected_evidence"]),
        witness_symbolic=dict(evidence["witness_symbolic"]),
        required_evidence_labels=list(evidence["required_labels"]),
        scene_entities=list(sampled_scene.scene_entities),
        render_map=dict(render_map),
        execution_trace=dict(sampled_scene.execution_trace),
        object_count=int(sampled_scene.object_count),
    )


class GeometryGraphingCountTask:
    """Count reference-line crossings, turning points, or local extrema on plotted graphs."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = "graphing"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query = _resolve_axes(int(instance_seed), params=params)
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.scene")

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_integer",
                "evidence_hint_pixel_point_set",
                "evidence_hint_reference_line_crossing_count",
                "evidence_hint_turning_point_count",
                "evidence_hint_local_extremum_count",
                "json_example_reference_line_crossing_count",
                "json_example_turning_point_count",
                "json_example_local_extremum_count",
                "json_example_answer_only_reference_line_crossing_count",
                "json_example_answer_only_turning_point_count",
                "json_example_answer_only_local_extremum_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )

        scene_context = resolve_graph_scene_context(
            rng,
            instance_seed=int(instance_seed),
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
            fallback_canvas_min=_DEFAULTS.canvas_size_min,
            fallback_canvas_max=_DEFAULTS.canvas_size_max,
            fallback_cells_min=_DEFAULTS.graph_cells_min,
            fallback_cells_max=_DEFAULTS.graph_cells_max,
            require_graph_paper_background=True,
            graph_style_overrides={
                "origin_fraction_x": 0.5,
                "origin_fraction_y": 0.5,
                "axis_scale_label_max_abs": 8,
                "origin_label_enabled": False,
            },
        )
        image, draw, background_meta = make_graph_scene_canvas(
            instance_seed=int(instance_seed),
            context=scene_context,
            background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
            require_graph_paper=True,
        )

        line_width = int(
            params.get(
                "line_width",
                group_default(_RENDER_DEFAULTS, "line_width", _DEFAULTS.line_width),
            )
        ) * int(scene_context.scene_scale)
        guide_line_width = int(
            params.get(
                "guide_line_width",
                group_default(_RENDER_DEFAULTS, "guide_line_width", _DEFAULTS.guide_line_width),
            )
        ) * int(scene_context.scene_scale)
        label_font_size_px = int(
            params.get(
                "label_font_size_px",
                resolve_scene_label_font_size_px(
                    canvas_size=int(scene_context.canvas_size),
                    graph_spacing=int(scene_context.graph_spacing),
                    scene_scale=int(scene_context.scene_scale),
                    min_px=int(group_default(_RENDER_DEFAULTS, "label_font_size_min", _DEFAULTS.label_font_size_min)),
                    max_px=int(group_default(_RENDER_DEFAULTS, "label_font_size_max", _DEFAULTS.label_font_size_max)),
                ),
            )
        )
        shape_style = sample_geometry_shape_style(
            rng,
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            anchor_colors=extract_background_anchor_colors(background_meta),
        )

        sampled_scene = _sample_scene(
            rng,
            scene_variant=str(query.scene_variant),
            query_variant=str(query.query_variant),
            reference_line_kind=query.reference_line_kind,
            extremum_kind=query.extremum_kind,
            target_count=int(query.target_count),
        )
        rendered_scene = _render_scene(
            draw,
            context=scene_context,
            sampled_scene=sampled_scene,
            shape_style=shape_style,
            line_width=int(line_width),
            guide_line_width=int(guide_line_width),
            label_font_size_px=int(label_font_size_px),
        )

        image, background_meta_final, post_noise_meta = finalize_graph_scene_image(
            image,
            instance_seed=int(instance_seed),
            context=scene_context,
            background_meta=background_meta,
            noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
        )

        object_description = _build_object_description(
            prompt_defaults=_PROMPT_DEFAULTS,
            scene_variant=str(query.scene_variant),
            query_variant=str(query.query_variant),
            reference_line_kind=query.reference_line_kind,
        )
        json_example, json_example_answer_only = build_prompt_json_examples(
            evidence_value=rendered_scene.evidence_value,
            answer_type="integer",
        )
        extremum_slots = _extremum_prompt_slots(
            prompt_defaults=_PROMPT_DEFAULTS,
            extremum_kind=query.extremum_kind,
        )
        reference_line_description = _reference_line_prompt_description(
            prompt_defaults=_PROMPT_DEFAULTS,
            reference_line_kind=query.reference_line_kind,
            query_line_y=sampled_scene.query_line_y,
        )
        evidence_hint = str(prompt_defaults["evidence_hint_pixel_point_set"])
        if str(query.query_variant) == REFERENCE_LINE_CROSSING_COUNT:
            evidence_hint = str(prompt_defaults["evidence_hint_reference_line_crossing_count"]).format(
                reference_line_description=str(reference_line_description)
            )
            json_example = str(prompt_defaults["json_example_reference_line_crossing_count"])
            json_example_answer_only = str(prompt_defaults["json_example_answer_only_reference_line_crossing_count"])
        elif str(query.query_variant) == TURNING_POINT_COUNT:
            evidence_hint = str(prompt_defaults["evidence_hint_turning_point_count"])
            json_example = str(prompt_defaults["json_example_turning_point_count"])
            json_example_answer_only = str(prompt_defaults["json_example_answer_only_turning_point_count"])
        elif str(query.query_variant) == LOCAL_EXTREMUM_COUNT:
            evidence_hint = str(prompt_defaults["evidence_hint_local_extremum_count"]).format(**dict(extremum_slots))
            json_example = str(prompt_defaults["json_example_local_extremum_count"])
            json_example_answer_only = str(prompt_defaults["json_example_answer_only_local_extremum_count"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "reference_line_description": str(reference_line_description),
                **dict(extremum_slots),
                "query_line_equation": (
                    "" if sampled_scene.query_line_y is None else f"y = {int(sampled_scene.query_line_y)}"
                ),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(prompt_defaults["answer_hint_integer"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(rendered_scene.answer_value))
        evidence_gt = TypedValue(type=str(rendered_scene.evidence_type), value=list(rendered_scene.evidence_value))

        query_params = {
            "scene_variant": str(query.scene_variant),
            "query_variant": str(query.query_variant),
            "query_variant": str(query.query_variant),
            "variant_probabilities": dict(query.query_variant_probabilities),
            "scene_variant_probabilities": dict(query.scene_variant_probabilities),
            "query_variant_probabilities": dict(query.query_variant_probabilities),
            "target_count": int(query.target_count),
            "target_count_probabilities": dict(query.target_count_probabilities),
        }
        if query.reference_line_kind is not None:
            query_params["reference_line_kind"] = str(query.reference_line_kind)
            query_params["reference_line_kind_probabilities"] = dict(query.reference_line_kind_probabilities)
        if query.extremum_kind is not None:
            query_params["extremum_kind"] = str(query.extremum_kind)
            query_params["extremum_kind_probabilities"] = dict(query.extremum_kind_probabilities)

        execution_trace = {
            "scene_variant": str(query.scene_variant),
            "query_variant": str(query.query_variant),
            "query_variant": str(query.query_variant),
            "scene_variant_probabilities": dict(query.scene_variant_probabilities),
            "query_variant_probabilities": dict(query.query_variant_probabilities),
            "query_variant_probabilities": dict(query.query_variant_probabilities),
            "target_count": int(query.target_count),
            "target_count_probabilities": dict(query.target_count_probabilities),
            "question_format": "count_graph_feature_points",
            "required_evidence_labels": list(rendered_scene.required_evidence_labels),
            **dict(rendered_scene.execution_trace),
        }
        if query.reference_line_kind is not None:
            execution_trace["reference_line_kind"] = str(query.reference_line_kind)
            execution_trace["reference_line_kind_probabilities"] = dict(query.reference_line_kind_probabilities)
        if query.extremum_kind is not None:
            execution_trace["extremum_kind"] = str(query.extremum_kind)
            execution_trace["extremum_kind_probabilities"] = dict(query.extremum_kind_probabilities)

        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_graphing_count",
                "entities": list(rendered_scene.scene_entities),
                "relations": {
                    "scene_variant": str(query.scene_variant),
                    "query_variant": str(query.query_variant),
                    "query_variant": str(query.query_variant),
                    "target_count": int(query.target_count),
                    **(
                        {"reference_line_kind": str(query.reference_line_kind)}
                        if query.reference_line_kind is not None
                        else {}
                    ),
                    **(
                        {"extremum_kind": str(query.extremum_kind)}
                        if query.extremum_kind is not None
                        else {}
                    ),
                },
            },
            "query_spec": {
                "query_variant": str(query.query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_size": int(scene_context.canvas_size),
                "coord_space": "pixel",
                "background_style": dict(background_meta_final),
                "post_image_noise": dict(post_noise_meta),
                "shape_style": dict(shape_style.to_trace_dict()),
                "graph_coordinate_frame": dict(scene_context.graph_frame),
                "graph_paper_grid": graph_paper_grid_from_frame(scene_context.graph_frame),
                **dict(scene_context.graph_layout_metadata),
                "scene_variant": str(query.scene_variant),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": dict(execution_trace),
            "witness_symbolic": dict(rendered_scene.witness_symbolic),
            "projected_evidence": dict(rendered_scene.projected_evidence),
        }

        complexity = build_geometry_graphing_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            scene_variant=str(query.scene_variant),
            query_variant=str(query.query_variant),
            reference_line_kind=query.reference_line_kind,
            extremum_kind=query.extremum_kind,
            object_count=int(rendered_scene.object_count),
            target_count=int(query.target_count),
            evidence_count=int(len(rendered_scene.evidence_value)),
            has_query_line=bool(sampled_scene.query_line_y is not None),
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
            query_variant=str(query.query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometryGraphingReferenceLineCrossingCountTask(FixedGeometryQueryTaskMixin, GeometryGraphingCountTask):
    """Count intersections between a plotted function and the marked reference line."""

    task_id = "task_geometry__function_graph__reference_line_crossing_count"
    fixed_query_variant = REFERENCE_LINE_CROSSING_COUNT
    public_scene_id = "function_graph"


@register_task
class GeometryGraphingExtremumCountTask(MultiFixedGeometryQueryTaskMixin, GeometryGraphingCountTask):
    """Count turning points or local extrema on a plotted function."""

    task_id = "task_geometry__function_graph__extremum_count"
    fixed_query_variants = (TURNING_POINT_COUNT, LOCAL_EXTREMUM_COUNT)
    public_scene_id = "function_graph"
