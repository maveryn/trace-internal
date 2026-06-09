"""Dataset builders for labeled chart task families."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import hash64, spawn_rng
from ...shared.color_distance import (
    sample_color_palette_with_distance_constraints,
    sample_color_with_distance_constraints,
)
from ...shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.named_colors import darken_color
from ...shared.render_variation import apply_layout_jitter_to_margins
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from .chart_scene import (
    ChartMarkSpec,
    ChartRenderParams,
    RenderedChartScene,
    SUPPORTED_CHART_SCENE_VARIANTS,
    resolve_chart_render_params,
)
from .label_assets import resolve_chart_compact_axis_labels

from .labeled_chart_core import (
    StatisticKind,
    SceneVariant,
    SUPPORTED_LABELED_CHART_SCENE_VARIANTS,
    PIE_LIKE_SCENE_VARIANTS,
    LabeledChartDefaults,
    is_pie_like_scene_variant,
    sorted_labels,
    projected_mark_annotation,
    resolve_value_bounds,
    resolve_mark_count_bounds,
    apply_scene_variant_mark_count_cap,
    resolve_target_answer_range,
    balanced_choice_from_values,
    hashed_choice_from_values,
    shuffle_values,
    sample_chart_labels,
    normalize_rgb,
    build_chart_mark_specs,
    resolve_chart_mark_colors,
    max_symmetric_delta,
    cyclic_pair_deltas,
    resolve_chart_axis_variant,
)


def sample_composition_with_sum(
    rng,
    *,
    target_sum: int,
    count: int,
    value_min: int,
    value_max: int,
) -> List[int]:
    """Sample one bounded integer composition with sum preserved exactly."""

    if int(count) <= 0:
        raise ValueError("composition count must be positive")
    if int(target_sum) < int(count) * int(value_min) or int(target_sum) > int(count) * int(value_max):
        raise ValueError("target_sum outside feasible support for bounded composition")

    values = [int(value_min)] * int(count)
    remaining = int(target_sum) - (int(count) * int(value_min))
    max_increment = int(value_max) - int(value_min)
    for index in range(int(count)):
        remaining_slots = int(count) - int(index) - 1
        max_possible_for_rest = int(remaining_slots) * int(max_increment)
        add_min = max(0, int(remaining) - int(max_possible_for_rest))
        add_max = min(int(max_increment), int(remaining))
        add_value = int(remaining) if int(index) == int(count) - 1 else int(rng.randint(int(add_min), int(add_max)))
        values[int(index)] += int(add_value)
        remaining -= int(add_value)
    if int(sum(values)) != int(target_sum):
        raise RuntimeError("bounded composition drifted from requested sum")
    return [int(value) for value in values]

def sample_percentage_composition(
    *,
    count: int,
    instance_seed: int,
    namespace: str,
) -> List[int]:
    """Sample one positive-integer percentage composition that sums to 100."""

    composition_rng = spawn_rng(int(instance_seed), str(namespace))
    values = sample_composition_with_sum(
        composition_rng,
        target_sum=100,
        count=int(count),
        value_min=1,
        value_max=100,
    )
    composition_rng.shuffle(values)
    return [int(value) for value in values]

def build_values_for_median(
    target_answer: int,
    *,
    count: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
) -> List[int]:
    """Construct values with unique median equal to `target_answer`."""

    if int(count) % 2 == 0:
        raise ValueError("median construction requires an odd mark count")
    pair_count = (int(count) - 1) // 2
    max_delta = max_symmetric_delta(int(target_answer), value_min=int(value_min), value_max=int(value_max))
    deltas = cyclic_pair_deltas(pair_count=int(pair_count), max_delta=int(max_delta))
    values: List[int] = [int(target_answer)]
    for delta in deltas:
        values.append(int(target_answer) - int(delta))
        values.append(int(target_answer) + int(delta))
    if len(values) != int(count):
        raise RuntimeError("median construction produced the wrong number of values")
    if sorted(values)[len(values) // 2] != int(target_answer):
        raise RuntimeError("median construction does not preserve requested median")
    return shuffle_values(values, instance_seed=int(instance_seed), namespace="charts.value_order.median")

def build_values_for_nth_rank(
    target_answer: int,
    *,
    count: int,
    rank_n: int,
    direction: str,
    value_min: int,
    value_max: int,
    instance_seed: int,
) -> List[int]:
    """Construct values where `target_answer` is the unique nth distinct ranked value."""

    if int(rank_n) < 2:
        raise ValueError("rank_n must be at least 2")
    if int(count) < int(rank_n):
        raise ValueError("count must be at least rank_n")
    rng = spawn_rng(int(instance_seed), f"charts.values.nth_rank:{str(direction)}:{int(rank_n)}:{int(target_answer)}")
    if str(direction) == "highest":
        above_candidates = [int(value) for value in range(int(target_answer) + 1, int(value_max) + 1)]
        if len(above_candidates) < int(rank_n) - 1:
            raise ValueError("not enough distinct values above target_answer for nth-highest construction")
        ranked_values = [int(value) for value in rng.sample(above_candidates, k=int(rank_n) - 1)]
        fill_pool = ranked_values + [int(value) for value in range(int(value_min), int(target_answer))]
    elif str(direction) == "lowest":
        below_candidates = [int(value) for value in range(int(value_min), int(target_answer))]
        if len(below_candidates) < int(rank_n) - 1:
            raise ValueError("not enough distinct values below target_answer for nth-lowest construction")
        ranked_values = [int(value) for value in rng.sample(below_candidates, k=int(rank_n) - 1)]
        fill_pool = ranked_values + [int(value) for value in range(int(target_answer) + 1, int(value_max) + 1)]
    else:
        raise ValueError(f"unsupported rank direction: {direction}")
    if not fill_pool and int(count) > int(rank_n):
        raise ValueError("rank construction has no non-target fill values")
    values = [int(value) for value in ranked_values] + [int(target_answer)]
    while len(values) < int(count):
        values.append(int(fill_pool[int(rng.randint(0, len(fill_pool) - 1))]))
    rng.shuffle(values)
    if values.count(int(target_answer)) != 1:
        raise RuntimeError("rank construction must keep target_answer unique")
    return [int(value) for value in values]

def choose_rank_n(
    feasible_ranks: Sequence[int],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> int:
    """Choose one feasible order-statistic rank deterministically."""

    values = [int(value) for value in feasible_ranks]
    if not values:
        raise ValueError(f"no feasible ranks for {namespace}")
    explicit_rank = params.get("rank_n")
    if explicit_rank is not None:
        selected = int(explicit_rank)
        if int(selected) not in set(values):
            raise ValueError("explicit rank_n is outside feasible support")
        return int(selected)
    selection_index = abs(int(hash64(int(instance_seed), str(namespace), 0)))
    return int(values[int(selection_index) % len(values)])

def choose_mark_count(
    feasible_counts: Sequence[int],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> int:
    """Choose one feasible mark count deterministically."""

    values = [int(value) for value in feasible_counts]
    if not values:
        raise ValueError(f"no feasible mark counts for {namespace}")
    explicit_count = params.get("mark_count")
    if explicit_count is not None:
        selected = int(explicit_count)
        if int(selected) not in set(values):
            raise ValueError("explicit mark_count is outside feasible support")
        return int(selected)
    return balanced_choice_from_values(values, params=params, instance_seed=int(instance_seed), namespace=str(namespace))

def _sample_int_values(
    rng,
    *,
    count: int,
    min_value: int,
    max_value: int,
) -> List[int]:
    """Sample integer values uniformly from one inclusive range."""

    if int(count) < 0:
        raise ValueError("count must be non-negative")
    if int(min_value) > int(max_value):
        raise ValueError("min_value must be <= max_value")
    return [int(rng.randint(int(min_value), int(max_value))) for _ in range(int(count))]

def _sample_values_from_pool(
    rng,
    *,
    count: int,
    pool: Sequence[int],
) -> List[int]:
    """Sample integer values uniformly with replacement from one explicit pool."""

    values = [int(value) for value in pool]
    if not values:
        raise ValueError("pool must not be empty")
    return [int(values[rng.randint(0, len(values) - 1)]) for _ in range(int(count))]

def summarize_statistic_from_values(
    *,
    statistic_kind: StatisticKind,
    labels: Sequence[str],
    values: Sequence[int],
    rank_n: int | None = None,
) -> Tuple[int, List[str], Dict[str, Any]]:
    """Resolve the statistic answer and supporting labels from one labeled value list."""

    resolved_labels = [str(label) for label in labels]
    resolved_values = [int(value) for value in values]
    if len(resolved_labels) != len(resolved_values):
        raise ValueError("labels and values must have the same length")

    marks = {str(label): int(value) for label, value in zip(resolved_labels, resolved_values)}
    if str(statistic_kind) == "median":
        if int(len(resolved_values)) % 2 == 0:
            raise ValueError("median requires an odd number of values")
        sorted_pairs = sorted(((int(value), str(label)) for label, value in marks.items()), key=lambda item: (item[0], item[1]))
        median_index = len(sorted_pairs) // 2
        median_value = int(sorted_pairs[median_index][0])
        support_labels = [str(label) for label, value in marks.items() if int(value) == int(median_value)]
        if len(support_labels) != 1:
            raise ValueError("median requires one unique median label")
        return (
            int(median_value),
            [str(support_labels[0])],
            {
                "support_label": str(support_labels[0]),
                "sorted_values": [int(value) for value, _ in sorted_pairs],
            },
        )
    if str(statistic_kind) in {"nth_highest", "nth_lowest"}:
        if rank_n is None:
            raise ValueError(f"{statistic_kind} requires rank_n")
        resolved_rank = int(rank_n)
        unique_values = sorted(set(int(value) for value in resolved_values), reverse=str(statistic_kind) == "nth_highest")
        if int(resolved_rank) < 1 or int(resolved_rank) > len(unique_values):
            raise ValueError(f"rank_n outside distinct value support for {statistic_kind}")
        target_value = int(unique_values[int(resolved_rank) - 1])
        ranked_labels = [str(label) for label, value in marks.items() if int(value) == int(target_value)]
        if len(ranked_labels) != 1:
            raise ValueError(f"{statistic_kind} requires one unique ranked label")
        return (
            int(target_value),
            [str(ranked_labels[0])],
            {
                "rank_n": int(resolved_rank),
                "rank_direction": "highest" if str(statistic_kind) == "nth_highest" else "lowest",
                "ranked_label": str(ranked_labels[0]),
                "ranked_distinct_values": [int(value) for value in unique_values],
            },
        )
    raise ValueError(f"unsupported statistic_kind: {statistic_kind}")


__all__ = [
    "_sample_int_values",
    "_sample_values_from_pool",
    "build_values_for_median",
    "build_values_for_nth_rank",
    "choose_mark_count",
    "choose_rank_n",
    "sample_composition_with_sum",
    "sample_percentage_composition",
    "summarize_statistic_from_values",
]
