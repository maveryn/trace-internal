"""Dataset construction for annotated-series chart tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ..shared.labeled_chart_common import balanced_choice_from_values, choose_mark_count, resolve_chart_axis_variant, sample_chart_labels
from .event_window_common import (
    SUPPORTED_ENDPOINT_SIDES,
    SUPPORTED_EXTREMUM_DIRECTIONS,
    SUPPORTED_QUERY_IDS,
    SUPPORTED_SCENE_VARIANTS,
    SUPPORTED_THRESHOLD_COMPARISONS,
    TASK_ID,
    _DEFAULTS,
    _GEN_DEFAULTS,
    _Dataset,
    _gen_int,
    _probability_map_from_weights,
)

def _choose_string_axis(
    params: Mapping[str, Any],
    *,
    axis: str,
    supported: Sequence[str],
    weights_key: str,
    balance_key: str,
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    explicit = params.get(str(axis))
    supported_values = tuple(str(item) for item in supported)
    if explicit is not None:
        value = str(explicit)
        if value not in set(supported_values):
            raise ValueError(f"unsupported {axis}: {value}")
        return value, {item: (1.0 if item == value else 0.0) for item in sorted(supported_values)}
    probabilities = _probability_map_from_weights(params, key=str(weights_key), supported=supported_values)
    positives = [item for item in supported_values if float(probabilities.get(str(item), 0.0)) > 0.0]
    if not positives:
        raise ValueError(f"no positive support for {axis}")
    use_balanced = bool(params.get(str(balance_key), group_default(_GEN_DEFAULTS, str(balance_key), True)))
    if bool(use_balanced) and max(probabilities[item] for item in positives) - min(probabilities[item] for item in positives) <= 1e-9:
        index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.{axis}")
        return str(positives[int(index) % len(positives)]), dict(probabilities)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{axis}")
    threshold = rng.random()
    cumulative = 0.0
    for item in positives:
        cumulative += float(probabilities[item])
        if float(threshold) <= float(cumulative):
            return str(item), dict(probabilities)
    return str(positives[-1]), dict(probabilities)


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _choose_window(
    params: Mapping[str, Any],
    *,
    mark_count: int,
    instance_seed: int,
    min_window_size: int = 2,
) -> Tuple[int, int]:
    min_size, max_size = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="window_size_min",
        max_key="window_size_max",
        fallback_min=3,
        fallback_max=6,
        context=f"generation defaults for {TASK_ID}",
    )
    min_size = max(int(min_window_size), min(int(min_size), int(mark_count)))
    max_size = max(int(min_size), min(int(max_size), int(mark_count)))
    window_size = balanced_choice_from_values(
        [int(value) for value in range(int(min_size), int(max_size) + 1)],
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.window_size",
    )
    start_values = [int(value) for value in range(0, int(mark_count) - int(window_size) + 1)]
    start_index = balanced_choice_from_values(
        start_values,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.window_start",
    )
    return int(start_index), int(window_size)


def _sample_values(*, count: int, params: Mapping[str, Any], instance_seed: int) -> Tuple[int, ...]:
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="value_min",
        max_key="value_max",
        fallback_min=_DEFAULTS.value_min,
        fallback_max=_DEFAULTS.value_max,
        context=f"generation defaults for {TASK_ID}",
    )
    support = [int(value) for value in range(int(value_min), int(value_max) + 1)]
    if len(support) < int(count):
        raise ValueError("annotated_series requires enough distinct values for all marks")
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.values")
    values = [int(value) for value in rng.sample(support, k=int(count))]
    return tuple(int(value) for value in values)


def _build_extremum_dataset(
    *,
    query_id: str,
    scene_variant: str,
    labels: Sequence[str],
    values: Sequence[int],
    window_start: int,
    window_size: int,
    params: Mapping[str, Any],
    instance_seed: int,
    query_id_probabilities: Mapping[str, float],
    scene_variant_probabilities: Mapping[str, float],
) -> _Dataset:
    direction, direction_probabilities = _choose_string_axis(
        params,
        axis="extremum_direction",
        supported=SUPPORTED_EXTREMUM_DIRECTIONS,
        weights_key="extremum_direction_weights",
        balance_key="balanced_extremum_direction_sampling",
        instance_seed=int(instance_seed),
    )
    window_pairs = [
        (int(value), str(label))
        for label, value in zip(labels[int(window_start) : int(window_start) + int(window_size)], values[int(window_start) : int(window_start) + int(window_size)])
    ]
    answer_value, answer_label = (
        max(window_pairs, key=lambda item: (item[0], item[1]))
        if direction == "highest"
        else min(window_pairs, key=lambda item: (item[0], item[1]))
    )
    del answer_value
    return _Dataset(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        labels=tuple(str(label) for label in labels),
        values=tuple(int(value) for value in values),
        window_labels=tuple(str(label) for label in labels[int(window_start) : int(window_start) + int(window_size)]),
        annotation_labels=(str(answer_label),),
        answer_value=str(answer_label),
        answer_type="string",
        query_params={
            "extremum_direction": str(direction),
            "extremum_direction_probabilities": dict(direction_probabilities),
            "window_start_index": int(window_start),
            "window_size": int(window_size),
        },
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
    )


def _build_threshold_dataset(
    *,
    query_id: str,
    scene_variant: str,
    labels: Sequence[str],
    values: Sequence[int],
    window_start: int,
    window_size: int,
    target_count: int,
    target_answer_range: Sequence[int],
    params: Mapping[str, Any],
    instance_seed: int,
    query_id_probabilities: Mapping[str, float],
    scene_variant_probabilities: Mapping[str, float],
) -> _Dataset:
    comparison, comparison_probabilities = _choose_string_axis(
        params,
        axis="threshold_comparison",
        supported=SUPPORTED_THRESHOLD_COMPARISONS,
        weights_key="threshold_comparison_weights",
        balance_key="balanced_threshold_comparison_sampling",
        instance_seed=int(instance_seed),
    )
    window_labels = [str(label) for label in labels[int(window_start) : int(window_start) + int(window_size)]]
    window_values = [int(value) for value in values[int(window_start) : int(window_start) + int(window_size)]]
    sorted_values = sorted(window_values)
    if str(comparison) == "greater_than":
        threshold = int(sorted_values[-int(target_count)] - 1)
        annotation_labels = [
            str(label)
            for label, value in zip(window_labels, window_values)
            if int(value) > int(threshold)
        ]
        comparison_phrase = "greater than"
    else:
        threshold = int(sorted_values[int(target_count) - 1] + 1)
        annotation_labels = [
            str(label)
            for label, value in zip(window_labels, window_values)
            if int(value) < int(threshold)
        ]
        comparison_phrase = "less than"
    if len(annotation_labels) != int(target_count):
        raise RuntimeError("threshold construction did not preserve the requested answer")
    return _Dataset(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        labels=tuple(str(label) for label in labels),
        values=tuple(int(value) for value in values),
        window_labels=tuple(window_labels),
        annotation_labels=tuple(str(label) for label in annotation_labels),
        answer_value=int(target_count),
        answer_type="integer",
        query_params={
            "threshold_comparison": str(comparison),
            "threshold_comparison_probabilities": dict(comparison_probabilities),
            "threshold_comparison_phrase": str(comparison_phrase),
            "threshold": int(threshold),
            "target_answer": int(target_count),
            "target_answer_range": [int(target_answer_range[0]), int(target_answer_range[1])],
            "window_start_index": int(window_start),
            "window_size": int(window_size),
        },
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
    )


def _build_callout_dataset(
    *,
    query_id: str,
    scene_variant: str,
    labels: Sequence[str],
    values: Sequence[int],
    params: Mapping[str, Any],
    instance_seed: int,
    query_id_probabilities: Mapping[str, float],
    scene_variant_probabilities: Mapping[str, float],
) -> _Dataset:
    endpoint_side, endpoint_side_probabilities = _choose_string_axis(
        params,
        axis="endpoint_side",
        supported=SUPPORTED_ENDPOINT_SIDES,
        weights_key="endpoint_side_weights",
        balance_key="balanced_endpoint_side_sampling",
        instance_seed=int(instance_seed),
    )
    endpoint_index = 0 if str(endpoint_side) == "first" else len(labels) - 1
    min_gap = max(2, _gen_int(params, "callout_gap_min", 3))
    max_gap = max(int(min_gap), _gen_int(params, "callout_gap_max", 9))
    feasible_indices = [
        int(index)
        for index in range(1, len(labels) - 1)
        if int(index) != int(endpoint_index)
        and int(min_gap) <= abs(int(index) - int(endpoint_index)) <= int(max_gap)
    ]
    if not feasible_indices:
        feasible_indices = [int(index) for index in range(1, len(labels) - 1) if int(index) != int(endpoint_index)]
    anchor_index = balanced_choice_from_values(
        feasible_indices,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.callout_anchor_index",
    )
    answer_value = abs(int(values[int(anchor_index)]) - int(values[int(endpoint_index)]))
    return _Dataset(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        labels=tuple(str(label) for label in labels),
        values=tuple(int(value) for value in values),
        window_labels=(),
        annotation_labels=(str(labels[int(anchor_index)]), str(labels[int(endpoint_index)])),
        answer_value=int(answer_value),
        answer_type="integer",
        query_params={
            "endpoint_side": str(endpoint_side),
            "endpoint_side_probabilities": dict(endpoint_side_probabilities),
            "anchor_label": str(labels[int(anchor_index)]),
            "endpoint_label": str(labels[int(endpoint_index)]),
            "anchor_index": int(anchor_index),
            "endpoint_index": int(endpoint_index),
        },
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
    )


def _build_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Dataset:
    scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
    query_id_probabilities = {str(query_id): 1.0}

    mark_count_min, mark_count_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="mark_count_min",
        max_key="mark_count_max",
        fallback_min=_DEFAULTS.mark_count_min,
        fallback_max=_DEFAULTS.mark_count_max,
        context=f"generation defaults for {TASK_ID}",
    )
    mark_count = choose_mark_count(
        [int(value) for value in range(int(mark_count_min), int(mark_count_max) + 1)],
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.mark_count",
    )
    labels = sample_chart_labels(
        count=int(mark_count),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.labels:{str(query_id)}:{int(mark_count)}",
    )
    values = _sample_values(count=int(mark_count), params=params, instance_seed=int(instance_seed))
    if str(query_id) == "event_window_extremum_label":
        window_start, window_size = _choose_window(params, mark_count=int(mark_count), instance_seed=int(instance_seed))
        return _build_extremum_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            labels=labels,
            values=values,
            window_start=int(window_start),
            window_size=int(window_size),
            params=params,
            instance_seed=int(instance_seed),
            query_id_probabilities=query_id_probabilities,
            scene_variant_probabilities=scene_variant_probabilities,
        )
    if str(query_id) == "event_window_threshold_count":
        target_min, target_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="threshold_count_min",
            max_key="threshold_count_max",
            fallback_min=1,
            fallback_max=5,
            context=f"generation defaults for {TASK_ID}",
        )
        target_max = min(int(target_max), max(1, _gen_int(params, "window_size_max", 6) - 1))
        target_min = max(1, min(int(target_min), int(target_max)))
        target_count = balanced_choice_from_values(
            [int(value) for value in range(int(target_min), int(target_max) + 1)],
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.threshold_count_target",
        )
        window_start, window_size = _choose_window(
            params,
            mark_count=int(mark_count),
            instance_seed=int(instance_seed),
            min_window_size=int(target_count) + 1,
        )
        return _build_threshold_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            labels=labels,
            values=values,
            window_start=int(window_start),
            window_size=int(window_size),
            target_count=int(target_count),
            target_answer_range=(int(target_min), int(target_max)),
            params=params,
            instance_seed=int(instance_seed),
            query_id_probabilities=query_id_probabilities,
            scene_variant_probabilities=scene_variant_probabilities,
        )
    if str(query_id) == "callout_endpoint_change_value":
        return _build_callout_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            labels=labels,
            values=values,
            params=params,
            instance_seed=int(instance_seed),
            query_id_probabilities=query_id_probabilities,
            scene_variant_probabilities=scene_variant_probabilities,
        )
    raise ValueError(f"unsupported annotated_series query id: {query_id}")
