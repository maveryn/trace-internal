"""Sampling helpers for matchstick puzzle scenes."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import (
    resolve_required_int_bounds,
)
from trace.tasks.shared.mcq import option_label_for_index

from .rules import (
    changed_digit_index,
    number_segment_keys,
    number_transition_allowed,
)
from .state import NumberDataset, OPTION_LABELS, OptionSpec


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


__all__ = [
    "build_number_dataset",
    "resolve_option_count",
]
