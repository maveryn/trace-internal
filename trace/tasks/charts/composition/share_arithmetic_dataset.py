"""Dataset construction for part-whole composition chart tasks."""

from __future__ import annotations

import colorsys
import itertools
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from ..shared.label_assets import resolve_chart_category_labels
from ..shared.labeled_chart_common import sample_composition_with_sum
from .share_arithmetic_common import (
    CIRCULAR_ORDER_DIRECTIONS,
    PART_WHOLE_QUERY_IDS,
    POSITIONAL_RELATIONS,
    TASK_ID,
    TRANSFER_GAP_QUERY_IDS,
    _CategorySpec,
    _Dataset,
    _TransferQuery,
    _GEN_DEFAULTS,
    _balanced_int,
    _category_count_bounds,
    _configured_int_values,
    _format_offset_list,
    _format_quoted,
    _ordinal,
    _params_with_shifted_sample_cursor,
    _resolve_count_bounds,
    _scene_axis_stride,
    _task_axis_stride,
    _value_bounds,
)

def _palette(count: int, *, instance_seed: int) -> Tuple[Tuple[int, int, int], ...]:
    colors: List[Tuple[int, int, int]] = []
    for index in range(int(count)):
        hue = (0.08 + (float(index) * 0.61803398875)) % 1.0
        lightness = 0.50 + (0.08 if int(index) % 2 else 0.0)
        saturation = 0.64
        red, green, blue = colorsys.hls_to_rgb(float(hue), float(lightness), float(saturation))
        colors.append((int(round(red * 255)), int(round(green * 255)), int(round(blue * 255))))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.palette")
    rng.shuffle(colors)
    return tuple((int(red), int(green), int(blue)) for red, green, blue in colors[: int(count)])


def _sample_categories(
    *,
    category_count: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
) -> Tuple[_CategorySpec, ...]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.categories")
    labels = list(
        resolve_chart_category_labels(
            rng,
            count=int(category_count),
            min_chars=2,
            max_chars=8,
            allow_spaces=False,
        ).labels
    )
    value_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.values")
    values = sample_composition_with_sum(
        value_rng,
        target_sum=100,
        count=int(category_count),
        value_min=int(value_min),
        value_max=int(value_max),
    )
    value_rng.shuffle(values)
    colors = _palette(int(category_count), instance_seed=int(instance_seed))
    return tuple(
        _CategorySpec(label=str(label), value=int(value), color_rgb=tuple(colors[index]))
        for index, (label, value) in enumerate(zip(labels, values))
    )


def _sample_categories_from_values(
    values: Sequence[int],
    *,
    instance_seed: int,
    namespace_suffix: str,
) -> Tuple[_CategorySpec, ...]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{namespace_suffix}.categories")
    labels = list(
        resolve_chart_category_labels(
            rng,
            count=len(values),
            min_chars=2,
            max_chars=8,
            allow_spaces=False,
        ).labels
    )
    colors = _palette(len(values), instance_seed=int(instance_seed))
    return tuple(
        _CategorySpec(label=str(label), value=int(value), color_rgb=tuple(colors[index]))
        for index, (label, value) in enumerate(zip(labels, values))
    )


def _sample_ranked_categories(
    *,
    category_count: int,
    instance_seed: int,
) -> Tuple[_CategorySpec, ...]:
    top_rank_count = 7
    if int(category_count) < top_rank_count + 1:
        raise ValueError("ranked share task requires at least 8 categories")
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.ranked.categories")
    labels = list(
        resolve_chart_category_labels(
            rng,
            count=int(category_count),
            min_chars=2,
            max_chars=8,
            allow_spaces=False,
        ).labels
    )
    top_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.ranked.top_values")
    rest_count = int(category_count) - int(top_rank_count)
    top_values: List[int] | None = None
    rest_values: Tuple[int, ...] | None = None
    for attempt in range(120):
        candidate_top = sorted(
            [int(value) for value in top_rng.sample(range(5, 22), k=int(top_rank_count))],
            reverse=True,
        )
        rest_sum = 100 - int(sum(candidate_top))
        rest_value_max = max(1, int(candidate_top[-1]) - 1)
        if int(rest_count) <= int(rest_sum) <= int(rest_count) * int(rest_value_max):
            rest_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.ranked.rest_values.{attempt}")
            rest_values = sample_composition_with_sum(
                rest_rng,
                target_sum=int(rest_sum),
                count=int(rest_count),
                value_min=1,
                value_max=int(rest_value_max),
            )
            top_values = list(candidate_top)
            break
    if top_values is None or rest_values is None:
        raise ValueError("could not construct ranked-share categories with unique top ranks")
    values = [int(value) for value in (*top_values, *rest_values)]
    rng.shuffle(values)
    colors = _palette(int(category_count), instance_seed=int(instance_seed))
    return tuple(
        _CategorySpec(label=str(label), value=int(value), color_rgb=tuple(colors[index]))
        for index, (label, value) in enumerate(zip(labels, values))
    )


def _rank_categories(categories: Sequence[_CategorySpec]) -> Tuple[_CategorySpec, ...]:
    return tuple(
        sorted(
            categories,
            key=lambda category: (-int(category.value), str(category.label)),
        )
    )


def _rank_categories_smallest(categories: Sequence[_CategorySpec]) -> Tuple[_CategorySpec, ...]:
    return tuple(
        sorted(
            categories,
            key=lambda category: (int(category.value), str(category.label)),
        )
    )


def _value_counts(categories: Sequence[_CategorySpec]) -> Dict[int, int]:
    counts: Dict[int, int] = {}
    for category in categories:
        counts[int(category.value)] = int(counts.get(int(category.value), 0)) + 1
    return counts


def _category_has_unique_value(category: _CategorySpec, counts: Mapping[int, int]) -> bool:
    return int(counts.get(int(category.value), 0)) == 1


def _condition_candidates(
    categories: Sequence[_CategorySpec],
    *,
    match_count_min: int,
    match_count_max: int,
) -> List[Tuple[_CategorySpec, _CategorySpec, Tuple[_CategorySpec, ...]]]:
    candidates: List[Tuple[_CategorySpec, _CategorySpec, Tuple[_CategorySpec, ...]]] = []
    for lower_ref in categories:
        for upper_ref in categories:
            if str(lower_ref.label) == str(upper_ref.label) or int(lower_ref.value) >= int(upper_ref.value):
                continue
            selected = tuple(
                category
                for category in categories
                if str(category.label) not in {str(lower_ref.label), str(upper_ref.label)}
                and int(lower_ref.value) < int(category.value) < int(upper_ref.value)
            )
            if int(match_count_min) <= len(selected) <= int(match_count_max):
                candidates.append((lower_ref, upper_ref, selected))
    return candidates


def _sample_conditional_categories_and_query(
    *,
    category_count: int,
    value_min: int,
    value_max: int,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], _CategorySpec, _CategorySpec, Tuple[_CategorySpec, ...], int]:
    match_min, match_max = _resolve_count_bounds(
        params,
        min_key="conditional_match_count_min",
        max_key="conditional_match_count_max",
        fallback_min=4,
        fallback_max=8,
    )
    for attempt in range(80):
        categories = _sample_categories(
            category_count=int(category_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed) + (int(attempt) * 1009),
        )
        candidates = _condition_candidates(
            categories,
            match_count_min=int(match_min),
            match_count_max=int(match_max),
        )
        if not candidates:
            continue
        available_counts = sorted({len(selected) for _, _, selected in candidates})
        target_count = _balanced_int(
            available_counts,
            params=count_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.conditional_match_count",
        )
        filtered_candidates = [
            candidate
            for candidate in candidates
            if len(candidate[2]) == int(target_count)
        ]
        chooser = spawn_rng(int(instance_seed), f"{TASK_ID}.conditional.candidate.{attempt}.{target_count}")
        lower_ref, upper_ref, selected = filtered_candidates[int(chooser.randrange(0, len(filtered_candidates)))]
        return tuple(categories), lower_ref, upper_ref, tuple(selected), int(attempt)
    raise ValueError("could not construct a conditional share query with the configured match-count bounds")


def _resolve_transfer_delta_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    return _resolve_count_bounds(
        params,
        min_key="counterfactual_transfer_delta_min",
        max_key="counterfactual_transfer_delta_max",
        fallback_min=3,
        fallback_max=10,
    )


def _sample_rank_conditioned_transfer(
    categories: Sequence[_CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> _TransferQuery | None:
    delta_min, delta_max = _resolve_transfer_delta_bounds(params)
    rank_min, rank_max = _resolve_count_bounds(
        params,
        min_key="transfer_rank_min",
        max_key="transfer_rank_max",
        fallback_min=1,
        fallback_max=5,
    )
    ranked_largest = _rank_categories(categories)
    ranked_smallest = _rank_categories_smallest(categories)
    max_rank = min(len(categories), int(rank_max))
    options: List[Tuple[int, int, _CategorySpec, _CategorySpec, int]] = []
    for source_rank in range(max(1, int(rank_min)), int(max_rank) + 1):
        for target_rank in range(max(1, int(rank_min)), int(max_rank) + 1):
            source = ranked_largest[int(source_rank) - 1]
            target = ranked_smallest[int(target_rank) - 1]
            if str(source.label) == str(target.label):
                continue
            for delta in range(int(delta_min), int(delta_max) + 1):
                if int(source.value) - int(delta) >= 1:
                    options.append((int(source_rank), int(target_rank), source, target, int(delta)))
    if not options:
        return None
    feasible_deltas = sorted({int(option[4]) for option in options})
    delta = _balanced_int(
        feasible_deltas,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.rank_conditioned_transfer_delta",
    )
    candidates = [option for option in options if int(option[4]) == int(delta)]
    option_index = _balanced_int(
        range(0, len(candidates)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.rank_conditioned_transfer_pair",
    )
    source_rank, target_rank, source, target, _ = candidates[int(option_index)]
    return _TransferQuery(
        source=source,
        target=target,
        delta=int(delta),
        extras={
            "source_rank": int(source_rank),
            "target_rank": int(target_rank),
            "source_rank_text": f"{_ordinal(int(source_rank))} largest",
            "target_rank_text": f"{_ordinal(int(target_rank))} smallest",
            "source_selection_rule": "ranked_largest",
            "target_selection_rule": "ranked_smallest",
            "ranked_largest_labels": [str(category.label) for category in ranked_largest],
            "ranked_smallest_labels": [str(category.label) for category in ranked_smallest],
            "ranked_largest_values": [int(category.value) for category in ranked_largest],
            "ranked_smallest_values": [int(category.value) for category in ranked_smallest],
            "calculation": "rank_conditioned_absolute_gap_after_share_transfer",
        },
    )


def _sample_threshold_conditioned_transfer(
    categories: Sequence[_CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> _TransferQuery | None:
    delta_min, delta_max = _resolve_transfer_delta_bounds(params)
    value_counts = _value_counts(categories)
    options: List[Tuple[_CategorySpec, _CategorySpec, int]] = []
    for source in categories:
        if not _category_has_unique_value(source, value_counts):
            continue
        for target in categories:
            if str(source.label) == str(target.label) or not _category_has_unique_value(target, value_counts):
                continue
            for delta in range(int(delta_min), int(delta_max) + 1):
                if int(source.value) - int(delta) >= 1 and int(target.value) >= 2:
                    options.append((source, target, int(delta)))
    if not options:
        return None
    feasible_deltas = sorted({int(option[2]) for option in options})
    delta = _balanced_int(
        feasible_deltas,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.threshold_conditioned_transfer_delta",
    )
    candidates = [option for option in options if int(option[2]) == int(delta)]
    option_index = _balanced_int(
        range(0, len(candidates)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.threshold_conditioned_transfer_pair",
    )
    source, target, _ = candidates[int(option_index)]
    source_threshold = int(source.value) + 1
    target_threshold = int(target.value) - 1
    return _TransferQuery(
        source=source,
        target=target,
        delta=int(delta),
        extras={
            "source_threshold": int(source_threshold),
            "target_threshold": int(target_threshold),
            "source_selection_rule": "largest_category_below_threshold",
            "target_selection_rule": "smallest_category_above_threshold",
            "calculation": "threshold_conditioned_absolute_gap_after_share_transfer",
        },
    )


def _sample_chart_order_adjacent_transfer(
    categories: Sequence[_CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> _TransferQuery | None:
    delta_min, delta_max = _resolve_transfer_delta_bounds(params)
    options: List[Tuple[str, _CategorySpec, _CategorySpec, int, int, int]] = []
    for source_index, source in enumerate(categories):
        for direction in CIRCULAR_ORDER_DIRECTIONS:
            step = 1 if str(direction) == "clockwise" else -1
            target_index = (int(source_index) + int(step)) % len(categories)
            target = categories[int(target_index)]
            for delta in range(int(delta_min), int(delta_max) + 1):
                if int(source.value) - int(delta) >= 1:
                    options.append(
                        (
                            str(direction),
                            source,
                            target,
                            int(source_index),
                            int(target_index),
                            int(delta),
                        )
                    )
    if not options:
        return None
    feasible_deltas = sorted({int(option[5]) for option in options})
    delta = _balanced_int(
        feasible_deltas,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.chart_order_adjacent_transfer_delta",
    )
    candidates = [option for option in options if int(option[5]) == int(delta)]
    direction_index = _balanced_int(
        range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.chart_order_adjacent_transfer_direction",
    )
    direction = str(CIRCULAR_ORDER_DIRECTIONS[int(direction_index)])
    direction_candidates = [option for option in candidates if str(option[0]) == str(direction)]
    if not direction_candidates:
        direction_candidates = candidates
    option_index = _balanced_int(
        range(0, len(direction_candidates)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.chart_order_adjacent_transfer_source",
    )
    direction, source, target, source_index, target_index, delta = direction_candidates[int(option_index)]
    return _TransferQuery(
        source=source,
        target=target,
        delta=int(delta),
        extras={
            "source_order_direction": str(direction),
            "source_index": int(source_index),
            "target_index": int(target_index),
            "source_selection_rule": "explicit_category_in_chart_order",
            "target_selection_rule": "adjacent_category_in_chart_order",
            "calculation": "adjacent_chart_order_absolute_gap_after_share_transfer",
        },
    )


def _sample_transfer_categories_and_query(
    *,
    query_id: str,
    category_count: int,
    value_min: int,
    value_max: int,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], _TransferQuery, int]:
    selectors = {
        "rank_conditioned_transfer_gap": _sample_rank_conditioned_transfer,
        "threshold_conditioned_transfer_gap": _sample_threshold_conditioned_transfer,
        "chart_order_adjacent_transfer_gap": _sample_chart_order_adjacent_transfer,
    }
    selector = selectors[str(query_id)]
    for attempt in range(160):
        categories = _sample_categories(
            category_count=int(category_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed) + (int(attempt) * 1009),
        )
        query = selector(
            categories,
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed) + int(attempt),
        )
        if query is not None:
            return tuple(categories), query, int(attempt)
    raise ValueError(f"could not construct transfer-gap query for {query_id}")


def _sample_total_count(
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> int:
    configured = params.get("part_whole_total_values", group_default(_GEN_DEFAULTS, "part_whole_total_values", None))
    if configured is None:
        configured = (600, 800, 1000, 1200, 1500, 1800, 2000, 2400, 3000)
    values = [int(value) for value in configured]
    if not values or any(int(value) <= 0 for value in values):
        raise ValueError("part_whole_total_values must contain positive integers")
    if any(int(value) % 100 != 0 for value in values):
        raise ValueError("part_whole_total_values must be multiples of 100 so count answers are integral")
    return _balanced_int(
        values,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.part_whole_total_count",
    )


def _count_from_share(total_count: int, share_value: int) -> int:
    return int((int(total_count) * int(share_value)) // 100)


def _build_selected_share_to_count_query(
    categories: Sequence[_CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], Dict[str, Any]]:
    rank_min, rank_max = _resolve_count_bounds(
        params,
        min_key="part_whole_rank_position_min",
        max_key="part_whole_rank_position_max",
        fallback_min=1,
        fallback_max=6,
    )
    set_size_min, set_size_max = _resolve_count_bounds(
        params,
        min_key="part_whole_rank_set_size_min",
        max_key="part_whole_rank_set_size_max",
        fallback_min=2,
        fallback_max=3,
    )
    feasible_positions = [
        positions
        for set_size in range(max(1, int(set_size_min)), min(int(set_size_max), int(rank_max) - int(rank_min) + 1) + 1)
        for positions in itertools.combinations(range(max(1, int(rank_min)), min(int(rank_max), len(categories)) + 1), int(set_size))
        if all(int(right) - int(left) >= 1 for left, right in zip(positions, positions[1:]))
    ]
    if not feasible_positions:
        raise ValueError("could not construct selected_share_to_count rank positions")
    position_index = _balanced_int(
        range(0, len(feasible_positions)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.part_whole_rank_position_set",
    )
    rank_positions = tuple(int(position) for position in feasible_positions[int(position_index)])
    ranked = _rank_categories(categories)
    selected = tuple(ranked[int(position) - 1] for position in rank_positions)
    return selected, {
        "ranked_labels": [str(category.label) for category in ranked],
        "ranked_values": [int(category.value) for category in ranked],
        "rank_positions": [int(position) for position in rank_positions],
        "rank_position_texts": [_ordinal(int(position)) for position in rank_positions],
        "rank_position_list_text": _format_quoted([_ordinal(int(position)) for position in rank_positions]),
        "rank_direction": "largest",
        "rank_position_set_size": int(len(rank_positions)),
        "rank_position_set_index": int(position_index),
    }


def _build_sector_share_to_angle_query(
    categories: Sequence[_CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], Dict[str, Any]] | None:
    span_min, span_max = _resolve_count_bounds(
        params,
        min_key="part_whole_angle_span_count_min",
        max_key="part_whole_angle_span_count_max",
        fallback_min=2,
        fallback_max=5,
    )
    feasible_span_min = max(1, int(span_min))
    feasible_span_max = min(int(span_max), len(categories) - 1)
    if int(feasible_span_min) > int(feasible_span_max):
        return None
    feasible_spans = range(int(feasible_span_min), int(feasible_span_max) + 1)
    direction_index = _balanced_int(
        range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.part_whole_angle_order_direction",
    )
    order_direction = str(CIRCULAR_ORDER_DIRECTIONS[int(direction_index)])
    step = 1 if str(order_direction) == "clockwise" else -1
    options: List[Tuple[int, int, Tuple[int, ...], int]] = []
    for span_count in feasible_spans:
        for start_index in range(0, len(categories)):
            selected_indices = tuple((int(start_index) + (int(step) * int(offset))) % len(categories) for offset in range(int(span_count)))
            selected_share = int(sum(int(categories[int(index)].value) for index in selected_indices))
            if int(selected_share) % 5 == 0:
                options.append((int(span_count), int(start_index), tuple(int(index) for index in selected_indices), int(selected_share)))
    if not options:
        return None
    option_index = _balanced_int(
        range(0, len(options)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.part_whole_angle_span",
    )
    span_count, start_index, selected_indices, selected_share = options[int(option_index)]
    selected = tuple(categories[int(index)] for index in selected_indices)
    return selected, {
        "start_category": str(selected[0].label),
        "end_category": str(selected[-1].label),
        "start_index": int(start_index),
        "end_index": int(selected_indices[-1]),
        "selected_indices": [int(index) for index in selected_indices],
        "span_count": int(span_count),
        "span_count_range": [int(feasible_span_min), int(feasible_span_max)],
        "chart_order_direction": str(order_direction),
        "selected_share_value": int(selected_share),
        "sector_angle_degrees": int((int(selected_share) * 360) // 100),
    }


def _build_chart_order_span_query(
    categories: Sequence[_CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    namespace_suffix: str,
) -> Tuple[Tuple[_CategorySpec, ...], Dict[str, Any]]:
    span_min, span_max = _resolve_count_bounds(
        params,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
    )
    feasible_span_min = max(2, int(span_min))
    feasible_span_max = min(int(span_max), len(categories) - 1)
    if int(feasible_span_min) > int(feasible_span_max):
        raise ValueError(f"{namespace_suffix} requires enough categories for a non-full chart-order span")
    feasible_spans = range(int(feasible_span_min), int(feasible_span_max) + 1)
    span_count = _balanced_int(
        feasible_spans,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{namespace_suffix}.span_count",
    )
    direction_index = _balanced_int(
        range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{namespace_suffix}.order_direction",
    )
    order_direction = str(CIRCULAR_ORDER_DIRECTIONS[int(direction_index)])
    start_index = _balanced_int(
        range(0, len(categories)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{namespace_suffix}.start_index",
    )
    step = 1 if str(order_direction) == "clockwise" else -1
    selected_indices = tuple((int(start_index) + (int(step) * int(offset))) % len(categories) for offset in range(int(span_count)))
    selected = tuple(categories[int(index)] for index in selected_indices)
    selected_share = int(sum(int(category.value) for category in selected))
    return selected, {
        "start_category": str(selected[0].label),
        "end_category": str(selected[-1].label),
        "start_index": int(start_index),
        "end_index": int(selected_indices[-1]),
        "selected_indices": [int(index) for index in selected_indices],
        "span_count": int(span_count),
        "span_count_range": [int(feasible_span_min), int(feasible_span_max)],
        "chart_order_direction": str(order_direction),
        "selected_share_value": int(selected_share),
    }


def _sample_subset_denominator_categories_and_query(
    *,
    category_count: int,
    value_min: int,
    value_max: int,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], Tuple[_CategorySpec, ...], Dict[str, Any], int]:
    subset_min, subset_max = _resolve_count_bounds(
        params,
        min_key="subset_denominator_size_min",
        max_key="subset_denominator_size_max",
        fallback_min=2,
        fallback_max=4,
    )
    subset_sizes = list(range(max(2, int(subset_min)), min(int(subset_max), int(category_count) - 1) + 1))
    if not subset_sizes:
        raise ValueError("subset_denominator_share_value requires at least one non-full subset")
    answer_values = _configured_int_values(
        params,
        key="subset_denominator_answer_values",
        fallback=(20, 25, 30, 40, 50, 60, 70, 75, 80),
    )

    feasible: List[Tuple[int, int, int, int, int]] = []
    for subset_size in subset_sizes:
        outside_count = int(category_count) - int(subset_size)
        subset_total_min = max(int(subset_size) * int(value_min), 12)
        subset_total_max = min(int(subset_size) * int(value_max), 100 - (int(outside_count) * int(value_min)))
        for answer_percent in answer_values:
            if not 1 <= int(answer_percent) <= 99:
                continue
            for subset_total in range(int(subset_total_min), int(subset_total_max) + 1):
                product = int(subset_total) * int(answer_percent)
                if product % 100 != 0:
                    continue
                target_value = int(product // 100)
                subset_remainder = int(subset_total) - int(target_value)
                outside_total = 100 - int(subset_total)
                if not int(value_min) <= int(target_value) <= int(value_max):
                    continue
                if not (int(subset_size) - 1) * int(value_min) <= int(subset_remainder) <= (int(subset_size) - 1) * int(value_max):
                    continue
                if not int(outside_count) * int(value_min) <= int(outside_total) <= int(outside_count) * int(value_max):
                    continue
                feasible.append(
                    (
                        int(answer_percent),
                        int(subset_size),
                        int(subset_total),
                        int(target_value),
                        int(outside_total),
                    )
                )
    if not feasible:
        raise ValueError("could not construct subset-denominator share values with configured bounds")

    available_answers = sorted({int(item[0]) for item in feasible})
    answer_percent = _balanced_int(
        available_answers,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.subset_denominator.answer_percent",
    )
    answer_candidates = [item for item in feasible if int(item[0]) == int(answer_percent)]
    available_subset_sizes = sorted({int(item[1]) for item in answer_candidates})
    subset_size = _balanced_int(
        available_subset_sizes,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.subset_denominator.subset_size",
    )
    size_candidates = [item for item in answer_candidates if int(item[1]) == int(subset_size)]
    available_subset_totals = sorted({int(item[2]) for item in size_candidates})
    subset_total = _balanced_int(
        available_subset_totals,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.subset_denominator.subset_total",
    )
    target_value = int(int(subset_total) * int(answer_percent) // 100)
    outside_total = int(100 - int(subset_total))
    subset_remainder = int(subset_total) - int(target_value)
    outside_count = int(category_count) - int(subset_size)

    subset_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.subset_denominator.subset_rest")
    outside_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.subset_denominator.outside")
    subset_rest = sample_composition_with_sum(
        subset_rng,
        target_sum=int(subset_remainder),
        count=int(subset_size) - 1,
        value_min=int(value_min),
        value_max=int(value_max),
    )
    outside_values = sample_composition_with_sum(
        outside_rng,
        target_sum=int(outside_total),
        count=int(outside_count),
        value_min=int(value_min),
        value_max=int(value_max),
    )
    entries: List[Tuple[str, int]] = [("target", int(target_value))]
    entries.extend(("subset", int(value)) for value in subset_rest)
    entries.extend(("outside", int(value)) for value in outside_values)
    layout_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.subset_denominator.layout")
    layout_rng.shuffle(entries)
    categories = _sample_categories_from_values(
        [int(value) for _, value in entries],
        instance_seed=int(instance_seed),
        namespace_suffix="subset_denominator",
    )
    subset_indices = tuple(index for index, (role, _) in enumerate(entries) if str(role) in {"target", "subset"})
    target_index = next(index for index, (role, _) in enumerate(entries) if str(role) == "target")
    selected = tuple(categories[int(index)] for index in subset_indices)
    target_category = categories[int(target_index)]
    return tuple(categories), tuple(selected), {
        "target_category": str(target_category.label),
        "target_index": int(target_index),
        "target_share_value": int(target_category.value),
        "category_list": [str(category.label) for category in selected],
        "subset_category_list": [str(category.label) for category in selected],
        "subset_category_list_text": _format_quoted([str(category.label) for category in selected]),
        "selected_indices": [int(index) for index in subset_indices],
        "subset_size": int(len(selected)),
        "subset_size_range": [int(min(subset_sizes)), int(max(subset_sizes))],
        "selected_share_value": int(subset_total),
        "subset_share_total": int(subset_total),
        "subset_denominator_percent": int(answer_percent),
        "calculation": "compute_category_share_within_named_subset_denominator",
    }, 0


def _sample_part_whole_categories_and_query(
    *,
    query_id: str,
    category_count: int,
    value_min: int,
    value_max: int,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], Tuple[_CategorySpec, ...], Dict[str, Any], int]:
    for attempt in range(160):
        categories = _sample_categories(
            category_count=int(category_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed) + (int(attempt) * 1009),
        )
        if str(query_id) in {"chart_order_share_to_count", "chart_order_remaining_count"}:
            selected, query_extras = _build_chart_order_span_query(
                categories,
                params=params,
                count_params=count_params,
                instance_seed=int(instance_seed) + int(attempt),
                min_key="part_whole_span_count_min",
                max_key="part_whole_span_count_max",
                fallback_min=3,
                fallback_max=5,
                namespace_suffix=str(query_id),
            )
            return tuple(categories), tuple(selected), dict(query_extras), int(attempt)
        if str(query_id) == "subset_denominator_share_value":
            return _sample_subset_denominator_categories_and_query(
                category_count=int(category_count),
                value_min=int(value_min),
                value_max=int(value_max),
                params=params,
                count_params=count_params,
                instance_seed=int(instance_seed) + int(attempt),
            )
        if str(query_id) == "selected_share_to_count":
            selected, query_extras = _build_selected_share_to_count_query(
                categories,
                params=params,
                count_params=count_params,
                instance_seed=int(instance_seed) + int(attempt),
            )
            return tuple(categories), tuple(selected), dict(query_extras), int(attempt)
        if str(query_id) == "sector_share_to_angle":
            query = _build_sector_share_to_angle_query(
                categories,
                params=params,
                count_params=count_params,
                instance_seed=int(instance_seed) + int(attempt),
            )
            if query is None:
                continue
            selected, query_extras = query
            return tuple(categories), tuple(selected), dict(query_extras), int(attempt)
    raise ValueError(f"could not construct part-whole query for {query_id}")


def _build_ranked_group_share_gap_query(
    categories: Sequence[_CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], Tuple[_CategorySpec, ...], Dict[str, Any]]:
    group_min, group_max = _resolve_count_bounds(
        params,
        min_key="group_gap_group_size_min",
        max_key="group_gap_group_size_max",
        fallback_min=2,
        fallback_max=3,
    )
    feasible_sizes = list(range(max(1, int(group_min)), min(int(group_max), len(categories) // 2) + 1))
    if not feasible_sizes:
        raise ValueError("ranked_group_share_gap requires enough categories for two disjoint groups")
    group_size = _balanced_int(
        feasible_sizes,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.ranked_group_gap_size",
    )
    ranked_largest = _rank_categories(categories)
    ranked_smallest = _rank_categories_smallest(categories)
    largest_group = tuple(ranked_largest[: int(group_size)])
    smallest_group = tuple(ranked_smallest[: int(group_size)])
    largest_share = int(sum(int(category.value) for category in largest_group))
    smallest_share = int(sum(int(category.value) for category in smallest_group))
    return largest_group, smallest_group, {
        "group_size": int(group_size),
        "group_size_range": [int(group_min), int(group_max)],
        "largest_group_labels": [str(category.label) for category in largest_group],
        "smallest_group_labels": [str(category.label) for category in smallest_group],
        "largest_group_share": int(largest_share),
        "smallest_group_share": int(smallest_share),
        "ranked_largest_labels": [str(category.label) for category in ranked_largest],
        "ranked_smallest_labels": [str(category.label) for category in ranked_smallest],
        "ranked_largest_values": [int(category.value) for category in ranked_largest],
        "ranked_smallest_values": [int(category.value) for category in ranked_smallest],
        "calculation": "rank_categories_then_subtract_bottom_group_share_from_top_group_share",
    }


def _sample_known_part_count_categories_and_query(
    *,
    category_count: int,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], Tuple[_CategorySpec, ...], _CategorySpec, Dict[str, Any], int]:
    for attempt in range(160):
        categories = _sample_ranked_categories(
            category_count=int(category_count),
            instance_seed=int(instance_seed) + (int(attempt) * 1009),
        )
        selected, query_extras = _build_selected_share_to_count_query(
            categories,
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed) + int(attempt),
        )
        selected_labels = {str(category.label) for category in selected}
        candidates = [category for category in categories if str(category.label) not in selected_labels]
        if not candidates:
            continue
        candidate_index = _balanced_int(
            range(0, len(candidates)),
            params=count_params,
            instance_seed=int(instance_seed) + int(attempt),
            namespace=f"{TASK_ID}.known_part_category",
        )
        known_category = candidates[int(candidate_index)]
        total_count = _sample_total_count(
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed) + int(attempt),
        )
        known_count = _count_from_share(int(total_count), int(known_category.value))
        selected_share = int(sum(int(category.value) for category in selected))
        return tuple(categories), tuple(selected), known_category, {
            **dict(query_extras),
            "known_count_category": str(known_category.label),
            "known_count_value": int(known_count),
            "known_category_share_value": int(known_category.value),
            "inferred_total_count": int(total_count),
            "selected_share_value": int(selected_share),
            "known_part_sampling_attempt": int(attempt),
            "calculation": "infer_total_from_one_known_category_count_then_convert_ranked_group_share_to_count",
        }, int(attempt)
    raise ValueError("could not construct known_part_to_group_count query")


def _build_cumulative_threshold_query(
    categories: Sequence[_CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], Dict[str, Any]] | None:
    count_min, count_max = _resolve_count_bounds(
        params,
        min_key="cumulative_threshold_answer_count_min",
        max_key="cumulative_threshold_answer_count_max",
        fallback_min=3,
        fallback_max=6,
    )
    threshold_min, threshold_max = _resolve_count_bounds(
        params,
        min_key="cumulative_threshold_min",
        max_key="cumulative_threshold_max",
        fallback_min=45,
        fallback_max=75,
    )
    ranked = _rank_categories(categories)
    prefix_sums: List[int] = []
    running = 0
    for category in ranked:
        running += int(category.value)
        prefix_sums.append(int(running))

    options: List[Tuple[int, int, int]] = []
    for answer_count in range(max(1, int(count_min)), min(int(count_max), len(ranked)) + 1):
        previous_sum = int(prefix_sums[int(answer_count) - 2]) if int(answer_count) > 1 else 0
        current_sum = int(prefix_sums[int(answer_count) - 1])
        threshold_low = max(int(threshold_min), int(previous_sum) + 1)
        threshold_high = min(int(threshold_max), int(current_sum))
        if int(threshold_low) <= int(threshold_high):
            options.append((int(answer_count), int(threshold_low), int(threshold_high)))
    if not options:
        return None

    feasible_counts = sorted({int(option[0]) for option in options})
    answer_count = _balanced_int(
        feasible_counts,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.cumulative_threshold_answer_count",
    )
    intervals = [(int(low), int(high)) for count, low, high in options if int(count) == int(answer_count)]
    interval_index = _balanced_int(
        range(0, len(intervals)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.cumulative_threshold_interval",
    )
    threshold_low, threshold_high = intervals[int(interval_index)]
    threshold_value = _balanced_int(
        range(int(threshold_low), int(threshold_high) + 1),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.cumulative_threshold_value",
    )
    selected = tuple(ranked[: int(answer_count)])
    previous_cumulative = int(prefix_sums[int(answer_count) - 2]) if int(answer_count) > 1 else 0
    selected_share = int(prefix_sums[int(answer_count) - 1])
    return selected, {
        "threshold_value": int(threshold_value),
        "threshold_range": [int(threshold_min), int(threshold_max)],
        "cumulative_answer_count": int(answer_count),
        "cumulative_answer_count_range": [int(count_min), int(count_max)],
        "previous_cumulative_share": int(previous_cumulative),
        "selected_share_value": int(selected_share),
        "ranked_labels": [str(category.label) for category in ranked],
        "ranked_values": [int(category.value) for category in ranked],
        "calculation": "rank_categories_largest_to_smallest_then_count_prefix_to_reach_threshold",
    }


def _sample_cumulative_threshold_categories_and_query(
    *,
    category_count: int,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], Tuple[_CategorySpec, ...], Dict[str, Any], int]:
    for attempt in range(160):
        categories = _sample_ranked_categories(
            category_count=int(category_count),
            instance_seed=int(instance_seed) + (int(attempt) * 1009),
        )
        query = _build_cumulative_threshold_query(
            categories,
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed) + int(attempt),
        )
        if query is None:
            continue
        selected, query_extras = query
        return tuple(categories), tuple(selected), dict(query_extras), int(attempt)
    raise ValueError("could not construct cumulative_share_threshold_count query")


def _annotation_value_for_label(
    label: str,
    *,
    extras: Mapping[str, Any],
    values_by_label: Mapping[str, int],
) -> int:
    if str(label) == "__total__":
        return int(extras["total_count"])
    if str(label) == "__known_count__":
        return int(extras["known_count_value"])
    return int(values_by_label[str(label)])


def _public_annotation_key(label: str) -> str:
    if str(label) == "__total__":
        return "total_count"
    if str(label) == "__known_count__":
        return "known_count"
    return str(label)


def _build_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Dataset:
    category_min, category_max = _category_count_bounds(params, query_id=str(query_id))
    count_params = _params_with_shifted_sample_cursor(
        params,
        divisor=int(_task_axis_stride(params) * _scene_axis_stride(params)),
    )
    category_count_support = list(range(int(category_min), int(category_max) + 1))
    if str(query_id) == "positional_segment_share_sum":
        category_count_support = [int(value) for value in category_count_support if int(value) % 2 == 0]
        if not category_count_support:
            raise ValueError("positional_segment_share_sum requires at least one even category count")
    category_count = _balanced_int(
        category_count_support,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.category_count",
    )
    value_min, value_max = _value_bounds(params, query_id=str(query_id))
    transfer_query: _TransferQuery | None = None
    transfer_sampling_attempt: int | None = None
    part_whole_selected: Tuple[_CategorySpec, ...] = ()
    part_whole_query_extras: Dict[str, Any] = {}
    part_whole_sampling_attempt: int | None = None
    ranked_group_largest: Tuple[_CategorySpec, ...] = ()
    ranked_group_smallest: Tuple[_CategorySpec, ...] = ()
    ranked_group_query_extras: Dict[str, Any] = {}
    known_part_selected: Tuple[_CategorySpec, ...] = ()
    known_part_category: _CategorySpec | None = None
    known_part_query_extras: Dict[str, Any] = {}
    known_part_sampling_attempt: int | None = None
    cumulative_selected: Tuple[_CategorySpec, ...] = ()
    cumulative_query_extras: Dict[str, Any] = {}
    cumulative_sampling_attempt: int | None = None
    if str(query_id) == "ranked_position_set_sum":
        categories = _sample_ranked_categories(
            category_count=int(category_count),
            instance_seed=int(instance_seed),
        )
    elif str(query_id) == "conditional_share_sum":
        categories = ()
    elif str(query_id) in TRANSFER_GAP_QUERY_IDS:
        categories, transfer_query, transfer_sampling_attempt = _sample_transfer_categories_and_query(
            query_id=str(query_id),
            category_count=int(category_count),
            value_min=int(value_min),
            value_max=int(value_max),
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed),
        )
    elif str(query_id) in PART_WHOLE_QUERY_IDS:
        categories, part_whole_selected, part_whole_query_extras, part_whole_sampling_attempt = _sample_part_whole_categories_and_query(
            query_id=str(query_id),
            category_count=int(category_count),
            value_min=int(value_min),
            value_max=int(value_max),
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed),
        )
    elif str(query_id) == "ranked_group_share_gap":
        categories = _sample_ranked_categories(
            category_count=int(category_count),
            instance_seed=int(instance_seed),
        )
        ranked_group_largest, ranked_group_smallest, ranked_group_query_extras = _build_ranked_group_share_gap_query(
            categories,
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed),
        )
    elif str(query_id) == "known_part_to_group_count":
        categories, known_part_selected, known_part_category, known_part_query_extras, known_part_sampling_attempt = _sample_known_part_count_categories_and_query(
            category_count=int(category_count),
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed),
        )
    elif str(query_id) == "cumulative_share_threshold_count":
        categories, cumulative_selected, cumulative_query_extras, cumulative_sampling_attempt = _sample_cumulative_threshold_categories_and_query(
            category_count=int(category_count),
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed),
        )
    else:
        categories = _sample_categories(
            category_count=int(category_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
        )

    if str(query_id) == "conditional_share_sum":
        categories, lower_ref, upper_ref, selected, sampling_attempt = _sample_conditional_categories_and_query(
            category_count=int(category_count),
            value_min=int(value_min),
            value_max=int(value_max),
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed),
        )

    labels = tuple(str(category.label) for category in categories)
    values_by_label = {str(category.label): int(category.value) for category in categories}
    extras: Dict[str, Any] = {
        "category_count": int(category_count),
        "category_count_range": [int(category_min), int(category_max)],
        "value_min": int(value_min),
        "value_max": int(value_max),
        "category_values": {str(label): int(values_by_label[str(label)]) for label in labels},
        "chart_order_labels": [str(label) for label in labels],
        "table_order_labels": [str(label) for label in sorted(labels)],
    }

    if str(query_id) == "ranked_position_set_sum":
        rank_min, rank_max = _resolve_count_bounds(
            params,
            min_key="rank_position_min",
            max_key="rank_position_max",
            fallback_min=1,
            fallback_max=7,
        )
        set_size_min, set_size_max = _resolve_count_bounds(
            params,
            min_key="rank_position_set_size_min",
            max_key="rank_position_set_size_max",
            fallback_min=3,
            fallback_max=3,
        )
        feasible_positions = [
            positions
            for set_size in range(max(1, int(set_size_min)), min(int(set_size_max), int(rank_max) - int(rank_min) + 1) + 1)
            for positions in itertools.combinations(range(max(1, int(rank_min)), int(rank_max) + 1), int(set_size))
            if all(int(right) - int(left) >= 2 for left, right in zip(positions, positions[1:]))
        ]
        position_index = _balanced_int(
            range(len(feasible_positions)),
            params=count_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.rank_position_set",
        )
        rank_positions = tuple(int(position) for position in feasible_positions[int(position_index)])
        ranked = _rank_categories(categories)
        selected_categories = tuple(ranked[int(position) - 1] for position in rank_positions)
        selected = tuple(str(category.label) for category in selected_categories)
        answer_value = int(sum(values_by_label[str(label)] for label in selected))
        extras.update(
            {
                "category_list": [str(label) for label in selected],
                "ranked_labels": [str(category.label) for category in ranked],
                "ranked_values": [int(category.value) for category in ranked],
                "rank_positions": [int(position) for position in rank_positions],
                "rank_position_texts": [_ordinal(int(position)) for position in rank_positions],
                "rank_position_list_text": _format_quoted([_ordinal(int(position)) for position in rank_positions]),
                "rank_direction": "largest",
                "rank_position_set_size": int(len(rank_positions)),
                "rank_position_set_index": int(position_index),
                "calculation": "rank_categories_by_share_then_sum_noncontiguous_rank_positions",
            }
        )
        annotation_labels = tuple(str(label) for label in selected)
    elif str(query_id) == "conditional_share_sum":
        selected_labels = tuple(str(category.label) for category in selected)
        answer_value = int(sum(int(category.value) for category in selected))
        extras.update(
            {
                "category_list": [str(label) for label in selected_labels],
                "lower_reference_category": str(lower_ref.label),
                "upper_reference_category": str(upper_ref.label),
                "lower_reference_value": int(lower_ref.value),
                "upper_reference_value": int(upper_ref.value),
                "matching_category_count": int(len(selected)),
                "matching_category_values": [int(category.value) for category in selected],
                "conditional_sampling_attempt": int(sampling_attempt),
                "calculation": "filter_categories_between_two_reference_shares_then_sum",
            }
        )
        annotation_labels = (str(lower_ref.label), str(upper_ref.label), *selected_labels)
    elif str(query_id) == "contiguous_chart_order_sum":
        span_min, span_max = _resolve_count_bounds(
            params,
            min_key="contiguous_span_count_min",
            max_key="contiguous_span_count_max",
            fallback_min=3,
            fallback_max=6,
        )
        feasible_span_min = max(2, int(span_min))
        feasible_span_max = min(int(span_max), int(category_count) - 1)
        if int(feasible_span_min) > int(feasible_span_max):
            raise ValueError("contiguous_chart_order_sum requires enough categories for a non-full chart-order span")
        feasible_spans = range(int(feasible_span_min), int(feasible_span_max) + 1)
        span_count = _balanced_int(
            feasible_spans,
            params=count_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.contiguous_span_count",
        )
        direction_index = _balanced_int(
            range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
            params=count_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.contiguous_order_direction",
        )
        order_direction = str(CIRCULAR_ORDER_DIRECTIONS[int(direction_index)])
        start_index = _balanced_int(
            range(0, int(category_count)),
            params=count_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.contiguous_start_index",
        )
        step = 1 if str(order_direction) == "clockwise" else -1
        selected_indices = tuple((int(start_index) + (int(step) * int(offset))) % int(category_count) for offset in range(int(span_count)))
        selected_categories = tuple(categories[int(index)] for index in selected_indices)
        selected = tuple(str(category.label) for category in selected_categories)
        answer_value = int(sum(int(category.value) for category in selected_categories))
        extras.update(
            {
                "category_list": [str(label) for label in selected],
                "start_category": str(selected[0]),
                "end_category": str(selected[-1]),
                "start_index": int(start_index),
                "end_index": int(selected_indices[-1]),
                "selected_indices": [int(index) for index in selected_indices],
                "span_count": int(span_count),
                "span_count_range": [int(feasible_span_min), int(feasible_span_max)],
                "chart_order_direction": str(order_direction),
                "calculation": "sum_contiguous_categories_in_circular_chart_order",
            }
        )
        annotation_labels = tuple(str(label) for label in selected)
    elif str(query_id) == "positional_segment_share_sum":
        relation_index = _balanced_int(
            range(0, len(POSITIONAL_RELATIONS)),
            params=count_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.positional_relation",
        )
        position_relation = str(POSITIONAL_RELATIONS[int(relation_index)])
        relation_seed = int(instance_seed) + (int(relation_index) * 10007)
        relation_rng = spawn_rng(int(relation_seed), f"{TASK_ID}.positional.{position_relation}")
        annotation_prefix: Tuple[str, ...] = ()
        order_direction = "clockwise"
        anchor_label: str | None = None

        if position_relation == "anchor_offset_sum":
            anchor_index = int(relation_rng.randrange(0, int(category_count)))
            anchor_label = str(categories[int(anchor_index)].label)
            direction_index = _balanced_int(
                range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
                params=count_params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.positional.anchor_direction",
            )
            order_direction = str(CIRCULAR_ORDER_DIRECTIONS[int(direction_index)])
            feasible_offsets = [
                offsets
                for offsets in itertools.combinations(range(1, int(category_count)), 2)
                if int(offsets[1]) - int(offsets[0]) >= 2
            ]
            offset_index = _balanced_int(
                range(0, len(feasible_offsets)),
                params=count_params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.positional.anchor_offsets",
            )
            selected_offsets = tuple(int(offset) for offset in feasible_offsets[int(offset_index)])
            step = 1 if str(order_direction) == "clockwise" else -1
            selected_indices = tuple((int(anchor_index) + (int(step) * int(offset))) % int(category_count) for offset in selected_offsets)
            selected_categories = tuple(categories[int(index)] for index in selected_indices)
            selected = tuple(str(category.label) for category in selected_categories)
            annotation_prefix = (str(anchor_label),)
            positional_instruction = (
                f"Starting at category \"{anchor_label}\" and moving {order_direction}, use the segments "
                f"{_format_offset_list(selected_offsets)} away from that anchor. Do not include category \"{anchor_label}\"."
            )
            extras.update(
                {
                    "anchor_category": str(anchor_label),
                    "anchor_index": int(anchor_index),
                    "selected_offsets": [int(offset) for offset in selected_offsets],
                    "offset_list_text": _format_offset_list(selected_offsets),
                    "offset_index": int(offset_index),
                }
            )
        elif position_relation == "opposite_neighbor_sum":
            anchor_index = int(relation_rng.randrange(0, int(category_count)))
            anchor_label = str(categories[int(anchor_index)].label)
            direction_index = _balanced_int(
                range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
                params=count_params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.positional.opposite_direction",
            )
            order_direction = str(CIRCULAR_ORDER_DIRECTIONS[int(direction_index)])
            step = 1 if str(order_direction) == "clockwise" else -1
            opposite_index = (int(anchor_index) + (int(category_count) // 2)) % int(category_count)
            neighbor_index = (int(opposite_index) + int(step)) % int(category_count)
            selected_indices = (int(opposite_index), int(neighbor_index))
            selected_categories = tuple(categories[int(index)] for index in selected_indices)
            selected = tuple(str(category.label) for category in selected_categories)
            annotation_prefix = (str(anchor_label),)
            positional_instruction = (
                f"Find the segment opposite category \"{anchor_label}\", then also use the segment immediately "
                f"{order_direction} from that opposite segment."
            )
            extras.update(
                {
                    "anchor_category": str(anchor_label),
                    "anchor_index": int(anchor_index),
                    "opposite_index": int(opposite_index),
                    "opposite_category": str(categories[int(opposite_index)].label),
                    "neighbor_index": int(neighbor_index),
                    "neighbor_category": str(categories[int(neighbor_index)].label),
                }
            )
        else:
            raise ValueError(f"unsupported positional relation: {position_relation}")

        answer_value = int(sum(int(category.value) for category in selected_categories))
        extras.update(
            {
                "category_list": [str(label) for label in selected],
                "selected_indices": [int(index) for index in selected_indices],
                "position_relation": str(position_relation),
                "position_relation_index": int(relation_index),
                "positional_instruction": str(positional_instruction),
                "chart_order_direction": str(order_direction),
                "calculation": "select_segments_by_circular_position_then_sum_shares",
            }
        )
        annotation_labels = (*annotation_prefix, *tuple(str(label) for label in selected))
    elif str(query_id) == "ranked_group_share_gap":
        largest_group = tuple(ranked_group_largest)
        smallest_group = tuple(ranked_group_smallest)
        largest_labels = tuple(str(category.label) for category in largest_group)
        smallest_labels = tuple(str(category.label) for category in smallest_group)
        largest_share = int(sum(int(category.value) for category in largest_group))
        smallest_share = int(sum(int(category.value) for category in smallest_group))
        answer_value = int(largest_share - smallest_share)
        extras.update(
            {
                "category_list": [*list(largest_labels), *list(smallest_labels)],
                "largest_group_share": int(largest_share),
                "smallest_group_share": int(smallest_share),
                **dict(ranked_group_query_extras),
            }
        )
        annotation_labels = (*largest_labels, *smallest_labels)
    elif str(query_id) == "known_part_to_group_count":
        if known_part_category is None:
            raise ValueError("known part category was not constructed")
        selected_categories = tuple(known_part_selected)
        selected = tuple(str(category.label) for category in selected_categories)
        selected_share = int(sum(int(category.value) for category in selected_categories))
        inferred_total_count = int(known_part_query_extras["inferred_total_count"])
        answer_value = _count_from_share(int(inferred_total_count), int(selected_share))
        extras.update(
            {
                "category_list": [str(label) for label in selected],
                "selected_share_value": int(selected_share),
                "known_part_sampling_attempt": int(known_part_sampling_attempt or 0),
                **dict(known_part_query_extras),
            }
        )
        annotation_labels = ("__known_count__", str(known_part_category.label), *tuple(str(label) for label in selected))
    elif str(query_id) == "cumulative_share_threshold_count":
        selected_categories = tuple(cumulative_selected)
        selected = tuple(str(category.label) for category in selected_categories)
        answer_value = int(len(selected_categories))
        extras.update(
            {
                "category_list": [str(label) for label in selected],
                "cumulative_sampling_attempt": int(cumulative_sampling_attempt or 0),
                **dict(cumulative_query_extras),
            }
        )
        annotation_labels = tuple(str(label) for label in selected)
    elif str(query_id) in TRANSFER_GAP_QUERY_IDS:
        if transfer_query is None:
            raise ValueError("transfer query was not constructed")
        source = transfer_query.source
        target = transfer_query.target
        delta = int(transfer_query.delta)
        source_new = int(source.value) - int(delta)
        target_new = int(target.value) + int(delta)
        answer_value = abs(int(target_new) - int(source_new))
        extras.update(
            {
                "source_category": str(source.label),
                "target_category": str(target.label),
                "transfer_delta": int(delta),
                "source_original_value": int(source.value),
                "target_original_value": int(target.value),
                "source_new_value": int(source_new),
                "target_new_value": int(target_new),
                "transfer_sampling_attempt": int(transfer_sampling_attempt or 0),
                **dict(transfer_query.extras),
            }
        )
        annotation_labels = (str(source.label), str(target.label))
    elif str(query_id) in PART_WHOLE_QUERY_IDS:
        selected_categories = tuple(part_whole_selected)
        selected = tuple(str(category.label) for category in selected_categories)
        selected_share = int(sum(int(category.value) for category in selected_categories))
        total_count = 0
        if str(query_id) in {
            "selected_share_to_count",
            "excluded_share_to_remaining_count",
            "chart_order_share_to_count",
            "chart_order_remaining_count",
        }:
            total_count = _sample_total_count(
                params=params,
                count_params=count_params,
                instance_seed=int(instance_seed),
            )
        if str(query_id) in {"selected_share_to_count", "chart_order_share_to_count"}:
            answer_value = _count_from_share(int(total_count), int(selected_share))
            extras.update(
                {
                    "category_list": [str(label) for label in selected],
                    "selected_share_value": int(selected_share),
                    "total_count": int(total_count),
                    "part_whole_sampling_attempt": int(part_whole_sampling_attempt or 0),
                    "calculation": (
                        "sum_chart_order_category_shares_then_convert_to_total_count"
                        if str(query_id) == "chart_order_share_to_count"
                        else "sum_ranked_category_shares_then_convert_to_total_count"
                    ),
                    **dict(part_whole_query_extras),
                }
            )
            annotation_labels = tuple(str(label) for label in selected)
        elif str(query_id) == "subset_denominator_share_value":
            answer_value = int(part_whole_query_extras["subset_denominator_percent"])
            extras.update(
                {
                    "category_list": [str(label) for label in selected],
                    "selected_share_value": int(selected_share),
                    "part_whole_sampling_attempt": int(part_whole_sampling_attempt or 0),
                    **dict(part_whole_query_extras),
                }
            )
            annotation_labels = tuple(str(label) for label in selected)
        elif str(query_id) in {"excluded_share_to_remaining_count", "chart_order_remaining_count"}:
            remaining_share = int(100 - int(selected_share))
            answer_value = _count_from_share(int(total_count), int(remaining_share))
            extras.update(
                {
                    "category_list": [str(label) for label in selected],
                    "selected_share_value": int(selected_share),
                    "remaining_share_value": int(remaining_share),
                    "total_count": int(total_count),
                    "part_whole_sampling_attempt": int(part_whole_sampling_attempt or 0),
                    "calculation": (
                        "exclude_chart_order_category_shares_then_convert_remaining_share_to_count"
                        if str(query_id) == "chart_order_remaining_count"
                        else "exclude_conditioned_category_shares_then_convert_remaining_share_to_count"
                    ),
                    **dict(part_whole_query_extras),
                }
            )
            if str(query_id) == "chart_order_remaining_count":
                annotation_labels = tuple(str(label) for label in selected)
            else:
                annotation_labels = (
                    "__total__",
                    str(extras["lower_reference_category"]),
                    str(extras["upper_reference_category"]),
                    *tuple(str(label) for label in selected),
                )
        elif str(query_id) == "sector_share_to_angle":
            if int(selected_share) % 5 != 0:
                raise ValueError("sector_share_to_angle requires selected share to be divisible by 5")
            answer_value = int((int(selected_share) * 360) // 100)
            extras.update(
                {
                    "category_list": [str(label) for label in selected],
                    "selected_share_value": int(selected_share),
                    "part_whole_sampling_attempt": int(part_whole_sampling_attempt or 0),
                    "calculation": "convert_circular_sector_share_to_degrees",
                    **dict(part_whole_query_extras),
                }
            )
            annotation_labels = tuple(str(label) for label in selected)
        else:
            raise ValueError(f"unsupported part-whole variant: {query_id}")
    else:
        raise ValueError(f"unsupported query_id: {query_id}")

    extras["answer_value"] = int(answer_value)
    extras["annotation_labels"] = [str(label) for label in annotation_labels]
    extras["annotation_values"] = [
        _annotation_value_for_label(str(label), extras=extras, values_by_label=values_by_label)
        for label in annotation_labels
    ]
    return _Dataset(
        categories=tuple(categories),
        answer_value=int(answer_value),
        annotation_labels=tuple(str(label) for label in annotation_labels),
        trace_extras=dict(extras),
    )
