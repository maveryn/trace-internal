"""Dataset construction for parallel-coordinates chart tasks."""

from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ..shared.label_assets import resolve_chart_entity_labels
from .profile_common import (
    CONDITION_QUERY_IDS,
    CROSSING_QUERY_IDS,
    DELTA_QUERY_IDS,
    SCENE_ID,
    TASK_ID,
    _GEN_DEFAULTS,
    _PROFILE_PALETTE,
    _Dataset,
    _Profile,
    _Query,
    _balanced_int,
    _gen_int,
    _resolve_scene_variant,
)

def _choose_axis_pair(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    axis_count: int,
    adjacent_only: bool,
    namespace: str,
) -> Tuple[int, int]:
    pairs = (
        [(index, index + 1) for index in range(int(axis_count) - 1)]
        if bool(adjacent_only)
        else [(i, j) for i in range(int(axis_count)) for j in range(i + 1, int(axis_count))]
    )
    if not pairs:
        raise ValueError("axis_count must allow at least one axis pair")
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    return tuple(pairs[int(index) % len(pairs)])  # type: ignore[return-value]

def _make_exact_inversion_permutation(n: int, inversions: int, rng) -> Tuple[int, ...]:
    """Return one permutation of 0..n-1 with exactly `inversions` inversions."""

    target = int(inversions)
    if target < 0 or target > (int(n) * (int(n) - 1)) // 2:
        raise ValueError("inversion count outside feasible range")
    for _ in range(2000):
        values = list(range(int(n)))
        rng.shuffle(values)
        if _inversion_count(values) == target:
            return tuple(values)
    # Deterministic construction from inversion vector.
    remaining = int(target)
    code: List[int] = []
    for i in range(int(n)):
        max_here = int(n) - 1 - int(i)
        take = min(max_here, remaining)
        code.append(int(take))
        remaining -= int(take)
    pool = list(range(int(n)))
    out: List[int] = []
    for take in code:
        out.append(pool.pop(int(take)))
    return tuple(out)

def _inversion_count(values: Sequence[int]) -> int:
    return sum(1 for i, j in combinations(range(len(values)), 2) if int(values[i]) > int(values[j]))

def _rank_values(order: Sequence[int], *, value_min: int, value_max: int) -> Dict[int, int]:
    n = len(order)
    if n <= 1:
        return {int(order[0]): int(value_min)}
    lo = int(value_min) + 1
    hi = int(value_max) - 1
    step = max(1, int((hi - lo) / max(1, n - 1)))
    return {int(profile_index): int(min(hi, lo + (rank * step))) for rank, profile_index in enumerate(order)}

def _sample_base(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    query_id_probabilities: Mapping[str, float],
) -> Tuple[str, Tuple[str, ...], List[str], int, int, int, int, Dict[str, Any]]:
    scene_variant, scene_probs = _resolve_scene_variant(params, instance_seed=int(instance_seed))
    axis_min, axis_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="axis_count_min",
        max_key="axis_count_max",
        fallback_min=4,
        fallback_max=6,
        context=f"generation defaults for {TASK_ID}",
    )
    profile_min, profile_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="profile_count_min",
        max_key="profile_count_max",
        fallback_min=5,
        fallback_max=8,
        context=f"generation defaults for {TASK_ID}",
    )
    if str(query_id) in CROSSING_QUERY_IDS:
        axis_min, axis_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="crossing_axis_count_min",
            max_key="crossing_axis_count_max",
            fallback_min=int(axis_min),
            fallback_max=int(axis_max),
            context=f"crossing generation defaults for {TASK_ID}",
        )
        profile_min, profile_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="crossing_profile_count_min",
            max_key="crossing_profile_count_max",
            fallback_min=int(profile_min),
            fallback_max=int(profile_max),
            context=f"crossing generation defaults for {TASK_ID}",
        )
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="value_min",
        max_key="value_max",
        fallback_min=1,
        fallback_max=20,
        context=f"generation defaults for {TASK_ID}",
    )
    axis_count, axis_count_probs = _balanced_int(
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.axis_count",
        low=int(axis_min),
        high=int(axis_max),
    )
    profile_count, profile_count_probs = _balanced_int(
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.profile_count",
        low=int(profile_min),
        high=int(profile_max),
    )
    metric_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.metrics")
    metrics = list(
        resolve_chart_entity_labels(
            metric_rng,
            count=int(axis_count),
            min_chars=2,
            max_chars=8,
            allow_spaces=False,
        ).labels
    )
    profile_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.profile_labels")
    profile_labels = list(
        resolve_chart_entity_labels(
            profile_rng,
            count=int(profile_count),
            min_chars=2,
            max_chars=6,
            allow_spaces=False,
        ).labels
    )
    trace_params = {
        "query_id": str(query_id),
        "scene_variant": str(scene_variant),
        "query_id_probabilities": dict(query_id_probabilities),
        "scene_variant_probabilities": dict(scene_probs),
        "axis_count": int(axis_count),
        "axis_count_probabilities": dict(axis_count_probs),
        "profile_count": int(profile_count),
        "profile_count_probabilities": dict(profile_count_probs),
        "value_min": int(value_min),
        "value_max": int(value_max),
    }
    return (
        str(scene_variant),
        tuple(str(value) for value in metrics),
        list(profile_labels),
        int(profile_count),
        int(axis_count),
        int(value_min),
        int(value_max),
        trace_params,
    )

def _build_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    query_id_probabilities: Mapping[str, float],
) -> _Dataset:
    (
        scene_variant,
        metrics,
        profile_labels,
        profile_count,
        axis_count,
        value_min,
        value_max,
        trace_params,
    ) = _sample_base(
        params=params,
        instance_seed=int(instance_seed),
        query_id=str(query_id),
        query_id_probabilities=query_id_probabilities,
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.values.{query_id}")
    values: List[List[int]] = [
        [int(rng.randint(int(value_min), int(value_max))) for _ in range(int(axis_count))]
        for _ in range(int(profile_count))
    ]
    axis_i, axis_j = _choose_axis_pair(
        params,
        instance_seed=int(instance_seed),
        axis_count=int(axis_count),
        adjacent_only=str(query_id) in CROSSING_QUERY_IDS,
        namespace=f"{TASK_ID}.{query_id}.axis_pair",
    )
    threshold: int | None = None
    reference_profile_id: str | None = None
    annotation_profile_ids: Tuple[str, ...] = ()
    crossing_pairs: Tuple[Tuple[str, str], ...] = ()

    if str(query_id) in CONDITION_QUERY_IDS:
        threshold_min = _gen_int(params, "condition_threshold_min", 8)
        threshold_max = _gen_int(params, "condition_threshold_max", 14)
        threshold, threshold_probs = _balanced_int(
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.threshold",
            low=int(threshold_min),
            high=int(threshold_max),
        )
        count_min = _gen_int(params, "condition_answer_count_min", 1)
        count_max = min(_gen_int(params, "condition_answer_count_max", 5), int(profile_count) - 1)
        target_count, target_count_probs = _balanced_int(
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.answer",
            low=int(count_min),
            high=max(int(count_min), int(count_max)),
        )
        annotation_indices = set(rng.sample(list(range(int(profile_count))), int(target_count)))
        for profile_index in range(int(profile_count)):
            is_target = int(profile_index) in annotation_indices
            if str(query_id) == "above_on_both_axes":
                if is_target:
                    values[profile_index][axis_i] = int(rng.randint(int(threshold) + 1, int(value_max)))
                    values[profile_index][axis_j] = int(rng.randint(int(threshold) + 1, int(value_max)))
                else:
                    fail_axis = axis_i if rng.random() < 0.5 else axis_j
                    values[profile_index][axis_i] = int(rng.randint(int(value_min), int(value_max)))
                    values[profile_index][axis_j] = int(rng.randint(int(value_min), int(value_max)))
                    values[profile_index][fail_axis] = int(rng.randint(int(value_min), int(threshold)))
            elif str(query_id) == "below_on_both_axes":
                if is_target:
                    values[profile_index][axis_i] = int(rng.randint(int(value_min), int(threshold) - 1))
                    values[profile_index][axis_j] = int(rng.randint(int(value_min), int(threshold) - 1))
                else:
                    fail_axis = axis_i if rng.random() < 0.5 else axis_j
                    values[profile_index][axis_i] = int(rng.randint(int(value_min), int(value_max)))
                    values[profile_index][axis_j] = int(rng.randint(int(value_min), int(value_max)))
                    values[profile_index][fail_axis] = int(rng.randint(int(threshold), int(value_max)))
            else:
                if is_target:
                    values[profile_index][axis_i] = int(rng.randint(int(threshold) + 1, int(value_max)))
                    values[profile_index][axis_j] = int(rng.randint(int(value_min), int(threshold) - 1))
                else:
                    if rng.random() < 0.5:
                        values[profile_index][axis_i] = int(rng.randint(int(value_min), int(threshold)))
                    else:
                        values[profile_index][axis_j] = int(rng.randint(int(threshold), int(value_max)))
            annotation_profile_ids = tuple(f"profile_{index}" for index in sorted(annotation_indices))
        answer: int | str = int(target_count)
        answer_type = "integer"
        trace_params.update(
            {
                "threshold": int(threshold),
                "threshold_probabilities": dict(threshold_probs),
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probs),
            }
        )
    elif str(query_id) in DELTA_QUERY_IDS:
        target_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.target_profile",
        ) % int(profile_count)
        deltas = list(range(1, min(12, int(value_max) - int(value_min)) + 1))
        rng.shuffle(deltas)
        if len(deltas) < int(profile_count):
            raise ValueError("not enough distinct deltas for profile extrema")
        target_delta = int(max(deltas))
        other_deltas = [int(value) for value in deltas if int(value) != int(target_delta)]
        for profile_index in range(int(profile_count)):
            delta = int(target_delta if int(profile_index) == int(target_index) else other_deltas.pop())
            base_low = int(value_min)
            base_high = int(value_max) - int(delta)
            base = int(rng.randint(int(base_low), int(base_high)))
            if str(query_id) == "largest_increase_between_axes":
                values[profile_index][axis_i] = int(base)
                values[profile_index][axis_j] = int(base + delta)
            elif str(query_id) == "largest_decrease_between_axes":
                values[profile_index][axis_i] = int(base + delta)
                values[profile_index][axis_j] = int(base)
            else:
                if int(profile_index) == int(target_index) or rng.random() < 0.5:
                    values[profile_index][axis_i] = int(base)
                    values[profile_index][axis_j] = int(base + delta)
                else:
                    values[profile_index][axis_i] = int(base + delta)
                    values[profile_index][axis_j] = int(base)
        annotation_profile_ids = (f"profile_{target_index}",)
        answer = str(profile_labels[int(target_index)])
        answer_type = "string"
        trace_params.update({"target_profile_index": int(target_index), "target_delta": int(target_delta)})
    elif str(query_id) == "all_crossings_between_adjacent_axes":
        max_crossings = min(_gen_int(params, "crossing_answer_count_max", 10), (int(profile_count) * (int(profile_count) - 1)) // 2)
        min_crossings = min(_gen_int(params, "crossing_answer_count_min", 1), int(max_crossings))
        target_count, target_count_probs = _balanced_int(
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.answer",
            low=int(min_crossings),
            high=int(max_crossings),
        )
        order_a = tuple(range(int(profile_count)))
        order_b = _make_exact_inversion_permutation(int(profile_count), int(target_count), rng)
        rank_values_a = _rank_values(order_a, value_min=int(value_min), value_max=int(value_max))
        rank_values_b = _rank_values(order_b, value_min=int(value_min), value_max=int(value_max))
        for profile_index in range(int(profile_count)):
            values[profile_index][axis_i] = int(rank_values_a[int(profile_index)])
            values[profile_index][axis_j] = int(rank_values_b[int(profile_index)])
        profile_ids = [f"profile_{index}" for index in range(int(profile_count))]
        crossing_pairs = tuple(
            (profile_ids[a], profile_ids[b])
            for a, b in combinations(range(int(profile_count)), 2)
            if (values[a][axis_i] - values[b][axis_i]) * (values[a][axis_j] - values[b][axis_j]) < 0
        )
        annotation_profile_ids = tuple(profile_ids)
        answer = int(len(crossing_pairs))
        answer_type = "integer"
        trace_params.update({"target_count": int(target_count), "target_count_probabilities": dict(target_count_probs)})
    elif str(query_id) == "crossings_involving_profile_between_axes":
        max_cross = min(_gen_int(params, "profile_crossing_answer_count_max", 5), int(profile_count) - 1)
        min_cross = min(_gen_int(params, "profile_crossing_answer_count_min", 1), int(max_cross))
        target_count, target_count_probs = _balanced_int(
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.answer",
            low=int(min_cross),
            high=int(max_cross),
        )
        target_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.target_profile",
        ) % int(profile_count)
        others = [index for index in range(int(profile_count)) if int(index) != int(target_index)]
        order_a = [int(target_index)] + others
        order_b = others[: int(target_count)] + [int(target_index)] + others[int(target_count) :]
        rank_values_a = _rank_values(order_a, value_min=int(value_min), value_max=int(value_max))
        rank_values_b = _rank_values(order_b, value_min=int(value_min), value_max=int(value_max))
        for profile_index in range(int(profile_count)):
            values[profile_index][axis_i] = int(rank_values_a[int(profile_index)])
            values[profile_index][axis_j] = int(rank_values_b[int(profile_index)])
        reference_profile_id = f"profile_{target_index}"
        crossing_pairs = tuple((reference_profile_id, f"profile_{index}") for index in others[: int(target_count)])
        annotation_profile_ids = (reference_profile_id,) + tuple(f"profile_{index}" for index in others[: int(target_count)])
        answer = int(target_count)
        answer_type = "integer"
        trace_params.update(
            {
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probs),
                "reference_profile_id": str(reference_profile_id),
                "reference_profile_label": str(profile_labels[int(target_index)]),
            }
        )
    else:
        raise ValueError(f"unsupported query id: {query_id}")

    profiles = tuple(
        _Profile(
            profile_id=f"profile_{index}",
            label=str(label),
            values=tuple(int(value) for value in values[index]),
            color_rgb=tuple(int(channel) for channel in _PROFILE_PALETTE[index % len(_PROFILE_PALETTE)]),
        )
        for index, label in enumerate(profile_labels)
    )
    trace_params.update(
        {
            "axis_i": int(axis_i),
            "axis_j": int(axis_j),
            "axis_i_label": str(metrics[int(axis_i)]),
            "axis_j_label": str(metrics[int(axis_j)]),
            "answer": answer,
            "answer_type": str(answer_type),
            "annotation_profile_ids": list(annotation_profile_ids),
            "crossing_pairs": [list(pair) for pair in crossing_pairs],
        }
    )
    return _Dataset(
        scene_variant=str(scene_variant),
        metrics=tuple(metrics),
        profiles=profiles,
        query=_Query(
            query_id=str(query_id),
            answer=answer,
            answer_type=str(answer_type),
            axis_i=int(axis_i),
            axis_j=int(axis_j),
            threshold=threshold,
            reference_profile_id=reference_profile_id,
            annotation_profile_ids=tuple(annotation_profile_ids),
            crossing_pairs=tuple(crossing_pairs),
            params=dict(trace_params),
        ),
    )
