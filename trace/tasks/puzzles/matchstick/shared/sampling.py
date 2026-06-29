"""Sampling helpers for matchstick puzzle scenes."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import (
    group_default,
    resolve_required_int_bounds,
)
from trace.tasks.shared.mcq import option_label_for_index

from .rules import (
    all_square_grid_edges,
    changed_digit_index,
    edge_signature,
    loose_endpoint_count,
    number_segment_keys,
    number_transition_allowed,
)
from .state import Edge, NumberDataset, OPTION_LABELS, OptionSpec, ShapeDataset


def resolve_option_count(
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    *,
    rng,
    force_count: int | None = None,
) -> tuple[int, tuple[int, int]]:
    """Resolve the visual answer-option count for matchstick tasks."""

    if force_count is not None:
        count = max(4, min(len(OPTION_LABELS), int(force_count)))
        return int(count), (int(count), int(count))
    if "option_count" in params:
        count = max(4, min(len(OPTION_LABELS), int(params["option_count"])))
        return int(count), (int(count), int(count))
    low, high = resolve_required_int_bounds(
        params,
        generation_defaults,
        min_key="option_count_min",
        max_key="option_count_max",
        fallback_min=4,
        fallback_max=6,
        context="matchstick option count",
    )
    low = max(4, min(len(OPTION_LABELS), int(low)))
    high = max(int(low), min(len(OPTION_LABELS), int(high)))
    return int(rng.randint(int(low), int(high))), (int(low), int(high))


def build_number_dataset(
    *,
    stick_delta: int,
    scene_variant: str,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    namespace: str,
    instance_seed: int,
) -> NumberDataset:
    """Build one source number plus six candidate transformed numbers."""

    rng = spawn_rng(int(instance_seed), f"{namespace}.number_dataset")
    option_count, _option_range = resolve_option_count(
        params,
        generation_defaults,
        rng=rng,
        force_count=6,
    )
    answer_index = int(rng.randrange(int(option_count)))

    numbers = list(range(10, 100))
    rng.shuffle(numbers)
    for source_number in numbers:
        reachable = [
            target_number
            for target_number in range(10, 100)
            if int(target_number) != int(source_number)
            and number_transition_allowed(
                int(source_number),
                int(target_number),
                stick_delta=int(stick_delta),
            )
        ]
        if not reachable:
            continue
        answer_number = int(reachable[int(rng.randrange(len(reachable)))])
        distractors = [
            target_number
            for target_number in range(10, 100)
            if int(target_number) != int(source_number)
            and int(target_number) != int(answer_number)
            and not number_transition_allowed(
                int(source_number),
                int(target_number),
                stick_delta=int(stick_delta),
            )
        ]
        rng.shuffle(distractors)
        if len(distractors) < int(option_count) - 1:
            continue
        options = [int(value) for value in distractors[: int(option_count) - 1]]
        options.insert(int(answer_index), int(answer_number))
        option_specs = tuple(
            OptionSpec(
                label=str(option_label_for_index(int(index))),
                is_correct=bool(index == int(answer_index)),
                value=int(number),
                metric_value=None,
            )
            for index, number in enumerate(options)
        )
        source_keys = number_segment_keys(int(source_number))
        answer_keys = number_segment_keys(int(answer_number))
        return NumberDataset(
            scene_variant=str(scene_variant),
            source_number=int(source_number),
            answer_number=int(answer_number),
            answer_label=str(option_label_for_index(int(answer_index))),
            option_count=int(option_count),
            option_specs=tuple(option_specs),
            changed_digit_index=int(
                changed_digit_index(int(source_number), int(answer_number))
            ),
            removed_segment_keys=tuple(sorted(source_keys - answer_keys)),
            added_segment_keys=tuple(sorted(answer_keys - source_keys)),
        )
    raise RuntimeError("failed to sample matchstick number dataset")


def _random_source_edges(
    rng,
    *,
    all_edges: Sequence[Edge],
    edge_count_min: int,
    edge_count_max: int,
) -> Tuple[Edge, ...]:
    edge_count = int(rng.randint(int(edge_count_min), int(edge_count_max)))
    edge_count = max(4, min(len(all_edges) - 2, int(edge_count)))
    chosen = rng.sample(list(all_edges), int(edge_count))
    return edge_signature(chosen)


def build_shape_dataset(
    *,
    extremum: str,
    scene_variant: str,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    namespace: str,
    instance_seed: int,
) -> ShapeDataset:
    """Build six edge arrangements and pick the unique loose-endpoint extremum."""

    rng = spawn_rng(int(instance_seed), f"{namespace}.shape_dataset")
    option_count, _option_range = resolve_option_count(
        params,
        generation_defaults,
        rng=rng,
        force_count=6,
    )
    grid_size = int(params.get("grid_size", group_default(generation_defaults, "grid_size", 3)))
    grid_size = max(2, min(4, int(grid_size)))
    all_edges = all_square_grid_edges(int(grid_size))
    edge_min, edge_max = resolve_required_int_bounds(
        params,
        generation_defaults,
        min_key="shape_edge_count_min",
        max_key="shape_edge_count_max",
        fallback_min=8,
        fallback_max=15,
        context=f"{namespace} shape edge count",
    )
    answer_index = int(rng.randrange(int(option_count)))

    for _attempt in range(500):
        sampled: Dict[Tuple[Edge, ...], int] = {}
        for _sample_index in range(180):
            candidate = _random_source_edges(
                rng,
                all_edges=all_edges,
                edge_count_min=int(edge_min),
                edge_count_max=int(edge_max),
            )
            sampled[tuple(candidate)] = loose_endpoint_count(candidate)
        if len(sampled) < int(option_count):
            continue
        metric_to_candidates: Dict[int, list[Tuple[Edge, ...]]] = defaultdict(list)
        for candidate, metric in sampled.items():
            metric_to_candidates[int(metric)].append(tuple(candidate))
        if len(metric_to_candidates) < 2:
            continue
        metrics = sorted(int(value) for value in metric_to_candidates)
        target_metric = int(metrics[-1] if str(extremum) == "max" else metrics[0])
        distractor_metrics = [
            metric for metric in metrics if int(metric) != int(target_metric)
        ]
        distractor_pool = [
            candidate
            for metric in distractor_metrics
            for candidate in metric_to_candidates[int(metric)]
        ]
        rng.shuffle(distractor_pool)
        if len(distractor_pool) < int(option_count) - 1:
            continue
        answer_candidates = metric_to_candidates[target_metric]
        answer_edges = tuple(answer_candidates[int(rng.randrange(len(answer_candidates)))])
        options = list(distractor_pool[: int(option_count) - 1])
        options.insert(int(answer_index), answer_edges)
        option_specs = tuple(
            OptionSpec(
                label=str(option_label_for_index(int(index))),
                is_correct=bool(index == int(answer_index)),
                value=tuple(edges),
                metric_value=int(loose_endpoint_count(edges)),
            )
            for index, edges in enumerate(options)
        )
        return ShapeDataset(
            scene_variant=str(scene_variant),
            answer_label=str(option_label_for_index(int(answer_index))),
            option_count=int(option_count),
            option_specs=tuple(option_specs),
            grid_size=int(grid_size),
        )
    raise RuntimeError("failed to sample matchstick endpoint-extremum dataset")


__all__ = [
    "build_number_dataset",
    "build_shape_dataset",
    "resolve_option_count",
]
