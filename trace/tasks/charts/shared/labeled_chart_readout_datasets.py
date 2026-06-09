"""Two-label readout dataset builders for labeled charts."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from ....core.seed import spawn_rng
from .labeled_chart_core import (
    LabeledChartDefaults,
    SceneVariant,
    apply_scene_variant_mark_count_cap,
    balanced_choice_from_values,
    is_pie_like_scene_variant,
    max_symmetric_delta,
    resolve_mark_count_bounds,
    resolve_value_bounds,
    sample_chart_labels,
)
from .labeled_chart_dataset_core import (
    _sample_int_values,
    choose_mark_count,
    sample_composition_with_sum,
)

def _default_readout_answer_range(
    readout_variant: str,
    *,
    value_min: int,
    value_max: int,
) -> Tuple[int, int]:
    """Return the default target-answer support for one two-label readout variant."""

    if str(readout_variant) == "sum_two":
        return int(2 * int(value_min)), int(2 * int(value_max))
    if str(readout_variant) == "difference_two_abs":
        return 0, int(value_max) - int(value_min)
    if str(readout_variant) in {"max_two", "min_two", "mean_two"}:
        return int(value_min), int(value_max)
    raise ValueError(f"unsupported readout_variant: {readout_variant}")

def _default_pie_readout_answer_range(readout_variant: str) -> Tuple[int, int]:
    """Return conservative default answer support for two-slice percentage readout."""

    if str(readout_variant) == "sum_two":
        return 2, 94
    if str(readout_variant) == "difference_two_abs":
        return 0, 90
    if str(readout_variant) == "max_two":
        return 1, 91
    if str(readout_variant) in {"min_two", "mean_two"}:
        return 1, 47
    raise ValueError(f"unsupported readout_variant: {readout_variant}")

def _build_query_pair_for_readout(
    readout_variant: str,
    *,
    target_answer: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
    namespace: str,
) -> List[int]:
    """Construct the ordered queried values for one two-label readout variant."""

    rng = spawn_rng(int(instance_seed), str(namespace))
    if str(readout_variant) == "sum_two":
        low = max(int(value_min), int(target_answer) - int(value_max))
        high = min(int(value_max), int(target_answer) - int(value_min))
        if int(low) > int(high):
            raise ValueError("sum_two target is outside feasible pair support")
        first = int(rng.randint(int(low), int(high)))
        second = int(target_answer) - int(first)
        values = [int(first), int(second)]
    elif str(readout_variant) == "difference_two_abs":
        if int(target_answer) < 0 or int(target_answer) > int(value_max) - int(value_min):
            raise ValueError("difference_two_abs target is outside feasible support")
        if int(target_answer) == 0:
            repeated = int(rng.randint(int(value_min), int(value_max)))
            values = [int(repeated), int(repeated)]
        else:
            low = int(rng.randint(int(value_min), int(value_max) - int(target_answer)))
            high = int(low) + int(target_answer)
            values = [int(low), int(high)]
    elif str(readout_variant) == "max_two":
        if int(target_answer) < int(value_min) or int(target_answer) > int(value_max):
            raise ValueError("max_two target is outside feasible support")
        other = int(rng.randint(int(value_min), int(target_answer)))
        values = [int(target_answer), int(other)]
    elif str(readout_variant) == "min_two":
        if int(target_answer) < int(value_min) or int(target_answer) > int(value_max):
            raise ValueError("min_two target is outside feasible support")
        other = int(rng.randint(int(target_answer), int(value_max)))
        values = [int(target_answer), int(other)]
    elif str(readout_variant) == "mean_two":
        if int(target_answer) < int(value_min) or int(target_answer) > int(value_max):
            raise ValueError("mean_two target is outside feasible support")
        max_delta = max_symmetric_delta(int(target_answer), value_min=int(value_min), value_max=int(value_max))
        delta = int(rng.randint(0, int(max_delta)))
        values = [int(target_answer) - int(delta), int(target_answer) + int(delta)]
    else:
        raise ValueError(f"unsupported readout_variant: {readout_variant}")
    if int(rng.randint(0, 1)) == 1:
        values = [int(values[1]), int(values[0])]
    return [int(value) for value in values]

def _build_pie_query_pair_for_readout(
    readout_variant: str,
    *,
    target_answer: int,
    mark_count: int,
    instance_seed: int,
    namespace: str,
) -> List[int]:
    """Construct the ordered queried percentages for one two-slice readout variant."""

    remaining_slots = int(mark_count) - 2
    if int(remaining_slots) < 0:
        raise ValueError("pie readout requires at least two marks")
    max_pair_sum = 100 - int(remaining_slots)
    rng = spawn_rng(int(instance_seed), str(namespace))

    if str(readout_variant) == "sum_two":
        if int(target_answer) < 2 or int(target_answer) > int(max_pair_sum):
            raise ValueError("sum_two target is outside feasible pie support")
        first = int(rng.randint(1, int(target_answer) - 1))
        second = int(target_answer) - int(first)
        values = [int(first), int(second)]
    elif str(readout_variant) == "difference_two_abs":
        if int(target_answer) < 0 or int(target_answer) > int(max_pair_sum) - 2:
            raise ValueError("difference_two_abs target is outside feasible pie support")
        if int(target_answer) == 0:
            repeated_max = int(max_pair_sum // 2)
            repeated = int(rng.randint(1, int(repeated_max)))
            values = [int(repeated), int(repeated)]
        else:
            low_max = int((int(max_pair_sum) - int(target_answer)) // 2)
            low = int(rng.randint(1, int(low_max)))
            values = [int(low), int(low) + int(target_answer)]
    elif str(readout_variant) == "max_two":
        if int(target_answer) < 1 or int(target_answer) > int(max_pair_sum) - 1:
            raise ValueError("max_two target is outside feasible pie support")
        other_high = int(min(int(target_answer), int(max_pair_sum) - int(target_answer)))
        other = int(rng.randint(1, int(other_high)))
        values = [int(target_answer), int(other)]
    elif str(readout_variant) == "min_two":
        if int(target_answer) < 1:
            raise ValueError("min_two target is outside feasible pie support")
        other_high = int(max_pair_sum) - int(target_answer)
        if int(other_high) < int(target_answer):
            raise ValueError("min_two target is outside feasible pie support")
        other = int(rng.randint(int(target_answer), int(other_high)))
        values = [int(target_answer), int(other)]
    elif str(readout_variant) == "mean_two":
        if int(target_answer) < 1 or (2 * int(target_answer)) > int(max_pair_sum):
            raise ValueError("mean_two target is outside feasible pie support")
        max_delta = int(target_answer) - 1
        delta = int(rng.randint(0, int(max_delta)))
        values = [int(target_answer) - int(delta), int(target_answer) + int(delta)]
    else:
        raise ValueError(f"unsupported readout_variant: {readout_variant}")

    if int(rng.randint(0, 1)) == 1:
        values = [int(values[1]), int(values[0])]
    return [int(value) for value in values]

def build_value_readout_dataset_for_variant(
    *,
    readout_variant: str,
    scene_variant: SceneVariant,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: LabeledChartDefaults,
    task_id: str,
) -> Tuple[List[int], int, List[int], Dict[str, Any]]:
    """Construct one labeled chart dataset for two-label numeric readout tasks."""

    pie_like = bool(is_pie_like_scene_variant(str(scene_variant)))
    value_min, value_max = resolve_value_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
        instance_seed=int(instance_seed),
    )
    mark_count_min, mark_count_max = resolve_mark_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    mark_count_min, mark_count_max = apply_scene_variant_mark_count_cap(
        scene_variant=str(scene_variant),
        mark_count_min=int(mark_count_min),
        mark_count_max=int(mark_count_max),
    )
    if pie_like:
        default_answer_min, default_answer_max = _default_pie_readout_answer_range(str(readout_variant))
    else:
        default_answer_min, default_answer_max = _default_readout_answer_range(
            str(readout_variant),
            value_min=int(value_min),
            value_max=int(value_max),
        )
    explicit_min = params.get("target_answer_min")
    explicit_max = params.get("target_answer_max")
    supported_answer_min = int(default_answer_min if explicit_min is None else explicit_min)
    supported_answer_max = int(default_answer_max if explicit_max is None else explicit_max)
    if int(supported_answer_min) > int(supported_answer_max):
        raise ValueError("target_answer_min must be <= target_answer_max")

    answer_candidates = [
        int(value)
        for value in range(int(supported_answer_min), int(supported_answer_max) + 1)
        if int(default_answer_min) <= int(value) <= int(default_answer_max)
    ]
    if not answer_candidates:
        raise ValueError("no feasible target answers for requested readout range")
    target_answer = balanced_choice_from_values(
        answer_candidates,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_answer:{str(readout_variant)}",
    )
    feasible_counts = [int(count) for count in range(int(mark_count_min), int(mark_count_max) + 1) if int(count) >= 2]
    mark_count = choose_mark_count(
        feasible_counts,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.mark_count:{str(readout_variant)}:{int(target_answer)}",
    )
    labels = list(
        sample_chart_labels(
            count=int(mark_count),
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.labels:{str(readout_variant)}:{int(mark_count)}",
        )
    )
    query_rng = spawn_rng(int(instance_seed), f"{task_id}.query_labels:{str(readout_variant)}")
    query_indices = list(range(int(mark_count)))
    query_rng.shuffle(query_indices)
    first_index, second_index = int(query_indices[0]), int(query_indices[1])
    query_labels = [str(labels[first_index]), str(labels[second_index])]
    query_values = _build_query_pair_for_readout(
        str(readout_variant),
        target_answer=int(target_answer),
        value_min=int(value_min),
        value_max=int(value_max),
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.query_values:{str(readout_variant)}",
    ) if not pie_like else _build_pie_query_pair_for_readout(
        str(readout_variant),
        target_answer=int(target_answer),
        mark_count=int(mark_count),
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.query_values:{str(readout_variant)}:pie",
    )
    if pie_like:
        remaining_rng = spawn_rng(int(instance_seed), f"{task_id}.other_values:{str(readout_variant)}:pie")
        remaining_sum = 100 - int(sum(query_values))
        remaining_values = sample_composition_with_sum(
            remaining_rng,
            target_sum=int(remaining_sum),
            count=int(mark_count) - 2,
            value_min=1,
            value_max=100,
        )
        remaining_rng.shuffle(remaining_values)
    else:
        remaining_rng = spawn_rng(int(instance_seed), f"{task_id}.other_values:{str(readout_variant)}")
        remaining_values = _sample_int_values(
            remaining_rng,
            count=int(mark_count) - 2,
            min_value=int(value_min),
            max_value=int(value_max),
        )
    values_by_label: Dict[str, int] = {}
    remaining_iter = iter(int(value) for value in remaining_values)
    for index, label in enumerate(labels):
        if int(index) == int(first_index):
            values_by_label[str(label)] = int(query_values[0])
        elif int(index) == int(second_index):
            values_by_label[str(label)] = int(query_values[1])
        else:
            values_by_label[str(label)] = int(next(remaining_iter))
    values = [int(values_by_label[str(label)]) for label in labels]
    annotation_values = [int(values_by_label[str(label)]) for label in query_labels]

    if str(readout_variant) == "sum_two":
        answer_value = int(sum(annotation_values))
    elif str(readout_variant) == "difference_two_abs":
        answer_value = int(abs(int(annotation_values[0]) - int(annotation_values[1])))
    elif str(readout_variant) == "max_two":
        answer_value = int(max(annotation_values))
    elif str(readout_variant) == "min_two":
        answer_value = int(min(annotation_values))
    elif str(readout_variant) == "mean_two":
        total = int(sum(annotation_values))
        if int(total) % 2 != 0:
            raise RuntimeError("mean_two annotation values must sum to an even number")
        answer_value = int(total // 2)
    else:
        raise ValueError(f"unsupported readout_variant: {readout_variant}")

    if int(answer_value) != int(target_answer):
        raise RuntimeError("constructed readout dataset does not match requested answer")

    trace_extras: Dict[str, Any] = {
        "value_min": 1 if pie_like else int(value_min),
        "value_max": 99 if pie_like else int(value_max),
        **({"value_semantics": "percentage", "composition_total": 100} if pie_like else {}),
        "target_answer_range": [int(supported_answer_min), int(supported_answer_max)],
        "mark_count_range": [int(mark_count_min), int(mark_count_max)],
        "target_answer": int(target_answer),
        "mark_count": int(mark_count),
        "labels": [str(label) for label in labels],
        "values_by_label": {str(label): int(values_by_label[str(label)]) for label in labels},
        "query_labels": [str(label) for label in query_labels],
        "query_values": [int(value) for value in annotation_values],
    }
    return [int(value) for value in values], int(answer_value), [int(value) for value in annotation_values], trace_extras


__all__ = ["build_value_readout_dataset_for_variant"]
