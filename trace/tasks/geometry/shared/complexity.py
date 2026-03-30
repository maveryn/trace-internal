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


def geometry_counting_density_balance(*, target_count: int, object_count: int) -> float:
    """Return one target-density factor that peaks near an even class split."""

    if int(object_count) <= 0:
        return 0.0
    density = float(target_count) / float(max(1, int(object_count)))
    return clamp_unit_interval(1.0 - abs((2.0 * density) - 1.0))


def geometry_label_set_output_burden(*, target_count: int, object_count: int) -> float:
    """Normalize output burden from label-set evidence size."""

    max_targets = max(1, int(object_count) - 1)
    return normalize_linear(
        float(target_count),
        min_value=1.0,
        max_value=float(max_targets),
    )


def geometry_measurement_output_burden(*, answer_format: str, evidence_point_count: int) -> float:
    """Normalize output burden for single-object measurement tasks."""

    return geometry_answer_format_output_burden(
        answer_format=str(answer_format),
        evidence_count=int(evidence_point_count),
        evidence_count_min=1,
        evidence_count_max=5,
    )


def geometry_answer_format_output_burden(
    *,
    answer_format: str,
    evidence_count: int,
    evidence_count_min: int,
    evidence_count_max: int,
) -> float:
    """Normalize output burden from answer-format precision plus evidence cardinality."""

    normalized_answer_format = str(answer_format).strip().lower()
    answer_format_load = {
        "integer": 0.25,
        "number": 0.50,
        "pi_expression": 0.70,
    }.get(normalized_answer_format)
    if answer_format_load is None:
        raise ValueError(f"unsupported geometry measurement answer_format: {answer_format}")
    evidence_load = normalize_linear(
        float(evidence_count),
        min_value=float(evidence_count_min),
        max_value=float(evidence_count_max),
    )
    return clamp_unit_interval((0.65 * float(answer_format_load)) + (0.35 * float(evidence_load)))


def geometry_analytical_output_burden(*, answer_format: str, evidence_ref_count: int) -> float:
    """Normalize output burden for analytical geometry tasks with measurement-map evidence."""

    return geometry_answer_format_output_burden(
        answer_format=str(answer_format),
        evidence_count=int(evidence_ref_count),
        evidence_count_min=1,
        evidence_count_max=4,
    )


def geometry_counting_classification_reasoning_score(*, task_kind: str, task_variant: str) -> float:
    """Return normalized reasoning load for one geometry counting class."""

    normalized_kind = str(task_kind).strip().lower()
    normalized_variant = str(task_variant).strip().lower()
    score_by_kind = {
        "angle": {
            "acute_angle": 0.30,
            "right_angle": 0.55,
            "obtuse_angle": 0.35,
        },
        "triangle": {
            "equilateral_triangle": 0.30,
            "isosceles_triangle": 0.80,
            "scalene_triangle": 0.45,
            "right_triangle": 0.55,
            "acute_triangle": 0.65,
            "obtuse_triangle": 0.60,
        },
        "quadrilateral": {
            "square": 0.35,
            "rectangle_non_square": 0.72,
            "rhombus_non_square": 0.78,
            "parallelogram_only": 0.88,
        },
        "shape_type": {
            "triangle": 0.30,
            "quadrilateral": 0.55,
            "pentagon": 0.35,
            "hexagon": 0.40,
            "circle": 0.25,
            "ellipse": 0.50,
        },
        "convexity": {
            "convex_polygon": 0.70,
            "concave_polygon": 0.50,
        },
    }
    kind_scores = score_by_kind.get(normalized_kind)
    if kind_scores is None or normalized_variant not in kind_scores:
        raise ValueError(f"unsupported geometry counting task/variant: {task_kind} / {task_variant}")
    return float(kind_scores[normalized_variant])


def geometry_counting_variant_ambiguity_score(*, task_kind: str, task_variant: str) -> float:
    """Return normalized per-variant ambiguity for one counting predicate."""

    normalized_kind = str(task_kind).strip().lower()
    normalized_variant = str(task_variant).strip().lower()
    score_by_kind = {
        "angle": {
            "acute_angle": 0.30,
            "right_angle": 0.65,
            "obtuse_angle": 0.35,
        },
        "triangle": {
            "equilateral_triangle": 0.25,
            "isosceles_triangle": 0.85,
            "scalene_triangle": 0.50,
            "right_triangle": 0.60,
            "acute_triangle": 0.72,
            "obtuse_triangle": 0.68,
        },
        "quadrilateral": {
            "square": 0.30,
            "rectangle_non_square": 0.78,
            "rhombus_non_square": 0.82,
            "parallelogram_only": 0.92,
        },
        "shape_type": {
            "triangle": 0.25,
            "quadrilateral": 0.62,
            "pentagon": 0.32,
            "hexagon": 0.38,
            "circle": 0.28,
            "ellipse": 0.58,
        },
        "convexity": {
            "convex_polygon": 0.74,
            "concave_polygon": 0.52,
        },
    }
    kind_scores = score_by_kind.get(normalized_kind)
    if kind_scores is None or normalized_variant not in kind_scores:
        raise ValueError(f"unsupported geometry counting task/variant: {task_kind} / {task_variant}")
    return float(kind_scores[normalized_variant])


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


def build_geometry_counting_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    object_count: int,
    object_count_min: int,
    object_count_max: int,
    target_count: int,
    task_kind: str,
    task_variant: str,
) -> TaskComplexity:
    """Build one normalized counting-family complexity payload."""

    weights = resolve_geometry_complexity_weights(task_group_defaults, task_id=task_id)
    density_balance = geometry_counting_density_balance(
        target_count=int(target_count),
        object_count=int(object_count),
    )
    variant_ambiguity = geometry_counting_variant_ambiguity_score(
        task_kind=str(task_kind),
        task_variant=str(task_variant),
    )
    return build_geometry_task_complexity(
        weights=weights,
        components={
            "visual_scan": geometry_visual_scan_score(
                object_count=int(object_count),
                object_count_min=int(object_count_min),
                object_count_max=int(object_count_max),
            ),
            "classification_reasoning": geometry_counting_classification_reasoning_score(
                task_kind=str(task_kind),
                task_variant=str(task_variant),
            ),
            "ambiguity": clamp_unit_interval((0.55 * density_balance) + (0.45 * variant_ambiguity)),
            "output_burden": geometry_label_set_output_burden(
                target_count=int(target_count),
                object_count=int(object_count),
            ),
        },
    )


def build_geometry_measurement_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    visual_scan: float,
    measurement_precision: float,
    ambiguity: float,
    output_burden: float,
) -> TaskComplexity:
    """Build one normalized measurement-family complexity payload."""

    weights = resolve_geometry_complexity_weights(task_group_defaults, task_id=task_id)
    return build_geometry_task_complexity(
        weights=weights,
        components={
            "visual_scan": clamp_unit_interval(float(visual_scan)),
            "measurement_precision": clamp_unit_interval(float(measurement_precision)),
            "ambiguity": clamp_unit_interval(float(ambiguity)),
            "output_burden": clamp_unit_interval(float(output_burden)),
        },
    )


def geometry_transformation_reasoning_score(*, query_variant: str, scene_variant: str) -> float:
    """Return normalized reasoning load for one transformation-matching query."""

    base_by_query = {
        "translation_match": 0.36,
        "reflection_match": 0.58,
        "rotation_match": 0.80,
    }
    query_key = str(query_variant).strip().lower()
    scene_key = str(scene_variant).strip().lower()
    if query_key not in base_by_query:
        raise ValueError(f"unsupported geometry transformation query_variant: {query_variant}")
    scene_bonus = {
        "triangle": 0.00,
        "quadrilateral": 0.08,
    }.get(scene_key)
    if scene_bonus is None:
        raise ValueError(f"unsupported geometry transformation scene_variant: {scene_variant}")
    return clamp_unit_interval(float(base_by_query[query_key]) + float(scene_bonus))


def build_geometry_transformation_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    visual_scan: float,
    query_variant: str,
    scene_variant: str,
    ambiguity: float,
    evidence_point_count: int,
) -> TaskComplexity:
    """Build one normalized transformation-family complexity payload."""

    weights = resolve_geometry_complexity_weights(task_group_defaults, task_id=task_id)
    return build_geometry_task_complexity(
        weights=weights,
        components={
            "visual_scan": clamp_unit_interval(float(visual_scan)),
            "transformation_reasoning": geometry_transformation_reasoning_score(
                query_variant=str(query_variant),
                scene_variant=str(scene_variant),
            ),
            "ambiguity": clamp_unit_interval(float(ambiguity)),
            "output_burden": geometry_graph_point_output_burden(
                evidence_point_count=int(evidence_point_count),
            ),
        },
    )


def geometry_similarity_reasoning_score(*, query_variant: str, scene_variant: str) -> float:
    """Return normalized reasoning load for one similarity-counting query."""

    base_by_query = {
        "congruent_count": 0.44,
        "similar_count": 0.72,
    }
    query_key = str(query_variant).strip().lower()
    scene_key = str(scene_variant).strip().lower()
    if query_key not in base_by_query:
        raise ValueError(f"unsupported geometry similarity query_variant: {query_variant}")
    scene_bonus = {
        "triangle": 0.00,
        "quadrilateral": 0.08,
    }.get(scene_key)
    if scene_bonus is None:
        raise ValueError(f"unsupported geometry similarity scene_variant: {scene_variant}")
    return clamp_unit_interval(float(base_by_query[query_key]) + float(scene_bonus))


def build_geometry_similarity_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_variant: str,
    object_count: int,
    target_count: int,
) -> TaskComplexity:
    """Build one normalized similarity-family complexity payload."""

    weights = resolve_geometry_complexity_weights(task_group_defaults, task_id=task_id)
    density_balance = geometry_counting_density_balance(
        target_count=int(target_count),
        object_count=int(object_count),
    )
    visual_scan = 0.58 + (0.06 if str(scene_variant) == "quadrilateral" else 0.0)
    return build_geometry_task_complexity(
        weights=weights,
        components={
            "visual_scan": clamp_unit_interval(float(visual_scan)),
            "similarity_reasoning": geometry_similarity_reasoning_score(
                query_variant=str(query_variant),
                scene_variant=str(scene_variant),
            ),
            "ambiguity": clamp_unit_interval((0.55 * float(density_balance)) + (0.20 if str(query_variant) == "similar_count" else 0.10)),
            "output_burden": geometry_label_set_output_burden(
                target_count=int(target_count),
                object_count=int(object_count),
            ),
        },
    )


def geometry_coordinate_relation_reasoning_score(*, query_variant: str, scene_variant: str) -> float:
    """Return normalized reasoning load for one coordinate-relation query."""

    query_key = str(query_variant).strip().lower()
    scene_key = str(scene_variant).strip().lower()
    score_by_query = {
        "parallel_count": 0.46,
        "perpendicular_count": 0.58,
        "collinear_count": 0.44,
        "same_quadrant_count": 0.36,
        "point_in_shape_count": 0.58,
    }
    if query_key not in score_by_query:
        raise ValueError(f"unsupported geometry coordinate query_variant: {query_variant}")
    scene_bonus = {
        "segment_set": 0.00,
        "line_points": 0.04,
        "quadrant_points": 0.00,
        "polygon_lattice": 0.12,
    }.get(scene_key)
    if scene_bonus is None:
        raise ValueError(f"unsupported geometry coordinate scene_variant: {scene_variant}")
    return clamp_unit_interval(float(score_by_query[query_key]) + float(scene_bonus))


def build_geometry_coordinate_relation_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_variant: str,
    object_count: int,
    target_count: int | None,
    evidence_type: str,
    evidence_count: int,
) -> TaskComplexity:
    """Build one normalized coordinate-relation complexity payload."""

    weights = resolve_geometry_complexity_weights(task_group_defaults, task_id=task_id)
    normalized_scene = str(scene_variant).strip().lower()
    normalized_query = str(query_variant).strip().lower()
    if normalized_scene == "polygon_lattice":
        visual_scan = normalize_linear(
            float(object_count),
            min_value=3.0,
            max_value=5.0,
        )
    elif normalized_scene == "line_points":
        visual_scan = normalize_linear(
            float(object_count),
            min_value=6.0,
            max_value=8.0,
        )
    else:
        visual_scan = normalize_linear(
            float(object_count),
            min_value=6.0,
            max_value=8.0,
        )
    if normalized_query in {"parallel_count", "perpendicular_count"}:
        ambiguity = {
            "parallel_count": 0.40,
            "perpendicular_count": 0.54,
        }[normalized_query]
    else:
        density_balance = geometry_counting_density_balance(
            target_count=int(target_count or 0),
            object_count=int(object_count),
        )
        scene_bonus = 0.10 if normalized_scene == "polygon_lattice" else (0.04 if normalized_scene == "line_points" else 0.0)
        query_bonus = 0.04 if normalized_query == "collinear_count" else 0.0
        ambiguity = clamp_unit_interval((0.58 * float(density_balance)) + 0.16 + float(scene_bonus) + float(query_bonus))

    if str(evidence_type) == "graph_point_set":
        output_burden = geometry_graph_point_output_burden(
            evidence_point_count=int(evidence_count),
        )
    elif str(evidence_type) == "label_set":
        output_burden = geometry_label_set_output_burden(
            target_count=int(target_count or 0),
            object_count=int(object_count),
        )
    else:
        raise ValueError(f"unsupported geometry coordinate evidence_type: {evidence_type}")

    return build_geometry_task_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "coordinate_reasoning": geometry_coordinate_relation_reasoning_score(
                query_variant=str(query_variant),
                scene_variant=str(scene_variant),
            ),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def geometry_solid_view_reasoning_score(*, query_variant: str, max_height: int) -> float:
    """Return normalized reasoning load for one solid-view query."""

    normalized_query = str(query_variant).strip().lower()
    base_by_query = {
        "top_view_visible_count": 0.34,
        "front_view_visible_count": 0.56,
        "right_view_visible_count": 0.58,
    }
    if normalized_query not in base_by_query:
        raise ValueError(f"unsupported geometry solid-view query_variant: {query_variant}")
    height_bonus = normalize_linear(float(max_height), min_value=2.0, max_value=3.0) * 0.12
    return clamp_unit_interval(float(base_by_query[normalized_query]) + float(height_bonus))


def build_geometry_solid_view_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    query_variant: str,
    cube_count: int,
    max_height: int,
    target_count: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build one normalized complexity payload for cube-stack view counting."""

    weights = resolve_geometry_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.65 * normalize_linear(float(cube_count), min_value=4.0, max_value=8.0))
        + (0.35 * normalize_linear(float(max_height), min_value=2.0, max_value=3.0))
    )
    ambiguity = clamp_unit_interval(
        (0.50 * normalize_linear(float(target_count), min_value=2.0, max_value=7.0))
        + (0.30 * normalize_linear(float(cube_count - target_count), min_value=0.0, max_value=5.0))
        + (0.12 if str(query_variant) != "top_view_visible_count" else 0.0)
    )
    output_burden = normalize_linear(
        float(evidence_count),
        min_value=2.0,
        max_value=7.0,
    )
    return build_geometry_task_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "projection_reasoning": geometry_solid_view_reasoning_score(
                query_variant=str(query_variant),
                max_height=int(max_height),
            ),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def geometry_graphing_reasoning_score(*, scene_variant: str, query_variant: str) -> float:
    """Return normalized reasoning load for one plotted-function query."""

    normalized_query = str(query_variant).strip().lower()
    score_by_query = {
        "x_intercept_count": 0.42,
        "horizontal_line_intersection_count": 0.58,
        "turning_point_count": 0.66,
        "local_minima_count": 0.68,
        "local_maxima_count": 0.68,
    }
    if normalized_query not in score_by_query:
        raise ValueError(f"unsupported geometry graphing query_variant: {query_variant}")
    scene_bonus = {
        "quadratic": 0.00,
        "absolute_value": 0.03,
        "cubic": 0.08,
        "sinusoid": 0.14,
        "piecewise_linear": 0.12,
    }.get(str(scene_variant).strip().lower())
    if scene_bonus is None:
        raise ValueError(f"unsupported geometry graphing scene_variant: {scene_variant}")
    return clamp_unit_interval(float(score_by_query[normalized_query]) + float(scene_bonus))


def build_geometry_graphing_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_variant: str,
    object_count: int,
    target_count: int,
    evidence_count: int,
    has_query_line: bool,
) -> TaskComplexity:
    """Build one normalized complexity payload for geometry graphing count tasks."""

    weights = resolve_geometry_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.72 * normalize_linear(float(object_count), min_value=1.0, max_value=9.0))
        + (0.28 * (0.24 if bool(has_query_line) else 0.0))
    )
    ambiguity = clamp_unit_interval(
        (0.58 * normalize_linear(float(target_count), min_value=0.0, max_value=4.0))
        + (0.18 if str(query_variant).strip().lower() == "horizontal_line_intersection_count" else 0.0)
        + (0.10 if str(scene_variant).strip().lower() == "piecewise_linear" else 0.0)
    )
    output_burden = normalize_linear(
        float(evidence_count),
        min_value=0.0,
        max_value=4.0,
    )
    return build_geometry_task_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "graphing_reasoning": geometry_graphing_reasoning_score(
                scene_variant=str(scene_variant),
                query_variant=str(query_variant),
            ),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def geometry_analytical_reasoning_score(*, task_kind: str, task_variant: str) -> float:
    """Return normalized reasoning load for one analytical geometry variant."""

    normalized_kind = str(task_kind).strip().lower()
    normalized_variant = str(task_variant).strip().lower()
    score_by_kind = {
        "volume": {
            "rectangular_prism_given_lwh": 0.30,
            "triangular_prism_given_b_h_l": 0.55,
            "square_pyramid_given_base_height": 0.75,
            "cylinder_given_r_h": 0.50,
            "cone_given_r_h": 0.78,
            "sphere_given_r": 0.58,
        },
        "surface_area": {
            "rectangular_prism_given_lwh": 0.35,
            "triangular_prism_given_a_b_c_l": 0.72,
            "square_pyramid_given_base_side_slant_height": 0.70,
            "cylinder_given_r_h": 0.52,
            "cone_given_r_slant_height": 0.66,
            "sphere_given_r": 0.48,
        },
        "area": {
            "rectangle": 0.30,
            "triangle": 0.38,
            "parallelogram": 0.50,
            "trapezoid": 0.62,
            "rhombus": 0.66,
            "circle": 0.52,
            "ellipse": 0.72,
        },
        "length": {
            "triangle_altitude_side": 0.48,
            "rectangle_diagonal_side": 0.44,
            "rhombus_diagonal_side": 0.58,
            "isosceles_trapezoid_leg": 0.66,
            "inscribed_square_side": 0.72,
            "circle_chord_length": 0.78,
        },
        "perimeter": {
            "right_triangle_leg_hypotenuse": 0.50,
            "rectangle_side_diagonal": 0.46,
            "rhombus_diagonals": 0.62,
            "isosceles_trapezoid_bases_height": 0.70,
            "inscribed_square_diameter": 0.74,
        },
        "composite_area": {
            "rectangle_inner_cutout": 0.60,
            "rectangle_triangle_cutout": 0.68,
            "rectangle_triangle_union": 0.64,
            "l_shape_cutout": 0.76,
            "step_rectangles_union": 0.72,
        },
    }
    kind_scores = score_by_kind.get(normalized_kind)
    if kind_scores is None or normalized_variant not in kind_scores:
        raise ValueError(f"unsupported geometry analytical task/variant: {task_kind} / {task_variant}")
    return float(kind_scores[normalized_variant])


def geometry_analytical_variant_ambiguity_score(*, task_kind: str, task_variant: str) -> float:
    """Return normalized ambiguity for one analytical geometry variant."""

    normalized_kind = str(task_kind).strip().lower()
    normalized_variant = str(task_variant).strip().lower()
    score_by_kind = {
        "volume": {
            "rectangular_prism_given_lwh": 0.28,
            "triangular_prism_given_b_h_l": 0.52,
            "square_pyramid_given_base_height": 0.62,
            "cylinder_given_r_h": 0.42,
            "cone_given_r_h": 0.70,
            "sphere_given_r": 0.46,
        },
        "surface_area": {
            "rectangular_prism_given_lwh": 0.35,
            "triangular_prism_given_a_b_c_l": 0.68,
            "square_pyramid_given_base_side_slant_height": 0.60,
            "cylinder_given_r_h": 0.50,
            "cone_given_r_slant_height": 0.72,
            "sphere_given_r": 0.44,
        },
        "area": {
            "rectangle": 0.28,
            "triangle": 0.34,
            "parallelogram": 0.48,
            "trapezoid": 0.62,
            "rhombus": 0.68,
            "circle": 0.42,
            "ellipse": 0.72,
        },
        "length": {
            "triangle_altitude_side": 0.40,
            "rectangle_diagonal_side": 0.36,
            "rhombus_diagonal_side": 0.50,
            "isosceles_trapezoid_leg": 0.58,
            "inscribed_square_side": 0.62,
            "circle_chord_length": 0.72,
        },
        "perimeter": {
            "right_triangle_leg_hypotenuse": 0.42,
            "rectangle_side_diagonal": 0.40,
            "rhombus_diagonals": 0.54,
            "isosceles_trapezoid_bases_height": 0.64,
            "inscribed_square_diameter": 0.66,
        },
        "composite_area": {
            "rectangle_inner_cutout": 0.52,
            "rectangle_triangle_cutout": 0.60,
            "rectangle_triangle_union": 0.56,
            "l_shape_cutout": 0.70,
            "step_rectangles_union": 0.66,
        },
    }
    kind_scores = score_by_kind.get(normalized_kind)
    if kind_scores is None or normalized_variant not in kind_scores:
        raise ValueError(f"unsupported geometry analytical task/variant: {task_kind} / {task_variant}")
    return float(kind_scores[normalized_variant])


def build_geometry_analytical_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    task_kind: str,
    task_variant: str,
    annotation_count: int,
    answer_format: str,
    reasoning_mode: str | None = None,
) -> TaskComplexity:
    """Build one normalized analytical-family complexity payload."""

    weights = resolve_geometry_complexity_weights(task_group_defaults, task_id=task_id)
    normalized_mode = str(reasoning_mode).strip().lower() if reasoning_mode is not None else ""
    mode_reasoning = 0.0 if not normalized_mode else {
        "explicit": 0.0,
        "derived": 0.22,
    }.get(normalized_mode)
    if reasoning_mode is not None and mode_reasoning is None:
        raise ValueError(f"unsupported geometry analytical reasoning_mode: {reasoning_mode}")
    mode_ambiguity = 0.0 if not normalized_mode else {
        "explicit": 0.0,
        "derived": 0.18,
    }.get(normalized_mode)
    if reasoning_mode is not None and mode_ambiguity is None:
        raise ValueError(f"unsupported geometry analytical reasoning_mode: {reasoning_mode}")

    visual_scan = normalize_linear(
        float(annotation_count),
        min_value=1.0,
        max_value=4.0,
    )
    return build_geometry_task_complexity(
        weights=weights,
        components={
            "visual_scan": visual_scan,
            "analytical_reasoning": clamp_unit_interval(
                geometry_analytical_reasoning_score(
                    task_kind=str(task_kind),
                    task_variant=str(task_variant),
                )
                + float(mode_reasoning)
            ),
            "ambiguity": clamp_unit_interval(
                (0.65 * geometry_analytical_variant_ambiguity_score(
                    task_kind=str(task_kind),
                    task_variant=str(task_variant),
                ))
                + (0.15 * float(visual_scan))
                + (0.20 * float(mode_ambiguity))
            ),
            "output_burden": geometry_analytical_output_burden(
                answer_format=str(answer_format),
                evidence_ref_count=int(annotation_count),
            ),
        },
    )


__all__ = [
    "build_geometry_analytical_complexity",
    "build_geometry_counting_complexity",
    "build_geometry_coordinate_relation_complexity",
    "build_geometry_comparison_complexity",
    "build_geometry_graphing_complexity",
    "build_geometry_measurement_complexity",
    "build_geometry_similarity_complexity",
    "build_geometry_solid_view_complexity",
    "build_geometry_transformation_complexity",
    "build_geometry_task_complexity",
    "clamp_unit_interval",
    "geometry_analytical_output_burden",
    "geometry_analytical_reasoning_score",
    "geometry_analytical_variant_ambiguity_score",
    "geometry_answer_format_output_burden",
    "geometry_comparison_reasoning_score",
    "geometry_coordinate_relation_reasoning_score",
    "geometry_counting_classification_reasoning_score",
    "geometry_counting_density_balance",
    "geometry_counting_variant_ambiguity_score",
    "geometry_gap_ambiguity_score",
    "geometry_graphing_reasoning_score",
    "geometry_graph_point_output_burden",
    "geometry_label_set_output_burden",
    "geometry_measurement_output_burden",
    "geometry_similarity_reasoning_score",
    "geometry_solid_view_reasoning_score",
    "geometry_transformation_reasoning_score",
    "geometry_visual_scan_score",
    "normalize_linear",
    "resolve_geometry_complexity_weights",
]
