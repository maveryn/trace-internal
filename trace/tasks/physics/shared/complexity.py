"""Shared normalized complexity helpers for physics-domain tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from ....core.task_group_config import resolve_task_group_section_defaults
from ....core.types import TaskComplexity


def clamp_unit_interval(value: float) -> float:
    """Clamp one numeric value into the canonical `[0, 1]` interval."""

    return max(0.0, min(1.0, float(value)))


def normalize_linear(value: float, *, min_value: float, max_value: float) -> float:
    """Normalize one value over an inclusive numeric interval."""

    lower = float(min_value)
    upper = float(max_value)
    if float(upper) <= float(lower):
        return 0.0
    return clamp_unit_interval((float(value) - float(lower)) / (float(upper) - float(lower)))


def normalize_int_with_bounds(value: int, bounds: Sequence[int]) -> float:
    """Normalize one integer difficulty knob over inclusive integer bounds."""

    if len(bounds) < 2:
        raise ValueError("physics complexity bounds must contain at least two values")
    return normalize_linear(float(value), min_value=float(bounds[0]), max_value=float(bounds[1]))


def resolve_physics_complexity_weights(
    task_group_defaults: Mapping[str, Any],
    *,
    task_id: str,
) -> Dict[str, float]:
    """Resolve active physics-complexity weights for one task."""

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
        raise ValueError(f"missing positive physics complexity weights for {task_id}")
    return weights


def build_physics_complexity(
    *,
    weights: Mapping[str, float],
    components: Mapping[str, float],
) -> TaskComplexity:
    """Build one normalized weighted `TaskComplexity` payload."""

    active_weights = {str(key): float(value) for key, value in weights.items() if float(value) > 0.0}
    if not active_weights:
        raise ValueError("physics complexity requires at least one positive active weight")
    normalized_components = {str(key): clamp_unit_interval(float(value)) for key, value in components.items()}
    missing = [criterion for criterion in active_weights if criterion not in normalized_components]
    if missing:
        raise ValueError(f"physics complexity is missing active criteria: {missing}")
    total_weight = sum(active_weights.values())
    score = sum(
        float(active_weights[criterion]) * float(normalized_components[criterion])
        for criterion in active_weights
    ) / float(total_weight)
    return TaskComplexity(
        complexity_score=clamp_unit_interval(float(score)),
        complexity_components={criterion: float(normalized_components[criterion]) for criterion in active_weights},
    )


def build_physics_force_diagram_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_variant: str,
    arrow_count: int,
    relevant_arrow_count: int,
    target_force: int,
) -> TaskComplexity:
    """Build normalized complexity for mechanics force-diagram scenes."""

    weights = resolve_physics_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.70 * normalize_linear(float(arrow_count), min_value=2.0, max_value=6.0))
        + (0.12 if str(scene_variant) == "surface_block" else 0.0)
        + (0.08 if str(scene_variant) == "textured_block" else 0.0)
    )
    force_reasoning = clamp_unit_interval(
        (0.42 if str(query_variant).startswith("net_") else 0.58)
        + (0.16 if str(scene_variant) == "surface_block" else 0.0)
        + (0.06 * normalize_linear(float(target_force), min_value=0.0, max_value=12.0))
    )
    ambiguity = clamp_unit_interval(
        (0.45 * normalize_linear(float(relevant_arrow_count), min_value=2.0, max_value=4.0))
        + (0.25 if int(target_force) == 0 else 0.0)
    )
    output_burden = normalize_linear(float(relevant_arrow_count), min_value=2.0, max_value=4.0)
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "force_reasoning": float(force_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_physics_lever_balance_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_variant: str,
    weight_count: int,
    relevant_weight_count: int,
    max_distance: int,
    target_answer: int,
) -> TaskComplexity:
    """Build normalized complexity for mechanics lever-balance scenes."""

    weights = resolve_physics_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.55 * normalize_linear(float(weight_count), min_value=2.0, max_value=4.0))
        + (0.14 if str(scene_variant) == "offset_fulcrum" else 0.0)
        + (0.10 if str(scene_variant) == "textured_beam" else 0.0)
    )
    torque_reasoning = clamp_unit_interval(
        (0.42 if str(query_variant) in {"left_torque", "right_torque"} else 0.62)
        + (0.14 * normalize_linear(float(max_distance), min_value=1.0, max_value=4.0))
        + (0.08 * normalize_linear(float(target_answer), min_value=1.0, max_value=24.0))
    )
    ambiguity = clamp_unit_interval(
        (0.35 * normalize_linear(float(relevant_weight_count), min_value=1.0, max_value=2.0))
        + (0.15 if str(query_variant) == "missing_weight_to_balance" else 0.0)
    )
    output_burden = normalize_linear(float(relevant_weight_count), min_value=1.0, max_value=2.0)
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "torque_reasoning": float(torque_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_physics_circuit_resistance_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_variant: str,
    resistor_count: int,
    target_answer: int,
) -> TaskComplexity:
    """Build normalized complexity for resistor-network equivalent-resistance scenes."""

    weights = resolve_physics_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.48 * normalize_linear(float(resistor_count), min_value=3.0, max_value=8.0))
        + (0.12 if str(scene_variant) == "parallel" else 0.0)
        + (0.18 if str(scene_variant) == "simple_series_parallel" else 0.0)
        + (0.12 if str(query_variant) == "missing_resistor_value" else 0.0)
    )
    circuit_reasoning = clamp_unit_interval(
        (0.56 if str(scene_variant) == "parallel" else 0.70)
        + (0.10 * normalize_linear(float(target_answer), min_value=1.0, max_value=18.0))
        + (0.14 if str(query_variant) == "missing_resistor_value" else 0.0)
    )
    ambiguity = clamp_unit_interval(
        (0.28 if str(scene_variant) == "parallel" else 0.10)
        + (0.10 if int(target_answer) <= 2 else 0.0)
        + (0.08 if str(query_variant) == "missing_resistor_value" else 0.0)
    )
    output_burden = normalize_linear(float(1 if str(query_variant) == "missing_resistor_value" else resistor_count), min_value=1.0, max_value=8.0)
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "circuit_reasoning": float(circuit_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


__all__ = [
    "build_physics_circuit_resistance_complexity",
    "build_physics_complexity",
    "build_physics_force_diagram_complexity",
    "build_physics_lever_balance_complexity",
    "clamp_unit_interval",
    "normalize_int_with_bounds",
    "resolve_physics_complexity_weights",
]
