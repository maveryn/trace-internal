"""Dataset and query construction for curve-panel chart tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from ....shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.label_assets import (
    resolve_chart_entity_labels,
    resolve_chart_panel_labels,
    validate_chart_label_namespaces,
)
from ...shared.labeled_chart_common import resolve_chart_axis_variant
from .multipanel_common import (
    SCENE_NAMESPACE,
    SUPPORTED_POINT_THRESHOLD_DIRECTIONS,
    SUPPORTED_THRESHOLD_CROSSING_DIRECTIONS,
    _GEN_DEFAULTS,
    _Curve,
    _Dataset,
    _Intersection,
    _Panel,
    _Query,
    _ThresholdCrossing,
    _balanced_choice,
    _gen_int,
    _intersection_id,
    _method_count,
    _method_count_max,
    _palette,
    _panel_answer_index_support,
    _panel_count,
    _point_id,
    _threshold_crossing_id,
    _without_sample_cursor,
)


def _method_labels_for_seed(*, count: int, instance_seed: int) -> Tuple[str, ...]:
    labels = resolve_chart_entity_labels(
        spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.method_labels"),
        count=int(count),
        min_chars=2,
        max_chars=7,
        allow_spaces=False,
    ).labels
    return tuple(str(label) for label in labels)


def _resolved_label_metadata(resolved: Any) -> Dict[str, Any]:
    return {
        "label_variant": str(resolved.label_variant),
        "label_pool_kind": str(resolved.label_pool_kind),
        "label_source_kind": str(resolved.label_source_kind),
        "label_bucket": str(resolved.label_bucket),
        "label_manifest": str(resolved.label_manifest),
        "label_filter": dict(resolved.label_filter),
        "label_bucket_probabilities": dict(resolved.label_bucket_probabilities),
    }


def _panel_labels_for_seed(
    *,
    count: int,
    params: Mapping[str, Any],
    instance_seed: int,
    reserved_labels: Sequence[str] = (),
) -> Tuple[Tuple[str, ...], Dict[str, Any]]:
    resolved = resolve_chart_panel_labels(
        spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.panel_labels"),
        count=int(count),
        min_chars=1,
        max_chars=10,
        allow_spaces=False,
        variant_weights=params.get(
            "panel_label_variant_weights",
            group_default(
                _GEN_DEFAULTS,
                "panel_label_variant_weights",
                {
                    "subplot_letters": 1.0,
                    "technical_topics": 0.75,
                    "condition_labels": 0.5,
                    "named_compact": 0.5,
                    "temporal_sequence": 0.25,
                },
            ),
        ),
        reserved_labels=tuple(str(label) for label in reserved_labels),
    )
    collision_check = validate_chart_label_namespaces(
        panel_labels=resolved.labels,
        other_label_groups={"method_labels": tuple(str(label) for label in reserved_labels)},
        context="scientific curve-panel labels",
    )
    return tuple(str(label) for label in resolved.labels), {
        "panel_label_resolution": _resolved_label_metadata(resolved),
        "panel_label_collision_check": dict(collision_check),
    }


def _x_values(params: Mapping[str, Any], *, instance_seed: int, min_required: int = 4) -> Tuple[int, ...]:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="x_tick_count_min",
        max_key="x_tick_count_max",
        fallback_min=6,
        fallback_max=12,
        context=f"generation defaults for {SCENE_NAMESPACE}",
    )
    low = max(4, int(min_required), int(low))
    high = max(int(low), int(high))
    count = int(
        _balanced_choice(
            list(range(int(low), int(high) + 1)),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.x_tick_count",
        )
    )
    step_min = int(_gen_int(params, "x_step_min", 5))
    step_max = int(_gen_int(params, "x_step_max", 20))
    span_min = int(_gen_int(params, "x_span_min", 50))
    span_max = int(_gen_int(params, "x_span_max", 100))
    if int(step_min) > int(step_max):
        raise ValueError("x_step_min must be <= x_step_max")
    if int(span_min) > int(span_max):
        raise ValueError("x_span_min must be <= x_span_max")
    step_support = [
        int(step)
        for step in range(max(1, int(step_min)), int(step_max) + 1)
        if int(span_min) <= int(step) * max(1, int(count) - 1) <= int(span_max)
    ]
    if not step_support:
        raise ValueError("x step/span support is empty for sampled x_tick_count")
    step = int(
        _balanced_choice(
            step_support,
            params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.x_step:{int(count)}",
        )
    )
    return tuple(int(index) * int(step) for index in range(int(count)))


def _threshold_values(params: Mapping[str, Any]) -> Tuple[int, ...]:
    raw = params.get("threshold_values", _GEN_DEFAULTS.get("threshold_values", (45, 55, 65)))
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        values = tuple(int(value) for value in raw)
        if values:
            return values
    return (45, 55, 65)


def _threshold_for_x_values(params: Mapping[str, Any], *, instance_seed: int, x_values: Sequence[int]) -> int:
    support = tuple(value for value in _threshold_values(params) if 10 <= int(value) <= 90)
    if not support:
        support = (45, 55, 65)
    return int(
        _balanced_choice(
            support,
            _without_sample_cursor(params),
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.threshold:{len(x_values)}:{int(max(x_values)) if x_values else 0}",
        )
    )


def _resolve_point_threshold_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_POINT_THRESHOLD_DIRECTIONS,
        **{"task" "_id": SCENE_NAMESPACE},
        explicit_key="point_threshold_direction",
        weights_key="point_threshold_direction_weights",
        balance_flag_key="balanced_point_threshold_direction_sampling",
        axis_namespace="point_threshold_direction",
    )


def _resolve_threshold_crossing_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_THRESHOLD_CROSSING_DIRECTIONS,
        **{"task" "_id": SCENE_NAMESPACE},
        explicit_key="threshold_crossing_direction",
        weights_key="threshold_crossing_direction_weights",
        balance_flag_key="balanced_threshold_crossing_direction_sampling",
        axis_namespace="threshold_crossing_direction",
    )

def _random_curve_values(*, rng: Any, count: int, value_min: int, value_max: int) -> List[int]:
    current = int(rng.randint(28, 72))
    values: List[int] = []
    for _ in range(int(count)):
        current += int(rng.randint(-15, 15))
        current = max(int(value_min) + 8, min(int(value_max) - 8, int(current)))
        values.append(int(current))
    return values


def _make_random_panels(
    *,
    panel_labels: Sequence[str],
    method_labels: Sequence[str],
    x_count: int,
    colors: Sequence[RGB],
    instance_seed: int,
    namespace: str,
    value_min: int,
    value_max: int,
) -> Dict[str, Dict[str, List[int]]]:
    values: Dict[str, Dict[str, List[int]]] = {}
    for panel in panel_labels:
        values[str(panel)] = {}
        for method in method_labels:
            rng = spawn_rng(int(instance_seed), f"{str(namespace)}:{str(panel)}:{str(method)}")
            values[str(panel)][str(method)] = _random_curve_values(
                rng=rng,
                count=int(x_count),
                value_min=int(value_min),
                value_max=int(value_max),
            )
    return values


def _panels_from_values(
    *,
    values_by_panel_method: Mapping[str, Mapping[str, Sequence[int]]],
    panel_labels: Sequence[str],
    method_labels: Sequence[str],
    colors: Sequence[RGB],
) -> Tuple[_Panel, ...]:
    panels: List[_Panel] = []
    for panel in panel_labels:
        curves: List[_Curve] = []
        for index, method in enumerate(method_labels):
            curves.append(
                _Curve(
                    method_label=str(method),
                    values=tuple(int(value) for value in values_by_panel_method[str(panel)][str(method)]),
                    color_rgb=tuple(colors[int(index) % len(colors)]),
                )
            )
        panels.append(_Panel(panel_label=str(panel), curves=tuple(curves)))
    return tuple(panels)


def _common_axes(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    min_x_tick_count: int = 4,
) -> Tuple[Tuple[int, ...], int, int, int, Tuple[str, ...], Tuple[str, ...], Dict[str, Any]]:
    non_answer_params = _without_sample_cursor(params)
    panel_count = _panel_count(non_answer_params, instance_seed=int(instance_seed))
    method_count = _method_count(non_answer_params, instance_seed=int(instance_seed))
    x_values = _x_values(
        non_answer_params,
        instance_seed=int(instance_seed),
        min_required=int(min_x_tick_count),
    )
    y_min = int(_gen_int(params, "y_value_min", 0))
    y_max = int(_gen_int(params, "y_value_max", 100))
    if int(y_min) >= int(y_max):
        raise ValueError("y_value_min must be lower than y_value_max")
    method_labels = _method_labels_for_seed(count=int(method_count), instance_seed=int(instance_seed))
    panel_labels, panel_label_meta = _panel_labels_for_seed(
        count=int(panel_count),
        params=params,
        instance_seed=int(instance_seed),
        reserved_labels=method_labels,
    )
    return (
        tuple(x_values),
        int(y_min),
        int(y_max),
        int(panel_count),
        tuple(panel_labels),
        tuple(method_labels),
        dict(panel_label_meta),
    )


def _build_curve_at_x_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    non_answer_params = _without_sample_cursor(params)
    method_answer_support = _method_labels_for_seed(count=_method_count_max(params), instance_seed=int(instance_seed))
    answer_method = str(
        _balanced_choice(
            method_answer_support,
            params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.curve_at_x.answer",
        )
    )
    min_method_count = max(3, int(method_answer_support.index(str(answer_method))) + 1)
    panel_count = _panel_count(non_answer_params, instance_seed=int(instance_seed))
    method_count = _method_count(non_answer_params, instance_seed=int(instance_seed), min_required=int(min_method_count))
    x_values = _x_values(non_answer_params, instance_seed=int(instance_seed))
    y_min = int(_gen_int(params, "y_value_min", 0))
    y_max = int(_gen_int(params, "y_value_max", 100))
    if int(y_min) >= int(y_max):
        raise ValueError("y_value_min must be lower than y_value_max")
    method_labels = _method_labels_for_seed(count=int(method_count), instance_seed=int(instance_seed))
    panel_labels, panel_label_meta = _panel_labels_for_seed(
        count=int(panel_count),
        params=params,
        instance_seed=int(instance_seed),
        reserved_labels=method_labels,
    )
    colors = _palette(params)
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.curve_at_x")
    query_panel = str(
        _balanced_choice(panel_labels, non_answer_params, instance_seed=int(instance_seed), namespace=f"{SCENE_NAMESPACE}.curve_at_x.panel")
    )
    x_index = 1 + int(rng.randint(0, max(1, len(x_values) - 3)))
    x_value = int(x_values[int(x_index)])
    values = _make_random_panels(
        panel_labels=panel_labels,
        method_labels=method_labels,
        x_count=len(x_values),
        colors=colors,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.curve_at_x.values",
        value_min=y_min,
        value_max=y_max,
    )
    winner_min = int(_gen_int(params, "curve_at_x_winner_min", 82))
    winner_max = int(_gen_int(params, "curve_at_x_winner_max", 92))
    gap_min = max(1, int(_gen_int(params, "curve_at_x_gap_min", 24)))
    gap_max = max(int(gap_min), int(_gen_int(params, "curve_at_x_gap_max", 56)))
    winner_min = max(int(y_min) + int(gap_min) + 5, min(int(y_max) - 5, int(winner_min)))
    winner_max = max(int(winner_min), min(int(y_max) - 5, int(winner_max)))
    winning_value = int(rng.randint(int(winner_min), int(winner_max)))
    for index, method in enumerate(method_labels):
        if str(method) == str(answer_method):
            values[str(query_panel)][str(method)][int(x_index)] = int(winning_value)
        else:
            gap = int(rng.randint(int(gap_min), int(gap_max)))
            values[str(query_panel)][str(method)][int(x_index)] = max(
                int(y_min) + 5,
                min(int(y_max) - 5, int(winning_value) - int(gap)),
            )

    annotation_ids = tuple(_point_id(str(query_panel), str(method), int(x_value)) for method in method_labels)
    query = _Query(
        prompt_key="curve_at_x_extremum_label",
        scene_variant="multipanel_line_grid",
        answer=str(answer_method),
        answer_type="string",
        panel_label=str(query_panel),
        method_label=str(answer_method),
        method_a_label="",
        method_b_label="",
        x_value=int(x_value),
        start_x_value=0,
        end_x_value=0,
        threshold_value=0,
        threshold_direction="",
        annotation_panel_labels=(str(query_panel),),
        annotation_point_ids=annotation_ids,
        annotation_intersection_ids=(),
        annotation_threshold_crossing_ids=(),
        trace={
            "query_panel_label": str(query_panel),
            "query_x_value": int(x_value),
            "compared_method_labels": list(method_labels),
            "values_at_query_x": {
                str(method): int(values[str(query_panel)][str(method)][int(x_index)])
                for method in method_labels
            },
            **dict(panel_label_meta),
        },
    )
    return _Dataset(
        scene_variant="multipanel_line_grid",
        x_values=tuple(x_values),
        y_min=int(y_min),
        y_max=int(y_max),
        panels=_panels_from_values(values_by_panel_method=values, panel_labels=panel_labels, method_labels=method_labels, colors=colors),
        query=query,
        intersections=(),
        threshold_crossings=(),
    )


def _build_threshold_count_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    non_answer_params = _without_sample_cursor(params)
    target_count = int(
        _balanced_choice(
            list(range(1, _method_count_max(params) + 1)),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.threshold_count.answer",
        )
    )
    panel_count = _panel_count(non_answer_params, instance_seed=int(instance_seed))
    method_count = _method_count(non_answer_params, instance_seed=int(instance_seed), min_required=int(target_count))
    x_values = _x_values(non_answer_params, instance_seed=int(instance_seed))
    y_min = int(_gen_int(params, "y_value_min", 0))
    y_max = int(_gen_int(params, "y_value_max", 100))
    if int(y_min) >= int(y_max):
        raise ValueError("y_value_min must be lower than y_value_max")
    method_labels = _method_labels_for_seed(count=int(method_count), instance_seed=int(instance_seed))
    panel_labels, panel_label_meta = _panel_labels_for_seed(
        count=int(panel_count),
        params=params,
        instance_seed=int(instance_seed),
        reserved_labels=method_labels,
    )
    colors = _palette(params)
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.threshold_count")
    query_panel = str(
        _balanced_choice(panel_labels, _without_sample_cursor(params), instance_seed=int(instance_seed), namespace=f"{SCENE_NAMESPACE}.threshold_count.panel")
    )
    x_index = 1 + int(rng.randint(0, max(1, len(x_values) - 3)))
    x_value = int(x_values[int(x_index)])
    threshold = _threshold_for_x_values(params, instance_seed=int(instance_seed), x_values=x_values)
    values = _make_random_panels(
        panel_labels=panel_labels,
        method_labels=method_labels,
        x_count=len(x_values),
        colors=colors,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.threshold_count.values",
        value_min=y_min,
        value_max=y_max,
    )
    shuffled_methods = list(method_labels)
    rng.shuffle(shuffled_methods)
    above_methods = set(str(method) for method in shuffled_methods[: int(target_count)])
    for method in method_labels:
        if str(method) in above_methods:
            values[str(query_panel)][str(method)][int(x_index)] = int(rng.randint(int(threshold) + 8, min(int(y_max) - 5, int(threshold) + 34)))
        else:
            values[str(query_panel)][str(method)][int(x_index)] = int(rng.randint(max(int(y_min) + 5, int(threshold) - 34), int(threshold) - 4))

    annotation_ids = tuple(
        _point_id(str(query_panel), str(method), int(x_value))
        for method in method_labels
        if str(method) in above_methods
    )
    query = _Query(
        prompt_key="threshold_series_count",
        scene_variant="multipanel_line_grid",
        answer=int(target_count),
        answer_type="integer",
        panel_label=str(query_panel),
        method_label="",
        method_a_label="",
        method_b_label="",
        x_value=int(x_value),
        start_x_value=0,
        end_x_value=0,
        threshold_value=int(threshold),
        threshold_direction="above",
        annotation_panel_labels=(str(query_panel),),
        annotation_point_ids=annotation_ids,
        annotation_intersection_ids=(),
        annotation_threshold_crossing_ids=(),
        trace={
            "query_panel_label": str(query_panel),
            "query_x_value": int(x_value),
            "threshold_value": int(threshold),
            "threshold_direction": "above",
            "threshold_direction_phrase": "above",
            "matching_method_labels": [str(method) for method in method_labels if str(method) in above_methods],
            "values_at_query_x": {
                str(method): int(values[str(query_panel)][str(method)][int(x_index)])
                for method in method_labels
            },
            **dict(panel_label_meta),
        },
    )
    return _Dataset(
        scene_variant="multipanel_line_grid",
        x_values=tuple(x_values),
        y_min=int(y_min),
        y_max=int(y_max),
        panels=_panels_from_values(values_by_panel_method=values, panel_labels=panel_labels, method_labels=method_labels, colors=colors),
        query=query,
        intersections=(),
        threshold_crossings=(),
    )


def _side_value(
    *,
    rng: Any,
    threshold: int,
    side: str,
    y_min: int,
    y_max: int,
    margin_min: int = 7,
    margin_max: int = 28,
) -> int:
    margin = int(rng.randint(int(margin_min), int(margin_max)))
    if str(side) == "above":
        return max(int(y_min) + 5, min(int(y_max) - 5, int(threshold) + int(margin)))
    if str(side) == "below":
        return max(int(y_min) + 5, min(int(y_max) - 5, int(threshold) - int(margin)))
    raise ValueError(f"unsupported threshold side: {side}")


def _make_single_threshold_crossing_curve(
    *,
    rng: Any,
    x_count: int,
    threshold: int,
    direction: str,
    crossing_index: int,
    y_min: int,
    y_max: int,
) -> List[int]:
    """Build a curve with one threshold crossing before crossing_index."""

    if int(x_count) < 3:
        raise ValueError("x_count must be at least 3 for threshold crossing curves")
    crossing_index = max(1, min(int(x_count) - 1, int(crossing_index)))
    before_side = "below" if str(direction) == "upward" else "above"
    after_side = "above" if str(direction) == "upward" else "below"
    values: List[int] = []
    for index in range(int(x_count)):
        side = before_side if int(index) < int(crossing_index) else after_side
        values.append(
            _side_value(
                rng=rng,
                threshold=int(threshold),
                side=str(side),
                y_min=int(y_min),
                y_max=int(y_max),
                margin_min=10,
                margin_max=30,
            )
        )
    return values


def _threshold_crossing_points(
    *,
    panel_label: str,
    method_label: str,
    x_values: Sequence[int],
    values: Sequence[int],
    threshold: int,
    direction: str,
) -> Tuple[_ThresholdCrossing, ...]:
    crossings: List[_ThresholdCrossing] = []
    for index in range(len(x_values) - 1):
        y0 = float(values[int(index)])
        y1 = float(values[int(index) + 1])
        requested_crossing = (
            (str(direction) == "upward" and y0 < float(threshold) < y1)
            or (str(direction) == "downward" and y0 > float(threshold) > y1)
        )
        if not requested_crossing:
            continue
        x0 = float(x_values[int(index)])
        x1 = float(x_values[int(index) + 1])
        t = (float(threshold) - y0) / (y1 - y0)
        x_value = x0 + (t * (x1 - x0))
        crossings.append(
            _ThresholdCrossing(
                crossing_id=_threshold_crossing_id(str(panel_label), str(method_label), len(crossings)),
                panel_label=str(panel_label),
                method_label=str(method_label),
                x_value=float(x_value),
                y_value=float(threshold),
                direction=str(direction),
            )
        )
    return tuple(crossings)


def _build_panel_point_threshold_count_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    non_answer_params = _without_sample_cursor(params)
    direction, direction_probabilities = _resolve_point_threshold_direction(params, instance_seed=int(instance_seed))
    x_values, y_min, y_max, _panel_count_value, panel_labels, method_labels, panel_label_meta = _common_axes(
        non_answer_params,
        instance_seed=int(instance_seed),
        min_x_tick_count=5,
    )
    colors = _palette(params)
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.panel_point_threshold_count")
    query_panel = str(
        _balanced_choice(
            panel_labels,
            non_answer_params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.panel_point_threshold_count.panel",
        )
    )
    threshold = _threshold_for_x_values(params, instance_seed=int(instance_seed), x_values=x_values)
    total_slots = int(len(method_labels)) * int(len(x_values))
    target_min = max(1, int(_gen_int(params, "point_threshold_target_count_min", 3)))
    target_max = min(int(total_slots) - 1, int(_gen_int(params, "point_threshold_target_count_max", 12)))
    if int(target_min) > int(target_max):
        target_min = max(1, min(int(total_slots), int(target_max)))
    target_count = int(
        _balanced_choice(
            list(range(int(target_min), int(target_max) + 1)),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.panel_point_threshold_count.answer",
        )
    )
    values = _make_random_panels(
        panel_labels=panel_labels,
        method_labels=method_labels,
        x_count=len(x_values),
        colors=colors,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.panel_point_threshold_count.values",
        value_min=y_min,
        value_max=y_max,
    )
    slots = [(str(method), int(x_index)) for method in method_labels for x_index in range(len(x_values))]
    rng.shuffle(slots)
    matching_slots = set(slots[: int(target_count)])
    matching_side = "above" if str(direction) == "above" else "below"
    nonmatching_side = "below" if str(direction) == "above" else "above"
    for method in method_labels:
        for x_index, _x_value in enumerate(x_values):
            side = matching_side if (str(method), int(x_index)) in matching_slots else nonmatching_side
            values[str(query_panel)][str(method)][int(x_index)] = _side_value(
                rng=rng,
                threshold=int(threshold),
                side=str(side),
                y_min=int(y_min),
                y_max=int(y_max),
            )

    annotation_ids = tuple(
        _point_id(str(query_panel), str(method), int(x_values[int(x_index)]))
        for method, x_index in slots[: int(target_count)]
    )
    query = _Query(
        prompt_key="panel_point_threshold_count",
        scene_variant="multipanel_line_grid",
        answer=int(target_count),
        answer_type="integer",
        panel_label=str(query_panel),
        method_label="",
        method_a_label="",
        method_b_label="",
        x_value=0,
        start_x_value=0,
        end_x_value=0,
        threshold_value=int(threshold),
        threshold_direction=str(direction),
        annotation_panel_labels=(str(query_panel),),
        annotation_point_ids=annotation_ids,
        annotation_intersection_ids=(),
        annotation_threshold_crossing_ids=(),
        trace={
            "query_panel_label": str(query_panel),
            "threshold_value": int(threshold),
            "threshold_direction": str(direction),
            "threshold_direction_phrase": "above" if str(direction) == "above" else "below",
            "point_threshold_direction_probabilities": dict(direction_probabilities),
            "matching_point_ids": list(annotation_ids),
            "values_in_query_panel": {
                str(method): [int(value) for value in values[str(query_panel)][str(method)]]
                for method in method_labels
            },
            **dict(panel_label_meta),
        },
    )
    return _Dataset(
        scene_variant="multipanel_line_grid",
        x_values=tuple(x_values),
        y_min=int(y_min),
        y_max=int(y_max),
        panels=_panels_from_values(values_by_panel_method=values, panel_labels=panel_labels, method_labels=method_labels, colors=colors),
        query=query,
        intersections=(),
        threshold_crossings=(),
    )


def _build_panel_curve_threshold_crossing_count_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    non_answer_params = _without_sample_cursor(params)
    direction, direction_probabilities = _resolve_threshold_crossing_direction(params, instance_seed=int(instance_seed))
    x_values, y_min, y_max, _panel_count_value, panel_labels, method_labels, panel_label_meta = _common_axes(
        non_answer_params,
        instance_seed=int(instance_seed),
        min_x_tick_count=5,
    )
    colors = _palette(params)
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.panel_curve_threshold_crossing_count")
    query_panel = str(
        _balanced_choice(
            panel_labels,
            non_answer_params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.panel_curve_threshold_crossing_count.panel",
        )
    )
    threshold = _threshold_for_x_values(params, instance_seed=int(instance_seed), x_values=x_values)
    target_min = max(1, int(_gen_int(params, "curve_threshold_target_count_min", 1)))
    target_max = min(len(method_labels), int(_gen_int(params, "curve_threshold_target_count_max", 4)))
    if int(target_min) > int(target_max):
        target_min = int(target_max)
    target_count = int(
        _balanced_choice(
            list(range(int(target_min), int(target_max) + 1)),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.panel_curve_threshold_crossing_count.answer",
        )
    )
    values = _make_random_panels(
        panel_labels=panel_labels,
        method_labels=method_labels,
        x_count=len(x_values),
        colors=colors,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.panel_curve_threshold_crossing_count.values",
        value_min=y_min,
        value_max=y_max,
    )
    shuffled_methods = list(method_labels)
    rng.shuffle(shuffled_methods)
    matching_methods = set(str(method) for method in shuffled_methods[: int(target_count)])
    crossings: List[_ThresholdCrossing] = []
    nonmatching_side = "below" if str(direction) == "upward" else "above"
    for method_index, method in enumerate(method_labels):
        if str(method) in matching_methods:
            pivot = 1 + ((int(method_index) + int(rng.randint(0, max(1, len(x_values) - 3)))) % max(1, len(x_values) - 2))
            pivot = max(1, min(len(x_values) - 1, int(pivot)))
            values[str(query_panel)][str(method)] = _make_single_threshold_crossing_curve(
                rng=rng,
                x_count=len(x_values),
                threshold=int(threshold),
                direction=str(direction),
                crossing_index=int(pivot),
                y_min=int(y_min),
                y_max=int(y_max),
            )
            method_crossings = _threshold_crossing_points(
                panel_label=str(query_panel),
                method_label=str(method),
                x_values=x_values,
                values=values[str(query_panel)][str(method)],
                threshold=int(threshold),
                direction=str(direction),
            )
            if len(method_crossings) != 1:
                raise RuntimeError("threshold crossing construction drifted from one crossing")
            crossings.extend(method_crossings)
        else:
            values[str(query_panel)][str(method)] = [
                _side_value(
                    rng=rng,
                    threshold=int(threshold),
                    side=str(nonmatching_side),
                    y_min=int(y_min),
                    y_max=int(y_max),
                )
                for _ in x_values
            ]

    if len(crossings) != int(target_count):
        raise RuntimeError("curve threshold crossing construction lost target count")
    annotation_crossing_ids = tuple(str(item.crossing_id) for item in crossings)
    query = _Query(
        prompt_key="panel_curve_threshold_crossing_count",
        scene_variant="multipanel_line_grid",
        answer=int(target_count),
        answer_type="integer",
        panel_label=str(query_panel),
        method_label="",
        method_a_label="",
        method_b_label="",
        x_value=0,
        start_x_value=0,
        end_x_value=0,
        threshold_value=int(threshold),
        threshold_direction=str(direction),
        annotation_panel_labels=(str(query_panel),),
        annotation_point_ids=(),
        annotation_intersection_ids=(),
        annotation_threshold_crossing_ids=annotation_crossing_ids,
        trace={
            "query_panel_label": str(query_panel),
            "threshold_value": int(threshold),
            "threshold_crossing_direction": str(direction),
            "threshold_crossing_phrase": "upward through" if str(direction) == "upward" else "downward through",
            "threshold_crossing_direction_probabilities": dict(direction_probabilities),
            "matching_method_labels": [str(method) for method in method_labels if str(method) in matching_methods],
            "threshold_crossing_points": [
                {
                    "crossing_id": str(item.crossing_id),
                    "method_label": str(item.method_label),
                    "x_value": round(float(item.x_value), 3),
                    "y_value": round(float(item.y_value), 3),
                    "direction": str(item.direction),
                }
                for item in crossings
            ],
            **dict(panel_label_meta),
        },
    )
    return _Dataset(
        scene_variant="multipanel_line_grid",
        x_values=tuple(x_values),
        y_min=int(y_min),
        y_max=int(y_max),
        panels=_panels_from_values(values_by_panel_method=values, panel_labels=panel_labels, method_labels=method_labels, colors=colors),
        query=query,
        intersections=(),
        threshold_crossings=tuple(crossings),
    )


def _build_cross_panel_threshold_earliest_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    direction, direction_probabilities = _resolve_threshold_crossing_direction(params, instance_seed=int(instance_seed))
    answer_panel_index = int(
        _balanced_choice(
            _panel_answer_index_support(params),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.cross_panel_threshold_earliest.answer",
        )
    )
    non_answer_params = _without_sample_cursor(params)
    min_panel_count = max(4, int(answer_panel_index) + 1)
    panel_count = _panel_count(non_answer_params, instance_seed=int(instance_seed), min_required=int(min_panel_count))
    method_count = _method_count(non_answer_params, instance_seed=int(instance_seed))
    x_values = _x_values(non_answer_params, instance_seed=int(instance_seed), min_required=6)
    y_min = int(_gen_int(params, "y_value_min", 0))
    y_max = int(_gen_int(params, "y_value_max", 100))
    if int(y_min) >= int(y_max):
        raise ValueError("y_value_min must be lower than y_value_max")
    method_labels = _method_labels_for_seed(count=int(method_count), instance_seed=int(instance_seed))
    panel_labels, panel_label_meta = _panel_labels_for_seed(
        count=int(panel_count),
        params=params,
        instance_seed=int(instance_seed),
        reserved_labels=method_labels,
    )
    answer_panel = str(panel_labels[int(answer_panel_index)])
    colors = _palette(params)
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.cross_panel_threshold_earliest")
    method_label = str(
        _balanced_choice(
            method_labels,
            non_answer_params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.cross_panel_threshold_earliest.method",
        )
    )
    threshold = _threshold_for_x_values(params, instance_seed=int(instance_seed), x_values=x_values)
    values = _make_random_panels(
        panel_labels=panel_labels,
        method_labels=method_labels,
        x_count=len(x_values),
        colors=colors,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.cross_panel_threshold_earliest.values",
        value_min=y_min,
        value_max=y_max,
    )
    crossings: List[_ThresholdCrossing] = []
    crossing_x_by_panel: Dict[str, float] = {}
    for panel_index, panel in enumerate(panel_labels):
        if str(panel) == str(answer_panel):
            pivot = 1
        else:
            pivot = 2 + (int(panel_index) % max(1, len(x_values) - 3))
            pivot = min(len(x_values) - 1, int(pivot))
        values[str(panel)][str(method_label)] = _make_single_threshold_crossing_curve(
            rng=rng,
            x_count=len(x_values),
            threshold=int(threshold),
            direction=str(direction),
            crossing_index=int(pivot),
            y_min=int(y_min),
            y_max=int(y_max),
        )
        panel_crossings = _threshold_crossing_points(
            panel_label=str(panel),
            method_label=str(method_label),
            x_values=x_values,
            values=values[str(panel)][str(method_label)],
            threshold=int(threshold),
            direction=str(direction),
        )
        if len(panel_crossings) != 1:
            raise RuntimeError("cross-panel threshold construction drifted from one crossing per panel")
        crossing = panel_crossings[0]
        crossings.append(crossing)
        crossing_x_by_panel[str(panel)] = round(float(crossing.x_value), 3)
    if min(crossing_x_by_panel, key=lambda label: (crossing_x_by_panel[label], label)) != str(answer_panel):
        raise RuntimeError("cross-panel threshold earliest construction lost unique target")

    annotation_crossing_ids = tuple(str(item.crossing_id) for item in crossings)
    query = _Query(
        prompt_key="cross_panel_threshold_earliest_label",
        scene_variant="multipanel_line_grid",
        answer=str(answer_panel),
        answer_type="string",
        panel_label=str(answer_panel),
        method_label=str(method_label),
        method_a_label="",
        method_b_label="",
        x_value=0,
        start_x_value=0,
        end_x_value=0,
        threshold_value=int(threshold),
        threshold_direction=str(direction),
        annotation_panel_labels=tuple(str(panel) for panel in panel_labels),
        annotation_point_ids=(),
        annotation_intersection_ids=(),
        annotation_threshold_crossing_ids=annotation_crossing_ids,
        trace={
            "method_label": str(method_label),
            "threshold_value": int(threshold),
            "threshold_crossing_direction": str(direction),
            "threshold_crossing_phrase": "upward through" if str(direction) == "upward" else "downward through",
            "threshold_crossing_direction_probabilities": dict(direction_probabilities),
            "threshold_crossing_x_by_panel": dict(crossing_x_by_panel),
            "winning_panel_label": str(answer_panel),
            **dict(panel_label_meta),
        },
    )
    return _Dataset(
        scene_variant="multipanel_line_grid",
        x_values=tuple(x_values),
        y_min=int(y_min),
        y_max=int(y_max),
        panels=_panels_from_values(values_by_panel_method=values, panel_labels=panel_labels, method_labels=method_labels, colors=colors),
        query=query,
        intersections=(),
        threshold_crossings=tuple(crossings),
    )


def _replace_curve_interval(
    curve_values: List[int],
    *,
    start_index: int,
    end_index: int,
    start_value: int,
    end_value: int,
    rng: Any,
    y_min: int,
    y_max: int,
) -> None:
    curve_values[int(start_index)] = int(start_value)
    curve_values[int(end_index)] = int(end_value)
    span = max(1, int(end_index) - int(start_index))
    for index in range(int(start_index) + 1, int(end_index)):
        alpha = float(index - int(start_index)) / float(span)
        base = (1.0 - alpha) * float(start_value) + alpha * float(end_value)
        curve_values[int(index)] = max(int(y_min) + 5, min(int(y_max) - 5, int(round(base + rng.randint(-4, 4)))))


def _build_cross_panel_delta_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    answer_panel_index = int(
        _balanced_choice(
            _panel_answer_index_support(params),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.cross_panel_delta.answer",
        )
    )
    non_answer_params = _without_sample_cursor(params)
    min_panel_count = max(4, int(answer_panel_index) + 1)
    panel_count = _panel_count(non_answer_params, instance_seed=int(instance_seed), min_required=int(min_panel_count))
    method_count = _method_count(non_answer_params, instance_seed=int(instance_seed))
    x_values = _x_values(non_answer_params, instance_seed=int(instance_seed))
    y_min = int(_gen_int(params, "y_value_min", 0))
    y_max = int(_gen_int(params, "y_value_max", 100))
    if int(y_min) >= int(y_max):
        raise ValueError("y_value_min must be lower than y_value_max")
    method_labels = _method_labels_for_seed(count=int(method_count), instance_seed=int(instance_seed))
    panel_labels, panel_label_meta = _panel_labels_for_seed(
        count=int(panel_count),
        params=params,
        instance_seed=int(instance_seed),
        reserved_labels=method_labels,
    )
    answer_panel = str(panel_labels[int(answer_panel_index)])
    colors = _palette(params)
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.cross_panel_delta")
    method_label = str(
        _balanced_choice(
            method_labels,
            _without_sample_cursor(params),
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.cross_panel_delta.method",
        )
    )
    max_start_index = max(1, len(x_values) - 3)
    start_index = int(rng.randint(1, int(max_start_index)))
    end_min = min(len(x_values) - 2, int(start_index) + 1)
    end_max = len(x_values) - 2
    if int(end_min) > int(end_max):
        raise RuntimeError("x value support is too small for cross-panel delta")
    end_index = int(rng.randint(int(end_min), int(end_max)))
    start_x = int(x_values[int(start_index)])
    end_x = int(x_values[int(end_index)])
    values = _make_random_panels(
        panel_labels=panel_labels,
        method_labels=method_labels,
        x_count=len(x_values),
        colors=colors,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.cross_panel_delta.values",
        value_min=y_min,
        value_max=y_max,
    )
    target_delta = int(42 + rng.randint(0, 12))
    deltas: Dict[str, int] = {}
    for panel_index, panel in enumerate(panel_labels):
        if str(panel) == str(answer_panel):
            start_value = int(rng.randint(18, 34))
            delta = int(target_delta)
        else:
            start_value = int(rng.randint(24, 56))
            delta = int(rng.randint(-12, int(target_delta) - 14))
        end_value = max(int(y_min) + 5, min(int(y_max) - 5, int(start_value) + int(delta)))
        actual_delta = int(end_value) - int(start_value)
        if str(panel) != str(answer_panel) and int(actual_delta) >= int(target_delta):
            end_value = int(start_value) + int(target_delta) - 14 - (int(panel_index) % 5)
            end_value = max(int(y_min) + 5, min(int(y_max) - 5, int(end_value)))
            actual_delta = int(end_value) - int(start_value)
        deltas[str(panel)] = int(actual_delta)
        _replace_curve_interval(
            values[str(panel)][str(method_label)],
            start_index=int(start_index),
            end_index=int(end_index),
            start_value=int(start_value),
            end_value=int(end_value),
            rng=rng,
            y_min=int(y_min),
            y_max=int(y_max),
        )
    if max(deltas, key=lambda label: (deltas[label], label)) != str(answer_panel):
        raise RuntimeError("cross-panel delta construction lost unique target")

    annotation_ids: List[str] = []
    for panel in panel_labels:
        annotation_ids.append(_point_id(str(panel), str(method_label), int(start_x)))
        annotation_ids.append(_point_id(str(panel), str(method_label), int(end_x)))
    query = _Query(
        prompt_key="cross_panel_delta_extremum_label",
        scene_variant="multipanel_line_grid",
        answer=str(answer_panel),
        answer_type="string",
        panel_label=str(answer_panel),
        method_label=str(method_label),
        method_a_label="",
        method_b_label="",
        x_value=0,
        start_x_value=int(start_x),
        end_x_value=int(end_x),
        threshold_value=0,
        threshold_direction="",
        annotation_panel_labels=(str(answer_panel),),
        annotation_point_ids=tuple(annotation_ids),
        annotation_intersection_ids=(),
        annotation_threshold_crossing_ids=(),
        trace={
            "method_label": str(method_label),
            "start_x_value": int(start_x),
            "end_x_value": int(end_x),
            "deltas_by_panel": dict(deltas),
            "winning_panel_label": str(answer_panel),
            **dict(panel_label_meta),
        },
    )
    return _Dataset(
        scene_variant="multipanel_line_grid",
        x_values=tuple(x_values),
        y_min=int(y_min),
        y_max=int(y_max),
        panels=_panels_from_values(values_by_panel_method=values, panel_labels=panel_labels, method_labels=method_labels, colors=colors),
        query=query,
        intersections=(),
        threshold_crossings=(),
    )


def _build_intersection_curves(
    *,
    x_values: Sequence[int],
    target_count: int,
    instance_seed: int,
    namespace: str,
) -> Tuple[List[int], List[int], List[_Intersection]]:
    rng = spawn_rng(int(instance_seed), str(namespace))
    interval_count = len(x_values) - 1
    change_positions = list(range(1, int(interval_count) + 1))
    rng.shuffle(change_positions)
    change_set = set(int(position) for position in change_positions[: int(target_count)])
    signs: List[int] = []
    sign = 1
    for index in range(len(x_values)):
        if int(index) > 0 and int(index) in change_set:
            sign *= -1
        signs.append(int(sign))

    method_a: List[int] = []
    method_b: List[int] = []
    for index, sign_value in enumerate(signs):
        base = int(50 + rng.randint(-7, 7))
        magnitude = int(12 + rng.randint(0, 14))
        method_a.append(max(8, min(92, int(base) + (int(sign_value) * int(magnitude)))))
        method_b.append(max(8, min(92, int(base) - (int(sign_value) * int(magnitude)))))
    return method_a, method_b, []


def _intersection_points(
    *,
    panel_label: str,
    method_a_label: str,
    method_b_label: str,
    x_values: Sequence[int],
    values_a: Sequence[int],
    values_b: Sequence[int],
) -> Tuple[_Intersection, ...]:
    intersections: List[_Intersection] = []
    for index in range(len(x_values) - 1):
        d0 = float(values_a[int(index)] - values_b[int(index)])
        d1 = float(values_a[int(index) + 1] - values_b[int(index) + 1])
        if d0 == 0.0 or d1 == 0.0 or (d0 > 0) == (d1 > 0):
            continue
        t = abs(d0) / (abs(d0) + abs(d1))
        x0 = float(x_values[int(index)])
        x1 = float(x_values[int(index) + 1])
        y0 = float(values_a[int(index)])
        y1 = float(values_a[int(index) + 1])
        x_value = x0 + (t * (x1 - x0))
        y_value = y0 + (t * (y1 - y0))
        intersections.append(
            _Intersection(
                intersection_id=_intersection_id(str(panel_label), str(method_a_label), str(method_b_label), len(intersections)),
                panel_label=str(panel_label),
                method_a_label=str(method_a_label),
                method_b_label=str(method_b_label),
                x_value=float(x_value),
                y_value=float(y_value),
            )
        )
    return tuple(intersections)


def _build_intersection_count_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    x_values, y_min, y_max, _panel_count_value, panel_labels, method_labels, panel_label_meta = _common_axes(
        params,
        instance_seed=int(instance_seed),
        min_x_tick_count=5,
    )
    colors = _palette(params)
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.intersection_count")
    query_panel = str(
        _balanced_choice(panel_labels, _without_sample_cursor(params), instance_seed=int(instance_seed), namespace=f"{SCENE_NAMESPACE}.intersection_count.panel")
    )
    method_a_label = str(method_labels[0])
    method_b_label = str(method_labels[1])
    target_count = int(
        _balanced_choice(
            list(range(0, 5)),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.intersection_count.answer",
        )
    )
    values = _make_random_panels(
        panel_labels=panel_labels,
        method_labels=method_labels,
        x_count=len(x_values),
        colors=colors,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.intersection_count.values",
        value_min=y_min,
        value_max=y_max,
    )
    method_a_values, method_b_values, _ = _build_intersection_curves(
        x_values=x_values,
        target_count=int(target_count),
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.intersection_count.curves",
    )
    values[str(query_panel)][str(method_a_label)] = list(method_a_values)
    values[str(query_panel)][str(method_b_label)] = list(method_b_values)
    intersections = _intersection_points(
        panel_label=str(query_panel),
        method_a_label=str(method_a_label),
        method_b_label=str(method_b_label),
        x_values=x_values,
        values_a=method_a_values,
        values_b=method_b_values,
    )
    if len(intersections) != int(target_count):
        raise RuntimeError("intersection construction drifted from target count")

    query = _Query(
        prompt_key="curve_intersection_count",
        scene_variant="multipanel_line_grid",
        answer=int(target_count),
        answer_type="integer",
        panel_label=str(query_panel),
        method_label="",
        method_a_label=str(method_a_label),
        method_b_label=str(method_b_label),
        x_value=0,
        start_x_value=0,
        end_x_value=0,
        threshold_value=0,
        threshold_direction="",
        annotation_panel_labels=(str(query_panel),),
        annotation_point_ids=(),
        annotation_intersection_ids=tuple(str(item.intersection_id) for item in intersections),
        annotation_threshold_crossing_ids=(),
        trace={
            "query_panel_label": str(query_panel),
            "method_a_label": str(method_a_label),
            "method_b_label": str(method_b_label),
            "intersection_count": int(target_count),
            "intersection_points": [
                {"x_value": round(float(item.x_value), 3), "y_value": round(float(item.y_value), 3)}
                for item in intersections
            ],
            **dict(panel_label_meta),
        },
    )
    return _Dataset(
        scene_variant="multipanel_line_grid",
        x_values=tuple(x_values),
        y_min=int(y_min),
        y_max=int(y_max),
        panels=_panels_from_values(values_by_panel_method=values, panel_labels=panel_labels, method_labels=method_labels, colors=colors),
        query=query,
        intersections=tuple(intersections),
        threshold_crossings=(),
    )


def _build_earliest_maximum_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    answer_panel_index = int(
        _balanced_choice(
            _panel_answer_index_support(params),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.earliest_max.answer",
        )
    )
    non_answer_params = _without_sample_cursor(params)
    min_panel_count = max(4, int(answer_panel_index) + 1)
    panel_count = _panel_count(non_answer_params, instance_seed=int(instance_seed), min_required=int(min_panel_count))
    method_count = _method_count(non_answer_params, instance_seed=int(instance_seed))
    x_values = _x_values(non_answer_params, instance_seed=int(instance_seed))
    y_min = int(_gen_int(params, "y_value_min", 0))
    y_max = int(_gen_int(params, "y_value_max", 100))
    if int(y_min) >= int(y_max):
        raise ValueError("y_value_min must be lower than y_value_max")
    method_labels = _method_labels_for_seed(count=int(method_count), instance_seed=int(instance_seed))
    panel_labels, panel_label_meta = _panel_labels_for_seed(
        count=int(panel_count),
        params=params,
        instance_seed=int(instance_seed),
        reserved_labels=method_labels,
    )
    answer_panel = str(panel_labels[int(answer_panel_index)])
    colors = _palette(params)
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.earliest_max")
    method_label = str(
        _balanced_choice(
            method_labels,
            _without_sample_cursor(params),
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.earliest_max.method",
        )
    )
    values = _make_random_panels(
        panel_labels=panel_labels,
        method_labels=method_labels,
        x_count=len(x_values),
        colors=colors,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.earliest_max.values",
        value_min=y_min,
        value_max=y_max,
    )
    peak_indices: Dict[str, int] = {}
    for panel_index, panel in enumerate(panel_labels):
        if str(panel) == str(answer_panel):
            peak_index = 1
        else:
            peak_index = 2 + (int(panel_index) % max(1, len(x_values) - 3))
            peak_index = min(len(x_values) - 2, int(peak_index))
        peak_indices[str(panel)] = int(peak_index)
        peak_value = int(82 + rng.randint(0, 12))
        curve: List[int] = []
        for index in range(len(x_values)):
            distance = abs(int(index) - int(peak_index))
            value = int(peak_value) - (int(distance) * int(12 + rng.randint(0, 4))) - int(rng.randint(0, 5))
            curve.append(max(int(y_min) + 5, min(int(y_max) - 5, int(value))))
        curve[int(peak_index)] = int(peak_value)
        values[str(panel)][str(method_label)] = list(curve)

    annotation_ids = tuple(
        _point_id(str(panel), str(method_label), int(x_values[int(peak_indices[str(panel)])]))
        for panel in panel_labels
    )
    peak_x_by_panel = {str(panel): int(x_values[int(peak_indices[str(panel)])]) for panel in panel_labels}
    if min(peak_x_by_panel, key=lambda label: (peak_x_by_panel[label], label)) != str(answer_panel):
        raise RuntimeError("earliest maximum construction lost unique target")

    query = _Query(
        prompt_key="earliest_maximum_panel_label",
        scene_variant="multipanel_line_grid",
        answer=str(answer_panel),
        answer_type="string",
        panel_label=str(answer_panel),
        method_label=str(method_label),
        method_a_label="",
        method_b_label="",
        x_value=0,
        start_x_value=0,
        end_x_value=0,
        threshold_value=0,
        threshold_direction="",
        annotation_panel_labels=(str(answer_panel),),
        annotation_point_ids=annotation_ids,
        annotation_intersection_ids=(),
        annotation_threshold_crossing_ids=(),
        trace={
            "method_label": str(method_label),
            "peak_x_by_panel": dict(peak_x_by_panel),
            "peak_indices_by_panel": {str(panel): int(index) for panel, index in peak_indices.items()},
            "winning_panel_label": str(answer_panel),
            **dict(panel_label_meta),
        },
    )
    return _Dataset(
        scene_variant="multipanel_line_grid",
        x_values=tuple(x_values),
        y_min=int(y_min),
        y_max=int(y_max),
        panels=_panels_from_values(values_by_panel_method=values, panel_labels=panel_labels, method_labels=method_labels, colors=colors),
        query=query,
        intersections=(),
        threshold_crossings=(),
    )


build_curve_at_x_dataset = _build_curve_at_x_dataset
build_threshold_count_dataset = _build_threshold_count_dataset
build_panel_point_threshold_count_dataset = _build_panel_point_threshold_count_dataset
build_panel_curve_threshold_crossing_count_dataset = _build_panel_curve_threshold_crossing_count_dataset
build_cross_panel_delta_dataset = _build_cross_panel_delta_dataset
build_cross_panel_threshold_earliest_dataset = _build_cross_panel_threshold_earliest_dataset
build_intersection_count_dataset = _build_intersection_count_dataset
build_earliest_maximum_dataset = _build_earliest_maximum_dataset

__all__ = [
    "build_cross_panel_delta_dataset",
    "build_cross_panel_threshold_earliest_dataset",
    "build_curve_at_x_dataset",
    "build_earliest_maximum_dataset",
    "build_intersection_count_dataset",
    "build_panel_curve_threshold_crossing_count_dataset",
    "build_panel_point_threshold_count_dataset",
    "build_threshold_count_dataset",
]
