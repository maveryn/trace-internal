"""Identity-free function-family sampling primitives."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from trace.tasks.shared.deterministic_sampling import resolve_selection_index, uniform_probability_map

from .defaults import DEFAULTS, GEN_DEFAULTS, float_tuple_default, int_tuple_default
from .state import GraphPoint, GraphPolylinePoint, SampledFunctionGraph

FAMILY_QUADRATIC = "quadratic"
FAMILY_ABSOLUTE_VALUE = "absolute_value"
FAMILY_CUBIC = "cubic"
FAMILY_SINUSOID = "sinusoid"
FAMILY_PIECEWISE_LINEAR = "piecewise_linear"


def average_rate_support() -> Tuple[float, ...]:
    """Return configured one-decimal average-rate answers."""

    values = float_tuple_default("average_rate_support", DEFAULTS.average_rate_support)
    if any(abs(float(value)) <= 1e-9 for value in values):
        raise ValueError("average_rate_support cannot include zero")
    return tuple(float(value) for value in values)


def reference_count_support_by_family() -> Dict[str, Tuple[int, ...]]:
    """Return reference-line crossing count support for each compatible family."""

    return {
        FAMILY_QUADRATIC: int_tuple_default(
            "quadratic_reference_line_crossing_support",
            DEFAULTS.quadratic_reference_support,
        ),
        FAMILY_ABSOLUTE_VALUE: int_tuple_default(
            "absolute_value_reference_line_crossing_support",
            DEFAULTS.absolute_value_reference_support,
        ),
        FAMILY_CUBIC: int_tuple_default("cubic_reference_line_crossing_support", DEFAULTS.cubic_reference_support),
        FAMILY_SINUSOID: int_tuple_default(
            "sinusoid_reference_line_crossing_support",
            DEFAULTS.sinusoid_reference_support,
        ),
        FAMILY_PIECEWISE_LINEAR: int_tuple_default(
            "piecewise_reference_line_crossing_support",
            DEFAULTS.piecewise_reference_support,
        ),
    }


def turning_count_support_by_family() -> Dict[str, Tuple[int, ...]]:
    """Return turning-point count support for each compatible family."""

    return {
        FAMILY_SINUSOID: int_tuple_default("sinusoid_turning_support", DEFAULTS.sinusoid_turning_support),
        FAMILY_PIECEWISE_LINEAR: int_tuple_default("piecewise_turning_support", DEFAULTS.piecewise_turning_support),
    }


def local_extremum_support_by_family() -> Dict[str, Tuple[int, ...]]:
    """Return one-kind local-extremum count support for each compatible family."""

    return {
        FAMILY_SINUSOID: int_tuple_default("sinusoid_local_extremum_support", DEFAULTS.sinusoid_local_support),
        FAMILY_PIECEWISE_LINEAR: int_tuple_default(
            "piecewise_local_extremum_support",
            DEFAULTS.piecewise_local_support,
        ),
    }


def horizontal_reference_line_support() -> Tuple[int, ...]:
    """Return supported nonzero horizontal guide-line y-values."""

    return int_tuple_default("horizontal_line_support", DEFAULTS.horizontal_line_support)


def support_union(support_by_family: Mapping[str, Sequence[int]]) -> Tuple[int, ...]:
    """Return the sorted union of integer answer support across families."""

    values = {int(value) for support in support_by_family.values() for value in support}
    if not values:
        raise ValueError("count support cannot be empty")
    return tuple(sorted(values))


def resolve_numeric_target(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    support: Sequence[int],
    namespace: str,
) -> Tuple[int, Dict[str, float]]:
    """Resolve one count target uniformly from a finite answer support."""

    ordered_support = tuple(int(value) for value in support)
    explicit = params.get("target_count")
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(ordered_support):
            raise ValueError(f"unsupported target_count: {selected}")
        return selected, uniform_probability_map(ordered_support, selected=selected)

    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    selected = int(ordered_support[int(index) % len(ordered_support)])
    probability = 1.0 / float(len(ordered_support))
    return selected, {str(value): float(probability) for value in ordered_support}


def resolve_rate_target(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[float, Dict[str, float]]:
    """Resolve one average-rate target uniformly from configured support."""

    support = average_rate_support()
    explicit = params.get("target_rate", params.get("average_rate"))
    if explicit is not None:
        selected = round(float(explicit), 1)
        if selected not in set(support):
            raise ValueError(f"unsupported target_rate: {selected}")
        return float(selected), {f"{float(value):.1f}": (1.0 if float(value) == selected else 0.0) for value in support}

    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace="function_graph.rate_target",
    )
    selected = float(support[int(index) % len(support)])
    probability = 1.0 / float(len(support))
    return selected, {f"{float(value):.1f}": float(probability) for value in support}


def resolve_family_for_target(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    support_by_family: Mapping[str, Sequence[int]],
    target_count: int,
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one compatible function family for a requested target count."""

    all_families = tuple(str(family) for family in support_by_family)
    allowed = tuple(
        str(family)
        for family, support in support_by_family.items()
        if int(target_count) in {int(value) for value in support}
    )
    if not allowed:
        raise ValueError(f"no function family supports target_count={target_count}")
    explicit = params.get("scene_variant")
    if explicit is not None:
        selected = str(explicit)
        if selected not in set(all_families):
            raise ValueError(f"unsupported scene_variant: {selected}")
        if selected not in set(allowed):
            raise ValueError(f"scene_variant {selected} does not support target_count={target_count}")
        return selected, {family: (1.0 if family == selected else 0.0) for family in all_families}

    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    selected = str(allowed[int(index) % len(allowed)])
    probability = 1.0 / float(len(allowed))
    return selected, {family: (float(probability) if family in set(allowed) else 0.0) for family in all_families}


def resolve_horizontal_reference_y(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[int, Dict[str, float]]:
    """Resolve one visible nonzero horizontal guide line."""

    support = horizontal_reference_line_support()
    explicit = params.get("reference_line_y", params.get("query_line_y"))
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(support):
            raise ValueError(f"unsupported horizontal reference y-value: {selected}")
        return selected, uniform_probability_map(support, selected=selected)

    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace="function_graph.horizontal_reference_y",
    )
    selected = int(support[int(index) % len(support)])
    probability = 1.0 / float(len(support))
    return selected, {str(value): float(probability) for value in support}


def sample_reference_scene(
    rng,
    *,
    family: str,
    target_count: int,
    reference_y: int | None,
) -> SampledFunctionGraph:
    """Sample a graph whose intersections with one reference line match the target."""

    if str(family) == FAMILY_QUADRATIC:
        return _build_quadratic_scene(rng, target_count=int(target_count), reference_y=reference_y)
    if str(family) == FAMILY_ABSOLUTE_VALUE:
        return _build_absolute_value_scene(rng, target_count=int(target_count), reference_y=reference_y)
    if str(family) == FAMILY_CUBIC:
        return _build_cubic_scene(rng, target_count=int(target_count), reference_y=reference_y)
    if str(family) == FAMILY_SINUSOID:
        return _build_sinusoid_reference_scene(rng, target_count=int(target_count), reference_y=reference_y)
    if str(family) == FAMILY_PIECEWISE_LINEAR:
        baseline_y = 0 if reference_y is None else int(reference_y)
        vertices, annotation_points = _piecewise_polyline_for_intersections(
            rng,
            target_count=int(target_count),
            baseline_y=int(baseline_y),
        )
        return _piecewise_scene(
            vertices=vertices,
            annotation_points=annotation_points,
            query_line_y=reference_y,
            purpose="reference_intersections",
        )
    raise ValueError(f"unsupported function family: {family}")


def sample_turning_scene(rng, *, family: str, target_count: int) -> SampledFunctionGraph:
    """Sample a graph with the requested number of visible turning points."""

    if str(family) == FAMILY_SINUSOID:
        return _build_sinusoid_turning_scene(rng, target_count=int(target_count))
    if str(family) == FAMILY_PIECEWISE_LINEAR:
        vertices, annotation_points = _piecewise_polyline_for_turning_points(rng, target_count=int(target_count))
        return _piecewise_scene(
            vertices=vertices,
            annotation_points=annotation_points,
            query_line_y=None,
            purpose="turning_points",
        )
    raise ValueError(f"unsupported function family: {family}")


def sample_local_extremum_scene(
    rng,
    *,
    family: str,
    target_count: int,
    extremum_sign: int,
) -> SampledFunctionGraph:
    """Sample a graph with the requested number of visible minima or maxima."""

    sign = -1 if int(extremum_sign) < 0 else 1
    if str(family) == FAMILY_SINUSOID:
        return _build_sinusoid_local_scene(rng, target_count=int(target_count), extremum_sign=int(sign))
    if str(family) == FAMILY_PIECEWISE_LINEAR:
        vertices, annotation_points = _piecewise_polyline_for_local_extrema(
            rng,
            target_count=int(target_count),
            extremum_sign=int(sign),
        )
        return _piecewise_scene(
            vertices=vertices,
            annotation_points=annotation_points,
            query_line_y=None,
            purpose="local_extrema",
        )
    raise ValueError(f"unsupported function family: {family}")


def _sample_from(values: Sequence[int], rng) -> int:
    if not values:
        raise ValueError("sampling support cannot be empty")
    return int(values[int(rng.randrange(len(values)))])


def _quadratic_sample_points(*, a_value: int, h_value: int, k_value: int) -> Tuple[GraphPolylinePoint, ...]:
    return tuple(
        (
            float(x_value) / 4.0,
            float(a_value * (((float(x_value) / 4.0) - float(h_value)) ** 2) + float(k_value)),
        )
        for x_value in range(-32, 33)
    )


def _build_quadratic_scene(rng, *, target_count: int, reference_y: int | None) -> SampledFunctionGraph:
    a_value = int(rng.choice((-1, 1)))
    h_value = int(rng.randint(-4, 4))
    baseline_y = 0 if reference_y is None else int(reference_y)
    if int(target_count) != 2:
        raise ValueError(f"unsupported quadratic target_count: {target_count}")
    root_delta = int(rng.randint(1, 3))
    h_value = int(rng.randint(-6 + root_delta, 6 - root_delta))
    k_value = int(baseline_y - (a_value * (root_delta**2)))
    annotation_points = ((int(h_value - root_delta), int(baseline_y)), (int(h_value + root_delta), int(baseline_y)))
    parameters = {"a": int(a_value), "h": int(h_value), "k": int(k_value)}
    return _function_scene(
        family=FAMILY_QUADRATIC,
        polyline=_quadratic_sample_points(a_value=int(a_value), h_value=int(h_value), k_value=int(k_value)),
        annotation_points=annotation_points,
        query_line_y=reference_y,
        parameters=parameters,
    )


def _absolute_value_sample_points(
    *,
    orientation: int,
    slope: int,
    h_value: int,
    k_value: int,
) -> Tuple[GraphPolylinePoint, ...]:
    return tuple(
        (
            float(x_value) / 4.0,
            float((orientation * slope * abs((float(x_value) / 4.0) - float(h_value))) + float(k_value)),
        )
        for x_value in range(-32, 33)
    )


def _build_absolute_value_scene(rng, *, target_count: int, reference_y: int | None) -> SampledFunctionGraph:
    if int(target_count) != 2:
        raise ValueError(f"unsupported absolute-value target_count: {target_count}")
    orientation = int(rng.choice((-1, 1)))
    slope = int(rng.choice((1, 2)))
    baseline_y = 0 if reference_y is None else int(reference_y)
    root_distance = int(rng.randint(1, 3))
    h_value = int(rng.randint(-6 + root_distance, 6 - root_distance))
    k_value = int(baseline_y - (orientation * slope * root_distance))
    annotation_points = (
        (int(h_value - root_distance), int(baseline_y)),
        (int(h_value + root_distance), int(baseline_y)),
    )
    parameters = {"orientation": int(orientation), "slope": int(slope), "h": int(h_value), "k": int(k_value)}
    return _function_scene(
        family=FAMILY_ABSOLUTE_VALUE,
        polyline=_absolute_value_sample_points(
            orientation=int(orientation),
            slope=int(slope),
            h_value=int(h_value),
            k_value=int(k_value),
        ),
        annotation_points=annotation_points,
        query_line_y=reference_y,
        parameters=parameters,
    )


def _choose_distinct_integers(rng, *, count: int, support: Sequence[int]) -> Tuple[int, ...]:
    values = [int(value) for value in support]
    if int(count) > len(values):
        raise ValueError("requested too many distinct integers")
    rng.shuffle(values)
    return tuple(sorted(int(value) for value in values[: int(count)]))


def _cubic_roots_for_target(rng, *, target_count: int) -> Tuple[int, int, int]:
    if int(target_count) not in {2, 3}:
        raise ValueError(f"unsupported cubic target_count: {target_count}")
    visible_support = [-7, -5, -3, -1, 1, 3, 5, 7]
    hidden_support = [-15, -13, -11, 11, 13, 15]
    visible_roots = _choose_distinct_integers(rng, count=int(target_count), support=visible_support)
    hidden_roots = _choose_distinct_integers(rng, count=int(3 - int(target_count)), support=hidden_support)
    roots = tuple(sorted((int(value) for value in visible_roots + hidden_roots)))
    return (int(roots[0]), int(roots[1]), int(roots[2]))


def _cubic_sample_points(
    *,
    scale_value: float,
    roots: Sequence[int],
    baseline_y: int,
) -> Tuple[GraphPolylinePoint, ...]:
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


def _build_cubic_scene(rng, *, target_count: int, reference_y: int | None) -> SampledFunctionGraph:
    baseline_y = 0 if reference_y is None else int(reference_y)
    roots = _cubic_roots_for_target(rng, target_count=int(target_count))
    scale_value = float(rng.choice((-0.012, -0.01, 0.01, 0.012)))
    visible_roots = tuple(int(root) for root in roots if -9 <= int(root) <= 9)
    annotation_points = tuple(sorted({(int(root), int(baseline_y)) for root in visible_roots}))
    parameters = {"scale": float(scale_value), "roots": [int(value) for value in roots], "baseline_y": int(baseline_y)}
    return _function_scene(
        family=FAMILY_CUBIC,
        polyline=_cubic_sample_points(scale_value=float(scale_value), roots=roots, baseline_y=int(baseline_y)),
        annotation_points=annotation_points,
        query_line_y=reference_y,
        parameters=parameters,
    )


def _positions_in_window(positions: Sequence[int]) -> Tuple[int, ...]:
    return tuple(int(value) for value in positions if -9 <= int(value) <= 9)


def _sinusoid_maxima_positions(phase_shift: int) -> Tuple[int, ...]:
    return _positions_in_window([int(phase_shift + (12 * k_value)) for k_value in range(-2, 3)])


def _sinusoid_minima_positions(phase_shift: int) -> Tuple[int, ...]:
    return _positions_in_window([int(phase_shift + 6 + (12 * k_value)) for k_value in range(-2, 3)])


def _sinusoid_midline_positions(phase_shift: int) -> Tuple[int, ...]:
    return _positions_in_window([int(phase_shift + 3 + (6 * k_value)) for k_value in range(-3, 4)])


def _phase_shift_for_count(*, target_count: int, mode: str) -> int:
    candidates: List[int] = []
    for phase_shift in range(-5, 7):
        if str(mode) == "maxima":
            count = len(_sinusoid_maxima_positions(int(phase_shift)))
        elif str(mode) == "minima":
            count = len(_sinusoid_minima_positions(int(phase_shift)))
        elif str(mode) == "midline":
            count = len(_sinusoid_midline_positions(int(phase_shift)))
        elif str(mode) == "turning":
            count = len(_sinusoid_maxima_positions(int(phase_shift))) + len(_sinusoid_minima_positions(int(phase_shift)))
        else:
            raise ValueError(f"unsupported sinusoid mode: {mode}")
        if int(count) == int(target_count):
            candidates.append(int(phase_shift))
    if not candidates:
        raise ValueError(f"no sinusoid phase_shift supports {mode} target_count={target_count}")
    return int(candidates[0])


def _sinusoid_sample_points(
    *,
    amplitude: int,
    phase_shift: int,
    midline_y: int,
) -> Tuple[GraphPolylinePoint, ...]:
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


def _build_sinusoid_reference_scene(rng, *, target_count: int, reference_y: int | None) -> SampledFunctionGraph:
    if int(target_count) not in {3, 4}:
        raise ValueError(f"unsupported sinusoid reference target_count: {target_count}")
    amplitude = int(rng.randint(2, 4))
    phase_shift = _phase_shift_for_count(target_count=int(target_count), mode="midline")
    midline_y = 0 if reference_y is None else int(reference_y)
    annotation_points = tuple((int(x_value), int(midline_y)) for x_value in _sinusoid_midline_positions(int(phase_shift)))
    parameters = {"amplitude": int(amplitude), "phase_shift": int(phase_shift), "midline_y": int(midline_y), "period": 12}
    return _function_scene(
        family=FAMILY_SINUSOID,
        polyline=_sinusoid_sample_points(amplitude=int(amplitude), phase_shift=int(phase_shift), midline_y=int(midline_y)),
        annotation_points=annotation_points,
        query_line_y=reference_y,
        parameters=parameters,
    )


def _build_sinusoid_turning_scene(rng, *, target_count: int) -> SampledFunctionGraph:
    if int(target_count) not in {3, 4}:
        raise ValueError(f"unsupported sinusoid turning target_count: {target_count}")
    amplitude = int(rng.randint(2, 4))
    phase_shift = _phase_shift_for_count(target_count=int(target_count), mode="turning")
    midline_y = int(_sample_from((-2, -1, 0, 1, 2), rng))
    annotation_points = tuple(
        (int(x_value), int(midline_y + amplitude)) for x_value in _sinusoid_maxima_positions(int(phase_shift))
    ) + tuple((int(x_value), int(midline_y - amplitude)) for x_value in _sinusoid_minima_positions(int(phase_shift)))
    parameters = {"amplitude": int(amplitude), "phase_shift": int(phase_shift), "midline_y": int(midline_y), "period": 12}
    return _function_scene(
        family=FAMILY_SINUSOID,
        polyline=_sinusoid_sample_points(amplitude=int(amplitude), phase_shift=int(phase_shift), midline_y=int(midline_y)),
        annotation_points=annotation_points,
        query_line_y=None,
        parameters=parameters,
    )


def _build_sinusoid_local_scene(rng, *, target_count: int, extremum_sign: int) -> SampledFunctionGraph:
    if int(target_count) not in {1, 2}:
        raise ValueError(f"unsupported sinusoid local-extremum target_count: {target_count}")
    amplitude = int(rng.randint(2, 4))
    sign = -1 if int(extremum_sign) < 0 else 1
    mode = "minima" if sign < 0 else "maxima"
    phase_shift = _phase_shift_for_count(target_count=int(target_count), mode=mode)
    midline_y = int(_sample_from((-2, -1, 0, 1, 2), rng))
    positions = _sinusoid_minima_positions(int(phase_shift)) if sign < 0 else _sinusoid_maxima_positions(int(phase_shift))
    annotation_points = tuple((int(x_value), int(midline_y + (sign * amplitude))) for x_value in positions)
    parameters = {"amplitude": int(amplitude), "phase_shift": int(phase_shift), "midline_y": int(midline_y), "period": 12}
    return _function_scene(
        family=FAMILY_SINUSOID,
        polyline=_sinusoid_sample_points(amplitude=int(amplitude), phase_shift=int(phase_shift), midline_y=int(midline_y)),
        annotation_points=annotation_points,
        query_line_y=None,
        parameters=parameters,
    )


def _piecewise_x_positions(key: str) -> Tuple[int, ...]:
    fallback = (
        DEFAULTS.piecewise_intersection_x_positions
        if str(key) == "piecewise_intersection_x_positions"
        else DEFAULTS.piecewise_turning_x_positions
    )
    return int_tuple_default(str(key), fallback)


def _piecewise_polyline_for_intersections(
    rng,
    *,
    target_count: int,
    baseline_y: int,
) -> Tuple[Tuple[GraphPoint, ...], Tuple[GraphPoint, ...]]:
    x_positions = list(_piecewise_x_positions("piecewise_intersection_x_positions"))
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
        vertices.append((int(x_value), int(baseline_y + (sign_value * int(rng.randint(2, 4))))))
    return tuple(vertices), tuple(annotation_points)


def _piecewise_polyline_for_turning_points(
    rng,
    *,
    target_count: int,
) -> Tuple[Tuple[GraphPoint, ...], Tuple[GraphPoint, ...]]:
    vertex_count = int(target_count) + 2
    x_positions = list(_piecewise_x_positions("piecewise_turning_x_positions"))
    start_index = int(rng.randint(0, len(x_positions) - vertex_count))
    selected_x = x_positions[start_index : start_index + vertex_count]
    sign_start = int(rng.choice((-1, 1)))
    vertices = tuple(
        (int(x_value), int(sign_start * ((-1) ** index) * int(rng.randint(2, 5))))
        for index, x_value in enumerate(selected_x)
    )
    return vertices, tuple(vertices[1:-1])


def _piecewise_polyline_for_local_extrema(
    rng,
    *,
    target_count: int,
    extremum_sign: int,
) -> Tuple[Tuple[GraphPoint, ...], Tuple[GraphPoint, ...]]:
    sign = -1 if int(extremum_sign) < 0 else 1
    vertex_count = int((2 * int(target_count)) + 1)
    x_positions = list(_piecewise_x_positions("piecewise_turning_x_positions"))
    start_index = int(rng.randint(0, len(x_positions) - vertex_count))
    selected_x = x_positions[start_index : start_index + vertex_count]
    target_is_low = sign < 0
    vertices: List[GraphPoint] = []
    annotation_points: List[GraphPoint] = []
    for index, x_value in enumerate(selected_x):
        is_target_slot = bool(index % 2 == 1)
        high = int(rng.randint(2, 5))
        low = -int(rng.randint(2, 5))
        y_value = low if (is_target_slot == target_is_low) else high
        point = (int(x_value), int(y_value))
        vertices.append(point)
        if 0 < index < (vertex_count - 1) and is_target_slot:
            annotation_points.append(point)
    return tuple(vertices), tuple(annotation_points)


def _function_scene(
    *,
    family: str,
    polyline: Sequence[GraphPolylinePoint],
    annotation_points: Sequence[GraphPoint],
    query_line_y: int | None,
    parameters: Mapping[str, Any],
) -> SampledFunctionGraph:
    return SampledFunctionGraph(
        polyline_graph=tuple((float(x), float(y)) for x, y in polyline),
        annotation_graph_points=tuple((int(x), int(y)) for x, y in annotation_points),
        query_line_y=(None if query_line_y is None else int(query_line_y)),
        scene_entities=[
            {
                "entity_id": "function_graph",
                "entity_type": "function_graph",
                "family": str(family),
                "parameters": dict(parameters),
            }
        ],
        render_map={
            "scene_variant": str(family),
            "function_parameters": dict(parameters),
            "annotation_points_graph": [list(point) for point in annotation_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        execution_trace={
            "family": str(family),
            "parameters": dict(parameters),
            "annotation_points_graph": [list(point) for point in annotation_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        object_count=1,
    )


def _piecewise_scene(
    *,
    vertices: Sequence[GraphPoint],
    annotation_points: Sequence[GraphPoint],
    query_line_y: int | None,
    purpose: str,
) -> SampledFunctionGraph:
    return SampledFunctionGraph(
        polyline_graph=tuple((float(point[0]), float(point[1])) for point in vertices),
        annotation_graph_points=tuple((int(x), int(y)) for x, y in annotation_points),
        query_line_y=(None if query_line_y is None else int(query_line_y)),
        scene_entities=[
            {
                "entity_id": "function_graph",
                "entity_type": "function_graph",
                "family": FAMILY_PIECEWISE_LINEAR,
                "vertices_graph": [list(point) for point in vertices],
            }
        ],
        render_map={
            "scene_variant": FAMILY_PIECEWISE_LINEAR,
            "polyline_vertices_graph": [list(point) for point in vertices],
            "annotation_points_graph": [list(point) for point in annotation_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        execution_trace={
            "family": FAMILY_PIECEWISE_LINEAR,
            "purpose": str(purpose),
            "polyline_vertices_graph": [list(point) for point in vertices],
            "annotation_points_graph": [list(point) for point in annotation_points],
            "query_line_y": (None if query_line_y is None else int(query_line_y)),
        },
        object_count=int(len(vertices)),
    )
