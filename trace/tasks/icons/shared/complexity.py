"""Shared complexity helpers for icon tasks.

These helpers implement the icon-domain complexity policy described in
`skills/task-complexity/`:
- tasks emit normalized criterion values in `[0, 1]`,
- domain/task-group/task config owns the active criteria and weights,
- final `complexity_score` is the normalized weighted mean over the active set.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, Mapping, Sequence

from ....core.task_group_config import resolve_task_group_section_defaults
from ....core.types import TaskComplexity
from .icon_scene import overlap_fraction_smaller


def _clip01(value: float) -> float:
    """Clamp one numeric value into `[0, 1]`."""

    return max(0.0, min(1.0, float(value)))


def _normalize_linear(value: float, *, min_value: float, max_value: float) -> float:
    """Normalize one scalar linearly into `[0, 1]`."""

    lo = float(min_value)
    hi = float(max_value)
    if hi <= lo:
        return 0.0
    return _clip01((float(value) - lo) / (hi - lo))


def resolve_icon_complexity_weights(
    task_group_defaults: Mapping[str, Any],
    *,
    task_id: str,
) -> Dict[str, float]:
    """Resolve normalized active complexity weights for one icon task."""

    complexity_defaults = resolve_task_group_section_defaults(
        task_group_defaults,
        "complexity",
        task_id=str(task_id),
    )
    raw_weights = complexity_defaults.get("criteria_weights", {})
    if not isinstance(raw_weights, Mapping):
        raise ValueError(f"complexity.criteria_weights must be a mapping for {task_id}")

    positive_weights: Dict[str, float] = {}
    for key, value in raw_weights.items():
        name = str(key).strip()
        if not name:
            continue
        weight = float(value)
        if weight > 0.0:
            positive_weights[name] = float(weight)
    if not positive_weights:
        raise ValueError(f"complexity.criteria_weights must contain at least one positive weight for {task_id}")

    total = float(sum(positive_weights.values()))
    return {name: float(weight) / total for name, weight in positive_weights.items()}


def build_icon_task_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    criterion_values: Mapping[str, float],
) -> TaskComplexity:
    """Build one task complexity payload from normalized icon-domain criteria."""

    weights = resolve_icon_complexity_weights(task_group_defaults, task_id=str(task_id))
    normalized_components: Dict[str, float] = {}
    for criterion_name in weights:
        if criterion_name not in criterion_values:
            raise ValueError(f"missing complexity criterion '{criterion_name}' for {task_id}")
        value = float(criterion_values[criterion_name])
        if value < -1e-6 or value > 1.0 + 1e-6:
            raise ValueError(
                f"complexity criterion '{criterion_name}' for {task_id} must be normalized into [0, 1], got {value}"
            )
        normalized_components[criterion_name] = _clip01(value)

    score = sum(float(weights[name]) * float(normalized_components[name]) for name in weights)
    return TaskComplexity(
        complexity_score=_clip01(score),
        complexity_components=normalized_components,
    )


def icon_visual_scan_score(
    *,
    object_count: int,
    object_count_min: int,
    object_count_max: int,
) -> float:
    """Normalize visual scan load from the active object-count support."""

    return _normalize_linear(
        float(object_count),
        min_value=float(object_count_min),
        max_value=float(object_count_max),
    )


def icon_target_density_balance(*, target_count: int, object_count: int) -> float:
    """Return one density-balance factor that peaks near a 50/50 target split."""

    if int(object_count) <= 0:
        return 0.0
    density = float(target_count) / float(max(1, int(object_count)))
    return _clip01(1.0 - abs((2.0 * density) - 1.0))


def icon_semantic_match_score(*, queried_attribute_count: int, max_attribute_count: int = 3) -> float:
    """Normalize semantic matching difficulty from conjunction depth."""

    return _normalize_linear(
        float(queried_attribute_count),
        min_value=1.0,
        max_value=float(max(1, int(max_attribute_count))),
    )


def icon_scene_clutter_score(
    *,
    scene_instances: Sequence[Mapping[str, Any]],
    scene_icon_size_min_px: int,
    scene_icon_size_max_px: int,
    scene_max_overlap_fraction: float,
    noise_edit_count_range: Sequence[int | float],
) -> float:
    """Measure icon-scene clutter from size, overlap, and per-icon noise."""

    if not scene_instances:
        return 0.0

    size_samples = []
    noise_load_samples = []
    boxes = []
    for entity in scene_instances:
        bbox = entity.get("bbox_xyxy", ())
        if isinstance(bbox, Sequence) and len(bbox) >= 4:
            width = max(1.0, float(bbox[2]) - float(bbox[0]))
            height = max(1.0, float(bbox[3]) - float(bbox[1]))
            size_samples.append(max(width, height))
            boxes.append((int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])))
        noise_edits = entity.get("noise_edits", ())
        if isinstance(noise_edits, Sequence):
            noise_load_samples.append(float(len(noise_edits)))
        else:
            noise_load_samples.append(0.0)

    avg_size = sum(size_samples) / float(max(1, len(size_samples)))
    size_load = 1.0 - _normalize_linear(
        avg_size,
        min_value=float(scene_icon_size_min_px),
        max_value=float(max(scene_icon_size_min_px, scene_icon_size_max_px)),
    )

    max_pair_overlap = 0.0
    for left, right in combinations(boxes, 2):
        max_pair_overlap = max(max_pair_overlap, float(overlap_fraction_smaller(left, right)))
    overlap_cap = max(1e-6, float(scene_max_overlap_fraction))
    overlap_load = _clip01(max_pair_overlap / overlap_cap)

    noise_cap = max(
        0.0,
        max((float(value) for value in noise_edit_count_range), default=0.0),
    )
    noise_load = (
        _clip01(sum(noise_load_samples) / (float(len(noise_load_samples)) * noise_cap))
        if noise_cap > 0.0 and noise_load_samples
        else 0.0
    )

    return _clip01((0.45 * size_load) + (0.35 * overlap_load) + (0.20 * noise_load))


def build_icons_counting_type_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    object_count: int,
    target_count: int,
    object_count_min: int,
    object_count_max: int,
    scene_instances: Sequence[Mapping[str, Any]],
    render_params: Mapping[str, Any],
) -> TaskComplexity:
    """Build complexity for the reference-scene type counting task."""

    visual_scan = icon_visual_scan_score(
        object_count=int(object_count),
        object_count_min=int(object_count_min),
        object_count_max=int(object_count_max),
    )
    ambiguity = _clip01(
        (0.70 * icon_target_density_balance(target_count=int(target_count), object_count=int(object_count)))
        + (0.30 * visual_scan)
    )
    clutter = icon_scene_clutter_score(
        scene_instances=scene_instances,
        scene_icon_size_min_px=int(render_params["scene_icon_size_min_px"]),
        scene_icon_size_max_px=int(render_params["scene_icon_size_max_px"]),
        scene_max_overlap_fraction=float(render_params["scene_max_overlap_fraction"]),
        noise_edit_count_range=render_params["icon_noise_edit_count_range"],
    )
    return build_icon_task_complexity(
        task_group_defaults=task_group_defaults,
        task_id=str(task_id),
        criterion_values={
            "visual_scan": float(visual_scan),
            "semantic_match": float(icon_semantic_match_score(queried_attribute_count=1)),
            "ambiguity": float(ambiguity),
            "clutter": float(clutter),
        },
    )


def build_icons_counting_color_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    object_count: int,
    target_count: int,
    object_count_min: int,
    object_count_max: int,
    sampled_palette_size: int,
    min_color_distance: float,
    scene_instances: Sequence[Mapping[str, Any]],
    render_params: Mapping[str, Any],
) -> TaskComplexity:
    """Build complexity for the reference-scene color counting task."""

    visual_scan = icon_visual_scan_score(
        object_count=int(object_count),
        object_count_min=int(object_count_min),
        object_count_max=int(object_count_max),
    )
    palette_load = _normalize_linear(float(sampled_palette_size), min_value=3.0, max_value=12.0)
    distance_difficulty = 1.0 - _normalize_linear(float(min_color_distance), min_value=40.0, max_value=60.0)
    ambiguity = _clip01(
        (0.55 * icon_target_density_balance(target_count=int(target_count), object_count=int(object_count)))
        + (0.25 * palette_load)
        + (0.20 * distance_difficulty)
    )
    clutter = icon_scene_clutter_score(
        scene_instances=scene_instances,
        scene_icon_size_min_px=int(render_params["scene_icon_size_min_px"]),
        scene_icon_size_max_px=int(render_params["scene_icon_size_max_px"]),
        scene_max_overlap_fraction=float(render_params["scene_max_overlap_fraction"]),
        noise_edit_count_range=render_params["icon_noise_edit_count_range"],
    )
    return build_icon_task_complexity(
        task_group_defaults=task_group_defaults,
        task_id=str(task_id),
        criterion_values={
            "visual_scan": float(visual_scan),
            "semantic_match": float(icon_semantic_match_score(queried_attribute_count=1)),
            "ambiguity": float(ambiguity),
            "clutter": float(clutter),
        },
    )


def build_icons_counting_orientation_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    object_count: int,
    target_count: int,
    object_count_min: int,
    object_count_max: int,
    rotation_candidate_count: int,
    scene_instances: Sequence[Mapping[str, Any]],
    render_params: Mapping[str, Any],
) -> TaskComplexity:
    """Build complexity for the reference-scene orientation counting task."""

    visual_scan = icon_visual_scan_score(
        object_count=int(object_count),
        object_count_min=int(object_count_min),
        object_count_max=int(object_count_max),
    )
    rotation_load = _normalize_linear(float(rotation_candidate_count), min_value=2.0, max_value=4.0)
    ambiguity = _clip01(
        (0.65 * icon_target_density_balance(target_count=int(target_count), object_count=int(object_count)))
        + (0.35 * rotation_load)
    )
    clutter = icon_scene_clutter_score(
        scene_instances=scene_instances,
        scene_icon_size_min_px=int(render_params["scene_icon_size_min_px"]),
        scene_icon_size_max_px=int(render_params["scene_icon_size_max_px"]),
        scene_max_overlap_fraction=float(render_params["scene_max_overlap_fraction"]),
        noise_edit_count_range=render_params["icon_noise_edit_count_range"],
    )
    return build_icon_task_complexity(
        task_group_defaults=task_group_defaults,
        task_id=str(task_id),
        criterion_values={
            "visual_scan": float(visual_scan),
            "semantic_match": float(icon_semantic_match_score(queried_attribute_count=1)),
            "ambiguity": float(ambiguity),
            "clutter": float(clutter),
        },
    )


def build_icons_counting_attribute_binding_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    object_count: int,
    target_count: int,
    distractor_count: int,
    object_count_min: int,
    object_count_max: int,
    distractor_categories: Sequence[str],
    scene_instances: Sequence[Mapping[str, Any]],
    render_params: Mapping[str, Any],
) -> TaskComplexity:
    """Build complexity for the multi-attribute binding counting task."""

    visual_scan = icon_visual_scan_score(
        object_count=int(object_count),
        object_count_min=int(object_count_min),
        object_count_max=int(object_count_max),
    )
    distractor_total = float(max(1, int(distractor_count)))
    hard_share = sum(
        1 for category in distractor_categories if str(category) in {"same_type_color", "same_type_orientation", "same_color_orientation"}
    ) / distractor_total
    medium_share = sum(
        1 for category in distractor_categories if str(category) in {"same_type_only", "same_color_only", "same_orientation_only"}
    ) / distractor_total
    ambiguity = _clip01(
        (0.55 * hard_share)
        + (0.20 * medium_share)
        + (0.25 * icon_target_density_balance(target_count=int(target_count), object_count=int(object_count)))
    )
    clutter = icon_scene_clutter_score(
        scene_instances=scene_instances,
        scene_icon_size_min_px=int(render_params["scene_icon_size_min_px"]),
        scene_icon_size_max_px=int(render_params["scene_icon_size_max_px"]),
        scene_max_overlap_fraction=float(render_params["scene_max_overlap_fraction"]),
        noise_edit_count_range=render_params["icon_noise_edit_count_range"],
    )
    return build_icon_task_complexity(
        task_group_defaults=task_group_defaults,
        task_id=str(task_id),
        criterion_values={
            "visual_scan": float(visual_scan),
            "semantic_match": float(icon_semantic_match_score(queried_attribute_count=3)),
            "ambiguity": float(ambiguity),
            "clutter": float(clutter),
        },
    )


def build_icons_counting_size_relation_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    object_count: int,
    target_count: int,
    object_count_min: int,
    object_count_max: int,
    reference_nominal_size_px: int,
    scene_nominal_sizes_px: Sequence[int],
    size_relation_min_delta_px: int,
    scene_size_min_px: int,
    scene_size_max_px: int,
    scene_instances: Sequence[Mapping[str, Any]],
    render_params: Mapping[str, Any],
) -> TaskComplexity:
    """Build complexity for the icon size-relation counting task."""

    visual_scan = icon_visual_scan_score(
        object_count=int(object_count),
        object_count_min=int(object_count_min),
        object_count_max=int(object_count_max),
    )
    if scene_nominal_sizes_px:
        avg_size_gap = sum(abs(int(size) - int(reference_nominal_size_px)) for size in scene_nominal_sizes_px) / float(
            len(scene_nominal_sizes_px)
        )
    else:
        avg_size_gap = float(size_relation_min_delta_px)
    max_gap = max(
        1.0,
        float(max(int(scene_size_max_px), int(reference_nominal_size_px)) - min(int(scene_size_min_px), int(reference_nominal_size_px))),
    )
    size_gap_difficulty = 1.0 - _normalize_linear(
        float(avg_size_gap),
        min_value=float(size_relation_min_delta_px),
        max_value=float(max_gap),
    )
    ambiguity = _clip01(
        (0.55 * icon_target_density_balance(target_count=int(target_count), object_count=int(object_count)))
        + (0.45 * size_gap_difficulty)
    )
    clutter = icon_scene_clutter_score(
        scene_instances=scene_instances,
        scene_icon_size_min_px=int(render_params["scene_icon_size_min_px"]),
        scene_icon_size_max_px=int(render_params["scene_icon_size_max_px"]),
        scene_max_overlap_fraction=float(render_params["scene_max_overlap_fraction"]),
        noise_edit_count_range=render_params["icon_noise_edit_count_range"],
    )
    return build_icon_task_complexity(
        task_group_defaults=task_group_defaults,
        task_id=str(task_id),
        criterion_values={
            "visual_scan": float(visual_scan),
            "semantic_match": float(icon_semantic_match_score(queried_attribute_count=1)),
            "ambiguity": float(ambiguity),
            "clutter": float(clutter),
        },
    )


def build_icons_relation_relative_position_type_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    object_count: int,
    target_count: int,
    distractor_count: int,
    object_count_min: int,
    object_count_max: int,
    same_type_nonspatial_distractor_count: int,
    different_type_spatial_distractor_count: int,
    target_region_area_ratio: float,
    same_type_boundary_proximity: float,
    scene_instances: Sequence[Mapping[str, Any]],
    render_params: Mapping[str, Any],
) -> TaskComplexity:
    """Build complexity for the anchored same-type directional relation task."""

    visual_scan = icon_visual_scan_score(
        object_count=int(object_count),
        object_count_min=int(object_count_min),
        object_count_max=int(object_count_max),
    )
    distractor_total = float(max(1, int(distractor_count)))
    same_type_wrong_side_share = float(same_type_nonspatial_distractor_count) / distractor_total
    different_type_queried_side_share = float(different_type_spatial_distractor_count) / distractor_total
    region_balance = _clip01(1.0 - abs((2.0 * float(target_region_area_ratio)) - 1.0))
    spatial_reasoning = _clip01((0.40 * region_balance) + (0.60 * visual_scan))
    ambiguity = _clip01(
        (0.35 * same_type_wrong_side_share)
        + (0.35 * different_type_queried_side_share)
        + (0.20 * icon_target_density_balance(target_count=int(target_count), object_count=int(object_count)))
        + (0.10 * _clip01(float(same_type_boundary_proximity)))
    )
    clutter = icon_scene_clutter_score(
        scene_instances=scene_instances,
        scene_icon_size_min_px=int(render_params["scene_icon_size_min_px"]),
        scene_icon_size_max_px=int(render_params["scene_icon_size_max_px"]),
        scene_max_overlap_fraction=float(render_params["scene_max_overlap_fraction"]),
        noise_edit_count_range=render_params["icon_noise_edit_count_range"],
    )
    return build_icon_task_complexity(
        task_group_defaults=task_group_defaults,
        task_id=str(task_id),
        criterion_values={
            "visual_scan": float(visual_scan),
            "spatial_reasoning": float(spatial_reasoning),
            "ambiguity": float(ambiguity),
            "clutter": float(clutter),
        },
    )


__all__ = [
    "build_icon_task_complexity",
    "build_icons_counting_color_complexity",
    "build_icons_counting_attribute_binding_complexity",
    "build_icons_counting_orientation_complexity",
    "build_icons_counting_size_relation_complexity",
    "build_icons_counting_type_complexity",
    "build_icons_relation_relative_position_type_complexity",
    "icon_scene_clutter_score",
    "icon_semantic_match_score",
    "icon_target_density_balance",
    "icon_visual_scan_score",
    "resolve_icon_complexity_weights",
]
