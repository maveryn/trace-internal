"""Shared helpers for geometry/counting task modules."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.sampling import normalize_positive_weights, weighted_choice
from ...shared.deterministic_sampling import resolve_selection_index
from ..shared.variant_sampling import has_non_null_param, is_uniform_probability_map

COUNTING_LABEL_POOL: Tuple[str, ...] = tuple("ABCDEFGHIJKL")


def resolve_counting_object_count(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, Dict[str, float]]:
    """Resolve how many labeled objects appear in one counting scene."""

    min_count = int(params.get("object_count_min", gen_defaults.get("object_count_min", int(fallback_min))))
    max_count = int(params.get("object_count_max", gen_defaults.get("object_count_max", int(fallback_max))))
    if min_count < 2 or min_count > max_count:
        raise ValueError("invalid object_count_min/object_count_max for counting task")
    supported_counts = [int(value) for value in range(int(min_count), int(max_count) + 1)]

    explicit = params.get("object_count")
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(supported_counts):
            raise ValueError("object_count is outside configured supported range")
        return int(selected), {
            str(value): (1.0 if int(value) == int(selected) else 0.0)
            for value in supported_counts
        }

    raw_weights = params.get(
        "object_count_weights",
        gen_defaults.get("object_count_weights", {str(value): 1.0 for value in supported_counts}),
    )
    if not isinstance(raw_weights, Mapping):
        raise ValueError("object_count_weights must be a mapping when provided")
    weights = {
        str(key): float(value)
        for key, value in raw_weights.items()
        if str(key) in {str(value) for value in supported_counts}
    }
    probabilities = normalize_positive_weights(weights, default_keys=[str(value) for value in supported_counts])
    selected = int(weighted_choice(rng, probabilities, sort_keys=True))

    enabled = bool(params.get("balanced_sampling", gen_defaults.get("balanced_sampling", True)))
    overridden = any(has_non_null_param(params, key) for key in ("object_count", "object_count_weights"))
    if bool(enabled) and (not overridden) and is_uniform_probability_map(probabilities):
        selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace="counting_object_count",
        )
        selected = int(supported_counts[int(selection_index) % len(supported_counts)])
    return int(selected), {
        str(key): float(value)
        for key, value in sorted(probabilities.items(), key=lambda item: int(item[0]))
    }


def resolve_counting_target_count(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    object_count: int,
    default_min: int = 1,
    default_margin_from_total: int = 1,
) -> Tuple[int, Dict[str, float]]:
    """Resolve how many objects match the queried class in one counting scene."""

    min_count = int(params.get("target_count_min", gen_defaults.get("target_count_min", int(default_min))))
    max_default = max(int(default_min), int(object_count) - int(default_margin_from_total))
    max_count = int(params.get("target_count_max", gen_defaults.get("target_count_max", int(max_default))))
    min_count = max(0, int(min_count))
    max_count = min(int(object_count), int(max_count))
    if min_count > max_count:
        raise ValueError("invalid target_count_min/target_count_max for counting task")
    supported_counts = [int(value) for value in range(int(min_count), int(max_count) + 1)]
    if not supported_counts:
        raise ValueError("counting task resolved no supported target counts")

    explicit = params.get("target_count")
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(supported_counts):
            raise ValueError("target_count is outside configured supported range")
        return int(selected), {
            str(value): (1.0 if int(value) == int(selected) else 0.0)
            for value in supported_counts
        }

    raw_weights = params.get(
        "target_count_weights",
        gen_defaults.get("target_count_weights", {str(value): 1.0 for value in supported_counts}),
    )
    if not isinstance(raw_weights, Mapping):
        raise ValueError("target_count_weights must be a mapping when provided")
    weights = {
        str(key): float(value)
        for key, value in raw_weights.items()
        if str(key) in {str(value) for value in supported_counts}
    }
    probabilities = normalize_positive_weights(weights, default_keys=[str(value) for value in supported_counts])
    selected = int(weighted_choice(rng, probabilities, sort_keys=True))

    enabled = bool(params.get("balanced_sampling", gen_defaults.get("balanced_sampling", True)))
    overridden = any(has_non_null_param(params, key) for key in ("target_count", "target_count_weights"))
    if bool(enabled) and (not overridden) and is_uniform_probability_map(probabilities):
        selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"counting_target_count_{int(object_count)}",
        )
        selected = int(supported_counts[int(selection_index) % len(supported_counts)])
    return int(selected), {
        str(key): float(value)
        for key, value in sorted(probabilities.items(), key=lambda item: int(item[0]))
    }


def resolve_counting_cardinality_pair(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    fallback_object_min: int,
    fallback_object_max: int,
    default_target_min: int = 1,
    default_margin_from_total: int = 1,
) -> Tuple[int, Dict[str, float], int, Dict[str, float]]:
    """Resolve one `(object_count, target_count)` pair with flatter count answers.

    Counting tasks often use the integer count itself as the final answer. If we
    always choose `object_count` first and then balance `target_count` only
    within that one scene size, smaller counts become overrepresented whenever
    multiple object-count values are feasible. This helper samples the count
    answer from the global feasible support first when defaults are in play, and
    then chooses a compatible object count.
    """

    min_object = int(params.get("object_count_min", gen_defaults.get("object_count_min", int(fallback_object_min))))
    max_object = int(params.get("object_count_max", gen_defaults.get("object_count_max", int(fallback_object_max))))
    if min_object < 2 or min_object > max_object:
        raise ValueError("invalid object_count_min/object_count_max for counting task")
    supported_object_counts = [int(value) for value in range(int(min_object), int(max_object) + 1)]

    min_target = int(params.get("target_count_min", gen_defaults.get("target_count_min", int(default_target_min))))
    max_default = max(int(default_target_min), int(max_object) - int(default_margin_from_total))
    max_target = int(params.get("target_count_max", gen_defaults.get("target_count_max", int(max_default))))
    min_target = max(0, int(min_target))
    max_target = min(int(max_object), int(max_target))
    supported_target_counts = [
        int(value)
        for value in range(int(min_target), int(max_target) + 1)
        if any(int(obj) - int(default_margin_from_total) >= int(value) for obj in supported_object_counts)
    ]
    if not supported_target_counts:
        raise ValueError("counting task resolved no globally feasible target counts")

    explicit_object = params.get("object_count")
    explicit_target = params.get("target_count")
    if explicit_object is not None and explicit_target is not None:
        object_count = int(explicit_object)
        target_count = int(explicit_target)
        if int(object_count) not in set(supported_object_counts):
            raise ValueError("object_count is outside configured supported range")
        feasible_targets = [
            int(value)
            for value in supported_target_counts
            if int(value) <= int(object_count) - int(default_margin_from_total)
        ]
        if int(target_count) not in set(feasible_targets):
            raise ValueError("target_count is outside configured supported range")
        return (
            int(object_count),
            {
                str(value): (1.0 if int(value) == int(object_count) else 0.0)
                for value in supported_object_counts
            },
            int(target_count),
            {
                str(value): (1.0 if int(value) == int(target_count) else 0.0)
                for value in supported_target_counts
            },
        )

    if explicit_object is not None:
        object_count = int(explicit_object)
        if int(object_count) not in set(supported_object_counts):
            raise ValueError("object_count is outside configured supported range")
        target_count, target_probabilities = resolve_counting_target_count(
            rng,
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
            object_count=int(object_count),
            default_min=int(default_target_min),
            default_margin_from_total=int(default_margin_from_total),
        )
        return (
            int(object_count),
            {
                str(value): (1.0 if int(value) == int(object_count) else 0.0)
                for value in supported_object_counts
            },
            int(target_count),
            dict(target_probabilities),
        )

    enabled = bool(params.get("balanced_sampling", gen_defaults.get("balanced_sampling", True)))
    target_weights_raw = params.get(
        "target_count_weights",
        gen_defaults.get("target_count_weights", {str(value): 1.0 for value in supported_target_counts}),
    )
    if not isinstance(target_weights_raw, Mapping):
        raise ValueError("target_count_weights must be a mapping when provided")
    target_weights = {
        str(key): float(value)
        for key, value in target_weights_raw.items()
        if str(key) in {str(value) for value in supported_target_counts}
    }
    target_probabilities = normalize_positive_weights(
        target_weights,
        default_keys=[str(value) for value in supported_target_counts],
    )

    if explicit_target is not None:
        target_count = int(explicit_target)
        if int(target_count) not in set(supported_target_counts):
            raise ValueError("target_count is outside configured supported range")
    else:
        target_count = int(weighted_choice(rng, target_probabilities, sort_keys=True))
        target_overridden = any(has_non_null_param(params, key) for key in ("target_count", "target_count_weights"))
        if bool(enabled) and (not target_overridden) and is_uniform_probability_map(target_probabilities):
            selection_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace="counting_global_target_count",
            )
            target_count = int(supported_target_counts[int(selection_index) % len(supported_target_counts)])

    feasible_object_counts = [
        int(value)
        for value in supported_object_counts
        if int(value) - int(default_margin_from_total) >= int(target_count)
    ]
    if not feasible_object_counts:
        raise ValueError("counting task resolved no feasible object counts for selected target_count")
    object_weights_raw = params.get(
        "object_count_weights",
        gen_defaults.get("object_count_weights", {str(value): 1.0 for value in supported_object_counts}),
    )
    if not isinstance(object_weights_raw, Mapping):
        raise ValueError("object_count_weights must be a mapping when provided")
    object_weights = {
        str(key): float(value)
        for key, value in object_weights_raw.items()
        if str(key) in {str(value) for value in feasible_object_counts}
    }
    object_probabilities = normalize_positive_weights(
        object_weights,
        default_keys=[str(value) for value in feasible_object_counts],
    )
    object_count = int(weighted_choice(rng, object_probabilities, sort_keys=True))
    object_overridden = any(has_non_null_param(params, key) for key in ("object_count", "object_count_weights"))
    if bool(enabled) and (not object_overridden) and is_uniform_probability_map(object_probabilities):
        selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"counting_object_count_for_target_{int(target_count)}",
        )
        object_count = int(feasible_object_counts[int(selection_index) % len(feasible_object_counts)])

    return (
        int(object_count),
        {
            str(key): float(value)
            for key, value in sorted(object_probabilities.items(), key=lambda item: int(item[0]))
        },
        int(target_count),
        {
            str(key): float(value)
            for key, value in sorted(target_probabilities.items(), key=lambda item: int(item[0]))
        },
    )


def assign_counting_labels(rng, *, object_count: int, label_pool: Sequence[str] = COUNTING_LABEL_POOL) -> Tuple[str, ...]:
    """Assign one shuffled subset of object labels for a counting scene."""

    if int(object_count) > len(label_pool):
        raise ValueError("object_count exceeds available counting labels")
    labels = [str(label) for label in label_pool[: int(object_count)]]
    rng.shuffle(labels)
    return tuple(str(label) for label in labels)


def counting_complexity_score(*, object_count: int, target_count: int) -> float:
    """Return one lightweight complexity proxy for counting scenes."""

    count_factor = min(1.0, max(0.0, (float(object_count) - 4.0) / 6.0))
    density = float(target_count) / float(max(1, int(object_count)))
    density_factor = 1.0 - abs(float(density) - 0.5) * 2.0
    return max(0.0, min(1.0, 0.34 + (0.28 * count_factor) + (0.24 * density_factor)))


__all__ = [
    "COUNTING_LABEL_POOL",
    "assign_counting_labels",
    "resolve_counting_cardinality_pair",
    "counting_complexity_score",
    "resolve_counting_object_count",
    "resolve_counting_target_count",
]
