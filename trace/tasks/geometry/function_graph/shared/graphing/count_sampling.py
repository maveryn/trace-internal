"""Sampling helpers for geometry graphing-count tasks."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ......core.sampling import normalize_positive_weights, weighted_choice
from ......core.seed import hash64, spawn_rng
from .....shared.config_defaults import group_default
from .....shared.deterministic_sampling import uniform_probability_map
from .....shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant

from .count_common import (
    COMPATIBILITY,
    HORIZONTAL_REFERENCE_LINE,
    LOCAL_EXTREMUM_COUNT,
    MAXIMUM_EXTREMUM,
    MINIMUM_EXTREMUM,
    REFERENCE_LINE_CROSSING_COUNT,
    SUPPORTED_EXTREMUM_KINDS,
    SUPPORTED_QUERY_IDS,
    SUPPORTED_REFERENCE_LINE_KINDS,
    SUPPORTED_SCENE_VARIANTS,
    TASK_ID,
    TURNING_POINT_COUNT,
    X_AXIS_REFERENCE_LINE,
    GraphPoint,
    GraphPolylinePoint,
    _DEFAULTS,
    _GEN_DEFAULTS,
    _ResolvedQuery,
    _SampledGraphScene,
    _TARGET_COUNT_BALANCE_SALT,
)

def _int_tuple_default(
    defaults: Mapping[str, Any],
    key: str,
    fallback: Sequence[int],
) -> Tuple[int, ...]:
    """Resolve one integer sequence from scene-package defaults."""

    raw_value = defaults.get(str(key), fallback)
    if not isinstance(raw_value, Sequence) or isinstance(raw_value, (str, bytes)):
        raise ValueError(f"{key} must be a sequence of integers for {TASK_ID}")
    values = tuple(int(value) for value in raw_value)
    if not values:
        raise ValueError(f"{key} cannot be empty for {TASK_ID}")
    return values


def _count_target_support(*, scene_variant: str, query_id: str) -> Tuple[int, ...]:
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
    key = (str(scene_variant).strip().lower(), str(query_id).strip().lower())
    support = support_map.get(key)
    if support is None:
        raise ValueError(f"unsupported graphing scene/query pair: {scene_variant} x {query_id}")
    return tuple(int(value) for value in support)


def _full_probability_map(supported: Sequence[str], probabilities: Mapping[str, float]) -> Dict[str, float]:
    """Expand one restricted probability map over the full supported domain."""

    positive = {str(key): float(value) for key, value in probabilities.items()}
    return {
        str(key): float(positive.get(str(key), 0.0))
        for key in supported
    }


def _query_target_support(query_id: str) -> Tuple[int, ...]:
    """Return the union count support for one query across compatible scene families."""

    supports = {
        int(value)
        for scene_variant, query_ids in COMPATIBILITY.items()
        if str(query_id) in set(str(item) for item in query_ids)
        for value in _count_target_support(scene_variant=str(scene_variant), query_id=str(query_id))
    }
    if not supports:
        raise ValueError(f"unsupported graphing query_id: {query_id}")
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
    so it stays decoupled from the separate query-id balancing stream
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
    query_id: str,
    params: Mapping[str, Any],
) -> Tuple[str | None, Dict[str, float], str | None, Dict[str, float]]:
    """Resolve parameter axes that are meaningful for the selected query id."""

    normalized_query = str(query_id).strip().lower()
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

    raise ValueError(f"unsupported graphing query_id: {query_id}")


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve scene axes and one count target for a fixed public count objective."""

    axis_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.axes")
    scene_supported = [str(value) for value in SUPPORTED_SCENE_VARIANTS]
    query_supported = [str(value) for value in SUPPORTED_QUERY_IDS]
    compatibility_map = {
        str(scene): tuple(str(query) for query in queries)
        for scene, queries in COMPATIBILITY.items()
    }
    explicit_scene = params.get("scene_variant")
    explicit_query = params.get("query_id")
    if explicit_scene is not None and str(explicit_scene) not in set(scene_supported):
        raise ValueError(f"unsupported scene_variant: {explicit_scene}")
    if explicit_query is None:
        raise ValueError("function_graph count objectives require a public task query_id")
    if explicit_query is not None and str(explicit_query) not in set(query_supported):
        raise ValueError(f"unsupported query_id: {explicit_query}")

    query_id = str(explicit_query)
    query_probs = _full_probability_map(query_supported, {query_id: 1.0})

    if explicit_scene is not None and explicit_query is not None:
        if str(explicit_query) not in set(compatibility_map.get(str(explicit_scene), ())):
            raise ValueError(f"incompatible geometry scene/query combination: {explicit_scene} + {explicit_query}")
        scene_variant = str(explicit_scene)
        scene_probs = _full_probability_map(scene_supported, {scene_variant: 1.0})
        support = _count_target_support(scene_variant=scene_variant, query_id=query_id)
    else:
        if explicit_scene is not None:
            scene_variant = str(explicit_scene)
            if str(query_id) not in set(compatibility_map.get(scene_variant, ())):
                raise ValueError(f"incompatible geometry scene/query combination: {scene_variant} + {query_id}")
            scene_probs = _full_probability_map(scene_supported, {scene_variant: 1.0})
            support = _count_target_support(scene_variant=scene_variant, query_id=query_id)
        else:
            support = _query_target_support(query_id)
            target_count, target_count_probs = _resolve_target_count(
                axis_rng,
                instance_seed=int(instance_seed),
                support=support,
                selection_namespace=f"{TASK_ID}.target_count.{query_id}",
                params=params,
            )
            allowed_scenes = [
                scene
                for scene in scene_supported
                if str(query_id) in set(compatibility_map.get(scene, ()))
                and int(target_count) in set(_count_target_support(scene_variant=scene, query_id=query_id))
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
                selection_namespace=f"{TASK_ID}.scene_variant.{query_id}.{target_count}",
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
                query_id=str(query_id),
                params=params,
            )
            return _ResolvedQuery(
                scene_variant=str(scene_variant),
                query_id=str(query_id),
                reference_line_kind=reference_line_kind,
                extremum_kind=extremum_kind,
                target_count=int(target_count),
                scene_variant_probabilities=dict(scene_probs),
                query_id_probabilities=dict(query_probs),
                reference_line_kind_probabilities=dict(reference_line_probs),
                extremum_kind_probabilities=dict(extremum_probs),
                target_count_probabilities=dict(target_count_probs),
            )

    target_count, target_count_probs = _resolve_target_count(
        axis_rng,
        instance_seed=int(instance_seed),
        support=support,
        selection_namespace=f"{TASK_ID}.target_count.{scene_variant}.{query_id}",
        params=params,
    )
    reference_line_kind, reference_line_probs, extremum_kind, extremum_probs = _resolve_query_parameters(
        axis_rng,
        instance_seed=int(instance_seed),
        query_id=str(query_id),
        params=params,
    )
    return _ResolvedQuery(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        reference_line_kind=reference_line_kind,
        extremum_kind=extremum_kind,
        target_count=int(target_count),
        scene_variant_probabilities=dict(scene_probs),
        query_id_probabilities=dict(query_probs),
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
    query_id: str,
    reference_line_kind: str | None,
    target_count: int,
) -> _SampledGraphScene:
    """Sample one integer-lattice quadratic that realizes the requested count."""

    a_value = int(rng.choice((-1, 1)))
    h_value = int(rng.randint(-4, 4))
    query_line_y: int | None = None
    annotation_points: Tuple[GraphPoint, ...]

    if str(query_id) != REFERENCE_LINE_CROSSING_COUNT:
        raise ValueError(f"unsupported quadratic query_id: {query_id}")

    if str(reference_line_kind) == X_AXIS_REFERENCE_LINE:
        if int(target_count) == 0:
            k_value = int(rng.randint(1, 4)) if int(a_value) > 0 else -int(rng.randint(1, 4))
            annotation_points = tuple()
        elif int(target_count) == 2:
            root_delta = int(rng.randint(1, 3))
            h_value = int(rng.randint(-6 + root_delta, 6 - root_delta))
            k_value = int(-a_value * (root_delta**2))
            annotation_points = (
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
            annotation_points = tuple()
        elif int(target_count) == 2:
            root_delta = int(rng.randint(1, 3))
            h_value = int(rng.randint(-6 + root_delta, 6 - root_delta))
            k_value = int(rng.randint(-3, 3))
            query_line_y = int(k_value + (a_value * (root_delta**2)))
            if int(query_line_y) == 0:
                shift = 1 if int(query_line_y) <= 0 else -1
                k_value += shift
                query_line_y += shift
            annotation_points = (
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
        annotation_graph_points=tuple(annotation_points),
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
            "annotation_points_graph": [list(point) for point in annotation_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        execution_trace={
            "family": "quadratic",
            "parameters": {"a": int(a_value), "h": int(h_value), "k": int(k_value)},
            "annotation_points_graph": [list(point) for point in annotation_points],
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
    query_id: str,
    reference_line_kind: str | None,
    target_count: int,
) -> _SampledGraphScene:
    """Sample one integer-lattice absolute-value graph that realizes the requested count."""

    orientation = int(rng.choice((-1, 1)))
    slope = int(rng.choice((1, 2)))
    h_value = int(rng.randint(-4, 4))
    query_line_y: int | None = None
    annotation_points: Tuple[GraphPoint, ...]

    if str(query_id) != REFERENCE_LINE_CROSSING_COUNT:
        raise ValueError(f"unsupported absolute-value query_id: {query_id}")

    if str(reference_line_kind) == X_AXIS_REFERENCE_LINE:
        if int(target_count) == 0:
            root_distance = int(rng.randint(1, 3))
            k_value = int(orientation * slope * root_distance)
            annotation_points = tuple()
        elif int(target_count) == 2:
            root_distance = int(rng.randint(1, 3))
            h_value = int(rng.randint(-6 + root_distance, 6 - root_distance))
            k_value = int(-orientation * slope * root_distance)
            annotation_points = (
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
            annotation_points = tuple()
        elif int(target_count) == 2:
            root_distance = int(rng.randint(1, 3))
            h_value = int(rng.randint(-6 + root_distance, 6 - root_distance))
            k_value = int(rng.randint(-3, 3))
            query_line_y = int(k_value + (orientation * slope * root_distance))
            if int(query_line_y) == 0:
                shift = 1 if int(query_line_y) <= 0 else -1
                k_value += shift
                query_line_y += shift
            annotation_points = (
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
        annotation_graph_points=tuple(annotation_points),
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
            "annotation_points_graph": [list(point) for point in annotation_points],
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
            "annotation_points_graph": [list(point) for point in annotation_points],
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
    query_id: str,
    reference_line_kind: str | None,
    target_count: int,
) -> _SampledGraphScene:
    """Sample one factored cubic graph with integer witness coordinates."""

    roots = _cubic_roots_for_target(rng, target_count=int(target_count))
    scale_value = float(rng.choice((-0.012, -0.01, 0.01, 0.012)))
    query_line_y: int | None = None
    visible_roots = tuple(int(root) for root in roots if -9 <= int(root) <= 9)

    if str(query_id) != REFERENCE_LINE_CROSSING_COUNT:
        raise ValueError(f"unsupported cubic query_id: {query_id}")

    if str(reference_line_kind) == X_AXIS_REFERENCE_LINE:
        baseline_y = 0
        annotation_points = tuple(sorted({(int(root), 0) for root in visible_roots}))
    elif str(reference_line_kind) == HORIZONTAL_REFERENCE_LINE:
        baseline_y = int(
            _sample_from(
                [value for value in _int_tuple_default(_GEN_DEFAULTS, "horizontal_line_support", _DEFAULTS.horizontal_line_support) if int(value) != 0],
                rng,
            )
        )
        query_line_y = int(baseline_y)
        annotation_points = tuple(sorted({(int(root), int(query_line_y)) for root in visible_roots}))
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
        annotation_graph_points=tuple(annotation_points),
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
            "annotation_points_graph": [list(point) for point in annotation_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        execution_trace={
            "family": "cubic",
            "parameters": dict(parameters),
            "annotation_points_graph": [list(point) for point in annotation_points],
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
    query_id: str,
    reference_line_kind: str | None,
    extremum_kind: str | None,
    target_count: int,
) -> _SampledGraphScene:
    """Sample one constrained cosine curve with integer-coordinate witnesses."""

    amplitude = int(rng.randint(2, 4))
    query_line_y: int | None = None
    midline_y = 0
    annotation_points: Tuple[GraphPoint, ...]

    if str(query_id) == REFERENCE_LINE_CROSSING_COUNT:
        if str(reference_line_kind) == X_AXIS_REFERENCE_LINE:
            if int(target_count) == 0:
                phase_shift = int(_sample_from(range(-5, 7), rng))
                midline_y = int(rng.choice((amplitude + 1, amplitude + 2, -amplitude - 1, -amplitude - 2)))
                annotation_points = tuple()
            elif int(target_count) in {3, 4}:
                phase_shift = _phase_shift_for_sinusoid_count(target_count=int(target_count), mode="midline")
                midline_y = 0
                annotation_points = tuple((int(x_value), 0) for x_value in _sinusoid_midline_positions(int(phase_shift)))
            else:
                raise ValueError(f"unsupported sinusoid reference-line target_count: {target_count}")
        elif str(reference_line_kind) == HORIZONTAL_REFERENCE_LINE:
            if int(target_count) == 0:
                phase_shift = int(_sample_from(range(-5, 7), rng))
                midline_y = int(_sample_from((-3, -2, -1, 1, 2, 3), rng))
                query_line_y = int(midline_y + rng.choice((amplitude + 1, amplitude + 2, -amplitude - 1, -amplitude - 2)))
                if int(query_line_y) == 0:
                    query_line_y += 1 if int(midline_y) >= 0 else -1
                annotation_points = tuple()
            elif int(target_count) in {3, 4}:
                phase_shift = _phase_shift_for_sinusoid_count(target_count=int(target_count), mode="midline")
                midline_y = int(_sample_from((-3, -2, -1, 1, 2, 3), rng))
                query_line_y = int(midline_y)
                annotation_points = tuple((int(x_value), int(query_line_y)) for x_value in _sinusoid_midline_positions(int(phase_shift)))
            else:
                raise ValueError(f"unsupported sinusoid reference-line target_count: {target_count}")
        else:
            raise ValueError(f"unsupported reference_line_kind: {reference_line_kind}")
    elif str(query_id) == TURNING_POINT_COUNT:
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
        annotation_points = tuple(
            (int(x_value), int(midline_y + amplitude)) for x_value in _sinusoid_maxima_positions(int(phase_shift))
        ) + tuple(
            (int(x_value), int(midline_y - amplitude)) for x_value in _sinusoid_minima_positions(int(phase_shift))
        )
    elif str(query_id) == LOCAL_EXTREMUM_COUNT:
        if int(target_count) not in {1, 2}:
            raise ValueError(f"unsupported sinusoid local-extremum target_count: {target_count}")
        if str(extremum_kind) == MINIMUM_EXTREMUM:
            phase_shift = _phase_shift_for_sinusoid_count(target_count=int(target_count), mode="minima")
            midline_y = int(_sample_from((-2, -1, 0, 1, 2), rng))
            annotation_points = tuple(
                (int(x_value), int(midline_y - amplitude))
                for x_value in _sinusoid_minima_positions(int(phase_shift))
            )
        elif str(extremum_kind) == MAXIMUM_EXTREMUM:
            phase_shift = _phase_shift_for_sinusoid_count(target_count=int(target_count), mode="maxima")
            midline_y = int(_sample_from((-2, -1, 0, 1, 2), rng))
            annotation_points = tuple(
                (int(x_value), int(midline_y + amplitude))
                for x_value in _sinusoid_maxima_positions(int(phase_shift))
            )
        else:
            raise ValueError(f"unsupported extremum_kind: {extremum_kind}")
    else:
        raise ValueError(f"unsupported sinusoid query_id: {query_id}")

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
        annotation_graph_points=tuple(annotation_points),
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
            "annotation_points_graph": [list(point) for point in annotation_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        execution_trace={
            "family": "sinusoid",
            "parameters": dict(parameters),
            "annotation_points_graph": [list(point) for point in annotation_points],
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
    annotation_points: List[GraphPoint] = []
    for index, x_value in enumerate(selected_x):
        if index % 2 == 1:
            point = (int(x_value), int(baseline_y))
            vertices.append(point)
            annotation_points.append(point)
            continue
        sign_value = int(sign_start * ((-1) ** (index // 2)))
        magnitude = int(rng.randint(2, 4))
        vertices.append((int(x_value), int(baseline_y + (sign_value * magnitude))))
    return tuple(vertices), tuple(annotation_points)


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
    annotation_points = tuple(vertices[1:-1])
    return tuple(vertices), tuple(annotation_points)


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
    annotation_points: List[GraphPoint] = []
    for index, x_value in enumerate(selected_x):
        use_high = (index % 2 == 0) if starts_high else (index % 2 == 1)
        y_value = int(high_values[index] if use_high else low_values[index])
        point = (int(x_value), int(y_value))
        vertices.append(point)
        if 0 < index < (vertex_count - 1):
            is_target_extremum = (not use_high) if starts_high else use_high
            if is_target_extremum:
                annotation_points.append(point)
    return tuple(vertices), tuple(annotation_points)


def _build_piecewise_linear_scene(
    rng,
    *,
    query_id: str,
    reference_line_kind: str | None,
    extremum_kind: str | None,
    target_count: int,
) -> _SampledGraphScene:
    """Sample one piecewise-linear graph that realizes the requested count."""

    if str(query_id) == REFERENCE_LINE_CROSSING_COUNT:
        if str(reference_line_kind) == X_AXIS_REFERENCE_LINE:
            vertices, annotation_points = _piecewise_polyline_for_intersections(
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
            vertices, annotation_points = _piecewise_polyline_for_intersections(
                rng,
                target_count=int(target_count),
                baseline_y=int(baseline_y),
            )
            query_line_y = int(baseline_y)
        else:
            raise ValueError(f"unsupported reference_line_kind: {reference_line_kind}")
    elif str(query_id) == TURNING_POINT_COUNT:
        vertices, annotation_points = _piecewise_polyline_for_turning_points(
            rng,
            target_count=int(target_count),
        )
        query_line_y = None
    elif str(query_id) == LOCAL_EXTREMUM_COUNT:
        vertices, annotation_points = _piecewise_polyline_for_local_extrema(
            rng,
            target_count=int(target_count),
            extremum_kind=str(extremum_kind),
        )
        query_line_y = None
    else:
        raise ValueError(f"unsupported piecewise-linear query_id: {query_id}")

    return _SampledGraphScene(
        polyline_graph=tuple((float(point[0]), float(point[1])) for point in vertices),
        annotation_graph_points=tuple(annotation_points),
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
            "annotation_points_graph": [list(point) for point in annotation_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        execution_trace={
            "family": "piecewise_linear",
            "polyline_vertices_graph": [list(point) for point in vertices],
            "annotation_points_graph": [list(point) for point in annotation_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        object_count=int(len(vertices)),
    )


def _sample_scene(
    rng,
    *,
    scene_variant: str,
    query_id: str,
    reference_line_kind: str | None,
    extremum_kind: str | None,
    target_count: int,
) -> _SampledGraphScene:
    """Sample one compatible graphing scene."""

    if str(scene_variant) == "quadratic":
        return _build_quadratic_scene(
            rng,
            query_id=str(query_id),
            reference_line_kind=reference_line_kind,
            target_count=int(target_count),
        )
    if str(scene_variant) == "absolute_value":
        return _build_absolute_value_scene(
            rng,
            query_id=str(query_id),
            reference_line_kind=reference_line_kind,
            target_count=int(target_count),
        )
    if str(scene_variant) == "cubic":
        return _build_cubic_scene(
            rng,
            query_id=str(query_id),
            reference_line_kind=reference_line_kind,
            target_count=int(target_count),
        )
    if str(scene_variant) == "sinusoid":
        return _build_sinusoid_scene(
            rng,
            query_id=str(query_id),
            reference_line_kind=reference_line_kind,
            extremum_kind=extremum_kind,
            target_count=int(target_count),
        )
    if str(scene_variant) == "piecewise_linear":
        return _build_piecewise_linear_scene(
            rng,
            query_id=str(query_id),
            reference_line_kind=reference_line_kind,
            extremum_kind=extremum_kind,
            target_count=int(target_count),
        )
    raise ValueError(f"unsupported graphing scene_variant: {scene_variant}")

__all__ = [
    "_resolve_axes",
    "_sample_scene",
    "_count_target_support",
    "_query_target_support",
]
