"""Shared helpers for geometry/comparison task modules."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.sampling import normalize_positive_weights, weighted_choice
from ...shared.deterministic_sampling import resolve_selection_index
from ..shared.graph_rendering import graph_units_to_pixel
from ...shared.variant_sampling import has_non_null_param, is_uniform_probability_map

COMPARISON_QUERY_TYPES: Tuple[str, str] = ("largest", "smallest")
COMPARISON_ANSWER_LABEL_POOL: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")


def resolve_comparison_query_type(
    rng,
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve comparison query type with weighted defaults."""

    explicit = params.get("query_type")
    if explicit is not None:
        selected = str(explicit).strip().lower()
        if selected not in set(COMPARISON_QUERY_TYPES):
            raise ValueError(f"unsupported query_type: {selected}")
        return selected, {
            key: (1.0 if key == selected else 0.0)
            for key in sorted(COMPARISON_QUERY_TYPES)
        }

    raw_weights = params.get(
        "query_type_weights",
        gen_defaults.get("query_type_weights", {key: 1.0 for key in COMPARISON_QUERY_TYPES}),
    )
    if not isinstance(raw_weights, Mapping):
        raise ValueError("query_type_weights must be a mapping when provided")
    weights = {
        str(key): float(value)
        for key, value in raw_weights.items()
        if str(key) in set(COMPARISON_QUERY_TYPES)
    }
    probabilities = normalize_positive_weights(
        weights,
        default_keys=COMPARISON_QUERY_TYPES,
    )
    selected = weighted_choice(rng, probabilities, sort_keys=True)
    return str(selected), {
        str(key): float(value) for key, value in sorted(probabilities.items())
    }


def resolve_comparison_object_count(
    rng,
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, Dict[str, float]]:
    """Resolve how many compared objects appear in the scene."""

    min_count = int(params.get("object_count_min", gen_defaults.get("object_count_min", int(fallback_min))))
    max_count = int(params.get("object_count_max", gen_defaults.get("object_count_max", int(fallback_max))))
    if min_count < 2 or min_count > max_count:
        raise ValueError("invalid object_count_min/object_count_max for comparison task")
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
    probabilities = normalize_positive_weights(
        weights,
        default_keys=[str(value) for value in supported_counts],
    )
    selected = int(weighted_choice(rng, probabilities, sort_keys=True))
    return int(selected), {
        str(key): float(value)
        for key, value in sorted(probabilities.items(), key=lambda item: int(item[0]))
    }


def resolve_comparison_winner_label(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    label_pool: Sequence[str] = COMPARISON_ANSWER_LABEL_POOL,
    selection_namespace: str = "comparison_winner_label",
) -> Tuple[str, Dict[str, float]]:
    """Resolve the intended winning answer label for one comparison scene."""

    normalized_pool = tuple(str(label).upper() for label in label_pool)
    explicit = params.get("winner_label")
    if explicit is not None:
        selected = str(explicit).strip().upper()
        if selected not in set(normalized_pool):
            raise ValueError(f"unsupported winner_label: {selected}")
        return selected, {
            key: (1.0 if key == selected else 0.0)
            for key in normalized_pool
        }

    raw_weights = params.get("winner_label_weights", {key: 1.0 for key in normalized_pool})
    if not isinstance(raw_weights, Mapping):
        raise ValueError("winner_label_weights must be a mapping when provided")
    weights = {
        str(key).upper(): float(value)
        for key, value in raw_weights.items()
        if str(key).upper() in set(normalized_pool)
    }
    probabilities = normalize_positive_weights(weights, default_keys=normalized_pool)
    selected = str(weighted_choice(rng, probabilities, sort_keys=True)).upper()

    enabled = bool(params.get("balanced_sampling", gen_defaults.get("balanced_sampling", True)))
    overridden = any(has_non_null_param(params, key) for key in ("winner_label", "winner_label_weights"))
    if bool(enabled) and (not overridden) and is_uniform_probability_map(probabilities):
        sampling_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(selection_namespace),
        )
        selected = str(normalized_pool[int(sampling_index) % len(normalized_pool)])
    return selected, {
        str(key): float(value) for key, value in sorted(probabilities.items())
    }


def apply_balanced_comparison_axes(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_type: str,
    query_type_probabilities: Mapping[str, float],
    object_count: int,
    object_count_probabilities: Mapping[str, float],
    query_types: Sequence[str] = COMPARISON_QUERY_TYPES,
) -> Tuple[str, Dict[str, float], int, Dict[str, float]]:
    """Apply deterministic balanced defaults over query type and object count."""

    enabled = bool(params.get("balanced_sampling", True))
    resolved_query = str(query_type)
    resolved_count = int(object_count)
    query_probs = {str(key): float(value) for key, value in query_type_probabilities.items()}
    count_probs = {str(key): float(value) for key, value in object_count_probabilities.items()}
    if not bool(enabled):
        return resolved_query, query_probs, resolved_count, count_probs

    sampling_index = abs(int(params.get("_sampling_index", instance_seed)))
    query_overridden = any(has_non_null_param(params, key) for key in ("query_type", "query_type_weights"))
    if (not query_overridden) and is_uniform_probability_map(query_probs):
        resolved_query = str(query_types[int(sampling_index) % len(tuple(query_types))])

    count_overridden = any(has_non_null_param(params, key) for key in ("object_count", "object_count_weights"))
    sorted_counts = [int(value) for value in sorted((int(key) for key in count_probs.keys()))]
    if (not count_overridden) and is_uniform_probability_map(count_probs) and sorted_counts:
        count_index = int(sampling_index // max(1, len(tuple(query_types)))) % len(sorted_counts)
        resolved_count = int(sorted_counts[count_index])

    return resolved_query, query_probs, resolved_count, count_probs


def comparison_complexity_score(*, object_count: int, gap_normalized: float) -> float:
    """Return one lightweight complexity proxy for comparison scenes."""

    count_factor = min(1.0, max(0.0, (float(object_count) - 4.0) / 2.0))
    ambiguity_factor = 1.0 - min(1.0, max(0.0, float(gap_normalized)))
    return max(0.0, min(1.0, 0.38 + (0.22 * count_factor) + (0.34 * ambiguity_factor)))


def slot_centers_graph_units(*, object_count: int, graph_cells: int, rng) -> List[Tuple[int, int]]:
    """Resolve a subset of well-separated graph-unit slot centers."""

    half_span = max(6, int(graph_cells // 2))
    x_step = min(max(4, int(round(float(graph_cells) * 0.26))), max(4, int(half_span - 3)))
    y_step = min(max(4, int(round(float(graph_cells) * 0.20))), max(4, int(half_span - 3)))
    all_slots = [
        (-int(x_step), int(y_step)),
        (0, int(y_step)),
        (int(x_step), int(y_step)),
        (-int(x_step), -int(y_step)),
        (0, -int(y_step)),
        (int(x_step), -int(y_step)),
    ]
    rng.shuffle(all_slots)
    return list(all_slots[: int(object_count)])


def bulky_slot_centers_graph_units(
    *,
    object_count: int,
    graph_cells: int,
    rng,
) -> List[Tuple[int, int]]:
    """Resolve a roomier subset of graph-unit slot centers for bulky objects.

    Comparison tasks over area/perimeter tend to need larger footprints than
    angle or segment scenes, so they use a wider two-column slot bank.
    """

    half_span = max(8, int(graph_cells // 2))
    x_step = min(max(6, int(round(float(graph_cells) * 0.34))), max(6, int(half_span - 3)))
    y_step = min(max(5, int(round(float(graph_cells) * 0.30))), max(5, int(half_span - 3)))
    all_slots = [
        (-int(x_step), int(y_step)),
        (int(x_step), int(y_step)),
        (-int(x_step), 0),
        (int(x_step), 0),
        (-int(x_step), -int(y_step)),
        (int(x_step), -int(y_step)),
    ]
    rng.shuffle(all_slots)
    return list(all_slots[: int(object_count)])


__all__ = [
    "COMPARISON_ANSWER_LABEL_POOL",
    "COMPARISON_QUERY_TYPES",
    "apply_balanced_comparison_axes",
    "bulky_slot_centers_graph_units",
    "comparison_complexity_score",
    "graph_units_to_pixel",
    "resolve_comparison_object_count",
    "resolve_comparison_query_type",
    "resolve_comparison_winner_label",
    "slot_centers_graph_units",
]
