"""Dataset and query construction for 3D bar-grid chart tasks."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.color_distance import sample_color_palette_with_distance_constraints
from ...shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ..shared.label_assets import resolve_chart_entity_labels
from ..shared.labeled_chart_common import sample_chart_labels
from .grid_common import (
    BBox,
    CONDITION_COUNT_QUERY_IDS,
    TASK_ID,
    _BarCell,
    _Dataset,
    _DEFAULT_PALETTE,
    _GEN_DEFAULTS,
    _Query,
    _RENDER_DEFAULTS,
    _as_rgb,
)


def _sample_palette(*, instance_seed: int, count: int) -> Tuple[RGB, ...]:
    rng = spawn_rng(int(instance_seed), "charts.three_d_bar.palette")
    raw_palette = _RENDER_DEFAULTS.get("series_palette_rgb")
    if isinstance(raw_palette, Sequence) and not isinstance(raw_palette, (str, bytes)) and len(raw_palette) >= int(count):
        palette = [_as_rgb(item, _DEFAULT_PALETTE[index % len(_DEFAULT_PALETTE)]) for index, item in enumerate(raw_palette)]
        rng.shuffle(palette)
        return tuple(palette[: int(count)])
    palette = sample_color_palette_with_distance_constraints(
        rng,
        palette_size=int(count),
        channel_min=35,
        channel_max=218,
        anchor_colors=((255, 255, 255), (248, 248, 248)),
        min_distance=44.0,
        distance_space="lab",
    )
    return tuple(tuple(int(channel) for channel in color) for color in palette)


def _sample_x_labels(*, count: int, instance_seed: int) -> Tuple[str, ...]:
    rng = spawn_rng(int(instance_seed), "charts.three_d_bar.x_labels")
    if rng.random() < 0.58:
        start = int(rng.randint(2014, 2026 - int(count)))
        return tuple(str(start + index) for index in range(int(count)))
    return tuple(
        str(label)
        for label in sample_chart_labels(
            count=int(count),
            instance_seed=int(instance_seed),
            namespace=f"task_charts__bar_3d.labels:x:{int(count)}",
        )
    )


def _sample_series_labels(*, count: int, instance_seed: int) -> Tuple[str, ...]:
    rng = spawn_rng(int(instance_seed), "charts.three_d_bar.series_labels")
    labels = resolve_chart_entity_labels(
        rng,
        count=int(count),
        min_chars=2,
        max_chars=7,
        allow_spaces=False,
    ).labels
    return tuple(str(label) for label in labels)


def _sample_query_id(
    params: Mapping[str, Any],
    *,
    allowed_query_ids: Sequence[str],
    instance_seed: int,
) -> str:
    allowed = tuple(str(value) for value in allowed_query_ids)
    allowed_set = set(allowed)
    explicit = params.get("query_id")
    if explicit is not None and str(explicit) != "default":
        query_id = str(explicit)
        if query_id not in allowed_set:
            raise ValueError(f"unsupported 3D bar query_id for this public task: {query_id}")
        return query_id
    rng = spawn_rng(int(instance_seed), "charts.three_d_bar.query_id")
    raw_weights = params.get("query_id_weights", params.get("query_variant_weights"))
    if isinstance(raw_weights, Mapping):
        weights = [max(0.0, float(raw_weights.get(query_id, 0.0))) for query_id in allowed]
        if sum(weights) > 0.0:
            threshold = rng.random() * sum(weights)
            cumulative = 0.0
            for query_id, weight in zip(allowed, weights):
                cumulative += float(weight)
                if threshold <= cumulative:
                    return str(query_id)
    return str(allowed[int(rng.randrange(len(allowed)))])


def _int_sequence_default(params: Mapping[str, Any], key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), list(fallback)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return tuple(int(value) for value in fallback)
    values = tuple(int(value) for value in raw)
    return values if values else tuple(int(value) for value in fallback)


def _condition_answer_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    return tuple(
        int(value)
        for value in _int_sequence_default(params, "condition_count_answer_support", (1, 2, 3, 4, 5))
        if int(value) > 0
    )


def _sample_pairwise_target_count(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    max_category_count: int,
) -> int:
    eligible_counts = [
        int(count)
        for count in _condition_answer_support(params)
        if 1 <= int(count) < int(max_category_count)
    ]
    if not eligible_counts:
        eligible_counts = [1]
    rng = spawn_rng(int(instance_seed), "charts.three_d_bar.pairwise_target_count")
    return int(eligible_counts[int(rng.randrange(len(eligible_counts)))])


def _sample_condition_target_count(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    axis_size: int,
    namespace: str,
) -> Tuple[int, Dict[str, float]]:
    support = tuple(
        int(count)
        for count in _condition_answer_support(params)
        if 1 <= int(count) < int(axis_size)
    )
    if not support:
        raise ValueError("condition count answer support has no nontrivial values for the selected axis")
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)) % len(support)
    selected = int(support[int(index)])
    return selected, uniform_probability_map(support, selected=selected)


def _pairwise_target_max_category_count(params: Mapping[str, Any]) -> int:
    _, x_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="condition_category_count_min",
        max_key="condition_category_count_max",
        fallback_min=4,
        fallback_max=6,
        context=f"generation defaults for {TASK_ID}",
    )
    return max(1, min(int(x_max), 8))


def _sample_grid(
    params: Mapping[str, Any],
    *,
    query_id: str,
    instance_seed: int,
) -> Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[Tuple[int, ...], ...], Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
    condition_query = str(query_id) in set(CONDITION_COUNT_QUERY_IDS)
    category_min_key = "condition_category_count_min" if condition_query else "category_count_min"
    category_max_key = "condition_category_count_max" if condition_query else "category_count_max"
    series_min_key = "condition_series_count_min" if condition_query else "series_count_min"
    series_max_key = "condition_series_count_max" if condition_query else "series_count_max"
    x_min, x_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key=category_min_key,
        max_key=category_max_key,
        fallback_min=4,
        fallback_max=6,
        context=f"generation defaults for {TASK_ID}",
    )
    series_min, series_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key=series_min_key,
        max_key=series_max_key,
        fallback_min=3,
        fallback_max=5,
        context=f"generation defaults for {TASK_ID}",
    )
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="value_min",
        max_key="value_max",
        fallback_min=6,
        fallback_max=36,
        context=f"generation defaults for {TASK_ID}",
    )
    x_max = max(int(x_min), min(int(x_max), 8))
    series_max = max(int(series_min), int(series_max))
    rng = spawn_rng(int(instance_seed), "charts.three_d_bar.grid")
    max_bar_count = max(1, int(params.get("max_bar_count", group_default(_GEN_DEFAULTS, "max_bar_count", 24))))
    pairwise_target_count = (
        _sample_pairwise_target_count(
            params,
            instance_seed=int(instance_seed),
            max_category_count=_pairwise_target_max_category_count(params),
        )
        if str(query_id) == "series_comparison_count"
        else None
    )
    valid_grid_sizes = [
        (int(x_count), int(series_count))
        for x_count in range(int(x_min), int(x_max) + 1)
        for series_count in range(int(series_min), int(series_max) + 1)
        if int(x_count) * int(series_count) <= int(max_bar_count)
        and (pairwise_target_count is None or int(x_count) > int(pairwise_target_count))
    ]
    if not valid_grid_sizes:
        raise ValueError("3D bar grid size constraints leave no valid category/series pairs")
    x_count, series_count = valid_grid_sizes[int(rng.randrange(len(valid_grid_sizes)))]
    x_labels = _sample_x_labels(count=int(x_count), instance_seed=int(instance_seed))
    series_labels = _sample_series_labels(count=int(series_count), instance_seed=int(instance_seed))
    values_grid = [
        [int(rng.randint(int(value_min), int(value_max))) for _ in range(int(series_count))]
        for _ in range(int(x_count))
    ]
    if str(query_id) == "series_comparison_count" and pairwise_target_count is not None:
        control_rng = spawn_rng(int(instance_seed), "charts.three_d_bar.pairwise_control_pair")
        series_order = list(range(int(series_count)))
        control_rng.shuffle(series_order)
        series_a, series_b = int(series_order[0]), int(series_order[1])
        x_order = list(range(int(x_count)))
        control_rng.shuffle(x_order)
        winning_x = set(int(index) for index in x_order[: int(pairwise_target_count)])
        for x_index in range(int(x_count)):
            low = int(control_rng.randint(int(value_min), max(int(value_min), int(value_max) - 1)))
            high = int(control_rng.randint(int(low) + 1, int(value_max))) if int(low) < int(value_max) else int(value_max)
            if int(x_index) in winning_x:
                values_grid[int(x_index)][int(series_a)] = int(high)
                values_grid[int(x_index)][int(series_b)] = int(low)
            else:
                values_grid[int(x_index)][int(series_a)] = int(low)
                values_grid[int(x_index)][int(series_b)] = int(high)
    values = tuple(tuple(int(value) for value in row) for row in values_grid)
    return (
        x_labels,
        series_labels,
        values,
        (int(x_min), int(x_max)),
        (int(series_min), int(series_max)),
        (int(value_min), int(value_max)),
    )


def _choose_interval(*, x_count: int, params: Mapping[str, Any], instance_seed: int) -> Tuple[int, int, Tuple[int, int]]:
    span_min, span_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="interval_category_count_min",
        max_key="interval_category_count_max",
        fallback_min=2,
        fallback_max=4,
        context=f"generation defaults for {TASK_ID}",
    )
    span_max = min(int(span_max), int(x_count))
    span_min = min(int(span_min), int(span_max))
    rng = spawn_rng(int(instance_seed), "charts.three_d_bar.interval")
    span_count = int(rng.randint(int(span_min), int(span_max)))
    start = int(rng.randint(0, int(x_count) - int(span_count)))
    return int(start), int(start + span_count - 1), (int(span_min), int(span_max))


def _valid_threshold(
    values: Sequence[int],
    *,
    want_at_least: bool,
    rng: Any,
    target_counts: Sequence[int] | None = None,
) -> Tuple[int, int] | None:
    if len(values) < 2:
        return None
    lower = min(int(value) for value in values)
    upper = max(int(value) for value in values)
    candidates_by_count: Dict[int, List[int]] = defaultdict(list)
    for threshold in range(int(lower), int(upper) + 1):
        if bool(want_at_least):
            count = sum(1 for value in values if int(value) >= int(threshold))
        else:
            count = sum(1 for value in values if int(value) < int(threshold))
        if 1 <= int(count) <= len(values) - 1:
            candidates_by_count[int(count)].append(int(threshold))
    if not candidates_by_count:
        return None
    preferred_counts = [
        int(count)
        for count in (target_counts or ())
        if int(count) in candidates_by_count
    ]
    available_counts = preferred_counts or sorted(int(count) for count in candidates_by_count.keys())
    target_count = int(available_counts[int(rng.randrange(len(available_counts)))])
    thresholds = candidates_by_count[int(target_count)]
    threshold = int(thresholds[int(rng.randrange(len(thresholds)))])
    return int(threshold), int(target_count)


def _build_query(
    *,
    query_id: str,
    x_labels: Sequence[str],
    series_labels: Sequence[str],
    values: Sequence[Sequence[int]],
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Query:
    rng = spawn_rng(int(instance_seed), f"charts.three_d_bar.query.{query_id}")
    x_count = len(x_labels)
    series_count = len(series_labels)

    def bar_id(x_index: int, series_index: int) -> str:
        return f"bar_{int(x_index)}_{int(series_index)}"

    if query_id == "series_total_value":
        series_index = int(rng.randrange(series_count))
        answer = int(sum(int(values[x_index][series_index]) for x_index in range(x_count)))
        annotation = tuple(bar_id(x_index, series_index) for x_index in range(x_count))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            annotation_bar_ids=annotation,
            trace={
                "series_label": str(series_labels[series_index]),
                "series_index": int(series_index),
                "selected_values": [int(values[x_index][series_index]) for x_index in range(x_count)],
            },
        )
    if query_id == "category_total_value":
        x_index = int(rng.randrange(x_count))
        answer = int(sum(int(values[x_index][series_index]) for series_index in range(series_count)))
        annotation = tuple(bar_id(x_index, series_index) for series_index in range(series_count))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            annotation_bar_ids=annotation,
            trace={
                "category_label": str(x_labels[x_index]),
                "category_index": int(x_index),
                "selected_values": [int(values[x_index][series_index]) for series_index in range(series_count)],
            },
        )
    if query_id == "series_interval_total_value":
        series_index = int(rng.randrange(series_count))
        start_index, end_index, span_range = _choose_interval(x_count=int(x_count), params=params, instance_seed=int(instance_seed))
        answer = int(sum(int(values[x_index][series_index]) for x_index in range(int(start_index), int(end_index) + 1)))
        annotation = tuple(bar_id(x_index, series_index) for x_index in range(int(start_index), int(end_index) + 1))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            annotation_bar_ids=annotation,
            trace={
                "series_label": str(series_labels[series_index]),
                "series_index": int(series_index),
                "start_category_label": str(x_labels[start_index]),
                "end_category_label": str(x_labels[end_index]),
                "start_category_index": int(start_index),
                "end_category_index": int(end_index),
                "interval_category_count": int(end_index) - int(start_index) + 1,
                "interval_category_count_range": list(span_range),
                "selected_values": [int(values[x_index][series_index]) for x_index in range(int(start_index), int(end_index) + 1)],
            },
        )
    if query_id == "series_total_gap_value":
        totals = [int(sum(int(values[x_index][series_index]) for x_index in range(x_count))) for series_index in range(series_count)]
        pairs = [(a, b) for a in range(series_count) for b in range(a + 1, series_count) if int(totals[a]) != int(totals[b])]
        if not pairs:
            raise ValueError("series totals are not distinct enough for a gap query")
        series_a, series_b = pairs[int(rng.randrange(len(pairs)))]
        answer = abs(int(totals[series_a]) - int(totals[series_b]))
        annotation = tuple(bar_id(x_index, series_index) for series_index in (series_a, series_b) for x_index in range(x_count))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            annotation_bar_ids=annotation,
            trace={
                "series_label_a": str(series_labels[series_a]),
                "series_label_b": str(series_labels[series_b]),
                "series_index_a": int(series_a),
                "series_index_b": int(series_b),
                "series_total_a": int(totals[series_a]),
                "series_total_b": int(totals[series_b]),
            },
        )
    if query_id == "category_total_gap_value":
        totals = [int(sum(int(values[x_index][series_index]) for series_index in range(series_count))) for x_index in range(x_count)]
        pairs = [(a, b) for a in range(x_count) for b in range(a + 1, x_count) if int(totals[a]) != int(totals[b])]
        if not pairs:
            raise ValueError("category totals are not distinct enough for a gap query")
        x_a, x_b = pairs[int(rng.randrange(len(pairs)))]
        answer = abs(int(totals[x_a]) - int(totals[x_b]))
        annotation = tuple(bar_id(x_index, series_index) for x_index in (x_a, x_b) for series_index in range(series_count))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            annotation_bar_ids=annotation,
            trace={
                "category_label_a": str(x_labels[x_a]),
                "category_label_b": str(x_labels[x_b]),
                "category_index_a": int(x_a),
                "category_index_b": int(x_b),
                "category_total_a": int(totals[x_a]),
                "category_total_b": int(totals[x_b]),
            },
        )
    if query_id == "category_extremum_gap_value":
        valid_categories = [
            x_index
            for x_index in range(x_count)
            if max(int(value) for value in values[x_index]) > min(int(value) for value in values[x_index])
        ]
        if not valid_categories:
            raise ValueError("category values are not distinct enough for an extremum gap")
        x_index = int(valid_categories[int(rng.randrange(len(valid_categories)))])
        category_values = [int(values[x_index][series_index]) for series_index in range(series_count)]
        answer = int(max(category_values) - min(category_values))
        annotation = tuple(bar_id(x_index, series_index) for series_index in range(series_count))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            annotation_bar_ids=annotation,
            trace={
                "category_label": str(x_labels[x_index]),
                "category_index": int(x_index),
                "category_values": list(category_values),
                "max_value": int(max(category_values)),
                "min_value": int(min(category_values)),
            },
        )
    if query_id == "series_threshold_count":
        series_index = int(rng.randrange(series_count))
        series_values = [int(values[x_index][series_index]) for x_index in range(x_count)]
        target_count, target_count_probabilities = _sample_condition_target_count(
            params,
            instance_seed=int(instance_seed),
            axis_size=int(x_count),
            namespace=f"{TASK_ID}.{query_id}.target_count",
        )
        threshold_info = _valid_threshold(
            series_values,
            want_at_least=True,
            rng=rng,
            target_counts=(int(target_count),),
        )
        if threshold_info is None:
            raise ValueError("series threshold query has no nontrivial count")
        threshold, answer = threshold_info
        annotation = tuple(bar_id(x_index, series_index) for x_index in range(x_count))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            annotation_bar_ids=annotation,
            trace={
                "series_label": str(series_labels[series_index]),
                "series_index": int(series_index),
                "comparison_phrase": "at least",
                "threshold": int(threshold),
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "selected_values": list(series_values),
            },
        )
    if query_id == "category_threshold_count":
        x_index = int(rng.randrange(x_count))
        category_values = [int(values[x_index][series_index]) for series_index in range(series_count)]
        target_count, target_count_probabilities = _sample_condition_target_count(
            params,
            instance_seed=int(instance_seed),
            axis_size=int(series_count),
            namespace=f"{TASK_ID}.{query_id}.target_count",
        )
        threshold_info = _valid_threshold(
            category_values,
            want_at_least=False,
            rng=rng,
            target_counts=(int(target_count),),
        )
        if threshold_info is None:
            raise ValueError("category threshold query has no nontrivial count")
        threshold, answer = threshold_info
        annotation = tuple(bar_id(x_index, series_index) for series_index in range(series_count))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            annotation_bar_ids=annotation,
            trace={
                "category_label": str(x_labels[x_index]),
                "category_index": int(x_index),
                "comparison_phrase": "below",
                "threshold": int(threshold),
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "selected_values": list(category_values),
            },
        )
    if query_id == "series_comparison_count":
        pairs_by_count: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
        for series_a in range(series_count):
            for series_b in range(series_count):
                if series_a == series_b:
                    continue
                count = sum(1 for x_index in range(x_count) if int(values[x_index][series_a]) > int(values[x_index][series_b]))
                if 1 <= int(count) <= int(x_count) - 1:
                    pairs_by_count[int(count)].append((int(series_a), int(series_b)))
        if not pairs_by_count:
            raise ValueError("series comparison query has no nontrivial count")
        target_count = _sample_pairwise_target_count(
            params,
            instance_seed=int(instance_seed),
            max_category_count=_pairwise_target_max_category_count(params),
        )
        if int(target_count) not in pairs_by_count:
            raise ValueError("series comparison query target count is unavailable")
        answer = int(target_count)
        pairs = pairs_by_count[int(answer)]
        series_a, series_b = pairs[int(rng.randrange(len(pairs)))]
        annotation = tuple(bar_id(x_index, series_index) for series_index in (series_a, series_b) for x_index in range(x_count))
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            annotation_bar_ids=annotation,
            trace={
                "series_label_a": str(series_labels[series_a]),
                "series_label_b": str(series_labels[series_b]),
                "series_index_a": int(series_a),
                "series_index_b": int(series_b),
                "target_count": int(target_count),
                "selected_values_a": [int(values[x_index][series_a]) for x_index in range(x_count)],
                "selected_values_b": [int(values[x_index][series_b]) for x_index in range(x_count)],
            },
        )
    raise ValueError(f"unsupported 3D bar query_id: {query_id}")


def _build_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[_Dataset, Dict[str, Any]]:
    x_labels, series_labels, values, x_count_range, series_count_range, value_range = _sample_grid(
        params,
        query_id=str(query_id),
        instance_seed=int(instance_seed),
    )
    palette = _sample_palette(instance_seed=int(instance_seed), count=len(series_labels))
    bars: List[_BarCell] = []
    for x_index, x_label in enumerate(x_labels):
        for series_index, series_label in enumerate(series_labels):
            bars.append(
                _BarCell(
                    bar_id=f"bar_{int(x_index)}_{int(series_index)}",
                    x_label=str(x_label),
                    series_label=str(series_label),
                    x_index=int(x_index),
                    series_index=int(series_index),
                    value=int(values[x_index][series_index]),
                    color_rgb=tuple(int(channel) for channel in palette[int(series_index) % len(palette)]),
                )
            )
    query = _build_query(
        query_id=str(query_id),
        x_labels=x_labels,
        series_labels=series_labels,
        values=values,
        params=params,
        instance_seed=int(instance_seed),
    )
    ranges = {
        "category_count_range": list(x_count_range),
        "series_count_range": list(series_count_range),
        "max_bar_count": int(params.get("max_bar_count", group_default(_GEN_DEFAULTS, "max_bar_count", 24))),
        "value_range": list(value_range),
    }
    return (
        _Dataset(
            x_labels=tuple(str(label) for label in x_labels),
            series_labels=tuple(str(label) for label in series_labels),
            bars=tuple(bars),
            query=query,
        ),
        dict(ranges),
    )
