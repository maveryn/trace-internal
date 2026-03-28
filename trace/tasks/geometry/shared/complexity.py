"""Shared geometry-domain helpers for within-task normalized complexity scoring.

This module follows the repo complexity policy:
- tasks emit normalized criterion values in `[0, 1]`,
- domain/task-group/task config owns active criteria and weights,
- final `complexity_score` is the normalized weighted mean over active criteria.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ....core.task_group_config import resolve_task_group_section_defaults
from ....core.types import TaskComplexity


def clamp_unit_interval(value: float) -> float:
    """Clamp one numeric value into the canonical `[0, 1]` interval."""

    return max(0.0, min(1.0, float(value)))


def normalize_linear(value: float, *, min_value: float, max_value: float) -> float:
    """Normalize one scalar linearly into `[0, 1]`."""

    lower = float(min_value)
    upper = float(max_value)
    if upper <= lower:
        return 0.0
    return clamp_unit_interval((float(value) - lower) / (upper - lower))


def resolve_geometry_complexity_weights(
    task_group_defaults: Mapping[str, Any],
    *,
    task_id: str,
) -> Dict[str, float]:
    """Resolve active geometry-complexity weights for one task."""

    defaults = resolve_task_group_section_defaults(task_group_defaults, "complexity", task_id=task_id)
    raw_weights = defaults.get("criteria_weights", {})
    if not isinstance(raw_weights, Mapping):
        raise ValueError(f"complexity.criteria_weights must be a mapping for {task_id}")

    weights: Dict[str, float] = {}
    for criterion, raw_weight in raw_weights.items():
        name = str(criterion).strip()
        if not name:
            continue
        weight = float(raw_weight)
        if weight < 0.0:
            raise ValueError(f"complexity weight for '{name}' in {task_id} must be non-negative")
        if weight == 0.0:
            continue
        weights[name] = weight
    if not weights:
        raise ValueError(f"missing positive geometry complexity weights for {task_id}")
    return weights


def build_geometry_task_complexity(
    *,
    weights: Mapping[str, float],
    components: Mapping[str, float],
) -> TaskComplexity:
    """Build one normalized geometry `TaskComplexity` record."""

    active_weights = {str(key): float(value) for key, value in weights.items() if float(value) > 0.0}
    if not active_weights:
        raise ValueError("geometry complexity requires at least one positive active weight")

    normalized_components = {str(key): clamp_unit_interval(float(value)) for key, value in components.items()}
    missing = [criterion for criterion in active_weights if criterion not in normalized_components]
    if missing:
        raise ValueError(f"geometry complexity is missing active criteria: {missing}")

    total_weight = sum(active_weights.values())
    if float(total_weight) <= 0.0:
        raise ValueError("geometry complexity active weights must sum to a positive value")

    score = sum(
        float(active_weights[criterion]) * float(normalized_components[criterion])
        for criterion in active_weights
    ) / float(total_weight)
    return TaskComplexity(
        complexity_score=clamp_unit_interval(score),
        complexity_components={criterion: float(normalized_components[criterion]) for criterion in active_weights},
    )


def geometry_visual_scan_score(
    *,
    object_count: int,
    object_count_min: int,
    object_count_max: int,
) -> float:
    """Normalize visual scan load from active object-count support."""

    return normalize_linear(
        float(object_count),
        min_value=float(object_count_min),
        max_value=float(object_count_max),
    )


def geometry_gap_ambiguity_score(
    *,
    gap_normalized: float,
    min_normalized_gap: float,
) -> float:
    """Normalize comparison ambiguity so smaller winner gaps score harder."""

    return clamp_unit_interval(
        1.0
        - normalize_linear(
            float(gap_normalized),
            min_value=float(min_normalized_gap),
            max_value=1.0,
        )
    )


def geometry_graph_point_output_burden(*, evidence_point_count: int) -> float:
    """Normalize geometry output burden from graph-point evidence cardinality."""

    return normalize_linear(
        float(evidence_point_count),
        min_value=2.0,
        max_value=4.0,
    )


def geometry_comparison_reasoning_score(comparison_kind: str) -> float:
    """Return normalized family-local reasoning load for comparison quantities."""

    normalized_kind = str(comparison_kind).strip().lower()
    score_by_kind = {
        "length": 0.35,
        "angle": 0.45,
        "perimeter": 0.70,
        "area": 0.80,
    }
    if normalized_kind not in score_by_kind:
        raise ValueError(f"unsupported geometry comparison kind: {comparison_kind}")
    return float(score_by_kind[normalized_kind])


def build_geometry_comparison_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    object_count: int,
    object_count_min: int,
    object_count_max: int,
    gap_normalized: float,
    min_normalized_gap: float,
    comparison_kind: str,
    evidence_point_count: int,
) -> TaskComplexity:
    """Build one normalized comparison-family complexity payload."""

    weights = resolve_geometry_complexity_weights(task_group_defaults, task_id=task_id)
    return build_geometry_task_complexity(
        weights=weights,
        components={
            "visual_scan": geometry_visual_scan_score(
                object_count=int(object_count),
                object_count_min=int(object_count_min),
                object_count_max=int(object_count_max),
            ),
            "comparison_reasoning": geometry_comparison_reasoning_score(str(comparison_kind)),
            "ambiguity": geometry_gap_ambiguity_score(
                gap_normalized=float(gap_normalized),
                min_normalized_gap=float(min_normalized_gap),
            ),
            "output_burden": geometry_graph_point_output_burden(
                evidence_point_count=int(evidence_point_count),
            ),
        },
    )


__all__ = [
    "build_geometry_comparison_complexity",
    "build_geometry_task_complexity",
    "clamp_unit_interval",
    "geometry_comparison_reasoning_score",
    "geometry_gap_ambiguity_score",
    "geometry_graph_point_output_burden",
    "geometry_visual_scan_score",
    "normalize_linear",
    "resolve_geometry_complexity_weights",
]
