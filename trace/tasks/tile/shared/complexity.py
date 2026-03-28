"""Shared tile-domain helpers for within-task normalized complexity scoring."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from ....core.task_group_config import resolve_task_group_section_defaults
from ....core.types import TaskComplexity


def clamp_unit_interval(value: float) -> float:
    """Clamp one numeric value into the canonical `[0, 1]` interval."""

    return max(0.0, min(1.0, float(value)))


def normalize_int_with_bounds(value: int, bounds: Sequence[int]) -> float:
    """Normalize one integer difficulty knob over an inclusive integer range."""

    if len(bounds) < 2:
        raise ValueError("tile complexity bounds must contain at least two values")
    lower = int(bounds[0])
    upper = int(bounds[1])
    if int(upper) <= int(lower):
        return 0.0
    return clamp_unit_interval((float(value) - float(lower)) / (float(upper) - float(lower)))


def normalize_float_with_bounds(value: float, bounds: Sequence[float]) -> float:
    """Normalize one float difficulty knob over an inclusive numeric range."""

    if len(bounds) < 2:
        raise ValueError("tile complexity float bounds must contain at least two values")
    lower = float(bounds[0])
    upper = float(bounds[1])
    if float(upper) <= float(lower):
        return 0.0
    return clamp_unit_interval((float(value) - float(lower)) / (float(upper) - float(lower)))


def resolve_tile_complexity_weights(
    task_group_defaults: Mapping[str, Any],
    *,
    task_id: str,
) -> Dict[str, float]:
    """Resolve active tile-complexity weights for one task."""

    defaults = resolve_task_group_section_defaults(task_group_defaults, "complexity", task_id=task_id)
    raw_weights = defaults.get("criteria_weights", {})
    if not isinstance(raw_weights, Mapping):
        raise ValueError(f"complexity.criteria_weights must be a mapping for {task_id}")

    weights: Dict[str, float] = {}
    for criterion, raw_weight in raw_weights.items():
        weight = float(raw_weight)
        if float(weight) < 0.0:
            raise ValueError(f"complexity weight for '{criterion}' in {task_id} must be non-negative")
        if float(weight) == 0.0:
            continue
        weights[str(criterion)] = float(weight)
    if not weights:
        raise ValueError(f"missing positive tile complexity weights for {task_id}")
    return weights


def build_tile_complexity(
    *,
    weights: Mapping[str, float],
    components: Mapping[str, float],
) -> TaskComplexity:
    """Build a normalized tile `TaskComplexity` record from weighted criteria."""

    active_weights = {str(key): float(value) for key, value in weights.items() if float(value) > 0.0}
    if not active_weights:
        raise ValueError("tile complexity requires at least one positive active weight")

    normalized_components = {str(key): clamp_unit_interval(float(value)) for key, value in components.items()}
    missing = [criterion for criterion in active_weights if criterion not in normalized_components]
    if missing:
        raise ValueError(f"tile complexity is missing active criteria: {missing}")

    total_weight = sum(active_weights.values())
    if float(total_weight) <= 0.0:
        raise ValueError("tile complexity active weights must sum to a positive value")

    score = sum(
        float(active_weights[criterion]) * float(normalized_components[criterion])
        for criterion in active_weights
    ) / float(total_weight)
    return TaskComplexity(
        complexity_score=clamp_unit_interval(float(score)),
        complexity_components={criterion: float(normalized_components[criterion]) for criterion in active_weights},
    )


__all__ = [
    "build_tile_complexity",
    "clamp_unit_interval",
    "normalize_float_with_bounds",
    "normalize_int_with_bounds",
    "resolve_tile_complexity_weights",
]
