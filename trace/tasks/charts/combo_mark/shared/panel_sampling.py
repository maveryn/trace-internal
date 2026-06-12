"""Semantic sampling and answer selection for combo-mark chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from trace.core.seed import hash64, spawn_rng
from trace.tasks.charts.shared.label_assets import (
    resolve_chart_category_labels,
    resolve_chart_compact_axis_labels,
)
from trace.tasks.charts.combo_mark.shared.panel_common import (
    ComboDataset,
    ComboScene,
    GENERATION_DEFAULTS,
    SCENE_NAMESPACE,
    choose_scene_variant,
    int_bounds,
)
from trace.tasks.shared.config_defaults import group_default


@dataclass(frozen=True)
class SelectionResult:
    answer: int | str
    answer_type: str
    annotation_points: dict[str, list[float]]
    trace: dict[str, Any]
    question_format: str


def sample_labels(rng: Any, count: int) -> tuple[str, ...]:
    labels = resolve_chart_compact_axis_labels(
        rng,
        count=int(count),
        min_chars=2,
        max_chars=3,
    ).labels
    return tuple(str(label) for label in labels)


def sample_values(rng: Any, *, count: int, low: int, high: int) -> tuple[int, ...]:
    return tuple(int(rng.randint(int(low), int(high))) for _ in range(int(count)))


def choose_metric_pair(instance_seed: int) -> tuple[str, str]:
    labels = resolve_chart_category_labels(
        spawn_rng(int(instance_seed), "charts.combo.metric_pair"),
        count=2,
        min_chars=2,
        max_chars=8,
        allow_spaces=False,
    ).labels
    return str(labels[0]), str(labels[1])


def sample_base_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    allowed_scene_variants: Sequence[str] | None = None,
    label_count_bounds: tuple[int, int] | None = None,
    scene_sampling_divisor: int = 1,
) -> tuple[ComboDataset, dict[str, Any]]:
    scene_variant, scene_probabilities, scene_params = choose_scene_variant(
        params=params,
        instance_seed=int(instance_seed),
        allowed_variants=allowed_scene_variants,
        sampling_divisor=int(scene_sampling_divisor),
    )
    fallback_bounds = label_count_bounds or (7, 11)
    label_min, label_max = int_bounds(scene_params, "label_count_min", "label_count_max", fallback_bounds)
    value_min, value_max = int_bounds(scene_params, "value_min", "value_max", (12, 88))
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.values")
    label_count = int(rng.randint(int(label_min), int(label_max)))
    labels = sample_labels(rng, label_count)
    primary_values = sample_values(rng, count=label_count, low=value_min, high=value_max)
    line_values = sample_values(rng, count=label_count, low=value_min, high=value_max)
    primary_name, line_name = choose_metric_pair(int(instance_seed))
    dataset = ComboDataset(
        labels=tuple(labels),
        primary_values=tuple(primary_values),
        line_values=tuple(line_values),
        primary_name=str(primary_name),
        line_name=str(line_name),
        scene_variant=str(scene_variant),
        label_count_range=(int(label_min), int(label_max)),
        scene_variant_probabilities=dict(scene_probabilities),
    )
    trace = {
        "label_count": int(label_count),
        "label_count_range": [int(label_min), int(label_max)],
        "value_range": [int(value_min), int(value_max)],
        "scene_variant": str(scene_variant),
        "scene_variant_probabilities": dict(scene_probabilities),
    }
    return dataset, trace


def dataset_with_values(
    dataset: ComboDataset,
    *,
    primary_values: Sequence[int] | None = None,
    line_values: Sequence[int] | None = None,
) -> ComboDataset:
    return ComboDataset(
        labels=tuple(dataset.labels),
        primary_values=tuple(int(value) for value in (primary_values if primary_values is not None else dataset.primary_values)),
        line_values=tuple(int(value) for value in (line_values if line_values is not None else dataset.line_values)),
        primary_name=str(dataset.primary_name),
        line_name=str(dataset.line_name),
        scene_variant=str(dataset.scene_variant),
        label_count_range=tuple(dataset.label_count_range),
        scene_variant_probabilities=dict(dataset.scene_variant_probabilities),
    )


def unique_extremum(labels: Sequence[str], values: Sequence[int], *, mode: str) -> tuple[str, int]:
    if not labels:
        raise ValueError("empty candidate set")
    target = max(values) if str(mode) == "max" else min(values)
    winners = [str(label) for label, value in zip(labels, values) if int(value) == int(target)]
    if len(winners) != 1:
        raise ValueError("extremum tie")
    return str(winners[0]), int(target)


def indices_for_keyed_annotation(
    indices: Iterable[int],
    scene: ComboScene,
    *,
    include_primary: bool,
    include_line: bool,
) -> tuple[dict[str, list[float]], list[str]]:
    points: dict[str, list[float]] = {}
    labels: list[str] = []
    for idx in indices:
        category_label = str(scene.labels[int(idx)])
        if include_primary:
            points[f"{category_label}.primary"] = [
                float(scene.primary_points[int(idx)][0]),
                float(scene.primary_points[int(idx)][1]),
            ]
            labels.append(f"{scene.primary_name}:{scene.labels[int(idx)]}")
        if include_line:
            points[f"{category_label}.line"] = [
                float(scene.line_points[int(idx)][0]),
                float(scene.line_points[int(idx)][1]),
            ]
            labels.append(f"{scene.line_name}:{scene.labels[int(idx)]}")
    return points, labels


def select_cross_mark_difference(
    scene: ComboScene,
    *,
    mode: str,
    rng: Any,
) -> SelectionResult:
    usable = [
        idx
        for idx, (primary_value, line_value) in enumerate(zip(scene.primary_values, scene.line_values))
        if int(primary_value) != int(line_value)
    ]
    if not usable:
        raise ValueError("cross-mark gap needs unequal values")
    idx = int(usable[int(rng.randrange(0, len(usable)))])
    if str(mode) == "primary_minus_line":
        answer = int(scene.primary_values[idx]) - int(scene.line_values[idx])
    elif str(mode) == "line_minus_primary":
        answer = int(scene.line_values[idx]) - int(scene.primary_values[idx])
    else:
        raise ValueError(f"unsupported cross-mark difference mode: {mode}")
    annotation, annotation_labels = indices_for_keyed_annotation(
        [idx],
        scene,
        include_primary=True,
        include_line=True,
    )
    return SelectionResult(
        answer=int(answer),
        answer_type="integer",
        annotation_points=annotation,
        trace={
            "target_label": str(scene.labels[idx]),
            "target_index": int(idx),
            "annotation_labels": annotation_labels,
        },
        question_format="cross_mark_difference_query",
    )


def select_conditioned_extremum(
    scene: ComboScene,
    *,
    condition_role: str,
    condition_relation: str,
    target_role: str,
    extremum: str,
    rng: Any,
) -> SelectionResult:
    if str(condition_role) == "primary":
        condition_values = scene.primary_values
    elif str(condition_role) == "line":
        condition_values = scene.line_values
    else:
        raise ValueError(f"unsupported condition role: {condition_role}")
    if str(target_role) == "primary":
        all_target_values = scene.primary_values
    elif str(target_role) == "line":
        all_target_values = scene.line_values
    else:
        raise ValueError(f"unsupported target role: {target_role}")
    above = str(condition_relation) == "above"
    threshold = select_threshold(condition_values, rng=rng, above=above)
    candidate_indices = [
        idx
        for idx, value in enumerate(condition_values)
        if (int(value) > int(threshold) if bool(above) else int(value) < int(threshold))
    ]
    target_values = [int(all_target_values[idx]) for idx in candidate_indices]
    answer, _ = unique_extremum(
        [scene.labels[idx] for idx in candidate_indices],
        target_values,
        mode=str(extremum),
    )
    answer_index = scene.labels.index(answer)
    annotation, annotation_labels = indices_for_keyed_annotation(
        [answer_index],
        scene,
        include_primary=True,
        include_line=True,
    )
    return SelectionResult(
        answer=str(answer),
        answer_type="string",
        annotation_points=annotation,
        trace={
            "threshold_value": int(threshold),
            "threshold_relation": str(condition_relation),
            "target_index": int(answer_index),
            "candidate_indices": [int(idx) for idx in candidate_indices],
            "annotation_labels": annotation_labels,
        },
        question_format="conditioned_extremum_query",
    )


def select_threshold(values: Sequence[int], *, rng: Any, above: bool, min_candidates: int = 2) -> int:
    sorted_values = sorted(set(int(value) for value in values))
    if len(sorted_values) < 4:
        raise ValueError("not enough distinct threshold values")
    candidates = []
    for low, high in zip(sorted_values[:-1], sorted_values[1:]):
        threshold = int((int(low) + int(high)) // 2)
        count = sum(1 for value in values if (int(value) > threshold if above else int(value) < threshold))
        if int(min_candidates) <= count <= len(values) - 1:
            candidates.append(threshold)
    if not candidates:
        raise ValueError("no usable threshold")
    return int(candidates[int(rng.randrange(0, len(candidates)))])


def balanced_target_count(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    label_count: int,
    sampling_divisor: int,
) -> tuple[int, dict[int, float], tuple[int, int]]:
    low = int(params.get("dual_condition_target_count_min", group_default(GENERATION_DEFAULTS, "dual_condition_target_count_min", 1)))
    high = int(params.get("dual_condition_target_count_max", group_default(GENERATION_DEFAULTS, "dual_condition_target_count_max", 5)))
    high = min(int(high), max(1, int(label_count) - 1))
    if int(high) < int(low):
        raise ValueError("dual-condition target count support is infeasible")
    support = tuple(range(int(low), int(high) + 1))
    probabilities = {int(value): 1.0 / float(len(support)) for value in support}
    sampling_index = params.get("_sample_cursor")
    if sampling_index is not None:
        index = abs(int(sampling_index)) // max(1, int(sampling_divisor))
    else:
        index = int(hash64(instance_seed, f"{SCENE_NAMESPACE}.dual_condition_target_count"))
    return int(support[int(index) % len(support)]), probabilities, (int(low), int(high))


def threshold_candidates_for(values: Sequence[int], *, above: bool) -> tuple[int, ...]:
    sorted_values = sorted(set(int(value) for value in values))
    if len(sorted_values) < 2:
        return ()
    thresholds = []
    for low, high in zip(sorted_values[:-1], sorted_values[1:]):
        thresholds.append(int(low) if bool(above) else int(high))
    return tuple(dict.fromkeys(thresholds))


def choose_targeted_condition(
    *,
    primary: Sequence[int],
    line: Sequence[int],
    rng: Any,
    target_count: int,
    primary_relation: str | None = None,
    line_relation: str | None = None,
    interval_role: str | None = None,
) -> tuple[list[int], dict[str, int]]:
    candidates: list[tuple[list[int], dict[str, int]]] = []
    if interval_role == "primary":
        primary_values = sorted(set(int(value) for value in primary))
        line_thresholds = threshold_candidates_for(line, above=True)
        for low_index, low in enumerate(primary_values):
            for high in primary_values[low_index:]:
                for line_threshold in line_thresholds:
                    matching = [
                        idx
                        for idx, (a, b) in enumerate(zip(primary, line))
                        if int(low) <= int(a) <= int(high) and int(b) > int(line_threshold)
                    ]
                    if len(matching) == int(target_count):
                        candidates.append(
                            (
                                [int(idx) for idx in matching],
                                {
                                    "lower_threshold_value": int(low),
                                    "upper_threshold_value": int(high),
                                    "line_threshold_value": int(line_threshold),
                                },
                            )
                        )
    elif interval_role == "line":
        line_values = sorted(set(int(value) for value in line))
        primary_thresholds = threshold_candidates_for(primary, above=True)
        for low_index, low in enumerate(line_values):
            for high in line_values[low_index:]:
                for primary_threshold in primary_thresholds:
                    matching = [
                        idx
                        for idx, (a, b) in enumerate(zip(primary, line))
                        if int(low) <= int(b) <= int(high) and int(a) > int(primary_threshold)
                    ]
                    if len(matching) == int(target_count):
                        candidates.append(
                            (
                                [int(idx) for idx in matching],
                                {
                                    "lower_threshold_value": int(low),
                                    "upper_threshold_value": int(high),
                                    "primary_threshold_value": int(primary_threshold),
                                },
                            )
                        )
    else:
        primary_above = str(primary_relation) == "above"
        line_above = str(line_relation) == "above"
        primary_thresholds = threshold_candidates_for(primary, above=primary_above)
        line_thresholds = threshold_candidates_for(line, above=line_above)
        for primary_threshold in primary_thresholds:
            for line_threshold in line_thresholds:
                matching = [
                    idx
                    for idx, (a, b) in enumerate(zip(primary, line))
                    if (int(a) > int(primary_threshold) if primary_above else int(a) < int(primary_threshold))
                    and (int(b) > int(line_threshold) if line_above else int(b) < int(line_threshold))
                ]
                if len(matching) == int(target_count):
                    candidates.append(
                        (
                            [int(idx) for idx in matching],
                            {
                                "primary_threshold_value": int(primary_threshold),
                                "line_threshold_value": int(line_threshold),
                            },
                        )
                    )
    if not candidates:
        raise ValueError("no targeted dual-condition threshold pair")
    return candidates[int(rng.randrange(0, len(candidates)))]


def select_condition_count(
    scene: ComboScene,
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    rng: Any,
    sampling_divisor: int,
    primary_relation: str | None = None,
    line_relation: str | None = None,
    interval_role: str | None = None,
) -> SelectionResult:
    target_count, target_probabilities, target_range = balanced_target_count(
        params=params,
        instance_seed=int(instance_seed),
        label_count=len(scene.labels),
        sampling_divisor=int(sampling_divisor),
    )
    matching, extra = choose_targeted_condition(
        primary=scene.primary_values,
        line=scene.line_values,
        rng=rng,
        target_count=int(target_count),
        primary_relation=primary_relation,
        line_relation=line_relation,
        interval_role=interval_role,
    )
    annotation, annotation_labels = indices_for_keyed_annotation(
        matching,
        scene,
        include_primary=True,
        include_line=True,
    )
    return SelectionResult(
        answer=int(len(matching)),
        answer_type="integer",
        annotation_points=annotation,
        trace={
            **extra,
            "target_count": int(target_count),
            "target_count_range": [int(target_range[0]), int(target_range[1])],
            "target_count_probabilities": {str(key): float(value) for key, value in target_probabilities.items()},
            "matching_indices": [int(idx) for idx in matching],
            "annotation_labels": annotation_labels,
        },
        question_format="dual_condition_count_query",
    )


def select_gap_extremum(
    scene: ComboScene,
    *,
    gap_mode: str,
) -> SelectionResult:
    candidates: list[tuple[int, int]] = []
    for idx, (primary_value, line_value) in enumerate(zip(scene.primary_values, scene.line_values)):
        signed_gap = int(primary_value) - int(line_value)
        if str(gap_mode) == "largest_absolute":
            candidates.append((idx, abs(int(signed_gap))))
        elif str(gap_mode) == "smallest_nonzero_absolute":
            if int(signed_gap) != 0:
                candidates.append((idx, abs(int(signed_gap))))
        elif str(gap_mode) == "largest_primary_over_line":
            if int(signed_gap) > 0:
                candidates.append((idx, int(signed_gap)))
        elif str(gap_mode) == "largest_line_over_primary" and int(signed_gap) < 0:
            candidates.append((idx, -int(signed_gap)))
    if not candidates:
        raise ValueError("no gap-extremum candidates")
    target_value = min(value for _, value in candidates) if str(gap_mode) == "smallest_nonzero_absolute" else max(value for _, value in candidates)
    winners = [idx for idx, value in candidates if int(value) == int(target_value)]
    if len(winners) != 1:
        raise ValueError("gap extremum tie")
    answer_index = int(winners[0])
    annotation, annotation_labels = indices_for_keyed_annotation(
        [answer_index],
        scene,
        include_primary=True,
        include_line=True,
    )
    return SelectionResult(
        answer=str(scene.labels[answer_index]),
        answer_type="string",
        annotation_points=annotation,
        trace={
            "target_index": int(answer_index),
            "target_label": str(scene.labels[answer_index]),
            "target_gap_value": int(target_value),
            "candidate_indices": [int(idx) for idx, _ in candidates],
            "gap_values": {str(scene.labels[idx]): int(abs(int(scene.primary_values[idx]) - int(scene.line_values[idx]))) for idx in range(len(scene.labels))},
            "signed_gap_values": {str(scene.labels[idx]): int(scene.primary_values[idx]) - int(scene.line_values[idx]) for idx in range(len(scene.labels))},
            "annotation_labels": annotation_labels,
        },
        question_format="gap_extremum_label_query",
    )


def crossing_target_role(target_role: str) -> str:
    if str(target_role) not in {"primary", "line"}:
        raise ValueError(f"unsupported crossing target role: {target_role}")
    return str(target_role)


def construct_threshold_crossing_values(
    *,
    target_role: str,
    above: bool,
    label_count: int,
    value_min: int,
    value_max: int,
    params: Mapping[str, Any],
    instance_seed: int,
    target_sampling_divisor: int,
) -> tuple[tuple[int, ...], dict[str, Any]]:
    if int(value_min) + 2 > int(value_max):
        raise ValueError("combo threshold crossing requires at least three possible values")
    crossing_index, index_probabilities, index_range = balanced_crossing_index(
        params=params,
        instance_seed=int(instance_seed),
        label_count=int(label_count),
        sampling_divisor=int(target_sampling_divisor),
    )
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.threshold_crossing:{target_role}:{'above' if above else 'below'}")
    threshold = int(rng.randint(int(value_min) + 1, int(value_max) - 1))
    values: list[int] = []
    for idx in range(int(label_count)):
        if int(idx) < int(crossing_index):
            value = rng.randint(int(value_min), int(threshold)) if bool(above) else rng.randint(int(threshold), int(value_max))
        elif int(idx) == int(crossing_index):
            value = rng.randint(int(threshold) + 1, int(value_max)) if bool(above) else rng.randint(int(value_min), int(threshold) - 1)
        else:
            value = rng.randint(int(value_min), int(value_max))
        values.append(int(value))
    return tuple(int(value) for value in values), {
        "threshold_value": int(threshold),
        "crossing_index": int(crossing_index),
        "crossing_index_range": [int(index_range[0]), int(index_range[1])],
        "crossing_index_probabilities": {str(key): float(value) for key, value in index_probabilities.items()},
        "crossing_direction": "above" if bool(above) else "below",
        "comparison_phrase": "above" if bool(above) else "below",
        "target_series_role": crossing_target_role(str(target_role)),
    }


def balanced_crossing_index(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    label_count: int,
    sampling_divisor: int,
) -> tuple[int, dict[int, float], tuple[int, int]]:
    low = int(params.get("crossing_index_min", group_default(GENERATION_DEFAULTS, "crossing_index_min", 2)))
    high = int(params.get("crossing_index_max", group_default(GENERATION_DEFAULTS, "crossing_index_max", int(label_count) - 2)))
    low = max(1, int(low))
    high = min(int(high), int(label_count) - 2)
    if int(low) > int(high):
        raise ValueError("no feasible combo threshold-crossing index support")
    support = tuple(range(int(low), int(high) + 1))
    probabilities = {int(value): 1.0 / float(len(support)) for value in support}
    sampling_index = params.get("_sample_cursor")
    if sampling_index is not None:
        index = abs(int(sampling_index)) // max(1, int(sampling_divisor))
    else:
        index = int(hash64(instance_seed, f"{SCENE_NAMESPACE}.crossing_index:{int(label_count)}"))
    return int(support[int(index) % len(support)]), probabilities, (int(low), int(high))


def select_threshold_crossing(
    scene: ComboScene,
    *,
    target_role: str,
    above: bool,
    crossing_trace: Mapping[str, Any],
) -> SelectionResult:
    target_role = crossing_target_role(str(target_role))
    threshold = int(crossing_trace["threshold_value"])
    answer_index = int(crossing_trace["crossing_index"])
    target_values = scene.primary_values if str(target_role) == "primary" else scene.line_values
    for idx in range(int(answer_index)):
        value = int(target_values[int(idx)])
        if bool(above) and int(value) > int(threshold):
            raise ValueError("pre-crossing value unexpectedly satisfies above-threshold rule")
        if not bool(above) and int(value) < int(threshold):
            raise ValueError("pre-crossing value unexpectedly satisfies below-threshold rule")
    answer_value = int(target_values[int(answer_index)])
    if bool(above) and int(answer_value) <= int(threshold):
        raise ValueError("crossing value does not satisfy above-threshold rule")
    if not bool(above) and int(answer_value) >= int(threshold):
        raise ValueError("crossing value does not satisfy below-threshold rule")
    annotation, annotation_labels = indices_for_keyed_annotation(
        range(0, int(answer_index) + 1),
        scene,
        include_primary=(str(target_role) == "primary"),
        include_line=(str(target_role) == "line"),
    )
    target_series_name = str(scene.primary_name if str(target_role) == "primary" else scene.line_name)
    return SelectionResult(
        answer=str(scene.labels[int(answer_index)]),
        answer_type="string",
        annotation_points=annotation,
        trace={
            **dict(crossing_trace),
            "target_series_name": str(target_series_name),
            "target_series_values": [int(value) for value in target_values],
            "answer_index": int(answer_index),
            "answer_label": str(scene.labels[int(answer_index)]),
            "ordered_annotation_labels": [str(scene.labels[int(idx)]) for idx in range(0, int(answer_index) + 1)],
            "annotation_labels": annotation_labels,
        },
        question_format="series_threshold_crossing_label_query",
    )


__all__ = [
    "SelectionResult",
    "construct_threshold_crossing_values",
    "dataset_with_values",
    "sample_base_dataset",
    "select_condition_count",
    "select_conditioned_extremum",
    "select_cross_mark_difference",
    "select_gap_extremum",
    "select_threshold_crossing",
]
