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


def build_physics_optics_ray_trace_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_variant: str,
    mirror_count: int,
    target_count: int,
    target_answer: int,
) -> TaskComplexity:
    """Build normalized complexity for optics ray-trace scenes."""

    weights = resolve_physics_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.38 * normalize_linear(float(mirror_count), min_value=1.0, max_value=4.0))
        + (0.30 * normalize_linear(float(target_count), min_value=3.0, max_value=5.0))
        + (
            0.14
            if str(scene_variant) == "quad_mirror"
            else 0.10
            if str(scene_variant) == "triple_mirror"
            else 0.04
            if str(scene_variant) == "double_mirror"
            else 0.0
        )
    )
    path_reasoning = clamp_unit_interval(
        (0.44 if str(query_variant) == "bounce_count" else 0.58)
        + (0.16 * normalize_linear(float(mirror_count), min_value=1.0, max_value=4.0))
        + (0.06 * normalize_linear(float(target_answer), min_value=0.0, max_value=5.0))
    )
    ambiguity = clamp_unit_interval(
        (0.22 * normalize_linear(float(target_count), min_value=3.0, max_value=5.0))
        + (0.16 if int(target_answer) == 0 else 0.0)
    )
    output_burden = normalize_linear(float(target_answer), min_value=0.0, max_value=5.0)
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "path_reasoning": float(path_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_physics_spring_extension_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_variant: str,
    target_answer: int,
    scale_factor: int,
    shown_measurement_count: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for spring-extension proportionality scenes."""

    weights = resolve_physics_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.36 * normalize_linear(float(shown_measurement_count), min_value=1.0, max_value=2.0))
        + (0.16 * normalize_linear(float(evidence_count), min_value=2.0, max_value=4.0))
        + (0.10 if str(scene_variant) == "staggered_springs" else 0.0)
        + (0.14 if str(scene_variant) == "textured_spring" else 0.0)
    )
    variant_reasoning = {
        "extension_difference": 0.00,
        "missing_extension_for_weight": 0.50,
        "missing_weight_for_extension": 1.00,
    }.get(str(query_variant), 1.00)
    proportional_reasoning = clamp_unit_interval(
        float(variant_reasoning)
        + (0.10 * normalize_linear(float(scale_factor), min_value=1.0, max_value=3.0))
        + (0.05 * normalize_linear(float(target_answer), min_value=1.0, max_value=12.0))
    )
    ambiguity = clamp_unit_interval(
        (0.18 if str(query_variant) == "missing_extension_for_weight" else 0.08)
        + (0.12 if str(query_variant) == "missing_weight_for_extension" else 0.0)
        + (0.08 if int(scale_factor) == 1 else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=2.0, max_value=4.0)
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "proportional_reasoning": float(proportional_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_physics_pulley_mechanical_advantage_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_variant: str,
    support_segment_count: int,
    disconnected_segment_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for mechanics pulley-system scenes."""

    weights = resolve_physics_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.34 * normalize_linear(float(support_segment_count), min_value=2.0, max_value=6.0))
        + (0.30 * normalize_linear(float(disconnected_segment_count), min_value=2.0, max_value=6.0))
        + (0.12 if str(scene_variant) == "compact_block" else 0.0)
        + (0.16 if str(scene_variant) == "tall_block" else 0.0)
    )
    pulley_reasoning = clamp_unit_interval(
        0.58
        + (0.16 * normalize_linear(float(support_segment_count), min_value=2.0, max_value=6.0))
        + (0.08 * normalize_linear(float(target_answer), min_value=4.0, max_value=108.0))
        + (0.05 if str(query_variant) == "load_force_from_effort" else 0.0)
    )
    ambiguity = clamp_unit_interval(
        (0.18 * normalize_linear(float(evidence_count), min_value=4.0, max_value=8.0))
        + (0.22 * normalize_linear(float(disconnected_segment_count), min_value=2.0, max_value=6.0))
        + (0.08 if int(support_segment_count) >= 5 else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=4.0, max_value=8.0)
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "pulley_reasoning": float(pulley_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_physics_sticky_collision_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_variant: str,
    component_abs_sum: int,
    total_mass: int,
    option_count: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for perpendicular sticky-collision scenes."""

    weights = resolve_physics_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.26 * normalize_linear(float(option_count), min_value=4.0, max_value=6.0))
        + (0.20 * normalize_linear(float(evidence_count), min_value=1.0, max_value=4.0))
        + (0.10 if str(scene_variant) == "compact_table" else 0.0)
        + (0.12 if str(scene_variant) == "gridded_table" else 0.0)
    )
    collision_reasoning = clamp_unit_interval(
        {
            "direction_choice": 0.54,
            "velocity_component": 0.66,
        }.get(str(query_variant), 0.60)
        + (0.12 * normalize_linear(float(component_abs_sum), min_value=2.0, max_value=12.0))
        + (0.08 * normalize_linear(float(total_mass), min_value=2.0, max_value=12.0))
    )
    ambiguity = clamp_unit_interval(
        (0.12 if str(query_variant) == "direction_choice" else 0.08)
        + (0.14 if int(option_count) >= 6 else 0.0)
        + (0.06 if str(scene_variant) == "compact_table" else 0.0)
    )
    output_burden = clamp_unit_interval(
        0.18 if str(query_variant) == "direction_choice" else 0.52
    )
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "collision_reasoning": float(collision_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_physics_hydraulic_piston_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_variant: str,
    mechanical_advantage: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for hydraulic-piston Pascal-law scenes."""

    weights = resolve_physics_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.32 * normalize_linear(float(evidence_count), min_value=3.0, max_value=4.0))
        + (0.20 * normalize_linear(float(mechanical_advantage), min_value=2.0, max_value=6.0))
        + (0.12 if str(scene_variant) == "compact_frame" else 0.0)
        + (0.14 if str(scene_variant) == "tall_columns" else 0.0)
    )
    pascal_reasoning = clamp_unit_interval(
        {
            "missing_output_force": 0.46,
            "missing_input_force": 0.56,
            "missing_piston_area": 0.64,
        }.get(str(query_variant), 0.56)
        + (0.16 * normalize_linear(float(mechanical_advantage), min_value=2.0, max_value=6.0))
        + (0.08 * normalize_linear(float(target_answer), min_value=4.0, max_value=72.0))
    )
    ambiguity = clamp_unit_interval(
        (0.12 if str(query_variant) == "missing_piston_area" else 0.08)
        + (0.10 if int(mechanical_advantage) in {2, 6} else 0.0)
    )
    output_burden = normalize_linear(float(target_answer), min_value=4.0, max_value=72.0)
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "pascal_reasoning": float(pascal_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_physics_pv_diagram_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_variant: str,
    work_mode: str | None,
    target_sign: str | None,
    work_magnitude: int,
    option_count: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for pressure-volume diagram scenes."""

    weights = resolve_physics_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.24 * normalize_linear(float(option_count), min_value=0.0, max_value=6.0))
        + (0.18 * normalize_linear(float(evidence_count), min_value=1.0, max_value=2.0))
        + (0.10 if str(scene_variant) == "paper_grid" else 0.0)
        + (0.12 if str(scene_variant) == "bold_grid" else 0.0)
    )
    pv_reasoning = clamp_unit_interval(
        {
            "work_value": 0.60,
            "process_sign_choice": 0.40,
        }.get(str(query_variant), 0.50)
        + (0.16 if str(work_mode) == "rectangular_cycle" else 0.0)
        + (0.12 * normalize_linear(float(abs(int(work_magnitude))), min_value=2.0, max_value=70.0))
    )
    ambiguity = clamp_unit_interval(
        (0.16 if str(query_variant) == "process_sign_choice" else 0.10)
        + (0.08 if str(target_sign) == "zero" else 0.0)
        + (0.08 if str(work_mode) == "rectangular_cycle" else 0.0)
    )
    output_burden = 0.22 if str(query_variant) == "process_sign_choice" else normalize_linear(
        float(abs(int(work_magnitude))),
        min_value=2.0,
        max_value=70.0,
    )
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "pv_reasoning": float(pv_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_physics_electrostatics_field_map_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_variant: str,
    direction_mode: str | None,
    charge_count: int,
    option_count: int,
    target_answer_magnitude: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for electrostatics field-map scenes."""

    weights = resolve_physics_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.28 * normalize_linear(float(charge_count), min_value=2.0, max_value=4.0))
        + (0.26 * normalize_linear(float(option_count), min_value=0.0, max_value=8.0))
        + (0.10 if str(scene_variant) == "paper_grid" else 0.0)
        + (0.12 if str(scene_variant) == "dense_grid" else 0.0)
    )
    field_reasoning = clamp_unit_interval(
        {
            "field_direction_choice": 0.58,
            "zero_field_point_label": 0.52,
            "potential_value": 0.64,
        }.get(str(query_variant), 0.56)
        + (0.14 if str(direction_mode) == "force_on_negative_charge" else 0.0)
        + (0.08 * normalize_linear(float(abs(int(target_answer_magnitude))), min_value=0.0, max_value=12.0))
    )
    ambiguity = clamp_unit_interval(
        (0.16 if str(query_variant) in {"field_direction_choice", "zero_field_point_label"} else 0.08)
        + (0.10 if int(option_count) >= 6 else 0.0)
        + (0.08 if int(charge_count) >= 3 else 0.0)
    )
    output_burden = clamp_unit_interval(
        0.24
        if str(query_variant) in {"field_direction_choice", "zero_field_point_label"}
        else normalize_linear(float(abs(int(target_answer_magnitude))), min_value=0.0, max_value=12.0)
    )
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "field_reasoning": float(field_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_physics_magnetism_force_field_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_variant: str,
    charge_sign: int,
    option_count: int,
    target_answer_magnitude: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for magnetism force-field scenes."""

    weights = resolve_physics_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.24 * normalize_linear(float(option_count), min_value=0.0, max_value=8.0))
        + (0.20 * normalize_linear(float(evidence_count), min_value=1.0, max_value=2.0))
        + (0.10 if str(scene_variant) == "field_grid" else 0.0)
        + (0.12 if str(scene_variant) == "lab_card" else 0.0)
    )
    magnetic_reasoning = clamp_unit_interval(
        {
            "force_direction_choice": 0.58,
            "missing_quantity_value": 0.48,
            "circular_path_radius_value": 0.64,
        }.get(str(query_variant), 0.52)
        + (0.12 if int(charge_sign) < 0 and str(query_variant) == "force_direction_choice" else 0.0)
        + (0.08 * normalize_linear(float(abs(int(target_answer_magnitude))), min_value=0.0, max_value=96.0))
    )
    ambiguity = clamp_unit_interval(
        (0.16 if str(query_variant) == "force_direction_choice" else 0.08)
        + (0.10 if int(option_count) >= 6 else 0.0)
        + (0.06 if str(scene_variant) == "field_grid" else 0.0)
    )
    output_burden = clamp_unit_interval(
        0.24
        if str(query_variant) == "force_direction_choice"
        else normalize_linear(float(abs(int(target_answer_magnitude))), min_value=1.0, max_value=96.0)
    )
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "magnetic_reasoning": float(magnetic_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_physics_waves_interference_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_variant: str,
    option_count: int,
    path_difference_steps: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for wave-interference scenes."""

    weights = resolve_physics_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.26 * normalize_linear(float(option_count), min_value=0.0, max_value=8.0))
        + (0.20 * normalize_linear(float(evidence_count), min_value=1.0, max_value=2.0))
        + (0.10 if str(scene_variant) == "grid_tank" else 0.0)
        + (0.12 if str(scene_variant) == "lab_sheet" else 0.0)
    )
    wave_reasoning = clamp_unit_interval(
        {
            "interference_point_choice": 0.62,
            "path_difference_value": 0.56,
        }.get(str(query_variant), 0.56)
        + (0.08 * normalize_linear(float(abs(int(path_difference_steps))), min_value=0.0, max_value=7.0))
    )
    ambiguity = clamp_unit_interval(
        (0.18 if str(query_variant) == "interference_point_choice" else 0.10)
        + (0.10 if int(option_count) >= 6 else 0.0)
        + (0.06 if str(scene_variant) == "grid_tank" else 0.0)
    )
    output_burden = clamp_unit_interval(
        0.24
        if str(query_variant) == "interference_point_choice"
        else normalize_linear(float(abs(int(path_difference_steps))), min_value=1.0, max_value=7.0)
    )
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "wave_reasoning": float(wave_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


__all__ = [
    "build_physics_circuit_resistance_complexity",
    "build_physics_complexity",
    "build_physics_electrostatics_field_map_complexity",
    "build_physics_lever_balance_complexity",
    "build_physics_magnetism_force_field_complexity",
    "build_physics_optics_ray_trace_complexity",
    "build_physics_pv_diagram_complexity",
    "build_physics_pulley_mechanical_advantage_complexity",
    "build_physics_spring_extension_complexity",
    "build_physics_sticky_collision_complexity",
    "build_physics_waves_interference_complexity",
    "clamp_unit_interval",
    "normalize_int_with_bounds",
    "resolve_physics_complexity_weights",
]
