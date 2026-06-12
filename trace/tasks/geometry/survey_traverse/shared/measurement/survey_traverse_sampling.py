"""Problem/query sampling for survey traverse tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ......core.seed import spawn_rng
from .....shared.config_defaults import group_default
from .....shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.fixed_query import geometry_selected_probability_map as _probability_map

from .survey_traverse_common import (
    AREA_QUERY_IDS,
    BEARING_SUPPORT,
    ELEVATION_QUERY_IDS,
    QUERY_IDS,
    AREA_NAMESPACE,
    BEARING_NAMESPACE,
    ELEVATION_NAMESPACE,
    TURN_SUPPORT,
    _COORDINATE_TRAVERSE_CASES,
    _LEVELING_CASES,
    _OFFSET_TRAPEZOID_CASES,
    _ResolvedAreaProblem,
    _ResolvedElevationProblem,
    _ResolvedProblem,
    _SLOPE_ELEVATION_CASES,
    _bearing_to_unit_vector,
    _normalize_bearing,
)

def _resolve_query_id(*, instance_seed: int, params: Mapping[str, Any]) -> tuple[str, Dict[str, float]]:
    explicit = params.get("query_id")
    if explicit is not None:
        query_id = str(explicit)
        if query_id not in QUERY_IDS:
            raise ValueError(f"unsupported query_id for {BEARING_NAMESPACE}: {query_id}")
        return query_id, _probability_map(QUERY_IDS, selected=query_id)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{BEARING_NAMESPACE}.query_id",
    )
    return str(QUERY_IDS[int(index) % len(QUERY_IDS)]), _probability_map(QUERY_IDS)

def _resolve_elevation_query_id(*, instance_seed: int, params: Mapping[str, Any]) -> tuple[str, Dict[str, float]]:
    explicit = params.get("query_id")
    if explicit is not None:
        query_id = str(explicit)
        if query_id not in ELEVATION_QUERY_IDS:
            raise ValueError(f"unsupported query_id for {ELEVATION_NAMESPACE}: {query_id}")
        return query_id, _probability_map(ELEVATION_QUERY_IDS, selected=query_id)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{ELEVATION_NAMESPACE}.query_id",
    )
    return str(ELEVATION_QUERY_IDS[int(index) % len(ELEVATION_QUERY_IDS)]), _probability_map(ELEVATION_QUERY_IDS)

def _resolve_area_query_id(*, instance_seed: int, params: Mapping[str, Any]) -> tuple[str, Dict[str, float]]:
    explicit = params.get("query_id")
    if explicit is not None:
        query_id = str(explicit)
        if query_id not in AREA_QUERY_IDS:
            raise ValueError(f"unsupported query_id for {AREA_NAMESPACE}: {query_id}")
        return query_id, _probability_map(AREA_QUERY_IDS, selected=query_id)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{AREA_NAMESPACE}.query_id",
    )
    return str(AREA_QUERY_IDS[int(index) % len(AREA_QUERY_IDS)]), _probability_map(AREA_QUERY_IDS)

def _case_probability_map(cases: Sequence[Tuple[int, ...]], selected: Tuple[int, ...] | None = None) -> Dict[str, float]:
    resolved = tuple(",".join(str(value) for value in case) for case in cases)
    if selected is not None:
        selected_key = ",".join(str(value) for value in selected)
        return {key: (1.0 if key == selected_key else 0.0) for key in resolved}
    probability = 1.0 / float(max(1, len(resolved)))
    return {key: probability for key in resolved}

def _select_elevation_case(
    *,
    cases: Sequence[Tuple[int, ...]],
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> tuple[Tuple[int, ...], Dict[str, float]]:
    explicit = params.get("elevation_case")
    if explicit is not None:
        if not isinstance(explicit, Sequence) or isinstance(explicit, (str, bytes)):
            raise ValueError("elevation_case must be a numeric sequence")
        selected = tuple(int(value) for value in explicit)
        if selected not in cases:
            raise ValueError(f"elevation_case={selected} is not supported by {namespace}")
        return selected, _case_probability_map(cases, selected=selected)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=namespace,
    )
    selected = tuple(cases[int(index) % len(cases)])
    return selected, _case_probability_map(cases)

def _select_area_case(
    *,
    cases: Sequence[Tuple[int, ...]],
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> tuple[Tuple[int, ...], Dict[str, float]]:
    explicit = params.get("area_case")
    if explicit is not None:
        if not isinstance(explicit, Sequence) or isinstance(explicit, (str, bytes)):
            raise ValueError("area_case must be a numeric sequence")
        selected = tuple(int(value) for value in explicit)
        if selected not in cases:
            raise ValueError(f"area_case={selected} is not supported by {namespace}")
        return selected, _case_probability_map(cases, selected=selected)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=namespace,
    )
    selected = tuple(cases[int(index) % len(cases)])
    return selected, _case_probability_map(cases)

def _select_bearing(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    key: str,
) -> tuple[int, Dict[str, float]]:
    explicit = params.get(key)
    if explicit is not None:
        bearing = int(explicit)
        if bearing not in BEARING_SUPPORT:
            raise ValueError(f"{key}={bearing} is not supported by {BEARING_NAMESPACE}")
        return bearing, _probability_map(BEARING_SUPPORT, selected=bearing)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=namespace,
    )
    bearing = int(BEARING_SUPPORT[int(index) % len(BEARING_SUPPORT)])
    return bearing, _probability_map(BEARING_SUPPORT)

def _select_turn(*, params: Mapping[str, Any], instance_seed: int) -> tuple[int, str, Dict[str, float]]:
    explicit_turn = params.get("turn_angle")
    if explicit_turn is not None:
        turn_angle = int(explicit_turn)
        if turn_angle not in TURN_SUPPORT:
            raise ValueError(f"turn_angle={turn_angle} is not supported by {BEARING_NAMESPACE}")
        turn_probabilities = _probability_map(TURN_SUPPORT, selected=turn_angle)
    else:
        index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{BEARING_NAMESPACE}.turn_angle",
        )
        turn_angle = int(TURN_SUPPORT[int(index) % len(TURN_SUPPORT)])
        turn_probabilities = _probability_map(TURN_SUPPORT)

    explicit_direction = params.get("turn_direction")
    if explicit_direction is not None:
        turn_direction = str(explicit_direction)
        if turn_direction not in {"left", "right"}:
            raise ValueError("turn_direction must be 'left' or 'right'")
    else:
        index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{BEARING_NAMESPACE}.turn_direction",
        )
        turn_direction = "left" if int(index) % 2 == 0 else "right"
    return int(turn_angle), str(turn_direction), turn_probabilities

def _station_labels(*, params: Mapping[str, Any], instance_seed: int, namespace: str = BEARING_NAMESPACE) -> Tuple[str, str, str]:
    explicit = params.get("station_labels")
    if explicit is not None:
        if not isinstance(explicit, Sequence) or isinstance(explicit, (str, bytes)) or len(explicit) != 3:
            raise ValueError("station_labels must be a three-item sequence")
        labels = tuple(str(value).strip().upper() for value in explicit)
        if len(set(labels)) != 3 or any(len(label) != 1 or not label.isalpha() for label in labels):
            raise ValueError("station_labels must contain three distinct single letters")
        return labels  # type: ignore[return-value]
    pools = (
        ("A", "B", "C"),
        ("P", "Q", "R"),
        ("K", "L", "M"),
        ("S", "T", "U"),
        ("D", "E", "F"),
        ("G", "H", "J"),
    )
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.station_labels",
    )
    return tuple(pools[int(index) % len(pools)])  # type: ignore[return-value]

def _station_labels4(*, params: Mapping[str, Any], instance_seed: int, namespace: str) -> Tuple[str, str, str, str]:
    explicit = params.get("station_labels")
    if explicit is not None:
        if not isinstance(explicit, Sequence) or isinstance(explicit, (str, bytes)) or len(explicit) not in {3, 4}:
            raise ValueError("station_labels must be a three- or four-item sequence")
        labels = tuple(str(value).strip().upper() for value in explicit)
        if len(set(labels)) != len(labels) or any(len(label) != 1 or not label.isalpha() for label in labels):
            raise ValueError("station_labels must contain distinct single letters")
        if len(labels) == 4:
            return labels  # type: ignore[return-value]
    labels3 = _station_labels(params=params, instance_seed=int(instance_seed), namespace=namespace)
    for candidate in ("D", "E", "F", "V", "W", "X", "Y", "Z"):
        if candidate not in labels3:
            return (labels3[0], labels3[1], labels3[2], candidate)
    raise ValueError("could not construct four unique station labels")

def _resolve_problem(*, instance_seed: int, params: Mapping[str, Any]) -> _ResolvedProblem:
    query_id, query_probabilities = _resolve_query_id(instance_seed=int(instance_seed), params=params)
    labels = _station_labels(params=params, instance_seed=int(instance_seed))
    if query_id == "bearing_from_back_bearing":
        answer, bearing_probabilities = _select_bearing(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{BEARING_NAMESPACE}.answer_bearing",
            key="target_bearing",
        )
        given_bearing = _normalize_bearing(int(answer) + 180)
        return _ResolvedProblem(
            query_id=query_id,
            answer=int(answer),
            known_bearing=int(answer),
            given_bearing=int(given_bearing),
            station_labels=labels,
            turn_angle=None,
            turn_direction=None,
            query_probabilities=query_probabilities,
            bearing_probabilities=bearing_probabilities,
            turn_probabilities={},
        )

    base_bearing, bearing_probabilities = _select_bearing(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{BEARING_NAMESPACE}.base_bearing",
        key="base_bearing",
    )
    turn_angle, turn_direction, turn_probabilities = _select_turn(params=params, instance_seed=int(instance_seed))
    answer = (
        _normalize_bearing(int(base_bearing) - int(turn_angle))
        if turn_direction == "left"
        else _normalize_bearing(int(base_bearing) + int(turn_angle))
    )
    if answer == 0:
        answer = 360
    if answer >= 360:
        raise ValueError("closed traverse generated unsupported 360-degree answer")
    return _ResolvedProblem(
        query_id=query_id,
        answer=int(answer),
        known_bearing=int(base_bearing),
        given_bearing=int(base_bearing),
        station_labels=labels,
        turn_angle=int(turn_angle),
        turn_direction=str(turn_direction),
        query_probabilities=query_probabilities,
        bearing_probabilities=bearing_probabilities,
        turn_probabilities=turn_probabilities,
    )

def _resolve_elevation_problem(*, instance_seed: int, params: Mapping[str, Any]) -> _ResolvedElevationProblem:
    query_id, query_probabilities = _resolve_elevation_query_id(instance_seed=int(instance_seed), params=params)
    labels = _station_labels(
        params=params,
        instance_seed=int(instance_seed),
        namespace=ELEVATION_NAMESPACE,
    )
    if query_id == "leveling_station_elevation":
        case, case_probabilities = _select_elevation_case(
            cases=_LEVELING_CASES,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{ELEVATION_NAMESPACE}.leveling_case",
        )
        reference_elevation, backsight, foresight = [int(value) for value in case]
        height_of_instrument = int(reference_elevation + backsight)
        target_elevation = int(height_of_instrument - foresight)
        return _ResolvedElevationProblem(
            query_id=query_id,
            answer=target_elevation,
            reference_elevation=reference_elevation,
            target_elevation=target_elevation,
            station_labels=labels,
            backsight=backsight,
            foresight=foresight,
            height_of_instrument=height_of_instrument,
            slope_distance=None,
            rise_per_20=None,
            total_rise=None,
            query_probabilities=query_probabilities,
            case_probabilities=case_probabilities,
        )

    case, case_probabilities = _select_elevation_case(
        cases=_SLOPE_ELEVATION_CASES,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{ELEVATION_NAMESPACE}.slope_case",
    )
    reference_elevation, slope_distance, rise_per_20 = [int(value) for value in case]
    total_rise = int((slope_distance // 20) * rise_per_20)
    target_elevation = int(reference_elevation + total_rise)
    return _ResolvedElevationProblem(
        query_id=query_id,
        answer=target_elevation,
        reference_elevation=reference_elevation,
        target_elevation=target_elevation,
        station_labels=labels,
        backsight=None,
        foresight=None,
        height_of_instrument=None,
        slope_distance=slope_distance,
        rise_per_20=rise_per_20,
        total_rise=total_rise,
        query_probabilities=query_probabilities,
        case_probabilities=case_probabilities,
    )

def _polygon_area(points: Sequence[Tuple[int, int]]) -> int:
    twice_area = 0
    for idx, (x0, y0) in enumerate(points):
        x1, y1 = points[(idx + 1) % len(points)]
        twice_area += int(x0) * int(y1) - int(y0) * int(x1)
    twice_area = abs(int(twice_area))
    if twice_area % 2 != 0:
        raise ValueError("survey coordinate traverse case must have integer area")
    return int(twice_area // 2)

def _offset_trapezoid_area(chainages: Sequence[int], offsets: Sequence[int]) -> int:
    if len(chainages) != len(offsets):
        raise ValueError("chainage and offset counts must match")
    twice_area = 0
    for left, right in zip(range(len(chainages) - 1), range(1, len(chainages))):
        width = int(chainages[right]) - int(chainages[left])
        if width <= 0:
            raise ValueError("chainages must be strictly increasing")
        twice_area += int(width) * (int(offsets[left]) + int(offsets[right]))
    if twice_area % 2 != 0:
        raise ValueError("survey offset case must have integer area")
    return int(twice_area // 2)

def _resolve_area_problem(*, instance_seed: int, params: Mapping[str, Any]) -> _ResolvedAreaProblem:
    query_id, query_probabilities = _resolve_area_query_id(instance_seed=int(instance_seed), params=params)
    labels = _station_labels4(
        params=params,
        instance_seed=int(instance_seed),
        namespace=AREA_NAMESPACE,
    )
    if query_id == "coordinate_traverse_area":
        case, case_probabilities = _select_area_case(
            cases=_COORDINATE_TRAVERSE_CASES,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{AREA_NAMESPACE}.coordinate_case",
        )
        points = tuple((int(case[idx]), int(case[idx + 1])) for idx in range(0, len(case), 2))
        return _ResolvedAreaProblem(
            query_id=query_id,
            answer=_polygon_area(points),
            station_labels=labels,
            coordinate_points=points,
            chainages=(),
            offsets=(),
            formula_family="survey_coordinate_traverse_area",
            query_probabilities=query_probabilities,
            case_probabilities=case_probabilities,
        )

    case, case_probabilities = _select_area_case(
        cases=_OFFSET_TRAPEZOID_CASES,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{AREA_NAMESPACE}.offset_case",
    )
    chainages = (0, int(case[0]), int(case[1]), int(case[2]))
    offsets = (int(case[3]), int(case[4]), int(case[5]), int(case[6]))
    return _ResolvedAreaProblem(
        query_id=query_id,
        answer=_offset_trapezoid_area(chainages, offsets),
        station_labels=labels,
        coordinate_points=(),
        chainages=chainages,
        offsets=offsets,
        formula_family="survey_offset_trapezoid_area",
        query_probabilities=query_probabilities,
        case_probabilities=case_probabilities,
    )


__all__ = [
    '_resolve_query_id',
    '_resolve_elevation_query_id',
    '_resolve_area_query_id',
    '_case_probability_map',
    '_select_elevation_case',
    '_select_area_case',
    '_select_bearing',
    '_select_turn',
    '_station_labels',
    '_station_labels4',
    '_resolve_problem',
    '_resolve_elevation_problem',
    '_polygon_area',
    '_offset_trapezoid_area',
    '_resolve_area_problem',
]
