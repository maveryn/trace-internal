"""Dataset construction for active part-whole composition tasks."""

from __future__ import annotations

import colorsys
import itertools
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from ....shared.config_defaults import group_default
from ...shared.label_assets import resolve_chart_category_labels
from ...shared.labeled_chart_common import sample_composition_with_sum
from .share_arithmetic_common import (
    ADJACENT_TRANSFER_GAP_QUERY_ID,
    CHART_ORDER_SHARE_TO_COUNT_QUERY_ID,
    CIRCULAR_ORDER_DIRECTIONS,
    CONTIGUOUS_CHART_ORDER_SUM_QUERY_ID,
    GEN_DEFAULTS,
    PART_WHOLE_QUERY_IDS,
    POSITIONAL_RELATIONS,
    POSITIONAL_SEGMENT_SHARE_SUM_QUERY_ID,
    SAMPLING_NAMESPACE,
    SECTOR_SHARE_TO_ANGLE_QUERY_ID,
    SUBSET_DENOMINATOR_SHARE_VALUE_QUERY_ID,
    TRANSFER_GAP_QUERY_IDS,
    CategorySpec,
    PartWholeDataset,
    TransferQuery,
    balanced_int,
    category_count_bounds,
    configured_int_values,
    format_offset_list,
    format_quoted,
    params_with_shifted_sample_cursor,
    resolve_count_bounds,
    scene_axis_stride,
    value_bounds,
)


def _palette(count: int, *, instance_seed: int) -> Tuple[Tuple[int, int, int], ...]:
    colors: List[Tuple[int, int, int]] = []
    for index in range(int(count)):
        hue = (0.08 + (float(index) * 0.61803398875)) % 1.0
        lightness = 0.50 + (0.08 if int(index) % 2 else 0.0)
        saturation = 0.64
        red, green, blue = colorsys.hls_to_rgb(float(hue), float(lightness), float(saturation))
        colors.append((int(round(red * 255)), int(round(green * 255)), int(round(blue * 255))))
    rng = spawn_rng(int(instance_seed), f"{SAMPLING_NAMESPACE}.palette")
    rng.shuffle(colors)
    return tuple((int(red), int(green), int(blue)) for red, green, blue in colors[: int(count)])


def _sample_categories(
    *,
    category_count: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
) -> Tuple[CategorySpec, ...]:
    rng = spawn_rng(int(instance_seed), f"{SAMPLING_NAMESPACE}.categories")
    labels = list(
        resolve_chart_category_labels(
            rng,
            count=int(category_count),
            min_chars=2,
            max_chars=8,
            allow_spaces=False,
        ).labels
    )
    value_rng = spawn_rng(int(instance_seed), f"{SAMPLING_NAMESPACE}.values")
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
        CategorySpec(label=str(label), value=int(value), color_rgb=tuple(colors[index]))
        for index, (label, value) in enumerate(zip(labels, values))
    )


def _sample_categories_from_values(
    values: Sequence[int],
    *,
    instance_seed: int,
    namespace_suffix: str,
) -> Tuple[CategorySpec, ...]:
    rng = spawn_rng(int(instance_seed), f"{SAMPLING_NAMESPACE}.{namespace_suffix}.categories")
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
        CategorySpec(label=str(label), value=int(value), color_rgb=tuple(colors[index]))
        for index, (label, value) in enumerate(zip(labels, values))
    )


def _resolve_transfer_delta_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    return resolve_count_bounds(
        params,
        min_key="counterfactual_transfer_delta_min",
        max_key="counterfactual_transfer_delta_max",
        fallback_min=3,
        fallback_max=10,
    )


def _sample_chart_order_adjacent_transfer(
    categories: Sequence[CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> TransferQuery | None:
    delta_min, delta_max = _resolve_transfer_delta_bounds(params)
    options: List[Tuple[str, CategorySpec, CategorySpec, int, int, int]] = []
    for source_index, source in enumerate(categories):
        for direction in CIRCULAR_ORDER_DIRECTIONS:
            step = 1 if str(direction) == "clockwise" else -1
            target_index = (int(source_index) + int(step)) % len(categories)
            target = categories[int(target_index)]
            for delta in range(int(delta_min), int(delta_max) + 1):
                if int(source.value) - int(delta) >= 1:
                    options.append((str(direction), source, target, int(source_index), int(target_index), int(delta)))
    if not options:
        return None
    feasible_deltas = sorted({int(option[5]) for option in options})
    delta = balanced_int(
        feasible_deltas,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{SAMPLING_NAMESPACE}.chart_order_adjacent_transfer_delta",
    )
    candidates = [option for option in options if int(option[5]) == int(delta)]
    direction_index = balanced_int(
        range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{SAMPLING_NAMESPACE}.chart_order_adjacent_transfer_direction",
    )
    direction = str(CIRCULAR_ORDER_DIRECTIONS[int(direction_index)])
    direction_candidates = [option for option in candidates if str(option[0]) == str(direction)]
    if not direction_candidates:
        direction_candidates = candidates
    option_index = balanced_int(
        range(0, len(direction_candidates)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{SAMPLING_NAMESPACE}.chart_order_adjacent_transfer_source",
    )
    direction, source, target, source_index, target_index, delta = direction_candidates[int(option_index)]
    return TransferQuery(
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
    category_count: int,
    value_min: int,
    value_max: int,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[CategorySpec, ...], TransferQuery, int]:
    for attempt in range(160):
        categories = _sample_categories(
            category_count=int(category_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed) + (int(attempt) * 1009),
        )
        query = _sample_chart_order_adjacent_transfer(
            categories,
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed) + int(attempt),
        )
        if query is not None:
            return tuple(categories), query, int(attempt)
    raise ValueError("could not construct adjacent transfer-gap query")


def _sample_total_count(
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> int:
    configured = params.get("part_whole_total_values", group_default(GEN_DEFAULTS, "part_whole_total_values", None))
    if configured is None:
        configured = (600, 800, 1000, 1200, 1500, 1800, 2000, 2400, 3000)
    values = [int(value) for value in configured]
    if not values or any(int(value) <= 0 for value in values):
        raise ValueError("part_whole_total_values must contain positive integers")
    if any(int(value) % 100 != 0 for value in values):
        raise ValueError("part_whole_total_values must be multiples of 100 so count answers are integral")
    return balanced_int(
        values,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{SAMPLING_NAMESPACE}.part_whole_total_count",
    )


def _count_from_share(total_count: int, share_value: int) -> int:
    return int((int(total_count) * int(share_value)) // 100)


def _build_sector_share_to_angle_query(
    categories: Sequence[CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[CategorySpec, ...], Dict[str, Any]] | None:
    span_min, span_max = resolve_count_bounds(
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
    direction_index = balanced_int(
        range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{SAMPLING_NAMESPACE}.part_whole_angle_order_direction",
    )
    order_direction = str(CIRCULAR_ORDER_DIRECTIONS[int(direction_index)])
    step = 1 if str(order_direction) == "clockwise" else -1
    options: List[Tuple[int, int, Tuple[int, ...], int]] = []
    for span_count in range(int(feasible_span_min), int(feasible_span_max) + 1):
        for start_index in range(0, len(categories)):
            selected_indices = tuple((int(start_index) + (int(step) * int(offset))) % len(categories) for offset in range(int(span_count)))
            selected_share = int(sum(int(categories[int(index)].value) for index in selected_indices))
            if int(selected_share) % 5 == 0:
                options.append((int(span_count), int(start_index), tuple(int(index) for index in selected_indices), int(selected_share)))
    if not options:
        return None
    option_index = balanced_int(
        range(0, len(options)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{SAMPLING_NAMESPACE}.part_whole_angle_span",
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
    categories: Sequence[CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[CategorySpec, ...], Dict[str, Any]]:
    span_min, span_max = resolve_count_bounds(
        params,
        min_key="part_whole_span_count_min",
        max_key="part_whole_span_count_max",
        fallback_min=3,
        fallback_max=5,
    )
    feasible_span_min = max(2, int(span_min))
    feasible_span_max = min(int(span_max), len(categories) - 1)
    if int(feasible_span_min) > int(feasible_span_max):
        raise ValueError("chart_order_share_to_count requires enough categories for a non-full chart-order span")
    span_count = balanced_int(
        range(int(feasible_span_min), int(feasible_span_max) + 1),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{SAMPLING_NAMESPACE}.chart_order_share_to_count.span_count",
    )
    direction_index = balanced_int(
        range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{SAMPLING_NAMESPACE}.chart_order_share_to_count.order_direction",
    )
    order_direction = str(CIRCULAR_ORDER_DIRECTIONS[int(direction_index)])
    start_index = balanced_int(
        range(0, len(categories)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{SAMPLING_NAMESPACE}.chart_order_share_to_count.start_index",
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
) -> Tuple[Tuple[CategorySpec, ...], Tuple[CategorySpec, ...], Dict[str, Any], int]:
    subset_min, subset_max = resolve_count_bounds(
        params,
        min_key="subset_denominator_size_min",
        max_key="subset_denominator_size_max",
        fallback_min=2,
        fallback_max=4,
    )
    subset_sizes = list(range(max(2, int(subset_min)), min(int(subset_max), int(category_count) - 1) + 1))
    if not subset_sizes:
        raise ValueError("subset_denominator_share_value requires at least one non-full subset")
    answer_values = configured_int_values(
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
                feasible.append((int(answer_percent), int(subset_size), int(subset_total), int(target_value), int(outside_total)))
    if not feasible:
        raise ValueError("could not construct subset-denominator share values with configured bounds")

    available_answers = sorted({int(item[0]) for item in feasible})
    answer_percent = balanced_int(
        available_answers,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{SAMPLING_NAMESPACE}.subset_denominator.answer_percent",
    )
    answer_candidates = [item for item in feasible if int(item[0]) == int(answer_percent)]
    available_subset_sizes = sorted({int(item[1]) for item in answer_candidates})
    subset_size = balanced_int(
        available_subset_sizes,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{SAMPLING_NAMESPACE}.subset_denominator.subset_size",
    )
    size_candidates = [item for item in answer_candidates if int(item[1]) == int(subset_size)]
    available_subset_totals = sorted({int(item[2]) for item in size_candidates})
    subset_total = balanced_int(
        available_subset_totals,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{SAMPLING_NAMESPACE}.subset_denominator.subset_total",
    )
    target_value = int(int(subset_total) * int(answer_percent) // 100)
    outside_total = int(100 - int(subset_total))
    subset_remainder = int(subset_total) - int(target_value)
    outside_count = int(category_count) - int(subset_size)

    subset_rng = spawn_rng(int(instance_seed), f"{SAMPLING_NAMESPACE}.subset_denominator.subset_rest")
    outside_rng = spawn_rng(int(instance_seed), f"{SAMPLING_NAMESPACE}.subset_denominator.outside")
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
    layout_rng = spawn_rng(int(instance_seed), f"{SAMPLING_NAMESPACE}.subset_denominator.layout")
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
        "subset_category_list_text": format_quoted([str(category.label) for category in selected]),
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
) -> Tuple[Tuple[CategorySpec, ...], Tuple[CategorySpec, ...], Dict[str, Any], int]:
    for attempt in range(160):
        categories = _sample_categories(
            category_count=int(category_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed) + (int(attempt) * 1009),
        )
        if str(query_id) == CHART_ORDER_SHARE_TO_COUNT_QUERY_ID:
            selected, query_extras = _build_chart_order_span_query(
                categories,
                params=params,
                count_params=count_params,
                instance_seed=int(instance_seed) + int(attempt),
            )
            return tuple(categories), tuple(selected), dict(query_extras), int(attempt)
        if str(query_id) == SUBSET_DENOMINATOR_SHARE_VALUE_QUERY_ID:
            return _sample_subset_denominator_categories_and_query(
                category_count=int(category_count),
                value_min=int(value_min),
                value_max=int(value_max),
                params=params,
                count_params=count_params,
                instance_seed=int(instance_seed) + int(attempt),
            )
        if str(query_id) == SECTOR_SHARE_TO_ANGLE_QUERY_ID:
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


def annotation_value_for_label(
    label: str,
    *,
    extras: Mapping[str, Any],
    values_by_label: Mapping[str, int],
) -> int:
    if str(label) == "__total__":
        return int(extras["total_count"])
    return int(values_by_label[str(label)])


def public_annotation_key(label: str) -> str:
    if str(label) == "__total__":
        return "total_count"
    return str(label)


def build_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> PartWholeDataset:
    category_min, category_max = category_count_bounds(params, query_id=str(query_id))
    count_params = params_with_shifted_sample_cursor(params, divisor=scene_axis_stride(params))
    category_count_support = list(range(int(category_min), int(category_max) + 1))
    if str(query_id) == POSITIONAL_SEGMENT_SHARE_SUM_QUERY_ID:
        category_count_support = [int(value) for value in category_count_support if int(value) % 2 == 0]
        if not category_count_support:
            raise ValueError("positional_segment_share_sum requires at least one even category count")
    category_count = balanced_int(
        category_count_support,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{SAMPLING_NAMESPACE}.category_count",
    )
    value_min, value_max = value_bounds(params, query_id=str(query_id))
    transfer_query: TransferQuery | None = None
    transfer_sampling_attempt: int | None = None
    part_whole_selected: Tuple[CategorySpec, ...] = ()
    part_whole_query_extras: Dict[str, Any] = {}
    part_whole_sampling_attempt: int | None = None

    if str(query_id) in TRANSFER_GAP_QUERY_IDS:
        categories, transfer_query, transfer_sampling_attempt = _sample_transfer_categories_and_query(
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
    else:
        categories = _sample_categories(
            category_count=int(category_count),
            value_min=int(value_min),
            value_max=int(value_max),
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

    if str(query_id) == CONTIGUOUS_CHART_ORDER_SUM_QUERY_ID:
        span_min, span_max = resolve_count_bounds(
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
        span_count = balanced_int(
            range(int(feasible_span_min), int(feasible_span_max) + 1),
            params=count_params,
            instance_seed=int(instance_seed),
            namespace=f"{SAMPLING_NAMESPACE}.contiguous_span_count",
        )
        direction_index = balanced_int(
            range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
            params=count_params,
            instance_seed=int(instance_seed),
            namespace=f"{SAMPLING_NAMESPACE}.contiguous_order_direction",
        )
        order_direction = str(CIRCULAR_ORDER_DIRECTIONS[int(direction_index)])
        start_index = balanced_int(
            range(0, int(category_count)),
            params=count_params,
            instance_seed=int(instance_seed),
            namespace=f"{SAMPLING_NAMESPACE}.contiguous_start_index",
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
    elif str(query_id) == POSITIONAL_SEGMENT_SHARE_SUM_QUERY_ID:
        relation_index = balanced_int(
            range(0, len(POSITIONAL_RELATIONS)),
            params=count_params,
            instance_seed=int(instance_seed),
            namespace=f"{SAMPLING_NAMESPACE}.positional_relation",
        )
        position_relation = str(POSITIONAL_RELATIONS[int(relation_index)])
        relation_seed = int(instance_seed) + (int(relation_index) * 10007)
        relation_rng = spawn_rng(int(relation_seed), f"{SAMPLING_NAMESPACE}.positional.{position_relation}")
        annotation_prefix: Tuple[str, ...] = ()
        if position_relation == "anchor_offset_sum":
            anchor_index = int(relation_rng.randrange(0, int(category_count)))
            anchor_label = str(categories[int(anchor_index)].label)
            direction_index = balanced_int(
                range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
                params=count_params,
                instance_seed=int(instance_seed),
                namespace=f"{SAMPLING_NAMESPACE}.positional.anchor_direction",
            )
            order_direction = str(CIRCULAR_ORDER_DIRECTIONS[int(direction_index)])
            feasible_offsets = [
                offsets
                for offsets in itertools.combinations(range(1, int(category_count)), 2)
                if int(offsets[1]) - int(offsets[0]) >= 2
            ]
            offset_index = balanced_int(
                range(0, len(feasible_offsets)),
                params=count_params,
                instance_seed=int(instance_seed),
                namespace=f"{SAMPLING_NAMESPACE}.positional.anchor_offsets",
            )
            selected_offsets = tuple(int(offset) for offset in feasible_offsets[int(offset_index)])
            step = 1 if str(order_direction) == "clockwise" else -1
            selected_indices = tuple((int(anchor_index) + (int(step) * int(offset))) % int(category_count) for offset in selected_offsets)
            selected_categories = tuple(categories[int(index)] for index in selected_indices)
            selected = tuple(str(category.label) for category in selected_categories)
            annotation_prefix = (str(anchor_label),)
            positional_instruction = (
                f"Starting at category \"{anchor_label}\" and moving {order_direction}, use the segments "
                f"{format_offset_list(selected_offsets)} away from that anchor. Do not include category \"{anchor_label}\"."
            )
            extras.update(
                {
                    "anchor_category": str(anchor_label),
                    "anchor_index": int(anchor_index),
                    "selected_offsets": [int(offset) for offset in selected_offsets],
                    "offset_list_text": format_offset_list(selected_offsets),
                    "offset_index": int(offset_index),
                }
            )
        elif position_relation == "opposite_neighbor_sum":
            anchor_index = int(relation_rng.randrange(0, int(category_count)))
            anchor_label = str(categories[int(anchor_index)].label)
            direction_index = balanced_int(
                range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
                params=count_params,
                instance_seed=int(instance_seed),
                namespace=f"{SAMPLING_NAMESPACE}.positional.opposite_direction",
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
        if str(query_id) == CHART_ORDER_SHARE_TO_COUNT_QUERY_ID:
            total_count = _sample_total_count(
                params=params,
                count_params=count_params,
                instance_seed=int(instance_seed),
            )
            answer_value = _count_from_share(int(total_count), int(selected_share))
            extras.update(
                {
                    "category_list": [str(label) for label in selected],
                    "selected_share_value": int(selected_share),
                    "total_count": int(total_count),
                    "part_whole_sampling_attempt": int(part_whole_sampling_attempt or 0),
                    "calculation": "sum_chart_order_category_shares_then_convert_to_total_count",
                    **dict(part_whole_query_extras),
                }
            )
            annotation_labels = tuple(str(label) for label in selected)
        elif str(query_id) == SUBSET_DENOMINATOR_SHARE_VALUE_QUERY_ID:
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
        elif str(query_id) == SECTOR_SHARE_TO_ANGLE_QUERY_ID:
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
            raise ValueError(f"unsupported part-whole query: {query_id}")
    else:
        raise ValueError(f"unsupported query_id: {query_id}")

    extras["answer_value"] = int(answer_value)
    extras["annotation_labels"] = [str(label) for label in annotation_labels]
    extras["annotation_values"] = [
        annotation_value_for_label(str(label), extras=extras, values_by_label=values_by_label)
        for label in annotation_labels
    ]
    return PartWholeDataset(
        categories=tuple(categories),
        answer_value=int(answer_value),
        annotation_labels=tuple(str(label) for label in annotation_labels),
        trace_extras=dict(extras),
    )


__all__ = ["annotation_value_for_label", "build_dataset", "public_annotation_key"]
