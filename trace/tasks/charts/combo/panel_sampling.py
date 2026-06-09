"""Query construction and annotation helpers for combo chart panel tasks."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

from ....core.seed import hash64, spawn_rng
from ....core.types import TypedValue
from ...shared.config_defaults import group_default
from ..shared.label_assets import resolve_chart_category_labels, resolve_chart_compact_axis_labels
from .panel_common import TASK_ID, _GEN_DEFAULTS, _THRESHOLD_CROSSING_QUERY_IDS, _ComboScene

def _sample_labels(rng, count: int) -> Tuple[str, ...]:
    labels = resolve_chart_compact_axis_labels(
        rng,
        count=int(count),
        min_chars=2,
        max_chars=3,
    ).labels
    return tuple(str(label) for label in labels)

def _sample_values(rng, *, count: int, low: int, high: int) -> Tuple[int, ...]:
    return tuple(int(rng.randint(int(low), int(high))) for _ in range(int(count)))

def _choose_metric_pair(instance_seed: int) -> Tuple[str, str]:
    labels = resolve_chart_category_labels(
        spawn_rng(int(instance_seed), "charts.combo.metric_pair"),
        count=2,
        min_chars=2,
        max_chars=8,
        allow_spaces=False,
    ).labels
    return str(labels[0]), str(labels[1])

def _unique_extremum(labels: Sequence[str], values: Sequence[int], *, mode: str) -> Tuple[str, int]:
    if not labels:
        raise ValueError("empty candidate set")
    target = max(values) if str(mode) == "max" else min(values)
    winners = [str(label) for label, value in zip(labels, values) if int(value) == int(target)]
    if len(winners) != 1:
        raise ValueError("extremum tie")
    return str(winners[0]), int(target)

def _indices_for_keyed_annotation(
    indices: Iterable[int],
    scene: _ComboScene,
    *,
    include_primary: bool,
    include_line: bool,
) -> Tuple[Dict[str, list[float]], list[str]]:
    points: Dict[str, list[float]] = {}
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

def _interval_keyed_annotation(start: int, end: int, scene: _ComboScene) -> Tuple[Dict[str, list[float]], list[str]]:
    start_label = str(scene.labels[int(start)])
    end_label = str(scene.labels[int(end)])
    points = {
        f"{start_label}.primary": [float(scene.primary_points[int(start)][0]), float(scene.primary_points[int(start)][1])],
        f"{start_label}.line": [float(scene.line_points[int(start)][0]), float(scene.line_points[int(start)][1])],
        f"{end_label}.primary": [float(scene.primary_points[int(end)][0]), float(scene.primary_points[int(end)][1])],
        f"{end_label}.line": [float(scene.line_points[int(end)][0]), float(scene.line_points[int(end)][1])],
    }
    labels = [
        f"{scene.primary_name}:{scene.labels[int(start)]}",
        f"{scene.line_name}:{scene.labels[int(start)]}",
        f"{scene.primary_name}:{scene.labels[int(end)]}",
        f"{scene.line_name}:{scene.labels[int(end)]}",
    ]
    return points, labels

def _is_threshold_crossing_query(query_id: str) -> bool:
    return str(query_id) in set(_THRESHOLD_CROSSING_QUERY_IDS)

def _threshold_crossing_target_role(query_id: str) -> str:
    return "primary" if str(query_id).startswith("primary_") else "line"

def _threshold_crossing_above(query_id: str) -> bool:
    return "_above_" in str(query_id)

def _target_series_annotation(
    indices: Iterable[int],
    scene: _ComboScene,
    *,
    target_role: str,
) -> Tuple[Dict[str, list[float]], list[str]]:
    return _indices_for_keyed_annotation(
        indices,
        scene,
        include_primary=(str(target_role) == "primary"),
        include_line=(str(target_role) == "line"),
    )

def _balanced_crossing_index(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    label_count: int,
    query_id: str,
    sampling_divisor: int,
) -> Tuple[int, Dict[int, float], Tuple[int, int]]:
    low = int(params.get("crossing_index_min", group_default(_GEN_DEFAULTS, "crossing_index_min", 2)))
    high = int(params.get("crossing_index_max", group_default(_GEN_DEFAULTS, "crossing_index_max", int(label_count) - 2)))
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
        index = int(hash64(instance_seed, f"charts.combo.crossing_index:{str(query_id)}:{int(label_count)}"))
    return int(support[int(index) % len(support)]), probabilities, (int(low), int(high))

def _construct_threshold_crossing_values(
    *,
    query_id: str,
    label_count: int,
    value_min: int,
    value_max: int,
    params: Mapping[str, Any],
    instance_seed: int,
    target_sampling_divisor: int,
) -> Tuple[Tuple[int, ...], Dict[str, Any]]:
    if int(value_min) + 2 > int(value_max):
        raise ValueError("combo threshold crossing requires at least three possible values")
    above = _threshold_crossing_above(str(query_id))
    crossing_index, index_probabilities, index_range = _balanced_crossing_index(
        params=params,
        instance_seed=int(instance_seed),
        label_count=int(label_count),
        query_id=str(query_id),
        sampling_divisor=int(target_sampling_divisor),
    )
    rng = spawn_rng(int(instance_seed), f"charts.combo.threshold_crossing:{str(query_id)}")
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
        "target_series_role": _threshold_crossing_target_role(str(query_id)),
    }

def _select_threshold(values: Sequence[int], *, rng, above: bool, min_candidates: int = 2) -> int:
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

def _balanced_target_count(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    label_count: int,
    sampling_divisor: int,
) -> Tuple[int, Dict[int, float], Tuple[int, int]]:
    low = int(params.get("dual_condition_target_count_min", group_default(_GEN_DEFAULTS, "dual_condition_target_count_min", 1)))
    high = int(params.get("dual_condition_target_count_max", group_default(_GEN_DEFAULTS, "dual_condition_target_count_max", 5)))
    high = min(int(high), max(1, int(label_count) - 1))
    if int(high) < int(low):
        raise ValueError("dual-condition target count support is infeasible")
    support = tuple(range(int(low), int(high) + 1))
    probabilities = {int(value): 1.0 / float(len(support)) for value in support}
    sampling_index = params.get("_sample_cursor")
    if sampling_index is not None:
        index = abs(int(sampling_index)) // max(1, int(sampling_divisor))
    else:
        index = int(hash64(instance_seed, "charts.combo.dual_condition_target_count"))
    return int(support[int(index) % len(support)]), probabilities, (int(low), int(high))

def _threshold_candidates_for(values: Sequence[int], *, above: bool) -> Tuple[int, ...]:
    sorted_values = sorted(set(int(value) for value in values))
    if len(sorted_values) < 2:
        return ()
    thresholds = []
    for low, high in zip(sorted_values[:-1], sorted_values[1:]):
        thresholds.append(int(low) if bool(above) else int(high))
    return tuple(dict.fromkeys(thresholds))

def _choose_targeted_dual_condition(
    *,
    query_id: str,
    primary: Sequence[int],
    line: Sequence[int],
    rng,
    target_count: int,
) -> Tuple[list[int], Dict[str, int]]:
    q = str(query_id)
    candidates: list[Tuple[list[int], Dict[str, int]]] = []
    if q == "primary_between_and_line_above":
        primary_values = sorted(set(int(value) for value in primary))
        line_thresholds = _threshold_candidates_for(line, above=True)
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
    elif q == "line_between_and_primary_above":
        line_values = sorted(set(int(value) for value in line))
        primary_thresholds = _threshold_candidates_for(primary, above=True)
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
        primary_above = "primary_above" in q
        line_above = "line_above" in q
        primary_thresholds = _threshold_candidates_for(primary, above=primary_above)
        line_thresholds = _threshold_candidates_for(line, above=line_above)
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

def _resolve_query_answer(
    *,
    task_query_ids: Sequence[str],
    query_id: str,
    scene: _ComboScene,
    rng,
    params: Mapping[str, Any],
    instance_seed: int,
    target_sampling_divisor: int,
    construction_trace: Mapping[str, Any] | None = None,
) -> Tuple[TypedValue, Dict[str, list[float]], Dict[str, Any], str, str, str, str]:
    labels = scene.labels
    primary = scene.primary_values
    line = scene.line_values
    q = str(query_id)
    prompt_slots: Dict[str, Any] = {}
    answer_hint_key = "answer_hint_value_integer"
    annotation_hint_key = "annotation_hint_needed_chart_marks"
    if q in set(_THRESHOLD_CROSSING_QUERY_IDS):
        crossing_trace = dict(construction_trace or {})
        if not crossing_trace:
            raise ValueError("threshold crossing query requires construction metadata")
        target_role = str(crossing_trace["target_series_role"])
        threshold = int(crossing_trace["threshold_value"])
        answer_index = int(crossing_trace["crossing_index"])
        above = _threshold_crossing_above(q)
        target_values = primary if str(target_role) == "primary" else line
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
        annotation, annotation_labels = _target_series_annotation(
            range(0, int(answer_index) + 1),
            scene,
            target_role=str(target_role),
        )
        target_series_name = str(scene.primary_name if str(target_role) == "primary" else scene.line_name)
        prompt_slots.update(
            {
                "target_series_name": str(target_series_name),
                "threshold_value": int(threshold),
                "comparison_phrase": str(crossing_trace["comparison_phrase"]),
                "crossing_direction": str(crossing_trace["crossing_direction"]),
            }
        )
        return (
            TypedValue(type="string", value=str(labels[int(answer_index)])),
            annotation,
            {
                **prompt_slots,
                **dict(crossing_trace),
                "target_series_values": [int(value) for value in target_values],
                "answer_index": int(answer_index),
                "answer_label": str(labels[int(answer_index)]),
                "ordered_annotation_labels": [str(labels[int(idx)]) for idx in range(0, int(answer_index) + 1)],
                "annotation_labels": annotation_labels,
            },
            "series_threshold_crossing_label_query",
            q,
            "answer_hint_crossing_label",
            "annotation_hint_target_prefix_marks",
        )
    if q in {
        "primary_minus_line_at_label",
        "line_minus_primary_at_label",
        "absolute_gap_at_label",
        "larger_minus_smaller_at_label",
    }:
        usable = [idx for idx, (a, b) in enumerate(zip(primary, line)) if int(a) != int(b)]
        if not usable:
            raise ValueError("cross-mark gap needs unequal values")
        idx = int(usable[int(rng.randrange(0, len(usable)))])
        if q == "primary_minus_line_at_label":
            answer = int(primary[idx]) - int(line[idx])
        elif q == "line_minus_primary_at_label":
            answer = int(line[idx]) - int(primary[idx])
        elif q == "absolute_gap_at_label":
            answer = abs(int(primary[idx]) - int(line[idx]))
        else:
            answer = max(int(primary[idx]), int(line[idx])) - min(int(primary[idx]), int(line[idx]))
        annotation, annotation_labels = _indices_for_keyed_annotation(
            [idx],
            scene,
            include_primary=True,
            include_line=True,
        )
        prompt_slots["target_label"] = str(labels[idx])
        return (
            TypedValue(type="integer", value=int(answer)),
            annotation,
            {"target_label": str(labels[idx]), "target_index": idx, "annotation_labels": annotation_labels},
            "cross_mark_difference_query",
            q,
            answer_hint_key,
            annotation_hint_key,
        )
    if q in {
        "max_line_where_primary_above_threshold",
        "min_line_where_primary_above_threshold",
        "max_primary_where_line_below_threshold",
        "min_primary_where_line_below_threshold",
    }:
        if "primary_above" in q:
            threshold = _select_threshold(primary, rng=rng, above=True)
            candidate_indices = [idx for idx, value in enumerate(primary) if int(value) > int(threshold)]
            target_values = [int(line[idx]) for idx in candidate_indices]
            mode = "max" if q.startswith("max_") else "min"
            answer, _ = _unique_extremum([labels[idx] for idx in candidate_indices], target_values, mode=mode)
            answer_index = labels.index(answer)
            annotation, annotation_labels = _indices_for_keyed_annotation(
                [answer_index],
                scene,
                include_primary=True,
                include_line=True,
            )
            relation_phrase = "above"
        else:
            threshold = _select_threshold(line, rng=rng, above=False)
            candidate_indices = [idx for idx, value in enumerate(line) if int(value) < int(threshold)]
            target_values = [int(primary[idx]) for idx in candidate_indices]
            mode = "max" if q.startswith("max_") else "min"
            answer, _ = _unique_extremum([labels[idx] for idx in candidate_indices], target_values, mode=mode)
            answer_index = labels.index(answer)
            annotation, annotation_labels = _indices_for_keyed_annotation(
                [answer_index],
                scene,
                include_primary=True,
                include_line=True,
            )
            relation_phrase = "below"
        prompt_slots.update({"threshold_value": int(threshold), "threshold_relation": relation_phrase})
        return (
            TypedValue(type="string", value=str(answer)),
            annotation,
            {
                "threshold_value": int(threshold),
                "target_index": int(answer_index),
                "candidate_indices": [int(idx) for idx in candidate_indices],
                "annotation_labels": annotation_labels,
            },
            "conditioned_extremum_query",
            q,
            "answer_hint_category_label_extremum",
            "annotation_hint_answer_category_marks",
        )
    if q in {
        "primary_above_and_line_above",
        "primary_above_and_line_below",
        "primary_below_and_line_above",
        "primary_between_and_line_above",
        "line_between_and_primary_above",
    }:
        target_count, target_probabilities, target_range = _balanced_target_count(
            params=params,
            instance_seed=int(instance_seed),
            label_count=len(labels),
            sampling_divisor=int(target_sampling_divisor),
        )
        matching, extra = _choose_targeted_dual_condition(
            query_id=q,
            primary=primary,
            line=line,
            rng=rng,
            target_count=int(target_count),
        )
        prompt_slots.update(dict(extra))
        annotation, annotation_labels = _indices_for_keyed_annotation(
            matching,
            scene,
            include_primary=True,
            include_line=True,
        )
        return (
            TypedValue(type="integer", value=int(len(matching))),
            annotation,
            {
                **extra,
                "target_count": int(target_count),
                "target_count_range": [int(target_range[0]), int(target_range[1])],
                "target_count_probabilities": {str(key): float(value) for key, value in target_probabilities.items()},
                "matching_indices": [int(idx) for idx in matching],
                "annotation_labels": annotation_labels,
            },
            "dual_condition_count_query",
            q,
            "answer_hint_matching_category_count",
            "annotation_hint_matching_category_marks",
        )
    if q in {
        "largest_absolute_gap_label",
        "smallest_nonzero_absolute_gap_label",
        "largest_primary_over_line_gap_label",
        "largest_line_over_primary_gap_label",
    }:
        candidates: list[Tuple[int, int]] = []
        for idx, (a, b) in enumerate(zip(primary, line)):
            signed_gap = int(a) - int(b)
            if q == "largest_absolute_gap_label":
                candidates.append((idx, abs(int(signed_gap))))
            elif q == "smallest_nonzero_absolute_gap_label":
                if int(signed_gap) != 0:
                    candidates.append((idx, abs(int(signed_gap))))
            elif q == "largest_primary_over_line_gap_label":
                if int(signed_gap) > 0:
                    candidates.append((idx, int(signed_gap)))
            elif q == "largest_line_over_primary_gap_label" and int(signed_gap) < 0:
                candidates.append((idx, -int(signed_gap)))
        if not candidates:
            raise ValueError("no gap-extremum candidates")
        target_value = min(value for _, value in candidates) if q == "smallest_nonzero_absolute_gap_label" else max(value for _, value in candidates)
        winners = [idx for idx, value in candidates if int(value) == int(target_value)]
        if len(winners) != 1:
            raise ValueError("gap extremum tie")
        answer_index = int(winners[0])
        candidate_indices = [int(idx) for idx, _ in candidates]
        annotation, annotation_labels = _indices_for_keyed_annotation(
            [answer_index],
            scene,
            include_primary=True,
            include_line=True,
        )
        return (
            TypedValue(type="string", value=str(labels[answer_index])),
            annotation,
            {
                "target_index": int(answer_index),
                "target_label": str(labels[answer_index]),
                "target_gap_value": int(target_value),
                "candidate_indices": candidate_indices,
                "gap_values": {str(labels[idx]): int(abs(int(primary[idx]) - int(line[idx]))) for idx in range(len(labels))},
                "signed_gap_values": {str(labels[idx]): int(primary[idx]) - int(line[idx]) for idx in range(len(labels))},
                "annotation_labels": annotation_labels,
            },
            "gap_extremum_label_query",
            q,
            "answer_hint_category_label",
            "annotation_hint_answer_category_marks",
        )
    raise ValueError(f"unsupported combo query id: {q}")
